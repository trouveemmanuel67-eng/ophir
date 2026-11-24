"""t481u : infobulle NOTE APEX / MONTANT sur la grille /250 (130 = 500 $ … 250 = 1 000 $)."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
JS = (ROOT / "src" / "template_trade.js").read_text(encoding="utf-8")
DATA = json.loads((ROOT / "data" / "template_trade.json").read_text(encoding="utf-8"))


def test_tableau_affiche_grille_250():
    assert "function ttLignesV2" in JS
    assert "<small>/${denom}</small>" in JS or '<small>/${denom}</small>' in JS
    assert "pilotHex" in JS
    # le barème /100 reste disponible pour les autres classes
    assert DATA["lignes"][0]["note"] == 75
    assert DATA["echelle"] == 250
    v2 = [(int(x["note"]), int(x["montant"])) for x in DATA["lignes_v2"]]
    assert v2 == [(130, 500), (154, 600), (178, 700), (202, 800), (226, 900), (250, 1000)]
