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



LUNI = {'ianuarie': 1, 'februarie': 2, 'martie': 3, 'aprilie': 4, 'mai': 5, 'iunie': 6, 'iulie': 7,
        'august': 8, 'septembrie': 9, 'octombrie': 10, 'noiembrie': 11, 'decembrie': 12}
PREFIX = {'lege': 'LP', 'hotarare': 'HG', 'decret': 'DP', 'ordin': 'O'}


def cod_legis(a):
    """„nr. 188, 24 august 2026" + „Lege…" -> ('LP188/2026', '24.08.2026')."""
    m = re.search(r'nr\.\s*(\d+)(?:-[IVXLC]+)?\s*,\s*(\d{1,2})\s+(\S+)\s+(\d{4})', a.get('act', ''))
    if not m:
        return None, None
    pre = PREFIX.get(norm(a.get('titlu', '')).split(' ')[0])
    luna = LUNI.get(norm(m.group(3)))
    if not pre or not luna:
        return None, None
    return pre + m.group(1) + '/' + m.group(4), '%02d.%02d.%s' % (int(m.group(2)), luna, m.group(4))


def adauga_din_monitor(acte, ids, cale=None):
    cale = Path(cale or AICI / 'date.json')
    if not cale.exists():
        return 0
    try:
        mo = json.load(open(cale, encoding='utf-8')).get('acte', {})
    except Exception as e:
        print('date.json nu a putut fi citit:', e)
        return 0
    # ce e deja în baza legis: (prefix, număr, an); ordinele au prefixe diferite (OMF, OMS…)
    def cheie(c):
        m = re.match(r'^([A-Z]+?)(\d+)(?:/\d+)?/(\d{4})$', c or '')
        if not m:
            return None
        p = 'DP' if m.group(1).startswith('DP') else ('O' if m.group(1).startswith('O') else m.group(1))
        return (p, m.group(2), m.group(3))
    exista = {cheie(c) for c in ids}
    n = 0
    for k, a in mo.items():
        cod, data = cod_legis(a)
        if not cod or cheie(cod) in exista:
            continue
        exista.add(cheie(cod))
        nr, an = re.match(r'^[A-Z]+(\d+)/(\d{4})$', cod).groups()
        acte[cod + '|mo' + k] = {
            'act': cod,
            'titlu': a.get('titlu', ''),
            'categorie': a.get('categorie', ''),
            'partener': a.get('partener', ''),
            'semnat': a.get('semnat', ''),
            'editie': 'MO ' + a.get('editie', '') if a.get('editie') else 'Monitorul Oficial',
            'data_editie': a.get('data_editie', ''),
            'editie_id': a.get('editie_id', ''),
            # fișa legis nu are încă doc_id cunoscut: ducem la căutarea după număr + data adoptării
            'url': 'https://www.legis.md/cautare/getResults?document_status=0&nr_doc=' + nr +
                   '&datepicker1=' + data + '&publication_status=+-+TOATE+-+&nr=&publish_date=&search_type=1&search_string=',
            'suport': bool(a.get('suport')),
        }
        ids[cod] = 'mo'
        n += 1
    return n


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

    # Actele noi vin zilnic din Monitorul Oficial (date.json, colectat de
    # monitor.yml pe GitHub, fără Cloudflare). Orice act ajunge întâi în
    # Monitor, apoi în legis.md — deci baza legis (istoricul) + Monitorul
    # (ce e nou) dau registrul complet, actualizat zilnic, fără ca cineva să
    # mai citească legis.md. Ce există deja în baza legis nu se dublează.
    din_mo = adauga_din_monitor(acte, ids)

    # data afișată = ultima colectare din Monitor, nu ziua de azi: altfel pagina
    # s-ar schimba (și s-ar face commit) în fiecare zi, fără nimic nou
    azi = datetime.date.today().strftime('%d.%m.%Y')
    try:
        azi = json.load(open(AICI / 'date.json', encoding='utf-8')).get('ultima_rulare') or azi
    except Exception:
        pass
    db = {'acte': acte, 'editii_vazute': [], 'ultima_rulare': azi, 'editii_lipsa': []}
    print(len(acte), 'acte', '(din care', din_mo, 'din Monitorul Oficial)')

    s = open(SRC, encoding='utf-8').read()
    AN = azi[6:10] if re.match(r'\d\d\.\d\d\.\d{4}', azi) else str(datetime.date.today().year)


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
                'Un acord, un rând. Actele din Registrul de stat al actelor juridice (legis.md), 1992–' + AN + ', grupate pe acordul din care fac parte, '
                'cu etapa la care a ajuns fiecare. <b>Versiune de test</b>: actele sunt găsite prin căutare în titlu și filtrate automat, '
                'deci pot exista și acte în plus, și acte scăpate.')
    inlocuieste("      '<span>Ediții parcurse: <b>' + ((db.editii_vazute||[]).length) + '</b></span>' +",
                "      '<span>Sursa: <b>legis.md</b> · ' + Object.keys(db.acte).length + ' acte</span>' +")
    inlocuieste("'>Ultima verificare: <b>'", "'>Extras la: <b>'")
    inlocuieste('Sursa: cuprinsurile Monitorului Oficial al Republicii Moldova.',
                'Sursa acestei versiuni: Registrul de stat al actelor juridice (legis.md), căutare după cuvinte-cheie în titlu, an cu an, '
                '1990–' + AN + ', apoi filtrare cu clasificatorul registrului, extins. Numărul actului deschide fișa lui pe legis.md.')
    inlocuieste("var antet = 'Acorduri de asistență externă — Monitorul Oficial al Republicii Moldova. ' +",
                "var antet = 'Acorduri de asistență externă — Registrul de stat (legis.md). ' +")
    # bara comună (meniu.js) marchează pagina curentă
    inlocuieste('<script src="meniu.js" data-pagina="acorduri-mo"></script>',
                '<script src="meniu.js" data-pagina="acorduri-legis"></script>')

    open(OUT, 'w', encoding='utf-8').write(s)
    print('scris', OUT, len(s) // 1024, 'KB')


if __name__ == '__main__':
    main(*sys.argv[1:3])
