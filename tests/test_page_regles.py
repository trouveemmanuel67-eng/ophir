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
    assert 'figure' not in na['technique']
    assert sum(na['technique'].values()) == pytest.approx(0.5)
    assert na['technique']['elliott'] * amp == pytest.approx(0.10 * 50 / 43 * 75, rel=1e-6)
    assert na['technique']['structure'] * amp == pytest.approx(0.10 * 50 / 43 * 75, rel=1e-6)
    assert na['technique']['fibonacci'] * amp == pytest.approx(0.08 * 50 / 43 * 75, rel=1e-6)
    assert na['technique']['rsi'] * amp == pytest.approx(0.05 * 50 / 43 * 75, rel=1e-6)
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
    assert v.get('utilise_par_le_calcul') is True
    assert v.get('affichage_seulement') is False
    assert v.get('applique_au_calcul') is True
    assert 'accumulation' in (v.get('intro') or '').lower() or 'accumulation' in (v.get('titre') or '').lower()
    criteres = v.get('criteres') or []
    assert [c['id'] for c in criteres] == [
        'rsi_14_hebdo', 'macd_12_26_9_hebdo', 'fibonacci', 'cci_20_hebdo'
    ]
    by = {c['id']: c for c in criteres}
    rsi, macd = by['rsi_14_hebdo'], by['macd_12_26_9_hebdo']
    for c in (rsi, macd):
        assert c['max'] == 27  # APE-25 : × 0,9
        assert c.get('retrait') is False
        assert c.get('cumulables') is True
    pts = {c['id']: c['points'] for c in rsi['conditions']}
    assert pts['rsi_sous_40'] == 9
    assert pts['divergence_rsi_haussiere_hebdo'] == 18
    pts = {c['id']: c['points'] for c in macd['conditions']}
    assert pts['macd_sous_0'] == 9
    assert pts['histo_4_barres_rouges_sous_0'] == 18
    assert "4 barres rouges" in (macd.get('regle_courte') or '')
    assert "max 27" in (macd.get('regle_courte') or '')
    banque = regles['apex_achat_v2_banque']
    macd_b = {c['id']: c for c in banque['criteres']}['macd_12_26_9_hebdo']
    assert "4 barres rouges" in (macd_b.get('regle_courte') or '')

    fibo = by['fibonacci']
    assert fibo['max'] == 27 and fibo.get('cumulables') is False and fibo.get('retrait') is False
    fp = {c['id']: c['points'] for c in fibo['conditions']}
    assert fp == {'sous_382': 9, 'sous_618': 18, 'sous_786': 27}
    assert 'elliott' not in by
    cci = by['cci_20_hebdo']
    assert cci['max'] == 18
    assert 'sous 20' in (cci['conditions'][0]['label'] + ' ' + (cci.get('regle_courte') or ''))
    assert 'Daveatt' in (cci.get('label') or '')
    assert 'sous 20' in cci['conditions'][0]['label']
    assert cci['conditions'][0]['points'] == 18
    assert sum(c['max'] for c in criteres) == 99
    # les règles de calcul de la note actuelle restent inchangées
    assert 'figure' not in regles['note_apex']['technique']
    assert abs(sum(regles['note_apex']['technique'].values()) - 0.5) < 1e-9
    assert regles['note_apex']['note_base'] == 50


def test_apex_achat_v2_ignore_par_le_calcul():
    src = (ROOT / 'apex' / 'score.py').read_text(encoding='utf-8')
    assert 'FOND_RULES' in src or 'compute(' in src  # le /100 ignore toujours le barème v2 additif


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
    assert 'function rgAchatV2Total' in js
    assert 'rg-row-total' in js

def test_structure_masquee_affichage_seulement(regles):
    assert 'structure' in (regles['apex_achat_v2'].get('masquer_criteres') or [])
    # le calcul conserve Structure (poids renormalisé après retrait de Figure)
    assert 'structure' in regles['note_apex']['technique']
    assert regles['note_apex']['technique']['structure'] == pytest.approx(0.10 * 50 / 43, rel=1e-6)
    js = (ROOT / 'src' / 'regles.js').read_text(encoding='utf-8')
    assert 'masquer_criteres' in js
    assert 'masquer.indexOf(x.id)>=0' in js

