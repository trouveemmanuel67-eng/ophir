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
function plcEsc(s){
  return String(s==null?'':s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}
function plcMeta(l){
  const parts=[];
  if(l.plafond_libelle) parts.push('Plafond '+l.plafond_libelle);
  else if(l.plafond!=null) parts.push('Plafond '+plcAmt(l.plafond,l.devise||'EUR'));
  if(l.fiscalite) parts.push(l.fiscalite);
  if(l.eligibilite) parts.push(l.eligibilite);
  if(l.garantie_libelle||l.garantie) parts.push('Garantie : '+(l.garantie_libelle||l.garantie));
  if(l.liquide_txt) parts.push(l.liquide_txt);
  return parts.join(' · ');
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
function plcRow(l){
  const meta=plcMeta(l);
  return `<article class="plc-row">
      <span class="plc-et">${plcEsc(l.etablissement||'—')}</span>
      <span class="plc-nm">${plcEsc(plcNom(l))}</span>
      <b class="plc-solde">${plcAmt(l.solde,l.devise)}</b>
      <span class="plc-taux">${plcEsc(plcTaux(l))}</span>
      <span class="plc-apex" title="${l.apex10&&l.apex10.decomp?String(l.apex10.decomp.texte).replace(/"/g,''):'Note APEX non calculée'}">${typeof apexNoteHTML==='function'?apexNoteHTML(l.apex10):''}</span>
      ${meta?`<span class="plc-meta">${plcEsc(meta)}</span>`:''}
      ${l.apex10&&l.apex10.decomp?`<span class="plc-dec">Note APEX : ${plcEsc(l.apex10.decomp.texte)}</span>`:''}
    </article>`;
}
function plcSrcFooter(){
  const R=PLC.reglementes||{};
  const srcs=(R.sources||[]).map(s=>{
    const d=s.date?(' ('+s.date+(s.mise_a_jour?(', màj '+s.mise_a_jour):'')+')'):'';
    if(s.url&&/^https?:\/\//i.test(s.url)) return `<a href="${plcEsc(s.url)}" target="_blank" rel="noopener noreferrer">${plcEsc(s.nom)}</a>${plcEsc(d)}`;
    return plcEsc((s.nom||'')+d);
  });
  const bits=[];
  if(R.verifie_libelle) bits.push('Épargne réglementée vérifiée le '+R.verifie_libelle);
  if(PLC.source) bits.push(PLC.source);
  const head=bits.join(' · ');
  const list=srcs.length?(' Sources : '+srcs.join(' ; ')+'.'):'';
  return `<div class="src">${head?plcEsc(head)+'.':''}${list}</div>`;
}
function renderPlacements(el){
  const L=Array.isArray(PLC.lignes)?PLC.lignes:[];
  const date=PLC.releve_libelle||PLC.generated||'';
  const reg=L.filter(l=>l.type==='reglemente');
  const autres=L.filter(l=>l.type!=='reglemente');
  const block=(title, arr)=>!arr.length?'':`<h3 class="plc-h">${plcEsc(title)}</h3>
    <div class="plc-colh" aria-hidden="true"><span>Établissement</span><span>Placement</span><span>Solde</span><span>Taux</span><span>Note APEX</span></div>
    <div class="plc-list">${arr.map(plcRow).join('')}</div>`;
  const tot=plcTotaux(L);
  const vreg=PLC.reglementes&&PLC.reglementes.verifie_libelle;
  el.innerHTML=`<div class="card no-group no-acc" id="plcCard">
    <h2>Placements</h2>
    <div class="desc">${vreg?`Épargne réglementée : taux en vigueur au ${plcEsc(vreg)}. `:''}${date?`Relevé détenu : ${plcEsc(date)}.`:''}${L.length?` ${L.length} ligne${L.length>1?'s':''}.`:''}</div>
    ${block('Épargne réglementée', reg)}
    ${block('Détenu', autres)}
    ${(!reg.length&&!autres.length)?'<div class="note">Aucun placement enregistré.</div>':''}
    ${tot?`<div class="plc-tot"><span>Total</span><b>${tot}</b></div>`:''}
    <div class="note">Note APEX épargne (−50 à 250) : contexte de taux 110 + fondamental épargne 90 (taux réel net d'impôt, garantie, disponibilité, change, frais) + sentiment Liquidités APEX inversé ±50. Produits exonérés : taux net = brut. Détail dans l'onglet Liquidités et la page Règles.</div>
    ${plcSrcFooter()}
  </div>`;
}
