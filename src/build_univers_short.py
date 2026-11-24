#!/usr/bin/env python3
"""t534u (Emmanuel, 24/11/2026) : univers propre des Meilleurs SHORT, à la place de la watchlist APEX.

50 actions cotées au NYSE (y compris les sociétés canadiennes cotées au NYSE), négociables en CFD chez Revolut,
en surachat sur le RSI 14 HEBDO (> 70 en priorité ; complété par RSI ≥ 65 si besoin) et dont la santé
financière se dégrade (révisions de BPA en baisse, CA en recul, marges en recul, dette en hausse, FCF en baisse…).

Étapes (régénérable : python3 src/build_univers_short.py [--force]) :
  1. Univers large : composants du S&P 500 (fichier officiel SPDR SPY, State Street) + grandes canadiennes cotées
     au NYSE (liste CANADA ci-dessous) + actions déjà négociées en CFD sur le compte Revolut
     (config/revolut_cfd_confirmes.json).
  2. Bougies hebdo Yahoo (historique max, period1/period2) → data/short_cache/ (non versionné).
     Place vérifiée dans les métadonnées Yahoo : exchangeName == 'NYQ' (NYSE). Les autres places sont écartées.
  3. RSI 14 sur clôtures HEBDO clôturées (même moteur que le site : ind_core.rsi, yahoo_week).
  4. Pour les RSI ≥ 65 : fondamentaux Yahoo (yfinance) + signes de dégradation ; tri : RSI > 70 d'abord,
     puis score de dégradation décroissant, puis RSI décroissant. On retient N = 50 titres ayant au moins un signe.
  5. CFD Revolut : « confirmé » si le symbole figure dans config/revolut_cfd_confirmes.json, sinon « à vérifier ».
→ config/univers_short.json (+ les métriques fondamentales nécessaires à la note SHORT).
"""
from __future__ import annotations
import json, math, os, sys, time, urllib.parse, urllib.request, datetime as D
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from zoneinfo import ZoneInfo

DIR = Path(__file__).resolve().parent
ROOT = Path(os.environ.get('APEX_ROOT') or DIR.parent)
sys.path[:0] = [str(DIR), str(ROOT)]
import ind_core as K  # noqa: E402
import yahoo_week as YW  # noqa: E402

PARIS = ZoneInfo('Europe/Paris')
NOW = D.datetime.now(PARIS)
CACHE = ROOT / 'data' / 'short_cache'
CACHE.mkdir(parents=True, exist_ok=True)
OUT = ROOT / 'config' / 'univers_short.json'
N = 50
RSI_SUR = 70.0
RSI_MIN = 65.0
RSI_PLANCHER = 50.0  # plancher du complément (jamais sous 50)
UA = {'User-Agent': 'Mozilla/5.0'}
FORCE = '--force' in sys.argv

# Grandes sociétés canadiennes cotées au NYSE (la place est revérifiée dans les métadonnées Yahoo).
CANADA = ['RY', 'TD', 'BMO', 'BNS', 'CM', 'MFC', 'SLF', 'ENB', 'TRP', 'CNQ', 'SU', 'CVE', 'IMO', 'CP', 'CNI', 'NTR',
          'TECK', 'FTS', 'EMA', 'BN', 'BAM', 'BEP', 'BEPC', 'BIP', 'BIPC', 'BCE', 'TU', 'RCI', 'CCJ', 'AEM', 'WPM',
          'FNV', 'KGC', 'B', 'AGI', 'QSR', 'GIB', 'WCN', 'TFII', 'MGA', 'PBA', 'AQN', 'GFL', 'CLS', 'CAE', 'TAC',
          'BTE', 'VET', 'OVV', 'WFG', 'TRI', 'SHOP', 'ATS', 'ERO', 'NGD', 'IAG', 'EQX', 'OR', 'PAAS', 'FSV', 'LSPD',
          'DOO', 'H', 'TECK', 'ENB', 'CNQ']


def spy_tickers():
    import openpyxl
    p = CACHE / 'spy_holdings.xlsx'
    try:
        raw = urllib.request.urlopen(urllib.request.Request(
            'https://www.ssga.com/library-content/products/fund-data/etfs/us/holdings-daily-us-en-spy.xlsx', headers=UA), timeout=40).read()
        p.write_bytes(raw)
    except Exception as e:
        print('SPY holdings : téléchargement impossible, cache utilisé', e)
    ws = openpyxl.load_workbook(p, read_only=True).active
    rows = list(ws.iter_rows(values_only=True))
    asof = rows[2][1]
    hdr = [i for i, r in enumerate(rows) if r and r[0] == 'Name'][0]
    t = [r[1] for r in rows[hdr + 1:] if r and r[1] and isinstance(r[4], (int, float)) and r[1] not in ('-', 'CASH_USD')]
    return sorted(set(t)), asof


