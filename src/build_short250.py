#!/usr/bin/env python3
"""APE-32 (t514u–t521u, validé par Emmanuel le 24/11/2026) : note SHORT sur 250, distincte de la note LONG.

Plus la note est haute, plus l'actif est un bon candidat short. Points entiers.
  RSI 14 hebdo (max 30)  : +10 si RSI > 70 ; +20 de plus s'il est resté > 70 plus de 3 semaines
                           (≥ 4 clôtures hebdo consécutives > 70, la dernière incluse). Cumulables.
  MACD 12/26/9 (max 30)  : +10 si la ligne MACD / cours × 100 > 4 % ; +20 de plus si, en plus, les 4 dernières barres
                           d'histogramme clôturées sont bleues (> 0) d'affilée. Cumulables.
  CCI Stoch. D (max 30)  : +10 si > 80 ; +20 de plus s'il est resté > 80 plus de 3 semaines (≥ 4 clôtures).
  Fondamental (max 81)   : lecture inversée du fondamental LONG : +9 par critère NON rempli ; critère sans
                           donnée = 4,5 (moitié) ; sous-total arrondi au point entier (demi vers le haut).
  Fear & Greed (±50)     : inverse du LONG (avidité 60 → +10 … 100 → +50 ; peur 40 → −10 … 0 → −50).
  Hype H (±29)           : H_short = round((attention − 50) × 0,58) (Indicateur d'Attention Long Swing).
  Fibonacci              : aucun point ; FILTRE d'entrée dans Meilleurs SHORT (note ≥ 70) : cours ≥ niveau 38,2 %
                           (retracement r ≤ 0,382 depuis l'ATH, corps hebdo ; ATH et au-delà autorisés).
Total borné −50..250. Catégories : Actions (hors banque), Actions bancaires, Énergie.
La note LONG n'est ni lue pour le calcul technique ni modifiée.
"""
from __future__ import annotations
import json, math, os, sys
from pathlib import Path

DIR = Path(__file__).resolve().parent
ROOT = Path(os.environ.get('APEX_ROOT') or DIR.parent)
sys.path[:0] = [str(DIR), str(ROOT)]
D = ROOT / 'data'

import ind_core as K  # noqa: E402
import fibo as FB  # noqa: E402
import build_apex_achat_v2_pilot as P  # noqa: E402

SEUIL = 70
MACD_PCT = 4.0  # ligne MACD / cours × 100 > 4 % (calibré : ~15 % des actifs aujourd'hui, ~20 % des semaines sur 5 ans)
try:
    SEUIL = int(json.loads((ROOT / 'config' / 'regles.json').read_text(encoding='utf-8'))['apex_short'].get('seuil', 70))
    MACD_PCT = float(json.loads((ROOT / 'config' / 'regles.json').read_text(encoding='utf-8'))['apex_short'].get('macd_pct', MACD_PCT))
except Exception:
    pass
MISE_BASE, MISE_PAS, MISE_MAX, PALIER = 100, 20, 200, 24
FIB_MAX_R = 0.382
H_COEF = 0.58
H_ABS = 29
USA_FR = ('NYSE', 'NASDAQ', 'AMEX', 'EURONEXT')


def jround(x):
    return int(math.floor(x + 0.5)) if x >= 0 else int(math.ceil(x - 0.5))


def streak(vals, pred):
    n = 0
    for v in reversed(vals):
        if v is not None and pred(v):
            n += 1
        else:
            break
    return n


def fg_short(value):
    if value is None:
        return None
    v = float(value)
    delta = v - 50.0
    n = min(5, int(math.floor(abs(delta) / 10.0)))
    return n * 10 if delta >= 0 else -n * 10


def h_short(att):
    if att is None:
        return None
    return max(-H_ABS, min(H_ABS, jround((float(att) - 50.0) * H_COEF)))


