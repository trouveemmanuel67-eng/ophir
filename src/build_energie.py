"""Onglet ÉNERGIE · fiches APEX Achat / Vente (pétrole, gaz, produits raffinés : contrats à terme en repères, ETC à exposition directe).

Même méthode et pondérations que l'onglet Actions (src/ind_core.py, 17/11/2026) : Charte graphique 20 %,
Elliott 15 %, Fibonacci 15 % (corps, base → ATH), Divergence RSI / MACD weekly 10 % (seulement si une divergence
récente apparaît), puis RSI, MACD, MM40, distance au plus haut 52 semaines, momentum et force relative
vs S&P 500 à 6 % chacun, sentiment technique contrarien 4 %. Indicateurs hebdomadaires sur bougies
clôturées. Fibonacci lu sur les corps ; structure d'Elliott de la Charte graphique lue sur les mèches.
CCI 20 : affiché, hors pondération.

Sources : Yahoo Finance, bougies 1w, historique maximal. Force relative contre le S&P 500.
Aucun chiffre n'est inventé : un symbole sans série valide est affiché comme indisponible.

-> data/energie.json  (inclus ensuite dans tabs_data.json)
"""
import os as _os
_APEX_ROOT = _os.path.abspath(_os.environ.get('APEX_ROOT') or _os.path.join(_os.path.dirname(__file__), '..'))
import elliott_zones as EZ
import json, os, sys, math, datetime as D, statistics as st, urllib.parse
from zoneinfo import ZoneInfo
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import elliott as E, ind_core as K, fibo as FB
import courtier_cash as CC

B = _APEX_ROOT + '/data/'
NOW = D.datetime.now(ZoneInfo('Europe/Paris'))
f1 = K.f1
fs = K.fs

def mtime(rel):
    p = B + rel
    if not os.path.exists(p):
        return None
    return D.datetime.fromtimestamp(os.path.getmtime(p), ZoneInfo('Europe/Paris')).strftime('%Y-%m-%d %H:%M')

def ypath(sym):
    return B + 'energie/yahoo_1wk_' + urllib.parse.quote(sym, safe='') + '.json'

def cci20(op, c):
    hi, lo = E.bodies(op, c)
    tp = [(h + l + cl) / 3 for h, l, cl in zip(hi, lo, c)]
    n, out = 20, [None] * len(tp)
    for i in range(n - 1, len(tp)):
        w = tp[i - n + 1:i + 1]
        sma = sum(w) / n
        md = sum(abs(x - sma) for x in w) / n
        out[i] = 0.0 if md == 0 else (tp[i] - sma) / (0.015 * md)
    return out

def cci_zone(v):
    if v is None:
        return 'indisponible'
    if v >= 100:
        return 'surachat (≥ +100)'
    if v <= -100:
        return 'survente (≤ −100)'
    return 'zone neutre'

def elliott_comment(e):
    return EZ.commentaire(e)


def extra_indicators(w, opens):
    wc = [x for x in w if x[2]]
    ds = [x[0] for x in wc]
    c = [x[1] for x in wc]
    op = [opens.get(d) for d in ds]
    r = K.rsi(c)
    e12, e26 = K.ema(c, 12), K.ema(c, 26)
    m = [a - b for a, b in zip(e12, e26)]
    sg = K.ema(m, 9)
    h = [a - b for a, b in zip(m, sg)]
    cc = cci20(op, c)
    last = len(c) - 1
    rz = 'surachat (≥ 70)' if r[last] is not None and r[last] >= 70 else (
        'survente (≤ 30)' if r[last] is not None and r[last] <= 30 else ('zone neutre' if r[last] is not None else 'indisponible')
    )
    if last >= 1:
        cross = 'MACD au-dessus du signal' if m[last] >= sg[last] else 'MACD sous le signal'
        mom = 'histogramme en hausse' if h[last] > h[last - 1] else 'histogramme en baisse'
        macd_txt = f"{cross}, {mom}"
        hist_prev = h[last - 1]
    else:
        macd_txt, hist_prev = 'indisponible', None
    cha = None
    cci_v = cc[last]
    return {
        'rsi': None if r[last] is None else round(r[last], 1),
        'rsi_zone': rz,
        'macd': round(m[last], 2),
        'signal': round(sg[last], 2),
        'hist': round(h[last], 2),
        'hist_prev': None if hist_prev is None else round(hist_prev, 2),
        'macd_texte': macd_txt,
        'cci': None if cci_v is None else round(cci_v, 1),
        'cci_zone': cci_zone(cci_v),
        'cci_n': 20,
    }

