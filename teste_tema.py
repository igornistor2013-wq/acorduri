"""Testele aspectului comun al site-ului (tema.css, fonturile din fonturi/, bara de navigare din meniu.js).

    python teste_tema.py             # fișierele: legătura spre tema.css în toate paginile, aceeași versiune (?v=), fonturile, licența,
                                     # nicio cerere externă, contrastul culorilor din temă
    python teste_tema.py --browser   # plus: pagina în browser — fonturile se încarcă, banda tricoloră, meniul (file, linia aurie, meniurile
                                     # derulante, RO/EN, căutarea), bara de execuție din KPI, harta sub KPI, fără scroll orizontal pe
                                     # desktop și telefon, fără cereri către servere de fonturi

Schimbarea aspectului nu are voie să schimbe funcțiile: aici se verifică doar legăturile, versiunile și forma; comportamentul îl acoperă
celelalte suite (teste.py, teste_debursari.py, teste_sectoare.py …), care trebuie să treacă neschimbate.
Are nevoie de (pentru --browser) Playwright.
"""
import functools, re, sys, threading
from pathlib import Path

AICI = Path(__file__).resolve().parent
picat = []


def verifica(nume, conditie, detaliu=''):
    print(('  ok   ' if conditie else '  PICĂ ') + nume + ('' if conditie else f'  → {str(detaliu)[:500]}'))
    if not conditie:
        picat.append(nume)


PAGINI = ['index.html', 'acorduri.html', 'legis_acorduri.html', 'hg246.html', 'despre.html', 'debursari.html', '404.html']
LEG = re.compile(r'<link rel="stylesheet" href="(/?)tema\.css\?v=(\d{4}-\d{2}-\d{2})">')

# ============================================================ legătura și versiunea
print('Legătura spre tema.css')
versiuni = set()
for f in PAGINI:
    s = (AICI / f).read_text(encoding='utf-8')
    m = LEG.findall(s)
    verifica(f'{f}: exact o legătură spre tema.css cu ?v=AAAA-LL-ZZ', len(m) == 1, m)
    if m:
        versiuni.add(m[0][1])
        # 404.html are <base href="/">, deci legătura absolută; celelalte pagini stau în rădăcină
        verifica(f'{f}: calea legăturii potrivită paginii', m[0][0] == ('/' if f == '404.html' else ''), m[0][0])
        # legătura vine DUPĂ ultimul <style> din <head> (altfel regulile paginii ar bate tema)
        cap = s[:s.index('</head>')]
        verifica(f'{f}: tema.css e legată după stilurile paginii', cap.rindex('</style>') < cap.index('tema.css'))
verifica('aceeași versiune (?v=) în toate paginile', len(versiuni) == 1, versiuni)

legis = (AICI / 'legis_pagina.py').read_text(encoding='utf-8')
verifica('legis_pagina.py construiește legis_acorduri.html din acorduri.html (moștenește legătura)', "SRC = AICI / 'acorduri.html'" in legis)

# ============================================================ foaia de stil, fonturile, licența
print('tema.css și fonturile')
css = (AICI / 'tema.css').read_text(encoding='utf-8')
verifica('tema.css nu cere nimic de pe alte servere (fără http, fără @import)', 'http' not in css.replace('http://scripts.sil.org', '') and '@import' not in css)
for fam, fis in (('Inter', 'fonturi/inter-var.woff2'), ('Newsreader', 'fonturi/newsreader-var.woff2')):
    verifica(f'@font-face {fam} → {fis}', f"font-family:'{fam}'" in css and f'url({fis})' in css)
    cale = AICI / fis
    verifica(f'{fis} există și e mic (< 120 KB)', cale.exists() and 0 < cale.stat().st_size < 120_000, cale.stat().st_size if cale.exists() else 0)
    verifica(f'{fis} e WOFF2', cale.exists() and cale.read_bytes()[:4] == b'wOF2')
    verifica(f'@font-face {fam}: font-display:swap (textul se vede imediat)', re.search(r"font-family:'%s'[^}]*font-display:swap" % fam, css) is not None)
lic = (AICI / 'fonturi' / 'LICENTA.txt')
verifica('fonturi/LICENTA.txt (SIL OFL 1.1, cu drepturile de autor)', lic.exists() and 'SIL OPEN FONT LICENSE Version 1.1' in lic.read_text(encoding='utf-8') and 'Inter Project Authors' in lic.read_text(encoding='utf-8') and 'Newsreader Project Authors' in lic.read_text(encoding='utf-8'))
verifica('meniu.js nu mai are butoane colorate pe categorii (file cu linie dedesubt)', 'mg-analize{background:linear-gradient' not in (AICI / 'meniu.js').read_text(encoding='utf-8'))
verifica('index.html nu mai are vechile reguli de buton colorat pe id-uri (#acorduriNavBtn{…gradient})', '#acorduriNavBtn, #hg246NavBtn{' not in (AICI / 'index.html').read_text(encoding='utf-8'))

