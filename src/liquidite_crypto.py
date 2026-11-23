"""Score de liquidité 0–100 pour les fiches crypto (23/11/2026).

Remplace le fondamental dans la note APEX /10. Plus de liquidité accumulée
non encore liquidée au-dessus du prix = signal d'achat ; plus en dessous =
signal de vente.

Source : saisie manuelle des cartes CoinAnk d'Emmanuel (les API officielles
CoinAnk Plan4 et CoinGlass Professional, qui donnent ces cartes en dollars,
sont payantes ; aucune API publique gratuite équivalente n'a été trouvée
le 23/11/2026). Les liquidations déjà exécutées (historiques) ne sont pas
ce que mesure cet indicateur.
"""
from __future__ import annotations
import os as _os
_APEX_ROOT = _os.path.abspath(_os.environ.get('APEX_ROOT') or _os.path.join(_os.path.dirname(__file__), '..'))
import json, os

B = _APEX_ROOT + '/data/'
PATH = B + 'crypto_liquidite.json'

# Pondération des horizons (1 an plus fort que 1 mois)
W_1Y, W_1M = 0.70, 0.30
# Écart max entre le prix de la capture et le prix APEX (clôture hebdo)
# au-delà duquel l'horizon n'entre pas dans le score (fenêtre non comparable)
STALE_PCT = 0.08
# Coefficients d'estimation, appliqués au pic chiffré de la même carte,
# uniquement quand le montant n'est pas lu sur la capture
COEF = {
    'plus_faibles': 0.20,   # bande « plus faible » que le pic jaune, par bande
    'visible': 0.20,        # bande visible, montant non chiffré
    'zone_large': 0.40,     # zone large non détaillée (ex. 2 000–3 500)
    'bande_fine': 0.10,
    'faible': 0.05,
    'presque_rien': 0.05,
}

# MSTR est une action, pas un contrat perps : pas de carte de liquidations
NO_MAP = {'mstr'}


def load(path=PATH):
    if not os.path.exists(path):
        return None
    return json.load(open(path))


def usd_fmt(x):
    if x is None:
        return 'n.c.'
    x = float(x)
    if abs(x) >= 1e9:
        v = x / 1e9
        s = f'{v:.2f}'.replace('.', ',').rstrip('0').rstrip(',')
        return f'{s} Md$'
    v = x / 1e6
    s = f'{v:.1f}'.replace('.', ',').rstrip('0').rstrip(',') if v < 10 else f'{v:.0f}'
    return f'{s} M$'


def _peak(bands):
    vals = [float(b['usd']) for b in bands or [] if b.get('usd') is not None]
    return max(vals) if vals else None


def _amount(band, peak):
    """Montant USD : valeur lue, ou estimation documentée, ou None."""
    if band.get('usd') is not None:
        return float(band['usd']), False
    kind = band.get('kind')
    if not kind or peak is None or kind not in COEF:
        return None, True
    return COEF[kind] * peak, True


def _side(band, price):
    lo = band.get('lo')
    hi = band.get('hi')
    role = band.get('role')
    if role in ('atm', 'consumed'):
        return role
    if lo is None or hi is None or price is None:
        return None
    if lo <= price <= hi:
        return 'atm'
    if hi < price:
        return 'below'
    if lo > price:
        return 'above'
    return None


