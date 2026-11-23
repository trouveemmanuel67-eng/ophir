"""Collecte ciblée Suisse : fusionne dans data/pays/ sans retélécharger les autres pays."""
import os as _os
_APEX_ROOT = _os.path.abspath(_os.environ.get('APEX_ROOT') or _os.path.join(_os.path.dirname(__file__), '..'))
import json, os, sys, time, math, urllib.request, urllib.parse, datetime as D
from concurrent.futures import ThreadPoolExecutor
import yfinance as yf

R=_APEX_ROOT + '/'
B=R+'data/pays/'
UA={'User-Agent':'Mozilla/5.0'}
CFG=json.load(open(R+'src/pays_config.json'))
SW=json.load(open(R+'src/swiss_xtb.json'))
C=CFG['countries']['ch']
now=lambda:D.datetime.now().strftime('%Y-%m-%d %H:%M')

def get(url,h=None):
    return urllib.request.urlopen(urllib.request.Request(url,headers={**UA,**(h or {})}),timeout=40).read()

def clean(x):
    if hasattr(x,'item'): x=x.item()
    if isinstance(x,float) and (math.isnan(x) or math.isinf(x)): return None
    return x

YSEC={r['ysec'][0]:r['key'] for r in C['rows']}
stocks=SW['stocks']
etf=SW['etf']

os.makedirs(B+'info',exist_ok=True)
os.makedirs(B+'qs',exist_ok=True)
os.makedirs(B+'wk',exist_ok=True)
os.makedirs(B+'tv',exist_ok=True)

# ---- info + sector ----
def info_one(s):
    p=B+f'info/{s}.json'
    if os.path.exists(p) and os.path.getsize(p)>200:
        return json.load(open(p))
    for a in range(3):
        try:
            i={k:clean(v) for k,v in yf.Ticker(s).info.items() if not isinstance(v,(list,dict))}
            out={'symbol':s,'retrieved':now(),'info':i}
            json.dump(out,open(p,'w'),ensure_ascii=False)
            return out
        except Exception as e:
            time.sleep(3*(a+1))
    out={'symbol':s,'retrieved':now(),'error':'fiche non récupérée'}
    json.dump(out,open(p,'w'))
    return out

print('info…',flush=True)
infos={}
with ThreadPoolExecutor(4) as ex:
    for out in ex.map(info_one, [x['yahoo'] for x in stocks]):
        infos[out['symbol']]=out
        sec=(out.get('info') or {}).get('sector')
        print(' ',out['symbol'], (out.get('info') or {}).get('shortName') or out.get('error'), sec, flush=True)

# ---- universe + screen ----
U_path=B+'universe.json'
U=json.load(open(U_path)) if os.path.exists(U_path) else {'retrieved':now(),'u':{}}
U['u']['ch']=[{'symbol':x['yahoo'],'name':(infos.get(x['yahoo'],{}).get('info') or {}).get('longName') or x['nom'],
               'cap':(infos.get(x['yahoo'],{}).get('info') or {}).get('marketCap'),
               'currency':'CHF'} for x in stocks]
U['retrieved']=now()
json.dump(U,open(U_path,'w'),ensure_ascii=False)

screen_path=B+'screen.json'
SCR=json.load(open(screen_path)) if os.path.exists(screen_path) else {'retrieved':now(),'s':{}}
ch={}
for r in C['rows']:
    ch[r['key']]=[]
unmapped=[]
for x in stocks:
    inf=(infos.get(x['yahoo']) or {}).get('info') or {}
    sec=inf.get('sector')
    key=YSEC.get(sec)
    rec={'symbol':x['yahoo'],'name':inf.get('longName') or inf.get('shortName') or x['nom'],
         'cap':inf.get('marketCap'),'currency':inf.get('currency') or 'CHF',
         'avgvol':inf.get('averageDailyVolume3Month'),'price':inf.get('regularMarketPrice')}
    if key:
        ch[key].append(rec)
    else:
        unmapped.append((x['yahoo'],sec,rec['name']))
for k in ch:
    ch[k]=[r for r in ch[k] if r.get('cap')]
    ch[k].sort(key=lambda r:-(r['cap'] or 0))
