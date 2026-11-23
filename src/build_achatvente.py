"""Compteur ACHAT / VENTE par onglet -> data/achatvente.json
Chaque composante est notée de −100 à +100 par une règle explicite (voir RULES), puis pondérée.
Score = Σ(poids × note) / Σ(poids des composantes disponibles). Bougies hebdomadaires clôturées uniquement."""
import os as _os
_APEX_ROOT = _os.path.abspath(_os.environ.get('APEX_ROOT') or _os.path.join(_os.path.dirname(__file__), '..'))
import json, csv, re, os, sys, datetime as D, bisect
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__))); import elliott as E, ind_core as K, fibo as FB, charte as CH
W_EL=K.W_EL; W_FI=K.W_FI; W_CH=K.W_CH; W_DV=K.W_DV; SC=K.SC   # 17/11/2026 : Elliott 15 % + Fibonacci 15 % + Charte graphique 20 % + Divergence RSI weekly 10 %, autres poids ×0,40 (proportions conservées)
B=_APEX_ROOT + '/data/'
NOW=D.datetime.now(D.timezone.utc)
clip=lambda x:max(-100.0,min(100.0,x))
def prank(h,v): return 100*(sum(1 for x in h if x<v)+0.5*sum(1 for x in h if x==v))/len(h)
def ema(v,n):
    k=2/(n+1);o=[];e=None
    for x in v: e=x if e is None else x*k+e*(1-k); o.append(e)
    return o
def rsi(v,n=14):
    o=[None]*len(v);g=l=0
    for i in range(1,len(v)):
        d=v[i]-v[i-1];up=max(d,0);dn=max(-d,0)
        if i<=n:
            g+=up;l+=dn
            if i==n: g/=n;l/=n;o[i]=100-100/(1+g/l) if l else 100
        else: g=(g*(n-1)+up)/n;l=(l*(n-1)+dn)/n;o[i]=100-100/(1+g/l) if l else 100
    return o
def macd(v):
    m=[a-b for a,b in zip(ema(v,12),ema(v,26))];s=ema(m,9);return m,s,[a-b for a,b in zip(m,s)]
def sma(v,n): return [sum(v[i-n+1:i+1])/n if i>=n-1 else None for i in range(len(v))]
def asof(series,d):
    keys=[x[0] for x in series];i=bisect.bisect_right(keys,d)-1
    return series[i] if i>=0 else None
def label(s): return 'Vente forte' if s<=-60 else 'Vente' if s<=-20 else 'Neutre' if s<20 else 'Achat' if s<60 else 'Achat fort'
# --- règles de notation (−100 … +100) ---
def r_rsi(x): return clip((x-50)/20*100)                       # RSI 70 → +100, 30 → −100 (lecture tendance)
def r_macd(m,s,h,hp,hist=None,i=None):
    return K.r_macd(m,s,h,hp,hist,i)
def r_mm(x,band): return clip(x/band*100)                       # écart à la moyenne mobile, ±band → ±100
def r_dd_actions(dd):                                           # règle d'Emmanuel : pas d'entrée au plus haut
    if dd>=-2: return -60.0
    if dd>=-12: return -60+(-2-dd)/10*120                        # −2 % → −60 ; −12 % → +60
    if dd>=-25: return 60.0
    return max(0.0,60-(-25-dd)/15*60)                           # baisse > 25 % : prudence, retour vers 0
def r_dd_crypto(dd): return clip((-dd-30)/30*80)                # record → −80 ; −30 % → 0 ; −60 % → +80
def r_contra(fg): return clip((50-fg)*2)                        # contrarien : peur extrême = +, euphorie = −
def r_pct_inv(p): return clip((50-p)*2)                         # percentile élevé = cher = négatif
def score(comps):
    av=[c for c in comps if c['note'] is not None]
    w=sum(c['poids'] for c in av)
    for c in comps: c['contrib']=round(c['poids']*c['note']/w,1) if c['note'] is not None and w else None
    return round(sum(c['poids']*c['note'] for c in av)/w,1) if w else None, [c['nom'] for c in comps if c['note'] is None and not c.get('facultatif')]
