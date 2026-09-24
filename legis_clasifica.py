"""Clasificator extins pentru actele extrase din legis.md.

Pornește de la monitor_watch.classify() și acoperă golurile găsite la
compararea cu legis.md: acord-cadru, acord de facilitate, înțelegeri prin
schimb de note, memorandumuri cu agenții de dezvoltare, Canada ca partener.
"""
import re, sys
sys.path.insert(0, str(__import__('pathlib').Path(__file__).resolve().parent))
import monitor_watch as mw

norm = mw.norm

# Parteneri în plus față de monitor_watch.PARTNERS
PARTENERI_EXTRA = [
    (r"banca (?:pentru|de) dezvoltare a consiliului europei|fondul de dezvoltare sociala al consiliului europei", "CEB"),
    (r"banca (?:de )?export-import a (?:japoniei|chinei|coreei)|\bjbic\b", "Japonia (JBIC)"),
    (r"commerzbank|unicredit|raiffeisen|deutsche bank|\bing bank", "Bancă comercială străină"),
    (r"regele de drept al canadei|guvernul canadei|\bcanadei\b", "Canada"),
    (r"agentia ceha pentru dezvoltare|republicii cehe", "Cehia"),
    (r"\bseco\b|secretariatul de stat elvetian", "Elveția"),
    (r"agentia austriaca pentru dezvoltare|\bada\b|guvernul austriei", "Austria"),
    (r"guvernul (?:regatului )?olandei|tarilor de jos", "Olanda"),
    (r"guvernul (?:republicii )?italiene|guvernul italiei", "Italia"),
    (r"guvernul (?:republicii )?franceze|guvernul frantei", "Franța"),
    (r"guvernul (?:republicii )?coreea|\bkoica\b", "Coreea"),
    (r"guvernul (?:republicii populare )?chineze|guvernul chinei", "China"),
    (r"guvernul (?:statului )?kuweit|fondul kuweitian", "Kuweit"),
    (r"fondul opec|\bofid\b", "OFID"),
    (r"banca de comert si dezvoltare a marii negre|\bbstdb\b", "BSTDB"),
    (r"corporatia financiara internationala|\bifc\b", "IFC"),
    (r"corporatia provocarile mileniului|provocarile mileniului", "SUA (MCC)"),
    (r"fondul global", "Fondul Global"),
    (r"\bdfid\b|regatului unit|marii britanii", "Regatul Unit"),
    (r"guvernul (?:regatului )?(?:danemarcei|norvegiei)", "Nordici"),
    (r"guvernul (?:republicii )?(?:ungare|ungariei)", "Ungaria"),
    (r"guvernul (?:republicii )?(?:estone|lituaniei|letoniei)", "Baltici"),
    (r"guvernul (?:statelor unite|sua)", "SUA"),
    (r"guvernul federatiei ruse|federatia rusa", "Rusia"),
    (r"guvernul (?:republicii )?turcia|\btika\b", "Turcia"),
    (r"fondul nordic de dezvoltare|\bndf\b|nefco", "Nordici"),
    (r"agentia de dezvoltare internationala a statelor unite", "SUA"),
]

# Denumiri vechi sau diferite de cele din Monitor, găsite în titlurile legis.md.
# Servesc la AFIȘAREA partenerului. La includerea memorandumurilor de cooperare
# nu contează — altfel intrau memorandumuri de colaborare între instituții
# (combaterea corupției, sport, educație), care nu sunt asistență externă.
PARTENERI_NUME = [
    (r"asociatia internationala de dezvoltare|agentia internationala pentru dezvoltare(?!\s+a\s+statelor)", "AID"),
    (r"fondul international pentru dezvoltare\s*a?\s*(?:agricol|agriculturii)|\bifad\b", "FIDA"),
    (r"banca europeana pentru investitii", "BEI"),
    (r"banca\W+internationala\s+(?:pentru|de)\s+reconstructi", "BIRD"),
    (r"banca europeana pentru\s*reconstructi", "BERD"),
    (r"comisia comunitatilor europene|comunitatea (?:economica )?europeana|uniunea\s*eu\s*ropeana|\benpi\b|politicii sectoriale de sanatate", "UE"),
    (r"republicii polon[ea]\b|guvernul republicii polonia", "Polonia"),
    # „între Republica Moldova și România" apare și în numele proiectelor de interconectare
    # BERD — acolo România nu e partener; o luăm doar din acordul de asistență rambursabilă
    (r"guvernul rom[ai]niei|rambursabil\w*\s+(?:intre|dintre)\s+republica moldova\s+si\s+romania", "România"),
    (r"republicii bulgaria", "Bulgaria"),
    (r"federatiei ruse", "Rusia"),
    (r"kazahstan", "Kazahstan"),
    (r"republicii populare chineze|\bicbc\b|comerciala din china|citic bank|bank of communication|medicina traditionala chineza", "China"),
    (r"fondul dezvoltarii economice arabe din kuwait|\bkuwait\b", "Kuweit"),
    (r"export credit bank", "Turcia"),
    (r"hewlett-packard", "Hewlett-Packard"),
    (r"siemens|simens", "Siemens (Germania)"),
    (r"dre[sz]dner bank|banca \W?aka\W", "Bancă comercială străină"),
    (r"\bfao\b|organizatia natiunilor unite pentru agricultura", "FAO"),
    (r"societatea germana pentru cooperare internationala|deutsche gesellschaft", "GIZ"),
    (r"ajutorul umanitar primit din strainatate", "CSI"),
]

