/* ===== Onglet OBLIGATIONS ===== */
const OB=JSON.parse(document.getElementById('data7').textContent);
IND.obligations=OB.ind; AV.obligations=OB.av;
const pt=(v,d=2)=>fmt(v,d)+' %';
function renderObligations(el){
  const C=OB.charts,L=C.last,R=C.retrieved,fredL=(id,t)=>lnk('https://fred.stlouisfed.org/series/'+id,t||id);
  el.innerHTML=`
  <div class="card"><h2>Taux souverains 10 ans · OAT, Bund, Treasury</h2>
   <div class="desc">Rendement des emprunts d'État à 10 ans de la France, de l'Allemagne et des États-Unis, moyennes mensuelles depuis janvier 2000.</div>
   <div class="kpis">${kpi('OAT France 10 ans',pt(L.fr[1]),'moyenne de '+mfr(L.fr[0])+' · BCE')+kpi('Bund Allemagne 10 ans',pt(L.de[1]),'moyenne de '+mfr(L.de[0])+' · BCE')+kpi('US Treasury 10 ans',pt(L.us10[1]),'au '+dshort(L.us10[0])+' · FRED')+kpi('US Treasury 30 ans',pt(L.us30[1]),'au '+dshort(L.us30[0])+' · FRED')}</div>
   <div class="chart" style="height:300px"><canvas id="cObY"></canvas></div>
   <div class="note">Les taux France et Allemagne sont les « taux longs de convergence » mensuels publiés par la BCE (emprunts d'État à 10 ans environ). La BCE ne publie pas de série quotidienne par pays ; la série quotidienne de la Banque de France (Webstat) n'était pas accessible.</div>
   <div class="src">Sources : ${lnk('https://data.ecb.europa.eu/data/datasets/IRS/IRS.M.FR.L.L40.CI.0000.EUR.N.Z','BCE IRS.M.FR.L.L40.CI.0000.EUR.N.Z')}, ${lnk('https://data.ecb.europa.eu/data/datasets/IRS/IRS.M.DE.L.L40.CI.0000.EUR.N.Z','IRS.M.DE.L.L40.CI.0000.EUR.N.Z')} (récupéré le ${R.ecb.replace(' ',' à ')}) ; ${fredL('DGS10','FRED DGS10')}, ${fredL('DGS30','DGS30')} (moyenne mensuelle des valeurs quotidiennes, récupéré le ${R.fred.replace(' ',' à ')}).</div></div>

  <div class="card"><h2>Écart OAT − Bund · risque France</h2>
   <div class="desc">Prime payée par l'État français par rapport à l'Allemagne sur 10 ans, en points de pourcentage, mensuel depuis 2000.</div>
   <div class="kpis">${kpi('Écart OAT − Bund',fmt(L.spread[1],2)+' pt',mfr(L.spread[0]))+kpi('Rang depuis 2000',fmt(C.pct.spread,0)+'ᵉ percentile','100 = écart le plus large observé')+kpi('Plus haut depuis 2000',(()=>{const m=C.spread.reduce((a,b)=>b[1]>a[1]?b:a);return fmt(m[1],2)+' pt'})(),(()=>{const m=C.spread.reduce((a,b)=>b[1]>a[1]?b:a);return mfr(m[0])})())}</div>
   <div class="chart" style="height:240px"><canvas id="cObSp"></canvas></div>
   <div class="note">Un écart qui s'élargit signifie que les marchés exigent plus de rendement pour prêter à la France qu'à l'Allemagne : il mesure le risque budgétaire et politique perçu sur la dette française.</div>
   <div class="src">Calcul APEX : OAT 10 ans − Bund 10 ans, séries BCE ci-dessus.</div></div>

  <div class="card"><h2>Courbe des taux US · 10 ans − 2 ans et 10 ans − 3 mois</h2>
   <div class="desc">Pente de la courbe des taux américaine, dernière valeur de chaque semaine depuis 2000. Sous zéro, la courbe est inversée.</div>
   <div class="kpis">${kpi('10 ans − 2 ans',sign(L.t10y2y[1],2)+' pt','au '+dshort(L.t10y2y[0]))+kpi('10 ans − 3 mois',sign(L.t10y3m[1],2)+' pt','au '+dshort(L.t10y3m[0]))+kpi('US 2 ans / 3 mois',pt(L.us2[1])+' / '+pt(L.us3m[1]),'au '+dshort(L.us2[0]))+kpi('Dernière inversion 10-2 ans',C.inv_last?dshort(C.inv_last):'aucune','dernier jour sous zéro')}</div>
   <div class="chart" style="height:260px"><canvas id="cObC"></canvas></div>
   <div class="note">Une courbe inversée a précédé la plupart des récessions américaines, avec un délai variable ; ce n'est pas un signal de date.</div>
   <div class="src">Source : ${fredL('T10Y2Y','FRED T10Y2Y')}, ${fredL('T10Y3M','T10Y3M')}, ${fredL('DGS2','DGS2')}, ${fredL('DGS3MO','DGS3MO')}. Récupéré le ${R.fred.replace(' ',' à ')}.</div></div>

  <div class="card"><h2>Taux réels et inflation anticipée · TIPS 10 ans</h2>
   <div class="desc">Rendement réel des obligations indexées sur l'inflation (TIPS 10 ans) et point mort d'inflation à 10 ans, hebdomadaire depuis 2003.</div>
   <div class="kpis">${kpi('Taux réel 10 ans (TIPS)',pt(L.tips[1]),'au '+dshort(L.tips[0]))+kpi('Inflation anticipée 10 ans (point mort)',pt(L.be[1]),'au '+dshort(L.be[0]))}</div>
   <div class="chart" style="height:260px"><canvas id="cObR"></canvas></div>
   <div class="src">Source : ${fredL('DFII10','FRED DFII10')}, ${fredL('T10YIE','T10YIE')}. Récupéré le ${R.fred.replace(' ',' à ')}.</div></div>

  <div class="card"><h2>Spreads de crédit · ICE BofA</h2>
   <div class="desc">Écart de rendement des obligations d'entreprises face aux emprunts d'État (option-adjusted spread), hebdomadaire depuis novembre 2023.</div>
   <div class="kpis">${kpi('Investment grade US',fmt(L.ig[1],2)+' pt','au '+dshort(L.ig[0])+' · '+fmt(C.pct.ig,0)+'ᵉ pct sur 3 ans')+kpi('High yield US',fmt(L.hy[1],2)+' pt','au '+dshort(L.hy[0])+' · '+fmt(C.pct.hy,0)+'ᵉ pct sur 3 ans')+kpi('High yield euro',fmt(L.ehy[1],2)+' pt','au '+dshort(L.ehy[0]))+kpi('Entreprises émergentes',fmt(L.em[1],2)+' pt','au '+dshort(L.em[0]))}${na('Investment grade euro','série ICE BofA euro IG absente de FRED')}</div>
   <div class="chart" style="height:260px"><canvas id="cObCr"></canvas></div>
   <div class="note">Depuis 2023, FRED ne diffuse plus que les 3 dernières années des indices ICE BofA : l'historique long n'est pas disponible gratuitement. Un spread qui s'élargit signale une hausse du risque de crédit perçu.</div>
   <div class="src">Source : ${fredL('BAMLC0A0CM','FRED BAMLC0A0CM')}, ${fredL('BAMLH0A0HYM2','BAMLH0A0HYM2')}, ${fredL('BAMLHE00EHYIOAS','BAMLHE00EHYIOAS')}, ${fredL('BAMLEMCBPIOAS','BAMLEMCBPIOAS')} (ICE Data Indices). Récupéré le ${R.fred.replace(' ',' à ')}.</div></div>

  <div class="card"><h2>Volatilité obligataire · indice MOVE</h2>
   <div class="desc">Indice ICE BofA MOVE (volatilité implicite des Treasuries), clôture hebdomadaire depuis 2003.</div>
   <div class="kpis">${kpi('MOVE',fmt(L.move[1],1),'clôture hebdo du '+dshort(L.move[0]))}</div>
   <div class="chart" style="height:240px"><canvas id="cObM"></canvas></div>
   <div class="note">Source : Yahoo Finance, symbole ^MOVE. Attention : la fiche Yahoo de ce symbole porte un libellé erroné ; les niveaux (entre 56 et 137 sur deux ans) correspondent à l'indice MOVE, mais la source n'est pas ICE directement.</div>
   <div class="src">Source : ${lnk('https://finance.yahoo.com/quote/%5EMOVE/history/','Yahoo Finance ^MOVE')}. Récupéré le ${R.yahoo.replace(' ',' à ')}.</div></div>

  <div class="card"><h2>Taux directeurs · Fed et BCE</h2>
   <div class="desc">Taux effectif des fonds fédéraux (moyenne mensuelle) et taux de la facilité de dépôt de la BCE, depuis 2000.</div>
   <div class="kpis">${kpi('Fed, borne haute de la cible',pt(L.fed[1]),'au '+dshort(L.fed[0]))+kpi('Fed funds effectif',pt(L.dff[1]),'au '+dshort(L.dff[0]))+kpi('BCE, taux de dépôt',pt(L.dfr[1]),'au '+dshort(L.dfr[0]))}</div>
   <div class="chart" style="height:240px"><canvas id="cObP"></canvas></div>
   <div class="src">Sources : ${fredL('DFEDTARU','FRED DFEDTARU')}, ${fredL('DFF','DFF')} ; ${lnk('https://data.ecb.europa.eu/data/datasets/FM/FM.D.U2.EUR.4F.KR.DFR.LEV','BCE FM.D.U2.EUR.4F.KR.DFR.LEV')}. Récupéré le ${R.fred.replace(' ',' à ')}.</div></div>`;
  const y=merge([C.y10.fr,C.y10.de,C.y10.us]);
  lineChart('cObY',y.labels.map(mfr),[{label:'OAT France',data:y.data[0],borderColor:'#5b8def'},{label:'Bund Allemagne',data:y.data[1],borderColor:'#e6c27a'},{label:'US Treasury',data:y.data[2],borderColor:'#e88f8f'}],{unit:' %',ticks:12,y:{ticks:{callback:v=>v+' %'}}});
  lineChart('cObSp',C.spread.map(x=>mfr(x[0])),[{label:'OAT − Bund',data:C.spread.map(x=>x[1]),borderColor:'#ff9a1f',fill:{target:'origin',above:'rgba(255,154,31,.15)'}}],{unit:' pt',ticks:12});
  const cv=merge([C.curve.t10y2y,C.curve.t10y3m]);
  lineChart('cObC',cv.labels.map(dshort),[{label:'10 ans − 2 ans',data:cv.data[0],borderColor:'#e6c27a',fill:{target:'origin',below:'rgba(255,45,45,.18)'}},{label:'10 ans − 3 mois',data:cv.data[1],borderColor:'#a9cdf5',borderWidth:1.2}],{unit:' pt',ticks:10});
  const rr=merge([C.real.tips,C.real.be]);
  lineChart('cObR',rr.labels.map(dshort),[{label:'Taux réel 10 ans (TIPS)',data:rr.data[0],borderColor:'#7fd1a8'},{label:'Inflation anticipée 10 ans',data:rr.data[1],borderColor:'#e88f8f'}],{unit:' %',ticks:10});
  const cr=merge([C.credit.BAMLC0A0CM,C.credit.BAMLH0A0HYM2,C.credit.BAMLHE00EHYIOAS,C.credit.BAMLEMCBPIOAS]);
  lineChart('cObCr',cr.labels.map(dshort),[{label:'IG US',data:cr.data[0],borderColor:'#7fd1a8'},{label:'HY US',data:cr.data[1],borderColor:'#ff9a1f'},{label:'HY euro',data:cr.data[2],borderColor:'#e6c27a'},{label:'Entreprises émergentes',data:cr.data[3],borderColor:'#a9cdf5'}],{unit:' pt',ticks:8});
  lineChart('cObM',C.move.map(x=>dshort(x[0])),[{label:'MOVE',data:C.move.map(x=>x[1]),borderColor:'#c9a7ff'}],{dec:1,ticks:10});
  const po=merge([C.policy.fed,C.policy.dfr]);
  lineChart('cObP',po.labels.map(mfr),[{label:'Fed funds effectif',data:po.data[0],borderColor:'#e88f8f'},{label:'BCE taux de dépôt',data:po.data[1],borderColor:'#5b8def',stepped:true}],{unit:' %',ticks:12});
  renderSegments(el);
}
const OB_DISPO=JSON.parse((document.getElementById('data15')||{textContent:'{}'}).textContent||'{}');
const OB_DISPO_MAX=(OB_DISPO&&OB_DISPO.max_par_pays)||5;
function obDispoOf(s){
  const pays=(s&& (s.pays||s.key))||'';
  const pack=(OB_DISPO.pays||{})[pays]||(OB_DISPO.pays||{})[s&&s.key]||null;
  return pack;
}
function obDispoHTML(s){
  const pack=obDispoOf(s);
  if(!pack||!pack.lignes||!pack.lignes.length) return '';
  const lignes=pack.lignes.slice(0,OB_DISPO_MAX);
  const date=OB_DISPO.date_libelle||'';
  const sous=[pack.emetteur,date].filter(Boolean);
  const rows=lignes.map(r=>{
    const ref=r.reference?` <span class="ob-ref">${r.reference_libelle||'Référence du bloc'}</span>`:'';
    const rdt=r.rdt==null||r.rdt===''?'—':fmt(r.rdt,2)+'\u00a0%';
    return `<tr${r.reference?' class="is-ref"':''}><td class="ob-d-nom">${r.nom}${ref}</td><td class="ob-d-rdt">${rdt}</td><td class="ob-d-t">${r.terme||''}</td></tr>`;
  }).join('');
  return `<div class="ob-dispo"><div class="ob-dispo-top"><b>Dispo Revolut</b>${sous.length?`<span>${sous.join(' · ')}</span>`:''}</div><table><tbody>${rows}</tbody></table></div>`;
}
const eurAmt=(v,c)=>(v>=1e6?fmt(v/1e6,1)+' M':v>=1e3?fmt(v/1e3,0)+' k':fmt(v,0))+' '+(c==='EUR'?'€':c||'');
function obList(s){
  const rows=apexSortByNote(s.list).map((r,k)=>`<li${r.tv?` data-pos-tv="${r.tv}"`:''}><div class="fl-h"><b>${k+1}. ${r.name}</b>${r.score==null?'<span class="fl-sc" style="color:#888;font-size:12px">non classé</span>':`<span class="fl-sc" style="color:${gcol(r.score)}"><i>Sélection</i>${fmt(r.score,0)}<small>/100</small></span>`}</div>
    ${tvTag(r.tv)}${typeof dispoBadge==='function'?dispoBadge(r.tv):''}${listApexBar(r)}<div class="fl-m"><span><i>Frais</i> ${r.ter==null?'n.d.':fmt(r.ter,2)+' %'}</span><span><i>Liquidité</i> ${r.liq==null?'n.d.':eurAmt(r.liq,r.ccy)+'/j'}</span><span><i>Cotation Yahoo depuis</i> ${r.years==null?'n.d.':(r.years<1?'moins d’1 an':fmt(r.years,0)+' ans')}</span>
    <span><i>Rdt distribué 12 m</i> ${r.yield==null?'n.d. (capitalisant ?)':fmt(r.yield,2)+' %'}</span>${r.rating_a!=null?`<span><i>Noté ≥ A</i> ${r.rating_a} %</span>`:''}</div>
    <div class="fl-t">${r.fx==='couvert'?'<b class="fl-ok">change couvert</b>':r.fx==='USD'?'<b class="fl-warn">exposé au dollar</b>':r.fx==='local'?'<b class="fl-warn">devises émergentes</b>':r.fx==='EUR'?'<b class="fl-ok">en euro</b>':''}<span>${r.isin?'ISIN '+r.isin+' · ':''}cotation en ${r.ccy}</span></div>${r.note_revolut?`<div class="fl-sub">${r.note_revolut}</div>`:''}</li>`).join('');
  const d=s.list.find(x=>x.retrieved);
  return `<details class="ind-meth sec-list"><summary>${s.list.length?`ETF de référence + ${s.list.length} ETF UCITS`:'ETF de référence (aucune alternative UCITS trouvée)'}</summary>
   <div class="fl-etf"><span class="fl-k">${s.ref_us?'ETF de référence (US)':'ETF de référence'}</span><b>${s.pname||s.sym}</b>${tvTag(s.tv)}</div>${s.note_revolut?`<div class="note">${s.note_revolut}</div>`:''}
   ${s.ref_us?'<div class="sec-d" style="text-align:left">Référence américaine utilisée pour les signaux : pas de DIC PRIIPs, donc en principe non achetable par un particulier résidant en Europe.</div>':''}
   ${s.list.length?`<ol class="fl">${rows}</ol>`:'<div class="note">Aucun ETF UCITS éligible trouvé.</div>'}
   ${s.list_note?`<div class="note">${s.list_note}</div>`:''}
   ${s.list.length<5&&!s.list_note?`<div class="note">Seulement ${s.list.length} ETF UCITS retenus pour ce segment : depuis le 17/11/2026, APEX ne garde que les ETF disponibles chez Revolut (les autres ont été retirés sans être remplacés par des ETF non vérifiés).</div>`:''}
   <div class="sec-d" style="text-align:left">Risques : ${s.risks.join(' ')} Les ETF obligataires ne sont pas éligibles au PEA : compte-titres uniquement. Score = frais 40 % + liquidité 40 % + ancienneté 20 %, en rang parmi ${s.n_cand} ETF UCITS candidats. Duration et rendement à l'échéance non récupérés (source gratuite fiable absente). Données ${lnk('https://finance.yahoo.com/quote/'+(d?d.yahoo:s.sym)+'/','Yahoo Finance')}${d?' récupérées le '+d.retrieved.replace(' ',' à '):''} ; symboles vérifiés dans la recherche TradingView.</div>
</details>`;
}
function segTile(s,i){
  const v=s.sent.value,a=s.av.score,pos=x=>`${Math.max(0,Math.min(100,x))}%`;
  const sc=(s.sent.components||[]).map(c=>`<div class="ind-sb"><div class="ind-sbl"><span>${c.name}</span><b class="sc-t" style="color:${c.value==null?'#888':gmir(c.value)}">${c.value==null?'n.d.':fmt(c.value,0)}</b></div><div class="ind-sbt">${c.value==null?'':`<i style="width:${pos(c.value)};background:${gmir(c.value)}"></i>`}</div><div class="ind-sbd">poids ${fmt(c.weight*100,1)} % · ${c.raw}</div></div>`).join('');
  const avSrc=(s.av&&s.av.components)?s.av:(s.av_instrument||s.av_panier||s.av||{});
  const ac=(avSrc.components||[]).map(c=>{const n=c.note;return `<div class="av-c"><div class="av-cl"><span>${c.nom}</span><b style="color:${n==null?'#888':avCol(n)}">${n==null?(c.facultatif?'non comptée':'n.d.'):sign(n,0)}</b></div><div class="av-cb"><div class="av-mid"></div>${n==null?'':`<i style="${n>=0?'left:50%':'right:50%'};width:${Math.abs(n)/2}%;background:${avCol(n)}"></i>`}</div><div class="av-cd">valeur ${c.valeur} · poids ${pw(c.poids)} % · contribution <b>${c.contrib==null?(c.facultatif?'non comptée':'retirée'):sign(c.contrib,1)}</b> · règle : ${c.regle}</div></div>`;}).join('');
  return `<div class="sec">
   <div class="sr">
    <div class="sr-c sec-h sr-n" ${s.tv?`data-pos-tv="${s.tv}"`:''}><b>${s.nom}</b><span>${s.sym.replace('.DE','').replace('.AS','')} · ${s.pname||s.sym}</span>${srWarn(s)}${typeof posBadges==='function'?posBadges(s.tv):''}${typeof dispoBadge==='function'?dispoBadge(s.tv):''}</div>
    ${srCells(s)}
    <div class="sr-c sr-b"></div>
   </div>
   ${obDispoHTML(s)}
   ${obList(s)}
   <details class="ind-meth sec-det ob-det" data-i="${i}"><summary>Détail et historique 1 an</summary>
     <p class="sr-close">Clôture hebdomadaire du ${dshort(s.date)} : <b>${fmt(s.close,2)} ${s.ccy==='USD'?'$':'€'}</b> (${s.sym} · ${s.pname||''}${s.ref_us?', ETF de référence américain':''}) · bougie clôturée${s.live?` ; semaine en cours au ${dshort(s.live.date)} : ${fmt(s.live.close,2)}, non utilisée`:''}.</p>
     ${s.warn.map(w=>`<div class="note">${w}</div>`).join('')}
     <div class="ind-subt" style="margin-top:8px">Sentiment, 52 semaines (moy. ${fmt(s.sent.avg,0)} · min ${fmt(s.sent.min[1],0)} · max ${fmt(s.sent.max[1],0)})</div>
     <div class="ind-spark" style="height:90px"><canvas id="cObS${i}"></canvas></div>
     <p class="sent-mir">Couleurs du sentiment (points de la courbe, barres des composantes) en dégradé miroir, lecture contrarienne : peur = bleu (zone d'achat), euphorie = rouge (zone de vente).</p>
     <div class="ind-subt">Achat / Vente${(avSrc.avg!=null&&avSrc.min&&avSrc.max)?`, 52 semaines (moy. ${sign(avSrc.avg,0)} · min ${sign(avSrc.min[1],0)} · max ${sign(avSrc.max[1],0)})`:''}</div>
     <div class="ind-spark" style="height:90px"><canvas id="cObA${i}"></canvas></div>
     <div class="ind-sub"><div class="ind-subt">Composantes du sentiment (0-100)</div>${sc}</div>
     <div class="ind-sub"><div class="ind-subt">Composantes Achat / Vente (−100 à +100)</div>${ac}</div>
     <p>Plus haut des clôtures hebdomadaires depuis le ${dshort(s.first)} : ${fmt(s.ath.close,2)} le ${dshort(s.ath.date)} (${sign(s.ath.dd,1)} %). Distance au plus haut 52 semaines : ${sign(s.dd52,1)} %.</p>
     <p>Source : ${lnk(s.url,'Yahoo Finance · '+s.sym)}, récupéré le ${s.retrieved.replace(' ',' à ')} (heure de Paris).</p>
   </details></div>`;
}
function obCharts(det){
  if(det.dataset.done)return;det.dataset.done='1';const i=det.dataset.i,s=OB.segments[+i];
  const ml=d=>new Date(d).toLocaleDateString('fr-FR',{month:'short',year:'2-digit'}),x={ticks:{maxTicksLimit:3,maxRotation:0,font:{size:9}},grid:{display:false}};
  const ss=s.sent.series||[],ah=(s.av&&s.av.history)||(s.av_instrument&&s.av_instrument.history)||(s.av_panier&&s.av_panier.history)||[];
  charts.push(new Chart(document.getElementById('cObS'+i),{type:'line',data:{labels:ss.map(p=>ml(p[0])),datasets:[{data:ss.map(p=>p[1]),borderColor:'rgba(255,255,255,.55)',borderWidth:1.2,pointRadius:2,pointBackgroundColor:ss.map(p=>gmir(p[1])),pointBorderWidth:0,tension:.25}]},
    options:{maintainAspectRatio:false,animation:false,plugins:{legend:{display:false},tooltip:{callbacks:{title:c=>dshort(ss[c[0].dataIndex][0])}}},scales:{x,y:{min:0,max:100,ticks:{stepSize:50,font:{size:9}}}}}}));
  charts.push(new Chart(document.getElementById('cObA'+i),{type:'bar',data:{labels:ah.map(p=>ml(p[0])),datasets:[{data:ah.map(p=>p[1]),backgroundColor:ah.map(p=>avCol(p[1])),borderWidth:0,barPercentage:1,categoryPercentage:.9}]},
    options:{maintainAspectRatio:false,animation:false,plugins:{legend:{display:false},tooltip:{callbacks:{title:c=>dshort(ah[c[0].dataIndex][0])}}},scales:{x,y:{min:-100,max:100,ticks:{stepSize:100,font:{size:9}}}}}}));
}
const OBP=JSON.parse(document.getElementById('data9').textContent);
const OB_GROUPS={us:['tcourt','tlong','usig','hy','infl'],eu:['eurgov','eurig','em'],fr:['france'],de:['de'],ch:['ch'],ca:['ca']};
const OB_FLAG={us:['flag-us.png','États-Unis'],fr:['flag-fr.png','France'],de:['flag-de.png','Allemagne'],it:['flag-it.png','Italie'],es:['flag-es.png','Espagne'],gb:['flag-gb.png','Royaume-Uni'],jp:['flag-jp.png','Japon'],ch:['flag-ch.png','Suisse'],nl:['flag-nl.png','Pays-Bas'],be:['flag-be.png','Belgique'],kr:['flag-kr.png','Corée du Sud'],au:['flag-au.png','Australie'],ca:['flag-ca.png','Canada']};
const MAT_COL={'2':'#a9cdf5','10':'#e6c27a','30':'#e88f8f'};
function obRates(cc){
  const P=OBP.countries[cc];if(!P)return '';const id='cOP'+cc,dt=x=>x[0].length===7?mfr(x[0]):dshort(x[0]);
  const mats=['2','10','30'].filter(m=>P.y[m]);
  const k=mats.map(m=>kpi(`${({us:'Treasury',de:'Bund',fr:'OAT',it:'BTP',jp:'JGB',kr:'KTB',au:'ACGB',es:'Bonos',gb:'Gilt',ch:'Confédération',nl:'DSL',be:'OLO',ca:'Canada'}[cc]||'Taux')} ${m} ans`,pt(P.last[m][1]),(P.last[m][0].length===7?'moyenne de ':'au ')+dt(P.last[m])+(m==='10'?' · '+fmt(P.pct10,0)+'ᵉ percentile depuis 2001':''))).join('')
    +(P.short?kpi((P.short_nom||'Taux 3 mois')+' (OCDE)',pt(P.short[1]),'moyenne de '+mfr(P.short[0])):'')
    +['2','30'].filter(m=>!P.y[m]).map(m=>na(m+' ans','voir note ci-dessous')).join('');
  const sp=P.spread;
  return `<div class="ob-rates" data-cc="${cc}">
   <h3 class="ob-h3">Taux souverains ${mats.map(m=>m+' ans').join(' / ')} · depuis 2001</h3>
   <div class="desc">Moyennes mensuelles des rendements des emprunts d'État ${cc==='us'?'américains':'de '+P.nom}, de janvier 2001 à ${mfr(P.y['10'][P.y['10'].length-1][0])}. Plus haut 10 ans : ${pt(P.max10[1])} (${mfr(P.max10[0])}) ; plus bas : ${pt(P.min10[1])} (${mfr(P.min10[0])}).</div>
   <div class="kpis">${k}</div>
   <div class="chart" style="height:260px"><canvas id="${id}Y"></canvas></div>
   ${P.missing.map(m=>`<div class="note">${m}.</div>`).join('')}
   ${sp?`<h3 class="ob-h3">Écart ${sp.nom}</h3>
   <div class="kpis">${kpi('Écart actuel',fmt(sp.last[1],2)+' pt','moyenne de '+mfr(sp.last[0]))+kpi('Rang depuis 2001',fmt(sp.pct,0)+'ᵉ percentile','100 = écart le plus large observé')+kpi('Plus haut depuis 2001',fmt(sp.max[1],2)+' pt',mfr(sp.max[0]))}</div>
   <div class="chart" style="height:220px"><canvas id="${id}S"></canvas></div>
   <div class="note">Prime exigée par les marchés pour prêter à cet État plutôt qu'à l'Allemagne, à 10 ans : un écart qui s'élargit traduit une hausse du risque budgétaire ou politique perçu.</div>`:''}
   ${P.slope&&P.slope.last&&P.slope.last[1]!=null?`<h3 class="ob-h3">Courbe des taux · ${P.slope.nom}</h3>
   <div class="kpis">${kpi(P.slope.nom,sign(P.slope.last[1],2)+' pt','moyenne de '+mfr(P.slope.last[0]))+kpi('Dernière inversion',P.slope.inv_last?mfr(P.slope.inv_last):'aucune depuis 2001','mois sous zéro le plus récent')}</div>
   <div class="ob-curve"><div class="chart" style="height:200px"><canvas id="${id}C"></canvas></div><div class="chart" style="height:200px"><canvas id="${id}L"></canvas></div></div>
   <div class="note">À gauche : courbe actuelle (dernières valeurs disponibles par échéance${P.short?' ; 3 mois = '+(P.short_nom||'taux interbancaire 3 mois')+', OCDE':''}). À droite : pente ${P.slope.nom} en moyenne mensuelle ; sous zéro, la courbe est inversée.${P.slope.nom.includes('3 mois')?' Le 2 ans n\'étant pas récupéré, la pente utilise le taux 3 mois de l\'OCDE.':''}</div>`:'<div class="note">Pente de la courbe non calculée : le taux 2 ans et un taux court récent ne sont pas disponibles pour ce pays.</div>'}
   <div class="src">Sources : ${P.sources.map(x=>lnk(x.url,x.nom)+' (récupéré le '+x.retrieved.replace(' ',' à ')+')').join(' ; ')}. Calcul APEX : moyennes mensuelles, écarts et pentes.</div>
  </div>`;
}
function obRatesCharts(cc){
  const P=OBP.countries[cc];if(!P)return;const id='cOP'+cc,mats=['2','10','30'].filter(m=>P.y[m]);
  const y=merge(mats.map(m=>P.y[m]));
  lineChart(id+'Y',y.labels.map(mfr),mats.map((m,j)=>({label:m+' ans',data:y.data[j],borderColor:MAT_COL[m]})),{unit:' %',ticks:12,y:{ticks:{callback:v=>v+' %'}}});
  if(P.spread)lineChart(id+'S',P.spread.series.map(x=>mfr(x[0])),[{label:P.spread.nom,data:P.spread.series.map(x=>x[1]),borderColor:'#ff9a1f',fill:{target:'origin',above:'rgba(255,154,31,.15)'}}],{unit:' pt',ticks:10});
  if(document.getElementById(id+'C'))charts.push(new Chart(document.getElementById(id+'C'),{type:'line',data:{labels:P.curve.map(x=>x[0]),datasets:[{label:'Courbe actuelle',data:P.curve.map(x=>x[1][1]),borderColor:'#e6c27a',backgroundColor:'#e6c27a',pointRadius:4,tension:.2}]},
    options:{maintainAspectRatio:false,animation:false,plugins:{legend:{display:false},tooltip:{callbacks:{label:c=>' '+fmt(c.parsed.y,2)+' % · '+(P.curve[c.dataIndex][1][0].length===7?'moyenne de '+mfr(P.curve[c.dataIndex][1][0]):dshort(P.curve[c.dataIndex][1][0]))}}},scales:{y:{ticks:{callback:v=>v+' %'}}}}}));
  if(document.getElementById(id+'L')&&P.slope&&P.slope.series)lineChart(id+'L',P.slope.series.map(x=>mfr(x[0])),[{label:P.slope.nom,data:P.slope.series.map(x=>x[1]),borderColor:'#a9cdf5',fill:{target:'origin',below:'rgba(255,45,45,.18)'}}],{unit:' pt',ticks:8});
}
function obAvScore(s){
  const n=s&&s.av&&s.av.score;
  return (n!=null&&n!==''&&Number.isFinite(Number(n)))?Number(n):null;
}
function obAvSort(a,b){
  const sa=obAvScore(a),sb=obAvScore(b);
  if(sa==null&&sb==null) return 0;
  if(sa==null) return 1;
  if(sb==null) return -1;
  return sb-sa;
}
function obEnsureRefNote(s){
  /* t344u : si la liste d'alternatives est vide, montrer la note de l'ETF de référence. */
  if(!s) return s;
  if((!s.apex10||s.apex10.note==null||s.apex10.display==='–')&&s.apex10_panier&&s.apex10_panier.note!=null){
    s.apex10=Object.assign({},s.apex10_panier,{detail:"Note de l'ETF de référence (aucune alternative UCITS dans la liste)."});
  }
  if((!s.av||s.av.score==null)&&s.av_panier&&s.av_panier.score!=null) s.av=s.av_panier;
  return s;
}
function renderSegments(el){
  (OB.segments||[]).forEach(obEnsureRefNote);
  const byKey=Object.fromEntries(OB.segments.map((s,i)=>[s.key,[s,i]]));
  const blocks=[];
  Object.entries(OB_GROUPS).forEach(([g,keys])=>{
    const L=keys.map(k=>byKey[k]).filter(Boolean);
    L.sort((a,b)=>obAvSort(a[0],b[0]));
    const S=L.map(x=>x[0]);
    if(!S.length&&!OBP.countries[g]) return;
    blocks.push({g,L,S,score:S.length===1?obAvScore(S[0]):null,marker:!S.length});
  });
  const multi=blocks.filter(b=>b.S.length>1);
  const scored=blocks.filter(b=>b.S.length===1).sort((a,b)=>{
    if(a.score==null&&b.score==null) return 0;
    if(a.score==null) return 1;
    if(b.score==null) return -1;
    return b.score-a.score;
  });
  const markers=blocks.filter(b=>!b.S.length);
  [...multi,...scored,...markers].forEach(({g,L,S})=>{
    if(!S.length){   // 17/11/2026 : segment retiré (aucun ETF disponible chez Revolut) -> taux du pays seuls, sans note APEX
      const P0=OBP.countries[g],F0=OB_FLAG[g];if(!P0&&!S.length)return;if(!P0)return;
      const c0=document.createElement('div');c0.className='card no-group ob-card';c0.dataset.cc=g;
      c0.innerHTML=`<h2>${F0?`<img class="flag-us" src="${F0[0]}" width="28" height="15" alt="Drapeau : ${F0[1]}">`:''}Obligations ${F0?F0[1]:g} · taux (repère de marché)</h2>
       <div class="desc acc-sum"><i>10 ans</i> <b>${pt(P0.last['10'][1])}</b>${P0.spread?` · <i>écart / Bund</i> <b>${fmt(P0.spread.last[1],2)} pt</b>`:''}${(P0.slope&&P0.slope.last&&P0.slope.last[1]!=null)?` · <i>${P0.slope.nom}</i> <b>${sign(P0.slope.last[1],2)} pt</b>`:''} · <i>sans note APEX</i></div>
       <div class="note">${(OB.removed_notes||{})[g]||"Aucun ETF de ce segment n'est disponible chez Revolut : segment retiré d'APEX (pas de note achat / vente). Les taux restent affichés comme repère de marché."}</div>
       ${obRates(g)}`;
      el.appendChild(c0);obRatesCharts(g);return;
    }
    const cnt=z=>S.filter(s=>s.av&&s.av.label&&s.av.label.includes(z)).length,P=OBP.countries[g],F=OB_FLAG[g];
    const c=document.createElement('div');c.className='card no-group ob-card';c.dataset.cc=g;
    const titre=g==='us'?'Obligations USA':g==='eu'?'Obligations zone euro, crédit et émergents':'Obligations '+F[1];
    const one=S.length===1?S[0]:null;
    const sum=(P?`<i>10 ans</i> <b>${pt(P.last['10'][1])}</b> · `:'')+(P&&P.spread?`<i>écart / Bund</i> <b>${fmt(P.spread.last[1],2)} pt</b> · `:'')+(P&&P.slope&&P.slope.last&&P.slope.last[1]!=null?`<i>${P.slope.nom}</i> <b>${sign(P.slope.last[1],2)} pt</b> · `:'')
      +(one?`<i>Achat / Vente</i> <b>${one.av.label} ${sign(one.av.score,0)}</b> · <i>Sentiment</i> <b>${one.sent.label} ${fmt(one.sent.value,0)}</b>`:`${S.length} segments · <i>Achat</i> <b>${cnt('Achat')}</b> · <i>Neutre</i> <b>${cnt('Neutre')}</b> · <i>Vente</i> <b>${cnt('Vente')}</b>`)+` · au ${dshort(S[0].date)}`;
    c.innerHTML=`<h2>${F?`<img class="flag-us" src="${F[0]}" width="28" height="15" alt="Drapeau : ${F[1]}">`:''}${titre} · ${P&&g!=='us'?'taux, ':''}sentiment et achat / vente</h2>
     <div class="desc acc-sum">${sum}</div>
     <div class="sr-mention"><span class="sr-date">Clôtures hebdomadaires au ${dshort(S[0].date)} (bougies clôturées uniquement)</span></div>
     <div class="sec-grid">${srHead('Segment · ETF de référence')}${L.map(([s,i])=>segTile(s,i)).join('')}</div>
     ${P?obRates(g):''}
     <div class="note ob-pea">Risques à surveiller : duration (sensibilité aux taux), devise${g==='kr'||g==='jp'||g==='au'||g==='us'||g==='gb'||g==='ch'?' (exposition non couverte sauf parts « couvertes »)':''} et crédit de l'émetteur ; détail par segment dans « ETF de référence + … ». Les ETF obligataires et les obligations ne sont pas éligibles au PEA : compte-titres uniquement.</div>
     <details class="ind-meth"><summary>Méthode et pondérations</summary>
      <p><b>Sentiment Peur / Euphorie (0-100).</b> ${OB.method_seg_sent}</p><p><b>Achat / Vente (−100 à +100).</b> ${OB.method_seg_av}${g!=='us'&&g!=='eu'?' Pour les pays, la valorisation est le niveau du taux 10 ans national classé depuis 2001. Les figures chartistes (tête-épaules, triangles, biseaux, etc.) sont lues sur le cours de l’ETF, relation inverse cours / rendement, confirmation à la clôture hebdomadaire (dossier figures_chartistes_obligations_weekly.txt).':''}</p>
      <p><b>Listes ETF UCITS.</b> ${OB.method_list}</p>
      <p>ETF de référence (signaux) : ${S.map(s=>s.nom+' = '+s.sym).join(' · ')}. ${g==='us'?'Depuis le 17/11/2026, les ETF américains (non vendus aux particuliers en Europe) sont remplacés comme référence par leur équivalent UCITS coté sur Xetra et disponible chez Revolut ; historique plus court et cotation en euros (exposition au dollar non couverte).':''}${g==='jp'||g==='au'?' L\'ETF de référence est coté en euros sur Xetra sans couverture : sa performance combine les taux locaux et le change.':''} Calcul reproductible avec <code>src/build_obligations.py</code>${P?' et <code>src/build_obpays.py</code>':''}.</p></details>
     <div class="src">Sources : ${lnk('https://finance.yahoo.com/','Yahoo Finance')} (clôtures hebdomadaires, fiches ETF), ${lnk('https://www.tradingview.com/','TradingView')} (symboles). Récupéré le ${S[0].retrieved.replace(' ',' à ')} (heure de Paris).</div>`;
    el.appendChild(c);srWire(c);if(P)obRatesCharts(g);
    c.querySelectorAll('.ob-det').forEach(dt=>dt.addEventListener('toggle',()=>{if(dt.open)obCharts(dt);}));
  });
}
