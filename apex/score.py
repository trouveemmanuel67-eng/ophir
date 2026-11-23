"""Calcul unique de la note APEX /10 (t320u).

Lit config/regles.json. Les bonus Elliott ne s'appliquent que sur un
comptage manuel (override). Une note ≥ 8 exige un AV Achat fort et une
confirmation technique. Les couleurs découlent uniquement de la note.
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


def compute(av, fond=None, elliott=None, divergence=None):
    """Calcule la note APEX /10.

    Retourne : note, display, hex, flag, pos, cap, timing, fond, brut.
    av manquant → note None, display « – ».
    """
    r = _R()
    na = r['note_apex']
    ell_r = r['elliott']
    cy = r['cyan']
    cap = []
    if av is None:
        return {
            'note': None, 'display': '–', 'hex': None, 'flag': 'none',
            'pos': None, 'cap': '', 'timing': None, 'fond': None, 'brut': None,
        }
    timing = av_pos(av, na['av_lo'], na['av_hi'])
    if fond is None:
        brut = timing
    else:
        fond = float(fond)
        brut = na['poids_timing'] * timing + na['poids_fondamental'] * fond
    n = brut / 10.0
    pen = fond_penalty(fond)
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
        av_fort = float(av) >= cy['av_achat_fort']
        vertes = set(ell_r['vagues_vertes'])
        conf = divergence_haussiere(divergence) or (fiable and key in vertes)
        if not (av_fort and conf):
            n = cy['plafond_sans_confirmation']
            cap.append('cyan')
    pos = n * 10.0
    return {
        'note': n,
        'display': fmt10(n),
        'hex': FC.hex_from_apex10(n),
        'flag': FC.flag_from_apex10(n),
        'pos': pos,
        'cap': '+'.join(cap),
        'timing': round(timing, 1),
        'fond': None if fond is None else round(fond, 1),
        'brut': round(brut, 1),
    }
