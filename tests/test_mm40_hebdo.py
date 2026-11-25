"""MM40 hebdo (équivalent MM200 jours), à contre-courant, 0 à +125."""
from __future__ import annotations
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
import sys
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from apex.score import (  # noqa: E402
    mm40_hebdo_points, mm40_hebdo_texte, MM40_HEBDO_MAX, MM40_HEBDO_MAX_AUTRES, round_half,
)
from apex.config import regles  # noqa: E402
from apex import metaux_points as MP  # noqa: E402
from apex import crypto_points as CP  # noqa: E402


def _closes(last, mm, n=52):
    """Série dont la MM40 vaut exactement `mm` et la dernière clôture `last`."""
    head = [mm] * 39
    # 39*mm + last != 40*mm unless last==mm; we want MM40 of the last 40 = mm,
    # so the 40-window is 39 values of x plus last, with (39x + last)/40 = mm
    # => 39x = 40*mm - last => x = (40*mm - last)/39
    x = (40 * mm - last) / 39.0
    return [100.0] * (n - 40) + [x] * 39 + [last]


def test_barème_lineaire_et_plafond():
    assert MM40_HEBDO_MAX == 125
    # au-dessus et sur la moyenne : 0
    pts, det = mm40_hebdo_points(_closes(115, 100))
    assert pts == 0 and det["ecart_pct"] == 15.0
    pts, det = mm40_hebdo_points(_closes(100, 100))
    assert pts == 0 and abs(det["ecart"]) < 1e-12
    # −16 % : 125 × 16/40 = 50 pile
    pts, det = mm40_hebdo_points(_closes(84, 100))
    assert abs(det["ecart"] + 0.16) < 1e-9
    assert pts == 50
    # −32 % : 100 pile
    pts, det = mm40_hebdo_points(_closes(68, 100))
    assert abs(det["ecart"] + 0.32) < 1e-9
    assert pts == 100
    # −20 % : 125 × 20/40 = 62,5 → arrondi Python (banker's) 62
    pts, det = mm40_hebdo_points(_closes(80, 100))
    assert abs(det["ecart"] + 0.20) < 1e-9
    assert pts == int(round_half(62.5))
    # −40 % : plafond 125
    pts, det = mm40_hebdo_points(_closes(60, 100))
    assert abs(det["ecart"] + 0.40) < 1e-9
    assert pts == 125
    # au-delà de −40 % : toujours 125
    pts, det = mm40_hebdo_points(_closes(50, 100))
    assert det["ecart"] < -0.40 and pts == 125
    # historique trop court
    pts, det = mm40_hebdo_points([1, 2, 3])
    assert pts is None and det["etat"] == "n.c."


def test_bareme_autres_30():
    assert MM40_HEBDO_MAX_AUTRES == 30
    # −16 % : 30 × 16/40 = 12
    pts, det = mm40_hebdo_points(_closes(84, 100), max_pts=30)
    assert abs(det["ecart"] + 0.16) < 1e-9
    assert pts == 12 and det["max"] == 30
    # −40 % et au-delà : plafond 30
    pts, det = mm40_hebdo_points(_closes(60, 100), max_pts=30)
    assert pts == 30
    pts, det = mm40_hebdo_points(_closes(50, 100), max_pts=30)
    assert det["ecart"] < -0.40 and pts == 30
    # au-dessus : 0
    pts, _ = mm40_hebdo_points(_closes(110, 100), max_pts=30)
    assert pts == 0


def test_bareme_short_inversee():
    # sous la MM40 et sur la moyenne : 0
    pts, det = mm40_hebdo_points(_closes(85, 100), max_pts=30, sens="short")
    assert pts == 0 and det["ecart_pct"] == -15.0 and det["sens"] == "short"
    pts, _ = mm40_hebdo_points(_closes(100, 100), max_pts=30, sens="short")
    assert pts == 0
    # +16 % : 30 × 16/40 = 12
    pts, det = mm40_hebdo_points(_closes(116, 100), max_pts=30, sens="short")
    assert abs(det["ecart"] - 0.16) < 1e-9
    assert pts == 12
    # +40 % et au-delà : plafond 30
    pts, det = mm40_hebdo_points(_closes(140, 100), max_pts=30, sens="short")
    assert abs(det["ecart"] - 0.40) < 1e-9 and pts == 30
    pts, det = mm40_hebdo_points(_closes(160, 100), max_pts=30, sens="short")
    assert det["ecart"] > 0.40 and pts == 30


