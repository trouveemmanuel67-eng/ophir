"""Notes APEX / SHORT affichées sur chaque ligne de Mes positions."""
from __future__ import annotations
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT)]

POS_JS = (ROOT / "src" / "positions.js").read_text(encoding="utf-8")
SHORT_JS = (ROOT / "src" / "best_short.js").read_text(encoding="utf-8")
BUILD = (ROOT / "src" / "build.py").read_text(encoding="utf-8")
POS = json.loads((ROOT / "data" / "positions.json").read_text(encoding="utf-8"))
PILOT = json.loads((ROOT / "data" / "apex_achat_v2_pilot.json").read_text(encoding="utf-8"))
SITE = json.loads((ROOT / "data" / "apex_achat_v2_site.json").read_text(encoding="utf-8"))
SHORT = json.loads((ROOT / "data" / "apex_short.json").read_text(encoding="utf-8"))
CRYPTO = json.loads((ROOT / "data" / "crypto_fiches.json").read_text(encoding="utf-8"))


def _pos(pid):
    rows = [p for p in POS["positions"] if p.get("id") == pid]
    assert rows, f"position {pid} absente"
    return rows[0]


def test_js_short_et_achat_separes():
    assert "function posTvKeys" in POS_JS
    assert "function posShortRec" in POS_JS
    assert "function posApexRec" in POS_JS
    assert "posBlocOf(p)==='short'" in POS_JS
    assert "kind:'short'" in POS_JS
    assert "Note SHORT" in POS_JS
    # plus de coupure qui masque la note crypto / SHORT sur un onglet actions
    assert "if(posIsEquity(p)) return '';" not in POS_JS
    assert "if(posIsEquity(p)) return '–';" not in POS_JS
    # Meilleurs SHORT : les notes tenues hors univers n'y entrent pas
    assert "!r.held_position" in SHORT_JS
    # le slim PILOT conserve les sous-jacents des CFD détenus (SMR, etc.)
    assert "if item.get('type') not in ('equity', 'cfd'):" in BUILD


def test_bdx_levier_x5():
    p = _pos("CFD-BDX")
    assert p["levier"] == 5
    assert p["cfd_badge"] == "CFD S x5"
    assert p["sens"] == "short"
    assert abs(p["quantite"] - 3.5) < 1e-9
    assert abs(p["prix_moyen"] - 222.56) < 1e-9


def test_notes_short_existantes():
    assert SHORT["by_tv"]["NYSE:BDX"]["note"] == 157
    assert SHORT["by_tv"]["NYSE:EG"]["note"] == 123
    assert SHORT["by_tv"]["NYSE:ABBV"]["note"] == 80
    # la note d'achat ABBV (61) ne doit pas être celle affichée en short
    assert PILOT["by_tv"]["NYSE:ABBV"]["total"] == 61
    assert SHORT["by_tv"]["NYSE:ABBV"]["note"] != PILOT["by_tv"]["NYSE:ABBV"]["total"]


def test_mstr_une_seule_note_crypto():
    mstr = next(a for a in CRYPTO["assets"] if a.get("sym") == "MSTR" or a.get("key") == "mstr")
    rec = mstr["apex10"]
    assert rec["note"] == 240
    assert rec["total"] == 240
    assert rec["total_max"] == 250
    # pas de seconde note Actions qui divergeraient
    assert "NASDAQ:MSTR" not in (PILOT.get("by_tv") or {})
    assert "NASDAQ:MSTR" not in (SITE.get("by_tv") or {})


def test_smr_note_achat_dans_pilot():
    rec = PILOT["by_tv"]["NYSE:SMR"]
    assert rec["ok"] is True
    assert rec["total_max"] == 250
    assert rec["total"] == 163
    assert rec["display"] == "163 / 250"
    assert rec["band"] == "vert"
    assert rec["regles"] == "apex_achat_v2"
    p = rec["points"]
    assert "elliott" not in p
    assert p == {
        "rsi": 9, "macd": 27, "fibonacci": 27, "cci": 18,
        "fondamental": 27, "fear_greed": 20, "hype": 5, "mm40": 30, "total": 163,
    }
    assert "Sentiment Énergie (XLE) 22 : +20" in rec["ligne"]
    assert "MM40 hebdo" in rec["ligne"]
    assert "→  163 / 250" in rec["ligne"] or "→ 163 / 250" in rec["ligne"]
    sent = rec["sentiment"]
    assert sent["cle"] == "us:XLE"
    assert sent["points"] == 20
    assert sent.get("repli_cnn") is False
    assert rec.get("hors_univers_position")
    site = json.loads((ROOT / "data" / "apex_achat_v2_site.json").read_text(encoding="utf-8"))
    assert site["by_tv"]["NYSE:SMR"]["total"] == 163


def test_mpc_note_short_hors_liste():
    rec = SHORT["by_tv"]["NYSE:MPC"]
    assert rec["held_position"] is True
    assert rec["univers"] == "held"
    assert rec["liste"] is False
    assert rec["mise"] is None
    assert isinstance(rec["note"], int)
    assert -50 <= rec["note"] <= 250
    assert "NYSE:MPC" not in SHORT["liste"]
    assert SHORT["n"] == 15
    assert "MM40 hebdo" in rec["ligne"]
    # sentiment maison, pas CNN
    sent = rec.get("sentiment") or {}
    assert sent.get("repli_cnn") is False or sent.get("cle") != "cnn"
