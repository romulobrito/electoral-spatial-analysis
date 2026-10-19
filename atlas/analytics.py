"""Neutral exploratory analytics for the source-pinned municipal atlas.

Outputs are retrospective, aggregate and noncausal. No location persuasion scores.
"""
from __future__ import annotations

import csv
import hashlib
import io
import math
import unicodedata
from collections import defaultdict
from pathlib import Path

from electoral_analysis.ibge_turnout import validate_ibge_response
from electoral_analysis.residual_diagnostics import IBGE_SHA

REQUIRED_METHODS = (
    "persistence", "ridge", "ridge_regional", "spatial_queen", "spatial_rook"
)
REQUIRED_MORAN = ("baseline", "ridge", "ridge_regional")
E010_REPRO_MAE = {
    "persistence": 2.13550811315029,
    "ridge": 1.9567342399383514,
    "ridge_regional": 1.7914991430214526,
    "spatial_queen": 1.9454537992440795,
    "spatial_rook": 1.9452735783182011,
}


def normalized_name(name: str) -> str:
    """Normalize only for conservative *exact* inter-election label matching."""
    plain = unicodedata.normalize("NFKD", name)
    plain = "".join(c for c in plain if not unicodedata.combining(c))
    return " ".join(plain.upper().split())


def matched_candidacies(options: dict) -> dict:
    """Avoid interpreting the same party/candidate number as the same person.

    Only identically named candidates, with exactly one code in each year, qualify.
    This is a name-label match, not a legally certified identifier.
    """
    years = ("2022", "2026")
    index = {}
    for year in years:
        grouped = defaultdict(list)
        for code, name in options[year].items():
            key = normalized_name(name)
            if not key:
                raise ValueError("Empty candidate label")
            grouped[key].append(str(code))
        index[year] = grouped
    matched = {}
    for key in sorted(set(index["2022"]) & set(index["2026"])):
        if len(index["2022"][key]) != 1 or len(index["2026"][key]) != 1:
            continue
        a, b = index["2022"][key][0], index["2026"][key][0]
        matched[key] = {
            "display_name": options["2026"][b],
            "code_2022": a, "code_2026": b,
            "matching_rule": "exact normalized official candidate label",
        }
    return matched


def census_indicators(raw: bytes, municipal_rows: dict) -> tuple[dict, dict]:
    """Strict frozen Census 2022 municipal join and QA summary."""
    if hashlib.sha256(raw).hexdigest() != IBGE_SHA:
        raise ValueError("Census 2022 SHA256 mismatch")
    import json

    indicators = validate_ibge_response(json.loads(raw))
    if set(indicators) != set(municipal_rows):
        raise ValueError("Census municipalities differ from frozen TSE–IBGE panel")
    compact = {}
    for code, values in indicators.items():
        population, density = values["population"], values["density_km2"]
        area = values["area_km2"]
        if (
            population is None or density is None or area is None
            or not all(math.isfinite(x) and x >= 0 for x in (population, density, area))
        ):
            raise ValueError("Invalid Census 2022 numeric values")
        compact[code] = {
            "population_2022": population,
            "density_2022_km2": density,
            "area_2022_km2": area,
        }
    return compact, {
        "source": "IBGE Censo Demográfico 2022: agregado 4714, variáveis 93, 6318, 614",
        "sha256": IBGE_SHA,
        "sample": len(compact),
        "reference_year": 2022,
        "interpretation": (
            "Descriptive aggregate associations only; Census population is not "
            "equivalent to electorate, and observed correlations are not causal."
        ),
    }


def _csv(path: Path) -> list[dict]:
    rows = list(csv.DictReader(io.StringIO(path.read_text(encoding="utf-8"))))
    if not rows:
        raise ValueError(f"Empty model diagnostic CSV: {path}")
    return rows


def _float(row: dict, field: str) -> float | None:
    raw = row.get(field, "")
    if raw is None or not raw.strip():
        return None
    value = float(raw)
    if not math.isfinite(value):
        raise ValueError(f"Nonfinite model diagnostic {field}")
    return value


