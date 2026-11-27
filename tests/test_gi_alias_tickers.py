"""Exclusion des Meilleures entrées : alias de tickers (XAU = XAUUSD, XAG = XAGUSD)."""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
JS = (ROOT / "src" / "good_invest.js").read_text(encoding="utf-8")


def test_table_alias_metaux_dans_good_invest():
    assert "GI_TICKER_ALIAS_GROUPS" in JS
    assert "function giAliasKeys" in JS
    assert "['XAU','XAUUSD','OANDA:XAUUSD']" in JS.replace(" ", "")
    assert "['XAG','XAGUSD','OANDA:XAGUSD']" in JS.replace(" ", "")
    assert "giAliasKeys(s).forEach(k=>set.add(k))" in JS.replace(" ", "")
    assert "giAliasKeys(s).some(k=>held.has(k))" in JS.replace(" ", "")


def _eval_js(script: str) -> dict:
    src = JS
    # garder uniquement les helpers d'alias / held, sans le reste du module
    start = src.index("const GI_TICKER_ALIAS_GROUPS")
    end = src.index("function giMontant")
    helpers = src[start:end]
    full = helpers + "\n" + script
    r = subprocess.run(
        ["node", "-e", full],
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(r.stdout)


def test_xau_detenue_exclut_xauusd():
    out = _eval_js(
        """
        globalThis.POS={positions:[{ticker:'XAU',tv_note:'XAU',fiche_tv:'XAU',statut:'active'}]};
        const held=giHeldSet();
        const xauusd=giIsHeld({tv:'OANDA:XAUUSD',ticker:'XAUUSD'}, held);
        const igln=giIsHeld({tv:'LSE:IGLN',ticker:'IGLN'}, held);
        const nflx=giIsHeld({tv:'NASDAQ:NFLX',ticker:'NFLX'}, held);
        process.stdout.write(JSON.stringify({
          hasXAUUSD: held.has('OANDA:XAUUSD') && held.has('XAUUSD'),
          xauusd, igln, nflx
        }));
        """
    )
    assert out["hasXAUUSD"] is True
    assert out["xauusd"] is True
    assert out["igln"] is False
    assert out["nflx"] is False


def test_xag_detenue_sous_ticker_court_exclut_xagusd():
    out = _eval_js(
        """
        globalThis.POS={positions:[{ticker:'XAG',tv_note:'XAG',fiche_tv:'XAG',statut:'active'}]};
        const held=giHeldSet();
        process.stdout.write(JSON.stringify({
          held: giIsHeld({tv:'OANDA:XAGUSD'}, held)
        }));
        """
    )
    assert out["held"] is True
