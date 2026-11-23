/* ===== Compteur ACHAT / VENTE (aiguille en demi-cercle, score −100 … +100) ===== */
const AV=JSON.parse(document.getElementById('data4').textContent);
const AVZ=[[-100,-60,'#ff2d2d','Vente forte'],[-60,-20,'#ff9a1f','Vente'],[-20,20,'#e6c27a','Neutre'],[20,60,'#22c55e','Achat'],[60,100,'#00e5ff','Achat fort']];
const avPos=s=>s==null?50:(Math.max(-100,Math.min(100,s))+100)/2;   // −100 → 0 % (gauche), +100 → 100 % (droite)
const avCol=(s,a=1)=>gcol(avPos(s),a);                   // même dégradé que la barre de sentiment
const APEX10_ROUGE={w1:1,w3:1,w5:1,deb_5:1,new1:1,bear_135:1,a:1,fin_a:1,b:1};
const APEX10_VERTE={fin_2:1,fin_2_conf:1,fin_4:1,fin_4_conf:1,fin_c:1,fin_c_conf:1,c:1,c_mid:1};
const APEX10_BONUS05={fin_2:1,fin_4:1,fin_c:1,c:1,c_mid:1};
const APEX10_BONUS10={fin_2_conf:1,fin_4_conf:1,fin_c_conf:1};
function fmtApex10(n){
  if(n==null||n==='') return '–';
  const x=Math.round(Number(n));
  return String(x);
}
function apex10EllKey(ell){
  if(!ell) return null;
  return (typeof ell==='string')?ell:(ell.key||null);
}
function apex10EllFiable(ell){
  return !!(ell && typeof ell==='object' && (ell.manuel||ell.override||ell.source==='manuel'));
}
function apex10Compute(av,fond,ell,divergence){
  /* t320u / t337u : la note APEX /100 vient du JSON, pas d'un recalcul JS.
     Conservé uniquement comme filet de sécurité, déjà converti sur 100. */
  if(av==null||av==='') return {note:null,display:'–',hex:null,pos:null,cap:'',flag:null};
  const lo=-60,hi=60,x=Math.max(lo,Math.min(hi,Number(av)));
  const timing=(x-lo)/(hi-lo)*100;
  let brut=timing;
  if(fond!=null&&fond!=='') brut=0.5*timing+0.5*Number(fond);
  let n=brut; const cap=[];
  if(fond!=null&&fond!==''&&Number(fond)<40){n=n-20*(40-Number(fond))/40;cap.push('fondamental');}
  const key=apex10EllKey(ell);
  const fiable=apex10EllFiable(ell);
  if(key&&APEX10_ROUGE[key]){n=Math.min(n,40);cap.push('elliott');}
  if(fiable){
    if(key&&APEX10_BONUS05[key]){n=n+5;cap.push('bonus');}
    else if(key&&APEX10_BONUS10[key]){n=n+10;cap.push('bonus');}
  }
  n=Math.max(0,Math.min(100,Math.round(n)));
  if(n>=80){
    const avFort=Number(av)>=60;
    const divOk=divergence!=null&&Number(divergence)>0;
    const ellOk=fiable&&key&&APEX10_VERTE[key];
    if(!(avFort&&(divOk||ellOk))){n=75;cap.push('cyan');}
  }
  return {note:n,display:fmtApex10(n),pos:n,hex:(typeof apexHexOf==='function')?apexHexOf(n):null,flag:(typeof apexFlagTV==='function')?apexFlagTV(n):null,cap:cap.join('+')};
}
function apex10Col(a){
  if(!a||a.note==null) return '#8a8a8a';
  if(typeof apexHexOf==='function') return apexHexOf(a.note);
  if(a.hex) return a.hex;
  return (typeof gcol==='function')?gcol(a.pos!=null?a.pos:a.note):'#e6c27a';
}
function apexNoteHTML(a){
  if(!a||a.note==null||a.display==='–') return `<div class="apex10 apex10-na"><b>–</b></div>`;
  const col=apex10Col(a);
  return `<div class="apex10"><b style="color:${col};text-shadow:0 0 16px ${col}80">${a.display}</b><small style="color:${col}">/100</small></div>`;
}
/* Barre fusionnée : une seule barre dégradée, échelle Achat / Vente (−100 → +100) au-dessus, Sentiment (0 → 100) en dessous.
   Curseur blanc = Achat / Vente, curseur gris (rond) = Sentiment. Deux échelles linéaires distinctes sur la même largeur. */
