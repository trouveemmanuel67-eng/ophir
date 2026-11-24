"""t502u APE-16 : MACD < 0 + 4 barres rouges (signe ou pente) = +20, plafond 30."""
from __future__ import annotations
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from build_apex_achat_v2_pilot import macd_points  # noqa: E402


def _det(det, mid="histo_4_barres_rouges_sous_0"):
    return next(x for x in det if x["id"] == mid)


def test_sous_0_seul():
    pts, det = macd_points(-0.5, [0.2, 0.1, 0.3, 0.4])
    assert pts == 10
    assert _det(det)["ok"] is False and _det(det)["points"] == 0


def test_quatre_neg_sans_macd_sous_0():
    """Plus de +20 si l'histogramme est < 0 mais la ligne MACD est ≥ 0."""
    pts, det = macd_points(0.2, [-1, -1, -1, -1, -1])
    assert pts == 0
    assert _det(det)["ok"] is False and _det(det)["points"] == 0


def test_sous_0_et_quatre_hist_negatifs():
    pts, det = macd_points(-0.4, [0.5, -0.1, -0.2, -0.3, -0.4])
    assert pts == 30
    d = _det(det)
    assert d["ok"] is True and d["points"] == 20
    assert d["streak"] >= 4
    assert d["macd_sous_0"] is True


def test_sous_0_et_quatre_barres_rouges_pente():
    """Histogramme encore > 0 mais 4 baisses d'affilée : barre rouge visuelle."""
    hist = [1.0, 0.9, 0.7, 0.4, 0.1]  # 4 pentes négatives
    pts, det = macd_points(-0.2, hist)
    assert pts == 30
    d = _det(det)
    assert d["ok"] is True and d["points"] == 20
    assert d["streak_rouge_pente"] >= 4


def test_plafond_30():
    pts, _ = macd_points(-1, [-1, -2, -3, -4, -5])
    assert pts == 30


def test_aucun():
    pts, det = macd_points(0.5, [0.1, 0.2, 0.3])
    assert pts == 0
    assert _det(det)["ok"] is False
