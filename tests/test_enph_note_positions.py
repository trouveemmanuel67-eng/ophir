"""ENPH (Mes positions) : note APEX Actions /250 et accroche hors univers."""
from __future__ import annotations
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT)]

PILOT = json.loads((ROOT / "data" / "apex_achat_v2_pilot.json").read_text(encoding="utf-8"))
POS = json.loads((ROOT / "data" / "positions.json").read_text(encoding="utf-8"))
WORLD = (ROOT / "src" / "build_apex_achat_v2_world.py").read_text(encoding="utf-8")
HARM = (ROOT / "src" / "harmonise250.py").read_text(encoding="utf-8")
PILOT_PY = (ROOT / "src" / "build_apex_achat_v2_pilot.py").read_text(encoding="utf-8")
POS_JS = (ROOT / "src" / "positions.js").read_text(encoding="utf-8")


def _enph_pos():
    rows = [p for p in POS["positions"] if p.get("ticker") == "ENPH"]
    assert rows, "ENPH doit figurer dans Mes positions"
    return rows[0]


def test_mapping_positions_deja_correct():
    p = _enph_pos()
    assert p["type"] == "equity"
    assert p["tab"] == "energie"
    assert p.get("fiche_tv") == "NASDAQ:ENPH" or p.get("tv_note") == "NASDAQ:ENPH"
    assert p.get("note_tv_ok") is True


def test_cause_hors_univers_et_hook_permanent():
    # ENPH n'est pas dans un top secteur / pays : flag hors_univers_position
    rec = PILOT["by_tv"]["NASDAQ:ENPH"]
    assert rec.get("hors_univers_position")
    assert "hors univers" in rec["hors_univers_position"].lower()
    assert "score_held_equities" in WORLD and "score_missing" in WORLD
    assert "score_held_equities" in HARM and "score_missing" in HARM
    assert "short_cache" in PILOT_PY
    # Mes positions lit uniquement PILOT.by_tv pour une equity
    assert "function posPilotRec" in POS_JS
    assert "posIsEquity(p)" in POS_JS


def test_note_actions_enph():
    rec = PILOT["by_tv"]["NASDAQ:ENPH"]
    assert rec["ok"] is True
    assert rec["total_max"] == 250
    assert rec["total_min"] == -50
    assert rec["total"] == 146
    assert rec["display"] == "146 / 250"
    assert rec["band"] == "vert"
    assert rec["regles"] == "apex_achat_v2"
    p = rec["points"]
    assert "elliott" not in p
    # grille ×0,9 + F&G secteur + H contre-courant
    assert p == {
        "rsi": 9, "macd": 27, "fibonacci": 27, "cci": 18,
        "fondamental": 18, "fear_greed": 30, "hype": 17, "total": 146,
    }
    assert rec["ligne"].startswith("RSI +9 · MACD +27 · Fibo +27 · CCI +18 · Fond +18")
    assert "Sentiment Technologie (XLK) 19 : +30" in rec["ligne"]
    assert "H +17" in rec["ligne"]
    assert "→  146 / 250" in rec["ligne"] or "→ 146 / 250" in rec["ligne"]
    sent = rec["sentiment"]
    assert sent["cle"] == "us:XLK"
    assert sent["points"] == 30
    assert sent.get("repli_cnn") is False
    att = rec["attention"]
    assert att["valeur"] == 18.4
    assert att["H"] == 17
    assert att["trends"] == 5.4
    assert att["mentions"] == 0.0
    assert att["volume"] == 74.4
    assert att["persistance"] == 16.7
    # Fond : 2 critères (dette nette, liquidité) × 9
    fond = rec["fond"]
    assert fond["points"] == 18 and fond["max"] == 81
    ok_ids = {e["id"] for e in fond["elements"] if e["ok"]}
    assert ok_ids == {"dette_nette_ebitda", "ratio_liquidite_courante"}
    assert rec["date_cloture"] == "2026-11-20"


def test_held_hook_ne_reprise_pas_enph_deja_notee():
    import score_held_equities as HE
    miss = HE.missing_held(PILOT.get("by_tv") or {})
    assert all(a["tv"] != "NASDAQ:ENPH" for a in miss)
    # Si on retire ENPH de l'univers, le hook la revoit
    by = {k: v for k, v in (PILOT.get("by_tv") or {}).items() if k != "NASDAQ:ENPH"}
    miss = HE.missing_held(by)
    tvs = [a["tv"] for a in miss]
    assert "NASDAQ:ENPH" in tvs


def test_find_wk_enph():
    import build_apex_achat_v2_pilot as P
    path, used = P.find_wk(P.yahoo_cands("NASDAQ:ENPH", "ENPH", "ENPH"))
    assert path and used == "ENPH"
    assert path.endswith("ENPH.json")


def test_attention_universe_inclut_enph():
    import attention_apex as A
    u = A.universe()
    tvs = {x["tv"] for x in u}
    assert "NASDAQ:ENPH" in tvs
    rec = next(x for x in u if x["tv"] == "NASDAQ:ENPH")
    assert rec["term"] == "Enphase stock"
