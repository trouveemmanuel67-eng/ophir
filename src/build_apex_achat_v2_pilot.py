#!/usr/bin/env python3
"""Pilote APEX ACHAT (accumulation de points).

Communication (XLC / ZPDK) : règles apex_achat_v2.
Finance / banques USA (XLF / ZPDF) : règles apex_achat_v2_banque.
Les autres sections ne sont pas recalculées ici.

Règles : tableau RÈGLES (commit ca3fba7+), bougies hebdo clôturées, départ 0.
"""
from __future__ import annotations
import json, os, sys, math, subprocess, urllib.parse
from datetime import datetime, date, timedelta, timezone
from zoneinfo import ZoneInfo
from pathlib import Path

DIR = Path(__file__).resolve().parent
ROOT = DIR.parent
sys.path.insert(0, str(DIR))
sys.path.insert(0, str(ROOT))

import ind_core as K
import fibo as FB
import yahoo_week as YW
import charte as CH
import elliott_zones as EZ
import elliott as E
from note_apex import divergence_haussiere
from apex.score import mm40_hebdo_points, mm40_hebdo_texte, MM40_HEBDO_MAX_AUTRES

PARIS = ZoneInfo('Europe/Paris')
NOW = datetime.now(PARIS)

# --- univers du pilote ---
SECTOR_SYM = 'XLC'
ETF = {
    'id': 'etf',
    'ticker': 'ZPDK',
    'yahoo': 'ZPDK.DE',
    'tv': 'XETR:ZPDK',
    'nom': 'SPDR S&P U.S. Communication Services Select Sector UCITS ETF',
}
# Les 5 actions « qualité / croissance » (classement fondamental existant, top 5)
# sont lues dynamiquement depuis fondamentaux.json.

SCALE_MIN = -50
SCALE_MAX = 250  # APE-25 : technique 99 + fondamental 81 + H ±27 + F&G ±50 (borné −50..250) (compression ×0,9 dans apply_attention)
HYPE_ABS = 27
TECH_MAX = 110
FOND_MAX = 90
FG_ABS = 50

CNN_URL = 'https://production.dataviz.cnn.io/index/fearandgreed/graphdata/2025-10-01'
CNN_PAGE = 'https://edition.cnn.com/markets/fear-and-greed'

ROOTS = [
    str(ROOT / 'data/fibo_max/{enc}.json'),
    str(ROOT / 'data/secteurs/yahoo_1wk_{enc}.json'),
    str(ROOT / 'data/pays/yahoo_1wk_{enc}.json'),
    str(ROOT / 'data/actions/yahoo_1wk_{enc}.json'),
    str(ROOT / 'data/energie/yahoo_1wk_{enc}.json'),
    str(ROOT / 'data/short_cache/yahoo_1wk_{enc}.json'),
    str(ROOT / 'data/pays/wk/{sym}.json'),
]


def quote(s):
    return urllib.parse.quote(s, safe='')


def find_wk(cands):
    for s in cands:
        enc = quote(s)
        for pat in ROOTS:
            p = pat.format(sym=s, enc=enc)
            if os.path.exists(p):
                return p, s
    return None, None


def yahoo_cands(tv, yahoo=None, ticker=None):
    cands = []
    for x in (yahoo, ticker):
        if x and x not in cands:
            cands.append(x)
    if tv and ':' in tv:
        ex, t = tv.split(':', 1)
        mp = {'XETR': [t + '.DE'], 'NYSE': [t], 'NASDAQ': [t], 'AMEX': [t]}
        for x in mp.get(ex, [t]) + [t]:
            if x and x not in cands:
                cands.append(x)
    elif tv and tv not in cands:
        cands.append(tv)
    return cands


def load_closed_weekly(path):
    bars, meta = YW.parse_yahoo_weekly(path, now=NOW)
    closed = [b for b in bars if b.get('closed') and b.get('close') and b['close'] > 0]
    return closed, meta, bars


def fg_points(value):
    """Tranches de 10 autour de 50 : 40→+10 … 0→+50 ; 60→−10 … 100→−50.
    Une tranche n'est comptée que lorsqu'elle est entièrement franchie
    (floor de |50 − valeur| / 10), plafonnée à ±50.
    Ex. 17,7 → écart 32,3 → 3 tranches → +30 (seuil 20 atteint, 10 pas encore).
    """
    if value is None or not math.isfinite(float(value)):
        return None
    v = float(value)
    delta = 50.0 - v
    n = int(math.floor(abs(delta) / 10.0))
    n = min(5, n)
    pts = n * 10
    return pts if delta >= 0 else -pts


def fg_label(v):
    v = float(v)
    return 'Peur extrême' if v < 25 else 'Peur' if v < 45 else 'Neutre' if v <= 55 else 'Avidité' if v <= 75 else 'Euphorie'


