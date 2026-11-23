"""Étape 2 · taux souverains par pays -> data/obpays.json (graphiques 2 / 10 / 30 ans sur 25 ans, écarts contre le Bund, courbe).
Sources : BCE (taux longs 10 ans FR / DE / IT, mensuels), Bundesbank (Bund 2 / 10 / 30 ans, courbe Svensson, quotidien),
Ministère des Finances du Japon (JGB 2 / 10 / 30 ans, quotidien), OCDE (taux longs 10 ans et taux 3 mois, mensuels), FRED (Treasuries)."""
import os as _os
_APEX_ROOT = _os.path.abspath(_os.environ.get('APEX_ROOT') or _os.path.join(_os.path.dirname(__file__), '..'))
import csv, json, os, datetime as D
from zoneinfo import ZoneInfo
R=_APEX_ROOT + '/'; B=R+'data/obpays/'; O=R+'data/obligations/'
NOW=D.datetime.now(ZoneInfo('Europe/Paris')); START='2001-01'
SRC=json.load(open(B+'sources.json'))
def mt(p): return D.datetime.fromtimestamp(os.path.getmtime(p),ZoneInfo('Europe/Paris')).strftime('%Y-%m-%d %H:%M')
def monthly(daily):
    m={}
    for d,v in daily: m.setdefault(d[:7],[]).append(v)
    return [[k,round(sum(v)/len(v),3)] for k,v in sorted(m.items()) if k>=START]
def bbk(code):
    out=[]
    for r in csv.reader(open(B+f'bbk_{code}.csv',encoding='utf-8-sig')):
        if len(r)>=2 and len(r[0])==10 and r[0][4]=='-' and r[1] not in ('.',''): out.append([r[0],float(r[1])])
    return out
def mof():
    out={}
    for f in ('mof_all.csv','mof_cur.csv'):
        rows=list(csv.reader(open(B+f,encoding='latin-1'))); hdr=next(r for r in rows if r and r[0]=='Date')
        for r in rows:
            if not r or '/' not in r[0]: continue
            y,m,d=r[0].split('/'); k=f'{int(y):04d}-{int(m):02d}-{int(d):02d}'
            out[k]={h:float(v) for h,v in zip(hdr[1:],r[1:]) if v not in ('-','')}
    ks=sorted(out); return {t:[[k,out[k][t]] for k in ks if t in out[k]] for t in ('2Y','10Y','30Y')}
def oecd(f):
    d={}
    for x in csv.DictReader(open(B+f)):
        if x['OBS_VALUE']: d.setdefault(x['REF_AREA'],[]).append([x['TIME_PERIOD'],round(float(x['OBS_VALUE']),3)])
    return {k:sorted(v) for k,v in d.items()}
def ecb(c):
    p=O+f'ecb_IRS_{c}.csv'
    if not os.path.exists(p): return None
    return [[r['TIME_PERIOD'],float(r['OBS_VALUE'])] for r in csv.DictReader(open(p)) if r['OBS_VALUE']]
def fred(s): return [[a,float(b)] for a,b in list(csv.reader(open(O+f'fred_{s}.csv')))[1:] if b not in ('','.')]
def oecd_merge(primary, extra):
    a=oecd(primary)
    if os.path.exists(B+extra):
        b=oecd(extra)
        for k,v in b.items():
            if k in a:
                d={x[0]:x[1] for x in a[k]}
                for m,val in v: d[m]=val
                a[k]=sorted(d.items())
            else:
                a[k]=v
    return a
