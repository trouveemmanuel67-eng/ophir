/* ===== INDICE ROTATION : ratio S&P 500 / WTI de Charles Gave (rail, sous Meilleurs short) ===== */
const IR_LIST_KEY='apex-ir-list';
let irChart=null;
function irData(){
  try{
    const el=document.getElementById('dataRotation');
    if(!el) return null;
    const j=JSON.parse(el.textContent||'null');
    return j&&j.officiel?j:null;
  }catch(e){ return null; }
}

function irCapData(){
  try{
    const el=document.getElementById('dataRotationCapitaux');
    if(!el) return null;
    const j=JSON.parse(el.textContent||'null');
    return j&&j.affichage?j:null;
  }catch(e){ return null; }
}
function irCapHead(RC){
  if(!RC||!RC.affichage) return '';
  const a=RC.affichage;
  const conf=a.confiance||'';
  const tip=irEsc(a.infobulle||'');
  return `<div class="ir-rcap ir-conf-${irEsc(conf)}" title="${tip}">
    <span class="ir-rcap-from">${irEsc(a.from_label)}</span>
    <span class="ir-rcap-arrow" aria-hidden="true">→</span>
    <span class="ir-rcap-to">${irEsc(a.to_label)}</span>
    <span class="ir-rcap-conf">· confiance ${irEsc(conf)}</span>
  </div>`;
}
function irCapBody(RC){
  if(!RC||!RC.classes||!RC.classes.paire) return '';
  const p=RC.classes.paire;
  const alt=RC.classes.alternative;
  const sec=RC.secteurs_actions_us;
  let html=`<div class="ir-rcap-box">
    <p class="ir-src-title">Rotation de capitaux la plus probable</p>
    ${irCapHead(RC)}
    ${alt?`<p class="ir-rcap-alt">Alternative : <b>${irEsc(alt.affichage)}</b>${alt.score_combine!=null?' (score combiné '+irNum(alt.score_combine,1)+')':''}.</p>`:''}
    <p class="ir-rcap-why">${irEsc(p.pourquoi)}</p>`;
  if(sec&&sec.ok&&sec.paire){
    const sp=sec.paire, sa=sec.alternative;
    html+=`<p class="ir-rcap-sec">Secteurs d’actions US : <b>${irEsc(sp.affichage)}</b> · confiance ${irEsc(sp.confiance)}.${sa?' Alternative : '+irEsc(sa.affichage)+'.':''}</p>`;
  }
  if(RC.flux_etf&&RC.flux_etf.disponibles===false){
    html+=`<p class="ir-rcap-miss">${irEsc(RC.flux_etf.note)}</p>`;
  }
  html+=`<p class="ir-rcap-meth">${irEsc(RC.methode||'')}</p>
    <p class="ir-maj">Mise à jour de la rotation de capitaux : ${irEsc(irUpdated(RC.updated))}.</p>
  </div>`;
  return html;
}
function irListIsOpen(){
  const c=document.getElementById('indiceRotationCard');
  return !!(c&&!c.classList.contains('pos-collapsed'));
}
function irSetListOpen(on,persist){
  const c=document.getElementById('indiceRotationCard');
  if(!c) return;
  c.classList.toggle('pos-collapsed',!on);
  const head=c.querySelector('.pos-rail-h');
  if(head) head.setAttribute('aria-expanded', on?'true':'false');
  if(persist!==false){ try{ localStorage.setItem(IR_LIST_KEY, on?'1':'0'); }catch(e){} }
  if(on) irDrawChart();
  if(typeof posSyncListChrome==='function') posSyncListChrome(typeof posListIsOpen==='function'&&posListIsOpen());
}
function irMonth(ym){
  if(!ym) return '—';
  const p=String(ym).split('-');
  if(p.length<2) return String(ym);
  const d=new Date(Number(p[0]), Number(p[1])-1, 1);
  if(Number.isNaN(d.getTime())) return String(ym);
  return d.toLocaleDateString('fr-FR',{month:'long',year:'numeric'});
}
function irDay(iso){
  if(!iso) return '—';
  const d=new Date(String(iso).slice(0,10)+'T12:00:00');
  if(Number.isNaN(d.getTime())) return String(iso);
  return d.toLocaleDateString('fr-FR',{day:'numeric',month:'short',year:'numeric'});
}
function irUpdated(iso){
  if(!iso) return '—';
  const m=String(iso).match(/^(\d{4}-\d{2}-\d{2})[ T](\d{2}:\d{2})/);
  if(!m) return String(iso);
  return irDay(m[1])+' à '+m[2].replace(':',' h ')+' (heure de Paris)';
}
function irNum(v,d){
  if(typeof fmt==='function') return fmt(v,d);
  if(v==null||Number.isNaN(Number(v))) return '—';
  return Number(v).toLocaleString('fr-FR',{minimumFractionDigits:d,maximumFractionDigits:d});
}
function irPct(v){
  if(v==null||Number.isNaN(Number(v))) return '—';
  const n=Number(v);
  const sign=n>0?'+':(n<0?'−':'');
  return sign+irNum(Math.abs(n),1)+' %';
}
function irEsc(s){
  return String(s==null?'':s).replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
}
function irDrawChart(){
  const canvas=document.getElementById('cIrRatio');
  const IR=irData();
  if(!canvas||!IR||!IR.serie||!IR.serie.length||typeof Chart==='undefined') return;
  if(canvas.closest('.pos-collapsed')) return;
  if(irChart){ try{ irChart.destroy(); }catch(e){} irChart=null; }
  const labels=IR.serie.map(p=>p.m);
  const ratio=IR.serie.map(p=>p.r);
  const ma=IR.serie.map(p=>p.ma);
  const cfg={
    type:'line',
    data:{
      labels,
      datasets:[
        {label:'Ratio S&P 500 / WTI',data:ratio,borderColor:'#e6c27a',backgroundColor:'#e6c27a',pointRadius:0,borderWidth:1.5,tension:.1,fill:{target:'1',above:'rgba(34,197,94,.16)',below:'rgba(232,143,143,.16)'}},
        {label:'Moyenne mobile 7 ans',data:ma,borderColor:'#a9cdf5',backgroundColor:'#a9cdf5',pointRadius:0,borderWidth:1.4,borderDash:[4,3],tension:.1,fill:false}
      ]
    },
    options:{
      maintainAspectRatio:false,animation:false,interaction:{mode:'index',intersect:false},
      plugins:{
        legend:{display:true,labels:{boxWidth:10,font:{size:10},color:'#c8c4bc'}},
        tooltip:{callbacks:{
          title:its=>its&&its.length?irMonth(its[0].label):'',
          label:c=>c.parsed.y==null?'':' '+c.dataset.label+' : '+irNum(c.parsed.y,1)
        }}
      },
      scales:{
        x:{ticks:{maxTicksLimit:8,autoSkip:true,callback:function(v){const l=this.getLabelForValue(v);return l?String(l).slice(0,4):'';},color:'#8d8d8d',font:{size:10}},grid:{color:'rgba(255,255,255,.06)'}},
        y:{ticks:{color:'#8d8d8d',font:{size:10},callback:v=>Number(v).toLocaleString('fr-FR')},grid:{color:'rgba(255,255,255,.06)'}}
      }
    }
  };
  if(typeof lineChart==='function'){
    /* on reste sur Chart.js direct : fill entre les deux courbes + libellés FR */
  }
  irChart=new Chart(canvas,cfg);
  if(typeof charts!=='undefined'&&Array.isArray(charts)) charts.push(irChart);
}
function irCrossTxt(c){
  if(!c||!c.month) return 'Date du dernier croisement : non déterminée (historique insuffisant).';
  const vers=c.to==='above'?'au-dessus de la moyenne (bust → boom)':'sous la moyenne (boom → bust)';
  return 'Dernier croisement : '+irMonth(c.month)+', passage '+vers+'.';
}
function irRender(){
  const host=document.getElementById('mes-pos');
  if(!host) return;
  const IR=irData();
  const off=IR&&IR.officiel;
  const rg=IR&&IR.regime_officiel;
  const prov=IR&&IR.provisoire;
  const above=off&&off.above;
  const headVal=off?((above?'Boom ':'Bust ')+irPct(off.ecart_pct)):'n.d.';
  const headClass=above===true?'ir-boom':(above===false?'ir-bust':'');
  let body;
  if(!off){
    body=`<p class="ir-empty">Les données du ratio S&amp;P 500 / WTI n’ont pas pu être chargées. Aucun chiffre n’est inventé.</p>`;
  }else{
    const srcCadre=(IR.sources_cadre||[]).map(s=>{
      const a=s.url?`<a href="${irEsc(s.url)}" target="_blank" rel="noopener">${irEsc(s.nom)}</a>`:irEsc(s.nom);
      return `<li>${a}${s.extrait?' — '+irEsc(s.extrait):''}</li>`;
    }).join('');
    const srcData=(IR.sources_donnees||[]).map(s=>{
      const a=s.url?`<a href="${irEsc(s.url)}" target="_blank" rel="noopener">${irEsc(s.nom)}</a>`:irEsc(s.nom);
      return `<li>${a} — ${irEsc(s.role||'')}</li>`;
    }).join('');
    const hist=IR.historique||{};
    const first=hist.premier_ma||hist.premier_ratio;
    let provHtml='';
    if(prov){
      const same=(prov.above===off.above);
      provHtml=`<p class="ir-prov">Lecture provisoire au ${irEsc(irDay(prov.date))} (dernier jour commun S&amp;P 500 et WTI spot) : ratio <b>${irNum(prov.ratio,1)}</b> (${irPct(prov.ecart_pct)} vs la moyenne). ${same?'Même régime que le mois achevé.':'Attention : cette lecture quotidienne ne correspond pas encore au régime officiel, qui reste celui du mois achevé.'} Le WTI spot FRED n’est pas encore publié après cette date.</p>`;
    }
    body=`
      <div class="ir-regime ${headClass}">
        <div class="ir-regime-k">${irEsc((rg&&rg.axe)||(above?'Boom':'Bust'))}</div>
        <p class="ir-regime-t">${irEsc((rg&&rg.rotation)||'')}</p>
        <p class="ir-regime-m">Régime officiel : ${irEsc(irMonth(off.month))} (mois calendaire achevé).</p>
      </div>
      <div class="ir-kpis">
        <div class="ir-kpi"><div class="l">Ratio</div><div class="v">${irNum(off.ratio,1)}</div><div class="s">S&amp;P ${irNum(off.spx,0)} / WTI ${irNum(off.wti,2)} $</div></div>
        <div class="ir-kpi"><div class="l">Moyenne 7 ans</div><div class="v">${irNum(off.ma84,1)}</div><div class="s">84 mois</div></div>
        <div class="ir-kpi"><div class="l">Écart</div><div class="v ${headClass}">${irPct(off.ecart_pct)}</div><div class="s">vs la moyenne</div></div>
      </div>
      ${provHtml}
      <div class="ir-chart"><canvas id="cIrRatio" aria-label="Graphique du ratio S&amp;P 500 / WTI et de sa moyenne mobile 7 ans"></canvas></div>
      <p class="ir-cross">${irEsc(irCrossTxt(IR.dernier_croisement))}</p>
      <p class="ir-note">Le ratio compte combien de barils de WTI « valent » le niveau du S&amp;P 500. Historique mensuel depuis ${irEsc(irMonth(first))}.</p>
      <div class="ir-src">
        <p class="ir-src-title">Cadre de Charles Gave</p>
        <ul>${srcCadre}</ul>
        <p class="ir-src-title">Sources des données</p>
        <ul>${srcData}</ul>
        <p class="ir-maj">Mise à jour des données : ${irEsc(irUpdated(IR.updated))}.</p>
        <p class="ir-warn">${irEsc(IR.avertissement||'')}</p>
      </div>`;
  }
  const RC=irCapData();
  const html=`<div class="card no-group" id="indiceRotationCard">
    <div class="pos-rail-h" role="button" tabindex="0" aria-expanded="false" aria-controls="irBody">
      <span class="pos-chev" aria-hidden="true">▸</span>
      <div class="ir-head-main">
        <div class="ir-head-row">
          <h2>INDICE ROTATION</h2>
          <span class="pos-head-tot ${headClass}">${irEsc(headVal)}</span>
        </div>
        ${irCapHead(RC)}
      </div>
    </div>
    <div class="pos-body gi-body ir-body" id="irBody">${irCapBody(RC)}${body}</div>
  </div>`;
  const wasOpen=irListIsOpen();
  let saved=null;
  try{ saved=localStorage.getItem(IR_LIST_KEY); }catch(e){}
  const prev=document.getElementById('indiceRotationCard');
  const gs=document.getElementById('bestShortCard');
  const gi=document.getElementById('goodInvestCard');
  if(prev) prev.outerHTML=html;
  else if(gs) gs.insertAdjacentHTML('afterend', html);
  else if(gi) gi.insertAdjacentHTML('afterend', html);
  else host.insertAdjacentHTML('beforeend', html);
  const card=document.getElementById('indiceRotationCard');
  if(!card) return;
  const open=wasOpen||saved==='1';
  card.classList.toggle('pos-collapsed', !open);
  const head=card.querySelector('.pos-rail-h');
  if(head){
    head.setAttribute('aria-expanded', open?'true':'false');
    const tog=e=>{ e.preventDefault(); irSetListOpen(!irListIsOpen()); };
    head.addEventListener('click',tog);
    head.addEventListener('keydown',e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();tog(e);}});
  }
  if(open) irDrawChart();
  if(typeof posSyncListChrome==='function') posSyncListChrome(typeof posListIsOpen==='function'&&posListIsOpen());
}
function irInit(){
  irRender();
}
