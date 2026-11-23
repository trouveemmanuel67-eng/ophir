"""Note APEX /10 (23/11/2026, assouplie le jour même).

Fusion de la note Achat/Vente (timing) et de la qualité fondamentale, sur 10.
Formule : 60 % timing + 40 % fondamental, puis pénalités / plafonds / bonus
Elliott, arrondi au demi-point, bornée 1–10.

  timing  = (AV + 60) / 120 × 100     # AV saturé sur [−60, +60] → 0–100
  fond    = qualité 0–100, si elle existe
  brut    = 0,6 × timing + 0,4 × fond     (si pas de fondamental : timing seul)
  note    = brut / 10, ajustée, arrondie à 0,5, bornée 1–10

Pourquoi normaliser l'AV sur ±60 (bornes fixes, pas des rangs) :
  les AV publiés vivent à peu près entre −57 et +67, donc (AV+100)/2
  n'utilisait jamais les extrémités de l'échelle. Les percentiles hebdo
  sont écartés : un 10/10 changerait chaque semaine sans que l'actif change,
  et les ETF sans fondamental à AV seulement « moins mauvais » se
  retrouveraient en tête.

Ajustements :
  fondamental < 40/100 → pénalité proportionnelle
      −2 × (40 − fond) / 40     (0 pt à 40, −2 pts à 0)
  Elliott (règle du 23/11/2026, dessin validé « PARFAIT ») :
      zone rouge (vagues 1, 3, 5, A, B : w1, w3, w5, deb_5, new1,
          bear_135, a, fin_a, b) → plafond 4/10 ; pas de label Achat
          sur le signal Achat/Vente affiché (au mieux Neutre)
      zone verte (fin de 2, fin de 4, vague C) : pas de plafond
          +0,5 si la zone est détectée (fin_2, fin_4, fin_c, c, c_mid)
          +1 si une bougie hebdo clôturée confirme le retournement
             (fin_2_conf, fin_4_conf, fin_c_conf)
          c_mid est vert mais sans bonus de confirmation (reste à +0,5)
          Ces bonus ne s'appliquent que sur un comptage Elliott fiable
          (override manuel). Un comptage automatique n'ajoute aucun bonus
          (t317u). Le plafond rouge automatique est conservé.

  Note ≥ 8 (cyan, t317u) : uniquement si l'AV est en zone « Achat fort »
      (AV ≥ +60) ET qu'une confirmation technique existe
      (divergence haussière RSI/MACD hebdo, ou zone Elliott verte issue
      d'un override manuel). Sinon la note est plafonnée à 7,5
      (dernier cran vert). Un AV « Achat » (+20 à +59) ne peut plus
      produire un cyan, même avec un timing élevé.

Sans fondamental (matières, obligations, indices, ETF, paniers sans score
agrégé) : note sur le timing seul + règles Elliott (pas de pénalité fond).
Le score de sélection des ETF obligataires (TER, liquidité, notation) n'est
jamais utilisé comme fondamental, et aucun fondamental maximal n'est inventé.
Pour les cryptos, le fondamental est remplacé par le score de liquidité 0–100
(liquidite_crypto.py) lorsqu'une carte CoinAnk a été saisie ; sinon timing seul.
Données insuffisantes (pas d'AV) : note vide, affichage « – ».

Couleur et drapeau : uniquement la note /10 affichée (t315u / t316u).
  0 à 2 violet (TV purple) ; 2,5 à 5 rouge ; 5,5 à 6,5 jaune (TV orange) ;
  7 à 7,5 vert ; 8 à 10 cyan (TV cyan, pas bleu).
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import flags_couleur as FC

# t320u : le calcul canonique vit dans apex.score (config/regles.json).
import sys as _sys
from pathlib import Path as _Path
_APEX = _Path(__file__).resolve().parents[1]
if str(_APEX) not in _sys.path:
    _sys.path.insert(0, str(_APEX))


import elliott_zones as EZ
ELLIOTT_ROUGE = EZ.ZONE_ROUGE
ELLIOTT_VERTE = EZ.ZONE_VERTE
ELLIOTT_BONUS05 = EZ.BONUS05
ELLIOTT_BONUS10 = EZ.BONUS10

W_AV, W_FOND = 0.60, 0.40
AV_LO, AV_HI = -60.0, 60.0          # bornes fixes de normalisation du timing
FOND_SEUIL, FOND_PEN_MAX = 40.0, 2.0
CAP_ELL_ROUGE = EZ.CAP_ROUGE
BONUS_ENTRY, BONUS_CONF = 0.5, 1.0
NOTE_MIN, NOTE_MAX = 1.0, 10.0
AV_ACHAT_FORT = 60.0          # seuil « Achat fort » (même borne que lab_av)
NOTE_CYAN = 8.0               # premier cran cyan
CAP_CYAN_SANS_CONF = 7.5      # dernier cran vert si le cyan n'est pas mérité


def av_pos(av):
    """AV −100…+100 → timing 0–100, saturé sur [AV_LO, AV_HI]."""
    x = max(AV_LO, min(AV_HI, float(av)))
    return (x - AV_LO) / (AV_HI - AV_LO) * 100.0


def round_half(x):
    return round(float(x) * 2.0) / 2.0


def fmt10(n):
    if n is None:
        return '–'
    n = float(n)
    if n == int(n):
        return str(int(n))
    return f'{n:.1f}'.replace('.', ',')


def flag_from_apex10(note):
    if note is None:
        return 'none'
    return FC.flag_from_pos(float(note) * 10.0)


def elliott_key_of(ell):
    if not ell:
        return None
    if isinstance(ell, str):
        return ell
    if isinstance(ell, dict):
        return ell.get('key')
    return None


def elliott_fiable(ell):
    """True uniquement pour un override / comptage manuel (pas un auto-détecté)."""
    if not isinstance(ell, dict):
        return False
    return bool(ell.get('manuel') or ell.get('override') or ell.get('source') == 'manuel')


def divergence_haussiere(div):
    """True si une divergence RSI/MACD hebdo haussière est fournie (note > 0)."""
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
    """Extrait la note de divergence d'un objet barre / AV (si elle a été conservée)."""
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
    """Pénalité en points /10 si fond < 40, sinon 0."""
    if fond is None or fond >= FOND_SEUIL:
        return 0.0
    return FOND_PEN_MAX * (FOND_SEUIL - float(fond)) / FOND_SEUIL


