#!/usr/bin/env python3
"""Sentiment 0-100 par secteur et par classe d'actifs (t536u / t537u, validé par Emmanuel).

Remplace, comme valeur d'entrée du critère F&G des notes LONG et SHORT, le CNN Fear & Greed
global par le sentiment du secteur (actions) ou de la classe d'actifs (hors actions).
Les barèmes ne changent pas (LONG ±50 par tranches de 10, SHORT ±30 inversé, 6 points par tranche).

Formule (indice composite APEX, non officiel) : moyenne simple de sous-scores 0-100,
rangs percentiles sur 5 × 252 séances, sans donnée future :
  prix (ETF / contrat / indice, clôtures journalières Yahoo) : écart à la SMA 125 j (rang),
  RSI 14 journalier (brut), distance au plus haut 52 semaines (rang), volatilité 20 j inversée (rang),
  performance 21 j (rang) ;
  ampleur (11 secteurs US seulement, holdings SPDR) : % de titres > SMA 50 j, % > SMA 200 j,
  force interne (proches des plus hauts 52 s. − proches des plus bas).
Classes : crypto = alternative.me (officiel) ; immobilier France et liquidités = indices APEX déjà
calculés (data/indicateur.json) ; le reste = même formule prix sur l'actif de référence.

-> data/sentiment_secteurs.json
"""
from __future__ import annotations

import json
import math
import os
import statistics
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import openpyxl

SITE = Path(os.environ.get('APEX_ROOT') or Path(__file__).resolve().parent.parent)
DATA = SITE / 'data'
CACHE = DATA / 'sentiment_cache'
HOLD = DATA / 'secteurs' / 'holdings'
PARIS = ZoneInfo('Europe/Paris')
UA = 'Mozilla/5.0 (compatible; APEX-sentiment/1.0)'
TODAY = datetime.now(PARIS)
PERIOD1 = int(datetime(2017, 6, 1, tzinfo=timezone.utc).timestamp())
PERIOD2 = int(time.time())
CACHE.mkdir(parents=True, exist_ok=True)

def lab(v):
    if v is None or (isinstance(v, float) and not math.isfinite(v)):
        return None
    return ('Peur extrême' if v < 25 else 'Peur' if v < 45 else 'Neutre'
            if v <= 55 else 'Avidité' if v <= 75 else 'Euphorie')


def prank(hist, v):
    h = [x for x in hist if x is not None and math.isfinite(x)]
    if not h or v is None or not math.isfinite(v):
        return None
    return 100.0 * (sum(1 for x in h if x < v) + 0.5 * sum(1 for x in h if x == v)) / len(h)


def sma(vals, n):
    out = [None] * len(vals)
    acc = 0.0
    ok = 0
    for i, x in enumerate(vals):
        if x is None:
            out[i] = None
            continue
        acc += x
        ok += 1
        if i >= n and vals[i - n] is not None:
            acc -= vals[i - n]
            ok -= 1
        if i >= n - 1 and ok == n:
            out[i] = acc / n
        else:
            # fenêtre incomplète si trous : moyenne des n dernières valeurs dispo
            window = [vals[j] for j in range(max(0, i - n + 1), i + 1) if vals[j] is not None]
            out[i] = (sum(window) / n) if len(window) == n else None
    return out


def rsi14(vals):
    """RSI de Wilder, 14 périodes."""
    n = 14
    out = [None] * len(vals)
    gain = loss = 0.0
    prev = None
    started = False
    count = 0
    avg_g = avg_l = None
    for i, x in enumerate(vals):
        if x is None:
            out[i] = out[i - 1] if i else None
            continue
        if prev is None:
            prev = x
            continue
        d = x - prev
        prev = x
        up, dn = max(d, 0.0), max(-d, 0.0)
        if not started:
            gain += up
            loss += dn
            count += 1
            if count == n:
                avg_g, avg_l = gain / n, loss / n
                out[i] = 100.0 if avg_l == 0 else 100.0 - 100.0 / (1.0 + avg_g / avg_l)
                started = True
        else:
            avg_g = (avg_g * (n - 1) + up) / n
            avg_l = (avg_l * (n - 1) + dn) / n
            out[i] = 100.0 if avg_l == 0 else 100.0 - 100.0 / (1.0 + avg_g / avg_l)
    return out


