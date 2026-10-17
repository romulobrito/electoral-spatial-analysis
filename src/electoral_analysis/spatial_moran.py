"""E008: auditable geographic contiguity and Moran tests for municipal turnout errors.

Only aggregate retrospective turnout; no candidate-support or persuasion scoring.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
import zipfile
from collections import Counter, defaultdict
from pathlib import Path

from .ibge_turnout import _fit_ridge, join_turnout, validate_ibge_response
from .municipal_crosswalk import read_crosswalk_zip
from .residual_diagnostics import (
    IBGE_SHA, PANEL_SHA, REGIONAL_SHRINKAGE, STATE_REGION,
)

GEOMETRY_SHA = "9c904fa1feb978a89042bfecd7758e571266f285d6122a4ff02ffe37bffb76a2"
CROSSWALK_SHA = "68328ddc166806594a2aab5809ac9aa602153535d6b8a71e886c337f9f3631ca"
EXPECTED_E007 = {"ridge_mae_pp": 1.9567342399383514,
                 "regional_mae_pp": 1.7914991430214526}
GEOMETRY_ZIP_MEMBER = "BR_Municipios_2022.shp"


def out_of_state_residuals(rows: list[dict]) -> dict[str, dict]:
    """Derive OOF errors without incorporating a heldout state in ridge or correction."""
    clean = [r for r in rows if not r["incomplete_2022_denominator"]
             and r["population_2022"] is not None
             and r["density_2022_km2"] is not None]
    states = sorted({r["uf"] for r in clean})
    if len(states) != 27 or any(s not in STATE_REGION for s in states):
        raise ValueError("Unexpected state coverage")
    output = {}
    for held in states:
        train = [r for r in clean if r["uf"] != held]
        predict = _fit_ridge(train)
        training_residuals = defaultdict(list)
        for item in train:
            training_residuals[STATE_REGION[item["uf"]]].append(
                item["delta_turnout_pp"] - predict(item))
        region = STATE_REGION[held]
        known = training_residuals[region]
        adjust = sum(known) / (len(known) + REGIONAL_SHRINKAGE)
        for item in (r for r in clean if r["uf"] == held):
            code = item["ibge"]
            if code in output:
                raise ValueError("Duplicate municipality")
            change = item["delta_turnout_pp"]
            predicted = predict(item)
            output[code] = {
                "uf": held,
                "baseline": change,
                "ridge": change - predicted,
                "ridge_regional": change - predicted - adjust,
            }
    if len(output) != 5569:
        raise ValueError("Changed panel composition; expected 5,569 municipalities")
    for metric, field in (
        ("ridge_mae_pp", "ridge"), ("regional_mae_pp", "ridge_regional")
    ):
        current = sum(abs(r[field]) for r in output.values()) / len(output)
        if abs(current - EXPECTED_E007[metric]) > 1e-8:
            raise ValueError(f"OOF residuals differ from E007 {metric}: {current}")
    return output


def _verify_zip(zip_path: Path) -> list[str]:
    with zipfile.ZipFile(zip_path) as archive:
        names = archive.namelist()
        if GEOMETRY_ZIP_MEMBER not in names:
            raise ValueError(f"Missing official municipal Shapefile: {names}")
        if any(name.startswith("/") or ".." in Path(name).parts for name in names):
            raise ValueError("Unsafe municipal archive members")
        if len(names) > 20:
            raise ValueError("Unexpected municipal ZIP contents")
    return names


def build_adjacency(path: Path, codes: set[str]) -> dict:
    """Queen/Rook contiguity on original IBGE 2022 boundaries; no geometry simplification."""
    import pyogrio
    from shapely.strtree import STRtree

    if hashlib.sha256(path.read_bytes()).hexdigest() != GEOMETRY_SHA:
        raise ValueError("Official IBGE Shapefile source SHA256 differs from audited snapshot")
    _verify_zip(path)
    # Read through GDAL's zip virtual file system; do not unpack potentially unsafe paths.
    gis = pyogrio.read_dataframe(
        f"/vsizip/{path.resolve()}/{GEOMETRY_ZIP_MEMBER}",
        columns=["CD_MUN", "SIGLA_UF"],
    )
    if len(gis) != 5572:
        raise ValueError("Unexpected 2022 official shapefile feature count")
    if gis.crs is None or gis.crs.to_epsg() != 4674:
        raise ValueError("Geometry datum must match IBGE's SIRGAS 2000 EPSG:4674")
    if len(set(gis["CD_MUN"].astype(str))) != 5572:
        raise ValueError("Repeated IBGE shape identifier")
    missing = codes - set(gis["CD_MUN"].astype(str))
    if missing:
        raise ValueError(f"Municipality geometries not found: {sorted(missing)[:8]}")
    additional = set(gis["CD_MUN"].astype(str)) - codes
    # 5572 shapes minus 5569 valid turnout model municipalities = 3:
    # two operational lagoons and one excluded exceptional Amazonas municipality.
    if len(additional) != 3:
        raise ValueError(f"Unexpected exclusion count {len(additional)}")
    df = gis.loc[gis["CD_MUN"].astype(str).isin(codes)].sort_values(
        "CD_MUN", kind="stable"
    )
    order = [str(x) for x in df["CD_MUN"]]
    geoms = list(df.geometry)
    if any(g is None or g.is_empty or not g.is_valid for g in geoms):
        raise ValueError("Invalid or empty IBGE polygon; manual geometry review required")
    tree = STRtree(geoms)
    queen_edges = set()
    rook_edges = set()
    for i, geom in enumerate(geoms):
        for candidate in tree.query(geom, predicate="intersects"):
            j = int(candidate)
            if j <= i:
                continue
            other = geoms[j]
            # "touches": boundaries intersect, interiors do not.
            if not geom.touches(other):
                continue
            queen_edges.add((i, j))
            # Rook requires actual shared one-dimensional boundary, not point contact.
            common = geom.boundary.intersection(other.boundary)
            if common.length > 1e-10:
                rook_edges.add((i, j))
    def serialize(edges):
        degrees = Counter()
        for i, j in edges:
            degrees[i] += 1
            degrees[j] += 1
        isolated = [order[i] for i in range(len(order)) if not degrees[i]]
        return {
            "edges": [[order[i], order[j]] for i, j in sorted(edges)],
            "edge_count": len(edges),
            "isolated_ibge_codes": isolated,
            "degree_min_nonisolated": min(degrees.values()) if degrees else None,
            "degree_max": max(degrees.values()) if degrees else None,
        }
    return {
        "ibge_2022_shapefile_sha256": GEOMETRY_SHA,
        "crs": "EPSG:4674",
        "method": "native source geometry; Shapely touches for queen; positive shared boundary length for rook",
        "municipalities": len(order),
        "geometry_exclusions": sorted(additional),
        "queen": serialize(queen_edges),
        "rook": serialize(rook_edges),
    }


def moran_statistic(values: dict[str, float], edges: list[list[str]]) -> dict:
    """Row-standardized Moran's I, excluding isolates from N and denominator."""
    neighbors = defaultdict(set)
    for a, b in edges:
        if a == b:
            raise ValueError("Self edge")
        neighbors[a].add(b)
        neighbors[b].add(a)
    if any(k not in values for k in neighbors):
        raise ValueError("Spatial adjacency code missing in residual data")
    observed_codes = sorted(neighbors)
    if len(observed_codes) < 4:
        raise ValueError("Too few connected observations")
    vector = [float(values[k]) for k in observed_codes]
    mean = sum(vector) / len(vector)
    centered = {code: values[code] - mean for code in observed_codes}
    denominator = sum(x*x for x in centered.values())
    if denominator <= 1e-18:
        raise ValueError("No variance in Moran response")
    numerator = sum(
        centered[code] * sum(centered[neighbor] for neighbor in neighbors[code]) /
        len(neighbors[code])
        for code in observed_codes
    )
    return {
        "I": numerator / denominator, "connected_n": len(observed_codes),
        "isolates_excluded": len(values) - len(observed_codes),
        "expected_null_I": -1/(len(observed_codes)-1),
        "degrees": {
            "minimum": min(len(x) for x in neighbors.values()),
            "maximum": max(len(x) for x in neighbors.values()),
            "mean": sum(map(len, neighbors.values()))/len(neighbors),
        },
    }


