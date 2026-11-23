"""Cas connus APEX (t342u) : base 50, amplitude ×1,5, pas de plafond Elliott sur la note."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'src'))

import pytest
from apex.score import compute, montant_template, bande_couleur, flag_tv, fmt10


def _parts(**kw):
    base = dict(elliott=0, structure=0, fibonacci=0, rsi=0, macd=0, cci=0)
    base.update(kw)
    return base


def test_formule_base50_amplitude_1_5():
    # Tout neutre, fond 50 → reste sur 50
    r0 = compute(0, 50, parts=_parts())
    assert r0['note'] == 50
    assert r0['flag'] == 'orange'
    assert r0['decomp']['texte'].startswith('Base 50')
    by0 = {x['id']: x for x in r0['decomp']['lignes']}
    assert by0['fond']['pts'] == pytest.approx(0)
    assert by0['elliott']['pts'] == pytest.approx(0)
    # Fond 100 + technique neutre = 50 + 37,5 = 87,5 → 88, AV neutre → portail cyan 75
    r = compute(0, 100, parts=_parts())
    assert r['brut'] == pytest.approx(87.5)
    assert r['note'] == 75
    assert r['flag'] == 'green'
    assert 'cyan' in r['cap']
    assert r['decomp']['renormalise'] is False
    by = {x['id']: x for x in r['decomp']['lignes']}
    assert by['fond']['poids'] == 50 and by['fond']['pts'] == pytest.approx(37.5)
    assert 'figure' not in by
    assert by['elliott']['pts'] == pytest.approx(0)
    assert by['elliott']['poids'] == int(round(0.1162790698 * 100))
    assert by['fibonacci']['poids'] == int(round(0.0930232558 * 100))
    assert 'Fond. +37,5' in r['decomp']['texte'] or 'Fond. +37.5' in r['decomp']['texte']
    assert 'Elliott 0' in r['decomp']['texte']


def test_renormalise_sans_fondamental():
    r = compute(0, None, parts=_parts())
    assert r['renormalise'] is True
    by = {x['id']: x for x in r['decomp']['lignes']}
    assert 'fond' not in by
    assert 'figure' not in by
    assert by['elliott']['poids'] == int(round(0.1162790698 * 2 * 100))
    assert by['fibonacci']['poids'] == int(round(0.0930232558 * 2 * 100))
    assert by['rsi']['poids'] == int(round(0.0581395349 * 2 * 100))
    assert r['note'] == 50  # tout neutre, 100 % technique
    assert 'sans fond.' in r['decomp']['texte']


def test_crypto_libelle_liquidite():
    r = compute(0, 80, parts=_parts(), classe='crypto')
    assert r['decomp']['libelle_fond'] == 'Liq.'
    assert 'Liq.' in r['decomp']['texte']
    assert r['decomp']['texte'].startswith('Base 50')


def test_pas_de_plafond_elliott_sur_la_note():
    # Fond 100 + technique neutre = 87,5 → 88 ; vague A manuelle : PLUS de plafond 40,
    # mais AV faible → portail cyan 75.
    ell = {'key': 'a', 'manuel': True, 'override': True, 'zone': 'rouge'}
    r = compute(-12.4, 100, ell, parts=_parts())
    assert r['note'] == 75
    assert r['flag'] == 'green'
    assert 'elliott' not in r['cap']
    assert 'cyan' in r['cap']
    # Vague 4 manuelle : pas de plafond, bonus +5 (87,5+5=92,5 → 93), AV faible → 75
    ell2 = {'key': 'fin_4', 'manuel': True, 'override': True, 'zone': 'verte'}
    r2 = compute(17.8, 100, ell2, parts=_parts())
    assert r2['note'] == 75
    assert 'bonus' in r2['cap']
    assert 'cyan' in r2['cap']
    # Comptage automatique en zone verte : pas de bonus, toujours portail cyan
    r3 = compute(17.8, 100, 'fin_4', parts=_parts())
    assert 'bonus' not in r3['cap']
    assert r3['note'] == 75
    # Sans portail (AV fort + confirmation) et vague rouge : la note peut dépasser 40
    hi = _parts(elliott=-60, structure=100, fibonacci=100, rsi=100, macd=100, cci=100)
    r4 = compute(65, 80, ell, divergence=100, parts=hi)
    assert r4['note'] > 40
    assert 'elliott' not in r4['cap']


def test_regle_cyan_achat_fort_et_divergence():
    # Technique au maximum, pas de fond → 100 brut, autorisé si AV ≥ +60 et divergence
    hi = _parts(elliott=100, structure=100, fibonacci=100, rsi=100, macd=100, cci=100)
    r = compute(65, None, None, divergence=100, parts=hi)
    assert r['note'] == 100 and r['flag'] == 'cyan'
    # Achat fort sans confirmation → 75
    r2 = compute(65, None, None, parts=hi)
    assert r2['note'] == 75 and 'cyan' in r2['cap']
    # AV seulement « Achat », même avec divergence → 75
    r3 = compute(45.2, None, None, divergence=100, parts=hi)
    assert r3['note'] == 75
    # Achat fort + zone verte manuelle → cyan autorisé
    r4 = compute(65, None, {'key': 'fin_4', 'manuel': True, 'zone': 'verte'}, parts=hi)
    assert r4['note'] == 100 and r4['flag'] == 'cyan'


def test_points_techniques_signes():
    from apex.score import pts_from_score
    # Poids 0,10, amplitude 1,5 : amp = 0,10×50×1,5 = 7,5
    assert pts_from_score(100, 0.10) == pytest.approx(7.5)
    assert pts_from_score(-100, 0.10) == pytest.approx(-7.5)
    assert pts_from_score(0, 0.10) == pytest.approx(0)
    assert pts_from_score(None, 0.07) == pytest.approx(0)
    # CCI neutre (0) = 0 point (plus la moitié des 5)
    assert pts_from_score(0, 0.05) == pytest.approx(0)
    # CCI +80, poids 0,05 : amp = 3,75 → +3
    assert pts_from_score(80, 0.05) == pytest.approx(3.0)
    assert pts_from_score(100, 0.05) == pytest.approx(3.75)
    assert pts_from_score(-80, 0.05) == pytest.approx(-3.0)


def test_rsi_macd_cci_apex():
    from technique_apex import score_rsi_apex, score_macd_apex, score_cci_apex
    assert score_rsi_apex(30) == 100
    assert score_rsi_apex(50) == 0
    assert score_rsi_apex(70) == -100
    assert score_rsi_apex(40) == 50
    # MACD sous zéro et sous signal, histogramme qui remonte : 70+30 = 100
    assert score_macd_apex(-1, 0, -0.1, -0.2) == 100
    # MACD sous zéro et sous signal, histo qui descend : 70
    assert score_macd_apex(-1, 0, -0.3, -0.2) == 70
    # MACD au-dessus de zéro et de la signal, sans extension : -70
    assert score_macd_apex(1, 0.5, 0.2, 0.1) == -70
    # CCI t338u : zones, pas de continu
    assert score_cci_apex(-200) == 100
    assert score_cci_apex(-100) == 80
    assert score_cci_apex(-150) == 80
    assert score_cci_apex(0) == 0
    assert score_cci_apex(-50) == 0
    assert score_cci_apex(50) == 0
    assert score_cci_apex(99.9) == 0
    assert score_cci_apex(100) == -80
    assert score_cci_apex(150) == -80
    assert score_cci_apex(200) == -100
    assert score_cci_apex(None) == 0


@pytest.mark.parametrize('note,site,tv', [
    (0, 'violet', 'purple'),
    (19, 'violet', 'purple'),
    (20, 'rouge', 'red'),
    (39, 'rouge', 'red'),
    (40, 'jaune', 'orange'),
    (50, 'jaune', 'orange'),
    (59, 'jaune', 'orange'),
    (60, 'vert', 'green'),
    (75, 'vert', 'green'),
    (79, 'vert', 'green'),
    (80, 'cyan', 'cyan'),
    (100, 'cyan', 'cyan'),
])
def test_couleurs_aux_bornes(note, site, tv):
    assert bande_couleur(note) == site
    assert flag_tv(note) == tv


@pytest.mark.parametrize('note,montant', [
    (70, None),
    (75, 500),
    (80, 600),
    (85, 700),
    (90, 800),
    (95, 900),
    (100, 1000),
])
def test_bareme_template_trade(note, montant):
    assert montant_template(note) == montant


def test_fmt10():
    assert fmt10(75) == '75'
    assert fmt10(100) == '100'
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
