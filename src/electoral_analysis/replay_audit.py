"""E014: audit archived historical aggregate election-night projection snapshots.

No forecasting, no candidate ranking and no simulated empirical claims.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import itertools
import json
import math
import random
import statistics
from collections import defaultdict
from datetime import datetime
from pathlib import Path

PROJECTION_COLUMNS = (
    "election_id", "model_id", "metric_id", "unit_id", "uf",
    "snapshot_utc", "data_asof_utc", "progress_fraction",
    "estimate_pct", "lower95_pct", "upper95_pct", "source_sha256",
)
TRUTH_COLUMNS = ("election_id", "metric_id", "unit_id", "uf", "final_pct")
EDGE_COLUMNS = ("unit_a", "unit_b")
BUCKETS = (0.0, .01, .025, .05, .10, .25, .50, 1.0)
BUCKET_LABELS = ("0–1%", "1–2.5%", "2.5–5%", "5–10%", "10–25%", "25–50%", "50–100%")


def _read(path: Path, columns: tuple[str, ...]) -> list[dict]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != list(columns):
            raise ValueError(f"{path.name}: exact ordered columns required: {list(columns)}")
        rows = list(reader)
    if not rows:
        raise ValueError(f"{path.name}: empty input")
    if any(any(v is None or not str(v).strip() for v in row.values()) for row in rows):
        raise ValueError(f"{path.name}: missing input value")
    return rows


def _pct(v: str, field: str) -> float:
    try:
        result = float(v)
    except ValueError as exc:
        raise ValueError(f"Invalid {field}: {v}") from exc
    if not math.isfinite(result) or not 0 <= result <= 100:
        raise ValueError(f"Invalid percentage {field}: {v}")
    return result


def _time(v: str) -> datetime:
    if not v.endswith("Z"):
        raise ValueError("E014 requires explicit UTC Z timestamps")
    try:
        return datetime.fromisoformat(v.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"Bad UTC timestamp {v}") from exc


def _bucket(progress: float) -> str:
    for k in range(len(BUCKET_LABELS)):
        if progress <= BUCKETS[k + 1]:
            return BUCKET_LABELS[k]
    raise ValueError("Invalid progress fraction")


def _truth(path: Path) -> dict:
    records = {}
    for row in _read(path, TRUTH_COLUMNS):
        key = (row["election_id"], row["metric_id"], row["unit_id"])
        if key in records:
            raise ValueError(f"Duplicate final official truth: {key}")
        records[key] = {"final_pct": _pct(row["final_pct"], "final_pct"),
                        "uf": row["uf"]}
    return records


def _projections(path: Path, truth: dict) -> list[dict]:
    parsed, seen, series = [], set(), defaultdict(list)
    for row in _read(path, PROJECTION_COLUMNS):
        key = (row["election_id"], row["metric_id"], row["unit_id"])
        match = truth.get(key)
        if match is None or match["uf"] != row["uf"]:
            raise ValueError(f"No compatible official final value for {key}")
        stamp = _time(row["snapshot_utc"])
        asof = _time(row["data_asof_utc"])
        if asof > stamp:
            raise ValueError(f"Future-data leakage: {key} asof {asof} > {stamp}")
        source = row["source_sha256"]
        if len(source) != 64 or any(c not in "0123456789abcdef" for c in source):
            raise ValueError("source_sha256 must be 64 lowercase hexadecimal characters")
        record_key = (*key, row["model_id"], stamp)
        if record_key in seen:
            raise ValueError(f"Duplicate forecast snapshot {record_key}")
        seen.add(record_key)
        try:
            progress = float(row["progress_fraction"])
        except ValueError as exc:
            raise ValueError("Invalid progress fraction") from exc
        if not math.isfinite(progress) or not 0 < progress <= 1:
            raise ValueError("Invalid progress fraction (0,1]")
        estimate, low, high = (_pct(row[x], x) for x in
                               ("estimate_pct", "lower95_pct", "upper95_pct"))
        if not low <= estimate <= high:
            raise ValueError("95% interval does not contain point estimate")
        final = match["final_pct"]
        obs = {
            "election_id": key[0], "metric_id": key[1], "unit_id": key[2],
            "uf": row["uf"], "model_id": row["model_id"],
            "snapshot_utc": row["snapshot_utc"],
            "progress_fraction": progress,
            "progress_bucket": _bucket(progress),
            "residual_pp": final-estimate,
            "abs_error_pp": abs(estimate-final),
            "square_error_pp": (estimate-final)**2,
            "covered95": int(low <= final <= high),
            "width95_pp": high-low,
            "source_sha256": source,
        }
        parsed.append(obs)
        series[(*key, row["model_id"])].append((stamp, progress))
    for key, points in series.items():
        ordered = sorted(points)
        if any(right[1] + 1e-9 < left[1]
               for left, right in itertools.pairwise(ordered)):
            raise ValueError(f"Decreasing snapshot progress; investigate revisions: {key}")
    return parsed


def _summary(rows: list[dict]) -> dict:
    n = len(rows)
    return {
        "observations": n,
        "elections": len({r["election_id"] for r in rows}),
        "distinct_snapshot_times": len({
            (r["election_id"], r["snapshot_utc"]) for r in rows
        }),
        "mae_pp": sum(r["abs_error_pp"] for r in rows)/n,
        "rmse_pp": math.sqrt(sum(r["square_error_pp"] for r in rows)/n),
        "bias_truth_minus_estimate_pp": sum(r["residual_pp"] for r in rows)/n,
        "empirical_95pct_interval_coverage": sum(r["covered95"] for r in rows)/n,
        "mean_interval_width_pp": sum(r["width95_pp"] for r in rows)/n,
        "note": "Repeated snapshots; not independent replicates or a coverage guarantee",
    }


def _comparison(rows: list[dict], reference: str,
                seed: int, draws: int) -> list[dict]:
    lookup = {
        (r["election_id"], r["metric_id"], r["unit_id"],
         r["snapshot_utc"], r["model_id"]): r for r in rows
    }
    grouped = defaultdict(list)
    models = sorted({r["model_id"] for r in rows} - {reference})
    for other in models:
        for r in rows:
            if r["model_id"] != other:
                continue
            ref = lookup.get((
                r["election_id"], r["metric_id"], r["unit_id"],
                r["snapshot_utc"], reference
            ))
            if ref is None:
                continue
            if abs(ref["progress_fraction"]-r["progress_fraction"]) > 1e-9:
                raise ValueError("Incomparable progress in paired forecast snapshots")
            grouped[(other, r["metric_id"], r["progress_bucket"])].append((
                r["election_id"], r["abs_error_pp"]-ref["abs_error_pp"]
            ))
    outcomes = []
    for (other, metric, bucket), values in sorted(grouped.items()):
        elections = defaultdict(list)
        for election, diff in values:
            elections[election].append(diff)
        # Each historical election is a cluster; do not count minute snapshots
        # or municipalities as independent elections.
        event_means = {e: statistics.mean(v) for e, v in elections.items()}
        event_values = [event_means[e] for e in sorted(event_means)]
        effect = statistics.mean(event_values)
        ci = None
        if len(event_values) >= 3:
            rng = random.Random(seed)
            sample = sorted(
                statistics.mean([rng.choice(event_values) for _ in event_values])
                for _ in range(draws)
            )
            ci = [sample[int(.025*(draws-1))], sample[int(.975*(draws-1))]]
        outcomes.append({
            "model": other, "reference": reference, "metric": metric,
            "progress_bucket": bucket, "matched_rows": len(values),
            "independent_elections": len(elections),
            "difference_mae_pp_event_mean": effect,
            "election_block_bootstrap_95ci_pp": ci,
            "smaller_is_better": True,
            "note": "Exploratory CI (only >=3 elections); model selection unaccounted for",
        })
    return outcomes


def _load_edges(path: Path) -> list[tuple[str, str]]:
    edges = set()
    for row in _read(path, EDGE_COLUMNS):
        a, b = row["unit_a"], row["unit_b"]
        if a == b:
            raise ValueError("Graph contains self-edge")
        edge = tuple(sorted((a, b)))
        if edge in edges:
            raise ValueError("Duplicate graph edge")
        edges.add(edge)
    return sorted(edges)


def _within_uf_moran(rows: list[dict],
                     edges: list[tuple[str, str]]) -> dict | None:
    """Descriptive Moran of truth minus archived estimate, same UF only."""
    values = {r["unit_id"]: r for r in rows}
    if len(values) != len(rows):
        raise ValueError("Spatial snapshot contains duplicate municipality IDs")
    neighbors = defaultdict(set)
    for a, b in edges:
        if a in values and b in values and values[a]["uf"] == values[b]["uf"]:
            neighbors[a].add(b)
            neighbors[b].add(a)
    if len(neighbors) < 4:
        return None
    by_uf = defaultdict(list)
    for unit in neighbors:
        by_uf[values[unit]["uf"]].append(unit)
    centered = {}
    for group in by_uf.values():
        mean = statistics.mean(values[n]["residual_pp"] for n in group)
        for n in group:
            centered[n] = values[n]["residual_pp"]-mean
    denom = sum(v*v for v in centered.values())
    if denom < 1e-14:
        return None
    numer = sum(
        centered[node]*statistics.mean(centered[n] for n in connected)
        for node, connected in neighbors.items()
    )
    return {
        "conditional_moran_I": numer/denom,
        "connected_municipalities": len(neighbors),
        "within_uf_groups": len(by_uf),
        "note": "Descriptive, same-UF graph; no permutation p-value or causal claim",
    }


def evaluate(projections: Path, truth: Path, *, reference: str | None = None,
             edges: Path | None = None, draws: int = 400, seed: int = 2718) -> dict:
    if draws < 100:
        raise ValueError("At least 100 resamples required")
    data = _projections(projections, _truth(truth))
    by_group = defaultdict(list)
    for row in data:
        by_group[(
            row["model_id"], row["metric_id"], row["progress_bucket"]
        )].append(row)
    summaries = []
    for (model, metric, bucket), entries in sorted(by_group.items()):
        summaries.append({
            "model": model, "metric": metric, "progress_bucket": bucket,
            **_summary(entries),
        })
    models = {r["model_id"] for r in data}
    if reference is not None and reference not in models:
        raise ValueError("Reference model not present in archived snapshots")
    spatial = []
    if edges is not None:
        graph = _load_edges(edges)
        snapshot_groups = defaultdict(list)
        for row in data:
            key = (row["election_id"], row["model_id"], row["metric_id"],
                   row["snapshot_utc"])
            snapshot_groups[key].append(row)
        for key, group in sorted(snapshot_groups.items()):
            result = _within_uf_moran(group, graph)
            if result:
                spatial.append({
                    "election": key[0], "model": key[1], "metric": key[2],
                    "snapshot_utc": key[3], **result,
                })
    return {
        "stage": "E014",
        "type": "retrospective_forecast_AUDIT_not_forecast",
        "inputs_sha256": {
            "archived_forecasts_csv": hashlib.sha256(projections.read_bytes()).hexdigest(),
            "official_final_csv": hashlib.sha256(truth.read_bytes()).hexdigest(),
            **({"same_uf_edges_csv": hashlib.sha256(edges.read_bytes()).hexdigest()}
               if edges else {}),
        },
        "counts": {
            "rows": len(data),
            "elections": len({r["election_id"] for r in data}),
            "models": len(models),
        },
        "progress_definition": "Source-specific; matched records require same denominator",
        "summary": summaries,
        "paired_differences": (
            _comparison(data, reference, seed, draws) if reference else []
        ),
        "spatial_descriptive": spatial,
        "limits": [
            "Declared source SHA256 format checked, not original archived bytes",
            "Declared source as-of is necessary but not sufficient proof against leakage",
            "One election cannot establish nominal 95% uncertainty coverage",
            "Municipal unweighted MAE is NOT national vote-share error",
            "No new predictions, campaign targeting or political rankings generated",
            "Synthetic fixtures are NOT evidence about any election or model",
        ],
        "seed": seed,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Audit archived historical aggregate election-night projections"
    )
    parser.add_argument("--projections", type=Path, required=True)
    parser.add_argument("--truth", type=Path, required=True)
    parser.add_argument("--reference")
    parser.add_argument("--edges", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--bootstrap-draws", type=int, default=400)
    args = parser.parse_args()
    if args.out.exists():
        parser.error("Refusing to overwrite existing report")
    output = evaluate(
        args.projections, args.truth, reference=args.reference,
        edges=args.edges, draws=args.bootstrap_draws,
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(output, ensure_ascii=False, indent=2)+"\n", encoding="utf-8"
    )
    print(json.dumps({
        "rows": output["counts"]["rows"],
        "groups": len(output["summary"]),
        "pairs": len(output["paired_differences"]),
        "spatial_snapshots": len(output["spatial_descriptive"]),
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
