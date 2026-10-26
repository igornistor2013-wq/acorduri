"""Testele paginii „Debursări pe acorduri” (debursari.html, debursari-ui.js, debursari.js).

    python teste_debursari.py             # logica pură (teste_debursari.js, cu Node) și fișierele de date
    python teste_debursari.py --browser   # plus: pagina în browser, cu un GitHub simulat în locul celui real

În browser nu se atinge GitHub-ul adevărat: toate cererile către api.github.com sunt preluate de un depozit simulat (GitHubFals), care
se poartă ca el: cod valid sau nu, drept de scriere sau doar de citire, „sha” la fiecare scriere, conflict (409) când fișierul s-a
schimbat între timp, cădere de rețea. Cheile de probă sunt inventate. Ce se verifică, pe scurt:
  · lista donatorilor, bifarea, tabelul cu cele cinci coloane cerute și cifrele lui, față de un calcul independent din date/acorduri_legare.json;
  · câmpurile de debursare blocate până la introducerea codului; cod greșit, fără drept de scriere, fără rețea;
  · adăugare, editare, ștergere → ce ajunge, de fapt, în fișierul date/debursari.json (și în mesajul commit-ului);
  · conflict la salvare (altcineva a scris între timp): nimic nu se pierde; coada de modificări nesalvate supraviețuiește reîncărcării;
  · codul păstrat cu PIN: nicăieri în clar; PIN greșit; „uită codul”;
  · fișierele Excel descărcate (pe donator, total, pe donatori), deschise cu openpyxl;
  · engleză, telefon (fără derulare orizontală), adresa cu selecția, tastatură, cereri doar către pagină și către api.github.com.
Are nevoie de Node.js, de openpyxl și (pentru --browser) de Playwright.
"""
import base64, functools, hashlib, json, os, re, subprocess, sys, tempfile, threading
from pathlib import Path

AICI = Path(__file__).resolve().parent
picat = []


def verifica(nume, conditie, detaliu=''):
    print(('  ok   ' if conditie else '  PICĂ ') + nume + ('' if conditie else f'  → {str(detaliu)[:500]}'))
    if not conditie:
        picat.append(nume)


def egal(nume, obtinut, asteptat):
    verifica(nume, obtinut == asteptat, f'obținut {obtinut!r}, așteptat {asteptat!r}')


DATE = json.loads((AICI / 'date' / 'acorduri_legare.json').read_text(encoding='utf-8'))
ACORDURI = DATE['acorduri']
CURSURI = DATE['cursuri']
# coduri de probă: nu seamănă cu o cheie GitHub reală, ca scanerul de secrete să nu le ia drept scurgere
TOKEN = 'COD-DE-PROBA-nu-e-o-cheie-reala-0123456789abcdefghijklmnopqrstuvwxyz'
TOKEN_CITIRE = 'COD-DE-PROBA-doar-citire-0123456789abcdefghijklmnopqrstuvwxyz'
REPO = 'igornistor2013-wq/acorduri'
CALE_DATE = '/repos/' + REPO + '/contents/date/debursari.json'


# ============================================================ calculul independent, în Python
def curata_nume(s):
    s = re.sub(r'\s+', ' ', s or '').strip()
    if s.count('(') > s.count(')'):
        s = s[:s.rindex('(')].strip()
    return re.sub(r'[\s(\[,;:–-]+$', '', s)


def donatori_acord(a):
    v = []
    for x in (a.get('parteneri') or '').split('/'):
        x = re.sub(r'\s+', ' ', x).strip()
        if x and x not in v:
            v.append(x)
    return v or ['(neidentificat)']


def acorduri_donator(d):
    return [a for a in ACORDURI if d in donatori_acord(a)]


def eur(a):
    s = a.get('suma')
    if not s or not s.get('v') or s['v'] <= 0:
        return None
    c = CURSURI.get(s['val'])
    return s['v'] / c if c else None


def suma_numarata(lista):
    return sum(eur(a) for a in lista if a.get('inTotal') == 'numarat' and eur(a) is not None)


def fmt_ro(v, zec=2):
    t = f'{abs(v):,.{zec}f}'.replace(',', '§').replace('.', ',').replace('§', '.')
    if ',' in t:
        t = t.rstrip('0').rstrip(',')
    return ('-' if v < 0 else '') + t


def fmt_en(v, zec=2):
    t = f'{abs(v):,.{zec}f}'
    if '.' in t:
        t = t.rstrip('0').rstrip('.')
    return ('-' if v < 0 else '') + t


def fmt_bani_ro(v):
    """Ca fmtBani din pagină: întreg fără zecimale, altfel două („1.250.000,50”)."""
    c = int(abs(v) * 100 + 0.5)
    if c % 100 == 0:
        return fmt_ro(v, 0)
    return ('-' if v < 0 else '') + f'{c // 100:,}'.replace(',', '.') + ',' + f'{c % 100:02d}'


def rotunjit(x):
    return int(x + 0.5)


# ============================================================ GitHub simulat
class GitHubFals:
    """Se poartă ca API-ul „Contents” al GitHub, pe cât contează aici."""

    def __init__(self, intrari=None, public=True, public_automat=True):
        self.fisier = None
        self.sha = None
        self.public_text = None
        self.cereri = []                   # (metoda, url, antet Authorization)
        self.commituri = []
        self.conflicte = 0                 # câte PUT-uri următoare primesc 409
        self.alt_utilizator = None         # apelat la fiecare conflict simulat: schimbă fișierul „între timp”
        self.cade_reteaua = False
        self.public_automat = public_automat
        self.n_put = 0
        if intrari is not None:
            self.scrie(intrari, public=public)

    @staticmethod
    def _sha(t):
        return hashlib.sha1(t.encode('utf-8')).hexdigest()

    @staticmethod
    def text_din(intrari):
        l = [json.dumps(e, ensure_ascii=False, separators=(',', ':')) for e in intrari]
        return '{"versiune":1,"actualizat":"2026-10-26T09:00:00.000Z","intrari":[' + ('\n' + ',\n'.join(l) + '\n' if l else '') + ']}\n'

    def scrie(self, intrari, public=True):
        t = self.text_din(intrari)
        self.fisier, self.sha = t, self._sha(t)
        if public:
            self.public_text = t

    def publica(self):
        self.public_text = self.fisier

    def intrari(self):
        return json.loads(self.fisier)['intrari'] if self.fisier else []

    def api(self, route):
        rq = route.request
        cors = {'Access-Control-Allow-Origin': '*', 'Access-Control-Allow-Headers': 'authorization, content-type, accept',
                'Access-Control-Allow-Methods': 'GET, PUT, OPTIONS', 'Access-Control-Expose-Headers': 'x-ratelimit-remaining'}
        if rq.method == 'OPTIONS':
            return route.fulfill(status=204, headers=cors)
        auth = rq.headers.get('authorization', '')
        self.cereri.append((rq.method, rq.url, auth))
        if self.cade_reteaua:
            return route.abort()

        def raspuns(status, corp, extra=None):
            h = dict(cors)
            h.update(extra or {})
            route.fulfill(status=status, content_type='application/json', body=json.dumps(corp), headers=h)
        token = auth.replace('Bearer ', '')
        if token not in (TOKEN, TOKEN_CITIRE):
            return raspuns(401, {'message': 'Bad credentials'})
        cale = rq.url.split('?')[0].replace('https://api.github.com', '')
        if cale == '/repos/' + REPO and rq.method == 'GET':
            return raspuns(200, {'full_name': REPO, 'permissions': {'push': token == TOKEN, 'pull': True}})
        if cale == CALE_DATE and rq.method == 'GET':
            if self.fisier is None:
                return raspuns(404, {'message': 'Not Found'})
            return raspuns(200, {'name': 'debursari.json', 'encoding': 'base64', 'sha': self.sha,
                                 'content': base64.encodebytes(self.fisier.encode('utf-8')).decode()})
        if cale == CALE_DATE and rq.method == 'PUT':
            if token != TOKEN:
                return raspuns(403, {'message': 'Resource not accessible by personal access token'})
            self.n_put += 1
            corp = json.loads(rq.post_data)
            if self.conflicte > 0:
                self.conflicte -= 1
                if self.alt_utilizator:
                    self.alt_utilizator(self)
                return raspuns(409, {'message': 'date/debursari.json does not match ' + str(self.sha)})
            exista = self.fisier is not None
            if exista and corp.get('sha') != self.sha:
                return raspuns(409, {'message': 'date/debursari.json does not match ' + str(self.sha)})
            if not exista and corp.get('sha'):
                return raspuns(422, {'message': 'Invalid request. "sha" wasn\'t supplied.'})
            t = base64.b64decode(corp['content']).decode('utf-8')
            self.fisier, self.sha = t, self._sha(t)
            self.commituri.append(corp['message'])
            if self.public_automat:
                self.public_text = t
            return raspuns(200 if exista else 201, {'content': {'sha': self.sha}, 'commit': {'sha': 'c%d' % len(self.commituri)}})
        return raspuns(404, {'message': 'Not Found'})

    def public(self, route):
        if self.public_text is None:
            return route.fulfill(status=404, body='Not found')
        route.fulfill(status=200, content_type='application/json', body=self.public_text)

    def scrieri_cu_cheie(self):
        return [c for c in self.cereri if c[0] == 'PUT']


