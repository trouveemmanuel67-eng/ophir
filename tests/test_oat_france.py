"""OAT françaises (Revolut) dans l'onglet Obligations : ISIN, notes APEX, duration."""
from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.build_oat_france import (  # noqa: E402
    FORMULE_DURATION, OATS, SETTLE, cashflows, duration_par_exemple,
)

DATA = json.loads((ROOT / "data" / "obligations_dispo.json").read_text(encoding="utf-8"))
JS = (ROOT / "src" / "obligations.js").read_text(encoding="utf-8")
TPL = (ROOT / "src" / "template.html").read_text(encoding="utf-8")
BUILD = (ROOT / "src" / "build.py").read_text(encoding="utf-8")

ISIN_OFFICIELS = {
    "FR0011317783": ("OAT 2,75 % oct. 2027", 2.75, "2027-10-25", 3.06),
    "FR0011883966": ("OAT 2,50 % mai 2030", 2.50, "2030-05-25", 3.77),
    "FR0013234333": ("OAT verte 1,75 % juin 2039", 1.75, "2039-06-25", 4.86),
    "FR0011461037": ("OAT 3,25 % mai 2045", 3.25, "2045-05-25", 5.16),
    "FR001400XJJ3": ("OAT 3,75 % mai 2056", 3.75, "2056-05-25", 5.30),
    "FR0010870956": ("OAT 4,00 % avr. 2060", 4.00, "2060-04-25", 5.30),
}


def _lignes():
    return DATA["pays"]["fr"]["lignes"]


def test_six_oat_isin_aft():
    lignes = _lignes()
    assert len(lignes) == 6
    isins = [x["isin"] for x in lignes]
    assert isins == list(ISIN_OFFICIELS)
    assert len(set(isins)) == 6
    for x in lignes:
        att = ISIN_OFFICIELS[x["isin"]]
        assert x["nom"] == att[0]
        assert x["coupon"] == att[1]
        assert x["maturite"] == att[2]
        assert x["rdt"] == att[3]
        assert x["ccy"] == "EUR"
        assert x["dispo_revolut"] is True
        assert x["emetteur"] == "Agence France Trésor"
        assert x["url_aft"].startswith("https://www.aft.gouv.fr/")
        assert x["isin"] in x["url_aft"].lower() or x["isin"].lower() in x["url_aft"].lower()


def test_courbe_situation_et_risque():
    sit = DATA["situation"]
    assert sit["titre"] == "Situation des taux français"
    assert len(sit["points"]) == 6
    assert [p["annee"] for p in sit["points"]] == ["2027", "2030", "2039", "2045", "2056", "2060"]
    assert [p["rdt"] for p in sit["points"]] == [3.06, 3.77, 4.86, 5.16, 5.30, 5.30]
    assert "Flat tax 30 %" in DATA["risque_court"]
    assert "hors PEA" in DATA["risque_court"]
    assert "taux" in DATA["risque_court"].lower()
    assert DATA["max_par_pays"] == 6
    assert "16 h 42" in DATA["date_libelle"]
    assert DATA["date_valorisation"] == "2026-11-26"


def test_duration_formule_pair_et_sensibilite():
    # Obligation au pair, coupon annuel = rendement, 30 ans : formule fermée.
    mac = duration_par_exemple(0.04, 30)
    assert abs(mac - 17.9837) < 1e-3
    assert abs(mac / 1.04 - 17.292) < 1e-3
    # Les 6 lignes ont une duration calculée, pas inventée.
    for x in _lignes():
        d = x["duration"]
        assert d["formule"] == FORMULE_DURATION
        assert d["date_reglement"] == "2026-11-26"
        assert d["macaulay"] > 0
        assert d["modifiee"] < d["macaulay"]  # y > 0
        assert d["sensibilite_plus_1pt_pct"] < 0
        # Recalcul à la volée : même résultat.
        oat = next(o for o in OATS if o["isin"] == x["isin"])
        rec = cashflows(oat["coupon"], oat["rdt"], oat["maturite"], oat["coupon_md"], SETTLE)
        assert rec["modifiee"] == d["modifiee"]
        assert rec["sensibilite_plus_1pt_pct"] == d["sensibilite_plus_1pt_pct"]
    # Les longues sont plus sensibles que les courtes.
    by = {x["isin"]: x["duration"]["modifiee"] for x in _lignes()}
    assert by["FR0011317783"] < by["FR0011883966"] < by["FR0013234333"]
    assert by["FR0013234333"] < by["FR0011461037"] < by["FR001400XJJ3"]
    assert by["FR001400XJJ3"] <= by["FR0010870956"]


def test_notes_apex_grille_et_couleurs():
    bands = {
        "violet": (-50, 10, "#9d54ff"),
        "rouge": (10, 70, "#ff2d2d"),
        "orange": (70, 130, "#ff8c1a"),
        "vert": (130, 190, "#22c55e"),
        "cyan": (190, 251, "#00e5ff"),
    }
    for x in _lignes():
        a = x["apex10"]
        assert a["scale"] == 250
        assert a["total_min"] == -50
        assert a["total_max"] == 250
        n = a["total"]
        assert n == a["note"]
        # Technique et MM40 manquantes = 0.
        pts = a["decomp"]["points"]
        assert pts["RSI"] == 0
        assert pts["MACD"] == 0
        assert pts["Fibo"] == 0
        assert pts["CCI"] == 0
        assert (pts.get("mm40") or pts.get("MM40 hebdo")) == 0
        tech = a["decomp"]["technique"]
        assert tech["etat"] == "n.c."
        fond = a["decomp"]["fondamental"]
        assert fond["max"] == 90
        assert fond["points"] is not None
        # Sentiment maison souverains euro, à contre-courant.
        sent = a.get("sentiment") or {}
        assert sent.get("cle") == "oblig:eurgov"
        assert a["band"] in bands
        lo, hi, hx = bands[a["band"]]
        assert lo <= n < hi
        assert a["hex"] == hx
        # 2056 trop récente : pas les 10 points d'ancienneté.
        ids = {e["id"]: e for e in fond["elements"]}
        if x["isin"] == "FR001400XJJ3":
            assert ids["age5"]["ok"] is False
            assert ids["age5"]["points"] == 0
        else:
            assert ids["age5"]["ok"] is True
            assert ids["age5"]["points"] == 10
        assert ids["change"]["points"] == 10
        assert ids["ter15"]["points"] == 10
        assert ids["enc500"]["points"] == 10
        assert ids["notation"]["points"] == 10


def test_affichage_js_et_css():
    assert "function obOatTile" in JS
    assert "function obRenderFrance" in JS
    assert "function obOatCurveChart" in JS
    assert "function obOatFranceDetail" in JS
    assert "cObOatFr" in JS
    assert "obOatFranceHas" in JS
    assert "srHead('OAT · Agence France Trésor')" in JS
    assert "srCells(s)" in JS
    assert "srWire(c)" in JS
    assert "sec-grid" in JS
    assert "dispo-badge" in JS
    assert "note ob-pea" in JS
    assert "oatFr" in JS
    assert "blocks.filter(b=>b.marker)" in JS
    assert "sans note APEX" in JS  # conservé pour les autres pays sans OAT
    assert ".ob-oat-curve" in TPL
    assert 'id="data15"' in TPL
    assert "data/obligations_dispo.json" in BUILD
    assert "src/obligations.js" in BUILD


def test_non_verifie_documente():
    nv = " ".join(DATA["non_verifie"])
    assert "Yahoo" in nv
    assert "MM40" in nv
    assert "EUNH" in nv
