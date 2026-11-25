"""Chargement des clôtures hebdomadaires confirmées pour le critère MM40."""
from __future__ import annotations

import os
import sys
import urllib.parse
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from . import paths

ROOT = paths.root()
DASH = Path('/workspace/invest/patrimoine-dashboard/data')
PARIS = ZoneInfo('Europe/Paris')

WEEKLY_PATS = [
    str(ROOT / 'data/fibo_max/{enc}.json'),
    str(ROOT / 'data/short_cache/yahoo_1wk_{enc}.json'),
    str(ROOT / 'data/liquidites_etf/yahoo_1wk_{enc}.json'),
    str(ROOT / 'data/metaux/y_{enc}.json'),
    str(ROOT / 'data/metaux/y_{sym}.json'),
    str(ROOT / 'data/secteurs/yahoo_1wk_{enc}.json'),
    str(ROOT / 'data/pays/yahoo_1wk_{enc}.json'),
    str(ROOT / 'data/pays/wk/{sym}.json'),
    str(ROOT / 'data/actions/yahoo_1wk_{enc}.json'),
    str(ROOT / 'data/energie/yahoo_1wk_{enc}.json'),
    str(DASH / 'secteurs/yahoo_1wk_{enc}.json'),
    str(DASH / 'pays/yahoo_1wk_{enc}.json'),
    str(DASH / 'actions/yahoo_1wk_{enc}.json'),
    str(DASH / 'energie/yahoo_1wk_{enc}.json'),
    str(DASH / 'liquidites/yahoo_1wk_{enc}.json'),
    str(DASH / 'crypto/yahoo_1wk_{enc}.json'),
]


def _quote(s):
    return urllib.parse.quote(s, safe='')


def yahoo_cands(tv=None, yahoo=None, ticker=None):
    cands = []
    for x in (yahoo, ticker):
        if x and x not in cands:
            cands.append(x)
    if tv and ':' in tv:
        ex, t = tv.split(':', 1)
        mp = {
            'XETR': [t + '.DE'],
            'NYSE': [t],
            'NASDAQ': [t],
            'AMEX': [t],
            'LSE': [t + '.L'],
            'EURONEXT': [t + '.PA', t + '.AS', t + '.L', t],
            'SIX': [t + '.SW'],
            'TSE': [t + '.T', t],
            'TSX': [t + '.TO', t],
            'HKEX': [t + '.HK', t],
            'KRX': [t + '.KS', t],
            'SWX': [t + '.SW'],
        }
        for x in mp.get(ex, [t]) + [t]:
            if x and x not in cands:
                cands.append(x)
    elif tv and tv not in cands:
        cands.append(tv)
    return cands


def find_weekly_path(tv=None, yahoo=None, ticker=None, path=None):
    if path and os.path.exists(path):
        return path, None
    for s in yahoo_cands(tv, yahoo, ticker):
        enc = _quote(s)
        for pat in WEEKLY_PATS:
            p = pat.format(sym=s, enc=enc)
            if os.path.exists(p):
                return p, s
    return None, None


def load_closed(path):
    src = str(paths.src_dir())
    if src not in sys.path:
        sys.path.insert(0, src)
    import yahoo_week as YW  # noqa: WPS433
    bars, meta = YW.parse_yahoo_weekly(path, now=datetime.now(PARIS))
    closed = [b for b in bars if b.get('closed') and b.get('close') and b['close'] > 0]
    return closed, meta


def weekly_closes(tv=None, yahoo=None, ticker=None, path=None, bars=None):
    """Liste des clôtures hebdo confirmées, ou []."""
    if bars:
        return [float(b['close']) for b in bars if b.get('close')]
    p, _ = find_weekly_path(tv, yahoo, ticker, path)
    if not p:
        return []
    closed, _ = load_closed(p)
    return [float(b['close']) for b in closed]
