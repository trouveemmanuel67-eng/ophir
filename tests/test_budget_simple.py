"""Onglet Budget : bandeau mensuel et bloc Comptes simplifiés (affichage seulement)."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
JS = (ROOT / "src" / "budget.js").read_text(encoding="utf-8")
TPL = (ROOT / "src" / "template.html").read_text(encoding="utf-8")


def _extract(fn: str) -> str:
    key = f"function {fn}"
    i = JS.find(key)
    assert i >= 0, fn
    j = JS.find("\nfunction ", i + 1)
    return JS[i:j if j >= 0 else None]


def test_bandeau_quatre_chiffres_euros():
    mens = _extract("bdgMensuelHtml")
    assert "bdg-kvs-simple" in mens
    assert "bdgMoyKv('Revenus'" in mens
    assert "bdgMoyKv('Dépenses'" in mens
    assert "bdgMoyKv('Manque / mois'" in mens
    assert "réduire de ${bdgAmtEuro(red.eur)}/mois" in mens
    assert "Base prudente, hors Air Glow." in mens
    # dollars absents du bandeau visible (restent dans le détail)
    visible = mens.split("const kvDetail")[0]
    assert "total_moyenne_usd" in visible  # passé à bdgMoyKv mais
    assert "true)}" in visible  # euroOnly
    assert "Voir le détail" in mens
    assert 'data-bdg-fold-default="closed"' in mens
    assert "mensuel-plus" in mens
    # le texte long et Air Glow ne sont plus dans le bandeau visible
    assert "Il te manque" in mens  # conservé dans le détail
    assert visible.count("Il te manque") == 0 or "kvDetail" in mens
    avant_detail = mens.split("kvDetail")[0]
    assert "Air Glow, frais de fonctionnement" not in avant_detail
    assert "Mois de sécurité" not in avant_detail
    assert "France Travail" not in avant_detail
    assert "Revenus réels" not in avant_detail
    assert "Air Glow, frais de fonctionnement" in mens
    assert "Mois de sécurité" in mens


def test_comptes_trois_colonnes_sans_dollars():
    cpt = _extract("bdgComptesHtml")
    assert "bdgHeadSimple" in cpt
    assert "bdgRowSimple" in cpt
    assert "Ce mois" in JS
    assert "function bdgHeadSimple" in JS
    # en-tête réduit
    header = cpt.split("bdg-table-simple")[0]
    assert "Dépenses" in header and "Revenus" in header and "Reste" in header
    assert "Salaire Tesla" not in header
    assert "Charges fixes crédit" not in header
    assert "depenses_usd" not in header
    # lignes vides masquées
    assert "if(zeroEmpty) return '';" in cpt
    # virements hors tableau principal
    assert "c.id!=='virements_internes'" in cpt
    assert "Épargne et virements internes" in cpt
    assert "ce n’est pas une dépense" in cpt or "ce n'est pas une dépense" in cpt
    # tickets repliés
    lidl = _extract("bdgLidlBlock")
    assert 'data-bdg-fold-default="closed"' in lidl
    # Air Glow reste une seule ligne, hors dépenses
    assert "bdg-comptes-airglow" in cpt
    assert cpt.count("Air Glow") >= 1
    # pas de paragraphes de source sous les totaux
    assert "Source :" not in cpt
    assert "charges_fixes_credit_note" not in cpt
    # Grok Heavy jamais proposé comme économie dans l'UI budget
    assert "Grok Heavy" not in cpt


def test_css_simple_et_mobile():
    assert ".bdg-kvs-simple" in TPL
    assert ".bdg-th-simple" in TPL
    assert ".bdg-row-simple" in TPL
    assert ".bdg-annex-line" in TPL
    # les 3 colonnes restent visibles sur mobile
    assert "bdg-row-simple > :nth-child(2)" in TPL
    assert "bdg-row-simple > :nth-child(3)" in TPL


def test_calculs_non_modifies_dans_le_js():
    # on n'invente pas de nouveaux montants : les chiffres viennent toujours des données
    assert "objectif_reduction_autres_postes" in JS
    assert "capacite_actuelle" in JS
    assert "depenses_recurrentes" in JS


def test_periode_octobre_uniquement():
    """La page Budget et le bouton n'affichent plus novembre."""
    assert "Budget · Octobre" in JS
    assert "Budget — Octobre 2026" in JS
    assert "Lidl (octobre et novembre au 24)" not in JS
    assert "Tickets Lidl, octobre 2026" in JS
    assert "const hasNov=false;" in JS
    lidl = _extract("bdgLidlBlock")
    assert "novembre au 24" not in lidl
    mens = _extract("bdgMensuelHtml")
    assert "Novembre au 25 (hors moyenne)" not in mens
    assert "WordPress 134,60" not in mens
    assert "Novembre, pour information seulement" not in mens
