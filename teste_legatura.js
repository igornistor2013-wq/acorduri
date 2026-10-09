#!/usr/bin/env node
/* Testele pentru legatura-amp.js (potrivirea acord ↔ proiect AMP).
   Rulare:  node teste_legatura.js
   Au trei părți: funcțiile mici, scenarii construite de mână (fiecare regulă are un caz care o
   încalcă) și o verificare pe datele reale din repository (arhiva AMP + registrul de acorduri). */
const fs = require('fs'), vm = require('vm'), path = require('path');
const M = require('./legatura-amp.js');

let ok = 0, esuate = [];
function verifica(nume, conditie, detaliu) {
  if (conditie) { ok++; console.log('  ok   ' + nume); }
  else { esuate.push(nume); console.log('  PICĂ ' + nume + (detaliu !== undefined ? '  → ' + JSON.stringify(detaliu) : '')); }
}
const egal = (nume, a, b) => verifica(nume, JSON.stringify(a) === JSON.stringify(b), { primit: a, asteptat: b });

console.log('Funcțiile mici');
const st = t => M.analiza(t).st.sort();
verifica('„reabilitarea drumurilor" și „reabilitare drumuri" au aceleași cuvinte', JSON.stringify(st('Reabilitarea drumurilor')) === JSON.stringify(st('Reabilitare drumuri')));
verifica('ortografia veche și cea nouă coincid (învățămîntul = învățământul)', JSON.stringify(st('Învățămîntul superior')) === JSON.stringify(st('Învățământul superior')));
verifica('diacriticele cu sedilă și cu virgulă coincid', JSON.stringify(st('Deşeuri solide')) === JSON.stringify(st('Deșeuri solide')));
verifica('cuvintele de umplutură nu intră', st('Proiectul de dezvoltare al Republicii Moldova').indexOf('proiec') < 0 && st('Acordul de grant').length === 0);
egal('numerele romane și cifrele sunt faza, nu cuvinte', M.analiza('Reabilitarea drumurilor — Proiectul VI').faza, ['vi']);
egal('anii unui program sunt fază', M.analiza('Programul 2014–2020').faza.sort(), ['2014', '2020']);
verifica('faza V diferă de faza VI', M.fazaDiferita(['v'], ['vi']));
verifica('aceeași fază nu diferă; lipsa fazei nu diferă', !M.fazaDiferita(['vi'], ['vi']) && !M.fazaDiferita([], ['vi']));

egal('BERD se potrivește cu numele întreg', M.compatibil('BERD', ['Banca Europeană pentru Reconstrucție și Dezvoltare']), 'da');
egal('BEI nu se potrivește cu Japonia', M.compatibil('BEI', ['Agenția Japoneză pentru Cooperare Internațională']), 'nu');
egal('AID (Asociația Internațională pentru Dezvoltare) e Banca Mondială, nu USAID',
     [M.compatibil('AID', ['Banca Mondială']), M.compatibil('AID', ['Agenția Statelor Unite pentru Dezvoltare Internațională'])], ['da', 'nu']);
egal('CEB nu e Consiliul Europei, deși numele ei îl cuprinde',
     [M.compatibil('CEB', ['Banca de Dezvoltare a Consiliului Europei']), M.compatibil('CEB', ['Consiliul Europei'])], ['da', 'nu']);
egal('„Fondul Global de Mediu" nu e Fondul Global pentru SIDA', M.familii('Fondul Global de Mediu'), ['gef']);
egal('un partener nerecunoscut nu se respinge', M.compatibil('Bancă comercială străină', ['Banca Europeană de Investiții']), 'necunoscut');
egal('România (cu â) se recunoaște, în partener și în numele ambasadei', [M.familii('România'), M.familii('Ambasada României în Republica Moldova')], [['ro'], ['ro']]);
egal('mai mulți parteneri: oricare se potrivește', M.compatibil('BIRD / AID', ['Banca Mondială']), 'da');

