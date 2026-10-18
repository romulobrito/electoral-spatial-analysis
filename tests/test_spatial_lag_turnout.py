"""Deterministic synthetic examples. These are not empirical election results."""
import math

import pytest

from electoral_analysis.spatial_lag_turnout import (
    _covariates,
    fit_ridge4,
    historical_neighbor_features,
    within_uf_moran_for_models,
)


def fixture(n=16):
    data = []
    for i in range(n):
        data.append({
            "ibge": f"{i:07d}",
            "turnout_2022": 0.65 + 0.011 * i,
            "population_2022": 800 + 530 * i,
            "density_2022_km2": 12 + i*i,
            "delta_turnout_pp": 2 - i * .09 + (i % 3) * .25,
            "uf": "SP",
        })
    return data


def test_neighbor_mean_uses_only_2022_data_and_isolates():
    rows = fixture(4)
    edges = [[rows[0]["ibge"], rows[1]["ibge"]],
             [rows[1]["ibge"], rows[2]["ibge"]]]
    features, summary = historical_neighbor_features(rows, edges)
    assert features[rows[1]["ibge"]]["neighbor_turnout_2022"] == pytest.approx(
        (rows[0]["turnout_2022"] + rows[2]["turnout_2022"]) / 2
    )
    assert features[rows[3]["ibge"]]["neighbor_turnout_2022"] == rows[3]["turnout_2022"]
    assert summary["isolate_count"] == 1
    assert not summary["uses_2026_outcomes"]
    # Changing 2026 election outcome must never alter a historical graph feature.
    rows[0]["delta_turnout_pp"] += 100
    updated, _ = historical_neighbor_features(rows, edges)
    assert updated == features


def test_spatial_ridge_training_does_not_inspect_test_outcomes():
    data = fixture()
    edges = [[data[i]["ibge"], data[i+1]["ibge"]] for i in range(len(data)-1)]
    history, _ = historical_neighbor_features(data, edges)
    first = fit_ridge4(data[:12], history)
    predicted = first(data[15])
    assert math.isfinite(predicted)
    data[15]["delta_turnout_pp"] += 10000
    second = fit_ridge4(data[:12], history)
    assert second(data[15]) == pytest.approx(predicted)


def test_reject_unrecognized_or_self_contiguity():
    rows = fixture(4)
    with pytest.raises(ValueError, match="Unknown or self-linked"):
        historical_neighbor_features(rows, [[rows[0]["ibge"], "NOT-A-MUNICIPALITY"]])
    with pytest.raises(ValueError, match="Unknown or self-linked"):
        historical_neighbor_features(rows, [[rows[0]["ibge"], rows[0]["ibge"]]])


def test_feature_contract_and_training_only_covariates():
    data = fixture()
    edges = [[data[i]["ibge"], data[i+1]["ibge"]] for i in range(len(data)-1)]
    history, _ = historical_neighbor_features(data, edges)
    x = _covariates(data[7], history)
    assert len(x) == 4
    assert x[0] == data[7]["turnout_2022"]
    assert x[1] == pytest.approx(math.log1p(data[7]["population_2022"]))
    assert x[3] == history[data[7]["ibge"]]["neighbor_turnout_2022"]


def test_conditional_residual_diagnostics_use_only_error_vectors():
    data = fixture(8)
    residuals = {
        row["ibge"]: {
            "uf": "SP",
            "baseline": float(i) - 2.0,
            "ridge": float(i) / 2 - 2.0,
            "ridge_regional": float(i) / 2 - 1.5,
            "spatial_queen": (-1)**i + 0.1*i,
            "spatial_rook": (-1)**i + 0.1*i,
        } for i, row in enumerate(data)
    }
    edges = [[data[i]["ibge"], data[i+1]["ibge"]] for i in range(len(data)-1)]
    graphs = {"queen": {"edges": edges}, "rook": {"edges": edges}}
    result = within_uf_moran_for_models(residuals, graphs, permutations=99)
    assert result["queen"]["connected_nodes"] == 8
    assert result["rook"]["spatial_ridge"]["two_sided_permutation_p"] > 0
    assert result["rook"]["regional_ridge"]["conditional_I"] == pytest.approx(
        result["rook"]["ordinary_ridge"]["conditional_I"]
    )
