"""Onglet Actions · SECTEURS PAR PAYS (France, Allemagne, Italie, Japon, Corée du Sud, Australie).
A) univers : plus grandes capitalisations cotées sur la place principale (screener Yahoo Finance)
B) fiche Yahoo (secteur, industrie, pays, ratios) de chaque titre
C) consensus (BPA, CA) + cours hebdomadaires des candidats retenus
D) clôtures hebdomadaires des instruments sectoriels, ETF pays et indices de référence
E) vérification des symboles TradingView.  -> data/pays/"""
import json, os, sys, time, math, urllib.request, urllib.parse, datetime as D
from concurrent.futures import ThreadPoolExecutor
import yfinance as yf
from yfinance import EquityQuery as Q
B='/workspace/invest/patrimoine-dashboard/data/pays/'
UA={'User-Agent':'Mozilla/5.0'}
CFG=json.load(open('/workspace/invest/patrimoine-dashboard/src/pays_config.json'))
def get(url,h=None): return urllib.request.urlopen(urllib.request.Request(url,headers={**UA,**(h or {})}),timeout=40).read()
def clean(x):
    if hasattr(x,'item'): x=x.item()
    if isinstance(x,float) and (math.isnan(x) or math.isinf(x)): return None
    return x
def df2(df):
    if df is None or getattr(df,'empty',True): return None
    return {str(i):{str(c):clean(v) for c,v in r.items()} for i,r in df.iterrows()}
def tvsearch(text,country=None):
    try:
        j=json.loads(get('https://symbol-search.tradingview.com/symbol_search/v3/?'+urllib.parse.urlencode({'text':text,'hl':0,'exchange':'','lang':'en','search_type':'undefined','domain':'production'}),
                         {'Origin':'https://www.tradingview.com','Referer':'https://www.tradingview.com/'}))
        return [{k:s.get(k) for k in ('symbol','exchange','description','type','country','isin','typespecs','currency_code')} for s in j.get('symbols',[]) if not country or s.get('country')==country][:10]
    except Exception as e: return {'error':str(e)}
step=sys.argv[1] if len(sys.argv)>1 else 'all'
now=lambda:D.datetime.now().strftime('%Y-%m-%d %H:%M')
if step in('all','A'):
    U={}
    for cc,c in CFG['countries'].items():
        qs=[]
        for pg in range(c.get('pages',1)):
            r=yf.screen(Q('and',[Q('eq',['region',c['region']]),Q('eq',['exchange',c['exchange']]),Q('gt',['intradaymarketcap',c['mincap']])]),offset=pg*250,sortField='intradaymarketcap',sortAsc=False,size=250)
            qs+=[x for x in r['quotes'] if x.get('quoteType')=='EQUITY' and x['symbol'].endswith(c['suffix'])]
        U[cc]=[{'symbol':x['symbol'],'name':x.get('longName') or x.get('shortName'),'cap':x.get('marketCap'),'currency':x.get('currency')} for x in qs]
        print(cc,len(U[cc]),flush=True)
    json.dump({'retrieved':now(),'u':U},open(B+'universe.json','w'),ensure_ascii=False)
if step in('all','B'):
    U=json.load(open(B+'universe.json'))['u']
    def info(s):
        p=B+f'info/{s}.json'
        if os.path.exists(p) and os.path.getsize(p)>200: return
        for a in range(3):
            try:
                i={k:clean(v) for k,v in yf.Ticker(s).info.items() if not isinstance(v,(list,dict))}
                json.dump({'symbol':s,'retrieved':now(),'info':i},open(p,'w'),ensure_ascii=False); return
            except Exception as e: time.sleep(4*(a+1))
        json.dump({'symbol':s,'retrieved':now(),'error':'fiche non récupérée'},open(p,'w'))
    al=[x['symbol'] for v in U.values() for x in v]
    with ThreadPoolExecutor(6) as ex: list(ex.map(info,al))
    print('B ok',len(al),flush=True)
if step in('all','C'):
    sel=json.load(open(B+'candidates.json'))
    def full(s):
        p=B+f'fond/{s}.json'
        if os.path.exists(p) and os.path.getsize(p)>500: return
        out={'symbol':s,'retrieved':now()}
        for a in range(3):
            try:
                T=yf.Ticker(s)
                for n in ('earnings_estimate','revenue_estimate'):
                    try: out[n]=df2(getattr(T,n))
                    except Exception: out[n]=None
                hh=T.history(period='max',interval='1wk',auto_adjust=False)
                out['weekly']=[[str(i)[:19],clean(r['Close'])] for i,r in hh.iterrows() if clean(r['Close']) is not None]
                break
            except Exception as e: out['error']=str(e); time.sleep(5*(a+1))
        json.dump(out,open(p,'w'),ensure_ascii=False)
    with ThreadPoolExecutor(5) as ex: list(ex.map(full,sel))
    print('C ok',len(sel),flush=True)
if step in('all','D'):
    P2=int(time.time())
    syms=sorted({x for c in CFG['countries'].values() for x in [c['bench'],c['etf']]+[r['sym'] for r in c['rows'] if r.get('sym')]})
    for s in syms:
        p=B+f"yahoo_1wk_{urllib.parse.quote(s)}.json"
        try: open(p,'wb').write(get(f'https://query2.finance.yahoo.com/v8/finance/chart/{urllib.parse.quote(s)}?period1=946684800&period2={P2}&interval=1wk&events=history'))
        except Exception as e: print('D ERR',s,e)
        time.sleep(.5)
    print('D ok',len(syms),flush=True)
if step in('all','E'):
    sel=json.load(open(B+'candidates.json'))+[x for c in CFG['countries'].values() for x in [c['etf']]+[r['sym'] for r in c['rows'] if r.get('sym')]]
    for s in sel:
        p=B+f'tv/{s}.json'
        if os.path.exists(p): continue
        q=CFG['tvq'].get(s) or s.split('.')[0].lstrip('^')
        json.dump(tvsearch(q),open(p,'w'),ensure_ascii=False); time.sleep(.35)
    print('E ok',len(sel),flush=True)
