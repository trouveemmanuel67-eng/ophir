#!/usr/bin/env bash
: "${APEX_ROOT:=$(cd "$(dirname "$0")/.." && pwd)}"
# Retélécharge les données brutes des onglets Actions, Crypto et Liquidités dans data/.
# Ensuite : python3 src/build_data_tabs.py && python3 src/build.py && python3 src/shot.py
set -e
D=${APEX_ROOT}/data; mkdir -p $D/{actions,crypto,liquidites}
P2=$(date +%s); UA="Mozilla/5.0"
for s in %5EFCHI %5EGSPC %5E990100-USD-STRD DX-Y.NYB; do
  curl -sf -m 30 -A "$UA" "https://query2.finance.yahoo.com/v8/finance/chart/$s?period1=946684800&period2=$P2&interval=1wk&events=history" -o $D/actions/yahoo_1wk_$s.json; sleep 3; done
for id in DGS10 GS10 VIXCLS; do curl -sf -m 60 "https://fred.stlouisfed.org/graph/fredgraph.csv?id=$id" -o $D/actions/fred_$id.csv; done
curl -sf -m 60 "https://data-api.ecb.europa.eu/service/data/IRS/M.FR.L.L40.CI.0000.EUR.N.Z?format=csvdata" -o $D/actions/ecb_IRS_FR_10y.csv
curl -sfL -m 60 -A "$UA" "https://www.multpl.com/shiller-pe/table/by-month" -o $D/actions/multpl_cape.html
python3 - <<'P'
import json,urllib.request
for a in ['btc','eth','xrp']:
    url=f"https://community-api.coinmetrics.io/v4/timeseries/asset-metrics?assets={a}&metrics=PriceUSD,CapMrktCurUSD&frequency=1d&page_size=10000&start_time=2010-01-01"; r=[]
    while url: d=json.load(urllib.request.urlopen(url,timeout=60)); r+=d['data']; url=d.get('next_page_url')
    json.dump(r,open(f'${APEX_ROOT}/data/crypto/coinmetrics_{a}_daily.json','w'))
P
for s in BTCUSDT ETHUSDT; do curl -sf -m 30 "https://api.binance.com/api/v3/klines?symbol=$s&interval=1w&limit=1000" -o $D/crypto/binance_${s}_1w.json; done
for s in XRP-USD SOL-USD; do curl -sf -m 30 -A "$UA" "https://query2.finance.yahoo.com/v8/finance/chart/$s?period1=-2208988800&period2=$P2&interval=1wk&events=history" -o $D/crypto/yahoo_1wk_$s.json; cp -f $D/crypto/yahoo_1wk_$s.json $D/fibo_max/$s.json; sleep 2; done
curl -sf -m 30 -A "$UA" "https://api.coingecko.com/api/v3/global" -o $D/crypto/coingecko_global.json
curl -sf -m 30 "https://api.alternative.me/fng/?limit=0&format=json" -o $D/crypto/alternative_fng.json
for k in "FM/D.U2.EUR.4F.KR.DFR.LEV" "EST/B.EU000A2X2A25.WT" "FM/M.U2.EUR.RT.MM.EURIBOR3MD_.HSTA" "EXR/D.USD.EUR.SP00.A" "EXR/D.JPY.EUR.SP00.A" "EXR/D.GBP.EUR.SP00.A" "EXR/D.CHF.EUR.SP00.A" "EXR/D.AUD.EUR.SP00.A" "EXR/D.CAD.EUR.SP00.A" "EXR/D.KRW.EUR.SP00.A"; do
  curl -sf -m 90 "https://data-api.ecb.europa.eu/service/data/$k?format=csvdata&startPeriod=1999-01-01" -o $D/liquidites/ecb_$(echo $k|tr '/' '_').csv; done
curl -sf -m 60 "https://bdm.insee.fr/series/sdmx/data/SERIES_BDM/011814632" -o $D/liquidites/insee_ipc_ga_011814632.xml
curl -sf -m 60 "https://opendata.caissedesdepots.fr/api/explore/v2.1/catalog/datasets/flux-et-taux-la-ldds-lep/exports/csv?use_labels=true&delimiter=%2C" -o $D/liquidites/cdc_flux_taux_la_ldds_lep.csv
# Table d'archive BdF (fixe, jusqu'à 08/2020) : déjà dans data/liquidites/bdf_taux_livrets_reglementes.csv
# Nouveaux changements de taux Livret A / LEP : ajouter une ligne citée dans data/liquidites/bdf_livrets_changements_officiels.json
# Colonne INDICATEUR
mkdir -p $D/indicateur
curl -sf -m 30 "https://api.alternative.me/fng/?limit=400&format=json" -o $D/indicateur/alternative_fng_400.json
START=$(date -d "-410 days" +%Y-%m-%d)
curl -sf -m 30 -A "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36" -H "Accept: application/json" -H "Referer: https://edition.cnn.com/" -H "Origin: https://edition.cnn.com" "https://production.dataviz.cnn.io/index/fearandgreed/graphdata/$START" -o $D/indicateur/cnn_fng.json
bash ${APEX_ROOT}/src/fetch_secteurs.sh
python3 ${APEX_ROOT}/src/fetch_fondamentaux.py   # ~15 min (yfinance, State Street, TradingView)
OBL_KEEP=1 python3 ${APEX_ROOT}/src/fetch_obligations.py   # ~5-25 min (FRED, BCE, Yahoo, TradingView ; OBL_KEEP=1 garde les fiches ETF de moins de 24 h)
# Ensuite : python3 src/build_data_tabs.py && python3 src/build_secteurs.py && python3 src/build_fondamentaux.py && python3 src/build_obligations.py && python3 src/build_indicateur.py && python3 src/build_achatvente.py && python3 src/build.py && python3 src/shot.py && python3 src/shot_indicateur.py && python3 src/shot_achatvente.py && python3 src/shot_obligations.py
echo "Données brutes mises à jour."
