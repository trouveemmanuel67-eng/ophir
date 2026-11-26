"""Sentiment sectoriel / par classe d'actifs (t537u) : remplace le CNN Fear & Greed global
comme valeur d'entrée du critère F&G des notes LONG et SHORT. Les barèmes ne changent pas.

Rattachement d'un actif (tv) à son sentiment, dans cet ordre :
 1. tables explicites tirées des fichiers du site : métaux (metaux.json, par métal), obligations
    (obligations.json, par segment), énergie (energie.json, par groupe et par actif), ETF de devise ;
 2. actions : secteur GICS (sous-section APEX : « Santé », « USA – XLV »…) et pays :
    USA, Canada, Japon, Corée → ETF sectoriel SPDR US ; France, Allemagne, Suisse → ETF sectoriel MSCI Europe ;
 3. ETF de section (ZPDx, paniers APEX:PANIER-FR-*) → leur secteur ; têtes de marché pays → indice du pays ;
 4. si aucun secteur ni classe n'est trouvé : 0 point (pas de repli CNN).
Crypto : classe « crypto » (alternative.me via sentiment_secteurs.json).
"""
from __future__ import annotations

import json
import math
import re
from functools import lru_cache

from . import paths

GICS_US = {
    'Information Technology': 'XLK', 'Financials': 'XLF', 'Energy': 'XLE', 'Health Care': 'XLV',
    'Industrials': 'XLI', 'Communication Services': 'XLC', 'Consumer Discretionary': 'XLY',
    'Consumer Staples': 'XLP', 'Utilities': 'XLU', 'Real Estate': 'XLRE', 'Materials': 'XLB',
}
GICS_EU = {
    'Information Technology': 'XS8R', 'Health Care': 'DXSE', 'Financials': 'XS7R', 'Communication Services': 'DXSG',
    'Consumer Discretionary': 'SPYR', 'Consumer Staples': 'DXSK', 'Industrials': 'DXSL', 'Materials': 'DXSC',
    'Utilities': 'XS6R', 'Energy': 'EXH1', 'Real Estate': 'EXI5',
}
SOUS_GICS = {
    'Communication': 'Communication Services', 'XLC': 'Communication Services',
    'Consommation discrétionnaire': 'Consumer Discretionary', 'XLY': 'Consumer Discretionary',
    'Consommation de base': 'Consumer Staples', 'XLP': 'Consumer Staples',
    'Énergie': 'Energy', 'XLE': 'Energy', 'Pétrole et gaz': 'Energy', 'Gaz naturel': 'Energy', 'Charbon': 'Energy',
    'Finance': 'Financials', 'XLF': 'Financials',
    'Santé': 'Health Care', 'XLV': 'Health Care',
    'Industrie': 'Industrials', 'XLI': 'Industrials', 'Machines': 'Industrials', 'Hydrogène et stockage': 'Industrials',
    'Matériaux': 'Materials', 'XLB': 'Materials',
    'Technologie': 'Information Technology', 'XLK': 'Information Technology', 'Solaire': 'Information Technology',
    'Immobilier': 'Real Estate', 'XLRE': 'Real Estate',
    'Services aux collectivités': 'Utilities', 'XLU': 'Utilities', 'Électricité et utilities': 'Utilities',
}
# clés courtes des sections France (pays.json, paniers, pilotes fr_*)
FR_KEY_GICS = {
    'com': 'Communication Services', 'cd': 'Consumer Discretionary', 'cs': 'Consumer Staples', 'en': 'Energy',
    'fin': 'Financials', 'sante': 'Health Care', 'ind': 'Industrials', 'mat': 'Materials', 'immo': 'Real Estate',
    'tech': 'Information Technology', 'util': 'Utilities',
}
EU_PAYS = ('France', 'Allemagne', 'Suisse', 'Belgique', 'Pays-Bas', 'Italie', 'Espagne', 'Royaume-Uni', 'Europe')
PAYS_HEAD = {'fr': 'pays:FR', 'de': 'pays:DE', 'ca': 'pays:CA', 'ch': 'pays:CH'}
METAL_KEY = {'or': 'metal:or', 'argent': 'metal:argent', 'platine': 'metal:platine', 'palladium': 'metal:palladium'}
ENERGIE_TV = {  # actifs énergie hors règle de groupe (secteur GICS réel)
    'NASDAQ:ENPH': 'us:XLK', 'NASDAQ:CSIQ': 'us:XLK', 'XETR:ENR': 'eu:DXSL', 'NASDAQ:BLDP': 'us:XLI',
    'NASDAQ:CEG': 'us:XLU', 'NYSE:CCJ': 'us:XLE', 'NYSE:BTU': 'us:XLE', 'XETR:URNU': 'us:XLE', 'XETR:U3O8': 'us:XLE',
    'XETR:XDW0': 'us:XLE', 'XETR:ZPDU': 'us:XLU', 'TVC:UKOIL': 'energie:brent', 'XETR:BNQ9': 'energie:gaz',
    # ETC et contrats à terme : sentiment de la matière, pas du secteur actions XLE.
    'LSE:CRUD': 'energie:petrole', 'XETR:OD7F': 'energie:petrole',
    'XETR:OOEA': 'energie:brent', 'LSE:BRNT': 'energie:brent',
    'LSE:NGAS': 'energie:gaz', 'XETR:EGAS': 'energie:gaz', 'NYMEX:NG1!': 'energie:gaz',
}
ETF_DEVISE_TV = {'ASX:SEMI': 'us:XLK', 'TSX:XCHP': 'us:XLK', 'NASDAQ:RING': 'metaux', 'LSE:AUCP': 'metaux',
                 'SIX:AUCO': 'metaux', 'TSE:1631': 'us:XLF'}
