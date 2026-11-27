#!/usr/bin/env python3
"""APE-32 (t514u–t521u, validé par Emmanuel le 24/11/2026) : note SHORT sur 250, distincte de la note LONG.

Plus la note est haute, plus l'actif est un bon candidat short. Points entiers.
  RSI 14 hebdo (max 25)  : +10 si RSI > 70 ; +15 de plus s'il est resté > 70 plus de 3 semaines
                           (≥ 4 clôtures hebdo consécutives > 70, la dernière incluse). Cumulables.
  MACD 12/26/9 (max 25)  : +10 si la ligne MACD / cours × 100 > 4 % ; +15 de plus si, en plus, les 4 dernières barres
                           d'histogramme clôturées sont bleues (> 0) d'affilée. Cumulables.
  CCI Stoch. D (max 25)  : +10 si > 80 ; +15 de plus s'il est resté > 80 plus de 3 semaines (≥ 4 clôtures).
  Fondamental (max 100)   : t686u (27/11/2026, tolérance) : base 10 + 10 par critère LONG NON rempli (9 critères) ;
                           critère sans donnée = moitié (5) ; une société saine garde 10, 9 non remplis = 100.
                           (avant : 125/9 ≈ 13,9 par critère non rempli, 0 pour une société saine.)
  Valorisation (max 30)  : t686u : PER (prévisionnel, repli courant) / médiane du PER de son secteur (S&P 500, Yahoo,
                           data/valo_short.json). 0 si ≤ 1× la médiane ; linéaire jusqu'à +30 à 2× ; plafonné.
                           PER absent ou négatif : n.c. = 0 point.
  Short interest (−20..+10) : t687u : à contre-courant, part du flottant vendue à découvert (Yahoo shortPercentOfFloat,
                           relevé bimensuel). +10 jusqu'à 2 % ; linéaire jusqu'à 0 à 5 % ; puis jusqu'à −20 à 15 % et au-delà.
                           Jours pour couvrir (shortRatio) ≥ 7 : −5 de plus (borné à −20). Donnée absente : n.c. = 0.
  Fear & Greed (±30)     : inverse du LONG, échelonné à 30 (avidité 60 → +6 … 100 → +30 ; peur 40 → −6 … 0 → −30).
                           valeur d'entrée = sentiment maison du SECTEUR de l'action (ETF SPDR US ou MSCI Europe,
                           data/sentiment_secteurs.json, apex/sentiment.py). Plus de repli CNN : si le secteur est inconnu, 0 point.
  Hype H (±20)           : H_short = round((attention − 50) × 0,4) (Indicateur d'Attention Long Swing).
  Filtre technique       : au moins signal_tech_min (1) bloc RSI / MACD / CCI à ≥ 10 points (surachat).
  Fibonacci              : aucun point ; FILTRE d'entrée dans Meilleurs SHORT (note ≥ 70) : cours ≥ niveau 38,2 %
                           (retracement r ≤ 0,382 depuis l'ATH, corps hebdo ; ATH et au-delà autorisés).
  MM40 hebdo (max 30)    : inversée par rapport au LONG. 0 point sous la MM40 semaines ; montée linéaire
                           de 0 à +30 entre 0 % et +40 % au-dessus ; plafonnée à +30 au-delà.
                           N'entre pas dans les filtres d'entrée (seuil, Fibonacci, signal de surachat).
Total borné −50..250 (t686u : + valorisation 0..30 ; le barème théorique dépasse 250, le total affiché est plafonné). Catégories : Actions (hors banque), Actions bancaires, Énergie.
La note LONG n'est ni lue pour le calcul technique ni modifiée.
"""
from __future__ import annotations
import json, math, os, sys, urllib.parse
from pathlib import Path

DIR = Path(__file__).resolve().parent
ROOT = Path(os.environ.get('APEX_ROOT') or DIR.parent)
sys.path[:0] = [str(DIR), str(ROOT)]
D = ROOT / 'data'

import ind_core as K  # noqa: E402
import fibo as FB  # noqa: E402
import build_apex_achat_v2_pilot as P  # noqa: E402
from apex.score import mm40_hebdo_points, mm40_hebdo_texte, MM40_HEBDO_MAX_AUTRES  # noqa: E402