# ============================================================ contrast
print('Contrastul culorilor din temă (WCAG)')
jet = dict(re.findall(r'--([a-z0-9-]+):\s*(#[0-9A-Fa-f]{6})', re.search(r':root\{(.*?)\n\}', css, re.S).group(1)))


def lum(h):
    h = h.lstrip('#'); c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    c = [x / 12.92 if x <= .03928 else ((x + .055) / 1.055) ** 2.4 for x in c]
    return .2126 * c[0] + .7152 * c[1] + .0722 * c[2]


def raport(a, b):
    la, lb = lum(a), lum(b)
    return (max(la, lb) + .05) / (min(la, lb) + .05)


for nume, fata, fundal, prag in [
    ('text principal pe alb', 'ink', 'bg', 7), ('text secundar (ink-2) pe alb', 'ink-2', 'bg', 7), ('text estompat (ink-dim) pe alb', 'ink-dim', 'bg', 4.5),
    ('text estompat pe panou-2', 'ink-dim', 'panel-2', 4.5), ('ink-2 pe panou-2', 'ink-2', 'panel-2', 4.5),
    ('aur-text pe alb', 'gold-ink', 'bg', 4.5), ('aur-text pe aur-fundal', 'gold-ink', 'gold-bg', 4.5),
    ('navy-deep pe blue-bg', 'navy-deep', 'blue-bg', 7), ('navy pe blue-bg', 'navy', 'blue-bg', 4.5),
    ('verde-text pe verde-fundal', 'green-ink', 'green-bg', 4.5), ('roșu pe roșu-fundal', 'red', 'red-bg', 4.5),
]:
    if fata in jet and fundal in jet:
        r = raport(jet[fata], jet[fundal])
        verifica(f'{nume}: {r:.1f}:1 (cel puțin {prag}:1)', r >= prag, f'{jet[fata]} pe {jet[fundal]}')
    else:
        verifica(f'{nume}: jetoanele --{fata}, --{fundal} există în tema.css', False)
for nume, fundal in (('alb pe navy-deep (tab activ, butoane)', 'navy-deep'), ('alb pe navy', 'navy')):
    r = raport('#FFFFFF', jet[fundal]); verifica(f'{nume}: {r:.1f}:1', r >= 7)
r = raport('#B87714', jet['bg']); verifica(f'auriul de accent (linii, bare) pe alb: {r:.1f}:1 — doar pentru elemente grafice (≥ 3:1)', r >= 3)

if '--browser' not in sys.argv:
    print('\n' + (f'{len(picat)} teste au picat: ' + '; '.join(picat) if picat else 'Toate testele temei au trecut.'))
    sys.exit(1 if picat else 0)

# ============================================================ browser
print('În browser')
sys.path.insert(0, str(AICI))
import legatura_acorduri as lga
from playwright.sync_api import sync_playwright

srv = lga._Server(('127.0.0.1', 0), functools.partial(lga._Liniste, directory=str(AICI)))
threading.Thread(target=srv.serve_forever, daemon=True).start()
BAZA = 'http://127.0.0.1:%d/' % srv.server_address[1]
EXT = []


def pagina(b, url, latime=1440, asteapta=3500):
    ctx = b.new_context(viewport={'width': latime, 'height': 900})

    def filtru(r):
        u = r.request.url
        if u.startswith(BAZA) or u.startswith('data:') or u.startswith('blob:'):
            return r.continue_()
        EXT.append(u); r.abort()
    ctx.route('**/*', filtru)
    pg = ctx.new_page(); errs = []
    pg.on('pageerror', lambda e: errs.append(str(e)[:150]))
    pg.goto(BAZA + url, wait_until='load', timeout=90000); pg.wait_for_timeout(asteapta)
    return ctx, pg, errs


