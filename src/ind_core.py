"""Moteur commun des indicateurs APEX (sentiment 0-100 et achat / vente −100…+100) sur clôtures hebdomadaires.
Mêmes formules que src/build_secteurs.py (secteurs USA), avec un indice de référence paramétrable pour la force relative."""
import json, os, sys, math, datetime as D, statistics as st
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__))); import elliott as E, fibo as FB, charte as CH, yahoo_week as YW, elliott_zones as EZ
from zoneinfo import ZoneInfo
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
    return YW.as_yweekly(B+'secteurs/'+f, now=NOW)
def macd_series(c, fast=12, slow=26, sig=9):
    """Ligne MACD 12/26, signal 9, histogramme. Même EMA que le reste du moteur."""
    e12,e26=ema(c,fast),ema(c,slow)
    m=[a-b for a,b in zip(e12,e26)]
    sg=ema(m,sig)
    h=[a-b for a,b in zip(m,sg)]
    return m,sg,h

def hist_streak(h,i):
    """Signe (+1 / −1) et nombre de barres consécutives de l'histogramme MACD se terminant en i (0 si barre nulle)."""
    if i is None or i<0 or i>=len(h) or h[i] is None or h[i]==0:
        return 0,0
    sign=1 if h[i]>0 else -1
    n=0
    for j in range(i,-1,-1):
        if h[j] is None or (1 if h[j]>0 else -1 if h[j]<0 else 0)!=sign:
            break
        n+=1
    return sign,n

def r_macd(m,s,h,hp,hist=None,i=None):
    """Note MACD classique, plafonnée si l'impulsion est déjà étendue (≥ 4 barres hebdo de même signe).
    4 barres positives : min(classique, −50). 4 barres négatives : max(classique, +50)."""
    base=(100 if h>hp else 50) if m>=s else (-50 if h>hp else -100)
    if hist is None or i is None:
        return base
    sign,k=hist_streak(hist,i)
    if sign>0 and k>=4:
        return min(base,-50)
    if sign<0 and k>=4:
        return max(base,50)
    return base

def macd_valeur(m,s,h,hp,hist=None,i=None):
    txt=('MACD > signal' if m>=s else 'MACD < signal')+(', histogramme en hausse' if h>hp else ', histogramme en baisse')
    if hist is not None and i is not None:
        sign,k=hist_streak(hist,i)
        if sign>0 and k>=4:
            txt+=f' · {k} barres positives consécutives, impulsion étendue'
        elif sign<0 and k>=4:
            txt+=f' · {k} barres négatives consécutives, impulsion baissière étendue'
    return txt

RULE_MACD=("+100 MACD > signal et histogramme en hausse ; +50 > signal ; −50 < signal mais histogramme en hausse ; −100 sinon. "
 "Si l'histogramme a au moins 4 barres hebdomadaires positives consécutives (impulsion déjà étendue), la note est plafonnée à −50. "
 "Symétrique : au moins 4 barres négatives consécutives, plancher à +50.")

def cci20(op,c,n=20):
    """CCI 20 sur les corps hebdomadaires (même formule que les fiches Énergie / Crypto et que CCI_S de la vue TradingView APEX).
    Typical price = (haut de corps + bas de corps + clôture) / 3. Seuils classiques ±100 (ligne violette = +100)."""
    if op is None:
        op=[None]*len(c)
    hi=[max(a,b) if a is not None else b for a,b in zip(op,c)]
    lo=[min(a,b) if a is not None else b for a,b in zip(op,c)]
    tp=[(h+l+cl)/3 for h,l,cl in zip(hi,lo,c)]
    out=[None]*len(tp)
    for i in range(n-1,len(tp)):
        w=tp[i-n+1:i+1]
        sma=sum(w)/n
        md=sum(abs(x-sma) for x in w)/n
        out[i]=0.0 if md==0 else (tp[i]-sma)/(0.015*md)
    return out

