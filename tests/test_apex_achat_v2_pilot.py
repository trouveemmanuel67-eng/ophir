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
