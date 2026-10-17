"""Minimal, auditable ingestion utilities for official election CSV files."""
from __future__ import annotations

import csv
import hashlib
from pathlib import Path


def sha256_file(path: str | Path) -> str:
    """Compute content fingerprint in streaming mode."""
    h = hashlib.sha256()
    with Path(path).open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def inspect_csv(path: str | Path, required_columns: set[str], *, delimiter: str = ";", encoding: str = "latin-1") -> dict:
    """Check header and file readability; does not claim schema harmonization."""
    path = Path(path)
    with path.open("r", encoding=encoding, newline="") as handle:
        reader = csv.DictReader(handle, delimiter=delimiter)
        if reader.fieldnames is None:
            raise ValueError("CSV has no header")
        missing = required_columns - set(reader.fieldnames)
        if missing:
            raise ValueError(f"Missing columns: {sorted(missing)}")
        rows = sum(1 for _ in reader)
    return {"file": path.name, "rows": rows, "columns": list(reader.fieldnames), "sha256": sha256_file(path)}


def turnout_rate(voters: int, eligible: int) -> float:
    """Proportion of voters; input totals must be consistent."""
    if eligible <= 0 or not (0 <= voters <= eligible):
        raise ValueError("Invalid counts for turnout")
    return voters / eligible