def cci_note(v):
    """Note facultative du CCI 20. Hors zone ±100 : None (poids redistribué). Au-dessus de +100 : pénalité ; sous −100 : bonus.
    |CCI| ≥ 200 → ±100 ; 100 ≤ |CCI| < 200 → ±80. Le seuil violet de la vue APEX est le +100 du CCI_S (période 20)."""
    if v is None: return None
    if v>=200: return -100.0
    if v>=100: return -80.0
    if v<=-200: return 100.0
    if v<=-100: return 80.0
    return None

def cci_zone(v):
    if v is None: return 'indisponible'
    if v>=100: return 'surachat (≥ +100, seuil violet)'
    if v<=-100: return 'survente (≤ −100)'
    return 'zone neutre'

RULE_CCI=("CCI 20 calculé sur les corps hebdomadaires, mêmes seuils que l'indicateur CCI_S de la vue TradingView APEX "
 "(ligne violette = +100, ligne de survente = −100). Au-dessus de +100 : surachat, note −80 (ou −100 si CCI ≥ +200). "
 "Sous −100 : survente, note +80 (ou +100 si CCI ≤ −200). Entre les deux seuils, le critère n'est pas compté et son poids "
 "est redistribué, afin de laisser Charte 20 %, Elliott 15 %, Fibonacci 15 % et Divergence 10 % inchangés.")
W_CCI=0.06  # 6 %, pris sur le panier des 40 % uniquement lorsque le CCI est en zone extrême

def _est_coeur(nom):
    return (nom.startswith("Vagues d'Elliott") or nom.startswith('Retracement') or
            nom.startswith('Charte graphique') or nom.startswith('Divergence'))

def cci_comp(v,poids=W_CCI):
    nt=cci_note(v)
    val=('n.d.' if v is None else f"{v:+.1f}".replace('.',',')+' · '+cci_zone(v))
    return {'nom':'CCI 20 hebdo (corps, seuil violet ±100)','poids':poids,'valeur':val,'note':nt,'regle':RULE_CCI,'facultatif':True}

def add_cci(comps,v):
    """Insère le CCI 20 juste après le MACD. Si le CCI est en zone extrême, les composantes du panier 40 %
    sont ramenées à 34 % pour laisser 6 % au CCI (Charte 20 %, Elliott 15 %, Fibonacci 15 %, Divergence 10 % inchangés).
    Hors zone, le CCI n'est pas compté et les poids du panier restent à 40 %."""
    cc=cci_comp(v,W_CCI)
    idx=next((i for i,x in enumerate(comps) if x['nom'].startswith('MACD')), len(comps)-1)
    comps.insert(idx+1,cc)
    if cc['note'] is None:
        return comps
    others=[x for x in comps if not _est_coeur(x['nom']) and x is not cc]
    tw=sum(x['poids'] for x in others)
    if tw>0:
        cible=0.40-W_CCI  # 0,34
        k=cible/tw
        for x in others:
            x['poids']=round(x['poids']*k,4)
    return comps
def r_dd(dd):   # même règle que l'onglet Actions : pas d'entrée au plus haut
    if dd>=-2: return -60.0
    if dd>=-12: return -60+(-2-dd)/10*120
    if dd>=-25: return 60.0
    return max(0.0,60-(-25-dd)/15*60)
def lab_s(v): return 'Peur extrême' if v<25 else 'Peur' if v<45 else 'Neutre' if v<=55 else 'Avidité' if v<=75 else 'Euphorie'
def lab_av(s): return 'Vente forte' if s<=-60 else 'Vente' if s<=-20 else 'Neutre' if s<20 else 'Achat' if s<60 else 'Achat fort'
f1=lambda x,n=1:f"{x:.{n}f}".replace('.',',')
fs=lambda x,n=1:f"{x:+.{n}f}".replace('.',',')
def yweekly(path):
    return YW.as_yweekly(path, now=NOW)
