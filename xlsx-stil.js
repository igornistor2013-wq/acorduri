/* xlsx-stil.js — scrie fișiere Excel (.xlsx) gata de folosit, fără nicio bibliotecă.

   De ce nu SheetJS: versiunea gratuită (xlsx.min.js) scrie doar valorile, fără nicio
   formatare — exact ce nu a plăcut la CSV. Aici fișierul se scrie direct (ZIP + XML) și
   are, pe lângă date:
     · titlu și rând de context (sursa, selecția activă, data) într-un antet colorat;
     · antet de tabel cu fundal, filtre pe coloane și rânduri înghețate la derulare;
     · formate de număr (mii separate, procente, ani, diferențe cu semn), nu text;
     · dungi alternante care rămân și după sortare (formatare condiționată);
     · bare în celule, scară de culoare pentru matrici, culori pentru diferențe;
     · rând de total cu formule (SUBTOTAL: se recalculează când filtrezi);
     · hyperlinkuri adevărate, note sub tabel, antet repetat la tipărire;
     · la tabelele late: prima coloană înghețată, antet pe grupe de coloane, culori pe etichete („Grant", „Împrumut"),
       înălțime de rând limitată și un titlu care încape pe ecran;
     · un grafic Excel nativ (editabil), alături de tabel, când are sens.
   Încărcat la cerere: index.html / unelte.js îl cer abia la primul export.

   Folosire:
     const blob = await XlsxStil.construieste({ foaie, titlu, subtitlu, antete, tipuri, randuri, ... });
   Câmpurile sunt descrise lângă funcția construieste(), la sfârșitul fișierului. */
