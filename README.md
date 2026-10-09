# Asistență externă pentru Republica Moldova

Paginile care arată, din surse oficiale, cine finanțează Republica Moldova
și unde au ajuns banii.

**Site:** https://nistor.vivi.md

| Pagina | Ce arată | Sursa |
|---|---|---|
| `index.html` | Donatori, proiecte, sume — tabloul principal, cu analize avansate și export. Butonul **Acorduri** deschide un meniu cu cele două registre de acorduri și cu „De la lege la bani" (acordurile legate de proiectele AMP) | Platforma AMP (live) + arhiva 1993–2022, verificare încrucișată cu IATI |
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

## Categoriile: grant, împrumut (credit), asistență tehnică

Fiecare act primește o categorie din titlu (`monitor_watch.classify`, extinsă pentru
legis.md în `legis_clasifica.py`). Regula, după HG 377/2018, anexa 1, pct. 9:

- **asistența financiară nerambursabilă** (și „ajutorul financiar nerambursabil”) este
  **Grant**;
- **asistența financiară rambursabilă** este **Împrumut** — „credit”, în vorbirea curentă;
  eticheta rămâne „Împrumut”, ca în regulament;
- **Asistență tehnică** rămâne asistență tehnică și când titlul o numește „nerambursabilă”:
  expertiza gratuită nu e bani dați în grant.

Ordinea în care se hotărăște (`monitor_watch.corecteaza`): 1. titlul spune „rambursabil”
sau amestecă credit și grant → Împrumut; 2. titlul numește un împrumut sau un credit →
Împrumut; 3. titlul spune „nerambursabil” → Grant; 4. titlul numește un grant → Grant;
5. doar când titlul nu spune nimic despre rambursare, **finanțatorul**: băncile de
dezvoltare (AID, BIRD, BERD, BEI, FIDA…) împrumută, agențiile de cooperare și donatorii
(UE, ONU, Suedia, Bulgaria, Guvernul României…) donează. Cuvintele din titlu bat deci
finanțatorul: grantul danez al FIDA e grant, creditul Guvernului României e împrumut.
Excepția e IFC (Corporația Financiară Internațională): ea împrumută firme private, iar
acordurile ei de cooperare cu Guvernul sunt proiecte de consultanță plătite de IFC, la care
statul contribuie în natură — deci **Asistență tehnică** (`CONSULTANTI` în `monitor_watch.py`).

„Asistență financiară” nu mai e o categorie în care rămân acte. Un act pe care nici titlul,
nici finanțatorul nu-l lămuresc — KfW, de pildă, a dat Moldovei și grant, și credit — rămâne
însă la „Asistență financiară” (mai bine neclasificat decât clasificat greșit), până îl
verifică cineva și scrie ce a găsit în **`date/categorii_manual.json`**:

    "HG241/2023": {"categorie": "Împrumut", "motiv": "...", "sursa": "https://..."}

Cheia e codul actului din legis.md, ca în `date/sume_manual.json`. „motiv” și „sursa” sunt
obligatorii (fără ele intrarea e ignorată și spusă pe ecran), iar decizia nu adaugă acte în
registru, doar le recategorizează. O cheie care nu mai corespunde niciunui act e semnalată la
fiecare rulare a `legis_pagina.py`. La ultima verificare erau trei: HG1108/2010 (KfW,
grant de 5 mil. EUR), HG241/2023 (Franța, calea ferată Chișinău–Ungheni: credit) și
AMAEIE8/2015 (acord de finanțare cu UE: grant).