def yopens(path):
    """ouvertures hebdomadaires {vendredi ISO: ouverture}, même découpage que yweekly (pour les corps de bougie Elliott)"""
    return YW.as_yopens(path, now=NOW)
W_EL=.15; W_FI=.15; W_CH=CH.W_CH; W_DV=CH.W_DV; SC=1-W_EL-W_FI-W_CH-W_DV   # 17/11/2026 : Elliott 15 % + Fibonacci 15 % + Charte graphique 20 % + Divergence RSI / MACD weekly 10 % (non comptée sans divergence, aucun bonus) ; les autres poids gardent leurs proportions sur les 40 % restants. 18/11/2026 : CCI 20 facultatif 6 % pris sur ce panier 40 % uniquement en zone ±100.
def missing(comps): return [x['nom'] for x in comps if x['note'] is None and not x.get('facultatif')]
def yhl(path):
    """plus hauts / plus bas hebdomadaires {vendredi ISO: (haut, bas)} (mèches), même découpage que yweekly"""
    return YW.as_yhl(path, now=NOW)
def W_S(BN): return [('RSI 14 hebdo (valeur brute 0-100)',1/6),('Écart à la moyenne mobile 40 semaines (rang 5 ans)',1/6),('Momentum 26 semaines (rang 5 ans)',1/6),
     (f'Force relative vs {BN} sur 13 semaines (rang 5 ans)',1/6),('Distance au plus haut 52 semaines (rang 5 ans)',1/6),('Volatilité réalisée 13 semaines, inversée (rang 5 ans)',1/6)]
