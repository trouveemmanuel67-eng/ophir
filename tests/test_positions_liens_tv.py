"""Liens TradingView du layout APEX depuis Mes positions."""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
JS = (ROOT / "src" / "positions.js").read_text(encoding="utf-8")
CSS = (ROOT / "src" / "template.html").read_text(encoding="utf-8")

LAYOUT = "https://www.tradingview.com/chart/lGi0h59c/?symbol="


def test_helpers_et_url_layout():
    assert "function posTvChartSymbol(p)" in JS
    assert "function posTvChartUrl(sym)" in JS
    assert "lGi0h59c" in JS
    assert "encodeURIComponent(sym)" in JS
    assert LAYOUT.split("?")[0] in JS
    assert "BITSTAMP:BTCUSD" in JS
    assert "BITSTAMP:ETHUSD" in JS
    assert "TVC:GOLD" in JS
    assert "NYSE:WAT" in JS
    assert "NYSE:ED" in JS
    assert "NASDAQ:DLTR" in JS


def test_ticker_est_un_lien_nouvel_onglet():
    row = JS.split("const row=p=>{")[1].split("const totDeb=")[0]
    assert "posTvChartSymbol(p)" in row
    assert "posTvChartUrl(tvChart)" in row
    assert 'target="_blank"' in row
    assert 'rel="noopener"' in row
    assert '<a class="pos-link"' in row
    assert "${go}${cp}" in row
    assert "TradingView" not in row  # pas de texte visible en plus
    assert "posOpenFiche(b.dataset.tab" not in JS.split("function renderMesPositions")[1]


def test_css_lien_reste_blanc():
    assert ".pos-row-c a.pos-link:link,.pos-row-c a.pos-link:visited{color:#fff}" in CSS


def test_symboles_positions_actives():
    start = JS.index("function posTvBare")
    end = JS.index("function posTvCopy")
    chunk = JS[start:end]
    keys = ("ticker", "type", "tab", "sous_jacent", "fiche_tv", "tv_note", "tv", "reglement", "statut")
    def slim(p):
        return {k: p.get(k) for k in keys}
    pos = json.loads((ROOT / "data" / "positions.json").read_text(encoding="utf-8"))
    rx = json.loads((ROOT / "data" / "positions_revolutx.json").read_text(encoding="utf-8"))
    rows = [slim(p) for p in pos.get("positions", []) if p.get("statut") in ("active", "en_attente")]
    rows += [slim(p) for p in rx.get("positions", []) if p.get("statut") in ("active", "en_attente")]
    payload = json.dumps(rows, ensure_ascii=False)
    script = chunk + """
const rows = JSON.parse(process.argv[1]);
const out = rows.map(p => ({
  ticker: p.ticker,
  type: p.type || null,
  fiche_tv: p.fiche_tv || null,
  tv_note: p.tv_note || null,
  symbol: posTvChartSymbol(p),
  url: posTvChartUrl(posTvChartSymbol(p))
}));
process.stdout.write(JSON.stringify(out));
"""
    r = subprocess.run(
        ["node", "-e", script, payload],
        capture_output=True,
        text=True,
        check=False,
    )
    assert r.returncode == 0, r.stderr or r.stdout
    out = json.loads(r.stdout)
    by = {x["ticker"]: x for x in out}

    expected = {
        "BTC": "BITSTAMP:BTCUSD",
        "ETH": "BITSTAMP:ETHUSD",
        "XAU": "TVC:GOLD",
        "WAT-CFD": "NYSE:WAT",
        "ED-CFD": "NYSE:ED",
        "DLTR-CFD": "NASDAQ:DLTR",
        "TGT-CFD": "NYSE:TGT",
        "FUC": "XETR:FUC",  # note TV sur Francfort, pas TSE:6954
        "VACD": "EURONEXT:VK",
        "TSLA-RSU": "NASDAQ:TSLA",
    }
    for tk, sym in expected.items():
        assert tk in by, f"{tk} absent des positions testées"
        assert by[tk]["symbol"] == sym, f"{tk}: {by[tk]['symbol']} != {sym}"
        assert by[tk]["url"] == LAYOUT + sym.replace(":", "%3A")

    cash = [x for x in out if (x["ticker"] or "").startswith("CASH") or x["ticker"] == "PEA"]
    assert cash, "les lignes cash devraient être dans l'échantillon"
    for x in cash:
        assert x["symbol"] == ""
        assert x["url"] == ""

    linked = [x for x in out if x["symbol"]]
    assert len(linked) >= 36
    for x in linked:
        assert x["url"].startswith(LAYOUT)
        assert "%3A" in x["url"]
        assert ":" not in x["url"].split("symbol=")[1]
