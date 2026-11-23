"""Critères « Charte graphique » (20 %) et « Divergence RSI / MACD weekly » (10 %) de la note APEX achat / vente.
Bougies HEBDOMADAIRES clôturées uniquement, calcul déterministe sans données futures.

Charte graphique (−100 … +100, + = achat) = structure d'Elliott (60 %) + figures chartistes validées (40 %),
moyenne pondérée des seuls éléments détectés ; rien de détecté → 0.
 · Structure d'Elliott lue sur les MÈCHES (plus hauts / plus bas hebdomadaires : pour Elliott les mèches sont acceptées ;
   les corps ne servent qu'aux tracés et au Fibonacci). Barème × (0,5 + 0,5 × confiance) :
   vague 5 en cours avec nouveau sommet au-dessus de la 3 −100 ; vague 5 en cours sans nouveau sommet −60 ;
   vague 5 terminée, A en cours −100 ; B −70 ; C encore loin de sa fin −50 ; C avancée −20 ;
   fin de 4 proche +60, confirmée +80 ; fin de C proche +70, confirmée +100 ; C terminée, nouvelle impulsion +50.
   Autres phases (1, 2, 3, 4 en cours, début de 5, impulsion baissière, indéterminé) : pas de signal de structure.
 · Figures chartistes (dossier « Figures chartistes weekly ») : épaule-tête-épaule, doubles sommets/creux, validés par
   une CLÔTURE hebdomadaire au-delà de la ligne de cou, dans les 8 dernières semaines, et non réintégrés
   (épaule-tête-épaule −90 / inversée +90 ; double sommet −70 / double creux +70).
 · Biseaux sur les CORPS hebdomadaires (18/11/2026) : deux droites convergentes, au moins 2 touches de chaque côté.
   Biseau montant en cours −70 ; biseau montant cassé par le bas −80 ; biseau descendant cassé par le haut +60.
   Un biseau montant en cours ou cassé l'emporte sur une figure haussière de la même semaine. Le biseau descendant
   en cours n'est pas anticipé (note seulement après cassure haussière).
Divergence RSI / MACD weekly (±100 ou non comptée, 10 %) : deux derniers sommets (ou creux) de clôture confirmés
sur 52 semaines, le plus récent dans les 13 dernières semaines. RSI : prix plus haut et RSI 14 plus bas (≥ 2 points)
→ −100 ; prix plus bas et RSI plus haut → +100. MACD (ligne 12/26) : même logique de prix, la ligne MACD fait un
plus bas plus haut (haussière) ou un plus haut plus bas (baissière). Sans divergence RSI ni MACD : note None,
poids redistribué, aucun bonus. Si les deux sont présentes, moyenne des notes.
Lectures manuelles (data/lectures_manuelles.json) : prioritaires sur la détection automatique, pour la dernière bougie.
"""
import json, os
import elliott as E
W_CH=.20; W_DV=.10
MAN_PATH=os.path.join(os.path.dirname(os.path.abspath(__file__)),'..','data','lectures_manuelles.json')
try: MAN=json.load(open(MAN_PATH))['lectures']
except Exception: MAN={}
def manuel(syms):
    for s in (syms or []):
        if not s: continue
        for k,v in MAN.items():
            if s==k or s in v.get('alias',[]): return k,v
    return None
f0=lambda x:f"{x:+.0f}"
fd=lambda d:f"{d[8:10]}/{d[5:7]}/{d[:4]}"
f2=lambda x:f"{x:,.2f}".replace(',',' ').replace('.',',')
RULE_CH=("Structure d'Elliott lue sur les mèches hebdomadaires (60 %) et figures chartistes weekly (40 %), "
 "moyenne des éléments détectés, 0 si rien n'est détecté. Structure, barème × (0,5 + 0,5 × confiance) : vague 5 avec nouveau sommet au-dessus de la 3, "
 "ou vague 5 terminée (A en cours) −100 ; vague 5 sans nouveau sommet −60 ; B −70 ; C loin de sa fin −50 ; C avancée −20 ; fin de 4 +60 (confirmée +80) ; "
 "fin de C +70 (confirmée +100) ; C terminée et nouvelle impulsion +50. Figures validées par une clôture hebdomadaire au-delà de la ligne de cou "
 "dans les 8 dernières semaines et non réintégrées : épaule-tête-épaule −90 (inversée +90) ; double sommet −70 (double creux +70). "
 "Biseaux tracés sur les corps hebdomadaires, au moins 2 touches de chaque côté, droites convergentes : biseau montant en cours −70 ; "
 "biseau montant cassé par le bas −80 ; biseau descendant cassé par le haut +60. Un biseau montant en cours ou cassé l'emporte sur une figure haussière "
 "de la même semaine. Une lecture manuelle d'Emmanuel remplace la détection automatique. Lecture automatique, à confirmer sur TradingView.")
