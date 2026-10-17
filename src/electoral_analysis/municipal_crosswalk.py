"""Strict official TSE–IBGE municipality code mapping for aggregate data."""
from __future__ import annotations

import csv
import io
import json
from collections import Counter
from pathlib import Path
from zipfile import ZipFile

REQUIRED = {"SG_UF", "CD_MUNICIPIO_TSE", "CD_MUNICIPIO_IBGE"}


def normalize_tse_code(value: str) -> str:
    """Canonical numeric identity with padded official TSE display variants."""
    value = value.strip()
    if not value.isdecimal():
        raise ValueError(f"Invalid TSE code: {value!r}")
    return str(int(value))


def read_crosswalk_zip(path: Path) -> dict:
    mapping: dict[tuple[str, str], str] = {}
    inconsistencies: list[dict] = []
    duplicates = 0
    with ZipFile(path) as archive:
        members = [x for x in archive.namelist() if x.lower().endswith(".csv")]
        if members != ["municipio_tse_ibge.csv"]:
            raise ValueError(f"Unexpected official CSV members: {members}")
        with archive.open(members[0]) as raw, io.TextIOWrapper(
            raw, encoding="latin-1", newline=""
        ) as stream:
            reader = csv.DictReader(stream, delimiter=";")
            if not reader.fieldnames or REQUIRED - set(reader.fieldnames):
                raise ValueError("Official municipality crosswalk lacks required fields")
            for record in reader:
                uf = record["SG_UF"].strip().upper()
                tse = normalize_tse_code(record["CD_MUNICIPIO_TSE"])
                ibge = record["CD_MUNICIPIO_IBGE"].strip()
                if not (len(uf) == 2 and ibge.isdecimal() and len(ibge) == 7):
                    inconsistencies.append({"uf": uf, "tse": tse, "ibge": ibge})
                    continue
                key = (uf, tse)
                if key in mapping:
                    if mapping[key] != ibge:
                        inconsistencies.append({"uf": uf, "tse": tse, "ibge": ibge,
                                                "previous": mapping[key]})
                    duplicates += 1
                else:
                    mapping[key] = ibge
    return {"map": mapping, "duplicates": duplicates, "inconsistencies": inconsistencies}


def build_comparison(a: dict, b: dict, crosswalk: dict) -> dict:
    """Only report municipalities with exact unique mapping in both elections."""
    table = crosswalk["map"]
    def index(report: dict) -> tuple[dict, list]:
        result, missing = {}, []
        for row in report["municipal_by_round"]:
            if row["round"] != 1 or row["uf"] == "ZZ":
                continue
            key = (row["uf"], normalize_tse_code(row["municipality_tse"]))
            ibge = table.get(key)
            if not ibge:
                missing.append({"uf": row["uf"], "tse": key[1]})
                continue
            pair = (row["uf"], ibge)
            if pair in result:
                raise ValueError(f"Many-to-one TSE/IBGE collision: {pair}")
            result[pair] = row
        return result, missing
    old, missing_old = index(a)
    new, missing_new = index(b)
    matched = []
    for key in sorted(old.keys() & new.keys()):
        first, second = old[key], new[key]
        matched.append({
            "uf": key[0], "municipality_ibge": key[1],
            "eligible_2022": first["eligible"], "eligible_2026": second["eligible"],
            "attended_2022": first["attended"], "attended_2026": second["attended"],
            "turnout_2022": first["turnout_rate"], "turnout_2026": second["turnout_rate"],
            "delta_turnout_pp": 100 * (second["turnout_rate"]-first["turnout_rate"])
            if first["turnout_rate"] is not None and second["turnout_rate"] is not None else None,
        })
    return {
        "status": "provisional pending municipality-level exceptional denominator allocation",
        "matched": len(matched), "only_2022": len(old.keys()-new.keys()),
        "only_2026": len(new.keys()-old.keys()),
        "unmapped_2022": missing_old, "unmapped_2026": missing_new,
        "crosswalk_inconsistencies": crosswalk["inconsistencies"],
        "crosswalk_duplicate_rows": crosswalk["duplicates"],
        "rows": matched,
    }


def main() -> int:
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("crosswalk_zip", type=Path)
    parser.add_argument("turnout_2022", type=Path)
    parser.add_argument("turnout_2026", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    cw = read_crosswalk_zip(args.crosswalk_zip)
    if cw["inconsistencies"]:
        raise ValueError("Official crosswalk has ambiguous or invalid rows")
    a = json.loads(args.turnout_2022.read_text(encoding="utf-8"))
    b = json.loads(args.turnout_2026.read_text(encoding="utf-8"))
    result = build_comparison(a, b, cw)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    if args.out.exists():
        parser.error("Refusing to overwrite existing analysis")
    args.out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({k: v for k, v in result.items() if k != "rows"}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