(function(){
'use strict';

/* ------------------------------------------------------------------ paletă
   Aceleași culori ca în pagină (--navy-deep, --navy, --blue-bg, --gold) și ca în raportul PDF. */
const CUL = {
  navyDeep: 'FF14233C', navy: 'FF1E4B8C', gold: 'FFFFD200', ink: 'FF1C2230', dim: 'FF6B7284',
  banda: 'FFEAF0FB', total: 'FFDCE6F5', zebra: 'FFF3F6FB', linie: 'FFD5DCE8', link: 'FF0563C1',
  verde: 'FF16794F', rosu: 'FFC0392B', alb: 'FFFFFFFF', albastruDeschis: 'FF9DB8DF'
};
const PALETA_GRAFIC = ['1E4B8C', '9DB8DF', 'C8871A', '2DD4BF', 'C0402C', '6B7284', '155A52', '7A5A1A', '16294A'];

/* ------------------------------------------------------------ utilitare XML */
const RX_CTRL = /[\u0000-\u0008\u000B\u000C\u000E-\u001F\uFFFE\uFFFF]/g;
function xe(s){
  return String(s == null ? '' : s).replace(RX_CTRL, '')
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}
function lit(i){                                   // 0 → A, 26 → AA
  let s = ''; i++;
  while(i > 0){ const r = (i - 1) % 26; s = String.fromCharCode(65 + r) + s; i = (i - r - 1) / 26; }
  return s;
}
const ref = (c, r) => lit(c) + (r + 1);            // coloană și rând, ambele de la 0
const ABS = (c, r) => '$' + lit(c) + '$' + (r + 1);
function nume_foaie(s, implicit){
  s = String(s || '').replace(/[\[\]:*?\/\\]/g, ' ').replace(/\s+/g, ' ').trim().replace(/^'+|'+$/g, '');
  if(s.length > 31){
    const taiat = s.slice(0, 31), sp = taiat.lastIndexOf(' ');
    s = (sp > 14 ? taiat.slice(0, sp) : taiat).trim();
  }
  return s || implicit || 'Date';
}
const citeaza_foaia = n => "'" + String(n).replace(/'/g, "''") + "'";
function numar(v){
  return typeof v === 'number' && isFinite(v);
}

/* --------------------------------------------------------- tipurile de coloane
   t text · i identificator (text) · e sumă · n număr întreg · y an · k loc în clasament · p procent dat în puncte
   (83,5 → 83,5%) · x diferență cu semn (verde / roșu) · s diferență cu semn, fără culori · v variație procentuală cu semn ·
   d două zecimale · z dată · m marcaj centrat, verde și îngroșat (de pildă „da") · c text scurt centrat (cod de valută) ·
   r curs de schimb, cu patru zecimale · l text lung, pe un singur rând (nu înalță rândul; textul întreg se vede în bara de formule) */
const TIP = {
  t: { fmt: 'General',            al: 'left',   wrap: true,  text: true },
  i: { fmt: '@',                  al: 'left',   wrap: false, text: true },
  e: { fmt: '#,##0',              al: 'right' },
  n: { fmt: '#,##0',              al: 'right' },
  y: { fmt: '0',                  al: 'center' },
  k: { fmt: '0',                  al: 'center' },
  p: { fmt: '0.0%',               al: 'right',  div: 100 },
  x: { fmt: '+#,##0;-#,##0;0',    al: 'right',  semn: true },
  s: { fmt: '+#,##0;-#,##0;0',    al: 'right' },
  v: { fmt: '+0.0%;-0.0%;0.0%',   al: 'right',  semn: true, div: 100 },
  d: { fmt: '#,##0.00',           al: 'right' },
  z: { fmt: 'dd.mm.yyyy',         al: 'center', data: true },
  m: { fmt: 'General',            al: 'center', wrap: false, text: true, font: { b: 1, c: CUL.verde } },
  c: { fmt: 'General',            al: 'center', wrap: false, text: true },
  r: { fmt: '#,##0.0000',         al: 'right' },
  l: { fmt: 'General',            al: 'left',   wrap: false, text: true }
};
const FMT_INCORPORATE = { 'General': 0, '0': 1, '0.00': 2, '#,##0': 3, '#,##0.00': 4, '0%': 9, '0.00%': 10, '@': 49 };

/* O dată ISO („2026-10-12") sau românească („12.10.2026") → numărul de zile Excel. */
function serialData(s){
  s = String(s);
  let m = /^(\d{4})-(\d{2})-(\d{2})/.exec(s), a, l, z;
  if(m){ a = +m[1]; l = +m[2]; z = +m[3]; }
  else if((m = /^(\d{1,2})\.(\d{1,2})\.(\d{4})$/.exec(s))){ z = +m[1]; l = +m[2]; a = +m[3]; }
  else return null;
  if(l < 1 || l > 12 || z < 1 || z > 31) return null;
  const t = Date.UTC(a, l - 1, z);
  return isNaN(t) ? null : Math.round((t - Date.UTC(1899, 11, 30)) / 86400000);
}

/* Când apelantul nu spune tipurile, le ghicim din antet și din valori. */
function deduceTipuri(antete, randuri){
  return antete.map((h, c) => {
    let nr = 0, text = 0, intregi = true, minV = Infinity, maxV = -Infinity;
    for(let i = 0; i < randuri.length; i++){
      const v = randuri[i][c];
      if(v === '' || v == null) continue;
      if(numar(v)){ nr++; if(!Number.isInteger(v)) intregi = false; minV = Math.min(minV, v); maxV = Math.max(maxV, v); }
      else text++;
    }
    if(!nr || text) return 't';
    if(/%/.test(h)) return 'p';
    if(intregi && /^(an|anul|year)$/i.test(String(h).trim()) && minV >= 1900 && maxV <= 2100) return 'y';
    return intregi ? 'n' : 'd';
  }).join('');
}

/* ------------------------------------------------------------------ stiluri */
function RegistruStiluri(){
  /* Primele intrări sunt cele cerute de format: fonts[0] = fontul implicit, fills[0..1] = „none" și
     „gray125", borders[0] = fără chenar, cellXfs[0] = stilul implicit. */
  const fonturi = [], formate = [], xfuri = [], cheiXf = new Map(), dxfuri = [];
  const umpleri = ['<fill><patternFill patternType="none"/></fill>', '<fill><patternFill patternType="gray125"/></fill>'];
  const chenare = ['<border><left/><right/><top/><bottom/><diagonal/></border>'];
  const pune = (lista, xml) => { let i = lista.indexOf(xml); if(i < 0){ i = lista.length; lista.push(xml); } return i; };

  const font = o => {
    o = o || {};
    return pune(fonturi, '<font>' + (o.b ? '<b/>' : '') + (o.i ? '<i/>' : '') + (o.u ? '<u/>' : '') +
      '<sz val="' + (o.sz || 11) + '"/><color rgb="' + (o.c || CUL.ink) + '"/><name val="Calibri"/><family val="2"/></font>');
  };
  const umplere = rgb => rgb
    ? pune(umpleri, '<fill><patternFill patternType="solid"><fgColor rgb="' + rgb + '"/><bgColor indexed="64"/></patternFill></fill>')
    : 0;
  const latura = (nume, v) => v ? '<' + nume + ' style="' + v[0] + '"><color rgb="' + v[1] + '"/></' + nume + '>' : '<' + nume + '/>';
  const chenar = o => o
    ? pune(chenare, '<border>' + latura('left', o.l) + latura('right', o.r) + latura('top', o.t) + latura('bottom', o.b) + '<diagonal/></border>')
    : 0;
  const format = cod => {
    if(cod in FMT_INCORPORATE) return FMT_INCORPORATE[cod];
    let i = formate.indexOf(cod);
    if(i < 0){ i = formate.length; formate.push(cod); }
    return 164 + i;
  };
  font({});                                                   // fonts[0]

  /* o = { fmt, font:{b,i,u,sz,c}, fill:rgb, border:{l,r,t,b:[stil,rgb]}, al:'left|center|right', v:'center|top',
           wrap:bool, indent:n } */
  function xf(o){
    o = o || {};
    const cheie = JSON.stringify(o);
    if(cheiXf.has(cheie)) return cheiXf.get(cheie);
    const nf = format(o.fmt || 'General'), fo = font(o.font), fi = umplere(o.fill), bo = chenar(o.border);
    const al = '<alignment' + (o.al ? ' horizontal="' + o.al + '"' : '') + ' vertical="' + (o.v || 'center') + '"' +
      (o.wrap ? ' wrapText="1"' : '') + (o.indent ? ' indent="' + o.indent + '"' : '') + '/>';
    const i = xfuri.length;
    xfuri.push('<xf numFmtId="' + nf + '" fontId="' + fo + '" fillId="' + fi + '" borderId="' + bo + '" xfId="0"' +
      ' applyNumberFormat="1" applyFont="1" applyFill="1" applyBorder="1" applyAlignment="1">' + al + '</xf>');
    cheiXf.set(cheie, i);
    return i;
  }
  xf({});                                                    // cellXfs[0] = implicit
  function dxf(xml){ return pune(dxfuri, xml); }

  function xml(){
    return '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>' +
      '<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">' +
      (formate.length ? '<numFmts count="' + formate.length + '">' + formate.map((c, i) => '<numFmt numFmtId="' + (164 + i) + '" formatCode="' + xe(c) + '"/>').join('') + '</numFmts>' : '') +
      '<fonts count="' + fonturi.length + '">' + fonturi.join('') + '</fonts>' +
      '<fills count="' + umpleri.length + '">' + umpleri.join('') + '</fills>' +
      '<borders count="' + chenare.length + '">' + chenare.join('') + '</borders>' +
      '<cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>' +
      '<cellXfs count="' + xfuri.length + '">' + xfuri.join('') + '</cellXfs>' +
      '<cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/></cellStyles>' +
      '<dxfs count="' + dxfuri.length + '">' + dxfuri.join('') + '</dxfs>' +
      '<tableStyles count="0" defaultTableStyle="TableStyleMedium9" defaultPivotStyle="PivotStyleLight16"/>' +
      '</styleSheet>';
  }
  return { xf: xf, dxf: dxf, xml: xml };
}

/* --------------------------------------------------------------- grafic nativ */
const EMU = 9525;                                 // un pixel
const NS_C = 'http://schemas.openxmlformats.org/drawingml/2006/chart';
const NS_A = 'http://schemas.openxmlformats.org/drawingml/2006/main';
const NS_R = 'http://schemas.openxmlformats.org/officeDocument/2006/relationships';

function textGrafic(sz, rgb, bold){
  return '<c:txPr><a:bodyPr/><a:lstStyle/><a:p><a:pPr><a:defRPr sz="' + sz + '" b="' + (bold ? 1 : 0) + '">' +
    '<a:solidFill><a:srgbClr val="' + rgb + '"/></a:solidFill><a:latin typeface="Calibri"/></a:defRPr></a:pPr><a:endParaRPr lang="ro-RO"/></a:p></c:txPr>';
}
/* Cod de format pentru axa valorilor: sume mari în mii/milioane/miliarde, ca în pagină („1,1 mld"). */
function formatAxa(max, limba){
  const en = limba === 'en';
  if(max >= 1e9) return en ? '0.0,,,"B"' : '0.0,,," mld"';
  if(max >= 1e6) return en ? '0.0,,"M"' : '0.0,," mil."';
  if(max >= 1e4) return en ? '0,"k"' : '0," mii"';
  return '#,##0';
}

/* g = { tip:'bar'|'col'|'colst'|'line', foaie, titlu, limba,
         antetR  (rândul antetului, de la 0), r0, r1 (primul și ultimul rând de date, de la 0),
         cat:coloana etichetelor, serii:[coloane], antete:[...], randuri:[[...]] (pentru memoria grafică),
         culori:[rgb...], tipCat:'t'|'y'|..., tipuri:string, legenda:bool, w, h (px) } */
function xmlGrafic(g){
  const bar = g.tip === 'bar', stivuit = g.tip === 'colst', linie = g.tip === 'line';
  const q = citeaza_foaia(g.foaie);
  const nr = g.r1 - g.r0 + 1;
  const cuvant = (c, a, b) => q + '!' + ABS(c, a) + (b != null ? ':' + ABS(c, b) : '');
  const rand = i => g.randuri[i];
  const esteNumCat = g.tipuri[g.cat] === 'y';
  let max = 0;
  g.serii.forEach(c => { for(let i = 0; i < nr; i++){ const v = rand(g.i0 + i)[c]; if(numar(v)) max = Math.max(max, Math.abs(v)); } });
  const divS = c => (TIP[g.tipuri[c]] && TIP[g.tipuri[c]].div) || 1;
  const procent = g.serii.length && g.serii.every(c => divS(c) === 100);
  const fmtVal = procent ? '0%' : formatAxa(max, g.limba);

  const serii = g.serii.map((c, k) => {
    const cul = (g.culori && g.culori[k]) || PALETA_GRAFIC[k % PALETA_GRAFIC.length];
    const cat = esteNumCat
      ? '<c:cat><c:numRef><c:f>' + xe(cuvant(g.cat, g.r0, g.r1)) + '</c:f><c:numCache><c:formatCode>0</c:formatCode><c:ptCount val="' + nr + '"/>' +
          Array.from({ length: nr }, (_, i) => numar(rand(g.i0 + i)[g.cat]) ? '<c:pt idx="' + i + '"><c:v>' + rand(g.i0 + i)[g.cat] + '</c:v></c:pt>' : '').join('') + '</c:numCache></c:numRef></c:cat>'
      : '<c:cat><c:strRef><c:f>' + xe(cuvant(g.cat, g.r0, g.r1)) + '</c:f><c:strCache><c:ptCount val="' + nr + '"/>' +
          Array.from({ length: nr }, (_, i) => '<c:pt idx="' + i + '"><c:v>' + xe(rand(g.i0 + i)[g.cat]) + '</c:v></c:pt>').join('') + '</c:strCache></c:strRef></c:cat>';
    const val = '<c:val><c:numRef><c:f>' + xe(cuvant(c, g.r0, g.r1)) + '</c:f><c:numCache><c:formatCode>General</c:formatCode><c:ptCount val="' + nr + '"/>' +
      Array.from({ length: nr }, (_, i) => { const v = rand(g.i0 + i)[c]; return numar(v) ? '<c:pt idx="' + i + '"><c:v>' + (v / divS(c)) + '</c:v></c:pt>' : ''; }).join('') +
      '</c:numCache></c:numRef></c:val>';
    const tx = '<c:tx><c:strRef><c:f>' + xe(cuvant(c, g.antetR)) + '</c:f><c:strCache><c:ptCount val="1"/><c:pt idx="0"><c:v>' + xe(g.antete[c]) + '</c:v></c:pt></c:strCache></c:strRef></c:tx>';
    if(linie){
      return '<c:ser><c:idx val="' + k + '"/><c:order val="' + k + '"/>' + tx +
        '<c:spPr><a:ln w="28575" cap="rnd"><a:solidFill><a:srgbClr val="' + cul + '"/></a:solidFill><a:round/></a:ln></c:spPr>' +
        '<c:marker><c:symbol val="circle"/><c:size val="5"/><c:spPr><a:solidFill><a:srgbClr val="' + cul + '"/></a:solidFill><a:ln w="9525"><a:solidFill><a:srgbClr val="FFFFFF"/></a:solidFill></a:ln></c:spPr></c:marker>' +
        cat + val + '<c:smooth val="0"/></c:ser>';
    }
    return '<c:ser><c:idx val="' + k + '"/><c:order val="' + k + '"/>' + tx +
      '<c:spPr><a:solidFill><a:srgbClr val="' + cul + '"/></a:solidFill></c:spPr><c:invertIfNegative val="0"/>' + cat + val + '</c:ser>';
  }).join('');

  const AX_CAT = 50010001, AX_VAL = 50010002;
  const tipGraficXml = linie
    ? '<c:lineChart><c:grouping val="standard"/><c:varyColors val="0"/>' + serii + '<c:marker val="1"/><c:axId val="' + AX_CAT + '"/><c:axId val="' + AX_VAL + '"/></c:lineChart>'
    : '<c:barChart><c:barDir val="' + (bar ? 'bar' : 'col') + '"/><c:grouping val="' + (stivuit ? 'stacked' : 'clustered') + '"/><c:varyColors val="0"/>' + serii +
      '<c:gapWidth val="' + (bar ? 55 : 70) + '"/>' + (stivuit ? '<c:overlap val="100"/>' : '') +
      '<c:axId val="' + AX_CAT + '"/><c:axId val="' + AX_VAL + '"/></c:barChart>';
  const linieAxa = '<c:spPr><a:ln w="9525"><a:solidFill><a:srgbClr val="C9CEDA"/></a:solidFill></a:ln></c:spPr>';
  const axaCat = '<c:catAx><c:axId val="' + AX_CAT + '"/><c:scaling><c:orientation val="' + (bar ? 'maxMin' : 'minMax') + '"/></c:scaling><c:delete val="0"/>' +
    '<c:axPos val="' + (bar ? 'l' : 'b') + '"/><c:numFmt formatCode="General" sourceLinked="0"/><c:majorTickMark val="none"/><c:minorTickMark val="none"/><c:tickLblPos val="nextTo"/>' +
    linieAxa + textGrafic(900, '3A4358', false) + '<c:crossAx val="' + AX_VAL + '"/><c:crosses val="autoZero"/><c:auto val="1"/><c:lblAlgn val="ctr"/><c:lblOffset val="100"/>' +
    (bar ? '<c:tickLblSkip val="1"/>' : (g.tip === 'line' && nr > 20 ? '<c:tickLblSkip val="' + Math.ceil(nr / 16) + '"/>' : '')) + '<c:noMultiLvlLbl val="0"/></c:catAx>';
  const axaVal = '<c:valAx><c:axId val="' + AX_VAL + '"/><c:scaling><c:orientation val="minMax"/>' + (linie ? '' : '<c:min val="0"/>') + '</c:scaling><c:delete val="0"/>' +
    '<c:axPos val="' + (bar ? 'b' : 'l') + '"/><c:majorGridlines><c:spPr><a:ln w="6350"><a:solidFill><a:srgbClr val="E3E7EF"/></a:solidFill></a:ln></c:spPr></c:majorGridlines>' +
    '<c:numFmt formatCode="' + xe(fmtVal) + '" sourceLinked="0"/><c:majorTickMark val="none"/><c:minorTickMark val="none"/><c:tickLblPos val="nextTo"/>' +
    '<c:spPr><a:ln><a:noFill/></a:ln></c:spPr>' + textGrafic(900, '6B7284', false) +
    '<c:crossAx val="' + AX_CAT + '"/><c:crosses val="' + (bar ? 'max' : 'autoZero') + '"/><c:crossBetween val="between"/></c:valAx>';
  const titlu = g.titlu
    ? '<c:title><c:tx><c:rich><a:bodyPr/><a:lstStyle/><a:p><a:pPr><a:defRPr sz="1200" b="1"/></a:pPr><a:r><a:rPr lang="ro-RO" sz="1200" b="1">' +
      '<a:solidFill><a:srgbClr val="14233C"/></a:solidFill><a:latin typeface="Calibri"/></a:rPr><a:t>' + xe(g.titlu) + '</a:t></a:r></a:p></c:rich></c:tx><c:overlay val="0"/></c:title><c:autoTitleDeleted val="0"/>'
    : '<c:autoTitleDeleted val="1"/>';
  const legenda = (g.serii.length > 1 && g.legenda !== false)
    ? '<c:legend><c:legendPos val="b"/><c:overlay val="0"/>' + textGrafic(900, '3A4358', false) + '</c:legend>' : '';
  return '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>' +
    '<c:chartSpace xmlns:c="' + NS_C + '" xmlns:a="' + NS_A + '" xmlns:r="' + NS_R + '">' +
    '<c:date1904 val="0"/><c:lang val="ro-RO"/><c:roundedCorners val="0"/>' +
    '<c:chart>' + titlu + '<c:plotArea><c:layout/>' + tipGraficXml + axaCat + axaVal +
    '<c:spPr><a:noFill/></c:spPr></c:plotArea>' + legenda + '<c:plotVisOnly val="1"/><c:dispBlanksAs val="gap"/></c:chart>' +
    '<c:spPr><a:solidFill><a:srgbClr val="FFFFFF"/></a:solidFill><a:ln w="9525"><a:solidFill><a:srgbClr val="D5DCE8"/></a:solidFill></a:ln></c:spPr>' +
    textGrafic(1000, '1C2230', false) +
    '</c:chartSpace>';
}
function xmlDesen(col, rand, w, h){
  return '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>' +
    '<xdr:wsDr xmlns:xdr="http://schemas.openxmlformats.org/drawingml/2006/spreadsheetDrawing" xmlns:a="' + NS_A + '">' +
    '<xdr:oneCellAnchor><xdr:from><xdr:col>' + col + '</xdr:col><xdr:colOff>0</xdr:colOff><xdr:row>' + rand + '</xdr:row><xdr:rowOff>0</xdr:rowOff></xdr:from>' +
    '<xdr:ext cx="' + (w * EMU) + '" cy="' + (h * EMU) + '"/>' +
    '<xdr:graphicFrame macro=""><xdr:nvGraphicFramePr><xdr:cNvPr id="2" name="Grafic 1"/><xdr:cNvGraphicFramePr/></xdr:nvGraphicFramePr>' +
    '<xdr:xfrm><a:off x="0" y="0"/><a:ext cx="0" cy="0"/></xdr:xfrm>' +
    '<a:graphic><a:graphicData uri="' + NS_C + '"><c:chart xmlns:c="' + NS_C + '" xmlns:r="' + NS_R + '" r:id="rId1"/></a:graphicData></a:graphic>' +
    '</xdr:graphicFrame><xdr:clientData/></xdr:oneCellAnchor></xdr:wsDr>';
}

/* ---------------------------------------------------------------------- ZIP */
const TABEL_CRC = (function(){
  const t = new Uint32Array(256);
  for(let i = 0; i < 256; i++){ let c = i; for(let k = 0; k < 8; k++) c = (c & 1) ? (0xEDB88320 ^ (c >>> 1)) : (c >>> 1); t[i] = c >>> 0; }
  return t;
})();
function crc32(u8){
  let c = 0xFFFFFFFF;
  for(let i = 0; i < u8.length; i++) c = TABEL_CRC[(c ^ u8[i]) & 0xFF] ^ (c >>> 8);
  return (c ^ 0xFFFFFFFF) >>> 0;
}
async function comprima(u8){
  if(typeof CompressionStream === 'undefined' || u8.length < 200) return null;
  try{
    const cs = new CompressionStream('deflate-raw');
    const w = cs.writable.getWriter();
    w.write(u8); w.close();
    const out = new Uint8Array(await new Response(cs.readable).arrayBuffer());
    return out.length < u8.length ? out : null;
  }catch(e){ return null; }
}
async function zip(fisiere, acum){
  const enc = new TextEncoder(), parti = [], central = [];
  let poz = 0;
  const u16 = n => [n & 255, (n >>> 8) & 255];
  const u32 = n => [n & 255, (n >>> 8) & 255, (n >>> 16) & 255, (n >>> 24) & 255];
  const d = acum || new Date();
  const timp = (d.getHours() << 11) | (d.getMinutes() << 5) | (d.getSeconds() >> 1);
  const data = (Math.max(0, d.getFullYear() - 1980) << 9) | ((d.getMonth() + 1) << 5) | d.getDate();
  for(const f of fisiere){
    const nume = enc.encode(f.nume), brut = typeof f.date === 'string' ? enc.encode(f.date) : f.date, crc = crc32(brut);
    const cmp = await comprima(brut), date = cmp || brut, metoda = cmp ? 8 : 0;
    const local = new Uint8Array([0x50, 0x4B, 0x03, 0x04].concat(u16(20), u16(0), u16(metoda), u16(timp), u16(data),
      u32(crc), u32(date.length), u32(brut.length), u16(nume.length), u16(0)));
    parti.push(local, nume, date);
    central.push({ nume: nume, crc: crc, c: date.length, u: brut.length, metoda: metoda, poz: poz });
    poz += local.length + nume.length + date.length;
  }
  const cd = [];
  let lungCd = 0;
  central.forEach(e => {
    const h = new Uint8Array([0x50, 0x4B, 0x01, 0x02].concat(u16(20), u16(20), u16(0), u16(e.metoda), u16(timp), u16(data),
      u32(e.crc), u32(e.c), u32(e.u), u16(e.nume.length), u16(0), u16(0), u16(0), u16(0), u32(0), u32(e.poz)));
    cd.push(h, e.nume);
    lungCd += h.length + e.nume.length;
  });
  const eocd = new Uint8Array([0x50, 0x4B, 0x05, 0x06].concat(u16(0), u16(0), u16(central.length), u16(central.length), u32(lungCd), u32(poz), u16(0)));
  return new Blob(parti.concat(cd, [eocd]), { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' });
}

/* ------------------------------------------------------------------ registrul */
const REL = 'http://schemas.openxmlformats.org/officeDocument/2006/relationships/';
const CT = 'application/vnd.openxmlformats-officedocument.';
const ANTET_XML = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>';

/* Lățimea unei coloane (în caractere Excel) după antet și conținut. */
function latimeColoana(c, antete, randuri, tip, setat){
  if(setat != null) return setat;
  const t = TIP[tip] || TIP.t;
  let max = 0;
  for(let i = 0; i < randuri.length; i++){
    const v = randuri[i][c];
    if(v == null || v === '') continue;
    let len;
    if(numar(v)){
      const x = t.div ? v / t.div : v;
      len = tip === 'p' || tip === 'v' ? 7 : tip === 'y' ? 5 : (Math.abs(x) >= 1000 ? String(Math.round(Math.abs(x))).length * 1.3 + 1 : String(x).length + 1) + (t.semn ? 1 : 0);
    } else {
      len = String(v).length;
    }
    if(len > max) max = len;
  }
  const cuvintele = String(antete[c]).split(/\s+/).reduce((m, w) => Math.max(m, w.length), 0);
  let w = Math.max(max + 2, cuvintele + 3);
  if(tip === 't') w = Math.min(Math.max(w, 12), 58);
  else if(tip === 'i') w = Math.min(Math.max(w, 10), 24);
  else if(tip === 'm' || tip === 'c') w = Math.min(Math.max(w, 8), 22);
  else w = Math.min(Math.max(w, 11), 22);
  return Math.round(w * 10) / 10;
}
const linii = (text, latime) => Math.max(1, String(text).split(/\n/).reduce((s, p) => s + Math.max(1, Math.ceil(p.length / Math.max(10, latime))), 0));

/* Șirurile partajate ale registrului de lucru: aceleași pentru toate foile. */
function RegistruSiruri(){
  const siruri = new Map();
  let nr = 0;
  const sir = s => {
    s = String(s == null ? '' : s).replace(RX_CTRL, '');
    if(s.length > 32000) s = s.slice(0, 32000) + '…';        // Excel nu primește mai mult de 32.767 de caractere într-o celulă
    nr++;
    let i = siruri.get(s);
    if(i === undefined){ i = siruri.size; siruri.set(s, i); }
    return i;
  };
  const xml = () => ANTET_XML + '<sst xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" count="' + nr + '" uniqueCount="' + siruri.size + '">' +
    [...siruri.keys()].map(s => '<si><t xml:space="preserve">' + xe(s) + '</t></si>').join('') + '</sst>';
  return { sir: sir, xml: xml };
}
/* Numele foilor trebuie să fie unice (fără deosebire între litere mari și mici) și de cel mult 31 de caractere:
   la a doua apariție se adaugă „ (2)”, „ (3)”… */
function numeUnice(lista){
  const folosite = new Set();
  return lista.map(n => {
    let nume = n, k = 1;
    while(folosite.has(nume.toLowerCase())){
      k++;
      const sufix = ' (' + k + ')';
      nume = n.slice(0, 31 - sufix.length).trim() + sufix;
    }
    folosite.add(nume.toLowerCase());
    return nume;
  });
}

/* spec:
     limba          'ro' | 'en'
     foaie          numele foii (max. 31 de caractere)
     titlu          titlul din banda de sus
     subtitlu       rândul de context: sursă, selecție, dată
     antete         [text...]            capetele de coloană
     tipuri         'teeen'              un caracter pe coloană (vezi TIP) — dacă lipsește, se ghicesc
     randuri        [[valori...]]        celulele, în ordinea coloanelor
     total          { eticheta, suma:[col...], raport:{col:[numărător, numitor]} }  rând de total cu formule
     randTotal      true  → ultimul rând din `randuri` e deja un total, scris ca atare, în afara filtrului
     note           ['text' | {t, u}]    sub tabel; {t, u} = text cu hyperlink
     bare           [col...]             bare în celule
     harta          { de, pana }         scară de culoare pe blocul de coloane (inclusiv)
     linkuri        { col: (rand, i) => url }   celula devine hyperlink
     latimi         { col: caractere }   lățime fixată
     inghetaColoane n                    primele n coloane rămân pe loc la derularea spre dreapta (și se repetă la tipărire)
     grupe          [{de, pana, text}]   bandă cu denumiri de grupe, deasupra antetului (coloane de la 0, ambele capete incluse)
     etichete       { col: [[text, culoareText, culoareFundal], …] }   culori pentru valori exacte („Grant", „da"), ARGB
     maxLinii       n                    rândurile cu text lung nu depășesc n linii (restul se citește în bara de formule)
     paginiLatime   n | 'auto'           pe câte pagini în lățime încape tabelul la tipărire (implicit: una)
     grafic         { tip:'bar'|'col'|'colst'|'line', cat, serii:[col...], n, ultimele, culori, titlu, legenda }
     subsol         text pentru colțul din stânga jos la tipărire (de pildă adresa site-ului)
     culoareFila    culoarea etichetei foii (ARGB, ex. 'FF1E4B8C')
     autor, data    metadate

   Un fișier cu mai multe foi: construieste({ limba, autor, subsol, foi:[spec1, spec2, …] }) — fiecare element e o specificație
   ca mai sus. Numele foilor se fac unice automat. O celulă cu link poate duce într-o altă foaie: adresa „#Numele foii”
   (așa cum a fost cerut în `foaie`) face un link în interiorul fișierului, către celula A1 a acelei foi. */
function construiesteFoaie(spec, idx, ctx){
  const en = ctx.en;
  const antete = spec.antete.map(x => String(x == null ? '' : x));
  const nC = antete.length;
  let randuri = spec.randuri.map(r => { const o = r.slice(0, nC); while(o.length < nC) o.push(''); return o; });
  let randTotalFinal = null;
  if(spec.randTotal && randuri.length){ randTotalFinal = randuri.pop(); }
  const nR = randuri.length;
  const tipuri = (spec.tipuri && spec.tipuri.length === nC ? spec.tipuri : deduceTipuri(antete, randuri)).split('');
  const foaie = ctx.nume;
  const S = ctx.S, sir = ctx.sir;

  /* ---- lățimi ---- */
  const latimi = antete.map((_, c) => latimeColoana(c, antete, randuri, tipuri[c], spec.latimi && spec.latimi[c]));
  /* Banda de titlu trebuie să aibă loc pentru titlu și pentru rândul de context: dacă tabelul e
     îngust, lărgim coloana de text (sau, fără text, toate coloanele în mod egal). */
  const LATIME_MIN = 80;
  let totalLat = latimi.reduce((a, b) => a + b, 0);
  if(totalLat < LATIME_MIN){
    const lipsa = LATIME_MIN - totalLat, tc = tipuri.indexOf('t');
    if(tc >= 0) latimi[tc] += lipsa;
    else latimi.forEach((w, c) => { latimi[c] = Math.round((w + lipsa / nC) * 10) / 10; });
    totalLat = latimi.reduce((a, b) => a + b, 0);
  }
  /* La un tabel lat, un titlu unit pe toată lățimea ar ieși din ecran: textul s-ar vedea doar până la marginea ferestrei.
     Textul (titlu, context, note) se unește deci doar peste primele coloane, cât încape pe ecran; fundalul benzii
     rămâne pe toată lățimea. */
  const LATIME_TEXT = 150;
  let nT = nC, latT = totalLat;
  if(totalLat > LATIME_TEXT * 1.15){
    nT = 0; latT = 0;
    while(nT < nC && latT < LATIME_TEXT){ latT += latimi[nT]; nT++; }
  }
  const nInghet = Math.max(0, Math.min(Math.floor(+spec.inghetaColoane || 0), nC - 1));
  const maxLinii = Math.max(0, Math.floor(+spec.maxLinii || 0));
  const grupe = [];
  (spec.grupe || []).filter(g => g && g.de >= 0 && g.pana < nC && g.pana >= g.de).sort((a, b) => a.de - b.de)
    .forEach(g => { if(!grupe.length || g.de > grupe[grupe.length - 1].pana) grupe.push(g); });

  /* ---- rânduri ---- */
  let r = 0;
  const rTitlu = r++;
  const rSub = spec.subtitlu ? r++ : -1;
  const rSpatiu = r++;
  const rGrupe = grupe.length ? r++ : -1;
  const rAntet = r++;
  const r0 = r, r1 = r0 + nR - 1;                                      // rândurile de date (de la 0)
  const rTotal = (spec.total && nR) ? r1 + 1 : (randTotalFinal ? r1 + 1 : -1);
  const ultimulTabel = rTotal >= 0 ? rTotal : r1;
  const note = (spec.note || []).filter(Boolean);
  const rNote0 = ultimulTabel + 2;

  /* ---- stiluri ---- */
  const stBanda = {
    titlu: S.xf({ font: { b: 1, sz: 17, c: CUL.alb }, fill: CUL.navyDeep, border: { b: ['medium', CUL.gold] }, al: 'left', wrap: true, indent: 1 }),
    sub: S.xf({ font: { sz: 10, c: 'FF2A3446' }, fill: CUL.banda, al: 'left', wrap: true, indent: 1 }),
    antet: S.xf({ font: { b: 1, sz: 11, c: CUL.alb }, fill: CUL.navy, border: { b: ['medium', CUL.gold] }, al: 'center', wrap: true }),
    antetStanga: S.xf({ font: { b: 1, sz: 11, c: CUL.alb }, fill: CUL.navy, border: { b: ['medium', CUL.gold] }, al: 'left', wrap: true, indent: 1 }),
    nota: S.xf({ font: { i: 1, sz: 9, c: CUL.dim }, al: 'left', wrap: true, v: 'top' }),
    notaLink: S.xf({ font: { u: 1, sz: 9, c: CUL.link }, al: 'left', wrap: true, v: 'top' })
  };
  const stGrupa = [CUL.total, CUL.banda].map(f => S.xf({ font: { b: 1, sz: 10, c: CUL.navyDeep }, fill: f, border: { b: ['thin', CUL.navy] }, al: 'center', wrap: true }));
  /* Cu înălțimea limitată (maxLinii), textul lung se taie jos: începe sus, ca să se vadă întregi primele linii. */
  const vData = maxLinii > 1 ? 'top' : undefined;
  const stData = tipuri.map((tp, c) => {
    const t = TIP[tp] || TIP.t;
    return S.xf({ fmt: t.fmt, font: t.font, border: { b: ['thin', CUL.linie] }, al: t.al, wrap: !!t.wrap, indent: t.al === 'left' ? 1 : 0, v: vData });
  });
  const stLink = tipuri.map((tp, c) => S.xf({ font: { u: 1, c: CUL.link }, border: { b: ['thin', CUL.linie] }, al: 'left', wrap: false, indent: 1, v: vData }));
  const stTotal = tipuri.map((tp, c) => {
    const t = TIP[tp] || TIP.t;
    return S.xf({ fmt: t.fmt, font: { b: 1, c: CUL.navyDeep }, fill: CUL.total, border: { t: ['medium', CUL.navy], b: ['thin', CUL.navy] }, al: c === 0 ? 'left' : t.al, indent: c === 0 ? 1 : 0 });
  });

  /* O adresă „https://…” duce în afara fișierului; „#Numele foii” duce la altă foaie a aceluiași fișier (la celula A1). */
  const legatura = (celula, url) => {
    if(!url) return null;
    if(/^https?:\/\//i.test(url)) return { ref: celula, url: url };
    if(url.charAt(0) === '#'){
      const final = ctx.hartaNume.get(url.slice(1));
      if(final) return { ref: celula, loc: citeaza_foaia(final) + '!A1', afisat: final };
    }
    return null;
  };
  const celText = (c, rr, st, text) => '<c r="' + ref(c, rr) + '" s="' + st + '" t="s"><v>' + sir(text) + '</v></c>';
  const celGol = (c, rr, st) => '<c r="' + ref(c, rr) + '" s="' + st + '"/>';
  const celNum = (c, rr, st, v) => '<c r="' + ref(c, rr) + '" s="' + st + '"><v>' + v + '</v></c>';

  const linkuri = [];                                                      // [celulă, adresă]
  const randuriXml = [];
  const unirea = [];                                                       // zone unite
  const inaltimi = {};
  const rand_ = (rr, celule, ht) => { randuriXml[rr] = '<row r="' + (rr + 1) + '"' + (ht ? ' ht="' + ht + '" customHeight="1"' : '') + '>' + celule + '</row>'; };

  /* titlu */
  {
    let x = celText(0, rTitlu, stBanda.titlu, spec.titlu);
    for(let c = 1; c < nC; c++) x += celGol(c, rTitlu, stBanda.titlu);
    rand_(rTitlu, x, 8 + 25 * linii(spec.titlu, latT / 1.7));
    if(nT > 1) unirea.push(ref(0, rTitlu) + ':' + ref(nT - 1, rTitlu));
  }
  /* rândul de context */
  if(rSub >= 0){
    const nl = linii(spec.subtitlu, latT * 1.15);
    let x = celText(0, rSub, stBanda.sub, spec.subtitlu);
    for(let c = 1; c < nC; c++) x += celGol(c, rSub, stBanda.sub);
    rand_(rSub, x, Math.min(110, 14 * nl + 6));
    if(nT > 1) unirea.push(ref(0, rSub) + ':' + ref(nT - 1, rSub));
  }
  rand_(rSpatiu, '', 6);
  /* grupe de coloane: o bandă deasupra antetului, cu denumirea fiecărei grupe unită peste coloanele ei */
  if(rGrupe >= 0){
    let x = '';
    grupe.forEach((g, k) => {
      for(let c = g.de; c <= g.pana; c++) x += c === g.de ? celText(c, rGrupe, stGrupa[k % 2], g.text) : celGol(c, rGrupe, stGrupa[k % 2]);
      if(g.pana > g.de) unirea.push(ref(g.de, rGrupe) + ':' + ref(g.pana, rGrupe));
    });
    rand_(rGrupe, x, 21);
  }

  /* antet */
  {
    let x = '';
    let maxL = 1;
    antete.forEach((h, c) => {
      x += celText(c, rAntet, (TIP[tipuri[c]] || TIP.t).al === 'left' ? stBanda.antetStanga : stBanda.antet, h);
      maxL = Math.max(maxL, linii(h, latimi[c] - 1));
    });
    rand_(rAntet, x, Math.min(78, Math.max(26, 15 * maxL + 8)));
  }

  /* date */
  const coloaneLink = spec.linkuri ? Object.keys(spec.linkuri).map(Number) : [];
  const ignora = [];
  for(let i = 0; i < nR; i++){
    const rr = r0 + i, rand = randuri[i];
    let x = '';
    for(let c = 0; c < nC; c++){
      const v = rand[c], tp = tipuri[c], t = TIP[tp] || TIP.t;
      let st = stData[c], url = null;
      if(coloaneLink.indexOf(c) >= 0 && v !== '' && v != null){
        try{ url = spec.linkuri[c](rand, i); }catch(e){ url = null; }
        const l = legatura(ref(c, rr), url);
        if(l){ st = stLink[c]; linkuri.push(l); } else url = null;
      }
      if(v === '' || v == null || (typeof v === 'number' && !isFinite(v))){ x += celGol(c, rr, st); continue; }
      if(t.data){
        const sd = typeof v === 'number' ? v : serialData(v);
        x += sd == null ? celText(c, rr, st, v) : celNum(c, rr, st, sd);
      } else if(t.text){
        x += celText(c, rr, st, v);
      } else if(numar(v)){
        x += celNum(c, rr, st, t.div ? v / t.div : v);
      } else {
        x += celText(c, rr, st, v);                                // ex. „NA", „nespecificat" într-o coloană de ani
      }
    }
    /* Rând cu text lung: înălțimea se fixează la maxLinii linii doar când textul are nevoie de mai multe. Fără ea, aplicația
       ar înălța rândul cât cere cel mai lung text, iar o listă cu sute de rânduri ar deveni greu de parcurs. Rândurile care
       încap în maxLinii linii nu primesc înălțime: aplicația le potrivește singură, exact, la deschidere (nu ghicim noi). */
    let ht = 0;
    if(maxLinii > 1){
      let nevoie = 1;
      for(let c = 0; c < nC; c++){
        const t = TIP[tipuri[c]] || TIP.t, v = rand[c];
        if(t.wrap && coloaneLink.indexOf(c) < 0 && typeof v === 'string' && v !== '') nevoie = Math.max(nevoie, linii(v, latimi[c] * 1.08));
      }
      if(nevoie > maxLinii) ht = maxLinii * 15;
    }
    rand_(rr, x, ht);
  }
  if(nR) tipuri.forEach((tp, c) => { if(tp === 'i') ignora.push(ref(c, r0) + ':' + ref(c, r1)); });

  /* rândul de total */
  const sumeTotal = {};                                                  // coloană → valoare, pentru memoria formulei
  if(rTotal >= 0){
    let x = '';
    if(randTotalFinal){
      randTotalFinal.forEach((v, c) => {
        const tp = tipuri[c], t = TIP[tp] || TIP.t;
        if(v === '' || v == null) x += celGol(c, rTotal, stTotal[c]);
        else if(numar(v) && !t.text) x += celNum(c, rTotal, stTotal[c], t.div ? v / t.div : v);
        else x += celText(c, rTotal, stTotal[c], v);
      });
    } else {
      const T = spec.total, suma = new Set(T.suma || []);
      for(let c = 0; c < nC; c++){
        if(c === 0) { x += celText(c, rTotal, stTotal[c], T.eticheta || 'Total'); continue; }
        if(suma.has(c)){
          const t = TIP[tipuri[c]] || TIP.t;
          let s = 0;
          for(let i = 0; i < nR; i++){ const v = randuri[i][c]; if(numar(v)) s += t.div ? v / t.div : v; }
          sumeTotal[c] = s;
          x += '<c r="' + ref(c, rTotal) + '" s="' + stTotal[c] + '"><f>SUBTOTAL(109,' + ref(c, r0) + ':' + ref(c, r1) + ')</f><v>' + s + '</v></c>';
        } else if(T.raport && T.raport[c]){
          const [nu, de] = T.raport[c];
          const a = sumeTotal[nu] != null ? sumeTotal[nu] : 0, b = sumeTotal[de] != null ? sumeTotal[de] : 0;
          const t = TIP[tipuri[c]] || TIP.t;
          x += '<c r="' + ref(c, rTotal) + '" s="' + stTotal[c] + '"' + (b ? '' : ' t="str"') + '><f>IF(' + ref(de, rTotal) + '=0,"",' + ref(nu, rTotal) + '/' + ref(de, rTotal) + ')</f><v>' + (b ? a / b : '') + '</v></c>';
        } else x += celGol(c, rTotal, stTotal[c]);
      }
    }
    rand_(rTotal, x, 20);
  }

  /* note */
  note.forEach((n, i) => {
    const rr = rNote0 + i, text = typeof n === 'string' ? n : n.t, url = typeof n === 'string' ? null : n.u;
    const lnk = legatura(ref(0, rr), url), hl = !!lnk;
    let x = celText(0, rr, hl ? stBanda.notaLink : stBanda.nota, text);
    for(let c = 1; c < nC; c++) x += celGol(c, rr, hl ? stBanda.notaLink : stBanda.nota);
    rand_(rr, x, Math.min(90, 12.5 * linii(text, latT * 1.3) + 3));
    if(nT > 1) unirea.push(ref(0, rr) + ':' + ref(nT - 1, rr));
    if(lnk) linkuri.push(lnk);
  });
  const ultimulRand = Math.max(rNote0 + note.length - 1, ultimulTabel);

  /* ---- formatare condiționată ---- */
  let prioritate = 1;
  const cf = [];
  const refZona = (c0, c1) => ref(c0, r0) + ':' + ref(c1, r1);
  if(nR){
    if(spec.harta){
      cf.push('<conditionalFormatting sqref="' + refZona(spec.harta.de, spec.harta.pana) + '"><cfRule type="colorScale" priority="' + (prioritate++) + '"><colorScale>' +
        '<cfvo type="min"/><cfvo type="max"/><color rgb="FFFFFFFF"/><color rgb="FF6FA3E0"/></colorScale></cfRule></conditionalFormatting>');
    }
    (spec.bare || []).forEach(c => {
      cf.push('<conditionalFormatting sqref="' + refZona(c, c) + '"><cfRule type="dataBar" priority="' + (prioritate++) + '"><dataBar>' +
        '<cfvo type="num" val="0"/><cfvo type="max"/><color rgb="FF9DB8DF"/></dataBar></cfRule></conditionalFormatting>');
    });
    Object.keys(spec.etichete || {}).forEach(col => {
      const c = +col;
      if(!(c >= 0 && c < nC)) return;
      (spec.etichete[col] || []).forEach(reg => {
        const dx = S.dxf('<dxf><font><b/><color rgb="' + reg[1] + '"/></font><fill><patternFill><bgColor rgb="' + reg[2] + '"/></patternFill></fill></dxf>');
        cf.push('<conditionalFormatting sqref="' + refZona(c, c) + '"><cfRule type="cellIs" dxfId="' + dx + '" priority="' + (prioritate++) + '" operator="equal">' +
          '<formula>"' + xe(String(reg[0]).replace(/"/g, '""')) + '"</formula></cfRule></conditionalFormatting>');
      });
    });
    const dxVerde = S.dxf('<dxf><font><color rgb="' + CUL.verde + '"/></font></dxf>');
    const dxRosu = S.dxf('<dxf><font><color rgb="' + CUL.rosu + '"/></font></dxf>');
    tipuri.forEach((tp, c) => {
      if(!(TIP[tp] && TIP[tp].semn)) return;
      cf.push('<conditionalFormatting sqref="' + refZona(c, c) + '">' +
        '<cfRule type="cellIs" dxfId="' + dxVerde + '" priority="' + (prioritate++) + '" operator="greaterThan"><formula>0</formula></cfRule>' +
        '<cfRule type="cellIs" dxfId="' + dxRosu + '" priority="' + (prioritate++) + '" operator="lessThan"><formula>0</formula></cfRule></conditionalFormatting>');
    });
    const dxZebra = S.dxf('<dxf><fill><patternFill><bgColor rgb="' + CUL.zebra + '"/></patternFill></fill></dxf>');
    cf.push('<conditionalFormatting sqref="' + refZona(0, nC - 1) + '"><cfRule type="expression" dxfId="' + dxZebra + '" priority="' + (prioritate++) + '">' +
      '<formula>MOD(SUBTOTAL(103,$A$' + (r0 + 1) + ':$A' + (r0 + 1) + '),2)=0</formula></cfRule></conditionalFormatting>');
  }

  /* ---- grafic ---- */
  let grafic = null;
  const gs = spec.grafic;
  if(gs && nR >= 2 && gs.serii && gs.serii.length){
    let i0 = 0, nrG = nR;
    if(gs.ultimele && gs.ultimele < nR){ i0 = nR - gs.ultimele; nrG = gs.ultimele; }
    else if(gs.n && gs.n < nR){ nrG = gs.n; }
    const nSerii = gs.serii.length;
    const orizontal = gs.tip === 'bar';
    const w = gs.w || (orizontal ? 660 : Math.max(640, Math.min(980, 120 + nrG * 26)));
    const h = gs.h || (orizontal ? Math.max(320, Math.min(760, 110 + nrG * (nSerii > 1 ? 30 : 22))) : 380);
    const xmlG = xmlGrafic({
      tip: gs.tip || 'bar', foaie: foaie, titlu: gs.titlu, limba: spec.limba, antetR: rAntet,
      r0: r0 + i0, r1: r0 + i0 + nrG - 1, i0: i0, cat: gs.cat || 0, serii: gs.serii, antete: antete, randuri: randuri,
      culori: gs.culori, tipuri: tipuri, legenda: gs.legenda
    });
    grafic = { xml: xmlG, desen: xmlDesen(nC + 1, r0, w, h) };
  }

  /* ---- foaia ---- */
  let idRel = 0;                                                           // linkurile din afara fișierului au câte o relație
  linkuri.forEach(l => { if(l.url) l.rid = ++idRel; });
  const kG = grafic ? ++ctx.nrGrafice : 0;                                 // graficele se numără pe tot fișierul: chart1.xml, chart2.xml…
  const colInghet = lit(nInghet), celulaPane = colInghet + (rAntet + 2);
  const panou = nInghet
    ? '<pane xSplit="' + nInghet + '" ySplit="' + (rAntet + 1) + '" topLeftCell="' + celulaPane + '" activePane="bottomRight" state="frozen"/>' +
      '<selection pane="topRight" activeCell="' + colInghet + '1" sqref="' + colInghet + '1"/>' +
      '<selection pane="bottomLeft" activeCell="A' + (rAntet + 2) + '" sqref="A' + (rAntet + 2) + '"/>' +
      '<selection pane="bottomRight" activeCell="' + celulaPane + '" sqref="' + celulaPane + '"/>'
    : '<pane ySplit="' + (rAntet + 1) + '" topLeftCell="A' + (rAntet + 2) + '" activePane="bottomLeft" state="frozen"/>' +
      '<selection pane="bottomLeft" activeCell="A' + (rAntet + 2) + '" sqref="A' + (rAntet + 2) + '"/>';
  const paginiLatime = spec.paginiLatime === 'auto' ? Math.max(1, Math.ceil(totalLat / 150)) : Math.max(1, Math.floor(+spec.paginiLatime || 1));
  const sheet = ANTET_XML +
    '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="' + NS_R + '">' +
    '<sheetPr><tabColor rgb="' + (spec.culoareFila || CUL.navy) + '"/><pageSetUpPr fitToPage="1"/></sheetPr>' +
    '<dimension ref="A1:' + ref(Math.max(nC - 1, 0), ultimulRand) + '"/>' +
    '<sheetViews><sheetView showGridLines="0"' + (idx === 0 ? ' tabSelected="1"' : '') + ' workbookViewId="0">' +
      panou + '</sheetView></sheetViews>' +
    '<sheetFormatPr defaultRowHeight="15"/>' +
    '<cols>' + latimi.map((w, c) => '<col min="' + (c + 1) + '" max="' + (c + 1) + '" width="' + (w + 0.7).toFixed(1) + '" customWidth="1"/>').join('') + '</cols>' +
    '<sheetData>' + randuriXml.map(x => x || '').join('') + '</sheetData>' +
    (nR ? '<autoFilter ref="' + ref(0, rAntet) + ':' + ref(nC - 1, r1) + '"/>' : '') +
    (unirea.length ? '<mergeCells count="' + unirea.length + '">' + unirea.map(m => '<mergeCell ref="' + m + '"/>').join('') + '</mergeCells>' : '') +
    cf.join('') +
    (linkuri.length ? '<hyperlinks>' + linkuri.map(l => l.url
      ? '<hyperlink ref="' + l.ref + '" r:id="rId' + l.rid + '"/>'
      : '<hyperlink ref="' + l.ref + '" location="' + xe(l.loc) + '" display="' + xe(l.afisat) + '"/>').join('') + '</hyperlinks>' : '') +
    '<printOptions horizontalCentered="1"/>' +
    '<pageMargins left="0.5" right="0.5" top="0.6" bottom="0.7" header="0.3" footer="0.3"/>' +
    '<pageSetup paperSize="9" orientation="landscape" fitToWidth="' + paginiLatime + '" fitToHeight="0"/>' +
    '<headerFooter><oddFooter>&amp;L&amp;8 ' + xe(String(spec.subsol || '').replace(/&/g, '&&')) + '&amp;C&amp;8 &amp;A&amp;R&amp;8 ' + (en ? 'Page' : 'Pagina') + ' &amp;P / &amp;N</oddFooter></headerFooter>' +
    (ignora.length ? '<ignoredErrors>' + ignora.map(z => '<ignoredError sqref="' + z + '" numberStoredAsText="1"/>').join('') + '</ignoredErrors>' : '') +
    (grafic ? '<drawing r:id="rId' + (idRel + 1) + '"/>' : '') +
    '</worksheet>';

  const relFoaie = ANTET_XML + '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">' +
    linkuri.filter(l => l.url).map(l => '<Relationship Id="rId' + l.rid + '" Type="' + REL + 'hyperlink" Target="' + xe(l.url) + '" TargetMode="External"/>').join('') +
    (grafic ? '<Relationship Id="rId' + (idRel + 1) + '" Type="' + REL + 'drawing" Target="../drawings/drawing' + kG + '.xml"/>' : '') +
    '</Relationships>';

  /* ---- numele definite ale foii (filtrul și rândurile care se repetă la tipărire) ---- */
  const nF = citeaza_foaia(foaie);
  const nume_def = (nR ? '<definedName name="_xlnm._FilterDatabase" localSheetId="' + idx + '" hidden="1">' + xe(nF) + '!' + ABS(0, rAntet) + ':' + ABS(nC - 1, r1) + '</definedName>' : '') +
    '<definedName name="_xlnm.Print_Titles" localSheetId="' + idx + '">' + (nInghet ? xe(nF) + '!$A:$' + lit(nInghet - 1) + ',' : '') +
      xe(nF) + '!$' + (rAntet + 1) + ':$' + (rAntet + 1) + '</definedName>';
  return { sheet: sheet, rels: relFoaie, grafic: grafic ? { xml: grafic.xml, desen: grafic.desen, k: kG } : null, defNames: nume_def };
}

async function construieste(spec){
  const foiSpec = (Array.isArray(spec.foi) && spec.foi.length) ? spec.foi : [spec];
  const prima = foiSpec[0];
  const limba = spec.limba || prima.limba;
  const en = limba === 'en';
  const acum = spec.data instanceof Date ? spec.data : (prima.data instanceof Date ? prima.data : new Date());
  const nume = numeUnice(foiSpec.map(f => nume_foaie(f.foaie, en ? 'Data' : 'Date')));
  const hartaNume = new Map();                                             // numele cerut → numele final, pentru linkurile dintre foi
  foiSpec.forEach((f, i) => { if(!hartaNume.has(String(f.foaie))) hartaNume.set(String(f.foaie), nume[i]); });
  const registruSiruri = RegistruSiruri();
  const ctx = { en: en, S: RegistruStiluri(), sir: registruSiruri.sir, nrGrafice: 0, hartaNume: hartaNume, nume: '' };
  const foi = foiSpec.map((f, i) => {
    ctx.nume = nume[i];
    return construiesteFoaie(Object.assign({ limba: limba, subsol: spec.subsol }, f), i, ctx);
  });
  const n = foi.length;
  const titlu = spec.titlu || prima.titlu || '';
  const autor = spec.autor || prima.autor || 'nistor.vivi.md';

  /* ---- registru, foi, metadate ---- */
  const workbook = ANTET_XML + '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="' + NS_R + '">' +
    '<bookViews><workbookView xWindow="0" yWindow="0" windowWidth="28800" windowHeight="15000" activeTab="0"/></bookViews>' +
    '<sheets>' + nume.map((nm, i) => '<sheet name="' + xe(nm) + '" sheetId="' + (i + 1) + '" r:id="rId' + (i + 1) + '"/>').join('') + '</sheets>' +
    '<definedNames>' + foi.map(f => f.defNames).join('') + '</definedNames>' +
    '<calcPr calcId="191029" fullCalcOnLoad="1"/></workbook>';
  const relWb = ANTET_XML + '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">' +
    foi.map((f, i) => '<Relationship Id="rId' + (i + 1) + '" Type="' + REL + 'worksheet" Target="worksheets/sheet' + (i + 1) + '.xml"/>').join('') +
    '<Relationship Id="rId' + (n + 1) + '" Type="' + REL + 'styles" Target="styles.xml"/>' +
    '<Relationship Id="rId' + (n + 2) + '" Type="' + REL + 'sharedStrings" Target="sharedStrings.xml"/></Relationships>';
  const iso = acum.toISOString().replace(/\.\d+Z$/, 'Z');
  const core = ANTET_XML + '<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" ' +
    'xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:dcterms="http://purl.org/dc/terms/" xmlns:dcmitype="http://purl.org/dc/dcmitype/" ' +
    'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"><dc:title>' + xe(titlu) + '</dc:title><dc:creator>' + xe(autor) + '</dc:creator>' +
    '<dcterms:created xsi:type="dcterms:W3CDTF">' + iso + '</dcterms:created><dcterms:modified xsi:type="dcterms:W3CDTF">' + iso + '</dcterms:modified></cp:coreProperties>';
  const app = ANTET_XML + '<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties"><Application>' + xe(autor) + '</Application></Properties>';
  const grafice = foi.filter(f => f.grafic).map(f => f.grafic);
  const tipuriContinut = ANTET_XML + '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">' +
    '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/>' +
    '<Override PartName="/xl/workbook.xml" ContentType="' + CT + 'spreadsheetml.sheet.main+xml"/>' +
    foi.map((f, i) => '<Override PartName="/xl/worksheets/sheet' + (i + 1) + '.xml" ContentType="' + CT + 'spreadsheetml.worksheet+xml"/>').join('') +
    '<Override PartName="/xl/styles.xml" ContentType="' + CT + 'spreadsheetml.styles+xml"/>' +
    '<Override PartName="/xl/sharedStrings.xml" ContentType="' + CT + 'spreadsheetml.sharedStrings+xml"/>' +
    grafice.map(g => '<Override PartName="/xl/drawings/drawing' + g.k + '.xml" ContentType="' + CT + 'drawing+xml"/>' +
      '<Override PartName="/xl/charts/chart' + g.k + '.xml" ContentType="' + CT + 'drawingml.chart+xml"/>').join('') +
    '<Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>' +
    '<Override PartName="/docProps/app.xml" ContentType="' + CT + 'extended-properties+xml"/></Types>';
  const relRadacina = ANTET_XML + '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">' +
    '<Relationship Id="rId1" Type="' + REL + 'officeDocument" Target="xl/workbook.xml"/>' +
    '<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/>' +
    '<Relationship Id="rId3" Type="' + REL + 'extended-properties" Target="docProps/app.xml"/></Relationships>';

  const fisiere = [
    { nume: '[Content_Types].xml', date: tipuriContinut },
    { nume: '_rels/.rels', date: relRadacina },
    { nume: 'xl/workbook.xml', date: workbook },
    { nume: 'xl/_rels/workbook.xml.rels', date: relWb },
    { nume: 'xl/styles.xml', date: ctx.S.xml() },
    { nume: 'xl/sharedStrings.xml', date: registruSiruri.xml() }
  ];
  foi.forEach((f, i) => {
    fisiere.push({ nume: 'xl/worksheets/sheet' + (i + 1) + '.xml', date: f.sheet });
    fisiere.push({ nume: 'xl/worksheets/_rels/sheet' + (i + 1) + '.xml.rels', date: f.rels });
  });
  grafice.forEach(g => {
    fisiere.push({ nume: 'xl/drawings/drawing' + g.k + '.xml', date: g.desen });
    fisiere.push({ nume: 'xl/drawings/_rels/drawing' + g.k + '.xml.rels', date: ANTET_XML + '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">' +
      '<Relationship Id="rId1" Type="' + REL + 'chart" Target="../charts/chart' + g.k + '.xml"/></Relationships>' });
    fisiere.push({ nume: 'xl/charts/chart' + g.k + '.xml', date: g.xml });
  });
  fisiere.push({ nume: 'docProps/core.xml', date: core }, { nume: 'docProps/app.xml', date: app });
  return zip(fisiere, acum);
}

const API = { construieste: construieste, serialData: serialData, deduceTipuri: deduceTipuri, TIP: TIP };
if(typeof window !== 'undefined') window.XlsxStil = API;
if(typeof module !== 'undefined' && module.exports) module.exports = API;
})();
