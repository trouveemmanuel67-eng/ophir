"""Onglet Crypto · fiches APEX Achat / Vente pour BTC, ETH, XRP, SOL et MSTR (proxy bitcoin).

Même méthode et pondérations que l'onglet Actions (src/ind_core.py, 17/11/2026) : Elliott 15 %,
Fibonacci 15 %, Charte graphique 20 % (src/charte.py), Divergence RSI / MACD weekly 10 % (seulement si
divergence récente), puis RSI 6, MACD 6, MM40 6, distance au plus haut 52 semaines 6, momentum 6,
force relative vs S&P 500 6 et sentiment technique contrarien 4 sur les 40 % restants.
Indicateurs hebdomadaires sur bougies clôturées. Fibonacci lu sur les corps ; structure d'Elliott
de la Charte graphique lue sur les mèches. CCI 20 : en zone ±100, critère facultatif 6 % (même formule et mêmes seuils que CCI_S, ligne violette = +100).

Sources : Binance (BTC/USDT, ETH/USDT, bougies 1w) ; Yahoo Finance (XRP-USD, SOL-USD, MSTR, S&P 500) ;
CoinMetrics (préfixe Fibonacci BTC/ETH/XRP, historique plus long que Binance / Yahoo) ;
alternative.me (Fear & Greed, contexte, hors note).

-> data/crypto_fiches.json  (inclus ensuite dans tabs_data.json)
"""
import os as _os
_APEX_ROOT = _os.path.abspath(_os.environ.get('APEX_ROOT') or _os.path.join(_os.path.dirname(__file__), '..'))
import elliott_zones as EZ
import json, os, sys, math, datetime as D, statistics as st
from zoneinfo import ZoneInfo
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import elliott as E, ind_core as K, fibo as FB

B = _APEX_ROOT + '/data/'
NOW = D.datetime.now(ZoneInfo('Europe/Paris'))
TODAY = NOW.date()
f1 = K.f1
fs = K.fs
FNG_FR = {
    'Extreme Fear': 'Peur extrême', 'Fear': 'Peur', 'Neutral': 'Neutre',
    'Greed': 'Avidité', 'Extreme Greed': 'Avidité extrême',
}

def mtime(rel):
    p = B + rel
    if not os.path.exists(p):
        return None
    return D.datetime.fromtimestamp(os.path.getmtime(p), ZoneInfo('Europe/Paris')).strftime('%Y-%m-%d %H:%M')

HL = {}
def binance_weeks(sym):
    HL[sym] = {}
    """Semaines Binance Mon 00:00 UTC → dimanche, datées au vendredi, clôturées uniquement pour le score."""
    k = json.load(open(B + f'crypto/binance_{sym}_1w.json'))
    nowms = D.datetime.now(D.timezone.utc).timestamp() * 1000
    w, opens, live = [], {}, None
    for x in k:
        o, c = float(x[1]), float(x[4])
        mon = D.datetime.fromtimestamp(x[0] / 1000, D.timezone.utc).date()
        fri = mon + D.timedelta(days=4)
        closed = x[6] < nowms
        if closed:
            w.append((fri.isoformat(), c, True))
            opens[fri.isoformat()] = o
            HL[sym][fri.isoformat()] = (float(x[2]), float(x[3]))
        else:
            live = {'date': fri.isoformat(), 'close': c, 'open_date': mon.isoformat()}
    return w, opens, live