def ysym(t):
    return t.replace('.', '-').replace('/', '-')


def chart_path(y):
    return CACHE / f'yahoo_1wk_{urllib.parse.quote(y, safe="")}.json'


def stale(p):
    if not p.exists() or p.stat().st_size < 1500:
        return True
    mt = D.datetime.fromtimestamp(p.stat().st_mtime, PARIS)
    today = NOW.date()
    last_fri = today - D.timedelta(days=(today.weekday() - 4) % 7)
    if last_fri == today:
        last_fri -= D.timedelta(days=7)
    return mt < D.datetime.combine(last_fri + D.timedelta(days=1), D.time(0, 0), tzinfo=PARIS)


def fetch_chart(y):
    p = chart_path(y)
    if not FORCE and not stale(p):
        return y, True
    p2 = int(time.time())
    for k in range(3):
        try:
            r = urllib.request.urlopen(urllib.request.Request(
                f'https://query2.finance.yahoo.com/v8/finance/chart/{urllib.parse.quote(y)}?period1=-2208988800&period2={p2}&interval=1wk&events=history',
                headers=UA), timeout=30).read()
            p.write_bytes(r)
            return y, True
        except Exception as e:
            if '404' in str(e):
                return y, False
            time.sleep(2 + 3 * k)
    return y, False


def weekly_info(y):
    p = chart_path(y)
    if not p.exists():
        return None
    try:
        raw = json.loads(p.read_text())
        meta = raw['chart']['result'][0]['meta']
        bars, _m = YW.parse_yahoo_weekly(str(p), now=NOW)
    except Exception:
        return None
    closed = [b for b in bars if b.get('closed') and b.get('close') and b['close'] > 0]
    if len(closed) < 52:
        return None
    c = [b['close'] for b in closed]
    r = K.rsi(c)
    return {'exchange': meta.get('exchangeName'), 'nom': meta.get('longName') or meta.get('shortName'),
            'currency': meta.get('currency'), 'rsi': None if r[-1] is None else round(r[-1], 1),
            'rsi_sem_sup70': _streak(r, 70),
            'date_cloture': closed[-1]['date'], 'close': c[-1]}


def _streak(r, th):
    n = 0
    for v in reversed(r):
        if v is not None and v > th:
            n += 1
        else:
            break
    return n


def clean(x):
    if hasattr(x, 'item'):
        x = x.item()
    if isinstance(x, float) and (math.isnan(x) or math.isinf(x)):
        return None
    return x


def _row(df, names):
    if df is None or getattr(df, 'empty', True):
        return None
    for n in names:
        if n in df.index:
            return [clean(v) for v in df.loc[n].tolist()]
    return None


