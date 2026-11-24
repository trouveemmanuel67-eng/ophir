#!/usr/bin/env python3
"""Met à jour data/positions_revolut.json à partir d'un relevé CSV Revolut Invest.

Depuis le 24/11/2026 (t452u), le livre officiel est produit par
update_positions_releve.py à partir de data/revolut/releve_courtiers_YYYY-MM-DD.json.
Ne pas relancer ce script sur un ancien CSV : il réintroduirait des lignes cédées.

Ne touche pas à positions.json : les lignes Revolut mises à jour vivent dans
positions_revolut.json et sont fusionnées au chargement (les lignes XTB du
livre de base restent inchangées).
"""
from __future__ import annotations

import argparse, csv, json, hashlib
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
BOOK = DATA / "positions.json"
TABS = DATA / "tabs_data.json"
OUT_DEFAULT = DATA / "positions_revolut.json"


def r2(x: float, n: int = 2) -> float:
    return round(x + 1e-12, n)


def r0(x: float) -> int:
    return int(round(x + 1e-12))


def num(s: str) -> float:
    return float(str(s).strip().replace("%", "").replace(" ", "").replace("\u2212", "-").replace(",", "."))


def load_csv(path: Path) -> list[dict]:
    rows = list(csv.DictReader(path.open(encoding="utf-8-sig"), delimiter=";"))
    if len(rows) != 18:
        raise SystemExit(f"{path} : {len(rows)} lignes, 18 attendues")
    return rows


