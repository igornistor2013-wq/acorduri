/* Legătura dintre acordurile din registru și proiectele din AMP — „de la lege la bani".

   Funcții pure, fără DOM: rulează la fel în dashboard și în Node (teste: teste_legatura.js).

   Un acord (date/acorduri_legare.json) și un proiect AMP se potrivesc când sunt de acord trei
   lucruri, și nicio potrivire nu e prezentată ca sigură fără al treilea:

     1. denumirea — cuvintele care contează (cele rare, nu „proiectul" sau „dezvoltare") din
        denumirea acordului se regăsesc în titlul proiectului;
     2. finanțatorul — BEI nu se leagă de un proiect al Japoniei, oricât de asemănător i-ar fi titlul;
     3. suma — suma acordului (sau costul total al proiectului, scris în același text) coincide
        cu angajamentele proiectului din AMP, cu cel mult 15% diferență.

   Nivelurile, de la cel mai sigur:
     confirmat — pusă de un om în date/legaturi_amp.json;
     suma      — denumire + finanțator + sumă (și fără contradicții de dată sau de fază);
     titlu     — denumire + finanțator, dar suma lipsește sau diferă: de verificat;
     ambiguu   — mai multe proiecte la fel de potrivite sau același proiect pentru mai multe acorduri.

   De ce atâta prudență: pe registrul real, la 4 din 5 acorduri cu titlu potrivit suma nu coincide.
   De obicei sunt faze diferite ale aceluiași program („Reabilitarea drumurilor — Proiectul V" și
   „— Proiectul VI" au același candidat în AMP) sau înregistrări parțiale în AMP. Prezentate ca
   legături sigure, ar pune pe un acord banii altuia. */
