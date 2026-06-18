# Data

This directory contains frozen curated CSV inputs for reproducing the opioid bioactivity stratification benchmarks.

The public repository intentionally includes curated data rather than the full raw retrieval cache. Raw-source retrieval and source-specific licensing should be documented in the manuscript and SI. ChEMBL-derived data are redistributed under ChEMBL's CC BY-SA terms; BindingDB, PubChem, and IUPHAR/BPS Guide to Pharmacology (GtoPdb) data retain their respective source terms.

The fully pooled `curated_long.csv` files were sanitized before publication to remove local filesystem paths while preserving scientific provenance fields, source identifiers, endpoint annotations, trust tiers, assay-readout labels, pharmacology labels, and pooled endpoint assignments.

Do not commit regenerated result folders from `results/`; they are derived artifacts.