SEUIL = 70
SEUIL_LISTE = 70  # orange, vert ou cyan (échelle APEX −50..250) : orange 70–129, vert 130–189, cyan ≥ 190
SIG_MIN = 1  # t528u : nb minimal de blocs RSI / MACD / CCI à ≥ 10 points (surachat) pour entrer dans la liste
N_LISTE_MAX = 10
MACD_PCT = 4.0  # ligne MACD / cours × 100 > 4 % (calibré : ~15 % des actifs aujourd'hui, ~20 % des semaines sur 5 ans)
try:
    _shcfg = json.loads((ROOT / 'config' / 'regles.json').read_text(encoding='utf-8'))['apex_short']
    SEUIL = int(_shcfg.get('seuil', 70))
    SEUIL_LISTE = int(_shcfg.get('seuil_liste', 70))
    SIG_MIN = int(_shcfg.get('signal_tech_min', SIG_MIN))
    MACD_PCT = float(_shcfg.get('macd_pct', MACD_PCT))
except Exception:
    pass
MISE_BASE, MISE_PAS, MISE_MAX, PALIER = 100, 20, 200, 24
FIB_MAX_R = 0.382
H_COEF = 0.4
H_ABS = 20
FOND_MAX = 125
FOND_BASE = 10   # t686u : plancher fondamental (une bonne santé n'écrase plus la note SHORT)
FOND_PAS = 10  # points par critère LONG non rempli (n.c. = moitié) : 10 + 9 × 10 = 100
VALO_MAX = 30    # t686u : valorisation excessive (PER / médiane du secteur)
VALO_R0, VALO_R1 = 1.0, 2.0  # 0 point à 1× la médiane, +30 à 2× et au-delà
try:
    _f = _shcfg.get('fond_tolerance') or {}
    FOND_BASE = int(_f.get('base', FOND_BASE)); FOND_PAS = int(_f.get('pas', FOND_PAS))
    _v = _shcfg.get('valorisation') or {}
    VALO_MAX = int(_v.get('max', VALO_MAX)); VALO_R0 = float(_v.get('ratio_0', VALO_R0)); VALO_R1 = float(_v.get('ratio_max', VALO_R1))
except Exception:
    pass
# t687u (27/11/2026) : short interest à contre-courant (éviter d'aller où tout le monde va).
SI_MAX = 10          # bonus max si peu shorté (asymétrique : la foule et le squeeze pèsent plus)
SI_MALUS = 20        # malus max si très shorté
SI_BAS, SI_ZERO, SI_HAUT = 2.0, 5.0, 15.0  # % du flottant : +10 ≤ 2 % → 0 à 5 % → −20 à 15 % et au-delà
SI_DTC_JOURS, SI_DTC_MALUS = 7.0, 5         # jours pour couvrir ≥ 7 : −5 de plus (risque de squeeze)
try:
    _si = _shcfg.get('short_interest') or {}
    SI_MAX = int(_si.get('bonus_max', SI_MAX)); SI_MALUS = int(_si.get('malus_max', SI_MALUS)); SI_BAS = float(_si.get('bas', SI_BAS)); SI_ZERO = float(_si.get('zero', SI_ZERO))
    SI_HAUT = float(_si.get('haut', SI_HAUT)); SI_DTC_JOURS = float(_si.get('dtc_jours', SI_DTC_JOURS)); SI_DTC_MALUS = int(_si.get('dtc_malus', SI_DTC_MALUS))
except Exception:
    pass
_VALO = None


def valo_doc():
    global _VALO
    if _VALO is None:
        try:
            _VALO = json.loads((ROOT / 'data' / 'valo_short.json').read_text(encoding='utf-8'))
        except Exception:
            _VALO = {}
    return _VALO


def _valo_rec(yahoo=None, ticker=None, tv=None):
    by = valo_doc().get('by_yahoo') or {}
    for k in (yahoo, ticker, (tv or '').split(':')[-1]):
        if k and (k in by or str(k).replace('.', '-') in by):
            return by.get(k) or by.get(str(k).replace('.', '-'))
    return None


def si_points_from(spf, dtc=None):
    """t687u : points short interest (−SI_MALUS..+SI_MAX) ; None si la part du flottant shortée manque."""
    if spf is None:
        return None
    x = float(spf)
    if x <= SI_BAS:
        pts = SI_MAX
    elif x <= SI_ZERO:
        pts = SI_MAX * (SI_ZERO - x) / (SI_ZERO - SI_BAS)
    elif x < SI_HAUT:
        pts = -SI_MALUS * (x - SI_ZERO) / (SI_HAUT - SI_ZERO)
    else:
        pts = -SI_MALUS
    pts = jround(pts)
    if dtc is not None and float(dtc) >= SI_DTC_JOURS:
        pts -= SI_DTC_MALUS
    return max(-SI_MALUS, min(SI_MAX, pts))