def score_horizon(h, price):
    """s_h = 50 + 50*(A-B)/(A+B). Bande au prix ou déjà traversée exclue."""
    bands = (h or {}).get('bands') or []
    peak = _peak(bands)
    A = B = 0.0
    A_est = B_est = False
    sides = {'above': [], 'below': [], 'atm': [], 'consumed': [], 'unknown': []}
    missing = False
    for b in bands:
        side = _side(b, price)
        amt, est = _amount(b, peak)
        rec = {
            'label': b.get('label') or '',
            'lo': b.get('lo'), 'hi': b.get('hi'),
            'usd': amt, 'est': est,
            'role': side or b.get('role'),
        }
        if side in ('atm', 'consumed'):
            sides[side].append(rec)
            continue
        if side not in ('above', 'below'):
            sides['unknown'].append(rec)
            continue
        if amt is None:
            missing = True
            sides[side].append(rec)
            continue
        if side == 'above':
            A += amt
            A_est = A_est or est
        else:
            B += amt
            B_est = B_est or est
        sides[side].append(rec)
    if A + B <= 0:
        s = None if missing or not (sides['above'] or sides['below']) else 50.0
    else:
        s = 50.0 + 50.0 * (A - B) / (A + B)
    return {
        'score': None if s is None else round(s, 1),
        'above_usd': A, 'below_usd': B,
        'above_est': A_est, 'below_est': B_est,
        'peak_usd': peak,
        'sides': sides,
        'missing': missing,
    }


def blend(s1y, s1m):
    parts, wsum = [], 0.0
    if s1y is not None:
        parts.append((W_1Y, s1y)); wsum += W_1Y
    if s1m is not None:
        parts.append((W_1M, s1m)); wsum += W_1M
    if not parts:
        return None
    if len(parts) == 1:
        return parts[0][1]
    return round(sum(w * s for w, s in parts) / wsum, 1)


def stale(capture_price, ref_price, pct=STALE_PCT):
    if capture_price is None or ref_price is None or ref_price <= 0:
        return False
    return abs(float(capture_price) - float(ref_price)) / float(ref_price) > pct


def for_asset(asset, db=None):
    """Calcule le bloc liquidite d'une fiche (clé btc/eth/xrp/sol/mstr)."""
    key = (asset or {}).get('key')
    price = (asset or {}).get('close')
    base = {
        'score': None, 'above_usd': None, 'below_usd': None,
        'above_est': False, 'below_est': False,
        'used': [], 'ignored': [], 'horizons': {},
        'source': None, 'comment': None,
    }
    if key in NO_MAP:
        base['comment'] = (
            "Strategy (MSTR) est une action, pas un contrat à terme perpétuel : "
            "pas de carte de liquidités accumulées. La note /10 reste sur le timing seul."
        )
        return base
    db = db if db is not None else load()
    if not db:
        base['comment'] = "Fichier de saisie de liquidité introuvable."
        return base
    base['source'] = db.get('source')
    rec = (db.get('assets') or {}).get(key)
    if not rec:
        base['comment'] = (
            "Pas de saisie CoinAnk pour cet actif : la note /10 reste sur le timing seul, "
            "sans score de liquidité (en attente d'une carte 1 an ou 1 mois)."
        )
        return base

    scores = {}
    tot_A = tot_B = 0.0
    tot_Ae = tot_Be = False
    w_used = {}
    for hid, label, w in (('1y', '1 an', W_1Y), ('1m', '1 mois', W_1M)):
        h = (rec.get('horizons') or {}).get(hid)
        if not h:
            continue
        cap_px = h.get('capture_price')
        ignored = None
        if stale(cap_px, price):
            ignored = (
                f"Carte {label} non retenue dans le score : le prix de la capture "
                f"({usd_price(cap_px)}) s'écarte de plus de {int(STALE_PCT*100)} % "
                f"du prix APEX de référence ({usd_price(price)}), la fenêtre n'est pas comparable."
            )
        calc = score_horizon(h, price if not ignored else cap_px)
        calc['label'] = label
        calc['capture_price'] = cap_px
        calc['capture_note'] = h.get('capture_price_note')
        calc['used'] = not ignored and calc.get('score') is not None
        if ignored:
            calc['ignored_why'] = ignored
            base['ignored'].append({'horizon': hid, 'why': ignored})
        base['horizons'][hid] = calc
        if calc['used']:
            scores[hid] = calc['score']
            base['used'].append(hid)
            # totaux affichés = somme des horizons retenus (pas un mélange 70/30 des montants)
            # Pour l'affichage tête de fiche : on expose aussi le blend des scores.
            w_used[hid] = w
            tot_A += calc['above_usd']
            tot_B += calc['below_usd']
            tot_Ae = tot_Ae or calc['above_est']
            tot_Be = tot_Be or calc['below_est']

    # Montants affichés en tête : horizon 1 an s'il est retenu, sinon 1 mois,
    # et totaux additionnés si les deux le sont (même unité, juste un cumul informatif)
    if '1y' in scores and '1m' in scores:
        # pondération des montants identique à celle des scores, pour un seul couple dessus/dessous
        A = W_1Y * base['horizons']['1y']['above_usd'] + W_1M * base['horizons']['1m']['above_usd']
        B = W_1Y * base['horizons']['1y']['below_usd'] + W_1M * base['horizons']['1m']['below_usd']
        base['above_usd'] = A
        base['below_usd'] = B
        base['above_est'] = tot_Ae
        base['below_est'] = tot_Be
    elif '1y' in scores:
        h = base['horizons']['1y']
        base['above_usd'] = h['above_usd']
        base['below_usd'] = h['below_usd']
        base['above_est'] = h['above_est']
        base['below_est'] = h['below_est']
    elif '1m' in scores:
        h = base['horizons']['1m']
        base['above_usd'] = h['above_usd']
        base['below_usd'] = h['below_usd']
        base['above_est'] = h['above_est']
        base['below_est'] = h['below_est']

    base['score'] = blend(scores.get('1y'), scores.get('1m'))
    if base['score'] is None and not base['comment']:
        base['comment'] = "Aucun horizon utilisable pour le score de liquidité."
    elif base['score'] is not None:
        bits = []
        if '1y' in scores and '1m' in scores:
            bits.append(
                f"Score 70 % carte 1 an ({_fmt_sc(scores['1y'])}) + 30 % carte 1 mois ({_fmt_sc(scores['1m'])})."
            )
        elif '1y' in scores:
            bits.append("Score porté par la seule carte 1 an (pas de carte 1 mois retenue).")
        elif '1m' in scores:
            bits.append("Score porté par la seule carte 1 mois (pas de carte 1 an).")
        base['comment'] = ' '.join(bits + [x['why'] for x in base['ignored']])
    return base


