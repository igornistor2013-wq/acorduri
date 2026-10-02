/* unelte.js — unelte adăugate peste pagina principală (index.html):
     · pe fiecare panou: „📋 Copiază" (imaginea panoului) și „⬇ CSV" (datele lui);
     · în antet: indicatorul de prospețime a datelor, „🔗 Copiază linkul" către
       selecția curentă și „📄 Raport PDF" pe o pagină;
     · în „Analize avansate": comparația între două perioade.
   Se încarcă ultimul, după toate scripturile paginii, și folosește funcțiile lor
   (getFilteredProjects, aggregateByDonor, donorLabel, fmtNum, linkSelectie …).
   html2canvas.min.js se încarcă abia la primul clic care are nevoie de el. */
(function(){
'use strict';

const en = () => (typeof currentLang !== 'undefined' && currentLang === 'en');
const L = (ro, eng) => en() ? eng : ro;

/* ---------------------------------------------------------------- stiluri */
const css = document.createElement('style');
css.textContent = `
  .panel-head{gap:8px;}
  .panel-head > h2{margin-right:auto;}
  .panel-head .unealta-panou{white-space:nowrap;}
  .panel-head .roata-panou{display:inline-flex;align-items:center;justify-content:center;gap:5px;min-width:34px;line-height:1;}
  .panel-head .roata-panou svg{display:block;transition:transform .25s ease;}
  .panel-head .roata-panou:hover svg, .panel-head .roata-panou.activ svg{transform:rotate(45deg);}
  .panel-head .roata-panou.activ{background:var(--navy);color:#fff;border-color:var(--navy);}
  .meniu-panou{position:fixed;z-index:10000;display:none;min-width:250px;padding:6px;background:var(--panel, #fff);
    border:1px solid var(--line-strong);border-radius:10px;box-shadow:0 12px 32px rgba(20,35,60,.18);}
  .meniu-panou.deschis{display:block;}
  .meniu-panou button{display:flex;align-items:flex-start;gap:10px;width:100%;text-align:left;background:none;border:none;
    border-radius:7px;padding:9px 11px;font:inherit;color:var(--ink);cursor:pointer;}
  .meniu-panou button:hover, .meniu-panou button:focus-visible{background:var(--blue-bg);outline:none;}
  .meniu-panou button + button{margin-top:2px;}
  .meniu-panou .mp-ico{font-size:15px;line-height:1.25;width:18px;text-align:center;flex:none;}
  .meniu-panou b{display:block;font-size:13px;font-weight:700;color:var(--navy);}
  .meniu-panou small{display:block;font-size:11.5px;color:var(--ink-dim);margin-top:2px;}
  @media (prefers-reduced-motion: reduce){.panel-head .roata-panou svg{transition:none;}}
  .panel-head .unealta-panou.ok, .unealta.ok{background:#16794f;color:#fff;border-color:#16794f;}
  .top-dreapta{display:flex;flex-direction:column;align-items:flex-end;gap:8px;}
  .unelte-sus{display:flex;flex-wrap:wrap;gap:6px;align-items:center;justify-content:flex-end;}
  .unealta{background:var(--panel);border:1px solid var(--line-strong);color:var(--navy);font:inherit;font-size:12px;
    font-weight:600;border-radius:7px;padding:6px 11px;cursor:pointer;white-space:nowrap;transition:.12s ease;}
  .unealta:hover{background:var(--navy);color:#fff;border-color:var(--navy);}
  .unealta:disabled{opacity:.65;cursor:progress;}
  .prospetime{display:inline-flex;align-items:center;gap:6px;font-size:11.5px;color:var(--ink-dim);padding:5px 10px;
    border-radius:999px;border:1px solid var(--line);background:var(--panel);white-space:nowrap;}
  .prospetime::before{content:'';width:8px;height:8px;border-radius:50%;background:#9aa3b5;flex:none;}
  .prospetime.p-ok::before{background:#1f9d5c;}
  .prospetime.p-warn::before{background:#d39b1a;}
  .prospetime.p-err::before{background:#c0392b;}
  .prospetime.p-load::before{background:#4d7ec2;animation:pPuls 1.2s ease-in-out infinite;}
  .prospetime:empty{display:none;}
  @keyframes pPuls{50%{opacity:.25}}
  @media (prefers-reduced-motion: reduce){.prospetime.p-load::before{animation:none;}}
  @media (max-width:800px){.top-dreapta{align-items:flex-start;}.unelte-sus{justify-content:flex-start;}}

  #cmpPanel .cmp-ctrl{display:flex;flex-wrap:wrap;gap:10px 22px;align-items:center;padding:12px 16px 2px;}
  #cmpPanel .cmp-per{display:flex;align-items:center;gap:6px;font-size:12.5px;color:var(--ink-dim);}
  #cmpPanel .cmp-per b{font-size:11px;text-transform:uppercase;letter-spacing:.05em;padding:3px 7px;border-radius:5px;}
  #cmpPanel .cmp-a b{background:#e8ebf1;color:#4b5567;}
  #cmpPanel .cmp-b b{background:var(--navy);color:#fff;}
  #cmpPanel select{font:inherit;font-size:12.5px;padding:4px 6px;border:1px solid var(--line-strong);border-radius:6px;
    background:var(--panel);color:var(--ink);}
  #cmpPanel .cmp-kpi{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:10px;margin-bottom:14px;}
  #cmpPanel .cmp-kpi > div{background:var(--blue-bg);border-radius:8px;padding:10px 12px;min-width:0;}
  #cmpPanel .cmp-kpi span{display:block;font-size:10.5px;color:var(--ink-dim);text-transform:uppercase;letter-spacing:.04em;}
  #cmpPanel .cmp-kpi b{display:block;font-size:18px;color:var(--navy-deep);font-variant-numeric:tabular-nums;margin-top:3px;white-space:nowrap;}
  #cmpPanel .cmp-kpi small{display:block;font-size:11.5px;color:var(--ink-dim);margin-top:2px;}
  #cmpPanel .cmp-sus{color:#16794f !important;}
  #cmpPanel .cmp-jos{color:#c0392b !important;}
  #cmpPanel .cmp-tab{width:100%;border-collapse:collapse;font-size:12.5px;}
  #cmpPanel .cmp-tab th{text-align:left;font-size:10.5px;text-transform:uppercase;letter-spacing:.04em;color:var(--ink-dim);
    padding:7px 8px;border-bottom:1px solid var(--line-strong);white-space:nowrap;}
  #cmpPanel .cmp-tab td{padding:6px 8px;border-bottom:1px solid var(--line);}
  #cmpPanel .cmp-tab .num{text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap;}
  #cmpPanel .cmp-nume{max-width:300px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;}
  #cmpPanel .cmp-bar{position:relative;height:12px;min-width:140px;}
  #cmpPanel .cmp-bar::after{content:'';position:absolute;left:50%;top:-3px;bottom:-3px;width:1px;background:var(--line-strong);}
  #cmpPanel .cmp-bar i{position:absolute;top:0;bottom:0;border-radius:3px;}
  #cmpPanel .cmp-scroll{overflow-x:auto;}
  @media (max-width:800px){#cmpPanel .cmp-kpi{grid-template-columns:repeat(2,minmax(0,1fr));}}
`;
document.head.appendChild(css);

/* -------------------------------------------------------- utilitare comune */
let lib = null;
function incarcaHtml2canvas(){
  if(window.html2canvas) return Promise.resolve();
  if(!lib) lib = new Promise((ok, fail) => {
    const s = document.createElement('script');
    s.src = 'html2canvas.min.js';
    s.onload = ok;
    s.onerror = () => { lib = null; fail(new Error('html2canvas nu s-a încărcat')); };
    document.head.appendChild(s);
  });
  return lib;
}
function dataAzi(){
  const d = new Date();
  return d.getFullYear() + '-' + String(d.getMonth() + 1).padStart(2, '0') + '-' + String(d.getDate()).padStart(2, '0');
}
function slug(s){
  return String(s || '').normalize('NFD').replace(/[\u0300-\u036f]/g, '')
    .toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-+|-+$/g, '').slice(0, 60) || 'date';
}
function descarca(blob, nume){
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = nume;
  document.body.appendChild(a); a.click(); a.remove();
  setTimeout(() => URL.revokeObjectURL(a.href), 4000);
}
/* Eticheta temporară a unui buton („✓ Copiat"), apoi revine singură. */
function eticheta(btn, text, implicit){
  btn.textContent = text;
  btn.classList.toggle('ok', text !== implicit());
  clearTimeout(btn._t);
  if(text !== implicit()) btn._t = setTimeout(() => { btn.textContent = implicit(); btn.classList.remove('ok'); }, 2200);
}
function titluPanou(panel){
  const h = panel.querySelector('.panel-head h2');
  if(!h) return '';
  const s = h.querySelector('[data-i18n], #cmpTitlu');
  return (s ? s.textContent : h.textContent).replace(/\s+/g, ' ').trim();
}

/* ============================================================ butoanele de pe panouri */
// panouri care nu sunt diagrame: filtre, export, antetul verificării IATI, tabelul de sub hartă
const EXCLUSE = ['mapCountryProjectsTitle', 'yearFilterTitle', 'donorFilterTitle', 'exportTitle',
                 'exportColumnsTitle', 'exportPreviewTitle', 'iatiCheckTitle'];
const ET = {
  ok:    () => L('✓ Copiat', '✓ Copied'),
  dl:    () => L('✓ Descărcat', '✓ Downloaded'),
  err:   () => L('✗ Eroare', '✗ Error'),
  gol:   () => L('Fără date', 'No data'),
  lucru: () => '⏳',
  roata: () => L('Opțiuni: copiază imaginea sau descarcă datele (CSV)', 'Options: copy the image or download the data (CSV)'),
  copy:  () => L('Copiază ca imagine', 'Copy as image'),
  copySub: () => L('PNG, gata de lipit în Word sau e-mail', 'PNG, ready to paste into Word or email'),
  csv:   () => L('Descarcă datele (CSV)', 'Download the data (CSV)'),
  csvSub:  () => L('sumele exacte · se deschide în Excel', 'exact amounts · opens in Excel')
};
/* Roata dințată (contur simplu, desenat cu stroke ca restul iconițelor din pagină) */
const ROATA = '<svg viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="currentColor" stroke-width="2" ' +
  'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false"><circle cx="12" cy="12" r="3"/>' +
  '<path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 ' +
  '1.51V21a2 2 0 1 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06a1.65 1.65 0 ' +
  '0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 1 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 ' +
  '2.83-2.83l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 1 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 ' +
  '1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 1 1 0 4h-.09a1.65 ' +
  '1.65 0 0 0-1.51 1z"/></svg>';

/* Pe roată arătăm pe scurt rezultatul („✓ Copiat"), apoi revine singură la iconiță. */
function rezultat(btn, text){
  clearTimeout(btn._t);
  btn.textContent = text;
  btn.classList.toggle('ok', text !== ET.lucru() && text !== ET.err());
  if(text === ET.lucru()) return;
  btn._t = setTimeout(() => { btn.innerHTML = ROATA; btn.classList.remove('ok'); }, 2200);
}

function imaginePanou(panel){
  return incarcaHtml2canvas().then(() => {
    /* Un panou poate avea sub diagramă un al doilea antet cu tabelul lui (harta are
       dedesubt „Proiectele țării selectate"); copiem doar partea de sus. */
    const ascunse = new Set(), capete = [...panel.children].filter(c => c.classList.contains('panel-head'));
    if(capete.length > 1){ let n = capete[1]; while(n){ ascunse.add(n); n = n.nextElementSibling; } }
    const bg = getComputedStyle(panel).backgroundColor;
    return window.html2canvas(panel, {
      backgroundColor: (bg && bg !== 'rgba(0, 0, 0, 0)') ? bg : '#ffffff',
      scale: Math.max(2, window.devicePixelRatio || 1), useCORS: true, logging: false,
      ignoreElements: el => ascunse.has(el) || (el.classList && el.classList.contains('unealta-panou'))
    });
  }).then(c => new Promise((ok, fail) => c.toBlob(b => b ? ok(b) : fail(new Error('imagine goală')), 'image/png')));
}

async function copiazaPanou(panel, btn){
  btn.disabled = true;
  rezultat(btn, ET.lucru());
  // promisiunea se dă direct lui ClipboardItem, în același clic — altfel Safari
  // refuză scrierea, pentru că randarea durează peste limita „gestului".
  const blob = imaginePanou(panel);
  try{
    if(!navigator.clipboard || !window.ClipboardItem) throw new Error('fără clipboard');
    await navigator.clipboard.write([new ClipboardItem({ 'image/png': blob })]);
    rezultat(btn, ET.ok());
  }catch(err){
    try{ descarca(await blob, slug(titluPanou(panel)) + '.png'); rezultat(btn, ET.dl()); }
    catch(e2){ console.warn('copiere panou:', err, e2); rezultat(btn, ET.err()); }
  }finally{ btn.disabled = false; }
}

/* --- CSV: separator „;", BOM UTF-8, sume întregi, zecimale cu virgulă — se deschide
   corect direct în Excel cu setări regionale românești (și în LibreOffice/Google Sheets). */
function celulaCsv(v){
  if(v === null || v === undefined) return '';
  if(typeof v === 'number'){
    if(!isFinite(v)) return '';
    return Number.isInteger(v) ? String(v) : String(Math.round(v * 100) / 100).replace('.', ',');
  }
  let s = String(v).replace(/\s+/g, ' ').trim();
  if(/^[=+@]/.test(s)) s = "'" + s;          // nu lăsăm Excel să interpreteze textul ca formulă
  if(/[";\n\r]/.test(s)) s = '"' + s.replace(/"/g, '""') + '"';
  return s;
}
function textCsv(cols, rows){
  return '\uFEFF' + [cols].concat(rows).map(r => r.map(celulaCsv).join(';')).join('\r\n') + '\r\n';
}
/* Rezervă pentru panourile fără date înregistrate: citim tabelul afișat. */
function numarDinText(s){
  s = String(s).replace(/\u00a0/g, ' ').trim();
  let m = s.match(/^(-?\d+(?:\.\d+)?)\s?%$/);
  if(m) return parseFloat(m[1]);
  if(en()){
    if(/^-?\d{1,3}(,\d{3})+(\.\d+)?$/.test(s) || /^-?\d+(\.\d+)?$/.test(s)) return parseFloat(s.replace(/,/g, ''));
  } else {
    if(/^-?\d{1,3}(\.\d{3})+(,\d+)?$/.test(s) || /^-?\d+(,\d+)?$/.test(s)) return parseFloat(s.replace(/\./g, '').replace(',', '.'));
  }
  return s;
}
function dinTabel(table){
  const text = el => {
    const tot = el.getAttribute('title') || (el.querySelector('[title]') && el.textContent.trim().endsWith('…') ? el.querySelector('[title]').getAttribute('title') : '');
    return (tot || el.textContent || '').replace(/\s+/g, ' ').trim();
  };
  const capete = table.tHead ? [...table.tHead.rows] : [];
  const cols = capete.length ? [...capete[capete.length - 1].cells].map(text) : [];
  const rows = [];
  [...table.tBodies].concat(table.tFoot ? [table.tFoot] : []).forEach(sec => {
    [...sec.rows].forEach(tr => {
      const cells = [...tr.cells];
      if(cells.length < 2 || tr.querySelector('.empty-state, .mai-proiecte')) return;
      rows.push(cells.map(td => numarDinText(text(td))));
    });
  });
  return rows.length ? { cols: cols, rows: rows } : null;
}
function dinBare(bare){
  const rows = [...bare].map(r => {
    const n = r.querySelector('.bname'), v = r.querySelector('.bar-val');
    return [n ? (n.getAttribute('title') || n.textContent).trim() : '', v ? numarDinText(v.textContent) : ''];
  });
  return rows.length ? { cols: [L('Nume', 'Name'), L('Valoare', 'Value')], rows: rows } : null;
}
function dateCsv(panel){
  if(panel.__dateCsv) return panel.__dateCsv;
  const tabele = [...panel.querySelectorAll('table')];
  const tab = tabele.find(tb => tb.offsetParent !== null) || tabele[0];
  if(tab){ const d = dinTabel(tab); if(d) return d; }
  const bare = panel.querySelectorAll('.bar-row');
  if(bare.length) return dinBare(bare);
  return null;
}
function csvPanou(panel, btn){
  if(window.__introRunning && typeof finishIntro === 'function') finishIntro();
  try{
    const d = dateCsv(panel);
    if(!d || !d.rows.length){ rezultat(btn, ET.gol()); return; }
    const blob = new Blob([textCsv(d.cols, d.rows)], { type: 'text/csv;charset=utf-8' });
    descarca(blob, slug(titluPanou(panel)) + '-' + dataAzi() + '.csv');
    rezultat(btn, ET.dl());
  }catch(err){ console.warn('CSV:', err); rezultat(btn, ET.err()); }
}

/* --- Meniul roții: unul singur pentru toată pagina, așezat în <body> cu poziție
   fixă, ca să nu fie tăiat de marginile rotunjite (overflow) ale panoului. */
let meniu = null, roataDeschisa = null;
function construiesteMeniu(){
  meniu = document.createElement('div');
  meniu.className = 'meniu-panou';
  meniu.setAttribute('role', 'menu');
  meniu.addEventListener('click', e => {
    const item = e.target.closest('[data-actiune]');
    if(!item || !roataDeschisa) return;
    const btn = roataDeschisa, panel = btn.closest('.panel');
    inchideMeniu(false);
    btn.focus();
    if(item.dataset.actiune === 'copiaza') copiazaPanou(panel, btn);
    else csvPanou(panel, btn);
  });
  meniu.addEventListener('keydown', e => {
    const iteme = [...meniu.querySelectorAll('[data-actiune]')];
    const i = iteme.indexOf(document.activeElement);
    if(e.key === 'ArrowDown'){ e.preventDefault(); iteme[(i + 1) % iteme.length].focus(); }
    else if(e.key === 'ArrowUp'){ e.preventDefault(); iteme[(i - 1 + iteme.length) % iteme.length].focus(); }
    else if(e.key === 'Tab'){ inchideMeniu(false); }
  });
  document.body.appendChild(meniu);
  // se închide la clic în afară, la Escape, la derulare sau la redimensionare
  document.addEventListener('click', e => {
    if(roataDeschisa && !meniu.contains(e.target) && !roataDeschisa.contains(e.target)) inchideMeniu(false);
  }, true);
  document.addEventListener('keydown', e => { if(e.key === 'Escape' && roataDeschisa) inchideMeniu(true); });
  window.addEventListener('scroll', () => { if(roataDeschisa) inchideMeniu(false); }, true);
  window.addEventListener('resize', () => { if(roataDeschisa) inchideMeniu(false); });
}
function deschideMeniu(btn, dinTastatura){
  if(!meniu) construiesteMeniu();
  const item = (act, ico, titlu, sub) =>
    '<button type="button" role="menuitem" data-actiune="' + act + '"><span class="mp-ico" aria-hidden="true">' + ico + '</span>' +
    '<span><b>' + esc(titlu) + '</b><small>' + esc(sub) + '</small></span></button>';
  meniu.innerHTML = item('copiaza', '📋', ET.copy(), ET.copySub()) + item('csv', '⬇', ET.csv(), ET.csvSub());
  meniu.classList.add('deschis');
  roataDeschisa = btn;
  btn.setAttribute('aria-expanded', 'true');
  btn.classList.add('activ');
  // sub roată, aliniat la dreapta ei; deasupra, dacă jos nu mai e loc
  const r = btn.getBoundingClientRect(), w = meniu.offsetWidth, hM = meniu.offsetHeight;
  let left = Math.min(r.right - w, window.innerWidth - w - 8);
  left = Math.max(8, left);
  let top = r.bottom + 6;
  if(top + hM > window.innerHeight - 8 && r.top - hM - 6 > 8) top = r.top - hM - 6;
  meniu.style.left = left + 'px';
  meniu.style.top = top + 'px';
  if(dinTastatura) meniu.querySelector('[data-actiune]').focus();
}
function inchideMeniu(focusPeRoata){
  if(!meniu || !roataDeschisa) return;
  const btn = roataDeschisa;
  meniu.classList.remove('deschis');
  btn.setAttribute('aria-expanded', 'false');
  btn.classList.remove('activ');
  roataDeschisa = null;
  if(focusPeRoata) btn.focus();
}
function laRoata(e){
  e.stopPropagation();
  const btn = e.currentTarget;
  if(btn.disabled) return;
  if(roataDeschisa === btn){ inchideMeniu(false); return; }
  if(roataDeschisa) inchideMeniu(false);
  // detail === 0: clic venit din tastatură (Enter / Space), deci mutăm focusul în meniu
  deschideMeniu(btn, e.detail === 0);
}

function butoanePanouri(){
  document.querySelectorAll('.panel > .panel-head').forEach(head => {
    const h2 = head.querySelector('h2');
    if(!h2 || head.querySelector('.unealta-panou')) return;
    const cheie = (h2.querySelector('[data-i18n]') || h2).getAttribute('data-i18n');
    if(EXCLUSE.includes(cheie)) return;
    // nu în grupurile segmentate (Angajamente | Debursări), ci într-un grup propriu
    let btns = [...head.children].find(c => c.classList.contains('btns') && !c.classList.contains('seg'));
    if(!btns){ btns = document.createElement('div'); btns.className = 'btns'; head.appendChild(btns); }
    const b = document.createElement('button');
    b.type = 'button';
    b.className = 'unealta-panou roata-panou';
    b.innerHTML = ROATA;
    b.title = ET.roata();
    b.setAttribute('aria-label', ET.roata());
    b.setAttribute('aria-haspopup', 'menu');
    b.setAttribute('aria-expanded', 'false');
    b.addEventListener('click', laRoata);
    btns.appendChild(b);
  });
}

/* ============================================================ antet: link + prospețime */
function textLink(){ return L('🔗 Copiază linkul', '🔗 Copy link'); }
function textPdf(){ return L('📄 Raport PDF', '📄 PDF report'); }

async function laLink(e){
  const btn = e.currentTarget;
  let url = location.href;
  try{ url = linkSelectie(); history.replaceState(history.state, '', url); }catch(err){}
  try{
    if(!navigator.clipboard || !navigator.clipboard.writeText) throw new Error('fără clipboard');
    await navigator.clipboard.writeText(url);
    eticheta(btn, L('✓ Link copiat', '✓ Link copied'), textLink);
  }catch(err){
    window.prompt(L('Linkul către selecția curentă:', 'Link to the current selection:'), url);
  }
}

window.renderProspetime = function(){
  const el = document.getElementById('prospetime');
  const st = (typeof lastStatus !== 'undefined') ? lastStatus : null;
  if(!el || !st) return;
  let cls, txt, tip;
  if(st.kind === 'loading'){
    cls = 'p-load'; txt = L('Se încarcă datele live AMP…', 'Loading live AMP data…');
    tip = L('Datele live se preiau din AMP la fiecare deschidere a paginii.', 'Live data is fetched from AMP every time the page opens.');
  } else if(st.kind === 'ok'){
    cls = 'p-ok'; txt = L('Date live AMP · ', 'Live AMP data · ') + __oraScurta(window.__liveLaOra);
    tip = L('Arhiva 1993–2022 completată cu raportul AMP live, preluat la deschiderea paginii.',
            'The 1993–2022 archive completed with the live AMP report, fetched when the page opened.');
  } else if(st.kind === 'warn'){
    cls = 'p-warn'; txt = L('Live AMP · sumele din arhivă', 'Live AMP · amounts from archive');
    tip = L('Raportul live a sosit fără coloane de sume recunoscute.', 'The live report arrived without recognisable amount columns.');
  } else {
    cls = 'p-err'; txt = L('Doar arhiva (1993–2022)', 'Archive only (1993–2022)');
    tip = (L('AMP nu a răspuns; cifrele nu includ actualizările live.', 'AMP did not respond; figures exclude live updates.') + __ultimaReusita()).trim();
  }
  el.className = 'prospetime ' + cls;
  el.textContent = txt;
  el.title = tip;
};

/* ============================================================ raport PDF pe o pagină */
/* Un PDF minimal scris de mână: o pagină A4 cu o singură imagine JPEG. Ocolim o
   bibliotecă PDF de sute de KB — și, mai important, fonturile ei standard, care nu
   au „ș", „ț", „ă": textul e desenat de browser, deci diacriticele ies corect. */
function pdfDinJpeg(jpeg, wPx, hPx, titlu, legatura){
  const enc = new TextEncoder(), parti = [], poz = [];
  let lung = 0;
  const pune = x => { const b = typeof x === 'string' ? enc.encode(x) : x; parti.push(b); lung += b.length; };
  const obiect = (n, corp) => { poz[n] = lung; pune(n + ' 0 obj\n' + corp + '\nendobj\n'); };
  const W = 595.28, H = 841.89;
  const hex16 = s => { let o = 'FEFF'; for(const ch of s){ const c = ch.codePointAt(0);
    if(c > 0xffff){ const v = c - 0x10000; o += (0xD800 + (v >> 10)).toString(16).padStart(4, '0') + (0xDC00 + (v & 1023)).toString(16).padStart(4, '0'); }
    else o += c.toString(16).padStart(4, '0'); } return '<' + o.toUpperCase() + '>'; };
  const continut = 'q ' + W + ' 0 0 ' + H + ' 0 0 cm /Im0 Do Q';
  const d = new Date(), p2 = n => String(n).padStart(2, '0');
  const dataPdf = 'D:' + d.getFullYear() + p2(d.getMonth() + 1) + p2(d.getDate()) + p2(d.getHours()) + p2(d.getMinutes()) + p2(d.getSeconds());

  pune('%PDF-1.4\n');
  pune(new Uint8Array([37, 226, 227, 207, 211, 10]));             // %âãÏÓ — marcaj de fișier binar
  obiect(1, '<< /Type /Catalog /Pages 2 0 R >>');
  obiect(2, '<< /Type /Pages /Kids [3 0 R] /Count 1 >>');
  const cuLink = !!(legatura && legatura.url && legatura.rect);
  obiect(3, '<< /Type /Page /Parent 2 0 R /MediaBox [0 0 ' + W + ' ' + H + '] ' +
            '/Resources << /XObject << /Im0 4 0 R >> /ProcSet [/PDF /ImageC] >> /Contents 5 0 R' +
            (cuLink ? ' /Annots [7 0 R]' : '') + ' >>');
  poz[4] = lung;
  pune('4 0 obj\n<< /Type /XObject /Subtype /Image /Width ' + wPx + ' /Height ' + hPx +
       ' /ColorSpace /DeviceRGB /BitsPerComponent 8 /Filter /DCTDecode /Length ' + jpeg.length + ' >>\nstream\n');
  pune(jpeg);
  pune('\nendstream\nendobj\n');
  obiect(5, '<< /Length ' + continut.length + ' >>\nstream\n' + continut + '\nendstream');
  obiect(6, '<< /Title ' + hex16(titlu) + ' /Producer (unelte.js) /CreationDate (' + dataPdf + ') >>');
  if(cuLink){
    const url = String(legatura.url).replace(/[^\x20-\x7e]/g, c => encodeURIComponent(c)).replace(/[\\()]/g, c => '\\' + c);
    obiect(7, '<< /Type /Annot /Subtype /Link /Rect [' + legatura.rect.map(v => v.toFixed(2)).join(' ') + '] /Border [0 0 0] ' +
              '/A << /S /URI /URI (' + url + ') >> >>');
  }
  const n = cuLink ? 8 : 7;
  const xref = lung;
  let x = 'xref\n0 ' + n + '\n0000000000 65535 f \n';
  for(let i = 1; i < n; i++) x += String(poz[i]).padStart(10, '0') + ' 00000 n \n';
  pune(x + 'trailer\n<< /Size ' + n + ' /Root 1 0 R /Info 6 0 R >>\nstartxref\n' + xref + '\n%%EOF\n');
  return new Blob(parti, { type: 'application/pdf' });
}

function aniText(){
  if(state.selectedYears.size === ALL_KEYS.size)
    return L('toți anii', 'all years') + (YEARS.length ? ' (' + YEARS[0] + '–' + YEARS[YEARS.length - 1] + ')' : '');
  return (__aniLaText(state.selectedYears) || '').replace(/-/g, '–').replace(/,/g, ', ').replace('NA', L('an nespecificat', 'year unspecified'));
}
function donatoriText(){
  const n = state.selectedDonors.size;
  if(n === DONORS.length) return L('toți donatorii', 'all donors') + ' (' + n + ')';
  if(n === 0) return L('niciun donator', 'no donor');
  const alesi = DONORS.filter(d => state.selectedDonors.has(d)).map(donorLabel);
  if(alesi.length <= 4) return alesi.join(', ');
  return n + ' ' + L('donatori selectați', 'selected donors') + ': ' + alesi.slice(0, 3).join(', ') + ' …';
}

function graficAni(peAn){
  const ani = [...peAn.keys()].sort((a, b) => a - b);
  const W = 1112, H = 230, sx = 64, jos = 26, sus = 8, ph = H - jos - sus;
  if(!ani.length) return '<div style="height:' + H + 'px;display:flex;align-items:center;justify-content:center;color:#7a8597;font-size:15px;">' +
    L('Nicio sumă cu an cunoscut în selecție.', 'No amounts with a known year in the selection.') + '</div>';
  const max = Math.max(1, ...ani.map(a => Math.max(peAn.get(a).ang, peAn.get(a).deb)));
  const pas = (W - sx) / ani.length, lb = Math.max(2, Math.min(18, pas * 0.36));
  const y = v => sus + ph - (v / max) * ph;
  let s = '<svg xmlns="http://www.w3.org/2000/svg" width="' + W + '" height="' + H + '" viewBox="0 0 ' + W + ' ' + H + '" style="display:block">';
  for(let i = 0; i <= 4; i++){
    const v = max * i / 4, yy = y(v);
    s += '<line x1="' + sx + '" x2="' + W + '" y1="' + yy + '" y2="' + yy + '" stroke="#e3e7ef"/>' +
         '<text x="' + (sx - 8) + '" y="' + (yy + 4) + '" text-anchor="end" font-size="12" fill="#6b7284">' + esc(fmtCompact(v)) + '</text>';
  }
  const fiecare = ani.length > 24 ? 2 : 1;
  ani.forEach((a, i) => {
    const o = peAn.get(a), x0 = sx + i * pas + (pas - 2 * lb - 2) / 2;
    s += '<rect x="' + x0 + '" y="' + y(o.ang) + '" width="' + lb + '" height="' + (sus + ph - y(o.ang)) + '" fill="#9db8df" rx="2"/>';
    s += '<rect x="' + (x0 + lb + 2) + '" y="' + y(o.deb) + '" width="' + lb + '" height="' + (sus + ph - y(o.deb)) + '" fill="#1E4B8C" rx="2"/>';
    if(i % fiecare === 0 || ani.length <= 24)
      s += '<text x="' + (sx + i * pas + pas / 2) + '" y="' + (H - 8) + '" text-anchor="middle" font-size="12" fill="#6b7284">' +
           (ani.length > 16 ? "'" + String(a).slice(2) : a) + '</text>';
  });
  return s + '</svg>';
}
function bareRaport(items, metric, eticheta){
  const max = Math.max(1, ...items.map(d => d[metric]));
  if(!items.length) return '<div style="color:#7a8597;font-size:14px;">—</div>';
  return items.map(d => '<div style="display:flex;align-items:center;gap:10px;margin:0 0 9px;">' +
    '<div style="width:250px;flex:none;font-size:14px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;color:#2a3446;">' + esc(eticheta(d.nume)) + '</div>' +
    '<div style="flex:1;height:14px;background:#e9eff8;border-radius:4px;overflow:hidden;"><div style="height:100%;width:' +
      Math.max(1, d[metric] / max * 100) + '%;background:#1E4B8C;border-radius:4px;"></div></div>' +
    '<div style="width:86px;flex:none;text-align:right;font-size:14px;font-weight:700;color:#14233c;font-variant-numeric:tabular-nums;">' + esc(fmtCompact(d[metric])) + '</div>' +
  '</div>').join('');
}

function htmlRaport(){
  const rows = getFilteredRows(), byDonor = aggregateByDonor(rows), proj = getFilteredProjects();
  const tot = { ang: proj.reduce((s, p) => s + p.ang, 0), deb: proj.reduce((s, p) => s + p.deb, 0),
                proj: countUniqueProjects(proj), don: byDonor.length };
  const mD = state2.donorMetric, mS = state2.sectorMetric, mB = state2.beneficiaryMetric;
  const topD = [...byDonor].filter(d => d.Angajamente || d.Debursari).sort((a, b) => b[mD] - a[mD]).slice(0, 10);
  const sect = aggregateBySector(proj).sort((a, b) => b[mS] - a[mS]).slice(0, 8);
  const ben = aggregateByBeneficiary(proj).sort((a, b) => b[mB] - a[mB]).slice(0, 8);
  const peAn = new Map();
  proj.forEach(p => { if(p.an === 'NA') return; const o = peAn.get(p.an) || { ang: 0, deb: 0 }; o.ang += p.ang; o.deb += p.deb; peAn.set(p.an, o); });
  const numeMetrica = m => (m === 'ang' || m === 'Angajamente') ? L('angajamente', 'commitments') : L('debursări', 'disbursements');
  const acum = new Date();
  const generat = String(acum.getDate()).padStart(2, '0') + '.' + String(acum.getMonth() + 1).padStart(2, '0') + '.' + acum.getFullYear() +
                  ', ' + String(acum.getHours()).padStart(2, '0') + ':' + String(acum.getMinutes()).padStart(2, '0');
  const st = (typeof lastStatus !== 'undefined' && lastStatus) ? lastStatus.kind : '';
  const sursaDate = st === 'ok'
    ? L('Arhiva AMP 1993–2022 + raportul AMP live, preluat ', 'AMP archive 1993–2022 + live AMP report, fetched ') + __oraScurta(window.__liveLaOra) + '.'
    : st === 'loading'
      ? L('Arhiva AMP 1993–2022 (datele live încă se încărcau la generare).', 'AMP archive 1993–2022 (live data was still loading).')
      : L('Doar arhiva AMP 1993–2022 — datele live nu au fost disponibile.', 'AMP archive 1993–2022 only — live data was unavailable.');
  let link = location.href;
  try{ link = linkSelectie(); }catch(e){}
  const scurt = u => { let s = u; try{ s = decodeURIComponent(u.replace(/\+/g, ' ')); }catch(e){} s = s.replace(/^https?:\/\//, ''); return s.length > 95 ? s.slice(0, 94) + '…' : s; };
  window.__raportLink = link;
  const kpi = (et, val, sub, cul) => '<div style="flex:1;background:#f3f6fb;border-radius:12px;padding:16px 18px;border-top:5px solid ' + cul + ';">' +
    '<div style="font-size:12.5px;text-transform:uppercase;letter-spacing:.06em;color:#6b7284;font-weight:700;">' + et + '</div>' +
    '<div style="font-size:31px;font-weight:800;color:#14233c;margin-top:6px;font-variant-numeric:tabular-nums;">' + val + '</div>' +
    '<div style="font-size:12.5px;color:#6b7284;margin-top:3px;font-variant-numeric:tabular-nums;">' + sub + '</div></div>';
  const titluSec = s => '<div style="font-size:16px;font-weight:800;color:#1E4B8C;text-transform:uppercase;letter-spacing:.05em;margin:0 0 12px;">' + s + '</div>';
  const th = 'style="text-align:right;padding:7px 8px;font-size:12px;text-transform:uppercase;letter-spacing:.04em;color:#6b7284;border-bottom:2px solid #d5dce8;"';
  const td = 'style="text-align:right;padding:7px 8px;font-size:14px;border-bottom:1px solid #e6eaf1;font-variant-numeric:tabular-nums;white-space:nowrap;"';
  return '' +
  '<div style="background:#14233c;color:#fff;margin:-48px -60px 26px;padding:34px 60px 28px;display:flex;justify-content:space-between;align-items:flex-end;gap:30px;">' +
    '<div><div style="font-size:14px;letter-spacing:.12em;text-transform:uppercase;color:#FFD200;font-weight:700;">' + L('Raport sintetic', 'Summary report') + '</div>' +
    '<div style="font-size:33px;font-weight:800;margin-top:6px;line-height:1.15;">' + L('Asistență externă pentru Republica Moldova', 'External assistance to the Republic of Moldova') + '</div></div>' +
    '<div style="text-align:right;font-size:13.5px;color:#c9d4e6;white-space:nowrap;">' + L('Generat', 'Generated') + ': ' + generat + '<br>' + esc(location.host || '') + '</div>' +
  '</div>' +
  '<div style="display:flex;gap:28px;font-size:15px;color:#2a3446;margin-bottom:20px;line-height:1.45;">' +
    '<div><b style="color:#6b7284;font-size:12.5px;text-transform:uppercase;letter-spacing:.05em;">' + L('Ani', 'Years') + '</b><br>' + esc(aniText()) + '</div>' +
    '<div style="flex:1;"><b style="color:#6b7284;font-size:12.5px;text-transform:uppercase;letter-spacing:.05em;">' + L('Donatori', 'Donors') + '</b><br>' + esc(donatoriText()) + '</div>' +
  '</div>' +
  '<div style="display:flex;gap:14px;margin-bottom:26px;">' +
    kpi(L('Angajamente', 'Commitments'), esc(fmtCompact(tot.ang)) + ' <span style="font-size:17px;color:#b8860b;">EUR</span>', esc(fmtNum(tot.ang)) + ' EUR', '#1E4B8C') +
    kpi(L('Debursări', 'Disbursements'), esc(fmtCompact(tot.deb)) + ' <span style="font-size:17px;color:#b8860b;">EUR</span>', esc(fmtNum(tot.deb)) + ' EUR', '#16794f') +
    kpi(L('Proiecte', 'Projects'), esc(fmtNum(tot.proj)), L('proiecte unice', 'unique projects'), '#b8860b') +
    kpi(L('Donatori activi', 'Active donors'), esc(String(tot.don)), L('în selecție', 'in selection'), '#CC092F') +
  '</div>' +
  titluSec(L('Evoluție după anul de început al proiectelor', 'By project start year') + ' <span style="font-weight:600;text-transform:none;letter-spacing:0;color:#6b7284;font-size:13.5px;">' +
    '<span style="display:inline-block;width:11px;height:11px;background:#9db8df;border-radius:2px;margin:0 5px 0 12px;"></span>' + L('angajamente', 'commitments') +
    '<span style="display:inline-block;width:11px;height:11px;background:#1E4B8C;border-radius:2px;margin:0 5px 0 14px;"></span>' + L('debursări', 'disbursements') + '</span>') +
  '<div style="margin-bottom:24px;">' + graficAni(peAn) + '</div>' +
  titluSec(L('Top 10 donatori', 'Top 10 donors') + ' · ' + numeMetrica(mD)) +
  '<table style="width:100%;border-collapse:collapse;margin-bottom:24px;"><thead><tr>' +
    '<th ' + th.replace('right', 'left') + '>#</th><th ' + th.replace('right', 'left') + '>' + L('Donator', 'Donor') + '</th>' +
    '<th ' + th + '>' + L('Proiecte', 'Projects') + '</th><th ' + th + '>' + L('Angajamente (EUR)', 'Commitments (EUR)') + '</th><th ' + th + '>' + L('Debursări (EUR)', 'Disbursements (EUR)') + '</th>' +
  '</tr></thead><tbody>' +
  (topD.length ? topD.map((d, i) => '<tr><td ' + td.replace('right', 'left') + '>' + (i + 1) + '</td>' +
    '<td style="padding:7px 8px;font-size:14px;border-bottom:1px solid #e6eaf1;max-width:560px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">' + esc(donorLabel(d.donator)) + '</td>' +
    '<td ' + td + '>' + esc(fmtNum(d.Proiecte)) + '</td><td ' + td + '>' + esc(fmtNum(d.Angajamente)) + '</td><td ' + td + '>' + esc(fmtNum(d.Debursari)) + '</td></tr>').join('')
    : '<tr><td colspan="5" style="padding:14px 8px;color:#7a8597;font-size:14px;">—</td></tr>') +
  '</tbody></table>' +
  '<div style="display:flex;gap:40px;">' +
    '<div style="flex:1;min-width:0;">' + titluSec(L('Sectoare', 'Sectors') + ' · ' + numeMetrica(mS)) + bareRaport(sect, mS, sectorLabel) + '</div>' +
    '<div style="flex:1;min-width:0;">' + titluSec(L('Beneficiari', 'Beneficiaries') + ' · ' + numeMetrica(mB)) + bareRaport(ben, mB, beneficiaryLabel) + '</div>' +
  '</div>' +
  '<div style="position:absolute;left:60px;right:60px;bottom:40px;border-top:1px solid #d5dce8;padding-top:14px;font-size:12.5px;color:#6b7284;line-height:1.55;">' +
    '<div>' + L('Sursă: platforma AMP (Aid Management Platform) a Republicii Moldova · sume în EUR. ', 'Source: the Republic of Moldova AMP (Aid Management Platform) · amounts in EUR. ') + esc(sursaDate) + '</div>' +
    '<div>' + L('Totalurile numără o singură dată proiectele cofinanțate; în tabelul de donatori, un proiect cofinanțat apare la fiecare donator.',
               'Totals count co-financed projects once; in the donor table, a co-financed project appears under each donor.') + '</div>' +
    '<div style="margin-top:6px;color:#1E4B8C;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;"><span id="raportLink" style="text-decoration:underline;">' +
      L('Deschide vederea online cu aceeași selecție', 'Open the online view with the same selection') + '</span> · ' + esc(scurt(link)) + '</div>' +
  '</div>';
}

async function laRaport(e){
  const btn = e.currentTarget;
  if(window.__introRunning && typeof finishIntro === 'function') finishIntro();
  btn.disabled = true;
  btn.textContent = L('⏳ Se generează…', '⏳ Generating…');
  let root = null;
  try{
    await incarcaHtml2canvas();
    const W = 1240, H = 1754;                                   // A4 la 150 dpi
    root = document.createElement('div');
    root.setAttribute('aria-hidden', 'true');
    root.style.cssText = 'position:fixed;left:-30000px;top:0;width:' + W + 'px;height:' + H + 'px;overflow:hidden;box-sizing:border-box;' +
      'padding:48px 60px;background:#fff;color:#14233c;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,"Helvetica Neue",Arial,sans-serif;';
    root.innerHTML = htmlRaport();
    document.body.appendChild(root);
    let legatura = null;
    const lk = root.querySelector('#raportLink');
    if(lk && window.__raportLink){
      const r0 = root.getBoundingClientRect(), r = lk.parentNode.getBoundingClientRect();
      const sx = 595.28 / W, sy = 841.89 / H;
      legatura = { url: window.__raportLink,
        rect: [(r.left - r0.left) * sx, 841.89 - (r.bottom - r0.top) * sy, (r.right - r0.left) * sx, 841.89 - (r.top - r0.top) * sy] };
    }
    const canvas = await window.html2canvas(root, { scale: 1.6, backgroundColor: '#ffffff', logging: false, width: W, height: H, windowWidth: W });
    const jpeg = await new Promise((ok, fail) => canvas.toBlob(b => b ? ok(b) : fail(new Error('imagine goală')), 'image/jpeg', 0.9));
    const bytes = new Uint8Array(await jpeg.arrayBuffer());
    const titlu = L('Raport sintetic — Asistență externă pentru Republica Moldova', 'Summary report — External assistance to the Republic of Moldova');
    descarca(pdfDinJpeg(bytes, canvas.width, canvas.height, titlu, legatura), L('raport-asistenta-externa-', 'external-assistance-report-') + dataAzi() + '.pdf');
    eticheta(btn, L('✓ Raport descărcat', '✓ Report downloaded'), textPdf);
  }catch(err){
    console.warn('raport PDF:', err);
    eticheta(btn, L('✗ Eroare la raport', '✗ Report failed'), textPdf);
  }finally{
    if(root) root.remove();
    btn.disabled = false;
  }
}

/* ============================================================ comparație între perioade */
/* baza: 'fin' = anul în care banii au fost efectiv angajați / debursați (anii financiari
   din AMP, câmpul y al fiecărui proiect); 'start' = anul de început al proiectului, cu
   toate sumele lui, ca în restul paginii. Pentru o comparație între perioade, anul
   financiar e cel corect: pe anul de început, perioadele recente par mereu mai mici,
   pentru că proiectele lor abia au început. */
const cmp = { m: 'deb', d: 'donor', baza: 'fin', a1: null, a2: null, b1: null, b2: null };

function aniFinanciari(){
  const s = new Set();
  (typeof ALL_RECORDS !== 'undefined' ? ALL_RECORDS : []).forEach(r => Object.keys(r.y || {}).forEach(k => {
    if(!/^\d{4}$/.test(k)) return;
    const v = r.y[k] || [], n = +k;
    if(n >= 1990 && n <= 2100 && ((v[0] || 0) || (v[1] || 0))) s.add(n);
  }));
  return [...s].sort((a, b) => a - b);
}
function aniDisponibili(){
  return cmp.baza === 'fin' ? aniFinanciari() : YEARS.filter(y => y !== 'NA').map(Number).sort((a, b) => a - b);
}
function perioadeImplicite(ani){
  const min = ani[0], max = ani[ani.length - 1];
  const b2 = Math.max(min, Math.min(max, new Date().getFullYear() - 1));   // ultimul an încheiat
  const b1 = Math.max(min, b2 - 2), a2 = Math.max(min, b1 - 1), a1 = Math.max(min, a2 - 2);
  return { a1: a1, a2: a2, b1: b1, b2: b2 };
}
function umple(id, ani, val){
  const s = document.getElementById(id);
  if(s) s.innerHTML = ani.map(y => '<option value="' + y + '"' + (y === val ? ' selected' : '') + '>' + y + '</option>').join('');
}
function intervalText(a, b){ return a === b ? String(a) : a + '–' + b; }
function semn(v, txt){ return (v > 0 ? '+' : v < 0 ? '−' : '') + txt; }

window.renderComparatie = function(){
  const body = document.getElementById('cmpBody');
  if(!body) return;
  const ani = aniDisponibili();
  etichetareComparatie();
  if(!ani.length){ body.innerHTML = '<div class="empty-state">' + esc(t('emptyCurrentSelection')) + '</div>'; return; }
  if(['a1', 'a2', 'b1', 'b2'].some(k => !ani.includes(cmp[k]))) Object.assign(cmp, perioadeImplicite(ani));
  umple('cmpA1', ani, cmp.a1); umple('cmpA2', ani, cmp.a2); umple('cmpB1', ani, cmp.b1); umple('cmpB2', ani, cmp.b2);
  const a1 = Math.min(cmp.a1, cmp.a2), a2 = Math.max(cmp.a1, cmp.a2), b1 = Math.min(cmp.b1, cmp.b2), b2 = Math.max(cmp.b1, cmp.b2);

  const chei = p => cmp.d === 'donor' ? p.donatori
    : cmp.d === 'sector' ? ((p.sectoare && p.sectoare.length) ? p.sectoare.map(s => s.nume) : ['Nespecificat'])
    : ((p.beneficiari && p.beneficiari.length) ? p.beneficiari : ['Nespecificat']);
  const etich = cmp.d === 'donor' ? donorLabel : cmp.d === 'sector' ? sectorLabel : beneficiaryLabel;
  const harta = new Map(), projA = new Set(), projB = new Set();
  let totA = 0, totB = 0;
  const adauga = (p, vA, vB, inA, inB) => {
    const cheie = p.id ? 'id:' + p.id : 'nm:' + p.denumire + '|' + p.donator;
    if(inA){ totA += vA; projA.add(cheie); }
    if(inB){ totB += vB; projB.add(cheie); }
    chei(p).forEach(k => {
      const o = harta.get(k) || { a: 0, b: 0 };
      if(inA) o.a += vA;
      if(inB) o.b += vB;
      harta.set(k, o);
    });
  };
  if(cmp.baza === 'fin'){
    // suma fiecărui an financiar merge în perioada în care cade anul — exact cum au curs banii
    const rec = new Map(ALL_RECORDS.map(r => [r.id, r]));
    const idx = cmp.m === 'ang' ? 0 : 1;
    PROJECTS.forEach(p => {
      const r = rec.get(p.id);
      if(!r || !r.y) return;
      let vA = 0, vB = 0;
      Object.keys(r.y).forEach(k => {
        if(!/^\d{4}$/.test(k)) return;
        const an = +k, val = Math.round((r.y[k] || [])[idx] || 0);
        if(!val) return;
        if(an >= a1 && an <= a2) vA += val;
        if(an >= b1 && an <= b2) vB += val;
      });
      if(vA || vB) adauga(p, vA, vB, !!vA, !!vB);
    });
  } else {
    PROJECTS.forEach(p => {
      if(p.an === 'NA') return;
      const inA = p.an >= a1 && p.an <= a2, inB = p.an >= b1 && p.an <= b2;
      if(!inA && !inB) return;
      const v = p[cmp.m] || 0;
      adauga(p, v, v, inA, inB);
    });
  }
  const randuri = [...harta.entries()].map(([k, o]) => ({ k: k, a: o.a, b: o.b, d: o.b - o.a }))
    .filter(r => r.a || r.b).sort((x, y) => Math.abs(y.d) - Math.abs(x.d));
  const varPct = (a, b) => a > 0 ? (b - a) / a * 100 : null;
  const etA = intervalText(a1, a2), etB = intervalText(b1, b2);
  const numeDim = cmp.d === 'donor' ? t('colDonor') : cmp.d === 'sector' ? 'Sector' : L('Beneficiar', 'Beneficiary');
  const numeM = cmp.m === 'ang' ? L('Angajamente', 'Commitments') : L('Debursări', 'Disbursements');

  __csvInreg(body, [numeDim, numeM + ' ' + etA + ' (EUR)', numeM + ' ' + etB + ' (EUR)', L('Diferență (EUR)', 'Difference (EUR)'), L('Variație (%)', 'Change (%)')],
    randuri.map(r => { const p = varPct(r.a, r.b); return [etich(r.k), Math.round(r.a), Math.round(r.b), Math.round(r.d), p === null ? '' : Math.round(p * 10) / 10]; }));

  const dif = totB - totA, pTot = varPct(totA, totB);
  const cls = v => v > 0 ? 'cmp-sus' : v < 0 ? 'cmp-jos' : '';
  const pctTxt = p => p === null ? L('nou', 'new') : semn(p, Math.abs(p).toFixed(1).replace('.', en() ? '.' : ',') + '%');
  let h = '<div class="cmp-kpi">' +
    '<div><span>' + L('Perioada A', 'Period A') + ' · ' + etA + '</span><b>' + esc(fmtCompact(totA)) + ' EUR</b><small>' + esc(fmtNum(projA.size)) + ' ' + L('proiecte', 'projects') + '</small></div>' +
    '<div><span>' + L('Perioada B', 'Period B') + ' · ' + etB + '</span><b>' + esc(fmtCompact(totB)) + ' EUR</b><small>' + esc(fmtNum(projB.size)) + ' ' + L('proiecte', 'projects') + '</small></div>' +
    '<div><span>' + L('Diferență', 'Difference') + '</span><b class="' + cls(dif) + '">' + esc(semn(dif, fmtCompact(Math.abs(dif)))) + ' EUR</b><small>' + esc(semn(dif, fmtNum(Math.abs(dif)))) + ' EUR</small></div>' +
    '<div><span>' + L('Variație', 'Change') + '</span><b class="' + cls(dif) + '">' + (totA > 0 ? esc(pctTxt(pTot)) : '—') + '</b><small>' + numeM.toLowerCase() + ', B ' + L('față de', 'vs') + ' A</small></div>' +
  '</div>';
  const top = randuri.slice(0, 15);
  if(!top.length){
    h += '<div class="empty-state">' + esc(t('emptyCurrentSelection')) + '</div>';
  } else {
    const maxD = Math.max(1, ...top.map(r => Math.abs(r.d)));
    h += '<div class="cmp-scroll"><table class="cmp-tab"><thead><tr><th>' + esc(numeDim) + '</th><th class="num">A · ' + etA + '</th><th class="num">B · ' + etB + '</th>' +
      '<th class="num">' + L('Diferență', 'Difference') + '</th><th class="num">' + L('Variație', 'Change') + '</th><th></th></tr></thead><tbody>' +
      top.map(r => {
        const w = Math.abs(r.d) / maxD * 50, p = varPct(r.a, r.b);
        const bara = r.d >= 0 ? 'left:50%;width:' + w + '%;background:#2f9e68;' : 'right:50%;width:' + w + '%;background:#d0574a;';
        return '<tr><td class="cmp-nume" title="' + esc(etich(r.k)) + '">' + esc(etich(r.k)) + '</td>' +
          '<td class="num">' + esc(fmtCompact(r.a)) + '</td><td class="num">' + esc(fmtCompact(r.b)) + '</td>' +
          '<td class="num ' + cls(r.d) + '">' + esc(semn(r.d, fmtCompact(Math.abs(r.d)))) + '</td>' +
          '<td class="num ' + cls(r.d) + '">' + esc(pctTxt(p)) + '</td>' +
          '<td style="width:24%"><div class="cmp-bar"><i style="' + bara + '"></i></div></td></tr>';
      }).join('') + '</tbody></table></div>';
  }
  body.innerHTML = h;

  const note = [];
  note.push(cmp.baza === 'fin'
    ? L('Sumele sunt puse pe anul în care au fost efectiv angajate sau debursate (anul financiar din AMP); „proiecte" = proiecte cu sume în perioadă.',
        'Amounts are placed in the year they were actually committed or disbursed (the AMP financial year); "projects" = projects with amounts in the period.')
    : L('Fiecare proiect intră cu toate sumele lui în anul de început, ca în restul paginii — perioadele recente par mai mici, pentru că proiectele lor încă debursează.',
        'Each project counts with all its amounts in its start year, as on the rest of the page — recent periods look smaller because their projects are still disbursing.'));
  note.push(L('Primele 15 după diferența absolută; din ⚙ se descarcă lista completă (CSV).', 'Top 15 by absolute difference; the ⚙ menu downloads the full list (CSV).'));
  if((a2 - a1) !== (b2 - b1)) note.push(L('Perioadele au lungimi diferite (' + (a2 - a1 + 1) + ' vs ' + (b2 - b1 + 1) + ' ani) — se compară sume totale, nu medii anuale.',
                                          'The periods differ in length (' + (a2 - a1 + 1) + ' vs ' + (b2 - b1 + 1) + ' years) — totals are compared, not yearly averages.'));
  if(Math.max(a2, b2) >= new Date().getFullYear()) note.push(L('Anul ' + new Date().getFullYear() + ' e în curs, deci datele lui sunt incomplete.',
                                                               new Date().getFullYear() + ' is still under way, so its data is incomplete.'));
  note.push(cmp.d === 'donor'
    ? L('Un proiect cofinanțat apare cu suma întreagă la fiecare donator; totalurile de sus îl numără o singură dată.',
        'A co-financed project appears with its full amount under each donor; the totals above count it once.')
    : cmp.d === 'sector'
      ? L('Un proiect cu mai multe sectoare apare la fiecare sector; totalurile de sus îl numără o singură dată.',
          'A project with several sectors appears under each sector; the totals above count it once.')
      : L('Un proiect cu mai mulți beneficiari apare la fiecare beneficiar; totalurile de sus îl numără o singură dată.',
          'A project with several beneficiaries appears under each beneficiary; the totals above count it once.'));
  const nota = document.getElementById('cmpNota');
  if(nota) nota.textContent = note.join(' ');
};

function etichetareComparatie(){
  const set = (id, txt) => { const el = document.getElementById(id); if(el) el.textContent = txt; };
  set('cmpTitlu', L('Comparație între perioade', 'Period comparison'));
  set('cmpEtA', L('Perioada A', 'Period A'));
  set('cmpEtB', L('Perioada B', 'Period B'));
  const seg = (sel, attr, val, txt) => { const b = document.querySelector(sel + ' [' + attr + '="' + val + '"]'); if(b){ b.textContent = txt; } };
  seg('#cmpMetrica', 'data-m', 'ang', L('Angajamente', 'Commitments'));
  seg('#cmpMetrica', 'data-m', 'deb', L('Debursări', 'Disbursements'));
  seg('#cmpDim', 'data-d', 'donor', L('Donatori', 'Donors'));
  seg('#cmpDim', 'data-d', 'sector', L('Sectoare', 'Sectors'));
  seg('#cmpDim', 'data-d', 'benef', L('Beneficiari', 'Beneficiaries'));
  seg('#cmpBaza', 'data-b', 'fin', L('An financiar', 'Financial year'));
  seg('#cmpBaza', 'data-b', 'start', L('An de început', 'Start year'));
  document.querySelectorAll('#cmpBaza button').forEach(b => {
    b.setAttribute('aria-pressed', String(b.dataset.b === cmp.baza));
    b.title = b.dataset.b === 'fin'
      ? L('Banii, în anul în care au fost angajați sau debursați', 'Money in the year it was committed or disbursed')
      : L('Toate sumele proiectului, în anul lui de început (ca în restul paginii)', 'All project amounts in its start year (as on the rest of the page)');
  });
  document.querySelectorAll('#cmpMetrica button').forEach(b => b.setAttribute('aria-pressed', String(b.dataset.m === cmp.m)));
  document.querySelectorAll('#cmpDim button').forEach(b => b.setAttribute('aria-pressed', String(b.dataset.d === cmp.d)));
}

function legaComparatia(){
  const p = document.getElementById('cmpPanel');
  if(!p) return;
  ['A1', 'A2', 'B1', 'B2'].forEach(k => {
    const s = document.getElementById('cmp' + k);
    if(s) s.addEventListener('change', () => { cmp[k.toLowerCase()] = +s.value; window.renderComparatie(); });
  });
  p.querySelectorAll('#cmpMetrica button').forEach(b => b.addEventListener('click', () => { cmp.m = b.dataset.m; window.renderComparatie(); }));
  p.querySelectorAll('#cmpDim button').forEach(b => b.addEventListener('click', () => { cmp.d = b.dataset.d; window.renderComparatie(); }));
  p.querySelectorAll('#cmpBaza button').forEach(b => b.addEventListener('click', () => { cmp.baza = b.dataset.b; window.renderComparatie(); }));
  etichetareComparatie();
}

/* ============================================================ pornire + limba */
window.__unelteLimba = function(){
  document.querySelectorAll('.roata-panou').forEach(b => { b.title = ET.roata(); b.setAttribute('aria-label', ET.roata()); });
  if(roataDeschisa) inchideMeniu(false);
  const bl = document.getElementById('btnLinkSelectie'), bp = document.getElementById('btnRaportPdf');
  if(bl && !bl.classList.contains('ok')){ bl.textContent = textLink(); }
  if(bl) bl.title = L('Copiază un link care deschide pagina cu exact aceiași ani și donatori', 'Copy a link that opens the page with exactly these years and donors');
  if(bp && !bp.disabled && !bp.classList.contains('ok')){ bp.textContent = textPdf(); }
  if(bp) bp.title = L('Descarcă un raport PDF de o pagină pentru selecția curentă', 'Download a one-page PDF report for the current selection');
  etichetareComparatie();
  window.renderProspetime();
};

function porneste(){
  butoanePanouri();
  const bl = document.getElementById('btnLinkSelectie'), bp = document.getElementById('btnRaportPdf');
  if(bl) bl.addEventListener('click', laLink);
  if(bp) bp.addEventListener('click', laRaport);
  legaComparatia();
  window.__unelteLimba();
  // dacă „Analize avansate" era deja deschisă (link direct la #analize), desenăm acum comparația
  if(typeof __advInitialized !== 'undefined' && __advInitialized) window.renderComparatie();
}
if(document.readyState === 'loading') document.addEventListener('DOMContentLoaded', porneste);
else porneste();
})();
