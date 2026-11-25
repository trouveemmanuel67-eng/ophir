#!/usr/bin/env python3
"""Ajoute le critère MM40 hebdo (0 à +30, à contre-courant) aux notes LONG existantes.

Idempotent : si le critère est déjà présent au barème +30, les points sont recalculés
et le total ajusté (ancien retirés, nouveaux ajoutés). Les métaux au comptant et les
cryptos conservent leur barème +125 (non retouchés). Épargne / monétaire et
immobilier résidentiel : non applicables (pas de cours hebdomadaire). SHORT exclu.
"""
from __future__ import annotations

import json
import os
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(os.environ.get('APEX_ROOT') or Path(__file__).resolve().parent.parent)
sys.path[:0] = [str(ROOT), str(ROOT / 'src')]

from apex.score import (  # noqa: E402
    mm40_hebdo_points, mm40_hebdo_texte, MM40_HEBDO_MAX_AUTRES, metaux_band, fmt10, round_half,
)
from apex.weekly_closes import weekly_closes  # noqa: E402

D = ROOT / 'data'
MIN, MAX = -50, 250
LABEL_AV = {'violet': 'Très faible', 'rouge': 'Faible', 'orange': 'Neutre', 'vert': 'Favorable', 'cyan': 'Très favorable'}

FILES = [
    'apex_achat_v2_pilot.json', 'apex_achat_v2_scores_full.json', 'apex_achat_v2_site.json',
    'apex_bars.json', 'energie.json', 'metaux.json', 'obligations.json', 'placements.json',
    'tabs_data.json', 'liquidites_etf_devises.json', 'secteurs.json', 'pays.json',
    'achatvente.json',
]

MM40_BIT = re.compile(r'(?: · )?MM40 hebdo(?: :[^·→]*| [+−\-]?\d+)')
TOTAL = re.compile(r'→\s+(-?−?\d+)\s*/\s*250')

STATS = Counter()
CHANGES = []  # (cat, key, avant, apres, pts, etat, raison)
NC = []


def _int(v):
    if v is None:
        return None
    if isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        return int(v)
    return int(str(v).replace('−', '-'))


def is_note(rec):
    """Uniquement une note APEX sur l'échelle −50 à 250 (pas un sous-critère /100)."""
    if not isinstance(rec, dict):
        return False
    v = rec.get('note', rec.get('total'))
    if not isinstance(v, (int, float)) or isinstance(v, bool):
        return False
    if rec.get('scale') == 250 or rec.get('v2') is True or rec.get('total_max') == 250:
        return True
    for t in (rec.get('ligne'), rec.get('display'),
              (rec.get('decomp') or {}).get('texte') if isinstance(rec.get('decomp'), dict) else None):
        if isinstance(t, str) and '/ 250' in t:
            return True
    return False


def is_moyenne(rec):
    if not isinstance(rec, dict):
        return False
    if rec.get('cap') == 'moyenne' or rec.get('n_moy'):
        return True
    det = rec.get('detail') or rec.get('decomp', {}).get('detail') if isinstance(rec.get('decomp'), dict) else rec.get('detail')
    if isinstance(det, str) and det.lower().startswith('moyenne'):
        return True
    return False


def is_epargne_or_immo(rec, ctx):
    if ctx.get('skip_classe') in ('epargne', 'immobilier'):
        return True
    dec = rec.get('decomp') or {}
    pts = dec.get('points') if isinstance(dec, dict) else {}
    if isinstance(pts, dict) and any(k in pts for k in ('Contexte taux', 'Fond. épargne', 'Contexte marché', 'Fond. immobilier')):
        return True
    txt = (rec.get('ligne') or '') + ' ' + ((dec.get('texte') if isinstance(dec, dict) else '') or '')
    if 'Fond. épargne' in txt or 'Contexte taux' in txt or 'Fond. immobilier' in txt or 'Contexte marché' in txt:
        return True
    return False


def already_125(rec, ctx):
    if ctx.get('kind') == 'spot' or ctx.get('classe') == 'crypto':
        return True
    det = None
    if isinstance(rec.get('detail'), dict):
        det = rec['detail'].get('mm40')
    dec = rec.get('decomp') if isinstance(rec.get('decomp'), dict) else {}
    if det is None:
        det = dec.get('mm40')
    if isinstance(det, dict) and det.get('max') == 125:
        return True
    return False


