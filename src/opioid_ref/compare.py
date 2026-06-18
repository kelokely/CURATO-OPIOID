from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd


def best_by_task(path: Path, arm: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    if df.empty:
        return pd.DataFrame()
    sort_cols = ["receptor", "target_id", "endpoint_scale", "R2"]
    df = df.sort_values(sort_cols, ascending=[True, True, True, False])
    best = df.groupby(["receptor", "target_id", "endpoint_scale"], as_index=False).head(1).copy()
    best["arm"] = arm
    return best


def load_pooled_counts(curated_long: Path) -> pd.DataFrame:
    cols = [
        "target_id",
        "pooled_endpoint_scale",
        "endpoint_family",
        "assay_readout",
    ]
    df = pd.read_csv(curated_long, usecols=lambda c: c in cols)
    rows = []
    for (target_id, scale), group in df.groupby(["target_id", "pooled_endpoint_scale"], dropna=False):
        if pd.isna(scale):
            continue
        rows.append(
            {
                "target_id": target_id,
                "endpoint_scale": scale,
                "n_pooled_records": len(group),
                "n_binding_endpoint_family_in_pool": int((group["endpoint_family"] == "binding").sum()),
                "n_functional_endpoint_family_in_pool": int((group["endpoint_family"] == "functional").sum()),
                "n_binding_displacement_readout_in_pool": int((group["assay_readout"] == "binding_displacement").sum()),
            }
        )
    return pd.DataFrame(rows)


def contrast(
    pooled_perf: Path,
    stratified_perf: list[Path],
    stratified_labels: list[str],
    pooled_long_development: Path,
) -> pd.DataFrame:
    pooled = best_by_task(pooled_perf, "fully_pooled")
    stratified = pd.concat(
        [best_by_task(path, label) for path, label in zip(stratified_perf, stratified_labels)],
        ignore_index=True,
    )
    stratified = stratified.sort_values(
        ["receptor", "target_id", "endpoint_scale", "R2"],
        ascending=[True, True, True, False],
    ).groupby(["receptor", "target_id", "endpoint_scale"], as_index=False).head(1)
    counts = load_pooled_counts(pooled_long_development)

    rows = []
    for _, p in pooled.iterrows():
        idx = (
            (stratified["receptor"] == p["receptor"])
            & (stratified["target_id"] == p["target_id"])
            & (stratified["endpoint_scale"] == p["endpoint_scale"])
        )
        s = stratified[idx].head(1)
        count = counts[
            (counts["target_id"] == p["target_id"]) & (counts["endpoint_scale"] == p["endpoint_scale"])
        ].head(1)
        srow = s.iloc[0] if not s.empty else None
        crow = count.iloc[0].to_dict() if not count.empty else {}
        strat_r2 = float(srow["R2"]) if srow is not None else np.nan
        rows.append(
            {
                "receptor": p["receptor"],
                "target_id": p["target_id"],
                "endpoint_scale": p["endpoint_scale"],
                "n_pooled_records": crow.get("n_pooled_records", np.nan),
                "n_external": int(p["n_external"]),
                "pooled_external_R2": float(p["R2"]),
                "pooled_model": p["model"],
                "pooled_RMSE": float(p["RMSE"]),
                "pooled_MAE": float(p["MAE"]),
                "best_stratified_external_R2": strat_r2,
                "best_stratified_arm": srow["arm"] if srow is not None else "",
                "best_stratified_stratum": srow["stratum"] if srow is not None else "",
                "best_stratified_model": srow["model"] if srow is not None else "",
                "best_stratified_n": int(srow["n_external"]) if srow is not None else np.nan,
                "delta_stratified_minus_pooled": round(strat_r2 - float(p["R2"]), 4)
                if np.isfinite(strat_r2)
                else np.nan,
                "n_binding_endpoint_family_in_pool": crow.get("n_binding_endpoint_family_in_pool", np.nan),
                "n_functional_endpoint_family_in_pool": crow.get("n_functional_endpoint_family_in_pool", np.nan),
                "n_binding_displacement_readout_in_pool": crow.get("n_binding_displacement_readout_in_pool", np.nan),
                "status": "ok",
            }
        )
    return pd.DataFrame(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description="Build fully pooled vs stratified contrast table.")
    parser.add_argument("--pooled", type=Path, required=True)
    parser.add_argument("--stratified", type=Path, nargs="+", required=True)
    parser.add_argument("--stratified-labels", nargs="+", required=True)
    parser.add_argument("--pooled-long-development", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    table = contrast(args.pooled, args.stratified, args.stratified_labels, args.pooled_long_development)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    table.to_csv(args.out, index=False)


if __name__ == "__main__":
    main()
