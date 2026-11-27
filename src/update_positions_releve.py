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
RELEVE = DATA / "revolut" / "releve_courtiers_2026-11-25.json"
YIELDS = DATA / "rendements_positions.json"
FRAIS_CFD = DATA / "revolut" / "frais_cfd_ovn.json"
FRAIS_TRADING = DATA / "revolut" / "frais_trading_ordres.json"
ABO_TV = DATA / "abonnement_tradingview.json"
COMPTE_JOINT = DATA / "budget" / "compte_joint_2026-10.json"
LIDL_TICKETS = DATA / "budget" / "lidl_tickets_2026-10_11.json"
LECLERC_TICKETS = DATA / "budget" / "tickets_leclerc_2026-11.json"
COMPTES = DATA / "budget" / "comptes_2026-10_11.json"
BUDGET_MENSUEL = DATA / "budget" / "budget_mensuel_moyen.json"
FRAIS_OCTOBRE = DATA / "budget" / "frais_courtage_2026-10.json"
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
             "fiche_proxy": False, "note_tv_ok": True,
             "date_ordre": "2026-11-24T12:07:00+01:00", "date_achat": "2026-11-24"},
    "CAT": {"nom": "Caterpillar Inc.", "type": "equity", "tab": "actions",
            "tv_note": "NYSE:CAT", "fiche_tv": "NYSE:CAT", "fiche_nom": "Caterpillar Inc.",
            "fiche_proxy": False, "note_tv_ok": True,
            "date_ordre": "2026-11-24T11:50:00+01:00", "date_achat": "2026-11-24"},
    "AVGO": {"nom": "Broadcom Inc.", "type": "equity", "tab": "actions",
             "tv_note": "NASDAQ:AVGO", "fiche_tv": "NASDAQ:AVGO", "fiche_nom": "Broadcom Inc.",
             "fiche_proxy": False, "note_tv_ok": True,
             "date_ordre": "2026-11-24T10:22:00+01:00", "date_achat": "2026-11-24"},
    "MU": {"nom": "Micron Technology, Inc.", "type": "equity", "tab": "actions",
           "tv_note": "NASDAQ:MU", "fiche_tv": "NASDAQ:MU", "fiche_nom": "Micron Technology, Inc.",
           "fiche_proxy": False, "note_tv_ok": True, "date_achat": "2026-11-24"},
    "HWM": {"nom": "Howmet Aerospace Inc.", "type": "equity", "tab": "actions",
            "tv_note": "NYSE:HWM", "fiche_tv": "NYSE:HWM", "fiche_nom": "Howmet Aerospace Inc.",
            "fiche_proxy": False, "note_tv_ok": True, "date_achat": "2026-11-24"},
    "GOOGL": {"nom": "Alphabet Inc.", "type": "equity", "tab": "actions",
              "tv_note": "NASDAQ:GOOGL", "fiche_tv": "NASDAQ:GOOGL", "fiche_nom": "Alphabet Inc.",
              "fiche_proxy": False, "note_tv_ok": True, "date_achat": "2026-11-24"},
    "ENPH": {"nom": "Enphase Energy", "type": "equity", "tab": "energie",
             "tv_note": "NASDAQ:ENPH", "fiche_tv": "NASDAQ:ENPH", "fiche_nom": "Enphase Energy",
             "fiche_proxy": False, "note_tv_ok": True, "date_achat": "2026-11-24"},
    "LRCX": {"nom": "Lam Research Corporation", "type": "equity", "tab": "actions",
             "tv_note": "NASDAQ:LRCX", "fiche_tv": "NASDAQ:LRCX", "fiche_nom": "Lam Research Corporation",
             "fiche_proxy": False, "note_tv_ok": True, "date_achat": "2026-11-24"},
    "MC": {"nom": "LVMH", "type": "equity", "tab": "actions",
           "tv_note": "EURONEXT:MC", "fiche_tv": "EURONEXT:MC",
           "fiche_nom": "LVMH Moët Hennessy Louis Vuitton SE",
           "fiche_proxy": False, "note_tv_ok": True,
           "fiche_note": "Ouverte entre le relevé du 24/11/2026 20 h 31 et le pointage du 25/11/2026 vers 08 h 15. 2,50761088 titres, 1 000 € investis, P/L −0,16 %, prix indiqué 396,80 €."},
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
    "BTC": {"nom": "Bitcoin", "type": "crypto", "tab": "crypto",
            "tv_note": "BTC", "fiche_tv": "BTC", "fiche_nom": "Bitcoin",
            "fiche_proxy": False, "note_tv_ok": True,
            "fiche_note": "Position Revolut X ouverte (ou réouverte) au 25/11/2026 vers 09 h 50 : 0,018 BTC."},
    "CFD-XPD": {"nom": "Palladium CFD", "type": "cfd", "tab": "metaux",
                "tv_note": "OANDA:XPDUSD", "fiche_tv": "OANDA:XPDUSD",
                "fiche_nom": "Palladium au comptant (sous-jacent du CFD Revolut)",
                "fiche_proxy": False, "note_tv_ok": True},
    "CFD-COST": {"nom": "Costco CFD", "type": "cfd", "tab": "actions",
                 "tv_note": "NASDAQ:COST", "fiche_tv": "NASDAQ:COST",
                 "fiche_nom": "Costco Wholesale Corporation",
                 "fiche_proxy": False, "note_tv_ok": True},
    "CFD-MSTR": {"nom": "MicroStrategy CFD", "type": "cfd", "tab": "actions",
                 "tv_note": "NASDAQ:MSTR", "fiche_tv": "NASDAQ:MSTR",
                 "fiche_nom": "Strategy (ex-MicroStrategy)",
                 "fiche_proxy": False, "note_tv_ok": True},
    "CFD-SMR": {"nom": "NuScale Power CFD", "type": "cfd", "tab": "energie",
                "tv_note": "NYSE:SMR", "fiche_tv": "NYSE:SMR",
                "fiche_nom": "NuScale Power Corporation (nucléaire)",
                "fiche_proxy": False, "note_tv_ok": True},
    "CFD-MPC": {"nom": "Marathon Petroleum CFD", "type": "cfd", "tab": "energie",
                "tv_note": "NYSE:MPC", "fiche_tv": "NYSE:MPC",
                "fiche_nom": "Marathon Petroleum Corporation",
                "fiche_proxy": False, "note_tv_ok": True},
    "CFD-AMD": {"nom": "AMD CFD", "type": "cfd", "tab": "actions",
                "tv_note": "NASDAQ:AMD", "fiche_tv": "NASDAQ:AMD",
                "fiche_nom": "Advanced Micro Devices, Inc.",
                "fiche_proxy": False, "note_tv_ok": True},
    "CFD-BDX": {"nom": "Becton Dickinson CFD", "type": "cfd", "tab": "actions",
                "tv_note": "NYSE:BDX", "fiche_tv": "NYSE:BDX",
                "fiche_nom": "Becton, Dickinson and Company",
                "fiche_proxy": False, "note_tv_ok": True},
    "CFD-EG": {"nom": "Everest Group CFD", "type": "cfd", "tab": "actions",
               "tv_note": "NYSE:EG", "fiche_tv": "NYSE:EG",
               "fiche_nom": "Everest Group, Ltd.",
               "fiche_proxy": False, "note_tv_ok": True},
    "CFD-ABBV": {"nom": "AbbVie CFD", "type": "cfd", "tab": "actions",
                 "tv_note": "NYSE:ABBV", "fiche_tv": "NYSE:ABBV",
                 "fiche_nom": "AbbVie Inc.",
                 "fiche_proxy": False, "note_tv_ok": True},
    "CFD-SPCX": {"nom": "SpaceX CFD", "type": "cfd", "tab": "actions",
                 "tv_note": "NASDAQ:SPCX", "fiche_tv": "NASDAQ:SPCX",
                 "fiche_nom": "Space Exploration Technologies Corp",
                 "fiche_proxy": False, "note_tv_ok": True},
    "CFD-TGT": {"nom": "Target CFD", "type": "cfd", "tab": "actions",
                "tv_note": "NYSE:TGT", "fiche_tv": "NYSE:TGT",
                "fiche_nom": "Target Corporation",
                "fiche_proxy": False, "note_tv_ok": True,
                "date_achat": "2026-11-27",
                "date_execution": "2026-11-27T07:22:00+01:00"},
    "CFD-MCK": {"nom": "McKesson CFD", "type": "cfd", "tab": "actions",
                "tv_note": "NYSE:MCK", "fiche_tv": "NYSE:MCK",
                "fiche_nom": "McKesson Corporation",
                "fiche_proxy": False, "note_tv_ok": True,
                "date_achat": "2026-11-27",
                "date_execution": "2026-11-27T07:07:00+01:00"},
    "CFD-DLTR": {"nom": "Dollar Tree CFD", "type": "cfd", "tab": "actions",
                 "tv_note": "NASDAQ:DLTR", "fiche_tv": "NASDAQ:DLTR",
                 "fiche_nom": "Dollar Tree, Inc.",
                 "fiche_proxy": False, "note_tv_ok": True,
                 "date_achat": "2026-11-27",
                 "date_execution": "2026-11-27T07:25:00+01:00"},
    "CFD-ED": {"nom": "Consolidated Edison CFD", "type": "cfd", "tab": "actions",
               "tv_note": "NYSE:ED", "fiche_tv": "NYSE:ED",
               "fiche_nom": "Consolidated Edison, Inc.",
               "fiche_proxy": False, "note_tv_ok": True,
               "date_achat": "2026-11-27",
               "date_execution": "2026-11-27T15:31:00+01:00"},
    "CFD-WAT": {"nom": "Waters CFD", "type": "cfd", "tab": "actions",
                "tv_note": "NYSE:WAT", "fiche_tv": "NYSE:WAT",
                "fiche_nom": "Waters Corporation",
                "fiche_proxy": False, "note_tv_ok": True,
                "date_achat": "2026-11-27",
                "date_execution": "2026-11-27T17:05:00+01:00"},
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
    if ticker in ("NFLX", "DASH", "RDDT", "VACD", "MC"):
        out["nom"] = META[ticker]["nom"]
    qty = float(p["quantite"])
    cours = float(p["prix_actuel"])
    pm = float(p.get("prix_moyen") or cours)
    val = float(p["valeur_usd"] if p.get("devise_prix") == "USD" or p.get("devise") == "USD" else p.get("valeur_usd"))
    # devise de cotation
    dev = (p.get("devise_prix") or p.get("devise") or "USD").upper()
    if dev == "EUR":
        # Valeur et P/L % officiels de la ligne (pointage 08 h 15) : on ne les
        # fait pas dériver en changeant le taux EURUSD. Les USD sont convertis
        # au taux officiel du 25/11 (1,0944).
        val_loc = float(p["valeur_eur"]) if p.get("valeur_eur") is not None else qty * cours
        official_pct = p.get("pl_pct")
        if official_pct is not None and float(official_pct) != -100:
            investi_eur = val_loc / (1 + float(official_pct) / 100.0)
            pl_eur = val_loc - investi_eur
        else:
            val_usd = float(p["valeur_usd"])
            pl_usd = float(p["pl_usd"])
            investi_eur = (val_usd - pl_usd) / fx
            pl_eur = val_loc - investi_eur
        out["quantite"] = qty
        out["prix_moyen"] = pm
        out["cours"] = cours
        fill_money(out, val_loc, investi_eur, "EUR", fx, pl=pl_eur, pnl_pct=official_pct)
        if official_pct is not None:
            out["pnl_pct"] = r2(official_pct)
            out["perf_debut_pct"] = out["pnl_pct"]
        out["valeur_usd"] = r2(val_loc * fx)
        out["investi_usd"] = r2(investi_eur * fx) if investi_eur is not None else None
        out["pnl_valeur"] = r2(pl_eur)
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
    val_acc = float(pea["valeur"])
    pl = float(pea["pl"])
    investi = val_acc - pl  # 20.00 €, même base que les relevés précédents
    out = rec_base("PEA", "xtb")
    out["id"] = "PEA-XTB"
    out["nom"] = "ligne PEA non identifiée"
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
    inst = pea.get("instrument_pl_pct")
    bits = [
        f"PEA XTB #54086450 : enveloppe {val_acc:.2f} €, résultat {pl:.2f} €, au 25/11/2026 vers 09 h 50 (Europe/Paris).",
        "Ligne unique à −51,1 %, logo bleu foncé avec un A, nom non lisible : « ligne PEA non identifiée ».",
    ]
    if pea.get("valeur_marche") is not None and pea.get("fonds_dispo") is not None:
        bits.append(
            f"Valeur de marché {float(pea['valeur_marche']):.2f} € + cash {float(pea['fonds_dispo']):.2f} €."
        )
    else:
        bits.append("Valeur de marché et cash du PEA non séparés sur la capture : non inventés.")
    if inst is not None:
        out["instrument_pl_pct"] = float(inst)
    out["fiche_note"] = " ".join(bits)
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
    out["fiche_note"] = ("Liquidités du compte-titres Revolut Invest, 5,50 $, non relues le 25/11/2026 à 09 h 50 ""(conservées du relevé du 24/11/2026 à 20 h 31, déjà incluses dans le total officiel du compte de courtage).")
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


