#!/usr/bin/env python3
"""APEX ACHAT −50 à 250 sur toutes les sections Actions du site
(USA 11 secteurs + France, Allemagne, Canada, Suisse).

Hors banque : apex_achat_v2.
Banques (industries Banks*, Savings Institutions) : apex_achat_v2_banque.
Assurances et autres financières : règles hors banque.
ETF / panier de section = moyenne des fondamentaux des 5 premières
actions du classement (top 5), chaque titre avec sa propre règle. Les rangs
suivants du top (6–10 aux USA, reste du top éligible en France) sont aussi
notés, même barème, sans entrer dans cette moyenne. Donnée manquante = 0, jamais inventée.
"""
from __future__ import annotations
import json, math, sys
from pathlib import Path

DIR = Path(__file__).resolve().parent
ROOT = DIR.parent
sys.path.insert(0, str(DIR))
sys.path.insert(0, str(ROOT))

import build_apex_achat_v2_pilot as P
import yahoo_week as YW

BANK_PREFIX = 'banks'
SAVINGS = ('savings institutions', 'savings & loans', 'savings and loans')


def is_bank(industry):
    if not industry:
        return False
    s = industry.strip().lower()
    if s.startswith(BANK_PREFIX):
        return True
    return s in SAVINGS or s.startswith('savings institutions')


def rules_of(industry):
    return P.FOND_RULES_BANQUE if is_bank(industry) else P.FOND_RULES


def regles_id(industry):
    return 'apex_achat_v2_banque' if is_bank(industry) else 'apex_achat_v2'


def load_bank_ratios():
    p = ROOT / 'data' / 'apex_achat_v2_banque_ratios.json'
    if not p.exists():
        return {}
    d = json.loads(p.read_text())
    return d.get('tickers') or {}


def merge_m(m, yahoo, ticker, ratios):
    m = dict(m or {})
    rec = ratios.get(yahoo or '') or ratios.get(ticker or '') or {}
    for k in ('ratio_cet1', 'cout_du_risque', 'coefficient_exploitation'):
        if rec.get(k) is not None and m.get(k) is None:
            m[k] = rec[k]
            m['_' + k + '_src'] = rec.get('sources', {}).get(k)
    return m


def compact_rec(rec):
    keep = (
        'id', 'ticker', 'tv', 'yahoo', 'nom', 'kind', 'ok', 'erreur',
        'date_cloture', 'close', 'points', 'ligne', 'total', 'total_max',
        'total_min', 'display', 'band', 'hex', 'av_label', 'regles',
        'industry', 'is_bank', 'watchlist_tv',
    )
    out = {k: rec[k] for k in keep if k in rec}
    # éléments fondamentaux résumés (utiles au contrôle, peu volumineux)
    det = ((rec.get('detail') or {}).get('fondamental') or {})
    elems = []
    for e in det.get('elements') or []:
        elems.append({
            'id': e.get('id'), 'label': e.get('label'), 'valeur': e.get('valeur'),
            'seuil': e.get('seuil'), 'ok': e.get('ok'), 'points': e.get('points'),
            'manquant': e.get('manquant'), 'moyenne_5': e.get('moyenne_5'),
            'n_bons': e.get('n_bons'), 'n_manquants': e.get('n_manquants'),
        })
    if elems or det.get('mode'):
        out['fond'] = {'points': det.get('points'), 'max': det.get('max') or 90,
                       'mode': det.get('mode'), 'elements': elems}
    cci = (rec.get('detail') or {}).get('cci') or {}
    if cci:
        out['cci'] = {'valeur': cci.get('valeur'), 'points': cci.get('points'), 'd': cci.get('d')}
    return out