RULE_DV=("Deux derniers sommets (ou creux) de clôture hebdomadaire confirmés sur 52 semaines, le plus récent dans les 13 dernières semaines. "
 "RSI 14 : prix plus haut et RSI plus bas d'au moins 2 points → divergence baissière −100 ; prix plus bas et RSI plus haut → haussière +100. "
 "Ligne MACD 12/26 : même logique de prix, plus haut plus bas du MACD (baissière −100) ou plus bas plus haut (haussière +100). "
 "Sans divergence RSI ni MACD, le critère n'est pas compté (note nulle, aucun bonus) et son poids est redistribué sur les autres. "
 "Si les deux divergences sont présentes, la note est la moyenne des deux.")
NOM_DIV="Divergence RSI / MACD weekly"
SMAP={'a':-100,'fin_a':-100,'b':-70,'c':60,'c_mid':60,'fin_2':60,'fin_2_conf':80,'fin_4':60,'fin_4_conf':80,'fin_c':70,'fin_c_conf':100}
STXT={'a':"vague 5 terminée, vague A en cours (zone rouge)",'fin_a':"fin de vague A (zone rouge)",'b':"vague B en cours (zone rouge)",
      'c':"vague C en cours (zone verte)",'c_mid':"vague C avancée (zone verte)",
      'fin_2':"fin de vague 2 proche",'fin_2_conf':"fin de vague 2 confirmée",
      'fin_4':"fin de vague 4 proche",'fin_4_conf':"fin de vague 4 confirmée",'fin_c':"fin de vague C proche",'fin_c_conf':"fin de vague C confirmée"}

def wicks(hl,ds,o,c):
    """hauts / bas hebdomadaires : mèches si hl = {date: (haut, bas)} est fourni, sinon corps de bougie."""
    bh,bl=E.bodies(o,c); hi=[];lo=[]
    for i,d in enumerate(ds):
        x=(hl or {}).get(d)
        if x and x[0] and x[1] and x[0]>=max(bh[i],bl[i])*0.999 and x[1]<=min(bh[i],bl[i])*1.001: hi.append(x[0]); lo.append(x[1])
        else: hi.append(bh[i]); lo.append(bl[i])
    return hi,lo

def structure(hi,lo,c):
    e=E.analyse_hl(hi,lo,c); k=e['key']; P=e.get('points') or []
    if k=='w5' and len(P)>=6:
        nh=P[5]>P[3]; base=-100 if nh else -60
        t="vague 5 en cours avec nouveau sommet au-dessus de la vague 3" if nh else "vague 5 en cours, sans nouveau sommet au-dessus de la 3"
    elif k in SMAP: base=SMAP[k]; t=STXT[k]
    else: return None
    return {'note':round(base*(0.5+0.5*e['conf']),1),'texte':f"Structure sur mèches : {t} (confiance {round(e['conf']*100)} %)",'key':k,'idx':e.get('idx',[])}

def pivots(v,k):
    n=len(v); H=[];L=[]
    for i in range(k,n-k):
        w=v[i-k:i+k+1]
        if v[i]==max(w) and v[i]>v[i-1]: H.append(i)
        if v[i]==min(w) and v[i]<v[i-1]: L.append(i)
    return H,L

