"""Sumele acordurilor, citite din textul integral al actelor de pe legis.md.

Titlurile actelor spun suma doar la ~5% din acorduri. Textul integral o spune
aproape mereu: legea de ratificare („Art. 1. – Se ratifică Acordul … în sumă de
25 de milioane de euro"), hotărârea de aprobare a semnării, hotărârea care
aprobă proiectul de lege sau acordul însuși, anexat la act.

    python legis_sume.py --headed --profil .legis_profil --browser msedge
    python legis_sume.py --limita-min 20        # se oprește după 20 de minute;
                                                # rularea următoare continuă de unde a rămas
    python legis_sume.py --doar 135636 121528   # doar actele cu aceste doc_id (test)
    python legis_sume.py --reincearca           # reia și actele care au dat eroare
    python legis_sume.py --fara-browser         # descarcă direct, fără browser (pe GitHub Actions)

Pentru fiecare act din registru (legi, hotărâri, ordine, acorduri publicate —
nu și decretele, care nu conțin sume) descarcă PDF-ul de pe
legis.md/cautare/downloadpdf/<doc_id>, prin aceeași fereastră de browser care a
trecut de Cloudflare, scoate textul și caută sumele. Rezultatul, cu fragmentul
de text din care vine fiecare sumă, se scrie în date/legis_sume.json. Un act
deja citit nu se mai descarcă.

Are nevoie de:  pip install playwright pypdf     (sau pdfplumber în loc de pypdf)
                --fara-browser are nevoie doar de:  pip install requests pypdf

Coduri de ieșire: 0 = a mers, 3 = blocat de Cloudflare, 1 = altă eroare.
"""
import argparse, base64, datetime, io, json, re, sys, time, unicodedata
from pathlib import Path

AICI = Path(__file__).resolve().parent
sys.path.insert(0, str(AICI))

IESIRE = AICI / 'date' / 'legis_sume.json'
BLOCAT = re.compile(r"Just a moment|verificării de securitate|nu ești un robot|Verify you are human|Checking your browser", re.I)
MAX_OCTETI = 30 * 1024 * 1024        # un PDF mai mare (acord cu toate anexele scanate) se sare


# ------------------------------------------------------------- sumele din text

def _fara_diacritice(s):
    return unicodedata.normalize('NFD', s).encode('ascii', 'ignore').decode('ascii').lower()


VALUTE = [
    (r'euro|eur\b|€', 'EUR'),
    (r'dolari(?:\s+(?:sua|s\.u\.a\.?|ai\s+sua|americani))?|usd\b|\$', 'USD'),
    (r'drepturi\s+speciale\s+de\s+tragere|dst\b|dts\b|sdr\b|xdr\b', 'DST'),
    (r'yeni(?:\s+japonezi)?|yen\b|jpy\b', 'JPY'),
    (r'franci\s+elvetieni|chf\b', 'CHF'),
    (r'lire\s+sterline|gbp\b', 'GBP'),
    (r'coroane\s+suedeze|sek\b', 'SEK'),
    (r'coroane\s+daneze|dkk\b', 'DKK'),
    (r'zloti|pln\b', 'PLN'),
    (r'yuani|cny\b|rmb\b', 'CNY'),
    (r'ecu\b', 'ECU'),
    (r'marci\s+germane|dem\b', 'DEM'),
    (r'lei\s+romanesti', 'ROL'),
    (r'lei(?:\s+moldovenesti)?|mdl\b', 'MDL'),
]
_VAL = '|'.join('(?:%s)' % p for p, _ in VALUTE)
_NUM = r'\d{1,3}(?:[ .,]\d{3})+(?:[.,]\d{1,2})?|\d+(?:[.,]\d+)?'
_MULT = r'miliarde|miliard|milioane|milion|mil\.?|mln\.?|mii|millions?|billions?'
# „25 de milioane de euro", „25 000 000 (douăzeci și cinci milioane) euro", „52,9 milioane EUR"
RX_DUPA = re.compile(r'(?<![\d.,])(' + _NUM + r')(?![\d])\s*(?:\([^)]{2,160}\)\s*)?(?:de\s+)?(' + _MULT + r')?\s*(?:de\s+)?(' + _VAL + r')', re.I)
# „EUR 25,000,000", „USD 15 million", „€ 4 340 000"
RX_INAINTE = re.compile(r'(?<![a-z])(eur|usd|sdr|xdr|chf|jpy|gbp|€|\$)\s?(' + _NUM + r')(?![\d])\s*(' + _MULT + r')?', re.I)
MULT = {'miliarde': 1e9, 'miliard': 1e9, 'billion': 1e9, 'billions': 1e9, 'milioane': 1e6, 'milion': 1e6,
        'mil': 1e6, 'mil.': 1e6, 'mln': 1e6, 'mln.': 1e6, 'million': 1e6, 'millions': 1e6, 'mii': 1e3}


