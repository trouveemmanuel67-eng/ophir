"""Note métaux APEX en points entiers additifs, même échelle et mêmes paliers que les actions (t475u)."""
from __future__ import annotations

import os
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
from technique_apex import score_structure

from .score import load_cnn_fg, metaux_band, metaux_cfg, divergence_haussiere, fmt10, round_half

FUT = {'Or': 'GC=F', 'Argent': 'SI=F', 'Platine': 'PL=F', 'Palladium': 'PA=F'}

METAUX_PATS = [
    str(ROOT / 'data/metaux/y_{enc}.json'),
    str(ROOT / 'data/metaux/y_{sym}.json'),
    str(ROOT / 'data/fibo_max/{enc}.json'),
    str(ROOT / 'data/secteurs/yahoo_1wk_{enc}.json'),
    str(ROOT / 'data/pays/yahoo_1wk_{enc}.json'),
    str(ROOT / 'data/actions/yahoo_1wk_{enc}.json'),
    str(ROOT / 'data/pays/wk/{sym}.json'),
]


def _quote(s):
    import urllib.parse
    return urllib.parse.quote(s, safe='')


def yahoo_cands_metaux(tv=None, yahoo=None, ticker=None, metal=None, kind=None):
    from build_apex_achat_v2_pilot import yahoo_cands
    cands = list(yahoo_cands(tv, yahoo, ticker))
    extra = []
    if tv and ':' in tv:
        ex, t = tv.split(':', 1)
        if ex == 'LSE':
            extra.append(t + '.L')
        elif ex == 'EURONEXT':
            extra.extend([t + '.AS', t + '.PA', t + '.L'])
        elif ex == 'OANDA' and metal and metal in FUT:
            extra.append(FUT[metal])
    if kind in ('spot', 'fut', 'futur') and metal in FUT:
        extra.append(FUT[metal])
    for x in extra:
        if x and x not in cands:
            cands.append(x)
    return cands


def find_wk_metaux(cands):
    for s in cands or []:
        enc = _quote(s)
        for pat in METAUX_PATS:
            p = pat.format(sym=s, enc=enc)
            if os.path.exists(p):
                return p, s
    return None, None


def structure_points(closes, highs=None, lows=None):
    """Sans fondamental : Structure à la place du fondamental, paliers de 10, max 90.

    Trois blocs de 30 points, issus des trois composantes déjà utilisées
    (tendance MM40 / pente 5 s., plus hauts et plus bas 13 s., position vs ATH) :
    − Tendance : note ≥ 70 → +30 ; ≥ 40 → +20 ; ≥ 10 → +10 ; sinon 0
    − PH/PB : plus hauts et plus bas plus hauts → +30 ; expansion → +10 ; sinon 0
    − ATH : note r_dd ≥ 50 → +30 ; ≥ 20 → +20 ; > 0 → +10 ; sinon 0
    """
    st, det = score_structure(closes, highs, lows)
    tend = (det.get('tendance') or {}).get('note')
    if tend is not None and tend >= 70:
        tp = 30
    elif tend is not None and tend >= 40:
        tp = 20
    elif tend is not None and tend >= 10:
        tp = 10
    else:
        tp = 0
    ph = det.get('plus_hauts_plus_bas') or {}
    note_ph = ph.get('note')
    if note_ph == 100:
        pp = 30
    elif note_ph == 25:
        pp = 10
    else:
        pp = 0
    ath = (det.get('ath') or {}).get('note')
    if ath is not None and ath >= 50:
        ap = 30
    elif ath is not None and ath >= 20:
        ap = 20
    elif ath is not None and ath > 0:
        ap = 10
    else:
        ap = 0
    total = min(90, int(tp + pp + ap))
    return total, {
        'points': total,
        'max': 90,
        'note_brute': None if st is None else round(float(st), 1),
        'blocs': [
            {'id': 'tendance', 'label': 'Tendance MM40 / pente 5 s.', 'points': tp, 'valeur': tend},
            {'id': 'phpb', 'label': 'Plus hauts / plus bas 13 s.', 'points': pp, 'valeur': note_ph, 'texte': ph.get('texte')},
            {'id': 'ath', 'label': 'Position vs ATH', 'points': ap, 'valeur': ath, 'dd': (det.get('ath') or {}).get('dd')},
        ],
    }


def _ligne(parts, total):
    bits = []
    for lab, pts in parts:
        if pts is None:
            continue
        if lab == 'F&G':
            bits.append(f"F&G {pts:+d}".replace('+', '+').replace('+-', '−').replace('-', '−') if pts < 0 else f"F&G +{pts}")
        else:
            bits.append(f"{lab} {pts}")
    return ' · '.join(bits) + f"  →  {total} / 250"


