from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


REQUIRED_SECTIONS = {
    "_meta",
    "target_class_patterns",
    "readout_rules",
    "effect_direction_rules",
    "assay_semantics_rules",
    "pharmacology_rules",
}


def load_ontology(path: str | Path) -> dict[str, Any]:
    ontology_path = Path(path)
    ontology = json.loads(ontology_path.read_text(encoding="utf-8"))
    missing = sorted(REQUIRED_SECTIONS.difference(ontology))
    if missing:
        raise ValueError(f"Ontology is missing required section(s): {', '.join(missing)}")
    meta = ontology.get("_meta") or {}
    if not meta.get("version"):
        raise ValueError("Ontology _meta.version is required for provenance")
    ontology["_sha256"] = sha256_file(ontology_path)
    return ontology


def sha256_file(path: str | Path) -> str:
    h = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()
