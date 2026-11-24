#!/usr/bin/env python3
"""t506u : plus aucune note hors de l'échelle unique −50..250 dans les données du site.

1. Note 250 réelle (grille actions) pour la tête « Marché France » (ETF CAC 40, EURONEXT:CAC)
   et pour Fanuc (TSE:6954, position FUC hors univers) : apex_achat_v2_pilot.json et scores_full, by_tv.
   CAC : technique de l'ETF ; fondamental et H = moyenne des actions France affichées (même règle
   que les ETF et paniers de section). Fanuc : ratios Yahoo déjà en base (data/pays/qs), H n.c.
2. Remplace chaque ancienne note /100 encore stockée (secteurs.json, pays.json France,
   achatvente.json, apex_bars.json, tabs_data.json) par la note 250 du même actif, ou par la
   moyenne 250 de la section. Une note /100 sans équivalent 250 est retirée (non affichée).
Aucune collecte : uniquement des données déjà en base.
"""
import json, os, sys
from pathlib import Path
ROOT = Path(os.environ.get('APEX_ROOT') or Path(__file__).resolve().parent.parent)
sys.path[:0] = [str(ROOT), str(ROOT / 'src')]
D = ROOT / 'data'
import build_apex_achat_v2_pilot as P  # noqa: E402
import apply_attention as AA  # noqa: E402
from apex.score import metaux_band  # noqa: E402

LOG = []


def load(n):
    return json.loads((D / n).read_text(encoding='utf-8'))


def save(n, d, indent=None):
    (D / n).write_text(json.dumps(d, ensure_ascii=False, indent=indent) + '\n', encoding='utf-8')


def is250(a):
    return isinstance(a, dict) and (a.get('scale') == 250 or a.get('total_max') == 250 or a.get('v2') is True)


FLAG = {'violet': 'purple', 'rouge': 'red', 'orange': 'orange', 'vert': 'green', 'cyan': 'cyan'}


def from_pilot(r, cap='apex_achat_v2'):
    t = int(r['total'])
    b = metaux_band(t)
    return {'note': t, 'display': str(t), 'total': t, 'total_min': -50, 'total_max': 250, 'scale': 250, 'v2': True,
            'hex': b['hex'], 'band': b['id'], 'flag': b['flag'], 'pos': t, 'cap': cap,
            'ligne': r.get('ligne') or '', 'decomp': {'texte': r.get('ligne') or '', 'echelle': 250}}


def avg_rec(notes, detail, label):
    notes = [float(x) for x in notes if x is not None]
    if not notes:
        return None
    n = int(round(sum(notes) / len(notes)))
    b = metaux_band(n)
    return {'note': n, 'display': str(n), 'total': n, 'total_min': -50, 'total_max': 250, 'scale': 250, 'v2': True,
            'hex': b['hex'], 'band': b['id'], 'flag': b['flag'], 'pos': n, 'cap': 'moyenne', 'n_moy': len(notes),
            'detail': detail, 'ligne': f'moyenne de {len(notes)} {label}  →  {n} / 250'}


# ------------------------------------------------------------------ 1. CAC 40 et Fanuc
def qsget(sym):
    """Ratios Yahoo déjà en base (data/pays/qs, même calcul que src/build_pays.py), sans collecte."""
    p = D / 'pays' / 'qs' / f'{sym}.json'
    if not p.exists():
        return None
    j = json.loads(p.read_text(encoding='utf-8'))
    q = j.get('qs')
    if not q:
        return None
    raw = lambda v: v.get('raw') if isinstance(v, dict) else v
    g = lambda m, k: raw((q.get(m) or {}).get(k))
    fd = lambda k: g('financialData', k)
    tr = {t.get('period'): t for t in ((q.get('earningsTrend') or {}).get('trend') or [])}

    def eg(per):
        e = (tr.get(per) or {}).get('earningsEstimate') or {}
        gr, base = raw(e.get('growth')), raw(e.get('yearAgoEps'))
        return None if gr is None or base is None or base <= 0 else gr * 100

    def rg(per):
        e = (tr.get(per) or {}).get('revenueEstimate') or {}
        gr = raw(e.get('growth'))
        return None if gr is None else gr * 100
    rev, eb = fd('totalRevenue'), fd('ebitda')
    pc = lambda x: None if x is None else x * 100
    m = {'nd_ebitda': ((fd('totalDebt') or 0) - (fd('totalCash') or 0)) / eb if eb and eb > 0 and fd('totalDebt') is not None else None,
         'op_margin': pc(fd('operatingMargins')), 'fcf_margin': (fd('freeCashflow') / rev * 100) if fd('freeCashflow') is not None and rev else None,
         'roe': pc(fd('returnOnEquity')), 'current': fd('currentRatio'),
         'eps_0y': eg('0y'), 'eps_1y': eg('+1y'), 'rev_0y': rg('0y'), 'rev_1y': rg('+1y')}
    return {'m': m, 'retrieved': j.get('retrieved')}