def test_texte_decomposition():
    assert mm40_hebdo_texte(-0.2044, 125) == "MM40 hebdo : écart −20,4 %, +125 pts"
    assert mm40_hebdo_texte(0.032, 0) == "MM40 hebdo : écart +3,2 %, 0 pts"
    assert "MM40 hebdo" in mm40_hebdo_texte(-0.40, 125)


def test_regles_et_page():
    mx = regles()["apex_metaux"]
    cx = regles()["apex_crypto"]
    assert mx["points"]["mm40"] == 125 and cx["points"]["mm40"] == 125
    assert "125" in mx["regles_courtes"]["mm40"] and "comptant" in mx["regles_courtes"]["mm40"].lower()
    assert "30" in mx["regles_courtes"]["mm40"]
    assert mx["points"].get("mm40_autres") == 30
    assert "125" in cx["regles_courtes"]["mm40"]
    for key in ("apex_obligations", "apex_energie", "apex_achat_v2"):
        bloc = regles()[key]
        if key == "apex_achat_v2":
            assert bloc["mm40"]["max"] == 30
        else:
            assert bloc["points"]["mm40"] == 30
    sh = regles()["apex_short"]
    assert sh["mm40"]["applique"] is True and sh["mm40"]["max"] == 30
    assert sh["grille"]["mm40"]["max"] == 30
    assert "sous la MM40" in sh["grille"]["mm40"]["regle"] or "sous la MM40" in sh["mm40"]["precision"]
    js = (ROOT / "src" / "regles.js").read_text(encoding="utf-8")
    grid_m = js.split("function rgMetauxGrid")[1].split("function rgCryptoChamp")[0]
    grid_c = js.split("function rgCryptoGrid")[1].split("function rgLiquidites")[0] if "function rgLiquidites" in js.split("function rgCryptoGrid")[1] else js.split("function rgCryptoGrid")[1][:4000]
    assert 'data-group="mm40"' in grid_m and "MM40 hebdo" in grid_m
    assert 'data-group="mm40"' in grid_c and "MM40 hebdo" in grid_c
    assert "pts.mm40" in grid_m and "pts.mm40" in grid_c


def test_spot_125_etc_et_minieres_30():
    import inspect
    src = inspect.getsource(MP.score_instrument)
    assert "mm40_hebdo_points" in src
    assert "max_pts=mm40_max" in src or "max_pts = mm40_max" in src or "max_pts=mm40_max" in src.replace(" ", "")
    mt = json.loads((ROOT / "data" / "metaux.json").read_text(encoding="utf-8"))
    for r in mt["rows"]:
        items = [(r.get("mlist") or {}).get("head")] + list(((r.get("mlist") or {}).get("items") or []))
        for it in items:
            if not it or not it.get("apex10"):
                continue
            dec = (it["apex10"].get("decomp") or {})
            pts = dec.get("points") or {}
            ligne = it["apex10"].get("ligne") or dec.get("texte") or ""
            assert pts.get("mm40") is not None or (dec.get("mm40") or {}).get("etat") == "n.c."
            assert "MM40 hebdo" in ligne
            mx = (dec.get("mm40") or {}).get("max")
            if it.get("kind") == "spot":
                assert mx == 125
                assert "écart" in ligne or (dec.get("mm40") or {}).get("etat") == "n.c."
            else:
                assert mx == 30 or (dec.get("mm40") or {}).get("etat") == "n.c."


def test_crypto_toutes_notees():
    import inspect
    src = inspect.getsource(CP.score_asset)
    assert "mm40_hebdo_points" in src
    data = json.loads((ROOT / "data" / "crypto_fiches.json").read_text(encoding="utf-8"))
    for a in data["assets"]:
        rec = a.get("apex10") or {}
        pts = (rec.get("decomp") or {}).get("points") or {}
        assert pts.get("mm40") is not None, a.get("key")
        assert "MM40 hebdo" in (rec.get("ligne") or "")
        assert "écart" in (rec.get("ligne") or "")
