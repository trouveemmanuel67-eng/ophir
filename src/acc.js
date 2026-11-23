/* ===== Accordéons : cartes repliées par défaut, état mémorisé dans localStorage ===== */
const ACC_KEY='ophir-acc:';
const accGet=id=>{try{return localStorage.getItem(ACC_KEY+id)==='1';}catch(e){return false;}};
const accSet=(id,v)=>{try{localStorage.setItem(ACC_KEY+id,v?'1':'0');}catch(e){}};
function accResize(card){card.querySelectorAll('canvas').forEach(c=>{const ch=Chart.getChart(c);if(ch)ch.resize();});}
function accToggle(card,open,save=true){
  card.classList.toggle('acc-open',open);
  const h=card.querySelector('.acc-head');if(h)h.setAttribute('aria-expanded',open);
  if(save)accSet(card.dataset.acc,open);
  if(open){requestAnimationFrame(()=>accResize(card));setTimeout(()=>accResize(card),320);}
}
function accEsc(s){return String(s||'').replace(/&/g,'&amp;').replace(/"/g,'&quot;').replace(/</g,'&lt;');}
function accPlain(html){const d=document.createElement('div');d.innerHTML=html;return (d.textContent||'').replace(/\s+/g,' ').trim();}
function accAbbrevTitle(full){
  let t=(full||'').replace(/^▸\s*/,'').trim();
  t=t.replace(/\s*·\s*(taux,\s*)?sentiment et achat \/ vente\s*$/i,'');
  t=t.replace(/\s*·\s*taux \(repère de marché\)\s*$/i,'');
  t=t.replace(/\s*·\s*notes APEX\s*$/i,'');
  t=t.replace(/^Secteurs\s+/i,'');
  t=t.replace(/^Obligations\s+/i,'');
  t=t.replace(/^CHIFFRES ET CHARTES GRAPHIQUES$/i,'Chiffres');
  t=t.replace(/^zone euro, crédit et émergents$/i,'Zone euro');
  t=t.replace(/^Corée du Sud$/i,'Corée');
  t=t.replace(/^BTC, ETH, XRP, SOL et MSTR$/i,'BTC–MSTR');
  t=t.replace(/^Métaux$/i,'Métaux');
  return t;
}
function accShortNom(n){
  const m={
    'Technologie':'Techno','Consommation discrétionnaire':'Conso. disc.','Consommation de base':'Conso. base',
    'Services aux collectivités':'Services','Biens de consommation':'Conso.','Santé':'Santé',
    'Finance':'Finance','Énergie':'Énergie','Industrie':'Industrie','Matériaux':'Matériaux',
    'Immobilier':'Immo','Télécommunications':'Télécom','Services de communication':'Com.',
    'Argent':'Ag','Platine':'Pt','Palladium':'Pd'
  };
  return m[n]||n;
}
function accParseSum(el){
  const raw=(el.innerText||'').replace(/\s+/g,' ').trim();
  const html=el.innerHTML;
  const pairs=[];
  const re=/<i>([\s\S]*?)<\/i>\s*<b>([\s\S]*?)<\/b>/gi;
  let m;
  while((m=re.exec(html))) pairs.push({k:accPlain(m[1]),v:accPlain(m[2])});
  const lead=accPlain(html.split(/<i>/i)[0]);
  const apexEl=el.querySelector&&el.querySelector('.js-apex10');
  const apex=apexEl&&apexEl.dataset.display?{display:apexEl.dataset.display,hex:apexEl.dataset.hex||'',note:apexEl.dataset.note}:null;
  const out={raw,date:'',count:'',mkt:'',achat:null,neutre:null,vente:null,smax:'',smin:'',warn:'',rate:'',spread:'',slope:'',av:'',sent:'',extra:[],sans:false,keys:[],apex};
  const dateM=raw.match(/\bau\s+(\d{1,2}\s+\S+(?:\s+\d{4})?)/i)||raw.match(/clôtures? hebdomadaires au\s+([^·]+)/i);
  if(dateM) out.date=dateM[1].trim();
  let gics=lead.match(/(\d+)\s+secteurs\s+GICS/i);
  let sect=lead.match(/(\d+)\s+secteurs\b/i);
  let seg=lead.match(/(\d+)\s+segments/i);
  let met=lead.match(/(\d+)\s+métaux/i);
  let secn=lead.match(/(\d+)\s+sections/i);
  let dev=lead.match(/(\d+)\s+devises/i);
  let nc=lead.match(/\+(\d+)\s+non couvert/i);
  if(gics) out.count=gics[1]+' GICS';
  else if(sect) out.count=sect[1]+' sect.';
  else if(seg) out.count=seg[1]+' seg.';
  else if(met) out.count=met[1]+' métaux';
  else if(secn) out.count=secn[1]+' sect.';
  else if(dev) out.count=dev[1]+' dev.';
  if(nc) out.count=(out.count?out.count+' ':'')+'+'+nc[1]+' n.c.';
  const nRep=(raw.match(/repères de marché\s+(\d+)/i)||[])[1];
  const nNa=(raw.match(/indisponible\s+(\d+)/i)||[])[1];
  if(nRep) out.extra.push(nRep+' repères');
  if(nNa) out.extra.push(nNa+' n.d.');
  const metals=[];
  pairs.forEach(({k,v})=>{
    const kl=k.toLowerCase();
    if(kl==='marché') out.mkt=v;
    else if(kl==='achat') out.achat=parseInt(v,10);
    else if(kl==='neutre') out.neutre=parseInt(v,10);
    else if(kl==='vente') out.vente=parseInt(v,10);
    else if(kl==='sentiment max'||kl==='sent. max') out.smax=v;
    else if(kl==='min') out.smin=v;
    else if(/^⚠/.test(k)||/près du record/i.test(k)) out.warn=v;
    else if(kl==='10 ans') out.rate=v;
    else if(/écart\s*\/\s*bund/i.test(k)) out.spread=v;
    else if(/ans\s*[−\-]\s*/.test(k)||/pente/i.test(k)) out.slope=k.replace(/\s+/g,' ')+' '+v;
    else if(kl==='achat / vente') out.av=v;
    else if(kl==='sentiment') out.sent=v;
    else if(kl==='dxy') out.extra.unshift('DXY '+v.replace(/\s*,\s*sans note/i,''));
    else if(/sans note/i.test(k)||/sans note/i.test(v)) out.sans=true;
    else if(/^(or|argent|platine|palladium)$/i.test(k)){
      const sc=(v.match(/([+−\-]?\d+)/)||[])[1];
      metals.push(accShortNom(k)+(sc?' '+sc.replace('-','−'):''));
      if(/Achat/i.test(v)) out.achat=(out.achat||0)+1;
      else if(/Vente/i.test(v)) out.vente=(out.vente||0)+1;
      else if(/Neutre/i.test(v)) out.neutre=(out.neutre||0)+1;
    } else {
      out.keys.push({k,v});
    }
  });
  if(metals.length) out.extra.push(metals.join(' · '));
  return out;
}
function accDotsHTML(p){
  if(p.achat==null&&p.neutre==null&&p.vente==null) return '';
  const a=p.achat||0,n=p.neutre||0,r=p.vente||0;
  const tip=a+' achat · '+n+' neutre · '+r+' vente';
  return `<span class="al al-dots" title="${accEsc(tip)}"><span><i class="g"></i>${a}</span><span><i class="o"></i>${n}</span><span><i class="r"></i>${r}</span></span>`;
}
function accCell(cls,text,title){
  const empty=!text;
  return `<span class="al ${cls}${empty?' is-empty':''}"${title?` title="${accEsc(title)}"`:''}>${empty?'—':text}</span>`;
}
function accApexHTML(p){
  const a=p&&p.apex;
  if(!a||!a.display||a.display==='–'||a.display==='-') return '';
  const col=a.hex||'#e6c27a';
  return `<span class="al al-note apex10" title="Note APEX /100"><b style="color:${col}">${accEsc(a.display)}</b><small style="color:${col}">/100</small></span>`;
}
function accLineHTML(p){
  const note=accApexHTML(p);
  let mkt=p.mkt?`Marché ${p.mkt}`:(p.rate?`10 ans ${p.rate}`:'');
  if(p.spread&&mkt) mkt+=' · '+p.spread;
  else if(p.spread&&!mkt) mkt='Bund '+p.spread;
  let mid=accDotsHTML(p);
  if(!mid&&p.av) mid=accCell('al-dots',p.av);
  if(!mid) mid=accCell('al-dots','');
  let mx='';
  if(p.smax){const parts=p.smax.split(/\s+/);const nom=parts.length>1?accShortNom(parts.slice(0,-1).join(' '))+' '+parts[parts.length-1]:p.smax;mx='S max '+nom;}
  else if(p.sent) mx='S '+p.sent;
  else if(p.spread&&!p.rate) mx='Bund '+p.spread;
  else if(p.extra[0]&&!p.smax) mx=p.extra[0];
  let mn='';
  if(p.smin){const parts=p.smin.split(/\s+/);const nom=parts.length>1?accShortNom(parts.slice(0,-1).join(' '))+' '+parts[parts.length-1]:p.smin;mn='min '+nom;}
  else if(p.slope) mn=p.slope.replace(/^10 ans\s*[−\-]\s*/,'10−')
    .replace(/^10 ans /,'10y ');
  else if(p.extra[1]) mn=p.extra[1];
  else if(p.sans) mn='sans note';
  let wn=p.warn?('⚠ '+p.warn):(p.sans&&!mn?'sans note':'');
  if(p.keys.length && !p.mkt && !p.rate && p.achat==null){
    const packed=p.keys.slice(0,3).map(x=>`<i>${accEsc(x.k)}</i> <b>${accEsc(x.v)}</b>`).join(' · ');
    return note+accCell('al-mkt','')+mid+`<span class="al al-keys al-max" style="grid-column:span 3" title="${accEsc(p.raw)}">${packed}</span>`;
  }
  return note+accCell('al-mkt',mkt)+mid+accCell('al-max',mx)+accCell('al-min',mn)+accCell('al-warn',wn,wn&&p.raw);
}
function accShortenTitle(head, parsed){
  const tt=head.querySelector('.acc-tt'); if(!tt) return;
  const full=tt.innerText.replace(/\s+/g,' ').trim();
  const imgs=[...tt.querySelectorAll('img')];
  let short=accAbbrevTitle(full);
  if(parsed&&parsed.count && !/GICS|sect\.|seg\.|métaux|n\.c\./i.test(short))
    short=(short?short+' · ':'')+parsed.count;
  tt.title=full+(parsed&&parsed.date?(' · au '+parsed.date):'');
  tt.textContent='';
  imgs.forEach(img=>tt.appendChild(img));
  tt.appendChild(document.createTextNode(short));
}
function accCompactSum(head){
  const desc=head.querySelector('.acc-sum');
  if(!desc||desc.classList.contains('acc-line')) return;
  const parsed=accParseSum(desc);
  const full=parsed.raw||desc.innerText.replace(/\s+/g,' ').trim();
  desc.className='desc acc-sum acc-line';
  desc.setAttribute('title',full);
  desc.innerHTML=accLineHTML(parsed);
  if(parsed.apex&&parsed.apex.display) head.classList.add('acc-has-note');
  accShortenTitle(head, parsed);
}
function accSumSpread(head){
  /* conservé pour compatibilité : l'accueil compact passe par accCompactSum */
  accCompactSum(head);
}
function accWire(card,id,head){
  card.dataset.acc=id;card.classList.add('acc');
  head.classList.add('acc-head');head.setAttribute('role','button');head.setAttribute('tabindex','0');
  const h2=head.querySelector('h2')||head;
  if(!h2.querySelector('.acc-chev')){const tt=document.createElement('span');tt.className='acc-tt';
    [...h2.childNodes].filter(n=>!(n.classList&&n.classList.contains('acc-key'))).forEach(n=>tt.appendChild(n));
    h2.insertBefore(tt,h2.firstChild);h2.insertAdjacentHTML('afterbegin','<span class="acc-chev" aria-hidden="true">▸</span>');}
  accCompactSum(head);
  const go=e=>{if(e.target.closest('a,button:not(.acc-head)'))return;accToggle(card,!card.classList.contains('acc-open'));};
  head.addEventListener('click',go);head.addEventListener('keydown',e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();go(e);}});
  accToggle(card,accGet(id),false);
}
function accBody(nodes){const b=document.createElement('div');b.className='acc-body';const i=document.createElement('div');i.className='acc-in';b.appendChild(i);nodes.forEach(n=>i.appendChild(n));return b;}
/* Cartes du contenu principal : seul l'en-tête (titre + sous-titre) reste visible */
function accMain(section,tabId){
  section.querySelectorAll('.card').forEach((card,k)=>{
    if(card.classList.contains('acc')||card.classList.contains('placeholder')||card.classList.contains('no-acc')||card.classList.contains('home-card')||card.classList.contains('home-hero'))return;
    const h2=card.querySelector(':scope>h2');if(!h2)return;
    const desc=h2.nextElementSibling&&h2.nextElementSibling.classList.contains('desc')?h2.nextElementSibling:null;
    const head=document.createElement('div');card.insertBefore(head,h2);head.appendChild(h2);if(desc)head.appendChild(desc);
    const kv=card.querySelector('.kpi .v');   // chiffre clé repris dans l'en-tête
    if(kv){const kl=card.querySelector('.kpi .l');const lab=kl?kl.textContent.split(' · ')[0]:'';h2.insertAdjacentHTML('beforeend',`<span class="acc-key" title="${kl?kl.textContent:''}"><small>${lab}</small> ${kv.innerHTML}</span>`);}
    const rest=[...card.childNodes].filter(n=>n!==head);
    card.appendChild(accBody(rest));
    accWire(card,tabId+'-'+k,head);
  });
  /* Bloc parent « CHIFFRES ET CHARTES GRAPHIQUES » qui regroupe toutes les cartes de l'onglet */
  if(!section.querySelector(':scope>.acc-group')){
    const subs=[...section.querySelectorAll(':scope>.card.acc:not(.no-group)')];if(!subs.length)return;
    const keys=subs.map(c=>c.querySelector(':scope>.acc-head .acc-key')).filter(Boolean)
      .map(k=>{const sm=k.querySelector('small');const v=k.cloneNode(true);v.querySelector('small')&&v.querySelector('small').remove();return `<i>${sm?sm.textContent:''}</i> <b>${v.textContent.trim()}</b>`;});
    const kids=[...section.childNodes].filter(n=>!(n.classList&&n.classList.contains('no-group')));
    const g=document.createElement('div');g.className='card acc-group';
    const head=document.createElement('div');
    head.innerHTML=`<h2>CHIFFRES ET CHARTES GRAPHIQUES</h2><div class="desc acc-sum">${subs.length} sections · ${keys.join(' · ')}</div>`;
    g.appendChild(head);g.appendChild(accBody(kids));section.appendChild(g);   /* ordre : Secteurs / Segments puis CHIFFRES */
    accWire(g,tabId+'-grp',head);
  }
}
/* Colonnes de droite : garde visibles les éléments essentiels, replie le reste */
function accSide(boxId,tabId){
  const card=document.querySelector('#'+boxId+' .card');if(!card||card.classList.contains('acc'))return;
  const keep=boxId==='ind'?['ind-t','ind-n','ind-badge','ind-val','ind-date','ind-gauge','ind-scale']:['av-sens','av-val','ind-date','av-gauge','av-scale','av-short'];
  const host=boxId==='ind'?card.querySelector('.ind-slot'):card;
  const h2=card.querySelector(':scope>h2');
  if(boxId==='av'){/* mention retirée */}
  const rest=[...host.children].filter(n=>n!==h2&&!keep.some(c=>n.classList&&n.classList.contains(c)));
  host.appendChild(accBody(rest));
  accWire(card,'side-'+boxId+'-'+tabId,h2);
  /* Format ligne pleine largeur : [titre + source] | [score + date] | [barre] | [mention / infos] ; le reste se déplie dessous */
  const pre=boxId==='ind'?'.ind-slot>':':scope>',q=sel=>card.querySelector(pre+sel);
  const srcEl=card.querySelector('.src')||[...card.querySelectorAll('p')].find(p=>/^Sources? :/.test(p.textContent.trim()));
  let src=null;if(srcEl){src=srcEl.cloneNode(true);src.className='ir-src';}
  const row=document.createElement('div');row.className='irow';
  const cell=(c,els)=>{const d=document.createElement('div');d.className='ir '+c;els.filter(Boolean).forEach(e=>d.appendChild(e));row.appendChild(d);};
  if(boxId==='ind'){cell('ir-t',[h2,q('.ind-t'),q('.ind-n'),src]);cell('ir-s',[q('.ind-val'),q('.ind-date')]);cell('ir-g',[q('.ind-gauge'),q('.ind-scale')]);cell('ir-i',[q('.ind-badge')]);}
  else{cell('ir-t',[h2,src]);cell('ir-s',[q('.av-val'),q('.ind-date')]);cell('ir-g',[q('.av-gauge'),q('.av-scale')]);cell('ir-i',[q('.av-sens'),q('.av-short')]);}
  card.insertBefore(row,card.firstChild);
}
function accAll(open){
  const tab=document.querySelector('section.tab.on');
  [...tab.querySelectorAll('.card.acc'),...document.querySelectorAll('.side .card.acc')].forEach(c=>accToggle(c,open));
  accBtn();
}
function accBtn(){
  const b=document.getElementById('accAll');if(!b)return;
  const tab=document.querySelector('section.tab.on');if(!tab)return;
  const all=[...tab.querySelectorAll('.card.acc'),...document.querySelectorAll('.side .card.acc')];
  const anyClosed=all.some(c=>!c.classList.contains('acc-open'));
  b.textContent=anyClosed?'▾ Tout déplier':'▸ Tout replier';b.dataset.open=anyClosed?'1':'0';
}
document.addEventListener('click',e=>{if(e.target.closest('.acc-head'))setTimeout(accBtn,0);});

