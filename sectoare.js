/* „Donatori → sectoare” cu proiectele fiecărui sector — panou din „Analize avansate”.
   ------------------------------------------------------------------
   Ce arată:
     1. o diagramă cu donatorii în stânga și sectoarele în dreapta. Lungimea barei = totalul donatorului sau al
        sectorului, cu fiecare proiect numărat o singură dată (deci cifrele coincid cu „Top donatori” și cu panoul
        „Distribuție pe sectoare” din pagina principală); grosimea liniei dintre ei = suma proiectelor acelui donator în acel sector.
     2. dedesubt, lista proiectelor pe fiecare sector. Un clic pe un donator, pe un sector sau pe o linie din
        diagramă filtrează lista.

   De ce bare și linii, nu un Sankey: un proiect cu mai multe sectoare apare cu suma întreagă în fiecare dintre ele
   (așa numără tot dashboardul). Într-un Sankey, înălțimea unui donator ar fi suma liniilor lui, deci mai mare decât totalul
   lui real (FMI: 1.213 mil în loc de 660 mil). Cu bare separate, totalurile rămân cele adevărate, iar liniile spun doar
   „cât din banii donatorului merge în sectorul acela”.

   Fișierul are două părți. Prima (agregări, filtre, construirea diagramei ca text SVG și a datelor pentru Excel) nu
   atinge pagina și se testează în Node (teste_sectoare.py). A doua desenează în pagină și pune evenimentele.
   Se încarcă după scriptul principal din index.html, care îi dă datele (PROJECTS) și funcțiile de etichetare. */
