"""t460u / t479u : boutons E, P et ✓ de Meilleures entrées, 22×22, sur une seule ligne."""
from __future__ import annotations
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CSS = (ROOT / "src" / "template.html").read_text(encoding="utf-8")
JS = (ROOT / "src" / "good_invest.js").read_text(encoding="utf-8")


def _block(start: str, end: str) -> str:
    i = CSS.find(start)
    j = CSS.find(end, i + 1) if i >= 0 else -1
    assert i >= 0, start
    return CSS[i:j if j >= 0 else i + 800]


def test_cote_a_cote_e_puis_p_puis_valide():
    assert 'class="gi-acts"' in JS
    i = JS.find('class="gi-acts"')
    chunk = JS[i:i + 1200]
    assert chunk.find(">E</button>") < chunk.find(">P</button>") < chunk.find("✓</button>")
    acts = _block(".gi-acts{", ".gi-elliott")
    assert "flex-direction:row" in acts
    assert "flex-direction:column" not in acts
    # une seule hauteur de ligne
    assert "grid-row:1" in acts
    assert ".gi-id{grid-column:2;grid-row:1;" in CSS
    assert ".gi-note{grid-column:3;grid-row:1;" in CSS
    assert ".gi-amt{grid-column:4;grid-row:1;" in CSS


def test_taille_moitie_22px():
    blk = _block(".gi-elliott,.gi-pattern,.gi-valid{", ".gi-elliott:hover")
    assert "width:22px" in blk and "height:22px" in blk
    assert "min-width:22px" in blk and "min-height:22px" in blk
    assert "width:44px" not in blk and "min-width:44px" not in blk
