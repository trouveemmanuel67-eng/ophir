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
function ttColor(note){
  const n=Number(note);
  if(!Number.isFinite(n)) return '#e6c27a';
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
}
function ttRender(){
  const host=document.getElementById('tt-wrap');
  if(!host) return;
  const lignes=Array.isArray(TT.lignes)?TT.lignes:[];
  const titre=TT.titre||'TEMPLATE TRADE';
  const unite=TT.unite||'$';
  const rows=lignes.map(l=>{
    const col=ttColor(l.note);
    return `<tr>
      <th scope="row"><span class="tt-note" style="color:${col};text-shadow:0 0 14px ${col}80">${ttNoteTxt(l.note)}<small>/100</small></span></th>
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
