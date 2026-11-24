#!/usr/bin/env python3
"""Construit positions.json, positions_revolut.json et positions_revolutx.json
à partir du relevé courtier du jour (JSON). Les lignes absentes du relevé sont
retirées. Un ordre d'achat en cours est une position déjà active (statut
en_attente, montant = coût total prévu, P/L 0). CFD exclus des listes.
"""
from __future__ import annotations

import hashlib, json, math
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
RELEVE = DATA / "revolut" / "releve_courtiers_2026-11-24.json"
PARIS = ZoneInfo("Europe/Paris")

# Métadonnées APEX (tickers TV, onglets, dates d'achat déjà connues).
# Les dates 19/11 ne sont conservées que si la quantité est inchangée
# (même lot). Aucune date n'est inventée.
META = {
    "NFLX": {"nom": "Netflix", "type": "equity", "tab": "actions",
             "tv_note": "NASDAQ:NFLX", "fiche_tv": "NASDAQ:NFLX", "fiche_nom": "Netflix, Inc.",
             "fiche_proxy": False, "note_tv_ok": True},
    "FUC": {"nom": "Fanuc Corporation", "type": "equity", "tab": "actions",
            "tv_note": "XETR:FUC", "fiche_tv": "TSE:6954",
            "fiche_nom": "Fanuc Corporation (TSE:6954, même titre que FUC à Francfort)",
            "fiche_proxy": True, "note_tv_ok": True,
            "fiche_note": "Position ouverte sur Francfort/Xetra (FUC) le 19/11/2026 ; fiche APEX : cotation Tokyo 6954.",
            "date_ordre": "2026-11-18", "date_execution": "2026-11-19T08:00:00+01:00",
            "keep_qty": 22.59053425, "perf_1an_yahoo": "6954.T"},
    "PPX": {"nom": "Kering", "type": "equity", "tab": "actions",
            "tv_note": "XETR:PPX", "fiche_tv": "EURONEXT:KER",
            "fiche_nom": "Kering SA (EURONEXT:KER, même titre que PPX à Francfort)",
            "fiche_proxy": True, "note_tv_ok": True,
            "fiche_note": "Position ouverte sur Francfort/Xetra (PPX) le 19/11/2026 ; fiche APEX : cotation Paris KER.",
            "date_ordre": "2026-11-18", "date_execution": "2026-11-19T08:00:00+01:00",
            "keep_qty": 3.81716432},
    "HMI": {"nom": "Hermès International", "type": "equity", "tab": "actions",
            "tv_note": "XETR:HMI", "fiche_tv": "EURONEXT:RMS",
            "fiche_nom": "Hermès International (EURONEXT:RMS, même titre que HMI à Francfort)",
            "fiche_proxy": True, "note_tv_ok": True,
            "fiche_note": "Position ouverte sur Francfort/Xetra (HMI) le 19/11/2026 ; fiche APEX : cotation Paris RMS.",
            "date_ordre": "2026-11-18", "date_execution": "2026-11-19T08:00:00+01:00",
            "keep_qty": 0.53251224},
    "URNU": {"nom": "Global X Uranium UCITS ETF", "type": "etf", "tab": "energie",
             "tv_note": "XETR:URNU", "fiche_tv": "XETR:URNU", "fiche_nom": "ETF uranium URNU (UCITS)",
             "fiche_proxy": False, "note_tv_ok": True,
             "date_ordre": "2026-11-18", "date_execution": "2026-11-19T08:00:00+01:00",
             "keep_qty": 43.39691628},
    "DASH": {"nom": "DoorDash", "type": "equity", "tab": "actions",
             "tv_note": "NASDAQ:DASH", "fiche_tv": "NASDAQ:DASH", "fiche_nom": "DoorDash, Inc.",
             "fiche_proxy": False, "note_tv_ok": True},
    "VACD": {"nom": "Vallourec S.A.", "type": "equity", "tab": "actions",
             "tv_note": "VACD", "fiche_tv": "EURONEXT:VK",
             "fiche_nom": "Vallourec S.A. (EURONEXT:VK, même titre que VACD chez Revolut)",
             "fiche_proxy": True, "note_tv_ok": True,
             "fiche_note": "Position Revolut sous le ticker VACD ; fiche APEX : cotation Paris EURONEXT:VK."},
    "XHYG": {"nom": "Xtrackers Euro High Yield Corporate Bond Dist ETF", "type": "etf", "tab": "obligations",
             "tv_note": "XETR:XHYG", "fiche_tv": "XETR:XHYG",
             "fiche_nom": "Xtrackers II EUR High Yield Corporate Bond UCITS ETF 1D",
             "fiche_proxy": False, "note_tv_ok": True},
    "RDDT": {"nom": "Reddit", "type": "equity", "tab": "actions",
             "tv_note": "NYSE:RDDT", "fiche_tv": "NYSE:RDDT", "fiche_nom": "Reddit, Inc.",
             "fiche_proxy": False, "note_tv_ok": True},
    "XUTL": {"nom": "Xtrackers II US Treasuries 10+ UCITS ETF 1D", "type": "etf", "tab": "obligations",
             "tv_note": "XETR:XUTL", "fiche_tv": "XETR:XUTL",
             "fiche_nom": "Xtrackers II US Treasuries 10+ UCITS ETF 1D",
             "fiche_proxy": False, "note_tv_ok": True},
    "BKNG": {"nom": "Booking Holdings", "type": "equity", "tab": "actions",
             "tv_note": "NASDAQ:BKNG", "fiche_tv": "NASDAQ:BKNG", "fiche_nom": "Booking Holdings Inc.",
             "fiche_proxy": False, "note_tv_ok": True},
    "CAT": {"nom": "Caterpillar Inc.", "type": "equity", "tab": "actions",
            "tv_note": "NYSE:CAT", "fiche_tv": "NYSE:CAT", "fiche_nom": "Caterpillar Inc.",
            "fiche_proxy": False, "note_tv_ok": True},
    "AVGO": {"nom": "Broadcom Inc.", "type": "equity", "tab": "actions",
             "tv_note": "NASDAQ:AVGO", "fiche_tv": "NASDAQ:AVGO", "fiche_nom": "Broadcom Inc.",
             "fiche_proxy": False, "note_tv_ok": True},
    "XAU": {"nom": "Or", "type": "metal", "tab": "metaux",
            "tv_note": "XAU", "fiche_tv": "XAU", "fiche_nom": "Or au comptant Revolut (XAU)",
            "fiche_proxy": False, "note_tv_ok": False,
            "fiche_note": "Métal au comptant Revolut (XAU), acheté le 24/11/2026. Pas d'instrument XAU dans la liste ETC de l'onglet Métaux.",
            "date_achat": "2026-11-24"},
    "XAG": {"nom": "Argent", "type": "metal", "tab": "metaux",
            "tv_note": "OANDA:XAGUSD", "fiche_tv": "OANDA:XAGUSD", "fiche_nom": "Argent au comptant Revolut",
            "fiche_proxy": False, "note_tv_ok": True, "date_achat": "2026-11-24"},
    "XPT": {"nom": "Platine", "type": "metal", "tab": "metaux",
            "tv_note": "OANDA:XPTUSD", "fiche_tv": "OANDA:XPTUSD", "fiche_nom": "Platine au comptant Revolut",
            "fiche_proxy": False, "note_tv_ok": True, "date_achat": "2026-11-24"},
    "XPD": {"nom": "Palladium", "type": "metal", "tab": "metaux",
            "tv_note": "OANDA:XPDUSD", "fiche_tv": "OANDA:XPDUSD", "fiche_nom": "Palladium au comptant Revolut",
            "fiche_proxy": False, "note_tv_ok": True, "date_achat": "2026-11-24"},
    "ETH": {"nom": "Ether", "type": "crypto", "tab": "crypto",
            "tv_note": "ETH", "fiche_tv": "ETH", "fiche_nom": "Ether",
            "fiche_proxy": False, "note_tv_ok": True,
            "fiche_note": "Prix de revient FIFO d'après l'historique revx trade private ETH-USD (aucun trade ETH-EUR). Coût moyen 1 809,07 $ / ETH conservé (quantité inchangée, 0,28)."},
    "MAU": {"nom": "Etablissements Maurel et Prom", "type": "equity", "tab": "energie",
            "tv_note": "EURONEXT:MAU", "fiche_tv": "EURONEXT:MAU",
            "fiche_nom": "Etablissements Maurel & Prom S.A.",
            "fiche_proxy": False, "note_tv_ok": True},
}


