"""t432u : bouton E rouge pour retirer une ligne de Meilleures entrées."""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
JS = (ROOT / 'src' / 'good_invest.js').read_text(encoding='utf-8')
CSS = (ROOT / 'src' / 'template.html').read_text(encoding='utf-8')


def test_bouton_e_rouge_sur_chaque_ligne():
    assert 'class="gi-elliott"' in JS
    assert '>E</button>' in JS
    assert 'title="Retirer : vague Elliott non propice"' in JS
    assert 'aria-label="Retirer : vague Elliott non propice"' in JS
    assert 'e.stopPropagation()' in JS
    assert 'giHideElliott' in JS
    assert '.gi-elliott{' in CSS
    assert 'color:#ff2d2d' in CSS
    assert 'min-width:44px' in CSS and 'min-height:44px' in CSS


def test_pas_de_liste_masquees_ni_de_confirm():
    assert 'Voir les masquées' not in JS
    assert 'confirm(' not in JS
    assert 'gi-masqu' not in JS.lower()


def test_masquage_ne_touche_pas_la_note():
    assert 'giHideElliott(b.dataset.tv)' in JS
    assert 'giRender()' in JS
    # le retrait filtre uniquement l'affichage de Meilleures entrées
    assert 'giCollect().filter(it=>!giIsElliottHidden(it.tv, hidden))' in JS
    assert 'note=' not in JS[JS.find('function giHideElliott'):JS.find('function giHideElliott')+400]


def test_stockage_localstorage_par_mois():
    assert "GI_ELLIOTT_KEY='apex-gi-elliott-hide'" in JS
    assert 'giMonthKey' in JS
    assert 'localStorage.setItem(GI_ELLIOTT_KEY' in JS
    assert 'if(raw[k]===month)' in JS


def test_reset_mensuel_et_compteur_via_node(tmp_path):
    script = r'''
const store = {};
global.localStorage = {
  getItem(k){ return Object.prototype.hasOwnProperty.call(store,k) ? store[k] : null; },
  setItem(k,v){ store[k] = String(v); },
};
global.GI_NOW = new Date(2026, 10, 24, 15, 0, 0); // 24/11/2026 heure locale
'''
    # Extraire uniquement les fonctions de masquage, sans le reste du fichier.
    start = JS.find("const GI_ELLIOTT_KEY='apex-gi-elliott-hide';")
    end = JS.find('const GI_PAYS_ACTIONS=')
    assert start != -1 and end != -1
    script += JS[start:end]
    script += r'''
function assert(cond, msg){ if(!cond){ console.error('FAIL', msg); process.exit(1); } }

giHideElliott('NASDAQ:NVDA');
giHideElliott('EURONEXT:MC');
let map = giElliottHiddenMap();
assert(map['NASDAQ:NVDA'] === '2026-11', 'masqué en novembre: '+JSON.stringify(map));
assert(map['EURONEXT:MC'] === '2026-11', 'MC masqué');
assert(giIsElliottHidden('NASDAQ:NVDA', map) === true, 'NVDA hidden');
assert(giIsElliottHidden('NASDAQ:AAPL', map) === false, 'AAPL visible');

// même mois : le masquage tient
global.GI_NOW = new Date(2026, 10, 30, 23, 59, 0);
map = giElliottHiddenMap();
assert(map['NASDAQ:NVDA'] === '2026-11', 'tient jusqu’à fin novembre');

// 1er décembre : reset automatique
global.GI_NOW = new Date(2026, 11, 1, 0, 0, 0);
map = giElliottHiddenMap();
assert(Object.keys(map).length === 0, 'reset le 1er: '+JSON.stringify(map));
assert(giIsElliottHidden('NASDAQ:NVDA', map) === false, 'NVDA réapparaît');
assert(JSON.parse(localStorage.getItem('apex-gi-elliott-hide')||'{}')['NASDAQ:NVDA'] == null, 'entrée périmée nettoyée');

console.log('ok');
'''
    f = tmp_path / 'test_gi_elliott.js'
    f.write_text(script, encoding='utf-8')
    r = subprocess.run(['node', str(f)], cwd=str(ROOT), capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
    assert 'ok' in r.stdout