def score_special(pil):
    fg = P.fetch_cnn_fng()
    acts = [a for sid, p in (pil.get('pilotes') or {}).items() if str(sid).startswith('fr_')
            for a in (p.get('actions') or []) if a.get('ok') and isinstance(a.get('points'), dict)]
    out = {}
    if acts:
        fonds = [int(a['points'].get('fondamental') or 0) for a in acts]
        hs = [a['points'].get('hype') for a in acts if a['points'].get('hype') is not None]
        fo = int(round(sum(fonds) / len(fonds)))
        h = AA._rnd(sum(hs) / len(hs)) if hs else None
        asset = {'tv': 'EURONEXT:CAC', 'yahoo': 'CAC.PA', 'ticker': 'CAC', 'nom': 'Marché France · ETF CAC 40 (Amundi, CAC.PA)',
                 'kind': 'etf', 'fond_total': 0, 'fond_elems': [], 'regles': 'apex_achat_v2'}
        rec = P.score_asset(asset, fg)
        if rec.get('ok'):
            att = {'valeur': None, 'H': h, 'n': len(hs), 'n_affichees': len(acts),
                   'precision': f'Moyenne arrondie des H des {len(hs)} actions France affichées (mêmes titres que le fondamental)'}
            AA.apply_rec(rec, h, att, fo)
            rec['tete_pays'] = 'France'
            rec['fond_mode'] = (f'Fondamental = moyenne des {len(fonds)} actions France affichées dans les 11 paniers '
                                '(9 critères × 9 points chacune) ; l’ETF n’a pas de ratios d’émetteur.')
            out['EURONEXT:CAC'] = rec
            LOG.append(('CAC', rec['ligne']))
        else:
            LOG.append(('CAC', 'n.c. : ' + str(rec.get('erreur'))))
    # Fanuc : position FUC (Xetra) notée sur sa cotation de Tokyo
    q = qsget('6954.T')
    m = (q or {}).get('m') or {}
    asset = {'tv': 'TSE:6954', 'yahoo': '6954.T', 'ticker': '6954', 'nom': 'Fanuc Corporation', 'kind': 'action',
             'm': m, 'regles': 'apex_achat_v2'}
    rec = P.score_asset(asset, fg, fond_rules=P.FOND_RULES)
    if rec.get('ok'):
        AA.apply_rec(rec, None, {'valeur': None, 'H': None,
                                 'precision': 'Pas de mesure d’attention W48 pour Fanuc (collecte Trends non relancée) : H non compté.'})
        rec['hors_univers_position'] = 'FUC (Xetra) · fiche Tokyo 6954'
        rec['fond_source'] = f"Yahoo Finance quoteSummary 6954.T relevé {(q or {}).get('retrieved')}"
        out['TSE:6954'] = rec
        LOG.append(('FUC', rec['ligne']))
    else:
        LOG.append(('FUC', 'n.c. : ' + str(rec.get('erreur'))))
    return out


