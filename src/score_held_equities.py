#!/usr/bin/env python3
"""Note APEX Actions (−50..250) pour les actions détenues absentes de l'univers noté.

Cause typique : le titre est classé hors des tops 10 ETF de secteur / paniers pays
(ex. ENPH sur l'onglet Énergie), donc jamais écrit dans by_tv ; Mes positions ne
montre un badge /250 que via PILOT.by_tv.

La note suit la grille Actions en vigueur (blocs techniques et fondamental ×0,9,
Hype H à contre-courant, F&G de secteur, pas d'Elliott). Donnée manquante = 0
ou H « – », jamais inventée.

Appelé par build_apex_achat_v2_world.py (après apply_doc) et par
harmonise250.inject_special, pour que la note reste recalculée comme les autres.
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

DIR = Path(__file__).resolve().parent
ROOT = DIR.parent
sys.path[:0] = [str(DIR), str(ROOT)]

import build_apex_achat_v2_pilot as P  # noqa: E402
import apply_attention as AA  # noqa: E402
import apply_sentiment as AS  # noqa: E402
import attention_apex as ATT  # noqa: E402
import yahoo_week as YW  # noqa: E402

# Déjà traités à part (tête CAC 40, Fanuc Tokyo) : ne pas les re-noter ici.
SKIP_TV = frozenset({'EURONEXT:CAC', 'TSE:6954', 'XETR:FUC'})
CACHE = ROOT / 'data' / 'fond250' / 'held_yahoo'


def _pos_files():
    for name in ('positions.json', 'positions_revolut.json', 'positions_revolutx.json'):
        p = ROOT / 'data' / name
        if p.exists():
            yield p


SKIP_TABS_CFD = frozenset({'metaux', 'liquidites', 'obligations', 'crypto'})


def iter_held_equities():
    """Actions détenues (equity ou CFD long sur action), clés TradingView de fiche."""
    seen = set()
    for path in _pos_files():
        doc = json.loads(path.read_text(encoding='utf-8'))
        for p in doc.get('positions') or []:
            typ = (p.get('type') or '').lower()
            tab = (p.get('tab') or '').lower()
            if typ in ('cash', 'rsu', 'etf', 'metal'):
                continue
            if typ == 'cfd':
                if (p.get('sens') or '').lower() == 'short':
                    continue
                if tab in SKIP_TABS_CFD:
                    continue
            elif typ and typ != 'equity':
                continue
            elif typ != 'equity' and p.get('tab') not in ('actions', 'pays'):
                continue
            tvs = [p.get('fiche_tv'), p.get('tv_note'), p.get('tv')]
            tvs = [t for t in tvs if t and t != 'pas de note']
            if not tvs:
                continue
            key = tvs[0]
            if key in seen or key in SKIP_TV:
                continue
            seen.add(key)
            ticker = p.get('sous_jacent') or p.get('ticker') or (key.split(':')[-1] if ':' in key else key)
            yahoo = ticker
            if key.startswith('NASDAQ:') or key.startswith('NYSE:') or key.startswith('AMEX:'):
                yahoo = key.split(':', 1)[1]
            yield {
                'tv': key,
                'aliases': [t for t in tvs if t != key],
                'ticker': yahoo,
                'yahoo': yahoo,
                'nom': p.get('fiche_nom') or (p.get('nom') or ticker).replace(' CFD', '').strip(),
                'kind': 'action',
                'tab': p.get('tab'),
                'source': path.name,
            }


def missing_held(by_tv):
    by_tv = by_tv or {}
    out = []
    for a in iter_held_equities():
        keys = [a['tv']] + list(a.get('aliases') or [])
        if any(k in by_tv and (by_tv[k] or {}).get('ok') and (by_tv[k] or {}).get('total') is not None
               for k in keys):
            continue
        if a['tv'] in SKIP_TV:
            continue
        out.append(a)
    return out


def volume_from_closed(closed):
    """Volume relatif 4 s. / 52 s. (variante A), semaines déjà clôturées uniquement."""
    vols = [float(b['volume']) for b in closed if b.get('volume') and b['volume'] > 0]
    if len(vols) < 30:
        return None
    import pandas as pd
    s = pd.Series(vols)
    if len(s) >= 52:
        base = float(s.iloc[-52:].mean())
    else:
        base = float(s.mean())
    if not base:
        return None
    r = float(s.iloc[-4:].mean() / base)
    score = round(ATT.clip(50 + 50 * math.log2(r)), 1)
    return {'ratio': round(r, 3), 'score': score, 'series': [float(x) for x in s.iloc[-64:]]}


def attention_for(asset, closed):
    """Attention Long Swing 0–100, sources réelles ; H via la grille Actions 0,54."""
    att_doc = AA.load_attention()
    by_tv = att_doc.get('by_tv') or {}
    by_key = att_doc.get('by_key') or {}
    for cand in [asset.get('tv'), *(asset.get('aliases') or []), asset.get('yahoo'), asset.get('ticker')]:
        if not cand:
            continue
        raw = by_tv.get(cand) or by_key.get(str(cand).upper())
        if raw and raw.get('attention') is not None:
            att_val = raw['attention']
            return att_val, AA.att_compact(raw), raw
    ticker = asset.get('ticker') or ''
    nom = asset.get('nom') or ticker
    # Terme US : court si connu, sinon « <nom> stock ». ENPH → Enphase stock (cache W48).
    if ticker == 'ENPH':
        term, geo, ape = 'Enphase stock', '', 'ENPH'
    else:
        term, geo, ape = (ATT.US_TERM.get(ticker, nom) + ' stock'), '', ticker
    tr_vals, tr_st = ATT.trends_fetch(term, geo, deadline=__import__('time').time() + 90, tries=2)
    tr = ATT.trends_score(tr_vals)
    ape_doc, ape_st = ATT.apewisdom_today()
    me = ATT.mentions_score(ape, ape_doc)
    vo = volume_from_closed(closed)
    pe = ATT.persist_score(vo and vo.get('series'), tr_vals if tr else None)
    sc = {
        'trends': None if not tr else tr['score'],
        'mentions': None if not me else me['score'],
        'volume': None if not vo else vo['score'],
        'persist': pe,
    }
    avail = {k: v for k, v in sc.items() if v is not None}
    wa = sum(ATT.W[k] for k in avail)
    att = round(sum(ATT.W[k] * v for k, v in avail.items()) / wa, 1) if wa else None
    raw = {
        'ticker': ticker, 'yahoo': asset.get('yahoo'), 'nom': nom, 'pays': 'USA',
        'attention': att, 'H': None if att is None else AA.h_points(att),
        'poids_dispo': round(wa, 2) if wa else 0,
        'composantes': sc,
        'trends': {'terme': term, 'geo': geo or 'monde', 'statut': tr_st, **(tr or {})},
        'mentions': {'ticker': ape, 'apewisdom': ape_st, **(me or {})},
        'volume': {'ratio_4s_52s': None if not vo else vo['ratio']},
        'manquants': [k for k, v in sc.items() if v is None] + ['X', 'StockTwits'],
    }
    return att, AA.att_compact(raw), raw


def _num(v):
    if v is None:
        return None
    try:
        x = float(v)
    except (TypeError, ValueError):
        return None
    if x != x or x in (float('inf'), float('-inf')):
        return None
    return x


def metrics_from_yahoo(yahoo, ticker=None):
    """Ratios Actions (même formules que build_fondamentaux / qsget), Yahoo live."""
    import yfinance as yf
    sym = yahoo or ticker
    T = yf.Ticker(sym)
    info = T.info or {}

    def pc(x):
        x = _num(x)
        return None if x is None else x * 100

    debt, cash, eb = _num(info.get('totalDebt')), _num(info.get('totalCash')), _num(info.get('ebitda'))
    rev, fcf = _num(info.get('totalRevenue')), _num(info.get('freeCashflow'))
    nd = ((debt or 0) - (cash or 0)) / eb if eb and eb > 0 and debt is not None else None

    def growth_eps(per):
        try:
            ee = T.earnings_estimate
            if ee is None or per not in ee.index:
                return None
            row = ee.loc[per]
            gr, base = _num(row.get('growth')), _num(row.get('yearAgoEps'))
            return None if gr is None or base is None or base <= 0 else gr * 100
        except Exception:
            return None

    def growth_rev(per):
        try:
            re_ = T.revenue_estimate
            if re_ is None or per not in re_.index:
                return None
            gr = _num(re_.loc[per].get('growth'))
            return None if gr is None else gr * 100
        except Exception:
            return None

    m = {
        'nd_ebitda': None if nd is None else round(nd, 2),
        'op_margin': None if pc(info.get('operatingMargins')) is None else round(pc(info.get('operatingMargins')), 2),
        'fcf_margin': None if (fcf is None or not rev) else round(fcf / rev * 100, 2),
        'roe': None if pc(info.get('returnOnEquity')) is None else round(pc(info.get('returnOnEquity')), 2),
        'current': None if _num(info.get('currentRatio')) is None else round(_num(info.get('currentRatio')), 3),
        'eps_0y': growth_eps('0y'),
        'eps_1y': growth_eps('+1y'),
        'rev_0y': growth_rev('0y'),
        'rev_1y': growth_rev('+1y'),
    }
    # Marge opérationnelle > 100 % : artefact Yahoo, traitée comme donnée manquante (pas inventée).
    if m.get('op_margin') is not None and m['op_margin'] > 100:
        m['op_margin'] = None
    if m['eps_0y'] is not None:
        m['eps_0y'] = round(m['eps_0y'], 2)
    if m['eps_1y'] is not None:
        m['eps_1y'] = round(m['eps_1y'], 2)
    if m['rev_0y'] is not None:
        m['rev_0y'] = round(m['rev_0y'], 2)
    if m['rev_1y'] is not None:
        m['rev_1y'] = round(m['rev_1y'], 2)
    meta = {
        'm': m,
        'industry': info.get('industry'),
        'sector': info.get('sector'),
        'source': 'Yahoo Finance key-statistics + earnings/revenue estimate',
        'url': f'https://finance.yahoo.com/quote/{sym}/key-statistics/',
        'retrieved': P.NOW.strftime('%Y-%m-%d %H:%M') + ' Europe/Paris',
        'yahoo': sym,
    }
    CACHE.mkdir(parents=True, exist_ok=True)
    (CACHE / f'{sym}.json').write_text(json.dumps(meta, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    return meta


def load_closed(asset):
    path, used = P.find_wk(P.yahoo_cands(asset.get('tv'), asset.get('yahoo'), asset.get('ticker')))
    if not path:
        return None, None, None
    closed, meta, all_bars = P.load_closed_weekly(path)
    return path, used, closed


def score_asset_held(asset, fg=None):
    """Note complète d'une action détenue : score_asset + H + sentiment de secteur."""
    path, used, closed = load_closed(asset)
    if not closed or len([b for b in closed if b.get('closed') and b.get('close') and b['close'] > 0]) < 52:
        return {'tv': asset.get('tv'), 'ok': False, 'erreur': 'série hebdomadaire introuvable ou trop courte'}
    meta = metrics_from_yahoo(asset.get('yahoo'), asset.get('ticker'))
    asset = dict(asset)
    asset['m'] = meta['m']
    asset['industry'] = meta.get('industry') or asset.get('industry')
    asset['kind'] = 'action'
    asset['regles'] = 'apex_achat_v2'
    if fg is None:
        fg = P.fetch_cnn_fng()
    rec = P.score_asset(asset, fg, fond_rules=P.FOND_RULES, closed_bars=closed)
    if not rec.get('ok'):
        return rec
    att_val, att, raw = attention_for(asset, closed)
    h = None if att_val is None else AA.h_points(att_val)
    AA.apply_rec(rec, h, att)
    rec['hors_univers_position'] = (
        f"{asset.get('ticker')} · action détenue hors univers Actions "
        f"(onglet {asset.get('tab') or 'n.c.'}, absente des tops secteur / pays)"
    )
    rec['fond_source'] = f"{meta['source']} relevé {meta['retrieved']}"
    rec['weekly_path'] = path
    rec['weekly_symbol_used'] = used
    rec['attention_raw'] = {k: raw[k] for k in ('trends', 'mentions', 'volume', 'manquants', 'poids_dispo') if k in raw}
    from apex import sentiment as SENT
    tv = rec.get('tv') or asset.get('tv')
    skey = SENT.key_for_tv(tv)
    if not skey and meta.get('sector'):
        gics = {
            'Technology': 'Information Technology', 'Healthcare': 'Health Care',
            'Financial Services': 'Financials', 'Communication Services': 'Communication Services',
            'Consumer Cyclical': 'Consumer Discretionary', 'Consumer Defensive': 'Consumer Staples',
            'Industrials': 'Industrials', 'Basic Materials': 'Materials',
            'Utilities': 'Utilities', 'Energy': 'Energy', 'Real Estate': 'Real Estate',
        }.get(meta['sector'])
        if gics and gics in SENT.GICS_US:
            skey = 'us:' + SENT.GICS_US[gics]
    # Si le CNN n'a pas été fourni, F&G est n.d. : on pose 0 pour que le sentiment maison puisse le remplacer.
    pts = rec.get('points')
    if isinstance(pts, dict) and pts.get('fear_greed') is None:
        pts['fear_greed'] = 0
    if isinstance(rec.get('ligne'), str):
        rec['ligne'] = rec['ligne'].replace('F&G n.d.', 'F&G +0')
    AS.patch(rec, skey, 'held')
    return rec


