"""Vérifie la colonne INDICATEUR (1360, 1920, mobile) et capture chaque onglet en 1920×1080."""
import sys
from playwright.sync_api import sync_playwright
B='/workspace/invest/patrimoine-dashboard/'
URL=sys.argv[1] if len(sys.argv)>1 else 'file://'+B+'index.html'
OUT=sys.argv[2] if len(sys.argv)>2 else B
tabs=['immobilier','actions','obligations','crypto','liquidites']; ok=True
with sync_playwright() as p:
    b=p.chromium.launch(executable_path='/usr/bin/google-chrome',args=['--no-sandbox'])
    for name,vp,mob in [('1920',{'width':1920,'height':1080},False),('1360',{'width':1360,'height':900},False),('mobile',{'width':390,'height':844},True)]:
        ctx=b.new_context(viewport=vp,is_mobile=mob,has_touch=mob,device_scale_factor=2 if mob else 1); pg=ctx.new_page(); logs=[]
        pg.on('console',lambda m: logs.append(f'{m.type}: {m.text}') if m.type in('error','warning') else None)
        pg.on('pageerror',lambda e: logs.append(f'pageerror: {e}'))
        pg.goto(URL+'#immobilier',wait_until='networkidle'); pg.wait_for_timeout(800)
        for t in tabs:
            pg.evaluate(f"location.hash='{t}'"); pg.wait_for_timeout(1200); pg.evaluate("scrollTo(0,0)")
            r=pg.evaluate("""()=>{const a=document.getElementById('duo').getBoundingClientRect(),m=document.getElementById('tabs').getBoundingClientRect();
              const ch=Chart.getChart('cInd');const empty=[...document.querySelectorAll('section.tab.on canvas, #duo canvas')].filter(c=>!c.closest('details:not([open])')).filter(c=>{const k=Chart.getChart(c);return !k||c.clientHeight<20||k.data.datasets.reduce((s,d)=>s+d.data.filter(v=>v!=null).length,0)==0}).map(c=>c.id);
              return {aside_x:Math.round(a.left),aside_w:Math.round(a.width),main_w:Math.round(m.width),below:a.top>=m.bottom-1,above:a.bottom<=m.top+1,spark:ch?ch.data.datasets[0].data.length:0,val:document.querySelector('.ind-val span').textContent,empty,overflow:document.documentElement.scrollWidth>innerWidth+1}}""")
            pg.evaluate("scrollTo(0,Math.min(1200,document.querySelector('.layout').offsetHeight-document.getElementById('duo').offsetHeight-40))"); pg.wait_for_timeout(200)
            top=pg.evaluate("Math.round(document.getElementById('duo').getBoundingClientRect().top)")
            line=r['above'] and abs(r['aside_w']-r['main_w'])<=1
            print(name,t,r,'ligne pleine largeur au-dessus du contenu' if line else 'ERREUR disposition')
            if r['empty'] or r['overflow'] or not line or r['spark']==0: ok=False
            if name=='1920':
                pg.evaluate("scrollTo(0,0)"); pg.wait_for_timeout(200)
                pg.screenshot(path=f'{OUT}apercu-indicateur-{t}.png')
            if name=='mobile' and t=='crypto':
                pg.screenshot(path=f'{OUT}apercu-indicateur-mobile-crypto.png',full_page=True)
        print(name,'console :','\n'.join(logs) or 'aucune erreur'); ok&=not logs; ctx.close()
    b.close()
print('OK' if ok else 'PROBLÈME')
