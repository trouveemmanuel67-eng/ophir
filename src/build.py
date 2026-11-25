import json, sys, os
from pathlib import Path as _P
_ROOT = _P(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))
try:
    from apex.paths import root, site_dir
    B=str(root())+'/'
    _SITE=site_dir()
except Exception:
    B=str(_ROOT)+'/'
    _SITE=_ROOT
esc=lambda t:t.replace('</','<\\/')

def _slim_pays(raw):
    """t455u : n'embarquer que les pays de l'univers Actions (USA, France)."""
    import json as _json
    d=_json.loads(raw)
    keep=set(d.get('univers_actions') or ['USA','France'])
    d['countries']=[c for c in (d.get('countries') or []) if (c or {}).get('nom') in keep]
    d['univers_actions']=sorted(keep, key=lambda x: (x!='USA', x!='France', x))
    return _json.dumps(d, ensure_ascii=False, separators=(',',':'))

t=open(B+'src/template.html').read()
def _dispo_slim(raw):
    """t509 : les produits retirés du site (config/retraits_site.json) ne sont pas embarqués non plus."""
    try:
        R=set((json.load(open(B+'config/retraits_site.json',encoding='utf-8')).get('retires') or {}).keys())
    except Exception:
        return raw
    d=json.loads(raw)
    import re as _re
    codes=sorted({k.split(':')[-1] for k in R},key=len,reverse=True)
    rx=_re.compile(r'(?<![A-Za-z0-9])('+'|'.join(map(_re.escape,codes))+r')(?![A-Za-z0-9])')
    def scrub(t):
        if not rx.search(t): return t
        parts=_re.split(r'(?<=[.;])\s+',t)
        return ' '.join(x for x in parts if not rx.search(x))
    def walk(o):
        if isinstance(o,dict):
            for k in [k for k in o if k in R or (isinstance(o[k],dict) and o[k].get('tv') in R)]: o.pop(k)
            for k,v in list(o.items()):
                if isinstance(v,str): o[k]=scrub(v)
                else: walk(v)
        elif isinstance(o,list):
            o[:]=[v for v in o if not (isinstance(v,dict) and v.get('tv') in R) and v not in R]
            for v in o: walk(v)
    walk(d)
    return json.dumps(d,ensure_ascii=False)
t=t.replace('__DATA__',esc(open(B+'data/dashboard_data.json').read())).replace('__DATA2__',esc(open(B+'data/tabs_data.json').read())).replace('__DATA3__',esc(open(B+'data/indicateur.json').read())).replace('/*__TABSJS__*/',open(B+'src/tabs.js').read()).replace('/*__INDJS__*/',open(B+'src/indicateur.js').read()).replace('__DATA4__',esc(open(B+'data/achatvente.json').read())).replace('/*__AVJS__*/',open(B+'src/achatvente.js').read()).replace('__DATA5__',esc(open(B+'data/secteurs.json').read())).replace('__DATA6__',esc(open(B+'data/fondamentaux.json').read())).replace('/*__FONDJS__*/',open(B+'src/fonds.js').read()).replace('/*__SECJS__*/',open(B+'src/secteurs.js').read()).replace('__DATA7__',esc(open(B+'data/obligations.json').read())).replace('/*__OBJS__*/',open(B+'src/obligations.js').read()).replace('__DATA8__',esc(_slim_pays(open(B+'data/pays.json').read()))).replace('__DATA9__',esc(open(B+'data/obpays.json').read())).replace('__DATA10__',esc(open(B+'data/metaux.json').read())).replace('/*__METJS__*/',open(B+'src/metaux.js').read()).replace('/*__PAYSJS__*/',open(B+'src/pays.js').read()).replace('__DATA11__',esc(open(B+'data/positions.json').read())).replace('__DATA12__',esc(_dispo_slim(open(B+'data/disponibilites.json').read()))).replace('__DATA13__',esc(open(B+'data/positions_revolutx.json').read())).replace('__DATA14__',esc(open(B+'data/positions_revolut.json').read())).replace('__DATA15__',esc(open(B+'data/obligations_dispo.json').read())).replace('__DATA16__',esc(open(B+'data/apex_bars.json').read())).replace('__DATA17__',esc(open(B+'data/placements.json').read())).replace('__DATA18__',esc(open(B+'data/template_trade.json').read())).replace('/*__POSJS__*/',open(B+'src/positions.js').read()).replace('/*__DISPOJS__*/',open(B+'src/dispo.js').read()).replace('/*__ACCJS__*/',open(B+'src/acc.js').read()).replace('/*__ACCUEILJS__*/',open(B+'src/accueil.js').read()).replace('/*__PLCJS__*/',open(B+'src/placements.js').read()).replace('__DATA19__',esc(open(B+'config/regles.json').read())).replace('/*__TTJS__*/',open(B+'src/template_trade.js').read()).replace('/*__RGJS__*/',open(B+'src/regles.js').read()).replace('/*__BDGJS__*/',open(B+'src/budget.js').read()).replace('/*__GIJS__*/',open(B+'src/good_invest.js').read()).replace('/*__GSJS__*/',open(B+'src/best_short.js').read()).replace('__DATA_ETF__',esc(open(B+'config/etf_reference.json').read())).replace('/*__SEARCHJS__*/',open(B+'src/recherche.js').read())
maj=''
# t537u : sentiment sectoriel (tableau de la page Règles)
_sent=_P(B+'data/sentiment_secteurs.json')
if _sent.exists():
    try:
        _sd=_json.loads(_sent.read_text()) if '_json' in globals() else __import__('json').loads(_sent.read_text())
        _keep=('value','label','court','date','points_long','points_short')
        _slim={'cnn':{k:(_sd.get('cnn') or {}).get(k) for k in _keep}}
        for _g in ('secteurs_us','secteurs_eu','classes'):
            _slim[_g]={_k:{k:_v.get(k) for k in _keep} for _k,_v in (_sd.get(_g) or {}).items()}
        t=t.replace('/*__SENTDATA__*/null', esc(__import__('json').dumps(_slim,ensure_ascii=False)))  # toutes les occurrences (achatvente.js + regles.js)
    except Exception as _e:
        print('sentiment_secteurs ignoré', _e)
