#!/usr/bin/env python3
"""Note APEX et duration des 6 OAT Revolut → data/obligations_dispo.json.

ISIN vérifiés sur les fiches officielles de l'Agence France Trésor (26/11/2026).
Rendements : relevé Revolut d'Emmanuel, 26/11/2026 à 16 h 42 (Europe/Paris).
Aucune donnée de prix de marché n'est inventée : sans série hebdomadaire
fiable, la technique et la MM40 valent 0 (critère manquant).
"""
from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from apex.long250 import (  # noqa: E402
    ago, assemble, bloc, crit, fred_src, house, last, sent_pack, yoy,
)

SETTLE = date(2026, 11, 26)
SRC_DATE = '26/11/2026'
RDT_LIB = 'rendements Revolut au 26/11/2026 à 16 h 42'
RDT_SRC = "App Revolut, onglet Obligations, 26/11/2026 à 16 h 42 (Europe/Paris)"

# Encours et dates d'émission : fiches AFT consultées le 26/11/2026.
OATS = [
    {
        'isin': 'FR0011317783',
        'nom': 'OAT 2,75 % oct. 2027',
        'coupon': 2.75,
        'maturite': date(2027, 10, 25),
        'coupon_md': (10, 25),
        'rdt': 3.06,
        'terme': 'court terme',
        'verte': False,
        'encours_meur': 56295,
        'premiere_emission': '2012-09-06',
        'url': 'https://www.aft.gouv.fr/fr/titre/fr0011317783',
        'url_en': 'https://www.aft.gouv.fr/en/titre/fr0011317783',
    },
    {
        'isin': 'FR0011883966',
        'nom': 'OAT 2,50 % mai 2030',
        'coupon': 2.50,
        'maturite': date(2030, 5, 25),
        'coupon_md': (5, 25),
        'rdt': 3.77,
        'terme': 'court terme',
        'verte': False,
        'encours_meur': 73381,
        'premiere_emission': '2014-04-30',
        'url': 'https://www.aft.gouv.fr/fr/titre/fr0011883966',
        'url_en': 'https://www.aft.gouv.fr/en/titre/fr0011883966',
    },
    {
        'isin': 'FR0013234333',
        'nom': 'OAT verte 1,75 % juin 2039',
        'coupon': 1.75,
        'maturite': date(2039, 6, 25),
        'coupon_md': (6, 25),
        'rdt': 4.86,
        'terme': 'moyen terme',
        'verte': True,
        'encours_meur': 36304,
        'premiere_emission': '2017-01-31',
        'url': 'https://www.aft.gouv.fr/en/titre/fr0013234333',
        'url_en': 'https://www.aft.gouv.fr/en/titre/fr0013234333',
    },
    {
        'isin': 'FR0011461037',
        'nom': 'OAT 3,25 % mai 2045',
        'coupon': 3.25,
        'maturite': date(2045, 5, 25),
        'coupon_md': (5, 25),
        'rdt': 5.16,
        'terme': 'long terme',
        'verte': False,
        'encours_meur': 31657,
        'premiere_emission': '2013-03-26',
        'url': 'https://www.aft.gouv.fr/en/titre/fr0011461037',
        'url_en': 'https://www.aft.gouv.fr/en/titre/fr0011461037',
    },
    {
        'isin': 'FR001400XJJ3',
        'nom': 'OAT 3,75 % mai 2056',
        'coupon': 3.75,
        'maturite': date(2056, 5, 25),
        'coupon_md': (5, 25),
        'rdt': 5.30,
        'terme': 'long terme',
        'verte': False,
        'encours_meur': 20676,
        'premiere_emission': '2025-02-12',
        'url': 'https://www.aft.gouv.fr/en/titre/fr001400xjj3',
        'url_en': 'https://www.aft.gouv.fr/en/titre/fr001400xjj3',
    },
    {
        'isin': 'FR0010870956',
        'nom': 'OAT 4,00 % avr. 2060',
        'coupon': 4.00,
        'maturite': date(2060, 4, 25),
        'coupon_md': (4, 25),
        'rdt': 5.30,
        'terme': 'long terme',
        'verte': False,
        'encours_meur': 22843,
        'premiere_emission': '2010-03-17',
        'url': 'https://www.aft.gouv.fr/fr/titre/fr0010870956',
        'url_en': 'https://www.aft.gouv.fr/en/titre/fr0010870956',
    },
]

MOIS = {1: 'janv.', 2: 'févr.', 3: 'mars', 4: 'avr.', 5: 'mai', 6: 'juin',
        7: 'juil.', 8: 'août', 9: 'sept.', 10: 'oct.', 11: 'nov.', 12: 'déc.'}