RISK_COMMON = (
    "Indicateur composite APEX, purement informatif. Ce n'est ni un conseil ni un signal d'ordre. "
    "Aucun rendement n'est promis. Les lectures d'Elliott, de Fibonacci et de la charte sont automatiques "
    "et peuvent différer de TradingView. On n'entre jamais sur un plus haut historique."
)
RISK_FUT = (
    "Contrat à terme continu Yahoo (front month, échéances non ajustées) : le cours peut sauter au moment du roll. "
    "Ce n'est pas un prix spot. Forte volatilité, saisonnalité, et sensibilité à l'OPEP+, aux stocks, à la météo "
    "et à la géopolitique."
)
RISK_OPEC = (
    "Le pétrole et ses produits raffinés restent exposés aux décisions de l'OPEP+, aux sanctions, aux conflits "
    "et aux variations de stocks. Aucun scénario de prix n'est certain."
)
RISK_GAS = (
    "Le gaz naturel est particulièrement volatil (météo, stockage, saisonnalité hivernale)."
)

RISK_ETC = (
    "ETC adossé à des contrats à terme, pas au prix spot : le roll des échéances "
    "(souvent en situation de contango) peut éroder la performance en détention longue. "
    "Frais courus. Une cotation en euros avec un sous-jacent en dollars entraîne un effet de change. "
    "Aucun rendement n'est promis. Instrument volatil."
)
RISK_TTF = (
    "EGAS suit des contrats à terme TTF (gaz européen), pas le Henry Hub américain. "
    "Le prix européen peut diverger fortement du prix américain (météo, stocks, interconnexions, géopolitique)."
)
RISK_BNQ9 = (
    "BNQ9 (BNPP Natural Gas ETC, ISIN DE000PB6GAS5) est un ETP adossé à des contrats à terme Henry Hub, "
    "pas au prix spot du gaz. En détention longue, le roll des échéances (souvent en situation de contango) "
    "a un coût qui peut éroder la performance par rapport au spot. L'instrument est très volatil "
    "(météo, stocks, saisonnalité hivernale). Frais courus d'environ 0,90 % par an. Cotation en euros, "
    "sous-jacent en dollars : effet de change. Aucun rendement n'est promis."
)
RISK_U_ETF = (
    "URNU et U3O8 sont des ETF UCITS d'actions minières et de la chaîne de l'uranium, pas de l'uranium physique : "
    "bêta actions, dilution, risque pays (Kazakhstan, Canada, Australie, Niger notamment) et sensibilité à la "
    "politique nucléaire. Ce n'est pas le prix spot de l'U3O8."
)
RISK_U_TRUST = (
    "Sprott Physical Uranium Trust détient de l'uranium physique : prime ou décote par rapport à la valeur des "
    "stocks, frais de conservation, pas de coupon, liquidité et cadre réglementaire. Ce n'est ni un ETF classique "
    "ni une action minière."
)
RISK_COAL = (
    "BTU (Peabody Energy) est un proxy action du charbon (l'ETF VanEck KOL, liquidé, a été retiré), "
    "pas un indice du prix du charbon : risque d'entreprise, transition énergétique, réglementation "
    "environnementale et demande électrique, notamment asiatique."
)
RISK_CCJ = (
    "Cameco (CCJ) est une action minière d'uranium, pas l'uranium physique : risque d'entreprise, de production et "
    "de pays (Canada, Kazakhstan), sensibilité à la politique nucléaire et au prix contractuel de l'U3O8."
)
RISK_XLE = (
    "XDW0 est un ETF UCITS d'actions du secteur énergie mondial (indice MSCI World Energy : majors, exploration, services, "
    "environ deux tiers aux États-Unis), coté en euros, pas un contrat sur "
    "le pétrole. Sensible aux résultats des sociétés, au dollar, aux dividendes et au poids de quelques valeurs "
    "dans le panier."
)


