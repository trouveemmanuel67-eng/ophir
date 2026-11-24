"""t444u tableau secteurs compact, t445u bouton P pattern baissier."""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ACC = (ROOT / "src" / "accueil.js").read_text(encoding="utf-8")
GI = (ROOT / "src" / "good_invest.js").read_text(encoding="utf-8")
CSS = (ROOT / "src" / "template.html").read_text(encoding="utf-8")
BUILD = (ROOT / "src" / "build.py").read_text(encoding="utf-8")
ETF = json.loads((ROOT / "config" / "etf_reference.json").read_text(encoding="utf-8"))


def test_etf_reference_config_complete():
    attendus = {
        "actions": "AMEX:SPY",
        "obligations": "AMEX:AGG",
        "metaux": "AMEX:GLD",
        "energie": "AMEX:XLE",
        "crypto": "NASDAQ:IBIT",
        "liquidites": "AMEX:BIL",
        "immobilier": "AMEX:VNQ",
    }
    for sid, tv in attendus.items():
        assert sid in ETF, sid
        assert ETF[sid]["tv"] == tv
        assert ETF[sid].get("nom")
    assert "__DATA_ETF__" in BUILD
    assert "dataEtfRef" in CSS
    assert "id=\"dataEtfRef\"" in CSS or "id='dataEtfRef'" in CSS
    assert "homeEtfHTML" in ACC
    assert "class=\"cp\"" in ACC or "class='cp'" in ACC or 'class="cp"' in ACC
    assert "data-c=" in ACC


def test_entetes_colonnes_compactes():
    assert "<span>Note APEX</span>" in ACC
    assert "<span>Détenu</span>" in ACC
    assert "<span>Latent</span>" in ACC
    assert "<span>Rdt</span>" in ACC
    assert "<span>ETF</span>" in ACC
    assert "<span>Sent.</span>" in ACC
    assert "<span>AV</span>" in ACC
    assert "<span>Hype</span>" in ACC
    assert "<span>Âge</span>" in ACC
    assert "<span>Drap.</span>" in ACC
    assert "Repère" not in ACC
    assert "homeApexNorm" in ACC  # tri conservé


def test_pas_inventer_rendement_ni_age_partiels():
    assert "homePosYield" in ACC
    assert "homePosBuyDate" in ACC
    assert "perf_1an_dates n'est pas une date d'achat" in ACC or "perf_1an_dates n’est pas une date d'achat" in ACC or "perf_1an_dates" in ACC
    assert "yAny&&!yMiss" in ACC
    assert "ageAny&&!ageMiss" in ACC
    assert "sectionHypeAvg" in ACC
    assert "indicateur d’attention non publié" in ACC or "indicateur d'attention non publié" in ACC


