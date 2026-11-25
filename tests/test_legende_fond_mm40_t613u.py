"""t613u : fondamental et MM40 hebdo visibles dans la légende des barres 250, comme S et H."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AV = (ROOT / "src" / "achatvente.js").read_text(encoding="utf-8")
FONDS = (ROOT / "src" / "fonds.js").read_text(encoding="utf-8")
OB = (ROOT / "src" / "obligations.js").read_text(encoding="utf-8")
SEC = (ROOT / "src" / "secteurs.js").read_text(encoding="utf-8")
TPL = (ROOT / "src" / "template.html").read_text(encoding="utf-8")
ACC = (ROOT / "src" / "acc.js").read_text(encoding="utf-8")


def test_helpers_et_barre_pilot():
    assert "function fondOf(" in AV
    assert "function mm40Of(" in AV
    assert "function attachAvgFondMm40(" in AV
    fn = AV.split("function dualBarPilot")[1].split("function apex100NoteHTML")[0]
    assert "Fondamental" in fn
    assert "MM40 hebdo" in fn
    assert "db-cur db-f" in fn
    assert "pilot-f" in fn
    assert "pilot-mm" in fn

def test_apex250_transmet_fond_et_mm40():
    fn = FONDS.split("function apex250Rec")[1].split("function listApexBar")[0]
    assert "fondOf" in fn
    assert "mm40Of" in fn


def test_segments_obligations_enrichis():
    assert "function enrichObAverages" in OB
    assert "attachAvgFondMm40" in OB
    assert "enrichObAverages();" in OB


def test_css_repere_f():
    assert ".db-cur.db-f{" in TPL
    assert "srHead" and "Fondamental" in SEC


def test_entete_et_bandeau_mentionnent_f():
    assert "Fondamental" in SEC.split("function srHead")[1].split("function srWire")[0]
    assert "curseurs AV, F, S et H" in ACC