FORMULE_DURATION = (
    'Coupons annuels, convention ACT/ACT (ICMA). '
    'f = (date de règlement → prochain coupon) / (coupon précédent → prochain coupon). '
    'Prix sale P = Σ CF_k / (1+y)^{t_k}, t_k = f + k − 1. '
    'Duration de Macaulay = (1/P) Σ t_k · PV(CF_k). '
    'Duration modifiée = Macaulay / (1+y). '
    'Sensibilité +1 pt = variation relative du prix sale recalculé à y + 1 %.'
)

# Notation souveraine France : calendrier AFT consulté le 26/11/2026.
NOTATION_FR = {
    'agences': {
        'S&P': 'A+',
        'Fitch': 'A+',
        "Moody's": 'Aa3',
        'DBRS': 'AA',
        'Scope': 'A+',
    },
    'seuil': 'A',
    'ok': True,
    'source': (
        'Agence France Trésor, calendrier des notations, consulté le 26/11/2026 '
        '(https://www.aft.gouv.fr/fr/calendrier-notations-france) : '
        'S&P A+ (perspective stable, prochaine décision 27/11/2026), '
        'Fitch A+ (négative, 30/10/2026), Moody’s Aa3 (négative, 23/10/2026). '
        'Toutes les notes des agences majeures sont ≥ A.'
    ),
}


def _coupon_on(year: int, md: tuple[int, int]) -> date:
    return date(year, md[0], md[1])


def prev_next_coupon(settle: date, maturity: date, md: tuple[int, int]) -> tuple[date, date]:
    """Coupon précédent (≤ règlement) et prochain (> règlement)."""
    cands = [_coupon_on(y, md) for y in range(settle.year - 1, maturity.year + 1)]
    cands = [c for c in cands if c <= maturity]
    prev = max(c for c in cands if c <= settle)
    nxt = min(c for c in cands if c > settle)
    return prev, nxt


def cashflows(coupon_pct: float, ytm: float, maturity: date, md: tuple[int, int],
              settle: date = SETTLE):
    """Flux restants, fraction f, prix sale, duration, sensibilité à y+1 pt."""
    prev, nxt = prev_next_coupon(settle, maturity, md)
    f = (nxt - settle).days / (nxt - prev).days
    cfs = []
    n = 0
    cdate = nxt
    while cdate <= maturity:
        n += 1
        t = f + (n - 1)
        cf = coupon_pct
        if cdate == maturity:
            cf += 100.0
        cfs.append((t, cf, cdate))
        cdate = _coupon_on(cdate.year + 1, md)
    y = ytm / 100.0
    dirty = sum(cf / (1 + y) ** t for t, cf, _ in cfs)
    mac = sum(t * cf / (1 + y) ** t for t, cf, _ in cfs) / dirty
    mod = mac / (1 + y)
    dirty2 = sum(cf / (1 + y + 0.01) ** t for t, cf, _ in cfs)
    sens = (dirty2 - dirty) / dirty * 100.0
    accrued = coupon_pct * (settle - prev).days / (nxt - prev).days
    resid = (maturity - settle).days / 365.25
    return {
        'f': round(f, 4),
        'n_coupons': n,
        'coupon_prec': prev.isoformat(),
        'coupon_suiv': nxt.isoformat(),
        'prix_sale': round(dirty, 3),
        'prix_clean': round(dirty - accrued, 3),
        'interet_couru': round(accrued, 3),
        'macaulay': round(mac, 2),
        'modifiee': round(mod, 2),
        'sensibilite_plus_1pt_pct': round(sens, 1),
        'residuelle_ans': round(resid, 2),
        'formule': FORMULE_DURATION,
        'date_reglement': settle.isoformat(),
        'convention': 'ACT/ACT ICMA, coupons annuels, nominal 100',
    }


def duration_par_exemple(y: float = 0.04, n: int = 30) -> float:
    """Duration de Macaulay d'une obligation au pair, coupon annuel = y, n années."""
    return (1 + y) / y * (1 - (1 + y) ** (-n))


