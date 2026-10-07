#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Teste pentru colectorul Monitorului Oficial.

Rulează înaintea colectării, în workflow. Dacă pică, colectarea nici nu
pornește — mai bine o rulare oprită decât un registru stricat.

    python3 teste.py

De ce există fișierul ăsta. Pe 7 septembrie automatizarea a picat cu
`NameError: name 'titlu' is not defined`: la adăugarea marcajului de suport
bugetar scrisesem numele unei variabile greșit. Python nu semnalează asta decât
când linia chiar e atinsă, iar verificările de atunci apelau direct funcțiile de
clasificare, fără să treacă prin parse_edition. Linia stricată era pe o cale pe
care n-o atingea nimic. A stat picată zile întregi.

Testele de aici trec prin căile reale: parse_edition pe un cuprins întreg,
main() pe o pagină simulată, recuperarea golurilor. Nu verifică doar că
funcțiile dau răspunsul bun, ci că lanțul se execută cap-coadă.
"""

import io
import json
import os
import sys
import tempfile
import contextlib

import monitor_watch as mw

ESECURI = []
GET_ADEVARAT = mw.get      # testele de mai jos înlocuiesc mw.get; aici rămâne cel adevărat


def verifica(nume, conditie, detaliu=""):
    if not conditie:
        ESECURI.append(nume + (": " + str(detaliu) if detaliu else ""))


def egal(nume, obtinut, asteptat):
    verifica(nume, obtinut == asteptat, f"am primit {obtinut!r}, așteptam {asteptat!r}")


# --------------------------------------------------------------- clasificare

def test_clasificare():
    cazuri = [
        ("Împrumut", "Lege pentru ratificarea Acordului de împrumut dintre Republica "
                     "Moldova și Banca Europeană pentru Reconstrucție și Dezvoltare"),
        ("Împrumut", "Hotărâre cu privire la aprobarea semnării Acordului de facilitate "
                     "de credit dintre Republica Moldova și Agenția Franceză de Dezvoltare"),
        ("Grant", "Hotărâre cu privire la aprobarea semnării Acordului de grant cu Swedfund"),
        ("Asistență tehnică", "Ordin cu privire la semnarea și intrarea în vigoare a Acordului "
                              "de Asistență Tehnică încheiat între Programul Alimentar Mondial "
                              "(PAM) și Ministerul Muncii și Protecției Sociale"),
        ("Asistență tehnică", "Ordin privind intrarea în vigoare a Acordului de colaborare dintre "
                              "Organizația pentru Dezvoltarea Antreprenoriatului și Programul "
                              "Națiunilor Unite pentru Dezvoltare pentru implementarea proiectului"),
        # deduse din finanțator, când titlul spune doar „finanțare"
        ("Împrumut", "Lege pentru ratificarea Acordului de finanțare dintre Republica Moldova "
                     "și Asociația Internațională pentru Dezvoltare"),
        ("Grant", "Hotărâre cu privire la aprobarea Acordului de finanțare dintre Republica "
                  "Moldova și Comisia Europeană pentru Programul URBACT IV"),
    ]
    for asteptat, titlu in cazuri:
        egal("clasificare: " + titlu[:48], mw.classify(titlu), asteptat)


def test_neclasificate():
    """Ce NU trebuie să intre în registru."""
    capcane = [
        "Hotărâre cu privire la aprobarea Acordului de colaborare dintre Ministerul "
        "Apărării și Academia Militară privind instruirea ofițerilor",
        "Lege pentru ratificarea Acordului dintre Republica Moldova și Republica "
        "Italiană în domeniul securității sociale",
        "Ordin cu privire la aprobarea Regulamentului privind acordarea serviciilor "
        "de consultanță agricolă",
        "Hotărâre pentru modificarea anexei nr. 1 la Hotărârea Guvernului nr. 246/2010 "
        "cu privire la modul de aplicare a facilităților fiscale și vamale aferente "
        "realizării proiectelor de asistență tehnică",
        "Decizie de inadmisibilitate a sesizării privind excepția de neconstituționalitate",
        "Hotărâre cu privire la aprobarea Raportului auditului conformității",
        "Chişinău, 20 martie 2024. Aprobat prin Hotărârea Guvernului nr. 215/2024 AVIZ "
        "la proiectul de lege pentru modificarea Legii bugetului de stat",
    ]
    for titlu in capcane:
        cat = mw.classify(titlu)
        verifica("nu trebuie clasificat: " + titlu[:44], cat is None, f"a primit {cat!r}")


def test_parteneri():
    cazuri = [
        ("BERD", "Acordul de împrumut cu Banca Europeană pentru Reconstrucție și Dezvoltare"),
        # forma greșită, cu plural, apare în titlurile oficiale
        ("BERD", "Acordul de grant cu Banca Europeană pentru Reconstrucții și Dezvoltare"),
        ("CEB", "Acord-cadru de împrumut cu Banca de Dezvoltare a Consiliului Europei"),
        ("CEB", "Acord de împrumut cu CEB pentru spitalul regional"),
        ("Polonia", "Acord de împrumut cu Bank Gospodarstwa Krajowego"),
        ("PAM", "Acord de Asistență Tehnică cu Programul Alimentar Mondial"),
        ("Elveția", "Acord de înțelegere cu Agenția Elvețiană pentru Dezvoltare și Cooperare"),
        ("Consiliul Europei", "Convenție cu Consiliul Europei privind drepturile omului"),
    ]
    for asteptat, titlu in cazuri:
        egal("partener: " + titlu[:44], mw.partner(titlu), asteptat)


def test_suport_bugetar():
    egal("suport bugetar: facilitatea de reformă",
         mw.e_suport_bugetar("Acordul de împrumut privind Facilitatea de reformă și creștere"), True)
    egal("suport bugetar: contract de performanță",
         mw.e_suport_bugetar("Acord de finanțare privind Contractul de performanță "
                             "pentru reforma sectorială"), True)
    egal("suport bugetar: împrumut obișnuit",
         mw.e_suport_bugetar("Acordul de împrumut cu BERD pentru drumuri"), False)
    # marcajul nu schimbă categoria: instrumentul rămâne instrument
    egal("instrumentul bate canalul de livrare",
         mw.classify("Lege pentru ratificarea Acordului de împrumut privind "
                     "Facilitatea de reformă și creștere"), "Împrumut")


# ------------------------------------------------------- lanțul de colectare

# Fiecare act pe un singur rând: colectorul citește pagina linie cu linie, iar
# o intrare ruptă în două nu se mai potrivește cu tiparul. E chiar felul în care
# arată cuprinsul pe site.
CUPRINS = (
    "<html><body>"
    "<p>741. Lege pentru ratificarea Acordului de împrumut dintre Republica Moldova și "
    "Banca Europeană pentru Reconstrucție și Dezvoltare privind proiectul de test, "
    "semnat la Chișinău la 27 iunie 2023 (nr. 188, 24 august 2026)</p>"
    "<p>742. Hotărâre cu privire la aprobarea semnării Acordului de grant privind "
    "Facilitatea de reformă și creștere (nr. 500, 20 august 2026)</p>"
    "<p>743. Hotărâre cu privire la aprobarea Regulamentului de organizare internă "
    "a unei instituții publice oarecare (nr. 501, 20 august 2026)</p>"
    "</body></html>"
)


def test_parse_edition():
    """Calea pe care a picat automatizarea în septembrie."""
    mw.get = lambda u, tries=3: CUPRINS
    ok, acte = mw.parse_edition("3400", "Monitorul Oficial Nr. 1-2 din 25.08.2026")
    verifica("parse_edition reușește", ok)
    egal("parse_edition: câte acte", len(acte), 2)
    if len(acte) == 2:
        egal("primul act: categorie", acte[0]["categorie"], "Împrumut")
        egal("primul act: partener", acte[0]["partener"], "BERD")
        egal("primul act: data semnării", acte[0]["semnat"], "27.06.2023")
        verifica("fiecare act are câmpul suport",
                 all("suport" in a for a in acte))
        egal("al doilea act: marcaj suport bugetar", acte[1]["suport"], True)
        verifica("actele au ediția și data",
                 all(a["editie"] and a["data_editie"] for a in acte))


def test_parse_edition_esec():
    """O eroare de rețea nu trebuie confundată cu o ediție fără acte."""
    mw.get = lambda u, tries=3: None
    ok, acte = mw.parse_edition("3401", "")
    verifica("ediția nedescărcată e marcată ca eșec", ok is False)
    egal("ediția nedescărcată nu produce acte", acte, [])


def test_rulare_completa():
    """main() cap-coadă, pe un registru temporar."""
    acasa = "<html><body><a href='/ro/monitor/3400'>" \
            "Monitorul Oficial Nr. 1-2 din 25.08.2026</a></body></html>"
    mw.get = lambda u, tries=3: acasa if u.endswith("/ro") else CUPRINS
    mw.time.sleep = lambda s: None

    with tempfile.TemporaryDirectory() as folder:
        vechi_data = mw.DATA
        mw.DATA = os.path.join(folder, "date.json")
        try:
            with contextlib.redirect_stdout(io.StringIO()):
                mw.main()
            db = json.load(open(mw.DATA, encoding="utf-8"))
        finally:
            mw.DATA = vechi_data

    egal("rulare completă: acte colectate", len(db["acte"]), 2)
    verifica("ediția e marcată ca văzută", "3400" in db["editii_vazute"])
    verifica("ultima rulare e completată", bool(db.get("ultima_rulare")))
    verifica("câmpul editii_lipsa e salvat", "editii_lipsa" in db)


def test_goluri():
    db = {"editii_vazute": ["3310", "3311", "3313", "3314"], "editii_esuate": {}}
    egal("golurile se detectează", mw.goluri(db), [3312])

    db = {"editii_vazute": ["3310", "3311", "3313"],
          "editii_esuate": {"3312": mw.MAX_INCERCARI}}
    egal("ediția inaccesibilă nu mai e raportată", mw.goluri(db), [])

    db = {"editii_vazute": ["3310", "3311", "3312"], "editii_esuate": {}}
    egal("șir continuu, niciun gol", mw.goluri(db), [])


def test_data_semnarii():
    egal("data semnării: formă lungă",
         mw.signed_on("Acord semnat la Chișinău la 27 iunie 2023"), "27.06.2023")
    egal("data semnării: absentă",
         mw.signed_on("Acord de împrumut fără dată"), "")


# ------------------------------------------- același număr, emitenți diferiți

def test_acte_cu_acelasi_numar():
    """Hotărârea nr. 10 și ordinul nr. 10 din aceeași zi sunt două acte, nu unul."""
    cuprins = (
        "<html><body>"
        "<p>10. Hotărâre cu privire la aprobarea semnării Acordului de grant dintre Guvernul "
        "Republicii Moldova și Guvernul Japoniei (nr. 10, 18 ianuarie 2026)</p>"
        "<p>11. Ordin cu privire la intrarea în vigoare a Contractului de asistență tehnică dintre "
        "Ministerul Finanțelor și Agenția Franceză de Dezvoltare (nr. 10, 18 ianuarie 2026)</p>"
        "</body></html>")
    mw.get = lambda u, tries=3: cuprins
    eticheta = "Monitorul Oficial Nr. 9-10 din 20.01.2026"

    db = {"acte": {}, "editii_vazute": []}
    with contextlib.redirect_stdout(io.StringIO()):
        ok, noi = mw.culege(db, "3500", eticheta)
    verifica("ediția cu două acte nr. 10 se citește", ok)
    egal("ambele acte nr. 10 sunt noi", noi, 2)
    egal("ambele acte nr. 10 rămân în registru", len(db["acte"]), 2)
    egal("fiecare cu tipul lui",
         sorted(mw.tip_act(a) for a in db["acte"].values()), ["hota", "ordi"])
    verifica("primul act păstrează cheia obișnuită, număr|ediție",
             "nr. 10, 18 ianuarie 2026|3500" in db["acte"])

    with contextlib.redirect_stdout(io.StringIO()):
        ok, noi = mw.culege(db, "3500", eticheta)
    egal("a doua citire nu adaugă nimic", noi, 0)
    egal("a doua citire nu pierde și nu dublează", len(db["acte"]), 2)

    # Actul venit întâi din PDF e înlocuit de versiunea de pe site, nu dublat.
    db = {"acte": {"nr. 10, 18 ianuarie 2026|pdf-9-10": {
        "act": "nr. 10, 18 ianuarie 2026", "editie_id": "pdf-9-10", "sursa": "PDF",
        "titlu": "Hotărâre cu privire la aprobarea semnării Acordului de grant dintre Guvernul "
                 "Republicii Moldova și Guvernul Japoniei"}}, "editii_vazute": []}
    with contextlib.redirect_stdout(io.StringIO()):
        mw.culege(db, "3500", eticheta)
    egal("versiunea din PDF nu se dublează", len(db["acte"]), 2)
    verifica("versiunea de pe site o înlocuiește pe cea din PDF",
             "nr. 10, 18 ianuarie 2026|pdf-9-10" not in db["acte"]
             and "nr. 10, 18 ianuarie 2026|3500" in db["acte"])


# ---------------------------------------------------------- rețea și timp

def test_404_fara_reincercari():
    """O pagină care nu există nu se cere de trei ori; o pană de server, da."""
    apeluri = []

    def fals(cod):
        def cere(url, headers=None, timeout=None):
            apeluri.append(url)
            e = mw.requests.HTTPError(str(cod))
            e.response = type("R", (), {"status_code": cod})()
            raise e
        return cere

    vechi_get, vechi_sleep = mw.requests.get, mw.time.sleep
    mw.time.sleep = lambda s: None
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            mw.requests.get = fals(404)
            rez = GET_ADEVARAT("https://exemplu.test/ro/monitor/1")
            egal("404: fără rezultat", rez, None)
            egal("404: o singură cerere", len(apeluri), 1)
            del apeluri[:]
            mw.requests.get = fals(500)
            GET_ADEVARAT("https://exemplu.test/ro/monitor/2")
            egal("500: se reîncearcă", len(apeluri), 3)
    finally:
        mw.requests.get, mw.time.sleep = vechi_get, vechi_sleep


def test_buget_de_timp():
    """Când timpul s-a terminat, rularea se oprește singură și salvează registrul."""
    acasa = ("<html><body><a href='/ro/monitor/3400'>Monitorul Oficial Nr. 1-2 din 25.08.2026</a>"
             "<a href='/ro/monitor/3401'>Monitorul Oficial Nr. 3-4 din 26.08.2026</a></body></html>")
    mw.get = lambda u, tries=3: acasa if u.endswith("/ro") else CUPRINS
    mw.time.sleep = lambda s: None
    iesire = io.StringIO()
    with tempfile.TemporaryDirectory() as folder:
        vechi_data, vechi_buget = mw.DATA, mw.BUGET_SECUNDE
        mw.DATA = os.path.join(folder, "date.json")
        mw.BUGET_SECUNDE = -1                      # bugetul e deja depășit
        try:
            with contextlib.redirect_stdout(iesire):
                mw.main()
            db = json.load(open(mw.DATA, encoding="utf-8"))
        finally:
            mw.DATA, mw.BUGET_SECUNDE = vechi_data, vechi_buget
    egal("buget depășit: nicio ediție citită", len(db["acte"]), 0)
    egal("buget depășit: edițiile nu sunt marcate ca văzute", db["editii_vazute"], [])
    verifica("buget depășit: registrul e totuși salvat", bool(db.get("ultima_rulare")))
    verifica("buget depășit: mesajul spune ce s-a întâmplat", "m-am oprit din citit" in iesire.getvalue())


# ------------------------------------------------------------------ pornire

def main():
    teste = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for t in teste:
        try:
            t()
        except Exception as e:                       # noqa: BLE001
            ESECURI.append(f"{t.__name__} a aruncat {type(e).__name__}: {e}")

    if ESECURI:
        print(f"{len(ESECURI)} teste au picat:\n")
        for e in ESECURI:
            print("  ✗ " + e)
        return 1

    print(f"Toate testele au trecut ({len(teste)} grupuri).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
