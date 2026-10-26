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
  sursaManual: 'date/proiecte_manual.json',      // obiective, date, rânduri omise (scrise de mână, cu sursă și citat)
  sursaDate: 'date/debursari.json'              // aceeași bază, citită ca fișier public (fără cod)
};
const NEIDENTIFICAT = '(neidentificat)';
const MAX_NOTA = 200;
const MAX_OBIECTIVE = 600;
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
/* De unde vine o informație despre proiect (obiective, început, finalizare): [română, engleză]. */
const SURSE_PROIECT = {
  manual: ['introdus de utilizator', 'entered by a user'],
  oficial: ['sursă oficială', 'official source'],
  amp: ['AMP', 'AMP']
};
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

/* Datele de început și de finalizare ale proiectelor pot fi întregi („2026-03-15”) sau parțiale („2026-03”, „2026”), după cât spune sursa:
   o dată parțială nu se completează cu o zi inventată. */
function dataPartiala(s) {
  const m = /^(\d{4})(?:-(\d{2})(?:-(\d{2}))?)?$/.exec(String(s == null ? '' : s).trim());
  if (!m) return null;
  const a = +m[1], l = m[2] ? +m[2] : 0, z = m[3] ? +m[3] : 0;
  if (a < 1950 || a > 2100) return null;
  if (m[2] && (l < 1 || l > 12)) return null;
  if (m[3] && !esteDataIso(m[0])) return null;
  return { a: a, l: l, z: z, p: z ? 'z' : (l ? 'l' : 'a') };
}
function esteDataPartiala(s) { return !!dataPartiala(s); }
/* „2026-03-15” → „15.03.2026”; „2026-03” → „03.2026”; „2026” → „2026”. Datele întregi se scriu cum le citește Excel. */
function fmtDataPartiala(s) {
  const d = dataPartiala(s);
  if (!d) return '';
  return d.p === 'z' ? pad(d.z) + '.' + pad(d.l) + '.' + d.a : d.p === 'l' ? pad(d.l) + '.' + d.a : String(d.a);
}
/* Începutul e după sfârșit? Se compară doar cât spun ambele date („2026-03” față de „2026-03-20” nu se contrazic). */
function inceputDupaSfarsit(i, s) {
  const x = dataPartiala(i), y = dataPartiala(s);
  if (!x || !y) return false;
  if (x.a !== y.a) return x.a > y.a;
  if (!x.l || !y.l) return false;
  if (x.l !== y.l) return x.l > y.l;
  if (!x.z || !y.z) return false;
  return x.z > y.z;
}

/* Ce scrie omul într-un câmp de dată: „15.03.2026”, „03.2026”, „2026”, „2026-03-15” (cu „.”, „/” sau „-” între părți). Întoarce data în forma
   păstrată în fișiere (AAAA-LL-ZZ, AAAA-LL sau AAAA), '' când câmpul e gol și null când nu se înțelege. */
function parseDataPartiala(txt) {
  const s = String(txt == null ? '' : txt).trim();
  if (!s) return '';
  let m, iso = null;
  if ((m = /^(\d{4})[-./](\d{1,2})[-./](\d{1,2})$/.exec(s))) iso = m[1] + '-' + pad(+m[2]) + '-' + pad(+m[3]);
  else if ((m = /^(\d{1,2})[-./](\d{1,2})[-./](\d{4})$/.exec(s))) iso = m[3] + '-' + pad(+m[2]) + '-' + pad(+m[1]);
  else if ((m = /^(\d{4})[-./](\d{1,2})$/.exec(s))) iso = m[1] + '-' + pad(+m[2]);
  else if ((m = /^(\d{1,2})[-./](\d{4})$/.exec(s))) iso = m[2] + '-' + pad(+m[1]);
  else if (/^\d{4}$/.test(s)) iso = s;
  return iso && dataPartiala(iso) ? iso : null;
}

/* ------------------------------------------------------------------ datele despre proiecte, scrise de mână (date/proiecte_manual.json) */
/* Fișierul are două liste: „omise” (rânduri-umbrelă din registru, care nu apar în lista de proiecte) și „proiecte” (obiective, început,
   finalizare, fiecare cu sursa și citatul exact). Aici se verifică ce s-a scris: o intrare fără sursă și citat nu se citește, ca să nu apară
   în pagină nimic ce nu se poate verifica. Întoarce { omise, proiecte, erori } — erorile spun ce intrare s-a respins și de ce. */
