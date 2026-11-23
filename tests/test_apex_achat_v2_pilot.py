import json, sys
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
import build_apex_achat_v2_pilot as P

def test_fg_tranches():
    assert P.fg_points(50) == 0
    assert P.fg_points(40) == 10
    assert P.fg_points(39.9) == 10
    assert P.fg_points(30) == 20
    assert P.fg_points(17.7) == 30
    assert P.fg_points(10) == 40
    assert P.fg_points(0) == 50
    assert P.fg_points(60) == -10
    assert P.fg_points(100) == -50
    assert P.fg_points(55) == 0  # écart 5, tranche non entière

def test_fibo_sous_x():
    # r = retracement depuis le haut
    assert P.fibo_points(0.20)[0] == 0
    assert P.fibo_points(0.382)[0] == 10
    assert P.fibo_points(0.50)[0] == 10
    assert P.fibo_points(0.618)[0] == 20
    assert P.fibo_points(0.786)[0] == 30
    assert P.fibo_points(1.0)[0] == 30

def test_pilot_file_communication_only():
    p = ROOT / 'data' / 'apex_achat_v2_pilot.json'
    assert p.exists()
    d = json.loads(p.read_text())
    assert d['pilot'] is True
    assert d['secteur_sym'] == 'XLC'
    assert d['etf']['tv'] == 'XETR:ZPDK'
    assert len(d['actions']) == 5
    assert d['fear_greed']['ok'] is True
    assert d['etf']['ok'] is True
    tvs = {a['tv'] for a in d['actions']}
    assert tvs == {'NASDAQ:APP', 'NYSE:RDDT', 'NASDAQ:META', 'NASDAQ:NFLX', 'NASDAQ:GOOGL'}
    # totaux cohérents
    for rec in [d['etf']] + d['actions']:
        pts = rec['points']
        expected = (pts['rsi'] + pts['macd'] + pts['fibonacci'] + pts['elliott']
                    + pts['cci'] + pts['fondamental'] + (pts['fear_greed'] or 0))
        assert rec['total'] == expected == pts['total']
        assert rec['total_min'] == -50 and rec['total_max'] == 270
    # le fichier secteurs des autres lignes n'est pas le lieu du pilote
    # (on ne greffe pas le score sur les 10 autres secteurs)


def test_quatre_tranches_egales():
    assert P.band_of(-50) == 'rouge'
    assert P.band_of(29.9) == 'rouge'
    assert P.band_of(30) == 'jaune'
    assert P.band_of(109.9) == 'jaune'
    assert P.band_of(110) == 'vert'
    assert P.band_of(189.9) == 'vert'
    assert P.band_of(190) == 'cyan'
    assert P.band_of(270) == 'cyan'
    # totaux publiés du pilote Communication
    assert P.band_of(130) == 'vert'   # META
    assert P.band_of(140) == 'vert'   # APP
    assert P.band_of(162) == 'vert'   # ZPDK
    assert P.band_of(180) == 'vert'   # GOOGL
    assert P.band_of(200) == 'cyan'   # NFLX
    assert P.band_of(210) == 'cyan'   # RDDT


def test_elliott_apres_vague_c_app_uniquement():
    # new1 (après C, vague 1 non confirmée) compte comme zone d'entrée
    pts, det = P.elliott_points('new1')
    assert pts == 20 and det['entry'] is True
    pts, det = P.elliott_points('fin_c')
    assert pts == 20
    pts, det = P.elliott_points('a')
    assert pts == 0
    pts, det = P.elliott_points('b')
    assert pts == 0
    pts, det = P.elliott_points('bear_135')
    assert pts == 0

    p = ROOT / 'data' / 'apex_achat_v2_pilot.json'
    d = json.loads(p.read_text())
    by = {a['tv']: a for a in d['actions']}
    by['XETR:ZPDK'] = d['etf']
    # APP : C terminée vers 228,5 puis rebond, vague 1 non confirmée → +20 (était 0)
    app = by['NASDAQ:APP']
    assert app['points']['elliott'] == 20
    assert app['total'] == 160
    ell = app['detail']['elliott']
    assert ell.get('key') == 'new1'
    assert ell.get('key_officielle') == 'b'
    assert ell.get('c_fin') and abs(ell['c_fin']['prix'] - 228.5) < 1
    # inchangés
    assert by['XETR:ZPDK']['points']['elliott'] == 0 and by['XETR:ZPDK']['total'] == 162
    assert by['NYSE:RDDT']['points']['elliott'] == 0 and by['NYSE:RDDT']['total'] == 210
    assert by['NASDAQ:META']['points']['elliott'] == 0 and by['NASDAQ:META']['total'] == 130
    assert by['NASDAQ:NFLX']['points']['elliott'] == 20 and by['NASDAQ:NFLX']['total'] == 200
    assert by['NASDAQ:GOOGL']['points']['elliott'] == 20 and by['NASDAQ:GOOGL']['total'] == 180
    # tri attendu après règle C : RDDT, NFLX, GOOGL, APP, META
    order = sorted(d['actions'], key=lambda a: -a['total'])
    assert [a['tv'] for a in order] == [
        'NYSE:RDDT', 'NASDAQ:NFLX', 'NASDAQ:GOOGL', 'NASDAQ:APP', 'NASDAQ:META'
    ]