_mp=_P(B+'data/maj.json')
if _mp.exists():
    maj=_mp.read_text()
t=t.replace('__MAJ__', esc(maj) if maj else 'null')
gi=''
_gp=_P(B+'data/good_invest.json')
if _gp.exists():
    gi=_gp.read_text()
t=t.replace('__GI__', esc(gi) if gi else 'null')

_rot=_P(B+'data/rotation.json')
rot=_rot.read_text() if _rot.exists() else ''
t=t.replace('__DATA_ROTATION__', esc(rot) if rot else 'null')
_rotc=_P(B+'data/rotation_capitaux.json')
rotc=_rotc.read_text() if _rotc.exists() else ''
t=t.replace('__DATA_ROTATION_CAPITAUX__', esc(rotc) if rotc else 'null')
_irjs=_P(B+'src/rotation.js')
t=t.replace('/*__IRJS__*/', _irjs.read_text() if _irjs.exists() else '')
_evt=_P(B+'data/evenements_sous_jacents.json')
evt=_evt.read_text() if _evt.exists() else ''
t=t.replace('__DATA_EVT__', esc(evt) if evt else 'null')
_evtjs=_P(B+'src/evenements.js')
t=t.replace('/*__EVTJS__*/', _evtjs.read_text() if _evtjs.exists() else '')


def _slim_pilot(raw):
    import json as _json
    d=_json.loads(raw)
    keep=('tv','ticker','nom','kind','ok','erreur','total','total_max','total_min',
          'display','band','hex','ligne','points','is_bank','regles','watchlist_tv','attention','sentiment')
    def v2_band(total):
        try:
            n=float(total)
        except (TypeError,ValueError):
            return None,None
        # t506u : échelle unique −50 à 250 (violet < 10, rouge 10–69, orange 70–129, vert 130–189, cyan ≥ 190)
        if n>=190: return 'cyan','#00e5ff'
        if n>=130: return 'vert','#22c55e'
        if n>=70: return 'orange','#ff8c1a'
        if n>=10: return 'rouge','#ff2d2d'
        return 'violet','#9d54ff'
    def rec(r):
        if not r: return r
        out={k:r[k] for k in keep if k in r}
        if out.get('total') is not None:
            b,h=v2_band(out['total'])
            if b:
                out['band']=b
                out['hex']=h
        return out
    KEEP_PAYS={'USA','France'}
    pil_all=d.get('pilotes') or {}
    keep_ids={sid for sid,pl in pil_all.items() if (pl or {}).get('pays') in KEEP_PAYS}
    keep_tv=set()
    for sid in keep_ids:
        pl=pil_all[sid]
        if (pl.get('etf') or {}).get('tv'): keep_tv.add(pl['etf']['tv'])
        for a in pl.get('actions') or []:
            if a.get('tv'): keep_tv.add(a['tv'])
    # positions détenues hors univers (ex. MBG) : conserver la note
    try:
        pos=_json.loads(_P(B+'data/positions.json').read_text())
        for item in (pos.get('positions') or []):
            if item.get('type') not in ('equity',):
                continue
            for k in (item.get('fiche_tv'), item.get('tv_note'), item.get('tv')):
                if k and k!='pas de note':
                    keep_tv.add(k)
    except Exception:
        pass
    # t506u : tête de marché France (ETF CAC 40) notée sur 250 par src/harmonise250.py
    keep_tv|={tv for tv,r in (d.get('by_tv') or {}).items() if (r or {}).get('tete_pays') in KEEP_PAYS}
    by={tv:rec(r) for tv,r in (d.get('by_tv') or {}).items() if tv in keep_tv}
    # alias TradingView des positions (fiche_tv vs tv_note) vers la même note
    try:
        pos=_json.loads(_P(B+'data/positions.json').read_text())
        for item in (pos.get('positions') or []):
            if item.get('type') not in ('equity',):
                continue
            keys=[k for k in (item.get('fiche_tv'), item.get('tv_note'), item.get('tv')) if k and k!='pas de note']
            hit=next((by[k] for k in keys if k in by), None)
            if hit:
                for k in keys:
                    if k not in by:
                        by[k]=hit
    except Exception:
        pass
    pilotes={}
    for sid,pl in pil_all.items():
        if sid not in keep_ids:
            continue
        pilotes[sid]={
            'section':pl.get('section'),
            'secteur_sym':pl.get('secteur_sym') or sid,
            'pays':pl.get('pays'),
            'etf':rec(pl.get('etf') or {}),
            'actions':[rec(a) for a in (pl.get('actions') or [])],
            'n_banques':pl.get('n_banques'),
            'n_hors_banque':pl.get('n_hors_banque'),
        }
    fg=d.get('fear_greed') or {}
    series=list(fg.get('series') or [])
    if len(series)>52: series=series[-52:]
    out={
        'generated':d.get('generated'),
        'pilot':True,
        'scale':d.get('scale') or {'min':-50,'max':250},
        'attention_meta':d.get('attention_meta'),
        'fear_greed':{k:fg[k] for k in ('value','label','date','points','source') if k in fg},
        'pilotes':pilotes,
        'secteurs_pilotes':[s for s in (d.get('secteurs_pilotes') or list(pilotes)) if s in keep_ids],
        'by_tv':by,
        'stats':d.get('stats'),
    }
    if series:
        out['fear_greed']['series']=series
    return _json.dumps(out, ensure_ascii=False, separators=(',',':'))

