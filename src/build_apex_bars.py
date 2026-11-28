"""Notes APEX (AV + sentiment) pour les listes d'actifs qui n'avaient pas encore de barre double.
Ne recalcule pas les fiches déjà publiées (secteurs, pays têtes, énergie, etc.).
Aucune note n'est inventée : historique < 52 semaines → données insuffisantes.
"""
import os as _os
_APEX_ROOT = _os.path.abspath(_os.environ.get('APEX_ROOT') or _os.path.join(_os.path.dirname(__file__), '..'))
import json, os, sys, traceback, urllib.parse, datetime as D
from zoneinfo import ZoneInfo
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ind_core as K
import fibo as FB

B = _APEX_ROOT + '/data/'
NOW = D.datetime.now(ZoneInfo('Europe/Paris'))
MIN_W = 52

def quote(s):
    return urllib.parse.quote(s, safe='')

def first_existing(paths):
    for p in paths:
        if p and os.path.exists(p):
            return p
    return None

def yahoo_cands(tv, yahoo=None, ticker=None):
    cands = []
    for x in (yahoo, ticker):
        if x and x not in cands:
            cands.append(x)
    if tv and ':' in tv:
        ex, t = tv.split(':', 1)
        mp = {
            'EURONEXT': [t + '.PA', t + '.AS', t + '.BR', t + '.LS'],
            'XETR': [t + '.DE'], 'MIL': [t + '.MI'],
            'NYSE': [t], 'NASDAQ': [t], 'AMEX': [t], 'CBOE': [t],
            'TSX': [t + '.TO'], 'TSE': [t + '.T'], 'JPX': [t + '.T'],
            'KRX': [t + '.KS'], 'ASX': [t + '.AX'], 'LSE': [t + '.L'], 'SIX': [t + '.SW'],
        }
        for x in mp.get(ex, [t]) + [t]:
            if x and x not in cands:
                cands.append(x)
    elif tv and tv not in cands:
        cands.append(tv)
    return cands

ROOTS = [
    B + 'fibo_max/{enc}.json',
    '/workspace/invest/indiv/yc/{enc}.json',
    '/workspace/invest/indiv/yc/{sym}.json',
    B + 'pays/wk/{sym}.json',
    B + 'energie/yahoo_1wk_{enc}.json',
    B + 'secteurs/yahoo_1wk_{enc}.json',
    B + 'pays/yahoo_1wk_{enc}.json',
    B + 'actions/yahoo_1wk_{enc}.json',
]

def find_wk(cands):
    for s in cands:
        enc = quote(s)
        p = first_existing([pat.format(sym=s, enc=enc) for pat in ROOTS])
        if p:
            return p, s
    return None, None

BENCH_FILES = {
    '^GSPC': first_existing([
        B + 'energie/yahoo_1wk_%5EGSPC.json',
        B + 'actions/yahoo_1wk_%5EGSPC.json',
        B + 'fibo_max/%5EGSPC.json',
    ]),
    '^FCHI': first_existing([B + 'pays/yahoo_1wk_%5EFCHI.json', B + 'actions/yahoo_1wk_%5EFCHI.json', B + 'fibo_max/%5EFCHI.json']),
    '^GDAXI': first_existing([B + 'pays/yahoo_1wk_%5EGDAXI.json', B + 'fibo_max/%5EGDAXI.json']),
    'FTSEMIB.MI': first_existing([B + 'pays/yahoo_1wk_FTSEMIB.MI.json', B + 'fibo_max/FTSEMIB.MI.json']),
    '1306.T': first_existing([B + 'pays/yahoo_1wk_1306.T.json', B + 'fibo_max/1306.T.json']),
    '^KS11': first_existing([B + 'pays/yahoo_1wk_%5EKS11.json', B + 'fibo_max/%5EKS11.json']),
    '^AXJO': first_existing([B + 'pays/yahoo_1wk_%5EAXJO.json', B + 'fibo_max/%5EAXJO.json']),
    '^GSPTSE': first_existing([B + 'pays/yahoo_1wk_%5EGSPTSE.json', B + 'fibo_max/%5EGSPTSE.json']),
    '^SSMI': first_existing([B + 'pays/yahoo_1wk_%5ESSMI.json', B + 'pays/wk/^SSMI.json', B + 'fibo_max/%5ESSMI.json']),
}