RISK_EQ = (
    "Action cotée, pas le prix spot de la matière première ou de l'électricité : risque d'entreprise, "
    "de bilan, de dividende et de secteur."
)
RISK_PIPE = (
    "Société de transport ou de midstream (oléoducs, gazoducs, GNL) : exposée aux volumes, aux tarifs "
    "régulés et aux projets d'infrastructure, pas au seul prix spot du gaz ou du pétrole."
)
RISK_UTIL = (
    "Producteur ou distributeur d'électricité / utility : exposé à la régulation des tarifs, au mix de "
    "production, à la météo et aux taux d'intérêt, pas à un contrat à terme sur l'électricité."
)
RISK_SOLAR = (
    "Action de la chaîne solaire (équipement, modules) : forte cyclicité, concurrence, politique de "
    "soutien et taux d'intérêt. Ce n'est pas un indice du prix de l'électricité solaire."
)
RISK_WIND = (
    "Siemens Energy : équipementier énergétique (éolien, turbines à gaz, réseau), pas un producteur "
    "d'électricité ni un indice du vent. Risque d'exécution des commandes et de cycle industriel."
)
RISK_H2 = (
    "Ballard Power (BLDP) est une action de piles à combustible, pas un prix de l'hydrogène : "
    "risque d'entreprise, de technologie et de demande encore limitée."
)
RISK_ZPDU = (
    "ZPDU est un ETF UCITS d'actions des utilities américains (équivalent de XLU, non vendu chez Revolut), "
    "coté en euros, pas un contrat sur l'électricité. Sensible aux taux, à la régulation et au dollar."
)

