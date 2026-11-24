/* ===== Helpers communs aux onglets Actions / Crypto / Liquidités ===== */
const T2=JSON.parse(document.getElementById('data2').textContent);
const lnk=(u,t)=>`<a href="${u}" target="_blank" rel="noopener">${t}</a>`;
const dshort=s=>new Date(s).toLocaleDateString('fr-FR',{day:'numeric',month:'short',year:'numeric'});
const big=v=>v>=1e12?fmt(v/1e12,2)+' T$':v>=1e9?fmt(v/1e9,1)+' Md$':fmt(v,0)+' $';
const kpi=(l,v,s,c='')=>`<div class="kpi"><div class="l">${l}</div><div class="v ${c}">${v}</div><div class="s">${s}</div></div>`;
const na=(l,why)=>`<div class="kpi na"><div class="l">${l}</div><div class="v">non récupéré</div><div class="s">${why}</div></div>`;
function merge(list){ // list: [[ [k,v],... ], ...] -> {labels, data:[...]}
  const keys=[...new Set(list.flatMap(s=>s.map(x=>x[0])))].sort();
  const maps=list.map(s=>new Map(s.map(x=>[x[0],x[1]])));
  return {labels:keys,data:maps.map(m=>keys.map(k=>m.has(k)?m.get(k):null))};
}
function lineChart(id,labels,sets,opt={}){
  const c=new Chart(document.getElementById(id),{type:'line',data:{labels,datasets:sets.map(s=>Object.assign({pointRadius:0,borderWidth:1.8,tension:.1,spanGaps:true},s))},
   options:Object.assign({maintainAspectRatio:false,animation:false,interaction:{mode:'index',intersect:false},
     plugins:{legend:{display:sets.length>1},tooltip:{callbacks:{label:c=>c.parsed.y==null?'':' '+c.dataset.label+' : '+fmt(c.parsed.y,opt.dec??2)+(opt.unit||'')}}},
     scales:{x:{ticks:{maxTicksLimit:opt.ticks||10,autoSkip:true}},y:Object.assign({type:opt.log?'logarithmic':'linear'},opt.log?{ticks:{callback:v=>{const l=Math.log10(v);return Math.abs(l-Math.round(l))<1e-9?v.toLocaleString('fr-FR'):'';}}}:{},opt.y||{})}},opt.extra||{})});
  charts.push(c);return c;
}
const pctTxt=p=>p?`<span class="${cls(p.pct)}">${sign(p.pct)} %</span>`:'<span class="mut">n.d.</span>';
/* Bloc technique hebdo (RSI 14 Wilder + MACD 12/26/9) */
function techHTML(id){return `<div class="chart" style="height:230px"><canvas id="${id}P"></canvas></div><div class="chart" style="height:130px"><canvas id="${id}R"></canvas></div><div class="chart" style="height:150px"><canvas id="${id}M"></canvas></div>`;}
const techCharts={};
function techDraw(id,t,label){
  (techCharts[id]||[]).forEach(c=>{c.destroy();const i=charts.indexOf(c);if(i>=0)charts.splice(i,1);});
  const L=t.dates.map(d=>dshort(d));
  const a=lineChart(id+'P',L,[{label:label+' (clôture hebdo)',data:t.close,borderColor:'#e6c27a'}],{dec:2,ticks:8});
  const r=lineChart(id+'R',L,[{label:'RSI 14',data:t.rsi,borderColor:'#a9cdf5'},{label:'70',data:t.rsi.map(()=>70),borderColor:'rgba(232,143,143,.5)',borderDash:[4,4],borderWidth:1},{label:'30',data:t.rsi.map(()=>30),borderColor:'rgba(127,209,168,.5)',borderDash:[4,4],borderWidth:1}],{dec:1,ticks:8,y:{min:0,max:100},extra:{plugins:{legend:{display:false}}}});
  const m=new Chart(document.getElementById(id+'M'),{data:{labels:L,datasets:[
    {type:'bar',label:'Histogramme',data:t.hist,backgroundColor:t.hist.map(v=>v>=0?'rgba(127,209,168,.6)':'rgba(232,143,143,.6)')},
    {type:'line',label:'MACD',data:t.macd,borderColor:'#a9cdf5',pointRadius:0,borderWidth:1.5},
    {type:'line',label:'Signal',data:t.signal,borderColor:'#e6c27a',pointRadius:0,borderWidth:1.5}]},
    options:{maintainAspectRatio:false,animation:false,interaction:{mode:'index',intersect:false},plugins:{legend:{labels:{font:{size:10}}}},scales:{x:{ticks:{maxTicksLimit:8}}}}});
  charts.push(m);techCharts[id]=[a,r,m];
}
function techKpis(t){
  const l=t.last,rz=l.rsi>=70?'surachat (≥ 70)':l.rsi<=30?'survente (≤ 30)':'zone neutre';
  const cross=l.macd>=l.signal?'MACD au-dessus du signal':'MACD sous le signal';
  const mom=Math.abs(l.hist)<Math.abs(l.hist_prev)?'histogramme qui se contracte':'histogramme qui s\'élargit';
  return kpi('RSI 14 hebdo',fmt(l.rsi,1),rz+' · clôture du '+dshort(l.date))+kpi('MACD 12/26/9 hebdo',fmt(l.macd,2),cross+' ('+fmt(l.signal,2)+')',l.macd>=l.signal?'up':'down')+kpi('Histogramme MACD',fmt(l.hist,2),mom+' (préc. '+fmt(l.hist_prev,2)+')',l.hist>=0?'up':'down');
}

