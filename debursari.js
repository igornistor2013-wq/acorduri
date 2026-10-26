/* debursari.js — logica paginii „Debursări pe acorduri” (debursari.html), fără DOM, ca să se poată testa în Node.

   Ce face pagina: ia acordurile din registrul legis.md (date/acorduri_legare.json, scris de legatura_acorduri.py chiar din
   registru), le repartizează pe donatori (partenerii din registru, cum îi numește și filtrul registrului), arată pentru fiecare
   donator proiectele lui — denumire, descriere succintă, tip de finanțare, suma proiectului — și, alături, suma debursărilor.
   Debursările nu vin dintr-o sursă oficială: se introduc de mână, după ce utilizatorul introduce un cod, și se salvează în
   „baza de date” a site-ului: fișierul date/debursari.json din repository.

   Cum se păstrează „baza de date”. Site-ul e static (GitHub Pages), deci nu are server care să primească datele. Singurul loc în
   care o pagină poate scrie, fără un serviciu în plus, e chiar repository-ul: GitHub dă o interfață (API-ul „Contents”) prin care
   se citește și se scrie un fișier, cu o cheie de acces. „Codul” cerut de pagină e această cheie (o „fine-grained personal access
   token” cu drept doar pe acest repository, doar „Contents: Read and write”). Fiecare salvare e un commit: istoricul și
   anularea vin gratis din git, iar scrierile simultane se rezolvă prin „sha” (vezi Depozit.salveaza).

   Cheia NU se scrie în niciun fișier și nu pleacă nicăieri în afara de api.github.com. Rămâne în memoria paginii; dacă
   utilizatorul vrea s-o țină pe dispozitiv, se păstrează în localStorage criptată cu un PIN ales de el (Seif: PBKDF2 + AES-GCM).

   Ce conține:
     · formatarea și citirea sumelor și a datelor (fmtSuma, fmtBani, parseSuma…);
     · donatorii și acordurile pregătite pentru pagină (pregateste);
     · legarea debursărilor de acorduri, inclusiv când se schimbă id-ul unui acord (lega);
     · totalurile, la fel ca în panoul de sume al registrului (agregaAcord, rezumat);
     · operațiile asupra fișierului de date și salvarea lui (aplicaOps, Depozit);
     · păstrarea cheii, protejată cu PIN (Seif);
     · specificațiile fișierelor Excel, pentru xlsx-stil.js (excelDonator, excelTotal, excelPeDonatori). */
