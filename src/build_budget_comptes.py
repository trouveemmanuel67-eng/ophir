#!/usr/bin/env python3
"""Construit le relevé perso et le bloc fusionné « Comptes » (joint + perso).

Ne modifie pas data/budget/compte_joint_2026-10.json (corrections Apple / Koch /
Air Glow / Deblock et emplacement Lidl conservés tels quels).
"""
from __future__ import annotations

import json
import re
from collections import defaultdict
from copy import deepcopy
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "budget"
JOINT = DATA / "compte_joint_2026-10.json"
OPS_RAW = Path("/tmp/ops_raw.json")
FX = 1.0944

CAT_DEFS = [
    ("logement", "Logement / loyer", True),
    ("energie", "Énergie", True),
    ("courses", "Courses", True),
    ("transport", "Transport / carburant", True),
    ("credit_revolut", "Crédit Revolut (remboursement)", True),
    ("assurances", "Assurances / mutuelle", True),
    ("telecom", "Télécom / internet", True),
    ("abonnements", "Abonnements", True),
    ("sante", "Santé", True),
    ("enfant", "Enfant / école", True),
    ("loisirs", "Loisirs / restaurants", True),
    ("achats", "Achats", True),
    ("banque", "Banque / frais", True),
    ("impots", "Impôts", True),
    ("virements_internes", "Virements internes / épargne / investissement", False),
    ("retraits", "Retraits", True),
    ("autres", "Autres", True),
    ("air_glow", "Air Glow, frais de fonctionnement", False),
]
CAT_LIB = {i: p for i, p, _ in CAT_DEFS}
IN_DEP = {i: d for i, _, d in CAT_DEFS}


def r2(x, n=2):
    if x is None:
        return None
    return round(float(x) + 1e-12, n)


def usd(eur):
    if eur in (None, ""):
        return None
    return r2(float(eur) * FX)


def clean_text(s):
    if not s:
        return s
    return s.replace("&#39;", "'").replace("&amp;", "&")


def src_lib(compte):
    return {
        "joint": "joint",
        "perso": "perso",
        "shana": "Shana",
        "depot": "dépôt",
        "perso/joint": "perso / joint",
        "joint/shana": "joint / Shana",
        "perso/shana": "perso / Shana",
        "perso/depot": "perso / dépôt",
    }.get(compte, compte or "")


def base_op(o, **extra):
    rec = {
        "date": o["date"],
        "date_libelle": o.get("date_libelle") or o["date"],
        "libelle": clean_text(o["libelle"]),
        "details": [clean_text(x) for x in (o.get("details") or [])],
        "sens": o["sens"],
        "montant_eur": r2(o["montant_eur"]),
        "montant_usd": usd(o["montant_eur"]),
        "solde_apres_eur": o.get("solde_apres_eur"),
        "page": o.get("page"),
        "statut": o.get("statut") or "comptable",
    }
    if o.get("fx_usd") is not None:
        rec["devise_origine"] = {"montant": o["fx_usd"], "devise": "USD"}
    if o.get("fx_note"):
        rec["details"] = rec["details"] + [o["fx_note"]] if o["fx_note"] not in rec["details"] else rec["details"]
    rec.update(extra)
    return rec


