"""Historique hebdomadaire MAXIMAL Yahoo (period1=1900, interval=1wk) pour le retracement de Fibonacci base → ATH.
Attention : range=max renvoie des bougies trimestrielles/mensuelles ; il faut period1/period2 pour garder l'hebdo."""
import json,os,glob,time,urllib.parse,urllib.request,sys
R='/workspace/invest/patrimoine-dashboard/data/'; O=R+'fibo_max/'
S=set()
uq=lambda f:urllib.parse.unquote(f)
for f in glob.glob(R+'secteurs/yahoo_1wk_*.json')+glob.glob(R+'pays/yahoo_1wk_*.json')+glob.glob(R+'actions/yahoo_1wk_*.json'):
    S.add(uq(os.path.basename(f)[10:-5]))
for f in glob.glob(R+'metaux/y_*.json'): S.add(uq(os.path.basename(f)[2:-5]))
for f in glob.glob(R+'obligations/w_*.json'):
    try: S.add(json.load(open(f))['symbol'])
    except Exception: pass
for o in json.load(open('/workspace/invest/indiv/map.json')): S.add(o['yahoo']); S.add(o['bench'])
S|={'BTC-USD','ETH-USD','XRP-USD','SOL-USD'}
S={s for s in S if s}
P2=int(time.time()); force='--force' in sys.argv
from zoneinfo import ZoneInfo
import datetime as D
def _stale(path):
    """True si le fichier n'a pas été retéléchargé après la dernière clôture du vendredi."""
    if not os.path.exists(path) or os.path.getsize(path)<=2000:
        return True
    mt=D.datetime.fromtimestamp(os.path.getmtime(path), ZoneInfo('Europe/Paris'))
    today=D.datetime.now(ZoneInfo('Europe/Paris')).date()
    last_fri=today-D.timedelta(days=(today.weekday()-4)%7)
    if today.weekday()<=3:  # lun–jeu : le vendredi visé est celui de la semaine précédente déjà passé
        pass
    deadline=D.datetime.combine(last_fri+D.timedelta(days=1), D.time(0,0), tzinfo=ZoneInfo('Europe/Paris'))
    return mt<deadline
for s in sorted(S):
    p=O+urllib.parse.quote(s,safe='')+'.json'
    if os.path.exists(p) and os.path.getsize(p)>2000 and not force and not _stale(p): continue
    for k in range(3):
        try:
            r=urllib.request.urlopen(urllib.request.Request(f'https://query2.finance.yahoo.com/v8/finance/chart/{urllib.parse.quote(s)}?period1=-2208988800&period2={P2}&interval=1wk&events=history',headers={'User-Agent':'Mozilla/5.0'}),timeout=30).read()
            open(p,'wb').write(r); break
        except Exception as e: print('ERR',s,e); time.sleep(3)
    time.sleep(.3)
print('symboles',len(S))
