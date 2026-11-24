"""Onglet MÉTAUX PRÉCIEUX -> data/metaux.json : indicateurs APEX par métal (contrats à terme continus Yahoo, référence DBC),
carte composite de l'onglet, listes « ETC principal + 5 instruments », séries des graphiques (prix USD / EUR depuis 2000, ratios,
or contre taux réel US, positions CFTC, records). Indices composites APEX, non officiels. Bougies hebdomadaires clôturées uniquement."""
import os as _os
_APEX_ROOT = _os.path.abspath(_os.environ.get('APEX_ROOT') or _os.path.join(_os.path.dirname(__file__), '..'))
import json, os, csv, bisect, urllib.parse, datetime as D, sys
from zoneinfo import ZoneInfo
R=_APEX_ROOT + '/'; sys.path.insert(0,R+'src'); import ind_core as K, revolut_rules as RV
B=R+'data/metaux/'; NOW=D.datetime.now(ZoneInfo('Europe/Paris'))
def J(p):
    try: return json.load(open(p))
    except Exception: return None
def mtime(p): return D.datetime.fromtimestamp(os.path.getmtime(p),ZoneInfo('Europe/Paris')).strftime('%Y-%m-%d %H:%M')
yf_=lambda s:B+'y_'+urllib.parse.quote(s,safe='')+'.json'
# fonctions de notation reprises de build_pays.py (santé financière, croissance prévue)
src=open(R+'src/build_pays.py').read(); exec(src[src.index('def raw(v)'):src.index('def wkly(s)')]); exec(src[src.index('HEALTH={'):src.index('def basket(')])
def wk(s):
    p=yf_(s)
    if not os.path.exists(p): return None,{}
    try: w,m=K.yweekly(p); return [x for x in w if x[2]],m
    except Exception: return None,{}
def tvv(s):
    code=s.split('.')[0]; suf=s.split('.')[-1] if '.' in s else ''
    ex={'DE':['XETR'],'L':['LSE'],'PA':['EURONEXT','Euronext Paris'],'AX':['ASX'],'JO':['JSE']}.get(suf,['NYSE','NASDAQ','AMEX'])
    for x in (J(B+f'tv/{s}.json') or []):
        if x.get('symbol')==code and (x.get('exchange') in ex or x.get('prefix') in ex):
            pre=x.get('prefix') or x.get('exchange'); pre='EURONEXT' if pre.startswith('Euronext') else pre
            return f'{pre}:{code}',x.get('description')
    return None,None
BW,BM=K.yweekly(yf_('DBC')); BEN={d:v for d,v,ok in BW if ok}; BN='DBC'
# 23/11/2026 · au moins 5 ETC physiques distincts (ISIN) par métal, hors CFD et ETP de futures.
# L'ETF de minières (G2X, SLVR/SILV, IS0E) n'entre pas dans ces 5.
# Palladium : seulement 3 ETC physiques européens à ISIN distincts (marché étroit).
MET=[('or','Or','GC=F','GLDA.DE',[('XAD5.DE','etc'),('8PSG.DE','etc'),('4GLD.DE','etc'),('IGLN.L','etc'),('PHGP.L','etc')],['NEM','AEM','B','FNV','KGC','AU','GFI','RGLD','NST.AX','EVN.AX']),
     ('argent','Argent','SI=F','XAD6.DE',[('8PSB.DE','etc'),('PHAG.L','etc'),('ISLN.L','etc')],['WPM','PAAS','HL','CDE','AG','FRES.L']),
     ('platine','Platine','PL=F','IPLT.L',[('8PSA.DE','etc'),('XPPT.DE','etc'),('XAD3.DE','etc'),('PHPT.AS','etc')],['SBSW','IMP.JO']),
     ('palladium','Palladium','PA=F','IPDM.L',[('8PSC.DE','etc'),('PHPD.AS','etc')],['SBSW','IMP.JO'])]
