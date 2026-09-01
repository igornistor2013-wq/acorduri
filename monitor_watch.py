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
  5. Pagina index.html citește date.json direct — nu se generează nimic

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
    # asistență tehnică — pct. 9.3 din anexa nr. 1 la HG 377/2018
    #
    # Lipsea complet din filtru. Contractele de stat de asistență tehnică fără
    # impact bugetar nu trec prin Guvern (anexa 1¹, pct. 6), dar SE PUBLICĂ:
    # autoritatea care le semnează emite un ordin cu data intrării în vigoare,
    # publicat în 10 zile împreună cu textul contractului (pct. 40 și 44). Deci
    # lasă urmă în Monitor, doar sub formă de ordin — iar tiparele de mai sus,
    # construite în jurul împrumuturilor și granturilor, nu-l prindeau.
    (ACORD + r"\s+de\s+asistenta\s+tehnica", "Asistență tehnică"),
    (CONTRACT + r"\s+de\s+asistenta\s+tehnica", "Asistență tehnică"),
    (ACORD + r"\s+de\s+cooperare\s+tehnica", "Asistență tehnică"),
    (r"memorandum[^.]{0,60}?asistenta\s+tehnica", "Asistență tehnică"),
    (r"proiect(?:ul|ului)?\s+de\s+asistenta\s+tehnica", "Asistență tehnică"),
    # Instrumentele „moi" prin care se acordă tot asistență tehnică. Nu putem
    # cere ca termenul să stea lângă cuvântul „acord": în titlurile reale, între
    # ele încap denumirile complete ale ambelor părți — „Acordului de înțelegere
    # între Ministerul Dezvoltării Economice și Digitalizării și Agenția
    # Elvețiană pentru Dezvoltare și Cooperare (SDC) privind consultanța…" are
    # 140 de caractere între cele două. Cerem ambele, oriunde în titlu.
    # Consultanța, instruirea și expertiza sunt chiar conținutul definiției
    # asistenței tehnice din pct. 9.3.
    (r"(?=.*\b(?:acord|acordul|acordului|memorandum|memorandumul|memorandumului)\b)"
     r".*\b(?:consultanta|instruire|expertiza|transfer\s+de\s+cunostinte)",
     "Asistență tehnică"),
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
    # dosare la Curtea Constituțională despre împrumuturi/credite din dreptul
    # civil: „contract de împrumut" apare acolo ca noțiune de Cod civil, nu ca
    # acord cu un partener extern
    r"decizie\s+de\s+inadmisibilitate",
    r"exceptia\s+de\s+neconstitutionalitate",
    r"codul\s+civil",
    # rapoartele Curții de Conturi despre proiecte finanțate extern sunt
    # despre execuția banilor, nu sunt acorduri — registrul urmărește acorduri
    r"raport(?:ul|ului)?\s+de\s+audit",
    r"raportul\s+auditului",
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
    (r"\bgiz\b|agentia de cooperare internationala a germaniei", "GIZ"),
    (r"\bpnud\b|programul natiunilor unite", "PNUD"),
    (r"\bunicef\b", "UNICEF"),
    (r"\bunops\b|oficiul natiunilor unite pentru servicii de proiect", "UNOPS"),
    (r"\bpam\b|programul alimentar mondial|\bwfp\b", "PAM"),
    (r"\bsdc\b|agentia elvetiana pentru dezvoltare", "Elveția"),
    (r"\bunhcr\b|inaltul comisariat.{0,30}refugiat", "UNHCR"),
    (r"\bficr\b|cruce ro[sș]ie|crucii rosii", "FICR"),
    (r"\bfida\b|fondul international pentru dezvoltare agricola", "FIDA"),
    # și la genitiv: „din partea Uniunii Europene", „a Comisiei Europene"
    # Agențiile executive ale UE (EISMEA, CINEA, HaDEA) semnează direct
    # acorduri de grant cu beneficiari din Moldova.
    (r"uniunea europeana|uniunii europene|comisia europeana|comisiei europene"
     r"|agentia executiva pentru|\beismea\b|\bcinea\b|\bhadea\b", "UE"),
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
    (r"guvernul regatului belgiei|guvernul belgiei", "Belgia"),
    (r"\bswedfund\b", "Suedia"),
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

    # Același act poate fi deja în registru sub altă cheie, dacă a venit din
    # PDF (import_pdf.py) unde nu se știa ID-ul ediției. Fără verificarea asta,
    # ar apărea de două ori în listă: o dată cu link către arhivă, o dată
    # cu link către ediție. Versiunea de pe site câștigă, fiindcă are linkul bun.
    dupa_act = {norm(a["act"]): k for k, a in db["acte"].items()}

    noi = 0
    for act in acte:
        key = act["act"] + "|" + act["editie_id"]
        veche = dupa_act.get(norm(act["act"]))
        if veche and veche != key:
            db["acte"].pop(veche, None)
            db["acte"][key] = act
            dupa_act[norm(act["act"])] = key
            continue
        if key not in db["acte"]:
            db["acte"][key] = act
            dupa_act[norm(act["act"])] = key
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

    total = len(db["acte"])
    if noi:
        print(f"\n{noi} acte noi. Total în registru: {total}.")
    else:
        print(f"\nNimic nou. Total în registru: {total}.")
    if esecuri:
        print("Ediții nedescărcate (se reiau la rularea următoare): " + ", ".join(esecuri))
    print("Pagina index.html citește date.json direct — nu e nimic de regenerat.")

    if PUBLICA and noi:
        publica()


# Pune True dacă folderul e un repository git legat la GitHub.
# La fiecare rulare cu acte noi, date.json va fi urcat automat.
PUBLICA = False


def publica():
    """Urcă date.json pe GitHub."""
    import subprocess
    def rulez(*args):
        return subprocess.run(args, cwd=HERE, capture_output=True, text=True)

    if rulez("git", "rev-parse", "--git-dir").returncode != 0:
        print("! Folderul nu e un repository git. Sar peste publicare.")
        return
    rulez("git", "add", "date.json")
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
