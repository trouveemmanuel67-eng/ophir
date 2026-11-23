"""t344u : notes manquantes affichées quand elles existent déjà."""
from __future__ import annotations
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_ifrb_affiche_la_note_de_l_etf_de_reference():
    ob = json.loads((ROOT / 'data' / 'obligations.json').read_text())
    s = next(x for x in ob['segments'] if x.get('tv') == 'EURONEXT:IFRB')
    assert s.get('list') in (None, []), 'IFRB n’a pas d’alternative UCITS'
    rec = s.get('apex10') or {}
    assert rec.get('note') is not None, 'la ligne OAT doit afficher la note de l’ETF de référence'
    assert rec.get('display') not in (None, '', '–')
    assert rec['note'] == (s.get('apex10_panier') or {}).get('note')
    assert (s.get('av') or {}).get('score') is not None


def test_build_apex10_ne_efface_plus_la_note_si_liste_vide():
    src = (ROOT / 'src' / 'build_apex10.py').read_text()
    assert 'aucune alternative UCITS' in src
    assert "s['apex10'] = rec" in src


def test_positions_relisent_les_notes_deja_calculees():
    js = (ROOT / 'src' / 'positions.js').read_text()
    assert 'function apex10FromKnown' in js
    assert 'T2.energie' in js
    assert 'apex10_panier' in js


def test_phpt_reste_sans_note_serie_yahoo_peu_fiable():
    mt = json.loads((ROOT / 'data' / 'metaux.json').read_text())
    items = [it for r in mt['rows'] for it in (r.get('mlist') or {}).get('items') or []]
    phpt = next(x for x in items if x.get('tv') == 'EURONEXT:PHPT')
    assert phpt.get('skip_score') is True
    rec = phpt.get('apex10') or {}
    assert rec.get('note') is None
    assert rec.get('display') in (None, '–')


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
