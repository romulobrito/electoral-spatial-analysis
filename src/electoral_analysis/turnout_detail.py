"""Audit official TSE detail-by-section archives across multiple state CSVs.

Aggregate only presidential records, never sum electors over other offices.
"""
from __future__ import annotations

import argparse
import csv
import io
import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from zipfile import ZipFile

from .acquisition import inventory_zip
from .etl import sha256_file

REQUIRED = {"ANO_ELEICAO", "NR_TURNO", "SG_UF", "CD_MUNICIPIO",
            "NR_ZONA", "NR_SECAO", "DS_CARGO", "QT_APTOS",
            "QT_COMPARECIMENTO", "QT_ABSTENCOES"}
COUNTS = ("QT_APTOS", "QT_COMPARECIMENTO", "QT_ABSTENCOES")


def audit_detail_archive(path: Path, year: int) -> dict:
    """Stream all archive CSVs; aggregate by TSE municipality with explicit integrity gates.

    Does not infer an IBGE municipality key or residential neighborhood.
    """
    members = [m["name"] for m in inventory_zip(path)
               if m["name"].lower().endswith(".csv")]
    if not members:
        raise ValueError("No CSV members in detail archive")
    seen: dict[tuple, tuple[int, int, int]] = {}
    duplicates = 0
    by_source = []
    nonconserving = 0
    discrepancy_samples = []
    with ZipFile(path) as z:
        for name in sorted(members):
            nrows = 0
            selected = 0
            with z.open(name) as binary, io.TextIOWrapper(
                binary, encoding="latin-1", newline=""
            ) as f:
                reader = csv.DictReader(f, delimiter=";")
                if reader.fieldnames is None:
                    raise ValueError(f"No header in {name}")
                reader.fieldnames = [v.strip().removeprefix("\ufeff") for v in reader.fieldnames]
                missing = REQUIRED - set(reader.fieldnames)
                if missing:
                    raise ValueError(f"{name}: missing {sorted(missing)}")
                for idx, row in enumerate(reader, 2):
                    nrows += 1
                    if row["DS_CARGO"].strip().casefold() != "presidente":
                        continue
                    selected += 1
                    try:
                        yr, turn = int(row["ANO_ELEICAO"]), int(row["NR_TURNO"])
                        counts = tuple(int(row[c]) for c in COUNTS)
                        identity = tuple(row[x].strip() for x in (
                            "SG_UF", "CD_MUNICIPIO", "NR_ZONA", "NR_SECAO"))
                    except (TypeError, ValueError) as e:
                        raise ValueError(f"{name}:{idx} invalid count/key") from e
                    if (yr != year or turn not in (1, 2) or
                            not all(identity) or min(counts) < 0):
                        raise ValueError(f"{name}:{idx} invalid year/turn/identity/count")
                    if counts[0] != counts[1] + counts[2]:
                        nonconserving += 1
                        if len(discrepancy_samples) < 50:
                            discrepancy_samples.append({"member": name, "line": idx,
                                                        "key": [turn, *identity],
                                                        "eligible": counts[0], "attended": counts[1],
                                                        "abstained": counts[2],
                                                        "difference": counts[0] - counts[1] - counts[2]})
                        continue
                    key = (turn, *identity)
                    previous = seen.get(key)
                    if previous is not None:
                        if previous != counts:
                            raise ValueError(f"{name}:{idx} inconsistent repeated section {key}")
                        duplicates += 1
                    else:
                        seen[key] = counts
            by_source.append({"member": name, "rows": nrows, "president_rows": selected})
    if not seen:
        raise ValueError("No presidential records")
    municipalities = defaultdict(lambda: [0, 0, 0, 0])
    totals = defaultdict(lambda: [0, 0, 0, 0])
    for (turn, uf, mun, _zone, _section), counts in seen.items():
        for target in (municipalities[(turn, uf, mun)], totals[turn]):
            target[0] += 1
            for i, value in enumerate(counts, 1):
                target[i] += value
    return {
        "year": year,
        "zip_sha256": sha256_file(path),
        "audited_at_utc": datetime.now(timezone.utc).isoformat(),
        "csv_members": len(members), "input_president_rows": sum(x["president_rows"] for x in by_source),
        "unique_presidential_sections": len(seen),
        "identical_duplicate_rows": duplicates,
        "quarantined_nonconserving_rows": nonconserving,
        "nonconserving_samples": discrepancy_samples,
        "counts_are_partial_if_quarantined": bool(nonconserving),
        "file_inventory": by_source,
        "national_by_round": [
            {"round": turn, "sections": v[0], "eligible": v[1],
             "attended": v[2], "abstained": v[3],
             "turnout_rate": v[2] / v[1] if v[1] else None}
            for turn, v in sorted(totals.items())
        ],
        "municipal_by_round": [
            {"round": turn, "uf": uf, "municipality_tse": mun,
             "sections": v[0], "eligible": v[1], "attended": v[2],
             "abstained": v[3], "turnout_rate": v[2] / v[1] if v[1] else None}
            for (turn, uf, mun), v in sorted(municipalities.items())
        ],
        "limitations": [
            "TSE municipality code is not an IBGE municipality code",
            "Section changes over elections preclude direct longitudinal section matching",
            "Polling-place neighborhood is not voter residential neighborhood",
            "Totals require comparison to official TSE final turnout publications",
        ],
    }


def comparable_municipal_changes(a: dict, b: dict) -> dict:
    """Descriptive 2022/2026 first-round differences for identical TSE UF+municipality keys.

    Repeated identities require manual verification of municipality crosswalk.
    """
    def index(report: dict) -> dict:
        return {(r["uf"], r["municipality_tse"]): r
                for r in report["municipal_by_round"] if r["round"] == 1}
    x, y = index(a), index(b)
    paired = []
    for key in sorted(x.keys() & y.keys()):
        before, after = x[key], y[key]
        paired.append({"uf": key[0], "municipality_tse": key[1],
                       "turnout_2022": before["turnout_rate"],
                       "turnout_2026": after["turnout_rate"],
                       "delta_turnout_pp": 100 * (after["turnout_rate"] - before["turnout_rate"])
                       if before["turnout_rate"] is not None and after["turnout_rate"] is not None
                       else None, "eligible_2022": before["eligible"],
                       "eligible_2026": after["eligible"]})
    return {"paired": len(paired), "2022_only": len(x.keys() - y.keys()),
            "2026_only": len(y.keys() - x.keys()),
            "key_assumption": "UF + TSE municipality ID stability; validate before scientific interpretation",
            "rows": paired}


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("archive", type=Path)
    p.add_argument("--year", type=int, choices=(2022, 2026), required=True)
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    if args.output.exists():
        p.error("Output already exists")
    result = audit_detail_archive(args.archive, args.year)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"year": args.year, "national_by_round": result["national_by_round"],
                      "municipalities": len(result["municipal_by_round"]),
                      "csv_members": result["csv_members"],
                      "duplicates": result["identical_duplicate_rows"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
