"""Captures de l\'onglet Crypto avec les fiches APEX BTC / ETH / MSTR."""
import os
from playwright.sync_api import sync_playwright
B="/workspace/invest/patrimoine-dashboard/"
OUT=B+"captures/"
os.makedirs(OUT, exist_ok=True)
URL="file://"+B+"index.html#crypto"
ok=True
with sync_playwright() as p:
    b=p.chromium.launch(executable_path="/usr/bin/google-chrome", args=["--no-sandbox","--disable-gpu"])
    pg=b.new_page(viewport={"width":1360,"height":900})
    logs=[]
    pg.on("console", lambda m: logs.append(f"{m.type}: {m.text}") if m.type in ("error","warning") else None)
    pg.on("pageerror", lambda e: logs.append(f"pageerror: {e}"))
    pg.goto(URL, wait_until="networkidle")
    pg.wait_for_timeout(800)
    pg.evaluate("location.hash=\'crypto\'")
    pg.wait_for_timeout(1500)
    pg.add_style_tag(content=".acc-body,.acc-chev{transition:none!important}")
    # Vue repliée (contexte de l\'onglet)
    pg.screenshot(path=OUT+"crypto_fiches_replie.png")
    # Déplier la carte des fiches
    pg.evaluate("""()=>{
      const c=document.getElementById(\'cxFiches\');
      if(c && typeof accToggle===\'function\') accToggle(c,true,false);
      else if(c) c.classList.add(\'acc-open\');
    }""")
    pg.wait_for_timeout(600)
    box=pg.evaluate("""()=>{
      const c=document.getElementById(\'cxFiches\');
      const r=c.getBoundingClientRect();
      return {h:c.scrollHeight, w:c.scrollWidth, open:c.classList.contains(\'acc-open\'), nSec:c.querySelectorAll(\'.sec\').length, visH:r.height};
    }""")
    print("carte dépliée", box)
    el=pg.query_selector("#cxFiches")
    el.scroll_into_view_if_needed()
    pg.wait_for_timeout(300)
    el.screenshot(path=OUT+"crypto_fiches.png")
    el.screenshot(path=OUT+"crypto_fiches_cartes.png")
    # Détails des 3 fiches
    pg.evaluate("document.querySelectorAll(\'#cxFiches .sec-det\').forEach(d=>d.open=true)")
    pg.wait_for_timeout(900)
    det=pg.evaluate("""()=>[...document.querySelectorAll(\'#cxFiches .sec-det canvas\')].map(c=>{const k=Chart.getChart(c);return [c.id,c.clientWidth,c.clientHeight,k?k.data.datasets[0].data.filter(v=>v!=null).length:0]})""")
    print("canvas détails", det)
    ok&=bool(det) and all(x[3]>0 and x[2]>=20 for x in det)
    el.screenshot(path=OUT+"crypto_fiches_detail.png")
    # Page : déplier aussi le groupe graphiques, viewport plus haut pour une vue d\'ensemble
    pg.evaluate("""()=>{
      const g=document.querySelector(\'#pcrypto>.acc-group\');
      if(g && typeof accToggle===\'function\') accToggle(g,true,false);
      else if(g) g.classList.add(\'acc-open\');
    }""")
    pg.wait_for_timeout(800)
    h=pg.evaluate("Math.max(document.body.scrollHeight, document.documentElement.scrollHeight)")
    print("document height", h)
    pg.set_viewport_size({"width":1360,"height":min(int(h)+40, 6000)})
    pg.wait_for_timeout(400)
    pg.screenshot(path=OUT+"crypto_fiches_page.png", full_page=True)
    print("\n".join(logs) or "console : aucune erreur")
    if logs:
        ok=False
    b.close()
print("OK" if ok else "PROBLÈME")