SCR.setdefault('s',{})['ch']=ch
SCR['retrieved']=now()
json.dump(SCR,open(screen_path,'w'),ensure_ascii=False)
print('screen', {k:len(v) for k,v in ch.items()}, 'unmapped', unmapped, flush=True)

# ---- candidates ----
cand=json.load(open(B+'candidates.json')) if os.path.exists(B+'candidates.json') else []
wk=json.load(open(B+'candidates_wk.json')) if os.path.exists(B+'candidates_wk.json') else []
add=[x['yahoo'] for x in stocks]+[C['etf'],C['bench']]
n0,n1=len(cand),len(wk)
for s in add:
    if s not in cand: cand.append(s)
    if s not in wk: wk.append(s)
# also sector members already in add
json.dump(cand,open(B+'candidates.json','w'),ensure_ascii=False)
json.dump(wk,open(B+'candidates_wk.json','w'),ensure_ascii=False)
print('candidates +',len(cand)-n0,'wk +',len(wk)-n1,flush=True)

# ---- quoteSummary ----
from yfinance.data import YfData
yd=YfData()
MOD='assetProfile,price,financialData,defaultKeyStatistics,summaryDetail,earningsTrend'
print('qs…',flush=True)
for k,s in enumerate(add):
    if s.startswith('^'):  # index: skip qs
        continue
    p=B+f'qs/{s}.json'
    if os.path.exists(p) and os.path.getsize(p)>200: 
        print(k+1,s,'qs skip',flush=True); continue
    ok=False
    for a in range(5):
        try:
            j=yd.get_raw_json(f'https://query2.finance.yahoo.com/v10/finance/quoteSummary/{s}',params={'modules':MOD,'corsDomain':'finance.yahoo.com','formatted':'false'})
            r=j['quoteSummary']['result'][0]
            json.dump({'symbol':s,'retrieved':now(),'qs':r},open(p,'w'),ensure_ascii=False)
            ok=True; break
        except Exception as e:
            msg=str(e)
            if '404' in msg or 'Not Found' in msg:
                json.dump({'symbol':s,'retrieved':now(),'error':msg[:120]},open(p,'w')); break
            time.sleep(8*(a+1))
    print(k+1,s,'qs','ok' if ok else 'ÉCHEC',flush=True)
    time.sleep(1.2)

# ---- weekly charts ----
P2=int(time.time())
print('weekly…',flush=True)
for s in add:
    dest_wk=B+f'wk/{s}.json'
    dest_y=B+'yahoo_1wk_'+urllib.parse.quote(s)+'.json'
    url=f'https://query2.finance.yahoo.com/v8/finance/chart/{urllib.parse.quote(s)}?period1=946684800&period2={P2}&interval=1wk&events=history'
    for dest in (dest_wk, dest_y):
        if os.path.exists(dest) and os.path.getsize(dest)>500: continue
        try:
            open(dest,'wb').write(get(url)); print(' ',s,dest, os.path.getsize(dest),flush=True)
        except Exception as e:
            print('H ERR',s,dest,e,flush=True)
        time.sleep(.45)

# ---- TradingView search ----
print('tv…',flush=True)
def tvsearch(text):
    try:
        j=json.loads(get('https://symbol-search.tradingview.com/symbol_search/v3/?'+urllib.parse.urlencode({'text':text,'hl':0,'exchange':'','lang':'en','search_type':'undefined','domain':'production'}),
                         {'Origin':'https://www.tradingview.com','Referer':'https://www.tradingview.com/'}))
        return [{k:x.get(k) for k in ('symbol','exchange','description','type','country','typespecs','currency_code','isin')} for x in j.get('symbols',[])][:15]
    except Exception as e:
        return {'error':str(e)}

for s in add:
    p=B+f'tv/{s}.json'
    if os.path.exists(p) and os.path.getsize(p)>10: 
        continue
    q=s.split('.')[0].lstrip('^')
    json.dump(tvsearch(q),open(p,'w'),ensure_ascii=False)
    print(' tv',s,flush=True)
    time.sleep(.35)
print('SUISSE FETCH OK',flush=True)
