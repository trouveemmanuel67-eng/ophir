"""La note d'un segment (moyenne de N ETF / actifs) égale la moyenne de ses membres, à ±1 près."""
import json
from pathlib import Path

from build_long250 import avg_rec, child_notes, _is_avg_rec, recalc_moyennes_doc, recalc_all_moyennes

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / 'data'


def _walk_avgs(obj, path='root'):
    if isinstance(obj, dict):
        if obj.get('mlist'):
            return
        rec = obj.get('apex10') if isinstance(obj.get('apex10'), dict) else None
        if rec and _is_avg_rec(rec):
            notes = child_notes(obj)
            if notes:
                yield obj, rec, notes, path
        for k, v in obj.items():
            if k in ('series', 'history', 'charts', 'hist', 'mlist'):
                continue
            yield from _walk_avgs(v, path + '.' + k)
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from _walk_avgs(v, f'{path}[{i}]')


def _load(name):
    return json.loads((DATA / name).read_text(encoding='utf-8'))


def test_inflation_egale_la_moyenne_des_4_etf():
    O = _load('obligations.json')
    s = next(x for x in O['segments'] if x.get('key') == 'infl')
    notes = child_notes(s)
    assert len(notes) == 4, notes
    attendu = avg_rec(notes, '', 'ETF')['note']
    assert abs(s['apex10']['note'] - attendu) <= 1
    assert s['apex10']['note'] == attendu
    assert 'moyenne de 4 ETF' in (s['apex10'].get('ligne') or '')


def test_tous_les_segments_obligataires():
    O = _load('obligations.json')
    assert len(O['segments']) >= 9
    for s in O['segments']:
        notes = child_notes(s)
        assert notes, s.get('nom')
        attendu = avg_rec(notes, '', 'ETF')['note']
        got = s['apex10']['note']
        assert abs(got - attendu) <= 1, (s.get('nom'), got, attendu, notes)


def test_toutes_les_moyennes_250_avec_enfants_locaux():
    bad = []
    for fn in ('obligations.json', 'secteurs.json', 'pays.json', 'tabs_data.json', 'crypto_fiches.json'):
        doc = _load(fn)
        for obj, rec, notes, path in _walk_avgs(doc):
            attendu = avg_rec(notes, '', 'x')['note']
            got = rec.get('note')
            if got is None or abs(float(got) - attendu) > 1:
                nom = obj.get('nom') or obj.get('name') or obj.get('tv') or obj.get('key') or path
                bad.append((fn, nom, got, attendu, notes))
    assert not bad, bad[:8]


def test_achatvente_alignee_sur_les_fiches():
    AV = _load('achatvente.json')
    S = _load('secteurs.json')
    T = _load('tabs_data.json')
    cases = [
        ('actions', child_notes(S), 'secteurs'),
        ('crypto', child_notes((T.get('crypto') or {}).get('fiches') or {}), 'cryptos'),
        ('liquidites', child_notes(((T.get('liquidites') or {}).get('fx') or {})), 'devises'),
    ]
    for key, notes, label in cases:
        rec = (AV.get(key) or {}).get('apex10')
        assert rec and notes, (key, rec, notes)
        attendu = avg_rec(notes, '', label)['note']
        assert abs(rec['note'] - attendu) <= 1, (key, rec['note'], attendu, notes)


def test_recalc_est_branche_dans_apply_sentiment():
    src = (ROOT / 'src' / 'apply_sentiment.py').read_text(encoding='utf-8')
    assert 'recalc_moyennes_doc' in src
    assert 'sync_achatvente_moyennes' in src


def test_recalc_corrige_une_moyenne_fausse():
    O = _load('obligations.json')
    s = next(x for x in O['segments'] if x.get('key') == 'infl')
    vrai = s['apex10']['note']
    s['apex10']['note'] = vrai + 40
    s['apex10']['total'] = vrai + 40
    n = recalc_moyennes_doc(O, 'obligations.json')
    assert n >= 1
    assert s['apex10']['note'] == vrai