function dualBar(sv,sl,av,al,cls='',compact=false,apex){
  const ap=avPos(av),sp=Math.max(0,Math.min(100,sv)),T=[-60,-20,20,60];
  const bar=`<div class="db ${cls}" role="img" aria-label="Achat / Vente ${sign(av,0)} (${al}) sur −100 à +100 ; sentiment ${fmt(sv,0)} (${sl}) sur 0 à 100">
   ${compact?`<div class="db-tk db-tk1"><i class="db-e0">−100 · Vente</i>${T.map(v=>`<i class="db-t${Math.abs(v)}" style="left:${avPos(v)}%">${v>0?'+':'−'}${Math.abs(v)}</i>`).join('')}<i style="left:50%">0</i><i class="db-e1">Achat · +100</i></div>`
   :`<div class="db-sc db-top"><span>−100 · Vente</span><span>Neutre · 0</span><span>Achat · +100</span></div>
   <div class="db-tk">${T.map(v=>`<i style="left:${avPos(v)}%">${v>0?'+':'−'}${Math.abs(v)}</i>`).join('')}</div>`}
   <div class="db-g"><div class="ind-bar"></div>${T.map(v=>`<i class="av-tick" style="left:${avPos(v)}%"></i>`).join('')}<div class="db-mid"></div>
    <div class="db-cur db-s" style="left:${sp}%;color:${gmir(sp)}" data-p="${sp}" title="Sentiment ${fmt(sv,0)} · ${sl} (couleur du dégradé miroir à cette position)">S</div><div class="db-cur db-a" style="left:${ap}%;color:${gsol(ap)}" data-p="${ap}" title="Achat / Vente ${sign(av,0)} · ${al} (couleur de la barre à cette position)">AV</div></div>
   <div class="db-sc db-bot"><span>0 · Peur extrême</span><span>Neutre</span><span>Euphorie · 100</span></div>
   ${compact?`<div class="db-leg"><span><i class="db-dot db-a" style="color:${gsol(ap)}">AV</i>Achat/Vente <b class="sc-t" style="color:${gsol(ap)}">${sign(av,0)} ${al}</b></span><span><i class="db-dot db-s" style="color:${gmir(sp)}">S</i>Sentiment <b class="sc-t" style="color:${gmir(sp)}">${fmt(sv,0)} ${sl}</b></span></div>`:''}
  </div>`;
  if(apex===undefined) return bar;
  return `<div class="apex-block">${apexNoteHTML(apex)}<div class="apex-rest">${bar}</div></div>`;
}
function avBar(score,mn,mx,avg,cls){   // barre horizontale −100 … +100, même rendu que la jauge de sentiment
  const p=v=>avPos(v)+'%';
  return `<div class="${cls}" role="img" aria-label="Achat / Vente : ${fmt(score,0)} sur une échelle de −100 à +100">
    ${mn!=null?`<div class="ind-range" style="left:${p(mn)};width:${Math.max(.5,avPos(mx)-avPos(mn))}%" title="plage 1 an"></div>`:''}
    <div class="ind-bar"></div>${[-60,-20,20,60].map(v=>`<i class="av-tick" style="left:${p(v)}"></i>`).join('')}
    ${avg!=null?`<div class="ind-avg" style="left:${p(avg)}" title="moyenne 1 an"></div>`:''}
    <div class="ind-cur" style="left:${p(score)};box-shadow:0 0 10px ${avCol(score,.9)}"></div></div>`;
}
let avChart=null;
function renderAchatVente(tabId){
  const box=document.getElementById('av'),g=AV[tabId];
  if(avChart){avChart.destroy();const i=charts.indexOf(avChart);if(i>=0)charts.splice(i,1);avChart=null;}
  if(!g){box.innerHTML='';return;}
  const cmax=Math.max(...g.components.map(c=>Math.abs(c.contrib||0)),1);
  const rows=g.components.map(c=>{const n=c.note;return `<div class="av-c"><div class="av-cl"><span>${c.nom}</span><b style="color:${n==null?'#888':avCol(n)}">${n==null?(c.facultatif?'non comptée':'n.d.'):sign(n,0)}</b></div>
    <div class="av-cb"><div class="av-mid"></div>${n==null?'':`<i style="${n>=0?'left:50%':'right:50%'};width:${Math.abs(n)/2}%;background:${avCol(n)}"></i>`}</div>
    <div class="av-cd">valeur ${c.valeur} · poids ${pw(c.poids)} % · contribution <b>${c.contrib==null?(c.facultatif?'non comptée':'retirée'):sign(c.contrib,1)}</b></div></div>`;}).join('');
  box.innerHTML=`<div class="card av-card"><h2>Achat / Vente</h2>
   <div class="av-sens">${g.sens}</div>
   <div class="av-val"><span style="color:${avCol(g.score)};text-shadow:0 0 14px ${avCol(g.score,.55)}">${sign(g.score,0)}</span><em style="color:${avCol(g.score)}">${g.label}</em></div>
   <div class="ind-date">score de −100 à +100 · au ${dshort(g.date)} (dernière bougie hebdomadaire clôturée)</div>
   ${avBar(g.score,g.min[1],g.max[1],g.avg,'ind-gauge av-gauge')}
   <div class="ind-scale av-scale"><span>−100 · Vente</span><span>Neutre · 0</span><span>Achat · +100</span></div>
   <div class="ind-legend"><i class="lg-avg"></i> moyenne · <i class="lg-rng"></i> plage min–max 1 an · <i class="lg-cur"></i> score actuel</div>
   <div class="ind-stats" style="margin-top:8px"><div><span>Moyenne 12 mois</span><b>${sign(g.avg,0)}</b></div><div><span>Min</span><b>${sign(g.min[1],0)}</b><small>${dshort(g.min[0])}</small></div><div><span>Max</span><b>${sign(g.max[1],0)}</b><small>${dshort(g.max[0])}</small></div></div>
   <div class="ind-spark" style="height:100px"><canvas id="cAv"></canvas></div>
   <div class="ind-sub"><div class="ind-subt">Composantes (note de −100 à +100)</div>${rows}</div>
   ${g.missing.length?`<div class="note">Composante(s) retirée(s) faute de donnée : ${g.missing.join(', ')}. Le score est recalculé sur les autres.</div>`:''}
   <details class="ind-meth"><summary>Méthode</summary><p>${apexPlain(g.method)}</p>
     <p>Score = Σ (poids × note) ÷ Σ (poids des composantes disponibles). Zones : ≤ −60 vente forte · −60 à −20 vente · −20 à +20 neutre · +20 à +60 achat · ≥ +60 achat fort.</p>
     <ul>${g.components.map(c=>`<li><b>${c.nom}</b> (${pw(c.poids)} %) : ${c.regle}</li>`).join('')}</ul>
     <p>Sources : ${g.sources.map(s=>lnk(s[1],s[0])).join(' · ')}. Calcul reproductible avec <code>src/build_achatvente.py</code>.</p></details>

  </div>`;
  const h=g.history;
  avChart=new Chart(document.getElementById('cAv'),{type:'bar',data:{labels:h.map(x=>dshort(x[0])),datasets:[{data:h.map(x=>x[1]),backgroundColor:h.map(x=>avCol(x[1])),borderWidth:0,barPercentage:1,categoryPercentage:.9}]},
    options:{maintainAspectRatio:false,animation:false,plugins:{legend:{display:false},tooltip:{callbacks:{label:c=>' '+sign(c.parsed.y,1)+' · '+(AVZ.find(z=>c.parsed.y<=z[1])||AVZ[4])[3]}}},scales:{x:{ticks:{maxTicksLimit:4,maxRotation:0,font:{size:10}},grid:{display:false}},y:{min:-100,max:100,ticks:{stepSize:50,font:{size:10}}}}}});
  charts.push(avChart);
}

