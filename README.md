# Acorduri de asistență externă — Monitorul Oficial al Republicii Moldova

Registru al actelor privind granturi, împrumuturi, finanțare și credite externe,
publicate în Monitorul Oficial. Se actualizează singur în fiecare zi lucrătoare.

**Dashboard:** `https://UTILIZATOR.github.io/NUME-REPOSITORY/`

## Cum funcționează

Un workflow GitHub Actions rulează în fiecare zi lucrătoare la 09:00 (ora Chișinăului),
citește edițiile recente ale Monitorului Oficial, extrage actele de finanțare externă
și face commit dacă a găsit ceva nou. Nu e nevoie ca vreun calculator să fie pornit.

## Fișiere

| Fișier | Rol |
|---|---|
| `index.html` | Dashboard-ul. Citește `date.json` la fiecare deschidere. |
| `date.json` | Datele. Actualizat automat de workflow. |
| `monitor_watch.py` | Scriptul de colectare. |
| `dashboard.html` | Variantă autonomă, cu datele incluse în fișier. |
| `.github/workflows/monitor.yml` | Programarea rulării zilnice. |

## Activare, o singură dată

1. **Settings → Pages** → Source: Deploy from a branch → Branch `main`, folder `/(root)` → Save
2. **Settings → Actions → General** → la „Workflow permissions" alege
   **Read and write permissions** → Save
3. **Actions** → „Verifică Monitorul Oficial" → **Run workflow** (ca să testezi imediat,
   fără să aștepți până mâine)

Pasul 2 este obligatoriu. Fără el, workflow-ul rulează dar nu poate face commit.

## Verificare

În fila **Actions** vezi fiecare rulare. Verde = a mers. Roșu = deschide-o și
citește ultimul pas pentru motiv.

Dacă vrei alt orar, schimbă linia `cron` din `.github/workflows/monitor.yml`.
Ora este în UTC: adună 3 pentru ora Chișinăului vara, 2 iarna.

## Sursa

Cuprinsurile Monitorului Oficial, monitorul.gov.md. Fiecare rând din dashboard
trimite la ediția în care actul a fost publicat.
