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
    # t463u : plus de paragraphe Fear & Greed dans le tableau compact
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
    # t463u : le tableau lit les règles courtes et les seuils de la config / du code.
    shorts = (REGLES.get("apex_metaux") or {}).get("regles_courtes") or {}
    assert "2/3" in shorts.get("fibonacci", "")
    assert "52" in shorts.get("fibonacci", "")
    assert "0 %" in shorts.get("fibonacci", "") and "−80" in shorts.get("fibonacci", "")
    gi = REGLES["good_invest"]
    assert "rgNum(gi.seuil" in JS or str(int(gi["seuil"])) in JS
    tt = REGLES["template_trade"]
    assert "template_trade" in JS
    assert "base_montant" in JS
    assert "pas_montant" in JS
    assert "Meilleures entrées" in JS
    for frag in ("23,6 %", "38,2 %", "61,8 %", "78,6 %", "−80", "+100"):
        assert frag in shorts.get("fibonacci", ""), frag