HELD_EQUITY_TV = {'NASDAQ:MSTR': 'us:XLK', 'NYSE:SMR': 'us:XLE'}


def fg_long(v):
    """Barème LONG inchangé : floor(|50 − v| / 10) × 10, signé, max ±50."""
    if v is None:
        return None
    d = 50.0 - float(v)
    n = min(5, int(math.floor(abs(d) / 10.0)))
    return n * 10 if d >= 0 else -n * 10


def fg_short(v):
    """Barème SHORT inchangé : floor(|v − 50| / 10) × 6, signé, max ±30."""
    if v is None:
        return None
    d = float(v) - 50.0
    n = min(5, int(math.floor(abs(d) / 10.0)))
    return n * 6 if d >= 0 else -n * 6


def _load(name):
    p = paths.data_dir() / name
    return json.loads(p.read_text(encoding='utf-8')) if p.exists() else {}


@lru_cache(maxsize=1)
def data():
    return _load('sentiment_secteurs.json')


def get(key):
    """Enregistrement de sentiment pour une clé ('us:XLV', 'eu:DXSE', 'metaux', 'cnn'…)."""
    d = data()
    if not key:
        return None
    if key == 'cnn':
        r = dict(d.get('cnn') or {})
        if r:
            r['court'] = 'CNN global (repli)'
        return r or None
    if key.startswith('us:'):
        return (d.get('secteurs_us') or {}).get(key[3:])
    if key.startswith('eu:'):
        return (d.get('secteurs_eu') or {}).get(key[3:])
    return (d.get('classes') or {}).get(key)


def _walk_tvs(obj, acc):
    if isinstance(obj, dict):
        for k in ('tv', 'tv_alt'):
            v = obj.get(k)
            if isinstance(v, str):
                acc.add(v)
            elif isinstance(v, list):
                acc.update(x for x in v if isinstance(x, str))
        for v in obj.values():
            _walk_tvs(v, acc)
    elif isinstance(obj, list):
        for v in obj:
            _walk_tvs(v, acc)


@lru_cache(maxsize=1)
def tables():
    T = {}
    m = _load('metaux.json')
    for r in m.get('rows') or []:
        key = METAL_KEY.get(r.get('key'))
        acc = set()
        _walk_tvs(r, acc)
        for tv in acc:
            T.setdefault(tv, key)
    o = _load('obligations.json')
    for s in o.get('segments') or []:
        key = 'oblig:' + s['key']
        acc = set()
        _walk_tvs(s, acc)
        for tv in acc:
            T.setdefault(tv, key)
    e = _load('energie.json')
    for a in e.get('assets') or []:
        tv = a.get('tv')
        if not tv:
            continue
        g, kind = a.get('groupe') or '', a.get('kind') or ''
        eur = (a.get('currency') == 'EUR')
        if tv in ENERGIE_TV:
            key = ENERGIE_TV[tv]
        elif kind == 'futures':
            if tv == 'NYMEX:NG1!' or g == 'Gaz naturel':
                key = 'energie:gaz'
            elif tv in ('TVC:UKOIL',) or a.get('yahoo') == 'BZ=F':
                key = 'energie:brent'
            else:
                key = 'energie:petrole'
        elif g == 'Gaz naturel' and kind == 'etc':
            key = 'energie:gaz'
        elif g in ('Pétrole et gaz', 'Gaz naturel'):
            key = 'eu:EXH1' if eur else 'us:XLE'
        elif g == 'Électricité et utilities':
            key = 'eu:XS6R' if eur else 'us:XLU'
        else:
            key = 'eu:EXH1' if eur else 'us:XLE'
        T[tv] = key
    T.update(ETF_DEVISE_TV)
    T.update(HELD_EQUITY_TV)
    # ETF sectoriels US et leurs équivalents UCITS
    s = _load('secteurs.json')
    for x in s.get('sectors') or []:
        for tv in (x.get('tv'), x.get('ref_us')):
            if tv:
                T.setdefault(tv, 'us:' + x['sym'])
    for sym in GICS_US.values():
        T.setdefault('AMEX:' + sym, 'us:' + sym)
    # têtes de marché pays
    p = _load('pays.json')
    for c in p.get('countries') or []:
        h = c.get('head') or {}
        tv = h.get('tv') if isinstance(h, dict) else None
        if tv and c.get('cc') in PAYS_HEAD:
            T[tv] = PAYS_HEAD[c['cc']]
    return T


