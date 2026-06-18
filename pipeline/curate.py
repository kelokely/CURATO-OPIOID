#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from opioid_ref.ontology import load_ontology


REQUIRED_LONG_COLUMNS = {
    "target_id",
    "endpoint",
    "pActivity",
    "relation",
    "endpoint_family",
    "assay_readout",
    "pharmacology_class",
    "pharmacology_stratum",
    "row_trust_tier",
}

INTERNAL_PATH_RE = re.compile(r"(?:/Users/|/project/|/gscratch/|/cluster/|/Volumes/)")


def validate_long(path: Path) -> dict:
    df = pd.read_csv(path, low_memory=False)
    missing = sorted(REQUIRED_LONG_COLUMNS.difference(df.columns))
    if missing:
        raise ValueError(f"{path} is missing required column(s): {', '.join(missing)}")
    path_hits = 0
    for col in df.select_dtypes(include=["object", "str"]).columns:
        path_hits += int(df[col].astype(str).str.contains(INTERNAL_PATH_RE, regex=True, na=False).sum())
    if path_hits:
        raise ValueError(f"{path} still contains {path_hits} internal path-like values")
    return {
        "path": str(path),
        "rows": int(len(df)),
        "compounds": int(df["inchikey"].nunique()) if "inchikey" in df.columns else None,
        "targets": sorted(map(str, df["target_id"].dropna().unique())),
        "row_trust_tiers": sorted(map(str, df["row_trust_tier"].dropna().unique())),
        "endpoint_families": sorted(map(str, df["endpoint_family"].dropna().unique())),
        "assay_readouts": sorted(map(str, df["assay_readout"].dropna().unique())),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate frozen curated inputs and ontology provenance.")
    parser.add_argument("--ontology", type=Path, default=Path("config/pharmacology_ontology.json"))
    parser.add_argument("--curated-long", type=Path, nargs="+", required=True)
    parser.add_argument("--out", type=Path, default=Path("results/curation_validation_summary.json"))
    args = parser.parse_args()

    ontology = load_ontology(args.ontology)
    summary = {
        "ontology_version": ontology["_meta"]["version"],
        "ontology_sha256": ontology["_sha256"],
        "curated_long": [validate_long(path) for path in args.curated_long],
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {args.out}")


if __name__ == "__main__":
    main()
