"""Onglet ÉNERGIE · fiches APEX Achat / Vente (gaz, pétrole, produits raffinés, uranium, charbon, XLE, carbone).

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
import elliott_zones as EZ
import json, os, sys, math, datetime as D, statistics as st, urllib.parse
from zoneinfo import ZoneInfo
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import elliott as E, ind_core as K, fibo as FB
import courtier_cash as CC

B = '/workspace/invest/patrimoine-dashboard/data/'
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
    # ----- Pétrole et gaz (repères à terme, puis actions au comptant) -----
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
        'key': 'tte', 'sym': 'TTE', 'nom': 'TotalEnergies',
        'sous': 'EURONEXT:TTE · major intégrée, cotation Paris',
        'groupe': 'Pétrole et gaz', 'kind': 'equity',
        'yahoo': 'TTE.PA', 'tv': 'EURONEXT:TTE',
        'src_name': 'Yahoo Finance · TTE.PA',
        'url': 'https://finance.yahoo.com/quote/TTE.PA/history/',
        'unit': '€', 'fsym': 'TTE.PA', 'syms': ['EURONEXT:TTE', 'TTE.PA', 'TTE'],
        'risks': [RISK_COMMON, RISK_EQ, RISK_OPEC],
    },
    {
        'key': 'xom', 'sym': 'XOM', 'nom': 'Exxon Mobil',
        'sous': 'NYSE:XOM · major intégrée (XTB au comptant)',
        'groupe': 'Pétrole et gaz', 'kind': 'equity',
        'yahoo': 'XOM', 'tv': 'NYSE:XOM',
        'src_name': 'Yahoo Finance · XOM',
        'url': 'https://finance.yahoo.com/quote/XOM/history/',
        'unit': '$', 'fsym': 'XOM', 'syms': ['NYSE:XOM', 'XOM'],
        'risks': [RISK_COMMON, RISK_EQ, RISK_OPEC],
    },
    {
        'key': 'cvx', 'sym': 'CVX', 'nom': 'Chevron',
        'sous': 'NYSE:CVX · major intégrée',
        'groupe': 'Pétrole et gaz', 'kind': 'equity',
        'yahoo': 'CVX', 'tv': 'NYSE:CVX',
        'src_name': 'Yahoo Finance · CVX',
        'url': 'https://finance.yahoo.com/quote/CVX/history/',
        'unit': '$', 'fsym': 'CVX', 'syms': ['NYSE:CVX', 'CVX'],
        'risks': [RISK_COMMON, RISK_EQ, RISK_OPEC],
    },
    {
        'key': 'cop', 'sym': 'COP', 'nom': 'ConocoPhillips',
        'sous': 'NYSE:COP · exploration-production',
        'groupe': 'Pétrole et gaz', 'kind': 'equity',
        'yahoo': 'COP', 'tv': 'NYSE:COP',
        'src_name': 'Yahoo Finance · COP',
        'url': 'https://finance.yahoo.com/quote/COP/history/',
        'unit': '$', 'fsym': 'COP', 'syms': ['NYSE:COP', 'COP'],
        'risks': [RISK_COMMON, RISK_EQ, RISK_OPEC],
    },
    {
        'key': 'eog', 'sym': 'EOG', 'nom': 'EOG Resources',
        'sous': 'NYSE:EOG · exploration-production',
        'groupe': 'Pétrole et gaz', 'kind': 'equity',
        'yahoo': 'EOG', 'tv': 'NYSE:EOG',
        'src_name': 'Yahoo Finance · EOG',
        'url': 'https://finance.yahoo.com/quote/EOG/history/',
        'unit': '$', 'fsym': 'EOG', 'syms': ['NYSE:EOG', 'EOG'],
        'risks': [RISK_COMMON, RISK_EQ, RISK_OPEC],
    },
    {
        'key': 'oxy', 'sym': 'OXY', 'nom': 'Occidental Petroleum',
        'sous': 'NYSE:OXY · exploration-production',
        'groupe': 'Pétrole et gaz', 'kind': 'equity',
        'yahoo': 'OXY', 'tv': 'NYSE:OXY',
        'src_name': 'Yahoo Finance · OXY',
        'url': 'https://finance.yahoo.com/quote/OXY/history/',
        'unit': '$', 'fsym': 'OXY', 'syms': ['NYSE:OXY', 'OXY'],
        'risks': [RISK_COMMON, RISK_EQ, RISK_OPEC],
    },
    {
        'key': 'vlo', 'sym': 'VLO', 'nom': 'Valero Energy',
        'sous': 'NYSE:VLO · raffinage (XTB au comptant)',
        'groupe': 'Pétrole et gaz', 'kind': 'equity',
        'yahoo': 'VLO', 'tv': 'NYSE:VLO',
        'src_name': 'Yahoo Finance · VLO',
        'url': 'https://finance.yahoo.com/quote/VLO/history/',
        'unit': '$', 'fsym': 'VLO', 'syms': ['NYSE:VLO', 'VLO'],
        'risks': [RISK_COMMON, RISK_EQ, RISK_OPEC],
    },
    {
        'key': 'dvn', 'sym': 'DVN', 'nom': 'Devon Energy',
        'sous': 'NYSE:DVN · exploration-production (XTB au comptant)',
        'groupe': 'Pétrole et gaz', 'kind': 'equity',
        'yahoo': 'DVN', 'tv': 'NYSE:DVN',
        'src_name': 'Yahoo Finance · DVN',
        'url': 'https://finance.yahoo.com/quote/DVN/history/',
        'unit': '$', 'fsym': 'DVN', 'syms': ['NYSE:DVN', 'DVN'],
        'risks': [RISK_COMMON, RISK_EQ, RISK_OPEC],
    },
    {
        'key': 'fang', 'sym': 'FANG', 'nom': 'Diamondback Energy',
        'sous': 'NASDAQ:FANG · exploration-production (XTB au comptant)',
        'groupe': 'Pétrole et gaz', 'kind': 'equity',
        'yahoo': 'FANG', 'tv': 'NASDAQ:FANG',
        'src_name': 'Yahoo Finance · FANG',
        'url': 'https://finance.yahoo.com/quote/FANG/history/',
        'unit': '$', 'fsym': 'FANG', 'syms': ['NASDAQ:FANG', 'FANG'],
        'risks': [RISK_COMMON, RISK_EQ, RISK_OPEC],
    },
    {
        'key': 'imo', 'sym': 'IMO', 'nom': 'Imperial Oil',
        'sous': 'AMEX:IMO · producteur intégré canadien (XTB au comptant)',
        'groupe': 'Pétrole et gaz', 'kind': 'equity',
        'yahoo': 'IMO', 'tv': 'AMEX:IMO',
        'src_name': 'Yahoo Finance · IMO',
        'url': 'https://finance.yahoo.com/quote/IMO/history/',
        'unit': '$', 'fsym': 'IMO', 'syms': ['AMEX:IMO', 'IMO'],
        'risks': [RISK_COMMON, RISK_EQ, RISK_OPEC],
    },
    {
        'key': 'sobo', 'sym': 'SOBO', 'nom': 'South Bow',
        'sous': 'NYSE:SOBO · oléoducs (filiale de TC Energy, XTB au comptant)',
        'groupe': 'Pétrole et gaz', 'kind': 'equity',
        'yahoo': 'SOBO', 'tv': 'NYSE:SOBO',
        'src_name': 'Yahoo Finance · SOBO',
        'url': 'https://finance.yahoo.com/quote/SOBO/history/',
        'unit': '$', 'fsym': 'SOBO', 'syms': ['NYSE:SOBO', 'SOBO'],
        'risks': [RISK_COMMON, RISK_EQ, RISK_PIPE],
    },

    # ----- Gaz naturel -----
    {
        'repere': True,
        'key': 'ng', 'sym': 'BNQ9', 'nom': 'Gaz naturel (BNQ9)',
        'sous': 'XETR:BNQ9 · BNPP Natural Gas ETC (ISIN DE000PB6GAS5)',
        'groupe': 'Gaz naturel', 'kind': 'etc',
        'yahoo': 'BNQ9.DE', 'tv': 'XETR:BNQ9',
        'src_name': 'Yahoo Finance · BNQ9.DE',
        'url': 'https://finance.yahoo.com/quote/BNQ9.DE/history/',
        'unit': '€', 'fsym': 'BNQ9.DE', 'syms': ['XETR:BNQ9', 'BNQ9.DE', 'BNQ9'],
        'repere_texte': (
            "ETP coté et achetable au comptant chez Revolut (BNPP Natural Gas ETC, ISIN DE000PB6GAS5, Xetra). "
            "Il est affiché comme repère de marché, sans note APEX ni drapeau, parce qu'il est adossé à des "
            "contrats à terme : ce n'est pas le prix spot du gaz, le roll des échéances a un coût en détention "
            "longue, et l'instrument est très volatil."
        ),
        'risks': [RISK_COMMON, RISK_BNQ9, RISK_GAS],
        'reuse': 'energie',
    },
    {
        'key': 'wmb', 'sym': 'WMB', 'nom': 'Williams Companies',
        'sous': 'NYSE:WMB · gazoducs / midstream (XTB au comptant)',
        'groupe': 'Gaz naturel', 'kind': 'equity',
        'yahoo': 'WMB', 'tv': 'NYSE:WMB',
        'src_name': 'Yahoo Finance · WMB',
        'url': 'https://finance.yahoo.com/quote/WMB/history/',
        'unit': '$', 'fsym': 'WMB', 'syms': ['NYSE:WMB', 'WMB'],
        'risks': [RISK_COMMON, RISK_EQ, RISK_PIPE],
    },
    {
        'key': 'kmi', 'sym': 'KMI', 'nom': 'Kinder Morgan',
        'sous': 'NYSE:KMI · gazoducs / midstream (XTB au comptant)',
        'groupe': 'Gaz naturel', 'kind': 'equity',
        'yahoo': 'KMI', 'tv': 'NYSE:KMI',
        'src_name': 'Yahoo Finance · KMI',
        'url': 'https://finance.yahoo.com/quote/KMI/history/',
        'unit': '$', 'fsym': 'KMI', 'syms': ['NYSE:KMI', 'KMI'],
        'risks': [RISK_COMMON, RISK_EQ, RISK_PIPE],
    },
    {
        'key': 'oke', 'sym': 'OKE', 'nom': 'ONEOK',
        'sous': 'NYSE:OKE · midstream gaz / LGN (XTB au comptant)',
        'groupe': 'Gaz naturel', 'kind': 'equity',
        'yahoo': 'OKE', 'tv': 'NYSE:OKE',
        'src_name': 'Yahoo Finance · OKE',
        'url': 'https://finance.yahoo.com/quote/OKE/history/',
        'unit': '$', 'fsym': 'OKE', 'syms': ['NYSE:OKE', 'OKE'],
        'risks': [RISK_COMMON, RISK_EQ, RISK_PIPE],
    },
    {
        'key': 'trgp', 'sym': 'TRGP', 'nom': 'Targa Resources',
        'sous': 'NYSE:TRGP · midstream gaz / LGN (XTB au comptant)',
        'groupe': 'Gaz naturel', 'kind': 'equity',
        'yahoo': 'TRGP', 'tv': 'NYSE:TRGP',
        'src_name': 'Yahoo Finance · TRGP',
        'url': 'https://finance.yahoo.com/quote/TRGP/history/',
        'unit': '$', 'fsym': 'TRGP', 'syms': ['NYSE:TRGP', 'TRGP'],
        'risks': [RISK_COMMON, RISK_EQ, RISK_PIPE],
    },
    {
        'key': 'enb', 'sym': 'ENB', 'nom': 'Enbridge',
        'sous': 'NYSE:ENB · oléoducs et gazoducs (XTB au comptant)',
        'groupe': 'Gaz naturel', 'kind': 'equity',
        'yahoo': 'ENB', 'tv': 'NYSE:ENB',
        'src_name': 'Yahoo Finance · ENB',
        'url': 'https://finance.yahoo.com/quote/ENB/history/',
        'unit': '$', 'fsym': 'ENB', 'syms': ['NYSE:ENB', 'ENB'],
        'risks': [RISK_COMMON, RISK_EQ, RISK_PIPE],
    },
    {
        'key': 'trp', 'sym': 'TRP', 'nom': 'TC Energy',
        'sous': 'NYSE:TRP · gazoducs (XTB au comptant)',
        'groupe': 'Gaz naturel', 'kind': 'equity',
        'yahoo': 'TRP', 'tv': 'NYSE:TRP',
        'src_name': 'Yahoo Finance · TRP',
        'url': 'https://finance.yahoo.com/quote/TRP/history/',
        'unit': '$', 'fsym': 'TRP', 'syms': ['NYSE:TRP', 'TRP'],
        'risks': [RISK_COMMON, RISK_EQ, RISK_PIPE],
    },
    {
        'key': 'pba', 'sym': 'PBA', 'nom': 'Pembina Pipeline',
        'sous': 'NYSE:PBA · midstream canadien (XTB au comptant)',
        'groupe': 'Gaz naturel', 'kind': 'equity',
        'yahoo': 'PBA', 'tv': 'NYSE:PBA',
        'src_name': 'Yahoo Finance · PBA',
        'url': 'https://finance.yahoo.com/quote/PBA/history/',
        'unit': '$', 'fsym': 'PBA', 'syms': ['NYSE:PBA', 'PBA'],
        'risks': [RISK_COMMON, RISK_EQ, RISK_PIPE],
    },
    {
        'key': 'gtt', 'sym': 'GTT', 'nom': 'Gaztransport & Technigaz',
        'sous': 'EURONEXT:GTT · confinement GNL, cotation Paris',
        'groupe': 'Gaz naturel', 'kind': 'equity',
        'yahoo': 'GTT.PA', 'tv': 'EURONEXT:GTT',
        'src_name': 'Yahoo Finance · GTT.PA',
        'url': 'https://finance.yahoo.com/quote/GTT.PA/history/',
        'unit': '€', 'fsym': 'GTT.PA', 'syms': ['EURONEXT:GTT', 'GTT.PA', 'GTT'],
        'risks': [RISK_COMMON, RISK_EQ, RISK_PIPE],
    },
    {
        'key': 'ig', 'sym': 'IG', 'nom': 'Italgas',
        'sous': 'MIL:IG · distribution de gaz, cotation Milan',
        'groupe': 'Gaz naturel', 'kind': 'equity',
        'yahoo': 'IG.MI', 'tv': 'MIL:IG',
        'src_name': 'Yahoo Finance · IG.MI',
        'url': 'https://finance.yahoo.com/quote/IG.MI/history/',
        'unit': '€', 'fsym': 'IG.MI', 'syms': ['MIL:IG', 'IG.MI', 'IG'],
        'risks': [RISK_COMMON, RISK_EQ, RISK_PIPE],
    },

    # ----- Électricité et utilities -----
    {
        'key': 'nee', 'sym': 'NEE', 'nom': 'NextEra Energy',
        'sous': 'NYSE:NEE · utility et renouvelables',
        'groupe': 'Électricité et utilities', 'kind': 'equity',
        'yahoo': 'NEE', 'tv': 'NYSE:NEE',
        'src_name': 'Yahoo Finance · NEE',
        'url': 'https://finance.yahoo.com/quote/NEE/history/',
        'unit': '$', 'fsym': 'NEE', 'syms': ['NYSE:NEE', 'NEE'],
        'risks': [RISK_COMMON, RISK_EQ, RISK_UTIL],
    },
    {
        'key': 'vst', 'sym': 'VST', 'nom': 'Vistra',
        'sous': 'NYSE:VST · producteur d\'électricité',
        'groupe': 'Électricité et utilities', 'kind': 'equity',
        'yahoo': 'VST', 'tv': 'NYSE:VST',
        'src_name': 'Yahoo Finance · VST',
        'url': 'https://finance.yahoo.com/quote/VST/history/',
        'unit': '$', 'fsym': 'VST', 'syms': ['NYSE:VST', 'VST'],
        'risks': [RISK_COMMON, RISK_EQ, RISK_UTIL],
    },
    {
        'key': 'etr', 'sym': 'ETR', 'nom': 'Entergy',
        'sous': 'NYSE:ETR · utility (nucléaire et réseaux)',
        'groupe': 'Électricité et utilities', 'kind': 'equity',
        'yahoo': 'ETR', 'tv': 'NYSE:ETR',
        'src_name': 'Yahoo Finance · ETR',
        'url': 'https://finance.yahoo.com/quote/ETR/history/',
        'unit': '$', 'fsym': 'ETR', 'syms': ['NYSE:ETR', 'ETR'],
        'risks': [RISK_COMMON, RISK_EQ, RISK_UTIL],
    },
    {
        'key': 'awk', 'sym': 'AWK', 'nom': 'American Water Works',
        'sous': 'NYSE:AWK · utility eau',
        'groupe': 'Électricité et utilities', 'kind': 'equity',
        'yahoo': 'AWK', 'tv': 'NYSE:AWK',
        'src_name': 'Yahoo Finance · AWK',
        'url': 'https://finance.yahoo.com/quote/AWK/history/',
        'unit': '$', 'fsym': 'AWK', 'syms': ['NYSE:AWK', 'AWK'],
        'risks': [RISK_COMMON, RISK_EQ, RISK_UTIL],
    },
    {
        'key': 'so', 'sym': 'SO', 'nom': 'Southern Company',
        'sous': 'NYSE:SO · utility (XTB au comptant)',
        'groupe': 'Électricité et utilities', 'kind': 'equity',
        'yahoo': 'SO', 'tv': 'NYSE:SO',
        'src_name': 'Yahoo Finance · SO',
        'url': 'https://finance.yahoo.com/quote/SO/history/',
        'unit': '$', 'fsym': 'SO', 'syms': ['NYSE:SO', 'SO'],
        'risks': [RISK_COMMON, RISK_EQ, RISK_UTIL],
    },
    {
        'key': 'duk', 'sym': 'DUK', 'nom': 'Duke Energy',
        'sous': 'NYSE:DUK · utility (XTB au comptant)',
        'groupe': 'Électricité et utilities', 'kind': 'equity',
        'yahoo': 'DUK', 'tv': 'NYSE:DUK',
        'src_name': 'Yahoo Finance · DUK',
        'url': 'https://finance.yahoo.com/quote/DUK/history/',
        'unit': '$', 'fsym': 'DUK', 'syms': ['NYSE:DUK', 'DUK'],
        'risks': [RISK_COMMON, RISK_EQ, RISK_UTIL],
    },
    {
        'key': 'xel', 'sym': 'XEL', 'nom': 'Xcel Energy',
        'sous': 'NASDAQ:XEL · utility (XTB au comptant)',
        'groupe': 'Électricité et utilities', 'kind': 'equity',
        'yahoo': 'XEL', 'tv': 'NASDAQ:XEL',
        'src_name': 'Yahoo Finance · XEL',
        'url': 'https://finance.yahoo.com/quote/XEL/history/',
        'unit': '$', 'fsym': 'XEL', 'syms': ['NASDAQ:XEL', 'XEL'],
        'risks': [RISK_COMMON, RISK_EQ, RISK_UTIL],
    },
    {
        'key': 'aep', 'sym': 'AEP', 'nom': 'American Electric Power',
        'sous': 'NASDAQ:AEP · utility (XTB au comptant)',
        'groupe': 'Électricité et utilities', 'kind': 'equity',
        'yahoo': 'AEP', 'tv': 'NASDAQ:AEP',
        'src_name': 'Yahoo Finance · AEP',
        'url': 'https://finance.yahoo.com/quote/AEP/history/',
        'unit': '$', 'fsym': 'AEP', 'syms': ['NASDAQ:AEP', 'AEP'],
        'risks': [RISK_COMMON, RISK_EQ, RISK_UTIL],
    },
    {
        'key': 'enel', 'sym': 'ENEL', 'nom': 'Enel',
        'sous': 'MIL:ENEL · utility, cotation Milan',
        'groupe': 'Électricité et utilities', 'kind': 'equity',
        'yahoo': 'ENEL.MI', 'tv': 'MIL:ENEL',
        'src_name': 'Yahoo Finance · ENEL.MI',
        'url': 'https://finance.yahoo.com/quote/ENEL.MI/history/',
        'unit': '€', 'fsym': 'ENEL.MI', 'syms': ['MIL:ENEL', 'ENEL.MI', 'ENEL'],
        'risks': [RISK_COMMON, RISK_EQ, RISK_UTIL],
    },
    {
        'key': 'eoan', 'sym': 'EOAN', 'nom': 'E.ON',
        'sous': 'XETR:EOAN · réseaux et énergie, cotation Xetra',
        'groupe': 'Électricité et utilities', 'kind': 'equity',
        'yahoo': 'EOAN.DE', 'tv': 'XETR:EOAN',
        'src_name': 'Yahoo Finance · EOAN.DE',
        'url': 'https://finance.yahoo.com/quote/EOAN.DE/history/',
        'unit': '€', 'fsym': 'EOAN.DE', 'syms': ['XETR:EOAN', 'EOAN.DE', 'EOAN'],
        'risks': [RISK_COMMON, RISK_EQ, RISK_UTIL],
    },
    {
        'key': 'rwe', 'sym': 'RWE', 'nom': 'RWE',
        'sous': 'XETR:RWE · producteur d\'électricité, cotation Xetra',
        'groupe': 'Électricité et utilities', 'kind': 'equity',
        'yahoo': 'RWE.DE', 'tv': 'XETR:RWE',
        'src_name': 'Yahoo Finance · RWE.DE',
        'url': 'https://finance.yahoo.com/quote/RWE.DE/history/',
        'unit': '€', 'fsym': 'RWE.DE', 'syms': ['XETR:RWE', 'RWE.DE', 'RWE'],
        'risks': [RISK_COMMON, RISK_EQ, RISK_UTIL],
    },
    {
        'key': 'engi', 'sym': 'ENGI', 'nom': 'Engie',
        'sous': 'EURONEXT:ENGI · énergie et services, cotation Paris',
        'groupe': 'Électricité et utilities', 'kind': 'equity',
        'yahoo': 'ENGI.PA', 'tv': 'EURONEXT:ENGI',
        'src_name': 'Yahoo Finance · ENGI.PA',
        'url': 'https://finance.yahoo.com/quote/ENGI.PA/history/',
        'unit': '€', 'fsym': 'ENGI.PA', 'syms': ['EURONEXT:ENGI', 'ENGI.PA', 'ENGI'],
        'risks': [RISK_COMMON, RISK_EQ, RISK_UTIL],
    },
    {
        'key': 'fts', 'sym': 'FTS', 'nom': 'Fortis',
        'sous': 'NYSE:FTS · utility canadienne (XTB au comptant)',
        'groupe': 'Électricité et utilities', 'kind': 'equity',
        'yahoo': 'FTS', 'tv': 'NYSE:FTS',
        'src_name': 'Yahoo Finance · FTS',
        'url': 'https://finance.yahoo.com/quote/FTS/history/',
        'unit': '$', 'fsym': 'FTS', 'syms': ['NYSE:FTS', 'FTS'],
        'risks': [RISK_COMMON, RISK_EQ, RISK_UTIL],
    },
    {
        'key': 'aqn', 'sym': 'AQN', 'nom': 'Algonquin Power & Utilities',
        'sous': 'NYSE:AQN · utility et renouvelables (XTB au comptant)',
        'groupe': 'Électricité et utilities', 'kind': 'equity',
        'yahoo': 'AQN', 'tv': 'NYSE:AQN',
        'src_name': 'Yahoo Finance · AQN',
        'url': 'https://finance.yahoo.com/quote/AQN/history/',
        'unit': '$', 'fsym': 'AQN', 'syms': ['NYSE:AQN', 'AQN'],
        'risks': [RISK_COMMON, RISK_EQ, RISK_UTIL],
    },
    {
        'key': 'bepc', 'sym': 'BEPC', 'nom': 'Brookfield Renewable',
        'sous': 'NYSE:BEPC · producteur renouvelable (XTB au comptant)',
        'groupe': 'Électricité et utilities', 'kind': 'equity',
        'yahoo': 'BEPC', 'tv': 'NYSE:BEPC',
        'src_name': 'Yahoo Finance · BEPC',
        'url': 'https://finance.yahoo.com/quote/BEPC/history/',
        'unit': '$', 'fsym': 'BEPC', 'syms': ['NYSE:BEPC', 'BEPC'],
        'risks': [RISK_COMMON, RISK_EQ, RISK_UTIL],
    },

    # ----- Solaire -----
    {
        'key': 'enph', 'sym': 'ENPH', 'nom': 'Enphase Energy',
        'sous': 'NASDAQ:ENPH · micro-onduleurs solaires (XTB au comptant, position active)',
        'groupe': 'Solaire', 'kind': 'equity',
        'yahoo': 'ENPH', 'tv': 'NASDAQ:ENPH',
        'src_name': 'Yahoo Finance · ENPH',
        'url': 'https://finance.yahoo.com/quote/ENPH/history/',
        'unit': '$', 'fsym': 'ENPH', 'syms': ['NASDAQ:ENPH', 'ENPH'],
        'risks': [RISK_COMMON, RISK_EQ, RISK_SOLAR],
    },
    {
        'key': 'csiq', 'sym': 'CSIQ', 'nom': 'Canadian Solar',
        'sous': 'NASDAQ:CSIQ · modules solaires (XTB au comptant)',
        'groupe': 'Solaire', 'kind': 'equity',
        'yahoo': 'CSIQ', 'tv': 'NASDAQ:CSIQ',
        'src_name': 'Yahoo Finance · CSIQ',
        'url': 'https://finance.yahoo.com/quote/CSIQ/history/',
        'unit': '$', 'fsym': 'CSIQ', 'syms': ['NASDAQ:CSIQ', 'CSIQ'],
        'risks': [RISK_COMMON, RISK_EQ, RISK_SOLAR],
    },

    # ----- Éolien -----
    {
        'key': 'enr', 'sym': 'ENR', 'nom': 'Siemens Energy',
        'sous': 'XETR:ENR · équipementier (éolien, turbines, réseau)',
        'groupe': 'Éolien', 'kind': 'equity',
        'yahoo': 'ENR.DE', 'tv': 'XETR:ENR',
        'src_name': 'Yahoo Finance · ENR.DE',
        'url': 'https://finance.yahoo.com/quote/ENR.DE/history/',
        'unit': '€', 'fsym': 'ENR.DE', 'syms': ['XETR:ENR', 'ENR.DE', 'ENR'],
        'risks': [RISK_COMMON, RISK_EQ, RISK_WIND],
    },

    # ----- Nucléaire et uranium -----
    {
        'key': 'urnu', 'sym': 'URNU', 'nom': 'ETF uranium URNU (UCITS)',
        'sous': 'XETR:URNU · Global X Uranium UCITS ETF (remplace AMEX:URA, non vendu chez Revolut)',
        'groupe': 'Nucléaire et uranium', 'kind': 'etf_equity',
        'yahoo': 'URNU.DE', 'tv': 'XETR:URNU',
        'src_name': 'Yahoo Finance · URNU.DE',
        'url': 'https://finance.yahoo.com/quote/URNU.DE/history/',
        'unit': '€', 'fsym': 'URNU.DE', 'syms': ['XETR:URNU', 'URNU.DE'],
        'risks': [RISK_COMMON, RISK_U_ETF],
        'reuse': 'energie',
    },
    {
        'key': 'u3o8', 'sym': 'U3O8', 'nom': 'ETF minières uranium U3O8 (UCITS)',
        'sous': 'XETR:U3O8 · Sprott Uranium Miners UCITS ETF (remplace AMEX:URNM, non vendu chez Revolut)',
        'groupe': 'Nucléaire et uranium', 'kind': 'etf_equity',
        'yahoo': 'U3O8.DE', 'tv': 'XETR:U3O8',
        'src_name': 'Yahoo Finance · U3O8.DE',
        'url': 'https://finance.yahoo.com/quote/U3O8.DE/history/',
        'unit': '€', 'fsym': 'U3O8.DE', 'syms': ['XETR:U3O8', 'U3O8.DE'],
        'risks': [RISK_COMMON, RISK_U_ETF],
        'reuse': 'energie',
    },
    {
        'key': 'ccj', 'sym': 'CCJ', 'nom': 'Uranium · proxy Cameco',
        'sous': "NYSE:CCJ · action, pas le prix de l'uranium (remplace TSX:U-U, pas d'uranium physique chez Revolut)",
        'groupe': 'Nucléaire et uranium', 'kind': 'equity_proxy',
        'yahoo': 'CCJ', 'tv': 'NYSE:CCJ',
        'src_name': 'Yahoo Finance · CCJ',
        'url': 'https://finance.yahoo.com/quote/CCJ/history/',
        'unit': '$', 'fsym': 'CCJ', 'syms': ['NYSE:CCJ', 'CCJ'],
        'risks': [RISK_COMMON, RISK_CCJ],
        'reuse': 'energie',
    },
    {
        'key': 'ceg', 'sym': 'CEG', 'nom': 'Constellation Energy',
        'sous': 'NASDAQ:CEG · producteur d\'électricité nucléaire',
        'groupe': 'Nucléaire et uranium', 'kind': 'equity',
        'yahoo': 'CEG', 'tv': 'NASDAQ:CEG',
        'src_name': 'Yahoo Finance · CEG',
        'url': 'https://finance.yahoo.com/quote/CEG/history/',
        'unit': '$', 'fsym': 'CEG', 'syms': ['NASDAQ:CEG', 'CEG'],
        'risks': [RISK_COMMON, RISK_EQ, RISK_UTIL],
    },

    # ----- Hydrogène et stockage -----
    {
        'key': 'bldp', 'sym': 'BLDP', 'nom': 'Ballard Power Systems',
        'sous': 'NASDAQ:BLDP · piles à combustible (XTB au comptant)',
        'groupe': 'Hydrogène et stockage', 'kind': 'equity',
        'yahoo': 'BLDP', 'tv': 'NASDAQ:BLDP',
        'src_name': 'Yahoo Finance · BLDP',
        'url': 'https://finance.yahoo.com/quote/BLDP/history/',
        'unit': '$', 'fsym': 'BLDP', 'syms': ['NASDAQ:BLDP', 'BLDP'],
        'risks': [RISK_COMMON, RISK_EQ, RISK_H2],
    },

    # ----- Charbon (existant, conservé) -----
    {
        'key': 'btu', 'sym': 'BTU', 'nom': 'Charbon · proxy Peabody Energy',
        'sous': 'NYSE:BTU · action, pas un indice du prix du charbon',
        'groupe': 'Charbon', 'kind': 'equity_proxy',
        'yahoo': 'BTU', 'tv': 'NYSE:BTU',
        'src_name': 'Yahoo Finance · BTU',
        'url': 'https://finance.yahoo.com/quote/BTU/history/',
        'unit': '$', 'fsym': 'BTU', 'syms': ['NYSE:BTU', 'BTU'],
        'risks': [RISK_COMMON, RISK_COAL],
        'reuse': 'energie',
    },

    # ----- ETF UCITS -----
    {
        'key': 'xdw0', 'sym': 'XDW0', 'nom': 'ETF énergie mondiale XDW0 (UCITS)',
        'sous': 'XETR:XDW0 · Xtrackers MSCI World Energy UCITS ETF (remplace AMEX:XLE, non vendu chez Revolut)',
        'groupe': 'ETF énergie et utilities (UCITS)', 'kind': 'etf_equity',
        'yahoo': 'XDW0.DE', 'tv': 'XETR:XDW0',
        'src_name': 'Yahoo Finance · XDW0.DE',
        'url': 'https://finance.yahoo.com/quote/XDW0.DE/history/',
        'unit': '€', 'fsym': 'XDW0.DE', 'syms': ['XETR:XDW0', 'XDW0.DE'],
        'risks': [RISK_COMMON, RISK_XLE, RISK_OPEC],
        'reuse': 'energie',
    },
    {
        'key': 'zpdu', 'sym': 'ZPDU', 'nom': 'ETF utilities US ZPDU (UCITS)',
        'sous': 'XETR:ZPDU · SPDR S&P US Utilities Select Sector UCITS ETF (remplace AMEX:XLU, non vendu chez Revolut)',
        'groupe': 'ETF énergie et utilities (UCITS)', 'kind': 'etf_equity',
        'yahoo': 'ZPDU.DE', 'tv': 'XETR:ZPDU',
        'src_name': 'Yahoo Finance · ZPDU.DE',
        'url': 'https://finance.yahoo.com/quote/ZPDU.DE/history/',
        'unit': '€', 'fsym': 'ZPDU.DE', 'syms': ['XETR:ZPDU', 'ZPDU.DE'],
        'risks': [RISK_COMMON, RISK_ZPDU],
        'reuse': 'secteurs',
    },
]


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

_spx_en = B + 'energie/yahoo_1wk_%5EGSPC.json'
_spx_ac = B + 'actions/yahoo_1wk_%5EGSPC.json'
spx_w, _ = K.yweekly(_spx_en if os.path.exists(_spx_en) else _spx_ac)
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
        'Pétrole et gaz', 'Gaz naturel', 'Électricité et utilities', 'Solaire', 'Éolien',
        'Nucléaire et uranium', 'Hydrogène et stockage', 'Charbon',
        'ETF énergie et utilities (UCITS)',
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
        "Les ETF adossés à des contrats à terme (UNG, USO, BNO, UGA, KRBN) ne sont pas inclus. "
        "Le charbon est suivi par l'action Peabody Energy (BTU), clairement identifiée comme proxy. "
        "Seuls les actifs achetables au comptant chez Revolut Invest France ou XTB (pas de CFD) ont une note. "
        "Les contrats à terme (WTI, Brent, fioul, essence) restent des repères de marché, sans note ni signal. "
        "Le gaz est suivi par l'ETP BNQ9 (BNPP Natural Gas ETC, ISIN DE000PB6GAS5), également affiché comme "
        "repère de marché sans note, car il est adossé à des contrats à terme (coût de roll, forte volatilité). "
        "Les ETF ou ETP adossés à des contrats à terme (UNG, USO, BNO, UGA, KRBN) restent exclus. "
        "Les notes déjà publiées au 18/11/2026 (URNU, U3O8, CCJ, BTU, XDW0, ZPDU) ne sont pas recalculées. "
        "Le signal de l'onglet est la note APEX de XDW0 (ETF UCITS MSCI World Energy), la même que sur l'onglet Actions / Secteurs. "
        "Aucun rendement n'est promis."
    ),
    'retrieved': {cfg['yahoo']: mtime('energie/yahoo_1wk_' + urllib.parse.quote(cfg['yahoo'], safe='') + '.json')
                  for cfg in ASSETS if not cfg.get('force_unavailable')},
    'spx': mtime('actions/yahoo_1wk_%5EGSPC.json'),
}

xdw0 = next((s for s in fiches if s.get('sym')=='XDW0' and s.get('av') and s['av'].get('score') is not None), None)
if xdw0:
    av = json.loads(json.dumps(xdw0['av']))
    av['date'] = xdw0.get('date') or av.get('date')
    av['sens'] = av.get('sens') or (
        "Score > 0 : contexte plus favorable à l'achat d'actions d'énergie ; < 0 : plus favorable à l'allègement."
    )
    av['method'] = (
        "Signal du secteur Énergie : note APEX de l'ETF UCITS Xtrackers MSCI World Energy (XETR:XDW0), "
        "déjà calculée le 18/11/2026 avec la grille APEX à 18/11 et reprise telle quelle (pas de recalcul). "
        "C'est la même note que sur l'onglet Actions / Secteurs. Ce n'est pas une moyenne des fiches de l'onglet."
    )
    av['sources'] = [[xdw0.get('src_name') or 'Yahoo Finance · XDW0.DE', xdw0.get('url') or 'https://finance.yahoo.com/quote/XDW0.DE/history/']]
    out['av'] = av
    out['av_source'] = 'XETR:XDW0'
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
