"""Calcul unique de la note APEX /10 (t329u).

Lit config/regles.json. Note = 50 % fondamental + 50 % technique
(Elliott, structure, Fibonacci, figure, RSI, MACD, CCI). Sans fondamental,
le technique est renormalisé à 100 %. Les bonus Elliott ne s'appliquent
que sur un comptage manuel. Une note ≥ 8 exige un AV Achat fort et une
confirmation. Les couleurs découlent uniquement de la note affichée.
"""
from __future__ import annotations
import sys
from pathlib import Path

from . import paths
from .config import regles as load_regles

# flags_couleur reste le module d'affichage (mêmes bornes que config/regles.json)
_SRC = str(paths.src_dir())
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)
import flags_couleur as FC  # noqa: E402


def _R():
    return load_regles()


def av_pos(av, lo=None, hi=None):
    r = _R()['note_apex']
    lo = r['av_lo'] if lo is None else lo
    hi = r['av_hi'] if hi is None else hi
    x = max(float(lo), min(float(hi), float(av)))
    return (x - float(lo)) / (float(hi) - float(lo)) * 100.0


def round_half(x, pas=None):
    pas = pas or _R()['note_apex']['arrondi']
    inv = 1.0 / float(pas)
    return round(float(x) * inv) / inv


def fmt10(n):
    if n is None:
        return '–'
    x = round_half(n)
    if abs(x - int(x)) < 1e-9:
        return str(int(x))
    return str(x).replace('.', ',')


def elliott_key_of(ell):
    if not ell:
        return None
    if isinstance(ell, str):
        return ell
    if isinstance(ell, dict):
        return ell.get('key')
    return None


def elliott_fiable(ell):
    """True uniquement pour un override / comptage manuel."""
    if not isinstance(ell, dict):
        return False
    return bool(ell.get('manuel') or ell.get('override') or ell.get('source') == 'manuel')


def divergence_haussiere(div):
    if div is None:
        return False
    if isinstance(div, dict):
        n = div.get('note')
        if n is None and div.get('haussiere') is not None:
            return bool(div.get('haussiere'))
    else:
        n = div
    try:
        return float(n) > 0
    except (TypeError, ValueError):
        return False


def divergence_of(obj):
    if not obj or not isinstance(obj, dict):
        return None
    av = obj.get('av') if isinstance(obj.get('av'), dict) else {}
    if av.get('divergence') is not None:
        return av['divergence']
    if obj.get('divergence') is not None:
        return obj['divergence']
    for c in (av.get('components') or []):
        nom = str(c.get('nom') or '')
        if nom.startswith('Divergence') and c.get('note') is not None:
            return c['note']
    return None


def fond_penalty(fond):
    r = _R()['note_apex']
    if fond is None or float(fond) >= r['fond_seuil']:
        return 0.0
    return r['fond_pen_max'] * (r['fond_seuil'] - float(fond)) / r['fond_seuil']


def bande_couleur(note):
    if note is None:
        return None
    n = float(note)
    for b in _R()['couleurs']['bandes']:
        if b['min'] - 1e-9 <= n <= b['max'] + 1e-9:
            return b['site']
    return None


def flag_tv(note):
    if note is None:
        return 'none'
    return FC.flag_from_apex10(note)


flag_from_apex10 = flag_tv


def montant_template(note):
    """Barème TEMPLATE TRADE : 7,5 → 500 $, +100 $ par 0,5, jusqu'à 10 → 1 000 $."""
    if note is None:
        return None
    t = _R()['template_trade']
    n = round_half(note)
    if n < t['base_note']:
        return None
    n = min(n, t['max_note'])
    steps = int(round((n - t['base_note']) / t['pas_note']))
    amt = t['base_montant'] + steps * t['pas_montant']
    return min(amt, t['max_montant'])


TECH_ORDER = (
    ('elliott', 'Elliott'),
    ('structure', 'Struct.'),
    ('fibonacci', 'Fibo'),
    ('figure', 'Figure'),
    ('rsi', 'RSI'),
    ('macd', 'MACD'),
    ('cci', 'CCI'),
)


def technique_weights(na=None):
    na = na or _R()['note_apex']
    raw = na.get('technique') or {}
    out = {}
    for key, _lab in TECH_ORDER:
        w = raw.get(key)
        if w is None:
            continue
        out[key] = float(w)
    return out


def _as_score(v):
    if v is None:
        return 0.0
    try:
        return max(-100.0, min(100.0, float(v)))
    except (TypeError, ValueError):
        return 0.0


def pts_from_score(score, weight):
    """score −100…+100 → points dans la note (dénominateur = weight × 100 si weight est une fraction)."""
    return float(weight) * 100.0 * (_as_score(score) + 100.0) / 200.0


def _fmt_pts(x):
    if x is None:
        return '–'
    r = round(float(x) * 10) / 10
    if abs(r - round(r)) < 1e-9:
        return str(int(round(r)))
    return f'{r:.1f}'.replace('.', ',')


def _hex_of_pts(pts, poids):
    if not poids:
        return '#8a8a8a'
    return FC.hex_from_apex10(10.0 * float(pts) / float(poids))


def collect_parts(obj):
    import sys
    from pathlib import Path
    src = str(paths.src_dir())
    if src not in sys.path:
        sys.path.insert(0, src)
    import technique_apex as TA
    return TA.collect_parts(obj)


