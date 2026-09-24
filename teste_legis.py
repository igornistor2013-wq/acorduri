"""Testele verificării legis.md. Rulate de workflow înaintea căutării.

    python teste_legis.py            # clasificator + unire (rapid, fără browser)
    python teste_legis.py --browser  # plus un test complet cu Playwright pe un
                                     # legis.md simulat local (inclusiv blocajul Cloudflare)
"""
import json, shutil, subprocess, sys, tempfile, threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import urlparse, parse_qs

AICI = Path(__file__).resolve().parent
sys.path.insert(0, str(AICI))
from legis_clasifica import clasifica, partener
import legis_watch as w
import legis_pagina as pagina

picat = []


def verifica(nume, conditie, detaliu=''):
    print(('  ok   ' if conditie else '  PICĂ ') + nume + ('' if conditie else f'  → {detaliu}'))
    if not conditie:
        picat.append(nume)


print('Clasificator')
CAZURI = [
    ('pentru ratificarea Acordului de împrumut dintre Republica Moldova și Banca Internațională pentru Reconstrucție și Dezvoltare', 'Împrumut', 'BIRD'),
    ('pentru ratificarea Acordului-cadru de împrumut dintre Republica Moldova și Banca de Dezvoltare a Consiliului Europei pentru Proiectul „Locuințe publice III”', 'Împrumut', 'CEB'),
    ('privind ratificarea Acordului de facilitate de împrumut dintre Republica Moldova și Majestatea Sa Regele de drept al Canadei', 'Împrumut', 'Canada'),
    ('pentru ratificarea Acordului de grant, întocmit prin schimb de note, dintre Guvernul Republicii Moldova și Guvernul Japoniei privind asigurarea fermierilor cu fertilizanți', 'Grant', 'Japonia'),
    ('pentru ratificarea Acordului dintre Republica Moldova și Bosnia și Herțegovina privind asistența juridică reciprocă', None, None),
    ('cu privire la acordarea ajutorului umanitar populației din Republica Turcia', None, None),
    ('pentru ratificarea Acordului dintre Republica Moldova și Uniunea Europeană privind participarea Republicii Moldova la Programul Europa Digitală', None, None),
    ('cu privire la reperfectarea licenţei Asociaţiei de Economii şi Împrumut „CIRCULA”', None, None),
    # partenerul din formulări vechi
    ('pentru ratificarea Acordului de finanţare dintre Republica Moldova şi Asociaţia Internaţională de Dezvoltare privind realizarea Proiectului „Suport de urgenţă pentru agricultura Moldovei”', 'Asistență financiară', 'AID'),
    ('pentru ratificarea Acordului de împrumut dintre Guvernul Republicii Moldova și Guvernul Republicii Polone în sumă de 20 de milioane de euro', 'Împrumut', 'Polonia'),
    ('pentru ratificarea Acordului-cadru dintre Guvernul Republicii Moldova şi Comisia Comunităţilor Europene privind asistenţa externă', 'Asistență financiară', 'UE'),
    # acte de cadru, nu acorduri
    ('pentru modificarea Hotărârii Guvernului nr. 246/2010 cu privire la modul de aplicare a facilităților fiscale și vamale aferente realizării proiectelor de asistență tehnică și investițională în derulare, care cad sub incidența tratatelor internaționale la care Republica Moldova este parte sau a contractelor de stat', None, None),
    ('cu privire la Programul de asistenţă tehnică pentru anii 2001-2002', None, None),
    ('cu privire la aprobarea Regulamentului privind autorizarea centrelor de asistenţă tehnică pentru maşinile de casă şi de control/imprimantele fiscale', None, None),
    ('cu privire la Oficiul de Gestionare a Programelor de Asistență Externă', None, None),
    ('privind contractele de credit pentru consumatori', None, None),
    ('pentru ratificarea Acordului de finanțare dintre Republica Moldova și Fondul Internațional pentru Dezvoltarea Agricolă în vederea realizării Proiectului de Reziliență Rurală (IFAD VII)', 'Asistență financiară', None),
]
for t, cat, part in CAZURI:
    c = clasifica(t)
    verifica(f'{(cat or "respins"):10} {t[:70]}…', c == cat, f'a dat {c}')
    if cat and part:
        verifica(f'partener {part}', part in partener(t), partener(t))

print('Diacritice stricate')
verifica('„оmprumut, finanюare, Germanг” reparat',
         pagina.repara('Acordului de оmprumut, finanюare între Banca Germanг') == 'Acordului de împrumut, finanţare între Banca Germană')

print('Ani de căutat')
import datetime
verifica('septembrie → doar anul curent', w.ani_de_cautat(datetime.date(2026, 9, 1)) == ['2026'])
verifica('februarie → și anul trecut', w.ani_de_cautat(datetime.date(2027, 2, 1)) == ['2027', '2026'])