@lru_cache(maxsize=1)
def actifs():
    a = _load('../config/actifs.json') if False else json.loads((paths.root() / 'config' / 'actifs.json').read_text(encoding='utf-8'))
    return {x['tv']: x for x in a.get('actifs') or [] if x.get('tv')}


def key_for_section(section, sous):
    section = section or ''
    if section.startswith('Métaux'):
        n = section.split('–')[-1].strip().lower()
        return METAL_KEY.get(n, 'metaux')
    if section.startswith('Crypto'):
        return 'crypto'
    if section.startswith('Obligations'):
        return None
    gics = SOUS_GICS.get(sous or '')
    if not gics:
        return None
    pays = section.split('–')[0].strip()
    if pays in EU_PAYS:
        return 'eu:' + GICS_EU[gics]
    return 'us:' + GICS_US[gics]


def key_for_tv(tv):
    if not tv:
        return None
    T = tables()
    if tv in T and T[tv]:
        return T[tv]
    m = re.match(r'APEX:PANIER-FR-(\w+)$', tv)
    if m:
        k = {'SANTE': 'sante'}.get(m.group(1), m.group(1).lower())
        if k in FR_KEY_GICS:
            return 'eu:' + GICS_EU[FR_KEY_GICS[k]]
    a = actifs().get(tv)
    if a:
        k = key_for_section(a.get('section'), a.get('sous_section'))
        if k:
            return k
    return None


def key_for_pilote(pk):
    """Clé des pilotes : 'XLV' (US) ou 'fr_sante' (France)."""
    if pk in GICS_US.values():
        return 'us:' + pk
    if pk.startswith('fr_') and pk[3:] in FR_KEY_GICS:
        return 'eu:' + GICS_EU[FR_KEY_GICS[pk[3:]]]
    return None


def key_for_row(cc, rowkey):
    gics = FR_KEY_GICS.get(rowkey or '')
    if not gics:
        return None
    if cc in ('fr', 'de', 'ch'):
        return 'eu:' + GICS_EU[gics]
    return 'us:' + GICS_US[gics]


def resolve(key, *, repli_cnn=False):
    """(clé effective, enregistrement). Plus de repli CNN dans les notes (repli_cnn=False)."""
    r = get(key) if key else None
    if r and r.get('value') is not None:
        return key, r
    if repli_cnn:
        return 'cnn', get('cnn')
    return None, None


def of(tv=None, key=None, classe=None, pilote=None, cc=None, row=None):
    """Résout le sentiment maison d'un actif. Retourne (clé, enregistrement) ou (None, None)."""
    k = key
    if k is None and tv:
        k = key_for_tv(tv)
    if k is None and pilote:
        k = key_for_pilote(pilote)
    if k is None and row:
        k = key_for_row(cc, row)
    if k is None and classe:
        k = classe
    return resolve(k)


def payload(key, rec, inv=False, short=False):
    """Bloc sentiment à poser sur une note (hors CNN)."""
    if not rec or rec.get('value') is None:
        return None
    val = float(rec['value'])
    pts = fg_short(val) if short else fg_long(val)
    if inv:
        pts = -pts
    return {
        'cle': key, 'nom': court(key, rec), 'valeur': round(val, 1),
        'zone': rec.get('label'), 'points': pts, 'inverse': inv,
        'date': rec.get('date'), 'repli_cnn': False,
    }


def court(key, rec):
    return (rec or {}).get('court') or key