def compute(av, fond=None, elliott=None, divergence=None, parts=None, classe=None):
    """Calcule la note APEX /10 (t329u).

    parts : scores −100…+100 des composantes techniques. Si absent, la
    note technique est l'AV normalisé (onglets au barème spécifique, ou
    appels sans composantes). Sans fondamental, le technique est
    renormalisé à 100 % (signalé dans decomp).
    """
    r = _R()
    na = r['note_apex']
    ell_r = r['elliott']
    cy = r['cyan']
    cap = []
    if av is None and not parts:
        return {
            'note': None, 'display': '–', 'hex': None, 'flag': 'none',
            'pos': None, 'cap': '', 'timing': None, 'fond': None, 'brut': None,
            'decomp': None, 'technique': None, 'renormalise': False,
        }
    timing = None if av is None else av_pos(av, na['av_lo'], na['av_hi'])
    weights = technique_weights(na)
    sum_w = sum(weights.values()) or 0.5
    fond_w = float(na.get('poids_fondamental', 0.5))
    tech_w = float(na.get('poids_technique', na.get('poids_timing', 0.5)))
    renormalise = fond is None
    lib_fond = 'Liq.' if (classe == 'crypto' or na.get('crypto_fond') and classe == 'crypto') else 'Fond.'
    if classe == 'crypto':
        lib_fond = 'Liq.'

    lignes = []
    pts_total = 0.0
    if renormalise:
        # Technique porté à 100 %
        scale = 1.0 / sum_w if sum_w else 2.0
        cap.append('sans_fond')
    else:
        scale = tech_w / sum_w if sum_w else 1.0
        fond = float(fond)
        pts_f = fond_w * 100.0 * fond / 100.0
        lignes.append({
            'id': 'fond', 'label': lib_fond, 'pts': round(pts_f, 2),
            'poids': int(round(fond_w * 100)), 'score': round(fond, 1),
            'hex': _hex_of_pts(pts_f, fond_w * 100),
        })
        pts_total += pts_f

    tech_used = False
    if parts:
        for key, label in TECH_ORDER:
            if key not in weights:
                continue
            w_frac = weights[key] * scale
            score = parts.get(key)
            pts = pts_from_score(score, w_frac)
            poids = int(round(w_frac * 100))
            lignes.append({
                'id': key, 'label': label, 'pts': round(pts, 2),
                'poids': poids, 'score': None if score is None else round(_as_score(score), 1),
                'hex': _hex_of_pts(pts, poids),
                'neutre': score is None and key == 'figure',
            })
            pts_total += pts
            tech_used = True
    if not tech_used:
        # Barème agrégé (AV normalisé 0–100) en 100 % si pas de fond, sinon part technique.
        if timing is None:
            return {
                'note': None, 'display': '–', 'hex': None, 'flag': 'none',
                'pos': None, 'cap': '', 'timing': None,
                'fond': None if fond is None else round(float(fond), 1),
                'brut': None, 'decomp': None, 'technique': None,
                'renormalise': renormalise,
            }
        w_frac = 1.0 if renormalise else tech_w
        # timing is already 0–100
        pts = w_frac * 100.0 * float(timing) / 100.0
        poids = int(round(w_frac * 100))
        lignes.append({
            'id': 'agregé', 'label': 'Tech.', 'pts': round(pts, 2),
            'poids': poids, 'score': round(float(timing), 1),
            'hex': _hex_of_pts(pts, poids),
        })
        pts_total += pts

    brut = pts_total
    n = brut / 10.0
    pen = fond_penalty(None if renormalise else fond)
    if pen:
        n = n - pen
        cap.append('fondamental')
    key = elliott_key_of(elliott)
    fiable = elliott_fiable(elliott)
    rouges = set(ell_r['vagues_rouges'])
    if key in rouges:
        n = min(n, ell_r['plafond_rouge'])
        cap.append('elliott')
    if fiable and ell_r.get('bonus_seulement_manuel', True):
        if key in set(ell_r['bonus_05']):
            n = n + ell_r['bonus_entry']
            cap.append('bonus')
        elif key in set(ell_r['bonus_10']):
            n = n + ell_r['bonus_conf']
            cap.append('bonus')
    elif not ell_r.get('bonus_seulement_manuel', True):
        if key in set(ell_r['bonus_05']):
            n = n + ell_r['bonus_entry']
            cap.append('bonus')
        elif key in set(ell_r['bonus_10']):
            n = n + ell_r['bonus_conf']
            cap.append('bonus')
    n = max(na['note_min'], min(na['note_max'], round_half(n, na['arrondi'])))
    if n >= cy['note_min']:
        av_fort = (av is not None) and (float(av) >= cy['av_achat_fort'])
        vertes = set(ell_r['vagues_vertes'])
        conf = divergence_haussiere(divergence) or (fiable and key in vertes)
        if not (av_fort and conf):
            n = cy['plafond_sans_confirmation']
            cap.append('cyan')
    pos = n * 10.0
    prefix = ''
    if renormalise:
        prefix = 'sans fond. · '
    texte = prefix + ' · '.join(
        f"{ln['label']} {_fmt_pts(ln['pts'])}/{ln['poids']}" for ln in lignes
    )
    decomp = {
        'renormalise': renormalise,
        'libelle_fond': None if renormalise else lib_fond,
        'lignes': lignes,
        'texte': texte,
        'pts': round(brut, 2),
    }
    tech_moy = None
    if parts:
        vals = [_as_score(parts.get(k)) for k, _ in TECH_ORDER if k in weights]
        if vals:
            tech_moy = round(sum(vals) / len(vals), 1)
    return {
        'note': n,
        'display': fmt10(n),
        'hex': FC.hex_from_apex10(n),
        'flag': FC.flag_from_apex10(n),
        'pos': pos,
        'cap': '+'.join(cap),
        'timing': None if timing is None else round(timing, 1),
        'fond': None if fond is None else round(float(fond), 1),
        'brut': round(brut, 1),
        'decomp': decomp,
        'technique': tech_moy,
        'renormalise': renormalise,
    }