def load_ben(sym):
    path = BENCH_FILES.get(sym)
    if not path:
        raise FileNotFoundError('benchmark introuvable: ' + sym)
    w, meta = K.yweekly(path)
    return {d: v for d, v, c in w if c}, (meta or {}).get('shortName') or sym

def collect():
    F = json.load(open(B + 'fondamentaux.json'))
    P = json.load(open(B + 'pays.json'))
    MT = json.load(open(B + 'metaux.json'))
    OB = json.load(open(B + 'obligations.json'))
    items = []
    def add(src, tv, yahoo, ticker, name, bench, **kw):
        items.append(dict(src=src, tv=tv, yahoo=yahoo, ticker=ticker, name=name, bench=bench, **kw))
    for k, s in (F.get('sectors') or {}).items():
        for r in s.get('top') or []:
            add('fond', r.get('tv'), r.get('yahoo'), r.get('ticker') or r.get('yahoo'), r.get('name'), '^GSPC', basket=k)
    for C in P.get('countries') or []:
        bench = C.get('bench') or '^GSPC'
        for row in (C.get('rows') or []):
            for r in (row.get('fond') or {}).get('top') or []:
                add('pays', r.get('tv'), r.get('yahoo') or r.get('ticker'), r.get('ticker'), r.get('name'), bench, cc=C.get('cc'))
    for r in MT.get('rows') or []:
        ml = r.get('mlist') or {}
        for it in [ml.get('head')] + list(ml.get('items') or []):
            if not it:
                continue
            add('metaux', it.get('tv'), it.get('ticker') or it.get('yahoo'), it.get('ticker'), it.get('name'), '^GSPC', kind=it.get('kind'))
    for s in OB.get('segments') or []:
        for r in s.get('list') or []:
            add('ob', r.get('tv'), r.get('yahoo'), r.get('yahoo'), r.get('name'), '^GSPC', seg=s.get('key'))
    # unique by tv (fallback yahoo/name)
    seen, uniq = set(), []
    for it in items:
        key = it.get('tv') or it.get('yahoo') or it.get('name')
        if not key or key in seen:
            continue
        seen.add(key)
        uniq.append(it)
    return uniq

def compact(r, sent):
    ell=r.get('elliott') or {}
    av=r.get('av') or {}
    ell_out=None
    if ell.get('key'):
        ell_out={'key': ell.get('key'), 'phase': ell.get('phase')}
        if ell.get('zone'):
            ell_out['zone']=ell.get('zone')
        if ell.get('manuel') or ell.get('override'):
            ell_out['manuel']=True
            ell_out['override']=True
            if ell.get('texte'): ell_out['texte']=ell.get('texte')
    av_out={'score': av.get('score'), 'label': av.get('label')}
    if av.get('score_affiche') is not None:
        av_out['score_affiche']=av['score_affiche']
    if av.get('cap_zone'):
        av_out['cap_zone']=av['cap_zone']
    div=av.get('divergence')
    if div is None:
        for c in (av.get('components') or []):
            if str(c.get('nom') or '').startswith('Divergence') and c.get('note') is not None:
                div=c['note']
                break
    if div is not None:
        av_out['divergence']=div
    rec = {
        'ok': True,
        'date': r['date'],
        'av': av_out,
        'sent': {'value': sent['value'], 'label': sent['label']},
        'elliott': ell_out,
    }
    tech = r.get('technique') or (r.get('av') or {}).get('technique')
    if tech:
        rec['technique'] = {k: tech.get(k) for k in ('elliott','structure','fibonacci','figure','rsi','macd','cci')}
        if tech.get('figure_texte'):
            rec['technique']['figure_texte'] = tech.get('figure_texte')
    return rec

