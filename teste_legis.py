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
print()
print('Sumele din textul actelor (legis_sume.py)')
import legis_sume as ls
SUME = [
    # textul real al art. 1 din LP14/2023: titlul nu are suma, textul o are
    ('Art. 1. – Se ratifică Acordul de împrumut dintre Republica Moldova și Banca Europeană pentru Reconstrucție '
     'și Dezvoltare în vederea realizării Proiectului „Deșeuri solide în Republica Moldova”, în sumă de 25 de milioane '
     'de euro, semnat la Chișinău la 4 ianuarie 2023.', (25000000, 'EUR')),
    # LP68/2020: „în valoare de", cu zecimală
    ('Art.1. – Se ratifică Acordul de finanțare dintre Republica Moldova şi Asociaţia Internaţională pentru Dezvoltare '
     'privind implementarea Proiectului „Răspuns de urgenţă la COVID-19”, în valoare de 52,9 milioane de euro, semnat '
     'la 28 aprilie 2020.', (52900000, 'EUR')),
    # greșeală de tipar dintr-un proiect de lege: „25.000.000 mil." nu înseamnă 25 de mii de miliarde
    ('Se ratifică Contractul de finanțare privind proiectul „Deșeuri solide în Republica Moldova”, în mărime de '
     '25.000.000 mil. EUR, semnat la Chișinău, la 18 octombrie 2019.', (25000000, 'EUR')),
    # textul acordului, în engleză; comisionul nu e suma acordului
    ('The Bank agrees to lend to the Borrower the amount of EUR 25,000,000 (twenty-five million Euros). '
     'Front-end fee of EUR 62,500.', (25000000, 'EUR')),
    ('Comisionul de angajament de 100 000 euro se plătește anual. Se aprobă semnarea Acordului de împrumut în sumă '
     'de 30 000 000 euro.', (30000000, 'EUR')),
    ('Se aprobă proiectul de lege pentru ratificarea Acordului de Credit în valoare de 5.800.000 DST (Drepturi '
     'Speciale de Tragere).', (5800000, 'DST')),
    ('Banca convine să acorde împrumutatului suma de şaizeci milioane euro (60.000.000 euro).', (60000000, 'EUR')),
    # contribuția în lei a Guvernului trece după suma acordului
    ('Contribuția Guvernului în sumă de 10 000 000 lei. Se ratifică Acordul de grant în sumă de 4 340 000 euro.',
     (4340000, 'EUR')),
    ('Se ratifică Acordul de împrumut, în sumă de 13,1\nmilioane de euro, semnat la 26 septembrie 2019.', (13100000, 'EUR')),
]
for text, astept in SUME:
    r = ls.sume_din_text(text)
    prima = (r[0]['v'], r[0]['val']) if r else None
    verifica(f'{astept[0]:,}'.replace(',', ' ') + f' {astept[1]} ← „{text[:60]}…”', prima == astept, r[:2])
verifica('anii unui program nu sunt sume', ls.sume_din_text('Programul Interreg NEXT 2021–2027, semnat la 11 august 2023.') == [])
for s, v in [('25 000 000', 25e6), ('25.000.000,00', 25e6), ('25,000,000', 25e6), ('52,9', 52.9), ('13.1', 13.1)]:
    verifica(f'numărul „{s}" = {v:g}', ls.numar(s) == v, ls.numar(s))