def compute(w,BEN,BN,opens=None,fsym=None,fpre=None,hl=None,syms=None,fibo_adjust_splits=True):
    """w = [(date ISO du vendredi, clôture, semaine clôturée ?)] ; BEN = {date: clôture de l'indice de référence}
    fpre : préfixe Fibonacci déjà calculé (ouvertures, clôtures, dates) ; sinon fsym sert à FB.prefix.
    fibo_adjust_splits : passé à fibo.analyse (False pour les crypto, afin de ne pas traiter un pump comme une division)."""
    live=[x for x in w if not x[2]]; wc=[x for x in w if x[2]]
    ds=[x[0] for x in wc]; c=[x[1] for x in wc]; n=len(c)
    op=[(opens or {}).get(d) for d in ds]
    ELL={}
    def ell(i):
        if i not in ELL: ELL[i]=E.analyse(op[:i+1],c[:i+1])
        if i==n-1: ELL[i]=CH.elliott_manuel(ELL[i],syms or [fsym])
        return ELL[i]
    FIB={}; FPRE=fpre if fpre is not None else (FB.prefix(fsym,ds[0],c[0]) if (fsym and ds) else None)   # historique maximal pour la base / l'ATH
    def fib(i):
        if i not in FIB: FIB[i]=FB.analyse(op[:i+1],c[:i+1],ds[:i+1],FPRE,adjust_splits=fibo_adjust_splits,sym=fsym,syms=syms)
        return FIB[i]
    CHC={}
    def cha(i):
        if i not in CHC: CHC[i]=CH.analyse(c[:i+1],ds[:i+1],op[:i+1],hl,r[:i+1],syms=(syms or [fsym]),manual=(i==n-1))
        return CHC[i]
    r=rsi(c); m,sg,h=macd_series(c)
    cci=cci20(op,c)
    mm=sma(c,40)
    ret=[None]+[c[i]/c[i-1]-1 for i in range(1,n)]
    gap=[(c[i]/mm[i]-1)*100 if mm[i] else None for i in range(n)]
    mo13=[(c[i]/c[i-13]-1)*100 if i>=13 else None for i in range(n)]
    mo26=[(c[i]/c[i-26]-1)*100 if i>=26 else None for i in range(n)]
    rs13=[]; rs26=[]
    for i in range(n):
        ok13=i>=13 and ds[i] in BEN and ds[i-13] in BEN; ok26=i>=26 and ds[i] in BEN and ds[i-26] in BEN
        rs13.append(((c[i]/c[i-13])/(BEN[ds[i]]/BEN[ds[i-13]])-1)*100 if ok13 else None)
        rs26.append(((c[i]/c[i-26])/(BEN[ds[i]]/BEN[ds[i-26]])-1)*100 if ok26 else None)
    dd52=[(c[i]/max(c[max(0,i-51):i+1])-1)*100 for i in range(n)]
    ddath=[(c[i]/max(c[:i+1])-1)*100 for i in range(n)]
    vol=[st.pstdev(ret[i-12:i+1])*math.sqrt(52)*100 if i>=13 else None for i in range(n)]
    def sent_at(i):
        lo=max(0,i-259); win=lambda s:[x for x in s[lo:i+1] if x is not None]
        parts=[r[i], prank(win(gap),gap[i]) if gap[i] is not None else None, prank(win(mo26),mo26[i]) if mo26[i] is not None else None,
               prank(win(rs13),rs13[i]) if rs13[i] is not None else None, prank(win(dd52),dd52[i]), 100-prank(win(vol),vol[i]) if vol[i] is not None else None]
        av=[p for p in parts if p is not None]; return sum(av)/len(av), parts
    def av_at(i,sv):
        comps=[E.comp(ell(i),W_EL),FB.comp(fib(i),W_FI),
         {'nom':'RSI 14 hebdo','poids':.15,'valeur':f1(r[i]) if r[i] is not None else 'n.d.','note':clip((r[i]-50)/20*100) if r[i] is not None else None,'regle':'(RSI − 50) / 20 × 100'},
         {'nom':'MACD 12/26/9 hebdo','poids':.15,'valeur':macd_valeur(m[i],sg[i],h[i],h[i-1],h,i) if i and None not in (m[i],sg[i],h[i],h[i-1]) else 'n.d.','note':r_macd(m[i],sg[i],h[i],h[i-1],h,i) if i and None not in (m[i],sg[i],h[i],h[i-1]) else None,'regle':RULE_MACD},
         {'nom':'Écart à la moyenne mobile 40 semaines','poids':.15,'valeur':(fs(gap[i])+' %') if gap[i] is not None else 'n.d.','note':clip(gap[i]/10*100) if gap[i] is not None else None,'regle':'±10 % → ±100'},
         {'nom':'Distance au plus haut 52 semaines','poids':.15,'valeur':fs(dd52[i])+' %','note':r_dd(dd52[i]),'regle':"≥ −2 % : −60 (pas d'entrée au plus haut) ; −2 → −12 % : de −60 à +60 ; −12 → −25 % : +60 ; au-delà : retour vers 0"},
         {'nom':'Momentum 13 et 26 semaines','poids':.15,'valeur':f"13 s. {fs(mo13[i]) if mo13[i] is not None else 'n.d.'} % · 26 s. {fs(mo26[i]) if mo26[i] is not None else 'n.d.'} %",'note':(clip(mo13[i]/15*100)+clip(mo26[i]/25*100))/2 if mo13[i] is not None and mo26[i] is not None else None,'regle':'moyenne de (13 s. : ±15 % → ±100) et (26 s. : ±25 % → ±100)'},
         {'nom':f'Force relative vs {BN} sur 26 semaines','poids':.15,'valeur':(fs(rs26[i])+' pt') if rs26[i] is not None else 'n.d.','note':clip(rs26[i]/10*100) if rs26[i] is not None else None,'regle':'surperformance de +10 pt → +100 ; sous-performance de −10 pt → −100'},
         {'nom':'Sentiment du secteur (lecture contrarienne)','poids':.10,'valeur':f1(sv,0),'note':clip((50-sv)*2),'regle':'(50 − sentiment) × 2 : euphorie = prudence, peur = opportunité'}]
        for x in comps[2:]: x['poids']=round(x['poids']*SC,4)
        comps[2:2]=[CH.comp(cha(i),W_CH),CH.comp_div(cha(i),W_DV)]
        add_cci(comps,cci[i])
        av=[x for x in comps if x['note'] is not None]; tw=sum(x['poids'] for x in av)
        for x in comps: x['contrib']=round(x['poids']*x['note']/tw,1) if x['note'] is not None else None
        return round(sum(x['poids']*x['note'] for x in av)/tw,1), comps
    last=n-1; ss=[]; avh=[]
    for i in range(n-52,n):
        sv,_=sent_at(i); ss.append([ds[i],round(sv,1)]); a,_=av_at(i,sv); avh.append([ds[i],a])
    sv,parts=sent_at(last); a,comps=av_at(last,sv)
    for x in comps: x['note']=None if x['note'] is None else round(x['note'],1)
    raw=[f"RSI {f1(r[last])}",f"écart {fs(gap[last])} %",f"{fs(mo26[last])} % sur 26 s.",(f"{fs(rs13[last])} pt vs "+BN+"" if rs13[last] is not None else 'n.d.'),f"{fs(dd52[last])} % sous le plus haut 52 s.",f"{f1(vol[last])} % annualisée"]
    athv=max(c); athd=ds[c.index(athv)]
    warn=[]
    if ddath[last]>=-2: warn.append(f"Proche du plus haut historique ({fs(ddath[last])} % sous le record de clôture hebdomadaire du {athd}) : risque d'entrée au sommet.")
    elif dd52[last]>=-2: warn.append(f"Proche du plus haut sur 52 semaines ({fs(dd52[last])} %) : risque d'entrée au sommet.")

    vals=[x[1] for x in ss]; mn=min(ss,key=lambda x:x[1]); mx=max(ss,key=lambda x:x[1])
    out={'date':ds[last],'close':round(c[last],2),'first':ds[0],'n':n,
      'live':({'date':live[-1][0],'close':round(live[-1][1],2)} if live else None),
      'sent':{'value':round(sv,1),'label':lab_s(sv),'avg':round(sum(vals)/len(vals),1),'min':mn,'max':mx,'series':ss,
              'components':[{'name':nm,'weight':wt,'value':None if p is None else round(p,1),'raw':rw} for (nm,wt),p,rw in zip(W_S(BN),parts,raw)]},
      'av':{'score':a,'label':lab_av(a),'components':comps,'history':avh,'missing':missing(comps),
            'avg':round(sum(x[1] for x in avh)/len(avh),1),'min':min(avh,key=lambda x:x[1]),'max':max(avh,key=lambda x:x[1])},
      'ath':{'date':athd,'close':round(athv,2),'dd':round(ddath[last],1)},'dd52':round(dd52[last],1),'warn':warn,
      'elliott':{k:v for k,v in ell(last).items() if k in('key','phase','conf','note','texte','thr','manuel','override','zone')}|{'dates':[ds[j] for j in ell(last).get('idx',[])],'points':ell(last).get('points',[]),'bodies':any(x is not None for x in op),'zone':(ell(last).get('zone') if ell(last) else None)},
      'charte':cha(last),
      'fibo':{k:v for k,v in fib(last).items() if k in('ok','r','note','zone','broken','base','base_date','ath','ath_date','niveaux','texte','base_apres_ath','debut')}}
    EZ.appliquer_av(out['av'], out.get('elliott'))
    if out.get('elliott') and not out['elliott'].get('zone'):
        out['elliott']['zone']=EZ.zone_of(out['elliott'].get('key'))
    import technique_apex as TA
    out['technique'] = TA.pack_from_compute(out, c, ds, op, hl)
    out['av']['technique'] = {k: out['technique'].get(k) for k in TA.TECH_IDS}
    return out
