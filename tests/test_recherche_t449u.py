"""t449u barre de recherche d'actifs."""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
JS = (ROOT / "src" / "recherche.js").read_text(encoding="utf-8")
CSS = (ROOT / "src" / "template.html").read_text(encoding="utf-8")
BUILD = (ROOT / "src" / "build.py").read_text(encoding="utf-8")
PILOT = json.loads((ROOT / "data" / "apex_achat_v2_pilot.json").read_text(encoding="utf-8"))


def test_barre_presente_et_mobile_loupe():
    assert "function apxSearchInit" in JS
    assert "Pas référencé sur APEX" in JS
    assert "aphSearchInit" not in JS
    assert "/*__SEARCHJS__*/" in CSS
    assert "/*__SEARCHJS__*/" in BUILD
    assert "src/recherche.js" in BUILD
    assert ".apx-s-tog{display:none" in CSS
    assert "@media(max-width:800px)" in CSS
    assert ".apx-s-tog{display:inline-flex}" in CSS
    assert "min-width:44px" in CSS and "min-height:44px" in CSS
    assert "apxSearchInit" in CSS  # appelé au chargement


def test_recherche_nvda_et_inconnu_via_node():
    assert "NASDAQ:NVDA" in (PILOT.get("by_tv") or {})
    script = JS + r"""
const PILOT = """ + json.dumps({"by_tv": {k: {kk: PILOT["by_tv"][k].get(kk) for kk in ("nom","ticker","tv","kind") if kk in PILOT["by_tv"][k]} for k in list(PILOT["by_tv"])[:]} }, ensure_ascii=False) + r""";
function assert(c,m){ if(!c){ console.error('FAIL', m); process.exit(1);} }
let hits = apxSearch('NVDA', 8);
assert(hits.length>=1, 'NVDA hits');
assert(hits[0].tv==='NASDAQ:NVDA' || hits.some(h=>h.tv==='NASDAQ:NVDA'||h.ticker==='NVDA'), 'NVDA trouvé: '+JSON.stringify(hits[0]));
hits = apxSearch('nvidia', 8);
assert(hits.some(h=>h.tv==='NASDAQ:NVDA'), 'recherche par nom');
hits = apxSearch('Caterpillar', 8);
assert(hits.some(h=>h.tv==='NYSE:CAT'), 'Caterpillar trouvé: '+JSON.stringify(hits));
hits = apxSearch('CAT', 8);
assert(hits.some(h=>h.tv==='NYSE:CAT'), 'CAT trouvé: '+JSON.stringify(hits));
hits = apxSearch('ZZZZNOTATICKER', 8);
assert(hits.length===0, 'inconnu absent');
assert(apxSearch('', 8).length===0, 'vide');
console.log('ok', apxIndex().length);
"""
    r = subprocess.run(["node", "-e", script], cwd=str(ROOT), capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "ok" in r.stdout
