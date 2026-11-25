#!/usr/bin/env python3
"""Construit data/rotation_capitaux.json : rotation de capitaux la plus probable.

Aucune donnée n'est inventée. Cette lecture est distincte de l'INDICE ROTATION
(Charles Gave, ratio S&P 500 / WTI), qui reste le régime boom/bust.

Méthode (scores 0-100, moyenne pondérée) :

  Score de SORTIE  = 40 % sentiment élevé
                   + 30 % essoufflement du momentum
                   + 30 % RSI élevé
  Score d'ENTRÉE   = 40 % sentiment bas (100 − sentiment)
                   + 30 % retournement du momentum
                   + 30 % RSI bas (100 − RSI)

  - Sentiment : indice composite APEX 0-100 déjà publié dans
    data/sentiment_secteurs.json (et data/indicateur.json pour
    Liquidités et Immobilier France).
  - Momentum : performance sur 21 séances, comparée à celle d'il y a
    10 séances, normalisée par la volatilité réalisée 20 j
    (variation typique de cette performance). Une détérioration
    augmente le score de sortie ; une amélioration, le score d'entrée.
  - RSI : RSI 14 journalier de la série de prix représentative.

Si une composante manque, les poids des composantes restantes sont
renormalisés (et le manque est déclaré). Les flux ETF ne sont pas
disponibles dans les sources du site : ils n'entrent pas dans le score.

La rotation la plus probable relie la classe au plus fort score de
sortie à la classe distincte au plus fort score d'entrée. Une paire
alternative (2e sortie → 1re entrée, ou 1re sortie → 2e entrée) est
donnée. Le même calcul est fait sur les 11 secteurs d'actions US (SPDR).

Confiance : forte si l'écart au 2e de chaque côté est ≥ 12 pts et les
deux scores ≥ 55 avec les 3 composantes ; moyenne si l'écart mini ≥ 6,
ou ≥ 4 avec des scores ≥ 55 ; sinon faible. Une composante manquante
plafonne la confiance à moyenne.
"""
from __future__ import annotations

import json
import math
import statistics
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

PARIS = ZoneInfo("Europe/Paris")
ROOT = Path(__file__).resolve().parents[1]
SRC = Path(__file__).resolve().parent
CACHE = ROOT / "data" / "sentiment_cache"
OUT = ROOT / "data" / "rotation_capitaux.json"

sys.path.insert(0, str(SRC))
import build_sentiment_secteurs as sent  # noqa: E402

# Paniers documentés (tickers Yahoo déjà en cache sentiment).
US_SECTORS = [(s, fr) for s, fr, *_ in sent.US_SECTORS]

