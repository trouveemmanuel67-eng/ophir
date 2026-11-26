"""Mobile et PC lisent la même source à jour : ?v= de build, meta no-cache, pas de service worker."""
from __future__ import annotations
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TPL = (ROOT / "src" / "template.html").read_text(encoding="utf-8")
POS = (ROOT / "src" / "positions.js").read_text(encoding="utf-8")
JS = (ROOT / "src" / "best_short.js").read_text(encoding="utf-8")


def test_meta_no_cache():
    assert 'http-equiv="Cache-Control"' in TPL
    assert "no-cache, no-store, must-revalidate" in TPL
    assert 'http-equiv="Pragma"' in TPL
    assert 'http-equiv="Expires"' in TPL


def test_asset_url_et_fetch_versionnes():
    assert "function apexAssetUrl" in TPL
    assert "function apexBuildVer" in TPL
    assert "data/build-version.json" in TPL
    assert "data/apex_short.json" in TPL
    assert "cache:'no-store'" in TPL
    assert "apexAssetUrl('positions.json')" in POS
    assert "apexAssetUrl('positions_revolut.json')" in POS
    assert "apexAssetUrl('positions_revolutx.json')" in POS
    assert "cache:'no-store'" in POS
    assert "gsApplyShort" in JS


def test_pas_de_service_worker():
    # Aucun SW n'est enregistré ; s'il en existait un, il est désinscrit.
    assert "serviceWorker.register" not in TPL
    assert "serviceWorker.register" not in POS
    assert "serviceWorker.register" not in JS
    assert "serviceWorker.getRegistrations" in TPL
    assert "unregister" in TPL
    assert not (ROOT / "sw.js").exists()
    assert not (ROOT / "service-worker.js").exists()
