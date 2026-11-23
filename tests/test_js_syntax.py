"""Syntaxe JavaScript du site — le bug t334u (if sans accolades + const) doit échouer ici."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'scripts' / 'garde_fou_site.py'


def test_syntaxe_js_du_site():
    r = subprocess.run(
        [sys.executable, str(SCRIPT), '--syntax', '--root', str(ROOT)],
        cwd=str(ROOT),
    )
    assert r.returncode == 0, 'syntaxe JS invalide — ne pas publier'


def test_detecte_if_sans_accolades_suivi_d_un_const(tmp_path):
    """Le SyntaxError qui vidait le site (t334u) doit être intercepté."""
    js = (
        'function listApexBar(r){\n'
        "  if(a10&&a10.display&&a10.display!=='–')\n"
        '    const dec=apexDecomp(a10);\n'
        '    return dec;\n'
        '}\n'
    )
    (tmp_path / 'src').mkdir()
    (tmp_path / 'src' / 'fonds.js').write_text(js, encoding='utf-8')
    (tmp_path / 'index.html').write_text(
        '<script>' + js + '</script>', encoding='utf-8'
    )
    r = subprocess.run(
        [sys.executable, str(SCRIPT), '--syntax', '--root', str(tmp_path)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert r.returncode != 0
    assert 'const' in (r.stdout + r.stderr)
