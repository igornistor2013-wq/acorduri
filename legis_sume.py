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
    (r'drepturi\s+speciale\s+de\s+tragere|d\.\s?s\.\s?t\.?|dst\b|dts\b|sdr\b|xdr\b', 'DST'),
    (r'yeni(?:\s+japonezi)?|yen\b|jpy\b', 'JPY'),
    (r'franci\s+elve\S{0,2}ieni|chf\b', 'CHF'),
    (r'lire\s+sterline|gbp\b', 'GBP'),
    (r'coroane\s+suedeze|sek\b', 'SEK'),
    (r'coroane\s+daneze|dkk\b', 'DKK'),
    (r'zloti|pln\b', 'PLN'),
    (r'yuani|cny\b|rmb\b', 'CNY'),
    (r'ecu\b', 'ECU'),
    (r'm[aă]rci\s+germane|dem\b', 'DEM'),
    (r'lei\s+rom\S{0,4}ne\S{0,2}ti', 'ROL'),
    (r'lei(?:\s+moldovenesti)?|mdl\b', 'MDL'),
]
_VAL = '|'.join('(?:%s)' % p for p, _ in VALUTE)
_NUM = r'\d{1,3}(?:[ .,]\d{3})+(?:[.,]\d{1,2})?|\d+(?:[.,]\d+)?'
# „million" stă înaintea lui „mil": altfel „1,500 million" era prins drept „mil" românesc
_MULT = r'miliarde|miliard|milioane|milion|millions?|billions?|mil\.?|mln\.?|mii'
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
    if re.search(r'[ .,]', s):
        return 0.0      # „35.700.00": număr rupt în PDF; mai bine fără sumă decât cu una greșită
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

    # aceiași candidați ca la suma acordului: fără conturi bancare, fără numere rupte,
    # cu „3,075 milioane" citit drept 3,075 mil. („25.000.000 mil. EUR", greșeală de
    # tipar, rămâne 25 de milioane)
    for start, end, v, cod in _candidati(t):
        adauga(start, end, v, cod)

    rez = sorted(gasite.values(), key=lambda x: (-x['s'], x['poz']))[:maxim]
    for r in rez:
        r.pop('poz', None)
        if r['v'] == int(r['v']):
            r['v'] = int(r['v'])
    return rez


# ------------------------------------------------- suma ACORDULUI din textul lui

# Textul unui acord (documentul atașat la lege) are multe sume. La „Moldova Solidarity
# Lanes" (LP295/2024): 41.205.000 EUR = împrumutul din ALT acord (considerentul A),
# 12.000.000 EUR = grantul din acest acord (D), 12.400.000 = grant + comisioanele
# băncii, 119.000.000 EUR = costul total al proiectului (art. 4.1), 5.000.000 EUR =
# o limită pentru tranșe (art. 7.3). Prima sumă din text ar fi fost greșită. Alegem
# suma care ține de ACEST acord și de instrumentul lui, iar costul total al
# proiectului îl păstrăm separat.
_GRANT = r'grant|subventi|nerambursabil|contributi|donati|ajutor'
_IMPR = r'imprumut|credit|loan|lend|facilitat'
_COST = (r'cost(?:ul|urile)?\s+(?:total|totale|estimat|final)|total(?:\s+project)?\s+cost|estimated\s+(?:total\s+)?cost|'
         r'valoarea\s+totala\s+a\s+proiectului|bugetul\s+(?:total\s+)?(?:al\s+)?proiectului|'
         # bugetul unui program întreg (Interreg), pentru toate țările: e cost, nu suma acordului
         r'buget\w{0,2}\s+total\s+al\s+programului|total\s+budget\s+of\s+the\s+programme|fonduri(?:lor)?\s+interreg|alocar\w+\s+financiar\w+\s+total\w+\s+a\s+ue\s+pentru\s+program|out\s+of\s+the')
_PROPRIU = r'prezent(?:ul|ului)\s+(?:acord|contract)|acest(?:ui)?\s+acord|this\s+agreement|hereunder|hereby'
_EXPLICIT = r'reprezentat[aă]?\s+de\s+prezentul\s+acord|valoarea\s+grantului|suma\s+(?:grantului|imprumutului|creditului)|amount\s+of\s+the\s+(?:grant|loan|credit)'
_MAXIM = (r'valoare(?:a)?\s+(?:principala\s+)?maxima|suma\s+maxima|maximum\s+amount|pana\s+la|up\s+to|not\s+exceeding|not\s+to\s+exceed|sa\s+nu\s+depaseasca|ce\s+nu\s+depaseste|'
          r'in\s+valoare(?:\s+totala)?\s+de|in\s+suma\s+de|amount\s+of|in\s+cuantum\s+de|in\s+marime\s+de')