def fetch_cnn_fng(reuse_file=True):
    """Télécharge l'indice CNN officiel. Pas de valeur inventée : en cas d'échec, on le signale."""
    dest = ROOT / 'data' / 'apex_achat_v2_cnn_fng.json'
    raw = None
    if reuse_file and dest.exists():
        try:
            cand = json.loads(dest.read_text(encoding='utf-8'))
            if (cand.get('fear_and_greed') or {}).get('score') is not None:
                raw = cand
        except Exception:
            raw = None
    cmd = [
        'curl', '-sS', '-L', '--max-time', '25',
        '-A', 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
        '-H', 'Accept: application/json,text/plain,*/*',
        '-H', 'Accept-Language: en-US,en;q=0.9',
        '-H', 'Referer: https://edition.cnn.com/markets/fear-and-greed',
        '-H', 'Origin: https://edition.cnn.com',
        '-o', str(dest),
        '-w', '%{http_code}',
        CNN_URL,
    ]
    if raw is None:
        try:
            code = subprocess.check_output(cmd, text=True).strip()
            if code != '200':
                return {'ok': False, 'erreur': f'HTTP {code}', 'url': CNN_URL}
            raw = json.loads(dest.read_text(encoding='utf-8'))
        except Exception as e:
            return {'ok': False, 'erreur': f'{type(e).__name__}: {e}', 'url': CNN_URL}

    fg = raw.get('fear_and_greed') or {}
    hist = (raw.get('fear_and_greed_historical') or {}).get('data') or []
    score = fg.get('score')
    ts = fg.get('timestamp')
    if score is None:
        return {'ok': False, 'erreur': 'pas de score dans la réponse CNN', 'url': CNN_URL}

    series = []
    for x in hist:
        try:
            d = datetime.fromtimestamp(x['x'] / 1000, timezone.utc).date().isoformat()
            series.append([d, float(x['y'])])
        except Exception:
            continue
    series.sort()
    if not series:
        # au moins la valeur courante
        d = None
        if ts:
            try:
                d = datetime.fromisoformat(ts.replace('Z', '+00:00')).astimezone(PARIS).date().isoformat()
            except Exception:
                d = None
        if d:
            series = [[d, float(score)]]

    last = series[-1]
    start = (date.fromisoformat(last[0]) - timedelta(days=365)).isoformat()
    win = [x for x in series if x[0] > start]
    if not win:
        win = series
    vals = [x[1] for x in win]
    mn = min(win, key=lambda x: x[1])
    mx = max(win, key=lambda x: x[1])
    retrieved = NOW.strftime('%Y-%m-%d %H:%M') + ' Europe/Paris'
    # date officielle du point : timestamp CNN, converti Europe/Paris
    date_valeur = last[0]
    if ts:
        try:
            date_valeur = datetime.fromisoformat(ts.replace('Z', '+00:00')).astimezone(PARIS).strftime('%Y-%m-%d %H:%M') + ' Europe/Paris'
        except Exception:
            date_valeur = last[0]

    value = round(float(score), 1)
    pts = fg_points(float(score))
    return {
        'ok': True,
        'value': value,
        'value_raw': float(score),
        'label': fg_label(value),
        'rating_cnn': fg.get('rating'),
        'points': pts,
        'date_valeur': date_valeur,
        'date_serie': last[0],
        'timestamp_cnn': ts,
        'retrieved': retrieved,
        'source': {'name': 'CNN Business', 'url': CNN_PAGE, 'api': CNN_URL},
        'avg': round(sum(vals) / len(vals), 1),
        'min': [mn[0], round(mn[1], 1)],
        'max': [mx[0], round(mx[1], 1)],
        'n': len(win),
        'series': [[d, round(v, 1)] for d, v in win],
        'interpretation': (
            "Milieu 50 = 0. Tranches entières de 10 points d'écart "
            "(floor(|50 − valeur| / 10) × 10, signé, max ±50)."
        ),
    }


def rsi_points(rsi_val, div):
    pts, det = 0, []
    if rsi_val is not None and rsi_val < 40:
        pts += 10
        det.append({'id': 'rsi_sous_40', 'ok': True, 'points': 10, 'valeur': round(rsi_val, 1)})
    else:
        det.append({'id': 'rsi_sous_40', 'ok': False, 'points': 0, 'valeur': None if rsi_val is None else round(rsi_val, 1)})
    bull = divergence_haussiere(div)
    if bull:
        pts += 20
        det.append({'id': 'divergence_rsi_haussiere_hebdo', 'ok': True, 'points': 20, 'texte': (div or {}).get('texte')})
    else:
        det.append({'id': 'divergence_rsi_haussiere_hebdo', 'ok': False, 'points': 0, 'texte': (div or {}).get('texte') if isinstance(div, dict) else None})
    return min(30, pts), det


