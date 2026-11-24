"""APE-25 validé le 24/11/2026 : H actions à contre-courant −27..+27."""
import json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'src')]
import apply_attention as AA  # noqa: E402


def test_formule_h():
    assert AA.HYPE_ABS == 27
    assert AA.h_points(0) == 27 and AA.h_points(50) == 0 and AA.h_points(100) == -27
    assert AA.h_points(25) == 14 and AA.h_points(75) == -14  # 13,5 → 14 (demi éloigné de zéro)
    assert AA.h_points(None) is None
    for a in range(0, 101):
        assert AA.h_points(a) == AA._rnd((50 - a) * 0.54)


def test_h_publie_et_etf_moyenne_10():
    d = json.loads((ROOT / 'data' / 'apex_achat_v2_scores_full.json').read_text())
    neg = 0
    for sid, p in d['pilotes'].items():
        hs = [a['points'].get('hype') for a in p['actions'] if a.get('ok') and a['points'].get('hype') is not None]
        for h in hs:
            assert -27 <= h <= 27
            neg += h < 0
        e = p['etf']
        if hs and e.get('ok') and e['points'].get('hype') is not None:
            assert e['points']['hype'] == AA._rnd(sum(hs) / len(hs))
        for r in [e] + p['actions']:
            if r.get('ok'):
                P = r['points']
                brut = sum(int(P.get(k) or 0) for k in ('rsi', 'macd', 'fibonacci', 'cci', 'fondamental', 'fear_greed', 'hype'))
                assert r['total'] == max(-50, min(250, brut))
    assert neg > 0  # H retire bien des points aux titres à la mode


def test_regles_h27():
    R = json.loads((ROOT / 'config' / 'regles.json').read_text())
    for k in ('apex_achat_v2', 'apex_achat_v2_banque'):
        h = R[k]['hype']
        assert (h['min'], h['max'], h['max_affiche']) == (-27, 27, '±27')
        f = next(c for c in h['criteres'] if c['id'] == 'hype_formule')
        assert '0,54' in f['regle'] and '−27' in f['regle']
    js = (ROOT / 'src' / 'regles.js').read_text()
    assert 'Math.max(lo,sMin+hMin)' in js
