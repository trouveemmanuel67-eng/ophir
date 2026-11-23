"""Retracement de Fibonacci « base → ATH » sur bougies HEBDOMADAIRES clôturées, CORPS de bougie uniquement (jamais les mèches).

Règle d'Emmanuel (corrigée le 16/11/2026) : le retracement est tracé de la bougie la plus basse depuis l'existence du graphique
jusqu'à la plus haute. Plus le cours est bas dans le retracement, plus le critère pousse à l'achat ; près de l'ATH il est négatif.

Méthode (déterministe, sans données futures) :
 1. Corps : haut = max(ouverture, clôture), bas = min(ouverture, clôture) ; sans ouverture, ouverture = clôture précédente
    (même convention que elliott.bodies).
 2. Historique : la série du calcul est PRÉCÉDÉE de l'historique hebdomadaire le plus long disponible chez Yahoo Finance
    (data/fibo_max, téléchargé avec period1 = 1900 et interval = 1wk ; « range=max » renvoie des bougies trimestrielles).
    Seules les semaines antérieures à la première semaine de la série sont ajoutées ; les prix sont remis à l'échelle si
    la jonction diffère de plus de 2 % (ajustement de split différent) ; une semaine isolée aberrante (×2 ou ÷2 par rapport
    aux deux voisines, puis retour) est ignorée.
 3. ATH = plus haut des corps de TOUT l'historique ; BASE = plus bas des corps de TOUT l'historique (plus de règle de cycle).
    Si le plus bas historique est postérieur à l'ATH, la définition est conservée (cas signalé : base_apres_ath).
 4. Position r = (ATH − cours) / (ATH − base), cours = dernière clôture hebdomadaire. r = 0 à l'ATH, r = 100 % sur la base.
 5. Note (−100 … +100, + = achat), interpolation linéaire entre les niveaux de Fibonacci :
      0 % → −80 · 23,6 % → −40 · 38,2 % → 0 · 50 % → +40 · 61,8 % → +80 · 78,6 % → +100 · 100 % → +80
    au-delà de 100 % (impossible avec la base historique, conservé par sécurité) : de +80 à +20 jusqu'à 110 %, puis +20.

Règle du 23/11/2026 (investissement long terme, t310u) :
  La composante Fibonacci de l'AV (15 %) n'utilise plus le seul retracement
  du dernier mouvement, ni le seul retracement historique. Elle combine :
    — 2/3  retracement du plus bas historique au plus haut historique
      (corps hebdo, semaines clôturées), en priorité les ancres de
      /workspace/invest/fibo_historique_2026-11-23.json lorsqu'elles existent,
      sinon le calcul Yahoo (data/fibo_max) déjà en place ;
    — 1/3  retracement du dernier mouvement : plus haut des corps des
      52 dernières semaines clôturées, et plus bas des corps sur les
      52 semaines qui précèdent ce sommet (inclus).
  Si l'une des deux lectures manque, on retient l'autre. Le poids total
  du critère reste 15 %.
"""
import math, os, json, statistics as st, urllib.parse, datetime as D
from zoneinfo import ZoneInfo
import elliott as E
import yahoo_week as YW

LEVELS=[0,.236,.382,.5,.618,.786,1.0]
PTS=[(0,-80),(.236,-40),(.382,0),(.5,40),(.618,80),(.786,100),(1.0,80),(1.1,20)]
RULE_TXT=("Retracement de Fibonacci pour l'investissement long terme (23/11/2026) : "
 "note = 2/3 retracement historique (plus bas historique → plus haut historique, corps des bougies hebdomadaires clôturées, "
 "ancres de fibo_historique_2026-11-23.json si disponibles, sinon historique maximal Yahoo) "
 "+ 1/3 retracement du dernier mouvement (plus haut des 52 dernières semaines, plus bas des 52 semaines précédant ce sommet). "
 "Position r = (haut − cours) / (haut − base). "
 "Note interpolée : 0 % −80 ; 23,6 % −40 ; 38,2 % 0 ; 50 % +40 ; 61,8 % +80 ; 78,6 % +100 ; 100 % +80. Poids total du critère : 15 %.")
