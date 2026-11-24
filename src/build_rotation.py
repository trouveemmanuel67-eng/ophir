#!/usr/bin/env python3
"""Construit data/rotation.json : ratio mensuel S&P 500 / WTI et moyenne mobile 7 ans.

Aucune donnée n'est inventée. Sources publiques déjà enregistrées dans data/rotation/ :
  - spx_daily.csv : clôtures quotidiennes du S&P 500 (Yahoo Finance ^GSPC, depuis 1927)
  - fred_WTISPLC.csv : WTI spot, moyenne mensuelle (FRED WTISPLC, depuis 1946)
  - fred_DCOILWTICO.csv : WTI spot Cushing, quotidien (FRED DCOILWTICO, depuis 1986)

Le ratio officiel d'un mois = dernier cours du S&P 500 de ce mois / moyenne mensuelle
WTI (WTISPLC). Si WTISPLC n'est pas encore publié pour un mois déjà achevé, on
prend la moyenne des séances DCOILWTICO de ce mois. La moyenne mobile est
arithmétique, sur 84 mois (7 ans). Le régime de Charles Gave se lit sur le
dernier mois calendaire achevé. Une lecture provisoire est donnée au dernier
jour commun aux deux séries quotidiennes, comparée à cette moyenne mobile
(le mois en cours n'entre pas dans la moyenne).

Pour rafraîchir les sources :
  curl --http1.1 -L -o data/rotation/fred_WTISPLC.csv \\
    'https://fred.stlouisfed.org/graph/fredgraph.csv?id=WTISPLC'
  curl --http1.1 -L -o data/rotation/fred_DCOILWTICO.csv \\
    'https://fred.stlouisfed.org/graph/fredgraph.csv?id=DCOILWTICO'
  et les clôtures ^GSPC (Yahoo query1, interval=1d), réexportées en spx_daily.csv.
"""
from __future__ import annotations

import csv
import json
import datetime as D
from pathlib import Path
from zoneinfo import ZoneInfo
from collections import defaultdict

PARIS = ZoneInfo("Europe/Paris")
ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "rotation"
OUT = ROOT / "data" / "rotation.json"
MA_MONTHS = 84


def _f(x):
    try:
        v = float(str(x).replace(",", "").strip())
    except (TypeError, ValueError):
        return None
    if v != v:
        return None
    return v


def read_fred_csv(path: Path, col: str):
    rows = []
    with path.open(newline="") as f:
        r = csv.DictReader(f)
        for row in r:
            d = (row.get("observation_date") or row.get("DATE") or "").strip()
            v = _f(row.get(col) or row.get("VALUE") or "")
            if not d or v is None:
                continue
            rows.append((D.date.fromisoformat(d[:10]), v))
    rows.sort()
    return rows


def read_spx_csv(path: Path):
    rows = []
    with path.open(newline="") as f:
        r = csv.DictReader(f)
        for row in r:
            d = (row.get("date") or "").strip()
            v = _f(row.get("close") or "")
            if not d or v is None:
                continue
            rows.append((D.date.fromisoformat(d[:10]), v))
    rows.sort()
    return rows


def month_end(series):
    acc = {}
    for d, v in series:
        acc[(d.year, d.month)] = (d, v)
    return acc


def month_avg(series):
    acc = defaultdict(list)
    for d, v in series:
        acc[(d.year, d.month)].append((d, v))
    out = {}
    for k, lst in acc.items():
        vals = [v for _, v in lst]
        out[k] = (lst[-1][0], sum(vals) / len(vals), len(vals))
    return out


def regime(above):
    if above is True:
        return {
            "id": "boom",
            "label": "Boom",
            "axe": "Boom (efficacité énergétique)",
            "rotation": (
                "Énergie bon marché par rapport aux actions : boom des actions, "
                "bust énergétique. Cadre favorable à la croissance."
            ),
        }
    if above is False:
        return {
            "id": "bust",
            "label": "Bust",
            "axe": "Bust (énergie chère)",
            "rotation": (
                "Énergie chère par rapport aux actions : boom énergétique, "
                "bust des actions. Cadre favorable aux matières premières et "
                "à l’énergie ; prudence sur les actions."
            ),
        }
    return None