def compute(av, fond=None, elliott=None, divergence=None):
    """Calcule la note APEX /10.

    Retourne un dict : note, display, hex, flag, pos, cap, timing, fond, brut.
    av manquant → note None, display « – ».
    bonus Elliott seulement si elliott est un dict marqué manuel/override.
    note ≥ 8 seulement si AV ≥ +60 et confirmation (divergence haussière
    ou zone verte manuelle).
    """
    cap = []
    if av is None:
        return {
            'note': None, 'display': '–', 'hex': None, 'flag': 'none',
            'pos': None, 'cap': '', 'timing': None, 'fond': None, 'brut': None,
        }
    timing = av_pos(av)
    if fond is None:
        brut = timing
    else:
        fond = float(fond)
        brut = W_AV * timing + W_FOND * fond
    n = brut / 10.0
    pen = fond_penalty(fond)
    if pen:
        n = n - pen
        cap.append('fondamental')
    key = elliott_key_of(elliott)
    fiable = elliott_fiable(elliott)
    if key in ELLIOTT_ROUGE:
        n = min(n, CAP_ELL_ROUGE)
        cap.append('elliott')
    if fiable:
        if key in ELLIOTT_BONUS05:
            n = n + BONUS_ENTRY
            cap.append('bonus')
        elif key in ELLIOTT_BONUS10:
            n = n + BONUS_CONF
            cap.append('bonus')
    n = max(NOTE_MIN, min(NOTE_MAX, round_half(n)))
    # Plafond cyan : Achat fort + confirmation technique (t317u)
    if n >= NOTE_CYAN:
        av_fort = float(av) >= AV_ACHAT_FORT
        conf = divergence_haussiere(divergence) or (fiable and key in ELLIOTT_VERTE)
        if not (av_fort and conf):
            n = CAP_CYAN_SANS_CONF
            cap.append('cyan')
    pos = n * 10.0
    code = FC.flag_from_apex10(n)
    return {
        'note': n,
        'display': fmt10(n),
        'hex': FC.hex_from_apex10(n),
        'flag': code,
        'pos': pos,
        'cap': '+'.join(cap),
        'timing': round(timing, 1),
        'fond': None if fond is None else round(fond, 1),
        'brut': round(brut, 1),
    }


from apex.score import compute  # remplace la fonction définie plus haut (même signature)

