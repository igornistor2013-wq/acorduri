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
  5. Pagina acorduri.html citește date.json direct — nu se generează nimic

Fișierele apar lângă script.
"""

import json
import os
import re
import sys
import time
from datetime import datetime, date

try:
    import requests
    from bs4 import BeautifulSoup
except ImportError:
    sys.exit("Lipsesc biblioteci. Rulează:  pip install requests beautifulsoup4")

BASE = "https://monitorul.gov.md"
HOME = BASE + "/ro"

# Câte ediții sărite recuperăm într-o singură rulare. Fiecare costă o secundă
# de pauză, deci 25 înseamnă sub un minut în plus; un gol mai mare se închide
# în rulările următoare, câte 25 pe zi.
MAX_RECUPERARI = 25

# Cât are voie să dureze citirea edițiilor, în secunde. Workflow-ul oprește
# job-ul după un număr fix de minute, iar o oprire forțată nu mai apucă să
# salveze nimic: tot ce se citise în rularea aceea se pierdea. O ediție care
# nu răspunde costă până la 100 de secunde (trei încercări a câte 30, plus
# pauzele), iar o rulare poate cere zece ediții și 25 de recuperări. Când
# bugetul se termină, ne oprim noi, salvăm ce avem și lăsăm restul pe mâine.
BUGET_SECUNDE = 7 * 60
HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "date.json")

UA = {"User-Agent": "Mozilla/5.0 (compatible; monitor-watch/1.0)"}

# ---------------------------------------------------------------- clasificare

# Termeni care indică un act de finanțare externă, grupați pe categoriile de
# asistență externă din HG 377/2018, anexa nr. 1, pct. 9:
#
#   Grant                (pct. 9.13)  asistență financiară nerambursabilă
#   Împrumut             (pct. 9.2)   asistență financiară rambursabilă
#   Suport bugetar       (pct. 9.20¹) transferat direct în bugetul public
#   Asistență tehnică    (pct. 9.3)   consultanță, instruire, expertiză
#   Asistență financiară (pct. 9.2)   categoria-părinte, folosită doar când
#                                     titlul nu spune dacă e rambursabilă
#
# „Credit" și „Contract de finanțare" nu mai sunt categorii separate, fiindcă
# nu există ca noțiuni în regulament: facilitatea de credit e tot împrumut, iar
# contractul de finanțare e denumirea pe care Banca Europeană de Investiții o
# dă instrumentului ei de creditare a proiectelor de investiții.
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
    # Asistența financiară se împarte după rambursare (HG 377/2018, anexa 1, pct. 9):
    # nerambursabilă = grant, rambursabilă = împrumut („credit"). Tiparele de aici țin
    # de PRIMIREA actului în registru; ce categorie primește o hotărăște corecteaza(),
    # mai jos. Formele gramaticale contează: titlurile scriu „asistenței financiare
    # nerambursabile" (genitiv, plural), nu doar „asistența financiară nerambursabilă".
    (r"asistent\w*\s+financiar\w*\s+nerambursabil\w*", "Grant"),
    (r"asistent\w*\s+financiar\w*\s+rambursabil\w*", "Împrumut"),
    # „ajutor nerambursabil" cere și un cuvânt de acord: hotărârile despre primirea ori
    # vămuirea unui ajutor nu sunt acorduri.
    # („acordarea" și „acordat" nu sunt acorduri, de aceea lista de forme e închisă.)
    (r"(?=.*\b(?:acord(?:ul|ului|uri|urile|urilor)|memorand\w*|intelegeri\w*|conventi\w*)\b)"
     r".*\bajutor\w*\s+(?:financiar\w*\s+)?nerambursabil\w*", "Grant"),
    # împrumuturi
    (ACORD + r"\s+de\s+imprumut", "Împrumut"),
    (CONTRACT + r"\s+de\s+imprumut", "Împrumut"),
    # finanțare
    (ACORD + r"\s+de\s+finan", "Asistență financiară"),
    (r"conventi(?:a|e|ei|i|ile|ilor)?\s+de\s+finan", "Asistență financiară"),
    (r"cooperare\s+si\s+finantare", "Asistență financiară"),
    (ACORD + r"\s+de\s+cooperare\s+financiara", "Asistență financiară"),
    (ACORD + r"\s+de\s+(?:asistenta|sprijin)\s+financiar", "Asistență financiară"),
    (r"asistenta\s+(?:financiara\s+)?(?:externa|macrofinanciara)", "Asistență financiară"),
    (r"memorandum[^.]{0,80}?(?:finantare|imprumut|macrofinanciar)", "Asistență financiară"),
    # suport bugetar — pct. 9.20¹: asistență transferată direct în bugetul
    # public național, pentru susținerea reformelor agreate. Instrumentele prin
    # care vine sunt denumite variat, dar toate înseamnă același lucru:
    # contractul de performanță pentru reforma sectorială al Uniunii Europene,
    # asistența macrofinanciară, Facilitatea de reformă și creștere.
    # Suportul bugetar nu mai e o categorie aici — vezi SUPORT_BUGETAR mai jos.
    # Tiparele rămân în listă doar ca actul să intre în registru chiar dacă
    # titlul nu numește niciun instrument.
    (r"suport\s+bugetar", "Asistență financiară"),
    (r"contract(?:ul|ului)?\s+de\s+performanta\s+pentru\s+reforma", "Asistență financiară"),
    (r"asistenta\s+macrofinanciara", "Asistență financiară"),
    (r"facilitat\w*\s+de\s+reforma\s+si\s+crestere", "Asistență financiară"),
    # contract de finanțare (mai specific decât „finanțare")
    (CONTRACT + r"\s+de\s+finan", "Împrumut"),
    # credite
    (r"facilitate\s+de\s+credit", "Împrumut"),
    (r"linie\s+de\s+credit", "Împrumut"),
    (ACORD + r"\s+de\s+credit", "Împrumut"),
    (CONTRACT + r"\s+de\s+credit", "Împrumut"),
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
    # „Facilitatea de cooperare tehnică 2016" și „Facilitatea pentru cooperare tehnică" sunt
    # același instrument al Uniunii Europene; titlurile au scris-o în ambele feluri, iar
    # forma cu „pentru" ajungea, după finanțator, la Grant.
    (r"facilitat\w*\s+(?:de|pentru)\s+cooperare\s+tehnica", "Asistență tehnică"),
    (r"memorandum[^.]{0,60}?asistenta\s+tehnica", "Asistență tehnică"),
    (r"proiect(?:ul|ului)?\s+de\s+asistenta\s+tehnica", "Asistență tehnică"),
]

# Termeni care înseamnă că actul NU e despre finanțare externă,
# chiar dacă a trecut de filtrul de mai sus.
# Tipare care intră în registru DOAR dacă în titlu apare un partener extern
# recunoscut. „Acord de colaborare dintre…" și memorandumurile despre instruire
# sau consultanță sunt formulări folosite la fel de des pentru înțelegeri interne
# între instituții moldovenești — colaborarea dintre un minister și o academie
# militară, instruirea studenților cu o universitate din România. Fără condiția
# asta, oricare dintre ele intra în registru ca „Grant" sau „Asistență tehnică".
#
# Nu putem cere ca termenul-cheie să stea lângă cuvântul „acord": în titlurile
# reale, între ele încap denumirile complete ale ambelor părți — 140 de caractere
# în cazul acordului cu Agenția Elvețiană pentru Dezvoltare și Cooperare.
INCLUDE_PARTENER = [
    # „Acord de colaborare dintre X și PNUD pentru implementarea proiectului Y".
    # Titlul nu numește niciun instrument financiar, deci nu e grant — asta ar
    # afirma că banii sunt nerambursabili, ceea ce textul nu spune. Dar nici nu
    # e un act oarecare: o agenție de dezvoltare care implementează un proiect
    # aduce expertiză și capacitate de execuție, adică exact ce descrie pct. 9.3
    # ca asistență tehnică — sprijin nerambursabil pentru transfer de cunoștințe
    # și consolidarea capacităților instituționale.
    #
    # Regula cere un partener extern recunoscut, altfel ar înghiți orice
    # colaborare între două instituții moldovenești.
    (ACORD + r"\s+de\s+colaborare\s+dintre", "Asistență tehnică"),
    (r"(?=.*\b(?:acord|acordul|acordului|memorandum|memorandumul|memorandumului)\b)"
     r".*\b(?:consultanta|instruire|expertiza|transfer\s+de\s+cunostinte)",
     "Asistență tehnică"),
]

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
    # avizele Guvernului la proiecte de lege — opinii, nu acorduri
    r"\baviz\b\s+la\s+proiectul\s+de\s+lege",
]

# Partenerii externi recunoscuți, pentru coloana „Partener".
# Tiparele se aplică tot pe text normalizat (fără diacritice), ca să prindem și
# „Asociaţia" cu ş-cedilă, și „Asociația" cu ș-virgulă — în Monitor apar ambele.
PARTNERS = [
    # În titlurile oficiale apare și forma greșită „pentru Reconstrucții".
    (r"\bbird\b|banca internationala pentru reconstructi", "BIRD"),
    (r"\bberd\b|banca europeana pentru reconstructi", "BERD"),
    (r"\bbei\b|banca europeana de investitii", "BEI"),
    (r"\baid\b|asociatia internationala pentru dezvoltare", "AID"),
    (r"banca mondiala|grupul bancii mondiale", "Banca Mondială"),
    # În Republica Moldova banca e citată drept CEB (Council of Europe
    # Development Bank), nu BDCE — așa apare în actele Ministerului Finanțelor
    # și în comunicatele OGPAE. BDCE e forma folosită mai ales în România.
    (r"\bceb\b|\bbdce\b|banca de dezvoltare a consiliului europei", "CEB"),
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
    # Bank Gospodarstwa Krajowego e banca de dezvoltare a Poloniei; apare în
    # titluri sub denumirea poloneză, fără traducere.
    (r"guvernul poloniei|bank gospodarstwa krajowego|\bbgk\b", "Polonia"),
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


# Unele titluri din legis.md au litere chirilice în loc de cele latine, în două feluri:
#
#   • cod de pagină greșit — textul în cp1250 citit ca cp1251: „оmprumut" (împrumut),
#     „finanюare" (finanțare), „Germanг" (Germană), „fьr" (für): о=î, ю=ț, г=ă, ь=ü;
#   • litere care arată la fel, strecurate la tastare: „сu" (cu), „сredit" (credit),
#     „sеmnаrеа" (semnarea), „sеmпаrеа" (п în loc de n).
#
# Fără reparație, „сredit" sau „оmprumut" scapă tiparelor și actul rămâne necategorisit
# sau ajunge, după finanțator, în altă categorie decât cea din titlu.
_CHIRILIC = str.maketrans({
    "ю": "t", "г": "a", "ь": "u",                                   # cp1250 citit ca cp1251
    "а": "a", "с": "c", "е": "e", "р": "p", "п": "n", "х": "x", "у": "y",
    "і": "i", "ѕ": "s", "ј": "j", "к": "k", "м": "m", "т": "t", "н": "h",
    "о": "o",
})


def norm(text):
    """Text cu diacritice reduse, pentru potrivire robustă."""
    t = text.lower()
    if re.search("[\u0400-\u04ff]", t):
        # „о" la început de cuvânt, înaintea lui n/m, e „î" cu cod de pagină greșit: „оn", „оmprumut"
        t = re.sub(r"(?<![\w])о(?=[nm])", "i", t)
        t = t.translate(_CHIRILIC)
    for a, b in (("ă", "a"), ("â", "a"), ("î", "i"), ("ș", "s"),
                 ("ş", "s"), ("ț", "t"), ("ţ", "t")):
        t = t.replace(a, b)
    return t


def categorie_bruta(title):
    """Categoria după tiparele din titlu, ÎNAINTE de a ține seama de rambursare și de finanțator.

    „Asistență financiară" apare aici ca atare când titlul numește doar finanțarea;
    classify() o transformă în Grant sau Împrumut. Separarea e pentru registrul legis.md,
    care are o listă de parteneri mai largă și trebuie să rezolve aceeași categorie-părinte
    cu ea, nu cu lista de aici."""
    n = norm(title)
    for pat in EXCLUDE:
        if re.search(norm(pat), n):
            return None
    # Cea mai specifică potrivire câștigă: contract de finanțare > finanțare.
    hits = []
    for pat, cat in INCLUDE:
        if re.search(norm(pat), n):
            hits.append(cat)
    if partner(title):
        for pat, cat in INCLUDE_PARTENER:
            if re.search(norm(pat), n):
                hits.append(cat)
    if not hits:
        return None
    # Ordinea de preferință: instrumentul bate canalul de livrare.
    #
    # Suportul bugetar (pct. 9.20¹) descrie CUM ajung banii — direct în buget —
    # nu dacă se întorc. „Acordul de împrumut privind Facilitatea de reformă și
    # creștere" e suport bugetar livrat ca împrumut; îl trecem la Împrumut,
    # fiindcă asta spune ce datorează statul. Rămâne Suport bugetar doar când
    # titlul nu numește niciun instrument.
    #
    # La fel, un grant care plătește servicii de consultanță rămâne grant:
    # asistența tehnică se aplică atunci când actul nu numește un instrument
    # financiar, ci descrie chiar transferul de expertiză.
    #
    # „Asistență financiară" e ultima, fiind categoria-părinte din pct. 9.2: o
    # folosim doar când titlul nu spune dacă banii sunt rambursabili sau nu.
    for pref in ORDINE_CATEGORII:
        if pref in hits:
            return pref
    return hits[0]


# Ordinea de preferință între categorii, de la cea mai specifică. Folosită la alegerea
# categoriei unui act (aici) și a unui acord cu acte de categorii diferite (acorduri.html).
ORDINE_CATEGORII = ("Împrumut", "Grant", "Asistență tehnică", "Asistență financiară")


def classify(title, partner_fn=None):
    """Returnează categoria actului, sau None dacă nu e relevant.

    partner_fn: funcția care spune cine e finanțatorul; registrul legis.md o dă pe a lui,
    cu o listă de parteneri mai largă (vezi dupa_finantator)."""
    cat = categorie_bruta(title)
    return corecteaza(title, cat, partner_fn) if cat else None


# ------------------------------------------------------------------ rambursare
#
# Asistența financiară se împarte, după HG 377/2018 (anexa 1, pct. 9), în două:
#
#   nerambursabilă  →  Grant     (pct. 9.13)
#   rambursabilă    →  Împrumut  (pct. 9.2), în vorbirea curentă „credit"
#
# Titlul spune adesea care din ele e: „asistența financiară rambursabilă",
# „ajutor financiar nerambursabil", „grantul danez", „acordul de credit". Cuvântul
# acela hotărăște, înaintea oricărei deducții după cine dă banii: Guvernul României
# a dat și grant (programul de asistență tehnică și financiară „în baza unui ajutor
# financiar nerambursabil"), și credit („asistența financiară rambursabilă"), iar
# după finanțator singur cele două s-ar fi numit la fel.
#
# Doar când titlul nu spune nimic despre rambursare se judecă după finanțator —
# băncile de dezvoltare împrumută, agențiile de cooperare donează — și, dacă nici
# finanțatorul nu lămurește, categoria rămâne „Asistență financiară".

# Nerambursabil, în toate formele („nerambursabil", „-ă", „-e", „-ei"), plus formulările
# care spun același lucru fără cuvântul acela.
RX_NERAMB = (r"\bnon-?rambursabil\w*|\bnerambursabil\w*|fara\s+rambursare|"
             r"cu\s+titlu\s+(?:gratuit|de\s+donatie)")
# Rambursabil. „non-rambursabil" nu e rambursabil.
RX_RAMB = r"(?<!non-)\brambursabil\w*"
# „Asistența tehnică nerambursabilă" spune că expertiza vine gratuit, nu că banii sunt
# grant: rămâne asistență tehnică. „Asistență tehnică și financiară ... ajutor financiar
# nerambursabil" e altceva — acolo nerambursabil stă lângă „financiar".
RX_TEHNIC_NERAMB = r"(?:asistent|cooperar|ajutor)\w*\s+tehnic\w*\s+(?:\w+\s+)?(?:" + RX_NERAMB + ")"
# Instrumentul numit direct. Împrumutul/creditul numit în titlu bate clasificarea după
# partener: „Acordul cu Guvernul României referitor la împrumut" e împrumut, deși
# România e de obicei donator.
RX_IMPRUMUT = (r"(?:acord|contract|conventi)\w*[- ]*(?:cadru\s+)?de\s+(?:imprumut|credit)|"
               r"\bimprumut\w*\b|\bcredit(?:ul|ului|e|ele)?\b")
RX_GRANT = r"\bgrant(?:ul|ului|uri|urile|urilor|e)?\b|\bgrand\b"      # „grand" e o greșeală de scriere din titluri
RX_ACORD_GRANT = r"acord\w*\s+de\s+gran[dt]"


def regim_rambursare(title):
    """Ce spune titlul despre rambursare: 'nerambursabil', 'rambursabil', 'mixt' sau None."""
    n = norm(title)
    neramb = bool(re.search(RX_NERAMB, re.sub(RX_TEHNIC_NERAMB, " ", n)))
    ramb = bool(re.search(RX_RAMB, n))
    if neramb and ramb:
        return "mixt"
    return "nerambursabil" if neramb else "rambursabil" if ramb else None


def corecteaza(title, cat, partner_fn=None):
    """Categoria finală a unui act, din categoria găsită de tipare (cat).

    Ordinea: 1. rambursabil (sau amestec) → Împrumut; 2. împrumut/credit numit în titlu
    → Împrumut (un titlu care numește și un „acord de grant" rămâne grant doar dacă
    tiparele nu l-au găsit deja împrumut: „Acordul de credit … și Acordul de grant …"
    e un act despre un credit); 3. nerambursabil → Grant; 4. grantul numit în titlu →
    Grant; 5. „Asistență financiară" rămasă → după finanțator."""
    n = norm(title)
    rg = regim_rambursare(title)
    acord_grant = bool(re.search(RX_ACORD_GRANT, n))
    if rg in ("rambursabil", "mixt"):
        return "Împrumut"
    if re.search(RX_IMPRUMUT, n) and (cat == "Împrumut" or not acord_grant):
        return "Împrumut"
    if rg == "nerambursabil":
        return "Grant"
    if acord_grant or re.search(RX_GRANT, n):
        return "Grant"
    if cat == "Asistență financiară":
        return dupa_finantator(title, partner_fn)
    return cat


