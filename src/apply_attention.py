#!/usr/bin/env python3
"""Applique l'apport H (attention / hype, à contre-courant) aux notes APEX actions.

Note APEX actions (APE-25) = RSI 27 + MACD 27 + Fibo 27 + CCI 18 (99) + Fondamental 81 + F&G (±50) + H (0..20)
=> échelle −50 à 250.  H = 20 − 2 × tranche d'attention (0–9 → 20, 100 → 0) ; attention absente => « – ».
Actions USA et France uniquement. ETF / panier de section = moyenne arrondie des H disponibles
des actions affichées (même logique que le fondamental). Hors USA / France : H « – ».
Idempotent : le total est recalculé à partir des composantes, jamais cumulé.
Ne touche à aucune autre section (Métaux, Oblig., Liq., Immo, Crypto, Énergie, ETF Marché).
"""
from __future__ import annotations
import json, sys
from pathlib import Path
import os

ROOT = Path(os.environ.get('APEX_ROOT') or Path(__file__).resolve().parent.parent)
DATA = ROOT / 'data'

SCALE_MIN, SCALE_MAX = -50, 250
HYPE_ABS = 20
# APE-25 (t503u) : échelle unique −50..250. Composantes compressées équitablement (× 0,9) :
# RSI 27, MACD 27, Fibo 27, CCI 18 (technique 99) + Fondamental 81 (9 × 9) + H 0..20 + F&G ±50.
FACTEUR = 0.9
BANDS = [
    ('violet', -50, 10, '#9d54ff'),
    ('rouge', 10, 70, '#ff2d2d'),
    ('orange', 70, 130, '#ff8c1a'),
    ('vert', 130, 190, '#22c55e'),
    ('cyan', 190, 251, '#00e5ff'),
]
SEUIL_MEILLEURES = 130
HEX = {n: h for n, _a, _b, h in BANDS}
LABEL = {'violet': 'Très faible', 'rouge': 'Faible', 'orange': 'Neutre', 'vert': 'Favorable', 'cyan': 'Très favorable'}
KEEP_PAYS = ('USA', 'France')
COMP = ('rsi', 'macd', 'fibonacci', 'cci', 'fondamental')


def band_of(t):
    t = float(t)
    if t >= 190: return 'cyan'
    if t >= 130: return 'vert'
    if t >= 70: return 'orange'
    if t >= 10: return 'rouge'
    return 'violet'


