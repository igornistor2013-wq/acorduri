"""Sumele acordurilor, citite din DOCUMENTELE ATAȘATE la acte pe legis.md.

legis_sume.py citește textul actului (legea, hotărârea). Suma stă însă de cele
mai multe ori în acordul însuși, publicat ca PDF atașat la act
(legis.md/UserFiles/Image/…/acord 203 ro.pdf). Scriptul acesta:

  1. deschide fișa fiecărui act de acord din registru (legi, hotărâri, ordine —
     nu și decretele) și găsește PDF-urile atașate;
  2. le descarcă prin aceeași fereastră de browser care a trecut de Cloudflare;
  3. scoate textul; dacă PDF-ul e scanat (fără text), îl citește cu OCR;
  4. alege suma acordului și costul total al proiectului (suma_acord din
     legis_sume.py) și le scrie în date/legis_sume.json, la „atas".

    python legis_atasamente.py --headed --profil .legis_profil --browser msedge
    python legis_atasamente.py --limita-min 30      # se oprește după 30 de minute; continuă data viitoare
    python legis_atasamente.py --doar 132350 132354 # doar actele cu aceste doc_id
    python legis_atasamente.py --reincearca         # reia erorile și PDF-urile rămase fără text (după ce instalezi OCR)
    python legis_atasamente.py --tot                # recitește tot (sumele puse de mână rămân)
    python legis_atasamente.py --pdf acord.pdf --instrument imprumut   # un PDF de pe disc, fără legis.md

Un act deja parcurs nu se mai deschide. Sumele introduse de mână („manual": true)
și cele deja găsite nu se pierd. La sfârșit scrie sume_lipsa.csv: atașamentele
rămase fără sumă, cu motivul și, unde există, suma cea mai probabilă pe care
scriptul n-a fost destul de sigur ca s-o publice („candidat").

Are nevoie de:  pip install playwright pypdf
Pentru PDF-urile scanate (OCR), în plus:  pip install pypdfium2 pytesseract
  și programul Tesseract, cu limba română:
  https://github.com/UB-Mannheim/tesseract/wiki  (la instalare bifează „Romanian")
Fără OCR scriptul merge la fel, doar că PDF-urile scanate rămân marcate „fara-text".

Coduri de ieșire: 0 = a mers, 3 = blocat de Cloudflare, 1 = legis.md nu răspunde sau altă eroare.
"""
import argparse, base64, csv, datetime, html as _html, json, os, re, sys, time
from pathlib import Path
from urllib.parse import quote, unquote, urljoin, urlsplit, urlunsplit

AICI = Path(__file__).resolve().parent
sys.path.insert(0, str(AICI))
import legis_sume as ls

RAPORT = AICI / 'sume_lipsa.csv'
DEPANARE = AICI / 'legis_atasamente_debug.html'


# ------------------------------------------------------- linkurile atașamentelor

RX_ATRIBUT = re.compile(r'''(?:href|src|data)\s*=\s*(?:"([^"]+)"|'([^']+)')''', re.I)


def canon(u):
    """Adresa în forma din legis_sume.json: spațiile și diacriticele codate (%20, %C8%9B)."""
    p = urlsplit(u.strip())
    return urlunsplit((p.scheme, p.netloc, quote(unquote(p.path), safe="/()!*'~,;=+&$@:"), p.query, ''))


def cheie_url(u):
    """Aceeași adresă scrisă cu sau fără %20 e același fișier."""
    return unquote(u or '').strip()


def linkuri_din_html(pagina, baza):
    """PDF-urile atașate la act: orice href/src spre …/UserFiles/….pdf din pagină."""
    out, vazute = [], set()
    for m in RX_ATRIBUT.finditer(pagina or ''):
        u = _html.unescape((m.group(1) or m.group(2) or '').strip())
        if 'userfiles' not in u.lower() or not re.search(r'\.pdf(?:[?#].*)?$', u, re.I):
            continue
        a = canon(urljoin(baza, u))
        if cheie_url(a) not in vazute:
            vazute.add(cheie_url(a))
            out.append(a)
    return out


# ------------------------------------------------------------- textul PDF-ului

_OCR = None          # (pypdfium2, pytesseract, limbi) sau False
MOTIV_FARA_OCR = ''


