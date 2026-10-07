# Asistență externă pentru Republica Moldova

Paginile care arată, din surse oficiale, cine finanțează Republica Moldova
și unde au ajuns banii.

**Site:** https://nistor.vivi.md

| Pagina | Ce arată | Sursa |
|---|---|---|
| `index.html` | Donatori, proiecte, sume — tabloul principal, cu analize avansate și export. Butonul **Acorduri** deschide un meniu cu cele două registre de acorduri | Platforma AMP (live) + arhiva 1993–2022, verificare încrucișată cu IATI |
| `acorduri.html` | Registrul acordurilor de asistență externă, act cu act, cu etapa la care a ajuns fiecare | Cuprinsurile Monitorului Oficial |
| `hg246.html` | Compară anexa nr. 1 la HG 246/2010 cu baza AMP și scoate în Word proiectele expirate | Documentul încărcat de utilizator + AMP |

## Registrul acordurilor — cum se actualizează

Un workflow GitHub Actions rulează în fiecare zi lucrătoare la 06:00 UTC
(09:00 la Chișinău vara, 08:00 iarna), citește edițiile recente ale Monitorului
Oficial, extrage actele de finanțare externă și le publică. Nu e nevoie ca
vreun calculator să fie pornit.

Fiecare rulare lasă un commit. Când apar acte, mesajul lui e „Acte noi”. Când
nu apare nimic, e „Verificare zilnică, fără acte noi” și atinge doar `date.json`
și `date/stare.json`: cele două poartă data ultimei verificări, pe care paginile
o arată și o compară cu ziua de azi. Restul fișierelor (pagina legis, fluxul
RSS, harta site-ului, datele deschise) se schimbă doar când apare ceva nou.

Înainte de colectare rulează `teste.py`. Dacă testele pică, colectarea nici nu
pornește: o rulare oprită se vede imediat în fila Actions, un registru stricat
ar trece neobservat.

Scriptul mai face trei lucruri care nu se văd:

**Recuperează edițiile sărite.** Prima pagină a Monitorului arată doar zece
ediții. Dacă automatizarea stă oprită mai mult, unele ies din listă înainte de
a fi citite. ID-urile fiind consecutive, orice număr lipsă e o ediție necitită
— scriptul o cere direct. După cinci încercări nereușite o consideră
inexistentă și nu o mai cere; numerotarea Monitorului are găuri reale, fiindcă
edițiile speciale și volumele suplimentare ocupă numere proprii.

**Semnalează tăcerea.** Dacă ultima colectare e mai veche de patru zile,
`acorduri.html` scrie asta cu roșu în antet. Pragul ține cont că rularea e
programată doar în zilele lucrătoare. Registrul din legis.md face același
lucru, cu data din `date/stare.json`.

**Se oprește la timp.** Când monitorul.gov.md răspunde greu, scriptul nu mai
așteaptă până îl oprește GitHub (o oprire forțată nu apucă să salveze nimic):
după șapte minute de citit se oprește singur, salvează ce are și lasă restul
edițiilor pe a doua zi. O pagină care nu există (404) nu mai e cerută de trei
ori la rând.

Două acte cu același număr și aceeași dată, dar de la emitenți diferiți — o
hotărâre de Guvern nr. 10 și un ordin nr. 10 din aceeași zi — sunt ținute ca
două acte: registrul le deosebește și după tip, nu doar după număr și dată.

## Fișiere

