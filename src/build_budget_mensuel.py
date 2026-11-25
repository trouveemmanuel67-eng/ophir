#!/usr/bin/env python3
"""Budget mensuel moyen du foyer, sourcé sur data/budget (1er oct. – 25 nov. 2026).

Ne modifie pas les fichiers de relevé ni la zone Lidl : lit
comptes_2026-10_11.json, lidl_tickets_2026-10_11.json et
data/abonnement_tradingview.json, puis écrit
data/budget/budget_mensuel_moyen.json et l'accroche à positions.json
sous budget.budget_mensuel.
"""
from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
BUDGET_DIR = DATA / "budget"
COMPTES = BUDGET_DIR / "comptes_2026-10_11.json"
LIDL = BUDGET_DIR / "lidl_tickets_2026-10_11.json"
ABO_TV = DATA / "abonnement_tradingview.json"
OUT = BUDGET_DIR / "budget_mensuel_moyen.json"
FX = 1.0944
JOURS_NOV_OBSERVES = 25
JOURS_NOV_COMPLETS = 30
SCALE_NOV = JOURS_NOV_COMPLETS / JOURS_NOV_OBSERVES  # 1.2


def r2(x, n=2):
    if x is None:
        return None
    return round(float(x) + 1e-12, n)


def usd(eur):
    return r2(eur * FX) if eur is not None else None


def moy_fixe(oct_e, nov_e):
    return r2((oct_e + nov_e) / 2)


def moy_var(oct_e, nov_e):
    return r2((oct_e + nov_e * SCALE_NOV) / 2)


def amt(o):
    v = float(o.get("montant_eur") or 0)
    if o.get("sens") == "credit":
        return -v
    return v


def lib(o):
    return (o.get("libelle") or "").strip()


def lib_l(o):
    return lib(o).lower()


def month(o):
    return (o.get("date") or "")[:7]


def cat_ops(d, cid):
    c = next((x for x in d["categories"] if x.get("id") == cid), None)
    return list((c or {}).get("operations") or []), c


def by_month(ops):
    tot = {"2026-10": 0.0, "2026-11": 0.0}
    for o in ops:
        m = month(o)
        if m in tot:
            tot[m] += amt(o)
    return r2(tot["2026-10"]), r2(tot["2026-11"])


def is_loa(o):
    return "cofica" in lib_l(o) or "loa tesla" in lib_l(o)


def is_koch(o):
    return "koch" in lib_l(o) or "dentiste" in lib_l(o)


def is_trip_loisir(o):
    l = lib_l(o)
    return "jardin des pins" in l or "yelloh" in l or "glacier du vin" in l


def is_trip_transport(o):
    d = o.get("date") or ""
    if not ("2026-10-20" <= d <= "2026-10-26"):
        return False
    l = lib(o)
    ll = l.lower()
    if is_loa(o) or "parking foch" in ll or ll == "cts":
        return False
    return True


def is_decathlon_nov(o):
    return "decathlon" in lib_l(o) and (o.get("date") or "").startswith("2026-11")


def is_amazon_exceptionnel(o):
    return "amazon" in lib_l(o) and abs(amt(o)) >= 200


def is_salomon(o):
    return "salomon" in lib_l(o)


def is_ir_solde(o):
    return "finances publiques" in lib_l(o) and abs(amt(o) - 288.0) < 0.01


def is_pot_naissance(o):
    return "pot de naissance" in lib_l(o) or "bastos" in lib_l(o)


def is_inpi(o):
    return "propriété industrielle" in lib_l(o) or "inpi" in lib_l(o)


def is_cci(o):
    return "cci " in lib_l(o) or lib_l(o).startswith("cci")


def is_tradingview(o):
    return "tradingview" in lib_l(o) or "trading view" in lib_l(o)


def is_wordpress(o):
    return "wordpress" in lib_l(o)


def is_grok_heavy(o):
    return "grok heavy" in lib_l(o)


def is_grok_apple(o):
    return lib_l(o).startswith("grok (via apple)") or lib_l(o) == "grok (via apple)"


def is_grok_direct(o):
    return "spacexsi" in lib_l(o) or "www.grok.com" in (o.get("note_classification") or "").lower()


def is_revolut_ultra(o):
    return "ultra" in lib_l(o)


def is_netflix(o):
    return "netflix" in lib_l(o)


def is_disney(o):
    return "disney" in lib_l(o)


def is_youtube(o):
    return "youtube" in lib_l(o)


def is_microsoft(o):
    return "microsoft" in lib_l(o)


def is_prime_video(o):
    return "amazon digital" in lib_l(o) or "prime video" in (o.get("note_classification") or "").lower()


def is_apple(o):
    return lib_l(o) == "apple" or lib_l(o).startswith("apple.com") or "apple.com/bill" in lib_l(o)


def is_free_hd(o):
    return "free telecom" in lib_l(o) or "haut débit" in (o.get("note_classification") or "").lower()


def is_free_mobile(o):
    return lib_l(o) == "free" or (lib_l(o).startswith("free") and "telecom" not in lib_l(o) and "haut" not in lib_l(o))


def poste(id_, libelle, moyenne, detail, **extra):
    rec = {
        "id": id_,
        "libelle": libelle,
        "moyenne_eur": moyenne,
        "moyenne_usd": usd(moyenne),
        "detail": detail,
    }
    rec.update(extra)
    return rec


def load_tv(comptes):
    if ABO_TV.exists():
        raw = json.loads(ABO_TV.read_text(encoding="utf-8"))
        # file may be a wrapper or the tv object itself
        if isinstance(raw, dict) and raw.get("montant_eur_mois") is not None:
            return raw
        if isinstance(raw, dict) and isinstance(raw.get("abonnement"), dict):
            return raw["abonnement"]
    # fallback: from a previous positions build if needed later
    return {
        "montant_eur_mois": 15.54,
        "montant_eur_an": 186.48,
        "formule": "Essential",
        "periodicite": "annuel",
        "avant": {"montant_eur_mois": 83.94, "formule": "Premium"},
        "objectif": {"economie_eur_mois": 68.4, "atteint": True},
    }


def lidl_deco(lidl):
    total = 0.0
    par = {}
    for mois, m in (lidl.get("mois") or {}).items():
        s = 0.0
        for sc in m.get("par_sous_categorie") or []:
            lab = (sc.get("id") or sc.get("libelle") or "").lower()
            if "noël" in lab or "noel" in lab or "déco" in lab or "deco" in lab:
                s += float(sc.get("eur") or 0)
        par[mois] = r2(s)
        total += s
    return r2(total), par


def lidl_textile(lidl):
    par = {}
    total = 0.0
    for mois, m in (lidl.get("mois") or {}).items():
        s = 0.0
        for sc in m.get("par_sous_categorie") or []:
            lab = (sc.get("id") or sc.get("libelle") or "").lower()
            if "textile" in lab or "vêtement" in lab or "vetement" in lab:
                s += float(sc.get("eur") or 0)
        par[mois] = r2(s)
        total += s
    return r2(total), par


def pending_ops(d):
    att = d.get("en_attente") or {}
    ops = list(att.get("operations") or [])
    assigned = []
    for o in ops:
        l = lib_l(o)
        cat = "autres"
        if "lidl" in l or "carrefour" in l or "leclerc" in l or "magasin u" in l or "auchan" in l or "monoprix" in l or "ika" in l:
            cat = "courses"
        elif "amazon" in l:
            cat = "achats"
        elif "phie" in l or "pharmacie" in l or "pasteur" in l:
            cat = "sante"
        elif "poste" in l:
            cat = "autres"
        rec = dict(o)
        rec["_pending_cat"] = cat
        assigned.append(rec)
    return assigned, att


