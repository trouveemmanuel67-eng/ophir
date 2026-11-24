"""t496u–t499u : Meilleurs short = plus mauvaises notes APEX (≤ 70), mise levier ×5."""
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


def _montant(n):
    if n > 70:
        return None
    steps = int(round((70 - max(n, -50)) / 24.0))
    return min(100 + steps * 20, 200)


def test_seuil_tri_montant_et_stockage():
    assert "GS_SEUIL=70" in JS
    assert "GS_MIRROR" not in JS and "gsMirror" not in JS
    assert "200 −" not in JS and "200 -" not in JS
    assert "Number(rec.note)>GS_SEUIL" in JS
    assert "a.note-b.note" in JS
    assert "apex-short-valide" in JS
    assert "apex-gi-valide" in GI
    assert "apex-short-valide" not in GI
    assert "gsIsUsaFranceTv" in JS
    assert "etf_local" in JS
    assert _montant(70) == 100
    assert _montant(46) == 120
    assert _montant(22) == 140
    assert _montant(-2) == 160
    assert _montant(-26) == 180
    assert _montant(-50) == 200
    assert "GS_SEUIL-Math.max(n,-50)" in JS or "GS_SEUIL-Math.max(n, -50)" in JS
    assert "100+steps*20" in JS
    assert "mise*5" in JS or "mise * 5" in JS


def test_presentation_et_avertissement():
    assert "Meilleurs short" in JS
    assert "/250" in JS
    assert "gs-warn" in JS and "XTB" in JS
    assert "marge commune Revolut" in JS
    assert "appel de marge" in JS
    assert "20 %" not in JS and "efface la mise" not in JS
    assert "mise (levier ×5)" in JS
    assert "Validés (${nVal})" in JS
    assert "gs-elliott" in JS and "gs-pattern" in JS and "gs-valid" in JS
    assert "note APEX ≤ 70/250" in JS
    assert "/*__GSJS__*/" in TPL
    assert "bestShortCard" in TPL
    assert "gsInit" in TPL
    assert "gsOn" in POS and "gsListIsOpen" in POS


def test_regles_short_grille():
    short = CFG["apex_short"]
    assert "formule" not in short
    assert short["gi_seuil"] == 70
    assert "200 − note LONG" not in RG and "200 - note LONG" not in RG
    assert "function rgShortGrid" in RG
    assert "Règles SHORT à définir" not in RG
    assert "≤ " in RG or "70" in RG
    short = CFG["apex_short"]
    assert "100 $" in short["montant"] and "levier" in short["montant"]
    assert "marge commune Revolut" in short["avertissement"]
    assert "20 %" not in short["avertissement"]


def test_notes_apex_inchangees():
    """Le lot short ne doit pas réécrire les notes APEX déjà publiées."""
    data = json.loads((ROOT / "data" / "crypto_fiches.json").read_text(encoding="utf-8"))
    want = {"btc": 104, "eth": 120, "sol": 80, "mstr": 90}
    for a in data["assets"]:
        rec = a.get("apex10") or {}
        if a.get("key") in want:
            assert rec.get("note") == want[a["key"]]
            assert rec.get("scale") == 250
