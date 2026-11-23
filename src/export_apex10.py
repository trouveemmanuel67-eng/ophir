"""Exporte notes_apex10_2026-11-23.csv et drapeaux_apex10_2026-11-23.txt."""
import os as _os
_APEX_ROOT = _os.path.abspath(_os.environ.get('APEX_ROOT') or _os.path.join(_os.path.dirname(__file__), '..'))
import json, csv, re
from pathlib import Path
from collections import Counter
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
import flags_couleur as FC

B = Path(_APEX_ROOT + '/data')
OUT_CSV = Path('/workspace/invest/notes_apex10_2026-11-23.csv')
OUT_TXT = Path('/workspace/invest/drapeaux_apex10_2026-11-23.txt')
WL_OLD = Path('/workspace/invest/apex_watchlist_live_apres_paniers10_2026-11-18.json')
# reconstructed 23/11 list if saved; else rebuild like the morning plan
LIVE_PREFIX = Path('/cursor/stores/user/grok-bot/agents/d95c5584-b71c-4eaf-9b43-eedd0ceb27f4/assets/01M83STHNK1ZNRCBJR6DZ5RJPT.txt')

REPERES = {'TVC:VIX','TVC:DXY','TVC:US10Y','XETR:BNQ9','NYMEX:CL1!','TVC:UKOIL','NYMEX:HO1!','NYMEX:RB1!','NYMEX:NG1!'}


def watchlist():
    old = json.loads(WL_OLD.read_text())['watchlist']['symbols']
    if LIVE_PREFIX.exists():
        rawt = LIVE_PREFIX.read_text()
        exch = {'TVC','XETR','NYSE','NASDAQ','AMEX','EURONEXT','MIL','TSE','KRX','ASX','BITSTAMP','CRYPTO','OANDA','LSE','NYMEX','CME','FX','FOREXCOM','BLACKBULL','VANTAGE','IG','TSX','JSE','SP','COMEX','ICE','CBOE','OMXSTO'}
        raw=[]
        for m in re.finditer(r'"(###[^"]+|[A-Za-z0-9_.:]+!?)"', rawt):
            s=m.group(1)
            if s.startswith('###') or (':' in s and s.split(':')[0] in exch):
                raw.append(s)
        seen=set(); cur=[]
        for s in raw:
            if s in seen: break
            seen.add(s); cur.append(s)
        last=cur[-1]
        tail=old[old.index(last)+1:]
        wl=cur+tail
        exp=old[:]
        i=exp.index('BITSTAMP:ETHUSD')
        if 'CRYPTO:XRPUSD' not in exp:
            exp=exp[:i+1]+['CRYPTO:XRPUSD','CRYPTO:SOLUSD']+exp[i+1:]
        if cur==exp[:len(cur)]:
            return wl if wl==exp else exp
    # fallback snapshot + XRP/SOL
    i=old.index('BITSTAMP:ETHUSD')
    if 'CRYPTO:XRPUSD' not in old:
        return old[:i+1]+['CRYPTO:XRPUSD','CRYPTO:SOLUSD']+old[i+1:]
    return old