NAME="Retracement de Fibonacci (historique + dernier mouvement, corps)"
f1=lambda x,n=1:f"{x:.{n}f}".replace('.',',')
lv=lambda l:('%g'%round(l*100,1)).replace('.',',')

def note_of(r):
    if r<=0: return float(PTS[0][1])
    for (a,va),(b,vb) in zip(PTS,PTS[1:]):
        if r<=b: return va+(vb-va)*(r-a)/(b-a)
    return 20.0

def zone(r):
    if r>1: return 'sous la base (structure cassée)'
    if r<=0: return "à l'ATH"
    for a,b in zip(LEVELS,LEVELS[1:]):
        if r<=b: return f"entre {lv(a)} % et {lv(b)} %"
    return '100 %'

MAXDIR=os.path.join(os.path.dirname(os.path.abspath(__file__)),'..','data','fibo_max')
PREFIX_LOG={}

HIST_JSON='/workspace/invest/fibo_historique_2026-11-23.json'
_HIST_IDX=None
LOOKBACK_MVT=52
POIDS_HIST, POIDS_MVT=2.0, 1.0  # 2/3 historique, 1/3 dernier mouvement

def _hist_index():
    """Index symbole / yahoo / ticker → ancres ATL–ATH du fichier historique."""
    global _HIST_IDX
    if _HIST_IDX is not None:
        return _HIST_IDX
    _HIST_IDX={}
    if not os.path.exists(HIST_JSON):
        return _HIST_IDX
    try:
        raw=json.load(open(HIST_JSON))
    except Exception:
        return _HIST_IDX
    for a in raw.get('actifs') or []:
        if not isinstance(a, dict):
            continue
        bas=(a.get('plus_bas_historique') or {})
        haut=(a.get('plus_haut_historique') or {})
        if bas.get('valeur') is None or haut.get('valeur') is None:
            continue
        if a.get('historique_trop_court') or a.get('repere_sans_fibo'):
            continue
        rec={
            'symbole':a.get('symbole'),
            'base':float(bas['valeur']),
            'base_date':(bas.get('date') or '')[:10] or None,
            'ath':float(haut['valeur']),
            'ath_date':(haut.get('date') or '')[:10] or None,
            'sens':a.get('sens') or 'bas→haut',
            'source':a.get('source'),
            'fiabilite':a.get('fiabilite'),
            'incertain':bool(a.get('incertain')),
        }
        if rec['ath']<=rec['base']:
            continue
        keys=[a.get('symbole'), a.get('symbole_yahoo')]
        if a.get('symbole') and ':' in a['symbole']:
            keys.append(a['symbole'].split(':',1)[1])
        for k in keys:
            if k and k not in _HIST_IDX:
                _HIST_IDX[k]=rec
    return _HIST_IDX

def anchors_json(syms):
    idx=_hist_index()
    for s in (syms or []):
        if not s:
            continue
        if s in idx:
            return idx[s]
        if isinstance(s, str) and ':' in s:
            tail=s.split(':',1)[1]
            if tail in idx:
                return idx[tail]
    return None

