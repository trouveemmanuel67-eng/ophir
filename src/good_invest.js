/* ===== MEILLEURES ENTRÉES : actions APEX v2 ≥ 130/250 ; métaux ≥ 130/250 ; autres ≥ 75/100 ===== */
const GI_SEUIL=75;
const GI_SEUIL_V2=130;
const GI_SEUIL_METAUX=130;
function giSeuilOf(it){
  if(it&&it.tab==='actions') return GI_SEUIL_V2;
  if(it&&it.tab==='metaux') return GI_SEUIL_METAUX;
  return GI_SEUIL;
}
const GI_LIST_KEY='apex-gi-list';
const GI_ELLIOTT_KEY='apex-gi-elliott-hide';
function giNow(){
  if(typeof GI_NOW!=='undefined'&&GI_NOW!=null){
    try{ return (typeof GI_NOW==='function')?new Date(GI_NOW()):new Date(GI_NOW); }catch(e){}
  }
  return new Date();
}
function giMonthKey(d){
  const x=d||giNow();
  return x.getFullYear()+'-'+String(x.getMonth()+1).padStart(2,'0');
}
function giElliottHiddenMap(){
  let raw=null;
  try{ raw=JSON.parse(localStorage.getItem(GI_ELLIOTT_KEY)||'{}'); }catch(e){ raw={}; }
  if(!raw||typeof raw!=='object'||Array.isArray(raw)) raw={};
  const month=giMonthKey();
  const out={};
  let changed=false;
  Object.keys(raw).forEach(k=>{
    if(raw[k]===month) out[k]=month;
    else changed=true;
  });
  if(changed){
    try{ localStorage.setItem(GI_ELLIOTT_KEY, JSON.stringify(out)); }catch(e){}
  }
  return out;
}
function giIsElliottHidden(tv, map){
  if(!tv) return false;
  return !!((map||giElliottHiddenMap())[String(tv)]);
}
function giHideElliott(tv){
  if(!tv) return;
  const map=giElliottHiddenMap();
  map[String(tv)]=giMonthKey();
  try{ localStorage.setItem(GI_ELLIOTT_KEY, JSON.stringify(map)); }catch(e){}
}
const GI_PATTERN_KEY='apex-gi-pattern-hide';
function giPatternHiddenMap(){
  let raw=null;
  try{ raw=JSON.parse(localStorage.getItem(GI_PATTERN_KEY)||'{}'); }catch(e){ raw={}; }
  if(!raw||typeof raw!=='object'||Array.isArray(raw)) raw={};
  const month=giMonthKey();
  const out={};
  let changed=false;
  Object.keys(raw).forEach(k=>{
    if(raw[k]===month) out[k]=month;
    else changed=true;
  });
  if(changed){
    try{ localStorage.setItem(GI_PATTERN_KEY, JSON.stringify(out)); }catch(e){}
  }
  return out;
}
function giIsPatternHidden(tv, map){
  if(!tv) return false;
  return !!((map||giPatternHiddenMap())[String(tv)]);
}
function giHidePattern(tv){
  if(!tv) return;
  const map=giPatternHiddenMap();
  map[String(tv)]=giMonthKey();
  try{ localStorage.setItem(GI_PATTERN_KEY, JSON.stringify(map)); }catch(e){}
}
const GI_VALIDE_KEY='apex-gi-valide';
let giShowValides=false;
function giValideMap(){
  let raw=null;
  try{ raw=JSON.parse(localStorage.getItem(GI_VALIDE_KEY)||'{}'); }catch(e){ raw={}; }
  if(!raw||typeof raw!=='object'||Array.isArray(raw)) raw={};
  const out={};
  Object.keys(raw).forEach(k=>{
    const v=raw[k];
    if(v) out[String(k)]=v===true?true:v;
  });
  return out;
}
function giIsValide(tv, map){
  if(!tv) return false;
  return !!((map||giValideMap())[String(tv)]);
}
function giSetValide(tv, on){
  if(!tv) return;
  const map=giValideMap();
  const k=String(tv);
  if(on) map[k]=true;
  else delete map[k];
  try{ localStorage.setItem(GI_VALIDE_KEY, JSON.stringify(map)); }catch(e){}
}
const GI_PAYS_ACTIONS=new Set(['USA','France']);
const GI_PAYS_HORS=['Allemagne','Canada','Suisse','Italie','Japon','Corée du Sud','Corée','Australie'];
function giEstActionHorsUnivers(it){
  if(!it) return false;
  const sec=String(it.section||'');
  if(/Indice\s*\/\s*ETF pays|Obligations|Métaux|Crypto|ENERGIE|Indices\s*&|Placements|Liquidités/i.test(sec)) return false;
  const pays=sec.split('–')[0].split(' - ')[0].trim();
  if(GI_PAYS_ACTIONS.has(pays)) return false;
  if(GI_PAYS_HORS.some(p=>pays===p||pays.startsWith(p))) return true;
  return false;
}