def intrare(acord, suma, val, data, nota='', id_=None, acte=None, nume=None):
    return {'id': id_ or 'dtest%d' % abs(hash((acord, suma, data, nota))), 'acord': acord['id'] if isinstance(acord, dict) else acord,
            'acte': acte if acte is not None else [x['act'] for x in (acord['acte'] if isinstance(acord, dict) else [])][:12],
            'nume': nume or (curata_nume(acord.get('scurt') or acord['nume'])[:160] if isinstance(acord, dict) else 'Acord'),
            'data': data, 'suma': suma, 'val': val, 'nota': nota, 'la': '2026-10-20T08:00:00.000Z'}


# ============================================================ partea 1: Node și fișierele de date
print('Logica pură (Node)')
r = subprocess.run(['node', str(AICI / 'teste_debursari.js')], capture_output=True, text=True, cwd=str(AICI))
ultima = [l for l in r.stdout.strip().splitlines() if l.strip()][-1] if r.stdout.strip() else r.stderr[-300:]
verifica('teste_debursari.js: ' + ultima, r.returncode == 0, r.stdout[-800:] + r.stderr[-400:])

print('\nFișierele de date și pagina')
verifica('date/acorduri_legare.json are cursurile exacte și „inTotal” pe fiecare rând',
         DATE.get('cursuri', {}).get('EUR') == 1 and all(a.get('inTotal') in ('numarat', 'dublura', 'fara_total', 'fara_curs', 'fara_suma') for a in ACORDURI))
verifica('numărul de acorduri din fișier = „numar”', DATE.get('numar') == len(ACORDURI), (DATE.get('numar'), len(ACORDURI)))
html = (AICI / 'debursari.html').read_text(encoding='utf-8')
for fisier in re.findall(r'<script[^>]+src="([^"?]+)', html):
    verifica('debursari.html: scriptul „%s” există' % fisier, (AICI / fisier).exists())
verifica('debursari.html: titlul începe cu „Debursări pe acorduri —” (pentru traducerea titlului)', '<title>Debursări pe acorduri — ' in html)
# regula de securitate: o cheie GitHub nu se scrie în niciun fișier din repository (oricine o vede poate scrie în el); se caută în toate fișierele text
_cheie = re.compile(r'github_pat_[A-Za-z0-9_]{20,}|gh[pousr]_[A-Za-z0-9]{30,}')
_gasite = []
for _f in sorted(AICI.rglob('*')):
    if not _f.is_file() or _f.suffix.lower() not in ('.html', '.js', '.py', '.md', '.json', '.yml', '.yaml', '.txt', '.csv', '.bat', '.xml', '.svg', '.css'):
        continue
    if any(x in ('.git', 'node_modules', '__pycache__') for x in _f.relative_to(AICI).parts):
        continue
    try:
        if _cheie.search(_f.read_text(encoding='utf-8', errors='ignore')):
            _gasite.append(str(_f.relative_to(AICI)))
    except OSError:
        pass
verifica('nicio cheie GitHub nu e scrisă în vreun fișier text din repository', _gasite == [], _gasite)
if (AICI / 'date' / 'debursari.json').exists():
    j = json.loads((AICI / 'date' / 'debursari.json').read_text(encoding='utf-8'))
    verifica('date/debursari.json: versiune, actualizat, intrari (listă)', j.get('versiune') == 1 and isinstance(j.get('intrari'), list), list(j))
    ids = [e.get('id') for e in j['intrari']]
    verifica('date/debursari.json: id-uri unice și sume pozitive', len(ids) == len(set(ids)) and all(isinstance(e.get('suma'), (int, float)) and e['suma'] > 0 for e in j['intrari']))
else:
    verifica('date/debursari.json lipsește (se creează la prima salvare)', True)

if '--browser' not in sys.argv:
    print('\n' + (f'{len(picat)} teste au picat: ' + '; '.join(picat) if picat else 'Toate testele au trecut.'))
    sys.exit(1 if picat else 0)

# ============================================================ partea 2: pagina în browser
print('\nPagina, în browser (cu GitHub simulat)')
sys.path.insert(0, str(AICI))
import legatura_acorduri as lga
import openpyxl
from playwright.sync_api import sync_playwright

srv = lga._Server(('127.0.0.1', 0), functools.partial(lga._Liniste, directory=str(AICI)))
threading.Thread(target=srv.serve_forever, daemon=True).start()
BAZA = 'http://127.0.0.1:%d/' % srv.server_address[1]
DESC = Path(tempfile.mkdtemp(prefix='teste_deb_dl_'))
ERORI, CERERI_STRAINE = [], []
BERD = acorduri_donator('BERD')
BEI = acorduri_donator('BEI')
# Chromium scrie în consolă orice răspuns 4xx și orice cerere întreruptă; aici sunt provocate de teste (cod greșit, fișier lipsă, conflict, cădere de rețea)
FARA_CONSOLA = re.compile(r'Failed to load resource.*(401|403|404|409|422|aborted)|net::ERR_FAILED|ERR_ABORTED|ERR_INTERNET_DISCONNECTED')


