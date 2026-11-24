"""t344u : notes manquantes affichées quand elles existent déjà."""
from __future__ import annotations
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_ifrb_retire_t509():
    """t509 (24/11/2026) : IFRB introuvable chez Revolut et XTB -> segment OAT retiré (carte taux, repère de marché)."""
    ob = json.loads((ROOT / 'data' / 'obligations.json').read_text())
    assert not any(x.get('tv') == 'EURONEXT:IFRB' for x in ob['segments'])
    assert 'fr' in ob.get('removed_notes', {})


def test_build_apex10_ne_efface_plus_la_note_si_liste_vide():
    src = (ROOT / 'src' / 'build_apex10.py').read_text()
    assert 'aucune alternative UCITS' in src
    assert "s['apex10'] = rec" in src


def test_positions_relisent_les_notes_deja_calculees():
    js = (ROOT / 'src' / 'positions.js').read_text()
    assert 'function apex10FromKnown' in js
    assert 'T2.energie' in js
    assert 'apex10_panier' in js


def test_phpt_absent_du_site_t509():
    """t506u : PHPT noté sur PHPT.MI ; t508u/t509 : introuvable chez Revolut et XTB -> absent de l'onglet et des données."""
    mt = json.loads((ROOT / 'data' / 'metaux.json').read_text())
    pl = next(r for r in mt['rows'] if r['nom'] == 'Platine')
    assert pl['etc_retenu']['tv'] == 'LSE:IPLT'
    assert 'PHPT' not in json.dumps(pl)
    assert sum(1 for it in [pl['mlist']['head']] + pl['mlist']['items'] if it.get('kind') == 'etc') == 1


def test_mda_reste_sans_note_historique_court():
    pays = json.loads((ROOT / 'data' / 'pays.json').read_text())
    found = None
    for C in pays['countries']:
        for s in C.get('rows') or []:
            for r in (s.get('fond') or {}).get('top') or []:
                if r.get('tv') == 'NYSE:MDA':
                    found = r
    assert found, 'MDA doit rester dans la liste Canada Industrie'
    rec = found.get('apex10') or {}
    assert rec.get('note') is None
    first = (found.get('timing') or {}).get('first') or ''
    assert first.startswith('2026-03'), first
