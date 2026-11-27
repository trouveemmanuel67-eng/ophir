#!/usr/bin/env python3
"""Exceptions APEX Actions : titres hors univers quantitatif, conservés en config.

Relu à chaque rafraîchissement (fondamentaux, notes held, sentiment).
Ne rien écrire en dur dans le HTML.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

DIR = Path(__file__).resolve().parent
ROOT = DIR.parent
sys.path[:0] = [str(DIR), str(ROOT)]

CONFIG = ROOT / 'config' / 'exceptions_actions.json'
FOND = ROOT / 'data' / 'fondamentaux.json'


def load():
    if not CONFIG.exists():
        return []
    doc = json.loads(CONFIG.read_text(encoding='utf-8'))
    out = []
    for a in doc.get('actions') or []:
        if not a.get('tv') or not a.get('ticker'):
            continue
        out.append(dict(a))
    return out


def sentiment_map():
    """tv → clé de sentiment maison (ex. NASDAQ:SPCX → us:XLI)."""
    out = {}
    for a in load():
        tv = a.get('tv')
        if not tv:
            continue
        cle = a.get('sentiment_cle')
        if not cle:
            etf = a.get('secteur_etf')
            if etf:
                cle = etf if str(etf).startswith('us:') else 'us:' + etf
        if cle:
            out[tv] = cle
    return out


def assets_for_score():
    """Descripteurs compatibles avec score_held_equities."""
    out = []
    for a in load():
        tv = a['tv']
        ticker = a.get('yahoo') or a['ticker']
        out.append({
            'tv': tv,
            'aliases': [a['ticker'], ticker] if ticker != a['ticker'] else [a['ticker']],
            'ticker': ticker,
            'yahoo': ticker,
            'nom': a.get('nom') or a.get('name') or a['ticker'],
            'kind': 'action',
            'tab': 'actions',
            'industry': a.get('industry'),
            'section': 'Actions USA – ' + (a.get('secteur_nom') or a.get('secteur_etf') or ''),
            'secteur_etf': a.get('secteur_etf'),
            'exception_apex': True,
            'source': 'config/exceptions_actions.json',
        })
    return out


def fond_row(a, metrics=None):
    m = (metrics or {}).get('m') if isinstance(metrics, dict) else None
    return {
        'ticker': a['ticker'],
        'name': a.get('nom') or a.get('name') or a['ticker'],
        'tv': a['tv'],
        'tv_ok': True,
        'yahoo': a.get('yahoo') or a['ticker'],
        'industry': a.get('industry'),
        'exception': True,
        'exception_mention': a.get('mention') or 'exception',
        'm': m or {},
        'retrieved': (metrics or {}).get('retrieved'),
    }


def merge_into(doc, metrics_by_yahoo=None):
    """Ajoute la liste `exceptions` sur chaque secteur concerné (ne touche pas à `top`)."""
    if not isinstance(doc, dict):
        return doc
    sectors = doc.setdefault('sectors', {})
    # reset previous exception lists so a withdrawn name disappears on refresh
    for s in sectors.values():
        if isinstance(s, dict) and 'exceptions' in s:
            s['exceptions'] = []
    metrics_by_yahoo = metrics_by_yahoo or {}
    for a in load():
        etf = a.get('secteur_etf')
        if not etf or etf not in sectors:
            continue
        sec = sectors[etf]
        rows = [r for r in (sec.get('exceptions') or []) if r.get('tv') != a['tv']]
        rows.append(fond_row(a, metrics_by_yahoo.get(a.get('yahoo') or a['ticker'])))
        sec['exceptions'] = rows
    return doc


def merge_fondamentaux_file(metrics_by_yahoo=None):
    if not FOND.exists():
        return None
    doc = json.loads(FOND.read_text(encoding='utf-8'))
    merge_into(doc, metrics_by_yahoo)
    FOND.write_text(json.dumps(doc, ensure_ascii=False) + '\n', encoding='utf-8')
    return doc


def inject_site_by_tv(held_compact):
    """Fusionne les notes compactes dans apex_achat_v2_site.json (embarqué dans index.html)."""
    path = ROOT / 'data' / 'apex_achat_v2_site.json'
    if not path.exists() or not held_compact:
        return
    doc = json.loads(path.read_text(encoding='utf-8'))
    doc.setdefault('by_tv', {}).update(held_compact)
    path.write_text(json.dumps(doc, ensure_ascii=False) + '\n', encoding='utf-8')