def moran_permutations(values: dict[str, float], edges: list[list[str]],
                       *, permutations: int = 499, seed: int = 2718) -> dict:
    """Permutation sensitivity: shuffle municipality residuals across fixed map nodes."""
    if permutations < 19:
        raise ValueError("Need at least 19 permutations")
    observed = moran_statistic(values, edges)
    nodes = sorted({v for edge in edges for v in edge})
    original = [values[n] for n in nodes]
    rng = random.Random(seed)
    permuted = []
    for _ in range(permutations):
        copy = original.copy()
        rng.shuffle(copy)
        measure = moran_statistic(dict(zip(nodes, copy)), edges)
        permuted.append(measure["I"])
    expected = observed["expected_null_I"]
    tail = sum(
        abs(x - expected) >= abs(observed["I"] - expected) - 1e-12
        for x in permuted
    )
    sorted_null = sorted(permuted)
    return {
        **observed,
        "null_mean_empirical": sum(permuted)/permutations,
        "null_interval_95pct": [
            sorted_null[int(.025 * (permutations-1))],
            sorted_null[int(.975 * (permutations-1))],
        ],
        "two_sided_permutation_p": (tail+1)/(permutations+1),
        "permutations": permutations, "seed": seed,
        "note": "Permutation diagnostic conditional on fixed map; no causal interpretation",
    }