/* Moyenne des notes /100 affichées d'une section (bandeau NOTE APEX), 23/11/2026 */
function labAv(s){
  s=Number(s);
  return s<=-60?'Vente forte':s<=-20?'Vente':s<20?'Neutre':s<60?'Achat':'Achat fort';
}
function labS(v){
  v=Number(v);
  return v<25?'Peur extrême':v<45?'Peur':v<=55?'Neutre':v<=75?'Avidité':'Euphorie';
}
function apex10FromAvg(notes){
  const xs=(notes||[]).map(Number).filter(Number.isFinite);
  if(!xs.length) return null;
  const n=Math.max(0,Math.min(100,Math.round(xs.reduce((a,b)=>a+b,0)/xs.length)));
  const pos=n;
  return {
    note:n, display:fmtApex10(n), pos,
    hex:(typeof apexHexOf==='function')?apexHexOf(n):((typeof gcol==='function')?gcol(pos):null),
    flag:(typeof apexFlagTV==='function')?apexFlagTV(n):null,
    cap:'moyenne', n_moy:xs.length,
    detail:'Moyenne des notes /100 affichées des actifs de la section, arrondie au point.'
  };
}
function meanNum(xs){
  const a=(xs||[]).map(Number).filter(Number.isFinite);
  if(!a.length) return null;
  return a.reduce((x,y)=>x+y,0)/a.length;
}
function assetApexNote(o){
  if(!o) return null;
  const a=o.apex10;
  if(a&&a.note!=null&&a.display!=='–') return Number(a.note);
  return null;
}
function sectionApexItems(tabId){
  const out=[];
  const push=(o,opts)=>{
    if(!o) return;
    let note=assetApexNote(o);
    const av=o.av&&o.av.score!=null&&o.av.score!==''?Number(o.av.score):null;
    let se=null;
    if(o.sent&&o.sent.value!=null&&o.sent.value!=='') se=Number(o.sent.value);
    else if(o.ind&&o.ind.value!=null) se=Number(o.ind.value);
    if(false&&note==null&&opts&&opts.fromAv){ /* t320u : plus de calcul de note côté JS */
      const r=null;
      if(r&&r.note!=null) note=r.note;
    }
    if(note==null) return;
    out.push({note,av,sent:se,name:o.nom||o.name||o.code||''});
  };
  if(tabId==='actions'&&typeof SEC!=='undefined') (SEC.sectors||[]).forEach(s=>push(s));
  else if(tabId==='obligations'&&typeof OB!=='undefined') (OB.segments||[]).forEach(s=>push(s));
  else if(tabId==='metaux'&&typeof MT!=='undefined') (MT.rows||[]).forEach(s=>push(s));
  else if(tabId==='energie'&&typeof T2!=='undefined'){
    ((T2.energie&&T2.energie.assets)||[]).forEach(s=>{if(s&&s.ok&&!s.repere) push(s);});
  }
  else if(tabId==='crypto'&&typeof T2!=='undefined'){
    const F=T2.crypto&&T2.crypto.fiches;
    ((F&&F.assets)||[]).forEach(s=>push(s));
  }
  else if(tabId==='liquidites'&&typeof T2!=='undefined'){
    ((T2.liquidites&&T2.liquidites.fx&&T2.liquidites.fx.assets)||[]).forEach(s=>push(s,{fromAv:true}));
  }
  return out;
}
function bakedSectionApex(tabId){
  if(tabId==='actions'&&typeof SEC!=='undefined'&&SEC.apex10&&SEC.apex10.note!=null) return SEC.apex10;
  if(tabId==='obligations'&&typeof OB!=='undefined'&&OB.apex10&&OB.apex10.note!=null) return OB.apex10;
  if(tabId==='metaux'&&typeof MT!=='undefined'&&MT.apex10&&MT.apex10.note!=null) return MT.apex10;
  if(tabId==='energie'&&typeof T2!=='undefined'&&T2.energie&&T2.energie.apex10&&T2.energie.apex10.note!=null) return T2.energie.apex10;
  if(tabId==='crypto'&&typeof T2!=='undefined'){
    const F=T2.crypto&&T2.crypto.fiches;
    if(F&&F.apex10&&F.apex10.note!=null) return F.apex10;
  }
  if(tabId==='liquidites'){
    const L=(typeof T2!=='undefined'&&T2.liquidites)||{};
    if(L.fx&&L.fx.apex10&&L.fx.apex10.note!=null) return L.fx.apex10;
    if(typeof AV!=='undefined'&&AV.liquidites&&AV.liquidites.apex10&&AV.liquidites.apex10.note!=null) return AV.liquidites.apex10;
  }
  if(tabId==='immobilier'&&typeof AV!=='undefined'&&AV.immobilier&&AV.immobilier.apex10&&AV.immobilier.apex10.note!=null) return AV.immobilier.apex10;
  return null;
}
function sectionApexAvg(tabId){
  const items=sectionApexItems(tabId);
  const notes=items.map(x=>x.note).filter(n=>n!=null&&Number.isFinite(n));
  const av=meanNum(items.map(x=>x.av));
  const se=meanNum(items.map(x=>x.sent));
  const baked=bakedSectionApex(tabId);
  const apex=baked||apex10FromAvg(notes);
  if(!apex) return null;
  return {
    apex10:apex,
    av:av==null?null:{score:av,label:labAv(av)},
    sent:se==null?null:{value:se,label:labS(se)},
    n:baked&&baked.n_moy!=null?baked.n_moy:notes.length
  };
}
function countryApexAvg(C){
  if(!C) return null;
  const S=(C.rows||[]).filter(s=>s&&s.covered&&s.apex10&&s.apex10.note!=null&&s.apex10.display!=='–');
  const notes=S.map(s=>Number(s.apex10.note)).filter(Number.isFinite);
  if(!notes.length) return null;
  const av=meanNum(S.map(s=>s.av&&s.av.score));
  const se=meanNum(S.map(s=>s.sent&&s.sent.value));
  return {
    apex10:apex10FromAvg(notes),
    av:av==null?null:{score:av,label:labAv(av)},
    sent:se==null?null:{value:se,label:labS(se)},
    n:notes.length
  };
}

