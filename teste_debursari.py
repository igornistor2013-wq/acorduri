"""Testele paginii „Debursări pe acorduri” (debursari.html, debursari-ui.js, debursari.js).

    python teste_debursari.py             # logica pură (teste_debursari.js, cu Node) și fișierele de date
    python teste_debursari.py --browser   # plus: pagina în browser, cu un GitHub simulat în locul celui real

În browser nu se atinge GitHub-ul adevărat: toate cererile către api.github.com sunt preluate de un depozit simulat (GitHubFals), care
se poartă ca el: cod valid sau nu, drept de scriere sau doar de citire, „sha” la fiecare scriere, conflict (409) când fișierul s-a
schimbat între timp, cădere de rețea; raportul AMP live e simulat la fel (cade sau întoarce un CSV de probă). Cheile de probă sunt inventate.
Ce se verifică, pe scurt:
  · lista donatorilor, bifarea, tabelul cu cele șase coloane și butonul de detalii (proiectul, data efectivă de începere, data finalizării,
    tipul, suma proiectului, suma debursărilor) și cifrele lui, față de un calcul independent din date/acorduri_legare.json; descrierea (obiectivele) nu mai are coloană, apare sus în rândul deschis;
  · fără dubluri: fiecare act dintr-un singur rând, rândurile-umbrelă omise și enumerate cu motivul, denumiri deosebite la același donator;
  · obiectivele și datele: din surse oficiale (cu citat și adresă), din AMP (arhiva și raportul live, doar legături sigure; cele probabile
    doar ca indiciu), introduse în pagină (formularul „Date despre proiect”), cu prioritatea dintre ele; salvarea în date/debursari.json;
  · fără cod: doar citire, fără formulare și fără bannere pe acorduri; o singură deblocare (bara fixă de sus) pentru toate acordurile; cod greșit, fără drept de scriere, fără rețea;
  · după deblocare: editare în tabel a datei de început, a datei finalizării și a sumei proiectului, plus debursările;
  · adăugare, editare, ștergere de debursări → ce ajunge, de fapt, în fișierul date/debursari.json (și în mesajul commit-ului);
  · conflict la salvare (altcineva a scris între timp): nimic nu se pierde; coada de modificări nesalvate supraviețuiește reîncărcării;
  · codul păstrat cu PIN: nicăieri în clar; PIN greșit; „uită codul”;
  · fișierele Excel descărcate (pe donator, total, pe donatori), deschise cu openpyxl;
  · engleză, telefon (fără derulare orizontală), adresa cu selecția, tastatură, cereri doar către pagină, api.github.com și proxy-ul AMP.
Are nevoie de Node.js, de openpyxl și (pentru --browser) de Playwright.
"""
import base64, datetime, functools, hashlib, json, os, re, subprocess, sys, tempfile, threading, unicodedata
from collections import Counter
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
# date/proiecte_manual.json: în browser, testele generale îl înlocuiesc cu MANUAL_GOL (aceleași rânduri omise, dar fără obiective și date oficiale),
# ca rezultatele să nu depindă de cât s-a completat între timp; fișierul adevărat se verifică separat (secțiunea 16)
MANUAL_REAL = json.loads((AICI / 'date' / 'proiecte_manual.json').read_text(encoding='utf-8'))
MANUAL_GOL = {'omise': MANUAL_REAL.get('omise', []), 'proiecte': []}
OMISE_ACTE = {c for o in MANUAL_REAL.get('omise', []) for c in o['acte']}
OMISE_ID = {a['id'] for a in ACORDURI if any(x['act'] in OMISE_ACTE for x in a['acte'])}
RANDURI = [a for a in ACORDURI if a['id'] not in OMISE_ID]          # rândurile care apar în liste
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
    """Donatorii = finanțatorii acordului însuși (parteneriAcord), nu toți partenerii adunați din actele grupate."""
    v = []
    for x in (a.get('parteneriAcord') or a.get('parteneri') or '').split('/'):
        x = re.sub(r'\s+', ' ', x).strip()
        if x and x not in v:
            v.append(x)
    return v or ['(neidentificat)']


def acorduri_donator(d):
    return [a for a in RANDURI if d in donatori_acord(a)]


def cheie_nume(s):
    s = ''.join(c for c in unicodedata.normalize('NFD', s or '') if not unicodedata.combining(c)).lower()
    return re.sub(r'[^a-z0-9]+', ' ', s).strip()


def proiecte_unite(lista):
    """Proiectele cu componentă de grant și de împrumut dintr-o listă de acorduri (a unui donator): rândurile cu aceeași denumire între care sunt și grant,
    și împrumut. Pagina le arată ca un singur rând, cu sumele pe componente; acordurile lor se văd când proiectul se deschide. {cheia denumirii: [acorduri]}"""
    fam = {}
    for a in lista:
        fam.setdefault(cheie_nume(curata_nume(a.get('scurt') or a['nume'])), []).append(a)
    return {k: m for k, m in fam.items() if len(m) > 1 and any(x['categorie'] == 'Grant' for x in m) and any(x['categorie'] == 'Împrumut' for x in m)}


def in_proiecte_unite(lista):
    return {x['id'] for m in proiecte_unite(lista).values() for x in m}


def cheie_proiect_unit(donator, id_):
    """Cheia proiectului unit (la acest donator) din care face parte acordul, sau None."""
    for k, m in proiecte_unite(acorduri_donator(donator)).items():
        if any(x['id'] == id_ for x in m):
            return k
    return None


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

    def __init__(self, intrari=None, public=True, public_automat=True, proiecte=None):
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
            self.scrie(intrari, public=public, proiecte=proiecte or [])

    @staticmethod
    def _sha(t):
        return hashlib.sha1(t.encode('utf-8')).hexdigest()

    @staticmethod
    def text_din(intrari, proiecte=None):
        def lista(v):
            l = [json.dumps(e, ensure_ascii=False, separators=(',', ':')) for e in v]
            return '[' + ('\n' + ',\n'.join(l) + '\n' if l else '') + ']'
        return '{"versiune":1,"actualizat":"2026-10-26T09:00:00.000Z","intrari":' + lista(intrari) + (',"proiecte":' + lista(proiecte) if proiecte else '') + '}\n'

    def scrie(self, intrari, public=True, proiecte=None):
        if proiecte is None:                  # „altcineva” care adaugă o debursare nu șterge datele despre proiecte
            proiecte = self.proiecte()
        t = self.text_din(intrari, proiecte)
        self.fisier, self.sha = t, self._sha(t)
        if public:
            self.public_text = t

    def publica(self):
        self.public_text = self.fisier

    def intrari(self):
        return json.loads(self.fisier)['intrari'] if self.fisier else []

    def proiecte(self):
        return json.loads(self.fisier).get('proiecte', []) if self.fisier else []

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
# fără „?v=” browserul poate păstra ore în șir un debursari-ui.js vechi lângă o pagină nouă (se vedea doar butonul „Debursare”, fără creioane)
for fisier in ('debursari.js', 'debursari-ui.js'):
    verifica('debursari.html: „%s” se încarcă cu versiune (?v=AAAA-LL-ZZ, cu o literă la urmă dacă se schimbă de mai multe ori în aceeași zi), ca să nu rămână o variantă veche în cache' % fisier,
             re.search(r'<script src="%s\?v=\d{4}-\d{2}-\d{2}[a-z]?"></script>' % re.escape(fisier), html) is not None)
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
ERORI, CERERI_STRAINE, CERERI_AMP = [], [], []
BERD = acorduri_donator('BERD')
BEI = acorduri_donator('BEI')
# Chromium scrie în consolă orice răspuns 4xx și orice cerere întreruptă; aici sunt provocate de teste (cod greșit, fișier lipsă, conflict, cădere de rețea)
FARA_CONSOLA = re.compile(r'Failed to load resource.*(401|403|404|409|422|aborted)|net::ERR_FAILED|ERR_ABORTED|ERR_INTERNET_DISCONNECTED')


class AmpFals:
    """Proxy-ul AMP (amp.vivi.md) simulat. Implicit raportul live „cade”, ca din sandbox, iar pagina trece pe arhiva încorporată; cu `csv` îl
    întoarce; cu `harta` (AMP ID → activityId) răspunde și la lista de linkuri cerută de amp-linkuri.js."""

    def __init__(self, csv=None, harta=None):
        self.csv, self.harta, self.cereri = csv, harta, []

    def api(self, route):
        rq = route.request
        cors = {'Access-Control-Allow-Origin': '*', 'Access-Control-Allow-Headers': 'content-type', 'Access-Control-Allow-Methods': 'GET, POST, OPTIONS'}
        if rq.method == 'OPTIONS':
            return route.fulfill(status=204, headers=cors)
        self.cereri.append((rq.method, rq.url))
        CERERI_AMP.append((rq.method, rq.url))
        if '/rest/data/saikureport/export/csv/661' in rq.url and self.csv is not None:
            return route.fulfill(status=200, content_type='text/csv; charset=utf-8', body=self.csv, headers=cors)
        if rq.url.endswith('/rest/data/report/custom/paginate') and self.harta is not None:
            copii = [{'contents': {'[AMP ID]': {'displayedValue': k}}, 'owner': {'id': v}} for k, v in self.harta.items()]
            return route.fulfill(status=200, content_type='application/json', headers=cors,
                                 body=json.dumps({'page': {'totalPageCount': 1, 'pageArea': {'children': copii}}}))
        return route.abort()

    def livrate(self, parte):
        return [c for c in self.cereri if parte in c[1]]


def pagina(ctx, fals, hash_='', lang=None, ascunde_404=False, manual=None, amp=None, confirmari=None, arhiva=True, asteapta_amp=True):
    """Deschide pagina. `manual`: conținutul date/proiecte_manual.json (implicit MANUAL_GOL; 'real' = fișierul adevărat); `amp`: un AmpFals
    (implicit raportul live cade); `confirmari`: conținutul date/legaturi_amp.json (implicit cel adevărat); `arhiva=False`: arhiva AMP nu se încarcă."""
    pg = ctx.new_page()
    pg.on('pageerror', lambda e: ERORI.append('pageerror: ' + str(e)[:300]))
    pg.on('console', lambda m: ERORI.append('console: ' + m.text[:300]) if m.type == 'error' and not FARA_CONSOLA.search(m.text) else None)
    pg.amp = amp or AmpFals()

    def straine(url):
        if not (url.startswith(BAZA) or url.startswith('https://api.github.com/') or url.startswith('https://amp.vivi.md/') or url.startswith('data:') or url.startswith('blob:')):
            CERERI_STRAINE.append(url)
            return True
        return False
    ctx.route(lambda u: straine(u), lambda r: r.abort())
    ctx.route(re.compile(r'https://api\.github\.com/.*'), fals.api)
    ctx.route(re.compile(r'https://amp\.vivi\.md/.*'), pg.amp.api)
    ctx.route(re.compile(r'^' + re.escape(BAZA) + r'date/debursari\.json(\?.*)?$'), fals.public)     # doar copia publică, nu API-ul
    if manual != 'real':
        corp_manual = json.dumps(MANUAL_GOL if manual is None else manual)
        ctx.route(re.compile(r'^' + re.escape(BAZA) + r'date/proiecte_manual\.json(\?.*)?$'), lambda r: r.fulfill(status=200, content_type='application/json', body=corp_manual))
    if confirmari is not None:
        corp_conf = json.dumps(confirmari)
        ctx.route(re.compile(r'^' + re.escape(BAZA) + r'date/legaturi_amp\.json(\?.*)?$'), lambda r: r.fulfill(status=200, content_type='application/json', body=corp_conf))
    if not arhiva:
        ctx.route(re.compile(r'^' + re.escape(BAZA) + r'arhiva\.js(\?.*)?$'), lambda r: r.abort())
    url = BAZA + 'debursari.html' + ('?lang=' + lang if lang else '') + hash_
    pg.goto(url, wait_until='networkidle', timeout=60000)
    pg.wait_for_selector('.don', timeout=20000)
    if asteapta_amp:
        amp_gata(pg)
    return pg


def amp_gata(pg):
    """Așteaptă să se termine citirea datelor din AMP (arhiva + raportul live), reușită sau nu."""
    pg.wait_for_function('["gata", "eroare"].includes(window.DebursariUI.stare().amp)', timeout=90000)


_AMP_AST = {}


def amp_asteptat():
    """Ce spune amp-date.js, rulat în Node pe arhiva reală și pe registrul real (raportul live căzut): {'stare': …, 'peAcord': {id rând: {id, inceput, sfarsit, nivel, legatura}}}."""
    if not _AMP_AST:
        cod_js = r"""
const fs = require('fs'), vm = require('vm'), cale = process.argv[1];
process.chdir(cale);
global.LegaturaAmp = require(cale + '/legatura-amp.js');
const A = require(cale + '/amp-date.js'), D = require(cale + '/debursari.js');
const reg = JSON.parse(fs.readFileSync('date/acorduri_legare.json', 'utf8'));
const baza = D.pregateste(reg, JSON.parse(fs.readFileSync('date/proiecte_manual.json', 'utf8')));
const rows = reg.acorduri.filter(x => baza.peId.has(x.id));
const ARCH = vm.runInNewContext(fs.readFileSync('arhiva.js', 'utf8') + ';ARCHIVE');
A.incarca({ acorduri: rows, confirmari: JSON.parse(fs.readFileSync('date/legaturi_amp.json', 'utf8')), arhiva: ARCH,
            fetch: async () => { throw new TypeError('Failed to fetch'); } }).then(r => {
  const o = {}; r.peAcord.forEach((v, k) => { o[k] = v; });
  process.stdout.write(JSON.stringify({ stare: r.stare, peAcord: o, n: rows.length }));
});
"""
        r = subprocess.run(['node', '-e', cod_js, str(AICI)], capture_output=True, text=True)
        _AMP_AST.update(json.loads(r.stdout))
    return _AMP_AST


def arhiva_amp():
    """Înregistrările din arhiva.js, citite independent (în Python): {AMP ID: înregistrare}."""
    t = (AICI / 'arhiva.js').read_text(encoding='utf-8')
    i = t.index('const ARCHIVE')
    return {x['id']: x for x in json.loads(t[t.index('[', i):t.rindex(']') + 1])}


def iso_din_amp(v):
    """„15/09/2020” (ZZ/LL/AAAA, ca în arhivă) → „2020-09-15”; gol → None."""
    m = re.match(r'^(\d{1,2})/(\d{1,2})/(\d{4})$', (v or '').strip())
    return '%s-%02d-%02d' % (m.group(3), int(m.group(2)), int(m.group(1))) if m else None


def fmt_data_iso(v):
    """2026-03-15 → 15.03.2026; 2026-03 → 03.2026; 2026 → 2026 (cum le scrie pagina)."""
    return '.'.join(reversed(v.split('-'))) if v else ''


def celula_data(r, k):
    """(atributul datetime sau None, textul) pentru celula k (2 = început, 3 = finalizare) a unui rând din tabel."""
    c = r.locator('td').nth(k)
    t = c.locator('time')
    return (t.get_attribute('datetime') if t.count() else None, c.inner_text().replace('\xa0', ' ').strip())


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
    r = pg.locator('section.panel[data-d="%s"] tr.ac[data-k="%s"]' % (donator, donator + '|' + id_))
    if r.count() == 0:                       # acordul face parte dintr-un proiect cu grant și împrumut, închis: se deschide proiectul (rândul lui apare dedesubt)
        cheie = cheie_proiect_unit(donator, id_)
        h = pg.locator('section.panel[data-d="%s"] tr.pg[data-gr="%s"]' % (donator, donator + '|' + cheie)) if cheie else None
        if h is not None and h.count() and 'deschis' not in (h.get_attribute('class') or ''):
            h.locator('.exp').click()
    return r


def nume_rand(r):
    """Denumirea cu mențiunea de deosebire, cum o scrie și Excel-ul (din eticheta butonului de detalii): rândul poate fi o componentă a unui proiect unit, care arată doar „Grant, 2023”."""
    return r.locator('.exp').get_attribute('aria-label').split(': ', 1)[1]


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


def completeaza_proiect(det, obiective=None, inceput=None, sfarsit=None, nota=None):
    """Scrie în formularul „Date despre proiect” al unui rând deschis (doar câmpurile date)."""
    f = det.locator('form.proj-form')
    for nume, val in (('obiective', obiective), ('inceput', inceput), ('sfarsit', sfarsit), ('nota', nota)):
        if val is not None:
            f.locator('[name=%s]' % nume).fill(val)
    return f


def trimite_proiect(det):
    det.locator('form.proj-form button[type=submit]').click()


