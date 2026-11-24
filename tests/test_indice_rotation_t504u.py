"""t504u : onglet INDICE ROTATION (ratio S&P 500 / WTI de Charles Gave)."""
from __future__ import annotations
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
JS = (ROOT / "src" / "rotation.js").read_text(encoding="utf-8")
TPL = (ROOT / "src" / "template.html").read_text(encoding="utf-8")
POS = (ROOT / "src" / "positions.js").read_text(encoding="utf-8")
BUILD = (ROOT / "src" / "build.py").read_text(encoding="utf-8")
DATA = json.loads((ROOT / "data" / "rotation.json").read_text(encoding="utf-8"))


def test_onglet_place_et_nom():
    assert "<h2>INDICE ROTATION</h2>" in JS
    assert "bestShortCard" in JS
    assert "insertAdjacentHTML('afterend'" in JS
    assert "indiceRotationCard" in JS
    assert "/*__IRJS__*/" in TPL
    assert "irInit" in TPL
    assert TPL.index("/*__GSJS__*/") < TPL.index("/*__IRJS__*/")
    assert TPL.index("gsInit") < TPL.index("irInit")
    assert "dataRotation" in TPL
    assert "__DATA_ROTATION__" in TPL
    assert "__DATA_ROTATION__" in BUILD
    assert "rotation.js" in BUILD
    assert "irListIsOpen" in POS
    assert "irOn" in POS
    assert "INDICE ROTATION" in TPL
    # sous Meilleurs short dans le rail, pas dans la nav principale
    assert "indiceRotationCard" in TPL
    nav = TPL.split("const TABS=")[1].split("];")[0]
    assert "INDICE ROTATION" not in nav


def test_donnees_reelles_pas_inventees():
    off = DATA["officiel"]
    assert off and off["ratio"] > 0 and off["ma84"] > 0
    assert off["spx"] > 0 and off["wti"] > 0
    assert abs(off["ratio"] - off["spx"] / off["wti"]) < 1e-3
    assert DATA["ma_mois"] == 84
    assert DATA["historique"]["n_ma"] >= 400  # historique long
    assert DATA["historique"]["premier_ma"] <= "1983-12"
    assert DATA["serie"]
    assert DATA["serie"][0]["m"] == DATA["historique"]["premier_ma"]
    # mois en cours exclu de la série officielle
    assert DATA["officiel"]["month"] == DATA["historique"]["dernier_mois"]
    assert all("r" in p and "ma" in p for p in DATA["serie"])
    assert "Yahoo" in DATA["sources_donnees"][0]["nom"]
    assert any("WTISPLC" in s["nom"] for s in DATA["sources_donnees"])
    assert any("DCOILWTICO" in s["nom"] for s in DATA["sources_donnees"])
    assert any("Gavekal" in s["nom"] for s in DATA["sources_cadre"])
    assert any("Institut des Libertés" in s["nom"] for s in DATA["sources_cadre"])
    # sources brutes présentes
    assert (ROOT / "data" / "rotation" / "fred_WTISPLC.csv").exists()
    assert (ROOT / "data" / "rotation" / "spx_daily.csv").exists()
    assert (ROOT / "data" / "rotation" / "fred_DCOILWTICO.csv").exists()


def test_regime_coherent_avec_la_moyenne():
    off = DATA["officiel"]
    if off["ratio"] > off["ma84"]:
        assert off["above"] is True
        assert DATA["regime_officiel"]["id"] == "boom"
        assert off["ecart_pct"] > 0
    elif off["ratio"] < off["ma84"]:
        assert off["above"] is False
        assert DATA["regime_officiel"]["id"] == "bust"
        assert off["ecart_pct"] < 0
    cross = DATA["dernier_croisement"]
    assert cross and cross["month"] <= off["month"]
    assert cross["to"] in ("above", "below")


def test_copy_cadre_et_dates():
    assert "irUpdated" in JS and "heure de Paris" in JS
    assert "irCrossTxt" in JS
    assert "Régime officiel" in JS
    assert "Lecture provisoire" in JS
    assert "Aucun rendement n’est promis" in DATA["avertissement"] or "Aucun rendement" in DATA["avertissement"]
    assert "bust énergétique" in (DATA["regime_officiel"]["rotation"] + DATA.get("regime_officiel", {}).get("rotation", ""))
