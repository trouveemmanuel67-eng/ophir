/* ===== MEILLEURS SHORT : uniquement les notes APEX rouges (échelle −50..250) (t501u) =====
   Affiche la vraie note APEX, même couleur et même échelle que partout, triée de la plus basse
   à la plus haute. Seuil = bande rouge de pilotBand / PILOT_BANDS_250 : 10 ≤ note < 70
   (10 inclus, 70 déjà orange ; sous 10, violet, hors liste).
   Mise (levier ×5) : 100 $ à 69 (dernière note entière rouge), +20 $ / 24 pts, 200 $ max à −50.
   Exposition équivalente = mise × 5.
   Univers : actions USA/France, métaux, crypto, ETF par devise — uniquement les notes sur 250.
   Les notes APEX ne sont pas recalculées ni modifiées.
*/
const GS_ROUGE_DE=10;
const GS_ROUGE_A=70;
const GS_SEUIL=69;
const GS_VALIDE_KEY='apex-short-valide';
const GS_LIST_KEY='apex-short-list';
const GS_ELLIOTT_KEY='apex-short-elliott-hide';
const GS_PATTERN_KEY='apex-short-pattern-hide';
let gsShowValides=false;

function gsIsRouge(note){
  const n=Number(note);
  if(!Number.isFinite(n)) return false;
  if(typeof pilotBand==='function'){
    return pilotBand(n, {total:n, scale:250, total_max:250}).id==='rouge';
  }
  return n>=GS_ROUGE_DE && n<GS_ROUGE_A;
}
function gsMontant(note){
  /* Mise (levier ×5) : 100 $ à 69, +20 $ / 24 pts, 200 $ max à −50. Uniquement notes rouges. */
  const n=Number(note);
  if(!Number.isFinite(n)||!gsIsRouge(n)) return null;
  const steps=Math.round((GS_SEUIL-Math.max(n,-50))/24);
  return Math.min(100+steps*20, 200);
}
function gsExpo(mise){
  return (mise==null)?null:mise*5;
}
function gsIsUsaFranceTv(tv){
  if(!tv) return false;
  const p=String(tv).split(':')[0];
  return p==='NYSE'||p==='NASDAQ'||p==='AMEX'||p==='EURONEXT';
}
function gsIsScale250(rec){
  if(!rec||typeof rec!=='object') return false;
  const sc=Number(rec.scale!=null?rec.scale:rec.total_max);
  return sc===250||rec.v2===true;
}
function gsMonthKey(d){
  const x=d||((typeof giNow==='function')?giNow():new Date());
  return x.getFullYear()+'-'+String(x.getMonth()+1).padStart(2,'0');
}
function gsHideMap(key){
  let raw=null;
  try{ raw=JSON.parse(localStorage.getItem(key)||'{}'); }catch(e){ raw={}; }
  if(!raw||typeof raw!=='object'||Array.isArray(raw)) raw={};
  const month=gsMonthKey();
  const out={};
  let changed=false;
  Object.keys(raw).forEach(k=>{
    if(raw[k]===month) out[k]=month;
    else changed=true;
  });
  if(changed){
    try{ localStorage.setItem(key, JSON.stringify(out)); }catch(e){}
  }
  return out;
}
function gsIsHidden(tv, map){
  if(!tv) return false;
  return !!((map||{})[String(tv)]);
}
function gsHideUntilMonth(key, tv){
  if(!tv) return;
  const map=gsHideMap(key);
  map[String(tv)]=gsMonthKey();
  try{ localStorage.setItem(key, JSON.stringify(map)); }catch(e){}
}
function gsValideMap(){
  let raw=null;
  try{ raw=JSON.parse(localStorage.getItem(GS_VALIDE_KEY)||'{}'); }catch(e){ raw={}; }
  if(!raw||typeof raw!=='object'||Array.isArray(raw)) raw={};
  const out={};
  Object.keys(raw).forEach(k=>{
    const v=raw[k];
    if(v) out[String(k)]=v===true?true:v;
  });
  return out;
}
function gsIsValide(tv, map){
  if(!tv) return false;
  return !!((map||gsValideMap())[String(tv)]);
}
function gsSetValide(tv, on){
  if(!tv) return;
  const map=gsValideMap();
  const k=String(tv);
  if(on) map[k]=true;
  else delete map[k];
  try{ localStorage.setItem(GS_VALIDE_KEY, JSON.stringify(map)); }catch(e){}
}