def collect_notes():
    """tv or synthetic key → {av, fond, cap, note, hex, flag, date, elliott}."""
    out={}
    def add(key, rec, src=None):
        if not key or not rec:
            return
        a = rec.get('apex10') if isinstance(rec, dict) else None
        av = None
        if isinstance(rec.get('av'), dict):
            av = rec['av'].get('score')
        elif rec.get('av') is not None and not isinstance(rec.get('av'), (list, dict)):
            av = rec.get('av')
        if not a and av is None:
            return
        cur = {
            'av': av,
            'fond': (a or {}).get('fond'),
            'cap': (a or {}).get('cap') or '',
            'note': (a or {}).get('note'),
            'display': (a or {}).get('display') or '–',
            'hex': (a or {}).get('hex'),
            'flag': (a or {}).get('flag') or 'none',
            'date': rec.get('date'),
            'src': src,
        }
        prev = out.get(key)
        if prev:
            # prioritaire : ne pas écraser une fiche déjà complète (apex_bars en premier)
            if prev.get('note') is not None and prev.get('av') is not None:
                return
            if prev.get('av') is not None and cur.get('av') is None:
                cur['av'] = prev['av']
            if prev.get('fond') is not None and cur.get('fond') is None:
                cur['fond'] = prev['fond']
            if prev.get('note') is not None and cur.get('note') is None:
                for k in ('note','display','hex','flag','cap'):
                    cur[k] = prev[k]
        out[key] = cur

    ab=json.loads((B/'apex_bars.json').read_text())
    for k,b in (ab.get('bars') or {}).items():
        add(k,b,'apex_bars')
    for fn, keyf, itf in [
        # handled below more carefully
    ]:
        pass
    sg=json.loads((B/'secteurs.json').read_text())
    for s in sg.get('sectors') or []:
        add(s.get('tv') or s.get('sym'), s, 'secteurs')
    P=json.loads((B/'pays.json').read_text())
    for C in P.get('countries') or []:
        h=C.get('head') or {}
        add(h.get('tv') or h.get('sym'), h, 'pays_head')
        add(f"{C.get('cc')}:{h.get('key') or 'head'}", h, 'pays_head')
        for r in C.get('rows') or []:
            add(r.get('tv') or f"{C.get('cc')}:{r.get('key')}", r, 'pays_row')
            for t in ((r.get('fond') or {}).get('top') or []):
                add(t.get('tv') or t.get('ticker'), t if t.get('apex10') else None, 'pays_top')
                # if top has apex10
                if t.get('apex10'):
                    add(t.get('tv') or t.get('ticker'), t, 'pays_top')
    CRY={'BTC':'BITSTAMP:BTCUSD','ETH':'BITSTAMP:ETHUSD','XRP':'CRYPTO:XRPUSD','SOL':'CRYPTO:SOLUSD','MSTR':'NASDAQ:MSTR'}
    for fn, src, getter in [
        ('crypto_fiches.json','crypto', lambda d: d.get('assets') or []),
        ('energie.json','energie', lambda d: d.get('assets') or []),
    ]:
        d=json.loads((B/fn).read_text())
        for a in getter(d):
            add(a.get('tv') or CRY.get(a.get('sym')) or a.get('sym'), a, src)
    mt=json.loads((B/'metaux.json').read_text())
    for r in mt.get('rows') or []:
        # d'abord les instruments du bouton, pour que le XPT / XAG / XPD
        # au comptant gardent leur propre note et ne soient pas écrasés
        # par la moyenne de ligne (même ticker TV).
        item_tvs=set()
        ml=r.get('mlist') or {}
        for it in [ml.get('head')]+list(ml.get('items') or []):
            if it:
                add(it.get('tv') or it.get('ticker'), it, 'metaux_item')
                if it.get('tv'):
                    item_tvs.add(it['tv'])
        line_key=r.get('key')
        if r.get('tv') and r['tv'] not in item_tvs:
            line_key=r['tv']
        add(line_key, r, 'metaux')
    ob=json.loads((B/'obligations.json').read_text())
    for s in ob.get('segments') or []:
        add(s.get('tv') or s.get('key'), s, 'obligations')
        for r in s.get('list') or []:
            add(r.get('tv') or r.get('yahoo'), r, 'ob_list')
    fx=B/'fx_apex.json'
    if fx.exists():
        FX=json.loads(fx.read_text())
        assets=FX if isinstance(FX,list) else (FX.get('assets') or FX.get('currencies') or [])
        for a in assets:
            if isinstance(a,dict):
                add(a.get('tv') or a.get('sym'), a, 'fx')
    return out


def fmt_av(v):
    if v is None or v=='':
        return ''
    return f'{float(v):+.1f}'

def fmt_fond(v):
    if v is None or v=='':
        return ''
    return f'{float(v):.1f}'.replace('.', ',')

def main():
    wl=watchlist()
    notes=collect_notes()
    section='Indices & macro'
    rows=[]
    items=[]
    for s in wl:
        if s.startswith('###'):
            section=s[3:].lstrip('\u2063\u200b\u200c\u200d ')
            continue
        items.append((s, section))
        n=notes.get(s)
        if s in REPERES:
            rows.append(dict(symbole=s, av='', fond='', cap='', note='', display='–', hex='', flag='aucun', a_changer='non', section=section))
            continue
        if not n or n.get('note') is None:
            rows.append(dict(symbole=s, av=fmt_av((n or {}).get('av')), fond=fmt_fond((n or {}).get('fond')),
                             cap=(n or {}).get('cap') or '', note='', display='–', hex='', flag='aucun', a_changer='non', section=section))
            continue
        flag=n.get('flag') or 'none'
        rows.append(dict(
            symbole=s,
            av=fmt_av(n.get('av')),
            fond=fmt_fond(n.get('fond')),
            cap=n.get('cap') or '',
            note=n['display'],
            display=n['display'],
            hex=n.get('hex') or '',
            flag=FC.FR.get(flag, flag),
            a_changer='oui',
            section=section,
        ))

    with OUT_CSV.open('w', newline='', encoding='utf-8') as f:
        w=csv.writer(f)
        w.writerow(['symbole','AV','fondamental','plafond appliqué','note /10','couleur'])
        for r in rows:
            w.writerow([r['symbole'], r['av'], r['fond'], r['cap'], r['display'], r['hex']])

    order=['rouge','orange','vert','cyan']
    chg=[r for r in rows if r['a_changer']=='oui']
    lines=['# Drapeaux TradingView à poser — note APEX /10 — 23/11/2026',
           '# Watchlist APEX id 355582461 — ordre de la watchlist, par section.',
           '# Seuils : 1–1,5 rouge ; 2–4,5 orange ; 5–8 vert ; 8,5–10 cyan.',
           '# Repères et actifs sans note : pas de drapeau (non listés).',
           '# Les couleurs live ne sont pas lisibles : toutes les cibles notées sont listées.',
           '']
    for col in order:
        grp=[r for r in chg if r['flag']==col]
        lines.append(f'## {col} ({len(grp)})')
        last=None
        for r in grp:
            if r['section']!=last:
                lines.append(f"# {r['section']}")
                last=r['section']
            lines.append(r['symbole'])
        lines.append('')
    OUT_TXT.write_text('\n'.join(lines)+'\n', encoding='utf-8')

    print('csv', OUT_CSV, 'n', len(rows))
    print('txt', OUT_TXT, 'à poser', len(chg))
    print('flags', Counter(r['flag'] for r in rows))
    print('notes', Counter(r['display'] for r in rows if r['display']!='–'))
    return rows

if __name__=='__main__':
    main()
