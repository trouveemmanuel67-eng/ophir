#!/usr/bin/env python3
"""Calcule les notes APEX (−50 à 250) des ETF PEA et met à jour data/pea.json.

Technique (même logique que les ETF du site) : RSI 30, MACD 30, Fibo 30, CCI 20.
MM40 hebdo à contre-courant, 0 à +30.
Sentiment maison des secteurs Europe, pondéré par la composition justETF, à
contre-courant (pas le CNN), barème officiel ±50.
Fondamental 90, critères ETF dividendes ; n.c. = 0, sans redistribution.
Cours hebdo : Yahoo Finance, semaines clôturées le vendredi.
"""
from __future__ import annotations

import json
import sys
import math
import datetime as D
import urllib.request
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

import ind_core as K
import charte as CH
import fibo as FB
from apex.score import (
    metaux_band, fmt10, round_half, fg_points,
    mm40_hebdo_points, mm40_hebdo_texte, MM40_HEBDO_MAX_AUTRES,
)
from build_apex_achat_v2_pilot import rsi_points, macd_points, fibo_points, cci_points
from yahoo_week import week_friday, friday_closed

PEA_JSON = ROOT / "data" / "pea.json"
SENT_JSON = ROOT / "data" / "sentiment_secteurs.json"
WK_DIR = ROOT / "data" / "pea_weekly"
PARIS = ZoneInfo("Europe/Paris")
TODAY = D.datetime.now(PARIS).date()

# Tickers Yahoo, par ordre de préférence (places de cotation / symboles XTB).
YAHOO = {
    "SEL": ["SEL.PA", "SELD.DE"],
    "EXSG": ["EXSG.DE"],
    "IQQA": ["IQQA.DE", "IDVY.AS"],
    "XD3E": ["DXSA.DE", "XD3E.DE"],
    "SPYW": ["SPYW.DE", "EUDV.PA"],
    "CD8": ["CD8.PA", "18M2.DE"],
    "IDVA": ["IDVA.AS"],
}

# Composition sectorielle justETF (pourcentage), résidu « Autre » / services
# aux entreprises → sentiment pays:EU. Sources : fiches justETF, sept. 2026.
SECTEURS = {
    "SEL":  {"date": "2026-09-30", "poids": {"Finance": 59.44, "Consommation discrétionnaire": 12.12, "Énergie": 9.79, "Autre": 18.65}},
    "EXSG": {"date": "2026-09-30", "poids": {"Finance": 53.64, "Énergie": 7.87, "Consommation discrétionnaire": 7.16, "Autre": 31.33}},
    "IQQA": {"date": "2026-09-30", "poids": {"Finance": 53.64, "Énergie": 7.87, "Consommation discrétionnaire": 7.16, "Autre": 31.33}},
    "XD3E": {"date": "2026-09-29", "poids": {"Finance": 42.23, "Services aux collectivités": 11.76, "Industrie": 9.08, "Consommation de base": 8.33, "Autre": 28.60}},
    "SPYW": {"date": "2026-09-30", "poids": {"Finance": 31.23, "Services aux collectivités": 14.07, "Industrie": 13.57, "Matériaux": 11.37, "Autre": 29.76}},
    "CD8":  {"date": "2026-09-24", "poids": {"Finance": 40.52, "Industrie": 16.30, "Énergie": 11.21, "Services aux collectivités": 7.61, "Autre": 24.36}},
    "IDVA": {"date": "2026-09-30", "poids": {"Finance": 53.64, "Énergie": 7.87, "Consommation discrétionnaire": 7.16, "Autre": 31.33}},
}

# Clés de sentiment_secteurs.json (secteurs_eu), plus pays:EU pour le résidu.
SENT_KEY = {
    "Finance": "XS7R",
    "Énergie": "EXH1",
    "Industrie": "DXSL",
    "Services aux collectivités": "XS6R",
    "Consommation de base": "DXSK",
    "Consommation discrétionnaire": "SPYR",
    "Matériaux": "DXSC",
    "Santé": "DXSE",
    "Technologie": "XS8R",
    "Communication": "DXSG",
    "Immobilier": "EXI5",
}

# Distributions en EUR (justETF, 26/11/2026) : 2022, 2023, 2024, 2025.
DIST_EUR = {
    "SEL":  [1.13, 0.91, 0.98, 1.33],
    "EXSG": [0.83, 0.88, 0.93, 0.96],
    "IQQA": [0.92, 1.00, 1.03, 1.04],
    "XD3E": [0.85, 0.90, 1.17, 1.37],
    "SPYW": [0.72, 0.75, 0.87, 1.12],
}

