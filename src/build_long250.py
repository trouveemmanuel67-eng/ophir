#!/usr/bin/env python3
"""APE-25 (t503u) : applique la note APEX unique −50..250 aux classes hors actions.

Métaux (cyan retiré, ETC = Hype 45 + Qualité 45), obligations, énergie, devises, ETF par devise
(fondamental 30), épargne / monétaire (Livret A, LEP, placements Revolut), immobilier.
Écrit dans data/*.json et un journal data/fond250/journal_notes.json (avant / après, n.c.).
"""
import json, os, re, sys
from pathlib import Path
ROOT = Path(os.environ.get('APEX_ROOT') or Path(__file__).resolve().parent.parent)
sys.path[:0] = [str(ROOT), str(ROOT / 'src')]
D = ROOT / 'data'
import apex.long250 as L  # noqa: E402
from apex.metaux_points import score_instrument  # noqa: E402
from apex.score import metaux_band, fmt10, round_half  # noqa: E402

J = {'avant_apres': {}, 'nc': {}}


def load(n):
    return json.loads((D / n).read_text(encoding='utf-8'))


def save(n, d):
    (D / n).write_text(json.dumps(d, ensure_ascii=False) + '\n', encoding='utf-8')


def note(a):
    return (a or {}).get('note')


def log(cat, key, avant, apres, nc=None):
    J['avant_apres'].setdefault(cat, {})[key] = [avant, apres]
    if nc:
        J['nc'].setdefault(cat, {})[key] = nc


def avg_rec(notes, detail, n_label):
    avg = int(round_half(sum(notes) / len(notes)))
    b = metaux_band(avg)
    return {'note': avg, 'display': fmt10(avg), 'hex': b['hex'], 'flag': b['flag'], 'band': b['id'], 'pos': avg,
            'cap': 'moyenne', 'n_moy': len(notes), 'detail': detail, 'scale': 250, 'total': avg, 'total_min': -50,
            'total_max': 250, 'v2': True, 'ligne': f'moyenne de {len(notes)} {n_label}  →  {avg} / 250'}


# ------------------------------------------------------------------ métaux
METAL = {'OANDA:XAUUSD': 'Or', 'OANDA:XAGUSD': 'Argent', 'OANDA:XPTUSD': 'Platine', 'OANDA:XPDUSD': 'Palladium'}


SERIE_OVERRIDE = {'EURONEXT:PHPT': {
    'yahoo': 'PHPT.MI', 'url': 'https://finance.yahoo.com/quote/PHPT.MI/',
    'note_serie': 'Note calculée sur la cotation Borsa Italiana PHPT.MI (même ISIN JE00B1VS2W53, en euros) : corrélation hebdomadaire 0,97 avec IPLT sur 3 ans. La série Euronext Amsterdam PHPT.AS (sauts de +127 %) n’est pas utilisée.'}}
LIST_NOTE_FIX = {"La série Yahoo de PHPT n'est pas assez fiable pour une note.": "PHPT est noté sur sa cotation de Milan (PHPT.MI, même ISIN), la série d’Amsterdam étant inexploitable."}


def metaux():
    M = load('metaux.json')
    for r in M.get('rows') or []:
        ml = r.get('mlist') or {}
        for k in ('list_note', 'note'):
            if isinstance(ml.get(k), str):
                for a, b in LIST_NOTE_FIX.items():
                    ml[k] = ml[k].replace(a, b)
        if isinstance(r.get('list_note'), str):
            for a, b in LIST_NOTE_FIX.items():
                r['list_note'] = r['list_note'].replace(a, b)
    fgv = L.fg()
    for r in M.get('rows') or []:
        metal = METAL.get(r.get('tv'))
        notes = []
        ml = r.get('mlist') or {}
        for it in [ml.get('head')] + list(ml.get('items') or []):
            if it and it.get('tv') in SERIE_OVERRIDE:
                # t506u : PHPT noté sur la cotation de Milan (même ISIN), la série Amsterdam est inexploitable.
                it.update(SERIE_OVERRIDE[it['tv']])
                it.pop('skip_score', None)
            if not it or it.get('skip_score'):
                continue
            av = (it.get('av') or {}).get('score') if isinstance(it.get('av'), dict) else None
            before = note(it.get('apex10'))
            rec = score_instrument(it, metal=metal, av=av, fg=fgv)
            if rec.get('note') is None and before is not None and not rec.get('erreur'):
                continue
            it['apex10'] = rec
            nc = ((rec.get('decomp') or {}).get('qualite_etc') or {}).get('nc')
            log('metaux', it.get('tv'), before, rec.get('note'), nc or (rec.get('erreur') and [rec['erreur']]))
            if rec.get('note') is not None:
                notes.append(float(rec['note']))
        notes = un_seul_etc(r, metal, notes)
        if notes:
            r['apex10'] = avg_rec(notes, 'Moyenne des notes −50 à 250 des instruments visibles (ETC retenu, métal au comptant, minières), hors titres sans note.', 'instruments')
    save('metaux.json', M)


