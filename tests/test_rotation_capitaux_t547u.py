"""t547u : rotation de capitaux la plus probable sous INDICE ROTATION."""
from __future__ import annotations
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
JS = (ROOT / "src" / "rotation.js").read_text(encoding="utf-8")
TPL = (ROOT / "src" / "template.html").read_text(encoding="utf-8")
BUILD = (ROOT / "src" / "build.py").read_text(encoding="utf-8")
REBUILD = (ROOT / "src" / "rebuild_apres_cloture.sh").read_text(encoding="utf-8")
DATA = json.loads((ROOT / "data" / "rotation_capitaux.json").read_text(encoding="utf-8"))


def test_injection_et_affichage():
    assert "dataRotationCapitaux" in TPL
    assert "__DATA_ROTATION_CAPITAUX__" in TPL
    assert "__DATA_ROTATION_CAPITAUX__" in BUILD
    assert "rotation_capitaux.json" in BUILD
    assert "build_rotation_capitaux.py" in REBUILD
    assert "build_rotation.py" in REBUILD
    # l'indice Gave n'est pas remplacé
    assert REBUILD.index("build_sentiment_secteurs.py") < REBUILD.index("build_rotation_capitaux.py")
    assert "irCapHead" in JS
    assert "irCapBody" in JS
    assert "ir-rcap-arrow" in JS
    assert "confiance" in JS
    assert "<h2>INDICE ROTATION</h2>" in JS


def test_paire_reelle_et_scores():
    assert DATA["ok"] is True
    p = DATA["classes"]["paire"]
    assert p["from_id"] != p["to_id"]
    assert p["from_label"] and p["to_label"]
    assert p["confiance"] in ("faible", "moyenne", "forte")
    assert 0 <= p["from"]["sortie"] <= 100
    assert 0 <= p["to"]["entree"] <= 100
    assert "Flux ETF" in p["pourquoi"]
    assert DATA["flux_etf"]["disponibles"] is False
    alt = DATA["classes"]["alternative"]
    assert alt is not None
    assert alt["from_id"] != alt["to_id"]
    assert (alt["from_id"], alt["to_id"]) != (p["from_id"], p["to_id"])
    ids = {r["id"] for r in DATA["classes"]["lignes"]}
    assert ids == {"actions", "obligations", "metaux", "energie", "crypto", "liquidites", "immobilier"}
    for r in DATA["classes"]["lignes"]:
        assert r["sortie"] is not None and 0 <= r["sortie"] <= 100
        assert r["entree"] is not None and 0 <= r["entree"] <= 100
        assert r["sentiment"] is not None
    # Liquidités : pas de RSI inventé
    liq = next(r for r in DATA["classes"]["lignes"] if r["id"] == "liquidites")
    assert liq["rsi"] is None
    assert any("rsi" in m for m in liq["missing"])
    # secteurs US
    sec = DATA["secteurs_actions_us"]
    assert sec["ok"] is True
    assert sec["paire"]["from_id"] != sec["paire"]["to_id"]
    assert len(sec["lignes"]) == 11


def test_affichage_aligne_sur_les_donnees():
    a = DATA["affichage"]
    p = DATA["classes"]["paire"]
    assert a["from_label"] == p["from_label"]
    assert a["to_label"] == p["to_label"]
    assert a["confiance"] == p["confiance"]
    assert "→" in a["ligne"]
    assert "confiance" in a["ligne"]
    assert a["infobulle"]
    assert "data/sentiment_secteurs.json" in [s["nom"] for s in DATA["sources"]]