_pp=_P(B+'data/apex_achat_v2_pilot.json')
pilot=''
if _pp.exists():
    pilot=_slim_pilot(_pp.read_text())
    _spj=_P(B+'data/apex_achat_v2_site.json')
    _spj.write_text(pilot)
    print('pilot slim', len(pilot), 'from', _pp.stat().st_size)
t=t.replace('__DATA_PILOT__', esc(pilot) if pilot else 'null')

# APE-32 : note SHORT sur 250 (src/build_short250.py) pour Meilleurs SHORT
_sh=_P(B+'data/apex_short.json')
short=''
if _sh.exists():
    _sd=json.loads(_sh.read_text())
    for _r in (_sd.get('by_tv') or {}).values():
        (_r.get('fond') or {}).pop('elements', None)
    short=json.dumps(_sd, ensure_ascii=False, separators=(',',':'))
    print('short', len(short))
t=t.replace('__DATA_SHORT__', esc(short) if short else 'null')


# identifiant de build (cache-busting) : horodatage Paris + sha court si dispo
import datetime as _dt, subprocess as _sp
from zoneinfo import ZoneInfo as _TZ
_build=_dt.datetime.now(_TZ('Europe/Paris')).strftime('%Y%m%d-%H%M%S')
try:
    _sha=_sp.check_output(['git','-C',str(_SITE if "_SITE" in dir() else B),'rev-parse','--short','HEAD'], text=True, stderr=_sp.DEVNULL).strip()
    if _sha:
        _build=_sha+'-'+_build
except Exception:
    pass
t=t.replace('__BUILD__', _build)
(_P(B)/'data'/'build-version.json').write_text('{"version":"%s"}\n'%_build, encoding='utf-8')
print('build', _build)

open(B+'index.html','w').write(t)
print('ok',len(t))

# t456u : index.html recharge positions.json, positions_revolut.json et
# positions_revolutx.json à la racine (fetch cache:no-cache). Ces copies
# doivent suivre data/, sinon elles écrasent le relevé embarqué.
_POS_ROOT=('positions.json','positions_revolut.json','positions_revolutx.json')
def _publish_positions_root(dest_root):
    dest_root=_P(dest_root)
    for fn in _POS_ROOT:
        src=_P(B+'data/'+fn)
        if not src.exists():
            continue
        target=dest_root/fn
        target.write_text(src.read_text(encoding='utf-8'), encoding='utf-8')
        print('positions root', target, 'bytes', target.stat().st_size)
_publish_positions_root(B)
# copie vers le site publié si distinct
try:
    if _SITE and _P(_SITE).resolve()!=_P(B).resolve():
        dest=_P(_SITE)/'index.html'
        dest.write_text(t)
        print('site', dest, 'bytes', dest.stat().st_size)
        _publish_positions_root(_SITE)
        _spj=_P(B+'data/apex_achat_v2_site.json')
        if _spj.exists():
            sdest=_P(_SITE)/'data'/'apex_achat_v2_site.json'
            sdest.parent.mkdir(parents=True, exist_ok=True)
            sdest.write_text(_spj.read_text())
            print('site pilot json', sdest, 'bytes', sdest.stat().st_size)
except Exception as e:
    print('site copy skipped', e)
