import json, sys
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
import build_apex_achat_v2_pilot as P


def base(rec):
    """Note APEX sans l'apport H (hype), pour comparer aux totaux validés avant t421u."""
    return rec['total'] - ((rec.get('points') or {}).get('hype') or 0)

def load_full():
    p = ROOT / 'data' / 'apex_achat_v2_scores_full.json'
    return json.loads(p.read_text())

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
    assert len(d['actions']) == 10
    assert d['fear_greed']['ok'] is True
    assert d['etf']['ok'] is True
    tvs = {a['tv'] for a in d['actions']}
    assert {'NASDAQ:APP', 'NYSE:RDDT', 'NASDAQ:META', 'NASDAQ:NFLX', 'NASDAQ:GOOGL'} <= tvs
    assert 'NYSE:TKO' in tvs and 'NYSE:LYV' in tvs
    for rec in [d['etf']] + d['actions']:
        pts = rec['points']
        expected = (pts['rsi'] + pts['macd'] + pts['fibonacci']
                    + pts['cci'] + pts['fondamental'] + (pts['fear_greed'] or 0)
                    + (pts.get('hype') or 0))
        assert rec['total'] == expected == pts['total']
        assert rec['total_min'] == -50 and rec['total_max'] == 250  # APE-25
        assert 'hype' in pts and (pts['hype'] is None or 0 <= pts['hype'] <= 20)
        assert 'elliott' not in pts
        assert 'Elliott' not in (rec.get('ligne') or '')
    # déploiement mondial : toutes les sections Actions sont dans pilotes
    assert 'XLF' in d['pilotes'] and 'fr_fin' in d['pilotes']
    assert set(d['secteurs_pilotes']) >= {'XLC', 'XLF', 'fr_fin'}


def test_cinq_tranches_egales():
    # APE-25 : −50 à 250, 5 tranches égales de 60 points
    assert P.SCALE_MIN == -50 and P.SCALE_MAX == 250 and P.HYPE_ABS == 20
    assert P.band_of(-50) == 'violet'
    assert P.band_of(9.9) == 'violet'
    assert P.band_of(10) == 'rouge'
    assert P.band_of(69.9) == 'rouge'
    assert P.band_of(70) == 'orange'
    assert P.band_of(129.9) == 'orange'
    assert P.band_of(130) == 'vert'
    assert P.band_of(189.9) == 'vert'
    assert P.band_of(190) == 'cyan'
    assert P.band_of(250) == 'cyan'
    import apply_attention as AA
    for t in (-50, 9, 10, 69, 70, 100, 130, 150, 190, 250):
        assert AA.band_of(t) == P.band_of(t)


def test_note_sans_elliott_sur_le_pilote_communication():
    d = load_full()
    xlc = d['pilotes']['XLC']
    by = {a['tv']: a for a in xlc['actions']}
    by['XETR:ZPDK'] = xlc['etf']
    # APE-25 : indicateurs × 0,9 (RSI/MACD/Fibo 9-18-27, CCI 18, fond 9 × 9) ; ETF : fond moyen des 10 titres
    for tv, total in {
        'NASDAQ:APP': 129, 'XETR:ZPDK': 115, 'NYSE:RDDT': 192,
        'NASDAQ:META': 102, 'NASDAQ:NFLX': 156, 'NASDAQ:GOOGL': 147,
    }.items():
        assert 'elliott' not in by[tv]['points']
        assert base(by[tv]) == total
        assert by[tv]['total_max'] == 250
        assert 'Elliott' not in (by[tv].get('ligne') or '')
    top5 = {'NYSE:RDDT', 'NASDAQ:NFLX', 'NASDAQ:GOOGL', 'NASDAQ:APP', 'NASDAQ:META'}
    order = sorted([a for a in xlc['actions'] if a['tv'] in top5], key=lambda a: -base(a))
    assert [a['tv'] for a in order] == [
        'NYSE:RDDT', 'NASDAQ:NFLX', 'NASDAQ:GOOGL', 'NASDAQ:APP', 'NASDAQ:META'
    ]
    assert len(xlc['actions']) == 10
    for a in xlc['actions']:
        assert 'elliott' not in a['points']
        assert a['total_max'] == 250


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
    d = load_full()
    d = d['pilotes']['XLC']
    expected = {
        'XETR:ZPDK':  {'cci_pts': 0,  'cci': 24.00, 'fond': 58, 'total': 115},
        'NASDAQ:APP': {'cci_pts': 0,  'cci': 54.29, 'fond': 81, 'total': 129},
        'NYSE:RDDT':  {'cci_pts': 18, 'cci': 14.87, 'fond': 81, 'total': 192},
        'NASDAQ:META':{'cci_pts': 0,  'cci': 33.95, 'fond': 72, 'total': 102},
        'NASDAQ:NFLX':{'cci_pts': 18, 'cci': 17.60, 'fond': 63, 'total': 156},
        'NASDAQ:GOOGL':{'cci_pts': 18,'cci': 8.12,  'fond': 63, 'total': 147},
    }
    recs = [d['etf']] + d['actions']
    for rec in recs:
        if rec['tv'] not in expected:
            assert rec['ok'] is True and rec['total_max'] == 250
            continue
        exp = expected[rec['tv']]
        det = rec['detail']['cci']
        assert rec['points']['cci'] == exp['cci_pts']
        assert abs(det['valeur'] - exp['cci']) < 0.05
        assert det.get('ligne') == 'D' and det.get('cci_period') == 28 and det.get('stoch_period') == 28
        assert rec['points']['fondamental'] == exp['fond']
        assert base(rec) == exp['total']
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