KIND={'etc':'ETC adossé au métal physique','etf':'ETF UCITS de minières','min':'Minière','spot':'Métal au comptant (Revolut)'}
# ISIN / frais / TV : justETF ou factsheet émetteur, 11/2026 ; table OMI XTB 24/09/2026 pour la dispo XTB.
# 8PSB = Invesco Physical Silver, pas un ETC platine.
ETC_META={
    'GLDA.DE': {'tv':'XETR:GLDA','isin':'FR0013416716','ter':0.12,'ter_note':'TER 0,12 % (justETF, 11/2026)','hedged':False},
    'XAD5.DE': {'tv':'XETR:XAD5','isin':'DE000A1E0HR8','ter':0.25,'ter_note':'TER 0,25 % (émetteur / justETF, 11/2026)','hedged':False},
    '8PSG.DE': {'tv':'XETR:8PSG','isin':'IE00B579F325','ter':0.12,'ter_note':'TER 0,12 % (Invesco / justETF, 2026)','hedged':False},
    '4GLD.DE': {'tv':'XETR:4GLD','isin':'DE000A0S9GB0','ter':0.36,'ter_note':'TER 0 % + frais administratifs / de garde 0,36 % (justETF, 11/2026)','hedged':False},
    'IGLN.L':  {'tv':'LSE:IGLN','isin':'IE00B4ND3602','ter':0.12,'ter_note':'TER 0,12 % (iShares / justETF, 2026)','hedged':False},
    'PHGP.L':  {'tv':'LSE:PHGP','isin':'JE00B1VS3770','ter':0.39,'ter_note':'TER 0,39 % (WisdomTree / justETF, 2026)','hedged':False},
    'XAD6.DE': {'tv':'XETR:XAD6','isin':'DE000A1E0HS6','ter':None,'ter_note':'ISIN DE000A1E0HS6 (table OMI XTB 24/09/2026)','hedged':False},
    '8PSB.DE': {'tv':'XETR:8PSB','isin':'IE00B43VDT70','ter':0.19,'ter_note':'TER 0,19 % (factsheet Invesco, même gamme que 8PSA)','hedged':False},
    'PHAG.L':  {'tv':'LSE:PHAG','isin':'JE00B1VS3333','ter':0.49,'ter_note':'TER 0,49 % (WisdomTree)','hedged':False},
    'ISLN.L':  {'tv':'LSE:ISLN','isin':'IE00B4NCWG09','ter':0.20,'ter_note':'TER 0,20 % (iShares, table OMI ISLN.UK 24/09/2026)','hedged':False},
    'IPLT.L':  {'tv':'LSE:IPLT','isin':'IE00B4LHWP62','ter':0.20,'ter_note':'TER 0,20 % (iShares, 20/11/2026)','hedged':False},
    '8PSA.DE': {'tv':'XETR:8PSA','isin':'IE00B40QP990','ter':0.19,'ter_note':'TER 0,19 % (factsheet Invesco)','hedged':False},
    'XPPT.DE': {'tv':'XETR:XPPT','isin':'DE000A2T0VT7','ter':0.38,'ter_note':'TER 0,38 % (émetteur Xtrackers)','hedged':False},
    'XAD3.DE': {'tv':'XETR:XAD3','isin':'DE000A1EK0H1','ter':0.75,'ter_note':'TER 0,75 % (factsheet émetteur au 30/09/2026), part couverte en euros','hedged':True},
    'PHPT.AS': {'tv':'EURONEXT:PHPT','isin':'JE00B1VS2W53','ter':0.49,'ter_note':'TER 0,49 % (WisdomTree). Série Yahoo peu fiable vs le platine : pas de note APEX.','hedged':False,'skip_score':True},
    'IPDM.L':  {'tv':'LSE:IPDM','isin':'IE00B4556L06','ter':0.20,'ter_note':'TER 0,20 % (iShares, table OMI IPDM.UK 24/09/2026)','hedged':False},
    '8PSC.DE': {'tv':'XETR:8PSC','isin':'IE00B4LJS984','ter':0.19,'ter_note':'TER 0,19 % (factsheet Invesco au 31/10/2026)','hedged':False},
    'PHPD.AS': {'tv':'EURONEXT:PHPD','isin':'JE00B1VS3002','ter':0.49,'ter_note':'TER 0,49 % (WisdomTree, 19/11/2026)','hedged':False},
}
# ETC physiques à conserver même absents de Revolut (demande 23/11, toutes les fiches métaux).
ETC_KEEP=set(v['tv'] for v in ETC_META.values())
SPOT={'or':None,'argent':('OANDA:XAGUSD','XAG','Argent au comptant Revolut'),
      'platine':('OANDA:XPTUSD','XPT','Platine au comptant Revolut'),
      'palladium':('OANDA:XPDUSD','XPD','Palladium au comptant Revolut')}
