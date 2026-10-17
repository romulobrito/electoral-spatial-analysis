"""Stream ZIP CSVs to audit municipal turnout. No voter-level analysis."""
from __future__ import annotations

import csv
import io
from collections import defaultdict
from pathlib import Path
from zipfile import ZipFile

from .acquisition import inventory_zip

FIELDS = {"NR_TURNO", "SG_UF", "CD_MUNICIPIO", "NR_ZONA", "NR_SECAO",
          "QT_APTOS", "QT_COMPARECIMENTO", "QT_ABSTENCOES"}


def _int(value: str, name: str, row: int) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError) as error:
        raise ValueError(f"Invalid integer field {name} at row {row}") from error
    if number < 0:
        raise ValueError(f"Negative field {name} at row {row}")
    return number


def audit_turnout_csv(stream, *, year: int, max_rows: int | None = None) -> dict:
    """Deduplicate section totals and reject conflicting counts.

    Outcome is section-level turnout, not the sum of candidate records.
    Historical comparisons require a verified geographic crosswalk.
    """
    reader = csv.DictReader(stream, delimiter=";")
    if not reader.fieldnames:
        raise ValueError("Missing CSV header")
    reader.fieldnames = [x.removeprefix("\ufeff").strip() for x in reader.fieldnames]
    missing = sorted(FIELDS - set(reader.fieldnames))
    if missing:
        raise ValueError(f"Missing required section-detail columns: {missing}")
    if not {"DS_CARGO", "DS_CARGO_PERGUNTA"} & set(reader.fieldnames):
        raise ValueError("Cannot verify presidential contest: cargo column is absent")
    observed: dict[tuple, tuple[int, int, int]] = {}
    repeats = 0
    processed = 0
    for row_number, row in enumerate(reader, start=2):
        if max_rows is not None and processed >= max_rows:
            break
        processed += 1
        cargo = (row.get("DS_CARGO") or row.get("DS_CARGO_PERGUNTA") or "").strip().casefold()
        if not cargo:
            raise ValueError(f"Empty contest field at row {row_number}")
        if cargo != "presidente":
            continue
        if not all(row.get(field, "").strip() for field in FIELDS):
            raise ValueError(f"Empty identity/count field at row {row_number}")
        key = (str(year), row["NR_TURNO"].strip(), row["SG_UF"].strip(),
               row["CD_MUNICIPIO"].strip(), row["NR_ZONA"].strip(), row["NR_SECAO"].strip())
        counts = tuple(_int(row[name].strip(), name, row_number) for name in
                       ("QT_APTOS", "QT_COMPARECIMENTO", "QT_ABSTENCOES"))
        if counts[0] != counts[1] + counts[2]:
            raise ValueError(f"Section totals do not reconcile at row {row_number}: {counts}")
        if key in observed:
            if observed[key] != counts:
                raise ValueError(f"Conflicting totals for electoral section {key} at row {row_number}")
            repeats += 1
        else:
            observed[key] = counts
    if not observed:
        raise ValueError("No presidential sections found; check contest coding and input")
    grouped = defaultdict(lambda: [0, 0, 0, 0])
    for key, counts in observed.items():
        group = (key[1], key[2], key[3])
        totals = grouped[group]
        totals[0] += 1
        for index, value in enumerate(counts, start=1):
            totals[index] += value
    municipalities = [{"year": year, "round": turn, "uf": uf, "municipality_tse": mun,
                       "sections": vals[0], "eligible": vals[1], "attended": vals[2],
                       "abstained": vals[3], "turnout_rate": vals[2] / vals[1] if vals[1] else None}
                      for (turn, uf, mun), vals in sorted(grouped.items())]
    return {"year": year, "input_rows": processed, "unique_president_sections": len(observed),
            "duplicate_section_rows": repeats, "is_partial": max_rows is not None,
            "municipality_round_groups": len(municipalities), "municipalities": municipalities}


def audit_turnout_zip(zip_path: str | Path, *, year: int, member_name: str | None = None,
                      max_rows: int | None = None) -> dict:
    path = Path(zip_path)
    inventory = inventory_zip(path)
    members = [obj["name"] for obj in inventory if obj["name"].lower().endswith(".csv")]
    if member_name is None:
        if len(members) != 1:
            raise ValueError("Archive has multiple/no CSVs; specify --member explicitly")
        member_name = members[0]
    if member_name not in members:
        raise ValueError("Selected CSV member not found")
    with ZipFile(path) as archive, archive.open(member_name) as binary:
        with io.TextIOWrapper(binary, encoding="latin-1", newline="") as handle:
            result = audit_turnout_csv(handle, year=year, max_rows=max_rows)
    return {"source_zip": path.name, "csv_member": member_name, **result}