# Suportul bugetar e un mod de livrare, nu un instrument.
#
# Pct. 9.20¹ îl definește ca asistență financiară transferată direct într-un
# buget component al bugetului public național. Poate fi grant — Contractul de
# performanță pentru reforma sectorială al Uniunii Europene — sau împrumut, cum
# e Facilitatea de reformă și creștere. Ca și categorie separată, el ascundea
# tocmai informația care contează: dacă statul are sau nu de rambursat.
#
# Așa că nu mai e categorie, ci un semn care însoțește categoria. Cele patru
# acte despre Facilitatea de reformă și creștere rămân la „Împrumut", dar poartă
# și marcajul; cele două despre Contractul de performanță sunt granturi cu
# marcaj. Categoria spune ce datorează statul, marcajul spune unde ajung banii.
SUPORT_BUGETAR = [
    r"suport\s+bugetar",
    r"contract(?:ul|ului)?\s+de\s+performanta\s+pentru\s+reforma",
    r"asistenta\s+macrofinanciara",
    r"facilitat\w*\s+de\s+reforma\s+si\s+crestere",
]


def e_suport_bugetar(title):
    n = norm(title)
    return any(re.search(norm(p), n) for p in SUPORT_BUGETAR)


# Cine dă banii spune, în practică, dacă se întorc.
#
# „Acord de finanțare" nu arată în titlu dacă e rambursabil, dar finanțatorul
# arată: băncile de dezvoltare împrumută, agențiile de cooperare donează.
# Acordul de finanțare cu AID e un împrumut — Ministerul Economiei îl numește
# explicit așa: „29,8 mil. Euro împrumutul AID". Acordurile de finanțare cu
# Comisia Europeană pentru URBACT, Interreg sau Planul de acțiuni multianual
# sunt granturi, la fel acordurile de cooperare și finanțare cu Federația
# Internațională de Cruce Roșie.
#
# Doar o regulă de rezervă: cuvintele din titlu (rambursabil, nerambursabil, grant,
# împrumut, credit) trec înaintea ei — vezi corecteaza().
#
# Pentru un finanțator necunoscut, sau care face și una, și alta (KfW: a dat Moldovei
# și grant — infrastructură socială, 5 mil. euro —, și credit; Agenția Japoneză JICA),
# rămânem la categoria-părinte: mai bine neclasificat decât clasificat greșit. De aceea
# KfW nu stă în nicio listă, iar un act cu KfW se lămurește doar din cuvintele titlului
# sau dintr-o hotărâre scrisă în date/categorii_manual.json.
#
# Banca Mondială și FIDA (IFAD) împrumută; granturile lor — „grant danez", fondul
# fiduciar ASAP — își spun grant în titlu și sunt prinse de regula grantului.
# Hewlett-Packard și Siemens au finanțat în rate (leasing, credit furnizor): se
# întorc. Băncile comerciale străine la fel. Bulgaria dă Moldovei doar granturi
# (portalul AMP trece asistența bulgară ca grant), deci stă între donatori.
CREDITORI = {"AID", "BIRD", "BERD", "BEI", "CEB", "AFD", "FMI", "Belgia",
             "Banca Mondială", "FIDA",
             "Canada", "OFID", "BSTDB", "Kuweit", "Japonia (JBIC)",
             "Bancă comercială străină", "Hewlett-Packard", "Siemens (Germania)"}