def from_btc(p, fx):
    out = rec_base("BTC", "revolutx")
    out["id"] = "RX-BTC"
    out["source"] = "Revolut X"
    qty = float(p["quantite"])
    cours = float(p["prix_usd"]) if p.get("prix_usd") is not None else None
    val = float(p["valeur_usd"])
    pl = p.get("pl_usd")
    if pl is None and p.get("pl_pct") is not None:
        # investi implicite à partir du % officiel, sans inventer un autre PRU
        pl = r2(val - val / (1 + float(p["pl_pct"]) / 100.0)) if float(p["pl_pct"]) != -100 else None
    pl = float(pl) if pl is not None else None
    investi = r2(val - pl) if pl is not None else None
    out["quantite"] = qty
    out["prix_moyen"] = r2(investi / qty, 2) if (investi and qty) else None
    out["cours"] = cours
    out["prix_affiche_usd"] = cours
    if p.get("note"):
        out["fiche_note"] = (out.get("fiche_note") or "") + (" " if out.get("fiche_note") else "") + p["note"]
    fill_money(out, val, investi, "USD", fx, pl=pl, pnl_pct=p.get("pl_pct"))
    return out


def from_xtb_cash(eur, fx):
    out = rec_base("CASH-XTB", "xtb")
    out["id"] = "CASH-XTB"
    out["nom"] = "Liquidités XTB"
    out["ticker"] = "CASH-XTB"
    out["type"] = "cash"
    out["tab"] = "liquidites"
    out["tv_note"] = None
    out["fiche_tv"] = None
    out["fiche_nom"] = None
    out["fiche_proxy"] = False
    out["note_tv_ok"] = False
    out["fiche_note"] = (
        "Fonds disponibles du compte XTB EUR #54086450, 5,93 €, relevés le 25/11/2026 vers 09 h 50 "
        "(inclus dans Mes transactions 525,14 € et dans le total 535,35 €)."
    )
    out["quantite"] = 1
    out["prix_moyen"] = r2(eur)
    out["cours"] = r2(eur)
    fill_money(out, eur, eur, "EUR", fx, pl=0, pnl_pct=0)
    out["pnl_pct"] = 0
    out["perf_debut_pct"] = 0
    return out


def from_cfd(p, fx):
    """Ligne CFD : montant = exposition (quantité × cours actuel), pas la marge.
    P/L % long = P/L / (exposition − P/L) ; short = P/L / coût d'entrée.
    """
    ticker = p["ticker"]
    key = f"CFD-{ticker}"
    out = rec_base(key, "revolut")
    sens_raw = (p.get("sens") or "Buy").strip()
    long_ = sens_raw.lower() in ("buy", "long", "l")
    levier = p.get("levier")
    levier = int(levier) if levier not in (None, "") else None
    out["id"] = key
    out["ticker"] = f"{ticker}-CFD"
    out["sous_jacent"] = ticker
    out["type"] = "cfd"
    out["sens"] = "long" if long_ else "short"
    out["levier"] = levier
    out["cfd_badge"] = (
        f"CFD {'L' if long_ else 'S'} x{levier}" if levier else f"CFD {'L' if long_ else 'S'}"
    )
    if p.get("marge_usd") not in (None, ""):
        out["marge_usd"] = r2(p["marge_usd"])
    out["prix_moyen"] = p.get("prix_ouverture")
    out["cours"] = p.get("prix_actuel")
    out["valeur_affichee_usd"] = p.get("valeur_affichee_usd")
    qty = p.get("quantite")
    out["quantite"] = float(qty) if qty not in (None, "") else None
    out["statut"] = "active"
    out["a_confirmer"] = bool(p.get("a_confirmer"))
    if p.get("note"):
        out["fiche_note"] = ((out.get("fiche_note") or "") + " " + p["note"]).strip()

    expo = None
    if out["quantite"] and out["cours"] not in (None, ""):
        expo = r2(float(out["quantite"]) * float(out["cours"]))
        out["exposition_usd"] = expo

    pl = p.get("pl_usd")
    if expo is not None and pl not in (None, ""):
        pl = float(pl)
        if long_:
            entry = expo - pl  # P/L % = P/L / (exposition − P/L)
        else:
            if out["prix_moyen"] not in (None, "") and out["quantite"]:
                entry = float(out["quantite"]) * float(out["prix_moyen"])
            else:
                entry = expo + pl  # P/L short = entrée − exposition
        pnl_pct = (100.0 * pl / entry) if entry else None
        fill_money(out, expo, entry, "USD", fx, pl=pl, pnl_pct=pnl_pct)
        if pnl_pct is not None:
            out["pnl_pct"] = r2(pnl_pct)
            out["perf_debut_pct"] = out["pnl_pct"]
        out["pnl_relu"] = True
        if out["prix_moyen"] is None and entry and out["quantite"]:
            out["prix_moyen"] = r2(entry / out["quantite"], 4)
    else:
        out["pnl_relu"] = False
        out["exposition_usd"] = expo
        out["perf_1an_libelle"] = "à confirmer" if out["a_confirmer"] else "P/L non relu"
        out["perf_1an_note"] = (
            "Cours actuel et/ou P&L non lus à 10 h 14 : le montant d'exposition et le P/L "
            "de cette ligne ne sont pas inventés. Ligne à confirmer (non visible sur la capture, "
            "présente dans le relevé du matin)."
        )
        # Pas de montant inventé : la ligne n'entre pas dans les totaux d'exposition.
        out["devise"] = "USD"
        out["valeur"] = None
        out["valeur_usd"] = None
        out["valeur_eur"] = None
        out["investi"] = None
        out["investi_usd"] = None
        out["investi_eur"] = None
        out["pnl_valeur"] = None
        out["pnl_pct"] = None
        out["perf_debut_pct"] = None
    apply_known_dates(out, key, out.get("quantite") or 0)
    if p.get("date_achat"):
        out["date_achat"] = p["date_achat"]
    if p.get("date_execution"):
        out["date_execution"] = p["date_execution"]
    fee = p.get("frais_ouverture_usd")
    if fee is None:
        fee = (META.get(key) or {}).get("frais_ouverture_usd")
    if fee not in (None, ""):
        out["frais_ouverture_usd"] = r2(fee)
    if p.get("prix_estime"):
        out["prix_estime"] = True
    return out


