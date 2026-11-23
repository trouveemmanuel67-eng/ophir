"""Colonne INDICATEUR : jauge « Sentiment de marché, 1 an » par onglet -> data/indicateur.json
Toutes les valeurs proviennent des fichiers bruts de data/. Rang percentile : 100*(nb<v + 0,5*nb==v)/n."""
import json, csv, re, os, datetime as D, bisect
B='/workspace/invest/patrimoine-dashboard/data/'
TODAY=D.date.today()
def mtime(p): return D.datetime.fromtimestamp(os.path.getmtime(B+p)).strftime('%Y-%m-%d %H:%M')
def prank(hist,v):
    n=len(hist); 
    return 100*(sum(1 for x in hist if x<v)+0.5*sum(1 for x in hist if x==v))/n if n else None
def label(v):
    return 'Peur extrême' if v<25 else 'Peur' if v<45 else 'Neutre' if v<=55 else 'Avidité' if v<=75 else 'Euphorie'
def summary(series):
    """series [[date,val]] triée ; fenêtre 1 an glissant à partir de la dernière date"""
    last=D.date.fromisoformat(series[-1][0]); start=(last-D.timedelta(days=365)).isoformat()
    s=[x for x in series if x[0]>start]
    vals=[x[1] for x in s]; mn=min(s,key=lambda x:x[1]); mx=max(s,key=lambda x:x[1])
    return {'value':round(s[-1][1],1),'date':s[-1][0],'label':label(s[-1][1]),'avg':round(sum(vals)/len(vals),1),
            'min':[mn[0],round(mn[1],1)],'max':[mx[0],round(mx[1],1)],'n':len(s),'series':[[d,round(v,1)] for d,v in s]}
def asof(series,d):
    """dernière valeur dont la date ≤ d (séries [[date,val]] triées)"""
    keys=[x[0] for x in series]; i=bisect.bisect_right(keys,d)-1
    return series[i] if i>=0 else None
MO=['janv.','févr.','mars','avr.','mai','juin','juil.','août','sept.','oct.','nov.','déc.']
def fr(d):
    p=d.split('-')
    if len(p)==3 and p[1].startswith('Q'): return 'T'+p[1][1]+' '+p[0]
    if len(p)==2 and p[1].startswith('Q'): return 'T'+p[1][1]+' '+p[0]
    if len(p)==2: return MO[int(p[1])-1]+' '+p[0]
    return f"{int(p[2])} {MO[int(p[1])-1]} {p[0]}"
out={}

# ---------- CRYPTO : Fear & Greed alternative.me ----------
f=json.load(open(B+'indicateur/alternative_fng_400.json'))['data']
s=sorted([[D.datetime.fromtimestamp(int(x['timestamp']),D.timezone.utc).date().isoformat(),float(x['value'])] for x in f])
out['crypto']={**summary(s),'official':True,'title':'Crypto Fear & Greed Index',
  'source':{'name':'alternative.me','url':'https://alternative.me/crypto/fear-and-greed-index/','api':'https://api.alternative.me/fng/?limit=400','retrieved':mtime('indicateur/alternative_fng_400.json')},
  'components':[],'missing':[],
  'method':"Indice officiel d'alternative.me, repris tel quel (valeur quotidienne de 0 à 100). D'après l'éditeur, il combine la volatilité (25 %), le momentum et les volumes (25 %), les réseaux sociaux (15 %), la dominance BTC (10 %) et Google Trends (10 %) ; la part « sondages » est suspendue. Fenêtre : 365 derniers jours."}

# ---------- ACTIONS : CNN Fear & Greed ----------
c=json.load(open(B+'indicateur/cnn_fng.json'))
h=c['fear_and_greed_historical']['data']
s={}
for x in h: s[D.datetime.fromtimestamp(x['x']/1000,D.timezone.utc).date().isoformat()]=float(x['y'])
s=sorted([[k,v] for k,v in s.items()])
sub=[('market_momentum_sp500','Momentum S&P 500 (vs moyenne 125 j)'),('market_volatility_vix','Volatilité (VIX vs moyenne 50 j)'),('safe_haven_demand','Demande de valeurs refuges (actions vs obligations)')]
out['actions']={**summary(s),'official':True,'title':'CNN Fear & Greed Index (marché actions US)',
  'source':{'name':'CNN Business','url':'https://edition.cnn.com/markets/fear-and-greed','api':'https://production.dataviz.cnn.io/index/fearandgreed/graphdata/2025-10-01','retrieved':mtime('indicateur/cnn_fng.json')},
  'components':[{'name':n,'weight':None,'value':round(c[k]['score'],1),'date':D.datetime.fromtimestamp(c[k]['timestamp']/1000,D.timezone.utc).date().isoformat()} for k,n in sub],
  'cnn_all':{k:round(c[k]['score'],1) for k in c if k not in('fear_and_greed','fear_and_greed_historical')},
  'missing':[],
  'method':"Indice officiel de CNN, repris tel quel. Il fait la moyenne à poids égaux de 7 sous-indicateurs du marché américain : momentum du S&P 500, nombre de plus hauts et plus bas à 52 semaines, ampleur du marché (McClellan), ratio put/call, VIX, demande d'obligations à haut rendement et demande de valeurs refuges. Les 3 petites barres affichent trois de ces sous-indicateurs, notés par CNN. Le CAC 40 n'entre pas dans cet indice. Fenêtre : 365 derniers jours."}

