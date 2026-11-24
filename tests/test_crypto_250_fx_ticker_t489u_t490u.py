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
    want = {"btc": 153, "eth": 173, "sol": 137, "mstr": 143}
    for a in data["assets"]:
        rec = a.get("apex10") or {}
        assert rec.get("scale") == 250
        assert rec.get("total_max") == 250
        if a["key"] in want:
            assert rec.get("note") == want[a["key"]], a["key"]
            pts = (rec.get("decomp") or {}).get("points") or {}
            assert pts.get("hype") is not None
            assert "Hype" in (rec.get("ligne") or "") or "HYPE" in (rec.get("ligne") or "")
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
    # APE-25 : la note devise passe sur −50..250
    assert "forceApex250" in bar and "fx250" in bar
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
        assert rec.get("scale") == 250 and -50 <= rec.get("note") <= 250


def test_etf_par_devise_t492u():
    js = (ROOT / "src" / "tabs.js").read_text(encoding="utf-8")
    assert "function fxEtfRow" in js
    row = js.split("function fxEtfRow")[1].split("function fxCard")[0]
    assert "forceApex250" in row
    assert "ophirCopyBtn(tv)" in row
    assert "3 ans ann." in row
    assert "données 3 ans annualisées insuffisantes" in row
    data = json.loads((ROOT / "data" / "liquidites_etf_devises.json").read_text(encoding="utf-8"))
    by = {a["ccy"]: a for a in data["assets"]}
    assert by["AUD"]["tv"] == "ASX:SEMI" and by["AUD"]["perf_kind"] == "total_return_annualise_3ans"
    assert by["USD"]["tv"] == "NASDAQ:RING" and by["USD"]["apex10"]["scale"] == 250
    assert by["CAD"]["tv"] == "TSX:XCHP"
    assert by["GBP"]["tv"] == "LSE:AUCP" and by["GBP"]["isin"] == "IE00B3CNHG25"
    assert by["JPY"]["tv"] == "TSE:1631"
    assert by["CHF"]["tv"] == "SIX:AUCO" and by["CHF"]["isin"] == "IE00B3CNHG25"
    assert by["KRW"]["ok"] is False and not by["KRW"].get("tv")
    for ccy in ("AUD", "USD", "CAD", "GBP", "JPY", "CHF"):
        rec = by[ccy]["apex10"]
        assert rec["scale"] == 250
        assert rec["decomp"]["points"]["hype"] is None
        assert rec["decomp"]["points"]["fondamental"] is None
        assert rec["note"] < 130
        assert by[ccy]["perf_3y_ann"] is not None
        # exclus du lot 1 an : pétrole, fret, classe SMI trop jeune
        assert by[ccy]["tv"] not in ("ASX:OOO", "AMEX:BWET", "SIX:SMIA")
    rg = (ROOT / "src" / "regles.js").read_text(encoding="utf-8")
    assert "function rgLiquiditesEtfGrid" in rg
    assert "rg-table-liquidites-etf" in rg
    assert "annualisée sur 3 ans" in rg
    assert "annualisée sur 3 ans" in (ROOT / "config" / "regles.json").read_text(encoding="utf-8")
