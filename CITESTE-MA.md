# Ce se urcă pe GitHub

Repository: `igornistor2013-wq/acorduri`

## Ce s-a schimbat

Paginile și-au schimbat rolurile:

| Fișier | Ce e acum | Înainte |
|---|---|---|
| `index.html` | pagina de donatori și proiecte — **pagina principală** | era registrul de acorduri |
| `acorduri.html` | registrul de acorduri | se numea `index.html` |
| `donatori.html` | doar o redirecționare către `index.html` | era pagina de donatori |

Adresa scurtă `igornistor2013-wq.github.io/acorduri/` deschide de acum
pagina de donatori.

## Fișierele din arhivă

| Fișier | Unde |
|---|---|
| `index.html` | rădăcină — 3,6 MB, e fosta pagină de donatori |
| `acorduri.html` | rădăcină — registrul, cu legăturile rescrise |
| `donatori.html` | rădăcină — redirecționare, ca linkurile vechi să nu moară |
| `date.json` | rădăcină — 194 de acte, preluat de pe GitHub, cu actul colectat pe 2 septembrie |
| `monitor_watch.py` | rădăcină |
| `import_pdf.py` | rădăcină |
| `.github/workflows/monitor.yml` | `.github/workflows/` — neschimbat, îl poți sări |

## Pașii

**1. Dezarhivează.** GitHub nu despachetează arhive; dacă urci `.zip`-ul ca
atare, rămâne un fișier inutil în repo.

**2. Urcă cele șase fișiere din rădăcină.** `Add file` → `Upload files`, le
tragi pe toate odată, `Commit changes`. Suprascrierea celor existente e normală
și așteptată — `index.html` și `donatori.html` se înlocuiesc complet.

**3. Verifică.** După un minut, deschide
`https://igornistor2013-wq.github.io/acorduri/` cu Ctrl+F5.

Ar trebui să vezi pagina de donatori, cu 7,57 mld EUR angajamente. Butonul
„Acorduri →" din antet duce la registru, cu 66 de acorduri. Din registru,
butonul „Donatori și proiecte →" te aduce înapoi, iar în orice rând deschis
linkul „Vezi proiectele și sumele …" deschide pagina de donatori filtrată pe
acel finanțator.

Vechea adresă `…/acorduri/donatori.html` redirecționează automat, deci
scurtătura ta de pe desktop continuă să meargă.

## De ce e inclus `date.json`

Nu e o versiune de-a mea: e chiar cel de pe GitHub, cu 194 de acte. L-am luat
de acolo fiindcă workflow-ul a rulat pe 2 septembrie și a colectat un act nou —
un ordin privind acordul de colaborare cu PNUD. Dacă aș fi pus copia mea, de pe
27 august, actul acela s-ar fi pierdut.

L-am verificat cu regulile curente: categoria și partenerul sunt corecte, iar
în șirul edițiilor nu există goluri.

## Dacă vrei un link și mai scurt

Un domeniu propriu se configurează din repo → `Settings` → `Pages` → caseta
`Custom domain`. Nu cere nicio modificare în fișiere: paginile se leagă între
ele prin căi relative, deci merg pe orice domeniu.