def r2(x, n=2):
    return round(float(x) + 1e-12, n)


def r0(x):
    return int(round(float(x) + 1e-12))


def signed_pct(pl, pct, investi):
    """Le relevé Revolut donne souvent un % non signé ; le signe suit pl."""
    if investi and abs(investi) > 1e-9:
        return r2(100.0 * pl / investi)
    if pct is None:
        return None
    p = float(pct)
    if pl is None:
        return r2(p)
    if pl < 0 and p > 0:
        return r2(-p)
    if pl > 0 and p < 0:
        return r2(abs(p))
    return r2(p)


def parse_fr_dt(s, default_hm="12:00"):
    """'24/11 12:07' ou '2026-11-24 22:00' → iso Paris."""
    if not s:
        return None
    s = str(s).strip()
    for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%d"):
        try:
            dt = datetime.strptime(s, fmt)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=PARIS)
            return dt
        except ValueError:
            pass
    # 24/11 12:07
    try:
        if " " in s:
            d, t = s.split(" ", 1)
        else:
            d, t = s, default_hm
        day, month = d.split("/")
        hour, minute = (t.split(":") + ["00"])[:2]
        dt = datetime(2026, int(month), int(day), int(hour), int(minute), tzinfo=PARIS)
        return dt
    except Exception:
        return None


