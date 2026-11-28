#!/usr/bin/env python3
"""APE-25 : collecte des fondamentaux publics (justETF, Yahoo Finance, FRED, FMI, BRI) avec source et date.
Écrit data/fond250/*.json. Aucune donnée inventée : champ absent = None (n.c.).
Usage : python3 src/fetch_fond250.py [justetf|yahoo|fred|imf|bis|all]
"""
import json, re, sys, html, time, datetime as dt, os, io, csv, urllib.request
from pathlib import Path
ROOT = Path(os.environ.get('APEX_ROOT') or Path(__file__).resolve().parent.parent)
OUT = ROOT / 'data' / 'fond250'
OUT.mkdir(parents=True, exist_ok=True)
UA = {'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleTexWebKit/537.36 Chrome/120 Safari/537.36'}
NOW = dt.datetime.now().strftime('%Y-%m-%d %H:%M')


def get(url, timeout=40):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode('utf-8', 'replace')


def _lines(s):
    t = re.sub(r'<script.*?</script>', '', s, flags=re.S)
    t = re.sub(r'<style.*?</style>', '', t, flags=re.S)
    t = re.sub(r'<[^>]+>', '\n', t)
    t = html.unescape(t)
    return [l.strip() for l in t.split('\n') if l.strip()]


MONTHS = {m: i for i, m in enumerate(['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'], 1)}


def justetf(isin):
    url = f'https://www.justetf.com/en/etf-profile.html?isin={isin}'
    s = get(url)
    L = _lines(s)
    def after(label, n=1):
        for i, l in enumerate(L):
            if l == label or l.startswith(label):
                return L[i + 1:i + 1 + n]
        return None
    m = re.search(r'<h1[^>]*>(.*?)</h1>', s, flags=re.S)
    name = html.unescape(re.sub(r'<[^>]+>', '', m.group(1))).strip() if m else None
    rec = {'isin': isin, 'nom': name, 'source': 'justETF', 'url': url, 'date': NOW}
    v = after('Total expense ratio')
    rec['ter'] = float(re.findall(r'[\d.]+', v[0])[0]) if v and re.findall(r'[\d.]+', v[0]) else None
    v = after('Fund size', 2)
    if v:
        try:
            cur, amt = v[0].split()[0], float(v[0].split()[1].replace(',', ''))
            unit = v[1]
            mult = {'m': 1.0, 'bn': 1000.0}.get(unit.strip().lower(), None)
            rec['encours_m'] = amt * mult if mult else None
            rec['encours_devise'] = cur
        except Exception:
            rec['encours_m'] = None
    v = after('Replication')
    rec['replication'] = v[0] if v else None
    v = after('Inception Date')
    rec['creation'] = None
    if v:
        mm = re.match(r'(\d{1,2}) (\w+) (\d{4})', v[0])
        if mm and mm.group(2) in MONTHS:
            rec['creation'] = f'{mm.group(3)}-{MONTHS[mm.group(2)]:02d}-{int(mm.group(1)):02d}'
    v = after('Currency risk') or after('Currency hedged')
    rec['couverture'] = v[0] if v else None
    v = after('Fund currency'); rec['devise_fonds'] = v[0] if v else None
    v = after('Legal structure'); rec['structure'] = v[0] if v else None
    v = after('Distribution policy'); rec['distribution'] = v[0] if v else None
    # nombre de lignes (section Holdings)
    rec['n_lignes'] = None
    mm = re.search(r'out of\s*([\d,]+)', ' '.join(L))
    if mm:
        rec['n_lignes'] = int(mm.group(1).replace(',', ''))
    return rec


def isin_list():
    D = ROOT / 'data'
    out = {}
    m = json.loads((D / 'metaux.json').read_text())
    for r in m['rows']:
        for i in [r['mlist'].get('head') or {}] + list(r['mlist']['items']):
            if i.get('isin'):
                out[i['isin']] = ('metaux', i.get('tv'))
    o = json.loads((D / 'obligations.json').read_text())
    for s in o['segments']:
        for e in s.get('list') or []:
            if e.get('isin'):
                out[e['isin']] = ('obligations', e.get('tv'))
    for isin, tv in HEADS.items():
        out[isin] = ('obligations', tv)
    t = json.loads((D / 'tabs_data.json').read_text())
    for a in t['liquidites']['fx']['assets']:
        e = a.get('etf_local') or {}
        if e.get('isin') and str(e['isin'])[:2] in ('IE', 'LU', 'DE', 'FR', 'JE'):
            out[e['isin']] = ('etf_devise', e.get('tv'))
    for isin, tv in ENERGIE_ETF.items():
        out[isin] = ('energie', tv)
    return out


