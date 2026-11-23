"""Contrôle JS de tous les onglets + captures du critère Charte graphique (fiche BTC, fiche AMD n'existe pas sur le site)."""
import os as _os
_APEX_ROOT = _os.path.abspath(_os.environ.get('APEX_ROOT') or _os.path.join(_os.path.dirname(__file__), '..'))
from playwright.sync_api import sync_playwright
B=_APEX_ROOT + "/"; OUT=B+"captures/"
logs=[]
with sync_playwright() as p:
    b=p.chromium.launch(executable_path="/usr/bin/google-chrome", args=["--no-sandbox","--disable-gpu"])
    pg=b.new_page(viewport={"width":1360,"height":1000})
    pg.on("console", lambda m: logs.append(f"{m.type}: {m.text}") if m.type in ("error",) else None)
    pg.on("pageerror", lambda e: logs.append(f"pageerror: {e}"))
    pg.goto("file://"+B+"index.html", wait_until="networkidle"); pg.wait_for_timeout(800)
    for t in ["actions","obligations","metaux","crypto","liquidites","immobilier"]:
        pg.evaluate(f"location.hash='{t}'"); pg.wait_for_timeout(1200)
        pg.evaluate("document.querySelectorAll('details').forEach(d=>d.open=true)"); pg.wait_for_timeout(700)
        n=pg.evaluate("document.body.innerText.split('Charte graphique').length-1")
        print(t,"mentions « Charte graphique » :",n)
    pg.evaluate("location.hash='crypto'"); pg.wait_for_timeout(1200)
    pg.add_style_tag(content=".acc-body,.acc-chev{transition:none!important}")
    pg.evaluate("""()=>{const c=document.getElementById('cxFiches'); if(c&&typeof accToggle==='function') accToggle(c,true,false); else if(c) c.classList.add('acc-open');
      document.querySelectorAll('#cxFiches details').forEach(d=>d.open=false); const d=document.querySelector('#cxFiches .sec-det'); if(d) d.open=true;}""")
    pg.wait_for_timeout(1000)
    sec=pg.query_selector("#cxFiches .sec"); sec.scroll_into_view_if_needed(); pg.wait_for_timeout(300)
    sec.screenshot(path=OUT+"charte_btc_fiche.png")
    inds=pg.query_selector("#cxFiches .sec .cx-inds"); inds.screenshot(path=OUT+"charte_btc_indicateurs.png")
    pg.evaluate("document.querySelectorAll('#cxFiches details').forEach(d=>d.open=false); const m=[...document.querySelectorAll('#cxFiches details.ind-meth')].find(d=>d.querySelector('summary').textContent.includes('Méthode')); if(m) m.open=true;")
    pg.wait_for_timeout(500)
    m=pg.query_selector("#cxFiches details.ind-meth:not(.sec-det)")
    if m: m.screenshot(path=OUT+"charte_methode.png")
    b.close()
print("\n".join(logs) or "console : aucune erreur JS")