def si_points(yahoo=None, ticker=None, tv=None):
    rec = _valo_rec(yahoo, ticker, tv) or {}
    spf, dtc = rec.get('short_pct_float'), rec.get('short_ratio')
    pts = si_points_from(spf, dtc)
    if pts is None:
        return None, {'pct_flottant': None, 'texte': 'SI n.c.'}
    return pts, {'pct_flottant': spf, 'jours_couvrir': dtc, 'date': rec.get('date_short'), 'points': pts,
                 'texte': f"SI {pts:+d}"}


def valo_points(yahoo=None, ticker=None, tv=None):
    """t686u : (points 0..VALO_MAX ou None si n.c., détail). PER / médiane du PER du secteur."""
    V = valo_doc()
    by = V.get('by_yahoo') or {}
    rec = None
    for k in (yahoo, ticker, (tv or '').split(':')[-1]):
        if k and (k in by or str(k).replace('.', '-') in by):
            rec = by.get(k) or by.get(str(k).replace('.', '-'))
            break
    if not rec or not rec.get('per'):
        return None, {'per': None, 'texte': 'Valo n.c.'}
    med = ((V.get('secteurs') or {}).get(rec.get('sector') or '') or {}).get('mediane_per')
    if not med:
        return None, {'per': rec['per'], 'texte': 'Valo n.c.'}
    r = rec['per'] / med
    pts = 0 if r <= VALO_R0 else min(VALO_MAX, jround(VALO_MAX * (r - VALO_R0) / (VALO_R1 - VALO_R0)))
    return pts, {'per': rec['per'], 'per_source': rec.get('per_source'), 'secteur': rec.get('sector'),
                 'mediane_secteur': med, 'ratio': round(r, 2), 'points': pts, 'date': V.get('genere'),
                 'texte': f"Valo +{pts}"}
FG_TRANCHE = 6  # t524u : grille F&G échelonnée à ±30 (6 points par tranche de 10)
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
    return n * FG_TRANCHE if delta >= 0 else -n * FG_TRANCHE


YAHOO_GICS = {
    'Technology': 'Information Technology', 'Healthcare': 'Health Care', 'Financial Services': 'Financials',
    'Communication Services': 'Communication Services', 'Consumer Cyclical': 'Consumer Discretionary',
    'Consumer Defensive': 'Consumer Staples', 'Industrials': 'Industrials', 'Basic Materials': 'Materials',
    'Utilities': 'Utilities', 'Energy': 'Energy', 'Real Estate': 'Real Estate',
}
EU_COUNTRIES = ('France', 'Germany', 'Switzerland', 'Belgium', 'Netherlands', 'Italy', 'Spain', 'United Kingdom')


def sentiment_for(tv, sector=None, country=None, fgv_cnn=None):
    """Sentiment maison du secteur (0–100, libellé, clé). Plus de repli CNN (fgv_cnn ignoré)."""
    try:
        from apex import sentiment as S
    except Exception:
        return None, None, None
    key = None
    g = YAHOO_GICS.get(sector or '')
    if g:
        eu = (tv or '').split(':')[0] in ('EURONEXT', 'XETR', 'SIX')  # place de cotation (MTD, EG : NYSE → US)
        key = ('eu:' + S.GICS_EU[g]) if eu else ('us:' + S.GICS_US[g])
    if key is None:
        key = S.key_for_tv(tv)
    k, rec = S.resolve(key)
    if rec and rec.get('value') is not None:
        return float(rec['value']), S.court(k, rec), k
    return None, None, None


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
    return tech_from_closed(closed, used, tv, ticker)