def test_fondamental_v2_neuf_elements(regles):
    fond = regles['apex_achat_v2']['fondamental']
    assert fond['max'] == 81
    assert fond['points_si_bon'] == 9
    els = [e for g in fond['groupes'] for e in g['elements']]
    assert [e['id'] for e in els] == [
        'dette_nette_ebitda', 'marge_operationnelle', 'marge_fcf', 'roe',
        'ratio_liquidite_courante', 'bpa_annee_prochaine', 'bpa_cette_annee',
        'ca_annee_prochaine', 'ca_cette_annee',
    ]
    assert all(e['points'] == 9 and e.get('seuil_a_valider') is False for e in els)
    by = {e['id']: e for e in els}
    assert by['dette_nette_ebitda']['bon_si'] == '< 2'
    assert by['marge_operationnelle']['bon_si'] == '> 15 %'
    assert by['marge_fcf']['bon_si'] == '> 10 %'
    assert by['roe']['bon_si'] == '> 15 %'
    assert by['ratio_liquidite_courante']['bon_si'] == '> 1,2'
    assert by['bpa_annee_prochaine']['bon_si'] == '> 10 %'
    assert by['bpa_cette_annee']['bon_si'] == '> 10 %'
    assert by['ca_annee_prochaine']['bon_si'] == '> 5 %'
    assert by['ca_cette_annee']['bon_si'] == '> 5 %'
    tech = sum(c['max'] for c in regles['apex_achat_v2']['criteres'])
    assert tech == 99
    assert tech + fond['max'] == 180
    # calcul inchangé
    assert regles['note_apex']['poids_fondamental'] == 0.5
    js = (ROOT / 'src' / 'regles.js').read_text(encoding='utf-8')
    assert 'function rgActionsGrid' in js
    assert 'rg-cards' in js
    assert 'rg-card' in js

def test_tableau_grille_homogene():
    js = (ROOT / 'src' / 'regles.js').read_text(encoding='utf-8')
    css = (ROOT / 'src' / 'template.html').read_text(encoding='utf-8')
    assert 'function rgActionsGrid' in js
    body = js.split('function rgActionsGrid')[1].split('function rgPageHTML')[0]
    assert 'rg-cards' in body and 'rg-fond-cols' in body
    assert 'idéalement' not in body.lower()
    assert 'Figure chartiste' not in body
    assert 'techSum' in js or 'RSI' in body or 'rsi' in body
    assert 'Fondamental' in body
    assert 'Sentiment' in body or 'sentBlock' in body
    assert '.rg-cards' in css
    assert 'grid-template-columns:1fr 1fr' in css
    assert '@media(max-width:800px)' in css
    # une colonne sur mobile
    mobile = css.split('@media(max-width:800px)')[1]
    assert '.rg-cards,.rg-fond-cols{grid-template-columns:1fr' in mobile or 'grid-template-columns:1fr' in mobile


def test_sentiment_fear_greed_affichage_seulement(regles):
    sent = regles['apex_achat_v2']['sentiment']
    assert sent.get('utilise_par_le_calcul') is False
    assert sent.get('affichage_seulement') is True
    assert sent.get('max_affiche') == '±50'
    assert 'fear_greed' not in (regles['note_apex'].get('technique') or {})
    assert 'sentiment' not in (regles['note_apex'].get('technique') or {})
    fg = (sent.get('criteres') or sent.get('elements') or [None])[0]
    assert fg and fg['id'] == 'fear_greed_index'
    assert fg['label'] == 'Fear & Greed Index'
    assert fg['points_max'] == '±50'
    assert 'Milieu 50' in fg['regle']
    assert 'peur 40 → +10' in fg['regle']
    assert 'avidité 60 → −10' in fg['regle']
    by = {c['valeur']: c['points'] for c in fg['conditions']}
    assert by[50] == 0
    assert by[40] == 10 and by[0] == 50
    assert by[60] == -10 and by[100] == -50
    js = (ROOT / 'src' / 'regles.js').read_text(encoding='utf-8')
    assert 'sentBlock' in js
    assert 'Fear' in js or 'sentiment' in js