def iso(dt):
    return dt.isoformat() if dt else None


def rec_base(ticker, courtier, statut="active"):
    m = dict(META.get(ticker) or {})
    return {
        "id": ticker,
        "nom": m.get("nom") or ticker,
        "ticker": ticker,
        "type": m.get("type") or "equity",
        "statut": statut,
        "tv_note": m.get("tv_note"),
        "note_tv_ok": bool(m.get("note_tv_ok")),
        "fiche_tv": m.get("fiche_tv"),
        "fiche_nom": m.get("fiche_nom"),
        "fiche_proxy": bool(m.get("fiche_proxy")),
        "fiche_note": m.get("fiche_note"),
        "tab": m.get("tab"),
        "apex_score": None,
        "apex_label": None,
        "drapeau": None,
        "drapeau_code": None,
        "courtier": courtier,
        "perf_1an_pct": None,
        "perf_1an_libelle": "à venir",
        "perf_1an_note": "Le relevé ne donne pas d'historique de la ligne ; le rendement 1 an n'est pas inventé.",
    }


def fill_money(out, valeur, investi, devise, fx, pl=None, pnl_pct=None):
    out["devise"] = devise
    out["valeur"] = r2(valeur)
    out["valeur_arrondie"] = r0(valeur)
    out["investi"] = r2(investi) if investi is not None else None
    out["investi_arrondi"] = r0(investi) if investi is not None else None
    if pl is not None:
        out["pnl_valeur"] = r2(pl)
    elif investi is not None:
        out["pnl_valeur"] = r2(valeur - investi)
        pl = out["pnl_valeur"]
    else:
        out["pnl_valeur"] = None
        pl = None
    out["pnl_pct"] = signed_pct(pl, pnl_pct, investi)
    out["perf_debut_pct"] = out["pnl_pct"]
    if devise == "EUR":
        out["valeur_eur"] = r2(valeur)
        out["investi_eur"] = r2(investi) if investi is not None else None
        out["valeur_usd"] = r2(valeur * fx)
        out["investi_usd"] = r2(investi * fx) if investi is not None else None
    else:
        out["valeur_usd"] = r2(valeur)
        out["investi_usd"] = r2(investi) if investi is not None else None
        out["valeur_eur"] = r2(valeur / fx)
        out["investi_eur"] = r2(investi / fx) if investi is not None else None


def apply_known_dates(out, ticker, qty):
    m = META.get(ticker) or {}
    keep = m.get("keep_qty")
    if keep is not None and abs(float(qty) - float(keep)) > 1e-6:
        return
    if m.get("date_achat"):
        out["date_achat"] = m["date_achat"]
    if m.get("date_ordre"):
        out["date_ordre"] = m["date_ordre"]
    if m.get("date_execution"):
        out["date_execution"] = m["date_execution"]


