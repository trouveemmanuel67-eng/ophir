"""Onglet PEA : ETF éligibles XTB, note APEX 250, projection des positions."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TPL = (ROOT / "src" / "template.html").read_text(encoding="utf-8")
BUILD = (ROOT / "src" / "build.py").read_text(encoding="utf-8")
JS = (ROOT / "src" / "pea.js").read_text(encoding="utf-8")
DATA = json.loads((ROOT / "data" / "pea.json").read_text(encoding="utf-8"))

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


def _fv_eq(monthly: float, rate_pa: float, months: int) -> float:
    """Annuité de fin de mois au taux mensuel équivalent i = (1+r)^(1/12) − 1."""
    i = (1 + rate_pa) ** (1 / 12) - 1
    if abs(i) < 1e-15:
        return monthly * months
    return monthly * ((1 + i) ** months - 1) / i


def test_onglet_apres_immobilier():
    nav = TPL.split("const TABS=")[1].split("];")[0]
    assert "id:'pea',label:'PEA'" in nav
    assert nav.index("id:'immobilier'") < nav.index("id:'pea'")
    assert "render:renderPea" in nav
    assert nav.index("id:'pea'") < nav.index("id:'marche-prive'")


def test_build_et_template_branchent_les_donnees():
    assert 'id="dataPea"' in TPL
    assert "__DATA_PEA__" in TPL
    assert "/*__PEAJS__*/" in TPL
    assert "data/pea.json" in BUILD
    assert "src/pea.js" in BUILD
    assert "function renderPea" in JS
    assert "peaFv" in JS
    assert "peaMensuel" in JS
    assert "positions_pea" in JS
    assert "no-acc" in JS
    assert "apexNoteHTML" in JS
    assert "pea-legende" in JS
    assert "pea-scs" not in JS
    assert "Plafond" not in JS
    assert "Avantage fiscal" not in JS


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
    assert "LU1812092168" in isins
    assert "DE0002635281" in isins
    assert "IE00B0M62S72" in isins
    assert "LU0292095535" in isins
    assert "IE00B5M1WJ87" in isins
    assert "FR0010717090" in isins
    assert "DE000A2QP380" in isins


def test_classement_par_note_apex():
    etfs = DATA["etfs"]
    notes = [e["apex10"]["total"] for e in etfs]
    assert notes == sorted(notes, reverse=True)
    assert DATA["classement"] == "note_apex"
    assert "note_grille" in DATA
    assert DATA["note_grille"]["points"]["fondamental"] == 90
    assert DATA["note_grille"]["points"]["mm40"] == 30
    assert "pas le CNN" in DATA["note_grille"]["regles"]["sentiment"].lower() or "Pas le CNN" in DATA["note_grille"]["regles"]["sentiment"]


def test_projection_positions_vertes_vide_a_zero():
    """Sans position PEA, le versement (100 € × ETF verts détenus) et tous les montants sont à 0."""
    assert DATA["positions_pea"] == []
    assert DATA["positions_pea_champs"] == ["isin", "quantite", "prix_moyen", "versement_mensuel"]
    p = DATA["projection"]
    assert p["titre"] == "Projection des positions"
    assert p["regle"] == "100 €/mois par ETF dès qu'il passe au vert (≥130)"
    assert p["seuil_vert"] == 130
    assert p["versement_unitaire_eur"] == 100
    assert p["n_etf_verts_detenus"] == 0
    assert p["versement_mensuel_eur"] == 0
    assert p["versement_annuel_eur"] == 0
    assert p["total_verse_eur"] == 0
    assert p["duree_ans"] == 5
    d = p["defaut"]
    assert d["an1"] == {"verse": 0, "estime": 0, "gain": 0, "gain_pct": 0}
    assert d["an5"] == {"verse": 0, "estime": 0, "gain": 0, "gain_pct": 0}
    assert d["taux_mensuel_equivalent_pct"] == 0
    assert "aucun rendement garanti" in p["avertissement"].lower()
    assert "perte en capital" in p["avertissement"]
    # Formule toujours au taux mensuel équivalent, quand un versement existe
    assert "Math.pow(1+r,1/12)-1" in JS
    assert "r/12" not in JS
    assert "peaMensuel" in JS
    assert "positions_pea" in JS
    assert "Projection 200" not in JS
    assert "200 €/mois" not in JS
    assert "pea-regle" in JS
    assert "peaVm" in JS
    assert "peaVa" in JS
    assert "peaIm" in JS
    assert "peaIa" in JS
    assert "peaC1" in JS
    assert "peaC5" in JS
    # Aujourd'hui aucun ETF listé n'est vert, et surtout aucune position
    assert all((e.get("apex10") or {}).get("total", 0) < 130 for e in DATA["etfs"])
    # Si une position verte existait, le versement serait 100 € × le nombre
    unit, seuil = p["versement_unitaire_eur"], p["seuil_vert"]
    etf = next(e for e in DATA["etfs"] if e["isin"])
    faux = {"isin": etf["isin"], "quantite": 1, "prix_moyen": 10, "versement_mensuel": unit}
    note = (etf.get("apex10") or {}).get("total") or 0
    attendu = unit if note >= seuil else 0
    assert attendu == 0  # les notes actuelles sont sous 130
    # La formule d'annuité reste juste pour un versement non nul
    assert abs(_fv_eq(100, 0.07, 12) - 1238.03) < 0.05
    assert "pea-scs" not in JS
    assert "pea-just" not in JS


def test_css_compact_mobile_et_note():
    bloc = TPL[TPL.find("/* ===== Onglet PEA ===== */"):]
    assert ".pea-yld" in bloc
    assert ".pea-apex" in bloc
    assert ".pea-legende" in bloc
    assert ".pea-vers" in bloc
    assert ".pea-horiz" in bloc
    assert ".pea-regle" in bloc
    assert "@media(max-width:640px)" in bloc
    assert "pea-sc-cap" not in bloc


def test_note_apex_formule_couleurs_et_nc():
    g = DATA["note_grille"]
    assert g["echelle"] == "−50 à 250"
    pts = g["points"]
    assert pts == {"rsi": 30, "macd": 30, "fibonacci": 30, "cci": 20, "sentiment": 50, "fondamental": 90, "mm40": 30}
    etfs = DATA["etfs"]
    assert etfs, "liste vide"
    for e in etfs:
        a = e["apex10"]
        assert a["scale"] == 250
        assert a["total_min"] == -50
        assert a["total_max"] == 250
        n = a["total"]
        assert isinstance(n, int) and -50 <= n <= 250
        p = a["decomp"]["points"]
        brut = p["rsi"] + p["macd"] + p["fibonacci"] + p["cci"] + p["sentiment"] + p["fondamental"] + p["mm40"]
        assert a["brut"] == brut
        assert n == max(-50, min(250, brut))
        bid, hx = _band(n)
        assert a["band"] == bid
        assert a["hex"] == hx
        # n.c. = 0, pas de redistribution
        fond = a["decomp"]["fondamental"]
        assert fond["points"] == p["fondamental"]
        assert fond["max"] == 90
        for c in fond["criteres"]:
            assert 0 <= c["points"] <= c["max"]
            if c["etat"] == "n.c.":
                assert c["points"] == 0
        # Valorisation : seule SPYW a un PER d'émetteur
        valo = next(c for c in fond["criteres"] if c["id"] == "valorisation")
        if e["id"] == "SPYW":
            assert valo["etat"] == "ok" and valo["per"] == 11.95 and valo["points"] == 10
        else:
            assert valo["etat"] == "n.c." and valo["points"] == 0
        # Capitalisants : rendement et dividende à 0
        if e["politique"] == "capitalisation":
            rend = next(c for c in fond["criteres"] if c["id"] == "rendement")
            div = next(c for c in fond["criteres"] if c["id"] == "dividende")
            assert rend["etat"] == "n.c." and rend["points"] == 0
            assert div["etat"] == "n.c." and div["points"] == 0
        assert a.get("yahoo") and a.get("n_semaines", 0) >= 40
        assert a["decomp"]["sentiment"]["source"].find("pas le CNN") >= 0
    # Légende et affichage
    assert "violet" in DATA["note_legende"]
    assert "cyan" in DATA["note_legende"]
    assert "pea-legende" in JS
    assert "apexNoteHTML" in JS


def test_symbole_tradingview_dans_la_ligne():
    """Chaque ETF a un symbole TradingView vérifié et un bouton qui copie ce ticker."""
    expected = {
        "SPYW": "XETR:SPYW",
        "SEL": "EURONEXT:SEL",
        "EXSG": "XETR:EXSG",
        "IQQA": "XETR:IQQA",
        "XD3E": "XETR:DXSA",  # XETR:XD3E n'existe pas
        "CD8": "EURONEXT:CD8",
        "IDVA": "EURONEXT:IDVA",
    }
    for e in DATA["etfs"]:
        assert e.get("tv") == expected[e["id"]], (e["id"], e.get("tv"))
        assert ":" in e["tv"]
    assert "pea-tv" in JS
    assert "e.tv" in JS
    assert "pea-cp" in JS
    assert "peaCopyTv" in JS
    assert "navigator.clipboard" in JS
    assert "execCommand('copy')" in JS
    assert "Copié" in JS
    assert "Copier pour TradingView" not in JS  # pas un bouton global, un bouton par ligne
    assert ".pea-tv" in TPL
    assert ".pea-cp" in TPL
    bloc = TPL[TPL.find("/* ===== Onglet PEA ===== */"):]
    assert "user-select:all" in bloc
    assert "width:32px" in bloc
    assert "height:32px" in bloc
    assert "min-width:32px" in bloc
    assert "min-height:32px" in bloc