# Valorisation officielle émetteur uniquement. SPYW : fiche State Street au 24/11/2026.
# Les autres : n.c. = 0 (pas de PER/P/B émetteur vérifié ce jour).
VALO = {
    "SPYW": {"per": 11.95, "pb": 1.76, "date": "2026-11-24", "source": "Fiche State Street SPDR, caractéristiques au 24/11/2026 (PER de l'année en cours 11,95 ; P/B moyen 1,76).", "url": "https://www.ssga.com/de/de/individual/etfs/state-street-spdr-sp-euro-dividend-aristocrats-ucits-etf-dist-spyw-gy"},
}


def yahoo_chart(ticker: str) -> dict | None:
    url = (
        f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}"
        "?range=10y&interval=1wk&events=div%7Csplit&includeAdjustedClose=true"
    )
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 APEX/PEA"})
    try:
        with urllib.request.urlopen(req, timeout=25) as r:
            return json.loads(r.read().decode())
    except Exception as e:
        print("yahoo fail", ticker, type(e).__name__, e)
        return None


def closed_weeks(raw: dict):
    """Clôtures hebdomadaires confirmées (vendredi passé), ouverture du corps."""
    res = (raw.get("chart") or {}).get("result") or []
    if not res:
        return [], {}
    d = res[0]
    ts = d.get("timestamp") or []
    q = (d.get("indicators") or {}).get("quote") or [{}]
    q = q[0]
    adj = ((d.get("indicators") or {}).get("adjclose") or [{}])
    closes = (adj[0].get("adjclose") if adj else None) or q.get("close") or []
    opens = q.get("open") or [None] * len(ts)
    tzname = (d.get("meta") or {}).get("exchangeTimezoneName") or "UTC"
    tz = ZoneInfo(tzname)
    wk, op = {}, {}
    now = D.datetime.now(PARIS)
    for t, o, c in zip(ts, opens, closes):
        if c is None or c <= 0:
            continue
        loc = D.datetime.fromtimestamp(t, tz)
        fri = week_friday(loc)
        # on écrase avec la dernière valeur de la semaine (clôture)
        wk[fri] = float(c)
        if o and o > 0 and fri not in op:
            op[fri] = float(o)
    out_c, out_o, dates = [], [], []
    for fri in sorted(wk):
        if not friday_closed(fri, now=now, is_last=(fri == max(wk))):
            continue
        dates.append(fri.isoformat())
        out_c.append(wk[fri])
        out_o.append(op.get(fri))
    return dates, out_c, out_o


def sent_tables():
    d = json.loads(SENT_JSON.read_text())
    eu = d.get("secteurs_eu") or {}
    classes = d.get("classes") or {}
    return eu, classes, d


def sentiment_pondere(eid: str, eu: dict, classes: dict):
    comp = SECTEURS[eid]
    pays = classes.get("pays:EU") or {}
    num = den = 0.0
    detail = []
    for nom, w in (comp["poids"] or {}).items():
        key = SENT_KEY.get(nom)
        src = eu.get(key) if key else None
        if not src:
            src = pays
            key = "pays:EU"
        val = src.get("value")
        if val is None:
            continue
        num += float(w) * float(val)
        den += float(w)
        detail.append({
            "secteur": nom, "poids_pct": w, "cle": key,
            "valeur": src.get("value"), "label": src.get("label"),
            "date": src.get("date"),
        })
    if den <= 0:
        return None, None, detail, "sentiment introuvable"
    val = num / den
    pts = fg_points(val)
    return val, pts, detail, None


