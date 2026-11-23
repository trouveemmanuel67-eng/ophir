"""Instantané hebdomadaire durable des notes APEX /10, AV, sentiment et zone Elliott.

Écrit data/historique_notes/AAAA-MM-JJ.json et met à jour index.json.
À lancer après build_apex10 (ou en fin de pipeline hebdomadaire).
N'invente aucune note : recopie les valeurs déjà calculées et publiées.
"""
import json, os, datetime as D
from zoneinfo import ZoneInfo
from collections import OrderedDict

B = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data')
OUT = os.path.join(B, 'historique_notes')
PARIS = ZoneInfo('Europe/Paris')


def load(name):
    p = os.path.join(B, name)
    if not os.path.exists(p):
        return None
    with open(p) as f:
        return json.load(f)


def pack(sym, nom, section, av=None, sent=None, ell=None, apex=None, extra=None):
    av = av or {}
    sent = sent or {}
    ell = ell or {}
    apex = apex or {}
    rec = {
        'symbole': sym,
        'nom': nom,
        'section': section,
        'note': apex.get('note'),
        'note_affichage': apex.get('display'),
        'drapeau': apex.get('flag'),
        'av': av.get('score') if isinstance(av, dict) else av,
        'av_label': av.get('label') if isinstance(av, dict) else None,
        'sentiment': sent.get('value') if isinstance(sent, dict) else sent,
        'sentiment_label': sent.get('label') if isinstance(sent, dict) else None,
        'elliott': (ell.get('key') if isinstance(ell, dict) else ell) or None,
        'elliott_zone': (ell.get('zone') if isinstance(ell, dict) else None) or None,
        'elliott_phase': (ell.get('phase') if isinstance(ell, dict) else None) or None,
    }
    if extra:
        rec.update(extra)
    return rec


