"""Meilleurs short : notes ≥ 70/250 (orange, vert ou cyan), plafond 10, hors positions déjà ouvertes."""
from __future__ import annotations
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
JS = (ROOT / "src" / "best_short.js").read_text(encoding="utf-8")
RG = (ROOT / "src" / "regles.js").read_text(encoding="utf-8")
CFG = json.loads((ROOT / "config" / "regles.json").read_text(encoding="utf-8"))
SHORT = json.loads((ROOT / "data" / "apex_short.json").read_text(encoding="utf-8"))


def test_seuil_liste_70():
    s = CFG["apex_short"]
    assert s["seuil_liste"] == 70
    assert s["n_liste_max"] == 10
    assert s["seuil"] == 70
    assert SHORT.get("seuil_liste") == 70
    assert "GS_SEUIL_LISTE=70" in JS
    assert "gsSeuilListe" in JS
    lect = (s.get("lecture") or "") + RG
    assert "70" in lect
    assert "orange" in lect.lower()


def test_liste_orange_vert_cyan_plafond_10():
    by = SHORT["by_tv"]
    liste = SHORT["liste"]
    assert SHORT["n_liste"] == len(liste)
    assert 1 <= len(liste) <= int(SHORT.get("n_liste_max") or 10)
    notes = []
    for tv in liste:
        rec = by[tv]
        assert rec["note"] >= 70, tv
        assert rec.get("liste") is True
        assert rec.get("fibo_ok") is True
        assert rec.get("tech_ok") is True
        assert not rec.get("held_position")
        tick = tv.split(":")[-1].upper()
        assert tick not in {"XRP", "BTC", "ETH", "DOGE", "SOL"} and not tick.startswith("XRP")
        notes.append(rec["note"])
    # tri décroissant
    assert notes == sorted(notes, reverse=True)
    for rec in by.values():
        if rec.get("liste"):
            assert rec["note"] >= SHORT.get("seuil_liste", 70)


def test_pas_de_complement_sous_70_ni_positions():
    elig = [
        r for r in SHORT["by_tv"].values()
        if r.get("note") is not None and r["note"] >= 70
        and r.get("fibo_ok") and r.get("tech_ok") and not r.get("held_position")
    ]
    assert SHORT["n_liste"] == min(len(elig), 10)
    sous = [r for r in SHORT["by_tv"].values() if r.get("liste") and r["note"] < 70]
    assert sous == []
    held = [r for r in SHORT["by_tv"].values() if r.get("liste") and r.get("held_position")]
    assert held == []
