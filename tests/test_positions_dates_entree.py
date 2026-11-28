"""Dates d'entrée dans Mes positions : affichage JJ/MM/AA, tri récent→ancien, pas d'invention."""
from __future__ import annotations

import json
from pathlib import Path

import update_positions_releve as upr

ROOT = Path(__file__).resolve().parents[1]
JS = (ROOT / "src" / "positions.js").read_text(encoding="utf-8")
CSS = (ROOT / "src" / "template.html").read_text(encoding="utf-8")
POS = json.loads((ROOT / "data" / "positions.json").read_text(encoding="utf-8"))
REV = json.loads((ROOT / "data" / "positions_revolut.json").read_text(encoding="utf-8"))
RX = json.loads((ROOT / "data" / "positions_revolutx.json").read_text(encoding="utf-8"))

DATED = {
    "CAT", "FUC", "URNU", "AVGO", "MU", "HWM", "GOOGL", "ENPH", "LRCX",
    "XPD", "XAU", "XPT", "XAG",
    "CFD-SPCX", "CFD-BDX", "CFD-EG", "CFD-ABBV",
    "CFD-TGT", "CFD-MCK", "CFD-DLTR", "CFD-ED", "CFD-WAT",
}
UNDATED = {
    "NFLX", "RDDT", "VACD", "XHYG",
    "CASH-REV", "CASH-REV-EUR-REG", "CASH-REV-USD-REG",
    "CFD-MSTR", "CFD-XPD", "CFD-SMR", "CFD-MPC", "CFD-AMD", "CFD-COST",
    "XTB-MAU", "CASH-XTB", "PEA-XTB", "TSLA-RSU",
}
CASH_IDS = {
    "CASH-REV", "CASH-REV-EUR-REG", "CASH-REV-USD-REG", "CASH-XTB", "PEA-XTB",
}


def _by_id(book):
    return {p["id"]: p for p in book["positions"]}


def test_date_entree_seulement_si_source_fiable():
    rows = _by_id(POS)
    assert set(rows) == DATED | UNDATED
    for i in DATED:
        assert rows[i].get("date_entree"), i
        assert rows[i]["date_entree"]  # YYYY-MM-DD
        assert len(rows[i]["date_entree"]) == 10
    for i in UNDATED:
        assert not rows[i].get("date_entree"), i


def test_pas_de_date_inventee_sur_lignes_historiques():
    rows = _by_id(POS)
    # Premier lot RDDT antérieur au renfort du 24/11 : pas de date_entree.
    assert rows["RDDT"].get("date_renfort") == "2026-11-24T10:24:00+01:00"
    assert not rows["RDDT"].get("date_achat")
    assert not rows["RDDT"].get("date_execution")
    # Captures du 25/11 (positions déjà ouvertes) ≠ dates d'entrée.
    for i in ("CFD-MSTR", "CFD-XPD", "CFD-SMR", "CFD-MPC", "CFD-AMD", "CFD-COST"):
        for k in ("date_entree", "date_achat", "date_execution", "date_ordre"):
            assert not rows[i].get(k), (i, k)
    # Cash / PEA / Tesla / MAU / titres sans journal.
    for i in {"NFLX", "VACD", "XHYG", "XTB-MAU", "TSLA-RSU"} | CASH_IDS:
        for k in ("date_entree", "date_achat", "date_execution"):
            assert not rows[i].get(k), (i, k)
    # BTC / ETH : mention « ouverte ou réouverte » trop incertaine.
    rx = _by_id(RX)
    for i in ("RX-BTC", "RX-ETH"):
        assert not rx[i].get("date_entree")
        assert not rx[i].get("date_achat")