function gsPush(out, rec){
  if(!rec||!rec.tv||rec.note==null||!gsIsRouge(rec.note)) return;
  const k=rec.tv;
  const prev=out.get(k);
  if(!prev){ out.set(k, rec); return; }
  if(rec.note<prev.note||(rec.note===prev.note&&String(rec.tv)<String(prev.tv))){
    out.set(k, rec);
  }
}

function gsFromApex(tv, nom, section, rec, tab, yahoo, ticker){
  if(!tv||!rec||!gsIsScale250(rec)||rec.note==null||rec.cap==='moyenne') return null;
  const note=Number(rec.note);
  if(!Number.isFinite(note)) return null;
  const hex=rec.hex||((typeof pilotHex==='function')?pilotHex({total:note, scale:250, total_max:250}):'#e6c27a');
  return {
    tv, nom:nom||tv, section:section||'', note,
    display:rec.display||String(note).replace('.',','), hex, flag:rec.flag||null,
    cap:rec.cap, tab:tab||'', yahoo:yahoo||'', ticker:ticker||'',
    scale:250, montant:gsMontant(note), expo:gsExpo(gsMontant(note))
  };
}

function gsCollect(){
  const out=new Map();
  const take=(tv, nom, section, rec, tab, yahoo, ticker)=>{
    gsPush(out, gsFromApex(tv, nom, section, rec, tab, yahoo, ticker));
  };

  /* Actions USA / France (notes APEX v2 sur 250 déjà publiées). */
  if(typeof PILOT!=='undefined'&&PILOT&&PILOT.by_tv){
    Object.keys(PILOT.by_tv).forEach(tv=>{
      const r=PILOT.by_tv[tv];
      if(!r||r.ok===false||r.total==null) return;
      if(r.kind&&r.kind!=='action') return;
      if(!gsIsUsaFranceTv(tv)) return;
      const rec={note:r.total, scale:(PILOT.scale&&PILOT.scale.max!=null)?Number(PILOT.scale.max):250, v2:true, hex:r.hex};
      take(tv, r.nom||tv, r.kind==='etf'?'ETF sectoriel':'Action', rec, 'actions', r.yahoo||'', r.ticker||'');
    });
  }

  /* Métaux */
  if(typeof MT!=='undefined'&&MT&&MT.rows){
    MT.rows.forEach(r=>{
      const ml=r.mlist||{};
      [ml.head].concat(ml.items||[]).forEach(it=>{
        if(!it||it.skip_score) return;
        take(it.tv||it.ticker, it.name||it.nom, 'Métaux – '+(r.nom||''), it.apex10, 'metaux', it.yahoo, it.ticker);
      });
    });
  }

  /* Crypto (XRP hors APEX, comme Meilleures entrées) */
  const CF=(typeof T2!=='undefined'&&T2&&T2.crypto&&T2.crypto.fiches)?T2.crypto.fiches:null;
  const assets=CF&&CF.assets||(typeof T2!=='undefined'&&T2&&T2.crypto&&T2.crypto.assets)||[];
  (typeof cxApexAssets==='function'?cxApexAssets(assets):assets.filter(a=>String((a&&a.key)||'').toLowerCase()!=='xrp')).forEach(a=>{
    take(a.tv||a.sym, a.nom||a.name, 'Crypto', a.apex10, 'crypto', a.yahoo, a.ticker||a.sym);
  });

  /* ETF par devise uniquement (pas la note /100 de la devise) */
  const fx=(((typeof T2!=='undefined'&&T2&&T2.liquidites)||{}).fx)||{};
  (fx.assets||[]).forEach(a=>{
    const e=a.etf_local;
    if(e&&e.ok&&e.tv&&e.apex10) take(e.tv, e.nom||e.court||e.tv, 'Liquidités – ETF par devise', e.apex10, 'liquidites', e.yahoo, (e.tv||'').split(':')[1]||'');
  });

  return [...out.values()]
    .sort((a,b)=> (a.note-b.note) || String(a.tv).localeCompare(String(b.tv)));
}

