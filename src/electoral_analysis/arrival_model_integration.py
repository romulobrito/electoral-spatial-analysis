"""E015 online aggregate turnout models under counterfactual municipal arrival.

E007/E013 model families are refit using revealed 2026 municipal turnout only.
Not an election-night replay, candidate forecast or political targeting model.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from collections import defaultdict
from pathlib import Path

import numpy as np

from .arrival_selection_stress import (
    STAGES,
    evaluate_path,
    load_population,
    order_paths,
)
from .ibge_turnout import validate_ibge_response
from .residual_diagnostics import IBGE_SHA, REGIONAL_SHRINKAGE, STATE_REGION

ALPHA = 10.0
MIN_TRAIN = 10
NEW_METHODS = (
    "e007_ridge_online", "e007_ridge_macro_online",
    "e013_quadratic_online", "e013_quadratic_macro_online",
)


def load_static(pop: dict, census_path: Path) -> np.ndarray:
    """Join audited 2022 IBGE features to the exact E014 municipality order."""
    raw = census_path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != IBGE_SHA:
        raise ValueError("E006 official Census 2022 SHA256 mismatch")
    census = validate_ibge_response(json.loads(raw))
    codes = list(map(str, pop["code"]))
    if len(set(codes)) != len(codes):
        raise ValueError("Duplicate municipality IDs")
    values = []
    for code, historical in zip(codes, pop["historical"]):
        row = census.get(code)
        if row is None or row["population"] is None or row["density_km2"] is None:
            raise ValueError(f"Missing historical covariates for {code}")
        if row["population"] < 0 or row["density_km2"] < 0:
            raise ValueError("Invalid historical covariate")
        values.append((
            historical, math.log1p(row["population"]),
            math.log1p(row["density_km2"]),
        ))
    x = np.asarray(values, dtype=float)
    if x.shape != (len(codes), 3) or not np.isfinite(x).all():
        raise ValueError("Invalid historical feature matrix")
    return x


def online_ridge(x: np.ndarray, seen: np.ndarray, delta_pp: np.ndarray,
                 *, quadratic: bool) -> tuple[np.ndarray, np.ndarray] | None:
    """Train-only standardization, fixed alpha 10, optional E013 square terms."""
    if len(seen) < MIN_TRAIN:
        return None
    a, y = x[seen], delta_pp
    mu, sd = a.mean(axis=0), a.std(axis=0)
    if np.any(sd < 1e-10):
        return None
    z = (x - mu) / sd
    if quadratic:
        z = np.column_stack((z, z * z))
    mu2, sd2 = z[seen].mean(axis=0), z[seen].std(axis=0)
    if np.any(sd2 < 1e-10):
        return None
    z = (z - mu2) / sd2
    train = z[seen]
    intercept = float(y.mean())
    slopes = np.linalg.solve(
        train.T @ train + ALPHA * np.eye(z.shape[1]),
        train.T @ (y - intercept),
    )
    predicted = intercept + z @ slopes
    if not np.isfinite(predicted).all():
        raise ValueError("Nonfinite ridge predictions")
    return predicted, y - predicted[seen]


def extend_path(pop: dict, x: np.ndarray, order: list[int],
                thresholds=STAGES) -> list[dict]:
    """Augment unchanged E014 estimates; hidden current turnout used for scoring."""
    w, h, y, uf = (pop[k] for k in ("weight", "historical", "current", "uf"))
    n = len(w)
    if x.shape != (n, 3) or not np.isfinite(x).all():
        raise ValueError("Covariate matrix must be finite and Nx3")
    if len(uf) != n or any(str(state) not in STATE_REGION for state in uf):
        raise ValueError("Missing UF-to-macrorregion mapping")
    original = evaluate_path(pop, order, thresholds)
    grouped = defaultdict(list)
    for record in original:
        grouped[record["threshold_pct"]].append(record)
    idx = np.asarray(order, dtype=int)
    total = w.sum()
    records = []
    for threshold in thresholds:
        stage = grouped[threshold * 100]
        old = {row["method"]: row for row in stage}
        stop = old["national_swing"]["municipalities_seen"]
        seen, hidden = idx[:stop], idx[stop:]
        current_delta = 100 * (y[seen] - h[seen])
        available = np.dot(w[seen], y[seen])
        national = old["national_swing"]["estimate_turnout_pct"]
        for item in stage:
            records.append({**item, "model_fallback": "not_applicable"})
        estimates = {}
        for quadratic, base, regional in (
            (False, NEW_METHODS[0], NEW_METHODS[1]),
            (True, NEW_METHODS[2], NEW_METHODS[3]),
        ):
            fitted = online_ridge(x, seen, current_delta, quadratic=quadratic)
            if fitted is None:
                reason = "national_swing_insufficient_training"
                estimates[base] = (national, reason)
                estimates[regional] = (national, reason)
                continue
            prediction, residual = fitted
            regional_sums = defaultdict(float)
            regional_counts = defaultdict(int)
            for i, error in zip(seen, residual):
                region = STATE_REGION[str(uf[i])]
                regional_sums[region] += float(error)
                regional_counts[region] += 1
            adjusted = np.array([
                regional_sums[STATE_REGION[str(state)]] /
                (regional_counts[STATE_REGION[str(state)]] + REGIONAL_SHRINKAGE)
                for state in uf[hidden]
            ], dtype=float)
            for method, correction in ((base, 0.0), (regional, adjusted)):
                hidden_turnout = np.clip(
                    h[hidden] + (prediction[hidden] + correction) / 100,
                    0, 1,
                )
                estimate = 100 * (
                    available + np.dot(w[hidden], hidden_turnout)
                ) / total
                estimates[method] = (float(estimate), "none")
        truth = old["national_swing"]["final_turnout_pct"]
        for method, (estimate, fallback) in estimates.items():
            records.append({
                "threshold_pct": threshold * 100,
                "actual_eligible_coverage_pct": old["national_swing"]["actual_eligible_coverage_pct"],
                "municipalities_seen": stop, "method": method,
                "estimate_turnout_pct": estimate, "final_turnout_pct": truth,
                "abs_error_pp": abs(estimate - truth),
                "signed_error_pp": estimate - truth,
                "model_fallback": fallback,
            })
    return records


def run(panel: Path, census: Path, *, reps: int = 120, seed: int = 20261026):
    pop = load_population(panel)
    x = load_static(pop, census)
    records = []
    for scenario, replicate, ordering in order_paths(pop, reps, seed):
        for row in extend_path(pop, x, ordering):
            records.append({**row, "scenario": scenario, "replicate": replicate})
    grouped = defaultdict(list)
    paired = defaultdict(dict)
    for row in records:
        grouped[(row["scenario"], row["threshold_pct"], row["method"])].append(row)
        paired[(row["scenario"], row["replicate"], row["threshold_pct"])][row["method"]] = row
    summaries = []
    for (scenario, target, method), rows in sorted(grouped.items()):
        errors = sorted(r["abs_error_pp"] for r in rows)
        deltas = [
            r["abs_error_pp"] -
            paired[(scenario, r["replicate"], target)]["historical_2022"]["abs_error_pp"]
            for r in rows
        ]
        summaries.append({
            "scenario": scenario, "target_coverage_pct": target,
            "method": method, "paths": len(rows),
            "mean_abs_error_pp": float(np.mean(errors)),
            "p90_abs_error_pp": errors[math.ceil(.9 * len(errors)) - 1],
            "max_abs_error_pp": errors[-1],
            "mean_difference_vs_historical_pp": float(np.mean(deltas)),
            "fallback_paths": sum(
                r["model_fallback"] not in ("none", "not_applicable")
                for r in rows
            ),
        })
    metadata = {
        "stage": "E015",
        "scope": "First-round aggregate turnout only; no candidate outcomes",
        "sample_municipalities": len(pop["code"]), "repetitions": reps,
        "seed": seed, "stages": list(STAGES),
        "paths": 2 * reps + 5,
        "panel_sha256": "2b84fd89497c10a9d47f6a1a1793da144ac1be845df97605101607e424e1323d",
        "census_sha256": IBGE_SHA,
        "model_family": "E007 linear ridge and E013 quadratic ridge, fitted sequentially",
        "ridge_alpha": ALPHA, "regional_shrinkage": REGIONAL_SHRINKAGE,
        "minimum_training_municipalities": MIN_TRAIN,
        "fallback": "E014 national swing if too few or degenerate training examples",
        "validation": "Observed current-year turnout for revealed municipalities only",
        "denominator": "2026 eligible electors in REVEALED municipalities, NOT reported sections",
        "limitations": [
            "Municipality arrival order is simulated, not the true TSE reporting order",
            "E007/E013 families reused, not their original fitted coefficients",
            "Same 2026 election in every permutation; not independent elections",
            "No genuine independent future-election temporal holdout",
            "No calibrated predictive intervals and no candidate-preference predictions",
        ],
    }
    return metadata, summaries, records


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--panel", type=Path, required=True)
    p.add_argument("--census", type=Path, required=True)
    p.add_argument("--out-dir", type=Path, required=True)
    p.add_argument("--reps", type=int, default=120)
    p.add_argument("--seed", type=int, default=20261026)
    args = p.parse_args()
    if args.out_dir.exists():
        p.error("Do not overwrite existing experiment directory")
    metadata, summaries, records = run(
        args.panel, args.census, reps=args.reps, seed=args.seed
    )
    args.out_dir.mkdir(parents=True)
    (args.out_dir / "metadata.json").write_text(
        json.dumps(metadata, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    for filename, rows in (
        ("scenario_summary.csv", summaries), ("path_errors.csv", records),
    ):
        with (args.out_dir / filename).open(
            "w", encoding="utf-8", newline=""
        ) as f:
            writer = csv.DictWriter(f, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
    print(json.dumps({
        "stage": "E015", "paths": 2 * args.reps + 5,
        "records": len(records), "methods": 8,
    }))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