def mise(note):
    if note is None or note < SEUIL:
        return None
    return min(MISE_BASE + int((note - SEUIL) // PALIER) * MISE_PAS, MISE_MAX)


def weekly(tv, yahoo, ticker):
    path, used = P.find_wk(P.yahoo_cands(tv, yahoo, ticker))
    if not path:
        return None, None
    closed, _m, _a = P.load_closed_weekly(path)
    return closed, used


def tech(tv, yahoo, ticker):
    closed, used = weekly(tv, yahoo, ticker)
    if not closed or len(closed) < 52:
        return None
    c = [b['close'] for b in closed]
    o = [b.get('open') if b.get('open') and b['open'] > 0 else None for b in closed]
    ds = [b['date'] for b in closed]
    r = K.rsi(c)
    rs = streak(r, lambda v: v > 70)
    rsi_pts = (10 if rs >= 1 else 0) + (20 if rs >= 4 else 0)
    m, _sg, h = K.macd_series(c)
    m_pct = None if (m[-1] is None or not c[-1]) else m[-1] / c[-1] * 100
    m_ok = m_pct is not None and m_pct > MACD_PCT
    hb = streak(h, lambda v: v > 0)
    macd_pts = (10 if m_ok else 0) + (20 if (m_ok and hb >= 4) else 0)
    _k, d_s, _raw = K.cci_stochastic_kd(c)
    cs = streak(d_s or [], lambda v: v > 80)
    cci_pts = (10 if cs >= 1 else 0) + (20 if cs >= 4 else 0)
    fib = FB.analyse(o, c, ds, adjust_splits=True, sym=used, syms=[used, tv, ticker], combine=False)
    fr = fib.get('r') if fib.get('ok') else None
    niv = (fib.get('niveaux') or {}).get('38,2 %') if fib.get('ok') else None
    return {
        'date_cloture': ds[-1], 'close': c[-1], 'symbole': used,
        'rsi': {'valeur': None if r[-1] is None else round(r[-1], 1), 'semaines_sup_70': rs, 'points': rsi_pts},
        'macd': {'ligne': None if m[-1] is None else round(m[-1], 3), 'pct_cours': None if m_pct is None else round(m_pct, 2), 'seuil_pct': MACD_PCT, 'barres_bleues': hb, 'points': macd_pts},
        'cci': {'d': None if not d_s or d_s[-1] is None else round(d_s[-1], 1), 'semaines_sup_80': cs, 'points': cci_pts},
        'fibo': {'r': fr, 'niveau_382': None if niv is None else round(niv, 4), 'ath': fib.get('ath'),
                 'ok': (fr is not None and fr <= FIB_MAX_R)},
    }


def fond_from(elements, missing_key):
    """+9 par critère NON rempli ; critère sans donnée = moitié (4,5), sous-total arrondi au point (demi vers le haut)."""
    brut, n_ko, n_nc, det = 0.0, 0, 0, []
    for e in elements or []:
        nc = bool(e.get(missing_key)) or e.get('ok') is None
        ko = (not nc) and e.get('ok') is False
        pts = 9 if ko else (4.5 if nc else 0)
        brut += pts
        n_ko += ko
        n_nc += nc
        det.append({'id': e.get('id'), 'label': e.get('label'), 'ok_long': e.get('ok'), 'nc': nc, 'points': pts})
    return min(81, jround(brut)), n_ko, n_nc, det


def assemble(base, t, fond, fgv, att):
    fgp = fg_short(fgv)
    hp = h_short(att)
    fpts, n_ko, n_nc, fdet = fond
    tot = t['rsi']['points'] + t['macd']['points'] + t['cci']['points'] + fpts + (fgp or 0) + (hp or 0)
    note = max(-50, min(250, int(tot)))
    manq = []
    if att is None:
        manq.append('attention (H = 0)')
    if fgv is None:
        manq.append('Fear & Greed')
    if n_nc:
        manq.append(f'{n_nc} critère(s) fondamental n.c. (4,5 pts chacun)')
    if t['fibo']['r'] is None:
        manq.append('Fibonacci')
    entre = note >= SEUIL and t['fibo']['ok']
    ligne = (f"RSI +{t['rsi']['points']} · MACD +{t['macd']['points']} · CCI +{t['cci']['points']} · Fond +{fpts}"
             f" · F&G {fgp:+d} · H {(hp or 0):+d}  →  {note} / 250").replace('+-', '−').replace('-', '−')
    base.update({
        'note': note, 'scale': 250,
        'points': {'rsi': t['rsi']['points'], 'macd': t['macd']['points'], 'cci': t['cci']['points'],
                   'fondamental': fpts, 'fear_greed': fgp, 'hype': hp},
        'ligne': ligne, 'date_cloture': t['date_cloture'], 'close': t['close'],
        'tech': {k: t[k] for k in ('rsi', 'macd', 'cci')}, 'fibo': t['fibo'],
        'fond': {'criteres_non_remplis': n_ko, 'nc': n_nc, 'elements': fdet},
        'attention': att, 'manquants': manq,
        'fibo_ok': t['fibo']['ok'], 'au_seuil': note >= SEUIL, 'liste': entre,
        'mise': mise(note) if entre else None,
    })
    base['expo'] = None if base['mise'] is None else base['mise'] * 5
    return base


def main():
    pil = json.loads((D / 'apex_achat_v2_pilot.json').read_text(encoding='utf-8'))
    T = json.loads((D / 'tabs_data.json').read_text(encoding='utf-8'))
    atj = json.loads((D / 'attention_apex.json').read_text(encoding='utf-8')).get('by_tv') or {}
    fg = pil.get('fear_greed') or {}
    fgv = fg.get('value') if fg.get('ok') else None
    out, sans_serie = {}, []

    energie = [a for a in (T.get('energie') or {}).get('assets') or [] if a.get('kind') in ('equity', 'equity_proxy')]
    etv = {a['tv'] for a in energie}

    for tv, r in (pil.get('by_tv') or {}).items():
        if r.get('kind') != 'action' or r.get('ok') is False or tv in etv:
            continue
        if tv.split(':')[0] not in USA_FR:
            continue
        t = tech(tv, r.get('yahoo'), r.get('ticker'))
        if not t:
            sans_serie.append(tv)
            continue
        att = (r.get('attention') or {}).get('valeur')
        if att is None:
            att = (atj.get(tv) or {}).get('attention')
        cat = 'banque' if r.get('is_bank') else 'action'
        base = {'tv': tv, 'nom': r.get('nom'), 'ticker': r.get('ticker'), 'yahoo': r.get('yahoo'),
                'categorie': cat, 'tab': 'actions'}
        out[tv] = assemble(base, t, fond_from((r.get('fond') or {}).get('elements'), 'manquant'), fgv, att)

    for a in energie:
        tv = a['tv']
        t = tech(tv, a.get('yahoo'), (tv.split(':')[1] if ':' in tv else tv))
        if not t:
            sans_serie.append(tv)
            continue
        fel = (((a.get('apex10') or {}).get('decomp') or {}).get('fondamental') or {}).get('elements')
        att = (atj.get(tv) or {}).get('attention')
        base = {'tv': tv, 'nom': a.get('nom'), 'ticker': tv.split(':')[-1], 'yahoo': a.get('yahoo'),
                'categorie': 'energie', 'groupe': a.get('groupe'), 'tab': 'energie'}
        out[tv] = assemble(base, t, fond_from(fel, 'nc'), fgv, att)

    liste = sorted([x for x in out.values() if x['liste']], key=lambda x: (-x['note'], x['tv']))
    exclus_fibo = sorted([x for x in out.values() if x['au_seuil'] and not x['fibo_ok']], key=lambda x: (-x['note'], x['tv']))
    doc = {
        'regles': 'apex_short_250', 'seuil': SEUIL, 'fear_greed': {'value': fgv, 'points_short': fg_short(fgv), 'date': fg.get('date_valeur')},
        'n': len(out), 'n_liste': len(liste),
        'liste': [x['tv'] for x in liste],
        'exclus_fibo': [{'tv': x['tv'], 'note': x['note'], 'r': x['fibo']['r']} for x in exclus_fibo],
        'sans_serie': sans_serie,
        'by_tv': out,
    }
    (D / 'apex_short.json').write_text(json.dumps(doc, ensure_ascii=False, separators=(',', ':')) + '\n', encoding='utf-8')
    print('notes SHORT', len(out), 'liste', len(liste), 'exclus fibo', len(exclus_fibo), 'sans série', sans_serie)
    top = sorted(out.values(), key=lambda x: -x['note'])[:15]
    for x in top:
        print(f"{x['tv']:18} {x['categorie']:8} {x['note']:4} fibo_r={x['fibo']['r']} liste={x['liste']} mise={x['mise']}  {x['ligne']}")
    return 0


if __name__ == '__main__':
    sys.exit(main())
