"""t487u / t488u : sections RÈGLES LONG Obligations, Liquidités, Placements, Immobilier, Énergie."""
from __future__ import annotations
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
JS = (ROOT / "src" / "regles.js").read_text(encoding="utf-8")
RG = json.loads((ROOT / "config" / "regles.json").read_text(encoding="utf-8"))


def test_sections_dans_la_page_long():
    page = JS.split("function rgPageHTML")[1].split("function rgRender")[0]
    for sid in ("obligations", "liquidites", "placements", "immobilier", "energie"):
        assert f"id:'{sid}'" in page, sid
    assert "rgObligationsGrid()" in page
    assert "rgLiquiditesGrid()" in page
    assert "rgPlacementsGrid()" in page
    assert "rgImmobilierGrid()" in page
    assert "rgEnergieGrid()" in page


def test_modele_actions_sans_elliott_dans_le_calcul():
    for key, has_tech, hi in (
        ("apex_obligations", True, 250),
        ("apex_placements", False, 140),
        ("apex_immobilier", False, 140),
        ("apex_energie", True, 250),
    ):
        cfg = RG[key]
        assert cfg["calcul_aligne"] is False
        pts = cfg["points"]
        assert pts["rsi"] == 30 and pts["macd"] == 30 and pts["fibonacci"] == 30 and pts["cci"] == 20
        assert pts["rsi"] + pts["macd"] + pts["fibonacci"] + pts["cci"] == 110
        assert pts["fondamental"] == 90 and pts["fear_greed"] == 50
        assert cfg["has_technique"] is has_tech
        assert cfg["note_max"] == hi
        assert "25/11" in cfg["regles_courtes"]["macd"]
        assert all(el.get("statut") == "non_calcule" for el in cfg["fond_criteres"]), key
        blob=" ".join([cfg.get("champ_application") or "", cfg.get("intro_courte") or "", cfg.get("note_actuelle") or ""])
        assert "elliott" in blob.lower()


def test_liquidites_deux_parties():
    cfg = RG["apex_liquidites"]
    ids = [p["id"] for p in cfg["parties"]]
    assert ids[:2] == ["epargne", "devises"]
    assert "etf_par_devise" in ids
    epargne = cfg["parties"][0]
    devises = cfg["parties"][1]
    assert epargne["has_technique"] is False and epargne["note_max"] == 140
    assert devises["has_technique"] is True and devises["note_max"] == 250
    assert "Pas de graphique" in epargne["sans_technique"]
    assert all(el.get("statut") == "non_calcule" for p in cfg["parties"] if p["id"] in ("epargne", "devises") for el in p["fond_criteres"])


def test_placements_immobilier_sans_technique():
    assert "Pas de graphique" in RG["apex_placements"]["sans_technique"]
    assert "Pas de graphique" in RG["apex_immobilier"]["sans_technique"]
    assert "n.c." in JS  # affichage des critères non calculés
    assert "rgCible250Board" in JS
