"""Sélection quantitative APEX : pour chaque secteur, ETF principal + panier d’actions (santé financière 50 % + croissance prévue 50 %).
PANIER : taille actuelle 5, maximum prévu 10 (ne pas remplir au-delà de PANIER_ACTUEL tant que la liste n’est pas revue).
Univers : 20 premières lignes de l'ETF SPDR (fichier officiel State Street). Données : Yahoo Finance (yfinance), consensus analystes.
Rangs percentiles au sein de l'univers du secteur. Timing séparé (n'entre pas dans le score). -> data/fondamentaux.json"""
import os as _os
_APEX_ROOT = _os.path.abspath(_os.environ.get('APEX_ROOT') or _os.path.join(_os.path.dirname(__file__), '..'))
import json, sys as _s; _s.path.insert(0,_APEX_ROOT + '/src'); import revolut_rules as RV, courtier_cash as CC; import json, os, datetime as D
from zoneinfo import ZoneInfo
PANIER_MAX=10
PANIER_ACTUEL=10
B=_APEX_ROOT + '/data/secteurs/'
TODAY=D.datetime.now(ZoneInfo('Europe/Paris')).date()
U=json.load(open(B+'holdings/universe.json'))
DUP={'GOOG':'GOOGL','FOX':'FOXA','NWS':'NWSA'}           # même société, deux catégories d'actions : on garde une seule ligne
YEX={'NMS':'NASDAQ','NGM':'NASDAQ','NCM':'NASDAQ','NYQ':'NYSE','ASE':'AMEX','PCX':'AMEX','BTS':'CBOE'}
def rsi(v,n=14):
    o=[None]*len(v);g=l=0
    for i in range(1,len(v)):
        d=v[i]-v[i-1];up=max(d,0);dn=max(-d,0)
        if i<=n:
            g+=up;l+=dn
            if i==n: g/=n;l/=n;o[i]=100-100/(1+g/l) if l else 100
        else: g=(g*(n-1)+up)/n;l=(l*(n-1)+dn)/n;o[i]=100-100/(1+g/l) if l else 100
    return o
def prank(vals,v,inv=False):
    h=[x for x in vals if x is not None]
    if v is None or len(h)<3: return None
    r=100*(sum(1 for x in h if x<v)+0.5*(sum(1 for x in h if x==v)-1))/(len(h)-1) if len(h)>1 else 50
    return 100-r if inv else r
def tvsym(sym,tvl,yexch):
    want=sym.replace('-','.').replace('/','.')
    if isinstance(tvl,list):
        for s in tvl:
            if s.get('symbol')==want and s.get('exchange') in ('NASDAQ','NYSE','AMEX','CBOE','NYSE ARCA'):
                return f"{s['exchange']}:{want}", s['exchange']==YEX.get(yexch, s['exchange']) or (yexch in('PCX','ASE') and s['exchange']=='AMEX')
    return None, False
# ---- pondérations par profil ----
HEALTH={
 'std':[('nd_ebitda','Dette nette / EBITDA',.125,True),('op_margin','Marge opérationnelle',.125,False),('fcf_margin','Marge de free cash-flow',.125,False),('roe','ROE',.075,False),('current','Current ratio',.05,False)],
 'fin':[('roe','ROE',.15,False),('roa','ROA',.15,False),('net_margin','Marge nette',.125,False),('op_margin','Marge opérationnelle',.075,False)],
 'reit':[('nd_ebitda','Dette nette / EBITDA',.175,True),('ebitda_margin','Marge d\'EBITDA',.125,False),('op_margin','Marge opérationnelle',.125,False),('roa','ROA',.075,False)]}
