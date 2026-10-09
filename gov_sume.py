"""Sumele acordurilor din notele de argumentare ale Guvernului (gov.md).

Textul oficial al multor acorduri (legea de ratificare, hotărârea) nu spune suma:
LP97/2026 (iDRIP) scrie doar „Se ratifică Acordul … semnat la 14 mai 2026".
Suma e însă în nota de argumentare pe care ministerul o depune la ședința
Guvernului („Aspectul financiar", „Descrierea contractului"). gov.md publică
pentru fiecare ședință lista proiectelor, fiecare cu PDF-ul lui
(sites/default/files/media/documents/sedinte-de-guvern/AAAA-LL/NU-….pdf),
sub licența CC BY-SA 4.0. Ședința are loc ÎNAINTE ca hotărârea să apară în
Monitorul Oficial, deci un acord nou are suma din ziua în care Monitorul îl
înregistrează.

    python gov_sume.py                  # ședințele noi (zilnic, pe GitHub Actions)
    python gov_sume.py --limita-min 40  # se oprește după 40 de minute; continuă data viitoare
    python gov_sume.py --pagini 200     # merge înapoi prin lista ședințelor (prima rulare)

Rezultatul: date/gov_sume.json — pentru fiecare punct de pe ordinea de zi care
privește un acord de asistență externă: titlul, data ședinței, PDF-ul, finanțatorul,
instrumentul și sumele găsite, cu fragmentul din notă.

Are nevoie de:  pip install requests beautifulsoup4 pypdf
Coduri de ieșire: 0 = a mers, 1 = gov.md nu a răspuns.
"""
import argparse, datetime, json, re, sys, time
from pathlib import Path
from urllib.parse import urljoin

AICI = Path(__file__).resolve().parent
sys.path.insert(0, str(AICI))

BAZA = 'https://gov.md'
LISTA = BAZA + '/ro/sedinte-de-guvern'
IESIRE = AICI / 'date' / 'gov_sume.json'
AGENT = 'Mozilla/5.0 (compatible; acorduri-monitor; +https://nistor.vivi.md)'

LUNI = {'ianuarie': 1, 'februarie': 2, 'martie': 3, 'aprilie': 4, 'mai': 5, 'iunie': 6, 'iulie': 7,
        'august': 8, 'septembrie': 9, 'octombrie': 10, 'noiembrie': 11, 'decembrie': 12}
RX_SEDINTA = re.compile(r'/ro/sedinte-de-guvern/(sedinta-guvernului-din-(\d{1,2})-([a-z]+)-(\d{4})[\w-]*)')
RX_NUMAR = re.compile(r'\(\s*număr\s+unic\s+([^)]+?)\s*\)', re.I)
# modificările (scrisori de modificare, amendamente, addendumuri, protocoale) au în notă
# sumele modificării — nu suma acordului; le păstrăm, dar pagina nu le arată ca sumă
# O ședință se recitește cât timp e recentă. Ordinea de zi apare pe gov.md cu
# câteva zile înaintea ședinței și se completează până în ziua ei (și după, cu
# punctele suplimentare): ședința din 7 octombrie 2026 era deja citită pe 2
# octombrie, iar ce s-a adăugat între timp nu mai ajungea niciodată în fișier.
ZILE_RECITIRE = 10
# De câte ori reîncercăm un PDF care n-a putut fi descărcat, la rulări diferite.
MAX_INCERCARI_PDF = 5
RX_MODIFICARE = re.compile(r'\b(?:scriso\w+ de modificare|amendament\w*|addendum\w*|protocol\w* adi\w+|acordul\w* de modificare)\b', re.I)


def data_din_slug(zi, luna, an):
    try:
        return datetime.date(int(an), LUNI[luna], int(zi)).isoformat()
    except Exception:
        return ''


def curata_titlu(t):
    """„(HG-PL) – Proiect de hotărâre a Guvernului cu privire la … (număr unic 664/MIDR/2026) UE"
    → „Hotărâre cu privire la …" (forma din Monitorul Oficial)."""
    t = re.sub(r'\s+', ' ', t or '').strip()
    t = RX_NUMAR.sub('', t)
    t = re.sub(r'^\(\s*[A-Z-]+\s*\)\s*[-–—]?\s*', '', t)
    t = re.sub(r'\s+UE\s*$', '', t)
    t = re.sub(r'^Proiect(?:ul)? de hotărâre a Guvernului\s+', 'Hotărâre ', t, flags=re.I)
    t = re.sub(r'^Proiect(?:ul)? de lege\s+', 'Lege ', t, flags=re.I)
    return t.strip(' .')


