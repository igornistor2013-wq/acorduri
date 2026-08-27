#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
monitor_watch.py — urmărește Monitorul Oficial al Republicii Moldova
și colectează actele privind asistența externă (grant, împrumut,
finanțare, credit).

Rulare:
    python3 monitor_watch.py
    python3 monitor_watch.py --backfill 3300 3323   # recuperează ediții vechi

Ce face:
  1. Citește lista edițiilor recente de pe monitorul.gov.md
  2. Recitește TOATE edițiile din listă la fiecare rulare (nu doar cele noi)
  3. Extrage actele care conțin termeni de finanțare externă
  4. Salvează în date.json (cumulativ, fără duplicate)
  5. Regenerează dashboard.html

Fișierele apar lângă script.
"""

import json
import os
import re
import sys
import time
from datetime import datetime

try:
    import requests
    from bs4 import BeautifulSoup
except ImportError:
    sys.exit("Lipsesc biblioteci. Rulează:  pip install requests beautifulsoup4")

BASE = "https://monitorul.gov.md"
HOME = BASE + "/ro"
HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "date.json")
OUT = os.path.join(HERE, "dashboard.html")

UA = {"User-Agent": "Mozilla/5.0 (compatible; monitor-watch/1.0)"}

# ---------------------------------------------------------------- clasificare

# Termeni care indică un act de finanțare externă.
#
# Tiparele se aplică pe text NORMALIZAT (litere mici, fără diacritice), de aceea
# sunt scrise aici direct fără diacritice — vezi norm() mai jos.
#
# ACORD acoperă și pluralul. Vechea versiune accepta doar „acord / acordul /
# acordului" și rata acte reale: „Amendament la ACORDURILE de finanțare dintre
# Republica Moldova și AID" (MO nr. 390-393 din 25.08.2026, poz. 421) n-a intrat
# niciodată în registru din cauza unei singure litere.
ACORD = r"acord(?:ul|ului|uri|urile|urilor)?"
CONTRACT = r"contract(?:ul|ului|e|ele|elor)?"

INCLUDE = [
    # granturi
    (ACORD + r"\s+de\s+grant", "Grant"),
    (r"grant(?:ul|ului|uri|urile|urilor)?\s+investi", "Grant"),
    (r"din\s+contul\s+grantului", "Grant"),
    (r"asistent[aă]\s+financiara\s+nerambursabila", "Grant"),
    (ACORD + r"\s+de\s+colaborare\s+dintre", "Grant"),
    # împrumuturi
    (ACORD + r"\s+de\s+imprumut", "Împrumut"),
    (CONTRACT + r"\s+de\s+imprumut", "Împrumut"),
    # finanțare
    (ACORD + r"\s+de\s+finan", "Finanțare"),
    (r"conventi(?:a|e|ei|i|ile|ilor)?\s+de\s+finan", "Finanțare"),
    (r"cooperare\s+si\s+finantare", "Finanțare"),
    (ACORD + r"\s+de\s+cooperare\s+financiara", "Finanțare"),
    (ACORD + r"\s+de\s+(?:asistenta|sprijin)\s+financiar", "Finanțare"),
    (r"asistenta\s+(?:financiara\s+)?(?:externa|macrofinanciara)", "Finanțare"),
    (r"memorandum[^.]{0,80}?(?:finantare|imprumut|macrofinanciar)", "Finanțare"),
    (r"suport\s+bugetar", "Finanțare"),
    # contract de finanțare (mai specific decât „finanțare")
    (CONTRACT + r"\s+de\s+finan", "Contract de finanțare"),
    # credite
    (r"facilitate\s+de\s+credit", "Credit"),
    (r"linie\s+de\s+credit", "Credit"),
    (ACORD + r"\s+de\s+credit", "Credit"),
    (CONTRACT + r"\s+de\s+credit", "Credit"),
]

# Termeni care înseamnă că actul NU e despre finanțare externă,
# chiar dacă a trecut de filtrul de mai sus.
EXCLUDE = [
    r"imprumut\s+interbibliotecar",
    r"asociati(?:i|ile|ilor)\s+de\s+economii\s+si\s+imprumut",
    r"risc(?:ul|ului)?\s+de\s+credit",
    r"istoriil?e?\s+de\s+credit",
    r"birou(?:l|ri|rile)\s+istoriilor\s+de\s+credit",
    r"credite?\s+fara\s+dobanda\s+.*(?:electoral|concurent)",
    r"cooperativ[ea]\s+de\s+intrajutorare",
    # sprijin financiar intern pentru producători — nu e asistență externă
    r"sprijin(?:ul|ului)?\s+financiar\s+(?:pentru\s+)?(?:producator|agricultor|fermier)",
    # finanțarea partidelor / campaniilor
    r"finantarea\s+(?:partidelor|campaniei|concurentilor)",
]

# Partenerii externi recunoscuți, pentru coloana „Partener".
# Tiparele se aplică tot pe text normalizat (fără diacritice), ca să prindem și
# „Asociaţia" cu ş-cedilă, și „Asociația" cu ș-virgulă — în Monitor apar ambele.
PARTNERS = [
    (r"\bbird\b|banca internationala pentru reconstructie", "BIRD"),
    (r"\bberd\b|banca europeana pentru reconstructie", "BERD"),
    (r"\bbei\b|banca europeana de investitii", "BEI"),
    (r"\baid\b|asociatia internationala pentru dezvoltare", "AID"),
    (r"banca mondiala|grupul bancii mondiale", "Banca Mondială"),
    (r"\bbdce\b|banca de dezvoltare a consiliului europei", "BDCE"),
    (r"\bafd\b|agentia franceza", "AFD"),
    (r"\bkfw\b", "KfW"),
    (r"\bjica\b|agentia japoneza", "JICA"),
    (r"\bgiz\b", "GIZ"),
    (r"\bpnud\b|programul natiunilor unite", "PNUD"),
    (r"\bunicef\b", "UNICEF"),
    (r"\bunhcr\b|inaltul comisariat.{0,30}refugiat", "UNHCR"),
    (r"\bficr\b|cruce ro[sș]ie|crucii rosii", "FICR"),
    (r"\bfida\b|fondul international pentru dezvoltare agricola", "FIDA"),
    # și la genitiv: „din partea Uniunii Europene", „a Comisiei Europene"
    (r"uniunea europeana|uniunii europene|comisia europeana|comisiei europene", "UE"),
    (r"consiliul(?:ui)? europei", "Consiliul Europei"),
    (r"\bfmi\b|fondul(?:ui)?\s+monetar", "FMI"),
    (r"\busaid\b|statele unite ale americii|guvernul sua", "SUA"),
    (r"guvernul japoniei", "Japonia"),
    (r"guvernul germaniei|republicii federale germania", "Germania"),
    (r"guvernul romaniei", "România"),
    (r"guvernul elvetiei|confederatiei elvetiene", "Elveția"),
    (r"\bsida\b|guvernul suediei", "Suedia"),
    (r"guvernul poloniei", "Polonia"),
    (r"guvernul turciei|\btika\b", "Turcia"),
]

MONTHS = {
    "ianuarie": 1, "februarie": 2, "martie": 3, "aprilie": 4,
    "mai": 5, "iunie": 6, "iulie": 7, "august": 8,
    "septembrie": 9, "octombrie": 10, "noiembrie": 11, "decembrie": 12,
}

# Linie de cuprins: "446. Hotărâre cu privire la ... (nr. 442, 12 august 2026)"
ITEM_RE = re.compile(
    r"^\s*(\d+[a-z]?)\.\s+(.{20,}?)\s*\(\s*(nr\.?\s*[^)]{1,80}?)\s*\)\s*$",
    re.IGNORECASE,
)


def norm(text):
    """Text cu diacritice reduse, pentru potrivire robustă."""
    t = text.lower()
    for a, b in (("ă", "a"), ("â", "a"), ("î", "i"), ("ș", "s"),
                 ("ş", "s"), ("ț", "t"), ("ţ", "t")):
        t = t.replace(a, b)
    return t


def classify(title):
    """Returnează categoria actului, sau None dacă nu e relevant."""
    n = norm(title)
    for pat in EXCLUDE:
        if re.search(norm(pat), n):
            return None
    # Cea mai specifică potrivire câștigă: contract de finanțare > finanțare.
    hits = []
    for pat, cat in INCLUDE:
        if re.search(norm(pat), n):
            hits.append(cat)
    if not hits:
        return None
    for pref in ("Contract de finanțare", "Credit", "Împrumut", "Grant", "Finanțare"):
        if pref in hits:
            return pref
    return hits[0]


# Când o instituție specifică e recunoscută, denumirea mai generală care apare
# în propriul ei nume devine zgomot: „Banca de Dezvoltare a Consiliului Europei"
# e BDCE, nu „BDCE / Consiliul Europei".
REDUNDANT = {"BDCE": "Consiliul Europei"}


def partner(title):
    n = norm(title)
    found = []
    for pat, name in PARTNERS:
        if re.search(norm(pat), n):
            if name not in found:
                found.append(name)
    for specific, generic in REDUNDANT.items():
        if specific in found and generic in found:
            found.remove(generic)
    return " / ".join(found)


def signed_on(title):
    """Extrage data semnării dacă apare în denumire."""
    m = re.search(
        r"semnat[ăa]?\s+(?:la\s+[^,]{0,40}?\s+)?la\s+(\d{1,2})\s+([a-zăâîșț]+)\s+(\d{4})",
        title, re.IGNORECASE)
    if not m:
        return ""
    day, mon, year = m.group(1), norm(m.group(2)), m.group(3)
    for name, num in MONTHS.items():
        if norm(name) == mon:
            return f"{int(day):02d}.{num:02d}.{year}"
    return ""


# ------------------------------------------------------------------ colectare

def get(url, tries=3):
    for i in range(tries):
        try:
            r = requests.get(url, headers=UA, timeout=30)
            r.raise_for_status()
            r.encoding = "utf-8"
            return r.text
        except Exception as e:
            if i == tries - 1:
                print(f"   ! nu am putut deschide {url}: {e}")
                return None
            time.sleep(2 * (i + 1))


def recent_editions(html):
    """Extrage (id, eticheta) pentru edițiile listate pe pagină."""
    soup = BeautifulSoup(html, "html.parser")
    out = []
    seen = set()
    for a in soup.find_all("a", href=True):
        m = re.search(r"/ro/monitor/(\d+)$", a["href"])
        if not m:
            continue
        eid = m.group(1)
        if eid in seen:
            continue
        seen.add(eid)
        out.append((eid, a.get_text(strip=True)))
    return out


def parse_edition(eid, label):
    """Returnează (a_reușit_descărcarea, listă_de_acte).

    Distincția contează. Versiunea veche întorcea listă goală și când ediția
    n-avea acte de finanțare, și când pagina nu s-a putut descărca — iar main()
    o marca oricum drept „văzută". O eroare de rețea de o secundă însemna că
    ediția aceea nu mai era citită NICIODATĂ.
    """
    html = get(f"{BASE}/ro/monitor/{eid}")
    if not html:
        return False, []
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "nav", "footer"]):
        tag.decompose()
    text = soup.get_text("\n")

    # Data ediției din eticheta "Monitorul Oficial Nr. 375-378 din 13.08.2026".
    # La backfill nu avem etichetă, așa că o luăm din pagină.
    source = label or ""
    m = re.search(r"din\s+(\d{2}\.\d{2}\.\d{4})", source)
    if not m:
        m = re.search(r"Nr\.\s*[\d\-]+\s*\n?\s*din\s+(\d{2}\.\d{2}\.\d{4})", text)
    ed_date = m.group(1) if m else ""
    m = re.search(r"Nr\.\s*([\d\-]+)", source) or re.search(
        r"Monitorul Oficial Nr\.\s*([\d\-]+)", text)
    ed_nr = m.group(1) if m else eid

    found = []
    for raw in text.split("\n"):
        line = " ".join(raw.split())
        if len(line) < 40:
            continue
        m = ITEM_RE.match(line)
        if not m:
            continue
        title, act = m.group(2).strip(), m.group(3).strip()
        cat = classify(title)
        if not cat:
            continue
        found.append({
            "act": re.sub(r"\s+", " ", act),
            "titlu": title,
            "categorie": cat,
            "partener": partner(title),
            "semnat": signed_on(title),
            "editie": ed_nr,
            "data_editie": ed_date,
            "editie_id": eid,
            "url": f"{BASE}/ro/monitor/{eid}",
        })
    return True, found


def load():
    if not os.path.exists(DATA):
        return {"acte": {}, "editii_vazute": [], "ultima_rulare": None}
    with open(DATA, encoding="utf-8") as f:
        return json.load(f)


def save(db):
    with open(DATA, "w", encoding="utf-8") as f:
        json.dump(db, f, ensure_ascii=False, indent=2)


# ----------------------------------------------------------------- dashboard

def sort_key(a):
    d = a.get("data_editie") or ""
    m = re.match(r"(\d{2})\.(\d{2})\.(\d{4})", d)
    return (m.group(3) + m.group(2) + m.group(1)) if m else "0"


def build_html(db):
    acte = sorted(db["acte"].values(), key=sort_key, reverse=True)
    cats = {}
    for a in acte:
        cats[a["categorie"]] = cats.get(a["categorie"], 0) + 1
    semnate = [a for a in acte if a.get("semnat")]

    def esc(s):
        return (str(s).replace("&", "&amp;").replace("<", "&lt;")
                .replace(">", "&gt;").replace('"', "&quot;"))

    rows = []
    for a in acte:
        rows.append(
            '<tr data-cat="{c}">'
            '<td class="rail"></td>'
            '<td class="act">{act}</td>'
            '<td class="cat">{c}</td>'
            '<td class="part">{p}</td>'
            '<td class="titlu">{t}</td>'
            '<td class="sig">{s}</td>'
            '<td class="ed"><a href="{u}" target="_blank" rel="noopener">{e}</a>'
            '<span>{d}</span></td>'
            "</tr>".format(
                c=esc(a["categorie"]), act=esc(a["act"]), p=esc(a["partener"] or "—"),
                t=esc(a["titlu"]), s=esc(a["semnat"] or "—"),
                u=esc(a["url"]), e=esc(a["editie"]), d=esc(a["data_editie"]),
            )
        )

    filters = ['<button data-f="all" aria-pressed="true">Toate ({})</button>'.format(len(acte))]
    for c in sorted(cats):
        filters.append('<button data-f="{0}" aria-pressed="false">{0} ({1})</button>'.format(esc(c), cats[c]))

    return TEMPLATE.format(
        total=len(acte),
        semnate=len(semnate),
        editii=len(db["editii_vazute"]),
        rulare=esc(db.get("ultima_rulare") or "—"),
        filtre="\n    ".join(filters),
        randuri="\n".join(rows) if rows else
        '<tr><td colspan="7" class="gol">Niciun act colectat încă. Rulează scriptul.</td></tr>',
    )


TEMPLATE = """<!DOCTYPE html>
<html lang="ro">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Asistență externă — acte publicate în Monitorul Oficial</title>
<style>
  :root{{
    --ink:#111C2E;--soft:#46586F;--rule:#CBD4DE;--paper:#EDF1F5;--card:#fff;
    --oxide:#A2382A;--brass:#8A6A2F;--sage:#3F6B54;--azure:#2F5D7C;--plum:#6B4A7A;
  }}
  *{{box-sizing:border-box}}
  body{{margin:0;background:var(--paper);color:var(--ink);padding:30px 18px 60px;
    font:15px/1.55 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif}}
  .wrap{{max-width:1240px;margin:0 auto}}
  header{{border-top:3px solid var(--ink);border-bottom:1px solid var(--rule);
    padding:20px 0 16px;margin-bottom:20px}}
  .eyebrow{{font:600 11px/1 ui-monospace,Menlo,Consolas,monospace;letter-spacing:.18em;
    text-transform:uppercase;color:var(--oxide);margin-bottom:11px}}
  h1{{font:400 28px/1.2 "Iowan Old Style","Palatino Linotype",Palatino,Georgia,serif;margin:0 0 8px}}
  .lede{{max-width:68ch;color:var(--soft);margin:0;font-size:14px}}
  .stats{{display:flex;flex-wrap:wrap;gap:10px 30px;margin:16px 0 18px;
    font:12px/1.4 ui-monospace,Menlo,Consolas,monospace;color:var(--soft)}}
  .stats b{{color:var(--ink);font-size:15px}}
  .filters{{display:flex;flex-wrap:wrap;gap:8px;margin:0 0 16px}}
  .filters button{{font:600 12px/1 ui-monospace,Menlo,Consolas,monospace;padding:9px 13px;
    border:1px solid var(--rule);background:var(--card);color:var(--soft);
    border-radius:2px;cursor:pointer}}
  .filters button:hover{{border-color:var(--soft);color:var(--ink)}}
  .filters button[aria-pressed="true"]{{background:var(--ink);border-color:var(--ink);color:#fff}}
  .filters button:focus-visible{{outline:2px solid var(--oxide);outline-offset:2px}}
  .scroll{{overflow-x:auto;background:var(--card);border:1px solid var(--rule);border-radius:2px}}
  table{{border-collapse:collapse;width:100%;min-width:1000px}}
  th{{font:600 11px/1.3 ui-monospace,Menlo,Consolas,monospace;letter-spacing:.1em;
    text-transform:uppercase;color:var(--soft);text-align:left;padding:13px 13px 9px;
    border-bottom:1px solid var(--ink);white-space:nowrap}}
  td{{padding:12px 13px;border-bottom:1px solid var(--rule);vertical-align:top;font-size:13.5px}}
  tbody tr:last-child td{{border-bottom:none}}
  tbody tr:hover{{background:#F7F9FB}}
  td.rail{{width:5px;padding:0;background:var(--soft)}}
  tr[data-cat="Grant"] td.rail{{background:var(--sage)}}
  tr[data-cat="Împrumut"] td.rail{{background:var(--oxide)}}
  tr[data-cat="Finanțare"] td.rail{{background:var(--brass)}}
  tr[data-cat="Contract de finanțare"] td.rail{{background:var(--azure)}}
  tr[data-cat="Credit"] td.rail{{background:var(--plum)}}
  .act,.cat,.part,.sig{{font:600 12px/1.4 ui-monospace,Menlo,Consolas,monospace;white-space:nowrap}}
  .cat{{color:var(--soft);font-weight:400}}
  .sig{{color:var(--oxide)}}
  .titlu{{max-width:58ch;line-height:1.45}}
  .ed{{font:12px/1.4 ui-monospace,Menlo,Consolas,monospace;white-space:nowrap}}
  .ed a{{color:var(--ink);text-decoration:none;border-bottom:1px solid var(--rule)}}
  .ed a:hover{{color:var(--oxide);border-color:var(--oxide)}}
  .ed span{{display:block;color:var(--soft);margin-top:3px}}
  .gol{{padding:34px;text-align:center;color:var(--soft)}}
  footer{{margin-top:26px;border-top:1px solid var(--rule);padding-top:16px;
    font-size:13px;color:var(--soft);max-width:74ch}}
  @media (max-width:640px){{body{{padding:20px 12px 44px}}h1{{font-size:23px}}}}
</style>
</head>
<body>
<div class="wrap">
<header>
  <div class="eyebrow">Monitorul Oficial al Republicii Moldova</div>
  <h1>Acorduri de asistență externă</h1>
  <p class="lede">Acte privind granturi, împrumuturi, finanțare și credite externe, colectate
  automat din cuprinsurile Monitorului Oficial. Fiecare rând trimite la ediția în care a fost publicat.</p>
</header>

<div class="stats">
  <div><b>{total}</b> acte</div>
  <div><b>{semnate}</b> cu dată de semnare</div>
  <div><b>{editii}</b> ediții parcurse</div>
  <div>ultima verificare: <b>{rulare}</b></div>
</div>

<div class="filters" role="group" aria-label="Filtrare după categorie">
    {filtre}
</div>

<div class="scroll">
<table>
  <thead><tr>
    <th></th><th>Act</th><th>Categorie</th><th>Partener</th>
    <th>Denumire</th><th>Semnat</th><th>Ediția</th>
  </tr></thead>
  <tbody id="rows">
{randuri}
  </tbody>
</table>
</div>

<footer>
  Coloana „Semnat" se completează doar când data apare explicit în denumirea actului.
  Un singur acord poate genera mai multe acte — inițierea negocierilor, aprobarea semnării,
  proiectul de lege, ratificarea și promulgarea.
</footer>
</div>

<script>
(function(){{
  var btns=document.querySelectorAll('.filters button');
  var rows=document.querySelectorAll('#rows tr');
  btns.forEach(function(b){{
    b.addEventListener('click',function(){{
      var f=b.dataset.f;
      btns.forEach(function(o){{o.setAttribute('aria-pressed',String(o===b));}});
      rows.forEach(function(r){{
        r.hidden=!(f==='all'||r.dataset.cat===f);
      }});
    }});
  }});
}})();
</script>
</body>
</html>
"""


# ----------------------------------------------------------------------- main

def culege(db, eid, label):
    """Citește o ediție și adaugă/actualizează actele în registru.

    Returnează (a_reușit, acte_noi). Actele deja existente se REÎMPROSPĂTEAZĂ:
    dacă tiparele de clasificare se îmbunătățesc, categoria și partenerul se
    corectează singure la rulările următoare, fără să ștergem nimic.
    """
    ok, acte = parse_edition(eid, label)
    if not ok:
        return False, 0
    noi = 0
    for act in acte:
        key = act["act"] + "|" + act["editie_id"]
        if key not in db["acte"]:
            db["acte"][key] = act
            noi += 1
            print(f"     + {act['categorie']}: {act['titlu'][:78]}…")
        else:
            db["acte"][key].update(act)
    return True, noi


def main():
    db = load()

    # Mod recuperare: python3 monitor_watch.py --backfill 3300 3323
    if "--backfill" in sys.argv:
        i = sys.argv.index("--backfill")
        try:
            de_la, pana_la = int(sys.argv[i + 1]), int(sys.argv[i + 2])
        except (IndexError, ValueError):
            sys.exit("Folosire: --backfill PRIMUL_ID ULTIMUL_ID  (ex. --backfill 3300 3323)")
        print(f"Recuperez edițiile {de_la}–{pana_la}…")
        noi = 0
        for num in range(de_la, pana_la + 1):
            eid = str(num)
            print(f" → ediția {eid}")
            ok, n = culege(db, eid, "")
            noi += n
            if ok and eid not in db["editii_vazute"]:
                db["editii_vazute"].append(eid)
            time.sleep(1)
        db["ultima_rulare"] = datetime.now().strftime("%d.%m.%Y %H:%M")
        save(db)
        with open(OUT, "w", encoding="utf-8") as f:
            f.write(build_html(db))
        print(f"\n{noi} acte noi. Total în registru: {len(db['acte'])}.")
        return

    print("Verific Monitorul Oficial…")

    home = get(HOME)
    if not home:
        sys.exit("Nu am putut deschide monitorul.gov.md. Verifică conexiunea.")

    editions = recent_editions(home)
    if not editions:
        sys.exit("Nu am găsit nicio ediție pe pagina principală.")

    # Recitim TOATE edițiile afișate pe prima pagină, nu doar cele nemarcate.
    # Sunt zece pagini, cu o pauză de o secundă între ele — sub un minut. În
    # schimb, orice îmbunătățire a filtrului recuperează retroactiv actele
    # ratate, în loc să le lase pierdute pentru totdeauna.
    noi = 0
    esecuri = []
    for eid, label in editions:
        print(f" → ediția {label or eid}")
        ok, n = culege(db, eid, label)
        noi += n
        if ok:
            if eid not in db["editii_vazute"]:
                db["editii_vazute"].append(eid)
        else:
            # NU o marcăm ca văzută — o reluăm mâine.
            esecuri.append(label or eid)
        time.sleep(1)

    db["editii_vazute"] = sorted(set(db["editii_vazute"]), key=lambda x: int(x) if x.isdigit() else 0)
    db["ultima_rulare"] = datetime.now().strftime("%d.%m.%Y %H:%M")
    save(db)

    with open(OUT, "w", encoding="utf-8") as f:
        f.write(build_html(db))

    total = len(db["acte"])
    if noi:
        print(f"\n{noi} acte noi. Total în registru: {total}.")
    else:
        print(f"\nNimic nou. Total în registru: {total}.")
    if esecuri:
        print("Ediții nedescărcate (se reiau la rularea următoare): " + ", ".join(esecuri))
    print(f"Dashboard: {OUT}")

    if PUBLICA and noi:
        publica()


# Pune True dacă folderul e un repository git legat la GitHub.
# La fiecare rulare cu acte noi, date.json va fi urcat automat.
PUBLICA = False


def publica():
    """Urcă date.json și dashboard.html pe GitHub."""
    import subprocess
    def rulez(*args):
        return subprocess.run(args, cwd=HERE, capture_output=True, text=True)

    if rulez("git", "rev-parse", "--git-dir").returncode != 0:
        print("! Folderul nu e un repository git. Sar peste publicare.")
        return
    rulez("git", "add", "date.json", "dashboard.html")
    msg = "date " + datetime.now().strftime("%d.%m.%Y")
    c = rulez("git", "commit", "-m", msg)
    if c.returncode != 0 and "nothing to commit" not in (c.stdout + c.stderr):
        print("! commit eșuat:", (c.stderr or c.stdout).strip()[:200])
        return
    p = rulez("git", "push")
    if p.returncode != 0:
        print("! push eșuat:", (p.stderr or p.stdout).strip()[:200])
    else:
        print("Publicat pe GitHub.")


if __name__ == "__main__":
    main()
