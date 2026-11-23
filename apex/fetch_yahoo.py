"""Télécharge les séries hebdomadaires. yfinance d'abord, puis query2 Yahoo en secours, avec réessais."""
from __future__ import annotations
import json, time, urllib.parse, urllib.request
from datetime import datetime, timezone
from pathlib import Path

from . import paths
from .config import actifs, actifs_a_suivre

UA = {'User-Agent': 'Mozilla/5.0 (compatible; APEX/1.0)'}
# Indices et contrats requis par les scripts de build (pas tous dans actifs.json).
BENCHMARKS = [
    '^GSPC', '^FCHI', '^GDAXI', '^SSMI', '^GSPTSE', '^VIX',
    'DBC', 'GC=F', 'SI=F', 'PL=F', 'PA=F',
    'EURUSD=X', 'DX-Y.NYB', 'URTH',
]
P1 = -2208988800  # 1900


def _save_chart(path: Path, payload: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding='utf-8')


def _query2(sym: str, tries=4, timeout=40):
    url = (
        f'https://query2.finance.yahoo.com/v8/finance/chart/{urllib.parse.quote(sym)}'
        f'?period1={P1}&period2={int(time.time())}&interval=1wk&events=history'
    )
    last = None
    for k in range(tries):
        try:
            r = urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=timeout)
            js = json.loads(r.read())
            if not (js.get('chart') or {}).get('result'):
                raise ValueError('empty chart')
            return js
        except Exception as e:
            last = e
            time.sleep(1.5 * (k + 1))
    raise last or RuntimeError('query2 failed')


def _yfinance(sym: str):
    import yfinance as yf  # type: ignore
    t = yf.Ticker(sym)
    hist = t.history(period='max', interval='1wk', auto_adjust=False)
    if hist is None or hist.empty:
        raise ValueError('yfinance empty')
    # Convert to Yahoo chart-like JSON so the existing readers still work
    idx = [int(getattr(i, 'timestamp', lambda: i.value // 10**9)()) if hasattr(i, 'timestamp') else int(i.value // 10**9)
           for i in hist.index]
    # pandas Timestamp.timestamp()
    ts = []
    for i in hist.index:
        try:
            ts.append(int(i.timestamp()))
        except Exception:
            ts.append(int(i.value // 10**9))
    def col(name):
        if name not in hist.columns:
            return [None] * len(hist)
        return [None if (v != v) else float(v) for v in hist[name].tolist()]  # NaN != NaN
    payload = {
        'chart': {
            'result': [{
                'meta': {'symbol': sym, 'instrumentType': 'EQUITY', 'dataGranularity': '1wk',
                         'source': 'yfinance',
                         'regularMarketTime': ts[-1] if ts else None,
                         'regularMarketPrice': (col('Close')[-1] if col('Close') else None)},
                'timestamp': ts,
                'indicators': {'quote': [{
                    'open': col('Open'), 'high': col('High'), 'low': col('Low'),
                    'close': col('Close'), 'volume': col('Volume'),
                }]},
            }],
            'error': None,
        }
    }
    return payload


def fetch_symbol(sym: str):
    last = None
    try:
        return _yfinance(sym), 'yfinance'
    except Exception as e:
        last = e
    try:
        return _query2(sym), 'query2'
    except Exception as e:
        raise RuntimeError(f'{sym}: yfinance={last}; query2={e}') from e


def cache_dir() -> Path:
    return paths.data_dir() / 'yahoo_cache'


def existing_paths_for(sym: str) -> list[Path]:
    """Chemins où le moteur lit les séries hebdo. On les crée s'ils n'existent pas encore
    (sur GitHub Actions le dépôt n'embarque pas les ~200 Mo de caches)."""
    data = paths.data_dir()
    enc = urllib.parse.quote(sym, safe='')
    raw = sym
    cands = []
    for folder, prefix in (
        (data / 'fibo_max', ''),
        (data / 'secteurs', 'yahoo_1wk_'),
        (data / 'pays', 'yahoo_1wk_'),
        (data / 'pays' / 'wk', ''),
        (data / 'actions', 'yahoo_1wk_'),
        (data / 'energie', 'yahoo_1wk_'),
        (data / 'metaux', 'y_'),
        (data / 'obligations', 'w_'),
        (data / 'crypto', 'yahoo_1wk_'),
        (data / 'liquidites', 'yahoo_1wk_'),
        (data / 'fx', 'yahoo_1wk_'),
    ):
        folder.mkdir(parents=True, exist_ok=True)
        names = [f'{prefix}{raw}.json']
        if enc != raw:
            names.append(f'{prefix}{enc}.json')
        for name in names:
            cands.append(folder / name)
    cands.append(cache_dir() / f'{enc}.json')
    # unique
    seen, out = set(), []
    for p in cands:
        s = str(p)
        if s not in seen:
            seen.add(s)
            out.append(p)
    return out


def run(limit=None, sleep=0.15) -> dict:
    cache_dir().mkdir(parents=True, exist_ok=True)
    # Univers réduit : pas les titres hors pays (sauf positions encore détenues).
    items = [a for a in actifs_a_suivre() if a.get('yahoo')]
    have = {a['yahoo'] for a in items}
    for sym in BENCHMARKS:
        if sym not in have:
            items.append({'yahoo': sym, 'tv': f'BENCH:{sym}'})
            have.add(sym)
    if limit:
        items = items[: int(limit)]
    ok, absent, missing = [], [], []
    for i, a in enumerate(items, 1):
        sym = a['yahoo']
        tv = a['tv']
        try:
            payload, src = fetch_symbol(sym)
            result = (payload.get('chart') or {}).get('result') or [None]
            ts = (result[0] or {}).get('timestamp') or []
            if not ts:
                absent.append({'tv': tv, 'yahoo': sym, 'raison': 'serie vide'})
                continue
            for p in existing_paths_for(sym):
                _save_chart(p, payload)
            ok.append({'tv': tv, 'yahoo': sym, 'source': src, 'n': len(ts)})
        except Exception as e:
            missing.append({'tv': tv, 'yahoo': sym, 'raison': str(e)})
        if sleep:
            time.sleep(sleep)
        if i % 50 == 0:
            print(f'fetch {i}/{len(items)} ok={len(ok)} fail={len(missing)}', flush=True)
    report = {
        'generated': datetime.now(timezone.utc).isoformat(),
        'n': len(items), 'n_ok': len(ok),
        'cours_absent': absent, 'yahoo_introuvable': missing,
    }
    dest = paths.data_dir() / '_fetch_report.json'
    dest.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print('fetch done', report['n_ok'], '/', report['n'], 'missing', len(missing), 'empty', len(absent))
    return report