def inst(s,kind):
    meta=ETC_META.get(s) or {}
    w,m=wk(s); tv,tvd=tvv(s)
    if meta.get('tv'): tv=meta['tv']
    # PHPT.AS (et assimilés) : historique trop peu corrélé / consigne skip_score → listé sans note
    min_bars=30 if not meta.get('skip_score') else 1
    if not w or len(w)<min_bars: return None
    if not tv and not meta.get('skip_score'):
        if not w or len(w)<30: return None
    t=timing([(d,c,ok) for d,c,ok in w]) if len(w)>=2 else None
    if t is None and not meta.get('skip_score'): return None
    x={'ticker':s,'name':m.get('longName') or m.get('shortName') or tvd or s,'tv':tv,'kind':kind,'kind_nom':KIND[kind],'currency':m.get('currency'),'timing':t,
       'hedged':bool(meta['hedged']) if 'hedged' in meta else ('hedged' in (m.get('longName') or '').lower()),
       'url':f'https://finance.yahoo.com/quote/{urllib.parse.quote(s)}/','retrieved':mtime(yf_(s))}
    if meta:
        x['isin']=meta.get('isin'); x['ter']=meta.get('ter'); x['ter_note']=meta.get('ter_note')
    if meta.get('skip_score') or not t or len(w)<30:
        x['skip_score']=True
        return x
    try:
        rec=K.compute(w,BEN,BN,K.yopens(yf_(s)),fsym=s,hl=K.yhl(yf_(s)),contrarien=True, sans_elliott=True)
        x['av']=rec.get('av'); x['elliott']=rec.get('elliott'); x['sent']=rec.get('sent')
        x['date']=rec.get('date'); x['close']=rec.get('close')
    except Exception as e:
        x['score_error']=str(e)
    return x
