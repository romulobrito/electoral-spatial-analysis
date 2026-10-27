"""Synthetic municipal TSE EA20 tests; not historical election-night files."""
import json
from datetime import datetime, timezone

import pytest

from electoral_analysis.municipal_ea20_replay import municipal_url, normalize, replay


def fixture(code="01392", attended="75", sa="1"):
    return json.dumps({
        "ele": "6258", "tpabr": "mu", "cdabr": code,
        "dg": "25/10/2026", "hg": "19:00:00",
        "carg": [{"cd": "1"}], "s": {"sa": sa, "ts": "4"},
        "e": {"esa": "100", "c": attended},
    }).encode()


def test_official_path_and_scope():
    assert municipal_url(6258, "AC", "01392").endswith(
        "/ac/ac01392-c0001-e006258-u.json"
    )
    assert normalize(
        fixture(), election=6258, uf="AC", code="01392",
        received=datetime(2026, 10, 25, 23, tzinfo=timezone.utc),
    )["attended_reported"] == 75


def test_reject_municipal_mismatch():
    with pytest.raises(ValueError, match="municipal identification"):
        normalize(
            fixture(), election=6258, uf="AC", code="01393",
            received=datetime(2026, 10, 25, 23, tzinfo=timezone.utc),
        )


def test_no_double_count_on_revision():
    base = dict(election_id="6258", uf="AC", municipality_tse="01392",
                total_sections=4)
    a = {**base, "generated_utc": "2026-10-25T22:00:00Z",
         "received_utc": "2026-10-25T22:01:00Z", "sha256": "a",
         "reported_sections": 1, "eligible_reported": 100,
         "attended_reported": 75}
    b = {**a, "generated_utc": "2026-10-25T22:02:00Z",
         "received_utc": "2026-10-25T22:03:00Z", "sha256": "b",
         "reported_sections": 2, "eligible_reported": 200,
         "attended_reported": 155}
    c = {**a, "municipality_tse": "01393", "sha256": "c",
         "received_utc": "2026-10-25T22:04:00Z"}
    result = replay([a, b, c])
    assert result[-1]["attended_in_reported_sections"] == 230
    assert result[-1]["municipalities_seen"] == 2
    assert len(replay([a, a])) == 1


def test_reject_forged_progress():
    row = dict(election_id="6258", uf="AC", municipality_tse="01392",
               total_sections=4, reported_sections=2,
               eligible_reported=200, attended_reported=150,
               generated_utc="2026-10-25T22:00:00Z",
               received_utc="2026-10-25T22:01:00Z", sha256="a")
    newer = {**row, "reported_sections": 1,
             "generated_utc": "2026-10-25T22:02:00Z",
             "received_utc": "2026-10-25T22:03:00Z", "sha256": "b"}
    with pytest.raises(ValueError, match="regressed"):
        replay([row, newer])