def reconstruct_basket_bars(row):
    members = row.get('basket') or []
    series, weights = {}, {}
    for m in members:
        sym = m.get('symbol')
        if not sym:
            continue
        path = ROOT / 'data' / 'pays' / 'wk' / f'{sym}.json'
        if not path.exists():
            continue
        try:
            bars, _meta = YW.parse_yahoo_weekly(str(path), now=P.NOW)
        except Exception:
            continue
        closed = [b for b in bars if b.get('closed') and b.get('close') and b['close'] > 0]
        if len(closed) < 60:
            continue
        series[sym] = {b['date']: b['close'] for b in closed}
        weights[sym] = (m.get('w') or 0) / 100.0
    if len(series) < 3:
        return None
    tot_w = sum(weights.values()) or 1.0
    weights = {k: v / tot_w for k, v in weights.items()}
    dates = sorted({d for s in series.values() for d in s})
    lvl, out, prev = 100.0, [], None
    for d in dates:
        if prev is None:
            if sum(1 for s in series.values() if d in s) >= 3:
                out.append({'date': d, 'open': lvl, 'high': lvl, 'low': lvl, 'close': lvl, 'closed': True})
                prev = d
            continue
        av = [k for k, s in series.items() if d in s and prev in s]
        if len(av) >= 3:
            sw = sum(weights[k] for k in av)
            lvl *= sum(weights[k] * series[k][d] / series[k][prev] for k in av) / sw
            prev_close = out[-1]['close']
            out.append({
                'date': d, 'open': prev_close, 'high': max(prev_close, lvl),
                'low': min(prev_close, lvl), 'close': lvl, 'closed': True,
            })
            prev = d
    return out


