"""Testele verificării legis.md. Rulate de workflow înaintea căutării.

    python teste_legis.py            # clasificator + unire (rapid, fără browser)
    python teste_legis.py --browser  # plus un test complet cu Playwright pe un
                                     # legis.md simulat local (inclusiv blocajul Cloudflare)
"""
import json, re, shutil, subprocess, sys, tempfile, threading
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
    # hotărârea publicată la 16 octombrie 2026; regula „acord-cadru" stă acum în monitor_watch (aceeași pentru ambele registre)
    ('privind inițierea negocierilor și aprobarea semnării Acordului-cadru de împrumut dintre Republica Moldova și Banca de Dezvoltare a Consiliului Europei „Modernizarea instituțiilor de învățământ profesional tehnic”', 'Împrumut', 'CEB'),
    ('privind inițierea negocierilor și aprobarea semnării Acordului–cadru de împrumut dintre Republica Moldova și Banca de Dezvoltare a Consiliului Europei „Modernizarea instituțiilor de învățământ profesional tehnic”', 'Împrumut', 'CEB'),
    ('privind ratificarea Acordului de facilitate de împrumut dintre Republica Moldova și Majestatea Sa Regele de drept al Canadei', 'Împrumut', 'Canada'),
    ('pentru ratificarea Acordului de grant, întocmit prin schimb de note, dintre Guvernul Republicii Moldova și Guvernul Japoniei privind asigurarea fermierilor cu fertilizanți', 'Grant', 'Japonia'),
    ('pentru ratificarea Acordului dintre Republica Moldova și Bosnia și Herțegovina privind asistența juridică reciprocă', None, None),
    ('cu privire la acordarea ajutorului umanitar populației din Republica Turcia', None, None),
    ('pentru ratificarea Acordului dintre Republica Moldova și Uniunea Europeană privind participarea Republicii Moldova la Programul Europa Digitală', None, None),
    ('cu privire la reperfectarea licenţei Asociaţiei de Economii şi Împrumut „CIRCULA”', None, None),
    # partenerul din formulări vechi
    ('pentru ratificarea Acordului de finanţare dintre Republica Moldova şi Asociaţia Internaţională de Dezvoltare privind realizarea Proiectului „Suport de urgenţă pentru agricultura Moldovei”', 'Împrumut', 'AID'),
    ('pentru ratificarea Acordului de împrumut dintre Guvernul Republicii Moldova și Guvernul Republicii Polone în sumă de 20 de milioane de euro', 'Împrumut', 'Polonia'),
    ('pentru ratificarea Acordului-cadru dintre Guvernul Republicii Moldova şi Comisia Comunităţilor Europene privind asistenţa externă', 'Grant', 'UE'),
    # acte de cadru, nu acorduri
    ('pentru modificarea Hotărârii Guvernului nr. 246/2010 cu privire la modul de aplicare a facilităților fiscale și vamale aferente realizării proiectelor de asistență tehnică și investițională în derulare, care cad sub incidența tratatelor internaționale la care Republica Moldova este parte sau a contractelor de stat', None, None),
    ('cu privire la Programul de asistenţă tehnică pentru anii 2001-2002', None, None),
    ('cu privire la aprobarea Regulamentului privind autorizarea centrelor de asistenţă tehnică pentru maşinile de casă şi de control/imprimantele fiscale', None, None),
    ('cu privire la Oficiul de Gestionare a Programelor de Asistență Externă', None, None),
    ('privind contractele de credit pentru consumatori', None, None),
    ('pentru ratificarea Acordului de finanțare dintre Republica Moldova și Fondul Internațional pentru Dezvoltarea Agricolă în vederea realizării Proiectului de Reziliență Rurală (IFAD VII)', 'Împrumut', None),
    # asistența financiară se împarte după rambursare: nerambursabilă = grant, rambursabilă = împrumut (credit)
    ('pentru ratificarea Acordului privind asistenţa financiară rambursabilă dintre Republica Moldova şi România', 'Împrumut', 'România'),
    ('cu privire la aprobarea Acordului dintre Guvernul Republicii Moldova și Guvernul Japoniei privind acordarea asistenței financiare nerambursabile', 'Grant', 'Japonia'),
    ('cu privire la aprobarea Acordului dintre Guvernul Republicii Moldova și Guvernul României privind acordarea unui ajutor financiar nerambursabil', 'Grant', 'România'),
    # nerambursabilitatea unei asistențe TEHNICE nu face din ea grant
    ('cu privire la aprobarea Acordului de asistență tehnică nerambursabilă dintre Guvernul Republicii Moldova și Guvernul Japoniei', 'Asistență tehnică', 'Japonia'),
    # cuvântul din titlu bate finanțatorul: BIRD împrumută de obicei, dar aici titlul spune grant
    ('pentru ratificarea Acordului dintre Republica Moldova şi Banca Internaţională pentru Reconstrucţie şi Dezvoltare privind acordarea grantului nr. TF015873 din Fondul de Carbon pentru Dezvoltare', 'Grant', 'BIRD'),
    ('privind promulgarea Legii pentru ratificarea Acordului de finanţare (grant danez) a Programului rural de rezilienţă economico-climatică incluzivă (IRECR) dintre Republica Moldova şi Fondul Internaţional pentru Dezvoltarea Agricolă', 'Grant', 'FIDA'),
    # și invers: un titlu cu „credit" rămâne împrumut chiar dacă numește și un acord de grant
    ('pentru ratificarea Acordului de credit și a Acordului de grant dintre Republica Moldova și Asociaţia Internaţională de Dezvoltare', 'Împrumut', 'AID'),
    ('pentru ratificarea Acordului dintre Republica Moldova şi Banca Europeană pentru Reconstrucţie şi Dezvoltare privind garanţia de stat pentru realizarea proiectului terminalului petrolier Giurgiuleşti', 'Împrumut', 'BERD'),
    # finanțatori care dau doar granturi / doar credite, când titlul nu spune
    ('privind iniţierea negocierilor și aprobarea semnării Acordului de asistență financiară dintre Guvernul Republicii Moldova și Ministerul Afacerilor Externe al Republicii Bulgaria', 'Grant', 'Bulgaria'),
    ('pentru ratificarea Acordului de finanțare dintre Republica Moldova și Banca Europeană de Investiții', 'Împrumut', 'BEI'),
    # KfW a dat și grant, și credit: fără cuvânt în titlu, actul NU se ghicește
    ('cu privire la aprobarea semnării Acordului de finanțare dintre Guvernul Republicii Moldova și KfW Entwicklungsbank', 'Asistență financiară', 'KfW'),
    # IFC împrumută firmelor private, nu statului: acordul de cooperare cu Guvernul e consultanță, nu credit
    ('pentru ratificarea Acordului de cooperare dintre Guvernul Republicii Moldova și Corporația Financiară Internațională în vederea realizării proiectului „Reforma climatului investițional în Republica Moldova, faza II”', 'Asistență tehnică', 'IFC'),
    # titlu cu litere chirilice în loc de cele latine (cod de pagină greșit), fără reparația din legis_pagina
    ('pentru ratificarea Acordului de оmprumut, finanюare şi proiect dintre Banca Germanг "Kreditanstalt fьr Wiederaufbau (KfW)", Republica Moldova şi Fondul de Investiюii Sociale din Moldova (FISM)', 'Împrumut', 'KfW'),
    ('pentru ratificarea Acordului de сredit dintre Republica Moldova și Banca Europeană de Investiții', 'Împrumut', 'BEI'),
    # cooperarea TEHNICĂ dintre guverne e transfer de expertiză, nu bani: asistență tehnică, deși
    # Germania dă granturi (HG238/2026: un expert german detașat pe lângă viceprim-ministru)
    ('cu privire la inițierea negocierilor și aprobarea semnării Înțelegerii, întocmite prin schimb de note, dintre Guvernul Republicii Moldova și Guvernul Republicii Federale Germania privind cooperarea tehnică pentru detașarea unui expert german în cadrul Cabinetului viceprim-ministrului pentru integrare europeană al Republicii Moldova', 'Asistență tehnică', 'Germania'),
    ('pentru inițierea negocierilor și aprobarea semnării Înțelegerii, întocmite prin schimb de note, dintre Guvernul Republicii Moldova și Guvernul Republicii Federale Germania privind cooperarea tehnică', 'Asistență tehnică', 'Germania'),
    ('cu privire la inițierea negocierilor și aprobarea semnării Înțelegerii, întocmite prin schimb de note, dintre Guvernul Republicii Moldova și Guvernul Republicii Federale Germania cu privire la cooperarea tehnică ce vizează proiectul „Modernizarea serviciilor comunale”', 'Asistență tehnică', 'Germania'),
    ('cu privire la inițierea negocierilor și aprobarea semnării Înțelegerii, întocmite prin schimb de note, dintre Guvernul Republicii Moldova și Guvernul Republicii Federale Germania privind cooperarea tehnică pentru finanțarea proiectului „Suport comunităților moldovenești”', 'Asistență tehnică', 'Germania'),
    # cooperarea FINANCIARĂ cu Germania (KfW) rămâne grant
    ('pentru inițierea negocierilor și aprobarea semnării Înțelegerii, întocmite prin schimb de note, dintre Guvernul Republicii Moldova și Guvernul Republicii Federale Germania privind cooperarea financiară', 'Grant', 'Germania'),
    # „cooperarea tehnică și financiară" e și una, și alta: nu se mută la asistență tehnică, o hotărăște finanțatorul
    ('pentru inițierea negocierilor și aprobarea semnării Înțelegerii, întocmite prin schimb de note, dintre Guvernul Republicii Moldova și Guvernul Republicii Federale Germania privind cooperarea tehnică și financiară', 'Grant', 'Germania'),
    # Facilitatea de cooperare tehnică a UE: același instrument, scris cu „de" ori cu „pentru"
    ('cu privire la inițierea negocierilor și aprobarea semnării Acordului de finanțare dintre Guvernul Republicii Moldova și Uniunea Europeană privind Facilitatea de cooperare tehnică 2016', 'Asistență tehnică', 'UE'),
    ('cu privire la inițierea negocierilor și aprobarea semnării Acordului de finanțare dintre Guvernul Republicii Moldova și Uniunea Europeană privind Facilitatea pentru cooperare tehnică', 'Asistență tehnică', 'UE'),
    # agenția elvețiană implementează proiecte: „acord" ca și „memorandum" = asistență tehnică; „acord de grant" rămâne grant
    ('privind inițierea negocierilor și aprobarea semnării Acordului dintre Ministerul Sănătății al Republicii Moldova și Agenția Elvețiană pentru Dezvoltare și Cooperare privind a doua fază a Proiectului „Progresul cu privire la acoperirea universală cu servicii de sănătate în Moldova”', 'Asistență tehnică', 'Elveția'),
    ('cu privire la Acordul între Parlamentul Republicii Moldova și Agenția Elvețiană pentru Dezvoltare și Cooperare privind prima fază a proiectului „Consolidarea Democrației Parlamentare în Moldova (PADEM)”', 'Asistență tehnică', 'Elveția'),
    ('cu privire la inițierea negocierilor și aprobarea semnării Memorandumului de înțelegere dintre Ministerul Sănătății al Republicii Moldova și Agenția Elvețiană pentru Dezvoltare și Cooperare privind prima fază a Proiectului „Progresul cu privire la acoperirea universală cu servicii de sănătate în Moldova”', 'Asistență tehnică', 'Elveția'),
    ('cu privire la aprobarea semnării Acordului de grant dintre Ministerul Sănătății al Republicii Moldova și Agenția Elvețiană pentru Dezvoltare și Cooperare privind a doua fază a Proiectului „X”', 'Grant', 'Elveția'),
    # un acord cu aceeași agenție care nu e despre un proiect nu devine asistență tehnică pe baza numelui ei
    ('pentru ratificarea Acordului de finanțare dintre Republica Moldova și Agenția Elvețiană pentru Dezvoltare și Cooperare', 'Grant', 'Elveția'),
]
for t, cat, part in CAZURI:
    c = clasifica(t)
    verifica(f'{(cat or "respins"):10} {t[:70]}…', c == cat, f'a dat {c}')
    if cat and part:
        verifica(f'partener {part}', part in partener(t), partener(t))

print('Categorii hotărâte de mână (date/categorii_manual.json)')
import legis_clasifica as lc
_titlu_fr = ('cu privire la inițierea negocierilor asupra proiectului Protocolului financiar dintre Guvernul Republicii Moldova și Guvernul '
             'Republicii Franceze privind finanțarea proiectului de modernizare a infrastructurii feroviare Chișinău – Ungheni')
verifica('fără decizie, titlul care nu spune dacă banii se rambursează rămâne „Asistență financiară”', clasifica(_titlu_fr) == 'Asistență financiară', clasifica(_titlu_fr))
verifica('decizia de mână bate clasificarea automată', lc.categorie_act('HG241/2023', _titlu_fr, {'HG241/2023': {'categorie': 'Împrumut'}}) == 'Împrumut')
verifica('alt cod, altă decizie: clasificarea automată rămâne', lc.categorie_act('HG1/2023', _titlu_fr, {'HG241/2023': {'categorie': 'Împrumut'}}) == 'Asistență financiară')
verifica('decizia nu adaugă acte: un titlu respins rămâne respins',
         lc.categorie_act('HG7/2023', 'cu privire la aprobarea Regulamentului intern', {'HG7/2023': {'categorie': 'Grant'}}) is None)
_t = Path(tempfile.mkdtemp())
try:
    json.dump({'_nota': 'ignorat',
               'A1/2020': {'categorie': 'Grant', 'motiv': 'm', 'sursa': 'https://x'},
               'A2/2020': {'categorie': 'Grant', 'motiv': 'm'},                        # fără sursă
               'A3/2020': {'categorie': 'Credit', 'motiv': 'm', 'sursa': 'https://x'},  # categorie inexistentă
               'A4/2020': {'categorie': 'Împrumut', 'motiv': ' ', 'sursa': 'https://x'}},   # motiv gol
              open(_t / 'm.json', 'w', encoding='utf-8'))
    _d = lc.decizii_manuale(_t / 'm.json')
    verifica('doar intrările complete (categorie validă + motiv + sursă) se aplică', list(_d) == ['A1/2020'], list(_d))
    verifica('fișierul lipsă nu oprește nimic', lc.decizii_manuale(_t / 'nu_exista.json') == {})
finally:
    shutil.rmtree(_t, ignore_errors=True)
_real = json.load(open(AICI / 'date' / 'categorii_manual.json', encoding='utf-8'))
verifica('date/categorii_manual.json: toate intrările au categorie validă, motiv și sursă (altfel ar fi ignorate)',
         set(lc.decizii_manuale()) == {k for k in _real if not k.startswith('_')}, sorted({k for k in _real if not k.startswith('_')} - set(lc.decizii_manuale())))
_brut = {r['c']: r for r in json.load(open(AICI / 'legis_brut.json', encoding='utf-8'))}
_coduri_mo = {pagina.cod_legis(a)[0] for a in json.load(open(AICI / 'date.json', encoding='utf-8')).get('acte', {}).values()}
verifica('fiecare decizie de mână privește un act din registru (din istoricul legis.md sau, dacă e foarte nou, doar din Monitor)',
         all((k in _brut and clasifica(pagina.repara(re.sub(r'^(Modificat|Abrogat|Suspendat)\s*', '', _brut[k]['t']).strip()))) or k in _coduri_mo
             for k in lc.decizii_manuale()),
         [k for k in lc.decizii_manuale() if k not in _brut and k not in _coduri_mo])

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

print()
print('Suma ACORDULUI din documentul atașat (suma_acord)')
_msl = open(AICI / 'teste_date_msl.txt', encoding='utf-8').read() if (AICI / 'teste_date_msl.txt').exists() else ''
if _msl:
    _r = ls.suma_acord(_msl, 'grant')
    verifica('Moldova Solidarity Lanes: suma acordului 12.000.000 EUR (nu împrumutul de 41,2 mil. din alt acord)',
             _r['suma'] and (_r['suma']['v'], _r['suma']['val']) == (12000000, 'EUR'), _r['suma'])
    verifica('Moldova Solidarity Lanes: costul total al proiectului 119.000.000 EUR, separat',
             _r['cost'] and (_r['cost']['v'], _r['cost']['val']) == (119000000, 'EUR'), _r['cost'])
