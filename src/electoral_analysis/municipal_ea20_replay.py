"""E020 municipality cumulative EA20 processing, neutral aggregate turnout only."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

TSE_BASE = "https://resultados.tse.jus.br"
FIELDS = (
    "election_id", "uf", "municipality_tse", "generated_utc",
    "received_utc", "reported_sections", "total_sections",
    "eligible_reported", "attended_reported", "sha256",
)


def municipal_url(election: int, uf: str, code: str) -> str:
    if election not in (6257, 6258) or not isinstance(election, int):
        raise ValueError("Invalid federal 2026 election")
    if not re.fullmatch(r"[A-Z]{2}", uf) or not re.fullmatch(r"\d{5}", code):
        raise ValueError("Invalid UF or municipality TSE code")
    lower = uf.lower()
    return (f"{TSE_BASE}/oficial/ele2026/{election}/dados/{lower}/"
            f"{lower}{code}-c0001-e{election:06d}-u.json")


def normalize(raw: bytes, *, election: int, uf: str, code: str,
              received: datetime) -> dict:
    if len(raw) > 2_000_000:
        raise ValueError("Oversize source")
    obj = json.loads(raw)
    if not isinstance(obj, dict):
        raise TypeError("Expected JSON object")
    if obj.get("ele") != str(election) or obj.get("tpabr") != "mu":
        raise ValueError("Wrong election or municipal scope")
    if str(obj.get("cdabr")) != code:
        raise ValueError("Wrong municipal identification")
    if not isinstance(obj.get("carg"), list) or not any(
        isinstance(c, dict) and str(c.get("cd")) == "1"
        for c in obj["carg"]
    ):
        raise ValueError("Missing presidential contest")
    if received.tzinfo is None or received.utcoffset() is None:
        raise ValueError("Naive receipt time")
    source_time = datetime.strptime(
        f'{obj["dg"]} {obj["hg"]}', "%d/%m/%Y %H:%M:%S"
    ).replace(tzinfo=ZoneInfo("America/Sao_Paulo")).astimezone(timezone.utc)
    if source_time > received.astimezone(timezone.utc):
        raise ValueError("Generation later than receipt")
    sec = obj["s"]
    electors = obj["e"]
    sa, ts = int(sec["sa"]), int(sec["ts"])
    esa, attended = int(electors["esa"]), int(electors["c"])
    if ts <= 0 or not 0 <= sa <= ts or not 0 <= attended <= esa:
        raise ValueError("Invalid reported section or turnout counters")
    if sa == 0 and (esa or attended):
        raise ValueError("Nonzero electorate in zero reported sections")
    stamp = lambda d: d.astimezone(timezone.utc).isoformat(timespec="seconds").replace(
        "+00:00", "Z"
    )
    return dict(zip(FIELDS, (
        str(election), uf, code, stamp(source_time), stamp(received),
        sa, ts, esa, attended, hashlib.sha256(raw).hexdigest()
    )))


def replay(records: list[dict]) -> list[dict]:
    """One latest snapshot per municipality. Never combine UF/national totals."""
    latest = {}
    result = []
    for row in sorted(records, key=lambda r: (r["received_utc"], r["generated_utc"])):
        key = (row["election_id"], row["uf"], row["municipality_tse"])
        previous = latest.get(key)
        if previous:
            if row["sha256"] == previous["sha256"]:
                continue
            if row["generated_utc"] < previous["generated_utc"]:
                continue
            if row["generated_utc"] == previous["generated_utc"]:
                raise ValueError("Conflicting snapshots with identical source time")
            if row["reported_sections"] < previous["reported_sections"]:
                raise ValueError("Reported sections regressed")
            if row["total_sections"] != previous["total_sections"]:
                raise ValueError("Unexpected total-sections revision")
            if row["eligible_reported"] < previous["eligible_reported"]:
                raise ValueError("Reported electorate regressed")
        latest[key] = row
        group = [r for k, r in latest.items() if k[0] == row["election_id"]]
        attended = sum(r["attended_reported"] for r in group)
        eligible = sum(r["eligible_reported"] for r in group)
        counted = sum(r["reported_sections"] for r in group)
        total = sum(r["total_sections"] for r in group)
        result.append({
            "received_utc": row["received_utc"], "election_id": row["election_id"],
            "municipality_updated": row["municipality_tse"],
            "municipalities_seen": len(group), "reported_sections": counted,
            "total_sections_in_observed_municipalities": total,
            "reported_section_coverage_pct": 100 * counted / total,
            "eligible_in_reported_sections": eligible,
            "attended_in_reported_sections": attended,
            "observed_turnout_pct": 100 * attended / eligible if eligible else None,
        })
    return result


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--json-events", type=Path, required=True,
                   help="JSONL of raw EA20 file path, election, UF, TSE code, receipt UTC")
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    if args.output.exists():
        p.error("Will not overwrite experiment")
    normalized = []
    for line in args.json_events.read_text(encoding="utf-8").splitlines():
        event = json.loads(line)
        received = datetime.fromisoformat(event["received_utc"].replace("Z", "+00:00"))
        normalized.append(normalize(
            Path(event["raw_path"]).read_bytes(),
            election=int(event["election_id"]), uf=event["uf"],
            code=event["municipality_tse"], received=received,
        ))
    records = replay(normalized)
    if not records:
        raise ValueError("Empty replay")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", newline="", encoding="utf-8") as out:
        writer = csv.DictWriter(out, fieldnames=list(records[0]))
        writer.writeheader()
        writer.writerows(records)
    print(json.dumps({"stage": "E020", "accepted": len(records)}))


if __name__ == "__main__":
    main()
