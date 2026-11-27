"""Onglet OBLIGATIONS -> data/obligations.json : graphiques, sentiment (0-100), ACHAT / VENTE (−100…+100),
segments (sentiment + achat/vente + liste ETF UCITS). Indices composites APEX, non officiels. Bougies hebdo clôturées uniquement."""
import os as _os
_APEX_ROOT = _os.path.abspath(_os.environ.get('APEX_ROOT') or _os.path.join(_os.path.dirname(__file__), '..'))
import json, sys as _s; _s.path.insert(0,_APEX_ROOT + '/src'); import revolut_rules as RV; import json, csv, os, math, bisect, statistics as st, datetime as D, re
from zoneinfo import ZoneInfo
import sys; sys.path.insert(0,os.path.dirname(os.path.abspath(__file__))); import elliott as E, fibo as FB, charte as CH, ind_core as K
B=_APEX_ROOT + '/data/obligations/'
NOW=D.datetime.now(ZoneInfo('Europe/Paris')); TODAY=NOW.date()
clip=lambda x:max(-100.0,min(100.0,x))
def mt(p): return D.datetime.fromtimestamp(os.path.getmtime(B+p),ZoneInfo('Europe/Paris')).strftime('%Y-%m-%d %H:%M')
def prank(h,v):
    h=[x for x in h if x is not None]
    return None if v is None or len(h)<20 else 100*(sum(1 for x in h if x<v)+0.5*sum(1 for x in h if x==v))/len(h)
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
def sma(v,n): return [sum(v[i-n+1:i+1])/n if i>=n-1 else None for i in range(len(v))]
def r_macd(m,s,h,hp,hist=None,i=None): return K.r_macd(m,s,h,hp,hist,i)
def r_dd(dd):   # obligations : pas d'entrée au plus haut, bandes resserrées (actif moins volatil)
    if dd>=-1: return -40.0
    if dd>=-8: return -40+(-1-dd)/7*100
    if dd>=-20: return 60.0
    return max(0.0,60-(-20-dd)/20*60)
lab_s=lambda v:'Peur extrême' if v<25 else 'Peur' if v<45 else 'Neutre' if v<=55 else 'Avidité' if v<=75 else 'Euphorie'
lab_av=lambda s:'Vente forte' if s<=-60 else 'Vente' if s<=-20 else 'Neutre' if s<20 else 'Achat' if s<60 else 'Achat fort'
f1=lambda x,n=1:f"{x:.{n}f}".replace('.',',')
fs=lambda x,n=1:f"{x:+.{n}f}".replace('.',',')
def fred(s):
    r=list(csv.reader(open(B+f'fred_{s}.csv')))[1:]
    return [[a,float(b)] for a,b in r if b not in('','.')]
def ecb(f):
    return [[r['TIME_PERIOD'],float(r['OBS_VALUE'])] for r in csv.DictReader(open(B+f)) if r['OBS_VALUE']]
def asof(series,d):
    keys=[x[0] for x in series];i=bisect.bisect_right(keys,d)-1
    return series[i] if i>=0 else None
def _chart_weekly(j):
    """Accepte le format Yahoo chart (celui qu'écrit fetch_yahoo) ou {weekly: [[date, close], ...]}."""
    if isinstance(j, dict) and j.get('weekly'):
        return j['weekly'], j
    res=((j.get('chart') or {}).get('result') or [None])[0] or {}
    ts=res.get('timestamp') or []
    q=((res.get('indicators') or {}).get('quote') or [{}])[0]
    closes=q.get('close') or []
    weekly=[]
    import datetime as _D
    for t,c in zip(ts, closes):
        if c is None:
            continue
        weekly.append([_D.datetime.utcfromtimestamp(int(t)).strftime('%Y-%m-%d %H:%M:%S'), float(c)])
    meta=res.get('meta') or {}
    return weekly, {'symbol': meta.get('symbol'), 'name': meta.get('shortName') or meta.get('symbol'), 'weekly': weekly}

def weekly(sym):
    fn=f'w_{sym.replace("^","_")}.json'
    raw=json.load(open(B+fn)); pairs,j=_chart_weekly(raw)
    if not j.get('retrieved'):
        j['retrieved']=mt(fn)
    wk={}
    for d0,c0 in pairs:
        d1=D.date.fromisoformat(d0[:10]); fri=d1+D.timedelta(days=(4-d1.weekday())%7) if d1.weekday()<=4 else d1-D.timedelta(days=d1.weekday()-4)
        wk[fri]=c0
    cl=[(f.isoformat(),wk[f]) for f in sorted(wk) if f<TODAY]
    live=[(f.isoformat(),wk[f]) for f in sorted(wk) if f>=TODAY]
    return cl,live,j
def to_weekly(daily,start='2000-01-01'):   # dernière valeur de chaque semaine (vendredi)
    wk={}
    for d,v in daily:
        if d<start: continue
        x=D.date.fromisoformat(d); fri=x+D.timedelta(days=(4-x.weekday())%7) if x.weekday()<=4 else x-D.timedelta(days=x.weekday()-4)
        wk[fri.isoformat()]=v
    return sorted(wk.items())
def monthly(daily,start='2000-01'):
    m={}
    for d,v in daily: m.setdefault(d[:7],[]).append(v)
    return [[k,round(sum(v)/len(v),3)] for k,v in sorted(m.items()) if k>=start]
F={s:fred(s) for s in ['DGS10','DGS2','DGS3MO','DGS30','T10Y2Y','T10Y3M','DFII10','T10YIE','BAMLC0A0CM','BAMLH0A0HYM2','BAMLHE00EHYIOAS','BAMLEMCBPIOAS','DFEDTARU','DFF']}
FR=ecb('ecb_IRS_FR.csv'); DE=ecb('ecb_IRS_DE.csv'); DFR=ecb('ecb_DFR.csv')
W={s:weekly(s) for s in ['TLT','IEF','SHY','AGG','LQD','HYG','TIP','EMB','^MOVE','EUNH.DE','IFRB.AS','EUN5.DE','IS0L.DE','IS0M.DE','XJSE.DE','148070.KS','XCS2.DE','IUSU.DE','IS04.DE','IBCD.DE','XUHY.DE','TIUP.DE','IUS7.DE','IS0P.DE','CBUS.DE']}   # 18/11/2026 : + souverains FR (IFRB) / ES / UK
out={'generated':NOW.strftime('%Y-%m-%d %H:%M')}
# ---------------- graphiques ----------------
us10m=monthly(F['DGS10']); spread=[[m,round(v-dict(DE)[m],3)] for m,v in FR if m in dict(DE)]
ch={'y10':{'fr':[x for x in FR if x[0]>='2000-01'],'de':[x for x in DE if x[0]>='2000-01'],'us':us10m},'spread':[x for x in spread if x[0]>='2000-01'],
    'curve':{'t10y2y':to_weekly(F['T10Y2Y']),'t10y3m':to_weekly(F['T10Y3M'])},'real':{'tips':to_weekly(F['DFII10']),'be':to_weekly(F['T10YIE'])},
    'credit':{k:to_weekly(F[k],'2023-01-01') for k in ['BAMLC0A0CM','BAMLH0A0HYM2','BAMLHE00EHYIOAS','BAMLEMCBPIOAS']},
    'move':[[d,round(v,2)] for d,v in W['^MOVE'][0] if d>='2003-01-01'],
    'policy':{'fed':monthly(F['DFF']),'fed_target':F['DFEDTARU'][-1],'dfr':[[m,v] for m,v in monthly(DFR)]}}
