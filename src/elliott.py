"""Lecture automatique des vagues d'Elliott sur bougies HEBDOMADAIRES, à partir des CORPS de bougie (jamais des mèches).
Règle d'Emmanuel (23/11/2026, dessin validé « PARFAIT ») :
  zones vertes (entrée) : fin de vague 2, fin de vague 4, vague C ;
  zones rouges (aucune entrée) : vague 1, vague 3, vague 5, vague A, vague B.

Méthode (déterministe, sans données futures) :
 1. Corps de bougie : haut = max(ouverture, clôture), bas = min(ouverture, clôture). Sans ouverture disponible,
    l'ouverture est remplacée par la clôture de la semaine précédente.
 2. ZigZag sur les corps, à plusieurs seuils adaptés à la volatilité de l'actif (multiples de la variation hebdomadaire
    médiane sur 5 ans, bornés entre 4 % et 60 %). Le dernier point est l'extrême provisoire de la jambe en cours.
 3. Pour chaque seuil, on teste les décomptes haussiers (1-2-3-4-5 puis A-B-C) et baissiers sur les derniers points,
    avec les règles classiques : la 2 ne repasse pas sous le départ de la 1, la 3 dépasse la 1 et n'est pas la plus
    courte, la 4 ne chevauche pas le territoire de la 1 (tolérance avec pénalité), la B ne dépasse pas le sommet de la 5
    (tolérance de 5 % avec pénalité). Les proportions de Fibonacci (2, 3, 4, C/A) ajustent la confiance.
 4. On retient le décompte de plus forte confiance (à confiance égale : le plus complet, puis le plus grand degré).
"""
import math, statistics as st

# barème de notation (−100 … +100, + = achat) — documenté sur le site
TABLE=[
 ('fin_c_conf', +100,"Fin de vague C probable, retournement confirmé par une bougie hebdomadaire clôturée : zone verte d'entrée"),
 ('fin_2_conf',  +80,"Fin de vague 2 probable, retournement confirmé par une bougie hebdomadaire clôturée : zone verte d'entrée"),
 ('fin_4_conf',  +80,"Fin de vague 4 probable, retournement confirmé par une bougie hebdomadaire clôturée : zone verte d'entrée"),
 ('fin_c',       +60,"Vague C proche de sa fin (C ≥ 100 % de A ou dans la zone de la 4) : zone verte d'entrée"),
 ('fin_4',       +60,"Vague 4 proche de sa fin (repli de 23,6 à 61,8 % de la 3) : zone verte d'entrée"),
 ('fin_2',       +60,"Vague 2 proche de sa fin (repli de 38,2 à 78,6 % de la 1) : zone verte d'entrée"),
 ('c_mid',       +60,"Vague C en cours (61,8 à 100 % de A) : zone verte d'entrée (sans bonus de confirmation)"),
 ('c',           +60,"Vague C en cours : zone verte d'entrée"),
 ('w4',          +20,"Vague 4 en cours, pas encore terminée"),
 ('w2',          +10,"Vague 2 en cours, pas encore terminée"),
 ('indet',         0,"Décompte indéterminé"),
 ('w1',            0,"Vague 1 en cours : zone rouge, aucune entrée"),
 ('w3',            0,"Vague 3 en cours : zone rouge, aucune entrée"),
 ('new1',          0,"Vague 1 naissante après la C : zone rouge, aucune entrée"),
 ('bear_24',     -30,"Rebond 2 ou 4 dans une impulsion baissière"),
 ('bear_135',    -50,"Impulsion baissière en cours (vague 1, 3 ou 5 vers le bas) : zone rouge, aucune entrée"),
 ('a',           -60,"Vague A de correction en cours après la 5 : zone rouge, aucune entrée"),
 ('fin_a',       -60,"Fin de vague A : zone rouge, aucune entrée (B puis C encore à venir)"),
 ('b',           -60,"Vague B de correction en cours : zone rouge, aucune entrée"),
 ('deb_5',       -60,"Début de vague 5 : zone rouge, aucune entrée"),
 ('w5',          -80,"Vague 5 en cours : zone rouge, aucune entrée"),
]
BASE={k:v for k,v,_ in TABLE}; TXT={k:t for k,_,t in TABLE}
PHASE={'fin_c_conf':'C','fin_2_conf':'2','fin_4_conf':'4','fin_c':'C','fin_4':'4','fin_2':'2','deb_5':'5','w4':'4','w1':'1','w2':'2','w3':'3','indet':'indéterminé',
       'c_mid':'C','bear_24':'baissière','bear_135':'baissière','a':'A','fin_a':'A','b':'B','c':'C','w5':'5','new1':'1'}