def test_fond_points_banque_seuils_et_manquants():
    total, els = P.fond_points({
        'roe': 11, 'roa': 1.1, 'ratio_cet1': None, 'cout_du_risque': None,
        'coefficient_exploitation': None, 'eps_0y': 11, 'eps_1y': 10,
        'rev_0y': 6, 'rev_1y': 5,
    }, P.FOND_RULES_BANQUE)
    by = {e['id']: e for e in els}
    assert by['roe']['points'] == 10
    assert by['roa']['points'] == 10
    assert by['ratio_cet1']['points'] == 0 and by['ratio_cet1']['manquant'] is True
    assert by['cout_du_risque']['points'] == 0 and by['cout_du_risque']['manquant'] is True
    assert by['coefficient_exploitation']['points'] == 0 and by['coefficient_exploitation']['manquant'] is True
    assert by['bpa_cette_annee']['points'] == 10
    assert by['bpa_annee_prochaine']['points'] == 0  # 10 n'est pas > 10
    assert by['pnb_cette_annee']['points'] == 10
    assert by['pnb_annee_prochaine']['points'] == 0  # 5 n'est pas > 5
    assert total == 40
    # sans aucune donnée : 0, rien n'est inventé
    total0, els0 = P.fond_points({}, P.FOND_RULES_BANQUE)
    assert total0 == 0 and len(els0) == 9 and all(e['manquant'] and e['points'] == 0 for e in els0)


def test_finance_usa_hors_banque_sur_le_top5():
    # MA, SCHW, V, BLK, SPGI ne sont pas des banques → règles hors banque ; XLF recalculé
    site = json.loads((ROOT / 'data' / 'apex_achat_v2_pilot.json').read_text())
    d = load_full()
    xlf = d['pilotes']['XLF']
    top5 = {'NYSE:MA', 'NYSE:SCHW', 'NYSE:V', 'NYSE:BLK', 'NYSE:SPGI'}
    tvs = {a['tv'] for a in xlf['actions']}
    assert top5 <= tvs
    assert len(xlf['actions']) == 10
    by5 = {a['tv']: a for a in xlf['actions'] if a['tv'] in top5}
    assert all(a.get('is_bank') is False for a in by5.values())
    assert all(a.get('regles') == 'apex_achat_v2' for a in by5.values())
    by = {a['tv']: a for a in xlf['actions']}
    # APE-25 (× 0,9 ; ETF : fond moyen des 10 titres)
    assert base(by['NYSE:MA']) == 102
    assert base(by['NYSE:V']) == 102
    assert base(by['NYSE:BLK']) == 102
    assert base(by['NYSE:SCHW']) == 120
    assert base(by['NYSE:SPGI']) == 84
    assert xlf['etf']['tv'] == 'XETR:ZPDF' and base(xlf['etf']) == 87
    assert base(site['by_tv']['XETR:ZPDF']) == 87
    # vraies banques présentes dans le fichier (autres pays)
    banks = [a for p in d['pilotes'].values() for a in p['actions'] if a.get('is_bank')]
    assert any(a['tv'] == 'EURONEXT:BNP' for a in banks)
    assert all(a.get('regles') == 'apex_achat_v2_banque' for a in banks)
    # CET1 et coût du risque jamais inventés
    miss = {(m['tv'], m['critere']) for m in d['manquantes'] if m.get('regles') == 'apex_achat_v2_banque'}
    for a in banks:
        assert (a['tv'], 'ratio_cet1') in miss
        assert (a['tv'], 'cout_du_risque') in miss


def test_is_bank_classification():
    from build_apex_achat_v2_world import is_bank
    assert is_bank('Banks - Diversified') and is_bank('Banks - Regional') and is_bank('Banks')
    assert is_bank('Savings Institutions')
    assert not is_bank('Insurance - Diversified')
    assert not is_bank('Credit Services')
    assert not is_bank('Asset Management')
    assert not is_bank('Capital Markets')
    assert not is_bank('Financial Data & Stock Exchanges')
