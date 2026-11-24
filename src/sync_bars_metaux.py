#!/usr/bin/env python3
"""APE-24 : recopie dans apex_bars.json la note APEX des métaux au comptant (OANDA:XAU/XAG/XPT/XPDUSD)
calculée par build_metaux (metaux.json, HYPE 90 comprise), pour que Mes positions et les listes
lisent la même note que l'onglet Métaux. N'ajoute pas d'entrée : met à jour celles qui existent."""
import json, os
from pathlib import Path
ROOT = Path(os.environ.get('APEX_ROOT') or Path(__file__).resolve().parent.parent)
D = ROOT / 'data'
m = json.loads((D / 'metaux.json').read_text(encoding='utf-8'))
spot = {}
for r in m.get('rows') or []:
    for it in ((r.get('mlist') or {}).get('items') or []):
        if it.get('kind') == 'spot' and it.get('apex10') and it.get('tv'):
            spot[it['tv']] = it['apex10']
p = D / 'apex_bars.json'
doc = json.loads(p.read_text(encoding='utf-8'))
n = 0
for tv, a in spot.items():
    b = (doc.get('bars') or {}).get(tv)
    if b is not None and b.get('apex10') != a:
        b['apex10'] = a
        n += 1
p.write_text(json.dumps(doc, ensure_ascii=False) + '\n', encoding='utf-8')
print('apex_bars : métaux au comptant synchronisés', n, '/', len(spot))
