"""Lignes Crypto compactes, univers BTC / ETH / SOL / MSTR."""
from __future__ import annotations
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_titre_et_sources_sans_mention_retiree():
    js = (ROOT / "src" / "tabs.js").read_text(encoding="utf-8")
    assert "BTC, ETH, SOL et MSTR · notes APEX" in js
    assert "Bitcoin, Ether, Solana et Strategy" in js
    fiche = js.split("function cxFichesHTML")[1].split("function renderCrypto")[0]
    assert "function cxApexAssets" not in js


def test_ligne_compacte_sans_liq_visible_ni_peur_euphorie():
    js = (ROOT / "src" / "tabs.js").read_text(encoding="utf-8")
    tile = js.split("function cxTile")[1].split("function cxCharts")[0]
    assert "listApexBar" in tile and "forceApex250" in tile
    assert "srCells" not in tile
    assert "cxLiqLine(s)" not in tile
    assert "cxLiqTitle" in tile and "cxLiqBox" in tile
    assert "dualBar(" not in tile
    css = (ROOT / "src" / "template.html").read_text(encoding="utf-8")
    assert "#cxFiches .cx-liq-line{display:none}" in css
    assert "srHead('Actif',100)" not in js and 'srHead("Actif",100)' not in js
    assert "srHead('Actif')" in js or 'srHead("Actif")' in js


def test_gi_recherche_accueil_moyenne_sans_filtre_legacy():
    for rel in ("src/good_invest.js", "src/recherche.js", "src/accueil.js", "src/achatvente.js"):
        txt = (ROOT / rel).read_text(encoding="utf-8")
        assert "cxApexAssets" not in txt


def test_data_cx_reste_index_dans_la_liste_complete():
    js = (ROOT / "src" / "tabs.js").read_text(encoding="utf-8")
    fiche = js.split("function cxFichesHTML")[1].split("function renderCrypto")[0]
    assert "all.indexOf(s)" in fiche
    charts = js.split("function cxCharts")[1].split("function cxFichesHTML")[0]
    assert "F.assets[+det.dataset.cx]" in charts


def test_fiches_et_panier_univers_courant():
    data = json.loads((ROOT / "data" / "crypto_fiches.json").read_text(encoding="utf-8"))
    keys = [a.get("key") for a in data.get("assets") or []]
    assert keys == ["btc", "eth", "sol", "mstr"]
    assert data.get("apex10", {}).get("n_moy") == 4
    tabs = json.loads((ROOT / "data" / "tabs_data.json").read_text(encoding="utf-8"))
    tkeys = [a.get("key") for a in ((tabs.get("crypto") or {}).get("fiches") or {}).get("assets") or []]
    assert tkeys == ["btc", "eth", "sol", "mstr"]
    top = ((tabs.get("crypto") or {}).get("global") or {}).get("top") or []
    known = {"btc", "eth", "usdt", "bnb", "usdc", "sol", "trx", "ada", "doge", "ton", "avax"}
    assert all(str(row[0]).lower() in known for row in top)