def current_mm40(rec):
    p = rec.get('points')
    if isinstance(p, dict) and isinstance(p.get('mm40'), (int, float)) and not isinstance(p.get('mm40'), bool):
        return int(p['mm40'])
    dec = rec.get('decomp') if isinstance(rec.get('decomp'), dict) else {}
    dp = dec.get('points') if isinstance(dec.get('points'), dict) else {}
    for k in ('mm40', 'MM40 hebdo'):
        if isinstance(dp.get(k), (int, float)) and not isinstance(dp.get(k), bool):
            return int(dp[k])
    for t in (rec.get('ligne'), dec.get('texte') if isinstance(dec, dict) else None):
        if not isinstance(t, str):
            continue
        m = re.search(r'MM40 hebdo :[^·→]*?([+−-]\d+)\s*pts', t)
        if m:
            return _int(m.group(1))
        m = re.search(r'MM40 hebdo ([+−-]?\d+)', t)
        if m:
            return _int(m.group(1))
    return None


def bind_ligne(txt, mm40_txt, total):
    if not isinstance(txt, str) or not txt:
        return txt
    if MM40_BIT.search(txt):
        txt = MM40_BIT.sub(' · ' + mm40_txt, txt)
    else:
        txt = TOTAL.sub(' · ' + mm40_txt + r'  →  \1 / 250', txt)
        if 'MM40 hebdo' not in txt:
            if '  →  ' in txt:
                txt = txt.replace('  →  ', ' · ' + mm40_txt + '  →  ', 1)
            else:
                txt = txt + ' · ' + mm40_txt
    txt = TOTAL.sub(f'→  {total} / 250', txt)
    return txt


def compute_mm40(rec, ctx):
    closes = []
    dec = rec.get('decomp') if isinstance(rec.get('decomp'), dict) else {}
    tech = dec.get('technique') if isinstance(dec.get('technique'), dict) else {}
    path = rec.get('weekly_path') or tech.get('source')
    if path == 'panier-reconstruit':
        path = None
    tv = rec.get('tv') or ctx.get('tv')
    yahoo = rec.get('yahoo') or rec.get('sym') or ctx.get('yahoo')
    ticker = rec.get('ticker') or rec.get('sym') or ctx.get('ticker')
    if ctx.get('classe') == 'devises' and ctx.get('ccy'):
        from apex.long250 import devise_weekly
        bars, pth = devise_weekly(ctx['ccy'])
        closes = [b['close'] for b in bars] if bars else []
        path = pth or path
    if not closes:
        closes = weekly_closes(tv, yahoo, ticker, path)
    return mm40_hebdo_points(closes, max_pts=MM40_HEBDO_MAX_AUTRES)