def valuta(cuvant):
    c = _fara_diacritice(cuvant).strip()
    for p, cod in VALUTE:
        if re.fullmatch(p, c):
            return cod
    return None


def numar(s):
    """„25 000 000" → 25000000 · „25.000.000,00" → 25000000 · „25,000,000" → 25000000 ·
    „52,9" → 52.9 · „13.1" → 13.1"""
    s = s.replace('\u00a0', ' ').strip()
    if re.fullmatch(r'\d{1,3}(?:[ .,]\d{3})+', s):
        return float(re.sub(r'[ .,]', '', s))
    m = re.fullmatch(r'(\d{1,3}(?:[ .]\d{3})+),(\d{1,2})', s) or re.fullmatch(r'(\d{1,3}(?:[ ,]\d{3})+)\.(\d{1,2})', s)
    if m:
        return float(re.sub(r'[ .,]', '', m.group(1)) + '.' + m.group(2))
    if re.fullmatch(r'\d+[.,]\d+', s):
        return float(s.replace(',', '.'))
    return float(re.sub(r'\D', '', s) or 0)


def _scor(inainte, propozitie, cod, v):
    i, p = _fara_diacritice(inainte), _fara_diacritice(propozitie)
    s = 0
    if re.search(r'\b(?:in|de|cu)\s+(?:suma|valoare|marime|cuantum)(?:\s+totala)?(?:\s+de)?\s*$', i[-45:]):
        s += 6
    elif re.search(r'suma\b|valoare|cuantum|marime|in limita|pana la|nu (?:va )?depasi|amount|not exceeding|up to|equivalent', i[-70:]):
        s += 3
    if re.search(r'se ratifica|se aproba|hotaraste|se accepta', p):
        s += 4
    if re.search(r'imprumut|grant|credit|finantar|asistent|ajutor|loan|lend|financing|facilit', p):
        s += 2
    if re.search(r'dobanz|comision|taxa|penalit|interest|fee|prima de|rambursar', i[-70:]):
        s -= 4
    if cod == 'MDL':
        s -= 2
    if v >= 1e6:
        s += 1
    return s


def sume_din_text(text, maxim=5):
    """Sumele dintr-un act, cele mai probabile primele: [{v, val, f, s}].
    f = fragmentul de text (≤ 200 caractere) din care vine suma, s = scorul."""
    t = re.sub(r'-\s*\n\s*', '', text or '')              # despărțiri în silabe la capăt de rând
    t = re.sub(r'\s+', ' ', t)
    gasite = {}

    def adauga(start, end, v, cod):
        if not cod or v < 1000:
            return
        inceput = max(0, t.rfind('. ', 0, start) + 1, t.rfind('; ', 0, start) + 1, start - 300)
        propozitie = t[inceput:min(len(t), end + 120)]
        s = _scor(t[max(0, start - 160):start], propozitie, cod, v)
        if s < 2:
            return
        a, b = max(0, start - 120), min(len(t), end + 60)
        f = ('…' if a > 0 else '') + t[a:b].strip() + ('…' if b < len(t) else '')
        k = (round(v, 2), cod)
        if k not in gasite or gasite[k]['s'] < s:
            gasite[k] = {'v': round(v, 2), 'val': cod, 'f': f[:220], 's': s, 'poz': start}

    for m in RX_DUPA.finditer(t):
        v = numar(m.group(1))
        mult = (m.group(2) or '').lower()
        if mult and v < 1e5:                  # „25.000.000 mil. EUR" (greșeală de tipar) rămâne 25 de milioane
            v *= MULT.get(mult, 1)
        adauga(m.start(), m.end(), v, valuta(m.group(3)))
    for m in RX_INAINTE.finditer(t):
        v = numar(m.group(2))
        mult = (m.group(3) or '').lower()
        if mult and v < 1e5:
            v *= MULT.get(mult, 1)
        sym = m.group(1).lower()
        cod = {'€': 'EUR', '$': 'USD', 'sdr': 'DST', 'xdr': 'DST'}.get(sym, sym.upper())
        adauga(m.start(), m.end(), v, cod)

    rez = sorted(gasite.values(), key=lambda x: (-x['s'], x['poz']))[:maxim]
    for r in rez:
        r.pop('poz', None)
        if r['v'] == int(r['v']):
            r['v'] = int(r['v'])
    return rez


# ------------------------------------------------------------------ actele

def tinte(brut):
    """doc_id-urile de citit: actele de acord din registru, fără decrete."""
    import legis_pagina as pagina
    from legis_clasifica import clasifica
    out = {}
    for r in brut:
        t = pagina.repara(re.sub(r'^(Modificat|Abrogat|Suspendat)\s*', '', r.get('t', '')).strip())
        if not clasifica(t):
            continue
        if re.match(r'^DP', r.get('c', '')):
            continue
        out[str(r['id'])] = r.get('c', '')
    return out