(function (rad) {
  'use strict';

  var TOLERANTA_SUMA = 0.15;        // 15% diferență între suma acordului și angajamentele proiectului
  var SUMA_MIN = 100000;            // sub atât, o egalitate de sume poate fi întâmplare
  var PRAG_ACOPERIRE = 0.6;         // partea din cuvintele acordului care trebuie regăsită în titlu
  var PRAG_DICE = 0.4;              // asemănarea generală a celor două denumiri
  var PRAG_ACOPERIRE_TITLU = 0.7;   // fără sumă care să confirme, denumirea trebuie să se potrivească mai bine
  var PRAG_ACOPERIRE_DATA = 0.85;   // cu data în contradicție, doar o denumire aproape identică mai ține
  var DIFERENTA_AMBIGUA = 0.12;     // sub această diferență de scor, două proiecte sunt „la fel de potrivite"
  var FEREASTRA_ANI = [-3, 8];      // începutul proiectului față de anul acordului: [de la, până la]

  /* ---------------------------------------------------------------- text */

  function fold(s) {
    return String(s == null ? '' : s).toLowerCase()
      .replace(/â/g, 'î')                                   // ortografia veche și cea nouă: „învățămîntul" = „învățământul"
      .normalize('NFD').replace(/[\u0300-\u036f]/g, '');
  }

  // Cuvinte care nu deosebesc un proiect de altul.
  var STOP = {};
  ('proiectul proiect proiectului project programul program programului acord acordul acordului acordurile contract ' +
   'contractul contractului imprumut imprumutul imprumutului grant grantul grantului finantare finantarea finantarii ' +
   'dintre privind pentru republica republicii moldova moldovei guvernul guvernului the and for of with ' +
   'semnat semnata incheiat modificare modificat aditional suplimentar').split(' ').forEach(function (w) { STOP[w] = 1; });

  var RX_FAZA = /^(i|ii|iii|iv|v|vi|vii|viii|ix|x|\d{1,2}|(?:19|20)\d\d)$/;

  /* Cuvintele unui text, aduse la o formă comparabilă: fără diacritice, fără cuvinte de umplutură,
     tăiate la 6 litere (reabilitarea = reabilitare, drumurilor = drumuri). Cifrele și numerele romane
     („Proiectul V", „2014–2020") nu intră aici: ele spun CARE fază a unui program e, și se compară separat. */
  function analiza(text) {
    var cuv = fold(text).match(/[a-z0-9]+/g) || [], st = {}, faza = {};
    cuv.forEach(function (w) {
      if (RX_FAZA.test(w)) { faza[w] = 1; return; }
      if (w.length < 3 || STOP[w]) return;
      st[w.slice(0, 6)] = 1;
    });
    return { st: Object.keys(st), faza: Object.keys(faza) };
  }

  /* ---------------------------------------------------------- finanțatori */

  /* Familii de finanțatori: aceeași organizație scrisă ca cod în acorduri („BERD") și ca nume întreg
     în AMP („Banca Europeană pentru Reconstrucție și Dezvoltare"). Ordinea contează doar la excepții:
     „Banca de Dezvoltare a Consiliului Europei" e CEB, nu Consiliul Europei. */
  var FAMILII = [
    ['ceb', /banca de dezvoltare a consiliului europei|\bceb\b/],
    ['coe', /consiliul europei/],
    ['berd', /reconstructie si dezvoltare(?! .*mondial)|\bberd\b|\bebrd\b/],
    ['bei', /europeana de investitii|\bbei\b|\beib\b/],
    ['bm', /banca mondiala|asociatia internationala pentru dezvoltare|agentia internationala pentru dezvoltare|banca internationala pentru reconstructie|\bbird\b|\baid\b|\bida\b|\bibrd\b|world bank/],
    ['ifc', /corporatia financiara internationala|\bifc\b/],
    ['fmi', /monetar international|\bfmi\b|\bimf\b/],
    ['ue', /uniunea europeana|uniunii europene|comisia europeana|delegatia uniunii|\bue\b|\bce\b|european union|european commission|programul operational comun|\benpi\b|\beni\b|tempus|erasmus|executiva pentru educatie|twinning/],
    ['de', /germani|german|\bkfw\b|\bgiz\b|\bgtz\b|\bbmz\b|siemens/],
    ['jp', /japon|\bjica\b|\bjbic\b/],
    ['us', /statele unite|statelor unite|\bsua\b|usaid|\bmcc\b|provocarile mileniului|millennium challenge|united states/],
    ['ch', /elveti|\bsdc\b|\bdez\b/],
    ['ro', /rom[ai]ni/],                      // „România" iese din fold() ca „rominia"
    ['pl', /polon|polan/],
    ['tr', /turci|turc|\btika\b/],
    ['cn', /china|chinez/],
    ['fr', /\bafd\b|franc[ae]|franta|franceza/],
    ['fida', /\bfida\b|\bifad\b|dezvoltare agricola/],
    ['nl', /oland|tarilor de jos|neerland/],
    ['se', /sued|\bsida\b/],
    ['cz', /cehi|\bceh|republica ceha/],
    ['at', /austri/],
    ['uk', /regatul unit|marii britanii|\bfcdo\b|\buk\b/],
    ['it', /ital/],
    ['dk', /danemarc/],
    ['fi', /finland/],
    ['no', /norvegi/],
    ['li', /liechtenstein/],
    ['sk', /slovac/],
    ['kw', /kuweit|kuwait/],
    ['nordic', /nordic|\bndf\b|nefco/],
    ['onu', /natiunilor unite|\bonu\b|\bpnud\b|\bundp\b|\bpam\b|\bwfp\b|unicef|\bfao\b|\boim\b|\biom\b|unhcr|unfpa|\bunep\b|organizatia mondiala a sanatatii|\boms\b|organizatia internationala a muncii|\bilo\b|organizatia internationala pentru migratie|energie atomica|\baiea\b/],
    ['crucea', /crucea rosie|\bficr\b|semiluna/],
    ['be', /belgi/], ['ca', /canad/], ['ru', /rusi|federatia rusa/], ['bg', /bulgari/], ['hu', /ungar/], ['kz', /kazah/],
    ['ee', /eston/], ['lt', /lituani/], ['lv', /leton/], ['lu', /luxemburg/], ['kr', /coree/], ['il', /israel/],
    ['fg', /fondul global|global fund/],
    ['gef', /fondul global de mediu|\bgef\b/]
  ];

  /* Familiile unui text (un cod de partener sau un șir de nume de finanțatori). */
  function familii(text) {
    var t = fold(text), out = {};
    FAMILII.forEach(function (f) { if (f[1].test(t)) out[f[0]] = 1; });
    // „Fondul Global de Mediu" nu e „Fondul Global pentru Combaterea SIDA"
    if (out.gef) delete out.fg;
    return Object.keys(out);
  }

  /* da = au o familie comună; necunoscut = unul dintre ei nu e recunoscut (bancă comercială, firmă,
     țară rară) — nu putem spune că nu se potrivesc; nu = ambele recunoscute, fără nimic comun. */
  function compatibil(partener, donatori) {
    var a = familii(partener), b = familii((donatori || []).join(' | '));
    if (!a.length || !b.length) return 'necunoscut';
    return a.some(function (x) { return b.indexOf(x) > -1; }) ? 'da' : 'nu';
  }

  /* ---------------------------------------------------------------- sume */

  function sumeAcord(a) {
    var o = [];
    if (a.suma && a.suma.eur) o.push({ v: a.suma.eur, sursa: a.suma.sursa || 'acord' });
    (a.alte || []).forEach(function (x) { if (x.eur) o.push({ v: x.eur, sursa: x.sursa || 'alta' }); });
    if (a.cost && a.cost.eur) o.push({ v: a.cost.eur, sursa: 'cost' });
    return o;
  }
  function sumeProiect(p) {
    var o = [];
    if (p.ang > 0) o.push({ v: p.ang, sursa: 'angajamente' });
    if (p.vp > 0) o.push({ v: p.vp, sursa: 'valoare propusă' });
    return o;
  }
  /* Cea mai apropiată pereche de sume, dacă e în toleranță. */
  function potrivireSuma(a, p) {
    var sa = sumeAcord(a), sp = sumeProiect(p);
    if (!sa.length || !sp.length) return { stare: 'necunoscut' };
    var best = null;
    sa.forEach(function (x) {
      sp.forEach(function (y) {
        var mare = Math.max(x.v, y.v), mic = Math.min(x.v, y.v);
        if (mic < SUMA_MIN) return;
        var rel = (mare - mic) / mare;
        if (rel <= TOLERANTA_SUMA && (!best || rel < best.rel)) best = { rel: rel, acord: x, proiect: y };
      });
    });
    return best ? { stare: 'da', rel: best.rel, acord: best.acord, proiect: best.proiect } : { stare: 'nu' };
  }

  /* ---------------------------------------------------------------- date */

  function anDin(s) { var m = /(\d{4})\s*$/.exec(String(s || '')) || /^(\d{4})/.exec(String(s || '')); return m ? +m[1] : null; }

  /* Începutul proiectului față de anul acordului. În AMP, „începutul" e de obicei primul an cu bani,
     nu data semnării: o diferență de câțiva ani în plus e normală, un proiect care a început cu mult
     ÎNAINTEA acordului nu poate fi proiectul lui. */
  function aniAcord(a) {
    var ani = {};
    [a.semnat, a.primul, a.ultimul].forEach(function (d) { var y = anDin(d); if (y) ani[y] = 1; });
    (a.acte || []).forEach(function (x) { var y = anDin(x.data); if (y) ani[y] = 1; });
    return Object.keys(ani).map(Number);
  }
  /* Un „acord" din registru poate cuprinde decenii: sub aceeași denumire stau actele unui acord din 2006
     și ale amendamentului lui din 2026. De aceea comparăm cu TOȚI anii actelor, nu doar cu cel al semnării:
     proiectul e plauzibil dacă începe într-o fereastră în jurul oricăruia dintre ei. */
  function dataPlauzibila(a, p) {
    var ani = aniAcord(a);
    if (!ani.length || !p.inceput) return 'necunoscut';
    return ani.some(function (y) { var d = p.inceput - y; return d >= FEREASTRA_ANI[0] && d <= FEREASTRA_ANI[1]; }) ? 'da' : 'nu';
  }

  /* Faza: „Proiectul V" nu e „Proiectul VI". Dacă ambele denumiri spun o fază și nu spun aceeași, diferă. */
  function fazaDiferita(fa, fp) {
    if (!fa.length || !fp.length) return false;
    var comune = fa.filter(function (x) { return fp.indexOf(x) > -1; }).length;
    return comune === 0 || (comune < fa.length && comune < fp.length);
  }

  /* ------------------------------------------------------------- potrivire */

  /* acorduri: lista din date/acorduri_legare.json.
     proiecte: [{id, titluri:[…], donatori:[…], inceput:an, ang, deb, vp}].
     confirmari: {confirmate:{idAcord:[idAmp…]}, respinse:{idAcord:[idAmp…]}, fara_proiect:[idAcord…]}. */
  function potriveste(acorduri, proiecte, confirmari) {
    confirmari = confirmari || {};
    var conf = confirmari.confirmate || {}, resp = confirmari.respinse || {};
    var faraProiect = {};
    (confirmari.fara_proiect || []).forEach(function (id) { faraProiect[id] = 1; });

    // IDF: un cuvânt care apare în multe denumiri („energetic", „școli") deosebește puțin
    var df = {}, N = 0;
    var numara = function (st) { N++; st.forEach(function (w) { df[w] = (df[w] || 0) + 1; }); };
    var pr = proiecte.map(function (p) {
      var v = (p.titluri || []).filter(Boolean).map(analiza);
      v.forEach(function (x) { numara(x.st); });
      return { p: p, v: v, byId: p.id };
    });
    var ac = acorduri.map(function (a) {
      var v = [a.scurt, a.nume].filter(Boolean).map(analiza);
      v.forEach(function (x) { numara(x.st); });
      return { a: a, v: v };
    });
    var idf = function (w) { return Math.log(1 + N / (1 + (df[w] || 0))); };

    // index: cuvânt → proiecte (pentru a nu compara fiecare acord cu fiecare proiect)
    var index = {};
    pr.forEach(function (x, i) {
      var vazut = {};
      x.v.forEach(function (t) { t.st.forEach(function (w) { if (!vazut[w]) { vazut[w] = 1; (index[w] = index[w] || []).push(i); } }); });
    });

    var proiectPeId = {};
    pr.forEach(function (x) { proiectPeId[x.p.id] = x; });

    var scorTitlu = function (a, p) {
      var wa = 0, wp = 0, wi = 0, ni = 0, pset = {};
      p.st.forEach(function (w) { pset[w] = 1; wp += idf(w); });
      a.st.forEach(function (w) { wa += idf(w); if (pset[w]) { wi += idf(w); ni++; } });
      if (!wa || !wp || ni < 2 && !(a.st.length === 1 && ni === 1)) return null;
      return { acop: wi / wa, dice: 2 * wi / (wa + wp), comune: ni };
    };

    var rezultate = ac.map(function (x) {
      var a = x.a, cand = {}, legaturi = [];
      // candidate: proiecte care au cel puțin două cuvinte comune cu vreo variantă a denumirii
      x.v.forEach(function (va) {
        var nr = {};
        va.st.forEach(function (w) { (index[w] || []).forEach(function (i) { nr[i] = (nr[i] || 0) + 1; }); });
        Object.keys(nr).forEach(function (i) { if (nr[i] >= 2 || va.st.length === 1) cand[i] = 1; });
      });
      Object.keys(cand).forEach(function (i) {
        var q = pr[+i], best = null;
        x.v.forEach(function (va) {
          q.v.forEach(function (vp) {
            var s = scorTitlu(va, vp);
            if (!s || s.acop < PRAG_ACOPERIRE || s.dice < PRAG_DICE) return;
            var scor = 0.6 * s.acop + 0.4 * s.dice;
            if (!best || scor > best.scor) best = { scor: scor, acop: s.acop, dice: s.dice, faza: fazaDiferita(va.faza, vp.faza) };
          });
        });
        if (!best) return;
        var donator = compatibil(a.parteneri, q.p.donatori);
        if (donator === 'nu') return;                              // alt finanțator: nu e proiectul lui
        var suma = potrivireSuma(a, q.p), data = dataPlauzibila(a, q.p), motive = [];
        var nivel = null;
        /* Suma proprie a acordului care coincide cu AMP = dovadă. Costul TOTAL al proiectului (scris în
           același text) care coincide cu AMP spune doar că e același proiect: la un proiect cu mai multe
           acorduri, fiecare ar primi toți banii. De aceea cost-ul singur nu ajunge pentru „suma". */
        var dovadaCost = suma.stare === 'da' && suma.acord.sursa === 'cost';
        var dataOk = data !== 'nu' || best.acop >= PRAG_ACOPERIRE_DATA;
        if (suma.stare === 'da' && !dovadaCost && dataOk && !(best.faza && best.dice < 0.8)) nivel = 'suma';
        else if (!best.faza && data !== 'nu' && best.acop >= PRAG_ACOPERIRE_TITLU) nivel = 'titlu';
        if (!nivel) return;
        /* Finanțator nerecunoscut (un minister trecut drept donor, o firmă): nu putem spune că nu se
           potrivește, dar atunci cerem și o denumire aproape identică. */
        if (donator === 'necunoscut' && nivel === 'titlu' && !(best.acop >= 0.85 && best.dice >= 0.6)) return;
        if (dovadaCost) motive.push('costul total al proiectului coincide');
        if (best.faza) motive.push('faza');
        if (suma.stare === 'nu') motive.push('suma diferă');
        if (suma.stare === 'necunoscut') motive.push('suma necunoscută');
        if (donator === 'necunoscut') motive.push('finanțator nerecunoscut');
        if (data === 'nu') motive.push('data');
        legaturi.push({ idProiect: q.p.id, nivel: nivel, scor: best.scor, titlu: best.acop, suma: suma, donator: donator, data: data, motive: motive });
      });
      return { acord: a, legaturi: legaturi };
    });

    /* Un acord cu două proiecte care i se potrivesc la sumă: contează cât de bine. „Deșeuri solide"
       (BEI, 25 mil. EUR) are un proiect cu 25,0 mil. și altul, „Deșeuri solide Chișinău", cu 23,6 mil.;
       al doilea nu are aceeași valoare să fie ales. */
    rezultate.forEach(function (r) {
      var s = r.legaturi.filter(function (l) { return l.nivel === 'suma'; });
      if (s.length < 2) return;
      var cel = Math.min.apply(null, s.map(function (l) { return l.suma.rel; }));
      s.forEach(function (l) {
        if (l.suma.rel - cel > 0.03) { l.nivel = 'ambiguu'; l.motive.push('alt proiect se potrivește mai bine la sumă'); }
      });
    });

    /* --- ambiguitate ---
       La nivelul titlului nu putem alege între proiecte la fel de potrivite; nu alegem. */
    rezultate.forEach(function (r) {
      var doarTitlu = r.legaturi.filter(function (l) { return l.nivel === 'titlu'; });
      if (doarTitlu.length > 1) {
        var max = Math.max.apply(null, doarTitlu.map(function (l) { return l.scor; }));
        var aproape = doarTitlu.filter(function (l) { return max - l.scor < DIFERENTA_AMBIGUA; });
        if (aproape.length > 1) aproape.forEach(function (l) { l.nivel = 'ambiguu'; l.motive.push('mai multe proiecte potrivite'); });
      }
    });
    /* Același proiect legat doar după titlu de mai multe acorduri: de la „Reabilitarea drumurilor —
       Proiectul V" și „— Proiectul VI" nu putem ști care e al cui. Acordurile cu același finanțator
       recunoscut și nume diferite sunt într-adevăr diferite; cele cu finanțatori diferiți (BEI + BERD
       pentru „Deșeuri solide") îl pot împărți. */
    var peProiect = {};
    rezultate.forEach(function (r) {
      r.legaturi.forEach(function (l) { if (l.nivel === 'titlu') (peProiect[l.idProiect] = peProiect[l.idProiect] || []).push({ r: r, l: l }); });
    });
    Object.keys(peProiect).forEach(function (id) {
      var L = peProiect[id];
      if (L.length < 2) return;
      var parteneri = {};
      L.forEach(function (x) { parteneri[familii(x.r.acord.parteneri).sort().join('+') || '?'] = 1; });
      if (Object.keys(parteneri).length === L.length && L.every(function (x) { return x.l.donator === 'da'; })) return;
      L.forEach(function (x) { x.l.nivel = 'ambiguu'; x.l.motive.push('același proiect pentru ' + L.length + ' acorduri'); });
    });

    /* --- confirmările unui om bat orice potrivire automată --- */
    rezultate.forEach(function (r) {
      var id = r.acord.id, respinse = {}, deja = {};
      (resp[id] || []).forEach(function (x) { respinse[x] = 1; });
      r.legaturi = r.legaturi.filter(function (l) { return !respinse[l.idProiect]; });
      (conf[id] || []).forEach(function (idAmp) {
        var q = proiectPeId[idAmp];
        var existent = r.legaturi.filter(function (l) { return l.idProiect === idAmp; })[0];
        if (existent) { existent.nivel = 'confirmat'; deja[idAmp] = 1; return; }
        r.legaturi.push({ idProiect: idAmp, nivel: 'confirmat', scor: 1, titlu: 1, donator: 'da', data: 'da', motive: q ? [] : ['proiectul nu e în datele de azi'],
                          suma: q ? potrivireSuma(r.acord, q.p) : { stare: 'necunoscut' } });
      });
      var rang = { confirmat: 0, suma: 1, titlu: 2, ambiguu: 3 };
      r.legaturi.sort(function (x, y) { return rang[x.nivel] - rang[y.nivel] || y.scor - x.scor; });
      r.faraProiect = !!faraProiect[id];
      r.stare = r.legaturi.length ? r.legaturi[0].nivel : (r.faraProiect ? 'fara-confirmat' : 'fara');
    });

    // legăturile văzute dinspre proiect: „care e baza legală a acestui proiect?"
    var peProiectFinal = {};
    rezultate.forEach(function (r) {
      r.legaturi.forEach(function (l) { (peProiectFinal[l.idProiect] = peProiectFinal[l.idProiect] || []).push({ acord: r.acord, nivel: l.nivel, scor: l.scor }); });
    });
    /* Proiect folosit de mai multe acorduri (BEI și BERD finanțează „Deșeuri solide"; un acord de bază și
       finanțările lui adiționale): banii lui nu sunt ai unui singur acord. Se vede pe legătură. */
    rezultate.forEach(function (r) {
      r.legaturi.forEach(function (l) {
        var altele = (peProiectFinal[l.idProiect] || []).filter(function (x) { return x.acord.id !== r.acord.id && x.nivel !== 'ambiguu'; });
        l.partajat = altele.length;
      });
    });
    return { rezultate: rezultate, peProiect: peProiectFinal };
  }

  /* Banii din spatele unui acord: angajat și debursat în AMP, adunate peste proiectele legate.
     Doar legăturile sigure (confirmat, suma) intră în total; cele „după titlu" se arată separat. */
  function bani(rez, proiectPeId) {
    var out = { ang: 0, deb: 0, proiecte: 0, siguri: 0, probabile: { ang: 0, deb: 0, proiecte: 0 } };
    rez.legaturi.forEach(function (l) {
      var p = proiectPeId[l.idProiect];
      if (!p) return;
      var sigur = l.nivel === 'confirmat' || l.nivel === 'suma';
      if (sigur && l.partajat) { out.partajate = (out.partajate || 0) + 1; out.ang += p.ang || 0; out.deb += p.deb || 0; out.siguri++; }
      else if (sigur) { out.ang += p.ang || 0; out.deb += p.deb || 0; out.siguri++; }
      else if (l.nivel === 'titlu') { out.probabile.ang += p.ang || 0; out.probabile.deb += p.deb || 0; out.probabile.proiecte++; }
      out.proiecte++;
    });
    return out;
  }

  var API = {
    potriveste: potriveste, bani: bani,
    // expuse pentru teste
    analiza: analiza, familii: familii, compatibil: compatibil, potrivireSuma: potrivireSuma,
    dataPlauzibila: dataPlauzibila, fazaDiferita: fazaDiferita, fold: fold,
    CONSTANTE: { TOLERANTA_SUMA: TOLERANTA_SUMA, SUMA_MIN: SUMA_MIN, PRAG_ACOPERIRE: PRAG_ACOPERIRE, PRAG_DICE: PRAG_DICE }
  };
  if (typeof module !== 'undefined' && module.exports) module.exports = API;
  else rad.LegaturaAmp = API;
})(typeof window !== 'undefined' ? window : this);
