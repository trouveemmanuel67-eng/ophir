/* ===== MEILLEURS SHORT : note SHORT sur 250 (APE-32, validée par Emmanuel le 24/11/2026) =====
   Note distincte de la note LONG, calculée par src/build_short250.py (data/apex_short.json) :
   RSI 25 + MACD 25 + CCI 25 + fondamental inversé 125 + sentiment du secteur inversé ±30 (t537u) + hype inversée ±20.
   Plus la note est haute, meilleur est le candidat short : tri de la plus haute à la plus basse.
   Entrée dans la liste : note SHORT ≥ 70/250 (orange, vert ou cyan), jusqu’à 10 titres, triés de la plus haute à la plus basse. Également : (RSI, MACD ou CCI ≥ 10 pts) ET filtre Fibonacci (cours au niveau 38,2 % ou au-dessus, ATH et au-delà autorisés). Ces filtres ne changent pas avec la MM40 hebdo inversée (0 à +30), qui entre seulement dans la note.
   Mise (levier ×5) : 100 $ à 70, +20 $ tous les 24 points au-dessus (94, 118, 142, 166), 200 $ max dès 190.
   Exposition équivalente = mise × 5. Univers (t534u) : 50 actions NYSE en CFD chez Revolut, RSI hebdo en surachat, santé en dégradation
   (config/univers_short.json, src/build_univers_short.py) ; plus la watchlist APEX.
   La note LONG n'est pas modifiée.
*/
const GS_SEUIL=70;
const GS_SEUIL_LISTE=70;
const GS_LISTE_MAX=10;
const GS_PALIER=24;
const GS_MISE_BASE=100;
const GS_MISE_PAS=20;
const GS_MISE_MAX=200;
const GS_VALIDE_KEY='apex-short-valide';
const GS_LIST_KEY='apex-short-list';
const GS_ELLIOTT_KEY='apex-short-elliott-hide';
const GS_PATTERN_KEY='apex-short-pattern-hide';
let SHORT=(()=>{try{const el=document.getElementById('dataShort');return el?JSON.parse(el.textContent):null;}catch(e){return null;}})();
function gsApplyShort(d){ if(d&&d.by_tv){ SHORT=d; const el=document.getElementById('dataShort'); if(el) el.textContent=JSON.stringify(d);} }
let gsShowValides=false;

function gsSeuil(){
  const s=SHORT&&Number(SHORT.seuil);
  return Number.isFinite(s)?s:GS_SEUIL;
}
function gsSeuilListe(){
  const s=SHORT&&Number(SHORT.seuil_liste);
  return Number.isFinite(s)?s:GS_SEUIL_LISTE;
}
function gsAuSeuil(note){
  const n=Number(note);
  return Number.isFinite(n)&&n>=gsSeuil();
}
function gsMontant(note){
  /* 100 $ à 70, +20 $ par palier entier de 24 points au-dessus, 200 $ max (dès 190). Exposition = mise × 5. */
  const n=Number(note);
  if(!gsAuSeuil(n)) return null;
  const steps=Math.floor((n-gsSeuil())/GS_PALIER);
  return Math.min(GS_MISE_BASE+steps*GS_MISE_PAS, GS_MISE_MAX);
}
function gsExpo(mise){
  return (mise==null)?null:mise*5;
}
const GS_CAT={action:'Action', banque:'Action bancaire', energie:'Énergie'};
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