def yahoo_weeks_safe(path, close_after='friday'):
    """Bougies Yahoo hebdo officielles (horodatage 00:00) ; le point live n'écrase jamais une semaine déjà clôturée.
    close_after='friday' : actions (semaine close le vendredi).
    close_after='sunday' : crypto 24/7 (semaine Yahoo lun–dim UTC, close seulement après le dimanche)."""
    d = json.load(open(path))['chart']['result'][0]
    ts, q, meta = d['timestamp'], d['indicators']['quote'][0], d['meta']
    tz = ZoneInfo(meta.get('exchangeTimezoneName') or 'UTC')
    opens_raw = q.get('open') or [None] * len(ts)
    wk, opens, live = {}, {}, None
    for t, o, v in zip(ts, opens_raw, q['close']):
        if v is None or v <= 0:
            continue
        loc = D.datetime.fromtimestamp(t, tz)
        ld = loc.date()
        if loc.hour == 0 and loc.minute == 0:
            fri = ld + D.timedelta(days=(4 - ld.weekday()) % 7)
            wk[fri] = v
            opens[fri.isoformat()] = o if (o and o > 0) else None
        else:
            mon = ld - D.timedelta(days=ld.weekday())
            fri = mon + D.timedelta(days=4)
            live = (fri, v, o if (o and o > 0) else None)
    # dimanche = vendredi + 2 ; une semaine crypto n'est close que le lundi suivant
    end = (lambda fri: fri + D.timedelta(days=2)) if close_after == 'sunday' else (lambda fri: fri)
    if live is not None:
        fri, v, o = live
        if TODAY <= end(fri):  # semaine en cours uniquement
            wk[fri] = v
            opens[fri.isoformat()] = o
    out = [(f.isoformat(), wk[f], TODAY > end(f)) for f in sorted(wk)]
    return out, meta, opens

def cm_prefix(asset, ds0, c0):
    """Préfixe Fibonacci depuis CoinMetrics (quotidien → hebdo) avant la première semaine de la série."""
    p = B + f'crypto/coinmetrics_{asset}_daily.json'
    if not os.path.exists(p):
        return None
    wk = {}
    for x in json.load(open(p)):
        if not x.get('PriceUSD'):
            continue
        d = D.date.fromisoformat(x['time'][:10])
        mon = d - D.timedelta(days=d.weekday())
        fri = mon + D.timedelta(days=4)
        px = float(x['PriceUSD'])
        if fri not in wk:
            wk[fri] = [px, px]
        else:
            wk[fri][1] = px
    f0 = D.date.fromisoformat(ds0[:10])
    pre = [(f, oc[0], oc[1]) for f, oc in sorted(wk.items()) if f < f0]
    if not pre:
        return None
    k = 1.0
    if c0 and f0 in wk and wk[f0][1] > 0:
        k = c0 / wk[f0][1]
        if abs(k - 1) <= 0.02:
            k = 1.0
    return ([r[1] * k for r in pre], [r[2] * k for r in pre], [r[0].isoformat() for r in pre])

def cci20(op, c):
    """CCI 20 sur le prix typique des CORPS (haut = max(O,C), bas = min(O,C)), jamais les mèches."""
    hi, lo = E.bodies(op, c)
    tp = [(h + l + cl) / 3 for h, l, cl in zip(hi, lo, c)]
    n, out = 20, [None] * len(tp)
    for i in range(n - 1, len(tp)):
        w = tp[i - n + 1:i + 1]
        sma = sum(w) / n
        md = sum(abs(x - sma) for x in w) / n
        out[i] = 0.0 if md == 0 else (tp[i] - sma) / (0.015 * md)
    return out

def pivot_ext(vals, k, hi=True):
    out = []
    for i in range(k, len(vals) - k):
        if vals[i] is None:
            continue
        neigh = [vals[i + j] for j in range(-k, k + 1) if j and vals[i + j] is not None]
        if len(neigh) < 2 * k:
            continue
        if hi and all(vals[i] > x for x in neigh):
            out.append(i)
        if (not hi) and all(vals[i] < x for x in neigh):
            out.append(i)
    return out