def inject_special():
    pil = load('apex_achat_v2_pilot.json')
    sp = score_special(pil)
    for name in ('apex_achat_v2_pilot.json', 'apex_achat_v2_scores_full.json'):
        p = D / name
        if not p.exists():
            continue
        doc = pil if name == 'apex_achat_v2_pilot.json' else load(name)
        doc.setdefault('by_tv', {}).update(json.loads(json.dumps(sp)))
        if name == 'apex_achat_v2_scores_full.json':
            # Fanuc : alias Xetra de la position
            if 'TSE:6954' in sp:
                doc['by_tv']['XETR:FUC'] = json.loads(json.dumps(sp['TSE:6954']))
        else:
            if 'TSE:6954' in sp:
                doc['by_tv']['XETR:FUC'] = json.loads(json.dumps(sp['TSE:6954']))
        save(name, doc)
    return pil


# ------------------------------------------------------------------ 2. carte tv → note 250
def note_map(pil):
    M = {}
    for tv, r in (pil.get('by_tv') or {}).items():
        if r.get('ok') and r.get('total') is not None:
            M[tv] = from_pilot(r)
    for sid, p in (pil.get('pilotes') or {}).items():
        e = p.get('etf') or {}
        if e.get('ok') and e.get('total') is not None:
            if e.get('tv'):
                M[e['tv']] = from_pilot(e)
            M['__sid__' + sid] = from_pilot(e)
        for a in p.get('actions') or []:
            if a.get('ok') and a.get('total') is not None and a.get('tv'):
                M.setdefault(a['tv'], from_pilot(a))

    def take(tv, a):
        if tv and is250(a) and a.get('note') is not None and a.get('cap') != 'moyenne':
            M.setdefault(tv, a)
    mt = load('metaux.json')
    for r in mt.get('rows') or []:
        ml = r.get('mlist') or {}
        for it in [ml.get('head')] + list(ml.get('items') or []):
            if it:
                take(it.get('tv'), it.get('apex10'))
                take(it.get('ticker'), it.get('apex10'))
    T = load('tabs_data.json')
    for a in (T.get('energie') or {}).get('assets') or []:
        take(a.get('tv'), a.get('apex10')); take(a.get('yahoo'), a.get('apex10'))
    for a in (((T.get('crypto') or {}).get('fiches') or {}).get('assets') or []):
        take(a.get('tv'), a.get('apex10')); take(a.get('sym'), a.get('apex10'))
    for a in (((T.get('liquidites') or {}).get('fx') or {}).get('assets') or []):
        take(a.get('tv'), a.get('apex10'))
        e = a.get('etf_local') or {}
        take(e.get('tv'), e.get('apex10'))
    O = load('obligations.json')
    for s in O.get('segments') or []:
        take(s.get('tv'), s.get('apex10'))
        for r in s.get('list') or []:
            take(r.get('tv'), r.get('apex10')); take(r.get('yahoo'), r.get('apex10'))
    return M, T


def fix(obj, key, rec, where):
    old = (obj.get(key) or {}).get('note') if isinstance(obj.get(key), dict) else None
    if rec is None:
        if obj.get(key) is not None:
            obj[key] = {'note': None, 'display': '–', 'scale': 250, 'total': None, 'total_min': -50, 'total_max': 250,
                        'cap': 'nc', 'detail': 'Ancienne note /100 retirée (t506u) : pas encore de note −50 à 250 pour cet actif.'}
            LOG.append((where, f'{old} /100 → retirée'))
        return
    obj[key] = json.loads(json.dumps(rec))
    LOG.append((where, f'{old} /100 → {rec.get("note")} / 250'))