def puncte_din_pagina(html, url_sedinta):
    """Punctele de pe ordinea de zi care au PDF: [(titlu, număr unic, url pdf)]."""
    from bs4 import BeautifulSoup
    supa = BeautifulSoup(html, 'html.parser')
    out, vazute = [], set()
    for a in supa.find_all('a', href=True):
        href = urljoin(url_sedinta, a['href'])
        if '/sedinte-de-guvern/' not in href or not href.lower().endswith('.pdf'):
            continue
        text = a.get_text(' ', strip=True)
        if not text or href in vazute:
            continue
        m = RX_NUMAR.search(text)
        if not m:                       # „Actele adoptate…", „Procesul-verbal…"
            continue
        vazute.add(href)
        out.append((text, m.group(1).strip(), href))
    return out


def sedinte_din_lista(html, baza=BAZA):
    """[(slug, data, url)] din pagina cu lista ședințelor."""
    out, vazute = [], set()
    for m in RX_SEDINTA.finditer(html):
        slug = m.group(1)
        if slug in vazute:
            continue
        vazute.add(slug)
        out.append((slug, data_din_slug(m.group(2), m.group(3), m.group(4)), baza + '/ro/sedinte-de-guvern/' + slug))
    return out


def e_recenta(data, azi=None):
    """Ședința e destul de nouă (sau încă în viitor) ca ordinea ei de zi să se mai schimbe?"""
    if not data:
        return False
    azi = azi or datetime.date.today()
    return data >= (azi - datetime.timedelta(days=ZILE_RECITIRE)).isoformat()


def citeste_nota(p, octeti, sume_din_text, text_din_pdf):
    """Pune în punctul p sumele din PDF-ul notei, sau eroarea. Întoarce True dacă PDF-ul a fost citit."""
    if not octeti or not octeti.startswith(b'%PDF'):
        p['eroare'] = 'PDF indisponibil'
        return False
    try:
        text, _ = text_din_pdf(octeti)
        p['sume'] = sume_din_text(text, maxim=3)
        p.pop('eroare', None)
        p.pop('incercari', None)
        return True
    except Exception as e:
        p['eroare'] = 'PDF necitibil: ' + str(e)[:100]
        return False


def incarca():
    try:
        return json.load(open(IESIRE, encoding='utf-8'))
    except Exception:
        return {'sedinte': {}, 'puncte': {}}


def salveaza(baza):
    IESIRE.parent.mkdir(exist_ok=True)
    baza['actualizat'] = datetime.datetime.now().strftime('%Y-%m-%d %H:%M')
    tmp = IESIRE.with_suffix('.tmp')
    json.dump(baza, open(tmp, 'w', encoding='utf-8'), ensure_ascii=False, indent=0, sort_keys=True)
    tmp.replace(IESIRE)