IND=json.load(open(B+'indicateur.json'))
TABS=json.load(open(B+'tabs_data.json')); DASH=json.load(open(B+'dashboard_data.json'))
MO=['janv.','févr.','mars','avr.','mai','juin','juil.','août','sept.','oct.','nov.','déc.']
out={}
def finish(key,sens,hist,comps_last,date,method,sources):
    s,miss=score(comps_last)
    for c in comps_last:
        c['note']=None if c['note'] is None else round(c['note'],1); c['poids']=round(c['poids'],4)
    out[key]={'score':s,'label':label(s),'date':date,'sens':sens,'components':comps_last,'missing':miss,
              'history':[[d,round(v,1)] for d,v in hist],'method':method,'sources':sources,
              'avg':round(sum(v for d,v in hist)/len(hist),1),'min':min(hist,key=lambda x:x[1]),'max':max(hist,key=lambda x:x[1])}

# ================= ACTIONS =================
A=TABS['actions']; I=A['indices']
s_m=open(B+'actions/multpl_cape.html').read()
cape=sorted([(D.datetime.strptime(a,'%b %d, %Y').date().isoformat(),float(b)) for a,b in re.findall(r'<td>([A-Z][a-z]{2} \d{1,2}, \d{4})</td>\s*<td>\s*(?:&#x2002;)?\s*([0-9.]+)\s*</td>',s_m)])
cape=[list(x) for x in cape]
vixw=A['vix']['weekly']
us=[[a,float(b)] for a,b in list(csv.reader(open(B+'actions/fred_DGS10.csv')))[1:] if b not in('.','')]
oat=[[x[0],x[1]] for x in A['taux10']['oat_m']]
cnn=IND['actions']['series']
pre={}
YF={'cac':'yahoo_1wk_%5EFCHI.json','spx':'yahoo_1wk_%5EGSPC.json','world':'yahoo_1wk_%5E990100-USD-STRD.json'}
YS={'cac':'^FCHI','spx':'^GSPC','world':'^990100-USD-STRD'}
for k in ('cac','spx','world'):
    x=I[k]; c=x['close']; r=rsi(c); m,sg,h=macd(c); mm=sma(c,40); O=K.yopens(B+'actions/'+YF[k])
    pre[k]=dict(dates=x['dates'],c=c,r=r,m=m,s=sg,h=h,mm=mm,o=[O.get(d) for d in x['dates']],ell={},fpre=FB.prefix(YS[k],x['dates'][0],c[0]),hl=K.yhl(B+'actions/'+YF[k]))
def cha_a(k,j):
    p=pre[k]; cc=p.setdefault('cha',{})
    if j not in cc: cc[j]=CH.analyse(p['c'][:j+1],p['dates'][:j+1],p['o'][:j+1],p['hl'],p['r'][:j+1],syms=[YS[k]],manual=(j==len(p['c'])-1))
    return cc[j]
def ell_a(k,j):
    p=pre[k]
    if j not in p['ell']: p['ell'][j]=E.analyse(p['o'][:j+1],p['c'][:j+1])
    return p['ell'][j]
def fib_a(k,j):
    p=pre[k]; fc=p.setdefault('fib',{})
    if j not in fc: fc[j]=FB.analyse(p['o'][:j+1],p['c'][:j+1],p['dates'][:j+1],p['fpre'])
    return fc[j]
