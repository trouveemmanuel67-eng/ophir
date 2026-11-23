"""Composantes techniques de la note APEX /10 (t329u).

Les scores sont dans [-100, +100] (+ = achat). Ils n'entrent pas dans
la note Achat / Vente du bandeau : seulement dans la note /10.
Structure = moyenne de (tendance hebdo, plus hauts et plus bas, position vs ATH).
Figure = détection hebdo (triangle, épaule-tête-épaule, double, biseau, drapeau) ;
neutre (0) si aucune figure validée.
"""
from __future__ import annotations

import sys
from pathlib import Path

_SRC = Path(__file__).resolve().parent
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

import charte as CH
from ind_core import clip, r_dd, cci_note

TECH_IDS = ('elliott', 'structure', 'fibonacci', 'figure', 'rsi', 'macd', 'cci')

# Préfixes des composantes déjà calculées par ind_core.compute
_PREFIX = {
    'elliott': ("Vagues d'Elliott", "Vague d'Elliott"),
    'fibonacci': ('Retracement de Fibonacci', 'Fibonacci'),
    'rsi': ('RSI 14',),
    'macd': ('MACD',),
    'cci': ('CCI 20', 'CCI '),
}


def notes_from_components(comps):
    out = {}
    figure = None
    for c in comps or []:
        if not isinstance(c, dict):
            continue
        nom = str(c.get('nom') or '')
        for key, prefs in _PREFIX.items():
            if any(nom.startswith(p) for p in prefs) and key not in out:
                out[key] = c.get('note')
        ch = c.get('charte') if isinstance(c.get('charte'), dict) else None
        if ch and ch.get('figure') and isinstance(ch['figure'], dict):
            if ch['figure'].get('note') is not None:
                figure = ch['figure']
    if figure and figure.get('note') is not None:
        out['figure'] = figure.get('note')
        out['figure_texte'] = figure.get('texte')
    return out


def _sma(vals, n):
    if len(vals) < n:
        return None
    return sum(vals[-n:]) / n


def score_structure(closes, highs=None, lows=None):
    """Tendance hebdo + plus hauts/plus bas + position vs ATH, à parts égales."""
    if not closes or len(closes) < 13:
        return None, {}
    c = float(closes[-1])
    n = len(closes)
    hi = list(highs) if highs and len(highs) == n else list(closes)
    lo = list(lows) if lows and len(lows) == n else list(closes)

    # 1) Tendance hebdo : écart à la MM40 et pente de la MM40 (5 semaines).
    tend = None
    detail = {}
    if n >= 40:
        sma = _sma(closes, 40)
        sma_prev = sum(closes[-45:-5]) / 40 if n >= 45 else sum(closes[-40:-1]) / 39
        if sma and sma_prev:
            gap = (c / sma - 1.0) * 100.0
            slope = (sma / sma_prev - 1.0) * 100.0
            tend = clip(0.6 * clip(gap / 8.0 * 100.0) + 0.4 * clip(slope / 2.0 * 100.0))
            detail['tendance'] = {'note': tend, 'gap_mm40': round(gap, 2), 'pente_5s': round(slope, 2)}
    elif n >= 13:
        sma = _sma(closes, 13)
        if sma:
            gap = (c / sma - 1.0) * 100.0
            tend = clip(gap / 8.0 * 100.0)
            detail['tendance'] = {'note': tend, 'gap_mm13': round(gap, 2)}

    # 2) Plus hauts et plus bas : deux fenêtres de 13 semaines.
    phpb = None
    if n >= 26:
        a_hi, a_lo = max(hi[-26:-13]), min(lo[-26:-13])
        b_hi, b_lo = max(hi[-13:]), min(lo[-13:])
        hh, hl_ = b_hi > a_hi, b_lo > a_lo
        lh, ll = b_hi < a_hi, b_lo < a_lo
        if hh and hl_:
            phpb = 100.0
            typ = 'plus hauts et plus bas plus hauts'
        elif lh and ll:
            phpb = -100.0
            typ = 'plus hauts et plus bas plus bas'
        elif hh and ll:
            phpb = 25.0
            typ = 'plus hauts plus hauts, plus bas plus bas (expansion)'
        elif lh and hl_:
            phpb = -25.0
            typ = 'plus hauts plus bas, plus bas plus hauts (compression)'
        else:
            phpb = 0.0
            typ = 'structure mixte'
        detail['plus_hauts_plus_bas'] = {'note': phpb, 'texte': typ}

    # 3) Position par rapport à l'ATH (corps), même barème que r_dd.
    ath = max(closes)
    dd = (c / ath - 1.0) * 100.0 if ath else 0.0
    ath_s = r_dd(dd)
    detail['ath'] = {'note': ath_s, 'dd': round(dd, 2)}

    parts = [x for x in (tend, phpb, ath_s) if x is not None]
    if not parts:
        return None, detail
    note = sum(parts) / len(parts)
    return float(clip(note)), detail