def build():
    global FX
    d = json.loads(COMPTES.read_text(encoding="utf-8"))
    lidl = json.loads(LIDL.read_text(encoding="utf-8")) if LIDL.exists() else {}
    tv = load_tv(d)
    fx = ((d.get("fx") or {}).get("taux")) or FX
    FX = float(fx)

    pending, att = pending_ops(d)
    pending_by = defaultdict(list)
    for o in pending:
        pending_by[o["_pending_cat"]].append(o)

    # ----- revenus (paiements mensuels déjà complets en novembre) -----
    sal_ops = [o for o in d.get("revenus_operations") or [] if "tesla" in lib_l(o)]
    ft_ops = [o for o in d.get("revenus_operations") or [] if "france travail" in lib_l(o)]
    int_ops = [o for o in d.get("revenus_operations") or [] if "intérêt" in lib_l(o) or "interet" in lib_l(o)]
    sal_oct = r2(sum(amt(o) for o in sal_ops if month(o) == "2026-10"))
    sal_nov = r2(sum(amt(o) for o in sal_ops if month(o) == "2026-11"))
    # credits: amt() negates credits? WAIT. Revenues are credits (sens=credit).
    # amt() returns -v for credits. That's wrong for revenues.
    # I need to use montant_eur absolute / according to sens carefully.

    def credit_amt(o):
        return float(o.get("montant_eur") or 0)

    sal_oct = r2(sum(credit_amt(o) for o in sal_ops if month(o) == "2026-10"))
    sal_nov = r2(sum(credit_amt(o) for o in sal_ops if month(o) == "2026-11"))
    ft_oct = r2(sum(credit_amt(o) for o in ft_ops if month(o) == "2026-10"))
    ft_nov = r2(sum(credit_amt(o) for o in ft_ops if month(o) == "2026-11"))
    int_tot = r2(sum(credit_amt(o) for o in int_ops))
    int_moy = r2(int_tot / 2)
    sal_moy = moy_fixe(sal_oct, sal_nov)
    ft_moy = moy_fixe(ft_oct, ft_nov)
    rev_moy = r2(sal_moy + ft_moy + int_moy)
    rev_conservateur = r2(sal_oct + ft_moy + int_moy)  # salaire d'octobre seulement
    rev_sans_ft = r2(sal_moy + int_moy)

    # ----- collect ops -----
    logement_ops, _ = cat_ops(d, "logement")
    transport_ops, _ = cat_ops(d, "transport")
    credit_ops, _ = cat_ops(d, "credit_revolut")
    assu_ops, _ = cat_ops(d, "assurances")
    tel_ops, _ = cat_ops(d, "telecom")
    abo_ops, _ = cat_ops(d, "abonnements")
    courses_ops, _ = cat_ops(d, "courses")
    sante_ops, _ = cat_ops(d, "sante")
    enfant_ops, _ = cat_ops(d, "enfant")
    loisirs_ops, _ = cat_ops(d, "loisirs")
    achats_ops, _ = cat_ops(d, "achats")
    autres_ops, _ = cat_ops(d, "autres")
    impot_ops, _ = cat_ops(d, "impots")
    vi_ops, vi_cat = cat_ops(d, "virements_internes")

    # pending added to November variable categories
    def with_pending(ops, cid):
        extra = [o for o in pending_by.get(cid, [])]
        return ops + extra, extra

    courses_ops, courses_pend = with_pending(courses_ops, "courses")
    sante_ops, sante_pend = with_pending(sante_ops, "sante")
    achats_ops, achats_pend = with_pending(achats_ops, "achats")
    autres_ops, autres_pend = with_pending(autres_ops, "autres")
    loisirs_ops, _ = with_pending(loisirs_ops, "loisirs")

    deco_tot, deco_par = lidl_deco(lidl)
    tex_tot, tex_par = lidl_textile(lidl)

    # ===== exceptionnels =====
    koch_ops = [o for o in sante_ops if is_koch(o)]
    koch_tot = r2(sum(amt(o) for o in koch_ops))
    remb = d.get("remboursements_operations") or []
    aon = r2(sum(credit_amt(o) for o in remb if "aon" in lib_l(o)))
    koch_net = r2(koch_tot - aon)

    decath_ops = [o for o in achats_ops if is_decathlon_nov(o)]
    decath_tot = r2(sum(amt(o) for o in decath_ops))
    amz_exc_ops = [o for o in achats_ops if is_amazon_exceptionnel(o)]
    amz_exc_tot = r2(sum(amt(o) for o in amz_exc_ops))
    salomon_ops = [o for o in achats_ops if is_salomon(o)]
    salomon_tot = r2(sum(amt(o) for o in salomon_ops))

    trip_loisir_ops = [o for o in loisirs_ops if is_trip_loisir(o)]
    trip_loisir_tot = r2(sum(amt(o) for o in trip_loisir_ops))
    trip_tr_ops = [o for o in transport_ops if is_trip_transport(o)]
    trip_tr_tot = r2(sum(amt(o) for o in trip_tr_ops))
    pot_ops = [o for o in loisirs_ops if is_pot_naissance(o)]
    pot_tot = r2(sum(amt(o) for o in pot_ops))

    ir_ops = [o for o in impot_ops if is_ir_solde(o)]
    ir_tot = r2(sum(amt(o) for o in ir_ops))

    inpi_ops = [o for o in autres_ops if is_inpi(o)]
    cci_ops = [o for o in autres_ops if is_cci(o)]
    inpi_cci_tot = r2(sum(amt(o) for o in inpi_ops + cci_ops))

    wp_ops = [o for o in abo_ops if is_wordpress(o)]
    wp_tot = r2(sum(amt(o) for o in wp_ops))
    heavy_ops = [o for o in abo_ops if is_grok_heavy(o)]
    heavy_tot = r2(sum(amt(o) for o in heavy_ops))
    grok_ap_ops = [o for o in abo_ops if is_grok_apple(o)]
    grok_ap_tot = r2(sum(amt(o) for o in grok_ap_ops))
    tv_paid = r2(sum(amt(o) for o in abo_ops if is_tradingview(o)))

    tv_mois = r2((tv.get("montant_eur_mois") if tv.get("montant_eur_mois") is not None else 15.54))
    tv_an = r2((tv.get("montant_eur_an") if tv.get("montant_eur_an") is not None else 186.48))

    def prov(id_, libelle, total, detail, n_mois=12):
        m = r2(total / n_mois) if total else 0.0
        return {
            "id": id_,
            "libelle": libelle,
            "total_periode_eur": r2(total),
            "total_periode_usd": usd(total),
            "moyenne_eur": m,
            "moyenne_usd": usd(m),
            "detail": detail,
        }

    provisions = [
        prov("dentiste_koch", "Dentiste (Dr Koch)", koch_tot,
             f"822,99 € le 27/10 + 126,37 € le 17/11 = {koch_tot:.2f} €. "
             f"Remboursements Aon déjà reçus : {aon:.2f} € (reste net {koch_net:.2f} €, à vérifier). "
             f"Lissé sur 12 mois, sorti du courant Santé."),
        prov("decathlon_nov", "Decathlon (pic de novembre)", decath_tot,
             "1 109,97 € le 14/11 + 699,97 € le 18/11. L'achat d'octobre (103,53 €) reste dans les achats courants."),
        prov("amazon_gros", "Amazon (paiements ≥ 200 €)", amz_exc_tot,
             "Dont 1 085,98 € le 13/11 et l'Amazon 264,71 € en attente du 24/11. "
             "Seuil retenu : tout paiement Amazon unitaire ≥ 200 € est traité comme exceptionnel."),
        prov("salomon", "Salomon Roppenheim", salomon_tot,
             "234,70 € le 28/10, outlet de Roppenheim. Seuil ≥ 200 €."),
        prov("deco_noel", "Déco de Noël Lidl", deco_tot,
             f"Rayon « Maison & déco (dont Noël) » des tickets Lidl : "
             f"{deco_par.get('2026-10', 0):.2f} € en octobre et {deco_par.get('2026-11', 0):.2f} € en novembre. "
             "Sorti des courses courantes."),
        prov("sejour_ramatuelle_loisirs", "Séjour Ramatuelle — loisirs", trip_loisir_tot,
             "Le Jardin des Pins 142,80 € + Yelloh ! Village 38,00 € + Le Glacier du Vin 12,00 € (20–24/10)."),
        prov("sejour_ramatuelle_transport", "Séjour Ramatuelle — transport", trip_tr_tot,
             "Péages APRR / VINCI, Eni Arlay, Avia et recharges Tesla du 20 au 26/10, hors Parking Foch (Strasbourg) et hors LOA."),
        prov("pot_naissance", "Pot de naissance (travail)", pot_tot,
             "Bastos 67, 20,93 € le 16/10. Ponctuel, confirmé par Emmanuel."),
        prov("impot_solde", "Solde impôt sur les revenus 2025", ir_tot,
             "288,00 € le 26/10 (DGFIP, facture 2667005282776). Le prélèvement à la source est déjà dans le salaire net Tesla. "
             "Aucune autre échéance d'impôt n'apparaît sur la période."),
        prov("tradingview", "TradingView Essential annuel", tv_an,
             f"186,48 €/an déjà souscrits le 25/11 (prélèvement le 6/12). Coût mensuel {tv_mois:.2f} €. "
             f"Les 83,94 € Premium encore prélevés les 7/10 et 7/11 (total {tv_paid:.2f} €) ne sont pas reconduits."),
        prov("wordpress", "WordPress (3 paiements rapprochés)", wp_tot,
             "21,60 € le 30/10, 26,40 € le 1/11 et 108,20 € le 6/11. Pas un rythme mensuel clair. "
             "Note du relevé : probable activité pro Air Glow — à confirmer. Lissé sur 12 mois."),
        prov("grok_heavy", "Grok Heavy (via Apple)", heavy_tot,
             "219,99 € le 4/11. Périodicité non confirmée. Hypothèse retenue : paiement à lisser sur 12 mois "
             f"({r2(heavy_tot/12):.2f} €/mois). Variante si l'abonnement est mensuel : +{r2(heavy_tot - heavy_tot/12):.2f} €/mois "
             "sur le budget récurrent (voir ci-dessous)."),
        prov("inpi_cci", "INPI + CCI Alsace (formalités, à confirmer)", inpi_cci_tot,
             "INPI 230,00 € le 7/10 et CCI Alsace Eurométropole 117,63 € le 17/10. "
             "Démarches ponctuelles, probable activité pro — toujours à confirmer. "
             "Lissées ici pour ne pas gonfler les « Autres » mensuels. Si c'est confirmé pro, les sortir du budget perso."),
    ]
    prov_total = r2(sum(p["moyenne_eur"] for p in provisions))

    # ===== charges fixes =====
    log_oct, log_nov = by_month(logement_ops)
    log_m = moy_fixe(log_oct, log_nov)

    loa_ops = [o for o in transport_ops if is_loa(o)]
    loa_oct, loa_nov = by_month(loa_ops)
    loa_m = moy_fixe(loa_oct, loa_nov)

    cr_oct, cr_nov = by_month(credit_ops)
    cr_m = moy_fixe(cr_oct, cr_nov)

    as_oct, as_nov = by_month(assu_ops)
    as_m = moy_fixe(as_oct, as_nov)

    # télécom : Free HD 39,99 both months ; Free Mobile only in November
    hd_ops = [o for o in tel_ops if is_free_hd(o)]
    mob_ops = [o for o in tel_ops if is_free_mobile(o) and not is_free_hd(o)]
    # fallback if classifiers miss
    if not hd_ops:
        hd_ops = [o for o in tel_ops if "telecom" in lib_l(o)]
    if not mob_ops:
        mob_ops = [o for o in tel_ops if o not in hd_ops]
    hd_m = r2(sum(amt(o) for o in hd_ops) / max(1, len({month(o) for o in hd_ops}))) if hd_ops else 0.0
    mob_tot_nov = r2(sum(amt(o) for o in mob_ops))
    tel_retenu = r2(hd_m + mob_tot_nov)  # 39.99+45.97 if mobiles only in nov
    tel_obs_oct, tel_obs_nov = by_month(tel_ops)
    tel_obs_moy = moy_fixe(tel_obs_oct, tel_obs_nov)

    # abonnements récurrents identifiés
    def monthly_if(pred):
        ops = [o for o in abo_ops if pred(o)]
        by = defaultdict(float)
        for o in ops:
            by[month(o)] += amt(o)
        months = [by[m] for m in ("2026-10", "2026-11") if abs(by[m]) > 0.001]
        # Apple credits can make a month negative — handle outside
        return ops, r2(by["2026-10"]), r2(by["2026-11"])

    rec_abos = []

    def add_abo(id_, name, pred, typ, note):
        ops, o, n = monthly_if(pred)
        if typ == "both":
            m = moy_fixe(o, n) if (o or n) else 0.0
        elif typ == "once_probable":
            # appear in one month only, keep that amount as probable monthly
            m = r2(o or n)
        else:
            m = moy_fixe(o, n)
        rec_abos.append({
            "id": id_, "libelle": name, "octobre_eur": o, "novembre_eur": n,
            "moyenne_eur": m, "moyenne_usd": usd(m), "n": len(ops), "detail": note, "type": typ,
        })
        return m

    m_ms = add_abo("microsoft", "Microsoft", is_microsoft, "both", "10,00 € les 2/10 et 3/11.")
    m_nf = add_abo("netflix", "Netflix", is_netflix, "both", "7,99 € les 15/10 et 15/11.")
    m_ds = add_abo("disney", "Disney+", is_disney, "both", "6,99 € les 16/10 et 16/11.")
    m_yt = add_abo("youtube", "YouTube", is_youtube, "both", "12,99 € les 18/10 et 18/11.")
    m_ul = add_abo("revolut_ultra", "Revolut Ultra", is_revolut_ultra, "both", "60,00 € les 7/10 et 7/11.")

    # Apple 34.95 and 4.99 (same amounts both months)
    apple_ops = [o for o in abo_ops if is_apple(o) and not is_grok_heavy(o) and not is_grok_apple(o)]
    apple_3495 = [o for o in apple_ops if o.get("sens") != "credit" and abs(amt(o) - 34.95) < 0.01]
    apple_499 = [o for o in apple_ops if o.get("sens") != "credit" and abs(amt(o) - 4.99) < 0.01]
    m_a3495 = moy_fixe(*by_month(apple_3495)) if apple_3495 else 0.0
    m_a499 = moy_fixe(*by_month(apple_499)) if apple_499 else 0.0
    rec_abos.append({"id": "apple_3495", "libelle": "Apple 34,95 €", "octobre_eur": r2(sum(amt(o) for o in apple_3495 if month(o)=="2026-10")), "novembre_eur": r2(sum(amt(o) for o in apple_3495 if month(o)=="2026-11")), "moyenne_eur": m_a3495, "moyenne_usd": usd(m_a3495), "n": len(apple_3495), "detail": "Prélèvement Apple.com/bill de 34,95 € les 20/10 et 20/11 (formule non identifiée : iCloud / Apple One / autre).", "type": "both"})
    rec_abos.append({"id": "apple_499", "libelle": "Apple 4,99 €", "octobre_eur": r2(sum(amt(o) for o in apple_499 if month(o)=="2026-10")), "novembre_eur": r2(sum(amt(o) for o in apple_499 if month(o)=="2026-11")), "moyenne_eur": m_a499, "moyenne_usd": usd(m_a499), "n": len(apple_499), "detail": "Prélèvement Apple.com/bill de 4,99 € les 22/10 et 22/11.", "type": "both"})

    m_pv = add_abo("prime_video", "Prime Video (Amazon Digital)", is_prime_video, "once_probable",
                   "Une seule échéance dans la période (6,99 € le 29/10). Retenu comme mensuel probable ; la prochaine tombée peut être après le 25/11.")
    m_gd = add_abo("grok_direct", "Grok direct (grok.com)", is_grok_direct, "once_probable",
                   "Une seule échéance (4,50 € / 5,00 $ le 26/10, SpaceXSI). Retenu comme mensuel probable, à confirmer s'il est toujours actif à côté de Grok Heavy.")

    abo_recurrent = r2(sum(a["moyenne_eur"] for a in rec_abos))

    # OVN projection (single observation)
    ovn_proj = 64.14
    ovn_obj = 20.0
    # Prefer live figure from positions if present, else known projection
    try:
        pos = json.loads((DATA / "positions.json").read_text(encoding="utf-8"))
        ovn = ((pos.get("budget") or {}).get("ovn") or {})
        if ovn.get("projection_eur") is not None:
            ovn_proj = r2(ovn["projection_eur"])
        if ovn.get("objectif_eur_mois") is not None:
            ovn_obj = r2(ovn["objectif_eur_mois"])
        ovn_dernier_usd = ovn.get("dernier_usd")
        ovn_dernier_eur = ovn.get("dernier_eur")
    except Exception:
        ovn_dernier_usd, ovn_dernier_eur = 2.34, 2.14

    # ===== variables =====
    def rec_month(ops, exclude_pred, pending_extra_already_in_ops=True):
        rec = [o for o in ops if not exclude_pred(o)]
        return by_month(rec), rec

    # courses: exclude lidl deco (not in bank ops as separate lines). Subtract deco from month totals.
    c_oct, c_nov = by_month(courses_ops)
    c_oct_r = r2(c_oct - (deco_par.get("2026-10") or 0))
    c_nov_r = r2(c_nov - (deco_par.get("2026-11") or 0))
    courses_m = moy_var(c_oct_r, c_nov_r)

    # transport hors LOA, hors séjour
    tr_var_ops = [o for o in transport_ops if not is_loa(o) and not is_trip_transport(o)]
    tr_oct, tr_nov = by_month(tr_var_ops)
    tr_m = moy_var(tr_oct, tr_nov)

    sante_rec = [o for o in sante_ops if not is_koch(o)]
    sa_oct, sa_nov = by_month(sante_rec)
    sante_m = moy_var(sa_oct, sa_nov)

    en_oct, en_nov = by_month(enfant_ops)
    enfant_m = moy_var(en_oct, en_nov)

    # ===== discrétionnaires =====
    def is_achat_exc(o):
        return is_decathlon_nov(o) or is_amazon_exceptionnel(o) or is_salomon(o)

    ach_rec = [o for o in achats_ops if not is_achat_exc(o)]
    ac_oct, ac_nov = by_month(ach_rec)
    achats_m = moy_var(ac_oct, ac_nov)

    loi_rec = [o for o in loisirs_ops if not is_trip_loisir(o) and not is_pot_naissance(o)]
    lo_oct, lo_nov = by_month(loi_rec)
    loisirs_m = moy_var(lo_oct, lo_nov)

    aut_rec = [o for o in autres_ops if not is_inpi(o) and not is_cci(o)]
    au_oct, au_nov = by_month(aut_rec)
    autres_m = moy_var(au_oct, au_nov)

    # restaurants courants (hors séjour, hors coiffeur/ongles, hors pot)
    def is_resto(o):
        l = lib_l(o)
        if is_trip_loisir(o) or is_pot_naissance(o):
            return False
        if "onglery" in l or "ciseaux" in l:
            return False
        keys = ["mcdonald", "snack", "kleber", "kléber", "stein", "thai", "selecta", "fritz schmitt"]
        return any(k in l for k in keys)

    resto_ops = [o for o in loisirs_ops if is_resto(o)]
    # Fritz may already be in courses after reclass — then it won't be in resto, which is correct
    re_oct, re_nov = by_month(resto_ops)
    resto_m = moy_var(re_oct, re_nov)

    # textile lidl monthly normalized
    tex_oct = deco_par and (tex_par.get("2026-10") or 0)
    tex_nov = tex_par.get("2026-11") or 0
    tex_m = moy_var(tex_oct, tex_nov)

    # groupes
    fixes_postes = [
        poste("logement", "Logement / loyer", log_m,
              f"Fonds Logement Intermédiaire : {log_oct:.2f} € le 5/10 et le 3/11. Charge fixe, novembre non ramené.",
              octobre_eur=log_oct, novembre_eur=log_nov, novembre_ramene_eur=log_nov),
        poste("loa_tesla", "LOA Tesla (Cofica Bail)", loa_m,
              f"486,32 € les 5/10 et 5/11. Confirmé par Emmanuel le 25/11. Charge fixe, dans Transport au relevé, isolée ici.",
              octobre_eur=loa_oct, novembre_eur=loa_nov, novembre_ramene_eur=loa_nov),
        poste("credit_revolut", "Crédit Revolut 23 500 €", cr_m,
              f"Mensualité 169,60 € les 9/10 et 9/11. Confirmé par Emmanuel. Charge fixe. Le capital n'est ni un revenu ni une dépense.",
              octobre_eur=cr_oct, novembre_eur=cr_nov, novembre_ramene_eur=cr_nov),
        poste("assurances", "Assurances / mutuelle (AXA)", as_m,
              f"Trois prélèvements AXA chaque 5 du mois, total {as_m:.2f} €/mois.",
              octobre_eur=as_oct, novembre_eur=as_nov, novembre_ramene_eur=as_nov),
        poste("telecom", "Télécom / internet", tel_retenu,
              f"Free Haut Débit {hd_m:.2f} €/mois (6/10 et 5/11). Free Mobile {mob_tot_nov:.2f} € observés seulement le 8/11 "
              f"(19,99 € + 25,98 €, probablement deux lignes). Hypothèse : ces lignes sont mensuelles et le prélèvement d'octobre "
              f"est hors période, ou elles ont démarré en novembre. Budget récurrent retenu : {tel_retenu:.2f} €. "
              f"Moyenne brute observée sans cette hypothèse : {tel_obs_moy:.2f} €.",
              octobre_eur=tel_obs_oct, novembre_eur=tel_obs_nov, novembre_ramene_eur=tel_obs_nov,
              hypothese="Free Mobile retenu à 45,97 €/mois alors qu'il n'apparaît qu'en novembre."),
        poste("abonnements", "Abonnements récurrents", abo_recurrent,
              "Somme des abonnements identifiés comme mensuels (voir la liste dans « Trous dans la raquette »). "
              "TradingView, WordPress et Grok Heavy sont dans les provisions annuelles, pas ici. "
              "Grok (via Apple) 114,99 € d'octobre n'est pas reconduit (crédit Apple 85,20 € le 4/11, probable changement de formule).",
              octobre_eur=None, novembre_eur=None, abonnements=rec_abos),
        poste("ovn", "Frais overnight CFD (projection)", ovn_proj,
              f"Une seule nuit relevée : {ovn_dernier_usd} $ ({ovn_dernier_eur} €) le 24/11 à 23 h 45. "
              f"Projection = dernier OVN × 30 jours = {ovn_proj:.2f} €. Objectif affiché sur le Budget : < {ovn_obj:.0f} €/mois. "
              "Ce n'est pas un total mensuel mesuré. Aucun frais bancaire classique n'apparaît sur les relevés (0 €).",
              hypothese="Projection à partir d'une seule observation."),
        poste("impots_recurrents", "Impôts récurrents", 0.0,
              "Le solde IR 2025 (288 €) est en provisions. Aucun autre prélèvement d'impôt sur la période ; le PAS est déjà dans le salaire net Tesla.",
              octobre_eur=0.0, novembre_eur=0.0),
        poste("energie", "Énergie", 0.0,
              "Aucune facture d'électricité ou de gaz sur les 56 jours. Possible inclusion dans le loyer, facturation trimestrielle, ou paiement hors de ces comptes — trou à vérifier.",
              octobre_eur=0.0, novembre_eur=0.0),
    ]
    fixes_tot = r2(sum(p["moyenne_eur"] for p in fixes_postes))

    pend_courses = r2(sum(amt(o) for o in courses_pend))
    pend_sante = r2(sum(amt(o) for o in sante_pend))
    pend_achats = r2(sum(amt(o) for o in achats_pend))
    pend_autres = r2(sum(amt(o) for o in autres_pend))
    pend_tot = r2(sum(amt(o) for o in pending))

    var_postes = [
        poste("courses", "Courses", courses_m,
              f"Octobre observé {c_oct:.2f} € − déco Noël {deco_par.get('2026-10', 0):.2f} € = {c_oct_r:.2f} €. "
              f"Novembre observé {c_nov:.2f} € (dont {pend_courses:.2f} € en attente Lidl/Carrefour des 23–24/11) "
              f"− déco Noël {deco_par.get('2026-11', 0):.2f} € = {c_nov_r:.2f} €, ramené à un mois : {r2(c_nov_r * SCALE_NOV):.2f} €. "
              f"Moyenne = (octobre + novembre ramené) / 2. "
              "115 paiements carte sur 49 jours distincts (plus les tickets encore en attente).",
              octobre_eur=c_oct_r, novembre_eur=c_nov_r, novembre_ramene_eur=r2(c_nov_r * SCALE_NOV)),
        poste("transport_hors_loa", "Transport hors LOA", tr_m,
              f"Péages, CTS, stationnement, carburant et recharges Tesla, hors LOA et hors trajet du séjour Ramatuelle "
              f"({trip_tr_tot:.2f} € lissés en provisions). "
              f"Octobre {tr_oct:.2f} €, novembre {tr_nov:.2f} € (surtout CTS), ramené {r2(tr_nov * SCALE_NOV):.2f} €.",
              octobre_eur=tr_oct, novembre_eur=tr_nov, novembre_ramene_eur=r2(tr_nov * SCALE_NOV)),
        poste("sante", "Santé courante", sante_m,
              f"Pharmacies et Dr Werth, hors dentiste Koch. Octobre {sa_oct:.2f} €, novembre {sa_nov:.2f} € "
              f"(dont pharmacie Pasteur 16,00 € en attente le 24/11).",
              octobre_eur=sa_oct, novembre_eur=sa_nov, novembre_ramene_eur=r2(sa_nov * SCALE_NOV)),
        poste("enfant", "Enfant / école", enfant_m,
              f"Octobre net {en_oct:.2f} € : 10 paiements Roblox (101,90 €) moins le crédit DGFIP de 36,35 € le 1/10, "
              "confirmé comme photo de classe (Collège Foch) — ce crédit réduit le poste Enfant. "
              "Rien d'autre sur les relevés en novembre au 25. Le virement de 80 € vers la poche Shana n'est pas une dépense (transfert interne).",
              octobre_eur=en_oct, novembre_eur=en_nov, novembre_ramene_eur=r2(en_nov * SCALE_NOV)),
    ]
    var_tot = r2(sum(p["moyenne_eur"] for p in var_postes))

    disc_postes = [
        poste("achats", "Achats courants", achats_m,
              f"Hors Decathlon de novembre, Amazon ≥ 200 € et Salomon. "
              f"Octobre {ac_oct:.2f} €, novembre {ac_nov:.2f} €, ramené {r2(ac_nov * SCALE_NOV):.2f} €. "
              "Reste notamment Temu, Shein, North Face, Karl Lagerfeld, petits Amazon, Normal, librairie.",
              octobre_eur=ac_oct, novembre_eur=ac_nov, novembre_ramene_eur=r2(ac_nov * SCALE_NOV)),
        poste("loisirs", "Loisirs / restaurants courants", loisirs_m,
              f"Hors séjour Ramatuelle et pot de naissance. Octobre {lo_oct:.2f} €, novembre {lo_nov:.2f} €, "
              f"ramené {r2(lo_nov * SCALE_NOV):.2f} €. Restauration courante seule : {resto_m:.2f} €/mois.",
              octobre_eur=lo_oct, novembre_eur=lo_nov, novembre_ramene_eur=r2(lo_nov * SCALE_NOV),
              restauration_courante_eur=resto_m),
        poste("autres", "Autres (courant)", autres_m,
              f"Hors INPI et CCI (provisions). Octobre {au_oct:.2f} € (MaxiZoo, X Ads), "
              f"novembre {au_nov:.2f} € (Cb Nx000018 et La Poste 18 € en attente). "
              "X Ads, MaxiZoo et le libellé tronqué restent à confirmer.",
              octobre_eur=au_oct, novembre_eur=au_nov, novembre_ramene_eur=r2(au_nov * SCALE_NOV)),
    ]
    disc_tot = r2(sum(p["moyenne_eur"] for p in disc_postes))

    dep_rec = r2(fixes_tot + var_tot + disc_tot + prov_total)
    capa_actuelle = r2(rev_moy - dep_rec)
    capa_conserv = r2(rev_conservateur - dep_rec)
    capa_sans_ft = r2(rev_sans_ft - dep_rec)

    # investissement
    inv_dets = [x for x in (d.get("totaux") or {}).get("virements_internes_detail") or [] if "investissement" in (x.get("id") or "")]
    inv_det = next((x for x in inv_dets if x.get("id") == "investissement"), None)
    inv_tot = r2(sum(float(x.get("montant_eur") or 0) for x in inv_dets))
    inv_n = sum(int(x.get("n") or 0) for x in inv_dets)
    inv_ops = []
    for o in vi_ops:
        note = (o.get("note_classification") or "") + " " + lib(o)
        low = note.lower()
        if any(k in low for k in ("xtb", "deblock", "investissement", "revolut x", "métaux", "metaux", "marge", "compte-titres", "crypto", "xag", "xau", "xpd", "xpt")):
            inv_ops.append(o)
    # Recharges Apple Pay reclassées vers XTB (détail investissement_xtb_apple_pay), côté entrants.
    apple_xtb = []
    for o in d.get("virements_internes_entrants") or []:
        note = (o.get("note_classification") or "") + " " + lib(o)
        if "xtb" in note.lower() and "apple pay" in note.lower():
            # ces lignes sont des crédits au relevé mais représentent un transfert sortant vers XTB
            rec = dict(o)
            rec["sens"] = "debit"
            apple_xtb.append(rec)
    inv_oct, inv_nov = by_month(inv_ops + apple_xtb)
    inv_moy = r2(inv_tot / 2)
    inv_note_bits = [((inv_det or {}).get("note") or "Flux vers XTB, Revolut X, marge, métaux, Deblock, compte-titres.")]
    for x in inv_dets:
        if x is not inv_det:
            inv_note_bits.append(f"{x.get('libelle')}: {x.get('montant_eur')} € ({x.get('note') or ''})")

    # ===== pistes =====
    eco_ovn = r2(max(0.0, ovn_proj - ovn_obj))
    eco_ultra = m_ul
    eco_tex_half = r2(tex_m / 2)
    eco_resto_half = r2(resto_m / 2)
    eco_youtube = m_yt
    eco_heavy_annuel = r2(heavy_tot / 12)  # already in provisions; cancelling annual after this year
    eco_heavy_mensuel = heavy_tot
    video_stack = r2(m_nf + m_ds + m_yt + m_pv)

    pistes = [
        {
            "id": "ovn",
            "libelle": "Tenir l'objectif de frais overnight CFD (< 20 €/mois)",
            "economie_eur_mois": eco_ovn,
            "economie_usd_mois": usd(eco_ovn),
            "source": f"Projection actuelle {ovn_proj:.2f} € (2,34 $ × 30 jours, une seule nuit le 24/11) − objectif 20 €.",
            "note": "Proposition, pas une décision. La projection repose sur une seule observation ; elle sera affinée quand d'autres nuits seront relevées. Réduire l'exposition overnight (ou fermer avant la clôture) est le levier.",
            "dans_panier_cible": True,
        },
        {
            "id": "revolut_ultra",
            "libelle": "Revoir ou résilier Revolut Ultra",
            "economie_eur_mois": eco_ultra,
            "economie_usd_mois": usd(eco_ultra),
            "source": "Deux prélèvements de 60,00 € les 7/10 et 7/11.",
            "note": "Proposition. L'économie maximale est 60 €/mois en cas de résiliation. Une formule inférieure n'est pas chiffrée ici (tarif non sourcé dans les relevés).",
            "dans_panier_cible": True,
        },
        {
            "id": "youtube",
            "libelle": "Revoir le stack vidéo (YouTube, Netflix, Disney+, Prime Video)",
            "economie_eur_mois": eco_youtube,
            "economie_usd_mois": usd(eco_youtube),
            "source": f"YouTube 12,99 € + Netflix 7,99 € + Disney+ 6,99 € + Prime Video 6,99 € = {video_stack:.2f} €/mois.",
            "note": "Proposition : l'économie retenue dans la cible est celle de YouTube seul (le plus cher, 12,99 €), si tu conserves les autres. Économie maximale si un seul abonnement vidéo est gardé : à calculer selon celui que tu gardes.",
            "dans_panier_cible": True,
        },
        {
            "id": "textile_lidl",
            "libelle": "Réduire de moitié le textile Lidl (hors déco déjà lissée)",
            "economie_eur_mois": eco_tex_half,
            "economie_usd_mois": usd(eco_tex_half),
            "source": f"Textile Lidl {tex_par.get('2026-10', 0):.2f} € en octobre et {tex_par.get('2026-11', 0):.2f} € en novembre, moyenne ramenée {tex_m:.2f} €/mois (tickets Lidl).",
            "note": "Proposition : moitié du rythme observé, sans viser zéro. Le non-alimentaire Lidl de novembre dépasse déjà l'alimentaire.",
            "dans_panier_cible": True,
        },
        {
            "id": "restauration",
            "libelle": "Réduire de moitié la restauration courante",
            "economie_eur_mois": eco_resto_half,
            "economie_usd_mois": usd(eco_resto_half),
            "source": f"McDonald's, snacks, cafés, restaurants hors séjour Ramatuelle : {resto_m:.2f} €/mois après ramener novembre.",
            "note": "Proposition : moitié du rythme observé. Le séjour est déjà sorti du courant et lissé en provisions.",
            "dans_panier_cible": True,
        },
        {
            "id": "grok_heavy",
            "libelle": "Clarifier puis éventuellement résilier Grok Heavy",
            "economie_eur_mois": eco_heavy_annuel,
            "economie_usd_mois": usd(eco_heavy_annuel),
            "economie_si_mensuel_eur": eco_heavy_mensuel,
            "source": "Apple.com/bill 219,99 € le 4/11, confirmé « Grok Heavy ».",
            "note": "Si l'abonnement est annuel (hypothèse du budget récurrent), il est déjà lissé à "
                    f"{eco_heavy_annuel:.2f} €/mois : le résilier ne change la cible qu'à la prochaine échéance. "
                    f"S'il est mensuel, l'économie est {eco_heavy_mensuel:.2f} €/mois — c'est alors le premier levier. "
                    "Les trois formules Grok (114,99 € via Apple en octobre, 4,50 € grok.com, 219,99 € Heavy) sont un doublon possible.",
            "dans_panier_cible": False,
        },
        {
            "id": "pro_airglow",
            "libelle": "Sortir du budget perso les formalités et pubs encore floues si elles sont pour Air Glow",
            "economie_eur_mois": r2(inpi_cci_tot / 12 + 22.27 / 2),  # rough, refined below
            "economie_usd_mois": None,
            "source": "INPI 230 €, CCI 117,63 €, X Ads 22,27 €, Envato 87,97 €, WordPress 156,20 €.",
            "note": "À confirmer une par une. INPI et CCI sont déjà lissés en provisions (et sortiraient complètement si c'est pro). "
                    "X Ads et Envato sont encore dans le courant. WordPress est en provisions, noté « probable pro ».",
            "dans_panier_cible": False,
        },
    ]
    # refine pro Air Glow saving if confirmed: provisions inpi/cci + wp + envato left in achats + x ads in autres
    xads = r2(sum(amt(o) for o in aut_rec if "x corp" in lib_l(o)))
    xads_oct, xads_nov = by_month([o for o in aut_rec if "x corp" in lib_l(o)])
    xads_m = moy_var(xads_oct, xads_nov)
    envato_tot = r2(sum(amt(o) for o in ach_rec if "envato" in lib_l(o)))
    envato_m = r2(envato_tot / 2)  # one-off in period, observed monthly avg without scaling much
    # actually envato is in oct achats recurring. If we remove it as pro one-off, courses... it's in achats_m.
    # For the piste, if all confirmed pro: inpi_cci already in provisions (28.97) would leave personal budget,
    # wp provision 13.02 would leave, xads_m leave autres, envato leave achats.
    eco_pro = r2(inpi_cci_tot / 12 + (wp_tot / 12) + xads_m + r2(envato_tot * SCALE_NOV / 2 if False else envato_tot / 2))
    # envato only in October, it's in ac_oct. Removing it would change achats_m by envato_tot/2 (not scaled, it's oct).
    # Use: inpi_cci/12 + wp/12 + xads_m + envato contribution to achats_m
    # envato is only oct 87.97, contribution to moy_var is 87.97/2 = 43.985
    eco_pro = r2(inpi_cci_tot / 12 + wp_tot / 12 + xads_m + r2(envato_tot / 2))
    for p in pistes:
        if p["id"] == "pro_airglow":
            p["economie_eur_mois"] = eco_pro
            p["economie_usd_mois"] = usd(eco_pro)

    panier = [p for p in pistes if p.get("dans_panier_cible")]
    eco_panier = r2(sum(p["economie_eur_mois"] for p in panier))
    capa_cible = r2(capa_actuelle + eco_panier)
    capa_cible_heavy_mensuel = r2(capa_actuelle - r2(heavy_tot - heavy_tot / 12) + eco_panier + eco_heavy_mensuel)
    # If heavy is monthly: current recurring should add (219.99-18.33), capacity decreases, then cancelling adds 219.99
    # net vs our baseline current: -201.66 + 219.99 + panier = +18.33 + panier, i.e. capa_actuelle + panier + 18.33
    # Wait: if heavy is monthly, capa_actuelle_true = capa_actuelle - (219.99-18.33)
    # after cancel heavy: +219.99, plus panier. Target = capa_actuelle - 201.66 + 219.99 + panier = capa_actuelle + 18.33 + panier
    # Yes capa_cible_heavy_mensuel as computed: capa_actuelle - 201.66 + panier + 219.99

    # objectif d'épargne proposé
    # conservative income capacity as a floor, target package as a stretch, propose a round number in between or the conservative
    # I'll propose min(1500, round capa_conserv or 1000) — don't invent: propose the conservative capacity rounded down to 100, and the target package as "cible si réductions + salaire moyen".
    def floor100(x):
        return int(x // 100 * 100)

    obj_souple = floor100(max(0, capa_conserv))  # based on October salary
    obj_cible = floor100(max(0, capa_cible))

    charges_fixes_reserve = r2(log_m + loa_m + cr_m + as_m + tel_retenu + abo_recurrent)  # without OVN (stoppable)
    reserve_3 = r2(charges_fixes_reserve * 3)
    reserve_6 = r2(charges_fixes_reserve * 6)

    # courses frequency
    courses_bank = [o for o in courses_ops if not o.get("statut") == "en_attente"]
    jours = {o.get("date") for o in courses_bank}
    jours_oct = {o.get("date") for o in courses_bank if month(o) == "2026-10"}
    jours_nov = {o.get("date") for o in courses_bank if month(o) == "2026-11"}
    from collections import Counter
    merch = Counter(lib(o) for o in courses_bank)
    merch_amt = defaultdict(float)
    for o in courses_bank:
        merch_amt[lib(o)] += amt(o)

    # trous
    trous = [
        {
            "id": "abonnements",
            "titre": "Abonnements récurrents identifiés",
            "detail": "Liste ci-dessous, avec les formules Grok empilées et TradingView déjà baissé à Essential.",
        },
        {
            "id": "grok_stack",
            "titre": "Stack Grok potentiellement en double",
            "detail": f"Grok (via Apple) {grok_ap_tot:.2f} € le 26/10, Grok direct 4,50 € le 26/10, Grok Heavy {heavy_tot:.2f} € le 4/11. "
                      "Crédit Apple 85,20 € le 4/11 : probable ajustement de formule, à confirmer. Trois libellés pour un même outil.",
        },
        {
            "id": "frequence_courses",
            "titre": f"Fréquence des courses : {len(courses_bank)} paiements carte, {len(jours)} jours distincts sur 56",
            "detail": f"Octobre : {len(jours_oct)} jours / {sum(1 for o in courses_bank if month(o)=='2026-10')} paiements. "
                      f"Novembre au 25 : {len(jours_nov)} jours / {sum(1 for o in courses_bank if month(o)=='2026-11')} paiements, "
                      "plus les tickets encore en attente. Panier Lidl moyen 23–26 €, beaucoup de petits passages. "
                      + " · ".join(f"{k} {v}× ({r2(merch_amt[k]):.2f} €)" for k, v in merch.most_common()),
        },
        {
            "id": "non_alim_lidl",
            "titre": "Non-alimentaire Lidl, surtout en novembre",
            "detail": f"Novembre : non-alimentaire 262,76 € > alimentaire 224,04 € (tickets au 24). "
                      f"Dont déco Noël {deco_par.get('2026-11', 0):.2f} € (déjà lissée) et textile {tex_par.get('2026-11', 0):.2f} €.",
        },
        {
            "id": "ovn_frais",
            "titre": "Frais overnight CFD au-dessus de l'objectif",
            "detail": f"Projection {ovn_proj:.2f} €/mois vs objectif {ovn_obj:.0f} € (ratio observé sur une nuit). "
                      "Aucun frais bancaire classique sur les relevés. Les frais d'ordres restent à relever (APE-38).",
        },
        {
            "id": "energie",
            "titre": "Pas de facture d'énergie sur 56 jours",
            "detail": "À vérifier : incluse dans le loyer, prélevée ailleurs, ou trimestrielle hors période.",
        },
        {
            "id": "pret",
            "titre": "Crédit Revolut 23 500 € et vague d'investissement de novembre",
            "detail": f"Mensualité 169,60 € déjà dans les charges fixes. Le capital a été viré le 6/11 vers FR76…20176 (clôturé le 16/11). "
                      f"Les versements vers l'investissement atteignent {inv_tot:.2f} € sur la période "
                      f"(octobre {inv_oct:.2f} €, novembre {inv_nov:.2f} €), soit bien plus que le reste du budget. "
                      "Une partie de l'épargne de novembre a pu être financée par le prêt, pas par un excédent mensuel. "
                      "Ce prêt a un coût : il s'ajoute à un budget qui, en flux observé (non lissé), était dans le rouge en octobre.",
        },
    ]

    floues = []
    for o in d.get("operations_ambigues") or []:
        floues.append({
            "sujet": o.get("sujet") or o.get("libelle"),
            "montant_eur": o.get("montant_eur"),
            "montant_usd": usd(o.get("montant_eur")),
            "classification": o.get("classification"),
            "question": o.get("question"),
        })
    # always useful extras
    extra_floues_ids = {f.get("sujet") for f in floues}
    extras = [
        {"sujet": "Périodicité de Grok Heavy (219,99 € le 4/11)", "montant_eur": heavy_tot,
         "montant_usd": usd(heavy_tot), "classification": "abonnements",
         "question": "Abonnement mensuel ou annuel ? Cela change le budget récurrent de près de 200 €/mois."},
        {"sujet": "WordPress 21,60 + 26,40 + 108,20 €", "montant_eur": wp_tot,
         "montant_usd": usd(wp_tot), "classification": "abonnements",
         "question": "Activité pro Air Glow ? Ponctuel ou abonnement ?"},
        {"sujet": "Apple 34,95 € et 4,99 € / mois", "montant_eur": r2(m_a3495 + m_a499),
         "montant_usd": usd(m_a3495 + m_a499), "classification": "abonnements",
         "question": "Quelles formules exactes (iCloud, Apple One, apps) ?"},
        {"sujet": "Free Mobile 19,99 € + 25,98 € (8/11 seulement)", "montant_eur": mob_tot_nov,
         "montant_usd": usd(mob_tot_nov), "classification": "telecom",
         "question": "Deux lignes mensuelles déjà en cours en octobre (prélèvement hors période) ou nouvelles lignes ?"},
        {"sujet": "Facture d'énergie absente", "montant_eur": 0, "montant_usd": 0,
         "classification": "energie", "question": "Où est payée l'électricité / le gaz ?"},
    ]
    for e in extras:
        if not any(e["sujet"][:20].lower() in (s or "").lower() for s in extra_floues_ids):
            floues.append(e)

    methodes = [
        "Période source : 1er octobre – 25 novembre 2026 (56 jours), comptes perso et joint fusionnés, change 1,0944.",
        "Les charges fixes (loyer, LOA, crédit, assurances, télécom, abonnements mensuels identifiés) ne sont pas ramenées : si l'échéance de novembre est déjà passée avant le 25, le mois est complet.",
        "Les postes variables et discrétionnaires de novembre (25 jours sur 30) sont ramenés à un mois entier : novembre × 30/25, puis moyenne avec octobre : (octobre + novembre ramené) / 2.",
        f"Les 6 opérations « en attente » des 23–24/11 ({pend_tot:.2f} €), hors soldes du relevé, sont intégrées aux postes variables de novembre pour ne pas sous-estimer le rythme "
        f"(Amazon {pend_achats:.2f} €, courses {pend_courses:.2f} €, La Poste {pend_autres:.2f} €, pharmacie {pend_sante:.2f} €).",
        "Les dépenses exceptionnelles identifiées sont sorties du courant et lissées sur 12 mois dans « Provisions annuelles » "
        "(dentiste Koch, Decathlon de novembre, Amazon ≥ 200 €, Salomon, déco de Noël Lidl, séjour Ramatuelle, pot de naissance, solde IR 2025, TradingView annuel, WordPress, Grok Heavy, INPI + CCI).",
        "Règle des achats exceptionnels : tout paiement unitaire ≥ 200 € dans Achats, plus les pics nommément identifiés (Decathlon de novembre, déco de Noël).",
        "Le salaire Tesla n'est pas ramené (paiement mensuel déjà reçu en novembre). Moyenne = moyenne arithmétique des deux bulletins (4 169,59 € en octobre, 6 315,41 € en novembre). "
        "Échantillon de deux mois seulement : novembre est supérieur de 51 % à octobre (heures, prime ou rattrapage possibles). Une variante conservative utilise le seul salaire d'octobre.",
        "France Travail : 876,60 € les 1/10 et 2/11. Revenu qui peut s'arrêter. Une variante de capacité d'épargne l'exclut.",
        "Grok Heavy : périodicité inconnue. Hypothèse retenue = lissage annuel. La variante « mensuel » est chiffrée à part.",
        "Free Mobile : retenu à 45,97 €/mois alors qu'il n'apparaît que le 8/11.",
        "Les virements vers l'investissement ne sont pas des dépenses. Ils sont affichés à part comme épargne réalisée. "
        "Le crédit Revolut 23 500 € n'est ni un revenu ni une dépense ; sa mensualité est une charge fixe.",
        "Air Glow pub (Facebook, MailPoet, Dualhook) reste hors des dépenses personnelles, comme dans le bloc Comptes.",
        "Tous les montants viennent des fichiers data/budget et de l'abonnement TradingView / de la projection OVN déjà suivis sur le site. Rien n'est inventé.",
    ]

    out = {
        "id": "budget_mensuel_moyen",
        "titre": "Budget mensuel moyen",
        "periode": d.get("periode") or {"debut": "2026-10-01", "fin": "2026-11-25", "libelle": "1er octobre – 25 novembre 2026"},
        "fx": {"taux": FX, "paire": "EURUSD", "source": "Taux déjà utilisé sur le site APEX (1,0944)."},
        "methode": {
            "jours_octobre": 31,
            "jours_novembre_observes": JOURS_NOV_OBSERVES,
            "jours_novembre_complets": JOURS_NOV_COMPLETS,
            "coefficient_novembre_variables": SCALE_NOV,
            "formule_variables": "(octobre + novembre × 30/25) / 2",
            "formule_fixes": "(octobre + novembre observé) / 2, ou mensualité contractuelle",
            "en_attente_inclus_eur": pend_tot,
            "hypotheses": methodes,
        },
        "revenus": {
            "salaire_tesla": {
                "octobre_eur": sal_oct, "octobre_usd": usd(sal_oct),
                "novembre_eur": sal_nov, "novembre_usd": usd(sal_nov),
                "moyenne_eur": sal_moy, "moyenne_usd": usd(sal_moy),
                "note": "Salaire Tesla France, réf. Salary 102026 (22/10, 4 169,59 €) et Salary 112026 (24/11, 6 315,41 €). "
                        f"Moyenne arithmétique des deux bulletins : {sal_moy:.2f} €. Novembre est supérieur de 51 % à octobre. "
                        "Échantillon court : la moyenne peut être trop haute si novembre inclut un rattrapage ou des heures exceptionnelles.",
            },
            "france_travail": {
                "octobre_eur": ft_oct, "novembre_eur": ft_nov,
                "moyenne_eur": ft_moy, "moyenne_usd": usd(ft_moy),
                "note": "876,60 € le 1/10 et le 2/11 (France Travail Grand Est). Revenu mensuel régulier sur la période, qui peut s'arrêter.",
            },
            "interets_epargne": {
                "periode_eur": int_tot, "moyenne_eur": int_moy, "moyenne_usd": usd(int_moy),
                "note": f"{int_tot:.2f} € d'intérêts du dépôt Revolut en novembre, soit {int_moy:.2f} €/mois en moyenne. Montant négligeable.",
            },
            "total_moyenne_eur": rev_moy,
            "total_moyenne_usd": usd(rev_moy),
            "variante_salaire_octobre_eur": rev_conservateur,
            "variante_salaire_octobre_usd": usd(rev_conservateur),
            "variante_sans_france_travail_eur": rev_sans_ft,
            "variante_sans_france_travail_usd": usd(rev_sans_ft),
        },
        "groupes": [
            {"id": "fixes", "libelle": "Charges fixes", "note": "Loyer, LOA, crédit, assurances, télécom, abonnements mensuels, projection OVN. Novembre non ramené.", "postes": fixes_postes, "total_moyenne_eur": fixes_tot, "total_moyenne_usd": usd(fixes_tot)},
            {"id": "variables", "libelle": "Variables courantes", "note": "Courses, transport hors LOA, santé courante, enfant. Novembre ramené à 30 jours. Exceptionnels sortis.", "postes": var_postes, "total_moyenne_eur": var_tot, "total_moyenne_usd": usd(var_tot)},
            {"id": "discretionnaires", "libelle": "Discrétionnaires", "note": "Achats, loisirs et autres courants, après sortie des pics. Novembre ramené à 30 jours.", "postes": disc_postes, "total_moyenne_eur": disc_tot, "total_moyenne_usd": usd(disc_tot)},
        ],
        "provisions": {
            "libelle": "Provisions annuelles",
            "note": "Dépenses exceptionnelles ou annuelles de la période, lissées sur 12 mois, pour ne pas les laisser gonfler le budget récurrent ni les oublier.",
            "lignes": provisions,
            "total_moyenne_eur": prov_total,
            "total_moyenne_usd": usd(prov_total),
        },
        "depenses_recurrentes": {
            "moyenne_eur": dep_rec,
            "moyenne_usd": usd(dep_rec),
            "detail": "Somme des charges fixes, variables courantes, discrétionnaires et provisions annuelles / 12.",
        },
        "epargne_realisee": {
            "libelle": "Vers l'investissement (épargne réalisée, pas une dépense)",
            "periode_eur": inv_tot,
            "periode_usd": usd(inv_tot),
            "octobre_eur": inv_oct,
            "novembre_eur": inv_nov,
            "moyenne_eur": inv_moy,
            "moyenne_usd": usd(inv_moy),
            "n": inv_n,
            "note": " ".join(inv_note_bits),
            "lignes": [{"id": x.get("id"), "libelle": x.get("libelle"), "montant_eur": x.get("montant_eur"), "montant_usd": usd(x.get("montant_eur")), "n": x.get("n"), "note": x.get("note")} for x in inv_dets],
            "alerte": "Le flux de novembre est très supérieur à celui d'octobre et au reste du budget (revenus − dépenses). "
                      "Il a pu être alimenté par le crédit Revolut de 23 500 € (capital viré le 6/11, compte destinataire clôturé le 16/11), "
                      "pas seulement par un excédent mensuel. Ce n'est donc pas une capacité d'épargne récurrente.",
        },
        "capacite_actuelle": {
            "eur": capa_actuelle,
            "usd": usd(capa_actuelle),
            "formule": "Revenus mensuels moyens (salaire moyen + France Travail + intérêts) − dépenses récurrentes moyennes (y compris provisions / 12).",
            "variante_salaire_octobre_eur": capa_conserv,
            "variante_salaire_octobre_usd": usd(capa_conserv),
            "variante_sans_france_travail_eur": capa_sans_ft,
            "variante_sans_france_travail_usd": usd(capa_sans_ft),
        },
        "trous": trous,
        "abonnements": rec_abos,
        "pistes": pistes,
        "panier_cible": {
            "libelle": "Panier de propositions retenu pour la capacité cible",
            "note": "Ce n'est pas une décision. Cinq leviers chiffrés à partir des relevés : OVN sous l'objectif, résiliation Revolut Ultra, résiliation YouTube, moitié du textile Lidl, moitié de la restauration courante. Grok Heavy et le reclassement pro sont chiffrés à part, faute de confirmation.",
            "lignes": [{"id": p["id"], "libelle": p["libelle"], "economie_eur_mois": p["economie_eur_mois"], "economie_usd_mois": p["economie_usd_mois"]} for p in panier],
            "total_economie_eur": eco_panier,
            "total_economie_usd": usd(eco_panier),
        },
        "capacite_cible": {
            "eur": capa_cible,
            "usd": usd(capa_cible),
            "formule": "Capacité actuelle + somme du panier de propositions.",
            "variante_grok_heavy_mensuel_eur": r2(capa_actuelle - r2(heavy_tot - heavy_tot / 12)),
            "variante_grok_heavy_mensuel_cible_eur": capa_cible_heavy_mensuel,
            "variante_grok_heavy_mensuel_note": f"Si Grok Heavy est mensuel, la capacité actuelle baisse de {r2(heavy_tot - heavy_tot/12):.2f} € "
                                               f"(on remplace le lissage annuel par 219,99 €/mois). La résiliation de Heavy devient alors le premier levier "
                                               f"({heavy_tot:.2f} €/mois) et la cible après panier + résiliation serait {capa_cible_heavy_mensuel:.2f} €.",
        },
        "objectif_epargne": {
            "propose_eur": obj_souple,
            "propose_usd": usd(obj_souple),
            "note": f"Objectif proposé : {obj_souple} €/mois, arrondi inférieur à 100 € de la capacité calculée avec le seul salaire d'octobre "
                    f"({capa_conserv:.2f} €). C'est volontairement prudent tant que le salaire de novembre (6 315,41 €) n'est pas confirmé comme un rythme normal, "
                    f"et tant que France Travail peut s'arrêter. Si le salaire moyen se confirme et si le panier de réductions est suivi, "
                    f"la cible calculée est {capa_cible:.2f} €/mois (objectif arrondi {obj_cible} €).",
            "cible_si_reductions_eur": obj_cible,
        },
        "reserve_securite": {
            "charges_fixes_eur": charges_fixes_reserve,
            "charges_fixes_usd": usd(charges_fixes_reserve),
            "detail": "Loyer + LOA Tesla + crédit Revolut + assurances + télécom + abonnements mensuels identifiés, hors OVN (réductible en fermant les positions) et hors provisions.",
            "mois_3_eur": reserve_3, "mois_3_usd": usd(reserve_3),
            "mois_6_eur": reserve_6, "mois_6_usd": usd(reserve_6),
            "note": "Réserve conseillée : 3 à 6 mois de charges fixes, soit "
                    f"{reserve_3:.2f} € à {reserve_6:.2f} €. Ce n'est pas un ordre de virement. Les soldes actuels des deux comptes sont bien en dessous de ce niveau ; "
                    "le crédit de 23 500 € n'est pas une réserve.",
        },
        "lignes_floues": floues,
        "source": {
            "comptes": "data/budget/comptes_2026-10_11.json",
            "lidl": "data/budget/lidl_tickets_2026-10_11.json",
            "tradingview": "data/abonnement_tradingview.json et budget.tradingview",
            "ovn": "budget.ovn (positions.json)",
            "genere_par": "src/build_budget_mensuel.py",
        },
    }
    return out


def attach_to_positions(payload):
    for path in (DATA / "positions.json", ROOT / "positions.json"):
        if not path.exists():
            continue
        book = json.loads(path.read_text(encoding="utf-8"))
        bud = book.get("budget")
        if not isinstance(bud, dict):
            continue
        bud["budget_mensuel"] = payload
        path.write_text(json.dumps(book, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print("attaché", path)


def main():
    payload = build()
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("écrit", OUT)
    attach_to_positions(payload)
    # résumé console
    r = payload["revenus"]
    print("revenus moyens", payload["revenus"]["total_moyenne_eur"])
    for g in payload["groupes"]:
        print(g["id"], g["total_moyenne_eur"])
        for p in g["postes"]:
            print("  ", p["id"], p["moyenne_eur"])
    print("provisions", payload["provisions"]["total_moyenne_eur"])
    print("depenses recurrentes", payload["depenses_recurrentes"]["moyenne_eur"])
    print("capacite actuelle", payload["capacite_actuelle"]["eur"])
    print("panier", payload["panier_cible"]["total_economie_eur"])
    print("capacite cible", payload["capacite_cible"]["eur"])
    print("investissement", payload["epargne_realisee"]["periode_eur"], "oct", payload["epargne_realisee"]["octobre_eur"], "nov", payload["epargne_realisee"]["novembre_eur"])


if __name__ == "__main__":
    main()