def from_invest_line(p, fx):
    ticker = p["ticker"]
    out = rec_base(ticker, "revolut")
    if p.get("nom") and ticker not in ("FUC", "PPX", "HMI", "URNU", "XUTL", "XHYG"):
        # garder les libellés APEX déjà soignés pour les titres déjà en base
        pass
    if ticker in ("NFLX", "DASH", "RDDT", "VACD"):
        out["nom"] = META[ticker]["nom"]
    qty = float(p["quantite"])
    cours = float(p["prix_actuel"])
    pm = float(p.get("prix_moyen") or cours)
    val = float(p["valeur_usd"] if p.get("devise_prix") == "USD" or p.get("devise") == "USD" else p.get("valeur_usd"))
    # devise de cotation
    dev = (p.get("devise_prix") or p.get("devise") or "USD").upper()
    if dev == "EUR":
        # valeur du relevé est en USD ; on conserve aussi la valeur locale
        val_loc = qty * cours
        val_usd = float(p["valeur_usd"])
        pl_usd = float(p["pl_usd"])
        investi_usd = val_usd - pl_usd
        # investi en EUR via le taux implicite, pas via qty*prix_moyen (frais possibles)
        investi_eur = investi_usd / fx
        pl_eur = val_loc - investi_eur
        out["quantite"] = qty
        out["prix_moyen"] = pm
        out["cours"] = cours
        fill_money(out, val_loc, investi_eur, "EUR", fx, pl=pl_eur, pnl_pct=p.get("pl_pct"))
        # recaler USD sur le relevé (source)
        out["valeur_usd"] = r2(val_usd)
        out["pnl_valeur"] = r2(pl_eur)
        out["investi_usd"] = r2(investi_usd)
    else:
        val_usd = float(p["valeur_usd"])
        pl_usd = float(p["pl_usd"])
        investi = val_usd - pl_usd
        out["quantite"] = qty
        out["prix_moyen"] = pm
        out["cours"] = cours
        fill_money(out, val_usd, investi, "USD", fx, pl=pl_usd, pnl_pct=p.get("pl_pct"))
    apply_known_dates(out, ticker, qty)
    return out


def from_metal(p, fx):
    ticker = p["ticker"]
    out = rec_base(ticker, "revolut")
    qty = float(p["quantite"])
    cours = float(p["prix_actuel"])
    val = float(p["valeur_usd"])
    pl = float(p["pl_usd"])
    investi = val - pl
    out["quantite"] = qty
    out["prix_moyen"] = r2(investi / qty, 4) if qty else cours
    out["cours"] = cours
    fill_money(out, val, investi, "USD", fx, pl=pl, pnl_pct=p.get("pl_pct"))
    apply_known_dates(out, ticker, qty)
    # date d'achat connue (24/11), même si le relevé ne l'affiche pas
    out["date_achat"] = "2026-11-24"
    return out


def from_order(o, fx):
    ticker = o["ticker"]
    out = rec_base(ticker, "revolut", statut="en_attente")
    qty = float(o["quantite"])
    prix = float(o["prix"])
    cout = float(o["cout_total_usd"])
    montant = float(o.get("montant_usd") or cout)
    out["quantite"] = qty
    out["prix_moyen"] = prix
    out["cours"] = prix
    fill_money(out, cout, cout, "USD", fx, pl=0, pnl_pct=0)
    dt = parse_fr_dt(o.get("date"))
    out["date_achat"] = (dt.date().isoformat() if dt else "2026-11-24")
    out["date_ordre"] = iso(dt) if dt else "2026-11-24"
    out["date_execution"] = None
    exp = parse_fr_dt(o.get("expiration"))
    out["expiration"] = iso(exp) if exp else "2026-11-24T22:00:00+01:00"
    out["sens"] = (o.get("sens") or "Buy").lower()
    out["ordre_type"] = o.get("type") or "Market"
    out["frais_estime"] = r2(cout - montant) if cout and montant else None
    out["fiche_note"] = (
        f"Ordre d'achat au marché chez Revolut, coût total prévu {r2(cout):.2f} $. "
        f"Expiration le 24/11/2026 à 22 h (Europe/Paris)."
    )
    return out


