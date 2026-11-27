#!/usr/bin/env python3
"""Note APEX (−50..250) des ETF détenus absents des onglets notés.

Cause typique : un ETF actions (ex. URNU, uranium) a été retiré des suggestions
d'achat de l'onglet Énergie, donc plus écrit dans energie.json / apex_bars ;
Mes positions ne montrait plus de pastille /250.

La note suit la grille ETF énergie habituelle (technique 110 à contre-courant,
sentiment ±50 à contre-courant, fondamental ETF 90, MM40 hebdo jusqu'à +30).
Un critère manquant vaut 0, sans redistribution.

Appelé par build_long250 après sync_bars_energie. La note est écrite dans
apex_bars.json (entrée held_only) pour que apex10FromKnown la relise, sans
réintroduire l'ETF dans l'onglet Énergie ni dans les suggestions d'achat.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

DIR = Path(__file__).resolve().parent
ROOT = DIR.parent
sys.path[:0] = [str(DIR), str(ROOT)]

from apex import long250 as L  # noqa: E402
from apex import sentiment as SENT  # noqa: E402

ENERGIE_ISIN = {v: k for k, v in L.ENERGIE_ETF.items()}
D = ROOT / 'data'


def _load(name):
    p = D / name
    return json.loads(p.read_text(encoding='utf-8')) if p.exists() else {}


def _save(name, obj):
    (D / name).write_text(json.dumps(obj, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')


def _pos_files():
    for name in ('positions.json', 'positions_revolut.json', 'positions_revolutx.json'):
        p = D / name
        if p.exists():
            yield p


def _actifs():
    doc = json.loads((ROOT / 'config' / 'actifs.json').read_text(encoding='utf-8'))
    return {a.get('tv'): a for a in (doc.get('actifs') or []) if a.get('tv')}


def _yahoo_of(tv, asset=None, ticker=None):
    if asset and asset.get('yahoo'):
        return asset['yahoo']
    if tv and tv.startswith('XETR:') and ':' in tv:
        return tv.split(':', 1)[1] + '.DE'
    return ticker


def iter_held_etfs():
    """ETF détenus (type etf), clés TradingView de fiche."""
    seen = set()
    actifs = _actifs()
    for path in _pos_files():
        doc = json.loads(path.read_text(encoding='utf-8'))
        for p in doc.get('positions') or []:
            typ = (p.get('type') or '').lower()
            if typ != 'etf':
                continue
            st = str(p.get('statut') or 'active').lower()
            if st not in ('active', 'en_attente'):
                continue
            tvs = [p.get('fiche_tv'), p.get('tv_note'), p.get('tv')]
            tvs = [t for t in tvs if t and t != 'pas de note']
            if not tvs:
                continue
            key = tvs[0]
            if key in seen:
                continue
            seen.add(key)
            asset = actifs.get(key) or {}
            ticker = p.get('ticker') or (key.split(':')[-1] if ':' in key else key)
            isin = asset.get('isin') or ENERGIE_ISIN.get(key)
            if not isin:
                src = p.get('rendement_source') or ''
                import re
                m = re.search(r'\b([A-Z]{2}[A-Z0-9]{10})\b', src)
                if m:
                    isin = m.group(1)
            yield {
                'tv': key,
                'aliases': [t for t in tvs if t != key],
                'ticker': ticker,
                'yahoo': _yahoo_of(key, asset, ticker),
                'nom': p.get('fiche_nom') or p.get('nom') or ticker,
                'isin': isin,
                'tab': p.get('tab'),
                'groupe': (asset.get('sous_section') or asset.get('section') or ''),
                'source': path.name,
            }


def _has_note(tv, aliases=None):
    keys = [tv] + list(aliases or [])
    bars = (_load('apex_bars.json').get('bars') or {})
    for k in keys:
        rec = (bars.get(k) or {}).get('apex10') or {}
        if rec.get('note') is not None and rec.get('display') != '–' and rec.get('held_only') is not True:
            return True
    en = {a.get('tv'): a for a in (_load('energie.json').get('assets') or [])}
    for k in keys:
        rec = (en.get(k) or {}).get('apex10') or {}
        if rec.get('note') is not None and rec.get('display') != '–':
            return True
    ob = _load('obligations.json')
    for s in ob.get('segments') or []:
        if s.get('tv') in keys:
            rec = s.get('apex10_panier') or s.get('apex10') or {}
            if rec.get('note') is not None:
                return True
        for e in s.get('list') or []:
            if e.get('tv') in keys:
                rec = e.get('apex10') or {}
                if rec.get('note') is not None:
                    return True
    pilot = (_load('apex_achat_v2_site.json').get('by_tv') or {})
    for k in keys:
        rec = pilot.get(k) or {}
        if rec.get('total') is not None:
            return True
    return False


def is_energie_etf(asset):
    if asset.get('tv') in ENERGIE_ISIN or asset.get('isin') in L.ENERGIE_ETF:
        return True
    tab = (asset.get('tab') or '').lower()
    if tab == 'energie':
        return True
    g = (asset.get('groupe') or '').lower()
    return 'uranium' in g or 'nucléaire' in g or 'nucleaire' in g


def missing_held():
    out = []
    for a in iter_held_etfs():
        if _has_note(a['tv'], a.get('aliases')):
            continue
        if not is_energie_etf(a):
            continue
        out.append(a)
    return out


def score_energie_etf(asset):
    """Grille ETF énergie : technique 110 + fonda 90 + sentiment ±50 + MM40 ≤ 30."""
    # tables() a pu être caché avant le correctif ENERGIE_TV : on force le rechargement.
    if hasattr(SENT, 'tables') and hasattr(SENT.tables, 'cache_clear'):
        SENT.tables.cache_clear()
    tv = asset.get('tv')
    yahoo = asset.get('yahoo')
    isin = asset.get('isin') or ENERGIE_ISIN.get(tv)
    groupe = asset.get('groupe') or 'Nucléaire et uranium'
    t, used = L.tech_of(tv, yahoo, asset.get('ticker'))
    fpts, fnc, fel = L.energie_etf_fond(isin, groupe, tv)
    blocks = [
        ('RSI', t and t['rsi']),
        ('MACD', t and t['macd']),
        ('Fibo', t and t['fibonacci']),
        ('CCI', t and t['cci']),
        ('Fond. ETF', fpts),
    ]
    g = L.house(tv=tv)
    fgp, flab, fmeta = L.sent_pack(g)
    rec = L.assemble(blocks, fgp, flab, {
        'fondamental': {'points': fpts, 'max': 90, 'elements': fel, 'nc': fnc},
        'technique': {'symbole': used, 'date_cloture': t and t['date_cloture'], 'detail': t and t['detail']} if t else {'erreur': 'série hebdomadaire introuvable'},
        'fear_greed': fmeta,
        'sentiment': g.get('payload'),
    }, mm40=L.mm40_of(tv, yahoo, asset.get('ticker')))
    rec['fond'] = fpts
    if g.get('payload'):
        rec['sentiment'] = g['payload']
    if not t:
        rec.update({'note': None, 'display': '–', 'total': None, 'erreur': 'série hebdomadaire introuvable'})
    rec['held_only'] = True
    rec['hors_univers_position'] = (
        f"{asset.get('ticker') or tv} · ETF détenu hors onglet Énergie "
        f"(retiré des suggestions d'achat, note conservée pour Mes positions)"
    )
    rec['tv'] = tv
    rec['yahoo'] = yahoo
    rec['isin'] = isin
    rec['nom'] = asset.get('nom')
    rec['kind'] = 'etf'
    rec['regles'] = 'apex_etf_energie_held'
    return rec


def score_missing():
    out = {}
    for a in missing_held():
        rec = score_energie_etf(a)
        if rec.get('tv'):
            out[rec['tv']] = rec
            print('held_etf', rec.get('tv'), rec.get('display') or rec.get('erreur'), flush=True)
    return out


def _bar_entry(rec):
    tech = ((rec.get('decomp') or {}).get('technique') or {})
    return {
        'ok': True,
        'date': tech.get('date_cloture') or rec.get('date'),
        'held_only': True,
        'apex10': rec,
    }


def _find_object(raw, start):
    """Index de la '}' qui ferme l'objet commençant à raw[start] == '{'."""
    if start >= len(raw) or raw[start] != '{':
        raise ValueError('pas un objet JSON')
    depth = 0
    in_str = False
    esc = False
    for i in range(start, len(raw)):
        c = raw[i]
        if in_str:
            if esc:
                esc = False
            elif c == '\\':
                esc = True
            elif c == '"':
                in_str = False
            continue
        if c == '"':
            in_str = True
        elif c == '{':
            depth += 1
        elif c == '}':
            depth -= 1
            if depth == 0:
                return i
    raise ValueError('objet JSON non refermé')


def _upsert_bar_text(raw, tv, entry):
    """Insère ou remplace une entrée dans l'objet bars, sans reformater le fichier."""
    key = json.dumps(tv, ensure_ascii=False)
    token = key + ': '
    marker = '"bars": {'
    pos = raw.find(marker)
    if pos < 0:
        raise RuntimeError('apex_bars.json : objet bars introuvable')
    body_at = pos + len(marker)
    # Cherche "TV": { à l'intérieur de bars, pas ailleurs.
    bars_end = _find_object(raw, pos + len('"bars": '))
    hit = raw.find(token, body_at, bars_end)
    blob = json.dumps({tv: entry}, ensure_ascii=False)[1:-1]
    if hit >= 0:
        colon = raw.find(':', hit)
        brace = raw.find('{', colon)
        end = _find_object(raw, brace)
        return raw[:hit] + blob + raw[end + 1:]
    insert = blob + ('' if raw[body_at:body_at + 1] in ('}', '') else ', ')
    return raw[:body_at] + insert + raw[body_at:]


def inject(scores=None):
    """Écrit les notes held_only dans apex_bars.json (crée l'entrée si besoin).

    Insertion chirurgicale : le reste du fichier n'est pas reformaté.
    """
    if scores is None:
        scores = score_missing()
    if not scores:
        print('held_etf : rien à injecter', flush=True)
        return scores
    path = D / 'apex_bars.json'
    raw = path.read_text(encoding='utf-8')
    n = 0
    for tv, rec in scores.items():
        if rec.get('note') is None:
            continue
        raw = _upsert_bar_text(raw, tv, _bar_entry(rec))
        n += 1
    json.loads(raw)  # valide avant d'écrire
    path.write_text(raw, encoding='utf-8')
    print('apex_bars : notes ETF détenus injectées', n, '/', len(scores), flush=True)
    return scores


if __name__ == '__main__':
    inject()
