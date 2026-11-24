"""Notes APEX −50..250 des ETF/ETC locaux sous chaque devise (t491u, critère 3 ans annualisés t492u).

Technique 110 (RSI 30, MACD 30, Fibo 30, CCI/Stoch 20, sans Elliott) +
Fear & Greed ±50 (même grille que les actions, source CNN) +
note de la devise face à l'euro 30 (paliers de 10 sur la note /100) +
Fondamental 30 (n.c. si absent, pas de redistribution) +
HYPE 30 (non comptée jusqu'au 25/11).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / 'src') not in sys.path:
    sys.path.insert(0, str(ROOT / 'src'))

import ind_core as K
import charte as CH
import fibo as FB
from .score import metaux_band, fmt10, round_half, fg_points, load_cnn_fg

DATA = ROOT / 'data' / 'liquidites_etf'


def devise_points(note_100):
    """Note devise /100 → 0..30, paliers de 10 : 0–9 → 0, 10–19 → 3, … 100 → 30."""
    if note_100 is None:
        return None
    v = max(0, min(100, float(note_100)))
    return int(min(30, 3 * (int(v) // 10)))


def hype_points_30(attention):
    """Grille HYPE 30 (à appliquer le 25/11). None → non comptée."""
    if attention is None:
        return None
    v = max(0, min(100, int(attention)))
    t = v // 10
    return max(0, 30 - 3 * t)


def _yahoo_weeks(path, close_after='friday'):
    import datetime as D
    from zoneinfo import ZoneInfo
    d = json.loads(Path(path).read_text())['chart']['result'][0]
    ts, q, meta = d['timestamp'], d['indicators']['quote'][0], d['meta']
    tz = ZoneInfo(meta.get('exchangeTimezoneName') or 'UTC')
    TODAY = D.datetime.now(ZoneInfo('Europe/Paris')).date()
    opens_raw = q.get('open') or [None] * len(ts)
    wk, opens, live = {}, {}, None
    for t, o, v in zip(ts, opens_raw, q['close']):
        if v is None or v <= 0:
            continue
        loc = D.datetime.fromtimestamp(t, tz)
        ld = loc.date()
        if loc.hour == 0 and loc.minute == 0:
            fri = ld + D.timedelta(days=(4 - ld.weekday()) % 7)
            wk[fri] = v
            opens[fri.isoformat()] = o if (o and o > 0) else None
        else:
            mon = ld - D.timedelta(days=ld.weekday())
            fri = mon + D.timedelta(days=4)
            live = (fri, v, o if (o and o > 0) else None)
    end = (lambda fri: fri + D.timedelta(days=2)) if close_after == 'sunday' else (lambda fri: fri)
    if live is not None:
        fri, v, o = live
        if TODAY <= end(fri):
            wk[fri] = v
            opens[fri.isoformat()] = o
    out = [(f.isoformat(), wk[f], TODAY > end(f)) for f in sorted(wk)]
    return out, opens


def _ligne(parts, n):
    bits = []
    for lab, pts in parts:
        if pts is None or pts == '—':
            bits.append('%s —' % lab)
            continue
        if isinstance(pts, (int, float)) and pts > 0:
            bits.append('%s +%s' % (lab, int(pts) if pts == int(pts) else pts))
        elif isinstance(pts, (int, float)) and pts < 0:
            bits.append('%s %s' % (lab, int(pts) if pts == int(pts) else pts))
        else:
            bits.append('%s 0' % lab)
    return '%s  →  %s / 250 · Hype non comptée (dès le 25/11)' % (' · '.join(bits), fmt10(n))


def score_etf(obj, note_devise_100, fg_value=None):
    from build_apex_achat_v2_pilot import rsi_points, macd_points, fibo_points, cci_points
    wk_path = DATA / obj['yahoo_weekly']
    if not wk_path.exists():
        return {'note': None, 'display': '–', 'erreur': 'série hebdomadaire introuvable', 'scale': 250}
    w, opens = _yahoo_weeks(wk_path, close_after='friday')
    closed = [(d, c) for d, c, ok in w if ok]
    if len(closed) < 52:
        return {'note': None, 'display': '–', 'erreur': 'historique hebdomadaire trop court (%s semaines)' % len(closed), 'scale': 250}
    ds = [d for d, _ in closed]
    c = [x for _, x in closed]
    o = [opens.get(d) if opens.get(d) and opens.get(d) > 0 else None for d in ds]
    r = K.rsi(c)
    rsi_val = r[-1]
    div = CH.divergence(c, ds, r)
    rsi_pts, rsi_det = rsi_points(rsi_val, div)
    m, sg, h = K.macd_series(c)
    macd_pts, macd_det = macd_points(m[-1], h)
    fib_calc = FB.analyse(o, c, ds, adjust_splits=False, sym=obj.get('tv') or obj.get('yahoo'), combine=False)
    r_hist = fib_calc.get('r') if fib_calc.get('ok') else None
    fibo_pts, fibo_det = fibo_points(r_hist)
    _k, d_s, _raw = K.cci_stochastic_kd(c)
    cci_val = d_s[-1] if d_s else None
    cci_pts, cci_det = cci_points(cci_val)

    if fg_value is None:
        fg = load_cnn_fg() or {}
        fg_value = fg.get('value') if fg.get('ok') else None
    fg_pts = fg_points(fg_value) if fg_value is not None else 0
    if fg_pts is None:
        fg_pts = 0

    dev_pts = devise_points(note_devise_100)
    fond_pts = None  # n.c., pas de redistribution
    hype_pts = None

    brut = int(rsi_pts + macd_pts + fibo_pts + cci_pts + (dev_pts or 0) + (fg_pts or 0))
    n = max(-50, min(250, int(round_half(brut))))
    band = metaux_band(n)
    parts = [
        ('RSI', rsi_pts), ('MACD', macd_pts), ('Fibo', fibo_pts), ('CCI', cci_pts),
        ('Devise', dev_pts if dev_pts is not None else '—'),
        ('Fond.', '—'),
        ('F&G', fg_pts if fg_value is not None else '—'),
    ]
    texte = _ligne(parts, n)
    return {
        'note': n, 'display': fmt10(n), 'hex': band['hex'], 'flag': band['flag'],
        'band': band['id'], 'pos': n, 'cap': 'fond_nc+hype_attente_25_11',
        'brut': brut, 'scale': 250, 'total': n, 'total_min': -50, 'total_max': 250,
        'v2': True, 'ligne': texte, 'renormalise': False,
        'technique': int(rsi_pts + macd_pts + fibo_pts + cci_pts),
        'devise_points': dev_pts, 'devise_note_100': note_devise_100,
        'fg_points': fg_pts if fg_value is not None else None, 'fg_value': fg_value,
        'fg_source': 'CNN',
        'decomp': {
            'texte': texte,
            'points': {
                'rsi': rsi_pts, 'macd': macd_pts, 'fibonacci': fibo_pts, 'cci': cci_pts,
                'devise': dev_pts, 'fondamental': None, 'hype': None,
                'fear_greed': fg_pts if fg_value is not None else None, 'total': n,
            },
            'rsi': {'valeur': None if rsi_val is None else round(float(rsi_val), 1), 'points': rsi_pts, 'conditions': rsi_det},
            'macd': {'points': macd_pts, 'conditions': macd_det},
            'fibonacci': {**fibo_det, 'points': fibo_pts},
            'cci': {**cci_det, 'points': cci_pts},
            'devise': {'note_100': note_devise_100, 'points': dev_pts, 'grille': '0–9→0, 10→3, … 100→30'},
            'fondamental': {'points': None, 'etat': 'n.c.'},
            'hype': {'points': None, 'etat': 'en_attente_25_11', 'grille': '0–9→+30, 10→+27, 50→+15, 100→0'},
            'fear_greed': {'valeur': fg_value, 'points': fg_pts if fg_value is not None else None, 'source': 'CNN'},
            'echelle': 250,
        },
    }
