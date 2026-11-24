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
t=open(B+'src/template.html').read()
t=t.replace('__DATA__',esc(open(B+'data/dashboard_data.json').read())).replace('__DATA2__',esc(open(B+'data/tabs_data.json').read())).replace('__DATA3__',esc(open(B+'data/indicateur.json').read())).replace('/*__TABSJS__*/',open(B+'src/tabs.js').read()).replace('/*__INDJS__*/',open(B+'src/indicateur.js').read()).replace('__DATA4__',esc(open(B+'data/achatvente.json').read())).replace('/*__AVJS__*/',open(B+'src/achatvente.js').read()).replace('__DATA5__',esc(open(B+'data/secteurs.json').read())).replace('__DATA6__',esc(open(B+'data/fondamentaux.json').read())).replace('/*__FONDJS__*/',open(B+'src/fonds.js').read()).replace('/*__SECJS__*/',open(B+'src/secteurs.js').read()).replace('__DATA7__',esc(open(B+'data/obligations.json').read())).replace('/*__OBJS__*/',open(B+'src/obligations.js').read()).replace('__DATA8__',esc(open(B+'data/pays.json').read())).replace('__DATA9__',esc(open(B+'data/obpays.json').read())).replace('__DATA10__',esc(open(B+'data/metaux.json').read())).replace('/*__METJS__*/',open(B+'src/metaux.js').read()).replace('/*__PAYSJS__*/',open(B+'src/pays.js').read()).replace('__DATA11__',esc(open(B+'data/positions.json').read())).replace('__DATA12__',esc(open(B+'data/disponibilites.json').read())).replace('__DATA13__',esc(open(B+'data/positions_revolutx.json').read())).replace('__DATA14__',esc(open(B+'data/positions_revolut.json').read())).replace('__DATA15__',esc(open(B+'data/obligations_dispo.json').read())).replace('__DATA16__',esc(open(B+'data/apex_bars.json').read())).replace('__DATA17__',esc(open(B+'data/placements.json').read())).replace('__DATA18__',esc(open(B+'data/template_trade.json').read())).replace('/*__POSJS__*/',open(B+'src/positions.js').read()).replace('/*__DISPOJS__*/',open(B+'src/dispo.js').read()).replace('/*__ACCJS__*/',open(B+'src/acc.js').read()).replace('/*__ACCUEILJS__*/',open(B+'src/accueil.js').read()).replace('/*__PLCJS__*/',open(B+'src/placements.js').read()).replace('__DATA19__',esc(open(B+'config/regles.json').read())).replace('/*__TTJS__*/',open(B+'src/template_trade.js').read()).replace('/*__RGJS__*/',open(B+'src/regles.js').read()).replace('/*__GIJS__*/',open(B+'src/good_invest.js').read()).replace('__DATA_ETF__',esc(open(B+'config/etf_reference.json').read())).replace('/*__SEARCHJS__*/',open(B+'src/recherche.js').read())
maj=''
_mp=_P(B+'data/maj.json')
if _mp.exists():
    maj=_mp.read_text()
t=t.replace('__MAJ__', esc(maj) if maj else 'null')
gi=''
_gp=_P(B+'data/good_invest.json')
if _gp.exists():
    gi=_gp.read_text()
t=t.replace('__GI__', esc(gi) if gi else 'null')

def _slim_pilot(raw):
    import json as _json
    d=_json.loads(raw)
    keep=('tv','ticker','nom','kind','ok','erreur','total','total_max','total_min',
          'display','band','hex','ligne','points','is_bank','regles','watchlist_tv')
    def v2_band(total):
        try:
            n=float(total)
        except (TypeError,ValueError):
            return None,None
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
# copie vers le site publié si distinct
try:
    if _SITE and _P(_SITE).resolve()!=_P(B).resolve():
        dest=_P(_SITE)/'index.html'
        dest.write_text(t)
        print('site', dest, 'bytes', dest.stat().st_size)
        _spj=_P(B+'data/apex_achat_v2_site.json')
        if _spj.exists():
            sdest=_P(_SITE)/'data'/'apex_achat_v2_site.json'
            sdest.parent.mkdir(parents=True, exist_ok=True)
            sdest.write_text(_spj.read_text())
            print('site pilot json', sdest, 'bytes', sdest.stat().st_size)
except Exception as e:
    print('site copy skipped', e)
