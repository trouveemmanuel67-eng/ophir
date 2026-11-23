"""Racine du projet OPHIR / APEX (config, data, src)."""
from __future__ import annotations
import os
from pathlib import Path

def root() -> Path:
    env = os.environ.get('APEX_ROOT')
    if env:
        return Path(env).resolve()
    here = Path(__file__).resolve()
    candidates = [here.parents[1]]  # .../patrimoine-dashboard
    if len(here.parents) > 2:
        candidates.append(here.parents[2])
    candidates.append(Path.cwd())
    for p in candidates:
        if (p / 'config' / 'regles.json').exists() or (p / 'src' / 'build.py').exists():
            return p
    return Path('/workspace/invest/patrimoine-dashboard')

def data_dir() -> Path:
    return Path(os.environ.get('APEX_DATA') or (root() / 'data'))

def config_dir() -> Path:
    return Path(os.environ.get('APEX_CONFIG') or (root() / 'config'))

def src_dir() -> Path:
    return root() / 'src'

def site_dir() -> Path:
    env = os.environ.get('APEX_SITE')
    if env:
        return Path(env)
    r = root()
    if (r / 'index.html').exists() and (r / '.git').exists():
        return r
    sibling = r.parent / 'ophir-site'
    if sibling.exists():
        return sibling
    return r
