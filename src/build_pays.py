"""Onglet Actions · SECTEURS PAR PAYS -> data/pays.json
Instrument de chaque secteur : ETF sectoriel coté (Japon NEXT FUNDS TOPIX-17, Corée KODEX / TIGER), indice sectoriel officiel (Australie S&P/ASX 200)
ou, à défaut, « panier APEX » : panier pondéré par la capitalisation (plafond 25 %) des plus grandes valeurs du pays dans le secteur Yahoo.
Indicateurs : mêmes formules que les secteurs USA (src/ind_core.py), force relative contre l'indice national. Bougies hebdomadaires clôturées uniquement."""
PANIER_MAX=10
PANIER_ACTUEL=10

import json, os, sys, datetime as D, urllib.parse
from zoneinfo import ZoneInfo
sys.path.insert(0,os.path.dirname(__file__)); import ind_core as K, revolut_rules as RV, courtier_cash as CC
R='/workspace/invest/patrimoine-dashboard/'; B=R+'data/pays/'
CFG=json.load(open(R+'src/pays_config.json'))['countries']; SCR=json.load(open(B+'screen.json'))
_SW=json.load(open(R+'src/swiss_xtb.json'))
SWISS_YAHOO=set(x['yahoo'] for x in _SW.get('stocks') or [])

NOW=D.datetime.now(ZoneInfo('Europe/Paris')); TODAY=NOW.date()
TVX={'.PA':'EURONEXT','.DE':'XETR','.MI':'MIL','.T':'TSE','.KS':'KRX','.AX':'ASX','.L':'LSE','.SW':'SIX'}
CUR={'EUR':'€','JPY':'¥','KRW':'₩','AUD':'A$','GBp':'p','USD':'$','CAD':'C$','CHF':'CHF','SEK':'SEK'}
US_EX={'NYSE','NASDAQ','AMEX','CBOE','NYSE ARCA','NYSE ARCA','BATS','CBOE BZX'}
def J(p):
    try: return json.load(open(p))
    except Exception: return None
def mtime(p): return D.datetime.fromtimestamp(os.path.getmtime(p),ZoneInfo('Europe/Paris')).strftime('%Y-%m-%d %H:%M')
def yfile(s): return B+'yahoo_1wk_'+urllib.parse.quote(s)+'.json'
def tvcheck(s):
    if s in ('^GSPTSE','GSPTSE'):
        l=J(B+f'tv/{s}.json')
        if isinstance(l,list):
            for x in l:
                if x.get('symbol') in ('TSX','GSPTSE','SPTTSE') and (x.get('exchange') or '') in ('TSX','TSE','TRADEWEB'):
                    return f"{x.get('exchange')}:{x.get('symbol')}",x.get('description')
        return 'TSX:TSX','S&P/TSX Composite'
    code=s.lstrip('^'); suf='.'+code.split('.')[-1] if '.' in code else ''
    if s.startswith('^AX'): code,ex='X'+code[2:4],'ASX'
    else: code,ex=(code.split('.')[0] if '.' in code else code),TVX.get(suf)
    l=J(B+f'tv/{s}.json')
    if s.startswith('^AX'): ex='SP'        # indices S&P/ASX 200 sectoriels : préfixe TradingView SP (ex. SP:XFJ)
    if isinstance(l,list):
        if not suf:                        # actions canadiennes cotées aux États-Unis (sans suffixe Yahoo)
            for x in l:
                if x.get('symbol')==code and (x.get('exchange') or '') in ('NYSE','NASDAQ','AMEX','CBOE','BATS','NYSE ARCA'):
                    return f"{x.get('exchange')}:{code}",x.get('description')
        for x in l:
            if x.get('symbol')==code and (x.get('exchange')==ex or (ex=='EURONEXT' and (x.get('exchange') or '').startswith('Euronext'))): return f'{ex}:{code}',x.get('description')
        if suf=='.MI':                      # ETF de Borsa Italiana (Euronext Milan) : TradingView les range sous le préfixe EURONEXT
            for x in l:
                if x.get('symbol')==code and (x.get('exchange') or '').startswith('Euronext') and x.get('type')=='fund': return f'EURONEXT:{code}',x.get('description')
        if suf=='.ST':                      # Stockholm (XTB .SE)
            for x in l:
                if x.get('symbol')==code and (x.get('exchange') or '') in ('OMXSTO','NASDAQ','OMX'):
                    exx='OMXSTO' if (x.get('exchange') or '').startswith('OMX') or x.get('exchange')=='OMXSTO' else x.get('exchange')
                    return f'{exx}:{code}',x.get('description')
        if suf=='.SW':                      # SIX Swiss Exchange (Yahoo .SW / XTB .CH)
            for x in l:
                if x.get('symbol')==code and (x.get('exchange') or '') in ('SIX','SWX','SIXSWX'):
                    return f"{x.get('exchange')}:{code}",x.get('description')
            for x in l:
                if x.get('symbol')==code and (x.get('type') or '') in ('stock','dr'):
                    return f"{x.get('exchange')}:{code}",x.get('description')
    return None,None