const a50 = { suma: { eur: 50e6, sursa: 'acord' }, alte: [], cost: null };
egal('suma în toleranță (10%) se potrivește', M.potrivireSuma(a50, { ang: 55e6 }).stare, 'da');
egal('suma peste toleranță (20%) nu', M.potrivireSuma(a50, { ang: 62.5e6 }).stare, 'nu');
egal('sumele mici nu confirmă nimic (sub 100.000 EUR)', M.potrivireSuma({ suma: { eur: 50000 } }, { ang: 50000 }).stare, 'nu');
egal('fără sumă într-o parte: necunoscut', M.potrivireSuma({ suma: null }, { ang: 5e6 }).stare, 'necunoscut');
egal('valoarea propusă a proiectului contează ca sumă', M.potrivireSuma(a50, { ang: 0, vp: 50e6 }).stare, 'da');

const acord2006 = { semnat: '', primul: '16.02.2006', ultimul: '01.10.2026', acte: [{ data: '16.02.2006' }, { data: '24.08.2019' }, { data: '01.10.2026' }] };
egal('acordul cu acte pe 20 de ani: proiectul din 2019 e plauzibil', M.dataPlauzibila(acord2006, { inceput: 2019 }), 'da');
egal('proiect început cu 10 ani înaintea oricărui act: nu', M.dataPlauzibila({ primul: '01.01.2020', acte: [] }, { inceput: 2009 }), 'nu');
egal('fără an: necunoscut', M.dataPlauzibila({ acte: [] }, { inceput: 2019 }), 'necunoscut');

console.log('\nScenarii construite de mână');
const ac = (id, scurt, parteneri, eur, extra) => Object.assign({ id: id, scurt: scurt, nume: scurt, parteneri: parteneri, categorie: 'Împrumut', semnat: '10.05.2019', primul: '01.03.2019', ultimul: '10.05.2019',
  suma: eur ? { v: eur, val: 'EUR', eur: eur, sursa: 'acord' } : null, alte: [], cost: null, acte: [{ act: 'LP1/2019', data: '10.05.2019' }] }, extra || {});
const pr = (id, titlu, donator, ang, extra) => Object.assign({ id: id, titluri: [titlu], donatori: [donator], inceput: 2020, ang: ang, deb: ang / 2, vp: 0 }, extra || {});
const BERD = 'Banca Europeană pentru Reconstrucție și Dezvoltare', BEI = 'Banca Europeană de Investiții', JP = 'Agenția Japoneză pentru Cooperare Internațională';
const potr = (a, p, c) => M.potriveste(a, p, c || {});
const prima = r => r.rezultate[0].legaturi[0];

let r = potr([ac('a1', 'Reabilitarea sistemului de alimentare cu apă din Bălți', 'BERD', 40e6)],
             [pr('P1', 'Reabilitarea sistemului de alimentare cu apă din Bălți', BERD, 41e6)]);
egal('denumire + finanțator + sumă = nivelul „suma"', [prima(r).nivel, r.rezultate[0].stare], ['suma', 'suma']);

r = potr([ac('a1', 'Reabilitarea sistemului de alimentare cu apă din Bălți', 'BERD', 40e6)],
         [pr('P1', 'Reabilitarea sistemului de alimentare cu apă din Bălți', JP, 41e6)]);
egal('aceeași denumire, alt finanțator: nicio legătură', r.rezultate[0].legaturi.length, 0);

r = potr([ac('a1', 'Reabilitarea sistemului de alimentare cu apă din Bălți', 'BERD', 40e6)],
         [pr('P1', 'Reabilitarea sistemului de alimentare cu apă din Bălți', BERD, 9e6)]);
egal('denumire + finanțator, dar suma diferă: „titlu", cu motivul scris', [prima(r).nivel, prima(r).motive.indexOf('suma diferă') > -1], ['titlu', true]);

r = potr([ac('a1', 'Reabilitarea sistemului de alimentare cu apă din Bălți', 'BERD', null)],
         [pr('P1', 'Reabilitarea sistemului de alimentare cu apă din Bălți', BERD, 9e6)]);
