#!/usr/bin/env python3
"""Recalcule data/good_invest.json (Meilleures entrées) après les notes ; t537u : à lancer après apply_sentiment.py."""
import os, sys
from pathlib import Path
ROOT = Path(os.environ.get('APEX_ROOT') or Path(__file__).resolve().parent.parent)
sys.path.insert(0, str(ROOT))
from apex import good_invest  # noqa: E402
out = good_invest.build()
print('Meilleures entrées :', out['n'])
