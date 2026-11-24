#!/usr/bin/env python3
"""Applique l'apport H (attention / hype, à contre-courant) aux notes APEX actions.

Note APEX actions = RSI + MACD + Fibo + CCI (110) + Fondamental (90) + F&G (±50) + H (±30)
=> échelle −80 à 280.  H = (50 − attention) × 0,6 ; attention absente => H = 0, affiché « – ».
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

SCALE_MIN, SCALE_MAX = -80, 280
HYPE_ABS = 30
# 5 tranches égales de 72 points sur [−80, 280] (mêmes proportions 20/40/60/80 % que l'ancienne échelle)
BANDS = [
    ('violet', -80, -8, '#9d54ff'),
    ('rouge', -8, 64, '#ff2d2d'),
    ('orange', 64, 136, '#ff8c1a'),
    ('vert', 136, 208, '#22c55e'),
    ('cyan', 208, 281, '#00e5ff'),
]
SEUIL_MEILLEURES = 136
HEX = {n: h for n, _a, _b, h in BANDS}
LABEL = {'violet': 'Très faible', 'rouge': 'Faible', 'orange': 'Neutre', 'vert': 'Favorable', 'cyan': 'Très favorable'}
KEEP_PAYS = ('USA', 'France')


def band_of(t):
    t = float(t)
    if t >= 208: return 'cyan'
    if t >= 136: return 'vert'
    if t >= 64: return 'orange'
    if t >= -8: return 'rouge'
    return 'violet'


def scale_obj(old=None):
    s = dict(old or {})
    s.update({'min': SCALE_MIN, 'max': SCALE_MAX, 'tech_max': 110, 'fond_max': 90, 'fg_abs': 50, 'hype_abs': HYPE_ABS,
              'seuil_meilleures_entrees': SEUIL_MEILLEURES,
              'regle_bandes': '5 tranches égales de 72 points sur −80 à 280 (proportions de l’échelle −50 à 250 conservées)',
              'bandes': [{'id': n, 'de': lo, 'a': (hi if hi < 281 else 280), 'hex': hx} for n, lo, hi, hx in BANDS],
              'drapeaux_5': [
                  {'id': 'violet', 'de': None, 'a': -8, 'regle': '< −8'},
                  {'id': 'rouge', 'de': -8, 'a': 64, 'regle': '−8 ≤ n < 64'},
                  {'id': 'orange', 'de': 64, 'a': 136, 'regle': '64 ≤ n < 136'},
                  {'id': 'vert', 'de': 136, 'a': 208, 'regle': '136 ≤ n < 208'},
                  {'id': 'cyan', 'de': 208, 'a': None, 'regle': '≥ 208'},
              ]})
    return s


def _fmt(k, v):
    if v is None:
        return f'{k} –' if k == 'H' else f'{k} n.d.'
    return f"{k} {'+' if v > 0 else ''}{v}"


def apply_rec(rec, h, att=None):
    """Met à jour un enregistrement noté (ok) avec l'apport H (None = « – »)."""
    if not rec or not rec.get('ok') or not isinstance(rec.get('points'), dict):
        return rec
    p = rec['points']
    p['hype'] = h
    base = sum(int(p.get(k) or 0) for k in ('rsi', 'macd', 'fibonacci', 'cci', 'fondamental', 'fear_greed'))
    total = base + (h or 0)
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
    return {'valeur': a['attention'], 'H': a['H'], 'trends': c.get('trends'), 'mentions': c.get('mentions'),
            'volume': c.get('volume'), 'persistance': c.get('persist'), 'poids_dispo': a.get('poids_dispo'),
            'manquants': [m for m in (a.get('manquants') or []) if m not in ('X', 'StockTwits')]}


def apply_doc(doc, att_by, att_meta=None):
    """Applique H à un document pilote (apex_achat_v2_pilot.json ou scores_full)."""
    pil = doc.get('pilotes') or {}
    res = {}  # tv -> (h, att)
    for sid, p in pil.items():
        pays = p.get('pays') or ('USA' if str(sid).startswith('XL') else None)
        hs = []
        names = []
        for a in p.get('actions') or []:
            tv = a.get('tv')
            att = att_compact(att_by.get(tv)) if pays in KEEP_PAYS else None
            h = att['H'] if att else None
            apply_rec(a, h, att)
            res[tv] = (h, att)
            if h is not None:
                hs.append(h); names.append(a.get('ticker') or tv)
        etf = p.get('etf') or {}
        if pays in KEEP_PAYS and hs:
            h = int(round(sum(hs) / len(hs)))
            att = {'valeur': None, 'H': h, 'moyenne_de': names, 'n': len(hs),
                   'precision': f'Moyenne arrondie des H de {len(hs)} action(s) affichée(s)'}
        else:
            h, att = None, None
        apply_rec(etf, h, att)
        if etf.get('tv'):
            res[etf['tv']] = (h, att)
    # rétrocompatibilité : copie « Communication » à la racine du document (etf / actions)
    for r in [doc.get('etf')] + list(doc.get('actions') or []):
        if isinstance(r, dict) and r.get('tv'):
            apply_rec(r, *res.get(r['tv'], (None, None)))
    for tv, r in (doc.get('by_tv') or {}).items():
        if tv in res:
            apply_rec(r, *res[tv])
        else:
            apply_rec(r, None, None)
    doc['scale'] = scale_obj(doc.get('scale'))
    if att_meta:
        doc['attention_meta'] = {k: att_meta.get(k) for k in ('generated', 'semaine', 'definition', 'poids', 'sources', 'stats')}
    return doc


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
