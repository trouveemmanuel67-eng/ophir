"""t484u–t486u : section HYPE 90 dans RÈGLES (métaux purs + crypto), pas encore dans le calcul."""
from __future__ import annotations
import inspect
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
import sys
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from apex.config import regles  # noqa: E402
from apex import metaux_points as MP  # noqa: E402


def test_hype_dans_regles_metaux_pas_dans_le_calcul():
    mx = regles()["apex_metaux"]
    assert mx["points"]["hype"] == 90
    assert "25/11" in mx["regles_courtes"]["hype"]
    assert "comptant" in mx["regles_courtes"]["hype"].lower() or "Comptant" in mx["regles_courtes"]["hype"]
    assert "ETC" in mx["regles_courtes"]["hype"]
    js = (ROOT / "src" / "regles.js").read_text(encoding="utf-8")
    grid = js.split("function rgMetauxGrid")[1].split("function rgCryptoChamp")[0]
    assert 'data-group="hype"' in grid
    assert "HYPE" in grid
    assert "hors ETC/ETF" in grid or "hors ETC" in mx["regles_courtes"]["hype"]
    src = inspect.getsource(MP.score_instrument)
    assert "hype_points" not in src
    assert "pts.hype" in grid or "HYPE" in grid


def test_section_crypto_regles_plus_hype():
    cx = regles()["apex_crypto"]
    assert cx["points"]["liquidite"] == 45 and cx["points"]["technique"] == 110
    assert cx["points"]["hype"] == 45
    assert cx["note_min"] == -50 and cx["note_max"] == 250
    assert "25/11" in cx["regles_courtes"]["hype"]
    assert "+45" in cx["regles_courtes"]["hype"] or "0–9 → +45" in cx["champ_application"]
    js = (ROOT / "src" / "regles.js").read_text(encoding="utf-8")
    assert "function rgCryptoGrid" in js
    assert "rg-table-crypto" in js
    page = js.split("function rgPageHTML")[1].split("function rgRender")[0]
    assert "rgCryptoGrid()" in page
    assert "id:'crypto'" in page or 'id:"crypto"' in page
