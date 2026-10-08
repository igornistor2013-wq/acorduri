#!/usr/bin/env python3
"""Acordurile din registrul legis.md, gata grupate, pentru „De la lege la bani".

Pagina de acorduri știe să grupeze zecile de acte ale unui acord (hotărârea de începere a
negocierilor, cea de aprobare a semnării, legea de ratificare, decretul, ordinul de intrare în
vigoare) într-un singur rând, să-i dea o denumire, să aleagă suma din cele patru surse posibile
(textul acordului, titlu, textul actului, nota Guvernului) și s-o treacă în euro. Regulile acelea
sunt lungi și au fost potrivite pe date reale, rând cu rând: nu le repetăm aici.

Scriptul deschide pagina într-un browser fără ecran, așteaptă să-și termine încărcările și îi
cere lista pe care ea o folosește (window.__ACORDURI__, definită în acorduri.html). Rezultatul,
date/acorduri_legare.json, îl citește dashboardul: acolo se leagă fiecare acord de proiectele
din AMP, pentru că doar acolo există datele AMP de azi.

Rulare:
    python3 legatura_acorduri.py              # scrie date/acorduri_legare.json
    python3 legatura_acorduri.py --dry-run    # arată ce ar scrie, fără să scrie
    python3 legatura_acorduri.py --pagina acorduri.html     # registrul din Monitorul Oficial

Are nevoie de Playwright:  pip install playwright  și  python -m playwright install chromium
Rulat automat de .github/workflows/legaturi.yml, după fiecare colectare din Monitor.

Coduri de ieșire: 0 = a mers (sau nu era nimic de schimbat), 1 = nu s-a putut citi pagina.
"""
import argparse
import datetime
import functools
import http.server
import json
import socketserver
import sys
import threading
from pathlib import Path

AICI = Path(__file__).resolve().parent
IESIRE = AICI / 'date' / 'acorduri_legare.json'
PAGINA = 'legis_acorduri.html'

# Sub atâtea acorduri, citirea a mers prost (pagina nu și-a încărcat datele): nu scriem peste
# fișierul bun. Registrul legis.md are peste cinci sute.
MINIM_ACORDURI = 200
# Dacă numărul de acorduri scade sub această parte din cât era, e o citire incompletă.
MINIM_FATA_DE_ANTERIOR = 0.8
# Sumele sosesc după încărcarea paginii, din date/legis_sume.json, date/gov_sume.json și
# date/sume_manual.json. Dacă fișierele acelea n-au putut fi citite, acordurile rămân, dar fără
# sume — iar „De la lege la bani" ar pierde pe tăcute tot ce se leagă prin sumă. Din registrul
# real, peste 60% dintre acorduri au sumă; sub atât, ceva nu s-a încărcat.
MINIM_CU_SUMA = 0.3


class _Liniste(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a):
        pass


class _Server(socketserver.ThreadingMixIn, http.server.HTTPServer):
    daemon_threads = True
    allow_reuse_address = True


