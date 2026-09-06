# Ce se urcă pe GitHub

Repository: `igornistor2013-wq/acorduri` · Site: `nistor.vivi.md`

## De urcat — trei fișiere

| Fișier | Ce s-a schimbat |
|---|---|
| `date.json` | 326 de acte, 12.01.2024 – 04.09.2026. Suportul bugetar a devenit un câmp separat, nu o categorie |
| `acorduri.html` | eticheta „suport bugetar" pe rânduri și în export; mesaj de eroare care recunoaște deschiderea prin dublu-click |
| `monitor_watch.py` | suportul bugetar detectat ca marcaj; categoria rămâne instrumentul |

Identice cu ce e deja pe GitHub, pot fi sărite: `index.html`, `donatori.html`,
`import_pdf.py`, `.github/workflows/monitor.yml`.

## Pașii

1. **Dezarhivează.** GitHub nu despachetează arhive.
2. Urcă cele trei fișiere: `Add file` → `Upload files`, `Commit changes`.
3. Verifică pe `https://nistor.vivi.md/acorduri.html` cu Ctrl+F5.

## Ce ar trebui să vezi

92 de acorduri. Filtrul pe tip are trei valori: Împrumut 46, Grant 45,
Asistență tehnică 1. Două rânduri poartă în plus eticheta mov
`suport bugetar` — unul e împrumut, celălalt grant.

## De ce suportul bugetar nu mai e categorie

Pct. 9.20¹ din anexa nr. 1 la HG 377/2018 îl definește ca asistență
transferată direct într-un buget component al bugetului public național. Asta
descrie unde ajung banii, nu dacă se întorc — deci poate fi grant sau
împrumut.

Ca și categorie separată, ascundea tocmai ce contează. Facilitatea de reformă
și creștere e suport bugetar dat ca împrumut: aveam de ales între a arăta că
statul are de rambursat și a arăta că banii intră direct în buget. Ca marcaj,
se arată amândouă.

Contractul de performanță pentru reforma sectorială cu Comisia Europeană e
grant cu marcaj; Facilitatea de reformă și creștere e împrumut cu marcaj.

## Despre `date.json`

E construit pornind de la fișierul de pe GitHub, ca să păstreze actul colectat
de automatizare pe 4 septembrie. Am recalculat categoriile, partenerii și
marcajul cu regulile curente. Niciun act fără partener, niciun gol în șirul
edițiilor.

## Ce a rămas

Semnele de întrebare din coloana etapelor sunt acordurile începute înainte de
12 ianuarie 2024. Se închid cu arhivele din 2023.

Linkurile duc în majoritate la căutarea generală a Monitorului, nu la ediția
exactă, fiindcă actele au venit din PDF-uri. Se repară rulând local
`python3 monitor_watch.py --backfill 3000 3311` și urcând `date.json`.