last=lambda s:F[s][-1]
ch['last']={'us10':last('DGS10'),'us2':last('DGS2'),'us3m':last('DGS3MO'),'us30':last('DGS30'),'t10y2y':last('T10Y2Y'),'t10y3m':last('T10Y3M'),'tips':last('DFII10'),'be':last('T10YIE'),
  'ig':last('BAMLC0A0CM'),'hy':last('BAMLH0A0HYM2'),'ehy':last('BAMLHE00EHYIOAS'),'em':last('BAMLEMCBPIOAS'),'fed':last('DFEDTARU'),'dff':last('DFF'),'dfr':DFR[-1],'fr':FR[-1],'de':DE[-1],'spread':spread[-1],
  'move':W['^MOVE'][0][-1]}
def pctl_all(series,v): return round(prank([x[1] for x in series],v),0)
ch['pct']={'spread':pctl_all(spread,spread[-1][1]),'hy':pctl_all(F['BAMLH0A0HYM2'],last('BAMLH0A0HYM2')[1]),'ig':pctl_all(F['BAMLC0A0CM'],last('BAMLC0A0CM')[1])}
inv=[x for x in F['T10Y2Y'] if x[1]<0]; ch['inv_last']=inv[-1][0] if inv else None
ch['retrieved']={'fred':mt('fred_DGS10.csv'),'ecb':mt('ecb_IRS_FR.csv'),'yahoo':W['TLT'][2]['retrieved']}
out['charts']=ch
# ---------------- séries de travail hebdo ----------------
def prep(sym):
    cl,live,j=W[sym]; ds=[d for d,_ in cl]; c=[v for _,v in cl]
    r=rsi(c); m,sg,h=K.macd_series(c); mm=sma(c,40)
    cci=K.cci20(None,c)
    return dict(sym=sym,ds=ds,c=c,r=r,m=m,sg=sg,h=h,mm=mm,cci=cci,live=live,name=j.get('name'),retrieved=j['retrieved'],fpre=FB.prefix(sym,ds[0],c[0]) if ds else None)
P={s:prep(s) for s in W if s!='^MOVE'}
W_EL=.15; W_FI=.15; W_CH=CH.W_CH; W_DV=CH.W_DV; SC=1-W_EL-W_FI-W_CH-W_DV   # 17/11/2026 : Elliott 15 % + Fibonacci 15 % + Charte graphique 20 % + Divergence RSI / MACD weekly 10 %, autres poids ×0,40 (proportions conservées)
def cha(p,i):   # Charte graphique / divergence : clôtures seules -> hauts / bas = corps (clôture précédente / clôture)
    cache=p.setdefault('_cha',{})
    if i not in cache: cache[i]=CH.analyse(p['c'][:i+1],p['ds'][:i+1],None,None,p['r'][:i+1],syms=[p.get('sym')],manual=(i==len(p['c'])-1))
    return cache[i]
def ell(p,i):   # ETF obligataires : clôtures seules -> corps = clôture précédente / clôture
    cache=p.setdefault('_ell',{})
    if i not in cache: cache[i]=E.analyse(None,p['c'][:i+1])
    return cache[i]
def fib(p,i):   # retracement de Fibonacci base → ATH, corps = clôture précédente / clôture (pas d'ouverture enregistrée)
    cache=p.setdefault('_fib',{})
    if i not in cache: cache[i]=FB.analyse(None,p['c'][:i+1],p['ds'][:i+1],p.get('fpre'),sym=p.get('sym') or p.get('tv'),syms=[p.get('tv'),p.get('sym'),p.get('yahoo')])
    return cache[i]
def at(p,d):
    i=bisect.bisect_right(p['ds'],d)-1; return i
mv=W['^MOVE'][0]
def lo5(d): return (D.date.fromisoformat(d)-D.timedelta(days=5*365)).isoformat()
def win(series,d,lo=None): return [v for x,v in series if (lo is None or x>lo) and x<=d]
# séries dérivées pour rangs (marché obligataire US large : TLT, IEF, AGG)
BASK=['TLT','IEF','AGG']
def mom13(p,i): return (p['c'][i]/p['c'][i-13]-1)*100 if i>=13 else None
dates=P['AGG']['ds']
momb=[];gapb=[]
for d in dates:
    xs=[mom13(P[s],at(P[s],d)) for s in BASK]; momb.append([d,sum(xs)/3 if None not in xs else None])
    a=P['AGG'];i=at(a,d); gapb.append([d,(a['c'][i]/a['mm'][i]-1)*100 if a['mm'][i] else None])
hyW=to_weekly(F['BAMLH0A0HYM2'],'2023-01-01'); igW=to_weekly(F['BAMLC0A0CM'],'2023-01-01')
def sent_tab(d):
    comps=[]
    m=asof(momb,d)[1]; comps.append(('Momentum 13 semaines TLT / IEF / AGG (rang 5 ans)',.25,prank(win(momb,d,lo5(d)),m),f"{fs(m)} % en moyenne"))
    v=asof(mv,d); comps.append(('Volatilité obligataire : indice MOVE, inversé (rang 5 ans)',.20,None if not v else 100-prank(win(mv,d,lo5(d)),v[1]),f"MOVE {f1(v[1])}" if v else 'n.d.'))
    h=asof(hyW,d); comps.append(('Spread high yield US (ICE BofA), inversé (rang depuis nov. 2023)',.15,None if not h else (lambda p:None if p is None else 100-p)(prank(win(hyW,d),h[1])),f"{f1(h[1],2)} pt" if h else 'n.d.'))
    g=asof(igW,d); comps.append(('Spread investment grade US (ICE BofA), inversé (rang depuis nov. 2023)',.10,None if not g else (lambda p:None if p is None else 100-p)(prank(win(igW,d),g[1])),f"{f1(g[1],2)} pt" if g else 'n.d.'))
    gp=asof(gapb,d)[1]; comps.append(('Écart AGG / moyenne mobile 40 semaines (rang 5 ans)',.15,prank(win(gapb,d,lo5(d)),gp),f"{fs(gp)} %"))
    rs=[P[s]['r'][at(P[s],d)] for s in BASK]; rr=sum(rs)/3; comps.append(('RSI 14 hebdo moyen TLT / IEF / AGG (valeur brute)',.15,rr,f"RSI {f1(rr)}"))
    av=[(w,v) for _,w,v,_ in comps if v is not None]
    return sum(w*v for w,v in av)/sum(w for w,_ in av), comps