Actele deja ținute în `date.json` și în `date/gov_sume.json` se pun la zi la fiecare rulare
(`monitor_watch.reclasifica`, o trecere în `gov_sume.py`): o regulă schimbată nu mai lasă
acte vechi pe categoria de ieri. La fel, sumele din atașamente se citesc după instrumentul
de azi al actului (împrumut sau grant, din categorie), nu după cel notat la prima citire.

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
| `monitor_watch.py` | Colectarea zilnică din Monitorul Oficial și regula categoriilor (grant / împrumut / asistență tehnică) |
| `import_pdf.py` | Importul din arhivele PDF ale Monitorului. Se rulează local |
| `teste.py` | Testele colectorului. Rulate de workflow înaintea colectării |
| `.github/workflows/monitor.yml` | Programarea rulării |
| `.github/workflows/legaturi.yml` | Rescrie `date/acorduri_legare.json` după fiecare colectare din Monitor sau citire a notelor Guvernului (cu Playwright) |
| `legis_acorduri.html` | Acordurile din legis.md, grupate pe acord. Datele sunt incluse în pagină |
| `legis_brut.json` | Istoricul: toate actele găsite pe legis.md, 1992–2026 |
| `legis_watch.py` | Reîmprospătarea istoricului de pe legis.md, cu browser (ocazional, de pe calculator) |
| `legis_extrage.js` | Căutările rulate în pagina legis.md |
| `legis_clasifica.py` | Ce e asistență externă, categoria, partenerul (extinde `monitor_watch.py`); citește și deciziile de mână din `date/categorii_manual.json` |
| `date/categorii_manual.json` | Categoria actelor pe care nici titlul, nici finanțatorul nu le lămuresc, hotărâtă de mână, cu motiv și sursă: `{"categorie": "Grant"\|"Împrumut"\|"Asistență tehnică", "motiv": "…", "sursa": "https://…"}`, pe codul actului din legis.md. Ce e aici bate clasificarea automată, dar nu adaugă acte; cheile care încep cu `_` sunt ignorate. Citit de `legis_pagina.py` și `legis_atasamente.py` |
| `legis_pagina.py` | Construiește `legis_acorduri.html` din `acorduri.html` + istoric + `date.json`; rulat de `monitor.yml` |
| `teste_legis.py` | Testele verificării legis.md |
| `legis_local.bat` | Aceeași verificare, rulată de pe calculatorul tău (Windows) |
| `legis_sume.py` | Sumele acordurilor, din textul integral al actelor: descarcă PDF-ul fiecărui act de pe legis.md (legi, hotărâri, ordine; fără decrete), caută „în sumă de…”, „în valoare de…” și scrie rezultatul, cu fragmentul de text, în `date/legis_sume.json`. Rulat de `legis_local.bat`; continuă de unde a rămas |
| `date/sume_manual.json` | Sume puse de mână, pe codul actului (`LP203/2022`). Citirea automată greșește uneori — o tranșă în locul sumei întregi, bugetul unui program întreg, o dată chiar un cont bancar. Ce e aici bate orice sumă citită automat: `{"v": …, "val": "EUR", "nota": "…"}` pune suma, `{"ascunde": true}` o ascunde pe cea greșită. Citit de pagină la fiecare deschidere și de `legis_pagina.py`. Un ordin venit din Monitorul Oficial apare cu un cod provizoriu, fără emitent (`O147/2026`), până ajunge în istoricul legis.md, unde are codul întreg (`OMMPS147/2026`); suma pusă sub oricare dintre cele două forme rămâne valabilă și sub cealaltă, cât timp în registru e un singur ordin cu acel număr și an. La fiecare construire a paginii, `legis_pagina.py` anunță cheile din fișier care nu mai corespund niciunui act |
| `legis_consola.js` | Aceeași citire a acordurilor atașate, dar fără nimic de instalat: se lipește în consola browserului (F12) pe www.legis.md. Citește PDF-urile cu pdf.js și pe cele scanate cu OCR (tesseract.js), ia și actele noi, și descarcă `legis_sume.json` gata de urcat în `date/`, plus `sume_lipsa.csv`. Continuă de unde a rămas. Pașii sunt scriși la începutul fișierului |
| `legis_atasamente.py` | Sumele din acordurile atașate la acte: deschide fișa fiecărui act pe legis.md, descarcă PDF-urile atașate (textul acordului), citește cu OCR pe cele scanate (dacă Tesseract e instalat) și scrie suma acordului și costul proiectului în `date/legis_sume.json`, la „atas”. Rulat de `legis_local.bat` după `legis_sume.py`; continuă de unde a rămas. Așteaptă ca fișa să-și încarce conținutul și redeschide o dată actele notate „fără atașamente” de versiunile care nu așteptau. O descărcare eșuată se notează și se trece mai departe; dacă legis.md nu mai răspunde deloc, se oprește și reia data viitoare. Ce rămâne fără sumă ajunge în `sume_lipsa.csv`, cu motivul |
| `gov_sume.py` | Sumele acordurilor din notele de argumentare ale Guvernului: citește de pe gov.md ordinea de zi a fiecărei ședințe și, pentru punctele despre acorduri, PDF-ul notei („Aspectul financiar”). Rulat zilnic de `.github/workflows/sume.yml`; rezultatul, `date/gov_sume.json`, e citit de pagina Acorduri la deschidere (sumele marcate cu G). Ședințele din ultimele zece zile se recitesc la fiecare rulare, fiindcă ordinea de zi se completează până în ziua ședinței; o notă care n-a putut fi descărcată se reîncearcă la rulările următoare |
| `legatura-amp.js` | Potrivirea dintre acorduri și proiectele AMP („De la lege la bani"): funcții pure, fără DOM, folosite de `index.html` și de teste |
| `teste_legatura.js` | Testele potrivirii: funcțiile mici, scenarii construite de mână și o verificare pe arhiva AMP + registrul real. Rulare: `node teste_legatura.js` |
| `legatura_acorduri.py` | Scrie `date/acorduri_legare.json`: deschide pagina registrului într-un browser fără ecran și îi cere lista acordurilor așa cum le vede ea (grupate, denumite, cu suma aleasă și trecută în euro). Are nevoie de Playwright |
| `date/acorduri_legare.json` | Acordurile din registru, gata grupate, un acord pe linie. Citit de pagina „De la lege la bani". Se rescrie doar când se schimbă ceva |
| `date/legaturi_amp.json` | Legăturile acord ↔ proiect AMP confirmate de oameni (vezi mai jos). Se completează de mână sau din pagină |
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

## De la lege la bani — acordurile legate de proiectele AMP

Pagina **Acorduri → De la lege la bani** (`index.html#legaturi`) caută fiecare acord din registru
printre proiectele din AMP și arată, la fiecare, cât s-a angajat și cât s-a debursat. Are și o
vedere „pe proiecte": de la proiectul AMP la acordurile lui. Lucrează cu aceleași cifre ca restul
dashboardului (arhivă + raportul live) și poate fi descărcată ca CSV.

**Cum se face o legătură.** Trei lucruri trebuie să fie de acord: *denumirea* (cuvintele rare din
denumirea acordului se regăsesc în titlul proiectului), *finanțatorul* (BEI nu se leagă de un proiect
al Japoniei) și *suma* (suma acordului coincide, cu cel mult 15% diferență, cu angajamentele
proiectului sau cu valoarea lui propusă). Nivelurile:

| Nivel | Înseamnă |
|---|---|
| **confirmat** | pus de un om în `date/legaturi_amp.json` |
| **sumă potrivită** | denumire + finanțator + sumă, fără contradicții de dată sau de fază |
| **de verificat** | denumire + finanțator, dar suma lipsește sau diferă; sau mai multe proiecte la fel de potrivite |
| **fără proiect** | nu s-a găsit nimic. Nu înseamnă că proiectul lipsește din AMP |

Doar legăturile „confirmat" și „sumă potrivită" intră în totaluri. De ce atâta prudență: de obicei
un titlu potrivit nu ajunge. „Reabilitarea drumurilor — Proiectul V" și „— Proiectul VI" au același
candidat în AMP, iar un proiect finanțat de două bănci (BEI și BERD) nu are banii unei singure bănci.
Un proiect folosit de mai multe acorduri e marcat „partajat". Semnul ⚠ apare când AMP are mult mai
puțin decât suma acordului (proiect înregistrat parțial sau acord încă nedebursat): atunci „Din
acord" arată ce scrie AMP, nu rata reală.

**Cum confirmi o legătură.** Deschide rândul unui acord și apasă *Confirmă*, *Respinge*, *Leagă*
(cu un AMP ID) sau *Nu există în AMP*. Alegerile rămân doar în browserul tău, într-un panou
„Confirmări în pregătire". Ca să apară pentru toți: *Copiază JSON*, lipești tot textul în
`date/legaturi_amp.json` și publici fișierul. Acordurile sunt identificate prin id-ul din linkul
registrului (`#acord=…`); dacă un id din fișier nu mai corespunde niciunui acord, pagina o spune.

**Linkuri în exporturile Excel.** Coloanele cu adrese („Link" din foaia „Acte" a registrelor, „Link AMP"
și linkul IATI din exportul dashboardului) se scriu ca hyperlinkuri adevărate. O adresă pusă într-o celulă ca
text simplu nu se deschide la clic în Excel sau LibreOffice, deși arată ca un link.
`python teste_legis.py --browser` verifică asta pe ambele registre.

**De unde vine lista acordurilor.** Regulile de grupare, de denumire și de sumă ale registrului sunt
lungi și potrivite pe date reale; nu le repetăm. `legatura_acorduri.py` deschide pagina
`legis_acorduri.html` într-un browser fără ecran și îi cere lista pe care ea o folosește
(`window.__ACORDURI__`, definită în `acorduri.html`). Workflow-ul `legaturi.yml` o rulează după fiecare
colectare din Monitor și după fiecare citire a notelor Guvernului. Dacă lista pare incompletă (prea
puține acorduri sau prea puține sume), nu scrie nimic și rularea apare roșie; fișierul bun rămâne.
Pe calculatorul tău: `pip install playwright`, `python -m playwright install chromium`, apoi
`python legatura_acorduri.py` (`--dry-run` arată ce ar scrie).

**Dacă pagina spune „Lista acordurilor nu s-a putut încărca".** Mesajul arată și cauza. Dacă
`date/acorduri_legare.json` nu poate fi folosit (nu e încă pe site, nu e JSON valid sau e gol), pagina
încearcă singură să citească lista direct din `legis_acorduri.html` și spune asta în rândul de stare;
eroarea apare doar când nici asta nu merge. Cauzele obișnuite: fișierul nu a fost urcat (verifică
adresa lui pe site: dacă dă 404, urcă-l sau pornește din Actions workflow-ul „Legături acord ↔ proiect
AMP"); `legis_acorduri.html` e versiunea veche, fără funcția de export; publicarea pe GitHub Pages nu s-a
terminat (durează un minut-două: apasă „Reîncearcă"); sau pagina e deschisă de pe disc (`file://`),
unde browserul nu lasă paginile să citească alte fișiere — deschide site-ul de pe adresa lui publică.

**Teste.** `node teste_legatura.js` (rulat și de `legaturi.yml`) și `python teste_legis.py --browser`
(include citirea listei din registrul real).

**Limite.** Potrivirea a fost judecată pe eșantioane, folosind suma drept martor; nu are o precizie
măsurată. Pentru acordurile fără sumă cunoscută nu există nicio confirmare automată, doar „de
verificat". Proiectele din AMP fără angajamente apar cu zero, iar legătura prin „valoarea propusă"
arată doar că proiectul există.

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