def analyse_dernier(o,c,ds=None):
    """Retracement du dernier mouvement (corps hebdo, 52 semaines).

    Sommet = plus haut des corps des 52 dernières semaines clôturées.
    Base = plus bas des corps sur les 52 semaines qui s'achèvent à ce sommet.
    """
    n=len(c)
    if n<26:
        return {'ok':False,'note':None,'texte':'historique insuffisant pour le dernier mouvement (moins de 26 semaines)'}
    hi,lo=E.bodies(o,c)
    w=min(LOOKBACK_MVT, n)
    win=range(n-w, n)
    a=max(win, key=lambda i:hi[i]); ath=hi[a]
    start=max(0, a-LOOKBACK_MVT+1)
    b=min(range(start, a+1), key=lambda i:lo[i]); base=lo[b]
    if ath<=base:
        return {'ok':False,'note':None,'texte':'amplitude nulle sur le dernier mouvement'}
    px=c[-1]; r=(ath-px)/(ath-base)
    d=lambda i:ds[i] if ds else None
    return {'ok':True,'r':round(r,4),'note':round(note_of(r),1),'zone':zone(r),'broken':r>1,
            'base':round(base,6),'base_i':b,'base_date':d(b),
            'ath':round(ath,6),'ath_i':a,'ath_date':d(a),'cours':px,
            'debut':d(start),'n':w,'lookback':LOOKBACK_MVT,
            'niveaux':{f"{lv(l)} %":round(ath-l*(ath-base),6) for l in LEVELS},
            'kind':'dernier_mouvement'}

def friday(iso):
    x=D.date.fromisoformat(iso[:10]); return x+D.timedelta(days=(4-x.weekday())%7) if x.weekday()<=4 else x-D.timedelta(days=x.weekday()-4)
def long_weekly(sym):
    """[(vendredi ISO, ouverture|None, clôture)] de l'historique Yahoo maximal (data/fibo_max), même découpage que ind_core.yweekly"""
    p=os.path.join(MAXDIR,urllib.parse.quote(sym,safe='')+'.json')
    if not os.path.exists(p): return None,None
    bars,meta=YW.parse_yahoo_weekly(p)
    # retracement sur semaines clôturées uniquement (la barre live n'entre pas dans la base / l'ATH)
    rows=[(b['date'], b['open'] if (b['open'] and b['open']>0) else None, b['close']) for b in bars if b['closed'] and b['close'] and b['close']>0]
    return rows, meta
def _despike(rows):
    out=[];drop=[]
    for i,r in enumerate(rows):
        if 0<i<len(rows)-1:
            a,b,c=rows[i-1][2],r[2],rows[i+1][2]
            if (b>2*a and b>2*c) or (b<a/2 and b<c/2): drop.append(r[0]); continue
        out.append(r)
    return out,drop
def prefix(sym,ds0,c0=None):
    """Semaines de l'historique maximal ANTÉRIEURES à la première semaine (ds0) de la série du calcul : (ouvertures, clôtures, dates)."""
    if not sym: return None
    rows,meta=long_weekly(sym)
    info={'sym':sym,'serie_debut':ds0,'max_debut':rows[0][0] if rows else None,'ajout':0,'echelle':1.0,'aberrantes':[]}
    PREFIX_LOG[sym]=info
    if not rows: info['texte']='historique maximal absent'; return None
    f0=friday(ds0).isoformat()
    rows,info['aberrantes']=_despike(rows)
    pre=[r for r in rows if r[0]<f0]
    if not pre: return None
    k=1.0
    if c0:
        j=[r for r in rows if r[0]>=f0][:1]
        if j and j[0][0]==f0 and j[0][2]>0:
            k=c0/j[0][2]
            if abs(k-1)<=.02: k=1.0
    info['ajout']=len(pre); info['echelle']=round(k,6)
    return ([None if r[1] is None else r[1]*k for r in pre],[r[2]*k for r in pre],[r[0] for r in pre])

def fix_splits(o,c):
    """Division non ajustée dans les données (saut ×3 ou ÷3 d'une semaine sur l'autre, nouveau niveau conservé 4 semaines) :
    les semaines antérieures sont remises à l'échelle du nouveau niveau, comme sur un graphique ajusté des divisions."""
    c=list(c); o=list(o) if o is not None else None; fixes=[]
    for i in range(len(c)-1,0,-1):
        k=c[i]/c[i-1] if c[i-1] else 1
        if (k>3 or k<1/3) and all(1/2<c[j]/c[i]<2 for j in range(i,min(len(c),i+5))):
            fixes.append((i,k))
            for j in range(i):
                c[j]*=k
                if o is not None and o[j] is not None: o[j]*=k
            if o is not None and o[i] is not None and not (c[i]/2<o[i]<c[i]*2): o[i]=None
    return o,c,fixes