def test_pas_d_intro_ni_base_affichage(regles):
    # le calcul part toujours de 50 ; la page RÈGLES n'affiche plus d'intro
    assert regles['note_apex']['note_base'] == 50
    assert 'accroche' not in (regles.get('apex_achat_v2') or {})
    js = (ROOT / 'src' / 'regles.js').read_text(encoding='utf-8')
    page = js.split('function rgPageHTML')[1].split('function rgRender')[0]
    assert 'rg-lead' not in page
    assert 'accroche' not in page
    assert 'La note part de 0' not in page
    assert 'clip dans 0–100' not in page
    assert 'Actions cotées' not in page
    grid = js.split('function rgActionsGrid')[1].split('function rgPageHTML')[0]
    assert "label:'Base'" not in grid
    assert "id:'base'" not in grid and 'id:"base"' not in grid


def test_echelle_actions_calculee_automatiquement(regles):
    v = regles['apex_achat_v2']
    tech = sum(c['max'] for c in v['criteres'])
    fond = v['fondamental']['max']
    # Fear & Greed ±50
    assert v['sentiment']['max_affiche'] == '±50'
    assert tech == 99 and fond == 81  # APE-25
    js = (ROOT / 'src' / 'regles.js').read_text(encoding='utf-8')
    assert 'function rgActionsScale' in js
    assert 'rg-scale' in js
    # le libellé est calculé, pas un « 270 » en dur dans le titre
    page = js.split('function rgPageHTML')[1].split('function rgRender')[0]
    assert 'rgActionsScale(' in page and '.label' in page
    assert '270' not in page
    css = (ROOT / 'src' / 'template.html').read_text(encoding='utf-8')
    assert '.rg-scale' in css


def test_accordeon_actions_generique():
    js = (ROOT / 'src' / 'regles.js').read_text(encoding='utf-8')
    css = (ROOT / 'src' / 'template.html').read_text(encoding='utf-8')
    assert 'function rgSectionAccordion' in js
    assert "id:'actions'" in js and 'open:true' in js
    assert 'rg-acc-btn' in js and 'rg-acc-panel' in js
    assert 'rg-acc-btn' in css and 'grid-template-rows' in css
    assert '.rg-acc-chev' in css


def test_elliott_retire_de_apex_achat_v2(regles):
    for key in ('apex_achat_v2', 'apex_achat_v2_banque'):
        ids = [c['id'] for c in (regles[key].get('criteres') or [])]
        assert 'elliott' not in ids
        intro = (regles[key].get('intro') or '')
        assert '250' in intro and '280' not in intro and 'Elliott' in intro


def test_cci_stochastic_daveatt_regle(regles):
    cci = {c['id']: c for c in (regles['apex_achat_v2']['criteres'] or [])}['cci_20_hebdo']
    assert cci['max'] == 18
    assert 'CCI Stochastic' in (cci.get('label') or '')
    assert 'Daveatt' in (cci.get('label') or '')
    assert '28' in (cci.get('label') or '')
    assert '+18 si sous 20' in (cci.get('regle_courte') or '')


def test_seuils_fondamentaux_valides(regles):
    fond = regles['apex_achat_v2']['fondamental']
    els = [e for g in fond['groupes'] for e in g['elements']]
    assert all(e.get('seuil_a_valider') is False for e in els)
    assert 'à valider' not in (fond.get('precision') or '').lower()
    by = {e['id']: e for e in els}
    assert by['dette_nette_ebitda']['bon_si'] == '< 2'
    assert by['marge_operationnelle']['bon_si'] == '> 15 %'
    assert by['marge_fcf']['bon_si'] == '> 10 %'
    assert by['roe']['bon_si'] == '> 15 %'
    assert by['ratio_liquidite_courante']['bon_si'] == '> 1,2'
    assert by['bpa_annee_prochaine']['bon_si'] == '> 10 %'
    assert by['bpa_cette_annee']['bon_si'] == '> 10 %'
    assert by['ca_annee_prochaine']['bon_si'] == '> 5 %'
    assert by['ca_cette_annee']['bon_si'] == '> 5 %'


