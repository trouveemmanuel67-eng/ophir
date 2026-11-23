"""Étape 1 : sections pays de l'onglet Actions — captures repliée / ouverte par pays, contrôles (ordre, lettres AV/S, couleurs miroir, défilement horizontal, console)."""
import os as _os
_APEX_ROOT = _os.path.abspath(_os.environ.get('APEX_ROOT') or _os.path.join(_os.path.dirname(__file__), '..'))
from playwright.sync_api import sync_playwright
import sys,re
U=(sys.argv[1] if len(sys.argv)>1 else 'file://' + _APEX_ROOT + '/index.html');O=_APEX_ROOT + '/shots';TAG=sys.argv[2] if len(sys.argv)>2 else ''
errs=[];fails=[]
CC=['fr','de','it','jp','kr','au']
with sync_playwright() as p:
  b=p.chromium.launch(executable_path='/usr/bin/google-chrome',args=['--no-sandbox'])
  for w in (1920,390):
    pg=b.new_page(viewport={'width':w,'height':900});pg.on('pageerror',lambda e:errs.append(str(e)));pg.on('console',lambda m:m.type=='error' and errs.append(m.text))
    pg.goto(U+'#actions');pg.evaluate("localStorage.clear()");pg.reload();pg.wait_for_timeout(2500)
    titles=pg.evaluate("[...document.querySelectorAll('#pactions>.card')].map(c=>(c.querySelector('h2')||{}).innerText||'')")
    t=[x.replace('▸','').strip() for x in titles]
    want=['SECTEURS USA','SECTEURS FRANCE','SECTEURS ALLEMAGNE','SECTEURS ITALIE','SECTEURS JAPON','SECTEURS CORÉE DU SUD','SECTEURS AUSTRALIE','CHIFFRES']
    idx=[next((i for i,x in enumerate(t) if x.upper().startswith(k)),-1) for k in want]
    if -1 in idx or idx!=sorted(idx): fails.append(f'{w} ordre {t}')
    opened=pg.evaluate("[...document.querySelectorAll('.pays-card')].filter(c=>c.classList.contains('acc-open')).length")
    if opened: fails.append(f'{w} {opened} cartes pays ouvertes par défaut')
    if pg.evaluate("document.documentElement.scrollWidth")>w: fails.append(f'{w} défilement horizontal replié')
    for cc in CC:
      el=pg.query_selector(f'.pays-card[data-cc={cc}]')
      if not el: fails.append(f'{w} carte {cc} absente'); continue
      if not pg.evaluate(f"!!document.querySelector('.pays-card[data-cc={cc}] h2 img[src=\"flag-{cc}.png\"]')"): fails.append(f'{w} drapeau {cc}')
      el.screenshot(path=f'{O}/pays_{cc}_replie_{w}{TAG}.png')
      pg.evaluate(f"document.querySelector('.pays-card[data-cc={cc}] .acc-head').click()");pg.wait_for_timeout(500)
      pg.evaluate(f"const c=document.querySelector('.pays-card[data-cc={cc}]');const s=[...c.querySelectorAll('.sec:not(.sec-nc):not(.sec-head)')][0];s&&s.querySelectorAll('details').forEach(d=>d.open=true)");pg.wait_for_timeout(1200)
      r=pg.evaluate(f"""(()=>{{const c=document.querySelector('.pays-card[data-cc={cc}]');const rows=[...c.querySelectorAll('.sec')];
        const bad=[];rows.filter(s=>!s.classList.contains('sec-nc')).forEach((s,k)=>{{const a=s.querySelector('.db-cur.db-a'),q=s.querySelector('.db-cur.db-s');if(!a||!q||a.textContent.trim()!=='AV'||q.textContent.trim()!=='S')bad.push(k)}});
        const cv=[...c.querySelectorAll('canvas')].filter(x=>x.offsetParent).length;
        return {{n:rows.length,nc:c.querySelectorAll('.sec-nc').length,bad,cv,mention:c.innerText.includes('Indicateur composite APEX, purement informatif'),list:c.innerText.includes('Sélection quantitative APEX, purement informative')}}}})()""")
      if r['bad']: fails.append(f'{w} {cc} lettres AV/S manquantes {r["bad"]}')
      if not r['mention']: fails.append(f'{w} {cc} mention AV absente')
      if r['cv']<2: fails.append(f'{w} {cc} graphiques détail non rendus ({r["cv"]})')
      print(w,cc,r)
      if pg.evaluate("document.documentElement.scrollWidth")>w: fails.append(f'{w} {cc} défilement horizontal ouvert')
      el.screenshot(path=f'{O}/pays_{cc}_ouvert_{w}{TAG}.png')
      pg.evaluate(f"document.querySelector('.pays-card[data-cc={cc}] .acc-head').click()");pg.wait_for_timeout(300)
    pg.close()
  b.close()
print('erreurs console',errs[:5]);print('ÉCHECS' if fails or errs else 'OK',fails)
