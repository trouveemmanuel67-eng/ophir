#!/usr/bin/env python3
"""Prévisionnel d'opportunité d'achat immobilier APEX (à contre-courant).

Génère data/immobilier_previsionnel.json à partir de données sourcées
et d'un modèle simple, documenté, sur 10 semestres (2027-S1 → 2031-S2).

Ce n'est pas une prévision certaine : les chemins de taux et de prix sont
des scénarios transparents, pas des promesses.
"""
from __future__ import annotations

import json
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "immobilier_previsionnel.json"

PERIODS = [
    "2027-S1", "2027-S2", "2028-S1", "2028-S2", "2029-S1",
    "2029-S2", "2030-S1", "2030-S2", "2031-S1", "2031-S2",
]
PERIOD_LABELS = {
    "2027-S1": "2027 1er sem.", "2027-S2": "2027 2e sem.",
    "2028-S1": "2028 1er sem.", "2028-S2": "2028 2e sem.",
    "2029-S1": "2029 1er sem.", "2029-S2": "2029 2e sem.",
    "2030-S1": "2030 1er sem.", "2030-S2": "2030 2e sem.",
    "2031-S1": "2031 1er sem.", "2031-S2": "2031 2e sem.",
}
SCENARIOS = ("baisse", "statu_quo", "remontee")
SCENARIO_LABELS = {
    "baisse": "Baisse des taux",
    "statu_quo": "Statu quo",
    "remontee": "Remontée des taux",
}

# Pondération du score sur 250, lecture à contre-courant.
W_PRIX = 70
W_ACCES = 60
W_VOLUME = 50
W_MARGE = 40
W_DPE = 30
TOTAL_MAX = W_PRIX + W_ACCES + W_VOLUME + W_MARGE + W_DPE  # 250
assert TOTAL_MAX == 250

MENSUALITE_MAX = 1500
DUREE_ANS = 25
TAUX_ACTUEL_25A = 3.57  # CL/CSA, prêts 25 ans, octobre 2026
TAUX_ACTUEL_MOY = 3.49  # CL/CSA, taux moyen, octobre 2026
SOFTMAX_T = 20.0  # température en points de score

# Appartements 4 pièces anciens, estimations Figaro au 01/10/2026 (€/m²).
APT_4P_COMMUNES = {
    "Schiltigheim": 2688,
    "Bischheim": 2488,
    "Hoenheim": 2159,
    "Souffelweyersheim": 3051,
    "Vendenheim": 3016,
    "La Wantzenau": 2940,
}
SURFACE_4P_TYP = 85  # hypothèse, médiane CUS tous appartements = 68 m² (2025)

# Maisons anciennes, notaires du Bas-Rhin, année 2025 (signé).
FERME_REF_PRIX = 230_000  # Haguenau / Niederbronn, prix médian
FERME_REF_M2 = 2000       # 230 000 € / 115 m²
FERME_REF_SURFACE = 115
FERME_REF_TERRAIN = 580   # m², sous les 10 ares visés


def clip(x, lo, hi):
    return lo if x < lo else hi if x > hi else x


def band(score: int):
    if score >= 190:
        return "cyan", "#00e5ff"
    if score >= 130:
        return "vert", "#22c55e"
    if score >= 70:
        return "orange", "#ff8c1a"
    if score >= 10:
        return "rouge", "#ff2d2d"
    return "violet", "#9d54ff"


def capital(mens: float, rate_pa: float, years: int = DUREE_ANS) -> float:
    """Capital empruntable, annuité constante, i = taux annuel / 12."""
    i = rate_pa / 100.0 / 12.0
    n = years * 12
    if i <= 0:
        return mens * n
    return mens * (1 - (1 + i) ** (-n)) / i


def mensualite(cap: float, rate_pa: float, years: int = DUREE_ANS) -> float:
    i = rate_pa / 100.0 / 12.0
    n = years * 12
    if i <= 0:
        return cap / n
    return cap * i / (1 - (1 + i) ** (-n))


