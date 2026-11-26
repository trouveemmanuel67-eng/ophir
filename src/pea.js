/* ===== Onglet PEA : ETF à rendement éligibles, note APEX, projection 200 €/mois ===== */
const PEA=(()=>{try{return JSON.parse(document.getElementById('dataPea').textContent);}catch(e){return {etfs:[],projection:{}};} })();

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
function peaSigneEur(v,dec){
  const n=Number(v);
  if(!Number.isFinite(n)) return '—';
  const d=dec==null?0:dec;
  const s=(n>0?'+':(n<0?'−':''));
  return s+Math.abs(n).toLocaleString('fr-FR',{minimumFractionDigits:d,maximumFractionDigits:d})+'\u00a0€';
}
function peaSignePct(v,dec){
  const n=Number(v);
  if(!Number.isFinite(n)) return '—';
  const d=dec==null?1:dec;
  const s=(n>0?'+':(n<0?'−':''));
  return s+Math.abs(n).toLocaleString('fr-FR',{minimumFractionDigits:d,maximumFractionDigits:d})+'\u00a0%';
}
/* Taux mensuel équivalent au taux annuel : i = (1+r)^(1/12) − 1. Annuité de fin de mois. */
function peaFv(monthly, ratePa, months){
  const p=Number(monthly), r=Number(ratePa), n=Number(months);
  if(!Number.isFinite(p)||!Number.isFinite(r)||!Number.isFinite(n)||n<=0) return NaN;
  const i=Math.pow(1+r,1/12)-1;
  if(Math.abs(i)<1e-15) return p*n;
  return p*((Math.pow(1+i,n)-1)/i);
}
function peaIMensuel(ratePa){
  const r=Number(ratePa);
  if(!Number.isFinite(r)) return NaN;
  return Math.pow(1+r,1/12)-1;
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
function peaNote(e){
  const a=e&&e.apex10;
  const tip=a&&(a.ligne||(a.decomp&&a.decomp.texte))?peaEsc(a.ligne||a.decomp.texte):'Note APEX non calculée';
  const html=(typeof apexNoteHTML==='function')?apexNoteHTML(a):'<div class="apex10 apex10-pilot apex10-na"><b>–</b><small>/ 250</small></div>';
  return `<span class="pea-apex" title="${tip}">${html}</span>`;
}
function peaRow(e,i){
  const yld=e.rendement_actuel_pct==null?'Cap.':peaPct(e.rendement_actuel_pct);
  const xtb=e.xtb+(e.xtb_alt?(' ou '+e.xtb_alt):'');
  const meta=[
    e.isin,
    'XTB '+xtb,
    e.encours_meur!=null?(Number(e.encours_meur).toLocaleString('fr-FR')+'\u00a0M€'):null
  ].filter(Boolean).join(' · ');
  const tip=e.note||(e.apex10&&(e.apex10.ligne||(e.apex10.decomp&&e.apex10.decomp.texte)))||'';
  return `<article class="pea-row"${tip?(' title="'+peaEsc(tip)+'"'):''}>
    <span class="pea-rk">${i+1}</span>
    <span class="pea-nm">${peaEsc(e.nom)}</span>
    <b class="pea-yld" title="Rendement de distribution actuel (justETF)">${peaEsc(yld)}</b>
    <span class="pea-ter">TER ${peaPct(e.ter_pct)}</span>
    <span class="pea-pol">${peaEsc(peaPol(e))}</span>
    ${peaNote(e)}
    <span class="pea-meta">${peaEsc(meta)}</span>
  </article>`;
}
function peaSet(el,id,text){
  const n=el.querySelector('#'+id);
  if(n) n.textContent=text;
}
function peaBind(el){
  const P=PEA.projection||{};
  const inp=el.querySelector('#peaTaux');
  const monthly=Number(P.versement_mensuel_eur||200);
  const upd=()=>{
    if(!inp) return;
    const raw=String(inp.value||'').replace(',','.');
    const rPct=Number(raw);
    const r=rPct/100;
    if(!Number.isFinite(r)||r<=-1||r>0.5){
      peaSet(el,'peaIm','—');
      peaSet(el,'peaC1','—');
      peaSet(el,'peaC5','—');
      peaSet(el,'peaG1','Taux invalide');
      peaSet(el,'peaG5','Taux invalide');
      return;
    }
    const i=peaIMensuel(r);
    const c1=peaFv(monthly,r,12);
    const c5=peaFv(monthly,r,60);
    const v1=monthly*12, v5=monthly*60;
    peaSet(el,'peaIm',peaPct(i*100,2));
    peaSet(el,'peaC1',peaEur(c1,0));
    peaSet(el,'peaC5',peaEur(c5,0));
    peaSet(el,'peaG1',peaSigneEur(c1-v1,0)+' · '+peaSignePct(100*(c1-v1)/v1,1)+'  ·  versé '+peaEur(v1,0));
    peaSet(el,'peaG5',peaSigneEur(c5-v5,0)+' · '+peaSignePct(100*(c5-v5)/v5,1)+'  ·  versé '+peaEur(v5,0));
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
  const defTx=P.taux_defaut_pct!=null?P.taux_defaut_pct:7;
  el.innerHTML=`<div class="card pea-card no-acc">
    <h2>ETF à rendement · PEA XTB</h2>
    <p class="pea-intro">${peaEsc(PEA.intro||'')}</p>
    <div class="pea-colh" aria-hidden="true"><span>#</span><span>Fonds</span><span>Rendement</span><span>Frais</span><span>Versement</span><span>Note</span></div>
    <div class="pea-list">${L.map(peaRow).join('')}</div>
    <p class="pea-legende">${peaEsc(PEA.note_legende||'')}</p>
    <div class="src">${peaEsc(PEA.xtb_avertissement||'')}</div>
  </div>
  <div class="card pea-card pea-proj no-acc">
    <h2>Projection ${peaEur(P.versement_mensuel_eur||200)}/mois sur ${P.duree_ans||5}\u00a0ans</h2>
    <div class="pea-vers">
      <div><span>Mensuel</span><b>${peaEur(P.versement_mensuel_eur||200)}</b></div>
      <div><span>Annualisé</span><b>${peaEur(P.versement_annuel_eur||2400)}</b></div>
    </div>
    <div class="pea-rates">
      <div>
        <span>Rendement annuel</span>
        <label class="pea-taux"><input id="peaTaux" type="number" inputmode="decimal" min="-20" max="50" step="0.1" value="${peaEsc(defTx)}"> %</label>
      </div>
      <div><span>Rendement mensuel équivalent</span><b id="peaIm"></b></div>
    </div>
    <div class="pea-horiz">
      <div><span>Capital à 1 an</span><b id="peaC1"></b><small id="peaG1"></small></div>
      <div><span>Capital à 5 ans</span><b id="peaC5"></b><small id="peaG5"></small></div>
    </div>
    <p class="pea-warn">${peaEsc(P.avertissement||'Estimation, aucun rendement garanti, risque de perte en capital')}</p>
  </div>`;
  peaBind(el);
}
