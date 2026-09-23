/* Căutarea acordurilor pe legis.md. Rulată de legis_watch.py într-o pagină
   deschisă pe www.legis.md (după ce Cloudflare a lăsat-o să treacă).

   Înainte, legis_watch.py setează window.LX_KNOWN = [doc_id-urile deja în
   bază pentru anii căutați]. Scriptul pornește căutările în fundal și se
   întoarce imediat; starea e în window.LX { pas, total, gata, err, rows }.
   La final, LX.noi() întoarce, ca text JSON, doar actele care NU sunt în bază.

   De ce două cereri pe căutare: legis.md ține parametrii căutării în sesiune
   (getResults) și dă rezultatele separat (getAjaxContent). URL-ul celei de-a
   doua e mereu același, deci cererile merg cu cache:'no-store' — altfel
   browserul întoarce rezultatele căutării precedente.

   Anii (ANI) sunt înlocuiți de legis_watch.py cu cei calculați după ora
   Chișinăului; valoarea de aici e doar pentru rularea manuală în consolă. */
(function(){
  var AJ = 'https://www.legis.md/cautare/getAjaxContent?filter_title=&filtru=&f0=&f1=&f2=&f3=&f4=&f5=&f6=&f7=&f8=&f9=&f10=&f11=&f12=&f13=&f14=&f15=&f16=&f17=&f18=&f19=&f20=&mi=&ag=&al=';
  var KW = ['împrumut','grant','finanțare','credit','asistență','cooperare tehnică','cooperare financiară',
            'schimb de note','Memorandum','donați','Banca','Fondul','Asociația Internațională','Agenția',
            'Corporația','ajutor','acord-cadru','facilitate'];
  var azi = new Date(), an = azi.getFullYear();
  var ANI = [String(an)]; if (azi.getMonth() < 3) ANI.push(String(an - 1));

  function sleep(ms){ return new Promise(function(r){ setTimeout(r, ms); }); }
  async function get(u){
    var c = new AbortController(), t = setTimeout(function(){ c.abort(); }, 20000);
    try { var r = await fetch(u, {cache:'no-store', signal:c.signal}); return await r.text(); }
    finally { clearTimeout(t); }
  }
  function parse(t){
    var d = document.createElement('div'); d.innerHTML = t; var out = [];
    d.querySelectorAll('tr').forEach(function(tr){
      var a = tr.querySelector('a[href*="doc_id="]'); if (!a) return;
      var x = tr.innerText.replace(/\s+/g,' ').trim();
      var m = /\(([A-Za-zА-я]+\d+[^)]*\/\d{4})\)\s*(\d\d-\d\d-\d{4})\s*(.*)/.exec(x); if (!m) return;
      out.push({c:m[1], pub:m[2], t:m[3], id:a.href.match(/doc_id=(\d+)/)[1]});
    });
    return out;
  }
  async function cauta(kw, y){
    var q = new URLSearchParams({document_status:'0', nr_doc:'', datepicker1:y, publication_status:' - TOATE - ',
                                 nr:'', publish_date:'', search_type:'1', search_string:kw});
    for (var i = 0; i < 5; i++){
      try {
        var t1 = await get('https://www.legis.md/cautare/getResults?' + q);
        if (/Just a moment/.test(t1)) { LX.cloudflare++; await sleep(10000 * (i + 1)); continue; }
        var t = await get(AJ + '&_=' + Date.now());
        if (/Just a moment/.test(t)) { LX.cloudflare++; await sleep(10000 * (i + 1)); continue; }
        var p = parse(t);
        // sesiune veche: majoritatea rezultatelor din alt an
        var bun = p.filter(function(o){ return o.c.endsWith('/' + y) || o.c.endsWith('/' + (+y + 1)); }).length;
        if (p.length && bun < p.length / 2) { await sleep(4000); continue; }
        return {ok:true, p:p};
      } catch(e) { await sleep(5000); }
    }
    return {ok:false, p:[]};
  }

  window.LX = {pas:0, total:ANI.length * KW.length, gata:false, err:[], rows:{}, cloudflare:0, ani:ANI,
    noi: function(){
      var k = {}; (window.LX_KNOWN || []).forEach(function(i){ k[String(i)] = true; });
      var r = Object.keys(LX.rows).filter(function(i){ return !k[i]; }).map(function(i){ return LX.rows[i]; });
      return JSON.stringify({extras: new Date().toISOString(), ani: LX.ani, err: LX.err,
        cloudflare: LX.cloudflare, gasite: Object.keys(LX.rows).length, rows: r});
    }};

  (async function(){
    for (var i = 0; i < ANI.length; i++) for (var j = 0; j < KW.length; j++){
      var r = await cauta(KW[j], ANI[i]); LX.pas++;
      if (!r.ok) { LX.err.push(ANI[i] + ' ' + KW[j]); continue; }
      r.p.forEach(function(o){ if (!LX.rows[o.id]) LX.rows[o.id] = {id:o.id, c:o.c, pub:o.pub, t:o.t, kw:[]}; LX.rows[o.id].kw.push(KW[j]); });
      await sleep(900);
    }
    LX.gata = true;
  })();
  return 'pornit: ' + LX.total + ' căutări pentru ' + ANI.join(', ');
})();
