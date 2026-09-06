# Ce se urcă pe GitHub

Repository: `igornistor2013-wq/acorduri` · Site: `nistor.vivi.md`

## Ce s-a schimbat

Registrul acoperă acum **12.01.2024 – 04.09.2026**, doi ani și opt luni fără
întrerupere: 326 de acte grupate în 92 de acorduri, de la 16 finanțatori.

| Fișier | De ce se schimbă |
|---|---|
| `date.json` | 326 de acte, cu tot 2024 integrat |
| `monitor_watch.py` | Bank Gospodarstwa Krajowego recunoscut ca Polonia; avizele Guvernului la proiecte de lege excluse; toleranță la „Reconstrucții" scris greșit în titlurile oficiale |
| `import_pdf.py` | data ediției luată din numele fișierului, cu coperta ca autoritate finală; ediții în mai multe volume (150a-176); ediții speciale fără număr; titluri care încep cu localitatea, respinse ca potriviri greșite |
| `acorduri.html` | data de început a acoperirii se calculează din date, nu mai e scrisă de mână |
| `index.html` | descărcarea IATI cere patru pagini deodată și arată progresul |

Nu se schimbă și pot fi sărite: `donatori.html` și
`.github/workflows/monitor.yml`.

## Pașii

**1. Dezarhivează.** GitHub nu despachetează arhive.

**2. Urcă cele cinci fișiere din rădăcină** — `date.json`, `acorduri.html`,
`index.html`, `monitor_watch.py`, `import_pdf.py`. `Add file` →
`Upload files`, le tragi pe toate odată, `Commit changes`.

**3. Verifică** pe `https://nistor.vivi.md/acorduri.html`, cu Ctrl+F5.

Ar trebui să vezi 92 de acorduri, iar filtrul pe an să ofere 2024, 2025 și
2026.

## Despre `date.json`

Conține și actul colectat de automatizare pe 4 septembrie — un ordin privind
amendamentul la acordul cu FICR. L-am preluat de pe GitHub și l-am unit cu
importul din arhivele 2024, ca să nu se piardă la suprascriere. Am păstrat de
la workflow și lista edițiilor văzute, și ora ultimei rulări.

În șirul edițiilor nu există goluri.

## Ce a rămas de făcut

Semnele de întrebare din coloana etapelor au scăzut de la 50 la 38 — sunt
acordurile începute înainte de 12 ianuarie 2024. Se închid doar cu arhivele
din 2023.

Linkurile din registru duc în majoritate la căutarea generală a Monitorului,
nu la ediția exactă, fiindcă actele au venit din PDF-uri. Se repară rulând
local:

    python3 monitor_watch.py --backfill 3000 3311

apoi urcând `date.json` rezultat.