rows=[]
for key,nom,fut,principal,others,miners in MET:
    w,m=K.yweekly(yf_(fut)); row={'key':key,'nom':nom,'sym':fut,'etf':(m.get('shortName') or fut)+' (contrat à terme continu, '+m.get('exchangeName','')+')','kind':'fut','covered':True,'currency':'USD',
       'url':f'https://finance.yahoo.com/quote/{urllib.parse.quote(fut)}/history/','retrieved':mtime(yf_(fut)),'tv':None,
       'note':"Signaux calculés sur le contrat à terme continu Yahoo (changements d'échéance non ajustés). Référence de force relative : DBC (Invesco DB Commodity Index, panier de matières premières), en dollars."}
    row.update(K.compute(w,BEN,BN,K.yopens(yf_(fut)),fsym=fut,hl=K.yhl(yf_(fut)),contrarien=True, sans_elliott=True))
    cand=[]
    for s,k in ([(principal,'etc')] if principal else [])+others:
        x=inst(s,k)
        if x: cand.append(x)
    if not principal:      # platine : ETC Xetra non couvert en euros avec l'historique le plus long
        xs=[x for x in cand if x['ticker'].endswith('.DE') and not x['hedged'] and x['tv']]
        p=max(xs,key=lambda x:x['timing']['first'] and -D.date.fromisoformat(x['timing']['first']).toordinal()); cand.remove(p); cand.insert(0,p)
    head=cand[0] if cand and cand[0]['tv'] else None; rest=[x for x in cand[1:] if x['tv']]
    mins=[]
    for s in miners:
        q=qsget(s) if J(B+f'qs/{s}.json') else None; x=inst(s,'min')
        if not x: continue
        if q: x.update({'m':{k:(None if v is None else round(v,2)) for k,v in q['m'].items()},'analysts':q['analysts'],'industry':q['industry'],'mrq':q['mrq']})
        else: x.update({'m':{},'analysts':None,'industry':None})
        mins.append(x)
    el=score([dict(x) for x in mins if x.get('m')],'std') if len(mins)>=3 else []
    el=[x for x in el if x['tv']]
    # Jusqu'à 2 minières (disponibles Revolut), après les ETC physiques.
    if el: pick=el[:2]; mnote=f"Minières classées par le score APEX santé / croissance parmi {len(mins)} grandes minières {nom.lower()} cotées ({len(el)} éligibles)."
    else:
        pick=[dict(x,score=None,health=None,growth=None) for x in mins if x['tv']][:2]
        mnote=f"Score santé / croissance non calculé : seulement {len(mins)} grandes minières de platinoïdes cotées et suivies (classement relatif impossible sous 3 titres). Données affichées à titre d'information."
    lst=rest+pick
    # 23/11/2026 · ETC physiques conservés sur les 4 fiches même absents de Revolut. Pas de modification TradingView.
    def allow(tv):
        return RV.keep(tv) or (tv in ETC_KEEP)
    if head and not allow(head['tv']): head=None
    l2=[]
    for x in lst:
        if not allow(x['tv']): continue
        u=RV.rep(x['tv'])
        if u:
            if any(y['tv']==u['tv'] for y in l2+([head] if head else [])): continue
            y=inst(u['yahoo'],x['kind'])
            if not y: continue
            if x['kind']=='min':
                q=qsget(u['yahoo']) if J(B+f"qs/{u['yahoo']}.json") else None
                y.update({'m':{k:(None if v is None else round(v,2)) for k,v in q['m'].items()},'analysts':q['analysts'],'industry':q['industry'],'mrq':q['mrq']} if q else {'m':{},'analysts':None,'industry':None})
                y.update(score=None,health=None,growth=None)
            y['note_revolut']=f"{u['old']} non disponible chez Revolut : remplacé par {u['tv']}."
            x=y
        l2.append(x)
    lst=l2
    TVM={'or':'TVC:GOLD','argent':'TVC:SILVER','platine':'TVC:PLATINUM','palladium':'TVC:PALLADIUM'}[key]; u=RV.rep(TVM)
    # Métal au comptant Revolut, dans le bouton (sauf l'or : pas de ticker XAU dans disponibilites.json).
    sp=SPOT.get(key)
    if sp:
        stv,scode,sname=sp
        row['tv']=stv
        spot={'ticker':scode,'name':sname,'tv':stv,'kind':'spot','kind_nom':KIND['spot'],'currency':'USD',
              'hedged':False,'isin':None,'ter':None,'ter_note':None,
              'av':row.get('av'),'elliott':row.get('elliott'),'sent':row.get('sent'),
              'date':row.get('date'),'close':row.get('close'),
              'timing':{'date':row.get('date'),'close':row.get('close'),'dd52':row.get('dd52'),'ddath':(row.get('ath') or {}).get('dd'),
                        'ath_date':(row.get('ath') or {}).get('date')},
              'note_revolut':"Métal au comptant de l'onglet Matières premières Revolut (bouton Acheter visible, achat non confirmé). Note alignée sur le contrat à terme continu, proxy du prix spot. Les nouveaux clients français ne peuvent plus s'inscrire aux matières premières ; les titulaires existants gardent l'accès (aide Revolut, 2026).",
              'url':None,'retrieved':row.get('retrieved')}
        # en tête des instruments (juste après l'ETC principal)
        lst=[spot]+[x for x in lst if x.get('tv')!=stv]
    list_note=None
    if key=='or':
        row['note_revolut']=("Instrument Revolut retenu pour l'or : GLDA (XETR:GLDA), ETC physique, plus 8PSG et XAD5 aussi chez Revolut. "
            "Le ticker XAU de l'onglet Matières premières n'est pas dans le référentiel de disponibilité APEX : il n'est pas ajouté comme instrument. "
            "Le contrat à terme TVC:GOLD n'est pas achetable au comptant. "
            "La note APEX (−50 à 250) de cette ligne est la moyenne des notes des instruments visibles dans le bouton ci-dessous.")
        list_note=("Six ETC physiques (ISIN distincts), hors CFD et ETP de futures. 4GLD, IGLN et PHGP : chez XTB (table OMI 24/09/2026), pas chez Revolut. Ajoutés le 23/11/2026.")
    elif key=='argent':
        row['note_revolut']=("Instruments Revolut : XAG (OANDA:XAGUSD, métal au comptant ; bouton Acheter visible, achat non confirmé) et l'ETC Invesco Physical Silver 8PSB (XETR:8PSB), plus XAD6. "
            "Attention : 8PSB n'est pas un ETC platine, c'est l'argent physique. "
            "La note APEX (−50 à 250) de cette ligne est la moyenne des notes des instruments visibles dans le bouton ci-dessous.")
        list_note=("Quatre ETC physiques à ISIN distincts trouvés avec un historique Yahoo exploitable (XAD6, 8PSB, PHAG, ISLN). Pas de 5ᵉ ETC argent physique distinct, sans ETP de futures ni doublon d'ISIN. ISLN est chez XTB (OMI 24/09/2026).")
    elif key=='platine':
        row['note_revolut']=("Instrument Revolut : XPT (OANDA:XPTUSD, métal au comptant de l'onglet Matières premières ; bouton Acheter visible, achat non confirmé). "
            "Les nouveaux clients français ne peuvent plus s'inscrire aux matières premières ; les titulaires existants gardent l'accès (aide Revolut, 2026). "
            "Aucun ETC platine n'est disponible chez Revolut (8PSB, visible chez Revolut, est l'ETC d'argent Invesco, pas le platine). "
            "Chez XTB (table OMI France du 24/09/2026, hors CFD) : iShares Physical Platinum ETC (IPLT.UK / LSE:IPLT). "
            "La note APEX (−50 à 250) de cette ligne est la moyenne des notes des instruments visibles dans le bouton ci-dessous.")
        list_note=("Cinq ETC physiques : IPLT, 8PSA, XPPT, XAD3 (couvert en euros) et WisdomTree PHPT. La série Yahoo de PHPT n'est pas assez fiable pour une note. Ce ne sont pas des CFD ni des ETP de futures.")
    else:
        row['note_revolut']=("Instrument Revolut : XPD (OANDA:XPDUSD, métal au comptant ; bouton Acheter visible, achat non confirmé). "
            "Aucun ETC palladium n'est chez Revolut. Chez XTB (OMI 24/09/2026) : iShares Physical Palladium ETC (IPDM.UK / LSE:IPDM). "
            "La note APEX (−50 à 250) de cette ligne est la moyenne des notes des instruments visibles dans le bouton ci-dessous.")
        list_note=("Seuls trois ETC palladium physiques à ISIN distincts sont cotés en Europe (iShares IPDM, Invesco 8PSC, WisdomTree PHPD). Le marché est étroit : pas de 4ᵉ ou 5ᵉ ETC physique trouvé, hors ETP de futures et hors doublons d'ISIN (SPAL est le même Invesco que 8PSC).")
    row['mlist']={'head':head,'items':lst,'miner_note':mnote,'n':len(lst),'list_note':list_note,'excluded':[[x['ticker'],x['why_not']] for x in (score([dict(x) for x in mins if x.get('m')],'std') and []) ]}
    rows.append(row)