def fond_oat(oat: dict, infl: float, d_inf: str, r10: float, d10: str,
             r10_6: float, d10_6: str, dfr: float, d_dfr: str) -> tuple[int, int, list]:
    ytm = oat['rdt']
    reel = None if infl is None or ytm is None else round(ytm - infl, 2)
    src_reel = (
        f"Rendement Revolut de l'OAT ({ytm:.2f} %) au 26/11/2026 à 16 h 42 "
        f"− inflation France sur 1 an (FRED {fred_src('CP0000FRM086NEST')}, {d_inf})"
    )
    pente = None if None in (r10, dfr) else round(r10 - dfr, 2)
    resid = (oat['maturite'] - SETTLE).days / 365.25
    courte = resid <= 5
    if r10 is None or r10_6 is None:
        ok_cyc = None
    elif courte:
        ok_cyc = r10 >= r10_6
    else:
        ok_cyc = r10 < r10_6
    lab_cyc = (
        'Duration courte et taux OAT 10 ans stables ou en hausse sur 6 mois'
        if courte else
        'Duration longue et taux OAT 10 ans en baisse sur 6 mois'
    )
    d0 = date.fromisoformat(oat['premiere_emission'])
    age = round((SETTLE - d0).days / 365.25, 1)
    E = [
        crit('reel_pos', 'Rendement réel > 0', '> 0 %', reel,
             None if reel is None else reel > 0, 10, src_reel, d_inf),
        crit('reel_15', 'Rendement réel > 1,5 %', '> 1,5 %', reel,
             None if reel is None else reel > 1.5, 10, src_reel, d_inf),
        crit('prime', 'Prime de terme : OAT 10 ans − taux de dépôt BCE > 0,5 pt',
             '> 0,5 pt', pente, None if pente is None else pente > 0.5, 10,
             fred_src('IRLTLT01FRM156N', 'ECBDFR'), d10),
        crit('duration_cycle', lab_cyc,
             f'OAT 10 ans {r10_6} % il y a 6 mois ({d10_6})' if r10_6 is not None else '—',
             r10, ok_cyc, 10,
             fred_src('IRLTLT01FRM156N') +
             f' ; duration {"courte" if courte else "longue"} '
             f'(échéance résiduelle {resid:.1f} ans au {SETTLE.isoformat()})', d10),
        crit('notation', 'Qualité de crédit : notation souveraine France ≥ A',
             '≥ A', 'S&P A+ / Fitch A+ / Moody’s Aa3', NOTATION_FR['ok'], 10,
             NOTATION_FR['source']),
        crit('ter15', 'Frais courants ≤ 0,15 %', '≤ 0,15 %', 0.0, True, 10,
             'Obligation en direct (pas de frais courants de fonds)'),
        crit('enc500', 'Encours ≥ 500 M€', '≥ 500 M€', oat['encours_meur'],
             oat['encours_meur'] >= 500, 10,
             f"Agence France Trésor, encours de la fiche {oat['url']}, consulté le {SRC_DATE}"),
        crit('age5', 'Ancienneté ≥ 5 ans', '≥ 5 ans', age,
             None if age is None else age >= 5, 10,
             f"Première émission {oat['premiere_emission']} (fiche AFT {oat['url']})"),
        crit('change', 'Risque de change maîtrisé (en EUR)', 'EUR', 'EUR', True, 10,
             'OAT libellée en euro, émetteur Agence France Trésor'),
    ]
    return bloc(E) + (E,)


def note_oat(oat: dict, infl, d_inf, r10, d10, r10_6, d10_6, dfr, d_dfr, g, fgp, flab, fmeta):
    fpts, fnc, fel = fond_oat(oat, infl, d_inf, r10, d10, r10_6, d10_6, dfr, d_dfr)
    # Technique et MM40 : pas de série hebdomadaire fiable (Yahoo 404 sur les ISIN).
    blocks = [
        ('RSI', 0),
        ('MACD', 0),
        ('Fibo', 0),
        ('CCI', 0),
        ('Fond. obligataire', fpts),
    ]
    mm40 = (0, {
        'max': 30, 'periode': '40 semaines', 'etat': 'n.c.', 'points': 0,
        'texte': 'MM40 hebdo : n.c. (pas de cours hebdomadaires fiables), 0 pt',
    })
    rec = assemble(
        blocks, fgp, flab or 'Sentiment',
        {
            'fondamental': {'points': fpts, 'max': 90, 'elements': fel, 'nc': fnc},
            'technique': {
                'etat': 'n.c.',
                'points': {'rsi': 0, 'macd': 0, 'fibonacci': 0, 'cci': 0},
                'detail': (
                    'Cours hebdomadaires des OAT individuelles introuvables '
                    'sur Yahoo Finance (requête 404 le 26/11/2026 pour les 6 ISIN, '
                    'suffixes .PA / .DE et ISIN nu). Critère manquant = 0 point.'
                ),
            },
            'fear_greed': fmeta,
            'sentiment': (g or {}).get('payload'),
        },
        mm40=mm40,
    )
    if g and g.get('payload'):
        rec['sentiment'] = g['payload']
    return rec, fpts, fel


def mois_lib(d: date) -> str:
    return f'{MOIS[d.month]} {d.year}'


