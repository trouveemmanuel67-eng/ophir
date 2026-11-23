"""Construit data/tabs_data.json (onglets Actions, Crypto, Liquidités) à partir des fichiers bruts de data/."""
import os as _os
_APEX_ROOT = _os.path.abspath(_os.environ.get('APEX_ROOT') or _os.path.join(_os.path.dirname(__file__), '..'))
import json, csv, re, os, sys, datetime as D
from zoneinfo import ZoneInfo
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ind_core as K
B=_APEX_ROOT + '/data/'
NOW=D.datetime.now(D.timezone.utc)
def mtime(p): return D.datetime.fromtimestamp(os.path.getmtime(B+p)).strftime('%Y-%m-%d %H:%M')

# ---------- indicateurs techniques ----------
def ema(v,n):
    k=2/(n+1); o=[]; e=None
    for x in v: e=x if e is None else x*k+e*(1-k); o.append(e)
    return o
def rsi(v,n=14):
    o=[None]*len(v); g=l=0
    for i in range(1,len(v)):
        d=v[i]-v[i-1]; up=max(d,0); dn=max(-d,0)
        if i<=n:
            g+=up; l+=dn
            if i==n: g/=n; l/=n; o[i]=100-100/(1+g/l) if l else 100
        else:
            g=(g*(n-1)+up)/n; l=(l*(n-1)+dn)/n; o[i]=100-100/(1+g/l) if l else 100
    return o
def macd(v):
    m=[a-b for a,b in zip(ema(v,12),ema(v,26))]; s=ema(m,9); return m,s,[a-b for a,b in zip(m,s)]
def tech(dates,closes,keep=156):
    r=rsi(closes); m,s,h=macd(closes)
    n=len(closes); i0=max(0,n-keep)
    return {'dates':dates[i0:],'close':closes[i0:],'rsi':[round(x,2) if x is not None else None for x in r[i0:]],
            'macd':[round(x,2) for x in m[i0:]],'signal':[round(x,2) for x in s[i0:]],'hist':[round(x,2) for x in h[i0:]],
            'last':{'date':dates[-1],'close':closes[-1],'rsi':round(r[-1],1),'macd':round(m[-1],2),'signal':round(s[-1],2),'hist':round(h[-1],2),'hist_prev':round(h[-2],2)}}

def perf(dates,vals,years):
    """dates ISO 'YYYY-MM-DD' triées ; valeur la plus proche à/avant la date cible."""
    last=D.date.fromisoformat(dates[-1]); out={}
    for y in years:
        tgt=last.replace(year=last.year-y)
        idx=[i for i,d in enumerate(dates) if D.date.fromisoformat(d)<=tgt]
        if not idx: out[y]=None; continue
        i=idx[-1]; out[y]={'from':dates[i],'v0':round(vals[i],2),'pct':round((vals[-1]/vals[i]-1)*100,1),
                           'cagr':round(((vals[-1]/vals[i])**(1/y)-1)*100,2)}
    return out

# ---------- ACTIONS ----------
def yahoo_weekly(f):
    w,meta=K.yweekly(B+'actions/'+f)
    return [(d, round(v,2) if isinstance(v,float) else v, c) for d,v,c in w], meta
idx_cfg=[('cac','CAC 40','yahoo_1wk_%5EFCHI.json','^FCHI','EUR'),('spx','S&P 500','yahoo_1wk_%5EGSPC.json','^GSPC','USD'),('world','MSCI World (indice prix, USD)','yahoo_1wk_%5E990100-USD-STRD.json','^990100-USD-STRD','USD')]
indices={}
for key,name,f,sym,cur in idx_cfg:
    w,meta=yahoo_weekly(f)
    wc=[x for x in w if x[2]]   # clôtures hebdo confirmées
    dates=[x[0] for x in wc]; vals=[x[1] for x in wc]
    pk=max(range(len(vals)),key=lambda i:vals[i])
    indices[key]={'name':name,'symbol':sym,'currency':cur,'dates':dates,'close':vals,'last':{'date':dates[-1],'value':vals[-1]},
      'perf':perf(dates,vals,[25,10,5,1]),'peak':{'date':dates[pk],'value':vals[pk],'dd':round((vals[-1]/vals[pk]-1)*100,1)},
      'tech':tech(dates,vals),'first':dates[0],'market_time':(D.datetime.fromtimestamp(meta['regularMarketTime'],D.timezone.utc).strftime('%Y-%m-%d %H:%M UTC') if meta.get('regularMarketTime') else None)}