def fond_points(etf: dict):
    eid = etf["id"]
    bits = []
    total = 0

    # 1. Rendement de distribution — 20 pts. Capitalisants : n.c.
    yld = etf.get("rendement_actuel_pct")
    if yld is None:
        bits.append({"id": "rendement", "label": "Rendement de distribution", "max": 20, "points": 0, "etat": "n.c.", "raison": "ETF capitalisant, pas de rendement versé à afficher."})
    elif yld >= 5:
        bits.append({"id": "rendement", "label": "Rendement de distribution", "max": 20, "points": 20, "etat": "ok", "valeur": yld, "seuil": "≥ 5,0 %"})
        total += 20
    elif yld >= 4:
        bits.append({"id": "rendement", "label": "Rendement de distribution", "max": 20, "points": 15, "etat": "ok", "valeur": yld, "seuil": "≥ 4,0 %"})
        total += 15
    elif yld >= 3:
        bits.append({"id": "rendement", "label": "Rendement de distribution", "max": 20, "points": 10, "etat": "ok", "valeur": yld, "seuil": "≥ 3,0 %"})
        total += 10
    else:
        bits.append({"id": "rendement", "label": "Rendement de distribution", "max": 20, "points": 0, "etat": "ok", "valeur": yld, "seuil": "< 3,0 %"})

    # 2. TER — 15 pts
    ter = etf.get("ter_pct")
    if ter is None:
        bits.append({"id": "ter", "label": "Frais TER", "max": 15, "points": 0, "etat": "n.c."})
    elif ter <= 0.25:
        bits.append({"id": "ter", "label": "Frais TER", "max": 15, "points": 15, "etat": "ok", "valeur": ter, "seuil": "≤ 0,25 %"})
        total += 15
    elif ter <= 0.30:
        bits.append({"id": "ter", "label": "Frais TER", "max": 15, "points": 10, "etat": "ok", "valeur": ter, "seuil": "≤ 0,30 %"})
        total += 10
    elif ter <= 0.35:
        bits.append({"id": "ter", "label": "Frais TER", "max": 15, "points": 5, "etat": "ok", "valeur": ter, "seuil": "≤ 0,35 %"})
        total += 5
    else:
        bits.append({"id": "ter", "label": "Frais TER", "max": 15, "points": 0, "etat": "ok", "valeur": ter, "seuil": "> 0,35 %"})

    # 3. Encours — 15 pts
    aum = etf.get("encours_meur")
    if aum is None:
        bits.append({"id": "encours", "label": "Encours", "max": 15, "points": 0, "etat": "n.c."})
    elif aum >= 1000:
        bits.append({"id": "encours", "label": "Encours", "max": 15, "points": 15, "etat": "ok", "valeur": aum, "seuil": "≥ 1 000 M€"})
        total += 15
    elif aum >= 500:
        bits.append({"id": "encours", "label": "Encours", "max": 15, "points": 10, "etat": "ok", "valeur": aum, "seuil": "≥ 500 M€"})
        total += 10
    elif aum >= 200:
        bits.append({"id": "encours", "label": "Encours", "max": 15, "points": 5, "etat": "ok", "valeur": aum, "seuil": "≥ 200 M€"})
        total += 5
    else:
        bits.append({"id": "encours", "label": "Encours", "max": 15, "points": 0, "etat": "ok", "valeur": aum, "seuil": "< 200 M€"})

    # 4. Ancienneté — 15 pts
    lan = etf.get("lancement")
    ans = None
    if lan:
        d0 = D.date.fromisoformat(lan)
        ans = (TODAY - d0).days / 365.25
    if ans is None:
        bits.append({"id": "anciennete", "label": "Ancienneté", "max": 15, "points": 0, "etat": "n.c."})
    elif ans >= 15:
        bits.append({"id": "anciennete", "label": "Ancienneté", "max": 15, "points": 15, "etat": "ok", "valeur_ans": round(ans, 2), "seuil": "≥ 15 ans"})
        total += 15
    elif ans >= 10:
        bits.append({"id": "anciennete", "label": "Ancienneté", "max": 15, "points": 10, "etat": "ok", "valeur_ans": round(ans, 2), "seuil": "≥ 10 ans"})
        total += 10
    elif ans >= 5:
        bits.append({"id": "anciennete", "label": "Ancienneté", "max": 15, "points": 5, "etat": "ok", "valeur_ans": round(ans, 2), "seuil": "≥ 5 ans"})
        total += 5
    else:
        bits.append({"id": "anciennete", "label": "Ancienneté", "max": 15, "points": 0, "etat": "ok", "valeur_ans": round(ans, 2), "seuil": "< 5 ans"})

    # 5. Stabilité / croissance du dividende — 15 pts
    # Aristocrates (règle d'indice 10 ans) : 15. Distributions EUR en hausse
    # sur 2023 < 2024 < 2025 : 10. Sinon ou capitalisant : 0.
    if eid == "SPYW":
        bits.append({"id": "dividende", "label": "Stabilité du dividende", "max": 15, "points": 15, "etat": "ok", "raison": "Indice S&P Euro High Yield Dividend Aristocrats : dividendes stables ou en hausse depuis 10 ans. Distributions EUR 2023–2025 également en hausse (justETF)."})
        total += 15
    elif eid in DIST_EUR:
        hist = DIST_EUR[eid]
        # hist = 2022, 2023, 2024, 2025
        up = hist[1] < hist[2] < hist[3]
        if up:
            bits.append({"id": "dividende", "label": "Stabilité du dividende", "max": 15, "points": 10, "etat": "ok", "valeur": hist, "raison": "Distributions en EUR en hausse sur 2023, 2024 et 2025 (justETF, 26/11/2026)."})
            total += 10
        else:
            bits.append({"id": "dividende", "label": "Stabilité du dividende", "max": 15, "points": 0, "etat": "ok", "valeur": hist, "raison": "Distributions en EUR non strictement croissantes sur 2023–2025."})
    else:
        bits.append({"id": "dividende", "label": "Stabilité du dividende", "max": 15, "points": 0, "etat": "n.c.", "raison": "ETF capitalisant, pas d'historique de distribution."})

    # 6. Valorisation PER — 10 pts, uniquement source émetteur
    valo = VALO.get(eid)
    if not valo or valo.get("per") is None:
        bits.append({"id": "valorisation", "label": "Valorisation (PER)", "max": 10, "points": 0, "etat": "n.c.", "raison": "Pas de PER ou P/B d'émetteur vérifié au 26/11/2026."})
    else:
        per = valo["per"]
        if per <= 12:
            pts, seuil = 10, "PER ≤ 12"
        elif per <= 15:
            pts, seuil = 5, "PER ≤ 15"
        else:
            pts, seuil = 0, "PER > 15"
        bits.append({"id": "valorisation", "label": "Valorisation (PER)", "max": 10, "points": pts, "etat": "ok", "per": per, "pb": valo.get("pb"), "seuil": seuil, "source": valo["source"], "date": valo["date"]})
        total += pts

    return total, bits


