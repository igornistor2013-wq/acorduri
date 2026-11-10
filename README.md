# Asistență externă pentru Republica Moldova

Paginile care arată, din surse oficiale, cine finanțează Republica Moldova
și unde au ajuns banii.

**Site:** https://nistor.vivi.md

| Pagina | Ce arată | Sursa |
|---|---|---|
| `index.html` | Donatori, proiecte, sume — tabloul principal, cu analize avansate și export. Butonul **Acorduri** deschide un meniu cu cele două registre de acorduri, cu „De la lege la bani" (acordurile legate de proiectele AMP) și cu „Debursări pe acorduri" | Platforma AMP (live) + arhiva 1993–2022, verificare încrucișată cu IATI |
| `acorduri.html` | Registrul acordurilor de asistență externă, act cu act, cu etapa la care a ajuns fiecare | Cuprinsurile Monitorului Oficial |
| `debursari.html` | Debursări pe acorduri: pe donatori, la bifarea unuia apar proiectele lui (denumire, obiectivele proiectului, data efectivă de începere, data finalizării, tip de finanțare, suma proiectului) și debursările introduse de mână după un cod de acces; Excel pe donator sau total | Registrul legis.md (`date/acorduri_legare.json`) + obiectivele din `date/proiecte_manual.json` + datele din AMP + ce introduc oamenii în `date/debursari.json` |
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

Fiecare act primește o categorie din titlu (`monitor_watch.classify`, extinsă în
`legis_clasifica.py`; ambele registre trec actele prin același filtru, vezi mai jos).
Regula, după HG 377/2018, anexa 1, pct. 9:

- **asistența financiară nerambursabilă** (și „ajutorul financiar nerambursabil”) este
  **Grant**;
- **asistența financiară rambursabilă** este **Împrumut** — „credit”, în vorbirea curentă;
  eticheta rămâne „Împrumut”, ca în regulament;
- **Asistență tehnică** rămâne asistență tehnică și când titlul o numește „nerambursabilă”:
  expertiza gratuită nu e bani dați în grant.
- **Cooperarea tehnică** dintre guverne — înțelegerea prin schimb de note pentru un expert german
  detașat pe lângă un viceprim-ministru, un proiect de consultanță — e tot **Asistență tehnică**:
  statul primește expertiză, nu bani, deci finanțatorul nu hotărăște (Germania dă și granturi).
  „Cooperarea tehnică și financiară” e și una, și alta și rămâne la finanțator. La fel, acordul cu
  o agenție de dezvoltare (elvețiană, austriacă, cehă) pentru un proiect e asistență tehnică, ca
  memorandumurile ei; un „acord de grant” sau „de finanțare” cu aceeași agenție își păstrează
  cuvântul. Același instrument al UE, „Facilitatea de cooperare tehnică”, se tratează la fel cu
  „de” ca și cu „pentru”.

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

Cheia e codul actului din legis.md, ca în `date/sume_manual.json`. Un act foarte nou, care e
încă doar în Monitorul Oficial și n-are fișă pe legis.md, are codul scos din numărul și tipul
lui (`HG430/2026`); ordinul — cu codul provizoriu, fără emitent (`O147/2026`). „motiv” și
„sursa” sunt obligatorii (fără ele intrarea e ignorată și spusă pe ecran); „sursa” poate fi și
descrierea unui document nepublicat online. Decizia nu adaugă acte în registru, doar le
recategorizează, și se aplică în ambele registre (legis.md și Monitor) și în datele deschise.
Toate actele unui acord au nevoie de aceeași decizie, altfel acordul apare pe două rânduri.
O cheie care nu mai corespunde niciunui act e semnalată la fiecare rulare a `legis_pagina.py`.
La ultima verificare erau șapte: HG1108/2010 (KfW, grant de 5 mil. EUR), HG241/2023 (Franța,
calea ferată Chișinău–Ungheni: credit), AMAEIE8/2015 (acord de finanțare cu UE: grant),
HG430/2026 și O147/2026 (acordul IP ODA – PNUD „Comunități reziliente prin abilitarea
femeilor”: nota Cancelariei de Stat spune că PNUD dă asistență „nerambursabilă, sub formă de
grant”, iar titlul hotărârii nu spune nimic despre rambursare), HG683/2024 (InfoTrustAlliance
Moldova, ITA-M: cooperare tehnică, nu grant) și HG654/2024 (proiectul moldo-elvețian în
domeniul proprietății intelectuale, MSIP, finanțat de Elveția prin SECO: datele primite pentru
registru îl numesc grant, de 794 407,37 EUR, deși titlul hotărârii vorbește de „asistență
tehnică” și nu spune că banii s-ar rambursa).

Actele deja ținute în `date.json` și în `date/gov_sume.json` se pun la zi la fiecare rulare
(`monitor_watch.reclasifica`, o trecere în `gov_sume.py`): o regulă schimbată nu mai lasă
acte vechi pe categoria de ieri. La fel, sumele din atașamente se citesc după instrumentul
de azi al actului (împrumut sau grant, din categorie), nu după cel notat la prima citire.

**Un singur filtru pentru cele două registre.** Ce act intră în registru hotărăște
`monitor_watch.clasifica_registru`, care trece titlul prin clasificatorul din `legis_clasifica.py`
(fără cuvântul de tip din față, „Hotărâre”, „Lege”, „Ordin”, cum îl dă legis.md). Înainte erau două
filtre și se îndepărtaseră: acordurile-cadru de împrumut ale CEB, acordurile de facilitate de
împrumut, înțelegerile prin schimb de note, memorandumurile cu agențiile de dezvoltare și garanțiile
de stat le știa doar legis.md. Din ianuarie 2024, registrul Monitorului a ratat astfel 52 de acte (14
despre acorduri-cadru CEB, 5 despre facilități de împrumut, 9 schimburi de note, 15 memorandumuri,
3 amendamente la acordul de asistență cu Statele Unite, 4 acorduri cu agenția elvețiană sau cu GIZ, 2
garanții de stat), între ele hotărârea publicată la 16 octombrie 2026 pentru Acordul-cadru de împrumut
„Modernizarea instituțiilor de învățământ profesional tehnic”. Cauza cea mai simplă a fost un tipar:
„acord de împrumut” nu trecea de „-cadru”; tiparele de bază primesc acum „acord-cadru”, cu cratimă,
semn lung sau spațiu. Pe cele 333 de acte deja în `date.json` filtrul nou dă aceeași categorie și
același partener ca cel vechi, deci niciun rând existent nu se schimbă; refuză, în schimb, câteva
feluri de zgomot pe care cel vechi le lăsa să treacă (instituirea unui grup de negociere, „contractele
de credit pentru consumatori”). Dacă `legis_clasifica.py` lipsește, colectarea merge mai departe pe
regulile de bază și scrie pe ecran ce nu va prinde.