def score_one(it, bens):
    key = it.get('tv') or it.get('yahoo') or it.get('name')
    cands = yahoo_cands(it.get('tv'), it.get('yahoo'), it.get('ticker'))
    path, ysym = find_wk(cands)
    if not path:
        return key, {'ok': False, 'raison': 'données insuffisantes'}
    try:
        w, meta = K.yweekly(path)
        wc = [x for x in w if x[2]]
        if len(wc) < MIN_W:
            return key, {'ok': False, 'raison': 'données insuffisantes'}
        opens = {k: (v if v else None) for k, v in K.yopens(path).items()}
        hl = K.yhl(path)
        ben_sym = it.get('bench') or '^GSPC'
        if ben_sym not in bens:
            bens[ben_sym] = load_ben(ben_sym)
        ben, bn = bens[ben_sym]
        fpre = FB.prefix(ysym, wc[0][0], wc[0][1]) if ysym else None
        r = K.compute(w, ben, bn, opens=opens, fsym=ysym, fpre=fpre, hl=hl,
                      syms=[x for x in (it.get('tv'), ysym, it.get('ticker')) if x],
                      contrarien=(it.get('src')=='metaux'), sans_elliott=(it.get('src')=='metaux'),
                      oblig=(it.get('src')=='ob'))   # t697u : lecture contrarienne du prix pour les ETF obligataires
        if r.get('av') is None or r['av'].get('score') is None or r.get('sent') is None or r['sent'].get('value') is None:
            return key, {'ok': False, 'raison': 'données insuffisantes'}
        return key, compact(r, r['sent'])
    except Exception:
        return key, {'ok': False, 'raison': 'données insuffisantes'}

def main():
    items = collect()
    print('à noter', len(items), flush=True)
    bens = {}
    # preload common benches
    for s in set(it['bench'] for it in items):
        try:
            bens[s] = load_ben(s)
            print('bench', s, 'n', len(bens[s][0]), flush=True)
        except Exception as e:
            print('BENCH FAIL', s, e, flush=True)
    bars = {}
    ok = fail = 0
    for i, it in enumerate(items, 1):
        key, rec = score_one(it, bens)
        bars[key] = rec
        if rec.get('ok'):
            ok += 1
        else:
            fail += 1
        if i % 25 == 0 or i == len(items):
            print(f'{i}/{len(items)} ok={ok} insuffisant={fail}', flush=True)
    out = {
        'generated': NOW.strftime('%Y-%m-%d %H:%M'),
        'method': (
            "Notes APEX calculées le 22/11/2026 avec la grille du 18/11 "
            "(unité hebdomadaire, bougies clôturées, Charte 20 %, Elliott 15 %, Fibonacci 15 %, "
            "Divergence RSI/MACD 10 % facultative, panier technique et sentiment 40 % dont CCI 20 "
            "facultatif hors zone ±100 et plafonnement MACD à 4 barres). "
            "Aucune note n'est inventée : un historique inférieur à 52 semaines clôturées est affiché comme données insuffisantes."
        ),
        'n': len(bars),
        'n_ok': ok,
        'n_insuffisant': fail,
        'bars': bars,
    }
    path = B + 'apex_bars.json'
    json.dump(out, open(path, 'w'), ensure_ascii=False)
    print('wrote', path, 'ok', ok, 'insuffisant', fail, 'bytes', os.path.getsize(path))
    # Tech 5
    for tv in ('NASDAQ:PLTR', 'NASDAQ:NVDA', 'NASDAQ:AVGO', 'NYSE:ANET', 'NASDAQ:AMD'):
        print('TECH', tv, bars.get(tv))

if __name__ == '__main__':
    main()