ser=[]; 
for d in dates[-52:]:
    s,_=sent_tab(d); ser.append([d,round(s,1)])
s,comps=sent_tab(dates[-1])
vals=[x[1] for x in ser]
out['ind']={'value':round(s,1),'date':dates[-1],'label':lab_s(s),'avg':round(sum(vals)/len(vals),1),'min':min(ser,key=lambda x:x[1]),'max':max(ser,key=lambda x:x[1]),'n':len(ser),'series':ser,
  'official':False,'title':'Sentiment obligataire · indice composite APEX',
  'components':[{'name':n,'weight':w,'value':None if v is None else round(v,1),'detail':dt} for n,w,v,dt in comps],
  'missing':["Spreads de crédit ICE BofA : FRED ne diffuse plus que les 3 dernières années (depuis nov. 2023), d'où un rang sur cette seule période.","Flux vers les fonds obligataires : pas de source gratuite fiable, composante non utilisée."],
  'source':{'name':'Calcul APEX · Yahoo Finance, FRED (ICE BofA)','url':'https://fred.stlouisfed.org/series/BAMLH0A0HYM2','retrieved':ch['retrieved']['fred']},
  'method':"Indice composite APEX, pas un indice officiel. 0 = peur sur le marché obligataire (prix en baisse, volatilité et spreads élevés), 100 = euphorie (rallye, volatilité et spreads comprimés). Six composantes de 0 à 100, calculées chaque semaine clôturée sans données futures : momentum 13 semaines moyen de TLT, IEF et AGG (25 %) ; indice MOVE inversé (20 %) ; spread high yield US inversé (15 %) ; spread investment grade US inversé (15 % → 10 %) ; écart d'AGG à sa moyenne mobile 40 semaines (15 %) ; RSI 14 hebdo moyen (15 %). Les rangs portent sur 5 ans, sauf les spreads (depuis nov. 2023). Fenêtre : 52 dernières semaines."}
out['ind']['method']=out['ind']['method'].replace('(15 % → 10 %)','(10 %)')
# ---------------- ACHAT / VENTE onglet ----------------
fedt=F['DFEDTARU']
def av_tab(d,sv):
    c=[E.comp_multi([(s_,ell(P[s_],at(P[s_],d))) for s_ in BASK],W_EL),FB.comp_multi([(s_,fib(P[s_],at(P[s_],d))) for s_ in BASK],W_FI)]
    rs=[P[s]['r'][at(P[s],d)] for s in BASK]; rr=sum(rs)/3
    c.append({'nom':'RSI 14 hebdo (moyenne TLT, IEF, AGG)','poids':.15,'valeur':f1(rr),'note':clip((rr-50)/20*100),'regle':'(RSI − 50) / 20 × 100'})
    M=[]
    for s in BASK:
        p=P[s];i=at(p,d); M.append(r_macd(p['m'][i],p['sg'][i],p['h'][i],p['h'][i-1],p['h'],i))
    c.append({'nom':'MACD 12/26/9 hebdo (TLT, IEF, AGG)','poids':.15,'valeur':' · '.join(n+' '+{100:'↑↑',50:'↑',-50:'↓',-100:'↓↓'}.get(x,str(x)) for n,x in zip(BASK,M)),'note':sum(M)/3,'regle':K.RULE_MACD})
    G=[]
    for s in BASK:
        p=P[s];i=at(p,d); G.append((p['c'][i]/p['mm'][i]-1)*100)
    g=sum(G)/3; c.append({'nom':'Écart à la moyenne mobile 40 semaines (moyenne 3 ETF)','poids':.10,'valeur':fs(g)+' %','note':clip(g/5*100),'regle':'±5 % → ±100'})
    t=asof(F['DFII10'],d); c.append({'nom':'Niveau du taux réel 10 ans US (TIPS)','poids':.15,'valeur':f1(t[1],2)+' %','note':clip((t[1]-1.0)/1.5*100),'regle':'taux réel 2,5 % → +100 ; 1 % → 0 ; −0,5 % → −100 (un rendement réel élevé rend les obligations attractives)'})
    sl=asof(F['T10Y2Y'],d); c.append({'nom':'Pente de la courbe US 10 ans − 2 ans','poids':.10,'valeur':fs(sl[1],2)+' pt','note':clip(sl[1]/1.0*100),'regle':'pente +1 pt → +100 ; −1 pt (inversion) → −100 : une courbe pentue rémunère la duration'})
    h=asof(hyW,d); p=prank(win(hyW,d),h[1]) if h else None
    c.append({'nom':'Spread high yield US (rang depuis nov. 2023)','poids':.10,'valeur':(f"{f1(h[1],2)} pt · {p:.0f}ᵉ pct" if p is not None else 'n.d.'),'note':None if p is None else clip((p-50)*2),'regle':'(percentile − 50) × 2 : spread large = crédit mieux rémunéré'})
    f0=asof(fedt,(D.date.fromisoformat(d)-D.timedelta(days=182)).isoformat()); f_=asof(fedt,d); df=f_[1]-f0[1]
    c.append({'nom':'Tendance du taux directeur de la Fed sur 6 mois','poids':.10,'valeur':f"{fs(df,2)} pt ({f1(f_[1],2)} %)",'note':clip(-df/0.5*100),'regle':'baisse de 0,5 pt → +100 ; hausse de 0,5 pt → −100'})
    c.append({'nom':'Sentiment obligataire APEX (lecture contrarienne)','poids':.15,'valeur':f1(sv,0),'note':clip((50-sv)*2),'regle':'(50 − sentiment) × 2'})
    for x in c[2:]: x['poids']=round(x['poids']*SC,4)
    IT=[(s_,cha(P[s_],at(P[s_],d))) for s_ in BASK]; c[2:2]=[CH.comp_multi(IT,W_CH),CH.comp_div_multi(IT,W_DV)]
    ccis=[P[s]['cci'][at(P[s],d)] for s in BASK]
    ccis=[x for x in ccis if x is not None]
    K.add_cci(c, (sum(ccis)/len(ccis) if ccis else None))
    av=[x for x in c if x['note'] is not None]; tw=sum(x['poids'] for x in av)
    for x in c: x['contrib']=round(x['poids']*x['note']/tw,1) if x['note'] is not None else None
    return round(sum(x['poids']*x['note'] for x in av)/tw,1),c
