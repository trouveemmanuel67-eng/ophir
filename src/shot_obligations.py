"""Vérifie l'onglet OBLIGATIONS (1920 / 1366 / 390 px) : ordre des onglets, accordéons, graphiques, segments, listes UCITS, copier, débordement, console."""
import os as _os
_APEX_ROOT = _os.path.abspath(_os.environ.get('APEX_ROOT') or _os.path.join(_os.path.dirname(__file__), '..'))
import sys, re
from playwright.sync_api import sync_playwright
B=_APEX_ROOT + '/'
URL=sys.argv[1] if len(sys.argv)>1 else 'file://'+B+'index.html'
OUT=sys.argv[2] if len(sys.argv)>2 else B
ok=True
def chk(c,msg):
    global ok
    print(('  ✔ ' if c else '  ✘ ')+msg); ok&=bool(c)
pat=re.compile(r'^(XETR|EURONEXT):[A-Z0-9]+$'); patref=re.compile(r'^(XETR|EURONEXT|KRX|NASDAQ|NYSE|AMEX|CBOE):[A-Z0-9]+$')
with sync_playwright() as p:
    b=p.chromium.launch(executable_path='/usr/bin/google-chrome',args=['--no-sandbox'])
    for w,h,mob in [(1920,1080,False),(1366,768,False),(390,844,True)]:
        print('==',w)
        ctx=b.new_context(viewport={'width':w,'height':h},is_mobile=mob,has_touch=mob,permissions=['clipboard-read','clipboard-write']);pg=ctx.new_page();logs=[]
        pg.on('console',lambda m: logs.append(m.type+': '+m.text) if m.type in('error','warning') else None);pg.on('pageerror',lambda e:logs.append(str(e)))
        pg.goto(URL+'#obligations',wait_until='networkidle');pg.evaluate('localStorage.clear()');pg.reload(wait_until='networkidle');pg.wait_for_timeout(1200)
        sfx={1920:'',1366:'-1366',390:'-mobile'}[w]
        tabs=pg.evaluate("[...document.querySelectorAll('#nav a')].map(a=>a.textContent.trim())")
        chk(tabs==['Actions','Obligations','Métaux précieux','Crypto','Liquidités','Immobilier'],f'ordre des onglets {tabs}')
        chk(pg.evaluate("document.title")=='APEX INDICATOR INVESTMENT' and not pg.evaluate("!!document.querySelector('footer')"),'titre APEX INDICATOR INVESTMENT, pas de pied de page')
        st=pg.evaluate("""()=>{const s=document.querySelector('#pobligations');return {grp:!!s.querySelector(':scope>.acc-group'),grpOpen:s.querySelector(':scope>.acc-group').classList.contains('open'),
          seg:!!s.querySelector(':scope>.no-group'),segOpen:s.querySelector(':scope>.no-group').classList.contains('open'),subs:s.querySelectorAll('.acc-group .card.acc').length,
          ind:document.querySelector('#duo .card').classList.contains('acc'),av:!!document.querySelector('#duo .db-cur.db-a'),btn:!!document.querySelector('#accAll'),
          mention:document.querySelector('#duo').textContent.includes("Indicateur composite APEX, purement informatif. Ne constitue pas un conseil ni un signal d'ordre.")}}""")
        chk(st['grp'] and not st['grpOpen'] and st['seg'] and not st['segOpen'],'bloc CHIFFRES ET CHARTES GRAPHIQUES et carte Segments repliés par défaut')
        chk(st['subs']==7,f"{st['subs']} cartes dans le bloc parent (7 attendues)")
        chk(st['ind'] and st['av'] and st['btn'] and st['mention'],'colonnes INDICATEUR / ACHAT-VENTE en accordéon, bouton Tout déplier, mention présente')
        iv=pg.evaluate("document.querySelector('#duo .ind-val')?.textContent.trim()"); avv=pg.evaluate("document.querySelector('#duo .av-val')?.textContent.trim()")
        print('  sentiment affiché',iv,'| achat/vente affiché',avv)
        pg.screenshot(path=f'{OUT}apercu-obligations-replie{sfx}.png',full_page=True)
        # tout déplier
        pg.click('#accAll');pg.wait_for_timeout(900)
        charts=pg.evaluate("""()=>['cObY','cObSp','cObC','cObR','cObCr','cObM','cObP'].map(id=>{const c=Chart.getChart(document.getElementById(id));return [id,c?c.data.datasets.reduce((a,d)=>a+d.data.filter(v=>v!=null).length,0):0,document.getElementById(id).clientHeight]})""")
        chk(all(n>10 and hh>50 for _,n,hh in charts),f'7 graphiques non vides {[(i,n) for i,n,_ in charts]}')
        nonrecup=pg.evaluate("[...document.querySelectorAll('#pobligations')].map(s=>s.textContent.includes('non récupéré'))[0]")
        chk(nonrecup,'mention « non récupéré » présente pour les données manquantes')
        pg.screenshot(path=f'{OUT}apercu-obligations-deplie{sfx}.png',full_page=True)
        # segments : ouvrir listes et détails
        pg.evaluate("document.querySelectorAll('#pobligations .sec-list,#pobligations .ob-det').forEach(d=>d.open=true)");pg.wait_for_timeout(1200)
        seg=pg.evaluate("""()=>[...document.querySelectorAll('#pobligations .sec')].map(s=>({nom:s.querySelector('.sec-h b').textContent,ref:s.querySelector('.fl-etf code')?.textContent,
          tv:[...s.querySelectorAll('.fl li code')].map(c=>c.textContent),note:!!s.querySelector('.sec-list .note'),
          mention:s.querySelector('.sec-list .av-short').textContent.includes("Sélection quantitative APEX, purement informative. Ne constitue pas un conseil ni une recommandation d'achat."),
          risk:s.querySelector('.sec-list').textContent.includes('Risques'),closed:s.textContent.includes('bougie clôturée'),
          ch:[...s.querySelectorAll('canvas')].map(c=>{const g=Chart.getChart(c);return g?g.data.datasets[0].data.length:0}),
          over:[...s.querySelectorAll('li,.fl-etf,.sec-h')].filter(e=>e.scrollWidth>e.clientWidth+1).length}))""")
        chk(len(seg)==14,f'{len(seg)} segments (14 attendus : 9 + 5 pays)')
        for x in seg:
            good=bool(x['ref'] and patref.match(x['ref'])) and all(pat.match(t) for t in x['tv']) and (len(x['tv'])==5 or x['note']) and x['mention'] and x['risk'] and x['closed'] and len(x['ch'])==2 and all(n>=40 for n in x['ch']) and x['over']==0
            chk(good,f"{x['nom']}: réf {x['ref']} + {len(x['tv'])} UCITS {x['tv']} · graphiques {x['ch']} · débordements {x['over']}")
        ow=pg.evaluate("document.documentElement.scrollWidth>innerWidth+1");chk(not ow,'pas de scroll horizontal (tout déplié)')
        pg.evaluate("document.querySelectorAll('#pobligations .sec')[4].scrollIntoView()");pg.wait_for_timeout(300)
        pg.screenshot(path=f'{OUT}apercu-obligations-segment{sfx}.png')
        pg.screenshot(path=f'{OUT}apercu-obligations-segments{sfx}.png',full_page=True)
        btn=pg.locator('#pobligations .sec-list .fl .cp').nth(2); btn.scroll_into_view_if_needed(); exp=btn.get_attribute('data-c'); btn.click(); pg.wait_for_timeout(250)
        got=pg.evaluate("navigator.clipboard.readText()"); chk(got==exp,f'copier {exp} → presse-papiers {got}')
        # retour onglet Actions puis Obligations : état persistant
        pg.goto(URL+'#actions');pg.wait_for_timeout(500);pg.goto(URL+'#obligations');pg.wait_for_timeout(500)
        chk(not logs,f'console : {logs or "aucune erreur"}'); ctx.close()
    b.close()
print('OK' if ok else 'PROBLÈME')
