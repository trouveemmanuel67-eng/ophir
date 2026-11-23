"""Onglet Actions · SECTEURS : sentiment Peur/Euphorie (0-100) et compteur ACHAT / VENTE (−100…+100)
pour les 11 secteurs GICS, mesurés par les ETF SPDR Select Sector (Yahoo Finance, clôtures hebdomadaires).
Indices composites APEX, non officiels. Bougies hebdomadaires clôturées uniquement, sans données futures.
-> data/secteurs.json"""
import json, os, math, datetime as D, statistics as st, urllib.parse
from zoneinfo import ZoneInfo
import sys; sys.path.insert(0,os.path.dirname(os.path.abspath(__file__))); import elliott as E, ind_core as K, fibo as FB, charte as CH, revolut_rules as RV
B='/workspace/invest/patrimoine-dashboard/data/'
NOW=D.datetime.now(ZoneInfo('Europe/Paris'))
clip=lambda x:max(-100.0,min(100.0,x))
def prank(h,v):
    h=[x for x in h if x is not None]; return 100*(sum(1 for x in h if x<v)+0.5*sum(1 for x in h if x==v))/len(h) if h else None
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
def yahoo_weekly(f):
    return K.yweekly(B+'secteurs/'+f)
def r_macd(m,s,h,hp,hist=None,i=None): return K.r_macd(m,s,h,hp,hist,i)
def r_dd(dd):   # même règle que l'onglet Actions : pas d'entrée au plus haut
    if dd>=-2: return -60.0
    if dd>=-12: return -60+(-2-dd)/10*120
    if dd>=-25: return 60.0
    return max(0.0,60-(-25-dd)/15*60)
def lab_s(v): return 'Peur extrême' if v<25 else 'Peur' if v<45 else 'Neutre' if v<=55 else 'Avidité' if v<=75 else 'Euphorie'
def lab_av(s): return 'Vente forte' if s<=-60 else 'Vente' if s<=-20 else 'Neutre' if s<20 else 'Achat' if s<60 else 'Achat fort'
f1=lambda x,n=1:f"{x:.{n}f}".replace('.',',')
fs=lambda x,n=1:f"{x:+.{n}f}".replace('.',',')
SECT=[('XLC','Communication','Communication Services'),('XLY','Consommation discrétionnaire','Consumer Discretionary'),('XLP','Consommation de base','Consumer Staples'),
      ('XLE','Énergie','Energy'),('XLF','Finance','Financials'),('XLV','Santé','Health Care'),('XLI','Industrie','Industrials'),('XLB','Matériaux','Materials'),
      ('XLRE','Immobilier','Real Estate'),('XLK','Technologie','Information Technology'),('XLU','Services aux collectivités','Utilities')]
spx,_=yahoo_weekly('yahoo_1wk_%5EGSPC.json'); spx={d:v for d,v,c in spx if c}
W_S=[('RSI 14 hebdo (valeur brute 0-100)',1/6),('Écart à la moyenne mobile 40 semaines (rang 5 ans)',1/6),('Momentum 26 semaines (rang 5 ans)',1/6),
     ('Force relative vs S&P 500 sur 13 semaines (rang 5 ans)',1/6),('Distance au plus haut 52 semaines (rang 5 ans)',1/6),('Volatilité réalisée 13 semaines, inversée (rang 5 ans)',1/6)]