hist=[]
for d,sv in ser:
    a,_=av_tab(d,sv); hist.append([d,a])
a,c=av_tab(dates[-1],s)
for x in c: x['note']=None if x['note'] is None else round(x['note'],1)
out['av']={'score':a,'label':lab_av(a),'date':dates[-1],'sens':"Score > 0 : contexte plus favorable à l'achat d'obligations (allonger la duration) ; < 0 : plus favorable à l'attente ou aux échéances courtes.",
  'components':c,'missing':[x['nom'] for x in c if x['note'] is None and not x.get('facultatif')],'history':hist,'avg':round(sum(x[1] for x in hist)/len(hist),1),'min':min(hist,key=lambda x:x[1]),'max':max(hist,key=lambda x:x[1]),
  'method':"Douze composantes notées de −100 à +100 puis pondérées : vagues d'Elliott de TLT, IEF et AGG selon ta règle (15 %, moyenne des trois : zones vertes d'entrée : fin de vague 2, fin de vague 4, vague C ; zones rouges (aucune entrée) : vagues 1, 3, 5, A et B), retracement de Fibonacci plus bas historique → plus haut historique des mêmes ETF (15 %, moyenne des trois : plus le cours est bas dans le retracement, plus la note pousse à l'achat), "+CH.TXT_CRIT+" (moyennes des trois ETF), technique hebdo des mêmes ETF (RSI 6 %, MACD 6 % avec plafond −50 dès 4 barres d'histogramme positives, CCI 20 facultatif 6 % en zone ±100, moyenne mobile 40 semaines 4 %), niveau du taux réel 10 ans US (6 %), pente 10 − 2 ans (4 %), spread high yield (4 %), tendance du taux de la Fed sur 6 mois (4 %), sentiment obligataire APEX lu de façon contrarienne (6 %). Les vagues, le retracement et la Charte graphique sont lus automatiquement sur les corps des bougies hebdomadaires (clôture précédente → clôture, faute d'ouverture dans les données Yahoo enregistrées) : approximation qui peut différer de ton indicateur TradingView. Bougies hebdomadaires clôturées uniquement ; historique 52 semaines.",
  'sources':[['Yahoo Finance (TLT, IEF, AGG)','https://finance.yahoo.com/quote/AGG/history/'],['FRED (DFII10, T10Y2Y, BAMLH0A0HYM2, DFEDTARU)','https://fred.stlouisfed.org/series/DFII10']]}
json.dump(out,open(_APEX_ROOT + '/data/obligations.json','w'),ensure_ascii=False)
print('sentiment',out['ind']['value'],out['ind']['label'],out['ind']['date'],[(x['name'][:30],x['value']) for x in out['ind']['components']])
print('achat/vente',a,lab_av(a),[(x['nom'][:25],x['valeur'],x['note']) for x in c])
print('last',ch['last'],ch['pct'],'inversion fin',ch['inv_last'])

# ================= SEGMENTS =================
SEG=json.load(open(_APEX_ROOT + '/src/obligations_segments.json'))
# 17/11/2026 · règle Revolut : ETF de référence US (non vendus en UE) remplacés par l'ETF UCITS cité comme doublon dans la proposition validée ;
# segments sans ETF achetable : Corée retirée (taux seuls). France rétablie le 18/11/2026 avec IFRB, à vérifier Revolut/XTB.
PRV={'tcourt':('IUSU.DE','XETR:IUSU','NASDAQ:SHY'),'tlong':('IS04.DE','XETR:IS04','NASDAQ:TLT'),'usig':('IBCD.DE','XETR:IBCD','AMEX:LQD'),'hy':('XUHY.DE','XETR:XUHY','AMEX:HYG'),'infl':('TIUP.DE','XETR:TIUP','AMEX:TIP'),'em':('IUS7.DE','XETR:IUS7','NASDAQ:EMB')}
for _k,(_y,_tv,_old) in PRV.items():
    SEG[_k]=dict(SEG[_k]); SEG[_k]['principal']={'yahoo':_y,'tv':_tv,'old':_old}
for _k in ('kr',): SEG.pop(_k,None)
TVR=json.load(open(B+'tv_search.json')); CAND=json.load(open(B+'candidats.json'))
for _k in list(SEG):
    TVR.setdefault(_k,[]); CAND.setdefault(_k,{})
USX={'NASDAQ','NYSE','AMEX','CBOE'}
yl=lambda s:[x for x in F[s]]
VAL={'tcourt':('Niveau du taux US 2 ans (rang depuis 2000)',F['DGS2'],'2000-01-01'),'tlong':('Niveau du taux US 30 ans (rang depuis 2000)',F['DGS30'],'2000-01-01'),
     'eurgov':('Niveau du Bund 10 ans (rang depuis 2000)',[[m+'-28',v] for m,v in DE],'2000-01-01'),'france':('Niveau de l\'OAT 10 ans (rang depuis 2000)',[[m+'-28',v] for m,v in FR],'2000-01-01'),
     'usig':('Spread investment grade US (rang depuis nov. 2023)',F['BAMLC0A0CM'],'2023-01-01'),'eurig':None,'hy':('Spread high yield US (rang depuis nov. 2023)',F['BAMLH0A0HYM2'],'2023-01-01'),
     'infl':('Niveau du taux réel 10 ans US (rang depuis 2003)',F['DFII10'],'2003-01-01'),'em':('Spread des obligations d\'entreprises émergentes (ICE BofA, rang depuis nov. 2023)',F['BAMLEMCBPIOAS'],'2023-01-01')}
OBP=json.load(open(_APEX_ROOT + '/data/obpays.json'))['countries']
_m=lambda cc:[[m+'-28',v] for m,v in OBP[cc]['y']['10']]
_SRC={'de':'Bund 10 ans, Bundesbank','it':'BTP 10 ans, BCE','jp':'JGB 10 ans, ministère des Finances du Japon','kr':'KTB 10 ans, OCDE','au':'ACGB 10 ans, OCDE',
      'es':'Bonos 10 ans, BCE','gb':'Gilt 10 ans, OCDE','ch':'Confédération 10 ans, OCDE','nl':'DSL 10 ans, BCE','be':'OLO 10 ans, BCE'}
for _k in ('de','it','jp','kr','au','es','gb','ch','nl','be'):
    if _k in OBP and OBP[_k].get('y',{}).get('10'): VAL[_k]=(f"Niveau du taux 10 ans ({_SRC[_k]}, rang depuis 2001)",_m(_k),'2001-01-01')
for _k in list(SEG):
    if _k not in VAL:
        SEG.pop(_k, None)  # univers t322u : pas d'Italie, Japon, etc.