# t507u : un seul ETC physique par métal (meilleure Qualité ETC, puis cotation en euro, frais, encours).
def _held_tvs():
    out = set()
    for fn in ('positions.json', 'positions_revolut.json', 'positions_revolutx.json'):
        try:
            d = load(fn)
        except Exception:
            continue
        for p in d.get('positions') or []:
            if p.get('statut') in ('active', 'en_attente'):
                for k in (p.get('fiche_tv'), p.get('tv_note'), p.get('tv')):
                    if k:
                        out.add(k)
    return out


def _qual(it):
    q = ((it.get('apex10') or {}).get('decomp') or {}).get('qualite_etc') or {}
    return q.get('points')


def _enc(it):
    for e in ((((it.get('apex10') or {}).get('decomp') or {}).get('qualite_etc') or {}).get('elements') or []):
        if e.get('id', '').startswith('enc') and e.get('valeur') is not None:
            return float(e['valeur'])
    return 0.0


def un_seul_etc(r, metal, notes):
    ml = r.get('mlist') or {}
    allit = [x for x in [ml.get('head')] + list(ml.get('items') or []) if x]
    etcs = [x for x in allit if x.get('kind') == 'etc' and (x.get('apex10') or {}).get('note') is not None]
    if len(etcs) <= 1:
        return notes
    eur = lambda x: 1 if (x.get('currency') or '').upper() == 'EUR' else 0
    ter = lambda x: x.get('ter') if x.get('ter') is not None else 9.9
    best = sorted(etcs, key=lambda x: (-(_qual(x) or 0), -eur(x), ter(x), -_enc(x), -(x['apex10']['note'])))[0]
    held = _held_tvs()
    retires, masques = [], []
    for x in etcs:
        if x is best:
            continue
        info = {'tv': x.get('tv'), 'isin': x.get('isin'), 'note': x['apex10'].get('note'), 'qualite_etc': _qual(x),
                'ter': x.get('ter'), 'devise': x.get('currency')}
        if x.get('tv') in held:
            x['masque_onglet'] = True
            masques.append(x)
            info['detenu'] = True
        retires.append(info)
    others = [x for x in allit if x.get('kind') != 'etc']
    ml['head'] = best
    ml['items'] = others
    ml['n'] = 1 + len(others)
    ml['etc_retires'] = retires
    if masques:
        ml['etc_detenus_masques'] = masques
    q = _qual(best)
    noms = ', '.join(i['tv'].split(':')[-1] for i in retires if i.get('tv'))
    ml['list_note'] = (f"Un seul ETC physique par métal (règle du 24/11/2026) : {best.get('tv')} (ISIN {best.get('isin')}), "
                       f"meilleure Qualité ETC ({q} / 45), puis cotation en euro et frais les plus bas"
                       f"{' ' + str(best.get('ter')).replace('.', ',') + ' %' if best.get('ter') is not None else ''}. "
                       f"Retirés de l'onglet, des Meilleures entrées et des Meilleurs SHORT : {noms}."
                       + (" Un ETC retiré mais détenu reste noté dans Mes positions." if masques else ''))
    r['etc_retenu'] = {'tv': best.get('tv'), 'isin': best.get('isin'), 'note': best['apex10'].get('note'), 'qualite_etc': q,
                       'ter': best.get('ter'), 'devise': best.get('currency')}
    add = f" ETC retenu pour ce métal : {best.get('tv')} (un seul ETC affiché depuis le 24/11/2026)."
    if r.get('note_revolut') and add not in r['note_revolut']:
        r['note_revolut'] = r['note_revolut'] + add
    log('metaux_un_etc', metal or r.get('nom'), None, best['apex10'].get('note'), [f"retenu {best.get('tv')}", f"retirés {noms}"])
    return [float(x['apex10']['note']) for x in [best] + others if (x.get('apex10') or {}).get('note') is not None]