INCLUDE_EXTRA = [
    (r"acord\w*-cadru\s+de\s+imprumut", "Împrumut"),
    (r"acord\w*-cadru\s+de\s+finantare", "Asistență financiară"),
    (r"acord\w*\s+de\s+facilitate\s+de\s+imprumut", "Împrumut"),
    (r"facilitate\s+de\s+imprumut", "Împrumut"),
    (r"acord\w*\s+de\s+facilitate\b", "Asistență financiară"),
    (r"mecanismului\s+de\s+reforma\s+si\s+crestere", "Asistență financiară"),
    (r"schimb\s+de\s+note.{0,200}(?:cooperar\w*\s+financiar|cooperar\w*\s+tehnic|finantar|grant|asistent)", "Asistență financiară"),
    (r"cooperar\w*\s+financiar\w*\s+pentru\s+finantare", "Asistență financiară"),
    (r"cooperar\w*\s+tehnic\w*\s+pentru\s+finantare", "Asistență tehnică"),
    (r"acord\w*\s+de\s+cooperare\s+tehnica\s+si\s+financiara", "Asistență financiară"),
    (r"acord\w*\s+de\s+garantare", "Împrumut"),
    (r"acord\w*\s+de\s+recreditare|acord\w*\s+de\s+imprumut\s+subsidiar", "Împrumut"),
    (r"acord\w*\s+de\s+donati", "Grant"),
    (r"acord\w*\s+privind\s+(?:acordarea\s+)?(?:granturilor|asistentei|ajutorului)", "Asistență financiară"),
    (r"acord\w*.{0,120}ajutor\w*\s+(?:umanitar|nerambursabil)", "Grant"),
    (r"asistent\w*\s+tehnic\w*", "Asistență tehnică"),
    (r"asistent\w*\s+(?:nerambursabil\w*|financiar\w*)", "Asistență financiară"),
]

# Memorandumuri/acorduri de proiect: intră doar cu partener extern recunoscut
INCLUDE_CU_PARTENER = [
    # formulări vechi: „Acordul dintre Guvernul RM și AID privind finanțarea
    # Proiectului…", „Acordul de asistență cu Guvernul SUA", „Acord de avans",
    # „Acord de restructurare a împrumutului", schimb de scrisori cu Japonia.
    (r"(?:acord|memorand|intelege|schimb\s+de\s+(?:note|scrisori)|protocol)\w*.{0,300}"
     r"(?:finantar|imprumut|credit|grant|avans|asistent\w*\s+(?:umanitar|tehnic|financiar)|donati|suport\w*\s+al\s+proiect|proiect)",
     "Asistență financiară"),
    (r"acord\w*\s+de\s+asistenta\b(?!\s+(?:juridic|reciproc|administrativ))", "Asistență financiară"),
    (r"memorandum\w*\s+de\s+intelegere.{0,250}(?:proiect|dezvoltare|cooperare)", "Asistență tehnică"),
    (r"acord\w*.{0,200}(?:implementare|realizare)a?\s+proiect", "Asistență tehnică"),
]

