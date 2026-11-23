import sys
from playwright.sync_api import sync_playwright
U,O=sys.argv[1],sys.argv[2];ok=True;errs=[]
with sync_playwright() as p:
  b=p.chromium.launch(executable_path='/usr/bin/google-chrome',args=['--no-sandbox'])
  for w in (1920,390):
    pg=b.new_page(viewport={'width':w,'height':900});pg.on('pageerror',lambda e:errs.append(str(e)));pg.on('console',lambda m:m.type=='error' and errs.append(m.text))
    pg.goto(U);pg.evaluate("localStorage.clear()");pg.reload();pg.wait_for_timeout(1500)
    hits=[]
    for t in ['actions','obligations','crypto','liquidites','immobilier']:
      pg.evaluate(f"location.hash='{t}'");pg.wait_for_timeout(900)
      pg.evaluate("document.querySelectorAll('details').forEach(d=>d.open=true)")
      n=pg.evaluate("(document.body.innerText.match(/ophir/gi)||[]).length + (document.title.match(/ophir/gi)||[]).length")
      hits.append((t,n))
    h=pg.evaluate("(()=>{const h=document.querySelector('#hh h1');const r=h.getBoundingClientRect();return {t:h.textContent,title:document.title,w:r.width,h:r.height,sw:document.documentElement.scrollWidth,meta:document.querySelector('meta[name=apple-mobile-web-app-title]').content}})()")
    good=all(n==0 for _,n in hits) and h['t']=='APEX INDICATOR INVESTMENT' and h['sw']<=w
    ok&=good;print('✔' if good else '✘',w,hits,h)
    pg.evaluate("location.hash='actions'");pg.wait_for_timeout(600);pg.evaluate("scrollTo(0,0)")
    pg.screenshot(path=f'{O}/entete_apex_{w}.png',clip={'x':0,'y':0,'width':w,'height':260 if w>500 else 330})
  b.close()
print('console:',errs or 'aucune erreur');print('OK' if ok and not errs else 'PROBLÈME')
