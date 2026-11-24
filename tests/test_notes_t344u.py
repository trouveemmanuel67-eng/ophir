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


def test_phpt_note_sur_milan_puis_retire_un_seul_etc():
    """t506u : PHPT noté sur PHPT.MI (même ISIN) ; t507u : retiré de l'onglet (un seul ETC par métal)."""
    mt = json.loads((ROOT / 'data' / 'metaux.json').read_text())
    pl = next(r for r in mt['rows'] if r['nom'] == 'Platine')
    ret = {i['tv']: i for i in pl['mlist'].get('etc_retires') or []}
    assert 'EURONEXT:PHPT' in ret and ret['EURONEXT:PHPT']['note'] is not None
    assert pl['etc_retenu']['tv'] == 'XETR:8PSA'
    shown = [it.get('tv') for it in [pl['mlist']['head']] + pl['mlist']['items']]
    assert 'EURONEXT:PHPT' not in shown
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