def from_tesla(plan, fx):
    """Ligne Tesla RSU / plan d'actions : avantage potentiel, non liquide, P/L non inventé."""
    out = rec_base("TSLA-RSU", "tesla")
    out["id"] = "TSLA-RSU"
    out["ticker"] = "TSLA-RSU"
    out["nom"] = plan.get("nom") or "Tesla RSU"
    out["type"] = "rsu"
    out["tab"] = None
    out["exclus_secteur"] = True
    out["non_liquide"] = True
    out["statut"] = "active"
    out["fiche_tv"] = "NASDAQ:TSLA"
    out["tv_note"] = "NASDAQ:TSLA"
    out["fiche_nom"] = "Plan d'actions Tesla (RSU)"
    out["note_tv_ok"] = True
    out["rsu_badge"] = "RSU"
    eur = float(plan.get("avantage_potentiel_eur") or 0)
    fill_money(out, eur, None, "EUR", fx, pl=None, pnl_pct=None)
    out["investi"] = None
    out["investi_usd"] = None
    out["investi_eur"] = None
    out["investi_arrondi"] = None
    out["pnl_valeur"] = None
    out["pnl_pct"] = None
    out["perf_debut_pct"] = None
    out["perf_1an_libelle"] = "non liquide"
    out["perf_1an_note"] = (
        "Avantage potentiel du plan d'actions Tesla, relevé le 25/11/2026 à 03 h 51 EDT "
        "(09 h 51 Europe/Paris). Valeur actuelle du compte 0 €. Aucun prix de revient ni P/L "
        "n'est inventé. Inclus dans le total de Mes positions, exclu du tableau sectoriel."
    )
    usd = out["valeur_usd"]
    def fr(n):
        return f"{n:,.2f}".replace(",", "X").replace(".", ",").replace("X", " ")
    bits = [
        f"Tesla RSU / plan d'actions : {fr(eur)} € ({fr(usd)} $ au taux {str(fx).replace('.', ',')}). Non liquide.",
        plan.get("note") or "",
    ]
    out["fiche_note"] = " ".join(b for b in bits if b).strip()
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
    pls = [x.get("pl_usd") for x in (rows or [])]
    if any(v is None or v == "" for v in pls) or not rows:
        return None, len(rows or [])
    return r2(sum(float(v) for v in pls)), len(rows)

def apply_yields(rows):
    """Attache le rendement de dividende/coupon sourcé, sans l'inventer."""
    if not YIELDS.exists():
        return
    data = json.loads(YIELDS.read_text())
    table = data.get("lignes") or {}
    for p in rows:
        rec = table.get(p.get("ticker")) or table.get(p.get("id"))
        if not rec or rec.get("rendement_pct") is None:
            continue
        p["rendement_pct"] = rec["rendement_pct"]
        p["rendement_type"] = rec.get("type")
        p["rendement_source"] = rec.get("source")
        p["rendement_date"] = rec.get("date") or data.get("date")
        if rec.get("forward_pct") is not None:
            p["rendement_forward_pct"] = rec["forward_pct"]
        if rec.get("note"):
            p["rendement_note"] = rec["note"]


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



def _mirror_site_root(data_file: Path):
    """Copie vers la racine du dépôt (fetch de index.html : positions.json, etc.)."""
    if data_file.parent.name != "data":
        return
    dest = data_file.parent.parent / data_file.name
    dest.write_bytes(data_file.read_bytes())
    print("mirrored", dest)

def build_frais_cfd(fx):
    """Lit data/revolut/frais_cfd_ovn.json et calcule la projection mensuelle (sans inventer de jour)."""
    raw = json.loads(FRAIS_CFD.read_text()) if FRAIS_CFD.exists() else {}
    jours = list(raw.get("jours") or [])
    obj_eur = raw.get("objectif_eur_mois") if raw.get("objectif_eur_mois") is not None else 20
    last = jours[-1] if jours else None
    last_usd = abs(float(last["montant_usd"])) if last and last.get("montant_usd") is not None else None
    jours_n = int((raw.get("projection") or {}).get("jours_calendaires") or 30)
    proj_usd = r2(last_usd * jours_n) if last_usd is not None else None
    proj_eur = r2(proj_usd / fx) if proj_usd is not None else None
    last_eur = r2(last_usd / fx) if last_usd is not None else None
    out = dict(raw)
    out.update({
        "dernier": last,
        "dernier_usd": last_usd,
        "dernier_eur": last_eur,
        "projection_jours": jours_n,
        "projection_usd": proj_usd,
        "projection_eur": proj_eur,
        "objectif_eur_mois": obj_eur,
        "ratio_objectif": r2(proj_eur / obj_eur, 2) if (proj_eur and obj_eur) else None,
        "depasse_objectif": bool(proj_eur is not None and proj_eur > obj_eur),
    })
    return out


MOIS_FR = {
    1: "janvier", 2: "février", 3: "mars", 4: "avril", 5: "mai", 6: "juin",
    7: "juillet", 8: "août", 9: "septembre", 10: "octobre", 11: "novembre", 12: "décembre",
}


def _in_month(date_str, ym):
    return str(date_str or "").startswith(ym)


def _fee_usd(row, fx):
    if row.get("montant_usd") not in (None, ""):
        return r2(abs(float(row["montant_usd"])))
    if row.get("montant") in (None, ""):
        return None
    d = str(row.get("devise") or "USD").upper()
    m = abs(float(row["montant"]))
    if d == "USD":
        return r2(m)
    if d == "EUR" and fx:
        return r2(m * fx)
    return None



def build_abonnement_tv(fx):
    """Abonnement TradingView sourcé (data/abonnement_tradingview.json). Pas de montant inventé."""
    if not ABO_TV.exists():
        return None
    raw = json.loads(ABO_TV.read_text(encoding="utf-8"))
    eur_mois = raw.get("montant_eur_mois")
    eur_an = raw.get("montant_eur_an")
    out = dict(raw)
    out["projection_eur"] = r2(eur_mois) if eur_mois not in (None, "") else None
    out["projection_usd"] = r2(float(eur_mois) * fx) if (eur_mois not in (None, "") and fx) else None
    out["montant_usd_an"] = r2(float(eur_an) * fx) if (eur_an not in (None, "") and fx) else None
    # Le prélèvement Essential (186,48 €) est au 6/12/2026 : rien d'observé en novembre.
    out["total_mois_usd"] = None
    out["total_mois_eur"] = None
    obj = dict(out.get("objectif") or {})
    if obj.get("economie_eur_mois") not in (None, "") and fx:
        obj["economie_usd_mois"] = r2(float(obj["economie_eur_mois"]) * fx)
    if obj.get("economie_eur_an") not in (None, "") and fx:
        obj["economie_usd_an"] = r2(float(obj["economie_eur_an"]) * fx)
    out["objectif"] = obj
    return out



def _cj_usd(eur, fx):
    if eur in (None, ""):
        return None
    return r2(float(eur) * fx) if fx else None


def _cj_ops(ops, fx):
    out = []
    for o in ops or []:
        rec = dict(o)
        rec["montant_usd"] = _cj_usd(rec.get("montant_eur"), fx)
        out.append(rec)
    return out




def _attach_lidl_tickets(sous, fx):
    """Injecte Lidl + Leclerc dans le bloc tickets de caisse, sans toucher aux autres champs Courses."""
    sous = [dict(s) for s in (sous or [])]
    bundle = _build_tickets_caisse(fx)
    if not bundle:
        return sous
    found = False
    for i, s in enumerate(sous):
        if s.get("id") in ("tickets_lidl", "tickets_caisse"):
            rec = dict(s)
            rec.update(bundle)
            rec["id"] = "tickets_caisse"
            rec["statut"] = "complet"
            sous[i] = rec
            found = True
            break
    if not found:
        sous.append(bundle)
    return sous


_TICKETS_CATS = [
    "Frais (fruits, légumes)", "Crèmerie & fromages", "Viande & poisson", "Boulangerie",
    "Épicerie salée", "Épicerie sucrée & snacks", "Plats préparés & pizzas",
    "Boissons sans alcool", "Alcool", "Entretien maison", "Hygiène & beauté",
    "Animaux (litière)", "Textile & vêtements", "Maison & déco (dont Noël)",
    "Cuisine & bricolage (non alimentaire)", "Sacs", "Non classé",
]
_TICKETS_ALIM = {
    "Frais (fruits, légumes)", "Crèmerie & fromages", "Viande & poisson", "Boulangerie",
    "Épicerie salée", "Épicerie sucrée & snacks", "Plats préparés & pizzas",
    "Boissons sans alcool", "Alcool",
}


def _cj_usd_safe(eur, fx):
    if eur is None or fx in (None, 0):
        return None
    try:
        return r2(float(eur) * float(fx))
    except (TypeError, ValueError):
        return None


def _tickets_empty_month(ym, libelle, fx):
    sous = []
    for c in _TICKETS_CATS:
        sous.append({
            "id": c, "libelle": c, "eur": 0.0, "usd": 0.0, "pct": 0.0,
            "alimentaire": c in _TICKETS_ALIM, "non_classe": c == "Non classé",
        })
    return {
        "mois": ym, "libelle": libelle, "n_tickets": 0,
        "total_eur": 0.0, "total_usd": 0.0,
        "alimentaire_eur": 0.0, "alimentaire_usd": 0.0, "alimentaire_pct": 0.0,
        "non_alimentaire_eur": 0.0, "non_alimentaire_usd": 0.0, "non_alimentaire_pct": 0.0,
        "non_classe_eur": 0.0, "non_classe_usd": 0.0,
        "deco_noel_eur": 0.0, "deco_noel_usd": 0.0, "deco_noel_pct": 0.0,
        "remises_eur": 0.0, "remises_eur_abs": 0.0, "remises_usd_abs": 0.0,
        "tr_eur": 0.0, "tr_usd": 0.0, "tr_pct": 0.0, "tr_a_confirmer_eur": 0.0,
        "cb_eur": 0.0, "cb_usd": 0.0,
        "panier_moyen_eur": 0.0, "panier_moyen_usd": 0.0,
        "par_sous_categorie": sous, "tickets": [],
    }