for _t, _i, _s, _c in [
    ('Banca acordă Împrumutatului un credit în valoare de 25 000 000 EUR în temeiul prezentului Contract. '
     '1.2. Costul total estimat al Proiectului este de 60 000 000 EUR.', 'imprumut', (25000000, 'EUR'), (60000000, 'EUR')),
    ('The Bank hereby agrees to lend to the Borrower an amount equal to EUR 30,000,000. The total cost of the Project is '
     'estimated at EUR 75,000,000. A front-end fee of EUR 75,000 shall be paid.', 'imprumut', (30000000, 'EUR'), (75000000, 'EUR')),
    ('Whereas the Borrower has received a loan of EUR 40,000,000 under a separate finance contract. The Bank shall make '
     'available to the Beneficiary a grant in an amount not exceeding EUR 5,000,000 under this Agreement.', 'grant', (5000000, 'EUR'), None)]:
    _r = ls.suma_acord(_t, _i)
    verifica(f'{_i}: suma {_s[0]:,} {_s[1]}'.replace(',', ' ') + (f', cost {_c[0]:,}'.replace(',', ' ') if _c else ''),
             _r['suma'] and (_r['suma']['v'], _r['suma']['val']) == _s and
             ((_r['cost']['v'], _r['cost']['val']) if _r['cost'] else None) == _c, _r)

print()
print('Acordurile atașate la acte (legis_atasamente.py)')
import legis_atasamente as la
_l = la.linkuri_din_html('<a href="/UserFiles/Image/RO/2022/mo230-234md/acord 203 ro.pdf">a</a>'
                         "<a href='https://www.legis.md/UserFiles/Image/x.PDF'>b</a><a href=\"/UserFiles/Image/x.PDF\">dublură</a>"
                         '<a href="/cautare/downloadpdf/1">actul</a><img src="/UserFiles/Image/sigla.png">',
                         'https://www.legis.md/cautare/getResults?doc_id=132350&lang=ro')
verifica('atașamentele din fișa actului: doar PDF-urile din UserFiles, fără dubluri, cu spațiile codate',
         _l == ['https://www.legis.md/UserFiles/Image/RO/2022/mo230-234md/acord%20203%20ro.pdf', 'https://www.legis.md/UserFiles/Image/x.PDF'], _l)
_u = la.uneste([{'u': 'https://x/a%20b.pdf', 'suma': {'v': 1, 'val': 'EUR', 'manual': True}}, {'u': 'https://x/c.pdf', 'suma': {'v': 5, 'val': 'EUR'}},
                {'u': 'https://x/vechi.pdf', 'suma': None}],
               [{'u': 'https://x/a b.pdf', 'suma': {'v': 2, 'val': 'EUR'}}, {'u': 'https://x/c.pdf', 'suma': None}, {'u': 'https://x/d.pdf', 'suma': {'v': 9, 'val': 'USD'}}])
verifica('suma pusă de mână nu e înlocuită', _u[0]['suma']['v'] == 1, _u[0])
verifica('o sumă deja găsită nu e ștearsă de o recitire fără rezultat', _u[1]['suma'] and _u[1]['suma']['v'] == 5, _u[1])
verifica('atașamentele noi se adaugă, cele vechi rămân', [x['u'][-5:] for x in _u[2:]] == ['d.pdf', 'i.pdf'], _u)
verifica('actul neparcurs se deschide; cel parcurs, nu', la.are_nevoie({'sume': []})
         and not la.are_nevoie({'sume': [], 'atas': [], 'atas_citit': 'x', 'fisa_ok': 1}) and not la.are_nevoie(None))
verifica('„niciun atașament” fără fișă confirmată se mai verifică o dată; cu atașamente găsite, nu',
         la.are_nevoie({'sume': [], 'atas': [], 'atas_citit': 'x'})
         and not la.are_nevoie({'sume': [], 'atas_citit': 'x', 'atas': [{'u': 'u', 'suma': None, 'metoda': 'text'}]}))
_f25 = 'The Bank agrees to lend to the Borrower the amount of EUR 25,000,000 (twenty-five million Euros). Front-end fee of EUR 62,500.'
_cred = {'atas_citit': 'x', 'fisa_ok': 1, 'instr': 'grant', 'atas': [{'u': 'u', 'suma': {'v': 25000000, 'val': 'EUR', 'f': _f25}, 'metoda': 'text'}]}
verifica('instrumentul de azi (din categorie) bate „instr” rămas din vechea clasificare: un credit notat „grant” își recitește suma, dar nu cel notat corect',
         la.are_nevoie(_cred) and not la.are_nevoie(_cred, instr='imprumut') and la.are_nevoie(_cred, instr='grant'))
verifica('instrument(): „imprumut” doar pentru împrumuturi, după categoria de azi, cu titlul curățat de „Modificat”',
         la.instrument('Modificat pentru ratificarea Acordului privind asistența financiară rambursabilă dintre Republica Moldova și România') == 'imprumut'
         and la.instrument('pentru ratificarea Acordului de grant dintre Republica Moldova și Uniunea Europeană') == 'grant'
         and la.instrument(_titlu_fr, 'HG241/2023', {'HG241/2023': {'categorie': 'Împrumut'}}) == 'imprumut')
verifica('fișa care încă își încarcă conținutul nu trece drept citită',
         not la.fisa_incarcata('Conținutul se încarcă... ' + 'x' * 400) and not la.fisa_incarcata('scurt')
         and la.fisa_incarcata('Lege pentru ratificarea Acordului ' * 20))
verifica('actul cu descărcarea eșuată se reia singur de câteva ori, apoi doar cu --reincearca',
         ls.de_reincercat({'eroare': ls.ESEC_DESCARCARE + ': Failed to fetch', 'incercari': 1})
         and not ls.de_reincercat({'eroare': ls.ESEC_DESCARCARE + ': x', 'incercari': ls.MAX_INCERCARI_DESCARCARE})
         and not ls.de_reincercat({'eroare': 'HTTP 404, nu e PDF'}) and not ls.de_reincercat({'sume': []}))
verifica('--reincearca reia PDF-urile scanate rămase fără text',
         la.are_nevoie({'atas_citit': 'x', 'atas': [{'u': 'u', 'suma': None, 'metoda': 'fara-text'}]}, reincearca=True)
         and not la.are_nevoie({'atas_citit': 'x', 'atas': [{'u': 'u', 'suma': None, 'metoda': 'text'}]}, reincearca=True))
_r = ls.suma_acord('2.01. Banca este de acord să acorde Împrumutatului suma de 17.700.000 Euro. 2.02. Împrumutatul poate retrage mijloacele.', 'imprumut')
verifica('sub prag: nicio sumă publicată, dar candidatul rămâne la vedere', _r['suma'] is None and _r['candidat'] and _r['candidat']['v'] == 17700000, _r)

print()
print('Sume luate greșit, văzute pe site (regulile din octombrie 2026)')
_s = lambda t, i='grant': (ls.suma_acord(t, i)['suma'] or {}).get('v')
_t = lambda t: [(x['v'], x['val']) for x in ls.sume_din_text(t)][:1]
verifica('un cont bancar nu e o sumă (REC4SMEs: MD04VI022240300000368EUR)',
         _s('90 % din valoarea maximă a grantului. Contul bancar pentru plăți: MD04VI022240300000368EUR VICBMD2XXXX') is None
         and not _t('Contul bancar pentru plăți: MD04VI022240300000368EUR'))
verifica('suma întreagă, nu prima tranșă',
         _s('Banca acordă, în temeiul prezentului Acord, un împrumut în valoare de până la 150.000.000 EUR, constând în: (i) Tranșa 1, '
            'în valoare de până la 90.000.000 EUR și (ii) Tranșa 2, în valoare de până la 60.000.000 EUR.', 'imprumut') == 150000000)
verifica('o cotă dintr-o sumă mai mare nu e suma acordului',
         _s('a maximum amount of EUR 7 526 403 out of the EUR 77 290 439 of the financial contribution under this Agreement for the grant') != 7526403)
verifica('plafonul de achiziții (2 500 CHF) nu e suma acordului',
         _s('under this Agreement the Ministry may undertake single-source procurement for a maximum value of up to 50,000 MDL (approximately 2,500 CHF) of the grant') is None)
verifica('un număr rupt în PDF („35.700.00 EUR") nu se ghicește',
         _s('Asociația acordă, în temeiul prezentului Acord, un credit în sumă de 35.700.00 EUR', 'imprumut') is None)
verifica('„3,075 milioane dolari" = 3,075 mil., nu 3 miliarde', _t('mijloace financiare în valoare de 3,075 milioane dolari S.U.A.') == [(3075000, 'USD')],
         _t('mijloace financiare în valoare de 3,075 milioane dolari S.U.A.'))
verifica('„5 926,0 milioane de yeni" rămâne 5,9 miliarde', _t('Se ratifică Acordul de împrumut în sumă de 5 926,0 milioane de yeni japonezi') == [(5926000000, 'JPY')])
verifica('D.S.T. înaintea echivalentului aproximativ în dolari',
         _t('Se ratifică Acordul de credit în sumă de 4.000.000 D.S.T. (circa 5 milioane dolari S.U.A.).') == [(4000000, 'DST')])
verifica('leii românești nu sunt lei moldovenești', _t('împrumutul pe termen lung în valoare de 20 miliarde lei româneşti, semnat') == [(20000000000, 'ROL')])
verifica('suma veche greșită e trimisă la recitit; cea bună și cea pusă de mână, nu',
         not ls.sume_tin({'sume': [{'v': 3075000000, 'val': 'USD', 'f': 'în valoare de 3,075 milioane dolari S.U.A. din'}]})
         and ls.sume_tin({'sume': [{'v': 600000, 'val': 'EUR', 'f': 'Se ratifică Acordul de grant, în sumă de 600000 de euro, semnat'}]})
         and not ls.suma_atas_tine({'suma': {'v': 22240300000368, 'val': 'EUR', 'f': 'valoarea maximă a grantului Contul bancar pentru plăți: MD04VI022240300000368EUR'}}, 'grant')
         and ls.suma_atas_tine({'suma': {'v': 1, 'val': 'EUR', 'f': 'x', 'manual': True}}, 'grant'))
_tmp = Path(tempfile.mkdtemp())
try:
    for _f in ('acorduri.html', 'legis_pagina.py', 'legis_clasifica.py', 'monitor_watch.py'):
        shutil.copy(AICI / _f, _tmp / _f)
    (_tmp / 'date').mkdir()
    json.dump([{'id': '9', 'c': 'OMDED182/2025', 'pub': '26-12-2025', 'kw': [],
                't': 'cu privire la intrarea în vigoare a Acordului de grant dintre Organizația pentru Dezvoltarea Antreprenoriatului și Agenția Executivă pentru Consiliul European pentru Inovare'},
               {'id': '8', 'c': 'LP115/2025', 'pub': '01-06-2025', 'kw': [], 't': 'pentru ratificarea Acordului de finanțare dintre Republica Moldova și Comisia Europeană pentru Programul Interreg Europe'},
               {'id': '7', 'c': 'LP155/2026', 'pub': '10-04-2026', 'kw': [], 't': 'pentru ratificarea Acordului de împrumut dintre Republica Moldova și Banca Europeană pentru Reconstrucție și Dezvoltare (Livada Moldovei II)'},
               {'id': '6', 'c': 'LP156/2026', 'pub': '10-04-2026', 'kw': [], 't': 'pentru ratificarea Acordului de împrumut dintre Republica Moldova și Banca Europeană de Investiții (Drumuri)'},
               {'id': '5', 'c': 'HG45/2009', 'pub': '27-01-2009', 'kw': [],
                't': 'privind inițierea negocierilor asupra proiectului Acordului de finanțare dintre Guvernul Republicii Moldova și Comisia Comunităților Europene pentru Proiectul „Evaluarea capacității și modernizarea Spitalului Clinic Republican din Chișinău”'}],
              open(_tmp / 'legis_brut.json', 'w', encoding='utf-8'))
    json.dump({'acte': {'9': {'act': 'OMDED182/2025', 'sume': [], 'atas': [{'u': 'u', 'suma': {'v': 22240300000368, 'val': 'EUR', 'f': 'cont'}, 'cost': None}]},
                        '8': {'act': 'LP115/2025', 'sume': [], 'atas': [{'u': 'u', 'suma': {'v': 493103338, 'val': 'EUR', 'f': 'buget'}, 'cost': None}]},
                        '7': {'act': 'LP155/2026', 'sume': [], 'atas': [{'u': 'u', 'suma': {'v': 150000000, 'val': 'EUR', 'f': 'împrumut'}, 'cost': {'v': 500000, 'val': 'EUR', 'f': 'prag studiu de fezabilitate'}}]},
                        '6': {'act': 'LP156/2026', 'sume': [], 'atas': [{'u': 'u', 'suma': {'v': 80000000, 'val': 'EUR', 'f': 'împrumut'}, 'cost': {'v': 120000000, 'val': 'EUR', 'f': 'costul proiectului'}}]}}},
              open(_tmp / 'date' / 'legis_sume.json', 'w', encoding='utf-8'))
    json.dump({'_nota': 'x', 'OMDED182/2025': {'v': 184297.33, 'val': 'EUR', 'nota': 'partea Moldovei'}, 'LP115/2025': {'ascunde': True},
               'LP155/2026': {'fara_cost': True, 'nota': 'pragul de 500 000 EUR nu e costul proiectului'},
               'HG45/2009': {'v': 3000000, 'val': 'EUR', 'u': 'https://eu4moldova.eu/projects/eu-project-page/?id=1365',
                             'nota': 'Pagina proiectului pe eu4moldova.eu', 'extern': True},
               'HG430/2026': {'v': 386910, 'val': 'USD', 'nota': 'Nota Cancelariei de Stat, document nepublicat online', 'extern': True}},
              open(_tmp / 'date' / 'sume_manual.json', 'w', encoding='utf-8'))
    # Un acord foarte nou: Monitorul îl are (hotărârea și ordinul), legis.md încă nu. Titlul nu spune dacă banii se
    # rambursează, deci regula automată dă „Asistență tehnică"; o notă oficială spune că e grant.
    _acord_nou = ('Acordului de colaborare dintre Instituția Publică Organizația pentru Dezvoltarea '
                  'Antreprenoriatului și Programul Națiunilor Unite pentru Dezvoltare pentru implementarea proiectului „Comunități reziliente prin abilitarea femeilor”')
    _t_hg = 'Hotărâre cu privire la aprobarea semnării ' + _acord_nou
    json.dump({'acte': {
        'nr. 430, 5 august 2026|3314': {'act': 'nr. 430, 5 august 2026', 'titlu': _t_hg, 'categorie': 'Asistență tehnică', 'partener': 'PNUD',
                                        'editie': '359-362', 'data_editie': '06.08.2026', 'editie_id': '3314', 'semnat': '', 'suport': False},
        'nr. 147, 24 august 2026|3327': {'act': 'nr. 147, 24 august 2026', 'categorie': 'Asistență tehnică', 'partener': 'PNUD',
                                         'titlu': 'Ordin cu privire la aducerea la cunoștința publică a datei intrării în vigoare a ' + _acord_nou,
                                         'editie': '407-409', 'data_editie': '02.09.2026', 'editie_id': '3327', 'semnat': '', 'suport': False}},
        'ultima_rulare': '10.10.2026'}, open(_tmp / 'date.json', 'w', encoding='utf-8'), ensure_ascii=False)
    # ordinul e dat sub codul întreg (OMDED147/2026), cum îl va avea în legis.md; decizia trebuie să-l prindă și sub codul provizoriu din Monitor
    _dec_t = {'categorie': 'Grant', 'motiv': 'nota spune „grant"', 'sursa': 'Nota CS-2684 din 15.07.2026 (document nepublicat)'}
    json.dump({'_nota': 'ignorat', 'HG430/2026': _dec_t, 'OMDED147/2026': _dec_t, 'HG999/2026': _dec_t},
              open(_tmp / 'date' / 'categorii_manual.json', 'w', encoding='utf-8'), ensure_ascii=False)
    _p = subprocess.run([sys.executable, str(_tmp / 'legis_pagina.py')], capture_output=True, text=True, timeout=120)
    _pag = (_tmp / 'legis_acorduri.html').read_text(encoding='utf-8') if (_tmp / 'legis_acorduri.html').exists() else ''
    _m = re.search(r'window\.__LEGIS__ = (\{.*?\});</script>', _pag, re.S)
    _a = {x['act']: x for x in json.loads(_m.group(1))['acte'].values()} if _m else {}
    verifica('suma pusă de mână (date/sume_manual.json) înlocuiește suma citită greșit',
             (_a.get('OMDED182/2025', {}).get('acord') or {}).get('v') == 184297.33, _p.stdout[-300:] + _p.stderr[-300:])
    verifica('„ascunde" scoate suma greșită din pagină', 'acord' not in _a.get('LP115/2025', {'acord': 1}))
    verifica('„fara_cost" scoate doar costul citit greșit, suma acordului rămâne',
             'cost' not in _a.get('LP155/2026', {'cost': 1}) and (_a.get('LP155/2026', {}).get('acord') or {}).get('v') == 150000000,
             str(_a.get('LP155/2026')))
    verifica('„extern" ajunge în pagină: suma are steagul și adresa sursei, nu o fișă legis.md',
             (_a.get('HG45/2009', {}).get('acord') or {}).get('extern') is True
             and (_a.get('HG45/2009', {}).get('acord') or {}).get('u') == 'https://eu4moldova.eu/projects/eu-project-page/?id=1365'
             and (_a.get('HG45/2009', {}).get('acord') or {}).get('v') == 3000000, str(_a.get('HG45/2009')))
    verifica('o sumă pusă de mână fără „extern" nu primește steagul',
             'extern' not in (_a.get('OMDED182/2025', {}).get('acord') or {'extern': 1}), str(_a.get('OMDED182/2025')))
    verifica('costul unui alt act, fără „fara_cost", nu se atinge',
             (_a.get('LP156/2026', {}).get('cost') or {}).get('v') == 120000000, str(_a.get('LP156/2026')))
    verifica('o sumă externă fără adresă (document nepublicat) rămâne fără adresă, nu trimite la fișa de pe legis.md',
             (_a.get('HG430/2026', {}).get('acord') or {}).get('u') == '' and (_a.get('HG430/2026', {}).get('acord') or {}).get('extern') is True
             and (_a.get('HG430/2026', {}).get('acord') or {}).get('v') == 386910, str(_a.get('HG430/2026')))
    verifica('o sumă pusă de mână, fără „extern" și fără adresă, trimite la fișa actului',
             str((_a.get('OMDED182/2025', {}).get('acord') or {}).get('u', '')).startswith('https://www.legis.md/'), str(_a.get('OMDED182/2025')))
    verifica('decizia de categorie se aplică și unui act venit doar din Monitor (fără fișă pe legis.md)',
             _a.get('HG430/2026', {}).get('categorie') == 'Grant' and (_a.get('HG430/2026', {}).get('decizie') or {}).get('sursa', '').startswith('Nota CS-2684'),
             str(_a.get('HG430/2026')))
    verifica('ordinul provizoriu din Monitor (O147/2026) primește decizia scrisă sub codul întreg (OMDED147/2026): acordul rămâne pe un rând',
             _a.get('O147/2026', {}).get('categorie') == 'Grant' and _a.get('HG430/2026', {}).get('categorie') == _a.get('O147/2026', {}).get('categorie'),
             str(_a.get('O147/2026')))
    verifica('un act fără decizie își păstrează categoria din titlu și nu primește „decizie"',
             'decizie' not in _a.get('LP156/2026', {'decizie': 1}) and _a.get('LP156/2026', {}).get('categorie') == 'Împrumut', str(_a.get('LP156/2026')))
    verifica('o decizie care nu mai corespunde niciunui act e spusă pe ecran',
             'HG999/2026' in _p.stdout and 'categorii_manual.json' in _p.stdout and 'HG430/2026' not in _p.stdout.split('HG999/2026')[0].split('ATENȚIE')[-1],
             _p.stdout[-400:])
