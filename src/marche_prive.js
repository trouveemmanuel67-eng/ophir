/* ===== Onglet Marché privé : fonds ELTIF Revolut, note APEX ===== */
const MP=(()=>{try{return JSON.parse(document.getElementById('dataMarchePrive').textContent);}catch(e){return {fonds:[]};}})();

function mpEsc(s){
  return String(s==null?'':s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}
function mpMeur(v){
  if(v==null||v==='') return 'n.c.';
  const n=Number(v);
  if(!Number.isFinite(n)) return 'n.c.';
  return n.toLocaleString('fr-FR',{maximumFractionDigits:n>=100?0:2})+'\u00a0M€';
}
function mpPct(v){
  const n=Number(v);
  if(!Number.isFinite(n)) return 'n.c.';
  return n.toLocaleString('fr-FR',{minimumFractionDigits:1,maximumFractionDigits:1})+'\u00a0%';
}
function mpNote(a){
  const tip=a&&(a.ligne||(a.decomp&&a.decomp.texte))?mpEsc(a.ligne||a.decomp.texte):'Note APEX non calculée';
  const html=(typeof apexNoteHTML==='function')?apexNoteHTML(a):'<div class="apex10 apex10-pilot apex10-na"><b>–</b><small>/ 250</small></div>';
  return `<span class="mp-apex" title="${tip}">${html}</span>`;
}
function mpRachat(f){
  const t=(f.liquidite||'').toLowerCase();
  if(t.indexOf('mensuel')===0||t.indexOf('rachats mensuels')>=0) return 'Mensuel';
  if(t.indexOf('trimestriel')>=0) return 'Trimestriel';
  return 'n.c.';
}
function mpCard(f){
  const a=f.apex10||{};
  const manq=(f.infos_manquantes||[]).map(x=>`<li>${mpEsc(x)}</li>`).join('');
  const crit=((((a.decomp||{}).fondamental)||{}).criteres)||[];
  const rows=crit.map(c=>{
    const et=c.etat==='n.c.'?' n.c.':'';
    return `<li><b>${mpEsc(c.label)}</b> ${c.points}/${c.max}${et}</li>`;
  }).join('');
  const isin=f.isin?`<span class="mp-isin">${mpEsc(f.isin)}</span>`:'';
  return `<article class="mp-card">
    <div class="mp-top">
      <div class="mp-id">
        <h3>${mpEsc(f.nom)}</h3>
        <span class="mp-type">${mpEsc(f.type)}</span>
      </div>
      ${mpNote(a)}
    </div>
    <div class="mp-kpis">
      <div><span>Frais / an</span><b>${mpEsc(mpPct(f.frais_annuels_pct))}</b></div>
      <div><span>Encours</span><b>${mpEsc(mpMeur(f.encours_meur))}</b></div>
      <div><span>Rachats</span><b>${mpEsc(mpRachat(f))}</b></div>
      <div><span>Risque</span><b>${f.sri!=null?(f.sri+'/7'):'n.c.'}</b></div>
    </div>
    <details class="mp-det">
      <summary>Détail</summary>
      <p class="mp-meta">${isin}${f.part?(' · '+mpEsc(f.part)):''}${f.nom_officiel?('<br>'+mpEsc(f.nom_officiel)):''}</p>
      <p class="mp-ligne">${mpEsc(a.ligne||(a.decomp&&a.decomp.texte)||'')}</p>
      <ul class="mp-crit">${rows}</ul>
      ${manq?`<p class="mp-k">Infos manquantes (0 point)</p><ul class="mp-miss">${manq}</ul>`:''}
      ${f.rendement_distribue?`<p class="mp-t">${mpEsc(f.rendement_distribue)}</p>`:''}
    </details>
  </article>`;
}
function renderMarchePrive(el){
  const L=Array.isArray(MP.fonds)?MP.fonds.slice():[];
  const risques=(MP.risques||[]).map(x=>`<li>${mpEsc(x)}</li>`).join('');
  el.innerHTML=`<div class="card mp-wrap no-acc">
    <h2>${mpEsc(MP.titre||'Marché privé')}</h2>
    <p class="mp-intro">${mpEsc(MP.intro||'')}</p>
    <div class="mp-list">${L.map(mpCard).join('')}</div>
    <ul class="mp-risques">${risques}</ul>
    <p class="mp-legende">${mpEsc(MP.note_legende||'')}</p>
    <p class="src">${mpEsc(MP.revolut||'')}</p>
  </div>`;
}