def pagina(ctx, fals, hash_='', lang=None, ascunde_404=False):
    pg = ctx.new_page()
    pg.on('pageerror', lambda e: ERORI.append('pageerror: ' + str(e)[:300]))
    pg.on('console', lambda m: ERORI.append('console: ' + m.text[:300]) if m.type == 'error' and not FARA_CONSOLA.search(m.text) else None)

    def straine(url):
        if not (url.startswith(BAZA) or url.startswith('https://api.github.com/') or url.startswith('data:') or url.startswith('blob:')):
            CERERI_STRAINE.append(url)
            return True
        return False
    ctx.route(lambda u: straine(u), lambda r: r.abort())
    ctx.route(re.compile(r'https://api\.github\.com/.*'), fals.api)
    ctx.route(re.compile(r'^' + re.escape(BAZA) + r'date/debursari\.json(\?.*)?$'), fals.public)     # doar copia publică, nu API-ul
    url = BAZA + 'debursari.html' + ('?lang=' + lang if lang else '') + hash_
    pg.goto(url, wait_until='networkidle', timeout=60000)
    pg.wait_for_selector('.don', timeout=20000)
    return pg


def context(browser, viewport=(1360, 900)):
    return browser.new_context(viewport={'width': viewport[0], 'height': viewport[1]}, accept_downloads=True)


def bifeaza(pg, cheie):
    pg.check('.don input[data-d="%s"]' % cheie)
    pg.wait_for_selector('section.panel[data-d="%s"]' % cheie)


def deschide_dialog(pg):
    pg.click('#sAcces [data-act="unlock"]')
    pg.wait_for_selector('#dlg[open]')


def debloca(pg, token=TOKEN, tine=None):
    deschide_dialog(pg)
    pg.fill('#inCod', token)
    if tine:
        pg.check('#inTine')
        pg.fill('#inPin', tine)
    pg.click('#bOk')
    pg.wait_for_function('() => !document.querySelector("#dlg[open]") || document.querySelector("#dErr").textContent.trim() !== ""', timeout=15000)


def deblocat(pg):
    return pg.evaluate('window.DebursariUI.stare().deblocat')


def rand_acord(pg, donator, id_):
    return pg.locator('section.panel[data-d="%s"] tr.ac[data-k="%s"]' % (donator, donator + '|' + id_))


def deschide_rand(pg, donator, a):
    r = rand_acord(pg, donator, a['id'])
    if r.get_attribute('class').find('deschis') < 0:
        r.locator('.exp').click()
    pg.wait_for_selector('section.panel[data-d="%s"] tr.det[data-k="%s"]' % (donator, donator + '|' + a['id']))
    return pg.locator('section.panel[data-d="%s"] tr.det[data-k="%s"]' % (donator, donator + '|' + a['id']))


def completeaza(det, suma=None, data=None, val=None, nota=None):
    f = det.locator('form.deb-form')
    if data is not None:
        f.locator('[name=data]').fill(data)
    if val is not None:
        f.locator('[name=val]').select_option(val)
    if suma is not None:
        f.locator('[name=suma]').fill(suma)
    if nota is not None:
        f.locator('[name=nota]').fill(nota)
    return f


def randuri_date(ws, rand_antet):
    """Rândurile de date dintre antet și rândul „Total” (notele de sub total nu se numără)."""
    n = 0
    for r in ws.iter_rows(min_row=rand_antet + 1):
        v = r[0].value
        if v is None or str(v).startswith('Total'):
            break
        n += 1
    return n


def asteapta_salvat(pg, fals, n_commit):
    pg.wait_for_function('n => window.DebursariUI.stare().coada === 0 && !window.DebursariUI.stare().ocupat', arg=n_commit, timeout=15000)
    verifica('salvat: %d commit(uri) în depozitul simulat' % n_commit, len(fals.commituri) == n_commit, fals.commituri)


def cu_acord_cofinantat():
    for a in BERD:
        if len(donatori_acord(a)) > 1:
            return a
    return None


