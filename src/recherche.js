/* ===== Recherche d'actifs (t449u, t458u) : début de mot du nom ou début du ticker ===== */
function apxFold(s){
  return String(s||'').normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase().replace(/[^a-z0-9]+/g,' ').trim();
}
function apxEsc(s){
  return String(s||'').replace(/&/g,'&amp;').replace(/"/g,'&quot;').replace(/</g,'&lt;');
}
function apxTvSel(tv){
  const s=String(tv||'');
  if(window.CSS&&typeof CSS.escape==='function') return CSS.escape(s);
  return s.replace(/\\/g,'\\\\').replace(/"/g,'\\"');
}
function apxTickOf(tv, ticker){
  if(ticker) return String(ticker);
  const t=String(tv||'');
  const i=t.lastIndexOf(':');
  return i>=0?t.slice(i+1):t;
}
function apxPushItem(map, it){
  if(!it||(!it.tv&&!it.ticker&&!it.nom)) return;
  const tv=it.tv||it.ticker||'';
  const key=String(tv||it.nom).toUpperCase();
  const prev=map.get(key);
  if(prev){
    if(!prev.nom&&it.nom) prev.nom=it.nom;
    if(!prev.ticker&&it.ticker) prev.ticker=it.ticker;
    if(!prev.tab&&it.tab) prev.tab=it.tab;
    if(it.held) prev.held=true;
    return;
  }
  map.set(key,{
    tv:tv||'',
    ticker:apxTickOf(tv, it.ticker),
    nom:it.nom||it.ticker||tv||'',
    tab:it.tab||'',
    section:it.section||'',
    held:!!it.held,
    posOnly:!!it.posOnly
  });
}
function apxBuildIndex(){
  const map=new Map();
  const add=(it)=>apxPushItem(map,it);
  if(typeof PILOT!=='undefined'&&PILOT&&PILOT.by_tv){
    Object.keys(PILOT.by_tv).forEach(tv=>{
      const r=PILOT.by_tv[tv];
      if(!r) return;
      add({tv:r.tv||tv, ticker:r.ticker, nom:r.nom, tab:'actions', section:r.kind==='etf'?'ETF':(r.kind==='panier'?'Panier':'Actions')});
    });
  }
  if(typeof PAYS!=='undefined'&&PAYS){
    (PAYS.countries||PAYS.pays||[]).filter(c=>typeof paysEstDansUnivers!=='function'||paysEstDansUnivers(c)).forEach(c=>{
      const rows=c.rows||[];
      rows.forEach(sec=>{
        const head=sec.head||sec.etf||null;
        if(head&&(head.tv||sec.tv)) add({tv:head.tv||sec.tv, ticker:head.ticker||sec.sym, nom:head.name||head.nom||sec.etf||sec.nom, tab:'actions', section:c.nom||'Actions'});
        (sec.rows||sec.list||sec.actions||[]).forEach(r=>{
          add({tv:r.tv, ticker:r.ticker, nom:r.name||r.nom, tab:'actions', section:(c.nom?c.nom+' · ':'')+(sec.nom||'Actions')});
        });
      });
      if(c.head&&c.head.tv) add({tv:c.head.tv, ticker:c.head.ticker, nom:c.head.name||c.head.nom||c.etf, tab:'actions', section:c.nom||'Actions'});
    });
  }
  if(typeof SEC!=='undefined'&&SEC){
    (SEC.sectors||SEC.secteurs||[]).forEach(s=>{
      if(s.tv||s.etf) add({tv:s.tv, ticker:s.tick||s.sym, nom:s.etf||s.nom, tab:'actions', section:'Secteur'});
      (s.list||s.actions||s.rows||[]).forEach(r=>{
        add({tv:r.tv, ticker:r.ticker, nom:r.name||r.nom, tab:'actions', section:s.nom||'Actions'});
      });
    });
  }
  if(typeof T2!=='undefined'&&T2){
    ((T2.energie&&T2.energie.assets)||[]).forEach(a=>{
      add({tv:a.tv||a.sym, ticker:a.sym, nom:a.nom, tab:'energie', section:'Énergie'});
    });
    const cx=T2.crypto&&T2.crypto.fiches;
    const cxAssets=(cx&&cx.assets)||[];
    cxAssets.forEach(a=>{
      add({tv:a.tv||a.sym||a.key, ticker:a.sym, nom:a.nom, tab:'crypto', section:'Crypto'});
    });
    const fx=T2.liquidites&&T2.liquidites.fx;
    ((fx&&(fx.assets||fx.pairs))||[]).forEach(a=>{
      add({tv:a.tv||a.sym||a.pair, ticker:a.sym, nom:a.nom||a.pair, tab:'liquidites', section:'Liquidités'});
    });
  }
  if(typeof OB!=='undefined'&&OB){
    (OB.segments||[]).forEach(s=>{
      if(s.tv) add({tv:s.tv, ticker:s.sym, nom:s.nom||s.pname, tab:'obligations', section:'Obligations'});
      (s.list||[]).forEach(r=>{
        add({tv:r.tv, ticker:r.ticker||r.sym, nom:r.name||r.nom, tab:'obligations', section:s.nom||'Obligations'});
      });
    });
  }
  if(typeof MT!=='undefined'&&MT){
    (MT.rows||[]).forEach(row=>{
      const ml=row.mlist||{};
      const items=[ml.head].concat(ml.items||[]).filter(Boolean);
      items.forEach(it=>{
        add({tv:it.tv||it.ticker, ticker:it.ticker||it.sym, nom:it.name||it.nom, tab:'metaux', section:row.nom||'Métaux'});
      });
    });
  }
  if(typeof ETF_REF!=='undefined'&&ETF_REF){
    Object.keys(ETF_REF).forEach(id=>{
      if(id.charAt(0)==='_') return;
      const r=ETF_REF[id];
      if(r&&r.tv) add({tv:r.tv, ticker:apxTickOf(r.tv), nom:r.nom||r.tv, tab:'accueil', section:'ETF de référence'});
    });
  }
  if(typeof POS!=='undefined'&&POS&&Array.isArray(POS.positions)){
    POS.positions.forEach(p=>{
      const tab=p.tab||((typeof homeTabOf==='function')?homeTabOf(p):'')||'';
      const tv=p.fiche_tv||p.tv_note||p.tv||p.ticker||'';
      add({tv, ticker:p.ticker, nom:p.nom, tab:tab||'', section:'Mes positions', held:true, posOnly:!p.fiche_tv&&!tab});
    });
  }
  return [...map.values()];
}
let _apxIndex=null;
function apxIndex(){
  if(!_apxIndex) _apxIndex=apxBuildIndex();
  return _apxIndex;
}
function apxIndexRefresh(){ _apxIndex=apxBuildIndex(); return _apxIndex; }

function apxTickerKeys(it){
  /* Symboles comparés : ticker brut, symbole après le préfixe TV, et racine avant .PA / .DE. */
  const out=[];
  const rawTv=String(it.tv||'');
  const rawTick=String(it.ticker||'');
  const push=s=>{ if(s) out.push(s); };
  push(rawTick);
  push(rawTv);
  if(rawTv.indexOf(':')>=0) push(rawTv.slice(rawTv.lastIndexOf(':')+1));
  if(rawTick.indexOf('.')>=0) push(rawTick.split('.')[0]);
  return out;
}
function apxScore(it, q, qf){
  /* t458u : uniquement début de ticker (avec ou sans préfixe TV) ou début d'un mot du nom.
     Pas de sous-chaîne au milieu d'un mot. Le ticker exact sort en premier. */
  if(!qf) return 0;
  const nom=apxFold(it.nom);
  const rawQ=String(q||'').toLowerCase().trim();
  const keys=apxTickerKeys(it);
  const folded=keys.map(apxFold);
  const raws=keys.map(s=>String(s||'').toLowerCase());
  if(folded.some(k=>k===qf)||raws.some(k=>k===rawQ)) return 100;
  if(folded.some(k=>k.startsWith(qf))||raws.some(k=>k.startsWith(rawQ))) return 86;
  if(nom===qf) return 84;
  if(nom.startsWith(qf)) return 76;
  if(nom.split(' ').some(w=>w&&w.startsWith(qf))) return 68;
  return 0;
}
function apxSearch(q, limit){
  const raw=String(q||'').trim();
  const qf=apxFold(raw);
  if(!qf) return [];
  const n=limit==null?8:limit;
  return apxIndex().map(it=>{
    const s=apxScore(it, raw, qf);
    return s>0?Object.assign({score:s},it):null;
  }).filter(Boolean).sort((a,b)=> (b.score-a.score) || String(a.nom).localeCompare(String(b.nom),'fr')).slice(0,n);
}

function apxSearchGo(it){
  if(!it) return;
  apxSearchSetOpen(false);
  const q=document.getElementById('apx-s-q');
  if(q) q.blur();
  const tv=it.tv;
  const flash=el=>{
    if(!el) return false;
    el.classList.add('pos-flash');
    try{ el.scrollIntoView({behavior:'smooth',block:'center'}); }catch(e){ el.scrollIntoView(); }
    setTimeout(()=>el.classList.remove('pos-flash'),2200);
    return true;
  };
  const findFiche=()=>{
    if(!tv) return null;
    const sel=apxTvSel(tv);
    return document.querySelector('#tabs [data-pos-tv="'+sel+'"]')
      || document.querySelector('[data-pos-tv="'+sel+'"]');
  };
  if(it.posOnly||(!it.tab&&it.held)){
    if(typeof posSetListOpen==='function') posSetListOpen(true);
    setTimeout(()=>{
      const el=document.querySelector('#mes-pos [data-pos-tv="'+apxTvSel(tv)+'"]');
      flash(el);
    },80);
    return;
  }
  if(typeof posOpenFiche==='function'&&it.tab&&tv){
    posOpenFiche(it.tab, tv);
    return;
  }
  if(it.tab){
    if((location.hash||'').slice(1)!==it.tab) location.hash=it.tab;
    setTimeout(()=>flash(findFiche()),350);
    setTimeout(()=>flash(findFiche()),900);
  }
}

function apxSearchRender(q){
  const box=document.getElementById('apx-s-sug');
  if(!box) return;
  const raw=String(q||'').trim();
  if(!raw){ box.hidden=true; box.innerHTML=''; return; }
  const hits=apxSearch(raw, 8);
  if(!hits.length){
    box.innerHTML='<li class="apx-s-empty" role="option" aria-disabled="true">Pas référencé sur APEX</li>';
    box.hidden=false;
    return;
  }
  box.innerHTML=hits.map((it,i)=>{
    const sub=[it.tv||it.ticker, it.section].filter(Boolean).join(' · ');
    return `<li role="option" class="apx-s-hit" data-i="${i}" tabindex="-1"><span class="apx-s-nom">${apxEsc(it.nom)}</span><span class="apx-s-sub">${apxEsc(sub)}</span></li>`;
  }).join('');
  box.hidden=false;
  box._hits=hits;
  box._active=-1;
}

function apxSearchMove(dir){
  const box=document.getElementById('apx-s-sug');
  if(!box||box.hidden) return;
  const items=[...box.querySelectorAll('.apx-s-hit')];
  if(!items.length) return;
  let i=box._active==null?-1:box._active;
  i=(i+dir+items.length)%items.length;
  box._active=i;
  items.forEach((el,k)=>el.classList.toggle('is-on',k===i));
  items[i].scrollIntoView({block:'nearest'});
}

function apxSearchChoose(){
  const box=document.getElementById('apx-s-sug');
  if(!box||box.hidden||!box._hits) return;
  const i=box._active>=0?box._active:0;
  const it=box._hits[i];
  if(it) apxSearchGo(it);
}

function apxSearchSetOpen(on){
  const root=document.getElementById('apex-search');
  if(!root) return;
  root.classList.toggle('is-open', !!on);
  const q=document.getElementById('apx-s-q');
  const tog=root.querySelector('.apx-s-tog');
  if(tog) tog.setAttribute('aria-expanded', on?'true':'false');
  if(on&&q){ q.focus(); q.select(); }
  if(!on){
    const box=document.getElementById('apx-s-sug');
    if(box){ box.hidden=true; }
  }
}

function apxSearchInit(){
  const host=document.getElementById('hh-tools');
  if(!host||document.getElementById('apex-search')) return;
  const root=document.createElement('div');
  root.id='apex-search';
  root.className='apx-s';
  root.innerHTML=`<button type="button" class="apx-s-tog" aria-label="Rechercher un actif" title="Rechercher un actif" aria-expanded="false" aria-controls="apx-s-q">
    <svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true"><circle cx="11" cy="11" r="7" fill="none" stroke="currentColor" stroke-width="2"/><path d="M16.5 16.5L21 21" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>
  </button>
  <div class="apx-s-box">
    <input id="apx-s-q" type="search" autocomplete="off" spellcheck="false" placeholder="Nom ou ticker…" aria-label="Rechercher un actif" aria-controls="apx-s-sug">
    <ul id="apx-s-sug" hidden role="listbox"></ul>
  </div>`;
  host.insertBefore(root, host.firstChild);
  const q=document.getElementById('apx-s-q');
  const tog=root.querySelector('.apx-s-tog');
  q.addEventListener('input',()=>apxSearchRender(q.value));
  q.addEventListener('keydown',e=>{
    if(e.key==='ArrowDown'){ e.preventDefault(); apxSearchMove(1); }
    else if(e.key==='ArrowUp'){ e.preventDefault(); apxSearchMove(-1); }
    else if(e.key==='Enter'){ e.preventDefault(); apxSearchChoose(); }
    else if(e.key==='Escape'){ e.preventDefault(); apxSearchSetOpen(false); q.blur(); }
  });
  q.addEventListener('focus',()=>{ apxSearchSetOpen(true); if(q.value) apxSearchRender(q.value); });
  tog.addEventListener('click',e=>{
    e.preventDefault();
    e.stopPropagation();
    const open=!root.classList.contains('is-open');
    apxSearchSetOpen(open);
  });
  document.getElementById('apx-s-sug').addEventListener('mousedown',e=>{
    const li=e.target.closest('.apx-s-hit');
    if(!li) return;
    e.preventDefault();
    const i=Number(li.dataset.i);
    const it=(document.getElementById('apx-s-sug')._hits||[])[i];
    if(it) apxSearchGo(it);
  });
  document.addEventListener('click',e=>{
    if(!root.contains(e.target)) apxSearchSetOpen(false);
  });
  apxIndexRefresh();
}