def _pivots(v, k=3):
    return CH.pivots(v, k)


def _valid_break(c, start, lvl, down):
    return CH._valid_break(c, start, lvl, down)


def _triangle(c, ds):
    """Triangle hebdo validé par une clôture hors des droites (sinon None)."""
    n = len(c)
    if n < 16:
        return None
    lo0 = max(0, n - 80)
    H, L = _pivots(c, 3)
    H = [i for i in H if i >= lo0]
    L = [i for i in L if i >= lo0]
    found = []
    for hs in range(len(H) - 1):
        for ls in range(len(L) - 1):
            i0, i1 = H[hs], H[hs + 1]
            j0, j1 = L[ls], L[ls + 1]
            start, end = min(i0, j0), max(i1, j1)
            if end - start < 8 or end - start > 52:
                continue
            if i1 == i0 or j1 == j0:
                continue
            # droites des deux derniers pivots hauts / bas
            sh = (c[i1] - c[i0]) / (i1 - i0)
            sl = (c[j1] - c[j0]) / (j1 - j0)
            # convergentes : hauts non haussiers, bas non baissiers, pentes distinctes
            if sh > 0.15 * c[i0] / 50 or sl < -0.15 * c[j0] / 50:
                continue
            if abs(sh - sl) < 1e-12:
                continue
            def up(q, sh=sh, i0=i0):
                return c[i0] + sh * (q - i0)
            def dn(q, sl=sl, j0=j0):
                return c[j0] + sl * (q - j0)
            # au moins une compression : l'écart final < 70 % de l'écart initial
            w0 = up(start) - dn(start)
            w1 = up(end) - dn(end)
            if w0 <= 0 or w1 <= 0 or w1 > 0.7 * w0:
                continue
            # cassure après le dernier pivot
            last_p = max(i1, j1)
            j_down = _valid_break(c, last_p, up, True)
            j_up = _valid_break(c, last_p, dn, False)
            typ = 'triangle'
            if abs(sh) < abs(sl) * 0.25:
                typ = 'triangle ascendant' if sl > 0 else 'triangle'
            elif abs(sl) < abs(sh) * 0.25:
                typ = 'triangle descendant' if sh < 0 else 'triangle'
            else:
                typ = 'triangle symétrique'
            if j_up is not None and (j_down is None or j_up <= j_down):
                found.append((j_up, 70.0, f"{typ} cassé par le haut, clôture du {CH.fd(ds[j_up])}"))
            elif j_down is not None:
                found.append((j_down, -70.0, f"{typ} cassé par le bas, clôture du {CH.fd(ds[j_down])}"))
    if not found:
        return None
    return max(found, key=lambda x: (x[0], abs(x[1])))


def _flag(c, ds):
    """Drapeau hebdo : hampe vive puis canal court, validé par cassure."""
    n = len(c)
    if n < 12:
        return None
    found = []
    for pole_len in (3, 4, 5, 6, 7, 8):
        for flag_len in (3, 4, 5, 6, 7, 8):
            i1 = n - 1 - flag_len
            i0 = i1 - pole_len
            if i0 < 1:
                continue
            pole = c[i1] / c[i0] - 1.0
            if abs(pole) < 0.12:
                continue
            flag = c[i1:i1 + flag_len + 1]
            if len(flag) < 4:
                continue
            fr = (max(flag) - min(flag)) / c[i1]
            if fr > 0.5 * abs(pole):
                continue
            # canal contraire ou latéral
            flag_move = flag[-1] / flag[0] - 1.0
            if pole > 0 and flag_move > 0.4 * pole:
                continue
            if pole < 0 and flag_move < 0.4 * pole:
                continue
            # cassure dans le sens de la hampe sur la dernière barre
            last = c[-1]
            if pole > 0 and last > max(flag[:-1]) * 1.002:
                found.append((n - 1, 70.0, f"drapeau haussier validé (hampe {pole*100:.1f} %, {flag_len} s.)"))
            elif pole < 0 and last < min(flag[:-1]) * 0.998:
                found.append((n - 1, -70.0, f"drapeau baissier validé (hampe {pole*100:.1f} %, {flag_len} s.)"))
    if not found:
        return None
    return max(found, key=lambda x: (x[0], abs(x[1])))