def from_mau(p, fx):
    out = rec_base("MAU", "xtb")
    qty = float(p["volume"])
    po = float(p["prix_ouverture"])
    cours = float(p["prix_actuel"])
    val = float(p["valeur"])
    pl = float(p["pl"])
    investi = val - pl  # 524.07
    out["id"] = "XTB-MAU"
    out["quantite"] = qty
    out["prix_moyen"] = po
    out["cours"] = cours
    fill_money(out, val, investi, "EUR", fx, pl=pl, pnl_pct=p.get("pl_pct"))
    # pas de date d'ouverture dans le relevé : on n'invente pas
    return out


def from_pea(pea, fx):
    val_acc = float(pea["valeur"])          # 10.40 = marché + cash
    val_mkt = float(pea["valeur_marche"])   # 9.57
    cash = float(pea.get("fonds_dispo") or 0)
    pl = float(pea["pl"])
    investi = val_acc - pl  # 20.00, même base que le 23/11
    out = rec_base("PEA", "xtb")
    out["id"] = "PEA-XTB"
    out["nom"] = "PEA XTB"
    out["ticker"] = "PEA"
    out["type"] = "cash"
    out["tab"] = None
    out["tv_note"] = None
    out["fiche_tv"] = None
    out["fiche_nom"] = None
    out["fiche_proxy"] = False
    out["note_tv_ok"] = False
    out["quantite"] = 1
    out["prix_moyen"] = r2(investi)
    out["cours"] = r2(val_acc)
    out["fiche_note"] = (
        f"PEA XTB #54086450 : valeur de marché {val_mkt:.2f} € + cash {cash:.2f} € "
        f"(enveloppe {val_acc:.2f} €). Lignes non lisibles (app mobile uniquement) : aucun titre inventé."
    )
    fill_money(out, val_acc, investi, "EUR", fx, pl=pl)
    return out


def from_cash(usd, fx):
    out = rec_base("CASH-REV", "revolut")
    out["id"] = "CASH-REV"
    out["nom"] = "Liquidités Revolut"
    out["ticker"] = "CASH"
    out["type"] = "cash"
    out["tab"] = "liquidites"
    out["tv_note"] = None
    out["fiche_tv"] = None
    out["fiche_nom"] = None
    out["fiche_proxy"] = False
    out["note_tv_ok"] = False
    out["fiche_note"] = "Liquidités du compte-titres Revolut Invest, relevé du 24/11/2026."
    out["quantite"] = 1
    out["prix_moyen"] = r2(usd)
    out["cours"] = r2(usd)
    fill_money(out, usd, usd, "USD", fx, pl=0, pnl_pct=0)
    out["pnl_pct"] = 0
    out["perf_debut_pct"] = 0
    return out


def from_eth(p, fx, old_investi=506.54):
    out = rec_base("ETH", "revolutx")
    out["id"] = "RX-ETH"
    out["source"] = "Revolut X"
    qty = float(p["quantite"])
    cours = float(p["prix_usd"])
    val = float(p["valeur_usd"])
    pl = float(p["pl_usd"])
    # coût de revient conservé (même quantité 0,28) ; contrôle : val - pl ≈ 506.54
    investi = r2(val - pl)
    out["quantite"] = qty
    out["prix_moyen"] = r2(investi / qty, 2) if qty else cours
    out["cours"] = cours
    fill_money(out, val, investi, "USD", fx, pl=pl, pnl_pct=p.get("pl_pct"))
    return out


def infer_fx(titres):
    ratios = []
    for p in titres:
        if (p.get("devise_prix") or p.get("devise")) != "EUR":
            continue
        loc = float(p["quantite"]) * float(p["prix_actuel"])
        usd = float(p["valeur_usd"])
        if loc > 0 and usd > 0:
            ratios.append(usd / loc)
    if not ratios:
        return 1.0925
    return r2(sum(ratios) / len(ratios), 6)


def cfd_stats(rows):
    pl = sum(float(x["pl_usd"]) for x in rows)
    return r2(pl), len(rows)


