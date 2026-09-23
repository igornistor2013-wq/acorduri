"""Construiește legis_acorduri.html (python3 legis_pagina.py [baza.json] [iesire.html]) în stilul acorduri.html, grupat pe acorduri.

Ia pagina acorduri.html așa cum e (aceeași grupare pe acord, aceleași etape,
filtre, fișe, export) și îi dă datele extrase de pe legis.md în locul
date.json. Datele sunt incluse în pagină, deci merge și deschisă direct de pe
disc, fără server.
"""
import json, re, sys, datetime
from pathlib import Path
AICI = Path(__file__).resolve().parent
sys.path.insert(0, str(AICI))
from legis_clasifica import clasifica, partener, norm
import monitor_watch as mw

SRC = AICI / 'acorduri.html'

# Tipul actului, ca prim cuvânt al titlului — pagina deduce etapa din el
# (/^lege/ = ratificare, /^ordin/ = punere în aplicare etc.)
TIP = [(r'^LP', 'Lege'), (r'^HP', 'Hotărâre a Parlamentului'), (r'^DPRM|^DP', 'Decret'),
       (r'^HG', 'Hotărâre'), (r'^DG', 'Dispoziție'), (r'^O', 'Ordin')]


def tip(cod):
    for p, n in TIP:
        if re.search(p, cod):
            return n
    return 'Act'


# Unele titluri vechi de pe legis.md au diacriticele stricate: textul a fost
# salvat în CP1250 și citit ca CP1251 („оmprumut, finanюare, Banca Germanг").
# Refacem literele: ă←г, ţ←ю, î←о, ş←є, â←в, ü←ь; iar literele chirilice
# identice ca formă cu cele latine (с, а, е, р) devin latine.
MOJI = {'г': 'ă', 'ю': 'ţ', 'о': 'î', 'є': 'ş', 'в': 'â', 'ь': 'ü', 'Г': 'Ă', 'Ю': 'Ţ',
        'О': 'Î', 'Є': 'Ş', 'В': 'Â'}
SOSII = {'с': 'c', 'а': 'a', 'е': 'e', 'р': 'p', 'х': 'x', 'С': 'C', 'А': 'A', 'Е': 'E', 'Р': 'P'}


def repara(t):
    if not re.search('[\u0400-\u04FF]', t):
        return t
    def cuv(m):
        w = m.group(0)
        if not re.search('[A-Za-zăâîşţșț]', w):     # cuvânt întreg chirilic: îl lăsăm
            return w
        return ''.join(SOSII.get(ch, MOJI.get(ch, ch)) for ch in w)
    return re.sub(r'\S+', cuv, t)



