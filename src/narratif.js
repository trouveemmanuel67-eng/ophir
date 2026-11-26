/* ===== NARRATIF : récits médiatiques à contre-courant (rail, juste au-dessus d'ÉVÈNEMENT) ===== */
const NAR_KEY='apex-nar-open';
function narData(){
  try{
    const el=document.getElementById('dataNarratif');
    if(!el) return null;
    const j=JSON.parse(el.textContent||'null');
    return j&&Array.isArray(j.narratifs)?j:null;
  }catch(e){ return null; }
}
function narEsc(s){
  return String(s==null?'':s).replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
}
function narUrl(u){
  const s=String(u||'');
  return /^https?:\/\//i.test(s)?narEsc(s):'#';
}
function narHost(u){
  try{ return new URL(u).hostname.replace(/^www\./,''); }catch(e){ return ''; }
}
function narParseDay(s){
  const m=String(s||'').match(/^(\d{4})-(\d{2})-(\d{2})/);
  if(!m) return null;
  return new Date(Number(m[1]), Number(m[2])-1, Number(m[3]));
}
function narFmtDM(d){
  if(!d) return '';
  const dd=String(d.getDate()).padStart(2,'0');
  const mm=String(d.getMonth()+1).padStart(2,'0');
  return dd+'/'+mm;
}
function narToday(){
  const n=new Date();
  return new Date(n.getFullYear(), n.getMonth(), n.getDate());
}
function narActeurNom(D, id){
  const a=(D&&D.acteurs||[]).find(x=>x.id===id);
  return a?a.nom:id;
}
function narProchain(D){
  if(!D||!Array.isArray(D.narratifs)) return null;
  const today=narToday();
  const cands=[];
  D.narratifs.forEach(n=>{
    const d=narParseDay(n.arrivee_debut);
    if(!d) return;
    cands.push({debut:d, label:n.titre, id:n.id, passe:d<today});
  });
  cands.sort((a,b)=>{
    const ao=a.passe?1:0, bo=b.passe?1:0;
    if(ao!==bo) return ao-bo;
    return a.debut-b.debut;
  });
  return cands[0]||null;
}
function narFmtDate(date){
  const s=String(date||'');
  if(/^\d{4}-\d{2}-\d{2}$/.test(s)) return s.slice(8,10)+'/'+s.slice(5,7)+'/'+s.slice(0,4);
  if(/^\d{4}-\d{2}$/.test(s)) return s.slice(5,7)+'/'+s.slice(0,4);
  return s;
}
function narSourcesHtml(arr){
  const list=(arr||[]).map(s=>{
    const src=s.source||s;
    const nom=src.nom||narHost(src.url)||'source';
    const date=narFmtDate(s.date||src.date||'');
    const texte=s.texte||s.fait||'';
    return `<li>${date?`<span class="nar-d">${narEsc(date)}</span> `:''}${texte?narEsc(texte)+' ':''}<a href="${narUrl(src.url)}" target="_blank" rel="noopener noreferrer">${narEsc(nom)} ↗</a></li>`;
  }).join('');
  return list?`<ul class="nar-ul nar-src">${list}</ul>`:'';
}
function narCardHtml(n, D){
  const id=narEsc(n.id);
  const typ=n.type==='Bulle-euphorie'?'euph':'peur';
  const typLab=n.type==='Bulle-euphorie'?'Bulle':'Peur';
  const acteurs=(n.acteurs||[]).map(a=>narActeurNom(D,a)).filter(Boolean);
  const secteurs=(n.secteurs||[]).join(' · ');
  const detail=`<div class="nar-det-in">
      ${secteurs?`<p class="nar-k">Secteurs</p><p class="nar-t">${narEsc(secteurs)}${n.actifs&&n.actifs.length?' · '+narEsc(n.actifs.join(', ')):''}</p>`:''}
      ${n.risque?`<p class="nar-k">Risque</p><p class="nar-t">${narEsc(n.risque)}</p>`:''}
      ${acteurs.length?`<p class="nar-k">Acteurs liés</p><p class="nar-t">${narEsc(acteurs.join(' · '))}</p>`:''}
      <p class="nar-k">Signaux d’avance</p>
      ${narSourcesHtml(n.signaux)}
    </div>`;
  return `<article class="nar-card" id="nar-${id}">
    <div class="nar-top">
      <span class="nar-badge nar-${typ}">${narEsc(typLab)}</span>
      <span class="nar-stade">${narEsc(n.stade||'—')}</span>
    </div>
    <p class="nar-titre">${narEsc(n.titre)}</p>
    <p class="nar-when">Arrivée estimée : ${narEsc(n.arrivee_estimee||'—')}</p>
    ${n.lecture?`<p class="nar-lec">${narEsc(n.lecture)}</p>`:''}
    <details class="nar-det"><summary>Voir le détail</summary>${detail}</details>
  </article>`;
}
function narActeurHtml(a){
  const ex=(a.exemples||[]).map(e=>{
    const src=e.source||{};
    return `<li><strong>${narEsc(e.titre||'')}</strong>${e.date?` <span class="nar-d">(${narEsc(e.date)})</span>`:''}<p class="nar-t">${narEsc(e.fait||'')}</p>${src.url?`<a href="${narUrl(src.url)}" target="_blank" rel="noopener noreferrer">${narEsc(src.nom||narHost(src.url)||'source')} ↗</a>`:''}</li>`;
  }).join('');
  const al=(a.signaux_alerte||[]).map(s=>`<li>${narEsc(s)}</li>`).join('');
  return `<article class="nar-card nar-act" id="nar-act-${narEsc(a.id)}">
    <p class="nar-titre">${narEsc(a.nom)}</p>
    <p class="nar-when">${narEsc(a.categorie||'')}</p>
    ${a.resume?`<p class="nar-lec">${narEsc(a.resume)}</p>`:''}
    <details class="nar-det"><summary>Voir le détail</summary>
      <div class="nar-det-in">
        ${al?`<p class="nar-k">Signaux d’alerte précoces</p><ul class="nar-ul">${al}</ul>`:''}
        ${ex?`<p class="nar-k">Exemples passés documentés</p><ul class="nar-ul nar-ex">${ex}</ul>`:''}
      </div>
    </details>
  </article>`;
}
function narStyle(){
  if(document.getElementById('narStyle')) return;
  const css=`
.nar-body{margin-top:6px;overflow-x:hidden}
.nar-maj{font-size:11px;color:var(--mut,#bababa);margin:0 0 8px}
.nar-disc{font-size:10.5px;color:var(--mut,#9a9a9a);font-weight:500}
.nar-intro{font-size:12px;line-height:1.35;color:#d8d0c8;margin:0 0 8px}
.nar-sec{font-size:11px;font-weight:750;letter-spacing:.06em;text-transform:uppercase;color:var(--acc2,#e6c27a);margin:12px 0 6px}
.nar-card{border:1px solid rgba(255,255,255,.14);border-radius:10px;padding:8px 10px;margin:0 0 8px;background:rgba(255,255,255,.03);overflow-x:hidden}
.nar-top{display:flex;align-items:center;gap:6px;flex-wrap:wrap;margin:0 0 4px}
.nar-badge{display:inline-block;padding:1px 7px;border-radius:999px;font-size:10px;font-weight:750;letter-spacing:.04em;text-transform:uppercase}
.nar-peur{background:rgba(248,113,113,.18);color:#f87171}
.nar-euph{background:rgba(230,194,122,.18);color:#e6c27a}
.nar-stade{font-size:10.5px;color:var(--mut,#bababa);letter-spacing:.02em}
.nar-titre{font-size:13.5px;font-weight:750;color:#fff;line-height:1.25;margin:0}
.nar-when{font-size:11px;color:#e6c27a;margin:3px 0 0;line-height:1.3}
.nar-lec{font-size:12px;line-height:1.35;color:#e8e8e8;margin:6px 0 0}
.nar-k{font-size:10px;font-weight:700;letter-spacing:.06em;text-transform:uppercase;color:var(--mut,#bababa);margin:8px 0 3px}
.nar-t{font-size:11.5px;line-height:1.4;color:#d8d8d8;margin:0 0 6px;overflow-wrap:anywhere;word-break:break-word}
.nar-ul{margin:0;padding-left:16px}
.nar-ul li{font-size:11.5px;line-height:1.4;color:#d8d8d8;margin:0 0 6px;overflow-wrap:anywhere;word-break:break-word}
.nar-ul a,.nar-src a{color:var(--acc,#a9cdf5);text-decoration:none}
.nar-ul a:hover{text-decoration:underline}
.nar-d{color:var(--mut,#bababa);font-variant-numeric:tabular-nums}
.nar-det{margin:6px 0 0}
.nar-det>summary{cursor:pointer;color:#7fb3e0;font-size:11.5px;font-weight:650;list-style:none}
.nar-det>summary::-webkit-details-marker{display:none}
.nar-det>summary::before{content:"▸ ";color:var(--mut,#bababa)}
.nar-det[open]>summary::before{content:"▾ "}
.nar-det-in{margin-top:4px}
.nar-ex strong{color:#fff;font-weight:700}
.nar-next{font-weight:650;letter-spacing:.04em}
#narCard h2{white-space:normal;line-height:1.3}
#mes-pos:not(.is-expanded) #narCard.pos-collapsed .nar-next-full{display:none}
#mes-pos:not(.is-expanded) #narCard.pos-collapsed h2{white-space:nowrap}
`;
  const st=document.createElement('style');
  st.id='narStyle';
  st.textContent=css;
  document.head.appendChild(st);
}
function narHtml(){
  const D=narData();
  let body, n=0, na=0;
  if(!D){
    body=`<p class="nar-empty">Les données des narratifs n’ont pas pu être chargées. Aucun chiffre n’est inventé.</p>`;
  }else{
    const evs=D.narratifs.slice();
    const acts=D.acteurs||[];
    n=evs.length; na=acts.length;
    body=`<p class="nar-maj">Mise à jour : ${narEsc(D.maj_label||D.maj||'—')} · <span class="nar-disc">Estimations, pas des conseils</span></p>
      <p class="nar-intro">Récits de peur ou d’euphorie qui peuvent passer dans les grands médias dans les 2 à 6 semaines. Lecture à contre-courant.</p>
      ${evs.map(e=>narCardHtml(e,D)).join('')}
      <h3 class="nar-sec">Qui lance les narratifs</h3>
      <p class="nar-intro">Repérer les cercles et médias qui poussent souvent un récit, et s’ils ont un intérêt déclaré. Faits sourcés seulement.</p>
      ${acts.map(narActeurHtml).join('')}`;
  }
  const nx=D?narProchain(D):null;
  const nxTxt=nx?(` · <span class="nar-next">prochain : ${narEsc(narFmtDM(nx.debut))} <span class="nar-next-full">${narEsc(nx.label)}</span></span>`):'';
  return `<div class="card no-group" id="narCard">
    <div class="pos-rail-h" role="button" tabindex="0" aria-expanded="false" aria-controls="narBody">
      <span class="pos-chev" aria-hidden="true">▸</span>
      <h2>NARRATIF${nxTxt}</h2>
      <span class="pos-head-tot">${n}<small>récit${n>1?'s':''}</small></span>
    </div>
    <div class="pos-body gi-body nar-body" id="narBody">${body}</div>
  </div>`;
}
function narListIsOpen(){
  const c=document.getElementById('narCard');
  return !!(c&&!c.classList.contains('pos-collapsed'));
}
function narSetListOpen(on,persist){
  const c=document.getElementById('narCard');
  if(!c) return;
  c.classList.toggle('pos-collapsed',!on);
  const head=c.querySelector('.pos-rail-h');
  if(head) head.setAttribute('aria-expanded', on?'true':'false');
  if(persist!==false){ try{ localStorage.setItem(NAR_KEY, on?'1':'0'); }catch(e){} }
  if(typeof posSyncListChrome==='function') posSyncListChrome(typeof posListIsOpen==='function'&&posListIsOpen());
}
function narWantedByHash(){
  const h=(location.hash||'').replace(/^#/,'').split('/')[0];
  return h==='narratif'||h==='nar';
}
function narMount(){
  const host=document.getElementById('mes-pos');
  if(!host) return;
  narStyle();
  const html=narHtml();
  const prev=document.getElementById('narCard');
  const evt=document.getElementById('evtCard');
  const ir=document.getElementById('indiceRotationCard');
  const gs=document.getElementById('bestShortCard');
  if(prev) prev.outerHTML=html;
  else if(evt) evt.insertAdjacentHTML('beforebegin', html);
  else if(ir) ir.insertAdjacentHTML('afterend', html);
  else if(gs) gs.insertAdjacentHTML('afterend', html);
  else host.insertAdjacentHTML('beforeend', html);
  const card=document.getElementById('narCard');
  if(!card) return;
  let saved=null;
  try{ saved=localStorage.getItem(NAR_KEY); }catch(e){}
  const open=narWantedByHash()||saved==='1';
  card.classList.toggle('pos-collapsed', !open);
  const head=card.querySelector('.pos-rail-h');
  if(head){
    head.setAttribute('aria-expanded', open?'true':'false');
    const tog=e=>{ e.preventDefault(); narSetListOpen(!narListIsOpen()); };
    head.addEventListener('click',e=>{ if(e.target.closest('a,details,button,input')) return; tog(e); });
    head.addEventListener('keydown',e=>{ if(e.target.closest('a,details,button,input')) return; if(e.key==='Enter'||e.key===' '){ e.preventDefault(); tog(e); } });
  }
  if(typeof posSyncListChrome==='function') posSyncListChrome(typeof posListIsOpen==='function'&&posListIsOpen());
  if(narWantedByHash()){
    narSetListOpen(true);
    try{ card.scrollIntoView({block:'nearest', behavior:'smooth'}); }catch(e){}
  }
}
function narOnHash(){
  if(narWantedByHash()){
    narSetListOpen(true);
    const card=document.getElementById('narCard');
    if(card){ try{ card.scrollIntoView({block:'nearest', behavior:'smooth'}); }catch(e){} }
  }
}
function narInit(){
  narMount();
  if(!document.documentElement._narHashBound){
    document.documentElement._narHashBound=true;
    window.addEventListener('hashchange', narOnHash);
  }
}
