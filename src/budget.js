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
function bdgTvOf(b){ return (b&&b.tradingview)||{}; }
function bdgTvObjectif(tv){
  const o=tv.objectif||{};
  if(!o||!o.libelle) return '—';
  if(o.atteint){
    const d=String(o.date_atteint||'');
    const m=d.match(/^(\d{4})-(\d{2})-(\d{2})/);
    const jour=m?(m[3]+'/'+m[2]):d;
    const ecoM=o.economie_eur_mois!=null?bdgAmt(o.economie_eur_mois,'EUR')+'/mois':'';
    const ecoA=o.economie_eur_an!=null?bdgAmt(o.economie_eur_an,'EUR')+'/an':'';
    const eco=[ecoM,ecoA].filter(Boolean).join(' · ');
    return '✓ Objectif atteint'+(jour?(' '+jour):'')+' — '+bdgEsc(o.libelle)+(eco?(' (économie '+eco+' vs Premium)'):'');
  }
  return bdgEsc(o.libelle);
}
function bdgDateShort(s){
  const m=String(s||'').match(/^(\d{4})-(\d{2})-(\d{2})/);
  return m?(String(Number(m[3]))+'/'+m[2]):(s||'');
}
function bdgJoint(b){ return (b&&b.compte_joint)||null; }
function bdgOpLine(o){
  const sens=o.sens==='credit'?'+':'';
  const when=bdgDateShort(o.date);
  const amt=bdgAmt(o.montant_eur,'EUR');
  const fx=o.devise_origine&&o.devise_origine.montant!=null?(' · '+bdgAmt(o.devise_origine.montant,o.devise_origine.devise==='USD'?'USD':'EUR').replace('\u00a0$',' $')):'';
  const src=o.compte_libelle||'';
  const srcHtml=src?`<span class="bdg-op-src">${bdgEsc(src)}</span>`:'';
  return `<li><span class="bdg-op-d">${bdgEsc(when)}</span><span class="bdg-op-l">${bdgEsc(o.libelle||'')}${srcHtml}</span><span class="bdg-op-m">${sens}${amt}</span></li>`;
}
function bdgOpsDetails(ops, summary, extra){
  const list=(ops&&ops.length)?(`<ul class="bdg-op-list">${ops.map(bdgOpLine).join('')}</ul>`):'<p class="desc">Aucune opération.</p>';
  return `<details class="bdg-ops"><summary>${bdgEsc(summary)}</summary>${list}${extra||''}</details>`;
}
function bdgRow(opts){
  const id=opts.id?` id="${opts.id}"`:'';
  const cls=['card','bdg-row'].concat(opts.cls||[]).join(' ');
  const det=opts.detailsHtml||`<div class="bdg-det">${opts.detail||'—'}</div>`;
  const obj=opts.objectif==null||opts.objectif===''?'—':opts.objectif;
  return `<div class="${cls}"${id}>
    <div class="bdg-poste"><h2>${opts.poste}</h2></div>
    <div class="bdg-detail bdg-wrap">${det}</div>
    <div class="bdg-num">${opts.obsUsd||'—'}</div>
    <div class="bdg-num">${opts.obsEur||'—'}</div>
    <div class="bdg-num">${opts.projUsd||'—'}</div>
    <div class="bdg-num">${opts.projEur||'—'}</div>
    <div class="bdg-obj">${obj}</div>
  </div>`;
}
function bdgHead(){
  return `<div class="home-table-h bdg-th" aria-hidden="true">
    <span>Poste</span><span>Détail</span><span>Observé ce mois $</span><span>€</span><span>Projection mensuelle $</span><span>€</span><span>Objectif</span>
  </div>`;
}
function bdgFoldKey(id){
  return 'apex-bdg-fold-'+id;
}
function bdgFoldGet(id, defOpen){
  try{
    const v=localStorage.getItem(bdgFoldKey(id));
    if(v==='0') return false;
    if(v==='1') return true;
  }catch(e){}
  return defOpen!==false;
}
function bdgFoldSet(id, open){
  try{ localStorage.setItem(bdgFoldKey(id), open?'1':'0'); }catch(e){}
}
function bdgFoldApply(root, open){
  if(!root) return;
  root.classList.toggle('is-folded', !open);
  const btn=root.querySelector(':scope > .home-hero-top .bdg-fold-btn, :scope > .bdg-fold-btn');
  const found=btn||root.querySelector('.bdg-fold-btn');
  if(found){
    found.setAttribute('aria-expanded', open?'true':'false');
    const arr=found.querySelector('.bdg-fold-arr');
    if(arr) arr.textContent=open?'\u25be':'\u25b8';
  }
}
function bdgFoldTitle(id, label, bodyId){
  return `<button type="button" class="bdg-fold-btn" aria-expanded="true" aria-controls="${bodyId}">`
    +`<span class="bdg-fold-arr" aria-hidden="true">\u25be</span> ${bdgEsc(label)}`
    +`</button>`;
}
function bdgBindFolds(scope){
  (scope||document).querySelectorAll('[data-bdg-fold]').forEach(el=>{
    const id=el.getAttribute('data-bdg-fold');
    if(!id) return;
    const def=el.getAttribute('data-bdg-fold-default')!=='closed';
    bdgFoldApply(el, bdgFoldGet(id, def));
    const btn=el.querySelector('.bdg-fold-btn');
    if(!btn || btn.dataset.bdgFoldBound) return;
    btn.dataset.bdgFoldBound='1';
    btn.addEventListener('click',e=>{
      e.preventDefault();
      e.stopPropagation();
      const open=el.classList.contains('is-folded');
      bdgFoldSet(id, open);
      bdgFoldApply(el, open);
    });
  });
}
function bdgOctOf(b){ return (b&&b.frais_octobre)||null; }
function bdgDateGmt(o){
  const d=bdgDate(o&&o.date);
  const h=o&&o.heure_gmt?String(o.heure_gmt).slice(0,5):'';
  return (d+(h?(' '+h):'')).trim();
}
function bdgFeeQty(n){
  if(n==null||n==='') return '';
  const v=Number(n);
  if(!Number.isFinite(v)) return String(n);
  const d=Math.abs(v-Math.round(v))<1e-9?0:(Math.abs(v*100-Math.round(v*100))<1e-9?2:8);
  return v.toLocaleString('fr-FR',{maximumFractionDigits:d,minimumFractionDigits:0});
}
function bdgFeeOpLine(o){
  const when=bdgDateGmt(o);
  const sym=o.symbole||'';
  const nom=o.nom&&o.nom!==sym?(' '+o.nom):'';
  const side=o.sens==='entree'?'achat':(o.sens==='sortie'?'vente':'');
  const typ=o.type==='overnight_fee'?'Overnight fee':(o.type==='trading_fee'?'trading fee':(o.type==='commission'?'commission':(o.type==='frais_reglementaire'?'frais (Fees)':(o.type==='Dividend'?'dividende':(o.type==='Bond coupon'?'coupon':(o.type||''))))));
  let mid='';
  if(o.quantite!=null&&o.prix!=null){
    const unit=(o.prix_devise==='EUR'?'EUR':'USD');
    mid=bdgFeeQty(o.quantite)+' @ '+bdgAmt(o.prix,unit);
    if(o.notionnel_usd!=null) mid+=' ('+bdgAmt(o.notionnel_usd,'USD')+')';
    else if(o.notionnel_eur!=null) mid+=' ('+bdgAmt(o.notionnel_eur,'EUR')+')';
  }
  const bits=[when,sym+nom,side,typ,mid].filter(Boolean).join(' · ');
  const amt=bdgPair(o.montant_usd,o.montant_eur);
  return `<li><span class="bdg-op-l">${bdgEsc(bits)}</span><span class="bdg-op-m">${amt}</span></li>`;
}
function bdgFeeOpsDetails(ops, summary, extra){
  const list=(ops&&ops.length)?(`<ul class="bdg-op-list">${ops.map(bdgFeeOpLine).join('')}</ul>`):'<p class="desc">Aucune opération.</p>';
  return `<details class="bdg-ops"><summary>${bdgEsc(summary)}</summary>${list}${extra||''}</details>`;
}
function bdgOctCatRow(c, opts){
  opts=opts||{};
  const absent=c.observe_usd==null&&c.observe_eur==null&&!(c.operations&&c.operations.length);
  const n=c.n_operations!=null?c.n_operations:((c.operations&&c.operations.length)||0);
  const sum=absent?(c.detail||'Aucun montant sur le relevé'):((n? (n+' opération'+(n>1?'s':'')):'')+(c.detail?((n?' · ':'')+c.detail):''));
  const det=absent?(`<div class="bdg-det">${bdgEsc(c.detail||'—')}</div>`):bdgFeeOpsDetails(c.operations||[], sum||'octobre 2026');
  const cls=opts.cls||((c.id==='ovn'&&c.depasse_objectif)?['is-over']:[]);
  const obj=opts.objectif!=null?opts.objectif:(c.objectif_eur!=null?('&lt; '+String(c.objectif_eur).replace('.', ',')+'\u00a0€'):'—');
  return bdgRow({id:opts.id||('bdg-oct-'+c.id),cls:cls,poste:c.poste||c.id,detailsHtml:det,obsUsd:absent?'—':bdgAmt(c.observe_usd,'USD'),obsEur:absent?'—':bdgAmt(c.observe_eur,'EUR'),projUsd:absent?'—':bdgAmt(c.projection_usd,'USD'),projEur:absent?'—':bdgAmt(c.projection_eur,'EUR'),objectif:obj});
}