if '--browser' in sys.argv:
    print('Browser, pe legis.md simulat')

    class Legis(BaseHTTPRequestHandler):
        blocat = False
        ultima = {}
        # două PDF-uri mici, făcute cu reportlab: o lege cu suma în art. 1 și o hotărâre fără sumă
        import base64
        pdf = {'135636': base64.b64decode('JVBERi0xLjMKJZOMi54gUmVwb3J0TGFiIEdlbmVyYXRlZCBQREYgZG9jdW1lbnQgKG9wZW5zb3VyY2UpCjEgMCBvYmoKPDwKL0YxIDIgMCBSCj4+CmVuZG9iagoyIDAgb2JqCjw8Ci9CYXNlRm9udCAvSGVsdmV0aWNhIC9FbmNvZGluZyAvV2luQW5zaUVuY29kaW5nIC9OYW1lIC9GMSAvU3VidHlwZSAvVHlwZTEgL1R5cGUgL0ZvbnQKPj4KZW5kb2JqCjMgMCBvYmoKPDwKL0NvbnRlbnRzIDcgMCBSIC9NZWRpYUJveCBbIDAgMCA1OTUuMjc1NiA4NDEuODg5OCBdIC9QYXJlbnQgNiAwIFIgL1Jlc291cmNlcyA8PAovRm9udCAxIDAgUiAvUHJvY1NldCBbIC9QREYgL1RleHQgL0ltYWdlQiAvSW1hZ2VDIC9JbWFnZUkgXQo+PiAvUm90YXRlIDAgL1RyYW5zIDw8Cgo+PiAKICAvVHlwZSAvUGFnZQo+PgplbmRvYmoKNCAwIG9iago8PAovUGFnZU1vZGUgL1VzZU5vbmUgL1BhZ2VzIDYgMCBSIC9UeXBlIC9DYXRhbG9nCj4+CmVuZG9iago1IDAgb2JqCjw8Ci9BdXRob3IgKGFub255bW91cykgL0NyZWF0aW9uRGF0ZSAoRDoyMDI2MTAwMjE4MTgyNSswMCcwMCcpIC9DcmVhdG9yIChhbm9ueW1vdXMpIC9LZXl3b3JkcyAoKSAvTW9kRGF0ZSAoRDoyMDI2MTAwMjE4MTgyNSswMCcwMCcpIC9Qcm9kdWNlciAoUmVwb3J0TGFiIFBERiBMaWJyYXJ5IC0gXChvcGVuc291cmNlXCkpIAogIC9TdWJqZWN0ICh1bnNwZWNpZmllZCkgL1RpdGxlICh1bnRpdGxlZCkgL1RyYXBwZWQgL0ZhbHNlCj4+CmVuZG9iago2IDAgb2JqCjw8Ci9Db3VudCAxIC9LaWRzIFsgMyAwIFIgXSAvVHlwZSAvUGFnZXMKPj4KZW5kb2JqCjcgMCBvYmoKPDwKL0ZpbHRlciBbIC9BU0NJSTg1RGVjb2RlIC9GbGF0ZURlY29kZSBdIC9MZW5ndGggNDIxCj4+CnN0cmVhbQpHYXQ9JWFcS2AtJkFAWk06UmhFTU9KRj5tUHNYXTIrOV9LQFA3MW9eQG4wak9rZ3FVS1grWWRiPz1dJm9RP2ZXMGIsRm1mTzIvP0VgR0w9LzdlX003LjJtOzRbLCcsMl4hLTBHVmNuS10vNSEhOVxLLFtxRClYJzc+cDRHJENmJl06YmRzbj1WcyohYVNjKzZwPS1qZGNPVTNZV1dQQzFCLm45cUpdbGNdbE9ZSURsUzZSJUQ4QSliTipiZ01YPiRnNDZsRzttJjRDYkxQJ1xfZDs3KjtJR1U8PlRVP0ZfMWIkXzY3Nl44OFNkcy9WJDw8WHQkQDxhIz9fSD5DMStsaVUyR1xZOHVJbDYqYy1aSjNibC4wV2tDcFc+NU5fLSpYIWpARztMYUFbMGhEYCYlQ25dMEdUbScpPkRhWC4vUWovPmtab2NpY0pDVVZBXjNYYF1uXzoqJ3NKNicxL0FePGliRkRlbjo3J1MlJ3E7OjI5ZF8sTSJca1pDSGlmOU9rSjBob0xsZj9cREMjdTA3OWViKFxRUGIxOGlvaERYOVpsbH4+ZW5kc3RyZWFtCmVuZG9iagp4cmVmCjAgOAowMDAwMDAwMDAwIDY1NTM1IGYgCjAwMDAwMDAwNjEgMDAwMDAgbiAKMDAwMDAwMDA5MiAwMDAwMCBuIAowMDAwMDAwMTk5IDAwMDAwIG4gCjAwMDAwMDA0MDIgMDAwMDAgbiAKMDAwMDAwMDQ3MCAwMDAwMCBuIAowMDAwMDAwNzMxIDAwMDAwIG4gCjAwMDAwMDA3OTAgMDAwMDAgbiAKdHJhaWxlcgo8PAovSUQgCls8YjIzMjZiOTE3MDcwNjdjM2NiZWRmZWNlOTZmYjQ2NTk+PGIyMzI2YjkxNzA3MDY3YzNjYmVkZmVjZTk2ZmI0NjU5Pl0KJSBSZXBvcnRMYWIgZ2VuZXJhdGVkIFBERiBkb2N1bWVudCAtLSBkaWdlc3QgKG9wZW5zb3VyY2UpCgovSW5mbyA1IDAgUgovUm9vdCA0IDAgUgovU2l6ZSA4Cj4+CnN0YXJ0eHJlZgoxMzAxCiUlRU9GCg=='),
               '121730': base64.b64decode('JVBERi0xLjMKJZOMi54gUmVwb3J0TGFiIEdlbmVyYXRlZCBQREYgZG9jdW1lbnQgKG9wZW5zb3VyY2UpCjEgMCBvYmoKPDwKL0YxIDIgMCBSCj4+CmVuZG9iagoyIDAgb2JqCjw8Ci9CYXNlRm9udCAvSGVsdmV0aWNhIC9FbmNvZGluZyAvV2luQW5zaUVuY29kaW5nIC9OYW1lIC9GMSAvU3VidHlwZSAvVHlwZTEgL1R5cGUgL0ZvbnQKPj4KZW5kb2JqCjMgMCBvYmoKPDwKL0NvbnRlbnRzIDcgMCBSIC9NZWRpYUJveCBbIDAgMCA1OTUuMjc1NiA4NDEuODg5OCBdIC9QYXJlbnQgNiAwIFIgL1Jlc291cmNlcyA8PAovRm9udCAxIDAgUiAvUHJvY1NldCBbIC9QREYgL1RleHQgL0ltYWdlQiAvSW1hZ2VDIC9JbWFnZUkgXQo+PiAvUm90YXRlIDAgL1RyYW5zIDw8Cgo+PiAKICAvVHlwZSAvUGFnZQo+PgplbmRvYmoKNCAwIG9iago8PAovUGFnZU1vZGUgL1VzZU5vbmUgL1BhZ2VzIDYgMCBSIC9UeXBlIC9DYXRhbG9nCj4+CmVuZG9iago1IDAgb2JqCjw8Ci9BdXRob3IgKGFub255bW91cykgL0NyZWF0aW9uRGF0ZSAoRDoyMDI2MTAwMjE4MTgyNSswMCcwMCcpIC9DcmVhdG9yIChhbm9ueW1vdXMpIC9LZXl3b3JkcyAoKSAvTW9kRGF0ZSAoRDoyMDI2MTAwMjE4MTgyNSswMCcwMCcpIC9Qcm9kdWNlciAoUmVwb3J0TGFiIFBERiBMaWJyYXJ5IC0gXChvcGVuc291cmNlXCkpIAogIC9TdWJqZWN0ICh1bnNwZWNpZmllZCkgL1RpdGxlICh1bnRpdGxlZCkgL1RyYXBwZWQgL0ZhbHNlCj4+CmVuZG9iago2IDAgb2JqCjw8Ci9Db3VudCAxIC9LaWRzIFsgMyAwIFIgXSAvVHlwZSAvUGFnZXMKPj4KZW5kb2JqCjcgMCBvYmoKPDwKL0ZpbHRlciBbIC9BU0NJSTg1RGVjb2RlIC9GbGF0ZURlY29kZSBdIC9MZW5ndGggMjU3Cj4+CnN0cmVhbQpHYXJvOjYjLU5WJjtCVFBNS2RQa0BabW4qR1smQSI0ZDZePUlwZz9YJjRyVjdOSklOMFZKL1ssT2ImKVpCJjdtMCtBOF1mRCNjSHVvNEo2J0BKM05XQk9LXURTJmxiPVEwV3EiSUxSJipYWHI0V2wwRixoW2JcQzRIUDFSLjFgMElLOGcwTmY5LmFkMSNGTDlOck1qLiheIS9NX0dCJkp1I3MjOygiP1BgLDBKSGBrR24oZmEuWE5ZMzgmb2VzNS5nXjMucFwtQW5xQyNkKl46Yjc5WVo7cGtqMSM1S3E+S2xSNktqc20+N1FLOldfLiQycHMrV0BQSVRaLmQnZ0p+PmVuZHN0cmVhbQplbmRvYmoKeHJlZgowIDgKMDAwMDAwMDAwMCA2NTUzNSBmIAowMDAwMDAwMDYxIDAwMDAwIG4gCjAwMDAwMDAwOTIgMDAwMDAgbiAKMDAwMDAwMDE5OSAwMDAwMCBuIAowMDAwMDAwNDAyIDAwMDAwIG4gCjAwMDAwMDA0NzAgMDAwMDAgbiAKMDAwMDAwMDczMSAwMDAwMCBuIAowMDAwMDAwNzkwIDAwMDAwIG4gCnRyYWlsZXIKPDwKL0lEIApbPGU4YmJmZDEyYjg4NTZkNWNhMzk1MjA4NDY0YWJmNTE0PjxlOGJiZmQxMmI4ODU2ZDVjYTM5NTIwODQ2NGFiZjUxND5dCiUgUmVwb3J0TGFiIGdlbmVyYXRlZCBQREYgZG9jdW1lbnQgLS0gZGlnZXN0IChvcGVuc291cmNlKQoKL0luZm8gNSAwIFIKL1Jvb3QgNCAwIFIKL1NpemUgOAo+PgpzdGFydHhyZWYKMTEzNwolJUVPRgo=')}

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
            if u.path.startswith('/cautare/downloadpdf/'):
                doc = u.path.rsplit('/', 1)[-1]
                if doc in Legis.pdf:
                    b = Legis.pdf[doc]
                    self.send_response(200); self.send_header('Content-Type', 'application/pdf')
                    self.send_header('Content-Length', str(len(b))); self.end_headers(); self.wfile.write(b)
                    return
                self.send_response(404); self.send_header('Content-Type', 'text/html'); self.end_headers()
                self.wfile.write(b'<html>nu exista</html>')
                return
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

        print()
        print('Sumele din PDF-urile actelor (legis_sume.py, legis.md simulat)')
        Legis.blocat = False
        shutil.copy(AICI / 'legis_sume.py', tmp / 'legis_sume.py')
        json.dump([{'id': '135636', 'c': 'LP14/2023', 'pub': '15-02-2023',
                    't': 'pentru ratificarea Acordului de împrumut dintre Republica Moldova și Banca Europeană pentru Reconstrucție și Dezvoltare în vederea realizării Proiectului „Deșeuri solide în Republica Moldova”', 'kw': []},
                   {'id': '121730', 'c': 'HG354/2020', 'pub': '12-06-2020',
                    't': 'cu privire la aprobarea semnării Acordului de împrumut dintre Republica Moldova și Banca Internațională pentru Reconstrucție și Dezvoltare', 'kw': []},
                   {'id': '999', 'c': 'HG999/2021', 'pub': '01-01-2021',
                    't': 'cu privire la aprobarea semnării Acordului de grant dintre Republica Moldova și Banca Europeană de Investiții', 'kw': []},
                   {'id': '777', 'c': 'DP77/2023', 'pub': '01-03-2023',
                    't': 'privind promulgarea Legii pentru ratificarea Acordului de împrumut dintre Republica Moldova și Banca Europeană pentru Reconstrucție și Dezvoltare', 'kw': []}],
                  open(tmp / 'legis_brut.json', 'w', encoding='utf-8'))
        p = subprocess.run([sys.executable, str(tmp / 'legis_sume.py'), '--url', url, '--asteapta-cf', '5', '--pauza', '0'],
                           capture_output=True, text=True, timeout=300, env=env_test)
        verifica('legis_sume.py rulează (cod 0)', p.returncode == 0, p.stdout[-800:] + p.stderr[-800:])
        rez = json.load(open(tmp / 'date' / 'legis_sume.json', encoding='utf-8')).get('acte', {}) \
              if (tmp / 'date' / 'legis_sume.json').exists() else {}
        s = (rez.get('135636') or {}).get('sume') or []
        verifica('LP14/2023: 25 de milioane EUR, din textul legii', bool(s) and (s[0]['v'], s[0]['val']) == (25000000, 'EUR'), rez.get('135636'))
        verifica('HG fără sumă: citită, fără sumă', rez.get('121730', {}).get('sume') == [], rez.get('121730'))
        verifica('act inexistent: eroare notată, nu oprire', 'eroare' in rez.get('999', {}), rez.get('999'))
        verifica('decretele nu se descarcă', '777' not in rez, list(rez))
        p = subprocess.run([sys.executable, str(tmp / 'legis_pagina.py')], capture_output=True, text=True, timeout=120, env=env_test)
        pag = (tmp / 'legis_acorduri.html').read_text(encoding='utf-8') if (tmp / 'legis_acorduri.html').exists() else ''
        import re as _re
        verifica('pagina primește suma actului', bool(_re.search(r'"sume":\s*\[\[25000000,\s*"EUR"', pag)), p.stdout[-400:] + p.stderr[-400:])
        p = subprocess.run([sys.executable, str(tmp / 'legis_sume.py'), '--url', url, '--asteapta-cf', '5', '--pauza', '0'],
                           capture_output=True, text=True, timeout=120, env=env_test)
        verifica('a doua rulare nu mai descarcă nimic', p.returncode == 0 and '0 de citit' in p.stdout, p.stdout[-300:])
        Legis.blocat = True
        p = subprocess.run([sys.executable, str(tmp / 'legis_sume.py'), '--url', url, '--asteapta-cf', '5', '--reincearca'],
                           capture_output=True, text=True, timeout=120, env=env_test)
        verifica('blocat de Cloudflare → cod 3', p.returncode == 3, p.stdout[-300:])

        # fără browser (cum rulează pe GitHub Actions): aceleași rezultate, același cod la blocaj
        Legis.blocat = False
        (tmp / 'date' / 'legis_sume.json').unlink()
        p = subprocess.run([sys.executable, str(tmp / 'legis_sume.py'), '--url', url, '--fara-browser', '--pauza', '0'],
                           capture_output=True, text=True, timeout=120, env=env_test)
        rez = json.load(open(tmp / 'date' / 'legis_sume.json', encoding='utf-8')).get('acte', {}) \
              if (tmp / 'date' / 'legis_sume.json').exists() else {}
        s = (rez.get('135636') or {}).get('sume') or []
        verifica('fără browser: LP14/2023 = 25 de milioane EUR', p.returncode == 0 and bool(s) and s[0]['v'] == 25000000,
                 p.stdout[-500:] + p.stderr[-500:])
        Legis.blocat = True
        p = subprocess.run([sys.executable, str(tmp / 'legis_sume.py'), '--url', url, '--fara-browser', '--reincearca'],
                           capture_output=True, text=True, timeout=120, env=env_test)
        verifica('fără browser, blocat → cod 3', p.returncode == 3, p.stdout[-300:])
    finally:
        srv.shutdown()
        shutil.rmtree(tmp, ignore_errors=True)

print()
if picat:
    print(f'Au picat {len(picat)} teste.'); sys.exit(1)
print('Toate testele legis au trecut.')
