"""data/changements_du_jour.json : couleurs, sauts de note, cours / Yahoo manquants."""
from __future__ import annotations
import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from . import paths
from .config import actif, actifs_by_tv
from .score import bande_couleur, flag_tv, fmt10

TZ = ZoneInfo('Europe/Paris')
SAUT = 3.0


def _now():
    return datetime.now(TZ)


def _hist_prev(data: Path, today: str):
    hist = data / 'historique_notes'
    if not hist.exists():
        return {}
    files = sorted(hist.glob('*.json'))
    prev = None
    for f in files:
        if f.stem < today:
            prev = f
        elif f.stem == today:
            break
    if not prev:
        return {}
    raw = json.loads(prev.read_text(encoding='utf-8'))
    # formats possibles : {tv: {note}} ou {notes: ...} ou liste
    if isinstance(raw, dict) and 'notes' in raw:
        raw = raw['notes']
    out = {}
    if isinstance(raw, dict):
        for k, v in raw.items():
            if k.startswith('_'):
                continue
            if isinstance(v, dict) and v.get('note') is not None:
                out[k] = v
            elif isinstance(v, (int, float)):
                out[k] = {'note': v}
    return out


def collect_current_notes(data: Path) -> dict:
    bars = json.loads((data / 'apex_bars.json').read_text(encoding='utf-8')).get('bars') or {}
    out = {}
    for tv, b in bars.items():
        a = (b or {}).get('apex10') or {}
        if a.get('note') is None:
            continue
        av = (b.get('av') or {})
        out[tv] = {
            'note': a['note'], 'display': a.get('display') or fmt10(a['note']),
            'flag': a.get('flag') or flag_tv(a['note']),
            'bande': bande_couleur(a['note']),
            'av': av.get('score'), 'date': b.get('date'),
        }
    return out


def build(saut=None) -> dict:
    data = paths.data_dir()
    r = json.loads((paths.config_dir() / 'regles.json').read_text())
    saut = saut if saut is not None else r.get('quotidien', {}).get('anomalie_saut_points', SAUT)
    today = _now().strftime('%Y-%m-%d')
    curr = collect_current_notes(data)
    prev = _hist_prev(data, today)
    couleurs, sauts = [], []
    for tv, rec in curr.items():
        old = prev.get(tv)
        if not old:
            continue
        if old.get('flag') and rec.get('flag') and old['flag'] != rec['flag']:
            couleurs.append({
                'tv': tv, 'nom': (actif(tv) or {}).get('nom') or tv,
                'note_avant': old.get('note'), 'note_apres': rec['note'],
                'couleur_avant': old.get('flag') or old.get('bande'),
                'couleur_apres': rec['flag'],
            })
        if old.get('note') is not None and abs(rec['note'] - old['note']) > saut:
            sauts.append({
                'tv': tv, 'type': 'saut_note',
                'note_avant': old['note'], 'note_apres': rec['note'],
                'delta': round(rec['note'] - old['note'], 1),
            })
    # anomalies cours / yahoo depuis un rapport de fetch s'il existe
    fetch_rep = data / '_fetch_report.json'
    cours_absents, yahoo_manquant = [], []
    if fetch_rep.exists():
        fr = json.loads(fetch_rep.read_text(encoding='utf-8'))
        for it in fr.get('cours_absent') or []:
            cours_absents.append({'tv': it.get('tv'), 'yahoo': it.get('yahoo'), 'type': 'cours_absent'})
        for it in fr.get('yahoo_introuvable') or []:
            yahoo_manquant.append({'tv': it.get('tv'), 'yahoo': it.get('yahoo'), 'type': 'yahoo_introuvable'})
    out = {
        'date': today,
        'maj': _now().strftime('%Y-%m-%dT%H:%M:%S%z'),
        'maj_label': _now().strftime('%d/%m/%Y %H:%M') + ' Europe/Paris',
        'n_notes': len(curr),
        'n_changements_couleur': len(couleurs),
        'n_anomalies': len(sauts) + len(cours_absents) + len(yahoo_manquant),
        'changements_couleur': couleurs,
        'anomalies': sauts + cours_absents + yahoo_manquant,
    }
    dest = data / 'changements_du_jour.json'
    dest.write_text(json.dumps(out, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return out
