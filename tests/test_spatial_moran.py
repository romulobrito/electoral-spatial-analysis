"""Synthetic graph checks; never use simulated data as electoral evidence."""
import pytest

from electoral_analysis.spatial_moran import moran_permutations, moran_statistic


def test_ring_alternating_signal_has_negative_moran():
    values = {"A": 1.0, "B": -1.0, "C": 1.0, "D": -1.0}
    edges = [["A", "B"], ["B", "C"], ["C", "D"], ["D", "A"]]
    result = moran_statistic(values, edges)
    assert result["I"] == pytest.approx(-1.0)
    assert result["connected_n"] == 4
    assert result["degrees"]["mean"] == 2.0


def test_isolates_are_explicitly_excluded():
    values = {"A": 1.0, "B": -1.0, "C": 2.0, "D": -2.0, "E": 100.0}
    edges = [["A", "B"], ["B", "C"], ["C", "D"]]
    r = moran_statistic(values, edges)
    assert r["connected_n"] == 4
    assert r["isolates_excluded"] == 1


def test_permutation_reproducibility_and_bounds():
    values = {"A": 1.0, "B": -1.0, "C": 1.0, "D": -1.0}
    edges = [["A", "B"], ["B", "C"], ["C", "D"], ["D", "A"]]
    a = moran_permutations(values, edges, permutations=39, seed=7)
    b = moran_permutations(values, edges, permutations=39, seed=7)
    assert a == b
    assert 0 < a["two_sided_permutation_p"] <= 1
    assert a["null_interval_95pct"][0] <= a["null_interval_95pct"][1]


def test_invalid_edges_and_low_variance_rejected():
    values = {"A": 1.0, "B": 1.0, "C": 1.0, "D": 1.0}
    edges = [["A", "B"], ["B", "C"], ["C", "D"]]
    with pytest.raises(ValueError, match="No variance"):
        moran_statistic(values, edges)
    with pytest.raises(ValueError, match="Self edge"):
        moran_statistic(values, edges + [["A", "A"]])
    with pytest.raises(ValueError, match="missing"):
        moran_statistic({"A": 1, "B": 2, "C": 3, "D": 4}, edges + [["X", "B"]])


def test_minimum_permutations():
    values = {"A": 1, "B": 2, "C": 3, "D": 4}
    edges = [["A", "B"], ["B", "C"], ["C", "D"]]
    with pytest.raises(ValueError, match="at least"):
        moran_permutations(values, edges, permutations=10)
