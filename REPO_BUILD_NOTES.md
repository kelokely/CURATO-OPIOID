# Repository Build Notes

## Current Status

This folder is a local draft of the public GitHub repository. It has not been pushed to GitHub.

Completed:

- Clean repository structure created.
- Versioned ontology copied to `config/pharmacology_ontology.json`.
- Curated-wide matrices copied for `low_resolution`, `mid_resolution`, `high_resolution`, and `fully_pooled`.
- Fully pooled curated-long tables copied and sanitized to remove machine-specific filesystem paths.
- Expected locked pooled-vs-stratified contrast table copied to `expected_outputs/`.
- Reference benchmark, ontology validation, and contrast-table scripts added.
- Production Slurm/HPC wrappers and large derived result folders excluded.

Remaining before public release:

- Run the quick check in a clean virtual environment.
- Run the full regeneration check and compare `results/fully_pooled_vs_stratified_external_contrast.csv` against `expected_outputs/fully_pooled_vs_stratified_external_contrast.csv`.
- Decide whether the public reference implementation must numerically match the production benchmark exactly or whether the production benchmark outputs remain the locked expected reference and this repo is a readable reproduction path.
- Confirm the final repository name, GitHub owner, visibility, and license text.
- Add the final manuscript DOI when available.

## Important Claim Boundary

The public architecture is ontology-driven: the engine loads `config/pharmacology_ontology.json` and records its version/hash. The shipped ontology is demonstrated and extensible for the opioid study; it should not be described as universal for every possible target or assay type.
