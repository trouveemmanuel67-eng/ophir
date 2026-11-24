"""t502u : ligne or au comptant Revolut (XAU / OANDA:XAUUSD) dans les métaux."""
from __future__ import annotations
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = (ROOT / "src" / "build_metaux.py").read_text(encoding="utf-8")
DISP = json.loads((ROOT / "data" / "disponibilites.json").read_text(encoding="utf-8"))
RV = (ROOT / "src" / "revolut_rules.py").read_text(encoding="utf-8")


def test_spot_or_dans_le_source():
    assert "OANDA:XAUUSD" in SRC
    assert "'or':('OANDA:XAUUSD','XAU','Or au comptant Revolut')" in SRC.replace(" ", "") or (
        "OANDA:XAUUSD" in SRC and "Or au comptant Revolut" in SRC
    )
    assert "pas de ticker XAU dans disponibilites" not in SRC
    assert "n'est pas ajouté comme instrument" not in SRC


def test_disponibilites_et_yahoo_proxy():
    rec = DISP["symbols"]["OANDA:XAUUSD"]
    assert rec["revolut"] is True
    assert "OANDA:XAUUSD':'GC=F" in RV or "OANDA:XAUUSD\":'GC=F" in RV


def test_ligne_presente_dans_metaux_json_si_deja_construit():
    p = ROOT / "data" / "metaux.json"
    if not p.exists():
        return
    data = json.loads(p.read_text(encoding="utf-8"))
    # Après rebuild uniquement ; on accepte l'absence avant build_metaux.
    rows = {r["key"]: r for r in data.get("rows") or []}
    orow = rows.get("or") or {}
    ml = orow.get("mlist") or {}
    tvs = [((ml.get("head") or {}).get("tv"))] + [it.get("tv") for it in (ml.get("items") or [])]
    if "OANDA:XAUUSD" in tvs:
        spot = next(it for it in (ml.get("items") or []) if it.get("tv") == "OANDA:XAUUSD")
        assert spot.get("kind") == "spot"
        assert "comptant" in (spot.get("name") or "").lower()