def tech_from_closed(closed, used, tv, ticker=None):
    if not closed or len(closed) < 52:
        return None
    c = [b['close'] for b in closed]
    o = [b.get('open') if b.get('open') and b['open'] > 0 else None for b in closed]
    ds = [b['date'] for b in closed]
    r = K.rsi(c)
    rs = streak(r, lambda v: v > 70)
    rsi_pts = (10 if rs >= 1 else 0) + (15 if rs >= 4 else 0)
    m, _sg, h = K.macd_series(c)
    m_pct = None if (m[-1] is None or not c[-1]) else m[-1] / c[-1] * 100
    m_ok = m_pct is not None and m_pct > MACD_PCT
    hb = streak(h, lambda v: v > 0)
    macd_pts = (10 if m_ok else 0) + (15 if (m_ok and hb >= 4) else 0)
    _k, d_s, _raw = K.cci_stochastic_kd(c)
    cs = streak(d_s or [], lambda v: v > 80)
    cci_pts = (10 if cs >= 1 else 0) + (15 if cs >= 4 else 0)
    fib = FB.analyse(o, c, ds, adjust_splits=True, sym=used, syms=[x for x in (used, tv, ticker) if x], combine=False)
    fr = fib.get('r') if fib.get('ok') else None
    niv = (fib.get('niveaux') or {}).get('38,2 %') if fib.get('ok') else None
    mm40_pts, mm40_det = mm40_hebdo_points(c, max_pts=MM40_HEBDO_MAX_AUTRES, sens='short')
    return {
        'date_cloture': ds[-1], 'close': c[-1], 'symbole': used,
        'rsi': {'valeur': None if r[-1] is None else round(r[-1], 1), 'semaines_sup_70': rs, 'points': rsi_pts},
        'macd': {'ligne': None if m[-1] is None else round(m[-1], 3), 'pct_cours': None if m_pct is None else round(m_pct, 2), 'seuil_pct': MACD_PCT, 'barres_bleues': hb, 'points': macd_pts},
        'cci': {'d': None if not d_s or d_s[-1] is None else round(d_s[-1], 1), 'semaines_sup_80': cs, 'points': cci_pts},
        'fibo': {'r': fr, 'niveau_382': None if niv is None else round(niv, 4), 'ath': fib.get('ath'),
                 'ok': (fr is not None and fr <= FIB_MAX_R)},
        'mm40': mm40_det,
        'mm40_points': mm40_pts,
    }


def fond_from(elements, missing_key):
    """t686u : base FOND_BASE (10) + FOND_PAS (10) par critère NON rempli ; critère sans donnée = moitié (5) ;
    sous-total arrondi au point (demi vers le haut). Société saine = 10 ; 9 non remplis = 100.
    (t524u, avant : 125/9 ≈ 13,9 par critère non rempli, base 0.)"""
    brut, n_ko, n_nc, det = float(FOND_BASE), 0, 0, []
    for e in elements or []:
        nc = bool(e.get(missing_key)) or e.get('ok') is None
        ko = (not nc) and e.get('ok') is False
        pts = FOND_PAS if ko else ((FOND_PAS / 2) if nc else 0)
        brut += pts
        n_ko += ko
        n_nc += nc
        det.append({'id': e.get('id'), 'label': e.get('label'), 'ok_long': e.get('ok'), 'nc': nc, 'points': round(pts, 2)})
    return min(FOND_MAX, jround(brut)), n_ko, n_nc, det


