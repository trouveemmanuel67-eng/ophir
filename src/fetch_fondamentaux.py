"""Composants des ETF SPDR sectoriels (fichiers officiels State Street) + données fondamentales,
consensus d'analystes et cours hebdomadaires Yahoo Finance (yfinance) + vérification du symbole TradingView.
-> data/secteurs/holdings/*.xlsx, data/secteurs/fond/<TICKER>.json, data/secteurs/tv_<SYM>.json"""
import json, os, sys, time, math, urllib.request, datetime as D
import openpyxl, yfinance as yf
B='/workspace/invest/patrimoine-dashboard/data/secteurs/'
ETFS=['XLC','XLY','XLP','XLE','XLF','XLV','XLI','XLB','XLRE','XLK','XLU']
TOP=int(os.environ.get('TOP','20'))
UA={'User-Agent':'Mozilla/5.0'}
def get(url,h=None):
    r=urllib.request.Request(url,headers={**UA,**(h or {})});return urllib.request.urlopen(r,timeout=40).read()
def clean(x):
    if hasattr(x,'item'): x=x.item()
    if isinstance(x,float) and (math.isnan(x) or math.isinf(x)): return None
    return x
def df2(df):
    if df is None or getattr(df,'empty',True): return None
    return {str(i):{str(c):clean(v) for c,v in r.items()} for i,r in df.iterrows()}
def tv(sym):
    try:
        j=json.loads(get(f'https://symbol-search.tradingview.com/symbol_search/v3/?text={sym}&hl=0&exchange=&lang=en&search_type=undefined&domain=production',
                         {'Origin':'https://www.tradingview.com','Referer':'https://www.tradingview.com/'}))
        return [{k:s.get(k) for k in ('symbol','exchange','description','type','country','isin','typespecs')} for s in j.get('symbols',[]) if s.get('country')=='US'][:8]
    except Exception as e: return {'error':str(e)}
universe={}
for e in ETFS:
    p=B+f'holdings/{e}.xlsx'
    open(p,'wb').write(get(f'https://www.ssga.com/library-content/products/fund-data/etfs/us/holdings-daily-us-en-{e.lower()}.xlsx'))
    ws=openpyxl.load_workbook(p,read_only=True).active; rows=list(ws.iter_rows(values_only=True))
    asof=rows[2][1]; hdr=[i for i,r in enumerate(rows) if r and r[0]=='Name'][0]
    h=[r for r in rows[hdr+1:] if r and r[1] and isinstance(r[4],(int,float)) and r[1] not in('-','CASH_USD') and str(r[7] or 'USD')=='USD']
    h=sorted(h,key=lambda r:-r[4])[:TOP]
    universe[e]={'asof':asof,'holdings':[{'name':r[0],'ticker':r[1],'weight':r[4],'cusip':r[2]} for r in h]}
    print(e,asof,[r[1] for r in h]); time.sleep(1)
json.dump(universe,open(B+'holdings/universe.json','w'),ensure_ascii=False)
for e in ETFS:
    json.dump(tv(e),open(B+f'tv_{e}.json','w')); time.sleep(.4)
tick=sorted({x['ticker'] for u in universe.values() for x in u['holdings']})
for k,t in enumerate(tick):
    ys=t.replace('.','-').replace('/','-')
    out={'ticker':t,'yahoo':ys,'retrieved':D.datetime.now().strftime('%Y-%m-%d %H:%M')}
    for attempt in range(3):
        try:
            T=yf.Ticker(ys); out['info']={k2:clean(v) for k2,v in T.info.items() if not isinstance(v,(list,dict))}
            for name in ('growth_estimates','earnings_estimate','revenue_estimate'):
                try: out[name]=df2(getattr(T,name))
                except Exception as ex: out[name]=None
            hh=T.history(period='max',interval='1wk',auto_adjust=False)
            out['weekly']=[[str(i)[:19],clean(r['Close'])] for i,r in hh.iterrows() if clean(r['Close']) is not None]
            break
        except Exception as ex:
            out['error']=str(ex); time.sleep(5*(attempt+1))
    out['tv']=tv(t.replace('/','.').replace('-','.'))
    json.dump(out,open(B+f'fond/{t}.json','w'),ensure_ascii=False)
    print(k+1,len(tick),t,out.get('info',{}).get('exchange'),len(out.get('weekly',[])),'tv',[s['exchange'] for s in out['tv'] if isinstance(out['tv'],list) and s.get('symbol')==t.replace('/','.').replace('-','.')][:2] if isinstance(out['tv'],list) else out['tv'],flush=True)
    time.sleep(.6)
print('fini')
