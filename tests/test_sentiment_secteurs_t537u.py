"""t537u : F&G sectoriel / par classe d'actifs ; barèmes LONG ±50 et SHORT ±30 inchangés."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'src')]
from apex import sentiment as S  # noqa: E402


def test_baremes_inchanges():
    assert [S.fg_long(v) for v in (0, 10.6, 19.1, 45, 50, 59.9, 66.1, 70.7, 100)] == [50, 30, 30, 0, 0, 0, -10, -20, -50]
    assert [S.fg_short(v) for v in (0, 19.1, 45, 50, 66.1, 70.7, 100)] == [-30, -18, 0, 0, 6, 12, 30]
    import build_short250 as B
    assert all(B.fg_short(v) == S.fg_short(v) for v in range(0, 101))


def test_rattachement():
    assert S.key_for_tv('NYSE:LLY') == 'us:XLV'
    assert S.key_for_tv('EURONEXT:SOP') == 'eu:XS8R'
    assert S.key_for_tv('APEX:PANIER-FR-SANTE') == 'eu:DXSE'
    assert S.key_for_tv('NYSE:AG') == 'metal:argent'
    assert S.key_for_tv('XETR:XHYG') == 'oblig:hy'
    assert S.key_for_pilote('fr_fin') == 'eu:XS7R' and S.key_for_pilote('XLK') == 'us:XLK'
    k, rec = S.resolve(None)
    assert k == 'cnn'


def test_notes_et_lignes():
    site = json.loads((ROOT / 'data' / 'apex_achat_v2_site.json').read_text(encoding='utf-8'))
    r = site['by_tv']['NYSE:LLY']
    assert r['sentiment']['cle'] == 'us:XLV'
    assert 'Sentiment Santé (XLV)' in r['ligne'] and 'F&G' not in r['ligne']
    p = r['points']
    assert r['total'] == max(-50, min(250, sum(p[k] for k in ('rsi', 'macd', 'fibonacci', 'cci', 'fondamental', 'fear_greed')) + p['hype']))
    sh = json.loads((ROOT / 'data' / 'apex_short.json').read_text(encoding='utf-8'))
    b = sh['by_tv']['NYSE:BDX']
    assert b['sentiment']['cle'] == 'us:XLV' and 'Sentiment Santé (XLV)' in b['ligne']