def clean_opens(o,c):
    """ouverture aberrante (≤ 0, ou hors de [÷2 ; ×2] de la clôture précédente ET de la clôture) → ignorée (ouverture = clôture précédente)"""
    if o is None: return None
    out=list(o)
    for i,x in enumerate(out):
        if x is None: continue
        ref=[v for v in (c[i-1] if i else None,c[i]) if v]
        if x<=0 or (ref and all(x<v/2 or x>v*2 for v in ref)): out[i]=None
    return out
def analyse(o,c,ds=None,pre=None,adjust_splits=True,sym=None,syms=None,combine=True):
    """o, c : ouvertures / clôtures hebdomadaires CLÔTURÉES (o peut être None) ; ds : dates ISO ; pre = prefix(...) (historique plus ancien).
    adjust_splits : correction des divisions d'actions (sauts ×3 / ÷3). À désactiver sur les crypto, où un tel saut est un mouvement de marché, pas une division.
    sym / syms : identifiants (TV, Yahoo) pour accrocher les ancres historiques du JSON.
    combine : si vrai (défaut), la note fusionne retracement historique (2/3) et dernier mouvement (1/3)."""
    if pre:
        o=list(pre[0])+(list(o) if o is not None else [None]*len(c)); c=list(pre[1])+list(c); ds=list(pre[2])+list(ds) if ds else None
    n=len(c)
    if n<52: return {'ok':False,'note':None,'texte':'historique insuffisant (moins de 52 semaines)'}
    if adjust_splits:
        o,c,fixes=fix_splits(o,c)
    else:
        fixes=[]
    o=clean_opens(o,c)
    hi,lo=E.bodies(o,c)
    a=max(range(n),key=lambda i:hi[i]); ath=hi[a]
    b=min(range(n),key=lambda i:lo[i]); base=lo[b]
    if ath<=base: return {'ok':False,'note':None,'texte':'amplitude nulle entre base et ATH'}
    px=c[-1]; r=(ath-px)/(ath-base)
    d=lambda i:ds[i] if ds else None
    hist={
        'ok':True,'r':round(r,4),'note':round(note_of(r),1),'zone':zone(r),'broken':r>1,
        'base':round(base,6),'base_i':b,'base_date':d(b),
        'ath':round(ath,6),'ath_i':a,'ath_date':d(a),'cours':px,
        'base_apres_ath':b>a,
        'splits_corriges':[(ds[i] if ds else i,round(k,4)) for i,k in fixes],
        'debut':d(0),'n':n,
        'niveaux':{f"{lv(l)} %":round(ath-l*(ath-base),6) for l in LEVELS},
        'source_historique':'yahoo_fibo_max',
    }
    keys=[]
    for s in ([sym] if sym else [])+(list(syms) if syms else []):
        if s and s not in keys:
            keys.append(s)
    anc=anchors_json(keys)
    if anc:
        b2,a2=anc['base'],anc['ath']
        if a2>b2:
            r2=(a2-px)/(a2-b2)
            hist.update({
                'r':round(r2,4),'note':round(note_of(r2),1),'zone':zone(r2),'broken':r2>1,
                'base':round(b2,6),'base_date':anc.get('base_date') or hist['base_date'],
                'ath':round(a2,6),'ath_date':anc.get('ath_date') or hist['ath_date'],
                'base_apres_ath':bool(anc.get('sens')=='haut→bas'),
                'niveaux':{f"{lv(l)} %":round(a2-l*(a2-b2),6) for l in LEVELS},
                'source_historique':'fibo_historique_json',
                'sens':anc.get('sens'),
                'fiabilite':anc.get('fiabilite'),
            })
    if not combine:
        return hist
    der=analyse_dernier(o,c,ds)
    hist['historique']={k:hist.get(k) for k in ('r','note','zone','base','base_date','ath','ath_date','source_historique')}
    hist['dernier']=({k:der.get(k) for k in ('ok','r','note','zone','base','base_date','ath','ath_date','lookback')} if der else None)
    hist['note_historique']=hist['note']
    hist['note_dernier']=der.get('note') if der and der.get('ok') else None
    notes=[]
    weights=[]
    if hist.get('note') is not None:
        notes.append(float(hist['note'])); weights.append(POIDS_HIST)
    if hist['note_dernier'] is not None:
        notes.append(float(hist['note_dernier'])); weights.append(POIDS_MVT)
    if notes:
        hist['note']=round(sum(n*w for n,w in zip(notes,weights))/sum(weights),1)
        hist['mix']='2/3 historique + 1/3 dernier mouvement' if len(notes)==2 else ('historique seul' if hist.get('note_historique') is not None and hist['note_dernier'] is None else 'dernier mouvement seul')
    return hist
