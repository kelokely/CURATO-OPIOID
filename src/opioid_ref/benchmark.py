from __future__ import annotations

import argparse
import json
import math
import re
import warnings
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd
from rdkit import Chem, DataStructs
from rdkit.Chem import Descriptors
from rdkit.Chem.rdFingerprintGenerator import GetMorganGenerator
from sklearn.ensemble import RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVR

from .ontology import load_ontology


TARGET_LABELS = {
    "CHEMBL233": "MOR",
    "CHEMBL236": "DOR",
    "CHEMBL237": "KOR",
    "CHEMBL2014": "NOP",
}

ENDPOINT_RE = re.compile(r"^p(?P<scale>IC50_func|EC50|AC50|Ki|Kd|IC50)_(?P<target>CHEMBL\d+)(?:_(?P<stratum>.+))?$")
MORGAN = GetMorganGenerator(radius=2, fpSize=2048)


@dataclass(frozen=True)
class Endpoint:
    column: str
    endpoint_scale: str
    target_id: str
    stratum: str

    @property
    def receptor(self) -> str:
        return TARGET_LABELS.get(self.target_id, self.target_id)


def endpoint_columns(df: pd.DataFrame) -> list[Endpoint]:
    endpoints: list[Endpoint] = []
    for col in df.columns:
        match = ENDPOINT_RE.match(col)
        if not match:
            continue
        if col.endswith("_relation"):
            continue
        target = match.group("target")
        if target not in TARGET_LABELS:
            continue
        endpoints.append(
            Endpoint(
                column=col,
                endpoint_scale=match.group("scale"),
                target_id=target,
                stratum=match.group("stratum") or "pooled",
            )
        )
    return endpoints


def descriptor_names() -> list[str]:
    return [name for name, _ in Descriptors._descList]


def molecule_from_smiles(smiles: object) -> Chem.Mol | None:
    if not isinstance(smiles, str) or not smiles.strip():
        return None
    return Chem.MolFromSmiles(smiles)


def featurize(smiles: Iterable[object]) -> tuple[np.ndarray, list[str], np.ndarray]:
    desc = Descriptors._descList
    names = [name for name, _ in desc] + [f"morgan_{i}" for i in range(2048)]
    rows: list[np.ndarray] = []
    ok: list[bool] = []
    for smi in smiles:
        mol = molecule_from_smiles(smi)
        if mol is None:
            rows.append(np.full(len(names), np.nan, dtype=float))
            ok.append(False)
            continue
        values = []
        for _, fn in desc:
            try:
                val = float(fn(mol))
            except Exception:
                val = np.nan
            values.append(val)
        fp = MORGAN.GetFingerprint(mol)
        arr = np.zeros((2048,), dtype=np.int8)
        DataStructs.ConvertToNumpyArray(fp, arr)
        rows.append(np.concatenate([np.asarray(values, dtype=float), arr.astype(float)]))
        ok.append(True)
    X = np.vstack(rows)
    finite = np.isfinite(X)
    enough = finite.sum(axis=0) > 0
    X = X[:, enough]
    kept_names = [name for name, keep in zip(names, enough) if keep]
    return X, kept_names, np.asarray(ok, dtype=bool)


def build_model(name: str, seed: int) -> object:
    if name == "RF":
        return RandomForestRegressor(n_estimators=300, min_samples_leaf=2, n_jobs=-1, random_state=seed)
    if name == "XGB":
        from xgboost import XGBRegressor

        return XGBRegressor(
            n_estimators=300,
            max_depth=6,
            learning_rate=0.1,
            subsample=0.8,
            colsample_bytree=0.8,
            n_jobs=-1,
            random_state=seed,
            verbosity=0,
        )
    if name == "LGBM":
        from lightgbm import LGBMRegressor

        return LGBMRegressor(
            n_estimators=300,
            max_depth=-1,
            learning_rate=0.1,
            n_jobs=-1,
            random_state=seed,
            verbose=-1,
        )
    if name == "SVR":
        return SVR(kernel="rbf", C=10.0, epsilon=0.1, gamma="scale")
    raise ValueError(f"Unknown model: {name}")


def model_pipeline(name: str, seed: int) -> Pipeline:
    return Pipeline(
        [
            ("impute", SimpleImputer(strategy="median")),
            ("scale", StandardScaler()),
            ("model", build_model(name, seed)),
        ]
    )


def metrics(y_true: np.ndarray, y_pred: np.ndarray) -> dict[str, float]:
    return {
        "R2": round(float(r2_score(y_true, y_pred)), 4),
        "RMSE": round(float(math.sqrt(mean_squared_error(y_true, y_pred))), 4),
        "MAE": round(float(mean_absolute_error(y_true, y_pred)), 4),
    }


def quick_subset(df: pd.DataFrame, endpoint: Endpoint, max_rows: int, seed: int) -> pd.DataFrame:
    observed = df[df[endpoint.column].notna()]
    if len(observed) <= max_rows:
        return df
    sampled = observed.sample(n=max_rows, random_state=seed)
    keep = set(sampled.index)
    return df.loc[df.index.isin(keep) | df[endpoint.column].isna()].copy()


