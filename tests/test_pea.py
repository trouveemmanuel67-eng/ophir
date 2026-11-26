"""Onglet PEA : ETF à rendement éligibles XTB, projection 200 €/mois sur 5 ans."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TPL = (ROOT / "src" / "template.html").read_text(encoding="utf-8")
BUILD = (ROOT / "src" / "build.py").read_text(encoding="utf-8")
JS = (ROOT / "src" / "pea.js").read_text(encoding="utf-8")
DATA = json.loads((ROOT / "data" / "pea.json").read_text(encoding="utf-8"))


def _fv(monthly: float, rate_pa: float, months: int) -> float:
    i = rate_pa / 12
    if abs(i) < 1e-15:
        return monthly * months
    return monthly * ((1 + i) ** months - 1) / i


def test_onglet_apres_immobilier():
    nav = TPL.split("const TABS=")[1].split("];")[0]
    assert "id:'pea',label:'PEA'" in nav
    assert nav.index("id:'immobilier'") < nav.index("id:'pea'")
    assert "render:renderPea" in nav
    after = nav.split("id:'pea'")[1]
    assert "id:'" not in after  # dernier onglet du menu


def test_build_et_template_branchent_les_donnees():
    assert 'id="dataPea"' in TPL
    assert "__DATA_PEA__" in TPL
    assert "/*__PEAJS__*/" in TPL
    assert "data/pea.json" in BUILD
    assert "src/pea.js" in BUILD
    assert "function renderPea" in JS
    assert "peaFv" in JS
    assert "peaTaux" in JS
    assert "no-acc" in JS  # cartes visibles, pas repliées par accMain


def test_liste_max_10_et_donnees_relies():
    etfs = DATA["etfs"]
    assert 1 <= len(etfs) <= 10
    isins = [e["isin"] for e in etfs]
    assert len(isins) == len(set(isins))
    for e in etfs:
        assert e["pea"] is True
        assert e["xtb_omi"] is True
        assert e["isin"] and len(e["isin"]) == 12
        assert e["xtb"]
        assert e["nom"]
        assert e["ter_pct"] is not None
        assert e["politique"] in ("distribution", "capitalisation")
        if e["politique"] == "distribution":
            assert e["rendement_actuel_pct"] and e["rendement_actuel_pct"] > 0
        else:
            assert e["rendement_actuel_pct"] is None
    # ISINs figés, vérifiés justETF + OMI : on n'invente pas de ticker
    assert "LU1812092168" in isins  # SEL, aussi confirmé page XTB
    assert "DE0002635281" in isins
    assert "IE00B0M62S72" in isins
    assert "LU0292095535" in isins
    assert "IE00B5M1WJ87" in isins
    assert "FR0010717090" in isins
    assert "DE000A2QP380" in isins


def test_classement_par_rendement_puis_capitalisants():
    etfs = DATA["etfs"]
    dist = [e for e in etfs if e["politique"] == "distribution"]
    acc = [e for e in etfs if e["politique"] == "capitalisation"]
    yields = [e["rendement_actuel_pct"] for e in dist]
    assert yields == sorted(yields, reverse=True)
    if dist and acc:
        assert etfs.index(dist[-1]) < etfs.index(acc[0])
    assert DATA["classement"] == "rendement_qualite"
    assert "note APEX sur 250 n'est pas calculée" in DATA["classement_libelle"]


def test_projection_trois_scenarios_et_formule():
    p = DATA["projection"]
    assert p["versement_mensuel_eur"] == 200
    assert p["duree_ans"] == 5
    assert p["n_versements"] == 60
    assert p["total_verse_eur"] == 12000
    ids = [s["id"] for s in p["scenarios"]]
    assert ids == ["prudent", "central", "favorable"]
    for s in p["scenarios"]:
        got = s["capital_eur"]
        exp = _fv(200, s["taux_pa_pct"] / 100, 60)
        assert abs(got - exp) < 0.05, (s["id"], got, exp)
    assert p["scenarios"][0]["taux_pa_pct"] == 4.0
    assert p["scenarios"][1]["taux_pa_pct"] == 7.0
    assert p["scenarios"][2]["taux_pa_pct"] == 10.0
    assert "Aucun rendement n'est garanti" in p["avertissement"]
    assert "perte en capital" in p["avertissement"]
    assert "150 000" in DATA["pea_regles"]
    assert "5 ans" in DATA["pea_regles"]


def test_css_compact_mobile_et_chiffres_cles():
    assert "/* ===== Onglet PEA ===== */" in TPL
    assert ".pea-sc-cap" in TPL
    assert ".pea-yld" in TPL
    assert "@media(max-width:640px)" in TPL
    assert "grid-template-columns:1fr" in TPL[TPL.find("/* ===== Onglet PEA ===== */"):]
