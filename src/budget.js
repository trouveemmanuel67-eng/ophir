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
function bdgFx(b){
  if(!b||b.fx==null||b.fx==='') return '';
  return String(b.fx).replace('.', ',');
}
function bdgWhen(rec){
  if(!rec) return '';
  const d=String(rec.date||'');
  const m=d.match(/^(\d{4})-(\d{2})-(\d{2})/);
  const day=m?(m[3]+'/'+m[2]+'/'+m[1]):d;
  let h=String(rec.heure||'');
  if(h){
    const hm=h.match(/^(\d{1,2}):(\d{2})/);
    h=hm?(hm[1].padStart(2,'0')+' h '+hm[2]):h;
  }
  const z=rec.zone||'Europe/Paris';
  return (day+(h?(' à '+h):'')+(z?(' ('+z+')'):'')).trim();
}
function bdgOvnOf(b){
  return (b&&b.ovn)||(typeof POS!=='undefined'&&POS&&POS.frais_cfd)||{};
}
function bdgOvnOver(o){
  const mois=o.projection_eur;
  const obj=o.objectif_eur_mois!=null?o.objectif_eur_mois:20;
  return !!o.depasse_objectif||(mois!=null&&Number.isFinite(Number(mois))&&Number(mois)>Number(obj));
}
function bdgTd(s){ return `<td>${s}</td>`; }
function bdgTableHTML(b){
  const o=bdgOvnOf(b);
  const t=(b&&b.trading)||{};
  const jour=o.dernier_usd!=null?Number(o.dernier_usd):(o.jours&&o.jours.length&&o.jours[o.jours.length-1].montant_usd!=null?Math.abs(Number(o.jours[o.jours.length-1].montant_usd)):null);
  const obj=o.objectif_eur_mois!=null?o.objectif_eur_mois:20;
  const over=bdgOvnOver(o);
  const detail= (jour==null||!Number.isFinite(Number(jour)))?'—':(bdgAmt(jour,'USD')+'/j');
  const objTxt='&lt; '+String(obj).replace('.', ',')+'\u00a0€';
  const pending=!!(t.a_relever||t.projection_note==='à relever'||!(t.lignes_mois||t.ordres||[]).length);
  const trDet=pending?'à relever':'—';
  const trUsd=pending?'—':bdgAmt(t.total_mois_usd,'USD');
  const trEur=pending?'—':bdgAmt(t.total_mois_eur,'EUR');
  const trPusd=pending?'—':bdgAmt(t.projection_usd,'USD');
  const trPeur=pending?'—':bdgAmt(t.projection_eur,'EUR');
  const der=o.dernier||((o.jours&&o.jours.length)?o.jours[o.jours.length-1]:null);
  const when=bdgWhen(der);
  const fx=bdgFx(b);
  const srcParts=[];
  if(when) srcParts.push('OVN relu le '+when);
  if(fx) srcParts.push('change '+fx);
  const src=srcParts.length?('Source : '+srcParts.join(' · ')+'.'):'';
  return `<div class="bdg-table-wrap">
    <table class="bdg-table" id="bdg-table">
      <thead>
        <tr>
          <th>Poste</th>
          <th>Détail</th>
          <th>Observé ce mois $</th>
          <th>€</th>
          <th>Projection mensuelle $</th>
          <th>€</th>
          <th>Objectif</th>
        </tr>
      </thead>
      <tbody>
        <tr id="bdg-ovn" class="${over?'is-over':'is-ok'}">
          <td>OVN</td>
          ${bdgTd(detail)}
          ${bdgTd(bdgAmt(o.total_mois_usd,'USD'))}
          ${bdgTd(bdgAmt(o.total_mois_eur,'EUR'))}
          ${bdgTd(bdgAmt(o.projection_usd,'USD'))}
          ${bdgTd(bdgAmt(o.projection_eur,'EUR'))}
          ${bdgTd(objTxt)}
        </tr>
        <tr id="bdg-trading">
          <td>Frais trading</td>
          ${bdgTd(trDet)}
          ${bdgTd(trUsd)}
          ${bdgTd(trEur)}
          ${bdgTd(trPusd)}
          ${bdgTd(trPeur)}
          <td>—</td>
        </tr>
      </tbody>
      <tfoot>
        <tr id="bdg-general">
          <td>Total général</td>
          <td></td>
          ${bdgTd(bdgAmt(b.total_observe_usd,'USD'))}
          ${bdgTd(bdgAmt(b.total_observe_eur,'EUR'))}
          ${bdgTd(bdgAmt(b.projection_usd,'USD'))}
          ${bdgTd(bdgAmt(b.projection_eur,'EUR'))}
          <td>—</td>
        </tr>
      </tfoot>
    </table>
  </div>
  ${src?`<p class="bdg-src">${bdgEsc(src)}</p>`:''}`;
}
function bdgPageHTML(){
  const b=bdgData()||{};
  const mois=b.mois_libelle||'';
  const title=mois?('Budget — '+mois):'Budget';
  return `<div class="rg-top">
      <button type="button" id="bdgBack" class="rg-back">← Retour</button>
      <h1 id="bdgPageTitle">${bdgEsc(title)}</h1>
      <button type="button" id="bdgClose" class="rg-close">Fermer</button>
    </div>
    <div class="rg-page-body">
      <div class="bdg-main">
        ${bdgTableHTML(b)}
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
