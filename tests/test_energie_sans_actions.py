"""L'onglet Énergie ne propose plus d'actions ni d'ETF d'actions."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INTERDITS = {'equity', 'equity_proxy', 'etf_equity'}
OK = {'futures', 'etc'}


def test_energie_uniquement_contrats_et_etc():
    en = json.loads((ROOT / 'data' / 'energie.json').read_text(encoding='utf-8'))
    kinds = {a.get('kind') for a in en['assets']}
    assert kinds <= OK, kinds
    assert not any(a.get('kind') in INTERDITS for a in en['assets'])
    assert any(a.get('kind') == 'futures' for a in en['assets'])
    assert any(a.get('kind') == 'etc' for a in en['assets'])
    # Tickers d'actions / ETF d'actions précédemment proposés dans l'onglet.
    interdits_tv = {
        'EURONEXT:TTE', 'NYSE:XOM', 'NASDAQ:ENPH', 'XETR:XDW0', 'XETR:URNU',
        'XETR:U3O8', 'NYSE:CCJ', 'NYSE:BTU', 'XETR:ZPDU', 'XETR:ENR',
    }
    present = {a.get('tv') for a in en['assets']}
    assert not (present & interdits_tv), present & interdits_tv


def test_energie_etc_disponibles_xtb():
    en = json.loads((ROOT / 'data' / 'energie.json').read_text(encoding='utf-8'))
    dispo = json.loads((ROOT / 'data' / 'disponibilites.json').read_text(encoding='utf-8'))
    etcs = [a for a in en['assets'] if a.get('kind') == 'etc']
    assert etcs
    for a in etcs:
        rec = (dispo.get('symbols') or {}).get(a['tv']) or {}
        assert rec.get('xtb') is True, a['tv']
        assert (a.get('apex10') or {}).get('scale') == 250, a['tv']
