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
    ("air_glow_pub", "Air Glow, pub (pro)", False),
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
            cat, typ = "remboursements", "remboursements"
            notes.append("DGFIP, référence COLLEGE FOCH — probable remboursement (impôt / frais scolaires). Non compté en salaire.")
            ambigu = {
                "sujet": "DGFIP FINANCES PUBLIQUES 36,35 € (COLLEGE FOCH)",
                "montant_eur": amt,
                "classification": "remboursements",
                "question": "Remboursement d'impôt, de frais scolaires, ou autre versement de la DGFIP ?",
            }
        elif "AON FRANCE" in lib:
            cat, typ = "remboursements", "remboursements"
            notes.append("Aon France, complément sécurité sociale (mutuelle). À rapprocher des soins dentaires Dr Koch. Non inclus dans les revenus.")
        elif lib == "Personal loan":
            cat, typ = "financement", "financement_entrant"
            notes.append("Prêt personnel Revolut 23 500 €. Ce n'est pas un revenu. Le jour même, 23 434,34 € partent vers le compte FR7610278010100002262220176.")
            ambigu = {
                "sujet": "Personal loan Revolut 23 500 € (6/11/2026)",
                "montant_eur": amt,
                "classification": "financement",
                "question": "Confirmer qu'il s'agit bien d'un prêt Revolut, et l'usage du virement de 23 434,34 € vers le compte FR7610278010100002262220176 (clôturé le 16/11, solde résiduel 47,89 € reçu sur le joint).",
            }
        elif "FRANCKY VETSCH" in lib:
            cat, typ = "a_confirmer_credit", "a_confirmer"
            notes.append("Petit virement reçu (2,00 €). Non compté en revenu en attendant confirmation.")
            ambigu = {
                "sujet": "Paiement envoyé par M FRANCKY VETSCH 2,00 €",
                "montant_eur": amt,
                "classification": "à confirmer (non inclus dans les revenus)",
                "question": "Remboursement, cadeau, ou autre ? À classer ?",
            }
        elif "Apple Pay" in lib:
            cat, typ = "virements_internes_entrants", "virement_interne"
            notes.append("Recharge Apple Pay. Probable alimentation depuis une carte à son nom — pas un revenu. À confirmer.")
            ambigu = {
                "sujet": f"{lib} {amt:.2f} €",
                "montant_eur": amt,
                "classification": "virements_internes_entrants",
                "question": "Recharge depuis une carte personnelle (*3356) ? Ce n'est pas compté en revenu.",
            }
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
        notes.append("Cofica Bail — probable échéance de LOA / financement véhicule. Classé en Transport.")
        ambigu = {
            "sujet": "Cofica Bail 486,32 € (5/10 et 5/11)",
            "montant_eur": 486.32,
            "classification": "transport",
            "question": "Confirmer qu'il s'agit bien d'une échéance de LOA / crédit véhicule ?",
        }
    elif "Free Telecom" in lib:
        cat, typ = "telecom", "depense"
        notes.append("Free Haut Débit.")
    elif "abonnement Ultra" in lib:
        cat, typ = "abonnements", "depense"
        notes.append("Abonnement Revolut Ultra.")
    elif lib == "repayment":
        cat, typ = "financement", "financement_sortant"
        notes.append("Libellé « repayment » 169,60 € (9/10 et 9/11). Probable échéance de crédit Revolut. Exclu des dépenses de consommation.")
        ambigu = {
            "sujet": "repayment 169,60 € (9/10 et 9/11)",
            "montant_eur": 169.60,
            "classification": "financement (exclu des dépenses perso)",
            "question": "Remboursement d'un crédit Revolut (lié au Personal loan ou à un autre crédit) ?",
        }
    elif lib in ("Netflix", "Disney+", "YouTube"):
        cat, typ = "abonnements", "depense"
    elif "Bastos" in lib:
        cat, typ = "autres", "depense"
        notes.append("PayPal *bastos_67 (Luxembourg). Catégorie Autres en attendant confirmation.")
        ambigu = {
            "sujet": "Bastos 67 (PayPal) 20,93 €",
            "montant_eur": amt,
            "classification": "autres",
            "question": "Tabac, commerçant, ou autre dépense ?",
        }
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
    "Apple": ("abonnements", "depense", None, None, "Facture Apple.com/bill. Les crédits Apple du même mois sont déduits du net Abonnements. Le 219,99 € du 4/11 n'est pas l'abonnement Grok d'octobre (114,99 €).",
              {"sujet": "Apple.com/bill 219,99 € le 4/11/2026", "montant_eur": 219.99, "classification": "abonnements", "question": "Objet de cette facture Apple (autre abonnement, achat, renouvellement) ? Ce n'est pas le Grok 114,99 € d'octobre."}),
    "Carrefour": ("courses", "depense", None, None, None, None),
    "Temu": ("achats", "depense", None, None, None, None),
    "WordPress": ("abonnements", "depense", None, None, "Wp*wordpress — abonnement site (probable activité pro Air Glow).", None),
    "Dr Eric Koch": ("sante", "depense", "Dentiste (Dr Koch)", "dentaire", "Dentiste (Dr Eric Koch, Strasbourg). Remboursement mutuelle Aon à vérifier (des versements Aon « complément sécurité sociale » apparaissent sur le compte perso en novembre).", None),
    "Karllagerfeld Outletro": ("achats", "depense", None, None, "Karl Lagerfeld outlet, Roppenheim.", None),
    "Axa": ("assurances", "depense", None, None, None, None),
    "MailPoet": ("abonnements", "depense", None, None, "MailPoet (Dublin) — extension e-mail WordPress, probable activité pro Air Glow.",
                 {"sujet": "MailPoet 85,95 € le 5/11/2026", "montant_eur": 85.95, "classification": "abonnements", "question": "Outil pro Air Glow (comme WordPress) ? Le laisser dans les abonnements perso, ou le sortir comme dépense pro ?",}),
    "Tradingview": ("abonnements", "depense", None, None, "Prélèvement TradingView (Premium 83,94 €). Déjà suivi à part dans le bloc courtage (objectif Essential annuel).", None),
    "Free": ("telecom", "depense", None, None, "Free Mobile.", None),
    "L'Onglery des Tanneurs": ("loisirs", "depense", None, None, "Institut d'ongles, Strasbourg.", None),
    "McDonald's": ("loisirs", "depense", None, None, None, None),
    "Facebook": ("air_glow_pub", "depense_pro", None, None, "Publicité Facebook / Meta, Air Glow (pro). Exclue des dépenses personnelles, comme en octobre.", None),
    "Monoprix": ("courses", "depense", None, None, None, None),
    "Cb Nx000018": ("autres", "depense", None, None, "Libellé tronqué (Cb Nx000018, Strasbourg).",
                    {"sujet": "Cb Nx000018 28,85 € (Strasbourg, 15/11)", "montant_eur": 28.85, "classification": "autres", "question": "Commerçant exact ?",}),
    "Thai S": ("loisirs", "depense", None, None, "Restaurant.", None),
    "Fritz Schmitt": ("loisirs", "depense", None, None, "Fritz Schmitt, Ottrott — probable restaurant ou cave.",
                      {"sujet": "Fritz Schmitt 23,20 € (Ottrott, 24/11)", "montant_eur": 23.20, "classification": "loisirs", "question": "Restaurant, cave, ou autre ?",}),
    "Snack Cicek": ("loisirs", "depense", None, None, None, None),
    "Normal": ("achats", "depense", None, None, "Normal Strasbourg (hygiène / bazar).", None),
    "CTS": ("transport", "depense", None, None, None, None),
    "Virement à : Shana Trouve": ("virements_internes", "virement_interne", None, None, "Virement vers la poche Shana. Les dépenses carte de Shana sont comptées à part (pas de double compte).", None),
    "Dualhook": ("autres", "depense", None, None, "Dualhook.com, Anvers.",
                 {"sujet": "Dualhook.com 14,40 € (Anvers, 21/11)", "montant_eur": 14.40, "classification": "autres", "question": "Commerçant / objet de l'achat ?",}),
    "IKA": ("courses", "depense", None, None, None, None),
    "Microsoft": ("abonnements", "depense", None, None, None, None),
    "Les Ciseaux D Or": ("loisirs", "depense", None, None, "Coiffeur, Strasbourg.", None),
    "Le Kleber": ("loisirs", "depense", None, None, "Le Kléber, Strasbourg (restauration).", None),
    "Stein Pâtisseries & Café": ("loisirs", "depense", None, None, None, None),
    "Librairie Kléber": ("achats", "depense", None, None, None, None),
    "Paiement envoyé par FRANCE TRAVAIL GRAND EST": ("revenus", "revenus", None, None, "Allocation France Travail Grand Est. Revenu réel du foyer.", None),
    "Recharge sur Apple Pay via *0225": ("virements_internes_entrants", "virement_interne", None, None, "Recharge Apple Pay. Probable alimentation depuis une carte à son nom — pas un revenu.",
                                         {"sujet": "Recharges Apple Pay *0225 650 € + 270 € (16/11, compte joint)", "montant_eur": 920.0, "classification": "virements_internes_entrants", "question": "Recharges depuis une carte personnelle (*0225) ? Ce n'est pas compté en revenu.",}),
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
            typ = oo.get("type") or ("virement_interne" if cat == "virements_internes" else ("depense_pro" if cat == "air_glow_pub" else "depense"))
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
        # Apple 219.99 ambiguity only for that amount; other Apple lines: same cat, no extra question
        if lib == "Apple":
            if o.get("sens") == "credit":
                note = "Crédit Apple.com/bill — déduit du net de la catégorie Abonnements."
                ambigu = None
            elif r2(o["montant_eur"]) != 219.99:
                ambigu = None
                if r2(o["montant_eur"]) != 219.99:
                    note = "Facture Apple.com/bill. Les crédits Apple du même mois sont déduits du net Abonnements."
            else:
                if apple_ambigu_once:
                    ambigu = None
                apple_ambigu_once = True
        if lib == "MailPoet":
            if mailpoet_once:
                ambigu = None
            mailpoet_once = True
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
    glow = next(c for c in cats if c["id"] == "air_glow_pub")
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
        ops_m = [o for o in fused if pred(o)]
        dep_m = r2(sum(
            (o["montant_eur"] if o["sens"] == "debit" else -o["montant_eur"])
            for o in ops_m
            if o.get("categorie") in IN_DEP and IN_DEP[o["categorie"]]
        )) or 0.0
        rev_m = r2(sum(o["montant_eur"] for o in ops_m if o["type"] == "revenus" and o["sens"] == "credit")) or 0.0
        return {"depenses_eur": dep_m, "depenses_usd": usd(dep_m), "revenus_eur": rev_m, "revenus_usd": usd(rev_m), "reste_eur": r2(rev_m - dep_m), "reste_usd": usd(r2(rev_m - dep_m))}

    totaux = {
        "depenses_eur": dep,
        "depenses_usd": usd(dep),
        "depenses_note": (
            "Somme nette des catégories de dépenses personnelles des deux comptes "
            "(virements internes, épargne, investissement, financement, remboursements et dépenses pro Air Glow pub exclus). "
            "Les virements perso → joint (et l'inverse) ne sont comptés qu'une fois, et uniquement en transferts internes. "
            "Les crédits Apple.com/bill du même mois sont déduits des Abonnements."
        ),
        "revenus_eur": rev,
        "revenus_usd": usd(rev),
        "revenus_detail": (
            "Salaire Tesla France 10 485,00 € (4 169,59 € le 22/10, réf. Salary 102026 ; "
            "6 315,41 € le 24/11, réf. Salary 112026) + France Travail Grand Est 1 753,20 € "
            "(876,60 € le 1/10 et 876,60 € le 2/11) + intérêts d'épargne Revolut 0,48 €. "
            "Les virements entre comptes, le prêt personnel, les recharges Apple Pay et les remboursements Aon / AXA / DGFIP ne sont pas des revenus."
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
            "DGFIP 36,35 € (perso, 1/10, réf. COLLEGE FOCH, à confirmer)."
        ),
        "reste_eur": reste,
        "reste_usd": usd(reste),
        "reste_formule": "revenus réels (salaire Tesla + France Travail + intérêts d'épargne) − dépenses personnelles (hors virements internes / épargne / investissement, hors Air Glow pub pro, hors financement, hors remboursements)",
        "virements_internes_entrants_eur": vin_tot,
        "virements_internes_entrants_usd": usd(vin_tot),
        "virements_internes_sortants_eur": intern_out["observe_eur"],
        "virements_internes_sortants_usd": intern_out["observe_usd"],
        "air_glow_pub_eur": glow["observe_eur"],
        "air_glow_pub_usd": glow["observe_usd"],
        "air_glow_pub_note": (
            f"Sous-total des paiements Facebook / Meta pour la publicité Air Glow ({glow['observe_eur']:.2f} €, "
            f"{glow['n_operations']} paiements sur les deux mois). Exclu du total des dépenses personnelles, "
            "sur confirmation d'Emmanuel le 25/11/2026 à 13 h 07."
        ),
        "emprunt_entrant_eur": pret,
        "emprunt_entrant_usd": usd(pret),
        "remboursements_emprunt_eur": remb_emp,
        "remboursements_emprunt_usd": usd(remb_emp),
        "financement_note": (
            "Prêt personnel Revolut 23 500 € le 6/11 (pas un revenu). "
            "Le jour même, 23 434,34 € sont virés vers le compte FR7610278010100002262220176 (transfert interne). "
            "Deux « repayment » de 169,60 € (9/10 et 9/11) sont traités comme remboursement d'emprunt, exclus des dépenses de consommation, à confirmer."
        ),
        "octobre": slice_tot(is_oct),
        "novembre_1_25": slice_tot(is_nov),
        "n_operations_fusionnees": len(fused),
        "n_transferts_dedoublonnes": matched_n,
        "virements_internes_detail": vi_break,
    }

    # perso JSON
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
        "titre": "Compte perso Emmanuel Trouvé, 1er octobre – 25 novembre 2026",
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
            "fin": "2026-11-25",
            "libelle": "1er octobre – 25 novembre 2026",
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
        "bastos", "dgfip", "francky", "*3356", "personal loan", "repayment", "cofica", "poche shana"
    ))]

    comptes_doc = {
        "id": "comptes_foyer_2026-10_11",
        "titre": "Comptes",
        "periode": {
            "debut": "2026-10-01",
            "fin": "2026-11-25",
            "libelle": "1er octobre – 25 novembre 2026",
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
                "Fusion des opérations du compte joint (data/budget/compte_joint_2026-10.json, y compris les 134 opérations "
                "du 1–25/11 précédemment hors bloc octobre) et du compte perso (même période). "
                "Les corrections déjà faites sur le joint sont conservées : Air Glow pub (pro), Grok (via Apple), "
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
        "operations_ambigues": ambigues,
        "tradingview_sur_le_releve": {
            "present_sur_le_releve": True,
            "total_eur": r2(sum(
                o["montant_eur"] for o in fused
                if o["libelle"] == "Tradingview" and o["sens"] == "debit"
            )),
            "note": (
                "Deux prélèvements TradingView Premium de 83,94 € figurent sur le compte joint (7/10 et 7/11). "
                "Ils restent dans Abonnements. Ils ne sont pas recopiés en seconde ligne dans le bloc courtage, "
                "où l'objectif Essential annuel (186,48 € / an) est déjà suivi."
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
            "air_glow": "Tous les paiements Facebook / Meta restent dans « Air Glow, pub (pro) », hors dépenses perso.",
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
    print(f"Air Glow pub {glow['observe_eur']:.2f}  n={glow['n_operations']}")
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
        return "Aucune opération sur la période (1er octobre – 25 novembre 2026)."
    n = len(ops)
    bits = [f"{n} opération" + ("s" if n != 1 else "")]
    srcs = {}
    for o in ops:
        k = o.get("compte_libelle") or o.get("compte") or "?"
        srcs[k] = srcs.get(k, 0) + 1
    bits.append(", ".join(f"{v} {k}" for k, v in sorted(srcs.items(), key=lambda x: -x[1])))
    if cid == "air_glow_pub":
        bits.append("publicité Facebook / Meta, exclue des dépenses personnelles")
    if cid == "virements_internes":
        bits.append("vers joint, épargne, XTB, Revolut X, marge, métaux, compte à son nom — exclus des dépenses")
    if credit and cid == "abonnements":
        bits.append(f"crédits Apple déduits ({credit:.2f} €)".replace(".", ","))
    return " · ".join(bits)


if __name__ == "__main__":
    raise SystemExit(build())
