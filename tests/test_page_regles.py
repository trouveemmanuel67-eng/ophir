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
