"""Note crypto APEX en points entiers additifs, échelle −50 à 250 (t489u).

Barème : Liquidité 45 (CoinAnk, 1 an 70 % / 1 mois 30 %) + Technique 110
(RSI 30, MACD 30, Fibo 30, CCI/Stoch 20, sans Elliott ni Structure)
+ Fear & Greed ±50 (même grille que les actions, source alternative.me déjà
sur les fiches). HYPE 45 : Attention Long Swing, à contre-courant.
MM40 hebdo 0 à +125, à contre-courant (0 au-dessus, linéaire jusqu’à −40 %,
puis plafond ; total borné à 250). Sans carte de liquidité : 0 point, pas de redistribution.
"""
from __future__ import annotations

import math
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
from .score import metaux_band, fmt10, round_half, fg_points, divergence_haussiere, mm40_hebdo_points, mm40_hebdo_texte


def crypto_data_dir() -> Path:
    cands = [
        ROOT / 'data' / 'crypto',
        ROOT.parent / 'patrimoine-dashboard' / 'data' / 'crypto',
    ]
    for p in cands:
        if (p / 'binance_BTCUSDT_1w.json').exists():
            return p
    raise FileNotFoundError('données hebdomadaires crypto introuvables')


# Grille HYPE 45 (à appliquer le 25/11, pas avant) :
# 0–9 → 45, puis −4 par tranche de 10 jusqu'à 50 → 25, puis −5 jusqu'à 100 → 0.
HYPE_GRILLE = (
    (0, 45), (10, 41), (20, 37), (30, 33), (40, 29),
    (50, 25), (60, 20), (70, 15), (80, 10), (90, 5), (100, 0),
)


def hype_points_45(attention):
    """Points HYPE crypto (0..45). attention 0–100. None → None (non comptée)."""
    if attention is None:
        return None
    v = max(0, min(100, int(attention)))
    t = v // 10
    if t <= 4:
        return 45 - 4 * t
    return max(0, 25 - 5 * (t - 5))


def liquidite_points(liq):
    """Convertit le score CoinAnk 0–100 (blend 70/30 déjà calculé) en 0..45 entiers.

    Si un seul horizon est retenu, le blend existant le renormalise à 100 %
    (même comportement qu'aujourd'hui), puis on le ramène sur 45.
    Plafonds affichés : 1 an 32, 1 mois 13 (70 % × 45 = 31,5 → 32, 30 % × 45 = 13,5 → 13).
    """
    if not liq or liq.get('score') is None:
        return 0, {
            'present': False, 'points': None,
            'raison': (liq or {}).get('comment') or 'sans_carte',
        }
    s = float(liq['score'])
    pts = max(0, min(45, int(round_half(s * 45 / 100.0))))
    used = list(liq.get('used') or [])
    horizons = liq.get('horizons') or {}
    det = {
        'present': True,
        'points': pts,
        'score_100': s,
        'used': used,
        'max_1y': 32,
        'max_1m': 13,
        'w_1y': 0.70,
        'w_1m': 0.30,
    }
    if '1y' in used and horizons.get('1y') and horizons['1y'].get('score') is not None:
        det['score_1y'] = horizons['1y']['score']
    if '1m' in used and horizons.get('1m') and horizons['1m'].get('score') is not None:
        det['score_1m'] = horizons['1m']['score']
    return pts, det


def _ligne(parts, n):
    bits = []
    for lab, pts in parts:
        if pts is None:
            bits.append('%s —' % lab)
            continue
        if pts == '—':
            bits.append('%s —' % lab)
            continue
        if isinstance(pts, str) and pts.startswith('MM40'):
            bits.append(pts)
            continue
        if isinstance(pts, (int, float)) and pts > 0:
            bits.append('%s +%s' % (lab, pts if pts == int(pts) else pts))
        elif isinstance(pts, (int, float)) and pts < 0:
            bits.append('%s %s' % (lab, pts))
        else:
            bits.append('%s 0' % lab)
    return '%s  →  %s / 250' % (' · '.join(bits), fmt10(n))


# Fichiers hebdo déjà utilisés par les fiches (ne pas inventer de source).
WEEKLY_FILES = {
    'btc':  ('binance', 'binance_BTCUSDT_1w.json', None),
    'eth':  ('binance', 'binance_ETHUSDT_1w.json', None),
    'sol':  ('yahoo',   'yahoo_1wk_SOL-USD.json', 'sunday'),
    'mstr': ('yahoo',   'yahoo_1wk_MSTR.json',    'friday'),
}


