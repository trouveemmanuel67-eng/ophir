"""t464u : page RÈGLES en colonnes LONG (règles actuelles) et SHORT (vide)."""
from __future__ import annotations
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
JS = (ROOT / "src" / "regles.js").read_text(encoding="utf-8")
CSS = (ROOT / "src" / "template.html").read_text(encoding="utf-8")


def test_panneaux_long_short():
    html = JS.split("function rgPageHTML")[1].split("function rgRender")[0]
    assert 'id="rg-pane-long"' in html
    assert 'id="rg-pane-short"' in html
    assert ">LONG<" in html
    assert ">SHORT<" in html
    assert "sections.map(rgSectionAccordion)" in html
    assert "${rgCommons()}" in html
    assert html.find("rg-pane-long") < html.find("${rgCommons()}") < html.find('id="rg-pane-short"')
    short = html.split('id="rg-pane-short"')[1]
    assert "Règles SHORT à définir" not in short
    assert "rgShortGrid()" in short
    assert "rgSectionAccordion" not in short
    assert "rgCommons" not in short
    assert "function rgShortGrid" in JS
    assert "200 − note LONG" not in JS and "200 - note LONG" not in JS
    assert "≤ " in JS or "70" in JS


def test_colonnes_desktop_empilees_mobile():
    assert "grid-template-columns:minmax(0,1fr) 300px" in CSS
    assert ".rg-page-main{grid-template-columns:1fr" in CSS
    assert "@media(max-width:900px)" in CSS


def test_plus_de_chevauchement_regles_communes():
    assert ".rg-board .rg-card{display:grid" in CSS
    assert ".rg-commons-grid .rg-card{display:block;white-space:normal" in CSS
    assert "\n.rg-card{display:grid;grid-template-columns:3.4em" not in CSS