RISK={'de':['Taux : moyen à élevé (toutes échéances de la dette fédérale).','Change : aucun (euro).','Crédit : très faible (République fédérale, notée AAA).'],
 'it':['Taux : moyen à élevé (toutes échéances).','Change : aucun (euro).','Crédit / spread : risque Italie (notation BBB) ; écart BTP − Bund de {spit} pt en {spitm}.'],
 'jp':['Taux : moyen à élevé (toutes échéances).','Change : exposition au yen non couverte (fonds coté en euros sur Xetra, actifs en JPY).','Crédit : faible (État japonais), dette publique très élevée.'],
 'kr':['Taux : élevé (KTB 10 ans).','Change : exposition au won coréen (fonds coté en KRW à Séoul) ; non accessible depuis la plupart des courtiers français.','Crédit : faible (République de Corée).'],
 'au':['Taux : moyen à élevé (toutes échéances).','Change : exposition au dollar australien non couverte (fonds coté en euros sur Xetra, actifs en AUD).','Crédit : très faible (Commonwealth d\'Australie, noté AAA).'],
 'tcourt':['Taux : faible (échéances 1-3 ans).','Change : exposition au dollar, sauf part couverte en EUR.','Crédit : très faible (État américain).'],
 'tlong':['Taux : très élevé (échéances de plus de 20 ans, forte duration).','Change : exposition au dollar, sauf part couverte en EUR.','Crédit : très faible (État américain).'],
 'eurgov':['Taux : moyen à élevé (toutes échéances).','Change : aucun (euro).','Crédit : États de la zone euro, notations hétérogènes (de AAA à BBB).'],
 'france':['Taux : moyen à élevé (toutes échéances).','Change : aucun (euro).','Crédit / spread : risque France ; écart OAT − Bund de {spread} pt en {spm}.'],
'es':['Taux : moyen à élevé (toutes échéances).','Change : aucun (euro).','Crédit / spread : risque Espagne (notation A) ; écart Bonos − Bund de {spes} pt en {spesm}.'],
'gb':['Taux : moyen à élevé (toutes échéances).','Change : part de référence couverte en euro (CBUS) ; le gilt en livre n’est pas l’exposition affichée.','Crédit : État britannique (notation AA).'],
 'usig':['Taux : moyen.','Change : exposition au dollar, sauf part couverte en EUR.','Crédit : entreprises notées investment grade (BBB et mieux).'],
 'eurig':['Taux : moyen.','Change : aucun (euro).','Crédit : entreprises notées investment grade (BBB et mieux).'],
 'hy':['Taux : modéré.','Change : exposition au dollar pour le haut rendement US.','Crédit : élevé, risque de défaut (notations BB et moins).'],
 'infl':['Taux : sensible aux taux réels.','Change : exposition au dollar pour les TIPS (aucune pour les indexées euro).','Crédit : faible (États) ; protège contre une inflation supérieure aux anticipations.'],
 'em':['Taux : moyen à élevé.','Change : dette surtout en dollars ; les fonds en devises locales ajoutent un risque de change émergent.','Crédit : élevé, risque pays et politique.']}
def fxof(n,h):
    n=' '+n.lower()+' '
    if h: return 'couvert'
    if 'local' in n: return 'local'
    if '$' in n or ' usd ' in n or 'u.s.' in n or ' us ' in n or 'treasury' in n: return 'USD'
    if '€' in n or ' eur ' in n or 'euro' in n: return 'EUR'
    return None
LNOTE={'au':"Seule autre part UCITS trouvée sur Xetra ou Euronext (recherche TradingView du {d}) : XETR:X2AE (Xtrackers II Australia Government Bond, autre classe de parts), dont la fiche Yahoo n'indique ni frais ni volume : non classée.",'jp':"Seules les parts couvertes en euros sont proposées en plus de l'ETF de référence (non couvert, exposé au yen).",'it':"Les ETF de la liste sont cotés à Milan (Euronext Milan, en euros) : données Yahoo Finance de la cotation milanaise (suffixe .MI) ; TradingView range ces cotations sous le préfixe EURONEXT. Pour un compte-titres français, vérifier la place proposée par le courtier.",'kr':"Aucun ETF UCITS investi en emprunts d'État coréens n'a été trouvé sur Xetra ou Euronext (recherche TradingView du {d}). L'ETF de référence KOSEF 10Y KTB (KRX:148070) est coté à Séoul en wons : il sert au calcul des indicateurs, il n'est pas proposé à l'achat.",
 'france':"Aucun autre ETF UCITS investi uniquement en dette d'État française n'a été trouvé sur Xetra ou Euronext (recherche TradingView du {d}) : seules existent des parts couvertes en USD ou en GBP du même fonds iShares, non pertinentes pour un investisseur en euros. Alternative : les OAT en direct, cotées sur Euronext Paris."}
def tvp(k,yahoo):
    base=yahoo.split('.')[0]
    for x in TVR.get(k,[]):
        if x.get('symbol')!=base: continue
        pre=x.get('prefix') or x['exchange']
        if '.' not in yahoo and pre in USX: return f"{pre}:{base}",x['description']
        if yahoo.endswith('.DE') and x['exchange']=='XETR': return f"XETR:{base}",x['description']
        if yahoo.endswith('.AS') and x['exchange']=='Euronext Amsterdam': return f"EURONEXT:{base}",x['description']
        if yahoo.endswith('.PA') and x['exchange']=='Euronext Paris': return f"EURONEXT:{base}",x['description']
        if yahoo.endswith('.KS') and x['exchange']=='KRX': return f"KRX:{base}",x['description']
    if yahoo.endswith('.DE'): return f"XETR:{base}",None
    if yahoo.endswith('.AS'): return f"EURONEXT:{base}",None
    return None,None
agg=P['AGG']; eu=P['EUNH.DE']
def rvlist(L,ptv):   # 17/11/2026 · règle Revolut sur la liste (sans repêcher d'autres ETF non vérifiés)
    out=[]
    for x in L:
        if not RV.keep(x['tv']) or x['tv'] not in RV.ACT or x['tv']==ptv: continue   # seulement les ETF déjà suivis dans APEX
        u=RV.rep(x['tv'])
        if u:
            if u['tv']==ptv or any(y['tv']==u['tv'] for y in out): continue
            x={'tv':u['tv'],'yahoo':u['yahoo'],'name':u['nom'],'isin':None,'venue':u['tv'].split(':')[0],'ccy':'EUR','ter':None,'liq':None,'avgvol':None,'years':None,'yield':None,'rating_a':None,
               'hedged':'hedged' in u['nom'].lower(),'fx':None,'dist':None,'retrieved':None,'score':None,'note_revolut':f"{u['old']} non disponible chez Revolut : remplacé par {u['tv']} ({u['revolut']}), non classé (fiche Yahoo non relue)."}
        out.append(x)
    return out
