"""Note APEX /10 — calcul unique dans apex.score (t329u).

50 % fondamental + 50 % technique (Elliott, structure, Fibonacci, figure,
RSI, MACD, CCI). Sans fondamental, le technique est renormalisé à 100 %.
Les bonus Elliott ne s'appliquent que sur un comptage manuel. Une note ≥ 8
exige un AV Achat fort et une confirmation. Les couleurs découlent de la
note affichée.
"""
from __future__ import annotations
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from apex.score import (  # noqa: F401
    av_pos, bande_couleur, collect_parts, compute, divergence_haussiere,
    divergence_of, elliott_fiable, elliott_key_of, flag_from_apex10, flag_tv,
    fmt10, fond_penalty, montant_template, pts_from_score, round_half,
    technique_weights, TECH_ORDER,
)
from apex.config import regles as load_regles
import flags_couleur as FC  # noqa: F401

_r = load_regles()['note_apex']
NOTE_MIN = float(_r['note_min'])
NOTE_MAX = float(_r['note_max'])
NOTE_CYAN = float(load_regles()['cyan']['note_min'])
W_AV = float(_r.get('poids_technique', _r.get('poids_timing', 0.5)))
W_FOND = float(_r.get('poids_fondamental', 0.5))
FOND_SEUIL = float(_r.get('fond_seuil', 40))
FOND_PEN_MAX = float(_r.get('fond_pen_max', 2))