def harmonise(pil):
    M, T = note_map(pil)
    pilotes = pil.get('pilotes') or {}
    # secteurs USA
    S = load('secteurs.json')
    tots = []
    for s in S.get('sectors') or []:
        r = M.get('__sid__' + str(s.get('sym'))) or M.get(s.get('tv'))
        if r:
            tots.append(r['note'])
        for k in ('apex10', 'apex10_instrument'):
            if s.get(k) is not None and not is250(s.get(k)):
                fix(s, k, r, f"secteurs {s.get('sym')} {k}")
    if not is250(S.get('apex10')):
        fix(S, 'apex10', avg_rec(tots, 'Moyenne des notes −50 à 250 des ETF de secteur USA.', 'secteurs'), 'secteurs global')
    save('secteurs.json', S)
    # pays (France)
    PJ = load('pays.json')
    for C in PJ.get('countries') or []:
        if C.get('nom') != 'France' and C.get('cc') not in ('fr',):
            continue
        tots = []
        for s in C.get('rows') or []:
            r = M.get('__sid__fr_' + str(s.get('key'))) or M.get(s.get('tv'))
            if r:
                tots.append(r['note'])
            for k in ('apex10', 'apex10_panier'):
                if s.get(k) is not None and not is250(s.get(k)):
                    fix(s, k, r, f"pays France {s.get('key')} {k}")
            f = s.get('fond') or {}
            for it in f.get('top') or []:
                if it.get('apex10') is not None and not is250(it.get('apex10')):
                    fix(it, 'apex10', M.get(it.get('tv')), f"pays France fond {it.get('tv')}")
        h = C.get('head') or {}
        if h and not is250(h.get('apex10')):
            fix(h, 'apex10', M.get(h.get('tv')), 'pays France tête CAC 40')
        if not is250(C.get('apex10')):
            fix(C, 'apex10', avg_rec(tots, 'Moyenne des notes −50 à 250 des 11 paniers de section France.', 'paniers'), 'pays France moyenne')
    save('pays.json', PJ)
    # achatvente : bandeaux de section
    AV = load('achatvente.json')
    us = [M['__sid__' + k]['note'] for k in pilotes if str(k).startswith('XL') and '__sid__' + k in M]
    cr = [a['apex10']['note'] for a in (((T.get('crypto') or {}).get('fiches') or {}).get('assets') or [])
          if is250(a.get('apex10')) and a['apex10'].get('note') is not None and str(a.get('key')).lower() != 'xrp']
    fx = [a['apex10']['note'] for a in (((T.get('liquidites') or {}).get('fx') or {}).get('assets') or [])
          if is250(a.get('apex10')) and a['apex10'].get('note') is not None and not a.get('repere')]
    src = {'actions': (us, 'Moyenne des notes −50 à 250 des ETF de secteur USA.', 'secteurs'),
           'crypto': (cr, 'Moyenne des notes −50 à 250 des cryptos affichées (hors XRP).', 'cryptos'),
           'liquidites': (fx, 'Moyenne des notes −50 à 250 des devises affichées.', 'devises')}
    for k, v in AV.items():
        if isinstance(v, dict) and v.get('apex10') is not None and not is250(v.get('apex10')):
            notes, det, lab = src.get(k, ([], '', ''))
            fix(v, 'apex10', avg_rec(notes, det, lab), f'achatvente {k}')
    save('achatvente.json', AV)
    # apex_bars : toutes les barres individuelles sur 250
    B = load('apex_bars.json')
    n_rep = n_ret = 0
    # t507u : un seul ETC par métal ; les ETC retirés (non détenus) quittent aussi apex_bars
    mt = load('metaux.json')
    for r in mt.get('rows') or []:
        for i in ((r.get('mlist') or {}).get('etc_retires') or []):
            if i.get('tv') and not i.get('detenu') and i['tv'] in (B.get('bars') or {}):
                B['bars'].pop(i['tv'])
                LOG.append(('apex_bars', f"ETC retiré {i['tv']} (un seul ETC par métal)"))
    for key, b in (B.get('bars') or {}).items():
        r = M.get(key)
        a = b.get('apex10')
        if r is not None:
            if not is250(a) or a.get('note') != r.get('note'):
                b['apex10'] = json.loads(json.dumps(r)); n_rep += 1
        elif str(b.get('apex10_retire') or '').startswith('ancienne note /100'):
            b['apex10_retire'] = 'ancienne note retirée (t506u, échelle unique −50 à 250) : titre hors univers USA / France, non affiché'
        elif a is not None and not is250(a):
            b.pop('apex10', None)
            b['apex10_retire'] = 'ancienne note retirée (t506u, échelle unique −50 à 250) : titre hors univers USA / France, non affiché'
            n_ret += 1
    B['apex10_t506u'] = f'{n_rep} barres alignées sur la note −50 à 250, {n_ret} anciennes notes /100 retirées (hors univers)'
    LOG.append(('apex_bars', B['apex10_t506u']))
    save('apex_bars.json', B)
    # tabs_data : tout objet apex10 restant hors 250
    def walk(o, path):
        if isinstance(o, dict):
            for k in ('apex10', 'apex10_instrument'):
                a = o.get(k)
                if isinstance(a, dict) and a.get('note') is not None and not is250(a):
                    fix(o, k, M.get(o.get('tv')) or M.get(o.get('sym')), f'tabs_data {path} {o.get("tv") or o.get("sym") or ""}')
            for k, v in o.items():
                if k not in ('apex10', 'apex10_instrument'):
                    walk(v, path + '.' + k)
        elif isinstance(o, list):
            for i, v in enumerate(o):
                walk(v, path)
    walk(T, 'tabs')
    save('tabs_data.json', T)


