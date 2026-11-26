"""Captures de l'onglet NARRATIF à 390 px et 1280 px."""
import os
import sys
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(os.environ.get("APEX_ROOT") or Path(__file__).resolve().parents[1])
URL = sys.argv[1] if len(sys.argv) > 1 else "file://" + str(ROOT / "index.html")
OUT = Path(sys.argv[2] if len(sys.argv) > 2 else "/workspace/invest/captures-narratif")
OUT.mkdir(parents=True, exist_ok=True)

def open_narratif(pg):
    pg.evaluate("""() => {
      try { localStorage.setItem('apex-nar-open', '1'); } catch (e) {}
      if (typeof narSetListOpen === 'function') narSetListOpen(true);
    }""")
    pg.wait_for_timeout(400)
    pg.evaluate("""() => {
      const c = document.getElementById('narCard');
      if (c) c.scrollIntoView({block:'start'});
    }""")
    pg.wait_for_timeout(300)

ok = True
logs_all = []
with sync_playwright() as p:
    browser = p.chromium.launch(executable_path="/usr/bin/google-chrome", args=["--no-sandbox"])
    for w, h, name, mobile in ((390, 844, "390", True), (1280, 900, "1280", False)):
        ctx = browser.new_context(viewport={"width": w, "height": h}, is_mobile=mobile, has_touch=mobile)
        pg = ctx.new_page()
        logs = []
        pg.on("console", lambda m: logs.append(f"{m.type}: {m.text}") if m.type in ("error", "warning") else None)
        pg.on("pageerror", lambda e: logs.append(f"pageerror: {e}"))
        sep = "&" if "?" in URL else "?"
        target = URL + ("" if "#narratif" in URL else "#narratif")
        if "v=" not in target and "file:" not in URL:
            # keep existing query
            pass
        pg.goto(target, wait_until="networkidle", timeout=60000)
        pg.wait_for_timeout(800)
        open_narratif(pg)
        card = pg.query_selector("#narCard")
        print(name, "narCard", "OK" if card else "MISSING")
        ok &= bool(card)
        # barre mobile repliée
        if w == 390:
            pg.screenshot(path=str(OUT / "narratif-barre-390.png"))
        pg.screenshot(path=str(OUT / f"narratif-{name}.png"), full_page=True)
        # zoom sur la carte ouverte
        if card:
            card.screenshot(path=str(OUT / f"narratif-carte-{name}.png"))
        # un détail ouvert
        det = pg.query_selector("#narCard details.nar-det")
        if det:
            det.evaluate("el => el.open = true")
            pg.wait_for_timeout(200)
            if w == 390:
                pg.screenshot(path=str(OUT / "narratif-detail-390.png"), full_page=True)
            else:
                pg.screenshot(path=str(OUT / "narratif-detail-1280.png"))
        print(name, "console:", "\n".join(logs) or "aucune erreur")
        if logs:
            logs_all.extend([name + ": " + x for x in logs])
            # warnings seules ne cassent pas forcément
            ok &= not any(x.startswith("pageerror") or x.startswith("error") for x in logs)
        ctx.close()
    browser.close()
print("OK" if ok else "PROBLÈME")
if logs_all:
    print("\n".join(logs_all))
sys.exit(0 if ok else 1)
