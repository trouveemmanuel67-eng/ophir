"""t461u : métaux alignés sur les actions (Elliott retiré, RSI/MACD contrariens, CCI toujours compté)."""
from __future__ import annotations
import ast
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGLES = json.loads((ROOT / "config" / "regles.json").read_text(encoding="utf-8"))
JS = (ROOT / "src" / "regles.js").read_text(encoding="utf-8")
SCORE = (ROOT / "apex" / "score.py").read_text(encoding="utf-8")
CORE = (ROOT / "src" / "ind_core.py").read_text(encoding="utf-8")
GI = (ROOT / "apex" / "good_invest.py").read_text(encoding="utf-8")
BM = (ROOT / "src" / "build_metaux.py").read_text(encoding="utf-8")
BARS = (ROOT / "src" / "build_apex_bars.py").read_text(encoding="utf-8")
A10 = (ROOT / "src" / "build_apex10.py").read_text(encoding="utf-8")


def test_config_apex_metaux():
    mx = REGLES["apex_metaux"]
    assert mx["retirer_elliott"] is True
    assert mx["ne_pas_redistribuer_elliott"] is True
    assert mx["exclure_zone_rouge_meilleures_entrees"] is False
    assert mx["cyan_sans_elliott"] is True
    assert mx["av_rsi_macd_contrarien"] is True
    assert mx["cci_toujours_compte"] is True


def test_fiche_regles_metaux_sans_elliott():
    cls = next(c for c in REGLES["fiche_regles"]["classes"] if c["id"] == "metaux")
    for key in ("technique", "timing"):
        ids = [f["id"] for f in (cls.get(key) or {}).get("fixes") or []]
        assert "elliott" not in ids, ids
    assert "Elliott retiré" in cls["precision"] or "ne font plus partie" in cls["precision"]


def test_score_saute_elliott_sans_redistribuer():
    assert "skip_ids.add('elliott')" in SCORE
    assert "if key not in weights or key in skip_ids" in SCORE
    # le dénominateur sum_w n'est pas recalculé après le skip
    assert "sum_w = sum(weights.values())" in SCORE
    i = SCORE.find("if classe == 'metaux'")
    assert i > 0
    # cyan sans elliott pour les métaux
    assert "if classe == 'metaux'" in SCORE
    assert "conf = divergence_haussiere(divergence)" in SCORE
    assert "classe != 'metaux' and fiable" in SCORE


def test_ind_core_contrarien_optionnel():
    assert "contrarien=False" in CORE
    assert "score_rsi_contrarien" in CORE
    assert "score_macd_contrarien" in CORE
    assert "add_cci_toujours" in CORE
    assert "contrarien=True" in BM
    assert "contrarien=(it.get('src')=='metaux')" in BARS
    # les autres builders n'activent pas le drapeau
    assert "contrarien=True" not in (ROOT / "src" / "build_energie.py").read_text(encoding="utf-8")
    assert "contrarien=True" not in (ROOT / "src" / "build_crypto_fiches.py").read_text(encoding="utf-8")


def test_gi_et_page_regles():
    assert "is_metaux" in GI
    assert "classe == 'metaux'" in GI
    assert "classe='metaux'" in A10
    assert "['structure','fibonacci','rsi','macd','cci']" in JS
    assert "plus d'exclusion" in JS or "plus d'exclusion" in JS
    assert "plus de condition Elliott" in JS
    assert "hors zone Elliott rouge" not in JS.split("function rgMetauxGrid")[1].split("function rgPageHTML")[0]