def fondamentaux(y):
    """Métriques des 9 critères (mêmes clés que build_fondamentaux.py) + signes de dégradation."""
    import yfinance as yf
    for k in range(3):
        try:
            T = yf.Ticker(y)
            i = {k2: clean(v) for k2, v in (T.info or {}).items() if not isinstance(v, (list, dict))}
            break
        except Exception as e:
            i = {}
            time.sleep(3 + 3 * k)
    def safe(name):
        try:
            return getattr(T, name)
        except Exception:
            return None
    ee = safe('earnings_estimate'); re_ = safe('revenue_estimate'); et = safe('eps_trend')
    qi = safe('quarterly_income_stmt'); qb = safe('quarterly_balance_sheet'); ac = safe('cashflow'); qc = safe('quarterly_cashflow')

    def eg(p):
        try:
            r = ee.loc[p]; g = clean(r.get('growth')); base = clean(r.get('yearAgoEps'))
            return None if g is None or base is None or base <= 0 else g * 100
        except Exception:
            return None

    def rg(p):
        try:
            g = clean(re_.loc[p].get('growth'))
            return None if g is None else g * 100
        except Exception:
            return None
    rev = i.get('totalRevenue'); eb = i.get('ebitda')
    m = {'nd_ebitda': ((i.get('totalDebt') or 0) - (i.get('totalCash') or 0)) / eb if eb and eb > 0 and i.get('totalDebt') is not None else None,
         'op_margin': i.get('operatingMargins') and i['operatingMargins'] * 100,
         'fcf_margin': (i['freeCashflow'] / rev * 100) if i.get('freeCashflow') is not None and rev else None,
         'roe': i.get('returnOnEquity') and i['returnOnEquity'] * 100, 'roa': i.get('returnOnAssets') and i['returnOnAssets'] * 100,
         'current': i.get('currentRatio'),
         'eps_0y': eg('0y'), 'eps_1y': eg('+1y'), 'rev_0y': rg('0y'), 'rev_1y': rg('+1y')}
    # --- signes de dégradation ---
    sig, det = 0.0, []

    def add(w, txt):
        nonlocal sig
        sig += w
        det.append(txt)
    # 1. révisions de BPA (consensus actuel vs il y a 90 jours), exercice en cours et suivant
    try:
        for p, lab in (('0y', 'BPA an'), ('+1y', 'BPA an+1')):
            cur = clean(et.loc[p].get('current')); old = clean(et.loc[p].get('90daysAgo'))
            if cur is not None and old not in (None, 0) and (cur - old) / abs(old) < -0.02:
                add(1, f'révision {lab} {100 * (cur - old) / abs(old):+.0f} % sur 90 j')
    except Exception:
        pass
    # 2. croissance attendue négative
    if m['eps_0y'] is not None and m['eps_0y'] < 0:
        add(1, f"BPA attendu {m['eps_0y']:+.0f} % cette année")
    elif m['eps_1y'] is not None and m['eps_1y'] < 0:
        add(1, f"BPA attendu {m['eps_1y']:+.0f} % l'an prochain")
    if m['rev_0y'] is not None and m['rev_0y'] < 0:
        add(1, f"CA attendu {m['rev_0y']:+.0f} % cette année")
    # 3. résultats trimestriels en recul sur un an (Yahoo)
    eg_q = i.get('earningsQuarterlyGrowth') if i.get('earningsQuarterlyGrowth') is not None else i.get('earningsGrowth')
    if eg_q is not None and eg_q < -0.05:
        add(1, f'bénéfice trim. {eg_q * 100:+.0f} % a/a')
    if i.get('revenueGrowth') is not None and i['revenueGrowth'] < 0:
        add(0.5, f"CA trim. {i['revenueGrowth'] * 100:+.0f} % a/a")
    # 4. marge opérationnelle trimestrielle en recul (dernier trimestre vs même trimestre un an plus tôt)
    try:
        oi = _row(qi, ['Operating Income', 'EBIT']); tr = _row(qi, ['Total Revenue', 'Operating Revenue'])
        if oi and tr and len(oi) >= 5 and len(tr) >= 5 and tr[0] and tr[4] and oi[0] is not None and oi[4] is not None:
            m0, m4 = oi[0] / tr[0] * 100, oi[4] / tr[4] * 100
            if m0 < m4 - 1:
                add(1, f'marge op. {m4:.0f} → {m0:.0f} % (trim. a/a)')
    except Exception:
        pass
    # 5. dette totale en hausse (> +10 % sur un an, bilan trimestriel)
    try:
        dt = _row(qb, ['Total Debt'])
        if dt and len(dt) >= 5 and dt[0] and dt[4] and dt[0] > dt[4] * 1.10:
            add(1, f'dette {100 * (dt[0] / dt[4] - 1):+.0f} % sur 1 an')
        elif dt and len(dt) >= 4 and dt[0] and dt[3] and dt[0] > dt[3] * 1.10:
            add(1, f'dette {100 * (dt[0] / dt[3] - 1):+.0f} % sur 3 trim.')
    except Exception:
        pass
    # 6. FCF en baisse (dernier exercice vs précédent) ou négatif
    try:
        fc = _row(ac, ['Free Cash Flow'])
        if fc and len(fc) >= 2 and fc[0] is not None and fc[1] is not None:
            if fc[0] < 0:
                add(1, 'FCF annuel négatif')
            elif fc[1] > 0 and fc[0] < fc[1] * 0.85:
                add(1, f'FCF {100 * (fc[0] / fc[1] - 1):+.0f} % sur l\'exercice')
    except Exception:
        pass
    # 7. levier excessif
    if m['nd_ebitda'] is not None and m['nd_ebitda'] > 4:
        add(0.5, f"dette nette/EBITDA {m['nd_ebitda']:.1f}")
    ind = (i.get('industry') or '')
    return {'metrics': {k: (None if v is None else round(float(v), 3)) for k, v in m.items()},
            'degradation': {'score': round(sig, 1), 'signes': det},
            'country': i.get('country'), 'sector': i.get('sector'), 'industry': ind,
            'is_bank': 'Banks' in ind, 'nom': i.get('longName') or i.get('shortName'),
            'market_cap': i.get('marketCap'), 'exchange_info': i.get('exchange')}


