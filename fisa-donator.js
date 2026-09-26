/* Fișa donatorului — un profil complet al unui finanțator, deschis prin clic pe
   numele lui (Top donatori, tabelul donatorilor) sau printr-un link direct:
   index.html#fisa=<nume>. Folosește datele deja încărcate de pagină (RAW,
   PROJECTS), deci arată aceleași cifre ca restul paginii: arhiva, plus raportul
   AMP live când a sosit. Fișa ignoră filtrele de an și donator ale paginii —
   e profilul întreg al donatorului. */
(function () {
  'use strict';
  var ANG = '#c8871a', DEB = '#22406b';
  var ultimFocus = null, curent = '';

  function en() { return typeof currentLang !== 'undefined' && currentLang === 'en'; }
  function T(ro, e) { return en() ? e : ro; }
  function bani(v) {
    var a = Math.abs(v || 0), E = en();
    if (a >= 999500000) return (v / 1e9).toFixed(2).replace(/\.?0+$/, '') + (E ? ' bn' : ' mld');
    if (a >= 999500) return (v / 1e6).toFixed(1).replace(/\.0$/, '') + (E ? ' M' : ' mil');
    if (a >= 999.5) return Math.round(v / 1e3) + (E ? ' K' : ' mii');
    return fmtNum(v || 0);
  }
  function eticheta(n) { try { return donorLabel(n); } catch (e) { return n; } }

  function stil() {
    if (document.getElementById('fisaStil')) return;
    var st = document.createElement('style');
    st.id = 'fisaStil';
    st.textContent =
      '.fd-ov{position:fixed;inset:0;z-index:9000;background:rgba(15,25,45,.45);display:flex;align-items:flex-start;justify-content:center;padding:4vh 16px;overflow:auto}' +
      '.fd-ov[hidden]{display:none}' +
      '.fd{background:#fff;border-radius:14px;max-width:980px;width:100%;box-shadow:0 20px 60px rgba(10,20,40,.35);color:#1c2230;position:relative}' +
      '.fd-h{display:flex;gap:14px;align-items:flex-start;justify-content:space-between;padding:20px 22px 12px;border-bottom:1px solid #e4e7ef}' +
      '.fd-h h2{margin:0;font-size:22px;line-height:1.2;color:#16294a;letter-spacing:-.01em}' +
      '.fd-grup{font-size:12px;color:#5f6679;margin-top:4px}' +
      '.fd-x{border:1px solid #c9ceda;background:#fff;border-radius:8px;width:34px;height:34px;font-size:18px;cursor:pointer;color:#22406b;flex:none}' +
      '.fd-x:hover{background:#eaf0fb}' +
      '.fd-b{padding:16px 22px 22px}' +
      '.fd-kpi{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:8px;margin-bottom:16px}' +
      '.fd-kpi div{background:#eaf0fb;border-radius:10px;padding:10px}' +
      '.fd-kpi b{display:block;font-size:17px;color:#16294a;font-variant-numeric:tabular-nums;white-space:nowrap}' +
      '.fd-kpi span{font-size:11px;color:#5f6679}' +
      '.fd-sub{font-size:11px;font-weight:700;letter-spacing:.06em;text-transform:uppercase;color:#5f6679;margin:14px 0 8px}' +
      '.fd-leg{display:flex;gap:14px;font-size:11.5px;color:#5f6679;margin:-2px 0 6px}.fd-leg i{display:inline-block;width:10px;height:10px;border-radius:3px;margin-right:5px;vertical-align:-1px}' +
      '.fd-ani svg{display:block;width:100%;height:auto}' +
      '.fd-2{display:grid;grid-template-columns:1fr 1fr;gap:18px}' +
      '.fd-r{display:grid;grid-template-columns:minmax(0,1fr) auto;gap:3px 10px;padding:5px 0}' +
      '.fd-r .n{font-size:12.5px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}' +
      '.fd-r .v{font-size:12px;font-weight:700;color:#22406b;font-variant-numeric:tabular-nums;white-space:nowrap}' +
      '.fd-r .bar{grid-column:1/-1;height:5px;background:#e7edf7;border-radius:3px;overflow:hidden}.fd-r .bar i{display:block;height:100%;border-radius:3px}' +
      '.fd-chips{display:flex;flex-wrap:wrap;gap:6px}.fd-chips span{background:#eaf0fb;border-radius:999px;padding:4px 10px;font-size:12px}.fd-chips b{color:#22406b}' +
      '.fd-t{width:100%;border-collapse:collapse;font-size:12.5px}.fd-t th{text-align:left;font-size:10.5px;text-transform:uppercase;letter-spacing:.05em;color:#5f6679;padding:6px 8px;border-bottom:1px solid #c9ceda}' +
      '.fd-t td{padding:7px 8px;border-bottom:1px solid #e4e7ef;vertical-align:top}.fd-t .num{text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap}.fd-t .id{font-family:Consolas,monospace;font-size:11px;color:#5f6679;white-space:nowrap}' +
      '.fd-act{display:flex;flex-wrap:wrap;gap:8px;margin-top:18px}' +
      '.fd-act button{border:1px solid #c9ceda;background:#fff;color:#22406b;border-radius:8px;padding:8px 14px;font-size:12.5px;font-weight:700;cursor:pointer}' +
      '.fd-act button.pr{background:#22406b;color:#fff;border-color:#22406b}.fd-act button:hover{filter:brightness(1.08)}' +
      '.fd-gol{font-size:12.5px;color:#5f6679}' +
      '.dn-link{background:none;border:none;padding:0;font:inherit;color:inherit;text-align:left;cursor:pointer;text-decoration:underline;text-decoration-color:rgba(34,64,107,.25);text-underline-offset:3px}' +
      '.dn-link:hover,.dn-link:focus-visible{color:#22406b;text-decoration-color:#22406b}' +
      '.bar-row button.bname{display:block;text-align:left;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}' +
      '@media (max-width:760px){.fd-kpi{grid-template-columns:repeat(2,minmax(0,1fr))}.fd-2{grid-template-columns:1fr}.fd-h h2{font-size:18px}.fd-b{padding:14px}.fd-h{padding:16px 14px 10px}.fd-t .hide-m{display:none}}' +
      '@media print{.fd-ov{position:static;background:none;padding:0}.fd{box-shadow:none}.fd-x,.fd-act{display:none}}';
    document.head.appendChild(st);
  }

  function container() {
    var ov = document.getElementById('fisaDonator');
    if (ov) return ov;
    stil();
    ov = document.createElement('div');
    ov.id = 'fisaDonator'; ov.className = 'fd-ov'; ov.hidden = true;
    ov.innerHTML = '<div class="fd" role="dialog" aria-modal="true" aria-labelledby="fdTitlu"></div>';
    ov.addEventListener('click', function (e) { if (e.target === ov) inchide(); });
    ov.addEventListener('keydown', function (e) {
      if (e.key === 'Escape') { e.stopPropagation(); inchide(); }
      if (e.key === 'Tab') {   // focusul rămâne în fișă
        var f = ov.querySelectorAll('button,a[href]'); if (!f.length) return;
        var a = f[0], z = f[f.length - 1];
        if (e.shiftKey && document.activeElement === a) { e.preventDefault(); z.focus(); }
        else if (!e.shiftKey && document.activeElement === z) { e.preventDefault(); a.focus(); }
      }
    });
    document.body.appendChild(ov);
    return ov;
  }

  function bare(lista, culoare, fmt) {
    if (!lista.length) return '<div class="fd-gol">' + T('Fără date.', 'No data.') + '</div>';
    var max = lista[0][1] || 1;
    return lista.map(function (x) {
      return '<div class="fd-r"><div class="n" title="' + esc(x[0]) + '">' + esc(x[0]) + '</div><div class="v">' + fmt(x[1]) + '</div>' +
        '<div class="bar"><i style="width:' + Math.max(2, Math.round(100 * x[1] / max)) + '%;background:' + culoare + '"></i></div></div>';
    }).join('');
  }

  function graficAni(ani) {
    var ks = Object.keys(ani).map(Number).sort(function (a, b) { return a - b; });
    if (!ks.length) return '<div class="fd-gol">' + T('Fără date pe ani.', 'No yearly data.') + '</div>';
    var y0 = ks[0], y1 = ks[ks.length - 1], n = y1 - y0 + 1;
    var W = 900, H = 170, pl = 8, pb = 22, pt = 8, max = 1;
    ks.forEach(function (y) { max = Math.max(max, ani[y].ang, ani[y].deb); });
    var slot = (W - pl * 2) / n, bw = Math.max(1.5, Math.min(14, slot / 2 - 1.5)), h = H - pb - pt;
    var s = '<svg viewBox="0 0 ' + W + ' ' + H + '" role="img" aria-label="' + T('Angajamente și debursări pe ani', 'Commitments and disbursements by year') + '">';
    s += '<line x1="' + pl + '" x2="' + (W - pl) + '" y1="' + (H - pb) + '" y2="' + (H - pb) + '" stroke="#c9ceda"/>';
    var pas = n > 24 ? 5 : (n > 12 ? 2 : 1);
    for (var y = y0; y <= y1; y++) {
      var cx = pl + (y - y0 + 0.5) * slot, o = ani[y] || { ang: 0, deb: 0 };
      var ha = o.ang / max * h, hd = o.deb / max * h;
      var tip = y + ' — ' + T('angajamente', 'commitments') + ': ' + fmtNum(o.ang) + ' EUR · ' + T('debursări', 'disbursements') + ': ' + fmtNum(o.deb) + ' EUR';
      if (ha > 0) s += '<rect x="' + (cx - bw - 1).toFixed(1) + '" y="' + (H - pb - ha).toFixed(1) + '" width="' + bw.toFixed(1) + '" height="' + ha.toFixed(1) + '" rx="1.5" fill="' + ANG + '"><title>' + esc(tip) + '</title></rect>';
      if (hd > 0) s += '<rect x="' + (cx + 1).toFixed(1) + '" y="' + (H - pb - hd).toFixed(1) + '" width="' + bw.toFixed(1) + '" height="' + hd.toFixed(1) + '" rx="1.5" fill="' + DEB + '"><title>' + esc(tip) + '</title></rect>';
      if ((y - y0) % pas === 0 || y === y1) s += '<text x="' + cx.toFixed(1) + '" y="' + (H - 6) + '" text-anchor="middle" font-size="11" fill="#5f6679">' + y + '</text>';
    }
    return s + '</svg>';
  }

  function deschide(nume, faraIstoric) {
    if (typeof PROJECTS === 'undefined' || !nume) return;
    var ov = container(), box = ov.firstChild, E = en();
    curent = nume;
    // cifrele pe donator: exact ca tabelul donatorilor (RAW, câte un rând pe donator și an)
    var randuri = (typeof RAW !== 'undefined' ? RAW : []).filter(function (r) { return r.donator === nume; });
    var ani = {}, ang = 0, deb = 0;
    randuri.forEach(function (r) {
      if (r.an === 'NA') return;
      ani[r.an] = ani[r.an] || { ang: 0, deb: 0 };
      ani[r.an].ang += r.Angajamente || 0; ani[r.an].deb += r.Debursari || 0;
    });
    randuri.forEach(function (r) { ang += r.Angajamente || 0; deb += r.Debursari || 0; });
    // proiectele donatorului (un proiect co-finanțat apare cu suma lui întreagă)
    var pr = PROJECTS.filter(function (p) { return (p.donatori || []).indexOf(nume) > -1; });
    var grup = new Map(), sect = new Map(), ben = new Map(), rai = new Map();
    pr.forEach(function (p) {
      var k = p.id || ('nm:' + p.denumire);
      if (!grup.has(k)) grup.set(k, { id: p.id, p: p, min: p.an, max: p.an, ang: 0, deb: 0 });
      var g = grup.get(k);
      if (p.an !== 'NA') { if (g.min === 'NA' || p.an < g.min) g.min = p.an; if (g.max === 'NA' || p.an > g.max) g.max = p.an; }
      g.ang += p.ang || 0; g.deb += p.deb || 0;
      (p.sectoare || []).forEach(function (s) { var n = s.nume || s; sect.set(n, (sect.get(n) || 0) + (p.ang || 0)); });
      (p.beneficiari || []).forEach(function (b) { ben.set(b, (ben.get(b) || 0) + (p.ang || 0)); });
      var r = p.id && typeof REGION_LOOKUP !== 'undefined' ? REGION_LOOKUP[p.id] : '';
      if (r) String(r).split(/\s*[;,]\s*/).forEach(function (x) { if (x) rai.set(x, (rai.get(x) || 0) + (p.ang || 0)); });
    });
    var proiecte = Array.from(grup.values()).sort(function (a, b) { return b.ang - a.ang; });
    var top = function (m, k) { return Array.from(m.entries()).filter(function (x) { return x[1] > 0; }).sort(function (a, b) { return b[1] - a[1]; }).slice(0, k); };
    var sectTop = top(sect, 6).map(function (x) { return [typeof sectorLabel === 'function' ? sectorLabel(x[0]) : x[0], x[1]]; });
    var benTop = top(ben, 6).map(function (x) { return [typeof beneficiaryLabel === 'function' ? beneficiaryLabel(x[0]) : x[0], x[1]]; });
    var raiTop = top(rai, 10);
    var ks = Object.keys(ani).map(Number).sort(function (a, b) { return a - b; });
    var per = ks.length ? (ks[0] === ks[ks.length - 1] ? ks[0] : ks[0] + '–' + ks[ks.length - 1]) : '—';
    var rata = ang > 0 ? Math.round(100 * deb / ang) + '%' : '—';
    var grupDon = '';
    try { grupDon = typeof groupOfDonor === 'function' ? groupOfDonor(nume) : ''; } catch (e) {}
    if (grupDon === nume) grupDon = '';
    var bEUR = function (v) { return bani(v) + ' EUR'; };

    box.innerHTML =
      '<div class="fd-h"><div><h2 id="fdTitlu">' + esc(eticheta(nume)) + '</h2>' +
        (grupDon ? '<div class="fd-grup">' + T('Grup', 'Group') + ': ' + esc(eticheta(grupDon)) + '</div>' : '') + '</div>' +
        '<button type="button" class="fd-x" aria-label="' + T('Închide fișa', 'Close') + '">×</button></div>' +
      '<div class="fd-b">' +
        '<div class="fd-kpi">' +
          '<div><b>' + fmtNum(proiecte.length) + '</b><span>' + T('proiecte', 'projects') + '</span></div>' +
          '<div><b>' + bani(ang) + '</b><span>' + T('angajamente, EUR', 'commitments, EUR') + '</span></div>' +
          '<div><b>' + bani(deb) + '</b><span>' + T('debursări, EUR', 'disbursements, EUR') + '</span></div>' +
          '<div><b>' + rata + '</b><span>' + T('rata de execuție', 'execution rate') + '</span></div>' +
          '<div><b>' + per + '</b><span>' + T('perioada', 'period') + '</span></div>' +
        '</div>' +
        '<div class="fd-sub">' + T('Pe ani', 'By year') + '</div>' +
        '<div class="fd-leg"><span><i style="background:' + ANG + '"></i>' + T('Angajamente', 'Commitments') + '</span><span><i style="background:' + DEB + '"></i>' + T('Debursări', 'Disbursements') + '</span></div>' +
        '<div class="fd-ani">' + graficAni(ani) + '</div>' +
        '<div class="fd-2">' +
          '<div><div class="fd-sub">' + T('Sectoare (angajamente)', 'Sectors (commitments)') + '</div>' + bare(sectTop, '#2a78d6', bEUR) + '</div>' +
          '<div><div class="fd-sub">' + T('Beneficiari (angajamente)', 'Beneficiaries (commitments)') + '</div>' + bare(benTop, '#1f8f66', bEUR) + '</div>' +
        '</div>' +
        (raiTop.length ? '<div class="fd-sub">' + T('Raioane cu proiecte localizate', 'Districts with located projects') + '</div><div class="fd-chips">' +
          raiTop.map(function (x) { return '<span>' + esc(x[0]) + ' · <b>' + bani(x[1]) + '</b></span>'; }).join('') + '</div>' : '') +
        '<div class="fd-sub">' + T('Cele mai mari proiecte', 'Largest projects') + (proiecte.length > 10 ? ' (10 ' + T('din', 'of') + ' ' + fmtNum(proiecte.length) + ')' : '') + '</div>' +
        (proiecte.length ? '<div style="overflow-x:auto"><table class="fd-t"><thead><tr><th class="hide-m">AMP ID</th><th>' + T('Proiect', 'Project') + '</th><th class="num">' + T('Perioada', 'Period') + '</th><th class="num">' + T('Angajamente', 'Commitments') + '</th><th class="num hide-m">' + T('Debursări', 'Disbursements') + '</th></tr></thead><tbody>' +
          proiecte.slice(0, 10).map(function (g) {
            var d = g.id && typeof REAL_DATES_LOOKUP !== 'undefined' ? REAL_DATES_LOOKUP[g.id] : null;
            var pp = d && d.s ? String(d.s).slice(-4) + (d.e ? '–' + String(d.e).slice(-4) : '') : (g.min === g.max ? g.min : g.min + '–' + g.max);
            var nm = typeof projectLabel === 'function' ? projectLabel(g.p) : g.p.denumire;
            return '<tr><td class="id hide-m">' + (typeof ampIdHtml === 'function' ? ampIdHtml(g.id) : esc(g.id || '—')) + '</td><td>' + esc(nm) + '</td><td class="num">' + esc(String(pp)) + '</td><td class="num">' + fmtNum(g.ang) + '</td><td class="num hide-m">' + fmtNum(g.deb) + '</td></tr>';
          }).join('') + '</tbody></table></div>' : '<div class="fd-gol">' + T('Niciun proiect.', 'No projects.') + '</div>') +
        '<div class="fd-act">' +
          '<button type="button" class="pr" data-a="filtru">' + T('Arată pe pagină doar acest donator', 'Show only this donor on the page') + '</button>' +
          '<button type="button" data-a="link">' + T('Copiază linkul fișei', 'Copy link to this profile') + '</button>' +
          '<button type="button" data-a="print">' + T('Printează / PDF', 'Print / PDF') + '</button>' +
          '<button type="button" data-a="inchide">' + T('Închide', 'Close') + '</button>' +
        '</div>' +
      '</div>';

    box.querySelector('.fd-x').onclick = inchide;
    box.querySelector('[data-a="inchide"]').onclick = inchide;
    box.querySelector('[data-a="print"]').onclick = function () { window.print(); };
    box.querySelector('[data-a="filtru"]').onclick = function () {
      inchide();
      try { if (typeof showMainView === 'function') showMainView(); } catch (e) {}
      try { aplicaDonatori(new Set([nume])); } catch (e) {}
      var p = document.getElementById('tablePanel'); if (p) p.scrollIntoView({ block: 'start' });
    };
    box.querySelector('[data-a="link"]').onclick = function () {
      var b = this, url = location.origin + location.pathname + '#fisa=' + encodeURIComponent(nume);
      var gata = function () { b.textContent = T('Linkul a fost copiat', 'Link copied'); setTimeout(function () { b.textContent = T('Copiază linkul fișei', 'Copy link to this profile'); }, 2000); };
      if (navigator.clipboard && navigator.clipboard.writeText) navigator.clipboard.writeText(url).then(gata, function () { prompt('Link:', url); });
      else prompt('Link:', url);
    };

    if (ov.hidden) ultimFocus = document.activeElement;
    ov.hidden = false;
    document.documentElement.style.overflow = 'hidden';
    box.querySelector('.fd-x').focus();
    if (!faraIstoric) {
      try { history.replaceState(history.state, '', location.pathname + location.search + '#fisa=' + encodeURIComponent(nume)); } catch (e) {}
    }
  }

  function inchide() {
    var ov = document.getElementById('fisaDonator');
    if (!ov || ov.hidden) return;
    ov.hidden = true; curent = '';
    document.documentElement.style.overflow = '';
    if (/^#fisa=/.test(location.hash)) {
      try { history.replaceState(history.state, '', location.pathname + location.search); } catch (e) {}
    }
    if (ultimFocus && ultimFocus.focus) ultimFocus.focus();
  }

  stil();   // stilul linkurilor de pe numele donatorilor trebuie să existe de la început

  // clic pe orice nume de donator marcat cu data-fisa
  document.addEventListener('click', function (e) {
    var el = e.target.closest && e.target.closest('[data-fisa]');
    if (!el) return;
    e.preventDefault();
    deschide(el.getAttribute('data-fisa'));
  });

  function dinAdresa() {
    var m = /^#fisa=(.+)$/.exec(location.hash || '');
    if (!m) return;
    var n = decodeURIComponent(m[1]);
    if (typeof DONORS !== 'undefined' && DONORS.indexOf(n) === -1) {
      // numele poate veni cu altă scriere (diacritice, majuscule)
      var f = typeof foldOrg === 'function' ? foldOrg(n) : n.toLowerCase();
      var gasit = DONORS.filter(function (d) { return (typeof foldOrg === 'function' ? foldOrg(d) : d.toLowerCase()) === f; })[0];
      if (gasit) n = gasit;
    }
    deschide(n, true);
  }
  /* #cauta=… (din căutarea globală): lista de proiecte de pe pagina principală,
     filtrată după textul căutat, cu pagina derulată la ea. */
  function cautaDinAdresa() {
    var m = /^#cauta=(.+)$/.exec(location.hash || '');
    if (!m) return;
    var q = decodeURIComponent(m[1]);
    try { if (typeof showMainView === 'function' && document.getElementById('mainView').style.display === 'none') showMainView(); } catch (e) {}
    var inp = document.getElementById('projSearchInput');
    if (!inp) return;
    inp.value = q;
    inp.dispatchEvent(new Event('input', { bubbles: true }));
    var p = document.getElementById('projectsPanel');
    if (p) setTimeout(function () { p.scrollIntoView({ block: 'start' }); }, 50);
  }
  window.addEventListener('hashchange', cautaDinAdresa);
  if (document.readyState === 'complete') setTimeout(cautaDinAdresa, 400);
  else window.addEventListener('load', function () { setTimeout(cautaDinAdresa, 400); });

  window.addEventListener('hashchange', dinAdresa);
  if (document.readyState === 'complete') setTimeout(dinAdresa, 300);
  else window.addEventListener('load', function () { setTimeout(dinAdresa, 300); });

  // la schimbarea limbii, fișa deschisă se redesenează în limba nouă
  window.FisaDonator = { deschide: deschide, inchide: inchide, reface: function () { if (curent) deschide(curent, true); } };
})();
