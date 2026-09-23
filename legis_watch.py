"""Verificarea zilnică a acordurilor pe legis.md (Registrul de stat).

Deschide legis.md într-un browser real (Playwright + Chromium), rulează
căutările din legis_extrage.js pentru anul curent, adaugă actele noi în
legis_brut.json, reconstruiește legis_acorduri.html și scrie raportul zilei.

    python legis_watch.py                  # pe GitHub Actions (browser invizibil)
    python legis_watch.py --headed --profil .legis_profil   # pe calculatorul tău

De ce browser și nu requests: legis.md e în spatele Cloudflare. O cerere
simplă primește pagina „Just a moment…", nu datele. Un browser adevărat trece
de verificarea automată — dar NU și de bifa „nu sunt robot", pe care scriptul
nu încearcă s-o ocolească. Dacă Cloudflare o cere, scriptul se oprește cu
codul 3 și spune asta în rezumatul rulării. Atunci soluția e rularea locală:
cu --headed --profil, bifezi o dată în fereastra deschisă, iar profilul
păstrează cookie-ul pentru rulările următoare.

Coduri de ieșire: 0 = a mers (cu sau fără acte noi), 3 = blocat de Cloudflare,
4 = căutarea n-a terminat la timp, 1 = altă eroare.
"""
import argparse, datetime, json, os, re, sys, time
from pathlib import Path

AICI = Path(__file__).resolve().parent
sys.path.insert(0, str(AICI))

import legis_pagina as pagina
from legis_clasifica import clasifica, partener

BLOCAT = re.compile(r"Just a moment|verificării de securitate|nu ești un robot|Verify you are human|Checking your browser", re.I)


# --------------------------------------------------------------------- unire

def ani_de_cautat(azi):
    """Anul curent; în ianuarie–martie și anul trecut — actele din decembrie
    apar în registru cu întârziere."""
    ani = [str(azi.year)]
    if azi.month <= 3:
        ani.append(str(azi.year - 1))
    return ani


def id_cunoscute(baza, ani):
    ani = set(ani)
    return sorted({int(r['id']) for r in baza
                   if r['c'].rsplit('/', 1)[-1] in ani or r['pub'][-4:] in ani})


def actualizeaza(nou, baza_p, out_dir):
    """Unește actele noi în bază, reconstruiește pagina, scrie raportul.
    Întoarce rezumatul ca dict."""
    baza = json.load(open(baza_p, encoding='utf-8'))
    dupa_id = {r['id']: r for r in baza}

    adaugate = []
    for r in nou['rows']:
        if r['id'] in dupa_id:
            dupa_id[r['id']]['t'] = r['t']          # „Modificat"/„Abrogat" apar ulterior
            continue
        rr = {'id': r['id'], 'c': r['c'], 'pub': r['pub'], 't': r['t'], 'kw': r.get('kw', [])}
        baza.append(rr); dupa_id[r['id']] = rr
        adaugate.append(rr)

    relevante = []
    for r in adaugate:
        t = pagina.repara(re.sub(r'^(Modificat|Abrogat|Suspendat)\s*', '', r['t']).strip())
        cat = clasifica(t)
        if cat:
            relevante.append({'cod': r['c'], 'pub': r['pub'].replace('-', '.'), 'cat': cat,
                              'partener': partener(t) or '—', 'titlu': t,
                              'link': 'https://www.legis.md/cautare/getResults?doc_id=' + r['id'] + '&lang=ro'})
    relevante.sort(key=lambda a: a['pub'][6:] + a['pub'][3:5] + a['pub'][:2], reverse=True)

    out_dir = Path(out_dir)
    json.dump(baza, open(out_dir / 'legis_brut.json', 'w', encoding='utf-8'), ensure_ascii=False)
    pagina.main(str(out_dir / 'legis_brut.json'), str(out_dir / 'legis_acorduri.html'))

    azi = datetime.date.today().strftime('%d.%m.%Y')
    linii = [f'# Verificare legis.md — {azi}', '',
             f'Ani căutați: {", ".join(nou.get("ani", []))}. Acte găsite de căutare: {nou.get("gasite", len(nou["rows"]))}; '
             f'noi față de bază: {len(adaugate)}; dintre ele, acorduri de asistență externă: **{len(relevante)}**.']
    if nou.get('err'):
        linii.append(f'Căutări eșuate (Cloudflare/timeout): {", ".join(nou["err"])}.')
    linii.append('')
    for a in relevante:
        linii.append(f'- [{a["cod"]}]({a["link"]}) · {a["pub"]} · {a["cat"]} · {a["partener"]} — {a["titlu"]}')
    if not relevante:
        linii.append('Niciun acord nou.')
    raport = '\n'.join(linii) + '\n'
    (out_dir / 'raport_legis.md').write_text(raport, encoding='utf-8')

    # jurnalul: cele mai noi rapoarte sus; doar zilele cu acte noi, ca să nu crească degeaba
    jurnal = out_dir / 'jurnal_legis.md'
    if adaugate or not jurnal.exists():
        vechi = jurnal.read_text(encoding='utf-8') if jurnal.exists() else ''
        jurnal.write_text(raport + '\n' + vechi, encoding='utf-8')

    return {'gasite': nou.get('gasite', len(nou['rows'])), 'noi': len(adaugate),
            'acorduri_noi': len(relevante), 'total_baza': len(baza), 'err': nou.get('err', []),
            'relevante': relevante, 'raport': raport}


