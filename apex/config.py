"""Lecture de config/regles.json, config/actifs.json et data/elliott_overrides.json."""
from __future__ import annotations
import json
from functools import lru_cache
from pathlib import Path

from . import paths

@lru_cache(maxsize=1)
def regles() -> dict:
    p = paths.config_dir() / 'regles.json'
    if not p.exists():
        raise FileNotFoundError(f'config/regles.json introuvable : {p}')
    return json.loads(p.read_text(encoding='utf-8'))

@lru_cache(maxsize=1)
def actifs() -> list:
    p = paths.config_dir() / 'actifs.json'
    if not p.exists():
        return []
    return json.loads(p.read_text(encoding='utf-8')).get('actifs') or []

@lru_cache(maxsize=1)
def actifs_by_tv() -> dict:
    return {a['tv']: a for a in actifs() if a.get('tv')}

def actifs_a_suivre() -> list:
    """Univers réduit (t322u) : visibles + titres détenus hors pays. Exclut univers=hors."""
    out = []
    for a in actifs():
        u = a.get('univers')
        if u == 'hors' or a.get('visible') is False:
            continue
        out.append(a)
    return out


@lru_cache(maxsize=1)
def overrides() -> dict:
    """Overrides Elliott : le fichier reste à part et prime."""
    p = paths.data_dir() / 'elliott_overrides.json'
    if not p.exists():
        # parfois sous config/
        q = paths.config_dir() / 'elliott_overrides.json'
        p = q if q.exists() else p
    if not p.exists():
        return {}
    raw = json.loads(p.read_text(encoding='utf-8'))
    if isinstance(raw, dict) and 'overrides' in raw:
        return raw['overrides'] or {}
    return raw if isinstance(raw, dict) else {}

def reload():
    """Invalide les caches (utile dans les tests)."""
    regles.cache_clear()
    actifs.cache_clear()
    actifs_by_tv.cache_clear()
    overrides.cache_clear()

def actif(tv: str | None) -> dict | None:
    if not tv:
        return None
    idx = actifs_by_tv()
    if tv in idx:
        return idx[tv]
    if ':' in tv:
        suf = tv.split(':', 1)[-1]
        for k, a in idx.items():
            if k.split(':', 1)[-1] == suf:
                return a
    return None