def macd_points(macd_line, hist):
    """MACD 12/26/9 hebdo, plafond 30.

    +10 si la ligne MACD est < 0.
    +20 si la ligne est < 0 ET 4 barres rouges consécutives sur l'histogramme
    clôturé : soit 4 histogrammes < 0 d'affilée, soit 4 barres chacune
    inférieure à la précédente (pente, lecture visuelle habituelle).
    Les deux bonus sont cumulables, puis min(30, pts).
    """
    pts, det = 0, []
    sous = macd_line is not None and macd_line < 0
    if sous:
        pts += 10
    det.append({'id': 'macd_sous_0', 'ok': bool(sous), 'points': 10 if sous else 0, 'valeur': None if macd_line is None else round(macd_line, 4)})
    streak = 0
    if hist:
        for h in reversed(hist):
            if h is not None and h < 0:
                streak += 1
            else:
                break
    streak_rouge_pente = 0
    if hist and len(hist) >= 5:
        for i in range(len(hist) - 1, len(hist) - 5, -1):
            a, b = hist[i - 1], hist[i]
            if a is not None and b is not None and b < a:
                streak_rouge_pente += 1
            else:
                break
    quatre = (streak >= 4) or (streak_rouge_pente >= 4)
    ok20 = bool(sous and quatre)
    if ok20:
        pts += 20
    det.append({
        'id': 'histo_4_barres_rouges_sous_0',
        'ok': ok20,
        'points': 20 if ok20 else 0,
        'streak': streak,
        'streak_rouge_pente': streak_rouge_pente,
        'macd_sous_0': bool(sous),
    })
    return min(30, pts), det


def fibo_points(r):
    """« sous X % » = retracement depuis le plus haut historique au-delà de X %
    (r = (ATH − cours) / (ATH − plus bas historique), corps hebdo).
    Paliers non cumulables : r ≥ 78,6 % → 30 ; ≥ 61,8 % → 20 ; ≥ 38,2 % → 10 ; sinon 0.
    """
    if r is None:
        return 0, {'ok': False, 'r': None, 'points': 0, 'palier': None}
    if r >= 0.786:
        pts, palier = 30, '78,6 %'
    elif r >= 0.618:
        pts, palier = 20, '61,8 %'
    elif r >= 0.382:
        pts, palier = 10, '38,2 %'
    else:
        pts, palier = 0, None
    return pts, {'ok': True, 'r': round(float(r), 4), 'r_pct': round(float(r) * 100, 1), 'points': pts, 'palier': palier}


def elliott_points(key):
    """Ancienne lecture sur la seule clé officielle (conservée pour les tests unitaires)."""
    entry = bool(key) and (key in EZ.ZONE_VERTE or key == 'new1')
    motif = None
    if key in EZ.ZONE_VERTE:
        motif = 'zone d’entrée (fin de vague 2, fin de vague 4, vague C)'
    elif key == 'new1':
        motif = 'après une vague C terminée, nouvelle vague 1 non confirmée'
    return (20 if entry else 0), {
        'key': key, 'entry': entry,
        'zone': 'verte' if entry else ('rouge' if key in EZ.ZONE_ROUGE else 'hors zone'),
        'motif': motif,
    }


def _elliott_all_candidates(opens, closes):
    """Tous les décomptes valides, le meilleur en tête (même barème que elliott.analyse)."""
    import math, statistics as st
    n = len(closes)
    if n < 60:
        return []
    hi, lo = E.bodies(opens, closes)
    r = [abs(math.log(closes[i] / closes[i - 1])) for i in range(max(1, n - 260), n) if closes[i] and closes[i - 1]]
    sig = st.median(r) if r else .02
    thrs = sorted(set(round(min(.60, max(.04, sig * k)), 3) for k in (4, 5, 6, 8, 10, 13, 16)))
    cands = []
    last = closes[-1]

    def cand(key, conf, npts, thr, pts, extra, idx):
        cands.append({
            'key': key, 'conf': float(conf), 'npts': npts, 'thr': thr,
            'points': [round(x, 4) for x in pts], 'idx': list(idx),
            'extra': {a: (round(b, 3) if isinstance(b, float) else b) for a, b in (extra or {}).items()},
        })

    for thr in thrs:
        pv = E.zigzag(hi, lo, thr)[-E.NPIV:]
        if len(pv) < 2:
            continue
        run = pv[-1]
        up = run[2] == 'H'
        turn = (last / run[1] - 1) if not up else (1 - last / run[1])
        turned = turn >= 0.3 * thr
        for k, idz in E.subseqs(pv):
            pts = [pv[i][1] for i in idz]
            first = pv[idz[0]][2]
            idx = [pv[i][0] for i in idz]
            if first == 'L':
                E._bull(pts, k, thr, turned, last, lambda *a: cand(*a, idx))
            elif k >= 4:
                E._bear(pts, k, thr, lambda *a: cand(*a, idx))
    cands.sort(key=lambda x: (x['conf'], x['npts'], -(x['thr'] or 0)), reverse=True)
    return cands