# ---------- IMMOBILIER : composite APEX ----------
dash=json.load(open(B+'dashboard_data.json'))
T=dash['trends']; AK=["achat immobilier","acheter immobilier","acheter maison","acheter appartement"]; VK=["vente immobilier","vendre immobilier","estimation immobilière","agence immobilière"]
weeks=[(d,i) for i,d in enumerate(T['dates']) if not T['partial'][i]]
share=[[d,sum(T['terms'][k][i] for k in AK)/(sum(T['terms'][k][i] for k in AK)+sum(T['terms'][k][i] for k in VK))*100] for d,i in weeks]
rates=[[x[0],x[1]] for x in dash['taux']['series']]          # BdF fixe >10 ans, mensuel (2001 →)
r=list(csv.DictReader(open(B+'ecb_M.FR.B.A2C.P.R.A.2250.EUR.N.csv')))
rates_all=[[x['TIME_PERIOD'],float(x['OBS_VALUE'])] for x in r]   # 2000 →
s_ins=open(B+'insee_010567059_ipla_fm_cvs.xml').read()
q=sorted((a,float(b)) for a,b in re.findall(r'TIME_PERIOD="([^"]+)" OBS_VALUE="([^"]+)"',s_ins))
qd=dict(q)
yoy=[]
for p,v in q:
    y,qq=p.split('-'); prev=f"{int(y)-1}-{qq}"
    if prev in qd: 
        mm={'Q1':'03','Q2':'06','Q3':'09','Q4':'12'}[qq]
        yoy.append([f"{y}-{mm}",(v/qd[prev]-1)*100,p])
sv=[x[1] for x in share]
ser=[];comp_last=None
for k,(d,sh) in enumerate(share):
    ym=d[:7]
    rt=asof(rates_all,ym); py=asof([[a,b] for a,b,_ in yoy],ym)
    s1=prank(sv[:k+1],sh) if k>=12 else None            # au moins 13 semaines d'historique
    s2=100-prank([x[1] for x in rates_all if x[0]<=rt[0]],rt[1])
    s3=prank([x[1] for x in yoy if x[0]<=py[0]],py[1])
    parts=[x for x in (s1,s2,s3) if x is not None]
    ser.append([d,sum(parts)/len(parts)])
    comp_last=(d,sh,s1,rt,s2,py,s3)
d,sh,s1,rt,s2,py,s3=comp_last
pyq=[x for x in yoy if x[0]==py[0]][0][2]
sm=summary(ser)
out['immobilier']={**sm,'official':False,'title':'Sentiment immobilier · indice composite APEX',
  'components':[
   {'name':'Part de l\'achat dans Google Trends (achat contre vente)','weight':1/3,'value':round(s1,1),'detail':f"part achat {sh:.1f} % la semaine du {fr(d)} ; rang parmi les semaines disponibles depuis le {fr(share[0][0])}"},
   {'name':'Taux de crédit immobilier, inversé','weight':1/3,'value':round(s2,1),'detail':f"taux BdF fixe > 10 ans {rt[1]:.2f} % ({fr(rt[0])}) ; 100 − rang depuis {fr(rates_all[0][0])}"},
   {'name':'Momentum des prix (indice Notaires-INSEE sur 1 an)','weight':1/3,'value':round(s3,1),'detail':f"{py[1]:+.1f} % sur 1 an au {fr(pyq)} ; rang depuis {fr(yoy[0][2])}"}],
  'missing':["Les 13 premières semaines de la fenêtre (de novembre 2025 à février 2026) sont calculées sans la composante Google Trends, faute d'historique suffisant pour la classer : la moyenne porte alors sur les 2 autres composantes."],
  'source':{'name':'Calcul APEX · INSEE, Banque de France, Google Trends','url':'https://www.insee.fr/fr/statistiques/serie/010567059','retrieved':dash['generated']},
  'method':"Indice composite APEX, pas un indice officiel. Chaque semaine, trois sous-scores de 0 à 100 sont calculés par rang percentile, sans regarder les données futures : (1) part de l'achat dans les recherches Google Trends achat + vente, classée parmi les semaines disponibles (12 mois seulement, d'où un rang relatif à l'année) ; (2) taux moyen des crédits nouveaux à l'habitat à taux fixe > 10 ans (Banque de France), inversé (taux bas = euphorie), classé depuis 2000 ; (3) variation sur un an de l'indice Notaires-INSEE des prix des logements anciens, classée depuis 1997. Chaque composante pèse 1/3. On retient la dernière valeur publiée à la date de chaque semaine (taux mensuel, prix trimestriel)."}

