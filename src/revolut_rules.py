"""Règle Revolut (validée par Emmanuel le 17/11/2026 20h42) : APEX ne garde que des actifs achetables au comptant chez
Revolut Invest France, sans CFD ; sinon un équivalent. Source : /workspace/invest/revolut_proposition_finale_2026-11-17.csv
  supprimer  -> retiré du site et de la watchlist
  remplacer  -> remplacé par remplacant_symbole_tv (pas de doublon)
  indicateur -> « Repère de marché » : affiché sans note APEX, sans signal achat / vente, sans drapeau
  garder / a_verifier -> inchangé"""
import csv
import os as _os
_APEX_ROOT = _os.path.abspath(_os.environ.get('APEX_ROOT') or _os.path.join(_os.path.dirname(__file__), '..'))
_CSV_CANDIDATES = [
    _os.path.join(_APEX_ROOT, 'config', 'revolut_proposition_finale_2026-11-17.csv'),
    '/workspace/invest/revolut_proposition_finale_2026-11-17.csv',
]
CSV = next((c for c in _CSV_CANDIDATES if _os.path.exists(c)), _CSV_CANDIDATES[0])
ROWS=list(csv.DictReader(open(CSV,encoding='utf-8-sig'),delimiter=';'))
ACT={r['symbole_tv']:r['action'] for r in ROWS}
DEL={r['symbole_tv'] for r in ROWS if r['action']=='supprimer'}|{'AMEX:KOL'}   # KOL : ETF radié, retiré de l'onglet Énergie
IND={r['symbole_tv'] for r in ROWS if r['action']=='indicateur'}
# Yahoo des remplaçants (vérifiés le 17/11/2026) ; métaux spot OANDA : proxy contrat à terme continu Yahoo (pas de spot gratuit)
YAHOO={'XETR:VUAA':'VUAA.MI','XETR:EXI3':'EXI3.DE','XETR:EXXT':'EXXT.DE','XETR:XRS2':'XRS2.DE','XETR:EXW1':'EXW1.DE','XETR:IUSZ':'IUSZ.DE','XETR:SXR2':'SXR2.DE',
 'XETR:XDJP':'XDJP.DE','XETR:GLDA':'GLDA.DE','OANDA:XAUUSD':'GC=F','OANDA:XAGUSD':'SI=F','XETR:SLVR':'SLVR.DE','NYSE:PAAS':'PAAS','OANDA:XPTUSD':'PL=F','OANDA:XPDUSD':'PA=F',
 'XETR:ZPDK':'ZPDK.DE','XETR:ZPDD':'ZPDD.DE','XETR:ZPDS':'ZPDS.DE','XETR:XDW0':'XDW0.DE','XETR:ZPDF':'ZPDF.DE','XETR:ZPDH':'ZPDH.DE','XETR:ZPDI':'ZPDI.DE',
 'XETR:ZPDM':'ZPDM.DE','XETR:IQQ7':'IQQ7.DE','XETR:QDVE':'QDVE.DE','XETR:ZPDU':'ZPDU.DE','XETR:SXRY':'SXRY.DE','NYSE:TAK':'TAK','NYSE:MFG':'MFG',
 'NYSE:MUFG':'MUFG','NYSE:IX':'IX','NYSE:SKM':'SKM','NYSE:SHG':'SHG','NYSE:PKX':'PKX','XETR:IBC6':'IBC6.DE','NYSE:WDS':'WDS','NYSE:BHP':'BHP',
 'XETR:GCRE':'GCRE.DE','XETR:TIUP':'TIUP.DE','XETR:28IY':'28IY.DE','XETR:IUS7':'IUS7.DE','EURONEXT:EMBH':'EMBH.PA','XETR:URNU':'URNU.DE',
 'XETR:U3O8':'U3O8.DE','NYSE:CCJ':'CCJ'}
REP={}
for r in ROWS:
    if r['action']=='remplacer':
        n=r['remplacant_symbole_tv']; REP[r['symbole_tv']]={'tv':n,'nom':r['remplacant_nom'],'revolut':r['remplacant_ticker_revolut'],'yahoo':YAHOO[n],'comment':r['commentaire'],'old':r['symbole_tv'],'old_nom':r['nom']}
REPY={v['yahoo']:v for v in REP.values()}
def keep(tv): return tv is None or tv not in DEL
def rep(tv): return REP.get(tv)