# 17/11/2026 · règle Revolut : URA -> URNU, URNM -> U3O8, U-U -> CCJ, XLE -> XDW0, KOL (radié) retiré ; contrats à terme = repères de marché sans note.
# 17/11/2026 · gaz : NG=F / NYMEX:NG1! remplacé par BNQ9 (ETP Revolut, toujours en repère car adossé à des futures).
ASSETS = [
    # ----- Pétrole et gaz (repères à terme, puis ETC à exposition directe) -----
    {
        'repere': True,
        'key': 'wti', 'sym': 'CL=F', 'nom': 'Pétrole WTI',
        'sous': 'NYMEX:CL1! · contrat à terme continu',
        'groupe': 'Pétrole et gaz', 'kind': 'futures',
        'yahoo': 'CL=F', 'tv': 'NYMEX:CL1!',
        'src_name': 'Yahoo Finance · CL=F',
        'url': 'https://finance.yahoo.com/quote/CL=F/history/',
        'unit': '$/baril', 'fsym': 'CL=F', 'syms': ['NYMEX:CL1!', 'CL=F', 'CL'],
        'risks': [RISK_COMMON, RISK_FUT, RISK_OPEC],
        'reuse': 'energie',
    },
    {
        'repere': True,
        'key': 'brent', 'sym': 'BZ=F', 'nom': 'Pétrole Brent',
        'sous': 'TVC:UKOIL · contrat à terme continu (Yahoo BZ=F)',
        'groupe': 'Pétrole et gaz', 'kind': 'futures',
        'yahoo': 'BZ=F', 'tv': 'TVC:UKOIL',
        'tv_alt': ['ICE:BRN1!', 'NYMEX:BB1!'],
        'src_name': 'Yahoo Finance · BZ=F',
        'url': 'https://finance.yahoo.com/quote/BZ=F/history/',
        'unit': '$/baril', 'fsym': 'BZ=F', 'syms': ['TVC:UKOIL', 'ICE:BRN1!', 'BZ=F'],
        'risks': [RISK_COMMON, RISK_FUT, RISK_OPEC],
        'reuse': 'energie',
    },
    {
        'repere': True,
        'key': 'ho', 'sym': 'HO=F', 'nom': 'Fioul (heating oil)',
        'sous': 'NYMEX:HO1! · contrat à terme continu',
        'groupe': 'Pétrole et gaz', 'kind': 'futures',
        'yahoo': 'HO=F', 'tv': 'NYMEX:HO1!',
        'src_name': 'Yahoo Finance · HO=F',
        'url': 'https://finance.yahoo.com/quote/HO=F/history/',
        'unit': '$/gallon', 'fsym': 'HO=F', 'syms': ['NYMEX:HO1!', 'HO=F'],
        'risks': [RISK_COMMON, RISK_FUT, RISK_OPEC],
        'reuse': 'energie',
    },
    {
        'repere': True,
        'key': 'rb', 'sym': 'RB=F', 'nom': 'Essence RBOB',
        'sous': 'NYMEX:RB1! · contrat à terme continu',
        'groupe': 'Pétrole et gaz', 'kind': 'futures',
        'yahoo': 'RB=F', 'tv': 'NYMEX:RB1!',
        'src_name': 'Yahoo Finance · RB=F',
        'url': 'https://finance.yahoo.com/quote/RB=F/history/',
        'unit': '$/gallon', 'fsym': 'RB=F', 'syms': ['NYMEX:RB1!', 'RB=F'],
        'risks': [RISK_COMMON, RISK_FUT, RISK_OPEC],
        'reuse': 'energie',
    },
    {
        'key': 'crud', 'sym': 'CRUD', 'nom': 'Pétrole WTI (ETC WisdomTree)',
        'sous': 'LSE:CRUD · WisdomTree WTI Crude Oil ETC (ISIN GB00B15KXV33). Même produit coté Xetra OD7F en euros, aussi chez XTB. Série Yahoo : CRUD.L (USD).',
        'groupe': 'Pétrole et gaz', 'kind': 'etc',
        'yahoo': 'CRUD.L', 'tv': 'LSE:CRUD',
        'tv_alt': ['XETR:OD7F'],
        'isin': 'GB00B15KXV33',
        'src_name': 'Yahoo Finance · CRUD.L',
        'url': 'https://finance.yahoo.com/quote/CRUD.L/history/',
        'unit': '$', 'fsym': 'CRUD.L', 'syms': ['LSE:CRUD', 'CRUD.L', 'XETR:OD7F'],
        'risks': [RISK_COMMON, RISK_ETC, RISK_OPEC],
    },
    {
        'key': 'ooea', 'sym': 'OOEA', 'nom': 'Pétrole Brent (ETC WisdomTree)',
        'sous': 'XETR:OOEA · WisdomTree Brent Crude Oil ETC (ISIN JE00B78CGV99), ligne Xetra en euros chez XTB. Série Yahoo : LSE:BRNT (même ISIN, USD) car la cotation Xetra n’est pas historisée sur Yahoo.',
        'groupe': 'Pétrole et gaz', 'kind': 'etc',
        'yahoo': 'BRNT.L', 'tv': 'XETR:OOEA',
        'tv_alt': ['LSE:BRNT'],
        'isin': 'JE00B78CGV99',
        'src_name': 'Yahoo Finance · BRNT.L',
        'url': 'https://finance.yahoo.com/quote/BRNT.L/history/',
        'unit': '$', 'fsym': 'BRNT.L', 'syms': ['XETR:OOEA', 'OOEA.DE', 'LSE:BRNT', 'BRNT.L'],
        'risks': [RISK_COMMON, RISK_ETC, RISK_OPEC],
    },
    # ----- Gaz naturel -----
    {
        'repere': True,
        'key': 'nghh', 'sym': 'NG=F', 'nom': 'Gaz naturel Henry Hub',
        'sous': 'NYMEX:NG1! · contrat à terme continu',
        'groupe': 'Gaz naturel', 'kind': 'futures',
        'yahoo': 'NG=F', 'tv': 'NYMEX:NG1!',
        'src_name': 'Yahoo Finance · NG=F',
        'url': 'https://finance.yahoo.com/quote/NG=F/history/',
        'unit': '$/MMBtu', 'fsym': 'NG=F', 'syms': ['NYMEX:NG1!', 'NG=F', 'NG'],
        'risks': [RISK_COMMON, RISK_FUT, RISK_GAS],
    },
    {
        'key': 'egas', 'sym': 'EGAS', 'nom': 'Gaz naturel TTF (ETC WisdomTree)',
        'sous': 'XETR:EGAS · WisdomTree European Natural Gas ETC (ISIN XS2872233403), contrats TTF, ligne Xetra en euros chez XTB. Série Yahoo : LSE:EGAS (même ISIN, GBp) car la cotation Xetra n’est pas historisée sur Yahoo.',
        'groupe': 'Gaz naturel', 'kind': 'etc',
        'yahoo': 'EGAS.L', 'tv': 'XETR:EGAS',
        'tv_alt': ['LSE:EGAS'],
        'isin': 'XS2872233403',
        'src_name': 'Yahoo Finance · EGAS.L',
        'url': 'https://finance.yahoo.com/quote/EGAS.L/history/',
        'unit': 'GBp', 'fsym': 'EGAS.L', 'syms': ['XETR:EGAS', 'EGAS.DE', 'LSE:EGAS', 'EGAS.L'],
        'risks': [RISK_COMMON, RISK_ETC, RISK_GAS, RISK_TTF],
    },
    {
        'key': 'ngas', 'sym': 'NGAS', 'nom': 'Gaz naturel Henry Hub (ETC WisdomTree)',
        'sous': 'LSE:NGAS · WisdomTree Natural Gas ETC (ISIN JE00BN7KB334), contrats Henry Hub',
        'groupe': 'Gaz naturel', 'kind': 'etc',
        'yahoo': 'NGAS.L', 'tv': 'LSE:NGAS',
        'isin': 'JE00BN7KB334',
        'src_name': 'Yahoo Finance · NGAS.L',
        'url': 'https://finance.yahoo.com/quote/NGAS.L/history/',
        'unit': '$', 'fsym': 'NGAS.L', 'syms': ['LSE:NGAS', 'NGAS.L', 'NGAS'],
        'risks': [RISK_COMMON, RISK_ETC, RISK_GAS],
    },
]


