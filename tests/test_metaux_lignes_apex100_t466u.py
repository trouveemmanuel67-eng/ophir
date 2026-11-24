"""t466u : lignes Métaux comme les secteurs, note et barre sur 0 à 100."""
from __future__ import annotations
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PAYS = (ROOT / "src" / "pays.js").read_text(encoding="utf-8")
MET = (ROOT / "src" / "metaux.js").read_text(encoding="utf-8")
AV = (ROOT / "src" / "achatvente.js").read_text(encoding="utf-8")
SEC = (ROOT / "src" / "secteurs.js").read_text(encoding="utf-8")


def test_barre_et_fonctions_echelle_100():
    assert "function dualBarApex100" in AV
    assert "function apex100NoteHTML" in AV
    assert "0,20,40,60,80,100" in AV.replace(" ", "") or "[0,20,40,60,80,100]" in AV
    assert "/ 100" in AV
    assert "apex-block-100" in AV


def test_ptile_metaux_pas_lechelle_actions():
    fn = PAYS.split("function pTile")[1].split("function pCharts")[0]
    assert "C.cc==='met'?'APEX ACHAT 0 à 100'" in fn or 'C.cc===\'met\'?\'APEX ACHAT 0 à 100\'' in fn
    assert "APEX ACHAT 0 à 100" in fn
    assert "APEX ACHAT −50 à 250" in fn
    assert "dualBarApex100(s.apex10,s.sent,s.av,true)" in fn
    # le placeholder /250 ne s'applique plus aux lignes métaux
    met_branch = fn.split("if(C.cc==='met')")[1].split("const p=pSecOf")[0]
    assert "v2Placeholder" not in met_branch
    assert "dualBarApex100" in met_branch


def test_entete_onglet_compteurs_et_echelle_100():
    assert "srHead('Métal · contrat de référence', 100)" in MET
    assert 'data-scale="100"' in MET
    assert "cnt('Achat')" in MET
    assert "cnt('Neutre')" in MET
    assert "cnt('Vente')" in MET
    assert "sectionApexAvg('metaux')" in MET
    assert "APEX ACHAT −50 à 250" not in MET


def test_sr_head_mode_100():
    fn = SEC.split("function srHead")[1].split("function srWire")[0]
    assert "Score APEX (0 à 100" in fn
    assert "Score APEX (−50 à 250" in fn