CLASS_SENT = {
    "actions": {
        "label": "Actions",
        "keys": [s for s, _ in US_SECTORS],
        "group": "secteurs_us",
        "tickers": [s for s, _ in US_SECTORS],
        "sentiment_note": "Moyenne simple des 11 secteurs GICS US (ETF SPDR).",
    },
    "obligations": {
        "label": "Obligations",
        "keys": [
            "oblig:tcourt", "oblig:tlong", "oblig:t710", "oblig:agg", "oblig:usig",
            "oblig:hy", "oblig:infl", "oblig:em", "oblig:eurgov", "oblig:eurig", "oblig:de",
        ],
        "group": "classes",
        "tickers": ["SHY", "IEF", "TLT", "AGG", "LQD", "HYG", "TIP", "EMB", "EUNH.DE", "EUN5.DE", "EXX6.DE"],
        "sentiment_note": "Moyenne simple des 11 indicateurs obligataires APEX (US, Europe, HY, TIPS, émergents).",
    },
    "metaux": {
        "label": "Métaux",
        "keys": ["metal:or", "metal:argent", "metal:platine", "metal:palladium"],
        "group": "classes",
        "tickers": ["GC=F", "SI=F", "PL=F", "PA=F"],
        "sentiment_note": "Moyenne simple or, argent, platine, palladium (contrats Yahoo).",
    },
    "energie": {
        "label": "Énergie",
        "keys": ["energie:petrole", "energie:brent", "energie:gaz"],
        "group": "classes",
        "tickers": ["CL=F", "BZ=F", "NG=F"],
        "sentiment_note": "Moyenne simple WTI, Brent et gaz naturel (contrats). Classe matières premières, distincte du secteur actions XLE.",
    },
    "crypto": {
        "label": "Crypto",
        "keys": ["crypto"],
        "group": "classes",
        "tickers": ["BTC-USD", "ETH-USD"],
        "sentiment_note": "Crypto Fear & Greed d'alternative.me (officiel). Momentum : moyenne Bitcoin et Ether.",
    },
    "liquidites": {
        "label": "Liquidités",
        "keys": ["liquidites"],
        "group": "classes",
        "tickers": [],
        "indicator": "liquidites",
        "sentiment_note": "Indice APEX « appétit pour le risque / attrait du cash » (data/indicateur.json). Pas de série de prix quotidienne : pas de RSI. Le momentum est la variation de l'indice sur 4 semaines.",
    },
    "immobilier": {
        "label": "Immobilier",
        "keys": ["immo:fr", "immo:reit_us", "immo:reit_eu"],
        "group": "classes",
        "tickers": ["VNQ", "EXI5.DE"],
        "indicator": "immobilier",
        "sentiment_note": "Moyenne de l'indice APEX immobilier France et des sentiments REIT US (VNQ) et Europe (EXI5). Momentum et RSI : uniquement les deux ETF REIT (pas de cours quotidien de l'immobilier physique français).",
    },
}

FADE_UNIT = 1.0  # 1 σ de variation du momentum 21 j (vol-normalisée) → score 0 ou 100
CONF_FORT_GAP = 12
CONF_MOYEN_GAP = 6
CONF_MOYEN_GAP_MIN = 4
CONF_SCORE_MIN = 55


def _r(x, n=1):
    if x is None:
        return None
    return round(float(x) + 1e-12, n)


def clip01(x):
    return max(0.0, min(100.0, x))


def load_cache(symbol):
    rec = sent.fetch_yahoo_chart(symbol, interval="1d", use_cache=True)
    if rec and rec.get("ok") and rec.get("series"):
        return rec
    # forcer la lecture du cache même périmé
    path = CACHE / f"yahoo_1d_{symbol.replace('/', '_').replace('=', '_')}.json"
    if path.exists() and path.stat().st_size > 200:
        try:
            return sent.parse_chart(json.loads(path.read_text()), symbol)
        except Exception:
            return {"ok": False, "symbol": symbol}
    return rec or {"ok": False, "symbol": symbol}


def ew_series(series_list):
    """Indice équipondéré à partir des rendements journaliers communs."""
    if not series_list:
        return []
    maps = []
    for s in series_list:
        if len(s) < 30:
            continue
        dmap = {d: c for d, c in s}
        maps.append(dmap)
    if not maps:
        return []
    # dates présentes dans au moins 2 séries, ou 1 si une seule série
    from collections import Counter
    cnt = Counter()
    for m in maps:
        cnt.update(m.keys())
    need = 1 if len(maps) == 1 else max(2, int(math.ceil(0.7 * len(maps))))
    dates = sorted(d for d, n in cnt.items() if n >= need)
    if len(dates) < 40:
        return []
    idx = []
    level = 100.0
    prev = None
    for d in dates:
        rets = []
        for m in maps:
            if prev is not None and d in m and prev in m and m[prev]:
                rets.append(m[d] / m[prev] - 1)
        if prev is None:
            idx.append((d, level))
        elif rets:
            level *= 1 + (sum(rets) / len(rets))
            idx.append((d, level))
        prev = d if any(d in m for m in maps) else prev
    return idx


