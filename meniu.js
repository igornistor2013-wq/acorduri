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
     index | acorduri-mo | acorduri-legis | hg246
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
  var CU_LIMBA = script.getAttribute('data-limba') === 'da';
  var limba = 'ro';

  var T = {
    ro: {
      acasa: 'Donatori și proiecte', analize: 'Analize avansate', export: 'Export',
      iati: 'IATI', iatiCheck: 'Verificare IATI d-portal', iatiCheckSub: 'Potrivirea proiectelor AMP cu activitățile IATI',
      iatiDash: 'Dashboard IATI d-portal', iatiDashSub: 'Activitățile raportate în IATI pentru Moldova',
      acorduri: 'Acorduri', legis: 'Acorduri · legis.md', legisSub: 'Registrul de stat al actelor juridice, 1992 până azi',
      mo: 'Acorduri · Monitorul Oficial', moSub: 'Cuprinsurile Monitorului, actualizat zilnic, din 2024',
      hg: 'HG 246', hgSub: '', meniu: 'Navigare', doarRo: '',
      acasaS: 'Donatori', analizeS: 'Analize', acorduriS: 'Acorduri'
    },
    en: {
      acasa: 'Donors & projects', analize: 'Advanced analytics', export: 'Export',
      iati: 'IATI', iatiCheck: 'IATI d-portal cross-check', iatiCheckSub: 'Matching AMP projects with IATI activities',
      iatiDash: 'IATI d-portal dashboard', iatiDashSub: 'Activities reported to IATI for Moldova',
      acorduri: 'Agreements', legis: 'Agreements · legis.md', legisSub: 'State Register of Legal Acts, 1992 to date',
      mo: 'Agreements · Official Gazette', moSub: 'Official Gazette contents, updated daily, since 2024',
      hg: 'HG 246', hgSub: '', meniu: 'Navigation', doarRo: ' · in Romanian',
      acasaS: 'Donors', analizeS: 'Analytics', acorduriS: 'Agreements'
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
    carte: '<path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/>',
    hg: '<path d="M9 11l3 3 8-8"/><path d="M20 12v7a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h9"/>',
    sag: '<polyline points="6 9 12 15 18 9"/>'
  };
  function svg(k, cls) { return '<svg class="' + (cls || 'mg-ico') + '" viewBox="0 0 24 24" aria-hidden="true">' + I[k] + '</svg>'; }

  var CSS = '' +
    '.mg{display:flex;flex-wrap:wrap;align-items:center;gap:10px;margin:0 0 22px;padding:0 0 18px;border-bottom:1px solid #c9ceda;' +
      'font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,"Helvetica Neue",Arial,sans-serif}' +
    '.mg-btns{display:flex;flex-wrap:wrap;gap:10px;align-items:center;flex:1;min-width:0}' +
    '.mg-b{display:inline-flex;align-items:center;gap:8px;border-radius:10px;padding:11px 18px;font-size:14px;font-weight:800;' +
      'white-space:nowrap;cursor:pointer;text-decoration:none;letter-spacing:.01em;border:1.5px solid transparent;font-family:inherit;line-height:1.2;' +
      'position:relative;transition:transform .3s cubic-bezier(.34,1.56,.64,1),box-shadow .25s ease,background .25s ease,filter .2s ease}' +
    '.mg-b:hover{transform:translateY(-2px);filter:brightness(1.07)}' +
    /* index.html are reguli vechi pe id-uri (overflow:hidden) care ar tăia bara aurie */
    '.mg .mg-b{overflow:visible !important}' +
    '.mg-b:active{transform:translateY(0) scale(.98)}' +
    '.mg-b:focus-visible{outline:2px solid #c8871a;outline-offset:3px}' +
    '.mg-ico{width:16px;height:16px;flex:none;stroke:currentColor;fill:none;stroke-width:2.3}' +
    '.mg-sag{width:14px;height:14px;flex:none;stroke:currentColor;fill:none;stroke-width:2.3;transition:transform .15s ease}' +
    '.mg-dd.deschis .mg-sag{transform:rotate(180deg)}' +
    '.mg-acasa{background:#fff;color:#22406b;border-color:#22406b}' +
    '.mg-acasa:hover{background:#eaf0fb}' +
    '.mg-analize{background:linear-gradient(135deg,#c8871a,#e0a545);color:#3a2a00;box-shadow:0 3px 10px rgba(200,135,26,.35)}' +
    '.mg-export{background:linear-gradient(135deg,#159d7a,#0d7a5f);color:#fff;box-shadow:0 3px 10px rgba(13,122,95,.3)}' +
    '.mg-iati{background:linear-gradient(135deg,#22406b,#2f5691);color:#fff;box-shadow:0 3px 10px rgba(34,64,107,.28)}' +
    '.mg-acorduri,.mg-hg{background:linear-gradient(135deg,#16294a,#22406b);color:#fff;box-shadow:0 3px 10px rgba(22,41,74,.28)}' +
    /* pagina curentă: bară aurie sub buton + chenar */
    '.mg-b.activ{box-shadow:0 0 0 2px #fff,0 0 0 4px #c8871a}' +
    '.mg-b.activ::after{content:"";position:absolute;left:14px;right:14px;bottom:-9px;height:3px;border-radius:2px;background:#c8871a}' +
    '.mg-dd{position:relative;display:inline-block}' +
    '.mg-pop{display:none;position:absolute;top:calc(100% + 8px);left:0;width:310px;max-width:calc(100vw - 32px);background:#fff;' +
      'border:1px solid #c9ceda;border-radius:10px;box-shadow:0 12px 28px -8px rgba(20,35,60,.28);overflow:hidden;z-index:60}' +
    '.mg-dd.deschis .mg-pop{display:block}' +
    '.mg-opt{display:flex;align-items:flex-start;gap:10px;padding:12px 16px;text-decoration:none;color:#1c2230;border-bottom:1px solid #e3e7f0}' +
    '.mg-opt:last-child{border-bottom:none}' +
    '.mg-opt:hover,.mg-opt:focus-visible{background:#eaf0fb;outline:none}' +
    '.mg-opt.activ{background:#fdf1dc}' +
    '.mg-opt .mg-ico{stroke:#22406b;margin-top:2px}' +
    '.mg-opt b{display:block;font-size:13.5px}' +
    '.mg-opt small{display:block;font-size:11.5px;color:#6b7284;margin-top:2px;white-space:normal;line-height:1.35}' +
    '.mg-limba{display:flex;gap:4px;background:#f5f6f9;border:1px solid #c9ceda;border-radius:8px;padding:3px;margin-left:auto}' +
    '.mg-limba button{border:none;background:transparent;color:#6b7284;font-size:12px;font-weight:700;padding:6px 12px;border-radius:6px;cursor:pointer;letter-spacing:.03em;font-family:inherit}' +
    '.mg-limba button.active{background:#22406b;color:#fff}' +
    '.mg-s{display:none}' +
    /* telefon: două rânduri de câte trei butoane egale, etichete scurte;
       comutatorul de limbă sus, în dreapta */
    '@media (max-width:720px){' +
      '.mg{gap:10px;margin-bottom:16px;padding-bottom:14px;justify-content:flex-end}' +
      '.mg-limba{order:-1;margin-left:auto}' +
      '.mg-btns{flex-basis:100%;display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:8px;position:relative}' +
      '.mg-dd{display:block;position:static}' +
      '.mg-b{width:100%;justify-content:center;padding:9px 6px;font-size:12.5px;gap:5px;border-radius:8px}' +
      '.mg-ico{width:14px;height:14px}' +
      '.mg-l{display:none}.mg-s{display:inline;overflow:hidden;text-overflow:ellipsis}' +
      '.mg-b.activ::after{bottom:-6px;left:20%;right:20%}' +
      '.mg-pop{left:0 !important;right:0;width:auto;max-width:none}' +
    '}' +
    '@media (prefers-reduced-motion:reduce){.mg-b,.mg-sag{transition:none}.mg-b:hover{transform:none}}' +
    '@media print{.mg{display:none}}';

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
          '</div>' +
        '</div>' +
        '<a class="mg-b mg-hg" data-k="hg246" id="hg246NavBtn" href="hg246.html">' + svg('hg') + lab('hg') + '</a>' +
      '</div>' +
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

  var cheieActiva = '';
  function activ(k) {
    cheieActiva = k || '';
    var grup = { iati: 'iati', dportal: 'iati', 'acorduri-mo': 'acorduri', 'acorduri-legis': 'acorduri' }[cheieActiva] || cheieActiva;
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
      var vederi = { acasa: 'showMainView', analize: 'showAdvancedView', export: 'showExportView', iati: 'showIatiView', dportal: 'showDportalView' };
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
      var o = nav.querySelectorAll('.mg-opt');
      var txt = [[t('iatiCheck'), t('iatiCheckSub')], [t('iatiDash'), t('iatiDashSub')],
                 [t('legis'), t('legisSub') + t('doarRo')], [t('mo'), t('moSub') + t('doarRo')]];
      o.forEach(function (el, i) { el.querySelector('b').textContent = txt[i][0]; el.querySelector('small').textContent = txt[i][1]; });
    }
  };
})();
