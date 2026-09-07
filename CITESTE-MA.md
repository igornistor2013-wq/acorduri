# Ce se urcă pe GitHub

Repository: `igornistor2013-wq/acorduri` · Site: `nistor.vivi.md`

## De urcat — patru fișiere

| Fișier | Ce e |
|---|---|
| `hg246.html` | **pagină nouă.** Compară anexa nr. 1 la HG 246/2010 cu baza AMP și scoate proiectele expirate într-un document Word |
| `amp-arhiva.json` | **fișier nou.** Cele 3.008 proiecte din arhiva AMP, doar câmpurile de care are nevoie pagina HG 246 |
| `index.html` | buton nou de navigare către HG 246 |
| `acorduri.html` | același buton |

Identice cu ce e deja pe GitHub, pot fi sărite: `date.json`, `donatori.html`,
`monitor_watch.py`, `import_pdf.py`, `.github/workflows/monitor.yml`.

## Pașii

1. **Dezarhivează.** GitHub nu despachetează arhive.
2. Urcă cele patru fișiere: `Add file` → `Upload files`, `Commit changes`.
3. Deschide `https://nistor.vivi.md/hg246.html`.

`amp-arhiva.json` trebuie să stea lângă `hg246.html`, în rădăcina repo-ului —
pagina îl cere prin cale relativă.

## Cum se folosește pagina nouă

Tragi anexa în format `.docx` în zona punctată. Numărul de înregistrare din
coloana a doua este chiar ID-ul proiectului în Platforma pentru gestionarea
asistenței externe, deci comparația se face după el.

Fiecare proiect e căutat în două surse: raportul live al platformei și arhiva
încorporată, care acoperă până în 2022. Când proiectul apare în amândouă,
câștigă datele live.

Proiectele a căror dată de finalizare a trecut apar într-un tabel pe ecran,
apoi le descarci în Word.

## Ce conține documentul generat

Nu e construit de la zero: se pornește de la fișierul tău, se șterg rândurile
care nu ne interesează și se adaugă o coloană. Bordurile, fonturile, titlurile
de secțiune pe toată lățimea și indicii superiori din numerotare rămân exact
cum erau. Coloana 7, „Data de finalizare", se adaugă la dreapta.

Titlurile de țară se păstrează doar dacă au sub ele măcar un proiect expirat.

## Rezultatul pe anexa trimisă

Din 1102 proiecte: 115 expirate, 193 fără dată de finalizare în platformă, 794
negăsite. Ultimele două cifre scad mult când raportul live răspunde — cifrele
de mai sus sunt obținute doar din arhivă, care se oprește în 2022.

Proiectele fără dată de finalizare nu sunt incluse în document. Absența datei
nu înseamnă că proiectul s-a încheiat, iar a le declara expirate ar fi o
afirmație pe care datele n-o susțin.

## Dacă raportul live nu răspunde

Pagina scrie asta explicit și continuă doar cu arhiva. Mesajul conține și
motivul între paranteze — de acolo se vede dacă e blocaj de rețea, CORS sau
altceva.
