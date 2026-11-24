"""t465u : Meilleures entrées affichent le ticker TV sans préfixe d'échange."""
from __future__ import annotations
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
JS = (ROOT / "src" / "good_invest.js").read_text(encoding="utf-8")


def test_ticker_court_sans_prefixe():
    assert "function giTickerCourt" in JS
    assert "lastIndexOf(':')" in JS
    assert "giTickerCourt(it.tv)" in JS
    render = JS.split("function giRender")[1]
    assert "${(it.nom||it.tv).replace(/</g,'')}</button>" not in render
    assert "giTickerCourt(it.tv)" in render


def test_infobulle_nom_et_copie_symbole_complet():
    render = JS.split("function giRender")[1]
    assert "it.nom||it.tv" in render
    assert "title=" in render
    assert "${go}" in render and "${cp}" in render and "✓</button>${cp}" in render
    assert "ophirCopyBtn(it.tv)" in render or "data-c=" in render
    assert "String(it.tv)" in render
