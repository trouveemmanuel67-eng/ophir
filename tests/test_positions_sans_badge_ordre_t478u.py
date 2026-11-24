"""t478u : plus de badge ORDRE dans Mes positions ; les en_attente restent listés."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
JS = (ROOT / "src" / "positions.js").read_text(encoding="utf-8")


def test_mes_positions_sans_badge_ordre():
    # La ligne Mes positions n'appelle plus posOrdreMark ; le statut en_attente reste affiché.
    start = JS.index("function renderMesPositions")
    end = JS.index("\nfunction ", start + 1)
    row = JS[start:end]
    assert "posOrdreMark" not in row
    assert "statut==='active'||p.statut==='en_attente'" in row or "statut==='active'||p.statut==='en_attente'" in JS
    # Le helper peut rester (fiches) ; seul le panneau ne l'affiche plus.
    assert "function posOrdreMark" in JS
