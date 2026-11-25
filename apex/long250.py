"""APE-25 (t503u) : note APEX unique −50..250 pour les classes hors actions.

Obligations, énergie (actions, proxies, ETF), devises, épargne / monétaire, immobilier, ETC métaux
(Qualité ETC), ETF par devise (fondamental 30). Grille : /workspace/invest/grille_apex_250_2026-11-24.md.
Données : data/fond250/*.json|csv (justETF, Yahoo Finance, FRED, Banque mondiale, BRI, sources manuelles
datées). Donnée absente = n.c. = 0 point, sans redistribution, listée dans 'nc'.
"""
from __future__ import annotations

import csv
import datetime as dt
import io
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for p in (ROOT, ROOT / 'src'):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

import ind_core as K  # noqa: E402
import charte as CH  # noqa: E402
import fibo as FB  # noqa: E402
from build_apex_achat_v2_pilot import rsi_points, macd_points, fibo_points, cci_points, load_closed_weekly  # noqa: E402
from .score import load_cnn_fg, metaux_band, fmt10, fg_points, mm40_hebdo_points, mm40_hebdo_texte, MM40_HEBDO_MAX_AUTRES  # noqa: E402
from .weekly_closes import weekly_closes  # noqa: E402
from .metaux_points import yahoo_cands_metaux, find_wk_metaux  # noqa: E402

F = ROOT / 'data' / 'fond250'
TODAY = dt.date.today()
MIN, MAX = -50, 250
HEADS = {'IE00B14X4S71': 'XETR:IUSU', 'IE00BSKRJZ44': 'XETR:IS04', 'IE00B4WXJJ64': 'XETR:EUNH', 'IE00B7LGZ558': 'EURONEXT:IFRB',
         'IE0032895942': 'XETR:IBCD', 'IE00B3F81R35': 'XETR:EUN5', 'IE00BDR5HM97': 'XETR:XUHY', 'LU1452600270': 'XETR:TIUP',
         'IE00B2NPKV68': 'XETR:IUS7', 'IE00B5V94313': 'XETR:IS0L'}
ENERGIE_ETF = {'IE000NDWFGA5': 'XETR:URNU', 'IE0005YK6564': 'XETR:U3O8', 'IE00BM67HM91': 'XETR:XDW0', 'IE00BWBXMB69': 'XETR:ZPDU'}


# ---------------------------------------------------------------- données
def _j(name):
    p = F / name
    return json.loads(p.read_text()) if p.exists() else {}


JE = _j('justetf.json')
YF = _j('yahoo.json')
WB = _j('worldbank.json')
BIS = _j('bis.json')
MAN = _j('manuel.json')
_FRED = {}


def fred(sid):
    """Série FRED [(date, valeur)] triée, valeurs manquantes retirées."""
    if sid in _FRED:
        return _FRED[sid]
    p = F / 'fred' / f'{sid}.csv'
    out = []
    if p.exists():
        for row in list(csv.reader(io.StringIO(p.read_text())))[1:]:
            if len(row) >= 2 and row[1] not in ('', '.'):
                try:
                    out.append((row[0], float(row[1])))
                except ValueError:
                    pass
    _FRED[sid] = out
    return out


def last(sid):
    s = fred(sid)
    return s[-1] if s else (None, None)


def ago(sid, months):
    """Valeur à (dernière date − n mois), observation la plus proche antérieure."""
    s = fred(sid)
    if not s:
        return (None, None)
    d = dt.date.fromisoformat(s[-1][0])
    y, m = d.year, d.month - months
    while m <= 0:
        m += 12; y -= 1
    tgt = dt.date(y, m, min(d.day, 28)).isoformat()
    prev = [x for x in s if x[0] <= tgt]
    return prev[-1] if prev else (None, None)


def yoy(sid):
    d, v = last(sid)
    d0, v0 = ago(sid, 12)
    if v is None or v0 in (None, 0):
        return None, d
    return round((v / v0 - 1) * 100, 2), d