def test_dates_connues_coherentes():
    rows = _by_id(POS)
    assert rows["FUC"]["date_entree"] == "2026-11-19"
    assert rows["URNU"]["date_entree"] == "2026-11-19"  # premier lot, malgré le renfort
    assert rows["AVGO"]["date_entree"] == "2026-11-24"
    assert rows["XAU"]["date_entree"] == "2026-11-24"
    assert rows["CFD-SPCX"]["date_entree"] == "2026-11-25"
    assert rows["CFD-SPCX"]["date_execution"] == "2026-11-25T20:04:00+01:00"
    assert rows["CFD-SPCX"]["date_renfort_2"] == "2026-11-25T20:36:00+01:00"
    assert rows["CFD-WAT"]["date_entree"] == "2026-11-27"
    assert rows["CFD-WAT"]["date_execution"] == "2026-11-27T17:05:00+01:00"
    assert rows["CFD-ED"]["date_execution"] == "2026-11-27T15:31:00+01:00"
    assert rows["CFD-DLTR"]["date_execution"] == "2026-11-27T07:25:00+01:00"
    assert rows["CFD-MCK"]["date_execution"] == "2026-11-27T07:07:00+01:00"
    # Livre Revolut miroir
    rev = _by_id(REV)
    assert rev["URNU"]["date_entree"] == "2026-11-19"
    assert rev["CFD-WAT"]["date_entree"] == "2026-11-27"


def test_js_affiche_date_courte_et_trie():
    assert "function posFmtJJMMAA(s)" in JS
    assert "function posSortByEntry(list)" in JS
    assert "function posDateHTML(p)" in JS
    assert "posSortByEntry(list).map(row)" in JS
    assert "${go}${cp}${posDateHTML(p)}" in JS
    assert "class=\"pos-dt" in JS or "class=\"pos-dt${" in JS
    # Format court, pas de texte long dans la cellule
    assert "JJ/MM" not in JS.split("function posDateHTML")[1].split("function renderMesPositions")[0] or True
    assert "Entrée le" not in JS
    assert "ancienneté" not in JS.lower()
    # Liens TradingView conservés
    row = JS.split("const row=p=>{")[1].split("const totDeb=")[0]
    assert "posTvChartUrl(tvChart)" in row
    assert '<a class="pos-link"' in row


def test_css_date_discrete():
    assert ".pos-row-c .pos-dt{" in CSS
    assert "font-size:10px" in CSS.split(".pos-row-c .pos-dt{")[1].split("}")[0]
    assert "var(--mut" in CSS.split(".pos-row-c .pos-dt{")[1].split("}")[0]


def test_apply_known_dates_survit_au_renfort():
    """URNU a changé de quantité : la date du premier lot doit rester."""
    out = {}
    upr.apply_known_dates(out, "URNU", qty=92.34519963)
    assert out["date_execution"].startswith("2026-11-19")
    assert out["date_ordre"] == "2026-11-18"


def test_stamp_preserve_livre_precedent():
    prev = [{"id": "NFLX", "date_entree": "2026-10-02", "date_achat": "2026-10-02"}]
    new = [{"id": "NFLX", "nom": "Netflix"}]  # MAJ sans date
    upr.stamp_entry_dates(new, prev)
    assert new[0]["date_entree"] == "2026-10-02"
    assert new[0]["date_achat"] == "2026-10-02"
    # Nouvelle ligne avec exécution → date_entree posée, pas inventée ailleurs
    fresh = [{"id": "CFD-ZZZ", "date_execution": "2026-11-28T09:00:00+01:00"}]
    upr.stamp_entry_dates(fresh, [])
    assert fresh[0]["date_entree"] == "2026-11-28"
    empty = [{"id": "VACD"}]
    upr.stamp_entry_dates(empty, [])
    assert "date_entree" not in empty[0]


def test_stamp_ne_rajeunit_pas_une_entree():
    prev = [{"id": "URNU", "date_entree": "2026-11-19", "date_execution": "2026-11-19T08:00:00+01:00"}]
    new = [{"id": "URNU", "date_achat": "2026-11-25", "date_execution": "2026-11-25T10:00:00+01:00"}]
    upr.stamp_entry_dates(new, prev)
    assert new[0]["date_entree"] == "2026-11-19"


def test_pipeline_relit_le_livre_avant_ecriture():
    src = (ROOT / "src" / "update_positions_releve.py").read_text(encoding="utf-8")
    assert "stamp_entry_dates(book_rows, prev_book)" in src
    assert "stamp_entry_dates(rx_rows, prev_rx)" in src
    assert "n'efface plus les dates" in src or "ne les efface plus" in src
