"""SPCX (SpaceX) : exception APEX dans la section Actions, note dans Mes positions."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT)]

CFG = json.loads((ROOT / 'config' / 'exceptions_actions.json').read_text(encoding='utf-8'))
FOND = json.loads((ROOT / 'data' / 'fondamentaux.json').read_text(encoding='utf-8'))
PILOT = json.loads((ROOT / 'data' / 'apex_achat_v2_pilot.json').read_text(encoding='utf-8'))
SITE = json.loads((ROOT / 'data' / 'apex_achat_v2_site.json').read_text(encoding='utf-8'))
FONDS_JS = (ROOT / 'src' / 'fonds.js').read_text(encoding='utf-8')
POS_JS = (ROOT / 'src' / 'positions.js').read_text(encoding='utf-8')
HELD_PY = (ROOT / 'src' / 'score_held_equities.py').read_text(encoding='utf-8')
FOND_PY = (ROOT / 'src' / 'build_fondamentaux.py').read_text(encoding='utf-8')
PILOT_PY = (ROOT / 'src' / 'build_apex_achat_v2_pilot.py').read_text(encoding='utf-8')


def test_config_exception_spcx():
    tvs = {a['tv'] for a in CFG.get('actions') or []}
    assert 'NASDAQ:SPCX' in tvs
    a = next(x for x in CFG['actions'] if x['tv'] == 'NASDAQ:SPCX')
    assert a['secteur_etf'] == 'XLI'
    assert a['mention'] == 'exception'
    assert a['ipo_date'] == '2026-06-12'


def test_spcx_dans_secteur_industrie_pas_dans_le_top():
    xli = (FOND.get('sectors') or {}).get('XLI') or {}
    tops = {r.get('tv') for r in (xli.get('top') or [])}
    assert 'NASDAQ:SPCX' not in tops
    ex = xli.get('exceptions') or []
    assert any(r.get('tv') == 'NASDAQ:SPCX' and r.get('exception') for r in ex)
    names = {r.get('name') for r in ex}
    assert 'SpaceX' in names


def test_spcx_note_dans_pilot_et_site():
    for doc, label in ((PILOT, 'pilot'), (SITE, 'site')):
        rec = (doc.get('by_tv') or {}).get('NASDAQ:SPCX')
        assert rec, f'NASDAQ:SPCX absent de {label}'
        assert rec.get('ok') is True
        assert rec.get('total') is not None
        assert rec.get('total_max') == 250
        assert rec.get('exception_apex') is True
        assert rec.get('historique_partiel') is True
        assert rec.get('n_closed') == 24
        pts = rec.get('points') or {}
        # Historique trop court : MACD, Fibo, CCI, MM40 valent 0, pas inventés.
        assert pts.get('macd') == 0
        assert pts.get('fibonacci') == 0
        assert pts.get('cci') == 0
        assert pts.get('mm40') == 0
        # RSI 14 calculable (24 semaines) : 40,5 → 0 pt (seuil < 40 non atteint).
        assert pts.get('rsi') == 0
        # Fondamental et sentiment maison Industrie (XLI) sont les seuls apports.
        assert pts.get('fondamental') == 36  # 40 bruts × 0,9
        assert pts.get('fear_greed') == 20
        sent = rec.get('sentiment') or {}
        assert sent.get('cle') == 'us:XLI'
        assert sent.get('points') == 20


def test_pipeline_survit_aux_rafraichissements():
    assert 'exceptions_actions' in HELD_PY
    assert 'EX.assets_for_score' in HELD_PY
    assert 'allow_partial=True' in HELD_PY
    assert 'EX.merge_into(out)' in FOND_PY
    assert 'allow_partial=False' in PILOT_PY
    assert 's.exceptions' in FONDS_JS
    assert 'fl-exc' in FONDS_JS
    assert 'function posPilotRec' in POS_JS
    from apex import sentiment as S
    if hasattr(S.tables, 'cache_clear'):
        S.tables.cache_clear()
    assert S.key_for_tv('NASDAQ:SPCX') == 'us:XLI'


def test_score_asset_sans_partial_reste_refuse():
    """Le seuil de 52 semaines reste obligatoire hors exception."""
    import build_apex_achat_v2_pilot as P
    path, used = P.find_wk(P.yahoo_cands('NASDAQ:SPCX', 'SPCX', 'SPCX'))
    closed, meta, _ = P.load_closed_weekly(path)
    assert len(closed) == 24
    rec = P.score_asset(
        {'tv': 'NASDAQ:SPCX', 'yahoo': 'SPCX', 'ticker': 'SPCX', 'nom': 'SpaceX', 'kind': 'action'},
        None, fond_rules=P.FOND_RULES, closed_bars=closed, allow_partial=False,
    )
    assert rec.get('ok') is False
    assert 'insuffisant' in (rec.get('erreur') or '')
