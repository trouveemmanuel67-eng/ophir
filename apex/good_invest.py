"""Liste GOOD INVEST précalculée (seuil et exclusions lus dans config/regles.json)."""
from __future__ import annotations
import json
from pathlib import Path

from . import paths
from .config import actif, regles
from .score import montant_template, fmt10, bande_couleur


def _held():
    data = paths.data_dir()
    held = set()

    def add(p):
        if not p or not isinstance(p, dict):
            return
        st = str(p.get('statut') or 'active').lower()
        if st in ('solde', 'sold', 'ferme', 'closed', 'annule'):
            return
        for s in (p.get('fiche_tv'), p.get('tv_note'), p.get('tv'), p.get('ticker'), p.get('yahoo'), p.get('sym')):
            if not s:
                continue
            u = str(s).strip()
            if not u or u == 'PEA':
                continue
            held.add(u)
            held.add(u.upper())
            if ':' in u:
                held.add(u.split(':')[-1])

    for fn in ('positions.json', 'positions_revolut.json', 'positions_revolutx.json'):
        p = data / fn
        if not p.exists():
            continue
        raw = json.loads(p.read_text(encoding='utf-8'))
        for pos in raw.get('positions') or []:
            add(pos)
    return held


def _zone_rouge(ell, tv=None, bars=None):
    """True si le titre est en vague rouge (aucune entrée)."""
    cfg = (regles().get('elliott') or {})
    if cfg.get('interdire_entree_zone_rouge', True) is False:
        return False
    if (regles().get('good_invest') or {}).get('exclure_zone_rouge', True) is False:
        return False
    rouges = set(cfg.get('vagues_rouges') or [])
    key = zone = None
    if isinstance(ell, dict):
        key, zone = ell.get('key'), ell.get('zone')
    elif isinstance(ell, str):
        key = ell
    if not key and tv and bars and tv in bars:
        e = (bars.get(tv) or {}).get('elliott') or {}
        if isinstance(e, dict):
            key, zone = e.get('key'), e.get('zone')
        elif isinstance(e, str):
            key = e
    return (key in rouges) or (zone == 'rouge')


def _is_held(tv, yahoo, held):
    for s in (tv, yahoo):
        if not s:
            continue
        u = str(s).strip()
        if u in held or u.upper() in held:
            return True
        if ':' in u and u.split(':')[-1] in held:
            return True
    return False


def build() -> dict:
    data = paths.data_dir()
    seuil = float(regles()['good_invest']['seuil'])
    bars = json.loads((data / 'apex_bars.json').read_text(encoding='utf-8')).get('bars') or {}
    held = _held()
    rows = []
    seen = set()
    def consider(tv, note_rec, av=None, nom=None, section=None, yahoo=None, ell=None):
        if not tv or not note_rec or note_rec.get('note') is None:
            return
        if float(note_rec['note']) < seuil:
            return
        if note_rec.get('cap') == 'moyenne':
            return
        if _zone_rouge(ell, tv, bars):
            return
        meta = actif(tv) or {}
        # t322u : hors univers (pays retirés) et titres seulement en positions
        if meta.get('univers') in ('hors', 'positions_seulement') or meta.get('visible') is False or meta.get('visible')=='positions':
            return
        if _is_held(tv, yahoo or meta.get('yahoo'), held):
            return
        if tv in seen:
            return
        seen.add(tv)
        note = float(note_rec['note'])
        br = meta.get('brokers') or {}
        rows.append({
            'tv': tv,
            'yahoo': yahoo or meta.get('yahoo'),
            'nom': nom or meta.get('nom') or tv,
            'note': note,
            'display': note_rec.get('display') or fmt10(note),
            'hex': note_rec.get('hex'),
            'flag': note_rec.get('flag'),
            'bande': bande_couleur(note),
            'av': av,
            'section': section or meta.get('section'),
            'montant': montant_template(note),
            'brokers': br,
        })

    # barres individuelles + enrichissement via config
    for tv, b in bars.items():
        a = (b or {}).get('apex10') or {}
        av = (b.get('av') or {}).get('score')
        consider(tv, a, av, ell=(b or {}).get('elliott'))

    def walk(obj):
        if isinstance(obj, dict):
            tv = obj.get('tv') or obj.get('sym') or obj.get('ticker')
            a = obj.get('apex10')
            av = (obj.get('av') or {}).get('score') if isinstance(obj.get('av'), dict) else None
            consider(tv, a, av, obj.get('etf') or obj.get('name') or obj.get('nom'), None, obj.get('yahoo') or obj.get('ticker') or obj.get('sym'), obj.get('elliott'))
            for v in obj.values():
                walk(v)
        elif isinstance(obj, list):
            for v in obj:
                walk(v)

    for fn in ('pays.json', 'metaux.json', 'energie.json', 'obligations.json', 'crypto_fiches.json', 'tabs_data.json'):
        fp = data / fn
        if fp.exists():
            walk(json.loads(fp.read_text(encoding='utf-8')))

    rows.sort(key=lambda r: (-r['note'], -(r.get('av') or 0), r['tv']))
    out = {
        'seuil': seuil,
        'n': len(rows),
        'liste': rows,
    }
    dest = data / 'good_invest.json'
    dest.write_text(json.dumps(out, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return out