(function (root, factory) {
  'use strict';
  const api = factory(root);
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  if (typeof window !== 'undefined') window.Debursari = api;
})(typeof globalThis !== 'undefined' ? globalThis : (typeof self !== 'undefined' ? self : this), function (root) {
'use strict';

/* ------------------------------------------------------------------ configurare */
const CONFIG = {
  repo: 'igornistor2013-wq/acorduri',          // unde se păstrează „baza de date”
  ramura: 'main',
  cale: 'date/debursari.json',
  api: 'https://api.github.com',
  sursaAcorduri: 'date/acorduri_legare.json',
  sursaDate: 'date/debursari.json'              // aceeași bază, citită ca fișier public (fără cod)
};
const NEIDENTIFICAT = '(neidentificat)';
const MAX_NOTA = 200;
const MAX_SUMA = 1e13;
const LUNGIME_MIN_PIN = 4;

/* ------------------------------------------------------------------ texte, ordine */
const STADII = [
  ['vig', 'În vigoare', 'In force'],
  ['prm', 'Promulgat', 'Promulgated'],
  ['rat', 'Ratificat / aprobat', 'Ratified / approved'],
  ['plg', 'Proiect de lege', 'Draft law'],
  ['sem', 'Semnare aprobată', 'Signing approved'],
  ['neg', 'Negocieri', 'Negotiations']
];
const TIPURI_EN = { 'Grant': 'Grant', 'Împrumut': 'Loan', 'Asistență tehnică': 'Technical assistance', 'Asistență financiară': 'Financial assistance' };
const ORDINE_TIP = ['Grant', 'Împrumut', 'Asistență tehnică', 'Asistență financiară'];
const SURSE_SUMA = {
  acord: ['din textul acordului', 'from the text of the agreement'],
  extern: ['sursă externă', 'external source'],
  titlu: ['din titlul actului', 'from the act title'],
  text: ['din textul actului', 'from the act text'],
  guvern: ['din nota Guvernului', 'from the Government note']
};
/* Denumirile complete ale donatorilor, pentru indiciul de sub acronim și pentru căutare. Acronimele sunt cele din registru. */
const NUME_DONATOR = {
  'AID': ['Asociația Internațională pentru Dezvoltare (Banca Mondială)', 'International Development Association (World Bank), IDA'],
  'BIRD': ['Banca Internațională pentru Reconstrucție și Dezvoltare (Banca Mondială)', 'International Bank for Reconstruction and Development (World Bank), IBRD'],
  'BERD': ['Banca Europeană pentru Reconstrucție și Dezvoltare', 'European Bank for Reconstruction and Development, EBRD'],
  'BEI': ['Banca Europeană de Investiții', 'European Investment Bank, EIB'],
  'CEB': ['Banca de Dezvoltare a Consiliului Europei', 'Council of Europe Development Bank'],
  'UE': ['Uniunea Europeană, Comisia Europeană', 'European Union, European Commission'],
  'AFD': ['Agenția Franceză de Dezvoltare, Franța', 'French Development Agency, France'],
  'KfW': ['Banca Germană de Dezvoltare, Germania', 'German Development Bank, Germany'],
  'GIZ': ['Agenția de Cooperare Internațională a Germaniei', 'German Agency for International Cooperation'],
  'JICA': ['Agenția Japoneză de Cooperare Internațională, Japonia', 'Japan International Cooperation Agency, Japan'],
  'FIDA': ['Fondul Internațional pentru Dezvoltare Agricolă', 'International Fund for Agricultural Development, IFAD'],
  'FICR': ['Federația Internațională a Societăților de Cruce Roșie și Semilună Roșie', 'International Federation of Red Cross and Red Crescent Societies'],
  'PNUD': ['Programul Națiunilor Unite pentru Dezvoltare', 'United Nations Development Programme, UNDP'],
  'PAM': ['Programul Alimentar Mondial', 'World Food Programme, WFP'],
  'FAO': ['Organizația pentru Alimentație și Agricultură a ONU', 'Food and Agriculture Organization of the UN'],
  'SUA': ['Statele Unite ale Americii, USAID', 'United States of America, USAID'],
  'SUA (MCC)': ['Corporația Provocările Mileniului, Statele Unite', 'Millennium Challenge Corporation, United States'],
  'IFC': ['Corporația Financiară Internațională', 'International Finance Corporation'],
  'Japonia': ['Japonia', 'Japan'], 'Japonia (JBIC)': ['Banca Export-Import a Japoniei', 'Export-Import Bank of Japan'],
  'Nordici': ['Danemarca, Norvegia, Fondul Nordic de Dezvoltare, NEFCO', 'Denmark, Norway, Nordic Development Fund, NEFCO'],
  'Banca Mondială': ['Banca Mondială', 'World Bank'],
  'Fondul Global': ['Fondul Global', 'Global Fund'],
  'Consiliul Europei': ['Consiliul Europei', 'Council of Europe'],
  'Bancă comercială străină': ['Bancă comercială străină', 'Foreign commercial bank'],
  'Regatul Unit': ['Regatul Unit', 'United Kingdom'], 'Elveția': ['Elveția', 'Switzerland'], 'Franța': ['Franța', 'France'],
  'România': ['România', 'Romania'], 'Germania': ['Germania', 'Germany'], 'Polonia': ['Polonia', 'Poland'],
  'Olanda': ['Olanda', 'Netherlands'], 'Turcia': ['Turcia', 'Türkiye'], 'Suedia': ['Suedia', 'Sweden'], 'Rusia': ['Rusia', 'Russia'],
  'Ungaria': ['Ungaria', 'Hungary'], 'Kuweit': ['Kuweit', 'Kuwait'], 'Italia': ['Italia', 'Italy'], 'Cehia': ['Cehia', 'Czechia'],
  'Belgia': ['Belgia', 'Belgium'], 'Austria': ['Austria', 'Austria'], 'Bulgaria': ['Bulgaria', 'Bulgaria'], 'Kazahstan': ['Kazahstan', 'Kazakhstan'],
  'China': ['China', 'China'], 'Canada': ['Canada', 'Canada'], 'CSI': ['Comunitatea Statelor Independente', 'Commonwealth of Independent States'],
  'Siemens (Germania)': ['Siemens (Germania)', 'Siemens (Germany)']
};
NUME_DONATOR[NEIDENTIFICAT] = ['Partener neidentificat în registru', 'Partner not identified in the register'];

/* ------------------------------------------------------------------ utilitare */
function fold(s) {
  return String(s == null ? '' : s).normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase();
}
function taie(s, n) {
  s = String(s == null ? '' : s);
  return s.length > n ? s.slice(0, n - 1).trimEnd() + '…' : s;
}
function slug(s) {
  return fold(s).replace(/[^a-z0-9]+/g, '-').replace(/^-+|-+$/g, '') || 'x';
}
function numar(v) { return typeof v === 'number' && isFinite(v); }
function pad(n) { return (n < 10 ? '0' : '') + n; }

/* 1250000.5 → „1.250.000,5” (română) sau „1,250,000.5” (engleză); cel mult `zec` zecimale, fără zerouri la coadă. */
function fmtSuma(v, en, zec) {
  if (!numar(v)) return '';
  zec = zec == null ? 2 : zec;
  const neg = v < 0 && Math.round(Math.abs(v) * Math.pow(10, zec)) > 0;
  const p = Math.abs(v).toFixed(zec).split('.');
  const int = p[0].replace(/\B(?=(\d{3})+(?!\d))/g, en ? ',' : '.');
  const fr = (p[1] || '').replace(/0+$/, '');
  return (neg ? '-' : '') + int + (fr ? (en ? '.' : ',') + fr : '');
}
/* Sumă exactă, cum o scrie un document: fără zecimale când e întreagă, altfel întotdeauna două: 1250000.5 → „1.250.000,50”
   (română) sau „1,250,000.50” (engleză). fmtSuma scoate zerourile de la coadă („1.250.000,5”), care la bani arată a greșeală. */
function fmtBani(v, en) {
  if (!numar(v)) return '';
  const cenți = Math.round(Math.abs(v) * 100);
  if (cenți % 100 === 0) return fmtSuma(v, en, 0);
  const p = (cenți / 100).toFixed(2).split('.');
  return (v < 0 ? '-' : '') + p[0].replace(/\B(?=(\d{3})+(?!\d))/g, en ? ',' : '.') + (en ? '.' : ',') + p[1];
}
/* Data cursurilor vine din registru în română („1 iulie 2026”); în pagina în engleză se scrie „1 July 2026”. */
const LUNI_EN = { ianuarie: 'January', februarie: 'February', martie: 'March', aprilie: 'April', mai: 'May', iunie: 'June',
                  iulie: 'July', august: 'August', septembrie: 'September', octombrie: 'October', noiembrie: 'November', decembrie: 'December' };
function dataTextEn(txt) {
  return String(txt == null ? '' : txt).replace(/[A-Za-zĂÂÎȘȚŞŢăâîșțşţ]+/g, function (m) { return LUNI_EN[m.toLowerCase()] || m; });
}
/* 340200000 → „340,2 mil.” (română) / „340.2 M” (engleză) */
function fmtCompact(v, en) {
  if (!numar(v)) return '';
  const a = Math.abs(v), z = (x, d) => { let t = x.toFixed(d); if (t.indexOf('.') >= 0) t = t.replace(/\.?0+$/, ''); return t.replace('.', en ? '.' : ','); };
  const s = a >= 1e9 ? z(a / 1e9, 2) + (en ? ' bn' : ' mld.') : a >= 1e6 ? z(a / 1e6, 1) + (en ? ' M' : ' mil.')
    : a >= 1e3 ? z(a / 1e3, 0) + (en ? ' K' : ' mii') : z(a, 0);
  return (v < 0 ? '-' : '') + s;
}
/* Ce scrie omul în câmpul „Suma”: „1.250.000,50”, „1,250,000.50”, „1 250 000,5”, „1250000.5”. Întoarce un număr sau NaN. */
function parseSuma(txt) {
  const s = String(txt == null ? '' : txt).replace(/[\s  ']/g, '');
  if (!s || !/^[0-9.,]+$/.test(s) || !/[0-9]/.test(s)) return NaN;
  const lp = s.lastIndexOf('.'), lv = s.lastIndexOf(',');
  let dec = null;
  if (lp >= 0 && lv >= 0) dec = lp > lv ? '.' : ',';
  else if (lp >= 0 || lv >= 0) {
    const sep = lp >= 0 ? '.' : ',', parti = s.split(sep);
    if (parti.length > 2) dec = null;                                         // 1.234.567 → separatori de mii
    else if (/^[1-9]\d{0,2}$/.test(parti[0]) && /^\d{3}$/.test(parti[1])) dec = null; // 1.250 → o mie două sute cincizeci (dar 0,123 e zecimală)
    else dec = sep;                                                           // 0,5 · 12,75 → zecimale
  }
  let intreg = s, frac = '';
  if (dec) {
    const k = s.lastIndexOf(dec);
    intreg = s.slice(0, k); frac = s.slice(k + 1);
    if (intreg.indexOf(dec) >= 0) return NaN;                                 // „1,234,5,6”
  }
  const alt = dec === '.' ? ',' : dec === ',' ? '.' : null;
  if (/[.,]/.test(intreg)) {                                                  // separatorii de mii trebuie să fie în grupe de câte trei
    if (!/^\d{1,3}([.,]\d{3})+$/.test(intreg)) return NaN;
    const sepi = intreg.replace(/\d/g, '');
    if (alt && sepi.split(alt).join('').length) return NaN;                   // amestec
    if (!alt && sepi.split(sepi.charAt(0)).join('').length) return NaN;       // „1.234,567” nu are sens fără zecimale
  }
  intreg = intreg.replace(/[.,]/g, '');
  if (!/^\d*$/.test(intreg) || !/^\d*$/.test(frac) || (!intreg && !frac)) return NaN;
  const v = parseFloat((intreg || '0') + (frac ? '.' + frac : ''));
  return isFinite(v) ? v : NaN;
}

function dataRo(iso) {
  const m = /^(\d{4})-(\d{2})-(\d{2})/.exec(iso || '');
  return m ? m[3] + '.' + m[2] + '.' + m[1] : (iso || '');
}
function esteDataIso(s) {
  const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(String(s || ''));
  if (!m) return false;
  const d = new Date(Date.UTC(+m[1], +m[2] - 1, +m[3]));
  return d.getUTCFullYear() === +m[1] && d.getUTCMonth() === +m[2] - 1 && d.getUTCDate() === +m[3];
}
function aziIso(d) {
  d = d || new Date();
  return d.getFullYear() + '-' + pad(d.getMonth() + 1) + '-' + pad(d.getDate());
}
function dataOraRo(d) {
  d = d || new Date();
  return pad(d.getDate()) + '.' + pad(d.getMonth() + 1) + '.' + d.getFullYear() + ', ' + pad(d.getHours()) + ':' + pad(d.getMinutes());
}
/* „01.10.2026” → „2026-10-01”, pentru comparații */
function ordRo(ro) {
  const m = /^(\d{2})\.(\d{2})\.(\d{4})$/.exec(ro || '');
  return m ? m[3] + m[2] + m[1] : '';
}

/* ------------------------------------------------------------------ acordurile și donatorii */
/* Donatorii unui acord: partenerii din registru, desfăcuți la „ / ”. Același lucru face filtrul „Partener” al registrului. */
function donatoriiAcordului(parteneri) {
  const v = [];
  String(parteneri || '').split('/').forEach(function (x) {
    x = x.replace(/\s+/g, ' ').trim();
    if (x && v.indexOf(x) < 0) v.push(x);
  });
  return v.length ? v : [NEIDENTIFICAT];
}
/* Denumirile din registru se taie uneori în mijlocul unei paranteze („Proiectul de dezvoltare al sistemului electroenergetic (”). */
function curataNume(s) {
  s = String(s == null ? '' : s).replace(/\s+/g, ' ').trim();
  const deschise = (s.match(/\(/g) || []).length, inchise = (s.match(/\)/g) || []).length;
  if (deschise > inchise) s = s.slice(0, s.lastIndexOf('(')).trim();
  return s.replace(/[\s(\[,;:–-]+$/, '');
}
function stadiu(et) {
  et = et || [];
  for (let i = 0; i < STADII.length; i++) if (et.indexOf(STADII[i][0]) >= 0) return STADII[i][0];
  return '';
}
function etichetaStadiu(k, en) {
  for (let i = 0; i < STADII.length; i++) if (STADII[i][0] === k) return STADII[i][en ? 2 : 1];
  return '';
}
function etichetaTip(c, en) { return en ? (TIPURI_EN[c] || c) : c; }
function numeDonator(k, en) { const x = NUME_DONATOR[k]; return x ? x[en ? 1 : 0] : k; }

/* Cursurile (unități de valută pentru 1 EUR). Cele exacte vin în fișier (cursuri); la un fișier mai vechi le deducem din rânduri. */
function deduCursuri(acorduri) {
  const c = { EUR: 1 }, v = {};
  (acorduri || []).forEach(function (a) {
    const s = a && a.suma;
    if (s && numar(s.v) && numar(s.eur) && s.eur > 0 && s.v > 0) (v[s.val] = v[s.val] || []).push(s.v / s.eur);
  });
  Object.keys(v).forEach(function (k) {
    const l = v[k].sort(function (a, b) { return a - b; });
    c[k] = l[Math.floor(l.length / 2)];
  });
  return c;
}

/* Rândurile fișierului date/acorduri_legare.json, pregătite pentru pagină. */
function pregateste(json) {
  json = json || {};
  const brut = Array.isArray(json.acorduri) ? json.acorduri : [];
  const cursuri = json.cursuri && Object.keys(json.cursuri).length ? Object.assign({}, json.cursuri) : deduCursuri(brut);
  cursuri.EUR = 1;
  const acorduri = [], peId = new Map(), peDonator = new Map(), peAct = new Map();
  brut.forEach(function (a) {
    if (!a || !a.id || peId.has(a.id)) return;
    const s = a.suma && numar(a.suma.v) && a.suma.v > 0 ? a.suma : null;
    const eur = s ? (cursuri[s.val] ? s.v / cursuri[s.val] : (numar(s.eur) ? s.eur : null)) : null;
    const inTotal = a.inTotal || (s ? (a.faraTotal ? 'fara_total' : (eur == null ? 'fara_curs' : 'numarat')) : 'fara_suma');
    const acte = (a.acte || []).map(function (x) { return { act: x.act || '', tip: x.tip || '', data: x.data || '', url: x.url || '', etape: x.etape || [] }; });
    const x = {
      id: a.id,
      nume: curataNume(a.scurt || a.nume) || a.nume || a.id,
      numeComplet: String(a.nume || '').replace(/\s+/g, ' ').trim(),
      categorie: a.categorie || '',
      parteneriText: a.parteneri || '',
      donatori: donatoriiAcordului(a.parteneri),
      stadiu: stadiu(a.et), etape: a.et || [],
      semnat: a.semnat || '', primul: a.primul || '', ultimul: a.ultimul || '',
      suma: s, sursaSuma: s ? (s.sursa || '') : '', actSuma: s ? (s.act || '') : '',
      eur: eur, inTotal: inTotal, eurTotal: inTotal === 'numarat' ? eur : null,
      alte: a.alte || [], cost: a.cost || null,
      acte: acte, coduri: acte.map(function (y) { return y.act; }).filter(Boolean),
      url: (acte.filter(function (y) { return y.url; })[0] || {}).url || ''
    };
    acorduri.push(x); peId.set(x.id, x);
    x.coduri.forEach(function (c) { (peAct.get(c) || peAct.set(c, []).get(c)).push(x); });
    x.donatori.forEach(function (d) { (peDonator.get(d) || peDonator.set(d, []).get(d)).push(x); });
  });
  const donatori = Array.from(peDonator.keys()).map(function (k) { return { cheie: k, acorduri: peDonator.get(k) }; });
  return { acorduri: acorduri, peId: peId, peAct: peAct, donatori: donatori, peDonator: peDonator, cursuri: cursuri,
           cursData: json.curs_data || '', actualizat: json.actualizat || '' };
}

/* Descrierea succintă din coloana a doua: titlul acordului, când spune mai mult decât denumirea; altfel o frază din ce se știe
   (tipul, donatorul, semnarea, ultimele acte, stadiul): pentru unele acorduri registrul nu are decât denumirea. */
function descriere(a, en) {
  // Un titlu care începe cu literă mică e un fragment dintr-un titlu mai lung („proiectului …”, „acordarea deplinelor puteri …”): nu se înțelege singur.
  if (a.numeComplet && a.numeComplet.length > a.nume.length + 12 && fold(a.numeComplet) !== fold(a.nume) && /^[A-ZĂÂÎȘȚŞŢ0-9„"“(]/.test(a.numeComplet)) return a.numeComplet;
  const t = etichetaTip(a.categorie, en), p = a.donatori.join(' / ');
  const semnat = a.semnat ? (en ? ', signed on ' : ', semnat la ') + a.semnat : '';
  const acte = (a.acte || []).slice(0, 3).map(function (x) { return x.act + (x.data ? (en ? ' of ' : ' din ') + x.data : ''); });
  const maiMulte = (a.acte || []).length - acte.length;
  const ac = acte.length ? (en ? ' Acts: ' : ' Acte: ') + acte.join(', ') + (maiMulte > 0 ? (en ? ' and ' + maiMulte + ' more' : ' și încă ' + maiMulte) : '') + '.' : '';
  const st = a.stadiu ? (en ? ' Stage: ' : ' Stadiu: ') + etichetaStadiu(a.stadiu, en).toLowerCase() + '.' : '';
  if (en) return (t || 'Agreement') + (a.donatori[0] === NEIDENTIFICAT ? '' : ' from ' + p) + semnat + '.' + ac + st;
  return (t || 'Acord') + (a.donatori[0] === NEIDENTIFICAT ? '' : ' de la ' + p) + semnat + '.' + ac + st;
}

/* ------------------------------------------------------------------ debursările */
function idNou() {
  return 'd' + Date.now().toString(36) + Math.random().toString(36).slice(2, 7);
}
function cursDe(cursuri, val) { return cursuri && numar(cursuri[val]) && cursuri[val] > 0 ? cursuri[val] : null; }
function eurIntrare(e, cursuri) {
  const c = cursDe(cursuri, e.val);
  return c && numar(e.suma) ? e.suma / c : null;
}
function intrareValida(e) {
  return !!(e && typeof e.id === 'string' && e.id && typeof e.acord === 'string' && numar(e.suma) && e.suma > 0 && typeof e.val === 'string' && e.val);
}
/* Verifică ce a scris omul în formular. Întoarce { ok, erori: {camp: cod}, valoare: {data, suma, val, nota} }. */
function valideazaFormular(c, cursuri, acum) {
  const erori = {}, v = {};
  v.data = String(c.data || '').trim();
  if (!esteDataIso(v.data)) erori.data = 'lipsa';
  else if (v.data > aziIso(acum)) erori.data = 'viitor';
  else if (v.data < '1990-01-01') erori.data = 'veche';
  v.suma = parseSuma(c.suma);
  if (!numar(v.suma)) erori.suma = String(c.suma || '').trim() ? 'format' : 'lipsa';
  else if (v.suma <= 0) erori.suma = 'zero';
  else if (v.suma > MAX_SUMA) erori.suma = 'mare';
  v.val = String(c.val || '').trim().toUpperCase();
  if (!cursDe(cursuri, v.val)) erori.val = 'valuta';
  v.nota = String(c.nota || '').replace(/\s+/g, ' ').trim();
  if (v.nota.length > MAX_NOTA) erori.nota = 'lunga';
  return { ok: !Object.keys(erori).length, erori: erori, valoare: v };
}
function intrareDin(acord, valoare, acum) {
  return {
    id: idNou(), acord: acord.id, acte: acord.coduri.slice(0, 12), nume: taie(acord.nume, 160),
    data: valoare.data, suma: Math.round(valoare.suma * 100) / 100, val: valoare.val, nota: valoare.nota,
    la: (acum || new Date()).toISOString()
  };
}
/* Leagă debursările de acorduri. Id-ul unui acord e cel al actului lui cel mai vechi și se poate schimba (se unesc două rânduri,
   apare un act mai vechi): atunci îl regăsim după oricare dintre actele păstrate în debursare. Ce nu se leagă nicicum e „orfan”. */
function lega(intrari, baza) {
  const peAcord = new Map(), orfane = [];
  (intrari || []).forEach(function (e) {
    if (!intrareValida(e)) return;
    let a = baza.peId.get(e.acord);
    if (!a && Array.isArray(e.acte)) {
      const voturi = new Map();
      e.acte.forEach(function (c) { (baza.peAct.get(c) || []).forEach(function (x) { voturi.set(x, (voturi.get(x) || 0) + 1); }); });
      let max = 0;
      voturi.forEach(function (n, x) { if (n > max) { max = n; a = x; } });
    }
    if (!a) { orfane.push(e); return; }
    (peAcord.get(a.id) || peAcord.set(a.id, []).get(a.id)).push(e);
  });
  const ord = function (x, y) { return (y.data || '').localeCompare(x.data || '') || (y.la || '').localeCompare(x.la || ''); };
  peAcord.forEach(function (l) { l.sort(ord); });
  orfane.sort(ord);
  return { peAcord: peAcord, orfane: orfane };
}

/* Debursările unui acord: câte sunt, cât fac în euro și în valuta acordului, ultima dată, cât la sută din sumă. */
function agregaAcord(a, intrari, cursuri) {
  intrari = intrari || [];
  const r = { n: intrari.length, eur: 0, inVal: null, valuta: a.suma ? a.suma.val : 'EUR', ultima: '', faraCurs: 0, pct: null, rest: null };
  let directe = 0, convertite = 0;
  intrari.forEach(function (e) {
    if ((e.data || '') > r.ultima) r.ultima = e.data;
    const x = eurIntrare(e, cursuri);
    if (x == null) { r.faraCurs++; return; }
    r.eur += x;
    if (e.val === r.valuta) directe += e.suma; else convertite += x;     // în valuta acordului: suma exactă, fără conversie dus-întors
  });
  const c = cursDe(cursuri, r.valuta);
  if (c) r.inVal = Math.round((directe + convertite * c) * 100) / 100;
  if (a.eurTotal != null && a.eurTotal > 0) { r.pct = r.eur / a.eurTotal; r.rest = a.eurTotal - r.eur; }
  return r;
}
/* Totalul unei liste de acorduri (un donator sau mai mulți, fiecare acord o singură dată). */
function rezumat(acorduri, peAcord, cursuri) {
  const vazut = new Set(), r = { n: 0, cuSuma: 0, sumaEur: 0, debEur: 0, debPeSuma: 0, nCuDeb: 0, nIntrari: 0, ultima: '', faraCurs: 0, pct: null, rest: null };
  acorduri.forEach(function (a) {
    if (vazut.has(a.id)) return;
    vazut.add(a.id);
    const g = agregaAcord(a, peAcord.get(a.id) || [], cursuri);
    r.n++;
    if (a.eurTotal != null) { r.cuSuma++; r.sumaEur += a.eurTotal; r.debPeSuma += g.eur; }
    r.debEur += g.eur; r.nIntrari += g.n; r.faraCurs += g.faraCurs;
    if (g.n) r.nCuDeb++;
    if (g.ultima > r.ultima) r.ultima = g.ultima;
  });
  if (r.sumaEur > 0) { r.pct = r.debPeSuma / r.sumaEur; r.rest = r.sumaEur - r.debPeSuma; }
  return r;
}

/* ------------------------------------------------------------------ filtre și ordonare */
function potriveste(a, f) {
  if (f.tip && a.categorie !== f.tip) return false;
  const n = (f.peAcord && f.peAcord.get(a.id) || []).length;
  if (f.deb === 'cu' && !n) return false;
  if (f.deb === 'fara' && n) return false;
  if (f.q) {
    const hay = fold([a.nume, a.numeComplet, a.parteneriText, a.coduri.join(' '), a.categorie, a.semnat].join(' '));
    const cuv = fold(f.q).split(/\s+/).filter(Boolean);
    if (!cuv.every(function (c) { return hay.indexOf(c) >= 0; })) return false;
  }
  return true;
}
function ordoneaza(lista, sort, peAcord, cursuri) {
  const g = new Map();
  const ag = function (a) { let x = g.get(a.id); if (!x) { x = agregaAcord(a, peAcord.get(a.id) || [], cursuri); g.set(a.id, x); } return x; };
  const nulLa = function (x, y, desc) {           // valorile lipsă merg la coadă, indiferent de sens
    if (x == null && y == null) return 0;
    if (x == null) return 1;
    if (y == null) return -1;
    return desc ? y - x : x - y;
  };
  const dupa = {
    suma: function (a, b) { return nulLa(a.eur, b.eur, true); },
    deb: function (a, b) { return ag(b).eur - ag(a).eur; },
    pct: function (a, b) { return nulLa(ag(a).pct, ag(b).pct, true); },
    nume: function (a, b) { return a.nume.localeCompare(b.nume, 'ro'); },
    data: function (a, b) { return (ordRo(b.semnat) || ordRo(b.primul)).localeCompare(ordRo(a.semnat) || ordRo(a.primul)); }
  }[sort] || function () { return 0; };
  return lista.slice().sort(function (a, b) { return dupa(a, b) || a.nume.localeCompare(b.nume, 'ro'); });
}
/* Donatorii pentru lista cu căsuțe: după număr de proiecte, după sumă, după debursări sau alfabetic. */
function ordoneazaDonatori(donatori, sort, peAcord, cursuri, en) {
  const r = new Map();
  const rez = function (d) { let x = r.get(d.cheie); if (!x) { x = rezumat(d.acorduri, peAcord, cursuri); r.set(d.cheie, x); } return x; };
  const cmp = {
    n: function (a, b) { return rez(b).n - rez(a).n; },
    suma: function (a, b) { return rez(b).sumaEur - rez(a).sumaEur; },
    deb: function (a, b) { return rez(b).debEur - rez(a).debEur; },
    nume: function () { return 0; }
  }[sort] || function () { return 0; };
  return donatori.slice().sort(function (a, b) {
    return cmp(a, b) || (a.cheie === NEIDENTIFICAT) - (b.cheie === NEIDENTIFICAT) || a.cheie.localeCompare(b.cheie, en ? 'en' : 'ro');
  });
}
/* Adresa paginii poate purta selecția: #d=BERD|BEI&q=…&tip=Grant&deb=cu&sort=deb */
function citesteHash(h) {
  const o = { d: [], q: '', tip: '', deb: '', sort: '' };
  String(h || '').replace(/^#/, '').split('&').forEach(function (p) {
    const i = p.indexOf('=');
    if (i < 0) return;
    let k = p.slice(0, i), v = '';
    try { v = decodeURIComponent(p.slice(i + 1).replace(/\+/g, ' ')); } catch (e) { return; }
    if (k === 'd') o.d = v.split('|').filter(Boolean);
    else if (k === 'q' || k === 'tip') o[k] = v.slice(0, 120);
    else if (k === 'deb') o.deb = /^(cu|fara)$/.test(v) ? v : '';
    else if (k === 'sort') o.sort = /^(suma|deb|pct|nume|data)$/.test(v) ? v : '';
  });
  return o;
}
function scrieHash(o) {
  const p = [];
  if (o.d && o.d.length) p.push('d=' + o.d.map(encodeURIComponent).join('|'));
  if (o.q) p.push('q=' + encodeURIComponent(o.q));
  if (o.tip) p.push('tip=' + encodeURIComponent(o.tip));
  if (o.deb) p.push('deb=' + o.deb);
  if (o.sort && o.sort !== 'suma') p.push('sort=' + o.sort);
  return p.length ? '#' + p.join('&') : '';
}

/* ------------------------------------------------------------------ „baza de date”: fișierul date/debursari.json */
class EroareDepozit extends Error {
  constructor(cod, mesaj, status) { super(mesaj); this.name = 'EroareDepozit'; this.cod = cod; this.status = status || 0; }
}
function dateGoale() { return { versiune: 1, actualizat: '', intrari: [] }; }
function citesteText(text) {
  let o;
  try { o = JSON.parse(String(text).replace(/^﻿/, '')); } catch (e) { throw new EroareDepozit('format', 'Fișierul cu debursări nu e un JSON valid.'); }
  if (!o || typeof o !== 'object' || Array.isArray(o)) throw new EroareDepozit('format', 'Fișierul cu debursări are alt format decât cel așteptat.');
  if (o.intrari == null) o.intrari = [];
  if (!Array.isArray(o.intrari)) throw new EroareDepozit('format', 'Fișierul cu debursări are alt format decât cel așteptat.');
  return o;
}
/* Operații: {t:'add', e}, {t:'upd', e}, {t:'del', id}. Se aplică pe orice stare a fișierului, deci se pot reaplica peste varianta mai nouă a cuiva altcuiva. */
function aplicaOps(date, ops, acum) {
  const nou = Object.assign({}, date, { intrari: (date.intrari || []).slice() });
  (ops || []).forEach(function (op) {
    if (op.t === 'del') nou.intrari = nou.intrari.filter(function (x) { return x.id !== op.id; });
    else if (op.t === 'add' || op.t === 'upd') {
      const i = nou.intrari.findIndex(function (x) { return x.id === op.e.id; });
      const e = Object.assign({}, op.e);
      if (i >= 0) nou.intrari[i] = op.t === 'upd' ? Object.assign({}, nou.intrari[i], e) : e;
      else nou.intrari.push(e);
    }
  });
  nou.versiune = 1;
  nou.actualizat = (acum || new Date()).toISOString();
  return nou;
}
/* Fișierul se scrie cu o înregistrare pe linie: o modificare se vede în git ca o linie, nu ca un fișier întreg. */
function text(date) {
  const cap = JSON.stringify({ versiune: date.versiune || 1, actualizat: date.actualizat || '' });
  const l = (date.intrari || []).map(function (e) { return JSON.stringify(e); });
  return cap.slice(0, -1) + ',"intrari":[' + (l.length ? '\n' + l.join(',\n') + '\n' : '') + ']}\n';
}
function b64DinText(s) {
  const b = new TextEncoder().encode(s);
  let bin = '';
  for (let i = 0; i < b.length; i += 0x8000) bin += String.fromCharCode.apply(null, b.subarray(i, i + 0x8000));
  return root.btoa(bin);
}
function textDinB64(b) {
  const bin = root.atob(String(b).replace(/\s+/g, ''));
  const x = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) x[i] = bin.charCodeAt(i);
  return new TextDecoder('utf-8').decode(x);
}
const pauza = function (ms) { return new Promise(function (ok) { setTimeout(ok, ms); }); };

/* Clientul pentru API-ul „Contents” al GitHub. `opt.fetch` se poate înlocui (în teste). Cheia merge doar în antetul Authorization. */
function Depozit(opt) {
  opt = opt || {};
  const cfg = Object.assign({}, CONFIG, opt);
  const F = opt.fetch || function () { return root.fetch.apply(root, arguments); };
  const urlFisier = cfg.api + '/repos/' + cfg.repo + '/contents/' + cfg.cale.split('/').map(encodeURIComponent).join('/');
  async function cere(met, url, token, corp, antet) {
    const h = Object.assign({ Accept: 'application/vnd.github+json' }, antet || {});
    if (token) h.Authorization = 'Bearer ' + token;
    if (corp) h['Content-Type'] = 'application/json';
    try {
      return await F(url, { method: met, headers: h, body: corp ? JSON.stringify(corp) : undefined, cache: 'no-store' });
    } catch (e) {
      throw new EroareDepozit('retea', 'Nu pot ajunge la GitHub. Verifică conexiunea la internet și încearcă din nou.');
    }
  }
  async function mesajDin(r) {
    try { const j = await r.json(); return j && j.message ? String(j.message).slice(0, 200) : ''; } catch (e) { return ''; }
  }
  async function eroare(r, ce) {
    const st = r.status, det = await mesajDin(r);
    const limita = st === 429 || (st === 403 && r.headers && r.headers.get && r.headers.get('x-ratelimit-remaining') === '0');
    if (st === 401) return new EroareDepozit('token', 'Codul nu e valid sau a expirat.', st);
    if (limita) return new EroareDepozit('limita', 'GitHub a limitat temporar cererile. Încearcă din nou peste câteva minute.', st);
    if (st === 403 || (st === 404 && ce === 'scriere')) return new EroareDepozit('drept', 'Codul nu are dreptul să scrie în repository-ul ' + cfg.repo + ' (are nevoie de „Contents: Read and write”).', st);
    if (st === 404) return new EroareDepozit('repo', 'Nu găsesc repository-ul ' + cfg.repo + ' cu acest cod.', st);
    if (st === 409 || st === 422) return new EroareDepozit('conflict', 'Fișierul s-a schimbat între timp.' + (det ? ' (' + det + ')' : ''), st);
    return new EroareDepozit('alt', 'GitHub a răspuns cu eroarea ' + st + (det ? ': ' + det : '') + '.', st);
  }
  /* Codul e bun? Are drept de scriere? Se află înainte ca omul să scrie ceva. */
  async function verifica(token) {
    const r = await cere('GET', cfg.api + '/repos/' + cfg.repo, token);
    if (!r.ok) throw await eroare(r, 'citire');
    let j = null;
    try { j = await r.json(); } catch (e) { /* fără detalii */ }
    if (j && j.permissions && j.permissions.push === false) {
      throw new EroareDepozit('drept', 'Codul poate citi repository-ul ' + cfg.repo + ', dar nu poate scrie în el (are nevoie de „Contents: Read and write”).', 403);
    }
    return { ok: true, scrie: j && j.permissions ? !!j.permissions.push : null };
  }
  /* Starea de acum a fișierului, prin API (fără întârzierea publicării site-ului). */
  async function citeste(token) {
    const url = urlFisier + '?ref=' + encodeURIComponent(cfg.ramura);
    const r = await cere('GET', url, token);
    if (r.status === 404) return { date: dateGoale(), sha: null, nou: true };
    if (!r.ok) throw await eroare(r, 'citire');
    const j = await r.json();
    let t;
    if (j && j.encoding === 'base64' && typeof j.content === 'string') t = textDinB64(j.content);
    else {                                                         // fișier între 1 și 100 MB: doar forma brută
      const r2 = await cere('GET', url, token, null, { Accept: 'application/vnd.github.raw+json' });
      if (!r2.ok) throw await eroare(r2, 'citire');
      t = await r2.text();
    }
    return { date: citesteText(t), sha: j.sha || null, nou: false };
  }
  /* Aplică operațiile peste varianta curentă a fișierului și o scrie. Dacă între timp altcineva a scris (409/422), citește din
     nou și reaplică aceleași operații: nimeni nu pierde ce a introdus. */
  async function salveaza(token, ops, mesaj, incercari) {
    incercari = incercari || 4;
    let ultima = null;
    for (let i = 1; i <= incercari; i++) {
      const cur = await citeste(token);
      const nou = aplicaOps(cur.date, ops);
      const corp = { message: mesaj, content: b64DinText(text(nou)), branch: cfg.ramura };
      if (cur.sha) corp.sha = cur.sha;
      const r = await cere('PUT', urlFisier, token, corp);
      if (r.ok) {
        let j = null;
        try { j = await r.json(); } catch (e) { /* fără detalii */ }
        return { date: nou, sha: j && j.content ? j.content.sha : null, commit: j && j.commit ? j.commit.sha : null };
      }
      ultima = await eroare(r, 'scriere');
      if (ultima.cod !== 'conflict') throw ultima;
      await (opt.pauza || pauza)(250 * i);
    }
    throw new EroareDepozit('conflict', 'Nu am putut salva: fișierul se tot schimbă. Încearcă din nou peste câteva secunde.', 409);
  }
  /* Fișierul așa cum îl vede oricine, fără cod: copia publicată pe site. */
  async function citestePublic() {
    let r;
    try { r = await F(cfg.sursaDate, { cache: 'no-cache' }); } catch (e) { throw new EroareDepozit('retea', 'Nu pot citi debursările.'); }
    if (r.status === 404) return dateGoale();
    if (!r.ok) throw new EroareDepozit('alt', 'Nu pot citi debursările (eroarea ' + r.status + ').', r.status);
    return citesteText(await r.text());
  }
  return { verifica: verifica, citeste: citeste, salveaza: salveaza, citestePublic: citestePublic, cfg: cfg };
}

/* ------------------------------------------------------------------ cheia, protejată cu PIN */
const Seif = (function () {
  const web = function () {
    if (root.crypto && root.crypto.subtle) return root.crypto;
    try { if (typeof require === 'function') return require('crypto').webcrypto || null; } catch (e) { /* în browser nu există */ }
    return null;
  };
  const subtle = function () { const w = web(); return w ? w.subtle : null; };
  const b64 = function (u8) { let s = ''; for (let i = 0; i < u8.length; i++) s += String.fromCharCode(u8[i]); return root.btoa(s); };
  const ub64 = function (s) { const b = root.atob(s), u = new Uint8Array(b.length); for (let i = 0; i < b.length; i++) u[i] = b.charCodeAt(i); return u; };
  async function cheie(pin, sare, iteratii) {
    const baza = await subtle().importKey('raw', new TextEncoder().encode(pin), 'PBKDF2', false, ['deriveKey']);
    return subtle().deriveKey({ name: 'PBKDF2', salt: sare, iterations: iteratii, hash: 'SHA-256' }, baza, { name: 'AES-GCM', length: 256 }, false, ['encrypt', 'decrypt']);
  }
  return {
    disponibil: function () { return !!subtle(); },
    async impacheteaza(token, pin, iteratii) {
      iteratii = iteratii || 250000;
      const sare = web().getRandomValues(new Uint8Array(16)), iv = web().getRandomValues(new Uint8Array(12));
      const k = await cheie(pin, sare, iteratii);
      const ct = await subtle().encrypt({ name: 'AES-GCM', iv: iv }, k, new TextEncoder().encode(token));
      return { v: 1, i: iteratii, s: b64(sare), n: b64(iv), c: b64(new Uint8Array(ct)) };
    },
    async deschide(obj, pin) {
      if (!obj || obj.v !== 1 || !obj.s || !obj.n || !obj.c) throw new EroareDepozit('seif', 'Codul salvat pe acest dispozitiv nu poate fi citit.');
      try {
        const k = await cheie(pin, ub64(obj.s), +obj.i || 250000);
        const t = await subtle().decrypt({ name: 'AES-GCM', iv: ub64(obj.n) }, k, ub64(obj.c));
        return new TextDecoder().decode(t);
      } catch (e) { throw new EroareDepozit('pin', 'PIN greșit.'); }
    }
  };
})();

/* ------------------------------------------------------------------ Excel */
/* Specificațiile pentru XlsxStil.construieste (vezi xlsx-stil.js). Toate primesc un context:
     { t(ro, en), en, baza (adresa paginii), cursuri, cursData, peAcord (Map id → debursări), generat (text), sursaData (data registrului) } */
const CULORI_TIP = [['Grant', 'FF155A52', 'FFE0F2F0'], ['Împrumut', 'FFA3311E', 'FFFBE8E3'], ['Asistență tehnică', 'FF3D5A80', 'FFE8EEF7'], ['Asistență financiară', 'FF8A5C0D', 'FFFDF1DC'],
                     ['Grant', 'FF155A52', 'FFE0F2F0'], ['Loan', 'FFA3311E', 'FFFBE8E3'], ['Technical assistance', 'FF3D5A80', 'FFE8EEF7'], ['Financial assistance', 'FF8A5C0D', 'FFFDF1DC']];
function textInTotal(stare, t) {
  return { numarat: t('da', 'yes'), dublura: t('nu: dublură', 'no: duplicate'), fara_total: t('nu: nu se adună', 'no: not added up'), fara_curs: t('nu: fără curs', 'no: no rate') }[stare] || '';
}
function subtitluComun(c, ce, extra) {
  extra = extra || c.filtre;                 // filtrele active din pagină: se văd în antetul fișierului
  return c.t('Sursa: registrul acordurilor din legis.md', 'Source: the agreements register from legis.md') + ' · ' + ce +
    (extra ? ' · ' + extra : '') + ' · ' +
    c.t('sume în EUR, la cursurile BCE din ', 'amounts in EUR, at the ECB rates of ') + (c.cursData || '—') + ' · ' +
    c.t('debursări introduse manual · generat ', 'disbursements entered manually · generated ') + c.generat;
}
function foaieProiecte(c, o) {
  const t = c.t, en = c.en;
  const cols = [];
  const col = function (nume, tip, lat) { cols.push([nume, tip, lat]); return cols.length - 1; };
  const cProiect = col(t('Proiectul', 'Project'), 't', 38);
  const cDon = o.cuDonatori ? col(t('Donatori', 'Donors'), 't', 16) : -1;
  const cDesc = col(t('Descriere succintă', 'Short description'), 't', 56);
  const cTip = col(t('Tip de finanțare', 'Type of financing'), 't', 18);
  const cStadiu = col(t('Stadiu', 'Stage'), 't', 18);
  const cSemnat = col(t('Semnat', 'Signed'), 'z', 12);
  const cSuma = col(t('Suma proiectului', 'Project amount'), 'e', 16);
  const cVal = col(t('Valuta', 'Currency'), 'c', 8);
  const cEur = col(t('Echivalent EUR', 'EUR equivalent'), 'e', 16);
  const cDebVal = col(t('Debursat (în valuta proiectului)', 'Disbursed (in the project currency)'), 'e', 18);
  const cDebEur = col(t('Debursat (echivalent EUR)', 'Disbursed (EUR equivalent)'), 'e', 17);
  const cPct = col(t('% debursat', '% disbursed'), 'p', 11);
  const cRest = col(t('Rest de debursat (EUR)', 'Left to disburse (EUR)'), 'e', 17);
  const cNr = col(t('Nr. debursări', 'No. of disbursements'), 'n', 11);
  const cUltima = col(t('Ultima debursare', 'Last disbursement'), 'z', 13);
  const cInTotal = col(t('Intră în total?', 'In the total?'), 'c', 16);
  const cLink = col(t('Link legis.md', 'legis.md link'), 't', 13);
  const randuri = [], urluri = [];
  o.acorduri.forEach(function (a) {
    const g = agregaAcord(a, c.peAcord.get(a.id) || [], c.cursuri), r = [];
    r[cProiect] = a.nume;
    if (cDon >= 0) r[cDon] = a.donatori.join(' / ');
    r[cDesc] = descriere(a, en);
    r[cTip] = etichetaTip(a.categorie, en);
    r[cStadiu] = etichetaStadiu(a.stadiu, en);
    r[cSemnat] = a.semnat || '';
    r[cSuma] = a.suma ? a.suma.v : ''; r[cVal] = a.suma ? a.suma.val : '';
    r[cEur] = a.eurTotal != null ? Math.round(a.eurTotal) : '';
    r[cDebVal] = g.n && g.inVal != null ? g.inVal : '';
    r[cDebEur] = g.n ? Math.round(g.eur) : '';
    r[cPct] = g.pct != null ? Math.round(g.pct * 1000) / 10 : '';
    r[cRest] = g.rest != null ? Math.round(g.rest) : '';
    r[cNr] = g.n;
    r[cUltima] = g.ultima || '';
    r[cInTotal] = textInTotal(a.inTotal, t);
    r[cLink] = a.url ? 'legis.md' : '';
    randuri.push(r); urluri.push(a.url);
  });
  const latimi = {}; cols.forEach(function (x, k) { latimi[k] = x[2]; });
  const etichete = {}; etichete[cTip] = CULORI_TIP;
  etichete[cInTotal] = [[t('da', 'yes'), 'FF16794F', 'FFE3F4EC'], [t('nu: dublură', 'no: duplicate'), 'FF6B7284', 'FFEEF0F4'],
                        [t('nu: nu se adună', 'no: not added up'), 'FF6B7284', 'FFEEF0F4'], [t('nu: fără curs', 'no: no rate'), 'FF6B7284', 'FFEEF0F4']];
  const linkuri = {}; linkuri[cLink] = function (rand, i) { return urluri[i]; };
  const re = rezumat(o.acorduri, c.peAcord, c.cursuri);
  const note = [
    t('Un rând = un acord din registrul legis.md (actele aceluiași acord sunt grupate). „Suma proiectului” e suma acordului, așa cum o arată registrul; ' +
      '„Echivalent EUR” e suma trecută în euro la cursurile BCE din ' + (c.cursData || '—') + ', doar pentru rândurile care intră în total (vezi coloana „Intră în total?”).',
      'One row = one agreement from the legis.md register (acts of the same agreement are grouped). "Project amount" is the agreement amount as the register shows it; ' +
      '"EUR equivalent" is the amount in euro at the ECB rates of ' + (c.cursData || '—') + ', only for the rows that count in the total (see the "In the total?" column).'),
    t('Debursările sunt introduse de mână (foaia „Debursări”); nu provin dintr-o sursă oficială. „% debursat” și „Rest de debursat” se calculează doar pentru rândurile care intră în total.',
      'Disbursements are entered by hand (the "Disbursements" sheet); they do not come from an official source. "% disbursed" and "Left to disburse" are computed only for the rows that count in the total.'),
    t('Totalul de jos adună rândurile vizibile și se recalculează când filtrezi în Excel. În total, debursările la proiectele cu sumă reprezintă ',
      'The total at the bottom adds up the visible rows and recalculates when you filter in Excel. Overall, disbursements on projects with an amount are ') +
      (re.pct != null ? fmtSuma(re.pct * 100, en, 1) + '%' : '—') + t(' din suma lor.', ' of their amount.')
  ];
  if (o.cuDonatori) note.push(t('Un acord cu mai mulți donatori apare o singură dată, cu toți donatorii în coloana „Donatori”.', 'An agreement with several donors appears once, with all its donors in the "Donors" column.'));
  else note.push(t('Un acord finanțat de mai mulți parteneri apare la fiecare dintre ei, cu suma întreagă a acordului.', 'An agreement financed by several partners appears under each of them, with the whole amount of the agreement.'));
  note.push({ t: t('Pagina, online: ', 'The page, online: ') + c.baza, u: c.baza });
  return {
    foaie: o.foaie, titlu: o.titlu, subtitlu: o.subtitlu,
    antete: cols.map(function (x) { return x[0]; }), tipuri: cols.map(function (x) { return x[1]; }).join(''), randuri: randuri, latimi: latimi,
    total: { eticheta: t('Total (rândurile vizibile)', 'Total (visible rows)'), suma: [cEur, cDebEur, cRest, cNr] },
    inghetaColoane: 1, maxLinii: 3, paginiLatime: 'auto', bare: [cPct],
    grupe: [{ de: cProiect, pana: cSemnat, text: t('PROIECTUL', 'THE PROJECT') }, { de: cSuma, pana: cEur, text: t('SUMA PROIECTULUI', 'PROJECT AMOUNT') },
            { de: cDebVal, pana: cUltima, text: t('DEBURSĂRI', 'DISBURSEMENTS') }, { de: cInTotal, pana: cLink, text: t('DETALII', 'DETAILS') }],
    etichete: etichete, linkuri: linkuri, note: note, culoareFila: o.culoare || 'FF1E4B8C', subsol: c.subsol
  };
}
function foaieDebursari(c, o) {
  const t = c.t, en = c.en;
  const idx = new Map(); o.acorduri.forEach(function (a) { idx.set(a.id, a); });
  const randuri = [];
  const intrari = [];
  o.acorduri.forEach(function (a) { (c.peAcord.get(a.id) || []).forEach(function (e) { intrari.push([a, e]); }); });
  (o.orfane || []).forEach(function (e) { intrari.push([null, e]); });
  intrari.sort(function (x, y) { return (y[1].data || '').localeCompare(x[1].data || '') || (x[0] ? x[0].nume : '~').localeCompare(y[0] ? y[0].nume : '~', 'ro'); });
  intrari.forEach(function (p) {
    const a = p[0], e = p[1], x = eurIntrare(e, c.cursuri);
    randuri.push([a ? a.donatori.join(' / ') : t('(acord negăsit în registru)', '(agreement not found in the register)'), a ? a.nume : (e.nume || ''),
                  e.data || '', e.suma, e.val, x != null ? Math.round(x) : '', e.nota || '', e.la ? dataOraRo(new Date(e.la)) : '']);
  });
  return {
    foaie: o.foaie || t('Debursări', 'Disbursements'), titlu: o.titlu || t('Debursările introduse', 'Disbursements entered'),
    subtitlu: o.subtitlu,
    antete: [t('Donatori', 'Donors'), t('Proiectul', 'Project'), t('Data', 'Date'), t('Suma', 'Amount'), t('Valuta', 'Currency'),
             t('Echivalent EUR', 'EUR equivalent'), t('Notă', 'Note'), t('Introdus la', 'Entered on')],
    tipuri: 'ttzdcetl', randuri: randuri,
    latimi: { 0: 18, 1: 44, 2: 12, 3: 16, 4: 8, 5: 16, 6: 44, 7: 17 },
    total: randuri.length ? { eticheta: t('Total (rândurile vizibile)', 'Total (visible rows)'), suma: [5] } : undefined,
    inghetaColoane: 0, maxLinii: 2, paginiLatime: 'auto', culoareFila: 'FFC8871A', subsol: c.subsol,
    note: [
      randuri.length ? t('Fiecare rând e o debursare introdusă manual. „Echivalent EUR” folosește cursurile BCE din ' + (c.cursData || '—') + '.',
                         'Each row is a disbursement entered manually. "EUR equivalent" uses the ECB rates of ' + (c.cursData || '—') + '.')
                     : t('Nicio debursare introdusă încă pentru această selecție.', 'No disbursement entered yet for this selection.'),
      { t: t('Pagina, online: ', 'The page, online: ') + c.baza, u: c.baza }
    ]
  };
}
function foaieRezumat(c, o) {
  const t = c.t, en = c.en;
  const randuri = o.donatori.map(function (d) {
    const r = rezumat(d.acorduri, c.peAcord, c.cursuri);
    return [d.cheie, numeDonator(d.cheie, en) === d.cheie ? '' : numeDonator(d.cheie, en), r.n, r.cuSuma, Math.round(r.sumaEur), Math.round(r.debEur),
            r.pct != null ? Math.round(r.pct * 1000) / 10 : '', r.rest != null ? Math.round(r.rest) : '', r.nIntrari, r.ultima || ''];
  });
  const tot = rezumat(o.toate, c.peAcord, c.cursuri);
  randuri.push([t('Total general (fiecare proiect o singură dată)', 'Grand total (each project once)'), '', tot.n, tot.cuSuma, Math.round(tot.sumaEur), Math.round(tot.debEur),
                tot.pct != null ? Math.round(tot.pct * 1000) / 10 : '', tot.rest != null ? Math.round(tot.rest) : '', tot.nIntrari, tot.ultima || '']);
  return {
    foaie: o.foaie || t('Pe donatori', 'By donor'), titlu: o.titlu, subtitlu: o.subtitlu,
    antete: [t('Donator', 'Donor'), t('Denumire completă', 'Full name'), t('Proiecte', 'Projects'), t('Din care cu sumă (în total)', 'Of which with an amount (in the total)'),
             t('Suma proiectelor (EUR)', 'Project amounts (EUR)'), t('Debursat total (EUR)', 'Total disbursed (EUR)'),
             t('% debursat (proiecte cu sumă)', '% disbursed (projects with an amount)'), t('Rest de debursat (EUR)', 'Left to disburse (EUR)'),
             t('Nr. debursări', 'No. of disbursements'), t('Ultima debursare', 'Last disbursement')],
    tipuri: 'ttnneepenz', randuri: randuri, randTotal: true,
    latimi: { 0: 22, 1: 46, 2: 10, 3: 14, 4: 18, 5: 18, 6: 15, 7: 17, 8: 11, 9: 13 },
    inghetaColoane: 1, maxLinii: 2, paginiLatime: 'auto', bare: [6], culoareFila: 'FF1E4B8C', subsol: c.subsol,
    note: [
      t('Un acord finanțat de mai mulți parteneri e numărat la fiecare dintre ei; rândul „Total general” îl numără o singură dată, deci nu coincide cu suma coloanelor.',
        'An agreement financed by several partners is counted under each of them; the "Grand total" row counts it once, so it differs from the sum of the columns.'),
      t('„Suma proiectelor” adună doar acordurile cu sumă care intră în total (aceleași reguli ca în panoul „Sumele acordurilor” din registru). „% debursat” compară debursările la acele proiecte cu suma lor.',
        '"Project amounts" adds up only the agreements with an amount that count in the total (the same rules as in the register\'s "Agreement amounts" panel). "% disbursed" compares the disbursements on those projects with their amount.'),
      { t: t('Pagina, online: ', 'The page, online: ') + c.baza, u: c.baza }
    ]
  };
}
function contextExcel(c) {
  return Object.assign({ subsol: (c.baza || '').replace(/^https?:\/\//, '') }, c);
}
/* Un donator: foaia „Proiecte” + foaia „Debursări”. */
function excelDonator(c0, donator) {
  const c = contextExcel(c0), t = c.t;
  const ac = donator.acorduri;
  const sub = subtitluComun(c, t('Donator: ', 'Donor: ') + donator.cheie + (numeDonator(donator.cheie, c.en) !== donator.cheie ? ' (' + numeDonator(donator.cheie, c.en) + ')' : ''));
  const foi = [
    foaieProiecte(c, { foaie: taie(donator.cheie, 31), titlu: t('Debursări pe acorduri — ', 'Disbursements by agreement — ') + donator.cheie, subtitlu: sub, acorduri: ac, cuDonatori: false }),
    foaieDebursari(c, { acorduri: ac, subtitlu: sub, titlu: t('Debursările introduse — ', 'Disbursements entered — ') + donator.cheie })
  ];
  return { limba: c.en ? 'en' : 'ro', autor: 'nistor.vivi.md', subsol: c.subsol, titlu: foi[0].titlu, foi: foi };
}
function unice(donatori) {
  const v = new Set(), r = [];
  donatori.forEach(function (d) { d.acorduri.forEach(function (a) { if (!v.has(a.id)) { v.add(a.id); r.push(a); } }); });
  return r;
}
/* Total: toate proiectele donatorilor aleși (fiecare o dată), rezumatul pe donatori și debursările. */
function excelTotal(c0, donatori, orfane) {
  const c = contextExcel(c0), t = c.t;
  const toate = unice(donatori);
  const ce = donatori.length === 1 ? t('Donator: ', 'Donor: ') + donatori[0].cheie : t('Donatori: ', 'Donors: ') + donatori.length;
  const sub = subtitluComun(c, ce);
  const foi = [
    foaieProiecte(c, { foaie: t('Total', 'Total'), titlu: t('Debursări pe acorduri — total', 'Disbursements by agreement — total'), subtitlu: sub, acorduri: ordoneaza(toate, 'suma', c.peAcord, c.cursuri), cuDonatori: true }),
    foaieRezumat(c, { foaie: t('Pe donatori', 'By donor'), titlu: t('Rezumat pe donatori', 'Summary by donor'), subtitlu: sub, donatori: donatori, toate: toate }),
    foaieDebursari(c, { acorduri: toate, orfane: orfane || [], subtitlu: sub, titlu: t('Debursările introduse', 'Disbursements entered') })
  ];
  return { limba: c.en ? 'en' : 'ro', autor: 'nistor.vivi.md', subsol: c.subsol, titlu: foi[0].titlu, foi: foi };
}
/* Pe donatori: rezumatul, apoi câte o foaie pentru fiecare donator, apoi debursările. */
function excelPeDonatori(c0, donatori, orfane) {
  const c = contextExcel(c0), t = c.t;
  const toate = unice(donatori);
  const sub = subtitluComun(c, t('Donatori: ', 'Donors: ') + donatori.length);
  const foi = [foaieRezumat(c, { foaie: t('Rezumat', 'Summary'), titlu: t('Rezumat pe donatori', 'Summary by donor'), subtitlu: sub, donatori: donatori, toate: toate })];
  donatori.forEach(function (d) {
    foi.push(foaieProiecte(c, { foaie: taie(d.cheie, 31), titlu: t('Debursări pe acorduri — ', 'Disbursements by agreement — ') + d.cheie,
      subtitlu: subtitluComun(c, t('Donator: ', 'Donor: ') + d.cheie + (numeDonator(d.cheie, c.en) !== d.cheie ? ' (' + numeDonator(d.cheie, c.en) + ')' : '')),
      acorduri: ordoneaza(d.acorduri, 'suma', c.peAcord, c.cursuri), cuDonatori: false, culoare: 'FF2DD4BF' }));
  });
  foi.push(foaieDebursari(c, { acorduri: toate, orfane: orfane || [], subtitlu: sub, titlu: t('Debursările introduse', 'Disbursements entered') }));
  return { limba: c.en ? 'en' : 'ro', autor: 'nistor.vivi.md', subsol: c.subsol, titlu: foi[0].titlu, foi: foi };
}

return {
  CONFIG: CONFIG, NEIDENTIFICAT: NEIDENTIFICAT, STADII: STADII, ORDINE_TIP: ORDINE_TIP, SURSE_SUMA: SURSE_SUMA, NUME_DONATOR: NUME_DONATOR,
  MAX_NOTA: MAX_NOTA, LUNGIME_MIN_PIN: LUNGIME_MIN_PIN,
  fold: fold, taie: taie, slug: slug, fmtSuma: fmtSuma, fmtBani: fmtBani, dataTextEn: dataTextEn, fmtCompact: fmtCompact, parseSuma: parseSuma,
  dataRo: dataRo, esteDataIso: esteDataIso, aziIso: aziIso, dataOraRo: dataOraRo, ordRo: ordRo,
  donatoriiAcordului: donatoriiAcordului, curataNume: curataNume, stadiu: stadiu, etichetaStadiu: etichetaStadiu, etichetaTip: etichetaTip, numeDonator: numeDonator,
  deduCursuri: deduCursuri, pregateste: pregateste, descriere: descriere,
  idNou: idNou, eurIntrare: eurIntrare, intrareValida: intrareValida, valideazaFormular: valideazaFormular, intrareDin: intrareDin, lega: lega,
  agregaAcord: agregaAcord, rezumat: rezumat, potriveste: potriveste, ordoneaza: ordoneaza, ordoneazaDonatori: ordoneazaDonatori,
  citesteHash: citesteHash, scrieHash: scrieHash,
  EroareDepozit: EroareDepozit, dateGoale: dateGoale, citesteText: citesteText, aplicaOps: aplicaOps, text: text, b64DinText: b64DinText, textDinB64: textDinB64,
  Depozit: Depozit, Seif: Seif,
  excelDonator: excelDonator, excelTotal: excelTotal, excelPeDonatori: excelPeDonatori, unice: unice
};
});