def rsi_div(closes, rsi, dates, lookback=80, k=3):
    n = len(closes)
    if n < 20:
        return {'type': 'indisponible', 'texte': 'Historique insuffisant pour détecter une divergence RSI.'}
    i0 = max(0, n - lookback)
    ph = [i for i in pivot_ext(closes, k, True) if i >= i0 and rsi[i] is not None]
    pl = [i for i in pivot_ext(closes, k, False) if i >= i0 and rsi[i] is not None]
    bear = (len(ph) >= 2 and closes[ph[-1]] > closes[ph[-2]] and rsi[ph[-1]] < rsi[ph[-2]])
    bull = (len(pl) >= 2 and closes[pl[-1]] < closes[pl[-2]] and rsi[pl[-1]] > rsi[pl[-2]])
    bits = []
    typ = 'aucune'
    if bear:
        typ = 'baissière'
        a, b = ph[-2], ph[-1]
        bits.append(
            f"divergence baissière : plus haut de clôture plus élevé ({f1(closes[a], 2)} $ le {dates[a]} → "
            f"{f1(closes[b], 2)} $ le {dates[b]}) alors que le RSI 14 recule ({f1(rsi[a])} → {f1(rsi[b])})"
        )
    if bull:
        typ = 'haussière' if typ == 'aucune' else 'double'
        a, b = pl[-2], pl[-1]
        bits.append(
            f"divergence haussière : plus bas de clôture plus bas ({f1(closes[a], 2)} $ le {dates[a]} → "
            f"{f1(closes[b], 2)} $ le {dates[b]}) alors que le RSI 14 remonte ({f1(rsi[a])} → {f1(rsi[b])})"
        )
    if typ == 'aucune':
        if len(ph) < 2 and len(pl) < 2:
            return {'type': 'indisponible', 'texte': "Pas assez de pivots confirmés (3 semaines de chaque côté) sur 80 semaines pour juger d'une divergence RSI."}
        return {'type': 'aucune', 'texte': 'Aucune divergence RSI récente sur les pivots hebdomadaires confirmés (fenêtre de 80 semaines, corps via la clôture).'}
    return {'type': typ, 'texte': ' ; '.join(bits) + ' · pivots confirmés, à recouper sur TradingView.'}

def cci_zone(v):
    if v is None:
        return 'indisponible'
    if v >= 100:
        return 'surachat (≥ +100)'
    if v <= -100:
        return 'survente (≤ −100)'
    return 'zone neutre'

def elliott_comment(e):
    return EZ.commentaire(e)


def extra_indicators(w, opens):
    wc = [x for x in w if x[2]]
    ds = [x[0] for x in wc]
    c = [x[1] for x in wc]
    op = [opens.get(d) for d in ds]
    r = K.rsi(c)
    e12, e26 = K.ema(c, 12), K.ema(c, 26)
    m = [a - b for a, b in zip(e12, e26)]
    sg = K.ema(m, 9)
    h = [a - b for a, b in zip(m, sg)]
    cc = cci20(op, c)
    last = len(c) - 1
    rz = 'surachat (≥ 70)' if r[last] is not None and r[last] >= 70 else (
        'survente (≤ 30)' if r[last] is not None and r[last] <= 30 else ('zone neutre' if r[last] is not None else 'indisponible')
    )
    if last >= 1:
        cross = 'MACD au-dessus du signal' if m[last] >= sg[last] else 'MACD sous le signal'
        mom = 'histogramme en hausse' if h[last] > h[last - 1] else 'histogramme en baisse'
        macd_txt = f"{cross}, {mom}"
        hist_prev = h[last - 1]
    else:
        macd_txt, hist_prev = 'indisponible', None
    div = rsi_div(c, r, ds)
    cci_v = cc[last]
    return {
        'rsi': None if r[last] is None else round(r[last], 1),
        'rsi_zone': rz,
        'div': div,
        'macd': round(m[last], 2),
        'signal': round(sg[last], 2),
        'hist': round(h[last], 2),
        'hist_prev': None if hist_prev is None else round(hist_prev, 2),
        'macd_texte': macd_txt,
        'cci': None if cci_v is None else round(cci_v, 1),
        'cci_zone': cci_zone(cci_v),
        'cci_n': 20,
    }

def fng_at(series, date):
    """Dernière valeur Fear & Greed connue à la date de clôture hebdo (ou avant)."""
    ok = [x for x in series if x[0] <= date]
    return ok[-1] if ok else None

# ----- données de marché -----
spx_w, _ = K.yweekly(B + 'actions/yahoo_1wk_%5EGSPC.json')
spx = {d: v for d, v, c in spx_w if c}

fng_raw = json.load(open(B + 'crypto/alternative_fng.json'))['data']
fng_series = sorted(
    (D.datetime.fromtimestamp(int(x['timestamp']), D.timezone.utc).date().isoformat(),
     int(x['value']), x['value_classification'])
    for x in fng_raw
)

