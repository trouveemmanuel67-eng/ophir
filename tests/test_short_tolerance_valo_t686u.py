"""t686u (27/11/2026) : note SHORT, fondamental tolérant (10 + 10 par critère non rempli) et valorisation excessive (0 à +30)."""
from __future__ import annotations
import json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT)]
import build_short250 as S  # noqa: E402

CFG = json.loads((ROOT / "config" / "regles.json").read_text(encoding="utf-8"))["apex_short"]
SHORT = json.loads((ROOT / "data" / "apex_short.json").read_text(encoding="utf-8"))
VALO = json.loads((ROOT / "data" / "valo_short.json").read_text(encoding="utf-8"))


def test_config_t686u():
    assert CFG["fond_tolerance"] == {"base": 10, "pas": 10, "tache": "t686u"}
    v = CFG["valorisation"]
    assert v["max"] == 30 and v["ratio_0"] == 1.0 and v["ratio_max"] == 2.0
    assert CFG["degradation_min"] == 0
    assert "valorisation" in CFG["total"]


def test_valo_bareme(monkeypatch):
    doc = {"genere": "x", "secteurs": {"Technology": {"mediane_per": 20.0, "n": 100}},
           "by_yahoo": {"A": {"sector": "Technology", "per": 20.0}, "B": {"sector": "Technology", "per": 30.0},
                         "C": {"sector": "Technology", "per": 40.0}, "D": {"sector": "Technology", "per": 90.0},
                         "E": {"sector": "Technology", "per": None}, "F": {"sector": "Technology", "per": 10.0}}}
    monkeypatch.setattr(S, "_VALO", doc)
    assert S.valo_points("A")[0] == 0
    assert S.valo_points("B")[0] == 15
    assert S.valo_points("C")[0] == 30
    assert S.valo_points("D")[0] == 30  # plafonné
    assert S.valo_points("F")[0] == 0
    assert S.valo_points("E")[0] is None  # n.c. : aucune invention
    assert S.valo_points("ZZZ")[0] is None


def test_donnees_valo():
    assert VALO["n"] >= 400 and "Technology" in VALO["secteurs"]
    for r in SHORT["by_tv"].values():
        v = r["points"].get("valorisation")
        assert v is None or (isinstance(v, int) and 0 <= v <= 30)
        assert 10 <= r["points"]["fondamental"] <= 100
        assert "Valo" in r["ligne"]


def test_liste_verte_pas_toute():
    notes = [SHORT["by_tv"][tv]["note"] for tv in SHORT["liste"]]
    assert notes and max(notes) >= 130