def patch_rec(rec, ctx):
    if not is_note(rec) or is_moyenne(rec) or is_epargne_or_immo(rec, ctx):
        return False
    tv = rec.get('tv') or ctx.get('tv') or ''
    if str(tv).startswith('APEX:PANIER') or rec.get('kind') == 'panier' or ctx.get('kind') == 'panier':
        STATS['paniers_saute'] += 1
        return False
    # n.c. sans barème déjà posé : ne pas recaler le total (évite de clipper un autre champ)
    if already_125(rec, ctx):
        STATS['conserve_125'] += 1
        return False
    pts, det = compute_mm40(rec, ctx)
    old = current_mm40(rec)
    before = int(round(float(rec.get('total', rec.get('note')))))
    if pts is None:
        if old is None:
            STATS['nc'] += 1
            NC.append({
                'tv': rec.get('tv') or ctx.get('tv'),
                'yahoo': rec.get('yahoo') or ctx.get('yahoo'),
                'nom': rec.get('nom') or rec.get('name') or rec.get('ticker'),
                'fichier': ctx.get('file'),
                'raison': (det or {}).get('raison') or 'série hebdomadaire absente',
            })
            return False
        new_total = before - (old or 0)
        etat = 'n.c.'
        raison = (det or {}).get('raison') or 'série hebdomadaire absente'
        mm40_txt = 'MM40 hebdo : —'
        STATS['nc'] += 1
        NC.append({
            'tv': rec.get('tv') or ctx.get('tv'),
            'yahoo': rec.get('yahoo') or ctx.get('yahoo'),
            'nom': rec.get('nom') or rec.get('name') or rec.get('ticker'),
            'fichier': ctx.get('file'),
            'raison': raison,
            'n': (det or {}).get('raison'),
        })
    else:
        new_total = before - (old or 0) + pts
        etat = 'applique'
        raison = None
        mm40_txt = (det or {}).get('texte') or mm40_hebdo_texte((det or {}).get('ecart'), pts)
        STATS['applique'] += 1
    new_total = max(MIN, min(MAX, int(new_total)))
    # points
    if isinstance(rec.get('points'), dict):
        rec['points']['mm40'] = pts
        rec['points']['total'] = new_total
    dec = rec.get('decomp')
    if not isinstance(dec, dict):
        rec['decomp'] = dec = {}
    if not isinstance(dec.get('points'), dict):
        dec['points'] = {}
    dec['points']['mm40'] = pts
    dec['points']['MM40 hebdo'] = pts
    if isinstance(dec['points'].get('total'), (int, float)):
        dec['points']['total'] = new_total
    dec['mm40'] = det
    if isinstance(rec.get('detail'), dict):
        rec['detail']['mm40'] = det
    for holder, fld in ((rec, 'ligne'), (dec, 'texte')):
        t = holder.get(fld)
        if isinstance(t, str) and t:
            holder[fld] = bind_ligne(t, mm40_txt, new_total)
    for f in ('total', 'note', 'pos', 'brut'):
        if isinstance(rec.get(f), (int, float)) and not isinstance(rec.get(f), bool):
            rec[f] = new_total
    disp = rec.get('display')
    if isinstance(disp, str):
        rec['display'] = f'{new_total} / 250' if '/' in disp else fmt10(new_total)
    b = metaux_band(new_total)
    if 'band' in rec:
        rec['band'] = b['id']
    if 'hex' in rec:
        rec['hex'] = b['hex']
    if 'flag' in rec:
        rec['flag'] = b['flag']
    if 'av_label' in rec:
        rec['av_label'] = LABEL_AV[b['id']]
    changed = new_total != before or old != pts
    if changed:
        STATS['modifiees'] += 1
        CHANGES.append({
            'cat': ctx.get('classe') or ctx.get('file'),
            'tv': rec.get('tv') or ctx.get('tv'),
            'nom': rec.get('nom') or rec.get('name') or rec.get('ticker') or rec.get('tv') or ctx.get('tv'),
            'avant': before,
            'apres': new_total,
            'delta': new_total - before,
            'mm40': pts,
            'etat': etat,
            'ecart_pct': (det or {}).get('ecart_pct'),
        })
    STATS['notes'] += 1
    return changed


def walk(obj, ctx):
    if isinstance(obj, dict):
        c = dict(ctx)
        if obj.get('tv'):
            c['tv'] = obj['tv']
        if obj.get('yahoo'):
            c['yahoo'] = obj['yahoo']
        if obj.get('ticker'):
            c['ticker'] = obj['ticker']
        if obj.get('kind'):
            c['kind'] = obj['kind']
        if obj.get('code') and (c.get('classe') == 'devises' or obj.get('quote_for')):
            c['ccy'] = obj.get('code') or obj.get('quote_for')
        # apex10 / apex10_panier / apex10_instrument
        for key in ('apex10', 'apex10_panier', 'apex10_instrument'):
            rec = obj.get(key)
            if is_note(rec):
                patch_rec(rec, c)
        # by_tv records are themselves notes
        if is_note(obj) and (isinstance(obj.get('points'), dict) or obj.get('ligne') or obj.get('ok') is True):
            if not any(k in obj for k in ('apex10', 'apex10_panier')):
                patch_rec(obj, c)
        for k, v in obj.items():
            cc = dict(c)
            if ctx.get('file') == 'tabs_data.json':
                if k == 'crypto':
                    cc['classe'] = 'crypto'
                    cc['skip_classe'] = 'crypto'
                elif k == 'apex_epargne':
                    cc['skip_classe'] = 'epargne'
                elif k == 'fx':
                    cc['classe'] = 'devises'
            if ctx.get('file') == 'placements.json':
                cc['skip_classe'] = 'epargne'
            if ctx.get('file') == 'achatvente.json' and k == 'immobilier':
                cc['skip_classe'] = 'immobilier'
            if ctx.get('file') == 'metaux.json':
                cc['classe'] = 'metaux'
            if k == 'etf_local':
                cc['classe'] = 'etf_devise'
            if isinstance(k, str) and ':' in k and k.split(':', 1)[0].isupper() and not (isinstance(v, dict) and v.get('tv')):
                cc['tv'] = k
            walk(v, cc)
    elif isinstance(obj, list):
        for v in obj:
            walk(v, ctx)


