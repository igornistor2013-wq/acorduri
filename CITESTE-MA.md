# Ce se urcă pe GitHub

Repository: `igornistor2013-wq/acorduri` · Site: `nistor.vivi.md`

## Ce s-a schimbat

Toate cele zece arhive ale Monitorului au fost **reprocesate de la zero** cu
filtrul curent. Importurile anterioare rulaseră cu versiuni mai vechi, care
nu cunoșteau asistența tehnică și o parte din finanțatori — actele care se
potriveau doar cu regulile noi nu fuseseră extrase deloc.

Registrul are acum **332 de acte în 96 de acorduri**, din 12.01.2024 până în
09.09.2026.

### Actele recuperate

| Data | Partener | Ce e |
|---|---|---|
| 19.08.2025 | PAM | Acord de Asistență Tehnică cu Ministerul Muncii |
| 04.09.2025 | BEI | Acord de cooperare privind servicii de consultanță |
| 20.11.2025 | JICA | Memorandum de înțelegere cu ODA |
| 29.05.2026 | Elveția | Acord de înțelegere cu Ministerul Dezvoltării Economice |

Categoria „Asistență tehnică" a urcat de la 3 la 7 acte. Au intrat în registru
doi finanțatori noi: PAM și Elveția.

## De urcat — patru fișiere

| Fișier | De ce |
|---|---|
| `date.json` | 332 de acte, cu tot ce s-a recuperat |
| `monitor_watch.py` | renunță la edițiile inaccesibile după cinci încercări; golurile se salvează înainte de scrierea fișierului |
| `acorduri.html` | „suport bugetar" e filtru funcțional, cu culoare proprie |
| `import_pdf.py` | câmpul `suport` pus și pe actele venite din PDF |

Identice cu ce e pe GitHub, pot fi sărite: `index.html`, `hg246.html`,
`amp-arhiva.json`, `donatori.html`, `.github/workflows/monitor.yml`.

## Pașii

1. **Dezarhivează.** GitHub nu despachetează arhive.
2. Urcă cele patru fișiere: `Add file` → `Upload files`, `Commit changes`.
3. Verifică pe `https://nistor.vivi.md/acorduri.html` cu Ctrl+F5.

Ar trebui să vezi 96 de acorduri, iar filtrul pe tip să arate Împrumut 46,
Grant 44, Asistență tehnică 6.

## Despre `date.json`

Conține și cele două acte colectate de automatizare pe 9 septembrie — legea și
decretul privind Scrisoarea de modificare la un acord de împrumut. Le-am
preluat de pe GitHub și le-am unit cu reprocesarea, ca să nu se piardă la
suprascriere.

## Verificarea încrucișată

Am recitit fiecare ediție din toate cele zece arhive — peste 11.000 de intrări
de cuprins — și am căutat ediții cu formulări de finanțare din care n-a ieșit
niciun act. Toate semnalările s-au dovedit mențiuni în corpul altor acte,
volume de continuare fără cuprins sau anexe.

Un caz merită reținut: două ediții din februarie 2025, nr. 53-57 și nr. 70-88,
au codificarea textului grav stricată și cuprinsul nu poate fi citit. Am
verificat direct dacă ascund acte de finanțare — zero. Dar dacă o astfel de
ediție ar conține un acord, l-am rata. E singura slăbiciune structurală rămasă
la import.

## Ce a rămas nerezolvat

Linkurile duc în majoritate la căutarea generală a Monitorului, nu la ediția
exactă, fiindcă actele vin din PDF-uri. Se repară rulând local
`python3 monitor_watch.py --backfill 3000 3311` și urcând `date.json`.

Data semnării se extrage doar pentru un sfert din acte.

Lipsește 2023 — de acolo vin cele 38 de etape marcate cu semnul întrebării.

Ediția 3333 rămâne necitită. Scriptul o mai cere de câteva ori, apoi renunță
singur și avertismentul dispare.
