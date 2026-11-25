#!/usr/bin/env python3
"""Indicateur d'Attention Long Swing APEX (« H », hype) — actions USA et France notées sur −80..280.

Note d'attention 0–100 (horizon semaines / mois, calcul hebdomadaire) :
  Google Trends 35 % · mentions 35 % · volume relatif 20 % · persistance 10 %.
Variante A : poids recalculés sur les sources disponibles. Aucune source -> attention « – ».
Apport APEX à contre-courant : H = (50 − attention) × 0,6, de −30 à +30 ; attention absente -> H = 0 affiché « – ».
Ce n'est ni un indicateur technique, ni le Fear & Greed, ni un signal d'achat ou de vente.

Sources :
- volume : yfinance, bougies hebdo (dernière bougie partielle exclue) ;
- Google Trends : pytrends (non officiel), 5 ans hebdo, cache local par semaine ISO + reprise après 429 ;
- mentions : ApeWisdom (agrégat public Reddit : wallstreetbets, stocks, investing…), instantané 24 h,
  sauvegardé chaque jour dans data/attention/apewisdom/AAAA-MM-JJ.json pour constituer l'historique ;
- X et StockTwits : non accessibles (manquants).

Écrit data/attention_apex.json (lu par build_apex_achat_v2_world.py / apply_attention.py).
Usage : python3 src/attention_apex.py [--max-minutes N] [--no-trends]
"""
from __future__ import annotations
import json, math, os, sys, time, datetime as dt
from pathlib import Path
import numpy as np, pandas as pd, requests

ROOT = Path(os.environ.get('APEX_ROOT') or Path(__file__).resolve().parent.parent)
DATA = ROOT / 'data'
ADIR = DATA / 'attention'
TR_CACHE = ADIR / 'trends_cache'
APE_DIR = ADIR / 'apewisdom'
for p in (ADIR, TR_CACHE, APE_DIR):
    p.mkdir(parents=True, exist_ok=True)
TODAY = dt.date.today()
ISOW = '%d-W%02d' % TODAY.isocalendar()[:2]
W = {'trends': 0.35, 'mentions': 0.35, 'volume': 0.20, 'persist': 0.10}
H_FACTOR = 0.6
PAUSE = 15      # secondes entre deux requêtes Google Trends
BACKOFF = 60    # pause après un 429 (× tentative)

# Termes Google Trends (nom court). USA : « <nom> stock », monde. France : nom seul, géo FR.
US_TERM = {
    'APP': 'AppLovin', 'RDDT': 'Reddit', 'META': 'Meta', 'NFLX': 'Netflix', 'GOOGL': 'Google',
    'ABNB': 'Airbnb', 'DASH': 'DoorDash', 'BKNG': 'Booking Holdings', 'GRMN': 'Garmin', 'CVNA': 'Carvana',
    'MNST': 'Monster Beverage', 'PM': 'Philip Morris', 'EL': 'Estee Lauder', 'KDP': 'Keurig Dr Pepper', 'COST': 'Costco',
    'EOG': 'EOG', 'EQT': 'EQT', 'COP': 'ConocoPhillips', 'OXY': 'Occidental', 'CVX': 'Chevron',
    'MA': 'Mastercard', 'SCHW': 'Schwab', 'V': 'Visa', 'BLK': 'BlackRock', 'SPGI': 'S&P Global',
    'ISRG': 'Intuitive Surgical', 'LLY': 'Eli Lilly', 'ABBV': 'AbbVie', 'VRTX': 'Vertex', 'REGN': 'Regeneron',
    'HWM': 'Howmet', 'GEV': 'GE Vernova', 'GE': 'GE Aerospace', 'TT': 'Trane', 'PWR': 'Quanta Services',
    'FCX': 'Freeport', 'NEM': 'Newmont', 'PKG': 'Packaging Corp', 'STLD': 'Steel Dynamics', 'CF': 'CF Industries',
    'SPG': 'Simon Property', 'EQIX': 'Equinix', 'PSA': 'Public Storage', 'O': 'Realty Income', 'CBRE': 'CBRE',
    'PLTR': 'Palantir', 'NVDA': 'Nvidia', 'AVGO': 'Broadcom', 'ANET': 'Arista', 'AMD': 'AMD',
    'VST': 'Vistra', 'ETR': 'Entergy', 'CEG': 'Constellation Energy', 'AWK': 'American Water', 'NEE': 'NextEra',
}
FR_TERM = {
    'PUB': 'Publicis', 'DEC': 'JCDecaux', 'ORA': 'Orange action', 'ETL': 'Eutelsat', 'MMT': 'M6 action',
    'RMS': 'Hermès action', 'KER': 'Kering', 'AC': 'Accor', 'MC': 'LVMH', 'SK': 'SEB action',
    'OR': "L'Oréal action", 'ITP': 'Interparfums', 'RCO': 'Rémy Cointreau', 'BN': 'Danone', 'BB': 'BIC action',
    'GTT': 'GTT action', 'TE': 'Technip Energies', 'VIRI': 'Viridien', 'TTE': 'TotalEnergies', 'MAU': 'Maurel & Prom',
    'BNP': 'BNP Paribas', 'CS': 'AXA action', 'EDEN': 'Edenred', 'GLE': 'Société Générale', 'ACA': 'Crédit Agricole action',
    'IPN': 'Ipsen', 'VIRP': 'Virbac', 'SAN': 'Sanofi', 'DIM': 'Sartorius Stedim', 'EL': 'EssilorLuxottica',
    'SU': 'Schneider Electric', 'SAF': 'Safran', 'LR': 'Legrand', 'AM': 'Dassault Aviation', 'HO': 'Thales',
    'VK': 'Vallourec', 'RBT': 'Robertet', 'AI': 'Air Liquide', 'ERA': 'Eramet', 'VCT': 'Vicat',
    'LI': 'Klépierre', 'COV': 'Covivio', 'URW': 'Unibail', 'GFC': 'Gecina', 'SOI': 'Soitec',
    'VU': 'Vusion', 'DSY': 'Dassault Systèmes', 'OVH': 'OVHcloud', 'CAP': 'Capgemini', 'ENGI': 'Engie',
    'VLTSA': 'Voltalia',
}
# ADR cotés aux USA (mentions Reddit mesurables) ; autres actions françaises : mentions « – ».
FR_ADR = {'TTE': 'TTE', 'SAN': 'SNY'}