function normalizeazaManual(j) {
  const r = { omise: [], proiecte: [], erori: [] };
  const lista = function (x) { return Array.isArray(x) ? x : []; };
  const coduri = function (x) { return lista(x).filter(function (c) { return typeof c === 'string' && c.trim(); }).map(function (c) { return c.trim(); }); };
  const sir = function (x) { return String(x == null ? '' : x).replace(/\s+/g, ' ').trim(); };
  lista(j && j.omise).forEach(function (o, i) {
    const acte = coduri(o && o.acte), motiv = sir(o && o.motiv);
    if (!acte.length || !motiv) { r.erori.push('omise[' + i + ']: lipsesc actele sau motivul'); return; }
    r.omise.push({ acte: acte, motiv: motiv, motivEn: sir(o.motiv_en), numaratLa: coduri(o.numarat_la) });
  });
  lista(j && j.proiecte).forEach(function (p, i) {
    const e = 'proiecte[' + i + ']';
    const acte = coduri(p && p.acte);
    if (!acte.length) { r.erori.push(e + ': lipsesc actele'); return; }
    const ro = sir(p.obiective && p.obiective.ro), en = sir(p.obiective && p.obiective.en);
    const inceput = sir(p.inceput), sfarsit = sir(p.sfarsit);
    if (!ro && !inceput && !sfarsit) { r.erori.push(e + ' (' + acte[0] + '): nu conține obiective și nici date'); return; }
    if (en && !ro) { r.erori.push(e + ' (' + acte[0] + '): obiectivele în engleză fără cele în română'); return; }
    if (ro.length > MAX_OBIECTIVE || en.length > MAX_OBIECTIVE) { r.erori.push(e + ' (' + acte[0] + '): obiectivele depășesc ' + MAX_OBIECTIVE + ' de caractere'); return; }
    if ((inceput && !esteDataPartiala(inceput)) || (sfarsit && !esteDataPartiala(sfarsit))) { r.erori.push(e + ' (' + acte[0] + '): dată în alt format decât AAAA-LL-ZZ, AAAA-LL sau AAAA'); return; }
    if (inceput && sfarsit && inceputDupaSfarsit(inceput, sfarsit)) { r.erori.push(e + ' (' + acte[0] + '): începutul e după sfârșit'); return; }
    const sursa = sir(p.sursa), citat = sir(p.citat);
    if (!/^https?:\/\/\S+$/.test(sursa) || citat.length < 12) { r.erori.push(e + ' (' + acte[0] + '): lipsește sursa (adresa documentului) sau citatul exact'); return; }
    r.proiecte.push({ acte: acte, ro: ro, en: en, inceput: inceput, sfarsit: sfarsit, sursa: sursa, citat: citat, nota: sir(p.nota) });
  });
  return r;
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

/* Rândurile fișierului date/acorduri_legare.json, pregătite pentru pagină. `manualBrut` e fișierul date/proiecte_manual.json (opțional).
   Donatorii unui rând sunt finanțatorii acordului însuși (parteneriAcord), nu toți partenerii adunați din actele grupate: un împrumut al BERD
   nu apare și la BEI doar fiindcă un act al grupului vorbește de ambele bănci. Rândurile-umbrelă („omise”) nu intră în listă. */
function pregateste(json, manualBrut) {
  json = json || {};
  const manual = normalizeazaManual(manualBrut);
  const brut = Array.isArray(json.acorduri) ? json.acorduri : [];
  const cursuri = json.cursuri && Object.keys(json.cursuri).length ? Object.assign({}, json.cursuri) : deduCursuri(brut);
  cursuri.EUR = 1;
  const acorduri = [], peId = new Map(), peDonator = new Map(), peAct = new Map();
  const toate = [], peActToate = new Map(), vazute = new Set();
  brut.forEach(function (a) {
    if (!a || !a.id || vazute.has(a.id)) return;
    vazute.add(a.id);
    const s = a.suma && numar(a.suma.v) && a.suma.v > 0 ? a.suma : null;
    const eur = s ? (cursuri[s.val] ? s.v / cursuri[s.val] : (numar(s.eur) ? s.eur : null)) : null;
    const inTotal = a.inTotal || (s ? (a.faraTotal ? 'fara_total' : (eur == null ? 'fara_curs' : 'numarat')) : 'fara_suma');
    const acte = (a.acte || []).map(function (x) { return { act: x.act || '', tip: x.tip || '', data: x.data || '', url: x.url || '', etape: x.etape || [] }; });
    const parteneri = a.parteneriAcord || a.parteneri || '';
    const x = {
      id: a.id,
      nume: curataNume(a.scurt || a.nume) || a.nume || a.id,
      numeComplet: String(a.nume || '').replace(/\s+/g, ' ').trim(),
      categorie: a.categorie || '',
      parteneriText: parteneri,
      parteneriRegistru: a.parteneri || '',
      donatori: donatoriiAcordului(parteneri),
      stadiu: stadiu(a.et), etape: a.et || [],
      semnat: a.semnat || '', primul: a.primul || '', ultimul: a.ultimul || '',
      suma: s, sursaSuma: s ? (s.sursa || '') : '', actSuma: s ? (s.act || '') : '',
      eur: eur, inTotal: inTotal, eurTotal: inTotal === 'numarat' ? eur : null,
      alte: a.alte || [], cost: a.cost || null,
      acte: acte, coduri: acte.map(function (y) { return y.act; }).filter(Boolean),
      url: (acte.filter(function (y) { return y.url; })[0] || {}).url || '',
      deosebire: null
    };
    toate.push(x);
    x.coduri.forEach(function (c) { (peActToate.get(c) || peActToate.set(c, []).get(c)).push(x); });
  });
  const omiseIds = new Map();
  manual.omise.forEach(function (o) {
    o.acte.forEach(function (c) { (peActToate.get(c) || []).forEach(function (x) { if (!omiseIds.has(x.id)) omiseIds.set(x.id, o); }); });
  });
  const omise = [];
  toate.forEach(function (x) {
    const o = omiseIds.get(x.id);
    if (o) { omise.push({ a: x, motiv: o.motiv, motivEn: o.motivEn || '', numaratLa: o.numaratLa }); return; }
    acorduri.push(x); peId.set(x.id, x);
    x.coduri.forEach(function (c) { (peAct.get(c) || peAct.set(c, []).get(c)).push(x); });
    x.donatori.forEach(function (d) { (peDonator.get(d) || peDonator.set(d, []).get(d)).push(x); });
  });
  adaugaDeosebiri(acorduri);
  const proiecteManual = new Map(), proiecteNegasite = [];
  manual.proiecte.forEach(function (p) {
    const a = gasesteAcord({ acte: p.acte }, { peId: peId, peAct: peAct });
    if (!a) { proiecteNegasite.push(p); return; }
    (proiecteManual.get(a.id) || proiecteManual.set(a.id, []).get(a.id)).push(p);
  });
  const donatori = Array.from(peDonator.keys()).map(function (k) { return { cheie: k, acorduri: peDonator.get(k) }; });
  return { acorduri: acorduri, peId: peId, peAct: peAct, donatori: donatori, peDonator: peDonator, cursuri: cursuri,
           omise: omise, proiecteManual: proiecteManual, proiecteNegasite: proiecteNegasite, eroriManual: manual.erori,
           cursData: json.curs_data || '', actualizat: json.actualizat || '' };
}

/* Rândul căruia îi aparține o înregistrare salvată (debursare sau date despre proiect). Id-ul unui acord e cel al actului lui cel mai vechi
   și se poate schimba (se unesc două rânduri, apare un act mai vechi): atunci îl regăsim după oricare dintre actele păstrate în înregistrare. */
function gasesteAcord(e, baza) {
  let a = e.acord ? baza.peId.get(e.acord) : null;
  if (!a && Array.isArray(e.acte)) {
    const voturi = new Map();
    e.acte.forEach(function (c) { (baza.peAct.get(c) || []).forEach(function (x) { voturi.set(x, (voturi.get(x) || 0) + 1); }); });
    let max = 0;
    voturi.forEach(function (n, x) { if (n > max) { max = n; a = x; } });
  }
  return a || null;
}

/* Rândurile cu aceeași denumire la același donator (de pildă un împrumut și un grant pentru același program, sau tranșe din ani diferiți)
   par dublate într-o listă. Sunt acorduri deosebite, dar numele nu le deosebește: le adăugăm o mențiune scurtă — tipul și anul semnării,
   iar dacă nici ele nu ajung, suma și codul celui mai vechi act. Nu se atinge denumirea din registru. */
function cheieNume(s) { return fold(s).replace(/[^a-z0-9]+/g, ' ').trim(); }
function anul(a) {
  const m = /(\d{4})$/.exec(a.semnat || '') || /(\d{4})$/.exec(a.primul || '');
  return m ? m[1] : '';
}
function partiDeosebire(a, nivel, en) {
  const p = [];
  const t = etichetaTip(a.categorie, en);
  if (t) p.push(t.toLowerCase());
  const an = anul(a);
  if (an) p.push(an);
  if (nivel >= 2 && a.suma) p.push(fmtCompact(a.suma.v, en) + ' ' + a.suma.val);
  if (nivel >= 3 && a.coduri.length) p.push(a.coduri[a.coduri.length - 1]);
  return p.join(', ');
}
function adaugaDeosebiri(acorduri) {
  const pe = new Map(), grupe = new Map();
  acorduri.forEach(function (a) {
    const n = cheieNume(a.nume);
    (pe.get(n) || pe.set(n, []).get(n)).push(a);
    a.donatori.forEach(function (d) { const k = d + '\u0001' + n; (grupe.get(k) || grupe.set(k, []).get(k)).push(a); });
  });
  const repetate = new Set();
  grupe.forEach(function (l, k) { if (l.length > 1) repetate.add(k.slice(k.indexOf('\u0001') + 1)); });
  repetate.forEach(function (n) {
    const fam = pe.get(n);
    fam.forEach(function (a) {
      // doar rândurile cu același nume care apar în aceeași listă de donator se încurcă între ele
      const vecini = fam.filter(function (b) { return b !== a && b.donatori.some(function (d) { return a.donatori.indexOf(d) >= 0; }); });
      if (!vecini.length) return;
      let nivel = 1;
      while (nivel < 3 && vecini.some(function (b) { return partiDeosebire(b, nivel, false) === partiDeosebire(a, nivel, false); })) nivel++;
      a.deosebire = { ro: partiDeosebire(a, nivel, false), en: partiDeosebire(a, nivel, true) };
    });
  });
}
/* Denumirea cu mențiunea de deosebire, cum se scrie în Excel. */
function numeAfisat(a, en) {
  const d = a.deosebire && a.deosebire[en ? 'en' : 'ro'];
  return d ? a.nume + ' (' + d + ')' : a.nume;
}

/* Ce se știe despre un rând: obiectivele proiectului și datele de început și de finalizare. Fiecare câmp se ia din prima sursă care îl are:
     1. ce a introdus un utilizator în pagină (date/debursari.json, `ctx.db`: Map id rând → înregistrare),
     2. surse oficiale, scrise de mână, cu adresa documentului și citatul exact (date/proiecte_manual.json, `ctx.manual`: Map id rând → intrări),
     3. AMP, doar când legătura cu proiectul e sigură (`ctx.amp`: Map id rând → { id, titlu, inceput, sfarsit, nivel: 'sigur' | 'probabil' });
        o legătură doar probabilă nu dă nicio dată în tabel: se păstrează ca indiciu (`ampProbabil`), fiindcă prea des nimerește altă fază sau alt an.
   Obiectivele nu vin din AMP: raportul pe care îl citim nu le cuprinde. Fiecare câmp își păstrează sursa (`tip`), ca pagina și Excel-ul să o spună. */
function infoProiect(a, ctx) {
  ctx = ctx || {};
  const db = (ctx.db && ctx.db.get(a.id)) || null;
  const oficiale = (ctx.manual && ctx.manual.get(a.id)) || [];
  const amp = (ctx.amp && ctx.amp.get(a.id)) || null;
  const r = { obiective: null, inceput: null, sfarsit: null, db: db, oficiale: oficiale, amp: amp, ampProbabil: null, contradictie: false };
  if (db && db.obiective) r.obiective = { ro: db.obiective, en: db.obiective, tip: 'manual', nota: db.nota || '', la: db.la || '' };
  else {
    const e = oficiale.filter(function (x) { return x.ro; })[0];
    if (e) r.obiective = { ro: e.ro, en: e.en || e.ro, tip: 'oficial', sursa: e.sursa, citat: e.citat, nota: e.nota || '' };
  }
  ['inceput', 'sfarsit'].forEach(function (k) {
    if (db && esteDataPartiala(db[k])) { r[k] = { v: db[k], tip: 'manual', nota: db.nota || '', la: db.la || '' }; return; }
    const e = oficiale.filter(function (x) { return esteDataPartiala(x[k]); })[0];
    if (e) { r[k] = { v: e[k], tip: 'oficial', sursa: e.sursa, citat: e.citat, nota: e.nota || '' }; return; }
    if (amp && amp.nivel === 'sigur' && esteDataPartiala(amp[k])) r[k] = { v: amp[k], tip: 'amp', idAmp: amp.id, titluAmp: amp.titlu || '' };
  });
  if (amp && amp.nivel === 'probabil' && (esteDataPartiala(amp.inceput) || esteDataPartiala(amp.sfarsit))) r.ampProbabil = amp;
  r.contradictie = !!(r.inceput && r.sfarsit && inceputDupaSfarsit(r.inceput.v, r.sfarsit.v));
  return r;
}
function etichetaSursaProiect(tip, en) { const x = SURSE_PROIECT[tip]; return x ? x[en ? 1 : 0] : ''; }
/* „sursă oficială” sau, când câmpurile vin din surse diferite, „obiective: sursă oficială; început: AMP; finalizare: AMP”. */
function textSursaProiect(info, en) {
  const camp = [[info.obiective, en ? 'objectives' : 'obiective'], [info.inceput, en ? 'start' : 'început'], [info.sfarsit, en ? 'completion' : 'finalizare']]
    .filter(function (x) { return x[0]; });
  if (!camp.length) return '';
  const tipuri = [];
  camp.forEach(function (x) { if (tipuri.indexOf(x[0].tip) < 0) tipuri.push(x[0].tip); });
  if (tipuri.length === 1) return etichetaSursaProiect(tipuri[0], en);
  return camp.map(function (x) { return x[1] + ': ' + etichetaSursaProiect(x[0].tip, en); }).join('; ');
}
/* Adresa documentului care susține un câmp: a sursei oficiale; pentru ce vine din AMP, nu există una (proiectul AMP se leagă separat). */
function legaturaSursaProiect(info) {
  const c = [info.obiective, info.inceput, info.sfarsit].filter(function (x) { return x && x.tip === 'oficial' && x.sursa; })[0];
  return c ? c.sursa : '';
}

/* Descrierea succintă din tabel = obiectivele proiectului. Când nu se știu, întoarce un șir gol: pagina scrie atunci „neintroduse”
   (nu o frază alcătuită din titlu și date, care ar părea obiective fără să fie). */
function descriere(a, en, info) {
  const o = info && info.obiective;
  return o ? (en ? (o.en || o.ro) : o.ro) : '';
}

/* ------------------------------------------------------------------ debursările */
function idNou(pref) {
  return (pref || 'd') + Date.now().toString(36) + Math.random().toString(36).slice(2, 7);
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
/* Ce scrie omul în formularul „Date despre proiect”: obiective, început, finalizare, notă. Toate sunt opționale, dar măcar unul trebuie completat
   (altfel înregistrarea se șterge). Datele pot fi întregi sau parțiale (vezi parseDataPartiala). */
function valideazaProiect(c) {
  const erori = {}, v = {};
  v.obiective = String(c.obiective || '').replace(/\s+/g, ' ').trim();
  if (v.obiective.length > MAX_OBIECTIVE) erori.obiective = 'lunga';
  v.inceput = parseDataPartiala(c.inceput);
  if (v.inceput === null) { erori.inceput = 'format'; v.inceput = ''; }
  v.sfarsit = parseDataPartiala(c.sfarsit);
  if (v.sfarsit === null) { erori.sfarsit = 'format'; v.sfarsit = ''; }
  if (!erori.inceput && !erori.sfarsit && v.inceput && v.sfarsit && inceputDupaSfarsit(v.inceput, v.sfarsit)) erori.sfarsit = 'ordine';
  v.nota = String(c.nota || '').replace(/\s+/g, ' ').trim();
  if (v.nota.length > MAX_NOTA) erori.nota = 'lunga';
  v.gol = !v.obiective && !v.inceput && !v.sfarsit;
  return { ok: !Object.keys(erori).length, erori: erori, valoare: v };
}
function proiectDin(acord, valoare, acum, id) {
  const e = { id: id || idNou('p'), acord: acord.id, acte: acord.coduri.slice(0, 12), nume: taie(acord.nume, 160) };
  if (valoare.obiective) e.obiective = valoare.obiective;
  if (valoare.inceput) e.inceput = valoare.inceput;
  if (valoare.sfarsit) e.sfarsit = valoare.sfarsit;
  if (valoare.nota) e.nota = valoare.nota;
  e.la = (acum || new Date()).toISOString();
  return e;
}
function proiectDbValid(e) {
  return !!(e && typeof e.id === 'string' && e.id && typeof e.acord === 'string' &&
            ((typeof e.obiective === 'string' && e.obiective.trim()) || esteDataPartiala(e.inceput) || esteDataPartiala(e.sfarsit)));
}
/* Leagă înregistrările „Date despre proiect” de rânduri: una pe rând (cea mai nouă); celelalte, mai vechi, rămân în fișier dar nu se arată.
   Fără rând (acordul nu mai e în registru sau s-a schimbat atât de mult încât nu se mai recunoaște) → orfane. */
function legaProiecte(proiecte, baza) {
  const peAcord = new Map(), orfane = [], vechi = [];
  (proiecte || []).filter(proiectDbValid).sort(function (x, y) { return (y.la || '').localeCompare(x.la || ''); }).forEach(function (e) {
    const a = gasesteAcord(e, baza);
    if (!a) { orfane.push(e); return; }
    if (peAcord.has(a.id)) { vechi.push(e); return; }
    peAcord.set(a.id, e);
  });
  return { peAcord: peAcord, orfane: orfane, vechi: vechi };
}

/* Leagă debursările de acorduri. Id-ul unui acord e cel al actului lui cel mai vechi și se poate schimba (se unesc două rânduri,
   apare un act mai vechi): atunci îl regăsim după oricare dintre actele păstrate în debursare. Ce nu se leagă nicicum e „orfan”. */
function lega(intrari, baza) {
  const peAcord = new Map(), orfane = [];
  (intrari || []).forEach(function (e) {
    if (!intrareValida(e)) return;
    const a = gasesteAcord(e, baza);
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
    const hay = fold([a.nume, a.numeComplet, a.parteneriText, a.coduri.join(' '), a.categorie, a.semnat, (f.extra && f.extra.get(a.id)) || ''].join(' '));
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
function dateGoale() { return { versiune: 1, actualizat: '', intrari: [], proiecte: [] }; }
function citesteText(text) {
  let o;
  try { o = JSON.parse(String(text).replace(/^﻿/, '')); } catch (e) { throw new EroareDepozit('format', 'Fișierul cu debursări nu e un JSON valid.'); }
  if (!o || typeof o !== 'object' || Array.isArray(o)) throw new EroareDepozit('format', 'Fișierul cu debursări are alt format decât cel așteptat.');
  if (o.intrari == null) o.intrari = [];
  if (!Array.isArray(o.intrari)) throw new EroareDepozit('format', 'Fișierul cu debursări are alt format decât cel așteptat.');
  if (o.proiecte == null) o.proiecte = [];
  if (!Array.isArray(o.proiecte)) throw new EroareDepozit('format', 'Fișierul cu debursări are alt format decât cel așteptat.');
  return o;
}
/* Operații: {t:'add', e}, {t:'upd', e}, {t:'del', id} pentru debursări; {t:'pset', p}, {t:'pdel', id} pentru datele despre proiecte
   (obiective, început, finalizare). Se aplică pe orice stare a fișierului, deci se pot reaplica peste varianta mai nouă a cuiva altcuiva. */
function aplicaOps(date, ops, acum) {
  const nou = Object.assign({}, date, { intrari: (date.intrari || []).slice(), proiecte: (date.proiecte || []).slice() });
  (ops || []).forEach(function (op) {
    if (op.t === 'pdel') nou.proiecte = nou.proiecte.filter(function (x) { return x.id !== op.id; });
    else if (op.t === 'pset') {
      if (!op.p || !op.p.id) return;
      const i = nou.proiecte.findIndex(function (x) { return x.id === op.p.id; });
      if (i >= 0) nou.proiecte[i] = Object.assign({}, op.p); else nou.proiecte.push(Object.assign({}, op.p));
    } else if (op.t === 'del') nou.intrari = nou.intrari.filter(function (x) { return x.id !== op.id; });
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
  const lista = function (v) { return '[' + (v.length ? '\n' + v.map(function (e) { return JSON.stringify(e); }).join(',\n') + '\n' : '') + ']'; };
  const pr = date.proiecte || [];
  return cap.slice(0, -1) + ',"intrari":' + lista(date.intrari || []) + (pr.length ? ',"proiecte":' + lista(pr) : '') + '}\n';
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
  const cDesc = col(t('Descriere succintă (obiectivele proiectului)', 'Short description (project objectives)'), 't', 56);
  const cInc = col(t('Data efectivă de începere', 'Actual start date'), 'z', 14);
  const cSfa = col(t('Data finalizării', 'Completion date'), 'z', 14);
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
  const cSursa = col(t('Sursa obiectivelor și a datelor', 'Source of objectives and dates'), 't', 30);
  const cLink = col(t('Link legis.md', 'legis.md link'), 't', 13);
  const randuri = [], urluri = [], urluriSursa = [];
  const infoDe = c.infoDe || function (a) { return infoProiect(a, { db: c.proiecteDb, manual: c.proiecteManual, amp: c.amp }); };
  const nr = { obiective: 0, inceput: 0, sfarsit: 0, n: 0 };
  o.acorduri.forEach(function (a) {
    const g = agregaAcord(a, c.peAcord.get(a.id) || [], c.cursuri), r = [], info = infoDe(a);
    nr.n++;
    r[cProiect] = numeAfisat(a, en);
    if (cDon >= 0) r[cDon] = a.donatori.join(' / ');
    r[cDesc] = descriere(a, en, info);
    r[cInc] = info.inceput ? fmtDataPartiala(info.inceput.v) : '';
    r[cSfa] = info.sfarsit ? fmtDataPartiala(info.sfarsit.v) : '';
    if (info.obiective) nr.obiective++;
    if (info.inceput) nr.inceput++;
    if (info.sfarsit) nr.sfarsit++;
    r[cSursa] = textSursaProiect(info, en) + (info.contradictie ? ' · ' + t('datele se contrazic', 'the dates contradict each other') : '');
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
    randuri.push(r); urluri.push(a.url); urluriSursa.push(legaturaSursaProiect(info));
  });
  const latimi = {}; cols.forEach(function (x, k) { latimi[k] = x[2]; });
  const etichete = {}; etichete[cTip] = CULORI_TIP;
  etichete[cInTotal] = [[t('da', 'yes'), 'FF16794F', 'FFE3F4EC'], [t('nu: dublură', 'no: duplicate'), 'FF6B7284', 'FFEEF0F4'],
                        [t('nu: nu se adună', 'no: not added up'), 'FF6B7284', 'FFEEF0F4'], [t('nu: fără curs', 'no: no rate'), 'FF6B7284', 'FFEEF0F4']];
  const linkuri = {}; linkuri[cLink] = function (rand, i) { return urluri[i]; }; linkuri[cSursa] = function (rand, i) { return urluriSursa[i]; };
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
  note.push(t('Descrierea succintă e obiectivele proiectului; datele de început și de finalizare sunt cele ale proiectului. Fiecare informație vine, în ordine, din: ce a introdus un utilizator în pagină; o sursă oficială (adresa documentului e în coloana „Sursa obiectivelor și a datelor”); AMP, platforma de gestionare a asistenței externe, doar pentru proiectele legate sigur de acord (denumire, finanțator și sumă coincid; acolo, „Data finalizării” e data propusă de terminare). Unde celula e goală, nu s-a găsit o sursă. O dată întreagă e o dată adevărată în Excel (se poate sorta); una cunoscută doar cu luna și anul (03.2026) sau doar cu anul (2026) rămâne text, cât spune sursa. Aici: obiective la ' + nr.obiective + ' din ' + nr.n + ' proiecte, data de început la ' + nr.inceput + ', data finalizării la ' + nr.sfarsit + '.',
    'The short description is the project objectives; the start and completion dates are those of the project. Each item comes, in this order, from: what a user entered in the page; an official source (the address of the document is in the "Source of objectives and dates" column); AMP, the external assistance management platform, only for projects linked with certainty to the agreement (name, funder and amount all agree; there, the completion date is the proposed completion date). An empty cell means no source was found. A full date is a real Excel date (it sorts); one known only as month and year (03.2026) or only as a year (2026) stays text, as far as the source goes. Here: objectives for ' + nr.obiective + ' of ' + nr.n + ' projects, start date for ' + nr.inceput + ', completion date for ' + nr.sfarsit + '.'));
  if (c.ampNota) note.push(c.ampNota);                // ce s-a întâmplat cu citirea datelor din AMP (raport live, arhivă)
  if (c.omise && c.omise.length) note.push(t('Nu sunt incluse ' + c.omise.length + ' rânduri-umbrelă din registru (negocieri sau memorandumuri pentru acorduri care au deja rândurile lor, cu aceleași sume): ' + c.omise.map(function (x) { return x.a.nume; }).join('; ') + '.',
    c.omise.length + ' umbrella rows of the register are not included (negotiations or memoranda for agreements that already have their own rows, with the same amounts): ' + c.omise.map(function (x) { return x.a.nume; }).join('; ') + '.'));
  if (o.cuDonatori) note.push(t('Un acord cu mai mulți donatori apare o singură dată, cu toți donatorii în coloana „Donatori”.', 'An agreement with several donors appears once, with all its donors in the "Donors" column.'));
  else note.push(t('Un acord finanțat de mai mulți parteneri apare la fiecare dintre ei, cu suma întreagă a acordului.', 'An agreement financed by several partners appears under each of them, with the whole amount of the agreement.'));
  note.push({ t: t('Pagina, online: ', 'The page, online: ') + c.baza, u: c.baza });
  return {
    foaie: o.foaie, titlu: o.titlu, subtitlu: o.subtitlu,
    antete: cols.map(function (x) { return x[0]; }), tipuri: cols.map(function (x) { return x[1]; }).join(''), randuri: randuri, latimi: latimi,
    total: { eticheta: t('Total (rândurile vizibile)', 'Total (visible rows)'), suma: [cEur, cDebEur, cRest, cNr] },
    inghetaColoane: 1, maxLinii: 3, paginiLatime: 'auto', bare: [cPct],
    grupe: [{ de: cProiect, pana: cSfa, text: t('PROIECTUL', 'THE PROJECT') }, { de: cTip, pana: cSemnat, text: t('ACORDUL', 'THE AGREEMENT') },
            { de: cSuma, pana: cEur, text: t('SUMA PROIECTULUI', 'PROJECT AMOUNT') },
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
  MAX_OBIECTIVE: MAX_OBIECTIVE, SURSE_PROIECT: SURSE_PROIECT,
  normalizeazaManual: normalizeazaManual, gasesteAcord: gasesteAcord, numeAfisat: numeAfisat,
  dataPartiala: dataPartiala, esteDataPartiala: esteDataPartiala, fmtDataPartiala: fmtDataPartiala, parseDataPartiala: parseDataPartiala, inceputDupaSfarsit: inceputDupaSfarsit,
  infoProiect: infoProiect, etichetaSursaProiect: etichetaSursaProiect, textSursaProiect: textSursaProiect, legaturaSursaProiect: legaturaSursaProiect,
  valideazaProiect: valideazaProiect, proiectDin: proiectDin, proiectDbValid: proiectDbValid, legaProiecte: legaProiecte,
  idNou: idNou, eurIntrare: eurIntrare, intrareValida: intrareValida, valideazaFormular: valideazaFormular, intrareDin: intrareDin, lega: lega,
  agregaAcord: agregaAcord, rezumat: rezumat, potriveste: potriveste, ordoneaza: ordoneaza, ordoneazaDonatori: ordoneazaDonatori,
  citesteHash: citesteHash, scrieHash: scrieHash,
  EroareDepozit: EroareDepozit, dateGoale: dateGoale, citesteText: citesteText, aplicaOps: aplicaOps, text: text, b64DinText: b64DinText, textDinB64: textDinB64,
  Depozit: Depozit, Seif: Seif,
  excelDonator: excelDonator, excelTotal: excelTotal, excelPeDonatori: excelPeDonatori, unice: unice
};
});
