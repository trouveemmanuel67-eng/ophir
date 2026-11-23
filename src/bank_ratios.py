#!/usr/bin/env python3
"""Ratios bancaires Yahoo Finance — jamais inventés.

CET1 : non publié dans T.info ni dans les états financiers Yahoo inspectés.
Coût du risque : uniquement si une ligne clairement crédit / créances
(provision for credit losses, credit impairment, loan loss provision).
Une ligne générique « Provisionand Write Offof Assets » (flux de trésorerie)
n'est pas retenue (pas spécifiquement le coût du risque crédit).
Coefficient d'exploitation :
  1) ligne « Efficiency Ratio » si elle existe ;
  2) sinon Operating Expense / Total Revenue × 100 ;
  3) sinon (SG&A + Occupancy + Professional + Other Non Interest Expense)
     / Total Revenue × 100, uniquement si ces postes existent sans
     double-comptage des sous-lignes de SG&A.
"""
from __future__ import annotations
import json, math
from datetime import datetime
from zoneinfo import ZoneInfo
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / 'data' / 'apex_achat_v2_banque_ratios.json'
PARIS = ZoneInfo('Europe/Paris')

CET1_LABELS = (
    'cet1', 'common equity tier 1', 'tier 1 common', 'tier1 common',
    'common tier 1', 'cet 1 ratio',
)
CREDIT_PROVISION_LABELS = (
    'provision for credit losses', 'provision for loan losses',
    'credit loss expense', 'credit impairment', 'impairment on loans',
    'loan loss provision', 'provisions for credit losses',
    'net charge offs', "provision for doubtful",
)
# trop générique, exclu volontairement : provisionand write offof assets
EFFICIENCY_LABELS = ('efficiency ratio', "coefficient d'exploitation", 'cost income ratio', 'cost-to-income')
OPEX_LABELS = ('operating expense', 'operating expenses')
REVENUE_LABELS = ('total revenue', 'operating revenue')
NET_LOAN_LABELS = ('net loan', 'net loans', 'gross loan', 'gross loans', 'total loans')
NIE_PARTS = (
    'selling general and administration',
    'occupancy and equipment',
    'professional expense and contract services expense',
    'other non interest expense',
    'other noninterest expense',
)


def _norm(s):
    return ' '.join(str(s).lower().replace('&', 'and').replace('-', ' ').split())


def _num(v):
    try:
        if v is None or (isinstance(v, float) and math.isnan(v)):
            return None
        x = float(v)
        if not math.isfinite(x):
            return None
        return x
    except Exception:
        return None


def _latest(df, labels):
    """Return (value, label, period, source_ok) for the first matching row, latest column."""
    if df is None or getattr(df, 'empty', True):
        return None
    wanted = {_norm(x) for x in labels}
    for lab in df.index:
        if _norm(lab) in wanted or any(_norm(lab).startswith(w) and w in _norm(lab) for w in wanted):
            for col in df.columns:
                v = _num(df.loc[lab, col])
                if v is not None:
                    period = str(col.date()) if hasattr(col, 'date') else str(col)[:10]
                    return {'valeur': v, 'ligne': str(lab), 'periode': period}
    return None


def _lookup_contains(df, needles):
    if df is None or getattr(df, 'empty', True):
        return None
    needles = tuple(_norm(n) for n in needles)
    for lab in df.index:
        nl = _norm(lab)
        if any(n in nl for n in needles):
            for col in df.columns:
                v = _num(df.loc[lab, col])
                if v is not None:
                    period = str(col.date()) if hasattr(col, 'date') else str(col)[:10]
                    return {'valeur': v, 'ligne': str(lab), 'periode': period}
    return None