def avg_notes(vals):
    vals = [int(v) for v in vals if v is not None]
    if not vals:
        return None
    return int(round_half(sum(vals) / len(vals)))


def patch_moyenne(rec, notes, detail=None):
    if not isinstance(rec, dict) or not notes:
        return
    old = rec.get('note', rec.get('total'))
    avg = max(MIN, min(MAX, avg_notes(notes)))
    rec['note'] = avg
    rec['total'] = avg
    rec['pos'] = avg
    rec['n_moy'] = len(notes)
    if detail:
        rec['detail'] = detail
    b = metaux_band(avg)
    rec['hex'] = b['hex']
    rec['band'] = b['id']
    rec['flag'] = b['flag']
    rec['display'] = rec['display'] if isinstance(rec.get('display'), str) and '/' not in str(rec.get('display') or '') else f'{avg} / 250'
    if rec.get('display') and '/' not in str(rec['display']):
        rec['display'] = fmt10(avg)
    else:
        rec['display'] = f'{avg} / 250'
    if old != avg:
        STATS['moyennes'] += 1


def recalc_averages():
    """Recalcule les moyennes de lignes métaux (instruments visibles).

    Les autres paniers (obligations, énergie, secteurs, pays) sont laissés
    aux scripts qui les construisent : un recalcul naïf à partir des enfants
    peut écraser une moyenne déjà publiée si certains enfants n'ont pas
    le même historique de mise à jour.
    """
    from build_long250 import recalc_moyennes_metaux
    recalc_moyennes_metaux()



def sync_bars():
    """Recopie les notes 250 récemment patchées vers apex_bars quand le tv correspond."""
    # Les barres ont déjà été walkées. Rien de plus ici sauf énergie.
    try:
        from build_long250 import sync_bars_energie
        sync_bars_energie()
    except Exception as e:
        print('sync_bars_energie', e)


def main():
    (D / 'fond250').mkdir(exist_ok=True)
    for name in FILES:
        p = D / name
        if not p.exists():
            continue
        doc = json.loads(p.read_text(encoding='utf-8'))
        walk(doc, {'file': name})
        p.write_text(json.dumps(doc, ensure_ascii=False) + '\n', encoding='utf-8')
        print('mm40', name, 'ok')
    recalc_averages()
    sync_bars()
    # unique n.c. by tv
    seen = set()
    nc_uniq = []
    for row in NC:
        k = row.get('tv') or row.get('yahoo') or row.get('nom')
        if k in seen:
            continue
        seen.add(k)
        nc_uniq.append(row)
    journal = {
        'stats': dict(STATS),
        'changes': CHANGES,
        'nc': nc_uniq,
    }
    dest = D / 'fond250' / 'journal_mm40.json'
    dest.write_text(json.dumps(journal, ensure_ascii=False, indent=1), encoding='utf-8')
    print('notes', STATS['notes'], 'appliquees', STATS['applique'], 'nc', STATS['nc'],
          'conserve_125', STATS['conserve_125'], 'modifiees', STATS['modifiees'],
          'moyennes', STATS['moyennes'])
    # top 10 hausses (unique tv)
    uniq = {}
    for ch in CHANGES:
        k = ch.get('tv') or ch.get('nom')
        if not k:
            continue
        if k not in uniq or ch['delta'] > uniq[k]['delta']:
            uniq[k] = ch
    top = sorted(uniq.values(), key=lambda x: (-x['delta'], -(x['apres'] or 0)))[:10]
    print('top 10 hausses:')
    for ch in top:
        print(' ', ch.get('tv') or ch.get('nom'), ch['avant'], '->', ch['apres'], 'mm40', ch['mm40'], 'delta', ch['delta'])
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
