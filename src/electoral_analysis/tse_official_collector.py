"""E019: audited polling of official TSE EA20 national JSON (2026).

One poll is the default. This is not a historical real-time replay unless the
collector was genuinely running and archiving each source response at the time.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo

from .turnout_snapshot_replay import REQUIRED, load_events, replay

ALLOWED_ELECTIONS = (6257, 6258)
BASE = "https://resultados.tse.jus.br"
MAX_BYTES = 2_000_000
BRASILIA = ZoneInfo("America/Sao_Paulo")


def official_url(election: int) -> str:
    if type(election) is not int or election not in ALLOWED_ELECTIONS:
        raise ValueError("E019 supports only 2026 federal elections 6257 and 6258")
    return (f"{BASE}/oficial/ele2026/{election}/dados/br/"
            f"br-c0001-e{election:06d}-u.json")


def _number(value: object, name: str) -> int:
    if value in (None, ""):
        return 0
    if not isinstance(value, (int, str)) or isinstance(value, bool):
        raise TypeError(f"Invalid {name}")
    s = str(value)
    if not s.isdecimal():
        raise ValueError(f"Noninteger {name}: {s!r}")
    return int(s)


def normalize(raw: bytes, election: int, received_utc: datetime) -> dict:
    """EA20 BR president => one cumulative, national E018 turnout observation."""
    if len(raw) > MAX_BYTES:
        raise ValueError("EA20 payload exceeds size cap")
    if received_utc.tzinfo is None or received_utc.utcoffset() is None:
        raise ValueError("Receipt timestamp must be timezone-aware")
    source = json.loads(raw)
    if not isinstance(source, dict):
        raise TypeError("EA20 root must be an object")
    if (source.get("ele") != str(election)
            or source.get("tpabr") != "br" or source.get("cdabr") != "br"):
        raise ValueError("Incorrect election or geographic scope")
    offices = source.get("carg")
    if not isinstance(offices, list) or not any(
        isinstance(c, dict) and c.get("cd") == "1" for c in offices
    ):
        raise ValueError("Missing presidential EA20 cargo")
    try:
        generated_local = datetime.strptime(
            f'{source["dg"]} {source["hg"]}', "%d/%m/%Y %H:%M:%S"
        ).replace(tzinfo=BRASILIA)
        generated = generated_local.astimezone(timezone.utc)
        sections = source["s"]
        voters = source["e"]
        counted = _number(sections["sa"], "s.sa")
        total = _number(sections["ts"], "s.ts")
        eligible = _number(voters["esa"], "e.esa")
        attended = _number(voters["c"], "e.c")
    except (KeyError, TypeError) as exc:
        raise ValueError("EA20 turnout/coverage schema mismatch") from exc
    if generated > received_utc.astimezone(timezone.utc):
        raise ValueError("Source generation timestamp is later than receipt")
    if total < 1 or not 0 <= counted <= total:
        raise ValueError("Invalid TSE section counts")
    if not 0 <= attended <= eligible:
        raise ValueError("Invalid TSE attendance/registered-elector counts")
    if counted == 0 and (eligible or attended):
        raise ValueError("Nonzero turnout with no counted sections")
    iso = lambda d: d.astimezone(timezone.utc).isoformat(timespec="seconds").replace(
        "+00:00", "Z"
    )
    return {
        "election_id": str(election),
        "unit_id": "BR",
        "source_generated_utc": iso(generated),
        "received_utc": iso(received_utc),
        "reported_sections": counted,
        "total_sections": total,
        "eligible_reported": eligible,
        "attended_reported": attended,
        "source_sha256": hashlib.sha256(raw).hexdigest(),
        "source_idg": str(source.get("idg", "")),
    }


def http_fetch(url: str, headers: dict) -> tuple[int, bytes, dict, str]:
    """Bounded HTTP fetch with conditional caching. No arbitrary source URLs."""
    request = urllib.request.Request(
        url, headers={"User-Agent": "electoral-spatial-analysis-e019/0.1",
                      "Accept": "application/json", **headers}
    )
    try:
        response = urllib.request.urlopen(request, timeout=25)
    except urllib.error.HTTPError as exc:
        if exc.code == 304:
            return 304, b"", dict(exc.headers), exc.geturl()
        raise
    with response:
        status = response.status
        body = response.read(MAX_BYTES + 1)
        if len(body) > MAX_BYTES:
            raise ValueError("Official source response too large")
        return status, body, dict(response.headers), response.geturl()


def journal(archive: Path) -> list[dict]:
    path = archive / "polls.jsonl"
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip()]


def poll_once(
    archive: Path, election: int, *,
    fetch=http_fetch, now=None,
) -> dict:
    """Content-addressed raw snapshots plus append-only receipt-time journal."""
    url = official_url(election)
    archive.mkdir(parents=True, exist_ok=True)
    lock = archive / ".e019.lock"
    try:
        fd = os.open(lock, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError as exc:
        raise RuntimeError("Archive is being written by another process") from exc
    os.close(fd)
    try:
        prior = journal(archive)
        previous = next(
            (rec for rec in reversed(prior)
             if rec.get("election_id") == str(election)
             and rec.get("status") in ("new", "duplicate")), None
        )
        headers = {}
        if previous:
            if previous.get("etag"):
                headers["If-None-Match"] = previous["etag"]
            if previous.get("last_modified"):
                headers["If-Modified-Since"] = previous["last_modified"]
        status, raw, meta, final_url = fetch(url, headers)
        expected = urlsplit(url)
        final = urlsplit(final_url)
        if final.scheme != "https" or final.hostname != expected.hostname:
            raise ValueError("Unexpected origin/redirect from TSE source")
        received = now or datetime.now(timezone.utc)
        if received.tzinfo is None:
            raise ValueError("Received timestamp must be timezone-aware")
        stamp = received.astimezone(timezone.utc).isoformat(
            timespec="seconds"
        ).replace("+00:00", "Z")
        if status == 304:
            if previous is None:
                raise ValueError("304 without prior verified snapshot")
            entry = {
                "status": "not_modified", "election_id": str(election),
                "received_utc": stamp, "source_url": url,
                "source_sha256": previous["source_sha256"],
            }
        elif status == 200:
            normalized = normalize(raw, election, received)
            digest = normalized["source_sha256"]
            raw_dir = archive / "raw"
            raw_dir.mkdir(exist_ok=True)
            destination = raw_dir / f"{digest}.json"
            if destination.exists():
                if hashlib.sha256(destination.read_bytes()).hexdigest() != digest:
                    raise ValueError("Immutable raw archive was modified")
            else:
                with destination.open("xb") as output:
                    output.write(raw)
                    output.flush()
                    os.fsync(output.fileno())
            entry = {
                "status": "duplicate" if any(
                    x.get("source_sha256") == digest
                    and x.get("election_id") == str(election)
                    and x.get("status") in ("new", "duplicate")
                    for x in prior
                ) else "new",
                "election_id": str(election), "received_utc": stamp,
                "source_url": url, "source_sha256": digest,
                "source_idg": normalized["source_idg"],
                "etag": meta.get("ETag", meta.get("Etag")),
                "last_modified": meta.get("Last-Modified"),
                "normalized": {
                    k: normalized[k] for k in REQUIRED
                },
            }
        else:
            raise ValueError(f"Unexpected upstream HTTP status {status}")
        line = json.dumps(entry, ensure_ascii=False, sort_keys=True) + "\n"
        with (archive / "polls.jsonl").open("a", encoding="utf-8") as file:
            file.write(line)
            file.flush()
            os.fsync(file.fileno())
        return entry
    finally:
        lock.unlink(missing_ok=True)


def export_replay(archive: Path, path: Path) -> dict:
    """Independently hash-check raw bytes before applying E018 replay."""
    events = []
    seen = set()
    for rec in journal(archive):
        if rec["status"] not in ("new", "duplicate"):
            continue
        digest = rec["source_sha256"]
        if (rec["election_id"], digest) in seen:
            continue
        raw = (archive / "raw" / f"{digest}.json").read_bytes()
        if hashlib.sha256(raw).hexdigest() != digest:
            raise ValueError("Archived TSE source bytes do not match SHA256")
        normalized = normalize(raw, int(rec["election_id"]), datetime.fromisoformat(
            rec["received_utc"].replace("Z", "+00:00")
        ))
        if {k: normalized[k] for k in REQUIRED} != rec["normalized"]:
            raise ValueError("Archived normalized record does not match raw JSON")
        seen.add((rec["election_id"], digest))
        events.append(rec["normalized"])
    if not events:
        raise ValueError("No real EA20 200 responses to export")
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        raise FileExistsError("Refusing to overwrite exported event CSV")
    with path.open("x", encoding="utf-8", newline="") as output:
        writer = csv.DictWriter(output, fieldnames=REQUIRED)
        writer.writeheader()
        writer.writerows(events)
    reviewed = replay(load_events(path))
    return {"source_snapshots": len(events), "replay_events": len(reviewed),
            "last_record": reviewed[-1]}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--election", type=int, choices=ALLOWED_ELECTIONS,
                        default=6258)
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--export", type=Path, required=True)
    parser.add_argument("--max-polls", type=int, default=1)
    parser.add_argument("--poll-seconds", type=int, default=60)
    args = parser.parse_args()
    if not 1 <= args.max_polls <= 200:
        parser.error("max-polls must be 1..200")
    if args.max_polls > 1 and args.poll_seconds < 30:
        parser.error("Minimum 30 seconds between upstream polls")
    for index in range(args.max_polls):
        print(json.dumps(poll_once(args.archive, args.election), ensure_ascii=False))
        if index < args.max_polls - 1:
            time.sleep(args.poll_seconds)
    print(json.dumps(export_replay(args.archive, args.export), ensure_ascii=False))


if __name__ == "__main__":
    main()