RECENT=8
def _valid_break(c,start,lvl,down):
    """première clôture après start qui casse lvl(j) ; renvoie j si récente et non réintégrée"""
    n=len(c)
    for j in range(start+1,n):
        if (c[j]<lvl(j)) if down else (c[j]>lvl(j)):
            if n-1-j>RECENT: return None
            last=n-1
            if down and c[last]>lvl(last)*1.02: return None
            if (not down) and c[last]<lvl(last)*0.98: return None
            return j
    return None


def _corps(o,c):
    """Haut et bas des corps hebdomadaires (max/min ouverture-clôture). Sans ouverture, le corps vaut la clôture."""
    if o is None:
        return list(c), list(c)
    bh=[max(a,b) if a is not None else b for a,b in zip(o,c)]
    bl=[min(a,b) if a is not None else b for a,b in zip(o,c)]
    return bh, bl

# notes des biseaux (18/11/2026) — pondérées dans les 20 % Charte (40 % figures)
NOTE_BISEAU_MONTANT_COURS=-70
NOTE_BISEAU_MONTANT_CASSE=-80
NOTE_BISEAU_DESC_CASSE=60

def biseaux_corps(c,ds,o=None):
    """Détecte un biseau montant ou descendant sur les corps hebdo (au moins 2 touches de chaque côté).
    Pairwise sur les pivots de corps, dernière barre admise comme toucher de la borne haute ou basse.
    Fenêtre 16 à 80 semaines, dernier toucher dans les 8 dernières semaines.
    Un biseau montant en cours ou cassé l'emporte sur un biseau descendant cassé plus ancien.
    Retourne un dict figure ou None."""
    n=len(c)
    if n<20: return None
    bh,bl=_corps(o,c)
    look=max(0,n-80)
    Hh,_=pivots(bh,2); _,Ll=pivots(bl,2)
    H=[i for i in Hh if i>=look]; L=[i for i in Ll if i>=look]
    e=n-1
    if (not H or e-H[-1]>=2) and bh[e]>=max(bh[max(look,e-5):e] or [bh[e]])*0.98:
        H.append(e)
    if (not L or e-L[-1]>=2) and bl[e]<=min(bl[max(look,e-5):e] or [bl[e]])*1.02:
        L.append(e)
    cands=[]
    for ia in range(len(H)):
        for ib in range(ia+1,len(H)):
            a,b=H[ia],H[ib]
            if not (6<=b-a<=70): continue
            us=(bh[b]-bh[a])/(b-a); ub=bh[a]-us*a
            U=lambda i,us=us,ub=ub:us*i+ub
            for ip in range(len(L)):
                for iq in range(ip+1,len(L)):
                    p,q=L[ip],L[iq]
                    if not (6<=q-p<=70): continue
                    s0,s1=min(a,p),max(b,q)
                    if not (16<=s1-s0+1<=80): continue
                    if s1<n-8: continue
                    # les deux droites doivent se chevaucher dans le temps
                    if max(a,b)<min(p,q) or max(p,q)<min(a,b): continue
                    ds_=(bl[q]-bl[p])/(q-p); db=bl[p]-ds_*p
                    Lw=lambda i,ds_=ds_,db=db:ds_*i+db
                    w0=U(s0)-Lw(s0); w1=U(s1)-Lw(s1)
                    if not (w0>0 and 0<w1<=0.85*w0): continue
                    kind=None
                    if us>0 and ds_>0 and ds_>us*1.05:
                        kind='rising'
                    elif us<0 and ds_<0 and us<ds_*1.05:
                        kind='falling'
                    if not kind: continue
                    span=s1-s0+1
                    viol=sum(1 for i in range(s0,s1+1) if bh[i]>U(i)*1.03 or bl[i]<Lw(i)*0.97)
                    if viol>max(2,0.12*span): continue
                    th=sum(1 for i in H if s0<=i<=s1 and abs(bh[i]-U(i))/max(abs(U(i)),1e-9)<=0.025)
                    tl=sum(1 for i in L if s0<=i<=s1 and abs(bl[i]-Lw(i))/max(abs(Lw(i)),1e-9)<=0.025)
                    if th<2 or tl<2: continue
                    Ue,Le=U(e),Lw(e)
                    last_c=c[e]
                    broken_dn=any(c[i]<Lw(i)*0.98 for i in range(max(s1,n-8),n)) and last_c<Le*1.02
                    broken_up=any(c[i]>U(i)*1.02 for i in range(max(s1,n-8),n)) and last_c>Ue*1.02
                    inside=last_c>=Le*0.98 and last_c<=Ue*1.05
                    status=None
                    if kind=='rising' and broken_dn:
                        status='broken_dn'
                    elif kind=='rising' and inside and max(a,b)>=n-8 and Ue>Le:
                        status='in_progress'
                    elif kind=='falling' and broken_up and max(a,b,p,q)>=n-12:
                        status='broken_up'
                    else:
                        continue
                    conv=1-w1/w0
                    prox=1-abs(last_c-(Ue if kind=='rising' else Le))/max(abs(Ue if kind=='rising' else Le),1)
                    score=conv*2+th+tl+prox+(1 if status!='in_progress' else 0)
                    cands.append(dict(kind=kind,status=status,s0=s0,s1=s1,a=a,b=b,p=p,q=q,th=th,tl=tl,
                                      Ue=Ue,Le=Le,w0=w0,w1=w1,score=score,viol=viol))
    if not cands: return None
    rising=[x for x in cands if x['kind']=='rising']
    falling=[x for x in cands if x['kind']=='falling' and x['status']=='broken_up']
    pool=rising or falling
    w=max(pool,key=lambda x:(x['score'],x['s1'],-x['s0']))
    if w['status']=='in_progress':
        note=NOTE_BISEAU_MONTANT_COURS
        etat='en cours'
        ev='figure baissière, le cours touche ou reste sous la borne haute'
    elif w['status']=='broken_dn':
        note=NOTE_BISEAU_MONTANT_CASSE
        etat='cassé vers le bas'
        ev='cassure baissière confirmée'
    else:
        note=NOTE_BISEAU_DESC_CASSE
        etat='cassé vers le haut'
        ev='cassure haussière confirmée'
    typ='montant' if w['kind']=='rising' else 'descendant'
    txt=(f"biseau {typ} {etat} (corps hebdo, {w['s1']-w['s0']+1} semaines, "
         f"{w['th']} touches hautes {fd(ds[w['a']])} / {fd(ds[w['b']])}, "
         f"{w['tl']} touches basses {fd(ds[w['p']])} / {fd(ds[w['q']])} ; "
         f"clôture {f2(c[e])} , borne haute {f2(w['Ue'])}, borne basse {f2(w['Le'])} ; {ev})")
    # date d'événement : dernière barre (en cours) ou dernier toucher (cassure)
    j=e if w['status']=='in_progress' else w['s1']
    prio=3 if w['kind']=='rising' else 2
    return {'note':float(note),'texte':'Figure : '+txt,'date':ds[j],'idx':j,'prio':prio,'kind':'wedge',
            'wedge':{k:w[k] for k in('kind','status','s0','s1','th','tl','Ue','Le')}}