def price_metrics(series):
    """RSI 14, perf 21 j, perf 21 j il y a 10 séances, vol 20 j, dates."""
    if not series or len(series) < 40:
        return None
    closes = [c for _, c in series]
    dates = [d for d, _ in series]
    n = len(closes)
    i = n - 1
    lag = 10
    if i < 21 + lag:
        return None
    rsi = sent.rsi14(closes)
    ret21 = (closes[i] / closes[i - 21] - 1) if closes[i - 21] else None
    ret21_prev = (closes[i - lag] / closes[i - lag - 21] - 1) if closes[i - lag - 21] else None
    rets = []
    for k in range(max(1, i - 19), i + 1):
        if closes[k - 1]:
            rets.append(closes[k] / closes[k - 1] - 1)
    vol20 = statistics.pstdev(rets) * math.sqrt(252) if len(rets) >= 15 else None
    # vol typique d'une perf 21 j (approx.)
    vol21 = (vol20 * math.sqrt(21 / 252) * 100) if vol20 is not None else None
    return {
        "date": dates[i],
        "close": _r(closes[i], 4),
        "rsi": None if rsi[i] is None else _r(rsi[i], 1),
        "ret21_pct": None if ret21 is None else _r(ret21 * 100, 2),
        "ret21_prev_pct": None if ret21_prev is None else _r(ret21_prev * 100, 2),
        "delta_ret21_pct": None if ret21 is None or ret21_prev is None else _r((ret21 - ret21_prev) * 100, 2),
        "vol20_ann_pct": None if vol20 is None else _r(vol20 * 100, 2),
        "vol21_pct": None if vol21 is None else _r(vol21, 2),
        "n": n,
    }


# Plancher : 3 points de % de variation du momentum 21 j valent au moins
# une unité de score. Sans ce plancher, un actif très peu volatil (obligations,
# REIT) verrait une micro-variation porter le score d'essoufflement à 100.
MIN_DELTA_SCALE = 3.0


def fade_turn_from_delta(delta, vol21):
    """delta = variation de la perf 21 j en points de %. vol21 = vol typique de cette perf."""
    if delta is None:
        return None, None
    scale = max(float(vol21) if vol21 and vol21 > 0 else MIN_DELTA_SCALE, MIN_DELTA_SCALE)
    z = delta / scale  # +1 = amélioration d'au moins 3 pts (ou 1 σ si plus volatile)
    turn = clip01(50 + 50 * (z / FADE_UNIT))
    fade = clip01(50 - 50 * (z / FADE_UNIT))
    return _r(fade, 1), _r(turn, 1)


def indicator_fade(series, weeks=4):
    """Variation d'un indice hebdomadaire 0-100 (Liquidités, Immo France)."""
    if not series or len(series) < weeks + 1:
        return None
    # series = [[date, value], ...]
    vals = [(str(a), float(b)) for a, b in series if b is not None]
    if len(vals) < weeks + 1:
        return None
    now_d, now_v = vals[-1]
    prev_d, prev_v = vals[-(weeks + 1)]
    delta = now_v - prev_v
    # 15 points d'indice en 4 semaines ≈ 1 « σ » conventionnelle de l'indicateur
    fade, turn = fade_turn_from_delta(delta, 15.0)
    return {
        "date": now_d,
        "value": _r(now_v, 1),
        "prev_date": prev_d,
        "prev_value": _r(prev_v, 1),
        "delta": _r(delta, 1),
        "fade": fade,
        "turn": turn,
        "weeks": weeks,
    }


def avg_sent(sent_root, spec):
    group = sent_root.get(spec["group"]) or {}
    # secteurs_us keys are XLK... ; classes keys as listed
    vals, used, missing = [], [], []
    for k in spec["keys"]:
        rec = group.get(k)
        if rec is None and spec["group"] == "classes":
            rec = (sent_root.get("classes") or {}).get(k)
        if rec is None and spec["group"] == "secteurs_us":
            rec = (sent_root.get("secteurs_us") or {}).get(k)
        if rec and rec.get("value") is not None:
            vals.append(float(rec["value"]))
            used.append({"id": k, "value": rec["value"], "label": rec.get("label"), "date": rec.get("date")})
        else:
            missing.append(k)
    if not vals:
        return None, used, missing
    return _r(sum(vals) / len(vals), 1), used, missing


