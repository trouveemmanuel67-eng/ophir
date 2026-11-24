"""t433u + t437u–t441u : montant /250, barre compacte, en-tête, carré de position."""
from __future__ import annotations

import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GI = (ROOT / 'src' / 'good_invest.js').read_text(encoding='utf-8')
AV = (ROOT / 'src' / 'achatvente.js').read_text(encoding='utf-8')
TT = (ROOT / 'src' / 'template_trade.js').read_text(encoding='utf-8')
POS = (ROOT / 'src' / 'positions.js').read_text(encoding='utf-8')
CSS = (ROOT / 'src' / 'template.html').read_text(encoding='utf-8')
FONDS = (ROOT / 'src' / 'fonds.js').read_text(encoding='utf-8')
PAYS = (ROOT / 'src' / 'pays.js').read_text(encoding='utf-8')


def test_gi_montant_appele_pour_les_actions_v2():
    assert "montant:giMontant(r.total, sc, 'actions')" in GI
    assert "montant:null}" not in GI and "montant: null" not in GI
    assert 'function giMontant(note, scale, tab)' in GI


def test_tt_montant_null_n_affiche_pas_zero():
    assert "if(v==null||v==='') return '—';" in TT
    # Number(null) === 0 ne doit plus passer
    assert TT.find("if(v==null||v==='') return '—';") < TT.find('const n=Number(v);')


def test_bareme_v2_proportionnel_via_node():
    script = r'''
const TT = {unite:'$', lignes:[
  {note:75, montant:500},{note:80, montant:600},{note:85, montant:700},
  {note:90, montant:800},{note:95, montant:900},{note:100, montant:1000}
]};
const GI_SEUIL_V2 = 130;
'''
    start = GI.find('function giMontant(note, scale, tab){')
    end = GI.find('function giEnrich(', start)
    assert start != -1 and end != -1
    script += GI[start:end]
    script += r'''
function assert(cond, msg){ if(!cond){ console.error('FAIL', msg, 'got', typeof msg==='string'?'':msg); process.exit(1); } }
// /100 inchangé
assert(giMontant(70, 100) == null, '70/100 → null');
assert(giMontant(75, 100) === 500, '75/100 → 500');
assert(giMontant(100, 100) === 1000, '100/100 → 1000');
assert(giMontant(77, 100) === 500, '77/100 → palier 75');
// /250 : 75→130, 80→154, 85→178, 90→202, 95→226, 100→250
assert(giMontant(129, 250) == null, '129/250 sous le seuil → null');
assert(giMontant(130, 250) === 500, '130/250 → 500');
assert(giMontant(154, 250) === 600, '154 → 600');
assert(giMontant(170, 250) === 600, '170 → palier 154');
assert(giMontant(178, 250) === 700, '178 → 700');
assert(giMontant(180, 250) === 700, '180 → palier 178');
assert(giMontant(190, 250) === 700, '190 → palier 178');
assert(giMontant(202, 250) === 800, '202 → 800');
assert(giMontant(210, 250) === 800, '210 → palier 202');
assert(giMontant(226, 250) === 900, '226 → 900');
assert(giMontant(250, 250) === 1000, '250 → 1000');
assert(giMontant(null, 250) == null, 'note absente → null');
console.log('ok');
'''
    r = subprocess.run(['node', '-e', script], capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr


def test_pas_de_sparkline_ni_legende_euphorie_sous_la_barre_v2():
    # Uniquement sous la barre pilote, pas le dualBar /100 ni les libellés F&G
    start = AV.find('function dualBarPilot')
    end = AV.find('\nfunction ', start + 10)
    if end == -1:
        end = len(AV)
    body = AV[start:end]
    assert 'pilotSpark' not in body
    assert 'Euphorie · 100' not in body
    assert '0 · Peur extrême' not in body
    assert 'pilot-spark' not in body
    assert 'db-bot' not in body
    assert 'pilotLegJoin' in body
    assert 'pilot-brk' in body


def test_score_a_gauche_de_la_barre():
    assert 'apex-block-pilot apex-block-line' in AV
    assert '.apex-block.apex-block-pilot{display:grid;grid-template-columns:auto minmax(0,1fr)' in CSS


def test_rang_a_gauche_du_titre():
    needle = '<div class="fl-id"><span class="fl-rk">${k+1}</span><b>${r.name}</b>'
    assert needle in FONDS
    assert needle in PAYS
    assert '.fl-id{display:flex;flex-wrap:wrap;align-items:center' in CSS


def test_carre_position_sans_texte_position_active():
    assert 'Position active' not in POS
    assert 'function posActifCarre' in POS
    assert 'pos-carre' in POS and 'is-gain' in POS and 'is-loss' in POS
    assert '.pos-carre.is-gain' in CSS
    assert '.pos-carre.is-loss' in CSS
    # le carré agrège les courtiers
    assert "courts.join(' · ')" in POS
