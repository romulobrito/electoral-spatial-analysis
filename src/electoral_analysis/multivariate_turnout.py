"""E013: multivariate and nonlinear retrospective MUNICIPAL turnout experiment.

Neutral aggregate participation, no candidate votes, voter profiling or targeting.
Validation folds remove each held-out UF's 2026 outcomes before fitting.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
from collections import defaultdict
from pathlib import Path

import numpy as np

from .ibge_turnout import _fit_ridge, join_turnout, validate_ibge_response
from .residual_diagnostics import (
    IBGE_SHA, PANEL_SHA, REGIONAL_SHRINKAGE, STATE_REGION,
)
from .spatial_moran import build_adjacency
from .state_conditional_moran import (
    conditional_permutations, prepare_within_state_graph,
)

EXPECTED_N = 5569
EXPECTED_E007_MAE = 1.7914991430214526
SEED = 2718
PENALTY = 10.0
VARIABLES = ("turnout_2022", "log_population_2022", "log_density_2022")


def predictors(row: dict) -> np.ndarray:
    """2022-only inputs: no target-year data or candidate share."""
    return np.array([
        row["turnout_2022"],
        math.log1p(row["population_2022"]),
        math.log1p(row["density_2022_km2"]),
    ], dtype=float)


def fixed_design(train: np.ndarray, test: np.ndarray, quadratic: bool):
    """All transformation parameters, including means, are train-fold-only."""
    mean = train.mean(axis=0)
    std = train.std(axis=0)
    if np.any(std < 1e-10) or np.any(~np.isfinite(std)):
        raise ValueError("Training predictor degeneracy")
    raw_train, raw_test = (train-mean)/std, (test-mean)/std
    if quadratic:
        raw_train = np.column_stack([raw_train, raw_train**2])
        raw_test = np.column_stack([raw_test, raw_test**2])
    second_mean = raw_train.mean(axis=0)
    second_scale = raw_train.std(axis=0)
    if np.any(second_scale < 1e-10):
        raise ValueError("Training nonlinear basis degeneracy")
    return ((raw_train-second_mean)/second_scale,
            (raw_test-second_mean)/second_scale)


def train_predict(train: list[dict], test: list[dict], *, quadratic: bool) -> np.ndarray:
    """Penalized linear or quadratic ridge, fixed alpha and no fold leakage."""
    x=np.stack([predictors(r) for r in train])
    z=np.stack([predictors(r) for r in test])
    y=np.array([r["delta_turnout_pp"] for r in train],dtype=float)
    a,b=fixed_design(x,z,quadratic)
    coefficients=np.linalg.solve(a.T@a + PENALTY*np.eye(a.shape[1]), a.T@(y-y.mean()))
    return y.mean() + b@coefficients


def state_cluster_ci(errors: dict, candidate: str, baseline: str = "ridge_regional",
                     *, replicates: int = 400, seed: int = SEED) -> list[float]:
    if replicates < 20:
        raise ValueError("Too few bootstrap draws")
    grouped=defaultdict(list)
    for record in errors.values():
        grouped[record["uf"]].append(
            abs(record[candidate])-abs(record[baseline])
        )
    states=sorted(grouped)
    rng=random.Random(seed)
    means=[]
    for _ in range(replicates):
        selected=[rng.choice(states) for _ in states]
        num=sum(sum(grouped[uf]) for uf in selected)
        den=sum(len(grouped[uf]) for uf in selected)
        means.append(num/den)
    means.sort()
    return [means[int((replicates-1)*0.025)],means[int((replicates-1)*0.975)]]


def evaluate(rows: list[dict], *, replicates: int = 400) -> tuple[dict, dict]:
    useful=[r for r in rows
            if not r["incomplete_2022_denominator"]
            and r["population_2022"] is not None
            and r["density_2022_km2"] is not None]
    if len(useful)!=EXPECTED_N or len({r["ibge"] for r in useful})!=EXPECTED_N:
        raise ValueError("E007 municipality sample or identifiers unexpectedly changed")
    states=sorted({r["uf"] for r in useful})
    if len(states)!=27 or set(states)!=set(STATE_REGION):
        raise ValueError("Expected 27 leave-state-out groups")
    errors={}
    fold_mae=[]
    for uf in states:
        train=[r for r in useful if r["uf"]!=uf]
        test=[r for r in useful if r["uf"]==uf]
        linear=_fit_ridge(train,PENALTY)
        quadratic_predictions=train_predict(train,test,quadratic=True)
        # Train-only regional shifts are computed separately for EACH model.
        quadratic_train=train_predict(train,train,quadratic=True)
        correction_linear=defaultdict(list)
        correction_quadratic=defaultdict(list)
        for k,row in enumerate(train):
            region=STATE_REGION[row["uf"]]
            correction_linear[region].append(row["delta_turnout_pp"]-linear(row))
            correction_quadratic[region].append(row["delta_turnout_pp"]-quadratic_train[k])
        def shrink(bucket: dict, region: str) -> float:
            values=bucket[region]
            return sum(values)/(len(values)+REGIONAL_SHRINKAGE)
        reg=STATE_REGION[uf]
        cl=shrink(correction_linear,reg)
        cq=shrink(correction_quadratic,reg)
        for i,row in enumerate(test):
            code=row["ibge"]
            if code in errors:
                raise ValueError("Duplicate held-out municipality")
            target=row["delta_turnout_pp"]
            errors[code]={
                "uf":uf,
                "persistence":target,
                "ridge":target-linear(row),
                "ridge_regional":target-linear(row)-cl,
                "quadratic":target-float(quadratic_predictions[i]),
                "quadratic_regional":target-float(quadratic_predictions[i])-cq,
            }
        fold_mae.append({
            "uf":uf,"municipalities":len(test),
            "ridge_regional_mae_pp":sum(abs(errors[x["ibge"]]["ridge_regional"]) for x in test)/len(test),
            "quadratic_regional_mae_pp":sum(abs(errors[x["ibge"]]["quadratic_regional"]) for x in test)/len(test),
        })
    names=("persistence","ridge","ridge_regional","quadratic","quadratic_regional")
    result={
        name:{
            "mae_pp":sum(abs(v[name]) for v in errors.values())/len(errors),
            "rmse_pp":math.sqrt(sum(v[name]**2 for v in errors.values())/len(errors)),
        } for name in names
    }
    if abs(result["ridge_regional"]["mae_pp"]-EXPECTED_E007_MAE)>1e-8:
        raise ValueError("E007 reference MAE cannot be replicated")
    for name in ("quadratic","quadratic_regional"):
        result[name]["minus_e007_mae_pp"]=result[name]["mae_pp"]-result["ridge_regional"]["mae_pp"]
        result[name]["state_bootstrap_95pct_pp"]=state_cluster_ci(
            errors,name,replicates=replicates)
    return {
        "fold_strategy":"Leave one entire UF out for each of 27 retrospective folds",
        "municipalities":len(errors),
        "model_results":result,
        "heldout_uf_mae":fold_mae,
        "degree_two_terms":"All three 2022 predictors squared; train-only normalized quadratic ridge",
        "ridge_alpha":PENALTY,
        "uf_cluster_bootstrap_replicates":replicates,
        "seed":SEED,
    },errors


def multivariate_associations(rows: list[dict]) -> dict:
    """Descriptive state-FE OLS slopes and clustered-UF intervals, NOT prediction."""
    import statsmodels.api as sm
    usable=[r for r in rows if not r["incomplete_2022_denominator"]
            and r["population_2022"] is not None
            and r["density_2022_km2"] is not None]
    states=sorted({r["uf"] for r in usable})
    a=np.stack([predictors(r) for r in usable])
    target=np.array([r["delta_turnout_pp"] for r in usable],dtype=float)
    mean,std=a.mean(axis=0),a.std(axis=0)
    standardized=(a-mean)/std
    # Descriptive fixed effects: not used to predict any heldout state's result.
    dummies=np.array([[float(r["uf"]==uf) for uf in states[1:]] for r in usable])
    exog=np.column_stack([np.ones(len(usable)),standardized,dummies])
    fitted=sm.OLS(target,exog).fit(
        cov_type="cluster",cov_kwds={"groups":[r["uf"] for r in usable]},
    )
    bounds=fitted.conf_int(alpha=0.05)
    associations=[]
    for j,name in enumerate(VARIABLES,1):
        reduced=np.delete(exog,j,axis=1)
        coefficient=np.linalg.lstsq(reduced,target,rcond=None)[0]
        full_sse=sum(fitted.resid**2)
        reduced_sse=sum((target-reduced@coefficient)**2)
        partial_r2=max(0.0,1-full_sse/reduced_sse) if reduced_sse>0 else None
        associations.append({
            "feature":name,
            "coefficient_pp_per_one_sd":float(fitted.params[j]),
            "cluster_se_pp":float(fitted.bse[j]),
            "cluster_95pct_ci_pp":[float(bounds[j,0]),float(bounds[j,1])],
            "partial_r2_sample":float(partial_r2) if partial_r2 is not None else None,
            "observed_2022_mean":float(mean[j-1]),
            "observed_2022_sd":float(std[j-1]),
        })
    return {
        "method":"Retrospective municipal OLS with UF fixed effects and UF-clustered standard errors",
        "observations":len(usable),"clusters_uf":len(states),
        "response":"2026 minus 2022 aggregate turnout (percentage points)",
        "r2_in_sample":float(fitted.rsquared),
        "r2_within_uf":float(1-sum(fitted.resid**2)/sum(
            (target[i]-np.mean([target[k] for k,r in enumerate(usable) if r["uf"]==usable[i]["uf"]]))**2
            for i in range(len(usable))
        )),
        "features":associations,
        "caveat":"Associations only. UF fixed-effects in-sample R² must not be interpreted as out-of-UF predictive performance; clustered CIs are exploratory with 27 clusters.",
    }


def spatial_diagnostics(errors: dict, graph: dict, *, permutations: int=499) -> dict:
    """Conditional Moran of each heldout residual with same UF-only queen graph."""
    prepared=prepare_within_state_graph(errors,graph["queen"]["edges"])
    result={}
    for model in ("ridge_regional","quadratic_regional"):
        converted={code:{"uf":v["uf"],"baseline":v[model],
                         "ridge":v["ridge"],"ridge_regional":v["ridge_regional"]}
                   for code,v in errors.items()}
        result[model]=conditional_permutations(converted,prepared,"baseline",
                                               permutations=permutations,seed=SEED)
    return {
        "topology":"IBGE 2022 native queen, neighbors restricted to same UF",
        "nodes":len(prepared["nodes"]),"intra_uf_edges":prepared["within_state_edges"],
        "permutations":permutations,"models":result,
    }


def main() -> int:
    ap=argparse.ArgumentParser()
    ap.add_argument("--panel",type=Path,required=True)
    ap.add_argument("--census",type=Path,required=True)
    ap.add_argument("--geometry",type=Path,required=True)
    ap.add_argument("--out-dir",type=Path,required=True)
    args=ap.parse_args()
    if args.out_dir.exists():
        ap.error("Output directory exists")
    raw_panel,raw_census=args.panel.read_bytes(),args.census.read_bytes()
    if hashlib.sha256(raw_panel).hexdigest()!=PANEL_SHA:
        raise ValueError("E005 panel SHA256 mismatch")
    if hashlib.sha256(raw_census).hexdigest()!=IBGE_SHA:
        raise ValueError("E006 Census SHA256 mismatch")
    rows,qa=join_turnout(json.loads(raw_panel),
        validate_ibge_response(json.loads(raw_census)),exceptional_ibge="1302603")
    eval_result,errors=evaluate(rows)
    association=multivariate_associations(rows)
    graph=build_adjacency(args.geometry,set(errors))
    moran=spatial_diagnostics(errors,graph)
    report={
        "stage":"E013", "scope":"Descriptive aggregate turnout, NOT candidate votes",
        "evaluation":eval_result,"multivariate":association,
        "conditional_moran":moran,"qa":qa,
        "sources":{"panel_sha256":PANEL_SHA,"census_sha256":IBGE_SHA,
                   "geometry_sha256":graph["ibge_2022_shapefile_sha256"]},
        "limitations":[
            "Nonlinear degree-two basis chosen after exploratory E009/E010; no independent future election holdout",
            "Census 2022 release timing prevents strict 2022-ex-ante forecast claim",
            "UF fixed effects describe within-state associations, not causal effects or unseen-state predictions",
            "Confidence intervals are exploratory, clustered by UF; 27 geographic clusters",
            "An observed spatial Moran need not identify its physical or social generating process",
            "No individual preferences, candidate votes, persuasion scores or neighborhood inference",
        ],
    }
    args.out_dir.mkdir(parents=True)
    (args.out_dir/"e013_results.json").write_text(
        json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    concise={"model_results":eval_result["model_results"],
             "associations":association["features"],
             "r2_in_sample":association["r2_in_sample"],
             "moran":moran["models"]}
    print(json.dumps(concise,ensure_ascii=False))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
