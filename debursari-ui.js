/* debursari-ui.js — ce vede și ce atinge omul pe pagina „Debursări pe acorduri” (debursari.html).

   Calculele, salvarea în „baza de date” (date/debursari.json) și fișierele Excel sunt în debursari.js, testat în Node. Aici sunt doar:
   încărcarea datelor, lista donatorilor cu căsuțe, tabelele de proiecte, fereastra cu codul de acces, formularul de debursare,
   coada de modificări nesalvate și butoanele de export.

   Despre cod. Cheia de acces nu se scrie nicăieri în clar: rămâne în variabila `cod`, închisă în această funcție (nu în DOM, nu într-un
   obiect global, nu în adresa paginii). Dacă omul cere, se păstrează pe dispozitiv numai criptată cu un PIN (Debursari.Seif). */
(function () {
'use strict';

var D = window.Debursari;
var RAD = document.getElementById('debRoot');
if (!D || !RAD) return;

var STIL_V = '2026-10-14';                   // ca în registru: se schimbă când se schimbă xlsx-stil.js
var CH_COADA = 'deb_coada_v1';               // modificări încă nesalvate (ca să nu se piardă la o reîncărcare)
var CH_SEIF = 'deb_seif_v1';                 // codul, criptat cu PIN-ul ales de utilizator
var CH_RECENT = 'deb_recent_v1';             // ultima stare salvată de acest browser: site-ul public o primește cu 1–2 minute întârziere
var FEREASTRA_RECENT = 10 * 60 * 1000;
var URL_COD = 'https://github.com/settings/personal-access-tokens/new?name=' + encodeURIComponent('Debursari nistor.vivi.md') +
  '&description=' + encodeURIComponent('Scrie doar date/debursari.json din repository-ul acorduri (pagina Debursări pe acorduri).') +
  '&target_name=' + encodeURIComponent(D.CONFIG.repo.split('/')[0]) + '&expires_in=90&contents=write';

var cod = null;                              // cheia de acces, doar în memorie
var dep = D.Depozit();

var S = {
  en: document.documentElement.lang === 'en',
  faza: 'incarc', eroareInc: null,
  baza: null, serv: null, coada: [], dinMemorie: false, debEroare: null,
  ocupat: false, eroareSalv: null, ultimaSalv: '',
  intrari: [], peAcord: new Map(), orfane: [], nesalvate: new Set(), cache: new Map(), rezDon: new Map(),
  sel: [], q: '', tip: '', deb: '', sort: 'suma', dq: '', dsort: 'n',
  deschise: new Set(), f: {}, fe: {}, ed: null, conf: null,
  dlg: { mod: 'cod', eroare: '', ocupat: false, tine: false }
};

/* ------------------------------------------------------------------ utilitare */
function $(s, r) { return (r || document).querySelector(s); }
function L(ro, en) { return S.en ? en : ro; }
function esc(s) {
  return String(s == null ? '' : s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;').replace(/'/g, '&#39;');
}
function qs(s) { return String(s).replace(/\\/g, '\\\\').replace(/"/g, '\\"'); }
function fm(v, z) { return D.fmtSuma(v, S.en, z); }
function fb(v) { return D.fmtBani(v, S.en); }                       // sumă exactă: 1.250.000,50 (nu 1.250.000,5)
function cursData() { var d = S.baza.cursData || ''; return d ? (S.en ? D.dataTextEn(d) : d) : '—'; }   // data cursurilor, în limba paginii
function fEur(v) { return v == null ? '—' : fm(v, 0) + ' EUR'; }
/* procent în puncte (0,05 → „<0,1”, ca un procent nenul să nu pară zero) */
function fmPct(p) { return p > 0 && p < 0.1 ? '<' + fm(0.1, 1) : fm(p, 1); }
function lsGet(k) { try { return localStorage.getItem(k); } catch (e) { return null; } }
function lsSet(k, v) { try { localStorage.setItem(k, v); return true; } catch (e) { return false; } }
function lsDel(k) { try { localStorage.removeItem(k); } catch (e) { /* fără stocare locală */ } }
var timere = {};
function peste(cheie, f, ms) { clearTimeout(timere[cheie]); timere[cheie] = setTimeout(f, ms); }
function live(msg) {
  var el = $('#live');
  if (!el) return;
  el.textContent = '';
  setTimeout(function () { el.textContent = msg; }, 30);
}
function dataOraDin(iso) { var d = iso ? new Date(iso) : null; return d && !isNaN(d) ? D.dataOraRo(d) : ''; }
function dataRegistru(s) {
  var m = /^(\d{4})-(\d{2})-(\d{2})(?:[ T](\d{2}:\d{2}))?/.exec(s || '');
  return m ? m[3] + '.' + m[2] + '.' + m[1] + (m[4] ? ' ' + m[4] : '') : (s || '');
}
function paginaUrl() { return location.origin + location.pathname; }

function ic(p) { return '<svg viewBox="0 0 24 24" aria-hidden="true" focusable="false">' + p + '</svg>'; }
var IC = {
  lock: ic('<rect x="3" y="11" width="18" height="11" rx="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/>'),
  unlock: ic('<rect x="3" y="11" width="18" height="11" rx="2"/><path d="M7 11V7a5 5 0 0 1 9.9-1"/>'),
  plus: ic('<line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/>'),
  chev: ic('<polyline points="6 9 12 15 18 9"/>'),
  x: ic('<line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>'),
  trash: ic('<polyline points="3 6 5 6 21 6"/><path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6"/><path d="M10 11v6"/><path d="M14 11v6"/><path d="M9 6V4a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v2"/>'),
  edit: ic('<path d="M12 20h9"/><path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z"/>'),
  xl: ic('<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="8" y1="13" x2="16" y2="13"/><line x1="8" y1="17" x2="16" y2="17"/>'),
  layers: ic('<polygon points="12 2 2 7 12 12 22 7 12 2"/><polyline points="2 17 12 22 22 17"/><polyline points="2 12 12 17 22 12"/>'),
  euro: ic('<path d="M18 6a7 7 0 1 0 0 12"/><line x1="4" y1="10" x2="14" y2="10"/><line x1="4" y1="14" x2="14" y2="14"/>'),
  coin: ic('<circle cx="12" cy="12" r="9"/><path d="M12 7v10"/><path d="M15 9.5a3 3 0 0 0-3-1.5c-1.7 0-3 .9-3 2.2 0 3 6 1.6 6 4.6 0 1.4-1.4 2.2-3 2.2a3.3 3.3 0 0 1-3.2-1.5"/>'),
  pct: ic('<line x1="19" y1="5" x2="5" y2="19"/><circle cx="6.5" cy="6.5" r="2.5"/><circle cx="17.5" cy="17.5" r="2.5"/>')
};

/* ------------------------------------------------------------------ mesaje de eroare, în ambele limbi */
function msgEroare(e) {
  var c = e && e.cod, rep = D.CONFIG.repo;
  var m = {
    token: ['Codul nu e valid sau a expirat.', 'The code is not valid or has expired.'],
    drept: ['Codul nu poate scrie în repository-ul ' + rep + ' (are nevoie de „Contents: Read and write”).',
            'The code cannot write to the ' + rep + ' repository (it needs "Contents: Read and write").'],
    repo: ['Nu găsesc repository-ul ' + rep + ' cu acest cod. Verifică dacă la „Repository access” ai ales repository-ul acorduri.',
           'I cannot find the ' + rep + ' repository with this code. Check that you chose the acorduri repository under "Repository access".'],
    limita: ['GitHub a limitat temporar cererile. Încearcă din nou peste câteva minute.', 'GitHub has temporarily limited requests. Try again in a few minutes.'],
    retea: ['Nu pot ajunge la GitHub. Verifică conexiunea la internet și încearcă din nou.', 'Cannot reach GitHub. Check your internet connection and try again.'],
    conflict: ['Nu am putut salva: fișierul se tot schimbă. Încearcă din nou peste câteva secunde.', 'Could not save: the file keeps changing. Try again in a few seconds.'],
    format: ['Fișierul cu debursări nu are formatul așteptat.', 'The disbursements file does not have the expected format.'],
    pin: ['PIN greșit.', 'Wrong PIN.'],
    seif: ['Codul păstrat pe acest dispozitiv nu poate fi citit. Introdu codul din nou.', 'The code kept on this device cannot be read. Enter the code again.']
  }[c];
  return m ? m[S.en ? 1 : 0] : ((e && e.message) || L('Eroare necunoscută.', 'Unknown error.'));
}

/* ------------------------------------------------------------------ date derivate */
function recalc() {
  if (!S.baza) return;
  var date = D.aplicaOps(S.serv || D.dateGoale(), S.coada);
  S.intrari = date.intrari;
  S.nesalvate = new Set(S.coada.filter(function (o) { return o.t !== 'del'; }).map(function (o) { return o.e.id; }));
  var l = D.lega(S.intrari, S.baza);
  S.peAcord = l.peAcord; S.orfane = l.orfane;
  S.cache = new Map(); S.rezDon = new Map();
}
function ag(a) {
  var x = S.cache.get(a.id);
  if (!x) { x = D.agregaAcord(a, S.peAcord.get(a.id) || [], S.baza.cursuri); S.cache.set(a.id, x); }
  return x;
}
function rezDon(d) {
  var x = S.rezDon.get(d.cheie);
  if (!x) { x = D.rezumat(d.acorduri, S.peAcord, S.baza.cursuri); S.rezDon.set(d.cheie, x); }
  return x;
}
function filtru() { return { q: S.q, tip: S.tip, deb: S.deb, peAcord: S.peAcord }; }
function filtrate(lista) {
  var f = filtru();
  return D.ordoneaza(lista.filter(function (a) { return D.potriveste(a, f); }), S.sort, S.peAcord, S.baza.cursuri);
}
function donatoriAfisati() {
  var cuv = D.fold(S.dq).split(/\s+/).filter(Boolean);
  var lst = S.baza.donatori.filter(function (d) {
    if (!cuv.length) return true;
    var h = D.fold(d.cheie + ' ' + D.numeDonator(d.cheie, false) + ' ' + D.numeDonator(d.cheie, true));
    return cuv.every(function (c) { return h.indexOf(c) >= 0; });
  });
  return D.ordoneazaDonatori(lst, S.dsort, S.peAcord, S.baza.cursuri, S.en);
}
function donatoriAlesi() {
  var set = new Set(S.sel);
  return D.ordoneazaDonatori(S.baza.donatori.filter(function (d) { return set.has(d.cheie); }), S.dsort, S.peAcord, S.baza.cursuri, S.en);
}
function listaKpi() { return S.sel.length ? D.unice(donatoriAlesi()) : S.baza.acorduri; }
function texteFiltre() {
  var p = [];
  if (S.q) p.push(L('căutare „', 'search "') + S.q + L('”', '"'));
  if (S.tip) p.push(L('tip: ', 'type: ') + D.etichetaTip(S.tip, S.en));
  if (S.deb) p.push(S.deb === 'cu' ? L('doar cu debursări', 'only with disbursements') : L('doar fără debursări', 'only without disbursements'));
  return p.length ? L('filtre: ', 'filters: ') + p.join('; ') : '';
}

/* ------------------------------------------------------------------ păstrarea locală: coada nesalvată și ultima stare */
function opValida(o) {
  return !!o && ((o.t === 'del' && typeof o.id === 'string') || ((o.t === 'add' || o.t === 'upd') && D.intrareValida(o.e)));
}
function scrieCoada() {
  if (!S.coada.length) lsDel(CH_COADA); else lsSet(CH_COADA, JSON.stringify({ v: 1, ops: S.coada }));
}
function citesteCoada() {
  var t = lsGet(CH_COADA);
  if (!t) return [];
  try { var o = JSON.parse(t); return o && o.v === 1 && Array.isArray(o.ops) ? o.ops.filter(opValida) : []; } catch (e) { return []; }
}
function pastreazaRecent() {
  if (S.serv) lsSet(CH_RECENT, JSON.stringify({ v: 1, la: Date.now(), date: S.serv }));
}
function citesteRecent() {
  var t = lsGet(CH_RECENT);
  if (!t) return null;
  try {
    var o = JSON.parse(t);
    if (o && o.v === 1 && Date.now() - o.la < FEREASTRA_RECENT && o.date && Array.isArray(o.date.intrari)) return o.date;
  } catch (e) { /* ignorat */ }
  return null;
}
function areSeif() { var t = lsGet(CH_SEIF); if (!t) return null; try { return JSON.parse(t); } catch (e) { return null; } }

/* ------------------------------------------------------------------ încărcarea datelor */
function incarca() {
  S.faza = 'incarc'; S.eroareInc = null;
  randeazaTot();
  var pA = fetch(D.CONFIG.sursaAcorduri, { cache: 'no-cache' }).then(function (r) {
    if (!r.ok) throw new Error('HTTP ' + r.status);
    return r.json();
  });
  var pD = dep.citestePublic().then(function (d) { return { d: d }; }, function (e) { return { e: e }; });
  Promise.all([pA, pD]).then(function (r) {
    S.baza = D.pregateste(r[0]);
    S.serv = r[1].d || D.dateGoale();
    S.debEroare = r[1].e || null;
    var rec = citesteRecent();
    S.dinMemorie = !!(rec && (rec.actualizat || '') > (S.serv.actualizat || ''));
    if (S.dinMemorie) S.serv = rec;
    S.coada = citesteCoada();
    recalc();
    aplicaHash(location.hash);
    S.faza = 'gata';
    randeazaTot();
  }, function (e) {
    S.faza = 'eroare'; S.eroareInc = e;
    randeazaTot();
  });
}
function aplicaHash(h) {
  var o = D.citesteHash(h);
  var cunoscut = new Set(S.baza.donatori.map(function (d) { return d.cheie; }));
  S.sel = o.d.filter(function (k) { return cunoscut.has(k); });
  S.q = o.q; S.tip = o.tip; S.deb = o.deb; S.sort = o.sort || 'suma';
}
function scrieHash() {
  var h = D.scrieHash({ d: S.sel, q: S.q, tip: S.tip, deb: S.deb, sort: S.sort });
  try { history.replaceState(null, '', location.pathname + location.search + h); } catch (e) { /* adresa rămâne cum e */ }
}

/* ------------------------------------------------------------------ randare: capul și bara de acces */
function randeazaCap() {
  $('#tTitlu').textContent = L('Debursări pe acorduri', 'Disbursements by agreement');
  $('#tSub').textContent = L('Acordurile din registrul legis.md, repartizate pe donatori. Bifează un donator ca să vezi proiectele lui; sumele debursate se introduc de mână, după ce introduci codul de acces.',
                              'The agreements from the legis.md register, grouped by donor. Tick a donor to see its projects; disbursed amounts are entered by hand after you enter the access code.');
  if (!S.baza) { $('#topMeta').innerHTML = ''; return; }
  var nd = S.intrari.length;
  $('#topMeta').innerHTML =
    '<span>' + L('Registru legis.md: ', 'legis.md register: ') + '<b>' + esc(dataRegistru(S.baza.actualizat) || '—') + '</b></span>' +
    '<span>' + L('Cursuri BCE: ', 'ECB rates: ') + '<b>' + esc(cursData()) + '</b></span>' +
    '<span>' + L('Debursări salvate: ', 'Saved disbursements: ') + '<b>' + nd + '</b>' + (S.serv && S.serv.actualizat ? ' · ' + esc(dataOraDin(S.serv.actualizat)) : '') + '</span>';
}
function areBlocari() { return !cod; }
function randeazaAcces() {
  var cls = 'acces', ico = IC.lock, tit, sub = '', btns = '', extra = '';
  var n = S.coada.length, seif = areSeif();
  if (cod) {
    cls += ' deblocat'; ico = IC.unlock;
    tit = L('Modificări permise', 'Editing unlocked');
    if (S.ocupat) sub = L('Se salvează…', 'Saving…');
    else if (S.eroareSalv) {
      cls += ' eroare';
      sub = '<span class="rau">' + esc(msgEroare(S.eroareSalv)) + '</span> ' + (n ? esc(L(n + ' modificări rămân nesalvate.', n + ' changes are still unsaved.')) : '');
      btns += '<button type="button" class="btn p" data-act="retry">' + L('Încearcă din nou', 'Try again') + '</button>';
    } else if (n) {
      cls += ' nesalvat';
      sub = esc(L(n + ' modificări nesalvate.', n + ' unsaved changes.'));
      btns += '<button type="button" class="btn p" data-act="retry">' + L('Salvează acum', 'Save now') + '</button>';
    } else {
      sub = esc(L('Totul e salvat', 'Everything is saved') + (S.ultimaSalv ? ' (' + S.ultimaSalv + ')' : '') +
        L('. Pagina publică vede modificarea în 1–2 minute.', '. The public page shows the change within 1–2 minutes.'));
    }
    btns += '<button type="button" class="btn" data-act="lock">' + IC.lock + L('Blochează', 'Lock') + '</button>';
  } else {
    tit = L('Doar citire', 'Read-only');
    sub = esc(L('Oricine poate vedea debursările. Ca să introduci sau să modifici, introdu codul de acces: se deblochează câmpurile de debursare.',
                'Anyone can see the disbursements. To enter or change them, enter the access code: the disbursement fields unlock.'));
    if (n) {
      cls += ' nesalvat';
      sub += ' ' + esc(L('Ai ' + n + ' modificări nesalvate dintr-o sesiune anterioară; se salvează după ce introduci codul.',
                         'You have ' + n + ' unsaved changes from an earlier session; they are saved once you enter the code.'));
      btns += '<button type="button" class="btn rosu" data-act="renunta-coada">' + L('Renunță la ele', 'Discard them') + '</button>';
    }
    btns = '<button type="button" class="btn p" data-act="unlock">' + IC.unlock + (seif ? L('Deblochează cu PIN', 'Unlock with PIN') : L('Introdu codul', 'Enter the code')) + '</button>' + btns;
  }
  if (S.dinMemorie && !S.ocupat) extra += '<span>' + esc(L('Se arată starea salvată de tine acum câteva minute; pagina publică o primește în curând.',
                                                       'Showing the state you saved a few minutes ago; the public page receives it shortly.')) + '</span>';
  if (S.debEroare) extra += '<span class="rau">' + esc(L('Nu am putut citi debursările salvate (' + msgEroare(S.debEroare) + '). Cifrele de mai jos nu le includ.',
                                                          'Could not read the saved disbursements (' + msgEroare(S.debEroare) + '). The figures below do not include them.')) + '</span>' +
                              ' <button type="button" class="lnk" data-act="reincarca">' + L('Reîncearcă', 'Retry') + '</button>';
  $('#sAcces').innerHTML = '<div class="' + cls + '" role="region" aria-label="' + esc(L('Acces pentru modificări', 'Access for editing')) + '">' +
    '<div class="acces-ico">' + ico + '</div><div class="acces-txt"><b>' + esc(tit) + '</b><span>' + sub + '</span>' + extra + '</div>' +
    '<div class="acces-btns">' + btns + '</div></div>';
}

/* ------------------------------------------------------------------ randare: indicatori */
function kpi(lbl, ico, val, sub, bar) {
  return '<div class="kpi"><div class="lbl">' + lbl + '</div><div class="kpi-ico">' + ico + '</div><div class="val">' + val + '</div><div class="sub">' + sub + '</div>' + (bar || '') + '</div>';
}
function randeazaKpi() {
  if (!S.baza) { $('#sKpi').innerHTML = ''; return; }
  var r = D.rezumat(listaKpi(), S.peAcord, S.baza.cursuri), nd = S.sel.length || S.baza.donatori.length;
  var fara = S.debEroare ? L('nu am putut citi debursările', 'could not read the disbursements') : '';
  var c1 = kpi(L('Proiecte (acorduri)', 'Projects (agreements)'), IC.layers, fm(r.n, 0),
    esc(S.sel.length ? nd + L(' donatori bifați', ' donors ticked') : L('toți cei ', 'all ') + nd + L(' donatori', ' donors')) + ' · ' + r.cuSuma + esc(L(' cu sumă în total', ' with an amount in the total')));
  var c2 = kpi(L('Suma proiectelor', 'Project amounts'), IC.coin, esc(D.fmtCompact(r.sumaEur, S.en)) + '<small>EUR</small>',
    esc(fm(r.sumaEur, 0)) + ' EUR · ' + esc(L('fiecare acord o dată', 'each agreement once')));
  var c3 = kpi(L('Debursat', 'Disbursed'), IC.euro, S.debEroare ? '—' : esc(D.fmtCompact(r.debEur, S.en)) + '<small>EUR</small>',
    S.debEroare ? esc(fara) : (r.nIntrari ? r.nIntrari + ' ' + esc(r.nIntrari === 1 ? L('debursare', 'disbursement') : L('debursări', 'disbursements')) + esc(L(' la ', ' on ')) + r.nCuDeb + ' ' +
                                             esc(r.nCuDeb === 1 ? L('proiect', 'project') : L('proiecte', 'projects')) + (r.ultima ? ' · ' + esc(L('ultima ', 'last ')) + esc(D.dataRo(r.ultima)) : '')
                                           : esc(L('nicio debursare introdusă încă', 'no disbursement entered yet'))));
  var pct = r.pct == null || S.debEroare ? null : r.pct;
  var c4 = kpi(L('Debursat din sumă', 'Disbursed of amount'), IC.pct, pct == null ? '—' : esc(fmPct(pct * 100)) + '<small>%</small>',
    pct == null ? esc(L('fără proiecte cu sumă în selecție', 'no projects with an amount in the selection')) : esc(L('rest de debursat: ', 'left to disburse: ')) + esc(fEur(r.rest)),
    pct == null ? '' : '<div class="bar' + (pct > 1 ? ' peste' : '') + '"><i style="width:' + Math.min(100, pct * 100).toFixed(1) + '%"></i></div>');
  $('#sKpi').innerHTML = '<div class="kpis">' + c1 + c2 + c3 + c4 + '</div>';
}

/* ------------------------------------------------------------------ randare: lista donatorilor */
function htmlDon(d) {
  var r = rezDon(d), nume = D.numeDonator(d.cheie, S.en), on = S.sel.indexOf(d.cheie) >= 0;
  var det = r.n + ' ' + (r.n === 1 ? L('proiect', 'project') : L('proiecte', 'projects')) + (r.sumaEur ? ' · ' + D.fmtCompact(r.sumaEur, S.en) + ' EUR' : '') +
    (r.nIntrari && !S.debEroare ? ' · ' + L('deb. ', 'disb. ') + D.fmtCompact(r.debEur, S.en) : '');
  return '<label class="don' + (on ? ' on' : '') + '"><input type="checkbox" data-d="' + esc(d.cheie) + '"' + (on ? ' checked' : '') + '>' +
    '<b>' + esc(d.cheie) + '</b>' + (nume !== d.cheie ? '<span class="nm" title="' + esc(nume) + '">' + esc(nume) + '</span>' : '') +
    '<small>' + esc(det) + '</small></label>';
}
function randeazaPicker() {
  if (!S.baza) { $('#sPicker').innerHTML = ''; return; }
  var sorturi = [['n', L('după numărul de proiecte', 'by number of projects')], ['suma', L('după suma proiectelor', 'by project amount')],
                 ['deb', L('după debursări', 'by disbursements')], ['nume', L('alfabetic', 'alphabetical')]];
  $('#sPicker').innerHTML = '<section class="panel" aria-labelledby="hDon">' +
    '<div class="panel-head"><h2 id="hDon">' + L('Donatori', 'Donors') + ' <small>' + esc(L('bifează unul sau mai mulți', 'tick one or more')) + '</small></h2>' +
    '<div class="head-btns"><button type="button" class="btn" data-act="toti-afisati">' + L('Bifează cei afișați', 'Tick those shown') + '</button>' +
    '<button type="button" class="btn" data-act="sterge-sel">' + L('Șterge selecția', 'Clear selection') + '</button></div></div>' +
    '<div class="picker-tools"><input class="seek" id="dq" type="search" autocomplete="off" value="' + esc(S.dq) + '" placeholder="' + esc(L('Caută un donator…', 'Search a donor…')) + '" aria-label="' + esc(L('Caută un donator', 'Search a donor')) + '">' +
    '<select class="sel" id="dsort" aria-label="' + esc(L('Ordonează donatorii', 'Sort donors')) + '">' +
    sorturi.map(function (x) { return '<option value="' + x[0] + '"' + (S.dsort === x[0] ? ' selected' : '') + '>' + esc(x[1]) + '</option>'; }).join('') + '</select>' +
    '<span class="n" id="pickN"></span></div>' +
    '<div class="don-lista" id="donLista" role="group" aria-label="' + esc(L('Lista donatorilor', 'Donor list')) + '"></div></section>';
  randeazaLista();
}
function contorDonatori(nAfisati) {
  var el = $('#pickN');
  if (el) el.textContent = nAfisati + ' / ' + S.baza.donatori.length + ' ' + L('donatori', 'donors') + ' · ' + S.sel.length + ' ' + L('bifați', 'ticked');
}
function randeazaLista() {
  var el = $('#donLista');
  if (!el || !S.baza) return;
  var sus = el.scrollTop, lst = donatoriAfisati();
  el.innerHTML = lst.length ? lst.map(htmlDon).join('') : '<div class="gol-msg"><b>' + esc(L('Niciun donator nu se potrivește.', 'No donor matches.')) + '</b>' + esc(L('Încearcă alt cuvânt: acronimul sau o parte din denumire.', 'Try another word: the acronym or part of the name.')) + '</div>';
  el.scrollTop = sus;
  contorDonatori(lst.length);
}

/* ------------------------------------------------------------------ randare: bara de filtre și de export */
function randeazaTool() {
  if (!S.baza) { $('#sTool').innerHTML = ''; return; }
  var tipuri = '<option value="">' + esc(L('Toate tipurile', 'All types')) + '</option>' +
    D.ORDINE_TIP.map(function (t) { return '<option value="' + esc(t) + '"' + (S.tip === t ? ' selected' : '') + '>' + esc(D.etichetaTip(t, S.en)) + '</option>'; }).join('');
  var debs = [['', L('Cu și fără debursări', 'With and without disbursements')], ['cu', L('Doar cu debursări', 'Only with disbursements')], ['fara', L('Doar fără debursări', 'Only without disbursements')]];
  var sorturi = [['suma', L('Ordine: suma proiectului', 'Order: project amount')], ['deb', L('Ordine: debursat', 'Order: disbursed')], ['pct', L('Ordine: % debursat', 'Order: % disbursed')],
                 ['nume', L('Ordine: denumire', 'Order: name')], ['data', L('Ordine: data semnării', 'Order: date signed')]];
  var opt = function (lst, cur) { return lst.map(function (x) { return '<option value="' + x[0] + '"' + (cur === x[0] ? ' selected' : '') + '>' + esc(x[1]) + '</option>'; }).join(''); };
  var nSel = S.sel.length;
  var ce = nSel ? nSel + ' ' + (nSel === 1 ? L('donator', 'donor') : L('donatori', 'donors')) : L('toți donatorii', 'all donors');
  var insigna = '<span class="badge">' + esc(nSel ? String(nSel) : L('toți', 'all')) + '</span>';
  $('#sTool').innerHTML = '<div class="toolbar" role="search">' +
    '<input class="seek" id="q" type="search" autocomplete="off" value="' + esc(S.q) + '" placeholder="' + esc(L('Caută în proiecte: denumire, act, partener…', 'Search projects: name, act, partner…')) + '" aria-label="' + esc(L('Caută în proiecte', 'Search in projects')) + '">' +
    '<select class="sel" id="ftip" aria-label="' + esc(L('Tip de finanțare', 'Type of financing')) + '">' + tipuri + '</select>' +
    '<select class="sel" id="fdeb" aria-label="' + esc(L('Debursări', 'Disbursements')) + '">' + opt(debs, S.deb) + '</select>' +
    '<select class="sel" id="fsort" aria-label="' + esc(L('Ordinea proiectelor', 'Project order')) + '">' + opt(sorturi, S.sort) + '</select>' +
    '<span class="sp"></span>' +
    '<button type="button" class="btn" data-act="excel-total" title="' + esc(L('Un singur fișier: toate proiectele, rezumatul pe donatori și debursările (' + ce + ')', 'One file: all projects, the summary by donor and the disbursements (' + ce + ')')) + '">' +
      IC.xl + 'Excel · total' + insigna + '</button>' +
    '<button type="button" class="btn" data-act="excel-donatori" title="' + esc(L('Un fișier cu o foaie pentru fiecare donator (' + ce + ')', 'One file with a sheet for each donor (' + ce + ')')) + '">' +
      IC.xl + esc(L('Excel · pe donatori', 'Excel · by donor')) + insigna + '</button>' +
    '</div><div class="ferr" id="exErr" role="alert"></div>';
}

/* ------------------------------------------------------------------ randare: rezultatele (tabelele proiectelor) */
var CLASA_TIP = { 'Grant': 't-grant', 'Împrumut': 't-imprumut', 'Asistență tehnică': 't-tehnica' };
function textNuInTotal(stare) {
  return { dublura: L('nu intră în total: dublură', 'not in the total: duplicate'), fara_total: L('nu se adună în total', 'not added to the total'),
           fara_curs: L('fără curs de schimb', 'no exchange rate'), fara_suma: L('suma nu e cunoscută', 'amount not known') }[stare] || '';
}
function htmlSuma(a) {
  if (!a.suma) return '<span class="nil">—</span><div class="amt-sub nuadun">' + esc(L('suma nu e cunoscută', 'amount not known')) + '</div>';
  var s = a.suma, src = D.SURSE_SUMA[a.sursaSuma];
  var h = '<div class="amt">' + esc(fb(s.v)) + ' <span class="cur">' + esc(s.val) + '</span></div>';
  if (s.val !== 'EUR' && a.eur != null) h += '<div class="amt-sub">≈ ' + esc(fm(a.eur, 0)) + ' EUR</div>';
  if (a.inTotal !== 'numarat') h += '<div class="amt-sub nuadun">' + esc(textNuInTotal(a.inTotal)) + '</div>';
  if (src) h += '<div class="amt-sub"><span class="amt-src" title="' + esc(L('Sursa sumei', 'Source of the amount')) + '">' + esc(src[S.en ? 1 : 0]) + '</span></div>';
  return h;
}
function htmlDeb(a, g, k) {
  var h;
  if (S.debEroare) h = '<span class="nil">—</span>';
  else if (!g.n) h = '<span class="nil">—</span>';
  else {
    h = '<div class="amt">' + esc(fm(g.eur, 0)) + ' <span class="cur">EUR</span></div>';
    if (g.inVal != null && a.suma && a.suma.val !== 'EUR') h += '<div class="amt-sub">' + esc(fb(g.inVal)) + ' ' + esc(a.suma.val) + '</div>';
    if (g.pct != null) {
      h += '<div class="bar' + (g.pct > 1 ? ' peste' : '') + '"><i style="width:' + Math.min(100, g.pct * 100).toFixed(1) + '%"></i></div>' +
           '<div class="pct"><b>' + esc(fmPct(g.pct * 100)) + '%</b> ' + esc(L('din suma proiectului', 'of the project amount')) + '</div>';
    }
    h += '<div class="amt-sub">' + g.n + ' ' + (g.n === 1 ? L('debursare', 'disbursement') : L('debursări', 'disbursements')) + (g.ultima ? ' · ' + esc(L('ultima ', 'last ')) + esc(D.dataRo(g.ultima)) : '') + '</div>';
  }
  return h + '<div style="margin-top:7px"><button type="button" class="btn mic" data-act="adauga" aria-label="' + esc(L('Adaugă o debursare la ', 'Add a disbursement to ') + a.nume) + '">' +
    (cod ? IC.plus : IC.lock) + esc(L('Debursare', 'Disbursement')) + '</button></div>';
}
function htmlRand(d, a) {
  var g = ag(a), k = d.cheie + '|' + a.id, deschis = S.deschise.has(k);
  var cof = a.donatori.filter(function (x) { return x !== d.cheie; });
  var meta = [];
  if (a.stadiu) meta.push('<span class="stg ' + a.stadiu + '">' + esc(D.etichetaStadiu(a.stadiu, S.en)) + '</span>');
  if (a.semnat) meta.push(esc(L('semnat ', 'signed ') + a.semnat));
  if (cof.length) meta.push('<span class="cof">' + esc(L('cofinanțat cu ', 'co-financed with ') + cof.join(', ')) + '</span>');
  var desc = D.descriere(a, S.en);
  return '<tr class="ac' + (deschis ? ' deschis' : '') + '" data-k="' + esc(k) + '">' +
    '<td data-l="' + esc(L('Proiectul', 'Project')) + '"><div class="pname">' + esc(a.nume) + '</div><div class="pmeta">' + meta.join(' · ') + '</div></td>' +
    '<td data-l="' + esc(L('Descriere succintă', 'Short description')) + '"><div class="pdesc" title="' + esc(desc) + '">' + esc(desc) + '</div></td>' +
    '<td data-l="' + esc(L('Tip de finanțare', 'Type of financing')) + '"><span class="tag ' + (CLASA_TIP[a.categorie] || 't-alt') + '">' + esc(D.etichetaTip(a.categorie, S.en) || '—') + '</span></td>' +
    '<td class="num" data-l="' + esc(L('Suma proiectului', 'Project amount')) + '">' + htmlSuma(a) + '</td>' +
    '<td class="num" data-l="' + esc(L('Suma debursărilor', 'Disbursed amount')) + '">' + htmlDeb(a, g, k) + '</td>' +
    '<td class="act"><button type="button" class="exp" data-act="comuta" aria-expanded="' + (deschis ? 'true' : 'false') + '" aria-label="' +
      esc((deschis ? L('Închide detaliile: ', 'Close details: ') : L('Deschide detaliile: ', 'Open details: ')) + a.nume) + '">' + IC.chev + '</button></td></tr>' +
    (deschis ? htmlDetalii(d, a, g, k) : '');
}

/* rândul deschis: debursările introduse, formularul de adăugare și datele despre acord */
function optiuniValuta(sel, a) {
  var chei = Object.keys(S.baza.cursuri), ascunse = ['ECU', 'ROL', 'DEM'];
  var pref = [a && a.suma ? a.suma.val : null, 'EUR', 'USD'];
  var lista = [];
  pref.concat(chei.sort()).forEach(function (c) {
    if (!c || lista.indexOf(c) >= 0 || chei.indexOf(c) < 0) return;
    if (ascunse.indexOf(c) >= 0 && c !== sel && !(a && a.suma && a.suma.val === c)) return;
    lista.push(c);
  });
  if (sel && lista.indexOf(sel) < 0) lista.push(sel);
  return lista.map(function (c) { return '<option value="' + esc(c) + '"' + (c === sel ? ' selected' : '') + '>' + esc(c) + '</option>'; }).join('');
}
var TEXTE_EROARE = {
  data: { lipsa: ['Alege data debursării.', 'Choose the disbursement date.'], viitor: ['Data nu poate fi în viitor.', 'The date cannot be in the future.'], veche: ['Data e prea veche (înainte de 1990).', 'The date is too old (before 1990).'] },
  suma: { lipsa: ['Scrie suma.', 'Enter the amount.'], format: ['Nu înțeleg suma. Scrie, de exemplu, 1.250.000,50.', "I can't read the amount. Write, for example, 1,250,000.50."],
          zero: ['Suma trebuie să fie mai mare decât zero.', 'The amount must be greater than zero.'], mare: ['Suma e prea mare.', 'The amount is too large.'] },
  val: { valuta: ['Alege o valută cu curs de schimb cunoscut.', 'Choose a currency with a known exchange rate.'] },
  nota: { lunga: ['Nota are cel mult ' + D.MAX_NOTA + ' de caractere.', 'The note has at most ' + D.MAX_NOTA + ' characters.'] }
};
function textErori(er) {
  return Object.keys(er || {}).map(function (c) {
    var m = TEXTE_EROARE[c] && TEXTE_EROARE[c][er[c]];
    return m ? m[S.en ? 1 : 0] : '';
  }).filter(Boolean).join(' ');
}
function previzualizare(f) {
  var s = String(f.suma || '').trim();
  if (!s) return '';
  var v = D.parseSuma(s);
  if (!isFinite(v)) return '<span style="color:var(--red)">' + esc(L('Nu înțeleg suma. Scrie, de exemplu, 1.250.000,50', "I can't read the amount. Write, for example, 1,250,000.50")) + '</span>';
  var x = D.eurIntrare({ suma: v, val: f.val }, S.baza.cursuri);
  return esc(L('Se citește: ', 'Read as: ')) + '<b>' + esc(fb(v)) + ' ' + esc(f.val) + '</b>' + (f.val !== 'EUR' && x != null ? ' ≈ ' + esc(fm(x, 0)) + ' EUR' : '');
}
function formDe(a) {
  return S.f[a.id] || (S.f[a.id] = { data: D.aziIso(), suma: '', val: a.suma ? a.suma.val : 'EUR', nota: '' });
}
function htmlForm(a, k) {
  var bl = !cod, f = formDe(a), er = S.fe[a.id] || {}, dis = bl ? ' disabled' : '';
  var inv = function (n) { return er[n] ? ' aria-invalid="true"' : ''; };
  var fk = function (n) { return ' data-fk="' + esc(k + '|' + n) + '"'; };
  return '<h3>' + esc(L('Adaugă o debursare', 'Add a disbursement')) + '</h3>' +
    '<form class="deb-form" data-k="' + esc(k) + '" data-a="' + esc(a.id) + '" novalidate>' +
    (bl ? '<div class="blocat">' + IC.lock + '<span>' + esc(L('Câmpurile sunt blocate. Introdu codul de acces ca să poți adăuga debursări.', 'The fields are locked. Enter the access code to add disbursements.')) +
          '</span><button type="button" class="btn mic p" data-act="unlock">' + esc(L('Introdu codul', 'Enter the code')) + '</button></div>' : '') +
    '<label>' + esc(L('Data debursării', 'Disbursement date')) + '<input type="date" name="data"' + fk('data') + ' value="' + esc(f.data) + '" min="1990-01-01" max="' + D.aziIso() + '"' + dis + inv('data') + '></label>' +
    '<label>' + esc(L('Valuta', 'Currency')) + '<select name="val"' + fk('val') + dis + inv('val') + '>' + optiuniValuta(f.val, a) + '</select></label>' +
    '<label class="w">' + esc(L('Suma debursată', 'Disbursed amount')) + '<input type="text" name="suma" inputmode="decimal" autocomplete="off" placeholder="1.250.000,50"' + fk('suma') + ' value="' + esc(f.suma) + '"' + dis + inv('suma') + '></label>' +
    '<label class="w">' + esc(L('Notă (opțional)', 'Note (optional)')) + '<input type="text" name="nota" maxlength="' + D.MAX_NOTA + '" autocomplete="off" placeholder="' + esc(L('de pildă: tranșa a doua, cererea de retragere nr. 4', 'for example: second tranche, withdrawal request no. 4')) + '"' + fk('nota') + ' value="' + esc(f.nota) + '"' + dis + '></label>' +
    '<div class="full prev" aria-live="polite">' + previzualizare(f) + '</div>' +
    '<div class="full ferr" role="alert">' + esc(textErori(er)) + '</div>' +
    '<div class="full"><button type="submit" class="btn p"' + dis + '>' + IC.plus + esc(L('Adaugă debursarea', 'Add the disbursement')) + '</button></div></form>';
}
function acteIntrare(e, faraEditare) {
  if (!cod) return '';
  if (S.conf === e.id) {
    return '<span class="cof">' + esc(L('Sigur?', 'Sure?')) + '</span> <button type="button" class="btn mic rosu" data-act="del-da" data-id="' + esc(e.id) + '">' + esc(L('Șterge', 'Delete')) + '</button> ' +
           '<button type="button" class="btn mic" data-act="del-nu">' + esc(L('Nu', 'No')) + '</button>';
  }
  return (faraEditare ? '' : '<button type="button" class="btn mic" data-act="ed" data-id="' + esc(e.id) + '" aria-label="' + esc(L('Editează debursarea din ', 'Edit the disbursement of ') + D.dataRo(e.data)) + '" title="' + esc(L('Editează', 'Edit')) + '">' + IC.edit + '</button> ') +
         '<button type="button" class="btn mic" data-act="del" data-id="' + esc(e.id) + '" aria-label="' + esc(L('Șterge debursarea din ', 'Delete the disbursement of ') + D.dataRo(e.data)) + '" title="' + esc(L('Șterge', 'Delete')) + '">' + IC.trash + '</button>';
}
function rowIntrare(e) {
  var x = D.eurIntrare(e, S.baza.cursuri), pend = S.nesalvate.has(e.id), conf = S.conf === e.id;
  return '<tr' + (conf ? ' class="conf"' : '') + '><td>' + esc(D.dataRo(e.data)) + (pend ? '<span class="nes">' + esc(L('nesalvat', 'unsaved')) + '</span>' : '') + '</td>' +
    '<td class="num">' + esc(fb(e.suma)) + ' ' + esc(e.val) + '</td><td class="num">' + (x == null ? '—' : esc(fm(x, 0))) + '</td>' +
    '<td class="nota">' + esc(e.nota || '') + '</td><td class="ea">' + acteIntrare(e) + '</td></tr>';
}
function rowEditare(a, e) {
  var f = S.ed.f, er = S.ed.fe || {};
  var inv = function (n) { return er[n] ? ' aria-invalid="true"' : ''; };
  var fk = function (n) { return ' data-fk="' + esc('ed|' + n) + '"'; };
  return '<tr class="ed"><td><input type="date" data-ed="data"' + fk('data') + ' value="' + esc(f.data) + '" min="1990-01-01" max="' + D.aziIso() + '" aria-label="' + esc(L('Data', 'Date')) + '"' + inv('data') + '></td>' +
    '<td><input type="text" inputmode="decimal" autocomplete="off" data-ed="suma"' + fk('suma') + ' value="' + esc(f.suma) + '" aria-label="' + esc(L('Suma', 'Amount')) + '"' + inv('suma') + '>' +
    '<select data-ed="val"' + fk('val') + ' aria-label="' + esc(L('Valuta', 'Currency')) + '"' + inv('val') + '>' + optiuniValuta(f.val, a) + '</select></td>' +
    '<td class="num">—</td>' +
    '<td><input type="text" autocomplete="off" maxlength="' + D.MAX_NOTA + '" data-ed="nota"' + fk('nota') + ' value="' + esc(f.nota) + '" aria-label="' + esc(L('Notă', 'Note')) + '"></td>' +
    '<td class="ea"><button type="button" class="btn mic p" data-act="ed-salveaza">' + esc(L('Salvează', 'Save')) + '</button> <button type="button" class="btn mic" data-act="ed-anuleaza">' + esc(L('Anulează', 'Cancel')) + '</button></td></tr>' +
    (Object.keys(er).length ? '<tr class="ed"><td colspan="5" class="ferr" role="alert">' + esc(textErori(er)) + '</td></tr>' : '');
}
function htmlIntrari(a, intrari, g) {
  var h = '<h3>' + esc(L('Debursări introduse', 'Disbursements entered')) + ' (' + intrari.length + ')</h3>';
  if (!intrari.length) return h + '<div class="nimic">' + esc(L('Nicio debursare introdusă pentru acest proiect.', 'No disbursement has been entered for this project.')) + '</div>';
  var rows = intrari.map(function (e) { return S.ed && S.ed.id === e.id ? rowEditare(a, e) : rowIntrare(e); }).join('');
  return h + '<table class="deb-ent"><thead><tr><th>' + esc(L('Data', 'Date')) + '</th><th class="num">' + esc(L('Suma', 'Amount')) + '</th><th class="num">≈ EUR</th><th>' + esc(L('Notă', 'Note')) + '</th><th></th></tr></thead>' +
    '<tbody>' + rows + '</tbody><tfoot><tr><td>' + esc(L('Total', 'Total')) + '</td><td class="num">' + (g.inVal != null ? esc(fb(g.inVal)) + ' ' + esc(g.valuta) : '') + '</td>' +
    '<td class="num">' + esc(fm(g.eur, 0)) + '</td><td colspan="2"></td></tr></tfoot></table>';
}
function htmlInfo(a) {
  var acte = a.acte.map(function (x) {
    var t = esc(x.act) + (x.data ? ' · ' + esc(x.data) : '');
    return x.url ? '<a href="' + esc(x.url) + '" target="_blank" rel="noopener" title="' + esc(x.tip + (x.data ? ', ' + x.data : '')) + '">' + t + '</a>' : '<span>' + t + '</span>';
  }).join('');
  var src = a.suma ? D.SURSE_SUMA[a.sursaSuma] : null;
  var inTotal = { numarat: L('da', 'yes'), dublura: L('nu: dublură a altui acord', 'no: duplicate of another agreement'), fara_total: L('nu: nu se adună în total', 'no: not added to the total'),
                  fara_curs: L('nu: fără curs de schimb', 'no: no exchange rate'), fara_suma: L('nu: suma nu e cunoscută', 'no: amount not known') }[a.inTotal] || '';
  var dl = [];
  if (a.numeComplet) dl.push([L('Titlul acordului', 'Agreement title'), esc(a.numeComplet)]);
  dl.push([L('Parteneri', 'Partners'), esc(a.parteneriText || '—')]);
  dl.push([L('Acte', 'Acts'), '<span class="acte">' + (acte || '—') + '</span>']);
  if (a.suma) dl.push([L('Suma', 'Amount'), esc(fb(a.suma.v) + ' ' + a.suma.val) + (src ? ' · ' + esc(src[S.en ? 1 : 0]) : '') + (a.actSuma ? ' (' + esc(a.actSuma) + ')' : '')]);
  dl.push([L('Intră în totaluri', 'Counted in totals'), esc(inTotal)]);
  return '<div class="det-info"><dl>' + dl.map(function (x) { return '<dt>' + esc(x[0]) + '</dt><dd>' + x[1] + '</dd>'; }).join('') + '</dl></div>';
}
function htmlDetalii(d, a, g, k) {
  var intrari = S.peAcord.get(a.id) || [];
  return '<tr class="det" data-k="' + esc(k) + '"><td colspan="6"><div class="det-grid"><div>' + htmlIntrari(a, intrari, g) + '</div><div>' + htmlForm(a, k) + '</div>' + htmlInfo(a) + '</div></td></tr>';
}

function htmlPanou(d) {
  var lista = filtrate(d.acorduri), r = D.rezumat(lista, S.peAcord, S.baza.cursuri), nume = D.numeDonator(d.cheie, S.en);
  var total = d.acorduri.length;
  var dsum = '<div class="dsum"><span><b>' + lista.length + '</b> ' + (lista.length === total ? L('proiecte', 'projects') : L('proiecte din ', 'projects of ') + total) + '</span>' +
    '<span>' + esc(L('suma ', 'amount ')) + '<b>' + esc(fEur(r.sumaEur)) + '</b></span>' +
    (S.debEroare ? '' : '<span>' + esc(L('debursat ', 'disbursed ')) + '<b>' + esc(fEur(r.debEur)) + '</b>' + (r.pct != null ? ' (' + esc(fmPct(r.pct * 100)) + '%)' : '') + '</span>') + '</div>';
  var corp;
  if (!lista.length) {
    corp = '<div class="gol-msg"><b>' + esc(L('Niciun proiect nu corespunde filtrelor.', 'No project matches the filters.')) + '</b>' + esc(L('Acest donator are ' + total + ' proiecte în total.', 'This donor has ' + total + ' projects in total.')) +
      '<div class="chips"><button type="button" class="chip" data-act="sterge-filtre">' + esc(L('Șterge filtrele', 'Clear filters')) + '</button></div></div>';
  } else {
    corp = '<div class="tbl-scroll"><table class="deb-tbl"><thead><tr><th>' + esc(L('Proiectul', 'Project')) + '</th><th>' + esc(L('Descriere succintă', 'Short description')) + '</th><th>' + esc(L('Tip de finanțare', 'Type of financing')) +
      '</th><th class="num">' + esc(L('Suma proiectului', 'Project amount')) + '</th><th class="num">' + esc(L('Suma debursărilor', 'Disbursed amount')) + '</th><th><span class="vh">' + esc(L('Detalii', 'Details')) + '</span></th></tr></thead><tbody>' +
      lista.map(function (a) { return htmlRand(d, a); }).join('') + '</tbody></table></div>';
  }
  return '<section class="panel" data-d="' + esc(d.cheie) + '" aria-label="' + esc(d.cheie) + '"><div class="panel-head"><div><h2>' + esc(d.cheie) + (nume !== d.cheie ? ' <small>' + esc(nume) + '</small>' : '') + '</h2>' + dsum + '</div>' +
    '<div class="head-btns"><button type="button" class="btn" data-act="excel-donator" data-d="' + esc(d.cheie) + '"' + (lista.length ? '' : ' disabled') + '>' + IC.xl + 'Excel · ' + esc(D.taie(d.cheie, 24)) + '</button>' +
    '<button type="button" class="btn" data-act="scoate" data-d="' + esc(d.cheie) + '" aria-label="' + esc(L('Scoate donatorul ' + d.cheie + ' din selecție', 'Remove donor ' + d.cheie + ' from the selection')) + '" title="' + esc(L('Scoate din selecție', 'Remove from selection')) + '">' + IC.x + '</button></div></div>' + corp + '</section>';
}
function htmlGol() {
  var top = D.ordoneazaDonatori(S.baza.donatori.filter(function (d) { return d.cheie !== D.NEIDENTIFICAT; }), 'n', S.peAcord, S.baza.cursuri, S.en).slice(0, 6);
  return '<div class="panel"><div class="gol-msg"><b>' + esc(L('Alege un donator din listă', 'Choose a donor from the list')) + '</b>' +
    esc(L('Proiectele lui apar aici, cu suma fiecăruia și cu debursările introduse. Poți bifa mai mulți donatori deodată.', 'Its projects appear here, with each amount and the disbursements entered. You can tick several donors at once.')) +
    '<div class="chips">' + top.map(function (d) { return '<button type="button" class="chip" data-act="alege" data-d="' + esc(d.cheie) + '">' + esc(d.cheie) + '</button>'; }).join('') + '</div></div></div>';
}
function randeazaRez() {
  var el = $('#sRez');
  if (!S.baza) {
    el.innerHTML = S.faza === 'eroare'
      ? '<div class="panel"><div class="eroare-mare"><b>' + esc(L('Nu pot citi acordurile', 'Cannot read the agreements')) + '</b>' + esc(L('Fișierul cu acordurile nu s-a încărcat. Verifică conexiunea și încearcă din nou.', 'The agreements file did not load. Check your connection and try again.')) +
        '<div class="chips"><button type="button" class="chip" data-act="reincarca">' + esc(L('Încearcă din nou', 'Try again')) + '</button></div></div></div>'
      : '<div class="panel"><div class="gol-msg">' + esc(L('Se încarcă acordurile din registru…', 'Loading the agreements from the register…')) + '</div></div>';
    return;
  }
  pastreazaFocus(function () {
    el.innerHTML = S.sel.length ? donatoriAlesi().map(htmlPanou).join('') : htmlGol();
  });
}
function randeazaOrfane() {
  var el = $('#sOrfane');
  if (!S.baza || !S.orfane.length) { el.innerHTML = ''; return; }
  var rows = S.orfane.map(function (e) { return '<tr' + (S.conf === e.id ? ' class="conf"' : '') + '><td>' + esc(D.dataRo(e.data)) + (S.nesalvate.has(e.id) ? '<span class="nes">' + esc(L('nesalvat', 'unsaved')) + '</span>' : '') + '</td><td>' + esc(e.nume || e.acord) + '</td>' +
    '<td class="num">' + esc(fb(e.suma)) + ' ' + esc(e.val) + '</td><td class="nota">' + esc(e.nota || '') + '</td><td class="ea">' + acteIntrare(e, true) + '</td></tr>'; }).join('');
  el.innerHTML = '<section class="panel"><div class="panel-head"><h2>' + esc(L('Debursări fără acord în registru', 'Disbursements without an agreement in the register')) + ' <small>' + S.orfane.length + '</small></h2></div><div class="panel-body">' +
    '<p style="margin:0 0 10px;font-size:12.5px;color:var(--ink-dim)">' + esc(L('Au fost introduse pentru acorduri care nu se mai găsesc în registru (de pildă, acordul a fost unit cu altul sau scos). Nu intră în totalurile pe donatori, dar rămân în fișierul de date și în Excel · total.',
      'They were entered for agreements that are no longer in the register (for example, the agreement was merged with another or removed). They are not counted in the donor totals, but stay in the data file and in Excel · total.')) + '</p>' +
    '<table class="deb-ent"><thead><tr><th>' + esc(L('Data', 'Date')) + '</th><th>' + esc(L('Proiectul', 'Project')) + '</th><th class="num">' + esc(L('Suma', 'Amount')) + '</th><th>' + esc(L('Notă', 'Note')) + '</th><th></th></tr></thead><tbody>' + rows + '</tbody></table></div></section>';
}
function randeazaNote() {
  var el = $('#sNote');
  if (!S.baza) { el.innerHTML = ''; return; }
  var p = [
    [L('De unde vin cifrele. ', 'Where the figures come from. '),
     L('Proiectele sunt acordurile din registrul legis.md (un rând adună toate actele aceluiași acord). „Suma proiectului” e suma acordului, așa cum o arată registrul; echivalentul în euro folosește cursurile BCE din ' + cursData() +
       '. Un acord finanțat de mai mulți parteneri apare la fiecare dintre ei, dar în totaluri e numărat o singură dată.',
       'The projects are the agreements from the legis.md register (one row combines all acts of the same agreement). "Project amount" is the agreement amount as the register shows it; the euro equivalent uses the ECB rates of ' + cursData() +
       '. An agreement financed by several partners appears under each of them, but is counted once in the totals.')],
    [L('Debursările ', 'Disbursements '),
     L('nu vin dintr-o sursă oficială: se introduc de mână și se păstrează în fișierul date/debursari.json din repository-ul site-ului. Oricine poate citi fișierul; scrie doar cine are codul de acces. Fiecare salvare e un commit, așa că istoricul modificărilor se vede în GitHub și o greșeală se poate anula.',
       'do not come from an official source: they are entered by hand and kept in the date/debursari.json file in the site repository. Anyone can read the file; only the holder of the access code can write. Every save is a commit, so the history of changes is visible on GitHub and a mistake can be undone.')],
    [L('Procentul debursat ', 'The disbursed percentage '),
     L('compară debursările la proiectele cu sumă (cele care intră în total) cu suma lor. Debursările la proiecte fără sumă apar în „Debursat”, dar nu în procent.',
       'compares the disbursements on projects with an amount (those counted in the total) with their amount. Disbursements on projects without an amount appear in "Disbursed" but not in the percentage.')]
  ];
  el.innerHTML = '<div class="note">' + p.map(function (x) { return '<p><b>' + esc(x[0]) + '</b>' + esc(x[1]) + '</p>'; }).join('') +
    '<p><button type="button" class="lnk" data-act="json">' + esc(L('Descarcă o copie a debursărilor (JSON)', 'Download a copy of the disbursements (JSON)')) + '</button>' +
    (areSeif() ? ' · <button type="button" class="lnk" data-act="uita-seif">' + esc(L('Uită codul păstrat pe acest dispozitiv', 'Forget the code kept on this device')) + '</button>' : '') + '</p></div>';
}
function randeazaNav() {
  $('#sNav').innerHTML = '<a href="index.html">' + esc(L('← Donatori și proiecte', '← Donors & projects')) + '</a><a href="legis_acorduri.html">' + esc(L('Acorduri · legis.md', 'Agreements · legis.md')) + '</a>' +
    '<a href="acorduri.html">' + esc(L('Acorduri · Monitorul Oficial', 'Agreements · Official Gazette')) + '</a><a href="index.html#legaturi">' + esc(L('De la lege la bani', 'From law to money')) + '</a>' +
    '<a href="#">' + esc(L('↑ Începutul paginii', '↑ Top of the page')) + '</a><a href="despre.html">' + esc(L('Despre date', 'About the data')) + '</a>';
}
function randeazaTot() {
  randeazaCap(); randeazaAcces(); randeazaKpi(); randeazaPicker(); randeazaTool(); randeazaRez(); randeazaOrfane(); randeazaNote(); randeazaNav();
  if (dlgDeschis()) randeazaDialog();
}
function dupaDate() {
  randeazaCap(); randeazaAcces(); randeazaKpi(); randeazaLista(); randeazaRez(); randeazaOrfane(); randeazaNote();
}

/* păstrează focusul (și poziția cursorului) când se refac tabelele */
function pastreazaFocus(fn) {
  var el = document.activeElement, fk = null, s = null, e = null;
  if (el && el !== document.body && RAD.contains(el) && el.getAttribute) {
    fk = el.getAttribute('data-fk');
    try { s = el.selectionStart; e = el.selectionEnd; } catch (x) { /* nu toate câmpurile au selecție */ }
  }
  fn();
  if (fk) {
    var n = RAD.querySelector('[data-fk="' + qs(fk) + '"]');
    if (n && !n.disabled) {
      n.focus();
      try { if (s != null && e != null) n.setSelectionRange(s, e); } catch (x) { /* ignorat */ }
    }
  }
}
function refaRand(k) {
  var tr = RAD.querySelector('tr.ac[data-k="' + qs(k) + '"]');
  if (!tr) { randeazaRez(); return; }
  var i = k.indexOf('|'), d = S.baza.donatori.filter(function (x) { return x.cheie === k.slice(0, i); })[0], a = S.baza.peId.get(k.slice(i + 1));
  if (!d || !a) { randeazaRez(); return; }
  pastreazaFocus(function () {
    var urm = tr.nextElementSibling;
    if (urm && urm.classList.contains('det')) urm.parentNode.removeChild(urm);
    var tmp = document.createElement('tbody');
    tmp.innerHTML = htmlRand(d, a);
    while (tmp.firstChild) tr.parentNode.insertBefore(tmp.firstChild, tr);
    tr.parentNode.removeChild(tr);
  });
}

/* ------------------------------------------------------------------ acțiuni: selecție, filtre, rânduri */
function comutaDonator(cheie, pornit) {
  var i = S.sel.indexOf(cheie), eraGol = !S.sel.length;
  if (pornit && i < 0) S.sel.push(cheie); else if (!pornit && i >= 0) S.sel.splice(i, 1);
  dupaSelectie();
  if (eraGol && S.sel.length) deruleazaLaRezultate();
}
/* Pe ecran îngust, tabelele sunt sub lista donatorilor: la prima bifare omul trebuie dus la ele, altfel pare că nu s-a întâmplat nimic. */
function deruleazaLaRezultate() {
  if (!window.matchMedia || !matchMedia('(max-width:1100px)').matches) return;
  setTimeout(function () {
    var p = $('#sRez .panel[data-d]');
    if (!p) return;
    var r = p.getBoundingClientRect();
    if (r.top > window.innerHeight * 0.6 || r.top < 0) p.scrollIntoView({ behavior: matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth', block: 'start' });
  }, 60);
}
function dupaSelectie() {
  scrieHash(); randeazaKpi(); randeazaTool(); randeazaRez();
  contorDonatori(donatoriAfisati().length);
  document.querySelectorAll('#donLista .don').forEach(function (l) {
    var i = l.querySelector('input'), on = S.sel.indexOf(i.getAttribute('data-d')) >= 0;
    i.checked = on; l.classList.toggle('on', on);
  });
}
function dupaFiltre() { scrieHash(); randeazaRez(); }
function comutaRand(k) {
  if (S.deschise.has(k)) S.deschise.delete(k); else S.deschise.add(k);
  refaRand(k);
}
function deschideRand(k) {
  if (!S.deschise.has(k)) { S.deschise.add(k); refaRand(k); }
}
function focuseazaFormular(k) {
  var n = RAD.querySelector('[data-fk="' + qs(k + '|suma') + '"]');
  if (n && !n.disabled) { n.focus(); return; }
  var f = RAD.querySelector('tr.det[data-k="' + qs(k) + '"] [data-act="unlock"]');
  if (f) f.focus();
}

/* ------------------------------------------------------------------ operații asupra debursărilor și salvarea lor */
function mesajCommit(ops) {
  var descr = function (o) {
    if (o.t === 'del') return 'șters: ' + D.taie(o.nume || o.id, 70);
    var e = o.e;
    return (o.t === 'add' ? 'adăugat: ' : 'modificat: ') + D.taie(e.nume || e.acord, 70) + ' — ' + D.fmtBani(e.suma, false) + ' ' + e.val + ' (' + e.data + ')';
  };
  return 'Debursări: ' + (ops.length === 1 ? descr(ops[0]) : ops.length + ' modificări');
}
function operatie(op) {
  S.coada.push(op); scrieCoada(); recalc();
  dupaDate();
  trimite();
}
function trimite() {
  if (S.ocupat || !cod || !S.coada.length) return Promise.resolve();
  S.ocupat = true; S.eroareSalv = null; randeazaAcces();
  var lot = S.coada.slice();
  return dep.salveaza(cod, lot, mesajCommit(lot)).then(function (r) {
    S.coada.splice(0, lot.length);
    S.serv = r.date; S.dinMemorie = false; S.ultimaSalv = D.dataOraRo();
    scrieCoada(); pastreazaRecent();
    S.ocupat = false;
    recalc(); dupaDate();
    live(L('Modificările au fost salvate.', 'The changes were saved.'));
    return S.coada.length ? trimite() : null;
  }, function (e) {
    S.ocupat = false; S.eroareSalv = e;
    if (e && (e.cod === 'token' || e.cod === 'drept')) cod = null;      // codul nu mai e bun: se blochează; modificările rămân în coadă
    randeazaAcces(); randeazaRez();
    live(msgEroare(e));
  });
}
function adauga(form) {
  var id = form.getAttribute('data-a'), k = form.getAttribute('data-k'), a = S.baza.peId.get(id);
  if (!a || !cod) return;
  var f = S.f[id] || {}, v = D.valideazaFormular(f, S.baza.cursuri);
  if (!v.ok) {
    S.fe[id] = v.erori; refaRand(k);
    var ordine = ['data', 'val', 'suma', 'nota'], prima = ordine.filter(function (c) { return v.erori[c]; })[0];
    var n = RAD.querySelector('[data-fk="' + qs(k + '|' + prima) + '"]'); if (n) n.focus();
    live(textErori(v.erori));
    return;
  }
  S.fe[id] = null;
  var e = D.intrareDin(a, v.valoare);
  S.f[id] = { data: f.data, val: f.val, suma: '', nota: '' };
  operatie({ t: 'add', e: e });
  live(L('Debursare adăugată: ', 'Disbursement added: ') + fb(e.suma) + ' ' + e.val + '.');
  focuseazaFormular(k);
}
function pornesteEditare(id) {
  var e = S.intrari.filter(function (x) { return x.id === id; })[0];
  if (!e) return;
  S.conf = null;
  S.ed = { id: id, f: { data: e.data, suma: fb(e.suma), val: e.val, nota: e.nota || '' }, fe: {} };
  randeazaRez();
  var n = RAD.querySelector('[data-fk="ed|suma"]'); if (n) n.focus();
}
function salveazaEditare() {
  if (!S.ed || !cod) return;
  var vechi = S.intrari.filter(function (x) { return x.id === S.ed.id; })[0];
  if (!vechi) { S.ed = null; randeazaRez(); return; }
  var v = D.valideazaFormular(S.ed.f, S.baza.cursuri);
  if (!v.ok) {
    S.ed.fe = v.erori; randeazaRez();
    var prima = ['data', 'val', 'suma', 'nota'].filter(function (c) { return v.erori[c]; })[0];
    var n = RAD.querySelector('[data-fk="ed|' + prima + '"]'); if (n) n.focus();
    return;
  }
  var nou = Object.assign({}, vechi, { data: v.valoare.data, suma: Math.round(v.valoare.suma * 100) / 100, val: v.valoare.val, nota: v.valoare.nota });
  S.ed = null;
  operatie({ t: 'upd', e: nou });
  live(L('Debursarea a fost modificată.', 'The disbursement was changed.'));
}
function sterge(id) {
  var e = S.intrari.filter(function (x) { return x.id === id; })[0];
  S.conf = null;
  operatie({ t: 'del', id: id, nume: e ? e.nume : '' });
  live(L('Debursarea a fost ștearsă.', 'The disbursement was deleted.'));
}

/* ------------------------------------------------------------------ fereastra cu codul de acces */
function dlgDeschis() { var d = $('#dlg'); return !!(d && d.open); }
function randeazaDialog() {
  var d = $('#dlg'), seif = areSeif(), pin = S.dlg.mod === 'pin' && seif, h;
  var eroare = '<div class="ferr" id="dErr" role="alert">' + esc(S.dlg.eroare) + '</div>';
  var ajutor = '<details><summary>' + esc(L('Cum obțin codul?', 'How do I get the code?')) + '</summary><ol>' +
    '<li>' + esc(L('Deschide pagina de creare a unui „fine-grained personal access token” pe GitHub (butonul de mai jos completează o parte din câmpuri).', 'Open the page for creating a fine-grained personal access token on GitHub (the button below fills in some of the fields).')) + '</li>' +
    '<li>' + esc(L('La „Repository access” alege „Only select repositories” și bifează doar „acorduri”.', 'Under "Repository access" choose "Only select repositories" and tick only "acorduri".')) + '</li>' +
    '<li>' + esc(L('La „Permissions → Repository permissions” pune „Contents” pe „Read and write”. Nimic altceva.', 'Under "Permissions → Repository permissions" set "Contents" to "Read and write". Nothing else.')) + '</li>' +
    '<li>' + esc(L('Apasă „Generate token” și copiază codul (începe cu github_pat_). Se arată o singură dată.', 'Press "Generate token" and copy the code (it starts with github_pat_). It is shown only once.')) + '</li>' +
    '<li>' + esc(L('Lipește-l aici. Nu-l pune în niciun fișier sau pagină și șterge-l din GitHub când nu mai ai nevoie de el.', 'Paste it here. Do not put it in any file or page, and delete it on GitHub when you no longer need it.')) + '</li></ol>' +
    '<p style="margin:10px 0 0"><a class="btn" href="' + esc(URL_COD) + '" target="_blank" rel="noopener">' + esc(L('Deschide GitHub', 'Open GitHub')) + '</a></p></details>';
  if (pin) {
    h = '<div class="dlg-in"><h2 id="dlgTitlu">' + esc(L('Deblochează cu PIN', 'Unlock with PIN')) + '</h2>' +
      '<p>' + esc(L('Pe acest dispozitiv e păstrat un cod de acces, criptat. Scrie PIN-ul ales atunci.', 'An access code is kept on this device, encrypted. Enter the PIN you chose then.')) + '</p>' +
      '<form id="fPin" novalidate autocomplete="off"><label for="inPin">PIN</label><input id="inPin" type="password" autocomplete="off" spellcheck="false">' + eroare +
      '<div class="acte-dlg"><button type="button" class="btn" data-dlg="alt-cod">' + esc(L('Folosesc alt cod', 'Use another code')) + '</button><button type="button" class="btn" data-dlg="inchide">' + esc(L('Renunță', 'Cancel')) + '</button>' +
      '<button type="submit" class="btn p" id="bOk"' + (S.dlg.ocupat ? ' disabled' : '') + '>' + esc(S.dlg.ocupat ? L('Se verifică…', 'Checking…') : L('Deblochează', 'Unlock')) + '</button></div></form></div>';
  } else {
    h = '<div class="dlg-in"><h2 id="dlgTitlu">' + esc(L('Introdu codul de acces', 'Enter the access code')) + '</h2>' +
      '<p>' + esc(L('Codul deblochează câmpurile în care se introduc debursările. E o cheie GitHub cu drept de scriere doar în acest repository; rămâne în memoria paginii și nu pleacă decât către GitHub.',
                    'The code unlocks the fields where disbursements are entered. It is a GitHub key with write access to this repository only; it stays in the page memory and goes nowhere except GitHub.')) + '</p>' +
      '<form id="fCod" novalidate autocomplete="off"><label for="inCod">' + esc(L('Cod de acces', 'Access code')) + '</label>' +
      '<input id="inCod" type="password" autocomplete="off" spellcheck="false" autocapitalize="off" autocorrect="off" placeholder="github_pat_…">' +
      (D.Seif.disponibil() ? '<label class="rand"><input type="checkbox" id="inTine"' + (S.dlg.tine ? ' checked' : '') + '>' + esc(L('Ține minte codul pe acest dispozitiv, protejat cu un PIN', 'Remember the code on this device, protected by a PIN')) + '</label>' +
        '<div id="rPin"' + (S.dlg.tine ? '' : ' hidden') + '><label for="inPin">' + esc(L('PIN nou (cel puțin ' + D.LUNGIME_MIN_PIN + ' caractere)', 'New PIN (at least ' + D.LUNGIME_MIN_PIN + ' characters)')) + '</label><input id="inPin" type="password" autocomplete="new-password" spellcheck="false"></div>' : '') +
      eroare + '<div class="acte-dlg">' + (seif ? '<button type="button" class="btn" data-dlg="cu-pin">' + esc(L('Am PIN', 'I have a PIN')) + '</button>' : '') +
      '<button type="button" class="btn" data-dlg="inchide">' + esc(L('Renunță', 'Cancel')) + '</button><button type="submit" class="btn p" id="bOk"' + (S.dlg.ocupat ? ' disabled' : '') + '>' + esc(S.dlg.ocupat ? L('Se verifică…', 'Checking…') : L('Deblochează', 'Unlock')) + '</button></div></form>' + ajutor + '</div>';
  }
  d.innerHTML = h;
}
function deschideDialog() {
  var d = $('#dlg');
  S.dlg = { mod: areSeif() ? 'pin' : 'cod', eroare: '', ocupat: false, tine: false };
  randeazaDialog();
  if (typeof d.showModal === 'function') { if (!d.open) d.showModal(); } else d.setAttribute('open', '');
  var n = $('#inPin', d) || $('#inCod', d);
  if (n) n.focus();
}
function inchideDialog() {
  var d = $('#dlg');
  if (!d) return;
  if (typeof d.close === 'function' && d.open) d.close(); else d.removeAttribute('open');
  d.innerHTML = '';
}
function eroareDialog(e) {
  S.dlg.ocupat = false; S.dlg.eroare = typeof e === 'string' ? e : msgEroare(e);
  randeazaDialog();
  var n = $('#inPin', $('#dlg')) || $('#inCod', $('#dlg'));
  if (n) n.focus();
}
function deblocheaza(token) {
  return dep.verifica(token).then(function () { return dep.citeste(token); }).then(function (cur) {
    cod = token; S.serv = cur.date; S.dinMemorie = false; S.debEroare = null; S.eroareSalv = null;
    recalc(); pastreazaRecent();
  });
}
function trimiteDialog() {
  var d = $('#dlg');
  if (S.dlg.ocupat) return;
  if (S.dlg.mod === 'pin' && areSeif()) {
    var p = $('#inPin', d).value;
    if (!p) { eroareDialog(L('Scrie PIN-ul.', 'Enter the PIN.')); return; }
    S.dlg.ocupat = true; marcheazaOcupat();
    var obj = areSeif(), deschis;
    try { deschis = D.Seif.deschide(obj, p); } catch (e) { deschis = Promise.reject(e); }
    deschis.then(function (t) { return deblocheaza(t); }).then(reusitaDeblocare, eroareDialog);
    return;
  }
  var token = $('#inCod', d).value.trim();
  if (!token) { eroareDialog(L('Scrie codul de acces.', 'Enter the access code.')); return; }
  if (!/^[\x21-\x7e]{20,255}$/.test(token)) {
    eroareDialog(L('Codul nu arată ca o cheie GitHub: n-ar trebui să aibă spații sau litere cu diacritice. Copiază-l din nou, întreg.',
                   'The code does not look like a GitHub key: it should have no spaces or accented letters. Copy it again, in full.'));
    return;
  }
  var ct = $('#inTine', d), tine = !!(ct && ct.checked), pinNou = '';
  if (tine) {
    pinNou = $('#inPin', d).value;
    if (pinNou.length < D.LUNGIME_MIN_PIN) { eroareDialog(L('PIN-ul trebuie să aibă cel puțin ' + D.LUNGIME_MIN_PIN + ' caractere.', 'The PIN must have at least ' + D.LUNGIME_MIN_PIN + ' characters.')); return; }
  }
  S.dlg.tine = tine; S.dlg.ocupat = true; marcheazaOcupat();
  deblocheaza(token).then(function () {
    if (!tine) return null;
    return D.Seif.impacheteaza(token, pinNou).then(function (obj) { lsSet(CH_SEIF, JSON.stringify(obj)); },
      function () { live(L('Nu am putut păstra codul pe acest dispozitiv; rămâne deblocat doar cât ține pagina deschisă.', 'Could not keep the code on this device; it stays unlocked only while the page is open.')); });
  }).then(reusitaDeblocare, eroareDialog);
}
function marcheazaOcupat() {                    // butonul arată că se verifică, fără să refacă dialogul (ca să nu se piardă ce a scris omul)
  var d = $('#dlg'), ok = $('#bOk', d);
  if (ok) { ok.disabled = true; ok.textContent = L('Se verifică…', 'Checking…'); }
  var er = $('#dErr', d); if (er) er.textContent = '';
}
function reusitaDeblocare() {
  inchideDialog();
  S.dlg = { mod: 'cod', eroare: '', ocupat: false, tine: false };
  randeazaTot();
  live(L('Câmpurile de debursare sunt deblocate.', 'The disbursement fields are unlocked.'));
  if (S.coada.length) trimite();
}

/* ------------------------------------------------------------------ Excel */
var incarcareStil = null;
function incarcaStil() {
  if (window.XlsxStil) return Promise.resolve(window.XlsxStil);
  if (incarcareStil) return incarcareStil;
  incarcareStil = new Promise(function (ok, nu) {
    var sc = document.createElement('script');
    sc.src = 'xlsx-stil.js?v=' + STIL_V;
    sc.onload = function () { window.XlsxStil ? ok(window.XlsxStil) : nu(new Error('xlsx-stil.js nu definește XlsxStil')); };
    sc.onerror = function () { incarcareStil = null; nu(new Error('xlsx-stil.js nu s-a încărcat')); };
    document.head.appendChild(sc);
  });
  return incarcareStil;
}
function descarcaBlob(blob, nume) {
  var url = URL.createObjectURL(blob), a = document.createElement('a');
  a.href = url; a.download = nume;
  document.body.appendChild(a); a.click(); document.body.removeChild(a);
  setTimeout(function () { URL.revokeObjectURL(url); }, 4000);
}
function ctxExcel() {
  return { t: L, en: S.en, baza: paginaUrl(), cursuri: S.baza.cursuri, cursData: cursData(), peAcord: S.peAcord,
           generat: D.dataOraRo(), filtre: texteFiltre() };
}
function donatoriExport() {
  var baza = S.sel.length ? donatoriAlesi() : D.ordoneazaDonatori(S.baza.donatori, S.dsort, S.peAcord, S.baza.cursuri, S.en);
  return baza.map(function (d) { return { cheie: d.cheie, acorduri: filtrate(d.acorduri) }; }).filter(function (d) { return d.acorduri.length; });
}
function exporta(tip, cheie, btn) {
  var err = $('#exErr'); if (err) err.textContent = '';
  var ctx = ctxExcel(), spec, nume, azi = D.aziIso();
  if (tip === 'donator') {
    var d = S.baza.donatori.filter(function (x) { return x.cheie === cheie; })[0];
    var lista = d ? filtrate(d.acorduri) : [];
    if (!lista.length) { if (err) err.textContent = L('Nu e nimic de exportat cu filtrele de acum.', 'Nothing to export with the current filters.'); return; }
    spec = D.excelDonator(ctx, { cheie: cheie, acorduri: lista });
    nume = 'debursari-' + D.slug(cheie) + '-' + azi + '.xlsx';
  } else {
    var dons = donatoriExport();
    if (!dons.length) { if (err) err.textContent = L('Nu e nimic de exportat cu filtrele de acum.', 'Nothing to export with the current filters.'); return; }
    var orf = S.sel.length ? [] : S.orfane;
    if (tip === 'total') { spec = D.excelTotal(ctx, dons, orf); nume = 'debursari-total-' + azi + '.xlsx'; }
    else { spec = D.excelPeDonatori(ctx, dons, orf); nume = 'debursari-pe-donatori-' + azi + '.xlsx'; }
  }
  if (btn) btn.disabled = true;
  incarcaStil().then(function (X) { return X.construieste(spec); }).then(function (blob) {
    descarcaBlob(blob, nume);
    live(L('Fișierul Excel a fost generat: ', 'The Excel file was generated: ') + nume);
  }, function (e) {
    if (window.console) console.warn('Exportul Excel a eșuat:', e);
    if (err) err.textContent = L('Nu am putut genera fișierul Excel. Încearcă din nou.', 'Could not generate the Excel file. Try again.');
  }).then(function () { if (btn) btn.disabled = false; });
}
function descarcaJson() {
  var date = D.aplicaOps(S.serv || D.dateGoale(), S.coada);
  descarcaBlob(new Blob([D.text(date)], { type: 'application/json' }), 'debursari-' + D.aziIso() + '.json');
}

/* ------------------------------------------------------------------ evenimente */
RAD.addEventListener('click', function (ev) {
  var b = ev.target.closest('[data-act]');
  if (b && RAD.contains(b)) { actiune(b.getAttribute('data-act'), b, ev); return; }
  var tr = ev.target.closest('tr.ac');
  if (tr && RAD.contains(tr) && !ev.target.closest('a,button,input,select,textarea,label')) {
    if (window.getSelection && String(window.getSelection())) return;      // omul selectează text, nu deschide rândul
    comutaRand(tr.getAttribute('data-k'));
  }
});
function actiune(act, b) {
  var tr = b.closest('tr'), k = tr ? tr.getAttribute('data-k') : null;
  if (!k) { var f = b.closest('form[data-k]'); if (f) k = f.getAttribute('data-k'); }
  switch (act) {
    case 'unlock': deschideDialog(); break;
    case 'lock': cod = null; S.ed = null; S.conf = null; randeazaTot(); live(L('Câmpurile sunt din nou blocate.', 'The fields are locked again.')); break;
    case 'retry': S.eroareSalv = null; if (!cod) deschideDialog(); else trimite(); break;
    case 'renunta-coada':
      if (S.ocupat) break;
      S.coada = []; scrieCoada(); recalc(); dupaDate(); randeazaTot(); break;
    case 'reincarca': incarca(); break;
    case 'toti-afisati':
      donatoriAfisati().forEach(function (d) { if (S.sel.indexOf(d.cheie) < 0) S.sel.push(d.cheie); });
      dupaSelectie(); break;
    case 'sterge-sel': S.sel = []; dupaSelectie(); break;
    case 'sterge-filtre': S.q = ''; S.tip = ''; S.deb = ''; scrieHash(); randeazaTool(); randeazaRez(); break;
    case 'alege': comutaDonator(b.getAttribute('data-d'), true); break;
    case 'scoate': comutaDonator(b.getAttribute('data-d'), false); break;
    case 'comuta': if (k) comutaRand(k); break;
    case 'adauga': if (k) { deschideRand(k); focuseazaFormular(k); } break;
    case 'ed': pornesteEditare(b.getAttribute('data-id')); break;
    case 'ed-salveaza': salveazaEditare(); break;
    case 'ed-anuleaza': S.ed = null; randeazaRez(); break;
    case 'del': S.ed = null; S.conf = b.getAttribute('data-id'); randeazaRez(); randeazaOrfane(); break;
    case 'del-nu': S.conf = null; randeazaRez(); randeazaOrfane(); break;
    case 'del-da': sterge(b.getAttribute('data-id')); break;
    case 'excel-donator': exporta('donator', b.getAttribute('data-d'), b); break;
    case 'excel-total': exporta('total', null, b); break;
    case 'excel-donatori': exporta('donatori', null, b); break;
    case 'json': descarcaJson(); break;
    case 'uita-seif': lsDel(CH_SEIF); randeazaAcces(); randeazaNote(); live(L('Codul păstrat pe acest dispozitiv a fost șters.', 'The code kept on this device was deleted.')); break;
  }
}
RAD.addEventListener('change', function (ev) {
  var t = ev.target;
  if (t.matches('.don input[type=checkbox]')) { comutaDonator(t.getAttribute('data-d'), t.checked); t.closest('.don').classList.toggle('on', t.checked); return; }
  if (t.id === 'dsort') { S.dsort = t.value; randeazaLista(); randeazaRez(); return; }
  if (t.id === 'ftip') { S.tip = t.value; dupaFiltre(); return; }
  if (t.id === 'fdeb') { S.deb = t.value; dupaFiltre(); return; }
  if (t.id === 'fsort') { S.sort = t.value; dupaFiltre(); return; }
  if (t.matches('form.deb-form select')) sincronizeazaFormular(t);
  if (t.matches('[data-ed]') && S.ed) S.ed.f[t.getAttribute('data-ed')] = t.value;
});
RAD.addEventListener('input', function (ev) {
  var t = ev.target;
  if (t.id === 'dq') { S.dq = t.value; peste('dq', randeazaLista, 120); return; }
  if (t.id === 'q') { S.q = t.value.slice(0, 120); peste('q', dupaFiltre, 160); return; }
  if (t.matches('form.deb-form input')) sincronizeazaFormular(t);
  if (t.matches('[data-ed]') && S.ed) S.ed.f[t.getAttribute('data-ed')] = t.value;
});
function sincronizeazaFormular(el) {
  var form = el.closest('form.deb-form'), id = form.getAttribute('data-a'), a = S.baza.peId.get(id);
  var f = formDe(a);
  f[el.name] = el.value;
  var er = S.fe[id];
  if (er && er[el.name]) { delete er[el.name]; el.removeAttribute('aria-invalid'); var m = form.querySelector('.ferr'); if (m) m.textContent = textErori(er); }
  var pv = form.querySelector('.prev'); if (pv) pv.innerHTML = previzualizare(f);
}
RAD.addEventListener('submit', function (ev) {
  var f = ev.target.closest('form.deb-form');
  if (!f) return;
  ev.preventDefault();
  adauga(f);
});
RAD.addEventListener('keydown', function (ev) {
  var t = ev.target;
  if (t.matches && t.matches('[data-ed]') && S.ed) {
    if (ev.key === 'Enter') { ev.preventDefault(); S.ed.f[t.getAttribute('data-ed')] = t.value; salveazaEditare(); }
    else if (ev.key === 'Escape') { ev.preventDefault(); S.ed = null; randeazaRez(); }
  }
});

/* fereastra codului */
var DLG = $('#dlg');
DLG.addEventListener('submit', function (ev) { ev.preventDefault(); trimiteDialog(); });
DLG.addEventListener('click', function (ev) {
  var b = ev.target.closest('[data-dlg]');
  if (!b) { if (ev.target === DLG) inchideDialog(); return; }
  var a = b.getAttribute('data-dlg');
  if (a === 'inchide') inchideDialog();
  else if (a === 'alt-cod') { S.dlg.mod = 'cod'; S.dlg.eroare = ''; randeazaDialog(); var n = $('#inCod', DLG); if (n) n.focus(); }
  else if (a === 'cu-pin') { S.dlg.mod = 'pin'; S.dlg.eroare = ''; randeazaDialog(); var p = $('#inPin', DLG); if (p) p.focus(); }
});
DLG.addEventListener('change', function (ev) {
  if (ev.target.id === 'inTine') {
    S.dlg.tine = ev.target.checked;
    var r = $('#rPin', DLG); if (r) { r.hidden = !ev.target.checked; if (ev.target.checked) { var p = $('#inPin', DLG); if (p) p.focus(); } }
  }
});
DLG.addEventListener('close', function () { DLG.innerHTML = ''; S.dlg.ocupat = false; });

window.addEventListener('hashchange', function () {
  if (!S.baza) return;
  aplicaHash(location.hash);
  randeazaKpi(); randeazaLista(); randeazaTool(); randeazaRez();
});
window.addEventListener('beforeunload', function (ev) {
  if (S.ocupat || (S.coada.length && cod)) { ev.preventDefault(); ev.returnValue = ''; }
});
new MutationObserver(function () {
  var en = document.documentElement.lang === 'en';
  if (en !== S.en) { S.en = en; randeazaTot(); }
}).observe(document.documentElement, { attributes: true, attributeFilter: ['lang'] });

/* pentru teste și depanare: nimic din ce ține de cod nu e expus */
window.DebursariUI = { stare: function () { return { sel: S.sel.slice(), coada: S.coada.length, deblocat: !!cod, ocupat: S.ocupat, intrari: S.intrari.length, orfane: S.orfane.length }; } };

incarca();
})();