DONATORI  = {"UE", "FICR", "PNUD", "UNICEF", "UNHCR", "GIZ", "Suedia", "Elveția",
             "SUA", "PAM", "UNOPS", "Consiliul Europei", "România", "Polonia",
             "Turcia", "Japonia", "Germania",
             "Cehia", "Austria", "Olanda", "Coreea", "SUA (MCC)", "Fondul Global",
             "Regatul Unit", "Nordici", "Baltici", "Bulgaria"}
# Corporația Financiară Internațională împrumută firmelor private, nu statului. Acordurile
# ei cu Guvernul (proiectul „Reforma climatului investițional”, finanțat de donatori și
# implementat de IFC; statul contribuie în natură, nu din buget) sunt de consultanță: nu
# sunt credit, deși numele ei sună a bancă.
CONSULTANTI = {"IFC"}
# Băncile chineze care au împrumutat drumurile (ICBC, Citic, Bank of Communications) apar
# ca „China", iar China dă și granturi: le recunoaștem după numele băncii.
RX_BANCA_CREDITOARE = (r"\bicbc\b|citic bank|bank of communication|bank of china|"
                       r"banca industriala si comerciala|export[- ]credit|exim\s?bank")


def dupa_finantator(title, partner_fn=None):
    """Împrumut sau Grant după finanțator; „Asistență financiară" când nu se poate spune.

    partner_fn: cine e finanțatorul. Registrul legis.md își dă lista lui de parteneri
    (denumiri vechi: „Asociația Internațională de Dezvoltare", „Comisia Comunităților
    Europene"), pe care partner() de aici n-o cunoaște."""
    parti = [p.strip() for p in ((partner_fn or partner)(title) or "").split(" / ") if p.strip()]
    if parti and all(p in CREDITORI for p in parti):
        return "Împrumut"
    if parti and all(p in DONATORI for p in parti):
        return "Grant"
    if parti and all(p in CONSULTANTI for p in parti):
        return "Asistență tehnică"
    if re.search(RX_BANCA_CREDITOARE, norm(title)) and not any(p in DONATORI for p in parti):
        return "Împrumut"
    return "Asistență financiară"