def _actifs_univers():
    """Carte tv → univers (oui / hors / positions_seulement)."""
    path = os.path.join(_APEX_ROOT, 'config', 'actifs.json')
    try:
        data = json.load(open(path, encoding='utf-8'))
    except Exception:
        return {}
    out = {}
    for a in data.get('actifs') or []:
        tv = a.get('tv')
        if tv:
            out[str(tv)] = a.get('univers') or 'oui'
    return out

_UNIV = _actifs_univers()

def _dans_univers(cfg):
    """t322u : actions/obligations hors USA/FR/DE/CA/CH retirées des listes (sauf positions détenues)."""
    if cfg.get('repere'):
        return True
    tv = cfg.get('tv')
    u = _UNIV.get(tv)
    if u == 'hors' or u == 'positions_seulement':
        return False
    return True

ASSETS = [c for c in ASSETS if _dans_univers(c)]


def unavailable(cfg, raison):
    return {
        'ok': False,
        'key': cfg['key'], 'sym': cfg['sym'], 'nom': cfg['nom'], 'sous': cfg['sous'],
        'groupe': cfg['groupe'], 'kind': cfg['kind'],
        'tv': cfg.get('tv'), 'tv_alt': cfg.get('tv_alt') or [], 'repere_texte': cfg.get('repere_texte'),
        'yahoo': cfg['yahoo'],
        'raison': raison,
        'url': cfg['url'], 'src_name': cfg['src_name'],
        'retrieved': mtime('energie/yahoo_1wk_' + urllib.parse.quote(cfg['yahoo'], safe='') + '.json'),
        'risks': cfg['risks'],
    }


# ----- réutilisation des notes APEX déjà publiées (pas de recalcul) -----
_old_path = B + 'energie.json'
OLD_EN = json.load(open(_old_path)) if os.path.exists(_old_path) else {'assets': []}
OLD_BY_SYM = {a.get('sym'): a for a in (OLD_EN.get('assets') or []) if a.get('sym')}
_sec_path = B + 'secteurs.json'
SEC_BY_TV = {}
if os.path.exists(_sec_path):
    for s in (json.load(open(_sec_path)).get('sectors') or []):
        if s.get('tv'):
            SEC_BY_TV[s['tv']] = s

def ypath_any(cfg):
    p = ypath(cfg['yahoo'])
    if os.path.exists(p):
        return p
    alt = B + 'secteurs/yahoo_1wk_' + urllib.parse.quote(cfg['yahoo'], safe='') + '.json'
    if os.path.exists(alt):
        return alt
    return p

def fill_display(cfg, item):
    """Complète ind / elliott_comment pour l'affichage, sans toucher à av ni sent."""
    if item.get('ind') and item.get('elliott_comment'):
        return item
    path = ypath_any(cfg)
    if not os.path.exists(path):
        return item
    try:
        w, meta = K.yweekly(path)
        opens = {k: (v if v else None) for k, v in K.yopens(path).items()}
    except Exception:
        return item
    if not item.get('ind'):
        try:
            item['ind'] = extra_indicators(w, opens)
            ch = item.get('charte') or {}
            dv = ch.get('div') or {}
            if not item['ind'].get('div'):
                item['ind']['div'] = {
                    'type': ('baissière' if (dv.get('note') or 0) < 0 else 'haussière') if dv.get('note') is not None else ('indisponible' if not dv else 'aucune'),
                    'texte': dv.get('texte') or "Aucune divergence RSI weekly récente : critère non compté, poids redistribué.",
                    'note': dv.get('note'),
                }
        except Exception:
            pass
    if not item.get('elliott_comment'):
        item['elliott_comment'] = elliott_comment(item.get('elliott'))
    return item