def weighted_score(parts):
    """parts: list of (name, value, weight). Ignore None values, renormalize."""
    ok = [(n, v, w) for n, v, w in parts if v is not None]
    if not ok:
        return None, [], [n for n, v, w in parts if v is None]
    tw = sum(w for _, _, w in ok)
    score = sum(v * w for _, v, w in ok) / tw
    detail = [{"nom": n, "value": _r(v, 1), "poids": _r(w / tw, 3)} for n, v, w in ok]
    missing = [n for n, v, w in parts if v is None]
    return _r(score, 1), detail, missing


def conf_label(gap_src, gap_tgt, s_out, s_in, missing_any):
    gaps = [g for g in (gap_src, gap_tgt) if g is not None]
    if not gaps:
        return "faible", "Écarts non calculables."
    mg = min(gaps)
    both = (s_out or 0) >= CONF_SCORE_MIN and (s_in or 0) >= CONF_SCORE_MIN
    if not missing_any and mg >= CONF_FORT_GAP and both:
        return "forte", f"Écarts nets (mini {str(_r(mg,1)).replace(chr(46), chr(44))} pts) et scores des deux côtés ≥ {CONF_SCORE_MIN}."
    if mg >= CONF_MOYEN_GAP or (mg >= CONF_MOYEN_GAP_MIN and both):
        lab = "moyenne"
        if missing_any:
            return lab, f"Écart mini {str(_r(mg,1)).replace(chr(46), chr(44))} pts, mais au moins une composante manque : confiance plafonnée à moyenne."
        return lab, f"Écart mini {str(_r(mg,1)).replace(chr(46), chr(44))} pts entre le premier et le deuxième de chaque côté."
    return "faible", f"Les scores sont proches (écart mini {str(_r(mg,1)).replace(chr(46), chr(44))} pts) : la paire est peu tranchée."


def pick_pairs(rows):
    def _k_out(r):
        return (
            -(r["sortie"] if r["sortie"] is not None else -1),
            -(r["sentiment"] if r["sentiment"] is not None else -1),
            -(r["rsi"] if r["rsi"] is not None else -1),
            r["id"],
        )

    def _k_in(r):
        return (
            -(r["entree"] if r["entree"] is not None else -1),
            (r["sentiment"] if r["sentiment"] is not None else 999),
            (r["rsi"] if r["rsi"] is not None else 999),
            r["id"],
        )

    ranked_out = sorted(rows, key=_k_out)
    ranked_in = sorted(rows, key=_k_in)
    ranked_out = [r for r in ranked_out if r["sortie"] is not None]
    ranked_in = [r for r in ranked_in if r["entree"] is not None]
    if len(ranked_out) < 2 or len(ranked_in) < 2:
        return None, None, ranked_out, ranked_in

    def first_in_not(src, ranked):
        for r in ranked:
            if r["id"] != src["id"]:
                return r
        return None

    src = ranked_out[0]
    tgt = first_in_not(src, ranked_in)
    if not tgt:
        return None, None, ranked_out, ranked_in
    primary = {"from": src, "to": tgt, "score": _r(((src["sortie"] or 0) + (tgt["entree"] or 0)) / 2, 1)}

    cands = []
    if len(ranked_out) >= 2:
        src2 = ranked_out[1]
        tgt2 = first_in_not(src2, ranked_in)
        if tgt2:
            cands.append({"from": src2, "to": tgt2, "score": _r(((src2["sortie"] or 0) + (tgt2["entree"] or 0)) / 2, 1)})
    tgt_b = None
    for r in ranked_in:
        if r["id"] != src["id"] and r["id"] != tgt["id"]:
            tgt_b = r
            break
    if tgt_b:
        cands.append({"from": src, "to": tgt_b, "score": _r(((src["sortie"] or 0) + (tgt_b["entree"] or 0)) / 2, 1)})
    alt = None
    for c in sorted(cands, key=lambda x: (-x["score"], x["from"]["id"])):
        if c["from"]["id"] != primary["from"]["id"] or c["to"]["id"] != primary["to"]["id"]:
            alt = c
            break
    return primary, alt, ranked_out, ranked_in