def softmax(scores, T=SOFTMAX_T):
    import math
    m = max(scores)
    exps = [math.exp((s - m) / T) for s in scores]
    s = sum(exps)
    return [e / s for e in exps]


# Taux 25 ans par semestre, en %. Scénario « remontée » calé sur
# l'anticipation Crédit Logement/CSA d'octobre 2026 (pic proche de 4 %
# fin T2 2027, ~3,85 % fin 2027). Au-delà, prolongement prudent :
# détente lente, sans revenir sous le taux actuel avant 2030.
# « Baisse » et « statu quo » sont des hypothèses alternatives, pas des
# prévisions d'un organisme.
TAUX = {
    "remontee": [3.85, 4.00, 3.90, 3.80, 3.70, 3.60, 3.55, 3.50, 3.50, 3.45],
    "statu_quo": [3.57, 3.57, 3.55, 3.55, 3.55, 3.55, 3.55, 3.55, 3.55, 3.55],
    "baisse": [3.40, 3.20, 3.00, 2.90, 2.80, 2.75, 2.70, 2.70, 2.75, 2.80],
}

# Variation de prix cumulée depuis fin 2026, en % (indice 100 aujourd'hui).
# Les appartements du nord de Strasbourg baissent déjà (−4,4 % sur un an
# au T2 2026, bases notariales). Les maisons rurales du nord du Bas-Rhin
# étaient encore stables en 2025 ; on leur ajoute une pression DPE
# autour de l'interdiction F au 1er janvier 2028.
PRIX_DELTA = {
    "appart": {
        "remontee": [-2.0, -4.0, -6.0, -5.5, -5.0, -4.0, -3.5, -3.0, -2.5, -2.0],
        "statu_quo": [-1.0, -2.0, -2.5, -2.5, -2.0, -1.5, -1.0, -0.5, 0.0, 0.5],
        "baisse": [-0.5, 0.0, 1.0, 2.0, 3.5, 5.0, 6.0, 7.0, 8.0, 9.0],
    },
    "ferme": {
        "remontee": [-3.0, -6.0, -9.0, -8.0, -6.0, -4.0, -3.0, -2.0, -1.0, 0.0],
        "statu_quo": [-2.0, -4.0, -7.0, -6.0, -4.0, -3.0, -2.0, -1.0, 0.0, 1.0],
        "baisse": [-1.0, -3.0, -5.0, -3.0, -1.0, 1.0, 2.0, 3.0, 4.0, 5.0],
    },
}

# Volume de transactions, 100 = niveau fin 2026 (~956 000 ventes / 12 mois).
# Plus le volume est bas, plus le marché est acheteur (plus de points).
VOLUME = {
    "appart": {
        "remontee": [92, 86, 84, 86, 90, 94, 96, 98, 100, 100],
        "statu_quo": [96, 94, 94, 95, 96, 97, 98, 99, 100, 100],
        "baisse": [98, 100, 104, 108, 110, 112, 112, 110, 108, 108],
    },
    "ferme": {
        # Offre supplémentaire de passoires avant l'interdiction F :
        # plus d'annonces, demande toujours timide = marché plus acheteur.
        "remontee": [90, 82, 78, 82, 88, 92, 95, 97, 99, 100],
        "statu_quo": [94, 88, 84, 86, 90, 94, 96, 98, 99, 100],
        "baisse": [96, 92, 90, 96, 102, 106, 108, 108, 106, 106],
    },
}