def seg_build(k,cfg):
    ysym=cfg['principal']['yahoo']; p=P[ysym]; ds=p['ds']; c=p['c']; n=len(c); bench=None if ysym in('AGG','EUNH.DE') or cfg.get('bench')=='none' else (eu if '.' in ysym else agg)
    if ysym=='EUNH.DE': bench=agg
    ret=[None]+[c[i]/c[i-1]-1 for i in range(1,n)]
    gap=[(c[i]/p['mm'][i]-1)*100 if p['mm'][i] else None for i in range(n)]
    mo13=[(c[i]/c[i-13]-1)*100 if i>=13 else None for i in range(n)]
    mo26=[(c[i]/c[i-26]-1)*100 if i>=26 else None for i in range(n)]
    bmap=dict(zip(bench['ds'],bench['c'])) if bench else {}
    rs13=[((c[i]/c[i-13])/(bmap[ds[i]]/bmap[ds[i-13]])-1)*100 if i>=13 and ds[i] in bmap and ds[i-13] in bmap else None for i in range(n)]
    dd52=[(c[i]/max(c[max(0,i-51):i+1])-1)*100 for i in range(n)]
    ddath=[(c[i]/max(c[:i+1])-1)*100 for i in range(n)]
    vol=[st.pstdev(ret[i-12:i+1])*math.sqrt(52)*100 if i>=13 else None for i in range(n)]
    val=VAL[k]
    def sent_at(i):
        lo=max(0,i-259); w_=lambda s:[x for x in s[lo:i+1] if x is not None]
        pr=lambda s,v:None if v is None else prank(w_(s),v)
        parts=[p['r'][i],pr(gap,gap[i]),pr(mo26,mo26[i]),pr(rs13,rs13[i]),pr(dd52,dd52[i]),None if vol[i] is None else (lambda q:None if q is None else 100-q)(prank(w_(vol),vol[i]))]
        av=[x for x in parts if x is not None]; return sum(av)/len(av),parts
    def av_at(i,sv):
        d=ds[i]; comps=[E.comp(ell(p,i),W_EL),FB.comp(fib(p,i),W_FI),
         {'nom':'RSI 14 hebdo','poids':.15,'valeur':f1(p['r'][i]),'note':clip((p['r'][i]-50)/20*100),'regle':'(RSI − 50) / 20 × 100'},
         {'nom':'MACD 12/26/9 hebdo','poids':.15,'valeur':K.macd_valeur(p['m'][i],p['sg'][i],p['h'][i],p['h'][i-1],p['h'],i),'note':r_macd(p['m'][i],p['sg'][i],p['h'][i],p['h'][i-1],p['h'],i),'regle':K.RULE_MACD},
         {'nom':'Écart à la moyenne mobile 40 semaines','poids':.15,'valeur':fs(gap[i])+' %','note':clip(gap[i]/5*100),'regle':'±5 % → ±100'},
         {'nom':'Distance au plus haut 52 semaines','poids':.10,'valeur':fs(dd52[i])+' %','note':r_dd(dd52[i]),'regle':"≥ −1 % : −40 (pas d'entrée au plus haut) ; −1 → −8 % : de −40 à +60 ; −8 → −20 % : +60 ; au-delà : retour vers 0"},
         {'nom':'Momentum 13 et 26 semaines','poids':.15,'valeur':f"13 s. {fs(mo13[i])} % · 26 s. {fs(mo26[i])} %",'note':(clip(mo13[i]/5*100)+clip(mo26[i]/8*100))/2,'regle':'moyenne de (13 s. : ±5 % → ±100) et (26 s. : ±8 % → ±100)'}]
        if val:
            hist=[x for x in val[1] if x[0]>=val[2] and x[0]<=d]; v=hist[-1] if hist else None; q=prank([x[1] for x in hist],v[1]) if v else None
            comps.append({'nom':'Valorisation : '+val[0],'poids':.20,'valeur':(f"{f1(v[1],2)} % · {q:.0f}ᵉ pct" if 'Niveau' in val[0] else f"{f1(v[1],2)} pt · {q:.0f}ᵉ pct") if q is not None else 'n.d.','note':None if q is None else clip((q-50)*2),'regle':'(percentile − 50) × 2 : rendement ou spread élevé = point d\'entrée plus attractif'})
        else:
            comps.append({'nom':'Valorisation : spread investment grade euro','poids':.20,'valeur':'non récupéré','note':None,'regle':'série ICE BofA euro IG absente de FRED'})
        comps.append({'nom':'Sentiment du segment (lecture contrarienne)','poids':.10,'valeur':f1(sv,0),'note':clip((50-sv)*2),'regle':'(50 − sentiment) × 2'})
        for x in comps[2:]: x['poids']=round(x['poids']*SC,4)
        comps[2:2]=[CH.comp(cha(p,i),W_CH),CH.comp_div(cha(p,i),W_DV)]
        K.add_cci(comps, p['cci'][i])
        av=[x for x in comps if x['note'] is not None]; tw=sum(x['poids'] for x in av)
        for x in comps: x['contrib']=round(x['poids']*x['note']/tw,1) if x['note'] is not None else None
        return round(sum(x['poids']*x['note'] for x in av)/tw,1),comps
    ss=[];avh=[]
    for i in range(n-52,n):
        sv,_=sent_at(i); ss.append([ds[i],round(sv,1)]); a,_=av_at(i,sv); avh.append([ds[i],a])
    sv,parts=sent_at(n-1); a,comps=av_at(n-1,sv)
    for x in comps: x['note']=None if x['note'] is None else round(x['note'],1)
    names=['RSI 14 hebdo (valeur brute 0-100)','Écart à la moyenne mobile 40 semaines (rang 5 ans)','Momentum 26 semaines (rang 5 ans)',
           f"Force relative vs {'AGG' if bench is agg else 'EUNH (souverains euro)'} sur 13 semaines (rang 5 ans)" if bench else ('Force relative (non applicable : ETF coté en wons, pas de référence comparable)' if cfg.get('bench')=='none' else 'Force relative (non applicable : ETF de référence)'),'Distance au plus haut 52 semaines (rang 5 ans)','Volatilité réalisée 13 semaines, inversée (rang 5 ans)']
    raw=[f"RSI {f1(p['r'][-1])}",f"écart {fs(gap[-1])} %",f"{fs(mo26[-1])} % sur 26 s.",(f"{fs(rs13[-1])} pt" if rs13[-1] is not None else 'n.d.'),f"{fs(dd52[-1])} % sous le plus haut 52 s.",f"{f1(vol[-1])} % annualisée"]
    av_=[x for x in parts if x is not None]; w=1/len(av_)
    athv=max(c); athd=ds[c.index(athv)]
    warn=[]
    if ddath[-1]>=-1: warn.append(f"Proche du plus haut historique ({fs(ddath[-1])} % sous le record de clôture hebdomadaire du {athd}) : risque d'entrée au sommet.")
    elif dd52[-1]>=-1: warn.append(f"Proche du plus haut sur 52 semaines ({fs(dd52[-1])} %) : risque d'entrée au sommet.")
    ptv,pdesc=tvp(k,ysym)
    if cfg['principal'].get('tv'): ptv=cfg['principal']['tv']
    vals=[x[1] for x in ss]
    def _sp(cc):
        s=(OBP.get(cc) or {}).get('spread') or {}
        last=s.get('last') or [None,None]
        return (f1(last[1],2) if last[1] is not None else 'n.d.'), (last[0] or '')
    _es,_esm=_sp('es'); _itv,_itm=_sp('it')
    risks=[r.replace('{spread}',f1(spread[-1][1],2)).replace('{spm}',spread[-1][0]).replace('{spit}',_itv).replace('{spitm}',_itm).replace('{spes}',_es).replace('{spesm}',_esm) for r in RISK.get(k,['Taux : moyen à élevé (toutes échéances).','Crédit : État souverain.'])]
    # ---- liste ETF UCITS ----
    pisin=None
    lst=[]
    for isin,ls in CAND[k].items():
        best=None
        for l in ls:
            f=B+'etf/'+l['yahoo']+'.json'
            if not os.path.exists(f): continue
            j=json.load(open(f)); i=j.get('info') or {}
            if i.get('quoteType')!='ETF': continue
            px=i.get('regularMarketPrice') or i.get('previousClose'); vol_=i.get('averageVolume')
            liq=(px or 0)*(vol_ or 0)
            if best is None or liq>best['liq']: best={**l,'liq':liq,'info':i,'ratings':j.get('ratings'),'retrieved':j['retrieved']}
        if not best: continue
        if best['yahoo']==ysym or (ptv and best['tv']==ptv): pisin=isin; continue
        i=best['info']; ter=i.get('netExpenseRatio')
        if ter is None or not best['liq']: continue
        if any(w in ((i.get('longName') or '')+' '+best['desc']).lower() for w in cfg['exclude']): continue
        ft=i.get('fundInceptionDate') or ((i.get('firstTradeDateMilliseconds') or 0)/1000) or i.get('firstTradeDateEpochUtc'); yrs=(NOW.timestamp()-ft)/31557600 if ft else None
        rt=best['ratings'] or {}; ga=sum((rt.get(x) or 0) for x in ('aaa','aa','a')) if rt else None
        nm=best['desc']; lnm=(i.get('longName') or '')+' '+nm; hedged=('hedged' in lnm.lower() and 'unhedged' not in lnm.lower())
        lst.append({'tv':best['tv'],'yahoo':best['yahoo'],'name':i.get('longName') or nm,'isin':isin,'venue':best['venue'],'ccy':i.get('currency'),'ter':ter,'liq':round(best['liq']),'avgvol':i.get('averageVolume'),
          'years':None if yrs is None else round(yrs,1),'yield':None if not i.get('yield') else round(i['yield']*100,2),'rating_a':None if not ga else min(100,round(ga*100)),'hedged':hedged,
          'fx':fxof(lnm,hedged),'dist':(any(w in lnm.lower() for w in ('dist','(dr) 1d',' 1d',' dis'))) and 'acc' not in lnm.lower(),'retrieved':best['retrieved']})
    for x in lst:
        L=[y for y in lst]
        def rk(vals,v,inv=False):
            h=[a for a in vals if a is not None]
            if v is None or len(h)<2: return None
            r=100*(sum(1 for a in h if a<v)+0.5*(sum(1 for a in h if a==v)-1))/(len(h)-1)
            return 100-r if inv else r
        lparts=[(.40,rk([y['ter'] for y in L],x['ter'],True)),(.40,rk([y['liq'] for y in L],x['liq'])),(.20,rk([y['years'] for y in L],x['years']))]
        av2=[(w_,v) for w_,v in lparts if v is not None]; x['score']=round(sum(w_*v for w_,v in av2)/sum(w_ for w_,_ in av2),1) if av2 else None
    lst=sorted([x for x in lst if x['score'] is not None],key=lambda x:-x['score']); nall=len(lst)
    def base(x):
        t=re.sub(r'\(.*?\)','',x['name'].lower())
        for w in ('accumulating','accum','distributing','acc','dist','dis','1c','1d','2c','usd','eur','shs','-',' d ',' c '):
            t=re.sub(r'(?<![a-z0-9])'+re.escape(w.strip())+r'(?![a-z0-9])','',t)
        return re.sub(r'\s+',' ',t).strip()+('|h' if x['hedged'] else '')
    seenb=set(); ded=[]
    for x in lst:
        b=base(x)
        if b in seenb: continue
        seenb.add(b); ded.append(x)
    lst=ded
    return {'key':k,'nom':cfg['nom'],'sym':ysym,'tv':ptv,'pname':p['name'] or pdesc,'ref_us':bool(cfg['principal'].get('ref')),'date':ds[-1],'close':round(c[-1],2),'first':ds[0],
      'live':({'date':p['live'][-1][0],'close':round(p['live'][-1][1],2)} if p['live'] else None),'ccy':cfg.get('ccy') or ('USD' if '.' not in ysym else 'EUR'),'pays':cfg.get('pays'),
      'sent':{'value':round(sv,1),'label':lab_s(sv),'avg':round(sum(vals)/len(vals),1),'min':min(ss,key=lambda x:x[1]),'max':max(ss,key=lambda x:x[1]),'series':ss,
              'components':[{'name':nm_,'weight':(w if pt is not None else 0),'value':None if pt is None else round(pt,1),'raw':rw} for nm_,pt,rw in zip(names,parts,raw)]},
      'av':{'score':a,'label':lab_av(a),'components':comps,'history':avh,'missing':[x['nom'] for x in comps if x['note'] is None and not x.get('facultatif')],'avg':round(sum(x[1] for x in avh)/len(avh),1),'min':min(avh,key=lambda x:x[1]),'max':max(avh,key=lambda x:x[1])},
      'ath':{'date':athd,'close':round(athv,2),'dd':round(ddath[-1],1)},'dd52':round(dd52[-1],1),'warn':warn,'risks':risks,
      'list':rvlist(lst,ptv)[:5],'note_revolut':(f"{cfg['principal']['old']} (ETF américain, non vendu aux particuliers en Europe) remplacé comme référence par {ptv}, équivalent UCITS disponible chez Revolut, coté en euros : exposition au dollar non couverte, historique plus court." if cfg['principal'].get('old') else None),'list_note':(LNOTE.get(k,'').replace('{d}',NOW.strftime('%d/%m/%Y')) or None),'n_cand':nall,'disponibilite':({'revolut':None,'xtb':None,'badge':'à vérifier Revolut/XTB'} if cfg.get('verif_courtier') else {'revolut':True,'xtb':None}),'url':f'https://finance.yahoo.com/quote/{ysym}/history/','retrieved':p['retrieved']}
