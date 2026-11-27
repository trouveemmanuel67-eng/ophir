#!/usr/bin/env python3
"""t686u (Emmanuel, 27/11/2026) : valorisation pour la note SHORT (« une bonne entreprise peut être trop chère »).

Pour chaque titre de l'univers large SHORT (S&P 500 + canadiennes NYSE + CFD Revolut, mêmes listes que
build_univers_short.py) : PER prévisionnel (forwardPE, consensus 12 mois) et PER courant (trailingPE), Yahoo Finance
(yfinance, Ticker.info). Puis médiane du PER par secteur Yahoo sur cet univers (PER prévisionnel, repli PER courant ;
PER ≤ 0 ou absent : ignoré, aucune invention).
→ data/valo_short.json (versionné) : {'secteurs': {secteur: {'mediane_per': x, 'n': k}}, 'by_yahoo': {...}}.
t687u (27/11/2026) : + short interest (shortPercentOfFloat en % du flottant, shortRatio = jours pour couvrir,
dateShortInterest = date de relevé FINRA/bourses, publié deux fois par mois, donc en retard).
Régénérable : python3 src/fetch_valo_short.py
"""
from __future__ import annotations
import json, os, statistics, sys, time, datetime as D
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from zoneinfo import ZoneInfo

DIR = Path(__file__).resolve().parent
ROOT = Path(os.environ.get('APEX_ROOT') or DIR.parent)
sys.path[:0] = [str(DIR), str(ROOT)]
import build_univers_short as B  # noqa: E402

OUT = ROOT / 'data' / 'valo_short.json'


def per_of(fwd, trl):
    """PER retenu : prévisionnel s'il est > 0, sinon courant s'il est > 0, sinon None."""
    for v, src in ((fwd, 'prévisionnel'), (trl, 'courant')):
        if isinstance(v, (int, float)) and v > 0:
            return float(v), src
    return None, None


def one(y):
    import yfinance as yf
    for k in range(3):
        try:
            i = yf.Ticker(y).info or {}
            fwd, trl = B.clean(i.get('forwardPE')), B.clean(i.get('trailingPE'))
            per, src = per_of(fwd, trl)
            spf, sr, dsi = B.clean(i.get('shortPercentOfFloat')), B.clean(i.get('shortRatio')), B.clean(i.get('dateShortInterest'))
            return y, {'short_pct_float': None if spf is None else round(float(spf) * 100, 2),
                       'short_ratio': None if sr is None else round(float(sr), 2),
                       'date_short': None if not dsi else D.datetime.fromtimestamp(int(dsi), ZoneInfo('UTC')).strftime('%Y-%m-%d'),
                       'sector': i.get('sector'), 'forward_pe': None if fwd is None else round(float(fwd), 2),
                       'trailing_pe': None if trl is None else round(float(trl), 2),
                       'per': None if per is None else round(per, 2), 'per_source': src}
        except Exception:
            time.sleep(2 + 3 * k)
    return y, None


def main():
    cfd = json.loads((ROOT / 'config' / 'revolut_cfd_confirmes.json').read_text(encoding='utf-8'))['symboles']
    spy, asof = B.spy_tickers()
    base = {B.ysym(t) for t in spy} | {B.ysym(t) for t in B.CANADA}
    base |= {B.ysym(t) for t in cfd if t.isalpha() and len(t) <= 5 and not B.is_crypto(t)}
    with ThreadPoolExecutor(8) as ex:
        res = dict(r for r in ex.map(one, sorted(base)) if r[1])
    sect = {}
    for y, r in res.items():
        if r.get('sector') and r.get('per'):
            sect.setdefault(r['sector'], []).append(r['per'])
    med = {s: {'mediane_per': round(statistics.median(v), 2), 'n': len(v)} for s, v in sorted(sect.items())}
    doc = {'genere': D.datetime.now(ZoneInfo('Europe/Paris')).strftime('%Y-%m-%d %H:%M'), 'zone': 'Europe/Paris',
           'source': f'Yahoo Finance (yfinance, Ticker.info : forwardPE, trailingPE, sector, shortPercentOfFloat, shortRatio, dateShortInterest) ; univers SPY au {asof} + canadiennes NYSE + CFD Revolut',
           'regle': 'PER retenu = prévisionnel (12 mois) s’il est > 0, sinon courant s’il est > 0 ; médiane par secteur Yahoo',
           'n': len(res), 'secteurs': med, 'by_yahoo': res}
    OUT.write_text(json.dumps(doc, ensure_ascii=False, separators=(',', ':')) + '\n', encoding='utf-8')
    print('écrit', OUT, len(res), json.dumps(med, ensure_ascii=False))


if __name__ == '__main__':
    main()