def pfmt(x):
    ax=abs(x); return f1(x,4 if ax<1 else 2 if ax<1000 else 0)

def valeur(f):
    if not f.get('ok'): return f['texte']
    hist=f"Cours à {f1(f['r']*100)} % du retracement historique ({f['zone']}) · base {pfmt(f['base'])}"+(f" ({f['base_date']})" if f.get('base_date') else '')+f" → ATH {pfmt(f['ath'])}"+(f" ({f['ath_date']})" if f.get('ath_date') else '')+" · corps hebdo"
    if f.get('source_historique'):
        hist+=" · source "+str(f['source_historique'])
    hist+=" · historique depuis "+str(f.get('debut') or '?')[:4]
    if f.get('base_apres_ath'):
        hist+=" · plus bas historique postérieur à l'ATH"
    der=f.get('dernier') or {}
    if der.get('ok'):
        hist+=(f" · dernier mouvement (52 s.) : {f1(der['r']*100)} % ({der.get('zone')}) "
               f"de {pfmt(der['base'])}"+(f" ({der['base_date']})" if der.get('base_date') else '')+
               f" à {pfmt(der['ath'])}"+(f" ({der['ath_date']})" if der.get('ath_date') else ''))
    if f.get('note_historique') is not None and f.get('note_dernier') is not None:
        hist+=f" · note 2/3 hist. ({f['note_historique']:+.0f}) + 1/3 mvt ({f['note_dernier']:+.0f}) = {f['note']:+.0f}"
    return hist

def comp(f,poids=.15):
    return {'nom':NAME,'poids':poids,'valeur':valeur(f),'note':f.get('note'),'regle':RULE_TXT,
            'fibo':{k:f.get(k) for k in ('r','zone','base','base_date','ath','ath_date','broken')} if f.get('ok') else None}

def comp_multi(items,poids=.15):
    """items = [(nom de l'actif, analyse)] : note moyenne des actifs disponibles"""
    ok=[(n,f) for n,f in items if f.get('ok')]
    if not ok: return {'nom':NAME,'poids':poids,'valeur':'non disponible','note':None,'regle':RULE_TXT}
    return {'nom':NAME,'poids':poids,'valeur':' · '.join(f"{n} : {f1(f['r']*100)} % ({f['note']:+.0f})".replace('.',',') for n,f in ok)+' · corps des bougies hebdomadaires',
            'note':sum(f['note'] for _,f in ok)/len(ok),'regle':RULE_TXT+' Moyenne des notes des actifs listés.',
            'fibo':[{'actif':n,'r':f['r'],'base':f['base'],'base_date':f['base_date'],'ath':f['ath'],'ath_date':f['ath_date']} for n,f in ok]}
