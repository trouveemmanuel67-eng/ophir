"""Notes APEX des devises des pays APEX, en euros (USD/EUR = 1/EURUSD, etc.).
Une note positive = contexte plus favorable à l'achat de cette devise contre l'euro.
Source : Yahoo Finance hebdo (bougies clôturées), série inversée. DXY non noté.
"""
import elliott_zones as EZ
import json, os, sys, math, datetime as D, urllib.parse
from zoneinfo import ZoneInfo
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ind_core as K
import fibo as FB
import charte as CH

B = '/workspace/invest/patrimoine-dashboard/data/'
L = B + 'liquidites/'
NOW = D.datetime.now(ZoneInfo('Europe/Paris'))
TODAY = NOW.date()

SPEC = [
    # code, nom, yahoo EURXXX, tv, dec for XXX/EUR price
    ('USD', 'Dollar américain', 'EURUSD=X', 'FX:EURUSD', 4),
    ('JPY', 'Yen japonais', 'EURJPY=X', 'FX:EURJPY', 6),
    ('GBP', 'Livre sterling', 'EURGBP=X', 'FX:EURGBP', 4),
    ('CHF', 'Franc suisse', 'EURCHF=X', 'FX:EURCHF', 4),
    ('AUD', 'Dollar australien', 'EURAUD=X', 'FX:EURAUD', 4),
    ('CAD', 'Dollar canadien', 'EURCAD=X', 'FX:EURCAD', 4),
    ('KRW', 'Won sud-coréen', 'EURKRW=X', 'FX:EURKRW', 6),
]
BN = 'panier APEX des devises'

def ypath(sym):
    return L + 'yahoo_1wk_' + urllib.parse.quote(sym, safe='') + '.json'

def mtime(path):
    if not os.path.exists(path):
        return None
    return D.datetime.fromtimestamp(os.path.getmtime(path), ZoneInfo('Europe/Paris')).strftime('%Y-%m-%d %H:%M')

def _rescale(x, ref):
    """Corrige les barres Yahoo dont un prix est décalé d'un facteur 10 ou 100 (ex. EURKRW)."""
    if not x or not ref or x <= 0 or ref <= 0:
        return x
    r = ref / x
    if 70 < r < 130:
        return x * 100
    if 70 < (1 / r) < 130:
        return x / 100
    if 7 < r < 13:
        return x * 10
    if 7 < (1 / r) < 13:
        return x / 10
    return x

def weekly_ohlc(path):
    """Barres hebdo officielles (lundi 00:00) uniquement, pour ne pas polluer le vendredi avec un tick du week-end."""
    d = json.load(open(path))['chart']['result'][0]
    ts = d['timestamp']
    q = d['indicators']['quote'][0]
    meta = d['meta']
    tz = ZoneInfo(meta.get('exchangeTimezoneName') or 'UTC')
    weeks = {}
    prev_c = None
    for t, o, h, l, c in zip(ts, q.get('open') or [], q.get('high') or [], q.get('low') or [], q.get('close') or []):
        if c is None or c <= 0:
            continue
        loc = D.datetime.fromtimestamp(t, tz)
        if not (loc.hour == 0 and loc.minute == 0):
            continue
        fri = (loc.date() + D.timedelta(days=(4 - loc.weekday()) % 7)).isoformat()
        ref = o if (o and o > 0) else prev_c
        if ref:
            c = _rescale(float(c), ref)
            o = _rescale(float(o), ref) if o and o > 0 else o
            h = _rescale(float(h), ref) if h and h > 0 else h
            l = _rescale(float(l), ref) if l and l > 0 else l
        # cohérence min/max après correction
        vals = [x for x in (o, h, l, c) if x and x > 0]
        if vals:
            if h is None or h <= 0:
                h = max(vals)
            else:
                h = max(h, *vals)
            if l is None or l <= 0:
                l = min(vals)
            else:
                l = min(l, *vals)
        weeks[fri] = (o if o and o > 0 else None, h if h and h > 0 else None, l if l and l > 0 else None, float(c))
        prev_c = float(c)
    fris = sorted(weeks)
    w, opens, hl, live = [], {}, {}, None
    for fri in fris:
        o, h, l, c = weeks[fri]
        closed = TODAY > D.date.fromisoformat(fri)
        if not closed:
            live = (fri, c, o, h, l)
            continue
        w.append((fri, c, True))
        if o:
            opens[fri] = o
        if h and l:
            hl[fri] = (h, l)
    return w, opens, hl, live, meta