function gsListIsOpen(){
  const c=document.getElementById('bestShortCard');
  return !!(c&&!c.classList.contains('pos-collapsed'));
}
function gsSetListOpen(on,persist){
  const c=document.getElementById('bestShortCard');
  if(!c) return;
  c.classList.toggle('pos-collapsed',!on);
  const head=c.querySelector('.pos-rail-h');
  if(head) head.setAttribute('aria-expanded', on?'true':'false');
  if(persist!==false){ try{ localStorage.setItem(GS_LIST_KEY, on?'1':'0'); }catch(e){} }
  if(typeof posSyncListChrome==='function') posSyncListChrome(typeof posListIsOpen==='function'&&posListIsOpen());
}
function gsTickerCourt(tv){
  if(typeof giTickerCourt==='function') return giTickerCourt(tv);
  if(!tv) return '';
  const s=String(tv);
  const i=s.lastIndexOf(':');
  return i>=0?s.slice(i+1):s;
}

function gsRender(){
  const host=document.getElementById('mes-pos');
  if(!host) return;
  const hiddenE=gsHideMap(GS_ELLIOTT_KEY);
  const hiddenP=gsHideMap(GS_PATTERN_KEY);
  const valides=gsValideMap();
  const all=gsCollect().filter(it=>!gsIsHidden(it.tv, hiddenE)&&!gsIsHidden(it.tv, hiddenP));
  const list=all.filter(it=>!gsIsValide(it.tv, valides));
  const listVal=all.filter(it=>gsIsValide(it.tv, valides));
  const n=list.length;
  const nVal=listVal.length;
  const rowOf=(it, checked)=>{
    const col=it.hex||((typeof pilotHex==='function')?pilotHex({total:it.note, scale:250, total_max:250}):'#e6c27a');
    const note=it.display||String(it.note).replace('.',',');
    const mise=it.montant;
    const expo=(it.expo!=null)?it.expo:gsExpo(mise);
    const amt=mise==null?'—':(mise+' $<small class="gs-expo">expo '+expo+' $</small>');
    const label=it.tv?gsTickerCourt(it.tv):(it.nom||'');
    const go=it.tv
      ? `<button type="button" class="gi-link gs-link" data-tab="${(it.tab||'').replace(/"/g,'')}" data-tv="${String(it.tv).replace(/"/g,'&quot;')}" title="${String(it.nom||it.tv).replace(/"/g,'&quot;')}">${String(label).replace(/</g,'')}</button>`
      : `<span class="pos-nm" title="${String(it.nom||'').replace(/"/g,'&quot;')}">${(it.nom||'').replace(/</g,'')}</span>`;
    const tip=[it.nom,it.tv, (mise!=null?('Mise '+mise+' $ (levier ×5) · exposition '+(expo)+' $'):'')].filter(Boolean).join(' · ');
    const cp=it.tv?((typeof ophirCopyBtn==='function')?ophirCopyBtn(it.tv):`<button type="button" class="cp" data-c="${String(it.tv).replace(/"/g,'&quot;')}" aria-label="Copier ${String(it.tv).replace(/"/g,'&quot;')}" title="Copier ${String(it.tv).replace(/"/g,'&quot;')}">⎘</button>`):'';
    const ev=it.tv
      ? `<div class="gi-acts"><button type="button" class="gi-elliott gs-elliott" data-tv="${String(it.tv).replace(/"/g,'&quot;')}" title="Retirer : vague Elliott non propice au short" aria-label="Retirer : vague Elliott non propice au short">E</button><button type="button" class="gi-pattern gs-pattern" data-tv="${String(it.tv).replace(/"/g,'&quot;')}" title="Pattern haussier : retirer jusqu'au 1er du mois" aria-label="Pattern haussier : retirer jusqu'au 1er du mois">P</button><button type="button" class="gi-valid gs-valid${checked?' is-on':''}" data-tv="${String(it.tv).replace(/"/g,'&quot;')}" title="${checked?'Retirer de Validés (erreur)':'Validé : déjà entré en short'}" aria-label="${checked?'Retirer de Validés':'Validé'}" aria-pressed="${checked?'true':'false'}">✓</button>${cp}</div>`
      : '';
    return `<article class="gi-row${it.tv?' has-fiche':''}" title="${tip.replace(/"/g,'&quot;')}">
      <div class="gi-id">${go}</div>
      ${ev}
      <span class="gi-note" style="color:${col}"><b>${note}</b><small>/250</small></span>
      <span class="gi-amt gs-amt" title="${mise!=null?('Mise '+mise+' $ (levier ×5) · exposition '+expo+' $'):''}">${amt}</span>
    </article>`;
  };
  const rows=list.map(it=>rowOf(it, false)).join('');
  const rowsVal=listVal.map(it=>rowOf(it, true)).join('');
  const html=`<div class="card no-group" id="bestShortCard">
    <div class="pos-rail-h" role="button" tabindex="0" aria-expanded="false" aria-controls="gsBody">
      <span class="pos-chev" aria-hidden="true">▸</span>
      <h2>Meilleurs short</h2>
      <span class="pos-head-tot">${n}<small>titre${n>1?'s':''}</small></span>
    </div>
    <div class="pos-body gi-body" id="gsBody">
      <p class="gs-warn">Le short peut faire perdre plus que la mise. Il faut un compte qui l’autorise (CFD chez XTB, par exemple). Levier ×5, marge commune Revolut : les shorts se soutiennent entre eux, mais une hausse générale du marché touche toutes les positions en même temps et peut déclencher un appel de marge sur l’ensemble.</p>
      <p class="gs-legende">Montants : mise (levier ×5). En petit : exposition équivalente.</p>
      <div class="gi-list">${rows||'<div class="gi-empty">Aucun titre au seuil (note APEX rouge, 10 ≤ note < 70/250).</div>'}</div>
      ${(nVal||gsShowValides)?`<div class="gi-valides">
        <button type="button" class="gi-valides-link gs-valides-link" aria-expanded="${gsShowValides?'true':'false'}">Validés (${nVal})</button>
        ${gsShowValides?(rowsVal||'<div class="gi-empty">Aucun titre validé en short.</div>'):''}
      </div>`:''}
    </div>
  </div>`;
  const wasOpen=gsListIsOpen();
  let saved=null;
  try{ saved=localStorage.getItem(GS_LIST_KEY); }catch(e){}
  const prev=document.getElementById('bestShortCard');
  const gi=document.getElementById('goodInvestCard');
  if(prev) prev.outerHTML=html;
  else if(gi) gi.insertAdjacentHTML('afterend', html);
  else host.insertAdjacentHTML('beforeend', html);

  const card=document.getElementById('bestShortCard');
  if(!card) return;
  const open=wasOpen||saved==='1';
  card.classList.toggle('pos-collapsed', !open);
  const head=card.querySelector('.pos-rail-h');
  if(head){
    head.setAttribute('aria-expanded', open?'true':'false');
    const tog=e=>{ e.preventDefault(); gsSetListOpen(!gsListIsOpen()); };
    head.addEventListener('click',tog);
    head.addEventListener('keydown',e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();tog(e);}});
  }
  card.querySelectorAll('.gs-link').forEach(b=>b.addEventListener('click',()=>{
    if(window.matchMedia('(max-width:1099px)').matches) gsSetListOpen(false);
    if(typeof posOpenFiche==='function') posOpenFiche(b.dataset.tab,b.dataset.tv);
  }));
  card.querySelectorAll('.gs-elliott').forEach(b=>b.addEventListener('click',e=>{
    e.preventDefault(); e.stopPropagation();
    gsHideUntilMonth(GS_ELLIOTT_KEY, b.dataset.tv);
    gsRender();
  }));
  card.querySelectorAll('.gs-pattern').forEach(b=>b.addEventListener('click',e=>{
    e.preventDefault(); e.stopPropagation();
    gsHideUntilMonth(GS_PATTERN_KEY, b.dataset.tv);
    gsRender();
  }));
  card.querySelectorAll('.gs-valid').forEach(b=>b.addEventListener('click',e=>{
    e.preventDefault(); e.stopPropagation();
    const tv=b.dataset.tv;
    gsSetValide(tv, !gsIsValide(tv));
    gsRender();
  }));
  const vLink=card.querySelector('.gs-valides-link');
  if(vLink){
    vLink.addEventListener('click',e=>{
      e.preventDefault(); e.stopPropagation();
      gsShowValides=!gsShowValides;
      gsRender();
    });
  }
  if(typeof posSyncListChrome==='function') posSyncListChrome(typeof posListIsOpen==='function'&&posListIsOpen());
}
function gsInit(){
  gsRender();
}