def descriere_rand(pg, r):
    """Descrierea succintă (obiectivele) nu mai are coloană în tabel: se vede sus, în partea deschisă a rândului.
    Deschide rândul (dacă era închis), citește blocul și îl închide la loc.
    Întoarce {'text', 'gol', 'src' (etichetele de sursă), 'href'/'n_link'/'t_link' (eticheta „sursă oficială”, cu adresa documentului)}."""
    k = r.get_attribute('data-k')
    era = 'deschis' in (r.get_attribute('class') or '')
    if not era:
        r.locator('.exp').click()
    det = pg.locator('tr.det[data-k="%s"]' % k)
    det.wait_for()
    b = det.locator('.det-desc')
    lnk = b.locator('a.src.s-oficial')
    rez = {'text': b.locator('.dd-t').inner_text().strip(), 'gol': b.locator('.dd-t.gol').count() == 1,
           'src': [x.strip() for x in b.locator('.psrc .src').all_inner_texts()],
           'n_link': lnk.count(), 'href': lnk.get_attribute('href') if lnk.count() else None, 't_link': lnk.inner_text().strip() if lnk.count() else None}
    if not era:
        pg.locator('tr.ac[data-k="%s"] .exp' % k).click()
        det.wait_for(state='detached')
    return rez


def sursa_celulei(r, k):
    """Etichetele de sursă („sursă oficială”, „AMP”, „introdus de utilizator”) din celula k a unui rând."""
    return [x.strip() for x in r.locator('td').nth(k).locator('.src').all_inner_texts()]


def toate_foile(cale):
    """Toate celulele unui fișier Excel, ca text (pentru a căuta în note)."""
    wb = openpyxl.load_workbook(cale)
    return [str(c.value) for ws in wb for row in ws.iter_rows() for c in row if c.value is not None]


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


DOAR = set(sys.argv[sys.argv.index('--doar') + 1].split(',')) if '--doar' in sys.argv else None      # ex.: --browser --doar 13,14


def rulez(n):
    return DOAR is None or str(n) in DOAR


