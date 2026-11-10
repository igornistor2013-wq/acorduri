"""Actualizează cursul valutar al paginilor din cursurile de referință ale Băncii Centrale Europene.

Citește cursurile zilnice ale BCE (https://www.ecb.europa.eu/stats/eurofxref/eurofxref-daily.xml: unități de valută
pentru 1 EUR, publicate în zilele lucrătoare, în jur de ora 16:00 la Frankfurt) și le scrie în:

  * acorduri.html și legis_acorduri.html: `CURS_DATA` și `PER_EUR` (tabelul cu care pagina trece sumele în euro) și
    mențiunea din comentariul de deasupra lor;
  * date/acorduri_legare.json: `curs_data`, `cursuri` și echivalentul în euro (`eur`) al fiecărei sume din fișier,
    ca pagina „Debursări pe acorduri” să lucreze cu aceleași cursuri ca registrul.

Ce nu vine de la BCE se calculează la fel ca până acum:
  * EUR = 1, ECU = 1, DEM = 1,95583 (cursul fix de trecere la euro);
  * ROL (leul românesc vechi) = 10 000 × RON;
  * DST (drepturile speciale de tragere) = 1 / valoarea în euro a coșului FMI (0,57813 USD + 0,37379 EUR + 1,0993 CNY +
    13,452 JPY + 0,08087 GBP, în vigoare din 1 august 2022), la cursurile zilei. Cu cursurile din 1 iulie 2026 dă
    exact 1 DST = 1,1905 EUR, valoarea cu care erau scrise paginile.

Scriptul nu schimbă nimic când data BCE nu e mai nouă decât cea din pagină (sâmbătă, duminică, sărbători) sau când
cursurile primite nu par bune (lipsește o valută, un curs iese cu mai mult de 30% din cel de până acum). Ultimul caz
oprește rularea cu eroare, ca să se vadă în Actions, iar fișierele rămân cum erau.

Folosire: `python curs_bce.py` (descarcă de la BCE) sau `python curs_bce.py fisier.xml` (din fișier, pentru probă);
`--director D` schimbă folderul cu fișierele paginilor.
"""
import argparse
import json
import math
import re
import sys
import time
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

AICI = Path(__file__).resolve().parent
URL_BCE = 'https://www.ecb.europa.eu/stats/eurofxref/eurofxref-daily.xml'
PAGINI = ('acorduri.html', 'legis_acorduri.html')
FISIER_DATE = Path('date') / 'acorduri_legare.json'

# valutele luate direct de la BCE (restul se deduc, vezi mai sus)
DE_LA_BCE = ('USD', 'JPY', 'CHF', 'SEK', 'CAD', 'DKK', 'GBP', 'PLN', 'RON', 'CNY', 'CZK')
FIXE = {'EUR': 1, 'ECU': 1, 'DEM': 1.95583}
# coșul DST al FMI (unități din fiecare valută într-un DST), în vigoare din 1 august 2022; în euro, EUR are 0,37379
COS_DST = {'USD': 0.57813, 'CNY': 1.0993, 'JPY': 13.452, 'GBP': 0.08087}
COS_DST_EUR = 0.37379
LUNI = ['ianuarie', 'februarie', 'martie', 'aprilie', 'mai', 'iunie', 'iulie', 'august', 'septembrie', 'octombrie', 'noiembrie', 'decembrie']
TOLERANTA = 0.30                       # un curs nou nu poate diferi cu mai mult de 30% de cel de până acum


def data_ro(iso):
    """2026-07-01 → „1 iulie 2026” (fără zero în față, ca în pagini)."""
    a, l, z = (int(x) for x in iso.split('-'))
    return '%d %s %d' % (z, LUNI[l - 1], a)


def iso_din_ro(text):
    """„1 iulie 2026” → (2026, 7, 1), ca două date să se compare; None dacă nu se poate citi."""
    m = re.fullmatch(r'\s*(\d{1,2}) ([a-zăâîșşțţ]+) (\d{4})\s*', text or '', re.I)
    if not m or m.group(2).lower() not in LUNI:
        return None
    return int(m.group(3)), LUNI.index(m.group(2).lower()) + 1, int(m.group(1))


