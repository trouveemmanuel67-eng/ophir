"""t452u / t549u : captures 25/11 09 h 50 + CFD 10 h 14 (exposition, pas la marge)."""
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
        "US260543BJ10", "US105756BB58",
    }
    have = {p["ticker"] for p in POS["positions"]} | {p["ticker"] for p in RV["positions"]} | {p["ticker"] for p in RX["positions"]}
    assert gone.isdisjoint(have)
    assert all(p.get("courtier") != "xtb" or p["ticker"] in {"MAU", "PEA", "CASH-XTB"} for p in POS["positions"])


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
    assert by[("MAU", "active")]["valeur"] == 519.21
    assert by[("PEA", "active")]["nom"] == "ligne PEA non identifiée"
    assert POS["n_en_attente"] == 0
    assert POS["n_actives"] == 34
    assert {p["ticker"] for p in RX["positions"]} == {"BTC", "ETH"}
    eth=next(p for p in RX["positions"] if p["ticker"]=="ETH")
    btc=next(p for p in RX["positions"] if p["ticker"]=="BTC")
    assert eth["quantite"] == 0.28
    assert eth["valeur"] == 468.35
    assert btc["valeur"] == 1086.14
    assert btc["quantite"] == 0.018
    assert "09 h 50" in RX["releve_libelle"]
    # CFD : montant = exposition (quantité × cours), levier lu par ligne
    cfds = {p["ticker"]: p for p in POS["positions"] if p.get("type") == "cfd"}
    assert set(cfds) == {"XPD-CFD", "COST-CFD", "MSTR-CFD", "SMR-CFD", "MPC-CFD", "AMD-CFD"}
    assert cfds["MSTR-CFD"]["cfd_badge"] == "CFD L x5"
    assert cfds["XPD-CFD"]["cfd_badge"] == "CFD L x5"
    assert cfds["SMR-CFD"]["cfd_badge"] == "CFD L x7"
    assert cfds["MPC-CFD"]["cfd_badge"] == "CFD S x2"
    assert cfds["AMD-CFD"]["cfd_badge"] == "CFD S x3"
    assert cfds["COST-CFD"]["cfd_badge"] == "CFD S x5"
    assert cfds["MSTR-CFD"]["valeur"] == 5108.08
    assert cfds["MSTR-CFD"]["pnl_pct"] == -8.96
    assert cfds["XPD-CFD"]["valeur"] == 6362.19
    assert cfds["XPD-CFD"]["pnl_pct"] == -24.3
    assert cfds["SMR-CFD"]["valeur"] == 1897.67
    assert cfds["SMR-CFD"]["pnl_pct"] == -37.74
    assert cfds["MPC-CFD"]["valeur"] == 1066.44
    assert cfds["MPC-CFD"]["pnl_pct"] == -30.28
    assert cfds["AMD-CFD"]["valeur"] == 1039.54
    assert cfds["AMD-CFD"]["pnl_pct"] == -38.54
    assert cfds["COST-CFD"].get("a_confirmer") is False
    assert cfds["COST-CFD"]["valeur"] == 603.63
    assert cfds["COST-CFD"]["pnl_pct"] == -0.6
    assert cfds["COST-CFD"]["pnl_valeur"] == -3.58
    assert cfds["COST-CFD"]["quantite"] == 0.55
    assert cfds["COST-CFD"]["cours"] == 1097.51
    assert cfds["COST-CFD"]["marge_usd"] == 120.62
    assert cfds["COST-CFD"].get("pnl_relu") is True
    al = POS["cfd_alerte"]
    assert al["afficher_encadre"] is True
    assert al["valeur_usd"] == 2614.02
    assert al["exposition_usd"] == 16077.55
    assert al["n"] == 6
    assert "COST" in al["tickers"]
    assert al.get("a_confirmer") in (None, [], ())
    assert al["marge_maintenance_pct"] == 98
    assert al["seuil_fermeture_usd"] == 1336.40
    assert "2 614,02" in al["libelle"]
    assert "16 077,55" in al["libelle"]
    assert POS["totaux"]["courtiers"]["revolut"]["valeur_usd"] == 30709.57
    assert POS["totaux"]["courtiers"]["revolut"]["cfd_exposition_usd"] == 16077.55
    assert POS["totaux"]["total_usd"] == 46313.82
    assert POS["totaux"]["liquide_usd"] == 32850.02
    tes=next(x for x in POS["positions"] if x["ticker"]=="TSLA-RSU")
    assert tes["valeur"] == 12302.45
    assert tes["valeur_usd"] == 13463.8
    assert tes["non_liquide"] is True
    assert tes["rsu_badge"] == "RSU"
    assert tes.get("tab") in (None, "")
    assert tes.get("pnl_pct") is None
    assert "entete_detail" in POS["totaux"]
    assert "13 463,80" in POS["totaux"]["entete_detail"]
    fr = POS["frais_cfd"]
    assert fr["dernier_usd"] == 2.34
    assert fr["projection_usd"] == 70.2
    assert fr["projection_eur"] == 64.14
    assert fr["objectif_eur_mois"] == 20
    assert fr["depasse_objectif"] is True
    assert POS["totaux"]["tesla_plan"]["avantage_potentiel_eur"] == 12302.45
    assert POS["totaux"]["tesla_plan"]["non_liquide"] is True
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
    assert "function posFraisCfdHTML" in JS
    assert "${posCfdAlertHTML()}${posFraisCfdHTML()}" not in JS
    assert "FRAIS CFD" not in JS
    assert "pos-frais-bar" not in JS
    assert "dont Tesla non liquide" not in JS
    assert "pos-mark-rsu" in JS
    assert "rsu_badge" in JS and "pos-mark-rsu" in CSS
    assert "homeIsHorsSecteur" in ACC
    assert "pos-total-strip" not in JS
    assert "posAmt(T.total_eur" not in JS

    BDG = (ROOT / "src" / "budget.js").read_text()
    assert "function bdgInit" in BDG
    assert "à relever" in BDG
    assert "bdg-table" in BDG and "bdg-table" in CSS
    assert "Observé ce mois" in BDG
    assert "Projection mensuelle" in BDG
    assert "Objectif" in BDG
    assert "bdg-ovn-line" not in BDG and "bdg-ovn-line" not in CSS
    assert "max-width:1720px" in CSS
    assert "pos-frais-bar" not in BDG
    assert "FRAIS CFD" not in BDG
    assert "Frais trading" in BDG
    assert "Abonnement TradingView" in BDG
    assert "id:'bdg-tv'" in BDG or "id:\"bdg-tv\"" in BDG or "bdg-tv" in BDG
    assert "bdg-cat-courses" in BDG
    assert "Objectif atteint" in BDG
    assert 'id="bdg-wrap"' in CSS
    assert "function bdgSetOpen" in BDG
    bud = POS["budget"]
    assert bud["mois"] == "2026-11"
    assert bud["ovn"]["total_mois_usd"] == 2.34
    assert bud["ovn"]["projection_usd"] == 70.2
    assert any(abs(float(j["montant_usd"])) == 2.34 for j in bud["ovn"]["lignes_mois"])
    assert bud["trading"]["a_relever"] is True
    assert bud["trading"]["ordres"] == []
    tv = bud["tradingview"]
    assert tv["poste"] == "Abonnement TradingView"
    assert tv["montant_eur_mois"] == 15.54
    assert tv["montant_eur_an"] == 186.48
    assert tv["projection_eur"] == 15.54
    assert tv["projection_usd"] == 17.01
    assert tv["total_mois_usd"] is None
    assert tv["objectif"]["atteint"] is True
    assert tv["objectif"]["libelle"] == "Passer à Essential annuel"
    assert tv["objectif"]["date_atteint"] == "2026-11-25"
    assert tv["objectif"]["economie_eur_mois"] == 68.4
    assert tv["objectif"]["economie_eur_an"] == 820.8
    assert "Essential annuel Black Friday, 186,48 €/an prélevé le 6/12/2026 (Premium 83,94 €/mois résilié)" in tv["detail"]
    assert bud["total_observe_usd"] == 2.34
    assert bud["projection_usd"] == 87.21
    assert bud["projection_eur"] == 79.68
    cj = bud["compte_joint"]
    assert cj["titre"] == "Compte joint famille, octobre 2026"
    assert cj["periode"]["mois"] == "2026-10"
    assert cj["totaux"]["depenses_eur"] == 5389.33
    assert cj["totaux"]["revenus_eur"] == 876.6
    assert cj["totaux"]["reste_eur"] == -4512.73
    assert cj["totaux"]["virements_internes_sortants_eur"] == 3773.46
    assert cj["totaux"]["air_glow_pub_eur"] == 128.28
    glow = next(c for c in cj["categories"] if c["id"] == "air_glow_pub")
    assert glow["poste"] == "Air Glow, pub (pro)"
    assert glow["n_operations"] == 24
    assert glow["observe_eur"] == 128.28
    assert glow["compte_dans_total_depenses"] is False
    autres = next(c for c in cj["categories"] if c["id"] == "autres")
    assert autres["observe_eur"] == 386.58
    assert autres["n_operations"] == 5
    assert all(o["libelle"] != "Facebook" for o in autres["operations"])
    deblock = [o for c in cj["categories"] if c["id"]=="virements_internes" for o in c["operations"] if o["libelle"]=="Deblock"]
    assert len(deblock) == 2
    assert round(sum(o["montant_eur"] for o in deblock), 2) == 150.0
    assert not any("Facebook" in (a.get("sujet") or "") or "Deblock" in (a.get("sujet") or "") for a in (cj.get("operations_ambigues") or []))
    assert "Air Glow, pub (pro)" in BDG
    assert "bdg-joint-airglow" in BDG
    courses = next(c for c in cj["categories"] if c["id"] == "courses")
    assert courses["observe_eur"] == 984.83
    assert courses["sous_categories"][0]["id"] == "tickets_lidl"
    assert courses["sous_categories"][0]["statut"] == "a_venir"
    assert cj["tradingview_sur_le_releve"]["present_sur_le_releve"] is True
    assert cj["tradingview_sur_le_releve"]["total_eur"] == 83.94
    assert "Compte joint famille" in BDG
    assert "Tickets Lidl" in BDG
    assert "bdg-courses-sous" in BDG
    assert "bdg-hero" in BDG and "bdg-hero" in CSS
    assert "home-hero" in CSS
    assert (ROOT / "data" / "revolut" / "frais_trading_ordres.json").exists()
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
