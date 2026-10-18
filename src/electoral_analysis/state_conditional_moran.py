"""E009: conditional spatial-autocorrelation diagnostic of heldout turnout residuals.

Restricted-within-UF neighbors, state-centered errors, within-UF permutations.
Only descriptive, aggregate electoral turnout; never vote choice or targeting.
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

from .ibge_turnout import join_turnout, validate_ibge_response
from .residual_diagnostics import IBGE_SHA, PANEL_SHA
from .spatial_moran import (
    build_adjacency,
    out_of_state_residuals,
)

METHODS = ("baseline", "ridge", "ridge_regional")


def prepare_within_state_graph(
    residuals: dict[str, dict], undirected_edges: list[list[str]]
) -> dict:
    """Exclude cross-UF edges before centering and define connected-node universe."""
    if not residuals:
        raise ValueError("No residual observations")
    nodes = sorted(residuals)
    key_to_index = {node: index for index, node in enumerate(nodes)}
    neighbors = [set() for _ in nodes]
    cross_state = 0
    duplicates = 0
    for source, target in undirected_edges:
        if source == target:
            raise ValueError("Self-loop is invalid")
        if source not in key_to_index or target not in key_to_index:
            raise ValueError("Unknown municipality in geography graph")
        if residuals[source]["uf"] != residuals[target]["uf"]:
            cross_state += 1
            continue
        a, b = key_to_index[source], key_to_index[target]
        if b in neighbors[a]:
            duplicates += 1
        neighbors[a].add(b)
        neighbors[b].add(a)
    connected = [i for i, group in enumerate(neighbors) if group]
    if len(connected) < 4:
        raise ValueError("Too few within-UF connected municipalities")
    remap = {old: new for new, old in enumerate(connected)}
    edges_by_index = [
        tuple(sorted(remap[j] for j in neighbors[old]))
        for old in connected
    ]
    groups: dict[str, list[int]] = defaultdict(list)
    for new, old in enumerate(connected):
        groups[residuals[nodes[old]]["uf"]].append(new)
    if any(len(members) < 2 for members in groups.values()):
        raise ValueError("State with only one connected node")
    states_without_edges = sorted(
        {record["uf"] for record in residuals.values()} - set(groups)
    )
    return {
        "nodes": [nodes[i] for i in connected],
        "neighbors": edges_by_index,
        "groups": {k: groups[k] for k in sorted(groups)},
        "source_edges": len(undirected_edges),
        "cross_state_edges_removed": cross_state,
        "duplicated_same_state_edges": duplicates,
        "within_state_edges": sum(len(n) for n in edges_by_index) // 2,
        "isolated_ibge_codes": [nodes[i] for i, x in enumerate(neighbors) if not x],
        "states_without_contiguity": states_without_edges,
        "original_nodes": len(nodes),
    }


def _uf_centered_vector(residuals: dict, prepared: dict, method: str) -> list[float]:
    if method not in METHODS:
        raise ValueError("Unknown residual method")
    observed = [float(residuals[node][method]) for node in prepared["nodes"]]
    if any(not math.isfinite(value) for value in observed):
        raise ValueError("Nonfinite heldout prediction residual")
    centered = observed.copy()
    for members in prepared["groups"].values():
        average = sum(observed[i] for i in members) / len(members)
        for i in members:
            centered[i] = observed[i] - average
    return centered


def _conditional_moran(vector: list[float], neighbors: list[tuple[int, ...]]) -> float:
    denominator = sum(value * value for value in vector)
    if denominator < 1e-18:
        raise ValueError("No within-UF variance remaining after demeaning")
    numerator = sum(
        value * (sum(vector[j] for j in neighbors[i]) / len(neighbors[i]))
        for i, value in enumerate(vector)
    )
    # Row-standardized spatial weights; S0=N for all connected nodes.
    return numerator / denominator


def conditional_permutations(
    residuals: dict, prepared: dict, method: str, *,
    permutations: int = 499, seed: int = 2718,
) -> dict:
    """Shuffle state-centered residuals within their UF, with fixed within-UF topology.

    Use empirical permutation center instead of a naive global -1/(N-1)
    expectation, because the null is conditioned on fixed UF membership.
    """
    if permutations < 99:
        raise ValueError("Insufficient permutation count for this protocol")
    z = _uf_centered_vector(residuals, prepared, method)
    neighbors = prepared["neighbors"]
    observed = _conditional_moran(z, neighbors)
    randomizer = random.Random(seed)
    groups = list(prepared["groups"].values())
    draws = []
    for _ in range(permutations):
        values = z.copy()
        for group in groups:
            shuffled = [z[i] for i in group]
            randomizer.shuffle(shuffled)
            for j, value in zip(group, shuffled):
                values[j] = value
        draws.append(_conditional_moran(values, neighbors))
    mean_null = sum(draws) / permutations
    extreme = sum(
        abs(value - mean_null) >= abs(observed - mean_null) - 1e-12
        for value in draws
    )
    greater = sum(value >= observed - 1e-12 for value in draws)
    ordered = sorted(draws)
    return {
        "conditional_I": observed,
        "null_center_empirical": mean_null,
        "null_95pct": [
            ordered[int(0.025 * (permutations - 1))],
            ordered[int(0.975 * (permutations - 1))],
        ],
        "two_sided_permutation_p": (1 + extreme) / (permutations + 1),
        "right_tailed_permutation_p": (1 + greater) / (permutations + 1),
        "permutations": permutations,
        "seed": seed,
        "connected_nodes": len(z),
        "state_groups": len(groups),
    }


def study(residuals: dict, adjacency: dict, *, permutations: int = 499) -> dict:
    """Six exploratory statistics: three historical turnout error vectors × two graphs."""
    if "edges" not in adjacency["queen"] or "edges" not in adjacency["rook"]:
        raise ValueError("Missing queen/rook contiguity")
    results = {}
    graphs = {}
    for contiguity in ("queen", "rook"):
        graph = prepare_within_state_graph(
            residuals, adjacency[contiguity]["edges"]
        )
        graphs[contiguity] = {
            key: value for key, value in graph.items()
            if key not in ("nodes", "neighbors", "groups")
        }
        graphs[contiguity]["connected_nodes"] = len(graph["nodes"])
        graphs[contiguity]["state_groups"] = {
            uf: len(members) for uf, members in graph["groups"].items()
        }
        results[contiguity] = {
            method: conditional_permutations(
                residuals, graph, method, permutations=permutations
            )
            for method in METHODS
        }
    return {
        "scope": "Within-UF spatial autocorrelation of retrospective municipal turnout residuals",
        "null": "Shuffle state-demeaned residuals ONLY within each same UF among nodes with in-state neighbors",
        "weights": "Symmetric geographic contiguity restricted to same UF, row-normalized to 1",
        "graphs": graphs,
        "conditional_moran": results,
        "interpretation_constraints": [
            "State-conditioned Moran and E008 global Moran use DIFFERENT weighting matrices, node sets and centering",
            "No analytic global -1/(N-1) null asserted; empirical within-UF null reported",
            "Permutations are exploratory; six correlated tests without multiplicity adjustment",
            "The UF holdout is retrospective; no causal or future-prediction claim",
            "No individual political preferences, candidate vote forecasts or campaign targeting",
        ],
    }


def report_csv(report: dict) -> str:
    from io import StringIO
    buffer = StringIO()
    writer = csv.writer(buffer)
    writer.writerow([
        "graph", "method", "within_uf_moran_I", "empirical_null_mean",
        "permutation_p_two_sided", "null_95pct_lower", "null_95pct_upper",
        "connected_municipalities", "same_uf_edges", "excluded_isolates",
        "cross_uf_edges_removed",
    ])
    for graph in ("queen", "rook"):
        for method in METHODS:
            r = report["conditional_moran"][graph][method]
            q = report["graphs"][graph]
            writer.writerow([
                graph, method, r["conditional_I"], r["null_center_empirical"],
                r["two_sided_permutation_p"], *r["null_95pct"],
                r["connected_nodes"], q["within_state_edges"],
                len(q["isolated_ibge_codes"]), q["cross_state_edges_removed"],
            ])
    return buffer.getvalue()


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--panel", type=Path, required=True)
    p.add_argument("--census", type=Path, required=True)
    p.add_argument("--geometry", type=Path, required=True)
    p.add_argument("--out-dir", type=Path, required=True)
    args = p.parse_args()
    if args.out_dir.exists():
        p.error("Output directory already exists")
    panel_bytes = args.panel.read_bytes()
    census_bytes = args.census.read_bytes()
    if hashlib.sha256(panel_bytes).hexdigest() != PANEL_SHA:
        raise ValueError("E005 official election panel SHA256 mismatch")
    if hashlib.sha256(census_bytes).hexdigest() != IBGE_SHA:
        raise ValueError("E006 IBGE census SHA256 mismatch")
    # The pinned E005 panel already contains verified IBGE municipality codes.
    # Never silently replace these IDs with a changed live TSE crosswalk.
    census = validate_ibge_response(json.loads(census_bytes))
    rows, quality = join_turnout(
        json.loads(panel_bytes), census, exceptional_ibge="1302603"
    )
    residuals = out_of_state_residuals(rows)
    adjacency = build_adjacency(args.geometry, set(residuals))
    result = study(residuals, adjacency)
    result["quality"] = quality
    args.out_dir.mkdir(parents=True)
    (args.out_dir / "conditional_moran.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (args.out_dir / "conditional_moran.csv").write_text(
        report_csv(result), encoding="utf-8"
    )
    print(json.dumps({
        "graphs": result["graphs"], "conditional_moran": result["conditional_moran"]
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
