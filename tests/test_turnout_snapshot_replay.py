"""Synthetic-only normalized snapshot audit tests."""
import hashlib

import pytest

from electoral_analysis.turnout_snapshot_replay import replay


def event(unit="A", generated="2026-10-25T19:00:00Z",
          received="2026-10-25T19:01:00Z", sections=1, eligible=100,
          attended=75, raw="snapshot1"):
    return {
        "election_id": "test-2026-round-2",
        "unit_id": unit,
        "source_generated_utc": generated,
        "received_utc": received,
        "generation": __import__("datetime").datetime.fromisoformat(
            generated.replace("Z", "+00:00")
        ),
        "arrival": __import__("datetime").datetime.fromisoformat(
            received.replace("Z", "+00:00")
        ),
        "reported_sections": sections, "total_sections": 3,
        "eligible_reported": eligible, "attended_reported": attended,
        "source_sha256": hashlib.sha256(raw.encode()).hexdigest(),
    }


def test_idempotent_retry():
    a = event()
    assert len(replay([a, a])) == 1


def test_late_stale_snapshot_cannot_rollback():
    a = event()
    newer = event(generated="2026-10-25T19:02:00Z",
                  received="2026-10-25T19:03:00Z",
                  sections=2, eligible=200, attended=150, raw="new")
    stale = event(received="2026-10-25T19:04:00Z", raw="late")
    assert replay([a, newer, stale])[-1]["reported_sections"] == 2


def test_conflicting_same_generation_is_rejected():
    with pytest.raises(ValueError, match="Conflicting"):
        replay([event(), event(raw="other", received="2026-10-25T19:04:00Z")])


def test_section_progress_may_not_decrease():
    a = event(sections=2, eligible=200, attended=150)
    b = event(generated="2026-10-25T19:02:00Z",
              received="2026-10-25T19:03:00Z",
              raw="newer", sections=1, eligible=100, attended=70)
    with pytest.raises(ValueError, match="decreased"):
        replay([a, b])


def test_parallel_units_combine_without_overwrite():
    a, b = event(), event(unit="B", raw="B")
    r = replay([a, b])
    assert r[-1]["attended_in_reported_sections"] == 150
    assert r[-1]["reported_sections"] == 2