# ---------- LIQUIDITÉS : appétit pour le risque / attrait du cash ----------
tabs=json.load(open(B+'tabs_data.json'))
L=tabs['liquidites']
estr=L['bce']['estr_m']; ipc=dict(L['ipc']['series'])
real=[[m,v-ipc[m]] for m,v in estr if m in ipc]       # rendement réel du cash, mensuel (oct. 2019 →)
vix=[[d,v] for d,v in tabs['actions']['vix']['weekly']]
dxy=[[d,v] for d,v in L['fx']['dxy_w']]
dxy13=[[dxy[i][0],(dxy[i][1]/dxy[i-13][1]-1)*100] for i in range(13,len(dxy))]
ser=[]; last=None
for d,vv in vix:
    if d<'2025-01-01': continue
    rr=asof(real,d[:7]); dx=asof(dxy13,d)
    lo=(D.date.fromisoformat(d)-D.timedelta(days=5*365)).isoformat()
    s_v=100-prank([x[1] for x in vix if lo<x[0]<=d],vv)
    s_r=100-prank([x[1] for x in real if x[0]<=rr[0]],rr[1]) if rr else None
    s_d=100-prank([x[1] for x in dxy13 if lo<x[0]<=dx[0]],dx[1]) if dx else None
    parts=[x for x in (s_r,s_d,s_v) if x is not None]
    ser.append([d,sum(parts)/len(parts)]); last=(d,rr,s_r,dx,s_d,vv,s_v,len(parts))
d,rr,s_r,dx,s_d,vv,s_v,np_=last
sm=summary(ser)
out['liquidites']={**sm,'official':False,'title':'Appétit pour le risque / attrait du cash · indice composite APEX',
  'components':[
   {'name':'Rendement réel du cash (€STR − inflation), inversé','weight':1/3,'value':round(s_r,1),'detail':f"€STR moyen − IPC sur 1 an = {rr[1]:+.2f} pt ({fr(rr[0])}) ; 100 − rang depuis {fr(real[0][0])}"},
   {'name':'Dollar Index (DXY), variation sur 13 semaines, inversée','weight':1/3,'value':round(s_d,1),'detail':f"{dx[1]:+.2f} % sur 13 semaines au {fr(dx[0])} ; 100 − rang sur 5 ans"},
   {'name':'VIX, inversé','weight':1/3,'value':round(s_v,1),'detail':f"VIX {vv:.2f} au {fr(d)} ; 100 − rang sur 5 ans"}],
  'missing':[] if np_==3 else ['Une composante manquait à la dernière date : la moyenne porte sur les composantes disponibles.'],
  'source':{'name':'Calcul APEX · BCE, INSEE, Yahoo Finance (ICE), FRED','url':'https://data.ecb.europa.eu/data/datasets/EST/EST.B.EU000A2X2A25.WT','retrieved':tabs['generated']},
  'method':"Indice composite APEX, pas un indice officiel. Il mesure l'appétit pour le risque par opposition à l'attrait du cash : 0 = le cash est très attractif et les marchés sont en mode refuge (peur), 100 = le cash rapporte peu en réel et les marchés recherchent le risque (euphorie). Trois sous-scores de 0 à 100, chacun de poids 1/3, sont calculés chaque semaine par rang percentile sans données futures : (1) rendement réel du cash = €STR moyen du mois − glissement annuel de l'IPC INSEE, inversé, classé depuis octobre 2019 (début de l'€STR) ; (2) variation du Dollar Index sur 13 semaines, inversée (un dollar qui monte vite traduit une recherche de refuge), classée sur 5 ans ; (3) VIX, inversé, classé sur 5 ans. On retient la dernière valeur publiée à chaque date (inflation mensuelle, donc avec un décalage d'environ un mois)."}

for g in out.values():   # décimales à la française dans les textes de détail
    for c in g['components']:
        if 'detail' in c: c['detail']=re.sub(r'(\d)\.(\d)',r'\1,\2',c['detail'])
json.dump(out,open(B+'indicateur.json','w'),ensure_ascii=False)
for k,v in out.items():
    print(k,v['value'],v['label'],v['date'],'moy',v['avg'],'min',v['min'],'max',v['max'],'n',v['n'],[ (c['name'][:25],c['value']) for c in v['components']])
