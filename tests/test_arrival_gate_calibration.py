"""E017 leakage and split invariants on synthetic aggregate turnout."""
import numpy as np
import pytest

from electoral_analysis.arrival_gate_calibration import (
    extend_path,
    fold,
    select_policy,
)


def fixture():
    n = 80
    hist = np.linspace(.61, .84, n)
    pop = {
        "weight": np.full(n, 100.),
        "historical": hist,
        "current": hist + .02,
        "group": np.array([0] * 40 + [1] * 40),
        "code": np.array([str(i) for i in range(n)]),
        "uf": np.array(["SP"] * 40 + ["RJ"] * 40),
        "groups": ["RJ", "SP"],
    }
    x = np.column_stack((hist, np.log1p(np.arange(n) + 900),
                         np.log1p(np.arange(n) % 13 + 3)))
    return pop, x


def test_hidden_turnout_invariance():
    pop, x = fixture()
    first = extend_path(pop, x, list(range(80)), thresholds=(.25,))
    modified = {**pop, "current": pop["current"].copy()}
    modified["current"][20:] = .1
    second = extend_path(modified, x, list(range(80)), thresholds=(.25,))
    for a, b in zip(first, second):
        assert a["method"] == b["method"]
        assert a["estimate_turnout_pct"] == pytest.approx(b["estimate_turnout_pct"])


def test_path_folds_are_disjoint():
    assert [fold("uniform_municipality_random", i, 120)
            for i in (0, 59, 60, 119)] == [
                "development", "development", "evaluation", "evaluation"
            ]
    assert fold("states_in_blocks", 0, 120) == "adversarial_descriptive"


def test_selection_rejects_incomplete_balanced_development():
    with pytest.raises(ValueError, match="Missing predeclared"):
        select_policy([], 120)


def test_policy_methods_present():
    pop, x = fixture()
    rows = extend_path(pop, x, list(range(80)), thresholds=(.25,))
    names = {row["method"] for row in rows}
    assert "e017_permissive_quadratic" in names
    assert "e017_moderate_linear" in names
    assert "uf_shrunk_swing" in names