def actions_at(i_ref):
    d=pre['spx']['dates'][i_ref]; comps=[]; raw={}
    def idx(k): 
        ds=pre[k]['dates']; j=bisect.bisect_right(ds,d)-1; return j
    R=[];M=[];MM=[];DD=[]
    for k in ('cac','spx','world'):
        p=pre[k]; j=idx(k)
        R.append(p['r'][j]); M.append(r_macd(p['m'][j],p['s'][j],p['h'][j],p['h'][j-1],p['h'],j))
        MM.append((p['c'][j]/p['mm'][j]-1)*100)
        hi=max(p['c'][max(0,j-51):j+1]); DD.append((p['c'][j]/hi-1)*100)
    rs=sum(R)/3; mmv=sum(MM)/3; ddv=sum(DD)/3
    comps.append(E.comp_multi([(nm,ell_a(k,idx(k))) for nm,k in (('CAC 40','cac'),('S&P 500','spx'),('MSCI World','world'))],W_EL))
    comps.append(FB.comp_multi([(nm,fib_a(k,idx(k))) for nm,k in (('CAC 40','cac'),('S&P 500','spx'),('MSCI World','world'))],W_FI))
    comps.append({'nom':'RSI 14 hebdo (moyenne CAC 40, S&P 500, MSCI World)','poids':.15,'valeur':f"{rs:.1f}".replace('.',','),'note':r_rsi(rs),'regle':'(RSI − 50) / 20 × 100'})
    comps.append({'nom':'MACD 12/26/9 hebdo (3 indices)','poids':.15,'valeur':' · '.join(n+' '+{100:'↑↑',50:'↑',-50:'↓',-100:'↓↓'}.get(x,str(x)) for n,x in zip(('CAC','S&P','World'),M)),'note':sum(M)/3,'regle':K.RULE_MACD})
    comps.append({'nom':'Position / moyenne mobile 40 semaines','poids':.15,'valeur':f"{mmv:+.1f} %".replace('.',','),'note':r_mm(mmv,10),'regle':'écart moyen des 3 indices, ±10 % → ±100'})
    comps.append({'nom':'Distance au plus haut 52 semaines','poids':.10,'valeur':f"{ddv:+.1f} %".replace('.',','),'note':r_dd_actions(ddv),'regle':'≥ −2 % : −60 (pas d\'entrée au plus haut) ; −2 → −12 % : de −60 à +60 ; −12 → −25 % : +60 ; au-delà : retour vers 0'})
    cp=asof(cape,d); pc=prank([x[1] for x in cape if x[0]<=cp[0]],cp[1])
    comps.append({'nom':'Valorisation : CAPE S&P 500 (percentile historique)','poids':.15,'valeur':f"{cp[1]:.2f} · {pc:.0f}ᵉ pct".replace('.',','),'note':r_pct_inv(pc),'regle':'(50 − percentile) × 2 : cher = négatif'})
    vw=asof(vixw,d); lo=(D.date.fromisoformat(d)-D.timedelta(days=5*365)).isoformat(); pv=prank([x[1] for x in vixw if lo<x[0]<=vw[0]],vw[1])
    comps.append({'nom':'VIX (percentile 5 ans, lecture contrarienne)','poids':.10,'valeur':f"{vw[1]:.1f} · {pv:.0f}ᵉ pct".replace('.',','),'note':clip((pv-50)*2),'regle':'(percentile − 50) × 2 : VIX élevé = peur = plutôt favorable'})
    u=asof(us,d); u0=asof(us,(D.date.fromisoformat(d)-D.timedelta(days=91)).isoformat())
    o=asof(oat,d[:7]); o0=asof(oat,(D.date.fromisoformat(o[0]+'-01')-D.timedelta(days=80)).isoformat()[:7])
    dt=((u[1]-u0[1])+(o[1]-o0[1]))/2
    comps.append({'nom':'Taux 10 ans US et OAT : variation sur 3 mois','poids':.10,'valeur':f"{dt:+.2f} pt".replace('.',','),'note':clip(-dt/0.5*100),'regle':'hausse de 0,5 pt → −100, baisse de 0,5 pt → +100'})
    f=asof(cnn,d)
    comps.append({'nom':'Sentiment : CNN Fear & Greed (contrarien)','poids':.10,'valeur':f"{f[1]:.0f}" if f else 'n.d.','note':r_contra(f[1]) if f else None,'regle':'(50 − indice) × 2'})
    for x in comps[2:]: x['poids']=round(x['poids']*SC,4)
    IT=[(nm,cha_a(k,idx(k))) for nm,k in (('CAC 40','cac'),('S&P 500','spx'),('MSCI World','world'))]
    comps[2:2]=[CH.comp_multi(IT,W_CH),CH.comp_div_multi(IT,W_DV)]
    ccis=[]
    for k in ('cac','spx','world'):
        p=pre[k]; j=idx(k)
        cc=p.setdefault('cci', K.cci20(p['o'], p['c']))
        if cc[j] is not None: ccis.append(cc[j])
    K.add_cci(comps, (sum(ccis)/len(ccis) if ccis else None))
    return d,comps
n=len(pre['spx']['dates']); hist=[]
for i in range(n-52,n):
    d,c=actions_at(i); s,_=score(c); hist.append([d,s])
