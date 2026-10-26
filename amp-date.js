/* amp-date.js — datele de început și de finalizare ale proiectelor, luate din AMP, pentru pagina „Debursări pe acorduri”.

   AMP (platforma de gestionare a asistenței externe) are pentru fiecare proiect „Data efectivă de începere” („Actual Start Date”) și „Data propusă
   de terminare” („Proposed Completion Date”). Registrul legis.md nu are aceste date: ele se iau din AMP după ce rândul din registru se leagă de
   proiectul lui AMP, cu aceeași potrivire prudentă ca în panoul „De la lege la bani” (legatura-amp.js: denumire + finanțator + sumă).

   Două surse, ca în dashboard (index.html):
     · arhiva încorporată (arhiva.js, export AMP 1993–2022), încărcată doar când e nevoie;
     · raportul live 661, prin același proxy (amp.vivi.md), cu termen-limită; are prioritate la același AMP ID.
   Dacă raportul live nu răspunde, rămâne arhiva; pagina spune ce s-a întâmplat.

   Legătura rând → proiect AMP are două trepte de încredere, pe care pagina le arată diferit:
     sigur    = confirmată de un om (date/legaturi_amp.json) sau denumire + finanțator + sumă care coincid;
     probabil = denumire + finanțator care se potrivesc, dar suma lipsește sau diferă.
   Potrivirile ambigue (mai multe proiecte la fel de potrivite, același proiect pentru mai multe acorduri) nu dau nicio dată.

   Fără DOM în logică: rulează la fel în Node (teste_amp_date.js). */