def score_figure(closes, dates, opens=None):
    """Note unique : figure la plus récente parmi les détecteurs weekly. 0 si aucune."""
    if not closes or not dates or len(closes) < 8:
        return 0.0, {'texte': 'Aucune figure chartiste validée', 'note': 0.0}
    c = list(closes)
    ds = list(dates)
    o = list(opens) if opens is not None else None
    cands = []
    fg = CH.figures(c, ds, o)
    if fg and fg.get('note') is not None:
        idx = ds.index(fg['date']) if fg.get('date') in ds else len(ds) - 1
        cands.append((idx, float(fg['note']), fg.get('texte') or 'figure', int(fg.get('prio') or 1)))
    tri = _triangle(c, ds)
    if tri:
        cands.append((tri[0], tri[1], 'Figure : ' + tri[2], 1))
    fl = _flag(c, ds)
    if fl:
        cands.append((fl[0], fl[1], 'Figure : ' + fl[2], 1))
    if not cands:
        return 0.0, {'texte': 'Aucune figure chartiste validée', 'note': 0.0}
    j, note, txt, prio = max(cands, key=lambda x: (x[0], x[3], abs(x[1])))
    return float(clip(note)), {'texte': txt, 'note': float(note), 'date': ds[j] if 0 <= j < len(ds) else None}


def _hl_aligned(dates, hl, closes):
    if not hl:
        return None, None
    hi, lo = [], []
    for d, c in zip(dates, closes):
        v = hl.get(d)
        if v is None:
            hi.append(c)
            lo.append(c)
        elif isinstance(v, (list, tuple)) and len(v) >= 2:
            hi.append(v[0] if v[0] is not None else c)
            lo.append(v[1] if v[1] is not None else c)
        else:
            hi.append(c)
            lo.append(c)
    return hi, lo


def pack_from_compute(out, closes, dates, opens=None, hl=None):
    """Construit le dict technique à partir du résultat de ind_core.compute."""
    av = (out or {}).get('av') or {}
    got = notes_from_components(av.get('components'))
    # CCI hors zone ±100 : neutre 0 pour la note /10 (le critère compte toujours).
    if got.get('cci') is None:
        got['cci'] = 0.0
    hi, lo = _hl_aligned(dates, hl, closes)
    st, st_d = score_structure(closes, hi, lo)
    got['structure'] = None if st is None else round(st, 1)
    got['structure_detail'] = st_d
    fg_note, fg_d = score_figure(closes, dates, opens)
    # Si une figure était déjà lue dans la charte, on garde la plus récente / |note| max.
    if got.get('figure') is not None and fg_d.get('note') == 0:
        pass
    else:
        got['figure'] = round(fg_note, 1)
        got['figure_texte'] = fg_d.get('texte')
    ell = (out or {}).get('elliott') or {}
    if got.get('elliott') is None and ell.get('note') is not None:
        got['elliott'] = ell.get('note')
    fib = (out or {}).get('fibo') or {}
    if got.get('fibonacci') is None and fib.get('note') is not None:
        got['fibonacci'] = fib.get('note')
    for k in TECH_IDS:
        v = got.get(k)
        if v is not None:
            got[k] = round(float(v), 1)
    return got


def collect_parts(obj):
    """Lit un dict technique déjà posé, sinon le reconstitue depuis av.components."""
    if not isinstance(obj, dict):
        return None
    t = obj.get('technique')
    if not t and isinstance(obj.get('av'), dict):
        t = obj['av'].get('technique')
    if isinstance(t, dict) and any(t.get(k) is not None for k in TECH_IDS):
        return {k: t.get(k) for k in TECH_IDS if k in t or True}
    av = obj.get('av') if isinstance(obj.get('av'), dict) else {}
    got = notes_from_components(av.get('components'))
    if got.get('cci') is None and any(k in got for k in ('rsi', 'macd', 'elliott', 'fibonacci')):
        got['cci'] = 0.0
    if any(got.get(k) is not None for k in TECH_IDS):
        return got
    return None


def cci_score_always(v):
    n = cci_note(v)
    return 0.0 if n is None else float(n)
