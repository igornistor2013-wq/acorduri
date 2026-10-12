"""Testele panoului „Donatori → sectoare" (sectoare.js).

    python teste_sectoare.py             # logica pură, cu Node: agregări, filtre, diagrama ca text SVG, datele pentru Excel
    python teste_sectoare.py --browser   # plus: panoul din dashboard, în română și engleză (clicuri, filtre, tastatură, Excel, CSV)

Logica pură se verifică prin comparație cu un calcul independent, scris aici în Python, pe date de probă mici (cu cazurile grele:
proiecte cu mai mulți donatori sau sectoare, fără sector, fără an, cu sume zero, rânduri duble) și pe 400 de proiecte generate la întâmplare.
Are nevoie de Node.js și de openpyxl (iar pentru --browser, de Playwright).
"""
import csv, functools, io, json, os, random, re, shutil, subprocess, sys, tempfile, threading, zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

import openpyxl

AICI = Path(__file__).resolve().parent
picat = []
SEP = '\u0002'
ALTII, ALTE = '§alti§', '§alte§'


def verifica(nume, conditie, detaliu=''):
    print(('  ok   ' if conditie else '  PICĂ ') + nume + ('' if conditie else f'  → {str(detaliu)[:400]}'))
    if not conditie:
        picat.append(nume)


def parti_xml_valide(cale):
    rele = []
    with zipfile.ZipFile(cale) as z:
        for n in z.namelist():
            if n.endswith('.xml') or n.endswith('.rels'):
                try:
                    ET.fromstring(z.read(n))
                except ET.ParseError as e:
                    rele.append((n, str(e)[:60]))
    return rele


# ============================================================ date de probă
def proiect(id_, donatori, sectoare, an, ang, deb):
    return {'id': id_, 'denumire': 'Proiect ' + id_, 'donator': ' / '.join(donatori), 'donatori': donatori,
            'sectoare': [{'cod': '', 'nume': s} for s in sectoare], 'an': an, 'ang': ang, 'deb': deb}


MICI = [
    proiect('1', ['A'], ['S1'], 2010, 100, 50),
    proiect('2', ['A'], ['S1', 'S2'], 2011, 200, 100),        # două sectoare
    proiect('3', ['B'], ['S2'], 2012, 300, 0),
    proiect('4', ['A', 'B'], ['S1'], 2013, 400, 400),         # doi donatori
    proiect('5', ['C'], [], 'NA', 50, 10),                    # fără sector și fără an
    proiect('6', ['D'], ['S3'], 2014, 0, 0),                  # sume zero
    proiect('1', ['A'], ['S1'], 2010, 0, 0),                  # rând dublu al proiectului 1
]


def aleatorii(n=400, seed=7):
    r = random.Random(seed)
    donori = ['Donator %02d' % i for i in range(30)]
    sect = ['Sector %02d' % i for i in range(15)] + ['Nespecificat']
    out = []
    for i in range(n):
        nd = r.choice([1, 1, 1, 1, 2, 3])
        ns = r.choice([0, 1, 1, 1, 1, 2, 2, 3])
        # donatorii „mari" apar mai des: distribuție înclinată, ca în datele reale
        dd = sorted({donori[min(int(r.expovariate(0.18)), 29)] for _ in range(nd)})
        ss = sorted({sect[min(int(r.expovariate(0.3)), 14)] for _ in range(ns)})
        an = r.choice([r.randint(1995, 2026)] * 9 + ['NA'])
        ang = r.choice([0, 0, r.randint(1, 5_000_000), r.randint(1, 90_000_000)])
        deb = int(ang * r.random()) if ang else 0
        out.append(proiect('p%d' % i, dd, ss, an, ang, deb))
    # câteva rânduri duble, ca să se vadă strângerea după AMP ID
    for i in range(0, 40, 8):
        d = dict(out[i]); d['ang'] = 11; d['deb'] = 3
        out.append(d)
    return out


# ============================================================ calculul independent, în Python
def unice(date):
    m = {}
    for p in date:
        k = p['id'] or ('nm:' + p['denumire'])
        g = m.setdefault(k, {'id': p['id'], 'an': p['an'], 'ang': 0, 'deb': 0, 'donatori': [], 'sectoare': []})
        g['ang'] += p['ang']; g['deb'] += p['deb']
        if p['an'] != 'NA' and (g['an'] == 'NA' or p['an'] < g['an']):
            g['an'] = p['an']
        for d in p['donatori']:
            if d not in g['donatori']: g['donatori'].append(d)
        for s in p['sectoare']:
            if s['nume'] not in g['sectoare']: g['sectoare'].append(s['nume'])
    for g in m.values():
        if not g['sectoare']: g['sectoare'].append('Nespecificat')
    return list(m.values())


def perioada(lista, de=0, pana=0):
    if not de and not pana:
        return lista
    return [p for p in lista if p['an'] != 'NA' and (not de or p['an'] >= de) and (not pana or p['an'] <= pana)]


def asteptat(lista, metric, nD, nS):
    """Nodurile, legăturile și totalurile, calculate direct din definiție."""
    def tot(cheie_p):
        t = {}
        for p in lista:
            for k in p[cheie_p]:
                x = t.setdefault(k, {'ang': 0, 'deb': 0, 'n': 0}); x['ang'] += p['ang']; x['deb'] += p['deb']; x['n'] += 1
        return t
    td, ts = tot('donatori'), tot('sectoare')
    ordine = lambda t: sorted(t, key=lambda k: (-t[k][metric], -t[k]['n'], k))
    top = lambda t, n: [k for k in ordine(t) if t[k][metric] > 0][:n]
    topD, topS = top(td, nD), top(ts, nS)
    leg = {}
    for p in lista:
        ds = {d if d in topD else ALTII for d in p['donatori']}
        ss = {s if s in topS else ALTE for s in p['sectoare']}
        for d in ds:
            for s in ss:
                x = leg.setdefault((d, s), {'ang': 0, 'deb': 0, 'n': 0}); x['ang'] += p['ang']; x['deb'] += p['deb']; x['n'] += 1
    alt = lambda cheie_p, top_, marcaj: {'ang': sum(p['ang'] for p in lista if any(k not in top_ for k in p[cheie_p])),
                                          'deb': sum(p['deb'] for p in lista if any(k not in top_ for k in p[cheie_p])),
                                          'n': sum(1 for p in lista if any(k not in top_ for k in p[cheie_p]))}
    return {'td': td, 'ts': ts, 'topD': topD, 'topS': topS, 'leg': leg, 'altD': alt('donatori', topD, ALTII), 'altS': alt('sectoare', topS, ALTE),
            'total': {'ang': sum(p['ang'] for p in lista), 'deb': sum(p['deb'] for p in lista), 'n': len(lista)}}


def grupe_asteptate(lista, metric, don=None, sec=None, altiD=(), alteS=()):
    gr = {}
    for p in lista:
        if don and not any((d in altiD) if don == ALTII else d == don for d in p['donatori']):
            continue
        for s in p['sectoare']:
            if sec and not ((s in alteS) if sec == ALTE else s == sec):
                continue
            g = gr.setdefault(s, {'n': 0, 'ang': 0, 'deb': 0, 'ids': []})
            g['n'] += 1; g['ang'] += p['ang']; g['deb'] += p['deb']; g['ids'].append(p['id'])
    return gr


# ============================================================ 1. logica pură, cu Node
print('Logica pură (sectoare.js), cu Node')
if not shutil.which('node'):
    print('  PICĂ nu există Node.js'); sys.exit(1)

