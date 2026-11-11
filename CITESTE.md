# Corecturi pentru igornistor2013-wq/acorduri — verificarea din 11.11.2026

Baza: commitul `617d512` („Acte noi — 10.11.2026”), care e și ultimul de pe `main` la data verificării.

## Cum le urci pe GitHub

**Varianta A — patch-ul (recomandată).** Păstrează mesajele commiturilor și se aplică peste orice commit nou al robotului.

```
cd acorduri
git checkout main && git pull
git am acorduri-verificare-2026-11.patch
git push
```

Patch-ul are două commituri (prima și a doua trecere); `git am` le aplică pe amândouă. Autorul lor va apărea „Claude”; ca să fie
al tău, înainte de `git push`: `git rebase --exec "git commit --amend --reset-author --no-edit" origin/main`.
Dacă `git am` se oprește cu conflict doar în `legis_acorduri.html` sau `date/acorduri_legare.json` (fișiere refăcute zilnic de robot),
păstrează versiunea ta: `git checkout --theirs <fișier>` (sau orice versiune), apoi `git add <fișier>` și `git am --continue`.
Workflow-ul „Legături acord ↔ proiect AMP” le reface oricum după push.

**Varianta B — fișierele.** Copiază fișierele din arhivă peste repository, păstrând căile (`date/…`), apoi
`git add -A && git commit -m "Verificare: sume după amendamente, acorduri despărțite, legături AMP" && git push`.

După push pornește `legaturi.yml` (rulează `teste_legatura.js`, reface pagina și `date/acorduri_legare.json`).
Datele deschise (`date/acorduri_legis.csv` și `.json`, scrise de `date_deschise.py`) se reîmprospătează la următoarea rulare zilnică a `monitor.yml`.

## Ce s-a corectat

Regula verificată la fiecare rând: **suma = suma după ultimul amendament ratificat; data din capul fișei = data acordului de bază;
un rând = un acord; legătura AMP confirmată numai când e sigură.**

### Sume (`date/sume_manual.json`)

| Rând | Înainte | Acum | Sursa |
|---|---|---|---|
| BERD, drumuri IV (hg479-2013) | 250 mil. EUR | **290 mil. EUR** (Acordul de modificare nr. 4, Legea 184/2025) | legis.md, Acord_184_ro.pdf |
| BERD, drumuri V (hg865-2023) | 150 mil. EUR | **300 mil. EUR** (Acordul de modificare nr. 1, Legea 98/2026) | legis.md, mo246-249 |
| UE, Contractul de consolidare a statului (HG432/2021) | 60 mil. EUR | **240 mil. EUR** (60 + 75 + 105) | Moldpres, 12.10.2023 |
| UE, HG90/2025 | 64 mil. EUR | **174 mil. EUR** | nota Guvernului la HG178/2025 |
| UE, MFA 2022 — grant | (pe rândul MFA 2017) | **75 mil. EUR** | Parlamentul European, Decizia (UE) 2023/1165 |
| UE, MFA 2022 — împrumut | (pe rândul MFA 2020) | **220 mil. EUR** | idem |
| UE, MFA 2022 — memorandum | 150 mil. EUR | **295 mil. EUR** (nu se adună în total) | addendumul, Legea 232/2023 |
| UE, MFA 2017 — împrumut (LP272/2017) | — | 60 mil. EUR | Legea 272/2017, art. 1 |
| BERD, deșeuri solide — grant TA (LP161/2025) | — | 1,6 mil. EUR | amendamentul nr. 1, legis.md |
| AID, MAC-P (LP176/2012) | — | 27,4 mil. DST (11,6 + 8,7 + 7,1) | legile de ratificare |
| AID, DRCM (LP224/2010) | — | 8,3 mil. DST (6,8 + 1,5) | legile de ratificare |
| AID, Servicii de sănătate și asistență socială (LP194/2007) | 6,6 mil. DST | **17,9 mil. DST** (11,3 + 6,6) | Banca Mondială, acordul 4320-MD |
| AID, e-Transformare (LP173/2011) | 2 mil. USD (avansul) | **12,7 mil. DST** | Legea 173/2011, art. 1 |
| AID+BIRD, Modernizarea serviciilor guvernamentale (LP25/2018) | 1,75 mil. USD (avansul) | **20 mil. USD** | Banca Mondială, P148537 |

### Rânduri despărțite (`date/contopiri_manual.json`, câte o notă la fiecare)

Acorduri diferite, cu titluri aproape identice, ajunseseră pe același rând (și suma unuia apărea la celălalt):
România 2010 și 2022 (câte 100 mil. EUR) · Polonia 2010 (15 mil. USD) și 2022 (20 mil. EUR) · memorandumurile MFA 2020 și 2022 ·
MFA 2017/2020 față de 2022 (grant, împrumut) · CET-Nord faza I (7 mil. EUR) și faza II (15 mil. EUR), plus granturile lor ·
„Livada Moldovei” (120 mil.) și „Livada Moldovei II” (150 mil.) · acordurile-cadru BDCE din 2005, 2007, 2009 și ambulanțele (2018) ·
două granturi BDCE „Locuințe publice III” (1 și 6 mil. EUR) · trei granturi ale Fondului fiduciar multidonator (2022, 2023, 2023) ·
FIDA 2004 și 2006 · AFD CMD 1016 01 G și CMD 1023 01 E · fazele proiectelor elvețiene (MENSANA I–III, bolile netransmisibile I–III,
acoperirea universală I–II, „Generație Sănătoasă”, migrația I–II) · schimburile de note cu Germania (2020, 2022, 2026) ·
memorandumurile cu România (2015, 2023), cu Țările de Jos (2010, 2013) și cu AFD (iunie și octombrie 2023) · actele din 2006 și 2012
care stăteau pe rândul proiectului electroenergetic din 2019. Rândurile care purtau titlul unui amendament au primit numele acordului.
După ambele treceri registrul are 496 de rânduri (471 înainte), 349 cu sumă (339 înainte).