function giHeldSet(){
  const set=new Set();
  const add=p=>{
    if(!p||typeof p!=='object') return;
    const st=String(p.statut||'active').toLowerCase();
    if(st==='solde'||st==='sold'||st==='ferme'||st==='closed'||st==='annule') return;
    // Actives, ordres en attente et ventes en attente : déjà en portefeuille (ou en cours de sortie).
    [p.fiche_tv,p.tv_note,p.tv,p.ticker,p.yahoo,p.sym].forEach(s=>{
      if(!s) return;
      const u=String(s).trim();
      if(!u||u==='PEA') return;
      set.add(u);
      set.add(u.toUpperCase());
      if(u.includes(':')) set.add(u.split(':').pop());
    });
  };
  (typeof POS!=='undefined'&&POS&&POS.positions||[]).forEach(add);
  (typeof POS_RV!=='undefined'&&POS_RV&&POS_RV.positions||[]).forEach(add);
  (typeof POS_RX!=='undefined'&&POS_RX&&POS_RX.positions||[]).forEach(add);
  return set;
}
function giIsHeld(it, held){
  const keys=[it.tv,it.yahoo,it.ticker,it.sym];
  return keys.some(s=>{
    if(!s) return false;
    const u=String(s).trim();
    if(held.has(u)||held.has(u.toUpperCase())) return true;
    if(u.includes(':')&&held.has(u.split(':').pop())) return true;
    return false;
  });
}
function giMontant(note, scale, tab){
  const n=Number(note);
  if(!Number.isFinite(n)) return null;
  const sc=Number(scale);
  const isMetaux=tab==='metaux'||sc===250&&tab==='metaux';
  if(isMetaux||(tab==='metaux')){
    const base=Number(GI_SEUIL_METAUX)||130, pas=24;
    if(n<base) return null;
    const steps=Math.round((Math.min(n,250)-base)/pas);
    return Math.min(500+steps*100, 1000);
  }
  const src=(typeof TT!=='undefined'&&TT&&Array.isArray(TT.lignes))
    ?TT.lignes.slice().filter(l=>l&&Number.isFinite(Number(l.note))).sort((a,b)=>Number(a.note)-Number(b.note))
    :[];
  const isV2=Number.isFinite(sc)&&sc!==100&&sc>=200;
  let lignes=src;
  if(isV2){
    const baseNote=Number(GI_SEUIL_V2)||130;
    if(src.length>=2){
      const minOld=Number(src[0].note), maxOld=Number(src[src.length-1].note);
      const spanOld=maxOld-minOld;
      if(spanOld>0){
        lignes=src.map(l=>({note:baseNote+((Number(l.note)-minOld)/spanOld)*(sc-baseNote), montant:l.montant}));
      }
    }else{
      lignes=[];
      for(let i=0;i<=5;i++) lignes.push({note:baseNote+i*(sc-baseNote)/5, montant:500+i*100});
    }
  }
  let best=null;
  for(const l of lignes){
    if(l&&Number(l.note)===n) return l.montant;
    if(l&&Number(l.note)<=n&&(!best||Number(l.note)>Number(best.note))) best=l;
  }
  return best?best.montant:null;
}
function giEnrich(prev, rec){
  if(!prev||!rec) return prev;
  if((!prev.nom||prev.nom===prev.tv)&&rec.nom&&rec.nom!==rec.tv) prev.nom=rec.nom;
  if(!prev.section&&rec.section) prev.section=rec.section;
  if(!prev.tab&&rec.tab) prev.tab=rec.tab;
  if(!prev.yahoo&&rec.yahoo) prev.yahoo=rec.yahoo;
  if(!prev.ticker&&rec.ticker) prev.ticker=rec.ticker;
  if(!prev.hex&&rec.hex) prev.hex=rec.hex;
  if(!prev.display&&rec.display) prev.display=rec.display;
  return prev;
}
function giPush(out, rec){
  if(!rec||!rec.tv||rec.note==null||Number(rec.note)<giSeuilOf(rec)) return;
  if(rec.cap==='moyenne') return;
  const k=rec.tv;
  const prev=out.get(k);
  if(!prev){ out.set(k, rec); return; }
  if(rec.note>prev.note||(rec.note===prev.note&&(rec.av||0)>(prev.av||0))){
    giEnrich(rec, prev);
    out.set(k, rec);
    return;
  }
  giEnrich(prev, rec);
}
function giPrecomputed(){
  try{
    const el=document.getElementById('dataGi');
    if(!el) return null;
    const j=JSON.parse(el.textContent||'null');
    if(!j||!Array.isArray(j.liste)) return null;
    const held=giHeldSet();
    return j.liste
      .filter(it=>it&&it.tv&&it.note!=null&&Number(it.note)>=giSeuilOf(it)&&!giIsHeld(it,held)&&!giEstActionHorsUnivers(it))
      .map(it=>Object.assign({},it,{montant:it.montant!=null?it.montant:giMontant(it.note,it.scale,it.tab)}))
      .sort((a,b)=> (b.note-a.note) || ((b.av||0)-(a.av||0)) || String(a.tv).localeCompare(String(b.tv)));
  }catch(e){ return null; }
}
function giStockRecs(){
  const out=[];
  if(!(typeof PILOT!=='undefined'&&PILOT&&PILOT.by_tv)) return out;
  const held=giHeldSet();
  const seen=new Set();
  Object.keys(PILOT.by_tv).forEach(tv=>{
    const r=PILOT.by_tv[tv];
    if(!r||r.total==null||r.ok===false) return;
    if(r.kind&&r.kind!=='action'&&r.kind!=='etf'&&r.kind!=='panier') return;
    if(r.total<GI_SEUIL_V2) return;
    const sc=(typeof PILOT!=='undefined'&&PILOT&&PILOT.scale&&PILOT.scale.max!=null)?Number(PILOT.scale.max):250;
    const it={tv, nom:r.nom||tv, section:r.kind==='panier'?'Panier APEX':(r.kind==='etf'?'ETF sectoriel':'Action'),
      note:r.total, display:String(r.total), hex:r.hex, flag:r.band, scale:sc, tab:'actions',
      ticker:r.ticker||'', yahoo:r.yahoo||'', montant:giMontant(r.total, sc, 'actions')};
    if(giIsHeld(it,held)) return;
    const k=r.tv||tv;
    if(seen.has(k)) return;
    seen.add(k);
    out.push(it);
  });
  return out.sort((a,b)=> (b.note-a.note) || String(a.tv).localeCompare(String(b.tv)));
}
function giCollect(){
  const stocks=giStockRecs();
  const pre=giPrecomputed();
  if(pre){
    const rest=pre.filter(it=>!(typeof isApexV2Tv==='function'&&isApexV2Tv(it.tv)) && !(typeof pilotRec==='function'&&pilotRec(it.tv)) && !giEstActionHorsUnivers(it));
    return stocks.concat(rest).sort((a,b)=> (b.note-a.note) || String(a.tv).localeCompare(String(b.tv)));
  }
  const out=new Map();
  const bars=(typeof APEX_BARS!=='undefined'&&APEX_BARS&&APEX_BARS.bars)?APEX_BARS.bars:{};
  const take=(tv, nom, section, rec, av, tab, yahoo, ticker)=>{
    if(!tv||!rec||rec.note==null) return;
    const score=(av&&typeof av==='object')?av.score:av;
    giPush(out,{
      tv, nom:nom||tv, section:section||'', note:Number(rec.note),
      display:rec.display||String(rec.note).replace('.',','), hex:rec.hex,
      flag:rec.flag, cap:rec.cap, av:score==null?null:Number(score),
      tab:tab||'', yahoo:yahoo||'', ticker:ticker||'',
      scale:(rec.scale!=null?rec.scale:(rec.total_max!=null?rec.total_max:(tab==='metaux'?250:undefined)))
    });
  };
  // Barres individuelles
  Object.keys(bars).forEach(tv=>{
    const b=bars[tv]||{};
    take(tv, tv, '', b.apex10, b.av, '', '', tv.includes(':')?tv.split(':')[1]:tv);
  });
  // USA — tops fondamentaux
  const usaNom=k=>{
    if(typeof SEC!=='undefined'&&SEC&&SEC.sectors){
      const hit=(SEC.sectors||[]).find(x=>x.sym===k||x.ref_us===k||x.tick===k);
      if(hit&&hit.nom) return hit.nom;
    }
    return k;
  };
  if(typeof FOND!=='undefined'&&FOND&&FOND.sectors){
    Object.keys(FOND.sectors).forEach(k=>{
      const s=FOND.sectors[k]||{};
      const sec='USA – '+(s.name||usaNom(k));
      (s.top||[]).forEach(t=>{
        const tv=t.tv||t.ticker||t.yahoo;
        const bar=tv?bars[tv]:null;
        take(tv, t.name||t.nom, sec, t.apex10||(bar&&bar.apex10), (bar&&bar.av)||t.av, 'actions', t.yahoo, t.ticker);
      });
    });
  }
  // ETF de secteur USA (instrument affiché)
  if(typeof SEC!=='undefined'&&SEC&&SEC.sectors){
    (SEC.sectors||[]).forEach(s=>{
      const rec=s.apex10_instrument||null;
      const tv=s.tv||s.sym;
      take(tv, s.etf||s.nom||tv, 'USA – '+(s.nom||''), rec, s.av_instrument||s.av, 'actions', s.yahoo, s.sym);
    });
  }
  // Pays : titres affichés + ETF de tête (hors moyennes de section)
  if(typeof PAYS!=='undefined'&&PAYS&&PAYS.countries){
    PAYS.countries.filter(C=>typeof paysEstDansUnivers!=='function'||paysEstDansUnivers(C)).forEach(C=>{
      const pays=C.nom||C.cc||'';
      const head=C.head||{};
      if(head.tv) take(head.tv, head.etf||head.nom||head.tv, 'Marché '+pays, head.apex10, head.av, 'actions', head.sym, head.sym);
      (C.rows||[]).forEach(r=>{
        const sec=pays+' – '+(r.nom||'');
        if(r.kind==='etf'||r.kind==='index'){
          if(r.tv){
            const bar=bars[r.tv];
            const rec=(bar&&bar.apex10)||r.apex10_instrument||(r.apex10&&r.apex10.cap!=='moyenne'?r.apex10:null);
            take(r.tv, r.etf||r.nom||r.tv, sec, rec, (bar&&bar.av)||r.av_instrument, 'actions', r.sym, r.sym);
          }
        }
        ((r.fond||{}).top||[]).forEach(t=>{
          const tv=t.tv||t.ticker;
          const bar=tv?bars[tv]:null;
          take(tv, t.name||t.nom, sec, t.apex10||(bar&&bar.apex10), (bar&&bar.av)||t.av, 'actions', t.yahoo||t.ticker, t.ticker);
        });
      });
    });
  }
  // Énergie
  const EN=(typeof T2!=='undefined'&&T2&&T2.energie)?T2.energie:(typeof ENERGIE!=='undefined'?ENERGIE:null);
  if(EN&&EN.assets){
    EN.assets.forEach(a=>{
      if(a.repere) return;
      take(a.tv||a.sym, a.nom||a.name, 'Énergie'+(a.groupe?' – '+a.groupe:''), a.apex10, a.av, 'energie', a.yahoo, a.ticker||a.sym);
    });
  }
  // Métaux
  if(typeof MT!=='undefined'&&MT&&MT.rows){
    MT.rows.forEach(r=>{
      const ml=r.mlist||{};
      [ml.head].concat(ml.items||[]).forEach(it=>{
        if(!it||it.skip_score) return;
        take(it.tv||it.ticker, it.name||it.nom, 'Métaux – '+(r.nom||''), it.apex10, it.av, 'metaux', it.yahoo, it.ticker);
      });
    });
  }
  // Crypto
  const CF=(typeof T2!=='undefined'&&T2&&T2.crypto&&T2.crypto.fiches)?T2.crypto.fiches:null;
  const assets=CF&&CF.assets||(typeof T2!=='undefined'&&T2&&T2.crypto&&T2.crypto.assets)||[];
  (typeof cxApexAssets==='function'?cxApexAssets(assets):assets.filter(a=>String((a&&a.key)||'').toLowerCase()!=='xrp')).forEach(a=>{
    take(a.tv||a.sym, a.nom||a.name, 'Crypto', a.apex10, a.av, 'crypto', a.yahoo, a.ticker||a.sym);
  });
  // Obligations (lignes affichées, pas le benchmark de segment)
  if(typeof OB!=='undefined'&&OB&&OB.segments){
    OB.segments.forEach(s=>{
      (s.list||[]).forEach(r=>{
        take(r.tv||r.yahoo, r.name||r.nom, 'Obligations – '+(s.nom||s.key||''), r.apex10, r.av, 'obligations', r.yahoo, r.yahoo);
      });
    });
  }
  // Devises (hors DXY)
  const fx=(((typeof T2!=='undefined'&&T2&&T2.liquidites)||{}).fx)||{};
  (fx.assets||[]).forEach(a=>{
    if(a.repere) return;
    take(a.tv||a.sym, a.nom||a.name, 'Liquidités – devises', a.apex10, a.av, 'liquidites', a.yahoo, a.sym);
  });
  const held=giHeldSet();
  return [...out.values()]
    .filter(it=>!giIsHeld(it, held))
    .map(it=>Object.assign(it,{montant:giMontant(it.note,it.scale,it.tab)}))
    .sort((a,b)=> (b.note-a.note) || ((b.av||0)-(a.av||0)) || String(a.tv).localeCompare(String(b.tv)));
}
function giListIsOpen(){
  const c=document.getElementById('goodInvestCard');
  return !!(c&&!c.classList.contains('pos-collapsed'));
}
function giSetListOpen(on,persist){
  const c=document.getElementById('goodInvestCard');
  if(!c) return;
  c.classList.toggle('pos-collapsed',!on);
  const head=c.querySelector('.pos-rail-h');
  if(head) head.setAttribute('aria-expanded', on?'true':'false');
  if(persist!==false){ try{ localStorage.setItem(GI_LIST_KEY, on?'1':'0'); }catch(e){} }
  if(typeof posSyncListChrome==='function') posSyncListChrome(typeof posListIsOpen==='function'&&posListIsOpen());
}
function giTickerCourt(tv){
  if(!tv) return '';
  const s=String(tv);
  const i=s.lastIndexOf(':');
  return i>=0?s.slice(i+1):s;
}
function giRender(){
  const host=document.getElementById('mes-pos');
  if(!host) return;
  const hidden=giElliottHiddenMap();
  const hiddenP=giPatternHiddenMap();
  const valides=giValideMap();
  const all=giCollect().filter(it=>!giIsElliottHidden(it.tv, hidden)).filter(it=>!giIsPatternHidden(it.tv, hiddenP));
  const list=all.filter(it=>!giIsValide(it.tv, valides));
  const listVal=all.filter(it=>giIsValide(it.tv, valides));
  const n=list.length;
  const nVal=listVal.length;
  const rowOf=(it, checked)=>{
    const col=it.scale===250||it.scale===270?(it.hex||((typeof pilotHex==='function')?pilotHex({total:it.note}):'#e6c27a')):((typeof ttColor==='function')?ttColor(it.note):(it.hex||'#e6c27a'));
    const note=it.display||String(it.note).replace('.',',');
    const amt=(typeof ttMontantTxt==='function')?ttMontantTxt(it.montant, (typeof TT!=='undefined'&&TT&&TT.unite)||'$'):(it.montant==null?'—':it.montant+' $');
    const label=it.tv?giTickerCourt(it.tv):(it.nom||'');
    const go=it.tv
      ? `<button type="button" class="gi-link" data-tab="${(it.tab||'').replace(/"/g,'')}" data-tv="${String(it.tv).replace(/"/g,'&quot;')}" title="${String(it.nom||it.tv).replace(/"/g,'&quot;')}">${String(label).replace(/</g,'')}</button>`
      : `<span class="pos-nm" title="${String(it.nom||'').replace(/"/g,'&quot;')}">${(it.nom||'').replace(/</g,'')}</span>`;
    const tip=[it.nom,it.tv].filter(Boolean).join(' · ');
    const cp=it.tv?((typeof ophirCopyBtn==='function')?ophirCopyBtn(it.tv):`<button type="button" class="cp" data-c="${String(it.tv).replace(/"/g,'&quot;')}" aria-label="Copier ${String(it.tv).replace(/"/g,'&quot;')}" title="Copier ${String(it.tv).replace(/"/g,'&quot;')}">⎘</button>`):'';
    const ev=it.tv
      ? `<div class="gi-acts"><button type="button" class="gi-elliott" data-tv="${String(it.tv).replace(/"/g,'&quot;')}" title="Retirer : vague Elliott non propice" aria-label="Retirer : vague Elliott non propice">E</button><button type="button" class="gi-pattern" data-tv="${String(it.tv).replace(/"/g,'&quot;')}" title="Pattern baissier : retirer jusqu'au 1er du mois" aria-label="Pattern baissier : retirer jusqu'au 1er du mois">P</button><button type="button" class="gi-valid${checked?' is-on':''}" data-tv="${String(it.tv).replace(/"/g,'&quot;')}" title="${checked?'Retirer de Validés (erreur)':'Validé : déjà entré en position'}" aria-label="${checked?'Retirer de Validés':'Validé'}" aria-pressed="${checked?'true':'false'}">✓</button>${cp}</div>`
      : '';
    return `<article class="gi-row${it.tv?' has-fiche':''}" title="${tip.replace(/"/g,'&quot;')}">
      <div class="gi-id">${go}</div>
      ${ev}
      <span class="gi-note" style="color:${col}"><b>${note}</b><small>/${(it.scale===250||it.scale===270)?250:100}</small></span>
      <span class="gi-amt">${amt}</span>
    </article>`;
  };
  const rows=list.map(it=>rowOf(it, false)).join('');
  const rowsVal=listVal.map(it=>rowOf(it, true)).join('');
  const html=`<div class="card no-group" id="goodInvestCard">
    <div class="pos-rail-h" role="button" tabindex="0" aria-expanded="false" aria-controls="giBody">
      <span class="pos-chev" aria-hidden="true">▸</span>
      <h2>Meilleures entrées</h2>
      <span class="pos-head-tot">${n}<small>titre${n>1?'s':''}</small></span>
    </div>
    <div class="pos-body gi-body" id="giBody">
      <div class="gi-list">${rows||'<div class="gi-empty">Aucun titre au seuil (actions ≥ 130/250, métaux ≥ 130/250, autres ≥ 75/100) hors portefeuille.</div>'}</div>
      ${(nVal||giShowValides)?`<div class="gi-valides">
        <button type="button" class="gi-valides-link" aria-expanded="${giShowValides?'true':'false'}">Validés (${nVal})</button>
        ${giShowValides?(rowsVal||'<div class="gi-empty">Aucun titre validé hors portefeuille.</div>'):''}
      </div>`:''}
    </div>
  </div>`;
  const wasOpen=giListIsOpen();
  let saved=null;
  try{ saved=localStorage.getItem(GI_LIST_KEY); }catch(e){}
  const prev=document.getElementById('goodInvestCard');
  if(prev) prev.outerHTML=html;
  else host.insertAdjacentHTML('beforeend', html);
  const card=document.getElementById('goodInvestCard');
  if(!card) return;
  const open=wasOpen||saved==='1';
  card.classList.toggle('pos-collapsed', !open);
  const head=card.querySelector('.pos-rail-h');
  if(head){
    head.setAttribute('aria-expanded', open?'true':'false');
    const tog=e=>{ e.preventDefault(); giSetListOpen(!giListIsOpen()); };
    head.addEventListener('click',tog);
    head.addEventListener('keydown',e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();tog(e);}});
  }
  card.querySelectorAll('.gi-link').forEach(b=>b.addEventListener('click',()=>{
    if(window.matchMedia('(max-width:1099px)').matches) giSetListOpen(false);
    if(typeof posOpenFiche==='function') posOpenFiche(b.dataset.tab,b.dataset.tv);
  }));
  card.querySelectorAll('.gi-elliott').forEach(b=>b.addEventListener('click',e=>{
    e.preventDefault();
    e.stopPropagation();
    giHideElliott(b.dataset.tv);
    giRender();
  }));
  card.querySelectorAll('.gi-pattern').forEach(b=>b.addEventListener('click',e=>{
    e.preventDefault();
    e.stopPropagation();
    giHidePattern(b.dataset.tv);
    giRender();
  }));
  card.querySelectorAll('.gi-valid').forEach(b=>b.addEventListener('click',e=>{
    e.preventDefault();
    e.stopPropagation();
    const tv=b.dataset.tv;
    giSetValide(tv, !giIsValide(tv));
    giRender();
  }));
  const vLink=card.querySelector('.gi-valides-link');
  if(vLink){
    vLink.addEventListener('click',e=>{
      e.preventDefault();
      e.stopPropagation();
      giShowValides=!giShowValides;
      giRender();
    });
  }
  if(typeof posSyncListChrome==='function') posSyncListChrome(typeof posListIsOpen==='function'&&posListIsOpen());
}
function giInit(){
  giRender();
}
