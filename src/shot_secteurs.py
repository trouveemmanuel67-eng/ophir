import sys
from playwright.sync_api import sync_playwright
URL=sys.argv[1]; OUT=sys.argv[2]; ok=True
with sync_playwright() as p:
    b=p.chromium.launch(executable_path='/usr/bin/google-chrome',args=['--no-sandbox'])
    for w,h,mob in [(1920,1080,False),(390,844,True)]:
        ctx=b.new_context(viewport={'width':w,'height':h},is_mobile=mob,has_touch=mob);pg=ctx.new_page();logs=[]
        pg.on('console',lambda m: logs.append(m.type+': '+m.text) if m.type in('error','warning') else None);pg.on('pageerror',lambda e:logs.append(str(e)))
        pg.goto(URL+'#actions',wait_until='networkidle');pg.evaluate('localStorage.clear()');pg.reload(wait_until='networkidle');pg.wait_for_timeout(1500)
        st=pg.evaluate("""()=>{const s=document.querySelector('#pactions>.card.no-group');const g=document.querySelector('#pactions>.acc-group');
          return {sec:!!s,acc:s.classList.contains('acc'),open:s.classList.contains('acc-open'),body:s.querySelector('.acc-in').getBoundingClientRect().height,
          sum:s.querySelector('.acc-sum').textContent,order:[...document.querySelectorAll('#pactions>*')].map(e=>e.className),grpSum:g.querySelector('.acc-sum').textContent,tiles:s.querySelectorAll('.sec').length,
          ow:document.documentElement.scrollWidth>innerWidth+1}}""")
        print(w,st); ok&=st['sec'] and not st['open'] and st['body']==0 and st['tiles']==11 and not st['ow']
        sfx='' if w==1920 else '-mobile'
        pg.evaluate('scrollTo(0,0)');pg.screenshot(path=f'{OUT}apercu-secteurs-replie{sfx}.png',full_page=True)
        pg.click('#pactions>.card.no-group>.acc-head');pg.wait_for_timeout(800)
        r=pg.evaluate("""()=>{const s=document.querySelector('#pactions>.card.no-group');const t=[...s.querySelectorAll('.sec')].map(e=>{const r=e.getBoundingClientRect();return [Math.round(r.width),Math.round(r.height)]});
          return {open:s.classList.contains('acc-open'),tiles:t.slice(0,3),minW:Math.min(...t.map(x=>x[0])),ow:document.documentElement.scrollWidth>innerWidth+1,
          over:[...s.querySelectorAll('.sec')].filter(e=>e.scrollWidth>e.clientWidth+1).length}}""")
        cc=pg.evaluate("[...document.querySelectorAll('#pactions>.card.no-group:not(.pays-card) .sec')].map((e,i)=>{const g=e.querySelector('.db-g'),c=g.querySelector('.db-cur.db-a').getBoundingClientRect(),b=g.querySelector('.ind-bar').getBoundingClientRect();return Math.abs(((c.left+c.width/2-b.left)/b.width*100)-avPos(SEC.sectors[i].av.score))})")
        print('  curseurs achat/vente : écart max',round(max(cc),2),'%'); ok&=max(cc)<2
        print('  ouvert',r); ok&=r['open'] and not r['ow'] and r['over']==0
        s=pg.query_selector('#pactions>.card.no-group'); s.scroll_into_view_if_needed(); pg.evaluate("document.querySelector('#pactions>.card.no-group').scrollIntoView()"); pg.wait_for_timeout(300)
        pg.screenshot(path=f'{OUT}apercu-secteurs-ouvert{sfx}.png',full_page=(w==390))
        # ouvrir tous les détails
        pg.evaluate("document.querySelectorAll('#pactions>.card.no-group:not(.pays-card) .sec-det').forEach(d=>d.open=true)");pg.wait_for_timeout(800)
        c=pg.evaluate("""()=>[...document.querySelectorAll('#pactions>.card.no-group:not(.pays-card) .sec-det canvas')].map(c=>{const k=Chart.getChart(c);return [c.id,c.clientWidth,c.clientHeight,k?k.data.datasets[0].data.filter(v=>v!=null).length:0]})""")
        bad=[x for x in c if x[1]<50 or x[2]<20 or x[3]<52]; print('  graphiques détail',len(c),'défectueux',bad); ok&=len(c)==22 and not bad
        if w==1920:
            pg.evaluate("document.querySelectorAll('#pactions>.card.no-group:not(.pays-card) .sec-det').forEach((d,i)=>d.open=i==9)");pg.wait_for_timeout(300)
            pg.evaluate("document.querySelectorAll('#pactions>.card.no-group:not(.pays-card) .sec')[9].scrollIntoView()");pg.wait_for_timeout(300)
            pg.screenshot(path=f'{OUT}apercu-secteurs-detail-tech.png')
        # persistance + tout replier/déplier
        pg.reload(wait_until='networkidle');pg.wait_for_timeout(1200)
        pe=pg.evaluate("document.querySelector('#pactions>.card.no-group').classList.contains('acc-open')"); print('  mémorisé après rechargement',pe); ok&=pe
        pg.evaluate("accAll(false)");pg.wait_for_timeout(400);pg.click('#accAll');pg.wait_for_timeout(600)
        a=pg.evaluate("[...document.querySelectorAll('#pactions .card.acc')].every(c=>c.classList.contains('acc-open'))"); print('  tout déplier inclut secteurs',a); ok&=a
        print(w,'console:',logs or 'aucune erreur'); ok&=not logs; ctx.close()
    b.close()
print('OK' if ok else 'PROBLÈME')