def text_din_pdf(octeti):
    try:
        import pdfplumber
        with pdfplumber.open(io.BytesIO(octeti)) as pdf:
            return '\n'.join((p.extract_text() or '') for p in pdf.pages), len(pdf.pages)
    except ImportError:
        pass
    try:
        from pypdf import PdfReader
    except ImportError:
        raise SystemExit('Lipsește biblioteca pentru PDF. Rulează:  pip install pypdf')
    r = PdfReader(io.BytesIO(octeti))
    return '\n'.join((p.extract_text() or '') for p in r.pages), len(r.pages)


JS_DESCARCA = """async (url) => {
  const c = new AbortController(), t = setTimeout(() => c.abort(), 90000);
  try {
    const r = await fetch(url, {cache: 'no-store', credentials: 'include', signal: c.signal});
    const tip = r.headers.get('content-type') || '';
    const b = new Uint8Array(await r.arrayBuffer());
    if (b.length > %d) return {status: r.status, tip: tip, mare: b.length};
    let s = '';
    for (let i = 0; i < b.length; i += 0x8000) s += String.fromCharCode.apply(null, b.subarray(i, i + 0x8000));
    return {status: r.status, tip: tip, b64: btoa(s)};
  } finally { clearTimeout(t); }
}""" % MAX_OCTETI


def incarca():
    try:
        return json.load(open(IESIRE, encoding='utf-8'))
    except Exception:
        return {'acte': {}}


def salveaza(baza):
    IESIRE.parent.mkdir(exist_ok=True)
    baza['actualizat'] = datetime.datetime.now().strftime('%Y-%m-%d %H:%M')
    tmp = IESIRE.with_suffix('.tmp')
    json.dump(baza, open(tmp, 'w', encoding='utf-8'), ensure_ascii=False, indent=0, sort_keys=True)
    tmp.replace(IESIRE)


