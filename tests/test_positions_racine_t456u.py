"""t456u / t510u : les JSON à la racine suivent le relevé Revolut du 24/11 à 20 h 31."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FILES = ('positions.json', 'positions_revolut.json', 'positions_revolutx.json')
STALE = {'NKE', 'STLA', 'PKX', 'BTC', 'AGNC', 'NLY', 'PDSE', 'MBG', 'PAH3'}
NEED = {'XAU', 'XAG', 'XPT', 'XPD', 'BKNG', 'CAT', 'AVGO', 'MU', 'HWM', 'GOOGL', 'ENPH', 'LRCX'}


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


def test_releve_24_11_dans_le_json_fethe():
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
    # pas de CFD mélangés
    kinds = {p.get('type') or p.get('kind') for p in book['positions']}
    assert 'cfd' not in {str(k).lower() for k in kinds if k}


def test_build_py_publie_la_racine():
    src = (ROOT / 'src' / 'build.py').read_text(encoding='utf-8')
    assert '_publish_positions_root' in src
    assert 'positions_revolutx.json' in src