# Marge de négociation, en %. Régions : 5,1 % en septembre 2026 (Laforêt).
# Logements F ou G : décotes souvent > 10 % (même source, nov. 2026).
MARGE = {
    "appart": {
        "remontee": [5.5, 6.5, 7.0, 6.5, 6.0, 5.5, 5.2, 5.0, 5.0, 5.0],
        "statu_quo": [5.2, 5.5, 5.7, 5.5, 5.3, 5.2, 5.1, 5.1, 5.0, 5.0],
        "baisse": [5.0, 4.6, 4.2, 4.0, 3.8, 3.6, 3.5, 3.5, 3.6, 3.6],
    },
    "ferme": {
        "remontee": [8.0, 10.0, 11.0, 10.0, 8.5, 7.0, 6.0, 5.5, 5.2, 5.0],
        "statu_quo": [7.5, 9.0, 10.0, 9.0, 7.5, 6.5, 5.8, 5.4, 5.2, 5.1],
        "baisse": [7.0, 8.0, 8.5, 7.0, 6.0, 5.2, 4.8, 4.6, 4.5, 4.5],
    },
}

# Pression DPE, points déjà sur 30. Pic autour du 1er janvier 2028 (classe F).
# Les appartements du premier ring sont moins exposés (parc plus mixte).
DPE_PTS = {
    "ferme": [12, 25, 30, 22, 15, 10, 8, 6, 5, 5],
    "appart": [4, 8, 12, 10, 6, 4, 3, 2, 2, 2],
}

# Points déjà acquis sur le critère prix (baisse déjà constatée).
PRIX_BASE = {"appart": 25, "ferme": 15}


def score_prix(kind: str, delta_pct: float) -> int:
    """Plus le prix a baissé (déjà + encore), plus on donne de points."""
    extra = clip(-delta_pct / 8.0, 0.0, 1.0) * (W_PRIX - PRIX_BASE[kind])
    # Si les prix remontent au-dessus d'aujourd'hui, on retire de la base.
    if delta_pct > 0:
        extra = -clip(delta_pct / 8.0, 0.0, 1.0) * PRIX_BASE[kind]
    return int(round(clip(PRIX_BASE[kind] + extra, 0, W_PRIX)))


def score_acces(prix: float, taux: float) -> int:
    """60 pts si la mensualité ≤ 65 % du plafond, 0 si elle atteint 1 500 €."""
    mens = mensualite(prix, taux)
    ratio = mens / MENSUALITE_MAX
    if ratio >= 1:
        return 0
    if ratio <= 0.65:
        return W_ACCES
    return int(round(W_ACCES * (1 - ratio) / (1 - 0.65)))


def score_volume(vol_index: float) -> int:
    """50 pts si le volume tombe à 75, 10 pts s'il revient à 115 (marché vendeur)."""
    pts = 10 + (115 - vol_index) / (115 - 75) * 40
    return int(round(clip(pts, 0, W_VOLUME)))


def score_marge(marge_pct: float) -> int:
    """0 pt à 2 % de marge (marché vendeur), 40 pts à 10 % ou plus."""
    pts = (marge_pct - 2.0) / (10.0 - 2.0) * W_MARGE
    return int(round(clip(pts, 0, W_MARGE)))


def typified_prices():
    zone = sum(APT_4P_COMMUNES.values()) / len(APT_4P_COMMUNES)
    coeur_noms = ("Schiltigheim", "Bischheim", "Hoenheim")
    coeur = sum(APT_4P_COMMUNES[n] for n in coeur_noms) / 3
    return {
        "appart_m2_zone": round(zone),
        "appart_m2_coeur": round(coeur),
        "appart_prix": round(zone) * SURFACE_4P_TYP,
        "ferme_m2": FERME_REF_M2,
        "ferme_prix": FERME_REF_PRIX,
    }


def score_period(kind: str, scen: str, i: int, prix0: float):
    taux = TAUX[scen][i]
    delta = PRIX_DELTA[kind][scen][i]
    prix = prix0 * (1 + delta / 100.0)
    vol = VOLUME[kind][scen][i]
    marge = MARGE[kind][scen][i]
    dpe = DPE_PTS[kind][i]
    sp = score_prix(kind, delta)
    sa = score_acces(prix, taux)
    sv = score_volume(vol)
    sm = score_marge(marge)
    total = sp + sa + sv + sm + dpe
    mens = mensualite(prix, taux)
    cap = capital(MENSUALITE_MAX, taux)
    b, hx = band(total)
    return {
        "periode": PERIODS[i],
        "label": PERIOD_LABELS[PERIODS[i]],
        "taux_25a": round(taux, 2),
        "prix_delta_pct": delta,
        "prix_typique": int(round(prix)),
        "mensualite_typique": int(round(mens)),
        "budget_accessible": int(round(cap)),
        "volume_index": vol,
        "marge_pct": marge,
        "points": {
            "prix": sp,
            "accessibilite": sa,
            "volume": sv,
            "marge": sm,
            "dpe": dpe,
            "total": total,
        },
        "note": total,
        "bande": b,
        "hex": hx,
    }