def _tickets_norm_month(m, fx):
    """Normalise un mois (ajoute Non classé / déco / TR à confirmer si absents)."""
    if not m:
        return None
    out = dict(m)
    by = {s.get("libelle") or s.get("id"): dict(s) for s in (m.get("par_sous_categorie") or [])}
    sous = []
    for c in _TICKETS_CATS:
        s = by.get(c) or {"id": c, "libelle": c, "eur": 0.0, "usd": 0.0, "pct": 0.0}
        s["id"] = c
        s["libelle"] = c
        s["eur"] = r2(s.get("eur") or 0)
        s["usd"] = s["usd"] if s.get("usd") is not None else _cj_usd_safe(s["eur"], fx)
        s["alimentaire"] = c in _TICKETS_ALIM
        s["non_classe"] = c == "Non classé"
        sous.append(s)
    tot = r2(out.get("total_eur") or 0)
    for s in sous:
        s["pct"] = r2(100.0 * (s["eur"] or 0) / tot) if tot else 0.0
    out["par_sous_categorie"] = sous
    if out.get("non_classe_eur") is None:
        out["non_classe_eur"] = next((s["eur"] for s in sous if s["non_classe"]), 0.0)
        out["non_classe_usd"] = _cj_usd_safe(out["non_classe_eur"], fx)
    deco = next((s["eur"] for s in sous if s["id"] == "Maison & déco (dont Noël)"), 0.0)
    out["deco_noel_eur"] = r2(out.get("deco_noel_eur") if out.get("deco_noel_eur") is not None else deco)
    out["deco_noel_usd"] = out.get("deco_noel_usd") if out.get("deco_noel_usd") is not None else _cj_usd_safe(out["deco_noel_eur"], fx)
    out["deco_noel_pct"] = r2(100.0 * (out["deco_noel_eur"] or 0) / tot) if tot else 0.0
    out["tr_a_confirmer_eur"] = r2(out.get("tr_a_confirmer_eur") or 0)
    out["tickets"] = list(out.get("tickets") or [])
    return out


def _tickets_add_month(a, b, libelle, fx):
    a = a or _tickets_empty_month((b or {}).get("mois") or "2026-11", libelle, fx)
    b = b or _tickets_empty_month((a or {}).get("mois") or "2026-11", libelle, fx)
    tot = r2((a.get("total_eur") or 0) + (b.get("total_eur") or 0))
    n = (a.get("n_tickets") or 0) + (b.get("n_tickets") or 0)
    by = {}
    for src in (a, b):
        for s in src.get("par_sous_categorie") or []:
            k = s.get("libelle") or s.get("id")
            rec = by.setdefault(k, {"id": k, "libelle": k, "eur": 0.0})
            rec["eur"] = r2((rec["eur"] or 0) + (s.get("eur") or 0))
    sous = []
    for c in _TICKETS_CATS:
        e = (by.get(c) or {}).get("eur") or 0.0
        sous.append({
            "id": c, "libelle": c, "eur": e, "usd": _cj_usd_safe(e, fx),
            "pct": r2(100.0 * e / tot) if tot else 0.0,
            "alimentaire": c in _TICKETS_ALIM, "non_classe": c == "Non classé",
        })
    alim = r2(sum(s["eur"] for s in sous if s["alimentaire"]))
    non = r2(sum(s["eur"] for s in sous if not s["alimentaire"] and not s["non_classe"]))
    nc = r2(sum(s["eur"] for s in sous if s["non_classe"]))
    deco = r2(next((s["eur"] for s in sous if s["id"] == "Maison & déco (dont Noël)"), 0.0))
    rem_abs = r2((a.get("remises_eur_abs") or 0) + (b.get("remises_eur_abs") or 0))
    rem = r2((a.get("remises_eur") or 0) + (b.get("remises_eur") or 0))
    tr = r2((a.get("tr_eur") or 0) + (b.get("tr_eur") or 0))
    tr_conf = r2((a.get("tr_a_confirmer_eur") or 0) + (b.get("tr_a_confirmer_eur") or 0))
    cb = r2((a.get("cb_eur") or 0) + (b.get("cb_eur") or 0))
    panier = r2(tot / n) if n else 0.0
    tickets = list(a.get("tickets") or []) + list(b.get("tickets") or [])
    return {
        "mois": a.get("mois") or b.get("mois"),
        "libelle": libelle or a.get("libelle") or b.get("libelle"),
        "n_tickets": n, "total_eur": tot, "total_usd": _cj_usd_safe(tot, fx),
        "alimentaire_eur": alim, "alimentaire_usd": _cj_usd_safe(alim, fx),
        "alimentaire_pct": r2(100.0 * alim / tot) if tot else 0.0,
        "non_alimentaire_eur": non, "non_alimentaire_usd": _cj_usd_safe(non, fx),
        "non_alimentaire_pct": r2(100.0 * non / tot) if tot else 0.0,
        "non_classe_eur": nc, "non_classe_usd": _cj_usd_safe(nc, fx),
        "deco_noel_eur": deco, "deco_noel_usd": _cj_usd_safe(deco, fx),
        "deco_noel_pct": r2(100.0 * deco / tot) if tot else 0.0,
        "remises_eur": rem, "remises_eur_abs": rem_abs, "remises_usd_abs": _cj_usd_safe(rem_abs, fx),
        "tr_eur": tr, "tr_usd": _cj_usd_safe(tr, fx),
        "tr_pct": r2(100.0 * tr / tot) if tot else 0.0,
        "tr_a_confirmer_eur": tr_conf,
        "cb_eur": cb, "cb_usd": _cj_usd_safe(cb, fx),
        "panier_moyen_eur": panier, "panier_moyen_usd": _cj_usd_safe(panier, fx),
        "par_sous_categorie": sous, "tickets": tickets,
    }


def _build_tickets_caisse(fx):
    lidl = json.loads(LIDL_TICKETS.read_text(encoding="utf-8")) if LIDL_TICKETS.exists() else None
    lec = json.loads(LECLERC_TICKETS.read_text(encoding="utf-8")) if LECLERC_TICKETS.exists() else None
    if not lidl and not lec:
        return None
    lidl_mois = {k: _tickets_norm_month(v, fx) for k, v in ((lidl or {}).get("mois") or {}).items()}
    lec_mois = {k: _tickets_norm_month(v, fx) for k, v in ((lec or {}).get("mois") or {}).items()}
    # tag enseigne on tickets if missing
    for m in lidl_mois.values():
        for t in m.get("tickets") or []:
            t.setdefault("enseigne", "lidl")
            t.setdefault("enseigne_libelle", "Lidl")
    for m in lec_mois.values():
        for t in m.get("tickets") or []:
            t.setdefault("enseigne", "leclerc")
            t.setdefault("enseigne_libelle", "E.Leclerc")
    tous_mois = {}
    for ym in sorted(set(lidl_mois) | set(lec_mois)):
        lib = (lidl_mois.get(ym) or lec_mois.get(ym) or {}).get("libelle") or ym
        tous_mois[ym] = _tickets_add_month(lidl_mois.get(ym), lec_mois.get(ym), lib, fx)
    # empty oct for leclerc display
    if "2026-10" not in lec_mois:
        lec_mois["2026-10"] = _tickets_empty_month("2026-10", "Octobre 2026 (aucun ticket E.Leclerc)", fx)
    if "2026-11" not in lidl_mois and "2026-11" in tous_mois:
        pass
    part = (lidl or {}).get("courses_releve_octobre") or {}
    note = part.get("note") or "Les Courses du relevé incluent aussi d’autres enseignes."
    return {
        "id": "tickets_caisse",
        "libelle": "Tickets de caisse — détail par rayons",
        "statut": "complet",
        "objectif": None,
        "source": {
            "intitule": "Tickets Lidl Plus, octobre 2026.",
            "fx": 1.0944,
        },
        "courses_releve_octobre": part,
        "note": note,
        "enseigne_defaut": "tous",
        "enseignes": {
            "tous": {"id": "tous", "libelle": "Tous", "mois": tous_mois},
            "lidl": {"id": "lidl", "libelle": "Lidl", "mois": lidl_mois},
            "leclerc": {"id": "leclerc", "libelle": "E.Leclerc", "mois": lec_mois},
        },
        "mois": tous_mois,
    }