if __name__ == '__main__':
    def chk(av, fond, ell, expect, cap=None, divergence=None):
        r = compute(av, fond, ell, divergence=divergence)
        assert r['note'] == expect, (av, fond, ell, r, expect)
        if cap is not None:
            assert r['cap'] == cap, (r['cap'], cap)

    chk(None, 90, None, None)
    # APP : AV −5,4, fond 89,7, Elliott B (zone rouge) → brut 63,2, plafond 4
    r = compute(-5.4, 89.7, 'b')
    print('APP −5.4 fond 89.7 ell b', r)
    assert r['note'] == 4.0 and r['cap'] == 'elliott' and r['flag'] == 'red'
    # DTE auto (t317u) : AV +44,3 (pas Achat fort), fond 57,3, fin_4_conf auto
    # → plus de bonus, brut 74,2 → 7,5 vert (n'atteint pas 8 sans bonus)
    r2 = compute(44.3, 57.3, 'fin_4_conf')
    print('DTE-like auto', r2)
    assert r2['note'] == 7.5 and r2['cap'] == '' and r2['flag'] == 'green'
    # Même DTE, override manuel : bonus +1 → 8,5 puis plafond cyan (AV < 60)
    r2m = compute(44.3, 57.3, {'key': 'fin_4_conf', 'manuel': True, 'zone': 'verte'})
    print('DTE-like manuel', r2m)
    assert r2m['note'] == 7.5 and 'bonus' in r2m['cap'] and 'cyan' in r2m['cap'] and r2m['flag'] == 'green'
    # Vague C auto : plus de bonus
    rC = compute(0, None, 'c')
    print('vague C auto', rC)
    assert rC['note'] == 5.0 and rC['cap'] == '' and 'elliott' not in rC['cap']
    # Vague C manuelle : +0,5
    rCm = compute(0, None, {'key': 'c', 'manuel': True, 'zone': 'verte'})
    print('vague C manuel', rCm)
    assert rCm['note'] == 5.5 and 'bonus' in rCm['cap']
    # w5 : plafond 4
    rW = compute(50, None, 'w5')
    print('w5', rW)
    assert rW['note'] == 4.0 and rW['cap'] == 'elliott' and rW['flag'] == 'red'
    # PIRC : mauvais fond + vague 5 → 1/10 violet (échelle t315u)
    r3 = compute(-38.9, 13.6, 'w5')
    print('PIRC-like', r3)
    assert r3['note'] == 1.0 and r3['flag'] == 'purple' and 'fondamental' in r3['cap']
    # AV saturé à gauche, sans fond → clamp 1
    chk(-80, None, None, 1.0)
    # Pénalité fond, pas de plafond dur à 4 : AV +50, fond 30
    # timing 91.67, brut 67.0, n 6.7, pénalité 0.5 → 6.2 → 6.0
    r4 = compute(50, 30, None)
    print('fond pénalité', r4)
    assert r4['note'] == 6.0 and r4['cap'] == 'fondamental'
    # Panier FR util auto : +22, fond 32.9, fin_4 auto → plus de bonus
    r5 = compute(22.0, 32.9, 'fin_4')
    print('FR util auto', r5)
    assert r5['note'] == 5.0 and 'bonus' not in r5['cap'] and 'fondamental' in r5['cap']
    # PRAR-like : AV +45,2, pas de fond, fin_2_conf auto → timing 87,7
    # → 9,0 puis plafond cyan 7,5
    rP = compute(45.2, None, 'fin_2_conf')
    print('PRAR-like', rP)
    assert rP['note'] == 7.5 and 'cyan' in rP['cap'] and rP['flag'] == 'green'
    # Cyan mérité : AV Achat fort + divergence haussière
    rOk = compute(65, None, None, divergence=100)
    print('cyan merité div', rOk)
    assert rOk['note'] == 10.0 and rOk['flag'] == 'cyan' and 'cyan' not in rOk['cap']
    # Achat fort sans confirmation → plafond 7,5
    rNo = compute(65, None, None)
    print('achat fort sans conf', rNo)
    assert rNo['note'] == 7.5 and 'cyan' in rNo['cap'] and rNo['flag'] == 'green'
    # Achat fort + zone verte manuelle → cyan autorisé
    rEll = compute(65, None, {'key': 'fin_4', 'manuel': True, 'zone': 'verte'})
    print('cyan merité ell manuel', rEll)
    assert rEll['note'] == 10.0 and rEll['flag'] == 'cyan' and 'bonus' in rEll['cap']
    print('ok')
