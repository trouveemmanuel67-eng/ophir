"""Vérifie la mise en page pleine largeur et le barre ACHAT / VENTE (1920, 1600, 1366, 390) ; captures 1920×1080."""
import sys, math
from playwright.sync_api import sync_playwright
B='/workspace/invest/patrimoine-dashboard/'
URL=sys.argv[1] if len(sys.argv)>1 else 'file://'+B+'index.html'
OUT=sys.argv[2] if len(sys.argv)>2 else B
tabs=['immobilier','actions','obligations','crypto','liquidites']; ok=True
JS="""()=>{const r=id=>document.getElementById(id).getBoundingClientRect();const m=r('tabs'),i=r('duo'),a=r('duo');
 const cur=document.querySelector('#duo .db-cur.db-a');const ang=+parseFloat(cur.style.left).toFixed(2);const tgt=+avPos(AV[location.hash.slice(1)].score).toFixed(2);
 const cb=cur.getBoundingClientRect(),bb=document.querySelector('#duo .db-g .ind-bar').getBoundingClientRect();const px=+(((cb.left+cb.width/2-bb.left)/bb.width)*100).toFixed(1);
 const empty=[...document.querySelectorAll('section.tab.on canvas, .side canvas')].filter(c=>!c.closest('details:not([open])')).filter(c=>{const k=Chart.getChart(c);return !k||c.clientHeight<20||k.data.datasets.reduce((s,d)=>s+d.data.filter(v=>v!=null).length,0)==0}).map(c=>c.id);
 return {main:[Math.round(m.left),Math.round(m.width)],ind:[Math.round(i.left),Math.round(i.top+scrollY)],av:[Math.round(a.left),Math.round(a.top+scrollY)],mainBottom:Math.round(m.bottom+scrollY),mainTop:Math.round(m.top+scrollY),
  angle:ang,target:tgt,px,score:document.querySelector('.av-val span').textContent,overflow:document.documentElement.scrollWidth>innerWidth+1,empty,
  warn:!!document.querySelector('.av-warn')&&document.querySelector('.av-warn').textContent.includes('Ne constitue pas un conseil ni un signal d')}}"""
with sync_playwright() as p:
    b=p.chromium.launch(executable_path='/usr/bin/google-chrome',args=['--no-sandbox'])
    for w,h,mob in [(1920,1080,False),(1600,900,False),(1366,768,False),(390,844,True)]:
        ctx=b.new_context(viewport={'width':w,'height':h},is_mobile=mob,has_touch=mob); pg=ctx.new_page(); logs=[]
        pg.on('console',lambda m: logs.append(f'{m.type}: {m.text}') if m.type in('error','warning') else None)
        pg.on('pageerror',lambda e: logs.append(f'pageerror: {e}'))
        pg.goto(URL+'#immobilier',wait_until='networkidle'); pg.wait_for_timeout(600)
        for t in tabs:
            pg.evaluate(f"location.hash='{t}'"); pg.wait_for_timeout(1700); pg.evaluate("scrollTo(0,0)")
            r=pg.evaluate(JS)
            lay='lignes pleine largeur au-dessus du contenu' if r['av'][0]==r['ind'][0]==r['main'][0] and r['ind'][1]<r['mainTop'] else 'ERREUR'
            needle_ok=abs(r['angle']-r['target'])<0.05 and abs(r['px']-r['target'])<1.5
            margin=r['main'][0]
            print(w,t,'main',r['main'],'marge',margin,lay,'curseur',r['angle'],'% (mesuré',r['px'],'%) / attendu',r['target'],'OK' if needle_ok else 'ERREUR','score',r['score'],'débordement' if r['overflow'] else '','vides',r['empty'] or '-','mention' if r['warn'] else 'MENTION ABSENTE')
            ok&= needle_ok and not r['overflow'] and not r['empty'] and lay!='ERREUR' and r['warn']
            if w==1920: pg.screenshot(path=f'{OUT}apercu-achatvente-{t}.png')
            if w==390 and t=='actions': pg.screenshot(path=f'{OUT}apercu-achatvente-mobile-actions.png',full_page=True)
        print(w,'console :','\n'.join(logs) or 'aucune erreur'); ok&=not logs; ctx.close()
    b.close()
print('OK' if ok else 'PROBLÈME')