def elliott_entry(opens, closes, dates, stored_key=None):
    """+20 si zone d'entrée (fin 2, fin 4, vague C) OU après une C terminée
    tant qu'aucune nouvelle vague 1 n'est confirmée (clé new1, officielle ou lecture alternative).
    """
    official = E.analyse(opens, closes) if opens is not None and closes and len(closes) >= 60 else {}
    key = official.get('key') or stored_key
    base = {
        'key': key,
        'key_officielle': official.get('key') or stored_key,
        'conf': official.get('conf'),
        'texte': official.get('texte'),
        'points_officiels': official.get('points'),
        'dates_officielles': ([dates[i] for i in official.get('idx', [])] if dates and official.get('idx') else None),
    }

    def pack(pts, det):
        merged = dict(base)
        merged.update(det)  # la lecture retenue (ex. new1) prime sur la clé officielle
        merged['entry'] = pts == 20
        merged['zone'] = 'verte' if merged['entry'] else ('rouge' if key in EZ.ZONE_ROUGE else 'hors zone')
        merged['points'] = pts
        return pts, merged

    if key in EZ.ZONE_VERTE:
        return pack(20, {'motif': 'zone d’entrée (fin de vague 2, fin de vague 4, vague C)'})
    if key == 'new1':
        extra = official.get('extra') or {}
        return pack(20, {
            'motif': 'après une vague C terminée, nouvelle vague 1 non confirmée',
            'rise': extra.get('rise'),
        })

    # Lecture alternative : vague C terminée puis rebond, vague 1 non confirmée (rise < 38,2 %)
    for cand in _elliott_all_candidates(opens, closes):
        if cand['key'] != 'new1':
            continue
        idx, pts = cand.get('idx') or [], cand.get('points') or []
        # P[8] = fin de C, P[9] = rebond (convention elliott._bull, k==10)
        c_fin = None
        rebond = None
        if len(idx) >= 10 and dates:
            i_c, i_r = idx[8], idx[9]
            if 0 <= i_c < len(dates):
                c_fin = {'date': dates[i_c], 'prix': pts[8] if len(pts) > 8 else None}
            if 0 <= i_r < len(dates):
                rebond = {'date': dates[i_r], 'prix': pts[9] if len(pts) > 9 else None}
        return pack(20, {
            'motif': 'après une vague C terminée, aucune nouvelle vague 1 confirmée',
            'lecture': 'alternative (le décompte officiel n’est pas une zone d’entrée)',
            'key': 'new1',
            'key_alternative': 'new1',
            'conf_alternative': cand['conf'],
            'rise': (cand.get('extra') or {}).get('rise'),
            'c_fin': c_fin,
            'rebond': rebond,
            'points_alternatifs': pts,
        })
    return pack(0, {'motif': None})


def cci_points(cci_val):
    """CCI Stochastic de Daveatt (0–100) : +20 si la ligne D est sous 20, sinon 0."""
    if cci_val is None:
        return 0, {'ok': False, 'valeur': None, 'points': 0}
    ok = cci_val < 20
    return (20 if ok else 0), {'ok': ok, 'valeur': round(cci_val, 2), 'points': 20 if ok else 0}


FOND_RULES = [
    ('dette_nette_ebitda', 'Dette nette / EBITDA', 'nd_ebitda', lambda v: v is not None and v < 2, '< 2'),
    ('marge_operationnelle', 'Marge opérationnelle', 'op_margin', lambda v: v is not None and v > 15, '> 15 %'),
    ('marge_fcf', 'Marge de cash-flow libre', 'fcf_margin', lambda v: v is not None and v > 10, '> 10 %'),
    ('roe', 'ROE', 'roe', lambda v: v is not None and v > 15, '> 15 %'),
    ('ratio_liquidite_courante', 'Ratio de liquidité courante', 'current', lambda v: v is not None and v > 1.2, '> 1,2'),
    ('bpa_annee_prochaine', 'BPA année prochaine', 'eps_1y', lambda v: v is not None and v > 10, '> 10 %'),
    ('bpa_cette_annee', 'BPA cette année', 'eps_0y', lambda v: v is not None and v > 10, '> 10 %'),
    ('ca_annee_prochaine', 'CA année prochaine', 'rev_1y', lambda v: v is not None and v > 5, '> 5 %'),
    ('ca_cette_annee', 'CA cette année', 'rev_0y', lambda v: v is not None and v > 5, '> 5 %'),
]


FOND_RULES_BANQUE = [
    ('roe', 'ROE', 'roe', lambda v: v is not None and v > 10, '> 10 %'),
    ('roa', 'ROA', 'roa', lambda v: v is not None and v > 1, '> 1 %'),
    ('ratio_cet1', 'Ratio CET1', 'ratio_cet1', lambda v: v is not None and v > 12, '> 12 %'),
    ('cout_du_risque', 'Coût du risque', 'cout_du_risque', lambda v: v is not None and v < 0.5, '< 0,5 %'),
    ('coefficient_exploitation', "Coefficient d'exploitation", 'coefficient_exploitation', lambda v: v is not None and v < 60, '< 60 %'),
    ('bpa_cette_annee', 'Croissance BPA année en cours', 'eps_0y', lambda v: v is not None and v > 10, '> 10 %'),
    ('bpa_annee_prochaine', 'Croissance BPA année prochaine', 'eps_1y', lambda v: v is not None and v > 10, '> 10 %'),
    ('pnb_cette_annee', 'Croissance PNB année en cours', 'rev_0y', lambda v: v is not None and v > 5, '> 5 %'),
    ('pnb_annee_prochaine', 'Croissance PNB année prochaine', 'rev_1y', lambda v: v is not None and v > 5, '> 5 %'),
]

