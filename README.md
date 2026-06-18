# CURATO-OPIOID

Pharmacology- and assay-readout-aware curation and QSAR benchmarking of public opioid-receptor bioactivity data

CURATO-OPIOID is a reference implementation of a curation and benchmarking framework that treats pharmacological mechanism and assay readout as primary axes of dataset definition, applied before any model is trained. It is the opioid-receptor instantiation of the CURATO approach to bioactivity-data curation.

## The Problem It Addresses

Public bioactivity databases are heterogeneous in ways that standardization of structures and units does not resolve. The same compound and target can carry agonist, antagonist, and inhibitor records, measured through binding displacement, cAMP, β-arrestin recruitment, or [³⁵S]GTPγS assays — readouts that quantify different biological events. A model trained on these records pooled together still emits predictions, but those predictions correspond to no single, well-defined quantity: the same agonist can be potent in one functional readout and markedly weaker in another, by biology rather than noise. The resulting QSAR claim is therefore unverifiable, because there is no coherent activity the pooled endpoint measures.

CURATO-OPIOID resolves this by making pharmacology class and assay readout explicit, auditable components of the dataset contract, so that each modeled endpoint corresponds to a defined receptor, activity scale, mechanism, and assay format — and so that the claim a model supports is testable.

## What It Does

Applied to the four opioid receptors (μ, δ, κ, and nociceptin/orphanin FQ; MOR, DOR, KOR, NOP), the framework:

- Reconciles multi-source public records into evidence groups that preserve source agreement and conflict, rather than concatenating overlapping data as if it were independent.
- Standardizes chemical identity deterministically, so that scaffold assignment, deduplication, and descriptor generation rest on stable structures.
- Assigns each record an endpoint family, pharmacology class, and assay readout, and reroutes binding-displacement records filed under functional labels so that affinity measurements are not modeled as functional potency.
- Stratifies functional endpoints by mechanism and readout before modeling, producing biologically coherent QSAR tasks in place of one ambiguous "functional activity" label.
- Benchmarks each endpoint under scaffold-locked external validation across five model families, with bootstrap confidence intervals, distribution-shift diagnostics, and SHAP attribution.
- Contrasts the stratified endpoints against a fully pooled baseline, demonstrating that pooled functional models attain apparently strong performance by predicting binding affinity for the majority of their records — that is, by answering a different question than their label claims.

## Why It Is Built This Way

The central premise is that the validity of a QSAR claim is determined first by how the dataset is defined, not by model architecture. CURATO-OPIOID is therefore organized around the dataset contract: endpoint meaning, evidence quality, and validation context are fixed before training, and the modeling step is downstream of, and constrained by, the curation logic.

The pharmacological knowledge that drives stratification is supplied as a separate, versioned ontology file rather than embedded in code. This makes the curation logic inspectable, makes the stratification reproducible against a pinned ontology version, and means the same framework extends to other target classes by describing their assays and mechanisms rather than by rewriting the pipeline. The general form of this approach is CURATO; this repository is its opioid demonstration.

## What This Repository Provides

A self-contained scientific reference path that reproduces the study's results from frozen curated inputs: the curated bioactivity datasets, the versioned pharmacology/assay-readout ontology, model training and scaffold-locked external validation, and the pooled-versus-stratified contrast. It is a reference implementation intended for reproduction and reuse, not a production system.

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
