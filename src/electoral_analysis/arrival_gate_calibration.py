"""E017: guarded turnout-model gate ablation with separate reveal-path folds.

All 2026 partial-election targets used for online fitting come exclusively from
revealed municipalities. No candidate-specific prediction or voter targeting.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
from collections import defaultdict
from pathlib import Path

import numpy as np

from .arrival_model_integration import load_static, online_ridge
from .arrival_robustness import (
    MAX_ABSOLUTE_DELTA_PP,
    TRAIN_QUANTILE_PAD_PP,
    extend_path as e016_extend_path,
    reference_uf_delta,
    support_diagnostics,
)
from .arrival_selection_stress import STAGES, load_population, order_paths

# Fixed policy grid; the development split chooses among these and the UF
# reference. Evaluation-split errors never affect the policy selection.
POLICIES = {
    "moderate": {"min_ufs": 6, "min_ess": 15.0, "max_oos": .60, "blend": .50},
    "permissive": {"min_ufs": 4, "min_ess": 10.0, "max_oos": .85, "blend": .35},
}
NEW_METHODS = tuple(
    f"e017_{name}_{family}"
    for name in POLICIES for family in ("linear", "quadratic")
)
CANDIDATES = (
    "uf_shrunk_swing",
    "e016_guarded_linear",
    "e016_guarded_quadratic",
    *NEW_METHODS,
)
EARLY_STAGES = (0.25, 1.0, 2.5, 5.0, 10.0)


def fold(scenario: str, replicate: int, reps: int) -> str:
    if scenario in ("uniform_municipality_random", "balanced_uf_random"):
        return "development" if replicate < reps // 2 else "evaluation"
    return "adversarial_descriptive"


def bounded_mixture(raw: np.ndarray, prior: np.ndarray,
                    observed_delta: np.ndarray, novelty: np.ndarray,
                    blend: float) -> tuple[np.ndarray, float]:
    """Same E016 train-only swing clipping; changed mixture strength only."""
    lo = float(np.clip(
        np.quantile(observed_delta, .05) - TRAIN_QUANTILE_PAD_PP,
        -MAX_ABSOLUTE_DELTA_PP, MAX_ABSOLUTE_DELTA_PP,
    ))
    hi = float(np.clip(
        np.quantile(observed_delta, .95) + TRAIN_QUANTILE_PAD_PP,
        -MAX_ABSOLUTE_DELTA_PP, MAX_ABSOLUTE_DELTA_PP,
    ))
    bounded = np.clip(raw, lo, hi)
    influence = blend / (1.0 + novelty**2)
    return influence * bounded + (1.0 - influence) * prior, float(np.mean(influence))


def extend_path(pop: dict, x: np.ndarray, order: list[int],
                thresholds=STAGES) -> list[dict]:
    """E014–E016 unchanged; four additional safety configurations."""
    previous = e016_extend_path(pop, x, order, thresholds)
    grouped = defaultdict(list)
    for row in previous:
        grouped[row["threshold_pct"]].append(row)
    idx = np.asarray(order, dtype=int)
    w, hist, actual = (
        pop["weight"], pop["historical"], pop["current"]
    )
    true_turnout = 100 * np.dot(w, actual) / w.sum()  # SCORING ONLY
    result = list(previous)
    for target in thresholds:
        baseline = {row["method"]: row for row in grouped[target * 100]}
        anchor = baseline["uf_shrunk_swing"]
        stop = int(anchor["municipalities_seen"])
        revealed, unseen = idx[:stop], idx[stop:]
        observed_delta = 100 * (actual[revealed] - hist[revealed])
        weights_seen = w[revealed]
        ess = float(weights_seen.sum()**2 / np.dot(weights_seen, weights_seen))
        ufs_seen = len(set(pop["uf"][revealed]))
        novelty, share = support_diagnostics(x, revealed, unseen, w)
        prior_delta = reference_uf_delta(pop, revealed, unseen)
        fits = {}
        for policy_name, cfg in POLICIES.items():
            if len(unseen) == 0:
                gate = "all_revealed"
            elif ufs_seen < cfg["min_ufs"]:
                gate = "uf_count"
            elif ess < cfg["min_ess"]:
                gate = "effective_n"
            elif share > cfg["max_oos"]:
                gate = "out_of_support"
            else:
                gate = "none"
            for quadratic, suffix in ((False, "linear"), (True, "quadratic")):
                method = f"e017_{policy_name}_{suffix}"
                reason = gate
                estimate = float(anchor["estimate_turnout_pct"])
                blend_weight = 0.0
                if reason == "none":
                    if quadratic not in fits:
                        fits[quadratic] = online_ridge(
                            x, revealed, observed_delta, quadratic=quadratic
                        )
                    trained = fits[quadratic]
                    if trained is None:
                        reason = "ridge_unavailable"
                    else:
                        estimate_delta, blend_weight = bounded_mixture(
                            trained[0][unseen], prior_delta,
                            observed_delta, novelty, cfg["blend"]
                        )
                        estimate = float(100 * (
                            np.dot(w[revealed], actual[revealed])
                            + np.dot(
                                w[unseen],
                                np.clip(hist[unseen] + estimate_delta / 100, 0, 1),
                            )
                        ) / w.sum())
                result.append({
                    "threshold_pct": target * 100,
                    "actual_eligible_coverage_pct": anchor["actual_eligible_coverage_pct"],
                    "municipalities_seen": stop,
                    "method": method,
                    "estimate_turnout_pct": estimate,
                    "final_turnout_pct": float(true_turnout),
                    "abs_error_pp": abs(estimate - true_turnout),
                    "signed_error_pp": estimate - true_turnout,
                    "model_fallback": reason,
                    "ufs_seen": ufs_seen,
                    "effective_sample_size": ess,
                    "out_of_support_hidden_electorate_pct": 100 * share,
                    "unweighted_mean_model_blend": blend_weight,
                })
    return result


def select_policy(rows: list[dict], reps: int) -> dict:
    """Select once using development arrival paths, before heldout summary."""
    available = [r for r in rows
                 if r["phase"] == "development"
                 and r["threshold_pct"] in EARLY_STAGES
                 and r["method"] in CANDIDATES]
    methods = defaultdict(list)
    for row in available:
        methods[row["method"]].append(float(row["abs_error_pp"]))
    if set(methods) != set(CANDIDATES):
        raise ValueError("Missing predeclared candidates in development set")
    n_expected = 2 * (reps // 2) * len(EARLY_STAGES)
    if any(len(values) != n_expected for values in methods.values()):
        raise ValueError("Development path count is not balanced")
    baseline_max = max(methods["uf_shrunk_swing"])
    scores = []
    for method in CANDIDATES:
        a = np.asarray(methods[method], dtype=float)
        max_excess = max(0.0, float(a.max() - baseline_max - 1.0))
        score = float(a.mean() + .25 * np.quantile(a, .95) + .5 * max_excess)
        scores.append({
            "method": method,
            "score": score, "dev_mae_pp": float(a.mean()),
            "dev_p95_pp": float(np.quantile(a, .95)),
            "dev_max_pp": float(a.max()),
            "excess_max_penalty_pp": max_excess,
        })
    scores.sort(key=lambda r: (r["score"], r["method"]))
    return {
        "selected": scores[0]["method"],
        "selection_scope": "120 development paths: 60 uniform + 60 UF-balanced, first 5 stages",
        "formula": "development MAE + 0.25*p95_abs_error + 0.5*max(0, max_error - baseline_max - 1pp)",
        "score_table": scores,
        "evaluation_paths_not_used_for_selection": 120,
    }


def run(panel: Path, census: Path, *, reps: int = 120, seed: int = 20261026):
    if reps < 4 or reps % 2:
        raise ValueError("Need even reps >= 4 for disjoint path split")
    pop = load_population(panel)
    x = load_static(pop, census)
    records = []
    for scenario, rep, ordering in order_paths(pop, reps, seed):
        phase = fold(scenario, rep, reps)
        for row in extend_path(pop, x, ordering):
            records.append({
                **row, "scenario": scenario, "replicate": rep, "phase": phase,
            })
    chosen = select_policy(records, reps)
    group = defaultdict(list)
    for row in records:
        group[(row["phase"], row["scenario"], row["threshold_pct"], row["method"])].append(row)
    summaries = []
    for (phase, scenario, stage, method), matches in sorted(group.items()):
        a = np.asarray([v["abs_error_pp"] for v in matches])
        summaries.append({
            "phase": phase, "scenario": scenario,
            "threshold_pct": stage, "method": method, "paths": len(matches),
            "mean_abs_error_pp": float(a.mean()),
            "p90_abs_error_pp": float(np.quantile(a, .9)),
            "max_abs_error_pp": float(a.max()),
            "fallback_fraction": float(np.mean([
                v.get("model_fallback") not in ("none", "not_applicable", None)
                for v in matches
            ])),
        })
    metadata = {
        "stage": "E017", "seed": seed, "paths": 2 * reps + 5,
        "municipalities": len(pop["code"]), "methods": 14,
        "reps_per_stochastic_scenario": reps, "policies": POLICIES,
        "selection": chosen,
        "panel_sha256": "2b84fd89497c10a9d47f6a1a1793da144ac1be845df97605101607e424e1323d",
        "census_sha256": "145bd9448282278e3de4290bf1e26e025bc783965defb6f82c71be467439b641",
        "warnings": [
            "Selection uses 2026 data in half of the synthetic reveal orders",
            "Evaluation permutations have disjoint orders but SAME election and municipal targets",
            "Deterministic adversarial paths are descriptive and were discussed before E017",
            "No independent temporal validation, no 95-percent interval calibration",
            "Aggregate first-round turnout only; never candidate-vote projections",
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
        p.error("Refusing to overwrite existing experiment")
    metadata, summary, records = run(
        args.panel, args.census, reps=args.reps, seed=args.seed
    )
    args.out_dir.mkdir(parents=True)
    (args.out_dir / "metadata.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    for filename, rows in (("scenario_summary.csv", summary), ("path_errors.csv", records)):
        columns = list(dict.fromkeys(k for row in rows for k in row))
        with (args.out_dir / filename).open("w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=columns)
            writer.writeheader()
            writer.writerows(rows)
    print(json.dumps({
        "stage": "E017", "paths": metadata["paths"], "rows": len(records),
        "selected": metadata["selection"]["selected"], "methods": metadata["methods"],
    }))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
