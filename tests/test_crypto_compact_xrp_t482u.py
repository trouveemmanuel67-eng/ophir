"""t482u : lignes Crypto compactes (échelle /100) et XRP retiré d'APEX."""
from __future__ import annotations
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_titre_sans_xrp_et_filtre():
    js = (ROOT / "src" / "tabs.js").read_text(encoding="utf-8")
    assert "BTC, ETH, SOL et MSTR · notes APEX" in js
    assert "BTC, ETH, XRP, SOL et MSTR · notes APEX" not in js
    assert "Bitcoin, Ether, Solana et Strategy" in js
    assert "function cxIsXrp" in js and "function cxApexAssets" in js
    fiche = js.split("function cxFichesHTML")[1].split("function renderCrypto")[0]
    assert "cxApexAssets(all)" in fiche
    assert "XRP, Solana" not in fiche


def test_ligne_compacte_sans_liq_visible_ni_peur_euphorie():
    js = (ROOT / "src" / "tabs.js").read_text(encoding="utf-8")
    tile = js.split("function cxTile")[1].split("function cxCharts")[0]
    assert "dualBarApex100" in tile
    assert "srCells" not in tile
    assert "cxLiqLine(s)" not in tile
    assert "cxLiqTitle" in tile and "cxLiqBox" in tile
    assert "dualBar(" not in tile
    css = (ROOT / "src" / "template.html").read_text(encoding="utf-8")
    assert "#cxFiches .cx-liq-line{display:none}" in css
    assert "srHead('Actif',100)" in js or 'srHead("Actif",100)' in js


def test_xrp_filtre_gi_recherche_accueil_moyenne():
    gi = (ROOT / "src" / "good_invest.js").read_text(encoding="utf-8")
    assert "cxApexAssets" in gi
    rech = (ROOT / "src" / "recherche.js").read_text(encoding="utf-8")
    assert "cxApexAssets" in rech
    acc = (ROOT / "src" / "accueil.js").read_text(encoding="utf-8")
    assert "cxApexAssets" in acc
    av = (ROOT / "src" / "achatvente.js").read_text(encoding="utf-8")
    items = av.split("function sectionApexItems")[1].split("function bakedSectionApex")[0]
    assert "cxApexAssets" in items
    baked = av.split("function bakedSectionApex")[1].split("function apexV2FromAvg")[0]
    assert "hasXrp" in baked


def test_data_cx_reste_index_dans_la_liste_complete():
    js = (ROOT / "src" / "tabs.js").read_text(encoding="utf-8")
    fiche = js.split("function cxFichesHTML")[1].split("function renderCrypto")[0]
    assert "all.indexOf(s)" in fiche
    charts = js.split("function cxCharts")[1].split("function cxFichesHTML")[0]
    assert "F.assets[+det.dataset.cx]" in charts