def score_one(etf: dict, eu, classes) -> dict:
    eid = etf["id"]
    # Yahoo weekly
    raw, used = None, None
    WK_DIR.mkdir(exist_ok=True)
    for t in YAHOO[eid]:
        raw = yahoo_chart(t)
        if raw and (raw.get("chart") or {}).get("result"):
            used = t
            (WK_DIR / f"{eid}_{t.replace('.', '_')}.json").write_text(json.dumps(raw))
            break
    if not raw or not used:
        return {"note": None, "display": "–", "erreur": "série Yahoo introuvable", "scale": 250, "total": None}

    dates, closes, opens = closed_weeks(raw)
    rsi_pts = macd_pts = fibo_pts = cci_pts = 0
    rsi_val = None
    rsi_det = macd_det = fibo_det = cci_det = {}
    mm40_pts, mm40_det = 0, {"etat": "n.c.", "points": 0, "raison": "série trop courte"}

    if len(closes) >= 40:
        r = K.rsi(closes)
        rsi_val = r[-1] if r else None
        div = CH.divergence(closes, dates, r)
        rsi_pts, rsi_det = rsi_points(rsi_val, div)
        m, sg, h = K.macd_series(closes)
        macd_pts, macd_det = macd_points(m[-1] if m else None, h)
        o_use = [opens[i] if opens[i] and opens[i] > 0 else None for i in range(len(dates))]
        fib_calc = FB.analyse(o_use, closes, dates, adjust_splits=False, sym=used, combine=False)
        r_hist = fib_calc.get("r") if fib_calc.get("ok") else None
        fibo_pts, fibo_det = fibo_points(r_hist)
        _k, d_s, _raw = K.cci_stochastic_kd(closes)
        cci_val = d_s[-1] if d_s else None
        cci_pts, cci_det = cci_points(cci_val)
        mm40_pts, mm40_det = mm40_hebdo_points(closes, max_pts=MM40_HEBDO_MAX_AUTRES)
        if mm40_pts is None:
            mm40_pts = 0

    sent_val, sent_pts, sent_det, sent_err = sentiment_pondere(eid, eu, classes)
    if sent_pts is None:
        sent_pts = 0

    fond_pts, fond_bits = fond_points(etf)

    brut = int(rsi_pts + macd_pts + fibo_pts + cci_pts + sent_pts + fond_pts + (mm40_pts or 0))
    n = max(-50, min(250, int(round_half(brut))))
    band = metaux_band(n)
    parts = [
        ("RSI", rsi_pts), ("MACD", macd_pts), ("Fibo", fibo_pts), ("CCI", cci_pts),
        ("Sentiment", sent_pts), ("Fond.", fond_pts),
        ("MM40 hebdo", (mm40_det or {}).get("texte") or mm40_hebdo_texte((mm40_det or {}).get("ecart"), mm40_pts)),
    ]
    bits = []
    for lab, pts in parts:
        if lab.startswith("MM40"):
            bits.append(str(pts))
        elif pts is None:
            bits.append(f"{lab} 0")
        else:
            bits.append(f"{lab} {int(pts) if pts == int(pts) else pts}")
    texte = " · ".join(bits) + f"  →  {fmt10(n)} / 250"

    return {
        "note": n, "display": fmt10(n), "hex": band["hex"], "flag": band["flag"],
        "band": band["id"], "scale": 250, "total": n, "total_min": -50, "total_max": 250,
        "v2": True, "ligne": texte, "brut": brut,
        "technique": int(rsi_pts + macd_pts + fibo_pts + cci_pts),
        "yahoo": used, "n_semaines": len(closes), "dernier_vendredi": dates[-1] if dates else None,
        "decomp": {
            "texte": texte,
            "points": {
                "rsi": rsi_pts, "macd": macd_pts, "fibonacci": fibo_pts, "cci": cci_pts,
                "sentiment": sent_pts, "fondamental": fond_pts, "mm40": mm40_pts, "total": n,
            },
            "rsi": {"valeur": None if rsi_val is None else round(float(rsi_val), 1), "points": rsi_pts, "conditions": rsi_det},
            "macd": {"points": macd_pts, "conditions": macd_det},
            "fibonacci": {**fibo_det, "points": fibo_pts},
            "cci": {**(cci_det or {}), "points": cci_pts},
            "sentiment": {
                "valeur": None if sent_val is None else round(float(sent_val), 1),
                "points": sent_pts, "source": "sentiment maison secteurs Europe, pondéré, pas le CNN",
                "date_composition": SECTEURS[eid]["date"],
                "detail": sent_det, "erreur": sent_err,
            },
            "fondamental": {"points": fond_pts, "max": 90, "criteres": fond_bits},
            "mm40": mm40_det,
            "echelle": 250,
        },
    }


