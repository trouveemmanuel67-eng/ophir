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
    assert set(cfds) == {"XPD-CFD", "COST-CFD", "MSTR-CFD", "SMR-CFD", "MPC-CFD", "AMD-CFD", "BDX-CFD", "EG-CFD", "ABBV-CFD", "SPCX-CFD"}
    assert cfds["MSTR-CFD"]["cfd_badge"] == "CFD L x6"
    assert cfds["MSTR-CFD"]["levier"] == 6
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
    assert cfds["BDX-CFD"]["cfd_badge"] == "CFD S x5"
    assert cfds["BDX-CFD"]["valeur"] == 778.96
    assert cfds["BDX-CFD"]["quantite"] == 3.5
    assert cfds["BDX-CFD"]["cours"] == 222.56
    assert cfds["BDX-CFD"]["marge_usd"] == 155.79
    assert cfds["BDX-CFD"]["sens"] == "short"
    assert cfds["BDX-CFD"]["tab"] == "actions"
    assert cfds["EG-CFD"]["cfd_badge"] == "CFD S x5"
    assert cfds["EG-CFD"]["valeur"] == 495.07
    assert cfds["EG-CFD"]["quantite"] == 1.14
    assert cfds["EG-CFD"]["cours"] == 434.27
    assert cfds["EG-CFD"]["marge_usd"] == 99.01
    assert cfds["EG-CFD"]["sens"] == "short"
    assert cfds["EG-CFD"]["tab"] == "actions"
    assert "frais_ouverture_usd" not in cfds["EG-CFD"]
    assert cfds["ABBV-CFD"]["cfd_badge"] == "CFD S x5"
    assert cfds["ABBV-CFD"]["valeur"] == 742.10
    assert cfds["ABBV-CFD"]["quantite"] == 2.5
    assert cfds["ABBV-CFD"]["cours"] == 296.84
    assert cfds["ABBV-CFD"]["marge_usd"] == 148.42
    assert cfds["ABBV-CFD"]["sens"] == "short"
    assert cfds["ABBV-CFD"]["tab"] == "actions"
    assert cfds["ABBV-CFD"]["frais_ouverture_usd"] == 1.86
    assert cfds["SPCX-CFD"]["cfd_badge"] == "CFD L x4"
    assert cfds["SPCX-CFD"]["valeur"] == 1076.95
    assert cfds["SPCX-CFD"]["investi"] == 1076.95
    assert cfds["SPCX-CFD"]["quantite"] == 8.5
    assert cfds["SPCX-CFD"]["cours"] == 126.70
    assert cfds["SPCX-CFD"]["prix_moyen"] == 126.70
    assert cfds["SPCX-CFD"]["marge_usd"] == 269.25
    assert cfds["SPCX-CFD"]["sens"] == "long"
    assert cfds["SPCX-CFD"]["tab"] == "actions"
    assert cfds["SPCX-CFD"]["levier"] == 4
    assert cfds["SPCX-CFD"]["pnl_valeur"] == 0.0
    assert cfds["SPCX-CFD"]["pnl_pct"] == 0.0
    assert cfds["SPCX-CFD"]["fiche_tv"] == "NASDAQ:SPCX"
    assert cfds["SPCX-CFD"]["apex_score"] is None
    assert cfds["SPCX-CFD"]["frais_ouverture_usd"] == 0.48
    al = POS["cfd_alerte"]
    assert al["afficher_encadre"] is True
    assert al["valeur_usd"] == 2614.02
    assert al["exposition_usd"] == 19170.63
    assert al["n"] == 10
    assert "COST" in al["tickers"] and "BDX" in al["tickers"] and "EG" in al["tickers"] and "ABBV" in al["tickers"] and "SPCX" in al["tickers"]
    assert al.get("a_confirmer") in (None, [], ())
    assert al["marge_maintenance_pct"] == 98
    assert al["seuil_fermeture_usd"] == 1336.40
    assert "2 614,02" in al["libelle"]
    assert "19 170,63" in al["libelle"]
    assert POS["totaux"]["courtiers"]["revolut"]["valeur_usd"] == 34479.48
    assert POS["totaux"]["courtiers"]["revolut"]["cfd_exposition_usd"] == 19170.63
    assert POS["totaux"]["total_usd"] == 50083.73
    assert POS["totaux"]["liquide_usd"] == 36619.93
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
    assert ("MC", "active") not in by
    assert ("BKNG", "active") not in by
    assert ("PPX", "active") not in by
    assert ("HMI", "active") not in by
    assert ("DASH", "active") not in by
    assert ("XUTL", "active") not in by
    assert by[("NFLX", "active")]["pnl_pct"] == 0.75
    assert by[("URNU", "active")]["quantite"] == 92.34519963
    assert by[("URNU", "active")]["prix_moyen"] == 14.69
    assert by[("URNU", "active")]["valeur"] == 1272.52
    assert by[("URNU", "active")]["pnl_valeur"] == -83.63
    assert by[("CASH-EUR-REG", "active")]["valeur"] == 2569.08
    assert by[("CASH-USD-REG", "active")]["valeur"] == 1112.72
    ventes = POS["ventes_2026_11_25"]
    assert ventes["totaux"]["pnl_realise_usd"] == -19.29
    assert ventes["totaux"]["pnl_realise_eur"] == -17.62
    assert ventes["totaux"]["n"] == 6


