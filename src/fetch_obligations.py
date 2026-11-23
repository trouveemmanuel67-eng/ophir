"""Onglet OBLIGATIONS : données brutes -> data/obligations/
FRED (taux, courbe, TIPS, breakeven, spreads ICE BofA, Fed), BCE (taux 10 ans FR/DE, taux de dépôt), Yahoo (ETF obligataires hebdo, ^MOVE),
recherche TradingView (ETF UCITS cotés sur Xetra / Euronext) + fiches Yahoo des candidats."""
import json, os, time, math, urllib.request, urllib.parse, datetime as D
import yfinance as yf
B='/workspace/invest/patrimoine-dashboard/data/obligations/'
UA={'User-Agent':'Mozilla/5.0'}
def get(url,h=None,t=90):
    """curl (plus fiable que urllib avec FRED), 4 essais"""
    import subprocess
    args=['curl','-sfL','-m',str(t)]+([] if 'stlouisfed' in url else ['-A','Mozilla/5.0'])+sum([['-H',f'{k}: {v}'] for k,v in (h or {}).items()],[])+[url]
    for k in range(4):
        r=subprocess.run(args,capture_output=True)
        if r.returncode==0 and r.stdout: return r.stdout
        time.sleep(5*(k+1))
    raise RuntimeError('échec '+url)
def clean(x):
    if hasattr(x,'item'): x=x.item()
    if isinstance(x,float) and (math.isnan(x) or math.isinf(x)): return None
    return x
FRED=['DGS10','DGS2','DGS3MO','DGS30','T10Y2Y','T10Y3M','DFII10','T10YIE','BAMLC0A0CM','BAMLH0A0HYM2','BAMLHE00EHYIOAS','BAMLEMCBPIOAS','DFEDTARU','DFF']
for s in FRED:
    open(B+f'fred_{s}.csv','wb').write(get(f'https://fred.stlouisfed.org/graph/fredgraph.csv?id={s}')); time.sleep(.5)
for c in ['FR','DE']:
    open(B+f'ecb_IRS_{c}.csv','wb').write(get(f'https://data-api.ecb.europa.eu/service/data/IRS/M.{c}.L.L40.CI.0000.EUR.N.Z?format=csvdata'))
open(B+'ecb_DFR.csv','wb').write(get('https://data-api.ecb.europa.eu/service/data/FM/D.U2.EUR.4F.KR.DFR.LEV?format=csvdata&startPeriod=1999-01-01'))
def weekly(sym):
    h=yf.Ticker(sym).history(period='max',interval='1wk',auto_adjust=False)
    return [[str(i)[:19],clean(r['Close'])] for i,r in h.iterrows() if clean(r['Close']) is not None]
REF=['TLT','IEF','SHY','AGG','LQD','HYG','TIP','EMB','^MOVE','EUNH.DE','IFRB.AS','EUN5.DE']
for s in REF:
    json.dump({'symbol':s,'retrieved':D.datetime.now().strftime('%Y-%m-%d %H:%M'),'weekly':weekly(s),'name':(yf.Ticker(s).info or {}).get('longName')},open(B+f'w_{s.replace("^","_")}.json','w')); time.sleep(1)
def tv(q,ex=''):
    u='https://symbol-search.tradingview.com/symbol_search/v3/?text='+urllib.parse.quote(q)+'&hl=0&exchange='+ex+'&lang=en&search_type=undefined&domain=production'
    try: return json.loads(get(u,{'Origin':'https://www.tradingview.com','Referer':'https://www.tradingview.com/'},30)).get('symbols',[])
    except Exception as e: return []
SEG=json.load(open('/workspace/invest/patrimoine-dashboard/src/obligations_segments.json'))
tvres={}
for k,s in SEG.items():
    found=[]
    for q in s['queries']:
        for ex in ('XETR','EURONEXT'):
            found+=tv(q,ex); time.sleep(.35)
    for p in s['principal_tv_query']:
        found+=tv(p[0],p[1]); time.sleep(.35)
    tvres[k]=found
json.dump(tvres,open(B+'tv_search.json','w'))
# fiches Yahoo des candidats (filtrage par mots-clés fait ici pour limiter les requêtes)
def ok(s,desc):
    d=desc.lower()
    return all(any(w in d for w in grp) for grp in s['must']) and not any(w in d for w in s['exclude'])
SUF={'XETR':'.DE','FR':'.PA','NL':'.AS'}
cands={}
for k,s in SEG.items():
    seen={}
    for x in tvres[k]:
        if x.get('type')!='fund' or '-' in x['symbol'] or not x.get('isin'): continue
        if not ok(s,x['description']): continue
        venue=x['exchange'] if x['exchange']=='XETR' else x.get('country')
        if venue not in SUF: continue
        ys=x['symbol']+SUF[venue]; key=(x['isin'])
        seen.setdefault(key,[]).append({'tv':f"{x.get('prefix') or x['exchange']}:{x['symbol']}",'yahoo':ys,'desc':x['description'],'isin':x['isin'],'venue':x['exchange'],'ccy':x.get('currency_code')})
    cands[k]=seen
json.dump(cands,open(B+'candidats.json','w'),ensure_ascii=False)
done=set()
for k,seen in cands.items():
    for isin,lst in seen.items():
        for c in lst:
            if c['yahoo'] in done: continue
            done.add(c['yahoo']); f=B+'etf/'+c['yahoo']+'.json'
            if os.environ.get('OBL_KEEP') and os.path.exists(f) and time.time()-os.path.getmtime(f)<86400: continue
            try:
                T=yf.Ticker(c['yahoo']); i=T.info or {}
                out={'yahoo':c['yahoo'],'retrieved':D.datetime.now().strftime('%Y-%m-%d %H:%M'),'info':{a:clean(b) for a,b in i.items() if not isinstance(b,(list,dict))}}
                try:
                    fd=T.funds_data; br=fd.bond_ratings; out['ratings']={a:clean(b) for a,b in (br or {}).items()}
                except Exception: out['ratings']=None
            except Exception as e: out={'yahoo':c['yahoo'],'error':str(e)}
            json.dump(out,open(f,'w')); print(k,c['tv'],c['yahoo'],(out.get('info') or {}).get('quoteType'),(out.get('info') or {}).get('netExpenseRatio'),(out.get('info') or {}).get('averageVolume'),flush=True); time.sleep(.5)
print('fini')