RISK_COMMON = (
    "Indicateur composite APEX, purement informatif. Ce n'est ni un conseil ni un signal d'ordre. "
    "Aucun rendement n'est promis. Les lectures d'Elliott et de Fibonacci sont automatiques et peuvent "
    "différer de TradingView."
)
RISK_CRYPTO = (
    "Les cryptoactifs peuvent perdre 50 à 80 % de leur valeur, de manière récurrente, n'ont pas de flux "
    "de trésorerie, et restent exposés au risque de liquidité, de garde et de réglementation."
)
RISK_MSTR = (
    "MSTR (Strategy, ex-MicroStrategy) est une action cotée, proxy imparfait du bitcoin : prime ou décote "
    "sur la valeur des bitcoins détenus, levier d'endettement, dilution, et risques propres à l'entreprise. "
    "Ce n'est pas du bitcoin au comptant. On n'entre jamais sur un plus haut historique."
)

ASSETS = [
    {
        'key': 'btc', 'sym': 'BTC', 'nom': 'Bitcoin',
        'sous': 'BTC/USDT · Binance',
        'kind': 'crypto',
        'src_name': 'Binance API /klines BTCUSDT 1w',
        'url': 'https://www.binance.com/fr/trade/BTC_USDT',
        'currency': 'USD',
        'unit': '$',
        'loader': 'binance', 'binance': 'BTCUSDT', 'cm': 'btc',
        'fsym': 'BTC-USD', 'syms': ['BITSTAMP:BTCUSD', 'BTC'],
        'retrieved_key': 'crypto/binance_BTCUSDT_1w.json',
        'risks': [RISK_COMMON, RISK_CRYPTO],
    },
    {
        'key': 'eth', 'sym': 'ETH', 'nom': 'Ether',
        'sous': 'ETH/USDT · Binance',
        'kind': 'crypto',
        'src_name': 'Binance API /klines ETHUSDT 1w',
        'url': 'https://www.binance.com/fr/trade/ETH_USDT',
        'currency': 'USD',
        'unit': '$',
        'loader': 'binance', 'binance': 'ETHUSDT', 'cm': 'eth',
        'fsym': 'ETH-USD', 'syms': ['BITSTAMP:ETHUSD', 'ETH'],
        'retrieved_key': 'crypto/binance_ETHUSDT_1w.json',
        'risks': [RISK_COMMON, RISK_CRYPTO],
    },
    {
        'key': 'xrp', 'sym': 'XRP', 'nom': 'XRP',
        'sous': 'XRP/USD · Yahoo Finance',
        'kind': 'crypto',
        'src_name': 'Yahoo Finance · XRP-USD',
        'url': 'https://finance.yahoo.com/quote/XRP-USD/history/',
        'currency': 'USD',
        'unit': '$',
        'loader': 'yahoo', 'yahoo': 'crypto/yahoo_1wk_XRP-USD.json',
        'cm': 'xrp',
        'fsym': 'XRP-USD', 'syms': ['CRYPTO:XRPUSD', 'XRP'],
        'tv': 'CRYPTO:XRPUSD',
        'close_after': 'sunday',
        'fibo_adjust_splits': False,
        'retrieved_key': 'crypto/yahoo_1wk_XRP-USD.json',
        'risks': [RISK_COMMON, RISK_CRYPTO],
    },
    {
        'key': 'sol', 'sym': 'SOL', 'nom': 'Solana',
        'sous': 'SOL/USD · Yahoo Finance',
        'kind': 'crypto',
        'src_name': 'Yahoo Finance · SOL-USD',
        'url': 'https://finance.yahoo.com/quote/SOL-USD/history/',
        'currency': 'USD',
        'unit': '$',
        'loader': 'yahoo', 'yahoo': 'crypto/yahoo_1wk_SOL-USD.json',
        'fsym': 'SOL-USD', 'syms': ['CRYPTO:SOLUSD', 'SOL'],
        'tv': 'CRYPTO:SOLUSD',
        'close_after': 'sunday',
        'fibo_adjust_splits': False,
        'retrieved_key': 'crypto/yahoo_1wk_SOL-USD.json',
        'risks': [RISK_COMMON, RISK_CRYPTO],
    },
    {
        'key': 'mstr', 'sym': 'MSTR', 'nom': 'Strategy (ex-MicroStrategy)',
        'sous': 'NASDAQ:MSTR · action, proxy bitcoin',
        'kind': 'action',
        'src_name': 'Yahoo Finance · MSTR',
        'url': 'https://finance.yahoo.com/quote/MSTR/history/',
        'currency': 'USD',
        'unit': '$',
        'loader': 'yahoo', 'yahoo': 'crypto/yahoo_1wk_MSTR.json',
        'fsym': 'MSTR', 'syms': ['NASDAQ:MSTR', 'MSTR'],
        'retrieved_key': 'crypto/yahoo_1wk_MSTR.json',
        'risks': [RISK_COMMON, RISK_MSTR],
    },
]