# ---- carte composite de l'onglet ----
W_MET={'or':.40,'argent':.20,'platine':.10,'palladium':.10}
CF=J(B+'cftc.json'); cf={}
for r in CF['rows']: cf.setdefault(r['m'],{})[r['d']]=(r['mm_long']-r['mm_short'])/r['oi']*100
cfs={m:sorted(v.items()) for m,v in cf.items()}
def cft_at(m,d):
    s=cfs[m]; ks=[x[0] for x in s]; i=bisect.bisect_right(ks,d)-1
    if i<156: return None,None
    v=s[i][1]; h=[x[1] for x in s[i-155:i+1]]; return v,K.prank(h,v)
byk={r['key']:r for r in rows}
dates=[x[0] for x in byk['or']['sent']['series']]
def comp_at(k_idx,d):
    parts=[]
    for k,wgt in W_MET.items():
        s=dict(byk[k]['sent']['series']).get(d); parts.append((f"Sentiment {byk[k]['nom'].lower()} (APEX)",wgt,s,'' if s is None else f"{s:.0f}"))
    vs=[cft_at(m,d) for m in ('or','argent')]; pc=[p for _,p in vs if p is not None]
    parts.append(('Positionnement spéculatif CFTC or + argent (managed money net, rang 3 ans)',.20,sum(pc)/len(pc) if pc else None,' · '.join(f"{m} {v:+.1f} % de l'OI".replace('.',',') for m,(v,_) in zip(('or','argent'),vs) if v is not None)))
    av=[(w,v) for _,w,v,_ in parts if v is not None]; return sum(w*v for w,v in av)/sum(w for w,_ in av),parts