def raw(v): return v.get('raw') if isinstance(v,dict) else v
def qsget(s):
    j=J(B+f'qs/{s}.json'); 
    if not j or 'qs' not in j: return None
    q=j['qs']; g=lambda m,k:raw((q.get(m) or {}).get(k))
    fd=lambda k:g('financialData',k)
    tr={t.get('period'):t for t in ((q.get('earningsTrend') or {}).get('trend') or [])}
    def eg(p):
        e=(tr.get(p) or {}).get('earningsEstimate') or {}; gr=raw(e.get('growth')); base=raw(e.get('yearAgoEps'))
        return None if gr is None or base is None or base<=0 else gr*100
    def rg(p):
        e=(tr.get(p) or {}).get('revenueEstimate') or {}; gr=raw(e.get('growth')); return None if gr is None else gr*100
    rev=fd('totalRevenue'); eb=fd('ebitda'); pc=lambda x:None if x is None else x*100
    m={'nd_ebitda':((fd('totalDebt') or 0)-(fd('totalCash') or 0))/eb if eb and eb>0 and fd('totalDebt') is not None else None,
       'op_margin':pc(fd('operatingMargins')),'net_margin':pc(fd('profitMargins')),'fcf_margin':(fd('freeCashflow')/rev*100) if fd('freeCashflow') is not None and rev else None,
       'ebitda_margin':pc(fd('ebitdaMargins')),'roe':pc(fd('returnOnEquity')),'roa':pc(fd('returnOnAssets')),'current':fd('currentRatio'),
       'eps_0y':eg('0y'),'eps_1y':eg('+1y'),'rev_0y':rg('0y'),'rev_1y':rg('+1y')}
    na=raw(((tr.get('+1y') or {}).get('earningsEstimate') or {}).get('numberOfAnalysts')) or fd('numberOfAnalystOpinions')
    ap=q.get('assetProfile') or {}; pr=q.get('price') or {}
    mrq=g('defaultKeyStatistics','mostRecentQuarter')
    return {'m':m,'analysts':na,'country':ap.get('country'),'sector':ap.get('sector'),'industry':ap.get('industry'),'name':raw(pr.get('longName')) or raw(pr.get('shortName')),
            'currency':fd('financialCurrency'),'mrq':D.datetime.fromtimestamp(mrq,ZoneInfo('UTC')).date().isoformat() if mrq else None,'retrieved':j['retrieved']}
def wkly(s):
    p=B+f'wk/{s}.json'
    if not os.path.exists(p): return None
    try: w,_=K.yweekly(p); return [x for x in w if x[2]]
    except Exception: return None
HEALTH={'std':[('nd_ebitda','Dette nette / EBITDA',.125,True),('op_margin','Marge opérationnelle',.125,False),('fcf_margin','Marge de free cash-flow',.125,False),('roe','ROE',.075,False),('current','Current ratio',.05,False)],
 'fin':[('roe','ROE',.15,False),('roa','ROA',.15,False),('net_margin','Marge nette',.125,False),('op_margin','Marge opérationnelle',.075,False)],
 'reit':[('nd_ebitda','Dette nette / EBITDA',.175,True),('ebitda_margin',"Marge d'EBITDA",.125,False),('op_margin','Marge opérationnelle',.125,False),('roa','ROA',.075,False)]}
