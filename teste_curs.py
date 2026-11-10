"""Testele actualizării cursului valutar (curs_bce.py). Rapide, fără rețea: XML-ul BCE e simulat.

    python teste_curs.py

Verifică: citirea XML-ului BCE, data în română, calculul DST și ROL, scrierea în pagini și în date/acorduri_legare.json
(pe o copie a fișierelor reale), că nu se schimbă nimic când data nu e mai nouă, și refuzul cursurilor care nu par bune.
"""
import json, re, shutil, sys, tempfile
from pathlib import Path

AICI = Path(__file__).resolve().parent
sys.path.insert(0, str(AICI))
import curs_bce as cb

picat = []


def verifica(nume, conditie, detaliu=''):
    print(('  ok   ' if conditie else '  PICĂ ') + nume + ('' if conditie else f'  → {detaliu}'))
    if not conditie:
        picat.append(nume)


def xml(data, cursuri):
    """XML în forma celui de la BCE (cu spațiile de nume ale lui)."""
    celule = ''.join('<Cube currency="%s" rate="%s"/>' % (v, r) for v, r in cursuri.items())
    return ('<?xml version="1.0" encoding="UTF-8"?><gesmes:Envelope xmlns:gesmes="http://www.gesmes.org/xml/2002-08-01" '
            'xmlns="http://www.ecb.int/vocabulary/2002-08-01/eurofxref"><gesmes:subject>Reference rates</gesmes:subject>'
            '<gesmes:Sender><gesmes:name>European Central Bank</gesmes:name></gesmes:Sender><Cube><Cube time="%s">%s</Cube></Cube></gesmes:Envelope>' % (data, celule))


# cursurile BCE din 1 iulie 2026, cu care sunt scrise paginile acum (plus valute pe care pagina nu le folosește)
IULIE = {'USD': '1.1383', 'JPY': '185.21', 'CHF': '0.9234', 'SEK': '11.0955', 'CAD': '1.6191', 'DKK': '7.4745', 'GBP': '0.85973',
         'PLN': '4.2958', 'RON': '5.2367', 'CNY': '7.7342', 'CZK': '24.254', 'AUD': '1.65', 'HUF': '390.1'}

print('Data și XML-ul BCE')
verifica('data în română, fără zero în față', [cb.data_ro('2026-07-01'), cb.data_ro('2026-11-10'), cb.data_ro('2027-02-03')], ['1 iulie 2026', '10 noiembrie 2026', '3 februarie 2027'])
verifica('data din pagină se citește înapoi, ca să se poată compara', [cb.iso_din_ro('1 iulie 2026'), cb.iso_din_ro('10 noiembrie 2026'), cb.iso_din_ro('ceva')], [(2026, 7, 1), (2026, 11, 10), None])
d, c = cb.citeste_xml(xml('2026-11-10', IULIE))
verifica('XML-ul BCE: data și cursurile (ca numere)', d == '2026-11-10' and c['USD'] == 1.1383 and c['CZK'] == 24.254 and len(c) == len(IULIE), (d, c))
try:
    cb.citeste_xml('<a><b/></a>')
    verifica('XML fără dată: eroare', False)
except ValueError:
    verifica('XML fără dată: eroare', True)

print('DST, ROL și tabelul')
cj = cb.cursuri_noi({k: float(v) for k, v in IULIE.items()}, {})
verifica('cu cursurile din 1 iulie 2026, DST = 0,83998 per EUR (1 DST = 1,1905 EUR), ca în pagini', cj['DST'] == 0.83998, cj['DST'])
verifica('ROL = 10 000 × RON; EUR, ECU 1; marca germană are cursul fix', cj['ROL'] == 52367 and cj['EUR'] == 1 and cj['ECU'] == 1 and cj['DEM'] == 1.95583, cj)
verifica('valutele pe care pagina nu le folosește (AUD, HUF) nu intră în tabel', 'AUD' not in cj and 'HUF' not in cj, sorted(cj))
vechi_ord = {'EUR': 1, 'DST': 0.8, 'USD': 1.1, 'JPY': 180}
verifica('tabelul vechi: cheile se păstrează în ordinea lui, cele noi vin la coadă', list(cb.cursuri_noi({k: float(v) for k, v in IULIE.items()}, vechi_ord))[:4] == ['EUR', 'DST', 'USD', 'JPY'])
verifica('numerele se scriu scurt: 1 / 24,25 / 0,83998', [cb.numar_js(1), cb.numar_js(24.25), cb.numar_js(0.83998), cb.numar_js(52367.0)], ['1', '24.25', '0.83998', '52367'])

