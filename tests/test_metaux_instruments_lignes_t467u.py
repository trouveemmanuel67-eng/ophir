"""t467u : instruments Métaux en lignes simples, comme les actions d'un secteur."""
from __future__ import annotations
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MET = (ROOT / "src" / "metaux.js").read_text(encoding="utf-8")
FONDS = (ROOT / "src" / "fonds.js").read_text(encoding="utf-8")


def test_mlist_lignes_pas_cartes():
    mlist = MET.split("function mList")[1].split("function renderMetaux")[0]
    assert "function mRow" in MET
    assert 'class="fl-row"' in MET
    assert "fl fl-pilot" in mlist
    assert 'class="fl-prin">principal' in MET
    assert "forceApex100:true" in MET
    assert "fl-etf" not in mlist
    assert "fl-m" not in mlist
    assert "<ol class=\"fl\">" not in mlist


def test_infos_isin_ter_en_infobulle():
    tip = MET.split("function mInstTip")[1].split("function mRow")[0]
    assert "r.isin" in tip
    assert "r.ter_note" in tip
    assert "r.kind_nom" in tip
    assert "r.currency" in tip
    row = MET.split("function mRow")[1].split("function mList")[0]
    assert "title=" in row
    assert "posBadges" in row
    assert "dispoBadge" in row
    assert "tvTag(r.tv)" in row


def test_list_apex_bar_force_100_avant_pilote():
    fn = FONDS.split("function listApexBar")[1].split("function fondQualite")[0]
    head = fn.split("const prec=")[0]
    assert "r.forceApex100" in head
    assert "dualBarApex100" in head
    assert "pilotRec" not in head