def slim_leg(row):
    return {
        "id": row["id"],
        "label": row["label"],
        "sortie": row["sortie"],
        "entree": row["entree"],
        "sentiment": row.get("sentiment"),
        "rsi": row.get("rsi"),
        "fade": row.get("fade"),
        "turn": row.get("turn"),
        "ret21_pct": row.get("ret21_pct"),
        "delta_ret21_pct": row.get("delta_ret21_pct"),
        "missing": row.get("missing") or [],
    }


def _fr(x, d=1, signed=False):
    if x is None:
        return "—"
    fmt = f"{{:{'+' if signed else ''}.{d}f}}"
    return fmt.format(float(x)).replace(".", ",")


def _leg_why(row, side):
    bits = [f"{row['label']} : sentiment {_fr(row.get('sentiment'))} / 100"]
    if side == "out" and row.get("fade") is not None:
        bits.append(f"essoufflement {_fr(row['fade'])}")
    if side == "in" and row.get("turn") is not None:
        mot = "retournement" if (row["turn"] or 0) >= 50 else "momentum pas encore retourné"
        bits.append(f"{mot} {_fr(row['turn'])}")
    if row.get("rsi") is not None:
        bits.append(f"RSI {_fr(row['rsi'])}")
    prix = row.get("prix") or {}
    if prix.get("mode") == "indicateur_4_semaines" and prix.get("delta_indicateur") is not None:
        bits.append(f"variation de l'indice sur 4 semaines {_fr(prix['delta_indicateur'], 1, True)} pts")
    elif row.get("ret21_pct") is not None:
        extra = ""
        if row.get("delta_ret21_pct") is not None:
            extra = f" ({_fr(row['delta_ret21_pct'], 2, True)} pt vs il y a 10 séances)"
        bits.append(f"perf. 21 j {_fr(row['ret21_pct'], 2, True)} %{extra}")
    return " ; ".join(bits)


def why_text(pair, kind):
    a, b = pair["from"], pair["to"]
    mid = _leg_why(a, "out")
    tail = _leg_why(b, "in")
    flux = "Flux ETF non disponibles, non utilisés."
    return (
        f"Score de sortie le plus élevé côté {a['label']} ({mid}). "
        f"Score d'entrée le plus élevé côté {b['label']} ({tail}). {flux}"
    )


