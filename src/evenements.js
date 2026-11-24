/* ===== Détection d'événements SOUS-JACENTS non médiatisés (dans INDICE ROTATION) ===== */
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
function evtStyle(){
  if(document.getElementById('evtStyle')) return;
  const css=`
.evt-wrap{margin-top:14px;border-top:1px solid var(--soft,rgba(255,255,255,.1));padding-top:10px}
.evt-h{display:flex;align-items:center;gap:8px;cursor:pointer;user-select:none;padding:4px 0}
.evt-h:focus-visible{outline:1px solid rgba(255,255,255,.35);outline-offset:2px;border-radius:8px}
.evt-h .evt-chev{flex:none;width:14px;color:var(--mut,#bababa);font-size:12px;line-height:1;transition:transform .2s ease}
.evt-wrap.is-open .evt-h .evt-chev{transform:rotate(90deg)}
.evt-h h3{margin:0;font-size:12px;font-weight:750;letter-spacing:.06em;text-transform:uppercase;color:#fff;line-height:1.3}
.evt-body{display:none;margin-top:8px}
.evt-wrap.is-open .evt-body{display:block}
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
.evt-empty{margin:0;padding:10px 12px;border:1px dashed rgba(230,194,122,.35);border-radius:10px;color:#c8c4bc;font-size:12px}`;
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
  let body;
  if(!D){
    body=`<p class="evt-empty">Les données des événements n’ont pas pu être chargées. Aucun chiffre n’est inventé.</p>`;
  }else{
    const evs=D.evenements.slice().sort((a,b)=>(a.rang||9)-(b.rang||9)).slice(0,3);
    const meth=(D.methode||[]).map(m=>`<li>${evtEsc(m)}</li>`).join('');
    const ec=(D.ecartes||[]).map(x=>`<p class="evt-ecart"><b>${evtEsc(x.sujet)}</b> : ${evtEsc(x.raison)}${x.url?` <a href="${evtUrl(x.url)}" target="_blank" rel="noopener noreferrer">source ↗</a>`:''}</p>`).join('');
    body=`<p class="evt-maj">Mise à jour : ${evtEsc(D.maj_label||D.maj||'—')} · horizon ${evtEsc(D.horizon||'—')}</p>
      <p class="evt-warn">${evtEsc(D.avertissement||'Estimations à partir de signaux faibles, pas des prévisions ; aucun conseil d’achat ou de vente.')}</p>
      ${evs.map(evtCardHtml).join('')}
      ${ec?`<p class="evt-k">Signaux écartés cette fois</p>${ec}`:''}
      ${meth?`<p class="evt-k">Méthode</p><ul class="evt-meth">${meth}</ul>`:''}
      ${(D.limites||[]).length?`<p class="evt-k">Limites</p><ul class="evt-meth">${D.limites.map(x=>`<li>${evtEsc(x)}</li>`).join('')}</ul>`:''}`;
  }
  return `<section class="evt-wrap" id="evtSection">
    <div class="evt-h" role="button" tabindex="0" aria-expanded="false" aria-controls="evtBody">
      <span class="evt-chev" aria-hidden="true">▸</span>
      <h3>Détection d'événements SOUS-JACENTS non médiatisés</h3>
    </div>
    <div class="evt-body" id="evtBody">${body}</div>
  </section>`;
}
function evtSetOpen(sec,on){
  sec.classList.toggle('is-open',on);
  const h=sec.querySelector('.evt-h');
  if(h) h.setAttribute('aria-expanded',on?'true':'false');
  try{ localStorage.setItem(EVT_KEY,on?'1':'0'); }catch(e){}
}
function evtMount(){
  const host=document.getElementById('irBody');
  if(!host||document.getElementById('evtSection')) return;
  evtStyle();
  host.insertAdjacentHTML('beforeend',evtHtml());
  const sec=document.getElementById('evtSection');
  if(!sec) return;
  let saved=null;
  try{ saved=localStorage.getItem(EVT_KEY); }catch(e){}
  sec.classList.toggle('is-open',saved==='1');
  const h=sec.querySelector('.evt-h');
  if(h){
    h.setAttribute('aria-expanded',saved==='1'?'true':'false');
    const tog=e=>{ e.preventDefault(); e.stopPropagation(); evtSetOpen(sec,!sec.classList.contains('is-open')); };
    h.addEventListener('click',tog);
    h.addEventListener('keydown',e=>{ if(e.key==='Enter'||e.key===' ') tog(e); });
  }
}
function evtInit(){
  evtMount();
  /* INDICE ROTATION se re-rend (outerHTML) : on remonte la section à chaque fois */
  try{
    const obs=new MutationObserver(()=>{ if(document.getElementById('irBody')&&!document.getElementById('evtSection')) evtMount(); });
    obs.observe(document.body,{childList:true,subtree:true});
  }catch(e){}
}
