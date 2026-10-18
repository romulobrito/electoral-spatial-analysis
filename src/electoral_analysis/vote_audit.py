"""Stream aggregate presidential voting results from official TSE ZIPs; no turnout inference."""
from __future__ import annotations

import argparse
import csv
import io
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from zipfile import ZipFile

from .acquisition import inventory_zip
from .etl import sha256_file

REQUIRED = {
    "ANO_ELEICAO", "NR_TURNO", "SG_UF", "CD_MUNICIPIO", "NR_ZONA",
    "NR_SECAO", "DS_CARGO", "NR_VOTAVEL", "NM_VOTAVEL", "QT_VOTOS",
}
# TSE special-vote codes; other special codes remain unclassified.
REFERENCE_2022 = {
    1: {"valid": 118229719, "blank": 1964779, "null": 3487874},
    2: {"valid": 118552353, "blank": 1769678, "null": 3930765},
}


def vote_category(number: str) -> str:
    code = int(number)
    if code == 95:
        return "blank"
    if code == 96:
        return "null"
    if 10 <= code <= 89:
        return "valid"
    return "unclassified"


def audit_csv(stream: io.TextIOBase, *, year: int) -> dict:
    reader = csv.DictReader(stream, delimiter=";")
    if not reader.fieldnames:
        raise ValueError("CSV header missing")
    reader.fieldnames = [c.strip().removeprefix("\ufeff") for c in reader.fieldnames]
    missing = sorted(REQUIRED.difference(reader.fieldnames))
    if missing:
        raise ValueError(f"Missing required vote columns: {missing}")
    totals = defaultdict(Counter)
    state_totals = defaultdict(Counter)
    candidates = Counter()
    unclassified = Counter()
    labels = defaultdict(set)
    sections = set()
    input_rows, excluded_other_office = 0, 0
    for number, row in enumerate(reader, 2):
        input_rows += 1
        if row["DS_CARGO"].strip().casefold() != "presidente":
            excluded_other_office += 1
            continue
        try:
            row_year = int(row["ANO_ELEICAO"])
            turn = int(row["NR_TURNO"])
            votes = int(row["QT_VOTOS"])
            option = str(int(row["NR_VOTAVEL"]))
        except (ValueError, TypeError) as error:
            raise ValueError(f"Invalid numeric field at row {number}") from error
        if row_year != year or turn not in (1, 2) or votes < 0:
            raise ValueError(f"Invalid year, round or count at row {number}")
        geography = tuple(row[k].strip() for k in (
            "SG_UF", "CD_MUNICIPIO", "NR_ZONA", "NR_SECAO"
        ))
        if not all(geography):
            raise ValueError(f"Empty geographic key at row {number}")
        sections.add((turn, *geography))
        category = vote_category(option)
        name = row["NM_VOTAVEL"].strip()
        totals[turn][category] += votes
        state_totals[(turn, geography[0])][category] += votes
        candidates[(turn, option, name, category)] += votes
        labels[(turn, option)].add(name)
        if category == "unclassified":
            unclassified[(turn, option, name)] += votes
    if not totals:
        raise ValueError("No presidential rows")
    cats = ("valid", "blank", "null", "unclassified")
    return {
        "year": year,
        "input_rows": input_rows,
        "filtered_other_cargo_rows": excluded_other_office,
        "unique_presidential_sections_over_rounds": len(sections),
        "rounds": [
            {"round": turn, **{k: totals[turn][k] for k in cats},
             "counted_votes": sum(totals[turn].values())}
            for turn in sorted(totals)
        ],
        "candidates_and_vote_options": [
            {"round": turn, "vote_option": code, "name": name,
             "category": cat, "votes": qty}
            for (turn, code, name, cat), qty in sorted(candidates.items())
        ],
        "state_aggregates": [
            {"round": turn, "uf": uf, **{k: vals[k] for k in cats}}
            for (turn, uf), vals in sorted(state_totals.items())
        ],
        "unclassified_options": [
            {"round": turn, "vote_option": code, "name": name, "votes": qty}
            for (turn, code, name), qty in sorted(unclassified.items())
        ],
        "diagnostics": {"vote_option_name_variants": [
            {"round": turn, "vote_option": code, "labels": sorted(values)}
            for (turn, code), values in sorted(labels.items()) if len(values) > 1
        ]},
        "metric_scope": "voting tallies only; no eligible-voter or turnout counts",
    }


def add_reference_audit(result: dict) -> dict:
    if result["year"] == 2022:
        checks = []
        for values in result["rounds"]:
            turn = values["round"]
            for cat in ("valid", "blank", "null"):
                expected = REFERENCE_2022.get(turn, {}).get(cat)
                checks.append({
                    "round": turn, "category": cat, "observed": values[cat],
                    "reference": expected, "difference": (
                        values[cat] - expected if expected is not None else None
                    ),
                    "matches": values[cat] == expected if expected is not None else None,
                })
        result["reference"] = {"kind": "2022 final TSE publication", "comparisons": checks}
    elif result["year"] == 2026:
        result["reference"] = {
            "kind": "TSE 2026-10-05 publication (99.99% sections; interim)",
            "published_as_valid": 125272513,
            "published_blank": 2300781,
            "published_null": 3674149,
            "comparable": False,
            "notice": "The published 125272513 'valid' quantity closely resembles total counted votes, not candidate-valid votes in this ZIP. Treat reference as semantically inconsistent pending clarification; never use as valid-vote reconciliation.",
            "source": "https://www.tse.jus.br/comunicacao/noticias/2026/Outubro/flavio-bolsonaro-e-lula-vao-disputar-o-2o-turno-para-a-presidencia-da-republica",
        }
    return result


def audit_zip(path: Path, *, year: int) -> dict:
    members = [m["name"] for m in inventory_zip(path)
               if m["name"].lower().endswith(".csv")]
    if len(members) != 1:
        raise ValueError(f"Ambiguous CSV members: {members}")
    with (ZipFile(path) as archive, archive.open(members[0]) as binary,
          io.TextIOWrapper(binary, encoding="latin-1", newline="") as stream):
        result = audit_csv(stream, year=year)
    result.update({
        "input_file": path.name, "csv_member": members[0],
        "sha256": sha256_file(path), "zip_bytes": path.stat().st_size,
        "audited_at_utc": datetime.now(timezone.utc).isoformat(),
    })
    return add_reference_audit(result)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("zip_file", type=Path)
    parser.add_argument("--year", type=int, choices=(2022, 2026), required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if args.out.exists():
        parser.error("Report already exists; select a new versioned path")
    result = audit_zip(args.zip_file, year=args.year)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: result[k] for k in (
        "year", "input_rows", "unique_presidential_sections_over_rounds",
        "rounds", "sha256", "reference"
    )}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
