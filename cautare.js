/* Căutarea globală din bara de navigare (butonul cu lupă, sau tastele / și Ctrl+K).
   Caută, din orice pagină:
     – paginile site-ului;
     – acordurile din registre (date/cautare.json, generat zilnic de date_deschise.py);
     – pe pagina principală, și donatorii și proiectele AMP deja încărcate.
   Pe celelalte pagini, donatorii și proiectele se caută printr-un link spre pagina
   principală (index.html#cauta=…), unde sunt datele. Se încarcă doar la prima
   deschidere, deci nu îngreunează paginile. */
(function () {
  'use strict';
  var BAZA = (window.__CAUTARE_BAZA || '');
  var acte = null, seIncarca = false, ultimFocus = null;

  function en() {
    if (typeof currentLang !== 'undefined') return currentLang === 'en';
    if (window.Traducere && window.Traducere.limba) return window.Traducere.limba() === 'en';
    return document.documentElement.lang === 'en';
  }
  function T(ro, e) { return en() ? e : ro; }
  function esc(s) { return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]; }); }
  function fold(s) { return String(s || '').normalize('NFD').replace(/[̀-ͯ]/g, '').replace(/[ţ]/g, 't').replace(/[ş]/g, 's').toLowerCase(); }
  function potriveste(text, cuvinte) { var f = fold(text); for (var i = 0; i < cuvinte.length; i++) if (f.indexOf(cuvinte[i]) === -1) return false; return true; }
  function evid(text, cuvinte) {
    var s = esc(text);
    cuvinte.forEach(function (c) {
      if (c.length < 2) return;
      // evidențiere tolerantă la diacritice: căutăm în forma „pliată", marcăm în original
      var f = fold(text), i = f.indexOf(c);
      if (i > -1) { var orig = text.substr(i, c.length); s = s.replace(esc(orig), '<mark>' + esc(orig) + '</mark>'); }
    });
    return s;
  }

  var PAGINI = [
    ['index.html', 'Donatori și proiecte', 'Donors & projects', 'pagina principală donatori proiecte angajamente debursări hartă'],
    ['index.html#analize', 'Analize avansate', 'Advanced analytics', 'grafice evoluție rata execuție sankey sectoare raioane hartă'],
    ['index.html#export', 'Export Excel', 'Excel export', 'descarcă excel tabel coloane'],
    ['index.html#iati', 'Verificare IATI', 'IATI cross-check', 'iati d-portal potrivire'],
    ['index.html#dportal', 'Dashboard IATI d-portal', 'IATI d-portal dashboard', 'iati activități publicatori'],
    ['legis_acorduri.html', 'Acorduri · legis.md', 'Agreements · legis.md', 'registrul de stat acte juridice acorduri împrumut grant'],
    ['acorduri.html', 'Acorduri · Monitorul Oficial', 'Agreements · Official Gazette', 'monitorul oficial acorduri etape ratificare'],
    ['hg246.html', 'HG 246 — proiecte expirate', 'HG 246 — expired projects', 'hg 246 anexa facilități fiscale vamale'],
    ['despre.html', 'Despre date și metodologie', 'About the data and methodology', 'metodologie surse date deschise csv json rss']
  ];

  function stil() {
    if (document.getElementById('cautStil')) return;
    var st = document.createElement('style'); st.id = 'cautStil';
    st.textContent =
      '.cg-ov{position:fixed;inset:0;z-index:9500;background:rgba(15,25,45,.45);display:flex;justify-content:center;align-items:flex-start;padding:8vh 16px 16px}' +
      '.cg-ov[hidden]{display:none}' +
      '.cg{background:#fff;border-radius:14px;width:100%;max-width:680px;box-shadow:0 20px 60px rgba(10,20,40,.35);overflow:hidden;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Arial,sans-serif;color:#1c2230}' +
      '.cg-top{display:flex;align-items:center;gap:10px;padding:12px 14px;border-bottom:1px solid #e4e7ef}' +
      '.cg-top svg{width:18px;height:18px;stroke:#22406b;fill:none;stroke-width:2.3;flex:none}' +
      '.cg-top input{flex:1;border:none;outline:none;font-size:16px;padding:6px 2px;background:transparent;color:#1c2230;min-width:0}' +
      '.cg-top button{border:1px solid #c9ceda;background:#fff;border-radius:6px;font-size:11px;font-weight:700;color:#4f5668;padding:4px 8px;cursor:pointer}' +
      '.cg-rez{max-height:62vh;overflow:auto;padding:6px 0 10px}' +
      '.cg-sec{font-size:10.5px;font-weight:700;letter-spacing:.07em;text-transform:uppercase;color:#5f6679;padding:10px 16px 4px}' +
      '.cg-it{display:block;padding:8px 16px;text-decoration:none;color:#1c2230;border-left:3px solid transparent;cursor:pointer}' +
      '.cg-it:hover,.cg-it.sel{background:#eaf0fb;border-left-color:#22406b;outline:none}' +
      '.cg-it b{display:block;font-size:13.5px;font-weight:650;line-height:1.35;overflow:hidden;text-overflow:ellipsis;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical}' +
      '.cg-it small{display:block;font-size:11.5px;color:#5f6679;margin-top:2px}' +
      '.cg-it mark{background:#fdf1dc;color:inherit;border-radius:2px;padding:0 1px}' +
      '.cg-gol{padding:18px 16px;font-size:13px;color:#5f6679}' +
      '.cg-jos{display:flex;gap:14px;flex-wrap:wrap;padding:8px 16px;border-top:1px solid #e4e7ef;font-size:11px;color:#5f6679}' +
      '.cg-jos kbd{border:1px solid #c9ceda;border-bottom-width:2px;border-radius:4px;padding:0 5px;font-size:10.5px;background:#f5f6f9}' +
      '@media (max-width:640px){.cg-ov{padding:10px}.cg-rez{max-height:70vh}.cg-jos{display:none}}';
    document.head.appendChild(st);
  }

  function construieste() {
    var ov = document.getElementById('cautareGlobala');
    if (ov) return ov;
    stil();
    ov = document.createElement('div');
    ov.id = 'cautareGlobala'; ov.className = 'cg-ov'; ov.hidden = true;
    ov.innerHTML = '<div class="cg" role="dialog" aria-modal="true" aria-label="">' +
      '<div class="cg-top"><svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="11" cy="11" r="7"/><line x1="21" y1="21" x2="16.5" y2="16.5"/></svg>' +
      '<input type="search" autocomplete="off" spellcheck="false" role="combobox" aria-expanded="true" aria-controls="cgRez" aria-autocomplete="list">' +
      '<button type="button" class="cg-x">Esc</button></div>' +
      '<div class="cg-rez" id="cgRez" role="listbox"></div>' +
      '<div class="cg-jos"></div></div>';
    document.body.appendChild(ov);
    var inp = ov.querySelector('input');
    ov.addEventListener('click', function (e) { if (e.target === ov) inchide(); });
    ov.querySelector('.cg-x').onclick = inchide;
    inp.addEventListener('input', function () { randeaza(inp.value); });
    inp.addEventListener('keydown', function (e) {
      var items = [].slice.call(ov.querySelectorAll('.cg-it'));
      var i = items.indexOf(ov.querySelector('.cg-it.sel'));
      if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
        e.preventDefault(); if (!items.length) return;
        i = e.key === 'ArrowDown' ? Math.min(items.length - 1, i + 1) : Math.max(0, i - 1);
        items.forEach(function (x) { x.classList.remove('sel'); x.setAttribute('aria-selected', 'false'); });
        items[i].classList.add('sel'); items[i].setAttribute('aria-selected', 'true'); items[i].scrollIntoView({ block: 'nearest' });
        inp.setAttribute('aria-activedescendant', items[i].id);
      } else if (e.key === 'Enter') {
        var ales = items[i] || items[0]; if (ales) { e.preventDefault(); ales.click(); }
      } else if (e.key === 'Escape') { e.preventDefault(); inchide(); }
    });
    return ov;
  }

  function incarcaActe(cb) {
    if (acte) return cb();
    if (seIncarca) return;
    seIncarca = true;
    fetch(BAZA + 'date/cautare.json').then(function (r) { if (!r.ok) throw new Error(r.status); return r.json(); })
      .then(function (j) { acte = j || []; seIncarca = false; cb(); })
      .catch(function () { acte = []; seIncarca = false; cb(); });
  }

  var nrId = 0;
  function item(href, titlu, sub, cuvinte, onclick) {
    var id = 'cgi' + (++nrId);
    return '<a class="cg-it" role="option" aria-selected="false" id="' + id + '" href="' + esc(href) + '"' + (onclick ? ' data-act="' + esc(onclick) + '"' : '') + '><b>' + evid(titlu, cuvinte) + '</b>' + (sub ? '<small>' + sub + '</small>' : '') + '</a>';
  }

  function randeaza(q) {
    var ov = construieste(), box = ov.querySelector('.cg-rez'), E = en();
    var cuvinte = fold(q).split(/\s+/).filter(Boolean);
    var peIndex = typeof PROJECTS !== 'undefined' && typeof DONORS !== 'undefined';
    var h = '';
    nrId = 0;
    // pagini
    var pag = PAGINI.filter(function (p) { return !cuvinte.length || potriveste(p[1] + ' ' + p[2] + ' ' + p[3], cuvinte); });
    if (pag.length) h += '<div class="cg-sec">' + T('Pagini', 'Pages') + '</div>' + pag.slice(0, cuvinte.length ? 4 : 9).map(function (p) { return item(BAZA + p[0], E ? p[2] : p[1], '', cuvinte); }).join('');
    if (cuvinte.length) {
      // donatori și proiecte (doar pe pagina principală, unde sunt încărcate)
      if (peIndex) {
        var lbl = function (d) { try { return donorLabel(d); } catch (e) { return d; } };
        var don = DONORS.filter(function (d) { return potriveste(d + ' ' + lbl(d), cuvinte); }).slice(0, 6);
        if (don.length) h += '<div class="cg-sec">' + T('Donatori', 'Donors') + '</div>' + don.map(function (d) {
          return item('index.html#fisa=' + encodeURIComponent(d), lbl(d), T('deschide fișa donatorului', 'open donor profile'), cuvinte);
        }).join('');
        var vazut = {}, pr = [];
        for (var i = 0; i < PROJECTS.length && pr.length < 8; i++) {
          var p = PROJECTS[i], k = p.id || p.denumire;
          if (vazut[k]) continue;
          var nm = typeof projectLabel === 'function' ? projectLabel(p) : p.denumire;
          if (potriveste(p.denumire + ' ' + nm + ' ' + (p.id || ''), cuvinte)) { vazut[k] = 1; pr.push([p, nm]); }
        }
        if (pr.length) h += '<div class="cg-sec">' + T('Proiecte AMP', 'AMP projects') + '</div>' + pr.map(function (x) {
          return item('index.html#cauta=' + encodeURIComponent(x[0].id || x[1]), x[1], esc((x[0].id || '') + ' · ' + lbl(x[0].donator)), cuvinte, 'proiect');
        }).join('');
      } else {
        h += '<div class="cg-sec">' + T('Donatori și proiecte', 'Donors and projects') + '</div>' +
          item(BAZA + 'index.html#cauta=' + encodeURIComponent(q.trim()), T('Caută „', 'Search “') + q.trim() + T('” printre proiectele AMP', '” in AMP projects'), T('pe pagina principală', 'on the main page'), []);
      }
      // acorduri
      if (acte === null) { h += '<div class="cg-gol">' + T('Se încarcă acordurile…', 'Loading agreements…') + '</div>'; incarcaActe(function () { randeaza(ov.querySelector('input').value); }); }
      else {
        var ac = acte.filter(function (a) { return potriveste(a[0] + ' ' + a[1] + ' ' + a[2], cuvinte); });
        if (ac.length) h += '<div class="cg-sec">' + T('Acorduri', 'Agreements') + ' · ' + ac.length + '</div>' + ac.slice(0, 8).map(function (a) {
          return item(BAZA + 'legis_acorduri.html#v=acte&q=' + encodeURIComponent(a[0]), a[1], esc(a[0] + (a[2] ? ' · ' + a[2] : '') + (a[3] ? ' · ' + a[3] : '')), cuvinte);
        }).join('') + (ac.length > 8 ? item(BAZA + 'legis_acorduri.html#v=acte&q=' + encodeURIComponent(q.trim()), T('Toate cele ', 'All ') + ac.length + T(' acte în registru →', ' acts in the register →'), '', []) : '');
      }
      if (!h || h.indexOf('cg-it') === -1) h += '<div class="cg-gol">' + T('Niciun rezultat.', 'No results.') + '</div>';
    }
    box.innerHTML = h;
    var first = box.querySelector('.cg-it'); if (first && cuvinte.length) { first.classList.add('sel'); first.setAttribute('aria-selected', 'true'); }
    box.querySelectorAll('.cg-it').forEach(function (a) {
      a.addEventListener('click', function (e) {
        var href = a.getAttribute('href');
        // pe aceeași pagină, schimbarea adresei nu reîncarcă: închidem și lăsăm pagina să reacționeze
        var acelasi = href.split('#')[0] === '' || location.pathname.split('/').pop() === href.split('#')[0].split('/').pop() || (href.split('#')[0].split('/').pop() === 'index.html' && /\/$|index\.html$/.test(location.pathname));
        inchide(true);
        if (acelasi && href.indexOf('#') > -1) {
          e.preventDefault();
          var h = href.slice(href.indexOf('#'));
          var peIndex = typeof PROJECTS !== 'undefined';
          if (location.hash === h) window.dispatchEvent(new HashChangeEvent('hashchange'));
          else location.hash = h;
          // registrele citesc filtrele din adresă doar la încărcare
          if (!peIndex) location.reload();
        }
      });
    });
  }

  function deschide() {
    var ov = construieste(), inp = ov.querySelector('input');
    ov.querySelector('.cg').setAttribute('aria-label', T('Căutare pe site', 'Site search'));
    inp.placeholder = T('Caută un donator, un proiect, un acord sau o pagină…', 'Search a donor, a project, an agreement or a page…');
    inp.setAttribute('aria-label', T('Caută pe site', 'Search the site'));
    ov.querySelector('.cg-jos').innerHTML = '<span><kbd>↑</kbd> <kbd>↓</kbd> ' + T('alege', 'choose') + '</span><span><kbd>Enter</kbd> ' + T('deschide', 'open') + '</span><span><kbd>Esc</kbd> ' + T('închide', 'close') + '</span><span><kbd>/</kbd> ' + T('deschide căutarea de oriunde', 'open search anywhere') + '</span>';
    ultimFocus = document.activeElement;
    ov.hidden = false;
    document.documentElement.style.overflow = 'hidden';
    randeaza(inp.value);
    setTimeout(function () { inp.focus(); inp.select(); }, 0);
    incarcaActe(function () { if (!ov.hidden && inp.value.trim()) randeaza(inp.value); });
  }
  function inchide(faraFocus) {
    var ov = document.getElementById('cautareGlobala');
    if (!ov || ov.hidden) return;
    ov.hidden = true;
    document.documentElement.style.overflow = '';
    if (faraFocus !== true && ultimFocus && ultimFocus.focus) ultimFocus.focus();
  }

  document.addEventListener('keydown', function (e) {
    var tag = (document.activeElement && document.activeElement.tagName) || '';
    var scrie = /INPUT|TEXTAREA|SELECT/.test(tag) || (document.activeElement && document.activeElement.isContentEditable);
    if ((e.key === '/' && !scrie && !e.ctrlKey && !e.metaKey && !e.altKey) || ((e.ctrlKey || e.metaKey) && (e.key === 'k' || e.key === 'K'))) {
      e.preventDefault(); deschide();
    }
  });

  window.Cautare = { deschide: deschide, inchide: inchide };
})();
