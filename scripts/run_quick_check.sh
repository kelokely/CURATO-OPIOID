#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
PYTHON_BIN="${PYTHON:-python3}"

"$PYTHON_BIN" pipeline/curate.py \
  --ontology config/pharmacology_ontology.json \
  --curated-long \
    data/fully_pooled/development/curated_long.csv \
    data/fully_pooled/external/curated_long.csv \
  --out results/quick_check/curation_validation_summary.json

"$PYTHON_BIN" pipeline/benchmark.py \
  --case-dir data/fully_pooled \
  --ontology config/pharmacology_ontology.json \
  --out results/quick_check/fully_pooled \
  --quick \
  --quick-rows 120 \
  --models RF,XGB,LGBM,SVR,Consensus

echo "Quick check completed. See results/quick_check/."