# ---------- classification perso ----------
def classify_perso(raw):
    lib = clean_text(raw["libelle"])
    det = " ".join(raw.get("details") or [])
    prod = raw["produit"]
    sens = raw["sens"]
    amt = raw["montant_eur"]
    notes = []
    ambigu = None
    rename = None
    sous = None
    typ = "depense"
    cat = None

    if prod == "depot":
        if sens == "credit" and amt is not None and amt < 2 and "Intérêts" in lib:
            cat, typ = "revenus", "revenus"
            notes.append("Intérêts nets du compte d'épargne Revolut.")
        else:
            cat, typ = "virements_internes" if sens == "debit" else "virements_internes_entrants", "virement_interne"
            notes.append("Mouvement entre le compte courant perso et le dépôt / épargne Revolut.")
        return cat, typ, rename, sous, notes, ambigu

    if prod == "shana":
        if sens == "credit" and lib.startswith("Virement de"):
            cat, typ = "virements_internes_entrants", "virement_interne"
            notes.append("Alimentation de la poche Shana (non un revenu).")
        elif lib == "Roblox":
            cat, typ = "enfant", "depense"
        elif lib == "Shein":
            cat, typ = "achats", "depense"
            notes.append("Shein (vêtements), carte de la poche Shana.")
        elif lib == "Carrefour":
            cat, typ = "courses", "depense"
        else:
            cat, typ = "autres", "depense"
            ambigu = {
                "sujet": lib,
                "montant_eur": amt,
                "classification": "autres",
                "question": f"Opération sur la poche Shana ({lib}) : confirmer la catégorie ?",
            }
        return cat, typ, rename, sous, notes, ambigu

    # compte courant Emmanuel
    if sens == "credit":
        if "TESLA FRANCE" in lib:
            cat, typ = "revenus", "revenus"
            m = re.search(r"Salary (\d+)", det)
            periode = m.group(1) if m else ""
            notes.append(
                f"Salaire Tesla France (réf. Salary {periode}). Compté en revenu réel du foyer. "
                "Emmanuel transfere ensuite vers le compte joint ou vers l'investissement."
            )
        elif "FRANCE TRAVAIL" in lib:
            cat, typ = "revenus", "revenus"
        elif "DGFIP" in lib:
            cat, typ = "enfant", "remboursement_categorie"
            rename = "Photo de classe (Collège Foch)"
            notes.append(
                "Versement DGFIP (réf. COLLEGE FOCH), confirmé par Emmanuel le 25/11/2026 : photo de classe. "
                "Classé dans Enfant, libellé « Photo de classe (Collège Foch) ». "
                "Crédit sur le relevé (36,35 €) : il réduit le net de la catégorie Enfant ; ce n'est pas un revenu."
            )
        elif "AON FRANCE" in lib:
            cat, typ = "remboursements", "remboursements"
            notes.append("Aon France, complément sécurité sociale (mutuelle). À rapprocher des soins dentaires Dr Koch. Non inclus dans les revenus.")
        elif lib == "Personal loan":
            cat, typ = "financement", "financement_entrant"
            notes.append(
                "Crédit Revolut 23 500 € (confirmé par Emmanuel le 25/11/2026). "
                "Ce n'est ni un revenu ni une dépense. Mensualité 169,60 € (libellé « repayment »). "
                "Le jour même, 23 434,34 € sont virés vers FR7610278010100002262220176 (transfert interne, pas une dépense)."
            )
        elif "FRANCKY VETSCH" in lib:
            cat, typ = "remboursements", "remboursements"
            rename = "Remboursement Red Bull (Francky Vetsch)"
            notes.append(
                "Virement de 2,00 € d'un collègue, remboursement d'un Red Bull. "
                "Confirmé par Emmanuel le 25/11/2026. Classé en remboursement : ce n'est ni une dépense ni un revenu."
            )
        elif "Apple Pay" in lib:
            cat, typ = "virements_internes_entrants", "virement_interne"
            m_card = re.search(r"\*(\d+)", lib)
            suffix = m_card.group(0) if m_card else ""
            rename = f"Investissement XTB (Apple Pay {suffix})".replace("  ", " ").strip()
            notes.append(
                "Recharge Apple Pay, confirmée par Emmanuel le 25/11/2026 : "
                "transfert de Revolut vers XTB pour acheter des actions. "
                "Virement interne / investissement (XTB), exclu des dépenses et des revenus."
            )
        elif "XTB" in lib:
            cat, typ = "virements_internes_entrants", "virement_interne"
            notes.append("Retour depuis XTB (courtier). Transfert interne, pas un revenu.")
        elif "Digital Assets" in lib:
            cat, typ = "virements_internes_entrants", "virement_interne"
            notes.append("Transfert depuis Revolut Digital Assets (crypto).")
        elif "investment account" in det.lower() or (lib == "Recharge" and "investment" in det.lower()):
            cat, typ = "virements_internes_entrants", "virement_interne"
            notes.append("Recharge depuis le compte d'investissement Revolut.")
        elif "Compte d'épargne" in lib or "Compte d'epargne" in lib:
            cat, typ = "virements_internes_entrants", "virement_interne"
            notes.append("Retour depuis le compte d'épargne Revolut.")
        elif "M OU MME EMMANUEL TROUVE" in lib:
            cat, typ = "virements_internes_entrants", "virement_interne"
            notes.append("Virement depuis un compte à son nom (M ou Mme Emmanuel Trouvé). Pas un revenu.")
        elif lib.startswith("Virement de : EMMANUEL TROUVE"):
            cat, typ = "virements_internes_entrants", "virement_interne"
            notes.append("Virement depuis le compte joint. Pas un revenu (évite le double compte avec le joint).")
        elif lib in ("Change en EUR", "Exchanged to EUR"):
            cat, typ = "virements_internes_entrants", "virement_interne"
            notes.append("Change de devise vers l'euro (poche interne Revolut). Pas un revenu.")
        else:
            cat, typ = "a_confirmer_credit", "a_confirmer"
            ambigu = {
                "sujet": lib,
                "montant_eur": amt,
                "classification": "à confirmer (non inclus dans les revenus)",
                "question": "Nature de ce crédit ?",
            }
        return cat, typ, rename, sous, notes, ambigu

    # debits
    if lib.startswith("Virement à : EMMANUEL TROUVE & PRISCILLA"):
        cat, typ = "virements_internes", "virement_interne"
        notes.append("Virement vers le compte joint. Exclu des dépenses ; n'est pas un revenu du joint.")
    elif lib.startswith("Virement à : Shana"):
        cat, typ = "virements_internes", "virement_interne"
        notes.append("Virement vers la poche Shana. Les dépenses carte de Shana sont comptées à part (pas de double compte).")
    elif "margin trading" in lib.lower():
        cat, typ = "virements_internes", "virement_interne"
        notes.append("Vers le compte de trading / marge Revolut (investissement).")
    elif "compte d'investissement" in lib.lower():
        cat, typ = "virements_internes", "virement_interne"
        notes.append("Vers le compte d'investissement Revolut.")
    elif lib in ("Xtb", "To Xtb") or lib.startswith("To Xtb"):
        cat, typ = "virements_internes", "virement_interne"
        notes.append("Vers le courtier XTB (investissement).")
    elif "Revolut X" in lib:
        cat, typ = "virements_internes", "virement_interne"
        notes.append("Vers Revolut X (investissement / crypto).")
    elif "Compte d'épargne" in lib:
        cat, typ = "virements_internes", "virement_interne"
        notes.append("Vers le compte d'épargne Revolut.")
    elif lib.startswith("To Emmanuel Trouvé") or lib.startswith("To Emmanuel Trouve"):
        cat, typ = "virements_internes", "virement_interne"
        if raw.get("date") == "2026-11-06" and amt in (23430.0, 4.34):
            notes.append(
                "Versement du capital du crédit Revolut 23 500 € vers FR7610278010100002262220176 "
                "(23 430,00 € + 4,34 € = 23 434,34 €). Confirmé par Emmanuel le 25/11/2026 : "
                "ce n'est ni un revenu ni une dépense. La mensualité est 169,60 €."
            )
        else:
            notes.append("Virement vers le compte FR7610278010100002262220176 à son nom. Transfert interne, pas une dépense.")
    elif lib.startswith("Change en") or lib.startswith("Exchanged to"):
        cat, typ = "virements_internes", "virement_interne"
        if lib in ("Change en XPT", "Change en XAG", "Change en XPD", "Change en XAU"):
            metal = {"XPT": "platine", "XAG": "argent", "XPD": "palladium", "XAU": "or"}[lib.split()[-1]]
            notes.append(f"Achat de {metal} (métaux Revolut). Investissement, exclu des dépenses personnelles.")
        else:
            notes.append("Change de devise (poche interne Revolut). Pas une dépense de consommation.")
    elif lib == "Cofica Bail":
        cat, typ = "transport", "depense"
        rename = "LOA Tesla (Cofica Bail)"
        notes.append("LOA de la Tesla (Cofica Bail), 486,32 € par mois. Confirmé par Emmanuel le 25/11/2026. Charge fixe, catégorie Transport.")
    elif "Free Telecom" in lib:
        cat, typ = "telecom", "depense"
        notes.append("Free Haut Débit.")
    elif "abonnement Ultra" in lib:
        cat, typ = "abonnements", "depense"
        notes.append("Abonnement Revolut Ultra.")
    elif lib == "repayment":
        cat, typ = "credit_revolut", "depense"
        rename = "Crédit Revolut (remboursement)"
        notes.append(
            "Mensualité du crédit Revolut 23 500 € (169,60 €). Confirmé par Emmanuel le 25/11/2026. "
            "Catégorie « Crédit Revolut (remboursement) », charge fixe."
        )
    elif lib in ("Netflix", "Disney+", "YouTube"):
        cat, typ = "abonnements", "depense"
    elif "Bastos" in lib:
        cat, typ = "loisirs", "depense"
        rename = "Cadeau / pot de naissance (travail)"
        notes.append("Pot de naissance au travail (PayPal *bastos_67). Confirmé par Emmanuel le 25/11/2026. Catégorie Loisirs.")
    else:
        cat, typ = "autres", "depense"
        ambigu = {
            "sujet": lib,
            "montant_eur": amt,
            "classification": "autres",
            "question": "Confirmer la catégorie de cette opération du compte perso ?",
        }
    return cat, typ, rename, sous, notes, ambigu