/* ================= ACTIONS ================= */
function renderActions(el){
  const A=T2.actions,I=A.indices,R=A.retrieved,keys=['cac','spx','world'];
  const rows=keys.map(k=>{const x=I[k];return `<tr><td>${x.name}</td><td>${fmt(x.last.value,2)}</td><td>${pctTxt(x.perf[25])}</td><td>${pctTxt(x.perf[10])}</td><td>${pctTxt(x.perf[5])}</td><td>${pctTxt(x.perf[1])}</td><td class="${cls(x.peak.dd)}">${sign(x.peak.dd)} %</td></tr>`;}).join('');
  const C=A.cape,V=A.vix,TX=A.taux10;
  el.innerHTML=`
  <div class="card"><h2>Grands indices actions · 25 ans</h2>
   <div class="desc">CAC 40, S&P 500 et MSCI World (indices de prix, hors dividendes), clôtures hebdomadaires du ${dshort(I.spx.dates[0])} au ${dshort(I.spx.last.date)}. Courbe rebasée à 100 au départ commun.</div>
   <div class="kpis">${keys.map(k=>kpi(I[k].name,fmt(I[k].last.value,2),'clôture hebdo du '+dshort(I[k].last.date)+' · '+I[k].currency)).join('')}</div>
   <div class="toggle" id="idxScale"><button class="on" data-l="1">Échelle log</button><button data-l="0">Échelle linéaire</button></div>
   <div class="chart" style="height:340px"><canvas id="cIdx"></canvas></div>
   <table style="margin-top:12px"><thead><tr><th>Indice</th><th>Dernière clôture</th><th>25 ans</th><th>10 ans</th><th>5 ans</th><th>1 an</th><th>Écart au plus haut*</th></tr></thead><tbody>${rows}</tbody></table>
   <div class="note">* Plus haut en clôture hebdomadaire depuis 2000 : CAC 40 ${fmt(I.cac.peak.value,2)} (${dshort(I.cac.peak.date)}), S&P 500 ${fmt(I.spx.peak.value,2)} (${dshort(I.spx.peak.date)}), MSCI World ${fmt(I.world.peak.value,2)} (${dshort(I.world.peak.date)}). Performances nominales en devise de l'indice, hors dividendes et hors inflation ; le MSCI World est en USD (effet de change non couvert pour un épargnant en euros). Seules les semaines clôturées sont retenues.</div>
   <div class="src">Source : Yahoo Finance (cotations des indices ${lnk('https://finance.yahoo.com/quote/%5EFCHI/history/','^FCHI')}, ${lnk('https://finance.yahoo.com/quote/%5EGSPC/history/','^GSPC')}, ${lnk('https://finance.yahoo.com/quote/%5E990100-USD-STRD/history/','^990100-USD-STRD (MSCI World)')}), éditeurs : Euronext, S&P Dow Jones Indices, MSCI. Récupéré le ${dfr(R.yahoo.slice(0,10))} à ${R.yahoo.slice(11)}.</div></div>

  <div class="card"><h2>Analyse technique hebdomadaire</h2>
   <div class="desc">RSI 14 (lissage de Wilder) et MACD 12/26/9 calculés sur les clôtures hebdomadaires confirmées (156 dernières semaines affichées). La semaine en cours n'est pas incluse.</div>
   <div class="toggle" id="techSel">${keys.map((k,i)=>`<button class="${i?'':'on'}" data-k="${k}">${I[k].name.split(' (')[0]}</button>`).join('')}</div>
   <div class="kpis" id="techK"></div>${techHTML('cTI')}
   <div class="src">Source des cours : Yahoo Finance, clôtures hebdo · calcul APEX (formules standard) · récupéré le ${dfr(R.yahoo.slice(0,10))}.</div></div>

  <div class="card"><h2>Valorisation · PER de Shiller (CAPE) du S&P 500</h2>
   <div class="desc">Prix rapporté à la moyenne des bénéfices réels sur 10 ans. Série mensuelle depuis ${C.first.slice(0,4)} (affichée depuis 1950).</div>
   <div class="kpis">${kpi('CAPE actuel',fmt(C.last[1],2),'au '+dshort(C.last[0]))+kpi('Moyenne historique',fmt(C.mean,1),'médiane '+fmt(C.median,1)+' · depuis '+C.first.slice(0,4))+kpi('Rang historique',fmt(C.pctile,1)+' %','part des mois où le CAPE était plus bas')+kpi('Record',fmt(C.max[1],2),dshort(C.max[0]))}</div>
   <div class="chart"><canvas id="cCape"></canvas></div>
   <div class="note">Un CAPE élevé a historiquement été associé à des rendements à 10 ans plus faibles, mais ce n'est pas un outil de timing à court terme. La dernière valeur est une estimation intra-mois de multpl.</div>
   <div class="src">Source : ${lnk('https://www.multpl.com/shiller-pe/table/by-month','multpl.com, table mensuelle du Shiller PE')} (données de R. Shiller, ${lnk('http://www.econ.yale.edu/~shiller/data.htm','Yale')}), récupéré le ${dfr(R.multpl.slice(0,10))}. Le fichier Shiller d'origine (ie_data.xls) n'a pas pu être téléchargé (erreur 500).</div></div>

  <div class="grid2">
   <div class="card"><h2>Volatilité · VIX</h2>
    <div class="desc">Volatilité implicite à 30 jours du S&P 500, dernière clôture de chaque semaine depuis 2000.</div>
    <div class="kpis">${kpi('VIX',fmt(V.last[1],2),'clôture du '+dshort(V.last[0]))+kpi('Moyenne depuis 2000',fmt(V.mean,1),'pic '+fmt(V.max[1],1)+' le '+dshort(V.max[0]))}</div>
    <div class="chart" style="height:260px"><canvas id="cVix"></canvas></div>
    <div class="src">Source : CBOE via ${lnk('https://fred.stlouisfed.org/series/VIXCLS','FRED (série VIXCLS)')}, récupéré le ${dfr(R.fred.slice(0,10))}.</div></div>
   <div class="card"><h2>Taux souverains à 10 ans</h2>
    <div class="desc">Treasury US 10 ans contre OAT France 10 ans, moyennes mensuelles depuis 2000.</div>
    <div class="kpis">${kpi('US 10 ans',fmt(TX.us_last[1],2)+' %','quotidien, '+dshort(TX.us_last[0]))+kpi('OAT 10 ans',fmt(TX.oat_last[1],2)+' %','moyenne de '+mfr(TX.oat_last[0]))+(TX.spread_last.v!=null?kpi('Écart OAT − US',sign(TX.spread_last.v,2)+' pt',mfr(TX.spread_last.month)+', moyennes mensuelles'):'')}</div>
    <div class="chart" style="height:260px"><canvas id="cT10"></canvas></div>
    <div class="src">Sources : ${lnk('https://fred.stlouisfed.org/series/DGS10','FRED DGS10')} / ${lnk('https://fred.stlouisfed.org/series/GS10','GS10')} (Federal Reserve), ${lnk('https://data.ecb.europa.eu/data/datasets/IRS/IRS.M.FR.L.L40.CI.0000.EUR.N.Z','BCE, IRS.M.FR.L.L40.CI.0000.EUR.N.Z')} (taux long terme de convergence France). Récupéré le ${dfr(R.ecb.slice(0,10))}.</div></div>
  </div>`;
  // courbe indices rebasés
  const start=I.spx.perf[25]?I.spx.perf[25].from:I.spx.dates[0];
  const reb=k=>{const x=I[k];const i0=x.dates.findIndex(d=>d>=start);const b=x.close[i0];return x.dates.slice(i0).map((d,i)=>[d,+(x.close[i0+i]/b*100).toFixed(2)]);};
  const mg=merge(keys.map(reb));const cols=['#e6c27a','#a9cdf5','#7fd1a8'];
  let ci=lineChart('cIdx',mg.labels.map(dshort),keys.map((k,i)=>({label:I[k].name,data:mg.data[i],borderColor:cols[i]})),{log:true,dec:1,unit:' (base 100)'});
  document.querySelectorAll('#idxScale button').forEach(b=>b.onclick=()=>{document.querySelectorAll('#idxScale button').forEach(x=>x.classList.toggle('on',x===b));const lg=b.dataset.l==='1';ci.options.scales.y.type=lg?'logarithmic':'linear';ci.options.scales.y.ticks.callback=lg?(v=>{const l=Math.log10(v);return Math.abs(l-Math.round(l))<1e-9?v.toLocaleString('fr-FR'):'';}):(v=>v.toLocaleString('fr-FR'));ci.update();});
  const showT=k=>{document.getElementById('techK').innerHTML=techKpis(I[k].tech);techDraw('cTI',I[k].tech,I[k].name.split(' (')[0]);};
  document.querySelectorAll('#techSel button').forEach(b=>b.onclick=()=>{document.querySelectorAll('#techSel button').forEach(x=>x.classList.toggle('on',x===b));showT(b.dataset.k);});
  showT('cac');
  lineChart('cCape',C.series.map(x=>x[0].slice(0,7)),[{label:'CAPE',data:C.series.map(x=>x[1]),borderColor:'#e6c27a'},{label:'Moyenne historique',data:C.series.map(()=>C.mean),borderColor:'rgba(255,255,255,.4)',borderDash:[5,4],borderWidth:1}],{dec:2,ticks:12});
  lineChart('cVix',V.weekly.map(x=>dshort(x[0])),[{label:'VIX',data:V.weekly.map(x=>x[1]),borderColor:'#e88f8f',borderWidth:1.2}],{dec:2,ticks:8});
  const t=merge([TX.us_m,TX.oat_m]);
  lineChart('cT10',t.labels.map(mfr),[{label:'US 10 ans',data:t.data[0],borderColor:'#a9cdf5'},{label:'OAT 10 ans',data:t.data[1],borderColor:'#e6c27a'}],{unit:' %',ticks:8,y:{ticks:{callback:v=>v+' %'}}});
  if(typeof renderSecteurs==='function') renderSecteurs(el);
  if(typeof renderPays==='function') renderPays(el);
}

/* ================= CRYPTO · fiches APEX BTC / ETH / SOL / MSTR (XRP retiré, t482u) ================= */
function cxIsXrp(s){
  if(!s) return false;
  if(String(s.key||'').toLowerCase()==='xrp') return true;
  const blob=[s.sym,s.tv,s.yahoo,s.ticker,s.nom].map(x=>String(x||'').toUpperCase());
  return blob.some(v=>v==='XRP'||v==='XRP-USD'||v==='XRPUSD'||v==='CRYPTO:XRPUSD'||v.endsWith(':XRPUSD'));
}
function cxApexAssets(list){
  return (list||[]).filter(s=>!cxIsXrp(s));
}
function cxLiqTitle(s){
  const L=s&&s.liquidite;
  if(!L) return '';
  const a=L.above_usd, b=L.below_usd;
  if(a==null && b==null) return '';
  let dir='';
  if(a!=null && b!=null){
    if(a>b) dir=' → achat';
    else if(b>a) dir=' → vente';
    else dir=' → neutre';
  }
  return 'Liquidité : '+cxUsd(a)+' au-dessus / '+cxUsd(b)+' en dessous'+dir;
}

function cxPx(s){
  const d=s.close>=1000?0:s.close<2?4:2;
  return fmt(s.close,d)+' '+(s.unit||'$');
}
function cxF(x){return fmt(x,x>=1000?0:x<1?4:2);}
function cxRepTile(s,i,pack){   // 17/11/2026 : repère de marché (non achetable au comptant chez Revolut) : ni note APEX, ni sentiment, ni signal
  const I=s.ind||{},fib=s.fibo||{};
  return `<div class="sec sec-rep">
   <div class="sr">
    <div class="sr-c sec-h sr-n"><b>${s.nom}</b><span>${s.sym} · ${s.sous}</span></div>
    <div class="sr-c sr-d"><span class="rep-badge" style="display:inline-block;border:1px solid #888;border-radius:10px;padding:2px 10px;font-size:12px;color:#ccc">Repère de marché</span> <span style="font-size:12px;color:#999">sans note APEX ni signal achat / vente</span></div>
    <div class="sr-c sr-b"></div>
   </div>
   <details class="ind-meth sec-det" data-cx="${i}" data-pack="${pack||'energie'}"><summary>Lecture de marché</summary>
     <p class="sr-close">Clôture hebdomadaire du ${dshort(s.date)} : <b>${cxPx(s)}</b> (${s.sym} · ${s.sous}) · bougie clôturée.</p>
     <p>${s.repere_texte || "Contrat à terme : il n'est pas achetable au comptant chez Revolut (pas de CFD dans APEX, ni d'ETF adossé à des contrats à terme). Il est affiché uniquement comme repère de marché, sans note ni drapeau."}</p>
     <p>RSI 14 hebdo : <b>${I.rsi==null?'n.d.':fmt(I.rsi,1)}</b> (${I.rsi_zone||'n.d.'}) · MACD : ${I.macd_texte||'n.d.'} · CCI 20 : ${I.cci==null?'n.d.':sign(I.cci,1)} (${I.cci_zone||'n.d.'}) · ${fib.ok?'Fibonacci base → ATH : '+fmt(fib.r*100,1)+' %':'Fibonacci n.d.'} · distance au record : ${s.ath&&s.ath.dd!=null?sign(s.ath.dd,1)+' %':'n.d.'}.</p>
     <p>Source : ${lnk(s.url,s.src_name)}. Données récupérées le ${(s.retrieved||'').replace(' ',' à ')} (heure de Paris).</p>
   </details>
  </div>`;
}

