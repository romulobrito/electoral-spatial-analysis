"""E016: conservative guards on online aggregate municipal turnout models.

Outcomes from unrevealed municipalities are used exclusively for retrospective
scoring. Controls are fixed engineering hypotheses, not fitted to 2026 scores.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
from collections import defaultdict
from pathlib import Path

import numpy as np

from .arrival_model_integration import extend_path as e015_extend_path
from .arrival_model_integration import load_static, online_ridge
from .arrival_selection_stress import STAGES, load_population, order_paths
from .residual_diagnostics import STATE_REGION

MIN_UFS = 8
MIN_EFFECTIVE_MUNICIPALITIES = 25.0
MAX_OUT_OF_SUPPORT_WEIGHT = 0.35
SUPPORT_PADDING_SD = 1.0
MAX_ABSOLUTE_DELTA_PP = 8.0
TRAIN_QUANTILE_PAD_PP = 2.0
MAX_MODEL_BLEND = 0.75
MODELS = ("e016_guarded_linear", "e016_guarded_quadratic")


def support_diagnostics(x: np.ndarray, seen: np.ndarray, hidden: np.ndarray,
                        weights: np.ndarray) -> tuple[np.ndarray, float]:
    """Compute train-derived covariate support without hidden-year outcomes."""
    mu = x[seen].mean(axis=0)
    std = x[seen].std(axis=0)
    if np.any(std < 1e-10):
        return np.full(len(hidden), float("inf")), 1.0
    known = (x[seen] - mu) / std
    unseen = (x[hidden] - mu) / std
    lo = np.quantile(known, .05, axis=0) - SUPPORT_PADDING_SD
    hi = np.quantile(known, .95, axis=0) + SUPPORT_PADDING_SD
    distance = np.maximum(
        0.0, np.maximum(unseen - hi, lo - unseen)
    ).max(axis=1)
    share = float(np.dot(weights[hidden], distance > 1e-12) / weights[hidden].sum())
    return distance, share


def guarded_delta(raw: np.ndarray, reference: np.ndarray,
                  observed_delta: np.ndarray, novelty: np.ndarray
                  ) -> tuple[np.ndarray, float, float]:
    """Clipped historical swing mixed with UF-smoothed reference.

    Never uses hidden-year turnout or the experiment's final national result.
    """
    lower = float(np.clip(
        np.quantile(observed_delta, .05) - TRAIN_QUANTILE_PAD_PP,
        -MAX_ABSOLUTE_DELTA_PP, MAX_ABSOLUTE_DELTA_PP,
    ))
    upper = float(np.clip(
        np.quantile(observed_delta, .95) + TRAIN_QUANTILE_PAD_PP,
        -MAX_ABSOLUTE_DELTA_PP, MAX_ABSOLUTE_DELTA_PP,
    ))
    bounded = np.clip(raw, lower, upper)
    influence = MAX_MODEL_BLEND / (1.0 + novelty**2)
    final = influence * bounded + (1 - influence) * reference
    return final, float(np.mean(abs(bounded - raw) > 1e-10)), float(np.mean(influence))


def reference_uf_delta(pop: dict, seen: np.ndarray, hidden: np.ndarray
                       ) -> np.ndarray:
    """Recompute exact E014 UF-shrunk delta, as municipal predictions (pp)."""
    weights = pop["weight"]
    historical = pop["historical"]
    observed = pop["current"]
    states = pop["group"]
    wk = weights[seen]
    changes = observed[seen] - historical[seen]
    national = float(np.dot(wk, changes) / wk.sum())
    n_groups = len(pop["groups"])
    group_count = np.bincount(states[seen], minlength=n_groups)
    group_w = np.bincount(states[seen], weights=wk, minlength=n_groups)
    group_num = np.bincount(states[seen], weights=wk * changes, minlength=n_groups)
    group_means = np.divide(
        group_num, group_w, out=np.full(n_groups, national),
        where=group_w > 0,
    )
    shrink = group_count / (group_count + 30.0)
    regional = shrink * group_means + (1.0 - shrink) * national
    return 100.0 * regional[states[hidden]]


def extend_path(pop: dict, x: np.ndarray, order: list[int],
                thresholds=STAGES) -> list[dict]:
    """Compare unchanged E014+E015 and two guarded E016 candidate methods."""
    existing = e015_extend_path(pop, x, order, thresholds)
    by_stage = defaultdict(list)
    for row in existing:
        by_stage[row["threshold_pct"]].append(row)
    result = []
    idx = np.asarray(order, dtype=int)
    weights = pop["weight"]
    h = pop["historical"]
    y = pop["current"]
    groups = pop["uf"]
    national_total = float(weights.sum())
    final = float(100 * np.dot(weights, y) / national_total)  # SCORING ONLY
    for target in thresholds:
        rows = by_stage[target * 100]
        result.extend(rows)
        baseline = {r["method"]: r for r in rows}
        stop = int(baseline["uf_shrunk_swing"]["municipalities_seen"])
        seen, hidden = idx[:stop], idx[stop:]
        observed_delta = 100.0 * (y[seen] - h[seen])
        wk = weights[seen]
        effective_n = float(wk.sum()**2 / np.dot(wk, wk))
        seen_ufs = len({str(groups[i]) for i in seen})
        if any(str(code) not in STATE_REGION for code in groups):
            raise ValueError("Invalid UF code")
        distance, outshare = support_diagnostics(x, seen, hidden, weights)
        reference = reference_uf_delta(pop, seen, hidden)
        ref_estimate = float(baseline["uf_shrunk_swing"]["estimate_turnout_pct"])
        # Numerical safeguard: reconstructed UF reference must match E014.
        reconstructed = 100 * (
            np.dot(weights[seen], y[seen])
            + np.dot(weights[hidden], np.clip(h[hidden] + reference / 100, 0, 1))
        ) / national_total
        if not math.isclose(reconstructed, ref_estimate, abs_tol=1e-8):
            raise ValueError("E014 UF reference changed unexpectedly")
        gate = "none"
        if seen_ufs < MIN_UFS:
            gate = "insufficient_geographic_coverage"
        elif effective_n < MIN_EFFECTIVE_MUNICIPALITIES:
            gate = "low_effective_sample_size"
        elif outshare > MAX_OUT_OF_SUPPORT_WEIGHT:
            gate = "covariate_extrapolation"
        for quadratic, method in ((False, MODELS[0]), (True, MODELS[1])):
            reason = gate
            bounded_fraction = 0.0
            mean_influence = 0.0
            raw_min = None
            raw_max = None
            estimate = ref_estimate
            if reason == "none":
                fit = online_ridge(x, seen, observed_delta, quadratic=quadratic)
                if fit is None:
                    reason = "singular_or_insufficient_training"
                else:
                    raw = fit[0][hidden]
                    raw_min, raw_max = float(raw.min()), float(raw.max())
                    predicted, bounded_fraction, mean_influence = guarded_delta(
                        raw, reference, observed_delta, distance
                    )
                    estimate = float(100 * (
                        np.dot(weights[seen], y[seen])
                        + np.dot(weights[hidden],
                                 np.clip(h[hidden] + predicted / 100, 0, 1))
                    ) / national_total)
            result.append({
                "threshold_pct": target * 100,
                "actual_eligible_coverage_pct": baseline["uf_shrunk_swing"]["actual_eligible_coverage_pct"],
                "municipalities_seen": stop,
                "method": method,
                "estimate_turnout_pct": estimate,
                "final_turnout_pct": final,
                "abs_error_pp": abs(estimate - final),
                "signed_error_pp": estimate - final,
                "model_fallback": reason,
                "ufs_seen": seen_ufs,
                "effective_sample_size": effective_n,
                "out_of_support_hidden_electorate_pct": 100 * outshare,
                "unweighted_clipped_prediction_fraction": bounded_fraction,
                "unweighted_mean_model_blend": mean_influence,
                "min_raw_delta_prediction_pp": raw_min,
                "max_raw_delta_prediction_pp": raw_max,
            })
    return result


def run(panel: Path, census: Path, *, reps: int = 120, seed: int = 20261026):
    pop = load_population(panel)
    x = load_static(pop, census)
    records = []
    for scenario, rep, order in order_paths(pop, reps, seed):
        for row in extend_path(pop, x, order):
            records.append({**row, "scenario": scenario, "replicate": rep})
    grouped = defaultdict(list)
    paired = defaultdict(dict)
    for row in records:
        key = (row["scenario"], row["replicate"], row["threshold_pct"])
        paired[key][row["method"]] = row
        grouped[(row["scenario"], row["threshold_pct"], row["method"])].append(row)
    summaries = []
    for (scenario, stage, method), group in sorted(grouped.items()):
        errors = sorted(float(r["abs_error_pp"]) for r in group)
        differences = [
            float(r["abs_error_pp"]) -
            float(paired[(scenario, r["replicate"], stage)]["uf_shrunk_swing"]["abs_error_pp"])
            for r in group
        ]
        summaries.append({
            "scenario": scenario, "target_coverage_pct": stage,
            "method": method, "paths": len(group),
            "mean_abs_error_pp": float(np.mean(errors)),
            "p90_abs_error_pp": errors[math.ceil(.9 * len(errors)) - 1],
            "max_abs_error_pp": errors[-1],
            "mean_difference_vs_uf_swing_pp": float(np.mean(differences)),
            "wins_vs_uf_swing": sum(d < -1e-12 for d in differences),
            "fallback_paths": sum(
                r.get("model_fallback") not in (None, "none", "not_applicable")
                for r in group
            ),
        })
    metadata = {
        "stage": "E016", "kind": "exploratory_robustness_development",
        "sample_municipalities": len(pop["code"]),
        "scenarios": 2 * reps + 5, "stages": list(STAGES),
        "number_of_methods": 10, "seed": seed, "reps": reps,
        "panel_sha256": "2b84fd89497c10a9d47f6a1a1793da144ac1be845df97605101607e424e1323d",
        "census_sha256": "145bd9448282278e3de4290bf1e26e025bc783965defb6f82c71be467439b641",
        "controls": {
            "minimum_ufs": MIN_UFS,
            "minimum_weighted_effective_sample_size": MIN_EFFECTIVE_MUNICIPALITIES,
            "maximum_hidden_electorate_out_of_covariate_support": MAX_OUT_OF_SUPPORT_WEIGHT,
            "historical_support_padding_sd": SUPPORT_PADDING_SD,
            "absolute_turnout_swing_clip_pp": MAX_ABSOLUTE_DELTA_PP,
            "observed_delta_quantile_pad_pp": TRAIN_QUANTILE_PAD_PP,
            "maximum_model_blend": MAX_MODEL_BLEND,
            "fallback": "uf_shrunk_swing",
        },
        "limitations": [
            "First-round aggregate municipal turnout, not candidate vote shares",
            "Same 2026 data as E014/E015, not prospective temporal validation",
            "Controls are exploratory engineering choices, not independently calibrated",
            "Order permutations are counterfactual, not actual TSE chronology",
            "No inferential coverage claims or individual-level electoral inference",
        ],
    }
    return metadata, summaries, records


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--panel", type=Path, required=True)
    parser.add_argument("--census", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--reps", type=int, default=120)
    parser.add_argument("--seed", type=int, default=20261026)
    args = parser.parse_args()
    if args.out_dir.exists():
        parser.error("Do not overwrite previous experiments")
    metadata, summary, records = run(
        args.panel, args.census, reps=args.reps, seed=args.seed
    )
    args.out_dir.mkdir(parents=True)
    (args.out_dir / "metadata.json").write_text(
        json.dumps(metadata, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    for filename, rows in (
        ("scenario_summary.csv", summary), ("path_errors.csv", records),
    ):
        columns = list(dict.fromkeys(k for row in rows for k in row))
        with (args.out_dir / filename).open(
            "w", encoding="utf-8", newline=""
        ) as f:
            writer = csv.DictWriter(f, fieldnames=columns)
            writer.writeheader()
            writer.writerows(rows)
    print(json.dumps({
        "stage": "E016", "paths": 2 * args.reps + 5,
        "records": len(records), "methods": 10,
    }))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
