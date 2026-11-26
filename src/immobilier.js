/* ===== Onglet Immobilier : prévisionnel d'achat à contre-courant ===== */
const IMMO=(()=>{try{return JSON.parse(document.getElementById('dataImmo').textContent);}catch(e){return null;}})();

function immoEsc(s){
  return String(s==null?'':s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}
function immoEur(v){
  const n=Number(v);
  if(!Number.isFinite(n)) return '—';
  return Math.round(n).toLocaleString('fr-FR')+'\u00a0€';
}
function immoPct(v,dec){
  const n=Number(v);
  if(!Number.isFinite(n)) return '—';
  const d=dec==null?0:dec;
  return n.toLocaleString('fr-FR',{minimumFractionDigits:d,maximumFractionDigits:d})+'\u00a0%';
}
function immoTaux(v){
  const n=Number(v);
  if(!Number.isFinite(n)) return '—';
  return n.toLocaleString('fr-FR',{minimumFractionDigits:2,maximumFractionDigits:2})+'\u00a0%';
}
function immoCourt(periode){
  const m=/^(\d{4})-S([12])$/.exec(periode||'');
  if(!m) return periode||'';
  return m[1].slice(2)+'\u00a0S'+m[2];
}

function immoFrise(bien){
  const best=bien.meilleure_periode;
  return `<div class="immo-frise" role="img" aria-label="Note d'opportunité par semestre, de 2027 à 2031.">${(bien.frise||[]).map(p=>{
    const on=p.periode===best?' on':'';
    const tip=immoEsc(`${p.label} · note ${p.note}/250 · ${immoPct(p.proba_pct,1)} de chance d’être la meilleure fenêtre`);
    return `<span class="immo-frise-i${on}" style="background:${p.hex||'#ff8c1a'}" title="${tip}"><i>${immoEsc(immoCourt(p.periode))}</i></span>`;
  }).join('')}</div>`;
}

function immoCarte(bien){
  if(!bien) return '';
  const id=immoEsc(bien.id);
  const proba=immoPct(bien.meilleure_proba_pct,0);
  return `<article class="immo-card" data-immo-id="${id}" style="--immo:${bien.meilleure_hex||'#22c55e'}">
    <div class="immo-top">
      <h3>${immoEsc(bien.titre)}</h3>
      <span class="immo-note" title="Note d'opportunité APEX à la meilleure fenêtre (mélange des 3 scénarios)">${bien.meilleure_note}<small>/250</small></span>
    </div>
    <button type="button" class="immo-fig" data-immo-id="${id}" aria-expanded="false" aria-label="Meilleure fenêtre ${immoEsc(bien.meilleure_label)}, ${proba}. Afficher les hypothèses.">
      <span class="immo-win">${immoEsc(bien.meilleure_label)}</span>
      <span class="immo-proba" style="color:${bien.meilleure_hex||'#22c55e'}">${proba}</span>
      <span class="immo-fig-l">Meilleure fenêtre · probabilité</span>
    </button>
    ${immoFrise(bien)}
    <div class="immo-kpis">
      <div><span>Prix au m²</span><b>${immoEur(bien.prix_m2_actuel)}</b></div>
      <div><span>Taux 25 ans</span><b>${immoTaux(bien.taux_actuel_25a)}</b></div>
      <div><span>Budget max</span><b>${immoEur(bien.budget_accessible_actuel)}</b></div>
    </div>
    <p class="immo-resume">${immoEsc(bien.resume)}</p>
  </article>`;
}

function immoPopHtml(bien){
  if(!bien||!IMMO) return '';
  const scens=bien.scenarios||{};
  const ordre=['baisse','statu_quo','remontee'];
  const lignes=ordre.map(k=>{
    const s=scens[k]; if(!s) return '';
    return `<tr><td>${immoEsc(s.label)}</td><td>${immoEsc(s.meilleure_label)}</td><td>${immoPct(s.meilleure_proba_pct,1)}</td><td>${s.meilleure_note}/250</td></tr>`;
  }).join('');
  const pts=(IMMO.methode&&IMMO.methode.poids)||{};
  const refs=bien.id==='ferme'?(IMMO.references||{}).ferme:(IMMO.references||{}).appart_4p;
  let refLigne='';
  if(bien.id==='ferme'&&refs){
    refLigne=`Bien typique : ${immoEur(refs.prix_median_2025)} (maison ancienne médiane, ${refs.surface_m2}\u00a0m², terrain ${refs.terrain_m2}\u00a0m², secteur ${immoEsc(refs.secteur)}, 2025). Mensualité actuelle : ${immoEur(bien.mensualite_typique_actuelle)} hors assurance.`;
  }else if(refs){
    refLigne=`Bien typique : ${immoEur(refs.prix_typique)} pour ${refs.surface_typique_m2}\u00a0m² à ${immoEur(refs.moyenne_zone_m2)}/m² (moyenne de 6 communes). Cœur Schiltigheim–Bischheim–Hoenheim : ${immoEur(refs.moyenne_coeur_m2)}/m². Mensualité actuelle : ${immoEur(bien.mensualite_typique_actuelle)} hors assurance.`;
  }
  const src=(IMMO.sources||[]).slice(0,8).map(s=>`<li><a href="${immoEsc(s.url)}" target="_blank" rel="noopener noreferrer">${immoEsc(s.titre)}</a></li>`).join('');
  const lim=(IMMO.limites||[]).slice(0,4).map(x=>`<li>${immoEsc(x)}</li>`).join('');
  const cons=IMMO.constats||{};
  return `<p class="immo-pop-h">Hypothèses et scénarios</p>
    <p class="immo-t">${immoEsc(IMMO.avertissement||'')}</p>
    <p class="immo-k">Les 3 scénarios de taux</p>
    <table class="immo-tab"><thead><tr><th>Scénario</th><th>Meilleure fenêtre</th><th>Proba.</th><th>Note</th></tr></thead><tbody>${lignes}</tbody></table>
    <p class="immo-t">Le mélange donne le même poids aux trois. Crédit Logement/CSA (octobre 2026) penche plutôt vers une remontée des taux en 2027.</p>
    <p class="immo-k">Score sur 250</p>
    <p class="immo-t">Prix ${pts.prix||70} · mensualité ${pts.accessibilite||60} · volumes ${pts.volume||50} · négociation ${pts.marge||40} · DPE ${pts.dpe||30}. Lecture à contre-courant : plus de points quand peu de gens veulent acheter.</p>
    <p class="immo-k">Bien typique et budget</p>
    <p class="immo-t">${immoEsc(refLigne)} Budget max à 1\u00a0500\u00a0€/mois sur 25 ans, aujourd’hui ${immoEur(bien.budget_accessible_actuel)}, autour de la meilleure fenêtre ${immoEur(bien.budget_accessible_fenetre)} (de ${immoEur(bien.budget_accessible_fenetre_min)} à ${immoEur(bien.budget_accessible_fenetre_max)} selon le scénario). Hors assurance, hors frais d’achat, hors travaux.</p>
    ${bien.id==='ferme'&&cons.dpe?`<p class="immo-t">${immoEsc(cons.dpe)}</p>`:''}
    <p class="immo-k">Saison</p>
    <p class="immo-t">${immoEsc((IMMO.methode&&IMMO.methode.saison)||'En général, l’hiver (novembre à février) se négocie mieux.')}</p>
    <p class="immo-k">Limites</p>
    <ul class="immo-ul">${lim}</ul>
    <p class="immo-k">Sources</p>
    <ul class="immo-ul immo-src">${src}</ul>`;
}

function immoPlacePop(btn){
  const pop=document.getElementById('immoPop');
  if(!pop||!btn) return;
  const r=btn.getBoundingClientRect();
  const vw=window.innerWidth, vh=window.innerHeight;
  const maxW=Math.min(440, vw-16);
  pop.style.visibility='hidden';
  pop.hidden=false;
  pop.style.width=maxW+'px';
  pop.style.maxWidth=maxW+'px';
  pop.style.maxHeight=Math.min(520, vh-24)+'px';
  const pr=pop.getBoundingClientRect();
  let left=Math.min(Math.max(8, r.left), vw-pr.width-8);
  let top=r.bottom+8;
  if(top+pr.height>vh-8){
    top=Math.max(8, r.top-pr.height-8);
  }
  if(top+pr.height>vh-8){
    top=Math.max(8, (vh-pr.height)/2);
  }
  pop.style.left=left+'px';
  pop.style.top=top+'px';
  pop.style.visibility='visible';
}

function immoHidePop(){
  const pop=document.getElementById('immoPop');
  if(pop){ pop.hidden=true; pop.innerHTML=''; pop.removeAttribute('data-immo-for'); }
  document.querySelectorAll('.immo-fig[aria-expanded="true"]').forEach(b=>b.setAttribute('aria-expanded','false'));
}

function immoShowPop(btn, pin){
  if(!IMMO||!btn) return;
  const id=btn.getAttribute('data-immo-id');
  const bien=(IMMO.biens||{})[id];
  if(!bien) return;
  const pop=document.getElementById('immoPop');
  if(!pop) return;
  const already=btn.getAttribute('aria-expanded')==='true' && pop.getAttribute('data-immo-for')===id;
  if(pin && already && pop._pinned){ immoHidePop(); pop._pinned=false; return; }
  document.querySelectorAll('.immo-fig[aria-expanded="true"]').forEach(b=>{ if(b!==btn) b.setAttribute('aria-expanded','false'); });
  btn.setAttribute('aria-expanded','true');
  pop.innerHTML=immoPopHtml(bien);
  pop.setAttribute('data-immo-for', id);
  pop._pinned=!!pin;
  immoPlacePop(btn);
}

function immoBind(root){
  if(!root||root._immoBound) return;
  root._immoBound=true;
  let pop=document.getElementById('immoPop');
  if(!pop){
    pop=document.createElement('div');
    pop.id='immoPop';
    pop.className='immo-pop';
    pop.hidden=true;
    pop.setAttribute('role','dialog');
    document.body.appendChild(pop);
  }
  root.querySelectorAll('.immo-fig').forEach(btn=>{
    btn.addEventListener('mouseenter',()=>{ if(!window.matchMedia('(hover:hover) and (pointer:fine)').matches) return; immoShowPop(btn,false); });
    btn.addEventListener('mouseleave',e=>{
      const popEl=document.getElementById('immoPop');
      if(popEl&&popEl._pinned) return;
      const to=e.relatedTarget;
      if(to&&(popEl.contains(to)||btn.contains(to))) return;
      immoHidePop();
    });
    btn.addEventListener('click',e=>{ e.preventDefault(); immoShowPop(btn,true); });
  });
  pop.addEventListener('mouseleave',()=>{ if(!pop._pinned) immoHidePop(); });
  if(!document._immoDoc){
    document._immoDoc=true;
    document.addEventListener('click',e=>{
      if(e.target.closest('.immo-fig')||e.target.closest('#immoPop')) return;
      immoHidePop();
    });
    document.addEventListener('keydown',e=>{ if(e.key==='Escape') immoHidePop(); });
    window.addEventListener('resize',()=>{
      const popEl=document.getElementById('immoPop');
      if(!popEl||popEl.hidden) return;
      const id=popEl.getAttribute('data-immo-for');
      const btn=document.querySelector('.immo-fig[data-immo-id="'+id+'"]');
      if(btn) immoPlacePop(btn);
    },{passive:true});
  }
}

function blocImmoPrev(){
  if(!IMMO||!IMMO.biens) return '';
  const f=IMMO.biens.ferme, a=IMMO.biens.appart;
  return `<div class="card immo-prev no-acc no-group" id="immoPrev">
    <h2>Quand chercher à acheter</h2>
    <p class="immo-intro">Meilleure fenêtre d’ici fin 2031, à contre-courant. Estimation, pas une certitude. Le détail s’affiche au survol ou au toucher.</p>
    <div class="immo-grid">${immoCarte(f)}${immoCarte(a)}</div>
    <p class="immo-saison">Dans l’année, l’hiver (novembre à février) se négocie en général mieux, quelle que soit la fenêtre. ${IMMO.contrainte&&IMMO.contrainte.apport?immoEsc(IMMO.contrainte.apport):''}</p>
  </div>`;
}
function immoInit(root){
  if(!root) return;
  immoBind(root);
}
