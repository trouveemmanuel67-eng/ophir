import sys
from playwright.sync_api import sync_playwright
U,O=sys.argv[1],sys.argv[2];ok=True;errs=[]
JS=r"""(t)=>{const ST=[[0,[255,45,45]],[33,[255,154,31]],[66,[34,197,94]],[100,[0,229,255]]];
const bar=p=>{p=Math.max(0,Math.min(100,p));for(let k=1;k<ST.length;k++)if(p<=ST[k][0]){const u=(p-ST[k-1][0])/(ST[k][0]-ST[k-1][0]);const c=ST[k-1][1].map((x,j)=>Math.round(x+(ST[k][1][j]-x)*u));return `rgb(${c.join(', ')})`;}};
const mir=p=>bar(100-p);
const near=(a,b)=>{const A=a.match(/\d+/g).map(Number),B=b.match(/\d+/g).map(Number);return A.slice(0,3).every((x,j)=>Math.abs(x-B[j])<=2);};
const nearV=(col,v)=>[-.5,-.3,-.15,0,.15,.3,.5].some(d=>near(col,mir(v+d)));const pos=(c,b)=>{const r=c.getBoundingClientRect(),q=b.getBoundingClientRect();return (r.left+r.width/2-q.left)/q.width*100;};
const R={tab:t,bad:[]};const D=document.getElementById('duo');const B=D.querySelector('.db-g .ind-bar');
const s=D.querySelector('.db-g .db-cur.db-s'),a=D.querySelector('.db-g .db-cur.db-a');const p=pos(s,B),pa=pos(a,B);
if(!near(getComputedStyle(s).color,mir(p)))R.bad.push('curseur sentiment barre fusionnée');
if(!near(getComputedStyle(a).color,bar(pa)))R.bad.push('curseur A/V barre fusionnée');
D.querySelectorAll('.db-dot.db-s').forEach((d,k)=>{const bg=getComputedStyle(d);if(!near(bg.color,mir(p))||d.textContent!=='S')R.bad.push('pastille sentiment '+k);});
if(D.querySelector('.db-leg'))R.bad.push('légende sous barre');
const LET=(root,lab)=>{root.querySelectorAll('.db-g').forEach(G=>{const b=G.querySelector('.ind-bar').getBoundingClientRect(),A=G.querySelector('.db-cur.db-a'),S=G.querySelector('.db-cur.db-s'),ra=A.getBoundingClientRect(),rs=S.getBoundingClientRect();
 if(A.textContent!=='AV'||S.textContent!=='S')R.bad.push('lettres '+lab);if(ra.bottom>b.top+0.5)R.bad.push('AV pas au-dessus '+lab);if(rs.top<b.bottom-0.5)R.bad.push('S pas en dessous '+lab);
 if(!(ra.bottom<=rs.top||ra.right<=rs.left||rs.right<=ra.left))R.bad.push('chevauchement '+lab);if(parseFloat(getComputedStyle(A).fontWeight)<700)R.bad.push('gras '+lab);if(!(R.fs||[]).some(x=>x.startsWith(lab)))R.fs=(R.fs||[]).concat(lab+':'+getComputedStyle(A).fontSize);});};
LET(D,'carte');
D.querySelectorAll('.db-dot.db-a').forEach(d=>{if(d.textContent!=='AV')R.bad.push('pastille AV');});
{const ga=D.querySelectorAll('.duo-col .ind-gauge .ind-cur.cur-a');ga.forEach(c=>{const bb2=c.parentElement.querySelector('.ind-bar');if(c.textContent!=='AV'||!near(getComputedStyle(c).color,bar(pos(c,bb2))))R.bad.push('jauge AV détail');});}
const sc=D.querySelectorAll('.duo-sc');
sc[0].querySelectorAll('.av-val span,.av-val em').forEach(e=>{if(!near(getComputedStyle(e).color,bar(pa)))R.bad.push('texte score A/V');});
sc[1].querySelectorAll('.ind-val span,.ind-val em').forEach(e=>{if(!near(getComputedStyle(e).color,mir(p)))R.bad.push('texte score sentiment');});
R.txt=[sc[0].querySelector('.av-val').textContent.trim()+' '+getComputedStyle(sc[0].querySelector('.av-val span')).color,sc[1].querySelector('.ind-val').textContent.trim()+' '+getComputedStyle(sc[1].querySelector('.ind-val span')).color];
const g=D.querySelector('.duo-col .ind-gauge');R.gauge=!!g;
if(g){const gb=g.querySelector('.ind-bar'),cur=g.querySelector('.ind-cur');if(!getComputedStyle(gb).backgroundImage.startsWith('linear-gradient(90deg, rgb(0, 229, 255)'))R.bad.push('barre jauge détail non miroir');
 const p2=pos(cur,gb);if(!near(getComputedStyle(cur).color,mir(p2))||cur.textContent!=='S')R.bad.push('curseur jauge détail');
 if(g.closest('.duo-col').querySelector('.ind-legend'))R.bad.push('légende sous jauge');}
const ch=Chart.getChart(document.getElementById('cInd'));if(ch){const f=ch.data.datasets[0].segment.borderColor;[10,30,50,70,90].forEach(v=>{if(!near(f({p0:{parsed:{y:v}},p1:{parsed:{y:v}}}),mir(v)))R.bad.push('courbe '+v);});R.chart='ok';}else R.chart='absente';
let nc=0;D.querySelectorAll('.duo-col .ind-sb').forEach(sb=>{const b=sb.querySelector('.ind-sbl b'),i=sb.querySelector('.ind-sbt i');if(!b||!i)return;const v=parseFloat(b.textContent.replace(',','.'));if(isNaN(v))return;nc++;if(!nearV(getComputedStyle(i).backgroundColor,v)||!nearV(getComputedStyle(b).color,v))R.bad.push('composante '+v);});R.comps=nc;
if(!(D.querySelector('.duo-scales')||{textContent:''}).textContent.includes('Toutes les représentations du sentiment'))R.bad.push('explication détail');
const P=document.getElementById('p'+t),L=t==='actions'?SEC.sectors:(t==='obligations'?OB_GROUPS.us.map(k=>OB.segments.find(s=>s.key===k)):null);
if(L){R.rows=0;P.querySelector(':scope>.no-group:not(.pays-card):not(.ob-card:not([data-cc=us]))').querySelectorAll('.sec-grid .sec').forEach((e,k)=>{const b=e.querySelector('.db-g .ind-bar'),x=e.querySelector('.db-cur.db-s'),xa=e.querySelector('.db-cur.db-a');const pp=pos(x,b),pq=pos(xa,b);
  if(!near(getComputedStyle(x).color,mir(pp)))R.bad.push('curseur ligne '+k);
  const lg=e.querySelector('.db-leg');const bs=lg?lg.querySelectorAll('b'):[];
  if(!lg||lg.querySelector('small')||bs.length!==2||!near(getComputedStyle(bs[0]).color,bar(pq))||!near(getComputedStyle(bs[1]).color,mir(pp)))R.bad.push('valeurs ligne '+k);
  const d=e.querySelector('.sec-det');if(!d.querySelector('.sent-mir'))R.bad.push('explication détail ligne '+k);
  const C=Chart.getChart(d.querySelector('canvas[id^=cSecS],canvas[id^=cObS]'));if(C){const ss=L[k].sent.series;C.data.datasets[0].pointBackgroundColor.forEach((col,j)=>{if(!near(col,mir(ss[j][1])))R.bad.push('point '+k+'/'+j);});}else R.bad.push('courbe ligne '+k);
  d.querySelectorAll('.ind-sb').forEach(sb=>{const bb=sb.querySelector('.ind-sbl b'),i=sb.querySelector('.ind-sbt i');if(!i)return;const v=parseFloat(bb.textContent.replace(',','.'));if(!nearV(getComputedStyle(i).backgroundColor,v)||!nearV(getComputedStyle(bb).color,v))R.bad.push('compo ligne '+k);});R.rows++;});
  LET(P.querySelector('.sec-grid'),'lignes');P.querySelectorAll('.sr-hd .db-dot').forEach(d=>{if(!['AV','S'].includes(d.textContent))R.bad.push('en-tête');});R.row0=P.querySelector('.sec-grid .sec .db-leg').textContent.replace(/\s+/g,' ').trim();}
R.sw=document.documentElement.scrollWidth;R.bad=R.bad.slice(0,8);return R;}"""
with sync_playwright() as p:
  b=p.chromium.launch(executable_path='/usr/bin/google-chrome',args=['--no-sandbox'])
  for w in (1920,390):
    pg=b.new_page(viewport={'width':w,'height':900});pg.on('pageerror',lambda e:errs.append(str(e)));pg.on('console',lambda m:m.type=='error' and errs.append(m.text))
    pg.goto(U);pg.evaluate("localStorage.clear()");pg.reload();pg.wait_for_timeout(1500)
    for t in ['actions','obligations','crypto','liquidites','immobilier']:
      pg.evaluate(f"location.hash='{t}'");pg.wait_for_timeout(1000)
      pg.evaluate("""(t)=>{document.querySelector('#duo .duo-card .acc-head').click();const P=document.getElementById('p'+t);P.querySelectorAll(':scope>.no-group>.acc-head,:scope>.no-group .acc-head').forEach(h=>{if(!h.closest('.acc-open'))h.click();});P.querySelectorAll('.sec-det').forEach(d=>d.open=true);}""",t)
      pg.wait_for_timeout(1500)
      r=pg.evaluate(JS,t);good=not r['bad'] and r['sw']<=w;ok&=good;print('✔' if good else '✘',w,r)
      if t=='actions':
        pg.evaluate("scrollTo(0,0)")
        pg.query_selector('#duo .duo-card').screenshot(path=f'{O}/actions_carte_detail_{w}.png')
        pg.query_selector('#pactions .sec-grid .sec').screenshot(path=f'{O}/secteur_detail_{w}.png')
    pg.close()
  b.close()
print('console:',errs or 'aucune erreur');print('OK' if ok and not errs else 'PROBLÈME')
