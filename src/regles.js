/* ===== Page RÈGLES : vue plein écran générée depuis config/regles.json (__DATA19__) ===== */
/* t347u / t348u / t459u : tableaux Actions (v2) et Métaux précieux (note /100 en vigueur). */
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
function rgFitRows(){
  const root=document.getElementById('rg-table-actions');
  if(!root||root.closest('[hidden]')||!root.getClientRects().length) return;
  const overflows=box=>{
    if(!box) return false;
    return Array.from(box.querySelectorAll('.rg-card')).some(c=>c.scrollWidth>c.clientWidth+1);
  };
  const tech=root.querySelector('[data-group="technique"] .rg-cards');
  if(tech){
    tech.classList.remove('rg-cards-span');
    void tech.offsetWidth;
    if(overflows(tech)) tech.classList.add('rg-cards-span');
  }
  const fond=root.querySelector('.rg-fond-cols');
  if(fond){
    fond.classList.remove('rg-fond-one');
    void fond.offsetWidth;
    if(overflows(fond)) fond.classList.add('rg-fond-one');
  }
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
    rgFitRows();
    requestAnimationFrame(()=>requestAnimationFrame(rgFitRows));
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
  const fondV2=RG&&RG.apex_achat_v2&&RG.apex_achat_v2.fondamental;
  if(fondV2){
    rows.push({id:'fond', kind:'fond-v2', html:rgFondAchatV2HTML(fondV2)});
  }else if(fond&&Number.isFinite(Number(wFond))){
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
    cci:'CCI Stochastic 28 hebdo (Daveatt)'
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
function rgAchatV2Total(){
  const v=(RG&&RG.apex_achat_v2)||{};
  const all=(v.criteres||[]).filter(c=>c&&c.max!=null&&Number.isFinite(Number(c.max)));
  const tech=all.reduce((s,c)=>s+Number(c.max),0);
  const fond=v.fondamental;
  const fondMax=fond&&fond.max!=null&&Number.isFinite(Number(fond.max))?Number(fond.max):0;
  const sum=tech+fondMax;
  const techDetail=all.map(c=>(c.label||c.id)+' '+rgNum(c.max)).join(' + ');
  let detail='';
  if(tech) detail+='Technique '+rgNum(tech)+(techDetail?' ('+techDetail+')':'');
  if(fondMax) detail+=(detail?' + ':'')+'Fondamental '+rgNum(fondMax);
  if(detail) detail+=' = '+rgNum(sum);
  return {sum, tech, fond:fondMax, detail, n:all.length+(fondMax?1:0)};
}
function rgFondAchatV2HTML(fond){
  if(!fond) return '';
  const groupes=(fond.groupes||[]).map(g=>{
    const rows=(g.elements||[]).map(el=>{
      const av=el.seuil_a_valider===true;
      const extra=el.precision?`<div class="rg-fond-note">${rgEsc(el.precision)}</div>`:'';
      const bon=el.bon_si||'';
      return `<tr>
        <th scope="row">${rgEsc(el.label||el.id||'')}</th>
        <td class="rg-bon">${rgEsc(bon)}${av?' <span class="rg-av">à valider</span>':''}${extra}</td>
        <td class="rg-num">${rgFmtPlus(el.points!=null?el.points:fond.points_si_bon)}</td>
      </tr>`;
    }).join('');
    return `<h3 class="rg-fond-g">${rgEsc(g.label||g.id||'')}</h3>
      <div class="rg-table-wrap rg-fond-wrap-in">
        <table class="rg-table rg-table-sm rg-table-fond-v2">
          <thead><tr><th>Élément</th><th>Bon si</th><th>Points</th></tr></thead>
          <tbody>${rows}</tbody>
        </table>
      </div>`;
  }).join('');
  const intro=fond.precision?`<p class="rg-p">${rgEsc(fond.precision)}</p>`:'';
  const max=fond.max!=null?rgNum(fond.max):'';
  return `<div class="rg-fond-v2" id="rg-fond-v2">
      <div class="rg-fond-head">
        <strong>${rgEsc(fond.label||'Fondamental')}</strong>
        <span class="rg-num">max ${max}</span>
      </div>
      ${intro}
      ${groupes}
    </div>`;
}
function rgTable(rows){
  const body=rows.map(r=>{
    if(r.kind==='fond-v2'){
      return `<tr class="rg-fond-wrap"><td colspan="4">${r.html||''}</td></tr>`;
    }
    const poids=r.poids==null?'—':rgPct(r.poids);
    return `<tr class="rg-row-${rgEsc(r.kind||'')}">
      <th scope="row">${rgEsc(r.label)}</th>
      <td class="rg-num">${poids}</td>
      <td class="rg-num">${rgEsc(r.ptsLabel)}</td>
      <td class="rg-rule">${rgEsc(r.regle)}</td>
    </tr>`;
  }).join('');
  const tot=rgAchatV2Total();
  const foot=tot.n?`<tfoot>
      <tr class="rg-row-total">
        <th scope="row">Total max. provisoire</th>
        <td class="rg-num">—</td>
        <td class="rg-num">${rgNum(tot.sum)}</td>
        <td class="rg-rule">${rgEsc(tot.detail)}.</td>
      </tr>
    </tfoot>`:'';
  return `<div class="rg-table-wrap">
    <table class="rg-table" id="rg-table-actions">
      <thead>
        <tr><th>Critère</th><th>Poids</th><th>Points max</th><th>Règle</th></tr>
      </thead>
      <tbody>${body}</tbody>
      ${foot}
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
  const aliases={rsi:['rsi','rsi_14_hebdo'],macd:['macd','macd_12_26_9','macd_12_26_9_hebdo'],cci:['cci','cci_20_hebdo'],fibonacci:['fibonacci'],elliott:['elliott']};
  const want=aliases[id]||[id];
  return all.find(c=>c&&want.includes(c.id))||null;
}
function rgAchatV2Rule(c){
  if(!c) return '';
  const conds=(c.conditions||[]).map(x=>(x.label||x.id||'')+' : '+rgFmtPlus(x.points)+' points');
  const bits=[];
  if(c.preambule) bits.push(String(c.preambule).trim());
  if(conds.length) bits.push(conds.join(' ; ')+'.');
  if(c.precision) bits.push(String(c.precision).trim());
  else{
    if(c.cumulables===false) bits.push('Paliers non cumulables.');
    else if(c.cumulables) bits.push('Conditions cumulables.');
    if(c.max!=null) bits.push('Maximum '+rgNum(c.max)+' points.');
    if(c.retrait===false) bits.push('Aucun retrait.');
  }
  return bits.join(' ').replace(/\s+/g,' ').trim();
}
function rgAchatV2RuleShort(c){
  if(!c) return '';
  if(c.regle_courte) return String(c.regle_courte).trim();
  if(c.regle) return String(c.regle).trim();
  const conds=(c.conditions||[]).map(x=>(x.label||x.id||'')+' : '+rgFmtPlus(x.points));
  const bits=[];
  if(c.preambule) bits.push(String(c.preambule).trim().replace(/\.$/, ''));
  if(conds.length) bits.push(conds.join(' ; ')+'.');
  if(c.cumulables===false) bits.push('Paliers non cumulables.');
  else if(c.cumulables) bits.push('Cumulables.');
  return bits.join(' ').replace(/\s+/g,' ').trim();
}
function rgActionsGrid(v, opts){
  v=v||((RG&&RG.apex_achat_v2)||{});
  opts=opts||{};
  const ordre=['rsi_14_hebdo','macd_12_26_9_hebdo','fibonacci','cci_20_hebdo'];
  const by={};
  (v.criteres||[]).forEach(c=>{if(c&&c.id) by[c.id]=c;});
  const tech=ordre.map(id=>by[id]).filter(Boolean);
  const techSum=tech.reduce((s,c)=>s+(Number(c.max)||0),0);
  const fond=v.fondamental||{};
  const fondPerso=false;
  const fondMax=fond.max!=null?Number(fond.max):90;
  const boardId=opts.boardId||'rg-table-actions';
  const card=(id, label, ruleHtml, pts)=>`<article class="rg-card" data-id="${rgEsc(id||'')}">
      <span class="rg-card-pts">${rgEsc(pts)}</span>
      <h3 class="rg-card-name">${rgEsc(label)}</h3>
      <p class="rg-card-rule">${ruleHtml}</p>
    </article>`;
  const techName=c=>{
    const id=c.id||'';
    if(id.startsWith('rsi')) return 'RSI';
    if(id.startsWith('macd')) return 'MACD';
    if(id.indexOf('fibonacci')>=0) return 'Fibonacci';
    if(id.indexOf('cci')>=0) return 'CCI';
    return (c.label||id).split(' ')[0];
  };
  const techNote=tech.map(c=>techName(c)+' '+rgNum(c.max)).join(' · ');
  const techCards=tech.map(c=>card(c.id, c.label||c.id, rgEsc(rgAchatV2RuleShort(c)), c.max!=null?rgNum(c.max):'—')).join('');
  const fondCols=(fond.groupes||[]).map(g=>{
    const cards=(g.elements||[]).map(el=>{
      const perso=el.a_personnaliser===true||fondPerso;
      const bon=el.bon_si?rgEsc(el.bon_si):'';
      const av=el.seuil_a_valider===true?' <span class="rg-av">à valider</span>':'';
      const pers='';
      const rule=(bon||av||pers)?`<span class="rg-seuil">${bon}</span>${av}${pers}`:'';
      const pts=perso?'—':rgFmtPlus(el.points!=null?el.points:fond.points_si_bon);
      return card(el.id, el.label||el.id, rule, pts);
    }).join('');
    return `<div class="rg-fond-col">
      <h3 class="rg-subh">${rgEsc(g.label||g.id||'')}</h3>
      <div class="rg-cards rg-cards-stack">${cards}</div>
    </div>`;
  }).join('');
  const sent=v.sentiment||{};
  const sentMax=sent.max_affiche||(sent.max!=null?('±'+rgNum(sent.max)):'±50');
  const sentCards=(sent.criteres||sent.elements||[]).map(el=>{
    const rule=rgEsc(el.regle_courte||el.regle||el.precision||rgAchatV2RuleShort(el));
    const pts=el.points_max||el.max_affiche||sentMax;
    return card(el.id, el.label||el.id, rule, pts);
  }).join('');
  const sentBlock=sentCards
    ?`<section class="rg-block" data-group="sentiment">
      <header class="rg-block-h">
        <div class="rg-block-title">${rgEsc(sent.label||'Sentiment')}</div>
        <span class="rg-block-pts">${rgEsc(sentMax)}</span>
      </header>
      <div class="rg-cards rg-cards-span">${sentCards}</div>
    </section>`
    :'';
  const fondTitle=fond.label||'Fondamental';
  const fondPts=rgNum(fondMax);
  const note=opts.note||v.champ_application||'';
  const noteHtml=note?`<p class="rg-p rg-app">${rgEsc(note)}</p>`:'';
  return `${noteHtml}<div class="rg-board" id="${rgEsc(boardId)}">
    <section class="rg-block" data-group="technique">
      <header class="rg-block-h">
        <div class="rg-block-title">Technique <span class="rg-group-note">${techNote}</span></div>
        <span class="rg-block-pts">${rgNum(techSum)}</span>
      </header>
      <div class="rg-cards rg-cards-span">${techCards}</div>
    </section>
    <section class="rg-block" data-group="fondamental">
      <header class="rg-block-h">
        <div class="rg-block-title">${rgEsc(fondTitle)}</div>
        <span class="rg-block-pts">${rgEsc(fondPts)}</span>
      </header>
      <div class="rg-fond-cols">${fondCols}</div>
    </section>
    ${sentBlock}
  </div>`;
}
function rgFmtScaleBound(n){
  if(!Number.isFinite(Number(n))) return '—';
  const x=Number(n);
  if(x<0) return '−'+rgNum(Math.abs(x));
  return rgNum(x);
}
function rgActionsScale(v){
  v=v||((RG&&RG.apex_achat_v2)||{});
  const ordre=['rsi_14_hebdo','macd_12_26_9_hebdo','fibonacci','cci_20_hebdo'];
  const by={};
  (v.criteres||[]).forEach(c=>{if(c&&c.id) by[c.id]=c;});
  const techMax=ordre.map(id=>by[id]).filter(Boolean).reduce((s,c)=>s+(Number(c.max)||0),0);
  const fondN=Number((v.fondamental||{}).max);
  const fond=Number.isFinite(fondN)?fondN:0;
  const sent=v.sentiment||{};
  const first=(sent.criteres||sent.elements||[])[0]||{};
  const aff=String(first.points_max||sent.max_affiche||'');
  let sMin=0, sMax=0;
  if(/±/.test(aff) || /±/.test(String(sent.max_affiche||''))){
    const raw=aff||String(sent.max_affiche||'');
    const n=Number(String(raw).replace(/[^\d.,]/g,'').replace(',','.'));
    if(Number.isFinite(n)){ sMin=-n; sMax=n; }
  } else if(sent.max!=null){
    sMax=Number(sent.max)||0;
    sMin=sent.min!=null?Number(sent.min):-Math.abs(sMax);
  }
  const min=sMin;
  const max=techMax+fond+sMax;
  return {min, max, techMax, fond, sMin, sMax, label: rgFmtScaleBound(min)+' à '+rgFmtScaleBound(max)};
}
function rgSectionAccordion(sec){
  /* Structure générique : un bouton + panneau coulissant par section (Actions aujourd'hui, Crypto / Métaux / ETF plus tard). */
  const id=sec.id||'sec';
  const open=!!sec.open;
  const panel='rg-acc-'+id;
  const scale=sec.scale?`<span class="rg-scale">${rgEsc(sec.scale)}</span>`:'';
  return `<section class="rg-sec rg-acc" id="rg-sec-${rgEsc(id)}" data-rg-section="${rgEsc(id)}">
          <button type="button" class="rg-acc-btn" aria-expanded="${open?'true':'false'}" aria-controls="${panel}" data-rg-acc="${rgEsc(id)}">
            <i class="rg-acc-chev" aria-hidden="true"></i>
            <span class="rg-acc-title">${rgEsc(sec.title||id)}</span>
            ${scale}
          </button>
          <div class="rg-acc-panel" id="${panel}"${open?'':' hidden'}>
            <div class="rg-acc-inner">${sec.body||''}</div>
          </div>
        </section>`;
}
function rgAccToggle(btn, force){
  if(!btn) return;
  const open=(force==null)?(btn.getAttribute('aria-expanded')!=='true'):!!force;
  const panel=document.getElementById(btn.getAttribute('aria-controls')||'');
  if(!panel){btn.setAttribute('aria-expanded', open?'true':'false');return;}
  if(open){
    panel.removeAttribute('hidden');
    btn.setAttribute('aria-expanded','false');
    requestAnimationFrame(()=>{btn.setAttribute('aria-expanded','true');});
  }else{
    btn.setAttribute('aria-expanded','false');
    const done=()=>{if(btn.getAttribute('aria-expanded')!=='true') panel.setAttribute('hidden',''); panel.removeEventListener('transitionend', done);};
    panel.addEventListener('transitionend', done);
    setTimeout(done, 450);
  }
}
function rgBindAccordions(root){
  (root||document).querySelectorAll('.rg-acc-btn').forEach(btn=>{
    if(btn._rgAcc) return;
    btn._rgAcc=true;
    btn.addEventListener('click',()=>rgAccToggle(btn));
  });
}
function rgTechWeightScale(renormalise){
  const na=(RG&&RG.note_apex)||{};
  const tech=na.technique||{};
  const sumW=Object.keys(tech).reduce((s,k)=>s+(Number(tech[k])||0),0);
  const techW=Number(na.poids_technique!=null?na.poids_technique:na.poids_timing);
  if(!sumW) return 1;
  if(renormalise!==false && (na.renormaliser_sans_fondamental!==false)) return 1/sumW;
  return (Number.isFinite(techW)?techW:0.5)/sumW;
}
function rgTechPtsMax(id, renormalise){
  const na=(RG&&RG.note_apex)||{};
  const w=Number((na.technique||{})[id]);
  if(!Number.isFinite(w)) return null;
  return rgPtsMax(w*rgTechWeightScale(renormalise));
}
function rgCard(id, label, ruleHtml, pts){
  return `<article class="rg-card" data-id="${rgEsc(id||'')}">
      <span class="rg-card-pts">${rgEsc(pts)}</span>
      <h3 class="rg-card-name">${rgEsc(label)}</h3>
      <p class="rg-card-rule">${ruleHtml}</p>
    </article>`;
}
function rgMetauxChamp(){
  const mx=(RG&&RG.apex_metaux)||{};
  if(mx.intro_courte) return String(mx.intro_courte);
  const na=(RG&&RG.note_apex)||{};
  const amp=rgAmp();
  return 'Or, argent, platine, palladium, leurs ETC et ETF. Note '+rgNum(na.note_min!=null?na.note_min:0)+' à '+rgNum(na.note_max!=null?na.note_max:100)+', base '+rgNum(amp.base)+'.';
}
function rgMetauxScale(){
  const na=(RG&&RG.note_apex)||{};
  const lo=na.note_min!=null?Number(na.note_min):0;
  const hi=na.note_max!=null?Number(na.note_max):100;
  return {min:lo, max:hi, label: rgFmtScaleBound(lo)+' à '+rgFmtScaleBound(hi)};
}
function rgMetauxRulesShort(){
  /* t463u : une ligne par critère, mêmes seuils que le code, format du tableau Actions. */
  const mx=(RG&&RG.apex_metaux)||{};
  const cfg=mx.regles_courtes||{};
  const na=(RG&&RG.note_apex)||{};
  const cy=(RG&&RG.cyan)||{};
  const gi=(RG&&RG.good_invest)||{};
  const tt=(RG&&RG.template_trade)||{};
  const unite=tt.unite||'$';
  const fondSeuil=rgNum(na.fond_seuil!=null?na.fond_seuil:40);
  const fondPen=rgNum(na.fond_pen_max!=null?na.fond_pen_max:20);
  return {
    structure: cfg.structure||'',
    fibonacci: cfg.fibonacci||'',
    rsi: cfg.rsi||'',
    macd: cfg.macd||'',
    cci: cfg.cci||'',
    fond: cfg.fond||('Minières seulement, si disponible. Pénalité si < '+fondSeuil+' /100, plafonnée à '+fondPen),
    gi: '≥ '+rgNum(gi.seuil!=null?gi.seuil:75)+' /100'+(gi.hors_portefeuille?', hors portefeuille':'')+'. '+rgNum(tt.base_note!=null?tt.base_note:75)+' = '+rgNum(tt.base_montant!=null?tt.base_montant:500)+'\u00a0'+unite+' ; +'+rgNum(tt.pas_montant!=null?tt.pas_montant:100)+'\u00a0'+unite+' par palier de '+rgNum(tt.pas_note!=null?tt.pas_note:5),
    cyan: 'Note ≥ '+rgNum(cy.note_min!=null?cy.note_min:80)+' : AV ≥ +'+rgNum(cy.av_achat_fort!=null?cy.av_achat_fort:60)+' et divergence haussière hebdo ; sinon plafond '+rgNum(cy.plafond_sans_confirmation!=null?cy.plafond_sans_confirmation:75)
  };
}
function rgMetauxGrid(){
  const na=(RG&&RG.note_apex)||{};
  const amp=rgAmp();
  const ordre=['structure','fibonacci','rsi','macd','cci']; /* t461u : hors critère elliott, poids conservé au dénominateur */
  const labels={structure:'Structure',fibonacci:'Fibonacci',rsi:'RSI',macd:'MACD',cci:'CCI'};
  const rules=rgMetauxRulesShort();
  const techCards=ordre.map(id=>{
    const pts=rgTechPtsMax(id, true);
    return rgCard(id, labels[id]||id, rgEsc(rules[id]||''), pts!=null?rgFmtPts(pts):'—');
  }).join('');
  const techNote=ordre.map(id=>{
    const pts=rgTechPtsMax(id, true);
    const short=id==='structure'?'Struct.':(id==='fibonacci'?'Fibo':id.toUpperCase());
    return short+' '+(pts!=null?rgFmtPts(pts):'—');
  }).join(' · ');
  const elliottPts=rgTechPtsMax('elliott', true);
  const techSum=(elliottPts!=null&&Number.isFinite(elliottPts))?(amp.totale-elliottPts):amp.totale;
  const fondMax=rgPtsMax(Number(na.poids_fondamental!=null?na.poids_fondamental:0.5));
  const fondCards=rgCard('fond','Fondamental (minières)',rgEsc(rules.fond||''), fondMax!=null?rgFmtPts(fondMax):'—');
  const cy=(RG&&RG.cyan)||{};
  const gi=(RG&&RG.good_invest)||{};
  const entreesCards=[
    rgCard('gi','Meilleures entrées',rgEsc(rules.gi), '≥ '+rgNum(gi.seuil!=null?gi.seuil:75)),
    rgCard('cyan','Portail cyan',rgEsc(rules.cyan), cy.plafond_sans_confirmation!=null?rgNum(cy.plafond_sans_confirmation):'75')
  ].join('');
  const note=rgMetauxChamp();
  const noteHtml=note?`<p class="rg-p rg-app">${rgEsc(note)}</p>`:'';
  return `${noteHtml}<div class="rg-board" id="rg-table-metaux">
    <section class="rg-block" data-group="technique">
      <header class="rg-block-h">
        <div class="rg-block-title">Technique <span class="rg-group-note">${techNote}</span></div>
        <span class="rg-block-pts">±${rgNum(techSum)}</span>
      </header>
      <div class="rg-cards rg-cards-span">${techCards}</div>
    </section>
    <section class="rg-block" data-group="fondamental">
      <header class="rg-block-h">
        <div class="rg-block-title">Fondamental</div>
        <span class="rg-block-pts">${fondMax!=null?rgFmtPts(fondMax):'—'}</span>
      </header>
      <div class="rg-cards rg-cards-span">${fondCards}</div>
    </section>
    <section class="rg-block" data-group="entree">
      <header class="rg-block-h">
        <div class="rg-block-title">Entrée</div>
      </header>
      <div class="rg-cards rg-cards-span">${entreesCards}</div>
    </section>
  </div>`;
}
function rgPageHTML(){
  if(!RG) return '<p class="rg-p">Règles indisponibles.</p>';
  const fr=RG.fiche_regles||{};
  const titre=fr.page_titre||fr.titre_panneau||'Règles de la note APEX';
  const vAct=(RG&&RG.apex_achat_v2)||{};
  const vBan=(RG&&RG.apex_achat_v2_banque)||null;
  const sections=[
    {id:'actions', title:vAct.section_titre||'Actions (hors banque)', scale:rgActionsScale(vAct).label, body:rgActionsGrid(vAct,{boardId:'rg-table-actions', note:vAct.champ_application}), open:true},
    vBan?{id:'banques', title:vBan.section_titre||vBan.titre||'Actions bancaires', scale:rgActionsScale(vBan).label, body:rgActionsGrid(vBan,{boardId:'rg-table-banques', note:vBan.champ_application||vBan.intro}), open:false}:null,
    {id:'metaux', title:'Métaux précieux', scale:rgMetauxScale().label, body:rgMetauxGrid(), open:false}
  ].filter(Boolean);
  return `<header class="rg-top">
      <button type="button" id="rgBack" class="rg-back">← Retour</button>
      <h1 id="rgPageTitle">${rgEsc(titre)}</h1>
      <button type="button" id="rgClose" class="rg-close">Fermer</button>
    </header>
    <div class="rg-page-body">
      <div class="rg-page-main">
        <div class="rg-pane rg-pane-long" id="rg-pane-long">
          <h2 class="rg-pane-h">LONG</h2>
          ${sections.map(rgSectionAccordion).join('')}
          ${rgCommons()}
        </div>
        <div class="rg-pane rg-pane-short" id="rg-pane-short">
          <h2 class="rg-pane-h">SHORT</h2>
          <p class="rg-p rg-short-empty">Règles SHORT à définir</p>
        </div>
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
  rgBindAccordions(page);
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
