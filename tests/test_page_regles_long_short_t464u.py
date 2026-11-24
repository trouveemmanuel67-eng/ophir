"""t464u / t513u : page RÈGLES en volets exclusifs LONG et SHORT."""
from __future__ import annotations
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
JS = (ROOT / "src" / "regles.js").read_text(encoding="utf-8")
CSS = (ROOT / "src" / "template.html").read_text(encoding="utf-8")


def test_panneaux_long_short():
    html = JS.split("function rgPageHTML")[1].split("function rgRender")[0]
    assert 'id="rg-pane-long"' in html
    assert 'id="rg-pane-short"' in html
    assert 'id="rg-tab-long"' in html
    assert 'id="rg-tab-short"' in html
    assert ">LONG<" in html
    assert ">SHORT<" in html
    assert "sections.map(rgSectionAccordion)" in html
    assert "${rgCommons()}" in html
    assert "${rgShortGrid()}" in html
    assert html.find("rg-tab-long") < html.find('id="rg-pane-long"') < html.find("${rgCommons()}") < html.find('id="rg-pane-short"')
    short = html.split('id="rg-pane-short"')[1]
    assert "Règles SHORT à définir" not in short
    assert "rgShortGrid()" in short
    assert "hidden" in short
    long = html.split('id="rg-pane-long"')[1].split('id="rg-pane-short"')[0]
    assert "hidden" not in long
    assert "function rgShortGrid" in JS
    assert "function rgSetSens" in JS
    assert "function rgShortCommons" in JS
    assert "200 − note LONG" not in JS and "200 - note LONG" not in JS
    assert "≤ " in JS or "70" in JS


def test_onglets_exclusifs_centres():
    assert "role=\"tablist\"" in JS
    assert "data-rg-sens" in JS
    assert "rgSetSens('long')" in JS
    assert ".rg-tabs{display:flex;justify-content:center" in CSS
    assert ".rg-tab{" in CSS
    assert "font-size:14.5px;font-weight:650" in CSS
    assert "font-size:32px;font-weight:800" not in CSS
    assert 'text-align:center' in CSS
    assert '.rg-pane[hidden]{display:none !important}' in CSS
    assert "grid-template-columns:minmax(0,1fr) 300px" not in CSS


def test_plus_de_chevauchement_regles_communes():
    assert ".rg-board .rg-card{display:grid" in CSS
    assert ".rg-commons-grid .rg-card{display:block;white-space:normal" in CSS
    assert "\n.rg-card{display:grid;grid-template-columns:3.4em" not in CSS