# ------------------------------------------------------------------ obligations
def obligations():
    O = load('obligations.json')
    g = L.fg()
    fgp = g['points'] if g.get('ok') else None
    for s in O['segments']:
        head_isin = next((k for k, v in L.HEADS.items() if v == s.get('tv')), None)
        def one(tv, yahoo, isin, nom, rating_a=None, hedged=None):
            t, used = L.tech_of(tv, yahoo, None)
            fpts, fnc, fel = L.oblig_fond(s['key'], tv, isin, nom, rating_a, hedged)
            blocks = [('RSI', t and t['rsi']), ('MACD', t and t['macd']), ('Fibo', t and t['fibonacci']), ('CCI', t and t['cci']), ('Fond. oblig.', fpts)]
            rec = L.assemble(blocks, fgp, 'F&G', {
                'fondamental': {'points': fpts, 'max': 90, 'elements': fel, 'nc': fnc},
                'technique': {'symbole': used, 'date_cloture': t and t['date_cloture'], 'detail': t and t['detail']} if t else {'erreur': 'série hebdomadaire introuvable'},
                'fear_greed': {'valeur': g.get('value'), 'source': 'CNN Fear & Greed, à contre-courant'}})
            rec['fond'] = fpts
            if not t:
                rec['cap'] = 'sans_technique'
                fnc = (fnc or []) + ['technique (série hebdomadaire introuvable)']
            return rec, fnc
        hrec, hnc = one(s.get('tv'), s.get('sym'), head_isin, s.get('pname'))
        log('obligations', s.get('tv'), note(s.get('apex10_panier')), hrec['note'], hnc)
        s['apex10_panier'] = hrec
        notes = []
        for e in s.get('list') or []:
            rec, nc = one(e.get('tv'), e.get('yahoo'), e.get('isin'), e.get('name'), e.get('rating_a'), e.get('hedged'))
            log('obligations', e.get('tv'), note(e.get('apex10')), rec['note'], nc)
            e['apex10'] = rec
            notes.append(rec['note'])
        if notes:
            s['apex10'] = avg_rec(notes, 'Moyenne des notes −50 à 250 des ETF UCITS affichés du segment.', 'ETF')
        else:
            s['apex10'] = dict(hrec, detail="Note de l'ETF de référence (aucune alternative UCITS dans la liste).")
    O['apex250'] = {'grille': 'Technique 110 + Fondamental obligataire 90 (9 × 10) + F&G ±50', 'genere': L.TODAY.isoformat()}
    save('obligations.json', O)


# ------------------------------------------------------------------ énergie
ENERGIE_ISIN = {v: k for k, v in L.ENERGIE_ETF.items()}


def energie(T):
    g = L.fg()
    fgp = g['points'] if g.get('ok') else None
    for a in T['energie']['assets']:
        k = a.get('kind')
        if k in ('futures', 'etc'):
            energie_contrat(a, g, fgp)
            continue
        if k not in ('equity', 'equity_proxy', 'etf_equity'):
            continue
        t, used = L.tech_of(a.get('tv'), a.get('yahoo'), None)
        if k == 'etf_equity':
            fpts, fnc, fel = L.energie_etf_fond(ENERGIE_ISIN.get(a.get('tv')), a.get('groupe'), a.get('tv'))
            lab = 'Fond. ETF'
        else:
            fpts, fnc, fel = L.energie_fond(a.get('yahoo'), a.get('groupe'), a.get('tv'))
            lab = 'Fond. énergie'
        blocks = [('RSI', t and t['rsi']), ('MACD', t and t['macd']), ('Fibo', t and t['fibonacci']), ('CCI', t and t['cci']), (lab, fpts)]
        rec = L.assemble(blocks, fgp, 'F&G', {
            'fondamental': {'points': fpts, 'max': 90, 'elements': fel, 'nc': fnc},
            'technique': {'symbole': used, 'date_cloture': t and t['date_cloture'], 'detail': t and t['detail']} if t else {'erreur': 'série hebdomadaire introuvable'},
            'fear_greed': {'valeur': g.get('value'), 'source': 'CNN Fear & Greed, à contre-courant'}})
        rec['fond'] = fpts
        log('energie', a.get('tv'), note(a.get('apex10')), rec['note'], fnc)
        a['apex10'] = rec
    T['energie']['apex250'] = {'grille': 'Technique 110 + Fondamental énergie 90 (actions : 9 ratios × 10 ; ETF et ETC : 9 critères justETF × 10 ; contrats à terme : critère de cycle seul, les 8 critères d’entreprise ou de fonds ne s’appliquent pas, sans redistribution) + F&G ±50'}
    notes = [float(a['apex10']['note']) for a in T['energie']['assets']
             if (a.get('apex10') or {}).get('note') is not None and (a.get('apex10') or {}).get('scale') == 250]
    if notes:
        T['energie']['apex10'] = avg_rec(notes, 'Moyenne des notes −50 à 250 de tous les actifs Énergie affichés (actions, ETF, ETC, contrats à terme), arrondie au point.', 'actifs')