def build_compte_joint(fx):
    """Compte joint famille octobre 2026, sourcé (data/budget/compte_joint_2026-10.json)."""
    if not COMPTE_JOINT.exists():
        return None
    raw = json.loads(COMPTE_JOINT.read_text(encoding="utf-8"))
    cats = []
    for c in raw.get("categories") or []:
        rec = {k: v for k, v in c.items() if k not in ("operations", "sous_categories", "commercants")}
        rec["observe_usd"] = _cj_usd(rec.get("observe_eur"), fx)
        rec["projection_eur"] = rec.get("observe_eur")
        rec["projection_usd"] = rec["observe_usd"]
        rec["operations"] = _cj_ops(c.get("operations"), fx)
        if c.get("id") == "courses":
            rec["commercants"] = []
            for m in c.get("commercants") or []:
                mm = dict(m)
                mm["total_usd"] = _cj_usd(mm.get("total_eur"), fx)
                rec["commercants"].append(mm)
            rec["sous_categories"] = _tickets_octobre_only(_attach_lidl_tickets(c.get("sous_categories") or [], fx))
        cats.append(rec)
    tot = dict(raw.get("totaux") or {})
    for k in list(tot):
        if k.endswith("_eur"):
            tot[k[:-4] + "_usd"] = _cj_usd(tot.get(k), fx)
    soldes = dict(raw.get("soldes") or {})
    for k in list(soldes):
        if k.endswith("_eur") and isinstance(soldes.get(k), (int, float)):
            soldes[k[:-4] + "_usd"] = _cj_usd(soldes.get(k), fx)
    hors = raw.get("operations_hors_octobre") or {}
    att = raw.get("en_attente") or {}
    ren = raw.get("renvoyes") or {}
    return {
        "id": raw.get("id"),
        "titre": raw.get("titre") or "Compte joint famille, octobre 2026",
        "compte": raw.get("compte"),
        "source": raw.get("source"),
        "periode": raw.get("periode"),
        "soldes": soldes,
        "fx": fx,
        "categories": cats,
        "totaux": tot,
        "revenus_operations": _cj_ops(raw.get("revenus_operations"), fx),
        "remboursements_operations": _cj_ops(raw.get("remboursements_operations"), fx),
        "virements_internes_entrants": _cj_ops(raw.get("virements_internes_entrants"), fx),
        "tradingview_sur_le_releve": raw.get("tradingview_sur_le_releve"),
        "operations_ambigues": raw.get("operations_ambigues") or [],
        "operations_hors_octobre": {
            "note": hors.get("note"),
            "n": hors.get("n"),
            "argent_sortant_eur": hors.get("argent_sortant_eur"),
            "argent_entrant_eur": hors.get("argent_entrant_eur"),
        },
        "en_attente": {
            "note": att.get("note"),
            "n": len(att.get("operations") or []),
            "total_sortant_eur": att.get("total_sortant_eur"),
        },
        "renvoyes": {
            "note": ren.get("note"),
            "n": len(ren.get("operations") or []),
        },
    }




def _tickets_octobre_only(sous):
    """Le bloc Comptes n'affiche qu'octobre : on retire les mois suivants des tickets."""
    out = []
    for s in sous or []:
        rec = dict(s)
        mois = rec.get("mois")
        if isinstance(mois, dict):
            rec["mois"] = {k: v for k, v in mois.items() if k == "2026-10"}
        ens = rec.get("enseignes")
        if isinstance(ens, dict):
            new_ens = {}
            for ek, ev in ens.items():
                ev2 = dict(ev) if isinstance(ev, dict) else ev
                if isinstance(ev2, dict) and isinstance(ev2.get("mois"), dict):
                    ev2["mois"] = {k: v for k, v in ev2["mois"].items() if k == "2026-10"}
                new_ens[ek] = ev2
            rec["enseignes"] = new_ens
        out.append(rec)
    return out


def build_comptes(fx):
    """Bloc fusionné « Comptes » (joint + perso), sourcé (data/budget/comptes_2026-10_11.json)."""
    if not COMPTES.exists():
        return None
    raw = json.loads(COMPTES.read_text(encoding="utf-8"))
    cats = []
    for c in raw.get("categories") or []:
        rec = {k: v for k, v in c.items() if k not in ("operations", "sous_categories", "commercants")}
        rec["observe_usd"] = _cj_usd(rec.get("observe_eur"), fx)
        rec["projection_eur"] = rec.get("observe_eur")
        rec["projection_usd"] = rec["observe_usd"]
        rec["operations"] = _cj_ops(c.get("operations"), fx)
        if c.get("id") == "courses":
            rec["commercants"] = []
            for m in c.get("commercants") or []:
                mm = dict(m)
                mm["total_usd"] = _cj_usd(mm.get("total_eur"), fx)
                rec["commercants"].append(mm)
            rec["sous_categories"] = _tickets_octobre_only(_attach_lidl_tickets(c.get("sous_categories") or [], fx))
        cats.append(rec)
    tot = dict(raw.get("totaux") or {})
    for k in list(tot):
        if k.endswith("_eur") and isinstance(tot.get(k), (int, float)):
            tot[k[:-4] + "_usd"] = _cj_usd(tot.get(k), fx)
    if isinstance(tot.get("virements_internes_detail"), list):
        det = []
        for d in tot["virements_internes_detail"]:
            dd = dict(d)
            if dd.get("montant_usd") is None:
                dd["montant_usd"] = _cj_usd(dd.get("montant_eur"), fx)
            det.append(dd)
        tot["virements_internes_detail"] = det
    soldes = dict(raw.get("soldes") or {})
    for k in list(soldes):
        if k.endswith("_eur") and isinstance(soldes.get(k), (int, float)):
            soldes[k[:-4] + "_usd"] = _cj_usd(soldes.get(k), fx)
    att = raw.get("en_attente") or {}
    ren = raw.get("renvoyes") or {}
    return {
        "id": raw.get("id"),
        "titre": raw.get("titre") or "Comptes",
        "periode": raw.get("periode"),
        "comptes": raw.get("comptes"),
        "source": raw.get("source"),
        "soldes": soldes,
        "fx": {"taux": fx, "paire": "EURUSD"} if not isinstance(raw.get("fx"), dict) else {**raw.get("fx"), "taux": fx},
        "categories": cats,
        "totaux": tot,
        "revenus_operations": _cj_ops(raw.get("revenus_operations"), fx),
        "remboursements_operations": _cj_ops(raw.get("remboursements_operations"), fx),
        "virements_internes_entrants": _cj_ops(raw.get("virements_internes_entrants"), fx),
        "financement_operations": _cj_ops(raw.get("financement_operations"), fx),
        "credits_a_confirmer": _cj_ops(raw.get("credits_a_confirmer"), fx),
        "operations_ambigues": raw.get("operations_ambigues") or [],
        "tradingview_sur_le_releve": raw.get("tradingview_sur_le_releve"),
        "regles": raw.get("regles"),
        "en_attente": {
            "note": att.get("note"),
            "n": att.get("n") if att.get("n") is not None else len(att.get("operations") or []),
            "total_sortant_eur": att.get("total_sortant_eur"),
        },
        "renvoyes": {
            "note": ren.get("note"),
            "n": ren.get("n") if ren.get("n") is not None else len(ren.get("operations") or []),
        },
    }



def build_budget_mensuel():
    """Budget mensuel moyen, sourcé (data/budget/budget_mensuel_moyen.json). Ne recalcule rien ici."""
    if not BUDGET_MENSUEL.exists():
        return None
    return json.loads(BUDGET_MENSUEL.read_text(encoding="utf-8"))



def build_frais_octobre(fx):
    """Frais de courtage octobre 2026, sourcés (data/budget/frais_courtage_2026-10.json)."""
    if not FRAIS_OCTOBRE.exists():
        return None
    raw = json.loads(FRAIS_OCTOBRE.read_text(encoding="utf-8"))
    # Recalcule les USD/EUR des totaux à partir des montants natifs, au fx du site.
    def conv_ops(ops):
        out = []
        for o in ops or []:
            rec = dict(o)
            dev = rec.get("devise_releve")
            native = rec.get("montant_releve")
            if native not in (None, "") and dev in ("USD", "EUR") and fx:
                amt = abs(float(native))
                if dev == "USD":
                    rec["montant_usd"] = r2(amt)
                    rec["montant_eur"] = r2(amt / fx)
                else:
                    rec["montant_eur"] = r2(amt)
                    rec["montant_usd"] = r2(amt * fx)
                sign = -1 if rec.get("categorie") in ("entree", "sortie", "ovn", "autres", "change") or rec.get("type") in ("commission", "trading_fee", "overnight_fee", "frais_reglementaire") else 1
                # income positive: montant_releve already positive
                if rec.get("categorie") in ("dividende", "coupon") or rec.get("type") in ("Dividend", "Bond coupon"):
                    sign = 1
                rec["montant_signe_usd"] = r2(sign * rec["montant_usd"])
                rec["montant_signe_eur"] = r2(sign * rec["montant_eur"])
            out.append(rec)
        return out

    def cat_tot(ops):
        usd_n = r2(sum(o.get("montant_usd") or 0 for o in ops if o.get("devise_releve") == "USD"))
        eur_n = r2(sum(o.get("montant_eur") or 0 for o in ops if o.get("devise_releve") == "EUR"))
        return r2(usd_n + (r2(eur_n * fx) if eur_n and fx else 0)), r2((r2(usd_n / fx) if usd_n and fx else 0) + eur_n)

    cats = []
    for c in raw.get("categories") or []:
        rec = {k: v for k, v in c.items() if k != "operations"}
        ops = conv_ops(c.get("operations") or [])
        rec["operations"] = ops
        if c.get("id") == "change" or (c.get("observe_usd") is None and not ops):
            rec["observe_usd"] = rec["observe_eur"] = rec["projection_usd"] = rec["projection_eur"] = None
        else:
            u, e = cat_tot(ops)
            rec["observe_usd"] = rec["projection_usd"] = u
            rec["observe_eur"] = rec["projection_eur"] = e
        cats.append(rec)
    by = {c["id"]: c for c in cats}
    tot = dict(raw.get("totaux") or {})
    tot["entree_usd"], tot["entree_eur"] = by["entree"]["observe_usd"], by["entree"]["observe_eur"]
    tot["sortie_usd"], tot["sortie_eur"] = by["sortie"]["observe_usd"], by["sortie"]["observe_eur"]
    tot["ovn_usd"], tot["ovn_eur"] = by["ovn"]["observe_usd"], by["ovn"]["observe_eur"]
    tot["autres_usd"], tot["autres_eur"] = by["autres"]["observe_usd"], by["autres"]["observe_eur"]
    tot["change_usd"] = tot["change_eur"] = None
    tot["frais_usd"] = r2(sum(x or 0 for x in (tot["entree_usd"], tot["sortie_usd"], tot["ovn_usd"], tot["autres_usd"])))
    tot["frais_eur"] = r2(sum(x or 0 for x in (tot["entree_eur"], tot["sortie_eur"], tot["ovn_eur"], tot["autres_eur"])))
    tot["objectif_ovn_eur"] = 20
    tot["ovn_depasse_objectif"] = (tot["ovn_eur"] or 0) > 20
    inc_raw = dict(raw.get("dividendes_et_coupons") or {})
    inc_ops = conv_ops(inc_raw.get("operations") or [])
    divs = [o for o in inc_ops if o.get("type") == "Dividend" or o.get("categorie") == "dividende"]
    coups = [o for o in inc_ops if o.get("type") == "Bond coupon" or o.get("categorie") == "coupon"]
    du, de = cat_tot(divs) if divs else (0, 0)
    cu, ce = cat_tot(coups) if coups else (0, 0)
    iu, ie = cat_tot(inc_ops) if inc_ops else (0, 0)
    inc = dict(inc_raw)
    inc["operations"] = inc_ops
    inc["dividendes_usd"], inc["dividendes_eur"] = du, de
    inc["coupons_usd"], inc["coupons_eur"] = cu, ce
    inc["net_usd"], inc["net_eur"] = iu, ie
    return {
        "id": raw.get("id"),
        "titre": raw.get("titre") or "Frais de courtage, octobre 2026",
        "compte": raw.get("compte"),
        "periode": raw.get("periode"),
        "fx": fx,
        "sources": raw.get("sources"),
        "categories": cats,
        "totaux": tot,
        "dividendes_et_coupons": inc,
        "operations_sans_frais": raw.get("operations_sans_frais") or [],
        "absents": raw.get("absents") or [],
        "notes": raw.get("notes") or [],
    }


