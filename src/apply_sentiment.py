#!/usr/bin/env python3
"""t537u : critère F&G des notes LONG = sentiment du secteur / de la classe d'actifs (data/sentiment_secteurs.json)
au lieu du CNN Fear & Greed global. Barème inchangé : floor(|50 − v| / 10) × 10, signé, max ±50
(« F&G inversé » des produits d'épargne : même barème, signe inversé). Seule la valeur d'entrée change.

Idempotent : l'ancien apport F&G est lu dans la note elle-même (points, décomposition ou ligne),
puis remplacé ; le total est recalculé (actions : somme des composantes ; sinon total − ancien + nouveau),
borné à −50..250. La ligne de détail affiche « Sentiment Santé (XLV) 66 : −10 ».
Rattachement : voir apex/sentiment.py. Si aucun secteur ni classe : 0 point, pas de repli CNN.
Crypto : même sentiment de classe (alternative.me via sentiment_secteurs.json).
Les moyennes (segments, paniers, bandeaux) reçoivent le sentiment maison de leurs membres,
et leur note est recalculée comme la moyenne des notes affichées (sauf les lignes métaux,
déjà traitées par recalc_moyennes_metaux).
Plus de repli CNN dans les notes. SHORT : src/build_short250.py.
Usage : python3 apply_sentiment.py [--dry-run]
"""
from __future__ import annotations

import json
import os
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(os.environ.get('APEX_ROOT') or Path(__file__).resolve().parent.parent)
sys.path[:0] = [str(ROOT), str(ROOT / 'src')]
from apex import sentiment as S  # noqa: E402
from apex.score import metaux_band  # noqa: E402

D = ROOT / 'data'
MIN, MAX = -50, 250
FILES = ['apex_achat_v2_pilot.json', 'apex_achat_v2_scores_full.json', 'apex_achat_v2_site.json', 'apex_bars.json',
         'energie.json', 'metaux.json', 'obligations.json', 'placements.json', 'tabs_data.json', 'crypto_fiches.json',
         'liquidites_etf_devises.json', 'secteurs.json', 'pays.json', 'achatvente.json']
TOK = re.compile(r'(?:F&G(?: inversé)?|Sentiment(?: inversé)? [^·→]*?\d+(?:,\d)? :) ([+−-]?\d+)')
TOTAL = re.compile(r'→\s+(-?−?\d+)\s*/\s*250')
LABEL_AV = {'violet': 'Très faible', 'rouge': 'Faible', 'orange': 'Neutre', 'vert': 'Favorable', 'cyan': 'Très favorable'}
TV_RE = re.compile(r'^[A-Z0-9_]+:[A-Z0-9_.\-!&]+$')

STATS = Counter()
CHANGES = {}
FALLBACK = Counter()


def _int(s):
    return int(str(s).replace('−', '-'))


def _signed(v):
    return ('+' + str(v)) if v > 0 else str(v).replace('-', '−')


def old_fg(rec):
    p = rec.get('points')
    if isinstance(p, dict) and isinstance(p.get('fear_greed'), (int, float)):
        return int(p['fear_greed']), False
    dec = rec.get('decomp')
    if isinstance(dec, dict):
        dp = dec.get('points')
        if isinstance(dp, dict):
            for k in ('F&G inversé', 'Sentiment inversé'):
                if isinstance(dp.get(k), (int, float)):
                    return int(dp[k]), True
            for k in ('F&G', 'fear_greed', 'Sentiment'):
                if isinstance(dp.get(k), (int, float)):
                    return int(dp[k]), False
    for t in (rec.get('ligne'), (dec or {}).get('texte') if isinstance(dec, dict) else None):
        if isinstance(t, str):
            m = TOK.search(t)
            if m:
                return _int(m.group(1)), ('inversé' in m.group(0))
    return None, False


def is_note(rec):
    v = rec.get('note', rec.get('total'))
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def seg_text(lab, val, pts, inv):
    v = '' if val is None else f" {int(round(val))}"
    return f"Sentiment{' inversé' if inv else ''} {lab}{v} : {_signed(pts)}"