GEN = r'''
const S = require(process.argv[2]);
const X = require(process.argv[3]);
const fs = require('fs');
const date = JSON.parse(fs.readFileSync(process.argv[4], 'utf8'));
const out = process.argv[5];
const lst = o => o instanceof Set ? [...o] : o;
const nodes = a => a.nodD.concat([]).map(x => x);
const rez = {};
const prep = (nume, proiecte, o) => {
  const u = S.unice(proiecte);
  const l = S.dinPerioada(u, o.de, o.pana);
  const agr = S.agrega(l, { metric: o.metric, nD: o.nD, nS: o.nS, fixD: o.fixD, fixS: o.fixS });
  const grupe = S.peSectoare(l, { metric: o.metric, sel: o.sel || {}, agr: agr });
  const matr = S.matrice(l, { metric: o.metric, sel: o.sel || {}, agr: agr });
  rez[nume] = {
    unice: u.map(p => ({ id: p.id, an: p.an, ang: p.ang, deb: p.deb, donatori: p.donatori, sectoare: p.sectoare })), lista: l.length,
    agr: { metric: agr.metric, total: agr.total, aparitii: agr.aparitii, nodD: agr.nodD.map(x => ({ cheie: x.cheie, alt: x.alt, ang: x.ang, deb: x.deb, n: x.n, nrLegat: x.nrLegat, nr: x.nr })),
           nodS: agr.nodS.map(x => ({ cheie: x.cheie, alt: x.alt, ang: x.ang, deb: x.deb, n: x.n, nrLegat: x.nrLegat, nr: x.nr })),
           legaturi: agr.legaturi, altiD: [...agr.altiD], alteS: [...agr.alteS], nrDonatori: agr.donatori.length, nrSectoare: agr.sectoare.length },
    grupe: grupe.map(g => ({ cheie: g.cheie, n: g.n, ang: g.ang, deb: g.deb, ids: g.proiecte.map(p => p.id), donatori: g.donatori.map(d => d.cheie) })),
    total: S.totalGrupe(grupe),
    matr: { donatori: matr.donatori, sectoare: matr.sectoare, cel: [...matr.cel.entries()] }
  };
  return { u, l, agr, grupe, matr };
};
const mici = date.mici, mari = date.aleatorii;
prep('mici_ang', mici, { metric: 'ang', nD: 2, nS: 2 });
prep('mici_deb', mici, { metric: 'deb', nD: 2, nS: 2 });
prep('mici_per', mici, { metric: 'ang', nD: 2, nS: 2, de: 2011, pana: 2013 });
prep('mici_donA', mici, { metric: 'ang', nD: 2, nS: 2, sel: { donator: 'A' } });
prep('mici_alte', mici, { metric: 'ang', nD: 2, nS: 2, sel: { sector: S.ALTE } });
prep('mici_alti', mici, { metric: 'ang', nD: 2, nS: 2, sel: { donator: S.ALTII } });
prep('mici_fix', mici, { metric: 'ang', nD: 1, nS: 1, fixD: ['B'], fixS: ['S2'] });
for (const m of ['ang', 'deb']) for (const nD of [5, 12]) {
  prep('mari_' + m + '_' + nD, mari, { metric: m, nD: nD, nS: 6 });
}
prep('mari_per', mari, { metric: 'ang', nD: 8, nS: 5, de: 2005, pana: 2015 });
const un = prep('mari_sel', mari, { metric: 'ang', nD: 8, nS: 5, sel: { donator: 'Donator 03', sector: 'Sector 02' } });
prep('mari_sel_alte', mari, { metric: 'ang', nD: 8, nS: 5, sel: { donator: S.ALTII, sector: S.ALTE } });

/* diagrama */
const etichete = { 'D<b>&"x': 'Donator <b> & "ghilimele"' };
const dd = [{ id: '1', denumire: 'x', donator: 'D<b>&"x', donatori: ['D<b>&"x'], sectoare: [{ nume: 'S&1' }], an: 2020, ang: 10, deb: 5 },
            { id: '2', denumire: 'y', donator: 'E', donatori: ['E'], sectoare: [{ nume: 'S&1' }, { nume: 'S2' }], an: 2021, ang: 7, deb: 1 }];
const l2 = S.unice(dd), a2 = S.agrega(l2, { metric: 'ang', nD: 5, nS: 5 });
const esc = s => String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;').replace(/'/g, '&#39;');
const ctxD = sel => ({ sel: sel || {}, etD: k => etichete[k] || k, etS: k => k, fmt: v => String(Math.round(v)), esc: esc, L: (ro, en) => ro, titluD: 'Donatori', titluS: 'Sectoare', aria: 'Test "aria"' });
const d1 = S.diagramaSvg(a2, ctxD());
const d2 = S.diagramaSvg(a2, ctxD({ donator: 'E' }));
const dm = S.diagramaSvg(S.agrega(S.unice(mari), { metric: 'ang', nD: 12, nS: 30 }), ctxD());
rez.svg = { svg: d1.svg, svgSel: d2.svg, H: d1.H, W: d1.W, mareH: dm.H, mare: dm.svg, nLeg: a2.legaturi.length };
rez.plural = { ro: [0, 1, 2, 3, 19, 20, 21, 99, 100, 101, 119, 120, 378, 1000, 3008].map(n => S.numar(n, false, 'proiect', 'proiecte', 'project', 'projects')),
               en: [0, 1, 2, 20].map(n => S.numar(n, true, 'proiect', 'proiecte', 'project', 'projects')),
               cuv: [S.cuvant(1, false, 'sector', 'sectoare', 'sector', 'sectors'), S.cuvant(27, false, 'sector', 'sectoare', 'sector', 'sectors'), S.cuvant(1, true, 'sector', 'sectoare', 'sector', 'sectors'), S.cuvant(5, true, 'sector', 'sectoare', 'sector', 'sectors')],
               fmt: S.numar(3008, false, 'proiect', 'proiecte', 'project', 'projects', n => n.toLocaleString('ro-RO')),
               aria1: S.diagramaSvg(S.agrega(S.unice([{ id: '1', denumire: 'x', donator: 'A', donatori: ['A'], sectoare: [{ nume: 'S' }], an: 2020, ang: 1, deb: 1 }]), { metric: 'ang', nD: 5, nS: 5 }), Object.assign(ctxD(), { en: false })).svg,
               ariaEn: S.diagramaSvg(S.agrega(S.unice([{ id: '1', denumire: 'x', donator: 'A', donatori: ['A'], sectoare: [{ nume: 'S' }], an: 2020, ang: 1, deb: 1 }]), { metric: 'ang', nD: 5, nS: 5 }), Object.assign(ctxD(), { en: true })).svg };
rez.focus = { f1: (() => { const f = S.focus({ legaturi: [{ d: 0, s: 0 }, { d: 0, s: 1 }, { d: 1, s: 1 }] }, { d: 0, s: null }); return { linii: [...f.linii], d: [...f.donatori], s: [...f.sectoare] }; })(),
              f2: (() => { const f = S.focus({ legaturi: [{ d: 0, s: 0 }, { d: 0, s: 1 }, { d: 1, s: 1 }] }, { d: null, s: 1 }); return { linii: [...f.linii], d: [...f.donatori], s: [...f.sectoare] }; })(),
              f3: S.focus({ legaturi: [] }, { d: null, s: null }) };

/* Excel: date → specificații → fișier */
const aSpec = f => {
  const o = f.opt; let rows = f.rows, randTotal = false;
  if(Array.isArray(o.randTotal) && !o.total){ rows = rows.concat([o.randTotal]); randTotal = true; }
  return { foaie: f.foaie, titlu: f.titlu, subtitlu: 'Test · ' + (o.context || []).join(' · '), antete: f.cols, tipuri: o.tip, randuri: rows, total: o.total || null, randTotal: randTotal,
           note: o.nota || [], bare: o.bare, harta: o.harta, linkuri: o.linkuri, latimi: o.latimi, grafic: o.grafic };
};
const exporta = async (nume, proiecte, o) => {
  const u = S.unice(proiecte), l = S.dinPerioada(u, o.de, o.pana);
  const agr = S.agrega(l, { metric: o.metric, nD: 8, nS: 30 });
  const sel = o.sel || {};
  const grupe = S.peSectoare(l, { metric: o.metric, sel: sel, agr: agr });
  const matr = S.matrice(l, { metric: o.metric, sel: sel, agr: agr });
  const d = S.datePentruExport(agr, grupe, matr, { L: (ro, en) => ro, en: false, etD: k => k, etS: k => k === S.FARA_SECTOR ? 'Nespecificat' : k, titlu: p => 'Titlu ' + p.id, perioada: p => String(p.an),
                                                    url: id => 'https://amp.gov.md/' + id, context: ['Perioadă: test'] });
  const b = await X.construieste({ limba: 'ro', subsol: 'test', foi: d.opt.foiExcel.map(aSpec) });
  fs.writeFileSync(out + '/' + nume + '.xlsx', Buffer.from(await b.arrayBuffer()));
  return { cols: d.cols, nrRanduri: d.rows.length, foi: d.opt.foiExcel.map(f => ({ foaie: f.foaie, nC: f.cols.length, nTip: (f.opt.tip || '').length, nR: f.rows.length,
             lungimiRanduri: [...new Set(f.rows.map(r => r.length))], randTotal: f.opt.randTotal || null })), grupe: grupe.map(g => ({ cheie: g.cheie, n: g.n, ang: g.ang, deb: g.deb })), total: S.totalGrupe(grupe) };
};
(async () => {
  rez.xl_mari = await exporta('xl_mari', mari, { metric: 'ang' });
  rez.xl_sel = await exporta('xl_sel', mari, { metric: 'deb', sel: { donator: 'Donator 03' }, de: 2000, pana: 2020 });
  rez.xl_mici = await exporta('xl_mici', mici, { metric: 'ang' });
  fs.writeFileSync(out + '/rez.json', JSON.stringify(rez));
})().catch(e => { console.error('EROARE', e && e.stack || e); process.exit(1); });
'''
tmp = Path(tempfile.mkdtemp(prefix='teste_sectoare_'))
try:
    (tmp / 'gen.js').write_text(GEN, encoding='utf-8')
    (tmp / 'date.json').write_text(json.dumps({'mici': MICI, 'aleatorii': aleatorii()}), encoding='utf-8')
    r = subprocess.run(['node', str(tmp / 'gen.js'), str(AICI / 'sectoare.js'), str(AICI / 'xlsx-stil.js'), str(tmp / 'date.json'), str(tmp)], capture_output=True, text=True, timeout=180)
    verifica('Node încarcă sectoare.js fără pagină și calculează toate cazurile', r.returncode == 0, (r.stderr or r.stdout)[-400:])
    rez = json.loads((tmp / 'rez.json').read_text(encoding='utf-8')) if r.returncode == 0 else {}

    # ------------------------------------------------ date mici, cu valori calculate de mână
    m = rez.get('mici_ang', {})
    verifica('mici: rândul dublu al proiectului 1 se strânge (6 proiecte din 7 rânduri)', len(m.get('unice', [])) == 6 and m['lista'] == 6, m.get('lista'))
    p1 = next((p for p in m.get('unice', []) if p['id'] == '1'), {})
    verifica('mici: sumele rândurilor duble se adună, donatorii și sectoarele se unesc', p1.get('ang') == 100 and p1.get('deb') == 50 and p1.get('donatori') == ['A'] and p1.get('sectoare') == ['S1'], p1)
    p5 = next((p for p in m.get('unice', []) if p['id'] == '5'), {})
    verifica('mici: proiectul fără sector intră la „Nespecificat”', p5.get('sectoare') == ['Nespecificat'], p5)
    nd = {x['cheie']: x for x in m['agr']['nodD']}
    ns = {x['cheie']: x for x in m['agr']['nodS']}
    verifica('mici: donatorii afișați sunt primii 2 după angajamente (A, B) + „Alții”', [x['cheie'] for x in m['agr']['nodD']] == ['A', 'B', ALTII], [x['cheie'] for x in m['agr']['nodD']])
    verifica('mici: totalul donatorului A numără fiecare proiect o singură dată: 100+200+400 = 700 din 3 proiecte', nd['A']['ang'] == 700 and nd['A']['n'] == 3, nd['A'])
    verifica('mici: proiectul cu doi donatori apare cu suma întreagă la fiecare (B = 300 + 400)', nd['B']['ang'] == 700 and nd['B']['n'] == 2, nd['B'])
    verifica('mici: „Alți donatori” = C și D (proiectele 5 și 6), 50 EUR, 2 proiecte, 2 donatori', nd[ALTII]['ang'] == 50 and nd[ALTII]['n'] == 2 and nd[ALTII]['nr'] == 2, nd[ALTII])
    verifica('mici: sectoarele afișate: S1, S2 + „Alte sectoare” (S3 și Nespecificat)', [x['cheie'] for x in m['agr']['nodS']] == ['S1', 'S2', ALTE], [x['cheie'] for x in m['agr']['nodS']])
    verifica('mici: sectorul S1 = 100+200+400 = 700 (3 proiecte); S2 = 200+300 = 500 (2 proiecte)', ns['S1']['ang'] == 700 and ns['S1']['n'] == 3 and ns['S2']['ang'] == 500 and ns['S2']['n'] == 2, (ns['S1'], ns['S2']))
    leg = {(l['d'], l['s']): l for l in m['agr']['legaturi']}
    verifica('mici: legăturile sunt cele din definiție (A→S1 700, A→S2 200, B→S2 300, B→S1 400, Alții→Alte 50)',
             {k: v['ang'] for k, v in leg.items()} == {('A', 'S1'): 700, ('A', 'S2'): 200, ('B', 'S2'): 300, ('B', 'S1'): 400, (ALTII, ALTE): 50}, {k: v['ang'] for k, v in leg.items()})
    verifica('mici: suma liniilor unui donator poate depăși bara lui (A: 900 față de 700) — de aceea nu e un Sankey',
             sum(l['ang'] for l in m['agr']['legaturi'] if l['d'] == 'A') == 900 and nd['A']['ang'] == 700)
    verifica('mici: totalul general numără fiecare proiect o dată (750 EUR, 6 proiecte), iar aparițiile în sectoare sunt 7',
             m['agr']['total'] == {'proiecte': 6, 'ang': 1050, 'deb': 560} or (m['agr']['total']['proiecte'] == 6 and m['agr']['total']['ang'] == 1050), m['agr']['total'])
    verifica('mici: legăturile sunt ordonate descrescător după sumă', [l['ang'] for l in m['agr']['legaturi']] == sorted([l['ang'] for l in m['agr']['legaturi']], reverse=True))
    md = rez['mici_deb']
    verifica('mici (debursări): donatorii cu 0 debursări nu au bară (D, C sunt în „Alții” doar dacă au sumă)', [x['cheie'] for x in md['agr']['nodD']][:2] == ['A', 'B'], [x['cheie'] for x in md['agr']['nodD']])
    mp = rez['mici_per']
    verifica('mici: perioada 2011–2013 păstrează proiectele 2, 3, 4 (fără 2010, 2014 și fără anul necunoscut)', mp['lista'] == 3, mp['lista'])
    verifica('mici: fără perioadă, proiectele fără an intră în calcul', m['lista'] == 6 and any(p['an'] == 'NA' for p in m['unice']))
    mfix = rez['mici_fix']
    verifica('mici: donatorul și sectorul selectate rămân în diagramă chiar dacă nu sunt printre primele', 'B' in [x['cheie'] for x in mfix['agr']['nodD']] and 'S2' in [x['cheie'] for x in mfix['agr']['nodS']], [x['cheie'] for x in mfix['agr']['nodD']])
    mda = rez['mici_donA']
    verifica('mici: selecția „donator A” → sectoarele S1 (3 proiecte) și S2 (1 proiect)', {g['cheie']: g['n'] for g in mda['grupe']} == {'S1': 3, 'S2': 1}, mda['grupe'])
    verifica('mici: în grup, proiectele sunt ordonate după sumă (400, 200, 100)', next(g for g in mda['grupe'] if g['cheie'] == 'S1')['ids'] == ['4', '2', '1'], mda['grupe'])
    mal = rez['mici_alte']
    verifica('mici: selecția „Alte sectoare” → S3 și Nespecificat, fiecare cu un proiect', {g['cheie']: g['n'] for g in mal['grupe']} == {'S3': 1, 'Nespecificat': 1}, mal['grupe'])
    mai = rez['mici_alti']
    verifica('mici: selecția „Alți donatori” → proiectele donatorilor C și D', sorted(i for g in mai['grupe'] for i in g['ids']) == ['5', '6'], mai['grupe'])
    verifica('mici: totalul grupurilor numără proiectul cu două sectoare o singură dată (aparițiile > proiecte)', m['total']['proiecte'] == 6 and m['total']['aparitii'] == 7 and m['total']['sectoare'] == 4, m['total'])
    mm = rez['mici_ang']['matr']
    cel = {k: v for k, v in mm['cel']}
    verifica('mici: matricea donator × sector: A×S1 = 700, A×S2 = 200, B×S1 = 400', cel.get('A' + SEP + 'S1') == 700 and cel.get('A' + SEP + 'S2') == 200 and cel.get('B' + SEP + 'S1') == 400, cel)
    verifica('mici: matricea nu are rânduri sau coloane cu total zero (donatorul D lipsește)', 'D' not in [x['cheie'] for x in mm['donatori']] and 'S3' not in [x['cheie'] for x in mm['sectoare']], mm['donatori'])

    # ------------------------------------------------ 400 de proiecte generate la întâmplare, față de calculul independent
    date_mari = aleatorii()
    for nume, metric, nD, de, pana, nS in [('mari_ang_5', 'ang', 5, 0, 0, 6), ('mari_ang_12', 'ang', 12, 0, 0, 6), ('mari_deb_5', 'deb', 5, 0, 0, 6), ('mari_deb_12', 'deb', 12, 0, 0, 6), ('mari_per', 'ang', 8, 2005, 2015, 5)]:
        r_ = rez[nume]
        lista = perioada(unice(date_mari), de, pana)
        a = asteptat(lista, metric, nD, nS)
        nodD = {x['cheie']: x for x in r_['agr']['nodD']}
        nodS = {x['cheie']: x for x in r_['agr']['nodS']}
        verifica(f'{nume}: donatorii afișați sunt primii {nD} după {metric} (ordinea și numărul)', [k for k in nodD if k != ALTII] == a['topD'], ([k for k in nodD if k != ALTII], a['topD']))
        verifica(f'{nume}: sectoarele afișate sunt primele {nS} după {metric}', [k for k in nodS if k != ALTE] == a['topS'], ([k for k in nodS if k != ALTE], a['topS']))
        verifica(f'{nume}: totalul și numărul de proiecte al fiecărui donator = suma proiectelor lui, fiecare o singură dată',
                 all(nodD[k]['ang'] == a['td'][k]['ang'] and nodD[k]['deb'] == a['td'][k]['deb'] and nodD[k]['n'] == a['td'][k]['n'] for k in a['topD']))
        verifica(f'{nume}: la fel pentru sectoare', all(nodS[k]['ang'] == a['ts'][k]['ang'] and nodS[k]['deb'] == a['ts'][k]['deb'] and nodS[k]['n'] == a['ts'][k]['n'] for k in a['topS']))
        legs = {(l['d'], l['s']): l for l in r_['agr']['legaturi']}
        asteptate = {k: v for k, v in a['leg'].items() if v[metric] > 0}
        verifica(f'{nume}: fiecare legătură donator–sector = suma proiectelor care au și donatorul, și sectorul ({len(asteptate)} legături)',
                 set(legs) == set(asteptate) and all(legs[k]['ang'] == asteptate[k]['ang'] and legs[k]['deb'] == asteptate[k]['deb'] and legs[k]['n'] == asteptate[k]['n'] for k in asteptate),
                 (sorted(set(legs) ^ set(asteptate))[:3]))
        verifica(f'{nume}: „Alți donatori” = proiectele care au cel puțin un donator din afara primilor, fiecare o singură dată',
                 (ALTII in nodD) == (a['altD'][metric] > 0) and (ALTII not in nodD or (nodD[ALTII]['ang'] == a['altD']['ang'] and nodD[ALTII]['n'] == a['altD']['n'])), (nodD.get(ALTII), a['altD']))
        verifica(f'{nume}: „Alte sectoare” la fel', (ALTE in nodS) == (a['altS'][metric] > 0) and (ALTE not in nodS or (nodS[ALTE]['ang'] == a['altS']['ang'] and nodS[ALTE]['n'] == a['altS']['n'])), (nodS.get(ALTE), a['altS']))
        verifica(f'{nume}: totalul general = fiecare proiect o singură dată', r_['agr']['total']['ang'] == a['total']['ang'] and r_['agr']['total']['deb'] == a['total']['deb'] and r_['agr']['total']['proiecte'] == a['total']['n'], (r_['agr']['total'], a['total']))
        gr = grupe_asteptate(lista, metric, altiD=set(r_['agr']['altiD']), alteS=set(r_['agr']['alteS']))
        g_ = {g['cheie']: g for g in r_['grupe']}
        verifica(f'{nume}: lista pe sectoare are câte un grup pe sector, cu proiectele și sumele lui', set(g_) == set(gr) and all(g_[k]['n'] == gr[k]['n'] and g_[k]['ang'] == gr[k]['ang'] and g_[k]['deb'] == gr[k]['deb'] and sorted(g_[k]['ids']) == sorted(gr[k]['ids']) for k in gr))
        verifica(f'{nume}: grupurile sunt ordonate descrescător după {metric}', [g[metric] for g in r_['grupe']] == sorted([g[metric] for g in r_['grupe']], reverse=True))
        verifica(f'{nume}: în fiecare grup proiectele sunt ordonate descrescător după {metric}', all([next(p for p in lista if p['id'] == i)[metric] for i in g['ids']] == sorted([next(p for p in lista if p['id'] == i)[metric] for i in g['ids']], reverse=True) for g in r_['grupe']))
    ms = rez['mari_sel']
    lista = unice(date_mari)
    a_ = asteptat(lista, 'ang', 8, 5)
    gr = grupe_asteptate(lista, 'ang', 'Donator 03', 'Sector 02')
    verifica('mari: selecția donator + sector dă exact proiectele care le au pe amândouă', {g['cheie']: g['n'] for g in ms['grupe']} == {k: v['n'] for k, v in gr.items()} and
             sorted(i for g in ms['grupe'] for i in g['ids']) == sorted(i for v in gr.values() for i in v['ids']), (ms['grupe'], gr))
    mse = rez['mari_sel_alte']
    gr2 = grupe_asteptate(lista, 'ang', ALTII, ALTE, altiD=set(mse['agr']['altiD']), alteS=set(mse['agr']['alteS']))
    verifica('mari: selecția „Alți donatori” + „Alte sectoare” dă proiectele care le au pe amândouă', sorted((g['cheie'], g['n']) for g in mse['grupe']) == sorted((k, v['n']) for k, v in gr2.items()), (mse['grupe'][:3], list(gr2.items())[:3]))
    mar = rez['mari_ang_12']
    verifica('mari: matricea are exact celulele donator × sector din definiție', all(
        v == sum(p['ang'] for p in lista if k.split(SEP)[0] in p['donatori'] and k.split(SEP)[1] in p['sectoare']) for k, v in {k: v for k, v in mar['matr']['cel']}.items()))
    verifica('mari: sumele pe donator din matrice = totalurile fiecărui donator (fiecare proiect o dată)', all(
        x['total'] == sum(p['ang'] for p in lista if x['cheie'] in p['donatori']) for x in mar['matr']['donatori']))

    # ------------------------------------------------ focus și diagrama SVG
    fo = rez['focus']
    verifica('focus: un donator luminează liniile lui și sectoarele legate', fo['f1']['linii'] == [0, 1] and fo['f1']['d'] == [0] and sorted(fo['f1']['s']) == [0, 1], fo['f1'])
    verifica('focus: un sector luminează liniile către el și donatorii legați', fo['f2']['linii'] == [1, 2] and sorted(fo['f2']['d']) == [0, 1] and fo['f2']['s'] == [1], fo['f2'])
    verifica('focus: fără donator și fără sector, nimic nu e în focus', fo['f3'] is None)
    pl = rez['plural']
    verifica('plural (română): 1 proiect, 2–19 proiecte, de la 20 și la sute rotunde „de proiecte”', pl['ro'] == ['0 proiecte', '1 proiect', '2 proiecte', '3 proiecte', '19 proiecte', '20 de proiecte', '21 de proiecte', '99 de proiecte', '100 de proiecte', '101 proiecte', '119 proiecte', '120 de proiecte', '378 de proiecte', '1000 de proiecte', '3008 proiecte'], pl['ro'])
    verifica('plural (engleză): 1 project, altfel projects', pl['en'] == ['0 projects', '1 project', '2 projects', '20 projects'], pl['en'])
    verifica('plural: cuvântul singur („1 sector”, „27 de sectoare”, „1 sector”, „5 sectors”)', pl['cuv'] == ['sector', 'de sectoare', 'sector', 'sectors'], pl['cuv'])
    verifica('plural: cu formatarea numărului (separator de mii) cuvântul se acordă după număr, nu după text', pl['fmt'].endswith('proiecte') and not pl['fmt'].endswith('de proiecte'), pl['fmt'])
    verifica('plural: în etichetele diagramei un singur proiect e „1 proiect” (română) / „1 project” (engleză)', 'EUR, 1 proiect"' in pl['aria1'] and 'EUR, 1 project"' in pl['ariaEn'], (re.findall(r'aria-label="[^"]*"', pl['aria1'])[:1], re.findall(r'aria-label="[^"]*"', pl['ariaEn'])[:1]))
    sv = rez['svg']
    verifica('svg: o legătură (linie + zonă de clic) pentru fiecare pereche, câte un rând pe nod', sv['svg'].count('class="sdg-link"') == sv['nLeg'] and sv['svg'].count('class="sdg-hit"') == sv['nLeg'] and sv['svg'].count('sdg-row sdg-d') == 2 and sv['svg'].count('sdg-row sdg-s') == 2,
             (sv['svg'].count('class="sdg-link"'), sv['nLeg']))
    verifica('svg: nicio coordonată NaN sau undefined', 'NaN' not in sv['svg'] and 'undefined' not in sv['svg'] and 'Infinity' not in sv['svg'])
    verifica('svg: <, >, & și ghilimelele din nume sunt scrise ca entități (nici un tag străin în text sau în atribute)', '<b>' not in sv['svg'].replace('<b', '').replace('</b', '') and 'D&lt;b&gt;&amp;&quot;x' in sv['svg'].replace('Donator &lt;b&gt; &amp; &quot;ghilimele&quot;', 'D&lt;b&gt;&amp;&quot;x'), sv['svg'][:200])
    try:
        ET.fromstring(sv['svg']); ET.fromstring(sv['mare'])
        ok_xml = True
    except ET.ParseError as e:
        ok_xml = str(e)
    verifica('svg: diagrama e XML bine format (se poate copia ca imagine)', ok_xml is True, ok_xml)
    verifica('svg: rândul selectat are aria-pressed="true" și numai el', sv['svgSel'].count('aria-pressed="true"') == 1 and sv['svg'].count('aria-pressed="true"') == 0, sv['svgSel'].count('aria-pressed="true"'))
    verifica('svg: fiecare rând poate fi atins cu tastatura (tabindex, role, aria-label)', sv['svg'].count('tabindex="0"') == 4 and sv['svg'].count('role="button"') == 4 and sv['svg'].count('aria-label=') == 5)
    verifica('svg: înălțimea crește cu numărul de rânduri (diagrama mare e mai înaltă decât cea mică)', sv['mareH'] > sv['H'] >= 80, (sv['H'], sv['mareH']))
    verifica('svg: culorile sunt atribute, nu CSS (se văd la fel în imaginea copiată)', 'fill="#22406b"' in sv['svg'] and 'fill="#c8871a"' in sv['svg'] and 'stroke-opacity=' in sv['svg'])
    verifica('svg: nu depinde de variabile CSS (var(--…)) care nu există în imaginea copiată', 'var(--' not in sv['svg'])

    # ------------------------------------------------ datele pentru Excel
    for nume in ('xl_mari', 'xl_sel', 'xl_mici'):
        xe = rez[nume]
        verifica(f'{nume}: fiecare foaie are la fel de multe tipuri, antete și celule pe rând', all(f['nC'] == f['nTip'] and f['lungimiRanduri'] in ([f['nC']], []) for f in xe['foi']), [(f['foaie'], f['nC'], f['nTip'], f['lungimiRanduri']) for f in xe['foi'] if not (f['nC'] == f['nTip'] and f['lungimiRanduri'] in ([f['nC']], []))])
        verifica(f'{nume}: primele trei foi sunt „Rezumat”, „Donator × sector”, „Toate proiectele”; apoi câte o foaie pe sector', [f['foaie'] for f in xe['foi']][:3] == ['Rezumat pe sectoare', 'Donator × sector', 'Toate proiectele'] and len(xe['foi']) == 3 + len(xe['grupe']), [f['foaie'] for f in xe['foi']][:4])
        verifica(f'{nume}: CSV-ul (lista plată) are un rând pentru fiecare pereche proiect–sector', xe['nrRanduri'] == sum(g['n'] for g in xe['grupe']), (xe['nrRanduri'], sum(g['n'] for g in xe['grupe'])))
        cale = tmp / (nume + '.xlsx')
        verifica(f'{nume}: fișierul .xlsx e o arhivă validă, cu toate părțile XML bine formate', cale.exists() and zipfile.is_zipfile(cale) and not parti_xml_valide(cale), parti_xml_valide(cale) if cale.exists() else 'lipsă')
        wb = openpyxl.load_workbook(cale)
        nume_foi = wb.sheetnames
        verifica(f'{nume}: foile din fișier = foile cerute (nume unice, cel mult 31 de caractere)', len(nume_foi) == len(xe['foi']) and len({n.lower() for n in nume_foi}) == len(nume_foi) and all(len(n) <= 31 for n in nume_foi), nume_foi[:5])
        if len(nume_foi) > 3:
            ws = wb['Rezumat pe sectoare']
            leg_int = [(c.coordinate, c.hyperlink.location) for row in ws.iter_rows(min_row=5, max_col=1) for c in row if c.hyperlink and c.hyperlink.location]
            verifica(f'{nume}: fiecare sector din „Rezumat” duce la foaia lui (link în fișier, spre A1)', len(leg_int) == len(xe['grupe']) and all(loc.split('!')[0].strip("'") in nume_foi and loc.endswith('!A1') for _, loc in leg_int), leg_int[:3])
            rez_ws = [[c for c in row] for row in ws.iter_rows(min_row=5, max_row=4 + len(xe['grupe']), max_col=4, values_only=True)]
            verifica(f'{nume}: „Rezumat” are proiectele și sumele fiecărui sector', [(r[1], r[2], r[3]) for r in rez_ws] == [(g['n'], round(g['ang']), round(g['deb'])) for g in xe['grupe']], rez_ws[:2])
            ultima = ws.cell(row=5 + len(xe['grupe']), column=1).value
            tot = ws.cell(row=5 + len(xe['grupe']), column=2).value
            verifica(f'{nume}: rândul de total din „Rezumat” numără proiectele o singură dată ({xe["total"]["proiecte"]}, nu {xe["total"]["aparitii"]})', 'unice' in str(ultima) and tot == xe['total']['proiecte'], (ultima, tot))
            with zipfile.ZipFile(cale) as z:
                verifica(f'{nume}: „Rezumat” are graficul cu primele 12 sectoare', 'xl/charts/chart1.xml' in z.namelist() and "Rezumat pe sectoare" in z.read('xl/charts/chart1.xml').decode('utf-8'))
            g0 = xe['grupe'][0]
            ws1 = wb[[n for n in nume_foi if n not in ('Rezumat pe sectoare', 'Donator × sector', 'Toate proiectele')][0]]
            verifica(f'{nume}: foaia primului sector are {g0["n"]} proiecte și totalul ca formulă', ws1.max_row >= 4 + g0['n'] and str(ws1.cell(row=5 + g0['n'], column=5).value).startswith('=SUBTOTAL(109,'), (ws1.max_row, ws1.cell(row=5 + g0['n'], column=5).value))
            link_amp = [c.hyperlink.target for row in ws1.iter_rows(min_row=5, max_row=4 + g0['n'], max_col=1) for c in row if c.hyperlink]
            verifica(f'{nume}: AMP ID-urile din foaia sectorului sunt link-uri spre AMP', len(link_amp) == sum(1 for r in ws1.iter_rows(min_row=5, max_row=4 + g0['n'], max_col=1, values_only=True) if r[0]) and all(u.startswith('https://amp.gov.md/') for u in link_amp), link_amp[:2])
    xs = rez['xl_sel']
    verifica('xl_sel: cu un donator ales, fiecare sector din fișier conține doar proiectele lui (perioada 2000–2020 respectată)', all(g['n'] > 0 for g in xs['grupe']), xs['grupe'][:3])
