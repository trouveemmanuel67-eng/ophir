"""t458u : la recherche ne matche plus une sous-chaîne au milieu d'un mot."""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
JS = (ROOT / "src" / "recherche.js").read_text(encoding="utf-8")
PILOT = json.loads((ROOT / "data" / "apex_achat_v2_pilot.json").read_text(encoding="utf-8"))


def _by_tv():
    out = {}
    for k, rec in (PILOT.get("by_tv") or {}).items():
        out[k] = {kk: rec[kk] for kk in ("nom", "ticker", "tv", "kind") if kk in rec}
    return out


def _run(extra: str):
    slim = json.dumps({"by_tv": _by_tv()}, ensure_ascii=False)
    script = JS + "\nconst PILOT = " + slim + ";\n" + extra
    r = subprocess.run(["node", "-e", script], cwd=str(ROOT), capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
    return r.stdout


def test_plus_de_sous_chaine_au_milieu_du_mot():
    js = JS
    assert "nom.indexOf(qf)" not in js
    assert "function apxTickerKeys" in js


def test_cat_ticker_exact_en_premier_sans_communication():
    out = _run(
        r"""
function assert(c,m){ if(!c){ console.error('FAIL', m); process.exit(1);} }
for (const q of ['CAT','cat']) {
  const hits=apxSearch(q, 12);
  assert(hits.length>=1, q+' vide');
  assert(hits[0].tv==='NYSE:CAT', q+' premier='+JSON.stringify(hits[0]));
  assert(!hits.some(h=>/Eutelsat|Communications/i.test(h.nom||'')||/PANIER-FR-COM/i.test(h.tv||'')), q+' sous-chaîne: '+JSON.stringify(hits.map(h=>h.tv+' '+h.nom)));
}
const orange=apxSearch('Orange', 8);
assert(orange.some(h=>h.tv==='EURONEXT:ORA'||/^ORA/i.test(h.ticker||'')), 'Orange: '+JSON.stringify(orange));
const nvda=apxSearch('NVDA', 8);
assert(nvda.length>=1 && (nvda[0].tv==='NASDAQ:NVDA'||nvda[0].ticker==='NVDA'), 'NVDA premier='+JSON.stringify(nvda[0]));
const pref=apxSearch('NYSE:CAT', 8);
assert(pref.length>=1 && pref[0].tv==='NYSE:CAT', 'préfixe TV');
console.log('ok');
"""
    )
    assert "ok" in out