_DEFINITIE = r'valoarea\s+maxima\s+a\s+(?:grantului|subventiei|imprumutului|creditului)'
# „transa" lipsea: „Tranșa 1, în valoare de până la 90.000.000 EUR" trecea drept suma întreagă
_LIMITA = r'nu\s+va\s+depasi\s+cu\s+mai\s+mult|tran\w{0,2}(?:a|e|ei|elor)\b|trans\b|tranche|instal?l?ments?|first\s+transfer|prefinant|pre-?financ|cumulat'
_COMISION = r'comision|\bfees?\b'
_ALT_ACORD = (r'in\s+temeiul\s+unui\s+contract|contract(?:ul)?\s+de\s+finantare\s+din\s+data\s+de|finance\s+contract\s+dated|'
              # trimitere la celălalt acord al aceluiași proiect: („Acord de împrumut") din data semnării
              r'acord(?:ul)?\s+de\s+(?:imprumut|finantare|grant)\W{0,8}din\s+data|(?:loan|financing|grant)\s+agreement\W{0,8}(?:of\s+(?:even|the\s+same)\s+date|dated)')
# Greșeli văzute în sumele publicate: o cotă dintr-o sumă mai mare („7 526 403 din
# 77 290 439", „15 % din împrumut (adică până la 18 milioane)"), cofinanțarea altcuiva,
# un plafon de achiziții, un cont bancar.
_PARTE_DUPA = r'^\W{0,3}(?:out\s+of|to\s+each|pentru\s+fiecare|fiecar(?:ui|ei)|din\s+(?:contributia|totalul|imprumutul|credit|grant|cei|cele))'
_PARTE_INAINTE = r'\d\s*%\s+(?:din|of)\b|adica\s+pana\s+la|approximately|aproximativ'
_COFIN = r'contributi[ae]\s+national|cofinanta|co-?financ|contributi[ae]\s+proprie'
_ACHIZ = r'procurement|achiziti'
_CONT = r'cont(?:ul)?\s+bancar|\biban\b|\bswift\b|\bbic\b|bank\s+account'


def _fold_ocr(s):
    # OCR-ul pune „T" în loc de „î" la început de cuvânt: „Tn" = „în", „Tmprumut" = „împrumut"
    return re.sub(r'\bt(?=[mn])', 'i', _fara_diacritice(s))


_MULT_RO = ('miliarde', 'miliard', 'milioane', 'milion', 'mil', 'mil.', 'mln', 'mln.')


def _valoare(cifre, mult):
    v = numar(cifre)
    # „3,075 milioane dolari" înseamnă 3,075 mil. (virgula e zecimală în română), nu
    # 3 075 mil.: așa apăreau în registru împrumuturi de 3 și 4,7 miliarde de dolari.
    if mult in _MULT_RO and re.fullmatch(r'\d{1,3},\d{3}', cifre.strip()):
        v = float(cifre.strip().replace(',', '.'))
    if mult and v < 1e5:
        v *= MULT.get(mult, 1)
    return v


def _candidati(t):
    # Un cont bancar nu e o sumă: „MD04VI022240300000368EUR" a fost citit drept
    # 22 240 300 000 368 EUR. Sărim cifrele lipite de o literă și valorile imposibile.
    for m in RX_DUPA.finditer(t):
        if m.start() and t[m.start() - 1].isalpha():
            continue
        mult = (m.group(2) or '').lower()
        v = _valoare(m.group(1), mult)
        if v >= 1e12:
            continue
        yield m.start(), m.end(), v, valuta(m.group(3))
    for m in RX_INAINTE.finditer(t):
        mult = (m.group(3) or '').lower()
        v = _valoare(m.group(2), mult)
        if v >= 1e12:
            continue
        sym = m.group(1).lower()
        yield m.start(), m.end(), v, {'€': 'EUR', '$': 'USD', 'sdr': 'DST', 'xdr': 'DST'}.get(sym, sym.upper())


