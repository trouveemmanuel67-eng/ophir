"""t456u / t549u : JSON racine = captures 25/11 09 h 50 + CFD 10 h 14."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FILES = ('positions.json', 'positions_revolut.json', 'positions_revolutx.json')
STALE = {'NKE', 'STLA', 'PKX', 'BTC', 'AGNC', 'NLY', 'PDSE', 'MBG', 'PAH3', 'BKNG', 'PPX', 'HMI', 'DASH', 'MC', 'XUTL'}
NEED = {'XAU', 'XAG', 'XPT', 'XPD', 'CAT', 'AVGO', 'MU', 'HWM', 'GOOGL', 'ENPH', 'LRCX', 'URNU'}


def _ticks(path):
    d = json.loads(path.read_text(encoding='utf-8'))
    return [p.get('ticker') for p in (d.get('positions') or [])]


def test_racine_identique_a_data():
    for fn in FILES:
        racine = ROOT / fn
        data = ROOT / 'data' / fn
        assert data.exists(), fn
        assert racine.exists(), f'{fn} manquant à la racine (index.html le fetch au démarrage)'
        assert racine.read_bytes() == data.read_bytes(), f'{fn} racine ≠ data/'


def test_releve_25_11_dans_le_json_fethe():
    ticks = _ticks(ROOT / 'positions.json')
    stale = STALE.intersection(ticks)
    assert not stale, f'lignes obsolètes encore présentes : {sorted(stale)}'
    missing = NEED.difference(ticks)
    assert not missing, f'manque {sorted(missing)}'
    # ordres en cours
    book = json.loads((ROOT / 'positions.json').read_text(encoding='utf-8'))
    pending = [p['ticker'] for p in book['positions'] if p.get('statut') == 'en_attente']
    assert pending == []
    assert book.get('n_en_attente') == 0
    metals = [p['ticker'] for p in book['positions'] if p.get('ticker') in {'XAU', 'XAG', 'XPT', 'XPD'}]
    assert len(metals) == 4
    cfds = [p for p in book['positions'] if (p.get('type') or '').lower() == 'cfd']
    assert {p['ticker'] for p in cfds} == {'XPD-CFD', 'COST-CFD', 'MSTR-CFD', 'SMR-CFD', 'MPC-CFD', 'AMD-CFD', 'BDX-CFD'}
    assert book['totaux']['courtiers']['revolut']['cfd_usd'] == 16856.51
    assert book['totaux']['courtiers']['revolut']['cfd_exposition_usd'] == 16856.51
    assert book['totaux']['total_usd'] == 47769.61
    assert any(p.get('ticker')=='TSLA-RSU' for p in book['positions'])


def test_build_py_publie_la_racine():
    src = (ROOT / 'src' / 'build.py').read_text(encoding='utf-8')
    assert '_publish_positions_root' in src
    assert 'positions_revolutx.json' in src
