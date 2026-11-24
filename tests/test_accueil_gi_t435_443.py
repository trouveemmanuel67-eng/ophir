"""t435u copie ticker, t436u mentions clôtures, t443u tableau secteurs."""
from __future__ import annotations

import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ACC = (ROOT / 'src' / 'accueil.js').read_text(encoding='utf-8')
GI = (ROOT / 'src' / 'good_invest.js').read_text(encoding='utf-8')
FONDS = (ROOT / 'src' / 'fonds.js').read_text(encoding='utf-8')
CSS = (ROOT / 'src' / 'template.html').read_text(encoding='utf-8')


def _js_sources():
    files = [
        'src/accueil.js', 'src/good_invest.js', 'src/secteurs.js', 'src/pays.js',
        'src/metaux.js', 'src/obligations.js', 'src/tabs.js',
    ]
    return {p: (ROOT / p).read_text(encoding='utf-8') for p in files}


def test_gi_copy_button_uses_tvtag_and_stop_propagation():
    assert 'ophirCopyBtn(it.tv)' in GI or 'class="cp"' in GI
    assert "data-c=" in FONDS and 'ophirCopy' in FONDS
    assert 'e.stopPropagation()' in FONDS
    assert 'navigator.clipboard' in FONDS
    assert 'execCommand' in FONDS
    assert "btn.dataset.tip=ok?'Copié'" in FONDS


def test_plus_de_mention_clotures_hebdo_sous_les_graphiques():
    for name, text in _js_sources().items():
        assert 'sr-mention' not in text, name
        assert 'Clôtures hebdomadaires au' not in text, name
        assert 'Bougies hebdomadaires clôturées uniquement' not in text, name
        assert 'Clôtures hebdomadaires des contrats à terme continus' not in text, name


def test_tableau_secteurs_noms_entiers_et_entete():
    assert '<span>Note APEX</span>' in ACC
    assert '<span>Signal</span>' not in ACC
    assert "short:'Oblig.'" in ACC  # libellé court conservé ailleurs, pas affiché
    assert '${homeEsc(label||short)}' in ACC
    assert "label:'Obligations'" in ACC
    assert "label:'Liquidités'" in ACC
    assert "label:'Immobilier'" in ACC
    assert "label:'Métaux précieux'" in ACC


def test_tri_normalise_note_via_node():
    start = ACC.find('function homeApexNorm(id){')
    end = ACC.find('function homeHeldHTML', start)
    assert start != -1 and end != -1
    script = ACC[start:end] + r'''
function sectionApexAvg(id){
  if(id==='actions') return {apexV2:{total:110, total_min:-50, total_max:250}};
  const notes={crypto:71, metaux:68, liquidites:60, immobilier:54, obligations:53, energie:49};
  if(id in notes) return {apex10:{note:notes[id]}};
  return null;
}
const PILOT = {scale:{min:-50, max:250}};
function assert(c,m){ if(!c){ console.error('FAIL', m); process.exit(1);} }
assert(Math.abs(homeApexNorm('crypto')-0.71)<1e-9, 'crypto');
assert(Math.abs(homeApexNorm('metaux')-0.68)<1e-9, 'metaux');
assert(Math.abs(homeApexNorm('actions')-(110+50)/300)<1e-9, 'actions 110/250');
assert(homeApexNorm('actions')>homeApexNorm('obligations'), '110/250 > 53/100 après norme');
assert(homeApexNorm('crypto')>homeApexNorm('actions'), 'crypto 71 > actions 110/250');
assert(homeApexNorm('inconnu')==null, 'absent');
console.log('ok');
'''
    r = subprocess.run(['node', '-e', script], capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr


def test_home_meta_wrapper_pour_mobile():
    assert '<div class="home-meta">' in ACC
    assert '.home-meta{display:contents}' in CSS


def test_tableau_mobile_sans_defilement_force():
    assert '.home-meta{display:contents}' in CSS
    assert '.home-table{min-width:0}' in CSS
    assert 'class="home-meta"' in ACC or "class='home-meta'" in ACC or 'class="home-meta">' in open(__import__('pathlib').Path(__file__).resolve().parents[1]/'src'/'accueil.js',encoding='utf-8').read()
    assert 'min-width:720px' not in CSS or CSS.count('.home-table{min-width:720px}') == 0
