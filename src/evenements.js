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
function evtConfClass(c){
  const k=String(c||'').toLowerCase();
  if(k.startsWith('élev')||k.startsWith('elev')) return 'evt-c-hi';
  if(k.startsWith('moy')) return 'evt-c-mid';
  return 'evt-c-lo';
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
function evtImpactHtml(e){
  const arr=e&&Array.isArray(e.impacts)?e.impacts:[];
  if(!arr.length) return '';
  const parts=arr.map(it=>{
    const down=String(it.sens||'')==='baisse';
    const arrow=down?'▼':'▲';
    const cls=down?'evt-dn':'evt-up';
    return `<span class="${cls}">${arrow} ${evtEsc(it.libelle||'')}</span>`;
  });
  return `<p class="evt-impact">${parts.join(' · ')}</p>`;
}
function evtSetMenuOpen(on){
  const btn=document.getElementById('evtDdBtn');
  const list=document.getElementById('evtDdList');
  if(!btn||!list) return;
  btn.setAttribute('aria-expanded', on?'true':'false');
  if(on) list.removeAttribute('hidden');
  else list.setAttribute('hidden','');
}

function evtStyle(){
  if(document.getElementById('evtStyle')) return;
  const css=`
.evt-body{margin-top:6px}
.evt-maj{font-size:11px;color:var(--mut,#bababa);margin:0 0 6px}
.evt-warn{font-size:10.5px;line-height:1.35;color:var(--acc2,#e6c27a);margin:0 0 10px}
.evt-card{border:1px solid rgba(255,255,255,.14);border-radius:10px;padding:10px 12px;margin:0 0 10px;background:rgba(255,255,255,.03)}
.evt-top{display:flex;align-items:baseline;gap:8px}
.evt-rang{flex:none;font-size:15px;font-weight:800;color:var(--acc2,#e6c27a)}
.evt-titre{font-size:13px;font-weight:700;color:#fff;line-height:1.3;margin:0}
.evt-badges{display:flex;flex-wrap:wrap;gap:6px;margin:8px 0 6px}
.evt-b{font-size:10.5px;font-weight:700;border-radius:999px;padding:2px 8px;border:1px solid rgba(255,255,255,.2);color:#fff;white-space:nowrap;font-variant-numeric:tabular-nums}
.evt-b.evt-p{border-color:rgba(230,194,122,.6);color:var(--acc2,#e6c27a)}
.evt-b.evt-c-hi{border-color:rgba(127,209,168,.6);color:var(--up,#7fd1a8)}
.evt-b.evt-c-mid{border-color:rgba(169,205,245,.6);color:var(--acc,#a9cdf5)}
.evt-b.evt-c-lo{border-color:rgba(232,143,143,.6);color:var(--down,#e88f8f)}
.evt-b.evt-cat{color:var(--mut,#bababa)}
.evt-res{font-size:12px;line-height:1.4;color:#e8e8e8;margin:0 0 6px}
.evt-k{font-size:10px;font-weight:700;letter-spacing:.06em;text-transform:uppercase;color:var(--mut,#bababa);margin:8px 0 3px}
.evt-t{font-size:11.5px;line-height:1.4;color:#d8d8d8;margin:0}
.evt-ul{margin:0;padding-left:16px}
.evt-ul li{font-size:11.5px;line-height:1.4;color:#d8d8d8;margin:0 0 3px}
.evt-ul a,.evt-src a,.evt-ecart a{color:var(--acc,#a9cdf5);text-decoration:none}
.evt-ul a:hover,.evt-src a:hover,.evt-ecart a:hover{text-decoration:underline}
.evt-dates{display:grid;gap:6px;margin-top:4px}
.evt-d{display:grid;grid-template-columns:auto minmax(0,1fr);gap:2px 8px;align-items:baseline;border-left:2px solid var(--acc2,#e6c27a);padding:2px 0 2px 8px}
.evt-d .n{font-size:11px;font-weight:800;color:var(--acc2,#e6c27a)}
.evt-d .w{font-size:12px;font-weight:700;color:#fff;font-variant-numeric:tabular-nums}
.evt-d .f{grid-column:1/-1;font-size:11px;line-height:1.35;color:#cfcfcf}
.evt-d .f a{color:var(--acc,#a9cdf5);text-decoration:none;margin-left:4px}
.evt-meth{margin:6px 0 0;padding-left:16px}
.evt-meth li{font-size:11px;line-height:1.4;color:#cfcfcf;margin:0 0 3px}
.evt-ecart{font-size:11px;line-height:1.4;color:#cfcfcf;margin:0 0 4px}
.evt-empty{margin:0;padding:10px 12px;border:1px dashed rgba(230,194,122,.35);border-radius:10px;color:#c8c4bc;font-size:12px}
.evt-impact{font-size:13px;font-weight:750;line-height:1.4;margin:0 0 8px;font-variant-numeric:tabular-nums}
.evt-up{color:#4ade80}
.evt-dn{color:#f87171}
.evt-dd{position:relative;min-width:0;flex:1 1 auto}
.evt-dd-btn{appearance:none;-webkit-appearance:none;display:flex;align-items:center;gap:6px;max-width:100%;margin:0;padding:0;border:0;background:transparent;color:inherit;font:inherit;cursor:pointer;text-align:left}
.evt-dd-btn:focus-visible{outline:1px solid rgba(230,194,122,.8);outline-offset:3px;border-radius:6px}
.evt-dd-caret{flex:none;color:var(--acc2,#e6c27a);font-size:11px;line-height:1}
.evt-dd-btn[aria-expanded="true"] .evt-dd-caret{transform:rotate(180deg)}
.evt-dd-list{position:absolute;z-index:5;left:0;right:auto;top:calc(100% + 6px);min-width:min(420px,70vw);margin:0;padding:6px 0;list-style:none;background:#14181f;border:1px solid rgba(230,194,122,.35);border-radius:10px;box-shadow:0 12px 32px rgba(0,0,0,.45)}
.evt-dd-list[hidden]{display:none !important}
.evt-dd-list a{display:block;padding:8px 12px;color:#f2efe8;text-decoration:none;font-size:12.5px;line-height:1.35;font-weight:650}
.evt-dd-list a:hover,.evt-dd-list a:focus{background:rgba(230,194,122,.12);color:#fff}
.evt-next{font-weight:650;letter-spacing:.04em}
#evtCard h2{white-space:normal;line-height:1.3}
#mes-pos:not(.is-expanded) #evtCard.pos-collapsed .evt-next-full{display:none}
#mes-pos:not(.is-expanded) #evtCard.pos-collapsed h2{white-space:nowrap}
`;
  const st=document.createElement('style');
  st.id='evtStyle';
  st.textContent=css;
  document.head.appendChild(st);
}
function evtCardHtml(e){
  const sources=(e.sources||[]).map(s=>`<li><a href="${evtUrl(s.url)}" target="_blank" rel="noopener noreferrer">${evtEsc(s.nom)}</a>${s.date?` <span style="color:var(--mut,#bababa)">(${evtEsc(s.date)})</span>`:''}</li>`).join('');
  const signaux=(e.signaux||[]).map(s=>`<li>${evtEsc(s)}</li>`).join('');
  const actifs=(e.actifs||[]).map(evtEsc).join(' · ');
  const med=e.mediatisation||{};
  const dates=(e.dates||[]).slice(0,3).map((d,i)=>`<div class="evt-d"><span class="n">${i+1}</span><span class="w">${evtEsc(d.fenetre)}</span><span class="f">${evtEsc(d.fait)}${d.source?`<a href="${evtUrl(d.source)}" target="_blank" rel="noopener noreferrer">${evtEsc(evtHost(d.source)||'source')} ↗</a>`:''}</span></div>`).join('');
  return `<article class="evt-card" id="evt-${evtEsc(e.id)}">
    <div class="evt-top"><span class="evt-rang">#${evtEsc(e.rang)}</span><p class="evt-titre">${evtEsc(e.titre)}</p></div>
    <div class="evt-badges">
      <span class="evt-b evt-p">Probabilité ${evtEsc(e.probabilite)} %</span>
      <span class="evt-b">Score ${evtEsc(e.score)}/100</span>
      <span class="evt-b ${evtConfClass(e.confiance)}">Confiance ${evtEsc(e.confiance)}</span>
      <span class="evt-b evt-cat">${evtEsc(e.categorie)}</span>
    </div>
    ${evtImpactHtml(e)}
    <p class="evt-res">${evtEsc(e.resume)}</p>
    ${e.decomposition_score?`<p class="evt-t" style="color:var(--mut,#bababa)">Score = intensité ${evtEsc(e.decomposition_score.intensite)} + corroboration ${evtEsc(e.decomposition_score.corroboration)} + sous-exposition ${evtEsc(e.decomposition_score.sous_exposition)} + impact ${evtEsc(e.decomposition_score.impact)} (sur 25 chacun)</p>`:''}
    ${e.evenement_mesure?`<p class="evt-k">Événement mesuré</p><p class="evt-t">${evtEsc(e.evenement_mesure)}</p>`:''}
    <p class="evt-k">Actifs ou secteurs touchés</p><p class="evt-t">${actifs||'—'}</p>
    <p class="evt-k">Médiatisation : ${evtEsc(med.niveau||'—')}</p><p class="evt-t">${evtEsc(med.mesure||'')} ${evtEsc(med.pourquoi||'')}${med.requete_x?` <span style="color:var(--mut,#bababa)">Requête X : « ${evtEsc(med.requete_x)} ».</span>`:''}</p>
    ${signaux?`<p class="evt-k">Signaux relevés</p><ul class="evt-ul">${signaux}</ul>`:''}
    <p class="evt-k">Sources</p><ul class="evt-ul evt-src">${sources||'<li>—</li>'}</ul>
    <p class="evt-k">3 dates ou fenêtres de déclenchement à surveiller</p>
    <div class="evt-dates">${dates||'<p class="evt-t">—</p>'}</div>
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
    const meth=(D.methode||[]).map(m=>`<li>${evtEsc(m)}</li>`).join('');
    const ec=(D.ecartes||[]).map(x=>`<p class="evt-ecart"><b>${evtEsc(x.sujet)}</b> : ${evtEsc(x.raison)}${x.url?` <a href="${evtUrl(x.url)}" target="_blank" rel="noopener noreferrer">source ↗</a>`:''}</p>`).join('');
    body=`<p class="evt-maj">Mise à jour : ${evtEsc(D.maj_label||D.maj||'—')} · horizon ${evtEsc(D.horizon||'—')}</p>
      <p class="evt-warn">${evtEsc(D.avertissement||'Estimations à partir de signaux faibles, pas des prévisions ; aucun conseil d’achat ou de vente.')}</p>
      ${evs.map(evtCardHtml).join('')}
      ${ec?`<p class="evt-k">Signaux écartés cette fois</p>${ec}`:''}
      ${meth?`<p class="evt-k">Méthode</p><ul class="evt-meth">${meth}</ul>`:''}
      ${(D.limites||[]).length?`<p class="evt-k">Limites</p><ul class="evt-meth">${D.limites.map(x=>`<li>${evtEsc(x)}</li>`).join('')}</ul>`:''}`;
  }
  const nx=D?evtProchain(D):null;
  const nxTxt=nx?(` · <span class="evt-next">prochain : ${evtEsc(evtFmtDM(nx.debut))} <span class="evt-next-full">${evtEsc(nx.label)}</span></span>`):'';
  const menu=(!D||!n)?'':`<div class="evt-dd" id="evtDd">
      <button type="button" class="evt-dd-btn" id="evtDdBtn" aria-haspopup="listbox" aria-expanded="false" aria-controls="evtDdList">
        <h2>ÉVÈNEMENT${nxTxt}</h2>
        <span class="evt-dd-caret" aria-hidden="true">▾</span>
      </button>
      <ul class="evt-dd-list" id="evtDdList" hidden role="listbox">
        ${ (D.evenements.slice().sort((a,b)=>(a.rang||9)-(b.rang||9)).slice(0,3) ).map(e=>`<li role="option"><a href="#evt-${evtEsc(e.id)}" data-evt="${evtEsc(e.id)}">#${evtEsc(e.rang)} ${evtEsc(e.titre)}</a></li>`).join('') }
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
    head.addEventListener('click',e=>{ if(e.target.closest('.evt-dd')) return; tog(e); });
    head.addEventListener('keydown',e=>{ if(e.target.closest('.evt-dd')) return; if(e.key==='Enter'||e.key===' '){ e.preventDefault(); tog(e); } });
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
  if(typeof posSyncListChrome==='function') posSyncListChrome(typeof posListIsOpen==='function'&&posListIsOpen());
}
function evtInit(){
  evtMount();
}