def invert_series(w, opens, hl, live):
    w2 = [(d, 1.0 / c, ok) for d, c, ok in w if c]
    opens2 = {d: 1.0 / o for d, o in opens.items() if o}
    hl2 = {}
    for d, (h, l) in hl.items():
        if h and l:
            hl2[d] = (1.0 / l, 1.0 / h)
    live2 = None
    if live and live[1]:
        fri, c, o, h, l = live
        live2 = {
            'date': fri,
            'close': 1.0 / c,
            'open': None if not o else 1.0 / o,
        }
    return w2, opens2, hl2, live2

def equal_weight_index(series_map):
    """Indice 100, rendement moyen des devises disponibles chaque vendredi (XXX/EUR)."""
    maps = {code: {d: c for d, c, ok in w} for code, w in series_map.items()}
    dates = sorted({d for mp in maps.values() for d in mp})
    prev = {}
    idx = {}
    level = 100.0
    last_d = None
    for d in dates:
        if last_d is None:
            idx[d] = level
            last_d = d
            for code, mp in maps.items():
                if d in mp:
                    prev[code] = mp[d]
            continue
        rec = []
        for code, mp in maps.items():
            if code in prev and d in mp and prev[code]:
                # ignore residual scale glitches still > 50 %
                r = mp[d] / prev[code] - 1.0
                if abs(r) <= 0.5:
                    rec.append(r)
            if d in mp:
                prev[code] = mp[d]
        if rec:
            level *= 1.0 + sum(rec) / len(rec)
        idx[d] = level
        last_d = d
    return idx

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
    cc = K.cci20(op, c)
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
    cci_v = cc[last]
    # plus de décimales : les cours inversés (JPY, KRW) sont très petits
    md = 6 if (c[last] or 0) < 0.01 else (5 if (c[last] or 0) < 0.1 else 4)
    return {
        'rsi': None if r[last] is None else round(r[last], 1),
        'rsi_zone': rz,
        'macd': None if m[last] is None else round(m[last], md),
        'signal': None if sg[last] is None else round(sg[last], md),
        'hist': None if h[last] is None else round(h[last], md),
        'hist_prev': None if hist_prev is None else round(hist_prev, md),
        'macd_texte': macd_txt,
        'cci': None if cci_v is None else round(cci_v, 1),
        'cci_zone': K.cci_zone(cci_v),
        'cci_n': 20,
    }

def perf_from(w):
    """w = [(date, close, closed)] déjà en XXX/EUR, semaines clôturées."""
    xs = [(d, c) for d, c, ok in w if ok]
    if len(xs) < 2:
        return {}
    last_d, last = xs[-1]
    def pct(old):
        return None if not old else round((last / old - 1) * 100, 2)
    out = {}
    if len(xs) >= 2:
        out['1w'] = {'pct': pct(xs[-2][1]), 'date': xs[-2][0]}
    # ~4 semaines ≈ 1 mois, ~52 ≈ 1 an
    if len(xs) >= 5:
        out['1m'] = {'pct': pct(xs[-5][1]), 'date': xs[-5][0]}
    if len(xs) >= 53:
        out['1y'] = {'pct': pct(xs[-53][1]), 'date': xs[-53][0]}
    return out

def trend_of(perf):
    p1m = (perf.get('1m') or {}).get('pct')
    p1y = (perf.get('1y') or {}).get('pct')
    if p1m is None or p1y is None:
        return None
    def side(p):
        if p > 0.5:
            return 1
        if p < -0.5:
            return -1
        return 0
    a, b = side(p1m), side(p1y)
    if a == 0 or b == 0 or a != b:
        return 'mixte'
    return 'hausse' if a > 0 else 'baisse'

