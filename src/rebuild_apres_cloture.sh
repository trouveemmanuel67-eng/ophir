#!/bin/bash
: "${APEX_ROOT:=$(cd "$(dirname "$0")/.." && pwd)}"
# Recalcule toutes les notes AV / sentiment sur les vraies bougies hebdo closes, puis la note /10, puis le site.
set -euo pipefail
SRC=${APEX_ROOT}/src
LOG=/tmp/rebuild_apex10.log
cd "$SRC"
exec > >(tee -a "$LOG") 2>&1
echo "==== $(date -Iseconds) rebuild APEX /10 ===="
for s in \
  build_secteurs.py \
  build_pays.py \
  build_energie.py \
  build_metaux.py \
  build_obligations.py \
  build_crypto_fiches.py \
  build_fx_apex.py \
  build_apex_bars.py \
  build_indicateur.py \
  build_sentiment_secteurs.py \
  build_rotation.py \
  build_rotation_capitaux.py \
  build_achatvente.py \
  build_data_tabs.py \
  build_obpays.py \
  build_apex10.py \
  apply_sentiment.py \
  fetch_valo_short.py \
  build_univers_short.py \
  build_short250.py \
  build_good_invest.py \
  build.py
do
  echo "---- $s $(date -Iseconds) ----"
  python3 -u "$s"
done
echo "==== done $(date -Iseconds) ===="
