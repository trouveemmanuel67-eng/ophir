"""Calcul unique de la note APEX /100 (t337u).

Lit config/regles.json. Note = somme des points (fondamental 50 + technique 50 ;
le poids « figure chartiste » a été retiré et les autres critères techniques
sont renormalisés proportionnellement). Sans
fondamental, le technique est renormalisé à 100 points. Les bonus Elliott
ne s'appliquent que sur un comptage manuel. Une note ≥ 80 exige un AV Achat
fort et une confirmation. Les couleurs découlent uniquement de la note affichée.
"""
from __future__ import annotations
import json
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


# MM40 hebdo (équivalent de la MM200 jours), à contre-courant.
# Même maximum que le fondamental des actions sur la grille 250 : +125.
MM40_HEBDO_MAX = 125
MM40_HEBDO_PLAFOND = 0.15
MM40_HEBDO_REGLE = (
    "MM40 hebdo, à contre-courant, sur les clôtures hebdomadaires confirmées "
    "(équivalent de la MM200 jours). 0 point si le cours est au-dessus de la MM40 ; "
    "montée linéaire de 0 à +125 entre 0 % et −15 % ; plafonné à +125 au-delà. "
    "Les points s’ajoutent au total, borné à −50…250."
)


def fmt_ecart_pct(ecart):
    """Pourcentage d’écart au format français : −20,4 / +1,2 / 0."""
    if ecart is None:
        return '—'
    pct = float(ecart) * 100.0
    txt = f"{pct:.1f}".replace(".", ",")
    if txt in ("-0,0", "0,0", "+0,0") or abs(pct) < 0.05:
        return "0"
    if pct > 0 and not txt.startswith("+"):
        txt = "+" + txt
    return txt.replace("-", "−")


def mm40_hebdo_texte(ecart, pts):
    """Libellé de décomposition : « MM40 hebdo : écart −20,4 %, +125 pts »."""
    if ecart is None or pts is None:
        return "MM40 hebdo : —"
    pts_txt = f"+{int(pts)}" if pts > 0 else str(int(pts))
    return f"MM40 hebdo : écart {fmt_ecart_pct(ecart)} %, {pts_txt} pts"


def mm40_hebdo_points(closes):
    """Écart à la MM40 semaines, à contre-courant (0 à +125).

    écart = (cours − MM40) / MM40. Au-dessus → 0 ; de 0 à −15 % → 0…+125
    linéairement ; au-delà de −15 % → +125. Historique < 40 semaines → n.c.

    Retourne (points:int|None, détail:dict).
    """
    base = {
        'max': MM40_HEBDO_MAX,
        'periode': '40 semaines',
        'regle': MM40_HEBDO_REGLE,
    }
    if not closes:
        d = dict(base, etat='n.c.', points=None, raison='série hebdomadaire absente')
        return None, d
    series = [float(x) for x in closes if x is not None]
    if len(series) < 40:
        d = dict(base, etat='n.c.', points=None,
                 raison=f'historique insuffisant ({len(series)} semaines)')
        return None, d
    cours = series[-1]
    mm = sum(series[-40:]) / 40.0
    if mm <= 0:
        d = dict(base, etat='n.c.', points=None, raison='MM40 nulle ou négative', cours=cours, mm40=mm)
        return None, d
    ecart = (cours - mm) / mm
    if ecart >= 0:
        pts = 0
    else:
        pts = int(round_half(min(MM40_HEBDO_MAX, (-ecart / MM40_HEBDO_PLAFOND) * MM40_HEBDO_MAX)))
        pts = max(0, min(MM40_HEBDO_MAX, pts))
    det = dict(
        base,
        etat='applique',
        points=pts,
        ecart=round(ecart, 6),
        ecart_pct=round(ecart * 100.0, 2),
        cours=cours,
        mm40=round(mm, 6),
        texte=mm40_hebdo_texte(ecart, pts),
    )
    return pts, det


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
    bandes = _R()['couleurs']['bandes']
    for i, b in enumerate(bandes):
        nxt = bandes[i + 1]['min'] if i + 1 < len(bandes) else None
        if nxt is None:
            if n >= b['min'] - 1e-9:
                return b['site']
        elif b['min'] - 1e-9 <= n < nxt:
            return b['site']
    return None


