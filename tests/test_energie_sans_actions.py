"""L'onglet Énergie ne propose plus d'actions ni d'ETF d'actions."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INTERDITS = {'equity', 'equity_proxy', 'etf_equity'}
OK = {'futures', 'etc'}


def test_energie_uniquement_contrats_et_etc():
    en = json.loads((ROOT / 'data' / 'energie.json').read_text(encoding='utf-8'))
    kinds = {a.get('kind') for a in en['assets']}
    assert kinds <= OK, kinds
    assert not any(a.get('kind') in INTERDITS for a in en['assets'])
    assert any(a.get('kind') == 'futures' for a in en['assets'])
    assert any(a.get('kind') == 'etc' for a in en['assets'])
    # Tickers d'actions / ETF d'actions précédemment proposés dans l'onglet.
    interdits_tv = {
        'EURONEXT:TTE', 'NYSE:XOM', 'NASDAQ:ENPH', 'XETR:XDW0', 'XETR:URNU',
        'XETR:U3O8', 'NYSE:CCJ', 'NYSE:BTU', 'XETR:ZPDU', 'XETR:ENR',
    }
    present = {a.get('tv') for a in en['assets']}
    assert not (present & interdits_tv), present & interdits_tv


def test_energie_etc_disponibles_xtb():
    en = json.loads((ROOT / 'data' / 'energie.json').read_text(encoding='utf-8'))
    dispo = json.loads((ROOT / 'data' / 'disponibilites.json').read_text(encoding='utf-8'))
    etcs = [a for a in en['assets'] if a.get('kind') == 'etc']
    assert etcs
    for a in etcs:
        rec = (dispo.get('symbols') or {}).get(a['tv']) or {}
        assert rec.get('xtb') is True, a['tv']
        assert (a.get('apex10') or {}).get('scale') == 250, a['tv']


def test_energie_sentiment_matiere_pas_xle():
    from apex import sentiment as S
    S.tables.cache_clear()
    S.data.cache_clear()
    attendu = {
        'LSE:CRUD': 'energie:petrole',
        'XETR:OOEA': 'energie:brent',
        'LSE:NGAS': 'energie:gaz',
        'XETR:EGAS': 'energie:gaz',
        'NYMEX:NG1!': 'energie:gaz',
        'NYMEX:CL1!': 'energie:petrole',
        'TVC:UKOIL': 'energie:brent',
        'NYMEX:HO1!': 'energie:petrole',
        'NYMEX:RB1!': 'energie:petrole',
    }
    for tv, cle in attendu.items():
        assert S.key_for_tv(tv) == cle, (tv, S.key_for_tv(tv), cle)


def test_energie_cycles_propres():
    from apex import long250 as L
    assert L.COMMODITY_CYCLE['NYMEX:NG1!'] == 'hh'
    assert L.COMMODITY_CYCLE['LSE:NGAS'] == 'hh'
    assert L.COMMODITY_CYCLE['XETR:EGAS'] == 'ttf'
    assert L.COMMODITY_CYCLE['TVC:UKOIL'] == 'brent'
    assert L.COMMODITY_CYCLE['XETR:OOEA'] == 'brent'
    ng = L.cycle_energie('NYMEX:NG1!', 'Gaz naturel')
    assert 'DCOILWTICO' not in (ng.get('source') or '')
    assert 'Henry Hub' in (ng.get('label') or '')
    br = L.cycle_energie('TVC:UKOIL', 'Pétrole et gaz')
    assert 'Brent' in (br.get('label') or '')
    assert 'DCOILWTICO' not in (br.get('source') or '')
    eg = L.cycle_energie('XETR:EGAS', 'Gaz naturel')
    assert 'TTF' in (eg.get('label') or '')
    assert 'DCOILWTICO' not in (eg.get('source') or '')


def test_energie_etc_fond_sans_phys_ni_lignes():
    from apex import long250 as L
    _pts, _nc, elems = L.energie_etc_fond('GB00B15KXV33', 'Pétrole et gaz', 'LSE:CRUD')
    ids = [e['id'] for e in elems]
    assert 'phys' not in ids and 'lignes30' not in ids
    assert 'roll' in ids and 'suivi' in ids and 'cycle' in ids
    assert sum(e['max'] for e in elems) == 90
    # Données vérifiables : backwardation WTI au 26/11/2026.
    roll = next(e for e in elems if e['id'] == 'roll')
    assert roll['ok'] is True and roll['points'] == 10
    suivi = next(e for e in elems if e['id'] == 'suivi')
    assert suivi['valeur'] is not None
    assert (suivi.get('source') or '')


def test_energie_notes_publiees_criteres():
    en = json.loads((ROOT / 'data' / 'energie.json').read_text(encoding='utf-8'))
    sent_ok = {
        'LSE:CRUD': 'energie:petrole',
        'XETR:OOEA': 'energie:brent',
        'LSE:NGAS': 'energie:gaz',
        'XETR:EGAS': 'energie:gaz',
        'NYMEX:NG1!': 'energie:gaz',
    }
    for a in en['assets']:
        rec = a.get('apex10') or {}
        assert rec.get('scale') == 250, a.get('tv')
        fond = (rec.get('decomp') or {}).get('fondamental') or {}
        assert fond.get('max') == 90, a.get('tv')
        ids = [e.get('id') for e in (fond.get('elements') or [])]
        if a.get('kind') == 'etc':
            assert 'phys' not in ids and 'lignes30' not in ids, a.get('tv')
            assert 'roll' in ids and 'suivi' in ids, a.get('tv')
        sent = rec.get('sentiment') or {}
        if a['tv'] in sent_ok:
            assert sent.get('cle') == sent_ok[a['tv']], (a['tv'], sent)
        if a['tv'] in ('NYMEX:NG1!', 'LSE:NGAS', 'XETR:EGAS'):
            cyc = next(e for e in (fond.get('elements') or []) if e.get('id') == 'cycle')
            assert 'DCOILWTICO' not in (cyc.get('source') or ''), a['tv']
