"""t687u (27/11/2026) : short interest à contre-courant dans la note SHORT (+10 peu shorté … −20 très shorté)."""
from __future__ import annotations
import json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT)]
import build_short250 as S  # noqa: E402

CFG = json.loads((ROOT / "config" / "regles.json").read_text(encoding="utf-8"))["apex_short"]
SHORT = json.loads((ROOT / "data" / "apex_short.json").read_text(encoding="utf-8"))


def test_bareme_si():
    f = S.si_points_from
    assert f(None) is None  # donnée absente : n.c., pas d'invention
    assert f(0.5) == 10 and f(2.0) == 10
    assert f(3.5) == 5 and f(5.0) == 0
    assert f(10.0) == -10 and f(15.0) == -20 and f(40.0) == -20
    assert f(1.0, 8) == 5  # jours pour couvrir ≥ 7 : −5
    assert f(20.0, 9) == -20  # borné


def test_config_et_donnees():
    g = CFG["grille"]["short_interest"]
    assert g["max"] == 10 and g["min"] == -20
    assert CFG["short_interest"]["tache"] == "t687u"
    for r in SHORT["by_tv"].values():
        v = r["points"].get("short_interest")
        assert v is None or -20 <= v <= 10
        assert "SI " in r["ligne"]