function cxUsd(x){
  if(x==null||x==='') return 'n.c.';
  const n=Number(x);
  if(Math.abs(n)>=1e9){
    const v=n/1e9;
    return (v>=10?v.toFixed(0):String(Math.round(v*100)/100)).replace('.',',')+' Md$';
  }
  const v=n/1e6;
  const r=Math.round(v*10)/10;
  const s=Number.isInteger(r)?String(r):r.toFixed(1);
  return s.replace('.',',')+' M$';
}
function cxLiqBands(arr, extra){
  if(!arr||!arr.length) return '';
  return arr.map(b=>{
    const amt=b.usd==null?'montant n.c.':(cxUsd(b.usd)+(b.est?' est.':''));
    return (b.label||'')+(b.label? ' · ':'')+amt;
  }).join(' ; ')+(extra||'');
}
function cxLiqLine(s){
  const L=s.liquidite;
  if(!L) return '';
  const a=L.above_usd, b=L.below_usd;
  if(a==null && b==null) return '';
  let dir='';
  if(a!=null && b!=null){
    if(a>b) dir=' → achat';
    else if(b>a) dir=' → vente';
    else dir=' → neutre';
  }
  return `<div class="cx-liq-line">Liquidité : ${cxUsd(a)} au-dessus / ${cxUsd(b)} en dessous${dir}</div>`;
}
function cxLiqBox(s){
  const L=s.liquidite;
  if(!L) return '';
  const sc=L.score, col=sc==null?'#888':(typeof gcol==='function'?gcol(sc):'#e6c27a');
  const est=t=>t?' (dont estimations)':'';
  let head='';
  if(sc!=null){
    head=`<div class="cx-liq-h">Liquidité accumulée non liquidée · score <b style="color:${col}">${String(sc).replace('.',',')}/100</b>
      · au-dessus <b>${cxUsd(L.above_usd)}${est(L.above_est)}</b>
      · en dessous <b>${cxUsd(L.below_usd)}${est(L.below_est)}</b>
      · plus au-dessus = achat, plus en dessous = vente</div>`;
  }else{
    head=`<div class="cx-liq-h">Liquidité accumulée non liquidée · <b>pas de score</b>${L.comment? ' · '+L.comment:''}</div>`;
  }
  const rows=[];
  const order=[['1y','Carte 1 an'],['1m','Carte 1 mois']];
  for(const [hid,lab] of order){
    const h=L.horizons&&L.horizons[hid];
    if(!h) continue;
    const used=h.used?'retenue dans le score':'non retenue dans le score';
    const sides=h.sides||{};
    const atm=(sides.atm||[]).concat(sides.consumed||[]);
    const parts=[];
    if(h.score!=null) parts.push('score '+String(h.score).replace('.',',')+'/100');
    parts.push('au-dessus '+cxUsd(h.above_usd)+(h.above_est?' est.':''));
    parts.push('en dessous '+cxUsd(h.below_usd)+(h.below_est?' est.':''));
    if(h.capture_price!=null) parts.push('prix de capture '+cxPx({close:h.capture_price,unit:'$'}));
    let detail='';
    if((sides.above||[]).length) detail+=' Au-dessus : '+cxLiqBands(sides.above)+'.';
    if((sides.below||[]).length) detail+=' En dessous : '+cxLiqBands(sides.below)+'.';
    if(atm.length) detail+=' Au prix / déjà traversée (exclue du solde) : '+cxLiqBands(atm)+'.';
    if(h.ignored_why) detail+=' '+h.ignored_why;
    else if(h.capture_note) detail+=' '+h.capture_note;
    rows.push(`<div class="cx-liq-hzn"><span class="l">${lab}</span> <span class="s">${used} · ${parts.join(' · ')}</span><div class="d">${detail}</div></div>`);
  }
  const src=L.source?`<div class="cx-liq-src">${L.source}${L.comment&&sc!=null?' '+L.comment:''}</div>`:'';
  return `<div class="cx-liq">${head}${rows.join('')}${src}</div>`;
}

