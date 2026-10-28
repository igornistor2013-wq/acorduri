/* Bara de navigare comună pentru toate paginile site-ului.
   ------------------------------------------------------------------
   Aceeași bară, cu aceleași butoane și în aceeași ordine, apare pe
   index.html (în toate vederile ei: dashboard, analize, export, IATI,
   d-portal), pe cele două registre de acorduri și pe HG 246. Înainte,
   fiecare pagină își avea propriul set de butoane, iar din unele (de ex.
   Acorduri) nu se putea ajunge la IATI sau la Analize.

   Se include acolo unde trebuie să apară bara:
     <script src="meniu.js" data-pagina="acorduri-mo"></script>
   data-pagina marchează butonul paginii curente:
     index | acorduri-mo | acorduri-legis | debursari | hg246
   Pe index, vederea curentă se marchează din pagină: Meniu.activ('iati').
   data-limba="da" adaugă comutatorul RO/EN (doar pe index, singura pagină
   tradusă); pagina îl leagă singură la setLanguage().
*/
(function () {
  'use strict';
  var script = document.currentScript;
  if (!script) return;
  var PAGINA = script.getAttribute('data-pagina') || '';
  var PE_INDEX = PAGINA === 'index';
  // comutatorul RO/EN apare pe toate paginile; pe index îl leagă pagina (setLanguage),
  // pe celelalte îl leagă traducere.js
  var CU_LIMBA = true;
  var limba = 'ro';

  var T = {
    ro: {
      acasa: 'Donatori și proiecte', analize: 'Analize avansate', export: 'Export',
      iati: 'IATI', iatiCheck: 'Verificare IATI d-portal', iatiCheckSub: 'Potrivirea proiectelor AMP cu activitățile IATI',
      iatiDash: 'Dashboard IATI d-portal', iatiDashSub: 'Activitățile raportate în IATI pentru Moldova',
      acorduri: 'Acorduri', legis: 'Acorduri · legis.md', legisSub: 'Registrul de stat al actelor juridice, 1992 până azi',
      mo: 'Acorduri · Monitorul Oficial', moSub: 'Cuprinsurile Monitorului, actualizat zilnic, din 2024',
      lege: 'De la lege la bani', legeSub: 'Acordurile legate de proiectele din AMP: cât s-a angajat și debursat',
      deb: 'Debursări pe acorduri', debSub: 'Pe donatori: proiecte, sume și debursări introduse de mână',
      hg: 'HG 246', hgSub: '', meniu: 'Navigare', doarRo: '',
      acasaS: 'Donatori', analizeS: 'Analize', acorduriS: 'Acorduri', despre: 'Despre date', cauta: 'Caută', cautaLung: 'Caută pe site (tasta /)', print: 'Printează sau salvează ca PDF'
    },
    en: {
      acasa: 'Donors & projects', analize: 'Advanced analytics', export: 'Export',
      iati: 'IATI', iatiCheck: 'IATI d-portal cross-check', iatiCheckSub: 'Matching AMP projects with IATI activities',
      iatiDash: 'IATI d-portal dashboard', iatiDashSub: 'Activities reported to IATI for Moldova',
      acorduri: 'Agreements', legis: 'Agreements · legis.md', legisSub: 'State Register of Legal Acts, 1992 to date',
      mo: 'Agreements · Official Gazette', moSub: 'Official Gazette contents, updated daily, since 2024',
      lege: 'From law to money', legeSub: 'Agreements linked to AMP projects: how much was committed and disbursed',
      deb: 'Disbursements by agreement', debSub: 'By donor: projects, amounts and disbursements entered by hand',
      hg: 'HG 246', hgSub: '', meniu: 'Navigation', doarRo: ' · in Romanian',
      acasaS: 'Donors', analizeS: 'Analytics', acorduriS: 'Agreements', despre: 'About the data', cauta: 'Search', cautaLung: 'Search the site (key /)', print: 'Print or save as PDF'
    }
  };

  var I = {
    acasa: '<path d="M3 11l9-8 9 8"/><path d="M5 10v10h14V10"/><path d="M10 20v-6h4v6"/>',
    analize: '<path d="M3 3v18h18"/><path d="M18 9l-5 5-4-4-4 4"/>',
    export: '<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/>',
    iati: '<circle cx="12" cy="12" r="10"/><line x1="2" y1="12" x2="22" y2="12"/><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"/>',
    check: '<path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"/><path d="M9 12l2 2 4-4"/>',
    dash: '<path d="M3 3v18h18"/><rect x="7" y="10" width="3" height="7"/><rect x="13" y="6" width="3" height="11"/>',
    acord: '<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="8" y1="13" x2="16" y2="13"/><line x1="8" y1="17" x2="13" y2="17"/>',
    lant: '<path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"/><path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"/>',
    monede: '<circle cx="8" cy="8" r="6"/><path d="M18.09 10.37A6 6 0 1 1 10.34 18"/><path d="M7 6h1v4"/><path d="m16.71 13.88.7.71-2.82 2.82"/>',
    carte: '<path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/>',
    hg: '<path d="M9 11l3 3 8-8"/><path d="M20 12v7a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h9"/>',
    sag: '<polyline points="6 9 12 15 18 9"/>',
    info: '<circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/>',
    lupa: '<circle cx="11" cy="11" r="7"/><line x1="21" y1="21" x2="16.5" y2="16.5"/>',
    print: '<polyline points="6 9 6 2 18 2 18 9"/><path d="M6 18H4a2 2 0 0 1-2-2v-5a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v5a2 2 0 0 1-2 2h-2"/><rect x="6" y="14" width="12" height="8"/>'
  };
  function svg(k, cls) { return '<svg class="' + (cls || 'mg-ico') + '" viewBox="0 0 24 24" aria-hidden="true">' + I[k] + '</svg>'; }

  /* Aspectul barei: „Raport editorial" luminos — file cu linie dedesubt (cea activă are
     linia aurie), câmp de căutare, comutator RO/EN segmentat. Structura (id-uri, clase,
     comportament) a rămas neschimbată; aici se schimbă doar prezentarea. */
  var CSS = '' +
    '.mg{display:flex;flex-wrap:wrap;align-items:center;gap:6px 16px;margin:0 0 30px;padding:0;border-bottom:1px solid #E1E6EF;' +
      'font-family:Inter,-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,"Helvetica Neue",Arial,sans-serif;font-variant-numeric:tabular-nums}' +
    '.mg-btns{display:flex;flex-wrap:wrap;gap:0 24px;align-items:stretch;flex:1;min-width:0}' +
    '.mg-b{display:inline-flex;align-items:center;gap:6px;padding:17px 1px 14px;font-size:15px;font-weight:600;color:#4A5470;' +
      'white-space:nowrap;cursor:pointer;text-decoration:none;border:0;border-bottom:3px solid transparent;border-radius:0;background:none;' +
      'font-family:inherit;line-height:1.2;position:relative;letter-spacing:0;transition:color .15s ease,border-color .15s ease}' +
    /* index.html are reguli generale pe button (ridicare, umbră, strălucire) și vechi pe id-uri (overflow:hidden):
       în bară nu trebuie să se aplice */
    '.mg .mg-b,.mg .mg-b:hover,.mg .mg-b:active{transform:none;filter:none;box-shadow:none;background:none}' +
    '.mg .mg-b{overflow:visible !important}' +
    '.mg .mg-b:hover{color:#12244A;border-bottom-color:#C9CFDD}' +
    '.mg .mg-b.activ{color:#12244A;font-weight:700;border-bottom-color:#B87714}' +
    '.mg .mg-b:focus-visible{outline:2px solid #12244A;outline-offset:-2px;border-radius:6px}' +
    '.mg-b .mg-ico{display:none}' +
    '.mg-ico{width:16px;height:16px;flex:none;stroke:currentColor;fill:none;stroke-width:2.2}' +
    '.mg-sag{width:14px;height:14px;flex:none;stroke:currentColor;fill:none;stroke-width:2.4;transition:transform .15s ease}' +
    '.mg-dd.deschis .mg-sag{transform:rotate(180deg)}' +
    '.mg-dd{position:relative;display:flex}' +
    '.mg-pop{display:none;position:absolute;top:calc(100% + 6px);left:-14px;width:330px;max-width:calc(100vw - 32px);background:#fff;' +
      'border:1px solid #E1E6EF;border-radius:14px;box-shadow:0 18px 40px -14px rgba(18,36,74,.3);overflow:hidden;z-index:60}' +
    '.mg-dd.deschis .mg-pop{display:block}' +
    '.mg-opt{display:flex;align-items:flex-start;gap:12px;padding:13px 18px;text-decoration:none;color:#141B2D;border-bottom:1px solid #EEF2F9}' +
    '.mg-opt:last-child{border-bottom:none}' +
    '.mg-opt:hover,.mg-opt:focus-visible{background:#F5F7FB;outline:none}' +
    '.mg-opt.activ{background:#EEF2F9;box-shadow:inset 3px 0 0 #B87714}' +
    '.mg-opt .mg-ico{stroke:#1F3D6E;margin-top:2px}' +
    '.mg-opt b{display:block;font-size:14px;font-weight:650;color:#12244A}' +
    '.mg-opt small{display:block;font-size:12.5px;color:#5B6478;margin-top:2px;white-space:normal;line-height:1.4}' +
    '.mg-unealta{display:inline-flex;align-items:center;gap:8px;height:40px;border:1px solid #C9CFDD;background:#fff;color:#4A5470;border-radius:10px;' +
      'padding:0 12px;font-size:14px;font-weight:500;cursor:pointer;font-family:inherit}' +
    '.mg .mg-unealta:hover{background:#F5F7FB;color:#12244A;border-color:#1F3D6E;transform:none;filter:none;box-shadow:none}' +
    '.mg-unealta:focus-visible{outline:2px solid #12244A;outline-offset:2px}' +
    '.mg-unealta .mg-ico{display:block;width:16px;height:16px}' +
    '.mg-cauta{margin-left:auto;min-width:210px;justify-content:flex-start;background:#F5F7FB;border-color:#E1E6EF}' +
    '.mg-cauta kbd{margin-left:auto;border:1px solid #C9CFDD;border-bottom-width:2px;border-radius:5px;padding:0 6px;font-size:11.5px;line-height:18px;background:#fff;color:#4A5470;font-family:inherit}' +
    '.mg-print{width:40px;padding:0;justify-content:center}' +
    '.mg-despre{display:inline-flex;align-items:center;gap:6px;font-size:14px;font-weight:600;color:#4A5470;text-decoration:none;padding:8px 2px;border-radius:8px;white-space:nowrap}' +
    '.mg-despre .mg-ico{display:none}' +
    '.mg-despre:hover{color:#12244A;text-decoration:underline;text-decoration-color:#B87714;text-decoration-thickness:2px;text-underline-offset:6px}' +
    '.mg-despre.activ{color:#12244A;text-decoration:underline;text-decoration-color:#B87714;text-decoration-thickness:2px;text-underline-offset:6px}' +
    '.mg-despre:focus-visible{outline:2px solid #12244A;outline-offset:2px}' +
    '.mg .mg-limba{display:flex;gap:2px;background:#F5F7FB;border:1px solid #E1E6EF;border-radius:10px;padding:3px}' +
    '.mg .mg-limba button{border:none;background:transparent;color:#4A5470;font-size:12.5px;font-weight:700;padding:6px 12px;border-radius:7px;cursor:pointer;letter-spacing:.04em;font-family:inherit;line-height:1.2}' +
    '.mg .mg-limba button:hover:not(.active){color:#12244A;background:#EEF2F9;transform:none;filter:none;box-shadow:none}' +
    '.mg .mg-limba button.active{background:#12244A;color:#fff}' +
    '.mg-s{display:none}' +
    /* telefon: trei file pe rând, etichete scurte; căutarea, Despre și limba sus */
    '@media (max-width:720px){' +
      '.mg{gap:8px;margin-bottom:18px;padding-bottom:0;justify-content:flex-end}' +
      '.mg-limba{order:-1}' +
      '.mg-despre{order:-2;margin-left:0;margin-right:auto;font-size:13px}' +
      '.mg-cauta{order:-2;min-width:0;margin-left:0;height:36px}.mg-cauta kbd,.mg-cauta-t{display:none}.mg-print{order:-2;height:36px;width:36px}' +
      '.mg-btns{flex-basis:100%;display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:0 4px;position:relative;border-top:1px solid #E1E6EF}' +
      '.mg-dd{display:block;position:static}' +
      '.mg-b{width:100%;justify-content:center;padding:12px 2px 10px;font-size:13.5px;gap:4px}' +
      '.mg-l{display:none}.mg-s{display:inline;overflow:hidden;text-overflow:ellipsis}' +
      '.mg-pop{left:0 !important;right:0;width:auto;max-width:none;top:100%}' +
    '}' +
    '@media (prefers-reduced-motion:reduce){.mg-b,.mg-sag{transition:none}}' +
    /* printare / PDF curat, pe toate paginile: fără meniu și butoane de lucru, fără
       umbre, tabelele și listele întregi (fără derulare internă), panourile nerupte */
    '@media print{@page{margin:14mm}html,body{background:#fff !important}.mg,.cg-ov,.map-zoom-controls,.map-mod,.map-back,.rmap-mod,.rmap-back,.mai-mult,.mai-mult-td,.link-acord,.xls,#dataStatus button,.btns .dd,.seek{display:none !important}' +
      '*{box-shadow:none !important;animation:none !important;transition:none !important}' +
      '.kpi,.et-card,tr,.fd-r,.bar-row{break-inside:avoid}h1,h2,h3,.panel-head{break-after:avoid}' +
      /* graficele desenate pentru ecran lat se micșorează la lățimea paginii, nu se taie */
      'svg{max-width:100% !important;min-width:0 !important;height:auto !important}.panel-body,.sd-wrap{overflow:visible !important}' +
      '.table-scroll,.map-list,.rmap-side,.cg-rez{max-height:none !important;overflow:visible !important}' +
      'a{color:inherit !important;text-decoration:none !important}}';

  function t(k) { return (T[limba] || T.ro)[k]; }
  // eticheta lungă pe ecran lat, cea scurtă pe telefon
  function lab(k) { var sc = t(k + 'S') || t(k); return '<span class="mg-l">' + t(k) + '</span><span class="mg-s">' + sc + '</span>'; }

  // pe index, butoanele păstrează id-urile vechi: codul paginii le leagă de vederi
  function html() {
    var ro = limba === 'ro';
    var noteRo = ro ? '' : t('doarRo');
    return '' +
      '<div class="mg-btns">' +
        '<a class="mg-b mg-acasa" data-k="acasa" id="mgAcasa" href="index.html">' + svg('acasa') + lab('acasa') + '</a>' +
        '<a class="mg-b mg-analize" data-k="analize" id="advancedAnalysisNavBtn" href="index.html#analize">' + svg('analize') + lab('analize') + '</a>' +
        '<a class="mg-b mg-export" data-k="export" id="updateNavBtn" href="index.html#export">' + svg('export') + lab('export') + '</a>' +
        '<div class="mg-dd" id="iatiSelector">' +
          '<button type="button" class="mg-b mg-iati" data-k="iati" id="iatiSelectorBtn" aria-haspopup="true" aria-expanded="false">' + svg('iati') + lab('iati') + '' + svg('sag', 'mg-sag') + '</button>' +
          '<div class="mg-pop" id="iatiSelectorMenu" role="menu">' +
            '<a class="mg-opt" role="menuitem" data-k="iati" id="iatiSelectorOptCheck" href="index.html#iati">' + svg('check') + '<span><b>' + t('iatiCheck') + '</b><small>' + t('iatiCheckSub') + '</small></span></a>' +
            '<a class="mg-opt" role="menuitem" data-k="dportal" id="iatiSelectorOptDash" href="index.html#dportal">' + svg('dash') + '<span><b>' + t('iatiDash') + '</b><small>' + t('iatiDashSub') + '</small></span></a>' +
          '</div>' +
        '</div>' +
        '<div class="mg-dd" id="acorduriSelector">' +
          '<button type="button" class="mg-b mg-acorduri" data-k="acorduri" id="acorduriNavBtn" aria-haspopup="true" aria-expanded="false">' + svg('acord') + lab('acorduri') + '' + svg('sag', 'mg-sag') + '</button>' +
          '<div class="mg-pop" id="acorduriSelectorMenu" role="menu">' +
            '<a class="mg-opt" role="menuitem" data-k="acorduri-legis" href="legis_acorduri.html">' + svg('carte') + '<span><b>' + t('legis') + '</b><small>' + t('legisSub') + noteRo + '</small></span></a>' +
            '<a class="mg-opt" role="menuitem" data-k="acorduri-mo" href="acorduri.html">' + svg('acord') + '<span><b>' + t('mo') + '</b><small>' + t('moSub') + noteRo + '</small></span></a>' +
            '<a class="mg-opt" role="menuitem" data-k="legaturi" id="acorduriOptLegaturi" href="index.html#legaturi">' + svg('lant') + '<span><b>' + t('lege') + '</b><small>' + t('legeSub') + '</small></span></a>' +
            '<a class="mg-opt" role="menuitem" data-k="debursari" id="acorduriOptDebursari" href="debursari.html">' + svg('monede') + '<span><b>' + t('deb') + '</b><small>' + t('debSub') + '</small></span></a>' +
          '</div>' +
        '</div>' +
        '<a class="mg-b mg-hg" data-k="hg246" id="hg246NavBtn" href="hg246.html">' + svg('hg') + lab('hg') + '</a>' +
      '</div>' +
      '<button type="button" class="mg-unealta mg-cauta" id="mgCauta" title="' + t('cautaLung') + '" aria-label="' + t('cautaLung') + '">' + svg('lupa') + '<span class="mg-cauta-t">' + t('cauta') + '</span><kbd>/</kbd></button>' +
      '<button type="button" class="mg-unealta mg-print" id="mgPrint" title="' + t('print') + '" aria-label="' + t('print') + '">' + svg('print') + '</button>' +
      '<a class="mg-despre' + (PAGINA === 'despre' ? ' activ' : '') + '" id="mgDespre" href="despre.html"' + (PAGINA === 'despre' ? ' aria-current="page"' : '') + '>' + svg('info') + '<span>' + t('despre') + '</span></a>' +
      (CU_LIMBA ? '<div class="mg-limba lang-switch" id="langSwitch"><button type="button" data-lang="ro" class="' + (ro ? 'active' : '') + '">RO</button>' +
                  '<button type="button" data-lang="en" class="' + (ro ? '' : 'active') + '">EN</button></div>' : '');
  }

  var st = document.createElement('style');
  st.textContent = CSS;
  document.head.appendChild(st);

  var nav = document.createElement('nav');
  nav.className = 'mg';
  nav.setAttribute('aria-label', t('meniu'));
  nav.innerHTML = html();
  script.parentNode.insertBefore(nav, script);
  var BAZA = (script.getAttribute('src') || '').replace(/meniu\.js.*$/, '');
  window.__CAUTARE_BAZA = BAZA;
  function incarcaCautare(cb) {
    if (window.Cautare) return cb();
    var s = document.createElement('script'); s.src = BAZA + 'cautare.js'; s.onload = cb; document.head.appendChild(s);
  }
  function legaUnelte() {
    var c = nav.querySelector('#mgCauta'); if (c) c.onclick = function () { incarcaCautare(function () { window.Cautare.deschide(); }); };
    var p = nav.querySelector('#mgPrint'); if (p) p.onclick = function () { window.print(); };
  }
  legaUnelte();
  // tasta / sau Ctrl+K deschide căutarea chiar înainte ca fișierul ei să fie încărcat
  document.addEventListener('keydown', function (e) {
    if (window.Cautare) return;
    var tag = (document.activeElement && document.activeElement.tagName) || '';
    if (/INPUT|TEXTAREA|SELECT/.test(tag)) return;
    if ((e.key === '/' && !e.ctrlKey && !e.metaKey && !e.altKey) || ((e.ctrlKey || e.metaKey) && (e.key === 'k' || e.key === 'K'))) {
      e.preventDefault(); incarcaCautare(function () { window.Cautare.deschide(); });
    }
  });
  /* Repere pentru cititoarele de ecran: dacă pagina nu-și marchează singură
     conținutul principal, îl marcăm noi (containerul în care stă meniul). */
  // (verificăm după încărcare: pe index și pe Despre conținutul principal e marcat mai jos în pagină)
  (function marcheazaMain(){
    function f(){
      if (!document.querySelector('main,[role="main"]') && nav.parentNode && nav.parentNode !== document.body) nav.parentNode.setAttribute('role', 'main');
      // antetul și subsolul paginilor stau în interiorul conținutului principal: nu sunt repere separate
      document.querySelectorAll('[role="main"] header, [role="main"] footer, main header, main footer').forEach(function (e) {
        if (!e.hasAttribute('role')) e.setAttribute('role', 'none');
      });
    }
    if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', f); else f();
  })();

  var cheieActiva = '';
  function activ(k) {
    cheieActiva = k || '';
    var grup = { iati: 'iati', dportal: 'iati', 'acorduri-mo': 'acorduri', 'acorduri-legis': 'acorduri', legaturi: 'acorduri', debursari: 'acorduri' }[cheieActiva] || cheieActiva;
    nav.querySelectorAll('.mg-b').forEach(function (b) {
      var on = b.getAttribute('data-k') === grup;
      b.classList.toggle('activ', on);
      if (on) b.setAttribute('aria-current', 'page'); else b.removeAttribute('aria-current');
    });
    nav.querySelectorAll('.mg-opt').forEach(function (o) { o.classList.toggle('activ', o.getAttribute('data-k') === cheieActiva); });
  }

  // meniurile derulante: clic, clic în afară, Esc, săgeți
  function leagaDropdown(dd) {
    var btn = dd.querySelector('.mg-b'), pop = dd.querySelector('.mg-pop');
    function arata(da, focus) {
      nav.querySelectorAll('.mg-dd.deschis').forEach(function (x) { if (x !== dd) inchide(x); });
      dd.classList.toggle('deschis', da);
      btn.setAttribute('aria-expanded', String(da));
      if (da) {
        pop.style.left = '';
        if (getComputedStyle(dd).position === 'static') { if (focus) { var o0 = pop.querySelector('.mg-opt'); if (o0) o0.focus(); } return; }
        pop.style.left = '0px';
        var r = pop.getBoundingClientRect(), vw = document.documentElement.clientWidth;
        if (r.right > vw - 12) pop.style.left = Math.round(vw - 12 - r.right) + 'px';
        if (focus) { var o = pop.querySelector('.mg-opt'); if (o) o.focus(); }
      }
    }
    btn.addEventListener('click', function (e) { e.stopPropagation(); arata(!dd.classList.contains('deschis'), false); });
    btn.addEventListener('keydown', function (e) { if (e.key === 'ArrowDown') { e.preventDefault(); arata(true, true); } });
    pop.addEventListener('keydown', function (e) {
      var opts = pop.querySelectorAll('.mg-opt'), i = Array.prototype.indexOf.call(opts, document.activeElement);
      if (e.key === 'ArrowDown') { e.preventDefault(); opts[(i + 1) % opts.length].focus(); }
      if (e.key === 'ArrowUp') { e.preventDefault(); opts[(i - 1 + opts.length) % opts.length].focus(); }
    });
    pop.addEventListener('click', function () { inchide(dd); });
  }
  function inchide(dd) {
    dd.classList.remove('deschis');
    var b = dd.querySelector('.mg-b'); if (b) b.setAttribute('aria-expanded', 'false');
  }
  function leagaTot() {
    nav.querySelectorAll('.mg-dd').forEach(leagaDropdown);
    if (PE_INDEX) {
      // pe index, butoanele schimbă vederea fără reîncărcare; restul (href) rămân
      // pentru „deschide în filă nouă"
      var vederi = { acasa: 'showMainView', analize: 'showAdvancedView', export: 'showExportView', iati: 'showIatiView', dportal: 'showDportalView', legaturi: 'showLegaturiView' };
      nav.querySelectorAll('[data-k]').forEach(function (el) {
        var fn = vederi[el.getAttribute('data-k')];
        if (!fn || el.tagName !== 'A') return;
        el.addEventListener('click', function (e) {
          if (e.ctrlKey || e.metaKey || e.shiftKey || e.button === 1) return;
          if (typeof window[fn] === 'function') { e.preventDefault(); window[fn](); }
        });
      });
    }
  }
  document.addEventListener('click', function (e) {
    nav.querySelectorAll('.mg-dd.deschis').forEach(function (dd) { if (!dd.contains(e.target)) inchide(dd); });
  });
  document.addEventListener('keydown', function (e) {
    if (e.key !== 'Escape') return;
    nav.querySelectorAll('.mg-dd.deschis').forEach(function (dd) { inchide(dd); var b = dd.querySelector('.mg-b'); if (b) b.focus(); });
  });

  leagaTot();
  if (!PE_INDEX) nav.querySelectorAll('.mg-limba button').forEach(function (b) {
    b.addEventListener('click', function () { if (window.Traducere) window.Traducere.seteaza(b.dataset.lang); });
  });
  activ(PE_INDEX ? 'acasa' : PAGINA);

  window.Meniu = {
    activ: activ,
    // schimbarea limbii refac etichetele; comutatorul RO/EN rămâne legat de pagină
    limba: function (l) {
      limba = l === 'en' ? 'en' : 'ro';
      nav.setAttribute('aria-label', t('meniu'));
      var set = function (sel, k) {
        var el = nav.querySelector(sel); if (!el) return;
        el.querySelector('.mg-l').textContent = t(k);
        el.querySelector('.mg-s').textContent = t(k + 'S') || t(k);
      };
      set('#mgAcasa', 'acasa');
      set('#advancedAnalysisNavBtn', 'analize');
      set('#updateNavBtn', 'export');
      set('#iatiSelectorBtn', 'iati');
      set('#acorduriNavBtn', 'acorduri');
      set('#hg246NavBtn', 'hg');
      var dsp = nav.querySelector('#mgDespre span'); if (dsp) dsp.textContent = t('despre');
      var cb = nav.querySelector('#mgCauta'); if (cb) { cb.title = t('cautaLung'); cb.setAttribute('aria-label', t('cautaLung')); cb.querySelector('.mg-cauta-t').textContent = t('cauta'); }
      var pb = nav.querySelector('#mgPrint'); if (pb) { pb.title = t('print'); pb.setAttribute('aria-label', t('print')); }
      nav.querySelectorAll('.mg-limba button').forEach(function (b) { b.classList.toggle('active', b.dataset.lang === limba); });
      var o = nav.querySelectorAll('.mg-opt');
      var txt = [[t('iatiCheck'), t('iatiCheckSub')], [t('iatiDash'), t('iatiDashSub')],
                 [t('legis'), t('legisSub') + t('doarRo')], [t('mo'), t('moSub') + t('doarRo')], [t('lege'), t('legeSub')], [t('deb'), t('debSub')]];
      o.forEach(function (el, i) { el.querySelector('b').textContent = txt[i][0]; el.querySelector('small').textContent = txt[i][1]; });
    }
  };
})();