def ocr_disponibil():
    """OCR-ul e opțional. Îl căutăm o singură dată și spunem de ce lipsește."""
    global _OCR, MOTIV_FARA_OCR
    if _OCR is not None:
        return _OCR
    try:
        import pypdfium2, pytesseract
    except ImportError as e:
        _OCR, MOTIV_FARA_OCR = False, 'lipsește biblioteca ' + (e.name or '') + ' (pip install pypdfium2 pytesseract)'
        return _OCR
    for cale in (r'C:\Program Files\Tesseract-OCR\tesseract.exe', r'C:\Program Files (x86)\Tesseract-OCR\tesseract.exe',
                 os.path.join(os.environ.get('LOCALAPPDATA', ''), 'Programs', 'Tesseract-OCR', 'tesseract.exe')):
        if cale and os.path.exists(cale):
            pytesseract.pytesseract.tesseract_cmd = cale
            break
    try:
        limbi = set(pytesseract.get_languages(config=''))
    except Exception:
        _OCR, MOTIV_FARA_OCR = False, 'programul Tesseract nu e instalat (vezi începutul fișierului)'
        return _OCR
    alese = '+'.join(l for l in ('ron', 'eng') if l in limbi) or 'eng'
    if 'ron' not in limbi:
        print('  ! Tesseract nu are limba română instalată: citesc cu „' + alese + '”, diacriticele pot ieși greșit.')
    _OCR = (pypdfium2, pytesseract, alese)
    return _OCR


def ocr_pdf(octeti, pagini_max):
    """Textul primelor pagini, citit cu OCR. None dacă OCR-ul nu e instalat."""
    unelte = ocr_disponibil()
    if not unelte:
        return None
    pypdfium2, pytesseract, limbi = unelte
    pdf = pypdfium2.PdfDocument(octeti)
    bucati = []
    try:
        for i in range(min(len(pdf), pagini_max)):
            imagine = pdf[i].render(scale=200 / 72).to_pil()
            bucati.append(pytesseract.image_to_string(imagine, lang=limbi))
    finally:
        pdf.close()
    t = '\n'.join(bucati)
    # OCR-ul rupe numerele: „17. 700. 000" → „17.700.000"
    return re.sub(r'(?<=\d)\s?([.,])\s(?=\d{3}(?!\d))', r'\1', t)


def text_atasament(octeti, ocr=True, pagini_ocr=25):
    """(text, pagini, metoda, caractere). metoda: 'text' = PDF-ul are text;
    'ocr' = scanat, citit cu OCR; 'fara-text' = scanat și OCR-ul lipsește."""
    try:
        text, pagini = ls.text_din_pdf(octeti)
    except SystemExit:
        raise
    except Exception:
        text, pagini = '', 0
    car = len(re.sub(r'\s+', '', text))
    if car >= max(200, 40 * min(pagini, 10)):
        return text, pagini, 'text', car
    if ocr:
        t2 = ocr_pdf(octeti, pagini_ocr)
        if t2 is not None:
            return text + '\n' + t2, pagini, 'ocr', len(re.sub(r'\s+', '', t2))
    return text, pagini, 'fara-text', car


def citeste_pdf(octeti, instrument, ocr=True, pagini_ocr=25):
    """Un atașament → {suma, cost, pagini, metoda[, candidat]}."""
    text, pagini, metoda, car = text_atasament(octeti, ocr, pagini_ocr)
    r = ls.suma_acord(text, instrument)
    out = {'suma': r['suma'], 'cost': r['cost'], 'pagini': pagini, 'metoda': metoda}
    if not r['suma'] and r.get('candidat'):
        out['candidat'] = r['candidat']
    return out


# ------------------------------------------------------------ unirea cu baza

def instrument(titlu):
    from legis_clasifica import clasifica
    return 'imprumut' if clasifica(titlu) == 'Împrumut' else 'grant'


def uneste(vechi, noi):
    """Atașamentele citite acum peste cele din bază. O sumă pusă de mână rămâne
    mereu; o sumă deja găsită nu e înlocuită de un rezultat fără sumă. Atașamentele
    din bază care nu mai apar în pagină se păstrează."""
    dupa = {cheie_url(x.get('u')): x for x in (vechi or [])}
    out, puse = [], set()
    for n in noi:
        k = cheie_url(n.get('u'))
        v = dupa.get(k)
        if v and v.get('suma') and (v['suma'].get('manual') or not n.get('suma')):
            n = v
        out.append(n)
        puse.add(k)
    for v in (vechi or []):
        if cheie_url(v.get('u')) not in puse:
            out.append(v)
    return out