# Când o instituție specifică e recunoscută, denumirea mai generală care apare
# în propriul ei nume devine zgomot: „Banca de Dezvoltare a Consiliului Europei"
# e CEB, nu „CEB / Consiliul Europei".
REDUNDANT = {"CEB": "Consiliul Europei"}


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
        if norm(name) != mon:
            continue
        # Verificăm că data chiar există. Un titlu cu „31 februarie" nu e
        # imposibil — sunt texte scrise de om — iar o dată inventată ar ajunge
        # în registru și de acolo în exportul Excel, arătând la fel de sigură
        # ca oricare alta. Mai bine niciun răspuns decât unul fals.
        try:
            date(int(year), num, int(day))
        except ValueError:
            print(f"   ! data semnării imposibilă, o ignor: {day} {name} {year}")
            return ""
        return f"{int(day):02d}.{num:02d}.{year}"
    return ""


# ------------------------------------------------------------------ colectare

def get(url, tries=3, pauze=(3, 8, 20, 45)):
    """Descarcă o pagină, cu reîncercări răbdătoare.

    Pe 16 septembrie colectarea a picat fiindcă monitorul.gov.md n-a răspuns:
    trei încercări a câte 30 de secunde, 98 de secunde în total, apoi ieșire cu
    eroare. Site-ul își revenise probabil în minutul următor, dar rularea era
    deja pierdută, iar ziua aceea a rămas necolectată.

    Pauzele cresc: 3, 8, 20, 45 de secunde. Un hop de rețea de un minut nu mai
    doboară rularea, iar o pană adevărată tot e semnalată — doar că după ce am
    dat sursei o șansă reală."""
    ultima = None
    for i in range(tries):
        try:
            r = requests.get(url, headers=UA, timeout=30)
            r.raise_for_status()
            r.encoding = "utf-8"
            return r.text
        except Exception as e:
            ultima = e
            # „Nu există" nu e o pană trecătoare: a doua și a treia încercare ar
            # primi același răspuns, după 11 secunde de pauze pierdute. La 25 de
            # ediții inexistente din șir, asta însemna cinci minute de așteptat.
            cod = getattr(getattr(e, "response", None), "status_code", None)
            if cod in (404, 410):
                print(f"   ! {url}: pagina nu există (HTTP {cod})")
                return None
            if i < tries - 1:
                asteptare = pauze[min(i, len(pauze) - 1)]
                print(f"   … {url} nu răspunde ({e.__class__.__name__}), "
                      f"reîncerc peste {asteptare}s")
                time.sleep(asteptare)
    print(f"   ! nu am putut deschide {url}: {ultima}")
    return None


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
            "suport": e_suport_bugetar(title),
            "url": f"{BASE}/ro/monitor/{eid}",
        })
    return True, found