def build_bien(kind: str, prix0: float, prix_m2: int, titre: str, resume_ctx: str):
    par_scen = {}
    for scen in SCENARIOS:
        rows = [score_period(kind, scen, i, prix0) for i in range(len(PERIODS))]
        probs = softmax([r["note"] for r in rows])
        for r, p in zip(rows, probs):
            r["proba_pct"] = round(100 * p, 1)
        best_i = max(range(len(rows)), key=lambda i: (rows[i]["note"], -i))
        par_scen[scen] = {
            "label": SCENARIO_LABELS[scen],
            "meilleure_periode": rows[best_i]["periode"],
            "meilleure_label": rows[best_i]["label"],
            "meilleure_proba_pct": rows[best_i]["proba_pct"],
            "meilleure_note": rows[best_i]["note"],
            "periodes": rows,
        }

    # Probabilité mélange : moyenne simple des 3 scénarios.
    mix = []
    for i, per in enumerate(PERIODS):
        p = sum(par_scen[s]["periodes"][i]["proba_pct"] for s in SCENARIOS) / 3
        n = sum(par_scen[s]["periodes"][i]["note"] for s in SCENARIOS) / 3
        b, hx = band(int(round(n)))
        mix.append({
            "periode": per,
            "label": PERIOD_LABELS[per],
            "proba_pct": round(p, 1),
            "note": int(round(n)),
            "bande": b,
            "hex": hx,
            "taux_par_scenario": {s: par_scen[s]["periodes"][i]["taux_25a"] for s in SCENARIOS},
            "budget_par_scenario": {s: par_scen[s]["periodes"][i]["budget_accessible"] for s in SCENARIOS},
        })
    # Renormaliser au cas où l'arrondi ferait dériver la somme.
    sprob = sum(x["proba_pct"] for x in mix)
    if sprob:
        for x in mix:
            x["proba_pct"] = round(x["proba_pct"] * 100 / sprob, 1)
        # Ajuster le plus gros pour tomber à 100,0.
        drift = round(100 - sum(x["proba_pct"] for x in mix), 1)
        mix[max(range(len(mix)), key=lambda i: mix[i]["proba_pct"])]["proba_pct"] = round(
            mix[max(range(len(mix)), key=lambda i: mix[i]["proba_pct"])]["proba_pct"] + drift, 1
        )

    best = max(mix, key=lambda x: (x["proba_pct"], -PERIODS.index(x["periode"])))
    # Budget accessible aujourd'hui, et à la meilleure fenêtre (scénario milieu = statu quo,
    # plus fourchette des 3 scénarios).
    cap_now = int(round(capital(MENSUALITE_MAX, TAUX_ACTUEL_25A)))
    i_best = PERIODS.index(best["periode"])
    budgets_best = [par_scen[s]["periodes"][i_best]["budget_accessible"] for s in SCENARIOS]
    notes_best = {s: par_scen[s]["periodes"][i_best]["note"] for s in SCENARIOS}
    mens_now = int(round(mensualite(prix0, TAUX_ACTUEL_25A)))

    return {
        "id": kind,
        "titre": titre,
        "prix_m2_actuel": prix_m2,
        "prix_typique_actuel": prix0,
        "mensualite_typique_actuelle": mens_now,
        "taux_actuel_25a": TAUX_ACTUEL_25A,
        "budget_accessible_actuel": cap_now,
        "meilleure_periode": best["periode"],
        "meilleure_label": best["label"],
        "meilleure_proba_pct": best["proba_pct"],
        "meilleure_note": best["note"],
        "meilleure_bande": best["bande"],
        "meilleure_hex": best["hex"],
        "budget_accessible_fenetre": int(round(sum(budgets_best) / 3)),
        "budget_accessible_fenetre_min": min(budgets_best),
        "budget_accessible_fenetre_max": max(budgets_best),
        "note_fenetre_par_scenario": notes_best,
        "meilleure_saison": "novembre à février",
        "frise": mix,
        "scenarios": par_scen,
        "resume_contexte": resume_ctx,
    }