# PNB : le consensus Yahoo « Revenue growth » (rev_0y / rev_1y) est la seule
# série d'estimations disponible. Pour les banques US, la ligne « Revenue »
# Yahoo correspond au total net revenue (intérêt + hors intérêt), proxy usuel
# du PNB. Ce n'est pas une ligne nominative « PNB ». On ne fabrique aucune
# autre valeur. CET1, coût du risque et coefficient d'exploitation sont absents
# des caches Yahoo / fondamentaux.json : 0 point, listés en manquantes.
PNB_SOURCE = (
    "Yahoo Finance, croissance du chiffre d'affaires / total net revenue "
    "(consensus analystes) — proxy du PNB, seule donnée disponible ; "
    "pas une ligne nominative « PNB »."
)
BANK_MISSING_SOURCES = {
    'ratio_cet1': (
        "Introuvable dans fondamentaux.json (clés m), dans les caches "
        "data/secteurs/fond et dans les statistiques / états financiers Yahoo "
        "précédemment inspectés (yfinance T.info et comptes JPM). Non inventé."
    ),
    'cout_du_risque': (
        "Introuvable dans fondamentaux.json, caches fond et états Yahoo "
        "(pas de ligne cost of risk / coût du risque). Non inventé."
    ),
    'coefficient_exploitation': (
        "Introuvable dans fondamentaux.json, caches fond et états Yahoo "
        "(pas de ligne efficiency ratio / coefficient d'exploitation). Non inventé."
    ),
}


def fond_points(m, rules=None):
    m = m or {}
    rules = rules or FOND_RULES
    elems, total = [], 0
    for eid, label, key, pred, seuil in rules:
        val = m.get(key)
        ok = bool(pred(val))
        pts = 10 if ok else 0
        total += pts
        rec = {
            'id': eid, 'label': label, 'cle': key, 'valeur': val,
            'seuil': seuil, 'ok': ok, 'points': pts, 'manquant': val is None,
        }
        if eid in ('pnb_cette_annee', 'pnb_annee_prochaine'):
            rec['source'] = PNB_SOURCE
        if val is None and eid in BANK_MISSING_SOURCES:
            rec['source'] = BANK_MISSING_SOURCES[eid]
        elems.append(rec)
    return total, elems


# APE-25 : échelle unique −50..250 (violet < 10, rouge 10–69, orange 70–129, vert 130–189, cyan ≥ 190)
PILOT_BANDS = [
    ('violet', -50, 10, '#9d54ff'),
    ('rouge', 10, 70, '#ff2d2d'),
    ('orange', 70, 130, '#ff8c1a'),
    ('vert', 130, 190, '#22c55e'),
    ('cyan', 190, 251, '#00e5ff'),
]


def band_of(total):
    t = float(total)
    if t >= 190:
        return 'cyan'
    if t >= 130:
        return 'vert'
    if t >= 70:
        return 'orange'
    if t >= 10:
        return 'rouge'
    return 'violet'


HEX = {name: hx for name, _lo, _hi, hx in PILOT_BANDS}


def compact_line(parts, total):
    bits = []
    for k, v in parts:
        if v is None:
            bits.append(f'{k} n.d.')
        else:
            sign = '+' if v > 0 else ''
            bits.append(f'{k} {sign}{v}')
    return ' · '.join(bits) + f'  →  {total} / {SCALE_MAX}'


