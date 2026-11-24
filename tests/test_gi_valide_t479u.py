"""t479u : case Validé (✓) dans Meilleures entrées, mémoire locale par symbole."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
JS = (ROOT / "src" / "good_invest.js").read_text(encoding="utf-8")
CSS = (ROOT / "src" / "template.html").read_text(encoding="utf-8")


def test_valide_localstorage_et_lien():
    assert "const GI_VALIDE_KEY='apex-gi-valide'" in JS
    assert "function giSetValide" in JS
    assert "function giIsValide" in JS
    assert "giSetValide(tv, !giIsValide(tv))" in JS
    assert "Validés (${nVal})" in JS or 'Validés (${nVal})' in JS
    assert "gi-valides-link" in JS and "gi-valides-link" in CSS
    assert "class=\"gi-valid" in JS or "class=\"gi-valid${" in JS
    # clé = symbole TradingView complet (it.tv)
    assert "giSetValide(tv" in JS
    # les titres validés sortent de la liste principale ; le compteur suit list.length
    assert "all.filter(it=>!giIsValide(it.tv, valides))" in JS
    assert "const n=list.length" in JS


def test_valide_meme_taille_que_ep():
    assert "width:22px" in CSS and ".gi-valid" in CSS
    blk = CSS[CSS.find(".gi-elliott,.gi-pattern,.gi-valid{"):CSS.find(".gi-elliott:hover")]
    assert "width:22px" in blk and "height:22px" in blk