(function (root, factory) {
  'use strict';
  const api = factory(root);
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  if (typeof window !== 'undefined') window.AmpDate = api;
})(typeof globalThis !== 'undefined' ? globalThis : (typeof self !== 'undefined' ? self : this), function (root) {
'use strict';

const AMP_PROXY = 'https://amp.vivi.md';
const AMP_RAPORT = 661;
const TERMEN_MS = 20000;
const AMP_QUERY = {
  name: 'spa-export',
  queryModel: { filters: {}, filtersApplied: true, settingsApplied: false, page: 1 },
  queryType: 'OLAP', type: 'QUERYMODEL',
  parameters: {}, plugins: {}, properties: {}, metadata: {},
  querySettings: { info: ['generatedHeaders'] }
};

const pad = function (n) { return (n < 10 ? '0' : '') + n; };
const fara = function (s) { return String(s == null ? '' : s).toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, '').trim(); };

/* ------------------------------------------------------------------ date */
/* „15/09/2020” (ordinea zi/lună/an, ca în exporturile AMP) → „2020-09-15”. Întoarce '' când nu e o dată reală. `ordine` = 'dmy' (implicit) sau
   'mdy', când un export folosește luna prima; se alege din valorile fișierului (vezi ordineaDatelor). */
function dataAmp(s, ordine) {
  s = String(s == null ? '' : s).trim();
  if (!s) return '';
  let a, l, z, m;
  if ((m = /^(\d{4})-(\d{2})-(\d{2})(?:[T ].*)?$/.exec(s))) { a = +m[1]; l = +m[2]; z = +m[3]; }
  else if ((m = /^(\d{1,2})[\/.\-](\d{1,2})[\/.\-](\d{4})(?:\s.*)?$/.exec(s))) {
    a = +m[3];
    if (ordine === 'mdy') { l = +m[1]; z = +m[2]; } else { z = +m[1]; l = +m[2]; }
  } else return '';
  if (a < 1950 || a > 2100 || l < 1 || l > 12 || z < 1 || z > 31) return '';
  const d = new Date(Date.UTC(a, l - 1, z));
  if (d.getUTCFullYear() !== a || d.getUTCMonth() !== l - 1 || d.getUTCDate() !== z) return '';
  return a + '-' + pad(l) + '-' + pad(z);
}
/* Un export cu „03/15/2020” (luna prima) se recunoaște după valorile cu al doilea număr peste 12; fără astfel de valori, rămâne zi/lună/an. */
function ordineaDatelor(valori) {
  let zl = 0, lz = 0;
  (valori || []).forEach(function (v) {
    const m = /^(\d{1,2})[\/.\-](\d{1,2})[\/.\-]\d{4}/.exec(String(v == null ? '' : v).trim());
    if (!m) return;
    if (+m[1] > 12) zl++; else if (+m[2] > 12) lz++;
  });
  return lz > zl ? 'mdy' : 'dmy';
}
const anDin = function (iso) { return iso ? +iso.slice(0, 4) : null; };

/* ------------------------------------------------------------------ arhiva */
/* ARCHIVE din arhiva.js: { id, t (titlu), d (donatori), ds, de (DD/MM/YYYY), vp, y: { an: [angajamente, debursări, …] } } */
function sumeAni(y) {
  let ang = 0, deb = 0, primul = null;
  Object.keys(y || {}).forEach(function (k) {
    const v = y[k] || [], a = +v[0] || 0, d = +v[1] || 0;
    ang += a; deb += d;
    if ((a || d) && /^(19|20)\d\d$/.test(k) && (primul == null || +k < primul)) primul = +k;
  });
  return { ang: ang, deb: deb, primul: primul };
}
function dinArhiva(arhiva) {
  const ordine = ordineaDatelor([].concat.apply([], (arhiva || []).map(function (a) { return [a && a.ds, a && a.de]; })));
  return (arhiva || []).filter(function (a) { return a && a.id; }).map(function (a) {
    const ds = dataAmp(a.ds, ordine), de = dataAmp(a.de, ordine), s = sumeAni(a.y);
    return { id: String(a.id), titluri: [a.t].filter(Boolean), donatori: Array.isArray(a.d) ? a.d.slice() : (a.d ? [String(a.d)] : []),
             inceput: anDin(ds) || s.primul, ang: s.ang, deb: s.deb, vp: +a.vp || 0, ds: ds, de: de, src: 'arhiva' };
  });
}

/* ------------------------------------------------------------------ raportul live (CSV) */
function tokenizeCSV(text, delim) {
  const rows = []; let row = [], cur = '', inQuotes = false;
  for (let i = 0; i < text.length; i++) {
    const c = text[i];
    if (inQuotes) {
      if (c === '"') { if (text[i + 1] === '"') { cur += '"'; i++; } else inQuotes = false; }
      else cur += c;
    } else if (c === '"') inQuotes = true;
    else if (c === delim) { row.push(cur); cur = ''; }
    else if (c === '\r') { /* \n încheie rândul */ }
    else if (c === '\n') { row.push(cur); rows.push(row); row = []; cur = ''; }
    else cur += c;
  }
  if (cur.length || row.length) { row.push(cur); rows.push(row); }
  return rows.filter(function (r) { return r.length > 1 || (r.length === 1 && r[0].trim() !== ''); });
}
/* Aceleași recunoașteri de coloane ca în index.html: raportul vine în română sau în engleză, iar denumirile nu sunt literale. */
function coloanaFinantare(h) {
  const x = fara(h);
  if (!/funding|finantare/.test(x) || !/total/.test(x)) return null;
  const an = x.match(/\b(\d{4})\b/);
  if (!an) return null;
  if (/commitment|angajament/.test(x)) return { an: an[1], m: 0 };
  if (/disbursement|debursa|plati/.test(x)) return { an: an[1], m: 1 };
  return null;
}
function coloanaTotalRaport(h) {
  const x = fara(h);
  if (!/total/.test(x) || /\b\d{4}\b/.test(x)) return null;
  if (/planned|planificat|pipeline/.test(x)) return null;
  const sfarsit = /total\w*$/.test(x);
  if (/commitment|angajament/.test(x)) return { m: 0, sfarsit: sfarsit };
  if (/disbursement|debursa|plati/.test(x)) return { m: 1, sfarsit: sfarsit };
  return null;
}
const numarCelula = function (s) {
  s = String(s == null ? '' : s).trim().replace(/\s/g, '').replace(/,/g, '');
  if (!s) return 0;
  const v = parseFloat(s);
  return isNaN(v) ? 0 : v;
};
/* Raportul live → proiecte. Întoarce { proiecte, areDate, coloaneSume }: `areDate` spune dacă raportul are coloanele de date (altfel, datele
   proiectelor se iau din arhivă); `coloaneSume` = câte coloane de sume s-au recunoscut (0 = denumirile s-au schimbat, sumele sunt necunoscute). */
function dinCsv(csv) {
  const text = String(csv == null ? '' : csv).replace(/^﻿/, '');
  const prima = text.split(/\r\n|\n/, 1)[0] || '';
  const delim = (prima.match(/;/g) || []).length >= (prima.match(/,/g) || []).length ? ';' : ',';
  const rows = tokenizeCSV(text, delim);
  if (rows.length < 2) throw new Error('CSV live fără rânduri de date');
  const h = rows[0].map(function (x) { return (x || '').trim(); });
  const gaseste = function (nume) {
    for (let k = 0; k < nume.length; k++) {
      const i = h.findIndex(function (x) { return x.toLowerCase() === nume[k].toLowerCase(); });
      if (i !== -1) return i;
    }
    return -1;
  };
  const iId = gaseste(['AMP ID', 'ID PGA']);
  const iTitlu = gaseste(['Project Title', 'Titlul proiectului']);
  const iDonor = gaseste(['Donor Agency', 'Organizație finanțatoare']);
  const iStart = gaseste(['Actual Start Date', 'Data efectivă de începere']);
  const iEnd = gaseste(['Proposed Completion Date', 'Data propusă de terminare']);
  if (iId === -1) throw new Error('CSV live fără coloana „AMP ID”');
  const fin = [];
  h.forEach(function (x, i) { const m = coloanaFinantare(x); if (m) fin.push({ i: i, an: m.an, m: m.m }); });
  const totaluri = [[], []];
  h.forEach(function (x, i) { const m = coloanaTotalRaport(x); if (m) totaluri[m.m].push({ i: i, sfarsit: m.sfarsit }); });
  const colTotal = totaluri.map(function (l) {
    const cu = l.filter(function (c) { return c.sfarsit; });
    if (cu.length === 1) return cu[0].i;
    return l.length === 1 ? l[0].i : -1;
  });
  const ordine = ordineaDatelor([].concat(iStart === -1 ? [] : rows.slice(1).map(function (r) { return r[iStart]; }), iEnd === -1 ? [] : rows.slice(1).map(function (r) { return r[iEnd]; })));
  const celula = function (c, i) { return i === -1 ? '' : String(c[i] == null ? '' : c[i]).replace(/\s+/g, ' ').trim(); };
  const dupa = new Map(), ordineId = [];
  for (let r = 1; r < rows.length; r++) {
    const c = rows[r];
    if (!c || c.length < 2) continue;
    const id = String(c[iId] || '').trim();
    if (!id) continue;
    const sume = [0, 0];
    let primul = null;
    fin.forEach(function (f) {
      const v = numarCelula(c[f.i]);
      if (!v) return;
      sume[f.m] += v;
      if (primul == null || +f.an < primul) primul = +f.an;
    });
    // banii scriși de raport în afara anilor lui: totalul raportului îi cuprinde (aceeași regulă ca în dashboard)
    [0, 1].forEach(function (m) {
      if (colTotal[m] === -1) return;
      const total = numarCelula(c[colTotal[m]]);
      if (total - sume[m] > 1) sume[m] = total;
    });
    const rand = { id: id, titlu: celula(c, iTitlu), donor: celula(c, iDonor), ds: dataAmp(celula(c, iStart), ordine), de: dataAmp(celula(c, iEnd), ordine),
                   ang: sume[0], deb: sume[1], primul: primul, brut: c };
    const g = dupa.get(id);
    if (!g) { rand.randuri = [c]; dupa.set(id, rand); ordineId.push(rand); continue; }
    // același AMP ID pe mai multe rânduri: rândurile identice se numără o dată, celelalte se adună
    if (g.randuri.some(function (b) { return b.length === c.length && b.every(function (v, i) { return v === c[i]; }); })) continue;
    g.randuri.push(c);
    g.ang += rand.ang; g.deb += rand.deb;
    if (rand.donor && g.donor.indexOf(rand.donor) < 0) g.donor += ' | ' + rand.donor;
    if (!g.titlu) g.titlu = rand.titlu;
    if (!g.ds) g.ds = rand.ds;
    if (!g.de) g.de = rand.de;
    if (rand.primul != null && (g.primul == null || rand.primul < g.primul)) g.primul = rand.primul;
  }
  const proiecte = ordineId.map(function (g) {
    return { id: g.id, titluri: [g.titlu].filter(Boolean), donatori: g.donor ? [g.donor] : [], inceput: anDin(g.ds) || g.primul, ang: g.ang, deb: g.deb, vp: 0,
             ds: g.ds, de: g.de, src: 'live' };
  });
  return { proiecte: proiecte, areDate: iStart !== -1 || iEnd !== -1, coloaneSume: fin.length };
}

/* Arhiva și raportul live într-o singură listă, după AMP ID: la același proiect, raportul live are prioritate (și datele lui, chiar goale).
   Când raportul n-are deloc coloane de date, datele rămân cele din arhivă. */
function uneste(arhiva, live, liveAreDate) {
  const m = new Map();
  (arhiva || []).forEach(function (p) { m.set(p.id, p); });
  (live || []).forEach(function (p) {
    const vechi = m.get(p.id);
    if (vechi && liveAreDate === false) m.set(p.id, Object.assign({}, p, { ds: vechi.ds, de: vechi.de, inceput: p.inceput || vechi.inceput }));
    else m.set(p.id, p);
  });
  return Array.from(m.values());
}

/* ------------------------------------------------------------------ potrivirea cu rândurile din registru */
/* Anii actelor unui rând (semnare, primul și ultimul act, fiecare act). */
function aniiRand(a) {
  const v = [];
  [a.semnat, a.primul, a.ultimul].concat((a.acte || []).map(function (x) { return x.data; })).forEach(function (d) {
    const m = /(\d{4})\s*$/.exec(String(d || ''));
    if (m && +m[1] >= 1990) v.push(+m[1]);
  });
  return v;
}
/* `acorduri` = rândurile din date/acorduri_legare.json (cu `parteneriAcord`: finanțatorul rândului, nu toți partenerii grupului).
   Întoarce { peAcord: Map(id rând → { id, titlu, inceput, sfarsit, nivel: 'sigur' | 'probabil', legatura }), numere }.
   Pentru datele din pagină se iau doar legăturile „sigur”; cele „probabil” rămân ca indiciu. Pe lângă prudența din legatura-amp.js, aici se mai
   cere că (1) proiectul AMP nu începe cu mai mult de doi ani înaintea primului act al rândului (un proiect mai vechi decât acordul nu e al lui) și
   (2) un același proiect AMP nu se dă la două rânduri ale aceluiași finanțator (de pildă faza I și faza II a unui împrumut, cu sume apropiate):
   îl primește rândul cu suma cea mai apropiată, iar la egalitate niciunul. Un proiect cofinanțat de doi finanțatori diferiți rămâne la amândoi. */
function potriveste(acorduri, proiecte, confirmari, LA) {
  LA = LA || root.LegaturaAmp || (typeof require === 'function' ? require('./legatura-amp.js') : null);
  if (!LA) throw new Error('legatura-amp.js nu e încărcat');
  const rand = (acorduri || []).map(function (a) { return Object.assign({}, a, { parteneri: a.parteneriAcord || a.parteneri || '' }); });
  const pr = proiecte.map(function (p) { return { id: p.id, titluri: p.titluri, donatori: p.donatori, inceput: p.inceput, ang: p.ang, deb: p.deb, vp: p.vp }; });
  const rez = LA.potriveste(rand, pr, confirmari || {});
  const peProiect = new Map(proiecte.map(function (p) { return [p.id, p]; }));
  const peAcord = new Map(), n = { sigur: 0, probabil: 0, ambiguu: 0, fara: 0, prea_vechi: 0 };
  const pePr = new Map();
  rez.rezultate.forEach(function (r) {
    const l = r.legaturi[0];
    if (!l) { n.fara++; return; }
    const nivel = l.nivel === 'confirmat' || l.nivel === 'suma' ? 'sigur' : l.nivel === 'titlu' ? 'probabil' : null;
    if (!nivel) { n.ambiguu++; return; }
    const p = peProiect.get(l.idProiect);
    if (!p || !(p.ds || p.de)) { n.fara++; return; }
    if (nivel === 'sigur' && l.nivel !== 'confirmat' && p.ds) {
      const ani = aniiRand(r.acord);
      if (ani.length && +p.ds.slice(0, 4) < Math.min.apply(null, ani) - 2) { n.prea_vechi++; return; }
    }
    peAcord.set(r.acord.id, { id: p.id, titlu: p.titluri[0] || '', inceput: p.ds, sfarsit: p.de, nivel: nivel, legatura: l.nivel });
    n[nivel]++;
    if (nivel === 'sigur' && l.nivel !== 'confirmat') {
      const fam = LA.familii(r.acord.parteneri).sort().join('+') || '?';
      const rel = l.suma && l.suma.stare === 'da' ? l.suma.rel : 1;
      (pePr.get(p.id) || pePr.set(p.id, []).get(p.id)).push({ id: r.acord.id, fam: fam, rel: rel });
    }
  });
  pePr.forEach(function (lista) {
    if (lista.length < 2) return;
    const pe = {};
    lista.forEach(function (x) { (pe[x.fam] = pe[x.fam] || []).push(x); });
    Object.keys(pe).forEach(function (k) {
      const l = pe[k].sort(function (x, y) { return x.rel - y.rel; });
      if (l.length < 2) return;
      const egal = l[1].rel - l[0].rel < 0.005;
      l.forEach(function (x, i) {
        if (i === 0 && !egal) return;
        peAcord.delete(x.id); n.sigur--; n.ambiguu++;
      });
    });
  });
  return { peAcord: peAcord, numere: n };
}

/* ------------------------------------------------------------------ încărcarea (browser) */
async function fetchCuTermen(F, url, opt, ms) {
  const ctrl = typeof AbortController !== 'undefined' ? new AbortController() : null;
  const t = ctrl ? setTimeout(function () { ctrl.abort(); }, ms) : null;
  try {
    return await F(url, Object.assign({}, opt, ctrl ? { signal: ctrl.signal } : {}));
  } catch (e) {
    if (e && e.name === 'AbortError') throw new Error('serverul nu a răspuns în ' + Math.round(ms / 1000) + ' secunde');
    throw e;
  } finally { if (t) clearTimeout(t); }
}
async function citesteRaportLive(opt) {
  const F = opt.fetch || function () { return root.fetch.apply(root, arguments); };
  const url = (opt.proxy || AMP_PROXY) + '/rest/data/saikureport/export/csv/' + AMP_RAPORT + '?language=' + (opt.limba || 'ro');
  const r = await fetchCuTermen(F, url, { method: 'POST', headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
                                           body: 'query=' + encodeURIComponent(JSON.stringify(AMP_QUERY)) }, opt.termenMs || TERMEN_MS);
  if (!r.ok) throw new Error('HTTP ' + r.status);
  const t = await r.text();
  if (!t || t.length < 100) throw new Error('răspuns gol de la AMP');
  return t;
}
function incarcaArhiva(opt) {
  /* `ARCHIVE` e o constantă globală a arhiva.js: se vede din orice script clasic, dar nu e proprietate a lui window. */
  if (typeof ARCHIVE !== 'undefined' && Array.isArray(ARCHIVE)) return Promise.resolve(ARCHIVE);
  if (opt.arhiva) return Promise.resolve(opt.arhiva);
  if (typeof document === 'undefined') return Promise.reject(new Error('arhiva nu e disponibilă'));
  return new Promise(function (ok, nu) {
    const s = document.createElement('script');
    s.src = opt.cale || 'arhiva.js';
    s.onload = function () { typeof ARCHIVE !== 'undefined' && Array.isArray(ARCHIVE) ? ok(ARCHIVE) : nu(new Error('arhiva.js nu conține ARCHIVE')); };
    s.onerror = function () { nu(new Error('nu pot încărca arhiva.js')); };
    document.head.appendChild(s);
  });
}
/* Tot lanțul: arhiva + raportul live → potrivirea cu rândurile. `opt`: { acorduri, confirmari, fetch, arhiva, cale, proxy, limba, termenMs, onStare }.
   Un eșec la una dintre surse nu oprește restul; starea spune ce s-a întâmplat. Întoarce { peAcord, stare }. */
async function incarca(opt) {
  const stare = { arhiva: null, live: null, eroareArhiva: '', eroareLive: '', legate: null, proiecte: 0, faza: 'start' };
  const spune = function (faza) { stare.faza = faza; if (opt.onStare) { try { opt.onStare(Object.assign({}, stare)); } catch (e) { /* afișarea nu oprește lucrul */ } } };
  spune('start');
  let arhiva = [], live = [], liveAreDate = true;
  const sarhiva = incarcaArhiva(opt).then(function (a) { arhiva = dinArhiva(a); stare.arhiva = arhiva.length; }, function (e) { stare.eroareArhiva = String(e && e.message || e); });
  const slive = citesteRaportLive(opt).then(function (t) {
    const x = dinCsv(t);
    live = x.proiecte; liveAreDate = x.areDate; stare.live = live.length;
  }, function (e) { stare.eroareLive = String(e && e.message || e); });
  await Promise.all([sarhiva, slive]);
  spune('potrivire');
  const toate = uneste(arhiva, live, liveAreDate);
  stare.proiecte = toate.length;
  if (!toate.length) { spune('gata'); return { peAcord: new Map(), stare: stare }; }
  // pauză scurtă, ca browserul să afișeze starea înainte de calcul
  await new Promise(function (ok) { setTimeout(ok, 0); });
  const r = potriveste(opt.acorduri || [], toate, opt.confirmari);
  stare.legate = r.numere;
  spune('gata');
  return { peAcord: r.peAcord, stare: stare };
}

return {
  AMP_PROXY: AMP_PROXY, AMP_RAPORT: AMP_RAPORT, TERMEN_MS: TERMEN_MS,
  dataAmp: dataAmp, ordineaDatelor: ordineaDatelor, dinArhiva: dinArhiva, dinCsv: dinCsv, uneste: uneste, potriveste: potriveste,
  tokenizeCSV: tokenizeCSV, coloanaFinantare: coloanaFinantare, coloanaTotalRaport: coloanaTotalRaport,
  citesteRaportLive: citesteRaportLive, incarcaArhiva: incarcaArhiva, incarca: incarca
};
});
