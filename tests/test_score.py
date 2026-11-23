"""Cas connus APEX (t317u / t320u)."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'src'))

import pytest
from apex.score import compute, montant_template, bande_couleur, flag_tv, fmt10


def test_prar_sans_cyan():
    # AV +45,2 Achat, pas de fond, fin_2_conf auto → pas de bonus, plafond cyan 7,5
    r = compute(45.2, None, 'fin_2_conf')
    assert r['note'] == 7.5
    assert r['flag'] == 'green'
    assert 'cyan' in r['cap']
    assert 'bonus' not in r['cap']


def test_pltr_override_a():
    ell = {'key': 'a', 'manuel': True, 'override': True, 'zone': 'rouge'}
    r = compute(-12.4, 85.8, ell)
    assert r['note'] == 4.0
    assert r['flag'] == 'orange'  # t328u : note 4,0 = jaune
    assert 'elliott' in r['cap']


def test_mfg_override_a():
    ell = {'key': 'a', 'manuel': True, 'override': True, 'zone': 'rouge'}
    r = compute(16.5, 61.5, ell)
    assert r['note'] == 4.0
    assert r['flag'] == 'orange'  # t328u : note 4,0 = jaune
    assert 'elliott' in r['cap']


def test_vk_fin_4_manuel():
    ell = {'key': 'fin_4', 'manuel': True, 'override': True, 'zone': 'verte'}
    r = compute(17.8, 75.4, ell)
    assert r['note'] == 7.5
    assert r['flag'] == 'green'
    assert 'bonus' in r['cap']
    assert 'cyan' not in r['cap']


def test_regle_cyan_achat_fort_et_divergence():
    assert compute(65, None, None, divergence=100)['note'] == 10.0
    assert compute(65, None, None, divergence=100)['flag'] == 'cyan'
    # Achat fort sans confirmation → 7,5
    r = compute(65, None, None)
    assert r['note'] == 7.5 and 'cyan' in r['cap']
    # AV Achat seulement, même avec divergence → 7,5
    r2 = compute(45.2, None, None, divergence=100)
    assert r2['note'] == 7.5
    # Achat fort + zone verte manuelle → cyan autorisé
    r3 = compute(65, None, {'key': 'fin_4', 'manuel': True, 'zone': 'verte'})
    assert r3['note'] == 10.0 and r3['flag'] == 'cyan'


@pytest.mark.parametrize('note,site,tv', [
    (0, 'violet', 'purple'),
    (1.5, 'violet', 'purple'),
    (2, 'rouge', 'red'),
    (3.5, 'rouge', 'red'),
    (4, 'jaune', 'orange'),
    (5, 'jaune', 'orange'),
    (5.5, 'jaune', 'orange'),
    (6, 'vert', 'green'),
    (6.5, 'vert', 'green'),
    (7.5, 'vert', 'green'),
    (8, 'cyan', 'cyan'),
    (10, 'cyan', 'cyan'),
])
def test_couleurs_aux_bornes(note, site, tv):
    assert bande_couleur(note) == site
    assert flag_tv(note) == tv


@pytest.mark.parametrize('note,montant', [
    (7.0, None),
    (7.5, 500),
    (8.0, 600),
    (8.5, 700),
    (9.0, 800),
    (9.5, 900),
    (10.0, 1000),
])
def test_bareme_template_trade(note, montant):
    assert montant_template(note) == montant


def test_fmt10():
    assert fmt10(7.5) == '7,5'
    assert fmt10(10.0) == '10'
    assert fmt10(None) == '–'

def test_scripts_sans_chemin_boite():
    """Les scripts du pipeline quotidien ne doivent plus pointer vers le chemin de la boîte."""
    from pathlib import Path
    hard = '/workspace/invest/patrimoine-dashboard'
    src = Path(__file__).resolve().parents[1] / 'src'
    pipeline = [
        'build.py', 'build_apex10.py', 'build_apex_bars.py', 'build_achatvente.py',
        'build_indicateur.py', 'build_data_tabs.py', 'build_secteurs.py', 'build_pays.py',
        'build_energie.py', 'build_metaux.py', 'build_obligations.py', 'build_crypto_fiches.py',
        'build_fx_apex.py', 'build_obpays.py', 'liquidite_crypto.py',
    ]
    hits = []
    for name in pipeline:
        text = (src / name).read_text(encoding='utf-8')
        if hard in text:
            hits.append(name)
    assert hits == [], hits


def test_actifs_a_suivre_exclut_hors():
    from apex.config import actifs, actifs_a_suivre
    tous = actifs()
    suivis = actifs_a_suivre()
    hors = [a for a in tous if a.get('univers') == 'hors']
    pos = [a for a in suivis if a.get('univers') == 'positions_seulement']
    assert len(hors) == 157
    assert all(a.get('univers') != 'hors' for a in suivis)
    tvs = {a['tv'] for a in pos}
    assert 'TSE:6954' in tvs and 'NYSE:PKX' in tvs
    assert len(suivis) == 449  # 447 visibles + 2 positions seulement

