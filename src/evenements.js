/* ===== ÉVÈNEMENT : détection d'événements sous-jacents (rail, sous INDICE ROTATION) ===== */
const EVT_KEY='apex-evt-open';
function evtData(){
  try{
    const el=document.getElementById('dataEvenements');
    if(!el) return null;
    const j=JSON.parse(el.textContent||'null');
    return j&&Array.isArray(j.evenements)?j:null;
  }catch(e){ return null; }
}
function evtEsc(s){
  return String(s==null?'':s).replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
}
function evtUrl(u){
  const s=String(u||'');
  return /^https?:\/\//i.test(s)?evtEsc(s):'#';
}
function evtHost(u){
  try{ return new URL(u).hostname.replace(/^www\./,''); }catch(e){ return ''; }
}
function evtMots(s,n){
  const w=String(s||'').trim().split(/\s+/).filter(Boolean);
  if(!w.length) return '';
  return w.length<=n?w.join(' '):w.slice(0,n).join(' ');
}
function evtTitre(e){
  const t=(e&&(e.titre_court||e.titre))||'';
  return evtMots(t,10);
}
function evtResume(e){
  const t=(e&&(e.resume_court||e.resume))||'';
  return evtMots(t,20);
}
function evtParseDay(s){
  const m=String(s||'').match(/^(\d{4})-(\d{2})-(\d{2})/);
  if(!m) return null;
  return new Date(Number(m[1]), Number(m[2])-1, Number(m[3]));
}
function evtFmtDM(d){
  if(!d) return '';
  const dd=String(d.getDate()).padStart(2,'0');
  const mm=String(d.getMonth()+1).padStart(2,'0');
  return dd+'/'+mm;
}
function evtToday(){
  const n=new Date();
  return new Date(n.getFullYear(), n.getMonth(), n.getDate());
}
function evtProchain(D){
  if(!D||!Array.isArray(D.evenements)) return null;
  const today=evtToday();
  const cands=[];
  D.evenements.forEach(e=>{
    (e.dates||[]).forEach(d=>{
      const debut=evtParseDay(d.debut), fin=evtParseDay(d.fin||d.debut);
      const end=fin||debut;
      if(!debut||!end||end<today) return;
      cands.push({debut, label:d.label||d.fenetre||e.titre, id:e.id, titre:e.titre});
    });
  });
  cands.sort((a,b)=>a.debut-b.debut);
  return cands[0]||null;
}
function evtDateCle(e){
  const today=evtToday();
  const cands=[];
  (e&&e.dates||[]).forEach(d=>{
    const debut=evtParseDay(d.debut), fin=evtParseDay(d.fin||d.debut);
    const end=fin||debut;
    if(!debut||!end||end<today) return;
    cands.push({debut, label:d.label||d.fenetre||'', fenetre:d.fenetre||''});
  });
  cands.sort((a,b)=>a.debut-b.debut);
  return cands[0]||null;
}
function evtImpactHtml(e){
  const arr=(e&&Array.isArray(e.impacts)?e.impacts:[]).slice(0,4);
  if(!arr.length) return '';
  const parts=arr.map(it=>{
    const down=String(it.sens||'')==='baisse';
    const arrow=down?'▼':'▲';
    const cls=down?'evt-dn':'evt-up';
    return `<span class="${cls}">${arrow} ${evtEsc(it.libelle||'')}</span>`;
  });
  return `<p class="evt-impact">${parts.join('')}</p>`;
}
function evtSetMenuOpen(on){
  const btn=document.getElementById('evtDdBtn');
  const list=document.getElementById('evtDdList');
  if(!btn||!list) return;
  btn.setAttribute('aria-expanded', on?'true':'false');
  if(on) list.removeAttribute('hidden');
  else list.setAttribute('hidden','');
}
function evtFineHover(){
  try{ return window.matchMedia('(hover: hover) and (pointer: fine)').matches; }catch(e){ return false; }
}
function evtPopEl(){
  let el=document.getElementById('evtPop');
  if(!el){
    el=document.createElement('div');
    el.id='evtPop';
    el.className='evt-pop';
    el.setAttribute('role','dialog');
    el.setAttribute('aria-modal','false');
    el.hidden=true;
    document.body.appendChild(el);
    el.addEventListener('pointerenter',()=>{ clearTimeout(evtPopTimer); });
    el.addEventListener('pointerleave',()=>{ if(evtFineHover() && !evtPopPinned) evtPopTimer=setTimeout(evtClosePop,180); });
  }
  return el;
}
function evtClosePop(){
  clearTimeout(evtPopTimer);
  evtPopPinned=false;
  const pop=document.getElementById('evtPop');
  if(pop){ pop.hidden=true; pop.innerHTML=''; pop.removeAttribute('data-evt-for'); }
  document.querySelectorAll('.evt-fig[aria-expanded="true"]').forEach(b=>b.setAttribute('aria-expanded','false'));
}
function evtPopHtml(e, kind){
  if(kind==='prob'){
    return `<p class="evt-pop-h">Probabilité ${evtEsc(e.probabilite)} %</p>
      <p class="evt-t">Confiance : ${evtEsc(e.confiance||'—')}</p>
      ${e.evenement_mesure?`<p class="evt-k">Événement mesuré</p><p class="evt-t">${evtEsc(e.evenement_mesure)}</p>`:''}`;
  }
  if(kind==='score'){
    const d=e.decomposition_score||{};
    const med=e.mediatisation||{};
    const signaux=(e.signaux||[]).map(s=>`<li>${evtEsc(s)}</li>`).join('');
    const actifs=(e.actifs||[]).map(evtEsc).join(' · ');
    const decomp=e.decomposition_score?`<p class="evt-t">Intensité ${evtEsc(d.intensite)} + corroboration ${evtEsc(d.corroboration)} + sous-exposition ${evtEsc(d.sous_exposition)} + impact ${evtEsc(d.impact)} (sur 25 chacun)</p>`:'';
    return `<p class="evt-pop-h">Score ${evtEsc(e.score)}/100</p>
      ${decomp}
      ${actifs?`<p class="evt-k">Actifs touchés</p><p class="evt-t">${actifs}</p>`:''}
      <p class="evt-k">Médiatisation : ${evtEsc(med.niveau||'—')}</p>
      <p class="evt-t">${evtEsc(med.mesure||'')} ${evtEsc(med.pourquoi||'')}${med.requete_x?` <span style="color:var(--mut,#bababa)">Requête X : « ${evtEsc(med.requete_x)} ».</span>`:''}</p>
      ${signaux?`<p class="evt-k">Signaux relevés</p><ul class="evt-ul">${signaux}</ul>`:''}`;
  }
  const dates=(e.dates||[]).slice(0,3).map((d,i)=>`<div class="evt-d"><span class="n">${i+1}</span><span class="w">${evtEsc(d.fenetre||evtFmtDM(evtParseDay(d.debut))||'')}</span><span class="f">${evtEsc(d.fait||'')}${d.source?`<a href="${evtUrl(d.source)}" target="_blank" rel="noopener noreferrer">${evtEsc(evtHost(d.source)||'source')} ↗</a>`:''}</span></div>`).join('');
  const sources=(e.sources||[]).map(s=>`<li><a href="${evtUrl(s.url)}" target="_blank" rel="noopener noreferrer">${evtEsc(s.nom)}</a>${s.date?` <span style="color:var(--mut,#bababa)">(${evtEsc(s.date)})</span>`:''}</li>`).join('');
  return `<p class="evt-pop-h">Dates à surveiller</p>
    <div class="evt-dates">${dates||'<p class="evt-t">—</p>'}</div>
    ${sources?`<p class="evt-k">Sources</p><ul class="evt-ul evt-src">${sources}</ul>`:''}`;
}
function evtPlacePop(pop, anchor){
  const margin=8;
  const vw=window.innerWidth;
  const vh=window.innerHeight;
  pop.style.position='fixed';
  pop.style.right='auto';
  pop.style.bottom='auto';
  pop.style.maxWidth=Math.min(360, Math.max(180, vw-margin*2))+'px';
  pop.style.width='auto';
  pop.style.maxHeight=Math.min(vh-margin*2, Math.floor(vh*0.62))+'px';
  pop.style.overflowY='auto';
  pop.style.overflowX='hidden';
  pop.style.left='0px';
  pop.style.top='0px';
  const pw=pop.offsetWidth;
  const ph=pop.offsetHeight;
  const r=anchor.getBoundingClientRect();
  const spaceLeft=r.left-margin;
  const spaceRight=vw-margin-r.right;
  let left, top;
  if(pw<=spaceLeft || pw<=spaceRight){
    left=pw<=spaceLeft && (spaceLeft>=spaceRight || pw>spaceRight) ? Math.round(r.left-pw-6) : Math.round(r.right+6);
    top=Math.round(r.top);
    if(top+ph>vh-margin) top=vh-margin-ph;
    if(top<margin) top=margin;
  }else{
    left=Math.round(r.left+r.width/2-pw/2);
    if(left+pw>vw-margin) left=vw-margin-pw;
    if(left<margin) left=margin;
    top=Math.round(r.bottom+6);
    if(top+ph>vh-margin){
      const above=r.top-ph-6;
      top=above>=margin?Math.round(above):margin;
    }
  }
  pop.style.left=left+'px';
  pop.style.top=top+'px';
}
function evtOpenPop(btn, pin){
  const id=btn.getAttribute('data-evt-id');
  const kind=btn.getAttribute('data-evt-pop');
  const D=evtData();
  const e=(D&&D.evenements||[]).find(x=>String(x.id)===String(id));
  if(!e) return;
  const pop=evtPopEl();
  document.querySelectorAll('.evt-fig[aria-expanded="true"]').forEach(b=>{ if(b!==btn) b.setAttribute('aria-expanded','false'); });
  btn.setAttribute('aria-expanded','true');
  pop.innerHTML=evtPopHtml(e, kind);
  pop.hidden=false;
  pop.setAttribute('data-evt-for', id+':'+kind);
  evtPopPinned=!!pin;
  evtPlacePop(pop, btn);
}
let evtPopTimer=0;
let evtPopPinned=false;
function evtBindPops(card){
  if(!card) return;
  card.querySelectorAll('.evt-fig').forEach(btn=>{
    btn.addEventListener('click',e=>{
      e.preventDefault();
      e.stopPropagation();
      const pop=document.getElementById('evtPop');
      const open=btn.getAttribute('aria-expanded')==='true' && pop && !pop.hidden;
      // Un second clic ferme seulement un popover déjà épinglé (le survol ne compte pas).
      if(open && evtPopPinned) evtClosePop();
      else { clearTimeout(evtPopTimer); evtOpenPop(btn, true); }
    });
    btn.addEventListener('pointerenter',e=>{
      if(!evtFineHover()) return;
      if(e.pointerType && e.pointerType!=='mouse') return;
      clearTimeout(evtPopTimer);
      evtOpenPop(btn, false);
    });
    btn.addEventListener('pointerleave',()=>{
      if(!evtFineHover() || evtPopPinned) return;
      evtPopTimer=setTimeout(evtClosePop,180);
    });
  });
  if(!document.documentElement._evtPopBound){
    document.documentElement._evtPopBound=true;
    document.addEventListener('pointerdown',e=>{
      if(e.target.closest('.evt-fig') || e.target.closest('#evtPop')) return;
      evtClosePop();
    }, true);
    document.addEventListener('keydown',e=>{ if(e.key==='Escape') evtClosePop(); });
    window.addEventListener('resize',()=>{
      const pop=document.getElementById('evtPop');
      if(!pop||pop.hidden) return;
      const btn=document.querySelector('.evt-fig[aria-expanded="true"]');
      if(btn) evtPlacePop(pop,btn); else evtClosePop();
    });
    window.addEventListener('scroll',()=>{
      const pop=document.getElementById('evtPop');
      if(!pop||pop.hidden) return;
      const btn=document.querySelector('.evt-fig[aria-expanded="true"]');
      if(!btn){ evtClosePop(); return; }
      const r=btn.getBoundingClientRect();
      if(r.bottom<0||r.top>window.innerHeight) evtClosePop();
      else evtPlacePop(pop,btn);
    }, true);
  }
}