def build_universe(name, items, sent_root, indicator):
    """items: list of {id,label,spec} where spec is CLASS_SENT-like or sector."""
    rows = []
    for it in items:
        spec = it["spec"]
        missing = []
        sent_val, used, miss_s = avg_sent(sent_root, spec) if "keys" in spec else (it.get("sentiment"), [], [])
        missing.extend([f"sentiment:{m}" for m in miss_s])
        metrics = None
        fade = turn = rsi = ret21 = dret = None
        px_date = None
        tickers_ok = []
        series_list = []
        for t in spec.get("tickers") or []:
            rec = load_cache(t)
            if rec and rec.get("ok") and rec.get("series"):
                series_list.append(rec["series"])
                tickers_ok.append({"ticker": t, "last": rec.get("last_date"), "n": rec.get("n")})
            else:
                missing.append(f"prix:{t}")
        if series_list:
            syn = ew_series(series_list) if len(series_list) > 1 else series_list[0]
            metrics = price_metrics(syn)
            if metrics:
                fade, turn = fade_turn_from_delta(metrics["delta_ret21_pct"], metrics["vol21_pct"])
                rsi = metrics["rsi"]
                ret21 = metrics["ret21_pct"]
                dret = metrics["delta_ret21_pct"]
                px_date = metrics["date"]
            else:
                missing.append("momentum_prix:historique insuffisant")
        elif spec.get("indicator"):
            ind = (indicator or {}).get(spec["indicator"]) or {}
            ser = ind.get("series") or []
            iv = indicator_fade(ser, 4)
            if iv:
                # L'indice Liquidités mesure l'appétit pour le risque (haut = cash
                # peu attrayant). Une baisse de l'indice (= plus de peur, cash plus
                # attractif) est un signal d'ENTRÉE en liquidités : on inverse le signe.
                if spec.get("indicator") == "liquidites":
                    fade, turn = fade_turn_from_delta(-(iv["delta"] or 0), 15.0)
                    iv["signe"] = "inverse (appétit pour le risque → attrait du cash)"
                else:
                    fade, turn = iv["fade"], iv["turn"]
                px_date = iv["date"]
                ret21 = None
                dret = None
                metrics = {
                    "mode": "indicateur_4_semaines",
                    "date": iv["date"],
                    "delta_indicateur": iv["delta"],
                    "prev_date": iv["prev_date"],
                    "prev_value": iv["prev_value"],
                    "fade": fade,
                    "turn": turn,
                    "signe": iv.get("signe"),
                }
            else:
                missing.append("momentum_indicateur:série trop courte")
            missing.append("rsi:pas de série de prix quotidienne")
        else:
            missing.append("prix:aucune série")

        sortie, det_s, miss_sc = weighted_score([
            ("sentiment élevé", sent_val, 0.40),
            ("essoufflement du momentum", fade, 0.30),
            ("RSI élevé", rsi, 0.30),
        ])
        entree, det_e, miss_ec = weighted_score([
            ("sentiment bas", None if sent_val is None else _r(100 - sent_val, 1), 0.40),
            ("retournement du momentum", turn, 0.30),
            ("RSI bas", None if rsi is None else _r(100 - rsi, 1), 0.30),
        ])
        rows.append({
            "id": it["id"],
            "label": it["label"],
            "sentiment": sent_val,
            "sentiment_detail": used,
            "sentiment_note": spec.get("sentiment_note"),
            "rsi": rsi,
            "fade": fade,
            "turn": turn,
            "ret21_pct": ret21,
            "delta_ret21_pct": dret,
            "prix": metrics,
            "tickers_ok": tickers_ok,
            "date_prix": px_date,
            "sortie": sortie,
            "entree": entree,
            "sortie_detail": det_s,
            "entree_detail": det_e,
            "missing": sorted(set(missing + [f"score:{m}" for m in (miss_sc + miss_ec)])),
        })
    return rows


def pack_pair(pair, alt_prefix=""):
    if not pair:
        return None
    return {
        "from_id": pair["from"]["id"],
        "from_label": pair["from"]["label"],
        "to_id": pair["to"]["id"],
        "to_label": pair["to"]["label"],
        "affichage": f"{pair['from']['label']} → {pair['to']['label']}",
        "score_combine": pair["score"],
        "from": slim_leg(pair["from"]),
        "to": slim_leg(pair["to"]),
        "pourquoi": why_text(pair, "primary"),
    }


def analyse(rows, titre):
    primary, alt, ranked_out, ranked_in = pick_pairs(rows)
    if not primary:
        return {
            "ok": False,
            "titre": titre,
            "erreur": "Données insuffisantes pour classer une paire (il faut au moins deux scores de sortie et d'entrée).",
            "lignes": rows,
        }
    gap_src = None
    if len(ranked_out) >= 2:
        gap_src = _r(ranked_out[0]["sortie"] - ranked_out[1]["sortie"], 1)
    gap_tgt = None
    # gap on the entry side among targets different from primary source? use raw 1st vs 2nd entry overall
    if len(ranked_in) >= 2:
        gap_tgt = _r(ranked_in[0]["entree"] - ranked_in[1]["entree"], 1)
    missing_any = bool((primary["from"].get("missing") or []) or (primary["to"].get("missing") or []))
    conf, conf_why = conf_label(gap_src, gap_tgt, primary["from"]["sortie"], primary["to"]["entree"], missing_any)
    p = pack_pair(primary)
    p["confiance"] = conf
    p["confiance_detail"] = conf_why
    p["ecart_sortie_pts"] = gap_src
    p["ecart_entree_pts"] = gap_tgt
    a = pack_pair(alt) if alt else None
    return {
        "ok": True,
        "titre": titre,
        "paire": p,
        "alternative": a,
        "classement_sortie": [{"id": r["id"], "label": r["label"], "sortie": r["sortie"]} for r in ranked_out],
        "classement_entree": [{"id": r["id"], "label": r["label"], "entree": r["entree"]} for r in ranked_in],
        "lignes": rows,
    }