def projection_at(rate_pa: float, monthly=200, months_1=12, months_5=60):
    """Taux mensuel équivalent et annuité de fin de mois."""
    i = (1 + rate_pa) ** (1 / 12) - 1
    def fv(n):
        if abs(i) < 1e-15:
            return monthly * n
        return monthly * ((1 + i) ** n - 1) / i
    v1, v5 = monthly * months_1, monthly * months_5
    c1, c5 = fv(months_1), fv(months_5)
    return {
        "taux_pa_pct": rate_pa * 100,
        "taux_mensuel_equivalent_pct": i * 100,
        "an1": {"verse": v1, "estime": round(c1, 2), "gain": round(c1 - v1, 2), "gain_pct": round(100 * (c1 - v1) / v1, 2)},
        "an5": {"verse": v5, "estime": round(c5, 2), "gain": round(c5 - v5, 2), "gain_pct": round(100 * (c5 - v5) / v5, 2)},
    }


def main():
    pea = json.loads(PEA_JSON.read_text())
    eu, classes, sent_raw = sent_tables()
    notes = {}
    for etf in pea["etfs"]:
        rec = score_one(etf, eu, classes)
        etf["apex10"] = rec
        notes[etf["id"]] = rec.get("total")
        print(etf["id"], rec.get("total"), rec.get("ligne") or rec.get("erreur"), "yahoo", rec.get("yahoo"), "sem", rec.get("n_semaines"))

    pea["etfs"].sort(key=lambda e: ((e.get("apex10") or {}).get("total") is not None, (e.get("apex10") or {}).get("total") or -999), reverse=True)

    pea["classement"] = "note_apex"
    pea["classement_libelle"] = (
        "Classés par note APEX sur 250. Sentiment maison des secteurs Europe, lu à contre-courant "
        "(pas le Fear & Greed CNN), MM40 hebdo à contre-courant (0 à +30), RSI, MACD, Fibonacci et CCI "
        "comme les autres ETF du site. Fondamental adapté aux ETF dividendes : rendement, frais, encours, "
        "ancienneté, stabilité du dividende, valorisation si une source d'émetteur la donne. "
        "Critère manquant = 0, sans redistribution."
    )
    pea["note_legende"] = (
        "Note APEX −50 à 250 : violet < 10, rouge 10–69, orange 70–129, vert 130–189, cyan ≥ 190. "
        "Technique 110 (RSI, MACD, Fibo, CCI) + sentiment ±50 + fondamental 90 + MM40 30, total plafonné à 250."
    )
    pea["note_grille"] = {
        "echelle": "−50 à 250",
        "points": {"rsi": 30, "macd": 30, "fibonacci": 30, "cci": 20, "sentiment": 50, "fondamental": 90, "mm40": 30},
        "technique_somme": 110,
        "borne": "total ramené dans [−50, 250]",
        "regles": {
            "rsi": "RSI 14 hebdo à contre-courant : +10 si RSI < 40 ; +20 si divergence haussière hebdo ; cumulables, plafond 30.",
            "macd": "MACD 12/26/9 hebdo à contre-courant : +10 si la ligne < 0 ; +20 si ligne < 0 et 4 barres rouges d'histogramme ; cumulables, plafond 30.",
            "fibonacci": "Retracement historique des corps hebdo : ≥ 38,2 % +10 ; ≥ 61,8 % +20 ; ≥ 78,6 % +30. Non cumulables.",
            "cci": "CCI Stochastic Daveatt : +20 si la ligne D est sous 20.",
            "sentiment": "Sentiment maison des secteurs Europe (fiches justETF), pondéré par la composition, résidu = Europe (STOXX 600). Barème officiel : floor(|50 − valeur| / 10) × 10, signé, max ±50. Pas le CNN Fear & Greed.",
            "mm40": "MM40 hebdo à contre-courant, 0 à +30 : 0 point au-dessus de la MM40 ; linéaire jusqu'à −40 % ; plafonné ensuite. Moins de 40 semaines : n.c. = 0.",
            "fondamental": "90 points : rendement de distribution 20, TER 15, encours 15, ancienneté 15, stabilité du dividende 15, valorisation PER 10. n.c. = 0, sans redistribution.",
        },
        "fond_paliers": {
            "rendement": "≥ 5,0 % → 20 ; ≥ 4,0 % → 15 ; ≥ 3,0 % → 10 ; sinon ou capitalisant (n.c.) → 0. Source : rendement actuel justETF, 26/11/2026.",
            "ter": "≤ 0,25 % → 15 ; ≤ 0,30 % → 10 ; ≤ 0,35 % → 5 ; sinon → 0. Source : justETF, 26/11/2026.",
            "encours": "≥ 1 000 M€ → 15 ; ≥ 500 M€ → 10 ; ≥ 200 M€ → 5 ; sinon → 0. Source : justETF, 26/11/2026.",
            "anciennete": "≥ 15 ans → 15 ; ≥ 10 ans → 10 ; ≥ 5 ans → 5 ; sinon → 0. Date de lancement justETF, au 26/11/2026.",
            "dividende": "Indice aristocrates (10 ans de dividendes stables ou en hausse) → 15 ; distributions en EUR en hausse sur 2023, 2024 et 2025 → 10 ; capitalisant ou historique non croissant → 0. Source : justETF, 26/11/2026.",
            "valorisation": "PER émetteur ≤ 12 → 10 ; ≤ 15 → 5 ; sinon ou n.c. → 0. Seul SPYW a un PER d'émetteur vérifié (State Street, 24/11/2026).",
        },
        "cours": "Yahoo Finance, clôtures hebdomadaires confirmées (vendredi), jusqu'au 20/11/2026 inclus (semaine en cours exclue).",
        "calcule_le": TODAY.isoformat(),
        "zone": "Europe/Paris",
    }

    # Projection compacte, taux par défaut 7 %, mensuel équivalent.
    calc = projection_at(0.07)
    pea["projection"] = {
        "versement_mensuel_eur": 200,
        "versement_annuel_eur": 2400,
        "duree_ans": 5,
        "n_versements": 60,
        "total_verse_eur": 12000,
        "mode": "fin_de_mois",
        "taux_defaut_pct": 7.0,
        "taux_convention": "mensuel_equivalent",
        "mode_libelle": "Versements en fin de mois. Taux mensuel équivalent i = (1 + r)^(1/12) − 1. Valeur future d'une annuité ordinaire.",
        "avertissement": "Estimation, aucun rendement garanti, risque de perte en capital.",
        "defaut": calc,
        # Conservé pour mémoire, plus affiché.
        "justification": pea.get("projection", {}).get("justification"),
        "scenarios": pea.get("projection", {}).get("scenarios"),
    }

    pea["generated"] = TODAY.isoformat()
    PEA_JSON.write_text(json.dumps(pea, ensure_ascii=False, indent=2) + "\n")
    print("écrit", PEA_JSON)


if __name__ == "__main__":
    main()