def make_resumes(biens):
    """Phrases courtes, une par bien, calées sur le résultat du modèle."""
    out = {}
    for k, b in biens.items():
        fen = b["meilleure_label"]
        p = b["meilleure_proba_pct"]
        if k == "ferme":
            out[k] = (
                f"La fenêtre la plus favorable se dessine au {fen} "
                f"(environ {p:.0f} % de chance d’être la meilleure). "
                "C’est autour de l’interdiction de louer les F, avec des taux encore hauts. "
                "Estimation, pas une certitude."
            )
        else:
            out[k] = (
                f"La fenêtre la plus favorable se dessine au {fen} "
                f"(environ {p:.0f} % de chance d’être la meilleure). "
                "Les 4 pièces du nord ont déjà baissé ; des taux encore hauts peuvent creuser un peu plus le prix. "
                "Estimation, pas une certitude."
            )
    return out


def build():
    typ = typified_prices()
    biens = {
        "ferme": build_bien(
            "ferme", typ["ferme_prix"], typ["ferme_m2"],
            "Corps de ferme",
            "Référence : maison ancienne médiane du secteur Haguenau / Niederbronn en 2025.",
        ),
        "appart": build_bien(
            "appart", typ["appart_prix"], typ["appart_m2_zone"],
            "4 pièces Strasbourg Nord",
            "Référence : moyenne des appartements 4 pièces anciens (6 communes à 15 km au nord).",
        ),
    }
    resumes = make_resumes(biens)
    for k, b in biens.items():
        b["resume"] = resumes[k]

    data = {
        "date": "2026-11-26",
        "generated": "2026-11-26",
        "avertissement": (
            "Estimation indicative, pas une prévision certaine. "
            "Les chemins de taux et de prix sont des scénarios transparents, pas des rendements ni des prix promis. "
            "Un achat peut se faire plus tôt ou plus tard selon l’apport, l’état du bien et les travaux."
        ),
        "horizon": {"debut": "2027-S1", "fin": "2031-S2", "pas": "semestre"},
        "contrainte": {
            "mensualite_max": MENSUALITE_MAX,
            "duree_ans": DUREE_ANS,
            "hors_assurance": True,
            "frais_ancien_pct": 8,
            "note_frais": (
                "Budget = capital empruntable à 1 500 €/mois sur 25 ans, hors assurance. "
                "L’assurance (souvent 0,25 à 0,40 % du capital par an) réduit la capacité. "
                "Les frais d’achat en ancien (environ 7 à 8 %) et les travaux se paient en plus, typiquement avec l’apport."
            ),
            "apport": (
                "L’apport est prévu d’ici 2 à 3 ans (vers 2028-2029). "
                "Cela recoupe la fenêtre de marché la plus probable, mais le montant d’apport n’est pas chiffré ici."
            ),
        },
        "taux_actuel": {
            "cl_csa_25a": TAUX_ACTUEL_25A,
            "cl_csa_moyen": TAUX_ACTUEL_MOY,
            "cl_csa_20a": 3.54,
            "cl_csa_15a": 3.32,
            "bdf_tese": 3.19,
            "bdf_periode": "2026-09",
            "cl_periode": "2026-10",
        },
        "methode": {
            "score_max": 250,
            "echelle": "violet <10, rouge 10–69, orange 70–129, vert 130–189, cyan ≥190",
            "lecture": "à contre-courant : plus de points quand les prix sont bas, les taux rendent le crédit lourd pour les autres, les volumes sont faibles, les marges de négociation sont hautes, et la pression DPE alimente l’offre.",
            "poids": {
                "prix": W_PRIX,
                "accessibilite": W_ACCES,
                "volume": W_VOLUME,
                "marge": W_MARGE,
                "dpe": W_DPE,
            },
            "probabilite": (
                f"Pour chaque scénario, la probabilité qu’un semestre soit la meilleure fenêtre "
                f"est un softmax des notes (température {SOFTMAX_T:.0f} points). "
                "Le mélange affiché donne le même poids aux trois scénarios. "
                "Crédit Logement/CSA (octobre 2026) penche plutôt vers une remontée des taux en 2027."
            ),
            "formules": {
                "capital": "C = M × (1 − (1+i)^(−n)) / i, i = taux annuel / 12, n = 300, M = 1 500 €",
                "prix": "points = base (25 appartements / 15 fermes) + jusqu’à 45 pts pour 8 % de baisse supplémentaire depuis fin 2026",
                "accessibilite": "60 pts si mensualité typique ≤ 65 % de 1 500 €, 0 si elle atteint ou dépasse 1 500 €",
                "volume": "10 pts à un indice 115, 50 pts à un indice 75 (100 = niveau fin 2026)",
                "marge": "0 pt à 2 % de marge, 40 pts à 10 % ou plus",
                "dpe": "barème fixe par semestre, pic au 1er semestre 2028 (interdiction de louer les F)",
            },
            "saison": (
                "Dans l’année, l’hiver (novembre à février) est en général le moment où l’on négocie le mieux : "
                "moins d’acheteurs, vendeurs parfois plus pressés. Ce n’est pas une règle locale garantie."
            ),
        },
        "biens": biens,
        "references": {
            "appart_4p": {
                "communes_m2": APT_4P_COMMUNES,
                "moyenne_zone_m2": typ["appart_m2_zone"],
                "moyenne_coeur_m2": typ["appart_m2_coeur"],
                "coeur": ["Schiltigheim", "Bischheim", "Hoenheim"],
                "surface_typique_m2": SURFACE_4P_TYP,
                "prix_typique": typ["appart_prix"],
                "source": "Figaro Immobilier, estimations au 01/10/2026, appartement 4 pièces ancien",
            },
            "ferme": {
                "secteur": "Haguenau / Niederbronn",
                "prix_median_2025": FERME_REF_PRIX,
                "surface_m2": FERME_REF_SURFACE,
                "terrain_m2": FERME_REF_TERRAIN,
                "prix_m2": FERME_REF_M2,
                "note": (
                    "Il n’existe pas de série officielle « corps de ferme ». "
                    "La référence est la maison ancienne médiane du secteur nord (notaires, 2025). "
                    "Le terrain médian (5,8 ares) est sous les 10 ares visés : un vrai corps de ferme à rénover "
                    "peut coûter plus cher (plus de terrain, plusieurs bâtiments) ou moins cher (gros travaux). "
                    "Les bases DVF de la DGFiP ne couvrent pas l’Alsace-Moselle (livre foncier)."
                ),
            },
        },
        "constats": {
            "prix_france": (
                "Indice Notaires-INSEE, France, T2 2026 : 125,7 (provisoire), −6,2 % sous le pic de T4 2022. "
                "T3 2026 : −0,3 % sur le trimestre, −1,2 % sur un an (publié le 24/11/2026)."
            ),
            "prix_province": "Province T3 2026 : prix stables sur le trimestre, −1,1 % sur un an (maisons −1,2 %, appartements −0,8 %).",
            "prix_strasbourg": "Appartements anciens à Strasbourg : −4,4 % sur un an au T2 2026 (bases notariales, cité par les Notaires de France / Europe 1, 16/11/2026).",
            "prix_strasbourg_m2": "Strasbourg, appartements anciens : 3 333 €/m² en médiane, 1 216 ventes, 01/10/2025–30/09/2026 (notaires de France).",
            "notaires_schiltigheim": "Schiltigheim, appartements anciens : 2 900 €/m², 160 ventes (bases notariales, citées en septembre 2026).",
            "notaires_bischheim": "Bischheim, appartements anciens : 2 417 €/m², 78 ventes (mêmes sources, septembre 2026).",
            "maisons_67": "Bas-Rhin, maisons anciennes : 2 212 €/m² en médiane sur 12 mois à fin juin 2026 (notaires). Année 2025 : prix de vente médian 257 900 €, 119 m², terrain 590 m², +2,3 %.",
            "volumes": "956 000 ventes sur 12 mois à fin septembre 2026 (INSEE, T3 2026). Les notaires anticipaient ~920 000 à la fin 2026 (note de conjoncture sur le T2 2026, données à fin août : 951 000, +3,6 % sur un an).",
            "delais_marges": "Délai moyen 101 jours en régions, marge de négociation 5,1 % en régions et 4,8 % au national (Laforêt, septembre 2026). 9 acquisitions sur 10 sont négociées. Décotes souvent > 10 % pour les logements F ou G.",
            "dpe": "Interdiction de mettre à la location (nouveaux baux, renouvellements, reconductions) : G depuis le 01/01/2025, F à partir du 01/01/2028, E à partir du 01/01/2034 (service-public.fr, vérifié le 01/01/2026).",
            "demographie": "Eurométropole de Strasbourg : 522 596 habitants au recensement 2023, contre 494 089 en 2017, soit +0,9 % par an (INSEE). Cela soutient la demande d’appartements familiaux dans le premier ring ; le marché rural du nord (Wissembourg) est plus fragile.",
            "zfe": "ZFE de l’Eurométropole : report envisagé de l’interdiction des Crit’Air 3 au 01/01/2028 (phase pédagogique en 2026, consultation fin 2026). Facteur secondaire pour un corps de ferme à 50 km si le trajet domicile-travail se fait avec un véhicule ancien.",
        },
        "sources": [
            {"titre": "INSEE, Indices Notaires-INSEE T3 2026 (IR n°284, 24/11/2026)", "url": "https://www.insee.fr/fr/statistiques/9149846"},
            {"titre": "INSEE, série des prix des logements anciens (idbank 010567059)", "url": "https://www.insee.fr/fr/statistiques/serie/010567059"},
            {"titre": "Notaires de France, tendances et prix au T2 2026", "url": "https://www.notaires.fr/fr/article/tendances-et-evolutions-des-prix-de-limmobilier-au-2e-trimestre-2026"},
            {"titre": "Chambre des notaires du Bas-Rhin, conjoncture 2025 (CID, mars 2026)", "url": "https://chambre-bas-rhin.notaires.fr/storage/file_manager_files/2026/04/cid-light67-2025t4.pdf"},
            {"titre": "Observatoire Crédit Logement/CSA, tableau de bord octobre 2026", "url": "https://lobservatoire.creditlogement.fr/wp-content/uploads/sites/2/2026/11/TDB_L_Observatoire_Credit_Logement_CSA_octobre2026.pdf"},
            {"titre": "Banque de France / BCE, taux des crédits habitat (MIR, fixe > 10 ans)", "url": "https://data.ecb.europa.eu/data/datasets/MIR/MIR.M.FR.B.A2C.P.R.A.2250.EUR.N"},
            {"titre": "Journal de l’Agence, perspectives de taux 2027 (15/10/2026, d’après CL/CSA)", "url": "https://www.journaldelagence.com/1414220-credits-immobiliers-taux-en-hausse-marches-en-panne-quelles-perspectives-pour-2027"},
            {"titre": "Laforêt, billet de tendances septembre 2026 (délais et marges)", "url": "https://www.laforet.com/storage/media/82711/LAFORET-BILLET-SEPTEMBRE-2026.pdf"},
            {"titre": "Service-Public, DPE et interdiction de location G/F/E", "url": "https://www.service-public.gouv.fr/particuliers/vosdroits/F16096"},
            {"titre": "INSEE, dossier complet Eurométropole de Strasbourg", "url": "https://www.insee.fr/fr/statistiques/2011101?geo=EPCI-246700488"},
            {"titre": "Eurométropole de Strasbourg, ZFE-m", "url": "https://www.strasbourg.eu/la-zfe-m"},
            {"titre": "Figaro Immobilier, prix au m² par commune (estimations au 01/10/2026)", "url": "https://immobilier.lefigaro.fr/prix-immobilier/schiltigheim/ville-67447"},
            {"titre": "ERA Immobilier Schiltigheim, baromètre septembre 2026 (prix notariaux communaux)", "url": "https://www.eraimmobilier.com/agence-immobiliere-schiltigheim-377/blog-immobilier/article/9387"},
            {"titre": "data.gouv, Demandes de valeurs foncières (absentes en Alsace-Moselle)", "url": "https://www.data.gouv.fr/fr/datasets/demandes-de-valeurs-foncieres/"},
            {"titre": "Crédit Agricole e-immobilier / MoneyVox, saisonnalité de la négociation", "url": "https://e-immobilier.credit-agricole.fr/conseils/1er-achat/y-t-il-une-bonne-saison-pour-acheter-son-logement"},
        ],
        "limites": [
            "Pas de série officielle « corps de ferme » : le modèle s’appuie sur les maisons anciennes des secteurs Haguenau / Niederbronn et Wissembourg. Les transactions de fermes à rénover avec 10 ares ou plus sont trop peu nombreuses pour une médiane robuste.",
            "Les bases DVF publiques ne couvrent pas le Bas-Rhin (livre foncier d’Alsace-Moselle). Les prix signés viennent des notaires, avec un décalage de quelques mois.",
            "Les prix au m² des 4 pièces par commune sont des estimations Figaro Immobilier (représentativité variable, parfois 1/5), pas des médianes notariales de 4 pièces. Les médianes notariales portent sur l’ensemble des appartements.",
            "Les chemins de taux après 2027 et tous les chemins de prix sont des hypothèses de scénarios, pas des prévisions d’un institut. Crédit Logement/CSA n’a publié une anticipation que jusqu’à fin 2027.",
            "Le budget de 1 500 €/mois est hors assurance, hors frais d’achat et hors travaux. Pour un corps de ferme, le coût de rénovation (surtout DPE) peut dépasser l’écart de prix.",
            "La surface de 85 m² pour un 4 pièces est une hypothèse de travail (la médiane de tous les appartements de la CUS est 68 m² en 2025).",
            "La ZFE et la démographie sont rappelées comme contexte, elles n’entrent pas dans le score.",
        ],
    }
    OUT.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return data


if __name__ == "__main__":
    d = build()
    print("écrit", OUT)
    for k, b in d["biens"].items():
        print(f"\n=== {b['titre']} ===")
        print("prix typique", b["prix_typique_actuel"], "€  |  m²", b["prix_m2_actuel"])
        print("mens actuelle", b["mensualite_typique_actuelle"], "€  |  budget now", b["budget_accessible_actuel"])
        print("meilleure", b["meilleure_label"], b["meilleure_proba_pct"], "%  note", b["meilleure_note"], b["meilleure_bande"])
        print("budget fenêtre", b["budget_accessible_fenetre"], "€  (", b["budget_accessible_fenetre_min"], "–", b["budget_accessible_fenetre_max"], ")")
        print("resume:", b["resume"])
        print("frise mélange:")
        for r in b["frise"]:
            print(f"  {r['periode']:8}  {r['proba_pct']:5.1f}%  note {r['note']:3}  {r['bande']}")
        for s in SCENARIOS:
            sc = b["scenarios"][s]
            print(f"  {s}: {sc['meilleure_label']}  {sc['meilleure_proba_pct']}%  note {sc['meilleure_note']}")
