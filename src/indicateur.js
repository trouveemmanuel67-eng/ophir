/* ===== Colonne INDICATEUR (une jauge par onglet + emplacement pour de futurs indicateurs) ===== */
const IND=JSON.parse(document.getElementById('data3').textContent);
const GRAD=[[0,[157,84,255]],[16,[157,84,255]],[24,[255,45,45]],[36,[255,45,45]],[44,[255,212,0]],[56,[255,212,0]],[64,[34,197,94]],[76,[34,197,94]],[84,[0,229,255]],[100,[0,229,255]]]; // t327u : 5 tranches égales de 20 (violet, rouge, jaune, vert, cyan), fondu doux aux frontières
/* Couleur de la barre à une position (0-100) en [r,g,b], et sa couleur inverse (255−R, 255−G, 255−B) */
function grgb(v){v=Math.max(0,Math.min(100,v));for(let i=1;i<GRAD.length;i++){const [p1,c1]=GRAD[i-1],[p2,c2]=GRAD[i];if(v<=p2){const t=(v-p1)/(p2-p1);return c1.map((x,j)=>Math.round(x+(c2[j]-x)*t));}}return GRAD[GRAD.length-1][1];}
const gmir=v=>gsol(100-v);   /* dégradé miroir : couleur de la barre à la position symétrique */
const ginv=v=>{const c=grgb(v);return `rgb(${255-c[0]},${255-c[1]},${255-c[2]})`;};
const gsol=v=>{const c=grgb(v);return `rgb(${c[0]},${c[1]},${c[2]})`;};
function gcol(v,a=1){v=Math.max(0,Math.min(100,v));for(let i=1;i<GRAD.length;i++){const [p1,c1]=GRAD[i-1],[p2,c2]=GRAD[i];if(v<=p2){const t=(v-p1)/(p2-p1);const c=c1.map((x,j)=>Math.round(x+(c2[j]-x)*t));return `rgba(${c[0]},${c[1]},${c[2]},${a})`;}}}

/* Couleur de la note APEX /100 : uniquement la note affichée, 5 tranches de 20 (t337u). */
function apexBand(note){
  const n=Number(note);
  if(!Number.isFinite(n)) return null;
  if(n<20) return 'violet';
  if(n<40) return 'rouge';
  if(n<60) return 'jaune';
  if(n<80) return 'vert';
  return 'cyan';
}
const APEX_HEX={violet:'#9d54ff',rouge:'#ff2d2d',jaune:'#ffd400',vert:'#22c55e',cyan:'#00e5ff'};
const APEX_TV={violet:'purple',rouge:'red',jaune:'orange',vert:'green',cyan:'cyan'};
function apexHexOf(note){const b=apexBand(note);return b?APEX_HEX[b]:'#8a8a8a';}
function apexFlagTV(note){const b=apexBand(note);return b?APEX_TV[b]:'none';}