def energie_contrat(a, g, fgp):
    """t506u : contrats à terme (WTI, Brent, fioul, essence) et ETC gaz notés sur la grille énergie."""
    t, used = L.tech_of(a.get('tv'), a.get('yahoo'), None)
    if a.get('kind') == 'etc':
        fpts, fnc, fel = L.energie_etf_fond(ENERGIE_ISIN.get(a.get('tv')) or a.get('isin') or ISIN_SOUS(a), a.get('groupe'), a.get('tv'))
        lab = 'Fond. ETC'
    else:
        cyc = L.cycle_wti()
        fel = [cyc]
        fpts = int(cyc.get('points') or 0)
        fnc = ['cycle'] if cyc.get('nc') else []
        lab = 'Cycle'
    blocks = [('RSI', t and t['rsi']), ('MACD', t and t['macd']), ('Fibo', t and t['fibonacci']), ('CCI', t and t['cci']), (lab, fpts)]
    regle = ('ETC : 9 critères justETF × 10 (TER, encours, ancienneté, réplication physique, ≥ 30 lignes, cycle WTI)'
             if a.get('kind') == 'etc' else
             'Contrat à terme : seul le cycle (WTI sous sa moyenne 5 ans, FRED DCOILWTICO) s’applique, +10 ; les 8 critères d’entreprise ou de fonds ne s’appliquent pas à un contrat (0, sans redistribution)')
    rec = L.assemble(blocks, fgp, 'F&G', {
        'fondamental': {'points': fpts, 'max': 90, 'elements': fel, 'nc': fnc, 'regle': regle},
        'technique': {'symbole': used, 'date_cloture': t and t['date_cloture'], 'detail': t and t['detail']} if t else {'erreur': 'série hebdomadaire introuvable'},
        'fear_greed': {'valeur': g.get('value'), 'source': 'CNN Fear & Greed, à contre-courant'}})
    rec['fond'] = fpts
    if not t:
        rec.update({'note': None, 'display': '–', 'total': None, 'erreur': 'série hebdomadaire introuvable'})
    log('energie', a.get('tv'), note(a.get('apex10')), rec['note'], fnc)
    a['apex10'] = rec
    # Le contrat reste un repère (non achetable au comptant, hors Meilleures entrées), mais il a sa note sur 250.
    if a.get('repere_texte'):
        a['repere_texte'] = (a['repere_texte']
            .replace("Il est affiché comme repère de marché, sans note APEX ni drapeau, parce qu'il est", 'Il est noté sur la grille énergie (ETC : 9 critères justETF, −50 à 250), mais reste signalé comme repère de marché, parce qu’il est'))


def ISIN_SOUS(a):
    m = re.search(r'ISIN ([A-Z]{2}[A-Z0-9]{10})', a.get('sous') or '')
    return m.group(1) if m else None