NOV_JOINT_MAP = {
    "Virement à : EMMANUEL TROUVE": ("virements_internes", "virement_interne", None, None, "Virement vers un compte à son nom. Transfert interne, pas une dépense.", None),
    "Virement de : EMMANUEL TROUVE": ("virements_internes_entrants", "virement_interne", None, None, "Alimentation du compte joint depuis un compte à son nom. Pas un revenu.", None),
    "Decathlon": ("achats", "depense", None, None, None, None),
    "Amazon": ("achats", "depense", None, None, None, None),
    "Fonds Logt Intermediaire-fonds De Logement": ("logement", "depense", None, None, None, None),
    "Lidl": ("courses", "depense", None, None, None, None),
    "Apple": ("abonnements", "depense", None, None, "Facture Apple.com/bill. Les crédits Apple du même mois sont déduits du net Abonnements.", None),
    "Carrefour": ("courses", "depense", None, None, None, None),
    "Temu": ("achats", "depense", None, None, None, None),
    "WordPress": ("air_glow", "depense_pro", None, None, "WordPress — frais de fonctionnement Air Glow, regroupé sur la ligne unique, hors dépenses personnelles.", None),
    "Dr Eric Koch": ("sante", "depense", "Dentiste (Dr Koch)", "dentaire", "Dentiste (Dr Eric Koch, Strasbourg). Remboursement mutuelle Aon à vérifier (des versements Aon « complément sécurité sociale » apparaissent sur le compte perso en novembre).", None),
    "Karllagerfeld Outletro": ("achats", "depense", None, None, "Karl Lagerfeld outlet, Roppenheim.", None),
    "Axa": ("assurances", "depense", None, None, None, None),
    "MailPoet": ("air_glow", "depense_pro", None, None, "MailPoet — abonnement annuel pour la publicité Air Glow. Confirmé par Emmanuel le 25/11/2026. Catégorie « Air Glow, frais de fonctionnement », exclu des dépenses personnelles.", None),
    "Tradingview": ("abonnements", "depense", None, None, "Prélèvement TradingView (Premium 83,94 €). Déjà suivi à part dans le bloc courtage (objectif Essential annuel).", None),
    "Free": ("telecom", "depense", None, None, "Free Mobile.", None),
    "L'Onglery des Tanneurs": ("loisirs", "depense", None, None, "Institut d'ongles, Strasbourg.", None),
    "McDonald's": ("loisirs", "depense", None, None, None, None),
    "Facebook": ("air_glow", "depense_pro", None, None, "Publicité Facebook / Meta — frais de fonctionnement Air Glow, hors dépenses personnelles.", None),
    "Monoprix": ("courses", "depense", None, None, None, None),
    "Cb Nx000018": ("autres", "depense", None, None, "Libellé tronqué (Cb Nx000018, Strasbourg).",
                    {"sujet": "Cb Nx000018 28,85 € (Strasbourg, 15/11)", "montant_eur": 28.85, "classification": "autres", "question": "Commerçant exact ?",}),
    "Thai S": ("loisirs", "depense", None, None, "Restaurant.", None),
    "Fritz Schmitt": ("courses", "depense", "Vin, confiture, tire-bouchon (Fritz Schmitt)", None,
                      "Vin, confiture et tire-bouchon chez Fritz Schmitt, Ottrott. Confirmé par Emmanuel le 25/11/2026. Catégorie Courses.", None),
    "Snack Cicek": ("loisirs", "depense", None, None, None, None),
    "Normal": ("achats", "depense", None, None, "Normal Strasbourg (hygiène / bazar).", None),
    "CTS": ("transport", "depense", None, None, None, None),
    "Virement à : Shana Trouve": ("virements_internes", "virement_interne", None, None, "Virement vers la poche Shana. Les dépenses carte de Shana sont comptées à part (pas de double compte).", None),
    "Dualhook": ("air_glow", "depense_pro", None, None, "Dualhook.com — publicité Air Glow. Confirmé par Emmanuel le 25/11/2026. Catégorie « Air Glow, frais de fonctionnement », exclu des dépenses personnelles.", None),
    "IKA": ("courses", "depense", None, None, None, None),
    "Microsoft": ("abonnements", "depense", None, None, None, None),
    "Les Ciseaux D Or": ("loisirs", "depense", None, None, "Coiffeur, Strasbourg.", None),
    "Le Kleber": ("loisirs", "depense", None, None, "Le Kléber, Strasbourg (restauration).", None),
    "Stein Pâtisseries & Café": ("loisirs", "depense", None, None, None, None),
    "Librairie Kléber": ("achats", "depense", None, None, None, None),
    "Paiement envoyé par FRANCE TRAVAIL GRAND EST": ("revenus", "revenus", None, None, "Allocation France Travail Grand Est. Revenu réel du foyer.", None),
    "Recharge sur Apple Pay via *0225": ("virements_internes_entrants", "virement_interne", "Investissement XTB (Apple Pay *0225)", None,
                                         "Recharge Apple Pay, confirmée par Emmanuel le 25/11/2026 : transfert de Revolut vers XTB pour acheter des actions. Virement interne / investissement (XTB), exclu des dépenses et des revenus.", None),
    "Paiement envoyé par M OU MME EMMANUEL TROUVE": ("virements_internes_entrants", "virement_interne", None, None, "Solde de clôture du compte FR7610278010100002262220176. Transfert interne, pas un revenu.", None),
    "E.Leclerc": ("courses", "depense", None, None, None, None),
}


def corridor_of(op):
    """Identifie un couloir de transfert interne inter-comptes, pour dédoublonner."""
    lib = op["libelle"]
    compte = op.get("compte")
    sens = op["sens"]
    if compte == "perso" and sens == "debit" and lib.startswith("Virement à : EMMANUEL TROUVE & PRISCILLA"):
        return "perso_to_joint"
    if compte == "joint" and sens == "credit" and lib.startswith("Virement de : EMMANUEL TROUVE"):
        return "perso_to_joint"
    if compte == "joint" and sens == "debit" and lib.startswith("Virement à : EMMANUEL TROUVE") and "PRISCILLA" not in lib and "Shana" not in lib:
        # "Virement à : EMMANUEL TROUVE" (pas le joint)
        return "joint_to_perso"
    if compte == "perso" and sens == "credit" and lib.startswith("Virement de : EMMANUEL TROUVE & PRISCILLA"):
        return "joint_to_perso"
    if compte == "perso" and sens == "debit" and lib.startswith("Virement à : Shana"):
        return "perso_to_shana"
    if compte == "shana" and sens == "credit" and lib.startswith("Virement de : EMMANUEL TROUVE") and "PRISCILLA" not in lib:
        return "perso_to_shana"
    if compte == "joint" and sens == "debit" and "Shana" in lib:
        return "joint_to_shana"
    if compte == "shana" and sens == "credit" and "PRISCILLA" in lib:
        return "joint_to_shana"
    if compte == "perso" and sens == "debit" and "À EUR Compte d'épargne" == lib:
        return "perso_to_depot"
    if compte == "depot" and sens == "credit" and "À EUR Compte d'épargne" == lib:
        return "perso_to_depot"
    if compte == "perso" and sens == "credit" and "À partir de EUR Compte d'épargne" == lib:
        return "depot_to_perso"
    if compte == "depot" and sens == "debit" and "À partir de EUR Compte d'épargne" == lib:
        return "depot_to_perso"
    return None


def match_compte_label(corridor):
    return {
        "perso_to_joint": "perso/joint",
        "joint_to_perso": "perso/joint",
        "perso_to_shana": "perso/shana",
        "joint_to_shana": "joint/shana",
        "perso_to_depot": "perso/depot",
        "depot_to_perso": "perso/depot",
    }[corridor]


def enrich(op, cat, typ, compte, rename=None, sous=None, notes=None, libelle_releve=None):
    rec = deepcopy(op) if "categorie" not in op or extra_needed(op) else deepcopy(op)
    # always build consistently
    rec = {
        "date": op["date"],
        "date_libelle": op.get("date_libelle") or op["date"],
        "libelle": rename or op["libelle"],
        "details": list(op.get("details") or []),
        "sens": op["sens"],
        "montant_eur": r2(op["montant_eur"]),
        "montant_usd": usd(op["montant_eur"]),
        "solde_apres_eur": op.get("solde_apres_eur"),
        "categorie": cat,
        "categorie_libelle": (
            "Santé / dentaire" if sous == "dentaire" else
            CAT_LIB.get(cat, typ)
        ),
        "type": typ,
        "page": op.get("page"),
        "statut": op.get("statut") or "comptable",
        "compte": compte,
        "compte_libelle": src_lib(compte),
    }
    if op.get("devise_origine"):
        rec["devise_origine"] = op["devise_origine"]
    if op.get("fx_usd") is not None and "devise_origine" not in rec:
        rec["devise_origine"] = {"montant": op["fx_usd"], "devise": "USD"}
    if notes:
        rec["note_classification"] = " ".join(notes) if isinstance(notes, list) else notes
    if sous:
        rec["sous_categorie"] = sous
    if libelle_releve:
        rec["libelle_releve"] = libelle_releve
    elif rename and rename != op["libelle"]:
        rec["libelle_releve"] = op["libelle"]
    # preserve existing notes from joint october if any and we didn't set one
    if not rec.get("note_classification") and op.get("note_classification"):
        rec["note_classification"] = op["note_classification"]
    if op.get("libelle_releve") and "libelle_releve" not in rec:
        rec["libelle_releve"] = op["libelle_releve"]
    if op.get("sous_categorie") and "sous_categorie" not in rec:
        rec["sous_categorie"] = op["sous_categorie"]
    return rec


