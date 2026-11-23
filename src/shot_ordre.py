import sys,asyncio
from playwright.async_api import async_playwright
U=sys.argv[1];O=sys.argv[2]
async def main():
  async with async_playwright() as p:
    b=await p.chromium.launch(channel='chrome');errs=[];ok=True
    for w,h in [(1920,1080),(390,844)]:
      pg=await b.new_page(viewport={'width':w,'height':h});pg.on('console',lambda m:m.type=='error' and errs.append(m.text));pg.on('pageerror',lambda e:errs.append(str(e)))
      for tab in ['actions','obligations']:
        await pg.goto(U+'#'+tab);await pg.evaluate("localStorage.clear()");await pg.reload();await pg.wait_for_timeout(1800)
        r=await pg.evaluate("""t=>{const y=e=>e?e.getBoundingClientRect().top+scrollY:null;const P=document.getElementById('p'+t);
          const sec=P.querySelector(':scope>.no-group');const grp=P.querySelector(':scope>.acc-group');const duo=document.querySelector('#duo .duo-card');
          const cols=[...document.querySelectorAll('#duo .db-cur.db-s,.sec-grid .db-cur.db-s')].map(c=>getComputedStyle(c).backgroundColor);
          return {duo:y(duo),sec:y(sec),grp:y(grp),sw:document.documentElement.scrollWidth,secT:sec&&sec.querySelector('h2').textContent.trim(),ncur:cols.length,cols:cols.slice(0,3)}}""",tab)
        good=r['duo']<r['sec']<r['grp'] and r['sw']<=w
        ok&=good;print(('✔' if good else '✘'),w,tab,r)
        if tab=='actions':
          await pg.screenshot(path=f"{O}/actions_base_{w}.png",full_page=True)
          if w==1920:
            el=await pg.query_selector('#pactions>.no-group');await el.screenshot(path=f"{O}/actions_lignes_secteurs_{w}.png")
          else:
            await pg.screenshot(path=f"{O}/actions_base_{w}_ecran.png")
      await pg.close()
    print('console:',errs or 'aucune erreur');print('OK' if ok and not errs else 'PROBLÈME');await b.close()
asyncio.run(main())