function fmtPts(x){
  if(x==null||!Number.isFinite(Number(x))) return '–';
  const r=Math.round(Number(x)*10)/10;
  if(Math.abs(r-Math.round(r))<1e-9) return String(Math.round(r));
  return String(r).replace('.',',');
}
function apexDecomp(rec){
  const d=rec&&rec.decomp;
  if(!d||!d.lignes||!d.lignes.length) return '';
  const bar=d.lignes.map(l=>{
    const w=Math.max(0,Number(l.poids)||0);
    const hex=l.hex||(typeof apexHexOf==='function'?apexHexOf(100*(l.pts||0)/Math.max(w,1)):'#8a8a8a');
    return `<i style="flex:${w};background:${hex}"></i>`;
  }).join('');
  const txt=d.texte||d.lignes.map(l=>`${l.label} ${fmtPts(l.pts)}/${l.poids}`).join(' · ');
  return `<div class="apex-dec"><span class="apex-dec-bar" aria-hidden="true">${bar}</span><span class="apex-dec-txt">${txt}</span></div>`;
}
let indChart=null;
function renderIndicator(tabId){
  const box=document.getElementById('ind'),g=IND[tabId];
  if(indChart){indChart.destroy();const i=charts.indexOf(indChart);if(i>=0)charts.splice(i,1);indChart=null;}
  if(!g){box.innerHTML=tabId==='placements'?'':'<div class="card"><h2>Indicateur</h2><div class="desc">Aucun indicateur pour cet onglet.</div></div>';return;}
  const pos=v=>`${Math.max(0,Math.min(100,v))}%`;
  const comps=g.components.length?`<div class="ind-sub"><div class="ind-subt">${g.official?'Sous-indicateurs (notés par la source)':'Composantes'}</div>${g.components.map(c=>`<div class="ind-sb"><div class="ind-sbl"><span>${c.name}</span><b class="sc-t" style="color:${gmir(c.value)}">${fmt(c.value,0)}</b></div><div class="ind-sbt"><i style="width:${pos(c.value)};background:${gmir(c.value)}"></i></div>${c.weight?`<div class="ind-sbd">poids ${fmt(c.weight*100,0)} % · ${c.detail}</div>`:(c.date?`<div class="ind-sbd">au ${dshort(c.date)}</div>`:'')}</div>`).join('')}</div>`:'';
  box.innerHTML=`<div class="card ind-card">
   <h2>Indicateur</h2>
   <div class="ind-slot" data-slot="sentiment">
    <div class="ind-t">Sentiment de marché, 1 an</div>
    <div class="ind-n">${g.title}</div>
    ${''}
    <div class="ind-val"><span class="sc-t" style="color:${gmir(g.value)}">${fmt(g.value,0)}</span><em class="sc-t" style="color:${gmir(g.value)}">${g.label}</em></div>
    <div class="ind-date">au ${dshort(g.date)}</div>
    <div class="ind-gauge">
      <div class="ind-range" style="left:${pos(g.min[1])};width:${Math.max(0.5,g.max[1]-g.min[1])}%" title="plage 1 an"></div>
      <div class="ind-bar ind-bar-mir"></div>
      <div class="ind-avg" style="left:${pos(g.avg)}" title="moyenne 1 an"></div>
      <div class="ind-cur" style="left:${pos(g.value)};background:${gmir(g.value)}"></div>
    </div>
    <div class="ind-scale"><span>0 · Peur extrême</span><span>Neutre</span><span>Euphorie · 100</span></div>
    <div class="ind-stats">
      <div><span>Moyenne 1 an</span><b>${fmt(g.avg,1)}</b></div>
      <div><span>Min 1 an</span><b>${fmt(g.min[1],1)}</b><small>${dshort(g.min[0])}</small></div>
      <div><span>Max 1 an</span><b>${fmt(g.max[1],1)}</b><small>${dshort(g.max[0])}</small></div>
    </div>
    <div class="ind-spark"><canvas id="cInd"></canvas></div>
    ${comps}
    ${g.missing.length?`<div class="note">${g.missing.join(' ')}</div>`:''}
    <details class="ind-meth"><summary>Méthode</summary><p>${apexPlain(g.method)}</p><p>Libellés : 0–24 peur extrême · 25–44 peur · 45–55 neutre · 56–75 avidité · 76–100 euphorie. Moyenne, minimum et maximum sur les ${g.n} observations des 365 derniers jours. Calcul reproductible avec <code>src/build_indicateur.py</code>.</p></details>
    <div class="src">Source : ${lnk(g.source.url,g.source.name)}${g.source.api?' · '+lnk(g.source.api,'API'):''} · dernière valeur au ${dshort(g.date)} · récupéré le ${dfr(g.source.retrieved.slice(0,10))}.</div>
   </div>
   <div class="ind-more" id="indMore" data-slots="futurs indicateurs"></div>
  </div>`;
  const s=g.series;
  indChart=new Chart(document.getElementById('cInd'),{type:'line',data:{labels:s.map(x=>dshort(x[0])),datasets:[{data:s.map(x=>x[1]),pointRadius:0,borderWidth:2,tension:.25,
    segment:{borderColor:ctx=>gmir((ctx.p0.parsed.y+ctx.p1.parsed.y)/2)},borderColor:gmir(g.value)},
    {data:s.map(()=>g.avg),borderColor:'rgba(255,255,255,.35)',borderDash:[3,3],borderWidth:1,pointRadius:0}]},
    options:{maintainAspectRatio:false,animation:false,interaction:{mode:'index',intersect:false},plugins:{legend:{display:false},tooltip:{filter:i=>i.datasetIndex===0,callbacks:{label:c=>' '+fmt(c.parsed.y,1)+' · '+label5(c.parsed.y)}}},
    scales:{x:{ticks:{maxTicksLimit:4,font:{size:10}},grid:{display:false}},y:{min:0,max:100,ticks:{stepSize:25,font:{size:10}}}}}});
  charts.push(indChart);
}
const label5=v=>v<25?'Peur extrême':v<45?'Peur':v<=55?'Neutre':v<=75?'Avidité':'Euphorie';