finally:
    shutil.rmtree(_tmp, ignore_errors=True)

print()
print('Fișierele puse de mână din date/ — forma lor (o greșeală de tastare nu trebuie să strice registrul)')
_COD = re.compile(r'^[A-Z]{1,8}\d+/\d{4}$')
_VALUTE = {'EUR', 'USD', 'JPY', 'CHF', 'SEK', 'CAD', 'DKK', 'GBP', 'PLN', 'RON', 'CNY', 'CZK', 'DEM', 'ECU', 'ROL', 'DST', 'MDL'}
_sm = json.loads((AICI / 'date' / 'sume_manual.json').read_text(encoding='utf-8'))
_sm_rele = []
for _k, _v in _sm.items():
    if _k.startswith('_'):
        continue
    if not _COD.match(_k) or not isinstance(_v, dict):
        _sm_rele.append((_k, 'cheie sau valoare')); continue
    if _v.get('v') is not None and not (isinstance(_v['v'], (int, float)) and _v['v'] > 0 and _v.get('val', 'EUR') in _VALUTE):
        _sm_rele.append((_k, 'suma sau valuta'))
    if _v.get('extern'):
        if not _v.get('nota') or len(_v['nota']) > 220:
            _sm_rele.append((_k, 'nota lipsește sau trece de 220 de caractere (pagina o taie)'))
        if _v.get('u') and not str(_v['u']).startswith('https://'):
            _sm_rele.append((_k, 'adresa sursei nu începe cu https://'))
verifica('sume_manual.json: fiecare cheie e un cod de act, sumele sunt pozitive, în valute cunoscute; sursele externe au notă (≤ 220 de caractere) și adresă https',
         not _sm_rele, _sm_rele[:5])
_cm = json.loads((AICI / 'date' / 'contopiri_manual.json').read_text(encoding='utf-8'))
_cm_rele, _in_muta = [], {}
for _tip in ('muta', 'uneste'):
    for _i, _e in enumerate(_cm.get(_tip, [])):
        if not isinstance(_e.get('acte'), list) or not _e['acte'] or not all(_COD.match(str(c)) for c in _e['acte']):
            _cm_rele.append((_tip, _i, 'lista de acte')); continue
        if not str(_e.get('nota', '')).strip():
            _cm_rele.append((_tip, _i, 'fără notă (de ce se unește/mută)'))
        if _tip == 'muta':
            if _e.get('langa') is not None and not _COD.match(str(_e['langa'])):
                _cm_rele.append((_tip, _i, 'langa'))
            if _e.get('langa') in _e['acte']:
                _cm_rele.append((_tip, _i, 'un act nu poate fi mutat lângă el însuși'))
            for _c in _e['acte']:
                if _c in _in_muta:
                    _cm_rele.append((_tip, _i, 'actul %s e mutat de două ori (și în intrarea %d)' % (_c, _in_muta[_c])))
                _in_muta[_c] = _i
verifica('contopiri_manual.json: fiecare „muta"/„uneste" are lista de acte, o notă care spune de ce, și niciun act nu e mutat de două ori',
         not _cm_rele, _cm_rele[:5])

print()
print('Ordinele: cod provizoriu din Monitor, cod întreg în legis.md')
verifica('forma comună a codului unui ordin', pagina.forma_ordin('OMMPS147/2026') == 'O147/2026'
         and pagina.forma_ordin('O147/2026') == 'O147/2026' and pagina.forma_ordin('HG147/2026') is None)
_man = {'_cum_se_foloseste': 'text', 'OMMPS147/2026': {'v': 5, 'val': 'EUR'}, 'LP1/2026': {'v': 7}}
verifica('suma pusă sub codul întreg se aplică și actului cu cod provizoriu',
         pagina.manual_pentru('O147/2026', _man, {'O147/2026': 1})[0] == {'v': 5, 'val': 'EUR'})
verifica('suma pusă sub codul provizoriu rămâne valabilă când actul primește codul întreg',
         pagina.manual_pentru('OMMPS147/2026', {'O147/2026': {'v': 9}}, {'O147/2026': 1}) == ({'v': 9}, 'O147/2026'))
verifica('două ordine cu același număr și an: nicio ghicire',
         pagina.manual_pentru('O147/2026', _man, {'O147/2026': 2}) == (None, None)
         and pagina.manual_pentru('OMF147/2026', {'O147/2026': {'v': 9}, 'OMS147/2026': {'v': 1}}, {'O147/2026': 1}) == (None, None))
verifica('cheia exactă bate orice altceva; legile și hotărârile nu au altă formă',
         pagina.manual_pentru('LP1/2026', _man, {})[1] == 'LP1/2026' and pagina.manual_pentru('LP2/2026', _man, {}) == (None, None))
with tempfile.TemporaryDirectory() as _d:
    _mo = {'acte': {
        'nr. 73, 16 martie 2026|3400': {'act': 'nr. 73, 16 martie 2026', 'editie': '100-101', 'data_editie': '20.03.2026', 'editie_id': '3400',
            'titlu': 'Ordin cu privire la intrarea în vigoare a Acordului de grant dintre Ministerul Sănătății și Agenția Franceză de Dezvoltare'},
        'nr. 74, 16 martie 2026|3400': {'act': 'nr. 74, 16 martie 2026', 'editie': '100-101', 'data_editie': '20.03.2026', 'editie_id': '3400',
            'titlu': 'Ordin cu privire la intrarea în vigoare a Contractului de asistență tehnică dintre Ministerul Muncii și Programul Alimentar Mondial'}}}
    json.dump(_mo, open(Path(_d) / 'mo.json', 'w', encoding='utf-8'), ensure_ascii=False)
    _acte, _ids = {}, {'OMMPS73/2026': '1', 'OMMPS74/2026': '2'}
    _tit = {'OMMPS73/2026': 'cu privire la aprobarea Regulamentului privind organizarea concursului pentru ocuparea funcțiilor vacante',
            'OMMPS74/2026': 'cu privire la intrarea în vigoare a Contractului de asistență tehnică dintre Ministerul Muncii și Programul Alimentar Mondial'}
    _n = pagina.adauga_din_monitor(_acte, _ids, Path(_d) / 'mo.json', titluri=_tit)
verifica('ordinul altui minister cu același număr nu ține locul celui din Monitor; același ordin nu se dublează',
         _n == 1 and [a['act'] for a in _acte.values()] == ['O73/2026'], (_n, list(_acte)))

print()
print('Notele Guvernului (gov_sume.py)')
import gov_sume as gs
verifica('titlul punctului devine titlul hotărârii',
         gs.curata_titlu('(HG-PL) – Proiect de hotărâre a Guvernului cu privire la aprobarea proiectului de lege pentru ratificarea '
                         'Acordului de împrumut (număr unic 664/MIDR/2026) UE')
         == 'Hotărâre cu privire la aprobarea proiectului de lege pentru ratificarea Acordului de împrumut')
_pag = ('<a href="/sites/default/files/media/documents/sedinte-de-guvern/2026-07/30-Actele.pdf">Actele adoptate</a>'
        '<table><tr><td>1.</td><td>Cu privire la resursele umane</td></tr>'
        '<tr><td>2.</td><td><a href="/sites/default/files/media/documents/sedinte-de-guvern/2026-07/NU-301-MEC-2026.pdf">'
        '(HG) – Proiect de hotărâre a Guvernului cu privire la aprobarea semnării Acordului de împrumut (număr unic 301/MEC/2026)</a></td></tr></table>')
_p = gs.puncte_din_pagina(_pag, 'https://gov.md/ro/sedinte-de-guvern/sedinta-guvernului-din-22-iulie-2026-ora-1300')
verifica('ordinea de zi: doar punctele cu număr unic și PDF', len(_p) == 1 and _p[0][1] == '301/MEC/2026'
         and _p[0][2].endswith('NU-301-MEC-2026.pdf'), _p)
_s = gs.sedinte_din_lista('<a href="/ro/sedinte-de-guvern/sedinta-guvernului-din-22-iulie-2026-ora-1300">x</a>'
                          '<a href="https://gov.md/ro/sedinte-de-guvern/sedinta-guvernului-din-7-ianuarie-2025-ora-1000">y</a>')
verifica('lista ședințelor, cu data din adresă', [x[1] for x in _s] == ['2026-07-22', '2025-01-07'], _s)
verifica('modificările se recunosc (suma lor nu e a acordului)',
         bool(gs.RX_MODIFICARE.search('ratificarea Scrisorii de modificare la Acordul de împrumut'))
         and not gs.RX_MODIFICARE.search('aprobarea semnării Acordului de împrumut'))
_azi = datetime.date(2026, 10, 7)
verifica('ședința recentă sau viitoare se recitește (ordinea de zi se mai completează); cea veche, nu',
         gs.e_recenta('2026-10-08', _azi) and gs.e_recenta('2026-09-28', _azi)
         and not gs.e_recenta('2026-09-20', _azi) and not gs.e_recenta('', _azi))
_n = {}
verifica('nota care nu se poate descărca rămâne de reîncercat, nu cu sumă',
         not gs.citeste_nota(_n, None, ls.sume_din_text, ls.text_din_pdf) and _n == {'eroare': 'PDF indisponibil'}
         and not gs.citeste_nota(_n, b'<html>eroare</html>', ls.sume_din_text, ls.text_din_pdf))

print()
print('Lista acordurilor pentru „De la lege la bani” (legatura_acorduri.py)')
import legatura_acorduri as lga
_ac = lambda i, suma=True: {'id': 'a%d' % i, 'nume': 'Acord %d' % i, 'suma': {'v': 1, 'val': 'EUR', 'eur': 1} if suma else None}
_bune = [_ac(i) for i in range(300)]
verifica('o citire bună trece', lga.valideaza(_bune) == [], lga.valideaza(_bune))
verifica('prea puține acorduri: pagina nu și-a încărcat datele', any('nu și-a încărcat' in x for x in lga.valideaza(_bune[:50])))
verifica('id-uri care se repetă se refuză', any('se repetă' in x for x in lga.valideaza(_bune[:250] + [_ac(1)])))
verifica('un acord fără denumire se refuză', any('fără id sau fără denumire' in x for x in lga.valideaza(_bune[:250] + [{'id': 'x', 'nume': ''}])))
_fara_suma = [_ac(i, suma=(i < 30)) for i in range(300)]
verifica('sumele care nu s-au încărcat (10% cu sumă) se refuză', any('sumele nu s-au încărcat' in x for x in lga.valideaza(_fara_suma)))
verifica('scăderea bruscă a numărului de acorduri față de fișierul de acum se refuză', any('față de' in x for x in lga.valideaza(_bune[:230], _bune)))
verifica('scăderea bruscă a acordurilor cu sumă față de fișierul de acum se refuză',
         any('cu sumă față de' in x for x in lga.valideaza([_ac(i, suma=(i < 100)) for i in range(300)], _bune)))
_nou = lga.continut(_bune[:3], '1 iulie 2026', '2026-10-07 10:00')
_text = lga.text_json(_nou)
verifica('fișierul scris e JSON valid și se citește înapoi la fel', json.loads(_text) == _nou, _text[:120])
verifica('un acord pe linie', _text.count('\n') == 3 + 2 and _text.startswith('{"actualizat"'), _text.count('\n'))
verifica('data scrierii nu schimbă conținutul', lga.fara_data(_nou) == lga.fara_data(lga.continut(_bune[:3], '1 iulie 2026', '2026-10-08 09:00')))
_real = json.load(open(AICI / 'date' / 'acorduri_legare.json', encoding='utf-8'))
verifica('fișierul din repository e coerent: numărul scris = numărul real, fără probleme de validare',
         _real['numar'] == len(_real['acorduri']) and lga.valideaza(_real['acorduri']) == [], lga.valideaza(_real['acorduri']))
_conf = json.load(open(AICI / 'date' / 'legaturi_amp.json', encoding='utf-8'))
verifica('date/legaturi_amp.json are cele trei liste așteptate de pagină',
         isinstance(_conf.get('confirmate'), dict) and isinstance(_conf.get('respinse'), dict) and isinstance(_conf.get('fara_proiect'), list))
