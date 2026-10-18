"""Observed, non-targeted municipal presidential vote and turnout summaries."""
from __future__ import annotations

import argparse
import csv
import io
import json
import math
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from zipfile import ZipFile

from .etl import sha256_file
from .municipal_crosswalk import normalize_tse_code, read_crosswalk_zip

COLUMNS = {"ANO_ELEICAO", "NR_TURNO", "SG_UF", "CD_MUNICIPIO", "DS_CARGO", "NR_VOTAVEL", "NM_VOTAVEL", "QT_VOTOS"}
EXPECTED_FIRST_ROUND = {
    2022: {"valid": 118229719, "blank": 1964779, "null": 3487874},
    2026: {"valid": 119306034, "blank": 2300798, "null": 3669003},
}


def aggregate_first_round_zip(path: Path, year: int) -> dict:
    """Aggregate all candidate options and vote types; reject inconsistent source snapshots."""
    if year not in EXPECTED_FIRST_ROUND:
        raise ValueError("Unsupported first-round election year")
    groups = defaultdict(lambda: {"categories": Counter(), "options": Counter()})
    national = Counter()
    option_names = defaultdict(set)
    records = selected = 0
    with ZipFile(path) as archive:
        members = [name for name in archive.namelist() if name.lower().endswith(".csv")]
        if len(members) != 1:
            raise ValueError(f"Expected single national CSV, found: {members}")
        with (archive.open(members[0]) as raw,
              io.TextIOWrapper(raw, encoding="latin-1", newline="") as stream):
            reader = csv.DictReader(stream, delimiter=";")
            if not reader.fieldnames or COLUMNS - set(reader.fieldnames):
                raise ValueError("Incomplete TSE vote-by-section CSV schema")
            for number, row in enumerate(reader, 2):
                records += 1
                if row["DS_CARGO"].strip().casefold() != "presidente" or row["NR_TURNO"].strip() != "1":
                    continue
                selected += 1
                try:
                    if int(row["ANO_ELEICAO"]) != year:
                        raise ValueError("Unexpected year")
                    votes = int(row["QT_VOTOS"])
                    option = int(row["NR_VOTAVEL"])
                    municipality = normalize_tse_code(row["CD_MUNICIPIO"])
                    if votes < 0:
                        raise ValueError("Negative votes")
                except (ValueError, TypeError) as error:
                    raise ValueError(f"Invalid election field at row {number}") from error
                uf = row["SG_UF"].strip().upper()
                if len(uf) != 2:
                    raise ValueError(f"Invalid UF at row {number}")
                category = ("blank" if option == 95 else "null" if option == 96 else
                            "valid" if 10 <= option <= 89 else "other")
                group = groups[(uf, municipality)]
                group["categories"][category] += votes
                national[category] += votes
                if category == "valid":
                    group["options"][option] += votes
                    option_names[option].add(row["NM_VOTAVEL"].strip())
    if not selected:
        raise ValueError("No presidential first-round records")
    comparisons = {
        key: {"observed": national[key], "expected": value,
              "difference": national[key] - value, "pass": national[key] == value}
        for key, value in EXPECTED_FIRST_ROUND[year].items()
    }
    if national["other"]:
        raise ValueError(f"Unclassified options: {national['other']}")
    if not all(check["pass"] for check in comparisons.values()):
        raise ValueError(f"National tally differs from audited snapshot: {comparisons}")
    return {
        "year": year, "zip_sha256": sha256_file(path), "csv_member": members[0],
        "input_records": records, "president_first_round_records": selected,
        "national": dict(national), "national_checks": comparisons,
        "candidate_option_names": {str(k): sorted(v) for k, v in sorted(option_names.items())},
        "municipalities": [
            {"uf": uf, "tse_code": tse, "valid": value["categories"]["valid"],
             "blank": value["categories"]["blank"], "null": value["categories"]["null"],
             "other": value["categories"]["other"],
             "candidate_votes": {
                 str(option): votes for option, votes in sorted(value["options"].items())
             }}
            for (uf, tse), value in sorted(groups.items())
        ],
    }


