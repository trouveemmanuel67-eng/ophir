"""Onglet Marché privé : 4 fonds ELTIF Revolut, note APEX 250, critère manquant = 0."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TPL = (ROOT / "src" / "template.html").read_text(encoding="utf-8")
BUILD = (ROOT / "src" / "build.py").read_text(encoding="utf-8")
JS = (ROOT / "src" / "marche_prive.js").read_text(encoding="utf-8")
DATA = json.loads((ROOT / "data" / "marche_prive.json").read_text(encoding="utf-8"))

BANDS = [
    ("violet", -50, 10, "#9d54ff"),
    ("rouge", 10, 70, "#ff2d2d"),
    ("orange", 70, 130, "#ff8c1a"),
    ("vert", 130, 190, "#22c55e"),
    ("cyan", 190, 251, "#00e5ff"),
]


def _band(note: int):
    if note >= 190:
        return "cyan", "#00e5ff"
    if note < 10:
        return "violet", "#9d54ff"
    for bid, lo, hi, hx in BANDS:
        if lo <= note < hi:
            return bid, hx
    return "cyan", "#00e5ff"


def _pts_frais(v):
    if v is None:
        return 0
    if v <= 3.0:
        return 40
    if v <= 3.5:
        return 25
    if v <= 4.0:
        return 15
    if v <= 5.0:
        return 5
    return 0


def _pts_encours(v):
    if v is None:
        return 0
    if v >= 500:
        return 30
    if v >= 250:
        return 20
    if v >= 100:
        return 15
    if v >= 50:
        return 10
    if v >= 20:
        return 5
    return 0


def _pts_sri(v):
    if v is None:
        return 0
    if v <= 2:
        return 20
    if v == 3:
        return 15
    if v == 4:
        return 10
    if v == 5:
        return 5
    return 0


def test_onglet_apres_pea():
    nav = TPL.split("const TABS=")[1].split("];")[0]
    assert "id:'marche-prive',label:'Marché privé'" in nav
    assert "render:renderMarchePrive" in nav
    assert nav.index("id:'pea'") < nav.index("id:'marche-prive'")
    after = nav.split("id:'marche-prive'")[1]
    assert "id:'" not in after  # dernier onglet du menu


def test_build_et_template_branchent_les_donnees():
    assert 'id="dataMarchePrive"' in TPL
    assert "__DATA_MARCHE_PRIVE__" in TPL
    assert "/*__MARCHE_PRIVE_JS__*/" in TPL
    assert "data/marche_prive.json" in BUILD
    assert "src/marche_prive.js" in BUILD
    assert "function renderMarchePrive" in JS
    assert "mp-card" in JS
    assert "mp-det" in JS
    assert "v==null" in JS  # encours manquant → n.c., pas 0 M€
    assert "aucun rendement" in (DATA.get("intro") or "").lower() or "Aucun rendement" in (DATA.get("intro") or "")


def test_css_compact_mobile():
    bloc = TPL[TPL.find("/* ===== Onglet Marché privé ===== */"):]
    assert ".mp-card" in bloc
    assert ".mp-kpis" in bloc
    assert ".mp-det" in bloc
    assert "@media(max-width:640px)" in bloc
    assert "grid-template-columns:repeat(2,minmax(0,1fr))" in bloc


def test_quatre_fonds_revolut_isins_uniques():
    fonds = DATA["fonds"]
    assert len(fonds) == 4
    isins = [f["isin"] for f in fonds]
    assert len(isins) == len(set(isins))
    noms = {f["nom"] for f in fonds}
    assert "Hamilton Lane Private Markets Access ELTIF" in noms
    assert "Partners Group Private Markets ELTIF" in noms
    assert "Apollo Global Private Credit ELTIF" in noms
    assert "Ares European Strategic Income ELTIF" in noms
    by = {f["id"]: f for f in fonds}
    assert by["hamilton-lane"]["isin"] == "LU3051916800"
    assert by["partners-group"]["isin"] == "LU3173236467"
    assert by["apollo"]["isin"] == "LU3146842573"
    assert by["ares"]["isin"] == "LU3091050792"
    assert by["ares"]["type"] == "Crédit privé"
    assert by["hamilton-lane"]["type"] == "Capital-investissement"
    assert by["partners-group"]["type"] == "Multi-actifs"
    assert by["apollo"]["type"] == "Crédit privé"


def test_classement_par_note_et_risques():
    fonds = DATA["fonds"]
    notes = [f["apex10"]["total"] for f in fonds]
    assert notes == sorted(notes, reverse=True)
    assert DATA["classement"] == "note_apex"
    risques = " ".join(DATA["risques"]).lower()
    assert "capital non garanti" in risques
    assert "liquidité" in risques
    assert "frais" in risques
    assert any("promis" in r.lower() or "garantie" in r.lower() for r in DATA["risques"])
    assert "aucun rendement promis" in DATA["intro"].lower()


def test_note_apex_formule_couleurs_et_nc():
    g = DATA["note_grille"]
    assert g["echelle"] == "−50 à 250"
    pts = g["points"]
    assert pts["frais"] == 40
    assert pts["encours"] == 30
    assert pts["anciennete"] == 30
    assert pts["performance"] == 30
    assert pts["liquidite"] == 30
    assert pts["sri"] == 20
    assert pts["transparence"] == 20
    assert pts["sentiment"] == 50
    assert g["fondamental_somme"] == 200
    assert g["technique"] == 0
    assert g["mm40"] == 0
    for f in DATA["fonds"]:
        a = f["apex10"]
        assert a["scale"] == 250
        assert a["total_min"] == -50
        assert a["total_max"] == 250
        n = a["total"]
        assert isinstance(n, int) and -50 <= n <= 250
        p = a["decomp"]["points"]
        fond = a["decomp"]["fondamental"]
        s = sum(c["points"] for c in fond["criteres"])
        assert fond["points"] == s
        assert fond["max"] == 200
        assert a["fondamental"] == s
        assert a["technique"] == 0
        assert a["mm40"] == 0
        assert a["sentiment"] == 0
        assert a["decomp"]["sentiment"]["etat"] == "n.c."
        brut = s + a["sentiment"]
        assert a["brut"] == brut
        assert n == max(-50, min(250, brut))
        bid, hx = _band(n)
        assert a["band"] == bid
        assert a["hex"] == hx
        for c in fond["criteres"]:
            assert 0 <= c["points"] <= c["max"]
            if c["etat"] == "n.c.":
                assert c["points"] == 0
        # Frais et SRI connus se recalculent
        frais = next(c for c in fond["criteres"] if c["id"] == "frais")
        assert frais["points"] == _pts_frais(f["frais_annuels_pct"])
        enc = next(c for c in fond["criteres"] if c["id"] == "encours")
        assert enc["points"] == _pts_encours(f["encours_meur"])
        sri = next(c for c in fond["criteres"] if c["id"] == "sri")
        assert sri["points"] == _pts_sri(f["sri"])


def test_infos_manquantes_valent_zero():
    by = {f["id"]: f for f in DATA["fonds"]}
    # Apollo et Partners Group : pas d'encours officiel, pas de perf, pas de date de lancement
    for fid in ("apollo", "partners-group"):
        f = by[fid]
        crit = {c["id"]: c for c in f["apex10"]["decomp"]["fondamental"]["criteres"]}
        assert crit["encours"]["etat"] == "n.c." and crit["encours"]["points"] == 0
        assert crit["performance"]["etat"] == "n.c." and crit["performance"]["points"] == 0
        assert crit["anciennete"]["etat"] == "n.c." and crit["anciennete"]["points"] == 0
        assert f["infos_manquantes"]
    # Ares : perf officielle non publiée (tirets du factsheet)
    ares = by["ares"]
    perf = next(c for c in ares["apex10"]["decomp"]["fondamental"]["criteres"] if c["id"] == "performance")
    assert perf["etat"] == "n.c." and perf["points"] == 0
    assert ares["encours_meur"] == 278
    assert ares["apex10"]["total"] == 100
    # Hamilton Lane : performance officielle trouvée, frais élevés = 0
    hl = by["hamilton-lane"]
    crit = {c["id"]: c for c in hl["apex10"]["decomp"]["fondamental"]["criteres"]}
    assert crit["performance"]["etat"] == "ok" and crit["performance"]["points"] == 30
    assert crit["frais"]["points"] == 0
    assert hl["encours_meur"] == 66.34
    assert hl["apex10"]["total"] == 85
    assert by["apollo"]["apex10"]["total"] == 55
    assert by["partners-group"]["apex10"]["total"] == 30