def fg_long(value, tranche=10, cap=50):
    if value is None:
        return None
    delta = 50.0 - float(value)
    n = min(cap // tranche, int(math.floor(abs(delta) / 10.0)))
    pts = n * tranche
    return pts if delta >= 0 else -pts


def fg_short(value, tranche=6, cap=30):
    if value is None:
        return None
    delta = float(value) - 50.0
    n = min(cap // tranche, int(math.floor(abs(delta) / 10.0)))
    pts = n * tranche
    return pts if delta >= 0 else -pts


# ---------------------------------------------------------------------------
# Téléchargements
# ---------------------------------------------------------------------------

def http_get(url, timeout=25, retries=3):
    last = None
    for k in range(retries):
        try:
            req = urllib.request.Request(url, headers={'User-Agent': UA})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read()
        except Exception as e:
            last = e
            time.sleep(0.6 * (k + 1))
    raise last


def yahoo_ticker(t):
    return t.replace('.', '-') if t.count('.') == 1 and not t.endswith(
        ('.DE', '.PA', '.AS', '.L', '.MI', '.SW', '.TO', '.T', '.AX', '.HK', '.F', '.SG')
    ) else t


def fetch_yahoo_chart(symbol, interval='1d', use_cache=True):
    safe = symbol.replace('^', '%5E').replace('=', '%3D').replace('/', '%2F')
    cache = CACHE / f"yahoo_{interval}_{symbol.replace('/', '_').replace('=', '_')}.json"
    if use_cache and cache.exists() and cache.stat().st_size > 200:
        # cache du jour OK
        age_h = (time.time() - cache.stat().st_mtime) / 3600
        if age_h < 12:
            raw = json.loads(cache.read_text())
            return parse_chart(raw, symbol)
    url = (f"https://query2.finance.yahoo.com/v8/finance/chart/{safe}"
           f"?period1={PERIOD1}&period2={PERIOD2}&interval={interval}&events=history")
    try:
        data = http_get(url)
        cache.write_bytes(data)
        return parse_chart(json.loads(data), symbol)
    except Exception as e:
        if cache.exists():
            try:
                return parse_chart(json.loads(cache.read_text()), symbol)
            except Exception:
                pass
        return {'ok': False, 'symbol': symbol, 'erreur': f'{type(e).__name__}: {e}'}


def parse_chart(raw, symbol):
    err = (raw.get('chart') or {}).get('error')
    res = (raw.get('chart') or {}).get('result')
    if err or not res:
        return {'ok': False, 'symbol': symbol, 'erreur': err or 'pas de résultat'}
    r0 = res[0]
    meta = r0.get('meta') or {}
    ts = r0.get('timestamp') or []
    q = (r0.get('indicators') or {}).get('quote') or [{}]
    closes = (q[0] or {}).get('close') or []
    rows = []
    for t, c in zip(ts, closes):
        if c is None or not math.isfinite(c):
            continue
        d = datetime.fromtimestamp(t, tz=timezone.utc).date().isoformat()
        rows.append((d, float(c)))
    # dédoublonnage (parfois deux points le même jour)
    by = {}
    for d, c in rows:
        by[d] = c
    series = sorted(by.items())
    return {
        'ok': True, 'symbol': symbol, 'n': len(series),
        'currency': meta.get('currency'),
        'name': meta.get('shortName') or meta.get('longName') or symbol,
        'exchange': meta.get('exchangeName'),
        'regular': meta.get('regularMarketPrice'),
        'regular_time': meta.get('regularMarketTime'),
        'series': series,
        'last_date': series[-1][0] if series else None,
        'last_close': series[-1][1] if series else None,
    }


def fetch_alternative_fng():
    cache = CACHE / 'alternative_fng.json'
    try:
        raw = http_get('https://api.alternative.me/fng/?limit=400')
        cache.write_bytes(raw)
        data = json.loads(raw)
    except Exception as e:
        if cache.exists():
            data = json.loads(cache.read_text())
        else:
            return {'ok': False, 'erreur': str(e)}
    rows = []
    for x in data.get('data') or []:
        d = datetime.fromtimestamp(int(x['timestamp']), tz=timezone.utc).date().isoformat()
        rows.append((d, float(x['value']), x.get('value_classification')))
    rows.sort()
    return {'ok': True, 'series': rows, 'last': rows[-1] if rows else None,
            'source': 'https://api.alternative.me/fng/?limit=400'}


def fetch_binance_funding():
    cache = CACHE / 'binance_funding_btcusdt.json'
    try:
        raw = http_get('https://fapi.binance.com/fapi/v1/fundingRate?symbol=BTCUSDT&limit=1000')
        cache.write_bytes(raw)
        data = json.loads(raw)
    except Exception as e:
        if cache.exists():
            data = json.loads(cache.read_text())
        else:
            return {'ok': False, 'erreur': str(e)}
    rows = []
    for x in data:
        ts = int(x['fundingTime']) / 1000
        d = datetime.fromtimestamp(ts, tz=timezone.utc).date().isoformat()
        rows.append((d, float(x['fundingRate']), ts))
    rows.sort(key=lambda x: x[2])
    return {'ok': True, 'series': rows, 'last': rows[-1] if rows else None,
            'source': 'https://fapi.binance.com/fapi/v1/fundingRate?symbol=BTCUSDT'}


# ---------------------------------------------------------------------------
# Composantes d'un sentiment style Fear & Greed
# ---------------------------------------------------------------------------

def last_idx(series):
    return len(series) - 1 if series else None


def component_etf(series, spy_series=None, lookback=252 * 5):
    """Sous-scores 0-100 à la dernière clôture, rangs sur ~5 ans (jours de bourse)."""
    if not series or len(series) < 80:
        return None
    dates = [d for d, _ in series]
    closes = [c for _, c in series]
    n = len(closes)
    i = n - 1
    r = rsi14(closes)
    s125 = sma(closes, 125)
    rets = [None] + [((closes[k] / closes[k - 1] - 1) if closes[k - 1] else None) for k in range(1, n)]
    gap = [(closes[k] / s125[k] - 1) if s125[k] else None for k in range(n)]
    # plus haut 52 semaines ≈ 252 séances
    dd52 = []
    for k in range(n):
        w = closes[max(0, k - 251):k + 1]
        dd52.append((closes[k] / max(w) - 1) if w else None)
    # vol 20 j annualisée
    vol = [None] * n
    for k in range(n):
        w = [rets[j] for j in range(max(1, k - 19), k + 1) if rets[j] is not None]
        if len(w) >= 15:
            vol[k] = statistics.pstdev(w) * math.sqrt(252) * 100
    ret21 = [(closes[k] / closes[k - 21] - 1) if k >= 21 and closes[k - 21] else None for k in range(n)]

    def win(arr):
        lo = max(0, i - lookback + 1)
        return [arr[k] for k in range(lo, i + 1) if arr[k] is not None]

    comps = {
        'momentum_sma125': {
            'nom': 'Momentum vs SMA 125 j (rang 5 ans)',
            'value': prank(win(gap), gap[i]),
            'raw': None if gap[i] is None else round(gap[i] * 100, 2),
            'raw_unit': '%',
        },
        'rsi14': {
            'nom': 'RSI 14 journalier (valeur brute 0-100)',
            'value': r[i],
            'raw': None if r[i] is None else round(r[i], 1),
            'raw_unit': 'RSI',
        },
        'prix_52s': {
            'nom': 'Distance au plus haut 52 semaines (rang 5 ans)',
            'value': prank(win(dd52), dd52[i]),
            'raw': None if dd52[i] is None else round(dd52[i] * 100, 2),
            'raw_unit': '%',
        },
        'vol20_inv': {
            'nom': 'Volatilité réalisée 20 j, inversée (rang 5 ans)',
            'value': None if vol[i] is None else (100 - prank(win(vol), vol[i]) if prank(win(vol), vol[i]) is not None else None),
            'raw': None if vol[i] is None else round(vol[i], 1),
            'raw_unit': '% ann.',
        },
        'momentum_21j': {
            'nom': 'Performance 21 j (rang 5 ans)',
            'value': prank(win(ret21), ret21[i]),
            'raw': None if ret21[i] is None else round(ret21[i] * 100, 2),
            'raw_unit': '%',
        },
    }
    vals = [c['value'] for c in comps.values() if c['value'] is not None]
    score = sum(vals) / len(vals) if vals else None
    return {
        'score': None if score is None else round(score, 1),
        'label': lab(score),
        'date': dates[i],
        'close': round(closes[i], 4),
        'n_composantes': len(vals),
        'composantes': {k: {**v, 'value': None if v['value'] is None else round(v['value'], 1)}
                        for k, v in comps.items()},
    }


def breadth_from_members(member_series, asof=None):
    """% de titres au-dessus de leur SMA50 et SMA200, et force 52 semaines."""
    if not member_series:
        return None
    above50 = above200 = near_hi = near_lo = used50 = used200 = used52 = 0
    details_missing = 0
    for rec in member_series:
        if not rec or not rec.get('ok') or not rec.get('series'):
            details_missing += 1
            continue
        s = rec['series']
        if asof:
            s = [(d, c) for d, c in s if d <= asof]
        if len(s) < 60:
            details_missing += 1
            continue
        closes = [c for _, c in s]
        last = closes[-1]
        s50 = sma(closes, 50)
        s200 = sma(closes, 200)
        if s50[-1] is not None:
            used50 += 1
            if last > s50[-1]:
                above50 += 1
        if s200[-1] is not None:
            used200 += 1
            if last > s200[-1]:
                above200 += 1
        if len(closes) >= 60:
            mx = max(closes[-252:]) if len(closes) >= 252 else max(closes)
            mn = min(closes[-252:]) if len(closes) >= 252 else min(closes)
            used52 += 1
            if mx and (last / mx) >= 0.95:
                near_hi += 1
            if mx and mn and (last - mn) / (mx - mn) <= 0.05 if mx != mn else False:
                near_lo += 1
            elif mn and last <= mn * 1.05:
                near_lo += 1
    if used50 < 8:
        return None
    p50 = 100.0 * above50 / used50
    p200 = 100.0 * above200 / used200 if used200 else None
    # force : (% proches des plus hauts − % proches des plus bas + 100) / 2
    force = None
    if used52:
        force = (100.0 * near_hi / used52 - 100.0 * near_lo / used52 + 100.0) / 2.0
    return {
        'pct_above_ma50': round(p50, 1),
        'n_ma50': used50,
        'n_above_ma50': above50,
        'pct_above_ma200': None if p200 is None else round(p200, 1),
        'n_ma200': used200,
        'n_above_ma200': above200,
        'force_52s': None if force is None else round(force, 1),
        'pct_near_high': round(100.0 * near_hi / used52, 1) if used52 else None,
        'pct_near_low': round(100.0 * near_lo / used52, 1) if used52 else None,
        'n_52s': used52,
        'manquants': details_missing,
        'date': asof,
    }


def combine_score(etf_rec, breadth=None, extra=None):
    """Moyenne équipondérée des composantes ETF + ampleur (si dispo) + extras."""
    if not etf_rec:
        return None
    parts = []
    for k, c in etf_rec['composantes'].items():
        if c['value'] is not None:
            parts.append((c['nom'], c['value'], c.get('raw'), c.get('raw_unit'), 1.0, k))
    if breadth:
        if breadth.get('pct_above_ma50') is not None:
            parts.append(('Ampleur : % de titres > SMA 50 j', breadth['pct_above_ma50'],
                          breadth['pct_above_ma50'], '%', 1.0, 'breadth_ma50'))
        if breadth.get('pct_above_ma200') is not None:
            parts.append(('Ampleur : % de titres > SMA 200 j', breadth['pct_above_ma200'],
                          breadth['pct_above_ma200'], '%', 1.0, 'breadth_ma200'))
        if breadth.get('force_52s') is not None:
            parts.append(('Force interne (proche 52 s. hauts vs bas)', breadth['force_52s'],
                          breadth['force_52s'], 'indice', 1.0, 'force_52s'))
    if extra:
        for e in extra:
            if e.get('value') is not None:
                parts.append((e['nom'], e['value'], e.get('raw'), e.get('raw_unit'),
                              e.get('weight', 1.0), e.get('id', e['nom'])))
    if not parts:
        return None
    tw = sum(p[4] for p in parts)
    score = sum(p[1] * p[4] for p in parts) / tw
    return {
        'score': round(score, 1),
        'label': lab(score),
        'date': etf_rec['date'],
        'close': etf_rec.get('close'),
        'n_composantes': len(parts),
        'composantes': [
            {'id': p[5], 'nom': p[0], 'value': round(p[1], 1), 'raw': p[2],
             'raw_unit': p[3], 'poids': p[4]}
            for p in parts
        ],
    }


# ---------------------------------------------------------------------------
# Holdings SPDR
# ---------------------------------------------------------------------------

CASH_TOKENS = ('CASH', 'USD', 'U.S. DOLLAR', 'US DOLLAR', 'CASH COLLATERAL')


def load_holdings(sym):
    path = HOLD / f'{sym}.xlsx'
    if not path.exists():
        return [], None
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    ws = wb.active
    rows = list(ws.iter_rows(values_only=True))
    wb.close()
    asof = None
    if len(rows) > 2 and rows[2] and rows[2][1]:
        asof = str(rows[2][1])
    hi = next((i for i, r in enumerate(rows) if r and r[0] == 'Name'), None)
    out = []
    if hi is None:
        return out, asof
    for r in rows[hi + 1:]:
        if not r or not r[1]:
            continue
        name = str(r[0] or '')
        tick = str(r[1]).strip()
        if tick in ('USD', 'CASH', '-') or any(t in name.upper() for t in CASH_TOKENS):
            continue
        y = yahoo_ticker(tick)
        w = r[4]
        out.append({'ticker': tick, 'yahoo': y, 'name': name, 'weight': float(w) if w is not None else None})
    return out, asof


# ---------------------------------------------------------------------------
# Univers
# ---------------------------------------------------------------------------

US_SECTORS = [
    ('XLK', 'Technologie', 'Information Technology', 'Technology'),
    ('XLF', 'Finance', 'Financials', 'Financial Services'),
    ('XLE', 'Énergie', 'Energy', 'Energy'),
    ('XLV', 'Santé', 'Health Care', 'Healthcare'),
    ('XLI', 'Industrie', 'Industrials', 'Industrials'),
    ('XLC', 'Communication', 'Communication Services', 'Communication Services'),
    ('XLY', 'Consommation discrétionnaire', 'Consumer Discretionary', 'Consumer Cyclical'),
    ('XLP', 'Consommation de base', 'Consumer Staples', 'Consumer Defensive'),
    ('XLU', 'Services aux collectivités', 'Utilities', 'Utilities'),
    ('XLRE', 'Immobilier', 'Real Estate', 'Real Estate'),
    ('XLB', 'Matériaux', 'Materials', 'Basic Materials'),
]

EU_SECTORS = [
    ('XS8R.DE', 'Technologie', 'Information Technology', 'Xtrackers MSCI Europe IT'),
    ('DXSE.DE', 'Santé', 'Health Care', 'Xtrackers MSCI Europe Health Care'),
    ('XS7R.DE', 'Finance', 'Financials', 'Xtrackers MSCI Europe Financials'),
    ('DXSG.DE', 'Communication', 'Communication Services', 'Xtrackers MSCI Europe Communication'),
    ('SPYR.DE', 'Consommation discrétionnaire', 'Consumer Discretionary', 'SPDR MSCI Europe Cons. Disc.'),
    ('DXSK.DE', 'Consommation de base', 'Consumer Staples', 'Xtrackers MSCI Europe Staples'),
    ('DXSL.DE', 'Industrie', 'Industrials', 'Xtrackers MSCI Europe Industrials'),
    ('DXSC.DE', 'Matériaux', 'Materials', 'Xtrackers MSCI Europe Materials'),
    ('XS6R.DE', 'Services aux collectivités', 'Utilities', 'Xtrackers MSCI Europe Utilities'),
    ('EXH1.DE', 'Énergie', 'Energy', 'iShares STOXX Europe 600 Oil & Gas (ICB, pas GICS)'),
    ('EXI5.DE', 'Immobilier', 'Real Estate', 'iShares STOXX Europe 600 Real Estate (ICB)'),
]

# Autres séries à télécharger
EXTRA_TICKERS = {
    'SPY': 'S&P 500 ETF',
    '^GSPC': 'S&P 500',
    '^VIX': 'VIX',
    '^VIX3M': 'VIX 3 mois',
    '^MOVE': 'MOVE (vol. obligataire)',
    'TLT': 'US Treasuries 20+ ans',
    'IEF': 'US Treasuries 7-10 ans',
    'SHY': 'US Treasuries 1-3 ans',
    'AGG': 'US Aggregate Bond',
    'LQD': 'US IG Corporate',
    'HYG': 'US High Yield',
    'TIP': 'US TIPS',
    'EMB': 'Emerging USD debt',
    'VNQ': 'US REIT (Vanguard)',
    'IQQ7.DE': 'iShares US Property Yield UCITS',
    'GLD': 'Or (ETF)',
    'SLV': 'Argent (ETF)',
    'PPLT': 'Platine (ETF)',
    'PALL': 'Palladium (ETF)',
    'GC=F': 'Or (contrat COMEX)',
    'SI=F': 'Argent (contrat)',
    'PL=F': 'Platine (contrat)',
    'PA=F': 'Palladium (contrat)',
    'DBC': 'Matières premières (panier)',
    'GSG': 'S&P GSCI',
    'USO': 'Pétrole WTI (ETF)',
    'UNG': 'Gaz naturel (ETF)',
    'CL=F': 'Pétrole WTI (contrat)',
    'BZ=F': 'Pétrole Brent (contrat)',
    'NG=F': 'Gaz naturel (contrat)',
    'HG=F': 'Cuivre (contrat)',
    'DX-Y.NYB': 'Dollar Index (DXY)',
    'EURUSD=X': 'EUR/USD',
    'USDJPY=X': 'USD/JPY',
    'GBPUSD=X': 'GBP/USD',
    'AUDJPY=X': 'AUD/JPY (proxy risque)',
    'BTC-USD': 'Bitcoin',
    'ETH-USD': 'Ethereum',
    'EXSA.DE': 'STOXX Europe 600 UCITS',
    '^STOXX': 'STOXX Europe 600',
    '^FCHI': 'CAC 40',
    '^GDAXI': 'DAX',
    '^GSPTSE': 'S&P/TSX',
    '^SSMI': 'SMI',
    'UUP': 'Dollar bullish ETF',
}


def collect_tickers():
    ticks = set()
    for s, *_ in US_SECTORS:
        ticks.add(s)
    for s, *_ in EU_SECTORS:
        ticks.add(s)
    ticks.update(EXTRA_TICKERS)
    holdings = {}
    all_members = set()
    for s, *_ in US_SECTORS:
        hs, asof = load_holdings(s)
        holdings[s] = {'asof': asof, 'rows': hs}
        for h in hs:
            all_members.add(h['yahoo'])
    return sorted(ticks), holdings, sorted(all_members)


def download_all(tickers, max_workers=8):
    results = {}
    n = len(tickers)
    print(f'Téléchargement Yahoo 1d : {n} symboles (workers={max_workers})')
    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        futs = {ex.submit(fetch_yahoo_chart, t): t for t in tickers}
        done = 0
        for fut in as_completed(futs):
            t = futs[fut]
            try:
                rec = fut.result()
            except Exception as e:
                rec = {'ok': False, 'symbol': t, 'erreur': str(e)}
            results[t] = rec
            done += 1
            if done % 50 == 0 or done == n:
                ok = sum(1 for r in results.values() if r.get('ok'))
                print(f'  {done}/{n}  ok={ok}')
    return results




# ---------------------------------------------------------------------------
# Classes d'actifs : actif de référence (formule prix)
# ---------------------------------------------------------------------------

CLASSES_PRIX = [
    # clé, symbole Yahoo, libellé court (affiché dans le détail des notes)
    ('metal:or', 'GC=F', 'Or (GC)'),
    ('metal:argent', 'SI=F', 'Argent (SI)'),
    ('metal:platine', 'PL=F', 'Platine (PL)'),
    ('metal:palladium', 'PA=F', 'Palladium (PA)'),
    ('energie:petrole', 'CL=F', 'Pétrole WTI (CL)'),
    ('energie:brent', 'BZ=F', 'Pétrole Brent (BZ)'),
    ('energie:gaz', 'NG=F', 'Gaz naturel (NG)'),
    ('oblig:tcourt', 'SHY', 'Treasuries courts (SHY)'),
    ('oblig:tlong', 'TLT', 'Treasuries longs (TLT)'),
    ('oblig:t710', 'IEF', 'Treasuries 7-10 ans (IEF)'),
    ('oblig:agg', 'AGG', 'Oblig. US agrégées (AGG)'),
    ('oblig:usig', 'LQD', 'Crédit IG USD (LQD)'),
    ('oblig:hy', 'HYG', 'High yield (HYG)'),
    ('oblig:infl', 'TIP', 'Indexées inflation (TIP)'),
    ('oblig:em', 'EMB', 'Dette émergente (EMB)'),
    ('oblig:eurgov', 'EUNH.DE', 'Souverains € (EUNH)'),
    ('oblig:eurig', 'EUN5.DE', 'Crédit IG € (EUN5)'),
    ('oblig:de', 'EXX6.DE', 'Bund (EXX6)'),
    ('immo:reit_us', 'VNQ', 'REIT US (VNQ)'),
    ('immo:reit_eu', 'EXI5.DE', 'Immobilier Europe (EXI5)'),
    ('fx:dxy', 'DX-Y.NYB', 'Dollar Index (DXY)'),
    ('fx:audjpy', 'AUDJPY=X', 'AUD/JPY'),
    ('pays:FR', '^FCHI', 'France (CAC 40)'),
    ('pays:DE', '^GDAXI', 'Allemagne (DAX)'),
    ('pays:CA', '^GSPTSE', 'Canada (TSX)'),
    ('pays:CH', '^SSMI', 'Suisse (SMI)'),
    ('pays:US', '^GSPC', 'États-Unis (S&P 500)'),
    ('pays:EU', '^STOXX', 'Europe (STOXX 600)'),
    ('pays:JP', '^N225', 'Japon (Nikkei)'),
    ('pays:KR', '^KS11', 'Corée (KOSPI)'),
]


def _rec(value, nom, court, date=None, source=None, official=False, extra=None):
    v = None if value is None else round(float(value), 1)
    r = {'value': v, 'label': lab(v), 'nom': nom, 'court': court, 'date': date,
         'points_long': fg_long(v), 'points_short': fg_short(v), 'official': official, 'source': source}
    if extra:
        r.update(extra)
    return r


def main():
    print('Sentiment par secteur / classe', TODAY.strftime('%Y-%m-%d %H:%M %Z'))
    etf_ticks, holdings, members = collect_tickers()
    etf_ticks = sorted(set(etf_ticks) | {s for _k, s, _c in CLASSES_PRIX})
    etf_data = download_all(etf_ticks, max_workers=6)
    member_data = download_all(members, max_workers=8)

    out = {'generated': TODAY.strftime('%Y-%m-%d %H:%M') + ' Europe/Paris', 'secteurs_us': {}, 'secteurs_eu': {}, 'classes': {}}

    # CNN global (repli)
    cnn = {}
    p = DATA / 'apex_achat_v2_cnn_fng.json'
    if p.exists():
        raw = json.loads(p.read_text())
        fg = raw.get('fear_and_greed') or {}
        if fg.get('score') is not None:
            ts = fg.get('timestamp')
            d = None
            try:
                d = datetime.fromisoformat(str(ts).replace('Z', '+00:00')).astimezone(PARIS).strftime('%Y-%m-%d')
            except Exception:
                pass
            cnn = _rec(fg['score'], 'CNN Fear & Greed (marché US, global)', 'CNN global', d,
                       'https://edition.cnn.com/markets/fear-and-greed', True)
    out['cnn'] = cnn

    for sym, fr, gics, _y in US_SECTORS:
        rec = etf_data.get(sym) or {}
        if not rec.get('ok'):
            continue
        es = component_etf(rec['series'])
        br = breadth_from_members([member_data.get(h['yahoo']) for h in holdings[sym]['rows']], asof=es['date'] if es else None)
        cb = combine_score(es, br) if es else None
        if not cb:
            continue
        out['secteurs_us'][sym] = _rec(cb['score'], f'{fr} US', f'{fr} ({sym})', cb['date'], 'Yahoo Finance + holdings SPDR',
                                      extra={'gics': gics, 'etf': sym, 'fr': fr,
                                             'ampleur': {k: (br or {}).get(k) for k in ('pct_above_ma50', 'pct_above_ma200', 'force_52s', 'n_ma50')},
                                             'composantes': [{'nom': c['nom'], 'value': c['value']} for c in cb['composantes']]})
    for sym, fr, gics, etf_name in EU_SECTORS:
        rec = etf_data.get(sym) or {}
        if not rec.get('ok'):
            continue
        es = component_etf(rec['series'])
        cb = combine_score(es) if es else None
        if not cb:
            continue
        court = sym.split('.')[0]
        out['secteurs_eu'][court] = _rec(cb['score'], f'{fr} Europe', f'{fr} Europe ({court})', cb['date'], 'Yahoo Finance (' + etf_name + ')',
                                        extra={'gics': gics, 'etf': court, 'yahoo': sym, 'fr': fr,
                                               'composantes': [{'nom': c['nom'], 'value': c['value']} for c in cb['composantes']]})

    C = out['classes']
    for key, sym, court in CLASSES_PRIX:
        rec = etf_data.get(sym) or {}
        es = component_etf(rec['series']) if rec.get('ok') else None
        if es and es.get('score') is not None:
            C[key] = _rec(es['score'], court, court, es['date'], f'Yahoo Finance ({sym})', extra={'yahoo': sym})

    # Paniers
    def panier(key, nom, court, parts):
        ok = [(C[k]['value'], w) for k, w in parts if C.get(k) and C[k].get('value') is not None]
        if ok:
            v = sum(a * w for a, w in ok) / sum(w for _a, w in ok)
            C[key] = _rec(v, nom, court, TODAY.strftime('%Y-%m-%d'), 'moyenne pondérée : ' + ', '.join(f'{k} {w}' for k, w in parts))
    # métaux : or 40 / argent 20 / platine 10 / palladium 10 (+ CFTC 20 repris de metaux.json)
    cftc = None
    try:
        for c in (json.loads((DATA / 'metaux.json').read_text()).get('ind') or {}).get('components') or []:
            if 'CFTC' in (c.get('name') or ''):
                cftc = c.get('value')
    except Exception:
        pass
    if cftc is not None:
        C['metal:cftc'] = _rec(cftc, 'Positionnement CFTC or + argent', 'CFTC', None, 'metaux.json')
    panier('metaux', 'Métaux précieux (panier)', 'Métaux précieux', [('metal:or', .4), ('metal:argent', .2), ('metal:platine', .1), ('metal:palladium', .1), ('metal:cftc', .2)])
    if C.get('fx:dxy') and C.get('fx:audjpy'):
        v = ((100 - C['fx:dxy']['value']) + C['fx:audjpy']['value']) / 2
        C['devises'] = _rec(v, 'Devises : appétit pour le risque', 'Devises', C['fx:dxy']['date'], '(100 − sentiment DXY + sentiment AUD/JPY) / 2')

    # Crypto : alternative.me (officiel)
    alt = fetch_alternative_fng()
    if alt.get('ok') and alt.get('last'):
        d, v, _c = alt['last']
        C['crypto'] = _rec(v, 'Crypto Fear & Greed (alternative.me)', 'Crypto (alternative.me)', d, alt.get('source'), True)

    # Immobilier France et liquidités : indices APEX déjà calculés
    try:
        ind = json.loads((DATA / 'indicateur.json').read_text())
        for k, key, court in (('immobilier', 'immo:fr', 'Immobilier France'), ('liquidites', 'liquidites', 'Liquidités')):
            g = ind.get(k) or {}
            if g.get('value') is not None:
                C[key] = _rec(g['value'], g.get('title') or court, court, g.get('date'), 'data/indicateur.json')
    except Exception as e:
        print('indicateur.json', e)

    out['methode'] = (
        "Indice composite APEX, non officiel, de 0 (peur extrême) à 100 (euphorie). Moyenne simple de sous-scores 0-100 : "
        "écart à la SMA 125 j, RSI 14 journalier, distance au plus haut 52 semaines, volatilité 20 j inversée, performance 21 j "
        "(rangs sur 5 ans, clôtures journalières Yahoo) ; pour les 11 secteurs US, + % de titres au-dessus de leur SMA 50 j et 200 j "
        "et force interne (holdings SPDR). Crypto : alternative.me. Immobilier France et liquidités : indices APEX de la colonne Indicateur. "
        "Repli : CNN Fear & Greed global quand un actif n’a pas de secteur ou de classe.")
    dest = DATA / 'sentiment_secteurs.json'
    dest.write_text(json.dumps(out, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    for k in ('secteurs_us', 'secteurs_eu', 'classes'):
        print(k, {a: b['value'] for a, b in out[k].items()})
    print('CNN', cnn.get('value'), '->', dest)


if __name__ == '__main__':
    main()
