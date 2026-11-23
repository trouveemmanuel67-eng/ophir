# Architecture d'amélioration pour OPHIR + Grok Bot APEX

**Statut :** Approuvé (TOP) — à implémenter via le bot APEX.

## Objectif
Rendre fluide le paramétrage de chaque indicateur, l'affichage des prix, les notes APEX, etc., avec mise à jour quotidienne des données essentielles, piloté par le Grok bot APEX.

## Architecture recommandée

### 1. Automatisation quotidienne (GitHub Actions)
- Workflow planifié (ex. 22h30 Europe/Paris après clôture US).
- Script Python (`scripts/update_positions.py`) utilisant `yfinance` + `pandas` + `ta` :
  - Récupère les cours actuels et historiques.
  - Met à jour `positions.json` (cours, valeurs, PnL, poids, perf).
  - Recalcule les indicateurs techniques (RSI, MACD, etc.).
  - Applique le moteur APEX (pondérations : Elliott ~15%, Fib ~15%, Chart patterns ~20%, divergence ~10%, etc.) pour `apex_score` / `apex_label`.
- Commit + push automatique → GitHub Pages se rafraîchit.

### 2. Configuration paramétrable
- `config/apex_config.json` ou `config/regles.json` : poids des composants, seuils, règles.
- `config/actifs.json` : mapping tickers Yahoo / TradingView, etc.
- Le bot APEX peut lire/modifier ces fichiers en langage naturel.

### 3. Rôle du Grok Bot APEX
- Routines quotidiennes de mise à jour et de contrôle.
- Paramétrage fluide : « augmente le poids Elliott à 20 % et recalcule ».
- Génération de notes APEX explicatives.
- Affichage et résumés des prix / notes / alertes.
- Gestion des drapeaux et anomalies.

### 4. Frontend
- Remplacer les embeds statiques par `fetch()` des JSON mis à jour.
- Afficher la date de dernière mise à jour.
- Option : charts TradingView ou Chart.js améliorés.

### 5. Limites
- Yahoo Finance n'a pas d'API officielle → source de secours recommandée.
- Comptages Elliott manuels restent prioritaires.
- Notes APEX = aide à la décision uniquement.

## Prochaines étapes pour le bot APEX
1. Créer `.github/workflows/daily-update.yml`.
2. Écrire le script Python de mise à jour.
3. Créer les fichiers de config de base.
4. Proposer les ajustements frontend (fetch dynamique).
5. Mettre en place la routine de contrôle quotidienne.

**Repo :** https://github.com/trouveemmanuel67-eng/ophir
**Site :** https://trouveemmanuel67-eng.github.io/ophir/