def main():
    now = D.datetime.now(PARIS)
    today = now.date()
    spx = read_spx_csv(RAW / "spx_daily.csv")
    wti_d = read_fred_csv(RAW / "fred_DCOILWTICO.csv", "DCOILWTICO")
    wti_m = read_fred_csv(RAW / "fred_WTISPLC.csv", "WTISPLC")
    if not spx or not wti_m:
        raise SystemExit("sources manquantes dans data/rotation/")

    spx_me = month_end(spx)
    wti_m_map = {(d.year, d.month): (d, v) for d, v in wti_m}
    wti_d_avg = month_avg(wti_d)

    last_closed = D.date(today.year, today.month, 1) - D.timedelta(days=1)
    closed_key = (last_closed.year, last_closed.month)

    series = []
    for key in sorted(spx_me):
        if key > closed_key:
            continue  # mois en cours exclu de la série officielle
        y, m = key
        sd, sv = spx_me[key]
        if key in wti_m_map:
            wd, wv = wti_m_map[key]
            wti_src = "FRED WTISPLC (moyenne mensuelle)"
        elif key <= closed_key and key in wti_d_avg:
            wd, wv, n = wti_d_avg[key]
            wti_src = f"FRED DCOILWTICO (moyenne de {n} séances, WTISPLC non encore publié)"
        else:
            continue
        if wv <= 0:
            continue
        series.append({
            "month": f"{y:04d}-{m:02d}",
            "spx": round(sv, 2),
            "spx_date": sd.isoformat(),
            "wti": round(wv, 3) if wv < 10 else round(wv, 2),
            "wti_date": wd.isoformat() if isinstance(wd, D.date) else str(wd)[:10],
            "wti_src": wti_src,
            "ratio": round(sv / wv, 4),
        })

    for i, row in enumerate(series):
        if i + 1 < MA_MONTHS:
            row["ma84"] = None
            continue
        window = [series[j]["ratio"] for j in range(i + 1 - MA_MONTHS, i + 1)]
        row["ma84"] = round(sum(window) / MA_MONTHS, 4)

    official = None
    for row in reversed(series):
        if row.get("ma84") is not None:
            official = row
            break

    # lecture provisoire : dernier jour commun S&P / WTI spot
    spx_map = dict(spx)
    wti_map = dict(wti_d)
    common_days = sorted(set(spx_map) & set(wti_map))
    last_common = common_days[-1] if common_days else None
    provisional = None
    if last_common and official and official.get("ma84"):
        pspx = spx_map[last_common]
        pwti = wti_map[last_common]
        if pwti > 0:
            pratio = pspx / pwti
            pma = official["ma84"]
            pecart = (pratio / pma - 1) * 100
            provisional = {
                "date": last_common.isoformat(),
                "spx": round(pspx, 2),
                "wti": round(pwti, 2),
                "ratio": round(pratio, 4),
                "ma84": pma,
                "ecart_pct": round(pecart, 2),
                "above": pratio > pma,
            }

    closed_rows = [r for r in series if r.get("ma84") is not None]
    last_cross = None
    prev_side = None
    for r in closed_rows:
        side = "above" if r["ratio"] > r["ma84"] else ("below" if r["ratio"] < r["ma84"] else "equal")
        if prev_side and side not in (prev_side, "equal") and prev_side != "equal":
            last_cross = {
                "month": r["month"],
                "from": prev_side,
                "to": side,
                "ratio": r["ratio"],
                "ma84": r["ma84"],
            }
        if side != "equal":
            prev_side = side

    off_above = None
    official_out = None
    if official and official.get("ma84") is not None:
        off_above = official["ratio"] > official["ma84"]
        official_out = {
            "month": official["month"],
            "spx": official["spx"],
            "spx_date": official["spx_date"],
            "wti": official["wti"],
            "wti_date": official["wti_date"],
            "wti_src": official["wti_src"],
            "ratio": official["ratio"],
            "ma84": official["ma84"],
            "ecart_pct": round((official["ratio"] / official["ma84"] - 1) * 100, 2),
            "above": off_above,
        }

    chart = [{"m": r["month"], "r": r["ratio"], "ma": r["ma84"]} for r in closed_rows]
    recent = []
    for r in closed_rows[-8:]:
        recent.append({
            "month": r["month"],
            "spx": r["spx"],
            "spx_date": r["spx_date"],
            "wti": r["wti"],
            "wti_date": r["wti_date"],
            "ratio": r["ratio"],
            "ma84": r["ma84"],
            "ecart_pct": round((r["ratio"] / r["ma84"] - 1) * 100, 2),
        })

    payload = {
        "titre": "INDICE ROTATION",
        "cadre": "Charles Gave · ratio S&P 500 / WTI",
        "updated": now.strftime("%Y-%m-%d %H:%M"),
        "updated_tz": "Europe/Paris",
        "ma_mois": MA_MONTHS,
        "officiel": official_out,
        "provisoire": provisional,
        "regime_officiel": regime(off_above) if official_out else None,
        "regime_provisoire": (
            regime(provisional["above"])
            if provisional and provisional.get("above") is not None
            else None
        ),
        "dernier_croisement": last_cross,
        "serie": chart,
        "recent": recent,
        "historique": {
            "premier_ratio": series[0]["month"] if series else None,
            "premier_ma": chart[0]["m"] if chart else None,
            "dernier_mois": series[-1]["month"] if series else None,
            "n_mois": len(series),
            "n_ma": len(chart),
            "spx_premier": spx[0][0].isoformat(),
            "spx_dernier": spx[-1][0].isoformat(),
            "wti_daily_premier": wti_d[0][0].isoformat() if wti_d else None,
            "wti_daily_dernier": wti_d[-1][0].isoformat() if wti_d else None,
            "wti_mensuel_premier": wti_m[0][0].isoformat(),
            "wti_mensuel_dernier": wti_m[-1][0].isoformat(),
        },
        "methode": (
            "Ratio officiel = dernier cours du S&P 500 du mois (Yahoo Finance ^GSPC) "
            "divisé par la moyenne mensuelle du WTI spot (FRED WTISPLC). Si cette "
            "moyenne n’est pas encore publiée pour un mois déjà achevé, on utilise "
            "la moyenne des séances FRED DCOILWTICO de ce mois. Moyenne mobile "
            "arithmétique sur 84 mois (7 ans). Le régime officiel de Charles Gave "
            "se lit sur le dernier mois calendaire achevé. Une lecture provisoire "
            "est donnée au dernier jour commun aux deux séries quotidiennes "
            "(S&P 500 Yahoo et WTI spot FRED DCOILWTICO), comparée à la moyenne "
            "mobile du mois achevé — le mois en cours n’entre pas dans la moyenne."
        ),
        "sources_donnees": [
            {
                "nom": "Yahoo Finance ^GSPC",
                "url": "https://finance.yahoo.com/quote/%5EGSPC/history/",
                "role": "S&P 500, clôtures quotidiennes (historique depuis 1927).",
            },
            {
                "nom": "FRED WTISPLC",
                "url": "https://fred.stlouisfed.org/series/WTISPLC",
                "role": "WTI spot, moyenne mensuelle, dénominateur officiel du ratio.",
            },
            {
                "nom": "FRED DCOILWTICO",
                "url": "https://fred.stlouisfed.org/series/DCOILWTICO",
                "role": "WTI spot Cushing, quotidien, depuis 1986 : lecture provisoire et secours si WTISPLC n’est pas encore publié.",
            },
        ],
        "sources_cadre": [
            {
                "nom": "Charles Gave, The General Theory of Portfolio Construction, Gavekal, octobre 2024",
                "url": "https://web.gavekal.com/media/ebook_files/PDF_The_General_Theory_of_Portfolio_Construction.pdf",
                "extrait": (
                    "Règle de l’axe d’efficacité énergétique : +1 si le ratio S&P 500 / WTI "
                    "est au-dessus de sa moyenne mobile 7 ans (côté droit des Quatre Quadrants, "
                    "boom déflationnaire ou inflationnaire) ; −1 s’il est en dessous (bust)."
                ),
            },
            {
                "nom": "Charles Gave, « L’économie est de l’énergie transformée », Institut des Libertés, 9 octobre 2022",
                "url": "https://institutdeslibertes.org/leconomie-est-de-lenergie-transformee/",
                "extrait": (
                    "Si le ratio S&P / WTI monte, la valeur créée par les sociétés cotées "
                    "couvre plus que le coût de l’énergie employée ; s’il baisse, les nouvelles "
                    "valeurs créées ne couvrent pas leur coût énergétique, et l’économie a de "
                    "grandes chances d’aller mal."
                ),
            },
        ],
        "avertissement": (
            "Ceci n’est que l’axe boom / bust (efficacité énergétique) des Quatre Quadrants "
            "de Charles Gave. L’axe d’inflation (obligations / or) n’est pas affiché ici. "
            "Aucun rendement n’est promis."
        ),
    }

    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("écrit", OUT, "mois", len(series), "avec MM", len(chart))
    print("officiel", official_out)
    print("provisoire", provisional)
    print("croisement", last_cross)
    print("maj", payload["updated"])


if __name__ == "__main__":
    main()