(function(){
'use strict';

const ALTII = '§alti§', ALTE = '§alte§';          // chei rezervate pentru nodurile „Alți donatori” / „Alte sectoare”
const FARA_SECTOR = 'Nespecificat';                 // cheia proiectelor fără sector (ca în celelalte panouri)
const SEP = '\u0002';

/* ======================================================================== 1. PARTEA PURĂ */

const cmpText = (a, b) => a < b ? -1 : a > b ? 1 : 0;

/* Un proiect = un rând (PROJECTS are deja unul singur, dar îl strângem după AMP ID ca să fim siguri). Sectoarele devin
   liste de denumiri; fără sector, proiectul intră la „Nespecificat”. */
function unice(proiecte){
  const m = new Map();
  (proiecte || []).forEach(p => {
    const k = p.id ? 'id:' + p.id : 'nm:' + p.denumire + '|' + p.donator;
    let g = m.get(k);
    if(!g){ g = { k: k, id: p.id || '', ref: p, an: p.an, ang: 0, deb: 0, donatori: [], sectoare: [] }; m.set(k, g); }
    g.ang += p.ang || 0; g.deb += p.deb || 0;
    if(p.an !== 'NA' && (g.an === 'NA' || g.an === undefined || p.an < g.an)) g.an = p.an;
    (p.donatori && p.donatori.length ? p.donatori : [p.donator]).forEach(d => { if(d && g.donatori.indexOf(d) < 0) g.donatori.push(d); });
    (p.sectoare || []).forEach(s => { const nume = s && (s.nume || s); if(nume && g.sectoare.indexOf(nume) < 0) g.sectoare.push(nume); });
  });
  const out = [...m.values()];
  out.forEach(g => { if(!g.sectoare.length) g.sectoare.push(FARA_SECTOR); if(!g.donatori.length) g.donatori.push('—'); });
  return out;
}

/* Perioada = anul de început al proiectului. Proiectele fără an (NA) intră doar când nu e aleasă nicio perioadă. */
function dinPerioada(lista, de, pana){
  de = +de || 0; pana = +pana || 0;
  if(!de && !pana) return lista;
  return lista.filter(p => p.an !== 'NA' && p.an !== undefined && (!de || p.an >= de) && (!pana || p.an <= pana));
}

function agrega(lista, o){
  o = o || {};
  const m = o.metric === 'deb' ? 'deb' : 'ang';
  const nD = o.nD > 0 ? o.nD : 12, nS = o.nS > 0 ? o.nS : 30;
  const donori = new Map(), sectoare = new Map(), dS = new Map(), sD = new Map();
  const adauga = (mp, k, p) => { let x = mp.get(k); if(!x){ x = { cheie: k, ang: 0, deb: 0, n: 0 }; mp.set(k, x); } x.ang += p.ang; x.deb += p.deb; x.n++; };
  const leaga = (mp, k, alte) => { let s = mp.get(k); if(!s){ s = new Set(); mp.set(k, s); } alte.forEach(x => s.add(x)); };
  let ang = 0, deb = 0, aparitii = 0;
  lista.forEach(p => {
    ang += p.ang; deb += p.deb; aparitii += p.sectoare.length;
    p.donatori.forEach(d => { adauga(donori, d, p); leaga(dS, d, p.sectoare); });
    p.sectoare.forEach(s => { adauga(sectoare, s, p); leaga(sD, s, p.donatori); });
  });
  const ordine = (a, b) => (b[m] - a[m]) || (b.n - a.n) || cmpText(a.cheie, b.cheie);
  const toti = [...donori.values()].sort(ordine), toate = [...sectoare.values()].sort(ordine);
  /* Nodurile afișate: primele n după măsură (fără cele cu 0) + cele care trebuie să se vadă oricum (selecția curentă). */
  const alege = (arr, n, fixe) => {
    const top = arr.filter(x => x[m] > 0).slice(0, n).map(x => x.cheie);
    (fixe || []).forEach(k => { if(k && k !== ALTII && k !== ALTE && arr.some(x => x.cheie === k) && top.indexOf(k) < 0) top.push(k); });
    top.sort((a, b) => ordine(arr.find(x => x.cheie === a), arr.find(x => x.cheie === b)));
    return top;
  };
  const topD = alege(toti, nD, o.fixD), topS = alege(toate, nS, o.fixS);
  const setD = new Set(topD), setS = new Set(topS);
  const altiD = new Set(toti.filter(x => !setD.has(x.cheie)).map(x => x.cheie));
  const alteS = new Set(toate.filter(x => !setS.has(x.cheie)).map(x => x.cheie));
  const alD = { cheie: ALTII, alt: true, nr: altiD.size, ang: 0, deb: 0, n: 0, leg: new Set() };
  const alS = { cheie: ALTE, alt: true, nr: alteS.size, ang: 0, deb: 0, n: 0, leg: new Set() };
  const leg = new Map();
  lista.forEach(p => {
    const ds = new Set(), ss = new Set();
    p.donatori.forEach(d => ds.add(setD.has(d) ? d : ALTII));
    p.sectoare.forEach(s => ss.add(setS.has(s) ? s : ALTE));
    if(ds.has(ALTII)){ alD.ang += p.ang; alD.deb += p.deb; alD.n++; p.sectoare.forEach(s => alD.leg.add(s)); }
    if(ss.has(ALTE)){ alS.ang += p.ang; alS.deb += p.deb; alS.n++; p.donatori.forEach(d => alS.leg.add(d)); }
    ds.forEach(d => ss.forEach(s => {
      const k = d + SEP + s;
      let x = leg.get(k);
      if(!x){ x = { d: d, s: s, ang: 0, deb: 0, n: 0 }; leg.set(k, x); }
      x.ang += p.ang; x.deb += p.deb; x.n++;
    }));
  });
  const nod = (cheie, mp, legat) => { const x = mp.get(cheie); return { cheie: cheie, alt: false, ang: x.ang, deb: x.deb, n: x.n, nrLegat: legat.get(cheie).size }; };
  const nodD = topD.map(k => nod(k, donori, dS)), nodS = topS.map(k => nod(k, sectoare, sD));
  if(alD.n && alD[m] > 0){ alD.nrLegat = alD.leg.size; nodD.push(alD); }
  if(alS.n && alS[m] > 0){ alS.nrLegat = alS.leg.size; nodS.push(alS); }
  const legaturi = [...leg.values()].filter(x => x[m] > 0).sort((a, b) => (b[m] - a[m]) || (b.n - a.n) || cmpText(a.d + a.s, b.d + b.s));
  return { metric: m, total: { proiecte: lista.length, ang: ang, deb: deb }, aparitii: aparitii,
           donatori: toti, sectoare: toate, nodD: nodD, nodS: nodS, legaturi: legaturi, altiD: altiD, alteS: alteS };
}

/* Selecția din diagramă: un donator (sau „Alți donatori”) și/sau un sector (sau „Alte sectoare”). */
function potrivesteDonator(d, sel, agr){
  if(!sel) return true;
  if(sel === ALTII) return agr.altiD.has(d);
  return d === sel;
}
function potrivesteSector(s, sel, agr){
  if(!sel) return true;
  if(sel === ALTE) return agr.alteS.has(s);
  return s === sel;
}
function perechi(lista, sel, agr){
  sel = sel || {};
  const out = [];
  lista.forEach(p => {
    if(sel.donator && !p.donatori.some(d => potrivesteDonator(d, sel.donator, agr))) return;
    p.sectoare.forEach(s => { if(potrivesteSector(s, sel.sector, agr)) out.push({ p: p, s: s }); });
  });
  return out;
}

/* Lista pe sectoare: un grup pe sector, cu proiectele lui (cele mai mari întâi) și donatorii lui principali. */
function peSectoare(lista, o){
  const m = o.metric === 'deb' ? 'deb' : 'ang';
  const grupe = new Map();
  perechi(lista, o.sel, o.agr).forEach(({ p, s }) => {
    let g = grupe.get(s);
    if(!g){ g = { cheie: s, n: 0, ang: 0, deb: 0, proiecte: [], dn: new Map() }; grupe.set(s, g); }
    g.n++; g.ang += p.ang; g.deb += p.deb; g.proiecte.push(p);
    p.donatori.forEach(d => { const x = g.dn.get(d) || { cheie: d, ang: 0, deb: 0, n: 0 }; x.ang += p.ang; x.deb += p.deb; x.n++; g.dn.set(d, x); });
  });
  const out = [...grupe.values()];
  out.forEach(g => {
    g.proiecte.sort((a, b) => (b[m] - a[m]) || (b.ang - a.ang) || cmpText(String(a.id), String(b.id)));
    g.donatori = [...g.dn.values()].sort((a, b) => (b[m] - a[m]) || (b.n - a.n) || cmpText(a.cheie, b.cheie));
    delete g.dn;
  });
  out.sort((a, b) => (b[m] - a[m]) || (b.n - a.n) || cmpText(a.cheie, b.cheie));
  return out;
}

/* Totalul „adevărat” al grupurilor: fiecare proiect o singură dată. */
function totalGrupe(grupe){
  const vazute = new Set(); let ang = 0, deb = 0, aparitii = 0;
  grupe.forEach(g => { aparitii += g.n; g.proiecte.forEach(p => { if(!vazute.has(p.k)){ vazute.add(p.k); ang += p.ang; deb += p.deb; } }); });
  return { proiecte: vazute.size, ang: ang, deb: deb, aparitii: aparitii, sectoare: grupe.length };
}

/* Donator × sector, doar cu ce intră în selecție. Fiecare celulă = suma proiectelor care au și donatorul, și sectorul. */
function matrice(lista, o){
  const m = o.metric === 'deb' ? 'deb' : 'ang', sel = o.sel || {}, agr = o.agr;
  const cel = new Map(), dT = new Map(), sT = new Map();
  lista.forEach(p => {
    const ds = p.donatori.filter(d => potrivesteDonator(d, sel.donator, agr)), ss = p.sectoare.filter(s => potrivesteSector(s, sel.sector, agr));
    if(!ds.length || !ss.length) return;
    ds.forEach(d => { dT.set(d, (dT.get(d) || 0) + p[m]); ss.forEach(s => { const k = d + SEP + s; cel.set(k, (cel.get(k) || 0) + p[m]); }); });
    ss.forEach(s => sT.set(s, (sT.get(s) || 0) + p[m]));
  });
  const ord = mp => [...mp.entries()].map(([cheie, total]) => ({ cheie: cheie, total: total })).filter(x => x.total > 0)
    .sort((a, b) => (b.total - a.total) || cmpText(a.cheie, b.cheie));
  return { donatori: ord(dT), sectoare: ord(sT), cel: cel };
}

/* ---------- diagrama, ca text SVG ----------
   Culorile și dimensiunile sunt scrise ca atribute (nu în CSS) ca să se vadă la fel și în imaginea copiată din meniul ⚙.
   o: { sel:{donator,sector}, etD(cheie), etS(cheie), fmt(v), esc(s), L(ro,en), en, titluD, titluS } */
const GEO = { W: 1180, LX: 240, DBX: 250, DAX: 420, SAX: 740, SBX: 750, SLX: 912, BMAX: 100, TOP: 40, BOT: 14, PS: 22, PDMIN: 30, TMAX: 20, TMIN: 1.2 };
const CUL = { donor: '#22406b', sector: '#c8871a', donorAlt: '#9db8df', sectorAlt: '#e6c689', ink: '#1c2230', dim: '#6b7284', banda: '#eaf0fb', linie: '#22406b' };
const FONT = "-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,'Helvetica Neue',Arial,sans-serif";

function taie(s, n){ s = String(s == null ? '' : s); return s.length > n ? s.slice(0, n - 1).trimEnd() + '…' : s; }
/* Cuvântul la forma potrivită numărului: „1 proiect”, „2 proiecte”, „20 de proiecte” (în română, de la 20 și la sute
   rotunde se pune „de”); „1 project”, „2 projects” în engleză. */
function cuvant(n, en, sgRo, plRo, sgEn, plEn){
  n = +n || 0;
  if(en) return n === 1 ? sgEn : plEn;
  if(n === 1) return sgRo;
  const m = n % 100;
  return (n > 0 && (m === 0 || m >= 20) ? 'de ' : '') + plRo;
}
const numar = (n, en, sgRo, plRo, sgEn, plEn, fmt) => (fmt ? fmt(+n || 0) : String(+n || 0)) + ' ' + cuvant(n, en, sgRo, plRo, sgEn, plEn);
const rot = v => Math.round(v * 10) / 10;

/* Ce linii, ce rânduri sunt „în focus” când se alege/trece cursorul peste un donator (d), un sector (s) sau o linie (d și s). */
function focus(agr, f){
  f = f || {};
  const d = f.d == null ? null : f.d, s = f.s == null ? null : f.s;
  if(d === null && s === null) return null;
  const linii = new Set(), rd = new Set(), rs = new Set();
  agr.legaturi.forEach((l, i) => {
    if((d === null || l.d === d) && (s === null || l.s === s)){ linii.add(i); rd.add(l.d); rs.add(l.s); }
  });
  if(d !== null) rd.add(d);
  if(s !== null) rs.add(s);
  return { linii: linii, donatori: rd, sectoare: rs };
}

function diagramaSvg(agr, o){
  const g = GEO, esc = o.esc || (x => String(x)), fmt = o.fmt || (x => String(Math.round(x)));
  const m = agr.metric, nD = agr.nodD.length, nS = agr.nodS.length;
  const corp = Math.max(nS * g.PS, nD * g.PDMIN, g.PS);
  const H = g.TOP + corp + g.BOT;
  const pD = corp / Math.max(nD, 1), pS = corp / Math.max(nS, 1);
  const yD = i => g.TOP + (i + 0.5) * pD, yS = i => g.TOP + (i + 0.5) * pS;
  const iD = new Map(agr.nodD.map((x, i) => [x.cheie, i])), iS = new Map(agr.nodS.map((x, i) => [x.cheie, i]));
  const maxN = Math.max(1, ...agr.nodD.map(x => x[m]), ...agr.nodS.map(x => x[m]));
  const maxL = Math.max(1, ...agr.legaturi.map(l => l[m]));
  const lungime = v => Math.max(2, v / maxN * g.BMAX);
  const gros = v => Math.max(g.TMIN, v / maxL * g.TMAX);
  const sel = o.sel || {};
  const sD = sel.donator ? (iD.has(sel.donator) ? iD.get(sel.donator) : null) : null;
  const sS = sel.sector ? (iS.has(sel.sector) ? iS.get(sel.sector) : null) : null;
  const f = focus({ legaturi: agr.legaturi.map(l => ({ d: iD.get(l.d), s: iS.get(l.s) })) }, o.focus || { d: sD, s: sS });
  const fam = FONT;
  let h = '';
  const antet = (x, ancora, text) => '<text x="' + x + '" y="16" text-anchor="' + ancora + '" font-family="' + fam + '" font-size="10.5" font-weight="700" letter-spacing=".06em" fill="' + CUL.dim + '">' + esc(text) + '</text>';
  h += antet(g.LX, 'end', String(o.titluD || '').toUpperCase()) + antet(g.SLX, 'start', String(o.titluS || '').toUpperCase());

  /* liniile: întâi cele groase, ca cele subțiri să rămână deasupra */
  let legH = '', hitH = '';
  agr.legaturi.forEach((l, k) => {
    const a = iD.get(l.d), b = iS.get(l.s);
    if(a === undefined || b === undefined) return;
    const x1 = g.DAX, y1 = yD(a), x2 = g.SAX, y2 = yS(b), xm = (x1 + x2) / 2;
    const d = 'M' + x1 + ',' + rot(y1) + ' C' + xm + ',' + rot(y1) + ' ' + xm + ',' + rot(y2) + ' ' + x2 + ',' + rot(y2);
    const w = rot(gros(l[m]));
    const aprins = f ? f.linii.has(k) : false;
    const op = f ? (aprins ? 0.78 : 0.06) : 0.2;
    legH += '<path class="sdg-link" data-l="' + k + '" d="' + d + '" fill="none" stroke="' + CUL.linie + '" stroke-opacity="' + op + '" stroke-width="' + w + '"/>';
    hitH += '<path class="sdg-hit" data-l="' + k + '" data-d="' + a + '" data-s="' + b + '" d="' + d + '" fill="none" stroke="transparent" stroke-width="' + Math.max(w, 12) + '" style="cursor:pointer"/>';
  });
  h += '<g class="sdg-legaturi">' + legH + '</g>';

  /* donatorii */
  let rd = '';
  agr.nodD.forEach((x, i) => {
    const y = yD(i), pe = sD === i, rel = f ? f.donatori.has(i) : false;
    const eticheta = o.etD(x.cheie);
    const len = lungime(x[m]), cul = x.alt ? CUL.donorAlt : CUL.donor;
    const aria = eticheta + ', ' + fmt(x[m]) + ' EUR, ' + numar(x.n, o.en, 'proiect', 'proiecte', 'project', 'projects') + (pe ? ', ' + o.L('selectat', 'selected') : '');
    rd += '<g class="sdg-row sdg-d" data-d="' + i + '" tabindex="0" role="button" aria-pressed="' + (pe ? 'true' : 'false') + '" aria-label="' + esc(aria) + '" style="cursor:pointer;outline:none">' +
      '<rect class="hit" x="0" y="' + rot(y - pD / 2) + '" width="' + g.DAX + '" height="' + rot(pD) + '" rx="4" fill="' + (pe ? CUL.banda : (rel && f ? 'rgba(34,64,107,.05)' : 'transparent')) + '"/>' +
      '<text class="nm" x="' + g.LX + '" y="' + rot(y) + '" text-anchor="end" dominant-baseline="central" font-family="' + fam + '" font-size="11.5" font-weight="' + (pe || (rel && f) ? 700 : 400) + '" fill="' + CUL.ink + '">' + esc(taie(eticheta, 38)) + '</text>' +
      '<rect class="bar" x="' + g.DBX + '" y="' + rot(y - 7) + '" width="' + rot(len) + '" height="14" rx="3" fill="' + cul + '"/>' +
      '<text class="val" x="' + rot(g.DBX + len + 6) + '" y="' + rot(y) + '" dominant-baseline="central" font-family="' + fam + '" font-size="10.5" fill="' + CUL.dim + '">' + esc(fmt(x[m])) + '</text>' +
      '<circle class="dot" cx="' + g.DAX + '" cy="' + rot(y) + '" r="3.5" fill="' + cul + '"/></g>';
  });
  /* sectoarele */
  let rs = '';
  agr.nodS.forEach((x, i) => {
    const y = yS(i), pe = sS === i, rel = f ? f.sectoare.has(i) : false;
    const eticheta = o.etS(x.cheie);
    const len = lungime(x[m]), cul = x.alt ? CUL.sectorAlt : CUL.sector;
    const aria = eticheta + ', ' + fmt(x[m]) + ' EUR, ' + numar(x.n, o.en, 'proiect', 'proiecte', 'project', 'projects') + (pe ? ', ' + o.L('selectat', 'selected') : '');
    rs += '<g class="sdg-row sdg-s" data-s="' + i + '" tabindex="0" role="button" aria-pressed="' + (pe ? 'true' : 'false') + '" aria-label="' + esc(aria) + '" style="cursor:pointer;outline:none">' +
      '<rect class="hit" x="' + g.SAX + '" y="' + rot(y - pS / 2) + '" width="' + (g.W - g.SAX - 4) + '" height="' + rot(pS) + '" rx="4" fill="' + (pe ? CUL.banda : (rel && f ? 'rgba(200,135,26,.10)' : 'transparent')) + '"/>' +
      '<circle class="dot" cx="' + g.SAX + '" cy="' + rot(y) + '" r="3.5" fill="' + cul + '"/>' +
      '<rect class="bar" x="' + g.SBX + '" y="' + rot(y - 6) + '" width="' + rot(len) + '" height="12" rx="3" fill="' + cul + '"/>' +
      '<text class="val" x="' + rot(g.SBX + len + 6) + '" y="' + rot(y) + '" dominant-baseline="central" font-family="' + fam + '" font-size="10.5" fill="' + CUL.dim + '">' + esc(fmt(x[m])) + '</text>' +
      '<text class="nm" x="' + g.SLX + '" y="' + rot(y) + '" dominant-baseline="central" font-family="' + fam + '" font-size="11.5" font-weight="' + (pe || (rel && f) ? 700 : 400) + '" fill="' + CUL.ink + '">' + esc(taie(eticheta, 42)) + '</text></g>';
  });
  h += '<g class="sdg-donatori">' + rd + '</g><g class="sdg-sectoare">' + rs + '</g><g class="sdg-zone">' + hitH + '</g>';
  const svg = '<svg class="sdg-svg" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ' + g.W + ' ' + H + '" width="' + g.W + '" height="' + H + '" role="group" aria-label="' + esc(o.aria || '') + '" style="display:block;width:100%;min-width:1000px;height:auto">' + h + '</svg>';
  return { svg: svg, W: g.W, H: H, iD: iD, iS: iS, maxN: maxN, maxL: maxL };
}

/* ---------- datele pentru CSV și Excel ----------
   c: { L, en, etD(cheie), etS(cheie), titlu(p), perioada(p), url(id), context:[…], limita }                                       */
function datePentruExport(agr, grupe, matr, c){
  const L = c.L, m = agr.metric;
  const rot0 = Math.round;
  const tot = totalGrupe(grupe);
  const dubluri = L('Un proiect cu mai multe sectoare apare în fiecare dintre ele, cu suma întreagă; „Total (proiecte unice)” îl numără o singură dată.',
                    'A project with several sectors appears in each of them with its full amount; “Total (unique projects)” counts it once.');
  const totalUnic = L('TOTAL (proiecte unice)', 'TOTAL (unique projects)');
  const colAng = L('Angajamente (EUR)', 'Commitments (EUR)'), colDeb = L('Debursări (EUR)', 'Disbursements (EUR)');
  const numeFoi = grupe.map(g => c.etS(g.cheie));

  /* 1. Rezumat pe sectoare */
  const rezumat = {
    foaie: L('Rezumat pe sectoare', 'Summary by sector'), titlu: L('Rezumat pe sectoare', 'Summary by sector'), cols: [L('Sector', 'Sector'), L('Proiecte', 'Projects'), colAng, colDeb, L('Donatori', 'Donors'), L('Donatorul principal', 'Main donor')],
    rows: grupe.map(g => [c.etS(g.cheie), g.n, rot0(g.ang), rot0(g.deb), g.donatori.length, g.donatori.length ? c.etD(g.donatori[0].cheie) : '']),
    opt: { tip: 'tneent', bare: [m === 'deb' ? 3 : 2], randTotal: grupe.length ? [totalUnic, tot.proiecte, rot0(tot.ang), rot0(tot.deb), '', ''] : null,
           linkuri: { 0: (r, i) => '#' + numeFoi[i] }, context: c.context,
           nota: [dubluri, L('Numele sectorului duce la foaia lui, cu proiectele.', 'The sector name links to its sheet with the projects.')],
           grafic: grupe.length > 1 ? { tip: 'bar', cat: 0, serii: [2, 3], n: 12, culori: ['9DB8DF', '1E4B8C'], titlu: L('Primele 12 sectoare', 'Top 12 sectors') } : null }
  };

  /* 2. Donator × sector */
  const sect = matr.sectoare, nSect = sect.length;
  const foaieMatrice = {
    foaie: L('Donator × sector', 'Donor × sector'), titlu: L('Donator × sector', 'Donor × sector'),
    cols: [L('Donator \\ sector', 'Donor \\ sector')].concat(sect.map(s => c.etS(s.cheie))).concat([L('Total (toate sectoarele)', 'Total (all sectors)')]),
    rows: matr.donatori.map(d => [c.etD(d.cheie)].concat(sect.map(s => rot0(matr.cel.get(d.cheie + SEP + s.cheie) || 0))).concat([rot0(d.total)])),
    opt: { tip: 't' + 'e'.repeat(nSect + 1), harta: nSect ? { de: 1, pana: nSect } : null, context: c.context,
           total: { eticheta: L('Total (donatorii afișați)', 'Total (donors shown)'), suma: Array.from({ length: nSect + 1 }, (_, i) => i + 1) },
           nota: [L('Măsura: ', 'Measure: ') + (m === 'deb' ? colDeb : colAng) + '.', L('Un proiect cu mai multe sectoare e numărat în fiecare; ultima coloană îl numără o singură dată.', 'A project with several sectors is counted in each; the last column counts it once.')] }
  };

  /* 3. Toate proiectele (câte un rând pentru fiecare pereche proiect–sector) */
  const plat = [];
  grupe.forEach(g => g.proiecte.forEach(p => plat.push([c.etS(g.cheie), p.id || '', c.titlu(p), p.donatori.map(c.etD).join(' / '), c.perioada(p), rot0(p.ang), rot0(p.deb)])));
  const colsPlat = [L('Sector', 'Sector'), 'AMP ID', L('Proiect', 'Project'), L('Donator', 'Donor'), L('Perioadă', 'Period'), colAng, colDeb];
  const toate = {
    foaie: L('Toate proiectele', 'All projects'), titlu: L('Toate proiectele, pe sectoare', 'All projects, by sector'), cols: colsPlat, rows: plat,
    opt: { tip: 'titttee', randTotal: plat.length ? [totalUnic, '', '', '', '', rot0(tot.ang), rot0(tot.deb)] : null, linkuri: { 1: r => (c.url && r[1]) ? c.url(r[1]) : null }, context: c.context,
           latimi: { 2: 60, 3: 36 }, nota: [dubluri] }
  };

  /* 4. Câte o foaie pe sector */
  const foi = [rezumat, foaieMatrice, toate];
  grupe.forEach((g, i) => {
    foi.push({
      foaie: numeFoi[i], titlu: numeFoi[i], cols: ['AMP ID', L('Proiect', 'Project'), L('Donator', 'Donor'), L('Perioadă', 'Period'), colAng, colDeb],
      rows: g.proiecte.map(p => [p.id || '', c.titlu(p), p.donatori.map(c.etD).join(' / '), c.perioada(p), rot0(p.ang), rot0(p.deb)]),
      opt: { tip: 'itttee', total: { eticheta: L('Total', 'Total'), suma: [4, 5] }, linkuri: { 0: r => (c.url && r[0]) ? c.url(r[0]) : null }, context: c.context, latimi: { 1: 60, 2: 36 },
             nota: [L('Un proiect cu mai multe sectoare apare și în foile celorlalte sectoare.', 'A project with several sectors also appears on the sheets of its other sectors.')] }
    });
  });
  return { cols: colsPlat, rows: plat, opt: { foiExcel: foi, context: c.context, tip: 'titttee' } };
}

/* ======================================================================== 2. PARTEA DE PAGINĂ */
const API = { ALTII: ALTII, ALTE: ALTE, FARA_SECTOR: FARA_SECTOR, GEO: GEO, cuvant: cuvant, numar: numar, unice: unice, dinPerioada: dinPerioada, agrega: agrega, perechi: perechi, peSectoare: peSectoare,
              totalGrupe: totalGrupe, matrice: matrice, focus: focus, diagramaSvg: diagramaSvg, datePentruExport: datePentruExport, potrivesteDonator: potrivesteDonator, potrivesteSector: potrivesteSector };
if(typeof module !== 'undefined' && module.exports) module.exports = API;
if(typeof document === 'undefined' || typeof window === 'undefined') return;
window.SectoareDonatori = API;

const G = window;
const en = () => { try{ return currentLang === 'en'; }catch(e){ return false; } };
const L = (ro, e) => en() ? e : ro;
const esc = s => G.esc ? G.esc(s) : String(s == null ? '' : s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;').replace(/'/g, '&#39;');
const fmtNum = n => G.fmtNum ? G.fmtNum(n) : String(Math.round(n));
const fmtCompact = n => G.fmtCompact ? G.fmtCompact(n) : String(Math.round(n));
const $ = id => document.getElementById(id);
const proiecteSursa = () => { try{ return PROJECTS; }catch(e){ return []; } };

const st = { metric: 'ang', de: '', pana: '', donator: '', sector: '', deschise: new Set(), pagina: new Map(), nD: 12, toate: false };
let cache = null;

function etD(k){ return k === ALTII ? L('Alți donatori', 'Other donors') + ' (' + (cache ? cache.agr.altiD.size : '') + ')' : (G.donorLabel ? G.donorLabel(k) : k); }
function etS(k){
  if(k === ALTE) return L('Alte sectoare', 'Other sectors') + ' (' + (cache ? cache.agr.alteS.size : '') + ')';
  if(k === FARA_SECTOR) return L('Nespecificat', 'Unspecified');
  return G.sectorLabel ? G.sectorLabel(k) : k;
}
function titluProiect(p){ return G.projectLabel ? G.projectLabel(p.ref) : (p.ref.denumire || ''); }
function perioada(p){
  if(p.an === 'NA' || p.an === undefined) return L('nespecificat', 'unspecified');
  let sf = null;
  try{ const sp = p.id && PROJECT_SPAN_LOOKUP[p.id]; if(sp && sp.e && sp.e >= p.an) sf = sp.e; }catch(e){}
  return sf && sf !== p.an ? p.an + '–' + sf : String(p.an);
}
const urlProiect = id => G.ampProjectUrl ? G.ampProjectUrl(id) : null;

function calculeaza(){
  const toate = unice(proiecteSursa());
  const ani = [...new Set(toate.filter(p => p.an !== 'NA' && p.an !== undefined).map(p => p.an))].sort((a, b) => a - b);
  // selecția păstrată între redesenări trebuie să existe și în datele noi (după o actualizare live, de pildă)
  if(st.de && ani.indexOf(+st.de) < 0) st.de = '';
  if(st.pana && ani.indexOf(+st.pana) < 0) st.pana = '';
  const lista = dinPerioada(toate, st.de, st.pana);
  let agr = agrega(lista, { metric: st.metric, nD: st.nD, nS: 30, fixD: [st.donator], fixS: [st.sector] });
  if(st.donator && st.donator !== ALTII && !agr.donatori.some(x => x.cheie === st.donator)) st.donator = '';
  if(st.sector && st.sector !== ALTE && !agr.sectoare.some(x => x.cheie === st.sector)) st.sector = '';
  if(st.donator === ALTII && !agr.altiD.size) st.donator = '';
  if(st.sector === ALTE && !agr.alteS.size) st.sector = '';
  if(st.donator && st.sector && !perechi(lista, { donator: st.donator, sector: st.sector }, agr).length) st.sector = '';
  agr = agrega(lista, { metric: st.metric, nD: st.nD, nS: 30, fixD: [st.donator], fixS: [st.sector] });
  const sel = { donator: st.donator, sector: st.sector };
  const grupe = peSectoare(lista, { metric: st.metric, sel: sel, agr: agr });
  cache = { toate: toate, ani: ani, lista: lista, agr: agr, sel: sel, grupe: grupe };
  return cache;
}

/* ---------- CSS ---------- */
function stiluri(){
  if($('sdg-css')) return;
  const s = document.createElement('style');
  s.id = 'sdg-css';
  s.textContent = [
    '#sdgPanel .sdg-bar{display:flex;flex-wrap:wrap;gap:8px 12px;align-items:center;padding:0 16px 12px}',
    '#sdgPanel .sdg-bar label{display:flex;align-items:center;gap:6px;font-size:11.5px;color:var(--ink-dim)}',
    '#sdgPanel .sdg-bar select{background:var(--bg);border:1px solid var(--line);border-radius:7px;color:var(--ink);padding:7px 9px;font-family:inherit;font-size:12.5px;max-width:280px;min-width:0}',
    '#sdgPanel .sdg-chips{display:flex;flex-wrap:wrap;gap:6px;align-items:center;margin-left:auto}',
    '#sdgPanel .sdg-chip{display:inline-flex;gap:4px;align-items:center;background:var(--blue-bg);color:var(--navy-deep);border:1px solid var(--line-strong);border-radius:999px;padding:3px 4px 3px 10px;font-size:12px;font-weight:600;max-width:100%}',
    '#sdgPanel .sdg-chip span{overflow:hidden;text-overflow:ellipsis;white-space:nowrap;max-width:260px}',
    '#sdgPanel .sdg-chip button{border:none;background:none;cursor:pointer;color:var(--navy);font-size:15px;line-height:1;padding:2px 7px;border-radius:50%;min-width:24px;min-height:24px}',
    '#sdgPanel .sdg-chip button:hover,#sdgPanel .sdg-chip button:focus-visible{background:#fff}',
    '#sdgPanel .sdg-btn{background:var(--panel);color:var(--navy);border:1px solid var(--line-strong);border-radius:6px;padding:6px 12px;font-size:11.5px;font-weight:600;cursor:pointer;font-family:inherit}',
    '#sdgPanel .sdg-btn:hover,#sdgPanel .sdg-btn:focus-visible{background:var(--blue-bg)}',
    '#sdgPanel .sdg-btn[disabled]{opacity:.55;cursor:default}',
    '#sdgPanel .sdg-wrap{overflow-x:auto;padding:0 8px 4px;-webkit-overflow-scrolling:touch}',
    '#sdgPanel .sdg-row:focus-visible .hit{stroke:#22406b;stroke-width:1.5}',
    '#sdgPanel .sdg-row:hover .hit{fill:rgba(34,64,107,.08)}',
    '#sdgPanel .sdg-leg{display:flex;flex-wrap:wrap;gap:6px 18px;align-items:center;padding:4px 16px 14px;font-size:11.5px;color:var(--ink-dim)}',
    '#sdgPanel .sdg-leg i{display:inline-block;vertical-align:-1px;margin-right:6px}',
    '#sdgPanel .sdg-leg .b{width:16px;height:9px;border-radius:2px}',
    '#sdgPanel .sdg-leg .l{width:28px;height:3px;background:#22406b;opacity:.35;border-radius:2px;margin-bottom:2px}',
    '#sdgPanel .sdg-leg .l.g{height:8px;opacity:.35}',
    '#sdgPanel .sdg-sum{padding:10px 16px;font-size:12px;color:var(--ink-dim);display:flex;flex-wrap:wrap;gap:4px 18px;align-items:center;border-bottom:1px solid var(--line)}',
    '#sdgPanel .sdg-sum b{color:var(--navy-deep)}',
    '#sdgPanel .sdg-gol{padding:22px 16px;text-align:center;color:var(--ink-dim);font-size:13px}',
    '#sdgPanel .sdg-cap,#sdgPanel .sdg-gh{display:grid;grid-template-columns:20px minmax(150px,2fr) 100px 120px 120px minmax(150px,2.4fr);gap:0 12px;align-items:center;padding:0 16px}',
    '#sdgPanel .sdg-cap{font-size:10.5px;font-weight:700;letter-spacing:.05em;text-transform:uppercase;color:var(--ink-dim);padding-top:8px;padding-bottom:6px;border-bottom:1px solid var(--line)}',
    '#sdgPanel .sdg-cap .n,#sdgPanel .sdg-gh .n{text-align:right;font-variant-numeric:tabular-nums}',
    '#sdgPanel .sdg-gh{width:100%;background:var(--panel);border:none;border-bottom:1px solid var(--line);padding-top:9px;padding-bottom:9px;cursor:pointer;font-family:inherit;font-size:12.5px;color:var(--ink);text-align:left}',
    '#sdgPanel .sdg-gh:hover,#sdgPanel .sdg-gh:focus-visible{background:var(--blue-bg)}',
    '#sdgPanel .sdg-gh[aria-expanded="true"]{background:var(--blue-bg)}',
    '#sdgPanel .sdg-car{color:var(--navy);font-size:11px;transition:transform .12s}',
    '#sdgPanel .sdg-gh[aria-expanded="true"] .sdg-car{transform:rotate(90deg)}',
    '#sdgPanel .sdg-gn{font-weight:700;color:var(--navy-deep);min-width:0;overflow:hidden;text-overflow:ellipsis}',
    '#sdgPanel .sdg-gd{font-size:11.5px;color:var(--ink-dim);min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}',
    '#sdgPanel .sdg-gb{border-bottom:1px solid var(--line);background:#fff}',
    '#sdgPanel .sdg-gb .table-scroll{max-height:480px}',
    '#sdgPanel .sdg-gb td.t{max-width:380px}',
    '#sdgPanel .sdg-gb td.d{min-width:150px;max-width:240px}',
    '#sdgPanel .sdg-gb td.t span{display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}',
    '#sdgPanel .sdg-mai{padding:10px 16px;display:flex;gap:8px;align-items:center;flex-wrap:wrap;font-size:12px;color:var(--ink-dim)}',
    '#sdgPanel .sdg-gb table{min-width:680px}',
    '@media (max-width:760px){',
    ' #sdgPanel .sdg-cap{display:none}',
    ' #sdgPanel .sdg-gh{display:flex;flex-wrap:wrap;align-items:baseline;gap:3px 12px;padding:10px 14px}',
    ' #sdgPanel .sdg-car{flex:0 0 14px}',
    ' #sdgPanel .sdg-gn{flex:1 1 calc(100% - 30px);white-space:normal}',
    ' #sdgPanel .sdg-gn + .n{margin-left:26px}',
    ' #sdgPanel .sdg-gh .n{text-align:left}',
    ' #sdgPanel .sdg-gh .n::after{content:" " attr(data-u);color:var(--ink-dim);font-size:11px}',
    ' #sdgPanel .sdg-gd{flex:1 1 100%;white-space:normal;padding-left:26px}',
    ' #sdgPanel .sdg-chips{margin-left:0}',
    '}'
  ].join('\n');
  document.head.appendChild(s);
}

/* ---------- tooltip ---------- */
function tip(){
  let t = $('advTooltip');
  if(!t){ t = document.createElement('div'); t.id = 'advTooltip'; t.className = 'tooltip'; document.body.appendChild(t); }
  return t;
}
function arataTip(html, x, y){
  const t = tip();
  t.innerHTML = html; t.style.display = 'block';
  const w = t.offsetWidth || 260, h = t.offsetHeight || 80;
  t.style.left = Math.max(8, Math.min(x + 14, window.innerWidth - w - 8)) + 'px';
  t.style.top = Math.max(8, (y + 14 + h > window.innerHeight - 8) ? y - h - 10 : y + 14) + 'px';
}
function ascundeTip(){ const t = $('advTooltip'); if(t) t.style.display = 'none'; }

/* ---------- controalele ---------- */
function controale(){
  const c = cache, bar = $('sdgBar');
  if(!bar) return;
  const ani = c.ani;
  const optAni = (val, minV, maxV) => '<option value="">' + esc(L('Toți anii', 'All years')) + '</option>' +
    ani.map(a => '<option value="' + a + '"' + (String(val) === String(a) ? ' selected' : '') + (((minV && a < minV) || (maxV && a > maxV)) ? ' disabled' : '') + '>' + a + '</option>').join('');
  const donOpt = '<option value="">' + esc(L('— Toți donatorii —', '— All donors —')) + '</option>' +
    c.agr.donatori.filter(x => x[st.metric] > 0 || x.cheie === st.donator).map(x => '<option value="' + esc(x.cheie) + '"' + (st.donator === x.cheie ? ' selected' : '') + '>' + esc(etD(x.cheie)) + ' (' + x.n + ')</option>').join('') +
    (c.agr.altiD.size && c.agr.nodD.some(x => x.cheie === ALTII) ? '<option value="' + esc(ALTII) + '"' + (st.donator === ALTII ? ' selected' : '') + '>' + esc(etD(ALTII)) + '</option>' : '');
  const chips = [];
  if(st.donator) chips.push('<span class="sdg-chip"><span title="' + esc(etD(st.donator)) + '">' + esc(L('Donator: ', 'Donor: ') + etD(st.donator)) + '</span><button type="button" data-sdg-clear="d" aria-label="' + esc(L('Scoate filtrul de donator', 'Remove the donor filter')) + '">×</button></span>');
  if(st.sector) chips.push('<span class="sdg-chip"><span title="' + esc(etS(st.sector)) + '">' + esc(L('Sector: ', 'Sector: ') + etS(st.sector)) + '</span><button type="button" data-sdg-clear="s" aria-label="' + esc(L('Scoate filtrul de sector', 'Remove the sector filter')) + '">×</button></span>');
  const nP = c.grupe.length ? totalGrupe(c.grupe).proiecte : 0;
  bar.innerHTML =
    '<label>' + esc(L('Perioada de început', 'Start year')) + ' <select id="sdgDe" aria-label="' + esc(L('De la anul', 'From year')) + '">' + optAni(st.de, 0, +st.pana || 0) + '</select></label>' +
    '<label>' + esc(L('până la', 'to')) + ' <select id="sdgPana" aria-label="' + esc(L('Până la anul', 'To year')) + '">' + optAni(st.pana, +st.de || 0, 0) + '</select></label>' +
    '<label>' + esc(L('Donator', 'Donor')) + ' <select id="sdgDonator">' + donOpt + '</select></label>' +
    '<div class="sdg-chips">' + chips.join('') +
    (chips.length ? '<button type="button" class="sdg-btn" data-sdg-clear="all">' + esc(L('Resetează selecția', 'Reset selection')) + '</button>' : '') +
    '<button type="button" class="sdg-btn" id="sdgSpreLista">' + esc(L('Proiectele ↓', 'Projects ↓')) + ' (' + fmtNum(nP) + ')</button></div>';
  const mb = $('sdgMetric');
  if(mb){
    const bs = mb.querySelectorAll('button');
    bs.forEach(b => {
      b.textContent = b.dataset.m === 'ang' ? L('Angajamente', 'Commitments') : L('Debursări', 'Disbursements');
      b.setAttribute('aria-pressed', b.dataset.m === st.metric ? 'true' : 'false');
    });
  }
}

/* ---------- diagrama ---------- */
function ctxDiagrama(extra){
  return Object.assign({ sel: cache.sel, etD: etD, etS: etS, fmt: fmtCompact, esc: esc, L: L, en: en(), titluD: L('Donatori', 'Donors'), titluS: L('Sectoare', 'Sectors'),
    aria: L('Diagramă: donatorii (stânga) și sectoarele (dreapta); grosimea liniei arată suma proiectelor donatorului în acel sector',
            'Diagram: donors (left) and sectors (right); line thickness shows the donor’s project amount in that sector') }, extra || {});
}
function diagrama(){
  const c = cache, el = $('sdgDiagrama');
  if(!el) return;
  if(!c.agr.nodD.length || !c.agr.nodS.length){
    el.innerHTML = '<div class="sdg-gol">' + esc(G.t ? G.t('emptyCurrentSelection') : L('Nicio dată pentru selecția curentă.', 'No data for the current selection.')) + '</div>';
    c.geom = null;
  } else {
    const d = diagramaSvg(c.agr, ctxDiagrama());
    d.focusAplicat = (c.sel.donator && d.iD.has(c.sel.donator) ? d.iD.get(c.sel.donator) : null) + ',' + (c.sel.sector && d.iS.has(c.sel.sector) ? d.iS.get(c.sel.sector) : null);
    c.geom = d;
    el.innerHTML = d.svg;
  }
  const lg = $('sdgLegenda');
  if(lg){
    lg.innerHTML = '<span><i class="b" style="background:#22406b"></i>' + esc(L('donator', 'donor')) + '</span><span><i class="b" style="background:#c8871a"></i>' + esc(L('sector', 'sector')) + '</span>' +
      '<span><i class="l"></i><i class="l g"></i>' + esc(L('linie = suma proiectelor donatorului în acel sector', 'line = the donor’s project amount in that sector')) + '</span>' +
      '<span>' + esc(L('bară = totalul, fiecare proiect o singură dată · măsura: ', 'bar = total, each project once · measure: ') + (st.metric === 'deb' ? L('debursări', 'disbursements') : L('angajamente', 'commitments'))) + '</span>';
  }
}

/* Evidențierea fără redesenare: liniile și rândurile se actualizează direct în SVG, ca să meargă și la trecerea cursorului. */
function aplicaFocus(fd, fs){
  const c = cache; if(!c || !c.geom) return;
  const svg = $('sdgDiagrama').querySelector('svg'); if(!svg) return;
  const cheie = fd + ',' + fs;
  if(c.geom.focusAplicat === cheie) return;
  c.geom.focusAplicat = cheie;
  if(!c.geom.idx) c.geom.idx = c.agr.legaturi.map(l => ({ d: c.geom.iD.get(l.d), s: c.geom.iS.get(l.s) }));
  const f = focus({ legaturi: c.geom.idx }, { d: fd, s: fs });
  const selD = c.sel.donator ? (c.geom.iD.has(c.sel.donator) ? c.geom.iD.get(c.sel.donator) : null) : null;
  const selS = c.sel.sector ? (c.geom.iS.has(c.sel.sector) ? c.geom.iS.get(c.sel.sector) : null) : null;
  svg.querySelectorAll('.sdg-link').forEach(p => { p.setAttribute('stroke-opacity', f ? (f.linii.has(+p.dataset.l) ? 0.78 : 0.06) : 0.2); });
  const rand = (g, idx, esteSel, rel, culoare) => {
    const hit = g.querySelector('.hit'), nm = g.querySelector('.nm');
    hit.setAttribute('fill', esteSel ? '#eaf0fb' : (rel ? culoare : 'transparent'));
    nm.setAttribute('font-weight', (esteSel || rel) ? 700 : 400);
  };
  svg.querySelectorAll('.sdg-d').forEach(g => { const i = +g.dataset.d; rand(g, i, selD === i, !!(f && f.donatori.has(i)), 'rgba(34,64,107,.05)'); });
  svg.querySelectorAll('.sdg-s').forEach(g => { const i = +g.dataset.s; rand(g, i, selS === i, !!(f && f.sectoare.has(i)), 'rgba(200,135,26,.10)'); });
}
function focusSelectie(){
  const c = cache; if(!c || !c.geom) return;
  const d = c.sel.donator && c.geom.iD.has(c.sel.donator) ? c.geom.iD.get(c.sel.donator) : null;
  const s = c.sel.sector && c.geom.iS.has(c.sel.sector) ? c.geom.iS.get(c.sel.sector) : null;
  aplicaFocus(d, s);
}

function textNod(x, esteDonator){
  const m = st.metric;
  const nume = esteDonator ? etD(x.cheie) : etS(x.cheie);
  const masura = m === 'deb' ? L('Debursări', 'Disbursements') : L('Angajamente', 'Commitments');
  const alt = m === 'deb' ? { e: L('Angajamente', 'Commitments'), v: x.ang } : { e: L('Debursări', 'Disbursements'), v: x.deb };
  return '<b>' + esc(nume) + '</b><br>' + masura + ': ' + fmtNum(x[m]) + ' EUR<br>' + alt.e + ': ' + fmtNum(alt.v) + ' EUR<br>' +
    numar(x.n, en(), 'proiect', 'proiecte', 'project', 'projects') + L(' (fiecare o singură dată)', ' (each counted once)') + ' · ' +
    (esteDonator ? numar(x.nrLegat, en(), 'sector', 'sectoare', 'sector', 'sectors') : numar(x.nrLegat, en(), 'donator', 'donatori', 'donor', 'donors')) +
    '<br><i style="opacity:.8">' + L('Clic: arată proiectele', 'Click: show the projects') + '</i>';
}
function textLinie(l){
  const m = st.metric;
  const masura = m === 'deb' ? L('Debursări', 'Disbursements') : L('Angajamente', 'Commitments');
  const alt = m === 'deb' ? { e: L('Angajamente', 'Commitments'), v: l.ang } : { e: L('Debursări', 'Disbursements'), v: l.deb };
  return '<b>' + esc(etD(l.d)) + '</b> → <b>' + esc(etS(l.s)) + '</b><br>' + masura + ': ' + fmtNum(l[m]) + ' EUR<br>' + alt.e + ': ' + fmtNum(alt.v) + ' EUR<br>' +
    numar(l.n, en(), 'proiect', 'proiecte', 'project', 'projects') + '<br><i style="opacity:.8">' + L('Clic: arată proiectele', 'Click: show the projects') + '</i>';
}

/* ---------- selecția ----------
   Un clic pe un donator sau pe un sector îl alege; al doilea clic pe același îl scoate. Dacă în diagramă e deja ales
   celălalt capăt și între ei nu există niciun proiect, alegerea veche se lasă: altfel lista ar rămâne goală și
   persoana ar crede că s-a stricat ceva. Un clic pe o linie alege ambele capete. */
function existaPereche(d, s){
  const c = cache; if(!c) return true;
  return perechi(c.lista, { donator: d, sector: s }, c.agr).length > 0;
}
function comuta(tip, cheie){
  if(tip === 'd'){
    if(st.donator === cheie) st.donator = '';
    else { st.donator = cheie; if(st.sector && !existaPereche(cheie, st.sector)) st.sector = ''; }
  } else if(tip === 's'){
    if(st.sector === cheie) st.sector = '';
    else { st.sector = cheie; if(st.donator && !existaPereche(st.donator, cheie)) st.donator = ''; if(cheie !== ALTE) st.deschise.add(cheie); }
  } else if(tip === 'ds'){
    const d = cheie[0], s = cheie[1];
    if(st.donator === d && st.sector === s){ st.donator = ''; st.sector = ''; }
    else { st.donator = d; st.sector = s; if(s !== ALTE) st.deschise.add(s); }
  }
  render();
}

/* ---------- lista pe sectoare ---------- */
const PAS = 100;
function corpGrup(g){
  const n = st.pagina.get(g.cheie) || PAS, rows = g.proiecte.slice(0, n);
  const ide = G.ampIdHtml || (id => esc(id || '—'));
  let h = '<div class="table-scroll"><table><thead><tr><th>AMP ID</th><th>' + esc(L('Proiect', 'Project')) + '</th><th>' + esc(L('Donator', 'Donor')) + '</th><th>' + esc(L('Perioadă', 'Period')) +
    '</th><th class="num">' + esc(L('Angajamente (EUR)', 'Commitments (EUR)')) + '</th><th class="num">' + esc(L('Debursări (EUR)', 'Disbursements (EUR)')) + '</th></tr></thead><tbody>';
  rows.forEach(p => {
    const tt = titluProiect(p), ddn = p.donatori.map(etD), dd = ddn.join(' / ');
    h += '<tr><td style="font-family:var(--mono,monospace);font-size:11.5px;color:var(--ink-dim);white-space:nowrap;">' + ide(p.id) + '</td>' +
      '<td class="t" title="' + esc(tt) + '"><span>' + esc(tt) + '</span></td><td class="d" title="' + esc(dd) + '">' + ddn.map(esc).join('<br>') + '</td>' +
      '<td style="white-space:nowrap;">' + esc(perioada(p)) + '</td><td class="num">' + fmtNum(p.ang) + '</td><td class="num">' + fmtNum(p.deb) + '</td></tr>';
  });
  h += '</tbody><tfoot><tr><td colspan="4">' + esc(L('Total sector', 'Sector total')) + ' (' + esc(numar(g.n, en(), 'proiect', 'proiecte', 'project', 'projects')) + ')</td><td class="num">' + fmtNum(g.ang) + '</td><td class="num">' + fmtNum(g.deb) + '</td></tr></tfoot></table></div>';
  if(g.n > n){
    h += '<div class="sdg-mai"><span>' + esc(L('Se arată ', 'Showing ') + n + L(' din ', ' of ') + g.n) + '</span>' +
      '<button type="button" class="sdg-btn" data-sdg-mai="' + esc(g.cheie) + '" data-n="' + PAS + '">' + esc(en() ? 'Show ' + Math.min(PAS, g.n - n) + ' more' : 'Încă ' + numar(Math.min(PAS, g.n - n), false, 'proiect', 'proiecte')) + '</button>' +
      '<button type="button" class="sdg-btn" data-sdg-mai="' + esc(g.cheie) + '" data-n="all">' + esc(L('Toate (', 'All (') + g.n + ')') + '</button></div>';
  }
  return h;
}
function grupHtml(g, i){
  const deschis = st.deschise.has(g.cheie), m = st.metric;
  const top = g.donatori.slice(0, 3).map(d => etD(d.cheie) + ' ' + fmtCompact(d[m])).join(' · ') + (g.donatori.length > 3 ? ' · +' + (g.donatori.length - 3) : '');
  return '<div class="sdg-g" data-g="' + i + '"><button type="button" class="sdg-gh" aria-expanded="' + (deschis ? 'true' : 'false') + '" data-g="' + i + '" aria-controls="sdgGb' + i + '">' +
    '<span class="sdg-car" aria-hidden="true">▶</span><span class="sdg-gn" title="' + esc(etS(g.cheie)) + '">' + esc(etS(g.cheie)) + '</span>' +
    '<span class="n" data-u="' + esc(L('proiecte', 'projects')) + '">' + g.n + '</span><span class="n" data-u="' + esc(L('angajamente', 'commitments')) + '">' + fmtCompact(g.ang) +
    '</span><span class="n" data-u="' + esc(L('debursări', 'disbursed')) + '">' + fmtCompact(g.deb) + '</span>' +
    '<span class="sdg-gd" title="' + esc(top) + '">' + esc(top) + '</span></button>' +
    '<div class="sdg-gb" id="sdgGb' + i + '"' + (deschis ? '' : ' hidden') + '>' + (deschis ? corpGrup(g) : '') + '</div></div>';
}
function lista(){
  const c = cache, el = $('sdgLista'), cnt = $('sdgCount');
  if(!el) return;
  const tot = totalGrupe(c.grupe);
  if(cnt) cnt.textContent = fmtNum(tot.proiecte);
  const btnT = $('sdgToate'), btnX = $('sdgExcel');
  if(btnT){ btnT.textContent = c.grupe.every(g => st.deschise.has(g.cheie)) && c.grupe.length ? L('Închide toate', 'Collapse all') : L('Deschide toate', 'Expand all'); btnT.disabled = !c.grupe.length; }
  if(btnX){ btnX.textContent = L('📊 Excel (.xlsx)', '📊 Excel (.xlsx)'); btnX.disabled = !c.grupe.length; }
  if(!c.grupe.length){
    el.innerHTML = '<div class="sdg-gol">' + esc(G.t ? G.t('emptyCurrentSelection') : L('Nicio dată pentru selecția curentă.', 'No data for the current selection.')) + '</div>';
    return;
  }
  const dubluri = tot.aparitii > tot.proiecte;
  el.innerHTML = '<div class="sdg-sum"><span><b>' + fmtNum(tot.sectoare) + '</b> ' + esc(cuvant(tot.sectoare, en(), 'sector', 'sectoare', 'sector', 'sectors')) + '</span><span><b>' + fmtNum(tot.proiecte) + '</b> ' + esc(cuvant(tot.proiecte, en(), 'proiect unic', 'proiecte unice', 'unique project', 'unique projects')) + '</span>' +
    '<span><b>' + fmtCompact(tot.ang) + '</b> EUR ' + esc(L('angajamente', 'commitments')) + ' · <b>' + fmtCompact(tot.deb) + '</b> EUR ' + esc(L('debursări', 'disbursements')) + ' <i>(' + esc(L('fiecare proiect o singură dată', 'each project once')) + ')</i></span>' +
    (dubluri ? '<span>' + esc(L('Apariții în sectoare: ', 'Appearances in sectors: ')) + '<b>' + fmtNum(tot.aparitii) + '</b> — ' + esc(L('un proiect cu mai multe sectoare apare în fiecare', 'a project with several sectors appears in each')) + '</span>' : '') + '</div>' +
    '<div class="sdg-cap"><span></span><span>' + esc(L('Sector', 'Sector')) + '</span><span class="n">' + esc(L('Proiecte', 'Projects')) + '</span><span class="n">' + esc(L('Angajamente', 'Commitments')) + '</span><span class="n">' + esc(L('Debursări', 'Disbursements')) +
    '</span><span>' + esc(L('Donatori principali', 'Main donors')) + '</span></div>' + c.grupe.map(grupHtml).join('');
}
function comutaGrup(i){
  const g = cache.grupe[i]; if(!g) return;
  const deschis = st.deschise.has(g.cheie);
  if(deschis) st.deschise.delete(g.cheie); else st.deschise.add(g.cheie);
  const box = $('sdgGb' + i), btn = box && box.previousElementSibling;
  if(!box) return;
  box.hidden = deschis;
  btn.setAttribute('aria-expanded', deschis ? 'false' : 'true');
  box.innerHTML = deschis ? '' : corpGrup(g);
  const btnT = $('sdgToate');
  if(btnT) btnT.textContent = cache.grupe.every(x => st.deschise.has(x.cheie)) ? L('Închide toate', 'Collapse all') : L('Deschide toate', 'Expand all');
}

/* ---------- datele pentru CSV și Excel ---------- */
function contextExport(){
  const c = cache, ctx = [];
  const de = st.de, pana = st.pana;
  ctx.push(L('Perioada (anul de început al proiectului): ', 'Period (project start year): ') + (de || pana ? (de || c.ani[0]) + '–' + (pana || c.ani[c.ani.length - 1]) : L('toți anii', 'all years')));
  if(st.donator) ctx.push(L('Donator: ', 'Donor: ') + etD(st.donator));
  if(st.sector) ctx.push(L('Sector: ', 'Sector: ') + etS(st.sector));
  ctx.push(L('Ordonat după: ', 'Sorted by: ') + (st.metric === 'deb' ? L('debursări', 'disbursements') : L('angajamente', 'commitments')));
  return ctx;
}
function dateExport(){
  if(!cache) calculeaza();
  const c = cache;
  const matr = matrice(c.lista, { metric: st.metric, sel: c.sel, agr: c.agr });
  return datePentruExport(c.agr, c.grupe, matr, { L: L, en: en(), etD: etD, etS: etS, titlu: titluProiect, perioada: perioada, url: urlProiect, context: contextExport() });
}
function inregistreaza(){
  const panel = $('sdgPanel');
  if(panel) panel.__dateCsv = () => dateExport();
}

/* ---------- desenarea întregului panou ---------- */
/* Redesenarea înlocuiește controalele și rândurile: cine navighează cu tastatura nu trebuie să-și piardă locul. */
let tacut = false;
function focusCurent(){
  const ae = document.activeElement, panel = $('sdgPanel'), c = cache;
  if(!ae || !panel || !c || !panel.contains(ae)) return null;
  if(ae.classList.contains('sdg-d')){ const x = c.agr.nodD[+ae.dataset.d]; return x ? { t: 'd', k: x.cheie } : null; }
  if(ae.classList.contains('sdg-s')){ const x = c.agr.nodS[+ae.dataset.s]; return x ? { t: 's', k: x.cheie } : null; }
  if(ae.hasAttribute('data-sdg-clear')) return { id: 'sdgSpreLista' };
  return ae.id ? { id: ae.id } : null;
}
function refocus(f){
  if(!f) return;
  let el = null;
  if(f.id) el = $(f.id);
  else if(f.t){
    const i = (f.t === 'd' ? cache.agr.nodD : cache.agr.nodS).findIndex(x => x.cheie === f.k);
    if(i >= 0) el = $('sdgDiagrama').querySelector(f.t === 'd' ? '.sdg-d[data-d="' + i + '"]' : '.sdg-s[data-s="' + i + '"]');
  }
  if(el){ tacut = true; try{ el.focus({ preventScroll: true }); }finally{ tacut = false; } }
}
function render(){
  if(!$('sdgPanel')) return;
  stiluri();
  const f = focusCurent();
  ascundeTip();
  calculeaza();
  controale();
  diagrama();
  lista();
  inregistreaza();
  refocus(f);
}

/* ---------- evenimente (o singură dată, pe panou) ---------- */
function leaga(){
  const panel = $('sdgPanel');
  if(!panel || panel.__sdgGata) return;
  panel.__sdgGata = true;
  const nodDin = e => e.target.closest ? e.target.closest('.sdg-row, .sdg-hit') : null;
  const infoNod = el => {
    const c = cache;
    if(!el || !c) return null;
    if(el.classList.contains('sdg-hit')){
      const l = c.agr.legaturi[+el.dataset.l];
      return l ? { html: textLinie(l), d: +el.dataset.d, s: +el.dataset.s } : null;
    }
    if(el.classList.contains('sdg-d')){ const x = c.agr.nodD[+el.dataset.d]; return x ? { html: textNod(x, true), d: +el.dataset.d, s: null } : null; }
    const x = c.agr.nodS[+el.dataset.s];
    return x ? { html: textNod(x, false), d: null, s: +el.dataset.s } : null;
  };
  panel.addEventListener('mousemove', e => {
    const el = nodDin(e); if(!el || !panel.contains(el)){ return; }
    const i = infoNod(el); if(!i) return;
    aplicaFocus(i.d, i.s);
    arataTip(i.html, e.clientX, e.clientY);
  });
  panel.addEventListener('mouseout', e => {
    const el = nodDin(e); if(!el) return;
    const catre = e.relatedTarget && e.relatedTarget.closest ? e.relatedTarget.closest('.sdg-row, .sdg-hit') : null;
    if(catre === el) return;
    ascundeTip(); focusSelectie();
  });
  panel.addEventListener('focusin', e => {
    const el = e.target.closest && e.target.closest('.sdg-row'); if(!el || tacut) return;
    const i = infoNod(el); if(!i) return;
    aplicaFocus(i.d, i.s);
    const r = el.getBoundingClientRect();
    arataTip(i.html, r.left + Math.min(r.width, 420) / 2, r.top + r.height / 2);
  });
  panel.addEventListener('focusout', e => { if(e.target.closest && e.target.closest('.sdg-row')){ ascundeTip(); focusSelectie(); } });
  panel.addEventListener('click', e => {
    const t = e.target;
    const rand = t.closest && t.closest('.sdg-row');
    const zona = t.closest && t.closest('.sdg-hit');
    if(zona){
      const l = cache.agr.legaturi[+zona.dataset.l]; if(l){ ascundeTip(); comuta('ds', [l.d, l.s]); } return;
    }
    if(rand){
      ascundeTip();
      if(rand.classList.contains('sdg-d')){ const x = cache.agr.nodD[+rand.dataset.d]; if(x) comuta('d', x.cheie); }
      else { const x = cache.agr.nodS[+rand.dataset.s]; if(x) comuta('s', x.cheie); }
      return;
    }
    const m = t.closest && t.closest('#sdgMetric button');
    if(m){ if(st.metric !== m.dataset.m){ st.metric = m.dataset.m; render(); } return; }
    const cl = t.closest && t.closest('[data-sdg-clear]');
    if(cl){ const w = cl.dataset.sdgClear; if(w === 'd' || w === 'all') st.donator = ''; if(w === 's' || w === 'all') st.sector = ''; render(); return; }
    if(t.closest && t.closest('#sdgSpreLista')){
      const cap = $('sdgListaCap');
      if(cap && cap.scrollIntoView) cap.scrollIntoView({ behavior: (window.matchMedia && matchMedia('(prefers-reduced-motion: reduce)').matches) ? 'auto' : 'smooth', block: 'start' });
      return;
    }
    const gh = t.closest && t.closest('.sdg-gh');
    if(gh){ comutaGrup(+gh.dataset.g); return; }
    const mai = t.closest && t.closest('[data-sdg-mai]');
    if(mai){
      const cheie = mai.dataset.sdgMai, g = cache.grupe.find(x => x.cheie === cheie); if(!g) return;
      st.pagina.set(cheie, mai.dataset.n === 'all' ? g.n : (st.pagina.get(cheie) || PAS) + PAS);
      const i = cache.grupe.indexOf(g), box = $('sdgGb' + i); if(box) box.innerHTML = corpGrup(g);
      return;
    }
    if(t.closest && t.closest('#sdgToate')){
      const toateDeschise = cache.grupe.every(g => st.deschise.has(g.cheie));
      cache.grupe.forEach(g => { if(toateDeschise) st.deschise.delete(g.cheie); else st.deschise.add(g.cheie); });
      lista();
      return;
    }
    if(t.closest && t.closest('#sdgExcel')){
      const btn = t.closest('#sdgExcel');
      if(!window.__xlsxDirect) return;
      const d = dateExport();
      window.__xlsxDirect({ titlu: L('Donatori → sectoare · cu proiectele fiecărui sector', 'Donors → sectors · with each sector’s projects'), nume: L('donatori-sectoare', 'donors-sectors'), vedere: 'advancedView',
                            cols: d.cols, rows: d.rows, opt: d.opt, btn: btn });
    }
  });
  panel.addEventListener('change', e => {
    const id = e.target.id;
    if(id === 'sdgDe'){ st.de = e.target.value; render(); }
    else if(id === 'sdgPana'){ st.pana = e.target.value; render(); }
    else if(id === 'sdgDonator'){
      st.donator = e.target.value;
      if(st.donator && st.sector && !existaPereche(st.donator, st.sector)) st.sector = '';
      render();
    }
  });
  panel.addEventListener('keydown', e => {
    if((e.key === 'Enter' || e.key === ' ') && e.target.classList && e.target.classList.contains('sdg-row')){
      e.preventDefault();
      e.target.dispatchEvent(new MouseEvent('click', { bubbles: true }));
    } else if(e.key === 'Escape' && (st.donator || st.sector) && e.target.classList && e.target.classList.contains('sdg-row')){
      st.donator = ''; st.sector = ''; render();
    }
  });
  window.addEventListener('scroll', ascundeTip, { passive: true });
}

window.__renderSectoare = function(){ try{ leaga(); render(); }catch(e){ console.warn('donatori → sectoare', e); } };
window.__sdgStare = st;
})();