finally:
    shutil.rmtree(tmp, ignore_errors=True)


# ============================================================ 2. în browser
if '--browser' in sys.argv:
    print()
    print('Panoul în dashboard, în browser')
    sys.path.insert(0, str(AICI))
    import legatura_acorduri as lga
    from playwright.sync_api import sync_playwright

    srv = lga._Server(('127.0.0.1', 0), functools.partial(lga._Liniste, directory=str(AICI)))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    baza = 'http://127.0.0.1:%d/' % srv.server_address[1]
    DESCARCARI = Path(tempfile.mkdtemp(prefix='teste_sectoare_dl_'))
    ERORI = []

    JS_STARE = '''() => {
      const c = window.__sdgStare, p = document.getElementById('sdgPanel');
      const rows = sel => [...p.querySelectorAll(sel)];
      return {
        metric: c.metric, donator: c.donator, sector: c.sector, de: c.de, pana: c.pana,
        nD: rows('.sdg-d').length, nS: rows('.sdg-s').length, legaturi: rows('.sdg-link').length,
        grupe: rows('.sdg-g').length, deschise: rows('.sdg-gh[aria-expanded="true"]').length, randuri: rows('#sdgLista tbody tr').length,
        count: p.querySelector('#sdgCount').textContent, chips: rows('.sdg-chip').map(x => x.textContent.replace(/×/g, '').trim()),
        selD: rows('.sdg-d[aria-pressed="true"]').map(x => x.getAttribute('aria-label')), selS: rows('.sdg-s[aria-pressed="true"]').map(x => x.getAttribute('aria-label')),
        golLista: !!p.querySelector('#sdgLista .sdg-gol')
      };
    }'''
    JS_ASTEPTAT = '''() => {
      // calculul „cu ochii paginii”: aceleași PROJECTS, fără funcțiile din sectoare.js
      const U = new Map();
      PROJECTS.forEach(p => { const k = p.id ? 'id:' + p.id : 'nm:' + p.denumire + '|' + p.donator; const g = U.get(k) || { ang: 0, deb: 0, d: new Set(), s: new Set(), an: p.an }; g.ang += p.ang; g.deb += p.deb;
        p.donatori.forEach(d => g.d.add(d)); (p.sectoare.length ? p.sectoare.map(s => s.nume) : ['Nespecificat']).forEach(s => g.s.add(s)); U.set(k, g); });
      const don = {}, sec = {};
      U.forEach(g => { g.d.forEach(d => { don[d] = (don[d] || 0) + g.ang; }); g.s.forEach(s => { sec[s] = (sec[s] || 0) + g.ang; }); });
      // și numerele paginii principale: RAW (an × donator) și aggregateBySector
      const raw = {}; RAW.forEach(r => { raw[r.donator] = (raw[r.donator] || 0) + r.Angajamente; });
      const bySec = {}; aggregateBySector(PROJECTS).forEach(o => { bySec[o.nume] = o.ang; });
      return { proiecte: U.size, ang: [...U.values()].reduce((s, g) => s + g.ang, 0), don: don, sec: sec, raw: raw, bySec: bySec };
    }'''

    def etichete(pg, sel):
        return pg.evaluate("(sel) => [...document.querySelectorAll(sel)].map(g => g.getAttribute('aria-label'))", sel)

    def tinta(pg, tip, regex):
        """indexul rândului (donator 'd' / sector 's') a cărui etichetă se potrivește cu expresia"""
        return pg.evaluate("([tip, rx]) => [...document.querySelectorAll(tip === 'd' ? '.sdg-d' : '.sdg-s')].findIndex(g => new RegExp(rx).test(g.getAttribute('aria-label')))", [tip, regex])

    try:
        with sync_playwright() as p:
            b = p.chromium.launch()
            for limba in ('ro', 'en'):
                print(f'  — {limba.upper()} —')
                ctx = b.new_context(viewport={'width': 1440, 'height': 1000}, accept_downloads=True)
                ctx.grant_permissions(['clipboard-read', 'clipboard-write'], origin=baza.rstrip('/'))
                pg = ctx.new_page()
                pg.on('pageerror', lambda e: ERORI.append(str(e)[:300]))
                pg.on('console', lambda m: ERORI.append(m.text[:300]) if m.type == 'error' and 'Failed to load resource' not in m.text else None)
                pg.route('**/*', lambda r: r.continue_() if r.request.url.startswith(baza) else r.abort())
                pg.goto(baza + 'index.html', wait_until='networkidle', timeout=120000)
                pg.wait_for_timeout(3500)
                pg.evaluate('window.finishIntro && finishIntro()')
                if limba == 'en':
                    pg.evaluate("setLanguage('en')"); pg.wait_for_timeout(1200)
                pg.evaluate('showAdvancedView()'); pg.wait_for_timeout(2500)
                S = lambda: pg.evaluate(JS_STARE)
                ast = pg.evaluate(JS_ASTEPTAT)
                st = S()
                verifica(f'{limba}: panoul apare în „Analize avansate”, cu titlul în limba aleasă', pg.locator('#sdgPanel h2 span').first.text_content().startswith('Donatori →' if limba == 'ro' else 'Donors →'), pg.locator('#sdgPanel h2 span').first.text_content())
                verifica(f'{limba}: diagrama are 12 donatori + „Alți donatori” și toate sectoarele cu sumă', st['nD'] == 13 and st['nS'] >= 20 and st['legaturi'] > 40, (st['nD'], st['nS'], st['legaturi']))
                verifica(f'{limba}: lista are un grup pe sector, toate închise', st['grupe'] >= 20 and st['deschise'] == 0, (st['grupe'], st['deschise']))
                verifica(f'{limba}: numărul de proiecte din antet = proiectele unice din pagină ({ast["proiecte"]})', st['count'].replace('.', '').replace(',', '') == str(ast['proiecte']), st['count'])
                # --- cifrele din diagramă = cifrele din restul paginii
                nod = pg.evaluate('''() => { const c = document.getElementById('sdgPanel'); return null; }''')
                diag = pg.evaluate('''() => { const out = {d: {}, s: {}}; document.querySelectorAll('.sdg-d, .sdg-s').forEach(g => { out[g.classList.contains('sdg-d') ? 'd' : 's'][g.getAttribute('aria-label')] = g.querySelector('.val').textContent; }); return out; }''')
                top_don = sorted(ast['don'].items(), key=lambda kv: -kv[1])[:3]
                top_sec = sorted(ast['sec'].items(), key=lambda kv: -kv[1])[:3]
                verifica(f'{limba}: totalul fiecărui donator din diagramă = „Top donatori” din pagina principală (RAW)', all(abs(ast['don'][k] - ast['raw'][k]) < 1 for k in ast['don'] if k in ast['raw']) and len(top_don) == 3, top_don)
                verifica(f'{limba}: totalul fiecărui sector din diagramă = panoul „Distribuție pe sectoare” din pagina principală (aggregateBySector)', all(abs(ast['sec'][k] - ast['bySec'][k]) < 1 for k in ast['sec'] if k in ast['bySec']) and len(ast['sec']) == len(ast['bySec']), (len(ast['sec']), len(ast['bySec'])))
                nod_d = pg.evaluate('''() => { const a = window.SectoareDonatori; const u = a.unice(PROJECTS); const g = a.agrega(u, {metric: 'ang', nD: 12, nS: 30}); return {d: g.nodD.map(x => [x.cheie, x.ang]), s: g.nodS.map(x => [x.cheie, x.ang])}; }''')
                verifica(f'{limba}: nodurile din diagramă au sumele din pagină (fiecare donator și fiecare sector afișat)',
                         all(k == '§alti§' or abs(v - ast['don'][k]) < 1 for k, v in nod_d['d']) and all(k == '§alte§' or abs(v - ast['sec'][k]) < 1 for k, v in nod_d['s']), nod_d['d'][:3])
                # --- bară de control
                pg.locator('#sdgMetric button[data-m="deb"]').click(); pg.wait_for_timeout(500)
                st2 = S()
                verifica(f'{limba}: butonul „Debursări” schimbă măsura (aria-pressed) și redesenează', st2['metric'] == 'deb' and pg.locator('#sdgMetric button[data-m="deb"]').get_attribute('aria-pressed') == 'true' and pg.locator('#sdgMetric button[data-m="ang"]').get_attribute('aria-pressed') == 'false', st2)
                pg.locator('#sdgMetric button[data-m="ang"]').click(); pg.wait_for_timeout(400)
                # --- perioada
                pg.select_option('#sdgDe', '2015'); pg.wait_for_timeout(500)
                pg.select_option('#sdgPana', '2020'); pg.wait_for_timeout(500)
                st3 = S()
                asteptat_per = pg.evaluate("() => PROJECTS.filter(p => p.an !== 'NA' && p.an >= 2015 && p.an <= 2020).length")
                verifica(f'{limba}: perioada 2015–2020 păstrează doar proiectele care au început atunci ({asteptat_per})', st3['count'].replace('.', '') == str(asteptat_per), (st3['count'], asteptat_per))
                optiuni = pg.evaluate("() => [...document.querySelectorAll('#sdgDe option')].filter(o => o.disabled).map(o => o.value)")
                verifica(f'{limba}: în „De la” nu se pot alege ani după „Până la” (opțiunile sunt dezactivate)', len(optiuni) > 0 and all(int(v) > 2020 for v in optiuni), optiuni[:3])
                pg.select_option('#sdgDe', ''); pg.select_option('#sdgPana', ''); pg.wait_for_timeout(500)
                # --- clic pe sector
                i = tinta(pg, 's', 'Educa|Education')
                pg.locator('.sdg-s').nth(i).click(); pg.wait_for_timeout(500)
                st4 = S()
                gr_edu = pg.evaluate("() => PROJECTS.filter(p => p.sectoare.some(s => s.nume === 'Educație')).length")
                verifica(f'{limba}: clic pe un sector → lista arată doar sectorul lui, deschis, cu toate proiectele lui ({gr_edu})', st4['grupe'] == 1 and st4['deschise'] == 1 and st4['count'].replace('.', '') == str(gr_edu) and len(st4['selS']) == 1, st4)
                verifica(f'{limba}: filtrul apare ca etichetă cu „×”', len(st4['chips']) == 1 and ('Educa' in st4['chips'][0] or 'Education' in st4['chips'][0]), st4['chips'])
                verifica(f'{limba}: se afișează cel mult 100 de proiecte odată, cu buton pentru restul', st4['randuri'] == min(100, gr_edu) and (gr_edu <= 100 or pg.locator('[data-sdg-mai]').count() == 2), st4['randuri'])
                pg.locator('[data-sdg-mai][data-n="100"]').first.click(); pg.wait_for_timeout(300)
                verifica(f'{limba}: „Încă 100” arată încă 100 de proiecte', S()['randuri'] == min(200, gr_edu), S()['randuri'])
                # --- clic pe un donator care nu are proiecte în sectorul ales: alegerea veche se lasă
                antet_nedorit = pg.evaluate('''() => { const g = window.SectoareDonatori, u = g.unice(PROJECTS), a = g.agrega(u, {metric: 'ang', nD: 12, nS: 30, fixS: ['Educație']});
                  const fara = a.nodD.filter(x => !x.alt && !a.legaturi.some(l => l.d === x.cheie && l.s === 'Educație'));
                  return fara.length ? fara[0].cheie : null; }''')
                if antet_nedorit:
                    j = pg.evaluate("(k) => { const g = window.SectoareDonatori, u = g.unice(PROJECTS), a = g.agrega(u, {metric: 'ang', nD: 12, nS: 30, fixS: ['Educație']}); return a.nodD.findIndex(x => x.cheie === k); }", antet_nedorit)
                    pg.locator('.sdg-d').nth(j).click(); pg.wait_for_timeout(500)
                    st5 = S()
                    verifica(f'{limba}: clic pe un donator fără proiecte în sectorul ales → rămâne doar donatorul, lista nu e goală', st5['donator'] == antet_nedorit and st5['sector'] == '' and not st5['golLista'] and st5['grupe'] >= 1, st5)
                    pg.locator('.sdg-d').nth(j).click(); pg.wait_for_timeout(300)
                    verifica(f'{limba}: al doilea clic pe același donator îl scoate', S()['donator'] == '', S())
                # --- clic pe o linie → ambele capete
                pg.evaluate("window.__sdgStare.donator = ''; window.__sdgStare.sector = ''; window.__renderSectoare()"); pg.wait_for_timeout(400)
                pg.evaluate('''() => { const l = document.querySelector('.sdg-hit'); l.dispatchEvent(new MouseEvent('click', {bubbles: true})); }'''); pg.wait_for_timeout(500)
                st6 = S()
                verifica(f'{limba}: clic pe o linie alege și donatorul, și sectorul ei; lista arată proiectele lor comune', st6['donator'] != '' and st6['sector'] != '' and st6['grupe'] == 1 and len(st6['chips']) == 2 and not st6['golLista'], st6)
                pg.locator('[data-sdg-clear="all"]').click(); pg.wait_for_timeout(400)
                st7 = S()
                verifica(f'{limba}: „Resetează selecția” scoate ambele filtre și închide etichetele', st7['donator'] == '' and st7['sector'] == '' and st7['chips'] == [] and st7['grupe'] >= 20, st7)
                # --- singular: o pereche donator–sector cu un singur proiect
                k1 = pg.evaluate("""() => { const g = window.SectoareDonatori, a = g.agrega(g.unice(PROJECTS), { metric: 'ang', nD: 12, nS: 30 }); return a.legaturi.findIndex(x => x.n === 1); }""")
                if k1 >= 0:
                    pg.evaluate("(k) => document.querySelectorAll('.sdg-hit')[k].dispatchEvent(new MouseEvent('click', {bubbles: true}))", k1); pg.wait_for_timeout(500)
                    sum1 = pg.locator('#sdgLista .sdg-sum').text_content()
                    foot1 = pg.locator('#sdgLista tfoot td').first.text_content()
                    verifica(f'{limba}: o pereche cu un singur proiect scrie „1 sector”, „1 proiect” (nu „1 sectoare”, „1 proiecte”)',
                             ('1 sector' in sum1 and '1 sectoare' not in sum1 and '1 proiect unic' in sum1 and '(1 proiect)' in foot1) if limba == 'ro' else
                             ('1 sector' in sum1 and '1 sectors' not in sum1 and '1 unique project' in sum1 and '(1 project)' in foot1), (sum1[:80], foot1))
                    pg.locator('[data-sdg-clear="all"]').click(); pg.wait_for_timeout(400)
                # --- cu mai multe: „378 de proiecte unice” în română
                pg.locator('.sdg-s').nth(tinta(pg, 's', 'Educa|Education')).click(); pg.wait_for_timeout(500)
                sum2 = pg.locator('#sdgLista .sdg-sum').text_content()
                verifica(f'{limba}: pentru 378 de proiecte româna scrie „de”, engleza nu', ('378 de proiecte unice' in sum2) if limba == 'ro' else ('378 unique projects' in sum2), sum2[:90])
                pg.locator('[data-sdg-clear="all"]').click(); pg.wait_for_timeout(400)
                # --- donator ales din listă (și unul din afara primilor 12)
                optiuni_d = pg.evaluate("() => [...document.querySelectorAll('#sdgDonator option')].map(o => [o.value, o.textContent])")
                verifica(f'{limba}: lista de donatori conține toți donatorii cu sumă (nu doar primii 12), cu numărul de proiecte', len(optiuni_d) > 100 and all(re.search(r'\(\d+\)$', t) for v, t in optiuni_d[1:-1]), len(optiuni_d))
                mic = optiuni_d[60][0]
                pg.select_option('#sdgDonator', mic); pg.wait_for_timeout(600)
                st8 = S()
                verifica(f'{limba}: un donator din afara primilor 12, ales din listă, apare în diagramă (rând în plus) și filtrează lista', st8['donator'] == mic and st8['nD'] == 14 and len(st8['selD']) == 1 and st8['grupe'] >= 1, st8)
                pg.select_option('#sdgDonator', ''); pg.wait_for_timeout(400)
                # --- tastatura
                pg.locator('.sdg-s').nth(2).focus(); pg.keyboard.press('Enter'); pg.wait_for_timeout(500)
                st9 = S()
                verifica(f'{limba}: Enter pe un sector focalizat îl alege, iar focusul rămâne pe același rând după redesenare', st9['sector'] != '' and pg.evaluate("document.activeElement && document.activeElement.classList.contains('sdg-s')"), st9)
                pg.keyboard.press('Escape'); pg.wait_for_timeout(400)
                verifica(f'{limba}: Escape scoate selecția', S()['sector'] == '', S())
                pg.locator('.sdg-d').nth(1).focus(); pg.keyboard.press('Space'); pg.wait_for_timeout(500)
                verifica(f'{limba}: bara de spațiu alege un donator', S()['donator'] != '')
                pg.keyboard.press('Escape'); pg.wait_for_timeout(300)
                # --- evidențiere la trecerea cursorului, fără redesenare
                pg.locator('.sdg-d').nth(0).hover(); pg.wait_for_timeout(300)
                hov = pg.evaluate("() => ({ aprinse: [...document.querySelectorAll('.sdg-link')].filter(l => +l.getAttribute('stroke-opacity') > 0.5).length, stinse: [...document.querySelectorAll('.sdg-link')].filter(l => +l.getAttribute('stroke-opacity') < 0.1).length, tip: document.getElementById('advTooltip').style.display, tipText: document.getElementById('advTooltip').innerText })")
                verifica(f'{limba}: trecerea cursorului peste un donator luminează liniile lui, estompează restul și arată cifrele', hov['aprinse'] > 0 and hov['stinse'] > hov['aprinse'] and hov['tip'] == 'block' and 'EUR' in hov['tipText'], hov)
                pg.mouse.move(5, 5); pg.wait_for_timeout(300)
                dup = pg.evaluate("() => [...document.querySelectorAll('.sdg-link')].filter(l => Math.abs(+l.getAttribute('stroke-opacity') - 0.2) < 0.001).length")
                verifica(f'{limba}: la plecarea cursorului liniile revin la starea obișnuită', dup == pg.evaluate("() => document.querySelectorAll('.sdg-link').length"), dup)
                # --- grup deschis / închis, „Deschide toate”
                pg.locator('.sdg-gh').nth(1).click(); pg.wait_for_timeout(300)
                verifica(f'{limba}: clic pe antetul unui grup îl deschide (aria-expanded) și arată tabelul', pg.locator('.sdg-gh').nth(1).get_attribute('aria-expanded') == 'true' and pg.locator('#sdgGb1 tbody tr').count() > 0)
                pg.locator('.sdg-gh').nth(1).click(); pg.wait_for_timeout(300)
                verifica(f'{limba}: al doilea clic îl închide și golește conținutul', pg.locator('.sdg-gh').nth(1).get_attribute('aria-expanded') == 'false' and pg.locator('#sdgGb1').inner_html() == '')
                pg.locator('#sdgToate').click(); pg.wait_for_timeout(800)
                s10 = S()
                verifica(f'{limba}: „Deschide toate” deschide toate grupurile', s10['deschise'] == s10['grupe'] and s10['randuri'] > 500, (s10['deschise'], s10['grupe'], s10['randuri']))
                pg.locator('#sdgToate').click(); pg.wait_for_timeout(500)
                verifica(f'{limba}: și le închide la al doilea clic', S()['deschise'] == 0)
                # --- AMP ID-urile devin legături (când corespondența e cunoscută) și titlurile apar în limba aleasă
                pg.locator('.sdg-gh').nth(0).click(); pg.wait_for_timeout(500)
                celula = pg.evaluate("() => { const t = document.querySelector('#sdgGb0 tbody tr'); return { id: t.children[0].textContent.trim(), titlu: t.children[1].textContent.trim(), donator: t.children[2].textContent.trim() }; }")
                verifica(f'{limba}: fiecare rând are AMP ID, titlu și donator', bool(celula['id']) and bool(celula['titlu']) and bool(celula['donator']), celula)
                pg.locator('.sdg-gh').nth(0).click(); pg.wait_for_timeout(200)

                # --- exporturile
                def deschide_meniu():
                    pg.locator('#sdgPanel > .panel-head .roata-panou').first.click(); pg.wait_for_timeout(300)

                def descarca(actiune):
                    deschide_meniu()
                    with pg.expect_download(timeout=60000) as d:
                        pg.locator('.meniu-panou [data-actiune="%s"]' % actiune).click()
                    cale = DESCARCARI / (limba + '_' + actiune + '_' + d.value.suggested_filename)
                    d.value.save_as(str(cale))
                    return cale, d.value.suggested_filename

                verifica(f'{limba}: primul antet are roata ⚙, al doilea (lista) nu', pg.locator('#sdgPanel .unealta-panou').count() == 1)
                cale, nume_f = descarca('xlsx')
                verifica(f'{limba}: ⚙ → Excel dă un fișier .xlsx cu numele panoului', nume_f.endswith('.xlsx') and ('donatori' in nume_f.lower() or 'donors' in nume_f.lower()), nume_f)
                verifica(f'{limba}: fișierul Excel e valid (arhivă, XML bine format)', zipfile.is_zipfile(cale) and not parti_xml_valide(cale), parti_xml_valide(cale))
                wb = openpyxl.load_workbook(cale)
                nume_foi = wb.sheetnames
                n_grupe = S()['grupe']
                verifica(f'{limba}: o foaie de rezumat, una cu matricea, una cu toate proiectele și câte una pe sector ({3 + n_grupe})', len(nume_foi) == 3 + n_grupe, (len(nume_foi), n_grupe))
                verifica(f'{limba}: numele foilor sunt în limba aleasă', (nume_foi[0] == 'Rezumat pe sectoare' and nume_foi[2] == 'Toate proiectele') if limba == 'ro' else (nume_foi[0] == 'Summary by sector' and nume_foi[2] == 'All projects'), nume_foi[:3])
                ws = wb[nume_foi[0]]
                verifica(f'{limba}: titlul, rândul de context (sursa, perioada, măsura) și antetul sunt pe foaia de rezumat', bool(ws['A1'].value) and 'AMP' in (ws['A2'].value or '') and ('toți anii' in ws['A2'].value or 'all years' in ws['A2'].value) and ws['A4'].value in ('Sector',), (ws['A1'].value, ws['A2'].value, ws['A4'].value))
                total_unic = pg.evaluate("() => PROJECTS.length")
                verifica(f'{limba}: totalul din rezumat = proiectele unice din pagină ({total_unic})', ws.cell(row=5 + n_grupe, column=2).value == total_unic, ws.cell(row=5 + n_grupe, column=2).value)
                ws_pl = wb[nume_foi[2]]
                n_perechi = sum(int(r[1]) for r in ws.iter_rows(min_row=5, max_row=4 + n_grupe, max_col=2, values_only=True))
                rand_total = next((i for i, r in enumerate(ws_pl.iter_rows(min_col=1, max_col=1, values_only=True), start=1) if str(r[0] or '').upper().startswith('TOTAL')), None)
                verifica(f'{limba}: foaia „Toate proiectele” are un rând pentru fiecare pereche proiect–sector ({n_perechi}), apoi rândul de total', rand_total == 5 + n_perechi and ws_pl.cell(row=4, column=1).value == 'Sector', (rand_total, n_perechi))
                matr = wb[nume_foi[1]]
                verifica(f'{limba}: foaia cu matricea are donatorii pe rânduri și sectoarele pe coloane', matr.max_column >= 10 and matr.max_row > 50, (matr.max_row, matr.max_column))
                ws_s = wb[nume_foi[3]]
                rand_ts = next((i for i, r in enumerate(ws_s.iter_rows(min_col=1, max_col=1, values_only=True), start=1) if str(r[0] or '').lower() == 'total'), None)
                lnk = [c for row in ws_s.iter_rows(min_row=5, max_row=min(ws_s.max_row, 9), max_col=1) for c in row if c.hyperlink]
                f_ang = ws_s.cell(row=rand_ts, column=5).value if rand_ts else None
                f_deb = ws_s.cell(row=rand_ts, column=6).value if rand_ts else None
                verifica(f'{limba}: foile de sector au hyperlink pe AMP ID și total ca formulă (SUBTOTAL peste toate rândurile)', bool(rand_ts) and str(f_ang) == f'=SUBTOTAL(109,E5:E{rand_ts - 1})' and str(f_deb) == f'=SUBTOTAL(109,F5:F{rand_ts - 1})' and len(lnk) >= 1, (rand_ts, f_ang, f_deb, len(lnk)))

                cale, nume_f = descarca('csv')
                text = cale.read_text(encoding='utf-8-sig')
                linii = list(csv.reader(io.StringIO(text), delimiter=';'))
                verifica(f'{limba}: ⚙ → CSV: lista plată, cu antet și un rând pentru fiecare pereche proiect–sector', nume_f.endswith('.csv') and len(linii[0]) == 7 and all(len(r) == 7 for r in linii) and len(linii) - 1 == n_perechi, (nume_f, linii[0], len(linii)))
                # --- butonul Excel de lângă listă
                with pg.expect_download(timeout=60000) as d:
                    pg.locator('#sdgExcel').click()
                cale2 = DESCARCARI / (limba + '_lista_' + d.value.suggested_filename); d.value.save_as(str(cale2))
                wb2 = openpyxl.load_workbook(cale2)
                verifica(f'{limba}: butonul „Excel” din antetul listei dă același fișier cu mai multe foi', wb2.sheetnames == nume_foi, (wb2.sheetnames[:4], nume_foi[:4]))
                pg.wait_for_timeout(2500)
                verifica(f'{limba}: butonul își recapătă textul după descărcare', 'Excel' in pg.locator('#sdgExcel').text_content(), pg.locator('#sdgExcel').text_content())
                # --- exportul reflectă selecția
                i = tinta(pg, 's', 'Educa|Education')
                pg.locator('.sdg-s').nth(i).click(); pg.wait_for_timeout(500)
                cale3, _ = descarca('xlsx')
                wb3 = openpyxl.load_workbook(cale3)
                verifica(f'{limba}: cu un sector ales, fișierul conține doar acel sector (3 foi generale + o foaie de sector)', len(wb3.sheetnames) == 4, wb3.sheetnames)
                ctx3 = wb3[wb3.sheetnames[0]]['A2'].value
                verifica(f'{limba}: rândul de context spune ce sector a fost ales', ('Educație' in ctx3) if limba == 'ro' else ('Education' in ctx3), ctx3)
                pg.locator('[data-sdg-clear="all"]').click(); pg.wait_for_timeout(300)
                # --- copiere ca imagine: doar diagrama, nu și lista
                pg.locator('.sdg-gh').nth(0).click(); pg.locator('.sdg-gh').nth(1).click(); pg.wait_for_timeout(300)
                deschide_meniu()
                pg.locator('.meniu-panou [data-actiune="copiaza"]').click()
                pg.wait_for_timeout(6000)
                dim = pg.evaluate('''async () => { try { const it = await navigator.clipboard.read(); const blob = await it[0].getType('image/png'); const bmp = await createImageBitmap(blob); return {w: bmp.width, h: bmp.height}; } catch(e) { return {err: String(e)}; } }''')
                alt_panou = pg.evaluate("() => { const p = document.getElementById('sdgPanel'); const cap = document.getElementById('sdgListaCap'); return {sus: Math.round(cap.getBoundingClientRect().top - p.getBoundingClientRect().top), total: Math.round(p.getBoundingClientRect().height), dpr: window.devicePixelRatio}; }")
                if 'err' in dim:
                    # fără clipboard în acest mediu, imaginea se descarcă (a doua cale a funcției)
                    print('    (clipboard indisponibil:', dim['err'][:80], ')')
                    verifica(f'{limba}: copierea ca imagine nu dă erori', not ERORI, ERORI[-2:])
                else:
                    verifica(f'{limba}: imaginea copiată conține doar diagrama (fără lista de sub ea)', abs(dim['h'] / max(2, alt_panou['dpr']) - alt_panou['sus']) < 40 and dim['h'] / max(2, alt_panou['dpr']) < alt_panou['total'] * 0.7, (dim, alt_panou))
                ctx.close()
            b.close()
    finally:
        shutil.rmtree(DESCARCARI, ignore_errors=True)
    verifica('browser: nicio eroare JavaScript în timpul testelor', not ERORI, ERORI[:3])

print()
if picat:
    print(f'{len(picat)} teste au picat:')
    for n in picat:
        print('  -', n)
    sys.exit(1)
print('Toate testele panoului „Donatori → sectoare” au trecut.')