def score_asset(asset, fg, elliott_key=None, fond_rules=None, closed_bars=None, allow_partial=False):
    path, used = (None, None)
    if not closed_bars:
        path, used = find_wk(yahoo_cands(asset.get('tv'), asset.get('yahoo'), asset.get('ticker')))
    out = {
        'id': asset.get('id') or asset.get('ticker'),
        'ticker': asset.get('ticker'),
        'tv': asset.get('tv'),
        'yahoo': asset.get('yahoo'),
        'nom': asset.get('nom') or asset.get('name'),
        'kind': asset.get('kind', 'action'),
        'weekly_path': path if path else (asset.get('weekly_path') or ('panier-reconstruit' if closed_bars else None)),
        'weekly_symbol_used': used or asset.get('weekly_symbol_used'),
        'industry': asset.get('industry'),
        'is_bank': bool(asset.get('is_bank')),
        'regles': asset.get('regles'),
    }
    if closed_bars:
        closed = [b for b in closed_bars if b.get('closed') and b.get('close') and b['close'] > 0]
        meta = {}
        all_bars = closed_bars
    elif not path:
        out['ok'] = False
        out['erreur'] = 'série hebdomadaire introuvable'
        return out
    else:
        closed, meta, all_bars = load_closed_weekly(path)
    if len(closed) < 52 and not allow_partial:
        out['ok'] = False
        out['erreur'] = f'historique insuffisant ({len(closed)} semaines clôturées)'
        out['n_closed'] = len(closed)
        return out
    if not closed:
        out['ok'] = False
        out['erreur'] = 'série hebdomadaire introuvable'
        out['n_closed'] = 0
        return out
    ds = [b['date'] for b in closed]
    c = [b['close'] for b in closed]
    o = [b.get('open') if b.get('open') and b['open'] > 0 else None for b in closed]
    last = closed[-1]
    r = K.rsi(c)
    rsi_val = r[-1]
    div = CH.divergence(c, ds, r) if rsi_val is not None else None
    rsi_pts, rsi_det = rsi_points(rsi_val, div)
    # MACD 12/26/9 : même seuil officiel de 52 semaines clôturées que le bloc technique.
    # En deçà, la ligne EMA n'est pas retenue (0, pas de chiffre inventé).
    if len(closed) < 52:
        m, sg, h = [None], [None], [None]
        macd_pts, macd_det = 0, {
            'ok': False, 'points': 0, 'insuffisant': True,
            'raison': f'historique insuffisant ({len(closed)} semaines clôturées, minimum 52)',
            'n_closed': len(closed), 'min_semaines': 52,
        }
    else:
        m, sg, h = K.macd_series(c)
        macd_pts, macd_det = macd_points(m[-1], h)
    fib = FB.analyse(o, c, ds, adjust_splits=True, sym=used, syms=[used, asset.get('tv'), asset.get('ticker')], combine=False)
    r_hist = fib.get('r') if fib.get('ok') else None
    # si combine=False, r est déjà le retracement historique
    fibo_pts, fibo_det = fibo_points(r_hist)
    if fib.get('ok'):
        fibo_det.update({
            'base': fib.get('base'), 'base_date': fib.get('base_date'),
            'ath': fib.get('ath'), 'ath_date': fib.get('ath_date'),
            'cours': fib.get('cours') or last['close'],
            'source': fib.get('source_historique'),
        })
    # Elliott retiré de la note APEX ACHAT (échelle −50 à 250, technique 110).
    # CCI Stochastic de Daveatt (pilotes Communication et banques USA), clôtures hebdo fermées.
    k_s, d_s, cci_raw = K.cci_stochastic_kd(c)
    cci_val = d_s[-1] if d_s else None
    cci_k = k_s[-1] if k_s else None
    cci_cci = cci_raw[-1] if cci_raw else None
    cci_pts, cci_det = cci_points(cci_val)
    cci_det.update({
        'k': None if cci_k is None else round(cci_k, 2),
        'd': None if cci_val is None else round(cci_val, 2),
        'cci': None if cci_cci is None else round(cci_cci, 2),
        'cci_period': K.CCI_STOCH_CCI_PERIOD,
        'stoch_period': K.CCI_STOCH_STOCH_PERIOD,
        'smooth_k': K.CCI_STOCH_SMOOTH_K,
        'smooth_d': K.CCI_STOCH_SMOOTH_D,
        'ligne': K.CCI_STOCH_LINE,
        'source': 'close hebdo clôturé',
    })

    fond_m = asset.get('m')
    # ETF et panier de section : on utilise la moyenne déjà calculée des 5 premières
    # actions. Un panier n'a pas de ratios d'émetteur ; le recalcul via fond_points
    # donnait Fond 0 (t454u).
    if asset.get('kind') in ('etf', 'panier') or 'fond_total' in asset:
        fond_total = asset.get('fond_total')
        fond_elems = asset.get('fond_elems')
        fond_mode = asset.get('fond_mode')
    else:
        fond_total, fond_elems = fond_points(fond_m, fond_rules)
        fond_mode = 'ratios de l’émetteur (Yahoo Finance, fondamentaux déjà en base)'

    sent_pl = None
    try:
        from apex import sentiment as S
        k, recs = S.of(tv=asset.get('tv'), key=S.key_for_section(asset.get('section'), asset.get('sous_section')))
        sent_pl = S.payload(k, recs)
    except Exception:
        sent_pl = None
    if sent_pl:
        fg_pts = sent_pl['points']
        fg_ok = True
        fg_lab = 'Sentiment ' + sent_pl['nom']
    else:
        fg_pts = 0
        fg_ok = False
        fg_lab = 'Sentiment'
    mm40_pts, mm40_det = mm40_hebdo_points(c, max_pts=MM40_HEBDO_MAX_AUTRES)
    if allow_partial and mm40_pts is None:
        mm40_pts = 0
        if isinstance(mm40_det, dict):
            mm40_det = dict(mm40_det, points=0, etat='insuffisant')
    total = rsi_pts + macd_pts + fibo_pts + cci_pts + int(round(fond_total or 0)) + (fg_pts or 0) + (mm40_pts or 0)
    band = band_of(total)
    parts = [
        ('RSI', rsi_pts), ('MACD', macd_pts), ('Fibo', fibo_pts),
        ('CCI', cci_pts),
        ('Fond', int(round(fond_total or 0))),
        (fg_lab, fg_pts if fg_ok else None),
        ('MM40 hebdo', mm40_pts),
    ]
    out.update({
        'ok': True,
        'date_cloture': last['date'],
        'close': last['close'],
        'n_closed': len(closed),
        'historique_partiel': bool(allow_partial and len(closed) < 52),
        'currency': (meta or {}).get('currency'),
        'points': {
            'rsi': rsi_pts, 'macd': macd_pts, 'fibonacci': fibo_pts,
            'cci': cci_pts,
            'fondamental': int(round(fond_total or 0)),
            'fear_greed': fg_pts if fg_ok else None,
            'mm40': mm40_pts,
            'total': total,
        },
        'detail': {
            'rsi': {'valeur': None if rsi_val is None else round(rsi_val, 1), 'points': rsi_pts, 'conditions': rsi_det},
            'macd': {'ligne': None if m[-1] is None else round(m[-1], 4),
                     'signal': None if sg[-1] is None else round(sg[-1], 4),
                     'hist': None if h[-1] is None else round(h[-1], 4),
                     'points': macd_pts, 'conditions': macd_det},
            'fibonacci': {**fibo_det, 'interpretation': (
                "Retracement r = (plus haut historique − cours) / (plus haut − plus bas historique), "
                "mesuré sur les corps hebdomadaires clôturés. « Sous X % » = r ≥ X % "
                "(le cours a retracé au-delà du niveau X % depuis le haut)."
            )},
            'cci': {**cci_det, 'seuil': 20, 'precision': 'CCI Stochastic Daveatt (CCI 28, stoch 28, lissages SMA 3 et 3, ligne D) ; +20 si < 20'},
            'fondamental': {'points': int(round(fond_total or 0)), 'max': 90, 'elements': fond_elems, 'mode': fond_mode},
            'mm40': mm40_det,
        },
        'ligne': compact_line(parts, total),
        'total': total,
        'total_max': SCALE_MAX,
        'total_min': SCALE_MIN,
        'display': f'{total} / {SCALE_MAX}',
        'band': band,
        'hex': HEX[band],
        'av_label': band_label(total),
        'sentiment': sent_pl,
    })
    return out


