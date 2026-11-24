/* ===== Onglet Actions · SECTEURS PAR PAYS (France, plus USA via secteurs). Univers limité à USA et France (t455u) : pas de carte, panier, compteur ni filtre pour les autres pays. ===== */
const PAYS=JSON.parse(document.getElementById('data8').textContent);
function pPilotId(C,s){return (C&&C.cc&&s&&s.key)?(C.cc+'_'+s.key):null;}
function pSecOf(C,s){const id=pPilotId(C,s);return (id&&typeof pilotOf==='function')?pilotOf(id):null;}

const pCur=c=>({EUR:'€',JPY:'¥',KRW:'₩',AUD:'A$',GBp:'p',USD:'$',CAD:'C$',CHF:'CHF',SEK:'SEK'}[c]||c||'');
const pNum=(v,c)=>fmt(v,c==='KRW'||c==='JPY'?0:2)+' '+pCur(c);
function pComps(s){
  const pos=x=>`${Math.max(0,Math.min(100,x))}%`;
  const sc=s.sent.components.map(c=>`<div class="ind-sb"><div class="ind-sbl"><span>${c.name}</span><b class="sc-t" style="color:${c.value==null?'#888':gmir(c.value)}">${c.value==null?'n.d.':fmt(c.value,0)}</b></div><div class="ind-sbt">${c.value==null?'':`<i style="width:${pos(c.value)};background:${gmir(c.value)}"></i>`}</div><div class="ind-sbd">poids ${fmt(c.weight*100,1)} % · ${c.raw}</div></div>`).join('');
  const ac=(s.av.components||[]).map(c=>{const n=c.note;return `<div class="av-c"><div class="av-cl"><span>${c.nom}</span><b style="color:${n==null?'#888':avCol(n)}">${n==null?(c.facultatif?'non comptée':'n.d.'):sign(n,0)}</b></div><div class="av-cb"><div class="av-mid"></div>${n==null?'':`<i style="${n>=0?'left:50%':'right:50%'};width:${Math.abs(n)/2}%;background:${avCol(n)}"></i>`}</div><div class="av-cd">valeur ${c.valeur} · poids ${pw(c.poids)} % · contribution <b>${c.contrib==null?(c.facultatif?'non comptée':'retirée'):sign(c.contrib,1)}</b> · règle : ${c.regle}</div></div>`;}).join('');
  return [sc,ac];
}
function pList(C,s){
  const f=s.fond;if(!f)return '';
  const pSec=pSecOf(C,s);
  const top=(f.top||[]).slice();
  const ordered=top.slice().sort((a,b)=>{
    const pa=typeof pilotRec==='function'?pilotRec(a.tv):null;
    const pb=typeof pilotRec==='function'?pilotRec(b.tv):null;
    const ta=(pa&&pa.total!=null)?pa.total:-Infinity;
    const tb=(pb&&pb.total!=null)?pb.total:-Infinity;
    if(tb!==ta) return tb-ta;
    return 0;
  });
  const rows=ordered.map((r,k)=>
    `<li class="fl-row"${r.tv?` data-pos-tv="${r.tv}"`:''}><div class="fl-id"><span class="fl-rk">${k+1}</span><b>${r.name}</b>${tvTag(r.tv)}${typeof posBadges==='function'?posBadges(r.tv):''}${typeof dispoBadge==='function'?dispoBadge(r.tv):''}</div>${listApexBar(Object.assign({},r,{forceV2:true}))}${r.note_revolut?`<div class="fl-sub">${r.note_revolut}</div>`:''}</li>`
  ).join('');
  const etfTv=(pSec&&pSec.etf&&pSec.etf.tv)||s.tv||null;
  const etfBar=etfTv?listApexBar({tv:etfTv, name:(pSec&&pSec.etf&&pSec.etf.nom)||s.etf||'', forceV2:true}):'';
  const head=s.kind==='basket'
    ?`<div class="fl-etf"><span class="fl-k">Instrument</span><b>Panier APEX (non négociable)</b>${etfBar}<span class="sec-d" style="text-align:left">${s.ex_ref?`${s.ex_ref} (${C.nom}) n'est pas disponible chez Revolut : lecture du secteur via ce panier`:`Aucun ETF sectoriel ${C.nom} coté n'a été retenu`} ; composition : ${s.basket.map(b=>`${b.name} ${fmt(b.w,1)} %`).join(' · ')}.</span></div>`
    :`<div class="fl-etf"><span class="fl-k">${s.kind==='index'?'Indice sectoriel':'ETF principal'}</span><b>${s.etf}</b>${tvTag(s.tv)}${etfBar}</div>`;
  const rv=f.top.length<Math.min(5,f.eligible)?`<div class="note">${Math.min(5,f.eligible)-f.top.length} titre(s) de la sélection retiré(s) : non disponible(s) chez Revolut (règle APEX du 17/11/2026, sans les remplacer par d'autres titres non vérifiés).</div>`:'';
  const few=f.eligible<5?`<div class="note">${f.eligible} titre(s) éligibles sur ${f.universe} analysés : données Yahoo (ratios, consensus d'au moins 3 analystes) insuffisantes pour les autres${f.excluded.length?' ('+f.excluded.map(e=>e[0]).join(', ')+')':''}.</div>`:'';
  return `<details class="ind-meth sec-list"${pSec?` data-pilot="${pPilotId(C,s)}"`:''}><summary>${s.kind==='basket'?'Panier':s.kind==='index'?'Indice':'ETF'} + ${top.length} actions qualité / croissance</summary>
   ${head}${f.covered===false?`<div class="sr-ncm" style="margin:8px 0">Liste non couverte : ${f.eligible} titre(s) seulement passent les critères (données Yahoo complètes, consensus d'au moins 3 analystes, symbole TradingView vérifié) parmi les ${f.universe} plus grandes capitalisations ${C.nom} du secteur ; minimum 3 pour publier une liste.${f.excluded.length?' Titres écartés : '+f.excluded.map(e=>e[0]+' ('+e[1]+')').join(' · ')+'.':''}</div>`:`<ol class="fl${pSec?' fl-pilot':''}">${rows}</ol>${rv}${few}`}
   <div class="sec-d" style="text-align:left">Score de qualité fondamentale 0-100 = 50 % santé financière + 50 % croissance prévue, en rang parmi les ${f.eligible} titres éligibles des ${f.universe} plus grandes capitalisations ${C.nom} du secteur (classement Yahoo Finance${C.cc==='jp'?', regroupé selon les catégories TOPIX-17 par correspondance APEX des industries':''}).${f.profile==='fin'?' Profil financier : ROE, ROA, marges. Les banques (industries Banks / Savings Institutions) sont notées avec le fondamental bancaire APEX ; assurances et autres financières avec les règles actions hors banque.':f.profile==='reit'?' Profil immobilier : dette nette / EBITDA, marges, ROA.':''} Devise de cotation locale.</div>
  </details>`;
}


function pTile(C,s,i){
  const id=C.cc+'_'+i;
  if(!s.covered) return `<div class="sec sec-nc"><div class="sr"><div class="sr-c sec-h sr-n"><b>${s.nom}</b><span>non couvert</span></div><div class="sr-c sr-d"><div class="sr-ncm">${s.why}</div></div><div class="sr-c sr-b"></div></div></div>`;
  const [sc,ac]=pComps(s);
  return `<div class="sec${s.head?' sec-head':''}">
   <div class="sr">
    <div class="sr-c sec-h sr-n"><b>${s.nom}</b>${s.head?'':`<span class="pilot-badge">APEX ACHAT −50 à 250</span>`}<span>${s.kind==='basket'?'Panier APEX · '+s.basket.length+' grandes capitalisations, pondérées (plafond 25 %)':(s.sym.startsWith('^')?s.sym+' · ':s.sym.split('.')[0]+' · ')+s.etf}</span>${srWarn(s)}</div>
    ${(()=>{const p=pSecOf(C,s); if(p&&p.etf&&p.etf.total!=null) return `<div class="sr-c sr-d">${dualBarPilot(p.etf, true)}</div>`; if(!s.head) return `<div class="sr-c sr-d">${typeof v2Placeholder==='function'?v2Placeholder():''}</div>`; return srCells(s);})()}
    <div class="sr-c sr-b"></div>
   </div>
   ${s.head?'':(s.mlist?mList(C,s):pList(C,s))}
   <details class="ind-meth sec-det" data-p="${C.cc}" data-i="${i}"><summary>Détail et historique 1 an</summary>
     ${s.note?`<div class="note">${s.note}</div>`:''}
     ${s.head?`<div class="fl-etf"><span class="fl-k">ETF principal du pays</span><b>${s.etf}</b>${tvTag(s.tv)}</div>`:''}
     <p class="sr-close">Clôture hebdomadaire du ${dshort(s.date)} : <b>${pNum(s.close,s.currency)}</b> (${s.kind==='basket'?'niveau du panier, base 100 à sa première semaine':s.sym+' · '+s.etf}) · bougie clôturée${s.live?` ; semaine en cours au ${dshort(s.live.date)} non utilisée`:''}.</p>
     ${s.warn.map(w=>`<div class="note">${w}</div>`).join('')}
     <div class="ind-subt" style="margin-top:8px">Sentiment, 52 semaines (moy. ${fmt(s.sent.avg,0)} · min ${fmt(s.sent.min[1],0)} le ${dshort(s.sent.min[0])} · max ${fmt(s.sent.max[1],0)} le ${dshort(s.sent.max[0])})</div>
     <div class="ind-spark" style="height:90px"><canvas id="cPS${id}"></canvas></div>
     <p class="sent-mir">Couleurs du sentiment (points de la courbe, barres des composantes) en dégradé miroir, lecture contrarienne : peur = bleu (zone d'achat), euphorie = rouge (zone de vente).</p>
     <div class="ind-subt">Achat / Vente${(s.av.avg!=null&&s.av.min&&s.av.max)?`, 52 semaines (moy. ${sign(s.av.avg,0)} · min ${sign(s.av.min[1],0)} · max ${sign(s.av.max[1],0)})`:''}</div>
     <div class="ind-spark" style="height:90px"><canvas id="cPA${id}"></canvas></div>
     <div class="ind-sub"><div class="ind-subt">Composantes du sentiment (0-100)</div>${sc}</div>
     <div class="ind-sub"><div class="ind-subt">Composantes Achat / Vente (−100 à +100)</div>${ac}</div>
     <p>Plus haut historique des clôtures hebdomadaires disponibles (depuis le ${dshort(s.first)}) : ${pNum(s.ath.close,s.currency)} le ${dshort(s.ath.date)}, soit ${sign(s.ath.dd,1)} %. Distance au plus haut 52 semaines : ${sign(s.dd52,1)} %.</p>
     <p>Source : ${lnk(s.url,'Yahoo Finance · '+(s.kind==='basket'?'cours hebdomadaires des titres du panier':s.sym))}${s.kind==='basket'?' (calcul APEX)':''}, référence ${C.bench_nom} (${lnk(C.bench_url,C.bench)}). Données récupérées le ${s.retrieved.replace(' ',' à ')} (heure de Paris).</p>
   </details>
  </div>`;
}
function pCharts(det){
  if(det.dataset.done)return;det.dataset.done='1';const C=det.dataset.p==='met'?MET_C:PAYS.countries.find(c=>c.cc===det.dataset.p),i=+det.dataset.i,s=i<0?C.head:C.rows[i],id=C.cc+'_'+i;
  const x={ticks:{maxTicksLimit:3,maxRotation:0,autoSkip:true,font:{size:9}},grid:{display:false}};
  const ml=d=>new Date(d).toLocaleDateString('fr-FR',{month:'short',year:'2-digit'});const ss=(s.sent&&s.sent.series)||[],ah=(s.av&&s.av.history)||[];
  charts.push(new Chart(document.getElementById('cPS'+id),{type:'line',data:{labels:ss.map(p=>ml(p[0])),datasets:[{data:ss.map(p=>p[1]),borderColor:'rgba(255,255,255,.55)',borderWidth:1.2,pointRadius:2,pointBackgroundColor:ss.map(p=>gmir(p[1])),pointBorderWidth:0,tension:.25}]},
    options:{maintainAspectRatio:false,animation:false,plugins:{legend:{display:false},tooltip:{callbacks:{title:c=>dshort(ss[c[0].dataIndex][0])}}},scales:{x,y:{min:0,max:100,ticks:{stepSize:50,font:{size:9}}}}}}));
  charts.push(new Chart(document.getElementById('cPA'+id),{type:'bar',data:{labels:ah.map(p=>ml(p[0])),datasets:[{data:ah.map(p=>p[1]),backgroundColor:ah.map(p=>avCol(p[1])),borderWidth:0,barPercentage:1,categoryPercentage:.9}]},
    options:{maintainAspectRatio:false,animation:false,plugins:{legend:{display:false},tooltip:{callbacks:{title:c=>dshort(ah[c[0].dataIndex][0])}}},scales:{x,y:{min:-100,max:100,ticks:{stepSize:100,font:{size:9}}}}}}));
}
function paysUniversActions(){
  const u=(typeof PAYS!=='undefined'&&PAYS&&Array.isArray(PAYS.univers_actions)&&PAYS.univers_actions.length)
    ?PAYS.univers_actions:['USA','France'];
  return new Set(u);
}
function paysEstDansUnivers(C){
  if(!C) return false;
  const u=paysUniversActions();
  const nom=String(C.nom||C.name||'').trim();
  if(nom&&u.has(nom)) return true;
  const cc=String(C.cc||'').toLowerCase();
  if(cc==='us'||cc==='usa') return u.has('USA');
  if(cc==='fr') return u.has('France');
  return false;
}
function renderPays(el){
  (PAYS.countries||[]).filter(paysEstDansUnivers).forEach(C=>{
    const S=(C.rows||[]).filter(s=>s.covered),nc=(C.rows||[]).filter(s=>!s.covered),d=C.head.date,cnt=z=>S.filter(s=>s.av&&s.av.label&&s.av.label.includes(z)).length;
    const hi=S.length?S.reduce((a,b)=>b.sent.value>a.sent.value?b:a):null;
    const lo=S.length?S.reduce((a,b)=>b.sent.value<a.sent.value?b:a):null;
    const nAth=S.filter(s=>s.warn.length).length;
    const kinds=[...new Set(S.map(s=>s.kind))];
    const c=document.createElement('div');c.className='card no-group pays-card';c.dataset.cc=C.cc;
    const head=Object.assign({},C.head,{head:true,covered:true});
    const st=(typeof countryApexAvg==='function')?countryApexAvg(C):null;
    const a10=(st&&st.apex10)||C.apex10||(C.head&&C.head.apex10)||null;
    const mktAv=(st&&st.av)||(C.av_pays)||(C.head&&C.head.av)||null;
    const scale=a10&&(a10.v2||a10.total_max===250||a10.scale===250||a10.total_max===270||a10.scale===270)?'250':'100';
    const disp=a10?(a10.total!=null?String(a10.total):a10.display):'';
    const apexTag=a10&&(a10.display||a10.total!=null)?`<span class="js-apex10" hidden data-display="${disp}" data-hex="${a10.hex||''}" data-note="${a10.total!=null?a10.total:a10.note}" data-scale="${scale}"></span>`:'';
    const mktTxt=mktAv&&mktAv.score!=null?` · <i>Marché</i> <b>${mktAv.label||''} ${sign(mktAv.score,0)}</b>`:'';
    const sumStocks=S.length
      ? `${S.length} secteurs${nc.length?` (+${nc.length} non couvert${nc.length>1?'s':''})`:''} · au ${dshort(d)}${mktTxt} · <i>Achat</i> <b>${cnt('Achat')}</b> · <i>Neutre</i> <b>${cnt('Neutre')}</b> · <i>Vente</i> <b>${cnt('Vente')}</b> · <i>sentiment max</i> <b>${hi.nom} ${fmt(hi.sent.value,0)}</b> · <i>min</i> <b>${lo.nom} ${fmt(lo.sent.value,0)}</b>${nAth?` · <i>⚠ près du record</i> <b>${nAth}</b>`:''}`
      : `Actions limitées à USA et France : seule la ligne Marché (ETF pays) est affichée · au ${dshort(d)}${mktTxt}`;
    const titre=S.length?`Secteurs ${C.nom} · sentiment et achat / vente`:`Marché ${C.nom}`;
    c.innerHTML=`<h2><img class="flag-us" src="${C.flag}" width="28" height="15" alt="Drapeau : ${C.nom}">${titre}</h2>
     <div class="desc acc-sum">${apexTag}${sumStocks}</div>
     ${kinds.includes('basket')?'<div class="ind-badge" style="margin-top:4px">« panier APEX » = panier calculé par APEX</div>':''}
     <div class="sec-grid">${srHead('Secteur · instrument', true)}${pTile(C,head,-1)}${C.rows.map((s,i)=>pTile(C,s,i)).join('')}</div>
     <details class="ind-meth"><summary>Méthode et pondérations</summary>
       <p><b>Sentiment Peur / Euphorie (0-100).</b> ${SEC.method_sent.replace(/S&P 500/g,C.bench_nom.split(' (')[0])}</p>
       <p><b>Achat / Vente (−100 à +100).</b> ${SEC.method_av.replace(/S&P 500/g,C.bench_nom.split(' (')[0])}</p>
       <p><b>Instruments.</b> ${C.cc==='jp'?"Les 17 catégories TOPIX-17 sont suivies par les ETF NEXT FUNDS TOPIX-17 (Nomura, cotés à Tokyo, 1617 à 1633).":C.cc==='au'?"Indices sectoriels officiels S&P/ASX 200 (classification GICS), cours hors dividendes.":C.cc==='kr'?"ETF sectoriels KODEX (Samsung Asset Management) et TIGER (Mirae Asset) cotés à la bourse de Corée ; secteurs sans ETF adapté : panier APEX.":`Aucun ETF ni indice sectoriel national ${C.nom} exploitable n'est disponible dans la source (Yahoo Finance) : chaque secteur est un « panier APEX ».`}
        Panier APEX : jusqu'à 10 plus grandes capitalisations du pays dans le secteur (classement Yahoo Finance, actions de préférence et doublons retirés), pondérées par la capitalisation actuelle avec un plafond de 25 % par titre, rendements hebdomadaires chaînés à partir de la première semaine où au moins 3 titres cotent. Composition actuelle appliquée au passé : biais du survivant possible. Un secteur est « non couvert » s'il compte moins de 3 titres avec un historique d'au moins 3 ans. La ligne « Marché ${C.nom} » mesure l'ETF principal du pays. Référence pour la force relative : ${C.bench_nom} (${C.bench}).</p>
       <p><b>Listes du classement fondamental</b> (affichage de tout le top éligible, et non plus seulement des 5 premières). Mêmes critères que les secteurs USA (santé ${PAYS.health_weights.std.map(([n,w])=>n+' '+fmt(w*100,1)+' %').join(' · ')} ; profil financier et immobilier adaptés ; croissance ${PAYS.growth_weights.map(([n,w])=>n+' '+fmt(w*100,1)+' %').join(' · ')}), appliqués aux 8 plus grandes capitalisations du secteur. Seuil assoupli à 3 analystes (couverture plus faible hors États-Unis). Calcul reproductible avec <code>src/fetch_pays2.py</code> et <code>src/build_pays.py</code>.</p></details>
     <div class="src">Sources : ${lnk('https://finance.yahoo.com/','Yahoo Finance')} (clôtures hebdomadaires, classement sectoriel, ratios et consensus), ${lnk(C.bench_url,C.bench_nom)}, ${lnk('https://www.tradingview.com/','TradingView')} (symboles vérifiés). Classement récupéré le ${C.screen_retrieved.replace(' ',' à ')} ; calcul le ${PAYS.generated.replace(' ',' à ')} (heure de Paris).</div>`;
    el.appendChild(c);srWire(c);
    c.querySelectorAll('.sec-det').forEach(dt=>dt.addEventListener('toggle',()=>{if(dt.open)pCharts(dt);}));
  });
}