| Fișier | Rol |
|---|---|
| `index.html` | Pagina principală: donatori și proiecte, analize, export, IATI |
| `arhiva.js` | Arhiva AMP (1993–2022), încărcată de `index.html`. Separată ca s-o țină browserul în cache |
| `traduceri-en.js` | Dicționarele EN mari (titluri de proiecte, beneficiari), încărcate de `index.html` |
| `fisa-donator.js` | Fișa donatorului: clic pe un nume de donator sau link `index.html#fisa=<nume>` |
| `cautare.js` | Căutarea globală din bara de navigare (lupă, tasta / sau Ctrl+K), încărcată la prima folosire |
| `amp-logo.png` | Sigla AMP din subsolul paginii principale |
| `amp-linkuri.js` | Face din fiecare AMP ID un link spre fișa proiectului pe amp.gov.md. Corespondența AMP ID → identificator intern vine din raportul public AMP, prin proxy-ul amp.vivi.md, și se ține în browser o zi |
| `amp-vechi.json` | AMP ID → activityId pe serverul vechi AMP (87.255.68.120:8888), pentru cele 3.008 proiecte ale arhivei. Construit o singură dată, deschizând paginile publice ale serverului vechi |
| `acorduri.html` | Registrul acordurilor. Citește `date.json` la fiecare deschidere |
| `hg246.html` | Comparația cu anexa HG 246. Citește `amp-arhiva.json` |
| `meniu.js` | Bara de navigare comună, aceeași pe toate paginile (Donatori, Analize, Export, IATI, Acorduri, HG 246). Un buton nou se adaugă o singură dată, aici |
| `traducere.js` | Engleza pentru paginile de acorduri, HG 246 și Despre: dicționar de fraze ale interfeței; denumirile oficiale ale actelor rămân în română |
| `despre.html` | Despre date și metodologie: surse, termeni, calcule, limite, date deschise, RSS (în română și engleză) |
| `date_deschise.py` | Scrie `date/acorduri_monitor.csv/.json`, `date/acorduri_legis.csv/.json`, `date/cautare.json` (indexul căutării), `rss.xml`, `sitemap.xml` și `date/stare.json` (data ultimei verificări, citită de registrul legis.md la deschidere); rulat de `monitor.yml`. Doar `date/stare.json` se schimbă în fiecare zi; celelalte, când apar acte noi |
| `robots.txt` | Indică motoarelor de căutare harta site-ului (`sitemap.xml`) |
| `xlsx.min.js` | Biblioteca SheetJS pentru Excel, încărcată doar la descărcare (nu la fiecare deschidere a paginii) |
| `unelte.js` | Roata dințată de pe fiecare panou (meniu cu „Copiază ca imagine" și „Descarcă datele (CSV)"), linkul care păstrează filtrele (`?ani=…&don=…`), raportul PDF pe o pagină, indicatorul de prospețime a datelor și comparația între perioade din „Analize avansate" |
| `html2canvas.min.js` | Biblioteca html2canvas, care transformă un panou în imagine; încărcată doar la primul „Copiază" sau „Raport PDF" |
| `favicon.svg`, `apple-touch-icon.png`, `og.png`, `404.html` | Iconița site-ului (logoul: harta Moldovei cu cele trei fluxuri), iconița pentru ecranul telefonului, imaginea de previzualizare a linkurilor, pagina „nu există” |
| `donatori.html` | Redirecționare către `index.html`, pentru linkurile vechi |
| `date.json` | Registrul acordurilor. Actualizat automat de workflow |
| `amp-arhiva.json` | Arhiva AMP, doar câmpurile de care are nevoie `hg246.html` |
| `monitor_watch.py` | Colectarea zilnică din Monitorul Oficial |
| `import_pdf.py` | Importul din arhivele PDF ale Monitorului. Se rulează local |
| `teste.py` | Testele colectorului. Rulate de workflow înaintea colectării |
| `.github/workflows/monitor.yml` | Programarea rulării |
| `legis_acorduri.html` | Acordurile din legis.md, grupate pe acord. Datele sunt incluse în pagină |
| `legis_brut.json` | Istoricul: toate actele găsite pe legis.md, 1992–2026 |
| `legis_watch.py` | Reîmprospătarea istoricului de pe legis.md, cu browser (ocazional, de pe calculator) |
| `legis_extrage.js` | Căutările rulate în pagina legis.md |
| `legis_clasifica.py` | Ce e asistență externă, categoria, partenerul (extinde `monitor_watch.py`) |
| `legis_pagina.py` | Construiește `legis_acorduri.html` din `acorduri.html` + istoric + `date.json`; rulat de `monitor.yml` |
| `teste_legis.py` | Testele verificării legis.md |
| `legis_local.bat` | Aceeași verificare, rulată de pe calculatorul tău (Windows) |
| `legis_sume.py` | Sumele acordurilor, din textul integral al actelor: descarcă PDF-ul fiecărui act de pe legis.md (legi, hotărâri, ordine; fără decrete), caută „în sumă de…”, „în valoare de…” și scrie rezultatul, cu fragmentul de text, în `date/legis_sume.json`. Rulat de `legis_local.bat`; continuă de unde a rămas |
| `date/sume_manual.json` | Sume puse de mână, pe codul actului (`LP203/2022`). Citirea automată greșește uneori — o tranșă în locul sumei întregi, bugetul unui program întreg, o dată chiar un cont bancar. Ce e aici bate orice sumă citită automat: `{"v": …, "val": "EUR", "nota": "…"}` pune suma, `{"ascunde": true}` o ascunde pe cea greșită. Citit de pagină la fiecare deschidere și de `legis_pagina.py`. Un ordin venit din Monitorul Oficial apare cu un cod provizoriu, fără emitent (`O147/2026`), până ajunge în istoricul legis.md, unde are codul întreg (`OMMPS147/2026`); suma pusă sub oricare dintre cele două forme rămâne valabilă și sub cealaltă, cât timp în registru e un singur ordin cu acel număr și an. La fiecare construire a paginii, `legis_pagina.py` anunță cheile din fișier care nu mai corespund niciunui act |
| `legis_consola.js` | Aceeași citire a acordurilor atașate, dar fără nimic de instalat: se lipește în consola browserului (F12) pe www.legis.md. Citește PDF-urile cu pdf.js și pe cele scanate cu OCR (tesseract.js), ia și actele noi, și descarcă `legis_sume.json` gata de urcat în `date/`, plus `sume_lipsa.csv`. Continuă de unde a rămas. Pașii sunt scriși la începutul fișierului |
| `legis_atasamente.py` | Sumele din acordurile atașate la acte: deschide fișa fiecărui act pe legis.md, descarcă PDF-urile atașate (textul acordului), citește cu OCR pe cele scanate (dacă Tesseract e instalat) și scrie suma acordului și costul proiectului în `date/legis_sume.json`, la „atas”. Rulat de `legis_local.bat` după `legis_sume.py`; continuă de unde a rămas. Așteaptă ca fișa să-și încarce conținutul și redeschide o dată actele notate „fără atașamente” de versiunile care nu așteptau. O descărcare eșuată se notează și se trece mai departe; dacă legis.md nu mai răspunde deloc, se oprește și reia data viitoare. Ce rămâne fără sumă ajunge în `sume_lipsa.csv`, cu motivul |
| `gov_sume.py` | Sumele acordurilor din notele de argumentare ale Guvernului: citește de pe gov.md ordinea de zi a fiecărei ședințe și, pentru punctele despre acorduri, PDF-ul notei („Aspectul financiar”). Rulat zilnic de `.github/workflows/sume.yml`; rezultatul, `date/gov_sume.json`, e citit de pagina Acorduri la deschidere (sumele marcate cu G). Ședințele din ultimele zece zile se recitesc la fiecare rulare, fiindcă ordinea de zi se completează până în ziua ședinței; o notă care n-a putut fi descărcată se reîncearcă la rulările următoare |
| `raport_legis.md`, `jurnal_legis.md` | Raportul ultimei rulări și istoricul zilelor cu acte noi. Le scrie `legis_watch.py`; apar în repository după prima rulare reușită a lui `legis_local.bat` |
| `CNAME` | Domeniul propriu |

