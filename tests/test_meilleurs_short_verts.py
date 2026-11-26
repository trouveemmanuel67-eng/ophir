"""Meilleurs short : uniquement notes vertes ou mieux (seuil 130), sans complément orange, plafond 10."""
from __future__ import annotations
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
JS = (ROOT / "src" / "best_short.js").read_text(encoding="utf-8")
RG = (ROOT / "src" / "regles.js").read_text(encoding="utf-8")
TPL = (ROOT / "src" / "template.html").read_text(encoding="utf-8")
CFG = json.loads((ROOT / "config" / "regles.json").read_text(encoding="utf-8"))
SHORT = json.loads((ROOT / "data" / "apex_short.json").read_text(encoding="utf-8"))


def test_seuil_vert_130():
    s = CFG["apex_short"]
    assert s["seuil_liste"] == 130
    assert s["n_liste_max"] == 10
    assert s["rsi_hebdo_min"] == 60
    assert s["seuil"] == 70  # barème de mise inchangé
    assert SHORT.get("seuil_liste") == 130
    assert "GS_SEUIL_LISTE=130" in JS
    assert "gsSeuilListe" in JS
    assert "verte ou mieux" in (s.get("lecture") or "") or "130" in RG


def test_liste_uniquement_verte_sans_orange():
    by = SHORT["by_tv"]
    liste = SHORT["liste"]
    assert SHORT["n_liste"] == len(liste)
    assert len(liste) <= int(SHORT.get("n_liste_max") or 10)
    for tv in liste:
        rec = by[tv]
        assert rec["note"] >= 130, tv
        assert rec.get("liste") is True
        assert rec.get("fibo_ok") is True
        assert rec.get("tech_ok") is True
        assert not rec.get("held_position")
        tick = tv.split(":")[-1].upper()
        assert tick not in {"XRP", "BTC", "ETH", "DOGE", "SOL"} and not tick.startswith("XRP")
    # aucun orange / rouge dans la liste
    for rec in by.values():
        if rec.get("liste"):
            assert rec["note"] >= 130
            assert rec["note"] >= SHORT.get("seuil_liste", 130)


def test_pas_de_complement_orange():
    verts = [r for r in SHORT["by_tv"].values()
             if r.get("note") is not None and r["note"] >= 130
             and r.get("fibo_ok") and r.get("tech_ok") and not r.get("held_position")]
    # La liste ne dépasse pas les verts éligibles, et n'ajoute pas d'orange pour faire 10
    assert SHORT["n_liste"] == min(len(verts), 10)
    oranges = [r for r in SHORT["by_tv"].values() if r.get("liste") and 70 <= r["note"] < 130]
    assert oranges == []
