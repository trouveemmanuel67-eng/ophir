"""Attache la note APEX /10 à toutes les listes publiées (après le recalcul AV)."""
import os as _os
_APEX_ROOT = _os.path.abspath(_os.environ.get('APEX_ROOT') or _os.path.join(_os.path.dirname(__file__), '..'))
import json, os, sys, datetime as D
from zoneinfo import ZoneInfo
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import note_apex as N
import liquidite_crypto as LQ

B = _APEX_ROOT + '/data/'
NOW = D.datetime.now(ZoneInfo('Europe/Paris'))


def load(name):
    p = B + name
    if not os.path.exists(p):
        return None
    return json.load(open(p))


def save(name, obj):
    p = B + name
    json.dump(obj, open(p, 'w'), ensure_ascii=False)
    print('wrote', p, 'bytes', os.path.getsize(p), flush=True)


def ell_of(obj):
    if not obj:
        return None
    if 'elliott' in obj and obj['elliott']:
        return obj['elliott']
    av = obj.get('av') or {}
    comps = av.get('components') or []
    for c in comps:
        if c.get('elliott') and (c['elliott'].get('key') if isinstance(c['elliott'], dict) else None):
            return c['elliott']
    return None


def fond_index(F):
    """tv / yahoo / ticker → score fondamental 0-100."""
    idx = {}
    if not F:
        return idx
    def add(r):
        if not r or not isinstance(r, dict) or r.get('score') is None:
            return
        sc = float(r['score'])
        for k in (r.get('tv'), r.get('yahoo'), r.get('ticker'), r.get('symbol')):
            if k:
                idx.setdefault(k, sc)
    for sec in (F.get('sectors') or {}).values():
        for r in sec.get('top') or []:
            add(r)
    return idx


def fond_lookup(idx, *keys):
    for k in keys:
        if k and k in idx:
            return idx[k]
    return None


def attach(obj, av=None, fond=None, elliott=None, divergence=None, classe=None):
    if av is None and obj is not None:
        av = (obj.get('av') or {}).get('score') if isinstance(obj.get('av'), dict) else None
    if elliott is None:
        elliott = ell_of(obj)
    if divergence is None and obj is not None:
        divergence = N.divergence_of(obj)
    parts = N.collect_parts(obj) if obj is not None else None
    rec = N.compute(av, fond, elliott, divergence=divergence, parts=parts, classe=classe)
    if obj is not None:
        obj['apex10'] = rec
    return rec


def fond_aggregate(members, idx, weight_key='w'):
    """Moyenne pondérée des fondamentaux disponibles (ignore les membres sans note)."""
    num = den = 0.0
    n = 0
    for m in members or []:
        if not isinstance(m, dict):
            sc = fond_lookup(idx, m)
            w = 1.0
            if sc is None:
                continue
            num += sc * w
            den += w
            n += 1
            continue
        sc = fond_lookup(idx, m.get('tv'), m.get('yahoo'), m.get('ticker'), m.get('symbol'), m.get('sym'))
        w = m.get(weight_key)
        if w is None:
            w = m.get('weight')
        if sc is None:
            continue
        w = float(w) if w is not None else 1.0
        num += sc * w
        den += w
        n += 1
    if den <= 0 or n == 0:
        return None
    return num / den



def moyenne_apex(notes, detail):
    """Moyenne des notes /10 affichées, arrondie au demi-point (règle t311u)."""
    import flags_couleur as FC
    if not notes:
        rec = N.compute(None)
        rec['cap'] = 'moyenne'
        rec['n_moy'] = 0
        rec['detail'] = detail
        return rec
    avg = N.round_half(sum(notes) / len(notes))
    avg = max(N.NOTE_MIN, min(N.NOTE_MAX, avg))
    pos = avg * 10.0
    return {
        'note': avg, 'display': N.fmt10(avg),
        'hex': FC.hex_from_apex10(avg),
        'flag': N.flag_from_apex10(avg), 'pos': pos,
        'cap': 'moyenne', 'fond': None, 'brut': None,
        'n_moy': len(notes), 'detail': detail,
    }


def moyenne_av(scores):
    import ind_core as K
    if not scores:
        return {'score': None, 'label': '–', 'n': 0, 'source': 'actifs_affiches'}
    sc = round(sum(scores) / len(scores), 1)
    return {'score': sc, 'label': K.lab_av(sc), 'n': len(scores), 'source': 'actifs_affiches'}


DETAIL_SECTION = (
    "Moyenne des notes /10 des actifs affichés dans la section "
    "(hors panier théorique non négociable), arrondie au demi-point."
)