def eurusd_weekly(tabs: dict) -> tuple[float, str]:
    fx = (tabs.get("liquidites") or {}).get("fx") or {}
    last = fx.get("eurusd_last") or (fx.get("eurusd_w") or [None])[-1]
    if not last or not isinstance(last, (list, tuple)) or len(last) < 2:
        raise SystemExit("EURUSD hebdomadaire introuvable dans tabs_data.json")
    return float(last[1]), str(last[0])


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--csv", type=Path, default=DATA / "revolut" / "positions_revolut_2026-11-22.csv")
    ap.add_argument("--releve", default="2026-11-22T19:34:00+01:00")
    ap.add_argument("--cash-usd", type=float, default=1.30, help="liquidités Invest, hors total")
    ap.add_argument("--compte-usd", type=float, default=10332.52, help="total affiché par Revolut, liquidités incluses")
    ap.add_argument("--out", type=Path, default=OUT_DEFAULT)
    args = ap.parse_args()

    book = json.loads(BOOK.read_text())
    h = hashlib.sha256(BOOK.read_bytes()).hexdigest()
    if h != "9e23e0ff69a2e2b90b39b7be1a29260281ec063f04a1857757cb786aa4f5477f":
        # on lit seulement ; un hash différent n'est pas réécrit, mais on prévient
        print("attention : hash de positions.json inattendu :", h)

    tabs = json.loads(TABS.read_text())
    fx, fx_date = eurusd_weekly(tabs)
    when = datetime.fromisoformat(args.releve)
    rows = load_csv(args.csv)
    by_id = {p["ticker"]: p for p in book["positions"] if p.get("courtier") == "revolut"}

    positions = []
    for r in rows:
        tid = r["ticker/ISIN"]
        if tid not in by_id:
            raise SystemExit(f"ligne {tid} absente du livre de base : métadonnées non inventées")
        src = dict(by_id[tid])
        q, pm, cours = num(r["quantite"]), num(r["prix_moyen"]), num(r["cours"])
        # mêmes quantités et prix moyens que le 19/11 : le coût déjà calculé (frais inclus) est conservé
        if abs(q - float(src["quantite"])) > 1e-8 or abs(pm - float(src["prix_moyen"])) > 1e-8:
            raise SystemExit(f"{tid} : quantité ou prix moyen changé, coût à reprendre à la main")
        dev = r["devise"].strip().upper()
        pnl_pct = num(r["PnL_%"])
        pnl_usd = num(r["PnL_USD"])
        if dev == "USD":
            val_usd = r2(q * cours)
            val_eur = r2(val_usd / fx)
            inv_usd = float(src["investi_usd"])
            inv_eur = r2(inv_usd / fx)
            val_nat, inv_nat = val_usd, inv_usd
            pnl = r2(pnl_usd)
        elif dev == "EUR":
            val_eur = r2(q * cours)
            val_usd = r2(val_eur * fx)
            inv_eur = float(src["investi_eur"])
            inv_usd = r2(inv_eur * fx)
            val_nat, inv_nat = val_eur, inv_eur
            pnl = r2(val_eur - inv_eur)
        else:
            raise SystemExit(f"{tid} : devise {dev} non gérée")

        src.update({
            "cours": cours,
            "investi": r2(inv_nat),
            "investi_arrondi": r0(inv_nat),
            "valeur": r2(val_nat),
            "valeur_arrondie": r0(val_nat),
            "pnl_valeur": pnl,
            "pnl_pct": pnl_pct,
            "valeur_usd": val_usd,
            "valeur_eur": val_eur,
            "investi_usd": r2(inv_usd),
            "investi_eur": r2(inv_eur),
            "perf_debut_pct": pnl_pct,
            "courtier": "revolut",
            "statut": "active",
        })
        positions.append(src)

    tot_eur = r2(sum(p["valeur_eur"] for p in positions))
    tot_usd = r2(sum(p["valeur_usd"] for p in positions))
    inv_eur = r2(sum(p["investi_eur"] for p in positions))
    inv_usd = r2(sum(p["investi_usd"] for p in positions))
    perf = r2(100.0 * (tot_eur / inv_eur - 1), 1) if inv_eur else None
    cash_eur = r2(args.cash_usd / fx) if args.cash_usd is not None else None

    releve_lib = f"Revolut {when.day}/{when.month:02d}/{when.year} à {when.hour} h {when.minute:02d}"
    out = {
        "releve": when.isoformat(),
        "releve_libelle": releve_lib + " (Europe/Paris)",
        "source": (
            f"Relevé Revolut Invest du {when.day}/{when.month:02d}/{when.year} à "
            f"{when.hour} h {when.minute:02d} (Europe/Paris), lecture seule, "
            f"{args.csv.name}, 18 lignes, aucun ordre en attente. "
            f"Le compte titres affiche {args.compte_usd:,.2f} $ ({perf:+.2f} % calculé sur les coûts connus en euros), "
            f"dont {args.cash_usd:,.2f} $ de liquidités Invest (non incluses dans Mes positions, comme précédemment). "
            f"Compte CFD exclu, règle APEX. "
            f"Quantités et prix moyens inchangés par rapport au 19/11 : les coûts d'achat du livre "
            f"(frais d'exécution Hermès, Kering, Fanuc inclus) sont conservés, seuls les cours sont mis à jour. "
            f"Conversion : Yahoo Finance, clôture hebdomadaire du {fx_date}, EURUSD {fx} "
            f"(même série que l'onglet Liquidités), et non le taux intra-journalier de Revolut, "
            f"d'où un écart possible avec les valorisations USD des lignes en euros. "
            f"Les lignes XTB restent celles de positions.json, non modifié. "
            f"sha256 positions.json lu : {h}."
        ),
        "compte": "Invest",
        "n_actives": 18,
        "n_en_attente": 0,
        "positions": positions,
        "fx": {
            "paire": "EURUSD",
            "taux": fx,
            "date": fx_date,
            "source": f"Yahoo Finance, clôture hebdomadaire du {fx_date}, EURUSD {fx} (série de l'onglet Liquidités)",
            "source_court": f"Yahoo Finance, clôture du {fx_date}",
            "zone": "Europe/Paris",
        },
        "liquidites": {
            "usd": args.cash_usd,
            "eur": cash_eur,
            "source": "Revolut Invest",
            "inclus_dans_total": False,
        },
        "totaux": {
            "devise_principale": "USD",
            "valeur_usd": tot_usd,
            "valeur_eur": tot_eur,
            "investi_usd": inv_usd,
            "investi_eur": inv_eur,
            "perf_debut_pct": perf,
            "n": 18,
            "statut": "ok",
            "affiche_revolut_usd": args.compte_usd,
            "liquidites_usd": args.cash_usd,
        },
        "positions_json_sha256": h,
        "desc": (
            f"{releve_lib} (Europe/Paris). 18 lignes, {tot_eur:,.2f} € / {tot_usd:,.2f} $, "
            f"{perf:+.1f} % depuis l'achat. Liquidités Invest {args.cash_usd:,.2f} $ "
            f"({cash_eur:,.2f} € au taux {fx}), hors total. CFD exclu."
        ),
    }
    args.out.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n")
    print("écrit", args.out)
    print("revolut", tot_eur, "€ /", tot_usd, "$  investi", inv_eur, "€  perf", perf, "%")
    print("cash", args.cash_usd, "$ =", cash_eur, "€  fx", fx, fx_date)
    print("positions.json", h, "non modifié")


if __name__ == "__main__":
    main()
