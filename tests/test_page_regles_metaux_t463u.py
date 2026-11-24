"""t463u : tableau Métaux précieux au format compact du tableau Actions."""
from __future__ import annotations
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
JS = (ROOT / "src" / "regles.js").read_text(encoding="utf-8")
REGLES = json.loads((ROOT / "config" / "regles.json").read_text(encoding="utf-8"))
FIBO = (ROOT / "src" / "fibo.py").read_text(encoding="utf-8")
TECH = (ROOT / "src" / "technique_apex.py").read_text(encoding="utf-8")
CORE = (ROOT / "src" / "ind_core.py").read_text(encoding="utf-8")


def _grid():
    chunk = JS.split("function rgMetauxGrid")[1]
    for stop in ("function rgCryptoChamp", "function rgPageHTML"):
        if stop in chunk:
            return chunk.split(stop)[0]
    return chunk


def test_format_compact_comme_actions():
    grid = _grid()
    # plus de CSS qui passe la règle à la ligne
    assert "grid-column:1/-1" not in grid
    assert "white-space:normal" not in grid
    # pas d'explications longues demandées au retrait (hors commentaires)
    visible = "\n".join(l for l in grid.splitlines() if not l.strip().startswith("/*") and "/*" not in l)
    for frag in ("contrat à terme", "Yahoo", "DBC", "clipp", "Elliott", "effet_echelle"):
        assert frag not in visible, frag
    assert "rgMetauxChamp" in grid or "intro_courte" in JS
    assert "Meilleures entrées" in grid
    assert "Portail cyan" in grid
    # une ligne d'intro, pas trois paragraphes d'effet d'échelle
    assert "effet_echelle_av" not in grid


def test_intro_courte():
    intro = REGLES["apex_metaux"]["intro_courte"]
    assert intro.count(".") <= 2
    assert "Or" in intro and "argent" in intro
    assert "−50 à 250" in intro
    assert "Yahoo" not in intro and "DBC" not in intro and "Elliott" not in intro


def test_seuils_courts_identiques_au_code():
    s = REGLES["apex_metaux"]["regles_courtes"]
    assert "RSI < 40" in s["rsi"] and "+10" in s["rsi"] and "+20" in s["rsi"]
    assert "MACD < 0" in s["macd"] and "4 barres" in s["macd"]
    assert "sous 0 + 4 barres rouges d'affilée" in s["macd"].lower() or "Sous 0 + 4 barres rouges d'affilée" in s["macd"]
    assert "25/11" in s["macd"]

    assert "38,2 %" in s["fibonacci"] and "61,8 %" in s["fibonacci"] and "78,6 %" in s["fibonacci"]
    assert "sous 20" in s["cci"]
    assert "9 critères" in s["fond"] or "9" in s["fond"]
    assert "sans redistribution" in s["structure"] or "retirée" in s["structure"].lower() or "Retirée" in s["structure"]
    assert 'data-group="structure"' not in _grid()
    assert "mx.gi_seuil" in JS and "mx.cyan_note_min" in JS and "av_achat_fort" in JS