def figures(c,ds,o=None):
    n=len(c); lo0=max(0,n-130); found=[]
    H,L=pivots(c,3); H=[i for i in H if i>=lo0]; L=[i for i in L if i>=lo0]
    # doubles sommets / creux
    for a,b in zip(H,H[1:]):
        if 4<=b-a<=52 and abs(c[b]/c[a]-1)<=.03:
            nk=min(c[a:b+1])
            if min(c[a],c[b])/nk-1>=.06:
                j=_valid_break(c,b,lambda _:nk,True)
                if j is not None and max(c[b:])<=max(c[a],c[b]): found.append((j,-70,f"double sommet ({f2(c[a])} / {f2(c[b])}) validé par la clôture du {fd(ds[j])} sous la ligne de cou {f2(nk)}"))
    for a,b in zip(L,L[1:]):
        if 4<=b-a<=52 and abs(c[b]/c[a]-1)<=.03:
            nk=max(c[a:b+1])
            if nk/max(c[a],c[b])-1>=.06:
                j=_valid_break(c,b,lambda _:nk,False)
                if j is not None and min(c[b:])>=min(c[a],c[b]): found.append((j,70,f"double creux ({f2(c[a])} / {f2(c[b])}) validé par la clôture du {fd(ds[j])} au-dessus de la ligne de cou {f2(nk)}"))
    # épaule-tête-épaule et inversée
    for s1,t,s2 in zip(H,H[1:],H[2:]):
        if 8<=s2-s1<=104 and c[t]>max(c[s1],c[s2])*1.03 and abs(c[s1]/c[s2]-1)<=.10:
            j1=min(range(s1,t+1),key=lambda q:c[q]); j2=min(range(t,s2+1),key=lambda q:c[q])
            sl=(c[j2]-c[j1])/(j2-j1) if j2!=j1 else 0; neck=lambda q,j1=j1,sl=sl:c[j1]+sl*(q-j1)
            j=_valid_break(c,s2,neck,True)
            if j is not None and max(c[s2:])<=c[t]: found.append((j,-90,f"épaule-tête-épaule (tête {f2(c[t])}) validée par la clôture du {fd(ds[j])} sous la ligne de cou"))
    for s1,t,s2 in zip(L,L[1:],L[2:]):
        if 8<=s2-s1<=104 and c[t]<min(c[s1],c[s2])/1.03 and abs(c[s1]/c[s2]-1)<=.10:
            j1=max(range(s1,t+1),key=lambda q:c[q]); j2=max(range(t,s2+1),key=lambda q:c[q])
            sl=(c[j2]-c[j1])/(j2-j1) if j2!=j1 else 0; neck=lambda q,j1=j1,sl=sl:c[j1]+sl*(q-j1)
            j=_valid_break(c,s2,neck,False)
            if j is not None and min(c[s2:])>=c[t]: found.append((j,90,f"épaule-tête-épaule inversée (tête {f2(c[t])}) validée par la clôture du {fd(ds[j])} au-dessus de la ligne de cou"))
    # biseaux sur les corps hebdomadaires (en cours ou cassés) — 18/11/2026
    wg=biseaux_corps(c,ds,o)
    if wg:
        found.append((wg['idx'],wg['note'],wg['texte'][9:] if wg['texte'].startswith('Figure : ') else wg['texte'],wg['prio']))
    if not found: return None
    j,nt,tx,pr=max((x if len(x)==4 else (x[0],x[1],x[2],1) for x in found), key=lambda x:(x[0],x[3],abs(x[1])))
    return {'note':float(nt),'texte':'Figure : '+tx,'date':ds[j],'prio':pr}

