"""t463u : tableau Métaux précieux au format compact du tableau Actions."""
from __future__ import annotations
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
JS = (ROOT / "src" / "regles.js").read_text(encoding="utf-8")
REGLES = json.loads((ROOT / "config" / "regles.json").read_text(encoding="utf-8"))
FIBO = (ROOT / "src" / "fibo.py").read_text(encoding="utf-8")
TECH = (ROOT / "src" / "technique_apex.py").read_text(encoding="utf-8")
CORE = (ROOT / "src" / "ind_core.py").read_text(encoding="utf-8")


def _grid():
    return JS.split("function rgMetauxGrid")[1].split("function rgPageHTML")[0]


def test_format_compact_comme_actions():
    grid = _grid()
    # plus de CSS qui passe la règle à la ligne
    assert "grid-column:1/-1" not in grid
    assert "white-space:normal" not in grid
    # pas d'explications longues demandées au retrait (hors commentaires)
    visible = "\n".join(l for l in grid.splitlines() if not l.strip().startswith("/*") and "/*" not in l)
    for frag in ("contrat à terme", "Yahoo", "DBC", "clipp", "Elliott", "effet_echelle"):
        assert frag not in visible, frag
    assert "rgMetauxChamp" in grid or "intro_courte" in JS
    assert "Meilleures entrées" in grid
    assert "Portail cyan" in grid
    # une ligne d'intro, pas trois paragraphes d'effet d'échelle
    assert "effet_echelle_av" not in grid


def test_intro_courte():
    intro = REGLES["apex_metaux"]["intro_courte"]
    assert intro.count(".") <= 2
    assert "Or" in intro and "argent" in intro
    assert "−50 à 250" in intro
    assert "Yahoo" not in intro and "DBC" not in intro and "Elliott" not in intro


def test_seuils_courts_identiques_au_code():
    s = REGLES["apex_metaux"]["regles_courtes"]
    # RSI contrarien
    assert "RSI 30 = +100" in s["rsi"] and "50 = 0" in s["rsi"] and "70 = −100" in s["rsi"]
    assert "50.0 - float(rsi_val)" in TECH or "50.0 - float(rsi_val)" in CORE
    # MACD
    for frag in ("+70", "+40", "−40", "−70", "+30", "4"):
        assert frag in s["macd"], frag
    assert "base = 70.0" in TECH and "adj += 30.0" in TECH and "k >= 4" in TECH
    # CCI
    assert "≤ −100 : +80" in s["cci"] and "≤ −200 : +100" in s["cci"]
    assert "≥ +100 : −80" in s["cci"] and "≥ +200 : −100" in s["cci"]
    assert "if v<=-200: return 100.0" in CORE and "if v<=-100: return 80.0" in CORE
    # Fibo
    assert "2/3" in s["fibonacci"] and "1/3" in s["fibonacci"]
    assert "POIDS_HIST, POIDS_MVT=2.0, 1.0" in FIBO
    for frag in ("0 %", "−80", "23,6 %", "−40", "38,2 %", "50 %", "+40", "61,8 %", "+80", "78,6 %", "+100", "100 %"):
        assert frag in s["fibonacci"], frag
    # Structure
    assert "±8 %" in s["structure"] and "5 s." in s["structure"] and "±2 %" in s["structure"]
    assert "gap / 8.0" in TECH and "slope / 2.0" in TECH
    assert "+100" in s["structure"] and "−100" in s["structure"] and "+25" in s["structure"] and "−25" in s["structure"]
    assert "−2 %" in s["structure"] and "−60" in s["structure"]
    assert "−12" in s["structure"] and "−25 %" in s["structure"] and "+60" in s["structure"]
    assert "if dd>=-2: return -60.0" in CORE and "if dd>=-25: return 60.0" in CORE
    # Fond
    na = REGLES["note_apex"]
    mx = REGLES["apex_metaux"]
    assert str(int(na["fond_seuil"])) in s["fond"]
    assert str(int(mx.get("fond_pen_max") or 60)) in s["fond"]
    # GI / cyan métaux (échelle −50 à 250) assemblés depuis apex_metaux
    assert "mx.gi_seuil" in JS and "mx.cyan_note_min" in JS and "av_achat_fort" in JS