def clip(x, a=0.0, b=100.0):
    return float(max(a, min(b, x)))


def universe():
    d = json.loads((DATA / 'apex_achat_v2_pilot.json').read_text())
    out, seen = [], set()
    for sid, p in (d.get('pilotes') or {}).items():
        pays = p.get('pays') or ('USA' if sid.startswith('XL') else None)
        if pays not in ('USA', 'France'):
            continue
        for a in p.get('actions') or []:
            tv = a.get('tv')
            if not tv or tv in seen:
                continue
            seen.add(tv)
            t = a.get('ticker') or tv.split(':')[-1]
            yahoo = a.get('yahoo') or (t + '.PA' if pays == 'France' else t)
            if pays == 'USA':
                term, geo, ape = (US_TERM.get(t, a.get('nom') or t) + ' stock'), '', t
            else:
                term, geo, ape = FR_TERM.get(t, a.get('nom') or t), 'FR', FR_ADR.get(t)
            out.append({'tv': tv, 'ticker': t, 'yahoo': yahoo, 'nom': a.get('nom'), 'pays': pays,
                        'section': sid, 'term': term, 'geo': geo, 'ape': ape})
    # Actions détenues hors univers (Mes positions) : même collecte d'attention
    try:
        import score_held_equities as HE
        for a in HE.iter_held_equities():
            tv = a.get('tv')
            if not tv or tv in seen:
                continue
            seen.add(tv)
            t = a.get('ticker') or tv.split(':')[-1]
            yahoo = a.get('yahoo') or t
            if t == 'ENPH':
                term, geo, ape = 'Enphase stock', '', 'ENPH'
            else:
                term, geo, ape = (US_TERM.get(t, a.get('nom') or t) + ' stock'), '', t
            out.append({'tv': tv, 'ticker': t, 'yahoo': yahoo, 'nom': a.get('nom'), 'pays': 'USA',
                        'section': 'held', 'term': term, 'geo': geo, 'ape': ape})
    except Exception:
        pass
    return out


# ---------- volume ----------
def volume_all(syms):
    import yfinance as yf
    res = {}
    for i in range(0, len(syms), 25):
        chunk = syms[i:i + 25]
        try:
            df = yf.download(chunk, period='2y', interval='1wk', auto_adjust=False,
                             group_by='ticker', progress=False, threads=True)
        except Exception as e:
            print('yfinance', e); continue
        for s in chunk:
            try:
                v = (df[s]['Volume'] if len(chunk) > 1 else df['Volume']).dropna()
            except Exception:
                continue
            v = v[v > 0]
            if len(v) and (pd.Timestamp.now(tz=v.index.tz) - v.index[-1]).days < 7:
                v = v.iloc[:-1]
            if len(v) < 30:
                continue
            r = float(v.iloc[-4:].mean() / v.iloc[-52:].mean())
            res[s] = {'ratio': round(r, 3), 'score': round(clip(50 + 50 * math.log2(r)), 1),
                      'series': [float(x) for x in v.iloc[-64:]]}
    return res


