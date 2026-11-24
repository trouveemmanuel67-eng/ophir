"""t474u : Mes positions affiche le ticker court + bouton copier, nom en infobulle."""
from __future__ import annotations
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
JS = (ROOT / "src" / "positions.js").read_text(encoding="utf-8")
CSS = (ROOT / "src" / "template.html").read_text(encoding="utf-8")


def test_helpers_ticker_et_copie():
    assert "function posTickerCourt(p)" in JS
    assert "function posTvCopy(p)" in JS
    assert "tick==='CASH'||tick==='PEA'" in JS
    fn = JS.split("function posTvCopy")[1].split("function ")[0]
    assert "fiche_tv" in fn


def test_ligne_sans_nom_visible():
    row = JS.split("const row=p=>{")[1].split("const tot1an=")[0]
    assert "posTickerCourt(p)" in row
    assert "ophirCopyBtn" in row or "class=\"cp\"" in row
    assert "posShortName(p)" not in row
    assert "pos-tick" not in row
    assert "title=\"${tipNom}\"" in row or "title=\"${tipNom}\"" in row
    assert "${go}${cp}" in row


def test_css_pas_delipsis_sur_ticker():
    assert ".pos-row-c .pos-id .cp" in CSS
    assert "width:22px" in CSS.split(".pos-row-c .pos-id .cp")[1][:80]
    block = CSS.split(".pos-row-c .pos-link,.pos-row-c .pos-nm")[1].split("}")[0]
    assert "flex:none" in block
    assert "text-overflow:ellipsis" not in block