def _binance_weeks(path):
    import json, datetime as D
    k = json.loads(Path(path).read_text())
    nowms = D.datetime.now(D.timezone.utc).timestamp() * 1000
    w, opens = [], {}
    for x in k:
        o, c = float(x[1]), float(x[4])
        mon = D.datetime.fromtimestamp(x[0] / 1000, D.timezone.utc).date()
        fri = mon + D.timedelta(days=4)
        closed = x[6] < nowms
        if closed:
            w.append((fri.isoformat(), c, True))
            opens[fri.isoformat()] = o
    return w, opens


def _yahoo_weeks_safe(path, close_after='friday'):
    import json, datetime as D
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


def _closed_weekly(key):
    """Clôtures hebdomadaires confirmées + opens, pour un actif (btc/eth/sol/mstr)."""
    cfg = WEEKLY_FILES.get(key)
    if not cfg:
        return None
    kind, fname, close_after = cfg
    path = crypto_data_dir() / fname
    if not path.exists():
        return None
    if kind == 'binance':
        w, opens = _binance_weeks(path)
    else:
        w, opens = _yahoo_weeks_safe(path, close_after=close_after or 'friday')
    closed = [(d, c) for d, c, ok in w if ok]
    if len(closed) < 52:
        return None
    ds = [d for d, _c in closed]
    c = [x for _d, x in closed]
    o = []
    for d in ds:
        v = opens.get(d) if isinstance(opens, dict) else None
        o.append(v if v and v > 0 else None)
    return {'dates': ds, 'closes': c, 'opens': o}


def score_asset(obj, fg_value=None):
    """Calcule la note −50..250 d'un cryptoactif (HYPE 45 comptée dès que l'attention est disponible)."""
    from build_apex_achat_v2_pilot import rsi_points, macd_points, fibo_points, cci_points

    obj = obj or {}
    key = obj.get('key')
    wk = _closed_weekly(key) if key else None
    if not wk:
        return {
            'note': None, 'display': '–', 'hex': None, 'flag': 'none',
            'pos': None, 'cap': '', 'scale': 250, 'total': None,
            'total_min': -50, 'total_max': 250, 'ligne': '',
            'erreur': 'série hebdomadaire introuvable ou trop courte',
        }

    c, o, ds = wk['closes'], wk['opens'], wk['dates']
    r = K.rsi(c)
    rsi_val = r[-1]
    div = CH.divergence(c, ds, r)
    rsi_pts, rsi_det = rsi_points(rsi_val, div)
    m, sg, h = K.macd_series(c)
    macd_pts, macd_det = macd_points(m[-1], h)
    fib = obj.get('fibo') or {}
    r_hist = fib.get('r') if fib.get('ok') else None
    if r_hist is None:
        fib_calc = FB.analyse(o, c, ds, adjust_splits=(key == 'mstr'), sym=key, combine=False)
        r_hist = fib_calc.get('r') if fib_calc.get('ok') else None
    fibo_pts, fibo_det = fibo_points(r_hist)
    _k, d_s, _raw = K.cci_stochastic_kd(c)
    cci_val = d_s[-1] if d_s else None
    cci_pts, cci_det = cci_points(cci_val)

    liq_pts, liq_det = liquidite_points(obj.get('liquidite'))

    if fg_value is None:
        fng = obj.get('fng') or {}
        fg_value = fng.get('value') if fng else None
    fg_pts = fg_points(fg_value) if fg_value is not None else 0
    if fg_pts is None:
        fg_pts = 0

    # HYPE 45 : Attention Long Swing, à contre-courant. Absente → non comptée (« – »).
    try:
        from apply_attention import attention_of
    except ImportError:
        from src.apply_attention import attention_of
    att_val = attention_of((key or '').upper(), obj.get('tv'), obj.get('yahoo'), obj.get('ticker'), obj.get('nom'))
    hype_pts = hype_points_45(att_val)

    mm40_pts, mm40_det = mm40_hebdo_points(c)
    brut = int(rsi_pts + macd_pts + fibo_pts + cci_pts + liq_pts + fg_pts + (hype_pts or 0) + (mm40_pts or 0))
    n = max(-50, min(250, int(round_half(brut))))
    band = metaux_band(n)
    cap = []
    if not liq_det.get('present'):
        cap.append('sans_liq')
    if hype_pts is None:
        cap.append('hype_nc')

    parts = [
        ('RSI', rsi_pts), ('MACD', macd_pts), ('Fibo', fibo_pts), ('CCI', cci_pts),
        ('Liq.', liq_pts if liq_det.get('present') else '—'),
        ('F&G', fg_pts if fg_value is not None else '—'),
        ('Hype', hype_pts if hype_pts is not None else '—'),
        ('MM40 hebdo', (mm40_det or {}).get('texte') or mm40_hebdo_texte((mm40_det or {}).get('ecart'), mm40_pts)),
    ]
    texte = _ligne(parts, n)

    return {
        'note': n,
        'display': fmt10(n),
        'hex': band['hex'],
        'flag': band['flag'],
        'band': band['id'],
        'pos': n,
        'cap': '+'.join(cap),
        'timing': None,
        'fond': None if not liq_det.get('present') else int(liq_pts),
        'brut': brut,
        'decomp': {
            'texte': texte,
            'points': {
                'rsi': rsi_pts, 'macd': macd_pts, 'fibonacci': fibo_pts, 'cci': cci_pts,
                'liquidite': liq_pts if liq_det.get('present') else None,
                'hype': hype_pts,
                'mm40': mm40_pts,
                'fear_greed': fg_pts if fg_value is not None else None,
                'total': n,
            },
            'rsi': {'valeur': None if rsi_val is None else round(float(rsi_val), 1), 'points': rsi_pts, 'conditions': rsi_det},
            'macd': {'points': macd_pts, 'conditions': macd_det},
            'fibonacci': {**fibo_det, 'points': fibo_pts},
            'cci': {**cci_det, 'points': cci_pts},
            'liquidite': liq_det,
            'hype': {'points': hype_pts, 'attention': att_val, 'grille': '0→45, 10→41, 20→37, 30→33, 40→29, 50→25, 60→20, 70→15, 80→10, 90→5, 100→0', 'etat': 'applique' if hype_pts is not None else 'n.c.'},
            'mm40': mm40_det,
            'fear_greed': {'valeur': fg_value, 'points': fg_pts if fg_value is not None else None, 'source': 'alternative.me'},
            'echelle': 250,
        },
        'technique': int(rsi_pts + macd_pts + fibo_pts + cci_pts),
        'renormalise': False,
        'scale': 250,
        'total': n,
        'total_min': -50,
        'total_max': 250,
        'ligne': texte,
        'fg_points': fg_pts if fg_value is not None else None,
        'fg_value': fg_value,
        'v2': True,
    }