def train_endpoint(
    endpoint: Endpoint,
    dev: pd.DataFrame,
    external: pd.DataFrame,
    X_dev: np.ndarray,
    X_ext: np.ndarray,
    valid_dev: np.ndarray,
    valid_ext: np.ndarray,
    models: list[str],
    seed: int,
) -> tuple[list[dict], list[dict]]:
    train_mask = dev[endpoint.column].notna().to_numpy() & valid_dev
    test_mask = external[endpoint.column].notna().to_numpy() & valid_ext
    if train_mask.sum() < 20 or test_mask.sum() < 10:
        return [], []

    y_train = dev.loc[train_mask, endpoint.column].astype(float).to_numpy()
    y_test = external.loc[test_mask, endpoint.column].astype(float).to_numpy()
    X_train = X_dev[train_mask]
    X_test = X_ext[test_mask]

    predictions: dict[str, np.ndarray] = {}
    rows: list[dict] = []
    pred_rows: list[dict] = []
    for model_name in models:
        if model_name == "Consensus":
            continue
        pipe = model_pipeline(model_name, seed)
        pipe.fit(X_train, y_train)
        with warnings.catch_warnings():
            warnings.filterwarnings(
                "ignore",
                message="X does not have valid feature names, but LGBMRegressor was fitted with feature names",
                category=UserWarning,
            )
            pred = pipe.predict(X_test)
        predictions[model_name] = pred
        m = metrics(y_test, pred)
        rows.append(result_row(endpoint, model_name, len(y_train), len(y_test), m))
        pred_rows.extend(prediction_rows(endpoint, model_name, external.loc[test_mask], y_test, pred))

    if "Consensus" in models and predictions:
        stacked = np.vstack([predictions[name] for name in ["RF", "XGB", "SVR"] if name in predictions])
        if stacked.size:
            pred = stacked.mean(axis=0)
            m = metrics(y_test, pred)
            rows.append(result_row(endpoint, "Consensus", len(y_train), len(y_test), m))
            pred_rows.extend(prediction_rows(endpoint, "Consensus", external.loc[test_mask], y_test, pred))
    return rows, pred_rows


def result_row(endpoint: Endpoint, model: str, n_train: int, n_external: int, m: dict[str, float]) -> dict:
    return {
        "receptor": endpoint.receptor,
        "target_id": endpoint.target_id,
        "endpoint_scale": endpoint.endpoint_scale,
        "stratum": endpoint.stratum,
        "endpoint_column": endpoint.column,
        "model": model,
        "n_train": n_train,
        "n_external": n_external,
        **m,
    }


def prediction_rows(endpoint: Endpoint, model: str, rows: pd.DataFrame, y_true: np.ndarray, y_pred: np.ndarray) -> list[dict]:
    out = []
    for (_, row), actual, pred in zip(rows.iterrows(), y_true, y_pred):
        out.append(
            {
                "receptor": endpoint.receptor,
                "target_id": endpoint.target_id,
                "endpoint_scale": endpoint.endpoint_scale,
                "stratum": endpoint.stratum,
                "model": model,
                "compound_id": row.get("compound_id", ""),
                "inchikey": row.get("inchikey", ""),
                "std_smiles": row.get("std_smiles", ""),
                "y_true": round(float(actual), 6),
                "y_pred": round(float(pred), 6),
            }
        )
    return out


def run_case(
    case_dir: Path,
    output_dir: Path,
    ontology_path: Path,
    models: list[str],
    seed: int,
    quick: bool,
    quick_rows: int,
) -> None:
    ontology = load_ontology(ontology_path)
    dev = pd.read_csv(case_dir / "development" / "curated_wide.csv")
    external = pd.read_csv(case_dir / "external" / "curated_wide.csv")
    endpoints = endpoint_columns(dev)
    if quick:
        endpoints = endpoints[: min(3, len(endpoints))]
        for endpoint in endpoints:
            dev = quick_subset(dev, endpoint, quick_rows, seed)
            external = quick_subset(external, endpoint, max(20, quick_rows // 4), seed)

    smiles_col = "std_smiles" if "std_smiles" in dev.columns else "smiles"
    X_dev, feature_names, valid_dev = featurize(dev[smiles_col])
    X_ext, _, valid_ext = featurize(external[smiles_col])

    results: list[dict] = []
    predictions: list[dict] = []
    for endpoint in endpoints:
        rows, pred_rows = train_endpoint(
            endpoint, dev, external, X_dev, X_ext, valid_dev, valid_ext, models, seed
        )
        results.extend(rows)
        predictions.extend(pred_rows)

    output_dir.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(results).to_csv(output_dir / "model_performance_table.csv", index=False)
    pd.DataFrame(predictions).to_csv(output_dir / "external_predictions.csv", index=False)
    provenance = {
        "seed": seed,
        "models": models,
        "quick": quick,
        "feature_count": len(feature_names),
        "ontology_version": ontology["_meta"]["version"],
        "ontology_sha256": ontology["_sha256"],
        "case_dir": str(case_dir),
    }
    (output_dir / "provenance.json").write_text(json.dumps(provenance, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run opioid reference QSAR benchmarks from curated CSVs.")
    parser.add_argument("--case-dir", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--ontology", type=Path, default=Path("config/pharmacology_ontology.json"))
    parser.add_argument("--models", default="RF,XGB,LGBM,SVR,Consensus")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--quick", action="store_true")
    parser.add_argument("--quick-rows", type=int, default=400)
    args = parser.parse_args()
    models = [m.strip() for m in args.models.split(",") if m.strip()]
    run_case(args.case_dir, args.out, args.ontology, models, args.seed, args.quick, args.quick_rows)


if __name__ == "__main__":
    main()