d,c=actions_at(n-1)
finish('actions',"Score > 0 : contexte plus favorable à l'achat d'actions ; < 0 : plus favorable à l'allègement.",hist,c,d,
 "Douze composantes notées de −100 à +100, puis pondérées (total 100 %). Vagues d'Elliott (15 %) : moyenne des lectures du CAC 40, du S&P 500 et du MSCI World selon ta règle, zones vertes d'entrée : fin de vague 2, fin de vague 4, vague C ; zones rouges (aucune entrée) : vagues 1, 3, 5, A et B. Retracement de Fibonacci du plus bas historique (base) au plus haut historique (ATH) sur les corps des bougies (15 %, moyenne des trois indices) : plus le cours est bas dans le retracement, plus la note pousse à l'achat ; négative près de l'ATH. "+CH.TXT_CRIT+" (moyennes des trois indices). Les autres composantes gardent leurs proportions sur les 40 % restants : tendance et momentum (RSI 6 %, MACD 6 %, moyenne mobile 40 semaines 6 %) sur les clôtures hebdomadaires confirmées des trois indices ; distance au plus haut sur 52 semaines (4 %), selon ta règle de ne pas entrer au plus haut ; valorisation par le CAPE du S&P 500 classé sur tout son historique depuis 1871 (6 %) ; VIX (4 %) et CNN Fear & Greed (4 %), lus de façon contrarienne modérée ; variation des taux à 10 ans US et OAT sur 3 mois (4 %). Lectures automatiques (Elliott et Fibonacci sur les corps des bougies, structure de la Charte graphique sur les mèches) : approximation qui peut différer de ton indicateur TradingView. Historique : une valeur par semaine clôturée sur 52 semaines.",
 [['Yahoo Finance (indices)','https://finance.yahoo.com/quote/%5EGSPC/history/'],['multpl / R. Shiller (CAPE)','https://www.multpl.com/shiller-pe/table/by-month'],['FRED (VIX, DGS10)','https://fred.stlouisfed.org/series/VIXCLS'],['BCE (OAT 10 ans)','https://data.ecb.europa.eu/data/datasets/IRS'],['CNN Fear & Greed','https://edition.cnn.com/markets/fear-and-greed']])

# ================= CRYPTO =================
k=json.load(open(B+'crypto/binance_BTCUSDT_1w.json')); nowms=NOW.timestamp()*1000
kc=[x for x in k if x[6]<nowms]
bd=[D.datetime.fromtimestamp(x[6]/1000,D.timezone.utc).date().isoformat() for x in kc]   # date de clôture (dimanche)
bc=[float(x[4]) for x in kc]; bo=[float(x[1]) for x in kc]; BELL={}
BHL={d:(float(x[2]),float(x[3])) for d,x in zip(bd,kc)}; BCH={}
def cha_b(j):
    if j not in BCH: BCH[j]=CH.analyse(bc[:j+1],bd[:j+1],bo[:j+1],BHL,syms=['BITSTAMP:BTCUSD','BTC'],manual=(j==len(bc)-1))
    return BCH[j]
def ell_b(j):
    if j not in BELL: BELL[j]=E.analyse(bo[:j+1],bc[:j+1])
    return BELL[j]
BFIB={}; BPRE=FB.prefix('BTC-USD',bd[0],bc[0])   # historique Yahoo BTC-USD antérieur à Binance (2017)
def fib_b(j):
    if j not in BFIB: BFIB[j]=FB.analyse(bo[:j+1],bc[:j+1],bd[:j+1],BPRE)
    return BFIB[j]
