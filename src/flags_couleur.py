"""Couleur de la note APEX /100 et drapeau TradingView (t337u : 5 tranches de 20).

La couleur vient UNIQUEMENT de la note APEX /100 affichée sur le site
(après overrides), copiée telle quelle. Pas de score AV, pas de milieux ±33.

Échelle (notes arrondies au point, 5 tranches de 20) :

  0 à <20   violet   — drapeau TV : purple
  20 à <40  rouge    — drapeau TV : red
  40 à <60  jaune    — drapeau TV : orange (pas de drapeau jaune sur TradingView)
  60 à <80  vert     — drapeau TV : green
  80 à 100  cyan     — drapeau TV : cyan (pas bleu)

Les barres Achat/Vente et sentiment (t327u) restent en 5 tranches égales de 20 points (0–100), indépendantes de la note /100.
Repères de marché et actifs sans note : pas de drapeau.
"""

# Arrêts du dégradé (position = note × 10). Palier constant dans chaque bande.
VIOLET = (157, 84, 255)   # #9d54ff
ROUGE = (255, 45, 45)     # #ff2d2d
JAUNE = (255, 212, 0)     # #ffd400
VERT = (34, 197, 94)      # #22c55e
CYAN = (0, 229, 255)      # #00e5ff

GRAD = [
    (0, VIOLET), (15, VIOLET),
    (20, ROUGE), (35, ROUGE),
    (40, JAUNE), (55, JAUNE),
    (60, VERT), (75, VERT),
    (80, CYAN), (100, CYAN),
]

# Bande site → code drapeau TradingView
TV_OF = {
    'violet': 'purple',
    'rouge': 'red',
    'jaune': 'orange',
    'vert': 'green',
    'cyan': 'cyan',
}
FR = {
    'purple': 'violet', 'red': 'rouge', 'orange': 'orange',
    'green': 'vert', 'cyan': 'cyan', 'violet': 'violet',
    'yellow': 'jaune', 'none': 'aucun',
}
HEX_BANDE = {
    'violet': '#9d54ff',
    'rouge': '#ff2d2d',
    'jaune': '#ffd400',
    'vert': '#22c55e',
    'cyan': '#00e5ff',
}
# Ancienne échelle (pour le fichier d'écart seulement)
ANCIEN_SEUILS = (
    (1.0, 1.5, 'red'),
    (2.0, 4.5, 'orange'),
    (5.0, 8.0, 'green'),
    (8.5, 10.0, 'cyan'),
)


def av_pos(s):
    """Note AV −100…+100 → position 0–100 sur la barre (affichage curseur, pas le drapeau)."""
    return (max(-100.0, min(100.0, float(s))) + 100.0) / 2.0


def grgb(v):
    v = max(0.0, min(100.0, float(v)))
    for i in range(1, len(GRAD)):
        p1, c1 = GRAD[i - 1]
        p2, c2 = GRAD[i]
        if v <= p2:
            t = 0.0 if p2 == p1 else (v - p1) / (p2 - p1)
            return tuple(int(round(c1[j] + (c2[j] - c1[j]) * t)) for j in range(3))
    return GRAD[-1][1]


def hex_of(rgb):
    return '#{:02x}{:02x}{:02x}'.format(*rgb)


def bande_from_apex10(note):
    """Note /100 → nom de bande site (violet/rouge/jaune/vert/cyan), ou None."""
    if note is None:
        return None
    try:
        n = float(note)
    except (TypeError, ValueError):
        return None
    if n < 20:
        return 'violet'
    if n < 40:
        return 'rouge'
    if n < 60:
        return 'jaune'
    if n < 80:
        return 'vert'
    return 'cyan'


def flag_from_apex10(note):
    """Note APEX /100 affichée → code drapeau TradingView (purple/red/orange/green/cyan/none)."""
    b = bande_from_apex10(note)
    if not b:
        return 'none'
    return TV_OF[b]


def hex_from_apex10(note):
    """Note /100 → hex site (couleur de bande, sans interpolation)."""
    b = bande_from_apex10(note)
    if not b:
        return None
    return HEX_BANDE[b]


def flag_from_pos(pos):
    """Position 0–100 (= note /100) → drapeau TV."""
    if pos is None:
        return 'none'
    return flag_from_apex10(float(pos))


def flag_ancien_from_apex10(note):
    """Ancienne échelle (1–1,5 rouge ; 2–4,5 orange ; 5–8 vert ; 8,5–10 cyan)."""
    if note is None:
        return 'none'
    n = float(note)
    for lo, hi, code in ANCIEN_SEUILS:
        if lo - 1e-9 <= n <= hi + 1e-9:
            return code
    return 'none'


def couleur_apex10(note):
    """Note /100 → (code TV, hex site, position 0–100)."""
    if note is None:
        return 'none', None, None
    n = float(note)
    pos = n
    return flag_from_apex10(n), hex_from_apex10(n), pos