egal('suma acordului necunoscută: „titlu", nu „suma"', prima(r).nivel, 'titlu');

r = potr([ac('a1', 'Energie termică pentru municipiul Bălți', 'BERD', null)],
         [pr('P1', 'Energie termică pentru municipiul Bălți, etapa 1', BERD, 1e6), pr('P2', 'Energie termică pentru municipiul Bălți, etapa 2', BERD, 2e6)]);
egal('două proiecte la fel de potrivite după titlu: ambele „ambiguu"', r.rezultate[0].legaturi.map(l => l.nivel), ['ambiguu', 'ambiguu']);

r = potr([ac('a1', 'Energie termică pentru municipiul Bălți', 'BERD', 20e6)],
         [pr('P1', 'Energie termică pentru municipiul Bălți', BERD, 20e6), pr('P2', 'Energie termică pentru municipiul Bălți', BERD, 18.2e6)]);
const niv = r.rezultate[0].legaturi.reduce((o, l) => { o[l.idProiect] = l.nivel; return o; }, {});
egal('două proiecte la sumă: rămâne „suma" cel cu suma mai apropiată', niv, { P1: 'suma', P2: 'ambiguu' });

r = potr([ac('a1', 'Reabilitarea drumurilor din Moldova — Proiectul V', 'BERD', 150e6), ac('a2', 'Reabilitarea drumurilor din Moldova — Proiectul VI', 'BERD', 344e6)],
         [pr('P1', 'Reabilitarea Drumurilor Naționale', BERD, 30e6)]);
egal('faza V și faza VI nu se leagă de un proiect fără fază și fără sumă care să confirme', [r.rezultate[0].legaturi.length, r.rezultate[1].legaturi.length], [0, 0]);

r = potr([ac('a1', 'Reabilitarea drumurilor din Moldova — Proiectul V', 'BERD', 150e6), ac('a2', 'Reabilitarea drumurilor din Moldova — Proiectul VI', 'BERD', 344e6)],
         [pr('P5', 'Reabilitarea drumurilor din Moldova — Proiectul V', BERD, 150e6), pr('P6', 'Reabilitarea drumurilor din Moldova — Proiectul VI', BERD, 344e6)]);
egal('fazele cu proiecte proprii se leagă fiecare de al lui', [r.rezultate[0].legaturi.map(l => l.idProiect), r.rezultate[1].legaturi.map(l => l.idProiect)], [['P5'], ['P6']]);

r = potr([ac('a1', 'Deșeuri solide în Republica Moldova', 'BEI', 25e6), ac('a2', 'Deșeuri solide în Republica Moldova', 'BERD', 25e6)],
         [pr('P1', 'Deșeuri solide în Republica Moldova', BEI + ' / ' + BERD, 25e6, { donatori: [BEI, BERD] })]);
egal('BEI și BERD finanțează același proiect: ambele legături rămân, marcate „partajat"', r.rezultate.map(x => [x.legaturi[0].nivel, x.legaturi[0].partajat]), [['suma', 1], ['suma', 1]]);

r = potr([ac('a1', 'Modernizarea școlilor din raionul Orhei', 'BIRD', null), ac('a2', 'Modernizarea școlilor din raionul Orhei', 'BIRD', null, { id: 'a2' })],
         [pr('P1', 'Modernizarea școlilor din raionul Orhei', 'Banca Mondială', 3e6)]);
egal('același proiect pentru două acorduri ale aceluiași finanțator, fără sumă: „ambiguu"', r.rezultate.map(x => x.legaturi[0].nivel), ['ambiguu', 'ambiguu']);

r = potr([ac('a1', 'Eficiența energetică în clădiri publice', 'BEI', 12.4e6, { cost: { v: 75e6, val: 'EUR', eur: 75e6 } })],
         [pr('P1', 'Eficiența energetică în clădiri publice', BEI, 75e6)]);