def assemble(base, t, fond, fgv, att, sent=None):
    if sent and sent[0] is not None:
        fgv = sent[0]
    fgp = fg_short(fgv)
    flab = 'F&G' if not sent else f"Sentiment {sent[1]} {int(round(fgv))} :" if fgv is not None else 'F&G'
    hp = h_short(att)
    fpts, n_ko, n_nc, fdet = fond
    mm40_det = t.get('mm40') or {}
    mm40_pts = t.get('mm40_points')
    if mm40_pts is None and isinstance(mm40_det, dict) and isinstance(mm40_det.get('points'), int):
        mm40_pts = mm40_det['points']
    vpts, vdet = valo_points(base.get('yahoo'), base.get('ticker'), base.get('tv'))
    spts, sdet = si_points(base.get('yahoo'), base.get('ticker'), base.get('tv'))
    tot = t['rsi']['points'] + t['macd']['points'] + t['cci']['points'] + fpts + (fgp or 0) + (hp or 0) + (mm40_pts or 0) + (vpts or 0) + (spts or 0)
    note = max(-50, min(250, int(tot)))
    manq = []
    if att is None:
        manq.append('attention (H = 0)')
    if fgv is None:
        manq.append('Fear & Greed')
    if n_nc:
        manq.append(f'{n_nc} critère(s) fondamental n.c. ({FOND_PAS / 2:g} pts chacun)'.replace('.', ','))
    if vpts is None:
        manq.append('valorisation (PER n.c.)')
    if spts is None:
        manq.append('short interest n.c.')
    if t['fibo']['r'] is None:
        manq.append('Fibonacci')
    if mm40_pts is None:
        manq.append('MM40 hebdo (historique insuffisant)')
    n_sig = sum(1 for k in ('rsi', 'macd', 'cci') if t[k]['points'] >= 10)
    tech_ok = n_sig >= SIG_MIN
    entre = note >= SEUIL_LISTE and t['fibo']['ok'] and tech_ok
    mm40_txt = (mm40_det or {}).get('texte') or mm40_hebdo_texte((mm40_det or {}).get('ecart'), mm40_pts)
    ligne = (f"RSI +{t['rsi']['points']} · MACD +{t['macd']['points']} · CCI +{t['cci']['points']} · Fond +{fpts}"
             f" · {flab} {(fgp or 0):+d} · H {(hp or 0):+d} · {mm40_txt} · {vdet['texte']} · {sdet['texte']}"
             f"  →  {note} / 250").replace('+-', '−').replace('-', '−')
    base.update({
        'note': note, 'scale': 250,
        'points': {'rsi': t['rsi']['points'], 'macd': t['macd']['points'], 'cci': t['cci']['points'],
                   'fondamental': fpts, 'fear_greed': fgp, 'hype': hp, 'mm40': mm40_pts, 'valorisation': vpts, 'short_interest': spts},
        'valorisation': vdet, 'short_interest': sdet,
        'sentiment': (None if not sent else {'cle': sent[2], 'nom': sent[1], 'valeur': None if fgv is None else round(fgv, 1),
                                             'points': fgp, 'repli_cnn': sent[2] == 'cnn'}),
        'ligne': ligne, 'date_cloture': t['date_cloture'], 'close': t['close'],
        'tech': {k: t[k] for k in ('rsi', 'macd', 'cci')}, 'fibo': t['fibo'],
        'fond': {'criteres_non_remplis': n_ko, 'nc': n_nc, 'elements': fdet},
        'attention': att, 'manquants': manq,
        'mm40': mm40_det,
        'fibo_ok': t['fibo']['ok'], 'signaux_tech': n_sig, 'tech_ok': tech_ok, 'au_seuil': note >= SEUIL, 'liste': entre,
        'mise': mise(note) if note >= SEUIL else None,
    })
    base['expo'] = None if base['mise'] is None else base['mise'] * 5
    return base


def load_univers():
    """t534u : univers SHORT propre (config apex_short.univers, par défaut config/univers_short.json)."""
    try:
        rel = json.loads((ROOT / 'config' / 'regles.json').read_text(encoding='utf-8'))['apex_short'].get('univers_fichier')
    except Exception:
        rel = None
    if not rel:
        return None
    p = ROOT / rel
    if not p.exists():
        print('univers SHORT introuvable :', p)
        return None
    return json.loads(p.read_text(encoding='utf-8'))


def tech_univers(yahoo, tv):
    name = 'yahoo_1wk_' + urllib.parse.quote(yahoo, safe='') + '.json'
    path = ROOT / 'data' / 'short_cache' / name
    if not path.exists():
        alt = Path('/workspace/invest/ophir-site/data/short_cache') / name
        path = alt if alt.exists() else path
    if not path.exists():
        return None
    closed, _m, _a = P.load_closed_weekly(str(path))
    return tech_from_closed(closed, yahoo, tv)


def main_univers(U, fgv, fg):
    out, sans_serie = {}, []
    for a in U.get('actions') or []:
        tv = a['tv']
        t = tech_univers(a['yahoo'], tv)
        if not t:
            sans_serie.append(tv)
            continue
        bank = bool(a.get('is_bank'))
        _tot, elems = P.fond_points(a.get('metrics') or {}, P.FOND_RULES_BANQUE if bank else P.FOND_RULES)
        cat = 'banque' if bank else 'action'  # énergie : critères standard (pas de fiche énergie pour ces titres)
        base = {'tv': tv, 'nom': a.get('nom'), 'ticker': a.get('ticker'), 'yahoo': a.get('yahoo'),
                'categorie': cat, 'tab': 'short', 'univers': 'short',
                'rsi_hebdo': a.get('rsi'), 'palier': a.get('palier'), 'cfd_revolut': a.get('cfd_revolut'),
                'degradation': a.get('degradation'), 'pays': a.get('country'), 'canada': a.get('canada')}
        out[tv] = assemble(base, t, fond_from(elems, 'manquant'), fgv, None,
                           sentiment_for(tv, a.get('sector'), a.get('country'), fgv))
    return out, sans_serie