out={'generated':NOW.strftime('%Y-%m-%d %H:%M'),'sectors':[]}
for sym,fr,gics in SECT:
    UC=RV.rep('AMEX:'+sym)   # 17/11/2026 : ETF SPDR US non vendu chez Revolut -> équivalent UCITS coté sur Xetra
    f=f"yahoo_1wk_{UC['yahoo']}.json"; w,meta=yahoo_weekly(f)
    live=[x for x in w if not x[2]]; wc=[x for x in w if x[2]]
    ds=[x[0] for x in wc]; c=[x[1] for x in wc]; n=len(c)
    OPN=K.yopens(B+'secteurs/'+f); op=[OPN.get(d) for d in ds]; ELL={}
    HLW=K.yhl(B+'secteurs/'+f); CHC={}
    def cha(i,ds=ds,c=c,op=op,HLW=HLW,CHC=CHC,sym=sym,n=n):
        if i not in CHC: CHC[i]=CH.analyse(c[:i+1],ds[:i+1],op[:i+1],HLW,syms=[UC['tv'],UC['yahoo']],manual=(i==n-1))
        return CHC[i]
    def ell(i):
        if i not in ELL: ELL[i]=E.analyse(op[:i+1],c[:i+1])
        return ELL[i]
    FIB={}; FPRE=FB.prefix(meta.get('symbol') or urllib.parse.unquote(sym),ds[0],c[0])
    def fib(i):
        if i not in FIB: FIB[i]=FB.analyse(op[:i+1],c[:i+1],ds[:i+1],FPRE,sym=UC.get('tv') or sym,syms=[UC.get('tv'),UC.get('yahoo'),sym])
        return FIB[i]
    r=rsi(c); m,sg,h=K.macd_series(c)
    cci=K.cci20(op,c)
    mm=sma(c,40)
    ret=[None]+[c[i]/c[i-1]-1 for i in range(1,n)]
    gap=[(c[i]/mm[i]-1)*100 if mm[i] else None for i in range(n)]
    mo13=[(c[i]/c[i-13]-1)*100 if i>=13 else None for i in range(n)]
    mo26=[(c[i]/c[i-26]-1)*100 if i>=26 else None for i in range(n)]
    rs13=[]; rs26=[]
    for i in range(n):
        ok13=i>=13 and ds[i] in spx and ds[i-13] in spx; ok26=i>=26 and ds[i] in spx and ds[i-26] in spx
        rs13.append(((c[i]/c[i-13])/(spx[ds[i]]/spx[ds[i-13]])-1)*100 if ok13 else None)
        rs26.append(((c[i]/c[i-26])/(spx[ds[i]]/spx[ds[i-26]])-1)*100 if ok26 else None)
    dd52=[(c[i]/max(c[max(0,i-51):i+1])-1)*100 for i in range(n)]
    ddath=[(c[i]/max(c[:i+1])-1)*100 for i in range(n)]
    vol=[st.pstdev(ret[i-12:i+1])*math.sqrt(52)*100 if i>=13 else None for i in range(n)]
    def sent_at(i):
        lo=max(0,i-259); win=lambda s:[x for x in s[lo:i+1] if x is not None]
        parts=[r[i], prank(win(gap),gap[i]) if gap[i] is not None else None, prank(win(mo26),mo26[i]) if mo26[i] is not None else None,
               prank(win(rs13),rs13[i]) if rs13[i] is not None else None, prank(win(dd52),dd52[i]), 100-prank(win(vol),vol[i]) if vol[i] is not None else None]
        av=[p for p in parts if p is not None]; return sum(av)/len(av), parts
    def av_at(i,sv):
        comps=[E.comp(ell(i),K.W_EL),FB.comp(fib(i),K.W_FI),
         {'nom':'RSI 14 hebdo','poids':.15,'valeur':f1(r[i]),'note':clip((r[i]-50)/20*100),'regle':'(RSI − 50) / 20 × 100'},
         {'nom':'MACD 12/26/9 hebdo','poids':.15,'valeur':K.macd_valeur(m[i],sg[i],h[i],h[i-1],h,i),'note':r_macd(m[i],sg[i],h[i],h[i-1],h,i),'regle':K.RULE_MACD},
         {'nom':'Écart à la moyenne mobile 40 semaines','poids':.15,'valeur':fs(gap[i])+' %','note':clip(gap[i]/10*100),'regle':'±10 % → ±100'},
         {'nom':'Distance au plus haut 52 semaines','poids':.15,'valeur':fs(dd52[i])+' %','note':r_dd(dd52[i]),'regle':"≥ −2 % : −60 (pas d'entrée au plus haut) ; −2 → −12 % : de −60 à +60 ; −12 → −25 % : +60 ; au-delà : retour vers 0"},
         {'nom':'Momentum 13 et 26 semaines','poids':.15,'valeur':f"13 s. {fs(mo13[i])} % · 26 s. {fs(mo26[i])} %",'note':(clip(mo13[i]/15*100)+clip(mo26[i]/25*100))/2,'regle':'moyenne de (13 s. : ±15 % → ±100) et (26 s. : ±25 % → ±100)'},
         {'nom':'Force relative vs S&P 500 sur 26 semaines','poids':.15,'valeur':(fs(rs26[i])+' pt') if rs26[i] is not None else 'n.d.','note':clip(rs26[i]/10*100) if rs26[i] is not None else None,'regle':'surperformance de +10 pt → +100 ; sous-performance de −10 pt → −100'},
         {'nom':'Sentiment du secteur (lecture contrarienne)','poids':.10,'valeur':f1(sv,0),'note':clip((50-sv)*2),'regle':'(50 − sentiment) × 2 : euphorie = prudence, peur = opportunité'}]
        for x in comps[2:]: x['poids']=round(x['poids']*K.SC,4)
        comps[2:2]=[CH.comp(cha(i),K.W_CH),CH.comp_div(cha(i),K.W_DV)]
        K.add_cci(comps,cci[i])
        av=[x for x in comps if x['note'] is not None]; tw=sum(x['poids'] for x in av)
        for x in comps: x['contrib']=round(x['poids']*x['note']/tw,1) if x['note'] is not None else None
        return round(sum(x['poids']*x['note'] for x in av)/tw,1), comps
    last=n-1; ss=[]; avh=[]
    for i in range(n-52,n):
        sv,_=sent_at(i); ss.append([ds[i],round(sv,1)]); a,_=av_at(i,sv); avh.append([ds[i],a])
    sv,parts=sent_at(last); a,comps=av_at(last,sv)
    for x in comps: x['note']=None if x['note'] is None else round(x['note'],1)
    raw=[f"RSI {f1(r[last])}",f"écart {fs(gap[last])} %",f"{fs(mo26[last])} % sur 26 s.",(f"{fs(rs13[last])} pt vs S&P 500" if rs13[last] is not None else 'n.d.'),f"{fs(dd52[last])} % sous le plus haut 52 s.",f"{f1(vol[last])} % annualisée"]
    athv=max(c); athd=ds[c.index(athv)]
    warn=[]
    if ddath[last]>=-2: warn.append(f"Proche du plus haut historique ({fs(ddath[last])} % sous le record de clôture hebdomadaire du {athd}) : risque d'entrée au sommet.")
    elif dd52[last]>=-2: warn.append(f"Proche du plus haut sur 52 semaines ({fs(dd52[last])} %) : risque d'entrée au sommet.")
    vals=[x[1] for x in ss]; mn=min(ss,key=lambda x:x[1]); mx=max(ss,key=lambda x:x[1])
    etf_name,etf_src=meta.get('longName'),'Yahoo Finance'
    hx=f'/workspace/invest/patrimoine-dashboard/data/secteurs/holdings/{sym}.xlsx'
    if False and os.path.exists(hx):
        try:
            import openpyxl
            r0=next(openpyxl.load_workbook(hx,read_only=True).active.iter_rows(values_only=True))
            if r0 and str(r0[0]).startswith('Fund Name') and r0[1]: etf_name,etf_src=str(r0[1]).replace('®','').strip(),'State Street (fichier de composition)'
        except Exception: pass
    out['sectors'].append({'sym':sym,'tick':UC['tv'].split(':')[1],'tv':UC['tv'],'yahoo':UC['yahoo'],'ref_us':'AMEX:'+sym,'revolut':UC['revolut'],
      'note_revolut':f"ETF US {sym} non vendu chez Revolut (CFD seulement) : remplacé par {UC['tv']} ({UC['nom']}), coté en euros sur Xetra. "+("Indice MSCI World Energy (mondial), pas seulement les États-Unis. " if sym=='XLE' else "")+"La force relative contre le S&P 500 (en dollars) inclut l'effet de change ; historique plus court que l'ETF US.",
      'nom':fr,'gics':gics,'etf':etf_name,'etf_src':etf_src,'currency':meta.get('currency'),
      'date':ds[last],'close':round(c[last],2),'first':ds[0],
      'live':({'date':live[-1][0],'close':round(live[-1][1],2)} if live else None),
      'market_time':D.datetime.fromtimestamp(meta['regularMarketTime'],ZoneInfo('Europe/Paris')).strftime('%Y-%m-%d %H:%M'),
      'sent':{'value':round(sv,1),'label':lab_s(sv),'avg':round(sum(vals)/len(vals),1),'min':mn,'max':mx,'series':ss,
              'components':[{'name':nm,'weight':wt,'value':None if p is None else round(p,1),'raw':rw} for (nm,wt),p,rw in zip(W_S,parts,raw)]},
      'av':{'score':a,'label':lab_av(a),'components':comps,'history':avh,'missing':K.missing(comps),
            'avg':round(sum(x[1] for x in avh)/len(avh),1),'min':min(avh,key=lambda x:x[1]),'max':max(avh,key=lambda x:x[1])},
      'ath':{'date':athd,'close':round(athv,2),'dd':round(ddath[last],1)},'dd52':round(dd52[last],1),'warn':warn,
      'elliott':{k:v for k,v in ell(last).items() if k in('key','phase','conf','note','texte','thr')}|{'dates':[ds[j] for j in ell(last).get('idx',[])],'points':ell(last).get('points',[]),'bodies':True},
      'fibo':{k:v for k,v in fib(last).items() if k in('ok','r','note','zone','broken','base','base_date','ath','ath_date','niveaux','texte','base_apres_ath','debut')},
      'url':f"https://finance.yahoo.com/quote/{UC['yahoo']}/history/",'retrieved':D.datetime.fromtimestamp(os.path.getmtime(B+'secteurs/'+f),ZoneInfo('Europe/Paris')).strftime('%Y-%m-%d %H:%M')})