try:
    with sync_playwright() as p:
        b = p.chromium.launch()

        if DOAR is None:                                    # --doar 13,14: doar secțiunile numite (pentru depanare); altfel, toate
            # ---------------------------------------------------------------- 1. lista donatorilor și bifarea
            print('\n1. Donatorii și tabelul')
            fals = GitHubFals(intrari=[])
            ctx = context(b)
            pg = pagina(ctx, fals)
            tokeni = pg.locator('.don input').evaluate_all('l => l.map(i => i.getAttribute("data-d"))')
            donatori_asteptati = {d for a in RANDURI for d in donatori_acord(a)}
            egal('lista are toți donatorii din registru (%d)' % len(donatori_asteptati), set(tokeni), donatori_asteptati)
            egal('ordinea implicită: după numărul de proiecte (primul = cel cu cele mai multe)', tokeni[0],
                 max(donatori_asteptati, key=lambda d: (len(acorduri_donator(d)), d)) if True else '')
            egal('nicio bifare la început: panoul cere să alegi un donator', pg.locator('#sRez .gol-msg b').inner_text(), 'Alege un donator din listă')
            kpi0 = pg.locator('.kpi .val').all_inner_texts()
            egal('indicatorii de la început: toate acordurile din liste (fără cele %d rânduri-umbrelă)' % len(OMISE_ID), kpi0[0], str(len(RANDURI)))
            pg.fill('#dq', 'banca')
            pg.wait_for_timeout(300)
            filtrati = pg.locator('.don input').evaluate_all('l => l.map(i => i.getAttribute("data-d"))')
            verifica('căutarea „banca” lasă donatorii cu „banca” în denumire (BERD, BEI, BIRD…)', {'BERD', 'BEI', 'BIRD'} <= set(filtrati) and 'UE' not in filtrati, filtrati)
            pg.fill('#dq', '')
            pg.wait_for_timeout(300)

            bifeaza(pg, 'BERD')
            antete = pg.locator('section.panel[data-d="BERD"] table.deb-tbl > thead th').all_inner_texts()
            egal('tabelul are cele șase coloane (+ butonul de detalii); descrierea nu mai are coloană, apare când deschizi proiectul', [x.strip().split('\n')[0].strip() for x in antete[:6]],
                 ['PROIECTUL', 'DATA EFECTIVĂ DE ÎNCEPERE', 'DATA FINALIZĂRII', 'TIP DE FINANȚARE', 'SUMA PROIECTULUI', 'SUMA DEBURSĂRILOR'])
            verifica('în tabel nu mai există coloana „Descriere succintă”, nici text de descriere în rânduri', len(antete) == 7 and 'DESCRIERE' not in ' '.join(antete).upper() and pg.locator('section.panel[data-d="BERD"] tr.ac .pdesc').count() == 0, antete)
            egal('șapte celule pe rând (șase coloane + butonul de detalii)', pg.locator('section.panel[data-d="BERD"] tr.ac').first.locator('td').count(), 7)
            U_BERD, IN_BERD = proiecte_unite(BERD), in_proiecte_unite(BERD)
            egal('tabelul BERD: un rând pe acord, în afară de proiectele cu grant și împrumut, care sunt un singur rând fiecare (%d rânduri simple + %d proiecte unite, cu %d acorduri; acordurile lor apar când proiectul se deschide)' % (len(BERD) - len(IN_BERD), len(U_BERD), len(IN_BERD)),
                 [pg.locator('section.panel[data-d="BERD"] tr.ac').count(), pg.locator('section.panel[data-d="BERD"] tr.pg').count()], [len(BERD) - len(IN_BERD), len(U_BERD)])
            sus = pg.locator('.kpi .val').all_inner_texts()
            egal('indicatorul „Proiecte” = rândurile lui BERD', sus[0], str(len(BERD)))
            asteptat_suma = rotunjit(suma_numarata(BERD))
            verifica('„Suma proiectelor” din indicator = calculul independent (%s EUR)' % fmt_ro(asteptat_suma, 0),
                     fmt_ro(asteptat_suma, 0) in pg.locator('.kpi .sub').all_inner_texts()[1], pg.locator('.kpi .sub').all_inner_texts())
            # primul rând, comparat cu datele
            lista_sumă = sorted([a for a in BERD if a['id'] not in IN_BERD], key=lambda a: -(eur(a) if eur(a) is not None else -1))       # rândurile simple; proiectele unite au rând propriu (secțiunea 19)
            prim = lista_sumă[0]
            r0 = pg.locator('section.panel[data-d="BERD"] tr.ac').first
            _nume0 = curata_nume(prim.get('scurt') or prim['nume'])
            _afis0 = r0.locator('.pname').inner_text()
            verifica('primul rând (cea mai mare sumă): denumirea din registru, cu o mențiune de deosebire când același donator are alte rânduri cu aceeași denumire',
                     _afis0 == _nume0 or (_afis0.startswith(_nume0 + ' (') and _afis0.endswith(')')), _afis0)
            egal('primul rând: tipul de finanțare', r0.locator('.tag').inner_text(), prim['categorie'])
            verifica('primul rând: suma proiectului', fmt_bani_ro(prim['suma']['v']) in r0.locator('td').nth(4).inner_text().replace('\xa0', ' '), r0.locator('td').nth(4).inner_text())
            egal('primul rând: fără obiective cunoscute, la deschidere descrierea spune „Obiective neintroduse” (nu o frază alcătuită din titlu și date)', descriere_rand(pg, r0)['text'], 'Obiective neintroduse')
            verifica('primul rând: la debursări apare „—” (nicio debursare încă)', '—' in r0.locator('td').nth(5).inner_text())
            AMP_AST = amp_asteptat()
            for _k, _camp in ((1, 'inceput'), (2, 'sfarsit')):                 # datele: doar din AMP și doar la legături sigure; altfel „—”
                _m = AMP_AST['peAcord'].get(prim['id'])
                _asteptat = _m[_camp] if _m and _m['nivel'] == 'sigur' and _m.get(_camp) else None
                egal('primul rând: celula „%s” (AMP: %s)' % ('început' if _k == 1 else 'finalizare', _asteptat or 'fără dată'), celula_data(r0, _k)[0] if _asteptat else celula_data(r0, _k)[1],
                     _asteptat if _asteptat else '—')
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
            egal('după „Șterge filtrele” se întorc toate rândurile (simple și proiecte unite)', [pg.locator('section.panel[data-d="BERD"] tr.ac').count(), pg.locator('section.panel[data-d="BERD"] tr.pg').count()], [len(BERD) - len(IN_BERD), len(U_BERD)])
            ctx.close()

            # ---------------------------------------------------------------- 2. câmpuri blocate, cod greșit
            print('\n2. Fără cod: doar citire, o singură deblocare pentru toate acordurile; cod greșit, fără drept, fără rețea')
            fals = GitHubFals(intrari=[])
            ctx = context(b)
            pg = pagina(ctx, fals)
            bifeaza(pg, 'BERD')
            a0 = BERD[0]
            det = deschide_rand(pg, 'BERD', a0)
            verifica('blocat: în detaliile acordului nu apare niciun formular, nici vreun banner de blocare (câmpurile nu se repetă la fiecare acord)', det.locator('form').count() == 0 and det.locator('.blocat').count() == 0 and pg.locator('#sRez .blocat').count() == 0, det.locator('form').count())
            det1 = deschide_rand(pg, 'BERD', BERD[1])
            verifica('blocat, al doilea acord deschis: la fel, fără formulare și fără banner', det1.locator('form').count() == 0 and pg.locator('#sRez form').count() == 0 and pg.locator('#sRez [data-act="unlock"]').count() == 0)
            egal('blocat: un singur buton de deblocare în toată pagina, în bara de acces', [pg.locator('[data-act="unlock"]').count(), pg.locator('#sAcces [data-act="unlock"]').count()], [1, 1])
            verifica('blocat: fără creioane de editare și fără butonul „Debursare” în tabel', pg.locator('#sRez .edt').count() == 0 and pg.locator('#sRez [data-act="adauga"]').count() == 0)
            verifica('blocat: detaliile se văd în continuare (datele proiectului, datele despre acord), doar în citire', det.locator('.det-proiect .dlp').count() == 1 and det.locator('.det-info').count() == 1 and det.locator('.det-grid.solo').count() == 1)
            egal('blocat: bara de acces spune „Doar citire”', pg.locator('#sAcces b').inner_text(), 'Doar citire')
            verifica('blocat: bara spune că un singur cod deblochează totul (început, finalizare, sumă, debursări)', all(x in pg.locator('#sAcces .acces-txt').inner_text() for x in ('Un singur cod', 'toate acordurile', 'data de început', 'data finalizării', 'suma proiectului', 'debursările')), pg.locator('#sAcces .acces-txt').inner_text())
            egal('bara de acces e „fixă” (position: sticky)', pg.evaluate('getComputedStyle(document.querySelector("#sAcces")).position'), 'sticky')
            pg.evaluate('window.scrollTo(0, Math.max(0, document.documentElement.scrollHeight / 2))')
            pg.wait_for_timeout(200)
            sus = pg.evaluate('[document.querySelector("#sAcces").getBoundingClientRect().top, window.scrollY, document.querySelector("#sAcces").getBoundingClientRect().height]')
            verifica('bara de acces rămâne în capul ferestrei la derulare (deblocarea e la îndemână de la orice acord)', -1 <= sus[0] <= 1 and sus[1] > 300, sus)
            verifica('înălțimea barei e măsurată (--acces-h), ca lista donatorilor să se așeze sub ea', pg.evaluate('parseInt(getComputedStyle(document.documentElement).getPropertyValue("--acces-h"))') >= 30)
            pg.evaluate('window.scrollTo(0, 0)')
            verifica('blocat: nicio cerere către GitHub până nu se cere deblocarea', len(fals.cereri) == 0, fals.cereri)
            pg.click('#sAcces [data-act="unlock"]')
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
            egal('bara de acces spune „Editare deblocată pentru toate acordurile”', pg.locator('#sAcces b').inner_text(), 'Editare deblocată pentru toate acordurile')
            stoc = pg.evaluate('JSON.stringify([Object.entries(localStorage), Object.entries(sessionStorage)])')
            verifica('cheia nu e în localStorage/sessionStorage', TOKEN not in stoc, stoc[:200])
            verifica('cheia nu e nicăieri în pagina HTML', TOKEN not in pg.content())
            verifica('citirea fișierului s-a făcut cu cheia în antetul Authorization, doar către api.github.com',
                     all(c[1].startswith('https://api.github.com/') for c in fals.cereri) and any(c[2] == 'Bearer ' + TOKEN for c in fals.cereri))
            a1 = [a for a in BERD if eur(a)][0]
            det = deschide_rand(pg, 'BERD', a1)
            campuri = det.locator('form.deb-form input, form.deb-form select, form.deb-form button[type=submit]')
            verifica('deblocat: câmpurile formularului sunt active', all(campuri.nth(i).is_enabled() for i in range(campuri.count())))
            altul = [a for a in BERD if a['id'] != a1['id']][0]
            det2 = deschide_rand(pg, 'BERD', altul)
            tot2 = det2.locator('form input, form select, form textarea, form button[type=submit]')
            verifica('o singură deblocare pentru toate acordurile: alt acord are formularele (debursare și proiect) active, fără alt cod', det2.locator('form.deb-form').count() == 1 and det2.locator('form.proj-form').count() == 1 and tot2.count() >= 10 and all(tot2.nth(i).is_enabled() for i in range(tot2.count())) and pg.locator('[data-act="unlock"]').count() == 0, tot2.count())
            verifica('formularul de proiect are și suma proiectului, cu valută', det2.locator('form.proj-form [name=suma]').count() == 1 and det2.locator('form.proj-form [name=val]').count() == 1)
            rand_acord(pg, 'BERD', altul['id']).locator('.exp').click()
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
            verifica('formularul păstrează data și valuta și golește suma', det.locator('form.deb-form [name=suma]').input_value() == '' and det.locator('form.deb-form [name=data]').input_value() == '2026-10-01')
            # cifrele
            eur_in = 1250000.5
            verifica('rândul: suma debursată în euro și numărul de debursări',
                     fmt_ro(rotunjit(eur_in), 0) in rand_acord(pg, 'BERD', a1['id']).locator('td').nth(5).inner_text() and '1 debursare' in rand_acord(pg, 'BERD', a1['id']).locator('td').nth(5).inner_text(),
                     rand_acord(pg, 'BERD', a1['id']).locator('td').nth(5).inner_text())
            if a1['inTotal'] == 'numarat':
                pct = eur_in / eur(a1) * 100
                verifica('rândul: procentul din suma proiectului', ('%s%%' % fmt_ro(pct, 1)) in rand_acord(pg, 'BERD', a1['id']).locator('td').nth(5).inner_text(), rand_acord(pg, 'BERD', a1['id']).locator('td').nth(5).inner_text())
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
            verifica('„Blochează” scoate din nou formularele, la toate acordurile deodată', not deblocat(pg) and pg.locator('section.panel[data-d="BERD"] tr.det form').count() == 0 and pg.locator('#sRez .edt').count() == 0 and pg.locator('#sAcces [data-act="unlock"]').count() == 1)
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
                     fmt_bani_ro(intrari_pe[0]['suma']) in rand_acord(pg, 'BERD', pe[0]['id']).locator('td').nth(5).inner_text() or pe[0]['suma']['val'] == 'EUR')
            verifica('panoul „Debursări fără acord în registru” arată orfana', 'Acord dispărut din registru' in pg.inner_text('#sOrfane') and '5.000 EUR' in pg.inner_text('#sOrfane'), pg.inner_text('#sOrfane'))
            verifica('orfana nu intră în totalul donatorului', fmt_ro(5000 + deb_total, 0) not in pg.inner_text('section.panel[data-d="BERD"] .dsum'))
            # filtrul „doar cu debursări”
            pg.select_option('#fdeb', 'cu')
            pg.wait_for_timeout(250)
            egal('filtrul „Doar cu debursări”: două rânduri', pg.locator('section.panel[data-d="BERD"] tr.ac').count(), 2)
            pg.select_option('#fdeb', 'fara')
            pg.wait_for_timeout(250)
            _fara = [a for a in BERD if a['id'] not in {x['id'] for x in pe}]
            egal('filtrul „Doar fără debursări”: restul (rânduri simple + proiecte unite, cu grant și împrumut)', [pg.locator('section.panel[data-d="BERD"] tr.ac').count(), pg.locator('section.panel[data-d="BERD"] tr.pg').count()],
                 [len(_fara) - len(in_proiecte_unite(_fara)), len(proiecte_unite(_fara))])
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
            verifica('Excel pe donator: antetul are coloanele cerute (obiective, data de început, data finalizării, sursa lor)', antet and all(x in antet for x in
                     ['Proiectul', 'Descriere succintă (obiectivele proiectului)', 'Data efectivă de începere', 'Data finalizării', 'Tip de finanțare', 'Suma proiectului', 'Debursat (echivalent EUR)',
                      'Sursa obiectivelor și a datelor']), antet)
            verifica('Excel pe donator: coloanele de obiective și date vin imediat după proiect, în ordinea cerută', antet and antet.index('Proiectul') + 1 == antet.index('Descriere succintă (obiectivele proiectului)') and
                     antet.index('Descriere succintă (obiectivele proiectului)') + 1 == antet.index('Data efectivă de începere') and antet.index('Data efectivă de începere') + 1 == antet.index('Data finalizării'), antet)
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
            egal('antetul de tabel în engleză', [x.strip().split('\n')[0].strip() for x in pg.locator('section.panel[data-d="BERD"] table.deb-tbl > thead th').all_inner_texts()[:6]],
                 ['PROJECT', 'ACTUAL START DATE', 'COMPLETION DATE', 'TYPE OF FINANCING', 'PROJECT AMOUNT', 'DISBURSED AMOUNT'])
            egal('descrierea fără obiective, în engleză (la deschidere)', descriere_rand(pg, pg.locator('section.panel[data-d="BERD"] tr.ac').first)['text'], 'Objectives not entered')
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
            verifica('fiecare celulă are eticheta ei pe cartonaș', pg.locator('tr.ac').first.locator('td[data-l]').count() == 6)
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

        # ================================================================ obiective și date despre proiecte
        BY_ID = {a['id']: a for a in ACORDURI}
        rb = sorted(BERD, key=lambda a: -(eur(a) if eur(a) is not None else -1))
        pA, pB, pC = rb[0], rb[1], rb[2]
        SURSA_A = 'https://documents.example.org/proiect-a.pdf'
        SURSA_B = 'https://documents.example.org/proiect-b.html'
        OBI_A = {'ro': 'Modernizarea rețelei de drumuri naționale și creșterea siguranței rutiere.', 'en': 'Modernising the national road network and improving road safety.'}
        CITAT_A = 'The Project aims to modernise the national road network.'
        OF = {'omise': MANUAL_REAL['omise'], 'proiecte': [
            {'acte': [pA['acte'][-1]['act']], 'obiective': OBI_A, 'inceput': '2019-05-14', 'sfarsit': '2027-12', 'sursa': SURSA_A,
             'citat': CITAT_A, 'nota': 'data efectivă a semnării contractului de lucrări'},
            {'acte': [pB['acte'][0]['act']], 'sfarsit': '2030', 'sursa': SURSA_B, 'citat': 'The loan closing date is 31 December 2030.'},
            {'acte': ['HG0000/1900'], 'obiective': {'ro': 'Intrare fără rând în registru'}, 'sursa': 'https://documents.example.org/x', 'citat': 'un citat suficient de lung'},
            {'acte': [pC['acte'][0]['act']], 'obiective': {'ro': 'Citat prea scurt'}, 'sursa': 'https://documents.example.org/y', 'citat': 'scurt'}]}

        # ---------------------------------------------------------------- 13. obiective și date din surse oficiale
        if rulez(13):
            print('\n13. Obiective și date din surse oficiale (adresă și citat exact)')
            fals = GitHubFals(intrari=[])
            ctx = context(b)
            pg = pagina(ctx, fals, hash_='#d=BERD', manual=OF, arhiva=False)
            rA, rB, rC = (rand_acord(pg, 'BERD', x['id']) for x in (pA, pB, pC))
            dA = descriere_rand(pg, rA)
            egal('sursă oficială: descrierea (la deschiderea proiectului) = obiectivele proiectului', dA['text'], OBI_A['ro'])
            verifica('sursă oficială: eticheta „sursă oficială” duce la document', dA['n_link'] == 1 and dA['href'] == SURSA_A and dA['t_link'] == 'sursă oficială',
                     (dA['n_link'], dA['href']))
            egal('data efectivă de începere: 14.05.2019 (datetime 2019-05-14)', [celula_data(rA, 1)[0], celula_data(rA, 1)[1].split('\n')[0]], ['2019-05-14', '14.05.2019'])
            egal('data finalizării parțială: doar luna și anul, cât spune sursa', [celula_data(rA, 2)[0], celula_data(rA, 2)[1].split('\n')[0]], ['2027-12', '12.2027'])
            egal('etichetele de sursă din celulele de date', [sursa_celulei(rA, 1), sursa_celulei(rA, 2)], [['sursă oficială'], ['sursă oficială']])
            verifica('rând cu o singură dată oficială: fără obiective, „Obiective neintroduse”', descriere_rand(pg, rB)['gol'])
            egal('data finalizării, doar anul (2030), din sursa oficială', [celula_data(rB, 2)[0], celula_data(rB, 2)[1].split('\n')[0]], ['2030', '2030'])
            egal('începutul necunoscut: „—”, fără dată inventată', [celula_data(rB, 1)[0], celula_data(rB, 1)[1]], [None, '—'])
            egal('rând fără nicio sursă: „Obiective neintroduse” și două „—”', [descriere_rand(pg, rC)['text'], celula_data(rC, 1)[1], celula_data(rC, 2)[1]], ['Obiective neintroduse', '—', '—'])
            dsum = pg.locator('section.panel[data-d="BERD"] .dsum').inner_text()
            verifica('antetul donatorului: acoperirea (obiective 1, început 1, finalizare 2)', all(x in dsum for x in ('obiective 1/%d' % len(BERD), 'început 1/%d' % len(BERD), 'finalizare 2/%d' % len(BERD))), dsum)
            # intrările respinse sau fără rând se spun, nu se ascund
            om = pg.locator('#sOmise details.omise.avert')
            verifica('intrările din fișier care nu s-au folosit (citat prea scurt, act negăsit) sunt anunțate', om.count() == 1 and '2 intrări' in om.locator('summary').inner_text(), om.count())
            om.locator('summary').click()
            verifica('lista celor nefolosite spune de ce', 'lipsește sursa' in om.inner_text() and 'HG0000/1900' in om.inner_text(), om.inner_text()[:300])
            # detaliile: citatul exact și documentul
            det = deschide_rand(pg, 'BERD', pA)
            dlp = det.locator('.det-proiect .dlp').inner_text()
            verifica('detalii: citatul exact din sursă, adresa documentului (gazda) și nota', CITAT_A in dlp and 'documents.example.org' in dlp and 'data efectivă a semnării contractului de lucrări' in dlp, dlp[:400])
            verifica('detalii: linkul spre document are adresa completă', det.locator('.det-proiect .citat a').first.get_attribute('href') == SURSA_A)
            # căutarea merge și în obiective (română și engleză)
            pg.fill('#q', 'siguranței rutiere')
            pg.wait_for_timeout(300)
            egal('căutarea în obiective (română): rămâne rândul cu acele obiective', pg.locator('section.panel[data-d="BERD"] tr.ac').evaluate_all('l => l.map(r => r.getAttribute("data-k"))'), ['BERD|' + pA['id']])
            pg.fill('#q', 'modernising national road')
            pg.wait_for_timeout(300)
            egal('căutarea în obiective (engleză): același rând', pg.locator('section.panel[data-d="BERD"] tr.ac').evaluate_all('l => l.map(r => r.getAttribute("data-k"))'), ['BERD|' + pA['id']])
            pg.fill('#q', '')
            # Excel: obiectivele, datele, sursa cu adresa documentului
            with pg.expect_download(timeout=60000) as d:
                pg.click('section.panel[data-d="BERD"] [data-act="excel-donator"]')
            cale = DESC / 'berd-oficiale.xlsx'
            d.value.save_as(str(cale))
            ws = openpyxl.load_workbook(cale)['BERD']
            antet, rand_antet = None, None
            for r in ws.iter_rows(min_row=1, max_row=12):
                if 'Proiectul' in [c.value for c in r]:
                    antet, rand_antet = [c.value for c in r], r[0].row
                    break
            iP, iD, iI, iF, iS = (antet.index(x) for x in ('Proiectul', 'Descriere succintă (obiectivele proiectului)', 'Data efectivă de începere', 'Data finalizării', 'Sursa obiectivelor și a datelor'))
            nume_A = nume_rand(rA)
            ra = [r for r in ws.iter_rows(min_row=rand_antet + 1) if r[iP].value == nume_A]
            verifica('Excel: rândul proiectului cu surse oficiale există o dată', len(ra) == 1, [r[iP].value for r in ws.iter_rows(min_row=rand_antet + 1, max_row=rand_antet + 4)])
            ra = ra[0]
            egal('Excel: obiectivele; data întreagă e dată adevărată (se sortează), cea doar cu luna și anul rămâne text', [ra[iD].value, ra[iI].value, ra[iF].value], [OBI_A['ro'], datetime.datetime(2019, 5, 14), '12.2027'])
            verifica('Excel: data întreagă are format de dată (zz.ll.aaaa)', ra[iI].number_format.lower().replace('/', '.') in ('dd.mm.yyyy', 'dd\\.mm\\.yyyy'), ra[iI].number_format)
            egal('Excel: sursa spune „sursă oficială”, cu hyperlink spre document', [ra[iS].value, ra[iS].hyperlink.target if ra[iS].hyperlink else None], ['sursă oficială', SURSA_A])
            nume_C = nume_rand(rC)
            rc_x = [r for r in ws.iter_rows(min_row=rand_antet + 1) if r[iP].value == nume_C][0]
            verifica('Excel: proiectul fără surse are celulele goale (nu „—” și nu text inventat)', [rc_x[iD].value, rc_x[iI].value, rc_x[iF].value, rc_x[iS].value] == [None, None, None, None] or
                     [rc_x[iD].value, rc_x[iI].value, rc_x[iF].value, rc_x[iS].value] == ['', '', '', ''], [rc_x[iD].value, rc_x[iI].value, rc_x[iF].value, rc_x[iS].value])
            note = ' '.join(toate_foile(cale))
            verifica('Excel: notele explică de unde vin obiectivele și datele, și spun ce rânduri-umbrelă lipsesc', 'Descrierea succintă e obiectivele proiectului' in note and 'rânduri-umbrelă' in note, note[:200])
            ctx.close()
            # engleză: obiectivele în engleză, etichetele în engleză
            fals = GitHubFals(intrari=[])
            ctx = context(b)
            pg = pagina(ctx, fals, hash_='#d=BERD', lang='en', manual=OF, arhiva=False)
            rA = rand_acord(pg, 'BERD', pA['id'])
            egal('engleză: obiectivele în engleză', descriere_rand(pg, rA)['text'], OBI_A['en'])
            egal('engleză: etichetele de sursă', [descriere_rand(pg, rA)['src'], sursa_celulei(rA, 1)], [['official source'], ['official source']])
            egal('engleză: data de început afișată la fel (zi.lună.an)', celula_data(rA, 1)[1].split('\n')[0], '14.05.2019')
            ctx.close()

        # ---------------------------------------------------------------- 14. formularul „Date despre proiect”
        if rulez(14):
            print('\n14. Date despre proiect scrise în pagină: validare, salvare, prioritate, ștergere')
            fals = GitHubFals(intrari=[])
            ctx = context(b)
            pg = pagina(ctx, fals, hash_='#d=BERD', manual=OF, arhiva=False)
            debloca(pg)
            detC = deschide_rand(pg, 'BERD', pC)
            fp = detC.locator('form.proj-form')
            cp = fp.locator('input, textarea, button[type=submit]')
            verifica('deblocat: formularul de proiect e activ', cp.count() >= 5 and all(cp.nth(i).is_enabled() for i in range(cp.count())), cp.count())
            egal('formularul e gol pentru un proiect fără date introduse', [fp.locator('[name=%s]' % n).input_value() for n in ('obiective', 'inceput', 'sfarsit', 'nota')], ['', '', '', ''])
            detC.locator('form.proj-form button[type=submit]').click()
            pg.wait_for_timeout(250)
            verifica('formular gol: „Completează cel puțin un câmp”, nimic scris', 'Completează cel puțin un câmp' in detC.locator('form.proj-form .ferr').inner_text() and fals.n_put == 0,
                     detC.locator('form.proj-form .ferr').inner_text())
            for inc, sfa, text_ in [('abc', '', 'Nu înțeleg data de început'), ('', '31.02.2020', 'Nu înțeleg data finalizării'), ('01.01.2020', '01.01.2019', 'nu poate fi înaintea')]:
                completeaza_proiect(detC, obiective='', inceput=inc, sfarsit=sfa)
                antes = fals.n_put
                trimite_proiect(detC)
                pg.wait_for_timeout(250)
                verifica('validare „%s / %s”: „%s”, fără scriere' % (inc, sfa, text_), text_ in detC.locator('form.proj-form .ferr').inner_text() and fals.n_put == antes, detC.locator('form.proj-form .ferr').inner_text())
            verifica('câmpul cu eroare are aria-invalid', detC.locator('form.proj-form [aria-invalid="true"]').count() >= 1)
            # salvare corectă: spațiile se curăță, datele pot fi parțiale
            completeaza_proiect(detC, obiective='Sprijin pentru reforma sectorului   energetic și securitatea aprovizionării.', inceput='15.03.2024', sfarsit='2028', nota='raportul anual, pag. 3')
            trimite_proiect(detC)
            asteapta_salvat(pg, fals, 1)
            e = fals.proiecte()[0] if fals.proiecte() else {}
            egal('fișierul: rândul, actele, obiectivele (spații curățate), datele (ISO, parțiale) și nota', [e.get('acord'), e.get('acte'), e.get('obiective'), e.get('inceput'), e.get('sfarsit'), e.get('nota')],
                 [pC['id'], [x['act'] for x in pC['acte']][:12], 'Sprijin pentru reforma sectorului energetic și securitatea aprovizionării.', '2024-03-15', '2028', 'raportul anual, pag. 3'])
            verifica('înregistrarea are id „p…”, numele rândului și ora salvării', str(e.get('id', '')).startswith('p') and e.get('nume') and e.get('la'), e)
            verifica('mesajul commit-ului: „Date proiecte: salvat: …”', fals.commituri[0].startswith('Date proiecte: salvat: '), fals.commituri)
            verifica('lista de debursări din fișier nu s-a atins', fals.intrari() == [])
            rC = rand_acord(pg, 'BERD', pC['id'])
            egal('tabel: obiectivele introduse', descriere_rand(pg, rC)['text'], 'Sprijin pentru reforma sectorului energetic și securitatea aprovizionării.')
            egal('tabel: datele introduse, cu eticheta „introdus de utilizator”', [celula_data(rC, 1)[1].split('\n')[0], celula_data(rC, 2)[1].split('\n')[0], descriere_rand(pg, rC)['src'], sursa_celulei(rC, 1), sursa_celulei(rC, 2)],
                 ['15.03.2024', '2028', ['introdus de utilizator'], ['introdus de utilizator'], ['introdus de utilizator']])
            verifica('formularul se reia din ce s-a salvat (data parțială rămâne parțială)', detC.locator('form.proj-form [name=sfarsit]').input_value() == '2028' and detC.locator('form.proj-form [name=inceput]').input_value() == '15.03.2024')
            # prioritatea pe câmp: ce scrie omul bate sursa oficială, dar numai pentru câmpul scris
            detA = deschide_rand(pg, 'BERD', pA)
            completeaza_proiect(detA, inceput='01.02.2020')
            trimite_proiect(detA)
            asteapta_salvat(pg, fals, 2)
            rA = rand_acord(pg, 'BERD', pA['id'])
            egal('prioritate pe câmp: obiectivele rămân cele oficiale; începutul e cel introdus; finalizarea rămâne cea oficială',
                 [descriere_rand(pg, rA)['text'], celula_data(rA, 1)[1].split('\n')[0], celula_data(rA, 2)[1].split('\n')[0]], [OBI_A['ro'], '01.02.2020', '12.2027'])
            egal('prioritate pe câmp: sursele afișate', [descriere_rand(pg, rA)['src'], sursa_celulei(rA, 1), sursa_celulei(rA, 2)], [['sursă oficială'], ['introdus de utilizator'], ['sursă oficială']])
            completeaza_proiect(detA, obiective='Obiective corectate de un utilizator.')
            trimite_proiect(detA)
            asteapta_salvat(pg, fals, 3)
            egal('modificare: aceeași înregistrare (nu se adaugă una nouă)', len(fals.proiecte()), 2)
            egal('obiectivele introduse înlocuiesc pe cele oficiale', descriere_rand(pg, rand_acord(pg, 'BERD', pA['id']))['text'], 'Obiective corectate de un utilizator.')
            # ștergere cu confirmare: ce era oficial se întoarce
            detA.locator('[data-act="proiect-sterge"]').click()
            verifica('ștergere: cere confirmare („Sigur?”)', 'Sigur?' in detA.locator('form.proj-form').inner_text())
            detA.locator('[data-act="proiect-sterge-nu"]').click()
            pg.wait_for_timeout(200)
            egal('„Nu” nu șterge și nu scrie', [len(fals.proiecte()), fals.n_put], [2, 3])
            detA.locator('[data-act="proiect-sterge"]').click()
            detA.locator('[data-act="proiect-sterge-da"]').click()
            asteapta_salvat(pg, fals, 4)
            egal('ștergere: rămâne doar înregistrarea rândului pC', [x['acord'] for x in fals.proiecte()], [pC['id']])
            verifica('mesajul commit-ului pentru ștergere: „Date proiecte: șters: …”', fals.commituri[3].startswith('Date proiecte: șters: '), fals.commituri)
            rA = rand_acord(pg, 'BERD', pA['id'])
            egal('după ștergere, rândul revine la sursa oficială', [descriere_rand(pg, rA)['text'], celula_data(rA, 1)[1].split('\n')[0], sursa_celulei(rA, 1)], [OBI_A['ro'], '14.05.2019', ['sursă oficială']])
            # blocarea la loc și citirea publică, fără cod
            pg.click('#sAcces [data-act="lock"]')
            pg.wait_for_timeout(200)
            verifica('„Blochează” scoate și formularul de proiect', pg.locator('form.proj-form').count() == 0 and pg.locator('#sRez .edt').count() == 0)
            pg.reload(wait_until='networkidle')
            pg.wait_for_selector('section.panel[data-d="BERD"] tr.ac')
            egal('după reîncărcare, datele salvate se văd public, fără cod', descriere_rand(pg, rand_acord(pg, 'BERD', pC['id']))['text'], 'Sprijin pentru reforma sectorului energetic și securitatea aprovizionării.')
            ctx.close()

            # date despre un proiect care nu mai e în registru: nu apar în tabele, dar se văd și se pot șterge
            print('   · date despre proiecte fără acord în registru')
            orf = {'id': 'porf1', 'acord': 'acord-care-nu-mai-exista', 'acte': ['HG99999/1999'], 'nume': 'Acord dispărut din registru', 'obiective': 'Obiective rămase fără acord',
                   'inceput': '2020-01-01', 'la': '2026-10-01T08:00:00.000Z'}
            fals = GitHubFals(intrari=[], proiecte=[orf])
            ctx = context(b)
            pg = pagina(ctx, fals, hash_='#d=BERD', manual=OF, arhiva=False)
            tx = pg.text_content('#sOrfane')
            verifica('panoul „Date despre proiecte fără acord în registru” arată înregistrarea', all(x in tx for x in ('Date despre proiecte fără acord în registru', 'Acord dispărut din registru', 'Obiective rămase fără acord', '01.01.2020')), tx)
            verifica('înregistrarea fără acord nu apare în niciun tabel', 'Obiective rămase fără acord' not in pg.inner_text('#sRez'))
            verifica('fără cod, nu are buton de ștergere', pg.locator('#sOrfane [data-act="proiect-orfan-sterge"]').count() == 0)
            debloca(pg)
            pg.click('#sOrfane [data-act="proiect-orfan-sterge"]')
            pg.click('#sOrfane [data-act="proiect-orfan-sterge-da"]')
            asteapta_salvat(pg, fals, 1)
            verifica('ștearsă din fișier, iar panoul dispare', fals.proiecte() == [] and pg.inner_text('#sOrfane').strip() == '', (fals.proiecte(), pg.inner_text('#sOrfane')))
            verifica('mesajul commit-ului: „Date proiecte: șters: …”', fals.commituri[0].startswith('Date proiecte: șters: '), fals.commituri)
            ctx.close()

            # salvare eșuată: datele rămân în coadă, marcate „nesalvat”, și supraviețuiesc reîncărcării
            print('   · salvare eșuată: coada de modificări')
            fals = GitHubFals(intrari=[])
            ctx = context(b)
            pg = pagina(ctx, fals, hash_='#d=BERD', manual=OF, arhiva=False)
            debloca(pg)
            detC = deschide_rand(pg, 'BERD', pC)
            fals.cade_reteaua = True
            completeaza_proiect(detC, obiective='Obiective în coadă', inceput='2021')
            trimite_proiect(detC)
            pg.wait_for_function('document.querySelector("#sAcces").textContent.includes("Nu pot ajunge la GitHub")', timeout=10000)
            verifica('eșec: datele se văd în tabel, marcate „nesalvat”', 'nesalvat' in rand_acord(pg, 'BERD', pC['id']).inner_text() and descriere_rand(pg, rand_acord(pg, 'BERD', pC['id']))['text'] == 'Obiective în coadă')
            egal('eșec: nimic în fișier, o modificare în coadă', [len(fals.proiecte()), pg.evaluate('window.DebursariUI.stare().coada')], [0, 1])
            pg.reload(wait_until='networkidle')
            pg.wait_for_selector('section.panel[data-d="BERD"] tr.ac')
            verifica('după reîncărcare, datele nesalvate se văd în continuare, marcate „nesalvat”', descriere_rand(pg, rand_acord(pg, 'BERD', pC['id']))['text'] == 'Obiective în coadă' and 'nesalvat' in rand_acord(pg, 'BERD', pC['id']).inner_text())
            fals.cade_reteaua = False
            debloca(pg)
            pg.wait_for_function('window.DebursariUI.stare().coada === 0', timeout=15000)
            egal('după deblocare, coada se salvează singură', [x.get('obiective') for x in fals.proiecte()], ['Obiective în coadă'])
            verifica('mesajul commit-ului pentru date de proiect din coadă', fals.commituri[0].startswith('Date proiecte: salvat: '), fals.commituri)
            ctx.close()

        # ---------------------------------------------------------------- 15. AMP
        if rulez(15):
            print('\n15. AMP: datele de început și de finalizare din arhivă și din raportul live')
            AMP_AST = amp_asteptat()
            sigure = {k: v for k, v in AMP_AST['peAcord'].items() if v['nivel'] == 'sigur'}
            probabile = {k: v for k, v in AMP_AST['peAcord'].items() if v['nivel'] == 'probabil'}
            verifica('amp-date.js pe arhiva și registrul reale: există legături sigure și probabile (%d și %d)' % (len(sigure), len(probabile)), len(sigure) >= 30 and len(probabile) >= 20, (len(sigure), len(probabile)))
            arh = arhiva_amp()
            don_amp = Counter(d for k in sigure for d in donatori_acord(BY_ID[k])).most_common(1)[0][0]
            fals = GitHubFals(intrari=[])
            ctx = context(b)
            pg = pagina(ctx, fals)
            bifeaza(pg, don_amp)
            amp_st = pg.locator('#sAmp .amp-st')
            tx = amp_st.inner_text().replace('\xa0', ' ')
            verifica('bara AMP: câte proiecte sunt legate sigur (%d din %d)' % (len(sigure), len(RANDURI)), '%d din %d proiecte sunt legate sigur' % (len(sigure), len(RANDURI)) in tx, tx)
            verifica('bara AMP: legăturile probabile (%d) apar doar ca indiciu, nu în tabel' % len(probabile), '%d legături doar probabile' % len(probabile) in tx, tx)
            verifica('bara AMP: raportul live nu a răspuns (Failed to fetch) și s-a folosit arhiva; buton „Reîncearcă”',
                     'Raportul AMP live nu a răspuns (Failed to fetch)' in tx and 'arhiva AMP' in tx and 'avert' in amp_st.get_attribute('class') and pg.locator('#sAmp [data-act="amp-reincearca"]').count() >= 1, tx)
            date = pg.evaluate('''(d) => [...document.querySelectorAll('section.panel[data-d="' + d + '"] tr.ac')].map(r => {
                const t = r.querySelectorAll('td');
                const dt = i => { const x = t[i].querySelector('time'); return x ? x.getAttribute('datetime') : null; };
                return [r.getAttribute('data-k').split('|').slice(1).join('|'), dt(1), dt(2), [...t[1].querySelectorAll('.src')].map(x => x.className), [...t[2].querySelectorAll('.src')].map(x => x.className)];
            })''', don_amp)
            gresite = []
            for k, i, f, c1, c2 in date:
                m = sigure.get(k)
                if (i, f) != ((m.get('inceput') or None) if m else None, (m.get('sfarsit') or None) if m else None):
                    gresite.append((k, i, f, m and (m.get('inceput'), m.get('sfarsit'))))
            egal('panoul %s: fiecare rând cu legătură sigură arată datele AMP, celelalte „—” (%d rânduri, %d cu date)' % (don_amp, len(date), sum(1 for x in date if x[0] in sigure)), gresite, [])
            verifica('datele AMP poartă eticheta „AMP” (și nu „sursă oficială”)', all(c1 in ([], ['src s-amp']) and c2 in ([], ['src s-amp']) for _, _, _, c1, c2 in date) and any(c1 == ['src s-amp'] for _, _, _, c1, _ in date), date[:3])
            verifica('rândurile cu legătură doar probabilă nu au date în tabel', all(i is None and f is None for k, i, f, _, _ in date if k in probabile), [x for x in date if x[0] in probabile][:3])
            nepotriviri = []
            for k, v in sigure.items():
                rec = arh.get(v['id'])
                if rec is not None and (iso_din_amp(rec.get('ds')), iso_din_amp(rec.get('de'))) != ((v.get('inceput') or None), (v.get('sfarsit') or None)):
                    nepotriviri.append((k, v['id'], rec.get('ds'), rec.get('de'), v.get('inceput'), v.get('sfarsit')))
            egal('datele legăturilor sigure = datele din arhiva AMP, citită independent în Python (%d proiecte)' % len(arh), nepotriviri, [])
            # linkurile spre fișa AMP se cer abia când se deschide un rând care are un proiect AMP
            rs = next(k for k in sigure if don_amp in donatori_acord(BY_ID[k]))
            verifica('amp-linkuri.js și lista de linkuri nu se cer cât timp niciun rând cu AMP nu e deschis', pg.amp.livrate('paginate') == [] and pg.locator('script[src^="amp-linkuri.js"]').count() == 0)
            det = deschide_rand(pg, don_amp, BY_ID[rs])
            dl = det.locator('.det-proiect .dlp').inner_text()
            verifica('detalii: proiectul AMP legat (cod), datele lui, „Legătură sigură”', sigure[rs]['id'] in dl and 'Legătură sigură' in dl and 'Actual Start Date' in dl and 'Proposed Completion Date' in dl, dl[:500])
            pg.wait_for_function('document.querySelectorAll("script[src^=\\"amp-linkuri.js\\"]").length === 1', timeout=10000)
            pg.wait_for_timeout(600)
            verifica('după deschiderea rândului, lista de linkuri se cere o singură dată', len(pg.amp.livrate('paginate')) == 1, pg.amp.cereri)
            ctx.close()

            # legătură doar probabilă: indiciu în detalii, copiere în formular, salvare de către om
            print('   · legătură probabilă: indiciu, copiere în formular, salvare')
            rp = next(k for k, v in probabile.items() if v.get('inceput') and v.get('sfarsit'))
            vp = probabile[rp]
            dp = donatori_acord(BY_ID[rp])[0]
            fals = GitHubFals(intrari=[])
            ctx = context(b)
            pg = pagina(ctx, fals)
            bifeaza(pg, dp)
            r = rand_acord(pg, dp, rp)
            egal('legătură probabilă: datele nu apar în tabel', [celula_data(r, 1)[1], celula_data(r, 2)[1]], ['—', '—'])
            det = deschide_rand(pg, dp, BY_ID[rp])
            dl = det.locator('.det-proiect .dlp').inner_text()
            verifica('detalii: „Legătură doar probabilă”, cu proiectul AMP și datele lui ca indiciu', 'Legătură doar probabilă' in dl and vp['id'] in dl and fmt_data_iso(vp['inceput']) in dl, dl[:500])
            verifica('fără cod, nu există butonul de copiere', det.locator('[data-act="foloseste-amp"]').count() == 0)
            debloca(pg)
            det = deschide_rand(pg, dp, BY_ID[rp])
            det.locator('[data-act="foloseste-amp"]').click()
            fp = det.locator('form.proj-form')
            egal('datele din AMP s-au copiat în formular, ca omul să le verifice', [fp.locator('[name=inceput]').input_value(), fp.locator('[name=sfarsit]').input_value()], [fmt_data_iso(vp['inceput']), fmt_data_iso(vp['sfarsit'])])
            verifica('nota spune de unde vin și că legătura nu e confirmată', ('din AMP, proiectul %s (legătură neconfirmată)' % vp['id']) in fp.locator('[name=nota]').input_value(), fp.locator('[name=nota]').input_value())
            egal('copierea nu scrie nimic până nu apeși „Salvează”', [fals.n_put, len(fals.proiecte())], [0, 0])
            trimite_proiect(det)
            asteapta_salvat(pg, fals, 1)
            r = rand_acord(pg, dp, rp)
            egal('după salvare, datele apar în tabel cu eticheta „introdus de utilizator”', [celula_data(r, 1)[0], celula_data(r, 2)[0], sursa_celulei(r, 1), sursa_celulei(r, 2)],
                 [vp['inceput'], vp['sfarsit'], ['introdus de utilizator'], ['introdus de utilizator']])
            ctx.close()

            # o sursă oficială bate AMP, câmp cu câmp
            print('   · sursă oficială înaintea AMP, câmp cu câmp')
            rs2 = next(k for k, v in sigure.items() if v.get('inceput') and v.get('sfarsit'))
            ds2 = donatori_acord(BY_ID[rs2])[0]
            OF2 = {'omise': MANUAL_REAL['omise'], 'proiecte': [{'acte': [BY_ID[rs2]['acte'][0]['act']], 'inceput': '2000-01-15', 'sursa': SURSA_B, 'citat': 'The project started in January 2000.'}]}
            fals = GitHubFals(intrari=[])
            ctx = context(b)
            pg = pagina(ctx, fals, manual=OF2)
            bifeaza(pg, ds2)
            r = rand_acord(pg, ds2, rs2)
            egal('începutul vine din sursa oficială, finalizarea din AMP', [celula_data(r, 1)[0], celula_data(r, 2)[0], sursa_celulei(r, 1), sursa_celulei(r, 2)],
                 ['2000-01-15', sigure[rs2]['sfarsit'], ['sursă oficială'], ['AMP']])
            ctx.close()

            # raportul live răspunde: datele lui au prioritate; o legătură confirmată de un om; linkul spre fișa AMP; Excel
            print('   · raportul live răspunde; legătură confirmată; link spre AMP; Excel')
            CSV_LIVE = '\n'.join(['AMP ID,Project Title,Donor Agency,Actual Start Date,Proposed Completion Date,Funding 2024 Actual Commitments Total,Funding 2024 Actual Disbursements Total',
                                  '9999000111111,Proiect de probă pentru testele paginii,BERD,12/03/2024,31/12/2027,1000000,0', ''])
            rc = next(a for a in rb if a['id'] not in AMP_AST['peAcord'])
            conf = {'confirmate': {rc['id']: ['9999000111111']}, 'respinse': {}, 'fara_proiect': []}
            amp = AmpFals(csv=CSV_LIVE, harta={'9999000111111': 7777})
            fals = GitHubFals(intrari=[])
            ctx = context(b)
            pg = pagina(ctx, fals, hash_='#d=BERD', amp=amp, confirmari=conf)
            cls = pg.locator('#sAmp .amp-st').get_attribute('class')
            tx = pg.locator('#sAmp .amp-st').inner_text().replace('\xa0', ' ')
            verifica('bara AMP: raportul live citit, fără avertisment', 'avert' not in cls and 'eroare' not in cls and 'nu a răspuns' not in tx, (cls, tx))
            verifica('bara AMP: o legătură sigură în plus (cea confirmată de un om)', '%d din %d proiecte sunt legate sigur' % (len(sigure) + 1, len(RANDURI)) in tx, tx)
            cerere = amp.livrate('/661')
            verifica('cererea către raport: POST, cu interogarea în corp', len(cerere) == 1 and cerere[0][0] == 'POST', cerere)
            r = rand_acord(pg, 'BERD', rc['id'])
            egal('legătură confirmată + raport live: datele din raport, cu eticheta „AMP”', [celula_data(r, 1)[0], celula_data(r, 2)[0], sursa_celulei(r, 1), sursa_celulei(r, 2)], ['2024-03-12', '2027-12-31', ['AMP'], ['AMP']])
            titlu_chip = r.locator('td').nth(1).locator('.src').get_attribute('title')
            verifica('eticheta „AMP” spune proiectul și câmpul (Actual Start Date)', '9999000111111' in titlu_chip and 'Actual Start Date' in titlu_chip, titlu_chip)
            det = deschide_rand(pg, 'BERD', rc)
            verifica('detalii: „Legătură confirmată de un om”', 'Legătură confirmată de un om' in det.locator('.det-proiect .dlp').inner_text())
            pg.wait_for_selector('.det-proiect a.amp-link', timeout=15000)
            egal('codul AMP devine link spre fișa proiectului în AMP', pg.locator('.det-proiect a.amp-link').first.get_attribute('href'), 'https://amp.gov.md/aim/viewActivityPreview.do~activityId=7777')
            with pg.expect_download(timeout=60000) as d:
                pg.click('section.panel[data-d="BERD"] [data-act="excel-donator"]')
            cale = DESC / 'berd-amp.xlsx'
            d.value.save_as(str(cale))
            ws = openpyxl.load_workbook(cale)['BERD']
            for rr in ws.iter_rows(min_row=1, max_row=12):
                if 'Proiectul' in [c.value for c in rr]:
                    antet, rand_antet = [c.value for c in rr], rr[0].row
                    break
            iP, iI, iF, iS = (antet.index(x) for x in ('Proiectul', 'Data efectivă de începere', 'Data finalizării', 'Sursa obiectivelor și a datelor'))
            _nume_rand = nume_rand(r)
            rx = [x for x in ws.iter_rows(min_row=rand_antet + 1) if x[iP].value == _nume_rand][0]
            egal('Excel: datele din AMP (date adevărate) și sursa „AMP”', [rx[iI].value, rx[iF].value, rx[iS].value], [datetime.datetime(2024, 3, 12), datetime.datetime(2027, 12, 31), 'AMP'])
            note = ' '.join(toate_foile(cale))
            verifica('Excel: nota spune ce s-a citit din AMP (raportul live și arhiva)', 'raportul AMP live (1 proiecte)' in note and ('arhiva AMP (%d proiecte' % len(arh)) in note, note[-600:])
            ctx.close()

            # raportul live pică, apoi „Reîncearcă”
            print('   · raportul live pică; „Reîncearcă”')
            amp2 = AmpFals()
            fals = GitHubFals(intrari=[])
            ctx = context(b)
            pg = pagina(ctx, fals, hash_='#d=BERD', amp=amp2, confirmari=conf)
            r = rand_acord(pg, 'BERD', rc['id'])
            verifica('raport căzut: avertisment, iar rândul fără proiect AMP în arhivă nu are date', 'avert' in pg.locator('#sAmp .amp-st').get_attribute('class') and celula_data(r, 1)[1] == '—')
            amp2.csv = CSV_LIVE
            pg.click('#sAmp [data-act="amp-reincearca"]')
            pg.wait_for_function('() => { const e = document.querySelector("#sAmp .amp-st"); return e && !e.classList.contains("avert") && !e.classList.contains("lucru") && !e.classList.contains("eroare"); }', timeout=60000)
            egal('după „Reîncearcă”, datele din raport apar', celula_data(rand_acord(pg, 'BERD', rc['id']), 1)[0], '2024-03-12')
            ctx.close()

            # nici arhiva, nici raportul: pagina merge mai departe, fără date din AMP, și spune de ce
            print('   · nici arhiva, nici raportul live')
            fals = GitHubFals(intrari=[])
            ctx = context(b)
            pg = pagina(ctx, fals, hash_='#d=BERD', arhiva=False)
            cls = pg.locator('#sAmp .amp-st').get_attribute('class')
            tx = pg.locator('#sAmp .amp-st').inner_text()
            verifica('fără date AMP: bara spune că nu s-au putut citi și că datele vin doar din surse oficiale sau introduse de utilizatori', 'eroare' in cls and 'Datele din AMP nu s-au putut citi' in tx and 'sursă oficială' in tx and 'utilizator' in tx, (cls, tx))
            egal('fără date AMP: toate celulele de date sunt „—”', pg.evaluate('document.querySelectorAll("section.panel[data-d=\\"BERD\\"] tr.ac time").length'), 0)
            with pg.expect_download(timeout=60000) as d:
                pg.click('section.panel[data-d="BERD"] [data-act="excel-donator"]')
            cale = DESC / 'berd-fara-amp.xlsx'
            d.value.save_as(str(cale))
            note = ' '.join(toate_foile(cale))
            verifica('Excel fără date AMP: nota spune că nu au putut fi citite', 'Datele AMP nu au putut fi citite' in note, note[-500:])
            ctx.close()

        # ---------------------------------------------------------------- 16. fără dubluri, cu fișierul adevărat de proiecte
        if rulez(16):
            print('\n16. Fără dubluri: rânduri-umbrelă omise, fiecare act într-un singur rând, denumiri deosebite; fișierul adevărat date/proiecte_manual.json')
            pe_act = {}
            for a in RANDURI:
                for x in a['acte']:
                    pe_act.setdefault(x['act'], set()).add(a['id'])
            egal('în date: fiecare act din registru apare într-un singur rând din liste (%d acte)' % len(pe_act), sorted(c for c, v in pe_act.items() if len(v) > 1), [])
            egal('în date: rândurile omise sunt cele care conțin actele din „omise” (%d)' % len(OMISE_ID), sorted(OMISE_ID), sorted(a['id'] for a in ACORDURI if any(x['act'] in OMISE_ACTE for x in a['acte'])))
            verifica('în date: rândurile omise nu se adună în niciun total', all(BY_ID[i]['inTotal'] != 'numarat' for i in OMISE_ID), [(i, BY_ID[i]['inTotal']) for i in OMISE_ID])
            verifica('în date: actele la care e „numărată” suma unui rând omis se găsesc în rânduri care rămân în liste', all(c in pe_act for o in MANUAL_REAL['omise'] for c in o.get('numarat_la', [])),
                     [c for o in MANUAL_REAL['omise'] for c in o.get('numarat_la', []) if c not in pe_act])
            verifica('în date: fiecare rând omis are motiv în română și în engleză', all(o.get('motiv') and o.get('motiv_en') for o in MANUAL_REAL['omise']))
            fals = GitHubFals(intrari=[])
            ctx = context(b)
            pg = pagina(ctx, fals, manual='real', arhiva=False)
            pg.click('[data-act="toti-afisati"]')
            sel = pg.evaluate('window.DebursariUI.stare().sel')
            pg.wait_for_function('n => document.querySelectorAll("section.panel[data-d]").length === n', arg=len(sel), timeout=60000)
            n_grupuri = pg.locator('section.panel[data-d] tr.pg').count()
            pg.evaluate('document.querySelectorAll("section.panel[data-d] tr.pg .exp").forEach(b => b.click())')           # proiectele cu grant și împrumut: se deschid, ca să se vadă și acordurile lor
            pg.wait_for_function('n => document.querySelectorAll("section.panel[data-d] tr.pg.deschis").length === n', arg=n_grupuri, timeout=30000)
            ids_afisate = set(pg.evaluate('[...document.querySelectorAll("section.panel[data-d] tr.ac")].map(r => r.getAttribute("data-k").split("|").slice(1).join("|"))'))
            asteptate = {a['id'] for a in RANDURI if set(donatori_acord(a)) & set(sel)}
            egal('în pagină, cu toți donatorii bifați (%d): exact rândurile neomise (%d)' % (len(sel), len(asteptate)), sorted(ids_afisate), sorted(asteptate))
            verifica('în pagină: niciun rând omis nu apare în vreo listă', not (ids_afisate & OMISE_ID), sorted(ids_afisate & OMISE_ID))
            dubluri = pg.evaluate('''() => [...document.querySelectorAll("section.panel[data-d]")].map(p => {
                const v = [...p.querySelectorAll("tr.pg .pname, tr.ac:not(.sub) .pname")].map(x => x.textContent.trim());
                const s = new Set(), d = [];
                v.forEach(n => { if (s.has(n)) d.push(n); s.add(n); });
                return [p.getAttribute("data-d"), d];
            }).filter(x => x[1].length)''')
            egal('în pagină: același donator nu are două proiecte cu aceeași denumire afișată (rândurile cu nume la fel se deosebesc prin tip, an sau sumă)', dubluri, [])
            verifica('în pagină: o denumire repetată la același donator poartă mențiunea de deosebire între paranteze', any(x.endswith(')') and ' (' in x for x in pg.evaluate('[...document.querySelectorAll("section.panel[data-d=\\"BERD\\"] tr.ac .pname")].map(x => x.textContent.trim())')))
            # lista rândurilor omise, cu motivul
            om = pg.locator('#sOmise details.omise').first
            verifica('lista omiselor: titlul spune câte rânduri (%d) și de ce' % len(OMISE_ID), ('%d rânduri din registru nu apar în liste, ca să nu dubleze proiecte' % len(OMISE_ID)) in om.locator('summary').inner_text(), om.locator('summary').inner_text())
            om.locator('summary').click()
            li = om.locator('li')
            egal('lista omiselor: un element pentru fiecare rând omis', li.count(), len(OMISE_ID))
            verifica('lista omiselor: fiecare element are actele, motivul și unde e numărată suma',
                     all(any(c in li.nth(i).inner_text() for c in OMISE_ACTE) and 'Numărat la:' in li.nth(i).inner_text() and len(li.nth(i).locator('.om-m').first.inner_text()) > 30 for i in range(li.count())), li.all_inner_texts())
            verifica('fișierul adevărat: nicio intrare respinsă sau fără rând (nu apare lista „nu s-au folosit”)', pg.locator('#sOmise details.omise.avert').count() == 0, pg.inner_text('#sOmise')[-300:])
            # obiectivele din fișierul adevărat: fiecare rând care are obiective în fișier le arată în pagină (și numai ele)
            cu_obi = set()
            for p in MANUAL_REAL.get('proiecte', []):
                if (p.get('obiective') or {}).get('ro'):
                    r_ = {i for c in p['acte'] for i in pe_act.get(c, ())}
                    cu_obi |= {sorted(r_)[0]} if r_ else set()
            # descrierea apare doar în rândul deschis: se deschid toate rândurile (unul câte unul, comutarea e sincronă), se citește blocul de sus, apoi se închid la loc
            in_pagina = set(pg.evaluate('''() => {
                let g = 0, b;
                while (g++ < 3000 && (b = document.querySelector("section.panel[data-d] tr.ac:not(.deschis) .exp"))) b.click();
                const r = [...document.querySelectorAll("section.panel[data-d] tr.det")].filter(d => d.querySelector(".det-desc .dd-t:not(.gol)")).map(d => d.getAttribute("data-k").split("|").slice(1).join("|"));
                g = 0; while (g++ < 3000 && (b = document.querySelector("section.panel[data-d] tr.ac.deschis .exp"))) b.click();
                return r;
            }'''))
            egal('obiectivele din date/proiecte_manual.json: rândurile care le au în fișier (%d) sunt cele care le arată în pagină' % len(cu_obi), sorted(in_pagina), sorted(cu_obi))
            # fiecare intrare din fișier are sursă și citat (altfel pagina o respinge): același test de pe Node, aici pe fișierul din repository
            verifica('fișierul adevărat: fiecare intrare are adresa documentului (http), citat de cel puțin 12 caractere, obiective sau date, în formatul AAAA, AAAA-LL sau AAAA-LL-ZZ',
                     all(re.match(r'^https?://\S+$', p.get('sursa', '')) and len(' '.join(p.get('citat', '').split())) >= 12 and ((p.get('obiective') or {}).get('ro') or p.get('inceput') or p.get('sfarsit')) and
                         all(re.match(r'^\d{4}(-\d{2}(-\d{2})?)?$', p.get(k, '2000')) for k in ('inceput', 'sfarsit'))
                         for p in MANUAL_REAL.get('proiecte', [])), [p.get('acte') for p in MANUAL_REAL.get('proiecte', [])][:5])
            # engleză: motivul în engleză
            pg.evaluate('Traducere.seteaza("en")')
            pg.wait_for_timeout(400)
            pg.locator('#sOmise details.omise summary').first.click()
            tx_en = pg.locator('#sOmise details.omise').first.inner_text()
            verifica('lista omiselor în engleză: titlul, motivul în engleză, „Counted under”', 'rows of the register do not appear in the lists' in tx_en and 'Counted under:' in tx_en and
                     all(any(o['motiv_en'][:40] in tx_en for o in MANUAL_REAL['omise']) for _ in (0,)), tx_en[:400])
            ctx.close()

        # ---------------------------------------------------------------- 17. editare în tabel
        if rulez(17):
            print('\n17. Editare în tabel, după o singură deblocare: data de început, data finalizării, suma proiectului')
            fals = GitHubFals(intrari=[])
            ctx = context(b)
            pg = pagina(ctx, fals, hash_='#d=BERD', manual=OF, arhiva=False)
            rC = rand_acord(pg, 'BERD', pC['id'])
            reg_txt = fmt_bani_ro(pC['suma']['v']) + ' ' + pC['suma']['val']
            amt0 = rC.locator('td').nth(4).inner_text().replace('\xa0', ' ')
            verifica('blocat: fără creioane în tabel', pg.locator('#sRez .edt').count() == 0)
            debloca(pg)
            verifica('deblocat: fiecare rând are trei creioane (început, finalizare, sumă)', all(rand_acord(pg, 'BERD', a['id']).locator('.edt').count() == 3 for a in BERD), [rand_acord(pg, 'BERD', a['id']).locator('.edt').count() for a in BERD][:5])
            egal('creioanele spun ce editează și la ce proiect', [rC.locator('.edt[data-f="%s"]' % f).get_attribute('aria-label').split(':')[0] for f in ('inceput', 'sfarsit', 'suma')],
                 ['Editează data efectivă de începere', 'Editează data finalizării', 'Editează suma proiectului'])
            egal('bara de acces spune cum se editează', 'Creionul din tabel' in pg.locator('#sAcces .acces-txt').inner_text(), True)
            # --- deschiderea editorului
            rC.locator('.edt[data-f="inceput"]').click()
            pg.wait_for_selector('tr.ac.edit[data-k="BERD|%s"]' % pC['id'])
            verifica('rândul intră în editare: câmpuri pentru început, finalizare, sumă și valută, și o bară cu Salvează / Anulează', all(rC.locator('[data-re=%s]' % n).count() == 1 for n in ('inceput', 'sfarsit', 'suma', 'val')) and
                     pg.locator('tr.re[data-k="BERD|%s"] [data-act="rand-salveaza"]' % pC['id']).count() == 1 and pg.locator('tr.re[data-k="BERD|%s"] [data-act="rand-anuleaza"]' % pC['id']).count() == 1)
            egal('focus pe câmpul al cărui creion a fost apăsat', pg.evaluate('document.activeElement.getAttribute("data-re")'), 'inceput')
            egal('câmpurile pornesc de la ce se vede acum: datele goale, suma și valuta din registru', [rC.locator('[data-re=inceput]').input_value(), rC.locator('[data-re=sfarsit]').input_value(), rC.locator('[data-re=suma]').input_value(), rC.locator('[data-re=val]').input_value()],
                 ['', '', fmt_bani_ro(pC['suma']['v']), pC['suma']['val']])
            verifica('lângă sumă se vede suma din registru', ('în registru: ' + reg_txt) in rC.locator('td').nth(4).inner_text().replace('\xa0', ' '), rC.locator('td').nth(4).inner_text())
            # --- validare
            rC.locator('[data-re=inceput]').fill('abc')
            antes = fals.n_put
            pg.click('tr.re[data-k="BERD|%s"] [data-act="rand-salveaza"]' % pC['id'])
            pg.wait_for_timeout(200)
            verifica('validare: „Nu înțeleg data de început”, câmpul are aria-invalid, nimic scris', 'Nu înțeleg data de început' in pg.locator('tr.re .ferr').inner_text() and rC.locator('[data-re=inceput]').get_attribute('aria-invalid') == 'true' and fals.n_put == antes, pg.locator('tr.re .ferr').inner_text())
            egal('după eroare, focus pe câmpul greșit; ce a scris omul rămâne scris', [pg.evaluate('document.activeElement.getAttribute("data-re")'), rC.locator('[data-re=inceput]').input_value()], ['inceput', 'abc'])
            rC.locator('[data-re=inceput]').fill('15.03.2024')
            rC.locator('[data-re=sfarsit]').fill('01.01.2023')
            pg.click('tr.re[data-k="BERD|%s"] [data-act="rand-salveaza"]' % pC['id'])
            pg.wait_for_timeout(200)
            verifica('validare: finalizarea nu poate fi înaintea începutului', 'nu poate fi înaintea' in pg.locator('tr.re .ferr').inner_text() and fals.n_put == antes, pg.locator('tr.re .ferr').inner_text())
            rC.locator('[data-re=sfarsit]').fill('12.2028')
            verifica('eroarea dispare când omul corectează câmpul', rC.locator('[data-re=sfarsit]').get_attribute('aria-invalid') is None and pg.locator('tr.re .ferr').inner_text().strip() == '')
            rC.locator('[data-re=suma]').fill('abc')
            pg.click('tr.re[data-k="BERD|%s"] [data-act="rand-salveaza"]' % pC['id'])
            pg.wait_for_timeout(200)
            verifica('validare: „Nu înțeleg suma”', 'Nu înțeleg suma' in pg.locator('tr.re .ferr').inner_text() and fals.n_put == antes, pg.locator('tr.re .ferr').inner_text())
            rC.locator('[data-re=suma]').fill(fmt_bani_ro(pC['suma']['v']))
            # --- salvare: doar ce s-a schimbat
            pg.click('tr.re[data-k="BERD|%s"] [data-act="rand-salveaza"]' % pC['id'])
            asteapta_salvat(pg, fals, 1)
            e = fals.proiecte()[0] if fals.proiecte() else {}
            egal('fișierul: doar datele schimbate (ISO / parțiale); suma rămasă neschimbată nu se scrie ca sumă a utilizatorului', [e.get('acord'), e.get('inceput'), e.get('sfarsit'), 'suma' in e, 'val' in e, 'obiective' in e], [pC['id'], '2024-03-15', '2028-12', False, False, False])
            verifica('mesajul commit-ului: „Date proiecte: salvat: …”', fals.commituri[0].startswith('Date proiecte: salvat: '), fals.commituri)
            rC = rand_acord(pg, 'BERD', pC['id'])
            egal('tabel: datele introduse, cu eticheta „introdus de utilizator”', [celula_data(rC, 1)[1].split('\n')[0], celula_data(rC, 2)[1].split('\n')[0], sursa_celulei(rC, 1), sursa_celulei(rC, 2)],
                 [ '15.03.2024', '12.2028', ['introdus de utilizator'], ['introdus de utilizator']])
            verifica('după salvare rândul iese din editare, iar focusul se întoarce pe creion', pg.locator('tr.ac.edit').count() == 0 and pg.locator('tr.re').count() == 0 and pg.evaluate('document.activeElement.classList.contains("edt")'))
            egal('suma rămâne cea din registru, fără marcaj de corectură', [reg_txt.split(' ')[0] in rC.locator('td').nth(4).inner_text().replace('\xa0', ' '), 'corectată' in rC.locator('td').nth(4).inner_text()], [True, False])
            # --- suma corectată
            suma_inainte = suma_numarata(BERD)
            rC.locator('.edt[data-f="suma"]').click()
            pg.wait_for_selector('tr.ac.edit')
            egal('focus pe suma', pg.evaluate('document.activeElement.getAttribute("data-re")'), 'suma')
            egal('câmpurile de date pornesc de la ce a fost introdus', [rC.locator('[data-re=inceput]').input_value(), rC.locator('[data-re=sfarsit]').input_value()], ['15.03.2024', '12.2028'])
            rC.locator('[data-re=suma]').fill('12.345.678,90')
            rC.locator('[data-re=val]').select_option('USD')
            rC.locator('[data-re=suma]').press('Enter')
            asteapta_salvat(pg, fals, 2)
            e = fals.proiecte()[0]
            egal('fișierul: aceeași înregistrare, cu suma și valuta noi; datele introduse înainte rămân', [len(fals.proiecte()), e.get('suma'), e.get('val'), e.get('inceput'), e.get('sfarsit')], [1, 12345678.9, 'USD', '2024-03-15', '2028-12'])
            rC = rand_acord(pg, 'BERD', pC['id'])
            tx = rC.locator('td').nth(4).inner_text().replace('\xa0', ' ')
            eur_nou = 12345678.9 / CURSURI['USD']
            verifica('tabel: suma nouă, echivalentul în euro, „corectată de utilizator” și suma din registru alături', '12.345.678,90 USD' in tx and ('≈ ' + fmt_ro(rotunjit(eur_nou), 0) + ' EUR') in tx and 'corectată de utilizator' in tx and ('în registru: ' + reg_txt) in tx, tx)
            if pC['inTotal'] == 'numarat':
                asteptat = suma_inainte - eur(pC) + eur_nou
                dsum = pg.locator('section.panel[data-d="BERD"] .dsum').inner_text().replace('\xa0', ' ')
                verifica('antetul donatorului: totalul sumelor ține seama de suma corectată', ('suma ' + fmt_ro(rotunjit(asteptat), 0) + ' EUR') in dsum, (dsum, asteptat))
            # --- în detalii: formularul de proiect arată suma, iar „Suma din registru” apare separat
            detC = deschide_rand(pg, 'BERD', pC)
            egal('detalii: formularul de proiect arată suma corectată și valuta', [detC.locator('form.proj-form [name=suma]').input_value(), detC.locator('form.proj-form [name=val]').input_value()], ['12.345.678,90', 'USD'])
            inf = detC.locator('.det-info').inner_text().replace('\xa0', ' ')
            verifica('detalii: „Suma din registru” cu valoarea de acolo, iar „Suma” spune că e corectată', 'suma din registru' in inf.lower() and reg_txt in inf and 'corectată de utilizator' in inf, inf)
            # --- Excel: suma nouă și nota
            with pg.expect_download(timeout=60000) as d:
                pg.click('section.panel[data-d="BERD"] [data-act="excel-donator"]')
            cale = DESC / 'berd-suma-corectata.xlsx'
            d.value.save_as(str(cale))
            wsb = openpyxl.load_workbook(cale)['BERD']
            for rr in wsb.iter_rows(min_row=1, max_row=12):
                if 'Proiectul' in [c.value for c in rr]:
                    antet, rand_antet = [c.value for c in rr], rr[0].row
                    break
            iP, iS, iV = antet.index('Proiectul'), antet.index('Suma proiectului'), antet.index('Suma proiectului') + 1
            rx = [x for x in wsb.iter_rows(min_row=rand_antet + 1) if x[iP].value == nume_rand(rC)][0]
            egal('Excel: rândul cu suma corectată (suma, valuta)', [rx[iS].value, rx[iV].value], [12345678.9, 'USD'])
            note = ' '.join(toate_foile(cale))
            verifica('Excel: nota spune că suma a fost corectată și arată registru → corectată', 'suma a fost corectată de un utilizator' in note and (reg_txt + ' → 12.345.678,90 USD') in note, note[-600:])
            # --- golirea sumei: se revine la registru
            rC.locator('.edt[data-f="suma"]').click()
            rC.locator('[data-re=suma]').fill('')
            pg.click('tr.re[data-k="BERD|%s"] [data-act="rand-salveaza"]' % pC['id'])
            asteapta_salvat(pg, fals, 3)
            e = fals.proiecte()[0]
            egal('suma goală: corectura dispare din fișier, datele rămân', [len(fals.proiecte()), 'suma' in e, 'val' in e, e.get('inceput')], [1, False, False, '2024-03-15'])
            rC = rand_acord(pg, 'BERD', pC['id'])
            verifica('tabel: suma din registru revine, fără marcaj', 'corectată' not in rC.locator('td').nth(4).inner_text() and reg_txt.split(' ')[0] in rC.locator('td').nth(4).inner_text().replace('\xa0', ' '), rC.locator('td').nth(4).inner_text())
            # --- Anulează și Esc nu scriu nimic
            antes = fals.n_put
            rC.locator('.edt[data-f="sfarsit"]').click()
            rC.locator('[data-re=sfarsit]').fill('2040')
            pg.click('tr.re[data-k="BERD|%s"] [data-act="rand-anuleaza"]' % pC['id'])
            pg.wait_for_timeout(200)
            verifica('„Anulează”: rândul revine la ce era, fără scriere', pg.locator('tr.ac.edit').count() == 0 and celula_data(rand_acord(pg, 'BERD', pC['id']), 2)[1].split('\n')[0] == '12.2028' and fals.n_put == antes)
            rand_acord(pg, 'BERD', pC['id']).locator('.edt[data-f="sfarsit"]').click()
            pg.fill('[data-fk="BERD|%s|re_sfarsit"]' % pC['id'], '2041')
            pg.keyboard.press('Escape')
            pg.wait_for_timeout(200)
            verifica('Esc anulează editarea, fără scriere', pg.locator('tr.ac.edit').count() == 0 and celula_data(rand_acord(pg, 'BERD', pC['id']), 2)[1].split('\n')[0] == '12.2028' and fals.n_put == antes)
            rand_acord(pg, 'BERD', pC['id']).locator('.edt[data-f="inceput"]').click()
            pg.click('tr.re[data-k="BERD|%s"] [data-act="rand-salveaza"]' % pC['id'])
            pg.wait_for_timeout(200)
            verifica('„Salvează” fără nicio schimbare nu scrie nimic (nu apare un commit nou)', fals.n_put == antes and pg.locator('tr.ac.edit').count() == 0, fals.n_put)
            # --- golirea tuturor câmpurilor șterge înregistrarea
            rand_acord(pg, 'BERD', pC['id']).locator('.edt[data-f="inceput"]').click()
            pg.fill('[data-fk="BERD|%s|re_inceput"]' % pC['id'], '')
            pg.fill('[data-fk="BERD|%s|re_sfarsit"]' % pC['id'], '')
            pg.click('tr.re[data-k="BERD|%s"] [data-act="rand-salveaza"]' % pC['id'])
            asteapta_salvat(pg, fals, 4)
            egal('toate câmpurile goale: înregistrarea se șterge, rândul revine la „—”', [fals.proiecte(), celula_data(rand_acord(pg, 'BERD', pC['id']), 1)[1], celula_data(rand_acord(pg, 'BERD', pC['id']), 2)[1]], [[], '—', '—'])
            verifica('mesajul commit-ului: „Date proiecte: șters: …”', fals.commituri[3].startswith('Date proiecte: șters: '), fals.commituri)
            # --- rând cu date din sursă oficială: editorul pornește de la valoarea oficială; se salvează doar ce se schimbă
            rA = rand_acord(pg, 'BERD', pA['id'])
            rA.locator('.edt[data-f="inceput"]').click()
            egal('sursă oficială: câmpurile pornesc de la datele oficiale', [rA.locator('[data-re=inceput]').input_value(), rA.locator('[data-re=sfarsit]').input_value()], ['14.05.2019', '12.2027'])
            rA.locator('[data-re=inceput]').fill('01.02.2020')
            rA.locator('[data-re=inceput]').press('Enter')
            asteapta_salvat(pg, fals, 5)
            e = fals.proiecte()[0]
            egal('fișierul are doar începutul scris de om; finalizarea oficială nu se copiază', [e.get('inceput'), 'sfarsit' in e, 'obiective' in e, 'suma' in e], ['2020-02-01', False, False, False])
            rA = rand_acord(pg, 'BERD', pA['id'])
            egal('tabel: începutul e al utilizatorului, finalizarea rămâne oficială', [celula_data(rA, 1)[1].split('\n')[0], celula_data(rA, 2)[1].split('\n')[0], sursa_celulei(rA, 1), sursa_celulei(rA, 2)], ['01.02.2020', '12.2027', ['introdus de utilizator'], ['sursă oficială']])
            rA.locator('.edt[data-f="inceput"]').click()
            rA.locator('[data-re=inceput]').fill('')
            rA.locator('[data-re=inceput]').press('Enter')
            asteapta_salvat(pg, fals, 6)
            egal('golirea câmpului scris de om: rândul revine la sursa oficială', [fals.proiecte(), celula_data(rand_acord(pg, 'BERD', pA['id']), 1)[1].split('\n')[0], sursa_celulei(rand_acord(pg, 'BERD', pA['id']), 1)], [[], '14.05.2019', ['sursă oficială']])
            # --- nota (sursa informației) din bara rândului
            rA = rand_acord(pg, 'BERD', pA['id'])
            rA.locator('.edt[data-f="sfarsit"]').click()
            rA.locator('[data-re=sfarsit]').fill('2030')
            pg.fill('[data-fk="BERD|%s|re_nota"]' % pA['id'], 'raport anual, pag. 3')
            pg.click('tr.re[data-k="BERD|%s"] [data-act="rand-salveaza"]' % pA['id'])
            asteapta_salvat(pg, fals, 7)
            egal('nota din bara rândului ajunge în înregistrare', [fals.proiecte()[0].get('sfarsit'), fals.proiecte()[0].get('nota')], ['2030', 'raport anual, pag. 3'])
            # --- o notă fără nicio valoare nu se salvează
            rB = rand_acord(pg, 'BERD', pC['id'])
            antes = fals.n_put
            rB.locator('.edt[data-f="inceput"]').click()
            pg.fill('[data-fk="BERD|%s|re_nota"]' % pC['id'], 'doar o notă')
            pg.click('tr.re[data-k="BERD|%s"] [data-act="rand-salveaza"]' % pC['id'])
            pg.wait_for_timeout(200)
            verifica('doar o notă, fără nicio valoare: „Completează cel puțin un câmp”, nimic scris', 'Completează cel puțin un câmp' in pg.locator('tr.re .ferr').inner_text() and fals.n_put == antes, pg.locator('tr.re .ferr').inner_text())
            # --- Blochează închide editoarele și scoate creioanele, la toate rândurile
            pg.click('#sAcces [data-act="lock"]')
            pg.wait_for_timeout(200)
            verifica('„Blochează”: niciun editor deschis, niciun creion; redeblocarea nu readuce editorul', pg.locator('tr.ac.edit').count() == 0 and pg.locator('#sRez .edt').count() == 0 and pg.locator('[data-re]').count() == 0)
            debloca(pg)
            verifica('după redeblocare: creioanele sunt înapoi, editoarele rămân închise', pg.locator('#sRez .edt').count() == 3 * len(BERD) and pg.locator('tr.ac.edit').count() == 0)
            pg.screenshot(path=str(DESC / 'desktop-editare-rand.png'))
            ctx.close()

            # engleză și telefon: editorul din rând
            print('   · engleză și telefon')
            fals = GitHubFals(intrari=[])
            ctx = context(b, viewport=(390, 844))
            pg = pagina(ctx, fals, hash_='#d=BERD', lang='en', manual=OF, arhiva=False)
            debloca(pg)
            egal('engleză: titlul barei', pg.locator('#sAcces b').inner_text(), 'Editing unlocked for all agreements')
            rC = rand_acord(pg, 'BERD', pC['id'])
            egal('engleză: creioanele', [rC.locator('.edt[data-f="%s"]' % f).get_attribute('aria-label').split(':')[0] for f in ('inceput', 'sfarsit', 'suma')], ['Edit the actual start date', 'Edit the completion date', 'Edit the project amount'])
            rC.locator('.edt[data-f="suma"]').click()
            verifica('engleză: suma în format englezesc, „in the register”, butoanele Save / Cancel', rC.locator('[data-re=suma]').input_value() == fmt_en(pC['suma']['v'], 2) and 'in the register' in rC.inner_text() and
                     pg.locator('tr.re [data-act="rand-salveaza"]').inner_text() == 'Save' and pg.locator('tr.re [data-act="rand-anuleaza"]').inner_text() == 'Cancel', rC.locator('[data-re=suma]').input_value())
            rC.locator('[data-re=suma]').fill('1,500,000.50')
            rC.locator('[data-re=val]').select_option('EUR')
            verifica('telefon: fără derulare orizontală cu editorul deschis', pg.evaluate('document.documentElement.scrollWidth <= window.innerWidth'), pg.evaluate('[document.documentElement.scrollWidth, window.innerWidth]'))
            pg.screenshot(path=str(DESC / 'telefon-editare-rand.png'))
            pg.click('tr.re[data-k="BERD|%s"] [data-act="rand-salveaza"]' % pC['id'])
            asteapta_salvat(pg, fals, 1)
            egal('engleză: suma scrisă „1,500,000.50” se citește corect', [fals.proiecte()[0].get('suma'), fals.proiecte()[0].get('val')], [1500000.5, 'EUR'])
            verifica('engleză: „corrected by a user” și „in the register”', 'corrected by a user' in rand_acord(pg, 'BERD', pC['id']).locator('td').nth(4).inner_text() and 'in the register' in rand_acord(pg, 'BERD', pC['id']).locator('td').nth(4).inner_text())
            ctx.close()

            # salvare eșuată: modificarea rămâne în coadă, marcată „nesalvat”, și se salvează după deblocare
            print('   · salvare eșuată: coada')
            fals = GitHubFals(intrari=[])
            ctx = context(b)
            pg = pagina(ctx, fals, hash_='#d=BERD', manual=OF, arhiva=False)
            debloca(pg)
            fals.cade_reteaua = True
            rC = rand_acord(pg, 'BERD', pC['id'])
            rC.locator('.edt[data-f="suma"]').click()
            rC.locator('[data-re=suma]').fill('777000')
            rC.locator('[data-re=val]').select_option('EUR')
            rC.locator('[data-re=suma]').press('Enter')
            pg.wait_for_function('document.querySelector("#sAcces").textContent.includes("Nu pot ajunge la GitHub")', timeout=10000)
            tx = rand_acord(pg, 'BERD', pC['id']).locator('td').nth(4).inner_text().replace('\xa0', ' ')
            verifica('eșec: suma nouă se vede în tabel, marcată „nesalvat”', '777.000 EUR' in tx and 'nesalvat' in tx, tx)
            pg.reload(wait_until='networkidle')
            pg.wait_for_selector('section.panel[data-d="BERD"] tr.ac')
            verifica('după reîncărcare: suma nesalvată se vede în continuare', '777.000 EUR' in rand_acord(pg, 'BERD', pC['id']).locator('td').nth(4).inner_text().replace('\xa0', ' '))
            fals.cade_reteaua = False
            debloca(pg)
            pg.wait_for_function('window.DebursariUI.stare().coada === 0', timeout=15000)
            egal('după deblocare, coada se salvează singură', [x.get('suma') for x in fals.proiecte()], [777000])
            ctx.close()

        # ---------------------------------------------------------------- 18. lățimea paginii
        if rulez(18):
            print('\n18. Lățimea paginii: cu toți donatorii bifați pagina nu se lărgește, iar de la ~1250 px tabelele încap în panou')
            fals = GitHubFals(intrari=[])
            ctx = context(b, viewport=(1280, 800))
            pg = pagina(ctx, fals, manual='real')
            pg.click('[data-act="toti-afisati"]')
            sel = pg.evaluate('window.DebursariUI.stare().sel')
            pg.wait_for_function('n => document.querySelectorAll("section.panel[data-d]").length === n', arg=len(sel), timeout=60000)
            egal('toți donatorii din listă sunt bifați, fiecare cu tabelul lui', [len(sel), pg.locator('section.panel[data-d] table.deb-tbl').count()], [pg.locator('.don input').count()] * 2)
            # cât iese pagina în lățime și cât iese tabelul din panoul lui (derulare orizontală)
            js_lat = '''() => { const de = document.documentElement, sc = [...document.querySelectorAll("section.panel .tbl-scroll")];
                return [de.scrollWidth - de.clientWidth, Math.max(0, ...sc.map(s => s.scrollWidth - s.clientWidth))]; }'''
            # conținut care iese din celula lui (în rândurile principale ale tabelelor)
            js_cel = '''() => { const r = [];
                document.querySelectorAll("section.panel table.deb-tbl > tbody > tr.ac").forEach(tr => [...tr.children].forEach((td, i) => {
                    const lim = td.getBoundingClientRect().right - parseFloat(getComputedStyle(td).paddingRight) + 1;
                    td.querySelectorAll("*").forEach(el => { const q = el.getBoundingClientRect(); if (q.width && q.right > lim) r.push([i + 1, (el.textContent || "").trim().slice(0, 20), Math.round(q.right - lim)]); });
                })); return r; }'''
            # cuvinte din antet rupte la mijloc: regula paginii lasă cuvintele să se rupă, ca textul să nu iasă din celulă; aici regula se scoate, ca să se vadă un cuvânt care nu încape
            js_antet = '''() => { const st = document.createElement("style"); st.textContent = "section.panel table.deb-tbl > thead th{overflow-wrap:normal !important}"; document.head.appendChild(st);
                const r = [...document.querySelectorAll("section.panel table.deb-tbl > thead th")].slice(0, 7).filter(t => t.scrollWidth > t.clientWidth + 1).map(t => t.textContent.trim().slice(0, 18));
                st.remove(); return r; }'''

            def masoara(lat, tabel_incape):
                pg.set_viewport_size({'width': lat, 'height': 800})
                pg.wait_for_timeout(250)
                pag, tab = pg.evaluate(js_lat)
                verifica('%d px: pagina nu se lărgește (nicio derulare orizontală a paginii)' % lat, pag <= 0, pag)
                if tabel_incape:
                    verifica('%d px: tabelele încap în panou (fără derulare în panou)' % lat, tab <= 1, tab)
                    peste = pg.evaluate(js_cel)
                    verifica('%d px: nimic nu iese din celula lui' % lat, peste == [], peste[:4])
                    rupte = pg.evaluate(js_antet)
                    verifica('%d px: niciun cuvânt din antet nu e rupt la mijloc' % lat, rupte == [], rupte)

            for lat in (1920, 1536, 1366, 1280, 1250):                      # laptop și desktop: tabelul încape întreg în panou
                masoara(lat, True)
            for lat in (1101, 1100, 1000, 920, 800, 390):                   # ecran mai îngust: tabelul se poate derula în panoul lui, dar pagina nu se lărgește
                masoara(lat, False)
            pg.evaluate('Traducere.seteaza("en")')
            pg.wait_for_timeout(400)
            for lat in (1280, 1250):                                        # și în engleză (antetele au alte cuvinte)
                masoara(lat, True)
            ctx.close()

        # ---------------------------------------------------------------- 19. proiecte cu grant și împrumut: un singur rând, sumele pe componente
        if rulez(19):
            print('\n19. Proiecte cu grant și împrumut: un singur rând, cu denumirea comună și sumele pe componente')
            fals = GitHubFals(intrari=[])
            ctx = context(b)
            pg = pagina(ctx, fals, hash_='#d=BERD&q=gazelor%20naturale')
            P = 'section.panel[data-d="BERD"]'
            PJ = "section.panel[data-d='BERD']"                       # același selector, pentru codul JavaScript evaluat în pagină (ghilimele simple în interior)
            U, IN_BERD = proiecte_unite(BERD), in_proiecte_unite(BERD)
            gaze = U[cheie_nume('Securitatea furnizării gazelor naturale')]
            grant = [x for x in gaze if x['categorie'] == 'Grant'][0]
            imprumut = [x for x in gaze if x['categorie'] == 'Împrumut'][0]
            total_unitati = len(BERD) - len(IN_BERD) + len(U)
            txt = lambda loc: loc.inner_text().replace('\xa0', ' ')
            h = pg.locator(P + ' tr.pg')
            egal('un singur rând pentru grantul și împrumutul cu aceeași denumire (în loc de două rânduri deosebite prin mențiune)', [h.count(), pg.locator(P + ' tr.ac.sub').count()], [1, 0])
            egal('denumirea comună, o singură dată, fără mențiunea „(grant, 2023)” / „(împrumut, 2022)”', h.locator('.pname').inner_text(), 'Securitatea furnizării gazelor naturale')
            meta = txt(h.locator('.pmeta'))
            verifica('sub denumire: tipurile componentelor și numărul de acorduri', 'grant + împrumut' in meta and '2 acorduri' in meta, meta)
            egal('coloana „Tip de finanțare”: ambele tipuri', h.locator('td').nth(3).locator('.tag').all_inner_texts(), ['Grant', 'Împrumut'])
            sume = txt(h.locator('td').nth(4))
            pe_tip = re.findall(r'(Grant|Împrumut)\s+([\d.,]+)\s+([A-Z]{3})', sume)
            egal('suma proiectului, separată pe componente: cât e grant și cât e împrumut, în valuta fiecăruia (calcul independent din registru)', pe_tip,
                 [('Grant', fmt_bani_ro(grant['suma']['v']), grant['suma']['val']), ('Împrumut', fmt_bani_ro(imprumut['suma']['v']), imprumut['suma']['val'])])
            total_gaze = fmt_ro(rotunjit(suma_numarata(gaze)), 0)
            verifica('totalul proiectului = grant + împrumut, în euro (%s)' % total_gaze, re.search(r'TOTAL\s+(≈ )?' + re.escape(total_gaze) + r' EUR', sume, re.I) is not None, sume)
            verifica('rândul proiectului nu are creioane de editare, nici butonul „Debursare” (ele sunt la fiecare componentă)', h.locator('.edt').count() == 0 and h.locator('[data-act="adauga"]').count() == 0)
            egal('proiectul e închis: butonul spune „Deschide acordurile proiectului”, iar acordurile componente nu sunt în tabel',
                 [h.locator('.exp').get_attribute('aria-expanded'), h.locator('.exp').get_attribute('aria-label').startswith('Deschide acordurile proiectului: '), pg.locator(P + ' tr.ac[data-k="BERD|%s"]' % grant['id']).count()], ['false', True, 0])
            dsum = txt(pg.locator(P + ' .dsum'))
            m = re.search(r'(\d+) proiecte din (\d+) \((\d+) acorduri\)', dsum)
            n_simple = pg.locator(P + ' tr.ac:not(.sub)').count()
            egal('antetul donatorului numără proiectele (un proiect unit = unul) și spune între paranteze câte acorduri sunt', [int(x) for x in m.groups()] if m else dsum, [1 + n_simple, total_unitati, len(gaze) + n_simple])
            # deschidere / închidere
            h.locator('.exp').click()
            pg.wait_for_selector(P + ' tr.ac.sub')
            sub = pg.locator(P + ' tr.ac.sub')
            egal('deschis: cele două acorduri componente apar sub proiect, întâi grantul, apoi împrumutul', [sub.count(), sub.evaluate_all('l => l.map(r => r.getAttribute("data-k"))')], [2, ['BERD|' + grant['id'], 'BERD|' + imprumut['id']]])
            egal('componentele se numesc după tip și an (denumirea comună e deasupra)', sub.locator('.pname').all_inner_texts(), ['Grant, ' + grant['semnat'][-4:], 'Împrumut, ' + imprumut['semnat'][-4:]])
            egal('fiecare componentă își are tipul și suma ei, ca un rând obișnuit', [[fmt_bani_ro(a['suma']['v']) in txt(sub.nth(i).locator('td').nth(4)), sub.nth(i).locator('.tag').inner_text()] for i, a in enumerate((grant, imprumut))],
                 [[True, 'Grant'], [True, 'Împrumut']])
            egal('deschis: aria-expanded, iar rândul proiectului rămâne deasupra componentelor', [h.locator('.exp').get_attribute('aria-expanded'), pg.evaluate('document.querySelector("' + PJ + ' tr.pg").nextElementSibling.getAttribute("data-k")')], ['true', 'BERD|' + grant['id']])
            verifica('numărătorile rămân pe acorduri: indicatorul „Proiecte” = acordurile lui BERD, suma din antet = calculul independent', pg.locator('.kpi .val').first.inner_text() == str(len(BERD)) and
                     ('suma ' + fmt_ro(rotunjit(suma_numarata([a for a in BERD])), 0)) not in dsum, (pg.locator('.kpi .val').first.inner_text(), dsum))
            # detaliile unei componente, apoi închiderea și redeschiderea proiectului
            rg = pg.locator(P + ' tr.ac.sub[data-k="BERD|%s"]' % grant['id'])
            rg.locator('.exp').click()
            pg.wait_for_selector(P + ' tr.det[data-k="BERD|%s"]' % grant['id'])
            egal('detaliile grantului se deschid sub componenta lui', pg.evaluate('document.querySelector("' + PJ + ' tr.ac.sub[data-k=\'BERD|' + grant['id'] + '\']").nextElementSibling.className'), 'det sub')
            h.locator('.exp').click()
            pg.wait_for_selector(P + ' tr.ac.sub', state='detached')
            egal('închis din nou: nici componentele, nici detaliile lor nu mai sunt în tabel', [pg.locator(P + ' tr.ac.sub').count(), pg.locator(P + ' tr.det').count(), pg.locator(P + ' tr.pg').count()], [0, 0, 1])
            h.locator('.exp').click()
            pg.wait_for_selector(P + ' tr.det[data-k="BERD|%s"]' % grant['id'])
            egal('redeschis: detaliile deschise înainte rămân deschise', [pg.locator(P + ' tr.ac.sub').count(), pg.locator(P + ' tr.det').count()], [2, 1])
            rg.locator('.exp').click()
            pg.wait_for_selector(P + ' tr.det', state='detached')
            # clic pe rând (nu doar pe buton) și tastatură
            h.locator('td').first.click()
            pg.wait_for_selector(P + ' tr.ac.sub', state='detached')
            egal('un clic pe rândul proiectului îl închide (ca la un rând obișnuit)', [pg.locator(P + ' tr.ac.sub').count(), h.locator('.exp').get_attribute('aria-expanded')], [0, 'false'])
            h.locator('.exp').focus()
            pg.keyboard.press('Enter')
            pg.wait_for_selector(P + ' tr.ac.sub')
            verifica('Enter pe butonul proiectului îl deschide, iar focusul rămâne pe buton', h.locator('.exp').get_attribute('aria-expanded') == 'true' and pg.evaluate('document.activeElement.classList.contains("exp") && document.activeElement.closest("tr").classList.contains("pg")'))
            # filtre: fără celălalt tip, proiectul nu se mai unește; cu toate tipurile revine
            pg.select_option('#ftip', 'Împrumut')
            pg.wait_for_timeout(250)
            egal('filtrul „Împrumut”: nu mai există proiect unit; împrumutul e rând obișnuit, cu mențiunea de deosebire', [pg.locator(P + ' tr.pg').count(), [x for x in pg.locator(P + ' tr.ac:not(.sub) .pname').all_inner_texts() if 'împrumut, ' + imprumut['semnat'][-4:] in x]],
                 [0, [curata_nume(imprumut.get('scurt') or imprumut['nume']) + ' (împrumut, ' + imprumut['semnat'][-4:] + ')']])
            pg.select_option('#ftip', '')
            pg.wait_for_selector(P + ' tr.pg')
            egal('fără filtru, proiectul unit revine și rămâne deschis', [pg.locator(P + ' tr.pg').count(), pg.locator(P + ' tr.ac.sub').count()], [1, 2])
            # ordine: proiectul unit se așază după totalul lui; fără căutare, tabelul întreg
            pg.fill('#q', '')
            pg.wait_for_function('n => document.querySelectorAll("section.panel[data-d=\'BERD\'] tr.pg").length === n', arg=len(U), timeout=15000)
            by_id = {a['id']: a for a in ACORDURI}
            by_cheie = {k: m for k, m in U.items()}
            def total_unit(chei):
                if chei.startswith('BERD|') and chei[5:] in by_id:
                    return eur(by_id[chei[5:]])
                m = by_cheie[chei[5:]]
                tot = suma_numarata(m)
                return tot if any(x.get('inTotal') == 'numarat' and eur(x) is not None for x in m) else (sum(eur(x) for x in m if eur(x) is not None) or None)
            chei_ordine = pg.evaluate('[...document.querySelectorAll("' + PJ + ' tbody > tr.pg, ' + PJ + ' tbody > tr.ac:not(.sub)")].map(r => r.getAttribute("data-gr") || r.getAttribute("data-k"))')
            totaluri = [total_unit(c) for c in chei_ordine]
            cu = [x for x in totaluri if x is not None]
            verifica('ordinea implicită (după sumă): proiectele, unite sau nu, sunt în ordinea descrescătoare a sumei sau a totalului lor; fără sumă, la coadă', cu == sorted(cu, reverse=True) and totaluri[:len(cu)] == cu, totaluri[:8])
            egal('proiectul cu totalul cel mai mare e primul rând (grant + împrumut)', chei_ordine[0], 'BERD|' + cheie_nume('Securitatea furnizării gazelor naturale'))
            egal('fără căutare: câte un rând pentru fiecare proiect (%d) și numărul de acorduri între paranteze' % total_unitati,
                 [len(chei_ordine), re.search(r'(\d+) proiecte \((\d+) acorduri\)', txt(pg.locator(P + ' .dsum'))).groups()], [total_unitati, (str(total_unitati), str(len(BERD)))])
            # engleză
            pg.evaluate('Traducere.seteaza("en")')
            pg.wait_for_timeout(500)
            h = pg.locator(P + ' tr.pg').first
            hu = pg.locator(P + ' tr.pg').filter(has_text='Securitatea furnizării gazelor naturale')
            sume_en = txt(hu.locator('td').nth(4))
            verifica('în engleză: tipurile (Grant, Loan), „2 agreements”, „Total”, sume cu virgulă la mii', 'grant + loan' in txt(hu.locator('.pmeta')) and '2 agreements' in txt(hu.locator('.pmeta')) and hu.locator('td').nth(3).locator('.tag').all_inner_texts() == ['Grant', 'Loan'] and
                     re.search(r'Grant\s+' + re.escape(fmt_en(grant['suma']['v'])) + r' EUR', sume_en) is not None and re.search(r'Loan\s+' + re.escape(fmt_en(imprumut['suma']['v'])) + r' EUR', sume_en) is not None and 'total' in sume_en.lower(), sume_en)
            egal('în engleză: componentele se numesc „Grant, 2023” și „Loan, 2022”; butonul: „Close the agreements of the project”',
                 [pg.locator(P + ' tr.ac.sub .pname').all_inner_texts()[:2], hu.locator('.exp').get_attribute('aria-label').startswith('Close the agreements of the project: ')],
                 [['Grant, ' + grant['semnat'][-4:], 'Loan, ' + imprumut['semnat'][-4:]], True])
            egal('în engleză: antetul donatorului spune „projects” și „agreements”', re.search(r'(\d+) projects \((\d+) agreements\)', txt(pg.locator(P + ' .dsum'))) is not None, True)
            pg.evaluate('Traducere.seteaza("ro")')
            pg.wait_for_timeout(300)
            ctx.close()

            # telefon: cartonaș pentru proiect, cartonașe mai înguste pentru componente; pagina nu se lărgește
            print('   · telefon')
            ctx = context(b, viewport=(390, 800))
            pg = pagina(ctx, GitHubFals(intrari=[]), hash_='#d=BERD&q=gazelor%20naturale')
            h = pg.locator(P + ' tr.pg')
            verifica('telefon: rândul proiectului e un cartonaș (grilă), cu eticheta fiecărei celule, iar antetul tabelului e ascuns', pg.evaluate('getComputedStyle(document.querySelector("' + PJ + ' tr.pg")).display') == 'grid' and
                     h.locator('td[data-l]').count() == 6 and pg.evaluate('getComputedStyle(document.querySelector("' + PJ + ' thead")).display') == 'none')
            h.locator('.exp').click()
            pg.wait_for_selector(P + ' tr.ac.sub')
            marg = pg.evaluate('[document.querySelector("' + PJ + ' tr.pg").getBoundingClientRect().left, document.querySelector("' + PJ + ' tr.ac.sub").getBoundingClientRect().left]')
            verifica('telefon: componentele sunt cartonașe trase spre dreapta față de proiect (cu cel puțin 10 px)', marg[1] - marg[0] >= 10, marg)
            lat = pg.evaluate('document.documentElement.scrollWidth - document.documentElement.clientWidth')
            verifica('telefon: pagina nu se lărgește (fără derulare orizontală)', lat <= 0, lat)
            verifica('telefon: sumele pe componente se văd întregi în cartonaș', all(fmt_bani_ro(a['suma']['v']) in txt(h.locator('td').nth(4)) for a in (grant, imprumut)) and
                     pg.evaluate('(() => { const c = document.querySelector("' + PJ + ' tr.pg td:nth-child(5)").getBoundingClientRect(), r = document.querySelector("' + PJ + ' tr.pg").getBoundingClientRect(); return c.right <= r.right + 1; })()'))
            ctx.close()

            # proiectul cu două granturi și un împrumut (BIRD, „Operațiunea de politici de dezvoltare 2”): detaliile unei componente sunt înalte și împing împrumutul sub ele,
            # în afara ferestrei; linia „Componentele proiectului” din detalii îl arată, iar un clic pe el duce la el
            print('   · linia „Componentele proiectului”, în detaliile unei componente')
            ctx = context(b, viewport=(1080, 800))
            pg = pagina(ctx, GitHubFals(intrari=[]), hash_='#d=BIRD&q=politici%20de%20dezvoltare%202')
            PB, PJB = 'section.panel[data-d="BIRD"]', "section.panel[data-d='BIRD']"
            cheie_dpo = cheie_nume('Moldova, măsuri în situație de urgență, reziliență și competitivitate. Operațiunea de politici de dezvoltare 2')
            dpo = proiecte_unite(acorduri_donator('BIRD'))[cheie_dpo]
            egal('în registru, proiectul are două granturi și un împrumut', sorted(x['categorie'] for x in dpo), ['Grant', 'Grant', 'Împrumut'])
            id_imp = [x['id'] for x in dpo if x['categorie'] == 'Împrumut'][0]
            pg.locator(PB + ' tr.pg[data-gr="BIRD|%s"] .exp' % cheie_dpo).click()
            pg.wait_for_selector(PB + ' tr.ac.sub')
            comp = pg.locator(PB + ' tr.ac.sub')
            nume_comp = comp.locator('.pname').all_inner_texts()
            egal('proiectul deschis: trei componente, în ordinea grant, grant, împrumut', [comp.count(), comp.locator('.tag').all_inner_texts()], [3, ['Grant', 'Grant', 'Împrumut']])
            comp.first.locator('.exp').click()
            pg.wait_for_selector(PB + ' tr.det')
            strip = pg.locator(PB + ' tr.det .det-comp')
            egal('detaliile primului grant: linia „Componentele proiectului” are toate cele trei componente, cu numele din rândurile lor', [strip.locator('.dc-l').text_content(), strip.locator('.dc').all_inner_texts()], ['Componentele proiectului', nume_comp])
            egal('componenta curentă (primul grant) e marcată, celelalte două sunt butoane', [strip.locator('.dc.cur').all_inner_texts(), strip.locator('.dc.cur').get_attribute('aria-current'), strip.locator('button.dc').count()], [[nume_comp[0]], 'true', 2])
            box = strip.locator('button.dc').last.bounding_box()
            verifica('împrumutul se vede în linie, pe ecran, fără derulare', box is not None and 0 <= box['y'] and box['y'] + box['height'] <= 800, box)
            verifica('(cauza) rândul împrumutului e sub detaliile grantului, în afara ferestrei', pg.locator(PB + ' tr.ac.sub[data-k="BIRD|%s"]' % id_imp).bounding_box()['y'] > 800)
            strip.locator('button.dc').last.click()
            pg.wait_for_selector(PB + ' tr.det[data-k="BIRD|%s"]' % id_imp)
            egal('un clic pe „Împrumut”: se deschid detaliile împrumutului, cele ale grantului se închid', pg.locator(PB + ' tr.det').evaluate_all('l => l.map(r => r.getAttribute("data-k"))'), ['BIRD|' + id_imp])
            pg.wait_for_function('s => { const t = document.querySelector(s).getBoundingClientRect().top; return t >= 0 && t < 300; }', arg=PJB + " tr.ac.sub[data-k='BIRD|" + id_imp + "']", timeout=10000)
            verifica('pagina a derulat la rândul împrumutului (sub bara de acces), iar rândul e deschis', pg.locator(PB + ' tr.ac.sub[data-k="BIRD|%s"]' % id_imp).get_attribute('class').find('deschis') >= 0)
            egal('focusul e pe butonul rândului împrumutului', pg.evaluate('(() => { const a = document.activeElement; return [a.classList.contains("exp"), a.closest("tr").getAttribute("data-k")]; })()'), [True, 'BIRD|' + id_imp])
            egal('în detaliile împrumutului, componenta curentă e împrumutul, iar celelalte două sunt butoane', [pg.locator(PB + ' tr.det .det-comp .dc.cur').all_inner_texts(), pg.locator(PB + ' tr.det .det-comp button.dc').all_inner_texts()], [[nume_comp[2]], nume_comp[:2]])
            # tastatură: Enter pe butonul celui de-al doilea grant
            pg.locator(PB + ' tr.det .det-comp button.dc').nth(1).focus()
            pg.keyboard.press('Enter')
            pg.wait_for_selector(PB + ' tr.det[data-k="BIRD|%s"]' % [x['id'] for x in dpo if x['categorie'] == 'Grant'][1])
            egal('Enter pe butonul unei componente deschide detaliile ei și le închide pe celelalte', [pg.locator(PB + ' tr.det').count(), pg.locator(PB + ' tr.det .det-comp .dc.cur').all_inner_texts()], [1, [nume_comp[1]]])
            # proiectul închis și redeschis: linia nu rămâne decât în detaliile deschise
            pg.locator(PB + ' tr.pg[data-gr="BIRD|%s"] .exp' % cheie_dpo).click()
            pg.wait_for_selector(PB + ' tr.ac.sub', state='detached')
            egal('proiectul închis: nici componentele, nici linia nu mai sunt în tabel', [pg.locator(PB + ' tr.ac.sub').count(), pg.locator(PB + ' .det-comp').count()], [0, 0])
            # un rând obișnuit (nu componentă) nu are linia
            rand_simplu = pg.locator(PB + ' tr.ac:not(.sub)').first
            rand_simplu.locator('.exp').click()
            pg.wait_for_selector(PB + ' tr.det')
            egal('detaliile unui rând obișnuit nu au linia „Componentele proiectului”', pg.locator(PB + ' .det-comp').count(), 0)
            rand_simplu.locator('.exp').click()
            # engleză
            pg.locator(PB + ' tr.pg[data-gr="BIRD|%s"] .exp' % cheie_dpo).click()
            pg.wait_for_selector(PB + ' tr.ac.sub')
            pg.locator(PB + ' tr.ac.sub').first.locator('.exp').click()
            pg.wait_for_selector(PB + ' tr.det .det-comp')
            pg.evaluate('Traducere.seteaza("en")')
            pg.wait_for_timeout(500)
            stripe = pg.locator(PB + ' tr.det .det-comp').first               # detaliile deschise mai înainte (al doilea grant) au rămas deschise
            egal('în engleză: „Components of the project” și numele componentelor (Grant, Grant, Loan)', [stripe.locator('.dc-l').text_content(), [x.split(',')[0] for x in stripe.locator('.dc').all_inner_texts()]], ['Components of the project', ['Grant', 'Grant', 'Loan']])
            pg.evaluate('Traducere.seteaza("ro")')
            pg.wait_for_timeout(300)
            ctx.close()
            # telefon: pastilele se așază pe rânduri, în cartonașul detaliilor; pagina nu se lărgește
            ctx = context(b, viewport=(390, 800))
            pg = pagina(ctx, GitHubFals(intrari=[]), hash_='#d=BIRD&q=politici%20de%20dezvoltare%202')
            pg.locator(PB + ' tr.pg[data-gr="BIRD|%s"] .exp' % cheie_dpo).click()
            pg.wait_for_selector(PB + ' tr.ac.sub')
            pg.locator(PB + ' tr.ac.sub').first.locator('.exp').click()
            pg.wait_for_selector(PB + ' tr.det .det-comp')
            lat = pg.evaluate('document.documentElement.scrollWidth - document.documentElement.clientWidth')
            verifica('telefon: cu linia deschisă pagina nu se lărgește', lat <= 0, lat)
            verifica('telefon: pastilele componentelor încap în cartonașul detaliilor', pg.evaluate('(() => { const td = document.querySelector("' + PJB + ' tr.det > td").getBoundingClientRect(); return [...document.querySelectorAll("' + PJB + ' tr.det .dc")].every(b => { const r = b.getBoundingClientRect(); return r.left >= td.left - 1 && r.right <= td.right + 1; }); })()'))
            ctx.close()

            # după deblocare: componentele se editează ca orice rând; rândul proiectului se reface cu sumele noi
            print('   · editare și debursare la o componentă')
            fals = GitHubFals(intrari=[])
            ctx = context(b)
            pg = pagina(ctx, fals, hash_='#d=BERD&q=gazelor%20naturale')
            debloca(pg)
            verifica('deblocat', deblocat(pg))
            h = pg.locator(P + ' tr.pg')
            h.locator('.exp').click()
            pg.wait_for_selector(P + ' tr.ac.sub')
            verifica('după deblocare: creioanele și butonul „Debursare” sunt la componente (3 + 1 pe fiecare), nu la rândul proiectului', pg.locator(P + ' tr.ac.sub .edt').count() == 6 and pg.locator(P + ' tr.ac.sub [data-act="adauga"]').count() == 2 and
                     h.locator('.edt').count() == 0 and h.locator('[data-act="adauga"]').count() == 0)
            rg = pg.locator(P + ' tr.ac.sub[data-k="BERD|%s"]' % grant['id'])
            rg.locator('.edt[data-f="suma"]').click()
            pg.wait_for_selector(P + ' tr.ac.edit')
            rg.locator('[data-re=suma]').fill('40.000.000')
            rg.locator('[data-re=suma]').press('Enter')
            asteapta_salvat(pg, fals, 1)
            h = pg.locator(P + ' tr.pg')
            sume = txt(h.locator('td').nth(4))
            nou_total = 40000000 + imprumut['suma']['v']
            verifica('suma grantului corectată: rândul proiectului arată grantul de 40.000.000 EUR și totalul nou (%s EUR); proiectul rămâne deschis' % fmt_ro(nou_total, 0),
                     re.search(r'Grant\s+40\.000\.000 EUR', sume) and re.search(r'TOTAL\s+' + re.escape(fmt_ro(nou_total, 0)) + r' EUR', sume, re.I) and pg.locator(P + ' tr.ac.sub').count() == 2, sume)
            verifica('componenta corectată arată „corectată de utilizator” și suma din registru', 'corectată de utilizator' in txt(pg.locator(P + ' tr.ac.sub[data-k="BERD|%s"]' % grant['id']).locator('td').nth(4)))
            # o debursare la împrumut: se vede și în rândul proiectului, ca procent din totalul proiectului
            det = deschide_rand(pg, 'BERD', imprumut)
            completeaza(det, suma='1.000.000', data='2026-10-01', val='EUR', nota='probă pentru proiectul unit')
            det.locator('form.deb-form button[type=submit]').click()
            asteapta_salvat(pg, fals, 2)
            h = pg.locator(P + ' tr.pg')
            deb = txt(h.locator('td').nth(5))
            pct = 1000000 / nou_total * 100
            verifica('debursarea unei componente apare în rândul proiectului: 1.000.000 EUR, 1 debursare, procentul din totalul proiectului', '1.000.000' in deb and '1 debursare' in deb and ('%s%%' % fmt_ro(round(pct, 1), 1)) in deb, deb)
            egal('antetul donatorului: debursat 1.000.000 EUR', 'debursat 1.000.000 EUR' in txt(pg.locator(P + ' .dsum')), True)
            # Excel: tot câte un rând pe acord (nu pe proiect unit), cu denumirile deosebite și suma fiecărui acord
            def excel_berd(nume):
                with pg.expect_download(timeout=60000) as d:
                    pg.click(P + ' [data-act="excel-donator"]')
                cale = DESC / nume
                d.value.save_as(str(cale))
                ws = openpyxl.load_workbook(cale)['BERD']
                for rr in ws.iter_rows(min_row=1, max_row=12):
                    if 'Proiectul' in [c.value for c in rr]:
                        return ws, [c.value for c in rr], rr[0].row
            nume_g = curata_nume(grant.get('scurt') or grant['nume']) + ' (grant, ' + grant['semnat'][-4:] + ')'
            nume_i = curata_nume(imprumut.get('scurt') or imprumut['nume']) + ' (împrumut, ' + imprumut['semnat'][-4:] + ')'
            ws, antet, ra = excel_berd('berd-proiect-unit-cautat.xlsx')                  # căutarea „gazelor naturale” e încă activă: se exportă doar proiectul unit
            iP, iS, iD = antet.index('Proiectul'), antet.index('Suma proiectului'), antet.index('Debursat (echivalent EUR)')
            rx = {r[iP].value: r for r in ws.iter_rows(min_row=ra + 1, max_row=ra + 2)}
            egal('Excel (cu căutarea activă): proiectul unit are două rânduri, câte unul pe acord, cu denumirile deosebite', [randuri_date(ws, ra), sorted(rx)], [2, sorted([nume_g, nume_i])])
            egal('Excel: suma fiecărui acord, în valuta lui (grantul, cu suma corectată)', [[rx[nume_g][iS].value, rx[nume_g][iS + 1].value], [rx[nume_i][iS].value, rx[nume_i][iS + 1].value]],
                 [[40000000, 'EUR'], [imprumut['suma']['v'], imprumut['suma']['val']]])
            verifica('Excel: debursarea (1.000.000 EUR) e la rândul împrumutului, nu la al grantului', abs((rx[nume_i][iD].value or 0) - 1000000) < 1 and not rx[nume_g][iD].value, [rx[nume_i][iD].value, rx[nume_g][iD].value])
            pg.fill('#q', '')
            pg.wait_for_function('n => document.querySelectorAll("section.panel[data-d=\'BERD\'] tr.pg").length === n', arg=len(U), timeout=15000)
            ws, antet, ra = excel_berd('berd-proiecte-unite.xlsx')
            egal('Excel (fără căutare): tot un rând pe acord (%d), nu pe proiect unit (%d)' % (len(BERD), total_unitati), randuri_date(ws, ra), len(BERD))
            nume_xl = [r[iP].value for r in ws.iter_rows(min_row=ra + 1, max_row=ra + len(BERD))]
            verifica('Excel: fiecare acord al unui proiect unit își păstrează rândul și mențiunea de deosebire (grant / împrumut, an)', nume_g in nume_xl and nume_i in nume_xl and len(set(nume_xl)) == len(nume_xl), nume_xl[:6])
            ctx.close()

        b.close()
except Exception as e:                                           # o eroare a testului însuși trebuie să se vadă
    import traceback
    traceback.print_exc()
    picat.append('eroare în teste: ' + repr(e)[:200])

print()
verifica('nicio eroare JavaScript și niciun mesaj de eroare în consolă', not ERORI, ERORI[:6])
verifica('nicio cerere în afara paginii, a api.github.com și a proxy-ului AMP', not CERERI_STRAINE, CERERI_STRAINE[:6])
verifica('cererile către AMP: doar raportul 661 (POST) și lista de linkuri a amp-linkuri.js, doar la proxy-ul amp.vivi.md',
         all(u.startswith('https://amp.vivi.md/rest/data/') and (('/saikureport/export/csv/661' in u and m == 'POST') or u.endswith('/rest/data/report/custom/paginate')) for m, u in CERERI_AMP), CERERI_AMP[:4])
print('\n' + (f'{len(picat)} teste au picat: ' + '; '.join(picat) if picat else 'Toate testele au trecut.'))
sys.exit(1 if picat else 0)
