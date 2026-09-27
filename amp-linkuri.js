/* Linkuri spre fișa fiecărui proiect în AMP (amp.gov.md).
   ------------------------------------------------------------------
   Pagina publică a unui proiect în AMP folosește identificatorul intern al
   activității, nu AMP ID-ul afișat în tabele:
     AMP ID 8721196017661  →  https://amp.gov.md/aim/viewActivityPreview.do~activityId=9381
   Corespondența vine din raportul public al AMP (endpointul de rapoarte
   personalizate), citit prin același proxy ca raportul live (amp.vivi.md).
   Se păstrează în browser o zi, ca să nu fie cerută la fiecare deschidere.

   Oriunde pagina afișează un AMP ID într-un <span data-ampid="…">, acesta devine
   link când corespondența e cunoscută. Proiectele care nu mai există în AMP-ul
   de azi (o parte din arhiva veche, 1993–2022) rămân fără link. */
(function () {
  'use strict';
  var URL_FISA = 'https://amp.gov.md/aim/viewActivityPreview.do~activityId=';
  /* Proiectele care nu mai sunt în AMP-ul de azi (o mare parte din arhiva
     1993–2022) au încă o pagină publică pe serverul vechi al platformei. Lista
     AMP ID → activityId de acolo e în amp-vechi.json (serverul vechi nu are o
     listă publică: a fost construită o singură dată, deschizând paginile). */
  var URL_VECHI = 'http://87.255.68.120:8888/aim/viewActivityPreview.do~public=true~pageId=2~activityId=';
  var vechi = null, hartaTerminata = false;   // true după ce lista AMP de azi a sosit sau a eșuat
  var CHEIE = 'ampActivityIds', VALABIL_MS = 24 * 3600 * 1000;
  var harta = null;

  function en() { return typeof currentLang !== 'undefined' && currentLang === 'en'; }

  window.ampActivityId = function (ampId) { return harta && ampId ? harta[String(ampId)] || null : null; };
  window.ampProjectUrl = function (ampId) {
    var a = window.ampActivityId(ampId); if (a) return URL_FISA + a;
    var v = vechi && ampId ? vechi[String(ampId)] : null; return v ? URL_VECHI + v : '';
  };

  function aplica(root) {
    if (!harta && !vechi) return;
    var noduri = (root && root.querySelectorAll ? root : document).querySelectorAll('[data-ampid]:not([data-amp-ok])');
    for (var i = 0; i < noduri.length; i++) {
      var el = noduri[i], id = el.getAttribute('data-ampid');
      var act = harta && harta[id], vec = !act && vechi && vechi[id];
      // AMP-ul de azi are prioritate: până nu știm dacă proiectul e acolo, nu punem linkul vechi
      if (!act && vec && !hartaTerminata) continue;
      // fără corespondență încă: lăsăm nodul neprocesat dacă una din liste n-a sosit
      if (!act && !vec) { if (hartaTerminata && vechi) el.setAttribute('data-amp-ok', '1'); continue; }
      el.setAttribute('data-amp-ok', '1');
      var a = document.createElement('a');
      a.href = act ? URL_FISA + act : URL_VECHI + vec; a.target = '_blank'; a.rel = 'noopener';
      a.className = 'amp-link' + (act ? '' : ' amp-vechi');
      a.title = act
        ? (en() ? 'Open the project page in AMP (amp.gov.md)' : 'Deschide fișa proiectului în AMP (amp.gov.md)')
        : (en() ? 'Open the project page on the old AMP server (archive)' : 'Deschide fișa proiectului pe serverul vechi AMP (arhivă)');
      a.textContent = el.textContent;
      a.addEventListener('click', function (e) { e.stopPropagation(); });   // rândurile care se deschid la clic nu reacționează
      el.textContent = '';
      el.appendChild(a);
    }
  }

  var st = document.createElement('style');
  st.textContent = '.amp-link{color:inherit;text-decoration:underline;text-decoration-color:rgba(34,64,107,.35);text-underline-offset:3px}' +
    '.amp-link::after{content:"\\2197";font-size:.85em;margin-left:2px;color:#22406b}' +
    '.amp-link:hover,.amp-link:focus-visible{color:#22406b;text-decoration-color:#22406b}' +
    '@media print{.amp-link::after{content:""}}';
  document.head.appendChild(st);

  // tabelele se redesenează des (filtre, sortare, limbă): legăm tot ce apare nou
  new MutationObserver(function (muts) {
    if (!harta && !vechi) return;
    for (var i = 0; i < muts.length; i++) {
      var m = muts[i];
      for (var j = 0; j < m.addedNodes.length; j++) {
        var n = m.addedNodes[j];
        if (n.nodeType !== 1) continue;
        if (n.hasAttribute && n.hasAttribute('data-ampid') && !n.hasAttribute('data-amp-ok')) aplica(n.parentNode || document);
        else if (n.querySelector && n.querySelector('[data-ampid]:not([data-amp-ok])')) aplica(n);
      }
    }
  }).observe(document.body, { childList: true, subtree: true });

  function gata(h) {
    harta = h; hartaTerminata = true;
    aplica(document);
    try { if (typeof exportRenderColumnPicker === 'function' && document.getElementById('updateView').style.display !== 'none') { exportRenderColumnPicker(); exportRenderPreview(); } } catch (e) {}
  }

  // lista statică a serverului vechi
  fetch('amp-vechi.json').then(function (r) { return r.ok ? r.json() : null; }).then(function (j) {
    if (j && typeof j === 'object') { vechi = j; aplica(document); }
  }).catch(function () {});

  // din cache, dacă e proaspăt
  try {
    var c = JSON.parse(localStorage.getItem(CHEIE) || 'null');
    if (c && c.t && Date.now() - c.t < VALABIL_MS && c.m) { gata(c.m); return; }
  } catch (e) {}

  var baza = (typeof AMP_PROXY !== 'undefined' ? AMP_PROXY : 'https://amp.vivi.md') + '/rest/data/report/custom/paginate';
  function pagina(n) {
    var body = { name: 'amp-links', add_columns: ['AMP ID'], add_hierarchies: [], add_measures: ['Actual Commitments'],
      show_empty_rows: true, show_empty_columns: false, page: n, recordsPerPage: 1000, rowTotals: false };
    return fetch(baza, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) })
      .then(function (r) { if (!r.ok) throw new Error('AMP ' + r.status); return r.json(); });
  }
  var h = {};
  (function urm(n) {
    pagina(n).then(function (j) {
      var p = j && j.page, copii = (p && p.pageArea && p.pageArea.children) || [];
      copii.forEach(function (c) {
        var ampId = c.contents && c.contents['[AMP ID]'] && c.contents['[AMP ID]'].displayedValue;
        var act = c.owner && c.owner.id;
        if (ampId && act > 0) h[ampId] = act;
      });
      if (p && p.totalPageCount && n < p.totalPageCount && n < 20) return urm(n + 1);
      if (!Object.keys(h).length) { hartaTerminata = true; aplica(document); return; }
      try { localStorage.setItem(CHEIE, JSON.stringify({ t: Date.now(), m: h })); } catch (e) {}
      gata(h);
    }).catch(function (e) { console.warn('linkuri AMP:', e); hartaTerminata = true; aplica(document); });
  })(1);
})();