GROWTH=[('eps_0y','Croissance BPA estimée, exercice en cours',.125,False),('eps_1y','Croissance BPA estimée, exercice suivant',.175,False),('rev_0y','Croissance CA estimée, exercice en cours',.075,False),('rev_1y','Croissance CA estimée, exercice suivant',.125,False)]
def prank(vals,v,inv=False):
    h=[x for x in vals if x is not None]
    if v is None or len(h)<3: return None
    r=100*(sum(1 for x in h if x<v)+0.5*(sum(1 for x in h if x==v)-1))/(len(h)-1)
    return 100-r if inv else r
def same_co(a,b):
    na=(a or '').lower().split(); nb=(b or '').lower().split()
    return bool(na and nb) and na[0]==nb[0] and (len(na)<2 or len(nb)<2 or na[1][:4]==nb[1][:4])
def members(cc,key):
    c=CFG[cc]; out=[]
    for x in SCR['s'][cc][key]:
        q=qsget(x['symbol']); info=(J(B+f"info/{x['symbol']}.json") or {}).get('info') or {}
        ctry=(q or {}).get('country') or info.get('country')
        if ctry and ctry!=c['country'] and cc!='ca': continue
        if cc=='de' and not ctry: continue
        if c.get('cash_only'):
            if x['symbol'] not in SWISS_YAHOO: continue
        # Canada : ISIN CA déjà filtré dans l'univers XTB ; Yahoo étiquette parfois United States / Bermuda (cotation NYSE).
        # Suisse : univers limité aux actions OMI XTB (ISIN CH, hors close-only) ; Revolut non confirmé.
        nm=(q or {}).get('name') or x['name']
        if any(same_co(nm,o['name']) for o in out): continue      # actions de préférence / doubles cotations
        out.append({**x,'name':nm,'q':q})
    return out
def score(rows,prof):
    H=HEALTH[prof]
    for r in rows:
        def block(spec):
            parts=[(w,prank([x['m'][k] for x in rows],r['m'][k],inv)) for k,_,w,inv in spec]; av=[(w,p) for w,p in parts if p is not None]
            return (sum(w*p for w,p in av)/sum(w for w,_ in av) if av else None), len(av)
        h,nh=block(H); g,ng=block(GROWTH)
        r['health']=None if h is None else round(h,1); r['growth']=None if g is None else round(g,1)
        r['eligible']=h is not None and g is not None and nh>=max(3,len(H)-2) and ng>=2 and (r['analysts'] or 0)>=3
        r['why_not']=None if r['eligible'] else f"données insuffisantes ({nh}/{len(H)} santé, {ng}/4 croissance, {r['analysts'] or 0} analystes)"
        r['score']=round(.5*h+.5*g,1) if r['eligible'] else None
    return sorted([r for r in rows if r['eligible']],key=lambda r:-r['score'])
def timing(w):
    cl=[c for _,c,_ in w]; r=K.rsi(cl) if len(cl)>20 else [None]; hi52=max(cl[-52:]); ath=max(cl); ia=cl.index(ath)
    t={'date':w[-1][0],'close':round(cl[-1],2),'dd52':round((cl[-1]/hi52-1)*100,1),'ddath':round((cl[-1]/ath-1)*100,1),'ath_date':w[ia][0],'rsi':round(r[-1],1) if r[-1] is not None else None,'first':w[0][0]}
    t['near']='ath' if t['ddath']>=-2 else '52s' if t['dd52']>=-2 else None; t['overbought']=t['rsi'] is not None and t['rsi']>=70
    return t
