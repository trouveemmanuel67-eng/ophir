"""Secteurs par pays, collecte économe (Yahoo limite les requêtes) :
S) classement par secteur (ou industries pour le Japon / TOPIX-17) via le screener Yahoo, triés par capitalisation
Q) une requête quoteSummary par candidat (profil, ratios, consensus), lente et reprenable
H) clôtures hebdomadaires via l'API chart
T) symboles TradingView.  -> data/pays/"""
import os as _os
_APEX_ROOT = _os.path.abspath(_os.environ.get('APEX_ROOT') or _os.path.join(_os.path.dirname(__file__), '..'))
import json, os, sys, time, urllib.request, urllib.parse, datetime as D
import yfinance as yf
from yfinance import EquityQuery as Q
B=_APEX_ROOT + '/data/pays/'
CFG=json.load(open(_APEX_ROOT + '/src/pays_config.json'))
UA={'User-Agent':'Mozilla/5.0'}
N=int(os.environ.get('N','12'))
now=lambda:D.datetime.now().strftime('%Y-%m-%d %H:%M')
def get(url,h=None): return urllib.request.urlopen(urllib.request.Request(url,headers={**UA,**(h or {})}),timeout=40).read()
step=sys.argv[1]
for d in ('qs','wk','tv'): os.makedirs(B+d,exist_ok=True)
if step=='S':
    out={}
    for cc,c in CFG['countries'].items():
        out[cc]={}
        for r in c['rows']:
            f=[Q('eq',['region',c['region']]),Q('eq',['exchange',c['exchange']])]
            f.append(Q('is-in',['industry',*r['yind']]) if r.get('yind') else Q('eq',['sector',r['ysec'][0]]))
            res=yf.screen(Q('and',f),sortField='intradaymarketcap',sortAsc=False,size=40 if cc=='de' else 25)
            out[cc][r['key']]=[{'symbol':x['symbol'],'name':x.get('longName') or x.get('shortName'),'cap':x.get('marketCap'),'currency':x.get('currency'),'avgvol':x.get('averageDailyVolume3Month'),'price':x.get('regularMarketPrice')}
                               for x in res['quotes'] if x.get('quoteType')=='EQUITY' and x['symbol'].endswith(c['suffix']) and x.get('marketCap')]
            time.sleep(.4)
        print(cc,{k:len(v) for k,v in out[cc].items()},flush=True)
    json.dump({'retrieved':now(),'s':out},open(B+'screen.json','w'),ensure_ascii=False)
if step=='Q':
    from yfinance.data import YfData
    yd=YfData()
    sel=json.load(open(B+'candidates.json'))[::(-1 if os.environ.get('REV') else 1)]; MOD='assetProfile,price,financialData,defaultKeyStatistics,summaryDetail,earningsTrend'
    for k,s in enumerate(sel):
        p=B+f'qs/{s}.json'
        if os.path.exists(p): continue
        for a in range(6):
            try:
                j=yd.get_raw_json(f'https://query2.finance.yahoo.com/v10/finance/quoteSummary/{s}',params={'modules':MOD,'corsDomain':'finance.yahoo.com','formatted':'false'})
                r=j['quoteSummary']['result'][0]; json.dump({'symbol':s,'retrieved':now(),'qs':r},open(p,'w'),ensure_ascii=False); break
            except Exception as e:
                msg=str(e)
                if '404' in msg or 'Not Found' in msg: json.dump({'symbol':s,'retrieved':now(),'error':msg[:100]},open(p,'w')); break
                time.sleep(20*(a+1))
        print(k+1,len(sel),s,'ok' if os.path.exists(p) else 'ÉCHEC',flush=True); time.sleep(float(os.environ.get('PAUSE','2.5')))
if step=='H':
    sel=json.load(open(B+'candidates_wk.json')); P2=int(time.time())
    for s in sel:
        p=B+f'wk/{s}.json'
        if os.path.exists(p): continue
        try: open(p,'wb').write(get(f'https://query2.finance.yahoo.com/v8/finance/chart/{urllib.parse.quote(s)}?period1=946684800&period2={P2}&interval=1wk&events=history'))
        except Exception as e: print('H ERR',s,e,flush=True)
        time.sleep(.6)
    print('H ok',flush=True)
if step=='T':
    sel=json.load(open(B+'candidates.json'))+[x for c in CFG['countries'].values() for x in [c['etf']]+[r['sym'] for r in c['rows'] if r.get('sym')]]
    for s in sel:
        p=B+f'tv/{s}.json'
        if os.path.exists(p): continue
        q=s.split('.')[0].lstrip('^')
        if s.startswith('^AX'): q=q[2:]+'' if False else 'X'+q[2:4]   # ^AXFJ -> XFJ
        try:
            j=json.loads(get('https://symbol-search.tradingview.com/symbol_search/v3/?'+urllib.parse.urlencode({'text':q,'hl':0,'exchange':'','lang':'en','search_type':'undefined','domain':'production'}),{'Origin':'https://www.tradingview.com','Referer':'https://www.tradingview.com/'}))
            json.dump([{k:x.get(k) for k in ('symbol','exchange','description','type','country','typespecs','currency_code')} for x in j.get('symbols',[])][:15],open(p,'w'),ensure_ascii=False)
        except Exception as e: print('T ERR',s,e,flush=True)
        time.sleep(.35)
    print('T ok',flush=True)
