"""Étape 2 : onglet Obligations par pays — ordre, drapeaux, repliées par défaut, AV/S, graphiques de taux rendus, PEA, scroll, console ; captures."""
from playwright.sync_api import sync_playwright
import sys
U=(sys.argv[1] if len(sys.argv)>1 else 'file:///workspace/invest/patrimoine-dashboard/index.html');O='/workspace/invest/patrimoine-dashboard/shots';TAG=sys.argv[2] if len(sys.argv)>2 else ''
errs=[];fails=[];CC=['us','fr','de','it','jp','kr','au','eu']
with sync_playwright() as p:
  b=p.chromium.launch(executable_path='/usr/bin/google-chrome',args=['--no-sandbox'])
  for w in (1920,390):
    pg=b.new_page(viewport={'width':w,'height':900});pg.on('pageerror',lambda e:errs.append(str(e)));pg.on('console',lambda m:m.type=='error' and errs.append(m.text))
    pg.goto(U+'#obligations');pg.evaluate("localStorage.clear()");pg.reload();pg.wait_for_timeout(2500)
    t=pg.evaluate("[...document.querySelectorAll('#pobligations>.card')].map(c=>((c.querySelector('h2')||{}).innerText||'').replace('▸','').trim())")
    want=['OBLIGATIONS USA','OBLIGATIONS FRANCE','OBLIGATIONS ALLEMAGNE','OBLIGATIONS ITALIE','OBLIGATIONS JAPON','OBLIGATIONS CORÉE DU SUD','OBLIGATIONS AUSTRALIE','OBLIGATIONS ZONE EURO','CHIFFRES']
    idx=[next((i for i,x in enumerate(t) if x.upper().startswith(k)),-1) for k in want]
    if -1 in idx or idx!=sorted(idx): fails.append(f'{w} ordre {t}')
    print(w,'ordre',[x[:40] for x in t])
    if pg.evaluate("[...document.querySelectorAll('.ob-card')].filter(c=>c.classList.contains('acc-open')).length"): fails.append(f'{w} carte ouverte par défaut')
    if pg.evaluate("document.documentElement.scrollWidth")>w: fails.append(f'{w} scroll replié')
    pg.screenshot(path=f'{O}/oblig_replie_{w}{TAG}.png',full_page=True)
    for cc in CC:
      el=pg.query_selector(f'.ob-card[data-cc={cc}]')
      if not el: fails.append(f'{w} carte {cc} absente'); continue
      pg.evaluate(f"document.querySelector('.ob-card[data-cc={cc}] .acc-head').click()");pg.wait_for_timeout(900)
      r=pg.evaluate(f"""(()=>{{const c=document.querySelector('.ob-card[data-cc={cc}]');const rows=[...c.querySelectorAll('.sec')];
        const bad=rows.filter(s=>{{const a=s.querySelector('.db-cur.db-a'),q=s.querySelector('.db-cur.db-s');return !a||!q||a.textContent.trim()!=='AV'||q.textContent.trim()!=='S'}}).length;
        const cv=[...c.querySelectorAll('.ob-rates canvas')].map(x=>{{const g=Chart.getChart(x);return [x.id,x.clientWidth,g?g.data.datasets.reduce((n,d)=>n+d.data.filter(v=>v!=null).length,0):0]}});
        return {{rows:rows.length,bad,cv,flag:!!c.querySelector('h2 img'),pea:c.innerText.includes('pas éligibles au PEA'),mention:c.innerText.includes('Indicateur composite APEX, purement informatif'),sum:c.querySelector('.acc-sum').innerText.slice(0,120)}}}})()""")
      print(w,cc,r)
      if r['bad'] or not r['rows']: fails.append(f'{w} {cc} lettres/lignes')
      if cc!='eu' and (not r['flag'] or not r['cv'] or any(x[1]<100 or x[2]<2 for x in r['cv'])): fails.append(f'{w} {cc} graphiques/drapeau {r["cv"]}')
      if not r['pea'] or not r['mention']: fails.append(f'{w} {cc} mentions')
      if pg.evaluate("document.documentElement.scrollWidth")>w: fails.append(f'{w} {cc} scroll ouvert')
      el.screenshot(path=f'{O}/oblig_{cc}_ouvert_{w}{TAG}.png')
      pg.evaluate(f"document.querySelector('.ob-card[data-cc={cc}] .acc-head').click()");pg.wait_for_timeout(300)
    pg.close()
  b.close()
print('erreurs console',errs[:5]);print('ÉCHECS' if fails or errs else 'OK',fails)