def citeste_xml(text):
    """XML-ul zilnic al BCE → (data ISO, {valuta: curs}). Cursurile rămân numere, cu cifrele scrise de BCE."""
    radacina = ET.fromstring(text)
    data, cursuri = None, {}
    for el in radacina.iter():
        if el.tag.endswith('}Cube') or el.tag == 'Cube':
            if el.get('time'):
                data = el.get('time')
            elif el.get('currency') and el.get('rate'):
                cursuri[el.get('currency')] = float(el.get('rate'))
    if not data or not re.fullmatch(r'\d{4}-\d{2}-\d{2}', data):
        raise ValueError('XML-ul BCE nu are data cursurilor')
    return data, cursuri


def descarca(url=URL_BCE, incercari=4, asteapta=20):
    """Descarcă XML-ul BCE; reîncearcă de câteva ori (rețea, serviciu ocupat)."""
    ultima = None
    for i in range(incercari):
        try:
            cerere = urllib.request.Request(url, headers={'User-Agent': 'acorduri.vivi.md curs_bce.py (cursul zilnic BCE)'})
            with urllib.request.urlopen(cerere, timeout=30) as r:
                return r.read().decode('utf-8')
        except Exception as e:                                      # noqa: BLE001 - orice eroare de rețea se reîncearcă
            ultima = e
            print('BCE nu a răspuns (încercarea %d din %d): %s' % (i + 1, incercari, e), file=sys.stderr)
            if i + 1 < incercari:
                time.sleep(asteapta)
    raise RuntimeError('nu am putut citi cursurile BCE: %s' % ultima)


def valoare_dst_eur(c):
    """Valoarea unui DST în euro, din coșul FMI, la cursurile BCE ale zilei."""
    return COS_DST_EUR + sum(unitati / c[v] for v, unitati in COS_DST.items())


def cursuri_noi(de_la_bce, vechi):
    """Tabelul complet de cursuri (în ordinea celui vechi), din cele ale BCE. Ridică ValueError dacă ceva nu e bun."""
    lipsesc = [v for v in DE_LA_BCE if v not in de_la_bce]
    if lipsesc:
        raise ValueError('BCE nu a dat cursul pentru: ' + ', '.join(lipsesc))
    c = dict(FIXE)
    c.update({v: de_la_bce[v] for v in DE_LA_BCE})
    c['ROL'] = round(c['RON'] * 10000)
    c['DST'] = round(1 / valoare_dst_eur(c), 5)
    rau = [v for v, x in c.items() if not (isinstance(x, (int, float)) and x > 0)]
    if rau:
        raise ValueError('curs nevalid pentru: ' + ', '.join(rau))
    for v, x in c.items():
        if v in vechi and vechi[v] and abs(x / vechi[v] - 1) > TOLERANTA:
            raise ValueError('cursul %s (%s) diferă cu mai mult de %d%% de cel de până acum (%s): nu-l scriu' % (v, x, TOLERANTA * 100, vechi[v]))
    return {v: c[v] for v in (list(vechi) + [k for k in c if k not in vechi]) if v in c}


def numar_js(x):
    """Numărul, scris scurt, ca în pagini (fără zerouri la coadă)."""
    if isinstance(x, int) or float(x).is_integer():
        return str(int(x))
    return repr(float(x))


def text_per_eur(c):
    """Tabelul `PER_EUR` din pagini, pe două rânduri (primele 7 valute, apoi restul)."""
    perechi = ['%s: %s' % (v, numar_js(x)) for v, x in c.items()]
    return 'var PER_EUR = { ' + ', '.join(perechi[:7]) + ',\n                  ' + ', '.join(perechi[7:]) + ' };'


RX_PER_EUR = re.compile(r'var PER_EUR = \{[^}]*\};')
RX_CURS_DATA = re.compile(r"var CURS_DATA = '[^']*';")
RX_COMENT_DATA = re.compile(r'(Centrale Europene din )\d{1,2} [a-zăâîșşțţ]+ \d{4}(\. DST)')
RX_COMENT_DST = re.compile(r'1 DST = [\d,]+ EUR')


def cursurile_din_pagina(html):
    """(data, {valuta: curs}) scrise acum în pagină; None dacă pagina nu are tabelul."""
    m, d = RX_PER_EUR.search(html), RX_CURS_DATA.search(html)
    if not m or not d:
        return None
    return d.group(0).split("'")[1], {k: float(v) for k, v in re.findall(r'([A-Z]{3}): ([\d.]+)', m.group(0))}