def compute(residuals: dict, adjacency: dict) -> dict:
    results = {}
    for method in ("baseline", "ridge", "ridge_regional"):
        values = {code: float(row[method]) for code, row in residuals.items()}
        results[method] = {}
        for contiguity in ("queen", "rook"):
            results[method][contiguity] = moran_permutations(
                values, adjacency[contiguity]["edges"], permutations=499, seed=2718
            )
    return {
        "source": "IBGE 2022 Malha Municipal Digital (EPSG:4674), TSE E005/E007 retrospective turnout",
        "source_geometry_sha256": GEOMETRY_SHA,
        "modeled_municipalities": len(residuals),
        "geometry": {kind: {
            k: v for k, v in adjacency[kind].items() if k != "edges"
        } for kind in ("queen", "rook")},
        "moran": results,
        "limitations": [
            "Queen and rook geometry graph differ for touch-at-point boundaries and islands",
            "Geometry connectivity is not geographical causal influence",
            "Tests are exploratory across six related outcomes/graphs, no confirmatory multiplicity claim",
            "OOF models are retrospective; model correction post hoc since E006",
            "No candidate support or neighborhood-level voter inference",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--panel", type=Path, required=True)
    parser.add_argument("--census", type=Path, required=True)
    parser.add_argument("--crosswalk", type=Path, required=True)
    parser.add_argument("--geometry", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    if args.output_dir.exists():
        parser.error("Output dir exists")
    panel_bytes = args.panel.read_bytes()
    census_bytes = args.census.read_bytes()
    if hashlib.sha256(panel_bytes).hexdigest() != PANEL_SHA:
        raise ValueError("E005 panel checksum mismatch")
    if hashlib.sha256(census_bytes).hexdigest() != IBGE_SHA:
        raise ValueError("E006 Census snapshot checksum mismatch")
    if hashlib.sha256(args.crosswalk.read_bytes()).hexdigest() != CROSSWALK_SHA:
        raise ValueError("TSE municipality crosswalk checksum mismatch")
    crosswalk = read_crosswalk_zip(args.crosswalk)
    if crosswalk["inconsistencies"] or crosswalk["map"].get(("AM", "2550")) != "1302603":
        raise ValueError("Unverified municipality crosswalk")
    census = validate_ibge_response(json.loads(census_bytes))
    panel = json.loads(panel_bytes)
    rows, quality = join_turnout(panel, census, exceptional_ibge="1302603")
    residuals = out_of_state_residuals(rows)
    adjacency = build_adjacency(args.geometry, set(residuals))
    report = compute(residuals, adjacency)
    report["quality"] = quality
    args.output_dir.mkdir(parents=True)
    (args.output_dir / "moran_results.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (args.output_dir / "graph_summary.json").write_text(
        json.dumps({k: v for k, v in adjacency.items() if k not in ("queen", "rook")},
                   ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    compact = {
        "queen_edges": adjacency["queen"]["edge_count"],
        "rook_edges": adjacency["rook"]["edge_count"],
        "queen_isolates": adjacency["queen"]["isolated_ibge_codes"],
        "rook_isolates": adjacency["rook"]["isolated_ibge_codes"],
    }
    print(json.dumps({"geometry": compact, "moran": report["moran"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
