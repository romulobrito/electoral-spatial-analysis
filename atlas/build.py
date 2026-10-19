"""Build a static, candidate-neutral atlas from the frozen E005 audit and IBGE mesh.

Raw election or geometry ZIP files are never copied into published outputs.
Political preference inference, location scoring and persuasion ranking are excluded.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from collections import Counter
from pathlib import Path

from .analytics import matched_candidacies, census_indicators, validation_diagnostics

E005_SHA = "2b84fd89497c10a9d47f6a1a1793da144ac1be845df97605101607e424e1323d"
IBGE_GEOMETRY_SHA = "9c904fa1feb978a89042bfecd7758e571266f285d6122a4ff02ffe37bffb76a2"
EXCEPTIONAL_AM_CODE = "1302603"
EXPECTED_MUNICIPALITIES = 5570
GEOMETRY_MEMBER = "BR_Municipios_2022.shp"
DISPLAY_SIMPLIFICATION_DEGREES = 0.008


def _json_dump(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
        + "\n",
        encoding="utf-8",
    )


def _validate_year(cell: dict) -> dict:
    valid = cell["valid"]
    blank = cell["blank"]
    null = cell["null"]
    attended = cell["attended"]
    eligible = cell["eligible_conserving_sections"]
    turnout = cell["turnout_rate"]
    candidates = cell["candidates"]
    votes_by_candidate = {
        str(key): details["votes"] for key, details in candidates.items()
    }
    if not all(
        isinstance(x, int) and x >= 0
        for x in (valid, blank, null, attended, eligible, *votes_by_candidate.values())
    ):
        raise ValueError("Invalid electoral vote counts")
    if valid + blank + null != attended or sum(votes_by_candidate.values()) != valid:
        raise ValueError("Candidate/ballot totals disagree")
    if not 0 <= attended <= eligible:
        raise ValueError("Attendance exceeds conserving-section electorate")
    if not (0 <= turnout <= 1) or abs(turnout - attended / eligible) > 1e-8:
        raise ValueError("Turnout is inconsistent with eligible count")
    return {
        "valid": valid,
        "blank": blank,
        "null": null,
        "attended": attended,
        "eligible": eligible,
        "turnout": turnout,
        "votes": votes_by_candidate,
    }


def normalize_panel(panel: dict) -> tuple[dict, dict]:
    """Create a compact all-candidacy factual municipal panel with source checks."""
    if panel.get("matched_municipalities") != EXPECTED_MUNICIPALITIES:
        raise ValueError("Unexpected municipal sample")
    options = panel["candidate_options"]
    normalized_options = {}
    for year in ("2022", "2026"):
        normalized_options[year] = {}
        for code, names in options[year].items():
            if not names or len(names) != 1:
                raise ValueError(f"Ambiguous candidate label {year}/{code}")
            normalized_options[year][code] = names[0]
    seen = set()
    result = {}
    counts = Counter()
    for record in panel["municipalities"]:
        code = str(record["municipality_ibge"])
        uf = record["uf"]
        if len(code) != 7 or not code.isascii() or not code.isdigit():
            raise ValueError("Invalid IBGE municipality code")
        if code in seen:
            raise ValueError("Duplicate IBGE municipality code")
        seen.add(code)
        if len(uf) != 2 or uf == "ZZ":
            raise ValueError("Overseas locations cannot be municipal polygons")
        counts[uf] += 1
        result[code] = {
            "uf": uf,
            "2022": _validate_year(record["2022"]),
            "2026": _validate_year(record["2026"]),
            "turnout_denominator_caveat": code == EXCEPTIONAL_AM_CODE,
        }
    if len(seen) != EXPECTED_MUNICIPALITIES:
        raise ValueError("Municipal row count changed")
    if len(counts) != 27:
        raise ValueError("Expected 27 UFs")
    for year in ("2022", "2026"):
        for record in result.values():
            if any(code not in normalized_options[year] for code in record[year]["votes"]):
                raise ValueError("Unlabelled observed candidate option")
    return result, {
        "years": ["2022", "2026"],
        "candidate_options": normalized_options,
        "municipalities": EXPECTED_MUNICIPALITIES,
        "municipalities_by_uf": dict(sorted(counts.items())),
        "electoral_panel_sha256": E005_SHA,
        "municipal_turnout_caveat_ibge": EXCEPTIONAL_AM_CODE,
        "scope": "Historical first-round aggregate voting and attendance; no forecasts",
        "source": "TSE first-round 2022 and 2026, official TSE-IBGE code crosswalk",
        "notes": [
            "Candidate vote shares use valid votes, not all eligible electors",
            "Municipality of polling is not necessarily municipality of residence",
            "2022 Amazonas turnout denominator exception may affect one municipal rate",
            "No individual preference inference, neighborhood allocation or campaign targeting",
        ],
    }


def _geometry_export(code: str, shape: object, name: str) -> dict:
    from shapely.geometry import mapping

    if shape is None or shape.is_empty or not shape.is_valid:
        raise ValueError(f"Invalid official polygon {code}")
    simplified = shape.simplify(
        DISPLAY_SIMPLIFICATION_DEGREES, preserve_topology=True
    )
    if simplified.is_empty or not simplified.is_valid:
        raise ValueError(f"Invalid display simplification for {code}")
    if simplified.geom_type not in ("Polygon", "MultiPolygon"):
        raise ValueError(f"Nonpolygon IBGE municipality geometry {code}")
    geom = mapping(simplified)
    return {
        "type": "Feature",
        "properties": {"ibge": code, "name": name},
        "geometry": geom,
    }


def normalize_geometries(gis: object, panel: dict) -> dict:
    """Demand exact municipal coverage; 2 extra IBGE operational features allowed."""
    if len(gis) != 5572:
        raise ValueError("IBGE geometry feature count mismatch")
    crs = getattr(gis, "crs", None)
    if crs is None or crs.to_epsg() != 4674:
        raise ValueError("Geometry must use original EPSG:4674")
    keys = [str(x) for x in gis["CD_MUN"]]
    if len(set(keys)) != len(keys):
        raise ValueError("Duplicate official geometry code")
    extra = set(keys) - set(panel)
    missing = set(panel) - set(keys)
    if extra != {"4300001", "4300002"} or missing:
        raise ValueError(f"Unreconciled official geographies: {extra=}, {missing=}")
    regions = {uf: [] for uf in sorted({r["uf"] for r in panel.values()})}
    for _, row in gis.iterrows():
        code = str(row["CD_MUN"])
        if code not in panel:
            continue
        uf = str(row["SIGLA_UF"])
        if uf != panel[code]["uf"]:
            raise ValueError(f"UF mismatch for {code}")
        name = str(row["NM_MUN"]).strip()
        if not name:
            raise ValueError(f"Empty municipality name: {code}")
        regions[uf].append(_geometry_export(code, row.geometry, name))
    if sum(len(x) for x in regions.values()) != EXPECTED_MUNICIPALITIES:
        raise ValueError("Missing municipality polygons in export")
    return regions


def create_site(panel: dict, gis: object, template_dir: Path, dest: Path, *, census_bytes: bytes | None = None, reports: Path | None = None) -> dict:
    """Fail closed before creating any public assets; no partial export."""
    if dest.exists():
        raise FileExistsError(f"Cannot overwrite published atlas directory: {dest}")
    rows, metadata = normalize_panel(panel)
    regions = normalize_geometries(gis, rows)
    if census_bytes is None or reports is None:
        raise ValueError('E012 requires frozen Census and scientific diagnostics')
    matches = matched_candidacies(metadata['candidate_options'])
    indicators, census_meta = census_indicators(census_bytes, rows)
    science = validation_diagnostics(reports)
    metadata['matched_candidate_labels'] = matches
    metadata['census'] = census_meta
    metadata['research_panel_version'] = 'E012'
    for asset in ("index.html", "app.js", "styles.css"):
        if not (template_dir / asset).is_file():
            raise ValueError(f"Missing static site template: {asset}")
    dest.mkdir(parents=True)
    for asset in ("index.html", "app.js", "styles.css"):
        shutil.copy2(template_dir / asset, dest / asset)
    _json_dump(dest / "data" / "municipalities.json", rows)
    _json_dump(dest / "data" / "metadata.json", metadata)
    _json_dump(dest / "data" / "census.json", indicators)
    _json_dump(dest / "data" / "research.json", science)
    for uf, features in regions.items():
        _json_dump(
            dest / "data" / "states" / f"{uf}.geojson",
            {"type": "FeatureCollection", "features": features},
        )
    files = sorted(path for path in dest.rglob("*") if path.is_file())
    size_bytes = sum(x.stat().st_size for x in files)
    manifest = {
        "municipalities": EXPECTED_MUNICIPALITIES,
        "uf_files": len(regions),
        "census_sha256": census_meta["sha256"],
        "matched_candidate_labels": len(matches),
        "research_version": "E012",
        "files": len(files),
        "bytes_total": size_bytes,
        "source_panel_sha256": E005_SHA,
        "geometry_zip_sha256": IBGE_GEOMETRY_SHA,
        "map_presentation_simplification_degrees": DISPLAY_SIMPLIFICATION_DEGREES,
        "note": "Geometry simplified for display only; not used in E008-E010 statistics",
    }
    _json_dump(dest / "data" / "manifest.json", manifest)
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--panel", type=Path, required=True)
    parser.add_argument("--geometry", type=Path, required=True)
    parser.add_argument("--census", type=Path, required=True)
    parser.add_argument("--reports", type=Path, default=Path("reports"))
    parser.add_argument("--template-dir", type=Path, default=Path("atlas/web"))
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    panel_bytes = args.panel.read_bytes()
    if hashlib.sha256(panel_bytes).hexdigest() != E005_SHA:
        raise ValueError("Unexpected E005 municipal panel SHA256")
    if hashlib.sha256(args.geometry.read_bytes()).hexdigest() != IBGE_GEOMETRY_SHA:
        raise ValueError("Unexpected IBGE 2022 municipal geometry SHA256")

    import pyogrio

    path = f"/vsizip/{args.geometry.resolve()}/BR_Municipios_2022.shp"
    gis = pyogrio.read_dataframe(path, columns=["CD_MUN", "NM_MUN", "SIGLA_UF"])
    panel = json.loads(panel_bytes)
    manifest = create_site(panel, gis, args.template_dir, args.out, census_bytes=args.census.read_bytes(), reports=args.reports)
    print(json.dumps(manifest, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