ss=[];ah=[]
for d in dates:
    v,parts=comp_at(0,d); ss.append([d,round(v,1)])
    a_parts=[(byk[k]['nom'],w,dict(byk[k]['av']['history']).get(d)) for k,w in W_MET.items()]
    cp=[p for _,p,_ in [(0,parts[-1][2],0)] if p is not None]
    a_parts.append(('CFTC (lecture contrarienne)',.20,None if parts[-1][2] is None else K.clip((50-parts[-1][2])*2) if hasattr(K,'clip') else max(-100,min(100,(50-parts[-1][2])*2))))
    av_=[(w,x) for _,w,x in a_parts if x is not None]; ah.append([d,round(sum(w*x for w,x in av_)/sum(w for w,_ in av_),1)])
sv,parts=comp_at(0,dates[-1]); d=dates[-1]
lab_s=K.lab_s; lab_av=K.lab_av
IND={'value':round(sv,1),'date':d,'label':lab_s(sv),'avg':round(sum(x[1] for x in ss)/len(ss),1),'min':min(ss,key=lambda x:x[1]),'max':max(ss,key=lambda x:x[1]),'n':len(ss),'series':ss,'official':False,
     'title':'Sentiment métaux précieux · indice composite APEX',
     'components':[{'name':n,'weight':w,'value':None if v is None else round(v,1),'detail':det} for n,w,v,det in parts],'missing':[],
     'source':{'name':'Calcul APEX · Yahoo Finance (contrats à terme COMEX / NYMEX), CFTC (Commitments of Traders)','url':'https://www.cftc.gov/MarketReports/CommitmentsofTraders/index.htm','retrieved':mtime(B+'cftc.json')},
     'method':"Indice composite APEX, pas un indice officiel. 0 = peur, 100 = euphorie. Moyenne pondérée des sentiments APEX de chaque métal (or 40 %, argent 20 %, platine 10 %, palladium 10 %, voir les lignes « Métaux ») et du positionnement net des gérants (« managed money ») sur les contrats à terme or et argent du rapport CFTC « disaggregated », exprimé en % de l'intérêt ouvert et classé sur 3 ans (20 %). Valeur au dernier vendredi clôturé ; le rapport CFTC est daté du mardi précédent."}
acomp=[]
for k,w in W_MET.items():
    a=byk[k]['av']['score']; acomp.append({'nom':'Achat / Vente '+byk[k]['nom'].lower()+' (APEX)','poids':w,'valeur':f"{a:+.1f}".replace('.',','),'note':a,'regle':'score de la ligne du métal'})
cv=parts[-1][2]; acomp.append({'nom':'Positionnement CFTC or + argent, lecture contrarienne','poids':.20,'valeur':'n.d.' if cv is None else f"rang {cv:.0f} sur 3 ans",'note':None if cv is None else round(max(-100,min(100,(50-cv)*2)),1),'regle':'(50 − rang) × 2 : spéculateurs très acheteurs = prudence'})
tw=sum(x['poids'] for x in acomp if x['note'] is not None)
for x in acomp: x['contrib']=None if x['note'] is None else round(x['poids']*x['note']/tw,1)
asc=round(sum(x['contrib'] for x in acomp if x['contrib'] is not None),1)
AV={'score':asc,'label':lab_av(asc),'date':d,'sens':"Score > 0 : contexte technique plus favorable à l'achat de métaux précieux ; < 0 : plutôt à la prudence.",'components':acomp,'missing':[],
    'history':ah,'avg':round(sum(x[1] for x in ah)/len(ah),1),'min':min(ah,key=lambda x:x[1]),'max':max(ah,key=lambda x:x[1]),
    'method':"Indicateur composite APEX, purement informatif. Moyenne pondérée des scores Achat / Vente APEX de chaque métal (or 40 %, argent 20 %, platine 10 %, palladium 10 %) et du positionnement spéculatif CFTC or + argent lu de façon contrarienne (20 %). Chaque score de métal n'intègre plus les vagues d'Elliott dans le bandeau (15 % retirés sans redistribution, t462u) ; le retracement de Fibonacci du plus bas historique (base) au plus haut historique (ATH) à 15 % (plus le cours est bas dans le retracement, plus la note pousse à l'achat ; négative près de l'ATH), lus automatiquement sur les corps des bougies hebdomadaires du contrat à terme ; approximation qui peut différer de ton indicateur TradingView.",
    'sources':[['Yahoo Finance (GC=F, SI=F, PL=F, PA=F, DBC)','https://finance.yahoo.com/quote/GC%3DF/history/'],['CFTC Commitments of Traders','https://www.cftc.gov/MarketReports/CommitmentsofTraders/index.htm']]}