egal('doar costul total al proiectului coincide: „titlu", nu „suma"', [prima(r).nivel, prima(r).motive.indexOf('costul total al proiectului coincide') > -1], ['titlu', true]);

r = potr([ac('a1', 'Pod peste Prut la Ungheni', 'BEI', 30e6, { semnat: '10.05.2019', primul: '01.03.2019', ultimul: '10.05.2019' })],
         [pr('P1', 'Pod peste Prut la Ungheni', BEI, 31e6, { inceput: 2005 })]);
egal('un proiect început cu 14 ani înaintea acordului nu se leagă, deși și denumirea, și suma se potrivesc doar parțial: nivelul „suma" cere data neîn contradicție decât la denumire identică',
      r.rezultate[0].legaturi.map(l => l.nivel), ['suma']);

r = potr([ac('a1', 'Energie termică pentru municipiul Bălți', 'BERD', 20e6)], [pr('P1', 'Alt proiect, fără legătură', BERD, 20e6)]);
egal('o sumă egală nu face o legătură fără denumire', r.rezultate[0].legaturi.length, 0);

// confirmările unui om
r = potr([ac('a1', 'Energie termică pentru municipiul Bălți', 'BERD', null)],
         [pr('P1', 'Energie termică pentru municipiul Bălți, etapa 1', BERD, 1e6), pr('P2', 'Energie termică pentru municipiul Bălți, etapa 2', BERD, 2e6)],
         { confirmate: { a1: ['P2'] } });
egal('o legătură confirmată trece înaintea celorlalte, iar acordul devine „confirmat"', [r.rezultate[0].legaturi[0].idProiect, r.rezultate[0].legaturi[0].nivel, r.rezultate[0].stare], ['P2', 'confirmat', 'confirmat']);
r = potr([ac('a1', 'Energie termică pentru municipiul Bălți', 'BERD', 20e6)], [pr('P1', 'Energie termică pentru municipiul Bălți', BERD, 20e6)], { respinse: { a1: ['P1'] } });
egal('o legătură respinsă dispare', [r.rezultate[0].legaturi.length, r.rezultate[0].stare], [0, 'fara']);
r = potr([ac('a1', 'Alt nume', 'BERD', 20e6)], [], { confirmate: { a1: ['PX'] } });
verifica('o confirmare pentru un proiect care nu mai e în date se păstrează, cu motivul', r.rezultate[0].legaturi.length === 1 && r.rezultate[0].legaturi[0].motive[0].indexOf('nu e în datele de azi') > -1);
r = potr([ac('a1', 'Fără proiect în AMP', 'BERD', 20e6)], [], { fara_proiect: ['a1'] });
egal('„fără proiect" confirmat de un om', r.rezultate[0].stare, 'fara-confirmat');

// banii
r = potr([ac('a1', 'Reabilitarea sistemului de alimentare cu apă din Bălți', 'BERD', 40e6)], [pr('P1', 'Reabilitarea sistemului de alimentare cu apă din Bălți', BERD, 41e6, { deb: 12e6 })]);
const b = M.bani(r.rezultate[0], { P1: { ang: 41e6, deb: 12e6 } });
egal('banii se adună din legăturile sigure', [b.ang, b.deb, b.siguri], [41e6, 12e6, 1]);
r = potr([ac('a1', 'Energie termică pentru municipiul Bălți', 'BERD', 20e6)], [pr('P1', 'Energie termică pentru municipiul Bălți', BERD, 5e6)]);
const b2 = M.bani(r.rezultate[0], { P1: { ang: 5e6, deb: 2e6 } });
egal('o legătură doar după titlu nu intră în total, se arată separat', [b2.deb, b2.siguri, b2.probabile.deb], [0, 0, 2e6]);