def rescrie_pagina(html, data_iso, c):
    """Pagina cu data și cursurile noi. Ridică ValueError dacă nu găsește locurile de schimbat."""
    if not RX_PER_EUR.search(html) or not RX_CURS_DATA.search(html):
        raise ValueError('nu găsesc CURS_DATA / PER_EUR în pagină')
    ro = data_ro(data_iso)
    html = RX_PER_EUR.sub(lambda m: text_per_eur(c), html, count=1)
    html = RX_CURS_DATA.sub(lambda m: "var CURS_DATA = '%s';" % ro, html, count=1)
    html = RX_COMENT_DATA.sub(lambda m: m.group(1) + ro + m.group(2), html, count=1)
    html = RX_COMENT_DST.sub(lambda m: '1 DST = %s EUR' % ('%.4f' % (1 / c['DST'])).replace('.', ','), html, count=1)
    return html


def euro(v, valuta, c):
    """Ca în pagini: Math.round(v / curs) (jumătățile în sus)."""
    return int(math.floor(v / c[valuta] + 0.5))


def rescrie_date(text, data_iso, c):
    """date/acorduri_legare.json cu cursurile noi și echivalentul în euro al fiecărei sume. Păstrează forma fișierului (un acord pe linie)."""
    d = json.loads(text)
    d['curs_data'] = data_ro(data_iso)
    d['cursuri'] = c
    schimbate = [0]

    def parcurge(x):
        if isinstance(x, dict):
            if 'v' in x and 'val' in x and 'eur' in x and x['val'] in c and isinstance(x['v'], (int, float)):
                nou = euro(x['v'], x['val'], c)
                if nou != x['eur']:
                    x['eur'] = nou
                    schimbate[0] += 1
            for y in x.values():
                parcurge(y)
        elif isinstance(x, list):
            for y in x:
                parcurge(y)
    parcurge(d.get('acorduri', []))
    antet = json.dumps({k: v for k, v in d.items() if k != 'acorduri'}, ensure_ascii=False, separators=(',', ':'))[:-1]
    linii = ',\n'.join(json.dumps(a, ensure_ascii=False, separators=(',', ':')) for a in d['acorduri'])
    return antet + ',"acorduri":[\n' + linii + '\n]}\n', schimbate[0]


def actualizeaza(director, xml_text):
    """Scrie cursurile din `xml_text` în fișierele din `director`. Întoarce un rezumat (text), sau None dacă nu era nimic de schimbat."""
    director = Path(director)
    data_iso, de_la_bce = citeste_xml(xml_text)
    data_noua = iso_din_ro(data_ro(data_iso))
    pagina_sursa = director / PAGINI[0]
    html = pagina_sursa.read_text(encoding='utf-8')
    actual = cursurile_din_pagina(html)
    if actual is None:
        raise ValueError('%s nu are CURS_DATA / PER_EUR' % PAGINI[0])
    data_actuala, vechi = actual
    prima = iso_din_ro(data_actuala)
    if prima and data_noua <= prima:
        return None
    c = cursuri_noi(de_la_bce, vechi)
    scrise = []
    for nume in PAGINI:
        cale = director / nume
        if not cale.exists():
            continue
        scrise.append((cale, rescrie_pagina(cale.read_text(encoding='utf-8'), data_iso, c)))
    cale_date = director / FISIER_DATE
    nr_eur = 0
    if cale_date.exists():
        text, nr_eur = rescrie_date(cale_date.read_text(encoding='utf-8'), data_iso, c)
        scrise.append((cale_date, text))
    for cale, text in scrise:                                      # scrierea abia după ce toate s-au calculat: ori toate, ori niciunul
        cale.write_text(text, encoding='utf-8')
    return 'cursul BCE din %s (înainte: %s): USD %s, JPY %s, DST %s; %d fișiere scrise, %d sume în euro schimbate' % (
        data_ro(data_iso), data_actuala, numar_js(c['USD']), numar_js(c['JPY']), numar_js(c['DST']), len(scrise), nr_eur)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('xml', nargs='?', help='fișier XML în formatul BCE (în loc de descărcare)')
    ap.add_argument('--director', default=str(AICI))
    a = ap.parse_args()
    try:
        text = Path(a.xml).read_text(encoding='utf-8') if a.xml else descarca()
        rez = actualizeaza(a.director, text)
    except (ValueError, RuntimeError, ET.ParseError) as e:
        print('EROARE: %s' % e, file=sys.stderr)
        return 1
    print(rez or 'Cursul din pagini e deja cel mai nou (sau BCE nu a publicat altul): nimic de schimbat.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
