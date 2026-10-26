"""E014: stress-test counterfactual MUNICIPAL arrival order of aggregate turnout.

Actual first-round 2026 municipal turnout; synthetic reveal orders only.
No candidate voting projections or real section-level election-night replay.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import random
from collections import defaultdict
from pathlib import Path

import numpy as np

PANEL_SHA256 = "2b84fd89497c10a9d47f6a1a1793da144ac1be845df97605101607e424e1323d"
EXCLUDED_IBGE = "1302603"
STAGES = (0.0025, .01, .025, .05, .10, .25, .50, .75, .95)
METHODS = ("partial_share", "historical_2022", "national_swing", "uf_shrunk_swing")
UF_PRIOR_COUNT = 30.0


def load_population(path: Path) -> dict:
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != PANEL_SHA256:
        raise ValueError("E005 official panel SHA256 mismatch")
    data = json.loads(raw)
    values = []
    for row in data["municipalities"]:
        if row["municipality_ibge"] == EXCLUDED_IBGE:
            continue
        old, new = row["2022"], row["2026"]
        w = int(new["eligible_conserving_sections"])
        attended = int(new["attended"])
        if w <= 0 or not 0 <= attended <= w:
            raise ValueError("Invalid 2026 municipal turnout")
        historical = float(old["turnout_rate"])
        if not 0 <= historical <= 1:
            raise ValueError("Invalid historical turnout")
        if abs(attended / w - new["turnout_rate"]) > 1e-11:
            raise ValueError("Recorded 2026 turnout != attended/eligible")
        values.append((row["municipality_ibge"], row["uf"], w, historical, attended / w))
    if len(values) != 5569 or len({v[0] for v in values}) != 5569:
        raise ValueError("Expected audited 5,569 comparable municipalities")
    values.sort()
    code, uf, weight, historical, current = zip(*values)
    groups = sorted(set(uf))
    if len(groups) != 27:
        raise ValueError("Expected 27 state/DF groups")
    ufids = {g: i for i, g in enumerate(groups)}
    return {
        "code": np.array(code),
        "uf": np.array(uf),
        "group": np.array([ufids[x] for x in uf], dtype=int),
        "weight": np.array(weight, dtype=float),
        "historical": np.array(historical, dtype=float),
        "current": np.array(current, dtype=float),
        "groups": groups,
    }


def order_paths(pop: dict, reps: int, seed: int):
    if reps < 2:
        raise ValueError("At least 2 replicate orders per stochastic scenario required")
    rng = random.Random(seed)
    n = len(pop["weight"])
    indices = list(range(n))
    old = pop["historical"]
    weights = pop["weight"]
    states = pop["group"]
    yield "low_historical_first", 0, sorted(indices, key=lambda i: (old[i], i))
    yield "high_historical_first", 0, sorted(indices, key=lambda i: (-old[i], i))
    yield "large_municipality_first", 0, sorted(indices, key=lambda i: (-weights[i], i))
    yield "small_municipality_first", 0, sorted(indices, key=lambda i: (weights[i], i))
    yield "states_in_blocks", 0, sorted(indices, key=lambda i: (states[i], i))
    for rep in range(reps):
        perm = indices.copy()
        rng.shuffle(perm)
        yield "uniform_municipality_random", rep, perm
        # UF balancing uses only registered electorate and location, never
        # the turnout that is being treated as hidden until the municipality arrives.
        by_state = defaultdict(list)
        for i in indices:
            by_state[states[i]].append(i)
        for group in by_state.values():
            rng.shuffle(group)
        total_by_state = np.bincount(states, weights=weights, minlength=27)
        pointers = [0] * 27
        seen_weight = [0.0] * 27
        balanced = []
        while len(balanced) < n:
            available = [g for g in range(27) if pointers[g] < len(by_state[g])]
            g = min(available, key=lambda k: (seen_weight[k] / total_by_state[k], k))
            i = by_state[g][pointers[g]]
            pointers[g] += 1
            seen_weight[g] += weights[i]
            balanced.append(i)
        yield "balanced_uf_random", rep, balanced


def evaluate_path(pop: dict, order: list[int], thresholds=STAGES) -> list[dict]:
    """The official 2026 target is consulted only for REVEALED units and scoring."""
    idx = np.asarray(order, dtype=int)
    n = len(idx)
    if n != len(pop["weight"]) or len(np.unique(idx)) != n:
        raise ValueError("Order must be an exact municipality permutation")
    w, h, y, groups = (
        pop["weight"], pop["historical"], pop["current"], pop["group"]
    )
    total_w = w.sum()
    actual = 100 * np.dot(w, y) / total_w  # SCORING ONLY
    hist_total = 100 * np.dot(w, h) / total_w
    cum = np.cumsum(w[idx])
    results = []
    for target in thresholds:
        if not 0 < target < 1:
            raise ValueError("Stage must be in (0,1)")
        stop = min(n - 1, int(np.searchsorted(
            cum, target * total_w, side="left"
        ))) + 1
        obs_idx, missed_idx = idx[:stop], idx[stop:]
        wo, yo, ho = w[obs_idx], y[obs_idx], h[obs_idx]
        coverage = wo.sum() / total_w
        partial = 100 * np.dot(wo, yo) / wo.sum()
        national_delta = np.dot(wo, (yo - ho)) / wo.sum()
        available_votes = np.dot(wo, yo)
        projected_national = 100 * (
            available_votes + np.dot(
                w[missed_idx],
                np.clip(h[missed_idx] + national_delta, 0, 1)
            )
        ) / total_w
        counts = np.bincount(groups[obs_idx], minlength=27)
        deltas_numer = np.bincount(
            groups[obs_idx], weights=wo * (yo - ho), minlength=27
        )
        weights_seen = np.bincount(
            groups[obs_idx], weights=wo, minlength=27
        )
        group_delta = np.divide(
            deltas_numer, weights_seen,
            out=np.full(27, national_delta), where=weights_seen > 0
        )
        shrink = counts / (counts + UF_PRIOR_COUNT)
        adjusted_delta = shrink * group_delta + (1 - shrink) * national_delta
        regional = 100 * (
            available_votes + np.dot(
                w[missed_idx],
                np.clip(
                    h[missed_idx] + adjusted_delta[groups[missed_idx]], 0, 1
                )
            )
        ) / total_w
        estimates = {
            "partial_share": partial,
            "historical_2022": hist_total,
            "national_swing": projected_national,
            "uf_shrunk_swing": regional,
        }
        for name, estimate in estimates.items():
            results.append({
                "threshold_pct": target * 100,
                "actual_eligible_coverage_pct": coverage * 100,
                "municipalities_seen": stop,
                "method": name,
                "estimate_turnout_pct": float(estimate),
                "final_turnout_pct": float(actual),
                "abs_error_pp": float(abs(estimate - actual)),
                "signed_error_pp": float(estimate - actual),
            })
    return results


def run(panel: Path, *, reps: int = 120, seed: int = 20261026):
    pop = load_population(panel)
    path_results = []
    for name, rep, ordering in order_paths(pop, reps, seed):
        for record in evaluate_path(pop, ordering):
            record.update({"scenario": name, "replicate": rep})
            path_results.append(record)
    groups = defaultdict(list)
    for row in path_results:
        groups[
            (row["scenario"], row["threshold_pct"], row["method"])
        ].append(row)
    summaries = []
    for (scenario, threshold, method), rows in sorted(groups.items()):
        errors = sorted(r["abs_error_pp"] for r in rows)
        coverages = sorted(r["actual_eligible_coverage_pct"] for r in rows)
        k = len(errors)
        summaries.append({
            "scenario": scenario, "target_coverage_pct": threshold,
            "method": method, "paths": k,
            "mean_abs_error_pp": sum(errors) / k,
            "p90_abs_error_pp": errors[math.ceil(.9 * k) - 1],
            "max_abs_error_pp": errors[-1],
            "median_actual_coverage_pct": coverages[k // 2],
        })
    overview = {
        "stage": "E014",
        "kind": "counterfactual_municipal_arrival_simulation",
        "source": "Audited 2022 and FIRST-ROUND 2026 municipal turnout panel",
        "panel_sha256": PANEL_SHA256,
        "municipalities": len(pop["weight"]),
        "states": len(pop["groups"]),
        "true_first_round_2026_turnout_pct": float(
            100 * np.dot(
                pop["weight"], pop["current"]
            ) / sum(pop["weight"])
        ),
        "historical_2022_turnout_pct_2026_weighted": float(
            100 * np.dot(
                pop["weight"], pop["historical"]
            ) / sum(pop["weight"])
        ),
        "denominator": (
            "2026 municipal electorate revealed, NOT percent of sections"
        ),
        "random_paths_per_stochastic_scenario": reps,
        "stochastic_scenarios": 2,
        "deterministic_scenarios": 5,
        "seed": seed,
        "uf_shrinkage_pseudocount": UF_PRIOR_COUNT,
        "important_limits": [
            "Actual municipal first-round turnout, synthetic arrival orders",
            "Not actual second-round vote shares or section-level timestamps",
            "Known final turnout used only for scoring",
            "2026 registered electorate presumed available before voting",
            "Exceptional municipality 1302603 excluded",
            "Same completed election for all runs, not independent replication",
            "No forecast interval coverage inferred from order permutations",
            "Not an evaluation of Rodrigo Mahlmeister's forecasting system",
        ],
    }
    return overview, summaries, path_results


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--panel", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--reps", type=int, default=120)
    parser.add_argument("--seed", type=int, default=20261026)
    args = parser.parse_args()
    if args.out_dir.exists():
        parser.error("Do not overwrite existing experiment directory")
    overview, summary, paths = run(args.panel, reps=args.reps, seed=args.seed)
    args.out_dir.mkdir(parents=True)
    (args.out_dir / "metadata.json").write_text(
        json.dumps(overview, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    for filename, rows in (
        ("scenario_summary.csv", summary), ("path_errors.csv", paths)
    ):
        with (args.out_dir / filename).open(
            "w", encoding="utf-8", newline=""
        ) as handle:
            writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
    print(json.dumps({
        "sample": overview["municipalities"],
        "true_turnout_pct": overview["true_first_round_2026_turnout_pct"],
        "simulation_paths": 2 * args.reps + 5,
        "results_rows": len(paths),
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