def totaux(rows, courtier=None):
    sel = [p for p in rows if courtier is None or p.get("courtier") == courtier]
    # ordres en cours inclus (capital déjà engagé)
    te = sum(p.get("valeur_eur") or 0 for p in sel)
    tu = sum(p.get("valeur_usd") or 0 for p in sel)
    ie = sum(p.get("investi_eur") or 0 for p in sel if p.get("investi_eur") is not None)
    iu = sum(p.get("investi_usd") or 0 for p in sel if p.get("investi_usd") is not None)
    vk = sum((p.get("valeur_eur") or 0) for p in sel if p.get("investi_eur") is not None)
    perf = r2((vk / ie - 1) * 100, 1) if ie else None
    return {
        "valeur_eur": r2(te),
        "valeur_usd": r2(tu),
        "investi_eur": r2(ie),
        "investi_usd": r2(iu),
        "perf_debut_pct": perf,
        "statut": "ok",
        "n": len(sel),
    }


def main():
    rel = json.loads(RELEVE.read_text())
    rv = rel["revolut"]["comptes"]
    titres = rv["compte_titres"]["positions"]
    ordres = rv["compte_titres"]["ordres"]
    metaux = rv["matieres_premieres"]["positions"]
    cash_usd = float(rv["compte_titres"]["liquidites_usd"])
    fx = infer_fx(titres)
    print("EURUSD implicite", fx)

    cfd_pl, cfd_n = cfd_stats(rv["cfd"]["positions"])
    cfd_val = float(rv["cfd"]["valeur_usd"])

    liv = []
    for p in titres:
        liv.append(from_invest_line(p, fx))
    for o in ordres:
        liv.append(from_order(o, fx))
    for p in metaux:
        liv.append(from_metal(p, fx))
    liv.append(from_cash(cash_usd, fx))

    xtb_eur = next(c for c in rel["xtb"]["comptes"] if c["id"] == "54086450")
    mau = xtb_eur["positions"][0]
    pea = xtb_eur["pea"]
    xtb_rows = [from_mau(mau, fx), from_pea(pea, fx)]

    eth_p = rv["revolut_x"]["positions"][0]
    rx_rows = [from_eth(eth_p, fx)]

    book_rows = liv + xtb_rows  # revolutx fusionné au chargement

    t_all = totaux(book_rows + rx_rows)
    t_rev = totaux(liv, "revolut")
    t_xtb = totaux(xtb_rows, "xtb")
    t_rx = totaux(rx_rows, "revolutx")
    t_xtb["compte"] = "54086450"
    t_xtb["devise_compte"] = "EUR"

    tot_usd = t_all["valeur_usd"]
    for p in book_rows + rx_rows:
        v = p.get("valeur_usd") or 0
        p["poids_pct"] = r2(1000 * v / tot_usd, 1) / 10 if tot_usd else None  # 1 décimale via r2? wait
        p["poids_pct"] = round(100 * v / tot_usd + 1e-9, 1) if tot_usd else None

    now = datetime(2026, 11, 24, 12, 35, tzinfo=PARIS)
    fx_obj = {
        "paire": "EURUSD",
        "taux": fx,
        "date": "2026-11-24",
        "source": (
            f"Taux implicite du relevé Revolut du 24/11/2026 vers 12 h 35 (Europe/Paris) : "
            f"EURUSD {str(fx).replace('.', ',')} d'après les lignes en euros "
            f"(FUC, PPX, HMI, URNU, VACD, XHYG, XUTL)."
        ),
        "source_court": "Relevé 24/11/2026 12:35, taux implicite",
        "zone": "Europe/Paris",
    }

    desc = (
        "Relevé du 24/11/2026 vers 12 h 35 (Europe/Paris). "
        "Les ordres d'achat en cours comptent comme des positions déjà actives "
        f"(coût total prévu). CFD exclus de Mes positions (valeur {cfd_val:,.2f} $, "
        f"P/L latent {cfd_pl:,.2f} $). "
        f"{cash_usd:,.2f} $ de liquidités sur le compte-titres Revolut."
    ).replace(",", " ").replace(".", ",") if False else (
        f"Relevé du 24/11/2026 vers 12 h 35 (Europe/Paris). "
        f"Les ordres d'achat en cours comptent comme des positions déjà actives "
        f"(coût total prévu). CFD exclus de Mes positions "
        f"(valeur {cfd_val:.2f} $, P/L latent {cfd_pl:.2f} $). "
        f"{cash_usd:.2f} $ de liquidités sur le compte-titres Revolut."
    )

    # French typography in desc
    def fr_money(n, d=2):
        s = f"{n:,.{d}f}"
        return s.replace(",", "X").replace(".", ",").replace("X", " ")

    desc = (
        f"Relevé du 24/11/2026 vers 12 h 35 (Europe/Paris). "
        f"Les ordres d'achat en cours comptent comme des positions déjà actives "
        f"(coût total prévu). CFD exclus de Mes positions "
        f"(valeur {fr_money(cfd_val)} $, P/L latent {fr_money(cfd_pl)} $). "
        f"{fr_money(cash_usd)} $ de liquidités sur le compte-titres Revolut."
    )

    pea_xtb = {
        "ouvert": True,
        "compte": "54086450",
        "devise": "EUR",
        "valeur_eur": r2(pea["valeur"]),
        "valeur_marche_eur": r2(pea["valeur_marche"]),
        "cash_eur": r2(pea["fonds_dispo"]),
        "pnl_eur": r2(pea["pl"]),
        "valeur_usd": r2(float(pea["valeur"]) * fx),
        "note": (
            f"PEA XTB #54086450 relevé le 24/11/2026 vers 12 h 31 (Europe/Paris) : "
            f"{fr_money(float(pea['valeur']))} € (valeur de marché {fr_money(float(pea['valeur_marche']))} €, "
            f"cash {fr_money(float(pea['fonds_dispo']))} €, résultat {fr_money(float(pea['pl']))} €). "
            f"Lignes visibles seulement sur mobile, non détaillées : aucun titre inventé. "
            f"Inclus dans Mes positions (ligne PEA XTB)."
        ),
    }
    xtb_id = {
        "compte": "54086450",
        "devise_compte": "EUR",
        "certitude": "élevée",
        "lignes": [
            {"nom": "Etablissements Maurel et Prom", "tv": "EURONEXT:MAU", "xtb": "MAU.FR",
             "cotation": "Euronext Paris"}
        ],
        "pea_compte": "54086450",
        "autres_comptes": [
            {"compte": "54128907", "devise": "USD", "valeur": 0.01, "note": "aucune position"},
            {"compte": "54351185", "devise": "USD", "valeur": 0.0, "note": "aucune position"},
            {"compte": "54351187", "devise": "CAD", "valeur": 0.0, "note": "aucune position (ENPH et PKX retirés)"},
        ],
        "note": (
            "Compte réel EUR #54086450 relevé le 24/11/2026 vers 12 h 31 (xStation 5) : "
            "Maurel & Prom (81 titres) et PEA. Comptes USD et CAD à 0 : ENPH et PKX ne sont plus détenus. "
            "Deutsche Bank clôturée le 16/11/2026. Aucun ordre XTB en attente."
        ),
    }

    cfd_alert = {
        "courtier": "revolut",
        "valeur_usd": r2(cfd_val),
        "pnl_usd": cfd_pl,
        "n": cfd_n,
        "libelle": f"CFD Revolut : valeur {fr_money(cfd_val, 0)} $, P/L latent ≈ {fr_money(cfd_pl, 0)} $",
        "note": "Les 22 lignes CFD restent exclues de Mes positions (règle en vigueur). Alerte compacte uniquement.",
    }

    book = {
        "releve": now.isoformat(),
        "releve_libelle": "Revolut 24/11/2026 à 12 h 35 · XTB 24/11/2026 à 12 h 31 (Europe/Paris)",
        "xtb_releve_libelle": "XTB 24/11/2026 à 12 h 31 (Europe/Paris)",
        "source": (
            "Relevés navigateur Revolut Invest / Revolut X / XTB xStation 5 du 24/11/2026 "
            "vers 12 h 35 (Europe/Paris). CFD exclus de Mes positions. "
            f"{fr_money(cash_usd)} $ de liquidités sur le compte-titres (incluses)."
        ),
        "compte": "Revolut Invest, Revolut X et XTB",
        "n_actives": sum(1 for p in book_rows if p["statut"] == "active"),
        "n_en_attente": sum(1 for p in book_rows if p["statut"] == "en_attente"),
        "positions": book_rows,
        "fx": fx_obj,
        "totaux": {
            "total_usd": t_all["valeur_usd"],
            "total_eur": t_all["valeur_eur"],
            "investi_usd": t_all["investi_usd"],
            "investi_eur": t_all["investi_eur"],
            "perf_debut_pct": t_all["perf_debut_pct"],
            "perf_1an_pct": None,
            "perf_1an_libelle": "à venir",
            "perf_1an_note": (
                "Le rendement du portefeuille sur 1 an n'est pas calculable proprement : "
                "le relevé ne donne pas la date d'achat de chaque ligne, et il n'existe pas "
                "d'historique hebdomadaire de la valeur du portefeuille. Aucune donnée n'est inventée."
            ),
            "courtiers": {
                "revolut": t_rev,
                "xtb": t_xtb,
                "revolutx": t_rx,
            },
        },
        "desc": desc,
        "pea_xtb": pea_xtb,
        "xtb_identification": xtb_id,
        "cfd_alerte": cfd_alert,
    }

    book_path = DATA / "positions.json"
    book_path.write_text(json.dumps(book, ensure_ascii=False, indent=2) + "\n")
    sha = hashlib.sha256(book_path.read_bytes()).hexdigest()

    rv_json = {
        "releve": now.isoformat(),
        "releve_libelle": "Revolut 24/11/2026 à 12 h 35 (Europe/Paris)",
        "source": (
            "Lecture navigateur Revolut Invest (compte-titres, matières premières, ordres) "
            "le 24/11/2026 vers 12 h 35. CFD exclus. "
            f"Liquidités ({fr_money(cash_usd)} $) incluses dans Mes positions (secteur Liquidités)."
        ),
        "compte": "Revolut Invest",
        "n_actives": sum(1 for p in liv if p["statut"] == "active"),
        "n_en_attente": sum(1 for p in liv if p["statut"] == "en_attente"),
        "positions": liv,
        "fx": fx_obj,
        "liquidites": {
            "usd": r2(cash_usd),
            "eur": r2(cash_usd / fx),
            "source": "Revolut Invest, cash au 24/11/2026 12:35",
            "inclus_dans_total": True,
        },
        "totaux": t_rev,
        "positions_json_sha256": sha,
        "cfd_alerte": cfd_alert,
        "desc": (
            f"Relevé Revolut Invest du 24/11/2026 à 12 h 35 (Europe/Paris). "
            f"CFD exclus. Ordres d'achat en cours inclus. "
            f"{fr_money(cash_usd)} $ de liquidités incluses."
        ),
    }
    (DATA / "positions_revolut.json").write_text(json.dumps(rv_json, ensure_ascii=False, indent=2) + "\n")

    rx_json = {
        "releve": now.isoformat(),
        "releve_libelle": "Revolut X 24/11/2026 vers 12 h 35 (Europe/Paris)",
        "source": "Lecture navigateur Revolut X le 24/11/2026 vers 12 h 35 (Europe/Paris). BTC n'est plus détenu.",
        "compte": "Revolut X",
        "n_actives": 1,
        "n_en_attente": 0,
        "positions": rx_rows,
        "fx": fx_obj,
        "totaux": t_rx,
        "desc": f"Relevé Revolut X du 24/11/2026 : ETH 0,28 ({fr_money(float(eth_p['valeur_usd']))} $).",
    }
    (DATA / "positions_revolutx.json").write_text(json.dumps(rx_json, ensure_ascii=False, indent=2) + "\n")

    print("wrote", book_path, "n", len(book_rows), "actives", book["n_actives"], "ordres", book["n_en_attente"])
    print("tickers", [p["ticker"] + ("*" if p["statut"] == "en_attente" else "") for p in book_rows])
    print("totaux USD", t_all["valeur_usd"], "EUR", t_all["valeur_eur"], "perf", t_all["perf_debut_pct"])
    print("cfd", cfd_val, cfd_pl, cfd_n)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