LT=oecd_merge('oecd_irlt.csv','oecd_irlt_extra.csv'); ST=oecd_merge('oecd_ir3.csv','oecd_ir3_extra.csv'); J=mof()
BBK={k:bbk(c) for k,c in (('2','R02XX'),('10','R10XX'),('30','R30XX'))}
EC={c:ecb(c) for c in ('FR','DE','IT')}
OECD_LT='https://data-explorer.oecd.org/vis?df[ds]=dsDisseminateFinalDMZ&df[id]=DSD_STES%40DF_FINMARK&df[ag]=OECD.SDD.STES'
def ecb_src(c): return {'nom':f'BCE IRS.M.{c}.L.L40.CI.0000.EUR.N.Z (taux long de convergence, mensuel)','url':f'https://data.ecb.europa.eu/data/datasets/IRS/IRS.M.{c}.L.L40.CI.0000.EUR.N.Z','retrieved':mt(O+f'ecb_IRS_{c}.csv')}
def oecd_src(kind): f='oecd_irlt.csv' if kind=='lt' else 'oecd_ir3.csv'; return {'nom':'OCDE, '+('taux longs IRLT (emprunts d\'État ~10 ans, mensuel)' if kind=='lt' else 'taux courts IR3TIB (3 mois interbancaire, mensuel)'),'url':OECD_LT,'retrieved':SRC[f]['retrieved']}
BBK_S={'nom':'Bundesbank BBSIS, rendements des titres fédéraux (courbe Svensson, échéances résiduelles 2 / 10 / 30 ans, quotidien)','url':'https://www.bundesbank.de/en/statistics/money-and-capital-markets/interest-rates-and-yields/term-structure-of-interest-rates-on-listed-federal-securities','retrieved':SRC['bbk_R10XX.csv']['retrieved']}
MOF_S={'nom':'Ministère des Finances du Japon, JGB Interest Rate (quotidien)','url':'https://www.mof.go.jp/english/policy/jgbs/reference/interest_rate/index.htm','retrieved':SRC['mof_cur.csv']['retrieved']}
FRED_S={'nom':'FRED DGS2 / DGS10 / DGS30 / DGS3MO (quotidien)','url':'https://fred.stlouisfed.org/series/DGS10','retrieved':mt(O+'fred_DGS10.csv')}
def last(s): return s[-1] if s else None
def pct(series,v):
    h=[x[1] for x in series]; return round(100*(sum(1 for x in h if x<v)+.5*sum(1 for x in h if x==v))/len(h))
def spread(a,b):
    bm=dict(b); return [[m,round(v-bm[m],3)] for m,v in a if m in bm and m>=START]
def pack(cc,nom,y,ylast,short,sources,missing,spr=None,spr_nom=None,daily=None):
    """y: {'2':monthly,'10':monthly,'30':monthly} ; ylast: dernière valeur (date, taux) par échéance ; short: taux 3 mois mensuel"""
    y10=y['10']; out={'cc':cc,'nom':nom,'y':{k:v for k,v in y.items() if v},'last':ylast,'short':short[-1] if short else None,'short_series':[x for x in short if x[0]>=START] if short else None,
       'sources':sources,'missing':missing}
    out['pct10']=pct(y10,y10[-1][1]); mx=max(y10,key=lambda x:x[1]); mn=min(y10,key=lambda x:x[1]); out['max10']=mx; out['min10']=mn
    # pente : 10 ans − 2 ans si le 2 ans existe, sinon 10 ans − 3 mois (OCDE)
    if y.get('2'): sl=spread(y['10'],y['2']); out['slope']={'nom':'10 ans − 2 ans','series':sl,'last':sl[-1] if sl else None}
    elif short: sl=spread(y['10'],short); out['slope']={'nom':'10 ans − 3 mois','series':sl,'last':sl[-1] if sl else None}
    else: out['slope']={'nom':'pente non calculée','series':[],'last':None}
    inv=[x for x in out['slope']['series'] if x[1]<0]; out['slope']['inv_last']=inv[-1][0] if inv else None
    out['curve']=[[m,v] for m,v in (('3 mois',short[-1] if short else None),('2 ans',ylast.get('2')),('10 ans',ylast.get('10')),('30 ans',ylast.get('30'))) if v]
    if spr: out['spread']={'nom':spr_nom,'series':spr,'last':spr[-1],'pct':pct(spr,spr[-1][1]),'max':max(spr,key=lambda x:x[1]),'min':min(spr,key=lambda x:x[1])}
    return out
