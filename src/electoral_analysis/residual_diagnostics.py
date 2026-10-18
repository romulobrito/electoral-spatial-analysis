"""E007: diagnose regional residuals of retrospectively held-out municipal turnout.

No candidate support forecast, persuasion segment, or individual voter inference.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
from collections import defaultdict
from pathlib import Path

from .ibge_turnout import _fit_ridge, join_turnout, validate_ibge_response
from .municipal_crosswalk import read_crosswalk_zip

REGIONS = {
    "Norte": "AC AP AM PA RO RR TO",
    "Nordeste": "AL BA CE MA PB PE PI RN SE",
    "Centro-Oeste": "DF GO MT MS",
    "Sudeste": "ES MG RJ SP",
    "Sul": "PR RS SC",
}
STATE_REGION = {uf: reg for reg, states in REGIONS.items() for uf in states.split()}
REGIONAL_SHRINKAGE = 100.0
IBGE_SHA = "145bd9448282278e3de4290bf1e26e025bc783965defb6f82c71be467439b641"
PANEL_SHA = "2b84fd89497c10a9d47f6a1a1793da144ac1be845df97605101607e424e1323d"


def stats(rows: list[dict]) -> dict:
    if not rows:
        raise ValueError("Empty diagnostics group")
    n = len(rows)

    def mae(field: str) -> float:
        return sum(abs(r[field]) for r in rows) / n

    def rmse(field: str) -> float:
        return math.sqrt(sum(r[field] ** 2 for r in rows) / n)

    return {
        "municipalities": n,
        "baseline_mae_pp": mae("baseline_residual"),
        "ridge_mae_pp": mae("ridge_residual"),
        "regional_mae_pp": mae("regional_residual"),
        "ridge_rmse_pp": rmse("ridge_residual"),
        "regional_rmse_pp": rmse("regional_residual"),
        "ridge_mean_signed_residual_pp": sum(r["ridge_residual"] for r in rows) / n,
        "regional_mean_signed_residual_pp": sum(r["regional_residual"] for r in rows) / n,
        "regional_minus_ridge_mae_pp": sum(
            abs(r["regional_residual"]) - abs(r["ridge_residual"]) for r in rows
        ) / n,
        "ridge_minus_baseline_mae_pp": sum(
            abs(r["ridge_residual"]) - abs(r["baseline_residual"]) for r in rows
        ) / n,
    }


def tercile_table(rows: list[dict], variable: str) -> list[dict]:
    valid = sorted((r for r in rows if r[variable] is not None), key=lambda r: r[variable])
    n = len(valid)
    if n == 0:
        return []
    bounds = [valid[min(n - 1, int(n * q))][variable] for q in (1 / 3, 2 / 3)]
    partitions = [[], [], []]
    for record in valid:
        idx = 0 if record[variable] <= bounds[0] else 1 if record[variable] <= bounds[1] else 2
        partitions[idx].append(record)
    return [
        {"tercile": name, "upper_limit": boundary, **stats(group)}
        for name, boundary, group in zip(
            ("lower", "middle", "upper"), (bounds[0], bounds[1], None), partitions
        ) if group
    ]


def study(rows: list[dict], *, samples: int = 400, seed: int = 2718) -> dict:
    """Leave-one-state-out ridge plus training-only macrorregional intercept correction."""
    if samples < 20:
        raise ValueError("Minimum bootstrap repetitions: 20")
    useful = [
        r for r in rows if not r["incomplete_2022_denominator"]
        and r["population_2022"] is not None
        and r["density_2022_km2"] is not None
    ]
    states = sorted({r["uf"] for r in useful})
    if len(states) != 27 or any(uf not in STATE_REGION for uf in states):
        raise ValueError("Expected all 27 state/DF groups")
    residuals = []
    for held_state in states:
        train = [r for r in useful if r["uf"] != held_state]
        test = [r for r in useful if r["uf"] == held_state]
        predict = _fit_ridge(train, penalty=10.0)
        regional_sums = defaultdict(float)
        regional_counts = defaultdict(int)
        for item in train:
            region = STATE_REGION[item["uf"]]
            regional_sums[region] += item["delta_turnout_pp"] - predict(item)
            regional_counts[region] += 1
        for item in test:
            region = STATE_REGION[held_state]
            correction = regional_sums[region] / (regional_counts[region] + REGIONAL_SHRINKAGE)
            observed = item["delta_turnout_pp"]
            estimate = predict(item)
            residuals.append({
                "uf": held_state, "region": region,
                "population_2022": item["population_2022"],
                "density_2022_km2": item["density_2022_km2"],
                "baseline_residual": observed,
                "ridge_residual": observed - estimate,
                "regional_residual": observed - estimate - correction,
            })
    by_state = defaultdict(list)
    by_region = defaultdict(list)
    for row in residuals:
        by_state[row["uf"]].append(row)
        by_region[row["region"]].append(row)
    summary = stats(residuals)
    mean = summary["ridge_mean_signed_residual_pp"]
    total_ss = sum((r["ridge_residual"] - mean) ** 2 for r in residuals)
    between_ss = sum(
        len(group) * (stats(group)["ridge_mean_signed_residual_pp"] - mean) ** 2
        for group in by_state.values()
    )
    rng = random.Random(seed)
    distribution = {"ridge_minus_baseline_mae_pp": [], "regional_minus_ridge_mae_pp": []}
    for _ in range(samples):
        sample = [row for _ in states for row in by_state[rng.choice(states)]]
        computed = stats(sample)
        for name, values in distribution.items():
            values.append(computed[name])
    intervals = {}
    for name, values in distribution.items():
        values.sort()
        intervals[name] = [values[int((samples - 1) * .025)], values[int((samples - 1) * .975)]]
    return {
        "scope": "Retrospective municipal turnout errors; not candidate support or voter targeting",
        "method": {
            "heldout": "Leave one entire UF outside training, 27 folds",
            "features": ["turnout_2022", "log1p(population_2022)", "log1p(density_2022)"],
            "ridge_penalty": 10.0,
            "regional_correction": "Train-only within-macrorregion residual mean shrunk by n/(n+100)",
            "fixed_shrinkage": 100.0,
        },
        "overall": summary,
        "state_residual_eta_squared": between_ss / total_ss if total_ss else None,
        "eta_squared_definition": "Descriptive inter-state residual variance fraction, NOT Moran's I",
        "state_folds_alphabetical": [
            {"uf": uf, "region": STATE_REGION[uf], **stats(by_state[uf])} for uf in states
        ],
        "macrorregions_alphabetical": [
            {"region": region, **stats(by_region[region])} for region in sorted(by_region)
        ],
        "population_terciles": tercile_table(residuals, "population_2022"),
        "density_terciles": tercile_table(residuals, "density_2022_km2"),
        "state_cluster_bootstrap": {
            "repetitions": samples, "seed": seed,
            "percentile_95_intervals_pp": intervals,
            "note": "Exploratory bootstrap sensitivity, not confirmatory significance",
        },
        "limitations": [
            "Regional correction conceived after E006: an exploratory post-hoc study",
            "No independent future electoral period is available for confirmatory validation",
            "Grouping by UF is not an adjacency-based autocorrelation test",
            "Census 2022 publication chronology does not establish 2022 ex-ante availability",
            "Polling location does not establish residential neighborhood or individual choice",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--electoral-panel", type=Path, required=True)
    parser.add_argument("--ibge-snapshot", type=Path, required=True)
    parser.add_argument("--crosswalk-zip", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if args.out.exists():
        parser.error("Output exists: preserve provenance")
    ibge_bytes = args.ibge_snapshot.read_bytes()
    panel_bytes = args.electoral_panel.read_bytes()
    if hashlib.sha256(ibge_bytes).hexdigest() != IBGE_SHA:
        raise ValueError("Census 2022 snapshot checksum mismatch")
    if hashlib.sha256(panel_bytes).hexdigest() != PANEL_SHA:
        raise ValueError("Electoral panel checksum mismatch")
    census = validate_ibge_response(json.loads(ibge_bytes))
    crosswalk = read_crosswalk_zip(args.crosswalk_zip)
    if crosswalk["inconsistencies"] or crosswalk["map"].get(("AM", "2550")) != "1302603":
        raise ValueError("Crosswalk or exceptional Amazonas municipality is not verified")
    panel = json.loads(panel_bytes)
    rows, quality = join_turnout(panel, census, exceptional_ibge="1302603")
    result = study(rows)
    result["quality"] = quality
    result["source_sha256"] = {"ibge": IBGE_SHA, "electoral": PANEL_SHA}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"overall": result["overall"],
                      "bootstrap": result["state_cluster_bootstrap"],
                      "eta_squared": result["state_residual_eta_squared"],
                      "quality": quality}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