def patch(rec, key, where):
    old, inv = old_fg(rec)
    if old is None or not is_note(rec):
        return
    k, sr = S.resolve(key)
    if (not sr or sr.get('value') is None) and k == 'cnn':
        k, sr = None, None
    if not sr or sr.get('value') is None:
        STATS['sans_sentiment'] += 1
        return
    if k == 'cnn':
        # plus de CNN dans les notes
        STATS['sans_sentiment'] += 1
        FALLBACK[where] += 1
        return
    val = float(sr['value'])
    new = S.fg_long(val)
    if inv:
        new = -new
    lab = S.court(k, sr)
    p = rec.get('points')
    before = rec.get('total', rec.get('note'))
    if isinstance(p, dict) and 'fear_greed' in p and all(x in p for x in ('rsi', 'macd', 'fondamental')):
        p['fear_greed'] = new
        base = sum(int(p.get(x) or 0) for x in ('rsi', 'macd', 'fibonacci', 'cci', 'fondamental', 'fear_greed'))
        total = max(MIN, min(MAX, base + int(p.get('hype') or 0) + int(p.get('mm40') or 0)))
        p['total'] = total
    else:
        total = max(MIN, min(MAX, int(round(float(before))) - old + new))
        if isinstance(p, dict) and 'fear_greed' in p:
            p['fear_greed'] = new
            if 'total' in p:
                p['total'] = total
    dec = rec.get('decomp')
    if isinstance(dec, dict) and isinstance(dec.get('points'), dict):
        for kk in list(dec['points']):
            if kk in ('F&G', 'F&G inversé', 'fear_greed', 'Sentiment', 'Sentiment inversé'):
                dec['points'][kk] = new
        if isinstance(dec['points'].get('total'), (int, float)):
            dec['points']['total'] = total
    seg = seg_text(lab, val, new, inv)
    for holder, fld in ((rec, 'ligne'), (dec if isinstance(dec, dict) else {}, 'texte')):
        t = holder.get(fld)
        if isinstance(t, str) and t:
            m = TOK.search(t)
            if m:
                t = t[:m.start()] + seg + t[m.end():]
            t = TOTAL.sub(f'→  {total} / 250', t)
            holder[fld] = t
    for f in ('total', 'note', 'pos'):
        if isinstance(rec.get(f), (int, float)) and not isinstance(rec.get(f), bool):
            rec[f] = total
    disp = rec.get('display')
    if isinstance(disp, str):
        rec['display'] = f'{total} / 250' if '/' in disp else str(total)
    b = metaux_band(total)
    if 'band' in rec:
        rec['band'] = b['id']
    if 'hex' in rec:
        rec['hex'] = b['hex']
    if 'flag' in rec:
        rec['flag'] = b['flag']
    if 'av_label' in rec:
        rec['av_label'] = LABEL_AV[b['id']]
    rec['sentiment'] = {'cle': k, 'nom': lab, 'valeur': round(val, 1), 'zone': sr.get('label'), 'points': new,
                        'inverse': inv, 'date': sr.get('date'), 'repli_cnn': False}
    fgmeta = rec.get('fear_greed')
    if isinstance(fgmeta, dict) and ('CNN' in str(fgmeta.get('source') or '') or fgmeta.get('valeur') is not None):
        rec['fear_greed'] = {'valeur': round(val, 1), 'source': 'sentiment maison ' + lab, 'points': new}
    dec = rec.get('decomp')
    if isinstance(dec, dict) and isinstance(dec.get('fear_greed'), dict) and 'CNN' in str((dec['fear_greed'] or {}).get('source') or ''):
        dec['fear_greed'] = {'valeur': round(val, 1), 'source': 'sentiment maison ' + lab, 'points': new}
    STATS['notes'] += 1
    if new != old:
        STATS['modifiees'] += 1
    return before, total