EXCLUDE_EXTRA = [
    r"deschiderea\s+conturilor|instituirea\s+.{0,40}sectiei|crearea\s+unitatii",
    r"rezultatele\s+(?:controlului|auditului)",
    r"ministerul\s+apararii|militar|armat",
    r"asistent\w*\s+(?:juridic|reciproc|administrativ|vamal)",
    r"ajutor\w*\s+reciproc|colaborarea\s+si\s+ajutorul",
    r"privilegi\w*\s+si\s+imunitat",
    r"\btva\b|accize|taxa\s+pe\s+valoarea",
    r"componentei|instituirea\s+(?:comisiei|grupului|consiliului)",
    r"^(?:cu\s+privire\s+la|privind)\s+acordarea\s+(?:unui\s+)?(?:ajutor|credit)",
    r"acordarea\s+ajutorului\s+umanitar\s+(?:populatiei|republicii|ucrainei|poporului)",
    r"concurent\w*\s+electoral",
    r"asociati\w*\s+de\s+economii\s+si\s+imprumut",
    r"licent\w*",
    r"credit\w*\s+(?:ipotecar|de\s+consum|bancar)",
    r"imprumut\w*\s+(?:din\s+)?(?:fondul\s+de\s+rezerva|intern|de\s+stat\s+pentru)",
    r"valori\w*\s+mobiliare\s+de\s+stat",
    r"statutul\s+organizatiei",
    r"aderarea\s+republicii\s+moldova\s+la\s+uniunea\s+europeana",
    r"participarea\s+republicii\s+moldova\s+la\s+program",
    r"comitet\w*\s+(?:mixt|de\s+asociere)",
    r"consiliul\w*\s+de\s+asociere",
    r"spatiul\s+aerian",
    r"transportul\s+rutier",
    r"evitarea\s+dublei\s+impuneri",
    r"promovarea\s+si\s+protejarea\s+(?:reciproca\s+)?a\s+investitiilor",
    r"readmisie",
    r"securitat\w*\s+sociala",
    # cooperare între instituții de combatere a corupției / spălării banilor
    r"combaterea\s+crimelor\s+economice|spalarii\s+banilor|finantarii\s+terorismului",
]


# Sprijin intern (fermieri, cooperative) — exclus doar când titlul nu e un acord.
# „Acordul de grant cu Japonia privind asigurarea fermierilor cu fertilizanți"
# e asistență externă, chiar dacă vorbește de fermieri.
EXCLUDE_INTERN = [r"fermier|producator\w*\s+agricol", r"cooperativ"]
E_ACORD = r"acord|memorand|intelege|schimb\s+de\s+(?:note|scrisori)"

# Un act intră în registru doar dacă e despre un document încheiat cu un
# partener: acord, memorandum, înțelegere, protocol, contract, convenție,
# schimb de note/scrisori — sau numește direct împrumutul/grantul/creditul.
# Fără asta intrau acte care doar pomenesc „asistența tehnică": modificările
# HG 246/2010, programele naționale de asistență tehnică, comunicate fiscale,
# regulamentele SFS pentru „centrele de asistență tehnică" ale caselor de marcat.
# „acordarea/acordat" nu contează — nu sunt acorduri.
DOCUMENT_ACORD = (r"\bacord(?!a|at|and|in)|memorand|intelegeri|\bcontract(?!elor\s+de\s+stat)|protocol|"
                  r"schimb\w*\s+de\s+(?:note|scrisori)|conventi|scrisor|amendament|aranjament|"
                  r"\bimprumut|\bgrant|\bcredit|finantar|tratat\w*\s+(?:de|privind|dintre|intre)")

# Acte de cadru (reguli generale, nu acorduri), chiar dacă titlul lor pomenește
# tratate sau contracte de stat.
EXCLUDE_CADRU = [
    r"246/2010|facilitat\w*\s+fiscale\s+si\s+vamale\s+aferente",       # HG 246/2010 și modificările ei
    r"facilitat\w*\s+prevazute\s+la\s+importul\s+marfurilor",
    r"centr\w*\s+de\s+asistenta\s+tehnica\s+pentru\s+masinile\s+de\s+casa",
    r"programul\w*\s+(?:national\w*\s+)?(?:de\s+|al\s+)?asistent\w*\s+tehnic\w*\s+pentru\s+anii",
    r"oficiul\w*\s+de\s+gestionare\s+a\s+programelor",
    r"managementul\s+asistentei\s+financiare",
    r"organizarea\s+si\s+functionarea",
    r"credit\w*\s+pentru\s+consumatori",
    r"contractelor\s+de\s+creditare\s+si\s+de\s+sprijin",
    r"asistentei\s+medicale\s+cetatenilor",
    r"dreptului\s+de\s+sedere",
]


