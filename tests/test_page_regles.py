"""t347u / t348u : page RÈGLES plein écran, tableau Actions uniquement."""
from __future__ import annotations
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope='module')
def regles():
    return json.loads((ROOT / 'config' / 'regles.json').read_text(encoding='utf-8'))


def test_page_sections_actions_seulement(regles):
    fr = regles['fiche_regles']
    secs = fr.get('page_sections') or []
    assert [s['id'] for s in secs] == ['actions']
    assert secs[0]['classe'] == 'actions'


def test_points_max_amplitude(regles):
    na = regles['note_apex']
    amp = na['amplitude_totale']
    assert na['note_base'] == 50
    assert na['amplitude_echelle'] == pytest.approx(1.5)
    assert amp == pytest.approx(75)
    # poids dans la note × amplitude = points max
    assert na['poids_fondamental'] * amp == pytest.approx(37.5)
    assert na['technique']['elliott'] * amp == pytest.approx(7.5)
    assert na['technique']['structure'] * amp == pytest.approx(7.5)
    assert na['technique']['fibonacci'] * amp == pytest.approx(6.0)
    assert na['technique']['figure'] * amp == pytest.approx(5.25)
    assert na['technique']['rsi'] * amp == pytest.approx(3.75)
    assert na['fond_pen_max'] == pytest.approx(20)


def test_js_page_plein_ecran_pas_panneau():
    js = (ROOT / 'src' / 'regles.js').read_text(encoding='utf-8')
    css = (ROOT / 'src' / 'template.html').read_text(encoding='utf-8')
    assert 'id="rg-page"' in js or "id='rg-page'" in js or 'rg-page' in js
    assert 'function rgSetOpen' in js
    assert '#regles' in js
    assert 'rgBack' in js and 'rgClose' in js
    assert 'rg-table-actions' in js
    assert 'body.rg-on' in css
    assert '#rg-page{display:none;position:fixed;inset:0' in css.replace(' ', '') or 'position:fixed;inset:0' in css
    # plus de sous-menu / panneau déroulant
    assert '.rg-wrap.is-open .rg-panel' not in css
    assert 'is-open' not in js or 'rg-wrap' in js  # bouton reste dans rg-wrap
    # pas de sections autres qu'Actions en table principale
    assert 'rg-sec-obligations' not in js
    assert 'rg-sec-crypto' not in js
    for w in ('avertissement', 'disclaimer', 'Ce n’est pas un conseil'):
        assert w.lower() not in js.lower()


def test_show_gere_ancre_regles():
    html = (ROOT / 'src' / 'template.html').read_text(encoding='utf-8')
    assert "id==='regles'" in html
    assert 'rgSetOpen(true,{fromHash:true})' in html


def test_garde_fou_ouvre_la_page():
    src = (ROOT / 'scripts' / 'garde_fou_site.py').read_text(encoding='utf-8')
    assert 'CHECK_REGLES_OPEN_JS' in src
    assert 'page RÈGLES' in src


def test_apex_achat_v2_rsi_seulement(regles):
    v = regles['apex_achat_v2']
    assert v.get('utilise_par_le_calcul') is False
    assert v.get('affichage_seulement') is True
    assert 'accumulation' in (v.get('intro') or '').lower() or 'accumulation' in (v.get('titre') or '').lower()
    criteres = v.get('criteres') or []
    assert [c['id'] for c in criteres] == ['rsi_14_hebdo', 'macd_12_26_9_hebdo']
    by = {c['id']: c for c in criteres}
    rsi, macd = by['rsi_14_hebdo'], by['macd_12_26_9_hebdo']
    for c in (rsi, macd):
        assert c['max'] == 30
        assert c.get('retrait') is False
        assert c.get('cumulables') is True
    pts = {c['id']: c['points'] for c in rsi['conditions']}
    assert pts['rsi_sous_40'] == 10
    assert pts['divergence_rsi_haussiere_hebdo'] == 20
    pts = {c['id']: c['points'] for c in macd['conditions']}
    assert pts['macd_sous_0'] == 10
    assert pts['histo_4_barres_rouges_sous_0'] == 20
    # les règles de calcul de la note actuelle restent inchangées
    assert regles['note_apex']['technique']['rsi'] == 0.05
    assert regles['note_apex']['note_base'] == 50


def test_apex_achat_v2_ignore_par_le_calcul():
    src = (ROOT / 'apex' / 'score.py').read_text(encoding='utf-8')
    assert 'apex_achat_v2' not in src


def test_js_rsi_affiche_regles_achat_dans_le_tableau():
    js = (ROOT / 'src' / 'regles.js').read_text(encoding='utf-8')
    css = (ROOT / 'src' / 'template.html').read_text(encoding='utf-8')
    assert 'function rgAchatV2Critere' in js
    assert 'function rgAchatV2Rule' in js
    assert 'rg-table-actions' in js
    # pas de tableau séparé ni de bloc replié
    assert 'rg-table-achat' not in js
    assert 'function rgAchatV2()' not in js
    assert 'rg-ref' not in js
    assert 'rg-table-achat' not in css
    assert '.rg-ref' not in css
    # la ligne RSI du tableau principal est remplacée par les règles d'affichage
    assert 'rgAchatV2Critere(x.id)' in js
    assert 'rgAchatV2Rule(v2)' in js