def rename_sent(r):
    for block in (r['sent']['components'], r['av']['components']):
        for x in block:
            if x.get('name') == 'Sentiment du secteur (lecture contrarienne)' or x.get('nom') == 'Sentiment du secteur (lecture contrarienne)':
                if 'name' in x:
                    x['name'] = 'Sentiment technique (lecture contrarienne)'
                if 'nom' in x:
                    x['nom'] = 'Sentiment technique (lecture contrarienne)'

def slim_charte(ch):
    if not ch:
        return None
    keep = {k: ch[k] for k in ch if k in ('note', 'valeur', 'texte', 'figures', 'div', 'source', 'regle', 'poids')}
    return keep

# ----- charger et inverser -----
raw = {}
for code, nom, yahoo, tv, dec in SPEC:
    path = ypath(yahoo)
    if not os.path.exists(path):
        raise SystemExit(f'fichier manquant : {path}')
    w, opens, hl, live, meta = weekly_ohlc(path)
    w2, o2, h2, live2 = invert_series(w, opens, hl, live)
    raw[code] = dict(nom=nom, yahoo=yahoo, tv=tv, dec=dec, path=path, meta=meta,
                     w=w2, opens=o2, hl=h2, live=live2, n=len(w2), first=w2[0][0] if w2 else None,
                     retrieved=mtime(path))
    print(f'  {code} weeks={len(w2)} first={raw[code]["first"]} last={w2[-1][0] if w2 else None} close_xxxeur={w2[-1][1] if w2 else None}')

bench = equal_weight_index({c: raw[c]['w'] for c in raw})
print('bench last', list(bench.items())[-1], 'n', len(bench))

assets = []
for code, nom, yahoo, tv, dec in SPEC:
    row = raw[code]
    w, opens, hl = row['w'], row['opens'], row['hl']
    if len([x for x in w if x[2]]) < 52:
        assets.append({'ok': False, 'code': code, 'sym': code, 'nom': nom, 'sous': "face à l'euro",
                       'tv': tv, 'yahoo': yahoo, 'raison': f"Historique hebdomadaire insuffisant ({len(w)} semaines)."})
        continue
    fpre = FB.prefix(f'{code}-EUR', w[0][0], w[0][1])
    r = K.compute(w, bench, BN, opens=opens, fsym=f'{code}-EUR', fpre=fpre, hl=hl, syms=[f'{code}/EUR'])
    rename_sent(r)
    ind = extra_indicators(w, opens)
    ch = r.get('charte') or {}
    dv = ch.get('div') or {}
    ind['div'] = {
        'type': ('baissière' if (dv.get('note') or 0) < 0 else 'haussière') if dv.get('note') is not None else ('indisponible' if not dv else 'aucune'),
        'texte': dv.get('texte') or "Aucune divergence RSI weekly récente : critère non compté, poids redistribué.",
        'note': dv.get('note'),
    }
    perf = perf_from(w)
    last = w[-1]
    live = row['live']
    if live:
        live = {'date': live['date'], 'close': round(live['close'], dec)}
    closed = [(d, c) for d, c, ok in w if ok]
    athv, athd = max((c, d) for d, c in closed)
    raw_close = closed[-1][1]
    item = {
        'ok': True,
        'code': code,
        'sym': code,
        'nom': nom,
        'sous': "face à l'euro",
        'tv': tv,
        'yahoo': yahoo,
        'unit': '€',
        'dec': dec,
        'quote_for': f'1 {code}',
        'date': r['date'],
        'close': round(raw_close, dec),
        'first': r['first'],
        'n': r['n'],
        'live': live,
        'ath': {'date': athd, 'close': round(athv, dec), 'dd': round((raw_close / athv - 1) * 100, 1)},
        'dd52': r['dd52'],
        'warn': r.get('warn') or [],
        'sent': r['sent'],
        'av': r['av'],
        'elliott': r['elliott'],
        'fibo': r['fibo'],
        'charte': slim_charte(ch),
        'ind': ind,
        'elliott_comment': elliott_comment(r.get('elliott')),
        'perf': perf,
        'trend': trend_of(perf),
        'url': f'https://finance.yahoo.com/quote/{urllib.parse.quote(yahoo, safe="")}/history/',
        'src_name': f'Yahoo Finance {yahoo}, série inversée ({code}/EUR)',
        'retrieved': row['retrieved'],
        'benchmark': BN,
    }
    assets.append(item)
    av = item['av']
    print(f"SCORE {code} {av['score']} {av['label']} date={item['date']} close={item['close']} €  S={item['sent']['value']}")