def make_descriptive_panel(v2022: dict, v2026: dict, crosswalk: dict,
                           t2022: dict, t2026: dict) -> dict:
    """Return observed all-candidate shares, never a propensity or targeting score."""
    if crosswalk["inconsistencies"]:
        raise ValueError("Crosswalk ambiguities must be resolved")
    mapper = crosswalk["map"]

    def indexed_votes(report):
        indexed, unmapped = {}, []
        for row in report["municipalities"]:
            if row["uf"] == "ZZ":
                continue
            ibge = mapper.get((row["uf"], normalize_tse_code(row["tse_code"])))
            if not ibge:
                unmapped.append({"uf": row["uf"], "tse_code": row["tse_code"]})
                continue
            key = (row["uf"], ibge)
            if key in indexed:
                raise ValueError(f"Multiple TSE codes for IBGE municipality {key}")
            indexed[key] = row
        return indexed, unmapped

    def indexed_turnout(report):
        indexed = {}
        for row in report["municipal_by_round"]:
            if row["round"] != 1 or row["uf"] == "ZZ":
                continue
            ibge = mapper.get((row["uf"], normalize_tse_code(row["municipality_tse"])))
            if ibge:
                key = (row["uf"], ibge)
                if key in indexed:
                    raise ValueError(f"Duplicate municipality turnout record {key}")
                indexed[key] = row
        return indexed

    old, missing_old = indexed_votes(v2022)
    new, missing_new = indexed_votes(v2026)
    turnout_old, turnout_new = indexed_turnout(t2022), indexed_turnout(t2026)
    available = old.keys() & new.keys() & turnout_old.keys() & turnout_new.keys()
    rows, mismatches = [], []
    for uf, ibge in sorted(available):
        a, b = old[(uf, ibge)], new[(uf, ibge)]
        ta, tb = turnout_old[(uf, ibge)], turnout_new[(uf, ibge)]
        for year, votes, turnout in ((2022, a, ta), (2026, b, tb)):
            ballots = votes["valid"] + votes["blank"] + votes["null"] + votes["other"]
            if ballots != turnout["attended"]:
                mismatches.append({"uf": uf, "ibge": ibge, "year": year,
                                   "ballots": ballots, "attendance": turnout["attended"]})

        def year_row(votes, turnout):
            valid = votes["valid"]
            return {
                "valid": valid, "blank": votes["blank"], "null": votes["null"],
                "eligible_conserving_sections": turnout["eligible"],
                "attended": turnout["attended"], "turnout_rate": turnout["turnout_rate"],
                "candidates": {
                    code: {"votes": count, "valid_share": count / valid if valid else None}
                    for code, count in votes["candidate_votes"].items()
                },
            }

        rows.append({"uf": uf, "municipality_ibge": ibge,
                     "2022": year_row(a, ta), "2026": year_row(b, tb)})
    if mismatches:
        raise ValueError(f"Vote/turnout municipal totals disagree: {mismatches[:5]}")
    return {
        "scope": "Observed first-round municipal results, not individual preferences or forecasts",
        "candidate_options": {
            "2022": v2022["candidate_option_names"],
            "2026": v2026["candidate_option_names"],
        },
        "matched_municipalities": len(rows),
        "not_paired_2022": len(old.keys() - new.keys()),
        "not_paired_2026": len(new.keys() - old.keys()),
        "unmapped_vote_geographies": {"2022": missing_old, "2026": missing_new},
        "missing_turnout_geographies": {
            "2022": len((old.keys() & new.keys()) - turnout_old.keys()),
            "2026": len((old.keys() & new.keys()) - turnout_new.keys()),
        },
        "source_hashes": {
            "voting_2022": v2022["zip_sha256"], "voting_2026": v2026["zip_sha256"],
            "turnout_2022": t2022["zip_sha256"], "turnout_2026": t2026["zip_sha256"],
        },
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "caveats": [
            "2022 Amazonas exceptional section not allocated to local conserving-section denominator",
            "Observed municipal candidate shares do not identify individual preferences",
            "Polling place is not a proxy for residential neighborhood",
            "Different candidate lists across elections do not identify individual voter transitions",
        ],
        "municipalities": rows,
    }


def summarize_turnout_baseline(panel: dict) -> dict:
    """Use 2022 observed municipal turnout as simple 2026 retrospective baseline."""
    points = [
        (r["2022"]["turnout_rate"], r["2026"]["turnout_rate"],
         min(r["2022"]["eligible_conserving_sections"],
             r["2026"]["eligible_conserving_sections"]))
        for r in panel["municipalities"]
        if r["2022"]["turnout_rate"] is not None and r["2026"]["turnout_rate"] is not None
    ]
    if not points:
        raise ValueError("No comparable positive-denominator municipalities")
    n = len(points)
    errors = [abs((b - a) * 100) for a, b, _ in points]
    weights = [w for _, _, w in points]
    total_weight = sum(weights)
    if not total_weight:
        raise ValueError("No positive eligible population")
    return {
        "baseline": "2026 municipal turnout estimate = 2022 observed rate",
        "scope": "Retrospective aggregate participation evaluation, not candidate forecast",
        "municipalities": n,
        "mae_pp": sum(errors) / n,
        "rmse_pp": math.sqrt(sum(e * e for e in errors) / n),
        "weighted_mae_pp": sum(e * w for e, w in zip(errors, weights)) / total_weight,
        "mean_difference_pp": sum((b - a) * 100 for a, b, _ in points) / n,
        "validation": "Simple temporal baseline; no spatial generalization claim",
    }


def main() -> int:
    p = argparse.ArgumentParser()
    for name in ("votes-2022", "votes-2026", "detail-2022", "detail-2026", "crosswalk"):
        p.add_argument("--" + name, type=Path, required=True)
    p.add_argument("--output-dir", type=Path, required=True)
    args = p.parse_args()
    out = args.output_dir
    if out.exists():
        p.error("Output directory already exists")
    v22 = aggregate_first_round_zip(args.votes_2022, 2022)
    v26 = aggregate_first_round_zip(args.votes_2026, 2026)
    cw = read_crosswalk_zip(args.crosswalk)
    t22 = json.loads(args.detail_2022.read_text(encoding="utf-8"))
    t26 = json.loads(args.detail_2026.read_text(encoding="utf-8"))
    panel = make_descriptive_panel(v22, v26, cw, t22, t26)
    baseline = summarize_turnout_baseline(panel)
    out.mkdir(parents=True)
    (out / "municipal_results.json").write_text(
        json.dumps(panel, ensure_ascii=False, indent=2), encoding="utf-8")
    summary = {
        "years": {
            str(year): {k: v[k] for k in (
                "national", "national_checks", "candidate_option_names", "zip_sha256"
            )} for year, v in ((2022, v22), (2026, v26))
        },
        "paired_municipalities": panel["matched_municipalities"],
        "unpaired_2022": panel["not_paired_2022"],
        "unpaired_2026": panel["not_paired_2026"],
        "turnout_baseline": baseline, "caveats": panel["caveats"],
    }
    (out / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