def main(BRUT=None, OUT=None):
    global s
    BRUT = BRUT or str(AICI / 'legis_brut.json')
    OUT = OUT or str(AICI / 'legis_acorduri.html')
    brut = json.load(open(BRUT, encoding='utf-8'))
    acte, ids = {}, {}
    for r in brut:
        t = repara(re.sub(r'^(Modificat|Abrogat|Suspendat)\s*', '', r['t']).strip())
        cat = clasifica(t)
        if not cat:
            continue
        titlu = tip(r['c']) + ' ' + t
        pub = r['pub'].replace('-', '.')
        acte[r['c'] + '|' + r['id']] = {
            'act': r['c'],
            'titlu': titlu,
            'categorie': cat,
            'partener': partener(t),
            'semnat': mw.signed_on(t),
            'editie': 'legis.md',
            'data_editie': pub,
            'editie_id': r['id'],
            'url': 'https://www.legis.md/cautare/getResults?doc_id=' + r['id'] + '&lang=ro',
            'suport': mw.e_suport_bugetar(t),
        }
        ids[r['c']] = r['id']

    azi = datetime.date.today().strftime('%d.%m.%Y')
    db = {'acte': acte, 'editii_vazute': [], 'ultima_rulare': azi, 'editii_lipsa': []}
    print(len(acte), 'acte')

    s = open(SRC, encoding='utf-8').read()


    def inlocuieste(vechi, nou, n=1):
        global s
        c = s.count(vechi)
        if c != n:
            raise SystemExit('EROARE: acorduri.html nu are forma așteptată (nu găsesc: ' + repr(vechi[:70]) +
                             '). Pagina legis se construiește din acorduri.html — urcă versiunea din setul nou.')
        s = s.replace(vechi, nou)


    # 1. Datele: incluse în pagină, în locul cererii către date.json
    inlocuieste('<script>\n(function(){\n  var DATA_URL = "date.json";',
                '<script>window.__LEGIS__ = ' + json.dumps(db, ensure_ascii=False, separators=(',', ':')) +
                ';</script>\n<script>\n(function(){\n  var DATA_URL = "date.json";')
    inlocuieste("  fetch(DATA_URL + (DATA_URL.indexOf('?')>-1?'&':'?')",
                "  if (window.__LEGIS__) { db = window.__LEGIS__; paint(); } else\n  fetch(DATA_URL + (DATA_URL.indexOf('?')>-1?'&':'?')")

    # 2. Numărul actului duce direct la fișa lui (doc_id), nu la o căutare
    inlocuieste('  function linkLegis(act){\n',
                '  function linkLegis(act){\n'
                '    if (window.__LEGIS__ && /^[A-Z]+\\d/.test(String(act || ""))) {\n'
                '      var hit = Object.keys(window.__LEGIS__.acte).filter(function(k){ return k.split("|")[0] === act; })[0];\n'
                '      return hit ? window.__LEGIS__.acte[hit].url : "";\n'
                '    }\n')

    # 3. „MO <ediție>" → sursa e legis.md
    inlocuieste("'MO ' + a.editie", "a.editie")
    inlocuieste('rel="noopener noreferrer">MO \' +', 'rel="noopener noreferrer">\' +')
    inlocuieste(": 'MO ' + esc(a.editie)) +", ": esc(a.editie)) +")
    inlocuieste('rel="noopener noreferrer">MO \'\n', 'rel="noopener noreferrer">\'\n')
    inlocuieste('<span class="nil-link">MO \')', '<span class="nil-link">\')')

    # 4. Hotărârile Parlamentului din anii '90 ratificau acordurile (azi — legea)
    inlocuieste("    if (/^lege/.test(t)) return ['rat'];",
                "    if (/^lege/.test(t)) return ['rat'];\n"
                "    if (/^hotarare a parlamentului (?:pentru|privind|cu privire la) ratific/.test(t)) return ['rat'];\n"
                "    if (/^hotarare a parlamentului/.test(t) && /proiectului de lege/.test(t)) return ['plg'];")
    inlocuieste("return etapa(a).indexOf('rat') > -1 && /^lege/.test(fold(a.titlu));",
                "return etapa(a).indexOf('rat') > -1 && /^(?:lege|hotarare a parlamentului)/.test(fold(a.titlu));")
    inlocuieste("return etapa(a).indexOf('rat') > -1 && /^hotarare/.test(fold(a.titlu));",
                "return etapa(a).indexOf('rat') > -1 && /^hotarare(?! a parlamentului)/.test(fold(a.titlu));")

    # 5. Texte: sursa e Registrul de stat, nu cuprinsurile Monitorului
    inlocuieste('<title>', '<title>Legis · ')
    inlocuieste('<h1>Acorduri de asistență externă</h1>',
                '<h1>Acorduri de asistență externă · Registrul de stat</h1>')
    inlocuieste('Un acord, un rând. Actele publicate în Monitorul Oficial sunt grupate pe acordul din care fac parte, cu etapa la care a ajuns fiecare.',
                'Un acord, un rând. Actele din Registrul de stat al actelor juridice (legis.md), 1992–2026, grupate pe acordul din care fac parte, '
                'cu etapa la care a ajuns fiecare. <b>Versiune de test</b>: actele sunt găsite prin căutare în titlu și filtrate automat, '
                'deci pot exista și acte în plus, și acte scăpate.')
    inlocuieste("      '<span>Ediții parcurse: <b>' + ((db.editii_vazute||[]).length) + '</b></span>' +",
                "      '<span>Sursa: <b>legis.md</b> · ' + Object.keys(db.acte).length + ' acte</span>' +")
    inlocuieste("'>Ultima verificare: <b>'", "'>Extras la: <b>'")
    inlocuieste('Sursa: cuprinsurile Monitorului Oficial al Republicii Moldova.',
                'Sursa acestei versiuni: Registrul de stat al actelor juridice (legis.md), căutare după cuvinte-cheie în titlu, an cu an, '
                '1990–2026, apoi filtrare cu clasificatorul registrului, extins. Numărul actului deschide fișa lui pe legis.md.')
    inlocuieste("var antet = 'Acorduri de asistență externă — Monitorul Oficial al Republicii Moldova. ' +",
                "var antet = 'Acorduri de asistență externă — Registrul de stat (legis.md). ' +")
    # butonul „Acorduri" din antet duce la registrul din Monitor
    inlocuieste('''      <span class="navbtn here">
        <svg viewBox="0 0 24 24"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>
        Acorduri
      </span>''', '''      <a class="navbtn away" href="acorduri.html">
        <svg viewBox="0 0 24 24"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>
        Acorduri (Monitor)
      </a>''')

    open(OUT, 'w', encoding='utf-8').write(s)
    print('scris', OUT, len(s) // 1024, 'KB')


if __name__ == '__main__':
    main(*sys.argv[1:3])
