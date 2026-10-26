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
egal('descriere: titlul complet când spune mai mult decât denumirea', D.descriere(B.peId.get('a3'), false).indexOf('Acordul de finanțare dintre') === 0, true);
egal('descriere: altfel o frază din ce se știe, cu actele (română)', D.descriere(B.peId.get('a1'), false), 'Împrumut de la BIRD / AID, semnat la 07.09.2026. Acte: HG1/2020 din 01.01.2020. Stadiu: în vigoare.');
egal('descriere: aceeași, în engleză', D.descriere(B.peId.get('a1'), true), 'Loan from BIRD / AID, signed on 07.09.2026. Acts: HG1/2020 of 01.01.2020. Stage: in force.');
const multe = Object.assign({}, B.peId.get('a1'), { acte: [1, 2, 3, 4, 5].map(i => ({ act: 'HG' + i + '/2020', data: '0' + i + '.01.2020' })) });
egal('descriere: cel mult trei acte, restul numărate', [D.descriere(multe, false).indexOf('Acte: HG1/2020 din 01.01.2020, HG2/2020 din 02.01.2020, HG3/2020 din 03.01.2020 și încă 2.') > 0, D.descriere(multe, true).indexOf('and 2 more.') > 0], [true, true]);
const fragment = Object.assign({}, B.peId.get('a3'), { numeComplet: 'proiectului „Modernizarea școlilor” din Republica Moldova, semnat de părți' });
egal('descriere: un titlu care începe cu literă mică (fragment) nu se folosește singur', D.descriere(fragment, false).indexOf('proiectului') < 0 && D.descriere(fragment, false).length > 10, true);
egal('descriere pentru un acord fără partener nu spune „de la”', D.descriere(B.peId.get('a5'), false).indexOf(' de la ') < 0, true);

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
egal('donator: coloanele cerute — proiect, descriere, tip, suma proiectului, debursări', [fp.antete[0], fp.antete[1], fp.antete[2], fp.antete[5], fp.antete[8]],
     ['Proiectul', 'Descriere succintă', 'Tip de finanțare', 'Suma proiectului', 'Debursat (în valuta proiectului)']);
egal('donator: un rând pe acord, în ordinea sumei', fp.randuri.map(r => r[0]), ['Sprijin pentru justiție', 'Reforma achizițiilor publice']);
egal('donator: suma și echivalentul în euro', [fp.randuri[0][5], fp.randuri[0][6], fp.randuri[0][7], fp.randuri[1][5]], [5000000, 'EUR', 5000000, '']);
egal('donator: debursat (în valuta proiectului și în euro), procent (în puncte), rest', [fp.randuri[0][8], fp.randuri[0][9], fp.randuri[0][10], fp.randuri[0][11]], [100000, 100000, 2, 4900000]);
egal('donator: fără debursări → celule goale, număr 0', [fp.randuri[1][8], fp.randuri[1][10], fp.randuri[1][12]], ['', '', 0]);
egal('donator: totalul se calculează cu formule pe coloanele de sumă (echivalent EUR, debursat EUR, rest, număr)', fp.total.suma, [7, 9, 11, 12]);
egal('donator: foaia Debursări are intrarea lui UE', xs.foi[1].randuri.map(r => [r[0], r[1], r[2], r[3], r[4]]), [['UE', 'Sprijin pentru justiție', '2026-05-01', 100000, 'EUR']]);
const cuFiltre = D.excelDonator(Object.assign(ctx(false), { filtre: 'filtre: tip: Grant' }), donUE);
verifica('filtrele active din pagină apar în antetul fișierului', cuFiltre.foi.every(f => f.subtitlu.indexOf('filtre: tip: Grant') > 0), cuFiltre.foi.map(f => f.subtitlu));
verifica('fără filtre, antetul nu pomenește filtre', xs.foi.every(f => f.subtitlu.indexOf('filtre') < 0), xs.foi.map(f => f.subtitlu));
xs = D.excelDonator(ctx(true), donUE);
egal('donator, engleză: foile și antetele', [xs.foi[0].antete[0], xs.foi[0].antete[2], xs.foi[1].foaie, xs.foi[0].randuri[0][2].indexOf('Grant') === 0], ['Project', 'Type of financing', 'Disbursements', true]);
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
egal('acord care nu intră în total: euro gol, motivul scris', [xs.foi[0].randuri[0][7], xs.foi[0].randuri[0][14]], ['', 'nu: nu se adună']);
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
const R = D.pregateste(real);
verifica('toate acordurile din fișier ajung în pagină', R.acorduri.length === real.acorduri.length && R.acorduri.length >= 400, [R.acorduri.length, real.acorduri.length]);
verifica('fișierul are cursurile exacte (nu trebuie deduse)', real.cursuri && real.cursuri.USD > 0 && real.cursuri.EUR === 1, real.cursuri);
verifica('fiecare rând are câmpul „inTotal”', real.acorduri.every(a => ['numarat', 'dublura', 'fara_total', 'fara_curs', 'fara_suma'].indexOf(a.inTotal) >= 0));
verifica('fiecare acord are cel puțin un donator, o denumire fără paranteză neînchisă și o descriere',
         R.acorduri.every(a => a.donatori.length >= 1 && a.nume && !/\($/.test(a.nume) && D.descriere(a, false).length > 10 && D.descriere(a, true).length > 10));
const dupaToken = (t) => real.acorduri.filter(a => String(a.parteneri || '').split('/').map(x => x.trim()).indexOf(t) >= 0).length;
const donUEr = R.donatori.filter(d => d.cheie === 'UE')[0];
egal('UE: numărul de proiecte = rândurile din registru care îl au printre parteneri', donUEr.acorduri.length, dupaToken('UE'));
verifica('suma donatorilor (cu repetări) ≥ numărul de acorduri; fiecare acord e la cel puțin un donator',
         R.donatori.reduce((s, d) => s + d.acorduri.length, 0) >= R.acorduri.length && R.acorduri.every(a => R.peDonator.get(a.donatori[0]).indexOf(a) >= 0));
const totalR = D.rezumat(R.acorduri, new Map(), R.cursuri);
const totalFisier = real.acorduri.filter(a => a.inTotal === 'numarat').reduce((s, a) => s + a.suma.eur, 0);
aproape('suma proiectelor = suma „echivalent EUR” din registru (diferă doar rotunjirea la euro a fiecărui rând)', totalR.sumaEur, totalFisier, real.acorduri.length * 0.5);
egal('numărul de proiecte cu sumă în total = rândurile „numărat”', totalR.cuSuma, real.acorduri.filter(a => a.inTotal === 'numarat').length);
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