def walk(obj, ctx, where, file):
    if isinstance(obj, dict):
        c = dict(ctx)
        tv = obj.get('tv')
        if isinstance(tv, str) and tv:
            c['tv'] = tv
        if file == 'pays.json':
            if obj.get('cc'):
                c['cc'] = obj['cc']; c['tv'] = None
            if obj.get('key') and not obj.get('tv'):
                c['row'] = obj['key']; c['tv'] = None
        if is_note(obj) and old_fg(obj)[0] is not None and not c.get('skip'):
            key = None
            cl = c.get('classe')
            if cl == 'liquidites':
                key = 'liquidites'
            elif c.get('tv') and str(c['tv']).startswith('FX:'):
                key = 'devises'
            if key is None and c.get('tv'):
                key = S.key_for_tv(c['tv'])
            if key is None and c.get('pilote'):
                key = S.key_for_pilote(c['pilote'])
            if key is None and c.get('row'):
                key = S.key_for_row(c.get('cc'), c['row'])
            if key is None and cl == 'devises':
                key = 'devises'
            if key is None and cl == 'metaux':
                key = 'metaux'
            if key is None and cl == 'crypto':
                key = 'crypto'
            if key is None and cl == 'liquidites':
                key = 'liquidites'
            if key is None and cl == 'immobilier':
                key = 'immo:fr'
            r = patch(obj, key, f"{file}:{c.get('tv') or c.get('pilote') or c.get('row')}")
            if r and c.get('tv'):
                CHANGES.setdefault((file, c['tv']), r)
        for k, v in obj.items():
            cc = dict(c)
            if where == 'root' and file == 'tabs_data.json':
                if k == 'crypto':
                    cc['classe'] = 'crypto'
                if k == 'energie':
                    cc['classe'] = cc.get('classe') or 'energie'
                if k == 'liquidites':
                    cc['classe'] = 'liquidites'
            if k == 'pilotes':
                cc['in_pilotes'] = True
            elif c.get('in_pilotes') and 'pilote' not in c:
                cc['pilote'] = k; cc['tv'] = None
            if k == 'apex_epargne':
                cc['classe'] = 'liquidites'
            if k == 'fx':
                cc['classe'] = 'devises'
            if k == 'immobilier':
                cc['classe'] = 'immobilier'
            if isinstance(v, dict) and TV_RE.match(str(k)) and not v.get('tv'):
                cc['tv'] = k
            walk(v, cc, 'child', file)
    elif isinstance(obj, list):
        for v in obj:
            walk(v, ctx, 'child', file)



def _sent_kids(obj):
    kids = []
    if not isinstance(obj, dict):
        return kids
    for k in ('list', 'assets', 'rows', 'items', 'lignes', 'produits', 'segments'):
        v = obj.get(k)
        if isinstance(v, list):
            for x in v:
                if not isinstance(x, dict):
                    continue
                a = x.get('apex10') if isinstance(x.get('apex10'), dict) else None
                if a and isinstance((a.get('sentiment') or x.get('sentiment')), dict):
                    kids.append(a if a.get('sentiment') else x)
                elif isinstance(x.get('sentiment'), dict):
                    kids.append(x)
    ml = obj.get('mlist') or {}
    for x in [ml.get('head')] + list(ml.get('items') or []):
        if isinstance(x, dict) and isinstance((x.get('apex10') or {}).get('sentiment'), dict):
            kids.append(x['apex10'])
    return kids


def _is_avg_note(rec):
    if not isinstance(rec, dict) or not is_note(rec):
        return False
    if rec.get('n_moy') or rec.get('cap') in ('moyenne', 'panier'):
        return True
    t = rec.get('ligne') or ''
    if isinstance(t, str) and t.lower().startswith('moyenne'):
        return True
    d = (rec.get('decomp') or {}).get('texte') if isinstance(rec.get('decomp'), dict) else ''
    return isinstance(d, str) and d.lower().startswith('moyenne')


def attach_avg_sent(target, kids):
    xs = []
    for k in kids or []:
        s = k.get('sentiment') if isinstance(k, dict) else None
        if isinstance(s, dict) and s.get('valeur') is not None and not s.get('repli_cnn') and s.get('cle') != 'cnn':
            xs.append(s)
    if not xs or not isinstance(target, dict):
        return False
    keys = []
    for s in xs:
        if s.get('cle') and s['cle'] not in keys:
            keys.append(s['cle'])
    val = sum(float(s['valeur']) for s in xs) / len(xs)
    nom = xs[0]['nom'] if len(keys) == 1 else ('moyenne de %d' % len(xs))
    # zone : mêmes seuils que le site (labS)
    v = val
    zone = 'Peur extrême' if v < 25 else 'Peur' if v < 45 else 'Neutre' if v <= 55 else 'Avidité' if v <= 75 else 'Euphorie'
    pts = None
    if len(set(s.get('points') for s in xs if s.get('points') is not None)) == 1:
        pts = xs[0].get('points')
    elif all(s.get('points') is not None for s in xs):
        pts = int(round(sum(s['points'] for s in xs) / len(xs)))
    target['sentiment'] = {
        'cle': keys[0] if len(keys) == 1 else 'moyenne',
        'nom': nom, 'valeur': round(val, 1), 'zone': zone, 'points': pts,
        'inverse': False, 'moyenne': True, 'n': len(xs), 'repli_cnn': False,
    }
    return True