def main():
    ap = argparse.ArgumentParser(description='Sumele acordurilor din notele Guvernului (gov.md)')
    ap.add_argument('--pagini', type=int, default=400, help='câte pagini din lista ședințelor parcurg cel mult')
    ap.add_argument('--limita-min', type=float, default=0, help='oprește după atâtea minute (0 = fără limită)')
    ap.add_argument('--pauza', type=float, default=1.0, help='secunde între două cereri către gov.md')
    ap.add_argument('--url', default=LISTA, help=argparse.SUPPRESS)          # pentru teste
    a = ap.parse_args()

    import requests
    from legis_clasifica import clasifica, partener
    from legis_sume import sume_din_text, text_din_pdf

    ses = requests.Session()
    ses.headers.update({'User-Agent': AGENT, 'Accept-Language': 'ro-RO,ro;q=0.9'})
    termen = time.time() + a.limita_min * 60 if a.limita_min else None
    baza = incarca()
    sedinte, puncte = baza.setdefault('sedinte', {}), baza.setdefault('puncte', {})
    noi_sed = noi_pct = cu_suma = 0
    schimbat = False        # ceva de salvat și fără ședințe sau puncte noi
    lista_url = a.url
    # Până când istoricul e citit tot, fiecare rulare merge mai departe în trecut (ședințele
    # deja citite se sar); după aceea, rulările zilnice se opresc la prima pagină deja cunoscută.
    complet = bool(baza.get('istoric_complet'))
    precedenta = None

    def ia(url, binar=False):
        for incercare in range(3):
            try:
                r = ses.get(url, timeout=90)
                if r.status_code == 200:
                    return r.content if binar else r.text
                if r.status_code == 404:
                    return None
            except Exception:
                pass
            time.sleep(5 * (incercare + 1))
        return None

    # Categoria și partenerul punctelor deja citite se pun la zi cu regulile de azi: la o
    # schimbare a regulilor (ex. asistența financiară rambursabilă = împrumut) rămâneau
    # cele de la data citirii, iar pagina leagă nota de acord și după categorie.
    for p in puncte.values():
        cat, par = clasifica(p.get('titlu', '')), partener(p.get('titlu', ''))
        if cat and (cat != p.get('categorie') or par != p.get('partener')):
            p['categorie'], p['partener'] = cat, par
            schimbat = True

    try:
        # Notele care n-au putut fi descărcate la o rulare anterioară. Rămâneau
        # pentru totdeauna cu „PDF indisponibil": punctul era deja în fișier, iar
        # ședința lui deja citită, deci nimic nu le mai cerea a doua oară.
        for numar, p in list(puncte.items()):
            if p.get('eroare') != 'PDF indisponibil' or p.get('incercari', 1) >= MAX_INCERCARI_PDF or not p.get('pdf'):
                continue
            if termen and time.time() > termen:
                break
            time.sleep(a.pauza)
            if citeste_nota(p, ia(p['pdf'], binar=True), sume_din_text, text_din_pdf):
                cu_suma += bool(p.get('sume'))
                print(f'  nota {numar} a putut fi citită acum', flush=True)
            else:
                p['incercari'] = p.get('incercari', 1) + 1
            schimbat = True

        for pag in range(a.pagini):
            if termen and time.time() > termen:
                print(f'Limita de {a.limita_min:g} minute: continuă la rularea următoare.')
                break
            html = ia(lista_url + (f'?page={pag}' if pag else ''))
            if html is None:
                if pag == 0:
                    print('gov.md nu răspunde.')
                    return 1
                break
            lista = sedinte_din_lista(html, re.match(r'^https?://[^/]+', lista_url).group(0))
            if not lista or [s[0] for s in lista] == precedenta:
                if not baza.get('istoric_complet'):
                    baza['istoric_complet'] = True      # am ajuns la capătul listei
                    schimbat = True                     # se salvează și dacă rularea n-a găsit nimic nou
                break
            precedenta = [s[0] for s in lista]
            # ședințele necitite și cele recente, a căror ordine de zi se mai poate completa
            noi = [s for s in lista if s[0] not in sedinte or e_recenta(s[1])]
            for slug, data, url in noi:
                if termen and time.time() > termen:
                    break
                time.sleep(a.pauza)
                pagina = ia(url)
                if pagina is None:
                    continue
                n_acord = 0
                for titlu_brut, numar, pdf in puncte_din_pagina(pagina, url):
                    titlu = curata_titlu(titlu_brut)
                    cat = clasifica(titlu)
                    if not cat or numar in puncte:
                        continue
                    n_acord += 1
                    time.sleep(a.pauza)
                    octeti = ia(pdf, binar=True)
                    p = {'titlu': titlu, 'data': data, 'sedinta': url, 'pdf': pdf,
                         'categorie': cat, 'partener': partener(titlu)}
                    if RX_MODIFICARE.search(titlu):
                        p['modificare'] = True
                    if citeste_nota(p, octeti, sume_din_text, text_din_pdf):
                        cu_suma += bool(p['sume'])
                    puncte[numar] = p
                    noi_pct += 1
                if slug in sedinte:
                    # ședință recentă, recitită: numărăm doar ce s-a adăugat acum
                    if n_acord:
                        sedinte[slug]['acorduri'] = sedinte[slug].get('acorduri', 0) + n_acord
                    continue
                sedinte[slug] = {'data': data, 'acorduri': n_acord}
                noi_sed += 1
                if noi_sed % 10 == 0:
                    salveaza(baza)
                    print(f'  {noi_sed} ședințe noi · {noi_pct} puncte despre acorduri · {cu_suma} cu sumă', flush=True)
            if not noi and pag >= 1 and complet:
                break               # o pagină întreagă deja citită: restul sunt mai vechi și citite
    finally:
        if noi_sed or noi_pct or schimbat:
            salveaza(baza)
    print(f'Gata: {noi_sed} ședințe noi, {noi_pct} puncte despre acorduri, {cu_suma} cu sumă. '
          f'Total: {len(sedinte)} ședințe, {len(puncte)} puncte.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
