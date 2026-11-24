/* ===== Accueil : patrimoine + lignes de secteurs (données déjà présentes, lecture seule) ===== */
const ETF_REF=(()=>{try{const el=document.getElementById('dataEtfRef');return el?JSON.parse(el.textContent):{};}catch(e){return {};}})();
function homeTabOf(p){
  const tab=p&&p.tab;
  if(tab==='obligations'||tab==='energie'||tab==='crypto'||tab==='metaux'||tab==='liquidites'||tab==='immobilier'||tab==='actions') return tab;
  if(tab==='pays') return 'actions';
  const tv=(p&&(p.fiche_tv||p.tv_note||''))+''+(p&&p.ticker?','+p.ticker:'');
  if(/NASDAQ:ENPH|,ENPH$|^ENPH$/i.test(tv) || (p&&p.ticker==='ENPH')) return 'energie';
  if(p&&p.type==='bond') return 'obligations';
  if(p&&(p.type==='equity'||p.type==='etf')) return 'actions';
  return null;
}
function homeColor(note){
  if(note&&typeof note==='object'){
    if(note.v2||note.scale===280||note.scale===250||note.scale===270){
      const id=note.band||((typeof pilotBand==='function')?pilotBand(note.note, note).id:null);
      if(id==='orange') return 'jaune';
      return id||null;
    }
    if(note.note!=null) return homeColor(note.note);
  }
  const b=(typeof apexBand==='function')?apexBand(note):null;
  return b||null;
}
function homeCount(notes){
  const t={violet:0,rouge:0,jaune:0,vert:0,cyan:0,n:0};
  (notes||[]).forEach(s=>{const c=homeColor(s);if(!c)return;t[c]++;t.n++;});
  return t;
}
function homeNoteOf(item){
  if(!item) return null;
  const a=item.apex10||item.apex10_instrument||null;
  if(a&&a.note!=null&&a.display!=='–'&&Number.isFinite(Number(a.note))) return Number(a.note);
  return null;
}
function homeScoresOf(list, pick){
  const out=[];
  (list||[]).forEach(item=>{
    const it=pick?pick(item):item;
    const a=it&&(it.apex10||it.apex10_instrument);
    if(a&&(a.scale===250||a.total_max===250||a.v2)&&a.note!=null&&a.display!=='–'){
      out.push(a);
      return;
    }
    const n=homeNoteOf(it);
    if(n!=null) out.push(n);
  });
  return out;
}
function homeAvOf(id){
  if(id==='obligations'&&typeof OB!=='undefined'&&OB.av) return OB.av;
  if(id==='metaux'&&typeof MT!=='undefined'&&MT.av) return MT.av;
  if(id==='energie'&&typeof T2!=='undefined'&&T2.energie&&T2.energie.av) return T2.energie.av;
  if(typeof AV!=='undefined'&&AV[id]) return AV[id];
  return null;
}
function homeIndOf(id){
  if(id==='obligations'&&typeof OB!=='undefined'&&OB.ind) return OB.ind;
  if(id==='metaux'&&typeof MT!=='undefined'&&MT.ind) return MT.ind;
  if(typeof IND!=='undefined'&&IND[id]) return IND[id];
  return null;
}
function homeEsc(s){return String(s||'').replace(/&/g,'&amp;').replace(/"/g,'&quot;').replace(/</g,'&lt;');}
function homeLastPair(v){
  if(!v) return null;
  if(Array.isArray(v)&&v.length>=2&&typeof v[0]==='string'&&typeof v[1]==='number') return v;
  if(v.last) return homeLastPair(v.last);
  return null;
}
function homeD(s){
  if(!s) return '';
  if(/^\d{4}-Q[1-4]$/.test(s)) return (typeof qfr==='function')?qfr(s):s;
  if(/^\d{4}-\d{2}$/.test(s)) return (typeof mfr==='function')?mfr(s):s;
  if(/^\d{4}-\d{2}-\d{2}$/.test(s)){
    const d=new Date(s+'T00:00:00');
    return isNaN(d)?s:d.toLocaleDateString('fr-FR',{day:'numeric',month:'short'});
  }
  return s;
}
function homePct1(v){
  if(v==null||!Number.isFinite(Number(v))) return '—';
  const n=Number(v);return (n>0?'+':n<0?'−':'')+Math.abs(n).toLocaleString('fr-FR',{minimumFractionDigits:1,maximumFractionDigits:1})+'\u00a0%';
}
function homeNum(v,d){
  if(v==null||!Number.isFinite(Number(v))) return '—';
  return Number(v).toLocaleString('fr-FR',{minimumFractionDigits:d,maximumFractionDigits:d});
}
function homeCashFromSource(src){
  if(!src) return {cash:null,cfd:null};
  const cash=src.match(/([0-9][0-9 \u00a0\u202f]*,[0-9]{2})\s*\$\s*de liquidités/i);
  const cfd=src.match(/compte CFD de\s*([0-9][0-9 \u00a0\u202f]*,[0-9]{2})\s*\$/i);
  const toNum=s=>s?Number(s.replace(/[ \u00a0\u202f]/g,'').replace(',','.')):null;
  return {cash:toNum(cash&&cash[1]),cfd:toNum(cfd&&cfd[1])};
}
function homeHeldMap(act){
  const map={actions:0,obligations:0,metaux:0,energie:0,crypto:0,liquidites:0,immobilier:0};
  act.forEach(p=>{
    const tab=homeTabOf(p);
    if(!tab||!(tab in map)) return;
    const v=p.valeur_eur;
    if(v!=null&&Number.isFinite(Number(v))) map[tab]+=Number(v);
  });
  return map;
}
function homeActionScores(){
  const scores=[];
  if(typeof PILOT!=='undefined'&&PILOT&&PILOT.pilotes){
    const seen=new Set();
    Object.keys(PILOT.pilotes).forEach(k=>{
      const p=PILOT.pilotes[k];
      const add=r=>{
        if(!r||r.total==null||seen.has(r.tv||r.ticker)) return;
        seen.add(r.tv||r.ticker||(k+':'+r.total));
        scores.push({v2:true, scale:280, note:r.total, band:r.band});
      };
      if(p&&p.etf) add(p.etf);
      (p&&p.actions||[]).forEach(add);
    });
    if(scores.length) return scores;
  }
  if(typeof SEC!=='undefined') homeScoresOf(SEC.sectors||SEC.secteurs).forEach(s=>scores.push(s));
  if(typeof PAYS!=='undefined') (PAYS.countries||PAYS.pays||[]).filter(c=>typeof paysEstDansUnivers!=='function'||paysEstDansUnivers(c)).forEach(c=>{
    if(c.head) homeScoresOf([c.head]).forEach(s=>scores.push(s));
    else homeScoresOf([c]).forEach(s=>scores.push(s));
    homeScoresOf(c.rows||[]).forEach(s=>scores.push(s));
  });
  return scores;
}
function homeBestWorst(act,n){
  const withPnl=act.filter(p=>p.pnl_pct!=null&&Number.isFinite(Number(p.pnl_pct)));
  const by=(a,b)=>Number(b.pnl_pct)-Number(a.pnl_pct);
  const best=[...withPnl].sort(by).slice(0,n);
  const worst=[...withPnl].sort((a,b)=>-by(a,b)).slice(0,n);
  return {best,worst};
}
function homeShortName(p){
  const nom=p.nom||p.titre||p.ticker||'—';
  if(nom==='Enphase Energy') return 'Enphase';
  if(nom==='AGNC Investment') return 'AGNC';
  return nom;
}
function homeBwBits(arr){
  if(!arr||!arr.length) return '—';
  return arr.map((p,i)=>{
    const pct=p.pnl_pct==null?'—':`<span class="${p.pnl_pct>=0?'up':'down'}">${posPct(p.pnl_pct)}</span>`;
    const sep=i?`<span class="sep">·</span>`:'';
    return `${sep}<span class="nm">${homeEsc(homeShortName(p))}</span>\u00a0${pct}`;
  }).join('');
}
function homeLab(ind){
  if(!ind||!ind.label) return '';
  return ind.label==='Peur extrême'?'Peur ext.':ind.label;
}
function homeSentMark(ind){
  if(!ind||ind.value==null) return null;
  const bits=[ind.title,ind.date&&homeD(ind.date)].filter(Boolean);
  return {text:`S ${fmt(ind.value,0)} ${homeLab(ind)}`.trim(), title:bits.join(' · ')};
}
function homeValMark(text, title){
  if(!text) return null;
  return {text, title:title||''};
}
function homeFlagsHTML(t){
  if(!t||!t.n) return '<div class="home-flags" title="Aucune fiche notée dans cet onglet">—</div>';
  const v2=t&&t.v2;
  const tip=(v2&&t.scale===250)
    ? `${t.cyan} cyan · ${t.vert} vert${t.vert>1?'s':''} · ${t.jaune} orange${t.jaune>1?'s':''} · ${t.rouge} rouge${t.rouge>1?'s':''} · ${t.violet} violet${t.violet>1?'s':''} (échelle −50 à 250 : <10 violet · 10–70 rouge · 70–130 orange · 130–190 vert · ≥190 cyan)`
    : v2
    ? `${t.cyan} cyan · ${t.vert} vert${t.vert>1?'s':''} · ${t.jaune} orange${t.jaune>1?'s':''} · ${t.rouge} rouge${t.rouge>1?'s':''} · ${t.violet} violet${t.violet>1?'s':''} (échelle −80 à 280 : <−8 violet · −8–64 rouge · 64–136 orange · 136–208 vert · ≥208 cyan)`
    : `${t.cyan} cyan · ${t.vert} vert${t.vert>1?'s':''} · ${t.jaune} jaune${t.jaune>1?'s':''} · ${t.rouge} rouge${t.rouge>1?'s':''} · ${t.violet} violet${t.violet>1?'s':''} (échelle /100 : 0–<20 violet · 20–<40 rouge · 40–<60 jaune · 60–<80 vert · 80–100 cyan)`;
  return `<div class="home-flags" title="${tip}"><span><i class="c"></i>${t.cyan}</span><span><i class="g"></i>${t.vert}</span><span><i class="y"></i>${t.jaune}</span><span><i class="r"></i>${t.rouge}</span><span><i class="vi"></i>${t.violet}</span></div>`;
}
function homeSigHTML(av,tabId){
  const st=(tabId&&typeof sectionApexAvg==='function')?sectionApexAvg(tabId):null;
  const v2=st&&st.apexV2;
  if(v2&&v2.total!=null){
    const col=(typeof pilotHex==='function')?pilotHex(v2):(v2.hex||'#e6c27a');
    const mx=v2.total_max!=null?v2.total_max:(v2.scale===250?250:280);
    return `<div class="home-sig apex10 apex10-pilot" style="color:${col}"><b>${v2.total}</b><small>/ ${mx}</small></div>`;
  }
  const a=(st&&st.apex10)||(av&&av.apex10)||null; /* t320u : pas de recalcul JS */
  if(a&&a.v2&&a.total!=null){
    const col=(typeof pilotHex==='function')?pilotHex(a):(a.hex||'#e6c27a');
    const mx=a.total_max!=null?a.total_max:(a.scale===250?250:280);
    return `<div class="home-sig apex10 apex10-pilot" style="color:${col}"><b>${a.total}</b><small>/ ${mx}</small></div>`;
  }
  if(a&&a.note!=null&&!(a.v2||a.scale===280||a.scale===250||a.scale===270)){
    const col=(typeof apex10Col==='function')?apex10Col(a):((typeof gcol==='function')?gcol(a.pos):'#e6c27a');
    return `<div class="home-sig apex10"><b style="color:${col}">${a.display}</b><small style="color:${col}">/100</small></div>`;
  }
  if(!av||av.score==null||av.score==='') return `<div class="home-sig"><b>–</b></div>`;
  const col=(typeof avCol==='function')?avCol(av.score):'#e6c27a';
  const lab=av.label||'';
  return `<div class="home-sig"><b style="color:${col}">${sign(av.score,0)}</b><em style="color:${col}">${lab}</em></div>`;
}
function homeApexNorm(id){
  /* (note − min)/(max − min) : actions sur l'échelle publiée (−50…250, ou PILOT.scale), autres 0…100. */
  const st=(typeof sectionApexAvg==='function')?sectionApexAvg(id):null;
  const v2=st&&st.apexV2;
  const sc=(typeof PILOT!=='undefined'&&PILOT&&PILOT.scale)?PILOT.scale:null;
  const v2min=(sc&&sc.min!=null)?Number(sc.min):-50;
  const v2max=(sc&&sc.max!=null)?Number(sc.max):250;
  if(v2&&v2.total!=null&&Number.isFinite(Number(v2.total))){
    const mn=v2.total_min!=null?Number(v2.total_min):v2min;
    const mx=v2.total_max!=null?Number(v2.total_max):v2max;
    const span=mx-mn;
    return span>0?(Number(v2.total)-mn)/span:null;
  }
  const a=(st&&st.apex10)||null;
  if(a&&(a.v2||a.scale===250||a.scale===270||a.scale===280||a.total_max===250||a.total_max===270||a.total_max===280)&&a.total!=null&&Number.isFinite(Number(a.total))){
    const mn=a.total_min!=null?Number(a.total_min):v2min;
    const mx=a.total_max!=null?Number(a.total_max):(a.total_max!=null?Number(a.total_max):v2max);
    const span=mx-mn;
    return span>0?(Number(a.total)-mn)/span:null;
  }
  if(a&&a.note!=null&&Number.isFinite(Number(a.note))) return Number(a.note)/100;
  return null;
}
function homeHeldHTML(map,id){
  const v=map[id];
  if(v==null||!(v>0)) return `<div class="home-held" title="Détenu">—</div>`;
  return `<div class="home-held" title="Détenu">${posAmt(v,'EUR')}</div>`;
}
function homeSectorPositions(act,id){
  return (act||[]).filter(p=>homeTabOf(p)===id);
}
function homeEmpty(cls,tip){
  return `<div class="${cls} is-empty"${tip?` title="${homeEsc(tip)}"`:''}>—</div>`;
}
function homePnlHTML(stats){
  const pct=stats&&stats.pnl;
  if(pct==null||!Number.isFinite(Number(pct))) return homeEmpty('home-pnl','Gain ou perte latent : pas de prix de revient sur les positions du secteur');
  const n=Number(pct);
  const tip=stats.pnlPartial?'Gain ou perte latent, uniquement sur les lignes avec prix de revient':'Gain ou perte latent des positions du secteur';
  return `<div class="home-pnl" title="${homeEsc(tip)}"><span class="${n>=0?'up':'down'}">${(typeof posPct==='function')?posPct(n):homePct1(n)}</span></div>`;
}
function homePosYield(p){
  if(!p) return null;
  const keys=['rendement','rendement_pct','yield','yield_pct','dividende','dividend_yield','coupon','coupon_pct','rdt'];
  for(let i=0;i<keys.length;i++){
    const v=p[keys[i]];
    if(v==null||v==='') continue;
    const n=Number(v);
    if(Number.isFinite(n)) return n;
  }
  return null;
}
function homeYieldHTML(stats){
  const y=stats&&stats.yield;
  if(y==null||!Number.isFinite(Number(y))) return homeEmpty('home-rdt','Rendement / dividende ou coupon : donnée absente sur les positions, non inventée');
  const n=Number(y);
  return `<div class="home-rdt" title="Rendement / dividende ou coupon moyen pondéré des positions du secteur">${(typeof posPct==='function')?posPct(n):homePct1(n)}</div>`;
}
function homeParseParisDate(s){
  /* Une date seule (YYYY-MM-DD) n'est pas un minuit UTC : new Date('2026-11-24')
     décale le jour et, l'après-midi à Paris, Math.round(elapsed/86400000) passe à 1 j
     pour un achat du jour (t458u). */
  if(s==null||s==='') return null;
  const str=String(s).trim();
  const m=str.match(/^(\d{4})-(\d{2})-(\d{2})$/);
  if(m){
    const d=new Date(Number(m[1]), Number(m[2])-1, Number(m[3]), 12, 0, 0);
    return isNaN(d.getTime())?null:d;
  }
  const d=new Date(str);
  return isNaN(d.getTime())?null:d;
}
function homeParisYMD(d){
  try{
    return new Intl.DateTimeFormat('en-CA',{timeZone:'Europe/Paris',year:'numeric',month:'2-digit',day:'2-digit'}).format(d);
  }catch(e){
    const y=d.getFullYear(), mo=String(d.getMonth()+1).padStart(2,'0'), da=String(d.getDate()).padStart(2,'0');
    return y+'-'+mo+'-'+da;
  }
}
function homeCalendarDays(from, now){
  if(!from||!now) return null;
  const a=homeParisYMD(from), b=homeParisYMD(now);
  const [ay,am,ad]=a.split('-').map(Number);
  const [by,bm,bd]=b.split('-').map(Number);
  const n=(Date.UTC(by,bm-1,bd)-Date.UTC(ay,am-1,ad))/86400000;
  return Number.isFinite(n)?n:null;
}
function homePosBuyDate(p){
  /* Dates d'achat explicites seulement. date_ordre / date_execution d'une vente en attente sont ignorées. perf_1an_dates n'est pas une date d'achat. Les ordres d'achat en cours (déjà actifs) comptent s'ils ont une date. */
  if(!p) return null;
  const st=String(p.statut||'active').toLowerCase();
  if(st!=='active'&&st!=='en_attente') return null;
  const raw=p.date_achat||p.date_ouverture||p.opened_at||p.purchase_date||null;
  let s=raw;
  if(s==null&&!p.vente_en_attente) s=p.date_execution||p.date_ordre||null;
  return homeParseParisDate(s);
}
function homeAgeTxt(days){
  if(days==null||!Number.isFinite(Number(days))||Number(days)<0) return null;
  const n=Number(days);
  if(n<45) return Math.round(n)+'\u00a0j';
  const mois=n/30.4375;
  if(mois<18) return mois.toLocaleString('fr-FR',{minimumFractionDigits:1,maximumFractionDigits:1})+'\u00a0mois';
  const ans=n/365.25;
  return ans.toLocaleString('fr-FR',{minimumFractionDigits:1,maximumFractionDigits:1})+'\u00a0an'+(ans>=1.95?'s':'');
}
function homeAgeHTML(stats){
  const txt=homeAgeTxt(stats&&stats.ageDays);
  if(!txt) return homeEmpty('home-age','Ancienneté : dates d’achat indisponibles (Revolut / XTB), non inventées');
  return `<div class="home-age" title="Ancienneté moyenne des positions, pondérée par le montant">${txt}</div>`;
}
function homeEtfHTML(id){
  const ref=(typeof ETF_REF!=='undefined'&&ETF_REF)?ETF_REF[id]:null;
  const tv=ref&&(ref.tv||ref.ticker);
  if(!tv) return homeEmpty('home-etf','Aucun ETF de référence configuré');
  const nom=ref.nom||'';
  const full=String(tv);
  const sym=full.indexOf(':')>=0?full.slice(full.indexOf(':')+1):full;
  const svg=(typeof CPSVG!=='undefined')?CPSVG:'<svg viewBox="0 0 16 16" width="12" height="12" aria-hidden="true"><rect x="5" y="1.5" width="8" height="10" rx="1.5" fill="none" stroke="currentColor" stroke-width="1.3"/><rect x="2.5" y="4.5" width="8" height="10" rx="1.5" fill="none" stroke="currentColor" stroke-width="1.3"/></svg>';
  /* Affiche le symbole (compact) ; le bouton copie le ticker TradingView complet (ex. AMEX:SPY). */
  return `<div class="home-etf" title="${homeEsc((nom?nom+' · ':'')+full)}"><span class="tvs"><code>${homeEsc(sym)}</code><button type="button" class="cp" data-c="${homeEsc(full)}" aria-label="Copier ${homeEsc(full)}" title="Copier ${homeEsc(full)}">${svg}</button></span></div>`;
}
function homeSentHTML(id){
  const ind=homeIndOf(id);
  if(!ind||ind.value==null||!Number.isFinite(Number(ind.value))) return homeEmpty('home-sent','Note Sentiment indisponible');
  const bits=['Note Sentiment',ind.title,ind.date&&homeD(ind.date),ind.label].filter(Boolean);
  return `<div class="home-sent" title="${homeEsc(bits.join(' · '))}">S\u00a0${fmt(ind.value,0)}</div>`;
}
function homeAvHTML(id){
  const av=homeAvOf(id);
  if(!av||av.score==null||av.score===''||!Number.isFinite(Number(av.score))) return homeEmpty('home-av','Note Achat / Vente indisponible');
  const col=(typeof avCol==='function')?avCol(av.score):'#e6c27a';
  const lab=av.label||'';
  const tip=['Note AV (Achat / Vente)',lab,av.date&&homeD(av.date)].filter(Boolean).join(' · ');
  return `<div class="home-av" title="${homeEsc(tip)}"><b style="color:${col}">${sign(av.score,0)}</b></div>`;
}
function homeHypeOf(id){
  /* Branchement H : si sectionHypeAvg est définie (intégration H non publiée), on affiche sa moyenne ; sinon « – ». */
  if(typeof sectionHypeAvg==='function'){
    const v=sectionHypeAvg(id);
    if(v!=null&&typeof v==='object'){
      const n=v.note!=null?v.note:(v.hype!=null?v.hype:v.total);
      if(n!=null&&Number.isFinite(Number(n))) return Number(n);
    }else if(v!=null&&Number.isFinite(Number(v))) return Number(v);
  }
  return null;
}
function homeHypeHTML(id){
  const n=homeHypeOf(id);
  if(n==null||!Number.isFinite(Number(n))) return `<div class="home-hype is-empty" title="Note HYPE indisponible (indicateur d’attention non publié)">–</div>`;
  return `<div class="home-hype" title="Note HYPE : moyenne d’attention des actifs du secteur">${fmt(n,0)}</div>`;
}
function homeSectorStats(act,id){
  const list=homeSectorPositions(act,id);
  let val=0,valK=0,invK=0,unkInvest=false;
  let yNum=0,yDen=0,yMiss=false,yAny=false;
  let ageNum=0,ageDen=0,ageMiss=false,ageAny=false;
  const now=(typeof giNow==='function')?giNow():new Date();
  (list||[]).forEach(p=>{
    const v=Number(p.valeur_eur);
    const w=Number.isFinite(v)&&v>0?v:null;
    if(Number.isFinite(v)&&v>0) val+=v;
    const inv=p.investi_eur;
    if(inv!=null&&inv!==''&&Number.isFinite(Number(inv))&&Number(inv)>0&&Number.isFinite(v)){valK+=v;invK+=Number(inv);}
    else if(Number.isFinite(v)&&v>0) unkInvest=true;
    const y=homePosYield(p);
    if(y!=null&&w){yNum+=y*w;yDen+=w;yAny=true;}
    else if(w) yMiss=true;
    const d=homePosBuyDate(p);
    if(d&&w){
      const days=homeCalendarDays(d, now);
      if(Number.isFinite(days)&&days>=0){ageNum+=days*w;ageDen+=w;ageAny=true;}
      else ageMiss=true;
    }else if(w) ageMiss=true;
  });
  const pnl=(invK>0)?(valK/invK-1)*100:null;
  /* Rendement et ancienneté : seulement si toutes les lignes détenues ont la donnée (sinon on n'affiche pas une moyenne partielle). */
  const yieldPct=(yAny&&!yMiss&&yDen>0)?yNum/yDen:null;
  const ageDays=(ageAny&&!ageMiss&&ageDen>0)?ageNum/ageDen:null;
  return {list,val,pnl,pnlPartial:!!(unkInvest&&invK>0),yield:yieldPct,ageDays};
}
function homeCard({id,label,short,counts,stats}){
  const av=homeAvOf(id);
  const full=label||short;
  const held={};held[id]=stats&&stats.val;
  return `<a class="card home-card no-acc no-group" href="#${id}" title="${homeEsc('Ouvrir l’onglet '+full)}">
    <h2 title="${homeEsc(full)}">${homeEsc(label||short)}</h2>
    ${homeSigHTML(av,id)}
    <div class="home-meta">
    ${homeHeldHTML(held,id)}
    ${homePnlHTML(stats)}
    ${homeYieldHTML(stats)}
    ${homeEtfHTML(id)}
    ${homeSentHTML(id)}
    ${homeAvHTML(id)}
    ${homeHypeHTML(id)}
    ${homeAgeHTML(stats)}
    ${homeFlagsHTML(counts)}
    <div class="home-go" aria-hidden="true">→</div>
    </div>
  </a>`;
}
function homeBook(list){
  let val=0,valK=0,invK=0,unk=false;
  (list||[]).forEach(p=>{
    const v=Number(p.valeur_eur);
    if(!Number.isFinite(v)) return;
    val+=v;
    const inv=p.investi_eur;
    if(inv!=null&&inv!==''&&Number.isFinite(Number(inv))){valK+=v;invK+=Number(inv);}
    else unk=true;
  });
  const pct=(invK>0)?(valK/invK-1)*100:null;
  return {val,pct,star:!!(unk&&invK>0),unkAll:!!(unk&&invK<=0)};
}
function homePctHTML(pct,star){
  if(pct==null||!Number.isFinite(Number(pct))) return '—';
  const html=`<span class="${Number(pct)>=0?'up':'down'}">${posPct(pct)}</span>`;
  return star?html+'<sup class="home-star" title="hors Bitcoin">*</sup>':html;
}
function homeKv(label, amount, pctHtml, tip){
  return `<div class="home-kv"${tip?` title="${homeEsc(tip)}"`:''}><span class="l">${homeEsc(label)}</span><b>${amount}</b>${pctHtml?`<small>${pctHtml}</small>`:''}</div>`;
}
function renderAccueil(el){
  const P=(typeof POS!=='undefined'&&POS)?POS:{positions:[],totaux:{},courtiers:{}};
  const T=P.totaux||{};
  const C=(T.courtiers)||{};
  const act=(P.positions||[]).filter(p=>p.statut==='active'||p.statut==='en_attente');
  const pend=(P.positions||[]).filter(p=>p.statut==='en_attente');
  const held=homeHeldMap(act);
  const nAct=P.n_actives!=null?P.n_actives:act.length;
  /* Le bandeau « Patrimoine et positions » a été retiré le 23/11/2026 :
     le total figure dans l'en-tête du panneau repliable « Mes positions ». */

  const cards=[
    {id:'actions',label:'Actions',short:'Actions',counts:(()=>{const c=homeCount(homeActionScores());c.v2=true;return c;})()},
    {id:'obligations',label:'Obligations',short:'Oblig.',counts:homeCount(homeScoresOf((typeof OB!=='undefined'&&OB.segments)||[]))},
    {id:'metaux',label:'Métaux précieux',short:'Métaux',counts:(()=>{const c=homeCount(homeScoresOf((typeof MT!=='undefined'&&MT.rows)||[]));c.v2=true;c.scale=250;return c;})()},
    {id:'energie',label:'Énergie',short:'Énergie',counts:homeCount(homeScoresOf((typeof T2!=='undefined'&&T2.energie&&T2.energie.assets)||[]))},
    {id:'crypto',label:'Crypto',short:'Crypto',counts:(()=>{const c=homeCount(homeScoresOf((typeof cxApexAssets==='function'?cxApexAssets: (xs=>xs.filter(s=>String((s&&s.key)||'').toLowerCase()!=='xrp')))((typeof T2!=='undefined'&&T2.crypto&&T2.crypto.fiches&&T2.crypto.fiches.assets)||[])));c.v2=true;return c;})()},
    {id:'liquidites',label:'Liquidités',short:'Liq.',counts:homeCount(homeScoresOf((typeof T2!=='undefined'&&T2.liquidites&&T2.liquidites.fx&&(T2.liquidites.fx.assets||T2.liquidites.fx.pairs))||[]))},
    {id:'immobilier',label:'Immobilier',short:'Immo',counts:{n:0,violet:0,rouge:0,jaune:0,vert:0,cyan:0}}
  ];
  cards.forEach(c=>{ c.stats=homeSectorStats(act,c.id); });
  cards.sort((a,b)=>{
    const sa=homeApexNorm(a.id),sb=homeApexNorm(b.id);
    if(sa==null&&sb==null) return String(a.label||'').localeCompare(String(b.label||''),'fr');
    if(sa==null) return 1;
    if(sb==null) return -1;
    if(sb!==sa) return sb-sa;
    return String(a.label||'').localeCompare(String(b.label||''),'fr');
  });

  el.innerHTML=`
    <div class="home-table-scroll">
      <div class="home-table">
        <div class="home-table-h" aria-hidden="true">
          <span>Secteur</span><span>Note APEX</span><span>Détenu</span><span>Latent</span><span>Rdt</span><span>ETF</span><span>Sent.</span><span>AV</span><span>Hype</span><span>Âge</span><span>Drap.</span><span></span>
        </div>
        ${cards.map(homeCard).join('')}
      </div>
    </div>`;
}