_ids = {a['id'] for a in _real['acorduri']}
_orfane = [k for k in list(_conf['confirmate']) + list(_conf['respinse']) + list(_conf['fara_proiect']) if k not in _ids]
verifica('nicio confirmare din legaturi_amp.json nu are un id de acord care nu mai există', _orfane == [], _orfane)

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
    print('Browser, pe registrul real: lista acordurilor (legatura_acorduri.py)')
    _lista, _curs = lga.citeste_acorduri()
    verifica('pagina de registru își dă lista de acorduri', len(_lista) >= lga.MINIM_ACORDURI, len(_lista))
    verifica('lista trece validarea și are cursul trecut', lga.valideaza(_lista) == [] and bool(_curs), (lga.valideaza(_lista), _curs))
    verifica('fiecare acord are acte, și aproape toate au partener (în registru e un act cu titlul „ACORD DE FINANȚARE*", fără finanțator)',
             all(a['acte'] for a in _lista) and sum(1 for a in _lista if a['parteneri']) >= 0.99 * len(_lista))
    _cu_eur = [a for a in _lista if a['suma'] and a['suma']['eur']]
    verifica('sumele în euro sunt numere pozitive', _cu_eur and all(a['suma']['eur'] > 0 for a in _cu_eur))
    verifica('lista scoasă acum are același număr de acorduri ca fișierul din repository', len(_lista) == _real['numar'], (len(_lista), _real['numar']))

    print()
    print('Browser, registrul din Monitorul Oficial: preia sumele deja citite pe legis.md (acorduri.html)')
    _mon, _ = lga.citeste_acorduri(pagina='acorduri.html')
    _dupa_nume = lambda n: next((a for a in _mon if a['nume'].strip().lower().startswith(n.lower())), None)
    verifica('registrul Monitor are sume la majoritatea acordurilor (înainte aveau doar o doime: 24 din 98)',
             sum(1 for a in _mon if a['suma']) >= 0.6 * len(_mon), (sum(1 for a in _mon if a['suma']), len(_mon)))
    _scoli = _dupa_nume('Reabilitarea și modernizarea școlilor din Moldova')
    verifica('suma citită din acordul atașat (legis.md) apare și în registrul Monitor: școlile = 40 000 000 EUR',
             _scoli and _scoli['suma'] and _scoli['suma']['eur'] == 40000000, _scoli and _scoli['suma'])
    _livada = _dupa_nume('Livada Moldovei II')
    verifica('Livada Moldovei II = 150 000 000 EUR (suma acordului), nu pragul de 500 000 EUR citit ca „cost"',
             _livada and _livada['suma'] and _livada['suma']['eur'] == 150000000 and not _livada['cost'], _livada and (_livada['suma'], _livada['cost']))
    _urbact = [a for a in _mon if 'urbact' in json.dumps(a, ensure_ascii=False).lower()]
    verifica('suma de program a URBACT (86,8 mil. EUR pentru toate țările) nu e atribuită Moldovei',
             bool(_urbact) and all(not a['suma'] or a['suma']['eur'] != 86769799 for a in _urbact), [a['suma'] for a in _urbact])

    print()
    print('Browser: exportul Excel din registru — stilizat, cu totalul din pagină, filtre, linkuri și rezerva fără xlsx-stil.js')
    import zipfile, xml.dom.minidom, functools, html as _html, datetime as _dt
    import openpyxl
    from playwright.sync_api import sync_playwright

    ANTET_ACORDURI = ['Acordul', 'Partener', 'Tip de finanțare', 'Suport bugetar', 'Suma', 'Valuta', 'Echivalent EUR', 'Intră în total?', 'Semnat',
                      'Etape parcurse (din 5)', 'Etapa atinsă', '1. Inițiere negocieri', '2. Aprobare semnare', '3. Aprobare proiect de lege',
                      '4. Ratificare sau aprobare', '5. Decret de promulgare', 'În vigoare din', 'Temeiul datei', 'Ani', 'Nr. acte', 'Prima publicare',
                      'Ultima publicare', 'Sursa sumei', 'Fragmentul din act', 'Link sursă', 'Costul total al proiectului', 'Valuta costului',
                      'Denumirea completă', 'Link în registru']
    ANTET_ACTE = ['Data ediției', 'Ediția', 'Act', 'Tip de finanțare', 'Suport bugetar', 'Partener', 'Etapa', 'Denumirea acordului',
                  'Titlul complet al actului', 'Semnat', 'Link']

    def _eur_pagina(text):
        """„11,85 mld. EUR" → (valoarea, cât poate fi de departe de cifra reală din cauza rotunjirii afișate)."""
        m = re.search(r'([\d,]+)\s*(mld\.|mil\.|mii)?\s*EUR', text)
        n = float(m.group(1).replace(',', '.'))
        u = {'mld.': 1e9, 'mil.': 1e6, 'mii': 1e3, None: 1}[m.group(2)]
        zec = len(m.group(1).split(',')[1]) if ',' in m.group(1) else 0
        return n * u, 0.5 * u * 10 ** (-zec) + 1

    def _tabel(cale, foaie, rand_antet=5):
        """Rândurile de date ale unei foi (de sub antet până la rândul „Total" sau până la primul rând gol), ca dicționare după antet."""
        ws = openpyxl.load_workbook(cale)[foaie]
        antet = [c.value for c in ws[rand_antet]]
        rez = []
        for r in range(rand_antet + 1, ws.max_row + 1):
            v = [c.value for c in ws[r]]
            if v[0] is None or (isinstance(v[0], str) and v[0].startswith('Total')):
                break
            rez.append(dict(zip(antet, v)))
        return antet, rez, ws

    def _descarca(pg, cale):
        with pg.expect_download(timeout=60000) as d:
            pg.click('#export')
        d.value.save_as(str(cale))
        return d.value.suggested_filename

    def _asteapta_pagina(pg):
        """Lista e în pagină, iar sumele (fișiere separate, aduse după încărcare) au sosit și s-au așezat: două citiri la fel la rând.
        Panoul „Sumele acordurilor" există doar pe legis.md, de aceea semnătura se bazează pe datele paginii (window.__ACORDURI__)."""
        pg.wait_for_function("() => (window.__GRUPURI__ || []).length > 50", timeout=60000)
        ant, la_fel = None, 0
        for _ in range(60):
            pg.wait_for_timeout(500)
            cur = pg.evaluate('''() => {
                const A = window.__ACORDURI__ ? window.__ACORDURI__() : [];
                const p = document.querySelector('#sume .sume-total');
                return (p ? p.innerText : '-') + '|' + A.length + '|' + A.reduce((s, a) => s + (a.suma ? (a.suma.eur || 0) : 0), 0)
                       + '|' + A.reduce((s, a) => s + a.acte.length, 0);
            }''')
            la_fel = la_fel + 1 if cur == ant else 0
            if la_fel >= 2:
                return
            ant = cur

    _dir = Path(tempfile.mkdtemp(prefix='reg_xlsx_'))
    _srv = lga._Server(('127.0.0.1', 0), functools.partial(lga._Liniste, directory=str(AICI)))
    threading.Thread(target=_srv.serve_forever, daemon=True).start()
    _baza = 'http://127.0.0.1:%d/' % _srv.server_address[1]
    try:
        with sync_playwright() as _p:
            _b = _p.chromium.launch()
            for _pagina in ('legis_acorduri.html', 'acorduri.html'):
                _nume = _pagina.split('.')[0]
                _pg = _b.new_page()
                _erori = []
                _pg.on('pageerror', lambda e: _erori.append(str(e)[:200]))
                _pg.route('**/*', lambda r: r.continue_() if r.request.url.startswith(_baza) else r.abort())
                _pg.goto(_baza + _pagina, wait_until='networkidle', timeout=90000)
                _asteapta_pagina(_pg)                # sumele sosesc pe rând (fișiere separate): așteptăm până se oprește redesenarea
                _panou = _pg.evaluate("() => !!document.querySelector('#sume')")
                verifica(_nume + ': panoul „Sumele acordurilor" există doar în registrul legis.md (la Monitor totalul se verifică după datele paginii)',
                         _panou == (_nume == 'legis_acorduri'), _panou)
                _info = _pg.evaluate('''() => {
                    const g = window.__GRUPURI__ || [];
                    const p = document.querySelector('#sume .sume-total');
                    return {grupuri: g.length, acte: g.reduce((s, x) => s + x.acte.length, 0), text: p ? p.innerText : '',
                            total: p && p.querySelector('b') ? p.querySelector('b').innerText : ''};
                }''')
                if _panou:
                    _tot_pag, _toler = _eur_pagina(_info['total'])
                    _m = re.search(r'(\d+)\s+(?:de\s+)?acord\w*\s+din\s+(\d+)', _info['text'])
                    _in_total_pag, _din_pag = (int(_m.group(1)), int(_m.group(2))) if _m else (-1, -1)
                else:
                    _tot_pag = _toler = _in_total_pag = _din_pag = None
                _A = _pg.evaluate('() => window.__ACORDURI__()')

                # ---- 1. vederea „Acorduri", fără filtre
                _f1 = _dir / (_nume + '-acorduri.xlsx')
                _nf = _descarca(_pg, _f1)
                verifica(_nume + ': fișierul se numește registru-acorduri-<data>.xlsx', re.fullmatch(r'registru-acorduri-\d{4}-\d\d-\d\d\.xlsx', _nf) is not None, _nf)
                _z = zipfile.ZipFile(_f1)
                _rele = []
                for _n in _z.namelist():
                    try:
                        xml.dom.minidom.parseString(_z.read(_n))
                    except Exception:
                        _rele.append(_n)
                verifica(_nume + ': toate părțile fișierului sunt XML valid', not _rele, _rele)
                verifica(_nume + ': stilurile și șirurile sunt părți ale fișierului, iar legăturile externe au relații',
                         {'xl/styles.xml', 'xl/sharedStrings.xml', 'xl/worksheets/_rels/sheet1.xml.rels'} <= set(_z.namelist()))
                _wb = openpyxl.load_workbook(_f1)
                verifica(_nume + ': trei foi — Acorduri, Sume pe tipuri, Pe valute', _wb.sheetnames == ['Acorduri', 'Sume pe tipuri', 'Pe valute'], _wb.sheetnames)
                _antet, _rand, _ws = _tabel(_f1, 'Acorduri')
                verifica(_nume + ': antetul are cele 29 de coloane, în ordinea hotărâtă', _antet == ANTET_ACORDURI, [(a, b) for a, b in zip(_antet, ANTET_ACORDURI) if a != b])
                verifica(_nume + ': un rând pe acord, cât în pagină (%d)' % _info['grupuri'], len(_rand) == _info['grupuri'] > 50, (len(_rand), _info['grupuri']))
                _suma_eur = sum(r['Echivalent EUR'] for r in _rand if isinstance(r['Echivalent EUR'], (int, float)))
                _da = sum(1 for r in _rand if r['Intră în total?'] == 'da')
                if _panou:
                    verifica(_nume + ': totalul în euro din coloană = totalul din panoul paginii (%s)' % _info['total'], abs(_suma_eur - _tot_pag) <= _toler, (_suma_eur, _tot_pag, _toler))
                    verifica(_nume + ': numărul rândurilor „da" = numărul din pagină (%d din %d)' % (_in_total_pag, _din_pag), _da == _in_total_pag and len(_rand) == _din_pag, (_da, _in_total_pag, len(_rand), _din_pag))
                    # tranșele aceluiași program nu sunt dubluri: grantul sectorial japonez a avut câte un schimb de scrisori pe an,
                    # trei dintre ele de câte 300 mil. yeni (aceeași sumă, aceleași cuvinte în denumire, numai tranșa le deosebește)
                    _sec = [r for r in _rand if 'ajustările structurale economice' in (r['Denumirea completă'] or '') and 'Japoniei' in (r['Denumirea completă'] or '')]
                    verifica(_nume + ': granturile sectoriale japoneze (patru tranșe, trei de câte 300 mil. yeni) sunt patru rânduri, toate numărate în total',
                             len(_sec) == 4 and all(r['Intră în total?'] == 'da' for r in _sec) and sorted(r['Suma'] for r in _sec) == [300000000, 300000000, 300000000, 400000000],
                             [(r['Acordul'][:40], r['Suma'], r['Intră în total?']) for r in _sec])
                    # coroanele cehe au curs (BCE, 1 iulie 2026): fără el, rândul ar fi rămas „nu: fără curs", în afara totalului
                    _rst = [r for r in _rand if 'RESTART' in (r['Denumirea completă'] or '')]
                    verifica(_nume + ': proiectul ceh RESTART (22 902 012,92 CZK) e un singur rând, numărat în total, cu echivalentul în euro la cursul BCE',
                             len(_rst) == 1 and _rst[0]['Valuta'] == 'CZK' and _rst[0]['Intră în total?'] == 'da' and abs(_rst[0]['Suma'] - 22902012.92) < 0.01
                             and abs(_rst[0]['Echivalent EUR'] - 22902012.92 / 24.254) <= 0.5 + 1e-6,
                             [(r['Acordul'][:40], r['Suma'], r['Valuta'], r['Echivalent EUR'], r['Intră în total?']) for r in _rst])
                # pe ambele pagini: rând cu rând, cifrele din fișier sunt cele din datele paginii (window.__ACORDURI__)
                _gresite = []
                for _i, (_r, _a) in enumerate(zip(_rand, _A)):
                    _s = _a['suma']
                    _bun = (_r['Acordul'] == _a['scurt'] and _r['Denumirea completă'] == _a['nume']
                            and (_r['Suma'], _r['Valuta']) == ((_s['v'], _s['val']) if _s else (None, None))
                            and (_r['Echivalent EUR'] is None or (_s and _s['eur'] is not None and abs(_r['Echivalent EUR'] - _s['eur']) <= 0.5 + 1e-6))
                            and (_a['faraTotal'] == (_r['Intră în total?'] == 'nu: nu se adună')))
                    if not _bun:
                        _gresite.append((_i, _r['Acordul'][:30], _r['Suma'], _r['Valuta'], _r['Echivalent EUR'], _r['Intră în total?'], _s))
                verifica(_nume + ': rând cu rând, numele, suma, valuta, echivalentul EUR și „nu se adună" coincid cu datele paginii', len(_A) == len(_rand) and not _gresite, _gresite[:3])
                _tot_date = sum(a['suma']['eur'] for r, a in zip(_rand, _A) if r['Intră în total?'] == 'da')
                verifica(_nume + ': totalul în euro din coloană = suma echivalentelor din datele paginii, pe rândurile „da"', abs(_suma_eur - _tot_date) <= 0.5 * _da + 1 and _da > 20, (_suma_eur, _tot_date, _da))
                _motive = {r['Intră în total?'] for r in _rand} - {None}
                verifica(_nume + ': motivele pentru care un rând nu intră în total sunt cele cunoscute', _motive <= {'da', 'nu: dublură', 'nu: nu se adună', 'nu: fără curs'}, _motive)
                verifica(_nume + ': rândurile care nu intră în total nu au echivalent EUR, cele care intră îl au',
                         all((r['Echivalent EUR'] is not None) == (r['Intră în total?'] == 'da') for r in _rand), [r['Acordul'] for r in _rand if (r['Echivalent EUR'] is not None) != (r['Intră în total?'] == 'da')][:3])
                verifica(_nume + ': orice rând cu sumă are și valută, și o stare față de total; fără sumă — nici una',
                         all((r['Suma'] is not None) == (r['Valuta'] is not None) == (r['Intră în total?'] is not None) for r in _rand), [r['Acordul'] for r in _rand if (r['Suma'] is None) != (r['Intră în total?'] is None)][:3])
                verifica(_nume + ': sumele și numărul de acte sunt numere, datele sunt date adevărate (se sortează), marcajele sunt „da"',
                         all(r['Suma'] is None or isinstance(r['Suma'], (int, float)) for r in _rand)
                         and all(isinstance(r['Nr. acte'], int) and r['Nr. acte'] >= 1 for r in _rand)
                         and all(r['Prima publicare'] is None or isinstance(r['Prima publicare'], _dt.datetime) for r in _rand)
                         and all(r['Semnat'] is None or isinstance(r['Semnat'], _dt.datetime) for r in _rand)
                         and all(r['Suport bugetar'] in (None, 'da') for r in _rand) and all(r['1. Inițiere negocieri'] in (None, 'da') for r in _rand),
                         [(r['Acordul'][:30], r['Prima publicare'], r['Semnat']) for r in _rand[:2]])
                verifica(_nume + ': „Etape parcurse" e un număr de la 0 la 5, egal cu numărul etapelor bifate',
                         all(isinstance(r['Etape parcurse (din 5)'], int) and 0 <= r['Etape parcurse (din 5)'] <= 5
                             and r['Etape parcurse (din 5)'] == sum(1 for k in ANTET_ACORDURI[11:16] if r[k] == 'da') for r in _rand), [r['Acordul'][:30] for r in _rand[:2]])
                _ultim = 6 + len(_rand) - 1
                verifica(_nume + ': antetul și prima coloană rămân pe loc la derulare (B6), cu filtre pe toată lista', _ws.freeze_panes == 'B6' and _ws.auto_filter.ref == 'A5:AC%d' % _ultim, (_ws.freeze_panes, _ws.auto_filter.ref))
                verifica(_nume + ': titlul e în banda albastră închisă, antetul albastru cu text alb, grupele de coloane deasupra',
                         _ws['A1'].fill.fgColor.rgb == 'FF14233C' and _ws['A5'].fill.fgColor.rgb == 'FF1E4B8C' and _ws['A5'].font.color.rgb == 'FFFFFFFF'
                         and [_ws[c + '4'].value for c in ('A', 'E', 'I', 'S', 'W')] == ['ACORD', 'SUMA ȘI TOTALUL', 'PARCURSUL ACORDULUI', 'ACTELE PUBLICATE', 'SURSE ȘI DETALII'],
                         [_ws[c + '4'].value for c in ('A', 'E', 'I', 'S', 'W')])
                _sub = _ws['A2'].value
                verifica(_nume + ': rândul de context spune sursa, lipsa filtrelor, numărul de acorduri și data', _sub.startswith('Sursa: ') and 'fără filtre' in _sub and ('%d de acorduri' % _info['grupuri']) in _sub.replace(' %d acorduri' % _info['grupuri'], ' %d de acorduri' % _info['grupuri']) and 'Generat: ' in _sub and 'cursul BCE din 1 iulie 2026' in _sub, _sub)
                verifica(_nume + ': sursa din antet e cea a paginii', ('legis.md' in _sub) == (_nume == 'legis_acorduri') and ('monitorul.gov.md' in _sub) == (_nume == 'acorduri'), _sub[:120])
                _reguli = {}
                for _rng in _ws.conditional_formatting:
                    for _r in _rng.rules:
                        _reguli.setdefault(str(_rng.sqref), []).append(_r)
                verifica(_nume + ': culori pe „Tip de finanțare" (4 tipuri) și pe „Intră în total?" (da / 3 motive de excludere)',
                         len(_reguli.get('C6:C%d' % _ultim, [])) == 4 and len(_reguli.get('H6:H%d' % _ultim, [])) == 4, {k: len(v) for k, v in _reguli.items()})
                _total_f = [c.value for c in _ws[_ultim + 1]]
                verifica(_nume + ': rândul de total adună coloana „Echivalent EUR" cu SUBTOTAL (se recalculează la filtrare)', _total_f[0] == 'Total (rândurile vizibile)' and _total_f[6] == '=SUBTOTAL(109,G6:G%d)' % _ultim, _total_f[:7])
                _wbv = openpyxl.load_workbook(_f1, data_only=True)
                _cache = _wbv['Acorduri'].cell(row=_ultim + 1, column=7).value
                verifica(_nume + ': valoarea calculată a totalului e trecută în fișier (se vede și fără recalculare)', _cache is not None and abs(_cache - _suma_eur) < 1, (_cache, _suma_eur))
                # foile cu cifrele pe tipuri și pe valute
                _a2, _r2, _w2 = _tabel(_f1, 'Sume pe tipuri', 4)
                _a3, _r3, _w3 = _tabel(_f1, 'Pe valute', 4)
                _t2 = sum(r['Echivalent EUR'] for r in _r2)
                _t3 = sum(r['Echivalent EUR'] for r in _r3)
                verifica(_nume + ': „Sume pe tipuri" are aceleași cifre ca ' + ('panoul din pagină' if _panou else 'coloana „Echivalent EUR"') + ': același total, același număr de acorduri cu sumă',
                         abs(_t2 - _suma_eur) < 1 and (not _panou or abs(_t2 - _tot_pag) <= _toler) and sum(r['Din care cu sumă (în total)'] for r in _r2) == _da, (_t2, _suma_eur, _tot_pag, _da))
                verifica(_nume + ': subtitlul foii „Sume pe tipuri" trimite la panoul din pagină doar acolo unde panoul există', ('panoul' in (_w2['A2'].value or '')) == _panou, _w2['A2'].value)
                verifica(_nume + ': „Pe valute" adună același total ca „Sume pe tipuri", iar cursurile sunt cele din pagină',
                         abs(_t3 - _t2) < 1 and sum(r['Acorduri'] for r in _r3) == _da and any(r['Valuta'] == 'EUR' and r['Unități pentru 1 EUR'] == 1 for r in _r3)
                         and all(r['Unități pentru 1 EUR'] > 0 for r in _r3), (_t3, _t2))
                verifica(_nume + ': „Sume pe tipuri" are un grafic cu bare', any('chart' in n for n in _z.namelist()) and _w2.freeze_panes == 'A5')
                verifica(_nume + ': pondere pe tipuri — suma ponderilor = 100%', abs(sum(r['Pondere din total'] for r in _r2) - 1) < 1e-9, [r['Pondere din total'] for r in _r2])
                # linkuri
                _leg_reg = [_ws.cell(row=r, column=29).hyperlink for r in range(6, _ultim + 1)]
                verifica(_nume + ': fiecare rând are „Link în registru", un link spre acordul din pagină (#acord=…)', all(h is not None and '#acord=' in h.target for h in _leg_reg) and _leg_reg[0].target.startswith(_baza + _pagina), (_leg_reg[0].target if _leg_reg[0] else None))
                _cu_sursa = [r for r in range(6, _ultim + 1) if _ws.cell(row=r, column=25).value]
                verifica(_nume + ': „Link sursă" e hyperlink doar unde există sursă, spre o adresă http(s), cu gazda ca text',
                         len(_cu_sursa) > 5 and all(_ws.cell(row=r, column=25).hyperlink and re.match(r'https?://', _ws.cell(row=r, column=25).hyperlink.target)
                                                     and _ws.cell(row=r, column=25).hyperlink.target.split('/')[2].replace('www.', '') == _ws.cell(row=r, column=25).value for r in _cu_sursa)
                         and all(_ws.cell(row=r, column=25).hyperlink is None for r in range(6, _ultim + 1) if r not in _cu_sursa), len(_cu_sursa))
                _ext = [r for r in _rand if r['Sursa sumei'] == 'sursă externă (nu din actele din registru)']
                verifica(_nume + ': sumele din surse externe sunt marcate „sursă externă (nu din actele din registru)"', len(_ext) >= 3 and all(r['Suma'] for r in _ext), len(_ext))
                verifica(_nume + ': pagina nu a dat erori JavaScript', not _erori, _erori)

                # ---- 2. filtrat: tip „Grant" + căutare „berd"
                _pg.fill('#seek', 'berd')
                _pg.wait_for_timeout(700)
                _pg.click('#catBtns button[data-cat="Grant"]')
                _pg.wait_for_timeout(900)
                _vizibile = _pg.evaluate("() => document.querySelectorAll('tr.acord').length")
                _f2 = _dir / (_nume + '-filtrat.xlsx')
                _nf2 = _descarca(_pg, _f2)
                _a4, _r4, _w4 = _tabel(_f2, 'Acorduri')
                verifica(_nume + ': exportul filtrat are exact rândurile de pe ecran (%d)' % _vizibile, 0 < len(_r4) == _vizibile, (len(_r4), _vizibile))
                verifica(_nume + ': toate rândurile filtrate sunt „Grant" cu BERD', all(r['Tip de finanțare'] == 'Grant' and 'BERD' in (r['Partener'] or '') for r in _r4), {(r['Tip de finanțare'], r['Partener']) for r in _r4})
                _sub2 = _w4['A2'].value
                verifica(_nume + ': contextul spune filtrele active (tip: Grant; căutare: berd), iar numele fișierului — tipul', 'tip: Grant' in _sub2 and 'căutare: berd' in _sub2 and 'fără filtre' not in _sub2 and '-grant-' in _nf2, (_sub2[:160], _nf2))
                _wb4 = openpyxl.load_workbook(_f2)
                _a5, _r5, _w5 = _tabel(_f2, 'Sume pe tipuri', 4)
                verifica(_nume + ': foaia „Sume pe tipuri" arată doar tipul filtrat, cu totalul rândurilor exportate',
                         [r['Tip de finanțare'] for r in _r5] == ['Grant'] and abs(_r5[0]['Echivalent EUR'] - sum(r['Echivalent EUR'] for r in _r4 if isinstance(r['Echivalent EUR'], (int, float)))) < 1
                         and _r5[0]['Acorduri în selecție'] == len(_r4), (_r5, len(_r4)))
                _pg.fill('#seek', '')
                _pg.click('#catBtns button[data-cat="all"]')
                _pg.wait_for_timeout(500)
                # o căutare fără rezultat: fișier valid, doar cu antetul și o notă
                _pg.fill('#seek', 'zzzzqqqq')
                _pg.wait_for_timeout(600)
                _f2b = _dir / (_nume + '-gol.xlsx')
                _descarca(_pg, _f2b)
                _wbg = openpyxl.load_workbook(_f2b)
                verifica(_nume + ': căutarea fără rezultate dă un fișier valid, cu antetul și fără foile de sume', _wbg.sheetnames == ['Acorduri'] and _wbg['Acorduri']['A5'].value == 'Acordul' and 'niciun acord' in _wbg['Acorduri']['A2'].value, (_wbg.sheetnames, _wbg['Acorduri']['A2'].value))
                _pg.fill('#seek', '')
                _pg.wait_for_timeout(400)

                # ---- 3. vederea „Acte"
                _pg.click('#vedBtns [data-ved="acte"]')
                _pg.wait_for_timeout(600)
                _f3 = _dir / (_nume + '-acte.xlsx')
                _nf3 = _descarca(_pg, _f3)
                _wb3 = openpyxl.load_workbook(_f3)
                _a6, _r6, _w6 = _tabel(_f3, 'Acte')
                verifica(_nume + ': vederea „Acte" — o singură foaie, „Acte", cu cele 11 coloane', _wb3.sheetnames == ['Acte'] and _a6 == ANTET_ACTE and _nf3.startswith('registru-acte-'), (_wb3.sheetnames, _a6, _nf3))
                verifica(_nume + ': un rând pe act, cât în registru (%d)' % _info['acte'], len(_r6) == _info['acte'] > 300, (len(_r6), _info['acte']))
                _date = [r['Data ediției'] for r in _r6]
                verifica(_nume + ': datele sunt date adevărate, în ordinea publicării (cele mai noi primele)', all(isinstance(d, _dt.datetime) for d in _date) and _date == sorted(_date, reverse=True), _date[:3])
                _leg = [(_w6.cell(row=r, column=11).value, _w6.cell(row=r, column=11).hyperlink) for r in range(6, 6 + len(_r6))]
                verifica(_nume + ': „Link" e hyperlink pe fiecare act care are adresă, spre http(s), cu gazda ca text',
                         sum(1 for t, h in _leg if h) > 300 and all((h is None) == (not t) for t, h in _leg)
                         and all(re.match(r'https?://', h.target) and h.target.split('/')[2].replace('www.', '') == t for t, h in _leg if h), sum(1 for t, h in _leg if h))
                verifica(_nume + ': „Ediția" nu are prefixul dublat („MO MO") și, la Monitor, începe cu „MO "', not any('MO MO' in (r['Ediția'] or '') for r in _r6) and (_nume == 'legis_acorduri' or all((r['Ediția'] or '').startswith('MO ') for r in _r6)), [r['Ediția'] for r in _r6[:3]])
                verifica(_nume + ': prima coloană din fiecare rând (data) și identificatorul actului rămân pe loc la derulare (D6)', _w6.freeze_panes == 'D6' and _w6.auto_filter.ref == 'A5:K%d' % (5 + len(_r6)), (_w6.freeze_panes, _w6.auto_filter.ref))
                verifica(_nume + ': etapa fiecărui act e scrisă ca etapă, nu ca cod (fără „vig", „neg", „sem"…)', not any(re.fullmatch(r'(vig|neg|sem|plg|rat|prm)', r['Etapa'] or '') for r in _r6), {r['Etapa'] for r in _r6} )
                _pg.close()

                # ---- 4. rezerva: xlsx-stil.js nu se poate încărca → foaia simplă, cu aceleași rânduri
                _pg = _b.new_page()
                _avert = []
                _pg.on('console', lambda m: _avert.append(m.text[:200]) if m.type == 'warning' else None)
                _pg.route('**/*', lambda r: r.abort() if 'xlsx-stil' in r.request.url or not r.request.url.startswith(_baza) else r.continue_())
                _pg.goto(_baza + _pagina, wait_until='networkidle', timeout=90000)
                _asteapta_pagina(_pg)
                _f4 = _dir / (_nume + '-simplu.xlsx')
                _nf4 = _descarca(_pg, _f4)
                _wb7 = openpyxl.load_workbook(_f4)
                _w7 = _wb7.active
                verifica(_nume + ': fără xlsx-stil.js se descarcă totuși fișierul, ca foaie simplă („Acorduri"), cu aceleași nume', _wb7.sheetnames == ['Acorduri'] and _nf4 == _nf, (_wb7.sheetnames, _nf4))
                verifica(_nume + ': foaia simplă are linia cu filtrele, antetul identic și un rând pe acord',
                         'Fără filtre' in (_w7['A1'].value or '') and [c.value for c in _w7[2]] == ANTET_ACORDURI and _w7.max_row == 2 + len(_rand), (_w7['A1'].value, _w7.max_row, len(_rand)))
                _leg7 = [c.hyperlink for c in _w7['AC'][2:] if c.hyperlink]
                verifica(_nume + ': în foaia simplă adresele rămân hyperlinkuri adevărate, nu text', len(_leg7) == len(_rand) and all('#acord=' in h.target for h in _leg7), len(_leg7))
                verifica(_nume + ': rezerva anunță în consolă că exportul stilizat nu e disponibil', any('Exportul stilizat nu e disponibil' in a for a in _avert), _avert)
                _pg.close()
            _b.close()
    finally:
        _srv.shutdown()
        shutil.rmtree(_dir, ignore_errors=True)

    print()
    print('Browser: indicatorii (KPI) din capul paginii — „Acorduri” și „Creditori”: cifre, fâșia pe tipuri, creditorii, telefonul, fără depășiri')
    _srv3 = lga._Server(('127.0.0.1', 0), functools.partial(lga._Liniste, directory=str(AICI)))
    threading.Thread(target=_srv3.serve_forever, daemon=True).start()
    _baza3 = 'http://127.0.0.1:%d/' % _srv3.server_address[1]
    try:
        with sync_playwright() as _p:
            _b = _p.chromium.launch()
            for _pagina in ('legis_acorduri.html', 'acorduri.html'):
                _nume = _pagina.split('.')[0]
                _pg = _b.new_page(viewport={'width': 1400, 'height': 900})
                _erori = []
                _pg.on('pageerror', lambda e: _erori.append(str(e)[:200]))
                _pg.route('**/*', lambda r: r.continue_() if r.request.url.startswith(_baza3) else r.abort())
                _pg.goto(_baza3 + _pagina, wait_until='networkidle', timeout=90000)
                _asteapta_pagina(_pg)
                _k = _pg.evaluate('''() => {
                    const G = window.__GRUPURI__ || [];
                    const cards = [...document.querySelectorAll('.kpis .kpi')].map(k => ({
                        lbl: k.querySelector('.lbl').innerText.trim(), val: k.querySelector('.val').innerText.trim(),
                        unit: (k.querySelector('.kpi-unit') || {}).innerText || '', ico: !!k.querySelector('.kpi-ico svg'),
                        leg: [...k.querySelectorAll('.kpi-leg span')].map(s => ({t: s.innerText.replace(/\\s+\\d+$/, '').trim(), n: +s.querySelector('b').innerText,
                                                                                   c: getComputedStyle(s.querySelector('i')).backgroundColor})),
                        seg: [...k.querySelectorAll('.kpi-strip i')].map(i => ({t: i.title, c: getComputedStyle(i).backgroundColor})),
                        top: [...k.querySelectorAll('.kpi-top3 .n')].map((n, j) => ({n: n.innerText, c: +k.querySelectorAll('.kpi-top3 .c')[j].innerText})),
                        subTel: (k.querySelector('.doar-tel') || {}).textContent || ''
                    }));
                    const orgs = {};
                    G.forEach(g => Object.keys(g.orgs || {}).forEach(o => { orgs[o] = (orgs[o] || 0) + 1; }));
                    return {cards, grupuri: G.length, acte: G.reduce((s, g) => s + g.acte.length, 0), orgs,
                            toate: [...document.querySelectorAll('.kpis .kpi .lbl')].map(e => e.innerText.trim().toLowerCase()),
                            meter: document.querySelectorAll('.kpis .kpi-meter').length,
                            textKpi: document.querySelector('.kpis').innerText,
                            tipuri: G.reduce((m, g) => { m[g.categorie || ''] = (m[g.categorie || ''] || 0) + 1; return m; }, {})};
                }''')
                _c = _k['cards']
                verifica(_nume + ': două carduri KPI — „Acorduri” și „Creditori”, cu pictogramele lor',
                         [x['lbl'].lower() for x in _c] == ['acorduri', 'creditori'] and all(x['ico'] for x in _c),
                         [(x['lbl'], x['ico']) for x in _c])
                verifica(_nume + ': „Ratificate sau aprobate” și „Cu dată de intrare în vigoare” nu mai sunt în indicatori (nici cardul, nici bara „n din total”)',
                         not any(w in _k['textKpi'].lower() for w in ('ratificate sau aprobate', 'intrare în vigoare', 'etapa 4 din 5')) and _k['meter'] == 0
                         and 'ratificate sau aprobate' not in _k['toate'], (_k['toate'], _k['meter']))
                verifica(_nume + ': „Acorduri" = numărul de acorduri (%d), „din N acte publicate" = numărul de acte (%d)' % (_k['grupuri'], _k['acte']),
                         _c[0]['val'] == str(_k['grupuri']) and _c[0]['unit'] == 'din %d acte publicate' % _k['acte'], (_c[0]['val'], _c[0]['unit']))
                _leg = _c[0]['leg']
                _cunoscute = ['Asistență tehnică', 'Împrumut', 'Grant', 'Asistență financiară']
                _asteptat = {n: _k['tipuri'].get(n, 0) for n in _cunoscute}
                _asteptat['Altele'] = sum(v for kk, v in _k['tipuri'].items() if kk not in _cunoscute)
                verifica(_nume + ': fâșia pe tipuri — legenda are numărul real de acorduri pe tip, iar suma ei e totalul',
                         {x['t']: x['n'] for x in _leg} == {n: v for n, v in _asteptat.items() if v > 0} and sum(x['n'] for x in _leg) == _k['grupuri'],
                         (_leg, _asteptat))
                verifica(_nume + ': fâșia și legenda merg împreună — același număr de segmente, aceeași ordine (cel mai mare tip primul), aceleași culori, titlu „Tip: n"',
                         len(_c[0]['seg']) == len(_leg) > 1 and [s['c'] for s in _c[0]['seg']] == [x['c'] for x in _leg]
                         and [x['n'] for x in _leg] == sorted((x['n'] for x in _leg), reverse=True)
                         and all(s['t'] == '%s: %d' % (x['t'], x['n']) for s, x in zip(_c[0]['seg'], _leg)), (_c[0]['seg'], _leg))
                verifica(_nume + ': culorile tipurilor în legendă sunt distincte (nu se confundă două tipuri)', len({x['c'] for x in _leg}) == len(_leg), [x['c'] for x in _leg])
                _top = sorted(_k['orgs'].values(), reverse=True)[:3]
                verifica(_nume + ': „Creditori" = numărul de finanțatori distincți (%d); primii trei, după numărul de acorduri, cu numărul real' % len(_k['orgs']),
                         _c[1]['val'] == str(len(_k['orgs'])) and [x['c'] for x in _c[1]['top']] == _top and all(_k['orgs'].get(x['n']) == x['c'] for x in _c[1]['top']),
                         (_c[1]['val'], _c[1]['top'], _top))
                # ---- lățimi: fără depășiri, cifrele pe aceeași linie într-un rând de carduri
                _lat = {}
                for _w in (1400, 1100, 980, 820, 520, 390, 340):
                    _pg.set_viewport_size({'width': _w, 'height': 900})
                    _pg.wait_for_timeout(250)
                    _lat[_w] = _pg.evaluate('''() => {
                        const ks = [...document.querySelectorAll('.kpis .kpi')], rows = {};
                        ks.forEach(k => { const t = Math.round(k.getBoundingClientRect().top); (rows[t] = rows[t] || []).push(k); });
                        const vals = Object.values(rows).map(r => r.map(k => Math.round(k.querySelector('.val').getBoundingClientRect().top - k.getBoundingClientRect().top)));
                        return {over: ks.filter(k => k.scrollWidth > k.clientWidth + 1).length, h: Math.max(...ks.map(k => k.clientHeight)), vals,
                                pagina: document.documentElement.scrollWidth - innerWidth, coloane: Object.values(rows)[0].length};
                    }''')
                verifica(_nume + ': nicio depășire (nici în card, nici pe pagină) la 340–1400 px', all(m['over'] == 0 and m['pagina'] <= 0 for m in _lat.values()), {w: (m['over'], m['pagina']) for w, m in _lat.items()})
                verifica(_nume + ': în fiecare rând de carduri, cifrele stau pe aceeași linie (la orice lățime)', all(max(r) - min(r) <= 1 for m in _lat.values() for r in m['vals']), {w: m['vals'] for w, m in _lat.items()})
                verifica(_nume + ': două carduri, mereu pe același rând (de la 1400 la 340 px); înălțimea rămâne rezonabilă (≤ 230 px)',
                         all(m['coloane'] == 2 for m in _lat.values()) and all(m['h'] <= 230 for m in _lat.values()), {w: (m['coloane'], m['h']) for w, m in _lat.items()})
                # ---- telefon: aceleași cifre, fără fâșie, legendă și bare; creditorii apar ca text
                _pg.set_viewport_size({'width': 390, 'height': 844})
                _pg.wait_for_timeout(250)
                _tel = _pg.evaluate('''() => {
                    const viz = s => [...document.querySelectorAll('.kpis ' + s)].map(e => getComputedStyle(e).display);
                    const k2 = document.querySelectorAll('.kpis .kpi')[1];
                    const t = k2.querySelector('.doar-tel');
                    return {strip: viz('.kpi-strip'), leg: viz('.kpi-leg'), top3: viz('.kpi-top3'), ico: viz('.kpi-ico'), subTel: t ? getComputedStyle(t).display + '|' + t.innerText : ''};
                }''')
                verifica(_nume + ': pe telefon dispar fâșia, legenda, barele creditorilor și pictogramele, iar creditorii se citesc ca text',
                         set(_tel['strip'] + _tel['leg'] + _tel['top3'] + _tel['ico']) == {'none'}
                         and _tel['subTel'] == 'block|' + ' · '.join(x['n'] for x in _c[1]['top']), _tel)
                _pg.set_viewport_size({'width': 1400, 'height': 900})
                _pg.wait_for_timeout(250)
                _desk = _pg.evaluate("() => { const t = document.querySelector('.kpis .doar-tel'); return t ? getComputedStyle(t).display : 'lipsă'; }")
                verifica(_nume + ': pe ecran lat textul doar-pentru-telefon nu se vede', _desk == 'none', _desk)
                verifica(_nume + ': pagina nu a dat erori JavaScript', not _erori, _erori)
                _pg.close()
            _b.close()
    finally:
        _srv3.shutdown()

    print()
    print('Browser: panoul „Sumele acordurilor, pe tipuri de finanțare” (legis.md) — total, bară, carduri pe tip, socoteala celor 551, telefon, engleză')

    def _suma_text(text):
        """„262 mil. USD” / „1,5 mld. EUR” / „580 000 CHF” → (valoarea, valuta)."""
        m = re.fullmatch(r'\s*([\d ,]+?)\s*(mld\.|mil\.|mii)?\s*([A-Z]{3})\s*', text.replace(' ', ' '))
        n = float(m.group(1).replace(' ', '').replace(',', '.'))
        return n * {'mld.': 1e9, 'mil.': 1e6, 'mii': 1e3, None: 1}[m.group(2)], m.group(3)

    _srv4 = lga._Server(('127.0.0.1', 0), functools.partial(lga._Liniste, directory=str(AICI)))
    threading.Thread(target=_srv4.serve_forever, daemon=True).start()
    _baza4 = 'http://127.0.0.1:%d/' % _srv4.server_address[1]
    try:
        with sync_playwright() as _p:
            _b = _p.chromium.launch()
            _pg = _b.new_page(viewport={'width': 1400, 'height': 900})
            _erori = []
            _pg.on('pageerror', lambda e: _erori.append(str(e)[:200]))
            _pg.route('**/*', lambda r: r.continue_() if r.request.url.startswith(_baza4) else r.abort())
            _pg.goto(_baza4 + 'legis_acorduri.html', wait_until='networkidle', timeout=90000)
            _asteapta_pagina(_pg)
            _s = _pg.evaluate("""() => {
                const q = (s, r) => (r || document).querySelector(s), qa = (s, r) => [...(r || document).querySelectorAll(s)];
                const rgb = e => getComputedStyle(e).backgroundColor;
                const A = window.__ACORDURI__();
                const cards = qa('#sume .sume-card').map(c => ({
                    tip: c.dataset.tip, eticheta: q('.st', c).innerText.trim(), sv: q('.sv', c).innerText.trim(), sn: q('.sn', c).innerText.trim(),
                    culoare: getComputedStyle(c, '::before').backgroundColor, ptr: c.tagName, titlu: c.title,
                    cap: q('.sx-cap', c) ? q('.sx-cap', c).innerText.trim() : null,
                    top: qa('.sx-r', c).map(r => ({n: q('.sx-n', r).innerText.trim(), t: q('.sx-n', r).title, s: q('.sx-s', r).innerText.trim()}))}));
                const kpiLeg = {}; qa('.kpis .kpi-leg span').forEach(s => { kpiLeg[s.innerText.replace(/\\s+\\d+$/, '').trim()] = rgb(q('i', s)); });
                const nota = qa('#sume .sume-nota b').map(b => +b.innerText);
                return {
                    nPanouri: qa('#sume').length, dupaKpi: !!(q('.kpis').nextElementSibling && q('.kpis').nextElementSibling.id === 'sume'),
                    inainteDeLista: !!(q('#sume').compareDocumentPosition(q('#lista')) & Node.DOCUMENT_POSITION_FOLLOWING),
                    lbl: q('#sume .sume-lbl').innerText.trim(), val: q('#sume .sume-val').innerText.trim(), acop: q('#sume .sume-acop').innerText.trim(),
                    bara: qa('#sume .sume-bar i').map(i => ({g: parseFloat(getComputedStyle(i).flexGrow), c: rgb(i), t: i.title})),
                    leg: qa('#sume .sume-leg span').map(s => ({t: s.innerText.replace(/\\s+\\d+%$/, '').trim(), p: parseInt(q('b', s).innerText), c: rgb(q('i', s))})),
                    cards, kpiLeg, nota, capNota: q('#sume .sume-nota .cap').innerText.trim(), expl: q('#sume .sume-expl').innerText,
                    nGrupuri: window.__GRUPURI__.length,
                    fara: A.filter(a => !a.suma).length, marcate: A.filter(a => a.suma && a.faraTotal).length,
                    A: A.map(a => ({n: a.nume, s: a.scurt, c: a.categorie, suma: a.suma, ft: a.faraTotal})),
                    detalii: {tag: q('#sume details') ? q('#sume details').open : null, randuri: qa('#sume .sume-tab tbody tr').map(r => qa('td', r).map(c => c.textContent.trim()))},
                    taburi: qa('#catBtns button').map(b => b.dataset.cat)};
            }""")
            _cards = _s['cards']
            verifica('panoul de sume: există o singură dată, imediat sub indicatori și înaintea listei',
                     _s['nPanouri'] == 1 and _s['dupaKpi'] and _s['inainteDeLista'], (_s['nPanouri'], _s['dupaKpi'], _s['inainteDeLista']))
            verifica('panoul de sume: o etichetă, totalul mare în euro și „n acorduri din N”', _s['lbl'].lower() == 'acordurile cu sumă cunoscută adună'
                     and re.fullmatch(r'[\d,]+ (?:mld\.|mil\.|mii) EUR', _s['val']) is not None and re.fullmatch(r'\d+ (?:de )?acord\w* din \d+', _s['acop']) is not None,
                     (_s['lbl'], _s['val'], _s['acop']))
            _tot, _tol = _eur_pagina(_s['val'])
            _cuprins = {}
            for _cd in _cards:
                _v, _tl = _eur_pagina(_cd['sv']) if _cd['sv'] != '—' else (0, 0)
                _m = re.fullmatch(r'(\d+) acorduri cu sumă din (\d+)(?: · (\d+)% din total)?', _cd['sn'])
                _cuprins[_cd['tip']] = {'v': _v, 'tol': _tl, 'n': int(_m.group(1)), 'toate': int(_m.group(2)), 'p': int(_m.group(3)) if _m.group(3) else None} if _m else None
            verifica('panoul de sume: câte un card pe tip (butoane, cu titlu), în ordinea tipurilor; fiecare cu suma, „n acorduri cu sumă din M · P% din total”',
                     len(_cards) >= 3 and all(c['ptr'] == 'BUTTON' and c['titlu'] and c['eticheta'].lower() == c['tip'].lower() for c in _cards)
                     and all(_cuprins[c['tip']] is not None for c in _cards) and {c['tip'] for c in _cards} == {x for x in _s['taburi'] if x != 'all'},
                     [(c['tip'], c['sv'], c['sn']) for c in _cards])
            verifica('panoul de sume: totalul mare = suma cardurilor pe tip (în limita rotunjirii afișate)',
                     abs(sum(x['v'] for x in _cuprins.values()) - _tot) <= _tol + sum(x['tol'] for x in _cuprins.values()),
                     (_tot, [(k, x['v']) for k, x in _cuprins.items()]))
            verifica('panoul de sume: cardurile împart cele %d de acorduri (suma lui „din M” = numărul de acorduri), iar „n” însumat = numărul din „n acorduri din N”' % _s['nGrupuri'],
                     sum(x['toate'] for x in _cuprins.values()) == _s['nGrupuri'] and re.search(r'(\d+)\s+(?:de\s+)?acord\w*\s+din\s+(\d+)', _s['acop']).groups()
                     == (str(sum(x['n'] for x in _cuprins.values())), str(_s['nGrupuri'])), (_cuprins, _s['acop']))
            verifica('panoul de sume: procentele (carduri și legendă) = partea fiecărui tip din total, rotunjită',
                     all(x['p'] is not None and abs(x['p'] - 100 * x['v'] / _tot) <= 1.05 for x in _cuprins.values() if x['v'])
                     and {l['t']: l['p'] for l in _s['leg']} == {k: x['p'] for k, x in _cuprins.items() if x['v']}, (_s['leg'], _cuprins))
            _gr = [b['g'] for b in _s['bara']]
            verifica('panoul de sume: bara are câte un segment pe tip, proporțional cu suma tipului, în ordinea cardurilor, cu legenda alături',
                     len(_s['bara']) == len(_s['leg']) == sum(1 for x in _cuprins.values() if x['v'])
                     and all(abs(g / sum(_gr) - _cuprins[c['tip']]['v'] / _tot) <= _cuprins[c['tip']]['tol'] / _tot + 0.002 for g, c in zip(_gr, [c for c in _cards if _cuprins[c['tip']]['v']]))
                     and [l['t'] for l in _s['leg']] == [c['tip'] for c in _cards if _cuprins[c['tip']]['v']]
                     and all(b['t'] == '%s: %d%%' % (l['t'], l['p']) for b, l in zip(_s['bara'], _s['leg'])), (_s['bara'], _s['leg']))
            _col = {c['tip']: c['culoare'] for c in _cards}
            verifica('panoul de sume: culoarea unui tip e aceeași în card, în bară, în legendă și în fâșia din indicatori; tipurile au culori distincte',
                     all(l['c'] == _col[l['t']] for l in _s['leg']) and all(b['c'] == l['c'] for b, l in zip(_s['bara'], _s['leg']))
                     and all(_s['kpiLeg'].get(k) == v for k, v in _col.items() if k in _s['kpiLeg']) and len(set(_col.values())) == len(_col)
                     and len([k for k in _col if k in _s['kpiLeg']]) >= 3, (_col, _s['kpiLeg']))
            # ---- socoteala acordurilor: se adună + au suma pe rând dar nu se adună + n-au sumă = toate
            _a_, _b_, _c_ = _s['nota']
            _expl = {k: int(v) for v, k in re.findall(r'(\d+) (repetă|au suma marcată|e într-o valută|sunt în valute)', _s['expl'])}
            _dubluri = _expl.get('repetă', 0); _marcate_txt = _expl.get('au suma marcată', 0); _farcurs = _expl.get('e într-o valută', 0) + _expl.get('sunt în valute', 0)
            verifica('panoul de sume: socoteala celor %d de acorduri — se adună + au suma pe rând, dar nu se adună + n-au încă suma = toate' % _s['nGrupuri'],
                     _s['capNota'] == 'Din cele %d de acorduri' % _s['nGrupuri'] and _a_ + _b_ + _c_ == _s['nGrupuri']
                     and _a_ == sum(x['n'] for x in _cuprins.values()), (_s['capNota'], _s['nota']))
            verifica('panoul de sume: „n-au încă suma” = acordurile fără sumă din date (%d); cele „marcate nu se adună” = cele din date (%d)' % (_s['fara'], _s['marcate']),
                     _c_ == _s['fara'] and _marcate_txt == _s['marcate'], (_c_, _s['fara'], _marcate_txt, _s['marcate']))
            verifica('panoul de sume: cele care „nu se adună” se descompun complet în explicația de dedesubt (dubluri + marcate + fără curs = %d)' % _b_,
                     _dubluri + _marcate_txt + _farcurs == _b_ and 'Totalul e un minim' in _s['expl'], (_b_, _expl, _s['expl']))
            # ---- cele mai mari trei acorduri pe tip: sunt ale tipului, în ordine descrescătoare, cu suma lor reală
            _dupa_nume = {}
            for _a in _s['A']:
                _dupa_nume.setdefault(_a['s'], []).append(_a)
                _dupa_nume.setdefault(_a['n'], []).append(_a)
            _prost = []
            for _cd in _cards:
                if not _cuprins[_cd['tip']]['n']:
                    continue
                _max_tip = max((a['suma']['eur'] for a in _s['A'] if a['c'] == _cd['tip'] and a['suma'] and not a['ft'] and a['suma']['eur'] is not None), default=None)
                _eurs = []
                if not (1 <= len(_cd['top']) <= 3 and (_cd['cap'] or '').lower() == 'cele mai mari'):
                    _prost.append((_cd['tip'], 'nr/titlu', _cd['cap'], len(_cd['top'])))
                for _r in _cd['top']:
                    _v_r, _val_r = _suma_text(_r['s'])
                    _cand = [a for a in _dupa_nume.get(_r['t'], []) if a['c'] == _cd['tip'] and a['suma'] and a['suma']['val'] == _val_r
                             and abs(a['suma']['v'] - _v_r) <= 0.006 * _v_r + 1]
                    if not _cand:
                        _prost.append((_cd['tip'], 'rând fără acord potrivit', _r))
                        continue
                    _eurs.append(_cand[0]['suma']['eur'])
                if _eurs != sorted(_eurs, reverse=True) or (_eurs and _eurs[0] != _max_tip):
                    _prost.append((_cd['tip'], 'ordine/maxim', _eurs, _max_tip))
            verifica('panoul de sume: „Cele mai mari” — până la trei acorduri pe tip, ale tipului respectiv, cu suma lor, în ordine descrescătoare; primul e cel mai mare din tip',
                     not _prost, _prost)
            verifica('panoul de sume: detaliul „Pe valute…” e închis, iar acordurile din tabelul lui se adună la fel ca în carduri',
                     _s['detalii']['tag'] is False and sum(int(r[2]) for r in _s['detalii']['randuri']) == sum(x['n'] for x in _cuprins.values()), _s['detalii']['tag'])
            # ---- clic pe card: filtrează lista pe tipul lui
            _tip = _cards[0]['tip']
            _pg.click('.sume-card[data-tip="%s"]' % _tip)
            _pg.wait_for_timeout(900)
            _fil = _pg.evaluate("""() => ({apasat: [...document.querySelectorAll('#catBtns button[aria-pressed=true]')].map(b => b.dataset.cat), hash: location.hash,
                afisate: (document.querySelector('#none') || {}).innerText || '',
                tipuri: [...new Set([...document.querySelectorAll('tr.acord')].map(r => (r.innerText.match(/(Grant|Împrumut|Asistență tehnică|Asistență financiară)/) || [])[1]))]})""")
            verifica('panoul de sume: clic pe cardul „%s” filtrează lista pe tipul lui (butonul „Tip”, adresa paginii, rândurile)' % _tip,
                     _fil['apasat'] == [_tip] and _fil['hash'] == '#cat=' + _tip and ('din %d afișate' % _cuprins[_tip]['toate']) in _fil['afisate'] and _fil['tipuri'] == [_tip], _fil)
            # ---- fără depășiri, trei carduri pe un rând de la 820 px
            _pg.evaluate("() => { const b = document.querySelector('#catBtns button[data-cat=\"all\"]'); if (b) b.click(); window.scrollTo(0, 0); }")
            _lat = {}
            for _w in (1400, 1100, 980, 820, 760, 390, 340):
                _pg.set_viewport_size({'width': _w, 'height': 900})
                _pg.wait_for_timeout(250)
                _lat[_w] = _pg.evaluate("""() => {
                    const cs = [...document.querySelectorAll('#sume .sume-card')];
                    const r = e => e.getBoundingClientRect();
                    return {pagina: document.documentElement.scrollWidth - innerWidth, cardPeste: cs.filter(c => c.scrollWidth > c.clientWidth + 1).length,
                            panouPeste: document.querySelector('#sume').scrollWidth - document.querySelector('#sume').clientWidth,
                            peRand: new Set(cs.map(c => Math.round(r(c).top))).size, nCarduri: cs.length,
                            valIn: cs.every(c => { const v = c.querySelector('.sv').getBoundingClientRect(), x = r(c); return v.left >= x.left && v.right <= x.right; }),
                            kpi: r(document.querySelector('.kpis')).bottom, sus: r(document.querySelector('#sume')).top, jos: r(document.querySelector('#sume')).bottom,
                            h: Math.round(r(document.querySelector('#sume')).height),
                            leg: getComputedStyle(document.querySelector('#sume .sume-leg')).display, sx: [...document.querySelectorAll('#sume .sume-card .sx')].map(e => getComputedStyle(e).display),
                            cap: [...document.querySelectorAll('#sume .sume-card .sx-cap')].map(e => getComputedStyle(e).display)};
                }""")
            verifica('panoul de sume: nicio depășire (nici în card, nici în panou, nici pe pagină) la 340–1400 px',
                     all(m['pagina'] <= 0 and m['cardPeste'] == 0 and m['panouPeste'] <= 0 and m['valIn'] for m in _lat.values()),
                     {w: (m['pagina'], m['cardPeste'], m['panouPeste'], m['valIn']) for w, m in _lat.items()})
            verifica('panoul de sume: pe ecran lat (≥ 820 px) cardurile stau toate pe un rând, cu „Cele mai mari” și legenda; pe telefon (≤ 390 px) stau unul sub altul, compacte',
                     all(_lat[w]['peRand'] == 1 and _lat[w]['leg'] != 'none' and set(_lat[w]['sx']) == {'flex'} for w in (1400, 1100, 980, 820))
                     and all(_lat[w]['peRand'] == _lat[w]['nCarduri'] and _lat[w]['leg'] == 'none' and set(_lat[w]['sx'] + _lat[w]['cap']) == {'none'} for w in (390, 340)),
                     {w: (m['peRand'], m['leg'], m['sx']) for w, m in _lat.items()})
            verifica('panoul de sume: pe telefon e sub indicatori și deasupra listei, iar înălțimea lui rămâne mică (≤ 700 px la 390 px)',
                     _lat[390]['kpi'] <= _lat[390]['sus'] and _lat[390]['h'] <= 700, {w: (m['kpi'], m['sus'], m['h']) for w, m in _lat.items() if w <= 390})
            _ord = _pg.evaluate("""() => { const y = s => document.querySelector(s).getBoundingClientRect().top + scrollY;
                return [y('.kpis'), y('#sume'), y('#lista')]; }""")
            verifica('panoul de sume: pe telefon ordinea pe verticală e indicatori → sume → listă', _ord == sorted(_ord) and len(set(_ord)) == 3, _ord)
            # ---- engleză: nicio frază românească în panou (în afară de denumirile acordurilor)
            _pg.set_viewport_size({'width': 1400, 'height': 900})
            _pg.evaluate("() => window.Traducere.seteaza('en')")
            _pg.wait_for_timeout(1200)
            _en = _pg.evaluate("""() => {
                const p = document.querySelector('#sume').cloneNode(true);
                [...p.querySelectorAll('.sx-n')].forEach(e => e.remove());
                const atr = [...p.querySelectorAll('[title],[aria-label]')].map(e => (e.getAttribute('title') || '') + ' ' + (e.getAttribute('aria-label') || '')).join(' | ');
                const kpi = document.querySelector('.kpis').cloneNode(true);
                return {text: p.textContent.replace(/\\s+/g, ' '), atr, kpi: kpi.textContent.replace(/\\s+/g, ' ')};
            }""")
            _ro = re.compile(r'[ăâîșțĂÂÎȘȚşţ]|\b(?:acord|acorduri|suma|sumă|din|nu au|se adună|repetă|valută)\b')
            verifica('panoul de sume în engleză: nicio frază românească în text (denumirile acordurilor rămân ca în registru)',
                     not _ro.search(_en['text']) and 'Agreement amounts, by type of financing' in _en['text'] and 'Largest' in _en['text']
                     and 'are added up in the total' in _en['text'] and 'The total is a minimum' in _en['text'], _ro.findall(_en['text'])[:8])
            verifica('panoul de sume în engleză: nici în titlurile de pe bară și carduri (title) nu rămâne română', not _ro.search(_en['atr']) and 'Loan' in _en['atr'], _en['atr'][:300])
            verifica('indicatorii în engleză: nicio frază românească („primii trei, după numărul de acorduri” se traduce)', not re.search(r'[ăâîșțĂÂÎȘȚ]|după|acorduri|primii', _en['kpi']) and 'top three' in _en['kpi'], _en['kpi'])
            _pg.evaluate("() => window.Traducere.seteaza('ro')")
            _pg.wait_for_timeout(600)
            _ro_inapoi = _pg.evaluate("() => document.querySelector('#sume .sume-lbl').innerText.trim().toLowerCase() + '|' + document.querySelector('#sume .sume-nota .cap').innerText")
            verifica('panoul de sume: revenirea la română reface textul', _ro_inapoi == 'acordurile cu sumă cunoscută adună|Din cele %d de acorduri' % _s['nGrupuri'], _ro_inapoi)
            verifica('panoul de sume: pagina nu a dat erori JavaScript', not _erori, _erori)
            _pg.close()
            # registrul din Monitorul Oficial: aceeași pagină-șablon, dar fără panoul de sume (rămâne „Cum se încheie un acord”)
            _pm = _b.new_page(viewport={'width': 1400, 'height': 900})
            _pm.route('**/*', lambda r: r.continue_() if r.request.url.startswith(_baza4) else r.abort())
            _pm.goto(_baza4 + 'acorduri.html', wait_until='networkidle', timeout=90000)
            _asteapta_pagina(_pm)
            _mon = _pm.evaluate("() => ({sume: document.querySelectorAll('#sume').length, kpi: document.querySelectorAll('.kpis .kpi').length, cum: !!document.querySelector('#cumSeIncheie')})")
            verifica('registrul din Monitorul Oficial: două carduri KPI, fără panoul de sume, cu „Cum se încheie un acord”', _mon == {'sume': 0, 'kpi': 2, 'cum': True}, _mon)
            _pm.close()
            _b.close()
    finally:
        _srv4.shutdown()

    print()
    print('Browser: sumele din surse externe — marcajul „ext.", legătura spre sursă, exportul Excel')
    _lista_l, _ = lga.citeste_acorduri()
    _ext_l = [a for a in _lista_l if a['suma'] and a['suma']['sursa'] == 'extern']
    verifica('registrul legis are acorduri cu suma dintr-o sursă externă, fiecare cu sumă în euro',
             len(_ext_l) >= 20 and all(a['suma']['eur'] and a['suma']['eur'] > 0 for a in _ext_l), len(_ext_l))
    # Compactul MCC: legea de ratificare și hotărârea de aprobare își scriu altfel titlul („Compact" / „Provocările
    # Mileniului") și ajungeau pe două rânduri, fiecare numărat în total. Acum sunt un singur rând (date/contopiri_manual.json),
    # cu suma din textul legii, nu dintr-o sursă externă.
    _mc = [a for a in _lista_l if any(x['act'] in ('LP125/2010', 'HG677/2009', 'HG499/2010') for x in a['acte'])]
    verifica('Compactul MCC: un singur rând, cu cele patru acte (hotărârea de inițiere, cea de aprobare, legea, decretul)',
             len(_mc) == 1 and {x['act'] for x in _mc[0]['acte']} == {'HG677/2009', 'HG499/2010', 'LP125/2010', 'DP391/2010'},
             [(a['nume'], [x['act'] for x in a['acte']]) for a in _mc])
    verifica('Compactul MCC: 262 mil. USD din textul legii, convertit în euro',
             len(_mc) == 1 and _mc[0]['suma'] and _mc[0]['suma']['v'] == 262000000 and _mc[0]['suma']['val'] == 'USD'
             and _mc[0]['suma']['sursa'] == 'text' and 150e6 < _mc[0]['suma']['eur'] < 300e6, _mc and _mc[0]['suma'])
    _tamp = [a for a in _lista_l if any(x['act'] == 'LP225/2016' for x in a['acte'])]
    verifica('TAMP (Banca Mondială): două acorduri ratificate prin aceeași lege, 20 mil. USD, sursă externă, convertit în euro',
             len(_tamp) == 1 and _tamp[0]['suma'] and _tamp[0]['suma']['v'] == 20000000 and _tamp[0]['suma']['val'] == 'USD'
             and _tamp[0]['suma']['sursa'] == 'extern' and 10e6 < _tamp[0]['suma']['eur'] < 30e6 and not _tamp[0]['faraTotal'],
             _tamp and _tamp[0]['suma'])
    _sib = next((a for a in _lista_l if a['nume'].strip() == 'Siemens'), None)
    verifica('creditul german din 1995: 30 mil. DEM din textul legii, nu „extern"',
             _sib and _sib['suma']['v'] == 30000000 and _sib['suma']['val'] == 'DEM' and _sib['suma']['sursa'] == 'text', _sib and _sib['suma'])
    # A doua verificare a dublurilor (date/contopiri_manual.json): același acord stătea pe două-patru rânduri, fiecare cu suma
    # numărată în total, iar alte rânduri amestecau actele a două acorduri diferite. Unificările și mutările de mână le îndreaptă.
    def _rd(*coduri):
        return [a for a in _lista_l if any(x['act'] in coduri for x in a['acte'])]

    def _ac(a):
        return {x['act'] for x in a['acte']}
    _r = _rd('DP1662/2024', 'LP264/2024', 'HG609/2024')
    verifica('„Deșeuri solide" (BERD, grant 4,34 mil. EUR): decretul DP1662/2024, legea LP264/2024 și hotărârea HG609/2024 stau pe un rând, cu suma numărată o dată',
             len(_r) == 1 and {'DP1662/2024', 'LP264/2024', 'HG609/2024'} <= _ac(_r[0]) and _r[0]['suma'] and _r[0]['suma']['v'] == 4340000
             and _r[0]['suma']['val'] == 'EUR', [(a['scurt'], sorted(_ac(a))) for a in _r])
    _r = _rd('HG226/2017', 'DPRM445/2017', 'LP278/2018')
    verifica('asistența macrofinanciară UE din 2017 (grant 40 mil. EUR): hotărârea de inițiere și decretul stau pe un rând, cu suma din textul acordului ratificat',
             len(_r) == 1 and {'HG226/2017', 'DPRM445/2017', 'LP278/2018'} <= _ac(_r[0]) and _r[0]['suma'] and _r[0]['suma']['v'] == 40000000
             and _r[0]['suma']['sursa'] == 'acord', [(a['scurt'], a['suma']) for a in _r])
    _r = _rd('HP543/1995', 'HG307/1995', 'HP1423/1997', 'HG1099/1997')
    verifica('Siemens (1995): hotărârile din 1995 și 1997 și legile stau pe un singur rând', len(_r) == 1 and len(_r[0]['acte']) == 4, [sorted(_ac(a)) for a in _r])
    _eib, _d4 = _rd('HG1030/2007'), _rd('HG372/2021')
    verifica('BEI „Drumuri europene în Moldova" (2007, 30 mil. EUR, sursă externă) și „Moldova drumuri IV" (2022, 150 mil. EUR) sunt rânduri diferite, fiecare cu suma lui',
             len(_eib) == 1 and len(_d4) == 1 and _eib[0]['id'] != _d4[0]['id'] and _eib[0]['suma'] and _d4[0]['suma']
             and (_eib[0]['suma']['v'], _eib[0]['suma']['sursa']) == (30000000, 'extern') and _d4[0]['suma']['v'] == 150000000
             and not ({'HG1030/2007', 'LP217/2007', 'DPRM1350/2007'} & _ac(_d4[0])) and _d4[0]['scurt'] == 'Moldova drumuri IV',
             [(a['scurt'], a['suma'], sorted(_ac(a))) for a in _eib + _d4])
    _jp = [_rd(c) for c in ('HG28/2007', 'HG233/2008', 'HG406/2009', 'HG103/2012')]
    verifica('Japonia, fermierii neprivilegiați (2KR): fiecare tranșă anuală e un rând (schimb de note separat), cu suma ei în yeni',
             all(len(x) == 1 for x in _jp) and len({x[0]['id'] for x in _jp}) == 4 and all(x[0]['suma'] and x[0]['suma']['val'] == 'JPY' for x in _jp)
             and [x[0]['suma']['v'] for x in _jp] == [230000000, 200000000, 160000000, 130000000], [(x[0]['scurt'], x[0]['suma']) for x in _jp if x])
    _tacis, _rural = _rd('HG824/2012', 'HG1421/2016'), _rd('HG852/2012', 'HG9/2014')
    verifica('TACIS 2006 și programul pentru zonele rurale: addendumurile nr. 2 și 3 la TACIS stau pe rândul TACIS, cele la programul rural pe alt rând, cu denumire citibilă',
             len(_tacis) == 1 and _ac(_tacis[0]) == {'HG824/2012', 'HG1421/2016'} and 'TACIS' in _tacis[0]['nume']
             and len(_rural) == 1 and _ac(_rural[0]) == {'HG852/2012', 'HG9/2014'} and 'zonelor rurale' in _rural[0]['nume'] and _rural[0]['scurt'] != 'Addendumul nr',
             [(a['scurt'], sorted(_ac(a))) for a in _tacis + _rural])
    _ap, _apd = _rd('HP119/1998'), _rd('HG1450/2008', 'HG164/2009')
    verifica('aeroportul Chișinău: creditul BERD din 1998 (9 mil. USD) și acordul direct BERD–BEI din 2008–2009 sunt rânduri diferite',
             len(_ap) == 1 and len(_apd) == 1 and _ap[0]['id'] != _apd[0]['id'] and _ap[0]['suma'] and _ap[0]['suma']['v'] == 9000000 and not _apd[0]['suma'],
             [(a['scurt'], a['suma']) for a in _ap + _apd])
    _c3, _c2 = _rd('HG846/2002', 'LP1175/2002'), _rd('HP551/1999')
    verifica('creditul trei pentru ajustări structurale (2002): hotărârea și legea pe un rând; creditul din 1999 (29,6 mil. DST) e alt rând',
             len(_c3) == 1 and len(_c2) == 1 and _c3[0]['id'] != _c2[0]['id'] and {'HG846/2002', 'LP1175/2002'} <= _ac(_c3[0])
             and _c3[0]['suma']['v'] == 24100000 and _c2[0]['suma']['v'] == 29600000, [(a['scurt'], a['suma']) for a in _c3 + _c2])
    _cbm, _cbm2 = _rd('HG8/2012'), _rd('HG10/2014')
    verifica('Măsuri de Consolidare a Încrederii: programul din 2011 (12 mil. EUR, sursă externă) și cel din 2013 (semnat în 2014) sunt rânduri diferite',
             len(_cbm) == 1 and len(_cbm2) == 1 and _cbm[0]['id'] != _cbm2[0]['id'] and _ac(_cbm[0]) == {'HG8/2012'} and _cbm[0]['suma']['v'] == 12000000
             and not _cbm2[0]['suma'], [(a['scurt'], a['suma']) for a in _cbm + _cbm2])
    _ita = _rd('HG683/2024')
    verifica('InfoTrustAlliance Moldova (ITA-M): cooperare tehnică, nu grant; bugetul de 1,5 mil. EUR se vede pe rând, dar „nu se adună" (sursele dau alte cifre)',
             len(_ita) == 1 and _ita[0]['categorie'] == 'Asistență tehnică' and _ita[0]['suma'] and _ita[0]['suma']['v'] == 1500000
             and _ita[0]['suma']['val'] == 'EUR' and _ita[0]['faraTotal'] is True, [(a['categorie'], a['suma'], a['faraTotal']) for a in _ita])
    _rs = _rd('HG115/2026', 'OMMPS264/2025', 'HG166/2026', 'OMMPS98/2026')
    verifica('Cehia, proiectul RESTART: ordinul de semnare a memorandumului (2025) și actele amendamentului nr. 1 (2026) stau pe un singur rând, asistență tehnică; '
             '22 902 012,92 CZK dintr-o sursă externă, trecut în euro la cursul BCE din 1 iulie 2026 (24,254)',
             len(_rs) == 1 and _ac(_rs[0]) == {'HG115/2026', 'OMMPS264/2025', 'HG166/2026', 'OMMPS98/2026'} and _rs[0]['categorie'] == 'Asistență tehnică'
             and _rs[0]['suma'] and _rs[0]['suma']['v'] == 22902012.92 and _rs[0]['suma']['val'] == 'CZK' and _rs[0]['suma']['sursa'] == 'extern'
             and _rs[0]['suma']['eur'] == round(22902012.92 / 24.254) and not _rs[0]['faraTotal'],
             [(a['scurt'], a['categorie'], a['suma'], sorted(_ac(a))) for a in _rs])
    _cr = _rd('HG574/2025')
    verifica('CRESTA (Elveția, Ministerul Justiției): un singur rând, asistență tehnică, 1 880 000 CHF dintr-o sursă externă, trecut în euro la cursul BCE din 1 iulie 2026',
             len(_cr) == 1 and _ac(_cr[0]) == {'HG574/2025'} and _cr[0]['categorie'] == 'Asistență tehnică' and _cr[0]['suma']
             and (_cr[0]['suma']['v'], _cr[0]['suma']['val'], _cr[0]['suma']['sursa']) == (1880000, 'CHF', 'extern')
             and _cr[0]['suma']['eur'] == round(1880000 / 0.9234) and not _cr[0]['faraTotal'], [(a['scurt'], a['categorie'], a['suma']) for a in _cr])
    _ms = _rd('HG654/2024')
    verifica('MSIP (proiectul moldo-elvețian în domeniul proprietății intelectuale, SECO): un singur rând, Grant (decizia de mână bate „asistență tehnică" din titlu); '
             '794 407,37 EUR dintr-o sursă externă, numărat o singură dată, fără conversie',
             len(_ms) == 1 and _ac(_ms[0]) == {'HG654/2024'} and _ms[0]['categorie'] == 'Grant' and _ms[0]['suma']
             and (_ms[0]['suma']['v'], _ms[0]['suma']['val'], _ms[0]['suma']['sursa']) == (794407.37, 'EUR', 'extern')
             and _ms[0]['suma']['eur'] == 794407 and not _ms[0]['faraTotal'], [(a['scurt'], a['categorie'], a['suma']) for a in _ms])
    _fi = _rd('HG80/2026', 'HG90/2026', 'OMMPS73/2026', 'HG416/2026', 'HG442/2026', 'OMMPS273/2026')
    verifica('FICR (centrele de plasament temporar pentru refugiați): acordul din 2026 și amendamentul nr. 1 pe un singur rând, Grant; suma e totalul după amendament (580 000 CHF), iar nota păstrează suma inițială (300 000 CHF)',
             len(_fi) == 1 and len(_fi[0]['acte']) == 6 and _fi[0]['categorie'] == 'Grant' and _fi[0]['suma'] and _fi[0]['suma']['v'] == 580000
             and _fi[0]['suma']['val'] == 'CHF' and not _fi[0]['faraTotal'], [(a['scurt'][:40], a['categorie'], a['suma']) for a in _fi])
    _sm = _rd('HG290/2025', 'HG362/2025', 'LP163/2025', 'DP281/2025')
    verifica('BDCE (CEB), acordul-cadru de 30 mil. EUR pentru școli: hotărârile (care îl numesc „Extinderea rețelei școlilor-model"), legea de ratificare și decretul (care îl numesc „Modernizarea școlilor") '
             'stau pe un singur rând, Împrumut, suma din textul acordului numărată o singură dată',
             len(_sm) == 1 and {'HG290/2025', 'HG362/2025', 'LP163/2025', 'DP281/2025'} <= _ac(_sm[0]) and _sm[0]['categorie'] == 'Împrumut' and _sm[0]['suma']
             and (_sm[0]['suma']['v'], _sm[0]['suma']['val'], _sm[0]['suma']['sursa'], _sm[0]['suma']['eur']) == (30000000, 'EUR', 'acord', 30000000)
             and not _sm[0]['faraTotal'], [(a['scurt'], a['categorie'], a['suma']) for a in _sm])
    _tt, _p99 = _rd('HG750/2003', 'LP301/2003'), _rd('HP418/1999')
    verifica('AID, Facilitarea Comerțului și Transportului în Europa de Sud-Est: hotărârea din 2003 stă cu legea din 2003 (5,3 mil. DST), nu cu hotărârile Parlamentului din 1999 (15 mil. USD), care rămân pe alt rând',
             len(_tt) == 1 and {'HG750/2003', 'LP301/2003', 'DPRM1378/2003'} <= _ac(_tt[0]) and _tt[0]['suma'] and (_tt[0]['suma']['v'], _tt[0]['suma']['val']) == (5300000, 'DST')
             and len(_p99) == 1 and _p99[0]['id'] != _tt[0]['id'] and 'HG750/2003' not in _ac(_p99[0]) and _p99[0]['suma'] and _p99[0]['suma']['v'] == 15000000,
             [(a['scurt'], a['suma'], sorted(_ac(a))) for a in _tt + _p99])
    _mon2, _ = lga.citeste_acorduri(pagina='acorduri.html')
    _ui = next((a for a in _mon2 if a['nume'].strip() == 'Sprijin pentru integrarea în UE'), None)
    verifica('registrul Monitor: „Sprijin pentru integrarea în UE" = 25 mil. EUR, sursă externă',
             _ui and _ui['suma'] and _ui['suma']['eur'] == 25000000 and _ui['suma']['sursa'] == 'extern', _ui and _ui['suma'])

    # Un acord foarte nou, doar în Monitorul Oficial (HG430/2026 + Ordinul 147/2026), încă fără fișă pe legis.md:
    # titlul nu spune dacă banii se rambursează, dar nota Cancelariei de Stat spune „grant" și dă suma (în lei, cu
    # echivalentul în dolari). Decizia de categorie și suma pusă de mână trebuie să ajungă la el în ambele registre.
    for _nume_reg, _lista_reg in (('legis', _lista_l), ('Monitor', _mon2)):
        _pn = [a for a in _lista_reg if 'Comunități reziliente prin abilitarea femeilor' in a['nume']]
        verifica('acordul IP ODA – PNUD (%s): un singur rând, „Grant", 386 910 USD dintr-o sursă externă, trecut în euro' % _nume_reg,
                 len(_pn) == 1 and _pn[0]['categorie'] == 'Grant' and _pn[0]['suma'] and _pn[0]['suma']['v'] == 386910
                 and _pn[0]['suma']['val'] == 'USD' and _pn[0]['suma']['sursa'] == 'extern' and 300e3 < _pn[0]['suma']['eur'] < 400e3,
                 [(a['categorie'], a['suma']) for a in _pn])
    _pn_l = next((a for a in _lista_l if 'Comunități reziliente prin abilitarea femeilor' in a['nume']), None)
    verifica('acordul IP ODA – PNUD: hotărârea și ordinul stau pe același rând (aceeași categorie)',
             _pn_l and {x['act'] for x in _pn_l['acte']} == {'HG430/2026', 'O147/2026'}, _pn_l and [x['act'] for x in _pn_l['acte']])

    import zipfile, functools, html as _html
    from playwright.sync_api import sync_playwright
    _srv2 = lga._Server(('127.0.0.1', 0), functools.partial(lga._Liniste, directory=str(AICI)))
    threading.Thread(target=_srv2.serve_forever, daemon=True).start()
    _baza2 = 'http://127.0.0.1:%d/' % _srv2.server_address[1]
    try:
        with sync_playwright() as _p:
            _b = _p.chromium.launch()
            for _pagina, _cauta, _gazda in (('acorduri.html', 'Sprijin pentru integrarea în UE', 'enlargement.ec.europa.eu'),
                                            ('legis_acorduri.html', 'TAMP', 'worldbank.org')):
                _pg = _b.new_page()
                _erori = []
                _pg.on('pageerror', lambda e: _erori.append(str(e)[:200]))
                _pg.route('**/*', lambda r: r.continue_() if r.request.url.startswith(_baza2) else r.abort())
                _pg.goto(_baza2 + _pagina, wait_until='networkidle', timeout=90000)
                _pg.wait_for_timeout(3000)
                _pg.fill('#seek', _cauta)
                _pg.wait_for_timeout(1200)
                _r = _pg.evaluate('''() => {
                    const tr = [...document.querySelectorAll('tr.acord')].find(t => /ext\\./.test(t.querySelector('td.c-suma').innerText));
                    if (!tr) return null;
                    const sp = tr.querySelector('td.c-suma .din-text');
                    tr.click();
                    const a = tr.nextElementSibling.querySelector('.det-suma a');
                    return {sup: sp.querySelector('sup') ? sp.querySelector('sup').textContent : '', titlu: sp.title, link: a ? a.href : '', textLink: a ? a.textContent : '',
                            detaliu: tr.nextElementSibling.querySelector('.det-suma').innerText};
                }''')
                _nume = _pagina.split('.')[0]
                verifica(_nume + ': suma din sursă externă are „ext." și explicația în titlu', _r and _r['sup'] == 'ext.' and _r['titlu'].startswith('Sursă externă'), _r)
                verifica(_nume + ': detaliul trimite la sursă, nu la un PDF legis.md',
                         _r and _gazda in _r['link'] and _r['textLink'] == 'sursa sumei' and 'din afara actelor din registru' in _r['detaliu'], _r)
                with _pg.expect_download(timeout=30000) as _d:
                    _pg.click('#export')    # vederea implicită: acordurile, filtrate pe căutare
                _fx = Path(tempfile.mkdtemp(prefix='ext_xlsx_')) / (_pagina.split('.')[0] + '-extern.xlsx')
                _d.value.save_as(str(_fx))           # openpyxl cere extensia .xlsx; fișierul temporar al descărcării n-o are
                _wsx = openpyxl.load_workbook(_fx)['Acorduri']
                shutil.rmtree(_fx.parent, ignore_errors=True)
                _ex = next((r for r in range(6, _wsx.max_row + 1) if _wsx.cell(row=r, column=23).value == 'sursă externă (nu din actele din registru)'), None)
                _hx = _wsx.cell(row=_ex, column=25).hyperlink if _ex else None
                verifica(_nume + ': exportul Excel numește sursa („sursă externă") și leagă adresa ei, cu gazda ca text',
                         _ex is not None and _hx is not None and _gazda in _hx.target and _wsx.cell(row=_ex, column=25).value == _gazda,
                         (_ex, _hx and _hx.target, _ex and _wsx.cell(row=_ex, column=25).value))
                verifica(_nume + ': rândul cu sursă externă are suma, valuta și echivalentul în euro, iar „Fragmentul din act" citează sursa',
                         _ex is not None and _wsx.cell(row=_ex, column=5).value and _wsx.cell(row=_ex, column=6).value and _wsx.cell(row=_ex, column=24).value, _ex)
                verifica(_nume + ': pagina nu a dat erori JavaScript', not _erori, _erori)
                # acordul foarte nou (IP ODA – PNUD): rândul, eticheta și fișa lui
                _pg.fill('#seek', 'Comunități reziliente')
                _pg.wait_for_timeout(1200)
                _n = _pg.evaluate('''() => {
                    const rows = [...document.querySelectorAll('tr.acord')].filter(t => t.innerText.indexOf('Comunități reziliente') >= 0);
                    if (rows.length !== 1) return {randuri: rows.length};
                    const tr = rows[0];
                    const tag = tr.querySelector('td[data-l="Categorie"] .tag');
                    const sp = tr.querySelector('td.c-suma .din-text');
                    tr.click();
                    const det = tr.nextElementSibling;
                    const ps = [...det.querySelectorAll('.det-suma')];
                    const dsuma = ps.find(x => x.innerText.indexOf('Suma acordului') === 0);
                    const dcat = ps.find(x => x.innerText.indexOf('Categorie:') === 0);
                    return {randuri: 1, eticheta: tag ? tag.innerText : '', clasa: tag ? tag.className : '', suma: tr.querySelector('td.c-suma').innerText,
                            sup: sp && sp.querySelector('sup') ? sp.querySelector('sup').textContent : '', titlu: sp ? sp.title : '',
                            dsuma: dsuma ? dsuma.innerText : '', dsumaLinkuri: dsuma ? dsuma.querySelectorAll('a').length : -1,
                            dcat: dcat ? dcat.innerText : ''};
                }''')
                verifica(_nume + ': acordul IP ODA – PNUD apare o dată, ca „Grant", cu 386 910 USD marcat „ext."',
                         _n and _n.get('randuri') == 1 and _n['eticheta'].strip() == 'Grant' and 't-grant' in _n['clasa']
                         and _n['suma'].replace('\xa0', ' ').startswith('386 910 USD') and _n['sup'] == 'ext.', _n)
                verifica(_nume + ': fișa spune că suma e dintr-o sursă externă, citează nota și arată că documentul nu e online, fără link spre legis.md',
                         _n and 'din afara actelor din registru' in _n['dsuma'] and '6 693 543 MDL' in _n['dsuma'] and 'nepublicat online' in _n['dsuma']
                         and _n['dsumaLinkuri'] == 0 and '6 693 543 MDL' in _n['titlu'], _n)
                verifica(_nume + ': fișa spune că categoria e hotărâtă de mână, cu motivul și sursa (nota Cancelariei de Stat)',
                         _n and 'hotărâtă de mână' in _n['dcat'] and 'Cancelariei de Stat' in _n['dcat'] and 'sub formă de grant' in _n['dcat'], _n)
                _pg.close()
            _b.close()
    finally:
        _srv2.shutdown()

print()
if picat:
    print(f'Au picat {len(picat)} teste.'); sys.exit(1)
print('Toate testele legis au trecut.')
