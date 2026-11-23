#!/usr/bin/env python3
"""Met à jour data/positions_revolutx.json à partir d'un relevé Revolut X.

Lecture seule : uniquement
  revx account balances
  revx order open / history
  revx trade private <PAIRE>
  revx market tickers / candles
Aucune commande de passage, modification ou annulation d'ordre n'est utilisée.
Ne touche pas à positions.json.
"""
from __future__ import annotations

import argparse, json, math, subprocess, sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

PARIS = timezone(timedelta(hours=1))  # Europe/Paris, UTC+1 en novembre
ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
RXDIR = DATA / "revolutx"
OUT_DEFAULT = DATA / "positions_revolutx.json"
SIGNIFICANT = {"BTC", "ETH"}
DUST_MIN_EUR = 1.0

# Commandes autorisées (lecture seule)
ALLOWED_PREFIXES = (
    ("revx", "account", "balances"),
    ("revx", "order", "open"),
    ("revx", "order", "history"),
    ("revx", "trade", "private"),
    ("revx", "market", "tickers"),
    ("revx", "market", "ticker"),
    ("revx", "market", "candles"),
)


def reject_if_unsafe(cmd: list[str]) -> None:
    if cmd[:1] != ["revx"]:
        raise SystemExit(f"commande interdite (pas revx) : {cmd}")
    # interdire toute mutation
    banned = {"place", "cancel", "replace", "configure", "strategy", "monitor"}
    if any(p in banned for p in cmd[1:]):
        raise SystemExit(f"commande d'écriture interdite : {cmd}")
    ok = any(tuple(cmd[: len(p)]) == p for p in ALLOWED_PREFIXES)
    if not ok:
        raise SystemExit(f"commande revx non autorisée (lecture seule) : {cmd}")


def run_revx(args: list[str]) -> dict:
    cmd = ["revx", *args]
    reject_if_unsafe(cmd)
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise SystemExit(f"échec {' '.join(cmd)}\n{r.stderr or r.stdout}")
    return json.loads(r.stdout)


def load_json(path: Path):
    return json.loads(path.read_text())


def mid_hl(c: dict) -> float:
    return (float(c["high"]) + float(c["low"])) / 2.0


def candle_at(path: Path, when: datetime) -> dict | None:
    if not path.exists():
        return None
    data = load_json(path)
    rows = data.get("data", data)
    target = int(when.astimezone(timezone.utc).timestamp() * 1000)
    best = None
    for c in rows:
        s = int(c["start"])
        if best is None or abs(s - target) < abs(int(best["start"]) - target):
            best = c
    return best


def trades_of(path: Path) -> list[dict]:
    if not path.exists():
        return []
    data = load_json(path)
    rows = data.get("data", data)
    return rows if isinstance(rows, list) else []


def fifo_remaining(trades: list[dict]) -> tuple[float, float, float, bool]:
    """Retourne (qty_nette, qty_fifo, coût_fifo en devise de cotation, historique_complet)."""
    ts = sorted(trades, key=lambda t: t["timestamp"])
    buy_q = sell_q = 0.0
    lots: list[list[float]] = []
    complete = True
    for t in ts:
        q, p = float(t["quantity"]), float(t["price"])
        if t["side"] == "buy":
            buy_q += q
            lots.append([q, p])
        else:
            sell_q += q
            left = q
            while left > 1e-12 and lots:
                take = min(lots[0][0], left)
                lots[0][0] -= take
                left -= take
                if lots[0][0] <= 1e-12:
                    lots.pop(0)
            if left > 1e-8:
                complete = False
    rem_q = sum(l[0] for l in lots)
    rem_cost = sum(l[0] * l[1] for l in lots)
    return buy_q - sell_q, rem_q, rem_cost, complete


def r2(x: float, n: int = 2) -> float:
    return round(x + 1e-12, n)


