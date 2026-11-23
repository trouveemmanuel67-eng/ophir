#!/usr/bin/env python3
"""Pilote APEX ACHAT (accumulation de points) — UNIQUEMENT Actions USA Communication
(ZPDK + 5 actions qualité / croissance). Les autres sections ne sont pas recalculées.

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
from note_apex import divergence_haussiere

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
SCALE_MAX = 270  # sera aussi recalculé depuis les max des critères
TECH_MAX = 130
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


def fetch_cnn_fng():
    """Télécharge l'indice CNN officiel. Pas de valeur inventée : en cas d'échec, on le signale."""
    dest = ROOT / 'data' / 'apex_achat_v2_cnn_fng.json'
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
    quatre = streak >= 4
    if quatre:
        pts += 20
    det.append({'id': 'histo_4_barres_rouges_sous_0', 'ok': quatre, 'points': 20 if quatre else 0, 'streak': streak})
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
    entry = bool(key) and key in EZ.ZONE_VERTE
    return (20 if entry else 0), {'key': key, 'entry': entry, 'zone': 'verte' if entry else ('rouge' if key in EZ.ZONE_ROUGE else 'hors zone')}


def cci_points(cci_val):
    """Seuil littéral d'Emmanuel : CCI < 20 (en attente de confirmation).
    Ce n'est pas le seuil classique ±100.
    """
    if cci_val is None:
        return 0, {'ok': False, 'valeur': None, 'points': 0}
    ok = cci_val < 20
    return (20 if ok else 0), {'ok': ok, 'valeur': round(cci_val, 1), 'points': 20 if ok else 0}


FOND_RULES = [
    ('dette_nette_ebitda', 'Dette nette / EBITDA', 'nd_ebitda', lambda v: v is not None and v < 2, '< 2'),
    ('marge_operationnelle', 'Marge opérationnelle', 'op_margin', lambda v: v is not None and v > 15, '> 15 %'),
    ('marge_fcf', 'Marge de cash-flow libre', 'fcf_margin', lambda v: v is not None and v > 10, '> 10 %'),
    ('roe', 'ROE', 'roe', lambda v: v is not None and v > 15, '> 15 %'),
    ('ratio_liquidite_courante', 'Ratio de liquidité courante', 'current', lambda v: v is not None and v > 1.2, '> 1,2'),
    ('bpa_annee_prochaine', 'BPA année prochaine', 'eps_1y', lambda v: v is not None and v > 0, '> 0 %'),
    ('bpa_cette_annee', 'BPA cette année', 'eps_0y', lambda v: v is not None and v > 0, '> 0 %'),
    ('ca_annee_prochaine', 'CA année prochaine', 'rev_1y', lambda v: v is not None and v > 0, '> 0 %'),
    ('ca_cette_annee', 'CA cette année', 'rev_0y', lambda v: v is not None and v > 0, '> 0 %'),
]


def fond_points(m):
    m = m or {}
    elems, total = [], 0
    for eid, label, key, pred, seuil in FOND_RULES:
        val = m.get(key)
        ok = pred(val)
        pts = 10 if ok else 0
        total += pts
        elems.append({'id': eid, 'label': label, 'cle': key, 'valeur': val, 'seuil': seuil, 'ok': ok, 'points': pts})
    return total, elems


def band_of(total):
    # 5 tranches égales sur [-50, 270] (largeur 64)
    t = float(total)
    span = SCALE_MAX - SCALE_MIN
    w = span / 5.0
    if t < SCALE_MIN + w:
        return 'violet'
    if t < SCALE_MIN + 2 * w:
        return 'rouge'
    if t < SCALE_MIN + 3 * w:
        return 'jaune'
    if t < SCALE_MIN + 4 * w:
        return 'vert'
    return 'cyan'


HEX = {'violet': '#9d54ff', 'rouge': '#ff2d2d', 'jaune': '#ffd400', 'vert': '#22c55e', 'cyan': '#00e5ff'}


def compact_line(parts, total):
    bits = []
    for k, v in parts:
        if v is None:
            bits.append(f'{k} n.d.')
        else:
            sign = '+' if v > 0 else ''
            bits.append(f'{k} {sign}{v}')
    return ' · '.join(bits) + f'  →  {total} / {SCALE_MAX}'


def score_asset(asset, fg, elliott_key=None):
    path, used = find_wk(yahoo_cands(asset['tv'], asset.get('yahoo'), asset.get('ticker')))
    out = {
        'id': asset.get('id') or asset.get('ticker'),
        'ticker': asset.get('ticker'),
        'tv': asset['tv'],
        'yahoo': asset.get('yahoo'),
        'nom': asset.get('nom') or asset.get('name'),
        'kind': asset.get('kind', 'action'),
        'weekly_path': path,
        'weekly_symbol_used': used,
    }
    if not path:
        out['ok'] = False
        out['erreur'] = 'série hebdomadaire introuvable'
        return out
    closed, meta, all_bars = load_closed_weekly(path)
    if len(closed) < 52:
        out['ok'] = False
        out['erreur'] = f'historique insuffisant ({len(closed)} semaines clôturées)'
        out['n_closed'] = len(closed)
        return out
    ds = [b['date'] for b in closed]
    c = [b['close'] for b in closed]
    o = [b.get('open') if b.get('open') and b['open'] > 0 else None for b in closed]
    last = closed[-1]
    r = K.rsi(c)
    rsi_val = r[-1]
    div = CH.divergence(c, ds, r)
    rsi_pts, rsi_det = rsi_points(rsi_val, div)
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
    ell_pts, ell_det = elliott_points(elliott_key)
    cci_series = K.cci20(o, c)
    cci_val = cci_series[-1] if cci_series else None
    cci_pts, cci_det = cci_points(cci_val)

    fond_m = asset.get('m')
    if asset.get('kind') == 'etf':
        fond_total = asset.get('fond_total')
        fond_elems = asset.get('fond_elems')
        fond_mode = asset.get('fond_mode')
    else:
        fond_total, fond_elems = fond_points(fond_m)
        fond_mode = 'ratios de l’émetteur (Yahoo Finance, fondamentaux déjà en base)'

    fg_pts = fg['points'] if fg.get('ok') else 0
    total = rsi_pts + macd_pts + fibo_pts + ell_pts + cci_pts + int(round(fond_total or 0)) + (fg_pts or 0)
    band = band_of(total)
    parts = [
        ('RSI', rsi_pts), ('MACD', macd_pts), ('Fibo', fibo_pts),
        ('Elliott', ell_pts), ('CCI', cci_pts),
        ('Fond', int(round(fond_total or 0))),
        ('F&G', fg_pts if fg.get('ok') else None),
    ]
    out.update({
        'ok': True,
        'date_cloture': last['date'],
        'close': last['close'],
        'n_closed': len(closed),
        'currency': (meta or {}).get('currency'),
        'points': {
            'rsi': rsi_pts, 'macd': macd_pts, 'fibonacci': fibo_pts,
            'elliott': ell_pts, 'cci': cci_pts,
            'fondamental': int(round(fond_total or 0)),
            'fear_greed': fg_pts if fg.get('ok') else None,
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
            'elliott': ell_det,
            'cci': {**cci_det, 'seuil': 20, 'precision': 'seuil littéral d’Emmanuel, en attente de confirmation'},
            'fondamental': {'points': int(round(fond_total or 0)), 'max': 90, 'elements': fond_elems, 'mode': fond_mode},
        },
        'ligne': compact_line(parts, total),
        'total': total,
        'total_max': SCALE_MAX,
        'total_min': SCALE_MIN,
        'display': f'{total} / {SCALE_MAX}',
        'band': band,
        'hex': HEX[band],
        'av_label': band_label(total),
    })
    return out


def band_label(total):
    b = band_of(total)
    return {'violet': 'Très faible', 'rouge': 'Faible', 'jaune': 'Neutre', 'vert': 'Favorable', 'cyan': 'Très favorable'}[b]


def load_elliott_key(tv, sector_obj=None):
    if sector_obj and (sector_obj.get('tv') == tv or sector_obj.get('tick') == 'ZPDK'):
        ell = sector_obj.get('elliott') or {}
        if ell.get('key'):
            return ell['key']
    bars = json.loads((ROOT / 'data' / 'apex_bars.json').read_text())
    rec = (bars.get('bars') or {}).get(tv) or {}
    ell = rec.get('elliott') or {}
    return ell.get('key')


def main():
    fond_all = json.loads((ROOT / 'data' / 'fondamentaux.json').read_text())
    sec_fond = fond_all['sectors'][SECTOR_SYM]
    top5 = list(sec_fond['top'][:5])
    secteurs = json.loads((ROOT / 'data' / 'secteurs.json').read_text())
    comm = next(s for s in secteurs['sectors'] if s['sym'] == SECTOR_SYM)

    fg = fetch_cnn_fng()
    print('F&G', fg.get('ok'), fg.get('value'), fg.get('points'), fg.get('date_valeur'), fg.get('erreur'))

    actions = []
    for r in top5:
        actions.append({
            'id': r['ticker'], 'ticker': r['ticker'], 'yahoo': r.get('yahoo') or r['ticker'],
            'tv': r['tv'], 'nom': r['name'], 'name': r['name'], 'kind': 'action', 'm': r.get('m'),
        })

    # Fondamental ETF : moyenne des 5 actions affichées (l'ETF n'a pas de ratios d'émetteur comparables)
    action_fonds = []
    for a in actions:
        tot, elems = fond_points(a['m'])
        a['_fond_tot'], a['_fond_elems'] = tot, elems
        action_fonds.append((tot, elems))
    n = len(action_fonds) or 1
    avg_total = sum(t for t, _ in action_fonds) / n
    # moyenne par critère
    etf_elems = []
    for i, rule in enumerate(FOND_RULES):
        eid, label, key, pred, seuil = rule
        vals = [el[i]['points'] for _, el in action_fonds]
        oks = [el[i]['ok'] for _, el in action_fonds]
        avg_pts = sum(vals) / n
        etf_elems.append({
            'id': eid, 'label': label, 'seuil': seuil,
            'points': round(avg_pts, 1),
            'ok': None,
            'moyenne_5': True,
            'n_bons': sum(1 for x in oks if x),
            'n': n,
        })
    etf_fond_total = round(avg_total)  # entier pour le total affiché
    # réconcilier : somme des moyennes arrondies vs moyenne des totaux
    # on conserve la moyenne des totaux, arrondie à l'entier le plus proche

    etf_asset = {
        **ETF, 'kind': 'etf',
        'fond_total': etf_fond_total,
        'fond_elems': etf_elems,
        'fond_mode': (
            "Moyenne des 5 actions « qualité / croissance » affichées dans le détail "
            "(APP, RDDT, META, NFLX, GOOGL). L'ETF n'a pas de Dette nette/EBITDA, marges, "
            "ROE, ratio de liquidité ou consensus BPA/CA d'émetteur comparables ; on n'invente pas ces ratios."
        ),
    }

    etf_score = score_asset(etf_asset, fg, elliott_key=load_elliott_key(ETF['tv'], comm))
    action_scores = [score_asset(a, fg, elliott_key=load_elliott_key(a['tv'])) for a in actions]

    out = {
        'generated': NOW.strftime('%Y-%m-%d %H:%M') + ' Europe/Paris',
        'pilot': True,
        'section': 'Actions USA – Communication',
        'secteur_sym': SECTOR_SYM,
        'etf_tv': ETF['tv'],
        'scale': {'min': SCALE_MIN, 'max': SCALE_MAX, 'tech_max': TECH_MAX, 'fond_max': FOND_MAX, 'fg_abs': FG_ABS,
                  'bandes': [
                      {'id': 'violet', 'de': -50, 'a': 14, 'hex': HEX['violet']},
                      {'id': 'rouge', 'de': 14, 'a': 78, 'hex': HEX['rouge']},
                      {'id': 'jaune', 'de': 78, 'a': 142, 'hex': HEX['jaune']},
                      {'id': 'vert', 'de': 142, 'a': 206, 'hex': HEX['vert']},
                      {'id': 'cyan', 'de': 206, 'a': 270, 'hex': HEX['cyan']},
                  ]},
        'fear_greed': fg,
        'etf': etf_score,
        'actions': action_scores,
        'by_tv': {},
        'interpretations': {
            'fibo': "« Sous X % » = retracement depuis le plus haut historique r ≥ X %, corps hebdo clôturés (plus bas historique → plus haut historique).",
            'cci': "CCI 20 hebdo < 20 (seuil littéral d'Emmanuel, en attente de confirmation) ; ce n'est pas ±100.",
            'fg': "Tranches entières : floor(|50 − valeur| / 10) × 10, signé, max ±50. Même valeur CNN pour tous les titres du pilote.",
            'fond_etf': etf_asset['fond_mode'],
            'ligne_secteur': "La ligne secteur affiche le total de l'ETF ZPDK (représentant du secteur), pas une moyenne des 5 actions.",
            'bougies': "Uniquement les semaines dont le vendredi est passé (yahoo_week.friday_closed). La barre de la semaine en cours est ignorée.",
        },
    }
    for rec in [etf_score] + action_scores:
        if rec.get('tv'):
            out['by_tv'][rec['tv']] = rec

    dest = ROOT / 'data' / 'apex_achat_v2_pilot.json'
    dest.write_text(json.dumps(out, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print('wrote', dest)
    def show(rec):
        pts = rec.get('points') or {}
        print(f"{rec.get('tv')}  {rec.get('nom')}: {rec.get('display')}  {rec.get('ligne')}  clot={rec.get('date_cloture')}")
    show(etf_score)
    for a in action_scores:
        show(a)
    return 0 if etf_score.get('ok') and all(a.get('ok') for a in action_scores) and fg.get('ok') else 2


if __name__ == '__main__':
    raise SystemExit(main())
