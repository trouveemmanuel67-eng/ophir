"""t489u : note crypto −50..250 ; t490u : devises ticker + barre /100."""
from __future__ import annotations
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from apex.crypto_points import hype_points_45, HYPE_GRILLE  # noqa: E402


def test_hype_45_grille():
    assert hype_points_45(0) == 45 and hype_points_45(9) == 45
    assert hype_points_45(10) == 41 and hype_points_45(50) == 25
    assert hype_points_45(100) == 0 and hype_points_45(90) == 5
    assert hype_points_45(None) is None
    assert HYPE_GRILLE[0] == (0, 45) and HYPE_GRILLE[-1] == (100, 0)


def test_notes_crypto_echelle_250_sans_hype():
    data = json.loads((ROOT / "data" / "crypto_fiches.json").read_text(encoding="utf-8"))
    want = {"btc": 104, "eth": 120, "sol": 80, "mstr": 90}
    for a in data["assets"]:
        rec = a.get("apex10") or {}
        assert rec.get("scale") == 250
        assert rec.get("total_max") == 250
        if a["key"] in want:
            assert rec.get("note") == want[a["key"]], a["key"]
            pts = (rec.get("decomp") or {}).get("points") or {}
            assert pts.get("hype") is None
            assert "Hype non comptée" in (rec.get("ligne") or "")
        if a["key"] in ("sol", "mstr"):
            assert ((rec.get("decomp") or {}).get("liquidite") or {}).get("present") is False
            assert pts.get("liquidite") is None


def test_gi_js_crypto_130():
    gi = (ROOT / "src" / "good_invest.js").read_text(encoding="utf-8")
    assert "tab==='crypto'" in gi
    assert "GI_SEUIL_METAUX" in gi.split("function giSeuilOf")[1].split("function giNow")[0]


def test_fx_ticker_et_barre_100():
    js = (ROOT / "src" / "tabs.js").read_text(encoding="utf-8")
    card = js.split("function fxCard")[1].split("function fxDxyCard")[0]
    assert "fxTickerHTML" in card and "fxBarHTML" in card
    assert "ophirCopyBtn(tv)" in js.split("function fxTickerHTML")[1].split("function fxBarHTML")[0]
    bar = js.split("function fxBarHTML")[1].split("function fxEtfRow")[0]
    assert "forceApex100" in bar
    assert "forceApex250" not in bar
    tabs = json.loads((ROOT / "data" / "tabs_data.json").read_text(encoding="utf-8"))
    assets = (tabs.get("liquidites") or {}).get("fx") or {}
    got = {a["sym"]: a.get("tv") for a in assets.get("assets") or []}
    expect = {
        "USD": "FX:EURUSD", "JPY": "FX:EURJPY", "GBP": "FX:EURGBP",
        "CHF": "FX:EURCHF", "AUD": "FX:EURAUD", "CAD": "FX:EURCAD", "KRW": "FX:EURKRW",
    }
    assert got == expect
    for a in assets.get("assets") or []:
        rec = a.get("apex10") or {}
        assert rec.get("scale") in (None, 100) or rec.get("total_max") in (None, 100)
        assert rec.get("scale") != 250


def test_etf_par_devise_t491u():
    js = (ROOT / "src" / "tabs.js").read_text(encoding="utf-8")
    assert "function fxEtfRow" in js
    assert "forceApex250" in js.split("function fxEtfRow")[1].split("function fxCard")[0]
    assert "ophirCopyBtn(tv)" in js.split("function fxEtfRow")[1].split("function fxCard")[0]
    data = json.loads((ROOT / "data" / "liquidites_etf_devises.json").read_text(encoding="utf-8"))
    by = {a["ccy"]: a for a in data["assets"]}
    assert by["AUD"]["tv"] == "ASX:OOO" and by["AUD"]["apex10"]["note"] == 68
    assert by["USD"]["tv"] == "AMEX:BWET" and by["USD"]["apex10"]["scale"] == 250
    assert by["CAD"]["tv"] == "TSX:XEG"
    assert by["GBP"]["tv"] == "LSE:FLRK" and by["GBP"]["isin"] == "IE00BHZRR030"
    assert by["JPY"]["tv"] == "TSE:2837"
    assert by["CHF"]["tv"] == "SIX:SMIA"
    assert by["KRW"]["ok"] is False and not by["KRW"].get("tv")
    for ccy in ("AUD", "USD", "CAD", "GBP", "JPY", "CHF"):
        rec = by[ccy]["apex10"]
        assert rec["scale"] == 250
        assert rec["decomp"]["points"]["hype"] is None
        assert rec["decomp"]["points"]["fondamental"] is None
        assert rec["note"] < 130
    rg = (ROOT / "src" / "regles.js").read_text(encoding="utf-8")
    assert "function rgLiquiditesEtfGrid" in rg
    assert "rg-table-liquidites-etf" in rg
    assert "etf_par_devise" in (ROOT / "config" / "regles.json").read_text(encoding="utf-8")