HEADS = {'IE00B14X4S71': 'XETR:IUSU', 'IE00BSKRJZ44': 'XETR:IS04', 'IE00B4WXJJ64': 'XETR:EUNH', 'IE00B7LGZ558': 'EURONEXT:IFRB',
         'IE0032895942': 'XETR:IBCD', 'IE00B3F81R35': 'XETR:EUN5', 'IE00BDR5HM97': 'XETR:XUHY', 'LU1452600270': 'XETR:TIUP',
         'IE00B2NPKV68': 'XETR:IUS7', 'IE00B5V94313': 'XETR:IS0L', 'LU1686831030': 'EURONEXT:EMBH'}
# ISIN candidats vérifiés par le nom renvoyé par justETF (voir verif dans le JSON)
ENERGIE_ETF = {'IE000NDWFGA5': 'XETR:URNU', 'IE0005YK6564': 'XETR:U3O8', 'IE00BM67HM91': 'XETR:XDW0', 'IE00BWBXMB69': 'XETR:ZPDU', 'GB00B15KXV33': 'LSE:CRUD', 'JE00B78CGV99': 'XETR:OOEA', 'XS2872233403': 'XETR:EGAS', 'JE00BN7KB334': 'LSE:NGAS'}


def run_justetf():
    p = OUT / 'justetf.json'
    doc = json.loads(p.read_text()) if p.exists() else {}
    for isin, (cat, tv) in isin_list().items():
        if isin in doc and doc[isin].get('ter') is not None:
            continue
        try:
            r = justetf(isin)
        except Exception as e:
            r = {'isin': isin, 'erreur': str(e)[:200], 'url': f'https://www.justetf.com/en/etf-profile.html?isin={isin}', 'date': NOW}
        r.update({'categorie': cat, 'tv': tv})
        doc[isin] = r
        print(isin, tv, r.get('nom'), r.get('ter'), r.get('encours_m'), r.get('creation'), r.get('replication'), r.get('couverture'))
        time.sleep(1.2)
    p.write_text(json.dumps(doc, ensure_ascii=False, indent=1))


YF_FIELDS = ['trailingPE', 'forwardPE', 'enterpriseToEbitda', 'totalDebt', 'totalCash', 'ebitda', 'operatingMargins', 'freeCashflow',
             'totalRevenue', 'dividendYield', 'payoutRatio', 'returnOnEquity', 'currency', 'financialCurrency', 'longName', 'sector', 'industry',
             'netExpenseRatio', 'totalAssets', 'fundInceptionDate', 'quoteType', 'marketCap']


def run_yahoo():
    import yfinance as yf
    D = ROOT / 'data'
    t = json.loads((D / 'tabs_data.json').read_text())
    syms = [a['yahoo'] for a in t['energie']['assets'] if a.get('kind') in ('equity', 'equity_proxy') and a.get('yahoo')]
    syms += [(a.get('etf_local') or {}).get('yahoo') for a in t['liquidites']['fx']['assets'] if (a.get('etf_local') or {}).get('yahoo')]
    p = OUT / 'yahoo.json'
    doc = json.loads(p.read_text()) if p.exists() else {}
    for s in syms:
        try:
            info = yf.Ticker(s).info or {}
            rec = {k: info.get(k) for k in YF_FIELDS}
        except Exception as e:
            rec = {'erreur': str(e)[:200]}
        rec.update({'source': 'Yahoo Finance (yfinance, Ticker.info)', 'url': f'https://finance.yahoo.com/quote/{s}/key-statistics', 'date': NOW})
        doc[s] = rec
        print(s, rec.get('trailingPE'), rec.get('enterpriseToEbitda'), rec.get('dividendYield'), rec.get('netExpenseRatio'))
        time.sleep(0.4)
    p.write_text(json.dumps(doc, ensure_ascii=False, indent=1))


FRED = ['DGS2', 'DGS10', 'DGS20', 'DFII5', 'DFII10', 'DFII20', 'T5YIE', 'T10YIE', 'BAMLC0A0CM', 'BAMLC0A0CMEY', 'BAMLH0A0HYM2', 'BAMLH0A0HYM2EY',
        'BAMLHE00EHYIOAS', 'BAMLHE00EHYIEY', 'BAMLEMCBPIOAS', 'BAMLEMCBPIEY', 'BAMLHE00EHYIOAS', 'BAMLEC0A0RMEY', 'BAMLEC0A0RMOAS' if False else 'BAMLC0A0CM',
        'IRLTLT01DEM156N', 'IRLTLT01FRM156N', 'IRLTLT01EZM156N', 'CP0000EZ19M086NEST', 'CPIAUCSL', 'DCOILWTICO', 'FEDFUNDS', 'ECBDFR', 'IR3TIB01EZM156N',
        'IRLTLT01JPM156N', 'CP0000FRM086NEST', 'IRLTLT01GBM156N', 'IRLTLT01CHM156N', 'IRLTLT01AUM156N', 'IRLTLT01CAM156N', 'IRLTLT01KRM156N',
        'DHHNGSP', 'DCOILBRENTEU',
        # t697u (obligations) : spread Moody's Baa − Treasury 10 ans, historique depuis 1986 (crédit IG US sur longue période).
        'BAA10Y']


