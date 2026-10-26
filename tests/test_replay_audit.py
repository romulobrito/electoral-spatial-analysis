"""Deterministic synthetic tests of E014 audit; NOT empirical election data."""
import csv

import pytest

from electoral_analysis.replay_audit import _bucket, _within_uf_moran, evaluate

FIELDS = [
    "election_id", "model_id", "metric_id", "unit_id", "uf",
    "snapshot_utc", "data_asof_utc", "progress_fraction",
    "estimate_pct", "lower95_pct", "upper95_pct", "source_sha256",
]


def fixture(tmp_path):
    pred = tmp_path / "pred.csv"
    truth = tmp_path / "truth.csv"
    edges = tmp_path / "edges.csv"
    with truth.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["election_id", "metric_id", "unit_id", "uf", "final_pct"])
        for elec in ("synthetic1", "synthetic2"):
            for i in range(4):
                w.writerow([elec, "neutral_metric", str(i), "SP", 45 + i])
    with pred.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(FIELDS)
        for elec in ("synthetic1", "synthetic2"):
            for minute, progress in (("00", .02), ("05", .1)):
                for method, error in (("reference", 1.4), ("variant", 0.7)):
                    for i in range(4):
                        estimate = 45 + i + (1 if i % 2 else -1) * error
                        w.writerow([elec, method, "neutral_metric", str(i), "SP",
                                    f"2026-10-25T20:{minute}:00Z",
                                    f"2026-10-25T19:{minute}:00Z",
                                    progress, estimate, estimate-3, estimate+3, "a"*64])
    with edges.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["unit_a", "unit_b"])
        for i in range(3):
            w.writerow([str(i), str(i+1)])
    return pred, truth, edges


def mutate(path, fn):
    with path.open(newline="") as f:
        rows = list(csv.DictReader(f))
    fn(rows)
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def test_synthetic_replay(tmp_path):
    pred, truth, edges = fixture(tmp_path)
    r = evaluate(pred, truth, reference="reference", edges=edges)
    assert r["counts"] == {"rows": 32, "elections": 2, "models": 2}
    assert len(r["summary"]) == 4
    assert len(r["paired_differences"]) == 2
    assert len(r["spatial_descriptive"]) == 8
    assert all(x["election_block_bootstrap_95ci_pp"] is None
               for x in r["paired_differences"])


def test_leakage_rejected(tmp_path):
    pred, truth, _ = fixture(tmp_path)
    mutate(pred, lambda rows: rows[0].update(
        data_asof_utc="2026-10-25T21:00:00Z"))
    with pytest.raises(ValueError, match="Future-data leakage"):
        evaluate(pred, truth)


def test_duplicate_rejected(tmp_path):
    pred, truth, _ = fixture(tmp_path)
    mutate(pred, lambda rows: rows[1].update(rows[0]))
    with pytest.raises(ValueError, match="Duplicate forecast snapshot"):
        evaluate(pred, truth)


def test_unmatched_truth_rejected(tmp_path):
    pred, truth, _ = fixture(tmp_path)
    mutate(pred, lambda rows: rows[0].update(unit_id="unknown"))
    with pytest.raises(ValueError, match="No compatible official final"):
        evaluate(pred, truth)


def test_incompatible_progress_rejected(tmp_path):
    pred, truth, _ = fixture(tmp_path)
    mutate(pred, lambda rows: next(
        r for r in rows if r["model_id"] == "variant"
    ).update(progress_fraction="0.03"))
    with pytest.raises(ValueError, match="Incomparable progress"):
        evaluate(pred, truth, reference="reference")


def test_progress_decrease_rejected(tmp_path):
    pred, truth, _ = fixture(tmp_path)
    mutate(pred, lambda rows: next(
        r for r in rows if r["snapshot_utc"].endswith("20:05:00Z")
    ).update(progress_fraction="0.005"))
    with pytest.raises(ValueError, match="Decreasing snapshot progress"):
        evaluate(pred, truth)


def test_interval_rejected(tmp_path):
    pred, truth, _ = fixture(tmp_path)
    mutate(pred, lambda rows: rows[0].update(
        lower95_pct="40", upper95_pct="41"))
    with pytest.raises(ValueError, match="interval does not contain"):
        evaluate(pred, truth)


def test_order_invariance(tmp_path):
    pred, truth, _ = fixture(tmp_path)
    a = evaluate(pred, truth, reference="reference")
    mutate(pred, lambda rows: rows.reverse())
    b = evaluate(pred, truth, reference="reference")
    assert a["summary"] == b["summary"]
    assert a["paired_differences"] == b["paired_differences"]


def test_bucket_and_spatial():
    assert _bucket(.02) == "1–2.5%"
    r = [{"unit_id": str(i), "uf": "SP", "residual_pp": float(i//2)}
         for i in range(6)]
    graph = [(str(i), str(i+1)) for i in range(5)]
    result = _within_uf_moran(r, graph)
    assert result["conditional_moran_I"] > 0
