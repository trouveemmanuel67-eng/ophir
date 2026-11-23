#!/usr/bin/env python3
"""Backtest exploratoire des notes TECHNIQUES APEX (sans sentiment, Elliott auto).

Univers : actions de la watchlist / listes APEX disposant d'un historique hebdo assez long.
À chaque vendredi clôturé de la fenêtre, on recalcule l'AV technique (composantes
disponibles hors sentiment, poids renormalisés) et la note /10 (timing seul +
plafonds / bonus Elliott automatique), puis on mesure le rendement à 4, 12 et 26
semaines. Aucune promesse de rendement.
"""
import json, os, sys, math, time, statistics as st
from collections import defaultdict
from datetime import date
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build_apex_bars as BAR
import ind_core as K
import elliott as E
import fibo as FB
import charte as CH
import elliott_zones as EZ
import note_apex as N

B = Path('/workspace/invest/patrimoine-dashboard/data')
OUT_MD = Path('/workspace/invest/backtest_apex_2026-11-23.md')
OUT_JSON = Path('/workspace/invest/backtest_apex_2026-11-23.json')

# Fenêtre : 5 ans de signaux, avec 26 semaines de suite disponibles.
# Dernière semaine clôturée : 2026-11-20 → dernier signal à 26 s. : 2026-05-22.
SIGNAL_START = date(2021, 11, 19)
SIGNAL_END_26 = date(2026, 5, 22)   # +26 s. <= 2026-11-20
HORIZONS = (4, 12, 26)
MIN_W_BEFORE = 52
NOTE_BUCKETS = [
    ('1 à 2,5', 1.0, 2.5),
    ('3 à 4,5', 3.0, 4.5),
    ('5 à 6,5', 5.0, 6.5),
    ('7 à 8', 7.0, 8.0),
    ('8,5 à 10', 8.5, 10.0),
]


def dparse(s):
    return date.fromisoformat(s[:10])


def av_tech(comps):
    """AV renormalisé sans la composante sentiment."""
    kept = []
    for x in comps:
        nom = (x.get('nom') or '')
        if 'Sentiment' in nom:
            continue
        if x.get('note') is None:
            continue
        kept.append(x)
    tw = sum(x['poids'] for x in kept)
    if tw <= 0:
        return None
    return round(sum(x['poids'] * x['note'] for x in kept) / tw, 1)


def max_dd_from_entry(closes):
    """closes[0] = entrée ; drawdown max (pic courant → creux) en fraction négative."""
    if len(closes) < 2:
        return 0.0
    peak = closes[0]
    mdd = 0.0
    for x in closes:
        if x > peak:
            peak = x
        dd = x / peak - 1.0
        if dd < mdd:
            mdd = dd
    return mdd


def fwd_ret(c, i, h):
    if i + h >= len(c) or c[i] in (None, 0) or c[i + h] is None:
        return None, None
    r = c[i + h] / c[i] - 1.0
    dd = max_dd_from_entry(c[i:i + h + 1])
    return r, dd


def bucket_of(note):
    if note is None:
        return None
    for name, a, b in NOTE_BUCKETS:
        if a - 1e-9 <= note <= b + 1e-9:
            return name
    return None


def zone_lab(key):
    z = EZ.zone_of(key) if key else None
    if z == 'verte':
        return 'zone verte'
    if z == 'rouge':
        return 'zone rouge'
    return 'zone neutre'