def divergence(c,ds,r,wave_idx=()):
    n=len(c); H,L=pivots(c,2); out=[]
    lo0=n-52
    H=[i for i in H if i>=lo0 and r[i] is not None]; L=[i for i in L if i>=lo0 and r[i] is not None]
    near=lambda i:any(abs(i-w)<=2 for w in wave_idx)
    if len(H)>=2:
        a,b=H[-2],H[-1]
        if n-1-b<=13 and 3<=b-a<=40 and c[b]>c[a] and r[b]<=r[a]-2 and r[a]>=50 and max(c[b:])<=c[b]:
            out.append((b,-100,f"divergence baissière : clôture plus haute ({f2(c[a])} le {fd(ds[a])} → {f2(c[b])} le {fd(ds[b])}) mais RSI plus bas ({r[a]:.0f} → {r[b]:.0f})".replace('.',',')+(' sur un sommet de vague' if near(b) else '')))
    if len(L)>=2:
        a,b=L[-2],L[-1]
        if n-1-b<=13 and 3<=b-a<=40 and c[b]<c[a] and r[b]>=r[a]+2 and r[a]<=50 and min(c[b:])>=c[b]:
            out.append((b,100,f"divergence haussière : clôture plus basse ({f2(c[a])} le {fd(ds[a])} → {f2(c[b])} le {fd(ds[b])}) mais RSI plus haut ({r[a]:.0f} → {r[b]:.0f})".replace('.',',')+(' sur un creux de vague' if near(b) else '')))
    if not out: return None
    b,nt,t=max(out); return {'note':float(nt),'texte':t[0].upper()+t[1:]}