def collect():
    items = []
    seen = set()

    def add(*a, **k):
        rec = pack(*a, **k)
        ksy = rec['symbole'] or rec['nom']
        if not ksy or ksy in seen:
            return
        seen.add(ksy)
        items.append(rec)

    AB = load('apex_bars.json') or {}
    bars = AB.get('bars') or {}

    F = load('fondamentaux.json') or {}
    for sid, s in (F.get('sectors') or {}).items():
        for r in s.get('top') or []:
            tv = r.get('tv') or r.get('yahoo')
            bar = bars.get(tv) or {}
            add(tv, r.get('name'), 'USA – ' + (s.get('name') or sid),
                r.get('av') or bar.get('av'), r.get('sent') or bar.get('sent'),
                r.get('elliott') or bar.get('elliott'), r.get('apex10') or bar.get('apex10'))

    SG = load('secteurs.json') or {}
    for s in SG.get('sectors') or []:
        add(s.get('tv') or s.get('sym'), s.get('nom') or s.get('name'), 'USA – secteurs',
            s.get('av'), s.get('sent'), s.get('elliott'), s.get('apex10'))

    P = load('pays.json') or {}
    for C in P.get('countries') or []:
        pays = C.get('nom') or C.get('cc')
        h = C.get('head') or {}
        add(h.get('tv'), h.get('nom') or ('Marché ' + pays), pays + ' – Marché',
            h.get('av'), h.get('sent'), h.get('elliott'), h.get('apex10'))
        for r in C.get('rows') or []:
            sec = r.get('nom') or ''
            add(r.get('tv'), f'{pays} – {sec}', pays + ' – secteur',
                r.get('av'), r.get('sent'), r.get('elliott'), r.get('apex10'))
            for t in ((r.get('fond') or {}).get('top') or []):
                tv = t.get('tv') or t.get('yahoo')
                bar = bars.get(tv) or {}
                add(tv, t.get('name'), f'{pays} – {sec}',
                    t.get('av') or bar.get('av'), t.get('sent') or bar.get('sent'),
                    t.get('elliott') or bar.get('elliott'), t.get('apex10') or bar.get('apex10'))

    MT = load('metaux.json') or {}
    for r in MT.get('rows') or []:
        add(r.get('tv') or r.get('nom'), r.get('nom'), 'Métaux précieux',
            r.get('av'), r.get('sent'), r.get('elliott'), r.get('apex10'))
        ml = r.get('mlist') or {}
        for it in [ml.get('head')] + list(ml.get('items') or []):
            if not it:
                continue
            add(it.get('tv'), it.get('nom') or it.get('name'), 'Métaux précieux – ' + (r.get('nom') or ''),
                it.get('av'), it.get('sent'), it.get('elliott'), it.get('apex10'))

    CF = load('crypto_fiches.json') or {}
    for a in (CF.get('assets') or CF.get('fiches') or {}).get('assets') if False else (CF.get('assets') or []):
        add(a.get('tv') or a.get('sym'), a.get('nom'), 'Crypto',
            a.get('av'), a.get('sent'), a.get('elliott'), a.get('apex10'))

    # crypto_fiches structure may nest under fiches
    if not any(x['section'] == 'Crypto' for x in items):
        pack_cf = CF.get('fiches') or CF
        for a in pack_cf.get('assets') or []:
            add(a.get('tv') or a.get('sym'), a.get('nom'), 'Crypto',
                a.get('av'), a.get('sent'), a.get('elliott'), a.get('apex10'))

    OB = load('obligations.json') or {}
    for s in OB.get('segments') or []:
        add(s.get('tv') or s.get('sym'), s.get('nom'), 'Obligations – ' + (s.get('nom') or ''),
            s.get('av'), s.get('sent'), s.get('elliott'), s.get('apex10'))
        for r in s.get('list') or []:
            add(r.get('tv') or r.get('yahoo'), r.get('name') or r.get('nom'), 'Obligations',
                r.get('av'), r.get('sent'), r.get('elliott'), r.get('apex10'))

    EN = load('energie.json') or {}
    for a in EN.get('assets') or []:
        if a.get('repere'):
            continue
        add(a.get('tv') or a.get('sym'), a.get('nom'), 'Énergie',
            a.get('av'), a.get('sent'), a.get('elliott'), a.get('apex10'))

    FX = load('fx_apex.json') or load('tabs_data.json') or {}
    # liquidités may live in tabs_data
    T2 = load('tabs_data.json') or {}
    fx = ((T2.get('liquidites') or {}).get('assets')
          or (T2.get('fx') or {}).get('assets') or [])
    for a in fx:
        add(a.get('tv') or a.get('sym') or a.get('pair'), a.get('nom'), 'Liquidités',
            a.get('av'), a.get('sent'), a.get('elliott'), a.get('apex10') or ((a.get('av') or {}).get('apex10')))

    return items


def main(date=None):
    now = D.datetime.now(PARIS)
    day = date or now.date().isoformat()
    os.makedirs(OUT, exist_ok=True)
    items = collect()
    n_note = sum(1 for x in items if x.get('note') is not None)
    snap = {
        'date': day,
        'genere': now.strftime('%Y-%m-%d %H:%M'),
        'fuseau': 'Europe/Paris',
        'n': len(items),
        'n_avec_note': n_note,
        'actifs': items,
    }
    path = os.path.join(OUT, day + '.json')
    with open(path, 'w') as f:
        json.dump(snap, f, ensure_ascii=False)
    # index
    idx_p = os.path.join(OUT, 'index.json')
    if os.path.exists(idx_p):
        idx = json.load(open(idx_p))
    else:
        idx = {'snapshots': []}
    rec = {'date': day, 'fichier': day + '.json', 'n': len(items), 'n_avec_note': n_note,
           'genere': snap['genere']}
    idx['snapshots'] = [s for s in idx.get('snapshots') or [] if s.get('date') != day]
    idx['snapshots'].append(rec)
    idx['snapshots'].sort(key=lambda s: s['date'])
    idx['dernier'] = rec
    with open(idx_p, 'w') as f:
        json.dump(idx, f, ensure_ascii=False, indent=2)
    print('snapshot', path, 'n', len(items), 'avec note', n_note, 'bytes', os.path.getsize(path))
    return path


if __name__ == '__main__':
    main()