def walk(it, bens):
    """Retourne une liste d'observations {date, note, zone, rets, dds}."""
    cands = BAR.yahoo_cands(it.get('tv'), it.get('yahoo'), it.get('ticker'))
    path, ysym = BAR.find_wk(cands)
    if not path:
        return None, 'no_file'
    w, meta = K.yweekly(path)
    wc = [x for x in w if x[2]]
    if len(wc) < MIN_W_BEFORE + 26 + 52:
        return None, 'short'
    ds = [x[0] for x in wc]
    c = [x[1] for x in wc]
    n = len(c)
    # need last close after SIGNAL_END_26
    if dparse(ds[-1]) < date(2026, 11, 13):
        return None, 'stale'
    opens = {k: (v if v else None) for k, v in K.yopens(path).items()}
    op = [opens.get(d) for d in ds]
    hl = K.yhl(path)
    ben_sym = it.get('bench') or '^GSPC'
    if ben_sym not in bens:
        try:
            bens[ben_sym] = BAR.load_ben(ben_sym)
        except Exception:
            return None, 'no_bench'
    BEN, BN = bens[ben_sym]
    is_crypto = (it.get('tv') or '').startswith(('BITSTAMP:', 'CRYPTO:')) or (ysym or '').endswith('-USD')
    fpre = FB.prefix(ysym, ds[0], c[0]) if ysym else None

    ELL, FIB, CHC = {}, {}, {}

    def ell(i):
        if i not in ELL:
            ELL[i] = E.analyse(op[:i + 1], c[:i + 1])  # auto, pas d'override manuel
        return ELL[i]

    def fib(i):
        if i not in FIB:
            FIB[i] = FB.analyse(op[:i + 1], c[:i + 1], ds[:i + 1], fpre, adjust_splits=not is_crypto)
        return FIB[i]

    def cha(i):
        if i not in CHC:
            # manual=False : pas de lecture manuelle (n'existerait pas dans le passé)
            CHC[i] = CH.analyse(c[:i + 1], ds[:i + 1], op[:i + 1], hl, r[:i + 1],
                                syms=[x for x in (it.get('tv'), ysym, it.get('ticker')) if x],
                                manual=False)
        return CHC[i]

    r = K.rsi(c)
    m, sg, macdh = K.macd_series(c)
    cci = K.cci20(op, c)
    mm = K.sma(c, 40)
    ret = [None] + [c[i] / c[i - 1] - 1 for i in range(1, n)]
    gap = [(c[i] / mm[i] - 1) * 100 if mm[i] else None for i in range(n)]
    mo13 = [(c[i] / c[i - 13] - 1) * 100 if i >= 13 else None for i in range(n)]
    mo26 = [(c[i] / c[i - 26] - 1) * 100 if i >= 26 else None for i in range(n)]
    rs26 = []
    for i in range(n):
        ok26 = i >= 26 and ds[i] in BEN and ds[i - 26] in BEN
        rs26.append(((c[i] / c[i - 26]) / (BEN[ds[i]] / BEN[ds[i - 26]]) - 1) * 100 if ok26 else None)
    dd52 = [(c[i] / max(c[max(0, i - 51):i + 1]) - 1) * 100 for i in range(n)]

    def comps_at(i):
        comps = [E.comp(ell(i), K.W_EL), FB.comp(fib(i), K.W_FI),
                 {'nom': 'RSI 14 hebdo', 'poids': .15,
                  'note': K.clip((r[i] - 50) / 20 * 100) if r[i] is not None else None},
                 {'nom': 'MACD 12/26/9 hebdo', 'poids': .15,
                  'note': K.r_macd(m[i], sg[i], macdh[i], macdh[i - 1], macdh, i) if i and None not in (m[i], sg[i], macdh[i], macdh[i - 1]) else None},
                 {'nom': 'Écart à la moyenne mobile 40 semaines', 'poids': .15,
                  'note': K.clip(gap[i] / 10 * 100) if gap[i] is not None else None},
                 {'nom': 'Distance au plus haut 52 semaines', 'poids': .15,
                  'note': K.r_dd(dd52[i])},
                 {'nom': 'Momentum 13 et 26 semaines', 'poids': .15,
                  'note': (K.clip(mo13[i] / 15 * 100) + K.clip(mo26[i] / 25 * 100)) / 2 if mo13[i] is not None and mo26[i] is not None else None},
                 {'nom': f'Force relative vs {BN} sur 26 semaines', 'poids': .15,
                  'note': K.clip(rs26[i] / 10 * 100) if rs26[i] is not None else None},
                 ]
        for x in comps[2:]:
            x['poids'] = round(x['poids'] * K.SC, 4)
        comps[2:2] = [CH.comp(cha(i), K.W_CH), CH.comp_div(cha(i), K.W_DV)]
        K.add_cci(comps, cci[i])
        return comps

    obs = []
    for i in range(n):
        di = dparse(ds[i])
        if di < SIGNAL_START or di > SIGNAL_END_26:
            continue
        if i < MIN_W_BEFORE or i + max(HORIZONS) >= n:
            continue
        comps = comps_at(i)
        a = av_tech(comps)
        if a is None:
            continue
        key = (ell(i) or {}).get('key')
        rec = N.compute(a, None, key)  # technique seule, pas de fondamental
        note = rec.get('note')
        row = {'date': ds[i], 'note': note, 'av': a, 'zone': zone_lab(key), 'key': key, 'rets': {}, 'dds': {}}
        okh = True
        for h in HORIZONS:
            rt, dd = fwd_ret(c, i, h)
            if rt is None:
                okh = False
                break
            row['rets'][h] = rt
            row['dds'][h] = dd
        if okh:
            obs.append(row)
    return obs, None


