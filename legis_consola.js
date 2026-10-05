/* legis_consola.js — scoate din legis.md documentele atașate la actele de acord și pregătește
   sumele pentru verificare. Nu trebuie instalat nimic.

   CUM SE FOLOSEȘTE
   1. Deschide https://www.legis.md în Edge sau Chrome (bifează „nu sunt robot" dacă apare).
   2. Apasă F12 și alege fila „Console".
   3. Copiază TOT acest fișier, lipește-l în consolă și apasă Enter.
      (Dacă browserul cere, scrie întâi:  allow pasting  și apasă Enter.)
   4. Lasă fila deschisă. În colțul din dreapta-jos apare o casetă cu progresul.
      Dacă browserul întreabă dacă permiți descărcarea mai multor fișiere, alege „Permite".
   5. La sfârșit (sau când apeși „Descarcă ce am până acum") se descarcă:
        documente_verificare_1.json, _2.json …  — DE TRIMIS LA VERIFICAT (încarcă-le în conversație)
        legis_sume.json                          — sumele alese automat (se urcă pe GitHub în „date"
                                                   abia după verificare)
        sume_lipsa.csv                           — ce a rămas fără sumă, cu motivul

   Dacă închizi fila sau apare din nou verificarea Cloudflare, reia de la pasul 1:
   scriptul continuă de unde a rămas (ține minte în browser ce a citit deja).

   CE FACE
   Pentru fiecare act de acord din registru (legi, hotărâri, ordine — fără decrete)
   deschide fișa actului pe legis.md, găsește PDF-urile atașate (textul acordului) și le
   descarcă. Actele parcurse la o rulare anterioară nu se reiau. Scoate textul — la cele
   scanate, cu OCR — și păstrează din fiecare document începutul lui și pasajele în care
   apar sume, cu textul din jur. Acestea ajung în documente_verificare_N.json: destul cât
   să se vadă, pentru fiecare acord, care sumă e a lui și care e o tranșă, un comision sau
   bugetul altcuiva. PDF-urile întregi nu se păstrează (ar fi mii de megaocteți).
   Actele noi, necitite încă, le citește și pe ele (textul actului). Sumele puse de mână rămân.

   Regulile de alegere a sumei sunt aceleași ca în legis_sume.py (suma_acord,
   sume_din_text); formatul lui legis_sume.json e același ca al lui legis_atasamente.py.

   Opțiuni (scrise în consolă ÎNAINTE de a lipi scriptul), de exemplu:
     window.LA_CFG = { DOAR: ['132350', '132354'] }   // doar aceste acte (doc_id)
     window.LA_CFG = { REINCEARCA: true }             // reia erorile și scanatele rămase necitite
     window.LA_CFG = { OCR: false }                   // fără OCR (mult mai repede; scanatele rămân necitite)
     window.LA_CFG = { PAGINI_OCR: 20 }               // câte pagini citește OCR-ul dintr-un PDF scanat
     window.LA_CFG = { DOVEZI: 'tot' }                // reia și actele deja parcurse, ca să strângă pasajele din toate
     window.LA_CFG = { DOVEZI: false }                // doar sumele, fără pasajele pentru verificare
   În timpul rulării:  LA.stop()  oprește și descarcă;  LA.descarca()  descarcă ce e până acum;
   LA.reset()  uită progresul ținut în browser. */