fiches = []
for cfg in ASSETS:
    live = None
    meta = {}
    if cfg['loader'] == 'binance':
        w, opens, live = binance_weeks(cfg['binance'])
    else:
        w, meta, opens = yahoo_weeks_safe(B + cfg['yahoo'], close_after=cfg.get('close_after', 'friday'))
        live_rows = [x for x in w if not x[2]]
        def pxround(v):
            return round(v, 4 if v < 2 else 2)
        live = {'date': live_rows[-1][0], 'close': pxround(live_rows[-1][1])} if live_rows else None
    wc = [x for x in w if x[2]]
    if len(wc) < 52:
        fiches.append({
            'key': cfg['key'], 'sym': cfg['sym'], 'nom': cfg['nom'], 'sous': cfg['sous'],
            'ok': False, 'raison': 'Historique hebdomadaire insuffisant (moins de 52 semaines clôturées).',
            'url': cfg['url'], 'src_name': cfg['src_name'],
            'retrieved': mtime(cfg['retrieved_key']),
            'risks': cfg['risks'],
        })
        continue
    ds0, c0 = wc[0][0], wc[0][1]
    fpre = None
    if cfg.get('cm'):
        fpre = cm_prefix(cfg['cm'], ds0, c0)
    if fpre is None and cfg.get('fsym'):
        fpre = FB.prefix(cfg['fsym'], ds0, c0)
    hl = HL.get(cfg['binance']) if cfg['loader'] == 'binance' else K.yhl(B + cfg['yahoo'])
    r = K.compute(w, spx, 'S&P 500', opens=opens, fsym=cfg.get('fsym'), fpre=fpre, hl=hl, syms=cfg.get('syms'), fibo_adjust_splits=cfg.get('fibo_adjust_splits', True))
    for block in (r['sent']['components'], r['av']['components']):
        for x in block:
            if x.get('name')=='Sentiment du secteur (lecture contrarienne)' or x.get('nom')=='Sentiment du secteur (lecture contrarienne)':
                if 'name' in x: x['name']='Sentiment technique (lecture contrarienne)'
                if 'nom' in x: x['nom']='Sentiment technique (lecture contrarienne)'
    if wc[-1][1] < 2:
        r['close'] = round(wc[-1][1], 4)
        if r.get('ath') and r['ath'].get('close') is not None and r['ath']['close'] < 2:
            r['ath']['close'] = round(r['ath']['close'], 4)
    ind = extra_indicators(w, opens)
    ell_c = elliott_comment(r.get('elliott'))
    fng = fng_at(fng_series, r['date'])
    # risques : ATH + textes fixes
    risks = list(r.get('warn') or []) + list(cfg['risks'])
    item = {
        'ok': True,
        'key': cfg['key'], 'sym': cfg['sym'], 'nom': cfg['nom'], 'sous': cfg['sous'],
        'kind': cfg['kind'], 'currency': cfg['currency'], 'unit': cfg['unit'],
        'tv': cfg.get('tv'),
        'date': r['date'], 'close': r['close'], 'first': r['first'], 'n': r['n'],
        'live': live, 'ath': r['ath'], 'dd52': r['dd52'], 'warn': r.get('warn') or [],
        'sent': r['sent'], 'av': r['av'],
        'elliott': r['elliott'], 'fibo': r['fibo'],
        'ind': ind, 'elliott_comment': ell_c,
        'fng': ({'date': fng[0], 'value': fng[1], 'label': FNG_FR.get(fng[2], fng[2])} if fng else None),
        'risks': risks,
        'url': cfg['url'], 'src_name': cfg['src_name'],
        'retrieved': mtime(cfg['retrieved_key']),
        'market_time': (
            D.datetime.fromtimestamp(meta['regularMarketTime'], ZoneInfo('Europe/Paris')).strftime('%Y-%m-%d %H:%M')
            if meta.get('regularMarketTime') else None
        ),
    }
    fiches.append(item)