with sync_playwright() as p:
    b = p.chromium.launch()
    ctx, pg, errs = pagina(b, 'index.html')
    verifica('index: fără erori de script', errs == [], errs)
    verifica('fontul Inter e încărcat', pg.evaluate("document.fonts.check('16px Inter') && [...document.fonts].some(f => f.family.replace(/['\"]/g,'') === 'Inter' && f.status === 'loaded')"))
    verifica('fontul Newsreader e încărcat', pg.evaluate("[...document.fonts].some(f => f.family.replace(/['\"]/g,'') === 'Newsreader' && f.status === 'loaded')"))
    verifica('textul paginii e Inter', pg.evaluate("getComputedStyle(document.body).fontFamily.startsWith('Inter')"))
    verifica('titlul h1 e Newsreader (serif)', pg.evaluate("getComputedStyle(document.querySelector('#mainView h1')).fontFamily.startsWith('Newsreader')"))
    verifica('cifrele mari din KPI sunt Newsreader', pg.evaluate("getComputedStyle(document.querySelector('.kpi .val')).fontFamily.startsWith('Newsreader')"))
    verifica('cifrele din tabele sunt tabulare (aliniere pe coloană)', pg.evaluate("getComputedStyle(document.querySelector('td.num')).fontVariantNumeric.includes('tabular-nums')"))
    bs = pg.evaluate("(() => { const c = getComputedStyle(document.body, '::before'); return [c.height, c.backgroundImage]; })()")
    verifica('banda tricoloră de 6 px deasupra paginii', bs[0] == '6px' and 'rgb(0, 70, 174)' in bs[1] and 'rgb(255, 210, 0)' in bs[1] and 'rgb(204, 9, 47)' in bs[1], bs)
    # meniul
    taburi = pg.evaluate("[...document.querySelectorAll('.mg-btns .mg-b')].map(e => e.innerText.trim())")
    verifica('meniul are cele șase file, în ordine', taburi == ['Donatori și proiecte', 'Analize avansate', 'Export', 'IATI', 'Acorduri', 'HG 246'], taburi)
    act = pg.evaluate("(() => { const e = document.querySelector('.mg-b.activ'); const c = getComputedStyle(e); return [e.innerText.trim(), c.borderBottomColor, c.borderBottomWidth, c.backgroundColor]; })()")
    verifica('fila activă: linie aurie de 3 px, fără fundal colorat', act[0] == 'Donatori și proiecte' and act[1] == 'rgb(184, 119, 20)' and act[2] == '3px' and act[3] == 'rgba(0, 0, 0, 0)', act)
    pg.click('#advancedAnalysisNavBtn'); pg.wait_for_timeout(600)
    verifica('clic pe „Analize avansate”: vederea se schimbă fără reîncărcare', pg.evaluate("getComputedStyle(document.getElementById('advancedView')).display !== 'none' && getComputedStyle(document.getElementById('mainView')).display === 'none'"))
    verifica('…iar fila activă urmează vederea', pg.evaluate("document.querySelector('.mg-b.activ').innerText.trim()") == 'Analize avansate')
    verifica('titlul vederii e serif', pg.evaluate("getComputedStyle(document.querySelector('#advancedView h1')).fontFamily.startsWith('Newsreader')"))
    pg.click('#mgAcasa'); pg.wait_for_timeout(400)
    pg.click('#acorduriNavBtn'); pg.wait_for_timeout(300)
    opt = pg.evaluate("[...document.querySelectorAll('#acorduriSelectorMenu .mg-opt')].map(e => e.querySelector('b').innerText.trim())")
    verifica('meniul „Acorduri” se deschide cu cele patru opțiuni', len(opt) == 4 and pg.evaluate("getComputedStyle(document.getElementById('acorduriSelectorMenu')).display") == 'block', opt)
    verifica('…și săgeata se rotește', pg.evaluate("getComputedStyle(document.querySelector('#acorduriNavBtn .mg-sag')).transform") != 'none')
    pg.keyboard.press('Escape'); pg.wait_for_timeout(200)
    verifica('Esc închide meniul derulant', pg.evaluate("getComputedStyle(document.getElementById('acorduriSelectorMenu')).display") == 'none')
    pg.click('#iatiSelectorBtn'); pg.wait_for_timeout(200)
    pg.click('#iatiSelectorOptDash'); pg.wait_for_timeout(600)
    verifica('IATI → Dashboard d-portal deschide vederea d-portal', pg.evaluate("getComputedStyle(document.getElementById('dportalView')).display !== 'none'"))
    pg.click('#mgAcasa'); pg.wait_for_timeout(400)
    # bara de execuție
    ex = pg.evaluate("""(() => { const i = document.querySelector('#kpiExecBar i'); const t = document.getElementById('kpiExecTxt').innerText;
      const num = s => parseInt(s.replace(/[^0-9]/g, ''), 10);
      const subs = [...document.querySelectorAll('#kpiRow .kpi .sub')].map(e => e.innerText);
      return { w: parseFloat(i.style.width), t, ang: num(subs[0]), deb: num(subs[1]) }; })()""")
    pct = round(ex['deb'] / ex['ang'] * 100)
    verifica('bara de execuție = debursat / angajat (rotunjit), cu text', ex['w'] == pct and ex['t'].startswith(str(pct) + '%'), ex)
    pg.click('#langSwitch button[data-lang=en]'); pg.wait_for_timeout(700)
    verifica('în engleză: textul barei de execuție e tradus', 'of commitments have been disbursed' in pg.inner_text('#kpiExecTxt'), pg.inner_text('#kpiExecTxt'))
    verifica('în engleză: filele meniului sunt traduse', pg.evaluate("document.querySelector('.mg-btns .mg-b').innerText.trim()") == 'Donors & projects')
    pg.click('#langSwitch button[data-lang=ro]'); pg.wait_for_timeout(500)
    # harta, mutată sub KPI
    ordine = pg.evaluate("""(() => { const m = document.getElementById('mapPanel'), g = document.querySelector('#mainView .grid'), k = document.getElementById('kpiRow');
      return { dupaKpi: !!(k.compareDocumentPosition(m) & Node.DOCUMENT_POSITION_FOLLOWING), inainteaFiltrelor: !!(m.compareDocumentPosition(g) & Node.DOCUMENT_POSITION_FOLLOWING),
               parti: ['mapSvg', 'mapList', 'mapMod', 'mapCard', 'mapProjTable', 'mapZoomIn'].every(i => !!m.querySelector('#' + i)) }; })()""")
    verifica('harta stă între KPI și filtre, cu toate părțile ei', ordine['dupaKpi'] and ordine['inainteaFiltrelor'] and ordine['parti'], ordine)
    pg.keyboard.press('Escape')
    pg.keyboard.press('/'); pg.wait_for_timeout(900)
    verifica('tasta / deschide căutarea pe site', pg.evaluate("!!window.Cautare && typeof window.Cautare.deschide === 'function'"))
    th = pg.evaluate("(() => { const t = document.querySelector('#tablePanel th'); const c = getComputedStyle(t); return [c.textTransform, c.borderBottomWidth, c.borderBottomColor]; })()")
    verifica('antetul de tabel: majuscule, linie navy de 2 px dedesubt', th == ['uppercase', '2px', 'rgb(31, 61, 110)'], th)
    # tipărire: bara dispare, nu rămân umbre
    pg.emulate_media(media='print'); pg.wait_for_timeout(200)
    verifica('la tipărire bara de navigare dispare', pg.evaluate("getComputedStyle(document.querySelector('.mg')).display") == 'none')
    pg.emulate_media(media='screen')
    ctx.close()

    # pe fiecare pagină: fără scroll orizontal, desktop și telefon, fără erori; legătura tema.css chiar se aplică
    for url in ['index.html', 'index.html#analize', 'index.html#export', 'index.html#iati', 'index.html#dportal', 'index.html#legaturi', 'acorduri.html',
                'legis_acorduri.html', 'hg246.html', 'despre.html', 'debursari.html', '404.html']:
        for lat in (1440, 390):
            ctx, pg, errs = pagina(b, url, lat, 2500)
            h = pg.evaluate("[document.documentElement.scrollWidth, document.documentElement.clientWidth]")
            verifica(f'{url} la {lat}px: fără scroll orizontal, fără erori', h[0] <= h[1] + 1 and errs == [], [h, errs])
            if lat == 1440:
                verifica(f'{url}: tema se aplică (Inter + banda tricoloră)', pg.evaluate("getComputedStyle(document.body).fontFamily.startsWith('Inter') && getComputedStyle(document.body, '::before').height === '6px'"))
            else:
                ph = pg.evaluate("(() => { const g = getComputedStyle(document.querySelector('.mg-btns')); const l = document.querySelector('.mg-l'); const s = document.querySelector('.mg-s'); return [g.display, getComputedStyle(l).display, getComputedStyle(s).display]; })()")
                # .mg-s e „inline”, dar ca element de flex în buton devine „block”: contează doar că se vede, iar eticheta lungă nu
                verifica(f'{url} la {lat}px: meniul pe telefon (grilă, etichete scurte)', ph[0] == 'grid' and ph[1] == 'none' and ph[2] in ('inline', 'block'), ph)
            ctx.close()
    b.close()

verifica('nicio cerere către servere de fonturi (Google Fonts etc.)', not [u for u in EXT if re.search(r'fonts\.(googleapis|gstatic)|typekit|use\.fontawesome', u)], [u for u in EXT if 'font' in u][:5])
print('\n' + (f'{len(picat)} teste au picat: ' + '; '.join(picat) if picat else 'Toate testele temei au trecut.'))
sys.exit(1 if picat else 0)
