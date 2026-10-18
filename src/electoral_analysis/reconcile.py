"""Reconcile TSE eligible/attendance totals against independently audited vote totals.

This module operates on aggregate, already-audited JSON; raw data are untouched.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

# Source: TSE totalization (2022) and 2026 portal note on temporary transfers.
BENCHMARKS = {
    2022: {"eligible": 156454011, "temporary_transfer_adjustment": 0,
           "attended": {1: 123682372, 2: 124252796}},
    2026: {"eligible": 158745463, "temporary_transfer_adjustment": 39,
           "attended": {1: 125275835}},
}


def reconcile(report: dict) -> dict:
    year = report["year"]
    if year not in BENCHMARKS:
        raise ValueError("Unsupported election year")
    benchmark = BENCHMARKS[year]
    results = []
    for row in report["national_by_round"]:
        turn = row["round"]
        extra = [r for r in report["exceptional_by_round_uf"] if r["round"] == turn]
        exceptional_eligible = sum(r["eligible"] for r in extra)
        exceptional_attended = sum(r["attended"] for r in extra)
        exceptional_abstained = sum(r["abstained"] for r in extra)
        if exceptional_attended != 0 or exceptional_abstained != 0:
            raise ValueError("Unexpected exceptional attendance/abstention; manual review required")
        raw_eligible = row["eligible"] + exceptional_eligible
        effective_eligible = raw_eligible - benchmark["temporary_transfer_adjustment"]
        expected_attended = benchmark["attended"].get(turn)
        if expected_attended is None:
            raise ValueError("No independent voting tally benchmark")
        checks = {
            "eligible_matches_official": effective_eligible == benchmark["eligible"],
            "attendance_matches_independent_voting": row["attended"] == expected_attended,
            "valid_adjusted_denominator": 0 <= row["attended"] <= effective_eligible,
        }
        results.append({
            "round": turn, "accepted_eligible": row["eligible"],
            "exceptional_eligible_unique": exceptional_eligible,
            "raw_eligible": raw_eligible,
            "temporary_transfer_adjustment": benchmark["temporary_transfer_adjustment"],
            "effective_eligible": effective_eligible,
            "attended": row["attended"], "implied_abstentions": effective_eligible-row["attended"],
            "turnout_rate_reconciled": row["attended"]/effective_eligible,
            "checks": checks, "all_checks_pass": all(checks.values()),
        })
    return {"year": year, "rounds": results, "all_checks_pass": all(
        x["all_checks_pass"] for x in results
    ), "note": "2026 TTE adjustment is explicit and sourced; exceptional sections are counted once only."}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("year_2022", type=Path)
    parser.add_argument("year_2026", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    reports = [json.loads(p.read_text(encoding="utf-8"))
               for p in (args.year_2022, args.year_2026)]
    results = [reconcile(r) for r in reports]
    args.out.parent.mkdir(parents=True, exist_ok=True)
    if args.out.exists():
        parser.error("Output already exists")
    args.out.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(json.dumps(results, ensure_ascii=False))
    if not all(r["all_checks_pass"] for r in results):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
