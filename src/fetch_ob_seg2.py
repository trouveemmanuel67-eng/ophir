"""Étape 2 · obligations par pays : ETF de référence (IS0L, IS0M, XJSE, 148070, XCS2), recherche TradingView des ETF UCITS
et fiches Yahoo des candidats, sans relancer tout fetch_obligations.py. Fusionne dans data/obligations/{tv_search,candidats}.json."""
import os as _os
_APEX_ROOT = _os.path.abspath(_os.environ.get('APEX_ROOT') or _os.path.join(_os.path.dirname(__file__), '..'))
import json, os, time, datetime as D, sys
sys.argv=[sys.argv[0]]
import importlib.util
import yfinance as yf
B=_APEX_ROOT + '/data/obligations/'
exec(open(_APEX_ROOT + '/src/fetch_obligations.py').read().split("FRED=[")[0])   # get(), clean()
def weekly(sym):
    h=yf.Ticker(sym).history(period='max',interval='1wk',auto_adjust=False)
    return [[str(i)[:19],clean(r['Close'])] for i,r in h.iterrows() if clean(r['Close']) is not None]
SEG=json.load(open(_APEX_ROOT + '/src/obligations_segments.json'))
NEW=['de','it','jp','kr','au']
for k in NEW:
    s=SEG[k]['principal']['yahoo']
    nm=None
    try: nm=(yf.Ticker(s).info or {}).get('longName')
    except Exception as e: print('info',s,e)
    json.dump({'symbol':s,'retrieved':D.datetime.now().strftime('%Y-%m-%d %H:%M'),'weekly':weekly(s),'name':nm},open(B+f'w_{s}.json','w')); print('w',s,nm,flush=True); time.sleep(2)
try: open(B+'ecb_IRS_IT.csv','wb').write(get('https://data-api.ecb.europa.eu/service/data/IRS/M.IT.L.L40.CI.0000.EUR.N.Z?format=csvdata')); print('ecb IT ok')
except Exception as e: print('ecb IT',e)
def tv(q,ex=''):
    u='https://symbol-search.tradingview.com/symbol_search/v3/?text='+urllib.parse.quote(q)+'&hl=0&exchange='+ex+'&lang=en&search_type=undefined&domain=production'
    try: return json.loads(get(u,{'Origin':'https://www.tradingview.com','Referer':'https://www.tradingview.com/'},30)).get('symbols',[])
    except Exception: return []
tvres=json.load(open(B+'tv_search.json')); cands=json.load(open(B+'candidats.json'))
def ok(s,desc):
    d=desc.lower(); return all(any(w in d for w in grp) for grp in s['must']) and not any(w in d for w in s['exclude'])
SUF={'XETR':'.DE','FR':'.PA','NL':'.AS','IT':'.MI'}
for k in NEW:
    s=SEG[k]; found=[]
    for q in s['queries']:
        for ex in ('XETR','EURONEXT'): found+=tv(q,ex); time.sleep(.4)
    for p in s['principal_tv_query']: found+=tv(p[0],p[1]); time.sleep(.4)
    tvres[k]=found; seen={}
    for x in found:
        if x.get('type')!='fund' or '-' in x['symbol'] or not x.get('isin'): continue
        if not ok(s,x['description']): continue
        venue=x['exchange'] if x['exchange']=='XETR' else x.get('country')
        if venue not in SUF: continue
        ys=x['symbol']+SUF[venue]
        L=seen.setdefault(x['isin'],[])
        if not any(c['yahoo']==ys for c in L): L.append({'tv':f"{x.get('prefix') or x['exchange']}:{x['symbol']}",'yahoo':ys,'desc':x['description'],'isin':x['isin'],'venue':x['exchange'],'ccy':x.get('currency_code')})
    cands[k]=seen; print(k,'candidats',len(seen),flush=True)
json.dump(tvres,open(B+'tv_search.json','w')); json.dump(cands,open(B+'candidats.json','w'),ensure_ascii=False)
for k in NEW:
    for isin,lst in cands[k].items():
        for c in lst:
            f=B+'etf/'+c['yahoo']+'.json'
            if os.path.exists(f) and 'error' not in json.load(open(f)): continue
            for t in range(3):
                try:
                    T=yf.Ticker(c['yahoo']); i=T.info or {}
                    out={'yahoo':c['yahoo'],'retrieved':D.datetime.now().strftime('%Y-%m-%d %H:%M'),'info':{a:clean(b) for a,b in i.items() if not isinstance(b,(list,dict))}}
                    try: out['ratings']={a:clean(b) for a,b in (T.funds_data.bond_ratings or {}).items()}
                    except Exception: out['ratings']=None
                    break
                except Exception as e: out={'yahoo':c['yahoo'],'error':str(e)}; time.sleep(20)
            json.dump(out,open(f,'w')); print(k,c['tv'],c['yahoo'],(out.get('info') or {}).get('quoteType'),(out.get('info') or {}).get('netExpenseRatio'),out.get('error','')[:60],flush=True); time.sleep(2.5)
print('fini')