def citeste_acorduri(radacina=AICI, pagina=PAGINA, asteapta_max=45):
    """Deschide pagina și întoarce (lista de acorduri, data cursurilor)."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        sys.exit('Lipsește Playwright. Instalează-l:  pip install playwright  și apoi  '
                 'python -m playwright install chromium')
    server = _Server(('127.0.0.1', 0), functools.partial(_Liniste, directory=str(radacina)))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    baza = 'http://127.0.0.1:%d/' % server.server_address[1]
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            try:
                page = browser.new_page()
                erori = []
                page.on('pageerror', lambda e: erori.append(str(e)[:200]))
                # pagina nu are nevoie de rețea; ce încearcă să iasă din calculator se oprește
                page.route('**/*', lambda r: r.continue_() if r.request.url.startswith(baza) else r.abort())
                page.goto(baza + pagina, wait_until='networkidle', timeout=90000)
                page.wait_for_function('typeof window.__ACORDURI__ === "function"', timeout=30000)
                # Sumele, legăturile spre legis.md și notele Guvernului sosesc după încărcare și
                # fiecare redesenează pagina. Așteptăm până când lista nu se mai schimbă.
                ultim, stabil, rest = None, 0, asteapta_max * 1000
                while rest > 0 and stabil < 3:
                    page.wait_for_timeout(700)
                    rest -= 700
                    acum = page.evaluate('''() => {
                        const l = window.__ACORDURI__();
                        return l.length + ':' + l.filter(x => x.suma).length + ':' +
                               l.reduce((s, x) => s + x.alte.length + (x.cost ? 1 : 0), 0);
                    }''')
                    stabil = stabil + 1 if acum == ultim else 0
                    ultim = acum
                acorduri = page.evaluate('window.__ACORDURI__()')
                curs = page.evaluate('window.__ACORDURI__.curs || ""')
                if erori:
                    print('Avertisment: pagina a dat erori JavaScript:', erori[:3], file=sys.stderr)
            finally:
                browser.close()
    finally:
        server.shutdown()
    return acorduri, curs


def valideaza(acorduri, anterior=None):
    """Întoarce o listă de probleme; goală = fișierul poate fi scris."""
    probleme = []
    if len(acorduri) < MINIM_ACORDURI:
        probleme.append('doar %d acorduri (sub %d): pagina nu și-a încărcat datele' % (len(acorduri), MINIM_ACORDURI))
    ids = [a.get('id') for a in acorduri]
    if len(set(ids)) != len(ids):
        probleme.append('id-uri care se repetă')
    if any(not a.get('id') or not a.get('nume') for a in acorduri):
        probleme.append('acorduri fără id sau fără denumire')
    if anterior and len(acorduri) < MINIM_FATA_DE_ANTERIOR * len(anterior):
        probleme.append('%d acorduri față de %d în fișierul de acum' % (len(acorduri), len(anterior)))
    cu = sum(1 for a in acorduri if a.get('suma'))
    if acorduri and cu < MINIM_CU_SUMA * len(acorduri):
        probleme.append('doar %d din %d acorduri au sumă: sumele nu s-au încărcat' % (cu, len(acorduri)))
    cu_ant = sum(1 for a in (anterior or []) if a.get('suma'))
    if cu_ant and cu < MINIM_FATA_DE_ANTERIOR * cu_ant:
        probleme.append('%d acorduri cu sumă față de %d în fișierul de acum' % (cu, cu_ant))
    return probleme


def continut(acorduri, curs, actualizat):
    return {'actualizat': actualizat, 'curs_data': curs, 'numar': len(acorduri), 'acorduri': acorduri}


def text_json(nou):
    """Fișierul, cu un acord pe linie: o schimbare se vede în git ca o linie, nu ca un fișier întreg."""
    antet = json.dumps({k: v for k, v in nou.items() if k != 'acorduri'}, ensure_ascii=False, separators=(',', ':'))[:-1]
    linii = ',\n'.join(json.dumps(a, ensure_ascii=False, separators=(',', ':')) for a in nou['acorduri'])
    return antet + ',"acorduri":[\n' + linii + '\n]}\n'


def fara_data(d):
    d = dict(d or {})
    d.pop('actualizat', None)
    return d


def main(argv=None):
    ap = argparse.ArgumentParser(description='Acordurile din registru, gata grupate, în date/acorduri_legare.json')
    ap.add_argument('--pagina', default=PAGINA, help='pagina din care se citesc acordurile (implicit: legis_acorduri.html)')
    ap.add_argument('--iesire', default=str(IESIRE))
    ap.add_argument('--dry-run', action='store_true', help='arată ce ar scrie, fără să scrie')
    ap.add_argument('--forteaza', action='store_true', help='scrie și când citirea pare incompletă')
    a = ap.parse_args(argv)
    iesire = Path(a.iesire)

    acorduri, curs = citeste_acorduri(pagina=a.pagina)
    try:
        anterior = json.load(open(iesire, encoding='utf-8'))
    except Exception:
        anterior = {}
    probleme = valideaza(acorduri, anterior.get('acorduri'))
    if probleme and not a.forteaza:
        print('Nu scriu: ' + '; '.join(probleme), file=sys.stderr)
        return 1

    nou = continut(acorduri, curs, datetime.datetime.now().strftime('%Y-%m-%d %H:%M'))
    cu_suma = sum(1 for x in acorduri if x.get('suma'))
    print('%d acorduri, din care %d cu sumă (curs: %s)' % (len(acorduri), cu_suma, curs or '—'))
    if fara_data(nou) == fara_data(anterior):
        print('Nimic schimbat față de %s — nu rescriu.' % iesire.name)
        return 0
    if a.dry_run:
        print('--dry-run: nu am scris nimic.')
        return 0
    iesire.parent.mkdir(exist_ok=True)
    tmp = iesire.with_suffix('.tmp')
    with open(tmp, 'w', encoding='utf-8') as f:
        f.write(text_json(nou))
    tmp.replace(iesire)
    print('Scris:', iesire)
    return 0


if __name__ == '__main__':
    sys.exit(main())
