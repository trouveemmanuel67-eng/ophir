"""Nouveaux fonds par zone et logo triangle APEX, sans l'ancien fond doré."""
from __future__ import annotations
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TPL = (ROOT / "src" / "template.html").read_text(encoding="utf-8")
RG = (ROOT / "src" / "regles.js").read_text(encoding="utf-8")
BDG = (ROOT / "src" / "budget.js").read_text(encoding="utf-8")
TT = (ROOT / "src" / "template_trade.js").read_text(encoding="utf-8")


def test_ancien_fond_supprime():
    assert not (ROOT / "bg-ophir.jpg").exists()
    assert not (ROOT / "bg-ophir.webp").exists()
    assert "bg-ophir" not in TPL


def test_nouveaux_fonds_optimises_et_versionnes():
    for name in ("accueil", "analyse", "outils"):
        webp = ROOT / "assets" / "bg" / f"{name}.webp"
        jpg = ROOT / "assets" / "bg" / f"{name}.jpg"
        assert webp.is_file(), webp
        assert jpg.is_file(), jpg
        assert webp.stat().st_size <= 200 * 1024, webp.stat().st_size
        assert f"assets/bg/{name}.webp?v=__BUILD__" in TPL
        assert f"assets/bg/{name}.jpg?v=__BUILD__" in TPL


def test_fond_fixe_via_pseudo_pas_attachment():
    assert "background-attachment" not in TPL
    assert '#hbg{position:fixed' in TPL
    assert "background-size:cover" in TPL
    assert "background-position:center center" in TPL


def test_repartition_des_fonds():
    assert "function apexApplyBg" in TPL
    assert "body.bg-analyse #hbg" in TPL
    assert "body.bg-outils #hbg" in TPL
    assert 'body class="bg-accueil"' in TPL
    assert "apexApplyBg" in RG
    assert "apexApplyBg" in BDG
    assert "apexApplyBg" in TT
    # show() réapplique le fond après l'ouverture de Règles / Budget
    assert TPL.split("if(typeof apexApplyBg==='function') apexApplyBg();")[1].startswith("\n}")


def test_logo_header_et_icones():
    assert "apex-logo.webp?v=__BUILD__" in TPL
    assert "apex-logo@2x.webp?v=__BUILD__" in TPL
    assert "apex-logo.png?v=__BUILD__" in TPL
    assert "apex-logo@2x.png?v=__BUILD__" in TPL
    for fn in (
        "apex-logo.png",
        "apex-logo@2x.png",
        "apex-logo.webp",
        "apex-logo@2x.webp",
        "favicon.ico",
        "favicon-16.png",
        "favicon-32.png",
        "favicon.png",
        "favicon-512.png",
        "apple-touch-icon.png",
        "apex-logo-full.png",
    ):
        p = ROOT / fn
        assert p.is_file(), fn
        assert p.stat().st_size > 200, fn
