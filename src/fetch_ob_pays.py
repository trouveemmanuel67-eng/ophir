"""Onglet Obligations · taux souverains par pays (25 ans) -> data/obpays/
OCDE (SDMX, taux longs 10 ans IRLT et taux 3 mois IR3TIB, mensuels), Bundesbank (Bund 2, 10, 30 ans, quotidiens),
Ministère des Finances du Japon (JGB 2, 10, 30 ans, quotidiens). États-Unis : FRED (déjà récupéré par fetch_obligations.py)."""
import subprocess, time, datetime as D, json
B='/workspace/invest/patrimoine-dashboard/data/obpays/'
def get(url,t=120):
    for k in range(4):
        r=subprocess.run(['curl','-sfL','-m',str(t),'-A','Mozilla/5.0',url],capture_output=True)
        if r.returncode==0 and r.stdout: return r.stdout
        time.sleep(5*(k+1))
    raise RuntimeError('échec '+url)
SRC={}
def save(name,url):
    try: open(B+name,'wb').write(get(url)); SRC[name]={'url':url,'retrieved':D.datetime.now().strftime('%Y-%m-%d %H:%M')}; print('ok',name,flush=True)
    except Exception as e: print('ERR',name,e,flush=True)
save('oecd_irlt.csv','https://sdmx.oecd.org/public/rest/data/OECD.SDD.STES,DSD_STES@DF_FINMARK,4.0/KOR+AUS+FRA+ITA+JPN+DEU+USA+CAN.M.IRLT.PA.....?startPeriod=2000-01&format=csvfilewithlabels')
save('oecd_ir3.csv','https://sdmx.oecd.org/public/rest/data/OECD.SDD.STES,DSD_STES@DF_FINMARK,4.0/KOR+AUS+FRA+ITA+JPN+DEU+USA+CAN.M.IR3TIB.PA.....?startPeriod=2000-01&format=csvfilewithlabels')
for m in ['R02XX','R10XX','R30XX']:
    save(f'bbk_{m}.csv',f'https://api.statistiken.bundesbank.de/rest/download/BBSIS/D.I.ZST.ZI.EUR.S1311.B.A604.{m}.R.A.A._Z._Z.A?format=csv&lang=en')
save('mof_all.csv','https://www.mof.go.jp/english/policy/jgbs/reference/interest_rate/historical/jgbcme_all.csv')
save('mof_cur.csv','https://www.mof.go.jp/english/policy/jgbs/reference/interest_rate/jgbcme.csv')
json.dump(SRC,open(B+'sources.json','w'),ensure_ascii=False)
