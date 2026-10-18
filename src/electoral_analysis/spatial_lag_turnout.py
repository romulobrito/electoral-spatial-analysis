"""E010: strict historical spatial-lag controls for aggregate turnout.

All graph features are computed exclusively from 2022 observed turnout and
official 2022 geometry. No 2026 held-out outcomes enter graph features.
No political-preference or candidate-vote estimation is performed.
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
from .residual_diagnostics import IBGE_SHA, PANEL_SHA, REGIONAL_SHRINKAGE, STATE_REGION
from .spatial_moran import build_adjacency
from .state_conditional_moran import conditional_permutations, prepare_within_state_graph

FEATURE_KEYS = ("turnout_2022", "log_population", "log_density", "neighbor_turnout_2022")
EXPECTED_NONSPATIAL_MAE = 1.9567342399383514
EXPECTED_REGIONAL_MAE = 1.7914991430214526
PENALTY = 10.0
SEED = 2718


def historical_neighbor_features(rows: list[dict], edges: list[list[str]]) -> tuple[dict, dict]:
    """Compute 2022-only neighborhood mean; leave isolates flagged with own-value fallback."""
    by_code = {r["ibge"]: r for r in rows}
    if len(by_code) != len(rows):
        raise ValueError("Duplicate municipality identifier")
    neighbor_codes = {key: set() for key in by_code}
    for a, b in edges:
        if a not in by_code or b not in by_code or a == b:
            raise ValueError("Unknown or self-linked municipality in graph")
        neighbor_codes[a].add(b)
        neighbor_codes[b].add(a)
    features = {}
    isolates = []
    for code, row in by_code.items():
        if not 0 <= row["turnout_2022"] <= 1:
            raise ValueError("Invalid historical turnout")
        neighbors = neighbor_codes[code]
        if neighbors:
            average = sum(by_code[n]["turnout_2022"] for n in neighbors) / len(neighbors)
        else:
            isolates.append(code)
            average = row["turnout_2022"]
        features[code] = {
            "neighbor_turnout_2022": average,
            "n_neighbors": len(neighbors),
        }
    return features, {
        "municipalities": len(by_code),
        "isolate_count": len(isolates),
        "isolate_codes": sorted(isolates),
        "feature_source": "only the frozen observed 2022 turnout rates and 2022 IBGE topology",
        "uses_2026_outcomes": False,
    }


def _covariates(row: dict, historical: dict[str, dict]) -> list[float]:
    if row["population_2022"] is None or row["density_2022_km2"] is None:
        raise ValueError("Census data unavailable for model feature")
    return [
        row["turnout_2022"],
        math.log1p(row["population_2022"]),
        math.log1p(row["density_2022_km2"]),
        historical[row["ibge"]]["neighbor_turnout_2022"],
    ]


def fit_ridge4(train: list[dict], historical: dict[str, dict], penalty: float = PENALTY):
    """Fixed four-feature ridge; all moments computed on training municipalities only."""
    if len(train) < 10:
        raise ValueError("Too few training municipalities")
    xx = [_covariates(row, historical) for row in train]
    yy = [row["delta_turnout_pp"] for row in train]
    n, d = len(train), len(FEATURE_KEYS)
    means = [sum(x[j] for x in xx) / n for j in range(d)]
    scales = [
        math.sqrt(sum((x[j] - means[j]) ** 2 for x in xx) / n)
        for j in range(d)
    ]
    if any(x <= 1e-12 for x in scales):
        raise ValueError("Train-fold-only predictor variance collapsed")
    target_mean = sum(yy) / n
    gram = [[0.0] * (d + 1) for _ in range(d)]
    for x, target in zip(xx, yy):
        z = [(x[j] - means[j]) / scales[j] for j in range(d)]
        for j in range(d):
            for k in range(d):
                gram[j][k] += z[j] * z[k]
            gram[j][d] += z[j] * (target - target_mean)
    for j in range(d):
        gram[j][j] += penalty
    for j in range(d):
        pivot = max(range(j, d), key=lambda idx: abs(gram[idx][j]))
        gram[j], gram[pivot] = gram[pivot], gram[j]
        factor = gram[j][j]
        if abs(factor) < 1e-12:
            raise ValueError("Singular penalized training system")
        gram[j] = [v / factor for v in gram[j]]
        for k in range(d):
            if k != j:
                multiplier = gram[k][j]
                gram[k] = [a - multiplier * b for a, b in zip(gram[k], gram[j])]
    slopes = [row[d] for row in gram]

    def predict(row: dict) -> float:
        x = _covariates(row, historical)
        return target_mean + sum(
            slopes[j] * (x[j] - means[j]) / scales[j] for j in range(d)
        )

    return predict


def evaluate(rows: list[dict], adjacency: dict, *, samples: int = 400, seed: int = SEED) -> dict:
    """All-state holdout, historical covariates only, four comparable residual vectors."""
    if samples < 20:
        raise ValueError("Too few state-cluster replicates")
    valid = [
        row for row in rows if not row["incomplete_2022_denominator"]
        and row["population_2022"] is not None
        and row["density_2022_km2"] is not None
    ]
    if len(valid) != 5569:
        raise ValueError("E010 sample differs from verified E007 panel")
    states = sorted({row["uf"] for row in valid})
    if len(states) != 27 or set(states) != set(STATE_REGION):
        raise ValueError("Unexpected UF holdout coverage")
    feature_versions = {}
    controls = {}
    # Estimate a separate spatial 4-feature ridge for queen and rook; no tuning.
    for topology in ("queen", "rook"):
        features, audit = historical_neighbor_features(valid, adjacency[topology]["edges"])
        feature_versions[topology] = features
        controls[topology] = audit

    errors = {}
    by_state = defaultdict(list)
    fold_counts = {}
    for uf in states:
        train = [row for row in valid if row["uf"] != uf]
        test = [row for row in valid if row["uf"] == uf]
        ordinary = _fit_ridge(train, penalty=PENALTY)
        spatial = {
            topo: fit_ridge4(train, feature_versions[topo])
            for topo in ("queen", "rook")
        }
        training_errors = defaultdict(list)
        for item in train:
            training_errors[STATE_REGION[item["uf"]]].append(
                item["delta_turnout_pp"] - ordinary(item)
            )
        region = STATE_REGION[uf]
        offset = sum(training_errors[region]) / (
            len(training_errors[region]) + REGIONAL_SHRINKAGE
        )
        fold_counts[uf] = len(test)
        for item in test:
            code = item["ibge"]
            if code in errors:
                raise ValueError("Duplicate held-out prediction")
            target = item["delta_turnout_pp"]
            errors[code] = {
                "uf": uf, "baseline": target,
                "ridge": target - ordinary(item),
                "ridge_regional": target - ordinary(item) - offset,
                "spatial_queen": target - spatial["queen"](item),
                "spatial_rook": target - spatial["rook"](item),
            }
            by_state[uf].append(code)

    methods = ("baseline", "ridge", "ridge_regional", "spatial_queen", "spatial_rook")
    overall = {
        metric: {
            "mae_pp": sum(abs(row[metric]) for row in errors.values()) / len(errors),
            "rmse_pp": math.sqrt(
                sum(row[metric] ** 2 for row in errors.values()) / len(errors)
            ),
        } for metric in methods
    }
    if abs(overall["ridge"]["mae_pp"] - EXPECTED_NONSPATIAL_MAE) > 1e-8:
        raise ValueError("E006 ridge benchmark failed to reproduce")
    if abs(overall["ridge_regional"]["mae_pp"] - EXPECTED_REGIONAL_MAE) > 1e-8:
        raise ValueError("E007 corrected ridge benchmark failed to reproduce")

    comparisons = ("spatial_queen", "spatial_rook")
    rng = random.Random(seed)
    intervals = {}
    for candidate in comparisons:
        deltas = []
        for _ in range(samples):
            sampled = [errors[code] for uf in (
                rng.choice(states) for _ in states
            ) for code in by_state[uf]]
            diff = sum(
                abs(r[candidate]) - abs(r["ridge_regional"]) for r in sampled
            ) / len(sampled)
            deltas.append(diff)
        deltas.sort()
        intervals[candidate] = {
            "candidate_minus_e007_mae_pp": (
                overall[candidate]["mae_pp"] - overall["ridge_regional"]["mae_pp"]
            ),
            "state_bootstrap_95pct_pp": [
                deltas[int((samples-1)*0.025)],
                deltas[int((samples-1)*0.975)],
            ],
        }
    return {
        "method": "Retrospective leave-one-UF-out; 2022-only graph covariates; no leakage of held-out 2026 outcomes",
        "feature_names": list(FEATURE_KEYS),
        "fixed_ridge_penalty": PENALTY,
        "fold_counts_uf_alphabetical": fold_counts,
        "sample_size": len(errors),
        "models": overall, "spatial_vs_e007": intervals,
        "feature_audit": controls,
        "state_cluster_bootstrap_replicates": samples,
        "seed": seed,
        "errors": errors,
    }


def within_uf_moran_for_models(errors: dict, adjacency: dict, *,
                               permutations: int = 499) -> dict:
    """Compare E007 residuals and historical spatial ridge under the E009 conditional null."""
    # E009's fixed interface expects baseline/ridge/ridge_regional fields.
    # Explicitly map baseline <- spatial model; this is a computational adapter only.
    response = {}
    for topo in ("queen", "rook"):
        converted = {
            code: {
                "uf": row["uf"],
                "baseline": row["spatial_" + topo],
                "ridge": row["ridge"],
                "ridge_regional": row["ridge_regional"],
            }
            for code, row in errors.items()
        }
        prepared = prepare_within_state_graph(converted, adjacency[topo]["edges"])
        response[topo] = {
            "spatial_ridge": conditional_permutations(
                converted, prepared, "baseline", permutations=permutations
            ),
            "ordinary_ridge": conditional_permutations(
                converted, prepared, "ridge", permutations=permutations
            ),
            "regional_ridge": conditional_permutations(
                converted, prepared, "ridge_regional", permutations=permutations
            ),
            "connected_nodes": len(prepared["nodes"]),
            "within_uf_edges": prepared["within_state_edges"],
        }
    return response


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--panel", type=Path, required=True)
    parser.add_argument("--census", type=Path, required=True)
    parser.add_argument("--geometry", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    if args.output_dir.exists():
        parser.error("Output directory already exists")
    panel_bytes, census_bytes = args.panel.read_bytes(), args.census.read_bytes()
    if hashlib.sha256(panel_bytes).hexdigest() != PANEL_SHA:
        raise ValueError("Frozen E005 panel checksum mismatch")
    if hashlib.sha256(census_bytes).hexdigest() != IBGE_SHA:
        raise ValueError("Frozen E006 census checksum mismatch")
    census = validate_ibge_response(json.loads(census_bytes))
    rows, quality = join_turnout(
        json.loads(panel_bytes), census, exceptional_ibge="1302603"
    )
    codes = {row["ibge"] for row in rows if not row["incomplete_2022_denominator"]}
    adjacency = build_adjacency(args.geometry, codes)
    prediction = evaluate(rows, adjacency)
    spatial_diagnostics = within_uf_moran_for_models(prediction["errors"], adjacency)
    prediction.pop("errors")
    report = {
        "scope": "Aggregate municipal voter turnout; no candidate voting outcome or persuasion model",
        "prediction": prediction,
        "spatial_residual_diagnostics": spatial_diagnostics,
        "source": {
            "electoral_panel_sha256": PANEL_SHA,
            "census_2022_sha256": IBGE_SHA,
            "official_geometry_sha256": adjacency["ibge_2022_shapefile_sha256"],
        },
        "quality": quality,
        "limitations": [
            "Retrospective 2022-to-2026 fold evaluation, not a proven 2022-ex-ante forecast",
            "2022 Census feature publication chronology not demonstrated before 2022 polling",
            "Candidate model introduced after observing E009; independent period needed for confirmation",
            "Contiguity and 2022 turnout are features only, not causal mechanisms",
            "Within-UF Moran is exploratory and not an estimate of voter behavior",
        ],
    }
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "spatial_turnout_model.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    compact = {
        "scope": report["scope"],
        "models": report["prediction"]["models"],
        "spatial_vs_e007": report["prediction"]["spatial_vs_e007"],
        "feature_audit": report["prediction"]["feature_audit"],
        "spatial_residual_diagnostics": report["spatial_residual_diagnostics"],
    }
    print(json.dumps(compact, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