res={'generated':NOW.strftime('%Y-%m-%d %H:%M'),'countries':{}}
# États-Unis
F={k:fred(s) for k,s in (('2','DGS2'),('10','DGS10'),('30','DGS30'))}; F3=monthly(fred('DGS3MO'))
res['countries']['us']=pack('us','États-Unis',{k:monthly(v) for k,v in F.items()},{k:last(v) for k,v in F.items()},F3,[FRED_S],[])
# Allemagne
deM={k:monthly(v) for k,v in BBK.items()}
res['countries']['de']=pack('de','Allemagne',deM,{k:last(v) for k,v in BBK.items()},ST['DEU'],[BBK_S,oecd_src('st')],[],None)
res['countries']['de']['short_nom']='Euribor 3 mois (zone euro)'
# France
fr=[x for x in EC['FR'] if x[0]>=START]; de10=[x for x in EC['DE'] if x[0]>=START]
res['countries']['fr']=pack('fr','France',{'2':None,'10':fr,'30':None},{'10':[fr[-1][0],fr[-1][1]]},ST['FRA'],[ecb_src('FR'),ecb_src('DE'),oecd_src('st')],
   ['OAT 2 ans et 30 ans : non récupéré (séries quotidiennes Banque de France / Agence France Trésor non accessibles en téléchargement automatique ; la BCE ne publie par pays que le taux 10 ans)'],spread(fr,de10),'OAT − Bund 10 ans (BCE)')
res['countries']['fr']['short_nom']='Euribor 3 mois (zone euro)'
# Italie
it=EC['IT']; itsrc=ecb_src('IT') if it else oecd_src('lt')
if not it: it=LT['ITA']; de10b=LT['DEU']; snom='BTP − Bund 10 ans (OCDE)'
else: de10b=de10; snom='BTP − Bund 10 ans (BCE)'
it=[x for x in it if x[0]>=START]
res['countries']['it']=pack('it','Italie',{'2':None,'10':it,'30':None},{'10':[it[-1][0],it[-1][1]]},ST['ITA'],[itsrc,ecb_src('DE'),oecd_src('st')],
   ['BTP 2 ans et 30 ans : non récupéré (pas de source gratuite téléchargeable trouvée : Banca d\'Italia / MEF sans API publique simple)'],spread(it,de10b),snom)
res['countries']['it']['short_nom']='Euribor 3 mois (zone euro)'
# Japon
jM={'2':monthly(J['2Y']),'10':monthly(J['10Y']),'30':monthly(J['30Y'])}
res['countries']['jp']=pack('jp','Japon',jM,{'2':last(J['2Y']),'10':last(J['10Y']),'30':last(J['30Y'])},ST['JPN'],[MOF_S,oecd_src('st')],[])
# Corée, Australie : OCDE uniquement
for cc,code,nom,miss in (('kr','KOR','Corée du Sud','KTB 2 ans et 30 ans : non récupéré (la Banque de Corée, ECOS, exige une clé API ; non utilisée)'),
                         ('au','AUS','Australie','ACGB 2 ans et 30 ans : non récupéré (le site de la Reserve Bank of Australia refuse le téléchargement automatique, erreur 403)')):
    lt=[x for x in LT[code] if x[0]>=START]
    res['countries'][cc]=pack(cc,nom,{'2':None,'10':lt,'30':None},{'10':[lt[-1][0],lt[-1][1]]},ST[code],[oecd_src('lt'),oecd_src('st')],[miss])
# Canada : OCDE IRLT / IR3 (2000-), écart vs Bund ; 2 ans et 30 ans non récupérés automatiquement
if 'CAN' in LT:
    lt=[x for x in LT['CAN'] if x[0]>=START]
    de10b=[x for x in (EC.get('DE') or LT.get('DEU') or []) if x[0]>=START]
    miss_ca="Obligation fédérale 2 ans et 30 ans : non récupérés automatiquement. Taux 10 ans et 3 mois : OCDE IRLT / IR3TIB (dernière observation parfois décalée d'un ou deux mois). Aucun ETF d'État canadien UCITS trouvé au comptant dans la table XTB OMI."
    res['countries']['ca']=pack('ca','Canada',{'2':None,'10':lt,'30':None},{'10':[lt[-1][0],lt[-1][1]]},ST.get('CAN') or [],[oecd_src('lt'),oecd_src('st'),ecb_src('DE')],[miss_ca],spread(lt,de10b),'Canada 10 ans − Bund 10 ans (OCDE / BCE)')