# ---------- Google Trends ----------
def _tr_file(term, geo):
    safe = ''.join(c if c.isalnum() else '_' for c in f'{geo}_{term}')
    return TR_CACHE / f'{ISOW}_{safe}.json'


_TR = {'sess': None}


def _session(geo):
    from pytrends.request import TrendReq
    if _TR['sess'] is None:
        _TR['sess'] = TrendReq(hl='en-US', tz=0, timeout=(10, 30))
    return _TR['sess']


def trends_fetch(term, geo, deadline, tries=3):
    """Une requête Google Trends (5 ans hebdo). Session réutilisée ; après un 429, pause puis nouvelle session.
    Pas d'invention : un terme resté bloqué vaut None et sera repris au passage suivant (cache de la semaine)."""
    fn = _tr_file(term, geo)
    if fn.exists():
        d = json.loads(fn.read_text())
        return d.get('values'), 'cache'
    err = None
    for i in range(tries):
        if time.time() > deadline:
            return None, 'temps écoulé (reprise au prochain passage)'
        try:
            p = _session(geo)
            p.build_payload([term], timeframe='today 5-y', geo=geo)
            df = p.interest_over_time()
            time.sleep(PAUSE)
            if df.empty:
                fn.write_text(json.dumps({'values': [], 'term': term, 'geo': geo}))
                return [], 'vide'
            s = df[term].astype(float)
            if 'isPartial' in df and bool(df['isPartial'].iloc[-1]):
                s = s.iloc[:-1]
            vals = [float(x) for x in s]
            fn.write_text(json.dumps({'values': vals, 'term': term, 'geo': geo,
                                      'last': str(s.index[-1].date()), 'fetched': TODAY.isoformat()}))
            return vals, 'ok'
        except Exception as e:
            err = str(e)[:70]
            _TR['sess'] = None
            time.sleep(BACKOFF * (i + 1))
    return None, f'bloqué ({err})'


def trends_score(vals):
    if not vals or len(vals) < 60 or max(vals) <= 0:
        return None
    s = pd.Series(vals)
    r4 = s.rolling(4).mean().dropna()
    cur = r4.iloc[-1]
    pct = (r4 < cur).mean() * 100 + (r4 == cur).mean() * 50
    return {'last4': round(float(cur), 1), 'med5y': round(float(s.median()), 1), 'score': round(float(pct), 1)}


# ---------- mentions ----------
def apewisdom_today():
    fn = APE_DIR / f'{TODAY.isoformat()}.json'
    if fn.exists():
        return json.loads(fn.read_text()), 'cache'
    out, page, pages = {}, 1, 1
    try:
        while page <= pages:
            d = requests.get(f'https://apewisdom.io/api/v1.0/filter/all-stocks/page/{page}', timeout=20).json()
            pages = d.get('pages', 1)
            for r in d.get('results') or []:
                out[r['ticker']] = r
            page += 1
            time.sleep(1)
    except Exception as e:
        return None, f'échec ({e})'
    fn.write_text(json.dumps({'date': TODAY.isoformat(), 'source': 'apewisdom.io all-stocks', 'tickers': out},
                             ensure_ascii=False))
    return {'date': TODAY.isoformat(), 'tickers': out}, 'ok'


def mentions_score(tk, ape):
    if not tk or not ape:
        return None
    T = ape['tickers']
    top = max(T.values(), key=lambda r: r['mentions'])
    ref = (top['mentions'] + (top.get('mentions_24h_ago') or 0)) / 2
    r = T.get(tk)
    m = ((r['mentions'] + (r.get('mentions_24h_ago') or 0)) / 2) if r else 0.0
    return {'m24': r['mentions'] if r else 0, 'm24_prev': (r.get('mentions_24h_ago') or 0) if r else 0,
            'rang': r['rank'] if r else None,
            'score': round(clip(100 * math.log1p(m) / math.log1p(ref)), 1)}