def basket(mem):
    """panier pondéré par la capitalisation actuelle (plafond 25 %), rendements hebdomadaires chaînés, membres disponibles chaque semaine"""
    ser={}; caps={}
    for x in mem:
        w=wkly(x['symbol'])
        if w and len(w)>=60: ser[x['symbol']]={d:c for d,c,_ in w}; caps[x['symbol']]=x['cap']
    if len(ser)<3: return None,list(ser)
    tot=sum(caps.values()); wt={k:v/tot for k,v in caps.items()}
    for _ in range(10):                                        # plafond 25 % redistribué
        over={k for k,v in wt.items() if v>.25}
        if not over: break
        ex=sum(wt[k]-.25 for k in over); rest=sum(v for k,v in wt.items() if k not in over)
        wt={k:(.25 if k in over else v+ex*v/rest) for k,v in wt.items()}
    dates=sorted({d for s in ser.values() for d in s}); lvl=100.0; out=[]; prev=None
    for d in dates:
        if prev is None:
            if sum(1 for s in ser.values() if d in s)>=3: out.append((d,lvl,True)); prev=d
            continue
        av=[k for k,s in ser.items() if d in s and prev in s]
        if len(av)>=3:
            sw=sum(wt[k] for k in av); lvl*=sum(wt[k]*ser[k][d]/ser[k][prev] for k in av)/sw; out.append((d,lvl,True)); prev=d
    return out,sorted(ser,key=lambda k:-wt[k]),{k:round(wt[k]*100,1) for k in ser}