Colectarea citește la fiecare rulare doar ultimele zece ediții, așa că o regulă corectată nu aduce
singură actele din edițiile care au ieșit de pe prima pagină. Se refac din ediții cu
`python3 monitor_watch.py --backfill PRIMUL ULTIMUL` (identificatorii edițiilor sunt în `date.json`,
la `editii_vazute`), iar pentru perioadele mai vechi, din arhivele PDF, cu `python3 import_pdf.py`;
ambele folosesc acum același filtru. Testele din `teste.py` (`test_acord_cadru`,
`test_acelasi_filtru_ca_legis`, `test_paritate_cu_legis_md`) pică dacă Monitorul refuză un act pe
care legis.md îl primește.

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
| `acorduri.html` | Registrul acordurilor. Citește `date.json` la fiecare deschidere. Sumele acordurilor le ia din patru locuri, în ordinea: documentul atașat actului pe legis.md, titlul, textul actului, nota Guvernului. Primele două cercetări (`date/legis_sume.json`, `date/sume_manual.json`) sunt făcute pe actele din legis.md; ca registrul din Monitor să le folosească și el, fiecare act primește fișa lui legis.md din `date/legaturi_legis.json` (cheia actului din Monitor → `doc_id` legis.md). Un act foarte nou, încă fără fișă pe legis.md, primește sumele și categoria hotărâte de mână după codul scos din numărul și tipul lui. Butonul „Excel” scrie un fișier stilizat cu `xlsx-stil.js` (încărcat la primul clic) sau, dacă acesta lipsește, vechea foaie simplă: vezi „Exportul Excel din registrele de acorduri” |
| `hg246.html` | Comparația cu anexa HG 246. Citește `amp-arhiva.json` |
| `meniu.js` | Bara de navigare comună, aceeași pe toate paginile (Donatori, Analize, Export, IATI, Acorduri, HG 246). Un buton nou se adaugă o singură dată, aici. Meniul „Acorduri” are trei opțiuni, în ordinea: Debursări pe acorduri, Acorduri · legis.md, Acorduri · Monitorul Oficial; „De la lege la bani” nu mai e în meniu (vederea există în continuare la `index.html#legaturi`, ca adresă directă). Etichetele se refac la schimbarea limbii după poziție (lista `txt` din `Meniu.limba`): ordinea de acolo trebuie să urmeze ordinea opțiunilor |
| `traducere.js` | Engleza pentru paginile de acorduri, HG 246 și Despre: dicționar de fraze ale interfeței; denumirile oficiale ale actelor rămân în română |
| `despre.html` | Despre date și metodologie: surse, termeni, calcule, limite, date deschise, RSS (în română și engleză) |
| `date_deschise.py` | Scrie `date/acorduri_monitor.csv/.json`, `date/acorduri_legis.csv/.json`, `date/cautare.json` (indexul căutării), `rss.xml`, `sitemap.xml` și `date/stare.json` (data ultimei verificări, citită de registrul legis.md la deschidere); rulat de `monitor.yml`. Categoria din fișierele CSV/JSON ține cont de deciziile de mână din `date/categorii_manual.json`, ca în pagini. Doar `date/stare.json` se schimbă în fiecare zi; celelalte, când apar acte noi |
| `robots.txt` | Indică motoarelor de căutare harta site-ului (`sitemap.xml`) |
| `xlsx.min.js` | Biblioteca SheetJS, încărcată doar la descărcare (nu la fiecare deschidere a paginii): pentru butonul „Export” (proiectele cu filtre și coloane alese) și pentru exportul rapid IATI. Graficele și tabelele din panouri se scriu cu `xlsx-stil.js` |
| `unelte.js` | Roata dințată de pe fiecare panou (meniu cu „Copiază ca imagine", „Descarcă Excel (.xlsx)" și „Date brute (CSV)"; construiește foaia Excel din datele pe care panoul le-a înregistrat, vezi secțiunea „Exporturile Excel"), linkul care păstrează filtrele (`?ani=…&don=…`), raportul PDF pe o pagină și indicatorul de prospețime a datelor |
| `xlsx-stil.js` | Scriitorul de fișiere `.xlsx` (ZIP + XML, fără bibliotecă): titlu și context, antet cu filtre, formate de număr, dungi, bare în celule, scară de culoare, rând de total cu formule `SUBTOTAL`, hyperlinkuri, note și grafic Excel nativ. Scrie și fișiere cu **mai multe foi** (`foi: […]`): nume de foaie unice (cel mult 31 de caractere), linkuri de la o foaie la alta (adresa `#Numele foii`), culoare pe fila foii; graficele se numerotează pe tot fișierul. Încărcat la primul export (`unelte.js` îl cere cu aceeași versiune `?v=` ca el). Pentru tabelele late ale registrelor mai știe: coloane înghețate, benzi de grupe, culori pe etichete (formatare condițională), înălțime de rând limitată și tipărire pe mai multe pagini în lățime (vezi „Exportul Excel din registrele de acorduri”) |
| `sectoare.js` | Panoul „Donatori → sectoare · cu proiectele fiecărui sector” din „Analize avansate”: diagrama donatori ↔ sectoare, lista proiectelor pe fiecare sector și exportul Excel cu mai multe foi (vezi secțiunea „Donatori → sectoare”). Prima parte (agregări, filtre, diagrama ca text SVG, datele pentru Excel) nu atinge pagina și se testează cu Node; a doua desenează în pagină. Încărcat din `index.html` înaintea lui `unelte.js` |
| `html2canvas.min.js` | Biblioteca html2canvas, care transformă un panou în imagine; încărcată doar la primul „Copiază" sau „Raport PDF" |
| `favicon.svg`, `apple-touch-icon.png`, `og.png`, `404.html` | Iconița site-ului (logoul: harta Moldovei cu cele trei fluxuri), iconița pentru ecranul telefonului, imaginea de previzualizare a linkurilor, pagina „nu există” |
| `donatori.html` | Redirecționare către `index.html`, pentru linkurile vechi |
| `date.json` | Registrul acordurilor. Actualizat automat de workflow |
| `amp-arhiva.json` | Arhiva AMP, doar câmpurile de care are nevoie `hg246.html` |
| `monitor_watch.py` | Colectarea zilnică din Monitorul Oficial și regula categoriilor (grant / împrumut / asistență tehnică); ce act intră în registru hotărăște `clasifica_registru`, filtrul comun cu legis.md |
| `import_pdf.py` | Importul din arhivele PDF ale Monitorului, cu același filtru ca citirea de pe site. Se rulează local |
| `teste.py` | Testele colectorului, inclusiv paritatea filtrului cu legis.md (acord-cadru, schimburi de note, memorandumuri, garanții de stat). Rulate de workflow înaintea colectării |
| `.github/workflows/monitor.yml` | Programarea rulării |
| `curs_bce.py` | Actualizează cursul valutar: citește cursurile zilnice de referință ale BCE (`eurofxref-daily.xml`) și le scrie în `acorduri.html` și `legis_acorduri.html` (`CURS_DATA`, `PER_EUR`) și în `date/acorduri_legare.json` (`curs_data`, `cursuri`, echivalentul în euro al sumelor). DST se calculează din coșul FMI, ROL din RON, DEM și ECU sunt fixe. Nu schimbă nimic dacă data BCE nu e mai nouă decât cea din pagină, și refuză (cu eroare) cursuri care nu par bune. Rulare: `python curs_bce.py [fisier.xml]` |
| `teste_curs.py` | Testele lui `curs_bce.py`, fără rețea (XML simulat, pe o copie a fișierelor): citirea XML-ului, data în română, DST și ROL, scrierea în cele trei fișiere, refuzul cursurilor greșite, că fișierele din repository au aceleași cursuri. Rulare: `python teste_curs.py` |
| `.github/workflows/curs.yml` | Rulează `curs_bce.py` în fiecare dimineață (05:20 UTC) și publică fișierele schimbate; pornire manuală posibilă |
| `.github/workflows/legaturi.yml` | Rescrie `date/acorduri_legare.json` după fiecare colectare din Monitor sau citire a notelor Guvernului (cu Playwright) |
| `legis_acorduri.html` | Acordurile din legis.md, grupate pe acord. Datele sunt incluse în pagină |
| `legis_brut.json` | Istoricul: toate actele găsite pe legis.md, 1992–2026 |
| `legis_watch.py` | Reîmprospătarea istoricului de pe legis.md, cu browser (ocazional, de pe calculator) |
| `legis_extrage.js` | Căutările rulate în pagina legis.md |
| `legis_clasifica.py` | Ce e asistență externă, categoria, partenerul (extinde `monitor_watch.py`) — filtrul ambelor registre: colectorul Monitorului îl apelează prin `monitor_watch.clasifica_registru`; citește și deciziile de mână din `date/categorii_manual.json` |
| `date/categorii_manual.json` | Categoria actelor pe care nici titlul, nici finanțatorul nu le lămuresc, hotărâtă de mână, cu motiv și sursă: `{"categorie": "Grant"\|"Împrumut"\|"Asistență tehnică", "motiv": "…", "sursa": "https://…"}`, pe codul actului din legis.md (un act foarte nou, doar din Monitor, are codul scos din număr și tip: `HG430/2026`, ordinul `O147/2026`). Ce e aici bate clasificarea automată, dar nu adaugă acte; cheile care încep cu `_` sunt ignorate. Citit de `legis_pagina.py`, `legis_atasamente.py`, `date_deschise.py` și de registrul din Monitor (`acorduri.html`); fișa acordului spune că categoria e hotărâtă de mână, cu motivul și sursa |
| `date/contopiri_manual.json` | Rândurile din registre (legis.md și Monitor) pe care regula automată de grupare nu le unește sau le unește greșit, hotărâte de mână: `{"uneste": [{"acte": ["LP148/2025", "HG183/2025"], "nota": "…", "nume": "…"}], "muta": [{"acte": ["LP58/2010", "DP242/2010"], "langa": "HG849/2009", "nota": "…"}]}`. Același acord ajunge uneori pe mai multe rânduri, fiindcă hotărârea de inițiere, hotărârea pentru proiectul de lege, legea și decretul își scriu titlul diferit (cu sau fără suma din titlu, cu altă denumire a proiectului). `uneste` pune pe un singur rând rândurile care conțin actele numite: rămâne rândul primului act găsit, celelalte se golesc în el, iar `nume` (opțional) îi dă altă denumire; cu un singur act în listă, `uneste` doar redenumește rândul (de pildă patru tranșe ale aceluiași program, care arătau la fel în listă și se deosebeau doar prin coada titlului, tăiată pe ecran, sau un titlu care purta numele unui ministru). `muta` scoate actele din rândul lor și le pune lângă actul `langa` (pe un rând nou, dacă `langa` lipsește): de pildă finanțarea suplimentară a unui proiect, care ajunsese pe rândul creditului de bază, sau actele altui acord, amestecate pe același rând (addendumul la programul TACIS stătea cu cel la programul pentru zonele rurale, fiindcă titlul lor dă aceeași denumire automată; contractul BEI din 2007 stătea cu „Moldova drumuri IV”; tranșele anuale japoneze 2KR, fiecare un schimb de note separat, stăteau pe un singur rând). Rândul din care pleacă un act își ia denumirea de la primul act rămas. Se aplică întâi `muta`, apoi `uneste`. Actele se numesc după codul din legis.md (`LP148/2025`), ca în `date/sume_manual.json`; un act care nu mai e în registru se sare, iar un fișier lipsă sau stricat nu schimbă nimic. Rândul unit își refac etapele, partenerii, data semnării (cea mai veche) și suma din titlu (a celui mai vechi act care are una). Rămân separate, deliberat: finanțările suplimentare și amendamentele care majorează un acord (au suma lor; un amendament care nu schimbă suma, ca amendamentul nr. 1 la memorandumul ceh RESTART, stă pe rândul acordului), două facilități diferite ale aceluiași finanțator (de pildă cele două facilități AFD de câte 40 mil. EUR) și cazurile în care o lege ratifică mai multe acorduri deodată. **Atenție la sumele de mână:** o sumă din `date/sume_manual.json` bate orice altă sumă din rând, iar cu mai multe sume de mână pe același rând câștigă cea a celui mai vechi act. De aceea un fragment unit cu acordul lui de bază nu mai poartă propria sumă sau marcajul `fara_total`: rândul întreg ar ieși din totaluri sau ar arăta suma greșită. Identificatorul rândului (`id` în `date/acorduri_legare.json`, linkul `#acord=`) vine de la cel mai vechi act al rândului; un link `#acord=` vechi rămâne valabil, pentru că se potrivește cu orice act din rând. Fișierul e citit de `acorduri.html` la fiecare deschidere; când se schimbă, pornește și `legaturi.yml` |
| `legis_pagina.py` | Construiește `legis_acorduri.html` din `acorduri.html` + istoric + `date.json`; rulat de `monitor.yml` |
| `teste_legis.py` | Testele verificării legis.md. Cu `--browser` deschide și cele două registre (legis.md și Monitor) și verifică exportul lor Excel: fișierele descărcate sunt citite cu openpyxl (antet, un rând pe acord, totalul în euro față de panou sau față de datele paginii, filtre, vederea „Acte”, linkuri, rezerva fără `xlsx-stil.js`). Verifică și indicatorii (KPI) din capul paginii (cifrele față de datele paginii, fâșia pe tipuri, creditorii, lățimile de la 340 la 1400 px, varianta pentru telefon) și panoul „Sumele acordurilor” (total, bară, carduri pe tip, socoteala acordurilor, engleza). Fără browser verifică forma fișierelor puse de mână (`date/sume_manual.json`: coduri de act, sume pozitive, notă ≤ 220 de caractere și adresă https la sursele externe; `date/contopiri_manual.json`: listă de acte, notă, niciun act mutat de două ori); cu browser ține pe loc rândurile unificate sau despărțite de mână (Deșeuri solide, asistența macrofinanciară 2017, Siemens, BEI „Drumuri europene” față de „Moldova drumuri IV”, tranșele japoneze 2KR și sectoriale, TACIS, aeroportul, creditul trei pentru ajustări structurale, Măsuri de Consolidare a Încrederii, ITA-M). Rulare: `python teste_legis.py [--browser]` |
| `legis_local.bat` | Aceeași verificare, rulată de pe calculatorul tău (Windows) |
| `legis_sume.py` | Sumele acordurilor, din textul integral al actelor: descarcă PDF-ul fiecărui act de pe legis.md (legi, hotărâri, ordine; fără decrete), caută „în sumă de…”, „în valoare de…” și scrie rezultatul, cu fragmentul de text, în `date/legis_sume.json`. Rulat de `legis_local.bat`; continuă de unde a rămas |
| `date/sume_manual.json` | Sume puse de mână, pe codul actului (`LP203/2022`). Citirea automată greșește uneori — o tranșă în locul sumei întregi, bugetul unui program întreg, o dată chiar un cont bancar. Ce e aici bate orice sumă citită automat: `{"v": …, "val": "EUR", "nota": "…"}` pune suma, `{"ascunde": true}` o ascunde pe cea greșită. Cu `{"fara_text": true}` se ascunde suma citită greșit din textul actului, cu `{"fara_cost": true}` costul proiectului citit greșit din atașament (de pildă pragul de la care se cere studiu de fezabilitate, luat drept cost), cu `{"fara_guvern": true}` suma luată din nota Guvernului când aceea e a unui program întreg (Interreg, URBACT: sute de milioane pentru toate țările participante), nu a acordului Moldovei. Cu `{"fara_total": true}` suma rămâne pe rând, dar nu se adună în totalurile pe tipuri de finanțare: același acord numărat pe alt rând (un memorandum care repetă suma din acordurile de împrumut și de grant; o înțelegere anterioară al cărei proiect e inclus în totalul unei înțelegeri mai noi) sau o valoare care nu e suma acordată prin acest act. Cu `{"extern": true}` suma vine dintr-o sursă din afara actelor din registru — decizia de finanțare a UE, pagina oficială a finanțatorului, textul acordului publicat de Ministerul Finanțelor, un comunicat oficial: `u` e adresa sursei, `nota` e citatul din ea; pagina o marchează „ext.” și, în loc de „documentul (PDF, legis.md)”, trimite la sursă (în `date/acorduri_legare.json` are `sursa: "extern"`). Se introduce așa doar o sumă dovedită cu un citat dintr-o sursă oficială care numește același acord; când sursa dă doar costul unui program, o sumă pe mai multe tranșe sau o cifră contrazisă de altă sursă, suma nu se pune. Pentru acordurile UE din 2008–2017, fără textul acordului semnat, se ia contribuția UE din fișa acțiunii (decizia anuală de finanțare, enlargement.ec.europa.eu) sau, la cele din 2008–2009, din raportul Comisiei SEC(2009) 514; nota spune atunci „Suma inițială”, fiindcă addendumurile din rând pot schimba totalul. Invers, când suma de pe rând e totalul de după un amendament (acordul FICR din 2026: 300 000 CHF la semnare, 580 000 CHF după amendamentul nr. 1), nota o spune și păstrează suma inițială, cu sursa ei. Când documentul dă echivalentul în euro al unei sume anunțate public în altă valută (MSIP, HG654/2024: 794 407,37 EUR față de 750 000 CHF anunțate de AGEPI și IPI), se introduce suma din document, în euro, iar nota spune și cifra publică, cu sursa ei în `u`. Granturile japoneze se iau din pagina oficială a Ministerului de Externe (schimbul de note, „限度” = plafon în yeni), cu data schimbului de note în notă. Sumele de aici se aplică și registrului din Monitor, inclusiv actelor foarte noi care sunt doar în Monitorul Oficial (cod scos din număr și tip: `HG430/2026`). Fișierul e citit de pagină la fiecare deschidere și de `legis_pagina.py`. O sumă pusă la inițierea negocierilor, din comunicatul Guvernului (plafon sau sumă preconizată, ca la HG562/2026, HG567/2026 și HG569/2026), bate și ea suma din textul acordului: când acordul se semnează sau se ratifică, se verifică din nou și se înlocuiește ori se scoate, altfel rămâne pe rând, fiindcă suma pusă de mână are prioritate. Dacă `extern` e pus și `u` lipsește, sursa e un document oficial nepublicat online (de pildă o notă a Cancelariei de Stat primită de la minister): pagina scrie „document oficial nepublicat online”, iar `nota` spune care document e și citează propoziția cu suma. Registrul nu are curs pentru lei și nu numără sume în lei (cursurile sunt cele de referință ale BCE din `PER_EUR`, în `acorduri.html`, la data din `CURS_DATA`, puse de `curs_bce.py` în fiecare dimineață; o valută nouă — ca coroana cehă, adăugată pentru proiectul RESTART: 22 902 012,92 CZK, 24,254 CZK pentru 1 EUR la 1 iulie 2026 — cere cursul ei acolo (și în lista `DE_LA_BCE` din `curs_bce.py`, ca să se actualizeze) și un loc în `_VALUTE` din `teste_legis.py`; fără curs, suma se vede pe rând, dar nu se adună); când nota dă suma în lei cu echivalentul aproximativ într-o valută (6 693 543 MDL ≈ 386 910 USD), se introduce valuta, iar nota păstrează propoziția întreagă. Un ordin venit din Monitorul Oficial apare cu un cod provizoriu, fără emitent (`O147/2026`), până ajunge în istoricul legis.md, unde are codul întreg (`OMMPS147/2026`); suma pusă sub oricare dintre cele două forme rămâne valabilă și sub cealaltă, cât timp în registru e un singur ordin cu acel număr și an. La fiecare construire a paginii, `legis_pagina.py` anunță cheile din fișier care nu mai corespund niciunui act |
| `legis_consola.js` | Aceeași citire a acordurilor atașate, dar fără nimic de instalat: se lipește în consola browserului (F12) pe www.legis.md. Citește PDF-urile cu pdf.js și pe cele scanate cu OCR (tesseract.js), ia și actele noi, și descarcă `legis_sume.json` gata de urcat în `date/`, plus `sume_lipsa.csv`. Continuă de unde a rămas. Pașii sunt scriși la începutul fișierului |
| `legis_atasamente.py` | Sumele din acordurile atașate la acte: deschide fișa fiecărui act pe legis.md, descarcă PDF-urile atașate (textul acordului), citește cu OCR pe cele scanate (dacă Tesseract e instalat) și scrie suma acordului și costul proiectului în `date/legis_sume.json`, la „atas”. Rulat de `legis_local.bat` după `legis_sume.py`; continuă de unde a rămas. Așteaptă ca fișa să-și încarce conținutul și redeschide o dată actele notate „fără atașamente” de versiunile care nu așteptau. O descărcare eșuată se notează și se trece mai departe; dacă legis.md nu mai răspunde deloc, se oprește și reia data viitoare. Ce rămâne fără sumă ajunge în `sume_lipsa.csv`, cu motivul |
| `gov_sume.py` | Sumele acordurilor din notele de argumentare ale Guvernului: citește de pe gov.md ordinea de zi a fiecărei ședințe și, pentru punctele despre acorduri, PDF-ul notei („Aspectul financiar”). Rulat zilnic de `.github/workflows/sume.yml`; rezultatul, `date/gov_sume.json`, e citit de pagina Acorduri la deschidere (sumele marcate cu G). Ședințele din ultimele zece zile se recitesc la fiecare rulare, fiindcă ordinea de zi se completează până în ziua ședinței; o notă care n-a putut fi descărcată se reîncearcă la rulările următoare. Multe puncte au pe gov.md doar proiectul hotărârii, fără nota de argumentare; atunci `sume` rămâne gol, iar suma se introduce de mână în `date/sume_manual.json`, cu `extern`, din nota primită pe altă cale sau din comunicatul oficial al Guvernului ori al finanțatorului (citatul în `nota`, adresa în `u`). Așa au venit fără sumă hotărârile din 7 și 15 octombrie 2026 (BERD irigații, CEB, BIRD, Japonia: PDF-urile NU-876, NU-860, NU-718, NU-959 și NU-939 de pe gov.md conțin doar proiectul hotărârii); sumele lor s-au pus din comunicatele Guvernului, ale MAIA și ale BERD din 13–15 octombrie 2026 |
| `legatura-amp.js` | Potrivirea dintre acorduri și proiectele AMP („De la lege la bani"): funcții pure, fără DOM, folosite de `index.html` și de teste |
| `teste_legatura.js` | Testele potrivirii: funcțiile mici, scenarii construite de mână și o verificare pe arhiva AMP + registrul real. Rulare: `node teste_legatura.js` |
| `teste_xlsx.py` | Testele exporturilor Excel. Fără argumente: generează cu Node foi de probă (grafice, totaluri, caractere speciale, 20.000 de rânduri) și le verifică (ZIP, XML, formate, formule, grafice). Cu `--browser`: deschide dashboardul în română și engleză, apasă ⚙ → „Descarcă Excel” pe 15 panouri din toate vederile și verifică fișierele descărcate. Rulare: `python teste_xlsx.py [--browser]`. Verifică și fișierele cu mai multe foi (nume, linkuri între foi, grafice numerotate pe tot fișierul, un singur `styles.xml`) și foile registrelor (secțiunea „registru:”: grupe de coloane, coloane înghețate, etichete colorate, înălțimea rândurilor, tipărirea pe lățime) |
| `teste_sectoare.py` | Testele panoului „Donatori → sectoare”. Fără argumente: cu Node, calculează independent (în Python) sumele pe donator, pe sector și pe pereche pentru un set mic făcut de mână și pentru 400 de proiecte aleatoare și le compară cu `sectoare.js`; verifică diagrama SVG (XML bine format, caractere speciale, fără variabile CSS) și datele pentru Excel (foile, linkurile dintre ele, totalurile, graficul). Cu `--browser`: deschide dashboardul în română și engleză și verifică totalurile din diagramă față de „Top donatori” și „Distribuție pe sectoare” din pagina principală, perioada, selecția cu clic și cu tastatura, lista pe grupe, ⚙ → Excel/CSV și butonul „Excel” al listei (fișierele descărcate sunt deschise cu openpyxl), exportul cu o selecție făcută, „Copiază ca imagine” și lipsa erorilor JavaScript. Rulare: `python teste_sectoare.py [--browser]` |
| `legatura_acorduri.py` | Scrie `date/acorduri_legare.json`: deschide pagina registrului într-un browser fără ecran și îi cere lista acordurilor așa cum le vede ea (grupate, denumite, cu suma aleasă și trecută în euro). Are nevoie de Playwright |
| `date/acorduri_legare.json` | Acordurile din registru, gata grupate, un acord pe linie. Citit de pagina „De la lege la bani". Se rescrie doar când se schimbă ceva |
| `date/legaturi_amp.json` | Legăturile acord ↔ proiect AMP confirmate de oameni (vezi mai jos). Se completează de mână sau din pagină |
| `debursari.html` | Pagina „Debursări pe acorduri”: structura (inclusiv `<dialog id="fisa">`, fereastra proiectului) și stilurile. Scripturile ei sunt `debursari.js` și `debursari-ui.js` (vezi „Debursări pe acorduri”), încărcate cu `?v=AAAA-LL-ZZ`: **la fiecare modificare a unuia dintre ele schimbă data din `debursari.html`** (dacă data de azi e deja pusă, adaugă o literă: `?v=2026-11-09b`), altfel browserul poate păstra o variantă veche (de pildă se vedea doar butonul „Debursare”, fără creioanele de editare). Un test verifică prezența lui `?v=` |
| `debursari.js` | Logica paginii, fără DOM, ca s-o poată testa Node: donatorii și proiectele lor, rândurile omise, obiectivele și datele proiectelor (sursele și ordinea lor), totalurile (aceleași reguli ca în registru), proiectele cu grant și împrumut unite într-un singur rând (`grupeazaProiecte`, `sumeComponente`, `ordoneazaUnitati`), operațiile asupra fișierului de date și salvarea lui prin API-ul GitHub („Depozit”), păstrarea codului cu PIN („Seif”) și specificațiile celor trei fișiere Excel |
| `debursari-ui.js` | Interfața paginii: alegerea donatorilor, tabelul, fereastra cu codul, fereastra proiectului (`#fisa`, cu fișa lui), formularele de debursare și de date despre proiect, panourile „AMP”, „Rânduri omise” și „Date fără acord găsit”, butoanele Excel, engleza și varianta pentru telefon. Nu ține codul nicăieri în afara memoriei paginii |
| `amp-date.js` | Datele de început și de finalizare din AMP pentru acordurile din „Debursări pe acorduri”: citește raportul AMP live (nr. 661, prin proxy-ul amp.vivi.md) și, când nu răspunde, arhiva `arhiva.js`; leagă un acord de un proiect AMP doar când denumirea, finanțatorul și suma coincid („sigur”) sau când un om a confirmat legătura în `date/legaturi_amp.json`; o legătură doar „probabilă” rămâne indiciu, nu dă date în tabel. Funcții pure, ca să le poată testa Node |
| `teste_amp_date.js` | Testele lui `amp-date.js`: formatele datelor, regulile de potrivire (sigur, probabil, ambiguu, prea vechi), legăturile confirmate sau respinse, raportul live față de arhivă, oprirea după 20 de secunde și o verificare pe arhiva AMP + registrul real. Rulare: `node teste_amp_date.js` |
| `date/proiecte_manual.json` | Date despre proiecte, scrise de mână și cu sursă. „omise”: rândurile-umbrelă ale registrului, care nu apar în lista de proiecte (cu motivul). „unite”: acordurile cu denumiri diferite care sunt același proiect (actele, denumirea proiectului, motivul) și se arată ca un singur proiect cu componente. „proiecte”: obiectivele proiectului și, când sursa le dă, data de început și de finalizare; fiecare intrare are adresa documentului oficial și citatul exact — fără ele nu se citește (citatul și nota rămân în fișier, ca dovadă; pagina nu le scrie, doar adresa documentului apare ca etichetă „sursă oficială”). Vezi „Debursări pe acorduri” |
| `date/debursari.json` | „Baza de date” a paginii: debursările introduse de mână, o înregistrare pe linie, și — la cheia `proiecte`, scrisă doar când nu e goală — datele despre proiecte introduse în pagină (obiective, început, finalizare). Fișier public; îl scrie doar pagina, prin API-ul GitHub, cu codul de acces. Fiecare salvare e un commit. La 3 noiembrie 2026 conține și datele din scrisoarea Ministerului Finanțelor (situația la 30.09.2026): 31 de debursări cumulate și datele de început/finalizare la 34 de rânduri, fiecare cu nota care citează scrisoarea (vezi „Datele din scrisoarea Ministerului Finanțelor”) |
| `teste_debursari.js` | Testele logicii (obiective și date cu sursele lor, rânduri omise, totaluri, operații, conflicte de scriere, PIN, specificațiile Excel). Rulare: `node teste_debursari.js` |
| `teste_debursari.py` | Verifică fișierele paginii (inclusiv `date/proiecte_manual.json`) și, cu `--browser`, pagina întreagă împotriva unui GitHub simulat (vezi „Debursări pe acorduri”, inclusiv deblocarea unică, editarea în tabel și proiectele cu grant și împrumut unite într-un rând, secțiunea 19, proiectul deschis, încadrat, secțiunea 20, și fișa proiectului, secțiunea 21); `--doar 13,14` rulează doar secțiunile numerotate (de la 13 în sus; 1–12 rulează doar fără `--doar`) |
| `raport_legis.md`, `jurnal_legis.md` | Raportul ultimei rulări și istoricul zilelor cu acte noi. Le scrie `legis_watch.py`; apar în repository după prima rulare reușită a lui `legis_local.bat` |
| `CNAME` | Domeniul propriu |

## Cursul valutar — se actualizează în fiecare dimineață

Sumele în valută se trec în euro cu cursurile de referință ale BCE. Până acum cursurile erau scrise de mână în `acorduri.html`
(`PER_EUR`, cu data în `CURS_DATA`) și rămâneau la data la care fuseseră puse (1 iulie 2026). Acum workflow-ul
`.github/workflows/curs.yml` rulează în fiecare zi la 05:20 UTC (07:20 iarna / 08:20 vara la Chișinău; GitHub întârzie uneori
cron-urile) `python curs_bce.py`, care citește `https://www.ecb.europa.eu/stats/eurofxref/eurofxref-daily.xml` și scrie:
`acorduri.html` și `legis_acorduri.html` (tabelul `PER_EUR`, `CURS_DATA` și mențiunea din comentariul de deasupra) și
`date/acorduri_legare.json` (`curs_data`, `cursuri` și `eur` la fiecare sumă, după aceeași formulă ca pagina: `Math.round(v / curs)`).
`legis_pagina.py` ia apoi cursurile din `acorduri.html`, deci și la următoarea colectare `legis_acorduri.html` iese cu aceleași cursuri.
Paginile arată data cursului: „Cursuri BCE: 10 noiembrie 2026” în capul paginii „Debursări pe acorduri”, „la cursul BCE din …” în registre
și în Excel.

BCE publică în zilele lucrătoare, după-amiaza, deci dimineața e cursul zilei de ieri (luni, cel de vineri); sâmbăta, duminica și în
sărbătorile BCE scriptul nu găsește o dată mai nouă și nu schimbă nimic (nu apare commit). Ce nu vine de la BCE: EUR și ECU = 1,
DEM = 1,95583 (cursul fix), ROL = 10 000 × RON, DST = 1 / valoarea în euro a coșului FMI (0,57813 USD + 0,37379 EUR + 1,0993 CNY +
13,452 JPY + 0,08087 GBP, în vigoare din 1 august 2022), la cursurile zilei; cu cursurile din 1 iulie 2026 dă exact 1 DST = 1,1905 EUR.
Când FMI schimbă coșul (următoarea revizuire: 1 august 2027), se schimbă `COS_DST` în `curs_bce.py`.

Siguranță: dacă BCE nu răspunde (4 încercări), nu dă o valută din cele 11 folosite (USD, JPY, CHF, SEK, CAD, DKK, GBP, PLN, RON, CNY,
CZK) sau dă un curs care diferă cu mai mult de 30% de cel de până acum, scriptul nu scrie nimic și rularea apare ca eșuată în
Actions (cursurile de până atunci rămân). Scrierea e „ori toate fișierele, ori niciunul”. Un workflow care nu pornește din cauza unei
erori de configurare se vede tot în Actions. Pornire manuală: Actions → „Cursul valutar (BCE)” → Run workflow. Testele:
`python teste_curs.py`, rulate și de workflow înaintea scrierii.

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
dashboardului (arhivă + raportul live) și se descarcă în Excel (butonul de sub filtre sau ⚙ de pe panou).

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

**Linkuri în exporturile Excel.** Coloanele cu adrese („Link" din foaia „Acte" a registrelor, „Link sursă" și „Link în registru" din foaia „Acorduri", „Link AMP"
și linkul IATI din exportul dashboardului și din exporturile ⚙ ale panourilor) se scriu ca hyperlinkuri adevărate. O adresă pusă într-o celulă ca
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

## Debursări pe acorduri — introduse de mână, păstrate în repository

Pagina **Acorduri → Debursări pe acorduri** (`debursari.html`) arată, pentru fiecare donator, proiectele
(acordurile) din registrul legis.md pe care le finanțează și, alături de suma proiectului, cât s-a
debursat. Debursările nu vin dintr-o sursă oficială: se introduc de mână, după ce un cod de acces
deblochează editarea, și se salvează în fișierul `date/debursari.json` din repository.

**O singură deblocare, pentru toate acordurile.** Fără cod, pagina e doar pentru citire: nu apar formulare
și niciun banner de blocare la acorduri; singurul buton „Introdu codul" e în bara de acces din capul paginii,
care rămâne vizibilă la derulare. După ce pui codul o dată, se deblochează tot, la toate acordurile deodată:

- **în tabel**, un creion lângă *data efectivă de începere*, *data finalizării* și *suma proiectului* deschide
  editarea rândului (câmpuri în celule, o notă opțională cu sursa informației, „Salvează" / „Anulează"; Enter
  salvează, Esc anulează). Se scrie în fișier doar ce a schimbat omul: o dată luată dintr-o sursă oficială sau
  din AMP, lăsată neschimbată, nu se copiază ca valoare scrisă de utilizator; golești un câmp ca să revii la
  sursă (la sumă, la cea din registru);
- **suma proiectului** scrisă de utilizator (cu valută) înlocuiește suma din registru doar la acel acord, în
  pagină (totaluri, procentul debursat, ordonări) și în Excel; rândul o marchează „corectată de utilizator" și
  arată alături suma din registru, iar Excel are o notă cu lista „registru → corectată". Un rând care nu intră
  în total (dublură, „nu se adună") rămâne în afara totalului și cu suma corectată. Se păstrează în
  `date/debursari.json`, în înregistrarea „Date despre proiect" a rândului (`suma` și `val`);
- **debursările** se adaugă din butonul „Debursare" al rândului (deschide detaliile, la formular) și se
  modifică sau se șterg din lista din detalii; formularul „Date despre proiect" din detalii are și el suma.

**Ce arată.** Pagina ia acordurile din `date/acorduri_legare.json` (scris de `legatura_acorduri.py`
chiar din registru) și le repartizează pe donatori: finanțatorii numiți în acordul însuși
(`parteneriAcord`), nu toți partenerii adunați din actele grupate; un împrumut al BERD nu apare și la BEI
doar fiindcă un act al grupului vorbește de ambele bănci. Un acord cofinanțat apare la fiecare finanțator
al lui, dar în totaluri se numără o singură dată; fără partener în registru, donatorul e „(neidentificat)".
Bifezi unul sau mai mulți donatori și apare lista proiectelor lor, cu coloanele **Proiectul**,
**Data efectivă de începere**, **Data finalizării**, **Tip de finanțare**, **Suma proiectului** (în valuta
acordului și în euro) și **Suma debursărilor** (cu procentul debursat). **Descrierea succintă** (obiectivele
proiectului) nu are coloană: apare doar când deschizi proiectul, în fereastra lui, cu sursa ca etichetă mică. Butonul
din dreapta deschide **fereastra proiectului**, o fereastră separată, mai mică, deasupra paginii (vezi mai jos): descrierea,
datele esențiale, perioada, parcursul acordului, debursările și, după deblocare, formularele. Se poate căuta (denumire, obiective, act, partener), filtra (tip de
finanțare, cu sau fără debursări) și sorta. Donatorii bifați și filtrele rămân în adresa paginii
(`#d=BERD|BEI&tip=…`), deci o selecție se trimite ca link. Pe laptop și pe desktop (ferestre de 1250 px sau mai
late) fiecare tabel încape întreg în panoul lui, chiar cu toți donatorii bifați; pe un ecran mai îngust tabelul se
derulează în panoul lui, iar pagina nu se lărgește. Pe telefon tabelul devine fișe; pagina are și varianta în engleză.

**Proiecte cu grant și împrumut: un singur rând, cu sumele pe componente.** (Acorduri cu denumiri diferite în registru, dar care sunt același proiect, se unesc de mână, vezi „unite” mai jos.) Registrul are separat grantul și
împrumutul aceluiași proiect (două acorduri, aceeași denumire, ani diferiți). Pagina le arată ca **un singur rând**,
cu denumirea comună o singură dată și, la „Suma proiectului", cât e grant, cât e împrumut (fiecare în valuta lui) și
**totalul** în euro; sub denumire scrie tipurile și numărul de acorduri („grant + împrumut · 2 acorduri"). Proiectul **nu se desface în tabel**: un clic pe rând
(sau pe butonul din dreapta) deschide **fereastra proiectului**, pe prima componentă, iar componentele (numite după tip și an,
„Grant, 2023", „Împrumut, 2022") se aleg în fereastră, din filele liniei **„Componentele proiectului · alege componenta”**:
fiecare filă are o casetă bifată la cea afișată, numele și suma componentei în valuta ei; un clic pe alta schimbă fereastra pe ea,
fără s-o închidă. Datele, debursările, detaliile și formularele (debursare, date despre proiect, inclusiv suma) sunt în fereastra
componentei; rândul proiectului nu are creioane, nici butonul „Debursare”, iar rândul are `data-ac` (acordurile lui). Rândul proiectului arată
debursările însumate ale componentelor, cu procentul din totalul proiectului, iar datele de început și de finalizare sunt cele din acorduri (începutul cel mai
timpuriu, finalizarea cea mai târzie, cu mențiunea „din acorduri"). Se unesc numai rândurile cu aceeași denumire
(fără diacritice și punctuație) **la același donator**, când între ele sunt și grant, și împrumut: două acorduri de
același tip sau de donatori diferiți nu se unesc, iar un filtru care ascunde una dintre componente (de pildă tipul
„Împrumut") desface proiectul în rânduri obișnuite, cu mențiunea „(împrumut, 2022)" ca înainte. Proiectele se sortează
după totalul lor. **Numărătorile și Excel-ul rămân pe acorduri**: indicatorii și sumele din antet nu se schimbă, antetul
donatorului spune „N proiecte (M acorduri)", iar Excel-ul are tot câte un rând pe acord, cu denumirile deosebite. Un
singur act care cuprinde și grant, și împrumut (de pildă acordul cu FIDA, `hg969/2008`) rămâne un singur rând, cu tipul
dat de registru, fiindcă registrul nu are sumele separate. Regulile sunt în `grupeazaProiecte` și `sumeComponente` din
`debursari.js`, cu teste în `teste_debursari.js` și în secțiunea 19 din `teste_debursari.py`.

**Suma în lei a acordului HG758/2017.** BCE nu publică un curs al leului moldovenesc, deci o sumă în MDL rămânea fără echivalent în euro și acordul ieșea din total (`inTotal: fara_curs`). În `date/sume_manual.json` suma e acum echivalentul dat de același raport (anexa din Raportul privind asistența externă pe 2017–2018): 230 mii USD, în loc de 4 mil. lei; nota din fișier spune de ce. Restul fluxului (`legis_pagina.py`, `legatura_acorduri.py`) rămâne neschimbat.

**Accesibilitate și atingere.** Butoanele „Deschide toate” și „Excel” din panoul de sectoare au text de pornire în HTML (JavaScript îl înlocuiește), iar câmpul `legJson` are etichetă în `ETICHETE_CONTROALE`. Pe ecran tactil (`@media (pointer:coarse)`) legăturile din subsol, comutatorul RO/EN, butoanele de analize și `.lnk` au o zonă de apăsare ceva mai mare; pe mouse nimic nu se schimbă. Pagina principală are în subsol un link către „Debursări pe acorduri” (`footerDebursari` în ambele dicționare).

**Pentru motoarele de căutare.** `index.html` are o singură `meta description` (cea care se potrivește cu `og:description`) și date structurate `WebSite`; `debursari.html` are un `Dataset` (descărcările: `date/acorduri_legare.json` și `date/debursari.json`); `404.html` are descriere și `noindex`. `sitemap.xml` avea deja `lastmod` (îl scrie `date_deschise.py`).

**Curățenie.** `tema.css` (o temă pe care nicio pagină nu o folosește) și testul ei, `teste_tema.py`, au fost scoase. Pagina „De la lege la bani” din `index.html#legaturi` rămâne: nu mai e în meniu, dar e unealta cu care se pregătesc confirmările acord ↔ proiect AMP (`legJson`, apoi `date/legaturi_amp.json`), așa că n-am șters-o. `CITESTE.txt` e doar nota pachetului și nu trebuie urcat în repository.

**Fără text explicativ pe pagină.** Paragraful de sub titlu („Acordurile din registrul legis.md, repartizate pe donatori…”) și blocul „De unde vin cifrele” (cinci paragrafe despre sursă, obiective, dubluri, debursări și procent) au fost scoase din „Debursări pe acorduri”. Din bloc au rămas, într-un rând mic, butonul „Descarcă o copie a debursărilor (JSON)” și, când există un cod păstrat pe dispozitiv, „Uită codul păstrat pe acest dispozitiv”, fiindcă sunt funcționale. `randeazaNote()` din `debursari-ui.js` le randează; `#tSub` nu mai există.

**Aspectul paginii (doar ecran).** Un bloc de CSS în `debursari.html`, în `@media screen`, chiar înainte de `@media print`, așază și
ierarhizează pagina fără să schimbe culorile și fonturile: bara de filtre e un card (căutarea și cele trei filtre pe primul rând,
butoanele „Excel · total” și „Excel · pe donatori” împreună, la dreapta, pe al doilea; pe telefon, câte unul pe rând); panoul unui
donator are linie albastră deasupra, acronimul mare, iar indicatorii din antet (proiecte, sumă, debursat, obiective/început/finalizare)
sunt cartonașe; tabelul are celule mai aerisite și un antet de coloane ușor colorat. Nu schimbă marcajul generat de
`debursari-ui.js`, deci selectorii testelor rămân aceiași; la tipărire nu se aplică.

**Acorduri cu denumiri diferite, dar același proiect: „unite” în `date/proiecte_manual.json`.** Regula de mai sus nu prinde
acordurile al căror nume diferă în registru (de pildă cele trei ale Federației Ruse: grantul HG 793/2020, împrumutul HG 169/2020
și creditul de stat HG 443/2009). Acestea se unesc de mână: o intrare în `unite` are `acte` (cel puțin două coduri de act, ca în
„omise”), `nume` (denumirea sub care se arată proiectul) și `motiv`; fără una dintre ele intrarea se respinge, cu mesaj. Rândul
unit se comportă ca proiectul cu grant și împrumut (sume pe componente, fereastră cu file pe componentă), dar se unește și
fără pereche grant + împrumut, și cu orice tipuri. Rămân valabile condițiile: același donator și cel puțin două acorduri rămase după
filtre (un filtru care ascunde toate în afară de unul îl desface în rând obișnuit). Cheia grupului e `~` + denumirea normalizată, ca
să nu se încurce cu un grup automat. Se scoate sau se schimbă ștergând/editând intrarea. Teste: `teste_debursari.js`, secțiunea 16
(forma intrărilor) și secțiunea 23 (rândul Rusia în browser) din `teste_debursari.py`.

**Proiectul cu componente nu mai are bloc încadrat.** Până acum se desfăcea în tabel, cu rândul lui și componentele într-un bloc cu fundal
albastru și bară; acum rândul rămâne neschimbat la deschidere (fundal obișnuit, bara subțire din stânga), iar tabelul nu primește
rânduri de componente. Regulile CSS ale blocului (`tr.pg.deschis`, `tr.ac.sub`) au rămas în `debursari.html`, nefolosite. Secțiunea 20
din `teste_debursari.py` verifică, la 1360, 1000, 820 și 390 px, că tabelul e neschimbat cu fereastra deschisă, că pagina nu se lărgește și
că filele încap în fereastră.

**Fereastra proiectului (ce se vede când deschizi un proiect).** Detaliile unui proiect nu se mai desfac în tabel, între
proiectele vecine (unde se amestecau cu ele), ci se deschid într-o **fereastră separată, mai mică, deasupra paginii**: un
`<dialog id="fisa">` modal, pe fundal întunecat; pagina din spate nu se derulează și nu poate fi atinsă cât e deschisă. Sus,
un antet care rămâne pe loc: tipul și situația acordului, denumirea proiectului, semnarea și cofinanțatorii, butonul
**Închide** și, la un proiect cu grant și împrumut, linia **Componentele proiectului** (filele cu casetă bifată: un clic pe o componentă schimbă
fereastra pe ea, fără s-o închidă; un proiect cu componente se deschide din rândul lui, pe prima componentă). Fereastra se închide cu
**Închide**, cu **Esc** sau cu un clic pe fundalul întunecat (nu și când o selecție de text începută în fereastră se
termină pe fundal), iar **focusul se întoarce pe butonul rândului** de unde s-a deschis (la un proiect cu componente,
pe butonul rândului proiectului, indiferent ce componentă era afișată); o schimbare a filtrelor din adresă o închide. Dedesubt de antet, fișa se derulează în
fereastră; pe telefon (820 px și mai puțin) fereastra ocupă tot ecranul și rămâne lipită sus doar bara cu tipul și „Închide”,
iar denumirea, componentele și fișa se derulează împreună. Fereastra e în afara tabelului și a zonei `#debRoot`, deci are
propriii ascultători de evenimente în `debursari-ui.js` (`deschideFisa`, `inchideFisa`, `randeazaFisa`, `spreComponenta`,
`nodFk`); se redesenează odată cu tabelul (de pildă la schimbarea limbii sau după o salvare), păstrând focusul, ce a scris
omul în câmpuri și poziția de derulare. Conținutul ei e marcat `data-no-tr` (traducerea o face pagina, prin `L(ro, en)`, nu
`traducere.js`). Fișa din fereastră e o succesiune ordonată de cartonașe albe cu titlu mic, în această ordine: **Descrierea proiectului** (obiectivele, cu sursa ca etichetă mică „sursă oficială” /
„AMP” / „introdus de utilizator”, iar la oficial, link spre document; când titlul întreg al acordului diferă de denumirea
din tabel, apare dedesubt), **Date esențiale** (donatorul cu denumirea întreagă sub acronim, suma acordului cu valuta, echivalentul
în euro și de unde vine suma, costul total al proiectului și alte sume din acte, când registrul le are, și dacă intră în totaluri),
**Perioada de implementare** (data de început și de finalizare, fiecare cu sursa ei, **durata** și **situația** — „în
desfășurare”, „termenul de finalizare a trecut” sau „urmează să înceapă” — calculate din cele două date, față de ziua de
azi; „≈” când o dată e doar luna sau anul; fără durată și situație când o dată lipsește sau datele se contrazic; apoi proiectul
AMP legat) și **Parcursul acordului** (actele din registru în ordinea datelor, fiecare cu etapa pe care o reprezintă — inițierea
negocierilor, aprobarea semnării, proiectul de lege, ratificarea, promulgarea, punerea în aplicare — tipul și numărul actului,
cu link spre el; un acord cu **nouă acte sau mai multe** arată primele trei și ultimele trei, iar restul se deschid cu
butonul „Arată încă N acte”, care se închide cu „Restrânge lista actelor”; starea se păstrează când fereastra se redesenează sau se redeschide). Pe
ecran lat cartonașele curg în două coloane echilibrate, de la 900 px în jos într-una (descriere, date, perioadă, parcurs); sub
ele, pe toată lățimea, **debursările**, iar după deblocare, unul lângă altul, formularul de debursare și cel de „Date despre
proiect”. **Citatul exact și nota din `date/proiecte_manual.json` nu se mai scriu în pagină**: rămân în fișier, ca dovadă pentru
cine îl întreține; nota și gazda documentului se văd doar în indiciul (`title`) etichetei sursei. Fișa nu inventează nimic:
tot ce arată vine din registru (actele, sumele, donatorii), din sursele de mai sus sau se calculează din datele de început și
de finalizare; **textul descrierii vine doar din surse** (obiectivele), așa că un proiect fără obiective spune „Obiective
neintroduse” până când cineva introduce obiectivele (formularul „Date despre proiect” sau o intrare nouă în `date/proiecte_manual.json`).
Logica pură e în `debursari.js` (`parcursAcord`, `parcursAfisat`, `durataProiect`, `fmtDurata`, `stareProiect`), cu teste în
`teste_debursari.js`; afișarea e în `debursari-ui.js` (`htmlDescriere`, `htmlInfo`, `htmlProiect`, `htmlParcurs`, `htmlDetalii`;
starea parcursului desfășurat e `S.cale`, fereastra deschisă e `S.fisa`), stilurile în `debursari.html` (`dialog#fisa`, `.fw`,
`.fisa`, `.fs`, `.fapte`, `.cale`); secțiunea 21 din `teste_debursari.py` verifică în browser conținutul fișei: ordinea actelor,
etapele, linkurile și legendele sunt calculate independent din registru, cu data înghețată (10.11.2026) pentru „în desfășurare /
încheiat”, în română și engleză, la 1360, 1000, 901/900 și 390 px, cu și fără cod, și cu fișierul adevărat de surse (niciun citat
în pagină). Secțiunea 22 verifică fereastra în sine: deschiderea și închiderea (Închide, Esc, clic pe fundal, o selecție care
iese pe fundal), focusul (pe titlu la deschidere, înapoi pe rând la închidere, în fereastră la Tab), derularea pe loc cu antetul
fix, schimbarea componentei, formularele după deblocare (ce s-a scris rămâne la redesenare; Esc într-o debursare aflată în
editare nu închide fereastra), telefonul (ecran întreg, bara lipită sus) și lățimile 1000, 821 și 820 px.

**Rânduri omise, ca un proiect să nu apară de două ori.** Cinci rânduri ale registrului nu apar în liste:
sunt rânduri-umbrelă, adică negocieri sau memorandumuri pentru acorduri care au deja rândurile lor, cu
aceleași sume (HG546/2026, HG799/2014, HG296/2013, HG704/2007, LP232/2023). Lista lor, cu motivul, e în
panoul „Rânduri omise" de sub tabel și în notele Excel-ului. Rămân în registru și nu schimbă totalurile
(niciunul nu se adună în total). Se schimbă în `date/proiecte_manual.json`, la „omise". Verificarea
dublurilor (octombrie 2026): niciun act nu e pe două rânduri; aceeași denumire la același donator (de pildă
două tranșe ale aceluiași program) primește în listă o deosebire (tipul, anul); rândurile cu denumiri
asemănătoare s-au verificat unul câte unul și sunt acorduri diferite (alt împrumut, altă tranșă, altă
bancă). Câteva rânduri ale registrului unesc totuși două acorduri distincte (de pildă Livada Moldovei I și
II); nu s-au despărțit, ca să nu se schimbe totalurile.

**Sumele.** Aceleași reguli ca în panoul „Sumele acordurilor" din registru: un rând intră în total doar
dacă îl numără registrul (`inTotal` din `date/acorduri_legare.json`: `numarat`, `fara_suma`, `fara_total` sau
`fara_curs`), în euro, la cursurile BCE din `cursuri` și `curs_data` ale aceluiași fișier (le scrie
`legatura_acorduri.py` odată cu lista, ca regulile registrului să nu fie repetate în pagină). „% debursat"
compară debursările la proiectele numărate cu suma lor; cardul „Debursat" adună toate debursările introduse.
Un proiect fără sumă rămâne în listă („suma nu e cunoscută") și poate primi debursări, dar nu intră în
procent. Nu se numără sume în lei (registrul n-are curs pentru ei) și nici o valută fără curs: o debursare
se introduce într-o valută care are curs în fișier.

**Obiectivele și datele proiectelor.** „Descriere succintă" înseamnă obiectivele proiectului (se vede doar în proiectul deschis), iar „Data
efectivă de începere" și „Data finalizării" sunt datele proiectului, cum le numește AMP („Actual Start Date" și
„Proposed Completion Date"). Registrul legis.md nu are nimic din acestea, deci fiecare câmp (obiectivele,
începutul, finalizarea) se ia, în ordine, din prima sursă care îl are:

1. **Ce a introdus un utilizator în pagină**, după ce a pus codul (secțiunea „Date despre proiect" din
   detalii, sau creionul din tabel). Se salvează în `date/debursari.json`, la cheia `proiecte`, cu data salvării și o notă.
2. **O sursă oficială, scrisă de mână** în `date/proiecte_manual.json`, la „proiecte": `acte` (orice cod de act al
   rândului), `obiective` (`ro` și `en`), `inceput` și `sfarsit` (`AAAA-LL-ZZ`, `AAAA-LL` sau `AAAA`, după cât spune
   sursa), `sursa` (adresa documentului oficial), `citat` (fragmentul exact din document care susține ce s-a
   scris; rămâne în fișier, ca dovadă, și nu se afișează în pagină) și, opțional, `nota` (se vede doar în indiciul etichetei sursei). O intrare fără sursă și citat nu se citește: pagina o semnalează în panoul „Date
   fără acord găsit", ca să nu apară în tabel nimic ce nu se poate verifica. Obiectivele se scriu în română
   (traducerea) și în engleză (cum le dă documentul); o dată se pune doar dacă sursa spune începutul sau
   sfârșitul proiectului (nu data aprobării sau a semnării), iar `nota` spune ce anume înseamnă data.
3. **AMP**, doar pentru date și doar când legătura acord ↔ proiect AMP e sigură: denumirea, finanțatorul și suma
   coincid, sau un om a confirmat legătura în `date/legaturi_amp.json`. O legătură doar „probabilă" nu dă nicio
   dată în tabel, fiindcă prea des nimerește altă fază sau alt an: se arată în detalii, ca indiciu, cu butonul
   „Copiază datele în formular". Obiectivele nu vin din AMP: raportul pe care îl citim nu le cuprinde.

Fiecare dată sau obiectiv arată în tabel și în Excel de unde vine („introdus de utilizator", „sursă oficială",
„AMP"). Datele din AMP vin din raportul AMP live (nr. 661, prin proxy-ul amp.vivi.md); dacă nu răspunde în 20 de
secunde, pagina folosește arhiva `arhiva.js`, care ajunge până în 2022, spune asta în panoul „AMP" și oferă
„Reîncearcă". Cu arhiva, în octombrie 2026, 42 din cele 460 de proiecte sunt legate sigur de un proiect AMP (cele 42
au fost verificate de mână), 41 doar probabil și 19 ambiguu; raportul live, care acoperă și anii 2022–2026,
leagă de regulă mai multe. O legătură probabilă se poate confirma în „De la lege la bani": de atunci devine
„sigură, confirmată" și în această pagină. O celulă goală („—", „Obiective neintroduse") înseamnă că nu s-a găsit
încă o sursă: pagina nu completează cu presupuneri. Cât e completat la donatorii afișați se vede sub titlul
tabelului („obiective N/M · început N/M · finalizare N/M", cu cifrele de la momentul deschiderii paginii).
Un utilizator poate corecta oricând un câmp din pagină; `date/proiecte_manual.json` e pentru ce se poate
dovedi cu un document oficial.

La data acestei versiuni (runda a cincea de surse oficiale), `date/proiecte_manual.json` are obiective pentru 240 din cele 466 de rânduri listate
(Banca Mondială 103, BERD 34, BEI 20, Japonia/JICA 17, Elveția 14, Uniunea Europeană 13, Germania — KfW, GIZ și acorduri guvernamentale — 12,
CEB 10, FIDA 9, AFD 7, SUA/MCC 1), fiecare cu adresa documentului oficial și citatul exact. Restul (China, SUA/USAID, granturile japoneze pentru IMM,
schimburile de note germane fără proiect numit, majoritatea acordurilor UE și o parte din ale Băncii Mondiale) rămân „neintroduse", până se găsește o sursă; se pot completa direct din pagină, cu codul de acces, sau în
fișier, cu o intrare nouă (sursă + citat). Datele de început și de finalizare vin deocamdată din AMP (la proiectele legate sigur) și din 60 de intrări oficiale
(Banca Mondială 35 — din rapoartele de implementare ISR, de finalizare ICR și din acordurile de finanțare: data intrării
în vigoare ca început, data de închidere ca final —, FIDA 8, JICA/Japonia 5, GIZ/Germania 4, AFD 4, Elveția/SDC 3 și
MCC 1); la fiecare, `nota` spune ce reprezintă data (intrare în vigoare, perioadă, închidere prevăzută sau reală) și
când legătura cu rândul din registru se bazează doar pe denumire sau pe sumă. Fișele BERD, BEI și CEB dau doar data
aprobării sau a semnării, nu perioada proiectului, deci la ele datele vin numai din AMP.

**Datele din scrisoarea Ministerului Finanțelor (situația la 30.09.2026).** Scrisoarea nr. 11/1-3/512/1729 din 01.11.2026 (semnată
electronic de secretarul de stat Ion Gumene, către Cancelaria de Stat), cu anexa „Informația privind sursele externe și rata de
valorificare la situația din 30.09.2026”, listează 42 de acorduri de împrumut și finanțare, fiecare cu data semnării, **data efectivă de
începere**, **termenul limită de implementare**, suma, legea de ratificare și **debursările efectuate** (în mii EUR, cumulat). Documentul nu
e public, deci nu poate sta în `date/proiecte_manual.json` (care cere adresa documentului); datele sunt introduse în `date/debursari.json`,
exact ca și cum ar fi fost scrise din pagină, fiecare cu o notă care citează scrisoarea („introdus de utilizator”). Rândurile din anexă s-au
legat de rândurile registrului după legea de ratificare (40 de acorduri) și, la două, după denumire, dată și sumă (INSPIREE, AFD: anexa
scrie Legea 314/2025, registrul LP106/2025; creditul BIRD „Conectivitate rurală”: anexa scrie 176/2025, registrul LP176/2024). Ce s-a scris:

* **Data efectivă de începere → „Data efectivă de începere”; termenul limită de implementare → „Data finalizării”**, la 34 de rânduri, doar
  unde câmpul n-avea nicio sursă. Ce are deja o sursă oficială (`date/proiecte_manual.json`) nu s-a atins, nici când anexa dă altă dată
  (șase câmpuri, mai jos); la fel cum o dată din AMP rămâne unde anexa nu spune nimic. Începutul și finalul spun în notă ce reprezintă.
* **Debursările**, la 31 de rânduri: câte o înregistrare cumulată, datată 30.09.2026, în euro (anexa dă mii EUR; suma = mii EUR × 1000).
  Suma lor, 1.015.106.200 EUR, este totalul din anexă. La cele 11 acorduri fără nicio tragere (anexa: 0,00) nu s-a scris nimic.
* **Sumele proiectelor**: la 35 din cele 42 de rânduri suma din anexă (în moneda acordului) e identică cu cea din registru, deci pagina o arată
  deja și nu s-a scris încă o dată. La celelalte șapte diferă (tabelul de mai jos): rămâne suma din registru, iar nota rândului spune ce dă anexa.
* **Nu s-au scris** obiectivele și tipul finanțării: anexa nu le are.

Discrepanțe, rămase pentru decizia ta (nu s-a schimbat nimic în registru):

| Rând | Registru | Anexa MF | Ce se vede |
|---|---|---|---|
| BEI, infrastructura feroviară (Legea 298/2016) | 50 mil. EUR (LP10/2022) | 74 mil. EUR (59,2 mil. debursat + 14,8 nedebursat) | pagina arată 118,4% debursat |
| BERD, Reabilitarea drumurilor IV (Legea 191/2013) | 250 mil. EUR (LP333/2022) | 290 mil. EUR (234,4 + 55,6) | pagina arată 93,8%, anexa 80,8% |
| BERD, Reabilitarea drumurilor V (Legea 53/2024) | 150 mil. EUR (LP53/2024) | 300 mil. EUR (nimic debursat) | fără debursare scrisă |
| BERD și BEI, Chișinău termoficare (Legile 14/2025 și 203/2025) | 143,5 mil. EUR | 143,0 mil. în coloana „suma”, dar 143,5 mil. în coloanele de debursat + nedebursat | anexa se contrazice; registrul coincide cu soldurile |
| BIRD și AID, Conectivitate rurală (Legile 176/2025 și 177/2024) | BIRD 92,4 / AID 5,6 mil. EUR | BIRD 5,6 / AID 92,4 mil. EUR în coloana „suma” (soldurile arată BIRD 92,4) | coloana „suma” pare inversată în anexă; registrul e corect |
| Yenul (JICA, Legea 171/2020) | 2.059 mil. JPY = 11,1 mil. EUR la cursul BCE din 1 iulie 2026 | 11,4 mil. EUR debursat (cursurile din zilele tragerilor) | pagina arată 102,8%, anexa 99,1% |

Date în conflict cu cele deja existente (rămân cele existente): final la JICA (2026-06 față de 24.11.2029), BIRD AGGRI (31.12.2029 față
de 01.09.2029) și FIDA IFAD VIII (30.03.2027 față de 30.09.2028); început la AID ÎMMM (25.11.2022 față de 22.11.2022), AFD INSPIREE
(10.03.2025 față de 06.09.2025) și BIRD reabilitare (10.12.2024 față de 11.07.2024). Cele din registru sunt, de regulă, datele de închidere
ale finanțatorului sau ale proiectului; cele din anexă, termenul de implementare al împrumutului: nu înseamnă același lucru.
Neconcordanțe în anexa însăși (datele de început și de final nu sunt în cauză): semnarea CEB „Locuințe publice III” (19.12.2024, după
intrarea în vigoare din 28.05.2024; registrul: 19.03.2024) și semnarea BIRD „Învățământul superior” suplimentar (02.06.2026, după
intrarea în vigoare din 31.07.2025). Rândul BERD „CET-Nord” al registrului grupează acte din 2014–2015, 2021–2022 și 2025; în anexă e Faza II
(semnată 24.12.2021, Legea 99/2022), iar nota o spune.

Un utilizator poate corecta oricând aceste înregistrări din pagină (creionul din tabel); `teste_debursari.js` verifică fișierul: fiecare
înregistrare are rând, notele au cel mult 200 de caractere, totalul MF se potrivește, iar nicio dată nu se scrie peste una oficială.

**Datele din Banca Mondială (Finances One, situația la 30.09.2026).** Seturile publice „IBRD Statement of Loans and Guarantees –
Historical Data” (`DS00975`) și „IDA Statement of Credits, Grants and Guarantees – Historical Data” (`DS00976`) de pe
financesone.worldbank.org dau, pentru fiecare credit al Moldovei: data semnării, **data intrării în vigoare** (*Effective Date*),
**data închiderii** (*Closed Date*, ultima înregistrată: poate fi prelungită), suma inițială, suma anulată și suma **debursată
cumulat**, toate în dolari (debursările la cursul zilei plății). Un credit s-a legat de un rând al registrului numai când data semnării
coincide cu `semnat` și suma BM / suma din registru se încadrează în cursul monedei acordului (EUR 1,0–1,4; DST 1,3–1,7; USD ≈ 1);
la rândurile cu două instrumente în aceeași zi s-a ales după sumă (dp461 și dp462/2022 au etichetele BIRD/AID inversate în registru
față de BM: s-au legat după sumă, registrul nu s-a schimbat). Ce s-a scris:

* **`date/proiecte_manual.json`**: 26 de intrări noi, doar unde câmpul (început sau final) nu avea nicio sursă; `sursa` e adresa API-ului
  cu filtrul pe numărul creditului (o singură înregistrare), `citat` e fragmentul exact din ea (semnarea, data, numărul). Nu s-a atins nicio
  dată care avea deja sursă.
* **`date/debursari.json`**: 35 de debursări cumulate la 30.09.2026, în USD (total 1.229.113.440,64 USD), doar la rândurile fără nicio
  debursare din scrisoarea MF. La două rânduri cu două instrumente în aceeași zi (hg623/2006, hg1370/2005) s-au scris doar datele.
* **Nu s-au schimbat** sumele proiectelor din registru și datele deja existente; diferențele (12 câmpuri, mai ales termene prelungite
  de BM după aprobare) sunt în foaia „Diferențe de date” din `banca_mondiala_potriviri.xlsx`, cu tot ce n-a putut fi legat.

**Date din registrul IATI și din documente FIDA.** IATI e registrul în care finanțatorii își publică singuri activitățile (data de început
și de final, angajamentul, plățile); `d-portal.org` îl afișează, iar `q.xml?aid=…` dă activitatea exact cum a publicat-o finanțatorul.
S-au legat de rânduri 18 activități: UE (11, DG NEAR), KfW și GIZ (4), AFD (1) și JICA (2), numai când finanțatorul, titlul și suma
(în moneda acordului) coincid. Alte 2 date (FIDA, programele RBDP și RFSADP) vin din documente FIDA/IOE.

* **`date/proiecte_manual.json`**: 20 de intrări noi, doar unde câmpul nu avea sursă. `sursa` e adresa activității, `citat` elementele
  `activity-date` exacte; `nota` spune dacă data e reală („Actual”) sau planificată („Planned”). La UE, începutul e data reală a acțiunii,
  finalul e sfârșitul planificat al perioadei de implementare. La `hg786/2024` și `hg90/2025` (activități „în pregătire”, cu două date
  de început care nu se potrivesc) s-a scris doar finalul; la JICA `hg277/2023` (creditul de politici) doar finalul, fiindcă începutul
  planificat (01.01.2023) e înainte de semnare.
* **`date/debursari.json`**: 3 debursări cumulate, doar la acorduri plătite integral (UE `hg432/2021`, 60 mil. EUR; KfW `hg1108/2010`,
  5 mil. EUR; AFD `hg462/2022`, 60 mil. EUR). La activitățile încă în plată nu s-a scris nimic: IATI nu spune la ce dată e totalul.
* **Ce nu spune IATI**: BERD și BEI publică doar data aprobării/semnării (nu perioada proiectului) și nicio plată, iar la nivelul deciziilor
  UE „plătit” e 0 (plățile sunt la nivelul contractelor), deci nu s-au folosit. Legăturile doar după sumă (sume rotunde: 5, 25, 40, 60 mil.)
  nu s-au scris; lista lor e în `surse_oficiale_potriviri.xlsx`.

**Credite mai vechi ale Băncii Mondiale, asistența macrofinanciară a UE și Compactul MCC.** A treia rundă de surse oficiale a extins legarea
cu Finances One la creditele din 1994–2017, a adăugat pagina DG ECFIN a Comisiei Europene (operațiunile MFA ale Moldovei, cu fiecare tranșă)
și cifra finală a Compactului MCC. La actele din 1995–2004, HG apare adesea la 2–5 săptămâni după semnarea BM, așa că potrivirea ține cont de
denumire, de sumă (la DST, 1,2–1,75 față de moneda actului; suma a două instrumente semnate în aceeași zi) și de fereastra de date a actelor.

* **`date/proiecte_manual.json`**: 38 de intrări noi, doar unde câmpul nu avea sursă. 35 vin din Finances One (început = *Effective Date*,
  final = *Closed Date*; `sursa` e API-ul filtrat pe numărul creditului, `citat` are semnarea, datele și numărul). La rândurile cu două
  instrumente ale aceluiași proiect (BIRD + AID, credit + grant) finalul e cel mai târziu. 3 vin de pe pagina ECFIN: finalul MFA 2017–2020
  (iulie 2020, sfârșitul perioadei de disponibilitate; `hg763/2017` și `hg226/2017`) și al MFA COVID-19 (08.10.2021; `hg501/2020`).
* **`date/debursari.json`**: 37 de debursări noi. 30 sunt cumulate BM la 30.09.2026 (529.413.952,19 USD; la rândurile cu două instrumente,
  suma lor). 6 sunt tranșe MFA, pe tipul acordului: `hg763/2017` (împrumut) 2 × 20 mil. EUR și `hg226/2017` (grant) 2 × 10 mil. EUR, plătite
  la 10.10.2019 și 10.07.2020 (datele aprobării plății de către Comisie; ECFIN spune doar „octombrie 2019” și „iulie 2020”), `hg501/2020`
  (MFA COVID-19) 2 × 50 mil. EUR, la 25.11.2020 și 08.10.2021. Una e a Compactului MCC (`hg677/2009`): 259.371.697 USD cheltuiți din
  262 mil. („Grant Expended”, pagina MCC în copia arhivată din 14.02.2017), datată la încheierea Compactului (01.09.2015), fiindcă cifra n-are
  dată proprie; datele Compactului erau deja în fișier.
* **MFA 2022–2024 nu s-a scris.** Decizia (UE) 2022/563 (295 mil. EUR, 5 tranșe între 01.08.2022 și 17.12.2024, încheiată) nu are rând propriu:
  actele ei sunt adunate în rândurile `hg226/2017`, `hg501/2020` și `dp1663/2020` (același titlu). Intrările manuale de mai sus listează numai
  actele din 2017 și 2020, deci rămân corecte dacă rândurile se despart. Rândul `dp1663/2020` (memorandumuri) nu s-a completat.
* **Ce nu s-a scris, în rest**: data semnării memorandumului MFA 2017 (ECFIN spune 24.11.2017, un comunicat al Comisiei din 10.10.2019 spune
  „octombrie 2017”) și începutul MFA COVID-19 (sursa dă doar memorandumul, 29.09.2020; „semnat” din registru, 22.06.2022, e al altui acord);
  la BM, rândurile cu instrumente ambigue sau cu sumă care nu se potrivește (`hg712/2010`: 2 mil. USD în registru, 20 mil. USD la BM, deci
  fără debursare), granturile din fonduri fiduciare (nu sunt în seturile IBRD și IDA) și creditele anulate înainte de intrarea în vigoare.
  Paginile de proiect BEI și CEB dau doar aprobarea, starea și (BEI) semnările, fără perioadă și fără plăți; la fel BERD (IATI).
* **Debursările din AMP nu s-au scris**: față de cele ale BM diferă mult (la `dprm1762/2015` AMP are 0, BM 70 mil. USD; la `dp793/2018`
  0,2 mil. EUR față de 23,6 mil. USD); comparația e în foaia „Debursări AMP vs BM” din `surse_oficiale_potriviri_3.xlsx`.

Cu acestea, rămân fără început 288 de rânduri (de la 321), fără final 280 (de la 316) și fără debursare 363 (de la 397), din 466 de rânduri
listate; cele mai multe sunt UE (programe sectoriale, fără plăți publicate pe acord), BERD, BEI, CEB și donatorii bilaterali mici.

**Registrul IATI (a doua trecere), granturile japoneze și evaluările JICA.** A patra rundă de surse oficiale a refăcut potrivirea pe sume
exacte, în moneda originală, între rândurile fără date și activitățile din registrul IATI (prin d-portal), a citit pagina fiecărei activități
potrivite (`q.xml?aid=…`, cu datele exacte) și a adăugat două surse pentru Japonia: fișa Ambasadei Japoniei din decembrie 2010 și evaluările
ex-post JICA. Un rând se leagă de o activitate doar când coincid finanțatorul, titlul și suma (în moneda originală), iar data angajamentului sau
a semnării se potrivește cu cea a rândului; sumele rotunde care se potrivesc fără titlu și dată nu se iau.

* **`date/proiecte_manual.json`**: 22 de intrări noi (21 cu început, 15 cu final), cu toate actele rândului în `acte`.
  * *Registrul IATI (8).* UE 3: `hg1257/2016` (reforma poliției, 14.12.2016 – 13.12.2023), `hg513/2017` (zone rurale, 21.07.2017 – 21.12.2026),
    `hg1363/2016` (Facilitatea pentru cooperare tehnică 2016, 21.07.2017 – 21.07.2027); începutul e „Actual Start” (coincide cu semnarea), finalul
    „Planned End”. AFD 3: `hg996/2023` (CMD100901, 30.09.2024 – 17.12.2025, final real), `hg537/2023` (CMD101001, 12.12.2023 – 28.02.2024, final
    planificat), `hg471/2025` (CMD101601, 17.12.2025 – 17.12.2025, plată unică). JICA: `hg103/2021` (echipamente de prevenire a incendiilor,
    26.11.2021 – 30.11.2024 planificat). DEZA/SDC: `hg574/2025` (CRESTA), doar finalul planificat, 14.06.2029. Citatul e rândul `<activity-date …>`
    din XML-ul activității, iar nota spune ce fel de dată e (reală sau planificată) și cum s-a legat rândul.
  * *Fișa Ambasadei Japoniei, decembrie 2010 (11).* La granturile 2KR (`hg1150/2002`, `hg229/2006`, `hg28/2007`, `hg233/2008`, `hg406/2009`) și la cele
    culturale (`hg1299/2002`, `hg88/2006`) începutul e luna schimbului de note („E/N signed in …”), iar finalul luna finalizării („Completed in …”). La
    cele patru granturi fără proiect pentru IMM (`hg246/2005`, `hg230/2006`, `hg2501/2007`, `hg232/2008`) fișa dă doar luna E/N, deci doar începutul.
    Rândurile se leagă după suma identică în yeni, luna E/N (față de data HG) și tipul grantului.
  * *Evaluări JICA și text de schimb de note (3).* `hg234/2011` (început 11.05.2011 = data E/N; finalul era deja în fișier) și `hg1211/2007` (început
    noiembrie 2007; finalul era deja în fișier), din evaluările ex-post; `hg103/2012` (început 17.04.2012, data notei din textul publicat pe ondrl.gov.md).
* **`date/debursari.json`**: 9 debursări noi, la 8 rânduri. AFD (5): `hg996/2023` 2 × 20 mil. EUR (31.12.2024 și 31.12.2025, adică întreg împrumutul de
  40 mil.), `hg537/2023` 40 mil. EUR (31.12.2023), `hg525/2024` 25 mil. EUR (31.12.2024), `hg471/2025` 25 mil. EUR (31.12.2025); AFD raportează plățile la
  31 decembrie, deci datele sunt de închidere de an, nu ale plăților. DEZA/SDC (1): `hg574/2025`, 250.000 CHF la 31.12.2025 din 1,88 mil. CHF angajați.
  JICA (3), sume finale din evaluările ex-post, datate la finalizare: `hg234/2011` 394 mil. JPY („Actual Grant Amount”, din 417; 02.10.2013), `hg156/2013`
  1.025 mil. JPY („Actual Grant Amount”, din 1.154; 31.01.2016, ziua lipsește) și `hg952/2012` 5.698 mil. JPY („Disbursed Amount”, credit, din 5.926;
  31.05.2018, sfârșitul perioadei efective).
* **Ce nu s-a scris, în rest**:
  * *Termenele din schimburile de note 2KR* (31.03.2003, 31.03.2006, 31.03.2007, 31.03.2008, 31.10.2010, 30.04.2013): sunt perioada în care grantul poate fi
    eliberat, nu finalizarea; la cinci granturi diferă cu 3–6 luni de luna finalizării din fișa Ambasadei, care a fost scrisă ca final.
  * *`hg1211/2007`*: evaluarea JICA dă finalizarea în decembrie 2008, fișa Ambasadei în martie 2009; a rămas decembrie 2008 (din rând). „Contract Amount” (483 mil. JPY)
    e valoarea contractelor, nu o plată, deci nu s-a scris ca debursare.
  * *`hg525/2024`*: are deja 2023–2028 (perioada programului de șase ani, din comunicatul AFD); IATI dă 04.12.2024 pentru această tranșă. S-a adăugat doar debursarea.
    Cele trei împrumuturi AFD pentru reforma energetică (`hg537/2023`, `hg525/2024`, `hg471/2025`; IATI le numește pe ultimele două „faza 2” și „faza 3”) au acum date de natură diferită: de verificat dacă se aliniază.
  * *iDRIP (`hg85/2026`, `hg252/2026`)*: rămân datele de pe pagina AFD; IATI are o activitate de irigații cu alte date și cu începutul înainte de semnare.
  * *`hg574/2025`*: începutul din IATI (01.10.2024) nu s-a scris, fiindcă rândul n-are dată de semnare, iar HG e din 03.09.2025. Celelalte rânduri elvețiene nu
    s-au legat: registrul SDC are 685 de activități pentru Moldova, fragmentate pe credite și ani, cu angajamente care nu coincid cu sumele din registru.
  * *Acordurile USAID pentru obiectivele de dezvoltare din 2016* (`hg938/2016`, `hg1062/2016`, `hg185/2022`, `hg186/2022`, `hg206/2021`): textele din 2021–2022 dau
    termenul de realizare 31.12.2025, dar până în 2024 s-au inițiat 18 amendamente și termenul actual nu s-a putut verifica.
  * *Angajamentele AFD dublate* (80 mil. EUR la `hg996/2023`, 50 mil. la `hg525/2024`, față de împrumuturi de 40 și 25 mil.) nu s-au folosit; plățile din IATI însumează
    exact împrumuturile. Perioadele de execuție din deciziile anuale de finanțare ale UE sunt calculate, nu citabile; fișele BEI și BERD, rapoartele de datorie externă ale MF și
    termenele de tragere din rapoartele Curții de Conturi nu dau perioada proiectului sau plăți pe acord.
* Detaliile (citate, adrese, motivele) sunt în `surse_oficiale_potriviri_4.xlsx`, livrat odată cu aceste fișiere (nu e în repository).

Cu acestea, rămân fără început 267 de rânduri (de la 288), fără final 265 (de la 280) și fără debursare 355 (de la 363), din 466 de rânduri
listate; cele mai multe sunt UE (acorduri de finanțare fără plăți publicate pe acord), BERD, BEI, CEB, Elveția (activități fragmentate) și donatorii bilaterali mici.

**Descrieri din Banca Mondială, din registrul IATI și din fișa Ambasadei Japoniei; angajamente și plăți KfW.** A cincea rundă a căutat ce mai lipsea
pe cele cinci câmpuri (descriere, început, final, angajament, debursare) în surse oficiale citite altfel sau încă nefolosite: API-ul public al proiectelor
Băncii Mondiale (`search.worldbank.org/api/v2/projects`, câmpul `pdo` — obiectivul de dezvoltare — sau, la proiectele vechi, `project_abstract`), registrul IATI
prin d-portal (activitățile KfW/GIZ publicate de BMZ, DEZA/SDC și UE/DG NEAR, câmpul `description`, plus datele și tranzacțiile KfW) și fișa Ambasadei Japoniei.
Rândurile s-au legat ca înainte: după finanțator, titlu (sau numărul creditului din Finances One) și, unde rândul are, după sumă și dată. Textul englez al fiecărei
descrieri e cel al sursei (cu „…” unde s-a omis o propoziție), cel românesc e traducerea, iar `citat` e un fragment exact din sursă, verificat pe înregistrarea originală.

* **`date/proiecte_manual.json`**: 71 de intrări noi (347 în total): 70 cu descriere și 4 cu date (trei dintre ele au și descriere; `hg132/2026` doar final).
  * *Banca Mondială (41 de descrieri).* La rândurile cu număr de credit, legătura e cea din runda a treia (Finances One: credit, instrument, data semnării); la celelalte,
    denumirea proiectului, unică în API. Un proiect cu mai multe rânduri (RISP II: `hg230/2009`, `hg736/2008`, `hg378/2006`) dă aceeași descriere fiecărui rând.
    `nota` dă numărul proiectului (`P…`) și motivul legării. La patru proiecte (cele două credite PRSC, fondul de investiții în sănătate și programul de apă și canalizare) fișa are semne stricate
     (de pildă „Government#s”, „inselected”, „,,services”): textul englez s-a oprit sau s-a întrerupt cu „…” înaintea lor, ca să rămână exact cel al sursei.
  * *KfW/GIZ prin IATI (6 intrări).* Descrieri la `omded116/2025` (IMM, faza II), `ome27/2025` (eficiență energetică în clădiri publice), `hg778/2022` (securitate
    energetică), `hg1074/2017` (Inițiativa sanitație, Cahul) și `hg319/2016` (modernizarea serviciilor comunale, GIZ). Date: `hg778/2022` 18.11.2022 – 31.03.2023
    (ambele reale, activitate încheiată), `hg1074/2017` 01.08.2018 (real) – 30.06.2027 (planificat), `hg319/2016` doar finalul real, 30.01.2019, și `hg132/2026` doar finalul
    planificat, 31.01.2029; începuturile din 2010, respectiv 01.02.2026, sunt înainte de hotărâri (22.03.2016 și 25.03.2026), deci nu s-au scris. Hotărârile
    HG778/2022 și HG1074/2017 numesc proiectul ca activitatea IATI (a doua, „colaborarea financiară pentru anul 2016 (proiectul «Iniţiativa sanitaţie»)”), iar angajamentul KfW pentru
    prima vine la nouă zile după hotărâre.
  * *DEZA/SDC prin IATI (10 descrieri)*: `hg284/2015`, `hg493/2016`, `hg838/2014`, `hg603/2019`, `hg138/2020`, `hg27/2024`, `ommps183/2024`, `hg574/2025`, `hg243/2020`, `hg490/2016`.
    La proiectele cu mai multe faze s-a luat descrierea fazei în care cade hotărârea (nota dă perioada). Numai descrierea: perioadele și sumele din IATI sunt pe credite și pe ani.
  * *UE, DG NEAR prin IATI (7 descrieri)*: `hg1363/2016`, `hg513/2017`, `hg1257/2016`, `hg352/2019`, `dp34/2021`, `hg717/2020`, `hg432/2021` — aceleași activități de la care veneau deja datele rândurilor.
  * *Fișa Ambasadei Japoniei (7 descrieri)*: cinci granturi 2KR (`hg1150/2002`, `hg229/2006`, `hg28/2007`, `hg233/2008`, `hg406/2009`) și două culturale (`hg1299/2002`, `hg88/2006`).
    Fișa nu enunță obiective: descrierea e programul și bunurile livrate, în formularea ei („32 Sampo combine harvesters”).
* **`date/sume_manual.json`**: 2 angajamente noi, cu `extern` și adresa activității IATI: `HG778/2022` (40 mil. EUR; descrierea IATI spune „The project volume of EUR 40 million”) și
  `HG1074/2017` (10 mil. EUR, angajament din 01.08.2018). Amândouă sunt granturi (IATI: tip de finanțare 110). `date/acorduri_legare.json` și `legis_acorduri.html` s-au refăcut cu
  `legatura_acorduri.py` și `legis_pagina.py`: 339 de acorduri cu sumă (de la 337), singurele schimbări fiind cele două rânduri.
* **`date/debursari.json`**: 3 plăți noi, toate KfW (BMZ): `hg778/2022` 40 mil. EUR (28.11.2022, activitate încheiată), `hg1074/2017` 9.488.074,47 EUR din 10 mil. (18.06.2026) și `ome27/2025`
  405.576 EUR din 38,7 mil. (09.04.2026). BMZ publică o singură tranzacție „Disbursement” pe activitate: valoarea e cumulată, iar data e a tranzacției din IATI, nu neapărat a ultimei plăți
  (nota fiecărei intrări o spune). La `omded116/2025` IATI arată 0 plătit, deci nu s-a scris nimic.
* **Ce nu s-a scris**:
  * *Schimburile de note germane fără proiect numit* (`hg299/2020`, `hg607/2019`, `hg640/2020`, `hg266/2022`) și `hg112/2024`, a cărei hotărâre acoperă patru proiecte (IMM, IMM măsuri adiționale,
    Programul deschis de dezvoltare urbană și măsurile lui adiționale) pe un rând care poartă numele ultimului: nicio descriere, dată sau sumă.
  * *GIZ*: angajamentele din IATI (de pildă 35,35 mil. EUR la „Strong Businesses and Communities”) nu coincid cu sumele din registru, deci nu s-au scris sume sau plăți; `hg316/2023` (Cahul II) n-are în IATI o activitate cu acest titlu.
  * *DEZA*: `hg21/2022` (CREATIVO) nu are descriere în IATI; la nicio activitate elvețiană nu s-au scris perioade, sume sau plăți (fragmentate pe credite și ani).
  * *UE*: `hg351/2019` și `hg353/2019` (acțiuni din aceeași zi, legătură neclară) nu s-au atins; IATI dă la UE plăți doar la nivelul contractelor.
  * *Banca Mondială*: 23 de rânduri BIRD/AID rămân fără descriere (operațiuni de politici și credite de ajustare structurală, granturi mici din fonduri fiduciare, câteva acte din 2026 și altele pe care nu s-a putut lega sigur
     un proiect cu text în API). La `hp204/1998` (First Cadastre Project)
    registrul are data semnării 07.07.2005, iar Finances One 08.06.1998: descrierea s-a scris după denumirea proiectului (P035771), diferența rămâne de verificat.
  * *Japonia*: cele patru granturi fără proiect pentru IMM (`hg246/2005`, `hg230/2006`, `hg2501/2007`, `hg232/2008`): fișa nu spune ce au finanțat.
  * *BERD*: registrul IATI al BERD are 63 de activități pentru Moldova, din 2016 încoace. Cele zece rânduri BERD rămase fără descriere sunt: șase mai vechi sau fără proiect de sine stătător în IATI (Termocom,
     creditul din 1996, terminalul petrolier Giurgulești, Apă-Canal Chișinău și cele două rânduri ale aeroportului, `hp119/1998` și `hg1450/2008`), hotărârea de împuternicire `hg41/2011` și trei rânduri „CET-Nord”
     (`hg690/2014`, `dprm1952/2016`, `dp1044/2018`); pentru acestea IATI are doar faza a II-a („GrCF2 W1-Balti District Heating Phase 2”, 24.12.2021), iar rândurile grupează actele ambelor faze, deci nu s-a scris nimic.
* Detaliile (citate, adrese, motivele) sunt în `surse_oficiale_potriviri_5.xlsx`, livrat odată cu aceste fișiere (nu e în repository).

Cu acestea, rămân fără descriere 226 de rânduri (de la 296), fără sumă 132 (de la 134) și fără debursare 352 (de la 355), din 466 de rânduri listate; dintre cele fără descriere,
cele mai multe sunt UE (64), Banca Mondială (23), Japonia (12), BERD (10), China (10), SUA (9) și donatorii bilaterali mici. Datele s-au scris la patru rânduri, deci fără început
scad cu 2 și fără final cu 4 (niciunul din cele patru nu avea date în AMP): cu raportul AMP din 08.11.2026, pagina publicată număra 252 de rânduri fără început și 250 fără final,
adică 250 și 246 după aceste date. La început și la final cifrele depind de raportul AMP, care se schimbă, deci pot diferi de cele din rundele de mai sus.

**Codul de acces și „baza de date".** Site-ul e static (GitHub Pages): n-are server care să primească
date. Singurul loc în care o pagină poate scrie fără un serviciu în plus e chiar repository-ul, prin
API-ul „Contents" al GitHub. „Baza de date" e deci fișierul `date/debursari.json`; pagina îl citește ca pe
un fișier public, iar pentru scriere folosește „codul": un *fine-grained personal access token* cu drept
doar pe acest repository. Fără cod pagina se poate citi, iar editarea (datele de început și de finalizare,
suma proiectului, debursările) e blocată pentru toate acordurile deodată; „Introdu codul" e în bara de sus.

Cum faci codul, o singură dată:

1. Cu contul care deține repository-ul, deschide https://github.com/settings/personal-access-tokens/new
   (în fereastra „Introdu codul", „Cum obțin codul?" → „Deschide GitHub" deschide pagina cu o parte din
   câmpuri completate).
2. **Repository access** → *Only select repositories* → `acorduri` (alegerea o faci tu; nu se poate
   completa din link).
3. **Permissions → Repository permissions → Contents** → *Read and write*. Nimic altceva.
4. **Generate token** și copiază codul (începe cu `github_pat_`; se arată o singură dată). Expiră după
   ce ai ales (90 de zile în link); când expiră, pagina spune „Codul nu e valid sau a expirat" și faci
   unul nou.
5. În pagină, în bara de sus: **Introdu codul** → lipești codul → **Deblochează** (o singură dată, pentru toate acordurile). Poți bifa „Ține minte codul pe acest
   dispozitiv, protejat cu un PIN": codul se păstrează în browser criptat (PBKDF2-SHA256 cu 250.000 de
   iterații + AES-GCM) și la următoarea vizită se deblochează cu PIN-ul. Fără PIN, codul rămâne doar în
   memoria paginii și dispare la reîncărcare. „Blochează" îl scoate din memorie.

**Codul nu se pune niciodată într-un fișier, într-o pagină sau într-un mesaj** (nici în acest repository,
nici în cod): oricine îl vede poate scrie în repository. Pagina îl trimite numai către `api.github.com`,
în antetul `Authorization`; testele verifică asta (nicio cerere în afara paginii și a GitHub, codul nu apare
în stocarea browserului decât criptat, nici în HTML). GitHub nu poate limita un cod la un singur fișier: cine
îl are poate scrie în tot repository-ul (nu și în `.github/workflows`, pentru care GitHub cere un drept
separat), deci și în paginile site-ului. De aceea codul se face doar pe repository-ul `acorduri`, cu termen
de expirare, și se șterge când nu mai e nevoie. Dacă un cod a ajuns undeva unde nu trebuia, se șterge din
GitHub (Settings → Developer settings → Personal access tokens) și se face altul.

**Ce se întâmplă la o salvare.** Fiecare debursare are: data, suma, valuta, o notă (cel mult 200 de
caractere) și acordul. Adăugarea, editarea și ștergerea sunt operații pe fișier: pagina citește starea
de acum a fișierului prin API, aplică operația și îl scrie înapoi, cu `sha`-ul citit. Dacă între timp altcineva
a scris (GitHub răspunde 409 sau 422), pagina citește din nou și reaplică aceleași operații, de cel mult
patru ori: nimeni nu pierde ce a introdus. Fiecare salvare e un commit, cu un mesaj de felul
`Debursări: adăugat: <proiectul> — 1.250.000 EUR (2026-09-30)`, deci istoricul se vede în GitHub
(fila *History* a fișierului) și o greșeală se poate anula acolo. Dacă salvarea nu reușește (fără internet,
cod expirat), modificarea rămâne într-o coadă păstrată în browser și se trimite la deblocarea următoare;
fereastra spune ce n-a mers.

**Ce știe oricine.** Debursările din `date/debursari.json` sunt publice, ca tot restul repository-ului:
oricine deschide pagina le vede, fără cod. Site-ul de pe GitHub Pages se actualizează cu o întârziere de
1–2 minute după un commit; ca omul care a salvat să nu vadă o stare veche, pagina ține în browser o copie
a ultimei salvări, valabilă zece minute. Un alt dispozitiv vede salvarea după publicare.

**Debursări fără acord găsit.** Fiecare debursare păstrează și codurile actelor acordului (`acte`, cel mult
12). Dacă registrul se schimbă (un acord e unit cu altul, i se schimbă id-ul), debursarea își regăsește
acordul după aceste coduri. Dacă nu-l găsește, apare în panoul „Debursări fără acord găsit": nu se pierde,
nu intră în totalurile pe donatori și se vede în „Excel · total".

**Excel.** Trei butoane, toate cu fișiere stilizate (`xlsx-stil.js`, ca restul exporturilor), care urmează
filtrele active (căutarea, tipul, cu/fără debursări) și le trec în subtitlul foii:

| Buton | Fișier | Foi |
|---|---|---|
| **Excel · BERD** (numele donatorului, în capul tabelului lui) | `debursari-berd-2026-10-26.xlsx` (donatorul și data) | foaia donatorului (un rând pe proiect: denumire, descriere succintă = obiectivele proiectului, data efectivă de începere, data finalizării, tip, stadiu, semnat, suma proiectului, valuta, echivalent EUR, debursat în valuta proiectului și în EUR, % debursat, rest de debursat, număr de debursări, ultima debursare, „Intră în total?”, sursa obiectivelor și a datelor, link legis.md) și „Debursări" (fiecare debursare introdusă) |
| **Excel · total** | `debursari-total-2026-10-26.xlsx` | „Total" (fiecare proiect o singură dată, cu coloana „Donatori"), „Pe donatori" (rezumat) și „Debursări" |
| **Excel · pe donatori** | `debursari-pe-donatori-2026-10-26.xlsx` | „Rezumat", câte o foaie pentru fiecare donator și „Debursări" |

O dată întreagă (de pildă 30.06.2029) e dată adevărată în Excel, deci se poate sorta și filtra; una cunoscută doar cu luna și anul (03.2026) sau doar cu anul (2026) rămâne text, cât spune sursa. Notele de sub tabel spun sursele obiectivelor și ale datelor, rândurile omise și starea AMP.
Cu donatori bifați, „total" și „pe donatori" cuprind doar donatorii bifați; fără niciunul, pe toți (și
debursările fără acord găsit). Pe foile cu proiecte și pe cea cu debursări, rândul de total e formulă
`SUBTOTAL`, deci se recalculează când filtrezi în Excel. În foaia „Pe donatori" („Rezumat"), rândul „Total
general" numără un acord cofinanțat o singură dată, deci nu coincide cu suma coloanei.

**Unde se schimbă ce.** Repository-ul, ramura și calea fișierului de date sunt în `CONFIG`, la începutul
lui `debursari.js` (de schimbat dacă repository-ul se mută sau se redenumește). Lista donatorilor, cu
denumirile lor complete (indiciul de sub acronim), e `NUME_DONATOR` din același fișier; un donator nou
din registru apare singur, doar fără denumire completă.

**Teste.** `node teste_debursari.js` (logica: sume față de o socoteală independentă, obiective și date cu
sursele lor și ordinea lor, rânduri omise, operații, conflicte, PIN, specificațiile Excel) și
`node teste_amp_date.js` (datele din AMP: potrivirea, arhiva și raportul live). `python teste_debursari.py`
verifică fișierele paginii (scripturi prezente, niciun cod GitHub în fișiere, forma lui `date/debursari.json` și
a lui `date/proiecte_manual.json`: fiecare intrare cu sursă și citat, fiecare rând găsit în registru, niciun rând
în două intrări); cu `--browser` deschide pagina cu Chromium împotriva unui GitHub simulat (coduri greșite sau
fără drept de scriere, conflicte de scriere, rețea căzută, fișier lipsă) și parcurge: donatorii și tabelul față
de o socoteală independentă, coloanele (inclusiv obiectivele și cele două date, pe desktop, pe telefon și în
engleză), formularul „Date despre proiect" (introducere, editare, ștergere, coada nesalvată, mesajele commit),
panourile „AMP", „Rânduri omise" și „Date fără acord găsit", câmpurile blocate, deblocarea, debursările (adăugare,
editare, ștergere, verificarea fișierului scris), coada după reîncărcare, PIN-ul, debursări existente și orfane,
cele trei fișiere Excel (deschise cu openpyxl; datele întregi sunt date adevărate), engleza, telefonul, lățimea
paginii cu toți donatorii bifați (de la 1920 la 390 px), starea din adresă, tastatura, lipsa erorilor JavaScript și a cererilor spre alte adrese decât pagina, `api.github.com`
și `amp.vivi.md`, plus fereastra proiectului (secțiunea 22: deschidere, închidere, focus, derulare, componente, telefon) și proiectul unit de mână (secțiunea 23: Federația Rusă, un rând cu trei componente). Cu `--doar 13,14` rulează doar secțiunile numerotate (secțiunile 1–12 rulează doar fără `--doar`).

**Limite.** Debursările sunt cele introduse de oameni și nu sunt verificate față de AMP sau o altă sursă;
pagina nu le leagă de proiectele AMP („De la lege la bani" arată debursările din AMP). Obiectivele din
`date/proiecte_manual.json` sunt traduse în română din documentul oficial (adresa și citatul exact sunt păstrate),
iar ce nu s-a găsit rămâne gol. „Data finalizării" din AMP e data propusă de terminare, nu cea reală. Datele din
AMP se văd doar la proiectele legate sigur de un acord, iar raportul live trebuie să răspundă din browserul tău
(altfel pagina arată arhiva, până în 2022). Un acord al cărui partener nu e recunoscut în registru apare la
„(neidentificat)". Data „semnat" e cea din registru; la câteva rânduri registrul o arată greșit (coloana
`Semnat` din registrul legis.md, de pildă la HG174/2006), iar pagina o preia ca atare.

## Exporturile Excel ale graficelor și tabelelor

Fiecare panou cu roată dințată (⚙) are în meniu trei acțiuni: **Copiază ca imagine**, **Descarcă Excel (.xlsx)**
și **Date brute (CSV)**. Trei butoane de sub tabele (tabelul „De la lege la bani”, diferențele AMP–IATI, proiectele
cu perioadă în afara anilor) dau acum tot Excel, nu CSV. CSV-ul a rămas ca a doua opțiune, pentru cine îl vrea.

**Ce conține fișierul.** Un rând de titlu (denumirea panoului) și un subtitlu cu sursa, selecția activă (anii și
donatorii aleși, căutarea, raionul etc.) și data generării; apoi tabelul, cu antet colorat, filtre pe coloane și
antet înghețat la derulare. Sumele au separator de mii (nu text), anii sunt numere întregi, procentele sunt procente,
diferențele au semn (verde/roșu la cele în care sensul contează), iar dungile alternante rămân și după sortare.
Unde are sens: bare în celule, scară de culoare (matricea donator × an, sector × donator), rând de total, hyperlinkuri
spre AMP, IATI sau registru, note sub tabel și, la panourile cu grafic, același grafic ca **grafic Excel nativ**
(bare, coloane, coloane stivuite sau linie), pe care îl poți edita. Foaia se tipărește pe lățimea unei pagini A4 pe lat, cu
antetul repetat și numărul paginii în subsol.

**Totalurile.** La donatori, sectoare, beneficiari, țări și tipuri de asistență un proiect cu mai mulți donatori
apare la fiecare, cu suma lui întreagă; totalul e deci al **proiectelor unice** (se numără o singură dată) și poate fi
mai mic decât suma rândurilor — o notă de sub tabel spune asta. La ani, regiuni și la statusurile din D-portal rândurile
se adună, iar totalul e formulă `SUBTOTAL`: se recalculează când filtrezi în Excel. Graficele din „Analize avansate”
nu folosesc filtrele din pagina principală (subtitlul o spune).

**Cum se leagă un panou nou.** Randarea panoului înregistrează datele lui cu
`__csvInreg(element, coloane, rânduri, opțiuni)` (în `index.html`); dacă tabelul e mare sau scump de construit,
cu `__csvInregLazy(element, () => ({cols, rows, opt}))`, calculat abia la export. `unelte.js` le citește (și, dacă
panoul n-a înregistrat nimic, ia tabelul vizibil). Opțiunile (`opt`), toate facultative:

| Opțiune | Ce face |
|---|---|
| `tip` | Un caracter pe coloană: `t` text, `i` identificator, `e` sumă în EUR, `n` număr întreg, `y` an, `k` loc în clasament, `p` procent dat în puncte (83,5 → 83,5%), `x` diferență cu semn (verde/roșu), `s` diferență cu semn, fără culori, `v` variație procentuală (verde/roșu), `d` două zecimale, `z` dată (ISO sau zz.ll.aaaa) |
| `total` | `{eticheta, suma:[coloane], raport:{col:[numărător, numitor]}}`: rând de total cu formule `SUBTOTAL` |
| `randTotal` | Un rând de total scris ca atare (numai în Excel), pentru totalurile care nu sunt suma rândurilor (proiecte unice) |
| `totalFinal` | Ultimul rând din `rows` e deja totalul (apare și în CSV); în Excel iese din filtru și devine rândul de total |
| `grafic` | `{tip:'bar'\|'col'\|'colst'\|'line', cat, serii:[coloane], n, ultimele, culori, titlu}`: graficul Excel; `n` = primele n rânduri, `ultimele` = ultimele n, `fara` = câte rânduri nu intră în grafic (doar pentru titlul „primele n”) |
| `bare`, `harta` | Bare în celule pe coloanele date; scară de culoare `{de, pana}` pe un bloc de coloane |
| `linkuri` | `{coloană: (rând, i) => adresă}`: celulele devin hyperlinkuri adevărate |
| `nota`, `context` | Note sub tabel; textul care înlocuiește „selecția” din subtitlu |
| `foiExcel` | `[{foaie, titlu, cols, rows, opt}, …]`: panoul cere un fișier cu **mai multe foi**. Prima foaie primește notele panoului și linkul „Deschide dashboardul”; `cols`/`rows` ale panoului rămân lista plată pentru CSV. Un link dintr-o foaie spre alta se scrie `#Numele foii` (numele cerut; dacă la scriere s-a schimbat din cauza unui duplicat, linkul îl urmează) |

Butoanele care nu pornesc dintr-un panou apelează `window.__xlsxDirect({titlu, nume, vedere, cols, rows, opt, btn})`;
`btn` e butonul apăsat, al cărui text revine după descărcare (roata dințată își schimbă singură iconița).

**Teste.** `python teste_xlsx.py` (scriitorul, cu Node) și `python teste_xlsx.py --browser` (15 panouri în română și
engleză, plus cele trei butoane). La construire, fișierele au fost validate pe schemele ISO/IEC 29500, citite cu
openpyxl și randate cu LibreOffice; într-un Excel adevărat n-au fost deschise, așa că, dacă Excel cere „reparare”,
păstrează fișierul și spune-ne ce panou l-a dat, ca să fie corectat.

## Indicatorii din capul registrelor (KPI)

Cele două carduri de sus, la fel în ambele registre (legis.md și Monitor), arată:

| Card | Ce arată |
|---|---|
| **Acorduri** | numărul de acorduri, „din N acte publicate” și o fâșie pe tipuri de finanțare, cu legenda alături (numele și numărul fiecărui tip) |
| **Creditori** | numărul de finanțatori distincți și primii trei, după numărul de acorduri, cu bare proporționale cu cel mai mare |

Cardurile „Ratificate sau aprobate” și „Cu dată de intrare în vigoare” au fost scoase (13 octombrie 2026). Cifra de la etapa 4
din 5 se vede în continuare în panoul „Cum se încheie un acord” din registrul Monitor (pe legis.md panoul e ascuns, locul lui îl
ia panoul de sume, mai jos), iar data intrării în vigoare, pe rândul fiecărui acord („În vigoare din …”) și în exportul Excel
(coloanele „În vigoare din” și „Temeiul datei”).

Culorile fâșiei sunt ale tipurilor din diagrama „Acorduri noi pe an” (primele patru sloturi validate pentru daltonism) și au
mereu legenda alături: culoarea nu e singurul lucru care spune ce e un segment.

**Pe ecrane mici.** Cele două carduri stau mereu pe același rând, de la 1400 la 340 px. Sub 700 px rămân scunde: fâșia,
legenda, barele creditorilor și pictogramele dispar, iar creditorii se citesc ca text („AID · UE · BIRD”).

**Unde e codul.** `kpi()`, `kpiTipuri()` și `kpiCreditori()` în `acorduri.html` (șablonul; `legis_acorduri.html` se
regenerează cu `python legis_pagina.py`, care nu atinge indicatorii). Testele: `python teste_legis.py --browser`, secțiunea
„indicatorii (KPI)”.

## Panoul „Sumele acordurilor, pe tipuri de finanțare” (legis.md)

Panoul stă imediat sub indicatori (și pe telefon, înaintea listei). Îl desenează doar registrul legis.md; în Monitor, în locul lui,
stă panoul „Cum se încheie un acord”. Are patru părți, în limbajul vizual al indicatorilor:

1. **Totalul.** „Acordurile cu sumă cunoscută adună”, cifra mare în euro (la cursul din data trecută în titlul panoului) și
   „n acorduri din N”.
2. **Bara.** Structura totalului pe tipuri de finanțare într-o singură bară, cu legenda alături: numele și procentul fiecărui tip.
3. **Cardurile pe tip.** Câte unul pentru Grant, Împrumut, Asistență tehnică (și pentru „Asistență financiară”, dacă un acord
   rămâne neclarificat): suma tipului, „n acorduri cu sumă din M · P% din total” și cele mai mari trei acorduri ale tipului, cu
   suma lor în valuta acordului. Un clic pe card filtrează lista pe tipul lui. Culoarea tipului e aceeași în card, în bară, în
   legendă și în fâșia din indicatori.
4. **Socoteala.** „Din cele 466 de acorduri: 325 se adună în total · 9 au suma pe rând, dar nu se adună · 132 nu au încă suma în
   registru” (cifrele de la 13.10.2026), iar dedesubt cele 9 sunt descompuse: câte unul care repetă același acord pe alt rând (acum niciunul),
   cele cu suma marcată „nu se adună” (se regăsește în alt acord sau e a unui program întreg) și cele într-o valută fără curs de
   conversie. Cele trei cifre dau mereu numărul tuturor acordurilor; „Totalul e un minim, nu tot ce s-a semnat”.
   „Repetă același acord” = aceeași sumă, aceeași valută, același finanțator și aceleași prime cuvinte din denumire; numărul tranșei
   din denumire intră și el în cheie, ca tranșele aceluiași program (granturile sectoriale japoneze: trei de câte 300 mil. yeni, câte un
   schimb de scrisori pe an) să nu fie luate drept același acord. O dublură adevărată se rezolvă la sursă, cu `date/contopiri_manual.json`.

Sub ele, „Pe valute și cum s-a făcut conversia” (închis, cu tabelul pe tip și valută și regulile de conversie).

Cifrele vin din `statSume()`, același cod care hotărăște „Intră în total?” în exportul Excel: pagina și fișierul nu pot ieși
diferit. Dacă un acord nu e numărat, rândul lui spune de ce (dublură, „nu se adună”, fără curs).

**Pe telefon** (sub 700 px) cele trei tipuri devin rânduri într-un singur chenar (tipul în stânga, cu numărul de acorduri și
procentul dedesubt; suma în dreapta), iar „Cele mai mari” și legenda barei dispar (numele și procentul rămân pe rânduri).
Panoul e mai scund de 700 px, ca lista să nu coboare sub un ecran de explicații.

**Unde e codul.** `panouSume()` și `statSume()` în `acorduri.html`. Testele: `python teste_legis.py --browser`, secțiunea
„panoul Sumele acordurilor”: totalul față de cardurile lui, procentele, proporțiile barei, culorile, cele 551 de acorduri
împărțite în trei, cele mai mari trei pe tip față de `window.__ACORDURI__`, clicul pe card, lățimile de la 340 la 1400 px,
ordinea pe telefon și traducerea în engleză.

## Exportul Excel din registrele de acorduri

Butonul „Excel” din antetul listei (în ambele registre, legis.md și Monitorul Oficial) descarcă **exact ce e pe ecran**:
aceleași filtre (tip de finanțare, etapă, finanțator, an, suport bugetar, căutarea), aceeași ordine, aceeași vedere.
Fișierul arată ca exporturile din dashboard: titlu și context (sursa, filtrele active, câte acorduri, cursul, data), antet
colorat, filtre pe coloane, culori, date și sume ca valori adevărate (se sortează și se adună), linkuri care se deschid.
Numele lui spune vederea, tipul filtrat și data: `registru-acorduri-2026-10-12.xlsx`, `registru-acorduri-grant-2026-10-12.xlsx`,
`registru-acte-2026-10-12.xlsx`.

**Vederea „Acorduri”** dă trei foi:

| Foaie | Ce conține |
|---|---|
| Acorduri | Un rând pe acord, 29 de coloane în cinci grupe (ACORD · SUMA ȘI TOTALUL · PARCURSUL ACORDULUI · ACTELE PUBLICATE · SURSE ȘI DETALII): denumirea, partenerul, tipul de finanțare (colorat), suportul bugetar, suma și valuta, echivalentul în EUR, **„Intră în total?”**, data semnării, etapele 1–5 și etapa atinsă, intrarea în vigoare și temeiul datei, anii, numărul de acte, prima și ultima publicare, sursa sumei cu fragmentul din act, costul total al proiectului, denumirea completă, linkul spre sursă și linkul spre acordul din registru (`#acord=…`). Prima coloană și antetul rămân pe loc la derulare; la tipărire se repetă pe fiecare pagină. Rândul de total e formulă `SUBTOTAL` și se recalculează când filtrezi în Excel |
| Sume pe tipuri | Cifrele panoului „Sumele acordurilor, pe tipuri de finanțare” (îl desenează doar legis.md; în Monitor regulile sunt aceleași), calculate pentru rândurile exportate, cu grafic Excel nativ |
| Pe valute | Suma în valuta acordului, cursul de conversie (BCE, la data trecută în pagină) și echivalentul în EUR, pe tip și pe valută |

**Vederea „Acte”** dă o singură foaie, „Acte”: un rând pe act (data ediției, ediția, actul, tipul de finanțare, suportul bugetar,
partenerul, etapa, denumirea acordului, titlul complet, data semnării și linkul), cele mai noi primele, cu data, ediția și
actul înghețate la derulare. O căutare fără rezultate dă un fișier valid, doar cu antetul și o notă.

**De ce există „Intră în total?”.** Dacă ai aduna coloana „Echivalent EUR” pe toate rândurile care au sumă, ai obține mai mult
decât arată pagina: unele rânduri au suma afișată, dar nu se adună (acordul e numărat la alt act sau suma nu e cea acordată),
iar altele repetă același acord (aceeași sumă, același finanțator, aceeași denumire). De aceea echivalentul în EUR apare doar
pe rândurile care intră în total; celelalte spun motivul: „nu: dublură”, „nu: nu se adună”, „nu: fără curs”. Același cod
(`statSume`) hotărăște ce se adună în pagină și în fișier. Testele compară totalul din fișier cu cel din panoul legis.md și,
rând cu rând, cu `window.__ACORDURI__`, pe ambele pagini.

**Rezerva.** `xlsx-stil.js` se încarcă abia la primul clic, cu `?v=` din constanta `STIL_V` (se schimbă la fiecare modificare a
lui, ca browserul să nu țină varianta veche). Dacă nu se poate încărca (rețea blocată, fișier lipsă), pagina scrie vechea foaie
simplă, cu aceleași rânduri (fără stil, dar cu datele întregi și cu linkurile) și lasă un avertisment în consolă.

**Șablonul și pagina generată.** `acorduri.html` e șablonul; `legis_acorduri.html` se scoate din el cu `legis_pagina.py`, prin
înlocuiri de text exacte. Exportul n-a cerut înlocuiri în plus în afara a două constante, `EXPORT_SURSA` (sursa din subtitlu) și
`EXPORT_PREFIX_EDITIE` (`'MO '` doar la Monitor), al căror text trebuie să apară exact o dată în șablon. După orice
modificare în șablon se rulează `python legis_pagina.py`.

**Câmpurile și tipurile adăugate lui `xlsx-stil.js`** (folosite de registre; dashboardul le poate folosi și el):

| Câmp sau tip | Ce face |
|---|---|
| `inghetaColoane: n` | primele n coloane rămân pe loc la derularea spre dreapta, împreună cu antetul; la tipărire se repetă |
| `grupe: [{de, pana, text}]` | o bandă cu denumirile grupelor, deasupra antetului (celule unite, culori alternante) |
| `etichete: {coloană: [[text, culoareText, culoareFundal], …]}` | colorează celulele cu valoarea exactă dată („Grant”, „da”): formatare condițională, deci culorile urmează valoarea la sortare și la editare |
| `maxLinii: n` | un rând cu text lung se înalță cel mult la n linii (text aliniat sus); restul se citește în bara de formule |
| `paginiLatime: n \| 'auto'` | pe câte pagini în lățime se tipărește tabelul (`auto`: una la fiecare 150 de caractere de lățime de coloană), în loc să fie micșorat la una |
| tip `m` | marcaj centrat, verde (de ex. „da”) |
| tip `c` | cod scurt, centrat, ca text (valuta, „Intră în total?”) |
| tip `r` | curs sau rată, cu patru zecimale |
| tip `l` | text lung pe o singură linie, fără împachetare: nu înalță rândul |

**Teste.** `python teste_xlsx.py` (secțiunea „registru:”: foile construite cu Node) și `python teste_legis.py --browser`
(fișierele descărcate din ambele pagini: fără filtre, cu filtre, căutare fără rezultat, vederea „Acte” și rezerva). La construire,
fișierele au fost validate pe schemele ISO/IEC 29500, citite cu openpyxl și randate cu LibreOffice; într-un Excel adevărat
n-au fost deschise.

## Donatori → sectoare, cu proiectele fiecărui sector

Panou în „Analize avansate”, imediat după „Sector × donator”. A fost cerut așa: „o diagramă cu donatori și cu sectoare
și lista de proiecte pe fiecare sector”. Are trei părți, pe aceeași alegere (măsura, perioada, donatorul, sectorul):

1. **Diagrama.** Donatorii (primii 12 după măsura aleasă, plus „Alți donatori”) în stânga, sectoarele (toate cele cu
   sumă, cel mult 30, plus „Alte sectoare”) în dreapta. **Lungimea barei = totalul donatorului sau al sectorului, cu fiecare
   proiect numărat o singură dată**, deci cifrele sunt aceleași cu „Top donatori” și cu panoul „Distribuție pe sectoare” din
   pagina principală (testele compară cu `RAW` și cu `aggregateBySector`). **Grosimea liniei** dintre un donator și un sector =
   suma proiectelor donatorului în sectorul acela. Măsura se alege între angajamente și debursări; perioada e anul de
   început al proiectului (proiectele fără an nu intră când o perioadă e aleasă). Lista „Donator” cuprinde toți
   donatorii, cu numărul de proiecte; unul din afara primilor 12 primește un rând în plus în diagramă.
2. **Lista „Proiectele fiecărui sector”.** Un grup pliabil pe sector (numărul de proiecte, angajamente, debursări), în
   ordinea sumei. Grupul deschis arată tabelul proiectelor: AMP ID (link spre AMP, ca peste tot), proiect, donator,
   perioadă, sume; câte 100 odată, cu „Încă 100”. Un clic pe un donator, pe un sector sau pe o linie din diagramă
   filtrează lista. Dacă după un clic pe un donator perechea cu sectorul ales nu are niciun proiect, alegerea veche se lasă
   (lista nu rămâne goală). Cu tastatura: Tab între rânduri, Enter sau Spațiu aleg, Escape scoate alegerea.
3. **Excel.** ⚙ → „Descarcă Excel (.xlsx)” sau butonul „Excel” din antetul listei dă un fișier cu mai multe foi:
   „Rezumat pe sectoare” (proiecte, sume, donatori și donatorul principal pe sector, cu grafic Excel și un link de la
   fiecare sector spre foaia lui), „Donator × sector” (matricea, cu scară de culoare), „Toate proiectele” (lista plată,
   aceeași cu CSV-ul) și câte o foaie pe sector, cu total ca formulă `SUBTOTAL` și AMP ID-uri legate de AMP. Fișierul
   respectă alegerea din pagină: cu un sector ales conține doar acel sector, și subtitlul spune asta.

**De ce bare și linii, nu un Sankey.** Un proiect cu mai multe sectoare apare cu suma lui întreagă în fiecare (așa
numără tot dashboardul). Într-un Sankey înălțimea unui donator ar fi suma liniilor lui, deci mai mare decât totalul
real: la FMI, 1.213 mil EUR în loc de 660 mil. Cu bare separate, totalurile rămân cele adevărate, iar liniile spun doar
„cât din banii donatorului merge în sectorul acela”. Pentru același motiv, suma de pe rândurile unei foi de sector nu se
adună cu a celorlalte: rândul „TOTAL (proiecte unice)” din „Rezumat” și din „Toate proiectele” numără fiecare proiect o
singură dată, iar o notă de sub tabel spune asta.

**Teste.** `python teste_sectoare.py` (logica, diagrama și datele pentru Excel, cu Node) și
`python teste_sectoare.py --browser` (panoul în română și engleză, cu fișierele descărcate).

## Importul din arhive PDF

Colectarea zilnică ajunge doar la edițiile de pe prima pagină a Monitorului.
Perioadele mai vechi se adaugă din arhivele PDF, local:

```
python3 import_pdf.py CALEA/CATRE/FOLDER_CU_PDF-URI --dry-run
python3 import_pdf.py CALEA/CATRE/arhiva.zip --dry-run
```

Primește un folder, un singur PDF sau o arhivă. Aplică același filtru ca citirea de pe
site (`monitor_watch.clasifica_registru`), deci după o regulă corectată îl poți rula din nou
pe o arhivă veche ca să recuperezi actele ratate. Arhivele `.zip` le desface
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
