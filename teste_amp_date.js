#!/usr/bin/env node
/* Testele pentru amp-date.js (datele de început și de finalizare ale proiectelor, luate din AMP): citirea datelor, arhiva, raportul live (CSV),
   unirea lor, potrivirea cu rândurile din registru și încărcarea cu eșecuri simulate. La sfârșit, o rulare pe arhiva reală și pe registrul real.
   Rulare:  node teste_amp_date.js */
const fs = require('fs'), path = require('path');
const LA = require('./legatura-amp.js');
global.LegaturaAmp = LA;
const A = require('./amp-date.js');

let ok = 0, esuate = [];
function verifica(nume, conditie, detaliu) {
  if (conditie) { ok++; console.log('  ok   ' + nume); }
  else { esuate.push(nume); console.log('  PICĂ ' + nume + (detaliu !== undefined ? '  → ' + JSON.stringify(detaliu) : '')); }
}
const egal = (nume, a, b) => verifica(nume, JSON.stringify(a) === JSON.stringify(b), { primit: a, asteptat: b });

(async function () {

console.log('Date AMP');
egal('zi/lună/an → AAAA-LL-ZZ', ['15/09/2020', '5/9/2020', '15.09.2020', '15-09-2020', '2020-09-15', '2020-09-15 00:00:00', '2020-09-15T10:00:00Z', ' 15/09/2020 '].map(x => A.dataAmp(x)), Array(8).fill('2020-09-15').map((x, i) => i === 1 ? '2020-09-05' : x));
egal('luna prima, când exportul o cere', [A.dataAmp('09/15/2020', 'mdy'), A.dataAmp('09/15/2020'), A.dataAmp('03/04/2020', 'mdy')], ['2020-09-15', '', '2020-03-04']);
egal('date care nu există sau nu se înțeleg → gol', ['31/02/2020', '00/01/2020', '15/13/2020', '15/09/1949', '15/09/2101', 'ieri', '', null, undefined, '15/09/20'].map(x => A.dataAmp(x)), Array(10).fill(''));
egal('ordinea datelor se deduce din valori: zi/lună/an implicit, lună/zi/an când se vede', [A.ordineaDatelor(['15/09/2020', '03/04/2021']), A.ordineaDatelor(['09/15/2020', '03/04/2021']), A.ordineaDatelor(['03/04/2021']), A.ordineaDatelor([])], ['dmy', 'mdy', 'dmy', 'dmy']);

console.log('\nArhiva');
const ARH = [
  { id: '8721152514657', t: 'Moldova Higher Education Project', d: ['Banca Mondială'], ds: '15/09/2020', de: '30/04/2026', vp: 0, y: { 2020: [1000, 100], 2021: [500, 200] } },
  { id: '2', t: 'Proiect fără date', d: ['UE'], ds: '', de: '', y: { 2019: [10, 0], '12': [5, 5] } },
  { id: '3', t: 'Doar sfârșit', d: [], ds: '', de: '31/12/2024', y: {} },
  { id: '', t: 'fără id' }, null
];
const PA = A.dinArhiva(ARH);
egal('arhiva: câte un proiect pentru fiecare înregistrare cu id', PA.map(p => p.id), ['8721152514657', '2', '3']);
egal('arhiva: datele în AAAA-LL-ZZ, sumele pe ani adunate, anul începutului', [PA[0].ds, PA[0].de, PA[0].ang, PA[0].deb, PA[0].inceput, PA[0].src], ['2020-09-15', '2026-04-30', 1500, 300, 2020, 'arhiva']);
egal('arhiva: fără dată de început, anul vine din primul an cu bani; chei de an stricate nu strică', [PA[1].ds, PA[1].inceput, PA[1].ang], ['', 2019, 15]);
egal('arhiva: donatori și titluri', [PA[0].donatori, PA[0].titluri, PA[2].donatori, PA[2].de], [['Banca Mondială'], ['Moldova Higher Education Project'], [], '2024-12-31']);

console.log('\nRaportul live (CSV)');
const CSV_EN = [
  'AMP ID,Project Title,Donor Agency,Actual Start Date,Proposed Completion Date,Funding 2020 Actual Commitments Total,Funding 2020 Actual Disbursements Total,Funding 2021 Actual Commitments Total,Funding 2021 Actual Disbursements Total,Totals Actual Commitments Total,Totals Actual Disbursements Total',
  '101,"Project, with comma",Banca Mondială,15/09/2020,30/04/2026,"1,000,000",200000,500000,100000,2500000,300000',
  '102,Alt proiect,UE,01/03/2021,,0,0,700000,0,700000,0',
  '102,Alt proiect,Germania,,31/12/2027,0,0,300000,0,300000,0',
  '102,Alt proiect,Germania,,31/12/2027,0,0,300000,0,300000,0',
  '103,Fără date,BEI,31/02/2020,x,0,0,0,0,0,0',
  ''
].join('\n');
let L = A.dinCsv(CSV_EN);
egal('CSV: un proiect pe AMP ID', L.proiecte.map(p => p.id), ['101', '102', '103']);
egal('CSV: titlul cu virgulă în ghilimele, donatorul, datele', [L.proiecte[0].titluri, L.proiecte[0].donatori, L.proiecte[0].ds, L.proiecte[0].de, L.proiecte[0].src], [['Project, with comma'], ['Banca Mondială'], '2020-09-15', '2026-04-30', 'live']);
egal('CSV: sumele pe ani; banii din afara anilor raportului se iau din totalul raportului', [L.proiecte[0].ang, L.proiecte[0].deb, L.proiecte[0].inceput], [2500000, 300000, 2020]);
egal('CSV: același AMP ID pe mai multe rânduri: se adună, donatorii se unesc, rândul identic se numără o dată, prima dată găsită rămâne',
     [L.proiecte[1].ang, L.proiecte[1].donatori, L.proiecte[1].ds, L.proiecte[1].de], [1000000, ['UE | Germania'], '2021-03-01', '2027-12-31']);
egal('CSV: dată care nu există sau nu se înțelege → gol', [L.proiecte[2].ds, L.proiecte[2].de], ['', '']);
egal('CSV: coloanele de date și de sume recunoscute', [L.areDate, L.coloaneSume], [true, 4]);
const CSV_RO = [
  'ID PGA;Titlul proiectului;Organizație finanțatoare;Data efectivă de începere;Data propusă de terminare;Finanțare 2022 Angajamente efective Total;Finanțare 2022 Debursări efective Total',
  '201;Titlu românesc;Uniunea Europeană;1/2/2022;28/02/2025;1000;50'
].join('\r\n');
L = A.dinCsv(CSV_RO);
egal('CSV în română, separat prin „;”, cu ID PGA', [L.proiecte[0].id, L.proiecte[0].ds, L.proiecte[0].de, L.proiecte[0].ang, L.proiecte[0].deb, L.coloaneSume], ['201', '2022-02-01', '2025-02-28', 1000, 50, 2]);
L = A.dinCsv('AMP ID,Project Title,Donor Agency,Funding 2021 Actual Commitments Total\n301,T,UE,5');
egal('CSV fără coloane de date: se spune, ca datele să rămână cele din arhivă', [L.areDate, L.proiecte[0].ds, L.proiecte[0].de], [false, '', '']);
egal('CSV: fără coloana AMP ID sau fără rânduri → eroare, nu rezultat gol', [(() => { try { A.dinCsv('A,B\n1,2'); return 'fără eroare'; } catch (e) { return e.message; } })(), (() => { try { A.dinCsv('AMP ID,Project Title'); return 'fără eroare'; } catch (e) { return e.message; } })()],
     ['CSV live fără coloana „AMP ID”', 'CSV live fără rânduri de date']);
egal('CSV cu luna prima în date (se vede din valori)', (() => { const x = A.dinCsv('AMP ID,Project Title,Donor Agency,Actual Start Date\n1,T,UE,09/15/2020\n2,T,UE,03/04/2021'); return x.proiecte.map(p => p.ds); })(), ['2020-09-15', '2021-03-04']);

console.log('\nUnirea arhivei cu raportul live');
const arh = [{ id: 'A', titluri: ['x'], ds: '2010-01-01', de: '2012-01-01', inceput: 2010 }, { id: 'B', titluri: ['y'], ds: '2011-01-01', de: '', inceput: 2011 }];
const liv = [{ id: 'B', titluri: ['y live'], ds: '2011-02-02', de: '2014-01-01', inceput: 2011, src: 'live' }, { id: 'C', titluri: ['z'], ds: '', de: '', inceput: null, src: 'live' }];
let U = A.uneste(arh, liv, true);
egal('la același AMP ID câștigă raportul live, cu datele lui', U.map(p => [p.id, p.ds, p.de, p.src || 'arhiva']), [['A', '2010-01-01', '2012-01-01', 'arhiva'], ['B', '2011-02-02', '2014-01-01', 'live'], ['C', '', '', 'live']]);
U = A.uneste(arh, [{ id: 'B', titluri: ['y live'], ds: '', de: '', inceput: 2011, src: 'live' }], false);
egal('raportul live fără coloane de date: datele rămân cele din arhivă', U.map(p => [p.id, p.ds, p.titluri[0]]), [['A', '2010-01-01', 'x'], ['B', '2011-01-01', 'y live']]);
U = A.uneste(arh, [{ id: 'B', titluri: ['y live'], ds: '', de: '', inceput: 2011, src: 'live' }], true);
egal('raportul live cu coloane de date, dar goale la un proiect: data goală a raportului câștigă', U.map(p => [p.id, p.ds]), [['A', '2010-01-01'], ['B', '']]);
egal('liste lipsă', [A.uneste(null, null).length, A.uneste(arh, null).length], [0, 2]);

console.log('\nPotrivirea cu rândurile din registru');
const rand = (id, scurt, parteneri, eur, an, extra) => Object.assign({
  id: id, nume: scurt, scurt: scurt, parteneri: parteneri, parteneriAcord: parteneri.split('/')[0].trim(), semnat: '01.06.' + an, primul: '01.06.' + an, ultimul: '01.06.' + an,
  suma: eur ? { v: eur, val: 'EUR', eur: eur, sursa: 'acord' } : null, alte: [], cost: null, acte: [{ act: 'HG1/' + an, data: '01.06.' + an }]
}, extra || {});
const proj = (id, titlu, donatori, ds, de, ang) => ({ id: id, titluri: [titlu], donatori: donatori, inceput: ds ? +ds.slice(0, 4) : null, ang: ang, deb: 0, vp: 0, ds: ds, de: de });
const ROWS = [
  rand('r1', 'Modernizarea serviciilor guvernamentale electronice', 'BIRD', 20e6, 2017),
  rand('r2', 'Reabilitarea sistemului termoenergetic urban Chișinău', 'BERD / BEI', 30e6, 2015),
  rand('r3', 'Infrastructura transfrontalieră pentru energie electrică', 'BEI', null, 2016),
  rand('r4', 'Programul educațional pentru învățământul profesional tehnic', 'CEB', 12e6, 2018),
  rand('r5', 'Programul educațional pentru învățământul profesional tehnic', 'CEB', 12.4e6, 2019),
  rand('r6', 'Securitatea alimentară și dezvoltarea agriculturii durabile', 'FIDA', 9e6, 2020),
  rand('r7', 'Un titlu fără nicio legătură cu proiectele din AMP', 'UE', 1e6, 2021)
];
const PROJ = [
  proj('p1', 'Modernizarea serviciilor guvernamentale electronice', ['Banca Mondială'], '2017-09-10', '2022-06-30', 20.2e6),
  proj('p2', 'Reabilitarea sistemului termoenergetic urban Chișinău', ['Banca Europeană de Investiții'], '2015-05-05', '2019-05-05', 30e6),
  proj('p3', 'Infrastructura transfrontalieră pentru energie electrică', ['Banca Europeană de Investiții'], '2016-03-01', '2020-03-01', 77e6),
  proj('p4', 'Programul educațional pentru învățământul profesional tehnic', ['Banca de Dezvoltare a Consiliului Europei'], '2019-02-02', '2024-02-02', 12.3e6),
  proj('p6', 'Securitatea alimentară și dezvoltarea agriculturii durabile', ['Fondul Internațional pentru Dezvoltare Agricolă'], '2012-01-01', '2016-01-01', 9e6)
];
let P = A.potriveste(ROWS, PROJ, {});
const nv = id => P.peAcord.get(id) && P.peAcord.get(id).nivel;
egal('legătură sigură: denumire + finanțator + sumă; datele proiectului AMP, cu id-ul și titlul lui', [nv('r1'), P.peAcord.get('r1').inceput, P.peAcord.get('r1').sfarsit, P.peAcord.get('r1').id, P.peAcord.get('r1').titlu], ['sigur', '2017-09-10', '2022-06-30', 'p1', 'Modernizarea serviciilor guvernamentale electronice']);
egal('finanțatorul rândului (parteneriAcord = BERD) nu se potrivește cu un proiect finanțat doar de BEI, deși registrul grupează „BERD / BEI”', [nv('r2'), A.potriveste([Object.assign({}, ROWS[1], { parteneriAcord: undefined })], PROJ, {}).peAcord.has('r2')], [undefined, true]);
egal('fără sumă, doar denumire + finanțator → „probabil” (datele se păstrează, dar pagina nu le folosește în tabel)', [nv('r3'), P.peAcord.get('r3') && P.peAcord.get('r3').legatura], ['probabil', 'titlu']);
egal('același proiect AMP pentru două rânduri ale aceluiași finanțator: îl primește cel cu suma mai apropiată (cel mai apropiat de 12,3 mil. e 12,4)', [nv('r4'), nv('r5')], [undefined, 'sigur']);
const P2 = A.potriveste(ROWS.map(r => r.id === 'r5' ? Object.assign({}, r, { suma: { v: 12e6, val: 'EUR', eur: 12e6, sursa: 'acord' } }) : r), PROJ.map(p => p.id === 'p4' ? Object.assign({}, p, { ang: 12e6 }) : p), {});
egal('la egalitate, niciunul din cele două rânduri nu primește datele (și se numără ca ambiguu)', [P2.peAcord.has('r4'), P2.peAcord.has('r5'), P2.numere.ambiguu >= 2], [false, false, true]);
egal('un proiect AMP care începe cu mai mult de doi ani înaintea actelor rândului nu e al lui', [nv('r6'), P.numere.prea_vechi], [undefined, 1]);
egal('rând fără legătură', nv('r7'), undefined);
egal('numerele: sigur / probabil / prea vechi', [P.numere.sigur, P.numere.probabil, P.numere.prea_vechi], [2, 1, 1]);
P = A.potriveste(ROWS, PROJ, { confirmate: { r7: ['p3'], r6: ['p6'] } });
egal('o legătură confirmată de un om e „sigur” chiar fără potrivire de nume, iar regula celor doi ani nu se aplică ei', [nv('r7'), P.peAcord.get('r7').id, nv('r6'), P.peAcord.get('r6').inceput], ['sigur', 'p3', 'sigur', '2012-01-01']);
egal('un proiect AMP fără nicio dată nu dă nimic', A.potriveste([ROWS[0]], [proj('p1', 'Modernizarea serviciilor guvernamentale electronice', ['Banca Mondială'], '', '', 20.2e6)], {}).peAcord.size, 0);
egal('doar data de sfârșit e suficientă', (() => { const x = A.potriveste([ROWS[0]], [proj('p1', 'Modernizarea serviciilor guvernamentale electronice', ['Banca Mondială'], '', '2022-06-30', 20.2e6)], {}); return [x.peAcord.get('r1').inceput, x.peAcord.get('r1').sfarsit]; })(), ['', '2022-06-30']);
egal('fără rânduri sau fără proiecte: gol, fără excepție', [A.potriveste([], PROJ, {}).peAcord.size, A.potriveste(ROWS, [], {}).peAcord.size], [0, 0]);

console.log('\nÎncărcarea (cu rețea simulată)');
const CSV_LIVE = [
  'AMP ID,Project Title,Donor Agency,Actual Start Date,Proposed Completion Date,Funding 2018 Actual Commitments Total,Funding 2018 Actual Disbursements Total',
  'p1,Modernizarea serviciilor guvernamentale electronice,Banca Mondială,11/09/2017,01/07/2023,20200000,1000'
].join('\n');
const ARH_MIN = [{ id: 'p1', t: 'Modernizarea serviciilor guvernamentale electronice', d: ['Banca Mondială'], ds: '10/09/2017', de: '30/06/2022', y: { 2018: [20200000, 0] } }];
const raspuns = (corp, status) => ({ ok: (status || 200) < 400, status: status || 200, text: async () => corp });
const chemari = [];
const stari = [];
let R1 = await A.incarca({ acorduri: ROWS, arhiva: ARH_MIN, fetch: async (u, o) => { chemari.push([u, o]); return raspuns(CSV_LIVE); }, onStare: s => stari.push(s.faza) });
egal('încărcare reușită: raportul live înlocuiește arhiva la același proiect', [R1.peAcord.get('r1').inceput, R1.peAcord.get('r1').sfarsit, R1.stare.arhiva, R1.stare.live, R1.stare.eroareLive, R1.stare.eroareArhiva], ['2017-09-11', '2023-07-01', 1, 1, '', '']);
egal('cererea: POST spre raportul 661, cu interogarea în corp', [chemari[0][0], chemari[0][1].method, chemari[0][1].body.indexOf('query=') === 0, chemari[0][1].headers['Content-Type']], ['https://amp.vivi.md/rest/data/saikureport/export/csv/661?language=ro', 'POST', true, 'application/x-www-form-urlencoded']);
egal('fazele afișate pe parcurs', stari, ['start', 'potrivire', 'gata']);
egal('starea finală: numărul de legături', [R1.stare.proiecte, R1.stare.legate.sigur], [1, 1]);
R1 = await A.incarca({ acorduri: ROWS, arhiva: ARH_MIN, fetch: async () => raspuns('Eroare', 500) });
egal('raportul live pică (HTTP 500): rămâne arhiva, iar starea spune de ce', [R1.peAcord.get('r1').inceput, R1.stare.live, R1.stare.eroareLive], ['2017-09-10', null, 'HTTP 500']);
R1 = await A.incarca({ acorduri: ROWS, arhiva: ARH_MIN, fetch: async () => { throw new TypeError('Failed to fetch'); } });
egal('fără rețea: rămâne arhiva', [R1.peAcord.get('r1').inceput, R1.stare.eroareLive], ['2017-09-10', 'Failed to fetch']);
R1 = await A.incarca({ acorduri: ROWS, arhiva: ARH_MIN, termenMs: 30, fetch: (u, o) => new Promise((ok, nu) => { o.signal.addEventListener('abort', () => { const e = new Error('aborted'); e.name = 'AbortError'; nu(e); }); }) });
egal('serverul nu răspunde: termen-limită, apoi arhiva', [R1.peAcord.get('r1').inceput, /nu a răspuns/.test(R1.stare.eroareLive)], ['2017-09-10', true]);
R1 = await A.incarca({ acorduri: ROWS, arhiva: ARH_MIN, fetch: async () => raspuns('prea scurt') });
egal('răspuns gol sau prea scurt: tratat ca eroare', [R1.stare.live, /gol/.test(R1.stare.eroareLive)], [null, true]);
R1 = await A.incarca({ acorduri: ROWS, fetch: async () => raspuns(CSV_LIVE) });
egal('fără arhivă (nu se poate încărca), dar cu raport live: merge doar cu raportul', [R1.peAcord.get('r1').inceput, R1.stare.arhiva, /arhiva/.test(R1.stare.eroareArhiva)], ['2017-09-11', null, true]);
R1 = await A.incarca({ acorduri: ROWS, fetch: async () => raspuns('Eroare', 503) });
egal('nicio sursă: rezultat gol, fără excepție', [R1.peAcord.size, R1.stare.faza, !!R1.stare.eroareArhiva, !!R1.stare.eroareLive], [0, 'gata', true, true]);
R1 = await A.incarca({ acorduri: ROWS, arhiva: ARH_MIN, fetch: async () => raspuns('AMP ID,Project Title\n1,T') });
egal('raport cu coloane neașteptate: eroarea nu strică arhiva', [R1.peAcord.has('r1'), !!R1.stare.eroareLive], [true, true]);
R1 = await A.incarca({ acorduri: ROWS, arhiva: ARH_MIN, fetch: async () => raspuns(CSV_LIVE.split('\n').map((l, i) => i ? l.replace(/,\d+,\d+$/, ',0,0') : l).join('\n')), confirmari: {} , onStare: () => { throw new Error('afișarea a căzut'); } });
egal('o eroare în afișarea stării nu oprește lucrul', R1.peAcord.has('r1'), true);

console.log('\nPe arhiva și pe registrul reale');
const src = fs.readFileSync(path.join(__dirname, 'arhiva.js'), 'utf8');
const ARCH = (new Function(src.replace(/^[\s\S]*?const ARCHIVE\s*=/, 'return (').replace(/;\s*$/, ')')))();
const real = JSON.parse(fs.readFileSync(path.join(__dirname, 'date', 'acorduri_legare.json'), 'utf8'));
const PR = A.dinArhiva(ARCH);
verifica('arhiva reală: toate înregistrările intră, cu AMP ID unic', PR.length === ARCH.length && new Set(PR.map(p => p.id)).size === PR.length, [PR.length, ARCH.length]);
verifica('arhiva reală: fiecare dată e în AAAA-LL-ZZ; aproape toate proiectele au început, cele mai multe și sfârșit', PR.every(p => (!p.ds || /^\d{4}-\d{2}-\d{2}$/.test(p.ds)) && (!p.de || /^\d{4}-\d{2}-\d{2}$/.test(p.de))) &&
         PR.filter(p => p.ds).length > 2900 && PR.filter(p => p.de).length > 2300, [PR.filter(p => p.ds).length, PR.filter(p => p.de).length]);
const mod = PR.find(p => p.id === '8721152514657');
egal('proiectul „Moldova Higher Education Project” din arhivă', [mod.ds, mod.de], ['2020-09-15', '2026-04-30']);
const t0 = Date.now();
const RR = A.potriveste(real.acorduri, PR, {});
const ms = Date.now() - t0;
verifica('registrul real × arhiva: potrivirea durează sub 5 secunde (' + ms + ' ms)', ms < 5000, ms);
verifica('registrul real × arhiva: zeci de legături sigure, nicio dată în afara formei', RR.numere.sigur >= 30 && [...RR.peAcord.values()].every(v => ['sigur', 'probabil'].indexOf(v.nivel) >= 0 && (!v.inceput || /^\d{4}-\d{2}-\d{2}$/.test(v.inceput)) && (!v.sfarsit || /^\d{4}-\d{2}-\d{2}$/.test(v.sfarsit))), RR.numere);
const ids = new Set(real.acorduri.map(a => a.id));
verifica('fiecare legătură e a unui rând care există în registru', [...RR.peAcord.keys()].every(id => ids.has(id)));
// același proiect AMP la două rânduri sigure: doar la finanțatori diferiți
const pePr = new Map();
real.acorduri.forEach(a => { const v = RR.peAcord.get(a.id); if (v && v.nivel === 'sigur') (pePr.get(v.id) || pePr.set(v.id, []).get(v.id)).push(a); });
const duble = [...pePr.entries()].filter(e => {
  const fam = e[1].map(a => LA.familii(a.parteneriAcord || a.parteneri || '').sort().join('+'));
  return new Set(fam).size !== fam.length;
}).map(e => [e[0], e[1].map(a => a.id)]);
egal('niciun proiect AMP nu e dat la două rânduri sigure ale aceluiași finanțator', duble, []);
const nepl = [...RR.peAcord.entries()].filter(e => e[1].nivel === 'sigur').filter(e => {
  const a = real.acorduri.find(x => x.id === e[0]);
  const ani = (a.acte || []).map(x => +String(x.data || '').slice(-4)).filter(y => y >= 1990);
  return e[1].inceput && ani.length && +e[1].inceput.slice(0, 4) < Math.min(...ani) - 2;
}).map(e => e[0]);
egal('nicio legătură sigură nu începe cu mai mult de doi ani înaintea primului act al rândului', nepl, []);

console.log('\n' + (esuate.length ? esuate.length + ' teste au picat: ' + esuate.join('; ') : 'Toate testele au trecut (' + ok + ').'));
process.exit(esuate.length ? 1 : 0);
})().catch(function (e) { console.error(e); process.exit(2); });
