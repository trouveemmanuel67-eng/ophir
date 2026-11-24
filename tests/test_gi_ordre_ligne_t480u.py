"""t480u : ticker à gauche, puis E, P, ✓ et copier, largeur de ticker fixe."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
JS = (ROOT / "src" / "good_invest.js").read_text(encoding="utf-8")
CSS = (ROOT / "src" / "template.html").read_text(encoding="utf-8")


def test_ticker_puis_boutons():
    start = JS.find("const ev=it.tv")
    end = JS.find("</article>`", start)
    chunk = JS[start:end]
    assert chunk.find('<div class="gi-id">${go}</div>') < chunk.find("${ev}")
    assert ">E</button>" in chunk and ">P</button>" in chunk and "✓</button>${cp}" in chunk
    assert "${go}${cp}" not in chunk


def test_largeur_ticker_fixe_boutons_alignes():
    assert "grid-template-columns:5.2rem auto minmax(0,1fr) auto auto" in CSS
    assert ".gi-id{grid-column:1;grid-row:1;width:5.2rem;min-width:5.2rem;max-width:5.2rem;" in CSS
    assert ".gi-acts{grid-column:2;grid-row:1;" in CSS
    assert ".gi-note{grid-column:4;grid-row:1;" in CSS
    assert ".gi-amt{grid-column:5;grid-row:1;" in CSS
    assert ".gi-acts .cp{" in CSS