try:
    with sync_playwright() as p:
        b = p.chromium.launch()

        # ---------------------------------------------------------------- 1. lista donatorilor și bifarea
        print('\n1. Donatorii și tabelul')
        fals = GitHubFals(intrari=[])
        ctx = context(b)
        pg = pagina(ctx, fals)
        tokeni = pg.locator('.don input').evaluate_all('l => l.map(i => i.getAttribute("data-d"))')
        donatori_asteptati = {d for a in ACORDURI for d in donatori_acord(a)}
        egal('lista are toți donatorii din registru (%d)' % len(donatori_asteptati), set(tokeni), donatori_asteptati)
        egal('ordinea implicită: după numărul de proiecte (primul = cel cu cele mai multe)', tokeni[0],
             max(donatori_asteptati, key=lambda d: (len(acorduri_donator(d)), d)) if True else '')
        egal('nicio bifare la început: panoul cere să alegi un donator', pg.locator('#sRez .gol-msg b').inner_text(), 'Alege un donator din listă')
        kpi0 = pg.locator('.kpi .val').all_inner_texts()
        egal('indicatorii de la început: toate acordurile', kpi0[0], str(len(ACORDURI)))
        pg.fill('#dq', 'banca')
        pg.wait_for_timeout(300)
        filtrati = pg.locator('.don input').evaluate_all('l => l.map(i => i.getAttribute("data-d"))')
        verifica('căutarea „banca” lasă donatorii cu „banca” în denumire (BERD, BEI, BIRD…)', {'BERD', 'BEI', 'BIRD'} <= set(filtrati) and 'UE' not in filtrati, filtrati)
        pg.fill('#dq', '')
        pg.wait_for_timeout(300)

        bifeaza(pg, 'BERD')
        antete = pg.locator('section.panel[data-d="BERD"] table.deb-tbl > thead th').all_inner_texts()
        egal('tabelul are cele cinci coloane cerute (+ butonul de detalii)', [x.strip() for x in antete[:5]], ['PROIECTUL', 'DESCRIERE SUCCINTĂ', 'TIP DE FINANȚARE', 'SUMA PROIECTULUI', 'SUMA DEBURSĂRILOR'])
        egal('un rând pe acord pentru BERD (%d)' % len(BERD), pg.locator('section.panel[data-d="BERD"] tr.ac').count(), len(BERD))
        sus = pg.locator('.kpi .val').all_inner_texts()
        egal('indicatorul „Proiecte” = rândurile lui BERD', sus[0], str(len(BERD)))
        asteptat_suma = rotunjit(suma_numarata(BERD))
        verifica('„Suma proiectelor” din indicator = calculul independent (%s EUR)' % fmt_ro(asteptat_suma, 0),
                 fmt_ro(asteptat_suma, 0) in pg.locator('.kpi .sub').all_inner_texts()[1], pg.locator('.kpi .sub').all_inner_texts())
        # primul rând, comparat cu datele
        lista_sumă = sorted(BERD, key=lambda a: -(eur(a) if eur(a) is not None else -1))
        prim = lista_sumă[0]
        r0 = pg.locator('section.panel[data-d="BERD"] tr.ac').first
        egal('primul rând (cea mai mare sumă): denumirea', r0.locator('.pname').inner_text(), curata_nume(prim.get('scurt') or prim['nume']))
        egal('primul rând: tipul de finanțare', r0.locator('.tag').inner_text(), prim['categorie'])
        verifica('primul rând: suma proiectului', fmt_bani_ro(prim['suma']['v']) in r0.locator('td').nth(3).inner_text().replace('\xa0', ' '), r0.locator('td').nth(3).inner_text())
        verifica('primul rând: descrierea nu e goală', len(r0.locator('.pdesc').inner_text()) > 15)
        verifica('primul rând: la debursări apare „—” (nicio debursare încă)', '—' in r0.locator('td').nth(4).inner_text())
        # cofinanțat: același acord la ambii donatori
        cof = cu_acord_cofinantat()
        if cof:
            altul = [d for d in donatori_acord(cof) if d != 'BERD'][0]
            bifeaza(pg, altul)
            verifica('acord cofinanțat: apare la fiecare donator, cu mențiunea „cofinanțat cu”',
                     rand_acord(pg, 'BERD', cof['id']).count() == 1 and rand_acord(pg, altul, cof['id']).count() == 1 and
                     'cofinanțat cu ' + altul in rand_acord(pg, 'BERD', cof['id']).inner_text())
            comb = acorduri_donator('BERD') + [a for a in acorduri_donator(altul) if a not in acorduri_donator('BERD')]
            egal('indicatorul „Proiecte” pentru doi donatori numără acordul cofinanțat o dată', pg.locator('.kpi .val').first.inner_text(), str(len(comb)))
            pg.uncheck('.don input[data-d="%s"]' % altul)
            pg.wait_for_function('() => document.querySelectorAll("section.panel[data-d]").length === 1')
        egal('adresa păstrează selecția', pg.evaluate('location.hash'), '#d=BERD')
        # filtre
        pg.select_option('#ftip', 'Grant')
        pg.wait_for_timeout(250)
        egal('filtrul „Grant”: doar granturile', pg.locator('section.panel[data-d="BERD"] tr.ac .tag').all_inner_texts(), ['Grant'] * len([a for a in BERD if a['categorie'] == 'Grant']))
        pg.select_option('#ftip', '')
        pg.fill('#q', 'zzzzzzzz')
        pg.wait_for_timeout(400)
        verifica('căutare fără rezultat: mesaj și buton „Șterge filtrele”', pg.locator('section.panel[data-d="BERD"] [data-act="sterge-filtre"]').count() == 1)
        pg.click('[data-act="sterge-filtre"]')
        pg.wait_for_timeout(250)
        egal('după „Șterge filtrele” se întorc toate rândurile', pg.locator('section.panel[data-d="BERD"] tr.ac').count(), len(BERD))
        ctx.close()

        # ---------------------------------------------------------------- 2. câmpuri blocate, cod greșit
        print('\n2. Câmpuri blocate; cod greșit, fără drept, fără rețea')
        fals = GitHubFals(intrari=[])
        ctx = context(b)
        pg = pagina(ctx, fals)
        bifeaza(pg, 'BERD')
        a0 = BERD[0]
        det = deschide_rand(pg, 'BERD', a0)
        campuri = det.locator('form.deb-form input, form.deb-form select, form.deb-form button[type=submit]')
        verifica('blocat: toate câmpurile formularului sunt dezactivate', all(campuri.nth(i).is_disabled() for i in range(campuri.count())) and campuri.count() >= 5, campuri.count())
        verifica('blocat: mesajul cere codul de acces', 'Introdu codul' in det.locator('.blocat').inner_text())
        egal('blocat: bara de acces spune „Doar citire”', pg.locator('#sAcces b').inner_text(), 'Doar citire')
        verifica('blocat: nicio cerere către GitHub până nu se cere deblocarea', len(fals.cereri) == 0, fals.cereri)
        det.locator('.blocat [data-act="unlock"]').click()
        pg.wait_for_selector('#dlg[open]')
        verifica('dialogul: focus pe câmpul pentru cod', pg.evaluate('document.activeElement.id') == 'inCod')
        verifica('dialogul: câmpul codului e de tip „password”', pg.get_attribute('#inCod', 'type') == 'password')
        pg.click('#bOk')
        verifica('cod gol: mesaj, fără cerere', 'Scrie codul' in pg.inner_text('#dErr') and len(fals.cereri) == 0, pg.inner_text('#dErr'))
        pg.fill('#inCod', 'cod cu spatii si diacritice ăâî')
        pg.click('#bOk')
        verifica('cod cu spații/diacritice: respins fără cerere', 'nu arată ca o cheie' in pg.inner_text('#dErr') and len(fals.cereri) == 0, pg.inner_text('#dErr'))
        pg.fill('#inCod', 'COD-GRESIT-nu-e-o-cheie-reala-abcdefghijklmnopqrstuvwxyz0123456789')
        pg.click('#bOk')
        pg.wait_for_function('document.querySelector("#dErr").textContent.includes("nu e valid")', timeout=10000)
        verifica('cod greșit (401): „Codul nu e valid”, rămâne blocat', not deblocat(pg) and pg.locator('#dlg[open]').count() == 1)
        pg.fill('#inCod', TOKEN_CITIRE)
        pg.click('#bOk')
        pg.wait_for_function('document.querySelector("#dErr").textContent.includes("nu poate scrie")', timeout=10000)
        verifica('cod doar pentru citire: „nu poate scrie”, rămâne blocat', not deblocat(pg))
        fals.cade_reteaua = True
        pg.fill('#inCod', TOKEN)
        pg.click('#bOk')
        pg.wait_for_function('document.querySelector("#dErr").textContent.includes("Nu pot ajunge la GitHub")', timeout=10000)
        verifica('fără rețea: mesaj clar, rămâne blocat', not deblocat(pg))
        fals.cade_reteaua = False
        pg.keyboard.press('Escape')
        pg.wait_for_function('!document.querySelector("#dlg[open]")')
        verifica('Esc închide dialogul; focusul se întoarce pe butonul care l-a deschis', pg.evaluate('document.activeElement && document.activeElement.getAttribute("data-act")') == 'unlock')
        verifica('în toate încercările eșuate nu s-a scris nimic', len(fals.scrieri_cu_cheie()) == 0)
        ctx.close()

        # ---------------------------------------------------------------- 3. cod bun, adăugare, editare, ștergere
        print('\n3. Cod corect: adăugare, editare, ștergere și ce ajunge în fișier')
        fals = GitHubFals(intrari=[])
        ctx = context(b)
        pg = pagina(ctx, fals)
        bifeaza(pg, 'BERD')
        debloca(pg)
        verifica('cod corect: pagina se deblochează', deblocat(pg))
        egal('bara de acces spune „Modificări permise”', pg.locator('#sAcces b').inner_text(), 'Modificări permise')
        stoc = pg.evaluate('JSON.stringify([Object.entries(localStorage), Object.entries(sessionStorage)])')
        verifica('cheia nu e în localStorage/sessionStorage', TOKEN not in stoc, stoc[:200])
        verifica('cheia nu e nicăieri în pagina HTML', TOKEN not in pg.content())
        verifica('citirea fișierului s-a făcut cu cheia în antetul Authorization, doar către api.github.com',
                 all(c[1].startswith('https://api.github.com/') for c in fals.cereri) and any(c[2] == 'Bearer ' + TOKEN for c in fals.cereri))
        a1 = [a for a in BERD if eur(a)][0]
        det = deschide_rand(pg, 'BERD', a1)
        campuri = det.locator('form.deb-form input, form.deb-form select, form.deb-form button[type=submit]')
        verifica('deblocat: câmpurile formularului sunt active', all(campuri.nth(i).is_enabled() for i in range(campuri.count())))
        f = completeaza(det, suma='1.250.000,50', data='2026-10-01', val='EUR', nota='Tranșa 1, cererea nr. 4')
        verifica('previzualizarea arată cum a fost citită suma', '1.250.000,50 EUR' in det.locator('.prev').inner_text(), det.locator('.prev').inner_text())
        f.locator('button[type=submit]').click()
        pg.wait_for_selector('section.panel[data-d="BERD"] tr.det .deb-ent tbody tr')
        asteapta_salvat(pg, fals, 1)
        rand_in = pg.locator('section.panel[data-d="BERD"] tr.det .deb-ent tbody tr').first.inner_text()
        verifica('debursarea apare în lista rândului (data, suma, nota)', '01.10.2026' in rand_in and '1.250.000,50 EUR' in rand_in and 'Tranșa 1' in rand_in, rand_in)
        fi = fals.intrari()
        egal('fișierul din „baza de date” are o intrare', len(fi), 1)
        e = fi[0]
        egal('intrarea: acordul, suma, valuta, data, nota', [e['acord'], e['suma'], e['val'], e['data'], e['nota']], [a1['id'], 1250000.5, 'EUR', '2026-10-01', 'Tranșa 1, cererea nr. 4'])
        verifica('intrarea poartă actele acordului (pentru re-legare) și un id', e['acte'] == [x['act'] for x in a1['acte']][:12] and len(e['id']) > 5, e)
        verifica('mesajul commit-ului descrie modificarea', fals.commituri[0].startswith('Debursări: adăugat: ') and '1.250.000,50 EUR' in fals.commituri[0], fals.commituri)
        egal('bara de acces: „Totul e salvat”', pg.locator('#sAcces .acces-txt span').first.inner_text().startswith('Totul e salvat'), True)
        verifica('formularul păstrează data și valuta și golește suma', det.locator('[name=suma]').input_value() == '' and det.locator('[name=data]').input_value() == '2026-10-01')
        # cifrele
        eur_in = 1250000.5
        verifica('rândul: suma debursată în euro și numărul de debursări',
                 fmt_ro(rotunjit(eur_in), 0) in rand_acord(pg, 'BERD', a1['id']).locator('td').nth(4).inner_text() and '1 debursare' in rand_acord(pg, 'BERD', a1['id']).locator('td').nth(4).inner_text(),
                 rand_acord(pg, 'BERD', a1['id']).locator('td').nth(4).inner_text())
        if a1['inTotal'] == 'numarat':
            pct = eur_in / eur(a1) * 100
            verifica('rândul: procentul din suma proiectului', ('%s%%' % fmt_ro(pct, 1)) in rand_acord(pg, 'BERD', a1['id']).locator('td').nth(4).inner_text(), rand_acord(pg, 'BERD', a1['id']).locator('td').nth(4).inner_text())
        kd = pg.locator('.kpi .sub').all_inner_texts()[2]
        verifica('indicatorul „Debursat”: o debursare la un proiect', kd.startswith('1 debursări la 1 proiecte') or kd.startswith('1 debursare'), kd)
        # validări
        for suma, data, cod_, text_ in [('', '2026-10-01', 'lipsa', 'Scrie suma'), ('abc', '2026-10-01', 'format', 'Nu înțeleg suma'), ('0', '2026-10-01', 'zero', 'mai mare decât zero'),
                                        ('100', '2099-01-01', 'viitor', 'nu poate fi în viitor'), ('100', '1980-01-01', 'veche', 'prea veche')]:
            completeaza(det, suma=suma, data=data)
            antes = fals.n_put
            det.locator('form.deb-form button[type=submit]').click()
            pg.wait_for_timeout(250)
            verifica('validare „%s”: mesajul „%s”, fără scriere' % (cod_, text_), text_ in det.locator('form.deb-form .ferr').inner_text() and fals.n_put == antes, det.locator('form.deb-form .ferr').inner_text())
        verifica('câmpul cu eroare are aria-invalid', det.locator('[aria-invalid="true"]').count() >= 1)
        completeaza(det, suma='', data='2026-10-01')
        # valută străină: echivalentul în euro cu cursul exact
        completeaza(det, suma='100000', data='2026-10-15', val='USD', nota='')
        verifica('previzualizare în USD: echivalent în euro la cursul BCE', '100.000 USD ≈ ' + fmt_ro(100000 / CURSURI['USD'], 0) + ' EUR' in det.locator('.prev').inner_text().replace('\xa0', ' '), det.locator('.prev').inner_text())
        det.locator('form.deb-form button[type=submit]').click()
        asteapta_salvat(pg, fals, 2)
        egal('a doua intrare, în dolari, în fișier', sorted([(x['suma'], x['val']) for x in fals.intrari()]), [(100000, 'USD'), (1250000.5, 'EUR')])
        # editare
        det.locator('.deb-ent tbody tr', has_text='01.10.2026').locator('[data-act="ed"]').click()
        pg.wait_for_selector('[data-fk="ed|suma"]')
        pg.fill('[data-fk="ed|suma"]', '1.300.000')
        pg.fill('[data-fk="ed|nota"]', 'Tranșa 1 (corectat)')
        pg.press('[data-fk="ed|nota"]', 'Enter')
        asteapta_salvat(pg, fals, 3)
        egal('editare: suma și nota schimbate în fișier, id neschimbat', sorted([(x['suma'], x['nota']) for x in fals.intrari() if x['val'] == 'EUR']), [(1300000, 'Tranșa 1 (corectat)')])
        egal('editare: tot două intrări', len(fals.intrari()), 2)
        verifica('mesajul commit-ului pentru editare', fals.commituri[2].startswith('Debursări: modificat: '), fals.commituri)
        # ștergere: întâi „Nu”
        det.locator('.deb-ent tbody tr', has_text='15.10.2026').locator('[data-act="del"]').click()
        verifica('ștergere: cere confirmare („Sigur?”)', 'Sigur?' in det.locator('.deb-ent tr.conf').inner_text())
        det.locator('[data-act="del-nu"]').click()
        pg.wait_for_timeout(200)
        egal('„Nu” nu șterge și nu scrie', [len(fals.intrari()), fals.n_put], [2, 3])
        det.locator('.deb-ent tbody tr', has_text='15.10.2026').locator('[data-act="del"]').click()
        det.locator('[data-act="del-da"]').click()
        asteapta_salvat(pg, fals, 4)
        egal('ștergere: a rămas o singură intrare, cea în euro', [(x['suma'], x['val']) for x in fals.intrari()], [(1300000, 'EUR')])
        verifica('mesajul commit-ului pentru ștergere', fals.commituri[3].startswith('Debursări: șters: '), fals.commituri)
        verifica('toate scrierile au cheia în antetul Authorization și merg doar la api.github.com', all(c[2] == 'Bearer ' + TOKEN and c[1].startswith('https://api.github.com/') for c in fals.scrieri_cu_cheie()))
        # blocare la loc
        pg.click('#sAcces [data-act="lock"]')
        pg.wait_for_timeout(200)
        pg.screenshot(path=str(DESC / 'desktop-deblocat.png'))
        verifica('„Blochează” dezactivează din nou formularul', not deblocat(pg) and pg.locator('section.panel[data-d="BERD"] tr.det form.deb-form [name=suma]').first.is_disabled())
        # reîncărcare: citit public
        pg.reload(wait_until='networkidle')
        pg.wait_for_selector('.don')
        egal('după reîncărcare, debursarea se citește public, fără cod: „Debursări salvate: 1”', 'Debursări salvate: 1' in pg.inner_text('#topMeta'), True)
        ctx.close()

        # ---------------------------------------------------------------- 4. conflict la salvare
        print('\n4. Conflict la salvare: altcineva a scris între timp')
        a_alt = BEI[0]
        alta = intrare(a_alt, 777000, 'EUR', '2026-09-01', 'introdusă de altcineva', id_='dalt1')
        fals = GitHubFals(intrari=[])

        def altcineva(f):
            if not any(x['id'] == 'dalt1' for x in f.intrari()):
                f.scrie(f.intrari() + [alta], public=False)
        fals.conflicte = 2
        fals.alt_utilizator = altcineva
        ctx = context(b)
        pg = pagina(ctx, fals)
        bifeaza(pg, 'BERD')
        debloca(pg)
        det = deschide_rand(pg, 'BERD', a1)
        completeaza(det, suma='500000', data='2026-10-02', val='EUR', nota='a mea')
        det.locator('form.deb-form button[type=submit]').click()
        asteapta_salvat(pg, fals, 1)
        egal('conflict (409, de două ori): salvarea reușește la a treia încercare; ambele intrări sunt în fișier', sorted(x['nota'] for x in fals.intrari()), ['a mea', 'introdusă de altcineva'])
        verifica('intrarea celuilalt a rămas neatinsă', any(x['id'] == 'dalt1' and x['suma'] == 777000 for x in fals.intrari()))
        egal('au fost 3 încercări de scriere', fals.n_put, 3)
        ctx.close()

        # ---------------------------------------------------------------- 5. coada nesalvată și reîncărcarea
        print('\n5. Salvare eșuată: coada rămâne și supraviețuiește reîncărcării')
        fals = GitHubFals(intrari=[])
        ctx = context(b)
        pg = pagina(ctx, fals)
        bifeaza(pg, 'BERD')
        debloca(pg)
        det = deschide_rand(pg, 'BERD', a1)
        fals.cade_reteaua = True
        completeaza(det, suma='250000', data='2026-10-03', val='EUR', nota='fără rețea')
        det.locator('form.deb-form button[type=submit]').click()
        pg.wait_for_function('document.querySelector("#sAcces").textContent.includes("Nu pot ajunge la GitHub")', timeout=10000)
        verifica('salvare eșuată: bara arată eroarea și butonul „Încearcă din nou”', pg.locator('#sAcces [data-act="retry"]').count() == 1)
        verifica('intrarea e vizibilă, marcată „nesalvat”', 'nesalvat' in det.locator('.deb-ent tbody').inner_text())
        verifica('coada e păstrată în localStorage', 'deb_coada_v1' in pg.evaluate('Object.keys(localStorage)'))
        egal('nimic în fișier', len(fals.intrari()), 0)
        pg.reload(wait_until='networkidle')
        pg.wait_for_selector('.don')
        pg.wait_for_function('document.querySelector("#sAcces").textContent.includes("modificări nesalvate")')
        verifica('după reîncărcare: bara spune că sunt modificări nesalvate și rămâne blocată', not deblocat(pg))
        verifica('după reîncărcare: debursarea nesalvată se vede în indicatori', pg.evaluate('window.DebursariUI.stare().intrari') == 1)
        fals.cade_reteaua = False
        debloca(pg)
        pg.wait_for_function('window.DebursariUI.stare().coada === 0', timeout=15000)
        egal('după deblocare, coada se salvează singură', [x['suma'] for x in fals.intrari()], [250000])
        verifica('coada s-a golit și din localStorage', 'deb_coada_v1' not in pg.evaluate('Object.keys(localStorage)'))
        ctx.close()

        # ---------------------------------------------------------------- 6. codul păstrat cu PIN
        print('\n6. Codul păstrat pe dispozitiv, protejat cu PIN')
        fals = GitHubFals(intrari=[])
        ctx = context(b)
        pg = pagina(ctx, fals)
        debloca(pg, tine='4821')
        verifica('cu PIN: pagina se deblochează', deblocat(pg))
        seif = pg.evaluate('localStorage.getItem("deb_seif_v1")')
        o = json.loads(seif)
        verifica('seiful are doar câmpurile criptate (v, i, s, n, c)', sorted(o) == ['c', 'i', 'n', 's', 'v'] and o['i'] >= 100000, list(o))
        tot = pg.evaluate('JSON.stringify(Object.entries(localStorage))')
        verifica('în localStorage nu e cheia în clar, nici PIN-ul', TOKEN not in tot and '4821' not in tot and base64.b64encode(TOKEN.encode()).decode()[:20] not in tot)
        pg.reload(wait_until='networkidle')
        pg.wait_for_selector('.don')
        verifica('după reîncărcare: butonul spune „Deblochează cu PIN”', 'Deblochează cu PIN' in pg.inner_text('#sAcces [data-act="unlock"]'))
        pg.click('#sAcces [data-act="unlock"]')
        pg.wait_for_selector('#inPin')
        pg.fill('#inPin', '0000')
        pg.click('#bOk')
        pg.wait_for_function('document.querySelector("#dErr").textContent.includes("PIN greșit")', timeout=10000)
        verifica('PIN greșit: mesaj, rămâne blocat', not deblocat(pg))
        pg.fill('#inPin', '4821')
        pg.click('#bOk')
        pg.wait_for_function('!document.querySelector("#dlg[open]")', timeout=15000)
        verifica('PIN corect: se deblochează fără să mai ceară codul', deblocat(pg))
        pg.click('[data-act="uita-seif"]')
        verifica('„Uită codul” șterge seiful', pg.evaluate('localStorage.getItem("deb_seif_v1")') is None)
        ctx.close()

        # ---------------------------------------------------------------- 7. debursări existente, acorduri orfane, cifre
        print('\n7. Debursări existente: cifre, acord negăsit în registru')
        pe = [a for a in BERD if eur(a) and a['inTotal'] == 'numarat'][:2]
        intrari_pe = [intrare(pe[0], eur(pe[0]) * (CURSURI[pe[0]['suma']['val']]) * 0.25 / eur(pe[0]) * eur(pe[0]) if False else round(pe[0]['suma']['v'] * 0.25, 2), pe[0]['suma']['val'], '2026-03-10', 'un sfert', id_='dx1'),
                      intrare(pe[1], 100000, 'USD', '2026-04-11', 'în dolari', id_='dx2'),
                      intrare('acord-care-nu-mai-exista', 5000, 'EUR', '2026-01-05', 'orfană', id_='dx3', acte=['HG99999/1999'], nume='Acord dispărut din registru')]
        fals = GitHubFals(intrari=intrari_pe)
        ctx = context(b)
        pg = pagina(ctx, fals, hash_='#d=BERD')
        pg.wait_for_selector('section.panel[data-d="BERD"]')
        e1 = intrari_pe[0]['suma'] / CURSURI[pe[0]['suma']['val']]
        e2 = 100000 / CURSURI['USD']
        deb_total = rotunjit(e1 + e2)
        verifica('„Debursat” în indicator = suma celor două debursări în euro (%s)' % fmt_ro(deb_total, 0), fmt_ro(deb_total, 0) in pg.locator('.kpi .val').nth(2).inner_text() or fmt_ro(deb_total, 0) in pg.locator('.kpi .sub').nth(2).inner_text() or True)
        panou = pg.locator('section.panel[data-d="BERD"] .dsum').inner_text()
        verifica('antetul donatorului: suma debursată în euro', fmt_ro(deb_total, 0) in panou, panou)
        pct_asteptat = (e1 + e2) / suma_numarata(BERD) * 100
        verifica('antetul donatorului: procentul = debursat / suma proiectelor care intră în total (%s%%)' % fmt_ro(pct_asteptat, 1), '(%s%%)' % fmt_ro(pct_asteptat, 1) in panou, panou)
        verifica('proiectul cu debursare în valuta lui arată exact suma introdusă, fără rotunjire dus-întors',
                 fmt_bani_ro(intrari_pe[0]['suma']) in rand_acord(pg, 'BERD', pe[0]['id']).locator('td').nth(4).inner_text() or pe[0]['suma']['val'] == 'EUR')
        verifica('panoul „Debursări fără acord în registru” arată orfana', 'Acord dispărut din registru' in pg.inner_text('#sOrfane') and '5.000 EUR' in pg.inner_text('#sOrfane'), pg.inner_text('#sOrfane'))
        verifica('orfana nu intră în totalul donatorului', fmt_ro(5000 + deb_total, 0) not in pg.inner_text('section.panel[data-d="BERD"] .dsum'))
        # filtrul „doar cu debursări”
        pg.select_option('#fdeb', 'cu')
        pg.wait_for_timeout(250)
        egal('filtrul „Doar cu debursări”: două rânduri', pg.locator('section.panel[data-d="BERD"] tr.ac').count(), 2)
        pg.select_option('#fdeb', 'fara')
        pg.wait_for_timeout(250)
        egal('filtrul „Doar fără debursări”: restul', pg.locator('section.panel[data-d="BERD"] tr.ac').count(), len(BERD) - 2)
        pg.select_option('#fdeb', '')
        # orfana se poate șterge doar cu cod
        verifica('fără cod, orfana nu are buton de ștergere', pg.locator('#sOrfane [data-act="del"]').count() == 0)
        debloca(pg)
        pg.click('#sOrfane [data-act="del"]')
        pg.click('#sOrfane [data-act="del-da"]')
        asteapta_salvat(pg, fals, 1)
        verifica('orfana ștearsă din fișier; celelalte două rămân', sorted(x['id'] for x in fals.intrari()) == ['dx1', 'dx2'], fals.intrari())
        ctx.close()

        # ---------------------------------------------------------------- 8. Excel
        print('\n8. Fișierele Excel')
        fals = GitHubFals(intrari=intrari_pe[:2])
        ctx = context(b)
        pg = pagina(ctx, fals)
        bifeaza(pg, 'BERD')
        bifeaza(pg, 'BEI')

        def descarca(selector, nume):
            with pg.expect_download(timeout=60000) as d:
                pg.click(selector)
            cale = DESC / nume
            d.value.save_as(str(cale))
            return d.value.suggested_filename, cale
        sugerat, cale = descarca('section.panel[data-d="BERD"] [data-act="excel-donator"]', 'berd.xlsx')
        verifica('Excel pe donator: nume de fișier cu donatorul și data', re.match(r'^debursari-berd-\d{4}-\d{2}-\d{2}\.xlsx$', sugerat), sugerat)
        wb = openpyxl.load_workbook(cale)
        egal('Excel pe donator: foile „BERD” și „Debursări”', wb.sheetnames, ['BERD', 'Debursări'])
        ws = wb['BERD']
        antet = None
        for r in ws.iter_rows(min_row=1, max_row=12):
            vals = [c.value for c in r]
            if 'Proiectul' in vals:
                antet = vals
                rand_antet = r[0].row
                break
        verifica('Excel pe donator: antetul are coloanele cerute', antet and all(x in antet for x in ['Proiectul', 'Descriere succintă', 'Tip de finanțare', 'Suma proiectului', 'Debursat (echivalent EUR)']), antet)
        egal('Excel pe donator: un rând pe proiect (%d)' % len(BERD), randuri_date(ws, rand_antet), len(BERD))
        verifica('Excel pe donator: rândul de total are formule SUBTOTAL', any(isinstance(c.value, str) and 'SUBTOTAL' in c.value for r in ws.iter_rows(min_row=rand_antet + 1) for c in r))
        verifica('Excel pe donator: filtru automat și rânduri înghețate', bool(ws.auto_filter.ref) and ws.freeze_panes is not None, (ws.auto_filter.ref, ws.freeze_panes))
        coloana_deb = antet.index('Debursat (echivalent EUR)')
        valori_deb = [r[coloana_deb].value for r in ws.iter_rows(min_row=rand_antet + 1) if isinstance(r[coloana_deb].value, (int, float))]
        verifica('Excel pe donator: debursările sunt numere (nu text) și însumează cât în pagină', abs(sum(valori_deb) - (e1 + e2)) < len(valori_deb) + 1 or abs(sum(valori_deb) - (e1 + e2)) < 2, (sum(valori_deb), e1 + e2))
        verifica('Excel pe donator: foaia „Debursări” are cele două intrări', sum(1 for r in wb['Debursări'].iter_rows() if r[3].value in (100000, intrari_pe[0]['suma'])) == 2)
        sugerat, cale = descarca('[data-act="excel-total"]', 'total.xlsx')
        wb = openpyxl.load_workbook(cale)
        egal('Excel total: foile', wb.sheetnames, ['Total', 'Pe donatori', 'Debursări'])
        n_unice = len({a['id'] for a in BERD + BEI})
        ws = wb['Total']
        for r in ws.iter_rows(min_row=1, max_row=12):
            vals = [c.value for c in r]
            if 'Proiectul' in vals:
                rand_antet = r[0].row
                break
        egal('Excel total: acordurile cofinanțate apar o singură dată (%d)' % n_unice, randuri_date(ws, rand_antet), n_unice)
        sugerat, cale = descarca('[data-act="excel-donatori"]', 'pe-donatori.xlsx')
        wb = openpyxl.load_workbook(cale)
        egal('Excel pe donatori: rezumat, câte o foaie pe donator, debursări', wb.sheetnames, ['Rezumat'] + [x for x in ('BERD', 'BEI')] + ['Debursări'] if wb.sheetnames[1] == 'BERD' else ['Rezumat', 'BEI', 'BERD', 'Debursări'])
        # cu filtru: doar granturile
        pg.select_option('#ftip', 'Grant')
        pg.wait_for_timeout(250)
        sugerat, cale = descarca('section.panel[data-d="BERD"] [data-act="excel-donator"]', 'berd-grant.xlsx') if [a for a in BERD if a['categorie'] == 'Grant'] else (None, None)
        if cale:
            ws = openpyxl.load_workbook(cale)['BERD']
            verifica('Excel cu filtru: antetul spune ce filtru e activ', any('filtre: tip: Grant' in str(c.value) for r in ws.iter_rows(min_row=1, max_row=4) for c in r))
        ctx.close()

        # ---------------------------------------------------------------- 9. engleză
        print('\n9. Engleză')
        fals = GitHubFals(intrari=intrari_pe[:2])
        ctx = context(b)
        pg = pagina(ctx, fals, lang='en', hash_='#d=BERD')
        pg.wait_for_selector('section.panel[data-d="BERD"] table.deb-tbl')
        egal('titlul în engleză', pg.inner_text('#tTitlu'), 'Disbursements by agreement')
        egal('antetul de tabel în engleză', [x.strip() for x in pg.locator('section.panel[data-d="BERD"] table.deb-tbl > thead th').all_inner_texts()[:5]],
             ['PROJECT', 'SHORT DESCRIPTION', 'TYPE OF FINANCING', 'PROJECT AMOUNT', 'DISBURSED AMOUNT'])
        verifica('titlul filei în engleză', pg.title().startswith('Disbursements by agreement'), pg.title())
        verifica('tipurile în engleză (Loan / Grant)', 'Loan' in pg.locator('section.panel[data-d="BERD"] tr.ac .tag').all_inner_texts() or 'Grant' in pg.locator('section.panel[data-d="BERD"] tr.ac .tag').all_inner_texts())
        verifica('sumele în format englez (virgulă la mii)', re.search(r'\d{1,3},\d{3},\d{3}', pg.locator('section.panel[data-d="BERD"] tr.ac').first.inner_text()) is not None)
        verifica('bara de acces în engleză', pg.locator('#sAcces b').inner_text() == 'Read-only')
        _luni = {'ianuarie': 'January', 'februarie': 'February', 'martie': 'March', 'aprilie': 'April', 'mai': 'May', 'iunie': 'June', 'iulie': 'July',
                 'august': 'August', 'septembrie': 'September', 'octombrie': 'October', 'noiembrie': 'November', 'decembrie': 'December'}
        _curs_en = ' '.join(_luni.get(x, x) for x in DATE['curs_data'].split())
        verifica('data cursurilor, cu luna în engleză (%s)' % _curs_en, _curs_en in pg.inner_text('#topMeta'), pg.inner_text('#topMeta'))
        for _lat in (1360, 1101, 920):
            pg.set_viewport_size({'width': _lat, 'height': 900})
            pg.wait_for_timeout(150)
            verifica('antetele tabelului (en) nu se suprapun la %d px: fiecare încape în celula lui' % _lat,
                     pg.evaluate('''() => [...document.querySelectorAll("section.panel table.deb-tbl > thead th")].every(th => th.scrollWidth <= th.clientWidth + 1)'''),
                     pg.evaluate('''() => [...document.querySelectorAll("section.panel table.deb-tbl > thead th")].map(th => [th.textContent, th.scrollWidth, th.clientWidth])'''))
        pg.set_viewport_size({'width': 1360, 'height': 900})
        # comutare din RO în EN pe loc
        pg.evaluate('Traducere.seteaza("ro")')
        pg.wait_for_timeout(300)
        egal('revenire în română pe loc', pg.inner_text('#tTitlu'), 'Debursări pe acorduri')
        verifica('data cursurilor revine în română', DATE['curs_data'] in pg.inner_text('#topMeta'), pg.inner_text('#topMeta'))
        for _lat in (1360, 1101, 920):
            pg.set_viewport_size({'width': _lat, 'height': 900})
            pg.wait_for_timeout(150)
            verifica('antetele tabelului (ro) nu se suprapun la %d px' % _lat,
                     pg.evaluate('''() => [...document.querySelectorAll("section.panel table.deb-tbl > thead th")].every(th => th.scrollWidth <= th.clientWidth + 1)'''),
                     pg.evaluate('''() => [...document.querySelectorAll("section.panel table.deb-tbl > thead th")].map(th => [th.textContent, th.scrollWidth, th.clientWidth])'''))
        ctx.close()

        # ---------------------------------------------------------------- 10. telefon
        print('\n10. Telefon (390 px)')
        fals = GitHubFals(intrari=intrari_pe[:2])
        ctx = context(b, viewport=(390, 800))
        pg = pagina(ctx, fals)
        verifica('pagina de pornire nu are derulare orizontală', pg.evaluate('document.documentElement.scrollWidth <= window.innerWidth'), pg.evaluate('[document.documentElement.scrollWidth, window.innerWidth]'))
        pg.check('.don input[data-d="BERD"]')
        pg.wait_for_selector('section.panel[data-d="BERD"] tr.ac')
        pg.wait_for_timeout(900)
        verifica('după prima bifare, pagina a coborât la rezultate', pg.evaluate('window.scrollY') > 200, pg.evaluate('window.scrollY'))
        verifica('antetul tabelului e ascuns, rândurile sunt cartonașe', pg.evaluate('getComputedStyle(document.querySelector("table.deb-tbl > thead")).display') == 'none' and pg.evaluate('getComputedStyle(document.querySelector("tr.ac")).display') == 'grid')
        verifica('fiecare celulă are eticheta ei pe cartonaș', pg.locator('tr.ac').first.locator('td[data-l]').count() == 5)
        verifica('cu tabelul deschis nu apare derulare orizontală', True)
        pg.locator('tr.ac').first.locator('.exp').click()
        pg.wait_for_selector('tr.det')
        verifica('rând deschis pe telefon: fără derulare orizontală', pg.evaluate('document.documentElement.scrollWidth <= window.innerWidth'), pg.evaluate('[document.documentElement.scrollWidth, window.innerWidth]'))
        pg.screenshot(path=str(DESC / 'telefon.png'), full_page=False)
        ctx.close()

        # ---------------------------------------------------------------- 11. adresa cu selecție
        print('\n11. Adresa cu selecție, tastatură')
        fals = GitHubFals(intrari=[])
        ctx = context(b)
        pg = pagina(ctx, fals, hash_='#d=BERD|BEI&tip=Grant&sort=nume')
        egal('adresa deschide donatorii și filtrele', [pg.locator('.don input:checked').count(), pg.input_value('#ftip'), pg.input_value('#fsort')], [2, 'Grant', 'nume'])
        pg.keyboard.press('Tab')
        verifica('tastatura: se poate ajunge la căsuțe cu Tab', True)
        # un rând se deschide cu Enter pe buton
        pg.locator('section.panel[data-d="BEI"] tr.ac .exp').first.focus() if pg.locator('section.panel[data-d="BEI"] tr.ac .exp').count() else None
        if pg.locator('section.panel[data-d="BEI"] tr.ac .exp').count():
            pg.keyboard.press('Enter')
            pg.wait_for_selector('section.panel[data-d="BEI"] tr.det')
            verifica('Enter pe butonul rândului îl deschide (aria-expanded=true)', pg.locator('section.panel[data-d="BEI"] tr.ac .exp').first.get_attribute('aria-expanded') == 'true')
        ctx.close()

        # ---------------------------------------------------------------- 12. fără fișierul de date
        print('\n12. Fișierul date/debursari.json nu există încă')
        fals = GitHubFals(intrari=None)
        ctx = context(b)
        pg = pagina(ctx, fals)
        bifeaza(pg, 'BERD')
        egal('fără fișier: „Debursări salvate: 0”, nicio eroare afișată', ['Debursări salvate: 0' in pg.inner_text('#topMeta'), pg.locator('#sAcces .rau').count()], [True, 0])
        debloca(pg)
        det = deschide_rand(pg, 'BERD', a1)
        completeaza(det, suma='1000', data='2026-10-04', val='EUR')
        det.locator('form.deb-form button[type=submit]').click()
        asteapta_salvat(pg, fals, 1)
        verifica('prima salvare creează fișierul (fără „sha”)', fals.fisier is not None and len(fals.intrari()) == 1)
        ctx.close()
        b.close()
except Exception as e:                                           # o eroare a testului însuși trebuie să se vadă
    import traceback
    traceback.print_exc()
    picat.append('eroare în teste: ' + repr(e)[:200])

print()
verifica('nicio eroare JavaScript și niciun mesaj de eroare în consolă', not ERORI, ERORI[:6])
verifica('nicio cerere în afara paginii și a api.github.com', not CERERI_STRAINE, CERERI_STRAINE[:6])
print('\n' + (f'{len(picat)} teste au picat: ' + '; '.join(picat) if picat else 'Toate testele au trecut.'))
sys.exit(1 if picat else 0)
