"""Compare les notes APEX /100 avant et après un recalcul. Signale les gros écarts."""
from __future__ import annotations
import json
from pathlib import Path

from . import paths

JSON_FILES = (
    'pays.json', 'secteurs.json', 'obligations.json', 'metaux.json',
    'energie.json', 'crypto_fiches.json', 'apex_bars.json', 'tabs_data.json',
    'achatvente.json', 'good_invest.json',
)

# Seuil « gros écart » : ne pas publier (écart de note ou note devenue vide).
MAX_ABS = 15
MAX_N_ABS_HALF = 25  # trop de mouvements ≥ 5 points = suspect hors clôture hebdo


def _walk(o, out, parent_key=''):
    if isinstance(o, dict):
        a = o.get('apex10') or o.get('apex10_instrument')
        tv = o.get('tv') or o.get('fiche_tv') or o.get('symbol') or o.get('ticker') or o.get('key') or o.get('sym')
        if a and isinstance(a, dict) and not tv and parent_key and (':' in str(parent_key) or str(parent_key).isupper()):
            tv = parent_key
        if a and isinstance(a, dict) and tv:
            note = a.get('note')
            out.append({
                'tv': str(tv),
                'nom': o.get('nom') or o.get('name') or o.get('titre') or '',
                'note': note,
                'display': a.get('display'),
                'flag': a.get('flag'),
            })
        for k, v in o.items():
            if k in ('series', 'historique', 'ohlc', 'components', 'charts'):
                continue
            _walk(v, out, k)
    elif isinstance(o, list):
        for v in o:
            _walk(v, out, parent_key)


def collect(data_dir: Path | None = None) -> dict:
    data_dir = Path(data_dir or paths.data_dir())
    rows = []
    for fn in JSON_FILES:
        p = data_dir / fn
        if not p.exists():
            continue
        try:
            _walk(json.loads(p.read_text(encoding='utf-8')), rows, fn)
        except Exception as e:
            print('note_diff: lecture impossible', fn, e)
    by = {}
    for r in rows:
        k = r['tv']
        if k not in by or (by[k].get('note') is None and r.get('note') is not None):
            by[k] = r
    return by


def backup_files(dest: Path, data_dir: Path | None = None) -> list[str]:
    data_dir = Path(data_dir or paths.data_dir())
    dest.mkdir(parents=True, exist_ok=True)
    saved = []
    for fn in JSON_FILES + ('index.html',):
        src = data_dir / fn if fn != 'index.html' else paths.root() / 'index.html'
        if src.exists():
            (dest / Path(fn).name).write_bytes(src.read_bytes())
            saved.append(fn)
    return saved


def restore_files(src: Path, data_dir: Path | None = None) -> None:
    data_dir = Path(data_dir or paths.data_dir())
    for p in src.iterdir():
        if not p.is_file():
            continue
        dest = paths.root() / 'index.html' if p.name == 'index.html' else data_dir / p.name
        dest.write_bytes(p.read_bytes())
        print('note_diff: restauré', dest)


def _bande(note):
    if note is None:
        return None
    try:
        from apex.score import bande_couleur
        return bande_couleur(note)
    except Exception:
        n = float(note)
        if n < 20: return 'violet'
        if n < 40: return 'rouge'
        if n < 60: return 'jaune'
        if n < 80: return 'vert'
        return 'cyan'


def _count_bandes(by):
    out = {}
    for v in by.values():
        b = _bande(v.get('note'))
        if b:
            out[b] = out.get(b, 0) + 1
    return out


def compare(before: dict, after: dict) -> dict:
    tvs = sorted(set(before) | set(after), key=str)
    changes = []
    appeared, disappeared = [], []
    for tv in tvs:
        b, a = before.get(tv), after.get(tv)
        bn = None if not b else b.get('note')
        an = None if not a else a.get('note')
        if bn is None and an is None:
            continue
        if b is None or bn is None:
            if an is not None:
                appeared.append({'tv': tv, 'nom': (a or {}).get('nom'), 'note': an})
            continue
        if a is None or an is None:
            disappeared.append({'tv': tv, 'nom': (b or {}).get('nom'), 'note': bn})
            continue
        try:
            d = float(an) - float(bn)
        except (TypeError, ValueError):
            continue
        if abs(d) < 1e-9:
            continue
        changes.append({
            'tv': tv,
            'nom': (a or b).get('nom') or '',
            'avant': bn,
            'apres': an,
            'delta': round(d, 4),
            'couleur_avant': _bande(bn),
            'couleur_apres': _bande(an),
        })
    changes.sort(key=lambda x: (-abs(x['delta']), x['tv']))
    n_big = sum(1 for c in changes if abs(c['delta']) >= MAX_ABS)
    n_half = sum(1 for c in changes if abs(c['delta']) >= 5)
    blocking = (
        n_big > 0
        or n_half > MAX_N_ABS_HALF
        or len(disappeared) > 5
    )
    couleurs_avant = _count_bandes(before)
    couleurs_apres = _count_bandes(after)
    changements_couleur = {}
    for c in changes:
        a, b_ = c.get('couleur_avant'), c.get('couleur_apres')
        if a and b_ and a != b_:
            k = f'{a}→{b_}'
            changements_couleur[k] = changements_couleur.get(k, 0) + 1
    # aussi les notes inchangées ne changent pas de bande
    n_coul = sum(changements_couleur.values())
    return {
        'n_avant': sum(1 for v in before.values() if v.get('note') is not None),
        'n_apres': sum(1 for v in after.values() if v.get('note') is not None),
        'n_identiques': (
            sum(1 for tv in set(before) & set(after)
                if before[tv].get('note') is not None
                and after[tv].get('note') is not None
                and float(before[tv]['note']) == float(after[tv]['note']))
        ),
        'n_changements': len(changes),
        'n_delta_ge_0_5': n_half,
        'n_delta_ge_15': n_big,
        'n_apparus': len(appeared),
        'n_disparus': len(disappeared),
        'couleurs_avant': couleurs_avant,
        'couleurs_apres': couleurs_apres,
        'n_changements_couleur': n_coul,
        'changements_couleur': changements_couleur,
        'blocking': blocking,
        'seuil_abs': MAX_ABS,
        'changements': changes,
        'apparus': appeared,
        'disparus': disappeared,
    }


def write(report: dict, dest: Path | None = None) -> Path:
    dest = dest or (paths.data_dir() / 'notes_diff.json')
    dest.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(
        'note_diff: changements', report['n_changements'],
        'delta>=15', report['n_delta_ge_15'],
        'apparus', report['n_apparus'],
        'disparus', report['n_disparus'],
        'couleurs', report.get('changements_couleur'),
        'blocking', report['blocking'],
    )
    for c in report['changements'][:30]:
        print(f"  {c['tv']}  {c['avant']} → {c['apres']}  ({c['delta']:+g})  {c['nom']}")
    if len(report['changements']) > 30:
        print(f"  … +{len(report['changements'])-30} lignes dans {dest}")
    return dest
