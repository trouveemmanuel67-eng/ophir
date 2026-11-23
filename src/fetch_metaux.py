"""Onglet MÉTAUX PRÉCIEUX : cours hebdomadaires Yahoo (contrats à terme COMEX / NYMEX, ETC physiques, minières), FRED (EUR/USD, taux réel 10 ans US),
CFTC (positions Commitments of Traders, rapport « disaggregated », contrats à terme seuls). -> data/metaux/"""
import os as _os
_APEX_ROOT = _os.path.abspath(_os.environ.get('APEX_ROOT') or _os.path.join(_os.path.dirname(__file__), '..'))
import json, os, time, io, zipfile, csv, urllib.request, urllib.parse, datetime as D
B=_APEX_ROOT + '/data/metaux/'; UA={'User-Agent':'Mozilla/5.0'}
def get(u,h=None,t=120): return urllib.request.urlopen(urllib.request.Request(u,headers={**UA,**(h or {})}),timeout=t).read()
P2=int(time.time())
SY=['GC=F','SI=F','PL=F','PA=F','DBC','^GSPC','4GLD.DE','XAD5.DE','8PSG.DE','PPFB.DE','GOLD.PA','G2X.DE','IS0E.DE','XAD6.DE','PHAG.L','SSLN.L','SILV.L','PHPT.L','IPLT.L','XAD3.DE','PHPD.L','SPAL.L',
    'NEM','AEM','B','WPM','FNV','KGC','AU','GFI','RGLD','PAAS','HL','CDE','AG','FRES.L','SBSW','IMP.JO','NST.AX','EVN.AX']
for s in SY:
    try: open(B+'y_'+urllib.parse.quote(s,safe='')+'.json','wb').write(get(f'https://query2.finance.yahoo.com/v8/finance/chart/{urllib.parse.quote(s)}?period1=946684800&period2={P2}&interval=1wk&events=history'))
    except Exception as e: print('Y ERR',s,e)
    time.sleep(.5)
print('yahoo ok',flush=True)
for sid in ['DEXUSEU','DFII10']:
    try: open(B+f'fred_{sid}.csv','wb').write(get(f'https://fred.stlouisfed.org/graph/fredgraph.csv?id={sid}',{'User-Agent':'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120 Safari/537.36'}))
    except Exception as e: print('FRED ERR',sid,e)
print('fred ok',flush=True)
CODES={'088691':'or','084691':'argent','076651':'platine','075651':'palladium'}
rows=[]
def take(raw):
    z=zipfile.ZipFile(io.BytesIO(raw)); n=z.namelist()[0]; r=csv.DictReader(io.TextIOWrapper(z.open(n),encoding='latin-1'))
    for x in r:
        c=(x.get('CFTC_Contract_Market_Code') or '').strip()
        if c in CODES:
            rows.append({'m':CODES[c],'d':(x.get('Report_Date_as_YYYY-MM-DD') or '').strip(),'name':x.get('Market_and_Exchange_Names','').strip(),
                         'mm_long':int(x['M_Money_Positions_Long_All']),'mm_short':int(x['M_Money_Positions_Short_All']),'oi':int(x['Open_Interest_All'])})
urls=['https://www.cftc.gov/files/dea/history/fut_disagg_txt_hist_2006_2016.zip']+[f'https://www.cftc.gov/files/dea/history/fut_disagg_txt_{y}.zip' for y in range(2017,D.date.today().year+1)]
for u in urls:
    try: take(get(u)); print('cftc',u[-12:],len(rows),flush=True)
    except Exception as e: print('CFTC ERR',u,e,flush=True)
    time.sleep(1)
json.dump({'retrieved':D.datetime.now().strftime('%Y-%m-%d %H:%M'),'rows':rows,'source':urls},open(B+'cftc.json','w'))
print('fini',flush=True)
