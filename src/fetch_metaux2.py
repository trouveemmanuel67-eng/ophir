"""Onglet MÉTAUX PRÉCIEUX (complément) : cours Yahoo des ETC platine / palladium / argent cotés sur Xetra, fiches quoteSummary des minières
(santé financière et croissance prévue), recherche TradingView de chaque instrument (vérification symbole + place). -> data/metaux/"""
import os as _os
_APEX_ROOT = _os.path.abspath(_os.environ.get('APEX_ROOT') or _os.path.join(_os.path.dirname(__file__), '..'))
import json, os, time, urllib.request, urllib.parse, datetime as D
from yfinance.data import YfData
B=_APEX_ROOT + '/data/metaux/'; UA={'User-Agent':'Mozilla/5.0'}
now=lambda:D.datetime.now().strftime('%Y-%m-%d %H:%M')
def get(u,h=None,t=60): return urllib.request.urlopen(urllib.request.Request(u,headers={**UA,**(h or {})}),timeout=t).read()
P2=int(time.time())
for s in ['8PSA.DE','VZLA.DE','XPPT.DE','8PSC.DE','VZLB.DE','8PSB.DE']:
    try: open(B+'y_'+urllib.parse.quote(s,safe='')+'.json','wb').write(get(f'https://query2.finance.yahoo.com/v8/finance/chart/{urllib.parse.quote(s)}?period1=946684800&period2={P2}&interval=1wk&events=history'))
    except Exception as e: print('Y ERR',s,e)
    time.sleep(.6)
MIN=['NEM','AEM','B','WPM','FNV','KGC','AU','GFI','RGLD','NST.AX','EVN.AX','PAAS','HL','CDE','AG','FRES.L','SBSW','IMP.JO']
yd=YfData(); MOD='assetProfile,price,financialData,defaultKeyStatistics,summaryDetail,earningsTrend'
for s in MIN:
    p=B+f'qs/{s}.json'
    if os.path.exists(p): continue
    for a in range(5):
        try:
            j=yd.get_raw_json(f'https://query2.finance.yahoo.com/v10/finance/quoteSummary/{s}',params={'modules':MOD,'corsDomain':'finance.yahoo.com','formatted':'false'})
            json.dump({'symbol':s,'retrieved':now(),'qs':j['quoteSummary']['result'][0]},open(p,'w'),ensure_ascii=False); break
        except Exception as e:
            if '404' in str(e): break
            time.sleep(15*(a+1))
    print('qs',s,os.path.exists(p),flush=True); time.sleep(2.5)
INS=['4GLD.DE','XAD5.DE','8PSG.DE','PPFB.DE','G2X.DE','IS0E.DE','XAD6.DE','8PSB.DE','PHAG.L','SSLN.L','SILV.L','8PSA.DE','VZLA.DE','XPPT.DE','IPLT.L','XAD3.DE','8PSC.DE','VZLB.DE','SPAL.L']+MIN
for s in INS:
    p=B+f'tv/{s}.json'
    if os.path.exists(p): continue
    try:
        j=json.loads(get('https://symbol-search.tradingview.com/symbol_search/v3/?'+urllib.parse.urlencode({'text':s.split('.')[0],'hl':0,'exchange':'','lang':'en','search_type':'undefined','domain':'production'}),{'Origin':'https://www.tradingview.com','Referer':'https://www.tradingview.com/'}))
        json.dump([{k:x.get(k) for k in ('symbol','exchange','prefix','description','type','country','currency_code')} for x in j.get('symbols',[])][:20],open(p,'w'),ensure_ascii=False)
    except Exception as e: print('T ERR',s,e)
    time.sleep(.5)
print('fini',flush=True)