RULE_TXT=("Lecture automatique sur bougies hebdomadaires clôturées, corps de bougie uniquement (ZigZag multi-seuils adapté à la volatilité, "
 "règles 2 < départ de 1, 3 jamais la plus courte, 4 sans chevauchement de la 1, ABC après la 5). "
 "Règle d'entrée du 23/11/2026 : zones vertes = fin de vague 2, fin de vague 4, vague C ; zones rouges = vagues 1, 3, 5, A et B. "
 "Un comptage manuel d'Emmanuel (data/elliott_overrides.json) prime sur le décompte automatique. "
 "Note du critère Elliott = barème × (0,5 + 0,5 × confiance). Décompte approximatif, il peut différer de ton indicateur TradingView.")

def bodies(o,c):
    hi=[];lo=[]
    for i,x in enumerate(c):
        op=o[i] if (o is not None and i<len(o) and o[i] is not None) else (c[i-1] if i else x)
        hi.append(max(op,x)); lo.append(min(op,x))
    return hi,lo

def zigzag(hi,lo,thr):
    """pivots alternés [(idx, prix, 'H'|'L')] ; le dernier est l'extrême provisoire de la jambe en cours."""
    n=len(hi)
    if n<3: return []
    piv=[]; d=0; ei=0; ehi=hi[0]; elo=lo[0]; hi_i=0; lo_i=0
    for i in range(1,n):
        if d==0:
            if hi[i]>ehi: ehi,hi_i=hi[i],i
            if lo[i]<elo: elo,lo_i=lo[i],i
            if ehi/elo-1>=thr:
                if hi_i>lo_i: piv.append((lo_i,elo,'L')); d=1; ei,ex=hi_i,ehi
                else: piv.append((hi_i,ehi,'H')); d=-1; ei,ex=lo_i,elo
            continue
        if d==1:
            if hi[i]>ex: ex,ei=hi[i],i
            elif lo[i]<=ex*(1-thr): piv.append((ei,ex,'H')); d=-1; ex,ei=lo[i],i
        else:
            if lo[i]<ex: ex,ei=lo[i],i
            elif hi[i]>=ex*(1+thr): piv.append((ei,ex,'L')); d=1; ex,ei=hi[i],i
    if d!=0: piv.append((ei,ex,'H' if d==1 else 'L'))
    return piv

def fibfit(x,lo,hi,soft=0.5):
    """1 dans [lo,hi], décroît en dehors"""
    if lo<=x<=hi: return 1.0
    dd=(lo-x) if x<lo else (x-hi); return max(0.0,1-dd/soft)

def _impulse(P,complete):
    """P = prix des points 0..k (k<=5) d'une impulsion haussière. Retourne (valide, confiance)"""
    k=len(P)-1; conf=1.0
    if P[1]<=P[0]: return False,0
    l1=P[1]-P[0]
    if k>=2:
        if P[2]<=P[0] or P[2]>=P[1]: return False,0
        conf*=0.7+0.3*fibfit((P[1]-P[2])/l1,.382,.786,.3)
    if k>=3:
        if P[3]<=P[1]: return False,0
        l3=P[3]-P[2]; conf*=0.7+0.3*fibfit(l3/l1,1.0,2.618,.6)
    if k>=4:
        if P[4]>=P[3] or P[4]<=P[2]: return False,0
        if P[4]<=P[1]:
            ov=(P[1]-P[4])/(P[3]-P[0])
            if ov>0.15: return False,0
            conf*=0.75                                    # chevauchement léger (diagonale / indices) : pénalité
        conf*=0.7+0.3*fibfit((P[3]-P[4])/l3,.236,.5,.3)
    if k>=5:
        if P[5]<=P[4]: return False,0
        l5=P[5]-P[4]
        if complete:
            if l3<l1 and l3<l5: return False,0
            if P[5]<=P[3]: conf*=0.6                      # 5 tronquée
    return True,conf

def _abc(P5,P4,PA,PB=None,PC=None):
    conf=1.0; la=P5-PA
    if la<=0: return False,0
    if PB is not None:
        if PB<=PA: return False,0
        if PB>P5*1.05: return False,0
        if PB>P5: conf*=0.7                                # B irrégulière
        conf*=0.7+0.3*fibfit((PB-PA)/la,.382,.886,.3)
    if PC is not None:
        if PC>=PB: return False,0
    return True,conf