out['method_sent']="Indice composite APEX, non officiel. Six sous-scores de 0 à 100, poids égaux (1/6 chacun), calculés chaque semaine sur les clôtures hebdomadaires confirmées de l'ETF, sans données futures : (1) RSI 14 de Wilder, valeur brute ; (2) écart du cours à sa moyenne mobile 40 semaines ; (3) performance sur 26 semaines ; (4) force relative contre le S&P 500 sur 13 semaines ; (5) distance au plus haut des 52 dernières semaines ; (6) volatilité réalisée sur 13 semaines, inversée (forte volatilité = peur). Les sous-scores 2 à 6 sont des rangs percentiles sur les 5 dernières années (260 semaines). Zones : 0-24 peur extrême · 25-44 peur · 45-55 neutre · 56-75 avidité · 76-100 euphorie."
out['method_av']="Indice composite APEX, non officiel. Onze composantes notées de −100 à +100 puis pondérées : vagues d'Elliott selon ta règle (15 % : pas d'entrée pendant une vague 5 ni tant que l'ABC qui suit n'est pas terminée ; entrées en fin de vague 4 ou en fin de vague C), retracement de Fibonacci du plus bas historique (base) au plus haut historique (ATH) sur les corps des bougies (15 % : plus le cours est bas dans le retracement, plus la note pousse à l'achat ; négative près de l'ATH ; plafonnée sous la base), "+CH.TXT_CRIT+", RSI 14 hebdo (6 %), MACD 12/26/9 hebdo (6 %, note plafonnée à −50 si l'histogramme a au moins 4 barres positives consécutives, plancher +50 si 4 barres négatives), CCI 20 hebdo facultatif (6 % pris sur le panier de 40 % uniquement au-delà des seuils ±100 du CCI_S, ligne violette = +100), écart à la moyenne mobile 40 semaines (6 %), distance au plus haut 52 semaines selon la règle « pas d'entrée au plus haut » (6 %), momentum 13 et 26 semaines (6 %), force relative contre le S&P 500 sur 26 semaines (6 %), sentiment du secteur lu de façon contrarienne (4 %). Les lectures sont automatiques (Elliott du critère dédié et Fibonacci sur les corps, structure de la Charte graphique sur les mèches) : c'est une approximation qui peut différer de ton indicateur TradingView. Score = Σ (poids × note) ÷ Σ (poids disponibles). Zones : ≤ −60 vente forte · −60 à −20 vente · −20 à +20 neutre · +20 à +60 achat · ≥ +60 achat fort. Cours hors dividendes."
json.dump(out,open(B+'secteurs.json','w'),ensure_ascii=False)
for s in out['sectors']:
    print(s['sym'].ljust(5),s['nom'][:28].ljust(28),s['date'],'clôt.',s['close'],'| sent',s['sent']['value'],s['sent']['label'],'| AV',s['av']['score'],s['av']['label'],'| ATH',s['ath'],'| live',s['live'],s['warn'])
