"""E019 synthetic EA20 fixtures and audited-archive behavior."""
import hashlib
import json
from datetime import datetime, timezone

import pytest

from electoral_analysis.tse_official_collector import (
    export_replay,
    normalize,
    official_url,
    poll_once,
)

T = datetime(2026, 10, 26, 3, 0, tzinfo=timezone.utc)


def fixture(sa=2, eligible=200, attended=153, hour="23:27:02"):
    return json.dumps({
        "ele": "6258", "tpabr": "br", "cdabr": "br", "dg": "25/10/2026",
        "hg": hour, "idg": "4241309",
        "carg": [{"cd": "1"}], "s": {"ts": "4", "sa": str(sa)},
        "e": {"esa": str(eligible), "c": str(attended)},
    }).encode()


def test_ea20_normalization_and_exact_url():
    d = normalize(fixture(), 6258, T)
    assert d["reported_sections"] == 2
    assert d["attended_reported"] == 153
    assert d["source_generated_utc"] == "2026-10-26T02:27:02Z"
    assert official_url(6258).endswith("br-c0001-e006258-u.json")


def test_wrong_election_fails_closed():
    with pytest.raises(ValueError, match="Incorrect election"):
        normalize(fixture(), 6257, T)


def test_future_generated_timestamp_rejected():
    with pytest.raises(ValueError, match="later than receipt"):
        normalize(fixture(), 6258, datetime(2026, 10, 25, 23, 0,
                                             tzinfo=timezone.utc))


def test_poll_raw_archive_idempotent_304_and_replay(tmp_path):
    calls = []

    def fake(url, headers):
        calls.append(dict(headers))
        if len(calls) == 1:
            return 200, fixture(), {"ETag": '"ver-a"'}, url
        return 304, b"", {}, url

    first = poll_once(tmp_path, 6258, fetch=fake, now=T)
    second = poll_once(tmp_path, 6258, fetch=fake, now=T)
    assert first["status"] == "new"
    assert second["status"] == "not_modified"
    assert calls[1]["If-None-Match"] == '"ver-a"'
    assert len(list((tmp_path / "raw").glob("*.json"))) == 1
    stats = export_replay(tmp_path, tmp_path / "events.csv")
    assert stats["replay_events"] == 1


def test_tampered_source_rejected(tmp_path):
    def fake(url, headers):
        return 200, fixture(), {}, url

    rec = poll_once(tmp_path, 6258, fetch=fake, now=T)
    (tmp_path / "raw" / (rec["source_sha256"] + ".json")).write_text("{}")
    with pytest.raises(ValueError, match="SHA256"):
        export_replay(tmp_path, tmp_path / "tampered.csv")


def test_redirect_off_origin_rejected(tmp_path):
    with pytest.raises(ValueError, match="Unexpected origin"):
        poll_once(tmp_path, 6258,
                  fetch=lambda url, headers:
                  (200, fixture(), {}, "https://example.invalid/data.json"),
                  now=T)


def test_exact_digest_of_archived_bytes():
    raw = fixture()
    assert normalize(raw, 6258, T)["source_sha256"] == hashlib.sha256(raw).hexdigest()
