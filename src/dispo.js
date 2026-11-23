/* ===== Disponibilité Revolut / XTB sur chaque fiche (data/disponibilites.json) =====
   Badge : Revolut et/ou XTB au comptant (OMI, pas CFD). */
const DISPO=(()=>{try{return JSON.parse(document.getElementById('data12').textContent);}catch(e){return {symbols:{}};}})();
function dispoOf(tv){
  if(!tv||!DISPO||!DISPO.symbols) return null;
  return DISPO.symbols[tv]||null;
}
function dispoBadge(tv){
  const d=dispoOf(tv); if(!d) return '';
  const r=d.revolut, x=d.xtb;
  let lab='', cls='dispo-badge';
  if(r===true && x===true){ lab='Revolut et XTB'; cls+=' dispo-both'; }
  else if(r===true){ lab='Revolut'; }
  else if(x===true){ lab='XTB'; cls+=' dispo-xtb'; }
  else if(r===false && x===false){ lab=d.badge||'ni Revolut ni XTB'; cls+=' dispo-none'; }
  else if(r===null && x===false){ lab=d.badge||'à vérifier Revolut'; cls+=' dispo-verif'; }
  else if(r===false && x===null){ lab=d.badge||'à vérifier XTB'; cls+=' dispo-verif'; }
  else if(d.note||r===null||x===null){ lab=d.badge||'à vérifier Revolut/XTB'; cls+=' dispo-verif'; }
  else return '';
  const tip=(d.note||'').replace(/"/g,'&quot;');
  return `<span class="${cls}"${tip?` title="${tip}"`:''}>${lab}</span>`;
}