def apply_notes(fiches_path=None, tabs_path=None):
    """Écrit les notes −50..250 dans crypto_fiches.json et tabs_data.json (avec HYPE 45 si l'attention est disponible)."""
    import json
    fiches_path = Path(fiches_path or (ROOT / 'data' / 'crypto_fiches.json'))
    tabs_path = Path(tabs_path or (ROOT / 'data' / 'tabs_data.json'))
    data = json.loads(fiches_path.read_text(encoding='utf-8'))
    notes = []
    for a in data.get('assets') or []:
        rec = score_asset(a)
        a['apex10'] = rec
        if rec.get('note') is not None:
            notes.append(int(rec['note']))
    if notes:
        n = int(sum(notes) / len(notes) + 0.5)  # half-up, comme Math.round JS
        band = metaux_band(n)
        data['apex10'] = {
            'note': n, 'display': fmt10(n), 'hex': band['hex'], 'flag': band['flag'],
            'band': band['id'], 'pos': n, 'cap': 'moyenne', 'scale': 250, 'total': n,
            'total_min': -50, 'total_max': 250, 'v2': True, 'n_moy': len(notes),
            'ok': True,
        }
    fiches_path.write_text(json.dumps(data, ensure_ascii=False) + '\n', encoding='utf-8')
    if tabs_path.exists():
        tabs = json.loads(tabs_path.read_text(encoding='utf-8'))
        if 'crypto' not in tabs:
            tabs['crypto'] = {}
        tabs['crypto']['fiches'] = data
        tabs_path.write_text(json.dumps(tabs, ensure_ascii=False, separators=(',', ':')) + '\n', encoding='utf-8')
    return {a['key']: (a.get('apex10') or {}).get('note') for a in data.get('assets') or []}