def partener(title, doar_baza=False):
    p = [x for x in (mw.partner(title) or '').split(' / ') if x]
    if re.search(r"banca (?:pentru|de) dezvoltare a consiliului europei", norm(title)) and "Consiliul Europei" in p:
        p.remove("Consiliul Europei")
    n = norm(title)
    for pat, name in PARTENERI_EXTRA + ([] if doar_baza else PARTENERI_NUME):
        if re.search(pat, n) and name not in p:
            p.append(name)
    return ' / '.join(p)


def clasifica(title):
    n = norm(title)
    if any(re.search(norm(x), n) for x in mw.EXCLUDE) or any(re.search(x, n) for x in EXCLUDE_EXTRA):
        return None
    if not re.search(E_ACORD, n) and any(re.search(x, n) for x in EXCLUDE_INTERN):
        return None
    if not re.search(DOCUMENT_ACORD, n) or any(re.search(x, n) for x in EXCLUDE_CADRU):
        return None
    cat = _categorie(title, n)
    if cat and cat != "Împrumut" and re.search(IMPRUMUT, n) and not re.search(r"acord\w*\s+de\s+grant", n):
        return "Împrumut"
    return cat


# Împrumutul/creditul numit în titlu bate clasificarea după partener: „Acordul
# cu Guvernul României referitor la împrumut" e împrumut, deși România e donator.
IMPRUMUT = r"(?:acord|contract|conventi)\w*[- ]*(?:cadru\s+)?de\s+(?:imprumut|credit)|\bimprumut\w*\b|\bcredit(?:ul|ului|e|ele)?\b"


def _categorie(title, n):
    c = mw.classify(title)
    if c:
        return c
    hits = [cat for pat, cat in INCLUDE_EXTRA if re.search(pat, n)]
    if not hits and partener(title):
        hits = [cat for pat, cat in INCLUDE_CU_PARTENER if re.search(pat, n)]
        # memorandumurile de cooperare intră doar cu un partener de asistență cunoscut
        if hits and not partener(title, doar_baza=True) and not re.search(
                r"\bimprumut|\bcredit|\bgrant|finantar|asistent\w*\s+(?:financiar|tehnic|umanitar)|\bavans|restructurare", n):
            hits = []
    if not hits:
        return None
    for pref in ("Împrumut", "Grant", "Asistență tehnică", "Asistență financiară"):
        if pref in hits:
            if pref == "Asistență financiară":
                parti = [x for x in partener(title).split(' / ') if x]
                if parti and all(x in mw.CREDITORI or x in ("Canada", "OFID", "BSTDB", "IFC", "Kuweit", "CEB", "Japonia (JBIC)", "Bancă comercială străină") for x in parti):
                    return "Împrumut"
                if parti and all(x in mw.DONATORI or x in ("Cehia", "Austria", "Olanda", "Coreea", "SUA (MCC)", "Fondul Global", "Regatul Unit", "Nordici", "Baltici") for x in parti):
                    return "Grant"
            return pref
    return hits[0]


# Tipul actului după prefixul codului legis
TIPURI = [
    (r"^LP", "Lege"), (r"^HP", "Hotărâre a Parlamentului"),
    (r"^DPRM|^DP", "Decret prezidențial"), (r"^HG", "Hotărâre de Guvern"),
    (r"^DG", "Dispoziție a Guvernului"), (r"^OG", "Ordonanță"),
    (r"^TR|^AI|^CV", "Tratat internațional"),
    (r"^OM|^O[A-Z]", "Ordin"), (r"^HBN", "Hotărâre BNM"),
]


def tip(cod):
    for pat, name in TIPURI:
        if re.search(pat, cod):
            return name
    return "Alt act"


def etapa(title):
    n = norm(title)
    if re.search(r"promulgar", n): return "Promulgare"
    if re.search(r"^(?:pentru|privind)\s+ratificar|^cu privire la ratificar", n): return "Ratificare (lege)"
    if re.search(r"proiectului\s+de\s+lege.{0,40}ratific", n): return "Proiect de lege de ratificare"
    if re.search(r"negocier", n) and re.search(r"semnar", n): return "Negociere și semnare"
    if re.search(r"negocier", n): return "Negociere"
    if re.search(r"semnar", n): return "Semnare"
    if re.search(r"aprobar", n): return "Aprobare"
    if re.search(r"intrar\w*\s+in\s+vigoare", n): return "Intrare în vigoare"
    if re.search(r"modific|complet", n): return "Modificare"
    return "Altă etapă"
