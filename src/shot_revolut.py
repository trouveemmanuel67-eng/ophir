"""Captures de contrôle après application de la règle Revolut (17/11/2026) : onglets Actions, Obligations, Métaux, Énergie."""
import sys
from playwright.sync_api import sync_playwright
B="/workspace/invest/patrimoine-dashboard/"; OUT=B+"captures/revolut/"
URL=(sys.argv[1] if len(sys.argv)>1 else "file://"+B+"index.html")
pref=(sys.argv[2] if len(sys.argv)>2 else "local")
with sync_playwright() as p:
    b=p.chromium.launch(executable_path="/usr/bin/google-chrome", args=["--no-sandbox","--disable-gpu"])
    pg=b.new_page(viewport={"width":1360,"height":900}); logs=[]
    pg.on("console", lambda m: logs.append(f"{m.type}: {m.text}") if m.type=="error" else None)
    pg.on("pageerror", lambda e: logs.append(f"pageerror: {e}"))
    pg.goto(URL, wait_until="networkidle"); pg.wait_for_timeout(1000)
    for tab in ['actions','obligations','metaux','energie']:
        pg.evaluate(f"location.hash='{tab}'"); pg.wait_for_timeout(1500)
        pg.add_style_tag(content=".acc-body,.acc-chev{transition:none!important}")
        pg.evaluate("""()=>{document.querySelectorAll('.card').forEach(c=>{if(typeof accToggle==='function'&&c.querySelector('.acc-head'))accToggle(c,true,false);});
          document.querySelectorAll('details.sec-list').forEach(d=>d.open=true);}""")
        pg.wait_for_timeout(1200)
        pg.screenshot(path=OUT+f"{pref}_{tab}.png", full_page=True)
        txt=pg.evaluate("()=>document.body.innerText")
        bad=[w for w in ['AMEX:XLC','AMEX:XLE','AMEX:URA','TSX:U-U','XETR:4GLD','LSE:SILV','NASDAQ:SHY','TSE:1617','SP:XTJ','KRX:005930','EURONEXT:SOI','LSE:SAUS'] if w in txt]
        good=[w for w in ['ZPDK','XDW0','URNU','GLDA','IUSU','IBC6','SXRY','Repère de marché','NYSE:TAK'] if w in txt]
        print(tab,'| anciens visibles:',bad,'| nouveaux visibles:',good)
    print('erreurs JS:',logs[:10])
    b.close()