## Registrul din legis.md — cum se actualizează

`legis_acorduri.html` e construită din două surse:

- **istoricul** din Registrul de stat (legis.md), 1992 până azi, extras o dată
  în `legis_brut.json`;
- **actele noi** din Monitorul Oficial (`date.json`), colectate zilnic de
  workflow-ul existent `monitor.yml`.

Orice lege, hotărâre sau decret apare întâi în Monitorul Oficial și abia apoi
în legis.md, deci actele noi nu trebuie căutate pe legis.md. După fiecare
colectare, `monitor.yml` rulează `legis_pagina.py`, care reconstruiește pagina
și o rescrie doar dacă i s-a schimbat conținutul. Data ultimei verificări nu e
un motiv de rescriere: pagina o citește la deschidere din `date/stare.json`.
Totul rulează pe GitHub; nimic de instalat.

Actele venite din Monitor apar cu sursa „MO …", iar numărul lor duce la
căutarea pe legis.md după număr și data adoptării. Actele din istoric duc
direct la fișa lor pe legis.md.

legis.md însuși nu poate fi citit de pe serverele GitHub: e protejat de
Cloudflare („nu sunt robot"). Pentru o reîmprospătare completă a istoricului,
ocazional, se poate rula de pe calculator `legis_local.bat` (cere Python, Git
și `pip install playwright requests beautifulsoup4`).

Testele: `python teste_legis.py` (rapid) sau `python teste_legis.py --browser`.

## Importul din arhive PDF

Colectarea zilnică ajunge doar la edițiile de pe prima pagină a Monitorului.
Perioadele mai vechi se adaugă din arhivele PDF, local:

```
python3 import_pdf.py CALEA/CATRE/FOLDER_CU_PDF-URI --dry-run
python3 import_pdf.py CALEA/CATRE/arhiva.zip --dry-run
```

Primește un folder, un singur PDF sau o arhivă. Arhivele `.zip` le desface
singur. Pentru `.rar` și `.7z` are nevoie de un program deja instalat (7-Zip,
WinRAR, `unrar` sau `tar`-ul din Windows 10/11); dacă nu găsește niciunul, spune
asta și atunci desfaci arhiva într-un folder și îi dai folderul. Scoți
`--dry-run` când ești mulțumit de ce vezi. Are nevoie de un extractor de text:
`poppler-utils`, `pdfplumber` sau `pypdf`.

Ediția rusească a fiecărui număr e sărită automat.

## Activare, o singură dată

1. **Settings → Pages** → Source: Deploy from a branch → Branch `main`,
   folder `/(root)`
2. **Settings → Actions → General** → la „Workflow permissions" alege
   **Read and write permissions**

Fără pasul 2, workflow-ul rulează dar nu poate face commit.

## Verificare

În fila **Actions** vezi fiecare rulare. Verde a mers, roșu deschide-o și
citește pasul marcat.

Dacă vrei alt orar, schimbă linia `cron` din workflow. Ora e în UTC.

## Ce nu acoperă registrul

Acoperirea începe în ianuarie 2024. Acordurile pornite înainte apar cu primele
etape marcate cu semnul întrebării — nu fiindcă n-au avut loc, ci fiindcă
actele lor sunt dinaintea perioadei acoperite.

Intrarea în vigoare a acordului însuși nu se poate urmări din cuprins: ordinul
ministrului afacerilor externe care o anunță e colectiv și nu numește acordul.
Data afișată e cea la care a intrat în vigoare legea de ratificare.

Majoritatea actelor provin din arhivele PDF, iar linkul lor duce la căutarea
generală a Monitorului, nu la ediția exactă.
