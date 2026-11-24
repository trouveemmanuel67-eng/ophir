/* ===== Secteurs : ETF principal + top 10 actions (sélection quantitative APEX) + bouton copier le symbole TradingView ===== */
const FOND=JSON.parse(document.getElementById('data6').textContent);
const APEX_BARS=(function(){
  const el=document.getElementById('data16');
  if(!el) return {bars:{}};
  try{return JSON.parse(el.textContent)||{bars:{}};}catch(e){return {bars:{}};}
})();
function apex250Rec(a){
  if(!a||a.note==null||a.display==='–') return null;
  const tot=a.total!=null?a.total:a.note;
  return {total:tot, total_max:a.total_max!=null?a.total_max:250, total_min:a.total_min!=null?a.total_min:-50, ligne:a.ligne||((a.decomp&&a.decomp.texte)||''), hex:a.hex, band:a.band};
}
function listApexBar(r){
  const a250=r&&r.apex10&&(r.apex10.scale===250||r.apex10.total_max===250||r.forceApex250);
  if(a250||(r&&r.forceApex250)){
    const rec=apex250Rec(r.apex10);
    if(rec&&typeof dualBarPilot==='function') return `<div class="fl-apex fl-apex-pilot">${dualBarPilot(rec, true)}</div>`;
  }
  if(r&&r.forceApex100){
    return `<div class="fl-apex fl-apex-100">${(typeof dualBarApex100==='function')?dualBarApex100(r.apex10,r.sent,r.av,true):''}</div>`;
  }
  const prec=(typeof pilotRec==='function')?pilotRec(r&&r.tv):null;
  if(prec&&prec.ok!==false&&prec.total!=null){
    return `<div class="fl-apex fl-apex-pilot">${dualBarPilot(prec, true)}</div>`;
  }
  if((typeof isApexV2Tv==='function'&&isApexV2Tv(r&&r.tv))||(r&&r.forceV2)){
    return `<div class="fl-apex fl-apex-pilot">${typeof v2Placeholder==='function'?v2Placeholder():'<div class="apex10 apex10-na"><b>–</b><small>/ 280</small></div>'}</div>`;
  }
  const key=r&&(r.tv||r.yahoo||r.ticker);
  const b=key&&APEX_BARS.bars?APEX_BARS.bars[key]:null;
  // 23/11/2026 : préférer la note déjà posée sur l'instrument (ETC / métal au
  // comptant calculés dans build_metaux, absents d'apex_bars).
  const av=(r&&r.av&&r.av.score!=null)?r.av:(b&&b.av);
  const sent=(r&&r.sent&&r.sent.value!=null)?r.sent:(b&&b.sent);
  const ell=(r&&r.elliott)||(b&&b.elliott);
  const a10=(r&&r.apex10)||(b&&b.apex10)||null;
  if(!av||av.score==null||!sent||sent.value==null){
    if(a10&&a10.display&&a10.display!=='–'){
      const dec=(typeof apexDecomp==='function')?apexDecomp(a10):'';
      return `<div class="fl-apex"><div class="apex10"><b>${a10.display}</b><small>/100</small></div>${dec}</div>`;
    }
    return '<div class="fl-apex fl-apex-na"><div class="apex10 apex10-na"><b>–</b></div></div>';
  }
  const rec=a10||null; /* t320u : pas de recalcul JS */
  const avAff=(av.score_affiche!=null)?av.score_affiche:av.score;
  const dec=(typeof apexDecomp==='function')?apexDecomp(rec):'';
  return `<div class="fl-apex">${dualBar(sent.value,sent.label,avAff,av.label,'db-sm db-list',true,rec)}${dec}</div>`;
}
function fondQualite(r){
  if(!r||r.score==null) return '';
  const tip=(r.health!=null||r.growth!=null)?`Santé ${fmt(r.health,0)} · Croissance ${fmt(r.growth,0)}`:'';
  return `<span class="fl-sc" style="color:${gcol(r.score)}"${tip?` title="${tip}"`:''}><i>Qualité fondamentale</i>${fmt(r.score,0)}<small>/100</small></span>`;
}
const CPSVG='<svg viewBox="0 0 24 24" width="13" height="13" aria-hidden="true"><rect x="8" y="8" width="12" height="12" rx="2" fill="none" stroke="currentColor" stroke-width="2"/><path d="M16 8V6a2 2 0 0 0-2-2H6a2 2 0 0 0-2 2v8a2 2 0 0 0 2 2h2" fill="none" stroke="currentColor" stroke-width="2"/></svg>';
const tvTag=s=>s?`<span class="tvs"><code>${s}</code>${ophirCopyBtn(s)}</span>`:'<span class="tvs"><code>non vérifié</code></span>';
const ophirCopyBtn=s=>s?`<button type="button" class="cp" data-c="${String(s).replace(/"/g,'&quot;')}" aria-label="Copier ${String(s).replace(/"/g,'&quot;')}" title="Copier ${String(s).replace(/"/g,'&quot;')}">${CPSVG}</button>`:'';
function ophirCopy(btn){
  const t=btn.dataset.c;
  const done=ok=>{btn.classList.remove('ok','ko');void btn.offsetWidth;btn.classList.add(ok?'ok':'ko');btn.dataset.tip=ok?'Copié':'Échec';clearTimeout(btn._t);btn._t=setTimeout(()=>btn.classList.remove('ok','ko'),1600);};
  const fb=()=>{const ta=document.createElement('textarea');ta.value=t;ta.setAttribute('readonly','');ta.style.cssText='position:fixed;top:0;left:0;opacity:0;font-size:16px';
    document.body.appendChild(ta);ta.focus();ta.select();ta.setSelectionRange(0,t.length);let ok=false;try{ok=document.execCommand('copy');}catch(e){}ta.remove();done(ok);};
  if(navigator.clipboard&&window.isSecureContext)navigator.clipboard.writeText(t).then(()=>done(true),fb);else fb();
}
document.addEventListener('click',e=>{const b=e.target.closest('.cp');if(b){e.preventDefault();e.stopPropagation();ophirCopy(b);}});
const pc=(v,d=0)=>v==null?'n.d.':sign(v,d)+' %';
function fondChips(r,prof){
  const m=r.m,c=[];
  if(prof==='fin'){c.push(['ROE',m.roe==null?'n.d.':fmt(m.roe,0)+' %']);c.push(['ROA',m.roa==null?'n.d.':fmt(m.roa,1)+' %']);}
  else{c.push(['Dette nette / EBITDA',m.nd_ebitda==null?'n.d.':fmt(m.nd_ebitda,1)+' ×']);c.push([prof==='reit'?'Marge EBITDA':'Marge op.',(prof==='reit'?m.ebitda_margin:m.op_margin)==null?'n.d.':fmt(prof==='reit'?m.ebitda_margin:m.op_margin,0)+' %']);}
  c.push(['BPA est. N+1',pc(m.eps_1y)]);c.push(['CA est. N+1',pc(m.rev_1y)]);
  return c.map(([k,v])=>`<span><i>${k}</i> ${v}</span>`).join('');
}
function fondTiming(t){
  const b=t.near?`<b class="fl-warn">⚠ proche du plus haut${t.near==='ath'?' historique':' 52 s.'}</b>`:'';
  const ob=t.overbought?'<b class="fl-warn">RSI ≥ 70 suracheté</b>':'';
  return `${b}${ob}<span>${sign(t.dd52,1)} % vs plus haut 52 s. · ${sign(t.ddath,1)} % vs record (${dshort(t.ath_date)}) · RSI hebdo ${t.rsi==null?'n.d.':fmt(t.rsi,0)}</span>`;
}
function fondList(sym){
  const s=FOND.sectors[sym];if(!s)return '';
  const pSec=(typeof pilotOf==='function')?pilotOf(sym):null;
  const pilot=true;
  const top=(s.top||[]).slice(0,10);
  const ordered=top.slice().sort((a,b)=>{
    const pa=typeof pilotRec==='function'?pilotRec(a.tv):null;
    const pb=typeof pilotRec==='function'?pilotRec(b.tv):null;
    const ta=(pa&&pa.total!=null)?pa.total:-Infinity;
    const tb=(pb&&pb.total!=null)?pb.total:-Infinity;
    if(tb!==ta) return tb-ta;
    return 0;
  });
  const rows=ordered.map((r,k)=>
    `<li class="fl-row"${r.tv?` data-pos-tv="${r.tv}"`:''}><div class="fl-id"><span class="fl-rk">${k+1}</span><b>${r.name}</b>${tvTag(r.tv)}${typeof posBadges==='function'?posBadges(r.tv):''}${typeof dispoBadge==='function'?dispoBadge(r.tv):''}</div>${listApexBar(r)}</li>`
  ).join('');
  const d=s.top[0];
  const etfTv=(pSec&&pSec.etf&&pSec.etf.tv)||(s.etf&&s.etf.tv)||null;
  const etfBar=etfTv?listApexBar({tv:etfTv, name:(pSec&&pSec.etf&&pSec.etf.nom)||(s.etf&&s.etf.nom)||'', forceV2:true}):'';
  return `<details class="ind-meth sec-list"${pilot?` data-pilot="${String(sym).toLowerCase()}"`:''}><summary>ETF + ${top.length} actions qualité / croissance</summary>
   <div class="fl-etf"><span class="fl-k">ETF principal</span><b>${s.etf.name}</b>${tvTag(s.etf.tv)}${etfBar}</div>
   <ol class="fl${pilot?' fl-pilot':''}">${rows}</ol>
   <div class="sec-d" style="text-align:left">Score de qualité fondamentale 0-100 = 50 % santé financière + 50 % croissance prévue, en rang parmi les ${s.eligible} titres éligibles des 20 premières lignes de ${sym} (composition State Street au ${s.asof}).${s.profile==='fin'?' Profil financier : ROE, ROA, marges (ratios bancaires CET1 / créances douteuses non disponibles).':s.profile==='reit'?' Profil immobilier : dette nette / EBITDA, marges, ROA (FFO non disponible : la croissance repose sur le BPA estimé).':''} Timing (plus haut, RSI) affiché à part, hors score. Données ${lnk('https://finance.yahoo.com/quote/'+(d?d.yahoo:sym)+'/key-statistics/','Yahoo Finance')} récupérées le ${d?d.retrieved.replace(' ',' à '):'?'} ; clôtures hebdo au ${d?dshort(d.timing.date):'?'}.</div>
  </details>`;
}
function fondMethod(){
  const w=(a)=>a.map(([n,x])=>`${n} ${fmt(x*100,1)} %`).join(' · ');
  const ex=Object.entries(FOND.sectors).flatMap(([k,s])=>s.excluded.map(e=>`${k} ${e[0]}`));
  return `<p><b>Listes « ETF + top 10 actions » (sélection quantitative APEX).</b> Univers : les 20 premières lignes de chaque ETF SPDR d'après le fichier officiel des positions de State Street (doublons de catégories d'actions retirés : GOOG, FOX, NWS). Données : Yahoo Finance via yfinance (ratios sur 12 mois glissants et consensus d'analystes), récupérées le ${FOND.generated.replace(' ',' à ')}. Chaque métrique est convertie en rang percentile au sein de l'univers du secteur, puis pondérée ; un bloc se recalcule sur les métriques disponibles. Score = 50 % santé + 50 % croissance. Éligibilité : au moins 5 analystes (3 pour l'immobilier, où le consensus porte surtout sur le FFO et non sur le BPA), 2 métriques de croissance et l'essentiel des métriques de santé ; la croissance du BPA est ignorée si la base de comparaison est négative.</p>
   <ul><li><b>Santé, profil standard (50 %)</b> : ${w(FOND.weights.std)}</li><li><b>Santé, Finance (50 %)</b> : ${w(FOND.weights.fin)} ; ratios bancaires (CET1, créances douteuses) et ratio combiné des assureurs non disponibles</li>
   <li><b>Santé, Immobilier (50 %)</b> : ${w(FOND.weights.reit)} ; FFO / AFFO non disponibles dans la source</li><li><b>Croissance prévue (50 %)</b> : ${w(FOND.growth_weights)} ; la croissance long terme (5 ans) n'est pas fournie par la source pour les titres individuels</li></ul>
   <p>Timing, hors score : distance au plus haut 52 semaines et au record (clôtures hebdomadaires depuis la cotation), RSI 14 hebdo. ⚠ si le cours est à moins de 2 % du plus haut ; badge si RSI ≥ 70. La position dans une « vague 5 » d'Elliott n'est pas évaluée (non mesurable de façon objective).${ex.length?` Titres non classés faute de données : ${ex.join(', ')}.`:''}</p>`;
}
