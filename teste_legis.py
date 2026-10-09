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
verifica('fiecare decizie de mână privește un act din registru',
         all(k in _brut and clasifica(pagina.repara(re.sub(r'^(Modificat|Abrogat|Suspendat)\s*', '', _brut[k]['t']).strip())) for k in lc.decizii_manuale()),
         [k for k in lc.decizii_manuale() if k not in _brut])

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
               {'id': '8', 'c': 'LP115/2025', 'pub': '01-06-2025', 'kw': [], 't': 'pentru ratificarea Acordului de finanțare dintre Republica Moldova și Comisia Europeană pentru Programul Interreg Europe'}],
              open(_tmp / 'legis_brut.json', 'w', encoding='utf-8'))
    json.dump({'acte': {'9': {'act': 'OMDED182/2025', 'sume': [], 'atas': [{'u': 'u', 'suma': {'v': 22240300000368, 'val': 'EUR', 'f': 'cont'}, 'cost': None}]},
                        '8': {'act': 'LP115/2025', 'sume': [], 'atas': [{'u': 'u', 'suma': {'v': 493103338, 'val': 'EUR', 'f': 'buget'}, 'cost': None}]}}},
              open(_tmp / 'date' / 'legis_sume.json', 'w', encoding='utf-8'))
    json.dump({'_nota': 'x', 'OMDED182/2025': {'v': 184297.33, 'val': 'EUR', 'nota': 'partea Moldovei'}, 'LP115/2025': {'ascunde': True}},
              open(_tmp / 'date' / 'sume_manual.json', 'w', encoding='utf-8'))
    _p = subprocess.run([sys.executable, str(_tmp / 'legis_pagina.py')], capture_output=True, text=True, timeout=120)
    _pag = (_tmp / 'legis_acorduri.html').read_text(encoding='utf-8') if (_tmp / 'legis_acorduri.html').exists() else ''
    _m = re.search(r'window\.__LEGIS__ = (\{.*?\});</script>', _pag, re.S)
    _a = {x['act']: x for x in json.loads(_m.group(1))['acte'].values()} if _m else {}
    verifica('suma pusă de mână (date/sume_manual.json) înlocuiește suma citită greșit',
             (_a.get('OMDED182/2025', {}).get('acord') or {}).get('v') == 184297.33, _p.stdout[-300:] + _p.stderr[-300:])
    verifica('„ascunde" scoate suma greșită din pagină', 'acord' not in _a.get('LP115/2025', {'acord': 1}))
finally:
    shutil.rmtree(_tmp, ignore_errors=True)

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
    print('Browser: exportul Excel din registru are linkuri clicabile')
    import zipfile, xml.dom.minidom, functools, html as _html
    from playwright.sync_api import sync_playwright
    _srv = lga._Server(('127.0.0.1', 0), functools.partial(lga._Liniste, directory=str(AICI)))
    threading.Thread(target=_srv.serve_forever, daemon=True).start()
    _baza = 'http://127.0.0.1:%d/' % _srv.server_address[1]
    try:
        with sync_playwright() as _p:
            _b = _p.chromium.launch()
            for _pagina in ('legis_acorduri.html', 'acorduri.html'):
                _pg = _b.new_page()
                _pg.route('**/*', lambda r: r.continue_() if r.request.url.startswith(_baza) else r.abort())
                _pg.goto(_baza + _pagina, wait_until='networkidle', timeout=90000)
                _pg.wait_for_timeout(2500)
                _pg.click('#vedBtns [data-ved="acte"]')
                _pg.wait_for_timeout(500)
                with _pg.expect_download(timeout=30000) as _d:
                    _pg.click('#export')
                _z = zipfile.ZipFile(_d.value.path())
                _foaie = _z.read('xl/worksheets/sheet1.xml').decode('utf-8')
                _cale_rel = 'xl/worksheets/_rels/sheet1.xml.rels'
                _rel = _z.read(_cale_rel).decode('utf-8') if _cale_rel in _z.namelist() else ''     # fără hyperlinkuri, fișierul nu există
                _nume = _pagina.split('.')[0]
                _adrese = re.findall(r'<t xml:space="preserve">(https?://[^<\s]+)</t>', _foaie)
                _legaturi = _foaie.count('<hyperlink ')
                verifica(_nume + ': foaia „Acte" are adrese, și fiecare e hyperlink (nu text simplu)', len(_adrese) > 100 and len(_adrese) == _legaturi, (len(_adrese), _legaturi))
                _tinte = re.findall(r'Target="([^"]+)" TargetMode="External"', _rel)
                verifica(_nume + ': fiecare hyperlink are o relație externă, spre aceeași adresă',
                         len(_tinte) == _legaturi and [_html.unescape(t) for t in _tinte] == [_html.unescape(a) for a in _adrese])
                verifica(_nume + ': stilul „hyperlink" e declarat și folosit',
                         'xl/styles.xml' in _z.namelist() and '/xl/styles.xml' in _z.read('[Content_Types].xml').decode() and 's="1"' in _foaie)
                _strict = []
                for _n in _z.namelist():
                    try:
                        xml.dom.minidom.parseString(_z.read(_n))
                    except Exception:
                        _strict.append(_n)
                verifica(_nume + ': toate părțile fișierului sunt XML valid', not _strict, _strict)
                _pg.close()
            _b.close()
    finally:
        _srv.shutdown()

print()
if picat:
    print(f'Au picat {len(picat)} teste.'); sys.exit(1)
print('Toate testele legis au trecut.')