def acum():
    """Ora Chișinăului, indiferent unde rulează scriptul.

    Pe GitHub Actions ceasul e în UTC, iar „Ultima verificare" de pe pagină
    apărea cu trei ore în urmă vara și cu două iarna, fără nimic care să spună
    că e alt fus orar. Dacă lista fusurilor orare lipsește (Windows fără
    pachetul tzdata), rămânem la ora calculatorului — care, la rularea locală,
    e oricum ora Chișinăului."""
    try:
        from zoneinfo import ZoneInfo
        return datetime.now(ZoneInfo("Europe/Chisinau"))
    except Exception:
        return datetime.now()


def load():
    if not os.path.exists(DATA):
        return {"acte": {}, "editii_vazute": [],
            "editii_esuate": {}, "ultima_rulare": None}
    with open(DATA, encoding="utf-8") as f:
        return json.load(f)


def save(db):
    with open(DATA, "w", encoding="utf-8") as f:
        json.dump(db, f, ensure_ascii=False, indent=2)

# ----------------------------------------------------------------------- main

def tip_act(a):
    """Tipul actului, din primul cuvânt al denumirii: „lege", „hota", „decr", „ordi".

    Patru litere ajung ca să deosebești tipurile și trec peste ortografia veche
    („Hotărîre" și „Hotărâre" dau amândouă „hota")."""
    return norm(a.get("titlu", "")).split(" ")[0][:4]


