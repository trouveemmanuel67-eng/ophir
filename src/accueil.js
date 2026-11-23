/* ===== Accueil : patrimoine + lignes de secteurs (données déjà présentes, lecture seule) ===== */
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
  if(typeof SEC!=='undefined') homeScoresOf(SEC.sectors||SEC.secteurs).forEach(s=>scores.push(s));
  if(typeof PAYS!=='undefined') (PAYS.countries||PAYS.pays||[]).forEach(c=>{
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
  const tip=`${t.cyan} cyan · ${t.vert} vert${t.vert>1?'s':''} · ${t.jaune} jaune${t.jaune>1?'s':''} · ${t.rouge} rouge${t.rouge>1?'s':''} · ${t.violet} violet${t.violet>1?'s':''} (échelle /10 : 0–1,5 violet · 2–3,5 rouge · 4–5,5 jaune · 6–7,5 vert · 8–10 cyan)`;
  return `<div class="home-flags" title="${tip}"><span><i class="c"></i>${t.cyan}</span><span><i class="g"></i>${t.vert}</span><span><i class="y"></i>${t.jaune}</span><span><i class="r"></i>${t.rouge}</span><span><i class="vi"></i>${t.violet}</span></div>`;
}
function homeSigHTML(av,tabId){
  const st=(tabId&&typeof sectionApexAvg==='function')?sectionApexAvg(tabId):null;
  const a=(st&&st.apex10)||(av&&av.apex10)||null; /* t320u : pas de recalcul JS */
  if(a&&a.note!=null){
    const col=(typeof apex10Col==='function')?apex10Col(a):((typeof gcol==='function')?gcol(a.pos):'#e6c27a');
    return `<div class="home-sig apex10"><b style="color:${col}">${a.display}</b><small style="color:${col}">/10</small></div>`;
  }
  if(!av||av.score==null||av.score==='') return `<div class="home-sig"><b>–</b></div>`;
  const col=(typeof avCol==='function')?avCol(av.score):'#e6c27a';
  const lab=av.label||'';
  return `<div class="home-sig"><b style="color:${col}">${sign(av.score,0)}</b><em style="color:${col}">${lab}</em></div>`;
}
function homeHeldHTML(map,id){
  const v=map[id];
  if(v==null||!(v>0)) return `<div class="home-held" title="Détenu">—</div>`;
  return `<div class="home-held" title="Détenu">${posAmt(v,'EUR')}</div>`;
}
function homeMarkHTML(m){
  if(!m||!m.text||m.text==='—') return `<div class="home-mark is-empty">—</div>`;
  const tip=m.title?` title="${homeEsc(m.title)}"`:'';
  return `<div class="home-mark"${tip}>${homeEsc(m.text)}</div>`;
}
function homeCard({id,label,short,counts,held,marks}){
  const av=homeAvOf(id);
  const pair=[(marks&&marks[0])||{text:'—'},(marks&&marks[1])||{text:'—'}];
  const full=label||short;
  return `<a class="card home-card no-acc no-group" href="#${id}" title="${homeEsc('Ouvrir l’onglet '+full)}">
    <h2 title="${homeEsc(full)}">${homeEsc(short||label)}</h2>
    ${homeSigHTML(av,id)}
    ${homeFlagsHTML(counts)}
    ${homeHeldHTML(held,id)}
    ${homeMarkHTML(pair[0])}
    ${homeMarkHTML(pair[1])}
    <div class="home-go" aria-hidden="true">→</div>
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
  const act=(P.positions||[]).filter(p=>p.statut==='active');
  const pend=(P.positions||[]).filter(p=>p.statut==='en_attente');
  const held=homeHeldMap(act);
  const nAct=P.n_actives!=null?P.n_actives:act.length;
  /* Le bandeau « Patrimoine et positions » a été retiré le 23/11/2026 :
     le total figure dans l'en-tête du panneau repliable « Mes positions ». */

  const vix=homeLastPair(typeof T2!=='undefined'&&T2.actions&&T2.actions.vix);
  const us10=homeLastPair(typeof T2!=='undefined'&&T2.actions&&T2.actions.taux10&&T2.actions.taux10.us_last);
  const orRow=(typeof MT!=='undefined'&&(MT.rows||[])).find(r=>/or/i.test(r.nom||''));
  const liv=(typeof T2!=='undefined'&&T2.liquidites&&T2.liquidites.livrets&&T2.liquidites.livrets.last);
  const prix=(typeof DATA!=='undefined'&&DATA.prix)||{};

  const marks={
    actions:[
      homeSentMark(homeIndOf('actions')),
      vix?homeValMark(`VIX ${homeNum(vix[1],1)}`, homeD(vix[0])):null
    ],
    obligations:[
      homeSentMark(homeIndOf('obligations')),
      us10?homeValMark(`US10Y ${homeNum(us10[1],1)}\u00a0%`, homeD(us10[0])):null
    ],
    metaux:[
      homeSentMark(homeIndOf('metaux')),
      orRow&&orRow.close!=null?homeValMark(`Or ${homeNum(orRow.close,0)}\u00a0$`, orRow.date?homeD(orRow.date):''):null
    ],
    energie:[null,null],
    crypto:[
      homeSentMark(homeIndOf('crypto'))
    ],
    liquidites:[
      homeSentMark(homeIndOf('liquidites')),
      Array.isArray(liv)&&liv.length>=3?homeValMark(`LA ${homeNum(liv[1],1)}\u00a0% · LEP ${homeNum(liv[2],1)}\u00a0%`, homeD(liv[0])):null
    ],
    immobilier:[
      homeSentMark(homeIndOf('immobilier')),
      prix.last&&prix.last.value!=null?homeValMark(
        `Indice ${homeNum(prix.last.value,1)}`,
        [homeD(prix.last.period), prix.peak&&prix.peak.dd!=null?`${homePct1(prix.peak.dd)} vs sommet`:''].filter(Boolean).join(' · ')
      ):null
    ]
  };
  if(typeof T2!=='undefined'&&T2.energie&&Array.isArray(T2.energie.assets)){
    const urnu=T2.energie.assets.find(a=>a.sym==='URNU'&&a.av&&a.av.score!=null);
    if(urnu) marks.energie[1]=homeValMark(`URNU ${sign(urnu.av.score,0)} ${urnu.av.label||''}`.trim(), 'Fiche URNU, déjà sur l’onglet Énergie');
  }

  const cards=[
    {id:'actions',label:'Actions',short:'Actions',counts:homeCount(homeActionScores()),held,marks:marks.actions},
    {id:'obligations',label:'Obligations',short:'Oblig.',counts:homeCount(homeScoresOf((typeof OB!=='undefined'&&OB.segments)||[])),held,marks:marks.obligations},
    {id:'metaux',label:'Métaux précieux',short:'Métaux',counts:homeCount(homeScoresOf((typeof MT!=='undefined'&&MT.rows)||[])),held,marks:marks.metaux},
    {id:'energie',label:'Énergie',short:'Énergie',counts:homeCount(homeScoresOf((typeof T2!=='undefined'&&T2.energie&&T2.energie.assets)||[])),held,marks:marks.energie},
    {id:'crypto',label:'Crypto',short:'Crypto',counts:homeCount(homeScoresOf((typeof T2!=='undefined'&&T2.crypto&&T2.crypto.fiches&&T2.crypto.fiches.assets)||[])),held,marks:marks.crypto},
    {id:'liquidites',label:'Liquidités',short:'Liq.',counts:homeCount(homeScoresOf((typeof T2!=='undefined'&&T2.liquidites&&T2.liquidites.fx&&(T2.liquidites.fx.assets||T2.liquidites.fx.pairs))||[])),held,marks:marks.liquidites},
    {id:'immobilier',label:'Immobilier',short:'Immo',counts:{n:0,violet:0,rouge:0,jaune:0,vert:0,cyan:0},held,marks:marks.immobilier}
  ];
  const sigScore=id=>{
    const av=homeAvOf(id);
    if(!av||av.score==null||av.score==='') return null;
    const n=Number(av.score);
    return Number.isFinite(n)?n:null;
  };
  cards.sort((a,b)=>{
    const sa=sigScore(a.id),sb=sigScore(b.id);
    if(sa==null&&sb==null) return 0;
    if(sa==null) return 1;
    if(sb==null) return -1;
    return sb-sa;
  });

  el.innerHTML=`
    <div class="home-table-scroll">
      <div class="home-table">
        <div class="home-table-h" aria-hidden="true">
          <span>Secteur</span><span>Signal</span><span>Drapeaux</span><span>Détenu</span><span>Sentiment</span><span>Repère</span><span></span>
        </div>
        ${cards.map(homeCard).join('')}
      </div>
    </div>`;
}