print('Scrierea în fișiere (pe o copie)')
tmp = Path(tempfile.mkdtemp())
try:
    (tmp / 'date').mkdir()
    for f in ('acorduri.html', 'legis_acorduri.html', 'date/acorduri_legare.json'):
        shutil.copy(AICI / f, tmp / f)
    inainte = {f: (tmp / f).read_text(encoding='utf-8') for f in ('acorduri.html', 'legis_acorduri.html', 'date/acorduri_legare.json')}
    vechi = cb.cursurile_din_pagina(inainte['acorduri.html'])
    verifica('pagina are acum data și cursurile (EUR 1, USD, DST)', vechi is not None and vechi[1].get('EUR') == 1 and 'USD' in vechi[1] and 'DST' in vechi[1], vechi)
    data_veche = vechi[0]
    # cursurile de acum ale paginii, în forma XML-ului BCE (plus valute pe care pagina nu le folosește): cu ele, scrierea trebuie să lase tabelul neschimbat
    ACUM = {v: repr(vechi[1][v]) for v in cb.DE_LA_BCE}
    ACUM.update({'AUD': '1.65', 'HUF': '390.1'})

    # aceeași dată, sau mai veche: nimic nu se schimbă
    azi_pagina = cb.iso_din_ro(data_veche)
    iso_veche = '%04d-%02d-%02d' % azi_pagina
    verifica('aceeași dată ca în pagină: nimic de schimbat', cb.actualizeaza(tmp, xml(iso_veche, ACUM)) is None and all((tmp / f).read_text(encoding='utf-8') == t for f, t in inainte.items()))
    verifica('o dată mai veche: nimic de schimbat', cb.actualizeaza(tmp, xml('2020-01-02', ACUM)) is None and all((tmp / f).read_text(encoding='utf-8') == t for f, t in inainte.items()))

    # o zi nouă, cu aceleași cursuri: se schimbă doar data (cursurile sunt cele de acum, deci textul tabelului trebuie să iasă la fel)
    rez = cb.actualizeaza(tmp, xml('2030-03-04', ACUM))
    verifica('o zi mai nouă: se scrie, cu rezumat', rez is not None and '4 martie 2030' in rez and '3 fișiere' in rez, rez)
    for f in ('acorduri.html', 'legis_acorduri.html'):
        t = (tmp / f).read_text(encoding='utf-8')
        verifica(f + ': CURS_DATA și comentariul au data nouă', "var CURS_DATA = '4 martie 2030';" in t and 'Centrale Europene din 4 martie 2030. DST' in t, re.findall(r"var CURS_DATA = '[^']*';", t))
        verifica(f + ': cu aceleași cursuri, tabelul PER_EUR și mențiunea DST ies identice cu cele de dinainte', cb.RX_PER_EUR.search(t).group(0) == cb.RX_PER_EUR.search(inainte[f]).group(0) and cb.RX_COMENT_DST.search(t).group(0) == cb.RX_COMENT_DST.search(inainte[f]).group(0),
                 (cb.RX_PER_EUR.search(t).group(0), cb.RX_PER_EUR.search(inainte[f]).group(0)))
        verifica(f + ': în rest, nimic altceva nu s-a schimbat (doar data, de două ori)', len([1 for a, b in zip(t.splitlines(), inainte[f].splitlines()) if a != b]) == 2 and len(t.splitlines()) == len(inainte[f].splitlines()))
    nou = json.loads((tmp / 'date/acorduri_legare.json').read_text(encoding='utf-8'))
    vechi_j = json.loads(inainte['date/acorduri_legare.json'])
    verifica('date/acorduri_legare.json: data nouă, aceleași cursuri, aceleași acorduri', nou['curs_data'] == '4 martie 2030' and nou['cursuri'] == vechi_j['cursuri'] and nou['acorduri'] == vechi_j['acorduri'])
    verifica('fișierul își păstrează forma: un acord pe linie', (tmp / 'date/acorduri_legare.json').read_text(encoding='utf-8').count('\n') == inainte['date/acorduri_legare.json'].count('\n'))

    # o zi nouă, cu cursuri schimbate (USD cu 10% mai scump, yenul cu 5% mai ieftin)
    usd_vechi, jpy_vechi = vechi[1]['USD'], vechi[1]['JPY']
    mod = dict(ACUM, USD=repr(round(usd_vechi * 1.1, 4)), JPY=repr(round(jpy_vechi * 0.95, 2)))          # USD cu 10% mai scump, yenul cu 5% mai ieftin
    rez = cb.actualizeaza(tmp, xml('2030-03-05', mod))
    t = (tmp / 'acorduri.html').read_text(encoding='utf-8')
    verifica('cursuri schimbate: PER_EUR are USD și JPY noi', 'USD: %s,' % mod['USD'] in t and 'JPY: %s,' % mod['JPY'] in t and 'USD: %s,' % cb.numar_js(usd_vechi) not in t, cb.RX_PER_EUR.search(t).group(0))
    verifica('cursuri schimbate: DST se recalculează din coș (alt curs decât înainte)', cb.cursurile_din_pagina(t)[1]['DST'] != vechi[1]['DST'] and abs(cb.cursurile_din_pagina(t)[1]['DST'] - 1 / cb.valoare_dst_eur(cb.cursurile_din_pagina(t)[1])) < 1e-5)
    nou = json.loads((tmp / 'date/acorduri_legare.json').read_text(encoding='utf-8'))
    verifica('cursuri schimbate: și fișierul de date le are, la fel ca pagina', nou['cursuri'] == cb.cursurile_din_pagina(t)[1] and nou['curs_data'] == '5 martie 2030', nou['cursuri'])
    usd = [a for a in nou['acorduri'] if a.get('suma') and a['suma'].get('val') == 'USD' and a['suma'].get('eur')]
    verifica('cursuri schimbate: echivalentul în euro al sumelor în USD e v / curs nou (rotunjit)', usd and all(a['suma']['eur'] == cb.euro(a['suma']['v'], 'USD', nou['cursuri']) for a in usd), len(usd))
    eur = [a for a in nou['acorduri'] if a.get('suma') and a['suma'].get('val') == 'EUR']
    verifica('sumele în EUR rămân cum erau (v rotunjit)', eur and all(a['suma']['eur'] == cb.euro(a['suma']['v'], 'EUR', {'EUR': 1}) for a in eur if a['suma'].get('eur') is not None), len(eur))
    verifica('rezumatul spune câte sume în euro s-au schimbat', rez and re.search(r'(\d+) sume în euro schimbate', rez) and int(re.search(r'(\d+) sume în euro schimbate', rez).group(1)) >= len(usd), rez)

    # cursuri care nu par bune: nimic nu se scrie
    stare = {f: (tmp / f).read_text(encoding='utf-8') for f in ('acorduri.html', 'legis_acorduri.html', 'date/acorduri_legare.json')}
    for nume, cursuri in (('lipsește o valută (USD)', {k: v for k, v in mod.items() if k != 'USD'}), ('un curs cu 50% mai mare', dict(mod, CHF=repr(round(vechi[1]['CHF'] * 1.5, 4)))), ('un curs de zero', dict(mod, SEK='0'))):
        try:
            cb.actualizeaza(tmp, xml('2030-03-06', cursuri))
            verifica('refuzat: ' + nume, False)
        except ValueError as e:
            verifica('refuzat: ' + nume + ' (%s)' % str(e)[:60], all((tmp / f).read_text(encoding='utf-8') == t for f, t in stare.items()))
    # pagina fără tabel
    (tmp / 'acorduri.html').write_text('<html></html>', encoding='utf-8')
    try:
        cb.actualizeaza(tmp, xml('2030-03-07', mod))
        verifica('pagina fără CURS_DATA / PER_EUR: eroare, nu scriere pe dibuite', False)
    except ValueError:
        verifica('pagina fără CURS_DATA / PER_EUR: eroare, nu scriere pe dibuite', True)
finally:
    shutil.rmtree(tmp, ignore_errors=True)

print('Fișierele reale din repository')
real = cb.cursurile_din_pagina((AICI / 'acorduri.html').read_text(encoding='utf-8'))
real_l = cb.cursurile_din_pagina((AICI / 'legis_acorduri.html').read_text(encoding='utf-8'))
date = json.loads((AICI / 'date/acorduri_legare.json').read_text(encoding='utf-8'))
verifica('acorduri.html și legis_acorduri.html au aceleași cursuri și aceeași dată', real == real_l, (real, real_l))
verifica('date/acorduri_legare.json are aceleași cursuri și aceeași dată ca pagina', date['cursuri'] == real[1] and date['curs_data'] == real[0], (date['curs_data'], real[0]))
verifica('DST din tabel = coșul FMI la cursurile din tabel (±0,00001)', abs(real[1]['DST'] - 1 / cb.valoare_dst_eur(real[1])) < 1e-5, (real[1]['DST'], 1 / cb.valoare_dst_eur(real[1])))

print()
if picat:
    print('%d teste au picat: %s' % (len(picat), '; '.join(picat))); sys.exit(1)
print('Toate testele cursului au trecut.')
