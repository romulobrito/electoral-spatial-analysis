"""E018: replay audited aggregate-turnout snapshots in received-time order.

Ingests normalized records, not assumed undocumented TSE JSON formats.
No candidate shares, race forecasts, or fabricated official timestamps.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path


REQUIRED = (
    "election_id", "unit_id", "source_generated_utc", "received_utc",
    "reported_sections", "total_sections", "eligible_reported",
    "attended_reported", "source_sha256",
)


def utc(s: str) -> datetime:
    if not s.endswith("Z"):
        raise ValueError("UTC timestamp must have Z suffix")
    date = datetime.fromisoformat(s.replace("Z", "+00:00"))
    if date.utcoffset() != timezone.utc.utcoffset(date):
        raise ValueError("Timestamp is not UTC")
    return date


def load_events(path: Path) -> list[dict]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if tuple(reader.fieldnames or ()) != REQUIRED:
            raise ValueError(f"Exact columns required: {REQUIRED}")
        records = list(reader)
    if not records:
        raise ValueError("No snapshots")
    for rec in records:
        if not rec["election_id"] or not rec["unit_id"]:
            raise ValueError("Missing election or unit identifier")
        rec["generation"] = utc(rec["source_generated_utc"])
        rec["arrival"] = utc(rec["received_utc"])
        if rec["generation"] > rec["arrival"]:
            raise ValueError("Future source generation time relative to receipt")
        for key in ("reported_sections", "total_sections",
                    "eligible_reported", "attended_reported"):
            rec[key] = int(rec[key])
        if not (0 <= rec["reported_sections"] <= rec["total_sections"]
                and rec["total_sections"] > 0):
            raise ValueError("Invalid section progress")
        if not (0 <= rec["attended_reported"] <= rec["eligible_reported"]):
            raise ValueError("Invalid turnout counts")
        digest = rec["source_sha256"].lower()
        if len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
            raise ValueError("Invalid source SHA256")
        rec["source_sha256"] = digest
    return records


def replay(events: list[dict]) -> list[dict]:
    """Retain one latest accepted state per election/unit.

    Identical repeated content is idempotent. Older generated snapshots that
    arrive late do not roll back progress; same-timestamp conflicting versions
    and decreases in counts fail closed. Later corrected turnout may decrease,
    but not section count or eligible electorate.
    """
    state = {}
    accepted = []
    ordered = sorted(events, key=lambda r: (r["arrival"], r["generation"], r["unit_id"]))
    for rec in ordered:
        key = (rec["election_id"], rec["unit_id"])
        previous = state.get(key)
        if previous is not None:
            if rec["source_sha256"] == previous["source_sha256"]:
                continue
            if rec["generation"] < previous["generation"]:
                continue
            if rec["generation"] == previous["generation"]:
                raise ValueError(f"Conflicting version at same source time: {key}")
            if rec["total_sections"] != previous["total_sections"]:
                raise ValueError("Total section denominator changed")
            if rec["reported_sections"] < previous["reported_sections"]:
                raise ValueError("Reported sections decreased")
            if rec["eligible_reported"] < previous["eligible_reported"]:
                raise ValueError("Eligible electorate in revealed sections decreased")
        state[key] = rec
        relevant = [v for (eid, _), v in state.items() if eid == key[0]]
        attended = sum(v["attended_reported"] for v in relevant)
        eligible = sum(v["eligible_reported"] for v in relevant)
        reports = sum(v["reported_sections"] for v in relevant)
        sections = sum(v["total_sections"] for v in relevant)
        accepted.append({
            "election_id": key[0], "received_utc": rec["received_utc"],
            "source_generated_utc": rec["source_generated_utc"],
            "unit_updated": key[1], "source_sha256": rec["source_sha256"],
            "units_observed": len(relevant), "reported_sections": reports,
            "total_sections_in_units": sections,
            "section_coverage_pct": 100 * reports / sections,
            "eligible_in_reported_sections": eligible,
            "attended_in_reported_sections": attended,
            "observed_turnout_pct": 100 * attended / eligible if eligible else None,
            "provisional": True,
        })
    return accepted


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--events", type=Path, required=True)
    p.add_argument("--out-dir", type=Path, required=True)
    args = p.parse_args()
    if args.out_dir.exists():
        p.error("Will not overwrite existing results")
    input_bytes = args.events.read_bytes()
    rows = replay(load_events(args.events))
    args.out_dir.mkdir(parents=True)
    (args.out_dir / "metadata.json").write_text(json.dumps({
        "stage": "E018", "source_csv_sha256": hashlib.sha256(input_bytes).hexdigest(),
        "received_events": len(rows), "source_type": "normalized_snapshots",
        "scope": "observed neutral aggregate participation, no outcome forecasting",
        "warning": "observed partial turnout is selection-biased; no national turnout forecast",
    }, indent=2) + "\n", encoding="utf-8")
    with (args.out_dir / "replay.csv").open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    print(json.dumps({"stage": "E018", "accepted": len(rows)}))


if __name__ == "__main__":
    main()
