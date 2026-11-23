#!/usr/bin/env bash
: "${APEX_ROOT:=$(cd "$(dirname "$0")/.." && pwd)}"
# Clôtures hebdomadaires Yahoo des 11 ETF sectoriels SPDR (GICS) + S&P 500 de référence -> data/secteurs/
set -e
D=${APEX_ROOT}/data/secteurs; mkdir -p $D
P2=$(date +%s); UA="Mozilla/5.0"
for s in XLC XLY XLP XLE XLF XLV XLI XLB XLRE XLK XLU %5EGSPC; do
  curl -sf -m 30 -A "$UA" "https://query2.finance.yahoo.com/v8/finance/chart/$s?period1=946684800&period2=$P2&interval=1wk&events=history" -o $D/yahoo_1wk_$s.json; sleep 2; done
echo ok
