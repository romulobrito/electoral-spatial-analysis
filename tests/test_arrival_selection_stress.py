"""Synthetic unit tests for reveal-order sensitivity; not election forecasts."""
import numpy as np
import pytest

from electoral_analysis.arrival_selection_stress import evaluate_path, order_paths


def fixture():
    return {
        "weight": np.array([10., 20., 30., 40., 50., 60.]),
        "historical": np.array([.6, .7, .8, .4, .5, .75]),
        "current": np.array([.65, .72, .78, .41, .53, .76]),
        "group": np.array([0, 0, 0, 1, 1, 1]),
        "code": np.array(["1", "2", "3", "4", "5", "6"]),
        "uf": np.array(["AA"] * 3 + ["BB"] * 3),
        "groups": ["AA", "BB"],
    }


def test_unrevealed_current_values_cannot_change_estimates():
    data = fixture()
    before = evaluate_path(data, list(range(6)), thresholds=(.08,))
    modified = fixture()
    modified["current"][2:] = .2
    after = evaluate_path(modified, list(range(6)), thresholds=(.08,))
    for a, b in zip(before, after):
        assert a["estimate_turnout_pct"] == pytest.approx(b["estimate_turnout_pct"])
        assert a["final_turnout_pct"] != pytest.approx(b["final_turnout_pct"])


def test_bad_order_rejected():
    with pytest.raises(ValueError, match="permutation"):
        evaluate_path(fixture(), [0, 0, 1, 2, 3, 4])


def test_seed_reproducibility_and_complete_permutations():
    data = fixture()
    a = list(order_paths(data, 2, 135))
    b = list(order_paths(data, 2, 135))
    assert a == b and len(a) == 9
    assert all(sorted(order) == list(range(6)) for _, _, order in a)


def test_historical_control_not_dependent_on_reveal_order():
    data = fixture()
    a = evaluate_path(data, list(range(6)), thresholds=(.15,))
    b = evaluate_path(data, list(reversed(range(6))), thresholds=(.15,))
    assert a[1]["method"] == "historical_2022"
    assert a[1]["estimate_turnout_pct"] == pytest.approx(b[1]["estimate_turnout_pct"])