def summarize(rows, keyfn, horizons=HORIZONS):
    groups = defaultdict(list)
    for r in rows:
        groups[keyfn(r)].append(r)
    out = {}
    for g, rs in sorted(groups.items(), key=lambda x: str(x[0])):
        cell = {'n': len(rs)}
        for h in horizons:
            rets = [x['rets'][h] for x in rs]
            dds = [x['dds'][h] for x in rs]
            cell[f'h{h}'] = {
                'n': len(rets),
                'ret_moy': statistics_mean(rets),
                'ret_med': statistics_median(rets),
                'taux_reussite': sum(1 for x in rets if x > 0) / len(rets) if rets else None,
                'dd_moy': statistics_mean(dds),
                'dd_med': statistics_median(dds),
                'dd_pire': min(dds) if dds else None,
            }
        out[g] = cell
    return out


def statistics_mean(xs):
    return sum(xs) / len(xs) if xs else None


def statistics_median(xs):
    if not xs:
        return None
    s = sorted(xs)
    m = len(s) // 2
    return s[m] if len(s) % 2 else 0.5 * (s[m - 1] + s[m])


def pct(x):
    if x is None:
        return 'n.d.'
    return f'{x*100:+.1f} %'.replace('.', ',')


def pct0(x):
    if x is None:
        return 'n.d.'
    return f'{x*100:.1f} %'.replace('.', ',')


def fmt_dd(x):
    if x is None:
        return 'n.d.'
    return f'{x*100:.1f} %'.replace('.', ',')


def main():
    t0 = time.time()
    items = BAR.collect()
    # ajouter crypto si présent
    CF = json.loads((B / 'crypto_fiches.json').read_text()) if (B / 'crypto_fiches.json').exists() else {}
    for a in CF.get('assets') or []:
        items.append({'tv': a.get('tv') or a.get('sym'), 'yahoo': a.get('yahoo') or a.get('sym'),
                      'ticker': a.get('sym'), 'name': a.get('nom'), 'bench': '^GSPC', 'src': 'crypto'})
    print('candidats', len(items), flush=True)
    bens = {}
    for s in ('^GSPC', '^FCHI', '^GDAXI', 'FTSEMIB.MI', '1306.T', '^KS11', '^AXJO', '^GSPTSE', '^SSMI'):
        try:
            bens[s] = BAR.load_ben(s)
            print('bench', s, len(bens[s][0]), flush=True)
        except Exception as e:
            print('bench fail', s, e, flush=True)

    all_obs = []
    meta = {'ok': 0, 'fail': defaultdict(int), 'symbols_ok': []}
    for i, it in enumerate(items, 1):
        try:
            obs, err = walk(it, bens)
        except Exception as e:
            obs, err = None, 'erreur:'+type(e).__name__
            if meta['fail'][err] < 3:
                print('ERR', it.get('tv') or it.get('name'), type(e).__name__, e, flush=True)
        if err or not obs:
            meta['fail'][err or 'empty'] += 1
        else:
            meta['ok'] += 1
            meta['symbols_ok'].append(it.get('tv') or it.get('name'))
            all_obs.extend(obs)
        if i % 25 == 0 or i == len(items):
            print(f'{i}/{len(items)} ok_sym={meta["ok"]} obs={len(all_obs)} {int(time.time()-t0)}s', flush=True)

    by_note = summarize(all_obs, lambda r: bucket_of(r['note']) or 'hors tranche')
    by_zone = summarize(all_obs, lambda r: r['zone'])
    # baseline = toutes les observations (achat-conservation univers, chaque semaine)
    baseline = summarize(all_obs, lambda r: 'univers (achat-conservation)')

    payload = {
        'date': '2026-11-23',
        'fenetre_signaux': [SIGNAL_START.isoformat(), SIGNAL_END_26.isoformat()],
        'horizons_semaines': list(HORIZONS),
        'n_symboles': meta['ok'],
        'n_symboles_exclus': dict(meta['fail']),
        'n_observations': len(all_obs),
        'par_tranche_de_note': by_note,
        'par_zone_elliott': by_zone,
        'achat_conservation': baseline,
        'secondes': round(time.time() - t0, 1),
        'methode': (
            "Note technique /10 = timing seul (AV sans sentiment, poids renormalisés) "
            "+ règles Elliott automatiques (plafond zone rouge, bonus zone verte). "
            "Pas de fondamental, pas de lectures manuelles, pas de frais."
        ),
    }
    OUT_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + '\n')
    write_md(payload, meta)
    print('wrote', OUT_MD, OUT_JSON, 'obs', len(all_obs), 'sec', payload['secondes'])