out['segments']=[seg_build(k,cfg) for k,cfg in SEG.items()]
for _s in out['segments']:
    cfg=SEG.get(_s['key']) or {}
    if cfg.get('verif_courtier'):
        extra="Disponibilité : à vérifier Revolut/XTB (non confirmé dans la vérification Revolut du 17/11/2026)."
        if _s['key']=='gb':
            extra+=" ETF de référence : iShares Core UK Gilts, part couverte en euro (ISIN IE000BI0GCN3), cotée sur Xetra (CBUS)."
        if _s['key']=='france':
            extra+=" Même fonds que IS0K sur certaines places allemandes (gettex/Stuttgart) ; Yahoo ne fournit pas IS0K.DE, les cours sont ceux d'IFRB.AS (ISIN IE00B7LGZ558). Absent de Revolut au 17/11/2026 (aucun ETF OAT seul trouvé). Alternative : OAT en direct (2056 et 2060 vues chez Revolut)."
        if _s['key']=='es':
            extra+=" iShares Spain Govt Bond UCITS ETF (ISIN IE00B428Z604), coté sur Xetra (IS0P)."
        _s['note_revolut']=((_s.get('note_revolut') or '')+' '+extra).strip()
        _s['list_note']=((_s.get('list_note') or '')+' '+extra).strip()

