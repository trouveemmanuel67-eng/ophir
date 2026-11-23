"""Format « lignes » : INDICATEUR et ACHAT / VENTE en lignes pleine largeur (tous onglets), secteurs et segments en lignes de tableau."""
import sys
from playwright.sync_api import sync_playwright
B='/workspace/invest/patrimoine-dashboard/'
URL=sys.argv[1] if len(sys.argv)>1 else 'file://'+B+'index.html'
OUT=sys.argv[2] if len(sys.argv)>2 else B
ok=True
def chk(c,m):
    global ok
    print(('  ✔ ' if c else '  ✘ ')+m); ok&=bool(c)
MENT="Indicateur composite APEX, purement informatif. Ne constitue pas un conseil ni un signal d'ordre."
with sync_playwright() as p:
    b=p.chromium.launch(executable_path='/usr/bin/google-chrome',args=['--no-sandbox'])
    for w,h,mob in [(1920,1080,False),(1366,768,False),(390,844,True)]:
        print('==',w); sfx={1920:'',1366:'-1366',390:'-mobile'}[w]
        ctx=b.new_context(viewport={'width':w,'height':h},is_mobile=mob,has_touch=mob,permissions=['clipboard-read','clipboard-write']);pg=ctx.new_page();logs=[]
        pg.on('console',lambda m: logs.append(m.type+': '+m.text) if m.type in('error','warning') else None);pg.on('pageerror',lambda e:logs.append(str(e)))
        pg.goto(URL+'#actions',wait_until='networkidle');pg.evaluate('localStorage.clear()');pg.reload(wait_until='networkidle');pg.wait_for_timeout(1200)
        for t in ['actions','obligations','crypto','liquidites','immobilier']:
            pg.evaluate(f"location.hash='{t}'");pg.wait_for_timeout(1300);pg.evaluate('scrollTo(0,0)')
            r=pg.evaluate("""(M)=>{const t=location.hash.slice(1),m=document.getElementById('tabs').getBoundingClientRect(),D=document.getElementById('duo'),d=D.getBoundingClientRect();
              const pc=(c)=>{const cb=c.getBoundingClientRect(),bb=D.querySelector('.db-g .ind-bar').getBoundingClientRect();return (cb.left+cb.width/2-bb.left)/bb.width*100;};
              const ca=[...D.querySelectorAll('.irow>.ir')].map(e=>[Math.round(e.getBoundingClientRect().left),Math.round(e.getBoundingClientRect().top)]);
              const a=D.querySelector('.db-cur.db-a'),s=D.querySelector('.db-cur.db-s');const ST=[[0,[255,45,45]],[33,[255,154,31]],[66,[34,197,94]],[100,[0,229,255]]];const ex=(p,inv)=>{if(inv)p=100-p;p=Math.max(0,Math.min(100,p));let c;for(let k=1;k<ST.length;k++){if(p<=ST[k][0]){const t=(p-ST[k-1][0])/(ST[k][0]-ST[k-1][0]);c=ST[k-1][1].map((x,j)=>Math.round(x+(ST[k][1][j]-x)*t));break;}}return `rgb(${c.join(', ')})`;};
              const okc=(el,inv)=>{const cb=el.getBoundingClientRect(),bb=el.parentElement.querySelector('.ind-bar').getBoundingClientRect();const p=(cb.left+cb.width/2-bb.left)/bb.width*100;return getComputedStyle(el).color===ex(p,inv)||getComputedStyle(el).color===ex(+el.dataset.p,inv);};
              const colOk=okc(a,false)&&okc(s,true);
              return {cards:D.querySelectorAll('.card').length,full:Math.abs(d.width-m.width)<=1,order:d.bottom<=m.top+1,ca,
                ea:Math.abs(pc(a)-avPos(AV[t].score)),es:Math.abs(pc(s)-Math.max(0,Math.min(100,IND[t].value))),va:AV[t].score,vs:IND[t].value,
                colors:[getComputedStyle(a).color,getComputedStyle(s).color],leg:D.querySelector('.db-leg')?'légende encore présente':'aucune',
                distinct:!D.querySelector('.db-leg')&&(D.querySelector('.duo-scales')||{textContent:''}).textContent.includes('deux échelles linéaires distinctes')&&D.querySelector('.duo-scales').textContent.includes('contrarienne'),bars:D.querySelectorAll('.irow .db-g').length,
                scales:D.querySelector('.db-top').textContent.includes('−100 · Vente')&&D.querySelector('.db-bot').textContent.includes('0 · Peur extrême')&&D.querySelector('.db-bot').textContent.includes('Euphorie · 100'),
                ment:D.querySelector('.duo-info').textContent.includes(M),src:D.querySelectorAll('.duo-info .ir-src').length,clean:!/Source|Score >|Calcul reproductible|purement informatif/.test(D.querySelector('.irow').textContent),spread:[...document.querySelectorAll('section.tab.on .as-flex')].every(e=>{const it=e.querySelectorAll('.as-it');return it.length>1&&Math.max(...[...it].map(x=>x.getBoundingClientRect().right))>e.getBoundingClientRect().right-(innerWidth>600?40:400)}),closed:!D.querySelector('.card').classList.contains('acc-open'),
                old:document.querySelectorAll('#ind .card,#av .card').length,colOk,ow:document.documentElement.scrollWidth>innerWidth+1,h:Math.round(d.height)}}""",MENT)
            oneline=all(r['ca'][k][0]>r['ca'][k-1][0] for k in range(1,len(r['ca']))) if w>1100 else True
            chk(r['cards']==1 and r['old']==0 and r['bars']==1 and r['full'] and r['order'] and r['ment'] and r['closed'] and not r['ow'] and oneline and r['ea']<1 and r['es']<1 and r['distinct'] and r['scales'] and r['src']==2 and r['clean'] and r['spread'] and r['colors'][0]!=r['colors'][1] and r['colOk'],
                f"{t}: 1 carte ({r['h']} px), 1 barre fusionnée · curseur A/V {r['va']:+.1f} écart {r['ea']:.2f} pt · curseur sentiment {r['vs']:.1f} écart {r['es']:.2f} pt · couleurs A/V {r['colors'][0]} = barre, sentiment {r['colors'][1]} = miroir : {'vérifié' if r['colOk'] else 'FAUX'} · légende « {r['leg'][:70]} » · ligne épurée (titre, scores, barre) · sources et mention dans le détail · résumés étalés")
            if t in('actions','obligations'): pg.screenshot(path=f'{OUT}apercu-fusion-{t}{sfx}.png')
        pg.evaluate("location.hash='actions'");pg.wait_for_timeout(900);pg.evaluate('scrollTo(0,0)');pg.click('#duo h2');pg.wait_for_timeout(900)
        dc=pg.evaluate("[...document.querySelectorAll('#duo canvas')].map(c=>{const g=Chart.getChart(c);return [c.id,c.clientWidth,g?g.data.datasets[0].data.length:0]})")
        chk(len(dc)>=2 and all(x[1]>50 and x[2]>0 for x in dc),f'carte dépliée : historiques des deux indicateurs {dc}')
        pg.screenshot(path=f'{OUT}apercu-fusion-deplie{sfx}.png',full_page=True);pg.click('#duo h2');pg.wait_for_timeout(400)
        for t,first in [('actions','Secteur'),('obligations','Segment')]:
            pg.evaluate(f"location.hash='{t}'");pg.wait_for_timeout(900)
            card=pg.locator(f'#p{t}>.card.no-group:not(.pays-card):not(.ob-card:not([data-cc=us]))')
            if 'acc-open' not in (card.get_attribute('class') or ''): pg.click(f'#p{t}>.card.no-group>.acc-head');pg.wait_for_timeout(700)
            pe=pg.evaluate("""(t)=>{const L=t==='actions'?SEC.sectors:OB_GROUPS.us.map(k=>OB.segments.find(s=>s.key===k));const ST=[[0,[255,45,45]],[33,[255,154,31]],[66,[34,197,94]],[100,[0,229,255]]];const ex=(p,inv)=>{if(inv)p=100-p;p=Math.max(0,Math.min(100,p));let c;for(let k=1;k<ST.length;k++){if(p<=ST[k][0]){const t=(p-ST[k-1][0])/(ST[k][0]-ST[k-1][0]);c=ST[k-1][1].map((x,j)=>Math.round(x+(ST[k][1][j]-x)*t));break;}}return `rgb(${c.join(', ')})`;};
              const okc=(el,inv)=>{const cb=el.getBoundingClientRect(),bb=el.parentElement.querySelector('.ind-bar').getBoundingClientRect();const p=(cb.left+cb.width/2-bb.left)/bb.width*100;return getComputedStyle(el).color===ex(p,inv)||getComputedStyle(el).color===ex(+el.dataset.p,inv);};return [...document.querySelectorAll('#p'+t+'>.card.no-group:not(.pays-card):not(.ob-card:not([data-cc=us])) .sec')].map((e,i)=>{const g=e.querySelector('.db-g'),bb=g.querySelector('.ind-bar').getBoundingClientRect(),p=c=>{const r=c.getBoundingClientRect();return (r.left+r.width/2-bb.left)/bb.width*100};
              return Math.max(Math.abs(p(g.querySelector('.db-a'))-avPos(L[i].av.score)),Math.abs(p(g.querySelector('.db-s'))-L[i].sent.value))+(e.querySelectorAll('.db-g').length-1)*100+(okc(g.querySelector('.db-a'),false)&&okc(g.querySelector('.db-s'),true)?0:1000)})}""",t)
            chk(max(pe)<1,f"{t}: une barre fusionnée par ligne, curseurs à la bonne place et couleurs vérifiées (A/V = couleur de la barre, sentiment = couleur de la barre), écart max {max(pe):.2f} pt")
            r=pg.evaluate("""(t)=>{const c=document.querySelector('#p'+t+'>.card.no-group');const rows=[...c.querySelectorAll('.sec>.sr')];const hd=c.querySelector('.sr-hd');
              const xs=e=>[...e.children].map(x=>Math.round(x.getBoundingClientRect().left));
              const h0=hd.offsetParent?xs(hd):null;
              return {n:rows.length,hd:!!h0,align:h0?rows.every(r=>JSON.stringify(xs(r))===JSON.stringify(h0)):null,btn:rows.every(r=>r.querySelectorAll('.sr-btn').length===2),
                 one:rows.map(r=>{const L=[...r.children].map(x=>x.getBoundingClientRect().left);let n=1;for(let k=1;k<L.length;k++)if(L[k]<=L[k-1])n++;return n;}),
                 ment:c.querySelector('.sr-mention').textContent.includes("Indicateur composite APEX, purement informatif"),
                 dets:[...c.querySelectorAll('.sec-det')].every(d=>d.textContent.includes("Indicateur composite APEX, purement informatif")),
                 sum:c.querySelector('.acc-sum').textContent.slice(0,60),over:[...c.querySelectorAll('.sr>*')].filter(e=>e.scrollWidth>e.clientWidth+1).length,
                 ow:document.documentElement.scrollWidth>innerWidth+1}}""",t)
            lay=(r['hd'] and r['align'] and max(r['one'])==1) if w>1100 else (not r['hd'] and max(r['one'])<=4)
            chk(r['n'] in(5,11) and r['btn'] and r['ment'] and r['dets'] and r['over']==0 and not r['ow'] and lay,
                f"{t}: {r['n']} lignes · en-tête {'aligné' if r['align'] else ('masqué (mobile)' if not r['hd'] else 'NON aligné')} · rangées par ligne {sorted(set(r['one']))} · 2 boutons par ligne · mention en tête et dans chaque détail · résumé « {r['sum']}… »")
            pg.evaluate(f"document.querySelector('#p{t}>.card.no-group:not(.pays-card):not(.ob-card:not([data-cc=us])) .sec-grid').scrollIntoView()");pg.wait_for_timeout(300)
            pg.screenshot(path=f'{OUT}apercu-fusion-lignes-{t}{sfx}.png')
            # ouvrir un panneau (liste) par bouton
            k=0 if t=='actions' else 4
            pg.locator(f'#p{t}>.card.no-group:not(.pays-card):not(.ob-card:not([data-cc=us])) .sec').nth(k).locator('.sr-btn').nth(0).click();pg.wait_for_timeout(500)
            st=pg.evaluate(f"(()=>{{const s=document.querySelectorAll('#p{t}>.card.no-group:not(.pays-card):not(.ob-card:not([data-cc=us])) .sec')[{k}];const d=s.querySelector('.sec-list'),r=s.querySelector('.sr').getBoundingClientRect(),dr=d.getBoundingClientRect();return {{open:d.open,below:dr.top>=r.bottom-1,full:dr.width>=r.width-40,btn:s.querySelector('.sr-btn').getAttribute('aria-expanded')}}}})()")
            chk(st['open'] and st['below'] and st['full'] and st['btn']=='true',f"{t}: bouton → panneau ouvert sous la ligne, pleine largeur {st}")
            cp=pg.locator(f'#p{t}>.card.no-group:not(.pays-card):not(.ob-card:not([data-cc=us])) .sec').nth(k).locator('.sec-list .cp').nth(1);cp.scroll_into_view_if_needed();exp=cp.get_attribute('data-c');cp.click();pg.wait_for_timeout(250)
            chk(pg.evaluate("navigator.clipboard.readText()")==exp,f'{t}: copier {exp}')
            pg.evaluate(f"document.querySelectorAll('#p{t}>.card.no-group:not(.pays-card):not(.ob-card:not([data-cc=us])) .sec')[{k}].scrollIntoView()");pg.wait_for_timeout(300)
            pg.screenshot(path=f'{OUT}apercu-fusion-panneau-{t}{sfx}.png')
            pg.locator(f'#p{t}>.card.no-group:not(.pays-card):not(.ob-card:not([data-cc=us])) .sec').nth(k).locator('.sr-btn').nth(1).click();pg.wait_for_timeout(700)
            n=pg.evaluate(f"[...document.querySelectorAll('#p{t}>.card.no-group:not(.pays-card):not(.ob-card:not([data-cc=us])) .sec')[{k}].querySelectorAll('.sec-det canvas')].map(c=>{{const g=Chart.getChart(c);return g?g.data.datasets[0].data.length:0}})")
            chk(len(n)==2 and min(n)>=40,f'{t}: détail 1 an ouvert, graphiques {n}')
            pg.evaluate(f"document.querySelectorAll('#p{t}>.card.no-group:not(.pays-card):not(.ob-card:not([data-cc=us])) .sec')[{k}].querySelectorAll('.sr-btn').forEach(b=>b.getAttribute('aria-expanded')==='true'&&b.click())");pg.wait_for_timeout(300)
            chk(not pg.evaluate("document.documentElement.scrollWidth>innerWidth+1"),f'{t}: pas de scroll horizontal')
        chk(not logs,f'console : {logs or "aucune erreur"}');ctx.close()
    b.close()
print('OK' if ok else 'PROBLÈME')
