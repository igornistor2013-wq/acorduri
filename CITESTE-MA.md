# De urcat pe GitHub — patru fișiere

Repository: `igornistor2013-wq/acorduri` · Site: `nistor.vivi.md`

| Fișier | Unde | Ce aduce |
|---|---|---|
| `teste.py` | rădăcină | **fișier nou.** Set de teste rulat de automatizare înainte de colectare |
| `index.html` | rădăcină | butoane reordonate și colorate; coloanele de sume din raportul live se recunosc după înțeles; datele live nu mai pot șterge sumele din arhivă |
| `acorduri.html` | rădăcină | avertisment când colectarea a tăcut prea mult |
| `monitor.yml` | `.github/workflows/` | rulează testele înaintea colectării |

## Ce NU se urcă

**`date.json` — nu-l atinge.** Versiunea de pe GitHub e mai nouă decât a mea:
aceleași 332 de acte, dar cu edițiile 3338–3340 deja parcurse și cu ediția 3333
marcată ca inaccesibilă după cinci încercări. A mea ar da înapoi o săptămână de
colectare.

Nici acestea nu s-au schimbat: `hg246.html`, `donatori.html`, `amp-arhiva.json`,
`monitor_watch.py`, `import_pdf.py`.

## Pașii

1. **Dezarhivează.** GitHub nu despachetează arhive.
2. Urcă cele trei fișiere din rădăcină: `Add file` → `Upload files`,
   `Commit changes`.
3. Intră în folderul `.github/workflows` din repository și urcă acolo
   `monitor.yml`.
4. Deschide fila `Actions` → „Verifică Monitorul Oficial" → `Run workflow`.

## Ce ar trebui să vezi

În jurnalul rulării apare un pas nou, **„Verifică scriptul"**, înaintea
colectării. Trebuie să scrie „Toate testele au trecut (9 grupuri)". Dacă pică,
colectarea nici nu pornește — mai bine o rulare oprită, care se vede în
Actions, decât un registru stricat, care trece neobservat.

Pe `acorduri.html`, lângă „Ultima verificare" apare de acum vechimea ei. Dacă
trec mai mult de patru zile fără colectare, textul devine roșu.

## De ce există `teste.py`

Pe 7 septembrie automatizarea a picat cu `NameError: name 'titlu' is not
defined` — o literă greșită într-un nume de variabilă. Python o semnalează abia
când linia e atinsă, iar verificările de atunci apelau direct funcțiile de
clasificare, fără să treacă prin `parse_edition`. Linia stricată era pe o cale
pe care n-o atingea nimic. A stat picată zile întregi.

Testele au fost validate reintroducând exact acea greșeală: pică imediat, la
două grupuri.