/* Tri durable d'une liste d'actifs : note /100 décroissante, à égalité AV décroissant, sans note en bas, ordre actuel sinon. */
function apexNoteOf(o){
  if(!o) return null;
  const a=o.apex10;
  if(a&&a.note!=null&&a.display!=='–') return Number(a.note);
  if(typeof APEX_BARS!=='undefined'&&APEX_BARS.bars){
    const key=o.tv||o.yahoo||o.ticker||o.sym;
    const b=key&&APEX_BARS.bars[key];
    if(b&&b.apex10&&b.apex10.note!=null&&b.apex10.display!=='–') return Number(b.apex10.note);
  }
  if(o.av&&o.av.score!=null&&o.av.apex10&&o.av.apex10.note!=null) return Number(o.av.apex10.note);
  if(false&&o.av&&o.av.score!=null){ /* t320u : la note vient du JSON, pas d'un recalcul JS */
    const r=null;
    if(r&&r.note!=null) return Number(r.note);
  }
  return null;
}
function apexAvOf(o){
  if(!o) return null;
  if(o.av&&o.av.score!=null&&o.av.score!=='') return Number(o.av.score);
  if(typeof APEX_BARS!=='undefined'&&APEX_BARS.bars){
    const key=o.tv||o.yahoo||o.ticker||o.sym;
    const b=key&&APEX_BARS.bars[key];
    if(b&&b.av&&b.av.score!=null) return Number(b.av.score);
  }
  return null;
}
function apexSortByNote(arr){
  const src=arr||[];
  return src.map((item,i)=>({item,i,note:apexNoteOf(item),av:apexAvOf(item)}))
    .sort((a,b)=>{
      const an=a.note!=null&&Number.isFinite(a.note), bn=b.note!=null&&Number.isFinite(b.note);
      if(an!==bn) return an?-1:1;
      if(an&&bn&&a.note!==b.note) return b.note-a.note;
      const aa=a.av!=null&&Number.isFinite(a.av), ba=b.av!=null&&Number.isFinite(b.av);
      if(aa!==ba) return aa?-1:1;
      if(aa&&ba&&a.av!==b.av) return b.av-a.av;
      return a.i-b.i;
    })
    .map(x=>x.item);
}


