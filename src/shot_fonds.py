"""Vérifie les listes ETF + 5 actions des secteurs et le bouton copier (1920 et 390 px)."""
import os as _os
_APEX_ROOT = _os.path.abspath(_os.environ.get('APEX_ROOT') or _os.path.join(_os.path.dirname(__file__), '..'))
import sys, re
from playwright.sync_api import sync_playwright
B=_APEX_ROOT + '/'
URL=sys.argv[1] if len(sys.argv)>1 else 'file://'+B+'index.html'
OUT=sys.argv[2] if len(sys.argv)>2 else B
ok=True
with sync_playwright() as p:
    b=p.chromium.launch(executable_path='/usr/bin/google-chrome',args=['--no-sandbox'])
    for w,h,mob in [(1920,1080,False),(390,844,True)]:
        ctx=b.new_context(viewport={'width':w,'height':h},is_mobile=mob,has_touch=mob,permissions=['clipboard-read','clipboard-write']);pg=ctx.new_page();logs=[]
        pg.on('console',lambda m: logs.append(m.type+': '+m.text) if m.type in('error','warning') else None);pg.on('pageerror',lambda e:logs.append(str(e)))
        pg.goto(URL+'#actions',wait_until='networkidle');pg.evaluate('localStorage.clear()');pg.reload(wait_until='networkidle');pg.wait_for_timeout(1200)
        closed=pg.evaluate("[...document.querySelectorAll('#pactions>.card.no-group:not(.pays-card) .sec-list')].filter(d=>d.open).length"); 
        pg.click('#pactions>.card.no-group>.acc-head');pg.wait_for_timeout(700)
        base=pg.evaluate("[...document.querySelectorAll('#pactions>.card.no-group:not(.pays-card) .sec')].map(e=>Math.round(e.getBoundingClientRect().height))")
        print(w,'listes ouvertes au départ',closed,'| hauteur vignettes (vue de base)',base[:4])
        sfx='' if w==1920 else '-mobile'
        # ouvrir la liste Technologie (index 9) pour la capture
        pg.evaluate("document.querySelectorAll('#pactions>.card.no-group:not(.pays-card) .sec-list')[9].open=true");pg.wait_for_timeout(400)
        pg.evaluate("document.querySelectorAll('#pactions>.card.no-group:not(.pays-card) .sec')[9].scrollIntoView()");pg.wait_for_timeout(300)
        pg.screenshot(path=f'{OUT}apercu-fonds-tech{sfx}.png',full_page=False)
        pg.evaluate("document.querySelectorAll('#pactions>.card.no-group:not(.pays-card) .sec-list').forEach(d=>d.open=true)");pg.wait_for_timeout(600)
        r=pg.evaluate("""()=>[...document.querySelectorAll('#pactions>.card.no-group:not(.pays-card) .sec-list')].map(d=>({etf:d.querySelector('.fl-etf code').textContent,n:d.querySelectorAll('.fl li').length,
           tv:[...d.querySelectorAll('.fl li code')].map(c=>c.textContent),mention:d.querySelector('.av-short').textContent.includes("Les prévisions d'analystes peuvent se révéler fausses"),
           over:[...d.querySelectorAll('li,.fl-etf')].filter(e=>e.scrollWidth>e.clientWidth+1).length}))""")
        pat=re.compile(r'^(NASDAQ|NYSE|AMEX|CBOE):[A-Z.]+$')
        for x in r:
            good=x['n']==5 and pat.match(x['etf']) and all(pat.match(t) for t in x['tv']) and x['mention'] and x['over']==0
            ok&=bool(good)
        print('  listes',len(r),'| toutes 1 ETF + 5 actions, symboles valides, mention, sans débordement :',all(x['n']==5 and x['mention'] and x['over']==0 for x in r))
        ow=pg.evaluate("document.documentElement.scrollWidth>innerWidth+1");print('  scroll horizontal',ow);ok&=not ow and closed==0
        pg.screenshot(path=f'{OUT}apercu-fonds-toutes{sfx}.png',full_page=True)
        # bouton copier : API clipboard
        btn=pg.locator('.sec-list .cp').nth(3); btn.scroll_into_view_if_needed(); exp=btn.get_attribute('data-c'); btn.click(); pg.wait_for_timeout(250)
        got=pg.evaluate("navigator.clipboard.readText()"); tip=pg.evaluate("getComputedStyle(document.querySelectorAll('#pactions>.card.no-group:not(.pays-card) .sec-list .cp')[3],'::after').content")
        print('  copier (clipboard API) :',exp,'→ presse-papiers',got,'| retour',tip); ok&=got==exp and 'Copié' in tip
        if w==1920:
            pg.evaluate("document.querySelectorAll('#pactions>.card.no-group:not(.pays-card) .sec-list .cp')[3].closest('li').scrollIntoView({block:'center'})"); pg.screenshot(path=f'{OUT}apercu-fonds-copie.png')
        # repli execCommand
        pg.evaluate("Object.defineProperty(navigator,'clipboard',{value:undefined,configurable:true})")
        b2=pg.locator('.sec-list .cp').nth(7); exp2=b2.get_attribute('data-c'); b2.click(); pg.wait_for_timeout(250)
        cls=b2.get_attribute('class'); print('  copier (repli execCommand) :',exp2,'| classe',cls); ok&='ok' in cls
        print(w,'console:',logs or 'aucune erreur'); ok&=not logs; ctx.close()
    b.close()
print('OK' if ok else 'PROBLÈME')
