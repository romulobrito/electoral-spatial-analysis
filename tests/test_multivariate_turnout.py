"""Synthetic tests for E013 inference and leakage safeguards."""
import numpy as np
import pytest

from electoral_analysis.multivariate_turnout import (
    fixed_design,
    predictors,
    state_cluster_ci,
    train_predict,
)


def rows():
    return [
        {"uf": "AA" if i < 14 else "BB", "ibge": f"{i:07d}",
         "turnout_2022": 0.5 + i * 0.009,
         "population_2022": 100 + 17 * i,
         "density_2022_km2": 3 + i * i,
         "delta_turnout_pp": 2 + np.sin(i) * 0.4 + (i % 3) * 0.11}
        for i in range(28)
    ]


def test_standardization_uses_training_only():
    train=np.array([[1.,2.,3.],[3.,4.,5.],[5.,8.,11.],
                    [7.,6.,8.],[9.,10.,15.]])
    test=np.array([[100.,200.,300.]])
    a,b=fixed_design(train,test,quadratic=True)
    assert np.allclose(a.mean(axis=0),0,atol=1e-10)
    assert not np.allclose(b[0],0)
    assert a.shape[1] == 6


def test_heldout_2026_target_not_used_in_prediction():
    panel=rows()
    train,test=panel[:20],panel[20:]
    before=train_predict(train,test,quadratic=True)
    for item in test:
        item["delta_turnout_pp"] += 1000
    after=train_predict(train,test,quadratic=True)
    assert np.allclose(before,after)
    assert predictors(test[0]).shape == (3,)


def test_cluster_interval_invariant_to_input_order():
    records={
        f"{i:03d}":{"uf":"AA" if i<8 else "BB","quadratic":float(i%3),
                    "ridge_regional":float(i%5)}
        for i in range(16)
    }
    a=state_cluster_ci(records,"quadratic",replicates=40)
    b=state_cluster_ci(dict(reversed(list(records.items()))),"quadratic",replicates=40)
    assert a == pytest.approx(b)


def test_insufficient_cluster_resamples_rejected():
    with pytest.raises(ValueError,match="Too few"):
        state_cluster_ci({},"quadratic",replicates=9)
