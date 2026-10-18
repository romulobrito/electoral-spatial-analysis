import math

import pytest

from electoral_analysis.residual_diagnostics import STATE_REGION, study
from electoral_analysis.residual_figure import error_bars_svg, markdown_report


def example_rows():
    rows = []
    for index, uf in enumerate(sorted(STATE_REGION)):
        for j in range(12):
            p = 1200 + 310 * j + 37 * index
            turnout = 0.67 + 0.004 * j + 0.001 * index
            change = (j % 5 - 2) * 0.62 + index * 0.06
            rows.append({
                "uf": uf,
                "turnout_2022": turnout,
                "population_2022": p,
                "density_2022_km2": 8 + j * 10 + index * 3,
                "delta_turnout_pp": change,
                "incomplete_2022_denominator": index == 0 and j == 0,
            })
    return rows


def test_grouped_predictions_and_no_candidate_scores():
    report = study(example_rows(), samples=40)
    assert report["overall"]["municipalities"] == 323
    assert len(report["state_folds_alphabetical"]) == 27
    assert len(report["macrorregions_alphabetical"]) == 5
    assert math.isfinite(report["overall"]["ridge_mae_pp"])
    assert "turnout" in report["scope"].lower()
    assert "Moran" in report["eta_squared_definition"]


def test_bootstrap_and_svg_reproducible():
    a = study(example_rows(), samples=30, seed=11)
    b = study(example_rows(), samples=30, seed=11)
    assert a["state_cluster_bootstrap"] == b["state_cluster_bootstrap"]
    svg = error_bars_svg(a)
    assert svg.startswith("<svg")
    assert "<rect" in svg
    assert "macrorregião" in markdown_report(a)


def test_state_coverage_enforced():
    with pytest.raises(ValueError, match="27"):
        study([r for r in example_rows() if r["uf"] != "AC"], samples=30)


def test_bootstrap_minimum_enforced():
    with pytest.raises(ValueError, match="20"):
        study(example_rows(), samples=10)