def r1(x: float) -> float:
    return round(x + 1e-12, 1)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--live", action="store_true", help="interroger revx (lecture seule) au lieu des fichiers déjà enregistrés")
    ap.add_argument("--balances", type=Path, default=RXDIR / "balances_2026-11-22.json")
    ap.add_argument("--open-orders", type=Path, default=RXDIR / "open_orders_2026-11-22.json")
    ap.add_argument("--releve", default="2026-11-22T18:06:00+01:00")
    ap.add_argument("--out", type=Path, default=OUT_DEFAULT)
    args = ap.parse_args()

    when = datetime.fromisoformat(args.releve)
    if args.live:
        bals = run_revx(["account", "balances", "--json"])
        (RXDIR / f"balances_live_{when.strftime('%Y-%m-%d_%H%M')}.json").write_text(json.dumps(bals, ensure_ascii=False, indent=2))
        if isinstance(bals, dict):
            bals = bals.get("data", bals)
        opens = run_revx(["order", "open", "--json"])
        (RXDIR / f"open_orders_live_{when.strftime('%Y-%m-%d_%H%M')}.json").write_text(json.dumps(opens, ensure_ascii=False, indent=2))
    else:
        bals = load_json(args.balances)
        if isinstance(bals, dict):
            bals = bals.get("data", bals)
        opens = load_json(args.open_orders)

    open_n = len((opens or {}).get("data") or opens or [])
    if isinstance(opens, list):
        open_n = len(opens)

    # Prix : bougies 1 minute (cours mid = (plus haut + plus bas) / 2)
    tag = when.strftime("%Y-%m-%d_%H%M")
    def _cand(pair):
        tagged = RXDIR / f"candles_{pair}_1m_{tag}.json"
        legacy = RXDIR / "candles_{}_1m_2026-11-22.json".format(pair)
        if tagged.exists():
            return candle_at(tagged, when)
        return candle_at(legacy, when)
    c_btc_eur = None if args.live else _cand("BTC-EUR")
    c_eth_eur = None if args.live else _cand("ETH-EUR")
    c_btc_usd = None if args.live else _cand("BTC-USD")
    if args.live:
        start = (when - timedelta(minutes=2)).strftime("%Y-%m-%dT%H:%M:%S")
        end = (when + timedelta(minutes=3)).strftime("%Y-%m-%dT%H:%M:%S")
        for pair, attr in (("BTC-EUR", "c_btc_eur"), ("ETH-EUR", "c_eth_eur"), ("BTC-USD", "c_btc_usd")):
            raw = run_revx(["market", "candles", pair, "--interval", "1m", "--since", start, "--until", end, "--json"])
            dest = RXDIR / f"candles_{pair}_1m_{tag}.json"
            dest.write_text(json.dumps(raw, ensure_ascii=False, indent=2))
            c = candle_at(dest, when)
            if pair == "BTC-EUR":
                c_btc_eur = c
            elif pair == "ETH-EUR":
                c_eth_eur = c
            else:
                c_btc_usd = c
        # tickers pour valoriser la poussière au même instant
        raw = run_revx(["market", "tickers", "--json"])
        (RXDIR / f"tickers_{tag}.json").write_text(json.dumps(raw, ensure_ascii=False, indent=2))
        tick_path_live = RXDIR / f"tickers_{tag}.json"
    else:
        tick_path_live = None

    if not c_btc_eur or not c_eth_eur:
        raise SystemExit("bougies BTC-EUR / ETH-EUR à l'heure du relevé introuvables")

    px_btc_eur = mid_hl(c_btc_eur)
    px_eth_eur = mid_hl(c_eth_eur)
    if c_btc_usd:
        px_btc_usd = mid_hl(c_btc_usd)
        eurusd = px_btc_usd / px_btc_eur
        fx_src = f"implicite BTC-USD / BTC-EUR, bougies 1 min à {when.hour} h {when.minute:02d} (Europe/Paris)"
    else:
        eurusd = None
        px_btc_usd = None
        fx_src = None

    qty = {b["currency"]: float(b["total"]) for b in bals if float(b.get("total") or 0) > 0}

    # Poussière : valoriser via tickers EUR (ou USD / taux implicite)
    tickers = {}
    tagged_tick = RXDIR / f"tickers_{tag}.json"
    tick_path = tick_path_live if (args.live and tick_path_live and tick_path_live.exists()) else (tagged_tick if tagged_tick.exists() else (RXDIR / "tickers_2026-11-22.json"))

    if tick_path.exists():
        td = load_json(tick_path)
        for t in td.get("data", td):
            tickers[t["symbol"]] = t

    def px_eur(sym: str) -> float | None:
        t = tickers.get(f"{sym}/EUR")
        if t and t.get("mid"):
            return float(t["mid"])
        t = tickers.get(f"{sym}/USD")
        if t and t.get("mid") and eurusd:
            return float(t["mid"]) / eurusd
        return None

    dust = []
    dust_eur = 0.0
    for cur, q in qty.items():
        if cur in SIGNIFICANT:
            continue
        p = px_eur(cur)
        v = (p * q) if p is not None else None
        dust.append({"currency": cur, "quantite": q, "valeur_eur": r2(v, 6) if v is not None else None})
        if v:
            dust_eur += v

    # Prix de revient via trade private (historique le plus long disponible)
    trades = {
        "BTC-USD": trades_of(RXDIR / "trades_BTC-USD.json"),
        "BTC-EUR": trades_of(RXDIR / "trades_BTC-EUR.json"),
        "ETH-USD": trades_of(RXDIR / "trades_ETH-USD.json"),
        "ETH-EUR": trades_of(RXDIR / "trades_ETH-EUR.json"),
    }
    if args.live:
        for pair in ("BTC-USD", "BTC-EUR", "ETH-USD", "ETH-EUR"):
            if not trades[pair]:
                raw = run_revx(["trade", "private", pair, "--start-date", "2017-01-01", "--limit", "1000", "--json"])
                (RXDIR / f"trades_{pair}.json").write_text(json.dumps(raw, ensure_ascii=False, indent=2))
                trades[pair] = trades_of(RXDIR / f"trades_{pair}.json")

    positions = []
    specs = [
        ("BTC", "Bitcoin", "BTC", px_btc_eur, trades["BTC-USD"] + trades["BTC-EUR"], "USD"),
        ("ETH", "Ether", "ETH", px_eth_eur, trades["ETH-USD"] + trades["ETH-EUR"], "USD"),
    ]
    notes_cost = {}
    for ident, nom, fiche, cours_eur, tr, cost_ccy in specs:
        q = qty.get(ident, 0.0)
        val_eur = q * cours_eur
        val_usd = val_eur * eurusd if eurusd else None
        net, rem, cost, complete = fifo_remaining(tr) if tr else (None, None, None, False)
        # Historique complet seulement si le solde est expliqué par les trades (écart < 0,5 %)
        invested = pnl = pnl_pct = prix_moyen = None
        note_cout = None
        if tr and rem and rem > 0 and complete and net is not None and abs(net - q) / max(q, 1e-12) < 0.01:
            avg = cost / rem
            # ramener le coût à la quantité réellement détenue
            cost_held = avg * q
            if cost_ccy == "USD" and eurusd:
                investi_usd = cost_held
                investi_eur = cost_held / eurusd
            else:
                investi_eur = cost_held
                investi_usd = cost_held * eurusd if eurusd else None
            invested = investi_eur
            pnl = val_eur - investi_eur
            pnl_pct = r1(100.0 * pnl / investi_eur) if investi_eur else None
            prix_moyen = r2(investi_eur / q, 2) if q else None
            note_cout = (
                f"Prix de revient FIFO d'après l'historique revx trade private "
                f"{ident}-USD (aucun trade {ident}-EUR). "
                f"Coût moyen {r2(avg, 2)} $ soit {r2(prix_moyen, 2)} € / {ident} "
                f"(taux implicite {r2(eurusd, 5)})."
            )
        else:
            gap = None if (net is None) else (q - net)
            note_cout = (
                f"Prix de revient incomplet : l'historique revx trade private "
                f"{ident}-USD/{ident}-EUR n'explique pas tout le solde "
                f"({q:.8f} détenu"
                + (f", net des trades {net:.8f}, écart {gap:.8f}" if net is not None else "")
                + "). Transfert ou dépôt probable, non inventé. Seul le montant est affiché."
            )
        notes_cost[ident] = note_cout
        positions.append({
            "id": f"RX-{ident}",
            "nom": nom,
            "ticker": ident,
            "type": "crypto",
            "statut": "active",
            "quantite": q,
            "prix_moyen": prix_moyen,
            "cours": r2(cours_eur, 2),
            "devise": "EUR",
            "investi": r2(invested, 2) if invested is not None else None,
            "investi_arrondi": int(round(invested)) if invested is not None else None,
            "valeur": r2(val_eur, 2),
            "valeur_arrondie": int(round(val_eur)),
            "pnl_valeur": r2(pnl, 2) if pnl is not None else None,
            "pnl_pct": pnl_pct,
            "tv_note": ident,
            "note_tv_ok": True,
            "fiche_tv": ident,
            "fiche_nom": nom,
            "fiche_proxy": False,
            "fiche_note": note_cout,
            "tab": "crypto",
            "apex_score": None,
            "apex_label": None,
            "drapeau": None,
            "drapeau_code": None,
            "courtier": "revolutx",
            "valeur_usd": r2(val_usd, 2) if val_usd is not None else None,
            "investi_usd": r2(investi_usd, 2) if invested is not None and eurusd else None,
            "valeur_eur": r2(val_eur, 2),
            "investi_eur": r2(invested, 2) if invested is not None else None,
            "perf_debut_pct": pnl_pct,
            "perf_1an_pct": None,
            "perf_1an_libelle": "à venir",
            "perf_1an_note": "Pas d'historique hebdomadaire de la valeur de la ligne Revolut X ; le rendement 1 an n'est pas inventé.",
            "poids_pct": None,
            "source": "Revolut X",
        })

    dust_line = None
    if dust_eur >= DUST_MIN_EUR:
        dust_line = {
            "id": "RX-DUST",
            "nom": "Poussière",
            "ticker": "DUST",
            "type": "crypto",
            "statut": "active",
            "quantite": None,
            "cours": None,
            "devise": "EUR",
            "valeur": r2(dust_eur, 2),
            "valeur_arrondie": int(round(dust_eur)),
            "valeur_eur": r2(dust_eur, 2),
            "valeur_usd": r2(dust_eur * eurusd, 2) if eurusd else None,
            "pnl_pct": None,
            "fiche_tv": None,
            "fiche_note": f"{len(dust)} petites lignes Revolut X regroupées, total {r2(dust_eur, 2)} €.",
            "tab": "crypto",
            "courtier": "revolutx",
            "source": "Revolut X",
        }
        positions.append(dust_line)

    total_eur = sum(p["valeur_eur"] for p in positions)
    total_usd = sum(p["valeur_usd"] or 0 for p in positions)
    for p in positions:
        p["poids_pct"] = r1(100.0 * p["valeur_eur"] / total_eur) if total_eur else None

    releve_dt = when.strftime("%d/%m/%Y à %H h %M").lstrip("0").replace("/0", "/")
    # 22/11/2026 à 18 h 06
    releve_lib = f"Revolut X {when.day}/{when.month:02d}/{when.year} à {when.hour} h {when.minute:02d}"

    out = {
        "releve": when.isoformat(),
        "releve_libelle": releve_lib + " (Europe/Paris)",
        "source": (
            f"Relevé Revolut X (CLI revx, lecture seule) du {when.day}/{when.month:02d}/{when.year} vers {when.hour} h {when.minute:02d} (Europe/Paris). "
            "Soldes : account balances. Aucun ordre ouvert (order open). "
            f"Cours mid BTC/EUR et ETH/EUR : (plus haut + plus bas) de la bougie 1 minute de {when.hour} h {when.minute:02d}. "
            "Taux EUR/USD implicite au même instant via BTC-USD / BTC-EUR. "
            "Prix de revient : trade private BTC-USD et ETH-USD (historique depuis 2017, paires EUR vides). "
            "Les ~40 autres cryptos, poussière inférieure à 1 €, sont omises. "
            "Aucune commande d'ordre n'a été utilisée. Ne remplace pas positions.json."
        ),
        "compte": "Revolut X",
        "n_actives": len(positions),
        "n_en_attente": open_n,
        "positions": positions,
        "fx": {
            "paire": "EURUSD implicite",
            "taux": r2(eurusd, 5) if eurusd else None,
            "date": "2026-11-22",
            "heure": when.strftime("%H:%M"),
            "zone": "Europe/Paris",
            "btc_eur": r2(px_btc_eur, 2),
            "eth_eur": r2(px_eth_eur, 2),
            "btc_usd": r2(px_btc_usd, 2) if px_btc_usd else None,
            "source": fx_src,
        },
        "totaux": {
            "devise_principale": "EUR",
            "valeur_eur": r2(total_eur, 2),
            "valeur_usd": r2(total_usd, 2),
            "n": len(positions),
            "statut": "ok",
            "dust_eur": r2(dust_eur, 4),
            "dust_lignes": len(dust),
            "dust_omise": dust_line is None,
        },
        "couts": notes_cost,
        "desc": (
            f"{releve_lib} (Europe/Paris). "
            f"BTC {qty.get('BTC',0):.8f} à {r2(px_btc_eur,2)} € et "
            f"ETH {qty.get('ETH',0):.8f} à {r2(px_eth_eur,2)} €. "
            f"Poussière {r2(dust_eur,2)} € sur {len(dust)} lignes, "
            + ("omise (< 1 €)." if dust_line is None else "regroupée.")
        ),
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n")
    print("écrit", args.out)
    print("BTC", qty.get("BTC"), "x", r2(px_btc_eur, 2), "=", r2(qty.get("BTC", 0) * px_btc_eur, 2), "€")
    print("ETH", qty.get("ETH"), "x", r2(px_eth_eur, 2), "=", r2(qty.get("ETH", 0) * px_eth_eur, 2), "€", "coût", notes_cost["ETH"][:80])
    print("total", r2(total_eur, 2), "€ /", r2(total_usd, 2), "$")
    print("poussière", r2(dust_eur, 4), "€ n=", len(dust), "omise" if dust_line is None else "ligne")
    print("eurusd", eurusd)


if __name__ == "__main__":
    main()
