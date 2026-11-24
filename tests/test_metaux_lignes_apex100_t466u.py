"""t466u / t470u : lignes Métaux comme les secteurs, note et barre sur −50 à 250."""
from __future__ import annotations
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PAYS = (ROOT / "src" / "pays.js").read_text(encoding="utf-8")
MET = (ROOT / "src" / "metaux.js").read_text(encoding="utf-8")
AV = (ROOT / "src" / "achatvente.js").read_text(encoding="utf-8")
SEC = (ROOT / "src" / "secteurs.js").read_text(encoding="utf-8")
FONDS = (ROOT / "src" / "fonds.js").read_text(encoding="utf-8")


def test_barre_pilote_disponible():
    assert "function dualBarPilot" in AV
    assert "function pilotBand" in AV


def test_ptile_metaux_echelle_250():
    fn = PAYS.split("function pTile")[1].split("function pCharts")[0]
    assert "APEX ACHAT −50 à 250" in fn
    assert "APEX ACHAT 0 à 100" not in fn
    met_branch = fn.split("if(C.cc==='met')")[1].split("const p=pSecOf")[0]
    assert "v2Placeholder" not in met_branch
    assert "dualBarPilot" in met_branch
    assert "apex250Rec" in met_branch


def test_entete_onglet_compteurs_et_echelle_250():
    assert "srHead('Métal · contrat de référence', true)" in MET
    assert 'data-scale="250"' in MET
    assert "cnt('Achat')" in MET
    assert "cnt('Neutre')" in MET
    assert "cnt('Vente')" in MET
    assert "sectionApexAvg('metaux')" in MET


def test_sr_head_mode_v2():
    fn = SEC.split("function srHead")[1].split("function srWire")[0]
    assert "Score APEX (−50 à 250" in fn