def build_budget(fx, now):
    """Agrège OVN, frais d'ordres, TradingView et le compte joint sourcé, sans inventer un montant manquant."""
    ovn = build_frais_cfd(fx)
    tv = build_abonnement_tv(fx)
    fo = build_frais_octobre(fx)
    cj = build_compte_joint(fx)
    comptes = build_comptes(fx)
    raw_t = json.loads(FRAIS_TRADING.read_text()) if FRAIS_TRADING.exists() else {"ordres": []}
    ym = f"{now.year:04d}-{now.month:02d}"
    mois_lib = f"{MOIS_FR[now.month]} {now.year}"
    jours_mois = [j for j in (ovn.get("jours") or []) if _in_month(j.get("date"), ym)]
    tot_ovn_usd = r2(sum(abs(float(j["montant_usd"])) for j in jours_mois if j.get("montant_usd") not in (None, "")))
    tot_ovn_eur = r2(tot_ovn_usd / fx) if fx else None
    lignes = []
    for o in list(raw_t.get("ordres") or []):
        usd = _fee_usd(o, fx)
        rec = dict(o)
        rec["montant_usd"] = usd
        rec["montant_eur"] = r2(usd / fx) if (usd is not None and fx) else None
        lignes.append(rec)
    lignes_mois = [x for x in lignes if _in_month(x.get("date"), ym)]
    a_relever = not lignes
    # Totaux de catégorie : somme des montants natifs, puis une seule conversion (comme les frais d'octobre).
    if a_relever:
        tot_tr_usd = tot_tr_eur = None
    else:
        usd_n = r2(sum(abs(float(x["montant"])) for x in lignes_mois if str(x.get("devise") or "").upper()=="USD" and x.get("montant") not in (None, "")))
        eur_n = r2(sum(abs(float(x["montant"])) for x in lignes_mois if str(x.get("devise") or "").upper()=="EUR" and x.get("montant") not in (None, "")))
        tot_tr_usd = r2(usd_n + (r2(eur_n * fx) if eur_n and fx else 0))
        tot_tr_eur = r2(eur_n + (r2(usd_n / fx) if usd_n and fx else 0))
    observe_usd = r2(tot_ovn_usd + (tot_tr_usd or 0))
    return {
        "mois": ym,
        "mois_libelle": mois_lib,
        "fx": fx,
        "ovn": {
            **ovn,
            "lignes_mois": jours_mois,
            "total_mois_usd": tot_ovn_usd,
            "total_mois_eur": tot_ovn_eur,
        },
        "trading": {
            "mode_emploi": raw_t.get("mode_emploi"),
            "recherche_repo": raw_t.get("recherche_repo"),
            "ordres": lignes,
            "lignes_mois": lignes_mois,
            "a_relever": a_relever,
            "total_mois_usd": tot_tr_usd,
            "total_mois_eur": tot_tr_eur,
            "projection_usd": tot_tr_usd,
            "projection_eur": tot_tr_eur,
            "projection_note": "à relever" if a_relever else raw_t.get("note"),
            "note": raw_t.get("note"),
        },
        "tradingview": tv,
        "frais_octobre": fo,
        "compte_joint": cj,
        "comptes": comptes,
        "budget_mensuel": build_budget_mensuel(),
        "total_observe_usd": observe_usd,
        "total_observe_eur": r2(observe_usd / fx) if fx else None,
        "projection_usd": r2((ovn.get("projection_usd") or 0) + ((tv or {}).get("projection_usd") or 0) + (tot_tr_usd or 0)),
        "projection_eur": r2((ovn.get("projection_eur") or 0) + ((tv or {}).get("projection_eur") or 0) + (tot_tr_eur or 0)),
        "projection_note": (
            "Projection mensuelle = OVN projeté (dernier jour relu × ~30 jours) "
            "et abonnement TradingView (Essential annuel / 12). "
            "Les frais d'ordres n'y sont pas inclus tant qu'aucun montant n'est sourcé."
            if a_relever else
            "Projection mensuelle = OVN projeté (dernier jour relu × ~30 jours), "
            "abonnement TradingView (Essential annuel / 12) et frais d'ordres déjà sourcés en novembre. "
            "Les transactions sans commission sont épuisées jusqu'au 7 décembre 2026."
        ),
    }


