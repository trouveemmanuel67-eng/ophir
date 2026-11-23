#!/bin/sh
# Active le hook pre-commit du dépôt (githooks/).
set -e
ROOT=$(git rev-parse --show-toplevel)
cd "$ROOT"
git config core.hooksPath githooks
chmod +x githooks/pre-commit scripts/garde_fou_site.py
echo "Hook pre-commit activé (core.hooksPath=githooks)."
