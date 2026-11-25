/* ===== Budget : frais OVN CFD et frais d'ordres, mensualisés ===== */
let bdgPrevTab=null;
let bdgHashLock=false;
function bdgEsc(s){
  return String(s==null?'':s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}
function bdgAmt(n,d){
  if(n==null||n==='') return '—';
  const v=Number(n);
  if(!Number.isFinite(v)) return '—';
  const sym=(typeof posSym==='function')?posSym(d):(d==='EUR'?'€':'$');
  return v.toLocaleString('fr-FR',{minimumFractionDigits:2,maximumFractionDigits:2})+'\u00a0'+sym;
}
function bdgPair(usd,eur){
  const a=bdgAmt(usd,'USD'), b=bdgAmt(eur,'EUR');
  if(a==='—'&&b==='—') return '—';
  if(a==='—') return b;
  if(b==='—') return a;
  return a+' / '+b;
}
function bdgDate(s){
  if(!s) return '';
  const m=String(s).match(/^(\d{4})-(\d{2})-(\d{2})/);
  return m? (m[3]+'/'+m[2]) : String(s);
}
function bdgData(){
  const b=(typeof POS!=='undefined'&&POS&&POS.budget)||(typeof POS_RV!=='undefined'&&POS_RV&&POS_RV.budget)||null;
  return b;
}
function bdgIsOpen(){ return document.body.classList.contains('bdg-on'); }
function bdgHashInfo(){
  const h=(location.hash||'').slice(1);
  return h==='budget'||h.indexOf('budget/')===0;
}
function bdgSetHash(on){
  if(bdgHashLock) return;
  bdgHashLock=true;
  try{
    if(on){
      if(!bdgHashInfo()){
        const cur=(location.hash||'').slice(1);
        if(cur&&cur!=='budget'&&cur!=='regles'&&cur.indexOf('regles')!==0) bdgPrevTab=cur;
        history.pushState(null,'',location.pathname+location.search+'#budget');
      }
    }else if(bdgHashInfo()){
      const back=(bdgPrevTab&&bdgPrevTab!=='budget'&&bdgPrevTab!=='regles')?bdgPrevTab:'accueil';
      history.replaceState(null,'',location.pathname+location.search+'#'+back);
    }
  }catch(e){
    if(on) location.hash='budget';
    else location.hash=bdgPrevTab||'accueil';
  }
  bdgHashLock=false;
}
function bdgSetOpen(on, opts){
  const fromHash=opts&&opts.fromHash;
  const page=document.getElementById('bdg-page');
  const btn=document.getElementById('bdgBtn');
  if(!page) return;
  document.body.classList.toggle('bdg-on',!!on);
  if(on){
    page.removeAttribute('hidden');
    page.setAttribute('aria-hidden','false');
    if(btn) btn.setAttribute('aria-expanded','true');
    if(typeof ttSetOpen==='function') ttSetOpen(false);
    if(typeof rgSetOpen==='function'&&typeof rgIsOpen==='function'&&rgIsOpen()) rgSetOpen(false,{fromHash:true});
    if(!fromHash) bdgSetHash(true);
  }else{
    page.setAttribute('hidden','');
    page.setAttribute('aria-hidden','true');
    if(btn) btn.setAttribute('aria-expanded','false');
    if(!fromHash) bdgSetHash(false);
  }
}
function bdgOvnHTML(b){
  const o=b&&b.ovn||{};
  const lignes=o.lignes_mois||o.jours||[];
  const rows=lignes.length
    ? lignes.map(j=>{
        const usd=j.montant_usd!=null?Math.abs(Number(j.montant_usd)):null;
        const eur=(usd!=null&&b.fx)?usd/Number(b.fx):null;
        const when=bdgDate(j.date)+(j.heure?(' · '+j.heure):'');
        return `<li class="bdg-row"><span>${bdgEsc(when||'jour')} — ${bdgEsc(j.libelle||'Frais overnight CFD')}</span><b>${bdgPair(usd,eur)}</b></li>`;
      }).join('')
    : `<li class="bdg-empty">Aucun OVN relu ce mois-ci.</li>`;
  const fraisBox=(typeof posFraisCfdHTML==='function')?posFraisCfdHTML():'';
  return `<section class="bdg-sec" id="bdg-ovn">
    <h2>Frais OVN <small>overnight CFD</small></h2>
    <ul class="bdg-list">${rows}</ul>
    <div class="bdg-tot"><span>Total du mois${b.mois_libelle?(' ('+bdgEsc(b.mois_libelle)+')'):''}</span><b>${bdgPair(o.total_mois_usd,o.total_mois_eur)}</b></div>
    <div class="bdg-tot"><span>Projection mensuelle</span><b>${bdgPair(o.projection_usd,o.projection_eur)}</b></div>
    ${fraisBox}
  </section>`;
}
function bdgTradingHTML(b){
  const t=b&&b.trading||{};
  const lignes=t.lignes_mois||t.ordres||[];
  let rows;
  if(t.a_relever||!lignes.length){
    const tip=t.recherche_repo&&t.recherche_repo.resultat?t.recherche_repo.resultat:'Aucun frais d’ordre sourcé dans le dépôt.';
    rows=`<li class="bdg-empty" title="${bdgEsc(tip)}">à relever</li>`;
  }else{
    rows=lignes.map(o=>{
      const when=bdgDate(o.date)+(o.heure?(' · '+o.heure):'');
      const act=[o.actif||o.ticker||'', o.courtier||'', o.type||''].filter(Boolean).join(' · ');
      return `<li class="bdg-row"><span>${bdgEsc(when)} — ${bdgEsc(act||'Ordre')}</span><b>${bdgPair(o.montant_usd,o.montant_eur)}</b></li>`;
    }).join('');
  }
  const proj=t.a_relever||t.projection_note==='à relever'
    ? 'à relever'
    : bdgPair(t.projection_usd,t.projection_eur);
  const tot=t.a_relever?'à relever':bdgPair(t.total_mois_usd,t.total_mois_eur);
  return `<section class="bdg-sec" id="bdg-trading">
    <h2>Frais trading <small>commissions, change, exécution</small></h2>
    <ul class="bdg-list">${rows}</ul>
    <div class="bdg-tot"><span>Total du mois${b.mois_libelle?(' ('+bdgEsc(b.mois_libelle)+')'):''}</span><b>${tot}</b></div>
    <div class="bdg-tot"><span>Projection mensuelle</span><b>${proj}</b></div>
    <p class="bdg-note">Fichier à compléter : data/revolut/frais_trading_ordres.json. Aucun montant n’est inventé.</p>
  </section>`;
}
function bdgPageHTML(){
  const b=bdgData()||{};
  const mois=b.mois_libelle||'mois en cours';
  return `<div class="rg-top">
      <button type="button" id="bdgBack" class="rg-back">← Retour</button>
      <h1 id="bdgPageTitle">Budget</h1>
      <button type="button" id="bdgClose" class="rg-close">Fermer</button>
    </div>
    <div class="rg-page-body">
      <div class="bdg-main">
        <p class="bdg-lead">Frais mensualisés — ${bdgEsc(mois)}. Montants en $ et en € (taux ${b.fx!=null?String(b.fx).replace('.',','):'—'}).</p>
        ${bdgOvnHTML(b)}
        ${bdgTradingHTML(b)}
        <section class="bdg-sec bdg-sec-tot" id="bdg-general">
          <h2>Total général des frais</h2>
          <div class="bdg-tot"><span>Observé ce mois</span><b>${bdgPair(b.total_observe_usd,b.total_observe_eur)}</b></div>
          <div class="bdg-tot"><span>Projection mensuelle</span><b>${bdgPair(b.projection_usd,b.projection_eur)}</b></div>
          ${b.projection_note?`<p class="bdg-note">${bdgEsc(b.projection_note)}</p>`:''}
        </section>
      </div>
    </div>`;
}
function bdgRender(){
  let wrap=document.getElementById('bdg-wrap');
  if(!wrap){
    const tools=document.getElementById('hh-tools');
    const rg=document.getElementById('rg-wrap');
    wrap=document.createElement('div');
    wrap.id='bdg-wrap';
    if(rg&&rg.parentNode) rg.parentNode.insertBefore(wrap, rg.nextSibling);
    else if(tools) tools.insertBefore(wrap, tools.firstChild);
    else document.body.appendChild(wrap);
  }
  wrap.innerHTML=`<button type="button" id="bdgBtn" class="rg-btn" aria-expanded="false" aria-controls="bdg-page">Budget</button>`;
  let page=document.getElementById('bdg-page');
  if(!page){
    page=document.createElement('div');
    page.id='bdg-page';
    page.setAttribute('hidden','');
    page.setAttribute('role','dialog');
    page.setAttribute('aria-modal','true');
    page.setAttribute('aria-hidden','true');
    page.setAttribute('aria-labelledby','bdgPageTitle');
    document.body.appendChild(page);
  }
  page.innerHTML=bdgPageHTML();
  const btn=document.getElementById('bdgBtn');
  if(btn) btn.addEventListener('click',e=>{e.preventDefault();e.stopPropagation();bdgSetOpen(!bdgIsOpen());});
  const close=()=>{bdgSetOpen(false);};
  const b1=document.getElementById('bdgBack');
  const b2=document.getElementById('bdgClose');
  if(b1) b1.addEventListener('click',e=>{e.preventDefault();close();});
  if(b2) b2.addEventListener('click',e=>{e.preventDefault();close();});
}
function bdgInit(){
  bdgRender();
  if(document.documentElement._bdgDocBound){
    if(bdgHashInfo()) bdgSetOpen(true,{fromHash:true});
    return;
  }
  document.documentElement._bdgDocBound=true;
  document.addEventListener('keydown',e=>{
    if(e.key==='Escape'&&bdgIsOpen()) bdgSetOpen(false);
  });
  if(bdgHashInfo()) bdgSetOpen(true,{fromHash:true});
}
