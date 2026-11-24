"""t446u bouton copier à droite du titre, t447u une seule ligne sans courtier."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GI = (ROOT / "src" / "good_invest.js").read_text(encoding="utf-8")
TABS = (ROOT / "src" / "tabs.js").read_text(encoding="utf-8")
FONDS = (ROOT / "src" / "fonds.js").read_text(encoding="utf-8")
CSS = (ROOT / "src" / "template.html").read_text(encoding="utf-8")


def test_gi_copy_a_droite_du_titre_sans_ticker_ni_type():
    assert "ophirCopyBtn" in FONDS
    assert "ophirCopyBtn(it.tv)" in GI
    assert "${go}" in GI and "${cp}" in GI and "✓</button>${cp}" in GI
    assert "gi-meta" not in GI
    assert "gi-sec" not in GI
    assert "gi-tick" not in GI
    # le ticker n'est plus affiché dans la ligne (seulement data-c / title / data-tv)
    assert "tvTag(it.tv)" not in GI


def test_gi_plus_de_courtier_une_seule_ligne():
    # plus de pastille Revolut / XTB dans le HTML des lignes
    assert "d.cls" not in GI
    assert "giDispoTxt(it.tv)" not in GI
    assert "gi-broker" not in GI
    assert "grid-template-rows:auto;" in CSS or "grid-template-rows:auto}" in CSS
    assert ".gi-acts{grid-column:2;grid-row:1;" in CSS
    assert ".gi-acts .cp{" in CSS
    # plus de deuxième rangée réservée au meta / courtier
    assert "grid-row:1 / span 2" not in CSS or CSS.count("gi-acts{grid-column:1;grid-row:1 / span 2") == 0


def test_fiches_crypto_energie_titre_plus_copie():
    assert "sr-titre" in TABS
    assert "ophirCopyBtn(s.tv)" in TABS
    # plus de sous-ligne « SYM · type » + ticker dans l'en-tête de fiche notée
    assert "<span>${s.sym} · ${s.sous}</span>${(s.tv&&typeof tvTag==='function')?tvTag(s.tv):''}" not in TABS
    assert "tvTag(s.tv)" not in TABS
    assert ".sr-titre{" in CSS
