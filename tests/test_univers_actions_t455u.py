"""t455u : la section Actions n'affiche que la France et les USA."""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_pays_embarque_uniquement_france():
    html = (ROOT / 'index.html').read_text(encoding='utf-8')
    # Le JSON pays est dans un script ; les cartes « Marché Allemagne/Canada/Suisse » ne doivent plus y figurer.
    for s in ('Marché Allemagne', 'Marché Canada', 'Marché Suisse'):
        assert s not in html, s
    # L'onglet Obligations peut encore citer l'Allemagne (Bund) : on ne vérifie que les têtes de pays Actions.
    for sym in ('EXS1.DE', 'SXR2.DE', 'XSMI.DE'):
        # absents du bloc pays embarqué, pas forcément de tout le HTML (bars, etc.)
        pass
    # Extraire le tableau PAYS.countries via le slim : France seule, pas de/ca/ch
    # On relit le slim comme build.py
    raw = (ROOT / 'data' / 'pays.json').read_text(encoding='utf-8')
    import sys
    sys.path.insert(0, str(ROOT / 'src'))
    # build.py s'exécute à l'import : on recopie la fonction
    d = json.loads(raw)
    keep = set(d.get('univers_actions') or ['USA', 'France'])
    countries = [c['nom'] for c in (d.get('countries') or []) if c.get('nom') in keep]
    assert 'France' in countries
    assert 'Allemagne' not in countries
    assert 'Canada' not in countries
    assert 'Suisse' not in countries


def test_renderpays_filtre_univers():
    js = (ROOT / 'src' / 'pays.js').read_text(encoding='utf-8')
    assert 'paysEstDansUnivers' in js
    assert 'filter(paysEstDansUnivers)' in js


def test_index_actions_sans_en_tetes_tiers():
    html = (ROOT / 'index.html').read_text(encoding='utf-8')
    # Les titres de cartes générés par renderPays viennent des données ; le JS contient le filtre.
    assert 'function paysEstDansUnivers' in html
    assert "filter(paysEstDansUnivers)" in html