def identitate(a):
    """Ce face dintr-un rând un act anume: numărul, data ȘI tipul.

    Numărul și data singure nu ajung. Fiecare emitent își numerotează actele
    separat, așa că în aceeași zi pot exista Hotărârea Guvernului nr. 10 și
    Ordinul ministrului finanțelor nr. 10 — în Registrul de stat sunt mai multe
    asemenea perechi. Cu vechea regulă, al doilea îl înlocuia pe primul în
    registru, fără niciun semn."""
    return norm(a["act"]) + "|" + tip_act(a)


def cheie_libera(db, act):
    """Cheia sub care se ține actul în date.json.

    Rămâne „număr|ediție", ca până acum — de ea atârnă legăturile spre legis.md
    din date/legaturi_legis.json. Doar când cheia e deja ocupată de ALT act (alt
    tip, același număr, aceeași ediție) îi adăugăm tipul."""
    key = act["act"] + "|" + act["editie_id"]
    if key in db["acte"] and identitate(db["acte"][key]) != identitate(act):
        key += "|" + tip_act(act)
    return key


def reclasifica(db):
    """Aplică regulile de azi și actelor mai vechi din registru.

    culege() rescrie doar actele din edițiile de pe prima pagină (ultimele zece). Un act
    mai vechi își păstra la nesfârșit categoria de la data când a intrat, chiar dacă
    regulile s-au schimbat între timp: „asistența financiară" rămânea așa, deși azi se
    hotărăște în grant sau împrumut. Un act pe care regulile de azi nu-l mai recunosc își
    păstrează categoria — îl scoate din registru un om, nu o regulă care se schimbă.
    Întoarce [(act, categoria veche, categoria nouă)]."""
    schimbate = []
    for a in db["acte"].values():
        cat = classify(a.get("titlu", ""))
        if cat and cat != a.get("categorie"):
            schimbate.append((a.get("act"), a.get("categorie"), cat))
            a["categorie"] = cat
    return schimbate


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
    dupa_act = {identitate(a): k for k, a in db["acte"].items()}

    noi = 0
    for act in acte:
        ident = identitate(act)
        key = cheie_libera(db, act)
        veche = dupa_act.get(ident)
        if veche and veche != key:
            db["acte"].pop(veche, None)
            db["acte"][key] = act
            dupa_act[ident] = key
            continue
        if key not in db["acte"]:
            db["acte"][key] = act
            dupa_act[ident] = key
            noi += 1
            print(f"     + {act['categorie']}: {act['titlu'][:78]}…")
        else:
            db["acte"][key].update(act)
    return True, noi