def run_fred():
    d = OUT / 'fred'
    d.mkdir(exist_ok=True)
    for sid in sorted(set(FRED)):
        url = f'https://fred.stlouisfed.org/graph/fredgraph.csv?id={sid}'
        try:
            import subprocess
            s = subprocess.run(['curl', '-s', '-m', '60', url], capture_output=True, text=True, timeout=90).stdout
            if not s.startswith('observation_date') and not s.startswith('DATE'):
                raise RuntimeError('réponse inattendue')
            (d / f'{sid}.csv').write_text(s)
            last = [l for l in s.strip().split('\n') if not l.endswith(',.') and not l.endswith(',')][-1]
            print(sid, last)
        except Exception as e:
            print(sid, 'ERR', e)
    run_bbk_real()
    run_eia_energy_spots()


def run_bbk_real():
    """t697u : taux réel anticipé 10 ans allemand (Bundesbank BBSEI.M.ERZ.GVB.DE._Z.R10XX, rendement nominal du Bund
    10 ans − inflation anticipée Consensus), écrit au format FRED (date, valeur) dans fred/BBSEI_DE_R10.csv."""
    import subprocess
    url = 'https://api.statistiken.bundesbank.de/rest/download/BBSEI/M.ERZ.GVB.DE._Z.R10XX?format=csv&lang=en'
    try:
        s = subprocess.run(['curl', '-sfL', '-m', '90', '-A', 'Mozilla/5.0', url], capture_output=True, text=True, timeout=120).stdout
        rows = []
        for line in s.splitlines():
            parts = line.split(',')
            if len(parts) >= 2 and len(parts[0]) == 7 and parts[0][4] == '-' and parts[1] not in ('', '.'):
                rows.append(f'{parts[0]}-01,{float(parts[1])}')
        if len(rows) < 100:
            raise RuntimeError('série trop courte')
        (OUT / 'fred' / 'BBSEI_DE_R10.csv').write_text('observation_date,BBSEI_DE_R10\n' + '\n'.join(rows) + '\n')
        print('BBSEI_DE_R10', rows[-1])
    except Exception as e:
        print('BBSEI_DE_R10', 'ERR', e)


# EIA est la source primaire de FRED DHHNGSP (Henry Hub) et DCOILBRENTEU (Brent).
# Repli utilisé quand fredgraph.csv est injoignable.
EIA_SPOTS = {
    'DHHNGSP': {
        'url': 'https://www.eia.gov/dnav/ng/hist_xls/RNGWHHDd.xls',
        'page': 'https://www.eia.gov/dnav/ng/hist/rngwhhdd.htm',
    },
    'DCOILBRENTEU': {
        'url': 'https://www.eia.gov/dnav/pet/hist_xls/RBRTEd.xls',
        'page': 'https://www.eia.gov/dnav/pet/hist/LeafHandler.ashx?n=PET&s=RBRTE&f=D',
    },
}


def run_eia_energy_spots():
    """Télécharge les spots EIA et les écrit au format FRED si la série manque ou est trop courte."""
    import subprocess, tempfile
    d = OUT / 'fred'
    d.mkdir(exist_ok=True)
    for sid, meta in EIA_SPOTS.items():
        dest = d / f'{sid}.csv'
        # On rafraîchit si le fichier a moins de 1000 lignes utiles (échec FRED fréquent).
        n = 0
        if dest.exists():
            n = sum(1 for line in dest.read_text().splitlines() if line and not line.startswith('observation_date'))
        if n >= 1000:
            print(sid, 'EIA skip, déjà', n, 'lignes')
            continue
        try:
            raw = subprocess.run(['curl', '-sL', '-m', '60', '-A', 'Mozilla/5.0', meta['url']], capture_output=True, timeout=90)
            if raw.returncode != 0 or len(raw.stdout) < 1000:
                raise RuntimeError(f'EIA HTTP/vide ({len(raw.stdout)} o)')
            with tempfile.TemporaryDirectory() as td:
                xls = Path(td) / 'spot.xls'
                xls.write_bytes(raw.stdout)
                conv = subprocess.run(['soffice', '--headless', '--convert-to', 'xlsx', '--outdir', td, str(xls)],
                                      capture_output=True, text=True, timeout=60)
                xlsx = Path(td) / 'spot.xlsx'
                if not xlsx.exists():
                    raise RuntimeError('conversion xlsx échouée: ' + (conv.stderr or conv.stdout or '')[:200])
                import openpyxl
                wb = openpyxl.load_workbook(xlsx, data_only=True)
                sh = wb['Data 1']
                rows = [('observation_date', sid)]
                for r in range(4, sh.max_row + 1):
                    day, val = sh.cell(r, 1).value, sh.cell(r, 2).value
                    if hasattr(day, 'date') and isinstance(val, (int, float)):
                        rows.append((day.date().isoformat(), str(val)))
                if len(rows) < 100:
                    raise RuntimeError('trop peu de lignes EIA')
                dest.write_text('\n'.join(','.join(r) for r in rows) + '\n')
                print(sid, 'EIA', rows[-1], 'n=', len(rows) - 1)
        except Exception as e:
            print(sid, 'EIA ERR', e)


