import copy
import math

import pytest

from electoral_analysis.ibge_turnout import (
    grouped_evaluation,
    join_turnout,
    validate_ibge_response,
)


def census_fixture():
    return [
        {"id": key, "variavel": label, "resultados": [{"classificacoes": [], "series": [
            {"localidade": {"id": "3500001", "nivel": {"id": "N6"}},
             "serie": {"2022": val}}
        ]}]} for key, label, val in (
            ("93", "População residente", "1000"),
            ("6318", "Área da unidade territorial", "10.0"),
            ("614", "Densidade demográfica", "100.0"),
        )
    ]


def test_ibge_schema_parser_strict():
    d = validate_ibge_response(census_fixture())
    assert d["3500001"]["population"] == 1000.0
    assert d["3500001"]["density_km2"] == 100


def test_conflicting_or_missing_year_fails():
    wrong = census_fixture()
    wrong[0]["resultados"][0]["series"][0]["serie"] = {"2026": "100"}
    with pytest.raises(ValueError, match="period"):
        validate_ibge_response(wrong)
    wrong = census_fixture()
    wrong[0]["resultados"][0]["series"].append(copy.deepcopy(
        wrong[0]["resultados"][0]["series"][0]))
    with pytest.raises(ValueError, match="Duplicate"):
        validate_ibge_response(wrong)


def test_join_flags_affected_2022_municipality():
    panel = {"municipalities": [{"uf": "AM", "municipality_ibge": "3500001",
                                "2022": {"turnout_rate": .72},
                                "2026": {"turnout_rate": .75}}]}
    joined, qc = join_turnout(panel, validate_ibge_response(census_fixture()),
                             exceptional_ibge="3500001")
    assert joined[0]["incomplete_2022_denominator"]
    assert qc["denominator_exception_count"] == 1
    assert joined[0]["delta_turnout_pp"] == pytest.approx(3)


def test_leave_state_out_ridge_only_for_turnout():
    rows = []
    for i, state in enumerate(["AC", "AL", "AM", "BA"]):
        for k in range(15):
            old = .68 + .01 * k + .006 * i
            change = (k % 5 - 2) * .5 + i * .25
            rows.append({"ibge": f"{i}{k:06d}", "uf": state,
                         "population_2022": 3000 + k * 1000 + i * 50,
                         "density_2022_km2": 20 + k * 10 + i,
                         "turnout_2022": old, "turnout_2026": old + change / 100,
                         "delta_turnout_pp": change,
                         "incomplete_2022_denominator": i == 2 and k == 0})
    report = grouped_evaluation(rows, resamples=25)
    assert report["municipalities_tested"] == 59
    assert report["state_folds"] == 4
    assert math.isfinite(report["ridge_mae_pp"])
    assert len(report["state_cluster_bootstrap_95ci_pp"]) == 2
    assert report["excluded_missing_or_exception"] == 1