# ---- graphiques ----
def fred(p): return [[a,float(b)] for a,b in list(csv.reader(open(p)))[1:] if b not in('','.')]
FX=fred(B+'fred_DEXUSEU.csv'); ew,_=K.yweekly(yf_('EURUSD=X')); fxw={d:v for d,v,ok in ew}
fk=[x[0] for x in FX]
def eurusd(d):
    if d in fxw: return fxw[d]
    i=bisect.bisect_right(fk,d)-1; return FX[i][1] if i>=0 else None
P={}
for key,nom,fut,*_ in MET:
    w,_=K.yweekly(yf_(fut)); w=[(d,c) for d,c,ok in w if ok]
    eur=[[d,round(c/eurusd(d),2)] for d,c in w if eurusd(d)]
    usd=[[d,round(c,2)] for d,c in w]
    ath_u=max(usd,key=lambda x:x[1]); ath_e=max(eur,key=lambda x:x[1])
    P[key]={'usd':usd,'eur':eur,'ath_usd':ath_u,'ath_eur':ath_e,'last_usd':usd[-1],'last_eur':eur[-1],'dd_usd':round((usd[-1][1]/ath_u[1]-1)*100,1),'dd_eur':round((eur[-1][1]/ath_e[1]-1)*100,1),
            'first':usd[0][0],'sym':fut}
def ratio(a,b):
    bm=dict(P[b]['usd']); r=[[d,round(v/bm[d],2)] for d,v in P[a]['usd'] if d in bm and bm[d]]
    h=[x[1] for x in r]; return {'series':r,'last':r[-1],'pct':round(K.prank(h,r[-1][1])),'max':max(r,key=lambda x:x[1]),'min':min(r,key=lambda x:x[1])}
RAT={'or_argent':ratio('or','argent'),'or_platine':ratio('or','platine')}
TIPS=fred(B+'fred_DFII10.csv'); tk=[x[0] for x in TIPS]
def tips_at(d):
    i=bisect.bisect_right(tk,d)-1; return TIPS[i][1] if i>=0 else None
GR=[[d,v,tips_at(d)] for d,v in P['or']['usd'] if d>=TIPS[0][0]]
COT={m:[[d,round(v,1)] for d,v in s] for m,s in cfs.items()}
COTL={m:{'date':s[-1][0],'net':round(s[-1][1],1),'pct':round(K.prank([x[1] for x in s[-156:]],s[-1][1]))} for m,s in cfs.items()}
res={'generated':NOW.strftime('%Y-%m-%d %H:%M'),'ind':IND,'av':AV,'rows':rows,'bench':'DBC','bench_nom':'DBC (Invesco DB Commodity Index Tracking Fund)','bench_url':'https://finance.yahoo.com/quote/DBC/history/',
     'charts':{'prices':P,'ratios':RAT,'gold_real':GR,'cot':COT,'cot_last':COTL,'retrieved':{'yahoo':mtime(yf_('GC=F')),'fred_fx':mtime(B+'fred_DEXUSEU.csv'),'fred_tips':mtime(B+'fred_DFII10.csv'),'cftc':CF['retrieved'],'eurusd':mtime(yf_('EURUSD=X'))},
               'fx_last':FX[-1]},
     'health_weights':{k:[(n,w) for _,n,w,_ in v] for k,v in HEALTH.items()},'growth_weights':[(n,w) for _,n,w,_ in GROWTH]}
json.dump(res,open(R+'data/metaux.json','w'),ensure_ascii=False)
print('TAB S',IND['value'],IND['label'],'AV',AV['score'],AV['label'],d)
for r in rows:
    L=r['mlist']; print(r['nom'],'S',r['sent']['value'],r['sent']['label'],'AV',r['av']['score'],r['av']['label'],r['date'],r['warn'],'| tête',L['head'] and (L['head']['tv'],L['head']['name']),'|',[(x['tv'],x.get('score')) for x in L['items']])
for k,p in P.items(): print(k,'USD',p['last_usd'],'ATH',p['ath_usd'],p['dd_usd'],'| EUR',p['last_eur'],'ATH',p['ath_eur'],p['dd_eur'])
print({k:(v['last'],v['pct']) for k,v in RAT.items()}, COTL, GR[-1])