def score_missing(by_tv, fg=None):
    """Retourne {tv: rec} pour chaque action détenue encore absente de by_tv."""
    out = {}
    for a in missing_held(by_tv):
        rec = score_asset_held(a, fg=fg)
        if rec.get('tv'):
            out[rec['tv']] = rec
            print('held', rec.get('tv'), rec.get('display') or rec.get('erreur'), flush=True)
        for al in a.get('aliases') or []:
            if rec.get('ok') and al not in out and al not in (by_tv or {}):
                out[al] = rec
    return out


def compact_held(rec):
    from build_apex_achat_v2_world import compact_rec
    out = compact_rec(rec)
    for k in ('sentiment', 'hors_univers_position', 'fond_source', 'points_brut', 'date_cloture', 'close'):
        if rec.get(k) is not None and k not in out:
            out[k] = rec[k]
    # fond déjà posé par compact_rec depuis detail ; après apply_rec il est aussi dans rec['fond']
    if 'fond' not in out and isinstance(rec.get('fond'), dict):
        out['fond'] = rec['fond']
    if not isinstance(out.get('decomp'), dict):
        mm40_det = (rec.get('detail') or {}).get('mm40') or (rec.get('decomp') or {}).get('mm40')
        if mm40_det is not None or isinstance(rec.get('points'), dict):
            out['decomp'] = {
                'points': dict(rec.get('points') or {}),
                **({'mm40': mm40_det} if mm40_det is not None else {}),
            }
    return out


def inject(docs, held):
    """Fusionne les notes held dans les documents pilote / scores_full (by_tv seulement)."""
    if not held:
        return
    for doc in docs:
        if not isinstance(doc, dict):
            continue
        doc.setdefault('by_tv', {}).update({k: compact_held(v) if 'detail' in (v or {}) else v
                                            for k, v in held.items()})


def main():
    pil = json.loads((ROOT / 'data' / 'apex_achat_v2_pilot.json').read_text(encoding='utf-8'))
    held = score_missing(pil.get('by_tv') or {})
    if not held:
        print('held: rien à ajouter')
        return 0
    names = ('apex_achat_v2_pilot.json', 'apex_achat_v2_scores_full.json')
    docs = []
    for name in names:
        p = ROOT / 'data' / name
        if not p.exists():
            continue
        doc = json.loads(p.read_text(encoding='utf-8'))
        inject([doc], held)
        p.write_text(json.dumps(doc, ensure_ascii=False) + '\n', encoding='utf-8')
        print('wrote', p, 'held', list(held))
        docs.append(doc)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