res={'generated':NOW.strftime('%Y-%m-%d %H:%M'),'countries':[],'health_weights':{k:[(n,w) for _,n,w,_ in v] for k,v in HEALTH.items()},'growth_weights':[(n,w) for _,n,w,_ in GROWTH]}
for cc,c in CFG.items():
    bw,bm=K.yweekly(yfile(c['bench'])); BEN={d:v for d,v,ok in bw if ok}; BN=c['bench_nom'].split(' (')[0]
    ew,em=K.yweekly(yfile(c['etf'])); etv,ed=tvcheck(c['etf'])
    head={'sym':c['etf'],'nom':'Marché '+c['nom'],'etf':em.get('longName') or ed or c['etf'],'tv':etv,'currency':em.get('currency'),'kind':'etf','url':f"https://finance.yahoo.com/quote/{c['etf']}/history/",'retrieved':mtime(yfile(c['etf']))}
    head.update(K.compute(ew,BEN,BN,K.yopens(yfile(c['etf'])),fsym=c['etf'],hl=K.yhl(yfile(c['etf'])))); head['note']=None if em.get('currency')==bm.get('currency') else f"ETF coté en {em.get('currency')} : la force relative contre le {BN} ({bm.get('currency')}) inclut l'effet de change."
    rows=[]
    for r in c['rows']:
        mem=members(cc,r['key']); row={'key':r['key'],'nom':r['nom'],'kind':r['kind'],'covered':True,'note':r.get('note')}
        prof='fin' if r['key'] in('fin','t1631','t1632') else 'reit' if r['key'] in('immo','t1633') else 'std'
        r=dict(r)
        if r['kind'] in('etf','index') and not RV.keep(tvcheck(r['sym'])[0]):   # 17/11/2026 : ETF / indice local non disponible chez Revolut -> panier APEX
            row['note']=f"{tvcheck(r['sym'])[0]} ({'indice sectoriel, non achetable' if r['kind']=='index' else 'ETF local'}) non disponible chez Revolut : secteur lu via un panier APEX des grandes valeurs. Pour s'exposer au pays, ETF {head['tv']}."
            row['ex_ref']=tvcheck(r['sym'])[0]; r['kind']='basket'; row['kind']='basket'
        if r['kind'] in('etf','index'):
            w,m=K.yweekly(yfile(r['sym'])); tv,tvd=tvcheck(r['sym'])
            row.update({'sym':r['sym'],'etf':m.get('longName') or tvd or r['sym'],'tv':tv,'currency':m.get('currency'),'url':f"https://finance.yahoo.com/quote/{urllib.parse.quote(r['sym'])}/history/",'retrieved':mtime(yfile(r['sym']))})
            wc=[x for x in w if x[2]]; opn=K.yopens(yfile(r['sym']))
        else:
            b=basket(mem[:10]); 
            if b[0] is None or len(b[0])<156:
                row.update({'covered':False,'why':f"non couvert : {len(b[1])} titre(s) coté(s) avec un historique suffisant parmi les grandes capitalisations du secteur (minimum 3, et 3 ans d'historique)."}); rows.append(row); continue
            wc,order,wts=b; opn=None
            row.update({'sym':'Panier APEX','etf':f"Panier APEX {r['nom'].lower()} · {c['nom']} ({len(order)} titres)",'tv':None,'currency':(mem[0].get('currency') or ''),'basket':[{'symbol':k,'name':next(x['name'] for x in mem if x['symbol']==k),'w':wts[k]} for k in order],
                        'url':f"https://finance.yahoo.com/quote/{order[0]}/history/",'retrieved':mtime(B+f'wk/{order[0]}.json')})
        if len(wc)<156 and r['kind']=='basket': row.update({'covered':False,'why':'non couvert : historique insuffisant'}); rows.append(row); continue
        row.update(K.compute([(d,v,True) for d,v,_ in wc]+[],BEN,BN,opn,fsym=r.get('sym'),hl=(K.yhl(yfile(r['sym'])) if r['kind'] in('etf','index') else None)))
        # ETF / indice / panier + 5 actions
        cand=[]
        for x in mem:   # on n'invente rien : seulement les titres du screen déjà téléchargés (qs+wk). Au-delà des 8 premiers, les fichiers manquent souvent.
            q=x['q']; w=wkly(x['symbol'])
            if not q or not w or len(w)<30: continue
            tv,_=tvcheck(x['symbol'])
            cand.append({'ticker':x['symbol'],'name':q['name'] or x['name'],'tv':tv,'m':{k:(None if v is None else round(v,2)) for k,v in q['m'].items()},'analysts':q['analysts'],
                         'industry':q['industry'],'timing':timing(w),'mrq':q['mrq'],'retrieved':q['retrieved'],'currency':q['currency'],'cap':x['cap']})
        el=score(cand,prof)
        for x in el:
            if not x['tv']: x['eligible']=False; x['why_not']='symbole TradingView non vérifié'
        el=[x for x in el if x['tv']]
        top=[]
        for x in el:      # jusqu'à 10, parmi les éligibles achetables au comptant chez Revolut ou XTB (OMI, pas CFD). Pas de titre hors univers.
            u=RV.rep(x['tv'])
            if u:
                w2,m2=K.yweekly(B+f"wk/{u['yahoo']}.json")
                x=dict(x,ticker=u['yahoo'],tv=u['tv'],name=m2.get('longName') or u['nom'],currency='USD',timing=timing([z for z in w2 if z[2]]),ref_local=u['old'],
                       note_revolut=f"Action locale {u['old']} non disponible chez Revolut : ADR {u['tv']} (même société, cotée en dollars). Fondamentaux de la société ; timing sur l'ADR.")
            if not CC.cash_ok(x['tv']): continue
            top.append(x)
            if len(top)>=PANIER_ACTUEL: break
        row['fond']={'profile':prof,'universe':len(cand),'eligible':len(el),'top':top,'covered':len(el)>=3,'excluded':[[x['ticker'],x['why_not']] for x in cand if not x['eligible']],
                     'pool':[x['symbol'] for x in mem if wkly(x['symbol']) and x.get('q')]}
        rows.append(row)
    res['countries'].append({'cc':cc,'nom':c['nom'],'flag':c['flag'],'bench':c['bench'],'bench_nom':c['bench_nom'],'bench_url':f"https://finance.yahoo.com/quote/{urllib.parse.quote(c['bench'])}/history/",
        'currency':bm.get('currency'),'head':head,'rows':rows,'screen_retrieved':SCR['retrieved']})
json.dump(res,open(R+'data/pays.json','w'),ensure_ascii=False)
for C in res['countries']:
    h=C['head']; print(f"\n== {C['nom']} | tête {h['sym']} {h['tv']} S {h['sent']['value']} AV {h['av']['score']} {h['date']}")
    for r in C['rows']:
        if not r['covered']: print('   ',r['nom'][:26].ljust(26),'NON COUVERT',r['why'][:80]); continue
        f=r['fond']; print('   ',r['nom'][:26].ljust(26),r['sym'][:11].ljust(11),(r['tv'] or '-').ljust(14),'S',str(r['sent']['value']).rjust(5),'AV',str(r['av']['score']).rjust(6),r['date'],'| 10 act:',f['eligible'],'/',f['universe'],[x['tv'] for x in f['top']])
