"""t470u : note métaux −50 à 250, F&G ±50 grille actions, tech+fond 0..200."""
from __future__ import annotations
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
import sys
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from apex.score import (  # noqa: E402
    fg_points, load_cnn_fg, metaux_fracs, metaux_max_pts, metaux_cfg,
    montant_template_metaux, compute, compute_metaux,
)
from apex.config import regles  # noqa: E402


def test_fg_grille_identique_actions():
    assert fg_points(50) == 0
    assert fg_points(40) == 10
    assert fg_points(30) == 20
    assert fg_points(20) == 30
    assert fg_points(10) == 40
    assert fg_points(0) == 50
    assert fg_points(60) == -10
    assert fg_points(70) == -20
    assert fg_points(80) == -30
    assert fg_points(90) == -40
    assert fg_points(100) == -50
    assert fg_points(17.7) == 30
    fg = load_cnn_fg()
    assert fg["ok"] and fg["points"] == fg_points(fg["value"])


def test_proportions_0_200():
    na = regles()["note_apex"]
    f = metaux_fracs(na, False)
    assert "elliott" not in f
    pts = {k: metaux_max_pts(v) for k, v in f.items()}
    assert abs(sum(pts.values()) - 200) < 1e-6
    assert round(pts["structure"], 1) == 26.3
    assert round(pts["fibonacci"], 1) == 21.1
    assert round(pts["rsi"], 1) == 13.2
    assert round(pts["macd"], 1) == 13.2
    assert round(pts["cci"], 1) == 13.2
    assert round(pts["fond"], 1) == 113.2
    fn = metaux_fracs(na, True)
    assert "fond" not in fn and "elliott" not in fn
    pts0 = {k: metaux_max_pts(v) for k, v in fn.items()}
    assert abs(sum(pts0.values()) - 200) < 1e-6
    assert round(pts0["structure"], 1) == 60.6
    assert round(pts0["fibonacci"], 1) == 48.5
    assert round(pts0["rsi"], 1) == 30.3


def test_compute_dispatch_et_bornes():
    rec = compute(0, None, None, parts={"structure": 0, "fibonacci": 0, "rsi": 0, "macd": 0, "cci": 0}, classe="metaux")
    assert rec["scale"] == 250
    assert rec["total_min"] == -50 and rec["total_max"] == 250
    assert rec["fg_points"] == 30
    # neutre tech + F&G +30 → 100+30 = 130
    assert rec["note"] == 130
    assert "/ 250" in rec["ligne"] and "F&G +30" in rec["ligne"]
    rec2 = compute_metaux(80, 80, None, divergence={"kind": "bullish", "tf": "1W"}, parts={"structure": 100, "fibonacci": 100, "rsi": 100, "macd": 100, "cci": 100})
    assert rec2["note"] <= 250
    rec3 = compute_metaux(-80, None, None, parts={"structure": -100, "fibonacci": -100, "rsi": -100, "macd": -100, "cci": -100})
    # 0 tech + F&G +30 = 30, still >= -50
    assert rec3["note"] >= -50
    assert rec3["note"] == 30


def test_gi_bareme_equivalent():
    assert montant_template_metaux(174) is None
    assert montant_template_metaux(175) == 500
    assert montant_template_metaux(190) == 600
    assert montant_template_metaux(250) == 1000
    mx = regles()["apex_metaux"]
    assert mx["note_min"] == -50 and mx["note_max"] == 250
    assert mx["gi_seuil"] == 175 and mx["gi_pas_note"] == 15
    assert mx["fg_abs"] == 50
    assert mx["cyan_note_min"] == 190 and mx["cyan_plafond"] == 175


def test_regles_grid_sentiment():
    js = (ROOT / "src" / "regles.js").read_text(encoding="utf-8")
    grid = js.split("function rgMetauxGrid")[1].split("function rgPageHTML")[0]
    assert 'data-group="sentiment"' in grid
    assert "Fear & Greed" in grid
    assert "fg_abs" in grid
    assert "rgMetauxMaxPts" in js
    assert "−50 à 250" in regles()["apex_metaux"]["intro_courte"]


def test_notes_lignes_metaux_json():
    mt = json.loads((ROOT / "data" / "metaux.json").read_text(encoding="utf-8"))
    got = {r["nom"]: r["apex10"]["note"] for r in mt["rows"]}
    assert got["Or"] == 162
    assert got["Argent"] == 169
    assert got["Platine"] == 171
    assert got["Palladium"] == 181
    for r in mt["rows"]:
        a = r["apex10"]
        assert a["scale"] == 250
        assert a["cap"] == "moyenne"
        assert -50 <= a["note"] <= 250
        assert "/ 250" in (a.get("ligne") or "")