# CAPE (multpl, données Shiller)
s=open(B+'actions/multpl_cape.html').read()
rows=re.findall(r'<td>([A-Z][a-z]{2} \d{1,2}, \d{4})</td>\s*<td>\s*(?:&#x2002;)?\s*([0-9.]+)\s*</td>',s)
cape=sorted([(D.datetime.strptime(a,'%b %d, %Y').date().isoformat(),float(b)) for a,b in rows])
cv=[v for d,v in cape]; cmean=sum(cv)/len(cv); cmed=sorted(cv)[len(cv)//2]
cape_d={'series':[[d,v] for d,v in cape if d>='1950-01-01'],'last':cape[-1],'mean':round(cmean,1),'median':round(cmed,1),'first':cape[0][0],
  'max':max(cape,key=lambda x:x[1]),'pctile':round(sum(1 for v in cv if v<cape[-1][1])/len(cv)*100,1)}
# FRED
def fred(f,start='2000-01-01'):
    r=list(csv.reader(open(B+f)))[1:]
    return [(a,float(b)) for a,b in r if b not in('.','') and a>=start]
vix=fred('actions/fred_VIXCLS.csv'); dgs10=fred('actions/fred_DGS10.csv'); gs10=fred('actions/fred_GS10.csv')
def weekly_last(s):
    wk={}
    for d,v in s:
        dt=D.date.fromisoformat(d); wk[dt-D.timedelta(days=dt.weekday())]=(d,v)
    return [wk[k] for k in sorted(wk)]
vixw=weekly_last(vix)
vv=[v for d,v in vix]
vix_d={'weekly':[[d,v] for d,v in vixw],'last':vix[-1],'mean':round(sum(vv)/len(vv),1),'max':max(vix,key=lambda x:x[1])}
oat=[(x['TIME_PERIOD'],float(x['OBS_VALUE'])) for x in csv.DictReader(open(B+'actions/ecb_IRS_FR_10y.csv')) if x['OBS_VALUE'] and x['TIME_PERIOD']>='2000-01']
taux10={'us_m':[[d[:7],v] for d,v in gs10],'oat_m':oat,'us_last':dgs10[-1],'oat_last':oat[-1],'us_m_last':gs10[-1]}
oatd=dict(oat); usd=dict((d[:7],v) for d,v in gs10)
taux10['spread_last']={'month':oat[-1][0],'v':round(oatd[oat[-1][0]]-usd.get(oat[-1][0],float('nan')),2) if oat[-1][0] in usd else None}
actions={'indices':indices,'cape':cape_d,'vix':vix_d,'taux10':taux10,
 'retrieved':{'yahoo':mtime('actions/yahoo_1wk_%5EGSPC.json'),'multpl':mtime('actions/multpl_cape.html'),'fred':mtime('actions/fred_VIXCLS.csv'),'ecb':mtime('actions/ecb_IRS_FR_10y.csv')}}

# ---------- CRYPTO ----------
def cm(a):
    r=json.load(open(B+f'crypto/coinmetrics_{a}_daily.json'))
    return [(x['time'][:10],float(x['PriceUSD'])) for x in r if x.get('PriceUSD')],[(x['time'][:10],float(x['CapMrktCurUSD'])) for x in r if x.get('CapMrktCurUSD')]
crypto={}
for a in ['btc','eth']:
    p,cap=cm(a)
    w=weekly_last(p)
    dates=[d for d,v in p]; vals=[v for d,v in p]
    pk=max(range(len(vals)),key=lambda i:vals[i])
    crypto[a]={'weekly':[[d,round(v,2)] for d,v in w],'last':{'date':dates[-1],'value':round(vals[-1],2)},'first':dates[0],
       'perf':perf(dates,vals,[10,5,1]),'peak':{'date':dates[pk],'value':round(vals[pk],2),'dd':round((vals[-1]/vals[pk]-1)*100,1)},
       'cap_last':[cap[-1][0],cap[-1][1]] if cap else None}
# Binance hebdo (bougies clôturées uniquement)
def binance(sym):
    k=json.load(open(B+f'crypto/binance_{sym}_1w.json'))
    nowms=NOW.timestamp()*1000
    closed=[x for x in k if x[6]<nowms]
    cur=[x for x in k if x[6]>=nowms]
    dates=[D.datetime.fromtimestamp(x[0]/1000,D.timezone.utc).date().isoformat() for x in closed]
    closes=[float(x[4]) for x in closed]
    t=tech(dates,closes)
    t['current']={'open_date':D.datetime.fromtimestamp(cur[0][0]/1000,D.timezone.utc).date().isoformat(),'close':float(cur[0][4])} if cur else None
    t['first']=dates[0]
    return t
crypto['btc_tech']=binance('BTCUSDT')
g=json.load(open(B+'crypto/coingecko_global.json'))['data']
crypto['global']={'total_cap_usd':g['total_market_cap']['usd'],'btc_dom':round(g['market_cap_percentage']['btc'],2),'eth_dom':round(g['market_cap_percentage']['eth'],2),
  'chg24h':round(g['market_cap_change_percentage_24h_usd'],2),'updated':D.datetime.fromtimestamp(g['updated_at'],D.timezone.utc).strftime('%Y-%m-%d %H:%M UTC'),
  'top':sorted([[k,round(v,2)] for k,v in g['market_cap_percentage'].items()],key=lambda x:-x[1])[:8]}
f=json.load(open(B+'crypto/alternative_fng.json'))['data']
fng=sorted([(D.datetime.fromtimestamp(int(x['timestamp']),D.timezone.utc).date().isoformat(),int(x['value']),x['value_classification']) for x in f])
fv=[v for d,v,c in fng]
crypto['fng']={'series':[[d,v] for d,v,c in fng],'last':fng[-1],'avg30':round(sum(fv[-30:])/30,1),'avg365':round(sum(fv[-365:])/365,1),'first':fng[0][0],
  'days_extreme_fear_30':sum(1 for v in fv[-30:] if v<25)}
crypto['retrieved']={'coinmetrics':mtime('crypto/coinmetrics_btc_daily.json'),'binance':mtime('crypto/binance_BTCUSDT_1w.json'),'coingecko':mtime('crypto/coingecko_global.json'),'alt':mtime('crypto/alternative_fng.json')}
# Fiches APEX BTC / ETH / XRP / SOL / MSTR (construites par src/build_crypto_fiches.py)
_fp=B+'crypto_fiches.json'
if os.path.exists(_fp):
    crypto['fiches']=json.load(open(_fp))


# ---------- LIQUIDITÉS ----------
L=B+'liquidites/'
raw=open(L+'bdf_taux_livrets_reglementes.csv',encoding='latin1').read().splitlines()
arch={}
for line in raw:
    m=re.match(r'^(\d{2})/(\d{4});([^;]*);([^;]*);',line)
    if m:
        ym=f"{m.group(2)}-{m.group(1)}"
        la=float(m.group(3).replace(',','.')); lep=None if m.group(4).strip()=='ND' else float(m.group(4).replace(',','.'))
        arch[ym]=(la,lep)
ch=json.load(open(L+'bdf_livrets_changements_officiels.json'))['changes']
chd={c['date']:(c['livret_a'],c['lep']) for c in ch}
months=[]; y,mo=2000,1
end=(NOW.year,NOW.month)
while (y,mo)<=end:
    months.append(f"{y}-{mo:02d}"); mo+=1
    if mo==13: y+=1; mo=1
liv={}; cur=None
for ym in months:
    if ym in arch: cur=arch[ym]; liv[ym]=cur+('bdf_archive',)
    else:
        if ym in chd: cur=chd[ym]
        liv[ym]=cur+('bdf_textes',)
# contrôle croisé avec la CDC (2024-01 → 2026-06)
cdc=list(csv.DictReader(open(L+'cdc_flux_taux_la_ldds_lep.csv',encoding='utf-8-sig')))
mism=[]
for r in cdc:
    ym=r['Date']; 
    if ym in liv and (abs(float(r['TLA/TLDDS'])-liv[ym][0])>1e-9 or abs(float(r['TLEP'])-liv[ym][1])>1e-9): mism.append((ym,r['TLA/TLDDS'],r['TLEP'],liv[ym]))
assert not mism, mism
def bdm(f):
    s=open(L+f).read()
    o=sorted((a,float(b)) for a,b in re.findall(r'TIME_PERIOD="([^"]+)" OBS_VALUE="([^"]+)"',s))
    return o,re.search(r'LAST_UPDATE="([^"]+)"',s).group(1)
ipc,ipc_upd=bdm('insee_ipc_ga_011814632.xml')
ipc=[x for x in ipc if x[0]>='2000-01']; ipcd=dict(ipc)
real=[[ym,round(liv[ym][0]-ipcd[ym],2),round(liv[ym][1]-ipcd[ym],2) if liv[ym][1] is not None else None] for ym in months if ym in ipcd]
def ecb(f,start='1999-01-01'):
    return [(x['TIME_PERIOD'],float(x['OBS_VALUE'])) for x in csv.DictReader(open(L+f)) if x['OBS_VALUE'] and x['TIME_PERIOD']>=start]
dfr=ecb('ecb_FM_D.U2.EUR.4F.KR.DFR.LEV.csv'); estr=ecb('ecb_EST_B.EU000A2X2A25.WT.csv'); eur3=ecb('ecb_FM_M.U2.EUR.RT.MM.EURIBOR3MD_.HSTA.csv'); eurusd=ecb('ecb_EXR_D.USD.EUR.SP00.A.csv')
def monthly(s,how='last'):
    m={}
    for d,v in s: m.setdefault(d[:7],[]).append(v)
    return [[k,round(v[-1] if how=='last' else sum(v)/len(v),3)] for k,v in sorted(m.items())]
dfr_ch=[]; prev=None
for d,v in dfr:
    if v!=prev: dfr_ch.append([d,v]); prev=v
dxy,_=yahoo_weekly('../liquidites/../actions/yahoo_1wk_DX-Y.NYB.json')
dxyc=[x for x in dxy if x[2]]
liq={'livrets':{'monthly':[[ym,liv[ym][0],liv[ym][1],liv[ym][2]] for ym in months],'last':[months[-1],liv[months[-1]][0],liv[months[-1]][1]],'changes':ch,'cdc_check':len(cdc)},
 'ipc':{'idbank':'011814632','series':ipc,'last':ipc[-1],'last_update':ipc_upd},
 'real':real,'real_last':real[-1],
 'bce':{'dfr_m':monthly([x for x in dfr if x[0]>='2000-01-01']),'dfr_last':dfr[-1],'dfr_changes':dfr_ch[-8:],'estr_m':monthly(estr,'avg'),'estr_last':estr[-1],'eur3_m':[[d,round(v,3)] for d,v in eur3 if d>='2000-01'],'eur3_last':eur3[-1]},
 'fx':{'eurusd_w':[[d,v] for d,v in weekly_last([x for x in eurusd if x[0]>='2000-01-01'])],'eurusd_last':eurusd[-1],
       'dxy_w':[[d,v] for d,v,c in dxyc],'dxy_last':[dxyc[-1][0],dxyc[-1][1]],
       'eurusd_1y':None},
 'mmf':None,
 'retrieved':{'bdf':mtime('liquidites/bdf_taux_livrets_reglementes.csv'),'cdc':mtime('liquidites/cdc_flux_taux_la_ldds_lep.csv'),'insee':mtime('liquidites/insee_ipc_ga_011814632.xml'),'ecb':mtime('liquidites/ecb_EXR_D.USD.EUR.SP00.A.csv'),'yahoo':mtime('actions/yahoo_1wk_DX-Y.NYB.json')}}
# EUR/USD : variation 1 an
ed=[d for d,v in eurusd]; ev=[v for d,v in eurusd]
liq['fx']['eurusd_perf']=perf(ed,ev,[1,5])
dd=[d for d,v,c in dxyc]; dv=[v for d,v,c in dxyc]
liq['fx']['dxy_perf']=perf(dd,dv,[1,5])
# Devises des pays représentés sur APEX, toutes contre l'euro (cours de référence BCE).
# Chine et Inde n'ont pas de bloc pays : CNY et INR non ajoutées.
def fx_trend(p1m, p1y):
    if p1m is None and p1y is None: return None
    a=p1m['pct'] if p1m else 0
    b=p1y['pct'] if p1y else 0
    if a>0.5 and b>0.5: return 'hausse'
    if a<-0.5 and b<-0.5: return 'baisse'
    return 'mixte'
def fx_pack(code, nom, pair, tv, series, dec):
    series=[x for x in series if x[0]>='2000-01-01']
    w=weekly_last(series)
    dates=[d for d,v in series]; vals=[v for d,v in series]
    pr=perf(dates,vals,[1,5])
    # 1 semaine et 1 mois (≈ 5 et 21 séances) sur la série quotidienne
    def ago(n):
        if len(series)<=n: return None
        v0=series[-1-n][1]
        return {'from':series[-1-n][0],'v0':round(v0,dec),'pct':round((series[-1][1]/v0-1)*100,1)}
    p1w,p1m=ago(5),ago(21)
    return {'code':code,'nom':nom,'pair':pair,'tv':tv,'dec':dec,
            'last':[series[-1][0],round(series[-1][1],dec)],
            'weekly':[[d,round(v,dec)] for d,v in w],
            'perf':{'1w':p1w,'1m':p1m,'1y':pr.get(1),'5y':pr.get(5)},
            'trend':fx_trend(p1m, pr.get(1)),
            'note':None}
FX_SPEC=[
    ('USD','Dollar américain','EUR/USD','FX:EURUSD','ecb_EXR_D.USD.EUR.SP00.A.csv',4),
    ('JPY','Yen japonais','EUR/JPY','FX:EURJPY','ecb_EXR_D.JPY.EUR.SP00.A.csv',2),
    ('GBP','Livre sterling','EUR/GBP','FX:EURGBP','ecb_EXR_D.GBP.EUR.SP00.A.csv',4),
    ('CHF','Franc suisse','EUR/CHF','FX:EURCHF','ecb_EXR_D.CHF.EUR.SP00.A.csv',4),
    ('AUD','Dollar australien','EUR/AUD','FX:EURAUD','ecb_EXR_D.AUD.EUR.SP00.A.csv',4),
    ('CAD','Dollar canadien','EUR/CAD','FX:EURCAD','ecb_EXR_D.CAD.EUR.SP00.A.csv',4),
    ('KRW','Won sud-coréen','EUR/KRW','FX:EURKRW','ecb_EXR_D.KRW.EUR.SP00.A.csv',1),
]
liq['fx']['pairs']=[fx_pack(code,nom,pair,tv,ecb(fn),dec) for code,nom,pair,tv,fn,dec in FX_SPEC]
liq['fx']['pairs_note']="Cours de référence BCE, une unité d'euro en devise étrangère (convention EXR). Repères de marché, sans note APEX. Pays représentés sur APEX : USD, EUR, JPY, GBP, CHF, AUD, CAD, KRW. CNY et INR non retenus (pas de bloc Chine ni Inde)."
liq['fx']['pairs_source']='https://data.ecb.europa.eu/data/datasets/EXR'

out={'generated':NOW.astimezone().strftime('%Y-%m-%d %H:%M'),'actions':actions,'crypto':crypto,'liquidites':liq}
if os.path.exists(B+'energie.json'):
    out['energie']=json.load(open(B+'energie.json'))
json.dump(out,open(B+'tabs_data.json','w'),ensure_ascii=False)
# résumé
for k,v in indices.items(): print(k,v['last'],{y:(p['pct'] if p else None) for y,p in v['perf'].items()},v['peak'],'RSI',v['tech']['last']['rsi'],'hist',v['tech']['last']['hist'])
print('CAPE',cape_d['last'],cape_d['mean'],cape_d['pctile'],'VIX',vix_d['last'],'US10',dgs10[-1],'GS10',gs10[-1],'OAT',oat[-1],taux10['spread_last'])
for a in['btc','eth']: print(a,crypto[a]['last'],{y:(p['pct'] if p else None) for y,p in crypto[a]['perf'].items()},crypto[a]['peak'])
print('BTC tech',crypto['btc_tech']['last'],crypto['btc_tech']['current'])
print('global',{k:crypto['global'][k] for k in('total_cap_usd','btc_dom','eth_dom','updated')},'fng',crypto['fng']['last'],crypto['fng']['avg30'])
print('livrets',liq['livrets']['last'],'ipc',liq['ipc']['last'],'real',liq['real_last'],'dfr',liq['bce']['dfr_last'],'estr',liq['bce']['estr_last'],'eur3',liq['bce']['eur3_last'],'eurusd',liq['fx']['eurusd_last'],liq['fx']['eurusd_perf'],'dxy',liq['fx']['dxy_last'],liq['fx']['dxy_perf'])
