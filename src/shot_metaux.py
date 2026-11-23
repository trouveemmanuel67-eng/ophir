"""Étape 3 : onglet Métaux précieux — ordre des onglets et des blocs, carte fusionnée, lignes AV/S (4 métaux), listes, graphiques, scroll, console ; captures."""
import os as _os
_APEX_ROOT = _os.path.abspath(_os.environ.get('APEX_ROOT') or _os.path.join(_os.path.dirname(__file__), '..'))
from playwright.sync_api import sync_playwright
import sys
U=(sys.argv[1] if len(sys.argv)>1 else 'file://' + _APEX_ROOT + '/index.html');O=_APEX_ROOT + '/shots';TAG=sys.argv[2] if len(sys.argv)>2 else ''
errs=[];fails=[]
with sync_playwright() as p:
  b=p.chromium.launch(executable_path='/usr/bin/google-chrome',args=['--no-sandbox'])
  for w in (1920,390):
    pg=b.new_page(viewport={'width':w,'height':900});pg.on('pageerror',lambda e:errs.append(str(e)));pg.on('console',lambda m:m.type=='error' and errs.append(m.text))
    pg.goto(U+'#metaux');pg.evaluate("localStorage.clear()");pg.reload();pg.wait_for_timeout(2500)
    tabs=pg.evaluate("[...document.querySelectorAll('#nav > *')].map(x=>x.innerText.trim()).filter(Boolean)")
    if tabs[:6]!=['Actions','Obligations','Métaux précieux','Crypto','Liquidités','Immobilier']: fails.append(f'{w} onglets {tabs}')
    st=pg.evaluate("""(()=>{const P=document.getElementById('pmetaux');const top=e=>e?Math.round(e.getBoundingClientRect().top+scrollY):-1;
      const duo=document.querySelector('#duo .duo-card'),met=P.querySelector('.met-card'),grp=P.querySelector('.acc-group');
      return {duo:top(duo),met:top(met),grp:top(grp),grpT:grp?grp.querySelector('h2').innerText:'',duoTxt:duo?duo.innerText.slice(0,80):'',open:[...P.querySelectorAll('.card.acc')].filter(c=>c.classList.contains('acc-open')).length,sw:document.documentElement.scrollWidth}})()""")
    print(w,tabs,st)
    if not(0<=st['duo']<st['met']<st['grp']): fails.append(f'{w} ordre des blocs {st}')
    if st['open']: fails.append(f'{w} cartes ouvertes par défaut')
    if st['sw']>w: fails.append(f'{w} scroll replié')
    pg.screenshot(path=f'{O}/metaux_replie_{w}{TAG}.png',full_page=True)
    pg.evaluate("document.querySelector('#pmetaux .met-card .acc-head').click()");pg.wait_for_timeout(700)
    pg.evaluate("document.querySelectorAll('#pmetaux .met-card details').forEach(d=>d.open=true)");pg.wait_for_timeout(1500)
    r=pg.evaluate("""(()=>{const c=document.querySelector('#pmetaux .met-card');const rows=[...c.querySelectorAll('.sec')];
      return {n:rows.length,letters:rows.every(s=>s.querySelector('.db-cur.db-a')?.textContent.trim()==='AV'&&s.querySelector('.db-cur.db-s')?.textContent.trim()==='S'),
       lists:rows.map(s=>[s.querySelector('.fl-etf code')?.textContent,[...s.querySelectorAll('.fl li code')].map(x=>x.textContent)]),
       ch:[...c.querySelectorAll('canvas')].map(x=>{const g=Chart.getChart(x);return g?g.data.datasets[0].data.length:0}),
       ment:c.innerText.includes('Indicateur composite APEX, purement informatif'),ment2:c.innerText.includes('Sélection quantitative APEX, purement informative'),
       cfd:/CFD/i.test(document.getElementById('pmetaux').innerText),sw:document.documentElement.scrollWidth}})()""")
    print(w,r)
    if r['n']!=4 or not r['letters'] or not r['ment'] or not r['ment2'] or r['cfd'] or r['sw']>w or len(r['ch'])!=8 or min(r['ch'])<40: fails.append(f'{w} section métaux {r}')
    if any(not l[0] or len(l[1])<3 for l in r['lists']): fails.append(f'{w} listes {r["lists"]}')
    pg.query_selector('#pmetaux .met-card').screenshot(path=f'{O}/metaux_section_ouverte_{w}{TAG}.png')
    pg.evaluate("document.querySelector('#pmetaux .met-card .acc-head').click()");pg.wait_for_timeout(300)
    pg.evaluate("document.querySelector('#pmetaux .acc-group>.acc-head').click()");pg.wait_for_timeout(500)
    pg.evaluate("document.querySelectorAll('#pmetaux .acc-group .card.acc:not(.acc-open)>.acc-head').forEach(h=>h.click())");pg.wait_for_timeout(1500)
    cv=pg.evaluate("[...document.querySelectorAll('#pmetaux .acc-group canvas')].map(x=>{const g=Chart.getChart(x);return [x.id,x.clientWidth,x.clientHeight,g?g.data.datasets[0].data.filter(v=>v!=null).length:0]})")
    print(w,'graphiques',cv)
    if len(cv)<8 or any(x[1]<100 or x[2]<100 or x[3]<100 for x in cv): fails.append(f'{w} graphiques {cv}')
    if pg.evaluate("document.documentElement.scrollWidth")>w: fails.append(f'{w} scroll chiffres')
    pg.query_selector('#pmetaux .acc-group').screenshot(path=f'{O}/metaux_chiffres_{w}{TAG}.png')
    pg.evaluate("document.querySelector('#duo .duo-card .acc-head')?.click()");pg.wait_for_timeout(800)
    pg.query_selector('#duo .duo-card').screenshot(path=f'{O}/metaux_carte_{w}{TAG}.png')
    pg.close()
  b.close()
print('erreurs console',errs[:5]);print('ÉCHECS' if fails or errs else 'OK',fails)
