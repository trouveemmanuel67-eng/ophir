/* ===== MEILLEURES ENTRÉES : actifs APEX ≥ 7,5/10 absents du portefeuille ===== */
const GI_SEUIL=7.5;
const GI_LIST_KEY='apex-gi-list';

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
function giMontant(note){
  const lignes=(typeof TT!=='undefined'&&TT&&Array.isArray(TT.lignes))?TT.lignes:[];
  const n=Number(note);
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
  if(!rec||!rec.tv||rec.note==null||Number(rec.note)<GI_SEUIL) return;
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
      .filter(it=>it&&it.tv&&it.note!=null&&Number(it.note)>=GI_SEUIL&&!giIsHeld(it,held))
      .map(it=>Object.assign({},it,{montant:it.montant!=null?it.montant:giMontant(it.note)}))
      .sort((a,b)=> (b.note-a.note) || ((b.av||0)-(a.av||0)) || String(a.tv).localeCompare(String(b.tv)));
  }catch(e){ return null; }
}
function giCollect(){
  const pre=giPrecomputed();
  if(pre) return pre;
  const out=new Map();
  const bars=(typeof APEX_BARS!=='undefined'&&APEX_BARS&&APEX_BARS.bars)?APEX_BARS.bars:{};
  const take=(tv, nom, section, rec, av, tab, yahoo, ticker)=>{
    if(!tv||!rec||rec.note==null) return;
    const score=(av&&typeof av==='object')?av.score:av;
    giPush(out,{
      tv, nom:nom||tv, section:section||'', note:Number(rec.note),
      display:rec.display||String(rec.note).replace('.',','), hex:rec.hex,
      flag:rec.flag, cap:rec.cap, av:score==null?null:Number(score),
      tab:tab||'', yahoo:yahoo||'', ticker:ticker||''
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
    PAYS.countries.forEach(C=>{
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
  assets.forEach(a=>{
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
    .map(it=>Object.assign(it,{montant:giMontant(it.note)}))
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
function giDispoTxt(tv){
  const d=typeof dispoOf==='function'?dispoOf(tv):null;
  if(!d) return {lab:'Dispo à vérifier', cls:'gi-broker is-na'};
  const r=d.revolut, x=d.xtb;
  if(r===true&&x===true) return {lab:'Revolut · XTB', cls:'gi-broker is-both'};
  if(r===true) return {lab:'Revolut', cls:'gi-broker is-rev'};
  if(x===true) return {lab:'XTB', cls:'gi-broker is-xtb'};
  if(r===false&&x===false) return {lab:'Ni Revolut ni XTB', cls:'gi-broker is-none'};
  return {lab:'Dispo à vérifier', cls:'gi-broker is-na'};
}
function giRender(){
  const host=document.getElementById('mes-pos');
  if(!host) return;
  const list=giCollect();
  const n=list.length;
  const rows=list.map(it=>{
    const col=(typeof ttColor==='function')?ttColor(it.note):(it.hex||'#e6c27a');
    const note=it.display||String(it.note).replace('.',',');
    const amt=(typeof ttMontantTxt==='function')?ttMontantTxt(it.montant, (typeof TT!=='undefined'&&TT&&TT.unite)||'$'):(it.montant==null?'—':it.montant+' $');
    const d=giDispoTxt(it.tv);
    const go=it.tv
      ? `<button type="button" class="gi-link" data-tab="${(it.tab||'').replace(/"/g,'')}" data-tv="${String(it.tv).replace(/"/g,'&quot;')}">${(it.nom||it.tv).replace(/</g,'')}</button>`
      : `<span class="pos-nm">${(it.nom||'').replace(/</g,'')}</span>`;
    const tip=[it.nom,it.tv,it.section,d.lab].filter(Boolean).join(' · ');
    const tick=it.tv?`<span class="gi-tick">${String(it.tv).replace(/</g,'')}</span>`:'';
    const sec=it.section?`<span class="gi-sec">${String(it.section).replace(/</g,'')}</span>`:'';
    return `<article class="gi-row${it.tv?' has-fiche':''}" title="${tip.replace(/"/g,'&quot;')}">
      <div class="gi-id">${go}</div>
      <span class="gi-note" style="color:${col}"><b>${note}</b><small>/10</small></span>
      <span class="gi-amt">${amt}</span>
      <div class="gi-meta">${tick}${sec}</div>
      <span class="${d.cls}">${d.lab}</span>
    </article>`;
  }).join('');
  const html=`<div class="card no-group" id="goodInvestCard">
    <div class="pos-rail-h" role="button" tabindex="0" aria-expanded="false" aria-controls="giBody">
      <span class="pos-chev" aria-hidden="true">▸</span>
      <h2>Meilleures entrées</h2>
      <span class="pos-head-tot">${n}<small>titre${n>1?'s':''}</small></span>
    </div>
    <div class="pos-body gi-body" id="giBody">
      <div class="gi-list">${rows||'<div class="gi-empty">Aucun titre à 7,5/10 ou plus hors portefeuille.</div>'}</div>
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
  if(typeof posSyncListChrome==='function') posSyncListChrome(typeof posListIsOpen==='function'&&posListIsOpen());
}
function giInit(){
  giRender();
}