def extract_from_frames(frames):
    """frames: dict name -> DataFrame."""
    out = {
        'ratio_cet1': None,
        'cout_du_risque': None,
        'coefficient_exploitation': None,
        'sources': {},
        'lignes_vues': {},
    }
    # CET1
    for name, df in frames.items():
        hit = _lookup_contains(df, CET1_LABELS)
        if hit:
            # si la valeur est un ratio déjà en % (~5-30) on la garde ;
            # si c'est un montant, on ne l'utilise pas comme ratio CET1.
            v = hit['valeur']
            if 0 < v <= 100:
                out['ratio_cet1'] = round(v, 2)
                out['sources']['ratio_cet1'] = {**hit, 'statement': name, 'formule': 'ligne Yahoo nominative'}
                break
    if not out['sources'].get('ratio_cet1'):
        out['sources']['ratio_cet1'] = {
            'manquant': True,
            'raison': "Aucune ligne CET1 / Common Equity Tier 1 dans les états et ratios Yahoo (T.info, income, balance, cashflow).",
        }

    # Coût du risque = provision crédit / prêts
    prov = None
    loans = None
    for name, df in frames.items():
        if prov is None:
            prov = _lookup_contains(df, CREDIT_PROVISION_LABELS)
            if prov:
                prov['statement'] = name
        if loans is None:
            loans = _latest(df, NET_LOAN_LABELS) or _lookup_contains(df, ('net loan', 'gross loan', 'total loan'))
            if loans:
                loans['statement'] = name
    if prov and loans and loans['valeur']:
        # provision annuelle typiquement ; si période trimestrielle, on le signale
        ratio = abs(prov['valeur']) / abs(loans['valeur']) * 100
        out['cout_du_risque'] = round(ratio, 4)
        out['sources']['cout_du_risque'] = {
            'formule': '|provision crédit| / |prêts nets| × 100',
            'provision': prov,
            'prets': loans,
        }
    else:
        # mentionner la ligne générique si vue, sans l'utiliser
        generic = None
        for name, df in frames.items():
            generic = _lookup_contains(df, ('provisionand write offof assets', 'provision and write off'))
            if generic:
                generic['statement'] = name
                break
        raison = "Pas de ligne nominative « provision for credit losses » / « credit impairment » dans les états Yahoo."
        if generic:
            raison += (
                f" Ligne générique trouvée et écartée : {generic['ligne']} "
                f"({generic['statement']}, {generic['periode']}, {generic['valeur']}) "
                "— pas spécifiquement le coût du risque crédit."
            )
        if loans:
            raison += f" Prêts disponibles : {loans['ligne']}={loans['valeur']} ({loans.get('statement')}, {loans['periode']})."
        out['sources']['cout_du_risque'] = {'manquant': True, 'raison': raison, 'prets': loans, 'ligne_generique_ecartee': generic}

    # Coefficient d'exploitation
    eff = None
    for name, df in frames.items():
        eff = _latest(df, EFFICIENCY_LABELS) or _lookup_contains(df, ('efficiency ratio',))
        if eff:
            v = eff['valeur']
            if v <= 1.5:  # parfois en fraction
                v = v * 100
            if 0 < v < 200:
                out['coefficient_exploitation'] = round(v, 2)
                out['sources']['coefficient_exploitation'] = {
                    **eff, 'statement': name, 'formule': 'ligne Yahoo Efficiency Ratio (ramenée en % si besoin)',
                }
                break
    if out['coefficient_exploitation'] is None:
        opex = rev = None
        for name, df in frames.items():
            if opex is None:
                opex = _latest(df, OPEX_LABELS)
                if opex:
                    opex['statement'] = name
            if rev is None:
                rev = _latest(df, REVENUE_LABELS)
                if rev:
                    rev['statement'] = name
        if opex and rev and rev['valeur']:
            v = opex['valeur'] / rev['valeur'] * 100
            out['coefficient_exploitation'] = round(v, 2)
            out['sources']['coefficient_exploitation'] = {
                'formule': 'Operating Expense / Total Revenue × 100 (Yahoo, même ordre de priorité des états)',
                'frais': opex, 'revenus': rev,
            }
        else:
            # somme des frais hors intérêt
            parts = {}
            rev2 = rev
            for name, df in frames.items():
                if df is None or getattr(df, 'empty', True):
                    continue
                for lab in df.index:
                    nl = _norm(lab)
                    if nl in NIE_PARTS and nl not in parts:
                        rec = _latest(df, (lab,))
                        if rec:
                            parts[nl] = {**rec, 'statement': name}
                if rev2 is None:
                    rev2 = _latest(df, REVENUE_LABELS)
                    if rev2:
                        rev2['statement'] = name
            # SG&A already includes marketing / G&A / salaries — only the four NIE_PARTS
            if parts and rev2 and rev2['valeur'] and 'selling general and administration' in parts:
                tot = sum(p['valeur'] for p in parts.values())
                v = tot / rev2['valeur'] * 100
                out['coefficient_exploitation'] = round(v, 2)
                out['sources']['coefficient_exploitation'] = {
                    'formule': (
                        '(Selling General And Administration + Occupancy And Equipment + '
                        'Professional Expense And Contract Services Expense + Other Non Interest Expense) '
                        '/ Total Revenue × 100. Les sous-lignes Marketing / G&A / Salaries ne sont pas '
                        'ajoutées (déjà dans le SG&A).'
                    ),
                    'postes': parts, 'revenus': rev2, 'somme_frais': tot,
                }
            else:
                out['sources']['coefficient_exploitation'] = {
                    'manquant': True,
                    'raison': (
                        "Pas de ligne Efficiency Ratio, pas de couple Operating Expense / Total Revenue, "
                        "et somme des frais hors intérêt incomplète."
                    ),
                    'postes_trouves': list(parts), 'revenus': rev2, 'opex': opex,
                }
    return out