(async function () {
  'use strict';

  var CFG = Object.assign({
    SITE: 'https://nistor.vivi.md',          // de unde iau registrul și sumele de până acum
    BAZA: location.origin,                   // legis.md
    OCR: true, PAGINI_OCR: 12, PAGINI_TEXT: 80, PAUZA: 400, MAX_MB: 30,
    LIMITA_DESC: 180, LIMITA_DOC: 360,       // secunde: cât aștept descărcarea, respectiv citirea unui document
    DOVEZI: true, PASAJE: 8,                 // păstrează, din fiecare document, pasajele cu sume, pentru verificare
    DOAR: null, REINCEARCA: false, TOT: false, TEST: false,
    PDFJS: 'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.min.js',
    PDFJS_WORKER: 'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.worker.min.js',
    TESSERACT: 'https://cdn.jsdelivr.net/npm/tesseract.js@5.1.1/dist/tesseract.min.js'
  }, window.LA_CFG || {});

  if (!CFG.TEST && !/(^|\.)legis\.md$/.test(location.hostname)) {
    alert('Scriptul trebuie lipit în consola paginii www.legis.md.\nDeschide întâi https://www.legis.md, apoi apasă F12 și lipește-l din nou.');
    return;
  }
  if (window.LA && window.LA.ruleaza) { alert('Scriptul rulează deja în această filă.'); return; }

  /*<SUME>*/
  // ------------------------------------------------ sumele din text (ca în legis_sume.py)
  function fold(s) { return String(s == null ? '' : s).normalize('NFD').replace(/[^\x00-\x7F]/g, '').toLowerCase(); }

  var VALUTE = [
    ['euro|eur\\b|€', 'EUR'],
    ['dolari(?:\\s+(?:sua|s\\.u\\.a\\.?|ai\\s+sua|americani))?|usd\\b|\\$', 'USD'],
    ['drepturi\\s+speciale\\s+de\\s+tragere|d\\.\\s?s\\.\\s?t\\.?|dst\\b|dts\\b|sdr\\b|xdr\\b', 'DST'],
    ['yeni(?:\\s+japonezi)?|yen\\b|jpy\\b', 'JPY'],
    ['franci\\s+elve\\S{0,2}ieni|chf\\b', 'CHF'],
    ['lire\\s+sterline|gbp\\b', 'GBP'],
    ['coroane\\s+suedeze|sek\\b', 'SEK'],
    ['coroane\\s+daneze|dkk\\b', 'DKK'],
    ['zloti|pln\\b', 'PLN'],
    ['yuani|cny\\b|rmb\\b', 'CNY'],
    ['ecu\\b', 'ECU'],
    ['m[aă]rci\\s+germane|dem\\b', 'DEM'],
    ['lei\\s+rom\\S{0,4}ne\\S{0,2}ti', 'ROL'],
    ['lei(?:\\s+moldovenesti)?|mdl\\b', 'MDL']
  ];
  // în textul cu diacritice, „\b" din JavaScript ar socoti „ă" drept capăt de cuvânt; Python nu
  var CAPAT = '(?![\\p{L}\\p{N}_])';
  var _VAL = VALUTE.map(function (v) { return '(?:' + v[0].replace(/\\b/g, CAPAT) + ')'; }).join('|');
  var _NUM = '\\d{1,3}(?:[ .,]\\d{3})+(?:[.,]\\d{1,2})?|\\d+(?:[.,]\\d+)?';
  var _MULT = 'miliarde|miliard|milioane|milion|millions?|billions?|mil\\.?|mln\\.?|mii';
  function RX_DUPA() { return new RegExp('(?<![\\d.,])(' + _NUM + ')(?![\\d])\\s*(?:\\([^)]{2,160}\\)\\s*)?(?:de\\s+)?(' + _MULT + ')?\\s*(?:de\\s+)?(' + _VAL + ')', 'giu'); }
  function RX_INAINTE() { return new RegExp('(?<![a-z])(eur|usd|sdr|xdr|chf|jpy|gbp|€|\\$)\\s?(' + _NUM + ')(?![\\d])\\s*(' + _MULT + ')?', 'giu'); }
  var MULT = { miliarde: 1e9, miliard: 1e9, billion: 1e9, billions: 1e9, milioane: 1e6, milion: 1e6, mil: 1e6, 'mil.': 1e6,
               mln: 1e6, 'mln.': 1e6, million: 1e6, millions: 1e6, mii: 1e3 };
  var SIMBOL = { '€': 'EUR', '$': 'USD', sdr: 'DST', xdr: 'DST' };

  function valuta(cuvant) {
    var c = fold(cuvant).trim();
    for (var i = 0; i < VALUTE.length; i++) if (new RegExp('^(?:' + VALUTE[i][0] + ')$').test(c)) return VALUTE[i][1];
    return null;
  }
  function numar(s) {
    s = String(s).replace(/\u00a0/g, ' ').trim();
    if (/^\d{1,3}(?:[ .,]\d{3})+$/.test(s)) return parseFloat(s.replace(/[ .,]/g, ''));
    var m = /^(\d{1,3}(?:[ .]\d{3})+),(\d{1,2})$/.exec(s) || /^(\d{1,3}(?:[ ,]\d{3})+)\.(\d{1,2})$/.exec(s);
    if (m) return parseFloat(m[1].replace(/[ .,]/g, '') + '.' + m[2]);
    if (/^\d+[.,]\d+$/.test(s)) return parseFloat(s.replace(',', '.'));
    if (/[ .,]/.test(s)) return 0;      // „35.700.00": număr rupt în PDF; mai bine fără sumă decât cu una greșită
    return parseFloat(s.replace(/\D/g, '') || '0');
  }
  var MULT_RO = { miliarde: 1, miliard: 1, milioane: 1, milion: 1, mil: 1, 'mil.': 1, mln: 1, 'mln.': 1 };
  function valoare(cifre, mult) {
    var v = numar(cifre);
    // „3,075 milioane dolari" înseamnă 3,075 mil. (virgula e zecimală în română), nu 3 075 mil.
    if (MULT_RO[mult] && /^\d{1,3},\d{3}$/.test(cifre.trim())) v = parseFloat(cifre.trim().replace(',', '.'));
    if (mult && v < 1e5) v *= (MULT[mult] || 1);
    return v;
  }
  function candidati(t) {
    var out = [];
    // Un cont bancar nu e o sumă: „MD04VI022240300000368EUR" a fost citit drept
    // 22 240 300 000 368 EUR. Sărim cifrele lipite de o literă și valorile imposibile.
    Array.from(t.matchAll(RX_DUPA())).forEach(function (m) {
      if (m.index && /\p{L}/u.test(t[m.index - 1])) return;
      var v = valoare(m[1], (m[2] || '').toLowerCase());
      if (v >= 1e12) return;
      out.push([m.index, m.index + m[0].length, v, valuta(m[3])]);
    });
    Array.from(t.matchAll(RX_INAINTE())).forEach(function (m) {
      var v = valoare(m[2], (m[3] || '').toLowerCase());
      if (v >= 1e12) return;
      var sym = m[1].toLowerCase();
      out.push([m.index, m.index + m[0].length, v, SIMBOL[sym] || sym.toUpperCase()]);
    });
    return out;
  }
  function intreg(x) { if (x && x.v === Math.trunc(x.v)) x.v = Math.trunc(x.v); return x; }

  function scor(inainte, propozitie, cod, v) {
    var i = fold(inainte), p = fold(propozitie), s = 0;
    if (/\b(?:in|de|cu)\s+(?:suma|valoare|marime|cuantum)(?:\s+totala)?(?:\s+de)?\s*$/.test(i.slice(-45))) s += 6;
    else if (/suma\b|valoare|cuantum|marime|in limita|pana la|nu (?:va )?depasi|amount|not exceeding|up to|equivalent/.test(i.slice(-70))) s += 3;
    if (/se ratifica|se aproba|hotaraste|se accepta/.test(p)) s += 4;
    if (/imprumut|grant|credit|finantar|asistent|ajutor|loan|lend|financing|facilit/.test(p)) s += 2;
    if (/dobanz|comision|taxa|penalit|interest|fee|prima de|rambursar/.test(i.slice(-70))) s -= 4;
    if (cod === 'MDL') s -= 2;
    if (v >= 1e6) s += 1;
    return s;
  }
  /* Sumele din textul unui act (legea, hotărârea), cele mai probabile primele. */
  function sume_din_text(text, maxim) {
    var t = String(text || '').replace(/-\s*\n\s*/g, '').replace(/\s+/g, ' ');
    var gasite = {};
    candidati(t).forEach(function (c) {
      var start = c[0], end = c[1], v = c[2], cod = c[3];
      if (!cod || v < 1000) return;
      var p1 = start >= 2 ? t.lastIndexOf('. ', start - 2) : -1, p2 = start >= 2 ? t.lastIndexOf('; ', start - 2) : -1;
      var inceput = Math.max(0, p1 + 1, p2 + 1, start - 300);
      var s = scor(t.slice(Math.max(0, start - 160), start), t.slice(inceput, Math.min(t.length, end + 120)), cod, v);
      if (s < 2) return;
      var a = Math.max(0, start - 120), b = Math.min(t.length, end + 60);
      var f = (a > 0 ? '…' : '') + t.slice(a, b).trim() + (b < t.length ? '…' : '');
      var vr = Math.round(v * 100) / 100, k = vr + '|' + cod;
      if (!gasite[k] || gasite[k].s < s) gasite[k] = { v: vr, val: cod, f: f.slice(0, 220), s: s, poz: start };
    });
    return Object.keys(gasite).map(function (k) { return gasite[k]; })
      .sort(function (x, y) { return (y.s - x.s) || (x.poz - y.poz); }).slice(0, maxim || 5)
      .map(function (r) { delete r.poz; return intreg(r); });
  }

  var _GRANT = /grant|subventi|nerambursabil|contributi|donati|ajutor/;
  var _IMPR = /imprumut|credit|loan|lend|facilitat/;
  var _COST = /cost(?:ul|urile)?\s+(?:total|totale|estimat|final)|total(?:\s+project)?\s+cost|estimated\s+(?:total\s+)?cost|valoarea\s+totala\s+a\s+proiectului|bugetul\s+(?:total\s+)?(?:al\s+)?proiectului|buget\w{0,2}\s+total\s+al\s+programului|total\s+budget\s+of\s+the\s+programme|fonduri(?:lor)?\s+interreg|alocar\w+\s+financiar\w+\s+total\w+\s+a\s+ue\s+pentru\s+program|out\s+of\s+the/;
  var _PROPRIU = /prezent(?:ul|ului)\s+(?:acord|contract)|acest(?:ui)?\s+acord|this\s+agreement|hereunder|hereby/;
  var _EXPLICIT = /reprezentat[aă]?\s+de\s+prezentul\s+acord|valoarea\s+grantului|suma\s+(?:grantului|imprumutului|creditului)|amount\s+of\s+the\s+(?:grant|loan|credit)/;
  var _MAXIM = /valoare(?:a)?\s+(?:principala\s+)?maxima|suma\s+maxima|maximum\s+amount|pana\s+la|up\s+to|not\s+exceeding|not\s+to\s+exceed|sa\s+nu\s+depaseasca|ce\s+nu\s+depaseste|in\s+valoare(?:\s+totala)?\s+de|in\s+suma\s+de|amount\s+of|in\s+cuantum\s+de|in\s+marime\s+de/;
  var _DEFINITIE = /valoarea\s+maxima\s+a\s+(?:grantului|subventiei|imprumutului|creditului)/;
  var _LIMITA = /nu\s+va\s+depasi\s+cu\s+mai\s+mult|tran\w{0,2}(?:a|e|ei|elor)\b|trans\b|tranche|instal?l?ments?|first\s+transfer|prefinant|pre-?financ|cumulat/;
  var _COMISION = /comision|\bfees?\b/;
  var _ALT_ACORD = /in\s+temeiul\s+unui\s+contract|contract(?:ul)?\s+de\s+finantare\s+din\s+data\s+de|finance\s+contract\s+dated|acord(?:ul)?\s+de\s+(?:imprumut|finantare|grant)\W{0,8}din\s+data|(?:loan|financing|grant)\s+agreement\W{0,8}(?:of\s+(?:even|the\s+same)\s+date|dated)/;
  // Greșeli văzute în sumele publicate: o cotă dintr-o sumă mai mare, cofinanțarea altcuiva,
  // un plafon de achiziții, un cont bancar.
  var _PARTE_DUPA = /^\W{0,3}(?:out\s+of|to\s+each|pentru\s+fiecare|fiecar(?:ui|ei)|din\s+(?:contributia|totalul|imprumutul|credit|grant|cei|cele))/;
  var _PARTE_INAINTE = /\d\s*%\s+(?:din|of)\b|adica\s+pana\s+la|approximately|aproximativ/;
  var _COFIN = /contributi[ae]\s+national|cofinanta|co-?financ|contributi[ae]\s+proprie/;
  var _ACHIZ = /procurement|achiziti/;
  var _CONT = /cont(?:ul)?\s+bancar|\biban\b|\bswift\b|\bbic\b|bank\s+account/;

  // OCR-ul pune „T" în loc de „î" la început de cuvânt: „Tn" = „în", „Tmprumut" = „împrumut"
  function fold_ocr(s) { return fold(s).replace(/\bt(?=[mn])/g, 'i'); }

  /* Propoziția în care stă suma: nu tăiem la punctele din numere („119.000.000"). */
  function propozitie(t, start, end) {
    var inainte = t.slice(Math.max(0, start - 260), start), m = null, x;
    var rx = /(?<!\d)[.;]\s+(?=[A-ZĂÂÎȘȚ„"(])|\n\s*[A-Z]\.\s|(?<![\p{L}\p{N}_])\d{1,2}\.\d{1,2}\.\s/gu;
    while ((x = rx.exec(inainte))) m = x;
    if (m) inainte = inainte.slice(m.index + m[0].length);
    var dupa = t.slice(end, end + 200);
    var m2 = /(?<!\d)\.\s+(?=[A-ZĂÂÎȘȚ])|\n\s*[A-Z]\.\s|(?<![\p{L}\p{N}_])\d{1,2}\.\d{1,2}\.\s/u.exec(dupa);
    if (m2) dupa = dupa.slice(0, m2.index);
    return [inainte, dupa];
  }

  /* Suma acordului și costul total al proiectului, din textul acordului (documentul atașat).
     instrument: 'grant' sau 'imprumut'. Întoarce {suma, cost, candidat}. */
  function suma_acord(text, instrument) {
    var t = String(text || '').replace(/-\s*\n\s*/g, '').replace(/[ \t]+/g, ' ');
    var propriu = instrument === 'grant' ? _GRANT : _IMPR, altul = instrument === 'grant' ? _IMPR : _GRANT;
    var sume = {}, costuri = {};
    candidati(t).forEach(function (c) {
      var start = c[0], end = c[1], v = c[2], cod = c[3];
      if (!cod || v < 1000 || cod === 'MDL') return;
      var pr = propozitie(t, start, end), inainte = pr[0], dupa = pr[1];
      var fi = fold_ocr(inainte), fd = fold_ocr(dupa), prop = fi + ' ' + fd;
      var frag = (inainte.slice(-150) + t.slice(start, end) + dupa.slice(0, 70)).replace(/\s+/g, ' ').trim();
      if (_COMISION.test(fd.slice(0, 70)) || _COMISION.test(fi.slice(-50))) return;      // suma e chiar un comision
      if (_CONT.test(fi.slice(-80))) return;                                              // număr de cont, nu sumă
      if (_PARTE_DUPA.test(fd.slice(0, 45))) return;                                      // o cotă: „X out of the Y", „X to each School"
      var k = v + '|' + cod;
      if (_COST.test(fi.slice(-140))) {
        if (!costuri[k]) costuri[k] = { v: v, val: cod, f: frag.slice(0, 230), poz: start };
        return;
      }
      var s = 0, areP = propriu.test(prop), areA = altul.test(prop);
      s += _PROPRIU.test(prop) ? 4 : 0;
      s += areP ? 4 : 0;
      s -= (areA && !areP) ? 4 : 0;
      s += _MAXIM.test(fi.slice(-90)) ? 3 : 0;
      s += _DEFINITIE.test(fi.slice(-140)) ? 3 : 0;
      s += _EXPLICIT.test(prop) ? 2 : 0;
      var transa = _LIMITA.test(fi.slice(-130));
      s -= transa ? 3 : 0;
      s -= _COMISION.test(prop) ? 3 : 0;
      s -= _ALT_ACORD.test(prop) ? 3 : 0;
      s -= _PARTE_INAINTE.test(fi.slice(-60)) ? 4 : 0;
      s -= _COFIN.test(fi.slice(-120)) ? 4 : 0;
      s -= _ACHIZ.test(prop) ? 4 : 0;
      s += v >= 1e6 ? 1 : 0;
      if (!sume[k] || sume[k].s < s) sume[k] = { v: v, val: cod, f: frag.slice(0, 230), s: s, poz: start, tr: transa };
    });
    // Totalul și tranșele lui: când lângă două sume stă și suma lor, acordul e totalul (doar pentru tranșe).
    var toateS = Object.keys(sume).map(function (k) { return sume[k]; }), dupa = {};
    toateS.forEach(function (x) { dupa[(Math.round(x.v * 100) / 100) + '|' + x.val] = x; });
    toateS.forEach(function (a) {
      toateS.forEach(function (b) {
        if (b.val !== a.val || b.v <= a.v || !(a.tr || b.tr)) return;
        var t = dupa[(Math.round((a.v + b.v) * 100) / 100) + '|' + a.val];
        if (t && Math.max(a.poz, b.poz, t.poz) - Math.min(a.poz, b.poz, t.poz) <= 1500) { t.total = 1; a.parte = 1; b.parte = 1; }
      });
    });
    toateS.forEach(function (x) { if (x.total && !x.parte) x.s += 3; else if (x.parte) x.s -= 4; delete x.total; delete x.parte; delete x.tr; });
    var alese = toateS.sort(function (x, y) { return (y.s - x.s) || (x.poz - y.poz); });
    var suma = alese.length && alese[0].s >= 6 && alese[0].v >= 10000 ? alese[0] : null;   // sub 10 000 e un plafon sau o taxă, nu un acord
    var candidat = alese.length && !suma && alese[0].s >= 3 ? alese[0] : null;
    var cost = Object.keys(costuri).map(function (k) { return costuri[k]; }).sort(function (x, y) { return (y.v - x.v) || (x.poz - y.poz); })[0] || null;
    [suma, cost, candidat].forEach(function (x) { if (x) { delete x.poz; intreg(x); } });
    return { suma: suma, cost: cost, candidat: candidat };
  }

  var REGULI = 3;      // crește când se schimbă regulile de alegere a sumei
  /* Suma veche, ținută în fișier, mai rezistă regulilor de azi? O reverificăm pe
     fragmentul păstrat lângă ea; dacă nu mai iese aceeași sumă, actul sau atașamentul se recitește. */
  function sume_tin(r) {
    if (r.v === REGULI || !(r.sume || []).length) return true;
    var s = r.sume[0], top = sume_din_text(s.f || '')[0];
    return !!top && top.v === s.v && top.val === s.val;
  }
  function suma_atas_tine(x, instrument) {
    var s = x.suma;
    if (!s || s.manual || x.v === REGULI) return true;
    var n = suma_acord(s.f || '', instrument).suma;
    return !!n && n.v === s.v && n.val === s.val;
  }
  /*</SUME>*/

  // ------------------------------------------------------------------ unelte
  var BLOCAT = /Just a moment|verificării de securitate|nu ești un robot|Verify you are human|Checking your browser/i;
  function eBlocat(status, text) {
    var inceput = String(text || '').slice(0, 5000);
    return BLOCAT.test(inceput) || ((status === 403 || status === 503) && /cloudflare/i.test(inceput));
  }
  function Blocat(url) { this.blocat = true; this.url = url || ''; this.message = 'blocat de Cloudflare'; }
  function somn(ms) { return new Promise(function (r) { setTimeout(r, ms); }); }
  function azi() { var d = new Date(); return d.getFullYear() + '-' + String(d.getMonth() + 1).padStart(2, '0') + '-' + String(d.getDate()).padStart(2, '0'); }
  function decod(s) { try { return decodeURIComponent(s); } catch (e) { return s; } }
  /* Aceeași adresă scrisă cu sau fără %20, cu sau fără www, e același fișier. */
  function cheieUrl(u) { try { return decod(new URL(u, CFG.BAZA).pathname).trim(); } catch (e) { return decod(String(u || '')).trim(); } }
  function canon(u) {
    var x = new URL(u, CFG.BAZA); x.hash = '';
    x.pathname = x.pathname.split('/').map(function (seg) {
      return encodeURIComponent(decod(seg)).replace(/%(2C|3B|3D|2B|26|24|40|3A)/g, function (m) { return decodeURIComponent(m); });
    }).join('/');
    return x.href;
  }
  var ta = document.createElement('textarea');
  function dezescapeaza(s) { ta.innerHTML = s; return ta.value; }
  function linkuriDinHtml(pagina, baza) {
    var out = [], vazute = {}, m, rx = /(?:href|src|data)\s*=\s*(?:"([^"]+)"|'([^']+)')/gi;
    while ((m = rx.exec(pagina || ''))) {
      var u = dezescapeaza((m[1] || m[2] || '').trim());
      if (!/userfiles/i.test(u) || !/\.pdf(?:[?#].*)?$/i.test(u)) continue;
      var a;
      try { a = canon(new URL(u, baza).href); } catch (e) { continue; }
      if (!vazute[cheieUrl(a)]) { vazute[cheieUrl(a)] = 1; out.push(a); }
    }
    return out;
  }
  async function cere(url, ms) {
    var c = new AbortController(), t = setTimeout(function () { c.abort(); }, ms || 90000);
    try {
      var r = await fetch(url, { cache: 'no-store', credentials: 'include', signal: c.signal });
      r.anuleaza = function () { try { c.abort(); } catch (e) {} };      // oprește și descărcarea corpului
      return r;
    }
    finally { clearTimeout(t); }
  }
  function incarcaScript(src) {
    return new Promise(function (ok, fail) {
      var s = document.createElement('script'); s.src = src; s.onload = ok;
      s.onerror = function () { fail(new Error('nu s-a putut încărca ' + src)); };
      document.head.appendChild(s);
    });
  }
  function salveazaFisier(nume, continut, tip) {
    var a = document.createElement('a');
    a.href = URL.createObjectURL(new Blob([continut], { type: tip }));
    a.download = nume; document.body.appendChild(a); a.click(); a.remove();
    setTimeout(function () { URL.revokeObjectURL(a.href); }, 5000);
  }

  // ------------------------------------------------------------------ caseta de progres
  var caseta = document.createElement('div');
  caseta.style.cssText = 'position:fixed;right:16px;bottom:16px;z-index:2147483647;width:360px;background:#fff;color:#16294a;' +
    'border:2px solid #22406b;border-radius:10px;box-shadow:0 10px 30px rgba(0,0,0,.3);font:13px/1.45 Arial,sans-serif;padding:12px 14px';
  caseta.innerHTML = '<b style="font-size:14px">Sumele acordurilor</b><div id="la-stare" style="margin:6px 0">Pornesc…</div><div id="la-pas" style="color:#22406b;font-size:12px;min-height:16px"></div>' +
    '<div id="la-cifre" style="color:#4f5668;font-size:12px"></div><div style="margin-top:9px;display:flex;gap:8px">' +
    '<button id="la-stop" style="padding:5px 10px;cursor:pointer">Oprește</button>' +
    '<button id="la-desc" style="padding:5px 10px;cursor:pointer">Descarcă ce am până acum</button></div>';
  document.body.appendChild(caseta);
  function spune(text, rosu) {
    var e = caseta.querySelector('#la-stare'); e.textContent = text; e.style.color = rosu ? '#b3261e' : '#16294a';
    console.log('[sume] ' + text);
  }
  function pas(text) { caseta.querySelector('#la-pas').textContent = text || ''; }
  /* Un document care nu se mai termină (descărcare agățată, PDF pe care biblioteca nu-l duce
     la capăt) nu are voie să oprească tot: după un timp îl lăsăm și trecem mai departe. */
  function cuLimita(p, secunde, ce) {
    return new Promise(function (ok, fail) {
      var t = setTimeout(function () { fail(new Error(ce + ' a durat peste ' + secunde + ' de secunde')); }, secunde * 1000);
      Promise.resolve(p).then(function (v) { clearTimeout(t); ok(v); }, function (e) { clearTimeout(t); fail(e); });
    });
  }
  var S = { acte: 0, total: 0, pdf: 0, sume: 0, ocr: 0, faraText: 0, erori: 0 };
  function cifre() {
    caseta.querySelector('#la-cifre').textContent = 'acte: ' + S.acte + ' din ' + S.total + ' · PDF-uri citite: ' + S.pdf +
      ' · cu sumă: ' + S.sume + ' (OCR: ' + S.ocr + ') · scanate necitite: ' + S.faraText + ' · erori: ' + S.erori;
  }

  // ------------------------------------------------------------------ PDF și OCR
  async function pregatestePdf() {
    if (!window.pdfjsLib) await incarcaScript(CFG.PDFJS);
    var lib = window.pdfjsLib || window['pdfjs-dist/build/pdf'];
    if (!lib) throw new Error('biblioteca pdf.js nu s-a încărcat');
    lib.GlobalWorkerOptions.workerSrc = CFG.PDFJS_WORKER;
    return lib;
  }
  var ocrW, motivFaraOcr = '';
  async function ocr() {
    if (ocrW !== undefined) return ocrW;
    try {
      if (!window.Tesseract) await incarcaScript(CFG.TESSERACT);
      ocrW = await window.Tesseract.createWorker(['ron', 'eng'], 1, CFG.OCR_OPT || {});
    } catch (e) {
      ocrW = null; motivFaraOcr = String((e && e.message) || e);
      console.warn('[sume] OCR indisponibil: ' + motivFaraOcr + '. PDF-urile scanate rămân marcate „fara-text".');
    }
    return ocrW;
  }
  /* (text, pagini, metoda): 'text' = PDF-ul are text; 'ocr' = scanat, citit cu OCR;
     'fara-text' = scanat și OCR-ul nu e disponibil. */
  async function textPdf(lib, octeti, cuOcr, ctl) {
    ctl = ctl || {};
    ctl.sarcina = lib.getDocument({ data: octeti, isEvalSupported: false });
    var doc = await ctl.sarcina.promise;
    try {
      var pagini = doc.numPages, text = '', i;
      for (i = 1; i <= Math.min(pagini, CFG.PAGINI_TEXT) && !ctl.anulat; i++) {
        if (i % 10 === 1) pas((ctl.nume || '') + 'citesc textul, pagina ' + i + ' din ' + pagini + '…');
        var tc = await (await doc.getPage(i)).getTextContent();
        text += tc.items.map(function (it) { return it.str + (it.hasEOL ? '\n' : ' '); }).join('') + '\n';
      }
      var car = text.replace(/\s+/g, '').length;
      if (car >= Math.max(200, 40 * Math.min(pagini, 10))) return { text: text, pagini: pagini, metoda: 'text' };
      var w = cuOcr ? await ocr() : null;
      if (!w) return { text: text, pagini: pagini, metoda: 'fara-text' };
      var t2 = '';
      for (i = 1; i <= Math.min(pagini, CFG.PAGINI_OCR) && !ctl.anulat; i++) {
        pas((ctl.nume || '') + 'PDF scanat, îl citesc cu OCR: pagina ' + i + ' din ' + Math.min(pagini, CFG.PAGINI_OCR) + '…');
        var pg = await doc.getPage(i), vp = pg.getViewport({ scale: 2 });
        var cv = document.createElement('canvas'); cv.width = Math.ceil(vp.width); cv.height = Math.ceil(vp.height);
        await pg.render({ canvasContext: cv.getContext('2d'), viewport: vp }).promise;
        t2 += (await w.recognize(cv)).data.text + '\n';
        cv.width = cv.height = 0;
      }
      // OCR-ul rupe numerele: „17. 700. 000" → „17.700.000"
      t2 = t2.replace(/(?<=\d)\s?([.,])\s(?=\d{3}(?!\d))/g, '$1');
      return { text: text + '\n' + t2, pagini: pagini, metoda: 'ocr' };
    } finally { try { await doc.destroy(); } catch (e) {} }
  }
  async function descarcaPdf(url) {
    var r = await cere(url), lung = +(r.headers.get('content-length') || 0);
    if (lung > CFG.MAX_MB * 1048576) { r.anuleaza(); return { eroare: 'PDF prea mare (' + Math.floor(lung / 1048576) + ' MB)' }; }
    var b;
    try { b = new Uint8Array(await cuLimita(r.arrayBuffer(), CFG.LIMITA_DESC, 'descărcarea')); }
    catch (e) { r.anuleaza(); return { eroare: String(e.message || e).slice(0, 120) }; }
    if (b.length > CFG.MAX_MB * 1048576) return { eroare: 'PDF prea mare (' + Math.floor(b.length / 1048576) + ' MB)' };
    if (!(b[0] === 0x25 && b[1] === 0x50 && b[2] === 0x44 && b[3] === 0x46)) {       // %PDF
      if (eBlocat(r.status, new TextDecoder().decode(b.subarray(0, 5000)))) throw new Blocat(url);
      return { eroare: 'HTTP ' + r.status + ', nu e PDF' };
    }
    return { octeti: b };
  }

  // ------------------------------------------------------------------ datele
  var PROGRES = 'LA_progres';
  var baza, acte, tinte = [], progres = {}, dovezi = {};
  /* Ce s-a citit se ține în browser (IndexedDB), act cu act, ca o rulare întreruptă să continue. */
  var dbP = new Promise(function (ok) {
    try {
      var q = indexedDB.open('legis_sume', 1);
      q.onupgradeneeded = function () { q.result.createObjectStore('acte'); };
      q.onsuccess = function () { ok(q.result); };
      q.onerror = q.onblocked = function () { ok(null); };
    } catch (e) { ok(null); }
  });
  function pastreaza(d) {
    return dbP.then(function (db) {
      if (!db || !d) return;
      return new Promise(function (ok) {
        try {
          var t = db.transaction('acte', 'readwrite');
          t.objectStore('acte').put({ r: progres[d] || null, d: dovezi[d] || null }, d);
          t.oncomplete = ok; t.onerror = t.onabort = function () { ok(); };
        } catch (e) { ok(); }
      });
    });
  }
  function incarcaPastrate() {
    return dbP.then(function (db) {
      if (!db) return {};
      return new Promise(function (ok) {
        var out = {};
        try {
          var c = db.transaction('acte', 'readonly').objectStore('acte').openCursor();
          c.onsuccess = function () { var cur = c.result; if (cur) { out[cur.key] = cur.value; cur.continue(); } else ok(out); };
          c.onerror = function () { ok(out); };
        } catch (e) { ok(out); }
      });
    });
  }
  function stergePastrate() {
    try { localStorage.removeItem(PROGRES); } catch (e) {}
    return dbP.then(function (db) { if (db) db.transaction('acte', 'readwrite').objectStore('acte').clear(); });
  }
  /* Din textul unui document: sumele găsite, fiecare cu pasajul din jurul ei. Întâi cea aleasă
     de reguli (suma, candidatul, costul), apoi celelalte, în ordinea din document. */
  function dovada(u, tx, sa) {
    var t = String(tx.text || '').replace(/-\s*\n\s*/g, '').replace(/[ \t]+/g, ' ');
    var uniq = {}, ord = [];
    candidati(t).forEach(function (c) {
      var v = c[2], cod = c[3];
      if (!cod || v < 1000 || cod === 'MDL') return;
      var k = v + '|' + cod;
      if (!uniq[k]) {
        uniq[k] = { v: v, val: cod, n: 0, poz: c[0],
                    f: t.slice(Math.max(0, c[0] - 300), Math.min(t.length, c[1] + 200)).replace(/\s+/g, ' ').trim() };
        ord.push(uniq[k]);
      }
      uniq[k].n++;
    });
    var ch = function (x) { return x ? x.v + '|' + x.val : '-'; }, kS = ch(sa.suma), kC = ch(sa.candidat), kT = ch(sa.cost);
    ord.forEach(function (p) { var k = p.v + '|' + p.val; p.rol = k === kS ? 'suma' : k === kC ? 'candidat' : k === kT ? 'cost' : ''; });
    ord.sort(function (a, b) { return ((b.rol ? 1 : 0) - (a.rol ? 1 : 0)) || ((a.v >= 1e5 ? 0 : 1) - (b.v >= 1e5 ? 0 : 1)) || (a.poz - b.poz); });
    return { u: u, pagini: tx.pagini, metoda: tx.metoda, car: t.replace(/\s+/g, '').length,
             inceput: t.replace(/\s+/g, ' ').trim().slice(0, 600), sume_gasite: ord.length,
             pasaje: ord.slice(0, CFG.PASAJE).map(function (p) { return intreg({ v: p.v, val: p.val, n: p.n, rol: p.rol, f: p.f }); }) };
  }
  /* documente_verificare_N.json: ce se trimite la verificat. Împărțit în fișiere de cel mult ~6 MB. */
  function fisiereDovezi() {
    var parti = [], cur = {}, marime = 0;
    Object.keys(dovezi).sort(function (x, y) { return (+y) - (+x); }).forEach(function (d) {
      if (!dovezi[d]) return;
      var s = JSON.stringify(dovezi[d]).length;
      if (marime && marime + s > 6e6) { parti.push(cur); cur = {}; marime = 0; }
      cur[d] = dovezi[d]; marime += s;
    });
    if (marime) parti.push(cur);
    return parti.map(function (p, i) {
      return { nume: 'documente_verificare_' + (i + 1) + '.json',
               text: JSON.stringify({ generat: azi(), reguli: REGULI, parte: i + 1, din: parti.length, acte: p }) };
    });
  }
  function areNevoie(r) {
    if (!r) return true;                                  // act necitit încă: îl citim cu totul
    if (r.eroare) return !!CFG.REINCEARCA;
    if (CFG.TOT || !('atas_citit' in r)) return true;
    // „niciun atașament" de la o versiune care nu aștepta încărcarea fișei: mai verificăm o dată
    if (!(r.atas || []).length && !r.fisa_ok) return true;
    if (!sume_tin(r)) return true;                       // o sumă veche nu mai rezistă regulilor de azi
    if ((r.atas || []).some(function (x) { return !suma_atas_tine(x, r.instr || 'grant'); })) return true;
    if (CFG.REINCEARCA) return !!r.atas_eroare || (r.atas || []).some(function (x) { return x.eroare || (x.metoda === 'fara-text' && !x.suma); });
    return false;
  }
  /* Atașamentele citite acum peste cele din bază: suma pusă de mână rămâne mereu;
     o sumă deja găsită nu e înlocuită de un rezultat fără sumă; ce nu mai apare în pagină se păstrează. */
  function uneste(vechi, noi) {
    var dupa = {}, puse = {}, out = [];
    (vechi || []).forEach(function (x) { dupa[cheieUrl(x.u)] = x; });
    noi.forEach(function (n) {
      var k = cheieUrl(n.u), v = dupa[k];
      if (v && v.suma && (v.suma.manual || !n.suma)) n = v;
      out.push(n); puse[k] = 1;
    });
    (vechi || []).forEach(function (v) { if (!puse[cheieUrl(v.u)]) out.push(v); });
    return out;
  }
  function rezultat() {
    baza.actualizat = azi() + ' ' + String(new Date().getHours()).padStart(2, '0') + ':' + String(new Date().getMinutes()).padStart(2, '0');
    return JSON.stringify(baza);
  }
  function raportCsv() {
    var q = function (v) { v = String(v == null ? '' : v); return /[;"\n]/.test(v) ? '"' + v.replace(/"/g, '""') + '"' : v; };
    var MOTIV = { 'fara-text': 'PDF scanat, fără OCR', ocr: 'citit cu OCR, suma negăsită', text: 'are text, suma negăsită' };
    var linii = [['act', 'doc_id', 'atasament', 'motiv', 'pagini', 'candidat', 'valuta', 'scor', 'fragment']];
    tinte.forEach(function (t) {
      var r = acte[t.doc];
      if (!r || !('atas_citit' in r)) return;
      if (!(r.atas || []).length) { if (!(r.sume || []).length) linii.push([t.act, t.doc, '', r.atas_eroare || 'niciun PDF atașat', '', '', '', '', '']); return; }
      if (r.atas.some(function (x) { return x.suma; })) return;
      r.atas.forEach(function (x) {
        var c = x.candidat || {};
        linii.push([t.act, t.doc, x.u || '', x.eroare || MOTIV[x.metoda] || 'citit de scriptul vechi', x.pagini || '', c.v || '', c.val || '', c.s || '', c.f || '']);
      });
    });
    return '\ufeff' + linii.map(function (l) { return l.map(q).join(';'); }).join('\r\n') + '\r\n';
  }
  function descarca() {
    salveazaFisier('legis_sume.json', rezultat(), 'application/json');
    setTimeout(function () { salveazaFisier('sume_lipsa.csv', raportCsv(), 'text/csv'); }, 800);
    fisiereDovezi().forEach(function (f, i) { setTimeout(function () { salveazaFisier(f.nume, f.text, 'application/json'); }, 1600 + 800 * i); });
  }

  var LA = window.LA = { ruleaza: true, oprit: false, stare: S,
    stop: function () { LA.oprit = true; spune('Mă opresc după actul curent…'); },
    descarca: function () { if (baza) descarca(); },
    reset: function () { stergePastrate(); console.log('[sume] progresul din browser a fost șters'); } };
  caseta.querySelector('#la-stop').onclick = LA.stop;
  caseta.querySelector('#la-desc').onclick = LA.descarca;

  try {
    // 1. registrul și sumele de până acum, de pe site
    spune('Iau registrul și sumele de până acum de pe ' + CFG.SITE.replace(/^https?:\/\//, '') + '…');
    var r1 = await fetch(CFG.SITE + '/date/legis_sume.json?_=' + Date.now(), { cache: 'no-store' });
    var r2 = await fetch(CFG.SITE + '/date/acorduri_legis.json?_=' + Date.now(), { cache: 'no-store' });
    if (!r1.ok || !r2.ok) throw new Error('nu pot citi datele de pe ' + CFG.SITE + ' (HTTP ' + r1.status + '/' + r2.status + ')');
    baza = await r1.json(); acte = baza.acte = baza.acte || {};
    (await r2.json()).forEach(function (a) {
      var m = /doc_id=(\d+)/.exec(a.link || '');
      if (!m || /^DP/.test(a.act || '')) return;                    // decretele nu conțin sume
      tinte.push({ doc: m[1], act: a.act, instr: a.categorie === 'Împrumut' ? 'imprumut' : 'grant', titlu: String(a.titlu || '').slice(0, 260) });
    });
    // 2. ce am citit deja în această filă, la o rulare întreruptă
    try { progres = JSON.parse(localStorage.getItem(PROGRES) || '{}') || {}; } catch (e) { progres = {}; }
    var pastrate = await incarcaPastrate();
    Object.keys(pastrate).forEach(function (d) { if (pastrate[d].r) progres[d] = pastrate[d].r; if (pastrate[d].d) dovezi[d] = pastrate[d].d; });
    var reluate = 0;
    Object.keys(progres).forEach(function (d) {          // ce am citit aici e cel puțin la fel de nou ca fișierul de pe site
      if (!(acte[d] && 'atas_citit' in acte[d]) || String(progres[d].atas_citit || '') >= String(acte[d].atas_citit)) { acte[d] = progres[d]; reluate++; }
    });

    var deCitit = tinte.filter(function (t) {
      return CFG.DOAR ? CFG.DOAR.map(String).indexOf(t.doc) > -1 : (areNevoie(acte[t.doc]) || (CFG.DOVEZI === 'tot' && !dovezi[t.doc]));
    });
    var parcurs = function (t) { return acte[t.doc] && 'atas_citit' in acte[t.doc] ? 1 : 0; };
    deCitit.sort(function (x, y) { return (parcurs(x) - parcurs(y)) || ((+y.doc) - (+x.doc)); });   // întâi cele neparcurse, cele mai noi primele
    S.total = deCitit.length; cifre();
    spune(tinte.length + ' acte de acord în registru · ' + deCitit.length + ' de deschis acum' + (reluate ? ' · ' + reluate + ' reluate din rularea întreruptă' : ''));
    if (!deCitit.length) { spune('Nimic de citit: toate actele au fost deja parcurse. Am descărcat fișierele.'); descarca(); LA.ruleaza = false; return; }
    var precedent = null;

    var lib = await pregatestePdf();
    var fisa = function (d) { return CFG.BAZA + '/cautare/getResults?doc_id=' + d + '&lang=ro'; };

    // 3. cum se citește fișa unui act
    /* Fișa își aduce conținutul după ce se deschide („Conținutul se încarcă..."), deci o cerere
       simplă nu ajunge: pagina trebuie deschisă și așteptată. Întâi într-un cadru ascuns; dacă
       legis.md îl refuză, într-o fereastră obișnuită, unde verificarea Cloudflare se poate bifa. */
    var REFUZ = /you have been blocked|Access denied|Attention Required|Error\s*10\d\d|403 Forbidden/i;
    function asteaptaPagina(iaDoc, d, rabdareCf) {
      return new Promise(function (ok, fail) {
        var t0 = Date.now(), ultim = -1, stabil = 0;
        var tic = setInterval(function () {
          var h = '', txt = '', inchis = false;
          try {
            var doc = iaDoc();
            if (doc === false) inchis = true;
            else if (doc && doc.readyState === 'complete' && doc.body && String(doc.location.href).indexOf('doc_id=' + d) > -1) {
              h = doc.documentElement.outerHTML; txt = doc.body.innerText || doc.body.textContent || '';
            }
          } catch (e) {}
          var cf = !!h && eBlocat(200, h.slice(0, 3000) + ' ' + txt.slice(0, 1500));        // verificarea Cloudflare, pe ecran
          var refuzat = !!h && !cf && REFUZ.test(txt.slice(0, 1500));
          var incarcat = !cf && !refuzat && txt.trim().length >= 300 && !/Conținutul se încarcă/i.test(txt);
          if (incarcat) { stabil = (h.length === ultim) ? stabil + 1 : 0; ultim = h.length; }
          if (incarcat && stabil >= 2) { clearInterval(tic); return ok({ status: 200, linkuri: linkuriDinHtml(h, fisa(d)), html: h }); }
          if (inchis || refuzat || Date.now() - t0 > (cf ? rabdareCf : 30000)) { clearInterval(tic); fail(new Blocat(fisa(d))); }
        }, 600);
      });
    }
    function prinCadru(d) {
      var f = document.createElement('iframe');
      f.style.cssText = 'position:fixed;left:-9999px;top:0;width:1200px;height:900px;border:0';
      f.src = fisa(d); document.body.appendChild(f);
      var curata = function () { try { f.remove(); } catch (e) {} };
      return asteaptaPagina(function () { return f.contentDocument; }, d, 8000)
        .then(function (r) { curata(); return r; }, function (e) { curata(); throw e; });
    }
    var fereastra = null;
    function prinFereastra(d) {
      try { fereastra.location.href = fisa(d); } catch (e) {}
      return asteaptaPagina(function () { return (!fereastra || fereastra.closed) ? false : fereastra.document; }, d, 300000);
    }
    /* O fereastră nouă se poate deschide doar la un clic al omului: îl cerem în casetă. */
    function cereFereastra() {
      return new Promise(function (ok) {
        spune('legis.md refuză citirea din fundal. Apasă butonul de mai jos: actele se vor deschide pe rând într-o fereastră separată. ' +
              'Las-o deschisă; dacă apare „nu sunt robot” în ea, bifează.', true);
        var b = document.createElement('button');
        b.id = 'la-fereastra'; b.textContent = 'Continuă într-o fereastră separată';
        b.style.cssText = 'display:block;margin-top:8px;padding:7px 12px;cursor:pointer;font-weight:bold;background:#22406b;color:#fff;border:0;border-radius:6px';
        b.onclick = function () {
          fereastra = window.open('about:blank', 'la_legis', 'width=1000,height=800,left=40,top=40');
          if (!fereastra) { b.textContent = 'Browserul a blocat fereastra — permite ferestrele pop-up pentru legis.md și apasă din nou'; return; }
          b.remove(); spune('Continui în fereastra separată…'); ok();
        };
        caseta.querySelector('#la-stare').appendChild(b);
      });
    }
    var gaseste = prinCadru;
    var cunoscute = Object.keys(acte).filter(function (d) { return (acte[d].atas || []).some(function (x) { return x.u; }); })
      .sort(function (x, y) { return (+y) - (+x); }).slice(0, 3);
    if (cunoscute.length) {
      spune('Verific cum apar atașamentele în fișa unui act…');
      var nimereste = async function (fn) {
        var ultim = '';
        for (var i = 0; i < cunoscute.length; i++) {
          var stiute = {}; acte[cunoscute[i]].atas.forEach(function (x) { if (x.u) stiute[cheieUrl(x.u)] = 1; });
          var g = await fn(cunoscute[i]); ultim = g.html;
          if (g.linkuri.some(function (u) { return stiute[cheieUrl(u)]; })) return [true, ''];
        }
        return [false, ultim];
      };
      var ok1;
      try { ok1 = await nimereste(prinCadru); }
      catch (e) { if (!e || !e.blocat) throw e; ok1 = null; }           // cadrul ascuns e refuzat
      if (!ok1) {
        await cereFereastra();
        gaseste = prinFereastra;
        ok1 = await nimereste(prinFereastra);
      }
      if (!ok1[0]) {
        salveazaFisier('legis_debug.html', ok1[1], 'text/html');
        spune('Nu găsesc în fișa actului atașamentele pe care le știu deja. Pagina legis.md arată altfel decât se aștepta scriptul. ' +
              'S-a descărcat legis_debug.html — trimite-l și căutarea se adaptează.', true);
        LA.ruleaza = false; return;
      }
    }

    // 4. actele, pe rând
    for (var n = 0; n < deCitit.length && !LA.oprit; n++) {
      if (precedent) await pastreaza(precedent);
      var T = deCitit[n], d = T.doc, r = acte[d], zi = azi();
      precedent = d;
      spune('Citesc ' + T.act + ' (' + (n + 1) + ' din ' + deCitit.length + ')…');
      if (!r || r.eroare || !sume_tin(r)) {                  // act nou sau cu o sumă care nu mai rezistă: (re)citim textul actului
        var vechiR = r && !r.eroare ? r : null;
        var pa = await descarcaPdf(CFG.BAZA + '/cautare/downloadpdf/' + d), nouR = null;
        if (pa.eroare) nouR = { act: T.act, eroare: pa.eroare, citit: zi };
        else {
          try {
            var ta2 = await cuLimita(textPdf(lib, pa.octeti, false, { nume: 'textul actului: ' }), CFG.LIMITA_DOC, 'citirea actului');
            nouR = { act: T.act, sume: sume_din_text(ta2.text), pagini: ta2.pagini, citit: zi, v: REGULI };
            if (!ta2.text.trim()) nouR.nota = 'PDF fără text (scanat)';
          } catch (e) { nouR = { act: T.act, eroare: 'PDF necitibil: ' + String(e.message || e).slice(0, 120), citit: zi }; }
        }
        if (nouR.eroare && !vechiR) { acte[d] = progres[d] = nouR; dovezi[d] = { act: T.act, titlu: T.titlu, eroare: nouR.eroare }; S.erori++; S.acte++; cifre(); await somn(CFG.PAUZA); continue; }
        if (!nouR.eroare) {                                  // păstrăm ce s-a citit din atașamente
          if (vechiR) ['atas', 'instr', 'atas_citit', 'atas_eroare'].forEach(function (k) { if (k in vechiR) nouR[k] = vechiR[k]; });
          r = acte[d] = nouR;
        } else { S.erori++; vechiR.v = REGULI; }             // recitirea n-a mers: rămâne ce era, nu mai încercăm la fiecare rulare
        await somn(CFG.PAUZA);
      }
      var g;
      try { g = await gaseste(d); }
      catch (e) {
        if (!e || !e.blocat || gaseste === prinFereastra) throw e;
        await cereFereastra();                               // cadrul ascuns e refuzat: trecem pe fereastră
        gaseste = prinFereastra;
        g = await prinFereastra(d);
      }
      r.fisa_ok = 1;                                         // conținutul fișei s-a încărcat cu adevărat
      if (g.status !== 200) { r.atas_eroare = 'fișa actului: HTTP ' + g.status; S.erori++; S.acte++; progres[d] = r; cifre(); await somn(CFG.PAUZA); continue; }
      delete r.atas_eroare;
      var instr = r.instr || T.instr, vechi = {}, noi = [], dv = [];
      (r.atas || []).forEach(function (x) {                  // suma veche care nu mai rezistă regulilor: o recitim
        if (!suma_atas_tine(x, instr)) { x.suma = null; delete x.metoda; }
        vechi[cheieUrl(x.u)] = x;
      });
      for (var j = 0; j < g.linkuri.length; j++) {
        var u = g.linkuri[j], v = vechi[cheieUrl(u)];
        // cu DOVEZI descărcăm fiecare document, și pe cele care au deja sumă: pasajele lor sunt ce se verifică
        if (!CFG.DOVEZI && v && v.suma && !CFG.TOT) { noi.push(v); continue; }                                   // are deja suma
        if (!CFG.DOVEZI && v && v.metoda && !CFG.TOT && !(CFG.REINCEARCA && v.metoda === 'fara-text')) { noi.push(v); continue; }   // citit deja
        var x = { u: u, suma: null, cost: null, citit: zi, v: REGULI };
        var eticheta = 'documentul ' + (j + 1) + ' din ' + g.linkuri.length + ': ';
        pas(eticheta + 'îl descarc…');
        var p = await descarcaPdf(u);
        if (p.eroare) x.eroare = p.eroare;
        else {
          var ctl = { nume: eticheta };
          try {
            var tx = await cuLimita(textPdf(lib, p.octeti, CFG.OCR, ctl), CFG.LIMITA_DOC, 'citirea documentului'), sa = suma_acord(tx.text, instr);
            x.suma = sa.suma; x.cost = sa.cost; x.pagini = tx.pagini; x.metoda = tx.metoda;
            if (!sa.suma && sa.candidat) x.candidat = sa.candidat;
            if (CFG.DOVEZI) dv.push(dovada(u, tx, sa));
          } catch (e) {
            x.eroare = 'PDF necitibil: ' + String(e.message || e).slice(0, 120);
            // oprim ce a rămas în lucru, ca documentul următor să pornească curat
            ctl.anulat = true;
            try { if (ctl.sarcina) ctl.sarcina.destroy(); } catch (e2) {}
            if (/a durat peste/.test(x.eroare) && ocrW) { try { ocrW.terminate(); } catch (e2) {} ocrW = undefined; }
          }
        }
        pas('');
        if (x.eroare && CFG.DOVEZI) dv.push({ u: u, eroare: x.eroare });
        S.pdf++; S.erori += x.eroare ? 1 : 0; S.sume += x.suma ? 1 : 0; S.ocr += x.metoda === 'ocr' ? 1 : 0; S.faraText += x.metoda === 'fara-text' ? 1 : 0;
        noi.push(x); cifre();
        await somn(CFG.PAUZA);
      }
      r.atas = uneste(r.atas, noi); r.instr = instr; r.atas_citit = zi;
      if (CFG.DOVEZI) dovezi[d] = { act: T.act, titlu: T.titlu, instr: instr, atas: dv };
      progres[d] = r; S.acte++; cifre();
      await somn(CFG.PAUZA);
    }
    if (precedent) await pastreaza(precedent);
    descarca();
    spune(LA.oprit ? 'Oprit. Am descărcat ce s-a citit până acum; la următoarea lipire a scriptului continuă de aici.'
                   : 'Gata. S-au descărcat legis_sume.json, sume_lipsa.csv și documente_verificare_….json. Fișierele „documente_verificare” sunt cele de trimis la verificat.');
  } catch (e) {
    try { if (typeof precedent !== 'undefined' && precedent) await pastreaza(precedent); } catch (e2) {}
    if (e && e.blocat) {
      if (acte && S.acte) descarca();
      spune('legis.md a refuzat cererea (Cloudflare). Deschide linkul de mai jos într-o filă nouă: dacă apare o verificare, treci de ea; ' +
            'apoi întoarce-te aici, apasă F5 și lipește din nou scriptul — continuă de unde a rămas. Dacă linkul arată „blocked”, așteaptă câteva ore.', true);
      if (e.url) {
        var leg = document.createElement('a');
        leg.href = e.url; leg.target = '_blank'; leg.rel = 'noopener'; leg.textContent = 'Deschide pagina refuzată';
        leg.style.cssText = 'display:block;margin-top:6px;color:#0b57d0;text-decoration:underline;font-weight:bold';
        caseta.querySelector('#la-stare').appendChild(leg);
      }
    } else {
      console.error(e);
      spune('Eroare: ' + String((e && e.message) || e) + '. Trimite acest mesaj.', true);
    }
  } finally {
    LA.ruleaza = false;
    try { if (typeof fereastra !== 'undefined' && fereastra && !fereastra.closed) fereastra.close(); } catch (e3) {}
    if (ocrW) { try { await ocrW.terminate(); } catch (e) {} }
  }
})();