IMF_IND = {'PCPIPCH': 'inflation', 'BCA_NGDPD': 'balance_courante', 'GGXWDG_NGDP': 'dette_publique', 'GGXCNL_NGDP': 'solde_public',
           'NGDP_RPCH': 'croissance', 'PPPEX': 'ppp_ex'}
IMF_C = ['USA', 'JPN', 'GBR', 'CHE', 'AUS', 'CAN', 'KOR', 'DEU', 'FRA', 'EURO']


def run_imf():
    doc = {'source': 'FMI, World Economic Outlook (DataMapper API)', 'date': NOW, 'series': {}}
    for ind, lab in IMF_IND.items():
        url = f'https://www.imf.org/external/datamapper/api/v1/{ind}/' + '/'.join(IMF_C)
        try:
            j = json.loads(get(url, 60))
            doc['series'][ind] = {'label': lab, 'url': url, 'values': (j.get('values') or {}).get(ind)}
            print(ind, {k: (v or {}).get('2026') for k, v in ((j.get('values') or {}).get(ind) or {}).items()})
        except Exception as e:
            print(ind, 'ERR', e)
    (OUT / 'imf.json').write_text(json.dumps(doc, ensure_ascii=False, indent=1))


BIS_C = ['US', 'JP', 'GB', 'CH', 'AU', 'CA', 'KR', 'XM']


def run_bis():
    doc = {'source': 'BRI (BIS), taux directeurs WS_CBPOL', 'date': NOW, 'series': {}}
    for c in BIS_C:
        url = f'https://stats.bis.org/api/v2/data/dataflow/BIS/WS_CBPOL/1.0/M.{c}?format=csv&startPeriod=2024-01'
        try:
            s = get(url, 60)
            rows = list(csv.DictReader(io.StringIO(s)))
            vals = [(r.get('TIME_PERIOD'), r.get('OBS_VALUE')) for r in rows if r.get('OBS_VALUE') not in (None, '', 'NaN')]
            doc['series'][c] = {'url': url, 'values': vals}
            print(c, vals[-3:])
        except Exception as e:
            print(c, 'ERR', e)
    (OUT / 'bis.json').write_text(json.dumps(doc, ensure_ascii=False, indent=1))


WB_IND = {'FP.CPI.TOTL.ZG': 'inflation', 'BN.CAB.XOKA.GD.ZS': 'balance_courante', 'GC.DOD.TOTL.GD.ZS': 'dette_publique',
          'GC.NLD.TOTL.GD.ZS': 'solde_public', 'NY.GDP.MKTP.KD.ZG': 'croissance', 'PA.NUS.PPPC.RF': 'ratio_prix_ppa'}
WB_C = ['USA', 'JPN', 'GBR', 'CHE', 'AUS', 'CAN', 'KOR', 'EMU']


def run_wb():
    import subprocess
    doc = {'source': 'Banque mondiale, World Development Indicators (API v2)', 'date': NOW, 'series': {}}
    for ind, lab in WB_IND.items():
        url = f"https://api.worldbank.org/v2/country/{';'.join(WB_C)}/indicator/{ind}?format=json&mrv=4&per_page=200"
        try:
            j = json.loads(subprocess.run(['curl', '-s', '-m', '60', url], capture_output=True, text=True, timeout=90).stdout)
            vals = {}
            for r in j[1] or []:
                if r.get('value') is not None:
                    vals.setdefault(r['countryiso3code'], []).append((r['date'], r['value']))
            doc['series'][ind] = {'label': lab, 'url': url, 'values': {k: sorted(v)[-1] for k, v in vals.items()}}
            print(ind, doc['series'][ind]['values'])
        except Exception as e:
            print(ind, 'ERR', e)
    (OUT / 'worldbank.json').write_text(json.dumps(doc, ensure_ascii=False, indent=1))


if __name__ == '__main__':
    what = sys.argv[1] if len(sys.argv) > 1 else 'all'
    for k, f in (('wb', run_wb), ('justetf', run_justetf), ('yahoo', run_yahoo), ('fred', run_fred), ('imf', run_imf), ('bis', run_bis)):
        if what in (k, 'all'):
            f()
