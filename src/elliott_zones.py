"""Zones d'entrée Elliott d'Emmanuel (23/11/2026, dessin validé « PARFAIT »).

ZONES VERTES (entrée) : fin de vague 2, fin de vague 4, vague C.
ZONES ROUGES (aucune entrée) : vague 1, vague 3, vague 5, vague A, vague B.

Le /100 n'est plus plafonné à 50 ou 65. En zone rouge, plafond unique 40/100,
et le signal Achat/Vente affiché ne peut pas porter le label Achat (au mieux
Neutre). En zone verte, pas de plafond ; bonus +5 si la zone est détectée,
+10 si une bougie hebdomadaire clôturée confirme le retournement.
c_mid est vert mais sans bonus de confirmation.
Les états w2 / w4 en cours (pas encore la fin), bear_24 et indet sont hors
zone : ni plafond, ni bonus.

Les comptages manuels (data/elliott_overrides.json) priment sur le décompte
automatique et sur lectures_manuelles.json.
"""
import json, os

DIR = os.path.dirname(os.path.abspath(__file__))
OV_PATH = os.path.join(DIR, '..', 'data', 'elliott_overrides.json')

ZONE_VERTE = frozenset({
    'fin_2', 'fin_2_conf',
    'fin_4', 'fin_4_conf',
    'c', 'c_mid', 'fin_c', 'fin_c_conf',
})
ZONE_ROUGE = frozenset({
    'w1', 'w3', 'w5', 'deb_5', 'new1',
    'bear_135',
    'a', 'fin_a', 'b',
})
# Bonus +0,5 (zone détectée, sans confirmation de retournement clôturé)
BONUS05 = frozenset({
    'fin_2', 'fin_4', 'fin_c',
    'c', 'c_mid',
})
# Bonus +1 (confirmation par bougie hebdo clôturée)
BONUS10 = frozenset({
    'fin_2_conf', 'fin_4_conf', 'fin_c_conf',
})
# c_mid : vert, +0,5 seulement (pas de +1)

CAP_ROUGE = 4.0
AV_ACHAT = 20.0          # seuil du label Achat (ind_core.lab_av)
AV_NEUTRE_MAX = 19.0     # score affiché plafonné, sous le seuil d'Achat

ENTRY_KEYS = ZONE_VERTE

_OV = None
_OV_INDEX = None


def _load():
    global _OV, _OV_INDEX
    if _OV_INDEX is not None:
        return
    _OV, _OV_INDEX = {}, {}
    try:
        raw = json.load(open(OV_PATH))
    except Exception:
        return
    ovs = raw.get('overrides') or {}
    _OV = ovs
    for k, v in ovs.items():
        if not isinstance(v, dict):
            continue
        _OV_INDEX[k] = v
        for a in v.get('alias') or []:
            if a:
                _OV_INDEX[a] = v


def override_of(syms):
    """Retourne le dict d'override, ou None."""
    _load()
    for s in (syms or []):
        if not s:
            continue
        if s in _OV_INDEX:
            return _OV_INDEX[s]
        # parfois le ticker Yahoo seul
        if isinstance(s, str) and ':' in s:
            tail = s.split(':', 1)[1]
            if tail in _OV_INDEX:
                return _OV_INDEX[tail]
    return None


def zone_of(key):
    if key in ZONE_VERTE:
        return 'verte'
    if key in ZONE_ROUGE:
        return 'rouge'
    return None


def apply_override(e, syms):
    """Remplace le décompte automatique par le comptage manuel, s'il existe."""
    import elliott as E
    ov = override_of(syms)
    if not ov:
        if e:
            e = dict(e)
            e['zone'] = zone_of(e.get('key'))
        return e
    key = ov['key']
    texte = ov.get('texte') or (E.TXT.get(key, key) + f" (lecture manuelle d'Emmanuel du {ov.get('date', '')})")
    return {
        'key': key,
        'phase': E.PHASE.get(key, key),
        'conf': 1.0,
        'note': float(E.BASE.get(key, 0)),
        'texte': texte,
        'thr': None,
        'points': [],
        'idx': [],
        'manuel': True,
        'override': True,
        'zone': zone_of(key),
    }


def commentaire(e):
    """Texte d'accompagnement (fiches crypto / énergie / devises)."""
    if not e:
        return {'entry': False, 'texte': "Lecture d'Elliott indisponible."}
    base = e.get('texte') or 'Décompte indéterminé'
    conf = e.get('conf')
    conf_s = f" · confiance {round(conf * 100):d} %" if (conf is not None and not e.get('manuel')) else ''
    key = e.get('key')
    z = zone_of(key)
    entry = key in ZONE_VERTE
    if e.get('manuel'):
        return {'entry': entry, 'zone': z, 'texte': base}
    if key == 'indet':
        suite = "La lecture automatique est indéterminée : pas de zone d'entrée retenue (entrée en fin de vague 2, fin de vague 4 ou vague C)."
    elif entry:
        suite = "Zone verte d'entrée (fin de vague 2, fin de vague 4 ou vague C)."
    elif z == 'rouge':
        suite = "Zone rouge : aucune entrée (vague 1, 3, 5, A ou B). Le signal Achat/Vente affiché est au mieux Neutre, la note /100 est plafonnée à 40."
    else:
        suite = "Hors zone d'entrée (entrée seulement en fin de vague 2, fin de vague 4 ou vague C)."
    return {'entry': entry, 'zone': z, 'texte': f"{base}{conf_s}. {suite}"}


def appliquer_av(av, ell):
    """Plafond du signal Achat/Vente *affiché* en zone rouge : pas de label Achat, au mieux Neutre.

    Le score brut (timing technique) est conservé dans score / score_raw.
    """
    if not av or av.get('score') is None:
        return av
    key = None
    if isinstance(ell, dict):
        key = ell.get('key')
    elif isinstance(ell, str):
        key = ell
    raw = float(av['score'])
    av['score_raw'] = av.get('score_raw', raw)
    if key in ZONE_ROUGE and raw >= AV_ACHAT:
        av['label'] = 'Neutre'
        av['score_affiche'] = AV_NEUTRE_MAX
        av['cap_zone'] = 'rouge'
    else:
        av['score_affiche'] = raw
        av.pop('cap_zone', None)
    return av
