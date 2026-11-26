"""Objectif courses Leclerc + Picard (867 €/mois) dans l'onglet Budget."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = json.loads((ROOT / "data" / "budget" / "budget_mensuel_moyen.json").read_text(encoding="utf-8"))
PARAMS = json.loads((ROOT / "data" / "budget" / "objectif_courses.json").read_text(encoding="utf-8"))
JS = (ROOT / "src" / "budget.js").read_text(encoding="utf-8")
TPL = (ROOT / "src" / "template.html").read_text(encoding="utf-8")
BUILDER = (ROOT / "src" / "build_budget_mensuel.py").read_text(encoding="utf-8")


def _poste(cid: str) -> dict:
    for g in DATA["groupes"]:
        for p in g["postes"]:
            if p["id"] == cid:
                return p
    raise AssertionError(cid)


def test_parametres_faciles_a_changer():
    assert PARAMS["leclerc"]["eur_semaine"] == 150
    assert PARAMS["picard"]["eur_par_passage"] == 100
    assert PARAMS["picard"]["frequence"] == "toutes_les_2_semaines"
    assert "objectif_courses.json" in BUILDER
    assert "PICARD_PASSAGES_AN" in BUILDER
    assert "toutes_les_semaines" in BUILDER


def test_objectif_867_leclerc_picard():
    oc = DATA["objectif_courses"]
    assert oc["leclerc_eur_mois"] == 650
    assert oc["picard_eur_mois"] == 217
    assert oc["total_eur_mois"] == 867
    courses = _poste("courses")
    assert courses["objectif_eur"] == 867
    assert courses["moyenne_eur"] == 980.57
    assert courses["economie_visee_eur"] == 113.57
    assert oc["observe_octobre_eur"] == 980.57
    assert oc["observe_octobre_brut_eur"] == 1001.54
    assert oc["economie_visee_eur"] == 113.57


def test_hygiene_pas_un_poste_a_part():
    ids = [p["id"] for g in DATA["groupes"] for p in g["postes"]]
    assert "hygiene" not in ids
    assert "entretien" not in ids
    assert "litiere" not in ids
    assert "déjà dans Courses" in DATA["objectif_courses"]["hygiene_entretien_litiere"]


def test_bandeau_recalcule_avec_le_panier():
    # Avant : déficit 1050.84, panier 135.91, réduction 914.93 / 1184.22.
    # Après : panier 249.48 (+113.57), réduction 801.36 / 1070.65.
    # Le déficit courant (il te manque) ne change pas.
    assert DATA["capacite_actuelle"]["eur"] == -1050.84
    assert DATA["capacite_actuelle"]["avec_air_glow_eur"] == -1320.13
    assert DATA["panier_cible"]["total_economie_eur"] == 249.48
    assert DATA["objectif_reduction_autres_postes"]["eur"] == 801.36
    assert DATA["objectif_reduction_autres_postes"]["avec_air_glow_eur"] == 1070.65
    ids = [p["id"] for p in DATA["panier_cible"]["lignes"]]
    assert "courses" in ids
    assert "ovn" in ids


def test_affichage_compact_et_detail_au_toucher():
    assert "bdgCoursesDetHtml" in JS
    assert "bdg-obj-line" in JS
    assert "bdg-courses-det" in JS
    assert "Objectif" in JS and "Économie visée" in JS
    assert ".bdg-obj-line" in TPL
    assert "Il te manque" in JS
    assert "Capacité cible personnelle (panier inchangé)" not in JS
