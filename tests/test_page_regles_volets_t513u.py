"""t513u : volets exclusifs LONG / SHORT sur la page Règles, SHORT limité à 3 catégories."""
from __future__ import annotations
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
JS = (ROOT / "src" / "regles.js").read_text(encoding="utf-8")
CSS = (ROOT / "src" / "template.html").read_text(encoding="utf-8")
SHORT_FN = JS.split("function rgShortGrid")[1].split("function rgSensActuel")[0]


def test_short_trois_categories_seulement():
    assert "short-actions" in SHORT_FN
    assert "short-banques" in SHORT_FN
    assert "short-energie" in SHORT_FN
    assert "Actions (hors banque)" in SHORT_FN
    assert "Actions bancaires" in SHORT_FN
    assert "Énergie" in SHORT_FN
    for forbidden in ("short-metaux", "short-crypto", "short-obligations", "short-liquidites", "short-placements", "short-immobilier"):
        assert forbidden not in SHORT_FN
    assert "rgShortCommons()" in SHORT_FN
    assert "sansCouleursEntrees:true" in SHORT_FN
    assert "rg-table-short-actions" in SHORT_FN
    assert "rg-table-short-banques" in SHORT_FN
    assert "rg-table-short-energie" in JS


def test_comptabilisation_short_sans_invention():
    assert "Pas de note miroir, pas de nouveau calcul." in JS
    assert "10 ≤ note < 70" in JS
    assert "100 $ à 69" in JS
    assert "+20 $ tous les 24 points" in JS
    assert "200 $ à −50" in JS
    assert "mise × 5" in JS
    assert "de la plus basse à la plus haute" in JS
    # pas de remise de l’encadré retiré de Meilleurs SHORT
    assert "Le short peut faire perdre plus que la mise" not in JS
    assert "Montants : mise (levier ×5)" not in JS
    assert "avertissement" not in JS.lower()


def test_long_reste_complet():
    html = JS.split("function rgPageHTML")[1].split("function rgRender")[0]
    long = html.split('id="rg-pane-long"')[1].split('id="rg-pane-short"')[0]
    assert "sections.map(rgSectionAccordion)" in long
    assert "${rgCommons()}" in long
    assert "rgShortGrid" not in long


def test_css_plus_de_deux_colonnes():
    assert "grid-template-columns:minmax(0,1fr) 300px" not in CSS
    assert ".rg-tab[aria-selected=\"true\"],.rg-tab.is-on" in CSS
    assert "font-size:32px" in CSS