function bdgCourtHtml(b){
  const o=bdgOvnOf(b);
  const t=(b&&b.trading)||{};
  const jour=o.dernier_usd!=null?Number(o.dernier_usd):(o.jours&&o.jours.length&&o.jours[o.jours.length-1].montant_usd!=null?Math.abs(Number(o.jours[o.jours.length-1].montant_usd)):null);
  const obj=o.objectif_eur_mois!=null?o.objectif_eur_mois:20;
  const over=bdgOvnOver(o);
  const detail=(jour==null||!Number.isFinite(Number(jour)))?'—':(bdgAmt(jour,'USD')+'/j');
  const objTxt='&lt; '+String(obj).replace('.', ',')+'\u00a0€';
  const pending=!!(t.a_relever||t.projection_note==='à relever'||!(t.lignes_mois||t.ordres||[]).length);
  const trDet=pending?'à relever':'—';
  const trDash=pending?'—':null;
  const tv=bdgTvOf(b);
  const tvOk=!!(tv.objectif&&tv.objectif.atteint);
  const tvDet=tv.detail||'—';
  const der=o.dernier||((o.jours&&o.jours.length)?o.jours[o.jours.length-1]:null);
  const when=bdgWhen(der);
  const fx=bdgFx(b);
  const srcParts=[];
  if(when) srcParts.push('OVN relu le '+when);
  if(tv&&tv.souscription&&tv.souscription.date){
    const h=tv.souscription.heure?String(tv.souscription.heure).replace(/^(\d{1,2}):(\d{2})/, (_,a,c)=>String(a).padStart(2,'0')+' h '+c):'';
    const dm=(String(tv.souscription.date).match(/^(\d{4})-(\d{2})-(\d{2})/)||[]);
    const whenTv=dm.length?(dm[3]+'/'+dm[2]+'/'+dm[1]):tv.souscription.date;
    srcParts.push('TradingView Essential annuel le '+(whenTv+(h?(' à '+h):''))+(tv.souscription.zone?(' ('+tv.souscription.zone+')'):''));
  }
  if(fx) srcParts.push('change '+fx);
  const fo=bdgOctOf(b);
  if(fo) srcParts.push('frais octobre 2026, relevés Revolut 56HF6NCA06C6 (pdftotext)');
  const src=srcParts.length?('Source : '+srcParts.join(' · ')+'.'):'';
  const mois=b.mois_libelle||'';
  const totOct=(fo&&fo.totaux)||{};
  const catsOct=(fo&&fo.categories)||[];
  const byOct={};
  catsOct.forEach(c=>{ if(c&&c.id) byOct[c.id]=c; });
  const fallbackTrading=bdgRow({id:'bdg-trading',poste:'Frais trading',detail:trDet,obsUsd:pending?'—':bdgAmt(t.total_mois_usd,'USD'),obsEur:pending?'—':bdgAmt(t.total_mois_eur,'EUR'),projUsd:pending?'—':bdgAmt(t.projection_usd,'USD'),projEur:pending?'—':bdgAmt(t.projection_eur,'EUR'),objectif:'—'});
  const octOrder=['entree','sortie','change','ovn','autres'];
  const OCT_POSTES={entree:'Entrée',sortie:'Sortie',change:'Change',ovn:'OVN octobre',autres:'Autres'};
  let octRows=fallbackTrading;
  if(fo){
    const rows=octOrder.map((id,i)=>{
      const c=Object.assign({id:id,poste:OCT_POSTES[id]||id,operations:[],observe_usd:null,observe_eur:null}, byOct[id]||{});
      if(!c.poste) c.poste=OCT_POSTES[id]||id;
      const opts={};
      if(id==='entree') opts.id='bdg-trading';
      if(id==='ovn'){ opts.cls=(c.depasse_objectif||(c.observe_eur!=null&&Number(c.observe_eur)>20))?['is-over']:[]; opts.objectif=objTxt; }
      return bdgOctCatRow(c, opts);
    });
    const totU=totOct.frais_usd, totE=totOct.frais_eur;
    const sans=fo.operations_sans_frais||[];
    const sansHtml=sans.length?bdgFeeOpsDetails(sans.map(s=>({
      date:s.date,heure_gmt:s.heure_gmt,symbole:s.symbole,nom:s.nom,sens:s.sens,type:s.type,quantite:s.quantite,prix:s.prix,prix_devise:s.devise_releve,notionnel_usd:s.notionnel_usd,notionnel_eur:s.notionnel_eur,montant_usd:0,montant_eur:0
    })), sans.length+' ordre'+(sans.length>1?'s':'')+' à commission et fees nuls'):'';
    rows.push(`<div class="bdg-foot" id="bdg-oct-total">
          <div class="bdg-poste"><h2>Total frais octobre</h2></div>
          <div class="bdg-detail bdg-wrap">${sansHtml||'<div class="bdg-det">Octobre 2026 · relevés actions/obligations et CFD</div>'}</div>
          <div class="bdg-num">${bdgAmt(totU,'USD')}</div>
          <div class="bdg-num">${bdgAmt(totE,'EUR')}</div>
          <div class="bdg-num">${bdgAmt(totU,'USD')}</div>
          <div class="bdg-num">${bdgAmt(totE,'EUR')}</div>
          <div class="bdg-obj">—</div>
        </div>`);
    const inc=fo.dividendes_et_coupons||{};
    const incOps=inc.operations||[];
    if(incOps.length){
      const note=inc.retenue_note||"Aucune retenue à la source n'apparaît sur le relevé.";
      rows.push(bdgRow({id:'bdg-oct-revenu',cls:['bdg-annexe'],poste:'Dividendes et coupons (oct.)',detailsHtml:bdgFeeOpsDetails(incOps, (incOps.length+' encaissement'+(incOps.length>1?'s':'')+' nets · '+note), ''),obsUsd:bdgAmt(inc.net_usd,'USD'),obsEur:bdgAmt(inc.net_eur,'EUR'),projUsd:bdgAmt(inc.net_usd,'USD'),projEur:bdgAmt(inc.net_eur,'EUR'),objectif:'—'}));
    }
    octRows=rows.join('\n        ');
  }
  const octKv=fo?`<div class="home-kv"><span class="l">Frais octobre</span><b>${bdgAmt(totOct.frais_eur,'EUR')}</b><small>${bdgAmt(totOct.frais_usd,'USD')}</small></div>`:'';
  return `<section class="card home-hero bdg-hero" id="bdg-courtage" data-bdg-fold="courtage">
    <div class="home-hero-top">
      <h2>${bdgFoldTitle('courtage','Frais de courtage et abonnements','bdg-courtage-body')}</h2>
      <p class="desc">${bdgEsc(mois?(mois+' · flux courants'):'Flux courants')}</p>
    </div>
    <div class="home-strip bdg-kvs bdg-fold-banner">
      <div class="home-kv"><span class="l">Total observé</span><b>${bdgAmt(b.total_observe_eur,'EUR')}</b><small>${bdgAmt(b.total_observe_usd,'USD')}</small></div>
      <div class="home-kv"><span class="l">Projection</span><b>${bdgAmt(b.projection_eur,'EUR')}</b><small>${bdgAmt(b.projection_usd,'USD')}</small></div>
      ${octKv}
    </div>
    <div class="bdg-fold-body" id="bdg-courtage-body">
    <div class="home-table-scroll">
      <div class="home-table bdg-table" id="bdg-table">
        ${bdgHead()}
        ${bdgRow({id:'bdg-ovn',cls:over?['is-over']:['is-ok'],poste:'OVN',detail:detail,obsUsd:bdgAmt(o.total_mois_usd,'USD'),obsEur:bdgAmt(o.total_mois_eur,'EUR'),projUsd:bdgAmt(o.projection_usd,'USD'),projEur:bdgAmt(o.projection_eur,'EUR'),objectif:objTxt})}
        ${octRows}
        ${bdgRow({id:'bdg-tv',cls:tvOk?['is-ok']:[],poste:'Abonnement TradingView',detailsHtml:`<div class="bdg-det">${bdgEsc(tvDet)}</div>`,obsUsd:bdgAmt(tv.total_mois_usd,'USD'),obsEur:bdgAmt(tv.total_mois_eur,'EUR'),projUsd:bdgAmt(tv.projection_usd,'USD'),projEur:bdgAmt(tv.projection_eur,'EUR'),objectif:bdgTvObjectif(tv)})}
        <div class="bdg-foot" id="bdg-general">
          <div class="bdg-poste"><h2>Total général</h2></div>
          <div class="bdg-detail"></div>
          <div class="bdg-num">${bdgAmt(b.total_observe_usd,'USD')}</div>
          <div class="bdg-num">${bdgAmt(b.total_observe_eur,'EUR')}</div>
          <div class="bdg-num">${bdgAmt(b.projection_usd,'USD')}</div>
          <div class="bdg-num">${bdgAmt(b.projection_eur,'EUR')}</div>
          <div class="bdg-obj">—</div>
        </div>
      </div>
    </div>
    ${src?`<p class="bdg-src">${bdgEsc(src)}</p>`:''}
    </div>
  </section>`;
}
function bdgLidlOf(c){
  const sous=(c&&c.sous_categories)||[];
  return sous.find(s=>s&&(s.id==='tickets_caisse'||s.id==='tickets_lidl')&&(s.mois||(s.enseignes&&s.enseignes.tous)))||null;
}
function bdgLidlPct(n){
  if(n==null||n==='') return '—';
  const v=Number(n);
  if(!Number.isFinite(v)) return '—';
  return v.toLocaleString('fr-FR',{minimumFractionDigits:1,maximumFractionDigits:1})+'\u00a0%';
}
function bdgTicketsEns(s, ens){
  if(!s) return null;
  if(s.enseignes&&s.enseignes[ens]&&s.enseignes[ens].mois) return s.enseignes[ens];
  if(ens==='tous'||ens==='lidl') return {id:ens, libelle:ens==='leclerc'?'E.Leclerc':(ens==='lidl'?'Lidl':'Tous'), mois:s.mois||{}};
  return {id:ens, libelle:'E.Leclerc', mois:{}};
}
function bdgTicketsPanel(s, ens){
  const pack=bdgTicketsEns(s, ens)||{mois:{}};
  const oct=pack.mois['2026-10']||{};
  const nov=pack.mois['2026-11']||{};
  const cats=oct.par_sous_categorie&&oct.par_sous_categorie.length?oct.par_sous_categorie:(nov.par_sous_categorie||[]);
  const rows=cats.map((o,i)=>{
    const n=(nov.par_sous_categorie||[]).find(x=>x.libelle===o.libelle)||(nov.par_sous_categorie||[])[i]||{};
    const empty=!(Number(o.eur)||Number(n.eur));
    const nc=!!(o.non_classe||o.libelle==='Non classé');
    return `<div class="bdg-lidl-row${empty?' is-empty':''}${o.alimentaire?'':' bdg-lidl-nonalim'}${nc?' bdg-lidl-nc':''}">
      <div class="bdg-lidl-lab">${bdgEsc(o.libelle)}</div>
      <div class="bdg-num">${bdgAmt(o.eur,'EUR')}</div>
      <div class="bdg-num">${bdgAmt(o.usd,'USD')}</div>
      <div class="bdg-num">${bdgLidlPct(o.pct)}</div>
      <div class="bdg-num">${bdgAmt(n.eur,'EUR')}</div>
      <div class="bdg-num">${bdgAmt(n.usd,'USD')}</div>
      <div class="bdg-num">${bdgLidlPct(n.pct)}</div>
    </div>`;
  }).join('');
  const foot=(lab,oa,na,cls='')=>`<div class="bdg-lidl-row bdg-lidl-foot ${cls}">
      <div class="bdg-lidl-lab">${bdgEsc(lab)}</div>
      <div class="bdg-num">${bdgAmt(oa.eur,'EUR')}</div>
      <div class="bdg-num">${bdgAmt(oa.usd,'USD')}</div>
      <div class="bdg-num">${bdgLidlPct(oa.pct)}</div>
      <div class="bdg-num">${bdgAmt(na.eur,'EUR')}</div>
      <div class="bdg-num">${bdgAmt(na.usd,'USD')}</div>
      <div class="bdg-num">${bdgLidlPct(na.pct)}</div>
    </div>`;
  const totLab=ens==='lidl'?'Total Lidl':(ens==='leclerc'?'Total E.Leclerc':'Total tickets');
  const totFoot=foot(totLab,{eur:oct.total_eur,usd:oct.total_usd,pct:oct.total_eur?100:0},{eur:nov.total_eur,usd:nov.total_usd,pct:nov.total_eur?100:0},'bdg-lidl-tot');
  const alimFoot=foot('Alimentaire',{eur:oct.alimentaire_eur,usd:oct.alimentaire_usd,pct:oct.alimentaire_pct},{eur:nov.alimentaire_eur,usd:nov.alimentaire_usd,pct:nov.alimentaire_pct});
  const nonFoot=foot('Non alimentaire',{eur:oct.non_alimentaire_eur,usd:oct.non_alimentaire_usd,pct:oct.non_alimentaire_pct},{eur:nov.non_alimentaire_eur,usd:nov.non_alimentaire_usd,pct:nov.non_alimentaire_pct});
  const ncNov=nov.non_classe_eur, ncOct=oct.non_classe_eur;
  const ncFoot=(Number(ncOct)||Number(ncNov))?foot('Non classé (écart de lecture)',{eur:ncOct||0,usd:oct.non_classe_usd,pct:oct.total_eur?((Number(ncOct)||0)/Number(oct.total_eur)*100):0},{eur:ncNov||0,usd:nov.non_classe_usd,pct:nov.total_eur?((Number(ncNov)||0)/Number(nov.total_eur)*100):0},'bdg-lidl-nc'):'';
  const trNovTxt=bdgAmt(nov.tr_eur,'EUR')+' · '+bdgLidlPct(nov.tr_pct)+(Number(nov.tr_a_confirmer_eur)?(' dont '+bdgAmt(nov.tr_a_confirmer_eur,'EUR')+' à confirmer'):'');
  const kv=(lab,octV,novV)=>`<div class="home-kv"><span class="l">${bdgEsc(lab)}</span><b>${octV}</b><small>oct</small><b>${novV}</b><small>nov</small></div>`;
  const kvs=`<div class="home-strip bdg-kvs bdg-lidl-kvs">
    ${kv('Alimentaire',bdgAmt(oct.alimentaire_eur,'EUR'),bdgAmt(nov.alimentaire_eur,'EUR'))}
    ${kv('Non alimentaire',bdgAmt(oct.non_alimentaire_eur,'EUR'),bdgAmt(nov.non_alimentaire_eur,'EUR'))}
    ${kv('Déco de Noël',bdgAmt(oct.deco_noel_eur,'EUR'),bdgAmt(nov.deco_noel_eur,'EUR'))}
    ${kv('Remises (économies)',bdgAmt(oct.remises_eur_abs,'EUR'),bdgAmt(nov.remises_eur_abs,'EUR'))}
    ${kv('Titres-restaurant',bdgAmt(oct.tr_eur,'EUR')+' · '+bdgLidlPct(oct.tr_pct),trNovTxt)}
    ${kv('Passages',String(oct.n_tickets||0),String(nov.n_tickets||0))}
    ${kv('Panier moyen',bdgAmt(oct.panier_moyen_eur,'EUR'),bdgAmt(nov.panier_moyen_eur,'EUR'))}
  </div>`;
  const ticketWhen=(t)=>{
    if(t.date_libelle) return t.date_libelle;
    return (t.date?bdgDate(t.date):'')+(t.heure?(' · '+t.heure.slice(0,5)):'');
  };
  const ticketMag=(t)=>{
    const ens=t.enseigne_libelle||(t.enseigne==='leclerc'?'E.Leclerc':(t.enseigne==='lidl'?'Lidl':''));
    const mag=t.magasin==='S'?'Schiltigheim':(t.magasin==='H'?'Hoenheim':(t.magasin_libelle||''));
    return [ens, mag].filter(Boolean).join(' · ')||'Ticket';
  };
  const ticketLine=(t)=>{
    const when=ticketWhen(t);
    const lab=ticketMag(t);
    const href=t.lien;
    const name=href?`<a href="${bdgEsc(href)}" target="_blank" rel="noopener">${bdgEsc(lab)}</a>`:bdgEsc(lab);
    const tr=Number(t.tr_eur)?(` · TR ${bdgAmt(t.tr_eur,'EUR')}${t.tr_a_confirmer?' à confirmer':''}`):'';
    return `<li><span class="bdg-op-d">${bdgEsc(when)}</span><span class="bdg-op-l">${name}${tr}</span><span class="bdg-op-m">${bdgAmt(t.a_payer_eur,'EUR')}</span></li>`;
  };
  const ticketList=(m,arr)=>`<details class="bdg-ops bdg-lidl-tickets"><summary>${bdgEsc(m.libelle||'')} · ${m.n_tickets||0} passage${(m.n_tickets||0)>1?'s':''} · ${bdgAmt(m.total_eur,'EUR')}</summary>
    <ul class="bdg-op-list">${(arr||[]).length?(arr||[]).map(ticketLine).join(''):'<li class="bdg-op-empty">Aucun ticket pour cette enseigne.</li>'}</ul>
  </details>`;
  return `${kvs}
    <div class="home-table-scroll">
      <div class="bdg-lidl-table">
        <div class="bdg-lidl-row bdg-lidl-th" aria-hidden="true">
          <div>Rayon</div>
          <div>Octobre €</div><div>$</div><div>%</div>
          <div>Novembre €</div><div>$</div><div>%</div>
        </div>
        ${rows}
        ${alimFoot}
        ${nonFoot}
        ${ncFoot}
        ${totFoot}
      </div>
    </div>
    <div class="bdg-lidl-lists">
      ${ticketList(oct,oct.tickets)}
      ${ticketList(nov,nov.tickets)}
    </div>`;
}
function bdgLidlBlock(c){
  const s=bdgLidlOf(c);
  if(!s) return '';
  const part=s.courses_releve_octobre||{};
  const note=s.note||part.note||'Les Courses du relevé incluent aussi d’autres enseignes.';
  const partLine=part.lidl_releve_eur!=null?(`Part Lidl d’octobre au relevé : ${bdgAmt(part.lidl_releve_eur,'EUR')} sur ${bdgAmt(part.observe_eur,'EUR')} de Courses (${bdgLidlPct(part.lidl_part_releve_pct)}), pour ${part.lidl_releve_n||'—'} paiements carte. Les tickets Lidl d’octobre totalisent ${bdgAmt(part.lidl_tickets_eur,'EUR')}.`):'';
  const filt=['tous','lidl','leclerc'].map(e=>{
    const lab=e==='tous'?'Tous':(e==='lidl'?'Lidl':'E.Leclerc');
    return `<button type="button" class="bdg-ens-btn${e==='tous'?' is-on':''}" data-ens="${e}" role="tab" aria-selected="${e==='tous'?'true':'false'}">${bdgEsc(lab)}</button>`;
  }).join('');
  const panels=['tous','lidl','leclerc'].map(e=>`<div class="bdg-ens-panel${e==='tous'?' is-on':''}" data-ens-panel="${e}">${bdgTicketsPanel(s,e)}</div>`).join('');
  return `<div class="bdg-sous bdg-lidl" id="bdg-courses-sous" data-bdg-fold="tickets">
    <div class="home-hero-top">
      <h3>${bdgFoldTitle('tickets', s.libelle||'Tickets de caisse — détail par rayons', 'bdg-tickets-body')}</h3>
      <p class="desc">Lidl (octobre et novembre au 24) et E.Leclerc (date inconnue, reçu le 25/11/2026) · change 1,0944 · objectif —</p>
    </div>
    <div class="bdg-fold-body" id="bdg-tickets-body">
      <div class="bdg-ens-filt" role="tablist" aria-label="Filtrer par enseigne">${filt}</div>
      ${panels}
      <p class="bdg-src">${bdgEsc(note)}${partLine?(' '+partLine):''}</p>
    </div>
  </div>`;
}
function bdgBindEnsFilt(scope){
  (scope||document).querySelectorAll('.bdg-lidl .bdg-ens-filt').forEach(bar=>{
    if(bar.dataset.bdgEnsBound) return;
    bar.dataset.bdgEnsBound='1';
    const root=bar.closest('.bdg-lidl');
    bar.querySelectorAll('.bdg-ens-btn').forEach(btn=>{
      btn.addEventListener('click',e=>{
        e.preventDefault();
        e.stopPropagation();
        const ens=btn.getAttribute('data-ens');
        bar.querySelectorAll('.bdg-ens-btn').forEach(b=>{
          const on=b===btn;
          b.classList.toggle('is-on', on);
          b.setAttribute('aria-selected', on?'true':'false');
        });
        (root||document).querySelectorAll('[data-ens-panel]').forEach(p=>{
          p.classList.toggle('is-on', p.getAttribute('data-ens-panel')===ens);
        });
      });
    });
  });
}
function bdgJointHtml(b){

  const j=bdgJoint(b);
  if(!j) return '';
  const tot=j.totaux||{};
  const per=(j.periode&&j.periode.libelle)||'octobre 2026';
  const fx=j.fx!=null?String(j.fx).replace('.', ','):(bdgFx(b)||'1,0944');
  const cats=j.categories||[];
  const rows=cats.filter(c=>c.id!=='air_glow_pub').map(c=>{
    const empty=!c.n_operations;
    const obsU=empty&&!(c.observe_eur)? '—' : bdgAmt(c.observe_usd,'USD');
    const obsE=empty&&!(c.observe_eur)? '—' : bdgAmt(c.observe_eur,'EUR');
    const zeroEmpty=empty && !(Number(c.observe_eur));
    let extra='';
    if(c.id==='courses'){
      extra='';
    }
    const sum=(c.detail||(c.n_operations? (c.n_operations+' opération'+(c.n_operations>1?'s':'')) : 'Aucune opération en octobre 2026.'));
    const det=empty?`<div class="bdg-det">${bdgEsc(c.detail||'Aucune opération en octobre 2026.')}</div>`:bdgOpsDetails(c.operations,sum,extra);
    const cls=['bdg-cat'];
    if(c.id==='courses') cls.push('bdg-cat-courses');
    if(c.id==='virements_internes') cls.push('bdg-cat-interne');
    if(c.id==='credit_revolut') cls.push('bdg-cat-fixe');
    if(c.id==='air_glow_pub') cls.push('bdg-cat-pro');
    if(zeroEmpty) cls.push('is-empty');
    const row=bdgRow({
      id:'bdg-cat-'+c.id,
      cls:cls,
      poste:c.poste||c.id,
      detailsHtml:det,
      obsUsd:zeroEmpty?'—':obsU,
      obsEur:zeroEmpty?'—':obsE,
      projUsd:zeroEmpty?'—':bdgAmt(c.projection_usd,'USD'),
      projEur:zeroEmpty?'—':bdgAmt(c.projection_eur,'EUR'),
      objectif:'—'
    });
    return c.id==='courses'? (row+bdgLidlBlock(c)) : row;
  }).join('');
  const resteNeg=Number(tot.reste_eur)<0;
  const depNote=tot.depenses_note||'Hors virements internes, épargne, investissement et dépenses pro Air Glow (pub)';
  const depRow=bdgRow({id:'bdg-joint-depenses',cls:['bdg-foot','bdg-tot-dep'],poste:'Total dépenses personnelles',detail:'Hors virements internes, épargne, investissement et Air Glow pub (pro)',obsUsd:bdgAmt(tot.depenses_usd,'USD'),obsEur:bdgAmt(tot.depenses_eur,'EUR'),projUsd:bdgAmt(tot.depenses_usd,'USD'),projEur:bdgAmt(tot.depenses_eur,'EUR'),objectif:'—'});
  const revDet=bdgOpsDetails(j.revenus_operations||[], tot.revenus_detail||'Revenus d’octobre');
  const revRow=bdgRow({id:'bdg-joint-revenus',cls:['bdg-foot','bdg-tot-rev'],poste:'Total revenus',detailsHtml:revDet,obsUsd:bdgAmt(tot.revenus_usd,'USD'),obsEur:bdgAmt(tot.revenus_eur,'EUR'),projUsd:bdgAmt(tot.revenus_usd,'USD'),projEur:bdgAmt(tot.revenus_eur,'EUR'),objectif:'—'});
  const resteRow=bdgRow({id:'bdg-joint-reste',cls:['bdg-foot','bdg-tot-reste',resteNeg?'is-over':'is-ok'],poste:'Reste (revenus − dépenses)',detail:tot.reste_formule||'Revenus − dépenses',obsUsd:bdgAmt(tot.reste_usd,'USD'),obsEur:bdgAmt(tot.reste_eur,'EUR'),projUsd:bdgAmt(tot.reste_usd,'USD'),projEur:bdgAmt(tot.reste_eur,'EUR'),objectif:'—'});
  const remb=j.remboursements_operations||[];
  const rembRow=remb.length?bdgRow({id:'bdg-joint-remb',cls:['bdg-annexe'],poste:'Remboursements (à part)',detailsHtml:bdgOpsDetails(remb, tot.remboursements_note||'Remboursements, non inclus dans les revenus'),obsUsd:bdgAmt(tot.remboursements_usd,'USD'),obsEur:bdgAmt(tot.remboursements_eur,'EUR'),projUsd:'—',projEur:'—',objectif:'—'}):'';
  const vin=j.virements_internes_entrants||[];
  const vinRow=bdgRow({id:'bdg-joint-vin',cls:['bdg-annexe','bdg-cat-interne'],poste:'Virements internes entrants',detailsHtml:bdgOpsDetails(vin, 'Alimentations du compte joint (non revenus) · '+((vin.length)||0)+' opération'+(vin.length>1?'s':'')),obsUsd:bdgAmt(tot.virements_internes_entrants_usd,'USD'),obsEur:bdgAmt(tot.virements_internes_entrants_eur,'EUR'),projUsd:'—',projEur:'—',objectif:'—'});
  const glow=cats.find(c=>c.id==='air_glow_pub');
  const glowRow=glow?bdgRow({id:'bdg-joint-airglow',cls:['bdg-foot','bdg-annexe','bdg-cat-pro'],poste:'Sous-total Air Glow, pub (pro)',detailsHtml:bdgOpsDetails(glow.operations||[], glow.detail||(tot.air_glow_pub_note||'Publicité Air Glow, exclue des dépenses personnelles')),obsUsd:bdgAmt(tot.air_glow_pub_usd!=null?tot.air_glow_pub_usd:glow.observe_usd,'USD'),obsEur:bdgAmt(tot.air_glow_pub_eur!=null?tot.air_glow_pub_eur:glow.observe_eur,'EUR'),projUsd:bdgAmt(glow.projection_usd,'USD'),projEur:bdgAmt(glow.projection_eur,'EUR'),objectif:'—' }):'';
  const tvFlag=j.tradingview_sur_le_releve||{};
  const tvNote=tvFlag.present_sur_le_releve?(tvFlag.note||'Un prélèvement TradingView figure sur le relevé ; non recopié en seconde ligne d’abonnement.'):'';
  const srcBits=[];
  const s=j.source||{};
  if(s.intitule) srcBits.push(s.intitule);
  if(s.periode_releve&&s.periode_releve.libelle) srcBits.push('période '+s.periode_releve.libelle);
  if(s.genere_le_libelle) srcBits.push('généré le '+s.genere_le_libelle);
  srcBits.push('change '+fx);
  const cpt=j.compte||{};
  if(cpt.banque) srcBits.push(cpt.banque);
  const src='Source : '+srcBits.join(' · ')+'.';
  const bank=cpt.titulaires?(' · '+cpt.titulaires):'';
  return `<section class="card home-hero bdg-hero" id="bdg-joint">
    <div class="home-hero-top">
      <h2>${bdgEsc(j.titre||'Compte joint famille, octobre 2026')}</h2>
      <p class="desc">${bdgEsc(per+(cpt.banque?(' · '+cpt.banque):'')+bank)}</p>
    </div>
    <div class="home-strip bdg-kvs">
      <div class="home-kv"><span class="l">Dépenses perso</span><b>${bdgAmt(tot.depenses_eur,'EUR')}</b><small>${bdgAmt(tot.depenses_usd,'USD')}</small></div>
      <div class="home-kv"><span class="l">Revenus</span><b>${bdgAmt(tot.revenus_eur,'EUR')}</b><small>${bdgAmt(tot.revenus_usd,'USD')}</small></div>
      <div class="home-kv ${resteNeg?'is-down':''}"><span class="l">Reste</span><b class="${resteNeg?'down':'up'}">${bdgAmt(tot.reste_eur,'EUR')}</b><small class="${resteNeg?'down':'up'}">${bdgAmt(tot.reste_usd,'USD')}</small></div>
      <div class="home-kv bdg-kv-pro"><span class="l">Air Glow pub (pro)</span><b>${bdgAmt(tot.air_glow_pub_eur,'EUR')}</b><small>${bdgAmt(tot.air_glow_pub_usd,'USD')}</small></div>
    </div>
    <div class="home-table-scroll">
      <div class="home-table bdg-table" id="bdg-table-joint">
        ${bdgHead()}
        ${rows}
        ${depRow}
        ${revRow}
        ${resteRow}
        ${rembRow}
        ${vinRow}
        ${glowRow}
      </div>
    </div>
    ${tvNote?`<p class="bdg-src bdg-tv-flag">${bdgEsc(tvNote)}</p>`:''}
    <p class="bdg-src">${bdgEsc(src)}</p>
  </section>`;
}
function bdgComptes(b){ return (b&&b.comptes)||null; }
function bdgComptesHtml(b){
  const j=bdgComptes(b);
  if(!j) return '';
  const tot=j.totaux||{};
  const per=(j.periode&&j.periode.libelle)||'1er octobre – 25 novembre 2026';
  const fxVal=(j.fx&&(j.fx.taux!=null?j.fx.taux:j.fx));
  const fx=fxVal!=null?String(fxVal).replace('.',','):(bdgFx(b)||'1,0944');
  const cats=j.categories||[];
  const viDet=(tot.virements_internes_detail||[]).map(d=>`${d.libelle} : ${bdgAmt(d.montant_eur,'EUR')}`).join(' · ');
  const rows=cats.filter(c=>c.id!=='air_glow_pub').map(c=>{
    const empty=!c.n_operations;
    const obsU=empty&&!(c.observe_eur)? '—' : bdgAmt(c.observe_usd,'USD');
    const obsE=empty&&!(c.observe_eur)? '—' : bdgAmt(c.observe_eur,'EUR');
    const zeroEmpty=empty && !(Number(c.observe_eur));
    let extra='';
    if(c.id==='courses'){
      extra='';
    }
    const sum=(c.id==='virements_internes'&&viDet)?viDet:(c.detail||(c.n_operations? (c.n_operations+' opération'+(c.n_operations>1?'s':'')) : 'Aucune opération sur la période.'));
    const det=empty?`<div class="bdg-det">${bdgEsc(c.detail||'Aucune opération sur la période.')}</div>`:bdgOpsDetails(c.operations,sum,extra);
    const cls=['bdg-cat'];
    if(c.id==='courses') cls.push('bdg-cat-courses');
    if(c.id==='virements_internes') cls.push('bdg-cat-interne');
    if(c.id==='credit_revolut') cls.push('bdg-cat-fixe');
    if(c.id==='air_glow_pub') cls.push('bdg-cat-pro');
    if(zeroEmpty) cls.push('is-empty');
    const row=bdgRow({
      id:'bdg-cat-'+c.id,
      cls:cls,
      poste:c.poste||c.id,
      detailsHtml:det,
      obsUsd:zeroEmpty?'—':obsU,
      obsEur:zeroEmpty?'—':obsE,
      projUsd:zeroEmpty?'—':bdgAmt(c.projection_usd,'USD'),
      projEur:zeroEmpty?'—':bdgAmt(c.projection_eur,'EUR'),
      objectif:'—'
    });
    return c.id==='courses'? (row+bdgLidlBlock(c)) : row;
  }).join('');
  const resteNeg=Number(tot.reste_eur)<0;
  const depRow=bdgRow({id:'bdg-comptes-depenses',cls:['bdg-foot','bdg-tot-dep'],poste:'Total dépenses personnelles',detail:'Hors virements internes, épargne, investissement, capital du crédit Revolut et Air Glow pub (pro)',obsUsd:bdgAmt(tot.depenses_usd,'USD'),obsEur:bdgAmt(tot.depenses_eur,'EUR'),projUsd:bdgAmt(tot.depenses_usd,'USD'),projEur:bdgAmt(tot.depenses_eur,'EUR'),objectif:'—'});
  const revDet=bdgOpsDetails(j.revenus_operations||[], tot.revenus_detail||'Revenus réels du foyer (salaire Tesla + France Travail)');
  const revRow=bdgRow({id:'bdg-comptes-revenus',cls:['bdg-foot','bdg-tot-rev'],poste:'Total revenus',detailsHtml:revDet,obsUsd:bdgAmt(tot.revenus_usd,'USD'),obsEur:bdgAmt(tot.revenus_eur,'EUR'),projUsd:bdgAmt(tot.revenus_usd,'USD'),projEur:bdgAmt(tot.revenus_eur,'EUR'),objectif:'—'});
  const resteRow=bdgRow({id:'bdg-comptes-reste',cls:['bdg-foot','bdg-tot-reste',resteNeg?'is-over':'is-ok'],poste:'Reste (revenus − dépenses)',detail:tot.reste_formule||'Revenus − dépenses personnelles',obsUsd:bdgAmt(tot.reste_usd,'USD'),obsEur:bdgAmt(tot.reste_eur,'EUR'),projUsd:bdgAmt(tot.reste_usd,'USD'),projEur:bdgAmt(tot.reste_eur,'EUR'),objectif:'—'});
  const remb=j.remboursements_operations||[];
  const rembRow=remb.length?bdgRow({id:'bdg-comptes-remb',cls:['bdg-annexe'],poste:'Remboursements (à part)',detailsHtml:bdgOpsDetails(remb, tot.remboursements_note||'Remboursements, non inclus dans les revenus'),obsUsd:bdgAmt(tot.remboursements_usd,'USD'),obsEur:bdgAmt(tot.remboursements_eur,'EUR'),projUsd:'—',projEur:'—',objectif:'—'}):'';
  const vin=j.virements_internes_entrants||[];
  const vinRow=bdgRow({id:'bdg-comptes-vin',cls:['bdg-annexe','bdg-cat-interne'],poste:'Virements internes entrants',detailsHtml:bdgOpsDetails(vin, 'Alimentations internes (non revenus) · '+((vin.length)||0)+' opération'+(vin.length>1?'s':'')),obsUsd:bdgAmt(tot.virements_internes_entrants_usd,'USD'),obsEur:bdgAmt(tot.virements_internes_entrants_eur,'EUR'),projUsd:'—',projEur:'—',objectif:'—'});
  const cr=tot.credit_revolut||{};
  const fin=j.financement_operations||[];
  const finNote=cr.note||tot.financement_note||'Crédit Revolut : ni un revenu ni une dépense. Mensualité 169,60 €.';
  const finDet=bdgOpsDetails(fin, finNote+(cr.mensualite_eur!=null?(' Mensualité : '+bdgAmt(cr.mensualite_eur,'EUR')+' / '+bdgAmt(cr.mensualite_usd,'USD')+'.'):'' ));
  const finRow=(fin.length||cr.capital_eur)?bdgRow({id:'bdg-comptes-credit-revolut',cls:['bdg-annexe','bdg-cat-fixe'],poste:cr.libelle||'Crédit Revolut 23 500 €',detailsHtml:finDet,obsUsd:bdgAmt(cr.mensualite_usd,'USD'),obsEur:bdgAmt(cr.mensualite_eur,'EUR'),projUsd:bdgAmt(cr.mensualite_usd,'USD'),projEur:bdgAmt(cr.mensualite_eur,'EUR'),objectif:'mensualité'}):'';
  const glow=cats.find(c=>c.id==='air_glow_pub');
  const glowRow=glow?bdgRow({id:'bdg-comptes-airglow',cls:['bdg-foot','bdg-annexe','bdg-cat-pro'],poste:'Sous-total Air Glow, pub (pro)',detailsHtml:bdgOpsDetails(glow.operations||[], glow.detail||(tot.air_glow_pub_note||'Publicité Air Glow, exclue des dépenses personnelles')),obsUsd:bdgAmt(tot.air_glow_pub_usd!=null?tot.air_glow_pub_usd:glow.observe_usd,'USD'),obsEur:bdgAmt(tot.air_glow_pub_eur!=null?tot.air_glow_pub_eur:glow.observe_eur,'EUR'),projUsd:bdgAmt(glow.projection_usd,'USD'),projEur:bdgAmt(glow.projection_eur,'EUR'),objectif:'—' }):'';
  const tvFlag=j.tradingview_sur_le_releve||{};
  const tvNote=tvFlag.present_sur_le_releve?(tvFlag.note||'Un prélèvement TradingView figure sur le relevé ; non recopié en seconde ligne d’abonnement.'):'';
  const srcBits=[];
  const s=j.source||{};
  if(s.intitule) srcBits.push(s.intitule);
  if(s.periode_releve&&s.periode_releve.libelle) srcBits.push('période '+s.periode_releve.libelle);
  if(s.genere_le_libelle) srcBits.push('généré le '+s.genere_le_libelle);
  srcBits.push('change '+fx);
  const src='Source : '+srcBits.join(' · ')+'.';
  const cptes=(j.comptes||[]).map(x=>x.libelle+(x.titulaires?(' ('+x.titulaires+')'):'')).join(' · ');
  const oct=tot.octobre||{}, nov=tot.novembre_1_25||{};
  const moisNote=(oct.depenses_eur!=null)?(`Octobre : dépenses ${bdgAmt(oct.depenses_eur,'EUR')} / revenus ${bdgAmt(oct.revenus_eur,'EUR')} / reste ${bdgAmt(oct.reste_eur,'EUR')}. 1–25 novembre : dépenses ${bdgAmt(nov.depenses_eur,'EUR')} / revenus ${bdgAmt(nov.revenus_eur,'EUR')} / reste ${bdgAmt(nov.reste_eur,'EUR')}.`):'';
  return `<section class="card home-hero bdg-hero" id="bdg-comptes" data-bdg-fold="comptes">
    <div class="home-hero-top">
      <h2>${bdgFoldTitle('comptes', j.titre||'Comptes', 'bdg-comptes-body')}</h2>
      <p class="desc">${bdgEsc(per+(cptes?(' · '+cptes):''))}</p>
    </div>
    <div class="home-strip bdg-kvs">
      <div class="home-kv"><span class="l">Dépenses perso</span><b>${bdgAmt(tot.depenses_eur,'EUR')}</b><small>${bdgAmt(tot.depenses_usd,'USD')}</small></div>
      <div class="home-kv"><span class="l">Revenus</span><b>${bdgAmt(tot.revenus_eur,'EUR')}</b><small>${bdgAmt(tot.revenus_usd,'USD')}</small></div>
      <div class="home-kv ${resteNeg?'is-down':''}"><span class="l">Reste</span><b class="${resteNeg?'down':'up'}">${bdgAmt(tot.reste_eur,'EUR')}</b><small class="${resteNeg?'down':'up'}">${bdgAmt(tot.reste_usd,'USD')}</small></div>
      <div class="home-kv"><span class="l">Salaire Tesla</span><b>${bdgAmt(tot.salaire_eur,'EUR')}</b><small>${bdgAmt(tot.salaire_usd,'USD')}</small></div>
      <div class="home-kv bdg-kv-fixe"><span class="l">Crédit Revolut 23 500 €</span><b>${bdgAmt((tot.credit_revolut||{}).mensualite_eur,'EUR')}</b><small>mensualité · ${bdgAmt((tot.credit_revolut||{}).mensualite_usd,'USD')}</small></div>
      <div class="home-kv bdg-kv-fixe"><span class="l">Charges fixes crédit</span><b>${bdgAmt(tot.charges_fixes_credit_mensuel_eur,'EUR')}</b><small>LOA Tesla + Revolut / mois · ${bdgAmt(tot.charges_fixes_credit_mensuel_usd,'USD')}</small></div>
      <div class="home-kv bdg-kv-pro"><span class="l">Air Glow pub (pro)</span><b>${bdgAmt(tot.air_glow_pub_eur,'EUR')}</b><small>${bdgAmt(tot.air_glow_pub_usd,'USD')}</small></div>
    </div>
    <div class="bdg-fold-body" id="bdg-comptes-body">
    <div class="home-table-scroll">
      <div class="home-table bdg-table" id="bdg-table-comptes">
        ${bdgHead()}
        ${rows}
        ${depRow}
        ${revRow}
        ${resteRow}
        ${rembRow}
        ${vinRow}
        ${finRow}
        ${glowRow}
      </div>
    </div>
    ${tvNote?`<p class="bdg-src bdg-tv-flag">${bdgEsc(tvNote)}</p>`:''}
    <p class="bdg-src">${bdgEsc(src)}</p>
    ${moisNote?`<p class="bdg-src">${moisNote}</p>`:''}
    ${tot.charges_fixes_credit_note?`<p class="bdg-src bdg-tv-flag">${bdgEsc(tot.charges_fixes_credit_note)}</p>`:''}
    </div>
  </section>`;
}

