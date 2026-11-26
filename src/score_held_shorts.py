#!/usr/bin/env python3
"""Note SHORT (−50..250) pour les shorts détenus absents de l'univers Meilleurs SHORT.

La note suit la grille SHORT (build_short250) : RSI / MACD / CCI, fondamental inversé,
sentiment maison du secteur inversé, H inversé, MM40 hebdo inversée.
Les titres déjà dans data/apex_short.json (univers) ne sont pas recalculés.
Les notes tenues sont marquées held_position=True pour ne pas entrer dans
la carte Meilleurs SHORT (l'univers n'est pas élargi).

Appelé par build_short250.main() après le calcul de l'univers, et en
autonome pour injecter une note sans recalculer les 15 titres de l'univers.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

DIR = Path(__file__).resolve().parent
ROOT = DIR.parent
sys.path[:0] = [str(DIR), str(ROOT)]

import build_short250 as S  # noqa: E402
import build_apex_achat_v2_pilot as P  # noqa: E402
import score_held_equities as HE  # noqa: E402


def iter_held_shorts():
    seen = set()
    for path in HE._pos_files():
        doc = json.loads(path.read_text(encoding='utf-8'))
        for p in doc.get('positions') or []:
            typ = (p.get('type') or '').lower()
            if typ != 'cfd' and (p.get('sens') or '').lower() != 'short':
                continue
            if typ == 'cfd' and (p.get('sens') or '').lower() != 'short':
                continue
            if (p.get('sens') or '').lower() != 'short':
                continue
            tvs = [x for x in (p.get('fiche_tv'), p.get('tv_note'), p.get('tv')) if x and x != 'pas de note']
            if not tvs:
                continue
            key = tvs[0]
            if key in seen:
                continue
            seen.add(key)
            ticker = key.split(':')[-1] if ':' in key else (p.get('ticker') or '').replace('-CFD', '')
            yield {
                'tv': key,
                'aliases': [t for t in tvs if t != key],
                'ticker': ticker,
                'yahoo': ticker,
                'nom': (p.get('nom') or ticker).replace(' CFD', '').strip(),
                'tab': p.get('tab') or 'actions',
                'source': path.name,
            }



def mark_held(doc):
    """Marque tous les shorts déjà en position (même s'ils sont dans l'univers) et les retire de la liste."""
    by = doc.get('by_tv') or {}
    keys = set(by)
    for a in iter_held_shorts():
        found = None
        for k in [a['tv']] + list(a.get('aliases') or []):
            if k in by:
                found = k
                break
        if not found:
            # ticker sans préfixe
            tick = (a.get('ticker') or '').upper()
            for k, rec in by.items():
                if (rec.get('ticker') or k.split(':')[-1]).upper() == tick:
                    found = k
                    break
        if found:
            by[found]['held_position'] = True
            by[found]['liste'] = False
    liste = sorted(
        [r for r in by.values() if r.get('liste') and not r.get('held_position')],
        key=lambda x: (-x['note'], x['tv']),
    )
    doc['liste'] = [x['tv'] for x in liste]
    doc['n_liste'] = len(liste)
    doc['n'] = sum(1 for r in by.values() if not r.get('held_position'))
    return doc


def missing_held_shorts(by_tv):
    by_tv = by_tv or {}
    out = []
    for a in iter_held_shorts():
        keys = [a['tv']] + list(a.get('aliases') or [])
        if any(k in by_tv and (by_tv[k] or {}).get('note') is not None for k in keys):
            continue
        out.append(a)
    return out


def _categorie(tab):
    if tab == 'energie':
        return 'energie'
    return 'action'


def score_asset_held_short(asset, fgv=None, fg=None):
    tv = asset['tv']
    t = S.tech(tv, asset.get('yahoo'), asset.get('ticker'))
    if not t:
        return {'tv': tv, 'ok': False, 'erreur': 'série hebdomadaire introuvable ou trop courte'}
    try:
        meta = HE.metrics_from_yahoo(asset.get('yahoo'), asset.get('ticker'))
        metrics = meta.get('m') or {}
        sector = meta.get('sector')
    except Exception as e:
        metrics, sector = {}, None
        meta = {'erreur': str(e)}
    bank = False
    _tot, elems = P.fond_points(metrics, P.FOND_RULES_BANQUE if bank else P.FOND_RULES)
    att = None  # H = 0 si l'attention n'est pas déjà en cache (pas d'invention)
    try:
        atj = json.loads((ROOT / 'data' / 'attention_apex.json').read_text(encoding='utf-8')).get('by_tv') or {}
        att = (atj.get(tv) or {}).get('attention')
    except Exception:
        pass
    cat = _categorie(asset.get('tab'))
    base = {
        'tv': tv,
        'nom': asset.get('nom'),
        'ticker': asset.get('ticker'),
        'yahoo': asset.get('yahoo'),
        'categorie': cat,
        'tab': asset.get('tab') or 'actions',
        'univers': 'held',
        'held_position': True,
    }
    sent = S.sentiment_for(tv, sector, None, fgv)
    rec = S.assemble(base, t, S.fond_from(elems, 'manquant'), fgv, att, sent)
    rec['held_position'] = True
    rec['fond_source'] = (meta or {}).get('source')
    rec['liste'] = False  # jamais dans Meilleurs SHORT
    rec['mise'] = None
    rec['expo'] = None
    return rec


def score_missing(by_tv, fgv=None, fg=None):
    if fgv is None:
        try:
            pil = json.loads((ROOT / 'data' / 'apex_achat_v2_pilot.json').read_text(encoding='utf-8'))
            fg = pil.get('fear_greed') or {}
            fgv = fg.get('value') if fg.get('ok') else None
        except Exception:
            fgv = None
    out = {}
    for a in missing_held_shorts(by_tv):
        rec = score_asset_held_short(a, fgv=fgv, fg=fg)
        if rec.get('tv') and rec.get('note') is not None:
            out[rec['tv']] = rec
            print('held short', rec.get('tv'), rec.get('note'), rec.get('ligne') or rec.get('erreur'), flush=True)
        elif rec.get('tv'):
            print('held short échec', rec.get('tv'), rec.get('erreur'), flush=True)
    return out


def inject(doc, held):
    """Ajoute les notes tenues dans by_tv sans les compter dans la liste officielle."""
    if not doc or not held:
        return doc
    by = doc.setdefault('by_tv', {})
    by.update(held)
    # n reste le décompte de l'univers (hors held_position)
    doc['n'] = sum(1 for r in by.values() if not r.get('held_position'))
    liste = [tv for tv, r in by.items() if r.get('liste') and not r.get('held_position')]
    liste = sorted(liste, key=lambda tv: (-(by[tv].get('note') or 0), tv))
    doc['liste'] = liste
    doc['n_liste'] = len(liste)
    return doc


def apply_to_file():
    path = ROOT / 'data' / 'apex_short.json'
    doc = json.loads(path.read_text(encoding='utf-8'))
    held = score_missing(doc.get('by_tv') or {})
    if not held:
        print('held short: rien à ajouter')
        return 0
    inject(doc, held)
    path.write_text(json.dumps(doc, ensure_ascii=False, separators=(',', ':')) + '\n', encoding='utf-8')
    print('wrote', path, 'held', list(held))
    return 0


if __name__ == '__main__':
    raise SystemExit(apply_to_file())
