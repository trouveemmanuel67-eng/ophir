import time, json, sys
from pytrends.request import TrendReq
A=["achat immobilier","acheter immobilier","acheter maison","acheter appartement"]
V=["vente immobilier","vendre immobilier","estimation immobilière","agence immobilière"]
reqs={"achat":A,"vente_pivot":V+["acheter maison"]}
for name,kw in reqs.items():
    for att in range(6):
        try:
            p=TrendReq(hl='fr-FR',tz=-60,timeout=(10,30))
            p.build_payload(kw,timeframe='today 12-m',geo='FR')
            df=p.interest_over_time()
            df.to_csv(f'trends_{name}_FR_12m.csv'); print(name,'OK',len(df)); break
        except Exception as e:
            print(name,'err',att,repr(e)[:200]); time.sleep(20*(att+1))
    time.sleep(15)