def main():
    F = load('fondamentaux.json')
    idx = fond_index(F)
    # enrich index with country tops (added below as we walk pays)

    n_ok = n_na = 0

    def count(rec):
        nonlocal n_ok, n_na
        if rec and rec.get('note') is not None:
            n_ok += 1
        else:
            n_na += 1

    # --- pays : first, index country tops ---
    P = load('pays.json')
    if P:
        for C in P.get('countries') or []:
            for r in C.get('rows') or []:
                for t in ((r.get('fond') or {}).get('top') or []):
                    if t.get('score') is not None:
                        for k in (t.get('tv'), t.get('yahoo'), t.get('ticker')):
                            if k:
                                idx.setdefault(k, float(t['score']))

    # --- apex_bars (actions et autres fiches compactes) ---
    AB = load('apex_bars.json')
    if AB:
        for k, b in (AB.get('bars') or {}).items():
            if not b or not b.get('ok'):
                rec = N.compute(None)
                if b is not None:
                    b['apex10'] = rec
                count(rec)
                continue
            fond = fond_lookup(idx, k, b.get('tv'), b.get('yahoo'))
            rec = attach(b, (b.get('av') or {}).get('score'), fond, b.get('elliott'))
            count(rec)
        AB['apex10_generated'] = NOW.strftime('%Y-%m-%d %H:%M')
        save('apex_bars.json', AB)

    # --- secteurs USA ---
    SG = load('secteurs.json')
    if SG:
        for s in SG.get('sectors') or []:
            members = []
            key = s.get('sym') or s.get('key')
            sec = (F.get('sectors') or {}).get(key) if F else None
            if sec:
                members = [x for x in (sec.get('top') or []) if isinstance(x, dict)]
            fond = fond_aggregate(members, idx, 'weight')
            if s.get('av') is not None and 'av_instrument' not in s:
                avp = s.get('av') or {}
                s['av_instrument'] = {k: avp[k] for k in avp if k in ('score', 'label', 'score_raw', 'score_affiche', 'cap_zone')}
            inst_rec = N.compute((s.get('av_instrument') or s.get('av') or {}).get('score'), fond, s.get('elliott'), divergence=N.divergence_of(s), parts=N.collect_parts(s))
            s['apex10_instrument'] = inst_rec
            notes, avs = [], []
            # L'ETF de section est affiché en tête : il compte dans la moyenne.
            if inst_rec.get('note') is not None:
                notes.append(float(inst_rec['note']))
            sc = (s.get('av_instrument') or s.get('av') or {}).get('score')
            if sc is not None:
                avs.append(float(sc))
            for m in members:
                tv = m.get('tv') or m.get('ticker') or m.get('yahoo')
                bar = (AB or {}).get('bars', {}).get(tv) if AB else None
                rec = (bar or {}).get('apex10') or m.get('apex10')
                if rec and rec.get('note') is not None:
                    notes.append(float(rec['note']))
                avs_src = (bar or {}).get('av') or m.get('av') or {}
                sc = avs_src.get('score') if isinstance(avs_src, dict) else None
                if sc is not None:
                    avs.append(float(sc))
            s['apex10'] = moyenne_apex(notes, DETAIL_SECTION)
            count(s['apex10'])
            avg_av = moyenne_av(avs)
            if notes:
                s['av'] = dict(s.get('av_instrument') or s.get('av') or {})
                # On conserve le détail de l'ETF, mais le score/label de ligne
                # reflète la moyenne des actifs affichés.
                s['av']['score'] = avg_av['score']
                s['av']['label'] = avg_av['label']
                s['av']['n'] = avg_av['n']
                s['av']['source'] = 'actifs_affiches'
        # Note pays USA : moyenne des notes /10 des secteurs GICS visibles
        # (pas d'ETF « Marché USA » dédié, contrairement aux autres pays).
        notes=[]
        avs=[]
        for s in SG.get('sectors') or []:
            rec=s.get('apex10') or {}
            if rec.get('note') is not None:
                notes.append(float(rec['note']))
            av=(s.get('av') or {}).get('score')
            if av is not None:
                avs.append(float(av))
        if notes:
            import flags_couleur as FC
            import ind_core as K
            avg=N.round_half(sum(notes)/len(notes))
            avg=max(N.NOTE_MIN, min(N.NOTE_MAX, avg))
            pos=avg*10.0
            SG['apex10']={
                'note':avg,'display':N.fmt10(avg),
                'hex':FC.hex_from_apex10(avg),
                'flag':N.flag_from_apex10(avg),'pos':pos,
                'cap':'moyenne','fond':None,'brut':None,
                'n_moy':len(notes),
                'detail':'Moyenne des notes /10 des secteurs GICS du pays (même méthode que les lignes de section), arrondie au demi-point.',
            }
            if avs:
                sc=round(sum(avs)/len(avs),1)
                SG['av_pays']={'score':sc,'label':K.lab_av(sc),'n':len(avs)}
        save('secteurs.json', SG)

    # --- pays ---
    if P:
        for C in P.get('countries') or []:
            h = C.get('head') or {}
            attach(h, (h.get('av') or {}).get('score'), None, h.get('elliott'))  # ETF/indice : pas de fondamental
            count(h.get('apex10'))
            for r in C.get('rows') or []:
                if not r.get('covered'):
                    rec = N.compute(None)
                    r['apex10'] = rec
                    count(rec)
                    continue
                members = r.get('basket') or ((r.get('fond') or {}).get('top') or [])
                fond = fond_aggregate(members, idx)
                # Signal du panier/ETF conservé à part : la note de section
                # est la moyenne des titres affichés (t311u), pas du panier théorique.
                if r.get('av') is not None and 'av_panier' not in r:
                    avp = r.get('av') or {}
                    r['av_panier'] = {k: avp[k] for k in avp if k in ('score', 'label', 'score_raw', 'score_affiche', 'cap_zone')}
                if r.get('elliott') is not None and 'elliott_panier' not in r:
                    ep = r.get('elliott') or {}
                    if isinstance(ep, dict):
                        r['elliott_panier'] = {k: ep[k] for k in ep if k in ('key', 'phase', 'zone', 'conf', 'texte')}
                panier_rec = N.compute((r.get('av_panier') or r.get('av') or {}).get('score'), fond, r.get('elliott_panier') or r.get('elliott'), divergence=N.divergence_of(r), parts=N.collect_parts(r))
                r['apex10_panier'] = panier_rec
                notes, avs = [], []
                for t in ((r.get('fond') or {}).get('top') or []):
                    # la barre de l'action vient de apex_bars ; on y attache aussi pour la liste
                    tv = t.get('tv') or t.get('ticker')
                    bar = (AB or {}).get('bars', {}).get(tv) if AB else None
                    if bar and bar.get('apex10'):
                        t['apex10'] = bar['apex10']
                    else:
                        rec = attach(t, (bar or {}).get('av', {}).get('score') if bar else None,
                                     t.get('score'), (bar or {}).get('elliott'))
                        count(rec)
                    rec = t.get('apex10') or {}
                    if rec.get('note') is not None:
                        notes.append(float(rec['note']))
                    avs_src = (bar or {}).get('av') or t.get('av') or {}
                    sc = avs_src.get('score') if isinstance(avs_src, dict) else None
                    if sc is not None:
                        avs.append(float(sc))
                # ETF / indice sectoriel affiché comme instrument de la ligne : il compte aussi.
                if r.get('kind') in ('etf', 'index') and panier_rec.get('note') is not None:
                    notes.append(float(panier_rec['note']))
                    sc = (r.get('av_panier') or {}).get('score')
                    if sc is not None:
                        avs.append(float(sc))
                r['apex10'] = moyenne_apex(notes, DETAIL_SECTION)
                count(r['apex10'])
                avg_av = moyenne_av(avs)
                if notes:
                    r['av'] = avg_av
                else:
                    # Aucun titre affiché : pas de note, pas de signal trompeur du panier.
                    r['av'] = {'score': None, 'label': '–', 'n': 0, 'source': 'actifs_affiches'}
            # Bandeau pays = moyenne des notes /10 affichées des secteurs couverts
            # (même règle que le bandeau d'onglet), pas la note de l'ETF « Marché ».
            notes, avs, sents = [], [], []
            for r in C.get('rows') or []:
                rec = r.get('apex10') or {}
                if r.get('covered') and rec.get('note') is not None:
                    notes.append(float(rec['note']))
                av = (r.get('av') or {}).get('score')
                if r.get('covered') and av is not None:
                    avs.append(float(av))
                se = (r.get('sent') or {}).get('value')
                if r.get('covered') and se is not None:
                    sents.append(float(se))
            if notes:
                import flags_couleur as FC
                import ind_core as K
                avg = N.round_half(sum(notes) / len(notes))
                avg = max(N.NOTE_MIN, min(N.NOTE_MAX, avg))
                pos = avg * 10.0
                C['apex10'] = {
                    'note': avg, 'display': N.fmt10(avg),
                    'hex': FC.hex_from_apex10(avg),
                    'flag': N.flag_from_apex10(avg), 'pos': pos,
                    'cap': 'moyenne', 'fond': None, 'brut': None,
                    'n_moy': len(notes),
                    'detail': 'Moyenne des notes /10 des secteurs couverts du pays (même méthode que le bandeau de section), arrondie au demi-point.',
                }
                if avs:
                    sc = round(sum(avs) / len(avs), 1)
                    C['av_pays'] = {'score': sc, 'label': K.lab_av(sc), 'n': len(avs)}
                if sents:
                    sv = round(sum(sents) / len(sents), 1)
                    C['sent_pays'] = {'value': sv, 'label': K.lab_s(sv), 'n': len(sents)}
        P['apex10_generated'] = NOW.strftime('%Y-%m-%d %H:%M')
        save('pays.json', P)

    # --- obligations ---
    OB = load('obligations.json')
    if OB:
        for s in OB.get('segments') or []:
            if s.get('av') is not None and 'av_panier' not in s:
                avp = s.get('av') or {}
                s['av_panier'] = {k: avp[k] for k in avp if k in ('score', 'label', 'score_raw', 'score_affiche', 'cap_zone')}
            s['apex10_panier'] = N.compute((s.get('av_panier') or s.get('av') or {}).get('score'), None, s.get('elliott'), divergence=N.divergence_of(s), parts=N.collect_parts(s))
            notes, avs = [], []
            for r in s.get('list') or []:
                av = (r.get('av') or {}).get('score') if isinstance(r.get('av'), dict) else None
                # ETF obligataire : pas de fondamental ; AV souvent absent → « – »
                bar = (AB or {}).get('bars', {}).get(r.get('tv') or r.get('yahoo')) if AB else None
                if av is None and bar:
                    av = (bar.get('av') or {}).get('score')
                    r['apex10'] = bar.get('apex10') or N.compute(av, None, bar.get('elliott'), divergence=N.divergence_of(bar), parts=N.collect_parts(bar) or N.collect_parts(r))
                else:
                    r['apex10'] = N.compute(av, None, ell_of(r) or ell_of(s), divergence=N.divergence_of(r) or N.divergence_of(s), parts=N.collect_parts(r) or N.collect_parts(s))
                count(r['apex10'])
                rec = r.get('apex10') or {}
                if rec.get('note') is not None:
                    notes.append(float(rec['note']))
                if av is not None:
                    avs.append(float(av))
            s['apex10'] = moyenne_apex(notes, DETAIL_SECTION)
            count(s['apex10'])
            if notes:
                s['av'] = moyenne_av(avs)
            else:
                s['av'] = {'score': None, 'label': '–', 'n': 0, 'source': 'actifs_affiches'}
        save('obligations.json', OB)

    # --- métaux ---
    MT = load('metaux.json')
    if MT:
        for r in MT.get('rows') or []:
            rec_fut = attach(dict(r), (r.get('av') or {}).get('score'), None, r.get('elliott'))
            # on conserve la note du contrat continu, mais la note affichée
            # de la ligne devient la moyenne des instruments visibles (23/11/2026).
            r['apex10_futur'] = rec_fut
            ml = r.get('mlist') or {}
            notes=[]
            for it in [ml.get('head')] + list(ml.get('items') or []):
                if not it:
                    continue
                if it.get('skip_score'):
                    it['apex10'] = N.compute(None)
                    continue
                tv = it.get('tv') or it.get('ticker')
                bar = (AB or {}).get('bars', {}).get(tv) if AB else None
                fond = None if it.get('kind') in ('etc','spot') else fond_lookup(idx, tv, it.get('ticker'))
                av = (it.get('av') or {}).get('score') if isinstance(it.get('av'), dict) else None
                if av is None and bar:
                    av = (bar.get('av') or {}).get('score')
                rec = attach(it, av, fond, ell_of(it) or (bar or {}).get('elliott'))
                count(rec)
                if rec and rec.get('note') is not None:
                    notes.append(float(rec['note']))
            if notes:
                avg = N.round_half(sum(notes)/len(notes))
                avg = max(N.NOTE_MIN, min(N.NOTE_MAX, avg))
                pos = avg * 10.0
                r['apex10'] = {
                    'note': avg, 'display': N.fmt10(avg),
                    'hex': FC.hex_from_apex10(avg),
                    'flag': N.flag_from_apex10(avg), 'pos': pos,
                    'cap': 'moyenne', 'timing': rec_fut.get('timing'),
                    'fond': None, 'brut': rec_fut.get('brut'),
                    'n_moy': len(notes),
                    'detail': 'Moyenne des notes /10 des instruments visibles (ETC, métal au comptant, minières), hors titres sans note.',
                }
                # couleur de la moyenne, pas celle du futur
                import flags_couleur as FC
                r['apex10']['hex'] = FC.hex_from_apex10(r['apex10']['note'])
            else:
                r['apex10'] = rec_fut
            count(r['apex10'])
        save('metaux.json', MT)

    # --- crypto : le fondamental est remplacé par le score de liquidité 0-100 ---
    CF = load('crypto_fiches.json')
    if CF:
        for a in CF.get('assets') or []:
            liq = LQ.for_asset(a)
            a['liquidite'] = liq
            fond = liq.get('score')  # None si pas de carte (SOL, MSTR, saisie manquante)
            rec = attach(a, (a.get('av') or {}).get('score'), fond, a.get('elliott'), classe='crypto')
            count(rec)
        save('crypto_fiches.json', CF)
        tabs = load('tabs_data.json')
        if tabs is not None:
            tabs.setdefault('crypto', {})['fiches'] = CF
            save('tabs_data.json', tabs)

    # --- énergie ---
    EN = load('energie.json')
    if EN:
        for a in EN.get('assets') or []:
            if a.get('repere'):
                rec = N.compute(None)
                a['apex10'] = rec
                count(rec)
                continue
            fond = fond_lookup(idx, a.get('tv'), a.get('yahoo'), a.get('sym'), a.get('ticker'))
            rec = attach(a, (a.get('av') or {}).get('score'), fond, a.get('elliott'))
            count(rec)
        notes = [float(a['apex10']['note']) for a in (EN.get('assets') or [])
                 if not a.get('repere') and (a.get('apex10') or {}).get('note') is not None]
        if notes:
            import flags_couleur as FC
            avg = N.round_half(sum(notes) / len(notes))
            avg = max(N.NOTE_MIN, min(N.NOTE_MAX, avg))
            pos = avg * 10.0
            EN['apex10'] = {
                'note': avg, 'display': N.fmt10(avg),
                'hex': FC.hex_from_apex10(avg),
                'flag': N.flag_from_apex10(avg), 'pos': pos,
                'cap': 'moyenne', 'fond': None, 'brut': None,
                'n_moy': len(notes),
                'detail': "Moyenne des notes /10 des actifs Énergie affichés, hors repères de marché, arrondie au demi-point.",
            }
        EN['apex10_generated'] = NOW.strftime('%Y-%m-%d %H:%M')
        save('energie.json', EN)
        tabs = load('tabs_data.json')
        if tabs is not None:
            tabs['energie'] = EN
            save('tabs_data.json', tabs)

    # --- achatvente / indicateur (niveau onglet) ---
    AV = load('achatvente.json')
    IND = load('indicateur.json')
    if AV and isinstance(AV, dict):
        for tab, g in AV.items():
            if not isinstance(g, dict) or g.get('score') is None:
                continue
            ell = None
            if IND and isinstance(IND, dict):
                # pas d'Elliott au niveau onglet en général
                pass
            rec = N.compute(g.get('score'), None, None)
            g['apex10'] = rec
            count(rec)
        save('achatvente.json', AV)

    # --- fx / tabs : notes /10 sur les devises (hors DXY, repère) ---
    tabs = load('tabs_data.json')
    if tabs and isinstance(tabs, dict):
        fx = ((tabs.get('liquidites') or {}).get('fx') or {})
        assets = fx.get('assets') or []
        changed = False
        for a in assets:
            if not isinstance(a, dict):
                continue
            if a.get('repere') or 'DXY' in str(a.get('sym') or '') or 'DXY' in str(a.get('nom') or ''):
                rec = N.compute(None)
                a['apex10'] = rec
                count(rec)
                changed = True
                continue
            rec = attach(a, (a.get('av') or {}).get('score') if isinstance(a.get('av'), dict) else a.get('av'),
                         None, a.get('elliott'))
            count(rec)
            changed = True
        if changed:
            save('tabs_data.json', tabs)

    print('notes /10 ok', n_ok, 'sans note', n_na, 'generated', NOW.strftime('%Y-%m-%d %H:%M'))
    try:
        import snapshot_notes as SN
        SN.main()
    except Exception as e:
        print('snapshot_notes:', e, flush=True)


if __name__ == '__main__':
    main()