def main():
    pil = json.loads((D / 'apex_achat_v2_pilot.json').read_text(encoding='utf-8'))
    T = json.loads((D / 'tabs_data.json').read_text(encoding='utf-8'))
    atj = json.loads((D / 'attention_apex.json').read_text(encoding='utf-8')).get('by_tv') or {}
    fg = pil.get('fear_greed') or {}
    fgv = fg.get('value') if fg.get('ok') else None
    out, sans_serie = {}, []

    energie = [a for a in (T.get('energie') or {}).get('assets') or [] if a.get('kind') in ('equity', 'equity_proxy')]
    etv = {a['tv'] for a in energie}
    U = load_univers()
    if U:
        energie, pil_items = [], {}
    else:
        pil_items = pil.get('by_tv') or {}

    for tv, r in pil_items.items():
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
        out[tv] = assemble(base, t, fond_from((r.get('fond') or {}).get('elements'), 'manquant'), fgv, att,
                           sentiment_for(tv, None, None, fgv))

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
        out[tv] = assemble(base, t, fond_from(fel, 'nc'), fgv, att, sentiment_for(tv, None, None, fgv))

    if U:
        out, sans_serie = main_univers(U, fgv, fg)

    def _crypto_tv(tv):
        try:
            from build_univers_short import is_crypto
        except Exception:
            is_crypto = lambda s: str(s).upper().split(':')[-1] in {'XRP', 'BTC', 'ETH', 'DOGE', 'SOL'}
        tick = (tv or '').split(':')[-1]
        return is_crypto(tick) or is_crypto(tv)

    for x in out.values():
        if _crypto_tv(x.get('tv')):
            x['liste'] = False
    liste = sorted([x for x in out.values() if x['liste']], key=lambda x: (-x['note'], x['tv']))
    # Plafond 10 : si moins de 10 titres ≥ seuil (orange/vert/cyan), la liste en affiche moins ; pas de complément sous 70.
    if len(liste) > N_LISTE_MAX:
        for x in liste[N_LISTE_MAX:]:
            x['liste'] = False
        liste = liste[:N_LISTE_MAX]
    exclus_tech = sorted([x for x in out.values() if x['au_seuil'] and x['fibo_ok'] and not x['tech_ok']], key=lambda x: (-x['note'], x['tv']))
    exclus_fibo = sorted([x for x in out.values() if x['au_seuil'] and not x['fibo_ok']], key=lambda x: (-x['note'], x['tv']))
    doc = {
        'regles': 'apex_short_250', 'seuil': SEUIL, 'seuil_liste': SEUIL_LISTE,
        'fear_greed': {'value': fgv, 'points_short': fg_short(fgv), 'date': fg.get('date_valeur'),
                                                       'role': 'repère d\'information, hors note (sentiment maison par secteur)'},
        'n': len(out), 'n_liste': len(liste), 'n_liste_max': N_LISTE_MAX,
        'liste': [x['tv'] for x in liste],
        'exclus_fibo': [{'tv': x['tv'], 'note': x['note'], 'r': x['fibo']['r']} for x in exclus_fibo],
        'signal_tech_min': SIG_MIN,
        'exclus_tech': [{'tv': x['tv'], 'note': x['note']} for x in exclus_tech],
        'sans_serie': sans_serie,
        'univers': ({'fichier': 'config/univers_short.json', 'genere': U.get('genere'), 'stats': U.get('stats'), 'regle': U.get('regle')} if U else 'watchlist APEX'),
        'by_tv': out,
    }
    import score_held_shorts as HS  # noqa: WPS433
    held = HS.score_missing(doc.get('by_tv') or {}, fgv=fgv, fg=fg)
    if held:
        HS.inject(doc, held)
    HS.mark_held(doc)
    (D / 'apex_short.json').write_text(json.dumps(doc, ensure_ascii=False, separators=(',', ':')) + '\n', encoding='utf-8')
    print('notes SHORT', len(out), 'liste', len(liste), 'exclus fibo', len(exclus_fibo), 'sans série', sans_serie)
    top = sorted(out.values(), key=lambda x: -x['note'])[:15]
    for x in top:
        print(f"{x['tv']:18} {x['categorie']:8} {x['note']:4} fibo_r={x['fibo']['r']} liste={x['liste']} mise={x['mise']}  {x['ligne']}")
    return 0


if __name__ == '__main__':
    sys.exit(main())