def score_instrument(obj, metal=None, av=None, fg=None):
    """Calcule la note −50..250 en points entiers pour un instrument ou un contrat."""
    from build_apex_achat_v2_pilot import (
        rsi_points, macd_points, fibo_points, cci_points, fond_points, load_closed_weekly,
    )
    from .score import _R

    cfg = metaux_cfg()
    obj = obj or {}
    metal = metal or obj.get('metal') or obj.get('nom_metal')
    kind = obj.get('kind')
    cands = yahoo_cands_metaux(
        obj.get('tv'), obj.get('yahoo') or obj.get('sym'),
        obj.get('ticker') or obj.get('sym'), metal=metal, kind=kind,
    )
    path, used = find_wk_metaux(cands)
    if not path:
        return {
            'note': None, 'display': '–', 'hex': None, 'flag': 'none',
            'pos': None, 'cap': '', 'scale': 250, 'total': None,
            'total_min': cfg['min'], 'total_max': cfg['max'], 'ligne': '',
            'erreur': 'série hebdomadaire introuvable',
        }
    closed, meta, _all = load_closed_weekly(path)
    if len(closed) < 52:
        return {
            'note': None, 'display': '–', 'hex': None, 'flag': 'none',
            'pos': None, 'cap': '', 'scale': 250, 'total': None,
            'total_min': cfg['min'], 'total_max': cfg['max'], 'ligne': '',
            'erreur': f'historique insuffisant ({len(closed)} semaines)',
        }
    c = [b['close'] for b in closed]
    o = [b.get('open') if b.get('open') and b['open'] > 0 else None for b in closed]
    ds = [b['date'] for b in closed]
    hi = [b.get('high') or b['close'] for b in closed]
    lo = [b.get('low') or b['close'] for b in closed]
    r = K.rsi(c)
    rsi_val = r[-1]
    div = CH.divergence(c, ds, r)
    rsi_pts, rsi_det = rsi_points(rsi_val, div)
    m, sg, h = K.macd_series(c)
    macd_pts, macd_det = macd_points(m[-1], h)
    fib = FB.analyse(o, c, ds, adjust_splits=True, sym=used, syms=[used, obj.get('tv'), obj.get('ticker')], combine=False)
    r_hist = fib.get('r') if fib.get('ok') else None
    fibo_pts, fibo_det = fibo_points(r_hist)
    _k, d_s, _raw = K.cci_stochastic_kd(c)
    cci_val = d_s[-1] if d_s else None
    cci_pts, cci_det = cci_points(cci_val)

    mdict = obj.get('m') if kind == 'min' else None
    has_fond = bool(mdict) and any(v is not None for v in mdict.values())
    cap = []
    struct_pts, struct_det = None, None
    if has_fond:
        fond_total, fond_elems = fond_points(mdict)
        extra = int(fond_total)
    else:
        # t483u : Structure retirée de la note, sans redistribution (comme Elliott).
        fond_total, fond_elems = None, None
        extra = 0
        cap.append('sans_fond')

    if fg is None:
        fg = load_cnn_fg()
    fg_pts = int(fg['points']) if fg and fg.get('ok') else 0
    brut = int(rsi_pts + macd_pts + fibo_pts + cci_pts + extra + fg_pts)
    n = max(int(cfg['min']), min(int(cfg['max']), int(round_half(brut))))
    # Portail cyan : même seuils 190 / 175, confirmation divergence haussière hebdo + AV ≥ +60.
    rcfg = _R()
    cy_av = (rcfg.get('cyan') or {}).get('av_achat_fort', 60)
    if av is None and isinstance(obj.get('av'), dict):
        av = obj['av'].get('score')
    if n >= cfg['cyan_min']:
        av_fort = (av is not None) and (float(av) >= cy_av)
        conf = divergence_haussiere(div)
        if not (av_fort and conf):
            n = int(cfg['cyan_plafond'])
            cap.append('cyan')
    cap = [c for c in cap if c]
    band = metaux_band(n)
    parts = [
        ('RSI', rsi_pts), ('MACD', macd_pts), ('Fibo', fibo_pts), ('CCI', cci_pts),
        *( [('Fond.', extra)] if has_fond else [] ),
        ('F&G', fg_pts if fg and fg.get('ok') else None),
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
        'fond': None if fond_total is None else int(fond_total),
        'brut': brut,
        'decomp': {
            'texte': texte,
            'points': {
                'rsi': rsi_pts, 'macd': macd_pts, 'fibonacci': fibo_pts, 'cci': cci_pts,
                'fondamental': fond_total, 'structure': struct_pts,
                'fear_greed': fg_pts if fg and fg.get('ok') else None, 'total': n,
            },
            'rsi': {'valeur': None if rsi_val is None else round(float(rsi_val), 1), 'points': rsi_pts, 'conditions': rsi_det},
            'macd': {'points': macd_pts, 'conditions': macd_det},
            'fibonacci': {**fibo_det, 'points': fibo_pts},
            'cci': {**cci_det, 'points': cci_pts},
            'fondamental': {'points': fond_total, 'elements': fond_elems} if has_fond else None,
            'structure': struct_det,
            'echelle': 250,
        },
        'technique': None,
        'renormalise': False,
        'scale': 250,
        'total': n,
        'total_min': cfg['min'],
        'total_max': cfg['max'],
        'ligne': texte,
        'fg_points': fg_pts if fg and fg.get('ok') else None,
        'fg_value': fg.get('value') if fg and fg.get('ok') else None,
        'weekly_used': used,
        'date_cloture': closed[-1]['date'],
        'm': mdict if has_fond else None,
    }


def moyenne_ligne(notes):
    cfg = metaux_cfg()
    if not notes:
        return None
    avg = int(round_half(sum(notes) / len(notes)))
    avg = max(int(cfg['min']), min(int(cfg['max']), avg))
    band = metaux_band(avg)
    return {
        'note': avg, 'display': fmt10(avg),
        'hex': band['hex'], 'flag': band['flag'], 'band': band['id'],
        'pos': avg, 'cap': 'moyenne',
        'fond': None, 'n_moy': len(notes),
        'detail': 'Moyenne des notes −50 à 250 des instruments visibles (ETC, métal au comptant, minières), hors titres sans note.',
        'scale': 250, 'total': avg, 'total_min': cfg['min'], 'total_max': cfg['max'],
        'ligne': 'moyenne de %d instrument%s  →  %s / 250' % (len(notes), 's' if len(notes) > 1 else '', fmt10(avg)),
    }