def fetch_ticker(yahoo):
    import yfinance as yf
    t = yf.Ticker(yahoo)
    frames = {}
    for name in (
        'income_stmt', 'quarterly_income_stmt', 'financials', 'quarterly_financials',
        'balance_sheet', 'quarterly_balance_sheet', 'cashflow', 'quarterly_cashflow',
    ):
        try:
            df = getattr(t, name)
            if df is not None and not getattr(df, 'empty', True):
                frames[name] = df
        except Exception as e:
            frames[name + '_error'] = None
    rec = extract_from_frames({k: v for k, v in frames.items() if v is not None})
    rec['yahoo'] = yahoo
    rec['retrieved'] = datetime.now(PARIS).strftime('%Y-%m-%d %H:%M') + ' Europe/Paris'
    rec['source'] = 'Yahoo Finance (yfinance états financiers)'
    rec['statements_ok'] = [k for k, v in frames.items() if v is not None]
    return rec


def main(tickers):
    data = {'generated': datetime.now(PARIS).strftime('%Y-%m-%d %H:%M') + ' Europe/Paris', 'tickers': {}}
    if DEST.exists():
        try:
            data = json.loads(DEST.read_text())
            data.setdefault('tickers', {})
        except Exception:
            pass
    for tk in tickers:
        print('fetch', tk, flush=True)
        try:
            data['tickers'][tk] = fetch_ticker(tk)
            print('  cet1', data['tickers'][tk]['ratio_cet1'],
                  'cdr', data['tickers'][tk]['cout_du_risque'],
                  'coef', data['tickers'][tk]['coefficient_exploitation'], flush=True)
        except Exception as e:
            data['tickers'][tk] = {'yahoo': tk, 'erreur': f'{type(e).__name__}: {e}',
                                   'ratio_cet1': None, 'cout_du_risque': None,
                                   'coefficient_exploitation': None}
            print('  ERR', e, flush=True)
        DEST.write_text(json.dumps(data, ensure_ascii=False, indent=2, default=str) + '\n')
    print('wrote', DEST)
    return 0


if __name__ == '__main__':
    import sys
    tks = sys.argv[1:] or [
        'BNP.PA', 'GLE.PA', 'ACA.PA', 'CBK.DE', 'RY', 'CM', 'TD', 'BNS', 'EFGN.SW',
    ]
    raise SystemExit(main(tks))