def extra_needed(op):
    return True


def build():
    joint = json.loads(JOINT.read_text(encoding="utf-8"))
    raw_ops = json.loads(OPS_RAW.read_text(encoding="utf-8"))
    ambigues = []
    perso_all = []  # categorized perso/shana/depot
    seen_ambigu_keys = set()

    def add_ambigu(a):
        if not a:
            return
        key = (a.get("sujet"), r2(a.get("montant_eur")))
        if key in seen_ambigu_keys:
            return
        seen_ambigu_keys.add(key)
        ambigues.append(a)

    # --- perso ops ---
    for raw in raw_ops:
        cat, typ, rename, sous, notes, ambigu = classify_perso(raw)
        add_ambigu(ambigu)
        compte = {"compte_courant": "perso", "shana": "shana", "depot": "depot"}[raw["produit"]]
        rec = enrich(base_op(raw), cat, typ, compte, rename=rename, sous=sous, notes=notes)
        rec["produit"] = raw["produit"]
        perso_all.append(rec)

    # --- joint October (keep classifications, except Shana transfer → internal) ---
    joint_ops = []
    for c in joint["categories"]:
        for o in c.get("operations") or []:
            oo = deepcopy(o)
            cat = c["id"]
            typ = oo.get("type") or ("virement_interne" if cat == "virements_internes" else ("depense_pro" if cat == "air_glow" else "depense"))
            if oo["libelle"].startswith("Virement à : Shana"):
                cat, typ = "virements_internes", "virement_interne"
                oo["note_classification"] = (
                    "Virement du joint vers la poche Shana (80 € le 24/10). "
                    "Dans le bloc fusionné « Comptes », ce n'est plus une dépense Enfant : "
                    "les paiements carte de Shana (Roblox, courses, etc.) sont comptés à leur catégorie réelle."
                )
            rec = enrich(oo, cat, typ, "joint")
            joint_ops.append(rec)
    for o in joint.get("revenus_operations") or []:
        rec = enrich(o, "revenus", "revenus", "joint")
        joint_ops.append(rec)
    for o in joint.get("remboursements_operations") or []:
        rec = enrich(o, "remboursements", "remboursements", "joint")
        joint_ops.append(rec)
    for o in joint.get("virements_internes_entrants") or []:
        rec = enrich(o, "virements_internes_entrants", "virement_interne", "joint")
        joint_ops.append(rec)

    # --- joint November ---
    nov_ops_raw = (joint.get("operations_hors_octobre") or {}).get("operations") or []
    unmapped = []
    apple_ambigu_once = False
    mailpoet_once = False
    applepay_once = False
    for o in nov_ops_raw:
        lib = o["libelle"]
        if lib not in NOV_JOINT_MAP:
            unmapped.append(lib)
            continue
        cat, typ, rename, sous, note, ambigu = NOV_JOINT_MAP[lib]
        if lib == "Apple":
            if o.get("sens") == "credit":
                note = "Crédit Apple.com/bill — déduit du net de la catégorie Abonnements."
                ambigu = None
            elif r2(o["montant_eur"]) == 219.99:
                rename = "Grok Heavy (via Apple)"
                note = (
                    "Abonnement Grok Heavy prélevé via Apple.com/bill (219,99 € le 4/11/2026). "
                    "Confirmé par Emmanuel le 25/11/2026 : libellé « Grok Heavy (via Apple) », catégorie Abonnements."
                )
                ambigu = None
            else:
                note = "Facture Apple.com/bill. Les crédits Apple du même mois sont déduits du net Abonnements."
                ambigu = None
        if lib.startswith("Recharge sur Apple Pay"):
            if applepay_once:
                ambigu = None
            applepay_once = True
        add_ambigu(ambigu)
        if cat == "abonnements" and o.get("sens") == "credit":
            typ = "remboursement_categorie"
        rec = enrich(o, cat, typ, "joint", rename=rename, sous=sous, notes=note, libelle_releve=(lib if rename else None))
        joint_ops.append(rec)
    if unmapped:
        raise SystemExit("Libellés joint novembre non mappés : " + ", ".join(sorted(set(unmapped))))

    # keep october joint ambiguities that still apply (not Shana transfer)
    for a in joint.get("operations_ambigues") or []:
        if "Shana" in (a.get("sujet") or ""):
            continue
        add_ambigu(a)

    # --- fusion + dédoublonnage ---
    all_ops = joint_ops + perso_all
    # group transfer corridors
    buckets = defaultdict(list)
    others = []
    for op in all_ops:
        cor = corridor_of(op)
        if cor:
            key = (cor, op["date"], r2(op["montant_eur"]))
            buckets[key].append(op)
        else:
            others.append(op)

    fused = list(others)
    matched_n = 0
    unmatched_transfers = []
    for key, grp in buckets.items():
        cor, date, amt = key
        # keep one representative: prefer the outgoing (debit) side with a combined compte label
        if len(grp) == 2:
            matched_n += 1
            debit = next((x for x in grp if x["sens"] == "debit"), grp[0])
            rec = deepcopy(debit)
            rec["compte"] = match_compte_label(cor)
            rec["compte_libelle"] = src_lib(rec["compte"])
            sides = " et ".join(sorted({src_lib(x["compte"]) for x in grp}))
            extra = f"Vu sur les deux relevés ({sides}). Compté une seule fois, exclu des dépenses et des revenus."
            rec["note_classification"] = ((rec.get("note_classification") or "") + " " + extra).strip()
            rec["double_vue"] = True
            fused.append(rec)
        elif len(grp) == 1:
            # transfer seen on one side only (other account / investment / traditional bank)
            rec = deepcopy(grp[0])
            rec["double_vue"] = False
            unmatched_transfers.append(rec)
            fused.append(rec)
        else:
            # more than 2 with same date+amount+corridor — match pairwise, leftover unmatched
            debits = [x for x in grp if x["sens"] == "debit"]
            credits = [x for x in grp if x["sens"] == "credit"]
            n = min(len(debits), len(credits))
            for i in range(n):
                matched_n += 1
                rec = deepcopy(debits[i])
                rec["compte"] = match_compte_label(cor)
                rec["compte_libelle"] = src_lib(rec["compte"])
                rec["note_classification"] = ((rec.get("note_classification") or "") + " Vu sur les deux relevés. Compté une seule fois.").strip()
                rec["double_vue"] = True
                fused.append(rec)
            for x in debits[n:] + credits[n:]:
                rec = deepcopy(x)
                rec["double_vue"] = False
                unmatched_transfers.append(rec)
                fused.append(rec)

    fused.sort(key=lambda o: (o["date"], 0 if o["sens"] == "credit" else 1, o["libelle"], o["montant_eur"] or 0))

    # --- buckets for output ---
    def is_oct(o):
        return o["date"] <= "2026-10-31"
    def is_nov(o):
        return "2026-11-01" <= o["date"] <= "2026-11-25"

    # Le bloc affiché « Comptes » ne compte que le mois d'octobre (1er–31).
    # Les règles de classification (virements internes, Air Glow, etc.) restent inchangées.
    fused_all = fused
    fused = [o for o in fused_all if is_oct(o)]

    revenus_ops = [o for o in fused if o["type"] == "revenus"]
    remb_ops = [o for o in fused if o["type"] == "remboursements"]
    fin_ops = [o for o in fused if o["type"] in ("financement_entrant", "financement_sortant")]
    vin_ops = [o for o in fused if o["categorie"] == "virements_internes_entrants"]
    # a_confirmer credits not in revenus
    autre_credits = [o for o in fused if o["type"] == "a_confirmer"]

    # categories
    cats = []
    lidl_sous = None
    for c in joint["categories"]:
        if c["id"] == "courses":
            lidl_sous = deepcopy(c.get("sous_categories") or [])

    for cid, poste, in_dep in CAT_DEFS:
        ops_c = [o for o in fused if o.get("categorie") == cid]
        debit = r2(sum(o["montant_eur"] for o in ops_c if o["sens"] == "debit")) or 0.0
        credit = r2(sum(o["montant_eur"] for o in ops_c if o["sens"] == "credit")) or 0.0
        observe = r2(debit - credit) or 0.0
        rec = {
            "id": cid,
            "poste": poste,
            "n_operations": len(ops_c),
            "debit_eur": debit,
            "credit_eur": credit,
            "observe_eur": observe,
            "observe_usd": usd(observe),
            "projection_eur": observe,
            "projection_usd": usd(observe),
            "objectif": None,
            "compte_dans_total_depenses": in_dep,
            "operations": ops_c,
            "detail": detail_cat(cid, ops_c, debit, credit, observe),
        }
        if cid == "courses":
            rec["sous_categories"] = lidl_sous or []
            rec["commercants"] = []
        cats.append(rec)

    dep = r2(sum(c["observe_eur"] for c in cats if c["compte_dans_total_depenses"])) or 0.0
    rev = r2(sum(o["montant_eur"] for o in revenus_ops if o["sens"] == "credit")) or 0.0
    remb = r2(sum(o["montant_eur"] for o in remb_ops if o["sens"] == "credit")) or 0.0
    glow = next(c for c in cats if c["id"] == "air_glow")
    intern_out = next(c for c in cats if c["id"] == "virements_internes")
    vin_tot = r2(sum(o["montant_eur"] for o in vin_ops if o["sens"] == "credit")) or 0.0
    reste = r2(rev - dep)
    salaire_ops = [o for o in revenus_ops if "TESLA" in o["libelle"].upper() or "Salaire" in (o.get("note_classification") or "")]
    # more reliable:
    salaire_ops = [o for o in revenus_ops if "TESLA" in o["libelle"].upper()]
    salaire = r2(sum(o["montant_eur"] for o in salaire_ops)) or 0.0
    ft_ops = [o for o in revenus_ops if "FRANCE TRAVAIL" in o["libelle"].upper()]
    ft = r2(sum(o["montant_eur"] for o in ft_ops)) or 0.0
    interets_ops = [o for o in revenus_ops if "Intérêts" in o["libelle"] or "interets" in o["libelle"].lower()]
    interets = r2(sum(o["montant_eur"] for o in interets_ops)) or 0.0
    pret = r2(sum(o["montant_eur"] for o in fin_ops if o["type"] == "financement_entrant")) or 0.0
    remb_emp = r2(sum(o["montant_eur"] for o in fin_ops if o["type"] == "financement_sortant")) or 0.0

    def vi_group(o):
        lib = o["libelle"]
        cpt = o.get("compte") or ""
        det = " ".join(o.get("details") or [])
        if cpt in ("perso/joint",) or ("PRISCILLA" in lib and "Shana" not in lib):
            return "entre_joint_et_perso"
        if "Shana" in lib or cpt in ("perso/shana", "joint/shana"):
            return "poche_shana"
        if "épargne" in lib.lower() or "epargne" in lib.lower() or cpt == "perso/depot":
            return "epargne"
        if (
            "Xtb" in lib or "XTB" in lib or "Revolut X" in lib or "margin" in lib.lower()
            or "investissement" in lib.lower() or lib == "Deblock"
            or lib.startswith("Change en X") or "investment" in det.lower()
            or "Digital Assets" in lib
        ):
            return "investissement"
        if "Change" in lib or "Exchanged" in lib:
            return "change_devise"
        return "compte_a_son_nom"

    VI_LABELS = {
        "investissement": ("Vers l'investissement (XTB, Revolut X, marge, métaux, Deblock, compte-titres)", "Flux sortants vers les courtiers et les métaux, exclus des dépenses."),
        "compte_a_son_nom": ("Vers un compte à son nom", "Y compris le transfert du prêt personnel 23 434,34 € vers FR7610278010100002262220176, et les virements du joint vers un autre compte Emmanuel (hors ce relevé perso)."),
        "entre_joint_et_perso": ("Entre le perso et le joint", "Allers-retours dédoublonnés (une seule ligne par virement). Ni dépense, ni revenu."),
        "epargne": ("Épargne Revolut (allers-retours)", "2 000 € vers le dépôt et 2 000 € en retour ; net 0 €, plus 0,48 € d'intérêts restés sur le dépôt."),
        "change_devise": ("Change de devise", "Conversions EUR/USD internes à Revolut, pas une dépense de consommation."),
        "poche_shana": ("Alimentation de la poche Shana", "Les dépenses carte de Shana sont déjà dans Courses, Achats et Enfant."),
    }

    vi_ops_all = [o for o in fused if o.get("categorie") == "virements_internes"]
    vi_break = []
    from collections import defaultdict as _dd
    bags = _dd(float)
    bags_n = _dd(int)
    for o in vi_ops_all:
        g = vi_group(o)
        bags[g] += o["montant_eur"] if o["sens"] == "debit" else -o["montant_eur"]
        bags_n[g] += 1
    for gid, (lab, note) in VI_LABELS.items():
        if gid in bags:
            val = r2(bags[gid]) or 0.0
            vi_break.append({
                "id": gid, "libelle": lab, "note": note,
                "n": bags_n[gid], "montant_eur": val, "montant_usd": usd(val),
            })

    # monthly splits for transparency (crédits de catégorie déduits, y compris Apple)
    def slice_tot(pred):
        ops_m = [o for o in fused_all if pred(o)]
        dep_m = r2(sum(
            (o["montant_eur"] if o["sens"] == "debit" else -o["montant_eur"])
            for o in ops_m
            if o.get("categorie") in IN_DEP and IN_DEP[o["categorie"]]
        )) or 0.0
        rev_m = r2(sum(o["montant_eur"] for o in ops_m if o["type"] == "revenus" and o["sens"] == "credit")) or 0.0
        return {"depenses_eur": dep_m, "depenses_usd": usd(dep_m), "revenus_eur": rev_m, "revenus_usd": usd(rev_m), "reste_eur": r2(rev_m - dep_m), "reste_usd": usd(r2(rev_m - dep_m))}

    credit_cat = next((c for c in cats if c["id"] == "credit_revolut"), None)
    credit_obs = (credit_cat or {}).get("observe_eur") or 0.0
    loa_mens = 486.32
    cred_mens = 169.60
    charges_fixes_mens = r2(loa_mens + cred_mens)

    apple_xtb_ops = [
        o for o in vin_ops
        if "Apple Pay" in (o.get("libelle") or "") or "Apple Pay" in (o.get("libelle_releve") or "")
    ]
    apple_xtb_eur = r2(sum(o["montant_eur"] for o in apple_xtb_ops if o.get("sens") == "credit")) or 0.0
    if apple_xtb_ops:
        vi_break.append({
            "id": "investissement_xtb_apple_pay",
            "libelle": "Investissement XTB (Apple Pay)",
            "note": (
                "Recharges Apple Pay 86 € + 650 € + 270 € = 1 006 €, confirmées par Emmanuel le 25/11/2026 : "
                "transferts de Revolut vers XTB pour acheter des actions. "
                "Virements internes / investissement (XTB), exclus des dépenses et des revenus. "
                "Montant constaté en entrées sur les comptes Revolut, non additionné aux virements sortants déjà partis vers les courtiers."
            ),
            "n": len(apple_xtb_ops),
            "montant_eur": apple_xtb_eur,
            "montant_usd": usd(apple_xtb_eur),
        })
    inv_out_eur = next((d["montant_eur"] for d in vi_break if d["id"] == "investissement"), 0.0) or 0.0

    totaux = {
        "depenses_eur": dep,
        "depenses_usd": usd(dep),
        "depenses_note": (
            "Somme nette des catégories de dépenses personnelles des deux comptes "
            "(virements internes, épargne, investissement, capital du crédit Revolut, remboursements d'assurance et la ligne Air Glow, frais de fonctionnement exclus). "
            "Les virements perso → joint (et l'inverse) ne sont comptés qu'une fois, et uniquement en transferts internes. "
            "Les crédits Apple.com/bill du même mois sont déduits des Abonnements."
        ),
        "revenus_eur": rev,
        "revenus_usd": usd(rev),
        "revenus_detail": (
            "Salaire Tesla France {salaire:.2f} € (22/10, réf. Salary 102026) "
            "+ France Travail Grand Est {ft:.2f} € (1/10)".format(salaire=salaire, ft=ft)
            + (f" + intérêts d'épargne Revolut {interets:.2f} €" if interets else "")
            + ". Les virements entre comptes, le prêt personnel, les alimentations Apple Pay destinées à l'investissement XTB et les remboursements d'assurance ne sont pas des revenus."
        ),
        "salaire_eur": salaire,
        "salaire_usd": usd(salaire),
        "france_travail_eur": ft,
        "france_travail_usd": usd(ft),
        "interets_epargne_eur": interets,
        "interets_epargne_usd": usd(interets),
        "remboursements_eur": remb,
        "remboursements_usd": usd(remb),
        "remboursements_note": (
            "Remboursements présentés à part, non inclus dans les revenus ni déduits des cotisations du mois : "
            "AXA 126,86 € (joint, 30/10, période 26/06–26/08) ; "
            "Aon France complément sécurité sociale 423,44 € (perso, novembre, à rapprocher des soins Dr Koch) ; "
            "Francky Vetsch 2,00 € (perso, 9/11, remboursement d'un Red Bull par un collègue, confirmé le 25/11/2026)."
        ),
        "reste_eur": reste,
        "reste_usd": usd(reste),
        "reste_formule": "revenus réels (salaire Tesla + France Travail + intérêts d'épargne) − dépenses personnelles (hors virements internes / épargne / investissement, hors Air Glow, frais de fonctionnement, hors capital du crédit Revolut, hors remboursements d'assurance)",
        "virements_internes_entrants_eur": vin_tot,
        "virements_internes_entrants_usd": usd(vin_tot),
        "virements_internes_sortants_eur": intern_out["observe_eur"],
        "virements_internes_sortants_usd": intern_out["observe_usd"],
        "air_glow_eur": glow["observe_eur"],
        "air_glow_usd": glow["observe_usd"],
        "air_glow_note": (
            f"Ligne unique « Air Glow, frais de fonctionnement » : {glow['observe_eur']:.2f} €, {glow['n_operations']} opérations "
            "(WordPress, publicité Facebook, MailPoet, Dualhook, X Ads, Envato, INPI, CCI). "
            "Exclue des dépenses personnelles. Mollie « Thood Franc… » à Roppenheim reste dans les Achats "
            "(commerçant physique non identifié comme frais pro Air Glow)."
        ),
        "air_glow_pub_eur": glow["observe_eur"],
        "air_glow_pub_usd": glow["observe_usd"],
        "air_glow_pub_note": (
            f"Ligne unique « Air Glow, frais de fonctionnement » : {glow['observe_eur']:.2f} €, {glow['n_operations']} opérations "
            "(WordPress, publicité Facebook, MailPoet, Dualhook, X Ads, Envato, INPI, CCI). "
            "Exclue des dépenses personnelles."
        ),

        "emprunt_entrant_eur": pret,
        "emprunt_entrant_usd": usd(pret),
        "remboursements_emprunt_eur": remb_emp,
        "remboursements_emprunt_usd": usd(remb_emp),
        "financement_note": (
            "Crédit Revolut 23 500 € le 6/11 (confirmé par Emmanuel le 25/11/2026) : ce n'est ni un revenu ni une dépense. "
            "Le capital (23 434,34 €) est viré le jour même vers FR7610278010100002262220176 (transfert interne). "
            "La mensualité de 169,60 € figure dans la catégorie « Crédit Revolut (remboursement) »."
        ),
        "octobre": slice_tot(is_oct),
        "novembre_1_25": slice_tot(is_nov),
        "n_operations_fusionnees": len(fused),
        "n_transferts_dedoublonnes": matched_n,
        "virements_internes_detail": vi_break,
        "investissement_eur": inv_out_eur,
        "investissement_usd": usd(inv_out_eur),
        "investissement_xtb_apple_pay_eur": apple_xtb_eur,
        "investissement_xtb_apple_pay_usd": usd(apple_xtb_eur),
        "investissement_note": (
            "Vers l'investissement (XTB, Revolut X, marge, métaux, Deblock, compte-titres) : "
            + f"{inv_out_eur:,.2f}".replace(",", "§").replace(".", ",").replace("§", " ")
            + " € sortants en octobre, exclus des dépenses."
            + (
                " Les recharges Apple Pay du mois, classées en virements internes / investissement XTB, "
                "ne sont ni une dépense ni un revenu, et ne sont pas additionnées aux sortants courtiers."
                if apple_xtb_eur else
                " Aucune recharge Apple Pay vers XTB n'apparaît en octobre."
            )
        ),
        "credit_revolut": {
            "libelle": "Crédit Revolut 23 500 €",
            "capital_eur": 23500.0,
            "capital_usd": usd(23500.0),
            "versement_capital_eur": 23434.34,
            "versement_capital_usd": usd(23434.34),
            "mensualite_eur": cred_mens,
            "mensualite_usd": usd(cred_mens),
            "n_echeances": (credit_cat or {}).get("n_operations") or 0,
            "echeances_eur": credit_obs,
            "echeances_usd": usd(credit_obs),
            "note": (
                "Crédit Revolut 23 500 €, confirmé par Emmanuel le 25/11/2026. "
                "Ni un revenu ni une dépense. Mensualité 169,60 €. "
                "Une échéance de 169,60 € apparaît en octobre. "
                "Le versement du capital (23 434,34 € le 6/11) est hors période."
            ),
        },
        "loa_tesla_mensualite_eur": loa_mens,
        "loa_tesla_mensualite_usd": usd(loa_mens),
        "charges_fixes_credit_mensuel_eur": charges_fixes_mens,
        "charges_fixes_credit_mensuel_usd": usd(charges_fixes_mens),
        "charges_fixes_credit_note": "Charges fixes de crédit : LOA Tesla (Cofica Bail) 486,32 €/mois + crédit Revolut 169,60 €/mois = 655,92 €/mois.",
    }

    # perso JSON
    perso_all = [o for o in perso_all if is_oct(o)]
    perso_cats = []
    for cid, poste, in_dep in CAT_DEFS:
        ops_c = [o for o in perso_all if o.get("categorie") == cid]
        debit = r2(sum(o["montant_eur"] for o in ops_c if o["sens"] == "debit")) or 0.0
        credit = r2(sum(o["montant_eur"] for o in ops_c if o["sens"] == "credit")) or 0.0
        observe = r2(debit - credit) or 0.0
        perso_cats.append({
            "id": cid, "poste": poste, "n_operations": len(ops_c),
            "debit_eur": debit, "credit_eur": credit,
            "observe_eur": observe, "observe_usd": usd(observe),
            "projection_eur": observe, "projection_usd": usd(observe),
            "objectif": None, "compte_dans_total_depenses": in_dep,
            "operations": ops_c,
            "detail": f"{len(ops_c)} opération" + ("s" if len(ops_c) != 1 else "") if ops_c else "Aucune opération sur le compte perso.",
        })
    p_rev = [o for o in perso_all if o["type"] == "revenus"]
    p_remb = [o for o in perso_all if o["type"] == "remboursements"]
    p_vin = [o for o in perso_all if o["categorie"] == "virements_internes_entrants"]
    p_fin = [o for o in perso_all if o["type"] in ("financement_entrant", "financement_sortant")]
    p_dep = r2(sum(c["observe_eur"] for c in perso_cats if c["compte_dans_total_depenses"])) or 0.0
    p_revenus = r2(sum(o["montant_eur"] for o in p_rev if o["sens"] == "credit")) or 0.0

    perso_doc = {
        "id": "compte_perso_2026-10_11",
        "titre": "Compte perso Emmanuel Trouvé, octobre 2026",
        "compte": {
            "banque": "Revolut France succursale de Revolut Bank UAB",
            "etablissement": "Revolut Bank UAB (Lituanie), succursale France, SIREN 917 420 077",
            "produit": "Compte personnel en EUR — compte courant, dépôt / épargne, poche Shana Trouve",
            "titulaires": "EMMANUEL TROUVE",
            "iban": "FR7628233000017263025964043",
            "bic": "REVOFRP2",
            "adresse": "21 A Rue Des Chasseurs, 67300 Schiltigheim, Bas-Rhin",
            "poche_shana": "Shana Trouve (compte courant rattaché au relevé)",
        },
        "source": {
            "type": "Relevé de compte PDF",
            "intitule": "Relevé EUR — compte perso Emmanuel Trouvé",
            "genere_le": "2026-11-25",
            "genere_le_libelle": "25 nov. 2026",
            "periode_releve": {
                "debut": "2026-10-01",
                "fin": "2026-11-25",
                "libelle": "du 1 octobre 2026 au 25 novembre 2026",
            },
            "extraction": "pdftotext -layout, le 25/11/2026 (Europe/Paris). Aucun montant inventé. 119 opérations du compte courant, 11 du dépôt, 29 de la poche Shana. Chemin des soldes vérifié opération par opération sur les trois produits.",
            "fourni_par": "Emmanuel Trouvé, 25/11/2026 à 13 h 15 (Europe/Paris)",
            "pages": 10,
            "note_depot": (
                "Sur le dépôt, les intérêts sont affichés nets sur les lignes (0,48 € au total). "
                "L'écart de 0,18 € entre le résumé (entrant 2 000,66 € / sortant 2 000,18 €) et la somme des lignes "
                "(entrant 2 000,48 € / sortant 2 000,00 €) correspond vraisemblablement au prélèvement fiscal sur les intérêts, "
                "non détaillé ligne à ligne. Solde de clôture cohérent : 0,48 €."
            ),
        },
        "periode": {
            "debut": "2026-10-01",
            "fin": "2026-10-31",
            "libelle": "Octobre 2026",
        },
        "soldes": {
            "courant_ouverture_eur": 45.86,
            "courant_cloture_eur": 280.43,
            "courant_sortant_eur": 52161.85,
            "courant_entrant_eur": 52396.42,
            "depot_ouverture_eur": 0.00,
            "depot_cloture_eur": 0.48,
            "depot_sortant_lignes_eur": 2000.00,
            "depot_entrant_lignes_eur": 2000.48,
            "shana_ouverture_eur": 91.80,
            "shana_cloture_eur": 34.98,
            "shana_sortant_eur": 190.10,
            "shana_entrant_eur": 133.28,
            "total_ouverture_eur": 137.66,
            "total_cloture_eur": 315.89,
            "verification": (
                "Compte courant : 45,86 + 52 396,42 − 52 161,85 = 280,43. "
                "Poche Shana : 91,80 + 133,28 − 190,10 = 34,98. "
                "Dépôt : 0,00 + 2 000,48 − 2 000,00 = 0,48 (voir note fiscale de 0,18 €). "
                "Total relevé : 137,66 + 54 530,36 − 54 352,13 = 315,89."
            ),
        },
        "fx": {"taux": FX, "paire": "EURUSD", "source": "Taux déjà utilisé sur le site APEX (plan Tesla, 25/11/2026). montant_usd = arrondi(montant_eur × 1,0944, 2)."},
        "regle_emmanuel": "Compte perso mais je transfère toujours le salaire sur le compte joint après réception ou en investissement.",
        "categories": perso_cats,
        "totaux": {
            "depenses_eur": p_dep,
            "depenses_usd": usd(p_dep),
            "revenus_eur": p_revenus,
            "revenus_usd": usd(p_revenus),
            "reste_eur": r2(p_revenus - p_dep),
            "reste_usd": usd(r2(p_revenus - p_dep)),
            "salaire_eur": r2(sum(o["montant_eur"] for o in p_rev if "TESLA" in o["libelle"].upper())),
        },
        "revenus_operations": p_rev,
        "remboursements_operations": p_remb,
        "virements_internes_entrants": p_vin,
        "financement_operations": p_fin,
        "operations_ambigues": [a for a in ambigues if "joint" not in (a.get("sujet") or "").lower() or "perso" in json.dumps(a, ensure_ascii=False).lower()],
        "operations": perso_all,
    }
    # simpler: perso ambigues = those added while classifying perso (before joint nov). We'll just store all perso-origin ones in perso file from a tag.
    # I'll recompute: ambigues collected in order; for perso file, filter those about perso/shana/depot/loan/repayment/bastos/dgfip/francky/apple pay *3356/cofica
    perso_doc["operations_ambigues"] = [a for a in ambigues if any(k in json.dumps(a, ensure_ascii=False).lower() for k in (
        "dgfip", "francky", "*3356", "poche shana"
    ))]

    comptes_doc = {
        "id": "comptes_foyer_2026-10_11",
        "titre": "Comptes",
        "periode": {
            "debut": "2026-10-01",
            "fin": "2026-10-31",
            "libelle": "Octobre 2026",
        },
        "comptes": [
            {
                "id": "joint",
                "libelle": "Compte joint",
                "titulaires": "EMMANUEL TROUVE & PRISCILLA AURORE MOONIEN",
                "iban": "FR7628233000013262519711931",
                "banque": "Revolut France succursale de Revolut Bank UAB",
                "soldes": joint.get("soldes"),
            },
            {
                "id": "perso",
                "libelle": "Compte perso",
                "titulaires": "EMMANUEL TROUVE",
                "iban": "FR7628233000017263025964043",
                "banque": "Revolut France succursale de Revolut Bank UAB",
                "soldes": perso_doc["soldes"],
            },
        ],
        "source": {
            "intitule": "Relevés Revolut EUR, compte joint et compte perso",
            "periode_releve": {"debut": "2026-10-01", "fin": "2026-11-25", "libelle": "du 1 octobre 2026 au 25 novembre 2026"},
            "genere_le": "2026-11-25",
            "genere_le_libelle": "25 nov. 2026",
            "extraction": (
                "Fusion des opérations du compte joint (data/budget/compte_joint_2026-10.json) "
                "et du compte perso. Le bloc affiché est limité au mois d'octobre 2026 (1er–31). "
                "Les corrections déjà faites sur le joint sont conservées : ligne unique Air Glow, frais de fonctionnement, Grok (via Apple), "
                "Dentiste (Dr Koch), Deblock en virement interne. "
                "Les virements perso → joint (et l'inverse) et les virements vers l'épargne / les courtiers / les métaux "
                "sont exclus des dépenses et des revenus, et dédoublonnés lorsqu'ils apparaissent sur les deux relevés. "
                "Le salaire Tesla et France Travail sont les revenus réels du foyer."
            ),
            "fx": FX,
        },
        "fx": {"taux": FX, "paire": "EURUSD", "source": "Taux déjà utilisé sur le site APEX (plan Tesla, 25/11/2026)."},
        "soldes": {
            "joint_ouverture_eur": joint["soldes"]["ouverture_eur"],
            "joint_cloture_octobre_eur": joint["soldes"]["cloture_octobre_eur"],
            "joint_cloture_releve_eur": joint["soldes"]["cloture_releve_eur"],
            "perso_ouverture_eur": 137.66,
            "perso_cloture_releve_eur": 315.89,
        },
        "categories": cats,
        "totaux": totaux,
        "revenus_operations": revenus_ops,
        "remboursements_operations": remb_ops,
        "virements_internes_entrants": vin_ops,
        "financement_operations": fin_ops,
        "credits_a_confirmer": autre_credits,
        # Le bloc affiché est limité à octobre : on retire les ambiguïtés datées de novembre.
        "operations_ambigues": [a for a in ambigues if not re.search(r"\b\d{1,2}/11(?:/2026)?\b", a.get("sujet") or "")],

        "tradingview_sur_le_releve": {
            "present_sur_le_releve": True,
            "total_eur": r2(sum(
                o["montant_eur"] for o in fused
                if o["libelle"] == "Tradingview" and o["sens"] == "debit"
            )),
            "note": (
                "Un prélèvement TradingView Premium de 83,94 € figure sur le compte joint le 7/10. "
                "Il reste dans Abonnements. Il n'est pas recopié en seconde ligne dans le budget mensuel moyen, "
                "où l'abonnement Essential annuel est déjà suivi en provisions."
            ),
        },
        "en_attente": joint.get("en_attente"),
        "renvoyes": {
            "note": (joint.get("renvoyes") or {}).get("note"),
            "n": len((joint.get("renvoyes") or {}).get("operations") or []),
        },
        "regles": {
            "doublons": "Un virement vu sur les deux relevés n'est listé qu'une fois, avec la mention de source « perso / joint » (ou équivalent).",
            "salaire": "Le salaire Tesla reçu sur le perso est un revenu. Son virement ultérieur vers le joint ou l'investissement est un transfert interne, pas une dépense, et pas un revenu du joint.",
            "france_travail": "Les allocations France Travail du joint sont des revenus du foyer.",
            "air_glow": "Tout ce qui relève d'Air Glow (WordPress, pubs Facebook, MailPoet, Dualhook, X Ads, Envato, INPI, CCI) est regroupé sur une seule ligne « Air Glow, frais de fonctionnement », hors dépenses personnelles.",
            "corrections_joint": "Grok (via Apple), Dentiste (Dr Koch), Deblock interne : inchangés.",
        },
    }

    DATA.mkdir(parents=True, exist_ok=True)
    perso_path = DATA / "compte_perso_2026-10_11.json"
    comptes_path = DATA / "comptes_2026-10_11.json"
    perso_path.write_text(json.dumps(perso_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    comptes_path.write_text(json.dumps(comptes_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    # report
    print("=== FUSION ===")
    print(f"ops fusionnées {len(fused)} (après dédoublonnage, paires {matched_n})")
    print(f"revenus {rev:.2f} €  dont salaire {salaire:.2f}  FT {ft:.2f}  intérêts {interets:.2f}")
    print(f"dépenses perso {dep:.2f} €")
    print(f"reste {reste:.2f} €")
    print(f"virements intern sortants {intern_out['observe_eur']:.2f}  entrants {vin_tot:.2f}")
    print(f"Air Glow, frais de fonctionnement {glow['observe_eur']:.2f}  n={glow['n_operations']}")
    print(f"emprunt {pret:.2f}  repayment {remb_emp:.2f}")
    print(f"remboursements {remb:.2f}")
    print(f"octobre {totaux['octobre']}")
    print(f"novembre {totaux['novembre_1_25']}")
    print("--- catégories ---")
    for c in cats:
        if c["n_operations"] or c["observe_eur"]:
            print(f"  {c['id']:22} n={c['n_operations']:3}  {c['observe_eur']:10.2f} €  in_dep={c['compte_dans_total_depenses']}")
    print(f"à confirmer ({len(ambigues)})")
    for a in ambigues:
        print(f"  - {a['sujet']} ({a.get('montant_eur')}) — {a.get('question')}")
    print("wrote", perso_path)
    print("wrote", comptes_path)
    return 0


def detail_cat(cid, ops, debit, credit, observe):
    if not ops:
        return "Aucune opération en octobre 2026."
    n = len(ops)
    bits = [f"{n} opération" + ("s" if n != 1 else "")]
    srcs = {}
    for o in ops:
        k = o.get("compte_libelle") or o.get("compte") or "?"
        srcs[k] = srcs.get(k, 0) + 1
    bits.append(", ".join(f"{v} {k}" for k, v in sorted(srcs.items(), key=lambda x: -x[1])))
    if cid == "air_glow":
        bits.append("WordPress, Facebook, MailPoet, Dualhook, X Ads, Envato, INPI et CCI — frais de fonctionnement, exclus des dépenses personnelles")
    if cid == "credit_revolut":
        bits.append("mensualité 169,60 € du crédit Revolut 23 500 € — charge fixe")
    if cid == "virements_internes":
        bits.append("vers joint, épargne, XTB, Revolut X, marge, métaux, compte à son nom — exclus des dépenses")
    if credit and cid == "abonnements":
        bits.append(f"crédits Apple déduits ({credit:.2f} €)".replace(".", ","))
    return " · ".join(bits)


if __name__ == "__main__":
    raise SystemExit(build())
