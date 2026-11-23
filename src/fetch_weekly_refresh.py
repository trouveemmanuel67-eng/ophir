"""Retélécharge toutes les séries hebdomadaires Yahoo déjà en cache (après clôture du vendredi).
Écrit le même historique maximal dans tous les chemins existants d'un symbole."""
import os as _os
_APEX_ROOT = _os.path.abspath(_os.environ.get('APEX_ROOT') or _os.path.join(_os.path.dirname(__file__), '..'))
import os, sys, json, glob, time, urllib.parse, urllib.request, datetime as D
from collections import defaultdict

ROOTS = [
    _APEX_ROOT + '/data/fibo_max/*.json',
    '/workspace/invest/indiv/y/*.json',
    '/workspace/invest/indiv/yc/*.json',
    _APEX_ROOT + '/data/secteurs/yahoo_1wk_*.json',
    _APEX_ROOT + '/data/pays/yahoo_1wk_*.json',
    _APEX_ROOT + '/data/pays/wk/*.json',
    _APEX_ROOT + '/data/actions/yahoo_1wk_*.json',
    _APEX_ROOT + '/data/energie/yahoo_1wk_*.json',
    _APEX_ROOT + '/data/metaux/y_*.json',
    _APEX_ROOT + '/data/obligations/w_*.json',
    _APEX_ROOT + '/data/crypto/yahoo_1wk_*.json',
    _APEX_ROOT + '/data/liquidites/yahoo_1wk_*.json',
    _APEX_ROOT + '/data/fx/yahoo_1wk_*.json',
]

PREFIXES = (
    'yahoo_1wk_', 'y_', 'w_',
)

def symbol_from_path(path):
    base = os.path.basename(path)
    if not base.endswith('.json'):
        return None
    name = base[:-5]
    for pref in PREFIXES:
        if name.startswith(pref):
            name = name[len(pref):]
            break
    return urllib.parse.unquote(name)

# Also harvest symbol field from obligations
def collect():
    by = defaultdict(list)
    for pat in ROOTS:
        for p in glob.glob(pat):
            if '/backups/' in p:
                continue
            # skip obviously non-chart files
            try:
                if os.path.getsize(p) < 200:
                    continue
            except OSError:
                continue
            sym = symbol_from_path(p)
            # obligations sometimes store {'symbol': ...} wrapping or raw chart
            try:
                raw = json.load(open(p))
            except Exception:
                continue
            if 'symbol' in raw and 'chart' not in raw:
                sym = raw.get('symbol') or sym
            if not isinstance(raw, dict) or 'chart' not in raw:
                # not a yahoo chart; skip
                continue
            if not sym:
                continue
            by[sym].append(p)
    return by

UA = {'User-Agent': 'Mozilla/5.0 (compatible; APEX/1.0)'}
P1 = -2208988800  # 1900, historique maximal
P2 = int(time.time())

def fetch(sym):
    url = (f'https://query2.finance.yahoo.com/v8/finance/chart/{urllib.parse.quote(sym)}'
           f'?period1={P1}&period2={P2}&interval=1wk&events=history')
    last = None
    for k in range(4):
        try:
            r = urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=40)
            data = r.read()
            js = json.loads(data)
            if not (js.get('chart') or {}).get('result'):
                raise ValueError('empty chart')
            return data
        except Exception as e:
            last = e
            time.sleep(1.5 * (k + 1))
    raise last

def main():
    by = collect()
    print('symboles', len(by), 'fichiers', sum(len(v) for v in by.values()), flush=True)
    ok = fail = 0
    failed = []
    logp = '/tmp/fetch_weekly_refresh.log'
    with open(logp, 'w') as log:
        for i, sym in enumerate(sorted(by), 1):
            try:
                data = fetch(sym)
                for p in by[sym]:
                    # preserve wrapping? these are raw chart files
                    open(p, 'wb').write(data)
                ok += 1
                if i % 25 == 0 or i == len(by):
                    print(f'{i}/{len(by)} ok={ok} fail={fail} last={sym}', flush=True)
            except Exception as e:
                fail += 1
                failed.append(sym)
                log.write(f'{sym}\t{e}\n'); log.flush()
                print('ERR', sym, e, flush=True)
            time.sleep(0.28)
    print('done ok', ok, 'fail', fail)
    if failed:
        print('failed:', ', '.join(failed[:40]), ('...' if len(failed)>40 else ''))
    print('log', logp)

if __name__ == '__main__':
    main()