out = {
    'generated': NOW.strftime('%Y-%m-%d %H:%M'),
    'benchmark': 'S&P 500',
    'assets': fiches,
    'method_sent': (
        "Indice composite APEX, non officiel, identique à celui des secteurs Actions. Six sous-scores de 0 à 100, "
        "poids égaux (1/6 chacun), calculés chaque semaine sur les clôtures hebdomadaires confirmées, sans données "
        "futures : (1) RSI 14 de Wilder, valeur brute ; (2) écart du cours à sa moyenne mobile 40 semaines ; "
        "(3) performance sur 26 semaines ; (4) force relative contre le S&P 500 sur 13 semaines ; "
        "(5) distance au plus haut des 52 dernières semaines ; (6) volatilité réalisée sur 13 semaines, inversée "
        "(forte volatilité = peur). Les sous-scores 2 à 6 sont des rangs percentiles sur les 5 dernières années "
        "(260 semaines). Zones : 0-24 peur extrême · 25-44 peur · 45-55 neutre · 56-75 avidité · 76-100 euphorie. "
        "Le Fear & Greed d'alternative.me est affiché pour le contexte, il n'entre pas dans ce sous-score."
    ),
    'method_av': (
        "Indice composite APEX, non officiel, mêmes pondérations que l'onglet Actions. Onze composantes notées de "
        "−100 à +100 puis pondérées : vagues d'Elliott selon la règle (15 % : pas d'entrée pendant une vague 5 ni "
        "tant que l'ABC qui suit n'est pas terminée ; entrées en fin de vague 4 ou en fin de vague C), retracement "
        "de Fibonacci du plus bas historique (base) au plus haut historique (ATH) sur les corps des bougies (15 % : "
        "plus le cours est bas dans le retracement, plus la note pousse à l'achat ; négative près de l'ATH ; "
        "plafonnée sous la base), Charte graphique (20 % : structure d'Elliott lue sur les mèches, vague 5 terminée "
        "ou nouveau sommet au-dessus de la 3 fortement négatif, fin de 4 ou de C positive, et figures chartistes weekly "
        "validées en clôture : épaule-tête-épaule, double sommet ou double creux, biseaux ; 0 si rien n'est détecté ; "
        "une lecture manuelle d'Emmanuel remplace la détection automatique), Divergence RSI / MACD weekly (10 % : −100 si "
        "baissière, +100 si haussière ; sans divergence récente, critère non compté et poids redistribué), "
        "RSI 14 hebdo (6 %), MACD 12/26/9 hebdo (6 %), écart à la moyenne mobile 40 semaines (6 %), distance au plus "
        "haut 52 semaines selon la règle « pas d'entrée au plus haut » (6 %), momentum 13 et 26 semaines (6 %), force "
        "relative contre le S&P 500 sur 26 semaines (6 %), sentiment technique lu de façon contrarienne (4 %). "
        "Les lectures sont automatiques : c'est une approximation qui peut différer de TradingView. "
        "Le CCI 20 (corps, mêmes seuils que CCI_S de la vue APEX, ligne violette = +100) entre dans la note lorsqu'il est en surachat ou en survente (6 % facultatif, pris sur le panier de 40 %). L'histogramme MACD est plafonné dès 4 barres hebdomadaires de même signe. "
        "Score = Σ (poids × note) ÷ Σ (poids disponibles). Zones : ≤ −60 vente forte · −60 à −20 vente · "
        "−20 à +20 neutre · +20 à +60 achat · ≥ +60 achat fort. BTC et ETH : cours Binance (USDT). "
        "XRP et SOL : cours Yahoo Finance (XRP-USD, SOL-USD). "
        "MSTR : cours Yahoo Finance (action, hors dividendes). Aucun rendement n'est promis."
    ),
    'retrieved': {
        'binance_btc': mtime('crypto/binance_BTCUSDT_1w.json'),
        'binance_eth': mtime('crypto/binance_ETHUSDT_1w.json'),
        'yahoo_xrp': mtime('crypto/yahoo_1wk_XRP-USD.json'),
        'yahoo_sol': mtime('crypto/yahoo_1wk_SOL-USD.json'),
        'yahoo_mstr': mtime('crypto/yahoo_1wk_MSTR.json'),
        'coinmetrics_xrp': mtime('crypto/coinmetrics_xrp_daily.json'),
        'spx': mtime('actions/yahoo_1wk_%5EGSPC.json'),
        'fng': mtime('crypto/alternative_fng.json'),
        'coinmetrics_btc': mtime('crypto/coinmetrics_btc_daily.json'),
        'coinmetrics_eth': mtime('crypto/coinmetrics_eth_daily.json'),
    },
}

