/* ===== TEMPLATE TRADE : grilles de taille de position selon la note APEX ===== */
const TT=(()=>{try{return JSON.parse(document.getElementById('data18').textContent);}catch(e){return {lignes:[]};}})();

function ttNoteTxt(n){
  const x=Number(n);
  const d=Number.isInteger(x)?0:1;
  return x.toLocaleString('fr-FR',{minimumFractionDigits:d,maximumFractionDigits:1});
}
function ttMontantTxt(v, unite){
  if(v==null||v==='') return '—';
  const n=Number(v);
  if(!Number.isFinite(n)) return '—';
  const s=Math.round(n).toLocaleString('fr-FR');
  const u=unite||TT.unite||'$';
  return s+'\u00a0'+u;
}
function ttLignesV2(){
  if(TT&&Array.isArray(TT.lignes_v2)&&TT.lignes_v2.length) return TT.lignes_v2;
  /* Même barème que giMontant (actions / métaux) : 130 = 500 $, +100 $ tous les 24 points, jusqu'à 250 = 1 000 $. */
  const out=[];
  for(let k=0;k<=5;k++) out.push({note:130+k*24, montant:500+k*100});
  return out;
}
function ttColor(note, scale){
  const n=Number(note);
  if(!Number.isFinite(n)) return '#e6c27a';
  const sc=scale!=null?Number(scale):(TT&&TT.echelle!=null?Number(TT.echelle):100);
  if(sc===250||sc===270||sc===280){
    if(typeof pilotHex==='function') return pilotHex({total:n, scale:250, total_max:250});
    if(typeof pilotBand==='function') return (pilotBand(n, {scale:250,total_max:250})||{}).hex||'#e6c27a';
  }
  if(typeof apexHexOf==='function') return apexHexOf(n);
  if(typeof apex10Col==='function') return apex10Col({note:n});
  return '#e6c27a';
}
function ttIsOpen(){
  const w=document.getElementById('tt-wrap');
  return !!(w&&w.classList.contains('is-open'));
}
function ttSetOpen(on){
  const w=document.getElementById('tt-wrap');
  const b=document.getElementById('ttBtn');
  const pan=document.getElementById('ttPanel');
  if(!w||!b) return;
  w.classList.toggle('is-open',!!on);
  b.setAttribute('aria-expanded', on?'true':'false');
  if(pan) pan.style.display=on?'block':'none';
  if(typeof apexApplyBg==='function') apexApplyBg();
}
function ttRender(){
  const host=document.getElementById('tt-wrap');
  if(!host) return;
  const scale=TT.echelle!=null?Number(TT.echelle):250;
  const lignes=scale===250||scale===270||scale===280?ttLignesV2():(Array.isArray(TT.lignes)?TT.lignes:[]);
  const titre=TT.titre||'TEMPLATE TRADE';
  const unite=TT.unite||'$';
  const denom=scale===250||scale===270||scale===280?250:100;
  const rows=lignes.map(l=>{
    const col=ttColor(l.note, denom);
    return `<tr>
      <th scope="row"><span class="tt-note" style="color:${col};text-shadow:0 0 14px ${col}80">${ttNoteTxt(l.note)}<small>/${denom}</small></span></th>
      <td>${ttMontantTxt(l.montant, unite)}</td>
    </tr>`;
  }).join('');
  host.innerHTML=`<button type="button" id="ttBtn" class="tt-btn" aria-expanded="false" aria-controls="ttPanel">${titre}</button>
    <div class="tt-panel card no-group no-acc" id="ttPanel" role="dialog" aria-label="${titre.replace(/"/g,'&quot;')}">
      <table class="tt-table">
        <thead><tr><th>Note APEX</th><th>Montant</th></tr></thead>
        <tbody>${rows||'<tr><td colspan="2">—</td></tr>'}</tbody>
      </table>
    </div>`;
  const btn=document.getElementById('ttBtn');
  if(btn) btn.addEventListener('click',e=>{e.stopPropagation();ttSetOpen(!ttIsOpen());});
}
function ttInit(){
  ttRender();
  if(document.documentElement._ttDocBound) return;
  document.documentElement._ttDocBound=true;
  document.addEventListener('pointerdown',e=>{
    if(!ttIsOpen()) return;
    const w=document.getElementById('tt-wrap');
    if(w&&!w.contains(e.target)) ttSetOpen(false);
  });
  document.addEventListener('keydown',e=>{
    if(e.key==='Escape'&&ttIsOpen()) ttSetOpen(false);
  });
}