function cxTile(s,i,pack,rank){
  if(s.repere) return cxRepTile(s,i,pack);
  if(!s.ok){
    return `<div class="sec">
     <div class="sr">
      <div class="sr-c sec-h sr-n"><b>${s.nom}</b><span>${s.sym} · ${s.sous||''}</span></div>
      <div class="sr-c sr-d"><div class="apex10 apex10-na"><b>–</b></div></div>
      <div class="sr-c sr-b"></div>
     </div>
    </div>`;
  }
  const I=s.ind||{},div=I.div||{},fib=s.fibo||{},ell=s.elliott_comment||{};
  const rsiV=I.rsi==null?'n.d.':fmt(I.rsi,1);
  const cciV=I.cci==null?'n.d.':sign(I.cci,1);
  const fibV=fib.ok?fmt(fib.r*100,1)+' %':'n.d.';
  const fibS=fib.ok?(fib.zone||'')+' · base → ATH sur les corps':'position indisponible';
  const athV=s.ath&&s.ath.dd!=null?`<span class="${cls(s.ath.dd)}">${sign(s.ath.dd,1)} %</span>`:'n.d.';
  const athS=s.ath?`record ${fmt(s.ath.close,s.ath.close>=1000?0:2)} $ le ${dshort(s.ath.date)} · pas d'entrée à l'ATH`:'record indisponible';
  const ellV=ell.entry?'Fin de 2 / 4 ou vague C':'Hors zone d\'entrée';
  const ellS=s.elliott?(s.elliott.texte||'lecture automatique')+' · à confirmer sur TradingView':'indisponible';
  const divS=div.texte||'divergence indisponible';
  const chC=(s.av&&s.av.components||[]).find(c=>c.nom&&c.nom.startsWith('Charte graphique'))||null,dvC=(s.av&&s.av.components||[]).find(c=>c.nom==='Divergence RSI weekly')||null;
  const chV=chC&&chC.note!=null?`<span style="color:${avCol(chC.note)}">${sign(chC.note,0)}</span>`:'n.d.';
  const chS=chC?((chC.charte&&chC.charte.source==='manuel')?'lecture manuelle · ':'')+'poids '+pw(chC.poids)+' % de la note APEX':'indisponible';
  const rk=(rank!=null&&rank!=='')?`<span class="fl-rk">${rank}</span>`:'';
  const tick=s.sym?`<span class="tvs"><code>${s.sym}</code>${(s.tv&&typeof ophirCopyBtn==='function')?ophirCopyBtn(s.tv):''}</span>`:'';
  const liqTip=cxLiqTitle(s);
  const bar=(typeof listApexBar==='function')?listApexBar(Object.assign({},s,{forceApex250:true})):((typeof dualBarPilot==='function'&&s.apex10)?dualBarPilot({total:s.apex10.total!=null?s.apex10.total:s.apex10.note,total_min:-50,total_max:250,ligne:s.apex10.ligne||'',hex:s.apex10.hex,band:s.apex10.band},true):'');
  return `<div class="sec"${s.tv?` data-pos-tv="${s.tv}"`:''}${liqTip?` title="${liqTip.replace(/"/g,'&quot;')}"`:''}>
   <div class="sr">
    <div class="sr-c sec-h sr-n sr-n-titre">${rk}<span class="sr-titre"><b>${s.nom}</b></span>${tick}${typeof posBadges==='function'?posBadges(s.tv||s.sym):''}${typeof dispoBadge==='function'?dispoBadge(s.tv):''}</div>
    <div class="sr-c sr-d">${bar}</div>
    <div class="sr-c sr-b"></div>
   </div>
   <details class="ind-meth sec-det" data-cx="${i}" data-pack="${pack||'crypto'}"><summary>Détail et historique 1 an</summary>
     <p class="sr-close">Clôture hebdomadaire du ${dshort(s.date)} : <b>${cxPx(s)}</b> (${s.sym} · ${s.sous}) · bougie clôturée${s.live?` ; semaine en cours au ${dshort(s.live.date)} : ${fmt(s.live.close,s.live.close>=1000?0:2)} ${s.unit||'$'}, non utilisée`:''}.</p>
     ${s.warn&&s.warn.length?s.warn.map(w=>`<div class="note">${w}</div>`).join(''):''}
     ${s.liquidite?cxLiqBox(s):''}
     <div class="cx-inds">
    <div class="cx-ind"><div class="l">RSI 14 hebdo</div><div class="v">${rsiV}</div><div class="s">${I.rsi_zone||'n.d.'} · ${div.type&&div.type!=='aucune'&&div.type!=='indisponible'?'divergence '+div.type:div.type==='indisponible'?'divergence n.d.':'pas de divergence récente'}</div></div>
    <div class="cx-ind"><div class="l">MACD 12/26/9</div><div class="v">${I.macd==null?'n.d.':fmt(I.macd,2)}</div><div class="s">${I.macd_texte||'n.d.'}</div></div>
    <div class="cx-ind"><div class="l">CCI 20 (corps)</div><div class="v">${cciV}</div><div class="s">${I.cci_zone||'n.d.'}</div></div>
    <div class="cx-ind"><div class="l">Fibonacci base → ATH</div><div class="v">${fibV}</div><div class="s">${fibS}</div></div>
    <div class="cx-ind"><div class="l">Distance à l'ATH</div><div class="v">${athV}</div><div class="s">${athS}</div></div>
    <div class="cx-ind"><div class="l">Vague d'Elliott</div><div class="v">${s.elliott&&s.elliott.phase?s.elliott.phase+' · '+ellV:'n.d.'}</div><div class="s">${ellS}</div></div>
    <div class="cx-ind"><div class="l">Charte graphique</div><div class="v">${chV}</div><div class="s">${chS}</div></div>
    <div class="cx-ind"><div class="l">Divergence RSI weekly</div><div class="v">${dvC&&dvC.note!=null?`<span style="color:${avCol(dvC.note)}">${sign(dvC.note,0)}</span>`:'non comptée'}</div><div class="s">${dvC&&dvC.note!=null?(dvC.note<0?'baissière':'haussière')+' · poids '+pw(dvC.poids)+' %':'aucune divergence récente · poids redistribué'}</div></div>
     </div>
     <p class="cx-div">${divS}</p>
     ${s.fng?`<p>Fear &amp; Greed (contexte, hors note) au ${dshort(s.fng.date)} : <b>${s.fng.value}</b> · ${s.fng.label}.</p>`:''}
     <div class="ind-subt" style="margin-top:8px">Sentiment, 52 semaines (moy. ${fmt(s.sent.avg,0)} · min ${fmt(s.sent.min[1],0)} le ${dshort(s.sent.min[0])} · max ${fmt(s.sent.max[1],0)} le ${dshort(s.sent.max[0])})</div>
     <div class="ind-spark" style="height:90px"><canvas id="cCxS${i}"></canvas></div>
     <p class="sent-mir">Couleurs du sentiment en dégradé miroir, lecture contrarienne : peur = bleu (zone d'achat), euphorie = rouge (zone de vente).</p>
     <div class="ind-subt">Achat / Vente, 52 semaines (moy. ${sign(s.av.avg,0)} · min ${sign(s.av.min[1],0)} · max ${sign(s.av.max[1],0)})</div>
     <div class="ind-spark" style="height:90px"><canvas id="cCxA${i}"></canvas></div>
     <div class="ind-sub"><div class="ind-subt">Composantes du sentiment (0-100)</div>${s.sent.components.map(c=>`<div class="ind-sb"><div class="ind-sbl"><span>${c.name}</span><b class="sc-t" style="color:${c.value==null?'#888':gmir(c.value)}">${c.value==null?'n.d.':fmt(c.value,0)}</b></div><div class="ind-sbt">${c.value==null?'':`<i style="width:${Math.max(0,Math.min(100,c.value))}%;background:${gmir(c.value)}"></i>`}</div><div class="ind-sbd">poids ${fmt(c.weight*100,1)} % · ${c.raw}</div></div>`).join('')}</div>
     <div class="ind-sub"><div class="ind-subt">Composantes Achat / Vente (−100 à +100)</div>${(s.av&&s.av.components||[]).map(c=>{const n=c.note;return `<div class="av-c"><div class="av-cl"><span>${c.nom}</span><b style="color:${n==null?'#888':avCol(n)}">${n==null?(c.facultatif?'non comptée':'n.d.'):sign(n,0)}</b></div><div class="av-cb"><div class="av-mid"></div>${n==null?'':`<i style="${n>=0?'left:50%':'right:50%'};width:${Math.abs(n)/2}%;background:${avCol(n)}"></i>`}</div><div class="av-cd">valeur ${c.valeur} · poids ${pw(c.poids)} % · contribution <b>${c.contrib==null?(c.facultatif?'non comptée':'retirée'):sign(c.contrib,1)}</b> · règle : ${c.regle}</div></div>`;}).join('')}</div>
     <p>${fib.ok?`Retracement de Fibonacci (corps) : cours à ${fmt(fib.r*100,1)} % (${fib.zone}) · base ${cxF(fib.base)} $ le ${fib.base_date?dshort(fib.base_date):'n.d.'} → ATH ${cxF(fib.ath)} $ le ${fib.ath_date?dshort(fib.ath_date):'n.d.'}${fib.debut?' · historique depuis '+dshort(fib.debut):''}${fib.base_apres_ath?" · le plus bas historique est postérieur à l'ATH":''}.`:'Retracement de Fibonacci indisponible'+(fib.texte? ' : '+fib.texte:'')+' .'}</p>
     <p>Plus haut des clôtures hebdomadaires de la série : ${s.ath?fmt(s.ath.close,s.ath.close>=1000?0:2)+' $ le '+dshort(s.ath.date)+', soit '+sign(s.ath.dd,1)+' %':'n.d.'}. Distance au plus haut 52 semaines : ${s.dd52!=null?sign(s.dd52,1)+' %':'n.d.'}.</p>
     <p class="cx-ell">${ell.texte||''}</p>
     ${chC?`<p class="cx-ch"><b>Charte graphique (${pw(chC.poids)} %) : ${chC.note==null?'n.d.':sign(chC.note,0)}.</b> ${chC.valeur}</p><p class="mut">Règle : ${chC.regle}</p>`:''}
     <p>Source : ${lnk(s.url,s.src_name)}. Données récupérées le ${(s.retrieved||'').replace(' ',' à ')} (heure de Paris). La semaine en cours n'est pas utilisée.</p>
   </details>
  </div>`;
}
function fichePack(name){
  if(name==='energie') return T2.energie;
  if(name==='fx') return T2.liquidites&&T2.liquidites.fx;
  return T2.crypto&&T2.crypto.fiches;
}
function cxCharts(det){
  if(det.dataset.done)return;det.dataset.done='1';
  const F=fichePack(det.dataset.pack),s=F&&F.assets[+det.dataset.cx],i=det.dataset.cx;
  if(!s||!s.ok||s.repere)return;
  const x={ticks:{maxTicksLimit:3,maxRotation:0,autoSkip:true,font:{size:9}},grid:{display:false}};
  const ml=d=>new Date(d).toLocaleDateString('fr-FR',{month:'short',year:'2-digit'});
  const ss=s.sent.series,ah=s.av.history;
  charts.push(new Chart(document.getElementById('cCxS'+i),{type:'line',data:{labels:ss.map(p=>ml(p[0])),datasets:[{data:ss.map(p=>p[1]),borderColor:'rgba(255,255,255,.55)',borderWidth:1.2,pointRadius:2,pointBackgroundColor:ss.map(p=>gmir(p[1])),pointBorderWidth:0,tension:.25}]},
    options:{maintainAspectRatio:false,animation:false,plugins:{legend:{display:false},tooltip:{callbacks:{title:c=>dshort(ss[c[0].dataIndex][0])}}},scales:{x,y:{min:0,max:100,ticks:{stepSize:50,font:{size:9}}}}}}));
  charts.push(new Chart(document.getElementById('cCxA'+i),{type:'bar',data:{labels:ah.map(p=>ml(p[0])),datasets:[{data:ah.map(p=>p[1]),backgroundColor:ah.map(p=>avCol(p[1])),borderWidth:0,barPercentage:1,categoryPercentage:.9}]},
    options:{maintainAspectRatio:false,animation:false,plugins:{legend:{display:false},tooltip:{callbacks:{title:c=>dshort(ah[c[0].dataIndex][0])}}},scales:{x,y:{min:-100,max:100,ticks:{stepSize:100,font:{size:9}}}}}}));
}
function cxFichesHTML(){
  const F=T2.crypto&&T2.crypto.fiches;
  if(!F||!F.assets||!F.assets.length) return '';
  const all=F.assets;
  const S=cxApexAssets(all);
  const ok=S.filter(s=>s.ok),d=ok[0]&&ok[0].date;
  const cnt=z=>ok.filter(s=>s.av&&s.av.label&&s.av.label.includes(z)).length;
  const ordered=apexSortByNote(S);
  return `<div class="card no-group no-acc" id="cxFiches"><h2>BTC, ETH, SOL et MSTR · notes APEX</h2>
   <div class="desc acc-sum">Bitcoin, Ether, Solana et Strategy (action NASDAQ, proxy bitcoin) · ${d?('clôtures hebdomadaires au '+dshort(d)):'dates indisponibles'} · <i>Achat</i> <b>${cnt('Achat')}</b> · <i>Neutre</i> <b>${cnt('Neutre')}</b> · <i>Vente</i> <b>${cnt('Vente')}</b></div>
   <div class="sec-grid">${typeof srHead==='function'?srHead('Actif'):''}${ordered.map((s,k)=>cxTile(s,all.indexOf(s),'crypto',k+1)).join('')}</div>
   <details class="ind-meth"><summary>Méthode et pondérations</summary>
     <p><b>Sentiment Peur / Euphorie (0-100).</b> ${apexPlain(F.method_sent)}</p>
     <p><b>Achat / Vente (−100 à +100).</b> ${apexPlain(F.method_av)}</p>
     <p>Le S&amp;P 500 sert de référence pour la force relative, comme sur l'onglet Actions. MSTR n'est pas du bitcoin au comptant. Calcul reproductible avec <code>src/build_crypto_fiches.py</code>.</p>
     <p><b>Note APEX /100 et liquidité.</b> Pour les cryptoactifs, la part fondamentale (50 %) est remplacée par un score de liquidité 0–100, lu sur les cartes CoinAnk de liquidités accumulées non encore liquidées : plus au-dessus du prix = achat, plus en dessous = vente. La carte 1 an pèse 70 %, la carte 1 mois 30 %. Les plafonds et bonus Elliott restent les mêmes. MSTR, et tout actif sans carte saisie (ex. SOL tant qu'une capture n'est pas fournie), restent notés sur le timing seul. Source et formule : <code>ressources/criteres_apex_2026-11-18.md</code> § g et <code>src/liquidite_crypto.py</code>.</p>
   </details>
   <div class="src">Sources : ${lnk('https://www.binance.com/fr/trade/BTC_USDT','Binance (BTC/USDT et ETH/USDT, klines 1w)')} · ${lnk('https://finance.yahoo.com/quote/XRP-USD/history/','Yahoo Finance (XRP-USD, SOL-USD, MSTR et S&P 500)')} · ${lnk('https://coinmetrics.io/community-network-data/','CoinMetrics')} (préfixe de l'historique Fibonacci BTC, ETH et XRP) · ${lnk('https://alternative.me/crypto/fear-and-greed-index/','alternative.me')} (Fear &amp; Greed, contexte) · ${lnk('https://coinank.com/liqHeatMap','CoinAnk Liquidation Heatmap')} (liquidité accumulée, saisie manuelle des captures d'Emmanuel, 23/11/2026). Récupéré le ${(F.retrieved&&F.retrieved.binance_btc||'').replace(' ',' à ')} (heure de Paris).</div></div>`;
}

/* ================= CRYPTO ================= */
function renderCrypto(el){

  const C=T2.crypto,R=C.retrieved,G=C.global,F=C.fng,BT=C.btc_tech;
  const ck=(a,n)=>{const x=C[a];return kpi(n,fmt(x.last.value,x.last.value>1000?0:2)+' $','clôture journalière du '+dshort(x.last.date))+kpi(n+' · 1 an / 5 ans',pctTxt(x.perf[1])+' / '+pctTxt(x.perf[5]),'10 ans : '+(x.perf[10]?sign(x.perf[10].pct,0)+' %':'n.d.'))+kpi(n+' · écart au record',`<span class="${cls(x.peak.dd)}">${sign(x.peak.dd)} %</span>`,'record '+fmt(x.peak.value,0)+' $ le '+dshort(x.peak.date));};
  const fz=v=>v<25?'#e88f8f':v<45?'#e6a87a':v<=55?'#bababa':v<=75?'#a6d98f':'#7fd1a8';
  el.innerHTML=cxFichesHTML()+`
  <div class="card"><h2>Bitcoin et Ether · historique complet</h2>
   <div class="desc">Prix de référence en USD, dernier cours de chaque semaine : BTC depuis le ${dshort(C.btc.first)}, ETH depuis le ${dshort(C.eth.first)}. Échelle logarithmique.</div>
   <div class="kpis">${ck('btc','BTC')}</div><div class="kpis">${ck('eth','ETH')}</div>
   <div class="chart" style="height:340px"><canvas id="cCx"></canvas></div>
   <div class="note">Le prix de référence CoinMetrics est un indice multi-plateformes, écart de quelques dixièmes de pourcent possible par rapport au cours Binance.</div>
   <div class="src">Source : ${lnk('https://coinmetrics.io/community-network-data/','CoinMetrics Community API')} (PriceUSD, quotidien), récupéré le ${dfr(R.coinmetrics.slice(0,10))} à ${R.coinmetrics.slice(11)}.</div></div>

  <div class="grid2">
   <div class="card"><h2>Marché crypto · capitalisation et dominance</h2>
    <div class="desc">Instantané de l'ensemble du marché suivi par CoinGecko.</div>
    <div class="kpis">${kpi('Capitalisation totale',big(G.total_cap_usd),'<span class="'+cls(G.chg24h)+'">'+sign(G.chg24h,2)+' %</span> sur 24 h')+kpi('Dominance BTC',fmt(G.btc_dom,1)+' %','ETH : '+fmt(G.eth_dom,1)+' %')}${na('Historique de la dominance','l\'API gratuite CoinGecko ne fournit que la valeur instantanée')}</div>
    <div class="chart" style="height:240px"><canvas id="cDom"></canvas></div>
    <div class="src">Source : ${lnk('https://www.coingecko.com/fr/capitalisation-mondiale-des-cryptomonnaies','CoinGecko /global')}, mise à jour CoinGecko ${G.updated.replace(' UTC','')} UTC, récupéré le ${dfr(R.coingecko.slice(0,10))}. Capitalisation BTC selon CoinMetrics : ${C.btc.cap_last?big(C.btc.cap_last[1])+' ('+dshort(C.btc.cap_last[0])+')':'n.d.'}.</div></div>
   <div class="card"><h2>Fear & Greed Index</h2>
    <div class="desc">Sentiment du marché crypto, de 0 (peur extrême) à 100 (avidité extrême), quotidien depuis le ${dshort(F.first)}.</div>
    <div class="kpis">${kpi('Aujourd\'hui',`<span style="color:${fz(F.last[1])}">${F.last[1]}</span>`,F.last[2]+' · '+dshort(F.last[0]))+kpi('Moyenne 30 j / 365 j',fmt(F.avg30,0)+' / '+fmt(F.avg365,0),F.days_extreme_fear_30+' jours de peur extrême sur 30')}</div>
    <div class="gauge" style="margin-bottom:12px"><div style="width:${F.last[1]}%;background:${fz(F.last[1])};color:#000">${F.last[1]}</div><div style="width:${100-F.last[1]}%;background:rgba(255,255,255,.06)"></div></div>
    <div class="chart" style="height:200px"><canvas id="cFng"></canvas></div>
    <div class="src">Source : ${lnk('https://alternative.me/crypto/fear-and-greed-index/','alternative.me')} (API /fng), récupéré le ${dfr(R.alt.slice(0,10))} à ${R.alt.slice(11)}.</div></div>
  </div>

  <div class="card"><h2>BTC · analyse technique hebdomadaire</h2>
   <div class="desc">BTC/USDT Binance, bougies hebdomadaires clôturées (lundi → dimanche UTC) depuis le ${dshort(BT.first)} ; RSI 14 Wilder et MACD 12/26/9.</div>
   <div class="kpis">${techKpis(BT)}${BT.current?kpi('Semaine en cours (non clôturée)',fmt(BT.current.close,0)+' $','ouverte le '+dshort(BT.current.open_date)+' · exclue du calcul'):''}</div>
   ${techHTML('cTB')}
   <div class="note">L'historique Binance commence en août 2017 : le RSI et le MACD démarrent donc à cette date, et non avec l'historique complet du BTC.</div>
   <div class="src">Source : ${lnk('https://www.binance.com/fr/trade/BTC_USDT','Binance API /klines BTCUSDT 1w')}, récupéré le ${dfr(R.binance.slice(0,10))} à ${R.binance.slice(11)} · calcul APEX.</div></div>

  <div class="card"><h2>Heatmap de liquidation · CoinAnk</h2>
   <div class="desc">C'est ton filtre d'entrée et de sortie sur le BTC. Les données ne sont pas intégrées ici : ouvre la page directement.</div>
   <div class="toggle"><a class="btnlink" href="https://coinank.com/liqHeatMapChart" target="_blank" rel="noopener">Ouvrir la heatmap BTC CoinAnk ↗</a></div>
   <div class="note">Les heatmaps sont des estimations issues d'un modèle (levier supposé, open interest) : une zone qui disparaît n'a pas forcément été liquidée.</div>
   <div class="src">Lien externe : ${lnk('https://coinank.com/liqHeatMapChart','coinank.com')}.</div></div>`;
  const b=C.btc.weekly,e=C.eth.weekly,mg=merge([b,e]);
  lineChart('cCx',mg.labels.map(dshort),[{label:'BTC (USD)',data:mg.data[0],borderColor:'#e6c27a'},{label:'ETH (USD)',data:mg.data[1],borderColor:'#a9cdf5'}],{log:true,dec:2,unit:' $',ticks:10});
  const top=G.top,other=Math.max(0,100-top.reduce((s,x)=>s+x[1],0));
  charts.push(new Chart(document.getElementById('cDom'),{type:'doughnut',data:{labels:[...top.map(x=>x[0].toUpperCase()),'Autres'],datasets:[{data:[...top.map(x=>x[1]),+other.toFixed(2)],backgroundColor:['#e6c27a','#a9cdf5','#7fd1a8','#e88f8f','#c9a0dc','#8fb3c9','#d9c08f','#9fc99f','#555'],borderColor:'#1a1a1a'}]},options:{maintainAspectRatio:false,animation:false,plugins:{legend:{position:'right'},tooltip:{callbacks:{label:c=>' '+c.label+' : '+fmt(c.parsed,2)+' %'}}}}}));
  const f=F.series.slice(-365);
  lineChart('cFng',f.map(x=>dshort(x[0])),[{label:'Fear & Greed',data:f.map(x=>x[1]),borderColor:'#e6c27a',borderWidth:1.4}],{dec:0,ticks:6,y:{min:0,max:100}});
  techDraw('cTB',BT,'BTC/USDT');
  const cx=el.querySelector('#cxFiches');
  if(cx){if(typeof srWire==='function')srWire(cx);cx.querySelectorAll('.sec-det').forEach(dt=>dt.addEventListener('toggle',()=>{if(dt.open)cxCharts(dt);}));}
}

/* ================= ÉNERGIE ================= */

function enTile(s,i){
  if(s.repere) return cxRepTile(s,i,'energie');
  if(!s.ok){
    return `<div class="sec">
     <div class="sr">
      <div class="sr-c sec-h sr-n"><b>${s.nom}</b><span>${s.sym} · ${s.sous||''}</span></div>
      <div class="sr-c sr-d"><div class="note">${s.raison||'Données indisponibles.'}</div></div>
      <div class="sr-c sr-b"></div>
     </div>
    </div>`;
  }
  // Fiche compacte façon Actions / Secteurs : barre APEX visible, indicateurs dans le détail.
  return cxTile(s,i,'energie');
}
function enFichesHTML(){
  const F=T2.energie;
  if(!F||!F.assets||!F.assets.length) return '';
  const S=F.assets,ok=S.filter(s=>s.ok);
  const dates=[...new Set(ok.map(s=>s.date).filter(Boolean))].sort();
  const d=dates.length===1?dates[0]:null;
  const dSpan=dates.length<=1?'':(dshort(dates[0])+' au '+dshort(dates[dates.length-1]));
  const cnt=z=>ok.filter(s=>s.av&&s.av.label&&s.av.label.includes(z)).length,nRep=S.filter(s=>s.repere).length;
  const nAth=ok.filter(s=>s.warn&&s.warn.length).length;
  const nNa=S.filter(s=>!s.ok).length;
  const groupes=F.groupes||[...new Set(S.map(s=>s.groupe).filter(Boolean))];
  let grid='';
  groupes.forEach(g=>{
    const items=apexSortByNote(S.filter(s=>s.groupe===g)).map(s=>({s,i:S.indexOf(s)}));
    if(!items.length) return;
    grid+=`<div class="en-gh">${g}</div>`+items.map(x=>enTile(x.s,x.i)).join('');
  });
  const orphelins=apexSortByNote(S.filter(s=>!groupes.includes(s.groupe)));
  if(orphelins.length) grid+=orphelins.map(s=>enTile(s,S.indexOf(s))).join('');
  const ret=F.retrieved||{};
  const retD=ret['CL=F']||ret['XDW0.DE']||F.generated||'';
  const a10=F.apex10||((typeof sectionApexAvg==='function'&&(sectionApexAvg('energie')||{}).apex10)||null);
  const apexTag=a10&&a10.display?`<span class="js-apex10" hidden data-display="${a10.display}" data-hex="${a10.hex||''}" data-note="${a10.note}"></span>`:'';
  const apexVis=a10&&a10.display?` · moyenne <b>${a10.display}/100</b>`:'';
  return `<div class="card no-group no-acc" id="enFiches">${apexTag}<h2>Énergie · notes APEX</h2>
   <div class="desc acc-sum">${groupes.length} sous-sections${apexVis} · ${d?('clôtures hebdomadaires au '+dshort(d)):(dSpan?('clôtures hebdomadaires du '+dSpan+' selon la fiche'):'dates selon la fiche')} · <i>Achat</i> <b>${cnt('Achat')}</b> · <i>Neutre</i> <b>${cnt('Neutre')}</b> · <i>Vente</i> <b>${cnt('Vente')}</b>${nAth?` · <i>⚠ près du record</i> <b>${nAth}</b>`:''}${nNa?` · <i>indisponible</i> <b>${nNa}</b>`:''}${nRep?` · <i>repères de marché</i> <b>${nRep}</b>`:''}${F.av&&F.av.score!=null?` · signal XDW0 <b>${sign(F.av.score,0)} ${F.av.label||''}</b>`:''}</div>
   <div class="sec-grid">${typeof srHead==='function'?srHead('Actif'):''}${grid}</div>
   <details class="ind-meth"><summary>Méthode et pondérations</summary>
     <p><b>Sentiment Peur / Euphorie (0-100).</b> ${apexPlain(F.method_sent)}</p>
     <p><b>Achat / Vente (−100 à +100).</b> ${apexPlain(F.method_av)}</p>
     <p>Le S&amp;P 500 sert de référence pour la force relative, comme sur l'onglet Actions. Chaque actif achetable au comptant (hors repères de marché) reçoit une note APEX /100, avec la même méthode et les mêmes règles Elliott (plafond zone rouge, bonus zone verte) que sur les autres onglets. Les listes sont triées par note. Le bandeau de l'onglet est la moyenne de ces notes, arrondie au point. Les ETF ou ETP adossés à des contrats à terme (UNG, USO, BNO, UGA, KRBN) ne sont pas notés. Le gaz est suivi par l'ETP BNQ9 (BNPP Natural Gas ETC, ISIN DE000PB6GAS5), affiché comme repère de marché sans note : il est adossé à des contrats à terme, avec un coût de roll en détention longue, et très volatil. Les contrats à terme (WTI, Brent, fioul, essence) restent des repères de marché sans note. Le charbon est suivi par l'action Peabody Energy (BTU), proxy clairement identifié. Calcul reproductible avec <code>src/build_energie.py</code> et <code>src/build_apex10.py</code>.</p>
   </details>
   <div class="src">Sources : ${lnk('https://finance.yahoo.com/','Yahoo Finance')} (actions et ETF UCITS au comptant ; ETP gaz BNQ9.DE et contrats à terme continus CL=F, BZ=F, HO=F, RB=F en repères ; S&amp;P 500 pour la force relative). Récupéré le ${(retD||'').replace(' ',' à ')} (heure de Paris).</div></div>`;
}
function renderEnergie(el){
  el.innerHTML = enFichesHTML() || '<div class="card"><h2>Énergie</h2><p>Données indisponibles pour le moment.</p></div>';
  const en=el.querySelector('#enFiches');
  if(en){
    en.querySelectorAll('.sec').forEach(sec=>{
      const inds=sec.querySelector(':scope>.cx-inds');
      const det=sec.querySelector(':scope>details.sec-det');
      if(inds&&det){
        const sum=det.querySelector(':scope>summary');
        det.insertBefore(inds, sum&&sum.nextSibling?sum.nextSibling:det.firstChild);
      }
    });
    if(typeof srWire==='function')srWire(en);
    en.querySelectorAll('.sec-det').forEach(dt=>dt.addEventListener('toggle',()=>{if(dt.open)cxCharts(dt);}));
  }
}

/* ================= LIQUIDITÉS · devises notées face à l'euro ================= */
const FX_FLAG={
  USD:['flag-us.png','États-Unis'],JPY:['flag-jp.png','Japon'],GBP:['flag-gb.png','Royaume-Uni'],
  CHF:['flag-ch.png','Suisse'],AUD:['flag-au.png','Australie'],CAD:['flag-ca.png','Canada'],KRW:['flag-kr.png','Corée du Sud']
};
function fxPx(s){
  const d=s.dec!=null?s.dec:(s.close<0.01?6:s.close<0.1?5:4);
  return fmt(s.close,d)+' €';
}
function fxF(x,dec){return fmt(x,dec!=null?dec:(x>=1?4:x>=0.01?5:6));}
function fxSort(assets){
  return (typeof apexSortByNote==='function')?apexSortByNote(assets):[...(assets||[])];
}
function fxSigHTML(av,apex){
  const a=apex||(av&&av.apex10)||null; /* t320u : pas de recalcul JS */
  if(a&&a.note!=null){
    const col=(typeof apex10Col==='function')?apex10Col(a):((typeof gcol==='function')?gcol(a.pos):'#e6c27a');
    return `<span class="home-sig apex10"><b style="color:${col}">${a.display}</b><small style="color:${col}">/100</small></span>`;
  }
  if(!av||av.score==null||av.score==='') return `<span class="home-sig"><b>–</b></span>`;
  const col=(typeof avCol==='function')?avCol(av.score):'#e6c27a';
  return `<span class="home-sig"><b style="color:${col}">${sign(av.score,0)}</b><em style="color:${col}">${av.label||''}</em></span>`;
}
function fxDetailHTML(s,i){
  if(!s||!s.ok||!s.av) return `<div class="note">${(s&&s.raison)||'Note indisponible.'}</div>`;
  const I=s.ind||{},div=I.div||{},fib=s.fibo||{},ell=s.elliott_comment||{};
  const dec=s.dec!=null?s.dec:4;
  const chC=(s.av&&s.av.components||[]).find(c=>c.nom&&c.nom.startsWith('Charte graphique'))||null;
  return `<div class="fx-det" data-cx="${i}" data-pack="fx">
     <div class="av-short">Note calculée face à l'euro (cours d'une unité de ${s.sym} en €).</div>
     <p class="sr-close">Clôture hebdomadaire du ${dshort(s.date)} : <b>${fxPx(s)}</b> pour 1 ${s.sym} (série ${s.sym}/EUR, inverse de ${s.tv||s.yahoo}) · bougie clôturée${s.live?` ; semaine en cours au ${dshort(s.live.date)} : ${fxF(s.live.close,dec)} €, non utilisée`:''}.</p>
     ${s.warn&&s.warn.length?s.warn.map(w=>`<div class="note">${w}</div>`).join(''):''}
     <p class="cx-div">${(div.texte)||''}</p>
     <div class="ind-subt" style="margin-top:8px">Sentiment, 52 semaines (moy. ${fmt(s.sent.avg,0)} · min ${fmt(s.sent.min[1],0)} le ${dshort(s.sent.min[0])} · max ${fmt(s.sent.max[1],0)} le ${dshort(s.sent.max[0])})</div>
     <div class="ind-spark" style="height:90px"><canvas id="cCxS${i}"></canvas></div>
     <p class="sent-mir">Couleurs du sentiment en dégradé miroir, lecture contrarienne : peur = bleu (zone d'achat), euphorie = rouge (zone de vente).</p>
     <div class="ind-subt">Achat / Vente, 52 semaines (moy. ${sign(s.av.avg,0)} · min ${sign(s.av.min[1],0)} · max ${sign(s.av.max[1],0)})</div>
     <div class="ind-spark" style="height:90px"><canvas id="cCxA${i}"></canvas></div>
     <div class="ind-sub"><div class="ind-subt">Composantes du sentiment (0-100)</div>${s.sent.components.map(c=>`<div class="ind-sb"><div class="ind-sbl"><span>${c.name}</span><b class="sc-t" style="color:${c.value==null?'#888':gmir(c.value)}">${c.value==null?'n.d.':fmt(c.value,0)}</b></div><div class="ind-sbt">${c.value==null?'':`<i style="width:${Math.max(0,Math.min(100,c.value))}%;background:${gmir(c.value)}"></i>`}</div><div class="ind-sbd">poids ${fmt(c.weight*100,1)} % · ${c.raw}</div></div>`).join('')}</div>
     <div class="ind-sub"><div class="ind-subt">Composantes Achat / Vente (−100 à +100)</div>${(s.av&&s.av.components||[]).map(c=>{const n=c.note;return `<div class="av-c"><div class="av-cl"><span>${c.nom}</span><b style="color:${n==null?'#888':avCol(n)}">${n==null?(c.facultatif?'non comptée':'n.d.'):sign(n,0)}</b></div><div class="av-cb"><div class="av-mid"></div>${n==null?'':`<i style="${n>=0?'left:50%':'right:50%'};width:${Math.abs(n)/2}%;background:${avCol(n)}"></i>`}</div><div class="av-cd">valeur ${c.valeur} · poids ${pw(c.poids)} % · contribution <b>${c.contrib==null?(c.facultatif?'non comptée':'retirée'):sign(c.contrib,1)}</b> · règle : ${c.regle}</div></div>`;}).join('')}</div>
     <p>${fib.ok?`Retracement de Fibonacci (corps) : cours à ${fmt(fib.r*100,1)} % (${fib.zone}) · base ${fxF(fib.base,dec)} € le ${fib.base_date?dshort(fib.base_date):'n.d.'} → ATH ${fxF(fib.ath,dec)} € le ${fib.ath_date?dshort(fib.ath_date):'n.d.'}${fib.debut?' · historique depuis '+dshort(fib.debut):''}${fib.base_apres_ath?" · le plus bas historique est postérieur à l'ATH":''}.`:'Retracement de Fibonacci indisponible.'}</p>
     <p>Plus haut des clôtures hebdomadaires de la série ${s.sym}/EUR : ${s.ath?fxF(s.ath.close,dec)+' € le '+dshort(s.ath.date)+', soit '+sign(s.ath.dd,1)+' %':'n.d.'}. Distance au plus haut 52 semaines : ${s.dd52!=null?sign(s.dd52,1)+' %':'n.d.'}.</p>
     <p class="cx-ell">${ell.texte||''}</p>
     ${chC?`<p class="cx-ch"><b>Charte graphique (${pw(chC.poids)} %) : ${chC.note==null?'n.d.':sign(chC.note,0)}.</b> ${chC.valeur}</p><p class="mut">Règle : ${chC.regle}</p>`:''}
     <p>Source : ${lnk(s.url,s.src_name)}. Force relative contre le panier équipondéré des 7 devises APEX. Données récupérées le ${(s.retrieved||'').replace(' ',' à ')} (heure de Paris). La semaine en cours n'est pas utilisée.</p>
   </div>`;
}
function fxTickerHTML(s){
  const tv=s&&s.tv;
  if(!tv) return '<span class="fx-tv"></span>';
  const cp=(typeof ophirCopyBtn==='function')?ophirCopyBtn(tv):'';
  return `<span class="fx-tv tvs"><code>${tv}</code>${cp}</span>`;
}
function fxBarHTML(s){
  /* t490u : barre d'indice de LA devise, échelle /100 (les règles −50..250 des devises ne sont pas encore calculées). */
  if(s&&s.ok&&s.apex10&&typeof listApexBar==='function')
    return `<div class="fx-apex">${listApexBar(Object.assign({},s,{forceApex100:true}))}</div>`;
  if(s&&s.ok&&s.apex10&&typeof dualBarApex100==='function')
    return `<div class="fx-apex">${dualBarApex100(s.apex10,s.sent,s.av,true)}</div>`;
  return `<div class="fx-apex">${fxSigHTML(s&&s.av,s&&s.apex10)}</div>`;
}
function fxEtfRow(s){
  const e=s&&s.etf_local;
  if(!e) return '';
  if(!e.ok){
    const why=(e.raison||'Données insuffisantes pour désigner un ETF/ETC liquide, sans inventer.').replace(/"/g,'&quot;');
    return `<div class="fx-etf fx-etf-na" title="${why}"><span class="fx-etf-k">ETF local</span><span class="fx-etf-na-t">Pas d’ETF/ETC retenu en ${s.sym} : données 3 ans annualisées insuffisantes (voir Détail / rapport), sans invention.</span></div>`;
  }
  const tv=e.tv||'';
  const cp=(tv&&typeof ophirCopyBtn==='function')?ophirCopyBtn(tv):'';
  const tick=tv?`<span class="tvs fx-tv"><code>${tv}</code>${cp}</span>`:'';
  const bar=(e.apex10&&typeof listApexBar==='function')?listApexBar(Object.assign({},e,{forceApex250:true})):((e.apex10&&e.apex10.display)?`<span class="home-sig apex10"><b>${e.apex10.display}</b><small>/250</small></span>`:'');
  const p3=e.perf_3y_ann!=null?e.perf_3y_ann:e.perf_1y;
  const perf=p3!=null?`3 ans ann. ${p3>=0?'+':''}${String(p3).replace('.',',')} %`:'';
  const asof=e.perf_asof?` au ${e.perf_asof.slice(8,10)}/${e.perf_asof.slice(5,7)}/${e.perf_asof.slice(0,4)}`:'';
  const yld=e.yield_label?` · Dist. ${e.yield_label}`:'';
  const tip=[e.nom, perf+asof, e.source, e.limitations].filter(Boolean).join(' · ').replace(/"/g,'&quot;');
  return `<div class="fx-etf" title="${tip}">
    <div class="fx-etf-id"><span class="fx-etf-k">ETF local</span><b>${e.court||e.nom||''}</b>${tick}</div>
    <div class="fx-etf-bar">${bar}</div>
    <div class="fx-etf-meta">${perf}${asof}${yld}</div>
  </div>`;
}
function fxCard(s,i){
  const fl=FX_FLAG[s.sym];
  const flag=fl?`<img class="flag-us" src="${fl[0]}" width="28" height="15" alt="Drapeau : ${fl[1]}">`:'';
  const sent=(s.ok&&s.sent&&s.sent.value!=null)?`S ${fmt(s.sent.value,0)} ${s.sent.label||''}`:'—';
  const warn=(s.warn&&s.warn.length)?`<span class="sec-warn" title="${s.warn.join(' ')}">⚠</span>`:'';
  return `<div class="card fx-card no-group">
    <h2>${flag}${s.nom} · ${s.sym} · face à l'euro</h2>
    <div class="desc fx-line">
      ${fxTickerHTML(s)}
      <span class="fx-px" title="Clôture hebdomadaire du ${s.date?dshort(s.date):''}">${s.ok&&s.close!=null?fxPx(s):'—'}</span>
      ${fxBarHTML(s)}
      <span class="fx-sent">${sent}</span>
      <span class="fx-warn">${warn}</span>
      ${fxEtfRow(s)}
    </div>
    ${fxDetailHTML(s,i)}
  </div>`;
}
function fxDxyCard(X){
  const last=X.dxy_last||[];
  const px=last[1]!=null?fmt(last[1],2):'—';
  const d=last[0]?dshort(last[0]):'';
  const p1=pctTxt(X.dxy_perf&&X.dxy_perf[1]);
  const p5=pctTxt(X.dxy_perf&&X.dxy_perf[5]);
  return `<div class="card fx-card fx-dxy no-group">
    <h2>Dollar Index (DXY) · repère, sans note APEX</h2>
    <div class="desc fx-line">
      <span class="fx-tv"></span>
      <span class="fx-px" title="Clôture hebdomadaire du ${d}">${px}</span>
      <span class="home-sig fx-rep"><b>—</b><em>Repère</em></span>
      <span class="fx-sent">1 an ${p1} · 5 ans ${p5}</span>
      <span class="fx-warn"></span>
    </div>
    <p class="note">Le DXY est un repère de marché (indice ICE), sans note APEX. Les notes des lignes portent sur le cours d'une unité de devise en euros.</p>
  </div>`;
}

/* ================= LIQUIDITÉS ================= */
function renderLiquidites(el){
  const Q=T2.liquidites,R=Q.retrieved,Lv=Q.livrets,I=Q.ipc,B=Q.bce,X=Q.fx,rl=Q.real_last;
  const fxA=X.assets||[];
  const fxSorted=fxSort(fxA);
  const dFx=(fxSorted[0]&&fxSorted[0].date)|| (fxA[0]&&fxA[0].date);
  const cntFx=z=>fxA.filter(s=>s.av&&s.av.label&&s.av.label.includes(z)).length;
  const idxOf=s=>fxA.indexOf(s);
  const chg=Lv.changes.slice(-4).map(c=>`<tr><td>1<sup>er</sup> ${mfr(c.date)}</td><td>${fmt(c.livret_a,2)} %</td><td>${fmt(c.lep,2)} %</td><td style="text-align:left;white-space:normal">${lnk(c.url,c.source)}</td></tr>`).join('');
  el.innerHTML=`
  <div class="fx-block no-group" id="fxFiches">
   <div class="fx-kicker">
    <h2>Devises par rapport à l'euro</h2>
    <div class="desc">${fxA.length} devises face à l'euro · ${dFx?('clôtures hebdomadaires au '+dshort(dFx)):'dates indisponibles'} · triées de la meilleure à la pire note · <span class="al-dots" title="Achat ${cntFx('Achat')} · Neutre ${cntFx('Neutre')} · Vente ${cntFx('Vente')}"><span><i class="g"></i>${cntFx('Achat')}</span><span><i class="o"></i>${cntFx('Neutre')}</span><span><i class="r"></i>${cntFx('Vente')}</span></span> · DXY en repère, sans note. Une note positive favorise l'achat de la devise contre l'euro.</div>
    <div class="fx-colh" aria-hidden="true"><span></span><span>Devise · face à l'euro</span><span>Ticker</span><span>Cours en €</span><span>Note APEX</span><span>Sentiment</span><span></span></div>
   </div>
   ${fxSorted.map(s=>fxCard(s,idxOf(s))).join('')}
   ${fxDxyCard(X)}
   <div class="card no-group" id="fxMeth">
    <h2>Méthode, historique EUR/USD et DXY</h2>
    <div class="desc acc-sum">Méthode de notation et courbes EUR/USD et DXY, en repères</div>
    <p>Chaque devise des pays représentés sur APEX (USD, JPY, GBP, CHF, AUD, CAD, KRW) a une note APEX et un signal Achat / Vente, calculés sur le cours hebdomadaire d'une unité de cette devise en euros (USD/EUR = 1/EURUSD, et ainsi de suite). Une note positive signifie un contexte plus favorable à l'achat de cette devise contre l'euro. Même grille et mêmes règles du 18/11 que les autres actifs notés (Charte 20 %, Elliott 15 %, Fibonacci 15 %, Divergence RSI/MACD 10 % facultative, panier technique 40 %). Force relative contre un panier équipondéré des 7 devises. Le DXY reste un repère de marché, sans note APEX. CNY et INR ne figurent pas : pas de bloc pays Chine ni Inde. La watchlist TradingView n'est pas modifiée.</p>
    <div class="chart" style="height:200px;margin-top:8px"><canvas id="cFx"></canvas></div>
    <div class="note">Le graphique ci-dessus conserve la convention EUR/USD (1 euro en dollars) et le DXY, comme repères. Les notes des lignes, elles, portent sur la série inversée (1 unité de devise en euros). Tendance = hausse ou baisse de cette série inversée si le mois et l'année vont dans le même sens (> 0,5 % ou < −0,5 %), sinon mixte. DXY : indice ICE (panier de 6 devises, l'euro y pèse environ 58 %), source Yahoo Finance, pas la Fed. Indice dollar officiel de la Fed : ${lnk('https://fred.stlouisfed.org/series/DTWEXBGS','FRED DTWEXBGS')}.</div>
    <div class="src">Sources : ${lnk('https://finance.yahoo.com/quote/EURUSD=X/history/','Yahoo Finance')} (barres hebdomadaires EURUSD=X, etc., série inversée pour la note) ; ${lnk('https://finance.yahoo.com/quote/DX-Y.NYB/history/','Yahoo Finance DX-Y.NYB')} (DXY, ICE). Récupéré le ${dfr((X.apex&&X.apex.generated||R.yahoo||R.ecb||'').slice(0,10))}.</div>
   </div>
  </div>

  <div class="card no-group"><h2>Épargne réglementée · Livret A et LEP</h2>
   <div class="desc">Taux de rémunération mensuels depuis janvier 2000, comparés à l'inflation française sur un an.</div>
   <div class="kpis">${kpi('Livret A',fmt(Lv.last[1],2)+' %','en vigueur depuis le 1er août 2026')+kpi('LEP',fmt(Lv.last[2],2)+' %','en vigueur depuis le 1er février 2026, maintenu en août')+kpi('Inflation France (IPC, 1 an)',fmt(I.last[1],1)+' %',mfr(I.last[0])+' · INSEE')+kpi('Rendement réel Livret A',`<span class="${cls(rl[1])}">${sign(rl[1],1)} pt</span>`,'taux − inflation, '+mfr(rl[0]))+kpi('Rendement réel LEP',`<span class="${cls(rl[2])}">${sign(rl[2],1)} pt</span>`,'taux − inflation, '+mfr(rl[0]))}</div>
   <div class="chart" style="height:300px"><canvas id="cLiv"></canvas></div>
   <div class="chart" style="height:200px;margin-top:10px"><canvas id="cReal"></canvas></div>
   <table style="margin-top:12px"><thead><tr><th>Derniers changements</th><th>Livret A</th><th>LEP</th><th style="text-align:left">Texte officiel</th></tr></thead><tbody>${chg}</tbody></table>
   <div class="note">Pour janv. 2000 → août 2020, la source est la table mensuelle d'archive de la Banque de France. Ensuite, chaque changement de taux est repris des rapports et communiqués officiels de la Banque de France (citations dans data/liquidites). La série a été vérifiée mois par mois contre l'open data de la Caisse des Dépôts (janv. 2024 → juin 2026) : aucun écart. Le rendement réel est un écart simple (taux − inflation), avant fiscalité : Livret A et LEP sont exonérés d'impôt. Le plafond et les conditions de revenus du LEP ne sont pas pris en compte.</div>
   <div class="src">Sources : ${lnk('https://webstat.banque-france.fr/fr/catalogue/mir1/MIR1.M.FR.B.L23FRLA.D.R.A.2230U6.EUR.O','Banque de France / Webstat')} (taux des livrets réglementés), ${lnk('https://www.banque-france.fr/fr/publications-et-statistiques/publications/rapport-sur-lepargne-reglementee-2025','Rapport sur l\'épargne réglementée 2025')}, ${lnk('https://opendata.caissedesdepots.fr/explore/dataset/flux-et-taux-la-ldds-lep/','Caisse des Dépôts open data')} ; inflation : ${lnk('https://www.insee.fr/fr/statistiques/serie/'+I.idbank,'INSEE, IPC base 2025, glissement annuel, idbank '+I.idbank)} (mise à jour INSEE ${dfr(I.last_update)}). Récupéré le ${dfr(R.insee.slice(0,10))}.</div></div>

  <div class="card no-group"><h2>Taux monétaires de la zone euro</h2>
   <div class="desc">Taux de la facilité de dépôt de la BCE (fin de mois), €STR (moyenne mensuelle, depuis oct. 2019) et Euribor 3 mois (moyenne mensuelle).</div>
   <div class="kpis">${kpi('Taux de dépôt BCE',fmt(B.dfr_last[1],2)+' %','depuis le '+dshort(B.dfr_changes[B.dfr_changes.length-1][0])+' (précédent '+fmt(B.dfr_changes[B.dfr_changes.length-2][1],2)+' %)')+kpi('€STR',fmt(B.estr_last[1],3)+' %','fixing du '+dshort(B.estr_last[0]))+kpi('Euribor 3 mois',fmt(B.eur3_last[1],3)+' %','moyenne de '+mfr(B.eur3_last[0]))}${na('Rendement des fonds monétaires','pas de série publique gratuite trouvée ; leur rendement brut suit l\'€STR, moins les frais')}</div>
   <div class="chart" style="height:300px"><canvas id="cBce"></canvas></div>
   <div class="note">Le taux de dépôt est le taux directeur qui pilote la rémunération des liquidités. Un fonds monétaire en euros rapporte en général à peu près l'€STR moins ses frais de gestion : à vérifier dans le DIC de chaque fonds.</div>
   <div class="src">Source : ${lnk('https://data.ecb.europa.eu/data/datasets/FM/FM.D.U2.EUR.4F.KR.DFR.LEV','BCE, FM.D.U2.EUR.4F.KR.DFR.LEV')}, ${lnk('https://data.ecb.europa.eu/data/datasets/EST/EST.B.EU000A2X2A25.WT','EST.B.EU000A2X2A25.WT (€STR)')}, ${lnk('https://data.ecb.europa.eu/data/datasets/FM/FM.M.U2.EUR.RT.MM.EURIBOR3MD_.HSTA','FM.M.U2.EUR.RT.MM.EURIBOR3MD_.HSTA (Euribor 3 m)')}, via data-api.ecb.europa.eu, récupéré le ${dfr(R.ecb.slice(0,10))}.</div></div>`;
  const lv=Lv.monthly.map(x=>[x[0],x[1]]),lp=Lv.monthly.map(x=>[x[0],x[2]]),ip=I.series;
  const m=merge([lv,lp,ip]);
  lineChart('cLiv',m.labels.map(mfr),[{label:'Livret A',data:m.data[0],borderColor:'#e6c27a',stepped:true},{label:'LEP',data:m.data[1],borderColor:'#7fd1a8',stepped:true},{label:'Inflation (IPC, 1 an)',data:m.data[2],borderColor:'#e88f8f',borderDash:[4,3],borderWidth:1.3}],{unit:' %',ticks:12,y:{ticks:{callback:v=>v+' %'}}});
  lineChart('cReal',Q.real.map(x=>mfr(x[0])),[{label:'Rendement réel Livret A',data:Q.real.map(x=>x[1]),borderColor:'#e6c27a',fill:{target:'origin',above:'rgba(127,209,168,.15)',below:'rgba(232,143,143,.18)'}},{label:'Rendement réel LEP',data:Q.real.map(x=>x[2]),borderColor:'#7fd1a8',borderWidth:1.2}],{unit:' pt',ticks:12});
  const b=merge([B.dfr_m,B.estr_m,B.eur3_m]);
  lineChart('cBce',b.labels.map(mfr),[{label:'Taux de dépôt BCE',data:b.data[0],borderColor:'#e6c27a',stepped:true},{label:'€STR',data:b.data[1],borderColor:'#7fd1a8'},{label:'Euribor 3 mois',data:b.data[2],borderColor:'#a9cdf5'}],{unit:' %',dec:3,ticks:12,y:{ticks:{callback:v=>v+' %'}}});
  const f=merge([X.eurusd_w,X.dxy_w.map(x=>{const d=new Date(x[0]);return [x[0],x[1]];})]);
  lineChart('cFx',f.labels.map(dshort),[{label:'EUR/USD (axe gauche)',data:f.data[0],borderColor:'#e6c27a',yAxisID:'y'},{label:'DXY (axe droit)',data:f.data[1],borderColor:'#a9cdf5',yAxisID:'y1'}],{dec:3,ticks:10,extra:{scales:{x:{ticks:{maxTicksLimit:10}},y:{position:'left'},y1:{position:'right',grid:{drawOnChartArea:false}}}}});
  if(!el._fxChartBound){
    el._fxChartBound=true;
    el.addEventListener('click',e=>{
      const card=e.target.closest('.fx-card');
      if(!card||card.classList.contains('fx-dxy')) return;
      setTimeout(()=>{
        if(!card.classList.contains('acc-open')) return;
        const det=card.querySelector('[data-cx][data-pack="fx"]');
        if(det&&typeof cxCharts==='function') cxCharts(det);
        if(typeof accResize==='function') accResize(card);
      },80);
    });
  }
}

