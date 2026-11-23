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
t=t.replace('__DATA__',esc(open(B+'data/dashboard_data.json').read())).replace('__DATA2__',esc(open(B+'data/tabs_data.json').read())).replace('__DATA3__',esc(open(B+'data/indicateur.json').read())).replace('/*__TABSJS__*/',open(B+'src/tabs.js').read()).replace('/*__INDJS__*/',open(B+'src/indicateur.js').read()).replace('__DATA4__',esc(open(B+'data/achatvente.json').read())).replace('/*__AVJS__*/',open(B+'src/achatvente.js').read()).replace('__DATA5__',esc(open(B+'data/secteurs.json').read())).replace('__DATA6__',esc(open(B+'data/fondamentaux.json').read())).replace('/*__FONDJS__*/',open(B+'src/fonds.js').read()).replace('/*__SECJS__*/',open(B+'src/secteurs.js').read()).replace('__DATA7__',esc(open(B+'data/obligations.json').read())).replace('/*__OBJS__*/',open(B+'src/obligations.js').read()).replace('__DATA8__',esc(open(B+'data/pays.json').read())).replace('__DATA9__',esc(open(B+'data/obpays.json').read())).replace('__DATA10__',esc(open(B+'data/metaux.json').read())).replace('/*__METJS__*/',open(B+'src/metaux.js').read()).replace('/*__PAYSJS__*/',open(B+'src/pays.js').read()).replace('__DATA11__',esc(open(B+'data/positions.json').read())).replace('__DATA12__',esc(open(B+'data/disponibilites.json').read())).replace('__DATA13__',esc(open(B+'data/positions_revolutx.json').read())).replace('__DATA14__',esc(open(B+'data/positions_revolut.json').read())).replace('__DATA15__',esc(open(B+'data/obligations_dispo.json').read())).replace('__DATA16__',esc(open(B+'data/apex_bars.json').read())).replace('__DATA17__',esc(open(B+'data/placements.json').read())).replace('__DATA18__',esc(open(B+'data/template_trade.json').read())).replace('/*__POSJS__*/',open(B+'src/positions.js').read()).replace('/*__DISPOJS__*/',open(B+'src/dispo.js').read()).replace('/*__ACCJS__*/',open(B+'src/acc.js').read()).replace('/*__ACCUEILJS__*/',open(B+'src/accueil.js').read()).replace('/*__PLCJS__*/',open(B+'src/placements.js').read()).replace('/*__TTJS__*/',open(B+'src/template_trade.js').read()).replace('/*__GIJS__*/',open(B+'src/good_invest.js').read())
maj=''
_mp=_P(B+'data/maj.json')
if _mp.exists():
    maj=_mp.read_text()
t=t.replace('__MAJ__', esc(maj) if maj else 'null')
open(B+'index.html','w').write(t)
print('ok',len(t))
# copie vers le site publié si distinct
try:
    if _SITE and _P(_SITE).resolve()!=_P(B).resolve():
        dest=_P(_SITE)/'index.html'
        dest.write_text(t)
        print('site', dest, 'bytes', dest.stat().st_size)
except Exception as e:
    print('site copy skipped', e)