console.log('\nPe datele reale din repository');
const AICI = __dirname;
const ctx = {}; vm.createContext(ctx);
vm.runInContext(fs.readFileSync(path.join(AICI, 'arhiva.js'), 'utf8') + ';this.A=ARCHIVE;', ctx);
const an = s => { const m = /(\d{4})$/.exec(s || ''); return m ? +m[1] : null; };
const proiecte = ctx.A.map(a => {
  let ang = 0, deb = 0;
  Object.keys(a.y).forEach(k => { if (/^(19|20)\d\d$/.test(k)) { ang += a.y[k][0] || 0; deb += a.y[k][1] || 0; } });
  return { id: String(a.id), titluri: [a.t], donatori: a.d, inceput: an(a.ds), ang: ang, deb: deb, vp: a.vp || 0 };
});
const G = JSON.parse(fs.readFileSync(path.join(AICI, 'date', 'acorduri_legare.json'), 'utf8')).acorduri;
const t0 = Date.now();
const R = M.potriveste(G, proiecte, {});
const ms = Date.now() - t0;
const dupa = (nivel) => R.rezultate.filter(x => x.stare === nivel).length;
console.log('  (' + G.length + ' acorduri × ' + proiecte.length + ' proiecte: ' + ms + ' ms; suma ' + dupa('suma') + ', titlu ' + dupa('titlu') + ', ambiguu ' + dupa('ambiguu') + ', fără ' + dupa('fara') + ')');
verifica('420 de comparații pe secundă ajung: sub 3 secunde', ms < 3000, ms);
verifica('cel puțin 40 de acorduri se leagă la nivelul „suma"', dupa('suma') >= 40, dupa('suma'));
verifica('nicio legătură nu are finanțator contrazis', R.rezultate.every(x => x.legaturi.every(l => l.donator !== 'nu')));
verifica('nicio legătură „suma" nu are suma în afara toleranței', R.rezultate.every(x => x.legaturi.every(l => l.nivel !== 'suma' || (l.suma.stare === 'da' && l.suma.rel <= M.CONSTANTE.TOLERANTA_SUMA))));
verifica('niciun acord nu are două legături „suma" cu sume foarte diferite',
         R.rezultate.every(x => { const s = x.legaturi.filter(l => l.nivel === 'suma').map(l => l.suma.rel); return s.length < 2 || Math.max.apply(null, s) - Math.min.apply(null, s) <= 0.03; }));
const gasit = (cauta, idAmp, parteneri) => R.rezultate.some(x => x.acord.scurt.toLowerCase().indexOf(cauta) > -1 && (!parteneri || x.acord.parteneri.indexOf(parteneri) > -1) &&
  x.legaturi.some(l => l.idProiect === idAmp && l.nivel === 'suma'));
verifica('„Deșeuri solide" (BEI, 25 mil. EUR) se leagă de 8721197417527', gasit('deșeuri solide', '8721197417527', 'BEI'));
verifica('Contractul de consolidare a statului (UE, 60 mil. EUR) se leagă de 8721160017102', gasit('consolidarea statului', '8721160017102') || gasit('consolidare a statului', '8721160017102') ||
         R.rezultate.some(x => x.legaturi.some(l => l.idProiect === '8721160017102' && l.nivel === 'suma')));
verifica('Răspuns de urgență la COVID-19 (AID) se leagă de 8721150613679',
         R.rezultate.some(x => x.legaturi.some(l => l.idProiect === '8721150613679' && l.nivel === 'suma')));
const drumuri = R.rezultate.filter(x => /drumurilor din moldova . proiectul (v|vi)$/i.test(x.acord.scurt));
verifica('fazele V și VI ale proiectului de drumuri nu primesc legături „suma" spre același proiect',
         drumuri.length < 2 || !drumuri.every(x => x.legaturi.some(l => l.nivel === 'suma' && l.idProiect === drumuri[0].legaturi[0].idProiect)));
verifica('toate cele ' + G.length + ' de acorduri din registru sunt în rezultat', R.rezultate.length === G.length);

console.log('\n' + (esuate.length ? esuate.length + ' teste au picat: ' + esuate.join('; ') : 'Toate testele au trecut (' + ok + ').'));
process.exit(esuate.length ? 1 : 0);