def _fmt_sc(s):
    if s is None:
        return '–'
    return f'{s:.1f}'.replace('.', ',').rstrip('0').rstrip(',') if s != int(s) else str(int(s))


def usd_price(p):
    if p is None:
        return 'n.d.'
    p = float(p)
    if p >= 1000:
        return f'{p:,.0f}'.replace(',', ' ') + ' $'
    if p >= 2:
        return f'{p:.2f}'.replace('.', ',') + ' $'
    return f'{p:.4f}'.replace('.', ',') + ' $'


if __name__ == '__main__':
    db = load()
    # contrôles de la formule, indépendants des saisies
    h = {'bands': [
        {'lo': 100, 'hi': 110, 'usd': 80, 'role': 'atm'},
        {'lo': 120, 'hi': 130, 'usd': 70},
        {'lo': 50, 'hi': 60, 'usd': 30},
    ]}
    r = score_horizon(h, 105)
    assert r['above_usd'] == 70 and r['below_usd'] == 30
    assert abs(r['score'] - 70) < 0.05, r
    assert blend(75, 100) == 82.5
    assert blend(75, None) == 75
    assert stale(72000, 61271)
    assert not stale(61500, 61271)
    print('formule ok')
    if db:
        demo = [
            {'key': 'btc', 'close': 61271.08},
            {'key': 'eth', 'close': 1724.33},
            {'key': 'xrp', 'close': 0.9274},
            {'key': 'sol', 'close': 70.57},
            {'key': 'mstr', 'close': 77.8},
        ]
        for a in demo:
            L = for_asset(a, db)
            print(a['key'], 'score', L['score'],
                  'dessus', usd_fmt(L['above_usd']), 'dessous', usd_fmt(L['below_usd']),
                  'used', L['used'])