def test_stats_pnl_yield_age_via_node():
    start = ACC.find("function homeTabOf(p){")
    end = ACC.find("function homeCard({", start)
    assert start != -1 and end != -1
    script = ACC[start:end] + r"""
function posPct(p){ const s=p<0?-1:1,a=Math.abs(Number(p)); const r=Math.round(a*10+1e-9)/10; return (s<0?'−':'+')+r.toFixed(1).replace('.',',')+'\u00a0%'; }
function posAmt(n){ return Math.round(n)+' €'; }
function fmt(v,d){ return Number(v).toLocaleString('fr-FR',{maximumFractionDigits:d,minimumFractionDigits:d}); }
function sign(v,d){ return (v>0?'+':'')+fmt(v,d); }
function avCol(){ return '#e6c27a'; }
function assert(c,m){ if(!c){ console.error('FAIL', m); process.exit(1);} }

const act=[
  {tab:'obligations',statut:'active',valeur_eur:200,investi_eur:100,yield:4},
  {tab:'obligations',statut:'active',valeur_eur:100,investi_eur:100,yield:2},
  {tab:'actions',statut:'active',valeur_eur:100,investi_eur:80,date_execution:'2026-01-01T00:00:00Z'},
  {tab:'actions',statut:'active',valeur_eur:100,investi_eur:80},
  {tab:'energie',statut:'active',valeur_eur:50,investi_eur:40,date_execution:'2026-10-24T00:00:00Z'},
];
global.giNow = () => new Date('2026-11-24T12:00:00Z');
function giNow(){ return new Date('2026-11-24T12:00:00Z'); }

const ob=homeSectorStats(act,'obligations');
assert(Math.abs(ob.pnl-50)<1e-9, 'pnl obliga 300/200-1 = 50%: '+ob.pnl);
assert(Math.abs(ob.yield-(4*200+2*100)/300)<1e-9, 'yield pondéré: '+ob.yield);
assert(ob.ageDays==null, 'âge incomplet obliga');

const ac=homeSectorStats(act,'actions');
assert(ac.yield==null, 'pas de yield actions');
assert(ac.ageDays==null, 'âge partiel actions → null');
assert(Math.abs(ac.pnl-25)<1e-9, 'pnl actions 200/160-1');

const en=homeSectorStats(act,'energie');
assert(en.ageDays!=null && en.ageDays>20 && en.ageDays<50, 'âge énergie ~31j: '+en.ageDays);
assert(homeAgeTxt(en.ageDays).indexOf('j')>=0, 'affichage jours');
assert(homePosYield({nom:'US Treasury 3,625 % mai 2053'})==null, 'ne pas lire le coupon dans le nom');
assert(homeHypeOf('actions')==null, 'H non publié');
console.log('ok');
"""
    r = subprocess.run(["node", "-e", script], capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr


def test_bouton_p_meme_mecanique_que_e():
    assert 'GI_PATTERN_KEY=\'apex-gi-pattern-hide\'' in GI
    assert 'class="gi-pattern"' in GI
    assert ">P</button>" in GI
    assert 'title="Pattern baissier : retirer jusqu\'au 1er du mois"' in GI
    assert "giHidePattern" in GI
    assert "giIsPatternHidden(it.tv, hiddenP)" in GI or "giIsPatternHidden(it.tv, hiddenP)" in GI
    assert "e.stopPropagation()" in GI
    assert "Voir les masquées" not in GI
    assert ".gi-pattern{" in CSS
    assert "min-width:44px" in CSS and "min-height:44px" in CSS


def test_reset_mensuel_pattern_via_node(tmp_path):
    start = GI.find("const GI_PATTERN_KEY='apex-gi-pattern-hide';")
    end = GI.find("const GI_PAYS_ACTIONS=")
    assert start != -1 and end != -1
    head_start = GI.find("function giNow(){")
    head_end = GI.find("function giElliottHiddenMap(){")
    script = r"""
const store = {};
global.localStorage = {
  getItem(k){ return Object.prototype.hasOwnProperty.call(store,k) ? store[k] : null; },
  setItem(k,v){ store[k] = String(v); },
};
global.GI_NOW = new Date(2026, 10, 24, 15, 0, 0);
"""
    script += GI[head_start:head_end]
    script += GI[start:end]
    script += r"""
function assert(cond, msg){ if(!cond){ console.error('FAIL', msg); process.exit(1); } }
giHidePattern('NASDAQ:NVDA');
let map = giPatternHiddenMap();
assert(map['NASDAQ:NVDA'] === '2026-11', 'masqué en novembre: '+JSON.stringify(map));
assert(giIsPatternHidden('NASDAQ:NVDA', map) === true, 'NVDA hidden');
assert(giIsPatternHidden('NASDAQ:AAPL', map) === false, 'AAPL visible');
global.GI_NOW = new Date(2026, 10, 30, 23, 59, 0);
map = giPatternHiddenMap();
assert(map['NASDAQ:NVDA'] === '2026-11', 'tient jusqu’à fin novembre');
global.GI_NOW = new Date(2026, 11, 1, 0, 0, 0);
map = giPatternHiddenMap();
assert(Object.keys(map).length === 0, 'reset le 1er: '+JSON.stringify(map));
assert(giIsPatternHidden('NASDAQ:NVDA', map) === false, 'NVDA réapparaît');
assert(JSON.parse(localStorage.getItem('apex-gi-pattern-hide')||'{}')['NASDAQ:NVDA'] == null, 'entrée périmée nettoyée');
console.log('ok');
"""
    f = tmp_path / "test_gi_pattern.js"
    f.write_text(script, encoding="utf-8")
    r = subprocess.run(["node", str(f)], cwd=str(ROOT), capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "ok" in r.stdout


def test_mobile_sans_defilement_force():
    assert ".home-meta{display:contents}" in CSS
    assert "min-width:720px" not in CSS or CSS.count(".home-table{min-width:720px}") == 0
    assert "@media(max-width:1099px)" in CSS
