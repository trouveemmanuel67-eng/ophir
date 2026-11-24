/* ===== Onglet Placements : comptes d'épargne et fonds monétaires (extensible) ===== */
const PLC=(()=>{try{return JSON.parse(document.getElementById('data17').textContent);}catch(e){return {lignes:[]};}})();

function plcAmt(v, ccy){
  const n=Number(v);
  if(!Number.isFinite(n)) return '—';
  const s=n.toLocaleString('fr-FR',{minimumFractionDigits:2,maximumFractionDigits:2});
  if(ccy==='EUR') return s+'\u00a0€';
  if(ccy==='USD') return s+'\u00a0$';
  return s+'\u00a0'+ccy;
}
function plcTaux(l){
  if(l.taux_libelle) return l.taux_libelle;
  if(l.taux==null||!Number.isFinite(Number(l.taux))) return '—';
  const t=Number(l.taux).toLocaleString('fr-FR',{minimumFractionDigits:2,maximumFractionDigits:2})+'\u00a0%';
  return l.taux_type==='apy'?t+" d'APY":l.taux_type==='brut'?t+' brut':t;
}
function plcNom(l){
  const base=l.nom||'—';
  return l.complement?base+' ('+l.complement+')':base;
}
function plcTotaux(lignes){
  const by={};
  (lignes||[]).forEach(l=>{
    const c=l.devise||'';
    if(!c||!Number.isFinite(Number(l.solde))) return;
    by[c]=(by[c]||0)+Number(l.solde);
  });
  const order=['EUR','USD'];
  const keys=order.filter(k=>k in by).concat(Object.keys(by).filter(k=>!order.includes(k)).sort());
  return keys.map(k=>plcAmt(by[k],k)).join(' \u00b7 ');
}
function renderPlacements(el){
  const L=Array.isArray(PLC.lignes)?PLC.lignes:[];
  const date=PLC.releve_libelle||PLC.generated||'';
  const rows=L.map(l=>`<article class="plc-row">
      <span class="plc-et">${(l.etablissement||'—').replace(/</g,'')}</span>
      <span class="plc-nm">${plcNom(l).replace(/</g,'')}</span>
      <b class="plc-solde">${plcAmt(l.solde,l.devise)}</b>
      <span class="plc-taux">${plcTaux(l)}</span>
      <span class="plc-apex" title="${l.apex10&&l.apex10.decomp?String(l.apex10.decomp.texte).replace(/"/g,''):'Note APEX non calculée'}">${typeof apexNoteHTML==='function'?apexNoteHTML(l.apex10):''}</span>
      ${l.apex10&&l.apex10.decomp?`<span class="plc-dec">Note APEX : ${String(l.apex10.decomp.texte).replace(/</g,'')}</span>`:''}
    </article>`).join('')||'<div class="note">Aucun placement enregistré.</div>';
  const tot=plcTotaux(L);
  el.innerHTML=`<div class="card no-group no-acc" id="plcCard">
    <h2>Placements</h2>
    <div class="desc">Relevé du ${date||'—'}.${L.length?` ${L.length} ligne${L.length>1?'s':''}.`:''}</div>
    <div class="plc-colh" aria-hidden="true"><span>Établissement</span><span>Placement</span><span>Solde</span><span>Taux</span><span>Note APEX</span></div>
    <div class="plc-list">${rows}</div>
    ${tot?`<div class="plc-tot"><span>Total</span><b>${tot}</b></div>`:''}
    <div class="note">Note APEX épargne (−50 à 250) : contexte de taux 110 + fondamental épargne 90 (taux réel net d'impôt, garantie, disponibilité, change, frais) + sentiment Liquidités APEX inversé ±50 (remplace le CNN global). Détail dans l'onglet Liquidités et la page Règles.</div>
    <div class="src">Source : ${PLC.source||('relevé du '+date)}</div>
  </div>`;
}