def are_nevoie(r, reincearca=False, tot=False):
    """Actul trebuie (re)deschis?"""
    if r is None or r.get('eroare'):
        return False                      # încă necitit de legis_sume.py
    if tot or 'atas_citit' not in r:
        return True
    # „Niciun atașament" notat de o versiune care nu aștepta încărcarea fișei: fișa își
    # aduce conținutul după ce se deschide, deci răspunsul putea fi citit prea devreme.
    # Mai verificăm o dată; după o citire confirmată actul primește „fisa_ok" și nu se
    # mai redeschide. Aceeași regulă ca în legis_consola.js — altfel sutele de acte
    # marcate așa rămâneau neverificate pentru cine rulează doar legis_local.bat.
    if not (r.get('atas') or []) and not r.get('fisa_ok'):
        return True
    if any(not ls.suma_atas_tine(x, r.get('instr') or 'grant') for x in r.get('atas') or []):
        return True                       # o sumă veche nu mai rezistă regulilor de azi
    if reincearca:
        return bool(r.get('atas_eroare')) or any(
            x.get('eroare') or (x.get('metoda') == 'fara-text' and not x.get('suma')) for x in r.get('atas') or [])
    return False


def salveaza(baza):
    """În forma compactă în care e ținut fișierul (o singură linie) — o scrie legis_sume.py."""
    ls.salveaza(baza)


def raport(acte, toate):
    """sume_lipsa.csv: ce a rămas fără sumă și de ce."""
    randuri = []
    for d, cod in toate.items():
        r = acte.get(d)
        if not r or 'atas_citit' not in r:
            continue
        if not r.get('atas'):
            if not r.get('sume'):
                randuri.append([cod, d, '', r.get('atas_eroare') or 'niciun PDF atașat', '', '', '', '', ''])
            continue
        if any(x.get('suma') for x in r['atas']):
            continue
        for x in r['atas']:
            c = x.get('candidat') or {}
            randuri.append([cod, d, x.get('u', ''), x.get('eroare') or {
                'fara-text': 'PDF scanat, fără OCR', 'ocr': 'citit cu OCR, suma negăsită',
                'text': 'are text, suma negăsită'}.get(x.get('metoda'), 'citit de scriptul vechi'),
                x.get('pagini', ''), c.get('v', ''), c.get('val', ''), c.get('s', ''), c.get('f', '')])
    with open(RAPORT, 'w', encoding='utf-8-sig', newline='') as f:
        w = csv.writer(f, delimiter=';')
        w.writerow(['act', 'doc_id', 'atasament', 'motiv', 'pagini', 'candidat', 'valuta', 'scor', 'fragment'])
        w.writerows(randuri)
    return len(randuri)


# ------------------------------------------------------------------ browser

JS_PAGINA = """async (url) => {
  const c = new AbortController(), t = setTimeout(() => c.abort(), 60000);
  try {
    const r = await fetch(url, {cache: 'no-store', credentials: 'include', signal: c.signal});
    return {status: r.status, text: await r.text()};
  } finally { clearTimeout(t); }
}"""


def e_blocat(status, text):
    inceput = (text or '')[:5000]
    return bool(ls.BLOCAT.search(inceput)) or (status in (403, 503) and 'cloudflare' in inceput.lower())


class Blocat(Exception):
    pass


# Textul pe care fișa îl arată până își aduce conținutul.
RX_SE_INCARCA = re.compile(r'Con[țţt]inutul se [îi]ncarc[ăa]', re.I)
# După atâtea fișe la rând care nu se deschid, problema e legătura cu legis.md, nu actele.
MAX_FISE_ESUATE_LA_RAND = 5


def fisa_incarcata(text):
    """Fișa și-a adus conținutul? (are text destul și nu mai scrie „Conținutul se încarcă")"""
    t = (text or '').strip()
    return len(t) >= 300 and not RX_SE_INCARCA.search(t)