print('Unire cu baza')
tmp = Path(tempfile.mkdtemp())
try:
    for f in ('acorduri.html',):
        shutil.copy(AICI / f, tmp / f)
    baza = [{'id': '1', 'c': 'LP1/2026', 'pub': '01-01-2026', 't': 'pentru ratificarea Acordului de împrumut dintre Republica Moldova și BERD', 'kw': []}]
    json.dump(baza, open(tmp / 'legis_brut.json', 'w', encoding='utf-8'))
    nou = {'ani': ['2026'], 'err': [], 'gasite': 3, 'rows': [
        {'id': '1', 'c': 'LP1/2026', 'pub': '01-01-2026', 't': 'Modificat pentru ratificarea Acordului de împrumut dintre Republica Moldova și BERD'},
        {'id': '2', 'c': 'HG2/2026', 'pub': '02-02-2026', 't': 'cu privire la aprobarea semnării Acordului de grant dintre Republica Moldova și Uniunea Europeană'},
        {'id': '3', 'c': 'HG3/2026', 'pub': '03-02-2026', 't': 'cu privire la aprobarea Regulamentului intern'}]}
    r = w.actualizeaza(nou, tmp / 'legis_brut.json', tmp)
    verifica('2 acte noi, 1 acord', (r['noi'], r['acorduri_noi']) == (2, 1), r)
    b2 = json.load(open(tmp / 'legis_brut.json', encoding='utf-8'))
    verifica('titlul actualizat la actul existent', b2[0]['t'].startswith('Modificat'))
    verifica('pagina conține acordul nou', 'HG2/2026' in (tmp / 'legis_acorduri.html').read_text(encoding='utf-8'))
    r2 = w.actualizeaza(nou, tmp / 'legis_brut.json', tmp)
    verifica('a doua rulare: nimic nou (fără dubluri)', r2['noi'] == 0, r2)
finally:
    shutil.rmtree(tmp, ignore_errors=True)


# ------------------------------------------------ test complet, cu browser
if '--browser' in sys.argv:
    print('Browser, pe legis.md simulat')

    class Legis(BaseHTTPRequestHandler):
        blocat = False
        ultima = {}

        def log_message(self, *a):
            pass

        def trimite(self, html):
            b = html.encode('utf-8')
            self.send_response(200); self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.send_header('Content-Length', str(len(b))); self.end_headers(); self.wfile.write(b)

        def do_GET(self):
            u = urlparse(self.path)
            if Legis.blocat:
                return self.trimite('<html><title>Just a moment...</title><body>Just a moment...</body></html>')
            if u.path == '/cautare/getResults':
                Legis.ultima = {k: v[0] for k, v in parse_qs(u.query).items()}
                return self.trimite('<html><body>rezultate</body></html>')
            if u.path == '/cautare/getAjaxContent':
                kw, an = Legis.ultima.get('search_string', ''), Legis.ultima.get('datepicker1', '')
                rand = ''
                if kw == 'împrumut' and an == '2026':
                    rand = ('<tr><td><a href="/cautare/getResults?doc_id=900001">(LP500/2026)</a>20-09-2026</td>'
                            '<td>pentru ratificarea Acordului de împrumut dintre Republica Moldova și Banca Europeană de Investiții</td></tr>'
                            '<tr><td><a href="/cautare/getResults?doc_id=1">(LP1/2026)</a>01-01-2026</td>'
                            '<td>pentru ratificarea Acordului de împrumut dintre Republica Moldova și BERD</td></tr>')
                return self.trimite('<table>' + rand + '</table>')
            return self.trimite('<html><body>Registrul de stat al actelor juridice</body></html>')

    srv = HTTPServer(('127.0.0.1', 0), Legis)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    url = f'http://127.0.0.1:{srv.server_port}/'

    tmp = Path(tempfile.mkdtemp())
    # rulările de test nu scriu în rezumatul GitHub — altfel actul simulat
    # LP500/2026 apare acolo ca și cum ar fi fost găsit pe legis.md
    import os
    env_test = {k: v for k, v in os.environ.items() if k != 'GITHUB_STEP_SUMMARY'}
    try:
        for f in ('acorduri.html', 'legis_watch.py', 'legis_pagina.py', 'legis_clasifica.py',
                  'monitor_watch.py', 'legis_extrage.js'):
            shutil.copy(AICI / f, tmp / f)
        json.dump([{'id': '1', 'c': 'LP1/2026', 'pub': '01-01-2026',
                    't': 'pentru ratificarea Acordului de împrumut dintre Republica Moldova și BERD', 'kw': []}],
                  open(tmp / 'legis_brut.json', 'w', encoding='utf-8'))

        p = subprocess.run([sys.executable, str(tmp / 'legis_watch.py'), '--url', url, '--ani', '2026', '--asteapta-cf', '5'],
                           capture_output=True, text=True, timeout=600, env=env_test)
        verifica('rulare reușită (cod 0)', p.returncode == 0, p.stdout[-800:] + p.stderr[-800:])
        rap = (tmp / 'raport_legis.md').read_text(encoding='utf-8') if (tmp / 'raport_legis.md').exists() else ''
        verifica('raportul are acordul nou LP500/2026', 'LP500/2026' in rap, rap)
        verifica('actul deja cunoscut nu e raportat', 'LP1/2026' not in rap, rap)

        Legis.blocat = True
        p = subprocess.run([sys.executable, str(tmp / 'legis_watch.py'), '--url', url, '--ani', '2026', '--asteapta-cf', '5'],
                           capture_output=True, text=True, timeout=300, env=env_test)
        verifica('blocat de Cloudflare → cod 3, fără modificări', p.returncode == 3, p.stdout[-500:])
    finally:
        srv.shutdown()
        shutil.rmtree(tmp, ignore_errors=True)

print()
if picat:
    print(f'Au picat {len(picat)} teste.'); sys.exit(1)
print('Toate testele legis au trecut.')