/* Carte unique « Sentiment & Achat / Vente » : une ligne pleine largeur, une barre fusionnée, détails des deux indicateurs dessous */
function duoBuild(tabId){
  const I=document.getElementById('ind'),A=document.getElementById('av'),D=document.getElementById('duo');if(!D)return;
  const gi=IND[tabId],ga=AV[tabId],ic=I&&I.querySelector(':scope>.card'),ac=A&&A.querySelector(':scope>.card');
  const st=(typeof sectionApexAvg==='function')?sectionApexAvg(tabId):null;
  if(!st&&(!gi||!ga||!ic||!ac)){D.innerHTML='';return;}
  const avObj=(st&&st.av)||(ga?{score:ga.score,label:ga.label}:null);
  const seObj=(st&&st.sent)||(gi?{value:gi.value,label:gi.label}:null);
  if(!avObj||!seObj){D.innerHTML='';return;}
  const a10=(st&&st.apex10)||(ga&&ga.apex10)||null; /* t320u : pas de recalcul JS */
  const sl=ic&&(ic.querySelector('.ind-slot')||ic);
  const q=(r,c)=>r&&r.querySelector(':scope>'+c);
  const src=c=>{if(!c)return '';const e=c.querySelector('.src')||[...c.querySelectorAll('p')].find(p=>/^Sources? :/.test(p.textContent.trim()));if(!e)return '';const k=e.cloneNode(true);k.className='ir-src';return k.outerHTML;};
  const card=document.createElement('div');card.className='card duo-card';
  const sLab=seObj.label==='Peur extrême'?'Peur ext.':seObj.label;
  const duoDate=st
    ?('Moyenne de '+st.n+' actif'+(st.n>1?'s':'')+' de la section')
    :[gi&&gi.date&&('S au '+dshort(gi.date)),ga&&ga.date&&('AV au '+dshort(ga.date))].filter(Boolean).join(' · ');
  const tip='Note APEX /100'+(st?' : moyenne des notes affichées de la section, arrondie au point':'')+(duoDate?' · '+duoDate:'');
  card.innerHTML=`<div class="irow duo-row duo-slim" title="${accEsc(tip)}">
   <div class="ir ir-t"><h2 title="Note APEX">Note APEX</h2></div>
   <div class="ir ir-s">${typeof apexNoteHTML==='function'?apexNoteHTML(a10):''}
    <div class="duo-sc" title="${accEsc('Achat / Vente, échelle −100 à +100'+(st?' · moyenne des actifs de la section':(ga&&ga.date?' · au '+dshort(ga.date):'')))}"><div class="av-val"><span class="sc-t" style="color:${gsol(avPos(avObj.score))}">${sign(avObj.score,0)}</span><em class="sc-t" style="color:${gsol(avPos(avObj.score))}">${avObj.label}</em></div></div>
    <div class="duo-sc" title="${accEsc('Sentiment de marché, échelle 0 à 100'+(st?' · moyenne des actifs de la section':(gi&&gi.date?' · au '+dshort(gi.date):'')))}"><div class="ind-val"><span class="sc-t" style="color:${gmir(seObj.value)}">${fmt(seObj.value,0)}</span><em class="sc-t" style="color:${gmir(seObj.value)}">${sLab}</em></div></div></div>
   <div class="ir ir-g">${dualBar(seObj.value,seObj.label,avObj.score,avObj.label,'db-lg db-slim')}</div></div>`;
  const hasDetails=!!(gi&&ga&&ic&&ac&&sl);
  if(hasDetails){
    const info=document.createElement('div');info.className='duo-info';
    const avgTxt=st?`<p class="duo-avg">Le bandeau affiche la moyenne des notes /100 visibles de la section (${st.n} actif${st.n>1?'s':''}), arrondie au point, avec les curseurs AV et S à la moyenne des mêmes actifs. L'historique et les composantes ci-dessous restent ceux de l'indicateur composite de l'onglet.</p>`:'';
    info.innerHTML=`${avgTxt}<div><div class="duo-n"><i class="db-dot db-s">S</i><b>Sentiment de marché, 1 an</b> · ${gi.title||''}</div>
     <div class="ind-date">${(q(sl,'.ind-date')||{}).innerHTML||''}</div>${src(ic)}</div>
    <div><div class="duo-n"><i class="db-dot db-a">AV</i><b>Achat / Vente</b> · indicateur composite APEX</div>
     <div class="ind-date">${(q(ac,'.ind-date')||{}).innerHTML||''}</div>${src(ac)}${(q(ac,'.av-sens')||{}).outerHTML||''}
     </div>
    <p class="duo-scales">Lecture de la barre : deux échelles linéaires distinctes sur la même largeur. Achat / vente de −100 à +100 (graduations au-dessus), curseur « AV » au-dessus de la barre ; sentiment de 0 à 100 (graduations en dessous), curseur « S » sous la barre. Le centre de chaque lettre (et sa petite pointe) marque la valeur exacte. « AV » prend la couleur de la barre à sa position. « S » prend la couleur du dégradé inversé (miroir : couleur de la barre à la position 100 − p), en lecture contrarienne : la peur est une zone d'achat (bleu), l'euphorie une zone de vente (rouge). Toutes les représentations du sentiment suivent ce dégradé miroir : jauge 1 an (barre et curseur), courbe d'historique, barres des composantes. Sur la jauge 1 an : trait blanc = moyenne, cadre = plage min–max sur 1 an, curseur = valeur actuelle.</p>`;
    const col=(t,nodes)=>{const d=document.createElement('div');d.className='duo-col';d.innerHTML=`<div class="duo-ct">${t}</div>`;nodes.filter(Boolean).forEach(n=>d.appendChild(n));return d;};
    const iRest=[...sl.children].filter(n=>!['ind-t','ind-n','ind-badge','ind-val','ind-date'].some(c=>n.classList.contains(c))).concat(sl!==ic?[...ic.children].filter(n=>n!==sl&&n.tagName!=='H2'):[]);
    const aRest=[...ac.children].filter(n=>n.tagName!=='H2'&&!['av-sens','av-val','ind-date'].some(c=>n.classList.contains(c)));
    [...iRest,...aRest].forEach(n=>{if(n.classList&&(n.classList.contains('ind-gauge')))n.insertAdjacentHTML('beforebegin','<div class="duo-pl">Plage sur 1 an (cadre) et moyenne (pointillé)</div>');});
    iRest.forEach(n=>n.classList&&n.classList.contains('ind-gauge')&&(n.classList.add('lt'),n.querySelectorAll('.ind-cur').forEach(c=>{c.classList.add('cur-s');c.style.color=gmir(gi.value);c.textContent='S';})));
    aRest.forEach(n=>n.classList&&n.classList.contains('ind-gauge')&&(n.classList.add('lt'),n.querySelectorAll('.ind-cur').forEach(c=>{c.classList.add('cur-a');c.style.color=gsol(avPos(ga.score));c.textContent='AV';})));
    card.appendChild(accBody([info,col('<i class="db-dot db-s">S</i>Sentiment de marché · historique et composantes',iRest),col('<i class="db-dot db-a">AV</i>Achat / Vente · historique et composantes',aRest)]));
    card.querySelectorAll('.db-dot.db-a').forEach(d=>d.style.color=gsol(avPos(avObj.score)));
    card.querySelectorAll('.db-dot.db-s').forEach(d=>d.style.color=gmir(seObj.value));
  }else if(st){
    const info=document.createElement('div');info.className='duo-info';
    info.innerHTML=`<p class="duo-avg">Le bandeau affiche la moyenne des notes /100 visibles de la section (${st.n} actif${st.n>1?'s':''}), arrondie au point, avec les curseurs AV et S à la moyenne des mêmes actifs. Les repères de marché (sans note) sont exclus.</p>
    <p class="duo-scales">Lecture de la barre : deux échelles linéaires distinctes sur la même largeur. Achat / vente de −100 à +100, curseur « AV » ; sentiment de 0 à 100, curseur « S ». « S » prend la couleur du dégradé miroir (lecture contrarienne).</p>`;
    card.appendChild(accBody([info]));
  }
  D.innerHTML='';D.appendChild(card);if(I)I.innerHTML='';if(A)A.innerHTML='';
  accWire(card,'duo-'+tabId,card.querySelector('.duo-row'));
}
