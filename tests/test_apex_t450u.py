"""t450u : CAT et le reste des top 10 US / top France sont notés /250."""
from __future__ import annotations
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORLD = (ROOT / "src" / "build_apex_achat_v2_world.py").read_text(encoding="utf-8")
FONDS = (ROOT / "src" / "fonds.js").read_text(encoding="utf-8")
PAYSJS = (ROOT / "src" / "pays.js").read_text(encoding="utf-8")


def test_collecte_top10_sans_changer_la_moyenne_etf():
    assert "list((sf.get('top') or [])[:10])" in WORLD
    assert "ETF_FOND_N = 5" in WORLD
    assert "avg_actions = actions[:ETF_FOND_N] or actions" in WORLD
    assert "list(fond.get('top') or [])" in WORLD
    assert "list((fond.get('top') or [])[:5])" not in WORLD
    assert "slice(0,10)" in FONDS
    assert "slice(0,5)" not in FONDS
    assert "slice();" in PAYSJS


def test_cat_et_top_manquants_notes():
    full = json.loads((ROOT / "data" / "apex_achat_v2_scores_full.json").read_text())
    bt = full["by_tv"]
    cat = bt["NYSE:CAT"]
    assert cat["ok"] is True
    assert cat["total"] == 170
    assert cat["total_max"] == 250 and cat["total_min"] == -50
    assert cat["points"] == {
        "rsi": 10, "macd": 30, "fibonacci": 10, "cci": 20,
        "fondamental": 70, "fear_greed": 30, "total": 170,
    }
    # notes déjà publiées inchangées (moyenne ETF et top 5)
    assert bt["XETR:ZPDF"]["total"] == 102
    assert bt["XETR:ZPDK"]["total"] == 140
    assert bt["NYSE:MA"]["total"] == 110
    xli = full["pilotes"]["XLI"]["actions"]
    assert len(xli) == 10
    assert {a["tv"] for a in xli} >= {
        "NYSE:HWM", "NASDAQ:ADP", "NYSE:UBER", "NYSE:CAT", "NASDAQ:CSX", "NYSE:ETN"
    }
    # 11 secteurs × 10 + France : tous les tops sont dans by_tv
    fond = json.loads((ROOT / "data" / "fondamentaux.json").read_text())
    pays = json.loads((ROOT / "data" / "pays.json").read_text())
    missing = []
    for sym, s in fond["sectors"].items():
        for it in s.get("top") or []:
            if it.get("tv") not in bt:
                missing.append(it.get("tv"))
    fr = next(c for c in pays["countries"] if c.get("nom") == "France")
    for row in fr["rows"]:
        for it in (row.get("fond") or {}).get("top") or []:
            if it.get("tv") not in bt:
                missing.append(it.get("tv"))
    assert missing == []