def validation_diagnostics(reports: Path) -> dict:
    """Use versioned scientific CSVs, NOT invented per-municipality model errors."""
    candidates = _csv(reports / "e010/model_comparison.csv")
    if {x["model"] for x in candidates} != set(REQUIRED_METHODS):
        raise ValueError("Unexpected E010 model set")
    models = []
    for entry in candidates:
        name = entry["model"]
        mae = _float(entry, "mae_pp")
        rmse = _float(entry, "rmse_pp")
        if mae is None or rmse is None or rmse < mae:
            raise ValueError("Invalid MAE/RMSE summary")
        if abs(mae - E010_REPRO_MAE[name]) > 1e-8:
            raise ValueError(f"E010 MAE changed unexpectedly for {name}")
        low = _float(entry, "state_bootstrap95_lower_pp")
        high = _float(entry, "state_bootstrap95_upper_pp")
        delta = _float(entry, "difference_vs_e007_mae_pp")
        if (low is None) != (high is None) or (
            low is not None and (low > high or delta is None or not low <= delta <= high)
        ):
            raise ValueError("Invalid state-cluster bootstrap band")
        models.append({
            "method": name, "mae_pp": mae, "rmse_pp": rmse,
            "vs_e007_mae_pp": delta,
            "state_cluster_bootstrap_95pct_pp": [low, high]
            if low is not None else None,
        })
    global_rows = _csv(reports / "e008/moran_summary.csv")
    conditional_rows = _csv(reports / "e009/conditional_moran_summary.csv")
    moran = {}
    for scope, entries, field in (
        ("global", global_rows, "queen_moran_I"),
        ("within_uf", conditional_rows, "conditional_moran_I"),
    ):
        moran[scope] = {}
        for entry in entries:
            if scope == "global":
                model = entry["model"]
                if model not in REQUIRED_MORAN:
                    # E008 names its persistence control as persistence.
                    if model == "persistence":
                        model = "baseline"
                    else:
                        raise ValueError("Unexpected global Moran model")
                for graph in ("queen", "rook"):
                    value = _float(entry, graph + "_moran_I")
                    pvalue = _float(entry, graph + "_permutation_p")
                    if value is None or pvalue is None:
                        raise ValueError("Missing E008 Moran data")
                    moran[scope].setdefault(model, {})[graph] = {
                        "I": value, "p": pvalue,
                    }
            else:
                graph, model = entry["graph"], entry["method"]
                if graph not in ("queen", "rook") or model not in REQUIRED_MORAN:
                    raise ValueError("Unexpected E009 Moran entry")
                value, pvalue = _float(entry, field), _float(entry, "permutation_p_two_sided")
                if value is None or pvalue is None:
                    raise ValueError("Missing E009 Moran statistic")
                moran[scope].setdefault(model, {})[graph] = {
                    "I": value, "p": pvalue,
                }
    for scope in moran.values():
        if set(scope) != set(REQUIRED_MORAN):
            raise ValueError("Incomplete Moran model coverage")
        for graph in scope.values():
            if set(graph) != {"queen", "rook"}:
                raise ValueError("Incomplete queen/rook comparisons")
    return {
        "models": sorted(models, key=lambda row: REQUIRED_METHODS.index(row["method"])),
        "moran": moran,
        "evaluation": {
            "municipalities": 5569,
            "heldout_groups": 27,
            "task": "Retrospective 2026 − 2022 municipal turnout change, pp",
            "comparison": "Whole-state holdout; train-only coefficients and normalization",
            "uncertainty": (
                "400 bootstrap draws of entire UFs, seed 2718; exploratory intervals "
                "for each historical-spatial model minus E007 ridge-regional MAE"
            ),
            "moran_permutations": 499,
            "caveat": (
                "Global and within-UF Moran use different graph/centering; "
                "do not interpret them as a direct before/after reduction. "
                "None of these metrics measures candidate voting or persuasion."
            ),
        },
        "sources": {
            "e010": "reports/e010/model_comparison.csv",
            "e009": "reports/e009/conditional_moran_summary.csv",
            "e008": "reports/e008/moran_summary.csv",
        },
    }