br=rsi(bc); bm,bs,bh=macd(bc); bmm=sma(bc,50)
cm=[(x['time'][:10],float(x['PriceUSD'])) for x in json.load(open(B+'crypto/coinmetrics_btc_daily.json')) if x.get('PriceUSD')]
cmd=[x[0] for x in cm]; cmv=[x[1] for x in cm]
fng=sorted([[D.datetime.fromtimestamp(int(x['timestamp']),D.timezone.utc).date().isoformat(),float(x['value'])] for x in json.load(open(B+'crypto/alternative_fng.json'))['data']])
def crypto_at(j):
    d=bd[j]; comps=[E.comp(ell_b(j),W_EL),FB.comp(fib_b(j),W_FI)]
    comps.append({'nom':'RSI 14 hebdo BTC','poids':.15,'valeur':f"{br[j]:.1f}".replace('.',','),'note':r_rsi(br[j]),'regle':'(RSI − 50) / 20 × 100'})
    comps.append({'nom':'MACD 12/26/9 hebdo BTC','poids':.15,'valeur':f"{bm[j]:,.0f} / signal {bs[j]:,.0f}".replace(',',' '),'note':r_macd(bm[j],bs[j],bh[j],bh[j-1],bh,j),'regle':K.RULE_MACD})
    x=(bc[j]/bmm[j]-1)*100
    comps.append({'nom':'Position / moyenne mobile 50 semaines','poids':.20,'valeur':f"{x:+.1f} %".replace('.',','),'note':r_mm(x,20),'regle':'±20 % → ±100 (garde-fou « couteau qui tombe »)'})
    mo=(bc[j]/bc[j-13]-1)*100
    comps.append({'nom':'Momentum 13 semaines','poids':.15,'valeur':f"{mo:+.1f} %".replace('.',','),'note':r_mm(mo,30),'regle':'±30 % → ±100'})
    i=bisect.bisect_right(cmd,d)-1; dd=(cmv[i]/max(cmv[:i+1])-1)*100
    comps.append({'nom':'Écart au record historique (contrarien)','poids':.15,'valeur':f"{dd:.1f} %".replace('.',','),'note':r_dd_crypto(dd),'regle':'au record → −80 ; −30 % → 0 ; −60 % et au-delà → +80'})
    f=asof(fng,d)
    comps.append({'nom':'Fear & Greed alternative.me (contrarien)','poids':.20,'valeur':f"{f[1]:.0f}",'note':r_contra(f[1]),'regle':'(50 − indice) × 2'})
    for x in comps[2:]: x['poids']=round(x['poids']*SC,4)
    comps[2:2]=[CH.comp(cha_b(j),W_CH),CH.comp_div(cha_b(j),W_DV)]
    bcci=globals().setdefault('_btc_cci', K.cci20(bo, bc))
    K.add_cci(comps, bcci[j])
    return d,comps
n=len(bc); hist=[]
for j in range(n-52,n):
    d,c=crypto_at(j); s,_=score(c); hist.append([d,s])
d,c=crypto_at(n-1)
finish('crypto',"Score > 0 : contexte plus favorable à l'achat de BTC ; < 0 : plus favorable à la prise de bénéfices ou à l'attente.",hist,c,d,
 "Dix composantes notées de −100 à +100. Vagues d'Elliott du BTC (15 %) selon ta règle : zones vertes d'entrée : fin de vague 2, fin de vague 4, vague C ; zones rouges (aucune entrée) : vagues 1, 3, 5, A et B. Retracement de Fibonacci du BTC du plus bas historique (base) au plus haut historique (ATH) sur les corps des bougies (15 %) : plus le cours est bas dans le retracement, plus la note pousse à l'achat ; négative près de l'ATH. Historique du BTC complété avant 2017 par Yahoo Finance (BTC-USD, depuis 2014). "+CH.TXT_CRIT+". Les autres gardent leurs proportions sur les 40 % restants : la tendance pèse 26 % (RSI 6 %, MACD 6 %, moyenne mobile 50 semaines 8 %, momentum 13 semaines 6 %) pour ne pas « acheter un couteau qui tombe » ; la lecture contrarienne modérée pèse 14 % : écart au record (6 %) et Fear & Greed (8 %), où la peur extrême compte en faveur de l'achat et l'euphorie en faveur de la vente. Lectures automatiques sur les bougies hebdomadaires Binance (Elliott et Fibonacci sur les corps, structure de la Charte graphique sur les mèches) : approximation qui peut différer de ton indicateur TradingView. Bougies BTC/USDT Binance clôturées (le dimanche à minuit UTC) ; record calculé sur le prix de référence CoinMetrics. Historique : 52 semaines clôturées.",
 [['Binance BTCUSDT 1w','https://www.binance.com/fr/trade/BTC_USDT'],['CoinMetrics','https://coinmetrics.io/community-network-data/'],['alternative.me','https://alternative.me/crypto/fear-and-greed-index/']])

