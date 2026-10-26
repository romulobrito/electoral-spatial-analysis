"""E015 leakage and fallback tests on synthetic municipality observations."""
import numpy as np
import pytest

from electoral_analysis.arrival_model_integration import extend_path, online_ridge


def fixture():
    n = 80
    h = np.linspace(.63, .83, n)
    uf = np.array(["SP"] * 40 + ["RJ"] * 40)
    pop = {
        "weight": np.ones(n) * 100,
        "historical": h,
        "current": np.clip(h + .02 - .05 * (h - .73), 0, 1),
        "group": np.array([0] * 40 + [1] * 40),
        "code": np.array([str(i) for i in range(n)]),
        "uf": uf, "groups": ["RJ", "SP"],
    }
    x = np.column_stack((
        h, np.log1p(np.arange(n) + 500),
        np.log1p((np.arange(n) % 17) + 3),
    ))
    return pop, x


def test_hidden_outcomes_do_not_change_estimates():
    pop, x = fixture()
    rows = extend_path(pop, x, list(range(80)), thresholds=(.25,))
    changed = {**pop, "current": pop["current"].copy()}
    changed["current"][20:] -= .1
    after = extend_path(changed, x, list(range(80)), thresholds=(.25,))
    for a, b in zip(rows, after):
        assert a["method"] == b["method"]
        assert a["estimate_turnout_pct"] == pytest.approx(b["estimate_turnout_pct"])
        assert a["final_turnout_pct"] != pytest.approx(b["final_turnout_pct"])


def test_early_fallback_reverts_to_national_swing():
    pop, x = fixture()
    rows = extend_path(pop, x, list(range(80)), thresholds=(.005,))
    national = next(
        r["estimate_turnout_pct"] for r in rows
        if r["method"] == "national_swing"
    )
    for row in rows:
        if row["method"].startswith(("e007", "e013")):
            assert row["estimate_turnout_pct"] == pytest.approx(national)
            assert "insufficient_training" in row["model_fallback"]


def test_training_normalization_excludes_hidden_features():
    pop, x = fixture()
    seen = np.arange(20)
    d = 100 * (pop["current"][seen] - pop["historical"][seen])
    before = online_ridge(x, seen, d, quadratic=True)[0]
    other = x.copy()
    other[40:] *= 1.4
    after = online_ridge(other, seen, d, quadratic=True)[0]
    assert before[:40] == pytest.approx(after[:40])


def test_bad_static_shape_rejected():
    pop, x = fixture()
    with pytest.raises(ValueError, match="Nx3"):
        extend_path(pop, x[:, :2], list(range(80)))