function evtStyle(){
  if(document.getElementById('evtStyle')) return;
  const css=`
.evt-body{margin-top:6px;overflow-x:hidden}
.evt-maj{font-size:11px;color:var(--mut,#bababa);margin:0 0 8px}
.evt-disc{font-size:10.5px;color:var(--mut,#9a9a9a);font-weight:500}
.evt-card{border:1px solid rgba(255,255,255,.14);border-radius:10px;padding:8px 10px;margin:0 0 8px;background:rgba(255,255,255,.03);overflow-x:hidden}
.evt-top{display:flex;align-items:baseline;gap:8px;min-width:0}
.evt-rang{flex:none;font-size:15px;font-weight:800;color:var(--acc2,#e6c27a)}
.evt-titre{font-size:13px;font-weight:700;color:#fff;line-height:1.25;margin:0;min-width:0}
.evt-figs{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:4px;margin:6px 0 4px}
.evt-fig{appearance:none;-webkit-appearance:none;display:block;width:100%;margin:0;padding:4px 2px;border:0;border-radius:8px;background:transparent;color:inherit;font:inherit;cursor:pointer;text-align:center;min-width:0}
.evt-fig:hover,.evt-fig:focus-visible,.evt-fig[aria-expanded="true"]{background:rgba(255,255,255,.07)}
.evt-fig:focus-visible{outline:1px solid rgba(230,194,122,.8);outline-offset:1px}
.evt-fig-n{display:block;font-size:22px;font-weight:800;line-height:1.05;font-variant-numeric:tabular-nums;color:#fff;letter-spacing:-.02em;white-space:nowrap}
.evt-fig-n.evt-p{color:var(--acc2,#e6c27a)}
.evt-fig-u{font-size:12px;font-weight:750;letter-spacing:0;color:inherit;opacity:.85}
.evt-fig-l{display:block;font-size:9px;font-weight:700;letter-spacing:.05em;text-transform:uppercase;color:var(--mut,#bababa);margin-top:2px;white-space:nowrap}
.evt-res{font-size:12px;line-height:1.3;color:#e8e8e8;margin:4px 0 0}
.evt-k{font-size:10px;font-weight:700;letter-spacing:.06em;text-transform:uppercase;color:var(--mut,#bababa);margin:8px 0 3px}
.evt-t{font-size:11.5px;line-height:1.4;color:#d8d8d8;margin:0;overflow-wrap:anywhere;word-break:break-word}
.evt-ul{margin:0;padding-left:16px}
.evt-ul li{font-size:11.5px;line-height:1.4;color:#d8d8d8;margin:0 0 3px;overflow-wrap:anywhere;word-break:break-word}
.evt-ul a,.evt-src a{color:var(--acc,#a9cdf5);text-decoration:none}
.evt-ul a:hover,.evt-src a:hover{text-decoration:underline}
.evt-dates{display:grid;gap:6px;margin-top:4px}
.evt-d{display:grid;grid-template-columns:auto minmax(0,1fr);gap:2px 8px;align-items:baseline;border-left:2px solid var(--acc2,#e6c27a);padding:2px 0 2px 8px;min-width:0}
.evt-d .n{font-size:11px;font-weight:800;color:var(--acc2,#e6c27a)}
.evt-d .w{font-size:12px;font-weight:700;color:#fff;font-variant-numeric:tabular-nums}
.evt-d .f{grid-column:1/-1;font-size:11px;line-height:1.35;color:#cfcfcf;overflow-wrap:anywhere;word-break:break-word}
.evt-d .f a{color:var(--acc,#a9cdf5);text-decoration:none;margin-left:4px}
.evt-empty{margin:0;padding:10px 12px;border:1px dashed rgba(230,194,122,.35);border-radius:10px;color:#c8c4bc;font-size:12px}
.evt-impact{font-size:11.5px;font-weight:750;line-height:1.3;margin:0;display:flex;flex-wrap:wrap;gap:2px 10px;font-variant-numeric:tabular-nums}
.evt-up{color:#4ade80}
.evt-dn{color:#f87171}
.evt-dd{position:relative;min-width:0;flex:1 1 auto}
.evt-dd-btn{appearance:none;-webkit-appearance:none;display:flex;align-items:center;gap:6px;max-width:100%;margin:0;padding:0;border:0;background:transparent;color:inherit;font:inherit;cursor:pointer;text-align:left}
.evt-dd-btn:focus-visible{outline:1px solid rgba(230,194,122,.8);outline-offset:3px;border-radius:6px}
.evt-dd-caret{flex:none;color:var(--acc2,#e6c27a);font-size:11px;line-height:1}
.evt-dd-btn[aria-expanded="true"] .evt-dd-caret{transform:rotate(180deg)}
.evt-dd-list{position:absolute;z-index:5;left:0;right:auto;top:calc(100% + 6px);min-width:min(420px,70vw);max-width:min(420px,calc(100vw - 16px));margin:0;padding:6px 0;list-style:none;background:#14181f;border:1px solid rgba(230,194,122,.35);border-radius:10px;box-shadow:0 12px 32px rgba(0,0,0,.45)}
.evt-dd-list[hidden]{display:none !important}
.evt-dd-list a{display:block;padding:8px 12px;color:#f2efe8;text-decoration:none;font-size:12.5px;line-height:1.35;font-weight:650}
.evt-dd-list a:hover,.evt-dd-list a:focus{background:rgba(230,194,122,.12);color:#fff}
.evt-next{font-weight:650;letter-spacing:.04em}
#evtCard h2{white-space:normal;line-height:1.3}
#mes-pos:not(.is-expanded) #evtCard.pos-collapsed .evt-next-full{display:none}
#mes-pos:not(.is-expanded) #evtCard.pos-collapsed h2{white-space:nowrap}
.evt-pop{position:fixed;z-index:9999;box-sizing:border-box;min-width:0;padding:10px 12px;background:#14181f;border:1px solid rgba(230,194,122,.45);border-radius:10px;box-shadow:0 12px 32px rgba(0,0,0,.5);color:#e8e8e8;overflow-x:hidden;overflow-y:auto;-webkit-overflow-scrolling:touch}
.evt-pop[hidden]{display:none !important}
.evt-pop-h{margin:0 0 6px;font-size:13px;font-weight:800;color:#fff}
`;
  const st=document.createElement('style');
  st.id='evtStyle';
  st.textContent=css;
  document.head.appendChild(st);
}
function evtCardHtml(e){
  const nx=evtDateCle(e);
  const dateTxt=nx?evtFmtDM(nx.debut):'—';
  const id=evtEsc(e.id);
  return `<article class="evt-card" id="evt-${id}">
    <div class="evt-top"><span class="evt-rang">#${evtEsc(e.rang)}</span><p class="evt-titre">${evtEsc(evtTitre(e))}</p></div>
    <div class="evt-figs">
      <button type="button" class="evt-fig" data-evt-id="${id}" data-evt-pop="prob" aria-expanded="false" aria-label="Probabilité ${evtEsc(e.probabilite)} %. Afficher le détail.">
        <span class="evt-fig-n evt-p">${evtEsc(e.probabilite)}<span class="evt-fig-u"> %</span></span>
        <span class="evt-fig-l">Probabilité</span>
      </button>
      <button type="button" class="evt-fig" data-evt-id="${id}" data-evt-pop="score" aria-expanded="false" aria-label="Score ${evtEsc(e.score)} sur 100. Afficher le détail.">
        <span class="evt-fig-n">${evtEsc(e.score)}<span class="evt-fig-u">/100</span></span>
        <span class="evt-fig-l">Score</span>
      </button>
      <button type="button" class="evt-fig" data-evt-id="${id}" data-evt-pop="date" aria-expanded="false" aria-label="Date clé ${evtEsc(dateTxt)}${nx&&nx.label?' · '+evtEsc(nx.label):''}. Afficher le détail.">
        <span class="evt-fig-n">${evtEsc(dateTxt)}</span>
        <span class="evt-fig-l">Date clé</span>
      </button>
    </div>
    ${evtImpactHtml(e)}
    ${evtResume(e)?`<p class="evt-res">${evtEsc(evtResume(e))}</p>`:''}
  </article>`;
}
function evtHtml(){
  const D=evtData();
  let body, n=0;
  if(!D){
    body=`<p class="evt-empty">Les données des événements n’ont pas pu être chargées. Aucun chiffre n’est inventé.</p>`;
  }else{
    const evs=D.evenements.slice().sort((a,b)=>(a.rang||9)-(b.rang||9)).slice(0,3);
    n=evs.length;
    body=`<p class="evt-maj">Mise à jour : ${evtEsc(D.maj_label||D.maj||'—')} · <span class="evt-disc">Estimations, pas des conseils</span></p>
      ${evs.map(evtCardHtml).join('')}`;
  }
  const nx=D?evtProchain(D):null;
  const nxTxt=nx?(` · <span class="evt-next">prochain : ${evtEsc(evtFmtDM(nx.debut))} <span class="evt-next-full">${evtEsc(nx.label)}</span></span>`):'';
  const menu=(!D||!n)?'':`<div class="evt-dd" id="evtDd">
      <button type="button" class="evt-dd-btn" id="evtDdBtn" aria-haspopup="listbox" aria-expanded="false" aria-controls="evtDdList">
        <h2>ÉVÈNEMENT${nxTxt}</h2>
        <span class="evt-dd-caret" aria-hidden="true">▾</span>
      </button>
      <ul class="evt-dd-list" id="evtDdList" hidden role="listbox">
        ${ (D.evenements.slice().sort((a,b)=>(a.rang||9)-(b.rang||9)).slice(0,3) ).map(e=>`<li role="option"><a href="#evt-${evtEsc(e.id)}" data-evt="${evtEsc(e.id)}">#${evtEsc(e.rang)} ${evtEsc(evtTitre(e))}</a></li>`).join('') }
      </ul>
    </div>`;
  return `<div class="card no-group" id="evtCard">
    <div class="pos-rail-h" role="button" tabindex="0" aria-expanded="false" aria-controls="evtBody">
      <span class="pos-chev" aria-hidden="true">▸</span>
      ${menu||`<h2>ÉVÈNEMENT${nxTxt}</h2>`}
      <span class="pos-head-tot">${n}<small>évènement${n>1?'s':''}</small></span>
    </div>
    <div class="pos-body gi-body evt-body" id="evtBody">${body}</div>
  </div>`;
}
function evtListIsOpen(){
  const c=document.getElementById('evtCard');
  return !!(c&&!c.classList.contains('pos-collapsed'));
}
function evtSetListOpen(on,persist){
  const c=document.getElementById('evtCard');
  if(!c) return;
  if(!on) evtClosePop();
  c.classList.toggle('pos-collapsed',!on);
  const head=c.querySelector('.pos-rail-h');
  if(head) head.setAttribute('aria-expanded', on?'true':'false');
  if(persist!==false){ try{ localStorage.setItem(EVT_KEY, on?'1':'0'); }catch(e){} }
  if(typeof posSyncListChrome==='function') posSyncListChrome(typeof posListIsOpen==='function'&&posListIsOpen());
}
function evtMount(){
  const host=document.getElementById('mes-pos');
  if(!host) return;
  evtStyle();
  const html=evtHtml();
  const prev=document.getElementById('evtCard');
  const ir=document.getElementById('indiceRotationCard');
  const gs=document.getElementById('bestShortCard');
  if(prev) prev.outerHTML=html;
  else if(ir) ir.insertAdjacentHTML('afterend', html);
  else if(gs) gs.insertAdjacentHTML('afterend', html);
  else host.insertAdjacentHTML('beforeend', html);
  const card=document.getElementById('evtCard');
  if(!card) return;
  let saved=null;
  try{ saved=localStorage.getItem(EVT_KEY); }catch(e){}
  const open=saved==='1';
  card.classList.toggle('pos-collapsed', !open);
  const head=card.querySelector('.pos-rail-h');
  if(head){
    head.setAttribute('aria-expanded', open?'true':'false');
    const tog=e=>{ e.preventDefault(); evtSetListOpen(!evtListIsOpen()); };
    head.addEventListener('click',e=>{ if(e.target.closest('.evt-dd')||e.target.closest('.evt-fig')) return; tog(e); });
    head.addEventListener('keydown',e=>{ if(e.target.closest('.evt-dd')||e.target.closest('.evt-fig')) return; if(e.key==='Enter'||e.key===' '){ e.preventDefault(); tog(e); } });
  }
  const ddBtn=document.getElementById('evtDdBtn');
  const ddList=document.getElementById('evtDdList');
  if(ddBtn&&ddList){
    ddBtn.addEventListener('click',e=>{ e.preventDefault(); e.stopPropagation(); evtSetMenuOpen(ddBtn.getAttribute('aria-expanded')!=='true'); });
    ddList.addEventListener('click',e=>{
      const a=e.target.closest('a[data-evt]');
      if(!a) return;
      e.preventDefault();
      e.stopPropagation();
      evtSetMenuOpen(false);
      evtSetListOpen(true);
      const target=document.getElementById('evt-'+a.getAttribute('data-evt'));
      if(target) target.scrollIntoView({block:'nearest', behavior:'smooth'});
    });
    if(!document.documentElement._evtDdBound){
      document.documentElement._evtDdBound=true;
      document.addEventListener('click',e=>{ if(!e.target.closest('#evtDd')) evtSetMenuOpen(false); });
      document.addEventListener('keydown',e=>{ if(e.key==='Escape') evtSetMenuOpen(false); });
    }
  }
  evtBindPops(card);
  if(typeof posSyncListChrome==='function') posSyncListChrome(typeof posListIsOpen==='function'&&posListIsOpen());
}
function evtInit(){
  evtMount();
}