function bdgMoy(b){ return (b&&b.budget_mensuel)||null; }
function bdgMoyHead(){
  return `<div class="home-table-h bdg-moy-th" aria-hidden="true">
    <span>Poste</span><span>Détail / hypothèse</span><span>Moyenne $</span><span>Moyenne €</span>
  </div>`;
}
function bdgMoyRow(p, cls){
  const c=['bdg-moy-row'].concat(cls||[]).join(' ');
  const divNet=p.dividendes_coupons_nets_eur;
  const side=(divNet!=null&&divNet!=='')
    ? `<div class="bdg-moy-side">En face : dividendes et coupons nets ${bdgAmt(divNet,'EUR')}${p.dividendes_coupons_nets_usd!=null?(' / '+bdgAmt(p.dividendes_coupons_nets_usd,'USD')):''} <small>(hors base prudente)</small></div>`
    : '';
  return `<div class="${c}">
    <div class="bdg-poste"><h2>${bdgEsc(p.libelle||p.id||'')}</h2></div>
    <div class="bdg-det">${bdgEsc(p.detail||'—')}${side}</div>
    <div class="bdg-num">${bdgAmt(p.moyenne_usd,'USD')}</div>
    <div class="bdg-num">${bdgAmt(p.moyenne_eur,'EUR')}</div>
  </div>`;
}
function bdgMoyFoot(lab, eur, usd){
  return `<div class="bdg-moy-row bdg-moy-foot">
    <div class="bdg-poste"><h2>${bdgEsc(lab)}</h2></div>
    <div class="bdg-det"></div>
    <div class="bdg-num">${bdgAmt(usd,'USD')}</div>
    <div class="bdg-num">${bdgAmt(eur,'EUR')}</div>
  </div>`;
}
function bdgMoyKv(label, eur, usd, extraCls, tone){
  const cls=['home-kv'].concat(extraCls||[]).filter(Boolean).join(' ');
  const t=tone||'';
  const bCls=t==='down'?'down':(t==='up'?'up':'');
  return `<div class="${cls}${t==='down'?' is-down':''}"><span class="l">${bdgEsc(label)}</span><b class="${bCls}">${bdgAmt(eur,'EUR')}</b><small class="${bCls}">${bdgAmt(usd,'USD')}</small></div>`;
}
function bdgMensuelHtml(b){
  const m=bdgMoy(b);
  if(!m) return '';
  const fx=(m.fx&&m.fx.taux!=null)?String(m.fx.taux).replace('.',','):'1,0944';
  const rev=m.revenus||{};
  const base=rev.base_prudente||{};
  const bonus=rev.france_travail_bonus||{};
  const obs=rev.octobre_observe||{};
  const dep=m.depenses_recurrentes||{};
  const act=m.capacite_actuelle||{};
  const cib=m.capacite_cible||{};
  const pan=m.panier_cible||{};
  const obj=m.objectif_epargne||{};
  const res=m.reserve_securite||{};
  const epar=m.epargne_realisee||{};
  const met=m.methode||{};
  const hyps=met.hypotheses||[];
  const defic=!!(m.deficitaire||act.deficitaire||Number(act.eur)<0);
  const actTone=defic?'down':'up';
  const cibTone=Number(cib.eur)<0?'down':'up';
  const noteHaut=m.note_haut||rev.note_base||'Base prudente : 2 800 € net + prime 4 000 €/an, sans commissions, Priscilla sans revenu';
  const refLib=m.mois_reference_libelle||'Mois de référence : octobre 2026';
  const moisSec=res.mois_securite;
  const moisSecTxt=(moisSec==null||moisSec==='')?'—':(Number(moisSec).toLocaleString('fr-FR',{minimumFractionDigits:2,maximumFractionDigits:2})+'\u00a0mois');
  const red=m.objectif_reduction_autres_postes||{};
  const alerte=defic?`<div class="bdg-moy-alerte" role="status">Budget déficitaire sur la base prudente : ${bdgAmt(act.eur,'EUR')} / mois (revenus 3 133,33 € − dépenses récurrentes d'octobre). Grok Heavy est conservé (outil de pilotage). Objectif de réduction sur les autres postes pour atteindre l'équilibre : ${bdgAmt(red.eur,'EUR')} / mois (déficit actuel − panier).</div>`:'';
  const kv=`<div class="home-strip bdg-kvs bdg-moy-kvs">
      ${bdgMoyKv('Base prudente', rev.total_moyenne_eur, rev.total_moyenne_usd)}
      ${bdgMoyKv('Dépenses récurrentes (octobre)', dep.moyenne_eur, dep.moyenne_usd)}
      ${bdgMoyKv("Capacité d'épargne actuelle", act.eur, act.usd, [], actTone)}
      ${bdgMoyKv('Capacité cible (propositions)', cib.eur, cib.usd, ['bdg-kv-fixe'], cibTone)}
      ${bdgMoyKv("Objectif de réduction sur les autres postes pour l'équilibre", red.eur, red.usd, [], 'down')}
      <div class="home-kv${(moisSec!=null&&moisSec<3)?' is-down':''}"><span class="l">Mois de sécurité</span><b class="${(moisSec!=null&&moisSec<3)?'down':''}">${moisSecTxt}</b><small>${bdgAmt(res.epargne_disponible_eur,'EUR')} d'épargne dispo</small></div>
      ${bdgMoyKv('Bonus France Travail (hors base)', bonus.octobre_eur, bonus.octobre_usd)}
      ${bdgMoyKv('Revenus réels d\'octobre (comparaison)', obs.total_eur, obs.total_usd)}
    </div>`;
  const hypHtml=hyps.length?(`<div class="bdg-moy-hyp"><h3 class="bdg-moy-h">Hypothèses de calcul</h3><ol>${hyps.map(h=>`<li>${bdgEsc(h)}</li>`).join('')}</ol></div>`):'';
  const sal=rev.salaire_tesla||{};
  const ft=rev.france_travail||{};
  const revRows=[
    {libelle:'Salaire net (base prudente)', moyenne_eur:base.salaire_net_eur, moyenne_usd:base.salaire_net_usd, detail:'2 800 € net par mois, sans commissions. Priscilla n\'a aucun revenu.'},
    {libelle:'Prime de participation (lissée)', moyenne_eur:base.prime_mensuelle_eur, moyenne_usd:base.prime_mensuelle_usd, detail:'4 000 € par an, soit 333,33 € / mois lissés sur 12 mois.'},
    {libelle:'France Travail (bonus temporaire, hors base)', moyenne_eur:bonus.moyenne_eur, moyenne_usd:bonus.moyenne_usd, detail:bonus.note},
    {libelle:'Salaire Tesla réellement perçu en octobre (comparaison)', moyenne_eur:sal.octobre_eur, moyenne_usd:sal.octobre_usd, detail:sal.note},
    {libelle:'France Travail observé en octobre (comparaison)', moyenne_eur:ft.octobre_eur, moyenne_usd:usdSafe(ft.octobre_eur), detail:ft.note},
    {libelle:'Dividendes et coupons nets d\'octobre (hors base)', moyenne_eur:(rev.dividendes_coupons_octobre||{}).net_eur, moyenne_usd:(rev.dividendes_coupons_octobre||{}).net_usd, detail:(rev.dividendes_coupons_octobre||{}).note}
  ].map(p=>bdgMoyRow(p)).join('');
  const revBlock=`<div class="bdg-moy-block" id="bdg-moy-revenus">
      <h3 class="bdg-moy-h">Revenus mensuels</h3>
      <div class="bdg-moy-table">${bdgMoyHead()}${revRows}${bdgMoyFoot('Total base prudente (retenue)', rev.total_moyenne_eur, rev.total_moyenne_usd)}</div>
      <p class="bdg-moy-p">Comparaison : revenus réellement perçus en octobre ${bdgAmt(obs.total_eur,'EUR')} / ${bdgAmt(obs.total_usd,'USD')}. Avec le bonus France Travail en plus de la base prudente : ${bdgAmt(rev.variante_avec_france_travail_eur,'EUR')} / ${bdgAmt(rev.variante_avec_france_travail_usd,'USD')}. Les dividendes et coupons nets d'octobre (${bdgAmt((rev.dividendes_coupons_octobre||{}).net_eur,'EUR')}) sont affichés en face des frais de courtage, sans entrer dans la base prudente.</p>
    </div>`;
  const groupes=(m.groupes||[]).map(g=>{
    const cls='bdg-moy-grp-'+g.id;
    const rows=(g.postes||[]).map(p=>bdgMoyRow(p,[cls])).join('');
    return `<div class="bdg-moy-block" id="bdg-moy-${bdgEsc(g.id)}">
      <h3 class="bdg-moy-h">${bdgEsc(g.libelle||g.id)}</h3>
      <p class="bdg-moy-p">${bdgEsc(g.note||'')}</p>
      <div class="bdg-moy-table">${bdgMoyHead()}${rows}${bdgMoyFoot('Sous-total '+ (g.libelle||''), g.total_moyenne_eur, g.total_moyenne_usd)}</div>
    </div>`;
  }).join('');
  const prov=m.provisions||{};
  const provRows=(prov.lignes||[]).map(p=>{
    const rec={libelle:p.libelle, moyenne_eur:p.moyenne_eur, moyenne_usd:p.moyenne_usd,
      detail:(p.detail||'')+(p.total_periode_eur!=null?(' Total période : '+String(p.total_periode_eur).replace('.',',')+' €.'):'')};
    return bdgMoyRow(rec);
  }).join('');
  const provBlock=`<div class="bdg-moy-block" id="bdg-moy-provisions">
      <h3 class="bdg-moy-h">${bdgEsc(prov.libelle||'Provisions annuelles')}</h3>
      <p class="bdg-moy-p">${bdgEsc(prov.note||'')}</p>
      <div class="bdg-moy-table">${bdgMoyHead()}${provRows}${bdgMoyFoot('Sous-total provisions / 12', prov.total_moyenne_eur, prov.total_moyenne_usd)}</div>
    </div>`;
  const eparBlock=`<div class="bdg-moy-block" id="bdg-moy-epargne">
      <h3 class="bdg-moy-h">${bdgEsc(epar.libelle||"Vers l'investissement")}</h3>
      <p class="bdg-moy-p">${bdgEsc(epar.note||'')}</p>
      <div class="bdg-moy-table">${bdgMoyHead()}
        ${bdgMoyRow({libelle:'Octobre (référence)', moyenne_eur:epar.octobre_eur, moyenne_usd:epar.octobre_usd, detail:"Épargne réalisée en octobre, ce n'est pas une dépense."})}
        ${bdgMoyRow({libelle:'Novembre au 25 (hors moyenne)', moyenne_eur:epar.novembre_eur, moyenne_usd:epar.novembre_usd, detail:'Hors mois de référence. Vague importante, éventuellement alimentée par le crédit Revolut.'})}
        ${bdgMoyFoot('Épargne réalisée d\'octobre (pas une capacité récurrente)', epar.moyenne_eur, epar.moyenne_usd)}
      </div>
      ${epar.alerte?`<p class="bdg-src bdg-moy-flag">${bdgEsc(epar.alerte)}</p>`:''}
    </div>`;
  const aboLi=a=>{
    const hors=a.inclus_dans_recurrent===false;
    const cons=!!a.conserve;
    const amt=hors&&a.affichage_eur!=null?bdgAmt(a.affichage_eur,'EUR'):bdgAmt(a.moyenne_eur,'EUR');
    const flag=hors?' <small class="bdg-moy-hors">hors récurrent</small>':(cons?' <small class="bdg-moy-keep">conservé (outil de pilotage)</small>':'');
    return `<li class="${hors?'is-hors':''}${cons?' is-keep':''}"><span>${bdgEsc(a.libelle||'')}<small>${bdgEsc(a.detail||'')}</small></span><span class="bdg-moy-eco">${amt}${flag}</span></li>`;
  };
  const abos=m.abonnements||[];
  const grokAbos=abos.filter(a=>a.famille==='grok');
  const autresAbos=abos.filter(a=>a.famille!=='grok');
  const aboList=(grokAbos.length?(`<li class="bdg-moy-abo-grp">Formules Grok</li>`+grokAbos.map(aboLi).join('')):'')+autresAbos.map(aboLi).join('');
  const trousHtml=`<div class="bdg-moy-block" id="bdg-moy-trous">
      <h3 class="bdg-moy-h">Trous dans la raquette</h3>
      <ul class="bdg-moy-list">${(m.trous||[]).map(t=>`<li><h3>${bdgEsc(t.titre||t.id||'')}</h3><p>${bdgEsc(t.detail||'')}</p></li>`).join('')}</ul>
      <h3 class="bdg-moy-h" style="margin-top:14px">Abonnements mensuels retenus</h3>
      <ul class="bdg-moy-abo">${aboList}</ul>
    </div>`;
  const pistesHtml=`<div class="bdg-moy-block" id="bdg-moy-pistes">
      <h3 class="bdg-moy-h">Pistes de réduction (propositions, pas des décisions)</h3>
      <ul class="bdg-moy-list">${(m.pistes||[]).map(t=>{
        const flag=t.dans_panier_cible?' · retenue dans la capacité cible':'';
        return `<li><h3>${bdgEsc(t.libelle||'')} <span class="bdg-moy-eco">${bdgAmt(t.economie_eur_mois,'EUR')}/mois</span></h3><p>${bdgEsc((t.source||'')+' '+(t.note||'')+flag)}</p></li>`;
      }).join('')}</ul>
      <p class="bdg-moy-p">${bdgEsc(pan.note||'')} Total du panier : ${bdgAmt(pan.total_economie_eur,'EUR')} / ${bdgAmt(pan.total_economie_usd,'USD')}. ${bdgEsc(red.libelle||"Objectif de réduction sur les autres postes pour atteindre l'équilibre")} : ${bdgAmt(red.eur,'EUR')} / ${bdgAmt(red.usd,'USD')} (déficit actuel − panier).</p>
    </div>`;
  const synt=`<div class="bdg-moy-block" id="bdg-moy-synthese">
      <h3 class="bdg-moy-h">Synthèse</h3>
      <div class="bdg-moy-table">${bdgMoyHead()}
        ${bdgMoyRow({libelle:'Base prudente de revenus', moyenne_eur:rev.total_moyenne_eur, moyenne_usd:rev.total_moyenne_usd, detail:noteHaut})}
        ${bdgMoyRow({libelle:'Dépenses récurrentes d\'octobre', moyenne_eur:dep.moyenne_eur, moyenne_usd:dep.moyenne_usd, detail:dep.detail})}
        ${bdgMoyRow({libelle:"Capacité d'épargne actuelle", moyenne_eur:act.eur, moyenne_usd:act.usd, detail:act.formule+(defic?' Budget déficitaire sur cette base.':'')})}
        ${bdgMoyRow({libelle:'Capacité cible après propositions', moyenne_eur:cib.eur, moyenne_usd:cib.usd, detail:cib.formule})}
        ${bdgMoyRow({libelle:(red.libelle||"Objectif de réduction sur les autres postes pour atteindre l'équilibre"), moyenne_eur:red.eur, moyenne_usd:red.usd, detail:red.formule+' '+(red.note||'')})}
        ${bdgMoyRow({libelle:"Objectif proposé", moyenne_eur:obj.propose_eur, moyenne_usd:obj.propose_usd, detail:obj.note})}
        ${bdgMoyRow({libelle:'Épargne disponible (25/11)', moyenne_eur:res.epargne_disponible_eur, moyenne_usd:res.epargne_disponible_usd, detail:res.epargne_disponible_note})}
        ${bdgMoyRow({libelle:'Mois de sécurité : '+moisSecTxt, moyenne_eur:null, moyenne_usd:null, detail:'Nombre de mois de charges fixes couverts par l\'épargne disponible. '+(res.note||'')})}
        ${bdgMoyRow({libelle:'Réserve 3 mois de charges fixes', moyenne_eur:res.mois_3_eur, moyenne_usd:res.mois_3_usd, detail:res.detail})}
        ${bdgMoyRow({libelle:'Réserve 6 mois de charges fixes', moyenne_eur:res.mois_6_eur, moyenne_usd:res.mois_6_usd, detail:res.note})}
      </div>
      <p class="bdg-moy-p">Comparaison : avec les revenus réellement perçus en octobre, la capacité serait de ${bdgAmt(act.variante_octobre_observe_eur,'EUR')}. Avec le bonus France Travail en plus de la base prudente : ${bdgAmt(act.variante_avec_france_travail_eur,'EUR')}. ${bdgEsc(cib.variante_grok_heavy_mensuel_note||'')}</p>
    </div>`;
  const floues=`<div class="bdg-moy-block" id="bdg-moy-flou">
      <h3 class="bdg-moy-h">Lignes encore floues</h3>
      <ul class="bdg-moy-list">${(m.lignes_floues||[]).map(t=>`<li><h3>${bdgEsc(t.sujet||'')} ${t.montant_eur!=null?('<span class="bdg-moy-eco">'+bdgAmt(t.montant_eur,'EUR')+'</span>'):''}</h3><p>${bdgEsc((t.classification?('Classé aujourd’hui : '+t.classification+'. '):'')+(t.question||''))}</p></li>`).join('')}</ul>
    </div>`;
  const src=(m.source&&(m.source.comptes||''))?'Source : relevés data/budget (comptes fusionnés + tickets Lidl), abonnement TradingView Essential. Change '+fx+'. Soldes au 25/11/2026.':'';
  return `<section class="card home-hero bdg-hero bdg-moy${defic?' is-deficitaire':''}" id="bdg-mensuel" data-bdg-fold="mensuel">
    <div class="home-hero-top">
      <h2>${bdgFoldTitle('mensuel', m.titre||'Budget mensuel moyen', 'bdg-mensuel-body')}</h2>
      <p class="desc">${bdgEsc(refLib)}</p>
      <p class="bdg-moy-note">${bdgEsc(noteHaut)}</p>
    </div>
    ${alerte}
    ${kv}
    <div class="bdg-fold-body" id="bdg-mensuel-body">
      ${hypHtml}
      ${revBlock}
      ${groupes}
      ${provBlock}
      ${eparBlock}
      ${synt}
      ${trousHtml}
      ${pistesHtml}
      ${floues}
      ${src?`<p class="bdg-src">${bdgEsc(src)}</p>`:''}
    </div>
  </section>`;
}
function usdSafe(eur){
  const n=Number(eur);
  if(!Number.isFinite(n)) return null;
  return Math.round((n*1.0944+1e-12)*100)/100;
}
function bdgTableHTML(b){
  return bdgMensuelHtml(b)+bdgCourtHtml(b)+bdgComptesHtml(b);
}
function bdgPageHTML(){
  const b=bdgData()||{};
  const title='Budget';
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
  bdgBindFolds(page);
  bdgBindEnsFilt(page);
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
