"""APE-32 (t514u–t521u) : Meilleurs short = note SHORT sur 250 (≥ 130) + filtre Fibonacci 38,2 %, mise levier ×5."""
from __future__ import annotations
import json, math, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT)]
JS = (ROOT / "src" / "best_short.js").read_text(encoding="utf-8")
GI = (ROOT / "src" / "good_invest.js").read_text(encoding="utf-8")
RG = (ROOT / "src" / "regles.js").read_text(encoding="utf-8")
TPL = (ROOT / "src" / "template.html").read_text(encoding="utf-8")
POS = (ROOT / "src" / "positions.js").read_text(encoding="utf-8")
CFG = json.loads((ROOT / "config" / "regles.json").read_text(encoding="utf-8"))


def _montant(n, seuil=70):
    if n < seuil:
        return None
    return min(100 + int(math.floor((n - seuil) / 24)) * 20, 200)


def test_seuil_tri_montant_et_stockage():
    assert "GS_SEUIL=70" in JS
    assert "dataShort" in JS and "dataShort" in TPL and "__DATA_SHORT__" in TPL
    assert "fibo_ok!==true" in JS
    assert "b.note-a.note" in JS  # meilleurs candidats en haut
    assert "apex-short-valide" in JS and "apex-gi-valide" in GI and "apex-short-valide" not in GI
    assert "Math.floor((n-gsSeuil())/GS_PALIER)" in JS
    assert "mise*5" in JS
    assert _montant(69) is None
    assert _montant(70) == 100
    assert _montant(93) == 100
    assert _montant(94) == 120
    assert _montant(118) == 140
    assert _montant(142) == 160
    assert _montant(166) == 180
    assert _montant(190) == 200
    assert _montant(250) == 200


def test_presentation():
    assert "Meilleurs short" in JS
    assert "/250" in JS or "/${it.scale||250}" in JS
    assert "Le short peut faire perdre plus que la mise" not in JS
    assert "Mise (levier ×5)" in JS
    assert "Validés (${nVal})" in JS
    assert "gs-elliott" in JS and "gs-pattern" in JS and "gs-valid" in JS
    assert "/*__GSJS__*/" in TPL and "bestShortCard" in TPL and "gsInit" in TPL
    assert "gsOn" in POS and "gsListIsOpen" in POS


def test_regles_short_grille():
    s = CFG["apex_short"]
    g = s["grille"]
    assert s["seuil"] == 70 and s["macd_pct"] == 4.0
    assert g["rsi"]["max"] == 25 and g["macd"]["max"] == 25 and g["cci"]["max"] == 25
    assert g["fondamental"]["max"] == 100 and g["fear_greed"]["max"] == 30 and g["hype"]["max"] == 20  # t686u : fond tolérant 10..100
    assert g["fibonacci"]["max"] == 0
    assert g["mm40"]["max"] == 30
    assert g["valorisation"]["max"] == 30
    # t686u : barème théorique 285 (fond 100 + MM40 30 + valorisation 30…), total affiché borné à 250
    assert sum(g[k]["max"] for k in ("rsi", "macd", "cci", "fondamental", "fear_greed", "hype", "mm40", "valorisation")) == 285
    # MM40 inversée s'ajoute, le total affiché reste borné à 250
    assert "MM40" in (s.get("total") or "")
    assert "marge commune Revolut" in s["avertissement"]
    assert "function rgShortGrid" in RG and "rg-table-short-grille" in RG


def test_calcul_short():
    import build_short250 as S
    assert S.fg_short(17.7) == -18 and S.fg_short(50) == 0 and S.fg_short(100) == 30 and S.fg_short(0) == -30 and S.fg_short(65) == 6
    assert S.h_short(100) == 20 and S.h_short(0) == -20 and S.h_short(48.3) == -1 and S.h_short(50) == 0 and S.h_short(None) is None
    assert S.mise(69) is None and S.mise(70) == 100 and S.mise(190) == 200 and S.mise(250) == 200
    assert S.streak([80, 60, 71, 72, 73, 75], lambda v: v > 70) == 4
    pts, ko, nc, _ = S.fond_from([{"ok": False}, {"ok": True}, {"ok": None, "manquant": True}], "manquant")
    assert (pts, ko, nc) == (25, 1, 1)  # t686u : base 10 + 10 (non rempli) + 5 (n.c.)
    assert S.fond_from([{"ok": False}] * 9, "manquant")[0] == 100
    assert S.fond_from([{"ok": True}] * 9, "manquant")[0] == 10  # société saine : plancher 10
    assert S.fond_from([{"ok": None}], "manquant")[0] == 15


def test_donnees_short():
    d = json.loads((ROOT / "data" / "apex_short.json").read_text(encoding="utf-8"))
    assert d["n"] >= 10
    for r in d["by_tv"].values():
        assert r["categorie"] in ("action", "banque", "energie")
        assert -50 <= r["note"] <= 250 and isinstance(r["note"], int)
        p = r["points"]
        assert p["rsi"] in (0, 10, 25) and p["macd"] in (0, 10, 25) and p["cci"] in (0, 10, 25)
        assert 0 <= p["fondamental"] <= 125 and isinstance(p["fondamental"], int)
        if r["liste"]:
            assert r["fibo_ok"] and r["note"] >= d.get("seuil_liste", 70) and r["tech_ok"]
            assert max(p["rsi"], p["macd"], p["cci"]) >= 10
    assert CFG["apex_short"]["signal_tech_min"] == 1
    assert "tech_ok===false" in JS and "signal_tech" in RG


def test_notes_apex_inchangees():
    """La note SHORT ne réécrit pas les notes LONG / APEX déjà publiées."""
    data = json.loads((ROOT / "data" / "crypto_fiches.json").read_text(encoding="utf-8"))
    want = {"btc": 153, "eth": 173, "sol": 137, "mstr": 143}
    for a in data["assets"]:
        rec = a.get("apex10") or {}
        if a.get("key") in want:
            assert rec.get("note") == want[a["key"]]
            assert rec.get("scale") == 250