def _propozitie(t, start, end):
    """Propoziția în care stă suma: nu tăiem la punctele din numere („119.000.000")."""
    inainte = t[max(0, start - 260):start]
    m = None
    for m in re.finditer(r'(?<!\d)[.;]\s+(?=[A-ZĂÂÎȘȚ„"(])|\n\s*[A-Z]\.\s|\b\d{1,2}\.\d{1,2}\.\s', inainte):
        pass
    if m:
        inainte = inainte[m.end():]
    dupa = t[end:end + 200]
    m2 = re.search(r'(?<!\d)\.\s+(?=[A-ZĂÂÎȘȚ])|\n\s*[A-Z]\.\s|\b\d{1,2}\.\d{1,2}\.\s', dupa)
    if m2:
        dupa = dupa[:m2.start()]
    return inainte, dupa


def suma_acord(text, instrument):
    """Suma acordului și costul total al proiectului, din textul acordului.
    instrument: 'grant' sau 'imprumut' (din categoria acordului).
    Întoarce {'suma': {v, val, f, s} | None, 'cost': {v, val, f} | None}."""
    t = re.sub(r'-\s*\n\s*', '', text or '')
    t = re.sub(r'[ \t]+', ' ', t)
    propriu_rx = _GRANT if instrument == 'grant' else _IMPR
    altul_rx = _IMPR if instrument == 'grant' else _GRANT
    sume, costuri = {}, {}
    for start, end, v, cod in _candidati(t):
        if not cod or v < 1000 or cod == 'MDL':
            continue
        inainte, dupa = _propozitie(t, start, end)
        fi, fd = _fold_ocr(inainte), _fold_ocr(dupa)
        prop = fi + ' ' + fd
        frag = re.sub(r'\s+', ' ', (inainte[-150:] + t[start:end] + dupa[:70])).strip()
        if re.search(_COMISION, fd[:70]) or re.search(_COMISION, fi[-50:]):
            continue                                            # suma e chiar un comision
        if re.search(_CONT, fi[-80:]):
            continue                                            # număr de cont, nu sumă
        if re.search(_PARTE_DUPA, fd[:45]):
            continue                                            # o cotă: „X out of the Y", „X to each School"
        if re.search(_COST, fi[-140:]):
            k = (v, cod)
            if k not in costuri:
                costuri[k] = {'v': v, 'val': cod, 'f': frag[:230], 'poz': start}
            continue
        s = 0
        s += 4 if re.search(_PROPRIU, prop) else 0
        are_propriu, are_altul = bool(re.search(propriu_rx, prop)), bool(re.search(altul_rx, prop))
        s += 4 if are_propriu else 0
        s -= 4 if (are_altul and not are_propriu) else 0
        s += 3 if re.search(_MAXIM, fi[-90:]) else 0
        s += 3 if re.search(_DEFINITIE, fi[-140:]) else 0
        s += 2 if re.search(_EXPLICIT, prop) else 0
        transa = bool(re.search(_LIMITA, fi[-130:]))
        s -= 3 if transa else 0
        s -= 3 if re.search(_COMISION, prop) else 0
        s -= 3 if re.search(_ALT_ACORD, prop) else 0
        s -= 4 if re.search(_PARTE_INAINTE, fi[-60:]) else 0
        s -= 4 if re.search(_COFIN, fi[-120:]) else 0
        s -= 4 if re.search(_ACHIZ, prop) else 0
        s += 1 if v >= 1e6 else 0
        k = (v, cod)
        if k not in sume or sume[k]['s'] < s:
            sume[k] = {'v': v, 'val': cod, 'f': frag[:230], 's': s, 'poz': start, 'tr': transa}
    # Totalul și tranșele lui: când lângă două sume stă și suma lor („până la 150.000.000 EUR,
    # constând în Tranșa 1 de 90.000.000 și Tranșa 2 de 60.000.000"), acordul e totalul. Doar
    # pentru tranșe: la „12 400 000 din care (i) 12 000 000 și (ii) 400 000" părțile sunt
    # lucruri diferite și una dintre ele poate fi chiar suma acordului.
    dupa = {(round(x['v'], 2), x['val']): x for x in sume.values()}
    totaluri, parti = set(), set()
    for a in sume.values():
        for b in sume.values():
            if b['val'] != a['val'] or b['v'] <= a['v'] or not (a['tr'] or b['tr']):
                continue
            t = dupa.get((round(a['v'] + b['v'], 2), a['val']))
            if t and max(a['poz'], b['poz'], t['poz']) - min(a['poz'], b['poz'], t['poz']) <= 1500:
                totaluri.add(id(t)); parti.add(id(a)); parti.add(id(b))
    for x in sume.values():
        if id(x) in totaluri and id(x) not in parti:
            x['s'] += 3
        elif id(x) in parti:
            x['s'] -= 4
    alese = sorted(sume.values(), key=lambda x: (-x['s'], x['poz']))
    for x in alese:
        x.pop('tr', None)
    # un acord sub 10 000 nu există în registru: o asemenea sumă e un plafon sau o taxă
    suma = alese[0] if alese and alese[0]['s'] >= 6 and alese[0]['v'] >= 10000 else None
    # Sub prag nu publicăm nimic, dar cea mai probabilă sumă rămâne la vedere
    # („candidat"), ca omul care verifică să nu pornească de la zero.
    candidat = alese[0] if alese and not suma and alese[0]['s'] >= 3 else None
    cost = sorted(costuri.values(), key=lambda x: (-x['v'], x['poz']))[0] if costuri else None
    for x in (suma, cost, candidat):
        if x:
            x.pop('poz', None)
            if x['v'] == int(x['v']):
                x['v'] = int(x['v'])
    return {'suma': suma, 'cost': cost, 'candidat': candidat}


