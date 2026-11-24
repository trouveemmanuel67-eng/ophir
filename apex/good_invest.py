"""Liste GOOD INVEST précalculée (seuil et exclusions lus dans config/regles.json)."""
from __future__ import annotations
import json
from pathlib import Path

from . import paths
from .config import actif, regles
from .score import montant_template, montant_template_metaux, fmt10, bande_couleur, metaux_band, metaux_cfg


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
    mx_cfg = metaux_cfg()
    seuil_metaux = float((regles().get('apex_metaux') or {}).get('gi_seuil', mx_cfg.get('gi_seuil', 175)))
    # APE-25 : onglet d'origine de chaque tv (les barres individuelles n'ont pas de classe)
    TAB = {}
    def _tabs(obj, cl):
        if isinstance(obj, dict):
            if obj.get('tv') and isinstance(obj.get('apex10'), dict):
                TAB.setdefault(obj['tv'], cl)
            for v in obj.values():
                _tabs(v, cl)
        elif isinstance(obj, list):
            for v in obj:
                _tabs(v, cl)
    for fn, cl in (('metaux.json', 'metaux'), ('obligations.json', 'obligations'), ('energie.json', 'energie')):
        if (data / fn).exists():
            _tabs(json.loads((data / fn).read_text(encoding='utf-8')), cl)
    def consider(tv, note_rec, av=None, nom=None, section=None, yahoo=None, ell=None, classe=None):
        if not tv or not note_rec or note_rec.get('note') is None:
            return
        if classe is None:
            classe = TAB.get(tv)
        if note_rec.get('cap') == 'moyenne':
            return
        meta = actif(tv) or {}
        sec = section or meta.get('section') or ''
        # t461u : plus d'exclusion « zone Elliott rouge » pour les métaux précieux.
        is_metaux = (classe == 'metaux') or str(sec).startswith('Métaux')
        is_crypto = (
            (classe == 'crypto')
            or str(sec).startswith('Crypto')
            or str(tv).upper() in {'BTC', 'ETH', 'SOL', 'MSTR', 'XRP'}
            or (classe != 'etf_devise' and 'hype_attente' in str(note_rec.get('cap') or '') and str(tv).upper() in {'BTC','ETH','SOL','MSTR','XRP'})
        )
        is_etf_devise = (
            (classe == 'etf_devise') or str(sec).startswith('Liquidités – ETF')
            or note_rec.get('devise_points') is not None
            or str(note_rec.get('cap') or '').startswith('fond_nc')
        )
        if (str(tv).upper() == 'XRP') or (str(nom or '').lower() in ('ripple', 'xrp')):
            return
        if is_metaux and note_rec.get('scale') != 250:
            # laisser metaux.json fournir la note −50..250
            return
        if is_crypto and note_rec.get('scale') != 250:
            return
        # APE-25 : toute note −50..250 (obligations, énergie, devises, épargne…) suit le seuil 130 et la mise 250.
        is250 = note_rec.get('scale') == 250 or note_rec.get('total_max') == 250
        cut = seuil_metaux if (is_metaux or is_crypto or is_etf_devise or is250) else seuil
        if float(note_rec['note']) < cut:
            return
        if not is_metaux and not is_crypto and not is_etf_devise and not is250 and _zone_rouge(ell, tv, bars):
            return
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
        if is_metaux or is_crypto or is_etf_devise or is250:
            band = metaux_band(note)
            montant = montant_template_metaux(note)
            scale = 250
            tab = 'metaux' if is_metaux else ('crypto' if is_crypto else ('liquidites' if is_etf_devise else (classe or 'autres')))
            bande = note_rec.get('band') or band['id']
            hx = note_rec.get('hex') or band['hex']
            fl = note_rec.get('flag') or band['flag']
        else:
            montant = montant_template(note)
            scale = 100
            tab = classe
            bande = bande_couleur(note)
            hx = note_rec.get('hex')
            fl = note_rec.get('flag')
        rows.append({
            'tv': tv,
            'yahoo': yahoo or meta.get('yahoo'),
            'nom': nom or meta.get('nom') or tv,
            'note': note,
            'display': note_rec.get('display') or fmt10(note),
            'hex': hx,
            'flag': fl,
            'bande': bande,
            'av': av,
            'section': section or meta.get('section'),
            'montant': montant,
            'brokers': br,
            'scale': scale,
            'tab': tab,
        })

    # barres individuelles + enrichissement via config
    for tv, b in bars.items():
        a = (b or {}).get('apex10') or {}
        av = (b.get('av') or {}).get('score')
        consider(tv, a, av, ell=(b or {}).get('elliott'))

    def walk(obj, classe=None):
        if isinstance(obj, dict):
            tv = obj.get('tv') or obj.get('sym') or obj.get('ticker')
            a = obj.get('apex10')
            av = (obj.get('av') or {}).get('score') if isinstance(obj.get('av'), dict) else None
            consider(tv, a, av, obj.get('etf') or obj.get('name') or obj.get('nom'), None, obj.get('yahoo') or obj.get('ticker') or obj.get('sym'), obj.get('elliott'), classe=classe)
            etf = obj.get('etf_local')
            if isinstance(etf, dict) and etf.get('ok') and etf.get('tv'):
                consider(etf.get('tv'), etf.get('apex10'), None, etf.get('nom') or etf.get('court'), 'Liquidités – ETF par devise', etf.get('yahoo'), None, classe='etf_devise')
            for v in obj.values():
                walk(v, classe)
        elif isinstance(obj, list):
            for v in obj:
                walk(v, classe)

    CL = {'metaux.json': 'metaux', 'crypto_fiches.json': 'crypto', 'obligations.json': 'obligations', 'energie.json': 'energie'}
    for fn in ('pays.json', 'metaux.json', 'energie.json', 'obligations.json', 'crypto_fiches.json', 'tabs_data.json'):
        fp = data / fn
        if fp.exists():
            doc = json.loads(fp.read_text(encoding='utf-8'))
            if fn == 'tabs_data.json':
                for k, v in doc.items():
                    if k != 'actions':
                        walk(v, classe=k if k in ('energie', 'liquidites', 'crypto') else None)
            else:
                walk(doc, classe=CL.get(fn))

    rows.sort(key=lambda r: (-r['note'], -(r.get('av') or 0), r['tv']))
    out = {
        'seuil': seuil,
        'n': len(rows),
        'liste': rows,
    }
    dest = data / 'good_invest.json'
    dest.write_text(json.dumps(out, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return out