def h_points(attention):
    """H à contre-courant 0..20 : attention 0–9 → +20, −2 par tranche de 10, 100 → 0."""
    if attention is None:
        return None
    v = max(0, min(100, int(attention)))
    return max(0, 20 - 2 * (v // 10))


def scale_obj(old=None):
    s = dict(old or {})
    s.update({'min': SCALE_MIN, 'max': SCALE_MAX, 'tech_max': 99, 'fond_max': 81, 'fg_abs': 50, 'hype_abs': HYPE_ABS,
              'hype_min': 0,
              'composantes': {'rsi': 27, 'macd': 27, 'fibonacci': 27, 'cci': 18, 'fondamental': 81, 'hype': 20, 'fear_greed': 50},
              'seuil_meilleures_entrees': SEUIL_MEILLEURES,
              'regle_bandes': 'Échelle unique −50 à 250 : violet < 10, rouge 10–69, orange 70–129, vert 130–189, cyan ≥ 190',
              'bandes': [{'id': n, 'de': lo, 'a': (hi if hi < 251 else 250), 'hex': hx} for n, lo, hi, hx in BANDS],
              'drapeaux_5': [
                  {'id': 'violet', 'de': None, 'a': 10, 'regle': '< 10'},
                  {'id': 'rouge', 'de': 10, 'a': 70, 'regle': '10 ≤ n < 70'},
                  {'id': 'orange', 'de': 70, 'a': 130, 'regle': '70 ≤ n < 130'},
                  {'id': 'vert', 'de': 130, 'a': 190, 'regle': '130 ≤ n < 190'},
                  {'id': 'cyan', 'de': 190, 'a': None, 'regle': '≥ 190'},
              ]})
    return s


def _fmt(k, v):
    if v is None:
        return f'{k} –' if k == 'H' else f'{k} n.d.'
    return f"{k} {'+' if v > 0 else ''}{v}"


def _brut(rec):
    """Composantes brutes (ancienne échelle 110/90), mémorisées une seule fois (idempotence)."""
    p = rec['points']
    if not isinstance(rec.get('points_brut'), dict):
        rec['points_brut'] = {k: p.get(k) for k in COMP}
    return rec['points_brut']


def _scale_elems(elems):
    for e in elems or []:
        if not isinstance(e, dict) or e.get('points') is None:
            continue
        if 'points_brut' not in e:
            e['points_brut'] = e['points']
        e['points'] = round(float(e['points_brut']) * FACTEUR, 1)
        if float(e['points']).is_integer():
            e['points'] = int(e['points'])


def rescale_rec(rec, fond_override=None):
    """Compresse RSI/MACD/Fibo/CCI/Fond × 0,9 (valeurs entières exactes : 10→9, 20→18, 30→27)."""
    if not rec or not rec.get('ok') or not isinstance(rec.get('points'), dict):
        return rec
    b = _brut(rec)
    p = rec['points']
    for k in COMP:
        v = b.get(k)
        p[k] = None if v is None else int(round(float(v) * FACTEUR))
    if fond_override is not None:
        p['fondamental'] = int(fond_override)
    for key in ('fond',):
        f = rec.get(key)
        if isinstance(f, dict):
            if fond_override is None:
                _scale_elems(f.get('elements'))
            f['points'] = p['fondamental']; f['max'] = 81
    c = rec.get('cci')
    if isinstance(c, dict) and c.get('points') is not None:
        c['points'] = p['cci']
    det = rec.get('detail')
    if isinstance(det, dict):
        for k in COMP:
            d = det.get(k)
            if isinstance(d, dict):
                d['points'] = p[k]
        fd = det.get('fondamental')
        if isinstance(fd, dict):
            fd['max'] = 81
            if fond_override is None:
                _scale_elems(fd.get('elements'))
    return rec


def apply_rec(rec, h, att=None, fond_override=None):
    """Met à jour un enregistrement noté (ok) avec l'apport H (None = « – »)."""
    if not rec or not rec.get('ok') or not isinstance(rec.get('points'), dict):
        return rec
    rescale_rec(rec, fond_override)
    p = rec['points']
    p['hype'] = h
    base = sum(int(p.get(k) or 0) for k in ('rsi', 'macd', 'fibonacci', 'cci', 'fondamental', 'fear_greed'))
    total = max(SCALE_MIN, min(SCALE_MAX, base + (h or 0)))
    p['total'] = total
    parts = [('RSI', p.get('rsi')), ('MACD', p.get('macd')), ('Fibo', p.get('fibonacci')), ('CCI', p.get('cci')),
             ('Fond', p.get('fondamental')), ('F&G', p.get('fear_greed')), ('H', h)]
    b = band_of(total)
    rec.update({'total': total, 'total_max': SCALE_MAX, 'total_min': SCALE_MIN,
                'display': f'{total} / {SCALE_MAX}', 'band': b, 'hex': HEX[b], 'av_label': LABEL[b],
                'ligne': ' · '.join(_fmt(k, v) for k, v in parts) + f'  →  {total} / {SCALE_MAX}'})
    rec['attention'] = att if att is not None else {'valeur': None, 'H': None}
    return rec


def att_compact(a):
    if not a or a.get('attention') is None:
        return None
    c = a.get('composantes') or {}
    return {'valeur': a['attention'], 'H': h_points(a['attention']), 'trends': c.get('trends'), 'mentions': c.get('mentions'),
            'volume': c.get('volume'), 'persistance': c.get('persist'), 'poids_dispo': a.get('poids_dispo'),
            'grille': '0–9 → +20, −2 par tranche de 10, 100 → 0',
            'manquants': [m for m in (a.get('manquants') or []) if m not in ('X', 'StockTwits')]}


def _etf_fond(etf, actions):
    """Fondamental ETF / panier = moyenne arrondie des fondamentaux (81) des actions affichées (toutes)."""
    ok = [a for a in actions if a.get('ok') and isinstance(a.get('points'), dict)]
    if not ok:
        return None
    vals = [int(a['points'].get('fondamental') or 0) for a in ok]
    n = len(vals)
    fond = int(round(sum(vals) / n))
    names = ', '.join(a.get('ticker') or a.get('tv') or '?' for a in ok)
    # moyenne par critère
    order, by = [], {}
    for a in ok:
        f = a.get('fond') or (a.get('detail') or {}).get('fondamental') or {}
        for e in f.get('elements') or []:
            if e.get('id') not in by:
                order.append(e.get('id')); by[e.get('id')] = {'label': e.get('label'), 'seuil': e.get('seuil'), 'vals': [], 'bons': 0, 'manq': 0}
            r = by[e['id']]; r['vals'].append(float(e.get('points') or 0)); r['bons'] += 1 if e.get('ok') else 0; r['manq'] += 1 if e.get('manquant') else 0
    elems = [{'id': i, 'label': by[i]['label'], 'valeur': None, 'seuil': by[i]['seuil'], 'ok': None,
              'points': round(sum(by[i]['vals']) / (len(by[i]['vals']) or 1), 1), 'manquant': None,
              'moyenne_10': True, 'n_bons': by[i]['bons'], 'n_manquants': by[i]['manq'], 'n': len(by[i]['vals'])} for i in order]
    mode = (f"Moyenne des {n} actions affichées ({names}). Chaque titre est noté avec sa règle (banque ou hors banque), "
            "9 critères × 9 points. L'instrument de section n'a pas de ratios d'émetteur ; donnée manquante = 0, rien n'est inventé.")
    for key in ('fond',):
        if isinstance(etf.get(key), dict):
            etf[key].update({'points': fond, 'max': 81, 'mode': mode, 'elements': elems})
    det = etf.get('detail')
    if isinstance(det, dict) and isinstance(det.get('fondamental'), dict):
        det['fondamental'].update({'points': fond, 'max': 81, 'mode': mode, 'elements': elems})
    return fond


def apply_doc(doc, att_by, att_meta=None):
    """Applique H (0..20) et l'échelle 250 à un document pilote (apex_achat_v2_pilot.json ou scores_full)."""
    pil = doc.get('pilotes') or {}
    res = {}  # tv -> (h, att, fond_override)
    for sid, p in pil.items():
        pays = p.get('pays') or ('USA' if str(sid).startswith('XL') else None)
        hs = []
        names = []
        acts = p.get('actions') or []
        for a in acts:
            tv = a.get('tv')
            att = att_compact(att_by.get(tv)) if pays in KEEP_PAYS else None
            h = att['H'] if att else None
            apply_rec(a, h, att)
            res[tv] = (h, att, None)
            if h is not None:
                hs.append(h); names.append(a.get('ticker') or tv)
        etf = p.get('etf') or {}
        if pays in KEEP_PAYS and hs:
            h = int(round(sum(hs) / len(hs)))
            att = {'valeur': None, 'H': h, 'moyenne_de': names, 'n': len(hs), 'n_affichees': len(acts),
                   'precision': f'Moyenne arrondie des H des {len(hs)} action(s) affichée(s) sur {len(acts)} (mêmes titres que le fondamental)'}
        else:
            h, att = None, None
        fo = _etf_fond(etf, acts) if etf.get('ok') else None
        apply_rec(etf, h, att, fo)
        if etf.get('tv'):
            res[etf['tv']] = (h, att, fo)
    # rétrocompatibilité : copie « Communication » à la racine du document (etf / actions)
    for r in [doc.get('etf')] + list(doc.get('actions') or []):
        if isinstance(r, dict) and r.get('tv'):
            h, att, fo = res.get(r['tv'], (None, None, None))
            if fo is not None:
                _copy_fond(r, pil, r['tv'])
            apply_rec(r, h, att, fo)
    for tv, r in (doc.get('by_tv') or {}).items():
        h, att, fo = res.get(tv, (None, None, None))
        if fo is not None:
            _copy_fond(r, pil, tv)
        apply_rec(r, h, att, fo)
    doc['scale'] = scale_obj(doc.get('scale'))
    if att_meta:
        doc['attention_meta'] = {k: att_meta.get(k) for k in ('generated', 'semaine', 'definition', 'poids', 'sources', 'stats')}
    return doc


def _copy_fond(r, pil, tv):
    for p in pil.values():
        e = p.get('etf') or {}
        if e.get('tv') == tv and e is not r:
            if isinstance(e.get('fond'), dict) and isinstance(r.get('fond'), dict):
                r['fond'] = json.loads(json.dumps(e['fond']))
            if isinstance((e.get('detail') or {}).get('fondamental'), dict) and isinstance((r.get('detail') or {}).get('fondamental'), dict):
                r['detail']['fondamental'] = json.loads(json.dumps(e['detail']['fondamental']))
            return


def _h_actions(rec):
    if rec is None:
        return None
    if rec.get('H_actions') is not None:
        return int(rec['H_actions'])
    if rec.get('H') is not None:
        return int(rec['H'])
    if rec.get('attention') is None:
        return None
    h = int(round((50.0 - float(rec['attention'])) * 0.6))
    return max(-30, min(30, h))


def _from_w48(doc):
    """Convertit attention_scores_YYYY-Wxx.json (clés actifs) vers by_tv + meta."""
    by_tv = {}
    by_key = {}
    for key, rec in (doc.get('actifs') or {}).items():
        if not isinstance(rec, dict):
            continue
        comp = rec.get('composantes') or {}
        item = {
            'attention': rec.get('attention'),
            'H': _h_actions(rec) if rec.get('classe') == 'action' else None,
            'classe': rec.get('classe'),
            'nom': rec.get('nom'),
            'yahoo': rec.get('yahoo'),
            'tv': rec.get('tv'),
            'composantes': {
                'trends': comp.get('trends'),
                'mentions': comp.get('mentions'),
                'volume': comp.get('volume'),
                'persist': comp.get('persistance') if 'persistance' in comp else comp.get('persist'),
                'persistance': comp.get('persistance') if 'persistance' in comp else comp.get('persist'),
            },
            'poids_dispo': rec.get('poids_dispo'),
            'manquants': rec.get('manquants'),
        }
        by_key[str(key).upper()] = item
        tv = rec.get('tv') or (key if isinstance(key, str) and ':' in str(key) else None)
        if rec.get('classe') == 'action' and tv:
            by_tv[tv] = item
    meta = {k: doc.get(k) for k in ('generated', 'semaine', 'definition', 'partiel', 'couverture', 'sources_globales')}
    meta['by_tv'] = by_tv
    meta['by_key'] = by_key
    meta['poids'] = doc.get('definition')
    meta['sources'] = doc.get('sources_globales')
    meta['stats'] = doc.get('couverture')
    return meta


_ATT_CACHE = None

def load_attention(refresh=False):
    """Charge le fichier W48 s'il est là, sinon data/attention_apex.json."""
    global _ATT_CACHE
    if _ATT_CACHE is not None and not refresh:
        return _ATT_CACHE
    cands = [
        DATA / 'attention_scores_2026-W48.json',
        Path('/workspace/invest/attention_pilote/attention_scores_2026-W48.json'),
        DATA / 'attention_apex.json',
    ]
    for fn in cands:
        if not fn.exists():
            continue
        doc = json.loads(fn.read_text(encoding='utf-8'))
        if 'actifs' in doc:
            meta = _from_w48(doc)
            print('attention', fn, 'semaine', meta.get('semaine'), 'by_tv', len(meta.get('by_tv') or {}))
            _ATT_CACHE = meta
            return meta
        if 'by_tv' in doc:
            print('attention', fn, 'by_tv', len(doc.get('by_tv') or {}))
            _ATT_CACHE = doc
            return doc
    _ATT_CACHE = {'by_tv': {}, 'by_key': {}}
    return _ATT_CACHE


def attention_of(*keys):
    """Note d'attention 0–100 pour un métal, une crypto ou un ticker, ou None."""
    att = load_attention()
    by_key = att.get('by_key') or {}
    by_tv = att.get('by_tv') or {}
    for k in keys:
        if not k:
            continue
        s = str(k)
        if s in by_tv and by_tv[s].get('attention') is not None:
            return by_tv[s]['attention']
        u = s.upper()
        if u in by_key and by_key[u].get('attention') is not None:
            return by_key[u]['attention']
        for rec in by_key.values():
            if rec.get('nom') and rec['nom'].upper() == u:
                return rec.get('attention')
            if rec.get('yahoo') and str(rec['yahoo']).upper() == u:
                return rec.get('attention')
    return None


def hype_points_90(attention):
    """HYPE métaux purs (comptant) : 0–9 → +90 … 100 → 0. None → non comptée (« – »)."""
    if attention is None:
        return None
    v = max(0, min(100, int(attention)))
    return 9 * (10 - (v // 10))


def main():
    att = load_attention()
    att_by = att.get('by_tv') or {}
    try:
        (DATA / 'attention_apex.json').write_text(json.dumps(att, ensure_ascii=False) + chr(10), encoding='utf-8')
    except Exception as e:
        print('mirror attention_apex.json', e)
    for name in ('apex_achat_v2_pilot.json', 'apex_achat_v2_scores_full.json'):
        p = DATA / name
        if not p.exists():
            continue
        doc = json.loads(p.read_text())
        apply_doc(doc, att_by, att)
        p.write_text(json.dumps(doc, ensure_ascii=False) + '\n')
        n = sum(1 for r in (doc.get('by_tv') or {}).values() if (r.get('points') or {}).get('hype') is not None)
        print('H appliqué', name, 'by_tv avec H', n, '/', len(doc.get('by_tv') or {}))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