def pack(section_id, section, etf_asset, actions, fg, sector_obj=None,
         closed_bars_etf=None, fond_etf_intro=''):
    # Moyenne ETF / panier : uniquement les 5 premières (règle inchangée).
    ETF_FOND_N = 5
    for a in actions:
        a['is_bank'] = is_bank(a.get('industry'))
        a['regles'] = regles_id(a.get('industry'))
    avg_actions = actions[:ETF_FOND_N] or actions
    action_fonds = []
    for a in avg_actions:
        tot, elems = P.fond_points(a.get('m'), rules_of(a.get('industry')))
        a['_fond_tot'], a['_fond_elems'] = tot, elems
        action_fonds.append((tot, elems, a))
    n = len(action_fonds) or 1
    avg_total = sum(t for t, _, _ in action_fonds) / n
    # moyenne par libellé : les règles peuvent différer (banque / hors banque)
    labels_order = []
    seen = set()
    for _, els, _ in action_fonds:
        for e in els:
            if e['id'] not in seen:
                seen.add(e['id'])
                labels_order.append((e['id'], e.get('label'), e.get('seuil')))
    etf_elems = []
    for eid, label, seuil in labels_order:
        vals, oks, manqs = [], [], []
        for _, els, _ in action_fonds:
            el = next((x for x in els if x['id'] == eid), None)
            if el is None:
                continue
            vals.append(el['points'])
            oks.append(el.get('ok'))
            manqs.append(el.get('manquant'))
        nn = len(vals) or 1
        rec = {
            'id': eid, 'label': label, 'seuil': seuil,
            'points': round(sum(vals) / nn, 1),
            'ok': None, 'moyenne_5': True,
            'n_bons': sum(1 for x in oks if x),
            'n_manquants': sum(1 for x in manqs if x),
            'n': nn,
        }
        etf_elems.append(rec)
    names = ', '.join(a.get('ticker') or a.get('nom') or '?' for a in avg_actions)
    etf_asset = {
        **etf_asset,
        'kind': etf_asset.get('kind') or 'etf',
        'fond_total': round(avg_total),
        'fond_elems': etf_elems,
        'fond_mode': (fond_etf_intro or (
            "Moyenne des {n} actions affichées ({names}). Chaque titre est noté avec "
            "sa règle (banque ou hors banque). L'instrument de section n'a pas de "
            "ratios d'émetteur ; donnée manquante = 0, rien n'est inventé."
        )).format(n=n, names=names),
        'is_bank': False,
        'regles': 'mixte' if len({a['regles'] for a in actions}) > 1 else (actions[0]['regles'] if actions else 'apex_achat_v2'),
    }
    if etf_asset.get('kind') == 'panier':
        ell_etf = ((sector_obj or {}).get('elliott') or {}).get('key')
    else:
        ell_etf = P.load_elliott_key(etf_asset.get('tv'), sector_obj)
    etf_score = P.score_asset(
        etf_asset, fg, elliott_key=ell_etf, closed_bars=closed_bars_etf,
    )
    if etf_asset.get('watchlist_tv'):
        etf_score['watchlist_tv'] = etf_asset['watchlist_tv']
    action_scores = [
        P.score_asset(a, fg, elliott_key=P.load_elliott_key(a.get('tv')), fond_rules=rules_of(a.get('industry')))
        for a in actions
    ]
    for rec, a in zip(action_scores, actions):
        rec['is_bank'] = a['is_bank']
        rec['regles'] = a['regles']
        rec['industry'] = a.get('industry')
    etf_score['regles'] = etf_asset['regles']

    manquantes = []
    for rec in action_scores:
        if not rec.get('ok'):
            manquantes.append({
                'tv': rec.get('tv'), 'nom': rec.get('nom'), 'section': section_id,
                'critere': 'serie_hebdo', 'label': 'Série hebdomadaire',
                'raison': rec.get('erreur') or 'scoring incomplet',
            })
            continue
        for e in (rec.get('detail') or {}).get('fondamental', {}).get('elements') or []:
            if e.get('manquant'):
                manquantes.append({
                    'tv': rec.get('tv'), 'nom': rec.get('nom'), 'ticker': rec.get('ticker'),
                    'section': section_id, 'critere': e['id'], 'label': e.get('label'),
                    'seuil': e.get('seuil'), 'points': 0, 'regles': rec.get('regles'),
                    'source': e.get('source') or 'donnée absente des fondamentaux en base (Yahoo Finance)',
                })
    out = {
        'generated': P.NOW.strftime('%Y-%m-%d %H:%M') + ' Europe/Paris',
        'pilot': True,
        'section': section,
        'secteur_sym': section_id,
        'etf_tv': etf_asset.get('tv'),
        'etf': etf_score,
        'actions': action_scores,
        'by_tv': {},
        'manquantes': manquantes,
        'n_banques': sum(1 for a in action_scores if a.get('is_bank')),
        'n_hors_banque': sum(1 for a in action_scores if not a.get('is_bank')),
    }
    for rec in [etf_score] + action_scores:
        if rec.get('tv'):
            out['by_tv'][rec['tv']] = rec
    return out


def collect_us(fond_all, secteurs, ratios):
    secs = []
    for sec in secteurs['sectors']:
        sym = sec['sym']
        sf = fond_all['sectors'][sym]
        # Top 10 du classement fondamental (l'ETF reste moyenné sur les 5 premières, voir pack).
        top = list((sf.get('top') or [])[:10])
        actions = []
        for r in top:
            yahoo = r.get('yahoo') or r['ticker']
            actions.append({
                'id': r['ticker'], 'ticker': r['ticker'], 'yahoo': yahoo,
                'tv': r['tv'], 'nom': r['name'], 'name': r['name'],
                'kind': 'action', 'industry': r.get('industry'),
                'm': merge_m(r.get('m'), yahoo, r['ticker'], ratios),
            })
        etf = sf.get('etf') or {}
        etf_meta = {
            'id': 'etf', 'ticker': etf.get('sym') or sec.get('tick'),
            'yahoo': sec.get('yahoo'), 'tv': etf.get('tv') or sec.get('tv'),
            'nom': etf.get('name') or sec.get('etf'),
            'kind': 'etf', 'watchlist_tv': sec.get('ref_us'),
        }
        secs.append({
            'id': sym, 'section': f"Actions USA – {sec.get('nom')}",
            'etf_meta': etf_meta, 'actions': actions, 'sector_obj': sec,
            'closed_bars_etf': None,
            'pays': 'USA', 'kind': 'etf',
        })
    return secs