/* ===== Pilote APEX ACHAT (accumulation de points) : Actions USA Communication uniquement ===== */
const PILOT=(function(){
  const el=document.getElementById('dataPilot');
  if(!el||!el.textContent||el.textContent.trim()==='null') return null;
  try{const d=JSON.parse(el.textContent);return (d&&d.pilot)?d:null;}catch(e){return null;}
})();
function isPilotSector(sym){return !!(PILOT&&PILOT.secteur_sym&&sym===PILOT.secteur_sym);}
function pilotRec(tv){return (PILOT&&PILOT.by_tv&&tv)?PILOT.by_tv[tv]:null;}
function pilotScale(){
  const mn=(PILOT&&PILOT.scale&&PILOT.scale.min!=null)?PILOT.scale.min:-50;
  const mx=(PILOT&&PILOT.scale&&PILOT.scale.max!=null)?PILOT.scale.max:270;
  return {min:mn,max:mx};
}
/* 4 tranches égales de 80 pts sur [-50, 270] ; borne inférieure incluse, 270 inclus dans le cyan */
const PILOT_BANDS=[
  {id:'rouge',de:-50,a:30,hex:'#ff2d2d'},
  {id:'jaune',de:30,a:110,hex:'#ffd400'},
  {id:'vert',de:110,a:190,hex:'#22c55e'},
  {id:'cyan',de:190,a:270,hex:'#00e5ff'}
];
function pilotBand(total){
  const t=Number(total);
  if(!Number.isFinite(t)) return {id:'',hex:'#8a8a8a'};
  if(t>=270) return PILOT_BANDS[3];
  if(t<-50) return PILOT_BANDS[0];
  return PILOT_BANDS.find(b=>t>=b.de&&t<b.a)||PILOT_BANDS[3];
}
function pilotPos(total){
  const {min:mn,max:mx}=pilotScale();
  const t=Number(total);
  if(!Number.isFinite(t)) return 50;
  return Math.max(0,Math.min(100,(t-mn)/(mx-mn)*100));
}
function pilotHex(rec){return pilotBand(rec&&rec.total).hex;}
function pilotNoteHTML(rec){
  if(!rec||rec.total==null) return '';
  const mx=rec.total_max!=null?rec.total_max:pilotScale().max;
  return `<div class="apex10 apex10-pilot" style="color:${pilotHex(rec)}"><b>${rec.total}</b><small>/ ${mx}</small></div>`;
}
function pilotBrk(rec){
  if(!rec||!rec.ligne) return '';
  return `<div class="pilot-brk">${rec.ligne}</div>`;
}
function pilotSpark(fg){
  const s=(fg&&fg.series)||[];
  if(s.length<2) return '';
  const vals=s.map(x=>x[1]).filter(Number.isFinite);
  if(!vals.length) return '';
  const lo=Math.min(0,...vals), hi=Math.max(100,...vals);
  const w=120,h=22,p=1;
  const pts=vals.map((v,i)=>{
    const x=p+i*(w-2*p)/Math.max(1,vals.length-1);
    const y=h-p-((v-lo)/Math.max(1e-6,hi-lo))*(h-2*p);
    return x.toFixed(1)+','+y.toFixed(1);
  }).join(' ');
  return `<svg class="pilot-spark" viewBox="0 0 ${w} ${h}" width="${w}" height="${h}" aria-hidden="true"><polyline fill="none" stroke="currentColor" stroke-width="1.2" points="${pts}"/></svg>`;
}
function dualBarPilot(rec, compact){
  const fg=(PILOT&&PILOT.fear_greed)||{};
  const total=rec&&rec.total!=null?rec.total:null;
  const {min:mn,max:mx}=pilotScale();
  const ap=pilotPos(total);
  const sv=Number(fg.value);
  const sp=Number.isFinite(sv)?Math.max(0,Math.min(100,sv)):null;
  const ticks=[-50,30,110,190,270];
  const pos=v=>((v-mn)/(mx-mn))*100;
  const hex=pilotHex(rec);
  const sl=fg.label||'–';
  const scol=sp!=null?gmir(sp):'#888';
  const tickHTML=ticks.map((v,i)=>{
    const edge=i===0?' db-e0':(i===ticks.length-1?' db-e1':'');
    const left=i===ticks.length-1?'':` style="left:${pos(v)}%"`;
    const lab=v<0?('−'+Math.abs(v)):String(v);
    return `<i class="${edge.trim()}"${left}>${lab}</i>`;
  }).join('');
  /* Même dégradé et traits de repère que les sections non pilotes ; une seule barre, deux curseurs. */
  const bandTicks=[20,40,60,80].map(p=>`<i class="av-tick" style="left:${p}%"></i>`).join('');
  const totTxt=total==null?'–':String(total);
  const fgTxt=Number.isFinite(sv)?fmt(sv,1):'–';
  const bar=`<div class="db db-pilot ${compact?'db-sm':''}" role="img" aria-label="Score APEX ${totTxt} sur ${mn} à ${mx} ; Fear & Greed CNN ${fgTxt} (${sl}) sur 0 à 100">
   <div class="db-tk db-tk1">${tickHTML}</div>
   <div class="db-g"><div class="ind-bar"></div>${bandTicks}
    ${sp!=null?`<div class="db-cur db-s" style="left:${sp}%;color:${scol}" data-p="${sp}" title="S = CNN Fear & Greed Index ${fgTxt} · ${sl}">S</div>`:''}
    ${total!=null?`<div class="db-cur db-a" style="left:${ap}%;color:${hex}" data-p="${ap.toFixed(1)}" title="AV = score APEX ${totTxt} / ${mx}">AV</div>`:''}
   </div>
   <div class="db-sc db-bot"><span>0 · Peur extrême</span><span>Euphorie · 100</span></div>
   <div class="db-leg pilot-leg"><span><i class="db-dot db-a" style="color:${hex}">AV</i>Total <b class="sc-t" style="color:${hex}">${totTxt}/${mx}</b></span><span><i class="db-dot db-s" style="color:${scol}">S</i>Fear &amp; Greed <b class="sc-t" style="color:${scol}">${fgTxt} ${sl}</b></span>${pilotSpark(fg)}</div>
  </div>`;
  return `<div class="apex-block apex-block-pilot${compact?' apex-block-line':''}">${pilotNoteHTML(rec)}<div class="apex-rest">${bar}${pilotBrk(rec)}</div></div>`;
}