out['removed_notes']={'kr':"L'ETF KOSEF 10 ans (KRX:148070) n'est pas disponible chez Revolut et aucun équivalent UCITS au comptant n'a été trouvé (17/11/2026) : segment retiré d'APEX, sans note achat / vente. Taux coréens affichés ci-dessous comme repère de marché.",
 'ch':"Aucun ETF obligataire souverain suisse UCITS largement listé sur Xetra n'a été retenu (les ETF iShares SBI Domestic Government sont des fonds de droit suisse, non UCITS). Les taux de la Confédération restent affichés comme repère de marché, sans note APEX.",
 'nl':"L'iShares Netherlands Government Bond UCITS ETF a été liquidé ; aucun successeur UCITS souverain néerlandais largement listé sur Xetra n'a été trouvé. Les Pays-Bas restent couverts par les ETF souverains zone euro (EUNH, XGLE). Taux DSL affichés comme repère de marché, sans note APEX.",
 'be':"L'iShares Belgium Government Bond UCITS ETF a été liquidé ; aucun successeur UCITS souverain belge largement listé sur Xetra n'a été trouvé. La Belgique reste couverte par les ETF souverains zone euro (EUNH, XGLE). Taux OLO affichés comme repère de marché, sans note APEX."}
out['method_seg_sent']="Indice composite APEX, non officiel, calculé sur les clôtures hebdomadaires confirmées de l'ETF de référence du segment, sans données futures : RSI 14, écart à la moyenne mobile 40 semaines, momentum 26 semaines, force relative sur 13 semaines (contre AGG pour les segments en dollars, contre l'ETF souverains euro EUNH pour les segments en euros), distance au plus haut 52 semaines, volatilité 13 semaines inversée. Poids égaux sur les composantes disponibles ; rangs sur 5 ans."
out['method_seg_av']="Indice composite APEX, non officiel. Vagues d'Elliott selon ta règle 15 % (zones vertes d'entrée : fin de vague 2, fin de vague 4, vague C ; zones rouges (aucune entrée) : vagues 1, 3, 5, A et B), retracement de Fibonacci plus bas historique → plus haut historique 15 % (plus le cours est bas dans le retracement, plus la note pousse à l'achat ; négative près de l'ATH ; plafonnée sous la base), "+CH.TXT_CRIT+", RSI hebdo 6 %, MACD hebdo 6 % (plafond −50 dès 4 barres d'histogramme positives), CCI 20 facultatif 6 % en zone ±100, écart à la moyenne mobile 40 semaines 6 % (±5 % → ±100), distance au plus haut 52 semaines 4 % (règle « pas d'entrée au plus haut », bandes adaptées aux obligations), momentum 13 et 26 semaines 6 %, valorisation du segment 8 % (niveau de taux ou de spread classé sur son historique), sentiment du segment lu de façon contrarienne 4 %. Les autres poids gardent leurs proportions d'origine sur les 40 % restants. Score recalculé sur les composantes disponibles. Les vagues, le retracement et la Charte graphique sont lus automatiquement sur les corps des bougies hebdomadaires (clôture précédente → clôture, faute d'ouverture et de mèches dans les données enregistrées) : approximation qui peut différer de ton indicateur TradingView. Pour les ETF obligataires, les figures (tête-épaules, triangles, biseaux, drapeaux, etc.) sont lues sur le cours de l’ETF (relation inverse cours / rendement) et confirmées à la clôture hebdomadaire, selon le dossier ressources/figures_chartistes_obligations_weekly.txt."
out['method_list']="Univers : ETF UCITS cotés sur Xetra ou Euronext trouvés par la recherche TradingView pour chaque segment (mots-clés affichés dans le script), une seule ligne par fonds (code ISIN, cotation la plus liquide retenue), à l'exclusion de l'ETF de référence. Données Yahoo Finance : frais courants, volume moyen sur 3 mois, cours, date de première cotation, rendement distribué sur 12 mois, répartition par notation. Score APEX 0-100 = rang des frais (40 %, plus bas = mieux) + rang de la liquidité (volume moyen × cours, 40 %) + rang de l'ancienneté (20 %). La duration et le rendement à l'échéance ne sont pas affichés : les valeurs fournies par Yahoo sont incohérentes (exemple : 3,6 ans de duration pour TLT, ETF d'obligations à plus de 20 ans) et aucune source gratuite fiable n'a été trouvée."
json.dump(out,open(_APEX_ROOT + '/data/obligations.json','w'),ensure_ascii=False)
for s in out['segments']:
    print(f"\n{s['key']} {s['nom']} | réf {s['tv']} {s['pname']} | {s['date']} | sent {s['sent']['value']} {s['sent']['label']} | AV {s['av']['score']} {s['av']['label']} | ATH {s['ath']['dd']} 52s {s['dd52']} {s['warn']} | candidats {s['n_cand']} manque {s['av']['missing']}")
    for x in s['list']: print('   ',x['tv'],x['score'],'TER',x['ter'],'liq',x['liq'],x['ccy'],'ans',x['years'],'rdt',x['yield'],'≥A',x['rating_a'],'couv' if x['hedged'] else '',x['name'][:60])