def flag_tv(note):
    if note is None:
        return 'none'
    return FC.flag_from_apex10(note)


flag_from_apex10 = flag_tv


def montant_template(note):
    """Barème TEMPLATE TRADE : 75 → 500 $, +100 $ par 5 points, jusqu'à 100 → 1 000 $."""
    if note is None:
        return None
    t = _R()['template_trade']
    n = round_half(note)
    if n < t['base_note']:
        return None
    n = min(n, t['max_note'])
    steps = int((n - t['base_note']) // t['pas_note'])  # paliers entiers (audit APE-24)
    amt = t['base_montant'] + steps * t['pas_montant']
    return min(amt, t['max_montant'])


TECH_ORDER = (
    ('elliott', 'Elliott'),
    ('structure', 'Struct.'),
    ('fibonacci', 'Fibo'),
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


def amplitude_echelle(na=None):
    na = na or _R()['note_apex']
    return float(na.get('amplitude_echelle', 1.5))


def pts_from_score(score, weight, scale=None):
    """Écart signé autour de 50 : weight (fraction) × 50 × amplitude × score/100.

    Neutre (score 0) → 0 point. score +100 → +amp, score −100 → −amp.
    Par défaut amplitude 1,5 (±75 au total). L'ancienne lecture « moitié des
    points au neutre » (weight×(score+100)/200) n'est plus utilisée.
    """
    if scale is None:
        scale = amplitude_echelle()
    amp = float(weight) * 50.0 * float(scale)
    return amp * _as_score(score) / 100.0


def _fmt_pts(x):
    if x is None:
        return '–'
    r = round(float(x) * 10) / 10
    if abs(r - round(r)) < 1e-9:
        return str(int(round(r)))
    return f'{r:.1f}'.replace('.', ',')


def _fmt_signed(x):
    if x is None:
        return '–'
    r = round(float(x) * 10) / 10
    if abs(r) < 1e-9:
        return '0'
    sign = '−' if r < 0 else '+'
    body = _fmt_pts(abs(r))
    return sign + body


def _hex_of_score(score):
    """Couleur du critère d'après son score −100…+100 (0 → jaune)."""
    return FC.hex_from_apex10((_as_score(score) + 100.0) / 2.0)


def _hex_of_pts(pts, poids):
    """Rétrocompat : interprète pts comme écart signé si |pts| ≤ |poids|*2."""
    if not poids:
        return '#8a8a8a'
    # base 50 : un écart de 0 = jaune (50). On ramène à 0–100 via 50 + 50*pts/amp
    return FC.hex_from_apex10(50.0 + 50.0 * float(pts) / float(poids))


def collect_parts(obj):
    import sys
    from pathlib import Path
    src = str(paths.src_dir())
    if src not in sys.path:
        sys.path.insert(0, src)
    import technique_apex as TA
    return TA.collect_parts(obj)


def compute(av, fond=None, elliott=None, divergence=None, parts=None, classe=None, obj=None, metal=None, fg=None):
    """Calcule la note APEX /100, ou −50 à 250 pour les métaux (t475u, points entiers).

    Hors métaux : part de 50, scores −100…+100, amplitude ×1,5, clip 0–100.
    Métaux : paliers entiers additifs comme les actions (RSI 30, MACD 30,
    Fibonacci 30, CCI/Stoch 20, fond 90 ou Structure 90, F&G ±50).
    """
    if classe == 'metaux':
        if obj is not None:
            from .metaux_points import score_instrument
            return score_instrument(obj, metal=metal, av=av, fg=fg)
        return compute_metaux(av, fond, elliott, divergence, parts)
    if classe == 'crypto' and obj is not None:
        from .crypto_points import score_asset
        return score_asset(obj)
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
    # t461u : métaux, même logique que les actions le 24/11 — Elliott retiré
    # sans redistribuer son poids (le trou reste dans le dénominateur).
    skip_ids = set()
    if classe == 'metaux':
        skip_ids.add('elliott')
    lib_fond = 'Liq.' if (classe == 'crypto' or na.get('crypto_fond') and classe == 'crypto') else 'Fond.'
    if classe == 'crypto':
        lib_fond = 'Liq.'

    amp_scale = amplitude_echelle(na)
    base = float(na.get('note_base', 50.0))
    lignes = []
    pts_total = 0.0
    if renormalise:
        # Technique porté à 100 % (amplitude totale ±75)
        scale = 1.0 / sum_w if sum_w else 2.0
        cap.append('sans_fond')
    else:
        scale = tech_w / sum_w if sum_w else 1.0
        fond = float(fond)
        score_f = max(-100.0, min(100.0, (fond - 50.0) * 2.0))
        pts_f = pts_from_score(score_f, fond_w, amp_scale)
        lignes.append({
            'id': 'fond', 'label': lib_fond, 'pts': round(pts_f, 2),
            'poids': int(round(fond_w * 100)), 'score': round(fond, 1),
            'hex': _hex_of_score(score_f),
        })
        pts_total += pts_f

    tech_used = False
    if parts:
        for key, label in TECH_ORDER:
            if key not in weights or key in skip_ids:
                continue
            w_frac = weights[key] * scale
            score = parts.get(key)
            pts = pts_from_score(score, w_frac, amp_scale)
            poids = int(round(w_frac * 100))
            sc = None if score is None else round(_as_score(score), 1)
            lignes.append({
                'id': key, 'label': label, 'pts': round(pts, 2),
                'poids': poids, 'score': sc,
                'hex': _hex_of_score(0.0 if score is None else score),
                'neutre': (sc is not None and abs(sc) < 1e-9),
            })
            pts_total += pts
            tech_used = True
    if not tech_used:
        # Barème agrégé (AV normalisé 0–100) : même base 50 + amplitude.
        if timing is None:
            return {
                'note': None, 'display': '–', 'hex': None, 'flag': 'none',
                'pos': None, 'cap': '', 'timing': None,
                'fond': None if fond is None else round(float(fond), 1),
                'brut': None, 'decomp': None, 'technique': None,
                'renormalise': renormalise,
            }
        w_frac = 1.0 if renormalise else tech_w
        score_t = max(-100.0, min(100.0, (float(timing) - 50.0) * 2.0))
        pts = pts_from_score(score_t, w_frac, amp_scale)
        poids = int(round(w_frac * 100))
        lignes.append({
            'id': 'agregé', 'label': 'Tech.', 'pts': round(pts, 2),
            'poids': poids, 'score': round(float(timing), 1),
            'hex': _hex_of_score(score_t),
        })
        pts_total += pts

    brut = base + pts_total
    n = brut
    pen = fond_penalty(None if renormalise else fond)
    if pen:
        n = n - pen
        cap.append('fondamental')
    key = elliott_key_of(elliott)
    fiable = elliott_fiable(elliott)
    # t342u : plus de plafond Elliott sur la note entière (le score du
    # critère retire déjà des points en zone rouge). L'entrée / le cyan
    # restent filtrés plus bas.
    # t461u : pas de bonus Elliott sur la note des métaux (Elliott retiré).
    if classe != 'metaux' and fiable and ell_r.get('bonus_seulement_manuel', True):
        if key in set(ell_r['bonus_05']):
            n = n + ell_r['bonus_entry']
            cap.append('bonus')
        elif key in set(ell_r['bonus_10']):
            n = n + ell_r['bonus_conf']
            cap.append('bonus')
    elif classe != 'metaux' and not ell_r.get('bonus_seulement_manuel', True):
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
        # t461u : portail cyan des métaux sans condition Elliott (comme les actions).
        if classe == 'metaux':
            conf = divergence_haussiere(divergence)
        else:
            conf = divergence_haussiere(divergence) or (fiable and key in vertes)
        if not (av_fort and conf):
            n = cy['plafond_sans_confirmation']
            cap.append('cyan')
    pos = n
    bits = [f"Base {_fmt_pts(base)}"]
    if renormalise:
        bits.append('sans fond.')
    bits.extend(f"{ln['label']} {_fmt_signed(ln['pts'])}" for ln in lignes)
    texte = ' · '.join(bits)
    decomp = {
        'renormalise': renormalise,
        'libelle_fond': None if renormalise else lib_fond,
        'lignes': lignes,
        'texte': texte,
        'pts': round(brut, 2),
        'base': base,
        'amplitude': amp_scale,
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



# ----- Métaux précieux : même échelle que les actions (−50 à 250), t470u -----
# Technique + fondamental (minières) = 0 à 200, en gardant les proportions
# des critères restants (Elliott hors calcul, son ancien poids est réparti
# pour que l'échelle soit entièrement couverte). F&G CNN ±50, même grille
# que les actions. Le bandeau Achat / Vente n'est pas modifié ici.

METAUX_PILOT_BANDS = (
    ('violet', -50, 10, '#9d54ff', 'purple'),
    ('rouge', 10, 70, '#ff2d2d', 'red'),
    ('orange', 70, 130, '#ff8c1a', 'orange'),
    ('vert', 130, 190, '#22c55e', 'green'),
    ('cyan', 190, 251, '#00e5ff', 'cyan'),
)


def fg_points(value):
    """Tranches de 10 autour de 50 : 40→+10 … 0→+50 ; 60→−10 … 100→−50.
    Une tranche n'est comptée que lorsqu'elle est entièrement franchie
    (floor de |50 − valeur| / 10), plafonnée à ±50.
    Ex. 17,7 → écart 32,3 → 3 tranches → +30 (seuil 20 atteint, 10 pas encore).
    """
    import math
    if value is None:
        return None
    try:
        v = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(v):
        return None
    delta = 50.0 - v
    n = int(math.floor(abs(delta) / 10.0))
    n = min(5, n)
    pts = n * 10
    return pts if delta >= 0 else -pts


def load_cnn_fg():
    """Lit l'indice CNN déjà utilisé pour les actions (pas de valeur inventée)."""
    from . import paths as _p
    root = _p.ROOT if hasattr(_p, 'ROOT') else Path(__file__).resolve().parents[1]
    data = getattr(_p, 'data_dir', None)
    data = data() if callable(data) else (root / 'data')
    for name in ('apex_achat_v2_pilot.json', 'apex_achat_v2_cnn_fng.json'):
        fp = data / name
        if not fp.exists():
            continue
        try:
            raw = json.loads(fp.read_text(encoding='utf-8'))
        except Exception:
            continue
        fg = raw.get('fear_greed')
        if isinstance(fg, dict) and fg.get('ok') and fg.get('value') is not None:
            pts = fg.get('points')
            if pts is None:
                pts = fg_points(fg.get('value'))
            return {
                'ok': True,
                'value': float(fg['value']),
                'points': int(pts) if pts is not None else 0,
                'label': fg.get('label') or '',
            }
        core = raw.get('fear_and_greed') or {}
        score = core.get('score')
        if score is not None:
            pts = fg_points(score)
            return {
                'ok': True,
                'value': float(score),
                'points': int(pts) if pts is not None else 0,
                'label': core.get('rating') or '',
            }
    return {'ok': False, 'value': None, 'points': 0, 'label': ''}


def metaux_cfg():
    mx = _R().get('apex_metaux') or {}
    return {
        'min': float(mx.get('note_min', -50)),
        'max': float(mx.get('note_max', 250)),
        'tech_fond': float(mx.get('tech_fond_max', 200)),
        'fg_abs': float(mx.get('fg_abs', 50)),
        'cyan_min': float(mx.get('cyan_note_min', 190)),
        'cyan_plafond': float(mx.get('cyan_plafond', 175)),
        'pen_max': float(mx.get('fond_pen_max', 60)),
        'arrondi': float((_R().get('note_apex') or {}).get('arrondi', 1)),
    }


def metaux_fracs(na, renormalise):
    """Fractions des critères restants (sans Elliott), somme 1."""
    used = {k: w for k, w in technique_weights(na).items() if k != 'elliott'}
    if not renormalise:
        used['fond'] = float(na.get('poids_fondamental', 0.5))
    s = sum(used.values()) or 1.0
    return {k: float(w) / s for k, w in used.items()}


def metaux_max_pts(frac, tech_fond=200.0):
    return float(tech_fond) * float(frac)


def metaux_contrib(score, max_pts):
    """0 .. max_pts, neutre (score 0) = moitié des points, comme une accumulation actions."""
    return float(max_pts) * (_as_score(score) + 100.0) / 200.0


def metaux_band(note):
    if note is None:
        return {'id': '', 'hex': '#8a8a8a', 'flag': 'none'}
    t = float(note)
    if t >= 190:
        return {'id': 'cyan', 'hex': '#00e5ff', 'flag': 'cyan'}
    if t < -50:
        return {'id': 'violet', 'hex': '#9d54ff', 'flag': 'purple'}
    for bid, lo, hi, hex_, flag in METAUX_PILOT_BANDS:
        if lo <= t < hi:
            return {'id': bid, 'hex': hex_, 'flag': flag}
    return {'id': 'cyan', 'hex': '#00e5ff', 'flag': 'cyan'}


def montant_template_metaux(note):
    """Aligné sur les actions : seuil 130 → 500 $, +100 $ tous les 24 points, jusqu'à 250 → 1 000 $."""
    if note is None:
        return None
    mx = _R().get('apex_metaux') or {}
    n = round_half(note)
    base = float(mx.get('gi_base_note', 130))
    if n < base:
        return None
    n = min(n, float(mx.get('gi_max_note', 250)))
    pas = float(mx.get('gi_pas_note', 24))
    steps = int((n - base) // pas)  # paliers entiers : 154 → 600 $, 250 → 1 000 $ (audit APE-24)
    amt = int(mx.get('gi_base_montant', 500)) + steps * int(mx.get('gi_pas_montant', 100))
    return min(amt, int(mx.get('gi_max_montant', 1000)))


def compute_metaux(av, fond=None, elliott=None, divergence=None, parts=None):
    """Note métaux −50 à 250 (t470u). Bandeau Achat / Vente inchangé."""
    r = _R()
    na = r['note_apex']
    cy_av = (r.get('cyan') or {}).get('av_achat_fort', 60)
    cfg = metaux_cfg()
    cap = []
    if av is None and not parts:
        return {
            'note': None, 'display': '–', 'hex': None, 'flag': 'none',
            'pos': None, 'cap': '', 'timing': None, 'fond': None, 'brut': None,
            'decomp': None, 'technique': None, 'renormalise': False,
            'scale': 250, 'total': None, 'total_min': cfg['min'], 'total_max': cfg['max'],
            'ligne': '',
        }
    timing = None if av is None else av_pos(av, na['av_lo'], na['av_hi'])
    renormalise = fond is None
    fracs = metaux_fracs(na, renormalise)
    if renormalise:
        cap.append('sans_fond')
    lignes = []
    pts_total = 0.0
    labels = dict(TECH_ORDER)
    labels['fond'] = 'Fond.'
    order = ['structure', 'fibonacci', 'rsi', 'macd', 'cci']
    if not renormalise:
        order = ['fond'] + order
        fond = float(fond)
        score_f = max(-100.0, min(100.0, (fond - 50.0) * 2.0))
        mxp = metaux_max_pts(fracs['fond'], cfg['tech_fond'])
        pts = metaux_contrib(score_f, mxp)
        lignes.append({
            'id': 'fond', 'label': 'Fond.', 'pts': round(pts, 2),
            'poids': int(round(fracs['fond'] * cfg['tech_fond'])),
            'score': round(fond, 1), 'hex': _hex_of_score(score_f),
            'max_pts': round(mxp, 2),
        })
        pts_total += pts

    tech_used = False
    if parts:
        for key in ['structure', 'fibonacci', 'rsi', 'macd', 'cci']:
            if key not in fracs:
                continue
            score = parts.get(key)
            mxp = metaux_max_pts(fracs[key], cfg['tech_fond'])
            pts = metaux_contrib(0.0 if score is None else score, mxp)
            sc = None if score is None else round(_as_score(score), 1)
            lignes.append({
                'id': key, 'label': labels.get(key, key), 'pts': round(pts, 2),
                'poids': int(round(fracs[key] * cfg['tech_fond'])),
                'score': sc, 'hex': _hex_of_score(0.0 if score is None else score),
                'neutre': (sc is not None and abs(sc) < 1e-9),
                'max_pts': round(mxp, 2),
            })
            pts_total += pts
            tech_used = True
    if not tech_used:
        if timing is None:
            return {
                'note': None, 'display': '–', 'hex': None, 'flag': 'none',
                'pos': None, 'cap': '', 'timing': None,
                'fond': None if fond is None else round(float(fond), 1),
                'brut': None, 'decomp': None, 'technique': None,
                'renormalise': renormalise,
                'scale': 250, 'total': None, 'total_min': cfg['min'], 'total_max': cfg['max'],
                'ligne': '',
            }
        # un seul bloc technique agrégé, même 0..tech_fond (ou part restante)
        frac_tech = sum(fracs[k] for k in fracs if k != 'fond') or 1.0
        mxp = metaux_max_pts(frac_tech, cfg['tech_fond'])
        score_t = max(-100.0, min(100.0, (float(timing) - 50.0) * 2.0))
        pts = metaux_contrib(score_t, mxp)
        lignes.append({
            'id': 'agregé', 'label': 'Tech.', 'pts': round(pts, 2),
            'poids': int(round(frac_tech * cfg['tech_fond'])),
            'score': round(float(timing), 1), 'hex': _hex_of_score(score_t),
            'max_pts': round(mxp, 2),
        })
        pts_total += pts

    fg = load_cnn_fg()
    fg_pts = int(fg['points']) if fg.get('ok') else 0
    if fg.get('ok'):
        lignes.append({
            'id': 'fear_greed', 'label': 'F&G', 'pts': fg_pts,
            'poids': int(cfg['fg_abs']), 'score': None if fg.get('value') is None else round(float(fg['value']), 1),
            'hex': '#e6c27a',
            'max_pts': cfg['fg_abs'],
        })
    else:
        cap.append('fg_absent')

    pen = 0.0
    if not renormalise:
        # Pénalité fondamentale : 20 pts sur /100 → 60 pts sur l'échelle 300 (−50..250).
        rpen = na
        if fond is not None and float(fond) < rpen['fond_seuil']:
            pen = cfg['pen_max'] * (rpen['fond_seuil'] - float(fond)) / rpen['fond_seuil']
            cap.append('fondamental')

    brut = pts_total + fg_pts - pen
    n = max(cfg['min'], min(cfg['max'], round_half(brut, cfg['arrondi'])))
    # APE-25 (t503u) : plus de plafond cyan, la note peut atteindre 250.
    band = metaux_band(n)
    bits = []
    if renormalise:
        bits.append('sans fond.')
    for ln in lignes:
        if ln['id'] == 'fear_greed':
            bits.append(f"{ln['label']} {_fmt_signed(ln['pts'])}")
        else:
            bits.append(f"{ln['label']} {_fmt_pts(ln['pts'])}")
    texte = ' · '.join(bits) + f"  →  {_fmt_pts(n)} / 250"
    decomp = {
        'renormalise': renormalise,
        'libelle_fond': None if renormalise else 'Fond.',
        'lignes': lignes,
        'texte': texte,
        'pts': round(brut, 2),
        'base': 0,
        'echelle': 250,
        'tech_fond_max': cfg['tech_fond'],
    }
    tech_moy = None
    if parts:
        vals = [_as_score(parts.get(k)) for k in ('structure', 'fibonacci', 'rsi', 'macd', 'cci') if k in (parts or {})]
        if vals:
            tech_moy = round(sum(vals) / len(vals), 1)
    return {
        'note': n,
        'display': fmt10(n),
        'hex': band['hex'],
        'flag': band['flag'],
        'band': band['id'],
        'pos': n,
        'cap': '+'.join(cap),
        'timing': None if timing is None else round(timing, 1),
        'fond': None if fond is None else round(float(fond), 1),
        'brut': round(brut, 1),
        'decomp': decomp,
        'technique': tech_moy,
        'renormalise': renormalise,
        'scale': 250,
        'total': n,
        'total_min': cfg['min'],
        'total_max': cfg['max'],
        'ligne': texte,
        'fg_points': fg_pts if fg.get('ok') else None,
        'fg_value': fg.get('value') if fg.get('ok') else None,
    }