def test_ordres_traites_comme_positions_actives_dans_le_js():
    assert "function posBlocOf" in JS
    assert "data-pos-bloc" in JS
    assert "function posVentesHTML" in JS
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
    assert bud["trading"]["a_relever"] is False
    assert len(bud["trading"]["ordres"]) == 9
    assert bud["trading"]["total_mois_usd"] == 10.85
    assert bud["trading"]["total_mois_eur"] == 9.91
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
    assert bud["total_observe_usd"] == 13.19
    assert bud["projection_usd"] == 98.06
    assert bud["projection_eur"] == 89.59
    cj = bud["compte_joint"]
    assert cj["titre"] == "Compte joint famille, octobre 2026"
    assert cj["periode"]["mois"] == "2026-10"
    assert cj["totaux"]["depenses_eur"] == 4909.86
    assert cj["totaux"]["revenus_eur"] == 876.6
    assert cj["totaux"]["reste_eur"] == -4033.26
    assert cj["totaux"]["virements_internes_sortants_eur"] == 3773.46
    assert cj["totaux"]["air_glow_pub_eur"] == 607.75
    glow = next(c for c in cj["categories"] if c["id"] == "air_glow")
    assert glow["poste"] == "Air Glow, frais de fonctionnement"
    assert glow["n_operations"] == 30
    assert glow["observe_eur"] == 607.75
    assert glow["compte_dans_total_depenses"] is False
    autres = next(c for c in cj["categories"] if c["id"] == "autres")
    assert autres["observe_eur"] == 16.68
    assert autres["n_operations"] == 1
    assert all(o["libelle"] != "Facebook" for o in autres["operations"])
    deblock = [o for c in cj["categories"] if c["id"]=="virements_internes" for o in c["operations"] if o["libelle"]=="Deblock"]
    assert len(deblock) == 2
    assert round(sum(o["montant_eur"] for o in deblock), 2) == 150.0
    assert not any("Facebook" in (a.get("sujet") or "") or "Deblock" in (a.get("sujet") or "") for a in (cj.get("operations_ambigues") or []))
    assert not any("114,99" in (a.get("sujet") or "") or "Dr Eric Koch" in (a.get("sujet") or "") for a in (cj.get("operations_ambigues") or []))
    abo = next(c for c in cj["categories"] if c["id"] == "abonnements")
    assert abo["observe_eur"] == 289.99
    assert abo["observe_usd"] == 317.37
    grok = [o for o in abo["operations"] if o["libelle"] == "Grok (via Apple)"]
    assert len(grok) == 1 and grok[0]["montant_eur"] == 114.99
    san = next(c for c in cj["categories"] if c["id"] == "sante")
    assert san["observe_eur"] == 852.15
    assert san["observe_usd"] == 932.59
    koch = [o for o in san["operations"] if o["libelle"] == "Dentiste (Dr Koch)"]
    assert len(koch) == 1 and koch[0]["montant_eur"] == 822.99
    assert koch[0]["sous_categorie"] == "dentaire"
    assert "mutuelle Aon" in (koch[0].get("note_classification") or "")
    assert "Air Glow, frais de fonctionnement" in BDG
    assert "bdg-joint-airglow" in BDG
    courses = next(c for c in cj["categories"] if c["id"] == "courses")
    assert courses["observe_eur"] == 984.83
    assert courses["sous_categories"][0]["id"] == "tickets_caisse"
    assert courses["sous_categories"][0]["statut"] == "complet"
    assert "mois" in courses["sous_categories"][0]
    assert cj["tradingview_sur_le_releve"]["present_sur_le_releve"] is True
    assert cj["tradingview_sur_le_releve"]["total_eur"] == 83.94
    assert "Compte joint famille" in BDG
    assert "Tickets de caisse" in BDG
    assert "bdg-courses-sous" in BDG
    assert "bdg-hero" in BDG and "bdg-hero" in CSS
    # Bloc fusionné « Comptes » (joint + perso), sans doublon des virements
    comptes = bud["comptes"]
    assert comptes["titre"] == "Comptes"
    assert comptes["periode"]["debut"] == "2026-10-01"
    assert comptes["periode"]["fin"] == "2026-11-25"
    assert comptes["totaux"]["salaire_eur"] == 10485.0
    assert comptes["totaux"]["france_travail_eur"] == 1753.2
    assert comptes["totaux"]["revenus_eur"] == 12238.68
    assert comptes["totaux"]["depenses_eur"] == 12628.58
    assert comptes["totaux"]["reste_eur"] == -389.9
    assert comptes["totaux"]["investissement_eur"] == 14882.73
    assert comptes["totaux"]["investissement_xtb_apple_pay_eur"] == 1006.0
    assert comptes["totaux"]["octobre"]["depenses_eur"] == 5736.05
    assert comptes["totaux"]["novembre_1_25"]["depenses_eur"] == 6892.53
    assert comptes["totaux"]["remboursements_eur"] == 552.3
    assert comptes["totaux"]["air_glow_pub_eur"] == 874.34
    assert comptes["totaux"]["n_transferts_dedoublonnes"] == 36
    assert comptes["totaux"]["charges_fixes_credit_mensuel_eur"] == 655.92
    assert comptes["totaux"]["credit_revolut"]["capital_eur"] == 23500.0
    assert comptes["totaux"]["credit_revolut"]["mensualite_eur"] == 169.6
    abo_c = next(c for c in comptes["categories"] if c["id"] == "abonnements")
    assert any(o["libelle"] == "Grok (via Apple)" and o["montant_eur"] == 114.99 for o in abo_c["operations"])
    assert any(o["libelle"] == "Grok Heavy (via Apple)" and o["montant_eur"] == 219.99 for o in abo_c["operations"])
    tr_c = next(c for c in comptes["categories"] if c["id"] == "transport")
    assert all(o["libelle"] != "Cofica Bail" for o in tr_c["operations"])
    assert sum(o["montant_eur"] for o in tr_c["operations"] if o["libelle"] == "LOA Tesla (Cofica Bail)") == 972.64
    cred = next(c for c in comptes["categories"] if c["id"] == "credit_revolut")
    assert cred["poste"] == "Crédit Revolut (remboursement)"
    assert cred["observe_eur"] == 339.2
    assert cred["compte_dans_total_depenses"] is True
    lois = next(c for c in comptes["categories"] if c["id"] == "loisirs")
    assert any(o["libelle"] == "Cadeau / pot de naissance (travail)" and o["montant_eur"] == 20.93 for o in lois["operations"])
    assert all(o["libelle"] != "Fritz Schmitt" for o in lois["operations"])
    courses_ops = next(c for c in comptes["categories"] if c["id"] == "courses")["operations"]
    assert any(o["libelle"] == "Vin, confiture, tire-bouchon (Fritz Schmitt)" and o["montant_eur"] == 23.2 for o in courses_ops)
    enf = next(c for c in comptes["categories"] if c["id"] == "enfant")
    assert any(o["libelle"] == "Photo de classe (Collège Foch)" and o["montant_eur"] == 36.35 and o["sens"] == "credit" for o in enf["operations"])
    remb_ops = comptes.get("remboursements_operations") or []
    assert any(o["libelle"] == "Remboursement Red Bull (Francky Vetsch)" and o["montant_eur"] == 2.0 for o in remb_ops)
    vin_ops = comptes.get("virements_internes_entrants") or []
    assert any(o["libelle"] == "Investissement XTB (Apple Pay *3356)" and o["montant_eur"] == 86.0 for o in vin_ops)
    assert sum(o["montant_eur"] for o in vin_ops if o["libelle"] == "Investissement XTB (Apple Pay *0225)") == 920.0
    assert not (comptes.get("credits_a_confirmer") or [])
    glow_c = next(c for c in comptes["categories"] if c["id"] in ("air_glow", "air_glow_pub"))
    assert any(o["libelle"] == "MailPoet" and o["montant_eur"] == 85.95 for o in glow_c["operations"])
    assert any(o["libelle"] == "Dualhook" and o["montant_eur"] == 14.4 for o in glow_c["operations"])
    amb = " ".join((a.get("sujet") or "") for a in (comptes.get("operations_ambigues") or []))
    assert "Cofica" not in amb and "repayment" not in amb and "Bastos" not in amb
    assert "219,99" not in amb and "MailPoet" not in amb and "Dualhook" not in amb and "Personal loan" not in amb
    assert "Fritz Schmitt" not in amb and "DGFIP" not in amb and "FRANCKY" not in amb and "Francky" not in amb
    assert "Apple Pay" not in amb and "*3356" not in amb and "*0225" not in amb and "Collège Foch" not in amb and "College Foch" not in amb
    assert "Crédit Revolut 23 500" in BDG
    assert "bdg-cat-fixe" in BDG and "bdg-cat-fixe" in CSS
    assert "bdg-fold-btn" in BDG and "data-bdg-fold" in BDG
    assert "apex-bdg-fold" in BDG and "localStorage" in BDG
    assert "bdg-fold-body" in BDG and "bdg-fold-banner" in BDG
    assert "is-folded" in CSS and ".bdg-fold-btn" in CSS
    san_c = next(c for c in comptes["categories"] if c["id"] == "sante")
    koch_c = [o for o in san_c["operations"] if o["libelle"] == "Dentiste (Dr Koch)"]
    assert len(koch_c) == 2
    assert all(o.get("sous_categorie") == "dentaire" for o in koch_c)
    deblock_c = [o for c in comptes["categories"] if c["id"]=="virements_internes" for o in c["operations"] if o["libelle"]=="Deblock"]
    assert round(sum(o["montant_eur"] for o in deblock_c), 2) == 150.0
    courses_c = next(c for c in comptes["categories"] if c["id"] == "courses")
    assert courses_c["sous_categories"][0]["id"] == "tickets_caisse"
    assert courses_c["sous_categories"][0]["statut"] == "complet"
    assert "mois" in courses_c["sous_categories"][0]
    assert "function bdgComptesHtml" in BDG
    assert "bdg-comptes" in BDG
    assert "bdg-op-src" in BDG and "bdg-op-src" in CSS
    assert "home-hero" in CSS
    assert (ROOT / "data" / "revolut" / "frais_trading_ordres.json").exists()
    assert "19/11/2026 à 21 h" not in JS
    assert "XTB 23/11/2026 à 13 h 48" not in JS
    assert "st!=='active'&&st!=='en_attente'" in ACC
    # moyenne ETF / âge : les dates d'ordre d'achat comptent
    assert "date_achat||p.date_ouverture" in ACC

    fo = bud["frais_octobre"]
    tot = fo["totaux"]
    assert tot["frais_usd"] == 108.79 and tot["frais_eur"] == 99.41
    assert tot["entree_usd"] == 28.63 and tot["entree_eur"] == 26.16
    assert tot["sortie_usd"] == 16.82 and tot["sortie_eur"] == 15.37
    assert tot["change_usd"] is None and tot["change_eur"] is None
    assert tot["ovn_usd"] == 63.31 and tot["ovn_eur"] == 57.85
    assert tot["autres_usd"] == 0.03 and tot["autres_eur"] == 0.03
    assert tot["ovn_depasse_objectif"] is True
    inc = fo["dividendes_et_coupons"]
    assert inc["net_usd"] == 30.63 and inc["net_eur"] == 27.99
    assert inc["dividendes_usd"] == 20.12 and inc["coupons_usd"] == 10.51
    assert inc["retenue_a_la_source_usd"] is None
    assert "Entrée" in BDG and "Sortie" in BDG and "OVN octobre" in BDG
    assert "Total frais octobre" in BDG
    assert "function bdgOctOf" in BDG
    assert bud["projection_usd"] == 98.06 and bud["projection_eur"] == 89.59


def test_source_dashboard_presente():
    src = ROOT / "data" / "revolut" / "releve_courtiers_2026-11-25.json"
    assert src.exists()
    rel = json.loads(src.read_text())
    assert rel["date"] == "2026-11-25"
    assert (ROOT / "src" / "update_positions_releve.py").exists()
