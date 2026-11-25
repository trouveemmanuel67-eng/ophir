"""t484u–t502u : HYPE 90 / 45 branchée sur le calcul (comptant et cryptos)."""
from __future__ import annotations
import inspect
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
import sys
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from apex.config import regles  # noqa: E402
from apex import metaux_points as MP  # noqa: E402


def test_hype_dans_regles_metaux_et_calcul_comptant():
    mx = regles()["apex_metaux"]
    assert mx["points"]["hype"] == 90
    assert "comptant" in mx["regles_courtes"]["hype"].lower() or "Comptant" in mx["regles_courtes"]["hype"]
    assert "comptant" in mx["regles_courtes"]["hype"].lower() or "Comptant" in mx["regles_courtes"]["hype"]
    assert "ETC" in mx["regles_courtes"]["hype"]
    js = (ROOT / "src" / "regles.js").read_text(encoding="utf-8")
    grid = js.split("function rgMetauxGrid")[1].split("function rgCryptoChamp")[0]
    assert 'data-group="hype"' in grid
    assert "HYPE" in grid
    assert "hors ETC/ETF" in grid or "hors ETC" in mx["regles_courtes"]["hype"]
    src = inspect.getsource(MP.score_instrument)
    assert "hype_points_90" in src
    assert "kind == 'spot'" in src or 'kind == "spot"' in src
    assert "pts.hype" in grid or "HYPE" in grid


def test_section_crypto_regles_plus_hype():
    cx = regles()["apex_crypto"]
    assert cx["points"]["liquidite"] == 45 and cx["points"]["technique"] == 110
    assert cx["points"]["hype"] == 45
    assert cx["note_min"] == -50 and cx["note_max"] == 250
    # HYPE 45 désormais branchée (W48)
    assert "+45" in cx["regles_courtes"]["hype"] or "0–9 → +45" in cx["champ_application"]
    js = (ROOT / "src" / "regles.js").read_text(encoding="utf-8")
    assert "function rgCryptoGrid" in js
    assert "rg-table-crypto" in js
    page = js.split("function rgPageHTML")[1].split("function rgRender")[0]
    assert "rgCryptoGrid()" in page
    assert "id:'crypto'" in page or 'id:"crypto"' in page


def test_hype_affichee_et_comptee_sur_lignes_metaux():
    """La Hype du comptant est posée sur la moyenne de ligne et transmise à la barre."""
    fonds = (ROOT / "src" / "fonds.js").read_text(encoding="utf-8")
    rec = fonds.split("function apex250Rec")[1].split("function listApexBar")[0]
    assert "rec.points=pts" in rec or "rec.points = pts" in rec
    assert "rec.attention" in rec
    av = (ROOT / "src" / "achatvente.js").read_text(encoding="utf-8")
    branch = av.split("if((tabId==='metaux'")[1].split("const baked=bakedSectionApex")[0]
    assert "apex.points={hype:h}" in branch or "apex.points = {hype:h}" in branch
    assert "kind==='spot'" in branch
    sec = (ROOT / "src" / "secteurs.js").read_text(encoding="utf-8")
    head = sec.split("function srHead")[1].split("function srWire")[0]
    assert "v2==='metaux'" in head
    assert "0→+90" in head or "0→+90" in head.replace("→", "→")
    mt = json.loads((ROOT / "data" / "metaux.json").read_text(encoding="utf-8"))
    want_h = {"Or": (36, 68.8), "Argent": (54, 46.7), "Platine": (54, 40.3), "Palladium": (90, 6.4)}
    for r in mt["rows"]:
        h, att = want_h[r["nom"]]
        a = r["apex10"]
        assert a["points"]["hype"] == h
        assert a["attention"]["valeur"] == att
        items = [(r.get("mlist") or {}).get("head")] + list(((r.get("mlist") or {}).get("items") or []))
        notes = [x["apex10"]["note"] for x in items if x and (x.get("apex10") or {}).get("note") is not None]
        from apex.score import round_half
        assert a["note"] == int(round_half(sum(notes) / len(notes)))
