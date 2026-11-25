"""t452u / t545u : pointage Revolut du 25/11/2026 (08 h 15) ; plus d'ordre en attente."""
from __future__ import annotations
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
POS = json.loads((ROOT / "data" / "positions.json").read_text())
RV = json.loads((ROOT / "data" / "positions_revolut.json").read_text())
RX = json.loads((ROOT / "data" / "positions_revolutx.json").read_text())
JS = (ROOT / "src" / "positions.js").read_text()
ACC = (ROOT / "src" / "accueil.js").read_text()
CSS = (ROOT / "src" / "template.html").read_text()


def tickers(rows, courtier=None):
    return {(p["ticker"], p.get("statut")) for p in rows if courtier is None or p.get("courtier") == courtier}


def test_anciennes_lignes_retirees():
    gone = {
        "NKE", "STLA", "AGNC", "NLY", "PDSE", "MBG", "PAH3", "P911",
        "PKX", "US912810TR95", "US912810SA79", "US91086QAV05",
        "US260543BJ10", "US105756BB58", "BTC",
    }
    have = {p["ticker"] for p in POS["positions"]} | {p["ticker"] for p in RV["positions"]} | {p["ticker"] for p in RX["positions"]}
    assert gone.isdisjoint(have)
    assert all(p.get("courtier") != "xtb" or p["ticker"] in {"MAU", "PEA"} for p in POS["positions"])


def test_lignes_du_releve_et_ordres():
    by = {(p["ticker"], p["statut"]): p for p in POS["positions"]}
    assert by[("NFLX", "active")]["valeur"] == 1072.71
    assert by[("CAT", "active")]["valeur"] == 754.66
    assert by[("BKNG", "active")]["valeur"] == 589.5
    assert by[("AVGO", "active")]["valeur"] == 544.06
    assert by[("RDDT", "active")]["valeur"] == 1073.72
    assert by[("MU", "active")]["valeur"] == 533.89
    assert by[("HWM", "active")]["valeur"] == 539.31
    assert by[("GOOGL", "active")]["valeur"] == 545.6
    assert by[("ENPH", "active")]["valeur"] == 534.05
    assert by[("LRCX", "active")]["valeur"] == 524.08
    assert by[("CASH", "active")]["valeur"] == 5.5
    assert by[("CASH", "active")]["tab"] == "liquidites"
    assert by[("XAU", "active")]["tab"] == "metaux"
    assert by[("XAU", "active")].get("date_achat") == "2026-11-24"
    assert by[("MAU", "active")]["fiche_tv"] == "EURONEXT:MAU"
    assert by[("MAU", "active")]["valeur"] == 522.45
    assert by[("PEA", "active")]["nom"] == "PEA XTB"
    assert POS["n_en_attente"] == 0
    assert POS["n_actives"] == 26
    assert {p["ticker"] for p in RX["positions"]} == {"ETH"}
    assert RX["positions"][0]["quantite"] == 0.28
    assert RX["positions"][0]["valeur"] == 478.24
    assert "12 h 35" in RX["releve_libelle"]  # Revolut X non relu le 25/11 08 h 15
    # CFD absents des listes
    assert all(p.get("type") != "cfd" for p in POS["positions"] + RV["positions"])
    assert "CFD Revolut" in (POS.get("cfd_alerte") or {}).get("libelle", "")
    assert "P/L non relu" in POS["cfd_alerte"]["libelle"]
    assert POS["cfd_alerte"]["n"] == 4
    assert ("MC", "active") in by
    assert by[("MC", "active")]["valeur"] == 998.4
    assert by[("MC", "active")]["fiche_tv"] == "EURONEXT:MC"
    assert by[("MC", "active")]["pnl_pct"] == -0.16
    assert by[("NFLX", "active")]["pnl_pct"] == 0.75
    assert by[("MC", "active")]["rendement_pct"] == 3.29


def test_ordres_traites_comme_positions_actives_dans_le_js():
    assert "function posIsHeld" in JS
    assert "p.statut==='active'||p.statut==='en_attente'" in JS
    assert "p.statut==='active'||p.statut==='en_attente'" in ACC
    assert "pos-mark-ordre" in JS and "pos-mark-ordre" in CSS
    assert "pos-cfd-alert" in JS and "pos-cfd-alert" in CSS
    assert "19/11/2026 à 21 h" not in JS
    assert "XTB 23/11/2026 à 13 h 48" not in JS
    assert "st!=='active'&&st!=='en_attente'" in ACC
    # moyenne ETF / âge : les dates d'ordre d'achat comptent
    assert "date_achat||p.date_ouverture" in ACC


def test_source_dashboard_presente():
    src = ROOT / "data" / "revolut" / "releve_courtiers_2026-11-25.json"
    assert src.exists()
    rel = json.loads(src.read_text())
    assert rel["date"] == "2026-11-25"
    assert (ROOT / "src" / "update_positions_releve.py").exists()