# După atâtea încercări nereușite, o ediție e considerată inaccesibilă și nu
# mai e cerută. Numerotarea Monitorului are găuri reale: edițiile speciale și
# volumele suplimentare („424-434b") ocupă numere proprii, iar unele nu ajung
# niciodată pe prima pagină. Fără pragul ăsta, scriptul ar cere la nesfârșit o
# pagină care nu există, iar pagina ar afișa pentru totdeauna un avertisment pe
# care nimeni nu-l poate rezolva.
MAX_INCERCARI = 5


def goluri(db):
    """Edițiile lipsă din șirul celor văzute.

    Pagina principală arată doar zece ediții. La ritmul obișnuit de publicare
    asta înseamnă în jur de trei săptămâni de rezervă — dar dacă automatizarea
    stă mai mult, sau dacă GitHub sare câteva rulări programate, edițiile ies
    din listă înainte de a fi citite și nu mai reapar niciodată. Registrul
    rămâne cu o gaură pe care nimeni n-o observă, fiindcă nimic nu semnalează
    lipsa.

    ID-urile sunt consecutive, așa că orice număr care lipsește între prima și
    ultima ediție văzută e o ediție pe care n-am citit-o.
    """
    vazute = sorted(int(x) for x in db["editii_vazute"] if str(x).isdigit())
    if len(vazute) < 2:
        return []
    renuntat = {int(k) for k, v in db.get("editii_esuate", {}).items()
                if v >= MAX_INCERCARI and str(k).isdigit()}
    return [i for i in range(vazute[0], vazute[-1] + 1)
            if i not in vazute and i not in renuntat]


