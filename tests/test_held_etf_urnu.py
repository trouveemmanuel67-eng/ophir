"""URNU : note APEX 250 dans Mes positions, sans revenir dans l'onglet Énergie."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT)]

EN = json.loads((ROOT / 'data' / 'energie.json').read_text(encoding='utf-8'))
BARS = json.loads((ROOT / 'data' / 'apex_bars.json').read_text(encoding='utf-8'))
POS_JS = (ROOT / 'src' / 'positions.js').read_text(encoding='utf-8')
GI_JS = (ROOT / 'src' / 'good_invest.js').read_text(encoding='utf-8')
SENT_PY = (ROOT / 'apex' / 'sentiment.py').read_text(encoding='utf-8')
LONG_PY = (ROOT / 'src' / 'build_long250.py').read_text(encoding='utf-8')


def test_urnu_absent_de_l_onglet_energie():
    tvs = {a.get('tv') for a in EN.get('assets') or []}
    assert 'XETR:URNU' not in tvs
    assert not any((a.get('kind') or '') in {'equity', 'equity_proxy', 'etf_equity'} for a in EN.get('assets') or [])


def test_urnu_note_dans_apex_bars():
    b = (BARS.get('bars') or {}).get('XETR:URNU')
    assert b, 'XETR:URNU doit figurer dans apex_bars pour Mes positions'
    assert b.get('held_only') is True
    rec = b.get('apex10') or {}
    assert rec.get('scale') == 250
    assert rec.get('total_max') == 250
    assert rec.get('note') == 158
    assert rec.get('total') == 158
    assert rec.get('band') == 'vert'
    assert rec.get('hex') == '#22c55e'
    assert rec.get('flag') == 'green'
    assert rec.get('kind') == 'etf'
    pts = (rec.get('decomp') or {}).get('points') or {}
    assert pts.get('RSI') == 10
    assert pts.get('MACD') == 30
    assert pts.get('Fibo') == 20
    assert pts.get('CCI') == 20
    assert pts.get('Fond. ETF') == 30
    assert pts.get('MM40 hebdo') == 28
    assert pts.get('Sentiment Énergie (XLE)') == 20
    # 80 technique + 30 fonda + 28 MM40 + 20 sentiment
    assert rec['note'] == 10 + 30 + 20 + 20 + 30 + 28 + 20
    fond = (rec.get('decomp') or {}).get('fondamental') or {}
    assert fond.get('points') == 30
    assert fond.get('max') == 90
    nc = fond.get('nc') or []
    assert 'Au moins 30 lignes' in nc
    assert any('Cycle uranium' in x for x in nc)
    by_id = {e['id']: e for e in fond.get('elements') or []}
    assert by_id['lignes30']['points'] == 0 and by_id['lignes30']['nc'] is True
    assert by_id['cycle']['points'] == 0 and by_id['cycle']['nc'] is True
    sent = rec.get('sentiment') or {}
    assert sent.get('cle') == 'us:XLE'
    assert sent.get('points') == 20


def test_sentiment_urnu_reste_mappe_hors_onglet():
    from apex import sentiment as S
    if hasattr(S.tables, 'cache_clear'):
        S.tables.cache_clear()
    assert S.key_for_tv('XETR:URNU') == 'us:XLE'
    assert 'T.setdefault(tv, key)' in SENT_PY
    assert 'ENERGIE_TV.items()' in SENT_PY


def test_pipeline_et_mes_positions_relisent_la_barre():
    assert 'score_held_etfs' in LONG_PY
    assert 'HEF.inject()' in LONG_PY
    assert 'function apex10FromKnown' in POS_JS
    assert 'APEX_BARS' in POS_JS
    assert 'if(b.held_only) return;' in GI_JS


def test_iter_held_equities_ignore_toujours_les_etf():
    import score_held_equities as HE
    tvs = {a['tv'] for a in HE.iter_held_equities()}
    assert 'XETR:URNU' not in tvs