def main():
    ap = argparse.ArgumentParser(description='Sumele acordurilor din documentele atașate la acte pe legis.md')
    ap.add_argument('--headed', action='store_true', help='fereastră vizibilă (ca să poți bifa Cloudflare)')
    ap.add_argument('--profil', help='dosarul profilului de browser (păstrează cookie-ul Cloudflare)')
    ap.add_argument('--browser', help='canalul browserului instalat, ex. msedge')
    ap.add_argument('--asteapta-cf', type=int, default=300, help='câte secunde aștept trecerea de Cloudflare')
    ap.add_argument('--limita-min', type=float, default=0, help='oprește după atâtea minute (0 = fără limită)')
    ap.add_argument('--pauza', type=float, default=0.5, help='secunde între două cereri')
    ap.add_argument('--doar', nargs='*', help='doar aceste doc_id')
    ap.add_argument('--reincearca', action='store_true', help='reia erorile și PDF-urile scanate rămase fără text')
    ap.add_argument('--tot', action='store_true', help='recitește toate actele (sumele puse de mână rămân)')
    ap.add_argument('--fara-ocr', action='store_true', help='nu încerca OCR la PDF-urile scanate')
    ap.add_argument('--pagini-ocr', type=int, default=25, help='câte pagini citește OCR-ul dintr-un PDF scanat')
    ap.add_argument('--pdf', help='citește un PDF de pe disc și arată ce găsește (fără legis.md)')
    ap.add_argument('--instrument', choices=['imprumut', 'grant'], default='imprumut', help='pentru --pdf')
    ap.add_argument('--url', default='https://www.legis.md/', help=argparse.SUPPRESS)   # pentru teste
    a = ap.parse_args()

    if a.pdf:
        r = citeste_pdf(Path(a.pdf).read_bytes(), a.instrument, not a.fara_ocr, a.pagini_ocr)
        if r['metoda'] == 'fara-text' and not a.fara_ocr:
            print('PDF scanat, iar OCR-ul nu e disponibil:', MOTIV_FARA_OCR)
        print(json.dumps(r, ensure_ascii=False, indent=1))
        return 0

    brut = json.load(open(AICI / 'legis_brut.json', encoding='utf-8'))
    toate = ls.tinte(brut)
    titluri = {str(r['id']): r.get('t', '') for r in brut}
    baza = ls.incarca()
    acte = baza.setdefault('acte', {})

    if a.doar:
        de_citit = [d for d in a.doar if d in acte and not acte[d].get('eroare')]
        lipsa = [d for d in a.doar if d not in de_citit]
        if lipsa:
            print('Sar peste', ', '.join(lipsa), '— nu sunt încă în date/legis_sume.json (rulează întâi legis_sume.py).')
    else:
        de_citit = [d for d in toate if are_nevoie(acte.get(d), a.reincearca, a.tot)]
    de_citit.sort(key=lambda d: -int(d) if d.isdigit() else 0)
    necitite = sum(1 for d in toate if d not in acte)
    print(f'{len(toate)} acte de acord în registru · {len(de_citit)} de deschis acum'
          + (f' · {necitite} încă necitite de legis_sume.py (rulează-l întâi)' if necitite else ''))
    if not a.fara_ocr and not ocr_disponibil():
        print('OCR indisponibil:', MOTIV_FARA_OCR + '. PDF-urile scanate vor rămâne marcate „fara-text”.')
    if not de_citit:
        print('Rămase fără sumă:', raport(acte, toate), 'rânduri în', RAPORT.name)
        return 0

    baza_url = a.url.rstrip('/')
    fisa = lambda d: f'{baza_url}/cautare/getResults?doc_id={d}&lang=ro'
    termen_total = time.time() + a.limita_min * 60 if a.limita_min else None
    azi = datetime.date.today().isoformat()
    stare = {'acte': 0, 'pdf': 0, 'sume': 0, 'ocr': 0, 'fara_text': 0, 'erori': 0, 'candidati': 0}
    oprit_retea = False

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

        def asteapta_cloudflare():
            termen = time.time() + a.asteapta_cf
            while True:
                try:
                    text = page.inner_text('body', timeout=10000)[:2000]
                except Exception:
                    text = ''
                if text and not ls.BLOCAT.search(text):
                    return True
                if time.time() > termen:
                    return False
                page.wait_for_timeout(3000)

        def linkuri_fetch(d):
            try:
                r = page.evaluate(JS_PAGINA, fisa(d))
            except Exception as e:
                # cererea a eșuat (rețea, termen depășit): actul rămâne de deschis data viitoare
                return 0, [], 'cerere eșuată: ' + str(e).split('\n')[0][:100]
            if e_blocat(r.get('status'), r.get('text')):
                raise Blocat()
            return r.get('status'), linkuri_din_html(r.get('text') or '', fisa(d)), r.get('text') or ''

        def linkuri_navigare(d):
            try:
                page.goto(fisa(d), wait_until='domcontentloaded', timeout=90000)
            except Exception as e:
                return 0, [], 'fișa nu s-a deschis: ' + str(e).split('\n')[0][:100]
            # Fișa își aduce conținutul după ce se deschide. Așteptăm până dispare
            # „Conținutul se încarcă" și pagina nu se mai schimbă, cel mult 30 de secunde.
            termen, ultim, stabil, continut, text = time.time() + 30, -1, 0, '', ''
            while True:
                continut = ''
                for cadru in page.frames:
                    try:
                        continut += cadru.content()
                    except Exception:
                        pass
                try:
                    text = page.inner_text('body', timeout=5000)
                except Exception:
                    text = ''
                if e_blocat(200, text[:5000]):
                    raise Blocat()
                if fisa_incarcata(text):
                    stabil = stabil + 1 if len(continut) == ultim else 0
                    ultim = len(continut)
                    if stabil >= 2:
                        return 200, linkuri_din_html(continut, fisa(d)), continut
                if time.time() > termen:
                    return 0, [], 'fișa nu și-a încărcat conținutul în 30 de secunde'
                page.wait_for_timeout(600)

        try:
            page.goto(baza_url + '/', wait_until='domcontentloaded', timeout=90000)
            if not asteapta_cloudflare():
                print('Blocat de Cloudflare: bifa „nu sunt robot" nu a fost bifată la timp.')
                return 3

            # Cum se găsesc atașamentele: încercăm pe un act la care le știm deja.
            # Dacă pagina primită prin fetch nu le conține (conținutul e adus de
            # scripturile paginii), trecem pe deschiderea fișei în fereastră.
            gaseste = linkuri_fetch
            cunoscute = sorted((d for d, r in acte.items() if any(x.get('u') for x in r.get('atas') or [])),
                               key=lambda d: -int(d) if d.isdigit() else 0)[:3]
            if cunoscute:
                def nimereste(fn):
                    for d in cunoscute:
                        stiute = {cheie_url(x['u']) for x in acte[d]['atas'] if x.get('u')}
                        _, gasite, continut = fn(d)
                        if stiute & {cheie_url(u) for u in gasite}:
                            return True, ''
                    return False, continut
                ok, _ = nimereste(linkuri_fetch)
                if not ok:
                    ok, continut = nimereste(linkuri_navigare)
                    if not ok:
                        DEPANARE.write_text(continut, encoding='utf-8')
                        print('Nu găsesc în fișa actului atașamentele pe care le știu deja (' + acte[cunoscute[-1]]['act'] +
                              '). Pagina legis.md arată altfel decât se aștepta scriptul.\nAm salvat pagina în ' +
                              DEPANARE.name + ' — trimite-mi fișierul și adaptez căutarea.')
                        return 1
                    gaseste = linkuri_navigare
                    print('Atașamentele apar doar în pagina deschisă în fereastră; lucrez așa (ceva mai încet).')

            fise_esuate = 0
            for i, d in enumerate(de_citit, 1):
                if termen_total and time.time() > termen_total:
                    print(f'Limita de {a.limita_min:g} minute: continuă la rularea următoare.')
                    break
                r = acte[d]
                status, linkuri, continut = gaseste(d)
                if status == 200 and not linkuri and gaseste is linkuri_fetch and RX_SE_INCARCA.search(continut or ''):
                    # răspunsul simplu a venit înainte de conținut: deschidem fișa în fereastră și așteptăm
                    status, linkuri, continut = linkuri_navigare(d)
                if status != 200:
                    r['atas_eroare'] = f'fișa actului: HTTP {status}' if status else 'fișa actului: ' + (continut or 'nu s-a deschis')[:120]
                    stare['erori'] += 1
                    fise_esuate += 1
                    if fise_esuate >= MAX_FISE_ESUATE_LA_RAND:
                        print(f'legis.md nu răspunde: {fise_esuate} fișe la rând nu s-au deschis. '
                              'Mă opresc și salvez ce am citit; actele acestea se reiau data viitoare.')
                        oprit_retea = True
                        break
                    continue
                fise_esuate = 0
                r.pop('atas_eroare', None)
                r['fisa_ok'] = 1                            # conținutul fișei a fost citit cu adevărat
                instr = r.get('instr') or instrument(titluri.get(d, ''))
                for x in r.get('atas') or []:           # suma veche care nu mai rezistă regulilor: o recitim
                    if not ls.suma_atas_tine(x, instr):
                        x['suma'] = None
                        x.pop('metoda', None)
                vechi = {cheie_url(x.get('u')): x for x in r.get('atas') or []}
                noi = []
                for u in linkuri:
                    v = vechi.get(cheie_url(u))
                    if v and v.get('suma') and not a.tot:
                        noi.append(v)                       # are deja suma: nu-l mai descărcăm
                        continue
                    if v and v.get('metoda') and not a.tot and not (a.reincearca and v['metoda'] == 'fara-text'):
                        noi.append(v)                       # citit deja de acest script
                        continue
                    try:
                        rez = page.evaluate(ls.JS_DESCARCA, u)
                    except Exception as e:
                        # o descărcare eșuată nu mai oprește tot: se notează la atașament
                        # și se reia cu --reincearca
                        rez = {'esec': str(e).split('\n')[0][:100]}
                    x = {'u': u, 'suma': None, 'cost': None, 'citit': azi, 'v': ls.REGULI}
                    if rez.get('esec'):
                        x['eroare'] = ls.ESEC_DESCARCARE + ': ' + rez['esec']
                    elif rez.get('mare'):
                        x['eroare'] = f"PDF prea mare ({rez['mare'] // 1048576} MB)"
                    else:
                        octeti = base64.b64decode(rez.get('b64') or '')
                        if not octeti.startswith(b'%PDF'):
                            if e_blocat(rez.get('status'), octeti[:5000].decode('utf-8', 'ignore')):
                                raise Blocat()
                            x['eroare'] = f"HTTP {rez.get('status')}, nu e PDF"
                        else:
                            try:
                                x.update(citeste_pdf(octeti, instr, not a.fara_ocr, a.pagini_ocr))
                            except SystemExit:
                                raise
                            except Exception as e:
                                x['eroare'] = 'PDF necitibil: ' + str(e)[:120]
                    stare['pdf'] += 1
                    stare['erori'] += bool(x.get('eroare'))
                    stare['sume'] += bool(x.get('suma'))
                    stare['ocr'] += x.get('metoda') == 'ocr'
                    stare['fara_text'] += x.get('metoda') == 'fara-text'
                    stare['candidati'] += bool(x.get('candidat'))
                    noi.append(x)
                    time.sleep(a.pauza)
                r['atas'] = uneste(r.get('atas'), noi)
                r['instr'] = instr
                r['atas_citit'] = azi
                stare['acte'] += 1
                if i % 10 == 0:
                    salveaza(baza)
                    print(f"  {i}/{len(de_citit)} · PDF-uri citite: {stare['pdf']} · cu sumă: {stare['sume']} "
                          f"(din care OCR: {stare['ocr']}) · scanate necitite: {stare['fara_text']} · erori: {stare['erori']}", flush=True)
                time.sleep(a.pauza)
        except Blocat:
            print('Cloudflare a cerut verificarea; mă opresc și salvez ce am citit.')
            salveaza(baza)
            return 3
        finally:
            if stare['acte'] or stare['erori']:
                salveaza(baza)
            ctx.close()
            if browser:
                browser.close()

    n = raport(acte, toate)
    if oprit_retea:
        return 1
    print(f"Gata: {stare['acte']} acte deschise, {stare['pdf']} PDF-uri citite, {stare['sume']} cu sumă găsită "
          f"({stare['ocr']} citite cu OCR), {stare['fara_text']} scanate rămase necitite, {stare['erori']} erori.")
    print(f"De verificat de mână: {n} rânduri în {RAPORT.name} ({stare['candidati']} cu o sumă-candidat).")
    print('Acum rulează:  python legis_pagina.py   (pune sumele în pagină)')
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit(1)
