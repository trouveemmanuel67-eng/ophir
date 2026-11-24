"""t454u : le fondamental d'un panier APEX est la moyenne des 5 premières actions, pas 0."""
from datetime import date, timedelta
from src.build_apex_achat_v2_pilot import score_asset

def _bars(n=80):
    d0 = date(2025, 1, 3)
    out = []
    px = 100.0
    for i in range(n):
        d = d0 + timedelta(days=7 * i)
        out.append({'date': d.isoformat(), 'open': px, 'high': px, 'low': px, 'close': px, 'closed': True})
    return out


def test_panier_utilise_fond_total_precalcule():
    rec = score_asset(
        {
            'kind': 'panier',
            'ticker': 'fr_com',
            'tv': 'APEX:PANIER-FR-COM',
            'nom': 'Panier test',
            'fond_total': 38,
            'fond_elems': [{'id': 'x', 'points': 38, 'moyenne_5': True}],
            'fond_mode': 'Moyenne des 5 actions affichées.',
        },
        fg={'ok': True, 'points': 30},
        closed_bars=_bars(),
    )
    assert rec['ok'] is True
    assert rec['points']['fondamental'] == 38
    assert rec['points']['fear_greed'] == 30
    assert rec['total'] == rec['points']['rsi'] + rec['points']['macd'] + rec['points']['fibonacci'] + rec['points']['cci'] + 38 + 30
    assert rec['total'] != rec['points']['rsi'] + rec['points']['macd'] + rec['points']['fibonacci'] + rec['points']['cci'] + 30
    assert 'Fond +38' in rec['ligne'] or 'Fond 38' in rec['ligne']


def test_action_sans_ratios_reste_fond_0():
    rec = score_asset(
        {'kind': 'action', 'ticker': 'TEST.PA', 'tv': 'EURONEXT:TEST', 'nom': 'Test', 'm': {}},
        fg={'ok': True, 'points': 30},
        closed_bars=_bars(),
    )
    assert rec['ok'] is True
    assert rec['points']['fondamental'] == 0


def test_panier_france_communication_dans_les_json():
    import json
    from pathlib import Path
    root = Path(__file__).resolve().parents[1]
    for name in ('data/apex_achat_v2_pilot.json', 'data/apex_achat_v2_site.json',
                 'data/apex_achat_v2_scores_full.json'):
        d = json.loads((root / name).read_text())
        p = d['pilotes']['fr_com']
        etf = p['etf']
        acts = [a for a in p['actions'] if a.get('ok')][:5]
        moy = round(sum((a.get('points') or {}).get('fondamental') or 0 for a in acts) / len(acts))
        assert etf['kind'] == 'panier'
        assert etf['points']['fondamental'] == moy
        assert moy == 38
        assert etf['total'] == 78
        assert etf['points']['total'] == 78
        # les actions elles-mêmes n'ont pas été recalculées
        by_t = {a.get('ticker'): (a.get('points') or {}).get('total') for a in p['actions']}
        assert by_t.get('MMT.PA') == 140
        assert by_t.get('ETL.PA') == 130
        assert by_t.get('ORA.PA') == 110


def test_etf_usa_communication_inchange():
    import json
    from pathlib import Path
    d = json.loads((Path(__file__).resolve().parents[1] / 'data/apex_achat_v2_pilot.json').read_text())
    etf = d['pilotes']['XLC']['etf']
    assert etf['kind'] == 'etf'
    assert etf['total'] == 140
    assert etf['points']['fondamental'] == 80
