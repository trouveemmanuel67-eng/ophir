"""Onglet NARRATIF : rail juste au-dessus d'ÉVÈNEMENT, données sourcées, affichage compact."""
from __future__ import annotations
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
JS = (ROOT / "src" / "narratif.js").read_text(encoding="utf-8")
TPL = (ROOT / "src" / "template.html").read_text(encoding="utf-8")
POS = (ROOT / "src" / "positions.js").read_text(encoding="utf-8")
BUILD = (ROOT / "src" / "build.py").read_text(encoding="utf-8")
DATA = json.loads((ROOT / "data" / "narratif.json").read_text(encoding="utf-8"))


def test_carte_dans_le_rail_au_dessus_evenement():
    assert "<h2>NARRATIF" in JS
    assert 'id="narCard"' in JS
    assert "insertAdjacentHTML('beforebegin'" in JS
    assert "getElementById('evtCard')" in JS
    assert "getElementById('mes-pos')" in JS
    assert "/*__NARJS__*/" in TPL
    assert "narInit" in TPL
    assert "__DATA_NARRATIF__" in TPL
    assert TPL.index("/*__EVTJS__*/") < TPL.index("/*__NARJS__*/")
    assert TPL.index("evtInit") < TPL.index("narInit")
    assert "NARRATIF" in TPL
    assert "#narCard" in TPL
    assert "NARRATIF et ÉVÈNEMENT" in TPL
    nav = TPL.split("const TABS=")[1].split("];")[0]
    assert "narratif" not in nav.lower()
    assert "NARRATIF" not in nav


def test_style_aligne_evenement():
    for token in (
        "#narCard{padding:10px 10px 8px;margin-top:10px}",
        "#narCard.pos-collapsed{padding:8px 10px}",
        "#narCard h2{text-transform:uppercase;letter-spacing:.06em;font-size:12px;font-weight:750;margin:0;color:#fff;white-space:nowrap}",
        "#mes-pos:not(.is-expanded) #narCard.pos-collapsed{background:#141414;border:1px solid rgba(255,255,255,.18);border-radius:999px;padding:8px 14px;box-shadow:0 4px 16px rgba(0,0,0,.35)}",
    ):
        assert token in TPL
    assert "narListIsOpen" in POS
    assert "narOn" in POS
    assert "#narCard" in TPL[TPL.find("@media(max-width:768px)"):]


def test_build_embarque_les_donnees():
    assert "data/narratif.json" in BUILD
    assert "__DATA_NARRATIF__" in BUILD
    assert "src/narratif.js" in BUILD or "narratif.js" in BUILD


def test_affichage_compact_et_ancre():
    assert "Voir le détail" in JS
    assert "nar-badge" in JS
    assert "Qui lance les narratifs" in JS
    assert "Estimations, pas des conseils" in JS
    assert "narWantedByHash" in JS
    assert "narratif" in JS
    assert "Mise à jour" in JS


def test_donnees_sourcées_sans_xrp():
    raw = (ROOT / "data" / "narratif.json").read_text(encoding="utf-8")
    assert not re.search(r"\bxrp\b", raw, re.I)
    evs = DATA["narratifs"]
    assert 6 <= len(evs) <= 10
    assert DATA.get("maj_label")
    assert DATA.get("avertissement")
    actor_ids = {a["id"] for a in DATA["acteurs"]}
    assert len(DATA["acteurs"]) >= 3
    for n in evs:
        assert n["type"] in ("Peur", "Bulle-euphorie")
        assert n["stade"] in ("naissant", "en montée", "déjà grand public")
        assert n.get("titre") and n.get("lecture") and n.get("risque")
        assert n.get("arrivee_estimee")
        assert n.get("signaux")
        for s in n["signaux"]:
            url = (s.get("source") or {}).get("url") or ""
            assert url.startswith("http"), (n["id"], s)
        for aid in n.get("acteurs") or []:
            assert aid in actor_ids
    for a in DATA["acteurs"]:
        assert a.get("signaux_alerte")
        assert a.get("exemples")
        for e in a["exemples"]:
            url = (e.get("source") or {}).get("url") or ""
            assert url.startswith("http"), (a["id"], e)