def persist_score(vol_series, tr_vals):
    parts = []
    for s in (vol_series, tr_vals):
        if not s or len(s) < 30:
            continue
        s = pd.Series(s)
        sm = s.rolling(3).mean()
        med = s.iloc[-52:].median()
        parts.append(float((sm.iloc[-12:] > med).mean() * 100))
    return round(float(np.mean(parts)), 1) if parts else None


def main():
    use_tr = '--no-trends' not in sys.argv
    mx = 150
    if '--max-minutes' in sys.argv:
        mx = float(sys.argv[sys.argv.index('--max-minutes') + 1])
    deadline = time.time() + mx * 60
    U = universe()
    print('univers', len(U), 'actions USA + France', flush=True)
    ape, ape_st = apewisdom_today()
    print('ApeWisdom', ape_st, flush=True)
    vol = volume_all([u['yahoo'] for u in U])
    print('volume', len(vol), '/', len(U), flush=True)
    tr_res = {}
    if use_tr:
        for passe in (1, 2, 3):
            todo = [u for u in U if tr_res.get(u['tv'], (None, ''))[0] is None and not str(tr_res.get(u['tv'], (None, ''))[1]).startswith('vide')]
            if not todo or time.time() > deadline:
                break
            print(f'Trends passage {passe} : {len(todo)} terme(s)', flush=True)
            for u in todo:
                tr_res[u['tv']] = trends_fetch(u['term'], u['geo'], deadline)
                print('  trends', u['tv'], u['term'], tr_res[u['tv']][1], flush=True)
    by_tv = {}
    for u in U:
        tr_vals, tr_st = tr_res.get(u['tv'], (None, 'désactivé'))
        tr = trends_score(tr_vals)
        me = mentions_score(u['ape'], ape)
        vo = vol.get(u['yahoo'])
        pe = persist_score(vo and vo['series'], tr_vals if tr else None)
        sc = {'trends': tr and tr['score'], 'mentions': me and me['score'],
              'volume': vo and vo['score'], 'persist': pe}
        avail = {k: v for k, v in sc.items() if v is not None}
        wa = sum(W[k] for k in avail)
        att = round(sum(W[k] * v for k, v in avail.items()) / wa, 1) if wa else None
        h = None if att is None else int(round((50 - att) * H_FACTOR))
        manq = [k for k, v in sc.items() if v is None]
        by_tv[u['tv']] = {
            'ticker': u['ticker'], 'yahoo': u['yahoo'], 'nom': u['nom'], 'pays': u['pays'],
            'attention': att, 'H': h, 'poids_dispo': round(wa, 2),
            'composantes': sc,
            'trends': {'terme': u['term'], 'geo': u['geo'] or 'monde', 'statut': tr_st, **(tr or {})},
            'mentions': {'ticker': u['ape'], **(me or {})},
            'volume': {'ratio_4s_52s': vo and vo['ratio']},
            'manquants': manq + ['X', 'StockTwits'],
        }
        print(f"{u['tv']:18s} att={att} H={h} {sc} tr={tr_st}", flush=True)
    n_ok = sum(1 for r in by_tv.values() if r['attention'] is not None)
    out = {
        'generated': dt.datetime.now().strftime('%Y-%m-%d %H:%M') + ' Europe/Paris',
        'semaine': ISOW,
        'definition': ("Attention long swing 0–100 : Google Trends 35 %, mentions 35 %, volume relatif 20 %, "
                       "persistance 10 % ; poids recalculés sur les sources disponibles. "
                       "H = (50 − attention) × 0,6, de −30 à +30, à contre-courant. Ni technique, ni Fear & Greed, "
                       "ni signal d'achat / vente."),
        'poids': W, 'h_facteur': H_FACTOR,
        'sources': {'apewisdom': ape_st, 'apewisdom_date': (ape or {}).get('date'),
                    'x': 'non accessible', 'stocktwits': 'non accessible (403)'},
        'stats': {'n': len(by_tv), 'avec_H': n_ok, 'sans_H': len(by_tv) - n_ok,
                  'trends_ok': sum(1 for r in by_tv.values() if r['composantes']['trends'] is not None)},
        'by_tv': by_tv,
    }
    (DATA / 'attention_apex.json').write_text(json.dumps(out, ensure_ascii=False, indent=1) + '\n')
    hist = ADIR / 'historique'
    hist.mkdir(exist_ok=True)
    (hist / f'{TODAY.isoformat()}.json').write_text(json.dumps(
        {tv: {'attention': r['attention'], 'H': r['H'], **r['composantes']} for tv, r in by_tv.items()}))
    print('écrit', DATA / 'attention_apex.json', out['stats'], flush=True)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