def test_actions_hors_banque_et_accordeon_bancaire(regles):
    v = regles['apex_achat_v2']
    assert v.get('date_validation') == '23/11/2026'
    assert v.get('reglage_valide') is True
    assert v.get('section_titre') == 'Actions (hors banque)'
    assert 'hors banques' in (v.get('champ_application') or '')
    assert 'USA' in (v.get('champ_application') or '') and 'France' in (v.get('champ_application') or '')
    assert 'Allemagne' not in (v.get('champ_application') or '')
    assert 'pilote' not in (v.get('intro') or '').lower()
    assert v.get('applique_au_calcul') is True
    # le réglage validé est bien celui du CCI Daveatt + seuils fond
    cci = {c['id']: c for c in (v.get('criteres') or [])}['cci_20_hebdo']
    assert 'Daveatt' in (cci.get('label') or '')
    assert all(e.get('seuil_a_valider') is False for g in v['fondamental']['groupes'] for e in g['elements'])

    b = regles['apex_achat_v2_banque']
    assert 'apex_achat_v2_banques' not in regles
    assert b.get('date_validation') == '23/11/2026'
    assert b.get('reglage_valide') is True
    assert b.get('utilise_par_le_calcul') is True
    assert b.get('affichage_seulement') is False
    assert b.get('applique_au_calcul') is True
    assert 'pilote' not in (b.get('champ_application') or '').lower()
    assert 'pilote' not in (b.get('intro') or '').lower()
    assert 'USA' in (b.get('champ_application') or '') and 'France' in (b.get('champ_application') or '')
    assert 'Allemagne' not in (b.get('champ_application') or '')
    assert [c['id'] for c in (b.get('criteres') or [])] == [c['id'] for c in (v.get('criteres') or [])]
    assert (b.get('sentiment') or {}).get('id') == (v.get('sentiment') or {}).get('id')
    fond = b['fondamental']
    assert fond.get('max') == 81
    assert fond.get('points_si_bon') == 9
    assert fond.get('a_personnaliser') is False
    els = [e for g in fond['groupes'] for e in g['elements']]
    assert [e['id'] for e in els] == [
        'roe', 'roa', 'ratio_cet1', 'cout_du_risque', 'coefficient_exploitation',
        'bpa_cette_annee', 'bpa_annee_prochaine', 'pnb_cette_annee', 'pnb_annee_prochaine',
    ]
    assert all(e['points'] == 9 and e.get('seuil_a_valider') is False for e in els)
    by = {e['id']: e for e in els}
    assert by['roe']['bon_si'] == '> 10 %'
    assert by['roa']['bon_si'] == '> 1 %'
    assert by['ratio_cet1']['bon_si'] == '> 12 %'
    assert by['cout_du_risque']['bon_si'] == '< 0,5 %'
    assert by['coefficient_exploitation']['bon_si'] == '< 60 %'
    assert by['bpa_cette_annee']['bon_si'] == '> 10 %'
    assert by['bpa_annee_prochaine']['bon_si'] == '> 10 %'
    assert by['pnb_cette_annee']['bon_si'] == '> 5 %'
    assert by['pnb_annee_prochaine']['bon_si'] == '> 5 %'
    assert by['bpa_cette_annee']['label'] == 'Croissance BPA année en cours'
    assert by['pnb_annee_prochaine']['label'] == 'Croissance PNB année prochaine'
    tech = sum(c['max'] for c in b['criteres'])
    assert tech == 99
    assert b['sentiment']['max_affiche'] == '±50'
    assert tech + fond['max'] + 50 == 230
    assert b['hype']['max'] == 20 and tech + fond['max'] + 50 + b['hype']['max'] == 250  # APE-25

    js = (ROOT / 'src' / 'regles.js').read_text(encoding='utf-8')
    assert 'Actions (hors banque)' in js
    assert "id:'banques'" in js and 'open:false' in js
    assert 'apex_achat_v2_banque' in js
    assert 'rgActionsScale(vBan).label' in js
    assert 'rg-table-banques' in js
    # le moteur de note historique /100 (apex/score.py) reste inchangé ; le pilote bancaire
    # est calculé par build_apex_achat_v2_pilot.py (règles apex_achat_v2_banque).
    score = (ROOT / 'apex' / 'score.py').read_text(encoding='utf-8')
    assert 'apex_achat_v2_banque' not in score
    builder = (ROOT / 'src' / 'build_apex_achat_v2_pilot.py').read_text(encoding='utf-8')
    assert 'FOND_RULES_BANQUE' in builder and 'apex_achat_v2_banque' in builder