def main():
    now = datetime.now(PARIS)
    sent_path = ROOT / "data" / "sentiment_secteurs.json"
    ind_path = ROOT / "data" / "indicateur.json"
    if not sent_path.exists():
        raise SystemExit("data/sentiment_secteurs.json manquant")
    sent_root = json.loads(sent_path.read_text())
    indicator = json.loads(ind_path.read_text()) if ind_path.exists() else {}

    class_items = [
        {"id": k, "label": v["label"], "spec": v}
        for k, v in CLASS_SENT.items()
    ]
    class_rows = build_universe("classes", class_items, sent_root, indicator)
    classes = analyse(class_rows, "Rotation entre classes d'actifs")

    sec_items = []
    for sym, fr in US_SECTORS:
        sec_items.append({
            "id": sym,
            "label": fr,
            "spec": {
                "keys": [sym],
                "group": "secteurs_us",
                "tickers": [sym],
                "sentiment_note": f"Sentiment APEX du secteur US {fr} ({sym}).",
            },
        })
    sec_rows = build_universe("secteurs", sec_items, sent_root, indicator)
    secteurs = analyse(sec_rows, "Rotation entre secteurs d'actions US")

    affichage = None
    if classes.get("ok"):
        p = classes["paire"]
        affichage = {
            "ligne": f"{p['affichage']} · confiance {p['confiance']}",
            "from_label": p["from_label"],
            "to_label": p["to_label"],
            "confiance": p["confiance"],
            "infobulle": p["pourquoi"],
        }
        if secteurs.get("ok"):
            sp = secteurs["paire"]
            affichage["secteurs"] = {
                "ligne": f"{sp['affichage']} · confiance {sp['confiance']}",
                "from_label": sp["from_label"],
                "to_label": sp["to_label"],
                "confiance": sp["confiance"],
                "infobulle": sp["pourquoi"],
            }

    out = {
        "titre": "Rotation de capitaux la plus probable",
        "updated": now.strftime("%Y-%m-%d %H:%M"),
        "updated_tz": "Europe/Paris",
        "ok": bool(classes.get("ok")),
        "affichage": affichage,
        "classes": classes,
        "secteurs_actions_us": secteurs,
        "flux_etf": {
            "disponibles": False,
            "note": "Aucune série de flux ETF n'est enregistrée sur le site. Les flux ne sont pas inventés et ne pèsent pas dans les scores.",
        },
        "methode": (
            "Score de sortie = 40 % sentiment élevé + 30 % essoufflement du momentum 21 j "
            "(variation vs il y a 10 séances, normalisée par la volatilité) + 30 % RSI 14. "
            "Score d'entrée = 40 % sentiment bas + 30 % retournement du momentum + 30 % RSI bas. "
            "Paire = plus forte sortie → plus forte entrée distincte. "
            "Flux ETF absents, non utilisés. Aucune donnée inventée."
        ),
        "sources": [
            {"nom": "data/sentiment_secteurs.json", "role": "Sentiments APEX par secteur US et par classe."},
            {"nom": "data/indicateur.json", "role": "Indices APEX Liquidités et Immobilier France (série hebdomadaire)."},
            {"nom": "data/sentiment_cache (Yahoo Finance)", "role": "Clôtures quotidiennes des ETF et contrats pour RSI et momentum."},
            {"nom": "alternative.me (via sentiment_secteurs)", "role": "Sentiment officiel Crypto Fear & Greed."},
        ],
        "avertissement": (
            "Lecture statistique interne, pas un conseil ni un ordre. "
            "Elle ne dit pas qu'une rotation aura lieu, seulement quelle paire est la plus cohérente "
            "avec le sentiment et le momentum disponibles. Aucun rendement n'est promis."
        ),
    }
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n")
    print("wrote", OUT)
    if affichage:
        print("classe", affichage["ligne"])
        if affichage.get("secteurs"):
            print("secteurs", affichage["secteurs"]["ligne"])
    else:
        print("pas de paire")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
