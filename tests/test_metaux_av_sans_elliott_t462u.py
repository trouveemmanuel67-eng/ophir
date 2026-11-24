"""t462u : Elliott retiré du bandeau Achat/Vente des métaux, sans redistribution."""
from __future__ import annotations
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGLES = json.loads((ROOT / "config" / "regles.json").read_text(encoding="utf-8"))
JS = (ROOT / "src" / "regles.js").read_text(encoding="utf-8")
CORE = (ROOT / "src" / "ind_core.py").read_text(encoding="utf-8")
BM = (ROOT / "src" / "build_metaux.py").read_text(encoding="utf-8")
BARS = (ROOT / "src" / "build_apex_bars.py").read_text(encoding="utf-8")


def test_config_av_sans_elliott():
    mx = REGLES["apex_metaux"]
    assert mx["av_sans_elliott"] is True
    assert mx["av_ne_pas_redistribuer_elliott"] is True
    assert mx["av_pas_plafond_zone_rouge"] is True
    assert "85" in (mx.get("effet_echelle_av") or "")
    assert "60" in (mx.get("effet_echelle_av") or "")
    prec = next(c["precision"] for c in REGLES["fiche_regles"]["classes"] if c["id"] == "metaux")
    assert "t462u" in prec


def test_builders_flag_metaux_seulement():
    assert "sans_elliott=False" in CORE
    assert "sans_elliott=True" in BM
    assert "sans_elliott=(it.get('src')=='metaux')" in BARS
    for fn in ("build_energie.py", "build_crypto_fiches.py", "build_obligations.py"):
        p = ROOT / "src" / fn
        if p.exists():
            txt = p.read_text(encoding="utf-8")
            assert "sans_elliott=True" not in txt, fn


def test_av_agrege_garde_le_trou():
    import sys
    sys.path.insert(0, str(ROOT / "src"))
    import ind_core as K
    others = [
        {"nom": "a", "poids": 0.85, "note": 100.0},
    ]
    # sans trou (redistribution) : amplitude reste ±100
    s, _ = K.av_agrege([dict(x) for x in others], hole=0.0)
    assert s == 100.0
    # avec trou 15 % : amplitude ±85, comme Elliott retiré sans redistribuer
    s, comps = K.av_agrege([dict(x) for x in others], hole=0.15)
    assert s == 85.0
    assert comps[0]["contrib"] == 85.0
    # le seuil +60 reste atteignable (85 > 60)
    assert s > 60


def test_page_regles_carte_av():
    grid = JS.split("function rgMetauxGrid")[1].split("function rgPageHTML")[0]
    assert "Bandeau Achat / Vente" in grid
    assert "effet_echelle_av" in grid
    assert "sans redistribuer" in grid
    assert "rgCard('av'" in grid
