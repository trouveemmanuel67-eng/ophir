"""t496u–t501u : Meilleurs short = notes APEX rouges (10 ≤ n < 70), mise levier ×5."""
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


def _js_round(x):
    """Équivalent de Math.round (demi-supérieur), pas le bankers rounding de Python."""
    import math
    return int(math.floor(x + 0.5)) if x >= 0 else int(math.ceil(x - 0.5))


def _montant(n):
    if not (10 <= n < 70):
        return None
    steps = _js_round((69 - max(n, -50)) / 24.0)
    return min(100 + steps * 20, 200)


def test_seuil_tri_montant_et_stockage():
    assert "GS_ROUGE_DE=10" in JS
    assert "GS_ROUGE_A=70" in JS
    assert "GS_SEUIL=69" in JS
    assert "gsIsRouge" in JS
    assert "pilotBand" in JS
    assert "GS_MIRROR" not in JS and "gsMirror" not in JS
    assert "200 −" not in JS and "200 -" not in JS
    assert "!gsIsRouge(rec.note, rec.scale)" in JS or "!gsIsRouge(rec.note,rec.scale)" in JS
    assert "a.note-b.note" in JS
    assert "apex-short-valide" in JS
    assert "apex-gi-valide" in GI
    assert "apex-short-valide" not in GI
    assert "gsIsApexNote" in JS or "gsIsScale250" in JS
    assert "gsIsUsaFranceTv" in JS
    assert "etf_local" in JS
    assert _montant(70) is None
    assert _montant(9) is None
    assert _montant(-3) is None
    assert _montant(-27) is None
    assert _montant(-50) is None
    assert _montant(69) == 100
    assert _montant(45) == 120
    assert _montant(21) == 140
    assert _montant(10) == 140
    assert "Math.floor((GS_SEUIL-n)/24)" in JS or "Math.floor((seuil-n)/24)" in JS or "Math.max(n,floor)" in JS or "GS_SEUIL-Math.max(n,-50)" in JS or "Math.max(n, floor)" in JS
    assert "100+steps*20" in JS
    assert "mise*5" in JS or "mise * 5" in JS


def test_presentation_et_avertissement():
    assert "Meilleurs short" in JS
    assert "/250" in JS
    assert "gs-warn" not in JS
    assert "gs-legende" not in JS
    assert "Le short peut faire perdre plus que la mise" not in JS
    assert "appel de marge" not in JS
    assert "Montants : mise (levier ×5)" not in JS
    assert "20 %" not in JS and "efface la mise" not in JS
    assert "Mise (levier ×5)" in JS
    assert "Validés (${nVal})" in JS
    assert "gs-elliott" in JS and "gs-pattern" in JS and "gs-valid" in JS
    assert "10 ≤ n < 70/250" in JS or "10 ≤ note < 70" in JS
    assert "≤ 70/250" not in JS
    assert "/*__GSJS__*/" in TPL
    assert "bestShortCard" in TPL
    assert "gsInit" in TPL
    assert "gsOn" in POS and "gsListIsOpen" in POS


def test_regles_short_grille():
    short = CFG["apex_short"]
    assert "formule" not in short
    assert short["gi_seuil"] == 69
    assert short["gi_seuil_min"] == 10
    assert short["gi_seuil_max_exclu"] == 70
    assert short["gi_seuil_sens"] == "rouge"
    assert "200 − note LONG" not in RG and "200 - note LONG" not in RG
    assert "function rgShortGrid" in RG
    assert "Règles SHORT à définir" not in RG
    assert "10 ≤ note < 70" in RG
    assert "100 $ à 69" in RG
    assert "100 $" in short["montant"] and "69/250" in short["montant"]
    assert "10 ≤ note < 70" in short["lecture"]
    assert "marge commune Revolut" in short["avertissement"]
    assert "20 %" not in short["avertissement"]


def test_notes_apex_inchangees():
    """Le lot short ne doit pas réécrire les notes APEX déjà publiées."""
    data = json.loads((ROOT / "data" / "crypto_fiches.json").read_text(encoding="utf-8"))
    want = {"btc": 153, "eth": 173, "sol": 137, "mstr": 143}
    for a in data["assets"]:
        rec = a.get("apex10") or {}
        if a.get("key") in want:
            assert rec.get("note") == want[a["key"]]
            assert rec.get("scale") == 250
