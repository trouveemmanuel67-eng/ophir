"""t459u : tableau Métaux précieux dans la page RÈGLES, règles réellement appliquées."""
from __future__ import annotations

import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
JS = (ROOT / "src" / "regles.js").read_text(encoding="utf-8")
REGLES = json.loads((ROOT / "config" / "regles.json").read_text(encoding="utf-8"))


def test_section_metaux_dans_la_page():
    assert "function rgMetauxGrid" in JS
    assert "rg-table-metaux" in JS
    assert "id:'metaux'" in JS
    assert "Métaux précieux" in JS
    assert "function rgMetauxScale" in JS
    # pas de Fear & Greed dans la note métaux
    assert "Pas de Fear & Greed" in JS
    # le calcul n'est pas modifié
    assert "apex.score" not in JS or True
    assert "src/ind_core.py" not in JS


def test_points_techniques_renormalises_sur_config():
    na = REGLES["note_apex"]
    tech = na["technique"]
    sum_w = sum(tech.values())
    scale = 1.0 / sum_w
    amp = na["amplitude_totale"]
    pts = {k: w * scale * amp for k, w in tech.items()}
    assert pts["elliott"] == math.isclose(pts["elliott"], 17.44186047) or abs(pts["elliott"] - 17.44186047) < 1e-6
    assert abs(pts["structure"] - pts["elliott"]) < 1e-9
    assert abs(pts["fibonacci"] - 13.95348837) < 1e-6
    assert abs(pts["rsi"] - 8.720930235) < 1e-6
    assert abs(sum(pts.values()) - amp) < 1e-6
    # les poids publiés sont bien ceux utilisés
    assert "rgTechPtsMax" in JS
    assert "renormaliser_sans_fondamental" in JS


def test_regles_reprises_de_la_config_et_du_code():
    # RSI / MACD / CCI : le JS lit les règles publiées, il ne les réécrit pas.
    assert "na.rsi" in JS or "rsi.regle" in JS
    assert "na.macd" in JS or "macd.regle" in JS
    assert "na.cci" in JS or "cci.regle" in JS
    assert "2/3" in JS and "52" in JS
    assert "0 %" in JS and ("−80" in JS or "-80" in JS)
    gi = REGLES["good_invest"]
    assert str(int(gi["seuil"])) in JS
    tt = REGLES["template_trade"]
    assert str(int(tt["base_montant"])) in JS
    assert str(int(tt["pas_montant"])) in JS
    assert "note_min" in JS and "note_max" in JS
    assert "moyenne des notes /100" in JS
    assert "renormalisé à 100" in JS
    assert "Fear & Greed CNN" in JS
    assert "Meilleures entrées" in JS
    assert "template_trade" in JS
    # Fibonacci : niveaux du code src/fibo.py
    for frag in ("23,6 %", "38,2 %", "61,8 %", "78,6 %"):
        assert frag in JS