### Data semnării

* `acorduri.html` → `semnatAcord`: capul fișei arată data acordului de bază, nu a unui amendament (BERD IV: 28.06.2013, nu 08.06.2016)
  și nici a unui acord de avans (Modernizarea serviciilor guvernamentale: 28.11.2017).
* `monitor_watch.py` → `signed_on`: citește și „semnate”, „încheiat”, „întocmit” (7 rânduri au primit data).

### AMP (`date/legaturi_amp.json`)

57 de legături confirmate (între ele BERD IV ↔ 8721179314481) și 9 respinse (proiect greșit sau altă fază). Legăturile sigure din
registru: 98 (41 înainte). Comparația s-a făcut cu arhiva AMP din repository; amp.gov.md nu a fost accesibil de aici.

### Alte fișiere

`date/debursari.json` (înregistrările MF pentru CET-Nord mutate pe faza II; notele BERD IV/V actualizate), `date/proiecte_manual.json`
(intrările pe fazele lor), `README.md` (secțiunea „Verificarea acordurilor după amendamente”), `teste.py`, `teste_legatura.js`,
plus `legis_acorduri.html` și `date/acorduri_legare.json` refăcute.

### A doua trecere (punctele rămase deschise)

| Rând | Înainte | Acum | Sursa |
|---|---|---|---|
| BDCE, locuințe sociale faza I (Legea 215/2007) | fără sumă; amendamentul din 2018 pe alt rând | **4,9 mil. EUR**, un singur rând cu amendamentul nr. 1 | IPN; textul Legii 87/2018 |
| BEI, infrastructura feroviară (LP10/2022) | 50 mil. EUR | **74 mil. EUR** (50 + 24, 17.12.2021) | comunicatul BEI din 2021 |
| AID, RISP (LP286/2004) | 8,3 mil. DST | **11,7 mil. DST** (8,3 + 3,4) | IEG, Banca Mondială |
| AID, Primul Proiect de Cadastru (LP240/2005) | 15,9 mil. USD; data 07.07.2005 | **13,5 mil. DST** (11,5 + 2); fără dată (vezi mai jos) | acordul 3061-MD; moldova.org |
| USAID, DOAG creștere economică (HG938/2016) | 2 rânduri, 220 mil. USD | **un rând, peste 512,4 mil. USD** (amendamentul nr. 19) | Moldpres, 18.12.2024 |
| USAID, DOAG democrație participativă (HG1062/2016) | 2 rânduri, fără sumă | **un rând, 134 632 542,51 USD** (amendamentul nr. 15) | Moldpres, 29.08.2024 |
| Elveția, MENSANA faza a III-a (HG176/2023) | 5,7 mil. EUR | **5,69 mil. CHF** | Radio Moldova, 29.03.2023 |
| Elveția, acoperire universală faza a II-a (HG802/2024) | fără sumă | **peste 3,3 mil. CHF** (limită inferioară) | P4H, 25.12.2024 |

* `semnatAcord`: la ratificarea unui amendament, o dată cu mai puțin de un an înaintea actului e a amendamentului, nu a acordului
  de bază. Cadastrul arăta 07.07.2005 (data modificării); acum rândul nu are dată, pentru că niciun titlu nu dă data acordului din
  08.06.1998 (registrul nu are o dată pusă de mână).
* AMP: confirmate cele două DOAG USAID (872114849402, 872114849400); respinsă legătura automată a fazei a II-a a acoperirii universale
  cu proiectul AMP al fazei I.

## Teste

Toate trec: `teste.py`, `teste_legis.py`, `teste_legatura.js`, `teste_debursari.js`, `teste_amp_date.js`, `teste_debursari.py`,
`teste_curs.py`, `teste_sectoare.py`. `teste_legis.py --browser` are aceleași 6 eșecuri ca pe `main` neatins (RESTART ×2, CRESTA,
rândul de context ×2, panoul de sume) — nu țin de aceste corecturi.

## Rămase deschise

* BERD IV, termenele: începutul 25.07.2014 coincide cu „Actual Start Date” din AMP (8721179314481); finalul 31.12.2028 vine doar
  din anexa MF (nepublicată) — AMP are încă finalizarea propusă inițial, 05.09.2021, iar BERD nu publică termenul.
* BDCE, Legea 4/2009: probabil împrumutul pentru Spitalul Clinic Republican (acordul AID 4320-MD din 2007 vorbește de un împrumut
  BDCE de cel puțin 5,8 mil.; presa, de 8 mil. EUR), dar textul legii nu s-a putut citi pe legis.md — fără sumă.
* Amendamentele UE din 2025 („UE pentru Reforme”, „UE pentru redresare și reziliență”, „Sprijin pentru integrarea în UE”,
  Facilitatea de cooperare tehnică): hotărârile Guvernului nu spun nicio sumă, iar textele amendamentelor nu sunt publice;
  addendumurile UE mai vechi, la fel.
* Acordurile USAID din 2010–2012 (creștere economică, ROLISP): fără sumă în registru.
* Bugetele fazelor elvețiene MENSANA I–II, bolile netransmisibile I–II, „Generație Sănătoasă”, migrația I–II: nu sunt publice.
