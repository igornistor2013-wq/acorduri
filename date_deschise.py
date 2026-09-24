"""Date deschise și flux RSS, generate din registrele de acorduri.

    python date_deschise.py

Scrie:
  date/acorduri_monitor.csv / .json   registrul din Monitorul Oficial (date.json)
  date/acorduri_legis.csv   / .json   registrul din legis.md (cel din legis_acorduri.html)
  rss.xml                             ultimele 50 de acte, pentru abonare

Rulează zilnic în monitor.yml, după colectare și după legis_pagina.py, ca
fișierele să fie mereu la zi cu paginile. CSV-urile au BOM UTF-8, ca Excel să
arate diacriticele corect la dublu-clic.
"""
import csv, datetime, email.utils, json, re
from pathlib import Path
from xml.sax.saxutils import escape

AICI = Path(__file__).resolve().parent
SITE = 'https://nistor.vivi.md'
COLOANE = ['act', 'data_editie', 'tip', 'titlu', 'categorie', 'partener', 'semnat', 'editie', 'suport_bugetar', 'link']


def tip(titlu):
    return (titlu or '').split(' ')[0]


def randuri(acte):
    out = []
    for a in acte.values():
        out.append({
            'act': a.get('act', ''),
            'data_editie': a.get('data_editie', ''),
            'tip': tip(a.get('titlu', '')),
            'titlu': a.get('titlu', ''),
            'categorie': a.get('categorie', ''),
            'partener': a.get('partener', ''),
            'semnat': a.get('semnat', ''),
            'editie': a.get('editie', ''),
            'suport_bugetar': 'da' if a.get('suport') else '',
            'link': a.get('url', ''),
        })

    def cheie(r):
        m = re.match(r'(\d{2})\.(\d{2})\.(\d{4})', r['data_editie'] or '')
        return (m.group(3) + m.group(2) + m.group(1)) if m else '0'
    out.sort(key=lambda r: (cheie(r), r['act']), reverse=True)
    return out


def scrie(nume, rows):
    d = AICI / 'date'
    d.mkdir(exist_ok=True)
    with open(d / (nume + '.csv'), 'w', encoding='utf-8-sig', newline='') as f:
        w = csv.DictWriter(f, fieldnames=COLOANE)
        w.writeheader()
        w.writerows(rows)
    with open(d / (nume + '.json'), 'w', encoding='utf-8') as f:
        json.dump(rows, f, ensure_ascii=False, indent=1)
    print(f'date/{nume}: {len(rows)} acte')


def acte_legis():
    p = AICI / 'legis_acorduri.html'
    if not p.exists():
        return {}
    s = p.read_text(encoding='utf-8')
    m = re.search(r'window\.__LEGIS__ = (\{.*?\});</script>', s, re.S)
    return json.loads(m.group(1)).get('acte', {}) if m else {}


def data_rss(d):
    m = re.match(r'(\d{2})\.(\d{2})\.(\d{4})', d or '')
    if not m:
        return None
    dt = datetime.datetime(int(m.group(3)), int(m.group(2)), int(m.group(1)), 9, 0, tzinfo=datetime.timezone.utc)
    return email.utils.format_datetime(dt)


def rss(rows, ultima):
    items = []
    for r in rows[:50]:
        desc = ' · '.join(x for x in [r['categorie'], r['partener'], ('Monitorul Oficial ' + r['editie']) if r['editie'] else ''] if x)
        guid = r['act'] + '|' + r['data_editie']
        items.append(
            '<item><title>' + escape(r['act'] + ' — ' + r['titlu'][:180]) + '</title>'
            '<link>' + escape(r['link'] or SITE + '/acorduri.html') + '</link>'
            '<guid isPermaLink="false">' + escape(guid) + '</guid>'
            + ('<pubDate>' + data_rss(r['data_editie']) + '</pubDate>' if data_rss(r['data_editie']) else '') +
            '<category>' + escape(r['categorie']) + '</category>'
            '<description>' + escape(desc + '. ' + r['titlu']) + '</description></item>')
    build = data_rss((ultima or '')[:10]) or email.utils.format_datetime(datetime.datetime.now(datetime.timezone.utc))
    xml = ('<?xml version="1.0" encoding="UTF-8"?>\n'
           '<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom"><channel>'
           '<title>Acorduri de asistență externă — Republica Moldova</title>'
           '<link>' + SITE + '/acorduri.html</link>'
           '<atom:link href="' + SITE + '/rss.xml" rel="self" type="application/rss+xml"/>'
           '<description>Actele noi privind acordurile de asistență externă (împrumuturi, granturi, asistență tehnică), '
           'din Monitorul Oficial, actualizate zilnic.</description>'
           '<language>ro</language><lastBuildDate>' + build + '</lastBuildDate>'
           + ''.join(items) + '</channel></rss>\n')
    (AICI / 'rss.xml').write_text(xml, encoding='utf-8')
    print('rss.xml:', len(items), 'articole')


def main():
    db = json.load(open(AICI / 'date.json', encoding='utf-8'))
    mo = randuri(db.get('acte', {}))
    scrie('acorduri_monitor', mo)
    scrie('acorduri_legis', randuri(acte_legis()))
    rss(mo, db.get('ultima_rulare'))


if __name__ == '__main__':
    main()
