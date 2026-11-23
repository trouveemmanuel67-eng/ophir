"""Captures de l'onglet Énergie (fiches APEX)."""
import os
from playwright.sync_api import sync_playwright
B="/workspace/invest/patrimoine-dashboard/"
OUT=B+"captures/"
os.makedirs(OUT, exist_ok=True)
URL="file://"+B+"index.html#energie"
ok=True
with sync_playwright() as p:
    b=p.chromium.launch(executable_path="/usr/bin/google-chrome", args=["--no-sandbox","--disable-gpu"])
    pg=b.new_page(viewport={"width":1360,"height":900})
    logs=[]
    pg.on("console", lambda m: logs.append(f"{m.type}: {m.text}") if m.type in ("error","warning") else None)
    pg.on("pageerror", lambda e: logs.append(f"pageerror: {e}"))
    pg.goto(URL, wait_until="networkidle")
    pg.wait_for_timeout(800)
    pg.evaluate("location.hash='energie'")
    pg.wait_for_timeout(1500)
    pg.add_style_tag(content=".acc-body,.acc-chev{transition:none!important}")
    nav=pg.evaluate("""()=>{
      const n=[...document.querySelectorAll('#nav a')].map(a=>({id:a.id,text:a.textContent,href:a.getAttribute('href'),on:a.classList.contains('on')}));
      const t=document.querySelector('#penergie');
      const c=document.getElementById('enFiches');
      return {nav:n, tab:!!t, display:t&&getComputedStyle(t).display, fiches:!!c, nSec:c?c.querySelectorAll('.sec').length:0, nGh:c?c.querySelectorAll('.en-gh').length:0};
    }""")
    print("nav/tab", nav)
    ok &= bool(nav.get('tab')) and nav.get('display')!='none' and nav.get('nSec',0)>=10
    # Déplier la carte (accordéon)
    pg.evaluate("""()=>{
      const c=document.getElementById('enFiches');
      if(c && typeof accToggle==='function') accToggle(c,true,false);
      else if(c) c.classList.add('acc-open');
    }""")
    pg.wait_for_timeout(800)
    el=pg.query_selector("#enFiches")
    if not el:
        print("PAS DE CARTE enFiches")
        ok=False
    else:
        el.scroll_into_view_if_needed()
        pg.wait_for_timeout(300)
        el.screenshot(path=OUT+"energie_fiches.png")
        pg.screenshot(path=OUT+"energie_onglet.png")
        # Détail de quelques fiches (NG, WTI, BNO, XLE)
        pg.evaluate("""()=>{
          const want=['NG=F','CL=F','BNO','XLE'];
          document.querySelectorAll('#enFiches .sec-det').forEach(d=>{
            const tile=d.closest('.sec');
            const t=tile?tile.innerText:'';
            if(want.some(s=>t.includes(s))) d.open=true;
          });
        }""")
        pg.wait_for_timeout(1200)
        det=pg.evaluate("""()=>[...document.querySelectorAll('#enFiches .sec-det[open] canvas')].map(c=>{const k=Chart.getChart(c);return [c.id,c.clientWidth,c.clientHeight,k?k.data.datasets[0].data.filter(v=>v!=null).length:0]})""")
        print("canvas détails", det)
        ok &= bool(det) and all(x[3]>0 and x[2]>=20 for x in det)
        el.screenshot(path=OUT+"energie_detail.png")
        h=pg.evaluate("Math.max(document.body.scrollHeight, document.documentElement.scrollHeight)")
        print("document height", h)
        pg.set_viewport_size({"width":1360,"height":min(int(h)+40, 9000)})
        pg.wait_for_timeout(400)
        pg.screenshot(path=OUT+"energie_page.png", full_page=True)
    print("\n".join(logs) or "console : aucune erreur")
    if logs:
        ok=False
        print("LOGS", logs)
    b.close()
print("OK" if ok else "PROBLÈME")