def collect_pays(pays, ratios):
    secs = []
    for c in pays['countries']:
        for row in c.get('rows') or []:
            if not row.get('covered'):
                continue
            fond = row.get('fond') or {}
            # Tous les titres du top éligible (souvent > 5) ; moyenne du panier inchangée (5 premières).
            top = list(fond.get('top') or [])
            actions = []
            for r in top:
                yahoo = r.get('yahoo') or r.get('ticker')
                actions.append({
                    'id': r.get('ticker'), 'ticker': r.get('ticker'),
                    'yahoo': yahoo, 'tv': r.get('tv'),
                    'nom': r.get('name'), 'name': r.get('name'),
                    'kind': 'action', 'industry': r.get('industry'),
                    'm': merge_m(r.get('m'), yahoo, r.get('ticker'), ratios),
                })
            sid = f"{c['cc']}_{row['key']}"
            kind = row.get('kind') or 'basket'
            if kind == 'basket' or not row.get('tv'):
                bars = reconstruct_basket_bars(row)
                etf_meta = {
                    'id': 'panier', 'ticker': sid, 'yahoo': None,
                    'tv': f'APEX:PANIER-{c["cc"].upper()}-{row["key"].upper()}',
                    'nom': row.get('etf') or f"Panier APEX {row.get('nom')} · {c['nom']}",
                    'kind': 'panier', 'weekly_path': 'panier-reconstruit',
                }
                closed = bars
            else:
                etf_meta = {
                    'id': 'etf', 'ticker': row.get('sym'), 'yahoo': row.get('sym'),
                    'tv': row.get('tv'), 'nom': row.get('etf') or row.get('sym'),
                    'kind': kind,
                }
                closed = None
            secs.append({
                'id': sid, 'section': f"{c['nom']} – {row.get('nom')}",
                'etf_meta': etf_meta, 'actions': actions, 'sector_obj': row,
                'closed_bars_etf': closed, 'pays': c['nom'], 'kind': kind,
            })
    return secs