def divergence_macd(c,ds,mline,wave_idx=()):
    """Divergence de la ligne MACD 12/26 vs clôtures, mêmes pivots et fenêtres que le RSI (52 / 13 semaines)."""
    n=len(c); H,L=pivots(c,2); out=[]
    lo0=n-52
    H=[i for i in H if i>=lo0 and i<len(mline) and mline[i] is not None]
    L=[i for i in L if i>=lo0 and i<len(mline) and mline[i] is not None]
    near=lambda i:any(abs(i-w)<=2 for w in wave_idx)
    if len(H)>=2:
        a,b=H[-2],H[-1]
        if n-1-b<=13 and 3<=b-a<=40 and c[b]>c[a] and mline[b]<mline[a] and max(c[b:])<=c[b]:
            out.append((b,-100,f"divergence MACD baissière : clôture plus haute ({f2(c[a])} le {fd(ds[a])} → {f2(c[b])} le {fd(ds[b])}) mais ligne MACD plus basse ({mline[a]:.2f} → {mline[b]:.2f})".replace('.',',')+(' sur un sommet de vague' if near(b) else '')))
    if len(L)>=2:
        a,b=L[-2],L[-1]
        if n-1-b<=13 and 3<=b-a<=40 and c[b]<c[a] and mline[b]>mline[a] and min(c[b:])>=c[b]:
            out.append((b,100,f"divergence MACD haussière : clôture plus basse ({f2(c[a])} le {fd(ds[a])} → {f2(c[b])} le {fd(ds[b])}) mais ligne MACD plus haute ({mline[a]:.2f} → {mline[b]:.2f})".replace('.',',')+(' sur un creux de vague' if near(b) else '')))
    if not out: return None
    b,nt,t=max(out); return {'note':float(nt),'texte':t[0].upper()+t[1:]}

def fusion_div(dv,dm):
    """Fusion RSI + MACD. Sans aucune divergence : note None, aucun bonus, poids redistribué."""
    if not dv and not dm:
        return {'note':None,'texte':"Aucune divergence RSI ni MACD récente : critère non compté, poids redistribué, aucun bonus"}
    if dv and not dm:
        return {'note':dv['note'],'texte':dv['texte']}
    if dm and not dv:
        return {'note':dm['note'],'texte':dm['texte']}
    return {'note':round((dv['note']+dm['note'])/2,1),'texte':dv['texte']+' · '+dm['texte']}

def analyse(c,ds,o=None,hl=None,r=None,syms=None,manual=True):
    """c, ds, o : clôtures, dates, ouvertures hebdomadaires CLÔTURÉES ; hl = {date: (haut, bas)} ; r = RSI 14 (calculé sinon)."""
    import ind_core as K
    if r is None:
        r=K.rsi(c)
    if len(c)<60:
        return {'charte':{'note':0.0,'texte':"Historique insuffisant : critère à 0",'manuel':None},'div':{'note':None,'texte':"Historique insuffisant"}}
    m=manuel(syms) if manual else None
    hi,lo=wicks(hl,ds,o,c)
    st=structure(hi,lo,c); fg=figures(c,ds,o)
    dv=divergence(c,ds,r,(st or {}).get('idx',[]))
    mline,sg,hist=K.macd_series(c)
    dm=divergence_macd(c,ds,mline,(st or {}).get('idx',[]))
    src='auto'
    if m:
        k,v=m; src='manuel'
        if 'structure' in v: st=v['structure']
        if 'figure' in v: fg=v['figure']
        if 'divergence' in v: dv=v['divergence']
    parts=[(x,w) for x,w in ((st,.6),(fg,.4)) if x and x.get('note') is not None]
    note=round(sum(x['note']*w for x,w in parts)/sum(w for _,w in parts),1) if parts else 0.0
    txt=' · '.join(x['texte'] for x,_ in parts) if parts else "Ni structure d'Elliott marquée ni figure chartiste validée : critère à 0"
    if m:
        k,v=m; txt=f"Lecture manuelle d'Emmanuel du {v.get('date','')} ({k}) : "+txt+(' · '+v['commentaire'] if v.get('commentaire') else '')
    else: txt+=' · lecture automatique, à confirmer sur TradingView'
    if not (m and 'divergence' in m[1]):
        dv=fusion_div(dv,dm)
    return {'charte':{'note':note,'texte':txt,'manuel':m[0] if m else None,'source':src,'structure':st and {'note':st['note'],'texte':st['texte']},'figure':fg},
            'div':{'note':(dv or {}).get('note'),'texte':((dv['texte'] if dv else "Aucune divergence RSI ni MACD récente : critère non compté, poids redistribué, aucun bonus")+(' (lecture manuelle)' if m and 'divergence' in m[1] else ''))}}