# rattacher aux paires déjà présentes dans tabs_data
tabs = json.load(open(B + 'tabs_data.json'))
liq = tabs['liquidites']
fx = liq['fx']
by_code = {a['code']: a for a in assets}
new_pairs = []
for p in fx.get('pairs') or []:
    code = p.get('code') or (p.get('pair') or '').split('/')[-1] or (p.get('pair') or '').replace('EUR/', '')
    # existing pack uses pair 'EUR/USD' and we had 'code' in fx_pack
    if 'code' not in p:
        # infer from pair
        if p.get('pair', '').startswith('EUR/'):
            code = p['pair'].split('/')[1]
        elif p.get('tv', '').startswith('FX:EUR'):
            code = p['tv'].replace('FX:EUR', '')
    a = by_code.get(code)
    merged = dict(p)
    if a:
        merged.update(a)
        # conserver le cours BCE d'origine sous ecb_*
        if 'last' in p:
            merged['ecb_last'] = p['last']
            merged['ecb_pair'] = p.get('pair')
            merged['ecb_perf'] = p.get('perf')
            merged['ecb_trend'] = p.get('trend')
        # la tendance / perf affichées sont celles de XXX/EUR (alignées sur la note)
        merged['perf'] = a['perf']
        merged['trend'] = a['trend']
        merged['last'] = [a['date'], a['close']]
    new_pairs.append(merged)

fx['pairs'] = new_pairs
fx['assets'] = assets
fx['apex'] = {
    'generated': NOW.strftime('%Y-%m-%d %H:%M'),
    'benchmark': BN,
    'method': (
        "Note APEX de chaque devise, calculée sur le cours hebdomadaire long d'une unité de cette devise en euros "
        "(USD/EUR = 1/EURUSD, et ainsi de suite). Une note positive signifie un contexte plus favorable à l'achat "
        "de cette devise contre l'euro. Pondérations et règles identiques aux autres actifs notés (Charte 20 %, "
        "Elliott 15 %, Fibonacci 15 %, Divergence RSI/MACD 10 % facultative, panier technique 40 % dont CCI 20 "
        "facultatif à 6 % hors zone neutre, règles du 18/11). Force relative contre un panier équipondéré des "
        "7 devises APEX (rendements hebdomadaires, en euros). Seuils : vert > +33, orange de −33 à +33, rouge < −33. "
        "DXY : repère de marché, sans note APEX. CNY et INR non retenus (pas de bloc pays Chine ni Inde). "
        "Source : Yahoo Finance, barres hebdomadaires clôturées, série inversée. La watchlist TradingView n'est pas modifiée."
    ),
    'source': 'Yahoo Finance, intervalle 1 semaine, séries EURXXX=X inversées',
}
fx['pairs_note'] = (
    "Notes APEX face à l'euro, sur le cours d'une unité de devise en EUR (série inversée). "
    "DXY reste un repère sans note. CNY et INR non retenus."
)

# ne pas toucher à positions.json ; on réécrit seulement tabs_data
json.dump(tabs, open(B + 'tabs_data.json', 'w'), ensure_ascii=False)
print('tabs_data patched, n assets', len(assets))
print('generated', fx['apex']['generated'])