def build() -> dict:
    infl, d_inf = yoy('CP0000FRM086NEST')
    d10, r10 = last('IRLTLT01FRM156N')
    d10_6, r10_6 = ago('IRLTLT01FRM156N', 6)
    d_dfr, dfr = last('ECBDFR')
    g = house(classe='oblig:eurgov')
    fgp, flab, fmeta = sent_pack(g)

    lignes = []
    for oat in OATS:
        dur = cashflows(oat['coupon'], oat['rdt'], oat['maturite'], oat['coupon_md'])
        rec, fpts, fel = note_oat(
            oat, infl, d_inf, r10, d10, r10_6, d10_6, dfr, d_dfr, g, fgp, flab, fmeta
        )
        lignes.append({
            'nom': oat['nom'],
            'isin': oat['isin'],
            'coupon': oat['coupon'],
            'maturite': oat['maturite'].isoformat(),
            'maturite_libelle': mois_lib(oat['maturite']),
            'rdt': oat['rdt'],
            'terme': oat['terme'],
            'ccy': 'EUR',
            'emetteur': 'Agence France Trésor',
            'dispo_revolut': True,
            'dispo': 'Revolut',
            'verte': oat['verte'],
            'encours_meur': oat['encours_meur'],
            'premiere_emission': oat['premiere_emission'],
            'url_aft': oat['url'],
            'duration': {
                'macaulay': dur['macaulay'],
                'modifiee': dur['modifiee'],
                'residuelle_ans': dur['residuelle_ans'],
                'sensibilite_plus_1pt_pct': dur['sensibilite_plus_1pt_pct'],
                'prix_sale': dur['prix_sale'],
                'prix_clean': dur['prix_clean'],
                'n_coupons': dur['n_coupons'],
                'date_reglement': dur['date_reglement'],
                'formule': dur['formule'],
                'convention': dur['convention'],
            },
            'apex10': rec,
        })

    # Risque court : on cite la plus longue (2056 et 2060, même rendement).
    long56 = next(x for x in lignes if x['isin'] == 'FR001400XJJ3')
    s56 = long56['duration']['sensibilite_plus_1pt_pct']
    risque = (
        f"Risque de taux élevé sur les longues (2056 : ≈ {s56:.0f} % si les taux "
        f"montent d'1 pt). Flat tax 30 %, hors PEA."
    ).replace('-', '−')

    out = {
        'max_par_pays': 6,
        'date_libelle': RDT_LIB,
        'source': RDT_SRC,
        'date_valorisation': SETTLE.isoformat(),
        'situation': {
            'titre': 'Situation des taux français',
            'texte': "Courbe montante : plus l'échéance est longue, plus le rendement est élevé.",
            'points': [
                {'annee': x['maturite'][:4], 'label': x['maturite'][:4], 'rdt': x['rdt'],
                 'nom': x['nom']}
                for x in lignes
            ],
        },
        'risque_court': risque,
        'methode_note': (
            'Grille obligations APEX déjà en place : technique 110 (RSI, MACD, Fibonacci, CCI) '
            '+ fondamental obligataire 90 (9 × 10) + sentiment maison à contre-courant ±50 '
            '+ MM40 hebdo 0 à +30 à contre-courant. Critère manquant = 0. '
            'Le rendement réel utilise le rendement de chaque OAT (Revolut) moins l’inflation '
            'France sur 1 an. La prime de terme et le cycle des taux utilisent l’OAT 10 ans '
            '(FRED IRLTLT01FRM156N) et le taux de dépôt BCE. '
            'Pas de sentiment maison « OAT France » (segment ETF retiré) : sentiment souverains '
            'euro (EUNH). Technique et MM40 à 0 faute de cours hebdomadaires fiables.'
        ),
        'non_verifie': [
            'Cours hebdomadaires des 6 OAT : introuvables sur Yahoo Finance le 26/11/2026 (HTTP 404). Technique et MM40 = 0 (n.c.).',
            'Pas de sentiment maison spécifique aux OAT françaises : repli sur le sentiment souverains euro (EUNH), à contre-courant.',
        ],
        'sources': {
            'rendements': RDT_SRC,
            'isin_encours': 'Fiches Agence France Trésor consultées le 26/11/2026',
            'inflation_taux': 'FRED : CP0000FRM086NEST, IRLTLT01FRM156N, ECBDFR',
            'notation': NOTATION_FR['source'],
        },
        'pays': {
            'fr': {
                'emetteur': 'Agence France Trésor',
                'dispo': 'Revolut',
                'ccy': 'EUR',
                'lignes': lignes,
            }
        },
    }
    return out


def main():
    out = build()
    dest = ROOT / 'data' / 'obligations_dispo.json'
    dest.write_text(json.dumps(out, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print('écrit', dest)
    for x in out['pays']['fr']['lignes']:
        d = x['duration']
        a = x['apex10']
        print(f"{x['isin']}  {x['nom']:32}  rdt {x['rdt']:.2f}  "
              f"note {a['total']:>4}  band {a['band']:7}  "
              f"mod {d['modifiee']:5.2f}  sens {d['sensibilite_plus_1pt_pct']:+.1f} %")


if __name__ == '__main__':
    main()
