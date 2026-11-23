"""Télécharge les historiques hebdomadaires Yahoo (période max) pour l'onglet ÉNERGIE."""
import os as _os
_APEX_ROOT = _os.path.abspath(_os.environ.get('APEX_ROOT') or _os.path.join(_os.path.dirname(__file__), '..'))
import json, os, time, urllib.parse, urllib.request, sys

R = _APEX_ROOT + '/data/'
O = R + 'energie/'
F = R + 'fibo_max/'
YC = '/workspace/invest/indiv/yc/'
os.makedirs(O, exist_ok=True)
os.makedirs(F, exist_ok=True)
os.makedirs(YC, exist_ok=True)

# Nouveaux symboles (22/11/2026). Les séries déjà notées (URNU, U3O8, CCJ, BTU, XDW0, BNQ9, futures)
# ne sont pas retéléchargées ici, pour ne pas recalculer les notes APEX existantes.
# ^GSPC est écrit seulement dans data/energie/ (pas dans data/actions/).
SYMS = [
    'TTE.PA', 'XOM', 'CVX', 'COP', 'EOG', 'OXY', 'VLO', 'DVN', 'FANG', 'IMO', 'SOBO',
    'TRGP', 'WMB', 'KMI', 'OKE', 'ENB', 'TRP', 'PBA', 'GTT.PA', 'IG.MI',
    'VST', 'NEE', 'ETR', 'AWK', 'SO', 'DUK', 'XEL', 'ENEL.MI', 'EOAN.DE', 'RWE.DE',
    'ENGI.PA', 'FTS', 'AEP', 'AQN', 'BEPC',
    'ENPH', 'CSIQ', 'ENR.DE', 'CEG', 'BLDP',
]
SPX = '^GSPC'

P2 = int(time.time())
# period1 = 1900-01-01 : historique hebdo maximal (comme fetch_fibo_max.py)
URL = 'https://query2.finance.yahoo.com/v8/finance/chart/{sym}?period1=-2208988800&period2={p2}&interval=1wk&events=history'
UA = {'User-Agent': 'Mozilla/5.0'}

def fetch(sym):
    url = URL.format(sym=urllib.parse.quote(sym), p2=P2)
    last = None
    for k in range(3):
        try:
            r = urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30).read()
            return r
        except Exception as e:
            last = e
            time.sleep(3)
    raise last

def valid_chart(raw):
    try:
        d = json.loads(raw)
    except Exception:
        return False, 'JSON invalide', None
    err = (d.get('chart') or {}).get('error')
    res = (d.get('chart') or {}).get('result')
    if err or not res:
        return False, (err or 'pas de résultat'), None
    r0 = res[0]
    ts = r0.get('timestamp') or []
    q = (r0.get('indicators') or {}).get('quote') or [{}]
    closes = [c for c in (q[0].get('close') or []) if c is not None and c > 0]
    meta = r0.get('meta') or {}
    return True, {
        'n': len(closes),
        'n_ts': len(ts),
        'currency': meta.get('currency'),
        'exchange': meta.get('exchangeName') or meta.get('fullExchangeName'),
        'name': meta.get('longName') or meta.get('shortName') or meta.get('symbol'),
        'type': meta.get('instrumentType'),
        'last': closes[-1] if closes else None,
        'regularMarketTime': meta.get('regularMarketTime'),
        'firstTradeDate': meta.get('firstTradeDate'),
        'symbol': meta.get('symbol') or '',
    }, d


FALLBACKS = [
    R + 'pays/wk/{sym}.json',
    R + 'fibo_max/{enc}.json',
    YC + '{enc}.json',
    YC + '{sym}.json',
]

def load_fallback(sym):
    enc = urllib.parse.quote(sym, safe='')
    for pat in FALLBACKS:
        path = pat.format(sym=sym, enc=enc)
        if not os.path.exists(path):
            continue
        try:
            raw = open(path, 'rb').read()
        except Exception:
            continue
        ok, info, _ = valid_chart(raw)
        if ok:
            return raw, info, path
    return None, None, None

def store(sym, raw, dests):
    for p in dests:
        os.makedirs(os.path.dirname(p) or '.', exist_ok=True)
        open(p, 'wb').write(raw)

report = []
for s in SYMS:
    q = urllib.parse.quote(s, safe='')
    paths = [O + 'yahoo_1wk_' + q + '.json', F + q + '.json', YC + q + '.json']
    raw = info = src = None
    try:
        raw = fetch(s)
        ok, info, _ = valid_chart(raw)
        if not ok:
            print('FAIL', s, info)
            raw, info, src = load_fallback(s)
            if raw is None:
                report.append({'sym': s, 'ok': False, 'raison': str(info)})
                open(O + 'yahoo_1wk_' + q + '.fail.txt', 'w').write(str(info))
                time.sleep(0.5)
                continue
            print('FALLBACK', s, src, info['n'] if info else '')
        else:
            print('OK', s, info['name'], 'n=', info['n'], 'last=', info['last'], info['exchange'], info['type'])
        store(s, raw, paths)
        report.append({'sym': s, 'ok': True, 'source': src or 'yahoo', **{k: info[k] for k in info}})
    except Exception as e:
        print('ERR', s, e)
        raw, info, src = load_fallback(s)
        if raw is not None:
            store(s, raw, paths)
            print('FALLBACK', s, src, info['n'] if info else '')
            report.append({'sym': s, 'ok': True, 'source': src, **{k: info[k] for k in info}})
        else:
            report.append({'sym': s, 'ok': False, 'raison': str(e)})
            open(O + 'yahoo_1wk_' + q + '.fail.txt', 'w').write(str(e))
    time.sleep(0.5)

# S&P 500 : copie locale pour les nouvelles notes, sans écraser data/actions/
q = urllib.parse.quote(SPX, safe='')
spx_dest = O + 'yahoo_1wk_' + q + '.json'
raw = info = src = None
try:
    raw = fetch(SPX)
    ok, info, _ = valid_chart(raw)
    if not ok:
        raise RuntimeError(str(info))
    open(spx_dest, 'wb').write(raw)
    print('OK', SPX, 'n=', info['n'], 'last=', info['last'], '->', spx_dest)
    report.append({'sym': SPX, 'ok': True, 'source': 'yahoo', **{k: info[k] for k in info}})
except Exception as e:
    print('ERR', SPX, e)
    fb = R + 'actions/yahoo_1wk_' + q + '.json'
    if os.path.exists(fb):
        raw = open(fb, 'rb').read()
        ok, info, _ = valid_chart(raw)
        if ok:
            open(spx_dest, 'wb').write(raw)
            print('FALLBACK SPX', fb)
            report.append({'sym': SPX, 'ok': True, 'source': fb, **{k: info[k] for k in info}})
        else:
            report.append({'sym': SPX, 'ok': False, 'raison': str(e)})
    else:
        report.append({'sym': SPX, 'ok': False, 'raison': str(e)})

json.dump(report, open(O + 'fetch_report.json', 'w'), ensure_ascii=False, indent=2)
print('--- done', sum(1 for x in report if x['ok']), '/', len(report))
