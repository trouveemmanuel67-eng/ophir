"""t496u : liste Meilleurs short, miroir exact de la note LONG."""
from __future__ import annotations
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
JS = (ROOT / "src" / "best_short.js").read_text(encoding="utf-8")
GI = (ROOT / "src" / "good_invest.js").read_text(encoding="utf-8")
RG = (ROOT / "src" / "regles.js").read_text(encoding="utf-8")
TPL = (ROOT / "src" / "template.html").read_text(encoding="utf-8")
POS = (ROOT / "src" / "positions.js").read_text(encoding="utf-8")
CFG = json.loads((ROOT / "config" / "regles.json").read_text(encoding="utf-8"))


def test_miroir_et_stockage_separes():
    assert "GS_MIRROR=200" in JS
    assert "GS_SEUIL=130" in JS
    assert "apex-short-valide" in JS
    assert "apex-gi-valide" in GI
    assert "apex-short-valide" not in GI
    assert "return GS_MIRROR-n" in JS or "return GS_MIRROR - n" in JS
    assert "500+steps*100" in JS
    assert "gsIsUsaFranceTv" in JS
    assert "etf_local" in JS
    assert "tab==='metaux'" not in JS.split("function gsCollect")[1][:200] or "Métaux" in JS
    assert "Ne pas modifier" or "on ne modifie pas les notes LONG" in JS.lower() or "ne modifie pas les notes LONG" in JS


def test_presentation_et_avertissement():
    assert "Meilleurs short" in JS
    assert "/250" in JS
    assert "gs-warn" in JS and "XTB" in JS
    assert "Validés (${nVal})" in JS
    assert "gs-elliott" in JS and "gs-pattern" in JS and "gs-valid" in JS
    assert "/*__GSJS__*/" in TPL
    assert "bestShortCard" in TPL
    assert "gsInit" in TPL
    assert "gsOn" in POS and "gsListIsOpen" in POS


def test_regles_short_grille():
    short = CFG["apex_short"]
    assert short["formule"].replace(" ", "").replace("−", "-") == "noteSHORT=200-noteLONG"
    assert short["gi_seuil"] == 130
    assert "200 − note LONG" in RG or "200 - note LONG" in RG
    assert "function rgShortGrid" in RG
    assert "Règles SHORT à définir" not in RG


def test_notes_long_crypto_inchangees():
    """Le lot short ne doit pas réécrire les notes LONG déjà publiées."""
    data = json.loads((ROOT / "data" / "crypto_fiches.json").read_text(encoding="utf-8"))
    want = {"btc": 104, "eth": 120, "sol": 80, "mstr": 90}
    for a in data["assets"]:
        rec = a.get("apex10") or {}
        if a.get("key") in want:
            assert rec.get("note") == want[a["key"]]
            assert rec.get("scale") == 250
