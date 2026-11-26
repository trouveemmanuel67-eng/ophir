"""Onglet Immobilier : prévisionnel d'achat à contre-courant sur 5 ans."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
import build_immo_previsionnel as m  # noqa: E402

TPL = (ROOT / "src" / "template.html").read_text(encoding="utf-8")
BUILD = (ROOT / "src" / "build.py").read_text(encoding="utf-8")
JS = (ROOT / "src" / "immobilier.js").read_text(encoding="utf-8")
DATA = json.loads((ROOT / "data" / "immobilier_previsionnel.json").read_text(encoding="utf-8"))

PERIODS = [
    "2027-S1", "2027-S2", "2028-S1", "2028-S2", "2029-S1",
    "2029-S2", "2030-S1", "2030-S2", "2031-S1", "2031-S2",
]
SCENARIOS = ("baisse", "statu_quo", "remontee")


def test_branchement_template_et_build():
    assert 'id="dataImmo"' in TPL
    assert "__DATA_IMMO__" in TPL
    assert "/*__IMMOJS__*/" in TPL
    assert "data/immobilier_previsionnel.json" in BUILD
    assert "src/immobilier.js" in BUILD
    assert "function blocImmoPrev" in JS
    assert "function immoInit" in JS
    assert "function renderImmobilier" in TPL
    assert "blocImmoPrev" in TPL
    assert TPL.index("const prev=(typeof blocImmoPrev") < TPL.index("blocPrix()+blocTaux()+blocTrends()")
    # L'onglet Immobilier reste juste avant le PEA, inchangé pour le reste du menu.
    nav = TPL.split("const TABS=")[1].split("];")[0]
    assert "id:'immobilier',label:'Immobilier'" in nav
    assert nav.index("id:'immobilier'") < nav.index("id:'pea'")


def test_cartes_compactes_et_detail_au_survol():
    for token in (
        "immo-grid",
        "immo-frise",
        "immo-proba",
        "immo-win",
        "immoPop",
        "mouseenter",
        "aria-expanded",
        "novembre à février",
    ):
        assert token in JS
    assert DATA["biens"]["ferme"]["titre"] == "Corps de ferme"
    assert DATA["biens"]["appart"]["titre"] == "4 pièces Strasbourg Nord"
    assert "Estimation, pas une certitude" in DATA["biens"]["ferme"]["resume"]
    assert "immo-prev" in TPL
    assert "immo-pop" in TPL
    assert ".immo-proba{" in TPL
    assert "no-acc" in JS and "no-group" in JS


def test_json_structure_et_sources():
    assert DATA["date"]
    assert DATA["avertissement"]
    assert "pas une prévision certaine" in DATA["avertissement"].lower() or "pas une prévision certaine" in DATA["avertissement"]
    assert DATA["methode"]["score_max"] == 250
    assert DATA["contrainte"]["mensualite_max"] == 1500
    assert DATA["contrainte"]["hors_assurance"] is True
    assert set(DATA["biens"]) == {"ferme", "appart"}
    assert len(DATA["sources"]) >= 8
    urls = [s["url"] for s in DATA["sources"]]
    assert any("insee.fr" in u for u in urls)
    assert any("creditlogement" in u for u in urls)
    assert any("service-public.gouv.fr" in u for u in urls)
    assert any("data.gouv.fr" in u for u in urls)
    assert any("limites" in DATA and DATA["limites"])
    assert any("livre foncier" in x.lower() or "Alsace-Moselle" in x or "DVF" in x for x in DATA["limites"])
    # Données locales minces pour les corps de ferme.
    assert "corps de ferme" in DATA["references"]["ferme"]["note"].lower()


def test_dix_periodes_trois_scenarios_proba():
    for key, bien in DATA["biens"].items():
        frise = bien["frise"]
        assert [p["periode"] for p in frise] == PERIODS
        tot = sum(p["proba_pct"] for p in frise)
        assert abs(tot - 100) < 0.15
        assert bien["meilleure_periode"] in PERIODS
        assert 0 < bien["meilleure_proba_pct"] <= 100
        assert 0 <= bien["meilleure_note"] <= 250
        assert bien["meilleure_bande"] in ("violet", "rouge", "orange", "vert", "cyan")
        for s in SCENARIOS:
            sc = bien["scenarios"][s]
            assert [p["periode"] for p in sc["periodes"]] == PERIODS
            st = sum(p["proba_pct"] for p in sc["periodes"])
            assert abs(st - 100) < 0.15
            for p in sc["periodes"]:
                pts = p["points"]
                assert pts["total"] == (
                    pts["prix"] + pts["accessibilite"] + pts["volume"] + pts["marge"] + pts["dpe"]
                )
                assert 0 <= pts["total"] <= 250
                assert pts["prix"] <= 70
                assert pts["accessibilite"] <= 60
                assert pts["volume"] <= 50
                assert pts["marge"] <= 40
                assert pts["dpe"] <= 30


def test_meilleure_fenetre_ferme_2028s1_tous_scenarios():
    f = DATA["biens"]["ferme"]
    assert f["meilleure_periode"] == "2028-S1"
    for s in SCENARIOS:
        assert f["scenarios"][s]["meilleure_periode"] == "2028-S1"


def test_appart_baisse_des_taux_plus_tot():
    """Si les taux baissent vite, la fenêtre des 4 pièces s'avance : on n'attend pas 2028."""
    a = DATA["biens"]["appart"]
    assert a["scenarios"]["baisse"]["meilleure_periode"] < "2028-S1"
    assert a["meilleure_periode"] == "2028-S1"  # mélange et scénarios de taux hauts


def test_formules_capital_et_softmax():
    cap = m.capital(1500, 3.57, 25)
    # Contrôle de cohérence : ~297 400 € à 3,57 % sur 25 ans.
    assert 297000 < cap < 298000
    mens = m.mensualite(cap, 3.57, 25)
    assert abs(mens - 1500) < 0.05
    # Softmax : le plus haut score reçoit la plus haute proba, somme = 1.
    probs = m.softmax([100, 120, 180])
    assert abs(sum(probs) - 1) < 1e-12
    assert probs[2] > probs[1] > probs[0]


def test_echelle_couleurs():
    assert m.band(9)[0] == "violet"
    assert m.band(10)[0] == "rouge"
    assert m.band(69)[0] == "rouge"
    assert m.band(70)[0] == "orange"
    assert m.band(129)[0] == "orange"
    assert m.band(130)[0] == "vert"
    assert m.band(189)[0] == "vert"
    assert m.band(190)[0] == "cyan"
    f = DATA["biens"]["ferme"]
    b, hx = m.band(f["meilleure_note"])
    assert f["meilleure_bande"] == b
    assert f["meilleure_hex"] == hx


def test_budget_sous_contrainte_et_prix_sources():
    f = DATA["biens"]["ferme"]
    a = DATA["biens"]["appart"]
    assert f["prix_m2_actuel"] == 2000
    assert f["prix_typique_actuel"] == 230000
    assert a["prix_m2_actuel"] == 2724
    assert a["prix_typique_actuel"] == 2724 * 85
    assert f["budget_accessible_actuel"] == a["budget_accessible_actuel"]
    assert f["mensualite_typique_actuelle"] < 1500
    assert a["mensualite_typique_actuelle"] < 1500
    # Le budget à la fenêtre reste du même ordre, selon les taux du semestre.
    assert 250000 < f["budget_accessible_fenetre"] < 350000


def test_json_regenerable():
    """Le fichier publié est exactement celui du modèle, rien n'est inventé à la main."""
    rebuilt = m.build()
    disk = json.loads((ROOT / "data" / "immobilier_previsionnel.json").read_text(encoding="utf-8"))
    assert rebuilt["biens"]["ferme"]["meilleure_periode"] == disk["biens"]["ferme"]["meilleure_periode"]
    assert rebuilt["biens"]["appart"]["frise"] == disk["biens"]["appart"]["frise"]
    assert rebuilt["methode"]["poids"] == disk["methode"]["poids"]