TXT = {
    'la note /100 reste sur le timing seul, sans score de liquidité': 'la liquidité compte 0 sur 45 dans la note −50 à 250, sans redistribution',
    'La note /100 reste sur le timing seul.': 'La liquidité compte 0 sur 45 dans la note −50 à 250, sans redistribution.',
}


def textes():
    for fn in ('tabs_data.json', 'crypto_fiches.json'):
        p = D / fn
        if not p.exists():
            continue
        raw = p.read_text(encoding='utf-8')
        new = raw
        for a, b in TXT.items():
            new = new.replace(a, b)
        if new != raw:
            p.write_text(new, encoding='utf-8')
            LOG.append((fn, 'textes /100 de la liquidité crypto reformulés'))


def retraits():
    """t509 (24/11/2026) : produits introuvables chez Revolut et XTB retirés de tout le site (config/retraits_site.json)."""
    cfgp = ROOT / 'config' / 'retraits_site.json'
    if not cfgp.exists():
        return
    cfg = json.loads(cfgp.read_text(encoding='utf-8'))
    R = cfg.get('retires') or {}
    # Obligations : segment dont l'ETF de référence est retiré -> carte « taux, repère de marché » (renderSegments)
    O = load('obligations.json')
    keep = []
    for s in O.get('segments') or []:
        if s.get('tv') in R:
            O.setdefault('removed_notes', {})[s.get('pays') or s.get('key')] = (cfg.get('removed_notes') or {}).get(s.get('pays') or s.get('key')) or R[s['tv']]
            LOG.append(('obligations', f"segment {s.get('key')} retiré ({s['tv']}, introuvable Revolut/XTB)"))
            continue
        s['list'] = [x for x in (s.get('list') or []) if x.get('tv') not in R]
        keep.append(s)
    O['segments'] = keep
    save('obligations.json', O)
    # ETF par devise (Liquidités) : ETF local retiré
    T = load('tabs_data.json')
    for a in ((T.get('liquidites') or {}).get('fx') or {}).get('assets') or []:
        e = a.get('etf_local') or {}
        if e.get('tv') in R:
            a['etf_local'] = {'ccy': e.get('ccy'), 'ok': False, 'nom': None, 'tv': None, 'indispo': True,
                              'raison': f"Le meilleur ETF 3 ans en {a.get('sym')} n'est disponible ni chez Revolut ni chez XTB : retiré d'APEX le 24/11/2026."}
            LOG.append(('tabs_data', f"ETF par devise {a.get('sym')} : {e['tv']} retiré (introuvable Revolut/XTB)"))
    save('tabs_data.json', T)
    # Barres individuelles
    B = load('apex_bars.json')
    for tv in list((B.get('bars') or {}).keys()):
        if tv in R:
            B['bars'].pop(tv)
            LOG.append(('apex_bars', f"{tv} retiré (introuvable Revolut/XTB)"))
    save('apex_bars.json', B)


def main():
    pil = inject_special()
    retraits()
    harmonise(pil)
    textes()
    (D / 'fond250').mkdir(exist_ok=True)
    (D / 'fond250' / 'harmonise250_t506u.json').write_text(json.dumps(LOG, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    for w, t in LOG[:400]:
        print(w, '·', t)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
