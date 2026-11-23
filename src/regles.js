/* ===== Page RÈGLES : vue plein écran générée depuis config/regles.json (__DATA19__) ===== */
/* t347u / t348u : pour l'instant, uniquement le tableau de score Actions. */
const RG=(()=>{try{return JSON.parse(document.getElementById('dataRegles').textContent);}catch(e){return null;}})();

let rgPrevTab='accueil';
let rgHashLock=false;

function rgPct(x, digits){
  const n=Number(x);
  if(!Number.isFinite(n)) return '—';
  const p=n*100;
  const d=digits!=null?digits:(Math.abs(p-Math.round(p))<1e-6?0:1);
  return p.toLocaleString('fr-FR',{minimumFractionDigits:d,maximumFractionDigits:d}).replace(/\s/g,'\u00a0')+'\u00a0%';
}
function rgEsc(s){
  return String(s==null?'':s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
}
function rgNum(x, d){
  const n=Number(x);
  if(!Number.isFinite(n)) return '—';
  let dd=d;
  if(dd==null){
    if(Math.abs(n-Math.round(n))<1e-9) dd=0;
    else if(Math.abs(n-Math.round(n*10)/10)<1e-9) dd=1;
    else dd=2;
  }
  return n.toLocaleString('fr-FR',{minimumFractionDigits:dd,maximumFractionDigits:dd}).replace(/\s/g,'\u00a0');
}
function rgAmp(){
  const na=(RG&&RG.note_apex)||{};
  const echelle=Number(na.amplitude_echelle);
  const tot=Number(na.amplitude_totale);
  return {
    base: Number(na.note_base)!=null&&Number.isFinite(Number(na.note_base))?Number(na.note_base):50,
    echelle: Number.isFinite(echelle)?echelle:1.5,
    totale: Number.isFinite(tot)?tot:75
  };
}
function rgPtsMax(poidsNote){
  const p=Number(poidsNote);
  if(!Number.isFinite(p)) return null;
  return p*rgAmp().totale;
}
function rgFmtPts(x){
  if(x==null||!Number.isFinite(Number(x))) return '—';
  const n=Number(x);
  if(n===0) return '0';
  return '±'+rgNum(n);
}
function rgIsOpen(){
  return document.body.classList.contains('rg-on');
}
function rgHashInfo(){
  const h=(location.hash||'').slice(1);
  if(h==='regles'||h.indexOf('regles/')===0||h.indexOf('regles-')===0) return true;
  return false;
}
function rgSetHash(on){
  if(rgHashLock) return;
  rgHashLock=true;
  try{
    if(on){
      if(!rgHashInfo()){
        const cur=(location.hash||'').slice(1);
        if(cur&&cur!=='regles') rgPrevTab=cur;
        history.pushState(null,'',location.pathname+location.search+'#regles');
      }
    }else if(rgHashInfo()){
      const back=(rgPrevTab&&rgPrevTab!=='regles')?rgPrevTab:'accueil';
      history.replaceState(null,'',location.pathname+location.search+'#'+back);
    }
  }catch(e){
    if(on) location.hash='regles';
    else location.hash=rgPrevTab||'accueil';
  }
  rgHashLock=false;
}
function rgSetOpen(on, opts){
  const fromHash=opts&&opts.fromHash;
  const page=document.getElementById('rg-page');
  const btn=document.getElementById('rgBtn');
  if(!page) return;
  document.body.classList.toggle('rg-on',!!on);
  if(on){
    page.removeAttribute('hidden');
    page.setAttribute('aria-hidden','false');
    if(btn) btn.setAttribute('aria-expanded','true');
    if(typeof ttSetOpen==='function') ttSetOpen(false);
    if(!fromHash) rgSetHash(true);
    const back=document.getElementById('rgBack');
    if(back) try{back.focus();}catch(e){}
  }else{
    page.setAttribute('hidden','');
    page.setAttribute('aria-hidden','true');
    if(btn) btn.setAttribute('aria-expanded','false');
    if(!fromHash) rgSetHash(false);
    if(btn) try{btn.focus();}catch(e){}
  }
}
function rgActionClass(){
  const fr=(RG&&RG.fiche_regles)||{};
  const secs=Array.isArray(fr.page_sections)?fr.page_sections:[{id:'actions',classe:'actions'}];
  const want=(secs[0]&&secs[0].classe)||'actions';
  const all=Array.isArray(fr.classes)?fr.classes:[];
  return all.find(c=>c&&c.id===want)||all.find(c=>c&&c.id==='actions')||null;
}
function rgRuleOf(id, fallback){
  const na=(RG&&RG.note_apex)||{};
  if(id==='rsi'&&na.rsi&&na.rsi.regle) return na.rsi.regle;
  if(id==='macd'&&na.macd&&na.macd.regle) return na.macd.regle;
  if(id==='cci'&&na.cci&&na.cci.regle) return na.cci.regle;
  return fallback||'';
}
function rgElliottRule(){
  const el=(RG&&RG.elliott)||{};
  const vertes=(el.vagues_vertes||[]).join(', ');
  const rouges=(el.vagues_rouges||[]).join(', ');
  let t="Zones vertes d'entrée : fin de vague 2, fin de vague 4, vague C ("+vertes+"). Zones rouges : vagues 1, 3, 5, A et B ("+rouges+").";
  if(el.plafond_sur_note_entiere===false){
    t+=" Pas de plafond Elliott sur la note entière : le score du critère retire déjà des points en zone rouge.";
  }else if(el.plafond_rouge!=null){
    t+=" Plafond de la note entière à "+String(el.plafond_rouge)+" en zone rouge.";
  }
  if(el.bonus_seulement_manuel){
    t+=" Bonus uniquement sur un comptage manuel";
    if(el.bonus_entry!=null) t+=" : +"+rgNum(el.bonus_entry)+" en zone verte";
    if(el.bonus_conf!=null) t+=" ; +"+rgNum(el.bonus_conf)+" si confirmation";
    t+=". Un décompte automatique ne donne pas de bonus.";
  }
  return t;
}
function rgFiboRule(parts){
  const fb=(RG&&RG.fibonacci)||{};
  const bits=[];
  if(Array.isArray(parts)&&parts.length){
    bits.push(parts.map(p=>rgPct(p.poids)+' '+p.label).join(' ; ')+'.');
  }else{
    if(fb.part_historique!=null) bits.push(rgPct(fb.part_historique)+' retracement historique');
    if(fb.part_dernier_mouvement!=null) bits.push(rgPct(fb.part_dernier_mouvement)+' dernier mouvement');
  }
  if(fb.base==='plus_bas_historique_vers_plus_haut_historique') bits.push('Base : plus bas historique → plus haut historique, corps des bougies hebdomadaires.');
  return (bits.join(' ')||'Retracement de Fibonacci hebdomadaire.').trim();
}
function rgFigureRule(label){
  const na=(RG&&RG.note_apex)||{};
  let t=label||'Figure chartiste hebdomadaire.';
  if(na.figure_neutre_si_aucune) t+=" Si aucune figure n'est validée, le score est neutre (0 point).";
  return t;
}
function rgRowsActions(cls){
  const amp=rgAmp();
  const parts=(cls.note&&cls.note.parts)||[];
  const wTech=(parts.find(p=>p.id==='technique'||p.id==='timing')||{}).poids;
  const wFond=(parts.find(p=>p.id==='fondamental'||p.id==='liquidite')||{}).poids;
  const tech=cls.technique||cls.timing||{};
  const fond=cls.fondamental||{};
  const rows=[];
  rows.push({
    id:'base', kind:'base', label:'Base', poids:null, pts:amp.base, ptsLabel:rgNum(amp.base),
    regle:'Point de départ de la note. Un critère neutre (score 0) n’ajoute ni ne retire aucun point.'
  });
  if(fond&&Number.isFinite(Number(wFond))){
    const sante=fond.part_sante, crois=fond.part_croissance;
    let regle=fond.formule||'Score fondamental 0–100.';
    if(sante!=null&&crois!=null){
      regle='Moyenne moitié santé ('+rgPct(sante)+') et moitié croissance ('+rgPct(crois)+'). Score 0–100, uniquement si les données sont suffisantes. Le score est ensuite converti en écart signé autour de 50 : (fond − 50) × 2, puis en points via le poids et l’amplitude ×'+rgNum(amp.echelle)+'.';
    }
    if(fond.si_absent) regle+=' '+fond.si_absent;
    rows.push({
      id:'fond', kind:'fond', label:fond.label||'Fondamental',
      poids:Number(wFond), pts:rgPtsMax(wFond),
      ptsLabel:rgFmtPts(rgPtsMax(wFond)),
      regle:regle
    });
  }
  const masquer=(((RG&&RG.apex_achat_v2)||{}).masquer_criteres)||[];
  (tech.fixes||[]).forEach(x=>{
    if(masquer.indexOf(x.id)>=0) return;
    const p=Number(x.poids);
    if(!Number.isFinite(p)) return;
    const wNote=p*Number(wTech||0);
    let regle=x.label||'';
    if(x.id==='elliott') regle=rgElliottRule();
    else if(x.id==='fibonacci') regle=rgFiboRule(x.parts||[]);
    else if(x.id==='figure') regle=rgFigureRule(x.label);
    else if(x.id==='rsi'||x.id==='macd'||x.id==='cci') regle=rgRuleOf(x.id, x.label);
    else if(x.id==='structure') regle=x.label||'Structure (tendance hebdomadaire, plus hauts et plus bas, position par rapport à l’ATH).';
    const v2=rgAchatV2Critere(x.id);
    if(v2){
      rows.push({
        id:x.id, kind:'achat', label:v2.label||rgShortLabel(x.id, x.label),
        poids:null, pts:v2.max, ptsLabel:v2.max!=null?rgNum(v2.max):'—',
        regle:rgAchatV2Rule(v2)
      });
      return;
    }
    rows.push({
      id:x.id, kind:'tech', label:rgShortLabel(x.id, x.label),
      poids:wNote, pts:rgPtsMax(wNote), ptsLabel:rgFmtPts(rgPtsMax(wNote)),
      regle:regle
    });
  });
  return rows;
}
function rgShortLabel(id, label){
  return ({
    elliott:"Vagues d'Elliott",
    structure:'Structure',
    fibonacci:'Fibonacci',
    figure:'Figure chartiste',
    rsi:'RSI 14 hebdo',
    macd:'MACD 12/26/9 hebdo',
    cci:'CCI 20 hebdo'
  })[id]||label||id;
}
function rgFondDetails(fond){
  if(!fond) return '';
  const profils=fond.profils||{};
  const ids=Object.keys(profils);
  const profHtml=ids.map(id=>{
    const pr=profils[id];
    const rows=(pr.sante||[]).map(x=>`<tr><th>${rgEsc(x.label)}</th><td>${rgPct(x.poids)}</td><td>${x.inverse?'Inversé (plus c’est bas, mieux c’est)':'Direct'}</td></tr>`).join('');
    return `<div class="rg-var">
      <h3>${rgEsc(pr.label||id)}</h3>
      <div class="rg-table-wrap">
        <table class="rg-table rg-table-sm">
          <thead><tr><th>Critère de santé</th><th>Poids dans le fondamental</th><th>Sens</th></tr></thead>
          <tbody>${rows}</tbody>
        </table>
      </div>
    </div>`;
  }).join('');
  let crois='';
  if(Array.isArray(fond.croissance)&&fond.croissance.length){
    crois=`<div class="rg-var rg-var-full">
      <h3>Croissance (même liste pour tous les profils)</h3>
      <div class="rg-table-wrap">
        <table class="rg-table rg-table-sm">
          <thead><tr><th>Critère de croissance</th><th>Poids dans le fondamental</th></tr></thead>
          <tbody>${fond.croissance.map(x=>`<tr><th>${rgEsc(x.label)}</th><td>${rgPct(x.poids)}</td></tr>`).join('')}</tbody>
        </table>
      </div>
    </div>`;
  }
  return `<div class="rg-block">
    <h2 class="rg-h2">Fondamental · santé et croissance</h2>
    <p class="rg-p">Le fondamental pèse ${rgPct(fond.poids)} de la note, à parts égales entre santé et croissance. Selon le type de titre, les métriques de santé changent.</p>
    <div class="rg-vars">${profHtml}${crois}</div>
  </div>`;
}
function rgConfLabel(s){
  const map={
    divergence_haussiere_hebdo:'divergence haussière hebdomadaire',
    elliott_vert_manuel:'zone Elliott verte (comptage manuel)'
  };
  return map[s]||String(s||'').replace(/_/g,' ');
}
function rgCommons(){
  if(!RG) return '';
  const el=RG.elliott||{};
  const cy=RG.cyan||{};
  const gi=RG.good_invest||{};
  const na=RG.note_apex||{};
  const tt=RG.template_trade||{};
  const bands=(RG.couleurs&&RG.couleurs.bandes)||[];
  const scale=bands.map(b=>{
    const lo=String(b.min).replace('.',',');
    const hi=String(b.max).replace('.',',');
    const tv=b.tv&&b.tv!==b.site?` <span class="rg-tv">TradingView : ${rgEsc(b.tv)}</span>`:'';
    return `<li class="rg-band"><i style="background:${rgEsc(b.hex||'#888')}"></i><b>${lo}–${hi}</b> ${rgEsc(b.site)}${tv}</li>`;
  }).join('');
  const conf=(cy.confirmation||[]).map(rgConfLabel).join(', ');
  const seuil=na.fond_seuil!=null?na.fond_seuil:40;
  const pmax=na.fond_pen_max!=null?na.fond_pen_max:20;
  const unite=tt.unite||'$';
  const dev=tt.devise||'USD';
  return `<section class="rg-sec" id="rg-sec-communes">
    <h2 class="rg-h2">Règles communes</h2>
    <div class="rg-commons-grid">
      <div class="rg-card">
        <h3>Couleurs</h3>
        <p class="rg-p">Cinq tranches égales de 20 points, d’après la note APEX /100.</p>
        <ul class="rg-bands">${scale}</ul>
      </div>
      <div class="rg-card">
        <h3>Portail cyan</h3>
        <p class="rg-p">Une note ≥ ${rgEsc(String(cy.note_min))} exige un Achat / Vente ≥ +${rgEsc(String(cy.av_achat_fort))} et une confirmation (${rgEsc(conf)}). Sinon la note est plafonnée à ${rgEsc(String(cy.plafond_sans_confirmation))}.</p>
      </div>
      <div class="rg-card">
        <h3>Pénalité fondamentale</h3>
        <p class="rg-p">Si le fondamental est inférieur à ${rgEsc(String(seuil))} / 100, une pénalité proportionnelle est retranchée de la note, plafonnée à ${rgEsc(String(pmax))} points.</p>
      </div>
      <div class="rg-card">
        <h3>Meilleures entrées</h3>
        <p class="rg-p">Note APEX ≥ ${rgEsc(String(gi.seuil))}${gi.hors_portefeuille?', hors portefeuille':''}${gi.exclure_zone_rouge?', hors zone Elliott rouge':''}${gi.inclut_ventes_en_attente?' (une vente en attente reste considérée comme détenue)':''}.</p>
      </div>
      <div class="rg-card">
        <h3>TEMPLATE TRADE</h3>
        <p class="rg-p">Note ${rgEsc(String(tt.base_note))} = ${rgEsc(String(tt.base_montant))}\u00a0${rgEsc(unite)} · puis +${rgEsc(String(tt.pas_montant))}\u00a0${rgEsc(unite)} par palier de ${rgEsc(String(tt.pas_note))} points · jusqu’à ${rgEsc(String(tt.max_note))} = ${rgEsc(String(tt.max_montant))}\u00a0${rgEsc(unite)} (${rgEsc(dev)}).</p>
      </div>
    </div>
  </section>`;
}
function rgTable(rows){
  const body=rows.map(r=>{
    const poids=r.poids==null?'—':rgPct(r.poids);
    return `<tr class="rg-row-${rgEsc(r.kind||'')}">
      <th scope="row">${rgEsc(r.label)}</th>
      <td class="rg-num">${poids}</td>
      <td class="rg-num">${rgEsc(r.ptsLabel)}</td>
      <td class="rg-rule">${rgEsc(r.regle)}</td>
    </tr>`;
  }).join('');
  return `<div class="rg-table-wrap">
    <table class="rg-table" id="rg-table-actions">
      <thead>
        <tr><th>Critère</th><th>Poids</th><th>Points max</th><th>Règle</th></tr>
      </thead>
      <tbody>${body}</tbody>
    </table>
  </div>`;
}
function rgFmtPlus(x){
  if(x==null||!Number.isFinite(Number(x))) return '—';
  const n=Number(x);
  if(n===0) return '0';
  const s=rgNum(n);
  return n>0?'+'+s:s;
}
function rgAchatV2Critere(id){
  const v=(RG&&RG.apex_achat_v2)||{};
  const all=Array.isArray(v.criteres)?v.criteres:[];
  const aliases={rsi:['rsi','rsi_14_hebdo'],macd:['macd','macd_12_26_9','macd_12_26_9_hebdo']};
  const want=aliases[id]||[id];
  return all.find(c=>c&&want.includes(c.id))||null;
}
function rgAchatV2Rule(c){
  if(!c) return '';
  const conds=(c.conditions||[]).map(x=>(x.label||x.id||'')+' : '+rgFmtPlus(x.points)+' points');
  const bits=[];
  if(conds.length) bits.push(conds.join(' ; ')+'.');
  if(c.precision) bits.push(String(c.precision).trim());
  else{
    if(c.cumulables) bits.push('Conditions cumulables.');
    if(c.max!=null) bits.push('Maximum '+rgNum(c.max)+' points.');
    if(c.retrait===false) bits.push('Aucun retrait.');
  }
  return bits.join(' ').replace(/\s+/g,' ').trim();
}
function rgPageHTML(){
  if(!RG) return '<p class="rg-p">Règles indisponibles.</p>';
  const fr=RG.fiche_regles||{};
  const cls=rgActionClass();
  const amp=rgAmp();
  const titre=fr.page_titre||fr.titre_panneau||'Règles de la note APEX';
  const intro=`La note APEX /100 des actions part de ${rgNum(amp.base)}. Chaque critère ajoute ou retire des points selon son score −100…+100 (neutre = 0), avec une amplitude ×${rgNum(amp.echelle)} (±${rgNum(amp.totale)}), puis un clip dans 0–100.`;
  const lead=cls&&cls.precision?`<p class="rg-p">${rgEsc(cls.precision)}</p>`:'';
  const rows=cls?rgRowsActions(cls):[];
  const fond=cls&&cls.fondamental;
  return `<header class="rg-top">
      <button type="button" id="rgBack" class="rg-back">← Retour</button>
      <h1 id="rgPageTitle">${rgEsc(titre)}</h1>
      <button type="button" id="rgClose" class="rg-close">Fermer</button>
    </header>
    <div class="rg-page-body">
      <div class="rg-page-main">
        <p class="rg-intro">${rgEsc(intro)}</p>
        ${lead}
        <section class="rg-sec" id="rg-sec-actions">
          <h2 class="rg-h2">Actions</h2>
          ${rgTable(rows)}
        </section>
        ${rgFondDetails(fond)}
        ${rgCommons()}
      </div>
    </div>`;
}
function rgRender(){
  const host=document.getElementById('rg-wrap');
  if(!host||!RG) return;
  const fr=RG.fiche_regles||{};
  const titre=fr.titre_bouton||'Règles';
  host.innerHTML=`<button type="button" id="rgBtn" class="rg-btn" aria-expanded="false" aria-controls="rg-page">${rgEsc(titre)}</button>`;
  let page=document.getElementById('rg-page');
  if(!page){
    page=document.createElement('div');
    page.id='rg-page';
    page.setAttribute('hidden','');
    page.setAttribute('role','dialog');
    page.setAttribute('aria-modal','true');
    page.setAttribute('aria-hidden','true');
    page.setAttribute('aria-labelledby','rgPageTitle');
    document.body.appendChild(page);
  }
  page.innerHTML=rgPageHTML();
  const btn=document.getElementById('rgBtn');
  if(btn) btn.addEventListener('click',e=>{e.preventDefault();e.stopPropagation();rgSetOpen(!rgIsOpen());});
  const close=()=>{rgSetOpen(false);};
  const b1=document.getElementById('rgBack');
  const b2=document.getElementById('rgClose');
  if(b1) b1.addEventListener('click',e=>{e.preventDefault();close();});
  if(b2) b2.addEventListener('click',e=>{e.preventDefault();close();});
}
function rgInit(){
  rgRender();
  if(document.documentElement._rgDocBound) {
    if(rgHashInfo()) rgSetOpen(true,{fromHash:true});
    return;
  }
  document.documentElement._rgDocBound=true;
  document.addEventListener('keydown',e=>{
    if(e.key==='Escape'&&rgIsOpen()) rgSetOpen(false);
  });
  if(rgHashInfo()) rgSetOpen(true,{fromHash:true});
}
(function(){
  const prev=window.ttSetOpen;
  if(typeof prev==='function'){
    window.ttSetOpen=function(on){prev(on);if(on) rgSetOpen(false,{fromHash:true});};
  }
})();