def main():
    cfd = json.loads((ROOT / 'config' / 'revolut_cfd_confirmes.json').read_text(encoding='utf-8'))['symboles']
    spy, asof = spy_tickers()
    base = {}
    for t in spy:
        base.setdefault(ysym(t), {'ticker': t, 'origine': 'S&P 500'})
    for t in CANADA:
        base.setdefault(ysym(t), {'ticker': t, 'origine': 'Canada (NYSE)'})
    for t in cfd:
        if t.isalpha() and len(t) <= 5:
            base.setdefault(ysym(t), {'ticker': t, 'origine': 'CFD Revolut déjà négocié'})
    print('univers large', len(base), 'SPY au', asof, flush=True)
    with ThreadPoolExecutor(6) as ex:
        res = list(ex.map(fetch_chart, sorted(base)))
    print('bougies ok', sum(1 for _, ok in res if ok), flush=True)
    nyse, rsi_all = {}, {}
    for y, ok in res:
        w = weekly_info(y) if ok else None
        if not w:
            continue
        if w['exchange'] != 'NYQ':
            continue
        nyse[y] = {**base[y], **w}
    n70 = [y for y, w in nyse.items() if (w['rsi'] or 0) > RSI_SUR]
    n65 = [y for y, w in nyse.items() if (w['rsi'] or 0) >= RSI_MIN]
    print('NYSE', len(nyse), 'RSI>70', len(n70), 'RSI>=65', len(n65), flush=True)
    # Fondamentaux par RSI hebdo décroissant ; si moins de N titres RSI ≥ 65 avec dégradation, on complète avec
    # les RSI hebdo suivants (palier « complément RSI < 65 », signalé), jusqu'à N titres ou RSI < RSI_PLANCHER.
    cands, elig = {}, []
    for y in sorted(nyse, key=lambda y: -(nyse[y]['rsi'] or 0)):
        r = nyse[y]['rsi'] or 0
        if r < RSI_MIN and (len(elig) >= N or r < RSI_PLANCHER):
            break
        try:
            f = fondamentaux(y)
        except Exception as e:
            print('fond ERR', y, e)
            continue
        c = {**nyse[y], **f}
        c['palier'] = 'RSI > 70' if r > RSI_SUR else ('RSI 65–70' if r >= RSI_MIN else 'complément RSI < 65')
        cands[y] = c
        if f['degradation']['score'] >= 1:
            elig.append(c)
        print(f"{y:6} RSI {r:5} deg {f['degradation']['score']:3} {f['country']} {'; '.join(f['degradation']['signes'])}", flush=True)
        time.sleep(0.3)
    rang = {'RSI > 70': 0, 'RSI 65–70': 1, 'complément RSI < 65': 2}
    elig.sort(key=lambda c: (rang[c['palier']], -c['degradation']['score'] if c['palier'] != 'complément RSI < 65' else -c['rsi'], -c['rsi']))
    retenus = elig[:N]
    for c in retenus:
        t = c['ticker']
        c['tv'] = 'NYSE:' + t.replace('-', '.')
        c['cfd_revolut'] = 'confirmé' if t in cfd else 'à vérifier'
        c['canada'] = (c.get('country') == 'Canada') or c['origine'].startswith('Canada')
        c['yahoo'] = ysym(t)
    doc = {
        'regle': "t534u : 50 actions cotées au NYSE (canadiennes comprises), CFD Revolut, RSI hebdo en surachat, santé en dégradation",
        'genere': NOW.strftime('%Y-%m-%d %H:%M'), 'zone': 'Europe/Paris',
        'script': 'src/build_univers_short.py',
        'sources': {'sp500': f'SPDR SPY holdings (State Street), au {asof}', 'cours': 'Yahoo Finance, bougies hebdo clôturées',
                    'fondamentaux': 'Yahoo Finance (yfinance) : info, estimations, tendance BPA, comptes trimestriels / annuels',
                    'cfd': 'config/revolut_cfd_confirmes.json (relevé CFD Revolut)'},
        'stats': {'univers_large': len(base), 'nyse': len(nyse), 'rsi_sup_70': len(n70), 'rsi_sup_65': len(n65),
                  'eligibles_degradation': len(elig), 'retenus': len(retenus),
                  'retenus_rsi_sup_70': sum(1 for c in retenus if c['rsi'] > RSI_SUR),
                  'retenus_rsi_65_70': sum(1 for c in retenus if RSI_MIN <= c['rsi'] <= RSI_SUR),
                  'retenus_complement_sous_65': sum(1 for c in retenus if c['rsi'] < RSI_MIN),
                  'rsi_min_retenu': min((c['rsi'] for c in retenus), default=None),
                  'cfd_confirmes': sum(1 for c in retenus if c['cfd_revolut'] == 'confirmé')},
        'rsi_seuil': RSI_SUR, 'rsi_min_complement': RSI_MIN, 'n': N,
        'actions': [{k: c.get(k) for k in ('tv', 'ticker', 'yahoo', 'nom', 'origine', 'country', 'canada', 'sector', 'industry', 'is_bank',
                                            'market_cap', 'rsi', 'rsi_sem_sup70', 'palier', 'date_cloture', 'close', 'degradation', 'metrics', 'cfd_revolut')}
                    for c in retenus],
    }
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    print('écrit', OUT, doc['stats'])


if __name__ == '__main__':
    main()
