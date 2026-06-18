# Opioid Bioactivity Stratification Reference

This repository is a minimal reference implementation for reproducing the opioid-receptor bioactivity curation and benchmarking study. It demonstrates pharmacological and assay-readout stratification of public bioactivity data for MOR, DOR, KOR, and NOP/NOR, followed by scaffold-locked external QSAR benchmarking.

This is not the production pipeline. It contains the scientific reference path needed for reproducibility: frozen curated CSV inputs, a versioned pharmacology/assay-readout ontology, model training, external validation, and pooled-vs-stratified contrast generation.

## Repository Structure

```text
config/
  pharmacology_ontology.json        Versioned ontology used for stratification provenance.
data/
  stratified/                       Frozen curated-wide matrices for naive, balanced, and maximal arms.
  fully_pooled/                     Frozen fully pooled curated-wide and curated-long inputs.
expected_outputs/
  fully_pooled_vs_stratified_external_contrast.csv
pipeline/
  curate.py                         Validates ontology and frozen curated-long inputs.
  benchmark.py                      Trains RF, XGB, LGBM, SVR, and Consensus models.
  compare.py                        Builds pooled-vs-stratified contrast tables.
src/opioid_ref/
  benchmark.py                      Reference benchmark implementation.
  compare.py                        Contrast-table implementation.
  ontology.py                       Ontology loading and provenance hashing.
scripts/
  run_quick_check.sh                Fast smoke test on a subset.
```

## Installation

Python 3.11 or newer is recommended.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -e .
```

The pinned environment includes RDKit, scikit-learn, XGBoost, LightGBM, and SHAP. SHAP is included for interpretability extensions; the default quick check does not require SHAP output.

## Ontology Design

The stratification rules are stored in `config/pharmacology_ontology.json`. The code loads this file at runtime and records its version and SHA-256 hash in provenance outputs. Supporting a new target class should be done by editing or extending the ontology, not by adding hidden pharmacology rules to Python code.

The supplied ontology is the version used to document the opioid-reference curation logic. It should be treated as demonstrated and extensible, not universal for every possible pharmacological assay type.

## Data Included

The repository includes frozen curated CSV inputs derived from public ChEMBL, BindingDB, and PubChem records used for the opioid study.

The compact stratified arms include curated-wide matrices for:

- `data/stratified/naive`
- `data/stratified/balanced`
- `data/stratified/maximal`

The fully pooled arm includes both curated-wide matrices and sanitized curated-long row-level tables:

- `data/fully_pooled/development/curated_long.csv`
- `data/fully_pooled/external/curated_long.csv`

The curated-long tables are path-scrubbed public copies; machine-specific filesystem paths were removed while retaining scientific provenance fields.

## Quick Reproduction Check

Run a fast smoke test:

```bash
bash scripts/run_quick_check.sh
```

This validates the ontology and curated-long tables, then trains the five model families on a small subset of the fully pooled arm. Outputs are written under `results/quick_check/`.

## Full Benchmark Regeneration

Run the fully pooled benchmark:

```bash
python pipeline/benchmark.py \
  --case-dir data/fully_pooled \
  --ontology config/pharmacology_ontology.json \
  --out results/fully_pooled
```

Run stratified benchmarks:

```bash
python pipeline/benchmark.py --case-dir data/stratified/balanced --ontology config/pharmacology_ontology.json --out results/balanced
python pipeline/benchmark.py --case-dir data/stratified/maximal --ontology config/pharmacology_ontology.json --out results/maximal
```

Build the pooled-vs-stratified contrast:

```bash
python pipeline/compare.py \
  --pooled results/fully_pooled/model_performance_table.csv \
  --stratified results/balanced/model_performance_table.csv results/maximal/model_performance_table.csv \
  --stratified-labels balanced maximal \
  --pooled-long-development data/fully_pooled/development/curated_long.csv \
  --out results/fully_pooled_vs_stratified_external_contrast.csv
```

The expected locked contrast table from the manuscript run is stored in `expected_outputs/` for comparison. Derived reports, dashboards, and figures are intentionally not committed.

## Citation

If you use this repository, please cite:

```text
Elokely et al. Pharmacological and assay-readout stratification of opioid-receptor bioactivity data for reproducible QSAR benchmarking. DOI: [TO BE ADDED]
```

## License

This repository is distributed for academic and non-commercial research use under CC BY-NC 4.0. See `LICENSE`.

## Reproducibility Note

This repository is a public reference implementation. It intentionally omits Slurm/HPC wrappers, internal synchronization scripts, production infrastructure, exploratory analyses, raw large result bundles, and machine-specific paths.