# Espagne, Pays-Bas, Belgique : taux 10 ans BCE (convergence), court OCDE, écart vs Bund
EC_NEW={c:ecb(c) for c in ('ES','NL','BE')}
def add_eu(cc, code, iso, nom, titre_spr):
    series=EC_NEW.get(iso)
    src=[oecd_src('st')]
    if series:
        y10=[x for x in series if x[0]>=START]
        src=[ecb_src(iso), ecb_src('DE'), oecd_src('st')]
    else:
        y10=[x for x in LT.get(code,[]) if x[0]>=START]
        src=[oecd_src('lt'), ecb_src('DE'), oecd_src('st')]
    de10b=[x for x in (EC.get('DE') or LT.get('DEU') or []) if x[0]>=START]
    short=ST.get(code) or ST.get('DEU') or []
    miss=[f"{nom} : taux 2 ans et 30 ans non récupérés (la BCE ne publie par pays que le taux 10 ans)."]
    res['countries'][cc]=pack(cc,nom,{'2':None,'10':y10,'30':None},{'10':[y10[-1][0],y10[-1][1]]},short,src,miss,spread(y10,de10b),titre_spr)
    res['countries'][cc]['short_nom']='Euribor 3 mois (zone euro)'

add_eu('es','ESP','ES','Espagne','Bonos − Bund 10 ans (BCE)')
add_eu('nl','NLD','NL','Pays-Bas','DSL − Bund 10 ans (BCE)')
add_eu('be','BEL','BE','Belgique','OLO − Bund 10 ans (BCE)')

# Royaume-Uni, Suisse : OCDE (taux longs ~10 ans)
for cc,code,nom,sprnom,miss in (
    ('gb','GBR','Royaume-Uni','Gilt − Bund 10 ans (OCDE / BCE)','Gilt 2 ans et 30 ans : non récupérés automatiquement. Taux 10 ans : OCDE IRLT, dernière observation parfois décalée d’un ou deux mois.'),
    ('ch','CHE','Suisse','Confédération − Bund 10 ans (OCDE / BCE)','Confédération 2 ans et 30 ans : non récupérés automatiquement. Taux 10 ans : OCDE IRLT.'),
):
    lt=[x for x in LT[code] if x[0]>=START]
    de10b=[x for x in (EC.get('DE') or LT.get('DEU') or []) if x[0]>=START]
    short=ST.get(code) or []
    # écarter un taux court trop ancien (plus de 18 mois) pour ne pas afficher une pente périmée
    cutoff=(NOW.date().replace(day=1) - D.timedelta(days=548)).isoformat()[:7]
    if short and short[-1][0] < cutoff:
        miss = miss + f" Taux 3 mois OCDE arrêté en {short[-1][0]}, trop ancien pour calculer une pente récente."
        short=[]
    src=[oecd_src('lt'), oecd_src('st')]
    if EC.get('DE'): src.append(ecb_src('DE'))
    res['countries'][cc]=pack(cc,nom,{'2':None,'10':lt,'30':None},{'10':[lt[-1][0],lt[-1][1]]},short,src,[miss],spread(lt,de10b),sprnom)

KEEP_CC={'us','fr','de','ca','ch'}  # univers t322u
res['countries']={k:v for k,v in res['countries'].items() if k in KEEP_CC}
json.dump(res,open(R+'data/obpays.json','w'),ensure_ascii=False)
for cc,c in res['countries'].items():
    print(cc,c['nom'],'|',{k:(v[0][0],len(v)) for k,v in c['y'].items()},'| last',c['last'],'| 3m',c['short'],'|',c['slope']['nom'],c['slope']['last'],'| spread',c.get('spread',{}).get('last'),'| pct10',c['pct10'],'| missing',len(c['missing']))