def comp(a,poids=W_CH):
    x=a['charte']; return {'nom':'Charte graphique (structure d’Elliott et figures chartistes weekly)','poids':poids,'valeur':x['texte'],'note':x['note'],'regle':RULE_CH,'charte':{k:x.get(k) for k in('source','manuel','structure','figure')}}
def comp_div(a,poids=W_DV):
    x=a['div']; return {'nom':NOM_DIV,'poids':poids,'valeur':x['texte'],'note':x['note'],'regle':RULE_DV,'facultatif':True}
def comp_multi(items,poids=W_CH):
    notes=[a['charte']['note'] for _,a in items]
    return {'nom':'Charte graphique (structure d’Elliott et figures chartistes weekly)','poids':poids,'valeur':' · '.join(f"{n} : {a['charte']['note']:+.0f}".replace('.',',') for n,a in items)+' · détail : '+' | '.join(f"{n} — {a['charte']['texte']}" for n,a in items),
            'note':sum(notes)/len(notes),'regle':RULE_CH+' Moyenne des notes des actifs listés.'}
def comp_div_multi(items,poids=W_DV):
    v=[(n,a['div']) for n,a in items if a['div']['note'] is not None]
    if not v: return {'nom':NOM_DIV,'poids':poids,'valeur':"Aucune divergence RSI ni MACD récente sur "+', '.join(n for n,_ in items)+" : critère non compté, poids redistribué",'note':None,'regle':RULE_DV,'facultatif':True}
    return {'nom':NOM_DIV,'poids':poids,'valeur':' | '.join(f"{n} : {d['texte']}" for n,d in v),'note':sum(d['note'] for _,d in v)/len(v),'regle':RULE_DV+' Moyenne des actifs où une divergence est détectée.','facultatif':True}

def elliott_manuel(e,syms):
    """remplace la lecture Elliott automatique par un comptage manuel prioritaire
    (data/elliott_overrides.json, sinon clé « elliott » de lectures_manuelles.json)."""
    import elliott_zones as EZ
    ov=EZ.apply_override(e,syms)
    if ov and ov.get('override'):
        return ov
    m=manuel(syms)
    if not m or not m[1].get('elliott'):
        if e:
            e=dict(e); e['zone']=EZ.zone_of(e.get('key'))
        return e
    k,v=m; key=v['elliott']['key']
    return {'key':key,'phase':E.PHASE[key],'conf':1.0,'note':float(E.BASE[key]),
            'texte':v['elliott'].get('texte') or (E.TXT[key]+f" (lecture manuelle d'Emmanuel du {v.get('date','')})"),
            'thr':None,'points':[],'idx':[],'manuel':True,'zone':EZ.zone_of(key)}

TXT_CRIT=("Charte graphique (20 %) : structure d'Elliott lue sur les mèches (vague 5 terminée, ou en cours avec un nouveau sommet au-dessus de la 3, "
 "fortement négative ; fin de vague 2, fin de vague 4 ou vague C positive) et figures chartistes weekly (épaule-tête-épaule, double sommet ou double creux, "
 "biseaux sur les corps : montant en cours −70, montant cassé par le bas −80, descendant cassé par le haut +60), 0 si rien n'est détecté ; "
 "une lecture manuelle d'Emmanuel (data/lectures_manuelles.json) remplace la détection automatique. "
 "Divergence RSI / MACD weekly (10 %) : −100 si une divergence baissière récente (RSI ou MACD) apparaît, +100 si elle est haussière ; "
 "sans divergence, critère non compté, aucun bonus, poids redistribué")