def reuse_fiche(cfg):
    src = None
    if cfg.get('reuse') == 'energie':
        src = OLD_BY_SYM.get(cfg['sym'])
    elif cfg.get('reuse') == 'secteurs':
        src = SEC_BY_TV.get(cfg['tv'])
    if not src:
        return None
    item = json.loads(json.dumps(src))  # deep copy
    for k in ('key', 'sym', 'nom', 'sous', 'groupe', 'kind', 'tv', 'tv_alt', 'yahoo',
              'url', 'src_name', 'unit', 'risks', 'repere_texte', 'fsym', 'syms'):
        if k in cfg and cfg[k] is not None:
            item[k] = cfg[k]
    item['ok'] = True if src.get('ok', True) else False
    item['reused'] = True
    if 'currency' not in item:
        item['currency'] = 'EUR' if str(cfg.get('unit')) == '€' else 'USD'
    if cfg.get('repere'):
        item['repere'] = True
        item['av'] = None
        item['sent'] = None
    item = fill_display(cfg, item)
    return item

# ----- données de marché -----

_spx_cands = [
    B + 'energie/yahoo_1wk_%5EGSPC.json',
    B + 'actions/yahoo_1wk_%5EGSPC.json',
    B + 'fibo_max/%5EGSPC.json',
]
_spx_path = next((p for p in _spx_cands if os.path.exists(p)), _spx_cands[0])
spx_w, _ = K.yweekly(_spx_path)
spx = {d: v for d, v, c in spx_w if c}

fiches = []
for cfg in ASSETS:
    if not cfg.get('repere') and not CC.cash_ok(cfg.get('tv')):
        fiches.append(unavailable(cfg, "Non retenu : achat au comptant chez Revolut Invest France ou XTB non vérifié dans disponibilites.json. Aucune note n'est inventée."))
        continue
    if cfg.get('reuse'):
        reused = reuse_fiche(cfg)
        if reused:
            fiches.append(reused)
            continue
    if cfg.get('force_unavailable'):
        fiches.append(unavailable(cfg, cfg['force_unavailable']))
        continue
    path = ypath_any(cfg)
    if not os.path.exists(path):
        fiches.append(unavailable(cfg, "Fichier Yahoo introuvable. Aucun cours n'est inventé."))
        continue
    try:
        w, meta = K.yweekly(path)
        opens = {k: (v if v else None) for k, v in K.yopens(path).items()}
        hl = K.yhl(path)
    except Exception as e:
        fiches.append(unavailable(cfg, f"Série Yahoo illisible ({e}). Aucun cours n'est inventé."))
        continue
    wc = [x for x in w if x[2]]
    live_rows = [x for x in w if not x[2]]
    live = {'date': live_rows[-1][0], 'close': round(live_rows[-1][1], 4 if live_rows[-1][1] < 10 else 2)} if live_rows else None
    if len(wc) < 52:
        fiches.append(unavailable(cfg, f"Historique hebdomadaire insuffisant ({len(wc)} semaines clôturées, minimum 52). Aucun cours n'est inventé."))
        continue
    fpre = FB.prefix(cfg.get('fsym'), wc[0][0], wc[0][1]) if cfg.get('fsym') else None
    r = K.compute(w, spx, 'S&P 500', opens=opens, fsym=cfg.get('fsym'), fpre=fpre, hl=hl, syms=cfg.get('syms'))
    for block in (r['sent']['components'], r['av']['components']):
        for x in block:
            if x.get('name') == 'Sentiment du secteur (lecture contrarienne)' or x.get('nom') == 'Sentiment du secteur (lecture contrarienne)':
                if 'name' in x:
                    x['name'] = 'Sentiment technique (lecture contrarienne)'
                if 'nom' in x:
                    x['nom'] = 'Sentiment technique (lecture contrarienne)'
    ind = extra_indicators(w, opens)
    # divergence affichée : celle de la charte (critère APEX), pas un second détecteur
    ch = r.get('charte') or {}
    dv = ch.get('div') or {}
    ind['div'] = {
        'type': ('baissière' if (dv.get('note') or 0) < 0 else 'haussière') if dv.get('note') is not None else ('indisponible' if not dv else 'aucune'),
        'texte': dv.get('texte') or "Aucune divergence RSI weekly récente : critère non compté, poids redistribué.",
        'note': dv.get('note'),
    }
    ell_c = elliott_comment(r.get('elliott'))
    risks = list(r.get('warn') or []) + list(cfg['risks'])
    dec = 3 if r['close'] < 10 else (2 if r['close'] < 1000 else 0)
    item = {
        'ok': True,
        'key': cfg['key'], 'sym': cfg['sym'], 'nom': cfg['nom'], 'sous': cfg['sous'],
        'groupe': cfg['groupe'], 'kind': cfg['kind'],
        'tv': cfg.get('tv'), 'tv_alt': cfg.get('tv_alt') or [], 'repere_texte': cfg.get('repere_texte'),
        'yahoo': cfg['yahoo'],
        'currency': (meta or {}).get('currency') or 'USD',
        'unit': cfg['unit'],
        'date': r['date'], 'close': round(r['close'], dec), 'first': r['first'], 'n': r['n'],
        'live': live, 'ath': r['ath'], 'dd52': r['dd52'], 'warn': r.get('warn') or [],
        'sent': r['sent'], 'av': r['av'],
        'elliott': r['elliott'], 'fibo': r['fibo'], 'charte': r.get('charte'),
        'ind': ind, 'elliott_comment': ell_c,
        'risks': risks,
        'url': cfg['url'], 'src_name': cfg['src_name'],
        'retrieved': mtime('energie/yahoo_1wk_' + urllib.parse.quote(cfg['yahoo'], safe='') + '.json'),
        'market_time': (
            D.datetime.fromtimestamp(meta['regularMarketTime'], ZoneInfo('Europe/Paris')).strftime('%Y-%m-%d %H:%M')
            if (meta or {}).get('regularMarketTime') else None
        ),
    }
    if cfg.get('repere'):   # repère de marché : ni note APEX, ni sentiment, ni signal achat / vente
        item.update(repere=True, av=None, sent=None, risks=[x for x in item['risks'] if x != RISK_COMMON])
    fiches.append(item)