def band_label(total):
    b = band_of(total)
    return {'violet': 'Très faible', 'rouge': 'Faible', 'orange': 'Neutre', 'jaune': 'Neutre', 'vert': 'Favorable', 'cyan': 'Très favorable'}[b]


def load_elliott_key(tv, sector_obj=None):
    if sector_obj and sector_obj.get('tv') == tv:
        ell = sector_obj.get('elliott') or {}
        if ell.get('key'):
            return ell['key']
    bars = json.loads((ROOT / 'data' / 'apex_bars.json').read_text())
    rec = (bars.get('bars') or {}).get(tv) or {}
    ell = rec.get('elliott') or {}
    return ell.get('key')


def _pack_sector(sector_sym, etf_meta, fond_rules, section, fg, fond_all, secteurs, regles_id, fond_etf_intro):
    sec_fond = fond_all['sectors'][sector_sym]
    top_all = list(sec_fond['top'][:10])
    top5 = top_all[:5]
    sec = next(s for s in secteurs['sectors'] if s['sym'] == sector_sym)

    actions = []
    for r in top_all:
        actions.append({
            'id': r['ticker'], 'ticker': r['ticker'], 'yahoo': r.get('yahoo') or r['ticker'],
            'tv': r['tv'], 'nom': r['name'], 'name': r['name'], 'kind': 'action', 'm': r.get('m'),
            'industry': r.get('industry'),
        })

    action_fonds = []
    for a in actions[:5] or actions:
        tot, elems = fond_points(a['m'], fond_rules)
        a['_fond_tot'], a['_fond_elems'] = tot, elems
        action_fonds.append((tot, elems))
    n = len(action_fonds) or 1
    avg_total = sum(t for t, _ in action_fonds) / n
    etf_elems = []
    for i, rule in enumerate(fond_rules):
        eid, label, key, pred, seuil = rule
        vals = [el[i]['points'] for _, el in action_fonds]
        oks = [el[i]['ok'] for _, el in action_fonds]
        manqs = [el[i].get('manquant') for _, el in action_fonds]
        avg_pts = sum(vals) / n
        rec = {
            'id': eid, 'label': label, 'seuil': seuil,
            'points': round(avg_pts, 1),
            'ok': None,
            'moyenne_5': True,
            'n_bons': sum(1 for x in oks if x),
            'n_manquants': sum(1 for x in manqs if x),
            'n': n,
        }
        srcs = [el[i].get('source') for _, el in action_fonds if el[i].get('source')]
        if srcs:
            rec['source'] = srcs[0]
        etf_elems.append(rec)
    etf_fond_total = round(avg_total)
    names = ', '.join(a['ticker'] for a in actions)
    etf_asset = {
        **etf_meta, 'kind': 'etf',
        'fond_total': etf_fond_total,
        'fond_elems': etf_elems,
        'fond_mode': fond_etf_intro.format(names=names, n=n),
    }
    etf_score = score_asset(etf_asset, fg, elliott_key=load_elliott_key(etf_meta['tv'], sec), fond_rules=fond_rules)
    action_scores = [score_asset(a, fg, elliott_key=load_elliott_key(a['tv']), fond_rules=fond_rules) for a in actions]

    manquantes = []
    for rec in action_scores:
        if not rec.get('ok'):
            manquantes.append({
                'tv': rec.get('tv'), 'nom': rec.get('nom'),
                'critere': 'serie_hebdo', 'label': 'Série hebdomadaire',
                'raison': rec.get('erreur') or 'scoring incomplet',
            })
            continue
        for e in (rec.get('detail') or {}).get('fondamental', {}).get('elements') or []:
            if e.get('manquant'):
                manquantes.append({
                    'tv': rec.get('tv'), 'nom': rec.get('nom'), 'ticker': rec.get('ticker'),
                    'critere': e['id'], 'label': e['label'], 'seuil': e.get('seuil'),
                    'points': 0,
                    'source': e.get('source') or 'donnée absente des fondamentaux en base (Yahoo Finance)',
                })

    out = {
        'generated': NOW.strftime('%Y-%m-%d %H:%M') + ' Europe/Paris',
        'pilot': True,
        'section': section,
        'secteur_sym': sector_sym,
        'regles': regles_id,
        'etf_tv': etf_meta['tv'],
        'scale': {'min': SCALE_MIN, 'max': SCALE_MAX, 'tech_max': TECH_MAX, 'fond_max': FOND_MAX, 'fg_abs': FG_ABS,
                  'bandes': [
                      {'id': name, 'de': lo, 'a': hi, 'hex': hx}
                      for name, lo, hi, hx in PILOT_BANDS
                  ]},
        'fear_greed': fg,
        'etf': etf_score,
        'actions': action_scores,
        'by_tv': {},
        'manquantes': manquantes,
        'interpretations': {
            'fibo': "« Sous X % » = retracement depuis le plus haut historique r ≥ X %, corps hebdo clôturés (plus bas historique → plus haut historique).",
            'cci': "CCI Stochastic hebdo de Daveatt (script TradingView XZyG5SOx) : CCI 28 sur la clôture, stochastique 28 du CCI, lissages SMA 3 et 3, ligne D (0–100). +20 si sous 20.",
            'fg': "Tranches entières : floor(|50 − valeur| / 10) × 10, signé, max ±50. Même valeur CNN pour tous les titres du pilote.",
            'fond_etf': etf_asset['fond_mode'],
            'ligne_secteur': f"La ligne secteur affiche le total de l'ETF {etf_meta['ticker']} (représentant du secteur), pas une moyenne des 5 actions.",
            'bougies': "Uniquement les semaines dont le vendredi est passé (yahoo_week.friday_closed). La barre de la semaine en cours est ignorée.",
        },
    }
    for rec in [etf_score] + action_scores:
        if rec.get('tv'):
            out['by_tv'][rec['tv']] = rec
    return out


