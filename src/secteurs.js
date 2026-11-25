/* ===== Lignes secteurs / segments (format tableau) ===== */
const MENTION_AV="";
const srPos=x=>`${Math.max(0,Math.min(100,x))}%`;
function srWarn(s){return s.warn.length?`<span class="sec-warn" title="${s.warn.join(' ')}">⚠ ${s.ath.dd>=-2?'Proche du plus haut historique':'Proche du plus haut 52 semaines'}</span>`:'';}
function srCells(s){
  const pSec=(typeof pilotOf==='function')?pilotOf(s.sym):null;
  const rec=(pSec&&pSec.etf&&pSec.etf.total!=null)?pSec.etf:((typeof pilotRec==='function'&&s.tv)?pilotRec(s.tv):null);
  if(rec&&rec.total!=null){
    return `<div class="sr-c sr-d">${dualBarPilot(rec, true)}</div>`;
  }
  if((typeof isActionSector==='function'&&isActionSector(s.sym))||(typeof isApexV2Tv==='function'&&isApexV2Tv(s.tv))){
    return `<div class="sr-c sr-d">${typeof v2Placeholder==='function'?v2Placeholder():'<div class="apex10 apex10-na"><b>–</b><small>/ 250</small></div>'}</div>`;
  }
  /* t506u : plus aucune barre /100. Note posée sur 250 → barre pilote ; sinon « – / 250 ». */
  const r250=(typeof apex250Rec==='function'&&s.apex10&&(s.apex10.scale===250||s.apex10.total_max===250||s.apex10.v2))?apex250Rec(s.apex10):null;
  if(r250&&typeof dualBarPilot==='function') return `<div class="sr-c sr-d">${dualBarPilot(r250, true)}</div>`;
  return `<div class="sr-c sr-d">${typeof v2Placeholder==='function'?v2Placeholder():'<div class="apex10 apex10-na"><b>–</b><small>/ 250</small></div>'}</div>`;
}
function srHead(first,v2){
  const mid=(v2==='metaux')
    ? `<i class="db-dot db-a">AV</i>Score APEX (−50 à 250, échelle du haut) · <i class="db-dot db-s">S</i>Fear &amp; Greed et <i class="db-dot db-h">H</i>Hype / attention (0 à 100, échelle du bas ; H à contre-courant, comptant 0→+90 … 100→0)`
    : (!v2||v2===100||v2==='100'||v2===250||v2==='250')
    ? `<i class="db-dot db-a">AV</i>Score APEX (−50 à 250, échelle du haut) · <i class="db-dot db-s">S</i>Fear &amp; Greed (0 à 100, échelle du bas)`
    : v2
    ? `<i class="db-dot db-a">AV</i>Score APEX (−50 à 250, échelle du haut) · <i class="db-dot db-s">S</i>Fear &amp; Greed et <i class="db-dot db-h">H</i>Hype / attention (0 à 100, échelle du bas ; H à contre-courant, ±27)`
    : '';
  return `<div class="sr sr-hd" aria-hidden="true"><div>${first}</div><div>${mid}</div><div>Détails</div></div>`;
}
/* Les panneaux <details> s'ouvrent sous la ligne ; leurs boutons sont placés dans la dernière colonne */
function srWire(root){
  root.querySelectorAll('.sec').forEach(sec=>{const box=sec.querySelector('.sr-b');
    sec.querySelectorAll(':scope>details').forEach(d=>{d.classList.add('sec-p');
      const b=document.createElement('button');b.type='button';b.className='sr-btn';b.textContent=d.querySelector(':scope>summary').textContent;
      const st=()=>{b.setAttribute('aria-expanded',d.open);b.classList.toggle('on',d.open);sec.classList.toggle('sec-open',!!sec.querySelector(':scope>details[open]'));};
      b.addEventListener('click',()=>{d.open=!d.open;});d.addEventListener('toggle',st);st();box.appendChild(b);});});
}
/* ===== Onglet Actions · SECTEURS : sentiment 0-100 + compteur ACHAT / VENTE par secteur GICS (ETF SPDR) ===== */
const SEC=JSON.parse(document.getElementById('data5').textContent);
function secTile(s,i){
  const v=s.sent.value,a=s.av.score,pos=x=>`${Math.max(0,Math.min(100,x))}%`;
  const sc=(s.sent.components||[]).map(c=>`<div class="ind-sb"><div class="ind-sbl"><span>${c.name}</span><b class="sc-t" style="color:${c.value==null?'#888':gmir(c.value)}">${c.value==null?'n.d.':fmt(c.value,0)}</b></div><div class="ind-sbt">${c.value==null?'':`<i style="width:${pos(c.value)};background:${gmir(c.value)}"></i>`}</div><div class="ind-sbd">poids ${fmt(c.weight*100,1)} % · ${c.raw}</div></div>`).join('');
  const avSrc=(s.av&&s.av.components)?s.av:(s.av_instrument||s.av_panier||s.av||{});
  const ac=(avSrc.components||[]).map(c=>{const n=c.note;return `<div class="av-c"><div class="av-cl"><span>${c.nom}</span><b style="color:${n==null?'#888':avCol(n)}">${n==null?(c.facultatif?'non comptée':'n.d.'):sign(n,0)}</b></div><div class="av-cb"><div class="av-mid"></div>${n==null?'':`<i style="${n>=0?'left:50%':'right:50%'};width:${Math.abs(n)/2}%;background:${avCol(n)}"></i>`}</div><div class="av-cd">valeur ${c.valeur} · poids ${pw(c.poids)} % · contribution <b>${c.contrib==null?(c.facultatif?'non comptée':'retirée'):sign(c.contrib,1)}</b> · règle : ${c.regle}</div></div>`;}).join('');
  return `<div class="sec">
   <div class="sr">
    <div class="sr-c sec-h sr-n"><b>${s.nom}</b><span class="pilot-badge">APEX ACHAT −50 à 250</span><span>${s.tick||s.sym} · ${s.etf}</span>${srWarn(s)}</div>
    ${srCells(s)}
    <div class="sr-c sr-b"></div>
   </div>
   ${typeof fondList==='function'?fondList(s.sym):''}
   <details class="ind-meth sec-det" data-i="${i}"><summary>Détail et historique 1 an</summary>
     <p class="sr-close">Clôture hebdomadaire du ${dshort(s.date)} : <b>${fmt(s.close,2)} ${s.currency==='EUR'?'€':'$'}</b> (${s.tv||s.sym} · ${s.etf}) · bougie clôturée${s.live?` ; semaine en cours au ${dshort(s.live.date)} : ${fmt(s.live.close,2)} ${s.currency==='EUR'?'€':'$'}, non utilisée`:''}.</p>${s.note_revolut?`<p class="sr-close">${s.note_revolut}</p>`:''}
     ${s.warn.map(w=>`<div class="note">${w}</div>`).join('')}
     <div class="ind-subt" style="margin-top:8px">Sentiment, 52 semaines (moy. ${fmt(s.sent.avg,0)} · min ${fmt(s.sent.min[1],0)} le ${dshort(s.sent.min[0])} · max ${fmt(s.sent.max[1],0)} le ${dshort(s.sent.max[0])})</div>
     <div class="ind-spark" style="height:90px"><canvas id="cSecS${i}"></canvas></div>
     <p class="sent-mir">Couleurs du sentiment (points de la courbe, barres des composantes) en dégradé miroir, lecture contrarienne : peur = bleu (zone d'achat), euphorie = rouge (zone de vente).</p>
     <div class="ind-subt">Achat / Vente${(avSrc.avg!=null&&avSrc.min&&avSrc.max)?`, 52 semaines (moy. ${sign(avSrc.avg,0)} · min ${sign(avSrc.min[1],0)} · max ${sign(avSrc.max[1],0)})`:''}</div>
     <div class="ind-spark" style="height:90px"><canvas id="cSecA${i}"></canvas></div>
     <div class="ind-sub"><div class="ind-subt">Composantes du sentiment (0-100)</div>${sc}</div>
     <div class="ind-sub"><div class="ind-subt">Composantes Achat / Vente (−100 à +100)</div>${ac}</div>
     <p>Plus haut historique des clôtures hebdomadaires disponibles (depuis le ${dshort(s.first)}) : ${fmt(s.ath.close,2)} ${s.currency==='EUR'?'€':'$'} le ${dshort(s.ath.date)}, soit ${sign(s.ath.dd,1)} %. Distance au plus haut 52 semaines : ${sign(s.dd52,1)} %.</p>
     <p>Source : ${lnk(s.url,'Yahoo Finance · '+(s.yahoo||s.sym)+' ('+s.etf+')')}, secteur GICS « ${s.gics} ». Données récupérées le ${s.retrieved.replace(' ',' à ')} (heure de Paris).</p>
   </details>
  </div>`;
}
function secCharts(det){
  if(det.dataset.done)return;det.dataset.done='1';const s=SEC.sectors[+det.dataset.i],i=det.dataset.i;
  const x={ticks:{maxTicksLimit:3,maxRotation:0,autoSkip:true,font:{size:9}},grid:{display:false}};
  const ml=d=>new Date(d).toLocaleDateString('fr-FR',{month:'short',year:'2-digit'});
  const ss=s.sent.series||[],ah=(s.av&&s.av.history)||(s.av_instrument&&s.av_instrument.history)||(s.av_panier&&s.av_panier.history)||[];
  charts.push(new Chart(document.getElementById('cSecS'+i),{type:'line',data:{labels:ss.map(p=>ml(p[0])),datasets:[{data:ss.map(p=>p[1]),borderColor:'rgba(255,255,255,.55)',borderWidth:1.2,pointRadius:2,pointBackgroundColor:ss.map(p=>gmir(p[1])),pointBorderWidth:0,tension:.25}]},
    options:{maintainAspectRatio:false,animation:false,plugins:{legend:{display:false},tooltip:{callbacks:{title:c=>dshort(ss[c[0].dataIndex][0])}}},scales:{x,y:{min:0,max:100,ticks:{stepSize:50,font:{size:9}}}}}}));
  charts.push(new Chart(document.getElementById('cSecA'+i),{type:'bar',data:{labels:ah.map(p=>ml(p[0])),datasets:[{data:ah.map(p=>p[1]),backgroundColor:ah.map(p=>avCol(p[1])),borderWidth:0,barPercentage:1,categoryPercentage:.9}]},
    options:{maintainAspectRatio:false,animation:false,plugins:{legend:{display:false},tooltip:{callbacks:{title:c=>dshort(ah[c[0].dataIndex][0])}}},scales:{x,y:{min:-100,max:100,ticks:{stepSize:100,font:{size:9}}}}}}));
}
function renderSecteurs(el){
  const S=SEC.sectors,d=S[0].date,cnt=z=>S.filter(s=>s.av&&s.av.label&&s.av.label.includes(z)).length;
  const hi=S.reduce((a,b)=>b.sent.value>a.sent.value?b:a),lo=S.reduce((a,b)=>b.sent.value<a.sent.value?b:a);
  const nAth=S.filter(s=>s.warn.length).length;
  const c=document.createElement('div');c.className='card no-group pays-card';c.dataset.cc='us';
  const stUs=(typeof sectionApexAvg==='function')?sectionApexAvg('actions'):null;
  const a10=(stUs&&(stUs.apexV2||stUs.apex10))||SEC.apex10||null;
  const avP=SEC.av_pays||null;
  const scale=a10&&(a10.v2||a10.total_max===280||a10.scale===280||a10.total_max===250||a10.scale===250||a10.total_max===270||a10.scale===270)?'250':'100';
  const disp=a10?(a10.total!=null?String(a10.total):a10.display):'';
  const apexTag=a10&&(a10.display||a10.total!=null)?`<span class="js-apex10" hidden data-display="${disp}" data-hex="${a10.hex||''}" data-note="${a10.total!=null?a10.total:a10.note}" data-scale="${scale}"></span>`:'';
  const mkt=avP&&avP.score!=null?` · <i>Marché</i> <b>${avP.label||''} ${sign(avP.score,0)}</b>`:'';
  c.innerHTML=`<h2><img class="flag-us" src="flag-us.png" width="28" height="15" alt="Drapeau des États-Unis">Secteurs USA · sentiment et achat / vente</h2>
   <div class="desc acc-sum">${apexTag}11 secteurs GICS · au ${dshort(d)}${mkt} · <i>Achat</i> <b>${cnt('Achat')}</b> · <i>Neutre</i> <b>${cnt('Neutre')}</b> · <i>Vente</i> <b>${cnt('Vente')}</b> · <i>sentiment max</i> <b>${hi.nom} ${fmt(hi.sent.value,0)}</b> · <i>min</i> <b>${lo.nom} ${fmt(lo.sent.value,0)}</b>${nAth?` · <i>⚠ près du record</i> <b>${nAth}</b>`:''}</div>
   <div class="sec-grid">${srHead('Secteur · ETF principal', true)}${S.map(secTile).join('')}</div>
   <details class="ind-meth"><summary>Méthode et pondérations</summary>
     <p><b>Sentiment Peur / Euphorie (0-100).</b> ${SEC.method_sent}</p>
     <p><b>Achat / Vente (−100 à +100).</b> ${SEC.method_av}</p>
     <p>Chaque secteur est représenté par un ETF UCITS achetable chez Revolut, coté en euros sur Xetra, qui suit le même indice que l'ETF SPDR Select Sector américain (non vendu aux particuliers en Europe) : ${S.map(s=>(s.tick||s.sym)+' = '+s.nom+(s.tick?' (au lieu de '+s.sym+')':'')).join(' · ')}. Exception : l'énergie est suivie par XDW0, indice MSCI World Energy (mondial). Historique plus court que les ETF US et force relative contre le S&P 500 en dollars, donc avec l'effet de change. Seules les bougies hebdomadaires clôturées (vendredi passé) sont utilisées ; une semaine en cours serait signalée et ignorée. Le S&P 500 (^GSPC) sert de référence pour la force relative. Calcul reproductible avec <code>src/build_secteurs.py</code>.</p>${typeof FOND!=='undefined'?fondMethod():''}</details>
   <div class="src">Source : ${lnk('https://finance.yahoo.com/quote/XLK/history/','Yahoo Finance')} (clôtures hebdomadaires des ETF SPDR et du S&P 500), ${lnk('https://www.ssga.com/us/en/intermediary/etfs/fund-finder','State Street SPDR')}. Récupéré le ${S[0].retrieved.replace(' ',' à ')} (heure de Paris).</div>`;
  el.appendChild(c);srWire(c);
  c.querySelectorAll('.sec-det').forEach(dt=>dt.addEventListener('toggle',()=>{if(dt.open)secCharts(dt);}));
}
