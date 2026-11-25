/* ===== Positions : positions.json (XTB + livre Revolut 19/11, inchangé) + positions_revolut.json + positions_revolutx.json ===== */
const POS=(()=>{try{return JSON.parse(document.getElementById('data11').textContent);}catch(e){return {positions:[]};}})();
let POS_RV=(()=>{try{const el=document.getElementById('data14');return el?JSON.parse(el.textContent):null;}catch(e){return null;}})();
let POS_RX=(()=>{try{const el=document.getElementById('data13');return el?JSON.parse(el.textContent):null;}catch(e){return null;}})();
function posMergeRevolut(rv){
  const R=rv||POS_RV;
  if(!R||!Array.isArray(R.positions)||!R.positions.length) return;
  const others=(POS.positions||[]).filter(p=>p.courtier!=='revolut');
  POS.positions=R.positions.map(p=>Object.assign({},p)).concat(others);
  if(R.liquidites) POS.liquidites=R.liquidites;
  POS._rvMerged=true;
}
function posIsHeld(p){
  const st=String((p&&p.statut)||'active').toLowerCase();
  return st==='active'||st==='en_attente';
}
function posRecompute(){
  const held=(POS.positions||[]).filter(posIsHeld);
  const T=POS.totaux||(POS.totaux={});
  const prevXtb=(T.courtiers&&T.courtiers.xtb)?Object.assign({},T.courtiers.xtb):null;
  const C={};
  let te=0,tu=0,ie=0,iu=0,vk=0,ik=0;
  held.forEach(p=>{
    const c=p.courtier||'revolut';
    const e=Number(p.valeur_eur)||0, u=Number(p.valeur_usd)||0;
    const eI=p.investi_eur, uI=p.investi_usd;
    const o=C[c]||(C[c]={valeur_eur:0,valeur_usd:0,investi_eur:0,investi_usd:0,val_known:0,n:0,statut:'ok'});
    o.valeur_eur+=e;o.valeur_usd+=u;o.n++;
    if(eI!=null&&eI!==''&&Number.isFinite(Number(eI))){o.investi_eur+=Number(eI);o.val_known+=e;}
    if(uI!=null&&uI!==''&&Number.isFinite(Number(uI))) o.investi_usd+=Number(uI);
    te+=e;tu+=u;
    if(eI!=null&&eI!==''&&Number.isFinite(Number(eI))){vk+=e;ik+=Number(eI);}
    if(uI!=null&&uI!==''&&Number.isFinite(Number(uI))) iu+=Number(uI);
  });
  Object.keys(C).forEach(c=>{
    const o=C[c];
    ['valeur_eur','valeur_usd','investi_eur','investi_usd'].forEach(k=>o[k]=Math.round((o[k]+1e-12)*100)/100);
    if(o.investi_eur>0) o.perf_debut_pct=Math.round(((o.val_known/o.investi_eur-1)*100)*10+1e-9)/10;
    delete o.val_known;
  });
  if(prevXtb){
    C.xtb=Object.assign({},prevXtb,C.xtb||{});
    if(POS_RV&&!(C.xtb.compte)) {/* conserve les champs XTB du livre */}
  }
  T.somme_lignes_eur=Math.round((te+1e-12)*100)/100;
  T.somme_lignes_usd=Math.round((tu+1e-12)*100)/100;
  T.total_eur=T.somme_lignes_eur;
  T.total_usd=T.somme_lignes_usd;
  T.investi_eur=Math.round((ik+1e-12)*100)/100;
  T.investi_usd=Math.round((iu+1e-12)*100)/100;
  T.courtiers=C;
  T.perf_debut_pct=ik>0?Math.round(((vk/ik-1)*100)*10+1e-9)/10:null;
  /* Totaux officiels des captures (09 h 50) : ils priment sur la somme des lignes
     (lignes titres/métaux encore au pointage 08 h 15, CFD affichés pour leur marge). */
  const off=T.officiels||POS.totaux&&POS.totaux.officiels;
  if(off){
    if(off.liquide_usd!=null) T.liquide_usd=off.liquide_usd;
    if(off.liquide_eur!=null) T.liquide_eur=off.liquide_eur;
    if(off.patrimoine_usd!=null){ T.patrimoine_usd=off.patrimoine_usd; T.total_usd=off.patrimoine_usd; }
    if(off.patrimoine_eur!=null){ T.patrimoine_eur=off.patrimoine_eur; T.total_eur=off.patrimoine_eur; }
    if(off.entete_detail) T.entete_detail=off.entete_detail;
    if(off.tesla_plan) T.tesla_plan=off.tesla_plan;
    ['revolut','xtb','revolutx'].forEach(k=>{
      if(!off[k]) return;
      C[k]=Object.assign({},C[k]||{},off[k]);
    });
    T.courtiers=C;
    if(off.revolut&&off.revolutx&&off.xtb){
      const iu=(Number(off.revolut.investi_usd)||0)+(Number(off.revolutx.investi_usd)||0)+(Number(off.xtb.investi_usd)||0);
      const vu=(Number(off.revolut.valeur_usd)||0)+(Number(off.revolutx.valeur_usd)||0)+(Number(off.xtb.valeur_usd)||0);
      if(iu>0) T.perf_debut_pct=Math.round(((vu/iu-1)*100)*10+1e-9)/10;
      T.investi_usd=Math.round((iu+1e-12)*100)/100;
    }
  }
  POS.n_actives=(POS.positions||[]).filter(p=>p.statut==='active').length;
  POS.n_en_attente=(POS.positions||[]).filter(p=>p.statut==='en_attente').length;
  const totU=T.total_usd||0;
  if(totU>0) POS.positions.forEach(p=>{
    const v=Number(p.valeur_usd!=null?p.valeur_usd:p.valeur)||0;
    p.poids_pct=Math.round((1000*v/totU)+1e-9)/10;
  });
  const bits=[];
  if(POS_RV&&POS_RV.releve_libelle) bits.push(POS_RV.releve_libelle);
  if(POS.xtb_releve_libelle) bits.push(POS.xtb_releve_libelle);
  if(POS_RX&&POS_RX.releve_libelle) bits.push(POS_RX.releve_libelle);
  if(bits.length) POS.releve_libelle=bits.join(' · ');
}
function posApplyOverlays(){
  posMergeRevolut(POS_RV);
  posMergeRevolutX(POS_RX);
  posRecompute();
}
function posMergeRevolutX(rx){
  const R=rx||POS_RX;
  if(!R||!Array.isArray(R.positions)||!R.positions.length) return;
  const base=POS.positions||[];
  if(base.some(p=>p.courtier==='revolutx')) return;
  const extra=R.positions.map(p=>Object.assign({},p));
  if(typeof T2!=='undefined'&&T2.crypto&&T2.crypto.fiches&&T2.crypto.fiches.assets){
    extra.forEach(p=>{
      const a=(T2.crypto.fiches.assets||[]).find(x=>x.sym===p.ticker||x.tv===p.fiche_tv);
      if(a&&a.av&&a.av.score!=null){
        p.apex_score=a.av.score;p.apex_label=a.av.label||null;
        const s=Number(a.av.score);
        p.apex10=a.apex10||null; /* t320u : pas de recalcul JS */
        p.drapeau=p.apex10&&p.apex10.flag?p.apex10.flag:p.apex_label;
        p.drapeau_code=(p.apex10&&p.apex10.flag)||'none';
      }
    });
  }
  POS.positions=base.concat(extra);
  const T=POS.totaux||(POS.totaux={});
  const addEur=Number(R.totaux&&R.totaux.valeur_eur)||extra.reduce((s,p)=>s+(Number(p.valeur_eur)||0),0);
  const addUsd=Number(R.totaux&&R.totaux.valeur_usd)||extra.reduce((s,p)=>s+(Number(p.valeur_usd)||0),0);
  T.total_eur=(Number(T.total_eur)||0)+addEur;
  T.total_usd=(Number(T.total_usd)||0)+addUsd;
  T.courtiers=T.courtiers||{};
  T.courtiers.revolutx={valeur_eur:addEur,valeur_usd:addUsd,n:extra.length,statut:'ok',libelle:R.releve_libelle||'Revolut X'};
  const tot=T.total_usd||0;
  if(tot>0) POS.positions.forEach(p=>{
    const v=Number(p.valeur_usd!=null?p.valeur_usd:p.valeur)||0;
    p.poids_pct=Math.round((1000*v/tot)+1e-9)/10;
  });
  POS.n_actives=POS.positions.filter(p=>p.statut==='active').length;
}
const posSym=d=>d==='USD'?'$':d==='EUR'?'€':d==='CAD'?'C$':d;
const posAmt=(n,d)=>{
  const v=Math.round(n);
  return v.toLocaleString('fr-FR')+'\u00a0'+posSym(d);
};
const posPct=p=>{
  if(p==null||p==='') return '—';
  const s=p<0?-1:1, a=Math.abs(Number(p));
  const r=Math.round(a*10+1e-9)/10; /* 1 décimale, arrondi 0,5 vers le haut */
  const t=(s<0?'−':'+')+r.toFixed(1).replace('.',',');
  return t+'\u00a0%';
};
const posFlagCol={green:'#22c55e',orange:'#ff9a1f',red:'#ff2d2d',cyan:'#00e5ff',none:'#888'};
const posCourtNom={revolut:'Revolut',xtb:'XTB',revolutx:'Revolut X',tesla:'Tesla'};
posApplyOverlays();
function posOfTv(tv){
  if(!tv||!POS.positions) return [];
  return POS.positions.filter(p=>p.fiche_tv===tv || p.tv_note===tv);
}
function posCourtLabel(p){
  const raw=(posCourtNom[p&&p.courtier]||(p&&p.courtier)||'Revolut');
  return String(raw).toUpperCase();
}
function posActifCarre(list){
  if(!list||!list.length) return '';
  const seen=new Set(), courts=[];
  list.forEach(p=>{
    const c=posCourtLabel(p);
    if(c&&!seen.has(c)){ seen.add(c); courts.push(c); }
  });
  const court=courts.join(' · ')||'REVOLUT';
  const devises=[...new Set(list.map(p=>p.devise||'USD'))];
  let amt;
  if(devises.length===1){
    const sum=list.reduce((s,p)=>s+(Number(p.valeur)||0),0);
    amt=posAmt(sum, devises[0]);
  }else{
    amt=list.map(p=>posAmt(p.valeur,p.devise)).join(' · ');
  }
  let pnl=null, hasPnl=false;
  const withInv=list.filter(p=>p.pnl_valeur!=null&&p.investi!=null&&Number(p.investi));
  if(withInv.length===list.length&&list.length){
    const inv=withInv.reduce((s,p)=>s+Number(p.investi),0);
    const pv=withInv.reduce((s,p)=>s+Number(p.pnl_valeur),0);
    if(inv){ pnl=100*pv/inv; hasPnl=true; }
  }else if(list.every(p=>p.pnl_pct!=null&&p.pnl_pct!=='')){
    if(list.length===1){ pnl=Number(list[0].pnl_pct); hasPnl=true; }
    else{
      const w=list.reduce((s,p)=>s+(Number(p.valeur)||0),0);
      if(w){ pnl=list.reduce((s,p)=>s+Number(p.pnl_pct)*(Number(p.valeur)||0),0)/w; hasPnl=true; }
    }
  }
  const cls='pos-carre'+(hasPnl?(pnl>=0?' is-gain':' is-loss'):' is-na');
  const pct=hasPnl?posPct(pnl):'–';
  const tip=[amt,court,hasPnl?posPct(pnl):'',...list.map(p=>[p.fiche_note,p.fiche_proxy?'Ce n’est pas le titre exact détenu.':''].filter(Boolean).join(' '))].filter(Boolean).join(' · ').replace(/"/g,'&quot;');
  return `<span class="${cls}" title="${tip}"><b>${amt}</b><span class="pos-carre-c">${court}</span><span class="pos-carre-p">${pct}</span></span>`;
}
function posOrdreTip(p){
  const court=posCourtNom[p.courtier]||p.courtier||'Revolut';
  const exp=p.expiration?String(p.expiration).replace('T',' ').replace(':00+01:00','').replace('+01:00',''):'';
  return (p.fiche_note||('Ordre d’achat au marché chez '+court))+(exp?' · expiration '+exp+' (Europe/Paris)':'');
}
function posOrdreMark(list){
  const pend=(list||[]).filter(p=>p.statut==='en_attente');
  if(!pend.length) return '';
  const tip=pend.map(posOrdreTip).filter(Boolean).join(' · ').replace(/"/g,'&quot;');
  return `<span class="pos-mark pos-mark-ordre" title="${tip}">ordre</span>`;
}
function posBadgeHTML(p){
  if(p.statut==='en_attente') return posActifCarre([p])+posOrdreMark([p]);
  return posActifCarre([p]);
}
function posBadges(tv){
  const L=posOfTv(tv); if(!L.length) return '';
  const pending=L.filter(p=>p.statut==='en_attente');
  const active=L.filter(p=>p.statut!=='en_attente');
  const all=active.concat(pending);
  const parts=[];
  if(all.length) parts.push(posActifCarre(all));
  if(pending.length) parts.push(posOrdreMark(pending));
  return `<span class="pos-badges">${parts.join('')}</span>`;
}
function posOpenFiche(tab,tv){
  const go=()=>{
    const el=document.querySelector('[data-pos-tv="'+tv+'"]');
    if(!el) return;
    el.closestAll=el.closest;
    let n=el;
    while(n&&n!==document){
      if(n.tagName==='DETAILS'&&!n.open) n.open=true;
      if(n.classList&&n.classList.contains('card')&&n.classList.contains('acc')&&typeof accToggle==='function')
        accToggle(n,true,false);
      n=n.parentElement;
    }
    el.classList.add('pos-flash');
    el.scrollIntoView({behavior:'smooth',block:'center'});
    setTimeout(()=>el.classList.remove('pos-flash'),2200);
  };
  const cur=(location.hash||'').slice(1);
  if(tab && cur!==tab){
    location.hash=tab;
    setTimeout(go,350); setTimeout(go,900);
  } else go();
}
function apex10FromKnown(tv){
  /* t344u : relire une note déjà calculée (onglets), sans recalcul. */
  if(!tv||tv==='pas de note') return null;
  /* APE-24 : métaux au comptant Revolut (XAU…) = ligne « au comptant » de l'onglet Métaux. */
  const MET_ALIAS={XAU:'OANDA:XAUUSD',XAG:'OANDA:XAGUSD',XPT:'OANDA:XPTUSD',XPD:'OANDA:XPDUSD'};
  if(MET_ALIAS[String(tv).toUpperCase()]) tv=MET_ALIAS[String(tv).toUpperCase()];
  const ok=a=>a&&a.note!=null&&a.display!=='–'?a:null;
  const bars=(typeof APEX_BARS!=='undefined'&&APEX_BARS.bars)?APEX_BARS.bars:{};
  if(ok((bars[tv]||{}).apex10)) return bars[tv].apex10;
  const scan=(arr,getTv,getA)=>{
    if(!arr) return null;
    for(const x of arr){ if(getTv(x)===tv){ const r=ok(getA(x)); if(r) return r; } }
    return null;
  };
  if(typeof T2!=='undefined'){
    let r=scan((T2.energie&&T2.energie.assets)||[],a=>a.tv||a.sym,a=>a.apex10); if(r) return r;
    const F=T2.crypto&&T2.crypto.fiches;
    r=scan((F&&F.assets)||[],a=>a.tv||a.sym||a.key,a=>a.apex10); if(r) return r;
    r=scan((T2.liquidites&&T2.liquidites.fx&&T2.liquidites.fx.assets)||[],a=>a.tv||a.sym||a.pair,a=>a.apex10); if(r) return r;
  }
  if(typeof OB!=='undefined'){
    for(const s of (OB.segments||[])){
      if(s.tv===tv){ const r=ok(s.apex10_panier)||(s.apex10&&s.apex10.cap!=='moyenne'?ok(s.apex10):null); if(r) return r; }
      const r=scan(s.list||[],x=>x.tv,x=>x.apex10); if(r) return r;
    }
  }
  if(typeof MT!=='undefined'){
    for(const row of (MT.rows||[])){
      const ml=row.mlist||{};
      const r=scan([ml.head].concat(ml.items||[],ml.etc_detenus_masques||[]).filter(Boolean),it=>it.tv||it.ticker,it=>it.apex10);
      if(r) return r;
    }
  }
  return null;
}
function posIsEquity(p){
  if(!p) return false;
  if(p.type==='equity') return true;
  if(p.tab==='actions'||p.tab==='pays') return true;
  return false;
}
function posPilotRec(p){
  if(!p||typeof pilotRec!=='function') return null;
  const keys=[p.fiche_tv,p.tv_note,p.tv,p.ticker].filter(k=>k&&k!=='pas de note');
  for(const k of keys){
    const r=pilotRec(k);
    if(r&&r.total!=null) return r;
  }
  return null;
}
function posApex10Of(p){
  if(p&&p.apex10&&p.apex10.note!=null) return p.apex10;
  const keys=[p&&p.fiche_tv,p&&p.tv_note,p&&p.tv,p&&p.ticker].filter(k=>k&&k!=='pas de note');
  for(const key of keys){
    const rec=apex10FromKnown(key);
    if(rec) return rec;
  }
  if(false&&p&&p.apex_score!=null) return null; /* t320u : pas de recalcul JS */
  return null;
}
function posFlagHTML(p){
  const rec=posPilotRec(p);
  if(rec&&rec.total!=null){
    const b=(typeof pilotBand==='function')?pilotBand(rec.total):{id:rec.band||'',hex:rec.hex||'#888'};
    const code=b.id||rec.band||'none';
    if(!code||code==='none') return '–';
    return `<span class="pos-flag pos-${code}"><i style="background:${b.hex||rec.hex}"></i></span>`;
  }
  const a=posApex10Of(p);
  const code=(a&&a.flag)||p.drapeau_code;
  if(!code||code==='none') return '–';
  const col=(a&&a.hex)||posFlagCol[code]||'#888';
  return `<span class="pos-flag pos-${code}"><i style="background:${col}"></i></span>`;
}
function posNoteHTML(p){
  const rec=posPilotRec(p);
  if(rec&&rec.total!=null){
    const col=(typeof pilotHex==='function')?pilotHex(rec):(rec.hex||'#e6c27a');
    const mx=rec.total_max!=null?rec.total_max:250;
    return `<span class="apex10 apex10-pilot" style="color:${col}"><b>${rec.total}</b><small>/ ${mx}</small></span>`;
  }
  if(posIsEquity(p)) return '–';
  const a=posApex10Of(p);
  if(a&&a.note!=null){
    if(a.scale===250||a.total_max===250||a.v2){
      const col=(typeof pilotHex==='function')?pilotHex(a):(a.hex||'#e6c27a');
      return `<span class="apex10 apex10-pilot" style="color:${col}"><b>${a.total!=null?a.total:a.note}</b><small>/ 250</small></span>`;
    }
    return `<span class="apex10 apex10-pilot apex10-na" title="Note APEX −50 à 250 non disponible"><b>–</b><small>/ 250</small></span>`;
  }
  if(p.apex_score==null) return '–';
  const lab=p.apex_label?` ${p.apex_label}`:'';
  const sign=p.apex_score>0?'+':'';
  return `${sign}${Number(p.apex_score).toLocaleString('fr-FR',{minimumFractionDigits:1,maximumFractionDigits:1})}${lab}`;
}
function posIsOpen(){return document.body.classList.contains('pos-open');}
function posSetOpen(on,persist){
  document.body.classList.toggle('pos-open',!!on);
  const b=document.getElementById('posReopen');
  if(b) b.setAttribute('aria-expanded', on?'true':'false');
  const ov=document.getElementById('pos-overlay');
  if(ov) ov.hidden=!on;
  if(persist!==false){ try{ localStorage.setItem('apex-pos-open', on?'1':'0'); }catch(e){} }
}
function posInitToggle(){
  const b=document.getElementById('posReopen');
  if(b) b.hidden=true;
  const ov=document.getElementById('pos-overlay');
  if(ov && !ov._posBound){
    ov._posBound=true;
    ov.addEventListener('click',()=>{posSetListOpen(false); if(typeof giSetListOpen==='function') giSetListOpen(false);});
  }
  /* Le bouton Mes positions reste toujours visible : plus de masquage par la croix. */
  posSetOpen(true,false);
  posApplyListState();
}
const POS_LIST_KEY='apex-pos-list';
function posListIsOpen(){
  const c=document.getElementById('mesPosCard');
  return !!(c&&!c.classList.contains('pos-collapsed'));
}
function posSyncListChrome(on){
  document.body.classList.toggle('pos-list-open',!!on);
  const giOn=typeof giListIsOpen==='function'&&giListIsOpen();
  const gsOn=typeof gsListIsOpen==='function'&&gsListIsOpen();
  const irOn=typeof irListIsOpen==='function'&&irListIsOpen();
  const evtOn=typeof evtListIsOpen==='function'&&evtListIsOpen();
  document.body.classList.toggle('gi-list-open',!!giOn);
  document.body.classList.toggle('gs-list-open',!!gsOn);
  document.body.classList.toggle('ir-list-open',!!irOn);
  document.body.classList.toggle('evt-list-open',!!evtOn);
  const rail=document.getElementById('mes-pos');
  if(rail) rail.classList.toggle('is-expanded',!!on||!!giOn||!!gsOn||!!irOn||!!evtOn);
  const ov=document.getElementById('pos-overlay');
  if(ov){
    const mobile=window.matchMedia('(max-width:1099px)').matches;
    ov.hidden=!(mobile&&(on||giOn||gsOn||irOn||evtOn));
  }
}
function posApplyListState(force){
  const c=document.getElementById('mesPosCard'); if(!c) return;
  let saved=null;
  try{ saved=localStorage.getItem(POS_LIST_KEY); }catch(e){}
  const on=force!==undefined?force:(saved==='1'); /* replié par défaut */
  c.classList.toggle('pos-collapsed',!on);
  const h=c.querySelector('.pos-rail-h');
  if(h){ h.setAttribute('aria-expanded',on?'true':'false'); }
  posSyncListChrome(on);
}
function posSetListOpen(on,persist){
  const c=document.getElementById('mesPosCard'); if(!c) return;
  c.classList.toggle('pos-collapsed',!on);
  const h=c.querySelector('.pos-rail-h');
  if(h) h.setAttribute('aria-expanded',on?'true':'false');
  posSyncListChrome(on);
  if(persist!==false){ try{ localStorage.setItem(POS_LIST_KEY,on?'1':'0'); }catch(e){} }
}
function posLinePerf(p, kind){
  if(p.statut==='en_attente') return `<span class="pos-na" title="Ordre en cours : le pourcentage vaut 0 jusqu’à l’exécution">+0,0 %</span>`;
  if(kind==='debut'&&(p.type==='cfd'||p.cfd_badge)&&p.perf_debut_pct==null){
    const lab=p.a_confirmer?'à confirmer':'P/L non relu';
    return `<span class="pos-na" title="${(p.fiche_note||'P/L de cette ligne CFD non relu : cours actuel et/ou quantité manquants, non inventés.').replace(/"/g,'&quot;')}">${lab}</span>`;
  }
  if(kind==='debut'&&(p.non_liquide||p.type==='rsu')&&p.perf_debut_pct==null){
    return `<span class="pos-na" title="${(p.perf_1an_note||p.fiche_note||'Non liquide, P/L non calculé.').replace(/"/g,'&quot;')}">${p.perf_1an_libelle||'non liquide'}</span>`;
  }
  if(kind==='debut') return p.perf_debut_pct==null?'—':`<span class="${p.perf_debut_pct>=0?'up':'down'}">${posPct(p.perf_debut_pct)}</span>`;
  if(p.perf_1an_pct==null){
    const lab=p.perf_1an_libelle||'à venir';
    return `<span class="pos-na" title="${(p.perf_1an_note||'').replace(/"/g,'&quot;')}">${lab}</span>`;
  }
  const tip=(p.perf_1an_note||p.perf_1an_libelle||'').replace(/"/g,'&quot;');
  return `<span class="${p.perf_1an_pct>=0?'up':'down'}" title="${tip}">${posPct(p.perf_1an_pct)}<small> 52 sem. actif</small></span>`;
}
function posTickerCourt(p){
  if(p&&p.sous_jacent) return String(p.sous_jacent);
  if(p&&p.ticker){
    const tk=String(p.ticker);
    return tk.replace(/-CFD$/,'');
  }
  if(p&&p.ticker) return String(p.ticker);
  const tv=p&&(p.fiche_tv||p.tv_note||'');
  if(tv&&String(tv).indexOf(':')>=0) return String(tv).slice(String(tv).lastIndexOf(':')+1);
  if(tv) return String(tv);
  return (p&&p.nom)?String(p.nom):'—';
}
function posTvCopy(p){
  /* Symbole TradingView complet. CASH / PEA n'en ont pas : pas de bouton copier. */
  const tv=p&&p.fiche_tv;
  if(!tv) return '';
  const tick=String((p&&p.ticker)||'').toUpperCase();
  if(tick==='CASH'||tick==='PEA') return '';
  return String(tv);
}
function posShortName(p){
  let n=p.nom||p.ticker||'—';
  const map={
    'Enphase Energy':'Enphase','AGNC Investment':'AGNC','Annaly Capital Management':'Annaly',
    'Porsche Automobil Holding SE':'Porsche','Hermès International':'Hermès','Fanuc Corporation':'Fanuc',
    'Mercedes-Benz Group AG':'Mercedes','Global X Uranium UCITS ETF':'Uranium',
    'Invesco Preferred Shares UCITS ETF (EUR Hdg)':'Preferred Shares',
    'Etablissements Maurel et Prom':'Maurel & Prom','Booking Holdings':'Booking',
    'Caterpillar Inc.':'Caterpillar','Broadcom Inc.':'Broadcom',
    'Liquidités Revolut':'Liquidités','Xtrackers Euro High Yield Corporate Bond Dist ETF':'High Yield €',
    'Xtrackers II US Treasuries 10+ UCITS ETF 1D':'Treasuries 10+'
  };
  if(map[n]) return map[n];
  n=n.replace(/\s+(janvier|février|mars|avril|mai|juin|juillet|août|septembre|octobre|novembre|décembre)\s+(\d{4})/i,' $2');
  n=n.replace(/^US Treasury\s+/,'T ');
  n=n.replace(/^Dow Chemical\s+/,'Dow ');
  n=n.replace(/\s+UCITS ETF(?:\s*\([^)]+\))?$/i,'');
  n=n.replace(/\s+(Corporation|International|Group AG|Holding SE)$/i,'');
  return n;
}
function posApexChip(p){
  const rec=posPilotRec(p);
  if(rec&&rec.total!=null){
    const col=(typeof pilotHex==='function')?pilotHex(rec):(rec.hex||'#e6c27a');
    const mx=rec.total_max!=null?rec.total_max:250;
    return `<span class="pos-chip apex10 apex10-pilot" style="color:${col};border-color:${col}" title="Note APEX ${rec.total}/${mx}">${rec.total}<small>/${mx}</small></span>`;
  }
  if(posIsEquity(p)) return '';
  const a=posApex10Of(p);
  if(a&&a.note!=null){
    const mx=(a.scale===250||a.total_max===250)?250:100;
    const col=(mx===250&&typeof pilotHex==='function')?pilotHex({total:a.total!=null?a.total:a.note, hex:a.hex, scale:250, total_max:250}):((typeof apex10Col==='function')?apex10Col(a):(a.hex||'#e6c27a'));
    const col2=a.hex||col;
    return `<span class="pos-chip apex10${mx===250?' apex10-pilot':''}" style="color:${col2};border-color:${col2}" title="Note APEX ${a.display}/${mx}">${a.display}<small>/${mx}</small></span>`;
  }
  if(p.apex_score==null||p.apex_score==='') return '';
  const col=(typeof avCol==='function')?avCol(p.apex_score):(posFlagCol[p.drapeau_code]||'#e6c27a');
  const lab=p.apex_label||'';
  const sg=p.apex_score>0?'+':'';
  const txt=sg+Number(p.apex_score).toLocaleString('fr-FR',{minimumFractionDigits:1,maximumFractionDigits:1});
  const tip=[txt,lab,p.drapeau].filter(Boolean).join(' \u00b7 ');
  return `<span class="pos-chip" style="color:${col};border-color:${col}" title="${tip.replace(/"/g,'&quot;')}">${txt}</span>`;
}

function posAmtDec(n,d){
  if(n==null||n==='') return '—';
  const v=Number(n);
  if(!Number.isFinite(v)) return '—';
  return v.toLocaleString('fr-FR',{minimumFractionDigits:2,maximumFractionDigits:2})+' '+posSym(d);
}
function posMoneyUsdEur(usd,eur){
  const a=(usd==null||usd==='')?'':posAmtDec(usd,'USD');
  const b=(eur==null||eur==='')?'':posAmtDec(eur,'EUR');
  if(!a||a==='—') return b||'—';
  if(!b||b==='—') return a;
  return a+' / '+b;
}
function posCfdAlertHTML(){
  const a=POS.cfd_alerte||(POS_RV&&POS_RV.cfd_alerte);
  if(!a||a.afficher_encadre!==true) return '';
  const tip=(a.note||'').replace(/"/g,'&quot;');
  return `<div class="pos-cfd-alert" role="alert" title="${tip}">${a.libelle||'CFD Revolut'}</div>`;
}
function posFraisCfdHTML(){
  const f=POS.frais_cfd||(POS_RV&&POS_RV.frais_cfd);
  if(!f||(f.dernier_usd==null&&!(f.jours&&f.jours.length))) return '';
  const last=f.dernier||((f.jours&&f.jours.length)?f.jours[f.jours.length-1]:null);
  const d=last&&last.date?String(last.date).slice(8,10)+'/'+String(last.date).slice(5,7):'';
  const jour=posMoneyUsdEur(f.dernier_usd,f.dernier_eur);
  const mois=posMoneyUsdEur(f.projection_usd,f.projection_eur);
  const obj=f.objectif_eur_mois!=null?f.objectif_eur_mois:20;
  const proj=Number(f.projection_eur);
  const ratio=obj?(proj/obj):0;
  const pct=Math.max(0,Math.min(100,Math.round(ratio*100)));
  const over=!!f.depasse_objectif||(proj>obj);
  const hyp=((f.projection&&f.projection.hypothese)||'').replace(/"/g,'&quot;');
  const fact=((f.facturation&&f.facturation.taux_par_instrument_note)||'').replace(/"/g,'&quot;');
  const jourTip=((last&&(last.libelle||''))||'Frais overnight CFD')+' du '+(d||'jour relu')+(last&&last.heure?(' à '+last.heure):'')+' (Europe/Paris).';
  return `<div class="pos-frais-cfd${over?' is-over':''}" title="${hyp||jourTip}">
    <div class="pos-frais-h">FRAIS CFD</div>
    <div class="pos-frais-row"><span>OVN ${d||'jour'}</span><b>${jour}</b></div>
    <div class="pos-frais-row" title="${hyp}"><span>Projection / mois</span><b>${mois}</b></div>
    <div class="pos-frais-obj">Objectif &lt; ${String(obj).replace('.',',')}\u00a0€ / mois</div>
    <div class="pos-frais-bar" role="progressbar" aria-valuemin="0" aria-valuemax="100" aria-valuenow="${pct}" aria-label="Projection par rapport à l’objectif"><i style="width:${pct}%"></i></div>
    <div class="pos-frais-note">${over?'Au-dessus de l’objectif. ':''}Projection = dernier OVN observé × ~${f.projection_jours||30} jours calendaires (facturé chaque nuit ; un triple le vendredi, s’il s’applique, couvre le week-end et aboutit au même ordre de grandeur). ${fact||'Aucun OVN théorique par position n’est inventé : les taux exacts ne sont pas publiés hors de l’app Revolut.'}</div>
  </div>`;
}
function renderMesPositions(){
  const host=document.getElementById('mes-pos'); if(!host) return;
  const L=POS.positions||[];
  const act=L.filter(p=>p.statut==='active'||p.statut==='en_attente');
  const pend=[];
  const T=POS.totaux||{};
  const C=T.courtiers||{};
  const rev=C.revolut||{};
  const xtb=C.xtb||{};
  const rxC=C.revolutx||{};
  const fx=POS.fx||{};
  const row=p=>{
    const mon=(p.valeur==null||p.valeur==='')
      ? (p.a_confirmer?'à confirmer':'—')
      : posAmt(p.valeur,p.devise);
    const court=posCourtNom[p.courtier]||p.courtier||'';
    const cx=p.courtier==='revolutx'?'RX':p.courtier==='xtb'?'X':p.courtier==='tesla'?'T':'R';
    const abbr=posTickerCourt(p);
    const nom=p.nom||abbr;
    const tipNom=String(nom).replace(/"/g,'&quot;');
    const go=(p.tab&&p.fiche_tv)
      ? `<button type="button" class="pos-link" data-tab="${p.tab}" data-tv="${String(p.fiche_tv).replace(/"/g,'&quot;')}" title="${tipNom}">${abbr.replace(/</g,'')}</button>`
      : `<span class="pos-nm" title="${tipNom}">${abbr.replace(/</g,'')}</span>`;
    const tvCopy=posTvCopy(p);
    const cp=tvCopy?((typeof ophirCopyBtn==='function')?ophirCopyBtn(tvCopy):`<button type="button" class="cp" data-c="${String(tvCopy).replace(/"/g,'&quot;')}" aria-label="Copier ${String(tvCopy).replace(/"/g,'&quot;')}" title="Copier ${String(tvCopy).replace(/"/g,'&quot;')}">⎘</button>`):'';
    const poids=p.poids_pct==null?'—':posPct(p.poids_pct).replace('+','');
    const sell=p.vente_en_attente?`<span class="pos-mark pos-mark-sell" title="${(p.vente_en_attente_note||'Vente en attente').replace(/"/g,'&quot;')}">vente</span>`:'';
    const ordre=''; /* t478u : plus de badge ORDRE dans Mes positions ; les en_attente restent dans la liste */
    const stale=p.non_reverifie?`<span class="pos-mark pos-mark-stale" title="Non revérifié le ${String(p.non_reverifie).replace(/"/g,'&quot;')}"></span>`:'';
    const cfd=p.cfd_badge?`<span class="pos-mark pos-mark-cfd" title="${(p.fiche_note||p.cfd_badge).replace(/"/g,'&quot;')}">${String(p.cfd_badge).replace(/</g,'')}</span>`:'';
    const rsu=p.rsu_badge?`<span class="pos-mark pos-mark-rsu" title="${(p.fiche_note||'Tesla RSU, non liquide').replace(/"/g,'&quot;')}">${String(p.rsu_badge).replace(/</g,'')}</span>`:'';
    const tip=[p.nom,p.ticker&&p.ticker!==p.nom?p.ticker:'',court,p.vente_en_attente_note||'',p.non_reverifie_note||'',p.fiche_note||''].filter(Boolean).join(' \u00b7 ');
    const posTv=p.fiche_tv||p.tv_note||p.ticker||'';
    return `<article class="pos-row pos-row-c ${p.statut==='en_attente'?'is-pend':''}${p.vente_en_attente?' is-sell':''}${p.fiche_tv?' has-fiche':''}"${posTv?` data-pos-tv="${String(posTv).replace(/"/g,'&quot;')}"`:''} title="${tip.replace(/"/g,'&quot;')}">
      <span class="pos-cx pos-cx-${cx.toLowerCase()}" title="${court}">${cx}</span>
      <span class="pos-id">${go}${cp}${cfd}${rsu}${sell}${ordre}${stale}</span>
      <b class="pos-m">${mon}</b>
      <span class="pos-p">${poids}</span>
      <span class="pos-d">${posLinePerf(p,'debut')}</span>
      ${posApexChip(p)||'<span class="pos-chip is-empty"></span>'}
    </article>`;
  };
  const totDeb=T.perf_debut_pct==null?'—':`<span class="${T.perf_debut_pct>=0?'up':'down'}">${posPct(T.perf_debut_pct)}</span>`;
  const xtbPending=xtb.statut==='a_integrer'||!xtb.n;
  const tesla=T.tesla_plan||{};
  const fxNote=(()=>{
    const bits=[];
    if(fx.taux) bits.push('EUR/USD '+String(fx.taux).replace('.',','));
    if(fx.cadusd) bits.push('CAD/USD '+String(fx.cadusd).replace('.',','));
    if(fx.eurcad) bits.push('EUR/CAD '+String(fx.eurcad).replace('.',','));
    if(!bits.length) return '';
    return 'Conversion '+bits.join(', ')+' au '+fx.date+' ('+(fx.source_court||fx.source||'Yahoo')+', Europe/Paris).';
  })();
  const headTip=[T.entete_detail||((POS.totaux&&POS.totaux.officiels&&POS.totaux.officiels.entete_detail)||''),POS.desc||('Relevé '+(POS.releve_libelle||'')),fxNote,xtbPending?'XTB n\u2019est pas encore intégré.':'',T.perf_1an_note||'',tesla.note||''].filter(Boolean).join(' ');
  const revTip=(()=>{
    const bits=[];
    if(rev.compte_courtage_usd!=null) bits.push('Courtage '+posAmt(rev.compte_courtage_usd,'USD')+' ('+posPct(rev.compte_courtage_pct)+').');
    if(rev.matieres_usd!=null) bits.push('Métaux '+posAmt(rev.matieres_usd,'USD')+' ('+posPct(rev.matieres_pct)+').');
    const expo=rev.cfd_exposition_usd!=null?rev.cfd_exposition_usd:rev.cfd_usd;
    if(expo!=null){
      let s='Exposition CFD '+posAmt(expo,'USD');
      if(rev.cfd_compte_usd!=null){
        s+=' — capital du compte '+posAmt(rev.cfd_compte_usd,'USD');
        if(rev.cfd_pct!=null) s+=' ('+posPct(rev.cfd_pct)+')';
      }
      bits.push(s+'.');
    }
    bits.push("L'exposition CFD est incluse dans le total Revolut (pas la marge).");
    return bits.join(' ');
  })();
  const html=`<div class="card no-group" id="mesPosCard">
    <div class="pos-rail-h" role="button" tabindex="0" aria-expanded="false" aria-controls="posBody" title="${headTip.replace(/"/g,'&quot;')}">
      <span class="pos-chev" aria-hidden="true">▸</span>
      <h2>Mes positions</h2>
      <span class="pos-head-tot">${posAmt(T.total_usd||0,'USD')} <small>${totDeb}</small></span>
    </div>
    <div class="pos-body" id="posBody">
      <div class="pos-total">
        <div class="pos-total-v" title="${((T.entete_detail||((POS.totaux&&POS.totaux.officiels&&POS.totaux.officiels.entete_detail)||'Total en dollars de toutes les positions, CFD en exposition et Tesla RSU compris, sans double compte.'))+' '+headTip).replace(/"/g,'&quot;')}">${posAmt(T.total_usd||0,'USD')} <small>${totDeb}</small></div>
      </div>
      ${posCfdAlertHTML()}
      <div class="pos-list">${act.map(row).join('')||'<div class="note">—</div>'}</div>
    </div>
  </div>`;
  const prev=document.getElementById('mesPosCard');
  if(prev) prev.outerHTML=html;
  else host.insertAdjacentHTML('afterbegin', html);
  const card=document.getElementById('mesPosCard');
  if(!card) return;
  card.querySelectorAll('.pos-link').forEach(b=>b.addEventListener('click',()=>{
    if(window.matchMedia('(max-width:1099px)').matches) posSetListOpen(false);
    posOpenFiche(b.dataset.tab,b.dataset.tv);
  }));
  const head=card.querySelector('.pos-rail-h');
  if(head){
    const tog=e=>{
      e.preventDefault();
      posSetListOpen(!posListIsOpen());
    };
    head.addEventListener('click',tog);
    head.addEventListener('keydown',e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();tog(e);}});
  }
  posApplyListState();
  if(typeof giRender==='function') giRender();
}
/* recharge éventuelle depuis positions.json (mise à jour sans reconstruire index.html) */
function posInit(){
  const apply=(base,rv,rx)=>{
    if(base&&base.positions){Object.keys(base).forEach(k=>{if(k!=='_rvMerged'&&k!=='_rxMerged') POS[k]=base[k];});}
    if(rv&&rv.positions) POS_RV=rv;
    if(rx&&rx.positions) POS_RX=rx;
    posApplyOverlays();
    renderMesPositions(); posInitToggle();
    if(typeof renderAccueil==='function'){
      const el=document.getElementById('paccueil')||document.getElementById('accueil');
      if(el&&document.body.classList.contains('home-on')) renderAccueil(el);
    }
  };
  renderMesPositions();
  posInitToggle();
  try{
    Promise.all([
      fetch('positions.json',{cache:'no-cache'}).then(r=>r.ok?r.json():null).catch(()=>null),
      fetch('positions_revolut.json',{cache:'no-cache'}).then(r=>r.ok?r.json():null).catch(()=>null),
      fetch('positions_revolutx.json',{cache:'no-cache'}).then(r=>r.ok?r.json():null).catch(()=>null)
    ]).then(([base,rv,rx])=>{if((base&&base.positions)||(rv&&rv.positions)||(rx&&rx.positions)) apply(base,rv,rx);});
  }catch(e){}
}
