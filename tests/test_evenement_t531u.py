"""t531u : section ÉVÈNEMENT sous INDICE ROTATION, même style que les cartes du rail."""
from __future__ import annotations
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
JS = (ROOT / "src" / "evenements.js").read_text(encoding="utf-8")
TPL = (ROOT / "src" / "template.html").read_text(encoding="utf-8")
POS = (ROOT / "src" / "positions.js").read_text(encoding="utf-8")


def test_carte_dans_le_rail_sous_indice_rotation():
    assert "<h2>ÉVÈNEMENT</h2>" in JS
    assert 'id="evtCard"' in JS
    assert "indiceRotationCard" in JS
    assert "insertAdjacentHTML('afterend'" in JS
    assert "getElementById('mes-pos')" in JS
    assert "getElementById('irBody')" not in JS
    assert "Détection d'événements SOUS-JACENTS non médiatisés" not in JS
    assert "/*__EVTJS__*/" in TPL
    assert "evtInit" in TPL
    assert TPL.index("/*__IRJS__*/") < TPL.index("/*__EVTJS__*/")
    assert TPL.index("irInit") < TPL.index("evtInit")
    assert "ÉVÈNEMENT" in TPL
    assert "#evtCard" in TPL
    nav = TPL.split("const TABS=")[1].split("];")[0]
    assert "ÉVÈNEMENT" not in nav


def test_meme_style_que_les_autres_cartes():
    for token in (
        "#evtCard{padding:10px 10px 8px;margin-top:10px}",
        "#evtCard.pos-collapsed{padding:8px 10px}",
        "#evtCard h2{text-transform:uppercase;letter-spacing:.06em;font-size:12px;font-weight:750;margin:0;color:#fff;white-space:nowrap}",
        "#mes-pos:not(.is-expanded) #evtCard.pos-collapsed{background:#141414;border:1px solid rgba(255,255,255,.18);border-radius:999px;padding:8px 14px;box-shadow:0 4px 16px rgba(0,0,0,.35)}",
    ):
        assert token in TPL
    assert "pos-head-tot" in JS
    assert "évènement" in JS
    assert "evtListIsOpen" in POS
    assert "evtOn" in POS


def test_contenu_interne_conserve():
    for token in (
        "evenement_mesure",
        "evtCardHtml",
        "Signaux écartés cette fois",
        "3 dates ou fenêtres de déclenchement à surveiller",
        "Les données des événements n’ont pas pu être chargées",
    ):
        assert token in JS