def main():
    ap = argparse.ArgumentParser(description='Sumele acordurilor din textele actelor de pe legis.md')
    ap.add_argument('--headed', action='store_true', help='fereastră vizibilă (ca să poți bifa Cloudflare)')
    ap.add_argument('--profil', help='dosarul profilului de browser (păstrează cookie-ul Cloudflare)')
    ap.add_argument('--browser', help='canalul browserului instalat, ex. msedge')
    ap.add_argument('--asteapta-cf', type=int, default=300, help='câte secunde aștept trecerea de Cloudflare')
    ap.add_argument('--limita-min', type=float, default=0, help='oprește după atâtea minute (0 = fără limită)')
    ap.add_argument('--pauza', type=float, default=0.6, help='secunde între două descărcări')
    ap.add_argument('--doar', nargs='*', help='doar aceste doc_id')
    ap.add_argument('--reincearca', action='store_true', help='reia și actele cu eroare')
    ap.add_argument('--fara-browser', action='store_true', help='descarcă direct (requests), fără browser')
    ap.add_argument('--url', default='https://www.legis.md/', help=argparse.SUPPRESS)   # pentru teste
    a = ap.parse_args()

    brut = json.load(open(AICI / 'legis_brut.json', encoding='utf-8'))
    toate = tinte(brut)
    baza = incarca()
    acte = baza.setdefault('acte', {})
    if a.doar:
        de_citit = [d for d in a.doar if d in toate] or list(a.doar)
    else:
        de_citit = [d for d in toate if d not in acte or (a.reincearca and acte[d].get('eroare'))]
    # cele mai noi întâi: doc_id-urile mari sunt actele recente
    de_citit.sort(key=lambda d: -int(d) if d.isdigit() else 0)
    if a.doar:
        print(f'{len(de_citit)} acte cerute cu --doar')
    else:
        print(f'{len(toate)} acte de acord în registru · {len(toate) - len(de_citit)} citite deja · {len(de_citit)} de citit')
    if not de_citit:
        return 0

    baza_url = a.url.rstrip('/')
    termen_total = time.time() + a.limita_min * 60 if a.limita_min else None
    stare = {'citite': 0, 'cu_suma': 0, 'erori': 0}

    def salveaza_daca():
        if stare['citite'] or stare['erori']:
            salveaza(baza)

    def citeste(descarca):
        """Bucla comună: descarcă(doc) → {'status', 'tip', 'octeti' | 'mare'}. Întoarce 0 sau 3."""
        for i, doc in enumerate(de_citit, 1):
            if termen_total and time.time() > termen_total:
                print(f'Limita de {a.limita_min:g} minute: continuă la rularea următoare.')
                return 0
            rez = descarca(f'{baza_url}/cautare/downloadpdf/{doc}')
            azi = datetime.date.today().isoformat()
            if rez.get('mare'):
                acte[doc] = {'act': toate.get(doc, ''), 'eroare': f"PDF prea mare ({rez['mare'] // 1048576} MB)", 'citit': azi}
                stare['erori'] += 1
                continue
            octeti = rez.get('octeti') or b''
            if not octeti.startswith(b'%PDF'):
                inceput = octeti[:3000].decode('utf-8', 'ignore')
                if BLOCAT.search(inceput) or rez.get('status') in (403, 503) and 'cloudflare' in inceput.lower():
                    print('Cloudflare a cerut verificarea; mă opresc și salvez ce am citit.')
                    return 3
                acte[doc] = {'act': toate.get(doc, ''), 'eroare': f"HTTP {rez.get('status')}, nu e PDF", 'citit': azi}
                stare['erori'] += 1
                continue
            try:
                text, pagini = text_din_pdf(octeti)
            except SystemExit:
                raise
            except Exception as e:
                acte[doc] = {'act': toate.get(doc, ''), 'eroare': 'PDF necitibil: ' + str(e)[:120], 'citit': azi}
                stare['erori'] += 1
                continue
            sume = sume_din_text(text)
            acte[doc] = {'act': toate.get(doc, ''), 'sume': sume, 'pagini': pagini, 'citit': azi}
            if not text.strip():
                acte[doc]['nota'] = 'PDF fără text (scanat)'
            stare['citite'] += 1
            stare['cu_suma'] += bool(sume)
            if i % 20 == 0:
                salveaza(baza)
                print(f"  {i}/{len(de_citit)} · cu sumă: {stare['cu_suma']} · erori: {stare['erori']}", flush=True)
            time.sleep(a.pauza)
        return 0

    if a.fara_browser:
        # Fără browser: o sesiune HTTP obișnuită. Merge doar dacă Cloudflare nu cere
        # verificarea pentru adresa de pe care rulăm; dacă o cere, codul 3 spune asta.
        import requests
        ses = requests.Session()
        ses.headers.update({'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                                          '(KHTML, like Gecko) Chrome/126.0 Safari/537.36',
                            'Accept-Language': 'ro-RO,ro;q=0.9,en;q=0.8'})
        try:
            r = ses.get(baza_url + '/', timeout=60)
            if BLOCAT.search(r.text[:5000]):
                print('Cloudflare cere verificarea pentru această adresă (fără browser nu trec).')
                return 3
        except Exception as e:
            print('legis.md nu răspunde:', e)
            return 1

        def descarca(url):
            for incercare in range(3):
                try:
                    r = ses.get(url, timeout=90)
                    return {'status': r.status_code, 'tip': r.headers.get('content-type', ''), 'octeti': r.content[:MAX_OCTETI + 1]}
                except Exception as e:
                    eroare = str(e)[:100]
                    time.sleep(5 * (incercare + 1))
            return {'status': 0, 'octeti': ('eroare de rețea: ' + eroare).encode()}
        try:
            cod = citeste(descarca)
        finally:
            salveaza_daca()
    else:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            opt = dict(headless=not a.headed, locale='ro-RO', viewport={'width': 1280, 'height': 900})
            if a.browser:
                opt['channel'] = a.browser
            if a.profil:
                ctx = p.chromium.launch_persistent_context(str(a.profil), **opt)
                page = ctx.pages[0] if ctx.pages else ctx.new_page()
                browser = None
            else:
                browser = p.chromium.launch(headless=not a.headed, **({'channel': a.browser} if a.browser else {}))
                ctx = browser.new_context(locale='ro-RO', viewport=opt['viewport'])
                page = ctx.new_page()
            try:
                page.goto(baza_url + '/', wait_until='domcontentloaded', timeout=90000)
                termen = time.time() + a.asteapta_cf
                while True:
                    try:
                        text = page.inner_text('body', timeout=10000)[:2000]
                    except Exception:
                        text = ''
                    if text and not BLOCAT.search(text):
                        break
                    if time.time() > termen:
                        print('Blocat de Cloudflare: bifa „nu sunt robot" nu a fost bifată la timp.')
                        return 3
                    page.wait_for_timeout(3000)

                def descarca(url):
                    rez = page.evaluate(JS_DESCARCA, url)
                    if rez.get('b64') is not None:
                        rez['octeti'] = base64.b64decode(rez.pop('b64'))
                    return rez
                cod = citeste(descarca)
            finally:
                salveaza_daca()
                ctx.close()
                if browser:
                    browser.close()
    citite, cu_suma, erori = stare['citite'], stare['cu_suma'], stare['erori']
    if cod == 3:
        return 3
    print(f'Gata: {citite} acte citite, {cu_suma} cu sumă, {erori} erori. Rezultatul: {IESIRE.relative_to(AICI)}')
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit(1)