out = {
    'generated': NOW.strftime('%Y-%m-%d %H:%M'),
    'benchmark': 'S&P 500',
    'assets': fiches,
    'groupes': [
        'Pétrole et gaz', 'Gaz naturel',
    ],
    'method_sent': (
        "Indice composite APEX, non officiel, identique à celui des secteurs Actions. Six sous-scores de 0 à 100, "
        "poids égaux (1/6 chacun), calculés chaque semaine sur les clôtures hebdomadaires confirmées, sans données "
        "futures : (1) RSI 14 de Wilder, valeur brute ; (2) écart du cours à sa moyenne mobile 40 semaines ; "
        "(3) performance sur 26 semaines ; (4) force relative contre le S&P 500 sur 13 semaines ; "
        "(5) distance au plus haut des 52 dernières semaines ; (6) volatilité réalisée sur 13 semaines, inversée "
        "(forte volatilité = peur). Les sous-scores 2 à 6 sont des rangs percentiles sur les 5 dernières années "
        "(260 semaines). Zones : 0-24 peur extrême · 25-44 peur · 45-55 neutre · 56-75 avidité · 76-100 euphorie."
    ),
    'method_av': (
        "Indice composite APEX, non officiel, mêmes pondérations que l'onglet Actions. Onze composantes notées de "
        "−100 à +100 puis pondérées : Charte graphique (20 % : structure d'Elliott lue sur les mèches, vague 5 "
        "terminée ou nouveau sommet au-dessus de la 3 fortement négatif, fin de 4 ou de C positive, et figures "
        "chartistes weekly validées en clôture : épaule-tête-épaule, double sommet ou double creux, biseaux ; "
        "0 si rien n'est détecté ; une lecture manuelle d'Emmanuel remplace la détection automatique), "
        "vagues d'Elliott selon la règle (15 % : pas d'entrée pendant une vague 5 ni tant que l'ABC qui suit n'est "
        "pas terminée ; entrées en fin de vague 4 ou en fin de vague C), retracement de Fibonacci du plus bas "
        "historique (base) au plus haut historique (ATH) sur les corps des bougies (15 % : plus le cours est bas "
        "dans le retracement, plus la note pousse à l'achat ; négative près de l'ATH ; plafonnée sous la base), "
        "Divergence RSI / MACD weekly (10 % : −100 si baissière, +100 si haussière ; sans divergence récente, critère "
        "non compté et poids redistribué), RSI 14 hebdo (6 %), MACD 12/26/9 hebdo (6 %), écart à la moyenne "
        "mobile 40 semaines (6 %), distance au plus haut 52 semaines selon la règle « pas d'entrée au plus haut » "
        "(6 %), momentum 13 et 26 semaines (6 %), force relative contre le S&P 500 sur 26 semaines (6 %), "
        "sentiment technique lu de façon contrarienne (4 %). "
        "Les lectures sont automatiques : c'est une approximation qui peut différer de TradingView. "
        "Le CCI 20 (corps, mêmes seuils que CCI_S de la vue APEX, ligne violette = +100) entre dans la note lorsqu'il est en surachat ou en survente (6 % facultatif, pris sur le panier de 40 %). L'histogramme MACD est plafonné dès 4 barres hebdomadaires de même signe. "
        "Score = Σ (poids × note) ÷ Σ (poids disponibles). Zones : ≤ −60 vente forte · −60 à −20 vente · "
        "−20 à +20 neutre · +20 à +60 achat · ≥ +60 achat fort. "
        "Contrats à terme : séries continues Yahoo (front month, rolls non ajustés). "
        "Cet onglet ne propose plus d'actions (majors, utilities, minières) ni d'ETF d'actions énergie. "
        "Les instruments achetables au comptant sont des ETC à exposition directe sur la matière première "
        "(WisdomTree WTI OD7F, Brent OOEA, gaz TTF EGAS, gaz Henry Hub NGAS), vérifiés dans la table OMI XTB "
        "du 24/09/2026. Disponibilité Revolut Invest France non vérifiée pour ces ETC. Pas de CFD. "
        "Les contrats à terme (WTI, Brent, fioul, essence, gaz Henry Hub) restent des repères de marché, "
        "non achetables au comptant, avec une note APEX sur 250. "
        "Les ETF américains adossés à des contrats à terme (UNG, USO, BNO, UGA) ne sont pas inclus "
        "(PRIIPs, absents de la table OMI XTB du 24/09/2026). "
        "Aucun rendement n'est promis."
    ),
    'retrieved': {cfg['yahoo']: mtime('energie/yahoo_1wk_' + urllib.parse.quote(cfg['yahoo'], safe='') + '.json')
                  for cfg in ASSETS if not cfg.get('force_unavailable')},
    'spx': mtime('actions/yahoo_1wk_%5EGSPC.json'),
}