function gsCollect(){
  const by=(SHORT&&SHORT.by_tv)||{};
  const sl=gsSeuilListe();
  const crypto=/^(XRP|BTC|ETH|DOGE|SOL|ADA|AVAX|AAVE|UNI|HBAR)(-|$)/i;
  return Object.keys(by).map(tv=>by[tv]).filter(r=>{
    if(!r||!r.tv||r.note==null||r.fibo_ok!==true||r.tech_ok===false||r.held_position) return false;
    const tick=String(r.tv).split(':').pop();
    if(crypto.test(tick)||/^XRP/i.test(tick)) return false;
    if(r.liste===false) return false;
    return Number(r.note)>=sl;
  }).map(r=>{
    const note=Number(r.note);
    const mise=gsMontant(note);
    const hex=(typeof pilotHex==='function')?pilotHex({total:note, scale:250, total_max:250}):'#22c55e';
    return {
      tv:r.tv, nom:r.nom||r.tv, section:GS_CAT[r.categorie]||'', note, display:String(note), hex,
      tab:r.tab||'actions', yahoo:r.yahoo||'', ticker:r.ticker||'', scale:250, ligne:r.ligne||'',
      montant:mise, expo:gsExpo(mise),
      cfd:r.cfd_revolut||'', rsiH:r.rsi_hebdo, deg:((r.degradation&&r.degradation.signes)||[]).join(' ; '), palier:r.palier||''
    };
  }).sort((a,b)=> (b.note-a.note) || String(a.tv).localeCompare(String(b.tv)));
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
  const cap=Math.max(0, Number((SHORT&&SHORT.n_liste_max)||GS_LISTE_MAX)||10);
  const verd=all.slice(0, cap);
  const list=verd.filter(it=>!gsIsValide(it.tv, valides));
  const listVal=verd.filter(it=>gsIsValide(it.tv, valides));
  const n=list.length;
  const nVal=listVal.length;
  const rowOf=(it, checked)=>{
    const col=it.hex||((typeof pilotHex==='function')?pilotHex({total:it.note, scale:it.scale||250, total_max:it.scale||250}):'#e6c27a');
    const note=it.display||String(it.note).replace('.',',');
    const mise=it.montant;
    const expo=(it.expo!=null)?it.expo:gsExpo(mise);
    const amt=mise==null?'—':(mise+' $<small class="gs-expo">expo '+expo+' $</small>');
    const label=it.tv?gsTickerCourt(it.tv):(it.nom||'');
    const go=it.tv
      ? `<button type="button" class="gi-link gs-link" data-tab="${(it.tab||'').replace(/"/g,'')}" data-tv="${String(it.tv).replace(/"/g,'&quot;')}" title="${String(it.nom||it.tv).replace(/"/g,'&quot;')}">${String(label).replace(/</g,'')}</button>`
      : `<span class="pos-nm" title="${String(it.nom||'').replace(/"/g,'&quot;')}">${(it.nom||'').replace(/</g,'')}</span>`;
    const tip=[it.nom,it.tv,it.section,it.ligne?('SHORT : '+it.ligne):'', (mise!=null?('Mise '+mise+' $ (levier ×5) · exposition '+(expo)+' $'):''),
      (it.rsiH!=null?('RSI hebdo '+String(it.rsiH).replace('.',',')):''), (it.deg?('Dégradation : '+it.deg):''), (it.cfd?('CFD Revolut : '+it.cfd):'')].filter(Boolean).join(' · ');
    const cp=it.tv?((typeof ophirCopyBtn==='function')?ophirCopyBtn(it.tv):`<button type="button" class="cp" data-c="${String(it.tv).replace(/"/g,'&quot;')}" aria-label="Copier ${String(it.tv).replace(/"/g,'&quot;')}" title="Copier ${String(it.tv).replace(/"/g,'&quot;')}">⎘</button>`):'';
    const ev=it.tv
      ? `<div class="gi-acts"><button type="button" class="gi-elliott gs-elliott" data-tv="${String(it.tv).replace(/"/g,'&quot;')}" title="Retirer : vague Elliott non propice au short" aria-label="Retirer : vague Elliott non propice au short">E</button><button type="button" class="gi-pattern gs-pattern" data-tv="${String(it.tv).replace(/"/g,'&quot;')}" title="Pattern haussier : retirer jusqu'au 1er du mois" aria-label="Pattern haussier : retirer jusqu'au 1er du mois">P</button><button type="button" class="gi-valid gs-valid${checked?' is-on':''}" data-tv="${String(it.tv).replace(/"/g,'&quot;')}" title="${checked?'Retirer de Validés (erreur)':'Validé : déjà entré en short'}" aria-label="${checked?'Retirer de Validés':'Validé'}" aria-pressed="${checked?'true':'false'}">✓</button>${cp}</div>`
      : '';
    return `<article class="gi-row${it.tv?' has-fiche':''}" title="${tip.replace(/"/g,'&quot;')}">
      <div class="gi-id">${go}</div>
      ${ev}
      <span class="gi-note" style="color:${col}"><b>${note}</b><small>/${it.scale||250}</small></span>
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
      <div class="gi-list">${rows||'<div class="gi-empty">Aucun titre au seuil (note SHORT ≥ ${gsSeuilListe()}/250, orange, vert ou cyan, signal technique de surachat et cours au-dessus du Fibonacci 38,2 %).</div>'}</div>
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
    /* t534u : univers SHORT propre (hors watchlist APEX) → pas de fiche sur le site : graphique TradingView. */
    if(b.dataset.tab==='short'){ window.open('https://www.tradingview.com/chart/?symbol='+encodeURIComponent(b.dataset.tv),'_blank','noopener'); return; }
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
