"""t470u / t475u : note métaux −50 à 250, points entiers comme les actions."""
from __future__ import annotations
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
import sys
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from apex.score import fg_points, load_cnn_fg, montant_template_metaux  # noqa: E402
from apex.config import regles  # noqa: E402
from apex.metaux_points import moyenne_ligne  # noqa: E402


def test_fg_grille_identique_actions():
    assert fg_points(50) == 0
    assert fg_points(40) == 10
    assert fg_points(0) == 50
    assert fg_points(60) == -10
    assert fg_points(100) == -50
    assert fg_points(17.7) == 30
    fg = load_cnn_fg()
    assert fg["ok"] and fg["points"] == fg_points(fg["value"])


def test_barème_entier_comme_actions():
    mx = regles()["apex_metaux"]
    pts = mx["points"]
    assert pts["rsi"] == 30 and pts["macd"] == 30 and pts["fibonacci"] == 30 and pts["cci"] == 20
    assert pts["rsi"] + pts["macd"] + pts["fibonacci"] + pts["cci"] == 110
    assert pts["fondamental"] == 90 and pts["structure"] == 0
    assert mx.get("retirer_structure") is True and mx.get("ne_pas_redistribuer_structure") is True
    assert pts["fear_greed"] == 50
    assert mx["note_min"] == -50 and mx["note_max"] == 250
    assert mx["gi_seuil"] == 130 and mx["gi_pas_note"] == 24


def test_structure_plus_dans_la_note():
    # la fonction peut encore exister, mais elle n'entre plus dans le total
    import inspect
    from apex import metaux_points as MP
    src = inspect.getsource(MP.score_instrument)
    assert "structure_points(c, hi, lo)" not in src
    assert "Struct." not in src


def test_gi_aligne_actions():
    assert montant_template_metaux(129) is None
    assert montant_template_metaux(130) == 500
    assert montant_template_metaux(250) == 1000


def test_regles_grid_points_entiers():
    js = (ROOT / "src" / "regles.js").read_text(encoding="utf-8")
    grid = js.split("function rgMetauxGrid")[1].split("function rgCryptoChamp")[0] if "function rgCryptoChamp" in js else js.split("function rgMetauxGrid")[1].split("function rgPageHTML")[0]
    assert 'data-group="sentiment"' in grid
    assert 'data-group="structure"' not in grid
    assert "Fear & Greed" in grid
    assert "CCI Stochastic" in grid
    intro = regles()["apex_metaux"]["intro_courte"]
    assert "−50 à 250" in intro
    assert "26,3" not in js and "113,2" not in js and "86,8" not in grid


def test_notes_lignes_metaux_json():
    mt = json.loads((ROOT / "data" / "metaux.json").read_text(encoding="utf-8"))
    got = {r["nom"]: r["apex10"]["note"] for r in mt["rows"]}
    assert got["Or"] == 87
    assert got["Argent"] == 136
    assert got["Platine"] == 112
    assert got["Palladium"] == 139
    for r in mt["rows"]:
        a = r["apex10"]
        assert a["scale"] == 250
        assert a["cap"] == "moyenne"
        assert isinstance(a["note"], int) or float(a["note"]) == int(a["note"])
        assert -50 <= a["note"] <= 250
        assert "/ 250" in (a.get("ligne") or "")
        # détail d'un instrument : uniquement des entiers
        ml = r.get("mlist") or {}
        for it in [ml.get("head")] + list(ml.get("items") or []):
            if not it or not it.get("apex10") or it["apex10"].get("note") is None:
                continue
            n = it["apex10"]["note"]
            assert int(n) == n
            ligne = it["apex10"].get("ligne") or ""
            assert "Struct." not in ligne
            if it.get("kind") == "spot":
                assert "Hype" in ligne or "HYPE" in ligne
            else:
                assert "Hype" not in ligne and "HYPE" not in ligne
            decomp = (it["apex10"].get("decomp") or {}).get("points") or {}
            if it.get("kind") == "min" and it["apex10"].get("fond") is not None:
                assert "Fond." in ligne
            else:
                assert "Fond." not in ligne
                assert decomp.get("structure") is None
