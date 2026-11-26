/* ===== Onglet PEA : ETF à rendement éligibles, projection 200 €/mois ===== */
const PEA=(()=>{try{return JSON.parse(document.getElementById('dataPea').textContent);}catch(e){return {etfs:[],projection:{scenarios:[]}};} })();

function peaEsc(s){
  return String(s==null?'':s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}
function peaEur(v,dec){
  const n=Number(v);
  if(!Number.isFinite(n)) return '—';
  const d=dec==null?0:dec;
  return n.toLocaleString('fr-FR',{minimumFractionDigits:d,maximumFractionDigits:d})+'\u00a0€';
}
function peaPct(v,dec){
  const n=Number(v);
  if(!Number.isFinite(n)) return '—';
  const d=dec==null?2:dec;
  return n.toLocaleString('fr-FR',{minimumFractionDigits:d,maximumFractionDigits:d})+'\u00a0%';
}
function peaFv(monthly, ratePa, months){
  const p=Number(monthly), r=Number(ratePa), n=Number(months);
  if(!Number.isFinite(p)||!Number.isFinite(r)||!Number.isFinite(n)||n<=0) return NaN;
  const i=r/12;
  if(Math.abs(i)<1e-15) return p*n;
  return p*((Math.pow(1+i,n)-1)/i);
}
function peaPol(e){
  if(e.politique==='capitalisation') return 'Cap.';
  if(e.politique==='distribution'){
    if(e.frequence==='annuelle') return 'Dist. / an';
    if(e.frequence==='semestrielle') return 'Dist. / 6 mois';
    if(e.frequence==='trimestrielle') return 'Dist. / trim.';
    return 'Dist.';
  }
  return '—';
}
function peaRow(e,i){
  const yld=e.rendement_actuel_pct==null?'Cap.':peaPct(e.rendement_actuel_pct);
  const xtb=e.xtb+(e.xtb_alt?(' ou '+e.xtb_alt):'');
  const meta=[
    e.isin,
    'XTB '+xtb,
    e.encours_meur!=null?(Number(e.encours_meur).toLocaleString('fr-FR')+'\u00a0M€'):null,
    e.replication,
    e.note
  ].filter(Boolean).join(' · ');
  return `<article class="pea-row">
    <span class="pea-rk">${i+1}</span>
    <span class="pea-nm">${peaEsc(e.nom)}</span>
    <b class="pea-yld" title="Rendement de distribution actuel (justETF)">${peaEsc(yld)}</b>
    <span class="pea-ter">TER ${peaPct(e.ter_pct)}</span>
    <span class="pea-pol">${peaEsc(peaPol(e))}</span>
    <span class="pea-meta">${peaEsc(meta)}</span>
  </article>`;
}
function peaScenCard(s, capital){
  const cap=capital!=null?capital:s.capital_eur;
  return `<div class="pea-sc" data-id="${peaEsc(s.id)}">
    <span class="pea-sc-nom">${peaEsc(s.nom)}</span>
    <b class="pea-sc-cap">${peaEur(cap)}</b>
    <span class="pea-sc-tx">${peaPct(s.taux_pa_pct,1)} / an</span>
    <span class="pea-sc-why">${peaEsc(s.justification||'')}</span>
  </div>`;
}
function peaBind(el){
  const P=PEA.projection||{};
  const inp=el.querySelector('#peaTaux');
  const out=el.querySelector('#peaCustom');
  const monthly=Number(P.versement_mensuel_eur||200);
  const months=Number(P.n_versements||60);
  const upd=()=>{
    if(!inp||!out) return;
    const raw=String(inp.value||'').replace(',','.');
    const r=Number(raw)/100;
    if(!Number.isFinite(r)||r<=-1||r>0.5){
      out.textContent='Taux invalide';
      return;
    }
    const cap=peaFv(monthly,r,months);
    out.innerHTML='À <b>'+peaPct(r*100,1)+'</b> / an : <b>'+peaEur(cap)+'</b>';
  };
  if(inp){
    inp.addEventListener('input',upd);
    inp.addEventListener('change',upd);
    upd();
  }
}
function renderPea(el){
  const L=Array.isArray(PEA.etfs)?PEA.etfs.slice(0,10):[];
  const P=PEA.projection||{};
  const sc=Array.isArray(P.scenarios)?P.scenarios:[];
  const defTx=(sc.find(s=>s.id==='central')||sc[0]||{}).taux_pa_pct;
  el.innerHTML=`<div class="card pea-card">
    <h2>ETF à rendement · PEA XTB</h2>
    <p class="pea-intro">${peaEsc(PEA.intro||'')}</p>
    <div class="pea-colh" aria-hidden="true"><span>#</span><span>Fonds</span><span>Rendement</span><span>Frais</span><span>Versement</span></div>
    <div class="pea-list">${L.map(peaRow).join('')}</div>
    <p class="pea-class">${peaEsc(PEA.classement_libelle||'')}</p>
    <div class="src">${peaEsc(PEA.xtb_avertissement||'')}</div>
  </div>
  <div class="card pea-card pea-proj">
    <h2>Projection ${peaEur(P.versement_mensuel_eur||200)}/mois sur ${P.duree_ans||5}\u00a0ans</h2>
    <div class="pea-kpis">
      <div><span>Versé</span><b>${peaEur(P.total_verse_eur||12000)}</b><small>${P.n_versements||60} versements</small></div>
      <div><span>PEA</span><b>5\u00a0ans</b><small>Avantage fiscal</small></div>
      <div><span>Plafond</span><b>150\u00a0000\u00a0€</b><small>versements</small></div>
    </div>
    <div class="pea-scs">${sc.map(s=>peaScenCard(s)).join('')}</div>
    <label class="pea-taux">Taux annuel
      <input id="peaTaux" type="number" inputmode="decimal" min="-20" max="50" step="0.1" value="${peaEsc(defTx==null?7:defTx)}"> %
    </label>
    <div id="peaCustom" class="pea-custom"></div>
    <p class="pea-just">${peaEsc(P.justification||'')}</p>
    <p class="pea-warn">${peaEsc(P.avertissement||'')} ${peaEsc(PEA.pea_regles||'')}</p>
    <div class="src">Sources : justETF (26/11/2026) · table OMI XTB France (24/09/2026) · Yahoo Finance pour les rythmes 5 ans et 10 ans (26/11/2026). ${peaEsc(P.mode_libelle||'')}</div>
  </div>`;
  peaBind(el);
}