def spune_schimbari(schimbate):
    if schimbate:
        print(f"\n{len(schimbate)} acte își schimbă categoria după regulile de azi:")
        for act, veche, noua in schimbate[:40]:
            print(f"   ~ {act}: {veche} → {noua}")


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
        db["ultima_rulare"] = acum().strftime("%d.%m.%Y %H:%M")
        spune_schimbari(reclasifica(db))
        save(db)
        print(f"\n{noi} acte noi. Total în registru: {len(db['acte'])}.")
        return

    print("Verific Monitorul Oficial…")
    inceput = time.time()

    def fara_timp():
        return time.time() - inceput > BUGET_SECUNDE

    # Pagina principală e singurul lucru fără de care nu se poate face nimic,
    # așa că îi dăm cinci încercări în loc de trei.
    home = get(HOME, tries=5)
    if not home:
        sys.exit("Nu am putut deschide monitorul.gov.md după 5 încercări. "
                 "Cel mai probabil site-ul e indisponibil — rularea următoare "
                 "reia de unde s-a oprit, fără pierderi.")

    editions = recent_editions(home)
    if not editions:
        sys.exit("Nu am găsit nicio ediție pe pagina principală.")

    # Recitim TOATE edițiile afișate pe prima pagină, nu doar cele nemarcate.
    # Sunt zece pagini, cu o pauză de o secundă între ele — sub un minut. În
    # schimb, orice îmbunătățire a filtrului recuperează retroactiv actele
    # ratate, în loc să le lase pierdute pentru totdeauna.
    noi = 0
    esecuri = []
    amanate = 0
    for eid, label in editions:
        if fara_timp():
            # Necitită acum, nemarcată ca văzută: se reia la rularea următoare.
            esecuri.append(label or eid)
            amanate += 1
            continue
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

    # Recuperarea golurilor. Le citim chiar acum, nu doar le raportăm: o ediție
    # sărită nu se mai întoarce niciodată pe prima pagină, deci dacă n-o luăm
    # aici, e pierdută definitiv. Limita de 25 pe rulare ține timpul sub un
    # minut în plus; dacă golul e mai mare, se închide în rulările următoare.
    # De la cele mai noi spre cele vechi. Golurile recente sunt cele apărute
    # din cauza unei pauze a automatizării și sunt cele pe care le vrea
    # utilizatorul; dacă am porni de la capătul vechi, într-un registru cu
    # multe goluri n-am ajunge niciodată la ediția de săptămâna trecută.
    lipsa = sorted(goluri(db), reverse=True)
    if lipsa:
        print(f"\n{len(lipsa)} ediții lipsă din șir — le recuperez "
              f"({min(len(lipsa), MAX_RECUPERARI)} acum, de la cele mai noi):")
        esuate = db.setdefault("editii_esuate", {})
        for eid in lipsa[:MAX_RECUPERARI]:
            if fara_timp():
                amanate += 1
                break
            print(f" ← ediția {eid}")
            ok, n = culege(db, str(eid), "")
            noi += n
            if ok:
                db["editii_vazute"].append(str(eid))
                esuate.pop(str(eid), None)
            else:
                esuate[str(eid)] = esuate.get(str(eid), 0) + 1
                if esuate[str(eid)] >= MAX_INCERCARI:
                    print(f"   ediția {eid} nu răspunde de {MAX_INCERCARI} ori — "
                          f"o consider inexistentă și nu o mai cer")
            time.sleep(1)
        db["editii_vazute"] = sorted(set(db["editii_vazute"]),
                                     key=lambda x: int(x) if x.isdigit() else 0)

    db["ultima_rulare"] = acum().strftime("%d.%m.%Y %H:%M")

    # Golurile rămase se calculează ÎNAINTE de salvare. Erau calculate după, așa
    # că valoarea proaspătă nu ajungea niciodată în fișier: date.json păstra o
    # listă goală, iar pagina nu avea ce afișa. Ediția 3333 lipsea din registru
    # de zile întregi fără ca nimic s-o semnaleze.
    ramase = goluri(db)
    db["editii_lipsa"] = [str(x) for x in ramase]
    renuntate = [k for k, v in db.get("editii_esuate", {}).items() if v >= MAX_INCERCARI]
    if renuntate:
        print(f"{len(renuntate)} ediții inaccesibile, verificate de "
              f"{MAX_INCERCARI} ori: " + ", ".join(sorted(renuntate)))
    spune_schimbari(reclasifica(db))
    save(db)

    total = len(db["acte"])
    if noi:
        print(f"\n{noi} acte noi. Total în registru: {total}.")
    else:
        print(f"\nNimic nou. Total în registru: {total}.")
    if amanate:
        print(f"Site-ul a răspuns greu: după {BUGET_SECUNDE // 60} minute m-am oprit din citit, "
              "ca rularea să apuce să salveze. Restul edițiilor se citesc la rularea următoare.")
    if esecuri:
        print("Ediții nedescărcate (se reiau la rularea următoare): " + ", ".join(esecuri))
    if ramase:
        print(f"Încă {len(ramase)} ediții lipsă din șir, cele mai noi: " +
              ", ".join(str(x) for x in sorted(ramase, reverse=True)[:12]) +
              ("…" if len(ramase) > 12 else "") +
              "\n  Se recuperează câte " + str(MAX_RECUPERARI) + " la fiecare rulare.")
    print("Pagina acorduri.html citește date.json direct — nu e nimic de regenerat.")

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