def main():
    fond_all = json.loads((ROOT / 'data' / 'fondamentaux.json').read_text())
    secteurs = json.loads((ROOT / 'data' / 'secteurs.json').read_text())
    pays = json.loads((ROOT / 'data' / 'pays.json').read_text())
    ratios = load_bank_ratios()
    fg = P.fetch_cnn_fng()
    print('F&G', fg.get('ok'), fg.get('value'), fg.get('points'), fg.get('date_valeur'), fg.get('erreur'))

    jobs = collect_us(fond_all, secteurs, ratios) + collect_pays(pays, ratios)
    pilotes, by_tv, manquantes = {}, {}, []
    n_ok = n_fail = 0
    for job in jobs:
        print('…', job['id'], job['section'], 'actions', len(job['actions']), flush=True)
        packed = pack(
            job['id'], job['section'], job['etf_meta'], job['actions'], fg,
            sector_obj=job['sector_obj'], closed_bars_etf=job['closed_bars_etf'],
        )
        packed['pays'] = job['pays']
        packed['kind'] = job['kind']
        pilotes[job['id']] = packed
        by_tv.update(packed.get('by_tv') or {})
        manquantes.extend(packed.get('manquantes') or [])
        recs = [packed['etf']] + packed['actions']
        n_ok += sum(1 for r in recs if r.get('ok'))
        n_fail += sum(1 for r in recs if not r.get('ok'))
        show = packed['etf']
        print(f"   ETF/panier {show.get('tv')} {show.get('display')} ok={show.get('ok')} {show.get('erreur') or ''}")
        for a in packed['actions']:
            tag = 'BANQUE' if a.get('is_bank') else 'hors-bq'
            print(f"   {a.get('tv')} {a.get('display')} {tag} fond={((a.get('points') or {}).get('fondamental'))} ok={a.get('ok')}")

    # fichier complet (détail) + fichier site compact
    full = {
        'generated': P.NOW.strftime('%Y-%m-%d %H:%M') + ' Europe/Paris',
        'pilot': True,
        'univers': 'actions_tous_pays_apex',
        'pays': ['USA', 'France', 'Allemagne', 'Canada', 'Suisse'],
        'classification_banque': (
            "Industries Yahoo commençant par « Banks » (Banks, Banks - Diversified, "
            "Banks - Regional, …) ou « Savings Institutions ». Les assurances, "
            "cartes (Credit Services), gestions d'actifs, bourses et capital markets "
            "sont traités en hors banque."
        ),
        'scale': {
            'min': P.SCALE_MIN, 'max': P.SCALE_MAX, 'tech_max': P.TECH_MAX,
            'fond_max': P.FOND_MAX, 'fg_abs': P.FG_ABS,
            'bandes': [{'id': n, 'de': lo, 'a': hi, 'hex': hx} for n, lo, hi, hx in P.PILOT_BANDS],
            'drapeaux_5': [
                {'id': 'violet', 'de': None, 'a': 14, 'regle': '< 14'},
                {'id': 'rouge', 'de': 14, 'a': 78, 'regle': '14 ≤ n < 78'},
                {'id': 'orange', 'de': 78, 'a': 142, 'regle': '78 ≤ n < 142'},
                {'id': 'vert', 'de': 142, 'a': 206, 'regle': '142 ≤ n < 206'},
                {'id': 'cyan', 'de': 206, 'a': None, 'regle': '≥ 206'},
            ],
        },
        'fear_greed': fg,
        'pilotes': pilotes,
        'secteurs_pilotes': list(pilotes),
        'by_tv': by_tv,
        'manquantes': manquantes,
        'stats': {'instruments_ok': n_ok, 'instruments_echec': n_fail, 'n_sections': len(pilotes)},
    }
    (ROOT / 'data' / 'apex_achat_v2_scores_full.json').write_text(
        json.dumps(full, ensure_ascii=False) + '\n'
    )
    compact_pilotes = {}
    compact_tv = {}
    for sid, p in pilotes.items():
        compact_pilotes[sid] = {
            'section': p['section'], 'secteur_sym': sid, 'pays': p.get('pays'),
            'etf': compact_rec(p['etf']),
            'actions': [compact_rec(a) for a in p['actions']],
            'n_banques': p.get('n_banques'), 'n_hors_banque': p.get('n_hors_banque'),
        }
        for rec in [p['etf']] + p['actions']:
            if rec.get('tv'):
                compact_tv[rec['tv']] = compact_rec(rec)
    site = {
        'generated': full['generated'],
        'pilot': True,
        # rétrocompat Communication (tests / anciens lecteurs)
        'secteur_sym': 'XLC',
        'section': pilotes['XLC']['section'],
        'etf': compact_rec(pilotes['XLC']['etf']),
        'actions': [compact_rec(a) for a in pilotes['XLC']['actions']],
        'univers': 'actions_tous_pays_apex',
        'scale': full['scale'],
        'fear_greed': fg,
        'pilotes': compact_pilotes,
        'secteurs_pilotes': list(pilotes),
        'by_tv': compact_tv,
        'stats': full['stats'],
    }
    dest = ROOT / 'data' / 'apex_achat_v2_pilot.json'
    dest.write_text(json.dumps(site, ensure_ascii=False) + '\n')
    print('wrote', dest, 'bytes', dest.stat().st_size)
    print('full', (ROOT / 'data' / 'apex_achat_v2_scores_full.json').stat().st_size)
    print('sections', len(pilotes), 'by_tv', len(compact_tv), 'ok', n_ok, 'fail', n_fail, 'manquantes', len(manquantes))
    return 0 if n_fail == 0 and fg.get('ok') else 2


if __name__ == '__main__':
    raise SystemExit(main())
