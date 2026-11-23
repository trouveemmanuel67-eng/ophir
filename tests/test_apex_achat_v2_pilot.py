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
    assert P.band_of(110) == 'vert'   # META (borne de la tranche verte)
    assert P.band_of(140) == 'vert'   # ZPDK
    assert P.band_of(160) == 'vert'   # APP
    assert P.band_of(180) == 'vert'   # GOOGL
    assert P.band_of(190) == 'cyan'   # NFLX
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
    assert by['XETR:ZPDK']['points']['elliott'] == 0 and by['XETR:ZPDK']['total'] == 140
    assert by['NYSE:RDDT']['points']['elliott'] == 0 and by['NYSE:RDDT']['total'] == 210
    assert by['NASDAQ:META']['points']['elliott'] == 0 and by['NASDAQ:META']['total'] == 110
    assert by['NASDAQ:NFLX']['points']['elliott'] == 20 and by['NASDAQ:NFLX']['total'] == 190
    assert by['NASDAQ:GOOGL']['points']['elliott'] == 20 and by['NASDAQ:GOOGL']['total'] == 180
    # tri attendu après règle C : RDDT, NFLX, GOOGL, APP, META
    order = sorted(d['actions'], key=lambda a: -a['total'])
    assert [a['tv'] for a in order] == [
        'NYSE:RDDT', 'NASDAQ:NFLX', 'NASDAQ:GOOGL', 'NASDAQ:APP', 'NASDAQ:META'
    ]


def test_cci_stochastic_formule_daveatt():
    """Formule Pine de Daveatt (XZyG5SOx) sur une série courte, longueurs réduites."""
    import ind_core as K
    assert K.CCI_STOCH_CCI_PERIOD == 28
    assert K.CCI_STOCH_STOCH_PERIOD == 28
    assert K.CCI_STOCH_SMOOTH_K == 3 and K.CCI_STOCH_SMOOTH_D == 3
    assert K.CCI_STOCH_LINE == 'D'
    src = [10.0, 20.0, 30.0, 10.0, 5.0, 40.0, 35.0, 25.0, 15.0, 18.0]
    k, d, cci = K.cci_stochastic_kd(src, 3, 3, 2, 2)
    assert cci[2] == 100.0 and cci[3] == -100.0
    assert abs(cci[4] - (-200.0 / 3.0)) < 1e-9
    assert abs(d[6] - 69.935897) < 1e-5
    assert abs(d[-1] - 25.0) < 1e-9
    # la ligne par défaut est D, bornée 0–100
    line = K.cci_stochastic(src, 3, 3, 2, 2)
    assert line[-1] == d[-1]
    assert all(x is None or 0 <= x <= 100 for x in line)


def test_cci_stoch_et_fond_valides_sur_pilote():
    d = json.loads((ROOT / 'data' / 'apex_achat_v2_pilot.json').read_text())
    expected = {
        'XETR:ZPDK':  {'cci_pts': 0,  'cci': 24.00, 'fond': 80, 'total': 140},
        'NASDAQ:APP': {'cci_pts': 0,  'cci': 54.29, 'fond': 90, 'total': 160},
        'NYSE:RDDT':  {'cci_pts': 20, 'cci': 14.87, 'fond': 90, 'total': 210},
        'NASDAQ:META':{'cci_pts': 0,  'cci': 33.95, 'fond': 80, 'total': 110},
        'NASDAQ:NFLX':{'cci_pts': 20, 'cci': 17.60, 'fond': 70, 'total': 190},
        'NASDAQ:GOOGL':{'cci_pts': 20,'cci': 8.12,  'fond': 70, 'total': 180},
    }
    recs = [d['etf']] + d['actions']
    for rec in recs:
        exp = expected[rec['tv']]
        det = rec['detail']['cci']
        assert rec['points']['cci'] == exp['cci_pts']
        assert abs(det['valeur'] - exp['cci']) < 0.05
        assert det.get('ligne') == 'D' and det.get('cci_period') == 28 and det.get('stoch_period') == 28
        assert rec['points']['fondamental'] == exp['fond']
        assert rec['total'] == exp['total']
    # NFLX : BPA année prochaine 5,1 % ne passe plus le seuil > 10 %
    nflx = next(a for a in d['actions'] if a['tv'] == 'NASDAQ:NFLX')
    bpa = next(e for e in nflx['detail']['fondamental']['elements'] if e['id'] == 'bpa_annee_prochaine')
    assert bpa['ok'] is False and bpa['points'] == 0 and bpa['seuil'] == '> 10 %'


def test_fond_points_seuils_valides():
    # BPA > 10 %, CA > 5 %, donnée manquante = 0
    total, els = P.fond_points({
        'nd_ebitda': 1.9, 'op_margin': 16, 'fcf_margin': 11, 'roe': 16, 'current': 1.3,
        'eps_1y': 10, 'eps_0y': 10.1, 'rev_1y': 5, 'rev_0y': 5.1,
    })
    by = {e['id']: e for e in els}
    assert by['bpa_annee_prochaine']['points'] == 0   # 10 n'est pas > 10
    assert by['bpa_cette_annee']['points'] == 10
    assert by['ca_annee_prochaine']['points'] == 0   # 5 n'est pas > 5
    assert by['ca_cette_annee']['points'] == 10
    assert total == 70
    total2, els2 = P.fond_points({'nd_ebitda': None})
    assert total2 == 0
    assert all(e['points'] == 0 for e in els2)