def write_md(p, meta):
    lines = []
    A = lines.append
    A('# Backtest exploratoire des notes techniques APEX')
    A('')
    A(f'*Calcul du {p["date"]} (Europe/Paris). Aucune promesse de rendement.*')
    A('')
    A('## Ce qui a été mesuré')
    A('')
    A('Recalcul, en bougies hebdomadaires clôturées, d’une **note technique APEX /10** sur les actions (et quelques crypto) de l’univers APEX actuel :')
    A('')
    A('- timing = score Achat/Vente **sans la composante sentiment**, poids des autres composantes renormalisés (Elliott auto 15 %, Fibonacci 15 %, charte 20 %, divergence RSI/MACD si elle existe, RSI, MACD, MM40, distance au plus haut 52 semaines, momentum, force relative, CCI facultatif) ;')
    A('- pas de qualité fondamentale (la note publiée aujourd’hui mêle 60 % timing et 40 % fondamental : ce n’est donc **pas** la note du site) ;')
    A('- Elliott **automatique seulement** (pas d’overrides manuels, pas de confirmation visuelle) ;')
    A('- à chaque vendredi de la fenêtre, on note l’actif avec les seules données alors disponibles, puis on observe le rendement total des **4, 12 et 26 semaines suivantes**.')
    A('')
    A(f'Fenêtre des signaux : **{p["fenetre_signaux"][0]}** au **{p["fenetre_signaux"][1]}** (environ cinq ans, en s’arrêtant 26 semaines avant la dernière clôture du 20/11/2026).')
    A(f'Symboles retenus : **{p["n_symboles"]}**. Observations (symbole × semaine) : **{p["n_observations"]}**.')
    if p['n_symboles_exclus']:
        A('Exclus (historique trop court, fichier ou indice manquant) : ' +
          ', '.join(f'{k} {v}' for k, v in p['n_symboles_exclus'].items()) + '.')
    A('')
    A('Le scénario **achat-conservation** est le rendement de *toutes* les observations de l’univers, sans filtrer par note ni par zone : c’est l’entrée répétée, chaque semaine, dans chaque nom encore vivant de la liste actuelle.')
    A('')
    A('## Résultats')
    A('')

    def table(title, bloc):
        A(f'### {title}')
        A('')
        A('| Groupe | n | Horizon | Rendement moyen | Rendement médian | Taux de réussite | Drawdown moyen | Drawdown médian | Pire drawdown |')
        A('|---|---:|---:|---:|---:|---:|---:|---:|---:|')
        for g, cell in bloc.items():
            first = True
            for h in HORIZONS:
                x = cell[f'h{h}']
                name = g if first else ''
                n = cell['n'] if first else ''
                A(f"| {name} | {n} | {h} s. | {pct(x['ret_moy'])} | {pct(x['ret_med'])} | {pct0(x['taux_reussite'])} | {fmt_dd(x['dd_moy'])} | {fmt_dd(x['dd_med'])} | {fmt_dd(x['dd_pire'])} |")
                first = False
        A('')

    table('Achat-conservation (univers)', p['achat_conservation'])
    table('Par tranche de note technique /10', p['par_tranche_de_note'])
    table('Par zone Elliott automatique', p['par_zone_elliott'])

    A('## Limites (à lire avec les chiffres)')
    A('')
    A('- **Biais de survie.** L’univers est la liste APEX d’aujourd’hui. Les sociétés retirées, en faillite ou sorties de l’indice n’y sont pas. Les rendements sont donc trop optimistes par rapport à un vrai portefeuille de l’époque.')
    A('- **Note différente de celle du site.** Ici : timing seul, sans sentiment et sans fondamental. Un 7/10 technique d’hier n’est pas le 7/10 publié aujourd’hui.')
    A('- **Elliott approximatif.** Le décompte automatique, recalculé à chaque semaine, n’est pas le dessin validé par Emmanuel. Les zones vertes / rouges sont donc bruyantes.')
    A('- **Frais non inclus.** Ni courtage, ni spread, ni fiscalité, ni glissement. Les écarts de quelques points de pourcentage peuvent disparaître après coûts, surtout à 4 semaines.')
    A('- **Observations dépendantes.** Un même titre produit une observation presque chaque semaine : les 4, 12 et 26 semaines se chevauchent. Les effectifs « n » ne sont pas des paris indépendants ; les moyennes sont plus précises que les tests statistiques naïfs.')
    A('- **Pas de gestion de portefeuille.** Une ligne = un actif, une semaine, un horizon. Pas de pondération, pas de limite de nombres de positions, pas de filet de stop.')
    A('- **Historiques et places de cotation.** Les cours viennent de Yahoo Finance (ajustés des divisions). Un écart avec le graphique TradingView reste possible.')
    A('')
    A('Ces chiffres décrivent le passé de cet univers, dans ce cadre. Ils ne disent pas ce que la note fera demain, et ils ne justifient pas un ordre.')
    A('')
    A(f'*Fichier machine : `backtest_apex_2026-11-23.json`. Durée de calcul : {p["secondes"]} s.*')
    A('')
    OUT_MD.write_text('\n'.join(lines), encoding='utf-8')


if __name__ == '__main__':
    main()
