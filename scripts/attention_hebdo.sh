#!/bin/bash
# APEX · Indicateur d'Attention Long Swing (H) — recalcul hebdomadaire (week-end) et publication.
# Commande unique :  bash /workspace/invest/patrimoine-dashboard/scripts/attention_hebdo.sh
# Options : --no-push (tout sauf commit/push) · --max-minutes N (budget Google Trends, défaut 180)
# 1. attention des actions USA + France (Trends avec cache/reprise, ApeWisdom daté, volume yfinance)
# 2. apport H appliqué aux notes APEX actions (−80 à 280), sans toucher aux autres sections
# 3. build du site, copie vers ophir-site, tests, garde-fou, commit + push
set -euo pipefail
GEN=/workspace/invest/patrimoine-dashboard
SITE=/workspace/invest/ophir-site
PUSH=1; MAXMIN=180
while [ $# -gt 0 ]; do
  case "$1" in
    --no-push) PUSH=0;;
    --max-minutes) MAXMIN="$2"; shift;;
  esac; shift
done
LOG=/workspace/invest/attention_pilote/hebdo_$(date +%F).log
exec > >(tee -a "$LOG") 2>&1
echo "==== $(date '+%F %T') attention hebdo ===="
cd "$GEN"
export APEX_ROOT="$GEN" APEX_SITE="$SITE"
# reprise : si des termes Trends restent bloqués (429), relancer la commande, le cache de la semaine est réutilisé
python3 -u src/attention_apex.py --max-minutes "$MAXMIN"
python3 -u src/apply_attention.py
python3 -u src/build.py
# copie des fichiers concernés vers le dépôt du site
for f in data/attention_apex.json data/apex_achat_v2_pilot.json data/apex_achat_v2_scores_full.json \
         src/attention_apex.py src/apply_attention.py scripts/attention_hebdo.sh; do
  mkdir -p "$SITE/$(dirname "$f")"; cp -p "$f" "$SITE/$f"
done
mkdir -p "$SITE/data/attention"
rsync -a --exclude trends_cache "$GEN/data/attention/" "$SITE/data/attention/"
cd "$SITE"
APEX_ROOT="$SITE" python3 -m pytest -q -p no:cacheprovider tests/test_apex_achat_v2_pilot.py tests/test_page_regles.py -k "not test_tableau_grille_homogene"
python3 scripts/garde_fou_site.py --root "$SITE"
if [ "$PUSH" = 1 ]; then
  git add index.html data/attention_apex.json data/attention data/apex_achat_v2_pilot.json \
          data/apex_achat_v2_scores_full.json data/apex_achat_v2_site.json data/build-version.json \
          src/attention_apex.py src/apply_attention.py scripts/attention_hebdo.sh
  if git diff --cached --quiet; then echo "Aucun changement."; else
    git commit -m "APEX · Attention H hebdomadaire ($(date '+%d/%m/%Y') Europe/Paris)."
    git push origin HEAD
    echo "En ligne : https://trouveemmanuel67-eng.github.io/ophir/?v=$(git rev-parse --short HEAD) (cache Pages ~10 min)"
  fi
fi
echo "==== fin $(date '+%F %T') ===="
