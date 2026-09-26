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
  var CHEIE = 'ampActivityIds', VALABIL_MS = 24 * 3600 * 1000;
  var harta = null;

  function en() { return typeof currentLang !== 'undefined' && currentLang === 'en'; }

  window.ampActivityId = function (ampId) { return harta && ampId ? harta[String(ampId)] || null : null; };
  window.ampProjectUrl = function (ampId) { var a = window.ampActivityId(ampId); return a ? URL_FISA + a : ''; };

  function aplica(root) {
    if (!harta) return;
    var noduri = (root && root.querySelectorAll ? root : document).querySelectorAll('[data-ampid]:not([data-amp-ok])');
    for (var i = 0; i < noduri.length; i++) {
      var el = noduri[i], id = el.getAttribute('data-ampid'), act = harta[id];
      el.setAttribute('data-amp-ok', '1');
      if (!act) continue;
      var a = document.createElement('a');
      a.href = URL_FISA + act; a.target = '_blank'; a.rel = 'noopener';
      a.className = 'amp-link';
      a.title = en() ? 'Open the project page in AMP (amp.gov.md)' : 'Deschide fișa proiectului în AMP (amp.gov.md)';
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
    if (!harta) return;
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
    harta = h;
    aplica(document);
    try { if (typeof exportRenderColumnPicker === 'function' && document.getElementById('updateView').style.display !== 'none') { exportRenderColumnPicker(); exportRenderPreview(); } } catch (e) {}
  }

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
      if (!Object.keys(h).length) return;
      try { localStorage.setItem(CHEIE, JSON.stringify({ t: Date.now(), m: h })); } catch (e) {}
      gata(h);
    }).catch(function (e) { console.warn('linkuri AMP:', e); });
  })(1);
})();
