"""t506u / t507u : toutes les notes embarquées sur −50..250, aucune barre /100, un seul ETC par métal."""
import json, re
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent


def _blocks():
    html = (ROOT / 'index.html').read_text(encoding='utf-8')
    for m in re.finditer(r'<script id="(data[^"]*)" type="application/json">(.*?)</script>', html, flags=re.S):
        try:
            yield m.group(1), json.loads(m.group(2))
        except Exception:
            continue


def test_aucune_note_hors_250_dans_index():
    bad = []

    def walk(o, path):
        if isinstance(o, dict):
            for k in ('apex10', 'apex10_panier', 'apex10_instrument'):
                a = o.get(k)
                if isinstance(a, dict) and a.get('note') is not None and not (a.get('scale') == 250 or a.get('total_max') == 250 or a.get('v2') is True):
                    bad.append((path, k, a.get('note')))
            for k, v in o.items():
                walk(v, path + '.' + k)
        elif isinstance(o, list):
            for v in o:
                walk(v, path)
    for name, d in _blocks():
        walk(d, name)
    assert not bad, bad[:10]


def test_bandes_250_dans_build():
    src = (ROOT / 'src' / 'build.py').read_text(encoding='utf-8')
    assert "if n>=190: return 'cyan'" in src and "if n>=130: return 'vert'" in src
    assert '208' not in src


def test_plus_de_barre_100_dans_le_js():
    for f in ('achatvente.js', 'accueil.js', 'positions.js', 'fonds.js', 'tabs.js', 'obligations.js', 'acc.js'):
        js = (ROOT / 'src' / f).read_text(encoding='utf-8')
        assert '</small>/100' not in js and '/100</small>' not in js and '/ 100</small>' not in js, f


def test_un_seul_etc_par_metal():
    mt = json.loads((ROOT / 'data' / 'metaux.json').read_text(encoding='utf-8'))
    attendu = {'Or': 'XETR:8PSG', 'Argent': 'LSE:ISLN', 'Platine': 'XETR:8PSA', 'Palladium': 'XETR:8PSC'}
    for r in mt['rows']:
        ml = r['mlist']
        etcs = [it for it in [ml['head']] + ml['items'] if it and it.get('kind') == 'etc']
        assert len(etcs) == 1, r['nom']
        assert etcs[0]['tv'] == attendu[r['nom']]
        assert r['etc_retenu']['tv'] == attendu[r['nom']]


def test_contrats_energie_notes_250():
    t = json.loads((ROOT / 'data' / 'tabs_data.json').read_text(encoding='utf-8'))
    for a in t['energie']['assets']:
        assert (a.get('apex10') or {}).get('scale') == 250, a.get('tv')
    assert t['energie']['apex10']['scale'] == 250
