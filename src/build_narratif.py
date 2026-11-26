#!/usr/bin/env python3
"""Narratif APEX — validation des données et veille hebdomadaire.

Méthode de rafraîchissement (chaque semaine) :
1. `python3 src/build_narratif.py --veille`
   Collecte des titres récents (flux RSS publics +, si possible, Google Trends).
   N'écrit pas les récits : le jugement éditorial reste humain.
2. Mettre à jour `data/narratif.json` (6 à 10 récits, acteurs, sources datées,
   liens, « non trouvé » si un chiffre manque). Interdit : inventer un chiffre,
   mentionner XRP, promettre un rendement, donner un ordre.
3. `python3 src/build_narratif.py` pour valider le JSON.
4. Reconstruire le site (`python3 src/build.py`) puis pousser.

Usage :
  python3 src/build_narratif.py           # valide data/narratif.json
  python3 src/build_narratif.py --veille  # titres récents, ne touche pas au JSON
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.request
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "narratif.json"
TYPES = {"Peur", "Bulle-euphorie"}
STADES = {"naissant", "en montée", "déjà grand public"}
XRP_RE = re.compile(r"\bxrp\b", re.I)

RSS_FEEDS = [
    ("Les Échos finance", "https://www.lesechos.fr/rss/rss_finance_marches.xml"),
    ("BFM économie", "https://www.bfmtv.com/rss/economie/"),
    ("CNBC top news", "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=2000&keyword=markets"),
    ("Reuters business", "https://feeds.reuters.com/reuters/businessNews"),
    ("FT markets", "https://www.ft.com/markets?format=rss"),
]

KEYWORDS = [
    "bulle", "bubble", "récession", "recession", "crédit privé", "private credit",
    "dette", "OAT", "Fed", "rate hike", "IA", "AI", "OPEC", "pétrole", "oil glut",
    "bureaux", "commercial real estate", "short seller", "13F",
]


def fail(msg: str) -> None:
    print("ERREUR:", msg, file=sys.stderr)
    sys.exit(1)


def _has_source(obj: dict) -> bool:
    src = obj.get("source") or {}
    url = (src.get("url") or obj.get("url") or "").strip()
    return url.startswith("http://") or url.startswith("https://")


def validate(path: Path = DATA) -> dict:
    if not path.exists():
        fail(f"fichier introuvable : {path}")
    raw = path.read_text(encoding="utf-8")
    if XRP_RE.search(raw):
        fail("le mot XRP est interdit dans les données Narratif")
    try:
        d = json.loads(raw)
    except json.JSONDecodeError as e:
        fail(f"JSON invalide : {e}")
    for k in ("titre", "maj", "maj_label", "avertissement", "methode", "narratifs", "acteurs"):
        if k not in d:
            fail(f"champ manquant : {k}")
    evs = d["narratifs"]
    if not isinstance(evs, list) or not (6 <= len(evs) <= 10):
        fail("il faut 6 à 10 narratifs")
    ids = set()
    actor_ids = {a.get("id") for a in (d.get("acteurs") or []) if a.get("id")}
    for n in evs:
        nid = n.get("id") or ""
        if not nid or nid in ids:
            fail(f"id de narratif manquant ou en double : {nid!r}")
        ids.add(nid)
        if n.get("type") not in TYPES:
            fail(f"{nid}: type invalide {n.get('type')!r}")
        if n.get("stade") not in STADES:
            fail(f"{nid}: stade invalide {n.get('stade')!r}")
        if not (n.get("titre") and n.get("lecture") and n.get("risque") and n.get("arrivee_estimee")):
            fail(f"{nid}: titre, lecture, risque ou date d'arrivée manquant")
        sigs = n.get("signaux") or []
        if not sigs:
            fail(f"{nid}: aucun signal sourcé")
        for s in sigs:
            if not _has_source(s):
                fail(f"{nid}: signal sans lien source")
        for aid in n.get("acteurs") or []:
            if aid not in actor_ids:
                fail(f"{nid}: acteur inconnu {aid!r}")
    acts = d.get("acteurs") or []
    if len(acts) < 3:
        fail("au moins 3 acteurs sont attendus")
    for a in acts:
        if not a.get("id") or not a.get("nom"):
            fail("acteur sans id ou nom")
        if not (a.get("signaux_alerte") or []):
            fail(f"{a.get('id')}: signaux d'alerte manquants")
        exs = a.get("exemples") or []
        if not exs:
            fail(f"{a.get('id')}: aucun exemple passé")
        for e in exs:
            if not _has_source(e):
                fail(f"{a.get('id')}: exemple sans lien source")
    print(f"OK {len(evs)} narratifs, {len(acts)} acteurs, maj {d.get('maj_label')}")
    return d


def _fetch(url: str, timeout: int = 20) -> str:
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "APEX-narratif-veille/1.0 (lecture publique RSS)"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", "replace")


def _items_from_rss(xml: str) -> list[tuple[str, str]]:
    items = []
    for block in re.findall(r"<item\b.*?</item>", xml, flags=re.I | re.S)[:30]:
        title = re.search(r"<title>(?:<!\[CDATA\[)?(.*?)(?:\]\]>)?</title>", block, flags=re.I | re.S)
        link = re.search(r"<link>(?:<!\[CDATA\[)?(.*?)(?:\]\]>)?</link>", block, flags=re.I | re.S)
        t = re.sub(r"<[^>]+>", "", (title.group(1) if title else "")).strip()
        u = (link.group(1) if link else "").strip()
        if t:
            items.append((t, u))
    return items


def veille() -> int:
    print(f"Veille Narratif — {date.today().isoformat()}")
    print("Titres bruts pour mise à jour manuelle de data/narratif.json.")
    print("Aucun récit n'est écrit automatiquement.\n")
    kw = [k.lower() for k in KEYWORDS]
    hits = 0
    for name, url in RSS_FEEDS:
        print(f"== {name} ==")
        try:
            xml = _fetch(url)
            items = _items_from_rss(xml)
            if not items:
                print("  (aucun item lu)")
                continue
            shown = 0
            for title, link in items:
                if any(k in title.lower() for k in kw):
                    print(f"  • {title}")
                    if link:
                        print(f"    {link}")
                    shown += 1
                    hits += 1
            if not shown:
                print("  (aucun titre ne correspond aux mots-clés)")
        except Exception as e:
            print(f"  indisponible : {type(e).__name__}: {e}")
        print()
    # Google Trends, best-effort, ne fait jamais échouer la veille.
    try:
        from pytrends.request import TrendReq
        terms = ["AI bubble", "recession", "private credit", "dette France"]
        p = TrendReq(hl="fr-FR", tz=-60, timeout=(10, 20))
        p.build_payload(terms, timeframe="now 7-d", geo="")
        df = p.interest_over_time()
        if df is not None and not df.empty:
            last = df.drop(columns=[c for c in df.columns if c == "isPartial"], errors="ignore").iloc[-1]
            print("== Google Trends (7 jours, dernière valeur) ==")
            for k, v in last.items():
                print(f"  {k}: {v}")
    except Exception as e:
        print(f"== Google Trends ==\n  non disponible : {type(e).__name__}: {e}")
    print(f"\n{hits} titre(s) à examiner. Mettre à jour data/narratif.json à la main, puis valider.")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Valide ou alimente l'onglet Narratif")
    ap.add_argument("--veille", action="store_true", help="Collecte RSS / trends, n'écrit pas le JSON")
    args = ap.parse_args(argv)
    if args.veille:
        return veille()
    validate()
    return 0


if __name__ == "__main__":
    sys.exit(main())
