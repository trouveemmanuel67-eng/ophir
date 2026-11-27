"""t672u : l'encadré rouge d'alerte CFD n'est plus affiché dans Mes positions."""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
JS = (ROOT / "src" / "positions.js").read_text(encoding="utf-8")
CSS = (ROOT / "src" / "template.html").read_text(encoding="utf-8")


def test_pos_cfd_alert_html_ne_rend_rien():
    m = re.search(r"function posCfdAlertHTML\(\)\{(.*?)\n\}", JS, re.S)
    assert m, "function posCfdAlertHTML manquante"
    body = m.group(1)
    assert "return '';" in body or 'return "";' in body
    assert "pos-cfd-alert" not in body
    assert "afficher_encadre" not in body
    assert "${posCfdAlertHTML()}" in JS


def test_css_encadre_rouge_retire():
    assert ".pos-cfd-alert{" not in CSS
    assert ".pos-cfd-alert {" not in CSS
    # L'encart Frais CFD n'est pas touché (le JS ne le rend plus, le style peut rester).
    assert ".pos-frais-cfd{" in CSS