# ================= IMMOBILIER =================
q=sorted((a,float(b)) for a,b in re.findall(r'TIME_PERIOD="([^"]+)" OBS_VALUE="([^"]+)"',open(B+'insee_010567059_ipla_fm_cvs.xml').read()))
qd=dict(q); yoy=[]
for p,v in q:
    y,qq=p.split('-');pv=f"{int(y)-1}-{qq}"
    if pv in qd: yoy.append([f"{y}-{ {'Q1':'03','Q2':'06','Q3':'09','Q4':'12'}[qq]}",(v/qd[pv]-1)*100,p])
rates=[[x['TIME_PERIOD'],float(x['OBS_VALUE'])] for x in csv.DictReader(open(B+'ecb_M.FR.B.A2C.P.R.A.2250.EUR.N.csv'))]
T=DASH['trends'];AK=["achat immobilier","acheter immobilier","acheter maison","acheter appartement"];VK=["vente immobilier","vendre immobilier","estimation immobilière","agence immobilière"]
wk=[(dd,i) for i,dd in enumerate(T['dates']) if not T['partial'][i]]
share=[[dd,sum(T['terms'][k][i] for k in AK)/(sum(T['terms'][k][i] for k in AK)+sum(T['terms'][k][i] for k in VK))*100] for dd,i in wk]
sent=IND['immobilier']['series']
def immo_at(k):
    d=share[k][0]; ym=d[:7]; comps=[]
    py=asof([[a,b] for a,b,_ in yoy],ym)
    comps.append({'nom':'Momentum des prix (Notaires-INSEE sur 1 an)','poids':.25,'valeur':f"{py[1]:+.1f} % ({[x[2] for x in yoy if x[0]==py[0]][0]})".replace('.',',').replace('-Q',' T'),'note':r_mm(py[1],5),'regle':'±5 % sur un an → ±100'})
    rt=asof(rates,ym); pr=prank([x[1] for x in rates if x[0]<=rt[0]],rt[1])
    comps.append({'nom':'Niveau des taux de crédit (percentile depuis 2000)','poids':.20,'valeur':f"{rt[1]:.2f} % · {pr:.0f}ᵉ pct".replace('.',','),'note':r_pct_inv(pr),'regle':'(50 − percentile) × 2 : taux bas = favorable'})
    r0=asof(rates,(D.date.fromisoformat(rt[0]+'-01')-D.timedelta(days=170)).isoformat()[:7]); dr=rt[1]-r0[1]
    comps.append({'nom':'Tendance des taux sur 6 mois','poids':.20,'valeur':f"{dr:+.2f} pt".replace('.',','),'note':clip(-dr/0.5*100),'regle':'baisse de 0,5 pt → +100 ; hausse de 0,5 pt → −100'})
    pt=prank([x[1] for x in share[:k+1]],share[k][1]) if k>=12 else None
    comps.append({'nom':'Ratio achat/vente Google Trends (percentile 12 mois)','poids':.15,'valeur':f"{share[k][1]:.1f} % achat".replace('.',',') if pt is not None else 'historique < 13 sem.','note':clip((pt-50)*2) if pt is not None else None,'regle':'(percentile − 50) × 2 : demande d\'achat en hausse = favorable'})
    g=asof(sent,d)
    comps.append({'nom':'Sentiment immobilier APEX (contrarien)','poids':.20,'valeur':f"{g[1]:.0f}" if g else 'n.d.','note':r_contra(g[1]) if g else None,'regle':'(50 − indice) × 2'})
    return d,comps
hist=[]
for k in range(len(share)):
    d,c=immo_at(k); s,_=score(c); hist.append([d,s])
d,c=immo_at(len(share)-1)
finish('immobilier',"Score > 0 : contexte plus favorable à un achat immobilier ; < 0 : plus favorable à attendre ou à vendre.",hist,c,d,
 "Cinq composantes notées de −100 à +100 : momentum des prix sur un an (25 %), niveau des taux de crédit classé depuis 2000 (20 %), tendance des taux sur 6 mois (20 %), ratio achat/vente Google Trends classé sur 12 mois (15 %) et sentiment immobilier APEX lu de façon contrarienne (20 %). À chaque date, on retient la dernière valeur publiée (taux mensuel, prix trimestriel). Les 13 premières semaines de l'historique sont calculées sans Google Trends, puis le score est renormalisé sur les composantes disponibles. Pas de critère Elliott ici : l'immobilier n'a pas de cours hebdomadaire négocié.",
 [['INSEE / Notaires','https://www.insee.fr/fr/statistiques/serie/010567059'],['Banque de France (MIR)','https://data.ecb.europa.eu/data/datasets/MIR/MIR.M.FR.B.A2C.P.R.A.2250.EUR.N'],['Google Trends','https://trends.google.com/trends/explore?date=today%2012-m&geo=FR']])