# ------------------------------------------- sumele vechi, la regulile de azi

REGULI = 3      # crește când se schimbă regulile de alegere a sumei


def sume_tin(r):
    """Suma din textul actului, ținută în bază, mai rezistă regulilor de azi?
    O reverificăm pe fragmentul păstrat lângă ea; dacă nu mai iese aceeași sumă
    (un „3,075 milioane" citit drept 3 miliarde, lei românești trecuți drept lei
    moldovenești), actul se recitește."""
    if r.get('v') == REGULI or not r.get('sume'):
        return True
    s = r['sume'][0]
    top = sume_din_text(s.get('f', ''))
    return bool(top) and top[0]['v'] == s['v'] and top[0]['val'] == s['val']


def suma_atas_tine(x, instrument):
    """La fel pentru suma citită dintr-un acord atașat. Cele puse de mână rămân."""
    s = x.get('suma')
    if not s or s.get('manual') or x.get('v') == REGULI:
        return True
    n = suma_acord(s.get('f', ''), instrument)['suma']
    return bool(n) and n['v'] == s['v'] and n['val'] == s['val']


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
        de_citit = [d for d in toate if d not in acte or (a.reincearca and acte[d].get('eroare'))
                    or not sume_tin(acte[d])]
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

    def pune(doc, nou):
        """Scrie actul recitit fără să piardă ce s-a citit din atașamentele lui; o
        eroare la recitire nu șterge un act citit bine înainte."""
        vechi = acte.get(doc) or {}
        if nou.get('eroare') and vechi and not vechi.get('eroare'):
            return
        for k in ('atas', 'instr', 'atas_citit', 'atas_eroare'):
            if k in vechi:
                nou[k] = vechi[k]
        acte[doc] = nou

    def citeste(descarca):
        """Bucla comună: descarcă(doc) → {'status', 'tip', 'octeti' | 'mare'}. Întoarce 0 sau 3."""
        for i, doc in enumerate(de_citit, 1):
            if termen_total and time.time() > termen_total:
                print(f'Limita de {a.limita_min:g} minute: continuă la rularea următoare.')
                return 0
            rez = descarca(f'{baza_url}/cautare/downloadpdf/{doc}')
            azi = datetime.date.today().isoformat()
            if rez.get('mare'):
                pune(doc, {'act': toate.get(doc, ''), 'eroare': f"PDF prea mare ({rez['mare'] // 1048576} MB)", 'citit': azi})
                stare['erori'] += 1
                continue
            octeti = rez.get('octeti') or b''
            if not octeti.startswith(b'%PDF'):
                inceput = octeti[:3000].decode('utf-8', 'ignore')
                if BLOCAT.search(inceput) or rez.get('status') in (403, 503) and 'cloudflare' in inceput.lower():
                    print('Cloudflare a cerut verificarea; mă opresc și salvez ce am citit.')
                    return 3
                pune(doc, {'act': toate.get(doc, ''), 'eroare': f"HTTP {rez.get('status')}, nu e PDF", 'citit': azi})
                stare['erori'] += 1
                continue
            try:
                text, pagini = text_din_pdf(octeti)
            except SystemExit:
                raise
            except Exception as e:
                pune(doc, {'act': toate.get(doc, ''), 'eroare': 'PDF necitibil: ' + str(e)[:120], 'citit': azi})
                stare['erori'] += 1
                continue
            sume = sume_din_text(text)
            pune(doc, {'act': toate.get(doc, ''), 'sume': sume, 'pagini': pagini, 'citit': azi, 'v': REGULI})
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