NPIV=14
def subseqs(pv):
    """sous-suites alternées de pivots finissant sur le dernier point (extrême provisoire), de 2 à 10 points ;
    chaque point retenu est l'extrême des pivots situés entre ses deux voisins (sommet = plus haut, creux = plus bas)."""
    n=len(pv); out=[]
    def ext(i,a,b):   # pv[i] extrême sur [a,b]
        t=pv[i][2]; seg=[pv[j][1] for j in range(a,b+1) if pv[j][2]==t]
        return pv[i][1]==(max(seg) if t=='H' else min(seg))
    def rec(seq):
        k=len(seq)
        if k>=2: out.append((k,seq[:]))
        if k>=10: return
        cur=seq[0]
        for j in range(cur-1,-1,-2):           # types alternés : écart impair
            nxt=seq[1] if k>=2 else n-1
            if not ext(cur,j,nxt): continue  # le point courant doit dominer sa jambe
            # le nouveau point doit être l'extrême entre lui-même et cur (aucun pivot du même type plus extrême dans l'intervalle)
            t=pv[j][2]; seg=[pv[m][1] for m in range(j,cur+1) if pv[m][2]==t]
            if pv[j][1]!=(max(seg) if t=='H' else min(seg)): continue
            rec([j]+seq)
    rec([n-1])
    # contrôle final du premier point : extrême sur [idx0, idx1]
    return out
def _bull(P,k,thr,turned,last,cand):
    if k>=7:
        if k>10: return
        ok,cf=_impulse(P[:6],True)
        if not ok: return
        PA=P[6]; PB=P[7] if k>=8 else None; PC=P[8] if k>=9 else None
        ok2,cf2=_abc(P[5],P[4],PA,PB,PC)
        if not ok2: return
        cf*=cf2; la=P[5]-PA
        if k==7: cand('a',cf,k,thr,P,{'drop':(P[5]-last)/P[5]})
        elif k==8: cand('b',cf,k,thr,P,{})
        elif k==9:
            lc=PB-PC; ratio=lc/la
            if ratio>=1.0 or (PC<=P[4] and ratio>=.618): key='fin_c_conf' if turned else 'fin_c'
            elif ratio>=.618: key='c_mid'
            else: key='c'
            cf*=0.7+0.3*fibfit(ratio,.618,1.618,.5)
            cand(key,cf,k,thr,P,{'ratio':ratio})
        else:
            lc=PB-PC
            if lc/la<.618 and PC>P[4]: return
            rise=(P[9]-PC)/(P[5]-PC)
            if rise<.382: cand('new1',cf*0.9,k,thr,P,{'rise':rise})
        return
    ok,cf=_impulse(P,False)
    if not ok: return
    if k==6:
        l1=P[1]-P[0]; prog=(P[5]-P[4])/l1
        cand('deb_5' if (prog<.382 and P[5]<P[3]) else 'w5',cf*0.95,k,thr,P,{'prog':prog})
    elif k==5:
        r4=(P[3]-P[4])/(P[3]-P[2])
        key=('fin_4_conf' if turned else 'fin_4') if (.236<=r4<=.618 and P[4]>P[1]) else 'w4'
        cand(key,cf*0.9,k,thr,P,{'r4':r4})
    elif k==4: cand('w3',cf*0.75,k,thr,P,{})
    elif k==3:
        r2=(P[1]-P[2])/(P[1]-P[0]) if P[1]!=P[0] else 0
        key=('fin_2_conf' if turned else 'fin_2') if (.382<=r2<=.786 and P[2]>P[0]) else 'w2'
        cand(key,cf*0.55,k,thr,P,{'r2':r2})
    else: cand('w1',cf*0.4,k,thr,P,{})
def _bear(P,k,thr,cand):
    if k>6: return
    M=[-x for x in P]; ok,cf=_impulse(M,False)
    if not ok: return
    cand('bear_135' if k in(4,6) else 'bear_24',cf*0.8*(0.85 if k<6 else 1),k,thr,P,{})

def analyse(o,c,ks=(4,5,6,8,10,13,16)):
    """o, c : ouvertures / clôtures hebdomadaires CLÔTURÉES (o peut être None). Retourne un dict décrivant la phase."""
    if len(c)<60: return {'key':'indet','phase':'indéterminé','conf':0,'note':0,'texte':TXT['indet']+' (historique insuffisant)'}
    hi,lo=bodies(o,c)
    return analyse_hl(hi,lo,c,ks)