GROWTH=[('eps_0y','Croissance BPA estimée, exercice en cours',.125,False),('eps_1y','Croissance BPA estimée, exercice suivant',.175,False),('rev_0y','Croissance CA estimée, exercice en cours',.075,False),('rev_1y','Croissance CA estimée, exercice suivant',.125,False)]
PROFILE={'XLF':'fin','XLRE':'reit'}
out={'generated':D.datetime.now(ZoneInfo('Europe/Paris')).strftime('%Y-%m-%d %H:%M'),'sectors':{},'weights':{k:[(n,w) for _,n,w,_ in v] for k,v in HEALTH.items()},'growth_weights':[(n,w) for _,n,w,_ in GROWTH],'missing':[],'tv_check':[]}
for etf,u in U.items():
    prof=PROFILE.get(etf,'std'); rows=[]
    for hd in u['holdings']:
        t=hd['ticker']
        if t in DUP: continue
        f=json.load(open(B+f'fond/{t}.json')); i=f.get('info',{})
        if not i: out['missing'].append(f"{etf} {t} : fiche Yahoo absente"); continue
        ee=f.get('earnings_estimate') or {}; re_=f.get('revenue_estimate') or {}; ge=f.get('growth_estimates') or {}
        def eg(p):
            r=ee.get(p) or {}; g=r.get('growth'); base=r.get('yearAgoEps')
            return None if g is None or base is None or base<=0 else g*100
        rg=lambda p:((re_.get(p) or {}).get('growth') or None) and re_[p]['growth']*100
        rev=i.get('totalRevenue'); eb=i.get('ebitda')
        m={'nd_ebitda':((i.get('totalDebt') or 0)-(i.get('totalCash') or 0))/eb if eb and eb>0 and i.get('totalDebt') is not None else None,
           'op_margin':i.get('operatingMargins') and i['operatingMargins']*100,'net_margin':i.get('profitMargins') and i['profitMargins']*100,
           'fcf_margin':(i['freeCashflow']/rev*100) if i.get('freeCashflow') is not None and rev else None,
           'ebitda_margin':i.get('ebitdaMargins') and i['ebitdaMargins']*100,
           'roe':i.get('returnOnEquity') and i['returnOnEquity']*100,'roa':i.get('returnOnAssets') and i['returnOnAssets']*100,
           'current':i.get('currentRatio'),'de':i.get('debtToEquity'),
           'eps_0y':eg('0y'),'eps_1y':eg('+1y'),'rev_0y':rg('0y'),'rev_1y':rg('+1y'),
           'ltg':(ge.get('LTG') or {}).get('stockTrend')}
        if m['ltg'] is not None: m['ltg']*=100
        nan=(ee.get('+1y') or {}).get('numberOfAnalysts') or i.get('numberOfAnalystOpinions')
        # timing (bougies hebdomadaires clôturées)
        wk={}
        for d0,c0 in f.get('weekly',[]):       # rattache chaque ligne au vendredi de sa semaine (lignes d'événements, point « live »)
            d1=D.date.fromisoformat(d0[:10]); fri=d1+D.timedelta(days=(4-d1.weekday())%7) if d1.weekday()<=4 else d1-D.timedelta(days=d1.weekday()-4)
            wk[fri]=c0
        w=[(fr_-D.timedelta(days=4),wk[fr_]) for fr_ in sorted(wk) if fr_<TODAY]   # semaines clôturées uniquement
        cl=[c for _,c in w]; r=rsi(cl) if len(cl)>20 else [None]
        hi52=max(cl[-52:]); ath=max(cl); ia=cl.index(ath)
        tim={'date':(w[-1][0]+D.timedelta(days=4)).isoformat(),'close':round(cl[-1],2),'dd52':round((cl[-1]/hi52-1)*100,1),'ddath':round((cl[-1]/ath-1)*100,1),
             'ath_date':(w[ia][0]+D.timedelta(days=4)).isoformat(),'rsi':round(r[-1],1) if r[-1] is not None else None,'first':w[0][0].isoformat()}
        tim['near']='ath' if tim['ddath']>=-2 else '52s' if tim['dd52']>=-2 else None
        tim['overbought']=tim['rsi'] is not None and tim['rsi']>=70
        sym,okx=tvsym(t,f.get('tv'),i.get('exchange'))
        out['tv_check'].append([t,sym,i.get('exchange'),okx])
        mrq=i.get('mostRecentQuarter')
        rows.append({'ticker':t,'name':i.get('longName') or i.get('shortName') or hd['name'],'weight':round(hd['weight'],2),'tv':sym,'tv_ok':okx,'yahoo':f['yahoo'],
          'm':{k:(None if v is None else round(v,2)) for k,v in m.items()},'analysts':nan,'timing':tim,'industry':i.get('industry'),
          'mrq':D.datetime.fromtimestamp(mrq,ZoneInfo('UTC')).date().isoformat() if mrq else None,'retrieved':f['retrieved'],'currency':i.get('financialCurrency')})
    H=HEALTH[prof]
    for r in rows:
        def block(spec):
            parts=[(w,prank([x['m'][k] for x in rows],r['m'][k],inv)) for k,_,w,inv in spec]
            av=[(w,p) for w,p in parts if p is not None]
            return (sum(w*p for w,p in av)/sum(w for w,_ in av) if av else None), len(av), [None if p is None else round(p) for _,p in parts]
        h,nh,hr=block(H); g,ng,gr=block(GROWTH)
        r['health']=None if h is None else round(h,1); r['growth']=None if g is None else round(g,1); r['ranks']={'health':hr,'growth':gr}
        MINA=3 if prof=='reit' else 5
        r['eligible']=nh>=max(3,len(H)-2) and ng>=2 and (r['analysts'] or 0)>=MINA
        r['why_not']=None if r['eligible'] else f"données insuffisantes ({nh}/{len(H)} santé, {ng}/4 croissance, {r['analysts'] or 0} analystes)"
        r['score']=round(.5*h+.5*g,1) if r['eligible'] else None
    el=sorted([r for r in rows if r['eligible']],key=lambda r:-r['score'])
    top=[]
    for r in el:
        if not CC.cash_ok(r.get('tv')): continue
        top.append(r)
        if len(top)>=PANIER_ACTUEL: break
    tvl=json.load(open(B+f'tv_{etf}.json')); te=[s for s in tvl if s.get('symbol')==etf and 'etf' in (s.get('typespecs') or [])]
    out['sectors'][etf]={'asof':u['asof'].replace('As of ',''),'profile':prof,'universe':len(rows),'eligible':len(el),
       'etf':(lambda u:{'sym':u['tv'].split(':')[1],'name':u['nom'],'tv':u['tv'],'ref_us':f"{te[0]['exchange']}:{etf}" if te else None,'revolut':u['revolut']})(RV.rep('AMEX:'+etf)),   # 17/11/2026 : équivalent UCITS Revolut
       'top':top,'panier':{'actuel':PANIER_ACTUEL,'max':PANIER_MAX},'excluded':[[r['ticker'],r['why_not']] for r in rows if not r['eligible']]}
try:
    import exceptions_actions as EX
    EX.merge_into(out)
except Exception as _ex:
    print('exceptions_actions non fusionnées:', _ex)
json.dump(out,open(_APEX_ROOT + '/data/fondamentaux.json','w'),ensure_ascii=False)

for e,s in out['sectors'].items():
    print(f"\n{e} {s['etf']['tv']} « {s['etf']['name']} » univers {s['universe']} éligibles {s['eligible']} profil {s['profile']} exclus {s['excluded']}")
    for r in s['top']:
        m=r['m'];t=r['timing']
        print('  ',r['tv'],'✓' if r['tv_ok'] else '≠yahoo',r['score'],'S',r['health'],'C',r['growth'],'| ndE',m['nd_ebitda'],'opM',m['op_margin'],'ROE',m['roe'],'BPA+1',m['eps_1y'],'CA+1',m['rev_1y'],'| dd52',t['dd52'],'ATH',t['ddath'],'RSI',t['rsi'],t['near'] or '',t['date'])
print('\nTV non vérifiés :',[x for x in out['tv_check'] if not x[3] or not x[1]])