def enrich_averages(obj):
    n = 0
    if isinstance(obj, dict):
        kids = _sent_kids(obj)
        rec = obj.get('apex10') if isinstance(obj.get('apex10'), dict) else None
        if rec and _is_avg_note(rec) and kids:
            if attach_avg_sent(rec, kids):
                n += 1
        if _is_avg_note(obj) and kids:
            if attach_avg_sent(obj, kids):
                n += 1
        # crypto fiches.apex10
        if 'fiches' in obj and isinstance(obj['fiches'], dict):
            n += enrich_averages(obj['fiches'])
        for v in obj.values():
            if v is rec:
                continue
            n += enrich_averages(v)
    elif isinstance(obj, list):
        for v in obj:
            n += enrich_averages(v)
    return n


def main(dry=False):
    if not S.data():
        print('data/sentiment_secteurs.json absent : rien à faire.')
        return 0
    for f in FILES:
        p = D / f
        if not p.exists():
            continue
        raw = p.read_text(encoding='utf-8')
        doc = json.loads(raw)
        n0 = STATS['notes']
        ctx = {}
        if f == 'placements.json':
            ctx['classe'] = 'liquidites'
        if f == 'metaux.json':
            ctx['classe'] = 'metaux'
        if f == 'crypto_fiches.json':
            ctx['classe'] = 'crypto'
        if f == 'liquidites_etf_devises.json':
            ctx['classe'] = 'devises'
        if f == 'achatvente.json':
            ctx['in_av'] = True
        walk(doc, ctx, 'root', f)
        na = enrich_averages(doc)
        if na:
            print(f'  moyennes enrichies : {na}')
        if f == 'metaux.json':
            from build_long250 import recalc_moyennes_metaux
            recalc_moyennes_metaux(doc)
        from build_long250 import recalc_moyennes_doc, sync_achatvente_moyennes
        nm = recalc_moyennes_doc(doc, f)
        if nm:
            print(f'  moyennes recalculées : {nm}')
        if f == 'achatvente.json':
            extra = sync_achatvente_moyennes(doc, close=False)
            if extra:
                print('  achatvente aligné :', extra)
        print(f'{f}: {STATS["notes"] - n0} notes')
        if not dry:
            if raw.startswith('{\n'):
                m = re.match(r'\{\n( +)', raw)
                out = json.dumps(doc, ensure_ascii=False, indent=len(m.group(1)) if m else 2)
            elif raw.startswith('{"generated":"') or raw[:200].count('": ') == 0:
                out = json.dumps(doc, ensure_ascii=False, separators=(',', ':'))
            else:
                out = json.dumps(doc, ensure_ascii=False)
            p.write_text(out + ('\n' if raw.endswith('\n') else ''), encoding='utf-8')
    if not dry:
        mp, bp = D / 'metaux.json', D / 'apex_bars.json'
        if mp.exists() and bp.exists():
            M = json.loads(mp.read_text(encoding='utf-8'))
            B = json.loads(bp.read_text(encoding='utf-8'))
            n = 0
            for r in M.get('rows') or []:
                tv, rec = r.get('tv'), r.get('apex10')
                if tv and rec and isinstance(B.get('bars'), dict) and tv in B['bars']:
                    B['bars'][tv]['apex10'] = rec
                    n += 1
            if n:
                raw_b = bp.read_text(encoding='utf-8')
                if raw_b.startswith('{' + chr(10)):
                    out_b = json.dumps(B, ensure_ascii=False, indent=2)
                elif raw_b[:200].count('": ') == 0:
                    out_b = json.dumps(B, ensure_ascii=False, separators=(',', ':'))
                else:
                    out_b = json.dumps(B, ensure_ascii=False)
                nl = chr(10) if raw_b.endswith(chr(10)) else ''
                bp.write_text(out_b + nl, encoding='utf-8')
                print('apex_bars : moyennes métaux recopiées', n)
    print('total', dict(STATS))
    print('repli CNN', sum(FALLBACK.values()), dict(list(FALLBACK.items())[:30]))
    return 0


if __name__ == '__main__':
    raise SystemExit(main('--dry-run' in sys.argv))
