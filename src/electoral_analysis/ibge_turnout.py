"""IBGE Census 2022, municipal turnout and grouped retrospective validation.

Observed aggregate turnout only, never candidate support or persuasion propensity.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
import urllib.request
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

from .municipal_crosswalk import read_crosswalk_zip

IBGE_URL = (
    "https://servicodados.ibge.gov.br/api/v3/agregados/4714/periodos/2022/"
    "variaveis/93%7C6318%7C614?localidades=N6%5Ball%5D"
)
VARIABLES = {"93": "population", "6318": "area_km2", "614": "density_km2"}
NAMES = {"93": "População residente", "6318": "Área da unidade territorial",
         "614": "Densidade demográfica"}


def validate_ibge_response(data: list) -> dict:
    """Validate exact IBGE municipal series, period, labels and numeric data."""
    if not isinstance(data, list) or {str(v.get("id")) for v in data} != set(VARIABLES):
        raise ValueError("Unexpected census variable identifiers")
    values = defaultdict(dict)
    for entry in data:
        variable_id = str(entry["id"])
        if entry.get("variavel") != NAMES[variable_id]:
            raise ValueError("Census variable definition changed")
        results = entry.get("resultados")
        if not isinstance(results, list) or len(results) != 1:
            raise ValueError("Unexpected classified census response")
        result = results[0]
        if result.get("classificacoes"):
            raise ValueError("Unexpected dimensions in census response")
        for series in result.get("series", []):
            locality = series["localidade"]
            code = str(locality["id"])
            if (len(code) != 7 or not code.isascii() or not code.isdigit()
                    or locality["nivel"]["id"] != "N6"):
                raise ValueError("Unexpected census geography")
            if set(series["serie"]) != {"2022"}:
                raise ValueError("Unexpected census reference period")
            metric = VARIABLES[variable_id]
            if metric in values[code]:
                raise ValueError(f"Duplicate geography/variable {code}/{metric}")
            raw = series["serie"]["2022"]
            if raw in (None, "", "-", "...", "X", ".."):
                number = None
            else:
                try:
                    number = float(raw)
                except (ValueError, TypeError) as error:
                    raise ValueError(f"Nonnumeric census record: {code}") from error
                if not math.isfinite(number) or number < 0:
                    raise ValueError(f"Invalid census value for {code}")
            values[code][metric] = number
    if not values or any(set(v) != set(VARIABLES.values()) for v in values.values()):
        raise ValueError("Incomplete census variable coverage")
    return dict(values)


def fetch_ibge(path: Path) -> dict:
    """Fetch fixed public IBGE endpoint with 15 MB cap and SHA256 manifest."""
    if path.exists():
        raise FileExistsError(path)
    host = urlsplit(IBGE_URL)
    if (host.scheme, host.hostname) != ("https", "servicodados.ibge.gov.br"):
        raise ValueError("Non-official census endpoint")
    request = urllib.request.Request(IBGE_URL, headers={
        "User-Agent": "electoral-spatial-analysis/0.1", "Accept": "application/json"
    })
    with urllib.request.urlopen(request, timeout=90) as response:
        final = urlsplit(response.geturl())
        if (final.scheme, final.hostname) != ("https", "servicodados.ibge.gov.br"):
            raise ValueError("Unexpected redirect")
        raw = response.read(15_000_001)
    if len(raw) > 15_000_000:
        raise ValueError("Census response exceeds size limit")
    validate_ibge_response(json.loads(raw))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(raw)
    return {"source": IBGE_URL, "sha256": hashlib.sha256(raw).hexdigest(),
            "bytes": len(raw), "retrieved_utc": datetime.now(timezone.utc).isoformat()}


def join_turnout(panel: dict, census: dict, *, exceptional_ibge: str) -> tuple[list, dict]:
    """Exact IBGE join, preserving the incomplete Amazonas 2022 denominator flag."""
    seen = set()
    unmatched = []
    rows = []
    for election in panel["municipalities"]:
        code = election["municipality_ibge"]
        if code in seen:
            raise ValueError(f"Repeated IBGE key {code}")
        seen.add(code)
        if code not in census:
            unmatched.append(code)
            continue
        a, b = election["2022"]["turnout_rate"], election["2026"]["turnout_rate"]
        if a is None or b is None or not (0 <= a <= 1 and 0 <= b <= 1):
            raise ValueError(f"Invalid municipal turnout: {code}")
        m = census[code]
        rows.append({
            "ibge": code, "uf": election["uf"],
            "population_2022": m["population"], "area_2022_km2": m["area_km2"],
            "density_2022_km2": m["density_km2"],
            "turnout_2022": a, "turnout_2026": b,
            "delta_turnout_pp": 100 * (b - a),
            "incomplete_2022_denominator": (election["uf"] == "AM" and code == exceptional_ibge),
        })
    return rows, {"electoral_rows": len(panel["municipalities"]), "joined": len(rows),
                  "unmatched_codes": unmatched, "census_rows": len(census),
                  "denominator_exception_count": sum(x["incomplete_2022_denominator"] for x in rows)}


def _feature(row: dict) -> list[float]:
    return [row["turnout_2022"], math.log1p(row["population_2022"]),
            math.log1p(row["density_2022_km2"])]


def _fit_ridge(train: list[dict], penalty: float = 10.0):
    """Train a fixed-ridge 3-feature model with train-fold-only standardization."""
    if len(train) < 10:
        raise ValueError("Insufficient grouped training data")
    xx = [_feature(row) for row in train]
    yy = [row["delta_turnout_pp"] for row in train]
    n = len(xx)
    means = [sum(x[j] for x in xx) / n for j in range(3)]
    scale = [math.sqrt(sum((x[j] - means[j]) ** 2 for x in xx) / n) for j in range(3)]
    if min(scale) < 1e-12:
        raise ValueError("Degenerate predictor in training fold")
    ym = sum(yy) / n
    matrix = [[0.0] * 4 for _ in range(3)]
    for x, target in zip(xx, yy):
        z = [(x[j] - means[j]) / scale[j] for j in range(3)]
        for j in range(3):
            for k in range(3):
                matrix[j][k] += z[j] * z[k]
            matrix[j][3] += z[j] * (target - ym)
    for j in range(3):
        matrix[j][j] += penalty
    for j in range(3):
        pivot = max(range(j, 3), key=lambda k: abs(matrix[k][j]))
        matrix[j], matrix[pivot] = matrix[pivot], matrix[j]
        factor = matrix[j][j]
        if factor < 1e-12:
            raise ValueError("Singular ridge linear system")
        matrix[j] = [x / factor for x in matrix[j]]
        for i in range(3):
            if i != j:
                mult = matrix[i][j]
                matrix[i] = [a - mult * b for a, b in zip(matrix[i], matrix[j])]
    slopes = [row[3] for row in matrix]
    def predict(row: dict) -> float:
        x = _feature(row)
        return ym + sum(slopes[j] * (x[j] - means[j]) / scale[j] for j in range(3))
    return predict


def grouped_evaluation(rows: list[dict], *, resamples: int = 400, seed: int = 2718) -> dict:
    """Leave one state out and compare to historical no-change turnout baseline."""
    usable = [row for row in rows if not row["incomplete_2022_denominator"]
              and row["population_2022"] is not None
              and row["density_2022_km2"] is not None]
    states = sorted({r["uf"] for r in usable})
    if len(states) < 3:
        raise ValueError("At least three states are required")
    fold_report = []
    errors = defaultdict(list)
    for uf in states:
        train = [r for r in usable if r["uf"] != uf]
        test = [r for r in usable if r["uf"] == uf]
        predict = _fit_ridge(train)
        for row in test:
            observed_change = row["delta_turnout_pp"]
            model_error = observed_change - predict(row)
            errors[uf].append({"base_abs": abs(observed_change),
                               "model_abs": abs(model_error),
                               "base_sq": observed_change ** 2,
                               "model_sq": model_error ** 2})
        fold_report.append({
            "uf": uf, "municipalities": len(test),
            "baseline_mae_pp": sum(v["base_abs"] for v in errors[uf]) / len(test),
            "model_mae_pp": sum(v["model_abs"] for v in errors[uf]) / len(test),
        })
    all_errors = [x for uf in states for x in errors[uf]]
    n = len(all_errors)
    rng = random.Random(seed)
    differences = []
    for _ in range(resamples):
        sampled = [e for uf in (rng.choice(states) for _ in states) for e in errors[uf]]
        differences.append(sum(e["model_abs"] - e["base_abs"] for e in sampled) / len(sampled))
    differences.sort()
    return {
        "scope": "Retrospective MUNICIPAL TURNOUT, not candidate votes or political support",
        "test": "Leave-one-state-out; every prediction evaluated on an unseen state",
        "features": ["turnout_2022", "log1p(census_population_2022)",
                     "log1p(census_density_2022)"],
        "fixed_ridge_penalty": 10.0, "municipalities_tested": n,
        "state_folds": len(states), "excluded_missing_or_exception": len(rows) - n,
        "baseline_mae_pp": sum(e["base_abs"] for e in all_errors) / n,
        "ridge_mae_pp": sum(e["model_abs"] for e in all_errors) / n,
        "baseline_rmse_pp": math.sqrt(sum(e["base_sq"] for e in all_errors) / n),
        "ridge_rmse_pp": math.sqrt(sum(e["model_sq"] for e in all_errors) / n),
        "ridge_minus_baseline_mae_pp": sum(e["model_abs"] - e["base_abs"] for e in all_errors) / n,
        "state_cluster_bootstrap_95ci_pp": [
            differences[int((resamples - 1) * 0.025)],
            differences[int((resamples - 1) * 0.975)],
        ],
        "bootstrap_iterations": resamples, "random_seed": seed,
        "state_folds_alphabetical": fold_report,
        "limitations": [
            "Census 2022 publication timing precludes strict 2022 ex-ante forecasting claims",
            "Cross-state transportability is not causal identification",
            "Aggregate turnout does not reveal individual or candidate-specific preferences",
        ],
    }


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--electoral-panel", type=Path, required=True)
    p.add_argument("--crosswalk-zip", type=Path, required=True)
    p.add_argument("--ibge-snapshot", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args()
    if args.out.exists():
        p.error("Output already exists")
    census = validate_ibge_response(json.loads(args.ibge_snapshot.read_text(encoding="utf-8")))
    crosswalk = read_crosswalk_zip(args.crosswalk_zip)
    exceptional_ibge = crosswalk["map"].get(("AM", "2550"))
    if not exceptional_ibge or crosswalk["inconsistencies"]:
        raise ValueError("Amazonas exception or crosswalk not independently resolved")
    panel = json.loads(args.electoral_panel.read_text(encoding="utf-8"))
    rows, quality = join_turnout(panel, census, exceptional_ibge=exceptional_ibge)
    report = grouped_evaluation(rows)
    report["quality"] = quality
    report["source"] = {
        "ibge_url": IBGE_URL,
        "ibge_snapshot_sha256": hashlib.sha256(args.ibge_snapshot.read_bytes()).hexdigest(),
        "e005_panel_sha256": hashlib.sha256(args.electoral_panel.read_bytes()).hexdigest(),
        "exceptional_am_ibge": exceptional_ibge, "census_year": 2022,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in report.items() if k != "state_folds_alphabetical"},
                     ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
