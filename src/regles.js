/* ===== Panneau RÈGLES : contenu généré depuis config/regles.json (__DATA19__) ===== */
const RG=(()=>{try{return JSON.parse(document.getElementById('dataRegles').textContent);}catch(e){return null;}})();

function rgPct(x, digits){
  const n=Number(x);
  if(!Number.isFinite(n)) return '—';
  const p=n*100;
  const d=digits!=null?digits:(Math.abs(p-Math.round(p))<1e-6?0:1);
  return p.toLocaleString('fr-FR',{minimumFractionDigits:d,maximumFractionDigits:d}).replace(' ','\u00a0')+'\u00a0%';
}
function rgEsc(s){
  return String(s==null?'':s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
}
function rgIsOpen(){
  const w=document.getElementById('rg-wrap');
  return !!(w&&w.classList.contains('is-open'));
}
function rgSetOpen(on){
  const w=document.getElementById('rg-wrap');
  const b=document.getElementById('rgBtn');
  if(!w||!b) return;
  w.classList.toggle('is-open',!!on);
  b.setAttribute('aria-expanded', on?'true':'false');
  if(on && typeof ttSetOpen==='function') ttSetOpen(false);
}
function rgClasses(){
  const fr=(RG&&RG.fiche_regles)||{};
  const all=Array.isArray(fr.classes)?fr.classes:[];
  const ordre=Array.isArray(fr.ordre_site)?fr.ordre_site:all.map(c=>c.id);
  const by={};
  all.forEach(c=>{if(c&&c.id) by[c.id]=c;});
  return ordre.map(id=>by[id]).filter(Boolean);
}
function rgTimingRows(timing, wNote){
  if(!timing) return [];
  const rows=[];
  const wT=Number.isFinite(Number(wNote))?Number(wNote):1;
  (timing.fixes||[]).forEach(x=>{
    const p=Number(x.poids);
    if(!Number.isFinite(p)) return;
    const row={id:x.id,label:x.label,poidsTiming:p,poidsNote:p*wT,facultatif:!!x.facultatif,detail:x.si_absent,parts:x.parts||[]};
    rows.push(row);
  });
  const panier=timing.panier||{};
  const pt=Number(panier.poids_total);
  (panier.composantes||[]).forEach(x=>{
    const pp=Number(x.poids_dans_panier);
    if(!Number.isFinite(pp)||!Number.isFinite(pt)) return;
    const p=pp*pt;
    rows.push({id:x.id,label:x.label,poidsTiming:p,poidsNote:p*wT,facultatif:!!x.facultatif});
  });
  const cci=timing.cci;
  if(cci&&Number.isFinite(Number(cci.poids))){
    rows.push({id:cci.id,label:cci.label,poidsTiming:Number(cci.poids),poidsNote:Number(cci.poids)*wT,facultatif:true,detail:cci.condition,horsTotal:true});
  }
  return rows;
}
function rgBar(rows){
  const vis=rows.filter(r=>!r.horsTotal&&r.poidsNote>0);
  const tot=vis.reduce((s,r)=>s+r.poidsNote,0)||1;
  const cols=['#e6c27a','#8ec8ff','#22c55e','#00e5ff','#ffd400','#ff8a4c','#9d54ff','#d8d0c2','#7ad0b0','#c4b5fd','#f9a8d4','#fca5a5'];
  const segs=vis.map((r,i)=>`<span class="rg-seg" style="width:${(r.poidsNote/tot*100).toFixed(3)}%;background:${cols[i%cols.length]}" title="${rgEsc(r.label)} · ${rgPct(r.poidsNote)}"></span>`).join('');
  return `<div class="rg-bar" role="img" aria-label="Répartition des poids dans la note">${segs}</div>`;
}
function rgDonut(parts){
  if(!parts||!parts.length) return '';
  const C=2*Math.PI*16;
  let acc=0;
  const cols={timing:'#e6c27a',technique:'#e6c27a',fondamental:'#8ec8ff',liquidite:'#00e5ff'};
  const segs=parts.map(p=>{
    const w=Number(p.poids)||0;
    const dash=w*C;
    const gap=C-dash;
    const rot=acc*360;
    acc+=w;
    const col=cols[p.id]||'#d8d0c2';
    return `<circle cx="20" cy="20" r="16" fill="none" stroke="${col}" stroke-width="6" stroke-dasharray="${dash} ${gap}" transform="rotate(${rot} 20 20)"></circle>`;
  }).join('');
  const lab=parts.map(p=>`<span><i style="background:${cols[p.id]||'#d8d0c2'}"></i>${rgEsc(p.label)} ${rgPct(p.poids)}</span>`).join('');
  return `<div class="rg-donut-wrap"><svg class="rg-donut" viewBox="0 0 40 40" aria-hidden="true">${segs}</svg><div class="rg-donut-leg">${lab}</div></div>`;
}
function rgFondBlock(fond, wNote){
  if(!fond) return '';
  const bits=[];
  bits.push(`<h4>${rgEsc(fond.label||'Fondamental')} · ${rgPct(fond.poids)}</h4>`);
  if(fond.formule) bits.push(`<p class="rg-p">${rgEsc(fond.formule)}</p>`);
  if(fond.remplace) bits.push(`<p class="rg-p">Ce bloc remplace le fondamental.</p>`);
  if(Array.isArray(fond.composantes)&&fond.composantes.length){
    bits.push('<ul class="rg-list">'+fond.composantes.map(c=>{
      const p=Number(c.poids);
      const ofNote=Number.isFinite(p)&&Number.isFinite(Number(wNote))?p*Number(wNote):null;
      return `<li><b>${rgEsc(c.label)}</b><span>${rgPct(p)} de la liquidité${ofNote!=null?' · '+rgPct(ofNote)+' de la note':''}</span></li>`;
    }).join('')+'</ul>');
  }
  const profils=fond.profils||{};
  const ids=Object.keys(profils);
  if(ids.length){
    bits.push('<div class="rg-profils">'+ids.map(id=>{
      const pr=profils[id];
      const sante=(pr.sante||[]).map(x=>`<li>${rgEsc(x.label)} · ${rgPct(x.poids)}${x.inverse?' (inversé)':''}</li>`).join('');
      return `<div class="rg-profil"><div class="rg-profil-t">${rgEsc(pr.label||id)}</div><ul>${sante}</ul></div>`;
    }).join('')+'</div>');
  }
  if(Array.isArray(fond.croissance)&&fond.croissance.length){
    bits.push('<p class="rg-k">Croissance (même liste pour tous les profils)</p><ul class="rg-list">'+
      fond.croissance.map(x=>`<li><b>${rgEsc(x.label)}</b><span>${rgPct(x.poids)}</span></li>`).join('')+'</ul>');
  }
  if(fond.si_absent) bits.push(`<p class="rg-p">${rgEsc(fond.si_absent)}</p>`);
  const pe=fond.penalite;
  if(pe){
    bits.push(`<p class="rg-p">${rgEsc(pe.texte||'Pénalité fondamental.')} Seuil ${rgEsc(String(pe.seuil))} / 100, maximum ${rgEsc(String(pe.maximum))} point${Number(pe.maximum)>1?'s':''}.</p>`);
  }
  return `<div class="rg-block">${bits.join('')}</div>`;
}
function rgCommons(){
  if(!RG) return '';
  const el=RG.elliott||{};
  const cy=RG.cyan||{};
  const gi=RG.good_invest||{};
  const bands=(RG.couleurs&&RG.couleurs.bandes)||[];
  const scale=bands.map(b=>{
    const lo=String(b.min).replace('.',',');
    const hi=String(b.max).replace('.',',');
    const tv=b.tv&&b.tv!==b.site?` (TradingView : ${b.tv})`:'';
    return `<span class="rg-band"><i style="background:${rgEsc(b.hex||'#888')}"></i>${lo}–${hi} ${rgEsc(b.site)}${rgEsc(tv)}</span>`;
  }).join('');
  const rouges=(el.vagues_rouges||[]).join(', ');
  const vertes=(el.vagues_vertes||[]).join(', ');
  const conf=(cy.confirmation||[]).join(', ');
  return `<div class="rg-commons">
    <h4>Règles communes</h4>
    <ul class="rg-list rg-list-plain">
      <li>Plafond Elliott : note limitée à ${rgEsc(String(el.plafond_rouge))} en vagues rouges (${rgEsc(rouges)}).</li>
      <li>Bonus Elliott : ${el.bonus_seulement_manuel?'uniquement sur un comptage manuel (un décompte automatique ne donne pas de bonus)':''}${el.bonus_entry!=null?' ; +'+String(el.bonus_entry).replace('.',',')+' si zone verte':' '}${el.bonus_conf!=null?' ; +'+String(el.bonus_conf).replace('.',',')+' si confirmation':''}. Zones vertes : ${rgEsc(vertes)}.</li>
      <li>Règle cyan : une note ≥ ${rgEsc(String(cy.note_min))} exige un Achat / Vente ≥ +${rgEsc(String(cy.av_achat_fort))} et une confirmation (${rgEsc(conf)}). Sinon la note est plafonnée à ${rgEsc(String(cy.plafond_sans_confirmation))}.</li>
      <li>Échelle de couleurs (5 tranches) : <span class="rg-bands">${scale}</span></li>
      <li>Meilleures entrées : note APEX ≥ ${rgEsc(String(gi.seuil))}${gi.hors_portefeuille?', hors portefeuille':''}${gi.inclut_ventes_en_attente?' (les ventes en attente restent considérées comme détenues)':''}.</li>
    </ul>
  </div>`;
}
function rgBody(cls){
  if(!cls) return '';
  if(!cls.note){
    return `<div class="rg-body"><p class="rg-p">${rgEsc(cls.precision||'')}</p>${rgCommons()}</div>`;
  }
  const parts=cls.note.parts||[];
  const tech=cls.technique||cls.timing||null;
  const wTech=(parts.find(p=>p.id==='technique'||p.id==='timing')||{}).poids;
  const rows=rgTimingRows(tech, wTech);
  const fibo=rows.find(r=>r.id==='fibonacci');
  let fiboTxt='';
  if(fibo&&fibo.parts&&fibo.parts.length){
    fiboTxt='<p class="rg-p">Dont Fibonacci : '+fibo.parts.map(p=>rgPct(p.poids)+' '+p.label).join(' ; ')+'.</p>';
  }
  const isTech=!!cls.technique;
  const list=rows.map(r=>{
    const extra=r.horsTotal?' (facultatif, pris sur le panier si le critère est actif)':(r.facultatif?' (facultatif)':'');
    const sous=isTech?'du technique':'du timing';
    const sub=Number(wTech)<1
      ? `${rgPct(r.poidsTiming)} ${sous} · ${rgPct(r.poidsNote)} de la note`
      : `${rgPct(r.poidsNote)} de la note`;
    return `<li${r.horsTotal?' class="rg-opt"':''}><b>${rgEsc(r.label)}</b><span>${sub}${extra}</span>${r.detail?`<small>${rgEsc(r.detail)}</small>`:''}</li>`;
  }).join('');
  const fond=cls.fondamental;
  const wFond=fond&&Number(fond.poids);
  const titreComp=isTech?'Composantes techniques':'Composantes du timing';
  return `<div class="rg-body">
    ${rgDonut(parts)}
    ${cls.precision?`<p class="rg-p">${rgEsc(cls.precision)}</p>`:''}
    ${parts.length?`<p class="rg-k">Composition de la note</p>${parts.map(p=>`<div class="rg-part"><b>${rgEsc(p.label)}</b> ${rgPct(p.poids)}</div>`).join('')}`:''}
    ${rows.length?`<p class="rg-k">${titreComp}</p>${rgBar(rows)}<ul class="rg-list">${list}</ul>${fiboTxt}`:''}
    ${rgFondBlock(fond, wFond)}
    ${rgCommons()}
  </div>`;
}
function rgSelect(id){
  const wrap=document.getElementById('rg-wrap');
  if(!wrap) return;
  wrap.querySelectorAll('.rg-nav button').forEach(b=>b.classList.toggle('on', b.dataset.id===id));
  const cls=rgClasses().find(c=>c.id===id);
  const box=document.getElementById('rgBody');
  if(box) box.innerHTML=rgBody(cls);
  wrap.dataset.cls=id;
}
function rgRender(){
  const host=document.getElementById('rg-wrap');
  if(!host||!RG) return;
  const fr=RG.fiche_regles||{};
  const titre=fr.titre_bouton||'Règles';
  const pan=fr.titre_panneau||titre;
  const classes=rgClasses();
  const first=classes[0]&&classes[0].id;
  const nav=classes.map((c,i)=>`<button type="button" data-id="${rgEsc(c.id)}" class="${i?'':'on'}">${rgEsc(c.label)}</button>`).join('');
  host.innerHTML=`<button type="button" id="rgBtn" class="rg-btn" aria-expanded="false" aria-controls="rgPanel">${rgEsc(titre)}</button>
    <div class="rg-panel card no-group no-acc" id="rgPanel" role="dialog" aria-label="${rgEsc(pan)}">
      <div class="rg-head">${rgEsc(pan)}</div>
      ${fr.intro?`<p class="rg-intro">${rgEsc(fr.intro)}</p>`:''}
      <div class="rg-layout">
        <div class="rg-nav" role="tablist">${nav}</div>
        <div id="rgBody" class="rg-main"></div>
      </div>
    </div>`;
  const btn=document.getElementById('rgBtn');
  if(btn) btn.addEventListener('click',e=>{e.stopPropagation();rgSetOpen(!rgIsOpen());});
  host.querySelectorAll('.rg-nav button').forEach(b=>{
    b.addEventListener('click',e=>{e.stopPropagation();rgSelect(b.dataset.id);});
  });
  if(first) rgSelect(first);
}
function rgInit(){
  rgRender();
  if(document.documentElement._rgDocBound) return;
  document.documentElement._rgDocBound=true;
  document.addEventListener('pointerdown',e=>{
    if(!rgIsOpen()) return;
    const w=document.getElementById('rg-wrap');
    if(w&&!w.contains(e.target)) rgSetOpen(false);
  });
  document.addEventListener('keydown',e=>{
    if(e.key==='Escape'&&rgIsOpen()) rgSetOpen(false);
  });
}
// Si TEMPLATE TRADE s'ouvre, fermer RÈGLES
(function(){
  const prev=window.ttSetOpen;
  if(typeof prev==='function'){
    window.ttSetOpen=function(on){prev(on);if(on) rgSetOpen(false);};
  }
})();
