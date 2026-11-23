"""Les poids affichés dans RÈGLES doivent coller au code, pas à un texte figé."""
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope='module')
def regles():
    return json.loads((ROOT / 'config' / 'regles.json').read_text(encoding='utf-8'))


def test_fiche_regles_presentes(regles):
    fr = regles['fiche_regles']
    assert fr['titre_bouton']
    ids = [c['id'] for c in fr['classes']]
    assert fr['ordre_site'] == ids
    assert 'actions' in ids and 'obligations' in ids and 'crypto' in ids
    assert 'immobilier' in ids and 'placements' in ids


def test_poids_techniques_identiques_au_json(regles):
    na = regles['note_apex']['technique']
    # poids dans la note finale
    assert na['elliott'] == pytest.approx(0.10)
    assert na['structure'] == pytest.approx(0.10)
    assert na['fibonacci'] == pytest.approx(0.08)
    assert na['figure'] == pytest.approx(0.07)
    assert na['rsi'] == pytest.approx(0.05)
    assert na['macd'] == pytest.approx(0.05)
    assert na['cci'] == pytest.approx(0.05)
    assert sum(na[k] for k in na) == pytest.approx(regles['note_apex']['poids_technique'])
    tech = next(c for c in regles['fiche_regles']['classes'] if c['id'] == 'actions')['technique']
    fixes = {x['id']: x['poids'] for x in tech['fixes']}
    # dans la fiche, les poids sont ceux du bloc technique (somme 1)
    assert fixes['elliott'] == pytest.approx(0.20)
    assert fixes['structure'] == pytest.approx(0.20)
    assert fixes['fibonacci'] == pytest.approx(0.16)
    assert fixes['figure'] == pytest.approx(0.14)
    assert fixes['rsi'] == pytest.approx(0.10)
    assert fixes['macd'] == pytest.approx(0.10)
    assert fixes['cci'] == pytest.approx(0.10)
    assert sum(fixes.values()) == pytest.approx(1.0)
    # et × 50 % = poids dans la note
    w = next(p['poids'] for p in next(c for c in regles['fiche_regles']['classes'] if c['id']=='actions')['note']['parts'] if p['id']=='technique')
    assert w == pytest.approx(0.5)
    assert fixes['elliott'] * w == pytest.approx(na['elliott'])


def test_poids_note_actions_et_crypto(regles):
    na = regles['note_apex']
    for cid, fond_id in (('actions', 'fondamental'), ('crypto', 'liquidite')):
        parts = next(c for c in regles['fiche_regles']['classes'] if c['id'] == cid)['note']['parts']
        by = {p['id']: p['poids'] for p in parts}
        assert by[fond_id] == pytest.approx(na['poids_fondamental'])
        assert by['technique'] == pytest.approx(na['poids_technique'])
        assert sum(p['poids'] for p in parts) == pytest.approx(1.0)


def test_pas_de_fondamental_obligations_etf(regles):
    by = {c['id']: c for c in regles['fiche_regles']['classes']}
    assert by['obligations']['fondamental'] is None
    assert by['etf_actions']['fondamental'] is None
    assert by['etf_actions']['note']['parts'][0]['poids'] == pytest.approx(1.0)
    assert by['obligations']['note']['parts'][0]['poids'] == pytest.approx(1.0)
    for cid in ('obligations', 'etf_actions', 'indices_macro'):
        fixes = {x['id']: x['poids'] for x in by[cid]['technique']['fixes']}
        assert sum(fixes.values()) == pytest.approx(1.0)
        assert by[cid]['technique'].get('renormalise') is True


def test_liquidite_crypto_70_30(regles):
    import sys
    sys.path.insert(0, str(ROOT / 'src'))
    import liquidite_crypto as L
    fond = next(c for c in regles['fiche_regles']['classes'] if c['id'] == 'crypto')['fondamental']
    comps = {x['id']: x['poids'] for x in fond['composantes']}
    assert comps['carte_1an'] == pytest.approx(L.W_1Y)
    assert comps['carte_1mois'] == pytest.approx(L.W_1M)
    assert sum(comps.values()) == pytest.approx(1.0)


def test_immobilier_et_liquidites_somment_a_1(regles):
    by = {c['id']: c for c in regles['fiche_regles']['classes']}
    for cid, expected in {
        'immobilier': {'prix': 0.25, 'taux_niveau': 0.20, 'taux_tendance': 0.20, 'trends': 0.15, 'sentiment': 0.20},
        'liquidites': {'rendement_reel': 0.30, 'estr': 0.20, 'tendance_bce': 0.20, 'appetit_risque': 0.30},
    }.items():
        got = {x['id']: x['poids_dans_panier'] for x in by[cid]['timing']['panier']['composantes']}
        assert got == expected
        assert sum(got.values()) == pytest.approx(1.0)


def test_placements_sans_note(regles):
    c = next(x for x in regles['fiche_regles']['classes'] if x['id'] == 'placements')
    assert c['note'] is None
    assert c['timing'] is None


def test_fibonacci_parts_issues_des_regles(regles):
    fib = next(x for x in next(c for c in regles['fiche_regles']['classes'] if c['id'] == 'actions')['timing']['fixes'] if x['id'] == 'fibonacci')
    parts = {p['id']: p['poids'] for p in fib['parts']}
    assert parts['historique'] == pytest.approx(regles['fibonacci']['part_historique'])
    assert parts['dernier_mouvement'] == pytest.approx(regles['fibonacci']['part_dernier_mouvement'])
    assert sum(parts.values()) == pytest.approx(1.0)
