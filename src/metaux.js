/* ===== Onglet MÉTAUX PRÉCIEUX (or, argent, platine, palladium) ===== */
const MT=JSON.parse(document.getElementById('data10').textContent);
IND.metaux=MT.ind; AV.metaux=MT.av;
const MET_C={cc:'met',nom:'métaux précieux',bench:MT.bench,bench_nom:MT.bench_nom,bench_url:MT.bench_url,rows:MT.rows};
const MCOL={or:'#e6c27a',argent:'#c9d1d9',platine:'#a9cdf5',palladium:'#c9a7ff'};
const mUsd=v=>fmt(v,v<100?2:0)+' $',mEur=v=>fmt(v,v<100?2:0)+' €';
function mInstTip(r){
  if(!r) return '';
  const parts=[];
  if(r.kind_nom) parts.push(r.kind_nom+(r.hedged?' (couvert en euros)':''));
  if(r.isin) parts.push('ISIN '+r.isin);
  if(r.ter_note) parts.push(r.ter_note);
  else if(r.ter!=null) parts.push('TER '+String(r.ter).replace('.',',')+' %');
  if(r.currency) parts.push('cotation '+r.currency);
  if(r.note_revolut) parts.push(r.note_revolut);
  return parts.join(' · ').replace(/"/g,'&quot;');
}
function mRow(r,k,principal){
  const tip=mInstTip(r);
  const badge=principal?'<span class="fl-prin">principal</span>':'';
  return `<li class="fl-row"${r.tv?` data-pos-tv="${r.tv}"`:''}><div class="fl-id"${tip?` title="${tip}"`:''}><span class="fl-rk">${k+1}</span><b>${r.name}</b>${badge}${tvTag(r.tv)}${typeof posBadges==='function'?posBadges(r.tv):''}${typeof dispoBadge==='function'?dispoBadge(r.tv):''}</div>${listApexBar(Object.assign({},r,{forceApex100:true}))}</li>`;
}
function mList(C,s){
  const L=s.mlist,h=L.head;
  const rest=apexSortByNote(L.items||[]);
  const rows=[h?mRow(h,0,true):''].concat(rest.map((r,i)=>mRow(r,h?i+1:i,false))).join('');
  return `<details class="ind-meth sec-list"><summary>ETC principal + ${L.items.length} instruments</summary>
   ${h?'':`<div class="sr-ncm">ETC principal : aucun ETC de ce métal disponible chez Revolut (vérification du 17/11/2026)</div>`}
   <ol class="fl fl-pilot">${rows}</ol>
   ${L.list_note?`<div class="note">${L.list_note}</div>`:(L.items.length<5?`<div class="note">Seulement ${L.items.length} instrument${L.items.length>1?'s':''} retenu${L.items.length>1?'s':''} : les instruments non disponibles chez Revolut ont été retirés (règle APEX du 17/11/2026) ; les autres candidats n'avaient pas d'historique Yahoo exploitable ou de symbole TradingView vérifié.</div>`:'')}
   <div class="sec-d" style="text-align:left">L'ETC principal est la ligne 1 ; les autres instruments suivent par note /100 (métal au comptant, ETC physiques, puis jusqu'à deux minières). ${L.miner_note} Score minières = 50 % santé financière + 50 % croissance prévue (mêmes critères que les secteurs actions). Les ETC sont des titres de créance émis par une société dédiée et adossés à du métal stocké en coffre : ce ne sont pas des fonds UCITS. ETC, ETF de minières et minières étrangères ne sont pas éligibles au PEA (compte-titres). Risques : prix du métal en dollars, change EUR/USD (sauf part couverte), émetteur de l'ETC ; pour les minières, risques d'exploitation et de pays.</div>
  </details>`;
}
function renderMetaux(el){
  const C=MT.charts,P=C.prices,R=C.retrieved,RA=C.ratios,CL=C.cot_last,K=['or','argent','platine','palladium'],NM={or:'Or',argent:'Argent',platine:'Platine',palladium:'Palladium'};
  const yl=lnk('https://finance.yahoo.com/quote/GC%3DF/history/','Yahoo Finance (GC=F, SI=F, PL=F, PA=F)'),fl=(id,t)=>lnk('https://fred.stlouisfed.org/series/'+id,t||id);
  el.innerHTML=`
  <div class="card"><h2>Cours des métaux précieux · USD et EUR depuis 2000</h2>
   <div class="kpis">${K.map(k=>kpi(NM[k],mUsd(P[k].last_usd[1])+' · '+mEur(P[k].last_eur[1]),'clôture hebdo du '+dshort(P[k].last_usd[0]))).join('')}</div>
   <div class="mt-grid">${K.map(k=>`<div><div class="ind-subt">${NM[k]} · depuis ${dshort(P[k].first)}</div><div class="chart" style="height:220px"><canvas id="cMtP${k}"></canvas></div></div>`).join('')}</div>
   <div class="note">Contrats à terme continus Yahoo : les changements d'échéance ne sont pas ajustés, d'où de petits sauts possibles. Conversion en euros : EUR/USD hebdomadaire Yahoo (EURUSD=X) depuis 2003, taux de référence FRED DEXUSEU avant.</div>
   <div class="src">Sources : ${yl}, ${lnk('https://finance.yahoo.com/quote/EURUSD%3DX/history/','EURUSD=X')}, ${fl('DEXUSEU','FRED DEXUSEU')}. Récupéré le ${R.yahoo.replace(' ',' à ')} (heure de Paris).</div></div>

  <div class="card"><h2>Records historiques · plus hauts des clôtures hebdomadaires</h2>
   <div class="desc">Plus haut des clôtures hebdomadaires depuis 2000 (pas le record intrajournalier) et distance actuelle, en dollars et en euros.</div>
   <div class="kpis">${K.map(k=>kpi(NM[k]+' · record USD',mUsd(P[k].ath_usd[1]),dshort(P[k].ath_usd[0])+' · actuel '+sign(P[k].dd_usd,1)+' %')+kpi(NM[k]+' · record EUR',mEur(P[k].ath_eur[1]),dshort(P[k].ath_eur[0])+' · actuel '+sign(P[k].dd_eur,1)+' %')).join('')}</div>
   <div class="src">Calcul APEX sur les séries ci-dessus (${yl}). Récupéré le ${R.yahoo.replace(' ',' à ')}.</div></div>

  <div class="card"><h2>Ratios or / argent et or / platine</h2>
   <div class="desc">Nombre d'onces d'argent (ou de platine) pour une once d'or, clôtures hebdomadaires depuis 2000.</div>
   <div class="kpis">${kpi('Or / argent',fmt(RA.or_argent.last[1],1),'au '+dshort(RA.or_argent.last[0])+' · '+fmt(RA.or_argent.pct,0)+'ᵉ percentile depuis 2000')+kpi('Or / platine',fmt(RA.or_platine.last[1],2),'au '+dshort(RA.or_platine.last[0])+' · '+fmt(RA.or_platine.pct,0)+'ᵉ percentile depuis 2000')+kpi('Or / argent, extrêmes',fmt(RA.or_argent.min[1],1)+' → '+fmt(RA.or_argent.max[1],1),dshort(RA.or_argent.min[0])+' / '+dshort(RA.or_argent.max[0]))+kpi('Or / platine, extrêmes',fmt(RA.or_platine.min[1],2)+' → '+fmt(RA.or_platine.max[1],2),dshort(RA.or_platine.min[0])+' / '+dshort(RA.or_platine.max[0]))}</div>
   <div class="mt-grid"><div class="chart" style="height:230px"><canvas id="cMtRa"></canvas></div><div class="chart" style="height:230px"><canvas id="cMtRp"></canvas></div></div>
   <div class="note">Un ratio élevé signifie que l'or est cher relativement à l'autre métal ; ce n'est pas un signal de date.</div>
   <div class="src">Calcul APEX : cours de l'or ÷ cours de l'argent ou du platine (${yl}).</div></div>

  <div class="card"><h2>Or et taux réel américain à 10 ans</h2>
   <div class="desc">Cours de l'or (échelle de gauche, log) et rendement réel des TIPS 10 ans (échelle de droite, inversée), hebdomadaire depuis 2003.</div>
   <div class="kpis">${kpi('Or',mUsd(C.gold_real[C.gold_real.length-1][1]),'au '+dshort(C.gold_real[C.gold_real.length-1][0]))+kpi('Taux réel 10 ans US',pt(C.gold_real[C.gold_real.length-1][2]),'dernière valeur FRED de la semaine')}</div>
   <div class="chart" style="height:280px"><canvas id="cMtG"></canvas></div>
   <div class="note">Axe du taux réel inversé : historiquement, une baisse des taux réels accompagne souvent une hausse de l'or (coût d'opportunité plus faible), relation instable depuis 2022.</div>
   <div class="src">Sources : ${yl}, ${fl('DFII10','FRED DFII10')}. Récupéré le ${R.fred_tips.replace(' ',' à ')}.</div></div>

  <div class="card"><h2>Positions CFTC · gérants de fonds (managed money)</h2>
   <div class="desc">Position nette (acheteurs − vendeurs) des « managed money » sur les contrats à terme américains, en % de l'intérêt ouvert, hebdomadaire depuis juin 2006.</div>
   <div class="kpis">${K.map(k=>kpi(NM[k],sign(CL[k].net,1)+' % de l\'OI','rapport du '+dshort(CL[k].date)+' · '+fmt(CL[k].pct,0)+'ᵉ percentile sur 3 ans')).join('')}</div>
   <div class="chart" style="height:280px"><canvas id="cMtC"></canvas></div>
   <div class="note">Rapport « Disaggregated Futures Only » : or et argent sur COMEX, platine et palladium sur NYMEX. Position mesurée le mardi, publiée le vendredi suivant.</div>
   <div class="src">Source : ${lnk('https://www.cftc.gov/MarketReports/CommitmentsofTraders/HistoricalCompressed/index.htm','CFTC, historique Commitments of Traders')}. Récupéré le ${R.cftc.replace(' ',' à ')} (heure de Paris).</div></div>

  <div class="card"><h2>Réserves d'or des banques centrales</h2>
   <div class="kpis">${na('Achats nets des banques centrales','non récupéré')}</div>
   <div class="note">Non récupéré : les statistiques de référence (World Gold Council, compilées à partir du FMI) ne se téléchargent qu'après inscription ; aucune source gratuite et automatisable jugée fiable n'a été retenue. Aucun chiffre n'est donc affiché.</div></div>

  <div class="card"><h2>Fiscalité française des métaux précieux · rappel</h2>
   <div class="desc">Note courte, vérifiée le 15 novembre 2026. Ne remplace pas un avis fiscal.</div>
   <ul class="mt-tax">
    <li><b>Or, argent, platine physiques (lingots, pièces) :</b> taxe forfaitaire de 11 % du prix de vente + 0,5 % de CRDS, soit 11,5 %, due même en cas de perte.</li>
    <li><b>Option pour le régime des plus-values sur biens meubles</b> si l'on justifie la date et le prix d'achat : seule la plus-value est taxée, avec un abattement de 5 % par année de détention au-delà de la deuxième, soit une exonération totale après 22 ans. Taux global indiqué pour 2026 : 36,2 % (19 % d'impôt + 17,2 % de prélèvements sociaux), selon une source privée.</li>
    <li><b>Palladium :</b> le ministère cite l'argent, le platine et l'or comme métaux précieux ; le palladium n'y figure pas. Régime à confirmer auprès de l'administration.</li>
    <li><b>ETC, ETF et actions de minières en compte-titres :</b> fiscalité des valeurs mobilières (prélèvement forfaitaire unique), pas la taxe forfaitaire. Non éligibles au PEA.</li>
   </ul>
   <div class="src">Sources : ${lnk('https://www.economie.gouv.fr/particuliers/vente-objet-precieux-fiscalite-taxe','economie.gouv.fr, Vente d\'objets précieux : quelle fiscalité ?')} ; ${lnk('https://bofip.impots.gouv.fr/bofip/3721-PGP.html/identifiant%3DBOI-RPPM-PVBMC-20-20140401','BOFiP BOI-RPPM-PVBMC-20 (articles 150 VI à 150 VM du CGI)')} ; ${lnk('https://www.service-public.gouv.fr/particuliers/vosdroits/R17176','service-public.gouv.fr, formulaire 2091-SD')} ; taux 2026 du régime des plus-values : ${lnk('https://support.majors.finance/ressources/or-metaux-precieux-fiscalite-cgp.html','Majors, 17 sept. 2026 (source privée)')}. Consulté le 15 nov. 2026.</div></div>`;
  const ml=p=>p[0].slice(0,4)===p[0]?p[0]:dshort(p[0]);
  K.forEach(k=>{const m=merge([P[k].usd,P[k].eur]);lineChart('cMtP'+k,m.labels.map(dshort),[{label:'USD',data:m.data[0],borderColor:MCOL[k]},{label:'EUR',data:m.data[1],borderColor:'#5b8def',borderWidth:1.2}],{log:true,dec:2,ticks:6});});
  lineChart('cMtRa',RA.or_argent.series.map(x=>dshort(x[0])),[{label:'Or / argent',data:RA.or_argent.series.map(x=>x[1]),borderColor:'#c9d1d9'}],{dec:1,ticks:6});
  lineChart('cMtRp',RA.or_platine.series.map(x=>dshort(x[0])),[{label:'Or / platine',data:RA.or_platine.series.map(x=>x[1]),borderColor:'#a9cdf5'}],{dec:2,ticks:6});
  const G=C.gold_real;
  charts.push(new Chart(document.getElementById('cMtG'),{type:'line',data:{labels:G.map(x=>dshort(x[0])),datasets:[{label:'Or (USD)',data:G.map(x=>x[1]),borderColor:'#e6c27a',yAxisID:'y',pointRadius:0,borderWidth:1.6},{label:'Taux réel 10 ans US (%)',data:G.map(x=>x[2]),borderColor:'#7fd1a8',yAxisID:'y1',pointRadius:0,borderWidth:1.2}]},
    options:{maintainAspectRatio:false,animation:false,interaction:{mode:'index',intersect:false},scales:{x:{ticks:{maxTicksLimit:8}},y:{type:'logarithmic',position:'left',ticks:{callback:v=>{const l=Math.log10(v);return Math.abs(l-Math.round(l))<1e-9||[500,2000,5000].includes(v)?v.toLocaleString('fr-FR'):''}}},y1:{position:'right',reverse:true,grid:{display:false},ticks:{callback:v=>v+' %'}}}}}));
  const cm=merge(K.map(k=>C.cot[k]));
  lineChart('cMtC',cm.labels.map(dshort),K.map((k,j)=>({label:NM[k],data:cm.data[j],borderColor:MCOL[k],borderWidth:1.3})),{unit:' %',dec:1,ticks:8});
  // section Métaux (lignes AV / S)
  const S=apexSortByNote(MT.rows),cnt=z=>S.filter(s=>s.av&&s.av.label&&s.av.label.includes(z)).length,d=S[0].date;
  const hi=S.reduce((a,b)=>b.sent.value>a.sent.value?b:a),lo=S.reduce((a,b)=>b.sent.value<a.sent.value?b:a);
  const stMt=(typeof sectionApexAvg==='function')?sectionApexAvg('metaux'):null;
  const a10=(stMt&&stMt.apex10)||null;
  const disp=a10?(a10.display!=null?String(a10.display):(a10.note!=null?String(a10.note):'')):'';
  const apexTag=a10&&disp?`<span class="js-apex10" hidden data-display="${disp}" data-hex="${a10.hex||''}" data-note="${a10.note!=null?a10.note:disp}" data-scale="100"></span>`:'';
  const c=document.createElement('div');c.className='card no-group met-card';
  c.innerHTML=`<h2>Métaux · sentiment et achat / vente</h2>
   <div class="desc acc-sum">${apexTag}4 métaux · au ${dshort(d)} · <i>Achat</i> <b>${cnt('Achat')}</b> · <i>Neutre</i> <b>${cnt('Neutre')}</b> · <i>Vente</i> <b>${cnt('Vente')}</b> · <i>sentiment max</i> <b>${hi.nom} ${fmt(hi.sent.value,0)}</b> · <i>min</i> <b>${lo.nom} ${fmt(lo.sent.value,0)}</b></div>
   <div class="sec-grid">${srHead('Métal · contrat de référence', 100)}${S.map(s=>pTile(MET_C,s,MT.rows.indexOf(s))).join('')}</div>
   <details class="ind-meth"><summary>Méthode et pondérations</summary>
    <p><b>Sentiment Peur / Euphorie (0-100).</b> ${apexPlain(SEC.method_sent.replace(/S&P 500/g,'DBC'))}</p>
    <p><b>Achat / Vente (−100 à +100).</b> ${apexPlain(SEC.method_av.replace(/S&P 500/g,'DBC'))}</p>
    <p>Mêmes formules que les secteurs actions, appliquées aux contrats à terme continus Yahoo (GC=F or COMEX, SI=F argent COMEX, PL=F platine NYMEX, PA=F palladium NYMEX) pour les barres Achat/Vente et Sentiment de chaque ligne. Référence de force relative : DBC (panier diversifié de matières premières). <b>Note APEX /100 de chaque métal</b> : moyenne (arrondie au point) des notes /100 des instruments visibles dans le bouton « ETC principal + N instruments » (ETC physiques, métal au comptant, minières) ; les titres sans note sont exclus. Calcul reproductible avec <code>src/fetch_metaux.py</code>, <code>src/fetch_metaux2.py</code> et <code>src/build_metaux.py</code>.</p></details>
   <div class="src">Sources : ${yl}, ${lnk(MT.bench_url,MT.bench_nom)}, ${lnk('https://www.tradingview.com/','TradingView')} (symboles vérifiés). Calcul le ${MT.generated.replace(' ',' à ')} (heure de Paris).</div>`;
  el.prepend(c);srWire(c);
  c.querySelectorAll('.sec-det').forEach(dt=>dt.addEventListener('toggle',()=>{if(dt.open)pCharts(dt);}));
}
