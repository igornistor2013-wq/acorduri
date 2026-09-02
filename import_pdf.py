#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
import_pdf.py — citește PDF-urile Monitorului Oficial salvate local și adaugă
actele de asistență externă în date.json.

Se folosește DOAR pentru edițiile pe care nu le poți lua de pe site. Pentru
restul, `python3 monitor_watch.py --backfill PRIMUL ULTIMUL` e mai simplu și
pune și linkul corect către ediție.

Rulare:
    python3 import_pdf.py FOLDER_CU_PDF-URI
    python3 import_pdf.py FOLDER --dry-run     # arată ce ar adăuga, fără să scrie

Se pune lângă monitor_watch.py și date.json — refolosește exact aceleași reguli
de clasificare, deci nu există riscul ca PDF-urile să fie filtrate altfel decât
edițiile luate de pe site.

Are nevoie de un extractor de text. În ordinea preferinței:
    pdftotext   (poppler-utils; cel mai bun, păstrează așezarea în pagină)
    pdfplumber  (pip install pdfplumber)
    pypdf       (pip install pypdf)
Ajunge oricare dintre ele.
"""

import json
import os
import re
import shutil
import subprocess
import sys
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

try:
    import monitor_watch as mw
except ImportError:
    sys.exit("Nu găsesc monitor_watch.py. Pune import_pdf.py în același folder.")

DATA = os.path.join(HERE, "date.json")


# ------------------------------------------------------------ extragere text

def repara_deplasarea(text):
    """Repară paginile în care textul iese ca „GHVWLQDWH" în loc de „destinate".

    Unele ediții folosesc fonturi încorporate fără tabelă ToUnicode, iar
    extractorul scoate codurile interne ale fontului în locul literelor. Nu e
    text pierdut: e o deplasare fixă de 29 de poziții. Spațiul (0x20) iese ca
    0x03, „G" e „d", „H" e „e". Îl folosim ca semnătură: o linie care conține
    0x03 e o linie deplasată și o mutăm înapoi.

    Fără reparația asta, cuprinsul acelor ediții e ilizibil și actele lor nu
    ajung niciodată în registru — tăcut, fiindcă fișierul se citește „cu
    succes", doar că iese abureală.
    """
    if "\x03" not in text:
        return text
    linii = []
    for linie in text.split("\n"):
        if "\x03" in linie:
            linie = "".join(
                chr(ord(c) + 29) if 0x03 <= ord(c) <= 0x61 and c != " " else c
                for c in linie)
        linii.append(linie)
    return "\n".join(linii)


def text_din_pdf(cale):
    """Întoarce textul PDF-ului, cu primul extractor disponibil."""
    return repara_deplasarea(_text_brut(cale))


def _text_brut(cale):
    if shutil.which("pdftotext"):
        try:
            r = subprocess.run(["pdftotext", "-layout", "-enc", "UTF-8", cale, "-"],
                               capture_output=True, timeout=120)
            if r.returncode == 0 and r.stdout:
                return r.stdout.decode("utf-8", "replace")
        except Exception:
            pass
    try:
        import pdfplumber
        with pdfplumber.open(cale) as pdf:
            return "\n".join((p.extract_text() or "") for p in pdf.pages)
    except ImportError:
        pass
    except Exception:
        return ""
    try:
        from pypdf import PdfReader
        return "\n".join((p.extract_text() or "") for p in PdfReader(cale).pages)
    except ImportError:
        sys.exit("Niciun extractor de PDF găsit. Instalează unul:\n"
                 "  sudo apt install poppler-utils     (recomandat)\n"
                 "  sau: pip install pdfplumber")
    except Exception:
        return ""


# ------------------------------------------------------------ parsare cuprins

# În PDF, un rând de cuprins se rupe pe mai multe linii:
#     421. Decret pentru inițierea negocierilor și aprobarea semnării
#     Amendamentului la Acordurile de finanțare dintre Republica Moldova
#     și Asociația Internațională pentru Dezvoltare (nr. 741-X, 21 august 2026)
# De aceea lipim tot textul într-un singur șir și căutăm global, cu ancora
# „(nr. …)" la final. Punctele de umplere din cuprins („….....") se șterg.
#
# Titlul TREBUIE să poată conține paranteze. Denumirile reale sunt pline de
# ele — „(BIRD)", „(Proiectul ÎMMM)", „(irigații)", „(TEN-T)" — iar o versiune
# care le interzicea rata tăcut majoritatea actelor, inclusiv acorduri de
# împrumut cu BERD. Ancora rămâne sigură fiindcă cerem ca ultima paranteză să
# arate a număr de act: începe cu „nr." și se termină cu un an din patru cifre.
LUNI = ("ianuarie|februarie|martie|aprilie|mai|iunie|iulie|august|"
        "septembrie|octombrie|noiembrie|decembrie")

# Ancora de final: „(nr. 741-X, 21 august 2026)" sau „(nr. 88 din 20.10.2005)".
# Cerem o dată adevărată, altfel potrivirea se agață și de anunțuri din partea
# a V-a, gen „(nr. cadastral 2527100323)".
ACT_NR = (r"nr\.?\s*[^()]{0,60}?(?:\d{1,2}\s+(?:" + LUNI + r")\s+\d{4}"
          r"|\d{1,2}\.\d{2}\.\d{4})")

ITEM_PDF = re.compile(
    r"(?:^|\s)(\d{1,4}[a-z]?)\.\s+"              # numărul poziției
    r"([A-ZĂÂÎȘȚ].{14,600}?)"                    # denumirea, începe cu majusculă
    r"\s*\(\s*(" + ACT_NR + r")\s*\)",
    re.DOTALL,
)

# Gunoi tipic care apare când o potrivire sare peste antetul unei pagini sau
# înghite începutul intrării următoare din cuprins.
GUNOI = re.compile(
    r"monitorul\.gov\.md|ISSN|MOLDPRES|PARTEA\s+[IVX]+"
    r"|\b\d{2,4}\.\s+(?:Decret|Lege|Hotărâre|Ordin|Decizie|Aviz|Dispozi)",
    re.I)

NR_EDITIE = re.compile(r"Nr\.\s*(\d{1,4}(?:\s*[-–]\s*\d{1,4})?)")
DATA_EDITIE = re.compile(r"din\s+(\d{1,2})\.(\d{2})\.(\d{4})")
DATA_COPERTA = re.compile(
    r"(\d{1,2})\s+(ianuarie|februarie|martie|aprilie|mai|iunie|iulie|august|"
    r"septembrie|octombrie|noiembrie|decembrie)\s+(\d{4})", re.IGNORECASE)


def curata(s):
    s = re.sub(r"[.·•]{3,}", " ", s)      # puncte de umplere din cuprins
    s = re.sub(r"-\s*\n\s*", "", s)       # cuvinte despărțite la capăt de rând
    return re.sub(r"\s+", " ", s).strip()


def meta_editie(text, nume_fisier, nr_la_id=None):
    """Numărul ediției, data ei și, dacă se poate, ID-ul de pe site."""
    cap = text[:4000]

    m = NR_EDITIE.search(cap)
    nr = re.sub(r"\s*[-–]\s*", "-", m.group(1)) if m else ""

    data = ""
    m = DATA_EDITIE.search(cap)
    if m:
        data = f"{int(m.group(1)):02d}.{m.group(2)}.{m.group(3)}"
    else:
        m = DATA_COPERTA.search(cap)
        if m:
            luna = mw.MONTHS.get(mw.norm(m.group(2)), 0)
            if luna:
                data = f"{int(m.group(1)):02d}.{luna:02d}.{m.group(3)}"

    # Cel mai sigur ID: cel pe care îl știm deja din registru pentru acest număr
    # de ediție, pus acolo de colectarea de pe site.
    if nr_la_id and nr in nr_la_id:
        return nr, data, nr_la_id[nr]

    # Altfel, dacă numele fișierului conține ID-ul (ex. 3322.pdf).
    #
    # Capcană: „MO_2025_055-060.pdf" — anul din nume arată exact ca un ID, iar
    # ID-uri reale de patru cifre chiar încep de la 2000, deci nu le putem
    # deosebi după mărime. Refuzăm doar numerele care sunt clar anul ediției
    # sau un an din numele fișierului. Când rămânem fără candidat sigur, mai
    # bine niciun link decât un link greșit.
    ani = set(re.findall(r"(?:19|20)\d{2}", os.path.basename(nume_fisier)))
    if data:
        ani.add(data[-4:])
    eid = ""
    for cand in re.findall(r"\d{4}", os.path.basename(nume_fisier)):
        if cand in ani:
            continue
        if nr and cand in nr:
            continue
        if 2000 <= int(cand) <= 4999:
            eid = cand
            break
    return nr, data, eid


def acte_din_text(text, nr, data, eid, url):
    plat = curata(text)
    gasite, vazute = [], set()
    for m in ITEM_PDF.finditer(plat):
        titlu = curata(m.group(2))
        act = curata(m.group(3))
        if len(titlu) < 20 or GUNOI.search(titlu):
            continue
        cat = mw.classify(titlu)
        if not cat:
            continue
        cheie = act + "|" + titlu[:60]
        if cheie in vazute:          # cuprinsul apare uneori de două ori
            continue
        vazute.add(cheie)
        gasite.append({
            "act": act,
            "titlu": titlu,
            "categorie": cat,
            "partener": mw.partner(titlu),
            "semnat": mw.signed_on(titlu),
            "editie": nr or "?",
            "data_editie": data,
            "editie_id": eid or ("pdf-" + (nr or "?")),
            "url": url,
            "sursa": "PDF",
        })
    return gasite


# ------------------------------------------------------------------- import

def e_ruseasca(text):
    """Ediția în limba rusă — aceleași acte, dar filtrul e scris în română.

    Nu ne bazăm pe numele fișierului: în arhive apar „…2026rus.pdf",
    „…202rus.pdf", chiar „…2026us.pdf". Ne uităm direct în text.
    """
    proba = text[:4000]
    chirilice = sum(1 for c in proba if "\u0400" <= c <= "\u04FF")
    litere = sum(1 for c in proba if c.isalpha())
    return litere > 200 and chirilice / litere > 0.3


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    dry = "--dry-run" in sys.argv
    if not args:
        sys.exit("Folosire: python3 import_pdf.py FOLDER_CU_PDF-URI [--dry-run]")

    sursa = args[0]
    temp = None
    if zipfile.is_zipfile(sursa):
        temp = os.path.join(HERE, "_pdf_temp")
        os.makedirs(temp, exist_ok=True)
        print(f"Dezarhivez {sursa}…")
        with zipfile.ZipFile(sursa) as z:
            z.extractall(temp)
        sursa = temp

    pdfs = []
    for radacina, _, fisiere in os.walk(sursa):
        for f in sorted(fisiere):
            if f.lower().endswith(".pdf"):
                pdfs.append(os.path.join(radacina, f))
    if not pdfs:
        sys.exit(f"Niciun PDF în {sursa}.")
    print(f"{len(pdfs)} PDF-uri de citit.\n")

    db = mw.load()
    # Un act deja în registru NU se dublează, indiferent din ce sursă a venit.
    existente = {mw.norm(a["act"]) for a in db["acte"].values()}
    # Numerele de ediție deja colectate de pe site ne dau ID-ul real, deci
    # linkul corect, chiar dacă numele fișierului PDF nu conține nimic util.
    nr_la_id = {a["editie"]: a["editie_id"] for a in db["acte"].values()
                if a.get("editie") and str(a.get("editie_id", "")).isdigit()}

    noi = fara_text = rusesti = 0
    for i, cale in enumerate(pdfs, 1):
        nume = os.path.basename(cale)
        text = text_din_pdf(cale)
        if not text.strip():
            print(f"[{i}/{len(pdfs)}] {nume}: fără text (scanat?) — sărit")
            fara_text += 1
            continue
        if e_ruseasca(text):
            print(f"[{i}/{len(pdfs)}] {nume}: ediție în rusă — sărită")
            rusesti += 1
            continue

        nr, data, eid = meta_editie(text, cale, nr_la_id)
        url = (f"https://monitorul.gov.md/ro/monitor/{eid}" if eid
               else "https://monitorul.gov.md/ro/search")

        adaugate = 0
        for act in acte_din_text(text, nr, data, eid, url):
            if mw.norm(act["act"]) in existente:
                continue
            db["acte"][act["act"] + "|" + act["editie_id"]] = act
            existente.add(mw.norm(act["act"]))
            adaugate += 1
            print(f"     + {act['categorie']}: {act['titlu'][:70]}…")
        noi += adaugate
        eticheta = f"Nr. {nr} din {data}" if nr and data else nume
        print(f"[{i}/{len(pdfs)}] {eticheta}: {adaugate} acte noi")

    print(f"\n{noi} acte noi. Total în registru: {len(db['acte'])}.")
    if rusesti:
        print(f"{rusesti} ediții în rusă sărite (dublurile celor românești).")
    if fara_text:
        print(f"{fara_text} PDF-uri fără strat de text — acelea au nevoie de OCR.")

    if dry:
        print("\n--dry-run: nu am scris nimic.")
    else:
        mw.save(db)
        print(f"\nAm scris {DATA}. Urcă-l pe GitHub — acorduri.html îl citește direct.")

    if temp:
        shutil.rmtree(temp, ignore_errors=True)


if __name__ == "__main__":
    main()
