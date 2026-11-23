"""Capture pleine page de chaque onglet + contrôle console et graphiques vides."""
import sys
from playwright.sync_api import sync_playwright
B='/workspace/invest/patrimoine-dashboard/'
URL=sys.argv[1] if len(sys.argv)>1 else 'file://'+B+'index.html'
OUT=sys.argv[2] if len(sys.argv)>2 else B
tabs=['immobilier','actions','obligations','crypto','liquidites']
ok=True
with sync_playwright() as p:
    b=p.chromium.launch(executable_path='/usr/bin/google-chrome',args=['--no-sandbox'])
    pg=b.new_page(viewport={'width':1360,'height':900}); logs=[]
    pg.on('console',lambda m: logs.append(f'{m.type}: {m.text}') if m.type in('error','warning') else None)
    pg.on('pageerror',lambda e: logs.append(f'pageerror: {e}'))
    pg.goto(URL+'#immobilier',wait_until='networkidle'); pg.wait_for_timeout(800)
    for t in tabs:
        pg.evaluate(f"location.hash='{t}'"); pg.wait_for_timeout(1500)
        info=pg.evaluate("""()=>[...document.querySelectorAll('section.tab.on canvas')].filter(c=>!c.closest('details:not([open])')).map(c=>{const ch=Chart.getChart(c);return {id:c.id,h:c.clientHeight,n:ch?ch.data.datasets.reduce((s,d)=>s+d.data.filter(v=>v!=null&&!(typeof v==='number'&&isNaN(v))).length,0):-1};})""")
        empty=[i for i in info if i['n']<=0 or i['h']<20]
        print(t,len(info),'graphiques', 'VIDES: '+str(empty) if empty else 'tous remplis')
        ok&=not empty
        pg.screenshot(path=f'{OUT}apercu-{t}.png',full_page=True)
    print('\n'.join(logs) or 'console : aucune erreur')
    ok&=not logs
    b.close()
print('OK' if ok else 'PROBLÈME')