# ------------------------------------------------------------------- browser

def extrage(ani, cunoscute, baza_url, headed, profil, asteapta_cf, limita_min):
    from playwright.sync_api import sync_playwright

    js = (AICI / 'legis_extrage.js').read_text(encoding='utf-8')
    js = js.replace('https://www.legis.md', baza_url.rstrip('/'))
    # anii se dau din Python, ca rularea de pe server (UTC) să nu greșească la Anul Nou
    js = re.sub(r"var ANI = \[String\(an\)\]; if \(azi\.getMonth\(\) < 3\) ANI\.push\(String\(an - 1\)\);",
                'var ANI = ' + json.dumps(ani) + ';', js)

    with sync_playwright() as p:
        opt = dict(headless=not headed, locale='ro-RO', viewport={'width': 1280, 'height': 900})
        if profil:
            ctx = p.chromium.launch_persistent_context(str(profil), **opt)
            page = ctx.pages[0] if ctx.pages else ctx.new_page()
            browser = None
        else:
            browser = p.chromium.launch(headless=not headed)
            ctx = browser.new_context(locale='ro-RO', viewport=opt['viewport'])
            page = ctx.new_page()
        try:
            page.goto(baza_url, wait_until='domcontentloaded', timeout=90000)

            # Verificarea automată Cloudflare se rezolvă singură în câteva secunde.
            # În modul --headed ai timp să bifezi tu, dacă e cerută bifa.
            termen = time.time() + asteapta_cf
            while True:
                try:
                    text = page.inner_text('body', timeout=10000)[:2000]
                except Exception:
                    text = ''
                if text and not BLOCAT.search(text):
                    break
                if time.time() > termen:
                    return None
                page.wait_for_timeout(3000)

            page.evaluate('window.LX_KNOWN = ' + json.dumps(cunoscute) + ';')
            print(page.evaluate(js))

            termen = time.time() + limita_min * 60
            while True:
                st = page.evaluate('({pas:LX.pas,total:LX.total,gata:LX.gata,err:LX.err,cf:LX.cloudflare})')
                if st['gata']:
                    break
                if time.time() > termen:
                    raise TimeoutError(f"căutarea n-a terminat în {limita_min} minute ({st['pas']}/{st['total']})")
                page.wait_for_timeout(5000)
            print(f"căutări: {st['total']}, eșuate: {len(st['err'])}, reîncercări Cloudflare: {st['cf']}")
            return json.loads(page.evaluate('LX.noi()'))
        finally:
            ctx.close()
            if browser:
                browser.close()


# ---------------------------------------------------------------------- main

def rezumat_github(text):
    """Pe GitHub Actions, textul apare pe pagina rulării."""
    f = os.environ.get('GITHUB_STEP_SUMMARY')
    if f:
        with open(f, 'a', encoding='utf-8') as g:
            g.write(text + '\n')


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--headed', action='store_true', help='fereastră de browser vizibilă (rulare locală)')
    ap.add_argument('--profil', help='folder de profil persistent: păstrează cookie-ul Cloudflare între rulări')
    ap.add_argument('--ani', nargs='+', help='anii de căutat (implicit: anul curent, plus anul trecut în ian–mar)')
    ap.add_argument('--url', default='https://www.legis.md/', help=argparse.SUPPRESS)   # pentru teste
    ap.add_argument('--asteapta-cf', type=int, default=None,
                    help='câte secunde așteaptă trecerea de Cloudflare (implicit 60; 300 cu --headed)')
    ap.add_argument('--limita', type=int, default=15, help='minute maxim pentru căutări')
    a = ap.parse_args()

    # data după ora Chișinăului, nu UTC
    azi = (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=3)).date()
    ani = a.ani or ani_de_cautat(azi)
    baza_p = AICI / 'legis_brut.json'
    baza = json.load(open(baza_p, encoding='utf-8'))
    asteapta = a.asteapta_cf if a.asteapta_cf is not None else (300 if a.headed else 60)

    print(f'Ani: {", ".join(ani)}; acte cunoscute în acești ani: {len(id_cunoscute(baza, ani))}')
    try:
        nou = extrage(ani, id_cunoscute(baza, ani), a.url, a.headed, a.profil, asteapta, a.limita)
    except TimeoutError as e:
        print('Eroare:', e); rezumat_github(f'### ⚠️ legis.md: {e}'); return 4

    if nou is None:
        msg = ('legis.md a cerut verificarea Cloudflare „nu sunt robot” și rularea s-a oprit. '
               'Scriptul nu încearcă s-o ocolească. Dacă se repetă zilnic, rulează local: '
               '`python legis_watch.py --headed --profil .legis_profil` (vezi README).')
        print(msg); rezumat_github('### ⛔ Blocat de Cloudflare\n\n' + msg)
        return 3

    r = actualizeaza(nou, baza_p, AICI)
    print(r['raport'])
    rezumat_github(r['raport'])
    print(json.dumps({k: v for k, v in r.items() if k not in ('relevante', 'raport')}, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    sys.exit(main())
