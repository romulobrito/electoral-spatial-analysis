"""E016 synthetic guards and hidden-outcome invariance."""
import numpy as np
import pytest

from electoral_analysis.arrival_robustness import extend_path, guarded_delta, support_diagnostics


def fixture():
    n = 100
    h = np.linspace(.64, .82, n)
    uf = np.array(["SP"] * 50 + ["RJ"] * 50)
    pop = {"weight": np.ones(n)*100, "historical": h,
           "current": h + .01, "group": np.array([0]*50+[1]*50),
           "code": np.array([str(i) for i in range(n)]),
           "uf": uf, "groups": ["RJ", "SP"]}
    x = np.column_stack((h, np.log1p(np.arange(n)+500),
                         np.log1p(np.arange(n)%17+3)))
    return pop, x


def test_invariance_to_unrevealed_outcomes():
    pop,x=fixture()
    before=extend_path(pop,x,list(range(100)),thresholds=(.2,))
    changed={**pop,"current":pop["current"].copy()}
    changed["current"][20:]=.2
    after=extend_path(changed,x,list(range(100)),thresholds=(.2,))
    for a,b in zip(before,after):
        assert a["method"]==b["method"]
        assert a["estimate_turnout_pct"]==pytest.approx(b["estimate_turnout_pct"])


def test_fallback_with_insufficient_uf_coverage():
    pop,x=fixture()
    rows=extend_path(pop,x,list(range(100)),thresholds=(.2,))
    benchmark=next(r["estimate_turnout_pct"] for r in rows if r["method"]=="uf_shrunk_swing")
    for r in rows:
        if r["method"].startswith("e016"):
            assert r["model_fallback"]=="insufficient_geographic_coverage"
            assert r["estimate_turnout_pct"]==pytest.approx(benchmark)


def test_guard_bounds_extreme_prediction():
    raw=np.array([-300.,300.,2.])
    ref=np.array([1.,1.,1.])
    result,clipped,blend=guarded_delta(raw,ref,np.array([-1.,0.,1.]),np.zeros(3))
    assert np.isfinite(result).all()
    assert np.max(np.abs(result))<10
    assert clipped>0
    assert blend==pytest.approx(.75)


def test_out_of_support_detected():
    x=np.column_stack((np.arange(30.),np.arange(30.)**2,np.arange(30.)+1))
    seen=np.arange(10)
    hidden=np.arange(10,30)
    d,share=support_diagnostics(x,seen,hidden,np.ones(30))
    assert share>.35 and np.max(d)>0