# APEX_ONLY=xrp,sol : injecte uniquement les nouveaux actifs et conserve les fiches BTC / ETH / MSTR déjà publiées
ONLY = {k.strip() for k in os.environ.get('APEX_ONLY', '').split(',') if k.strip()}
if ONLY:
    prev_path = B + 'crypto_fiches.json'
    if os.path.exists(prev_path):
        prev = json.load(open(prev_path))
        fresh = {s['key']: s for s in fiches if s['key'] in ONLY}
        oldmap = {s['key']: s for s in prev.get('assets') or []}
        oldmap.update(fresh)
        order = ['btc', 'eth', 'xrp', 'sol', 'mstr']
        assets = [oldmap[k] for k in order if k in oldmap]
        seen = {s['key'] for s in assets}
        for s in (prev.get('assets') or []) + fiches:
            if s['key'] not in seen:
                assets.append(s); seen.add(s['key'])
        out['assets'] = assets
        # garder les textes de méthode à jour, mais ne pas écraser les timestamps des sources inchangées
        if isinstance(out.get('retrieved'), dict) and isinstance(prev.get('retrieved'), dict):
            merged = dict(prev['retrieved'])
            merged.update({k: v for k, v in out['retrieved'].items() if k in ('yahoo_xrp', 'yahoo_sol', 'coinmetrics_xrp') or k not in merged})
            out['retrieved'] = merged

json.dump(out, open(B + 'crypto_fiches.json', 'w'), ensure_ascii=False)
# Note APEX −50..250 (Hype, liquidité, MM40 hebdo) : durable après chaque reconstruction des fiches.
import sys as _sys
_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if _root not in _sys.path:
    _sys.path.insert(0, _root)
from apex.crypto_points import apply_notes as _apply_crypto_notes
_apply_crypto_notes(B + 'crypto_fiches.json', B + 'tabs_data.json' if os.path.exists(B + 'tabs_data.json') else None)

for s in fiches:
    if not s.get('ok'):
        print(s['sym'], 'INDISPONIBLE', s.get('raison'))
        continue
    fib = s['fibo']
    fibs = f"r={f1(fib['r']*100)} % ({fib.get('zone')})" if fib.get('ok') else fib.get('texte', 'n.d.')
    print(
        s['sym'].ljust(5), s['date'], 'clôt.', s['close'],
        '| sent', s['sent']['value'], s['sent']['label'],
        '| AV', s['av']['score'], s['av']['label'],
        '| RSI', s['ind']['rsi'], s['ind']['div']['type'],
        '| MACD', s['ind']['macd_texte'],
        '| CCI', s['ind']['cci'], s['ind']['cci_zone'],
        '| Fibo', fibs,
        '| ATH', s['ath']['dd'], '%',
        '| Elliott', s['elliott'].get('phase'), s['elliott'].get('key'),
        '|', s['warn'],
    )
