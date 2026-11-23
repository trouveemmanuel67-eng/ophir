"""Cas connus APEX (t317u / t320u)."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'src'))

import pytest
from apex.score import compute, montant_template, bande_couleur, flag_tv, fmt10



def _parts(**kw):
    base = dict(elliott=0, structure=0, fibonacci=0, figure=0, rsi=0, macd=0, cci=0)
    base.update(kw)
    return base


def test_formule_50_50_decomp():
    # Tous les scores techniques à 0 (neutre) + fond 100 → 50 + 25 = 75 → 7,5
    r = compute(0, 100, parts=_parts())
    assert r['note'] == 7.5
    assert r['flag'] == 'green'
    assert r['decomp']['renormalise'] is False
    by = {x['id']: x for x in r['decomp']['lignes']}
    assert by['fond']['poids'] == 50 and by['fond']['pts'] == 50
    assert by['elliott']['poids'] == 10 and by['elliott']['pts'] == 5
    assert by['fibonacci']['poids'] == 8 and by['fibonacci']['pts'] == 4
    assert by['figure']['poids'] == 7
    assert by['rsi']['poids'] == 5
    assert 'Fond.' in r['decomp']['texte']
    assert 'Elliott' in r['decomp']['texte']


def test_renormalise_sans_fondamental():
    r = compute(0, None, parts=_parts())
    assert r['renormalise'] is True
    by = {x['id']: x for x in r['decomp']['lignes']}
    assert 'fond' not in by
    assert by['elliott']['poids'] == 20
    assert by['fibonacci']['poids'] == 16
    assert by['figure']['poids'] == 14
    assert by['rsi']['poids'] == 10
    assert r['note'] == 5.0  # tout neutre, 100 % technique
    assert 'sans fond.' in r['decomp']['texte']


def test_crypto_libelle_liquidite():
    r = compute(0, 80, parts=_parts(), classe='crypto')
    assert r['decomp']['libelle_fond'] == 'Liq.'
    assert r['decomp']['texte'].startswith('Liq.')


def test_plafonds_elliott_et_bonus_manuel():
    # Fond 100 + technique neutre = 7,5 ; vague A manuelle → plafond 4
    ell = {'key': 'a', 'manuel': True, 'override': True, 'zone': 'rouge'}
    r = compute(-12.4, 100, ell, parts=_parts())
    assert r['note'] == 4.0
    assert r['flag'] == 'orange'
    assert 'elliott' in r['cap']
    # Même situation, vague 4 manuelle : pas de plafond, bonus +0,5 → 8 puis cyan (AV faible) → 7,5
    ell2 = {'key': 'fin_4', 'manuel': True, 'override': True, 'zone': 'verte'}
    r2 = compute(17.8, 100, ell2, parts=_parts())
    assert r2['note'] == 7.5
    assert 'bonus' in r2['cap']
    assert 'cyan' in r2['cap']
    # Comptage automatique en zone verte : pas de bonus
    r3 = compute(17.8, 100, 'fin_4', parts=_parts())
    assert 'bonus' not in r3['cap']
    assert r3['note'] == 7.5


def test_regle_cyan_achat_fort_et_divergence():
    # Technique au maximum, pas de fond → 10 brut, autorisé si AV ≥ +60 et divergence
    hi = _parts(elliott=100, structure=100, fibonacci=100, figure=100, rsi=100, macd=100, cci=100)
    r = compute(65, None, None, divergence=100, parts=hi)
    assert r['note'] == 10.0 and r['flag'] == 'cyan'
    # Achat fort sans confirmation → 7,5
    r2 = compute(65, None, None, parts=hi)
    assert r2['note'] == 7.5 and 'cyan' in r2['cap']
    # AV seulement « Achat », même avec divergence → 7,5
    r3 = compute(45.2, None, None, divergence=100, parts=hi)
    assert r3['note'] == 7.5
    # Achat fort + zone verte manuelle → cyan autorisé
    r4 = compute(65, None, {'key': 'fin_4', 'manuel': True, 'zone': 'verte'}, parts=hi)
    assert r4['note'] == 10.0 and r4['flag'] == 'cyan'


def test_points_techniques_lineaires():
    from apex.score import pts_from_score
    assert pts_from_score(100, 0.10) == 10
    assert pts_from_score(-100, 0.10) == 0
    assert pts_from_score(0, 0.10) == 5
    assert pts_from_score(None, 0.07) == pytest.approx(3.5)


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