def analyse_hl(hi,lo,c,ks=(4,5,6,8,10,13,16)):
    """Même lecture que analyse(), mais sur des hauts / bas fournis (ex. MÈCHES hebdomadaires : utilisées par le critère
    Charte graphique, car pour Elliott les mèches sont acceptées)."""
    n=len(c)
    if n<60: return {'key':'indet','phase':'indéterminé','conf':0,'note':0,'texte':TXT['indet']+' (historique insuffisant)'}
    r=[abs(math.log(c[i]/c[i-1])) for i in range(max(1,n-260),n) if c[i] and c[i-1]]
    sig=st.median(r) if r else .02
    thrs=sorted(set(round(min(.60,max(.04,sig*k)),3) for k in ks))
    best=None; last=c[-1]
    def cand(key,conf,npts,thr,P,extra,I):
        nonlocal best
        cs=(round(conf,3),npts,-thr)
        if best is None or cs>best[0]: best=(cs,key,conf,thr,P,extra,I)
    for thr in thrs:
        pv=zigzag(hi,lo,thr)[-NPIV:]
        if len(pv)<2: continue
        run=pv[-1]; up=run[2]=='H'
        turn=(last/run[1]-1) if not up else (1-last/run[1])   # rebond / repli depuis l'extrême provisoire
        turned= turn>=0.3*thr
        for k,idx in subseqs(pv):
            P=[pv[i][1] for i in idx]; first=pv[idx[0]][2]
            I=[pv[i][0] for i in idx]
            if first=='L': _bull(P,k,thr,turned,last,lambda *a:cand(*a,I))
            elif k>=4: _bear(P,k,thr,lambda *a:cand(*a,I))
    if best is None:
        return {'key':'indet','phase':'indéterminé','conf':0,'note':0,'texte':TXT['indet'],'thr':None}
    _,key,conf,thr,P,extra,I=best
    conf=max(0.0,min(1.0,conf))
    if conf<0.35: key='indet'
    note=round(BASE[key]*(0.5+0.5*conf),1)
    return {'key':key,'phase':PHASE[key],'conf':round(conf,2),'note':note,'texte':TXT[key],'thr':thr,'points':[round(x,4) for x in P],'idx':I,'extra':{a:round(b,3) for a,b in extra.items()}}

def valeur(e):
    if e.get('manuel'): return e['texte']
    if e['key']=='indet': return e['texte']+' · lecture automatique, à confirmer sur TradingView'
    return f"{e['texte']} · confiance {round(e['conf']*100):d} % · lecture automatique, à confirmer sur TradingView"

def comp(e,poids=.25):
    return {'nom':"Vagues d'Elliott (ta règle : fin de 2, fin de 4 ou vague C)",'poids':poids,'valeur':valeur(e),'note':e['note'],'regle':RULE_TXT,'elliott':{'phase':e['phase'],'key':e['key'],'conf':e['conf']}}

SHORT={'fin_c_conf':'fin de C confirmée','fin_2_conf':'fin de 2 confirmée','fin_4_conf':'fin de 4 confirmée','fin_c':'fin de C proche','fin_4':'fin de 4 proche','fin_2':'fin de 2 proche',
       'deb_5':'début de 5','w4':'vague 4','w1':'vague 1','w2':'vague 2','w3':'vague 3','indet':'indéterminé','c_mid':'vague C avancée','bear_24':'rebond baissier',
       'bear_135':'impulsion baissière','a':'vague A','fin_a':'fin de vague A','b':'vague B','c':'vague C','w5':'vague 5','new1':'vague 1 naissante'}
def comp_multi(items,poids=.25):
    """items = [(nom de l'actif, analyse)] : note moyenne"""
    notes=[e['note'] for _,e in items]
    return {'nom':"Vagues d'Elliott (ta règle : fin de 4 ou fin de C)",'poids':poids,'valeur':' · '.join(f"{n} : {SHORT[e['key']]} ({e['note']:+.0f})".replace('.',',') for n,e in items)+' · lecture automatique, à confirmer sur TradingView',
            'note':sum(notes)/len(notes),'regle':RULE_TXT+' Moyenne des notes des actifs listés.','elliott':[{'actif':n,'phase':e['phase'],'key':e['key'],'conf':e['conf']} for n,e in items]}