def median_years(sid, years=10):
    s = fred(sid)
    if not s:
        return None
    d = dt.date.fromisoformat(s[-1][0])
    lo = dt.date(d.year - years, d.month, min(d.day, 28)).isoformat()
    v = sorted(x[1] for x in s if x[0] >= lo)
    return v[len(v) // 2] if v else None


def fred_src(*sids):
    return 'FRED (St. Louis Fed) : ' + ', '.join(f'{s} au {last(s)[0]}' for s in sids)


def bis_rate(c):
    s = ((BIS.get('series') or {}).get(c) or {}).get('values') or []
    s = [(d, float(v)) for d, v in s]
    if not s:
        return None, None, None
    six = s[-7][1] if len(s) >= 7 else None
    return s[-1][1], s[-1][0], six


def wb(ind, c):
    v = (((WB.get('series') or {}).get(ind) or {}).get('values') or {}).get(c)
    return (v[1], v[0]) if v else (None, None)


# ---------------------------------------------------------------- briques
def crit(cid, label, seuil, valeur, ok, pts, source=None, date=None):
    nc = valeur is None or ok is None
    return {'id': cid, 'label': label, 'seuil': seuil,
            'valeur': None if valeur is None else (round(valeur, 2) if isinstance(valeur, float) else valeur),
            'ok': None if nc else bool(ok), 'points': 0 if nc or not ok else int(pts), 'max': int(pts),
            'nc': nc, 'source': source, 'date': date}


def bloc(elems):
    return int(sum(e['points'] for e in elems)), [e['label'] for e in elems if e['nc']]


def weekly_path(tv=None, yahoo=None, ticker=None):
    return find_wk_metaux(yahoo_cands_metaux(tv, yahoo, ticker))


def tech_from_closed(closed, used=None, tv=None):
    if len(closed) < 52:
        return None
    c = [b['close'] for b in closed]
    o = [b.get('open') if b.get('open') and b['open'] > 0 else None for b in closed]
    ds = [b['date'] for b in closed]
    r = K.rsi(c)
    div = CH.divergence(c, ds, r)
    rp, rd = rsi_points(r[-1], div)
    m, _sg, h = K.macd_series(c)
    mp, md = macd_points(m[-1], h)
    fib = FB.analyse(o, c, ds, adjust_splits=True, sym=used, syms=[used, tv], combine=False)
    fp, fd = fibo_points(fib.get('r') if fib.get('ok') else None)
    _k, d_s, _raw = K.cci_stochastic_kd(c)
    cp, cd = cci_points(d_s[-1] if d_s else None)
    return {'rsi': rp, 'macd': mp, 'fibonacci': fp, 'cci': cp, 'date_cloture': ds[-1], 'close': c[-1], 'n': len(c),
            'detail': {'rsi': {'valeur': None if r[-1] is None else round(float(r[-1]), 1), 'conditions': rd},
                       'macd': {'conditions': md}, 'fibonacci': fd, 'cci': cd}}


def tech_of(tv=None, yahoo=None, ticker=None):
    path, used = weekly_path(tv, yahoo, ticker)
    if not path:
        return None, None
    closed, _meta, _all = load_closed_weekly(path)
    return tech_from_closed(closed, used, tv), used


def _fmt(lab, v):
    if v is None:
        return f'{lab} n.c.'
    if lab.startswith('F&G') or lab.startswith('Sent'):
        return f'{lab} {v:+d}'.replace('-', '−')
    return f'{lab} {v}'


def mm40_of(tv=None, yahoo=None, ticker=None, closes=None, path=None, max_pts=None):
    """Points MM40 hebdo (barème +30 par défaut) et détail, à partir d'une série ou d'un symbole."""
    cap = MM40_HEBDO_MAX_AUTRES if max_pts is None else int(max_pts)
    if closes is None:
        closes = weekly_closes(tv, yahoo, ticker, path)
    return mm40_hebdo_points(closes, max_pts=cap)


def assemble(blocks, fg_pts, fg_label='F&G', meta=None, mm40=None):
    """blocks : [(label, points|None)] ; fg_pts : points sentiment signés (±50).

    mm40 : (points, détail) déjà calculé, ou None pour ne pas ajouter le critère
    (épargne, immobilier). Les points None (n.c.) n'entrent pas dans le total.
    """
    blocks = list(blocks)
    if mm40 is not None:
        pts, det = mm40
        label = (det or {}).get('texte') or mm40_hebdo_texte((det or {}).get('ecart'), pts)
        blocks.append(('MM40 hebdo', pts if pts is not None else None))
        # On remplace le libellé brut par le texte complet dans _fmt via meta, et
        # on pose le texte après coup si pts est un int.
        if meta is None:
            meta = {}
        else:
            meta = dict(meta)
        meta['mm40'] = det
        meta.setdefault('points_mm40', pts)
    brut = int(sum((v or 0) for _l, v in blocks if not isinstance(v, str)) + (fg_pts or 0))
    n = max(MIN, min(MAX, brut))
    band = metaux_band(n)
    bits = []
    for l, v in blocks + [(fg_label, fg_pts)]:
        if l == 'MM40 hebdo' and meta and isinstance(meta.get('mm40'), dict) and meta['mm40'].get('texte'):
            bits.append(meta['mm40']['texte'])
        else:
            bits.append(_fmt(l, v))
    texte = ' · '.join(bits) + f'  →  {n} / 250'
    out = {'note': n, 'display': fmt10(n), 'hex': band['hex'], 'flag': band['flag'], 'band': band['id'], 'pos': n,
           'scale': 250, 'total_max': MAX, 'total_min': MIN, 'total': n, 'v2': True, 'cap': '',
           'decomp': {'texte': texte, 'points': {l: v for l, v in blocks}, 'echelle': 250}}
    out['decomp']['points'][fg_label] = fg_pts
    if meta and meta.get('points_mm40') is not None:
        out['decomp']['points']['mm40'] = meta['points_mm40']
        out['decomp']['points']['MM40 hebdo'] = meta['points_mm40']
    if meta:
        out['decomp'].update(meta)
    out['ligne'] = texte
    return out


FG = None


def fg():
    """Repère CNN (hors note). Pour le calcul, utiliser house()."""
    global FG
    if FG is None:
        FG = load_cnn_fg() or {}
        if FG:
            FG = dict(FG)
            FG['role'] = 'repere_hors_note'
    return FG


def house(tv=None, classe=None, inv=False):
    """Sentiment maison du secteur / de la classe, pour le critère ±50."""
    from . import sentiment as S
    k, rec = S.of(tv=tv, classe=classe)
    pl = S.payload(k, rec, inv=inv)
    if not pl:
        return {'ok': False, 'points': 0, 'value': None, 'label': None, 'cle': None,
                'payload': None, 'court': None, 'source': None}
    return {'ok': True, 'points': pl['points'], 'value': pl['valeur'], 'label': pl['zone'],
            'cle': k, 'payload': pl, 'court': pl['nom'],
            'source': 'sentiment maison ' + pl['nom']}


def sent_pack(g):
    """(points, libellé de ligne, meta fear_greed) à passer à assemble."""
    if g and g.get('ok'):
        lab = 'Sentiment ' + (g.get('court') or '')
        meta = {'valeur': g.get('value'), 'source': g.get('source'), 'points': g['points']}
        return g['points'], lab, meta
    return 0, 'Sentiment', {'valeur': None, 'source': None, 'points': 0}


def years_since(iso):
    if not iso:
        return None
    try:
        d = dt.date.fromisoformat(iso[:10])
    except ValueError:
        return None
    return round((TODAY - d).days / 365.25, 1)


# ---------------------------------------------------------------- change (EUR)
_FX = {}


def eur_per(ccy):
    """Cours BCE : combien d'EUR pour 1 unité de devise (dernier jour)."""
    if ccy in ('EUR', None):
        return 1.0
    if ccy == 'GBp':
        return None if eur_per('GBP') is None else eur_per('GBP') / 100
    if ccy in _FX:
        return _FX[ccy]
    p = Path('/workspace/invest/patrimoine-dashboard/data/liquidites') / f'ecb_EXR_D.{ccy}.EUR.SP00.A.csv'
    v = None
    if p.exists():
        rows = [r for r in csv.DictReader(io.StringIO(p.read_text())) if r.get('OBS_VALUE') not in (None, '', 'NaN')]
        if rows:
            v = 1.0 / float(rows[-1]['OBS_VALUE'])
    _FX[ccy] = v
    return v


# ---------------------------------------------------------------- qualité ETF (justETF)
def je_of(isin):
    r = JE.get(isin) or {}
    return r if r and not r.get('erreur') else None


def etf_quality(isin, regles, cycle=None, yahoo=None, pts=None):
    """regles : liste d'identifiants parmi ter25, ter15, ter40, ter20, ter50, enc300, enc500, enc1000, age3, age5, phys, lignes30, cycle."""
    r = je_of(isin) if isin else None
    y = YF.get(yahoo) if yahoo else None
    m = MAN.get(yahoo) if yahoo else None
    src = (f"justETF ({r['url']}) relevé {r['date']}" if r else None)
    ter = r.get('ter') if r else None
    if ter is None and m and m.get('ter') is not None:
        ter, src_ter = m['ter'], f"{m['source']} ({m['url']}) {m['date']}"
    elif ter is None and y and y.get('netExpenseRatio') is not None:
        ter, src_ter = float(y['netExpenseRatio']), f"Yahoo Finance ({y['url']}) {y['date']}"
    else:
        src_ter = src
    enc = r.get('encours_m') if r else None
    src_enc = src
    if enc is not None and r.get('encours_devise') not in (None, 'EUR'):
        k = eur_per(r['encours_devise'])
        enc = enc * k if k else None
    if enc is None and y and y.get('totalAssets'):
        k = eur_per(y.get('currency'))
        if k:
            enc = y['totalAssets'] * k / 1e6
            src_enc = f"Yahoo Finance totalAssets ({y['url']}) {y['date']}, converti au cours BCE"
    crea = r.get('creation') if r else None
    src_crea = src
    if crea is None and y and y.get('fundInceptionDate'):
        crea = dt.datetime.utcfromtimestamp(y['fundInceptionDate']).date().isoformat()
        src_crea = f"Yahoo Finance fundInceptionDate ({y['url']}) {y['date']}"
    age = years_since(crea)
    rep = r.get('replication') if r else None
    nl = r.get('n_lignes') if r else None
    P = dict(PTS, **(pts or {}))
    E = []
    for rid in regles:
        if rid.startswith('ter'):
            s = {'ter25': 0.25, 'ter15': 0.15, 'ter40': 0.40, 'ter20': 0.20, 'ter50': 0.50}[rid]
            E.append(crit(rid, f'Frais courants ≤ {str(s).replace(".", ",")} %', f'≤ {s} %', ter, None if ter is None else ter <= s, P[rid], src_ter, None))
        elif rid.startswith('enc'):
            s = int(rid[3:])
            lab = f'Encours ≥ {s} M€' if s < 1000 else 'Encours ≥ 1 Md€'
            E.append(crit(rid, lab, f'≥ {s} M€', None if enc is None else round(enc), None if enc is None else enc >= s, P[rid], src_enc, None))
        elif rid.startswith('age'):
            s = int(rid[3:])
            E.append(crit(rid, f'Ancienneté ≥ {s} ans', f'≥ {s} ans (création {crea})' if crea else f'≥ {s} ans', age, None if age is None else age >= s, P[rid], src_crea, crea))
        elif rid == 'phys':
            E.append(crit(rid, 'Réplication physique', 'Physical', rep, None if rep is None else rep.lower().startswith('phys'), P[rid], src, None))
        elif rid == 'lignes30':
            E.append(crit(rid, 'Au moins 30 lignes', '≥ 30', nl, None if nl is None else nl >= 30, P[rid], src, None))
        elif rid == 'cycle':
            E.append(cycle if cycle else crit('cycle', 'Cycle du secteur', '—', None, None, PTS['cycle']))
    return E


PTS = {'ter25': 9, 'ter15': 9, 'ter40': 10, 'ter20': 10, 'ter50': 10, 'enc300': 10, 'enc500': 10, 'enc1000': 10,
       'age3': 10, 'age5': 10, 'phys': 10, 'lignes30': 10, 'cycle': 10}


def cycle_wti():
    s = fred('DCOILWTICO')
    if not s:
        return crit('cycle', 'Cycle pétrole : WTI sous sa moyenne 5 ans', 'WTI < moyenne 5 ans', None, None, 10)
    d, v = s[-1]
    d0 = dt.date.fromisoformat(d)
    lo = dt.date(d0.year - 5, d0.month, min(d0.day, 28)).isoformat()
    vals = [x[1] for x in s if x[0] >= lo]
    moy = sum(vals) / len(vals)
    return crit('cycle', 'Cycle pétrole : WTI sous sa moyenne 5 ans (achat en bas de cycle)', f'< {moy:.1f} $', v, v < moy, 10,
                fred_src('DCOILWTICO'), d)


def cycle_taux_us():
    d, v = last('DGS10')
    d6, v6 = ago('DGS10', 6)
    ok = None if v is None or v6 is None else v < v6
    return crit('cycle', 'Cycle des taux : 10 ans US en baisse sur 6 mois', f'< {v6} % ({d6})' if v6 is not None else '—',
                v, ok, 10, fred_src('DGS10'), d)


def cycle_nc(label):
    return crit('cycle', label, '—', None, None, 10, 'aucune série publique gratuite du prix de l’uranium dans les sources du site', None)


# ---------------------------------------------------------------- ETC métaux
def etc_quality(isin):
    ids = ['ter25', 'ter15', 'enc1000', 'age5', 'phys']
    E = etf_quality(isin, ids, pts={k: 9 for k in ids})  # 5 × 9 = 45
    return bloc(E) + (E,)


# ---------------------------------------------------------------- énergie
GROUP_CYCLE = {'Pétrole et gaz': 'wti', 'Gaz naturel': 'wti', 'Charbon': 'wti', 'Électricité et utilities': 'taux',
               'Solaire': 'taux', 'Éolien': 'taux', 'Hydrogène et stockage': 'taux', 'Nucléaire et uranium': 'uranium'}


def cycle_of(groupe, tv=None):
    if tv in ('NASDAQ:CEG',):
        return cycle_taux_us()
    k = GROUP_CYCLE.get(groupe)
    if tv in ('XETR:XDW0',):
        k = 'wti'
    if tv in ('XETR:ZPDU',):
        k = 'taux'
    if k == 'wti':
        return cycle_wti()
    if k == 'taux':
        return cycle_taux_us()
    return cycle_nc('Cycle uranium : prix spot sous sa moyenne 5 ans')


def energie_fond(yahoo, groupe, tv=None):
    y = YF.get(yahoo) or {}
    src = f"Yahoo Finance ({y.get('url')}) relevé {y.get('date')}" if y else None
    def g(k):
        v = y.get(k)
        return None if v is None else float(v)
    pe, ev = g('trailingPE'), g('enterpriseToEbitda')
    debt, cash, ebitda = g('totalDebt'), g('totalCash'), g('ebitda')
    nd = None if None in (debt, ebitda) or not ebitda or ebitda <= 0 else (debt - (cash or 0)) / ebitda
    om = None if g('operatingMargins') is None else g('operatingMargins') * 100
    fcf, rev = g('freeCashflow'), g('totalRevenue')
    fm = None if None in (fcf, rev) or not rev else fcf / rev * 100
    dy = g('dividendYield')
    po = None if g('payoutRatio') is None else g('payoutRatio') * 100
    roe = None if g('returnOnEquity') is None else g('returnOnEquity') * 100
    E = [
        crit('per', 'PER < 12', '< 12', pe, None if pe is None else 0 < pe < 12, 10, src),
        crit('ev_ebitda', 'VE / EBITDA < 7', '< 7', ev, None if ev is None else 0 < ev < 7, 10, src),
        crit('nd_ebitda', 'Dette nette / EBITDA < 2', '< 2', nd, None if nd is None else nd < 2, 10, src),
        crit('marge_op', 'Marge opérationnelle > 15 %', '> 15 %', om, None if om is None else om > 15, 10, src),
        crit('marge_fcf', 'Marge de cash-flow libre > 8 %', '> 8 %', fm, None if fm is None else fm > 8, 10, src),
        crit('rdt_div', 'Rendement du dividende > 3 %', '> 3 %', dy, None if dy is None else dy > 3, 10, src),
        crit('payout', 'Taux de distribution < 70 % (dividende versé)', '0 < x < 70 %', po, None if po is None else 0 < po < 70, 10, src),
        crit('roe', 'ROE > 12 %', '> 12 %', roe, None if roe is None else roe > 12, 10, src),
        cycle_of(groupe, tv),
    ]
    return bloc(E) + (E,)


def energie_etf_fond(isin, groupe, tv):
    E = etf_quality(isin, ['ter40', 'ter20', 'enc300', 'enc1000', 'age3', 'age5', 'phys', 'lignes30', 'cycle'], cycle=cycle_of(groupe, tv))
    return bloc(E) + (E,)


# ---------------------------------------------------------------- obligations
SEG = {
    # key: (rendement nominal, réel direct, inflation, type, prime)
    'tcourt': {'rdt': 'DGS2', 'reel': 'DFII5', 'infl': 'CPIAUCSL', 'prime': ('pente_us',), 'ccy': 'USD'},
    'tlong': {'rdt': 'DGS20', 'reel': 'DFII20', 'infl': 'CPIAUCSL', 'prime': ('pente_us',), 'ccy': 'USD'},
    'eurgov': {'rdt': ('IRLTLT01DEM156N', 'IRLTLT01FRM156N'), 'infl': 'CP0000EZ19M086NEST', 'prime': ('pente_eur', 'IRLTLT01DEM156N'), 'ccy': 'EUR'},
    'france': {'rdt': 'IRLTLT01FRM156N', 'infl': 'CP0000FRM086NEST', 'prime': ('pente_eur', 'IRLTLT01FRM156N'), 'ccy': 'EUR'},
    'de': {'rdt': 'IRLTLT01DEM156N', 'infl': 'CP0000EZ19M086NEST', 'prime': ('pente_eur', 'IRLTLT01DEM156N'), 'ccy': 'EUR'},
    'usig': {'rdt': 'BAMLC0A0CMEY', 'infl': 'CPIAUCSL', 'prime': ('oas', 'BAMLC0A0CM'), 'ccy': 'USD'},
    'eurig': {'rdt': None, 'infl': 'CP0000EZ19M086NEST', 'prime': ('oas', None), 'ccy': 'EUR'},
    'hy': {'rdt': 'BAMLH0A0HYM2EY', 'infl': 'CPIAUCSL', 'prime': ('oas', 'BAMLH0A0HYM2'), 'ccy': 'USD'},
    'infl': {'rdt': 'DFII10', 'reel': 'DFII10', 'infl': 'CPIAUCSL', 'prime': ('pente_us',), 'ccy': 'USD'},
    'em': {'rdt': 'BAMLEMCBPIEY', 'infl': 'CPIAUCSL', 'prime': ('oas', 'BAMLEMCBPIOAS'), 'ccy': 'USD'},
}
# Les ETF de la liste HY en euro utilisent l'indice ICE BofA Euro High Yield.
HY_EUR = {'rdt': 'BAMLHE00EHYIEY', 'infl': 'CP0000EZ19M086NEST', 'prime': ('oas', 'BAMLHE00EHYIOAS'), 'ccy': 'EUR'}


def _rdt(spec):
    if spec is None:
        return None, None, None
    if isinstance(spec, tuple):
        vals = [last(s) for s in spec]
        if any(v is None for _d, v in vals):
            return None, None, None
        return round(sum(v for _d, v in vals) / len(vals), 2), min(d for d, _v in vals), 'moyenne ' + ' / '.join(spec)
    d, v = last(spec)
    return v, d, spec


def court_ou_long(nom):
    n = (nom or '').lower()
    for k in ('1-3', '0-5', '2.5-5.5', '0-3', '1-5', 'short', 'ultrashort', '0-1'):
        if k in n:
            return 'courte'
    return 'longue'


def oblig_macro(spec, nom):
    """Critères 1 à 4 (segment / indice)."""
    E = []
    rdt, d_r, lab_r = _rdt(spec.get('rdt'))
    if spec.get('reel'):
        dre, reel = last(spec['reel'])
        src_reel = fred_src(spec['reel']) + ' (rendement réel des TIPS)'
    else:
        inf, d_i = yoy(spec['infl'])
        reel = None if rdt is None or inf is None else round(rdt - inf, 2)
        dre = d_r
        src_reel = (f'FRED : {lab_r} au {d_r} − inflation sur 1 an {spec["infl"]} au {d_i}' if rdt is not None else
                    'rendement de l’indice euro investment grade introuvable dans les sources gratuites (FRED ne publie plus ICE BofA Euro Corporate)')
    E.append(crit('reel_pos', 'Rendement réel > 0', '> 0 %', reel, None if reel is None else reel > 0, 10, src_reel, dre))
    E.append(crit('reel_15', 'Rendement réel > 1,5 %', '> 1,5 %', reel, None if reel is None else reel > 1.5, 10, src_reel, dre))
    pr = spec['prime']
    if pr[0] == 'pente_us':
        d10, v10 = last('DGS10'); _d2, v2 = last('DGS2')
        pente = None if None in (v10, v2) else round(v10 - v2, 2)
        E.append(crit('prime', 'Prime de terme : pente 10 ans − 2 ans US > 0', '> 0 pt', pente, None if pente is None else pente > 0, 10, fred_src('DGS10', 'DGS2'), d10))
    elif pr[0] == 'pente_eur':
        d10, v10 = last(pr[1]); _dd, dfr = last('ECBDFR')
        pente = None if None in (v10, dfr) else round(v10 - dfr, 2)
        E.append(crit('prime', 'Prime de terme : 10 ans − taux de dépôt BCE > 0,5 pt', '> 0,5 pt', pente, None if pente is None else pente > 0.5, 10, fred_src(pr[1], 'ECBDFR'), d10))
    else:
        sid = pr[1]
        if sid:
            d, v = last(sid); med = median_years(sid, 10)
            E.append(crit('prime', 'Prime de crédit : spread OAS ≥ sa médiane 10 ans', f'≥ {med:.2f} pt' if med is not None else '—', v,
                          None if v is None or med is None else v >= med, 10, fred_src(sid), d))
        else:
            E.append(crit('prime', 'Prime de crédit : spread OAS ≥ sa médiane 10 ans', '—', None, None, 10,
                          'spread de l’indice euro investment grade introuvable dans les sources gratuites', None))
    dur = court_ou_long(nom)
    d, v = last('DGS10' if spec['ccy'] == 'USD' else 'IRLTLT01DEM156N')
    d6, v6 = ago('DGS10' if spec['ccy'] == 'USD' else 'IRLTLT01DEM156N', 6)
    if v is None or v6 is None:
        ok = None
    elif dur == 'longue':
        ok = v < v6
    else:
        ok = v >= v6
    sid10 = 'DGS10' if spec['ccy'] == 'USD' else 'IRLTLT01DEM156N'
    lab = ('Duration longue et taux 10 ans en baisse sur 6 mois' if dur == 'longue' else 'Duration courte et taux 10 ans stables ou en hausse sur 6 mois')
    E.append(crit('duration_cycle', lab, f'10 ans {v6} % il y a 6 mois ({d6})', v, ok, 10,
                  fred_src(sid10) + f' ; duration {dur} déduite de l’échéance indiquée dans le nom du fonds', d))
    return E


def rating_share(tv, rating_a=None):
    if rating_a is not None:
        return float(rating_a), 'Yahoo Finance, répartition des notations (obligations.json)'
    sym = {'XETR:IUSU': 'IUSU.DE', 'XETR:IS04': 'IS04.DE', 'XETR:EUNH': 'EUNH.DE', 'EURONEXT:IFRB': 'IFRB.AS', 'XETR:IBCD': 'IBCD.DE',
           'XETR:EUN5': 'EUN5.DE', 'XETR:XUHY': 'XUHY.DE', 'XETR:TIUP': 'TIUP.DE', 'XETR:IUS7': 'IUS7.DE', 'XETR:IS0L': 'IS0L.DE'}.get(tv)
    p = Path('/workspace/invest/patrimoine-dashboard/data/obligations/etf') / f'{sym}.json'
    if sym and p.exists():
        r = json.loads(p.read_text()).get('ratings') or {}
        if r and any(r.get(k) for k in ('aaa', 'aa', 'a', 'bbb', 'bb', 'b', 'below_b')):
            return round((float(r.get('aaa') or 0) + float(r.get('aa') or 0) + float(r.get('a') or 0)) * 100, 1), f'Yahoo Finance, répartition des notations ({sym}, relevé {json.loads(p.read_text()).get("retrieved")})'
    return None, None


def oblig_fond(seg_key, tv, isin, nom, rating_a=None, hedged=None):
    spec = SEG[seg_key]
    if seg_key == 'hy' and nom and ('EUR High Yield' in nom or 'Euro High Yield' in nom or 'EUR HIGH YIELD' in nom.upper()) and 'USD' not in nom:
        spec = HY_EUR
    E = oblig_macro(spec, nom)
    ra, src_ra = rating_share(tv, rating_a)
    E.append(crit('notation', 'Qualité : ≥ 50 % des titres notés A ou mieux', '≥ 50 %', ra, None if ra is None else ra >= 50, 10, src_ra))
    E += etf_quality(isin, ['ter15', 'enc500', 'age5'])
    for e in E:
        if e['id'] == 'ter15':
            e['max'] = 10; e['points'] = 10 if e['ok'] else 0
    r = je_of(isin) if isin else None
    dev = r.get('devise_fonds') if r else None
    couv = r.get('couverture') if r else None
    if couv is None and hedged is not None:
        couv = 'Yes' if hedged else 'No'
    ok = None
    if dev is not None or couv is not None:
        ok = (dev == 'EUR') or (str(couv).lower().startswith('yes'))
    E.append(crit('change', 'Risque de change maîtrisé (fonds en EUR ou couvert)', 'EUR ou couvert', f'{dev or "?"} / couverture {couv or "?"}' if ok is not None else None,
                  ok, 10, f"justETF ({r['url']})" if r else 'obligations.json (champ couvert)'))
    return bloc(E) + (E,)


# ---------------------------------------------------------------- devises
CCY_WB = {'USD': 'USA', 'JPY': 'JPN', 'GBP': 'GBR', 'CHF': 'CHE', 'AUD': 'AUS', 'CAD': 'CAN', 'KRW': 'KOR'}
CCY_BIS = {'USD': 'US', 'JPY': 'JP', 'GBP': 'GB', 'CHF': 'CH', 'AUD': 'AU', 'CAD': 'CA', 'KRW': 'KR'}


def devise_fond(ccy):
    c = CCY_WB[ccy]
    pol, d_pol, _six = bis_rate(CCY_BIS[ccy])
    ecb, d_ecb, _ = bis_rate('XM')
    s_bis = f"BRI, taux directeurs WS_CBPOL ({d_pol})"
    diff = None if None in (pol, ecb) else round(pol - ecb, 2)
    inf, y_inf = wb('FP.CPI.TOTL.ZG', c)
    inf_ez, _ = wb('FP.CPI.TOTL.ZG', 'EMU')
    s_wb = 'Banque mondiale (WDI)'
    ca, y_ca = wb('BN.CAB.XOKA.GD.ZS', c)
    debt, y_debt = wb('GC.DOD.TOTL.GD.ZS', c)
    sol, y_sol = wb('GC.NLD.TOTL.GD.ZS', c)
    gr, y_gr = wb('NY.GDP.MKTP.KD.ZG', c)
    gr_ez, _ = wb('NY.GDP.MKTP.KD.ZG', 'EMU')
    reel = None if None in (pol, inf) else round(pol - inf, 2)
    E = [
        crit('taux_sup', 'Taux directeur > taux BCE', f'> {ecb} %', pol, None if diff is None else diff > 0, 10, s_bis, d_pol),
        crit('taux_ecart', 'Écart de taux directeur > 1,5 pt', '> 1,5 pt', diff, None if diff is None else diff > 1.5, 10, s_bis, d_pol),
        crit('inflation', 'Inflation < zone euro', f'< {inf_ez:.2f} %' if inf_ez is not None else '—', inf, None if None in (inf, inf_ez) else inf < inf_ez, 10, f'{s_wb} FP.CPI.TOTL.ZG', y_inf),
        crit('taux_reel', 'Taux directeur réel > 0', '> 0', reel, None if reel is None else reel > 0, 10, f'{s_bis} − {s_wb} inflation', y_inf),
        crit('balance', 'Balance courante > 0 % du PIB', '> 0 %', ca, None if ca is None else ca > 0, 10, f'{s_wb} BN.CAB.XOKA.GD.ZS', y_ca),
        crit('dette', 'Dette publique < 90 % du PIB', '< 90 %', debt, None if debt is None else debt < 90, 10, f'{s_wb} GC.DOD.TOTL.GD.ZS (administration centrale)', y_debt),
        crit('solde', 'Solde public > −3 % du PIB', '> −3 %', sol, None if sol is None else sol > -3, 10, f'{s_wb} GC.NLD.TOTL.GD.ZS', y_sol),
        crit('croissance', 'Croissance réelle > zone euro', f'> {gr_ez:.2f} %' if gr_ez is not None else '—', gr, None if None in (gr, gr_ez) else gr > gr_ez, 10, f'{s_wb} NY.GDP.MKTP.KD.ZG', y_gr),
        crit('ppa', 'Sous-évaluée selon la PPA', 'cours < PPA', None, None, 10, 'FMI DataMapper bloqué (403) et indicateur Banque mondiale PA.NUS.PPPC.RF archivé', None),
    ]
    return bloc(E) + (E,)


def devise_weekly(ccy):
    """Bougies hebdo de 1 unité de devise en EUR, inversées depuis EURxxx=X (Yahoo, déjà en base)."""
    import urllib.parse
    name = f'yahoo_1wk_{urllib.parse.quote("EUR" + ccy + "=X", safe="")}.json'
    for base in (ROOT / 'data' / 'fibo_max', Path('/workspace/invest/patrimoine-dashboard/data/liquidites')):
        p = base / (urllib.parse.quote('EUR' + ccy + '=X', safe='') + '.json') if base.name == 'fibo_max' else base / name
        if p.exists():
            closed, _m, _a = load_closed_weekly(p)
            inv = []
            for b in closed:
                if not b.get('close'):
                    continue
                inv.append({'date': b['date'], 'close': 1.0 / b['close'],
                            'open': (1.0 / b['open']) if b.get('open') else None,
                            'high': (1.0 / b['low']) if b.get('low') else None,
                            'low': (1.0 / b['high']) if b.get('high') else None, 'closed': True})
            return inv, str(p)
    return [], None


def score_devise(ccy):
    bars, path = devise_weekly(ccy)
    t = tech_from_closed(bars, f'EUR{ccy}=X (inversé)') if bars else None
    fpts, fnc, fel = devise_fond(ccy)
    g = house(classe='devises')
    fgp, flab, fmeta = sent_pack(g)
    blocks = [('RSI', t and t['rsi']), ('MACD', t and t['macd']), ('Fibo', t and t['fibonacci']), ('CCI', t and t['cci']), ('Fond. devise', fpts)]
    closes = [b['close'] for b in bars] if bars else []
    out = assemble(blocks, fgp, flab,
                   {'fondamental': {'points': fpts, 'max': 90, 'elements': fel, 'nc': fnc},
                    'technique': {'source': path, 'date_cloture': t and t['date_cloture'], 'detail': t and t['detail']},
                    'fear_greed': fmeta,
                    'sentiment': g.get('payload')},
                   mm40=mm40_of(closes=closes, path=path))
    if g.get('payload'):
        out['sentiment'] = g['payload']
    return out


# ---------------------------------------------------------------- épargne / monétaire
def epargne_score(prod):
    """prod : dict(id, nom, taux, ccy, impose(bool), garantie(str|None), liquide(bool|None), frais(bool|None), src)."""
    ccy = prod['ccy']
    if ccy == 'EUR':
        pol_s, infl_s, l10 = 'ECBDFR', 'CP0000FRM086NEST', 'IRLTLT01FRM156N'
    else:
        pol_s, infl_s, l10 = 'FEDFUNDS', 'CPIAUCSL', 'DGS10'
    d_p, pol = last(pol_s); d_p6, pol6 = ago(pol_s, 6)
    inf, d_i = yoy(infl_s)
    # inflation il y a 6 mois
    s = fred(infl_s)
    inf6 = None
    if len(s) >= 19:
        inf6 = round((s[-7][1] / s[-19][1] - 1) * 100, 2)
    if ccy == 'EUR' and prod.get('ipc'):
        ser = [x for x in prod['ipc'] if x[1] is not None]
        inf, d_i = float(ser[-1][1]), ser[-1][0]
        inf6 = float(ser[-7][1]) if len(ser) >= 7 else None
        infl_s = 'INSEE IPC France, glissement annuel (idbank %s)' % prod.get('ipc_id', '011814632')
    d10, v10 = last(l10)
    taux = prod['taux']
    C = [
        crit('vs_directeur', 'Taux ≥ taux directeur − 0,25 pt', f'≥ {pol - 0.25:.2f} %' if pol is not None else '—', taux,
             None if pol is None or taux is None else taux >= pol - 0.25, 30, fred_src(pol_s), d_p),
        crit('directeur_tendance', 'Taux directeur stable ou en hausse sur 6 mois', f'≥ {pol6} % ({d_p6})', pol, None if None in (pol, pol6) else pol >= pol6, 30, fred_src(pol_s), d_p),
        crit('inflation_baisse', 'Inflation en baisse sur 6 mois', f'< {inf6} % (il y a 6 mois)' if inf6 is not None else '—', inf, None if None in (inf, inf6) else inf < inf6, 30, infl_s if infl_s.startswith('INSEE') else fred_src(infl_s), d_i),
        crit('courbe_plate', 'Courbe plate : 10 ans − taux directeur < 0,5 pt', '< 0,5 pt', None if None in (v10, pol) else round(v10 - pol, 2),
             None if None in (v10, pol) else (v10 - pol) < 0.5, 20, fred_src(l10, pol_s), d10),
    ]
    pfu = (MAN.get('PFU') or {}).get('taux')
    net = None if taux is None else (taux * (1 - pfu / 100) if prod['impose'] and pfu else taux)
    reel = None if None in (net, inf) else round(net - inf, 2)
    src_net = ('exonéré d’impôt' if not prod['impose'] else f"PFU {pfu} % ({(MAN.get('PFU') or {}).get('url')})") + (f' ; inflation {infl_s}, {d_i}' if infl_s.startswith('INSEE') else f' ; inflation {infl_s} (FRED, {d_i})')
    Fd = [
        crit('reel_pos', 'Taux net d’impôt − inflation > 0', '> 0', reel, None if reel is None else reel > 0, 20, src_net, d_i),
        crit('reel_1', 'Taux réel net > 1 pt', '> 1 pt', reel, None if reel is None else reel > 1, 10, src_net, d_i),
        crit('garantie', 'Capital garanti (État ou fonds de garantie des dépôts)', 'oui', prod.get('garantie'), None if prod.get('garantie') is None else prod['garantie'] != 'non', 20, prod.get('src_garantie')),
        crit('liquidite', 'Disponible à tout moment', 'oui', prod.get('liquide_txt'), prod.get('liquide'), 20, prod.get('src_liquide')),
        crit('change', 'Sans risque de change pour un épargnant en euros', 'EUR', ccy, ccy == 'EUR', 10, 'devise du produit'),
        crit('frais', 'Sans frais', 'oui', prod.get('frais_txt'), prod.get('frais'), 10, prod.get('src_frais')),
    ]
    cpts, cnc = bloc(C)
    fpts, fnc = bloc(Fd)
    g = house(classe='liquidites', inv=True)
    fgp, flab, fmeta = sent_pack(g)
    rec = assemble([('Contexte taux', cpts), ('Fond. épargne', fpts)], fgp, flab or 'Sentiment inversé',
                    {'contexte': {'points': cpts, 'max': 110, 'elements': C, 'nc': cnc},
                     'fondamental': {'points': fpts, 'max': 90, 'elements': Fd, 'nc': fnc, 'taux_net': None if net is None else round(net, 2)},
                     'fear_greed': fmeta,
                     'sentiment': g.get('payload')})
    if g.get('payload'):
        rec['sentiment'] = g['payload']
    return rec


# ---------------------------------------------------------------- immobilier
def immobilier_score(comp):
    """comp : composantes existantes d'achatvente.json['immobilier']."""
    def find(prefix):
        return next((c for c in comp if str(c.get('nom', '')).startswith(prefix)), None)
    def num(s):
        import re
        m = re.search(r'[-−]?\d+(?:,\d+)?', str(s or ''))
        return None if not m else float(m.group(0).replace(',', '.').replace('−', '-'))
    mom, taux, tend, trends, sent = (find('Momentum'), find('Niveau des taux'), find('Tendance des taux'), find('Ratio achat'), find('Sentiment immobilier'))
    pct = None
    if taux:
        import re
        m = re.search(r'(\d+)\s*ᵉ', str(taux.get('valeur')))
        pct = int(m.group(1)) if m else None
    tr_note = trends.get('note') if trends else None
    C = [
        crit('prix_baisse', 'Prix Notaires-INSEE en baisse sur 1 an (achat en bas de cycle)', '< 0 %', num(mom and mom.get('valeur')), None if not mom else num(mom['valeur']) < 0, 30, 'Notaires-INSEE (composante APEX immobilier)', None),
        crit('taux_bas', 'Taux de crédit sous la médiane depuis 2000', '< 50ᵉ percentile', pct, None if pct is None else pct < 50, 30, 'Banque de France MIR1 (composante APEX immobilier)', None),
        crit('taux_baisse', 'Taux de crédit en baisse sur 6 mois', '< 0 pt', num(tend and tend.get('valeur')), None if not tend else num(tend['valeur']) < 0, 30, 'Banque de France MIR1 (composante APEX immobilier)', None),
        crit('demande', 'Demande d’achat (Google Trends) au-dessus de sa médiane 12 mois', 'percentile > 50', tr_note, None if tr_note is None else tr_note > 0, 20, 'Google Trends (composante APEX immobilier)', None),
    ]
    Fd = [
        crit('rdt_locatif', 'Rendement locatif brut − OAT 10 ans > 2 pts', '> 2 pts', None, None, 20, 'loyers et prix au m² nationaux non collectés dans le site'),
        crit('prix_revenu', 'Ratio prix / revenu sous sa moyenne longue', '< moyenne', None, None, 20, 'série prix/revenu (CGEDD-Friggit) non collectée'),
        crit('credits', 'Production de crédits à l’habitat en hausse sur 1 an', '> 0 %', None, None, 20, 'série Banque de France des crédits nouveaux non collectée'),
        crit('transactions', 'Nombre de transactions en hausse sur 1 an', '> 0 %', None, None, 15, 'série CGEDD des transactions non collectée'),
        crit('vacance', 'Taux de logements vacants < 8 %', '< 8 %', None, None, 15, 'INSEE (recensement) non collecté'),
    ]
    cpts, cnc = bloc(C)
    fpts, fnc = bloc(Fd)
    g = house(classe='immo:fr')
    if g.get('ok'):
        fgp, flab, fmeta = sent_pack(g)
        rec = assemble([('Contexte marché', cpts), ('Fond. immobilier', fpts)], fgp, flab or 'Sentiment immo',
                       {'contexte': {'points': cpts, 'max': 110, 'elements': C, 'nc': cnc},
                        'fondamental': {'points': fpts, 'max': 90, 'elements': Fd, 'nc': fnc},
                        'fear_greed': fmeta, 'sentiment': g.get('payload')})
        rec['sentiment'] = g['payload']
        return rec
    sv = num(sent and sent.get('valeur'))
    sp = None if sv is None else (1 if sv < 50 else -1) * int(abs(50 - sv) // 10) * 10
    return assemble([('Contexte marché', cpts), ('Fond. immobilier', fpts)], sp, 'Sentiment immo',
                    {'contexte': {'points': cpts, 'max': 110, 'elements': C, 'nc': cnc},
                     'fondamental': {'points': fpts, 'max': 90, 'elements': Fd, 'nc': fnc},
                     'sentiment': {'valeur': sv, 'regle': 'sentiment immobilier APEX à contre-courant, tranches de 10 (±50)'}})