def main():
    rel = json.loads(RELEVE.read_text())
    rv = rel["revolut"]["comptes"]
    titres = rv["compte_titres"]["positions"]
    ordres = rv["compte_titres"]["ordres"]
    metaux = rv["matieres_premieres"]["positions"]
    cash_usd = float(rv["compte_titres"]["liquidites_usd"])

    # Taux officiel du 25/11 (plan Tesla, 03 h 51 EDT) : plus récent que le taux
    # implicite des lignes euro conservées du 24/11 20 h 31 (1,094217).
    fx_rel = (rel.get("fx") or {})
    fx = float(fx_rel.get("taux") or 1.0944)
    print("EURUSD officiel", fx)

    cfd_acc = rv["cfd"]
    cfd_rows_raw = cfd_acc.get("positions") or []
    raw_cfd_val = cfd_acc.get("valeur_usd")
    cfd_val = float(raw_cfd_val) if raw_cfd_val not in (None, "") else None
    cfd_pct = cfd_acc.get("pl_pct")
    cfd_pl = cfd_acc.get("pl_usd")
    if cfd_pl in (None, "") and cfd_val is not None and cfd_pct not in (None, ""):
        cfd_pl = r2(cfd_val - cfd_val / (1 - float(cfd_pct) / 100.0)) if float(cfd_pct) != 100 else None
    elif cfd_pl not in (None, ""):
        cfd_pl = float(cfd_pl)
    else:
        cfd_pl = None
    cfd_names = [x.get("ticker") for x in cfd_rows_raw if x.get("ticker")]
    cfd_n = len(cfd_rows_raw)

    liv = []
    for p in titres:
        liv.append(from_invest_line(p, fx))
    for o in ordres:
        liv.append(from_order(o, fx))
    for p in metaux:
        liv.append(from_metal(p, fx))
    liv.append(from_cash(cash_usd, fx))
    cfd_rows = [from_cfd(p, fx) for p in cfd_rows_raw]
    liv.extend(cfd_rows)

    xtb_eur = next(c for c in rel["xtb"]["comptes"] if str(c["id"]) == "54086450")
    mau = xtb_eur["positions"][0]
    pea = xtb_eur["pea"]
    xtb_cash = float(xtb_eur.get("fonds_disponibles") or 0)
    xtb_rows = [from_mau(mau, fx), from_xtb_cash(xtb_cash, fx), from_pea(pea, fx)]

    rx_raw = rv["revolut_x"]["positions"]
    rx_rows = []
    for p in rx_raw:
        if p.get("ticker") == "BTC":
            rx_rows.append(from_btc(p, fx))
        elif p.get("ticker") == "ETH":
            rx_rows.append(from_eth(p, fx))
        else:
            raise SystemExit(f"ligne Revolut X inconnue: {p.get('ticker')}")

    apply_yields(liv)
    apply_yields(xtb_rows)
    apply_yields(rx_rows)

    book_rows = liv + xtb_rows  # revolutx fusionné au chargement JS

    t_liv_spot = totaux([p for p in liv if p.get("type") != "cfd"], "revolut")
    t_xtb = totaux(xtb_rows, "xtb")
    t_rx = totaux(rx_rows, "revolutx")
    t_xtb["compte"] = "54086450"
    t_xtb["devise_compte"] = "EUR"

    def fr_money(n, d=2):
        s = f"{n:,.{d}f}"
        return s.replace(",", "X").replace(".", ",").replace("X", " ")

    # Courtage et métaux : totaux officiels des captures 09 h 50.
    # CFD : exposition (quantité × cours) des lignes relues à 10 h 14, pas la marge
    # ni la seule valeur du compte.
    off_ct_usd = 12549.34
    off_met_usd = 2082.68
    off_cfd_compte = 2614.02
    off_cfd_affiche = 2644.26
    off_cfd_pl = -4264.65 if cfd_pl is None else r2(cfd_pl)
    off_cfd_pct = -61.56
    cfd_relu = [p for p in cfd_rows if p.get("pnl_relu") and p.get("valeur_usd") is not None]
    expo_cfd = r2(sum(p["valeur_usd"] for p in cfd_relu))
    entry_cfd = r2(sum((p.get("investi_usd") or 0) for p in cfd_relu))
    pl_cfd_lignes = r2(sum((p.get("pnl_valeur") or 0) for p in cfd_relu))
    off_cfd_usd = expo_cfd  # montant retenu dans les totaux = exposition
    off_spot_usd = r2(off_ct_usd + off_met_usd)
    inv_ct = off_ct_usd / (1 - 0.0038)
    inv_met = off_met_usd / (1 - 0.0412)
    inv_spot = r2(inv_ct + inv_met)
    off_rev_usd = r2(off_spot_usd + expo_cfd)
    off_rev_investi = r2(inv_spot + entry_cfd)
    off_rev_pl = r2(off_rev_usd - off_rev_investi)
    off_rev_pct = r2(100.0 * off_rev_pl / off_rev_investi, 1) if off_rev_investi else None
    off_rx_usd = 1554.56
    off_rx_pl = -47.69
    off_rx_pct = -2.98
    off_xtb_eur = 535.35
    off_xtb_pl = -14.65
    off_xtb_usd = r2(off_xtb_eur * fx)
    liquide_usd = r2(off_rev_usd + off_rx_usd + off_xtb_usd)
    liquide_eur = r2(off_rev_usd / fx + off_rx_usd / fx + off_xtb_eur)
    tesla_eur = 12302.45
    tesla_usd = r2(tesla_eur * fx)
    patrimoine_eur = r2(liquide_eur + tesla_eur)
    patrimoine_usd = r2(liquide_usd + tesla_usd)


    t_rev = {
        "valeur_eur": r2(off_rev_usd / fx),
        "valeur_usd": off_rev_usd,
        "investi_usd": off_rev_investi,
        "investi_eur": r2(off_rev_investi / fx),
        "perf_debut_pct": off_rev_pct,
        "statut": "ok",
        "n": sum(1 for p in liv if p.get("statut") in ("active", "en_attente")),
        "compte_courtage_usd": off_ct_usd,
        "compte_courtage_pct": -0.38,
        "matieres_usd": off_met_usd,
        "matieres_pct": -4.12,
        "cfd_exposition_usd": expo_cfd,
        "cfd_entree_usd": entry_cfd,
        "cfd_compte_usd": off_cfd_compte,
        "cfd_compte_affiche_usd": off_cfd_affiche,
        "cfd_usd": expo_cfd,
        "cfd_pct": off_cfd_pct,
        "cfd_pl_usd": off_cfd_pl,
        "cfd_pl_lignes_usd": pl_cfd_lignes,
        "somme_lignes_usd": t_liv_spot["valeur_usd"] + expo_cfd,
        "note": (
            f"Total Revolut = courtage {off_ct_usd} $ + métaux {off_met_usd} $ (captures 09 h 50) "
            f"+ exposition CFD {expo_cfd} $ (10 h 14). Le capital du compte CFD n'est que "
            f"{off_cfd_compte} $ : l'exposition dépasse le capital."
        ),
    }
    t_rx.update({
        "valeur_usd": off_rx_usd,
        "valeur_eur": r2(off_rx_usd / fx),
        "investi_usd": r2(off_rx_usd - off_rx_pl),
        "investi_eur": r2((off_rx_usd - off_rx_pl) / fx),
        "perf_debut_pct": off_rx_pct,
        "n": len(rx_rows),
        "statut": "ok",
    })
    t_xtb.update({
        "valeur_eur": off_xtb_eur,
        "valeur_usd": off_xtb_usd,
        "investi_eur": r2(off_xtb_eur - off_xtb_pl),
        "investi_usd": r2((off_xtb_eur - off_xtb_pl) * fx),
        "perf_debut_pct": r2(100.0 * off_xtb_pl / (off_xtb_eur - off_xtb_pl), 1) if (off_xtb_eur - off_xtb_pl) else None,
        "fonds_disponibles_eur": 5.93,
        "n": len(xtb_rows),
        "statut": "ok",
    })

    tesla = rel.get("tesla_plan") or {}
    tesla_plan = {
        "nom": tesla.get("nom") or "Plan d'actions Tesla",
        "avantage_potentiel_eur": tesla_eur,
        "avantage_potentiel_usd": tesla_usd,
        "valeur_compte_eur": tesla.get("valeur_compte_eur", 0),
        "non_liquide": True,
        "libelle": tesla.get("libelle") or "non liquide / avantage potentiel",
        "cours_tsla_usd": tesla.get("cours_tsla_usd", 384.68),
        "fx": fx,
        "releve": tesla.get("releve"),
        "releve_libelle": tesla.get("releve_libelle"),
        "note": tesla.get("note"),
    }
    tesla_row = from_tesla(tesla_plan, fx)
    book_rows = book_rows + [tesla_row]

    officiels = {
        "source": "Captures Revolut / Revolut X / XTB et plan Tesla du 25/11/2026 vers 09 h 50 (Europe/Paris) ; CFD vers 10 h 11–10 h 14, short COST relu à 11 h 01. Tesla à 03 h 51 EDT (09 h 51 Europe/Paris).",
        "fx": fx,
        "revolut": t_rev,
        "revolutx": t_rx,
        "xtb": t_xtb,
        "liquide_usd": liquide_usd,
        "liquide_eur": liquide_eur,
        "patrimoine_usd": patrimoine_usd,
        "patrimoine_eur": patrimoine_eur,
        "tesla_plan": tesla_plan,
        "note": (
            "Courtage 12 549,34 $ et métaux 2 082,68 $ : captures du 25/11 à 09 h 50. "
            "Lignes titres et métaux encore au pointage 08 h 15 (notes TradingView). "
            f"CFD au 25/11 vers 10 h 14 : exposition {fr_money(expo_cfd)} $ incluse dans les totaux, "
            f"alors que la valeur du compte (capital) n'est que {fr_money(off_cfd_compte)} $ "
            f"(affiché {fr_money(off_cfd_affiche)} $, P&L {fr_money(off_cfd_pl).replace('-', '−')} $, −61,56 %). "
            "Short COST relu à 11 h 01, inclus dans l'exposition. Tesla RSU inclus dans le total de Mes positions, pas en double compte."
        ),
    }

    tot_usd = patrimoine_usd
    entete_detail = (
        f"Total {fr_money(patrimoine_usd)} $ = courtage Revolut {fr_money(off_ct_usd)} $ + "
        f"métaux {fr_money(off_met_usd)} $ + exposition CFD {fr_money(expo_cfd)} $ + "
        f"Revolut X {fr_money(off_rx_usd)} $ + XTB {fr_money(off_xtb_eur)} € ({fr_money(off_xtb_usd)} $) + "
        f"Tesla RSU {fr_money(tesla_eur)} € ({fr_money(tesla_usd)} $). "
        "Sans double compte : le capital du compte CFD n'est pas ajouté en plus de l'exposition ; "
        "les liquidités sont déjà dans le courtage Revolut et le compte XTB. "
        "Le % porte sur les positions avec prix de revient connu (Tesla non liquide, P/L non calculé)."
    )
    officiels["entete_detail"] = entete_detail
    officiels["total_affiche_usd"] = patrimoine_usd
    for p in book_rows + rx_rows:
        v = p.get("valeur_usd") or 0
        p["poids_pct"] = round(100 * v / tot_usd + 1e-9, 1) if tot_usd else None

    now = datetime(2026, 11, 25, 10, 14, tzinfo=PARIS)
    frais_cfd = build_frais_cfd(fx)
    budget = build_budget(fx, now)
    fx_obj = {
        "paire": "EURUSD",
        "taux": fx,
        "date": "2026-11-25",
        "source": fx_rel.get("source") or (
            "Taux EURUSD 1,0944 indiqué sur le plan d'actions Tesla au 25/11/2026 "
            "à 03 h 51 EDT (09 h 51 Europe/Paris)."
        ),
        "source_court": fx_rel.get("source_court") or "Plan Tesla 25/11/2026 03:51 EDT",
        "zone": "Europe/Paris",
    }

    cfd_note = cfd_acc.get("note") or ""
    cfd_txt = (
        f"exposition {fr_money(expo_cfd)} $ (somme quantité × cours des 6 lignes relues, COST inclus à 11 h 01), "
        f"P&L lignes {fr_money(pl_cfd_lignes).replace('-', '−')} $, "
        f"valeur du compte {fr_money(off_cfd_compte)} $ (affiché {fr_money(off_cfd_affiche)} $, "
        f"{fr_money(off_cfd_pl).replace('-', '−')} $, −61,56 %), "
        f"marge de maintenance 98 % / seuil de fermeture 1 336,40 $"
    )

    desc = (
        f"Captures du 25/11/2026 : courtage, métaux, Revolut X, XTB et Tesla vers 09 h 50 ; "
        f"CFD vers 10 h 11–10 h 14 (Europe/Paris). "
        f"Revolut Invest, montant retenu {fr_money(off_rev_usd)} $ = courtage {fr_money(off_ct_usd)} $ "
        f"(−0,38 %) + métaux {fr_money(off_met_usd)} $ (−4,12 %) + exposition CFD {fr_money(expo_cfd)} $. "
        f"Attention : l'exposition CFD dépasse le capital du compte ({fr_money(off_cfd_compte)} $ ; {cfd_txt}). "
        f"Les CFD sont des positions normales dans Mes positions, les totaux, le tableau sectoriel et le patrimoine "
        f"(montant = exposition, pas la marge). Short COST relu à 11 h 01, inclus dans l'exposition. "
        f"Lignes titres et métaux : cours et P/L du pointage 08 h 15 (notes TradingView). "
        f"Revolut X {fr_money(off_rx_usd)} $ (−47,69 $, −2,98 %). "
        f"XTB {fr_money(off_xtb_eur)} € (fonds disponibles 5,93 €, gain −14,65 €). "
        f"Plan Tesla (RSU) : avantage potentiel {fr_money(tesla_eur)} € ({fr_money(tesla_usd)} $), compte 0 €, non liquide, inclus dans le total de Mes positions. "
        f"Taux EURUSD {str(fx).replace('.', ',')}."
    )

    pea_xtb = {
        "ouvert": True,
        "compte": "54086450",
        "devise": "EUR",
        "valeur_eur": r2(pea["valeur"]),
        "valeur_marche_eur": r2(pea["valeur_marche"]) if pea.get("valeur_marche") is not None else None,
        "cash_eur": r2(pea["fonds_dispo"]) if pea.get("fonds_dispo") is not None else None,
        "pnl_eur": r2(pea["pl"]),
        "instrument_pl_pct": pea.get("instrument_pl_pct"),
        "ligne": pea.get("ligne") or "ligne PEA non identifiée",
        "valeur_usd": r2(float(pea["valeur"]) * fx),
        "note": (
            f"PEA XTB #54086450 relevé le 25/11/2026 vers 09 h 50 (Europe/Paris) : "
            f"{fr_money(float(pea['valeur']))} € (résultat {fr_money(float(pea['pl']))} €). "
            f"Une ligne à −51,1 %, nom non lisible : « ligne PEA non identifiée ». "
            f"Valeur de marché et cash non séparés : non inventés. Inclus dans Mes positions."
        ),
    }
    xtb_id = {
        "compte": "54086450",
        "devise_compte": "EUR",
        "certitude": "élevée",
        "lignes": [
            {"nom": "Etablissements Maurel et Prom", "tv": "EURONEXT:MAU", "xtb": "MAU.FR",
             "cotation": "Euronext Paris"},
            {"nom": "ligne PEA non identifiée", "tv": None, "xtb": None,
             "cotation": None, "note": "PEA, logo bleu foncé avec un A, nom non lisible, −51,1 %."},
        ],
        "pea_compte": "54086450",
        "autres_comptes": [
            {"compte": "54128907", "devise": "USD", "valeur": 0.01, "note": "aucune position, non relu à 09 h 50"},
            {"compte": "54351185", "devise": "USD", "valeur": 0.0, "note": "aucune position, non relu à 09 h 50"},
            {"compte": "54351187", "devise": "CAD", "valeur": 0.0, "note": "aucune position (ENPH et PKX retirés), non relu à 09 h 50"},
        ],
        "note": (
            "Compte réel EUR #54086450 relevé le 25/11/2026 vers 09 h 50 : "
            "Maurel & Prom (81 titres, 519,21 €, −0,93 %), liquidités 5,93 €, et PEA 10,21 €. "
            "Deutsche Bank clôturée le 16/11/2026. Aucun ordre XTB en attente. "
            "Comptes USD et CAD non relus à 09 h 50 (à 0 le 24/11)."
        ),
    }

    # Alerte rouge : l'exposition dépasse le capital, marge de maintenance 98 %.
    cfd_alert = {
        "courtier": "revolut",
        "inclus": True,
        "afficher_encadre": True,
        "valeur_usd": off_cfd_compte,
        "valeur_affichee_usd": off_cfd_affiche,
        "pnl_usd": off_cfd_pl,
        "pnl_pct": off_cfd_pct,
        "exposition_usd": expo_cfd,
        "pl_lignes_usd": pl_cfd_lignes,
        "marge_reservee_usd": 2672.80,
        "solde_pret_a_investir_usd": 0,
        "liquidites_usd": 0,
        "marge_maintenance_pct": 98,
        "seuil_fermeture_usd": 1336.40,
        "n": len(cfd_relu),
        "tickers": [p["sous_jacent"] for p in cfd_relu],
        "a_confirmer": [p["sous_jacent"] for p in cfd_rows if p.get("a_confirmer")],
        "libelle": (
            f"Alerte CFD : l'exposition {fr_money(expo_cfd)} $ dépasse le capital du compte "
            f"({fr_money(off_cfd_compte)} $, affiché {fr_money(off_cfd_affiche)} $, "
            f"P&L {fr_money(off_cfd_pl).replace('-', '−')} $, −61,56 %). "
            f"Marge de maintenance 98 % — fermeture forcée si la valeur passe sous 1 336,40 $. "
            f"Marge réservée 2 672,80 $, solde prêt à investir 0 $, cash USD 0 $."
        ),
        "note": cfd_note,
    }

    book = {
        "releve": now.isoformat(),
        "releve_libelle": "COST CFD 25/11/2026 à 11 h 01 · autres CFD 10 h 14 · autres comptes 09 h 50 (Europe/Paris)",
        "xtb_releve_libelle": "XTB 25/11/2026 à 09 h 50 (Europe/Paris)",
        "source": desc,
        "compte": "Revolut Invest, Revolut X, XTB et plan Tesla (non liquide)",
        "n_actives": sum(1 for p in book_rows if p["statut"] == "active"),
        "n_en_attente": sum(1 for p in book_rows if p["statut"] == "en_attente"),
        "positions": book_rows,
        "fx": fx_obj,
        "totaux": {
            "total_usd": patrimoine_usd,
            "total_eur": patrimoine_eur,
            "entete_detail": entete_detail,
            "investi_usd": r2(t_rev["investi_usd"] + t_rx["investi_usd"] + t_xtb["investi_usd"]),
            "investi_eur": r2(t_rev["investi_eur"] + t_rx["investi_eur"] + t_xtb["investi_eur"]),
            "perf_debut_pct": r2(
                100.0 * (
                    (t_rev["valeur_usd"] + t_rx["valeur_usd"] + t_xtb["valeur_usd"])
                    / (t_rev["investi_usd"] + t_rx["investi_usd"] + t_xtb["investi_usd"])
                    - 1
                ),
                1,
            ),
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
            "officiels": officiels,
            "tesla_plan": tesla_plan,
            "patrimoine_usd": patrimoine_usd,
            "patrimoine_eur": patrimoine_eur,
            "liquide_usd": liquide_usd,
            "liquide_eur": liquide_eur,
        },
        "desc": desc,
        "pea_xtb": pea_xtb,
        "xtb_identification": xtb_id,
        "cfd_alerte": cfd_alert,
        "frais_cfd": frais_cfd,
        "budget": budget,
    }

    book_path = DATA / "positions.json"
    book_path.write_text(json.dumps(book, ensure_ascii=False, indent=2) + "\n")
    _mirror_site_root(book_path)
    sha = hashlib.sha256(book_path.read_bytes()).hexdigest()

    rv_json = {
        "releve": now.isoformat(),
        "releve_libelle": "Revolut 25/11/2026 : CFD 10 h 14 · courtage et métaux 09 h 50 (Europe/Paris)",
        "source": (
            "Captures Revolut Invest : CFD du 25/11/2026 vers 10 h 11–10 h 14 (exposition, pas la marge) ; "
            "courtage et métaux à 09 h 50. Lignes titres et métaux au pointage 08 h 15 "
            f"(notes TradingView). Liquidités ({fr_money(cash_usd)} $) incluses (non relues)."
        ),
        "compte": "Revolut Invest",
        "n_actives": sum(1 for p in liv if p["statut"] == "active"),
        "n_en_attente": sum(1 for p in liv if p["statut"] == "en_attente"),
        "positions": liv,
        "fx": fx_obj,
        "liquidites": {
            "usd": r2(cash_usd),
            "eur": r2(cash_usd / fx),
            "source": "Revolut Invest, cash au 24/11/2026 20:31, non relu le 25/11 09:50",
            "inclus_dans_total": True,
        },
        "totaux": t_rev,
        "positions_json_sha256": sha,
        "cfd_alerte": cfd_alert,
        "frais_cfd": frais_cfd,
        "budget": budget,
        "desc": (
            f"Captures Revolut Invest du 25/11/2026 (CFD 10 h 14, reste 09 h 50). "
            f"Total retenu {fr_money(off_rev_usd)} $ dont exposition CFD {fr_money(expo_cfd)} $ "
            f"(capital du compte CFD {fr_money(off_cfd_compte)} $). "
            f"{fr_money(cash_usd)} $ de liquidités du compte-titres (non relues)."
        ),
    }
    (DATA / "positions_revolut.json").write_text(json.dumps(rv_json, ensure_ascii=False, indent=2) + "\n")
    _mirror_site_root(DATA / "positions_revolut.json")

    rx_json = {
        "releve": now.isoformat(),
        "releve_libelle": "Revolut X 25/11/2026 à 09 h 50 (Europe/Paris)",
        "source": (
            "Capture Revolut X du 25/11/2026 vers 09 h 50 (Europe/Paris). "
            "Bitcoin ajouté (0,018 BTC). Ether conservé (0,28 ETH), cours mis à jour."
        ),
        "compte": "Revolut X",
        "n_actives": len(rx_rows),
        "n_en_attente": 0,
        "positions": rx_rows,
        "fx": fx_obj,
        "totaux": t_rx,
        "desc": (
            f"Relevé Revolut X du 25/11/2026 à 09 h 50 : total {fr_money(off_rx_usd)} $ "
            f"(−47,69 $, −2,98 %). BTC 0,018 = {fr_money(1086.14)} $ (−0,87 %), "
            f"ETH 0,28 = {fr_money(468.35)} $ (−7,54 %)."
        ),
    }
    (DATA / "positions_revolutx.json").write_text(json.dumps(rx_json, ensure_ascii=False, indent=2) + "\n")
    _mirror_site_root(DATA / "positions_revolutx.json")

    print("wrote", book_path, "n", len(book_rows), "actives", book["n_actives"], "ordres", book["n_en_attente"])
    print("tickers", [p["ticker"] + ("*" if p["statut"] == "en_attente" else "") for p in book_rows])
    print("rx", [p["ticker"] for p in rx_rows])
    print("totaux USD", liquide_usd, "EUR", liquide_eur, "patrimoine EUR", patrimoine_eur)
    print("cfd compte", off_cfd_compte, "expo", expo_cfd, "pl", off_cfd_pl, "lignes", [p["ticker"] for p in cfd_rows])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
