"""t452u : relevé courtier du 24/11/2026, ordres en cours = positions actives."""
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
        "ENPH", "PKX", "US912810TR95", "US912810SA79", "US91086QAV05",
        "US260543BJ10", "US105756BB58", "BTC",
    }
    have = {p["ticker"] for p in POS["positions"]} | {p["ticker"] for p in RV["positions"]} | {p["ticker"] for p in RX["positions"]}
    assert gone.isdisjoint(have)
    assert all(p.get("courtier") != "xtb" or p["ticker"] in {"MAU", "PEA"} for p in POS["positions"])


def test_lignes_du_releve_et_ordres():
    by = {(p["ticker"], p["statut"]): p for p in POS["positions"]}
    assert by[("NFLX", "active")]["valeur"] == 1059.98
    assert by[("CAT", "en_attente")]["valeur"] == 749.09
    assert by[("CAT", "en_attente")]["pnl_pct"] == 0
    assert by[("BKNG", "en_attente")]["valeur"] == 577.44
    assert by[("AVGO", "en_attente")]["valeur"] == 543.48
    assert by[("RDDT", "active")]["valeur"] == 232.29
    assert by[("RDDT", "en_attente")]["valeur"] == 815.14
    assert by[("CASH", "active")]["valeur"] == 1388.4
    assert by[("CASH", "active")]["tab"] == "liquidites"
    assert by[("XAU", "active")]["tab"] == "metaux"
    assert by[("XAU", "active")].get("date_achat") == "2026-11-24"
    assert by[("MAU", "active")]["fiche_tv"] == "EURONEXT:MAU"
    assert by[("MAU", "active")]["valeur"] == 522.45
    assert by[("PEA", "active")]["nom"] == "PEA XTB"
    assert POS["n_en_attente"] == 4
    assert {p["ticker"] for p in RX["positions"]} == {"ETH"}
    assert RX["positions"][0]["quantite"] == 0.28
    assert RX["positions"][0]["valeur"] == 478.24
    # CFD absents des listes
    assert all(p.get("type") != "cfd" for p in POS["positions"] + RV["positions"])
    assert "CFD Revolut" in (POS.get("cfd_alerte") or {}).get("libelle", "")
    assert "−7 800" in POS["cfd_alerte"]["libelle"]


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
    src = ROOT / "data" / "revolut" / "releve_courtiers_2026-11-24.json"
    assert src.exists()
    rel = json.loads(src.read_text())
    assert rel["date"] == "2026-11-24"
    assert (ROOT / "src" / "update_positions_releve.py").exists()