json.dump(out, open(B + 'energie.json', 'w'), ensure_ascii=False)
tp = B + 'tabs_data.json'
if os.path.exists(tp):
    tabs = json.load(open(tp))
    tabs['energie'] = out
    json.dump(tabs, open(tp, 'w'), ensure_ascii=False)

for s in fiches:
    if s.get('repere'):
        print(s['sym'].ljust(8), s['date'], 'clôt.', s['close'], 'REPÈRE DE MARCHÉ (sans note)'); continue
    if not s.get('ok'):
        print(s['sym'].ljust(8), 'INDISPONIBLE', s.get('raison', '')[:120])
        continue
    fib = s['fibo']
    fibs = f"r={f1(fib['r']*100)} % ({fib.get('zone')})" if fib.get('ok') else fib.get('texte', 'n.d.')
    print(
        s['sym'].ljust(8), s['date'], 'clôt.', s['close'], s.get('unit'),
        '| sent', s['sent']['value'], s['sent']['label'],
        '| AV', s['av']['score'], s['av']['label'],
        '| RSI', s['ind']['rsi'], (s['ind'].get('div') or {}).get('type'),
        '| MACD', s['ind']['macd_texte'],
        '| CCI', s['ind']['cci'], s['ind']['cci_zone'],
        '| Fibo', fibs,
        '| ATH', s['ath']['dd'], '%',
        '| Elliott', s['elliott'].get('phase'), s['elliott'].get('key'),
        '| TV', s.get('tv'),
        '|', s['warn'],
    )