# ================= LIQUIDITÉS =================
L=TABS['liquidites']
estr=[[x['TIME_PERIOD'],float(x['OBS_VALUE'])] for x in csv.DictReader(open(B+'liquidites/ecb_EST_B.EU000A2X2A25.WT.csv'))]
dfr=[[x['TIME_PERIOD'],float(x['OBS_VALUE'])] for x in csv.DictReader(open(B+'liquidites/ecb_FM_D.U2.EUR.4F.KR.DFR.LEV.csv'))]
ipc=dict(L['ipc']['series']); estm=L['bce']['estr_m']
real=[[m,v-ipc[m]] for m,v in estm if m in ipc]
sentL=IND['liquidites']['series']
def liq_at(d):
    comps=[]
    rr=asof(real,d[:7])
    comps.append({'nom':'Rendement réel du cash (€STR − inflation)','poids':.30,'valeur':f"{rr[1]:+.2f}".replace('.',',')+f" pt ({MO[int(rr[0][5:])-1]} {rr[0][:4]})",'note':r_mm(rr[1],1.5),'regle':'±1,5 pt → ±100 : rendement réel positif = cash attractif'})
    e=asof(estr,d)
    comps.append({'nom':'Niveau de l\'€STR (rémunération du monétaire)','poids':.20,'valeur':f"{e[1]:.3f} %".replace('.',','),'note':clip((e[1]-1.5)/1.5*100),'regle':'(€STR − 1,5) / 1,5 × 100 : 3 % → +100, 0 % → −100'})
    f0=asof(dfr,(D.date.fromisoformat(d)-D.timedelta(days=182)).isoformat()); f1=asof(dfr,d); df=f1[1]-f0[1]
    comps.append({'nom':'Tendance du taux de dépôt BCE sur 6 mois','poids':.20,'valeur':f"{df:+.2f} pt ({f1[1]:.2f} %)".replace('.',','),'note':clip(df/0.5*100),'regle':'hausse de 0,5 pt → +100 ; baisse de 0,5 pt → −100'})
    g=asof(sentL,d)
    comps.append({'nom':'Appétit pour le risque APEX (lecture inverse)','poids':.30,'valeur':f"{g[1]:.0f}" if g else 'n.d.','note':clip((g[1]-50)*2) if g else None,'regle':'(indice − 50) × 2 : euphorie sur le risque = renforcer le cash'})
    return comps
dates=[x[0] for x in sentL]; hist=[]
for d in dates:
    s,_=score(liq_at(d)); hist.append([d,s])
c=liq_at(dates[-1])
finish('liquidites',"Score > 0 : renforcer le cash et le monétaire ; < 0 : alléger le cash au profit des actifs risqués.",hist,c,dates[-1],
 "Quatre composantes notées de −100 à +100 : rendement réel du cash, soit €STR moyen − inflation INSEE (30 %) ; niveau de l'€STR (20 %) ; tendance du taux de dépôt de la BCE sur 6 mois (20 %) ; appétit pour le risque APEX lu à l'inverse (30 %), car une euphorie sur les actifs risqués plaide pour renforcer le cash et une peur extrême pour l'alléger. Historique : une valeur par semaine sur 52 semaines. Pas de critère Elliott ici : le cash n'a pas de cours hebdomadaire.",
 [['BCE (€STR, taux de dépôt)','https://data.ecb.europa.eu/data/datasets/EST/EST.B.EU000A2X2A25.WT'],['INSEE (IPC)','https://www.insee.fr/fr/statistiques/serie/011814632']])

json.dump(out,open(B+'achatvente.json','w'),ensure_ascii=False)
for k,v in out.items():
    print(k,v['score'],v['label'],v['date'],'moy',v['avg'],'min',v['min'],'max',v['max'],'manque',v['missing'])
    for c in v['components']: print('   ',c['nom'][:48].ljust(48),c['valeur'],'note',c['note'],'poids',c['poids'],'contrib',c['contrib'])