# ------------------------------------------------------------------ devises + ETF par devise
def devises(T):
    from apex.fx_etf_points import hype_points_30
    import apply_attention as AA
    AA.load_attention(refresh=True)
    g = L.fg()
    for a in T['liquidites']['fx']['assets']:
        ccy = a.get('code') or a.get('quote_for')
        if ccy not in L.CCY_WB:
            continue
        before = note(a.get('apex10'))
        rec = L.score_devise(ccy)
        log('devises', ccy, before, rec['note'], rec['decomp']['fondamental']['nc'])
        a['apex10'] = rec
        e = a.get('etf_local')
        if not e or not e.get('apex10'):
            continue
        x = e['apex10']; P = x['decomp']['points']
        dev = max(0, min(30, ((rec['note'] + 50) // 30) * 3))
        isin = e.get('isin') if str(e.get('isin') or '')[:2] in ('IE', 'LU', 'DE', 'FR', 'JE') else None
        E = L.etf_quality(isin, ['ter50', 'enc500', 'age5'], yahoo=e.get('yahoo'))
        fpts, fnc = L.bloc(E)
        att = AA.attention_of(e.get('tv'), e.get('yahoo'), e.get('ticker'), e.get('nom'))
        hp = hype_points_30(att)
        fgp = g['points'] if g.get('ok') else None
        blocks = [('RSI', P.get('rsi')), ('MACD', P.get('macd')), ('Fibo', P.get('fibonacci')), ('CCI', P.get('cci')),
                  ('Devise', dev), ('Fond.', fpts), ('Hype', hp)]
        new = L.assemble(blocks, fgp, 'F&G', {
            'fondamental': {'points': fpts, 'max': 30, 'elements': E, 'nc': fnc},
            'devise': {'points': dev, 'note_devise_250': rec['note'], 'regle': 'floor((note devise + 50) / 30) × 3, max 30'},
            'hype': {'points': hp, 'attention': att, 'grille': '0–9→+30, 10→+27, 50→+15, 100→0'}})
        new['decomp']['points'].update({'rsi': P.get('rsi'), 'macd': P.get('macd'), 'fibonacci': P.get('fibonacci'), 'cci': P.get('cci'),
                                        'devise': dev, 'fondamental': fpts, 'hype': hp, 'fear_greed': fgp, 'total': new['note']})
        for k in ('fg_value',):
            if k in x:
                new[k] = x[k]
        log('etf_devise', e.get('tv'), note(x), new['note'], fnc)
        e['apex10'] = new


# ------------------------------------------------------------------ épargne
def epargne(T, PL):
    liv = T['liquidites']['livrets']['monthly'][-1]
    src_liv = 'Banque de France, taux des livrets réglementés (tabs_data.liquidites.livrets, mois %s)' % liv[0]
    sp = 'https://www.service-public.fr/particuliers/vosdroits/F2365'
    prods = [
        {'id': 'livret_a', 'nom': 'Livret A', 'taux': liv[1], 'ccy': 'EUR', 'impose': False, 'garantie': 'État', 'src_garantie': 'Service-Public (Livret A : capital garanti par l’État) ' + sp,
         'liquide': True, 'liquide_txt': 'retrait à tout moment', 'src_liquide': sp, 'frais': True, 'frais_txt': 'aucun frais', 'src_frais': sp, 'src_taux': src_liv},
        {'id': 'lep', 'nom': 'LEP', 'taux': liv[2], 'ccy': 'EUR', 'impose': False, 'garantie': 'État', 'src_garantie': 'Service-Public (LEP) https://www.service-public.fr/particuliers/vosdroits/F2367',
         'liquide': True, 'liquide_txt': 'retrait à tout moment', 'src_liquide': 'https://www.service-public.fr/particuliers/vosdroits/F2367', 'frais': True, 'frais_txt': 'aucun frais',
         'src_frais': 'https://www.service-public.fr/particuliers/vosdroits/F2367', 'src_taux': src_liv},
    ]
    help_url = 'https://help.revolut.com/fr-FR/help/accounts/difference-between-instant-access-savings-and-flexible-account/'
    fcf_url = 'https://www.revolut.com/fr-FR/flexible-cash-funds/'
    for ln in PL.get('lignes') or []:
        if ln['id'] == 'revolut-epargne-eur':
            prods.append({'id': ln['id'], 'nom': 'Revolut, compte d’épargne EUR', 'taux': ln['taux'], 'ccy': 'EUR', 'impose': True,
                          'garantie': 'FGD lituanien (dépôts Revolut Bank UAB, 100 000 €)', 'src_garantie': help_url,
                          'liquide': True, 'liquide_txt': 'accès instantané, aucun frais de retrait', 'src_liquide': help_url,
                          'frais': True, 'frais_txt': 'aucun frais de retrait ni montant minimum', 'src_frais': help_url, 'src_taux': PL.get('source')})
        elif ln['id'] == 'revolut-mmf-usd':
            prods.append({'id': ln['id'], 'nom': 'Revolut, fonds monétaires flexibles USD', 'taux': ln['taux'], 'ccy': 'USD', 'impose': True,
                          'garantie': 'non', 'src_garantie': fcf_url + ' (capital non garanti ; protection des investisseurs 22 000 € seulement en cas de faillite)',
                          'liquide': False, 'liquide_txt': 'vente à tout moment, fonds sous 2 jours ouvrés', 'src_liquide': fcf_url,
                          'frais': False, 'frais_txt': 'frais de service annuels selon l’abonnement', 'src_frais': fcf_url, 'src_taux': PL.get('source')})
    ipc = (T['liquidites'].get('ipc') or {})
    for p in prods:
        p['ipc'] = ipc.get('series'); p['ipc_id'] = ipc.get('idbank')
    out = []
    for p in prods:
        rec = L.epargne_score(p)
        rec['decomp'].update({'produit': {k: p[k] for k in ('nom', 'taux', 'ccy', 'impose')}, 'source_taux': p.get('src_taux')})
        nc = rec['decomp']['contexte']['nc'] + rec['decomp']['fondamental']['nc']
        log('epargne', p['id'], None, rec['note'], nc)
        out.append({'id': p['id'], 'nom': p['nom'], 'taux': p['taux'], 'devise': p['ccy'], 'apex10': rec})
        for ln in PL.get('lignes') or []:
            if ln['id'] == p['id']:
                ln['apex10'] = rec
    T['liquidites']['apex_epargne'] = {'grille': 'Contexte de taux 110 + Fondamental épargne 90 + CNN Fear & Greed inversé ±50', 'produits': out}


def immobilier():
    A = load('achatvente.json')
    im = A.get('immobilier') or {}
    rec = L.immobilier_score(im.get('components') or [])
    log('immobilier', 'marche_residentiel_france', None, rec['note'], rec['decomp']['contexte']['nc'] + rec['decomp']['fondamental']['nc'])
    im['apex10'] = rec
    A['immobilier'] = im
    save('achatvente.json', A)


def sync_bars_energie():
    """Recopie les notes 250 dans energie.json (même liste que tabs_data) et dans apex_bars.json (puces Mes positions,
    listes) : aucune entrée créée, seules celles qui existent sont mises à jour."""
    T = load('tabs_data.json'); O = load('obligations.json'); M = load('metaux.json')
    new = {}
    for a in T['energie']['assets']:
        if (a.get('apex10') or {}).get('scale') == 250:
            new[a['tv']] = a['apex10']
    for s in O['segments']:
        if (s.get('apex10_panier') or {}).get('scale') == 250:
            new[s['tv']] = s['apex10_panier']
        for e in s.get('list') or []:
            if (e.get('apex10') or {}).get('scale') == 250:
                new[e['tv']] = e['apex10']
    for r in M.get('rows') or []:
        for it in ((r.get('mlist') or {}).get('items') or []):
            if (it.get('apex10') or {}).get('note') is not None and it.get('tv'):
                new.setdefault(it['tv'], it['apex10'])
    for a in T['liquidites']['fx']['assets']:
        e = a.get('etf_local') or {}
        if (e.get('apex10') or {}).get('scale') == 250 and e.get('tv'):
            new[e['tv']] = e['apex10']
    E = load('energie.json')
    for a in E.get('assets') or []:
        if a.get('tv') in new:
            a['apex10'] = new[a['tv']]
    save('energie.json', E)
    B = load('apex_bars.json')
    n = 0
    for tv, rec in new.items():
        b = (B.get('bars') or {}).get(tv)
        if b is not None:
            b['apex10'] = rec; n += 1
    save('apex_bars.json', B)
    print('apex_bars : notes 250 synchronisées', n, '/', len(new))


def main():
    metaux()
    obligations()
    T = load('tabs_data.json')
    PL = load('placements.json')
    energie(T)
    devises(T)
    epargne(T, PL)
    save('tabs_data.json', T)
    save('placements.json', PL)
    immobilier()
    sync_bars_energie()
    (D / 'fond250').mkdir(exist_ok=True)
    (D / 'fond250' / 'journal_notes.json').write_text(json.dumps(J, ensure_ascii=False, indent=1), encoding='utf-8')
    for cat, d in J['avant_apres'].items():
        print(cat, len(d), {k: v for k, v in list(d.items())[:6]})


if __name__ == '__main__':
    main()
