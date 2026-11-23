"""Vérifie les accordéons (repliés par défaut, dépliage, graphiques non vides, mémorisation) à 1920 et 390 px."""
import sys
from playwright.sync_api import sync_playwright
B='/workspace/invest/patrimoine-dashboard/'
URL=sys.argv[1] if len(sys.argv)>1 else 'file://'+B+'index.html'
OUT=sys.argv[2] if len(sys.argv)>2 else B
tabs=['immobilier','actions','obligations','crypto','liquidites']; ok=True
STATE="""()=>{const tab=document.querySelector('section.tab.on');const cards=[...tab.querySelectorAll('.card.acc'),...document.querySelectorAll('.side .card.acc')];
 const vis=el=>{const r=el.getBoundingClientRect();return r.height>0&&r.width>0};
 const bodies=cards.map(c=>Math.round(c.querySelector('.acc-in').getBoundingClientRect().height));
 const keepInd=['.ind-val','.db','.ind-date','.db-cur.db-s'].every(s=>vis(document.querySelector('#duo '+s)));
 const keepAv=['.db-cur.db-a','.av-val','.db-top','.db-bot'].every(s=>vis(document.querySelector('#duo '+s)));
 const hidden=['#duo .duo-col .ind-spark','#duo .ind-stats','#duo .duo-col+.duo-col .ind-spark','#duo .av-warn'].map(s=>document.querySelector(s)).every(e=>{const r=e.getBoundingClientRect();const p=e.closest('.acc-in').getBoundingClientRect();return p.height<1;});
 const charts=[...tab.querySelectorAll('canvas'),...document.querySelectorAll('.side canvas')].filter(c=>!c.closest('details:not([open])')).map(c=>{const k=Chart.getChart(c);return {id:c.id,w:c.clientWidth,h:c.clientHeight,n:k?k.data.datasets.reduce((s,d)=>s+d.data.filter(v=>v!=null).length,0):0}});
 return {n:cards.length,open:cards.filter(c=>c.classList.contains('acc-open')).length,bodies,keepInd,keepAv,hidden,charts,footer:!!document.querySelector('footer'),overflow:document.documentElement.scrollWidth>innerWidth+1,btn:document.getElementById('accAll').textContent}}"""
with sync_playwright() as p:
    b=p.chromium.launch(executable_path='/usr/bin/google-chrome',args=['--no-sandbox'])
    for w,h,mob in [(1920,1080,False),(390,844,True)]:
        ctx=b.new_context(viewport={'width':w,'height':h},is_mobile=mob,has_touch=mob); pg=ctx.new_page(); logs=[]
        pg.on('console',lambda m: logs.append(f'{m.type}: {m.text}') if m.type in('error','warning') else None)
        pg.on('pageerror',lambda e: logs.append(f'pageerror: {e}'))
        pg.goto(URL+'#immobilier',wait_until='networkidle'); pg.evaluate("localStorage.clear()"); pg.reload(wait_until='networkidle'); pg.wait_for_timeout(600)
        for t in tabs:
            pg.evaluate(f"location.hash='{t}'"); pg.wait_for_timeout(1500); pg.evaluate("scrollTo(0,0)")
            s=pg.evaluate(STATE)
            closed=s['open']==0 and max(s['bodies'])==0 and s['keepInd'] and s['keepAv'] and s['hidden'] and not s['overflow']
            print(w,t,'replié :',s['n'],'cartes,',s['open'],'ouvertes, corps max',max(s['bodies']),'px | essentiels visibles',s['keepInd'] and s['keepAv'],'| repliés cachés',s['hidden'],'| pied de page',s['footer'],'|',s['btn'], 'OK' if closed else 'ERREUR')
            ok&=closed
            if w==1920: pg.screenshot(path=f'{OUT}apercu-replie-{t}.png',full_page=True)
            if w==390 and t=='actions': pg.screenshot(path=f'{OUT}apercu-replie-mobile-actions.png',full_page=True)
            pg.click('#accAll'); pg.wait_for_timeout(700)
            s=pg.evaluate(STATE)
            bad=[c for c in s['charts'] if c['w']<50 or c['h']<20 or c['n']==0]
            print('   déplié :',s['open'],'/',s['n'],'| graphiques',len(s['charts']),'vides/mal dimensionnés',bad or 'aucun','|',s['btn'])
            ok&= s['open']==s['n'] and not bad and not s['overflow']
            if w==1920 and t=='actions':
                pg.reload(wait_until='networkidle'); pg.wait_for_timeout(1500)
                s2=pg.evaluate(STATE); print('   après rechargement (localStorage) :',s2['open'],'/',s2['n'],'ouvertes'); ok&=s2['open']==s2['n']
                pg.evaluate("accAll(false)"); pg.wait_for_timeout(500)
                pg.click('#pactions .card.acc .acc-head'); pg.wait_for_timeout(900); pg.evaluate("scrollTo(0,0)")
                pg.screenshot(path=f'{OUT}apercu-deplie-actions-indices.png')
            pg.evaluate("accAll(false)"); pg.wait_for_timeout(400)
        print(w,'console :','\n'.join(logs) or 'aucune erreur'); ok&=not logs; ctx.close()
    b.close()
print('OK' if ok else 'PROBLÈME')
