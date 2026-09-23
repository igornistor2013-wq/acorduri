# Asistență externă pentru Republica Moldova

Patru pagini care arată, din surse oficiale, cine finanțează Republica Moldova
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
Oficial, extrage actele de finanțare externă și face commit dacă a găsit ceva
nou. Nu e nevoie ca vreun calculator să fie pornit.

Înainte de colectare rulează `teste.py`. Dacă testele pică, colectarea nici nu
pornește: o rulare oprită se vede imediat în fila Actions, un registru stricat
ar trece neobservat.

Scriptul mai face două lucruri care nu se văd:

**Recuperează edițiile sărite.** Prima pagină a Monitorului arată doar zece
ediții. Dacă automatizarea stă oprită mai mult, unele ies din listă înainte de
a fi citite. ID-urile fiind consecutive, orice număr lipsă e o ediție necitită
— scriptul o cere direct. După cinci încercări nereușite o consideră
inexistentă și nu o mai cere; numerotarea Monitorului are găuri reale, fiindcă
edițiile speciale și volumele suplimentare ocupă numere proprii.

**Semnalează tăcerea.** Dacă ultima colectare e mai veche de patru zile,
`acorduri.html` scrie asta cu roșu în antet. Pragul ține cont că rularea e
programată doar în zilele lucrătoare.

## Fișiere

| Fișier | Rol |
|---|---|
| `index.html` | Pagina principală: donatori și proiecte. Conține arhiva AMP încorporată |
| `acorduri.html` | Registrul acordurilor. Citește `date.json` la fiecare deschidere |
| `hg246.html` | Comparația cu anexa HG 246. Citește `amp-arhiva.json` |
| `donatori.html` | Redirecționare către `index.html`, pentru linkurile vechi |
| `date.json` | Registrul acordurilor. Actualizat automat de workflow |
| `amp-arhiva.json` | Arhiva AMP, doar câmpurile de care are nevoie `hg246.html` |
| `monitor_watch.py` | Colectarea zilnică din Monitorul Oficial |
| `import_pdf.py` | Importul din arhivele PDF ale Monitorului. Se rulează local |
| `teste.py` | Testele colectorului. Rulate de workflow înaintea colectării |
| `.github/workflows/monitor.yml` | Programarea rulării |
| `legis_acorduri.html` | Acordurile din legis.md, grupate pe acord. Datele sunt incluse în pagină |
| `legis_brut.json` | Toate actele găsite pe legis.md (baza); actualizat de `legis.yml` |
| `legis_watch.py` | Verificarea zilnică pe legis.md, cu browser (Playwright) |
| `legis_extrage.js` | Căutările rulate în pagina legis.md |
| `legis_clasifica.py` | Ce e asistență externă, categoria, partenerul (extinde `monitor_watch.py`) |
| `legis_pagina.py` | Construiește `legis_acorduri.html` din `acorduri.html` + bază |
| `teste_legis.py` | Testele verificării legis.md |
| `legis_local.bat` | Aceeași verificare, rulată de pe calculatorul tău (Windows) |
| `raport_legis.md`, `jurnal_legis.md` | Raportul ultimei rulări și istoricul zilelor cu acte noi |
| `.github/workflows/legis.yml` | Programarea verificării legis.md |
| `CNAME` | Domeniul propriu |

## Registrul din legis.md — cum se actualizează

Workflow-ul **Verifică legis.md** rulează zilnic la 07:00 UTC (10:00 la
Chișinău vara). Deschide legis.md într-un Chromium invizibil, face 18 căutări
după cuvinte-cheie în actele din anul curent (în ianuarie–martie și din anul
trecut), păstrează doar actele care nu sunt deja în `legis_brut.json`, le trece
prin clasificator și reconstruiește `legis_acorduri.html`. Face commit doar
dacă a apărut ceva nou. Ce a găsit se vede în rezumatul rulării, în Actions.

**Cloudflare.** legis.md e protejat de Cloudflare. Un browser adevărat trece
de obicei de verificarea automată, dar Cloudflare poate cere bifa „nu sunt
robot" — mai ales serverelor GitHub. Scriptul nu încearcă s-o ocolească: se
oprește cu mesajul „Blocat de Cloudflare" și rularea apare roșie. Dacă se
întâmplă zilnic, dezactivează workflow-ul (Actions → Verifică legis.md → ⋯ →
Disable workflow) și rulează local:

1. o singură dată: `pip install playwright` și `python -m playwright install chromium`;
2. dublu-click pe `legis_local.bat` în folderul repository-ului. Se deschide o
   fereastră de browser; dacă apare bifa, bifeaz-o. Profilul `.legis_profil`
   păstrează cookie-ul, deci rulările următoare trec singure;
3. pentru rulare zilnică: Task Scheduler → Creare activitate de bază → Zilnic
   → Pornire program → `legis_local.bat`.

Fișierul `.bat` face `git pull`, rulează verificarea și, dacă sunt acte noi,
`git commit` și `git push`.

Testele: `python teste_legis.py` (rapid) sau `python teste_legis.py --browser`
(include o rulare completă pe un legis.md simulat local, și cazul blocat).

## Importul din arhive PDF

Colectarea zilnică ajunge doar la edițiile de pe prima pagină a Monitorului.
Perioadele mai vechi se adaugă din arhivele PDF, local:

```
python3 import_pdf.py CALEA/CATRE/arhiva.rar --dry-run
```

Merge direct pe arhivă, fără dezarhivare. Scoți `--dry-run` când ești mulțumit
de ce vezi. Are nevoie de un extractor de text: `poppler-utils` sau `pdfplumber`.

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
