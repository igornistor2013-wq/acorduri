#!/usr/bin/env node
/* Testele pentru debursari.js (pagina „Debursări pe acorduri”): formatarea sumelor, donatorii, totalurile, legarea debursărilor de
   acorduri, operațiile asupra fișierului de date, clientul GitHub (cu un GitHub simulat în memorie), păstrarea cheii cu PIN și
   specificațiile fișierelor Excel.
   Rulare:  node teste_debursari.js
   Ultima parte rulează pe datele reale din repository (date/acorduri_legare.json). */
const fs = require('fs'), path = require('path');
const D = require('./debursari.js');

let ok = 0, esuate = [];
function verifica(nume, conditie, detaliu) {
  if (conditie) { ok++; console.log('  ok   ' + nume); }
  else { esuate.push(nume); console.log('  PICĂ ' + nume + (detaliu !== undefined ? '  → ' + JSON.stringify(detaliu) : '')); }
}
const egal = (nume, a, b) => verifica(nume, JSON.stringify(a) === JSON.stringify(b), { primit: a, asteptat: b });
const aproape = (nume, a, b, tol) => verifica(nume, Math.abs(a - b) <= (tol == null ? 1e-6 : tol), { primit: a, asteptat: b });

(async function () {

console.log('Sume: afișare și citire');
egal('1250000,5 în română', D.fmtSuma(1250000.5, false), '1.250.000,5');
egal('1250000,5 în engleză', D.fmtSuma(1250000.5, true), '1,250,000.5');
egal('număr întreg, fără zecimale', D.fmtSuma(30000000, false, 0), '30.000.000');
egal('două zecimale, fără zerouri la coadă', [D.fmtSuma(12.1, false), D.fmtSuma(12.1234, false), D.fmtSuma(12, false)], ['12,1', '12,12', '12']);
egal('sub 1000 nu se grupează', D.fmtSuma(999.99, false), '999,99');
egal('valoare care nu e număr → text gol', [D.fmtSuma(NaN), D.fmtSuma(undefined), D.fmtSuma(null)], ['', '', '']);
egal('fmtBani: bani cu două zecimale, întregi fără zecimale (ro și en)',
     [D.fmtBani(1250000.5, false), D.fmtBani(1250000.5, true), D.fmtBani(30000000, false), D.fmtBani(12.1, false), D.fmtBani(0.5, false), D.fmtBani(999.99, true)],
     ['1.250.000,50', '1,250,000.50', '30.000.000', '12,10', '0,50', '999.99']);
egal('fmtBani: rotunjire la bani, zero, negativ și valori care nu sunt numere',
     [D.fmtBani(12.345, false), D.fmtBani(794407.37, false), D.fmtBani(0, false), D.fmtBani(-1234.5, false), D.fmtBani(1.004, false), D.fmtBani(NaN), D.fmtBani(null)],
     ['12,35', '794.407,37', '0', '-1.234,50', '1', '', '']);
egal('dataTextEn: luna din data cursurilor, în engleză', [D.dataTextEn('1 iulie 2026'), D.dataTextEn('15 decembrie 2025'), D.dataTextEn('3 Mai 2024'), D.dataTextEn(''), D.dataTextEn(null)],
     ['1 July 2026', '15 December 2025', '3 May 2024', '', '']);
egal('fmtBani se citește înapoi la fel', [D.parseSuma(D.fmtBani(1250000.5, false)), D.parseSuma(D.fmtBani(1250000.5, true)), D.parseSuma(D.fmtBani(1250, false)), D.parseSuma(D.fmtBani(1.5, false))], [1250000.5, 1250000.5, 1250, 1.5]);
egal('fmtCompact: mii, milioane, miliarde, în ambele limbi',
     [D.fmtCompact(12000, false), D.fmtCompact(340200000, false), D.fmtCompact(2350000000, false), D.fmtCompact(340200000, true), D.fmtCompact(2350000000, true), D.fmtCompact(950, false)],
     ['12 mii', '340,2 mil.', '2,35 mld.', '340.2 M', '2.35 bn', '950']);
const citiri = [
  ['1.250.000,50', 1250000.5], ['1,250,000.50', 1250000.5], ['1 250 000,5', 1250000.5], ['1250000.5', 1250000.5], ['1250000', 1250000],
  ['0,5', 0.5], ['12,75', 12.75], ['1.250', 1250], ['1,250', 1250], ['1.234.567', 1234567], ['100.000', 100000], ['1.5', 1.5], ['1,5', 1.5],
  ['0.123', 0.123], ['0,123', 0.123], ['1.234,56', 1234.56], ['1,234.56', 1234.56], ['  7 500 000  ', 7500000], ['3 000 000', 3000000], ['25.000.000,00', 25000000],
  ['abc', NaN], ['', NaN], ['-5', NaN], ['1e6', NaN], ['1.2.3', NaN], ['1,234,5,6', NaN], ['12.34.56,78', NaN], ['1.234,567,8', NaN], [',', NaN], ['.', NaN]
];
citiri.forEach(function (p) {
  const r = D.parseSuma(p[0]);
  verifica('parseSuma(' + JSON.stringify(p[0]) + ') = ' + p[1], Number.isNaN(p[1]) ? Number.isNaN(r) : Math.abs(r - p[1]) < 1e-9, r);
});
egal('ce se scrie se citește înapoi la fel (ro și en)',
     [D.parseSuma(D.fmtSuma(1234567.89, false)), D.parseSuma(D.fmtSuma(1234567.89, true)), D.parseSuma(D.fmtSuma(4000, false))], [1234567.89, 1234567.89, 4000]);

console.log('\nDate');
egal('dataRo', [D.dataRo('2026-03-05'), D.dataRo(''), D.dataRo('xx')], ['05.03.2026', '', 'xx']);
egal('esteDataIso: zile reale, nu 30 februarie, nu luna 13',
     ['2026-02-28', '2026-02-30', '2026-13-01', '2024-02-29', '2025-02-29', '26-01-01', '2026-1-1'].map(D.esteDataIso), [true, false, false, true, false, false, false]);
egal('aziIso folosește data locală', D.aziIso(new Date(2026, 9, 26, 23, 59)), '2026-10-26');
egal('ordRo ordonează datele din registru', [D.ordRo('01.10.2026'), D.ordRo('x')], ['20261001', '']);

console.log('\nDonatori și denumiri');
egal('un parteneri cu două valori → doi donatori', D.donatoriiAcordului('BIRD / AID'), ['BIRD', 'AID']);
egal('același donator repetat se numără o dată; spațiile se curăță', D.donatoriiAcordului(' UE  /  UE / Germania '), ['UE', 'Germania']);
egal('partener gol → „neidentificat”', [D.donatoriiAcordului(''), D.donatoriiAcordului(null)], [[D.NEIDENTIFICAT], [D.NEIDENTIFICAT]]);
egal('„SUA / SUA (MCC)” rămân doi donatori, ca în filtrul registrului', D.donatoriiAcordului('SUA / SUA (MCC)'), ['SUA', 'SUA (MCC)']);
egal('denumire tăiată în mijlocul unei paranteze', D.curataNume('Proiectul de dezvoltare al sistemului electroenergetic ('), 'Proiectul de dezvoltare al sistemului electroenergetic');
egal('denumirea întreagă rămâne neatinsă', D.curataNume('Apă Nord Moldova (faza II)'), 'Apă Nord Moldova (faza II)');
egal('virgula de la coadă se scoate, puncțiile de tăiere (…) rămân', [D.curataNume('Livada Moldovei,'), D.curataNume('Acordul de grant și proiect dintre Ministerul…')], ['Livada Moldovei', 'Acordul de grant și proiect dintre Ministerul…']);
egal('stadiul = cel mai înaintat', [D.stadiu(['neg', 'sem']), D.stadiu(['vig']), D.stadiu([]), D.stadiu(['prm', 'rat', 'neg']), D.stadiu(['neg', 'sem', 'plg', 'rat'])], ['sem', 'vig', '', 'prm', 'rat']);
egal('etichetele stadiului, în ambele limbi', [D.etichetaStadiu('vig', false), D.etichetaStadiu('vig', true), D.etichetaStadiu('', false)], ['În vigoare', 'In force', '']);
egal('tipul de finanțare în engleză', [D.etichetaTip('Împrumut', true), D.etichetaTip('Grant', true), D.etichetaTip('Asistență tehnică', true), D.etichetaTip('Altceva', true)], ['Loan', 'Grant', 'Technical assistance', 'Altceva']);
egal('numele complet al donatorului', [D.numeDonator('BERD', false), D.numeDonator('BERD', true), D.numeDonator('Japonia', true), D.numeDonator('Necunoscut', false)],
     ['Banca Europeană pentru Reconstrucție și Dezvoltare', 'European Bank for Reconstruction and Development, EBRD', 'Japan', 'Necunoscut']);

console.log('\nAcordurile pregătite pentru pagină');
const CURSURI = { EUR: 1, USD: 1.1383, JPY: 185.21, DST: 0.83998, CHF: 0.9234 };
const ac = (id, scurt, parteneri, suma, extra) => Object.assign({
  id: id, nume: scurt, scurt: scurt, parteneri: parteneri, categorie: 'Grant', semnat: '', primul: '01.01.2020', ultimul: '01.01.2021', et: ['neg', 'sem'],
  suma: suma, faraTotal: false, inTotal: suma ? 'numarat' : 'fara_suma', alte: [], cost: null,
  acte: [{ act: 'HG' + id.replace(/\D/g, '') + '/2020', tip: 'Hotărâre', data: '01.01.2020', editie: 'legis.md', url: 'https://www.legis.md/x?doc_id=' + id.replace(/\D/g, ''), etape: ['neg'] }]
}, extra || {});
const S = (v, val, eur) => ({ v: v, val: val, eur: eur == null ? Math.round(v / (CURSURI[val] || 1)) : eur, sursa: 'acord', act: 'HG1/2020' });
const JSON_TEST = {
  actualizat: '2026-10-26 10:00', curs_data: '1 iulie 2026', cursuri: CURSURI,
  acorduri: [
    ac('a1', 'Modernizarea școlilor', 'BIRD / AID', S(10000000, 'USD'), { categorie: 'Împrumut', et: ['vig', 'rat'], semnat: '07.09.2026' }),
    ac('a2', 'Sprijin pentru justiție', 'UE', S(5000000, 'EUR')),
    ac('a3', 'Reforma achizițiilor publice', 'UE', null, { nume: 'Acordul de finanțare dintre Republica Moldova și Uniunea Europeană privind reforma achizițiilor publice' }),
    ac('a4', 'Calea ferată', 'BERD', S(8000000, 'EUR'), { categorie: 'Împrumut', faraTotal: true, inTotal: 'fara_total' }),
    ac('a5', 'Proiect fără partener', '', S(1000000, 'EUR')),
    ac('a6', 'Echipamente agricole', 'JICA / Japonia', S(1852100000, 'JPY'), { categorie: 'Împrumut' }),
    ac('a7', 'Moneda locală', 'CEB', { v: 5000, val: 'MDL', eur: null, sursa: 'acord', act: 'HG7/2020' }, { categorie: 'Împrumut', inTotal: 'fara_curs' })
  ]
};
const B = D.pregateste(JSON_TEST);
egal('toate acordurile intră, fiecare cu id unic', B.acorduri.map(a => a.id), ['a1', 'a2', 'a3', 'a4', 'a5', 'a6', 'a7']);
egal('donatorii: BIRD și AID au același acord; UE are două',
     B.donatori.map(d => d.cheie + ':' + d.acorduri.length).sort(), ['AID:1', 'BERD:1', 'BIRD:1', 'CEB:1', 'JICA:1', 'Japonia:1', 'UE:2', D.NEIDENTIFICAT + ':1'].sort());
aproape('echivalentul în euro folosește cursul exact, nu rotunjirea din fișier', B.peId.get('a1').eur, 10000000 / 1.1383, 1e-6);
egal('doar rândurile „numărate” intră în total', B.acorduri.map(a => a.eurTotal != null), [true, true, false, false, true, true, false]);
egal('valută fără curs: suma rămâne pe rând, dar fără euro', [B.peId.get('a7').eur, B.peId.get('a7').suma.val], [null, 'MDL']);
egal('denumire: se păstrează scurta; titlul complet — pentru descriere', [B.peId.get('a1').nume, B.peId.get('a3').numeComplet.indexOf('Acordul de finanțare') === 0], ['Modernizarea școlilor', true]);
egal('actele și linkul spre legis.md', [B.peId.get('a2').coduri, B.peId.get('a2').url.indexOf('legis.md') > 0], [['HG2/2020'], true]);
egal('peAct găsește acordurile după codul actului', B.peAct.get('HG2/2020').map(a => a.id), ['a2']);
egal('cursurile și data lor', [B.cursData, B.cursuri.USD, B.cursuri.EUR], ['1 iulie 2026', 1.1383, 1]);
const FARA_CURSURI = D.pregateste(Object.assign({}, JSON_TEST, { cursuri: undefined }));
aproape('un fișier mai vechi, fără cursuri: se deduc din rânduri', FARA_CURSURI.cursuri.USD, 1.1383, 0.001);
egal('descriere = obiectivele proiectului; fără obiective, șir gol (nu o frază alcătuită din titlu și date)',
     [D.descriere(B.peId.get('a1'), false), D.descriere(B.peId.get('a1'), true, D.infoProiect(B.peId.get('a1'), {})), D.descriere(B.peId.get('a3'), false, null)], ['', '', '']);
const INFO_O = { obiective: { ro: 'Modernizarea școlilor', en: 'Modernising schools', tip: 'oficial' } };
egal('descriere: obiectivele în limba paginii', [D.descriere(B.peId.get('a1'), false, INFO_O), D.descriere(B.peId.get('a1'), true, INFO_O)], ['Modernizarea școlilor', 'Modernising schools']);
egal('descriere: fără traducere în engleză, se păstrează textul român', D.descriere(B.peId.get('a1'), true, { obiective: { ro: 'Text', en: '', tip: 'manual' } }), 'Text');

console.log('\nDebursările: formular, legare, totaluri');
const ACUM = new Date(2026, 9, 26, 12, 0);
const V = c => D.valideazaFormular(c, B.cursuri, ACUM);
let v = V({ data: '2026-10-01', suma: '1.250.000,50', val: 'EUR', nota: ' tranșa  2 ' });
egal('formular corect', [v.ok, v.valoare.suma, v.valoare.val, v.valoare.nota, v.valoare.data], [true, 1250000.5, 'EUR', 'tranșa 2', '2026-10-01']);
egal('data lipsă / invalidă', [V({ data: '', suma: '1', val: 'EUR' }).erori.data, V({ data: '2026-02-30', suma: '1', val: 'EUR' }).erori.data], ['lipsa', 'lipsa']);
egal('data din viitor se refuză, azi se primește', [V({ data: '2026-10-27', suma: '1', val: 'EUR' }).erori.data, V({ data: '2026-10-26', suma: '1', val: 'EUR' }).ok], ['viitor', true]);
egal('data prea veche', V({ data: '1989-12-31', suma: '1', val: 'EUR' }).erori.data, 'veche');
egal('suma: lipsă, text, zero, uriașă', [V({ data: '2026-10-01', suma: '', val: 'EUR' }).erori.suma, V({ data: '2026-10-01', suma: 'mult', val: 'EUR' }).erori.suma,
     V({ data: '2026-10-01', suma: '0', val: 'EUR' }).erori.suma, V({ data: '2026-10-01', suma: '99999999999999', val: 'EUR' }).erori.suma], ['lipsa', 'format', 'zero', 'mare']);
egal('valuta fără curs (MDL) nu se primește', V({ data: '2026-10-01', suma: '5', val: 'MDL' }).erori.val, 'valuta');
egal('nota prea lungă', V({ data: '2026-10-01', suma: '5', val: 'EUR', nota: 'x'.repeat(201) }).erori.nota, 'lunga');
egal('valuta scrisă cu litere mici se primește', V({ data: '2026-10-01', suma: '5', val: 'usd' }).valoare.val, 'USD');
const e1 = D.intrareDin(B.peId.get('a1'), { data: '2026-03-15', suma: 1000000.004, val: 'USD', nota: '' }, ACUM);
egal('intrarea nouă: leagă acordul, păstrează actele și denumirea, rotunjește la bani', [e1.acord, e1.acte, e1.nume, e1.suma, e1.val, e1.la], ['a1', ['HG1/2020'], 'Modernizarea școlilor', 1000000, 'USD', ACUM.toISOString()]);
verifica('id-urile intrărilor sunt unice și nevide', (function () { const s = new Set(); for (let i = 0; i < 500; i++) s.add(D.idNou()); return s.size === 500 && [...s].every(x => /^d[a-z0-9]{8,}$/.test(x)); })());
const e2 = { id: 'e2', acord: 'a1', acte: ['HG1/2020'], nume: 'x', data: '2026-06-01', suma: 500000, val: 'EUR', nota: '', la: '2026-06-02T10:00:00.000Z' };
const e3 = { id: 'e3', acord: 'a2', acte: ['HG2/2020'], nume: 'y', data: '2026-05-01', suma: 100000, val: 'EUR', nota: '', la: '2026-05-02T10:00:00.000Z' };
const eOrfan = { id: 'e4', acord: 'inexistent', acte: ['HG999/2000'], nume: 'z', data: '2026-01-01', suma: 7, val: 'EUR', la: '2026-01-02T10:00:00.000Z' };
const eRupt = { id: 'e5', acord: 'a1', suma: -5, val: 'EUR' };
let L = D.lega([e1, e2, e3, eOrfan, eRupt], B);
const LL = L;                                                  // cu o orfană, pentru fișierele Excel
egal('legare după id; cea mai nouă dată întâi', [L.peAcord.get('a1').map(e => e.id), L.peAcord.get('a2').map(e => e.id)], [['e2', e1.id], ['e3']]);
egal('fără acord în registru → orfană; intrarea stricată se ignoră', [L.orfane.map(e => e.id), (L.peAcord.get('inexistent') || []).length], [['e4'], 0]);
L = D.lega([Object.assign({}, e2, { acord: 'id-vechi-schimbat', acte: ['HG1/2020', 'HG77/1999'] })], B);
egal('id-ul acordului s-a schimbat: se regăsește după actele păstrate', [L.peAcord.has('a1'), L.orfane.length], [true, 0]);
L = D.lega([Object.assign({}, e2, { acord: 'id-vechi', acte: ['HG2/2020', 'HG2/2020', 'HG1/2020'] })], B);
egal('la mai multe potriviri, câștigă acordul cu cele mai multe acte comune', L.peAcord.has('a2'), true);

const cursuri = B.cursuri;
let g = D.agregaAcord(B.peId.get('a1'), [e1, e2], cursuri);
aproape('suma debursată în euro = USD convertit + EUR', g.eur, 1000000 / 1.1383 + 500000, 1e-6);
aproape('în valuta acordului (USD): sumele în USD directe + EURul convertit', g.inVal, 1000000 + 500000 * 1.1383, 0.005);
egal('numărul, ultima dată', [g.n, g.ultima], [2, '2026-06-01']);
aproape('procentul din suma acordului', g.pct, g.eur / (10000000 / 1.1383), 1e-9);
aproape('restul de debursat', g.rest, 10000000 / 1.1383 - g.eur, 1e-6);
g = D.agregaAcord(B.peId.get('a3'), [Object.assign({}, e3, { acord: 'a3' })], cursuri);
egal('acord fără sumă: se arată debursarea în euro, fără procent', [g.valuta, Math.round(g.inVal), g.pct, g.rest], ['EUR', 100000, null, null]);
g = D.agregaAcord(B.peId.get('a4'), [{ id: 'x', acord: 'a4', data: '2026-01-01', suma: 100, val: 'EUR' }], cursuri);
egal('acord care nu intră în total: fără procent, debursarea se arată oricum', [g.pct, g.eur], [null, 100]);
g = D.agregaAcord(B.peId.get('a2'), [{ id: 'x', acord: 'a2', data: '2026-02-01', suma: 100, val: 'XYZ' }, { id: 'y', acord: 'a2', data: '2026-01-01', suma: 50, val: 'EUR' }], cursuri);
egal('valută necunoscută în fișier: se numără, dar nu se convertește', [g.n, g.faraCurs, g.eur, g.ultima], [2, 1, 50, '2026-02-01']);
egal('acord fără debursări', (g = D.agregaAcord(B.peId.get('a2'), [], cursuri), [g.n, g.eur, g.inVal, g.pct, g.ultima]), [0, 0, 5000000 === 0 ? 0 : 0, 0, '']);

L = D.lega([e1, e2, e3], B);
const R_UE = D.rezumat(B.peDonator.get('UE'), L.peAcord, cursuri);
egal('rezumat UE: 2 proiecte, 1 cu sumă, 5 mil. EUR, 100 mii debursat', [R_UE.n, R_UE.cuSuma, R_UE.sumaEur, R_UE.debEur], [2, 1, 5000000, 100000]);
aproape('procentul UE = debursat pe proiectele cu sumă / suma lor', R_UE.pct, 100000 / 5000000, 1e-12);
const R_TOT = D.rezumat(B.acorduri.concat(B.acorduri), L.peAcord, cursuri);
egal('totalul numără fiecare acord o singură dată, chiar dacă lista îl repetă', R_TOT.n, 7);
aproape('suma totală = doar rândurile numărate', R_TOT.sumaEur, 10000000 / 1.1383 + 5000000 + 1000000 + 1852100000 / 185.21, 1e-3);
aproape('debursat total = toate intrările valide', R_TOT.debEur, 1000000 / 1.1383 + 500000 + 100000, 1e-6);
const R_DUBLU = D.rezumat(B.peDonator.get('BIRD').concat(B.peDonator.get('AID')), L.peAcord, cursuri);
egal('un acord cofinanțat de doi donatori ținuți împreună: numărat o dată', [R_DUBLU.n, R_DUBLU.nIntrari], [1, 2]);

console.log('\nObiective, date de început și de finalizare');
const SURSA = 'https://exemplu.org/doc', CITAT = 'citat exact din document';
const M0 = D.normalizeazaManual({
  omise: [{ acte: ['HG1/2020'], motiv: '  umbrelă   pentru a1 ', numarat_la: ['HG2/2020'] }, { acte: [], motiv: 'x' }, { acte: ['HG3/2020'] }],
  proiecte: [
    { acte: ['HG1/2020'], obiective: { ro: 'Obiectiv  RO', en: 'Objective EN' }, inceput: '2021-03-15', sfarsit: '2025-12', sursa: SURSA, citat: CITAT, nota: ' despre date ' },
    { acte: ['HG2/2020'], obiective: { ro: 'Fără sursă' } },
    { acte: ['HG3/2020'], inceput: '15.03.2021', sursa: SURSA, citat: CITAT },
    { acte: ['HG4/2020'], inceput: '2026-05', sfarsit: '2026-02', sursa: SURSA, citat: CITAT },
    { acte: ['HG5/2020'], obiective: { ro: 'x'.repeat(601) }, sursa: SURSA, citat: CITAT },
    { acte: ['HG6/2020'], obiective: { en: 'Only EN' }, sursa: SURSA, citat: CITAT },
    { acte: ['HG7/2020'], sursa: SURSA, citat: CITAT },
    { acte: ['HG8/2020'], inceput: '2021-02-30', sursa: SURSA, citat: CITAT },
    { acte: ['HG9/2020'], obiective: { ro: 'Sursă fără adresă web' }, sursa: 'exemplu.org', citat: CITAT },
    { acte: ['HG10/2020'], obiective: { ro: 'Citat prea scurt' }, sursa: SURSA, citat: 'scurt' },
    { obiective: { ro: 'Fără acte' }, sursa: SURSA, citat: CITAT }
  ]
});
egal('fișierul manual: o intrare bună se păstrează, cu spațiile curățate', [M0.proiecte.length, M0.proiecte[0].ro, M0.proiecte[0].en, M0.proiecte[0].inceput, M0.proiecte[0].sfarsit, M0.proiecte[0].nota], [1, 'Obiectiv RO', 'Objective EN', '2021-03-15', '2025-12', 'despre date']);
egal('fișierul manual: rândurile omise (cu motivul curățat) și cele fără acte sau fără motiv', [M0.omise.length, M0.omise[0].motiv, M0.omise[0].numaratLa], [1, 'umbrelă pentru a1', ['HG2/2020']]);
egal('fișierul manual: fără sursă, dată în alt format, început după sfârșit, text prea lung, engleză fără română, fără conținut, dată inexistentă, sursă fără adresă web, citat scurt, fără acte — toate respinse, 12 erori',
     [M0.erori.length, M0.proiecte.length], [12, 1]);
egal('fișierul manual: lipsă sau altceva decât obiect → liste goale, fără excepție', [D.normalizeazaManual(null).proiecte.length, D.normalizeazaManual({ omise: 5, proiecte: 'x' }).omise.length, D.normalizeazaManual(undefined).erori.length], [0, 0, 0]);

const MAN = {
  omise: [{ acte: ['HG4/2020'], motiv: 'Rând-umbrelă pentru a2', numarat_la: ['HG2/2020'] }],
  proiecte: [
    { acte: ['HG1/2020'], obiective: { ro: 'Modernizarea clădirilor școlilor', en: 'Modernising school buildings' }, inceput: '2021-03-15', sfarsit: '2025-12', sursa: SURSA + '/a1', citat: 'citat exact pentru a1 din document' },
    { acte: ['HG999/1999'], obiective: { ro: 'Un proiect care nu mai e în registru' }, sursa: SURSA, citat: CITAT },
    { acte: ['HG2/2020'], obiective: { ro: 'Sprijin pentru reforma justiției' }, sursa: SURSA + '/a2', citat: 'citat exact pentru a2 din document' },
    { acte: ['HG2/2020'], obiective: { ro: 'A doua intrare, ignorată pentru obiective' }, inceput: '2020-06', sursa: SURSA + '/a2b', citat: 'citat exact pentru a2, a doua intrare' }
  ]
};
const BM = D.pregateste(JSON_TEST, MAN);
egal('rând omis: nu mai apare în listă, nici la donatorul lui, dar se ține minte cu motivul și cu locul unde e numărată suma',
     [BM.acorduri.map(a => a.id), BM.peDonator.has('BERD'), BM.omise.map(o => [o.a.id, o.motiv, o.numaratLa])], [['a1', 'a2', 'a3', 'a5', 'a6', 'a7'], false, [['a4', 'Rând-umbrelă pentru a2', ['HG2/2020']]]]);
egal('rândul omis nu se găsește după act (nu primește debursări)', [BM.peAct.has('HG4/2020'), BM.peId.has('a4')], [false, false]);
egal('intrarea pentru un act care nu mai e în registru ajunge în „negăsite”, nu se pierde în tăcere', [BM.proiecteNegasite.map(p => p.acte[0]), BM.eroriManual.length], [['HG999/1999'], 0]);
egal('intrările pe rând: două pentru a2, una pentru a1', [BM.proiecteManual.get('a1').length, BM.proiecteManual.get('a2').length, BM.proiecteManual.has('a3')], [1, 2, false]);
const A1 = BM.peId.get('a1'), A2 = BM.peId.get('a2'), A3 = BM.peId.get('a3');
let inf = D.infoProiect(A1, { manual: BM.proiecteManual });
egal('info: obiective și date din sursa oficială, cu adresa și citatul', [inf.obiective.tip, inf.obiective.ro, inf.obiective.en, inf.inceput.tip, inf.inceput.v, inf.sfarsit.v, inf.inceput.sursa, inf.obiective.citat],
     ['oficial', 'Modernizarea clădirilor școlilor', 'Modernising school buildings', 'oficial', '2021-03-15', '2025-12', SURSA + '/a1', 'citat exact pentru a1 din document']);
inf = D.infoProiect(A2, { manual: BM.proiecteManual });
egal('info: fiecare câmp din prima intrare care îl are (obiectivele din prima, începutul din a doua)', [inf.obiective.ro, inf.obiective.sursa, inf.inceput.v, inf.inceput.sursa, inf.sfarsit], ['Sprijin pentru reforma justiției', SURSA + '/a2', '2020-06', SURSA + '/a2b', null]);
egal('info: fără nicio sursă, nimic nu se inventează', (inf = D.infoProiect(A3, {}), [inf.obiective, inf.inceput, inf.sfarsit, inf.contradictie]), [null, null, null, false]);
const AMP1 = new Map([['a1', { id: '872111', titlu: 'Titlu AMP', inceput: '2020-01-10', sfarsit: '2026-06-30', nivel: 'sigur' }]]);
inf = D.infoProiect(A1, { manual: BM.proiecteManual, amp: AMP1 });
egal('info: sursa oficială bate AMP', [inf.inceput.v, inf.inceput.tip, inf.sfarsit.v, inf.sfarsit.tip], ['2021-03-15', 'oficial', '2025-12', 'oficial']);
inf = D.infoProiect(A1, { amp: AMP1 });
egal('info: din AMP, cu id-ul și titlul proiectului AMP; obiectivele nu vin niciodată din AMP', [inf.inceput.tip, inf.inceput.v, inf.sfarsit.v, inf.inceput.idAmp, inf.inceput.titluAmp, inf.obiective], ['amp', '2020-01-10', '2026-06-30', '872111', 'Titlu AMP', null]);
inf = D.infoProiect(A2, { amp: new Map([['a2', { id: '1', titlu: 'T', inceput: '2019-05-02', sfarsit: '', nivel: 'probabil' }]]) });
egal('info: o legătură doar probabilă cu AMP nu dă nicio dată în tabel; rămâne ca indiciu', [inf.inceput, inf.sfarsit, inf.ampProbabil && inf.ampProbabil.titlu], [null, null, 'T']);
inf = D.infoProiect(A2, { amp: new Map([['a2', { id: '1', titlu: 'T', inceput: '2019-05-02', sfarsit: '', nivel: 'sigur' }]]) });
egal('info: din AMP (legătură sigură); o dată goală în AMP rămâne goală; fără indiciu', [inf.inceput.tip, inf.inceput.v, inf.sfarsit, inf.ampProbabil], ['amp', '2019-05-02', null, null]);
inf = D.infoProiect(A1, { amp: new Map([['a1', { id: '1', titlu: 'T', inceput: '31/12/2019', sfarsit: '', nivel: 'sigur' }]]) });
egal('info: o dată AMP care nu e în forma AAAA-LL-ZZ nu se folosește', [inf.inceput, inf.sfarsit], [null, null]);
const DB1 = new Map([['a1', { id: 'p1', acord: 'a1', obiective: 'Obiectiv introdus de om', inceput: '2022-01', nota: 'din contract', la: '2026-10-26T10:00:00.000Z' }]]);
inf = D.infoProiect(A1, { db: DB1, manual: BM.proiecteManual, amp: AMP1 });
egal('info: ce a introdus omul bate sursele oficiale și AMP; câmpul pe care nu l-a completat vine din sursa următoare',
     [inf.obiective.tip, inf.obiective.ro, inf.obiective.en, inf.inceput.tip, inf.inceput.v, inf.sfarsit.tip, inf.sfarsit.v], ['manual', 'Obiectiv introdus de om', 'Obiectiv introdus de om', 'manual', '2022-01', 'oficial', '2025-12']);
inf = D.infoProiect(A1, { db: new Map([['a1', { id: 'p1', acord: 'a1', inceput: '2030' }]]), manual: BM.proiecteManual });
egal('info: începutul de după finalizare e semnalat ca o contradicție', [inf.inceput.v, inf.sfarsit.v, inf.contradictie], ['2030', '2025-12', true]);
inf = D.infoProiect(A1, { db: new Map([['a1', { id: 'p1', acord: 'a1', inceput: '2025-12' }]]), manual: BM.proiecteManual });
egal('info: aceeași lună nu se contrazice', inf.contradictie, false);
egal('sursa scrisă: o singură sursă sau câmp cu câmp, în ambele limbi', [
  D.textSursaProiect(D.infoProiect(A1, { manual: BM.proiecteManual }), false),
  D.textSursaProiect(D.infoProiect(A1, { db: DB1, manual: BM.proiecteManual }), false),
  D.textSursaProiect(D.infoProiect(A1, { db: DB1, manual: BM.proiecteManual }), true),
  D.textSursaProiect(D.infoProiect(A3, {}), false)],
  ['sursă oficială', 'obiective: introdus de utilizator; început: introdus de utilizator; finalizare: sursă oficială', 'objectives: entered by a user; start: entered by a user; completion: official source', '']);
egal('adresa sursei: doar a unei surse oficiale', [D.legaturaSursaProiect(D.infoProiect(A1, { manual: BM.proiecteManual })), D.legaturaSursaProiect(D.infoProiect(A1, { amp: AMP1 })), D.legaturaSursaProiect(D.infoProiect(A1, { db: DB1 }))], [SURSA + '/a1', '', '']);

console.log('\nDate despre proiect introduse de utilizator');
egal('citire date: „15.03.2021”, „03.2021”, „2021”, „2021-03-15”, cu „/” sau „-”',
     ['15.03.2021', '5.3.2021', '15/03/2021', '15-03-2021', '2021-03-15', '2021/3/5', '03.2021', '3/2021', '2021-03', '2021', ' 2021 ', ''].map(D.parseDataPartiala),
     ['2021-03-15', '2021-03-05', '2021-03-15', '2021-03-15', '2021-03-15', '2021-03-05', '2021-03', '2021-03', '2021-03', '2021', '2021', '']);
egal('citire date: nu se inventează zile și luni', ['30.02.2021', '31.04.2021', '15.13.2021', '00.03.2021', '2021-00', '1949', '2101', 'ieri', '15.03.21', '15.03', '1.2.3.2021'].map(D.parseDataPartiala), [null, null, null, null, null, null, null, null, null, null, null]);
egal('afișare: dată întreagă, lună, an; formă greșită → gol', ['2026-03-05', '2026-03', '2026', 'x', ''].map(D.fmtDataPartiala), ['05.03.2026', '03.2026', '2026', '', '']);
egal('ordinea datelor se judecă doar cât spun ambele', [['2026-03', '2026-03-20'], ['2026-04', '2026-03-20'], ['2027', '2026-12-31'], ['2026', '2026-01-01'], ['2026-03-21', '2026-03-20'], ['', '2026']].map(x => D.inceputDupaSfarsit(x[0], x[1])), [false, true, true, false, true, false]);
const VP = c => D.valideazaProiect(c);
let vp = VP({ obiective: ' Modernizarea   școlilor ', inceput: '15.03.2021', sfarsit: '2025', nota: ' n  1 ' });
egal('formular „Date despre proiect” corect', [vp.ok, vp.valoare.obiective, vp.valoare.inceput, vp.valoare.sfarsit, vp.valoare.nota, vp.valoare.gol], [true, 'Modernizarea școlilor', '2021-03-15', '2025', 'n 1', false]);
egal('formular: o singură informație ajunge', [VP({ obiective: 'x' }).ok, VP({ inceput: '2020' }).ok, VP({ sfarsit: '12.2030' }).ok], [true, true, true]);
egal('formular: gol = ștergere (e valid, dar marcat „gol”)', (vp = VP({}), [vp.ok, vp.valoare.gol]), [true, true]);
egal('formular: erori — dată, ordine, text lung, notă lungă', [VP({ inceput: 'ieri' }).erori.inceput, VP({ sfarsit: '2020-13' }).erori.sfarsit, VP({ inceput: '2026-05', sfarsit: '2026-02' }).erori.sfarsit,
     VP({ obiective: 'x'.repeat(601) }).erori.obiective, VP({ obiective: 'x'.repeat(600) }).ok, VP({ obiective: 'x', nota: 'y'.repeat(201) }).erori.nota], ['format', 'format', 'ordine', 'lunga', true, 'lunga']);
const P1 = D.proiectDin(A1, vp = VP({ obiective: 'Modernizarea școlilor', inceput: '2021-03', sfarsit: '', nota: '' }).valoare, ACUM);
egal('înregistrarea nouă: leagă rândul, păstrează actele, scrie doar ce s-a completat', [P1.acord, P1.acte, P1.nume, P1.obiective, P1.inceput, 'sfarsit' in P1, 'nota' in P1, P1.la, /^p[a-z0-9]{8,}$/.test(P1.id)],
     ['a1', ['HG1/2020'], 'Modernizarea școlilor', 'Modernizarea școlilor', '2021-03', false, false, ACUM.toISOString(), true]);
egal('înregistrarea refăcută își păstrează id-ul', D.proiectDin(A1, vp, ACUM, P1.id).id, P1.id);
let dd = D.aplicaOps(D.dateGoale(), [{ t: 'pset', p: P1 }], ACUM);
egal('operația „pset” adaugă; aceeași operație repetată nu dublează', [dd.proiecte.length, D.aplicaOps(dd, [{ t: 'pset', p: P1 }]).proiecte.length], [1, 1]);
dd = D.aplicaOps(dd, [{ t: 'pset', p: Object.assign({}, P1, { obiective: 'Nou', inceput: '2022' }) }]);
egal('„pset” cu același id înlocuiește înregistrarea întreagă', [dd.proiecte.length, dd.proiecte[0].obiective, dd.proiecte[0].inceput], [1, 'Nou', '2022']);
egal('„pset” fără înregistrare sau fără id se ignoră', D.aplicaOps(dd, [{ t: 'pset' }, { t: 'pset', p: {} }]).proiecte.length, 1);
dd = D.aplicaOps(dd, [{ t: 'add', e: e2 }]);
egal('operațiile pe debursări și pe proiecte nu se amestecă', [dd.intrari.length, dd.proiecte.length], [1, 1]);
egal('„pdel” șterge doar înregistrarea cu id-ul dat', [D.aplicaOps(dd, [{ t: 'pdel', id: P1.id }]).proiecte.length, D.aplicaOps(dd, [{ t: 'pdel', id: P1.id }]).intrari.length, D.aplicaOps(dd, [{ t: 'pdel', id: 'altul' }]).proiecte.length], [0, 1, 1]);
egal('fișierul fără proiecte se scrie ca înainte (nicio cheie „proiecte”)', D.text(D.aplicaOps(D.dateGoale(), [{ t: 'add', e: e2 }], ACUM)).indexOf('proiecte') < 0, true);
const textDd = D.text(dd);
egal('fișierul cu proiecte: o înregistrare pe linie, se citește înapoi la fel', [textDd.split('\n').length, JSON.stringify(D.citesteText(textDd).proiecte), JSON.stringify(D.citesteText(textDd).intrari)], [textDd.split('\n').length, JSON.stringify(dd.proiecte), JSON.stringify(dd.intrari)]);
verifica('fiecare înregistrare e pe linia ei (git arată o modificare ca o linie)', textDd.split('\n').filter(l => l.indexOf('"id":"' + P1.id + '"') >= 0).length === 1 && /\n\{"id":"p/.test(textDd));
egal('fișier vechi, fără „proiecte”: se citește cu listă goală; „proiecte” care nu e listă → eroare de format', [D.citesteText('{"versiune":1,"intrari":[]}').proiecte, (() => { try { D.citesteText('{"intrari":[],"proiecte":5}'); return 'fără eroare'; } catch (e) { return e.cod; } })()], [[], 'format']);
const PA = P1, PB = Object.assign({}, P1, { id: 'pvechi', la: '2026-01-01T00:00:00.000Z', obiective: 'Mai vechi' });
const PC = { id: 'pc', acord: 'id-vechi', acte: ['HG2/2020'], obiective: 'Legat după act', la: '2026-02-01T00:00:00.000Z' };
const PO = { id: 'po', acord: 'x', acte: ['HG999/1999'], obiective: 'Orfan', la: '2026-02-01T00:00:00.000Z' };
const PX = { id: 'px', acord: 'a1' };
const LP = D.legaProiecte([PB, PA, PC, PO, PX], B);
egal('înregistrările legate de rânduri: cea mai nouă pe rând; cea veche rămâne în fișier, dar nu se arată', [LP.peAcord.get('a1').id, LP.vechi.map(e => e.id), LP.peAcord.get('a2').id, LP.orfane.map(e => e.id), LP.peAcord.size], [PA.id, ['pvechi'], 'pc', ['po'], 2]);
egal('o înregistrare fără obiective și fără date nu se ia în seamă', LP.peAcord.has('px') || LP.orfane.some(e => e.id === 'px') || LP.vechi.some(e => e.id === 'px'), false);
egal('căutarea poate folosi și textul obiectivelor', [B.acorduri.filter(a => D.potriveste(a, { peAcord: new Map(), q: 'extinderea canalizarii', extra: new Map([['a2', 'extinderea canalizării']]) })).map(a => a.id), B.acorduri.filter(a => D.potriveste(a, { peAcord: new Map(), q: 'extinderea canalizarii' })).length], [['a2'], 0]);

console.log('\nSuma proiectului corectată de utilizator');
const VPS = (c, cur) => D.valideazaProiect(c, cur);
vp = VPS({ suma: '1.250.000,50', val: 'eur' }, CURSURI);
egal('suma corectată: se citește, valuta se scrie cu majuscule, rotunjire la bani', [vp.ok, vp.valoare.suma, vp.valoare.val, vp.valoare.gol], [true, 1250000.5, 'EUR', false]);
egal('suma goală = „folosește suma din registru”: nu cere valuta, nu e eroare, formularul rămâne gol', (vp = VPS({ suma: '  ', val: 'XYZ' }, CURSURI), [vp.ok, vp.valoare.suma, vp.valoare.gol]), [true, null, true]);
egal('suma: erori — format, zero, prea mare', [VPS({ suma: 'abc', val: 'EUR' }).erori.suma, VPS({ suma: '0', val: 'EUR' }).erori.suma, VPS({ suma: '1.000.000.000.000.000', val: 'EUR' }).erori.suma], ['format', 'zero', 'mare']);
egal('suma: valuta trebuie să aibă curs de schimb (când se dau cursurile) și să fie scrisă', [VPS({ suma: '5', val: 'XYZ' }, CURSURI).erori.val, VPS({ suma: '5', val: '' }, CURSURI).erori.val, VPS({ suma: '5', val: 'USD' }, CURSURI).ok], ['valuta', 'valuta', true]);
egal('suma singură ajunge (celelalte câmpuri pot lipsi), nu e „gol”', [VPS({ suma: '5', val: 'EUR' }, CURSURI).ok, VPS({ suma: '5', val: 'EUR' }, CURSURI).valoare.gol, VPS({ suma: '5', val: 'EUR', inceput: '2020' }, CURSURI).valoare.inceput], [true, false, '2020']);
egal('formularul vechi (fără sumă) merge ca înainte', [VP({ obiective: 'x' }).valoare.suma, VP({ obiective: 'x' }).valoare.val, VP({ obiective: 'x' }).ok], [null, '', true]);
const PS1 = D.proiectDin(A1, VPS({ suma: '12.000.000', val: 'EUR', inceput: '2021' }, CURSURI).valoare, ACUM);
egal('înregistrarea cu sumă: suma și valuta se scriu doar când există', [PS1.suma, PS1.val, PS1.inceput, 'suma' in P1, 'val' in P1], [12000000, 'EUR', '2021', false, false]);
egal('o înregistrare doar cu sumă e validă; fără valută, cu sumă zero sau negativă nu', [D.proiectDbValid({ id: 'p1', acord: 'a1', suma: 5, val: 'EUR' }), D.proiectDbValid({ id: 'p1', acord: 'a1', suma: 5 }), D.proiectDbValid({ id: 'p1', acord: 'a1', suma: 0, val: 'EUR' }),
     D.proiectDbValid({ id: 'p1', acord: 'a1', suma: -3, val: 'EUR' }), D.proiectDbValid({ id: 'p1', acord: 'a1' })], [true, false, false, false, false]);
const LPS = D.legaProiecte([{ id: 'ps', acord: 'a1', suma: 7, val: 'EUR', la: '2026-02-01T00:00:00.000Z' }], B);
egal('o înregistrare doar cu sumă se leagă de rând', LPS.peAcord.has('a1'), true);

const BS = D.pregateste(JSON_TEST);
const sumaEurTotal = () => D.rezumat(BS.acorduri, new Map(), CURSURI).sumaEur;
const sumaInitiala = sumaEurTotal();
const a1s = BS.peId.get('a1');
egal('înainte de corectură: suma din registru e și „registru”, fără marcaj', [a1s.suma.v, a1s.suma.val, a1s.registru.suma.v, a1s.sumaCorectata, a1s.sursaSuma], [10000000, 'USD', 10000000, undefined, 'acord']);
let nc = D.aplicaSume(BS, new Map([['a1', { id: 'p1', acord: 'a1', suma: 12000000, val: 'EUR' }]]));
egal('suma corectată înlocuiește pe rând suma, valuta, echivalentul în euro, sursa și cifra din total', [nc, a1s.suma.v, a1s.suma.val, a1s.eur, a1s.eurTotal, a1s.inTotal, a1s.sursaSuma, a1s.sumaCorectata],
     [1, 12000000, 'EUR', 12000000, 12000000, 'numarat', 'utilizator', true]);
egal('suma din registru rămâne la îndemână pe rând', [a1s.registru.suma.v, a1s.registru.suma.val, a1s.registru.sursaSuma], [10000000, 'USD', 'acord']);
aproape('totalul pe donatori ține seama de suma corectată (12 000 000 EUR în loc de 10 000 000 USD)', sumaEurTotal(), sumaInitiala - 10000000 / 1.1383 + 12000000, 1e-6);
D.aplicaSume(BS, new Map([['a1', { id: 'p1', acord: 'a1', suma: 12000000, val: 'EUR' }]]));
aproape('aplicată a doua oară, nimic nu se schimbă (nu se adună, nu se strică)', sumaEurTotal(), sumaInitiala - 10000000 / 1.1383 + 12000000, 1e-6);
egal('procentul debursat se judecă față de suma corectată', D.agregaAcord(a1s, [{ id: 'e', acord: 'a1', suma: 6000000, val: 'EUR', data: '2026-01-01' }], CURSURI).pct, 0.5);
D.aplicaSume(BS, new Map());
egal('fără corectură (ștearsă), suma din registru revine întreagă', [a1s.suma.v, a1s.suma.val, a1s.sursaSuma, a1s.sumaCorectata, a1s.inTotal], [10000000, 'USD', 'acord', false, 'numarat']);
aproape('…și totalul la fel', sumaEurTotal(), sumaInitiala, 1e-6);
nc = D.aplicaSume(BS, new Map([['a3', { id: 'p3', acord: 'a3', suma: 2500000, val: 'EUR' }], ['a4', { id: 'p4', acord: 'a4', suma: 9000000, val: 'EUR' }], ['a7', { id: 'p7', acord: 'a7', suma: 4000, val: 'EUR' }], ['a2', { id: 'p2', acord: 'a2', suma: 1, val: 'XYZ' }]]));
const [a3s, a4s, a7s, a2s] = ['a3', 'a4', 'a7', 'a2'].map(i => BS.peId.get(i));
egal('rând fără sumă → cu sumă corectată intră în total', [a3s.suma.v, a3s.inTotal, a3s.eurTotal], [2500000, 'numarat', 2500000]);
egal('rând care nu se adună în total (dublură / „nu se adună”) rămâne în afara totalului, dar arată suma corectată', [a4s.suma.v, a4s.inTotal, a4s.eurTotal, a4s.sumaCorectata], [9000000, 'fara_total', null, true]);
egal('rând în valută fără curs → corectat în euro, intră în total', [a7s.suma.v, a7s.suma.val, a7s.inTotal, a7s.eurTotal], [4000, 'EUR', 'numarat', 4000]);
egal('valută fără curs de schimb în înregistrare: corectura se ignoră, rămâne suma din registru; se numără doar corecturile aplicate', [a2s.suma.v, a2s.sumaCorectata, nc], [5000000, false, 3]);
D.aplicaSume(BS, new Map());
egal('toate rândurile revin la registru', BS.acorduri.every(a => a.suma === a.registru.suma && a.eur === a.registru.eur && a.inTotal === a.registru.inTotal && a.sumaCorectata === false), true);
egal('etichetele sursei sumei au și „corectată de utilizator”', [D.SURSE_SUMA.utilizator[0], D.SURSE_SUMA.utilizator[1]], ['corectată de utilizator', 'corrected by a user']);

console.log('\nDenumiri la fel, rânduri deosebite');
const JSON_NUME = {
  cursuri: CURSURI,
  acorduri: [
    ac('n1', 'Reabilitarea drumurilor', 'BEI', S(50e6, 'EUR'), { categorie: 'Împrumut', semnat: '01.02.2015' }),
    ac('n2', 'Reabilitarea drumurilor', 'BEI', S(30e6, 'EUR'), { categorie: 'Împrumut', semnat: '03.04.2019' }),
    ac('n3', 'Reabilitarea drumurilor', 'BEI', S(20e6, 'EUR'), { categorie: 'Grant', semnat: '05.06.2019' }),
    ac('n4', 'Reabilitarea drumurilor', 'Japonia', S(1e9, 'JPY'), { categorie: 'Împrumut', semnat: '01.02.2015' }),
    ac('n5', 'Alt proiect', 'BEI', S(5e6, 'EUR')),
    ac('n6', 'Reabilitarea drumurilor', 'BEI', S(30e6, 'EUR'), { categorie: 'Împrumut', semnat: '03.04.2019' }),
    ac('n7', 'Reabilitarea drumurilor', 'BEI / Japonia', S(7e6, 'EUR'), { categorie: 'Grant', semnat: '01.01.2020' })
  ]
};
const BN = D.pregateste(JSON_NUME);
const dn = id => BN.peId.get(id).deosebire;
egal('aceeași denumire și același donator: tip și an (cel mai scurt text care deosebește)', [dn('n1').ro, dn('n3').ro, dn('n7').ro], ['împrumut, 2015', 'grant, 2019', 'grant, 2020']);
egal('tip și an la fel: se adaugă suma, apoi codul celui mai vechi act', [dn('n2').ro, dn('n6').ro], ['împrumut, 2019, 30 mil. EUR, HG2/2020', 'împrumut, 2019, 30 mil. EUR, HG6/2020']);
egal('în engleză', [dn('n1').en, dn('n2').en], ['loan, 2015', 'loan, 2019, 30 M EUR, HG2/2020']);
egal('un rând cu nume unic sau care nu împarte donatorul cu un rând la fel nu primește mențiune', [BN.peId.get('n5').deosebire, BN.peId.get('n4').deosebire && 'are'], [null, 'are']);
egal('numele afișat', [D.numeAfisat(BN.peId.get('n1'), false), D.numeAfisat(BN.peId.get('n1'), true), D.numeAfisat(BN.peId.get('n5'), false)],
     ['Reabilitarea drumurilor (împrumut, 2015)', 'Reabilitarea drumurilor (loan, 2015)', 'Alt proiect']);
verifica('în lista fiecărui donator, două rânduri nu au același nume afișat', (function () {
  let bun = true;
  BN.donatori.forEach(d => { const v = d.acorduri.map(a => D.fold(D.numeAfisat(a, false))); if (new Set(v).size !== v.length) bun = false; });
  return bun;
})(), BN.donatori.map(d => [d.cheie, d.acorduri.map(a => D.numeAfisat(a, false))]));
egal('denumirea din registru rămâne neatinsă', BN.peId.get('n1').nume, 'Reabilitarea drumurilor');
const PN = D.pregateste({ cursuri: CURSURI, acorduri: [ac('q1', 'Școli', 'UE', S(1, 'EUR'), { parteneri: 'UE / BEI', parteneriAcord: 'BEI' })] });
egal('donatorii unui rând: finanțatorul acordului (parteneriAcord), nu toți partenerii din grup; registrul rămâne la îndemână', [PN.acorduri[0].donatori, PN.acorduri[0].parteneriText, PN.acorduri[0].parteneriRegistru], [['BEI'], 'BEI', 'UE / BEI']);
egal('fără parteneriAcord (fișier mai vechi): partenerii din registru', D.pregateste({ cursuri: CURSURI, acorduri: [ac('q2', 'Școli', 'UE / BEI', null)] }).acorduri[0].donatori, ['UE', 'BEI']);

console.log('\nFiltre, ordonare, adresă');
const peAc = L.peAcord;
const F = (f) => B.acorduri.filter(a => D.potriveste(a, Object.assign({ peAcord: peAc }, f))).map(a => a.id);
egal('căutare fără diacritice: „scoli” găsește „școli”', F({ q: 'scoli' }), ['a1']);
egal('căutare pe mai multe cuvinte (toate trebuie să apară)', [F({ q: 'reforma achizitiilor' }), F({ q: 'reforma justitie' })], [['a3'], []]);
egal('căutare după partener și după codul actului', [F({ q: 'JICA' }), F({ q: 'hg2/2020' })], [['a6'], ['a2']]);
egal('filtru pe tip', F({ tip: 'Împrumut' }), ['a1', 'a4', 'a6', 'a7']);
egal('filtru „cu debursări” și „fără debursări”', [F({ deb: 'cu' }), F({ deb: 'fara' })], [['a1', 'a2'], ['a3', 'a4', 'a5', 'a6', 'a7']]);
egal('ordonare după sumă (euro) descrescător; cele fără sumă la coadă, alfabetic', D.ordoneaza(B.acorduri, 'suma', peAc, cursuri).map(a => a.id), ['a6', 'a1', 'a4', 'a2', 'a5', 'a7', 'a3']);
egal('ordonare după denumire (alfabetic, cu diacritice)', D.ordoneaza(B.acorduri, 'nume', peAc, cursuri).map(a => a.nume)[0], 'Calea ferată');
egal('ordonare după debursări', D.ordoneaza(B.acorduri, 'deb', peAc, cursuri).slice(0, 2).map(a => a.id), ['a1', 'a2']);
egal('donatorii: după număr de proiecte, „neidentificat” la coadă la egalitate',
     D.ordoneazaDonatori(B.donatori, 'n', peAc, cursuri, false).map(d => d.cheie)[0], 'UE');
egal('donatorii: alfabetic', D.ordoneazaDonatori(B.donatori, 'nume', peAc, cursuri, false).map(d => d.cheie).slice(0, 3), ['AID', 'BERD', 'BIRD']);
const h = { d: ['BERD', 'Bancă comercială străină', 'SUA (MCC)'], q: 'școli & drumuri', tip: 'Împrumut', deb: 'cu', sort: 'deb' };
egal('adresa se scrie și se citește înapoi la fel', D.citesteHash(D.scrieHash(h)), h);
egal('fără selecție, adresa e goală', D.scrieHash({ d: [], q: '', tip: '', deb: '', sort: 'suma' }), '');
egal('adresă stricată sau cu valori necunoscute: ignorate', D.citesteHash('#d=%E0%A4%A&deb=poate&sort=altceva&tip=Grant'), { d: [], q: '', tip: 'Grant', deb: '', sort: '' });

console.log('\nFișierul de date');
const date0 = D.dateGoale();
const ACUM2 = new Date('2026-10-26T09:00:00Z');
let date1 = D.aplicaOps(date0, [{ t: 'add', e: e1 }, { t: 'add', e: e2 }], ACUM2);
egal('adăugare', [date1.intrari.map(e => e.id), date1.versiune, date1.actualizat], [[e1.id, 'e2'], 1, '2026-10-26T09:00:00.000Z']);
verifica('fișierul de plecare nu se modifică', date0.intrari.length === 0);
let date2 = D.aplicaOps(date1, [{ t: 'upd', e: { id: 'e2', suma: 600000 } }, { t: 'del', id: e1.id }], ACUM2);
egal('modificare parțială (restul câmpurilor rămâne) și ștergere', [date2.intrari.length, date2.intrari[0].suma, date2.intrari[0].data], [1, 600000, '2026-06-01']);
egal('a adăuga de două ori aceeași intrare nu o dublează', D.aplicaOps(date1, [{ t: 'add', e: e2 }]).intrari.length, 2);
egal('a modifica o intrare care nu mai există o adaugă (altcineva a șters-o între timp)', D.aplicaOps(date0, [{ t: 'upd', e: e2 }]).intrari.map(e => e.id), ['e2']);
egal('a șterge o intrare inexistentă nu strică nimic', D.aplicaOps(date1, [{ t: 'del', id: 'nu-exista' }]).intrari.length, 2);
const txt = D.text(date1);
egal('o intrare pe linie, între paranteze pe linii proprii', [txt.split('\n').length, txt.startsWith('{"versiune":1,"actualizat":"2026-10-26T09:00:00.000Z","intrari":[\n{'), txt.endsWith('}\n]}\n')], [5, true, true]);
egal('fișierul gol se scrie compact', D.text(date0), '{"versiune":1,"actualizat":"","intrari":[]}\n');
egal('textul se citește înapoi identic', D.citesteText(txt), date1);
egal('BOM la început se tolerează; lipsa listei devine listă goală', [D.citesteText('﻿{"versiune":1}').intrari, D.citesteText('{}').intrari], [[], []]);
['nu e json', '[1,2]', '"text"', '{"intrari":5}', 'null'].forEach(function (rau) {
  let cod = '';
  try { D.citesteText(rau); } catch (e) { cod = e.cod; }
  verifica('fișier stricat se refuză cu un cod clar: ' + JSON.stringify(rau), cod === 'format', cod);
});
const mare = 'ș ț ă î â € — „ghilimele” '.repeat(6000);
egal('base64 pe text lung, cu diacritice, nu se strică (tăiat în bucăți)', D.textDinB64(D.b64DinText(mare)), mare);
egal('base64 cu linii noi (cum le dă GitHub) se citește', D.textDinB64(D.b64DinText('Șțăîâ').replace(/(.{4})/g, '$1\n')), 'Șțăîâ');

console.log('\nClientul GitHub (GitHub simulat în memorie)');
function GitHubFals(opt) {
  opt = opt || {};
  const st = { sha: opt.sha || null, text: opt.text == null ? null : opt.text, cereri: [], puteri: opt.push !== false, token: opt.token || 'tok_secret_123', versiune: 0 };
  st.fetch = async function (url, o) {
    o = o || {};
    st.cereri.push({ url: url, met: o.method || 'GET', antet: o.headers || {}, corp: o.body ? JSON.parse(o.body) : null, cache: o.cache });
    if (st.cadere) { throw new TypeError('Failed to fetch'); }
    const raspuns = (status, corp, antet) => ({ status: status, ok: status >= 200 && status < 300, headers: { get: k => (antet || {})[k.toLowerCase()] || null },
      json: async () => corp, text: async () => typeof corp === 'string' ? corp : JSON.stringify(corp) });
    const auth = (o.headers || {}).Authorization;
    if (url.indexOf('api.github.com') >= 0) {
      if (st.fortat) { const f = st.fortat(url, o); if (f) return raspuns(f.status, f.corp || {}, f.antet); }
      if (auth !== 'Bearer ' + st.token) return raspuns(401, { message: 'Bad credentials' });
      if (/\/contents\//.test(url)) {
        if ((o.method || 'GET') === 'GET') {
          if (st.text == null) return raspuns(404, { message: 'Not Found' });
          if (st.mare && !((o.headers || {}).Accept || '').includes('raw')) return raspuns(200, { sha: st.sha, encoding: 'none', content: '', size: 2000000 });
          if (((o.headers || {}).Accept || '').includes('raw')) return raspuns(200, st.text);
          return raspuns(200, { sha: st.sha, encoding: 'base64', content: D.b64DinText(st.text).replace(/(.{60})/g, '$1\n') });
        }
        const c = JSON.parse(o.body);
        if (!st.puteri) return raspuns(404, { message: 'Not Found' });
        if (st.inainteDePut) { const f = st.inainteDePut; st.inainteDePut = null; f(st); }
        if ((c.sha || null) !== st.sha) return raspuns(c.sha ? 409 : 422, { message: c.sha ? 'does not match' : 'Invalid request. "sha" wasn\'t supplied.' });
        st.text = D.textDinB64(c.content); st.versiune++; st.sha = 'sha' + st.versiune;
        st.mesaje = (st.mesaje || []).concat(c.message);
        return raspuns(st.versiune === 1 && !opt.sha ? 201 : 200, { content: { sha: st.sha }, commit: { sha: 'c' + st.versiune } });
      }
      return raspuns(200, { full_name: 'igornistor2013-wq/acorduri', permissions: { push: st.puteri, pull: true } });
    }
    // fișierul public de pe site
    if (st.text == null) return raspuns(404, 'nu există');
    return raspuns(200, st.text);
  };
  return st;
}
const PAUZA0 = () => Promise.resolve();
const dep = (st) => D.Depozit({ fetch: st.fetch, pauza: PAUZA0 });
const prinde = async (f) => { try { await f(); return null; } catch (e) { return e; } };

let gh = GitHubFals();
egal('verifică: cod bun, cu drept de scriere', await dep(gh).verifica('tok_secret_123'), { ok: true, scrie: true });
egal('verifică: cod greșit → „token”', (await prinde(() => dep(gh).verifica('altul'))).cod, 'token');
gh = GitHubFals({ push: false });
egal('verifică: cod care doar citește → „drept”', (await prinde(() => dep(gh).verifica('tok_secret_123'))).cod, 'drept');
gh = GitHubFals({ fortat: null }); gh.fortat = (u) => /\/repos\/[^/]+\/[^/]+$/.test(u) ? { status: 404 } : null;
egal('verifică: repository negăsit → „repo”', (await prinde(() => dep(gh).verifica('tok_secret_123'))).cod, 'repo');

gh = GitHubFals();
let c = await dep(gh).citeste('tok_secret_123');
egal('citire când fișierul nu există încă: gol, fără sha', [c.date.intrari, c.sha, c.nou], [[], null, true]);
let sv = await dep(gh).salveaza('tok_secret_123', [{ t: 'add', e: e1 }], 'Debursare: test');
const put1 = gh.cereri.filter(r => r.met === 'PUT')[0];
egal('prima salvare: fără sha, pe ramura main, cu mesajul dat', [put1.corp.sha, put1.corp.branch, put1.corp.message], [undefined, 'main', 'Debursare: test']);
egal('fișierul scris conține intrarea', D.citesteText(gh.text).intrari.map(e => e.id), [e1.id]);
egal('salvarea întoarce starea nouă și sha-ul nou', [sv.date.intrari.map(e => e.id), sv.sha], [[e1.id], 'sha1']);
sv = await dep(gh).salveaza('tok_secret_123', [{ t: 'add', e: e2 }], 'Debursare: a doua');
const put2 = gh.cereri.filter(r => r.met === 'PUT')[1];
egal('a doua salvare trimite sha-ul curent și păstrează intrarea veche', [put2.corp.sha, D.citesteText(gh.text).intrari.map(e => e.id)], ['sha1', [e1.id, 'e2']]);
verifica('cheia merge doar în antetul Authorization; nu e în adrese, nu e în corpul cererilor',
         gh.cereri.every(r => r.antet.Authorization === 'Bearer tok_secret_123' && r.url.indexOf('tok_secret') < 0 && JSON.stringify(r.corp || '').indexOf('tok_secret') < 0));
verifica('toate cererile spre API cer „no-store” (fără copii vechi din memoria browserului)', gh.cereri.every(r => r.cache === 'no-store'));
verifica('adresa fișierului e cea din configurare', gh.cereri.some(r => r.url.indexOf('/repos/igornistor2013-wq/acorduri/contents/date/debursari.json') >= 0));

// altcineva scrie între citire și scriere: 409, apoi se reia peste varianta lui
gh = GitHubFals({ text: D.text(D.aplicaOps(D.dateGoale(), [{ t: 'add', e: e3 }])), sha: 'shaA' });
gh.inainteDePut = (s) => { s.text = D.text(D.aplicaOps(D.citesteText(s.text), [{ t: 'add', e: eOrfan }])); s.sha = 'shaB'; };
sv = await dep(gh).salveaza('tok_secret_123', [{ t: 'add', e: e1 }], 'Debursare: conflict');
egal('conflict: a mers a doua oară, cu ale mele și ale celuilalt', D.citesteText(gh.text).intrari.map(e => e.id).sort(), ['e3', 'e4', e1.id].sort());
egal('conflict: s-au făcut două scrieri (prima respinsă), a doua cu sha-ul nou', gh.cereri.filter(r => r.met === 'PUT').map(r => r.corp.sha), ['shaA', 'shaB']);
// patru conflicte la rând
gh = GitHubFals({ text: D.text(D.dateGoale()), sha: 'shaA' });
let n = 0; gh.fortat = (u, o) => (o.method === 'PUT' ? (n++, { status: 409, corp: { message: 'conflict' } }) : null);
egal('patru conflicte la rând → „conflict”, după patru încercări', [(await prinde(() => dep(gh).salveaza('tok_secret_123', [{ t: 'add', e: e1 }], 'm'))).cod, n], ['conflict', 4]);
// erori
gh = GitHubFals({ text: D.text(D.dateGoale()), sha: 'shaA' });
egal('cheie greșită la salvare → „token”', (await prinde(() => dep(gh).salveaza('alta', [{ t: 'add', e: e1 }], 'm'))).cod, 'token');
gh = GitHubFals({ text: D.text(D.dateGoale()), sha: 'shaA', push: false });
egal('fără drept de scriere → „drept”', (await prinde(() => dep(gh).salveaza('tok_secret_123', [{ t: 'add', e: e1 }], 'm'))).cod, 'drept');
gh = GitHubFals({ text: D.text(D.dateGoale()), sha: 'shaA' }); gh.fortat = () => ({ status: 403, corp: { message: 'rate limit' }, antet: { 'x-ratelimit-remaining': '0' } });
egal('limita de cereri GitHub → „limita”', (await prinde(() => dep(gh).citeste('tok_secret_123'))).cod, 'limita');
gh = GitHubFals(); gh.cadere = true;
egal('fără rețea → „retea”', [(await prinde(() => dep(gh).citeste('tok_secret_123'))).cod, (await prinde(() => dep(gh).salveaza('t', [], 'm'))).cod], ['retea', 'retea']);
gh = GitHubFals({ text: 'asta nu e json', sha: 'shaA' });
egal('fișier de date stricat în repository → „format” (nu se suprascrie pe orbește)', (await prinde(() => dep(gh).salveaza('tok_secret_123', [{ t: 'add', e: e1 }], 'm'))).cod, 'format');
verifica('…și nu s-a scris nimic', gh.cereri.filter(r => r.met === 'PUT').length === 0);
gh = GitHubFals({ text: D.text(D.aplicaOps(D.dateGoale(), [{ t: 'add', e: e3 }])), sha: 'shaA' }); gh.mare = true;
c = await dep(gh).citeste('tok_secret_123');
egal('fișier mare (conținut gol în răspuns): se cere forma brută, sha-ul rămâne', [c.date.intrari.map(e => e.id), c.sha], [['e3'], 'shaA']);
gh = GitHubFals({ text: null });
egal('copia publică: lipsește → gol; există → citită; eroare de server → „alt”',
     [(await dep(gh).citestePublic()).intrari, (gh.text = D.text(D.aplicaOps(D.dateGoale(), [{ t: 'add', e: e3 }])), (await dep(gh).citestePublic()).intrari.map(e => e.id))], [[], ['e3']]);
gh.fortat = () => null; gh.fetch = async () => ({ status: 500, ok: false, headers: { get: () => null }, json: async () => ({}), text: async () => '' });
egal('copia publică: eroare 500', (await prinde(() => dep(gh).citestePublic())).cod, 'alt');
gh = GitHubFals({ text: D.text(D.dateGoale()), sha: 'shaA' });
await dep(gh).salveaza('tok_secret_123', [{ t: 'add', e: Object.assign({}, e1, { nota: 'Tranșa a doua — „cerere de retragere” nr. 4; ț ș ă' }) }], 'Debursare: Școli +1.000.000 USD');
egal('diacriticele, ghilimelele și linia lungă din notă ajung nealterate în fișier și în mesajul commit-ului',
     [D.citesteText(gh.text).intrari[0].nota, gh.mesaje[0]], ['Tranșa a doua — „cerere de retragere” nr. 4; ț ș ă', 'Debursare: Școli +1.000.000 USD']);

console.log('\nCheia, protejată cu PIN');
verifica('WebCrypto e disponibil în acest mediu', D.Seif.disponibil());
const TOKEN = 'COD-DE-PROBA-nu-e-o-cheie-reala-QRSTUVWXYZ0123456789abcdefghijklmnopqrstuvwxyz';   // nu seamănă cu o cheie GitHub, ca scanerul de secrete să n-o ia drept scurgere
const seif = await D.Seif.impacheteaza(TOKEN, 'parola-mea-1234', 2000);
egal('seiful nu conține cheia în clar', [JSON.stringify(seif).indexOf('COD-DE-PROBA'), JSON.stringify(seif).indexOf(TOKEN.slice(10, 30))], [-1, -1]);
egal('forma seifului', [seif.v, seif.i, Object.keys(seif).sort()], [1, 2000, ['c', 'i', 'n', 's', 'v']]);
egal('PIN-ul bun deschide seiful', await D.Seif.deschide(seif, 'parola-mea-1234'), TOKEN);
let ePin = await prinde(() => D.Seif.deschide(seif, 'parola-mea-1235'));
egal('PIN greșit → „pin”, fără să dea cheia', [ePin && ePin.cod, ePin && ePin.message.indexOf('github_pat')], ['pin', -1]);
ePin = await prinde(() => D.Seif.deschide({ v: 1, s: 'AAAA', n: 'AAAA', c: '!!!', i: 2000 }, 'x'));
egal('seif stricat → „pin” (nu se deosebește de un PIN greșit)', ePin && ePin.cod, 'pin');
ePin = await prinde(() => D.Seif.deschide({ v: 9 }, 'x'));
egal('seif de altă versiune → „seif”', ePin && ePin.cod, 'seif');
const seif2 = await D.Seif.impacheteaza(TOKEN, 'parola-mea-1234', 2000);
verifica('două împachetări ale aceleiași chei diferă (sare și iv aleatorii)', seif2.c !== seif.c && seif2.s !== seif.s && seif2.n !== seif.n);
egal('PIN cu diacritice și lung', await D.Seif.deschide(await D.Seif.impacheteaza(TOKEN, 'ștefan-ăîâ-12345678901234567890', 1500), 'ștefan-ăîâ-12345678901234567890'), TOKEN);

console.log('\nFișierele Excel (specificațiile)');
const X = require('./xlsx-stil.js');
const PEA = LL.peAcord;
const ctx = (en) => ({ t: (ro, e) => en ? e : ro, en: !!en, baza: 'https://nistor.vivi.md/debursari.html', cursuri: cursuri, cursData: '1 iulie 2026', peAcord: PEA, generat: '26.10.2026, 12:00' });
const donUE = B.donatori.filter(d => d.cheie === 'UE')[0], donBIRD = B.donatori.filter(d => d.cheie === 'BIRD')[0];
D.aplicaSume(BS, new Map([['a1', { id: 'p1', acord: 'a1', suma: 12000000, val: 'EUR' }]]));
const donBS = BS.donatori.filter(d => d.cheie === 'BIRD')[0];
const xsC = D.excelDonator(ctx(false), donBS);
const foaieC = xsC.foi[0], cSC = foaieC.antete.indexOf('Suma proiectului');
egal('Excel: rândul cu suma corectată arată suma nouă și valuta nouă', [foaieC.randuri[0][cSC], foaieC.randuri[0][cSC + 1]], [12000000, 'EUR']);
verifica('Excel: nota spune că suma a fost corectată de un utilizator și arată ambele sume (registru → corectată)', foaieC.note.some(n => typeof n === 'string' && n.indexOf('suma a fost corectată de un utilizator') > 0 && n.indexOf('10.000.000 USD → 12.000.000 EUR') > 0), foaieC.note.filter(n => typeof n === 'string').map(n => n.slice(0, 80)));
verifica('Excel în engleză: nota despre suma corectată', D.excelDonator(ctx(true), donBS).foi[0].note.some(n => typeof n === 'string' && n.indexOf('amount was corrected by a user') > 0 && n.indexOf('10,000,000 USD → 12,000,000 EUR') > 0));
verifica('Excel: fără corecturi, nota lipsește', !D.excelDonator(ctx(false), donUE).foi[0].note.some(n => typeof n === 'string' && n.indexOf('corectată de un utilizator') >= 0));
D.aplicaSume(BS, new Map());
D.aplicaSume(BS, new Map());
function verificaSpec(nume, spec) {
  const foi = spec.foi;
  const coerent = foi.every(f => {
    const nC = f.antete.length;
    return f.tipuri.length === nC && f.randuri.every(r => r.length === nC && r.every(x => x === '' || typeof x === 'string' || (typeof x === 'number' && isFinite(x)))) &&
           (!f.total || f.total.suma.every(i => i >= 0 && i < nC)) && Object.keys(f.latimi || {}).every(k => +k < nC) && f.foaie.length <= 31;
  });
  verifica(nume + ': antete, tipuri și rânduri au aceeași lățime; numai numere finite sau text', coerent, foi.map(f => [f.foaie, f.antete.length, f.tipuri.length]));
}
let xs = D.excelDonator(ctx(false), donUE);
verificaSpec('donator', xs);
egal('donator: foile „UE” și „Debursări”', xs.foi.map(f => f.foaie), ['UE', 'Debursări']);
const fp = xs.foi[0];
const H = (f, nume) => f.antete.indexOf(nume);
egal('donator: coloanele cerute — proiect, descriere (obiective), început, finalizare, tip, suma proiectului, debursări', [fp.antete[0], fp.antete[1], fp.antete[2], fp.antete[3], fp.antete[4], H(fp, 'Suma proiectului') > 4, H(fp, 'Debursat (în valuta proiectului)') > H(fp, 'Suma proiectului')],
     ['Proiectul', 'Descriere succintă (obiectivele proiectului)', 'Data efectivă de începere', 'Data finalizării', 'Tip de finanțare', true, true]);
egal('donator: cele două coloane de date sunt de tip dată (z), descrierea text, sursa text', [fp.tipuri[2], fp.tipuri[3], fp.tipuri[1], fp.tipuri[H(fp, 'Sursa obiectivelor și a datelor')]], ['z', 'z', 't', 't']);
egal('donator: un rând pe acord, în ordinea sumei', fp.randuri.map(r => r[0]), ['Sprijin pentru justiție', 'Reforma achizițiilor publice']);
const cS = H(fp, 'Suma proiectului');       // coloanele de sumă vin una după alta: sumă, valută, echivalent EUR, debursat (valută), debursat (EUR), %, rest, număr
egal('donator: suma și echivalentul în euro', [fp.randuri[0][cS], fp.randuri[0][cS + 1], fp.randuri[0][cS + 2], fp.randuri[1][cS]], [5000000, 'EUR', 5000000, '']);
egal('donator: debursat (în valuta proiectului și în euro), procent (în puncte), rest', [fp.randuri[0][cS + 3], fp.randuri[0][cS + 4], fp.randuri[0][cS + 5], fp.randuri[0][cS + 6]], [100000, 100000, 2, 4900000]);
egal('donator: fără debursări → celule goale, număr 0', [fp.randuri[1][cS + 3], fp.randuri[1][cS + 5], fp.randuri[1][cS + 7]], ['', '', 0]);
egal('donator: totalul se calculează cu formule pe coloanele de sumă (echivalent EUR, debursat EUR, rest, număr)', fp.total.suma, [cS + 2, cS + 4, cS + 6, cS + 7]);
egal('donator: fără obiective și fără date, celulele sunt goale și sursa nu inventează nimic', [fp.randuri[0][1], fp.randuri[0][2], fp.randuri[0][3], fp.randuri[0][H(fp, 'Sursa obiectivelor și a datelor')]], ['', '', '', '']);
egal('donator: foaia Debursări are intrarea lui UE', xs.foi[1].randuri.map(r => [r[0], r[1], r[2], r[3], r[4]]), [['UE', 'Sprijin pentru justiție', '2026-05-01', 100000, 'EUR']]);
const cuFiltre = D.excelDonator(Object.assign(ctx(false), { filtre: 'filtre: tip: Grant' }), donUE);
verifica('filtrele active din pagină apar în antetul fișierului', cuFiltre.foi.every(f => f.subtitlu.indexOf('filtre: tip: Grant') > 0), cuFiltre.foi.map(f => f.subtitlu));
verifica('fără filtre, antetul nu pomenește filtre', xs.foi.every(f => f.subtitlu.indexOf('filtre') < 0), xs.foi.map(f => f.subtitlu));
xs = D.excelDonator(ctx(true), donUE);
egal('donator, engleză: foile și antetele', [xs.foi[0].antete[0], xs.foi[0].antete[2], xs.foi[0].antete[3], xs.foi[0].antete[4], xs.foi[1].foaie, xs.foi[0].randuri[0][4].indexOf('Grant') === 0],
     ['Project', 'Actual start date', 'Completion date', 'Type of financing', 'Disbursements', true]);
xs = D.excelTotal(Object.assign(ctx(false), { peAcord: LL.peAcord }), [donUE, donBIRD, B.donatori.filter(d => d.cheie === 'AID')[0]], LL.orfane);
verificaSpec('total', xs);
egal('total: foile „Total”, „Pe donatori”, „Debursări”', xs.foi.map(f => f.foaie), ['Total', 'Pe donatori', 'Debursări']);
egal('total: acordul cofinanțat BIRD+AID apare o singură dată, cu ambii donatori', xs.foi[0].randuri.filter(r => r[0] === 'Modernizarea școlilor').map(r => r[1]), ['BIRD / AID']);
egal('total: rezumatul are un rând pe donator + totalul general', xs.foi[1].randuri.map(r => r[0]).slice(0, 3).concat(xs.foi[1].randuri.length), ['UE', 'BIRD', 'AID', 4]);
const tg = xs.foi[1].randuri[3];
egal('total: „Total general” numără fiecare proiect o dată (3 proiecte), nu suma coloanelor', [tg[2], xs.foi[1].randuri.slice(0, 3).reduce((s, r) => s + r[2], 0)], [3, 4]);
verifica('rezumatul își marchează ultimul rând ca total (randTotal)', xs.foi[1].randTotal === true);
egal('orfanele apar în foaia Debursări, marcate', xs.foi[2].randuri.filter(r => r[0].indexOf('negăsit') > 0).length, 1);
xs = D.excelPeDonatori(Object.assign(ctx(false), { peAcord: LL.peAcord }), [donUE, donBIRD], LL.orfane);
verificaSpec('pe donatori', xs);
egal('pe donatori: rezumat, o foaie pe donator, apoi debursări', xs.foi.map(f => f.foaie), ['Rezumat', 'UE', 'BIRD', 'Debursări']);
xs = D.excelTotal(ctx(false), B.donatori, []);
const nume = xs.foi.map(f => f.foaie);
verifica('foile au nume unice (fără a conta diferențele de majuscule)', new Set(nume.map(x => x.toLowerCase())).size === nume.length, nume);
xs = D.excelDonator(ctx(false), B.donatori.filter(d => d.cheie === 'BERD')[0]);
egal('acord care nu intră în total: euro gol, motivul scris', [xs.foi[0].randuri[0][H(xs.foi[0], 'Echivalent EUR')], xs.foi[0].randuri[0][H(xs.foi[0], 'Intră în total?')]], ['', 'nu: nu se adună']);
// scris cu adevărat de xlsx-stil.js
for (const spec of [D.excelDonator(ctx(false), donUE), D.excelTotal(ctx(true), B.donatori, LL.orfane), D.excelPeDonatori(ctx(false), B.donatori, [])]) {
  const blob = await X.construieste(spec);
  const buf = Buffer.from(await blob.arrayBuffer());
  verifica('xlsx-stil.js scrie fișierul „' + spec.titlu + '” (arhivă ZIP, ' + spec.foi.length + ' foi)', buf.length > 2000 && buf.slice(0, 2).toString() === 'PK', buf.length);
}
const goale = D.excelDonator(ctx(false), { cheie: 'Zero', acorduri: [] });
const blobGol = await X.construieste(goale);
verifica('un donator fără niciun acord tot produce un fișier valid', Buffer.from(await blobGol.arrayBuffer()).slice(0, 2).toString() === 'PK');

console.log('\nPe datele reale din repository');
const real = JSON.parse(fs.readFileSync(path.join(__dirname, 'date', 'acorduri_legare.json'), 'utf8'));
const MANUAL = JSON.parse(fs.readFileSync(path.join(__dirname, 'date', 'proiecte_manual.json'), 'utf8'));
const R0 = D.pregateste(real);
const R = D.pregateste(real, MANUAL);
verifica('fără fișierul manual, toate acordurile din registru ajung în pagină', R0.acorduri.length === real.acorduri.length && R0.acorduri.length >= 400 && R0.omise.length === 0, [R0.acorduri.length, real.acorduri.length]);
verifica('cu fișierul manual: fiecare rând din registru e în listă sau între cele omise, o singură dată', R.acorduri.length + R.omise.length === real.acorduri.length && R.omise.length >= 1 &&
         new Set(R.acorduri.map(a => a.id).concat(R.omise.map(o => o.a.id))).size === real.acorduri.length, [R.acorduri.length, R.omise.length, real.acorduri.length]);
verifica('fișierul are cursurile exacte (nu trebuie deduse)', real.cursuri && real.cursuri.USD > 0 && real.cursuri.EUR === 1, real.cursuri);
verifica('fiecare rând are câmpul „inTotal”', real.acorduri.every(a => ['numarat', 'dublura', 'fara_total', 'fara_curs', 'fara_suma'].indexOf(a.inTotal) >= 0));
verifica('fiecare acord are cel puțin un donator, o denumire fără paranteză neînchisă și titlul din registru',
         R.acorduri.every(a => a.donatori.length >= 1 && a.nume && !/\($/.test(a.nume) && a.numeComplet && a.numeComplet.length > 0));
const omiseId = new Set(R.omise.map(o => o.a.id));
const dupaToken = (t) => real.acorduri.filter(a => !omiseId.has(a.id) && String(a.parteneriAcord || a.parteneri || '').split('/').map(x => x.trim()).indexOf(t) >= 0).length;
const donUEr = R.donatori.filter(d => d.cheie === 'UE')[0];
egal('UE: numărul de proiecte = rândurile (neomise) care îl au printre finanțatori', donUEr.acorduri.length, dupaToken('UE'));
verifica('suma donatorilor (cu repetări) ≥ numărul de acorduri; fiecare acord e la cel puțin un donator',
         R.donatori.reduce((s, d) => s + d.acorduri.length, 0) >= R.acorduri.length && R.acorduri.every(a => R.peDonator.get(a.donatori[0]).indexOf(a) >= 0));
const totalR = D.rezumat(R.acorduri, new Map(), R.cursuri);
const totalFisier = real.acorduri.filter(a => a.inTotal === 'numarat').reduce((s, a) => s + a.suma.eur, 0);   // rândurile omise nu se adună niciodată în total (vezi mai jos)
aproape('suma proiectelor = suma „echivalent EUR” din registru (diferă doar rotunjirea la euro a fiecărui rând)', totalR.sumaEur, totalFisier, real.acorduri.length * 0.5);
egal('numărul de proiecte cu sumă în total = rândurile „numărat”', totalR.cuSuma, real.acorduri.filter(a => a.inTotal === 'numarat').length);
console.log('\nDubluri: verificări pe datele reale');
const peActReal = new Map();
real.acorduri.forEach(a => (a.acte || []).forEach(x => { if (x.act) (peActReal.get(x.act) || peActReal.set(x.act, []).get(x.act)).push(a.id); }));
const actDublat = [...peActReal.entries()].filter(e => new Set(e[1]).size > 1).map(e => e[0]);
egal('niciun act nu apare în două rânduri ale registrului', actDublat, []);
const peDonDub = [];
R.donatori.forEach(d => {
  const v = new Map();
  d.acorduri.forEach(a => { const k = D.fold(D.numeAfisat(a, false)); (v.get(k) || v.set(k, []).get(k)).push(a.id); });
  v.forEach((l, k) => { if (l.length > 1) peDonDub.push(d.cheie + ': ' + k + ' → ' + l.join(', ')); });
});
egal('în lista fiecărui donator, două rânduri nu au același nume afișat (denumirea + mențiunea de deosebire)', peDonDub, []);
egal('niciun rând nu are mențiune de deosebire fără să aibă un vecin cu același nume și același donator', R.acorduri.filter(a => a.deosebire && !R.acorduri.some(b => b !== a && D.fold(b.nume) === D.fold(a.nume) && b.donatori.some(x => a.donatori.indexOf(x) >= 0))).map(a => a.id), []);
egal('rândurile omise nu se adună în niciun total (altfel suma ar fi numărată de două ori)', R.omise.filter(o => o.a.inTotal === 'numarat').map(o => o.a.id), []);
egal('suma unui rând omis e numărată în alte rânduri: fiecare act din „numarat_la” se găsește într-un rând care rămâne în listă', R.omise.filter(o => o.numaratLa.length === 0 || o.numaratLa.some(c => !(R.peAct.get(c) || []).length)).map(o => o.a.id), []);
egal('fișierul manual: nicio intrare respinsă, nicio intrare fără rând în registru', [R.eroriManual, R.proiecteNegasite.map(p => p.acte)], [[], []]);
egal('fișierul manual: fiecare act dintr-o intrare aparține aceluiași rând (nu amestecă două acorduri)', MANUAL.proiecte.filter(p => {
  const randuri = new Set();
  p.acte.forEach(c => (peActReal.get(c) || []).forEach(id => randuri.add(id)));
  return randuri.size !== 1;
}).map(p => p.acte), []);
egal('fișierul manual: anii datelor sunt plauzibili (1990–2045) și începutul nu e după sfârșit', MANUAL.proiecte.filter(p => ['inceput', 'sfarsit'].some(k => p[k] && (+String(p[k]).slice(0, 4) < 1990 || +String(p[k]).slice(0, 4) > 2045)) || D.inceputDupaSfarsit(p.inceput, p.sfarsit)).map(p => p.acte), []);
egal('fișierul manual: o intrare nu trece de 600 de caractere la obiective și are sursă web și citat', MANUAL.proiecte.filter(p => !/^https?:\/\//.test(p.sursa || '') || String(p.citat || '').length < 12 ||
     ['ro', 'en'].some(l => ((p.obiective || {})[l] || '').length > 600)).map(p => p.acte), []);
egal('finanțatorul acordului (parteneriAcord) există pe fiecare rând, nu e gol și e o submulțime a partenerilor din registru', real.acorduri.filter(a => {
  if (typeof a.parteneriAcord !== 'string') return true;
  const tok = x => String(x || '').split('/').map(y => y.trim()).filter(Boolean);
  const reg = tok(a.parteneri);
  return reg.length ? !(tok(a.parteneriAcord).length && tok(a.parteneriAcord).every(t => reg.indexOf(t) >= 0)) : false;
}).map(a => a.id), []);
egal('donatorii unui rând = finanțatorii acordului: un rând nu apare la un donator doar fiindcă un act al grupului îl pomenește', R.acorduri.filter(a => a.parteneriText !== (real.acorduri.filter(x => x.id === a.id)[0].parteneriAcord || real.acorduri.filter(x => x.id === a.id)[0].parteneri || '')).map(a => a.id), []);
// Excel pe date reale, cu fișierul manual și cu date AMP inventate
const ampR = new Map(R.acorduri.slice(0, 40).map((a, i) => [a.id, { id: 'amp' + i, titlu: 'Proiect ' + i, inceput: '2020-0' + (1 + i % 9) + '-15', sfarsit: i % 2 ? '2026-12-31' : '', nivel: i % 3 ? 'sigur' : 'probabil' }]));
const ctxR = Object.assign(ctx(false), { peAcord: new Map(), proiecteManual: R.proiecteManual, amp: ampR, omise: R.omise, ampNota: 'Nota AMP de probă: raportul live nu a răspuns.' });
const xdon = D.excelTotal(ctxR, R.donatori, []);
verificaSpec('total pe date reale, cu surse', xdon);
const fT = xdon.foi[0], iSursa = fT.antete.indexOf('Sursa obiectivelor și a datelor'), iInc = fT.antete.indexOf('Data efectivă de începere'), iSf = fT.antete.indexOf('Data finalizării'), iNume = fT.antete.indexOf('Proiectul');
verifica('Excel pe date reale: fiecare rând cu dată are sursă scrisă; nicio celulă nu conține „undefined” sau „null”', fT.randuri.every(r => (!r[iInc] && !r[iSf]) || r[iSursa]) &&
         fT.randuri.every(r => r.every(x => !/undefined|null|NaN/.test(String(x)))), fT.randuri.filter(r => r.some(x => /undefined|null|NaN/.test(String(x)))).slice(0, 2));
verifica('Excel pe date reale: datele întregi au forma zz.ll.aaaa (se citesc ca dată în Excel), cele parțiale ll.aaaa sau aaaa', fT.randuri.every(r => [r[iInc], r[iSf]].every(x => x === '' || /^(\d{2}\.\d{2}\.\d{4}|\d{2}\.\d{4}|\d{4})$/.test(x))), fT.randuri.slice(0, 3).map(r => [r[iInc], r[iSf]]));
verifica('Excel pe date reale: nota despre citirea datelor din AMP (ce s-a întâmplat cu raportul live) ajunge în fișier', fT.note.some(n => typeof n === 'string' && n.indexOf('Nota AMP de probă') === 0), fT.note.map(n => String(n.t || n).slice(0, 40)));
verifica('Excel pe date reale: nota explică datele întregi (dată adevărată) și pe cele parțiale (text)', fT.note.some(n => typeof n === 'string' && n.indexOf('rămâne text') > 0 && n.indexOf('dată adevărată') > 0), fT.note.map(n => String(n.t || n).slice(0, 40)));
verifica('Excel pe date reale: rândurile omise nu apar în foaie, dar sunt pomenite în note', R.omise.every(o => !fT.randuri.some(r => r[iNume] === o.a.nume && r[iNume + 1] === o.a.donatori.join(' / '))) && fT.note.some(n => typeof n === 'string' && n.indexOf('rânduri-umbrelă') > 0), fT.note.map(n => String(n.t || n).slice(0, 60)));
verifica('Excel pe date reale: în foaie nu apar două rânduri cu același nume afișat și aceiași donatori', (function () { const v = fT.randuri.map(r => D.fold(r[iNume]) + '|' + r[iNume + 1]); return new Set(v).size === v.length; })());
// un donator real, de la un capăt la altul
const peRand = new Map();
const donB = R.donatori.filter(d => d.cheie === 'BERD')[0];
const xr = D.excelDonator(Object.assign(ctx(false), { peAcord: peRand }), donB);
verificaSpec('BERD pe datele reale', xr);
egal('BERD: un rând pe acord în foaia „Proiecte”', xr.foi[0].randuri.length, donB.acorduri.length);
const xt = D.excelPeDonatori(Object.assign(ctx(false), { peAcord: peRand }), R.donatori, []);
verificaSpec('toți donatorii reali', xt);
verifica('un fișier cu toți donatorii (' + R.donatori.length + ' foi + rezumat + debursări) se scrie', Buffer.from(await (await X.construieste(xt)).arrayBuffer()).slice(0, 2).toString() === 'PK');

console.log('\n' + (esuate.length ? esuate.length + ' teste au picat: ' + esuate.join('; ') : 'Toate testele au trecut (' + ok + ').'));
process.exit(esuate.length ? 1 : 0);
})().catch(function (e) { console.error(e); process.exit(2); });