def main():
    fond_all = json.loads((ROOT / 'data' / 'fondamentaux.json').read_text())
    secteurs = json.loads((ROOT / 'data' / 'secteurs.json').read_text())

    fg = fetch_cnn_fng()
    if isinstance(fg, dict):
        fg.setdefault('role', 'repere_hors_note')
    print('F&G CNN (repère hors note)', fg.get('ok'), fg.get('value'), fg.get('date_valeur'), fg.get('erreur'))

    etf_xlc = {
        'id': 'etf', 'ticker': 'ZPDK', 'yahoo': 'ZPDK.DE', 'tv': 'XETR:ZPDK',
        'nom': 'SPDR S&P U.S. Communication Services Select Sector UCITS ETF',
    }
    etf_xlf = {
        'id': 'etf', 'ticker': 'ZPDF', 'yahoo': 'ZPDF.DE', 'tv': 'XETR:ZPDF',
        'nom': 'SPDR S&P U.S. Financials Select Sector UCITS ETF',
    }
    xlc = _pack_sector(
        'XLC', etf_xlc, FOND_RULES, 'Actions USA – Communication',
        fg, fond_all, secteurs, 'apex_achat_v2',
        "Moyenne des {n} actions « qualité / croissance » affichées dans le détail "
        "({names}). L'ETF n'a pas de ratios d'émetteur comparables ; on n'invente pas ces ratios.",
    )
    xlf = _pack_sector(
        'XLF', etf_xlf, FOND_RULES_BANQUE, 'Actions USA – Finance / banques',
        fg, fond_all, secteurs, 'apex_achat_v2_banque',
        "Moyenne des {n} actions « qualité / croissance » affichées dans le détail "
        "({names}). Fondamental bancaire (apex_achat_v2_banque) : 9 critères à +10. "
        "L'ETF n'a pas de ratios d'émetteur ; moyenne des 5, donnée manquante = 0, rien n'est inventé.",
    )

    out = dict(xlc)
    out['pilotes'] = {'XLC': xlc, 'XLF': xlf}
    out['secteurs_pilotes'] = ['XLC', 'XLF']
    out['by_tv'] = {}
    out['by_tv'].update(xlc.get('by_tv') or {})
    out['by_tv'].update(xlf.get('by_tv') or {})
    out['fear_greed'] = fg

    dest = ROOT / 'data' / 'apex_achat_v2_pilot.json'
    dest.write_text(json.dumps(out, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print('wrote', dest)

    def show(rec):
        print(f"{rec.get('tv')}  {rec.get('nom')}: {rec.get('display')}  {rec.get('ligne')}  clot={rec.get('date_cloture')} ok={rec.get('ok')}")
    print('--- XLC ---')
    show(xlc['etf'])
    for a in xlc['actions']:
        show(a)
    print('--- XLF ---')
    show(xlf['etf'])
    for a in xlf['actions']:
        show(a)
    print('manquantes XLF', len(xlf.get('manquantes') or []))
    ok = (
        xlc['etf'].get('ok') and all(a.get('ok') for a in xlc['actions'])
        and xlf['etf'].get('ok') and all(a.get('ok') for a in xlf['actions'])
        and fg.get('ok')
    )
    return 0 if ok else 2


if __name__ == '__main__':
    raise SystemExit(main())
