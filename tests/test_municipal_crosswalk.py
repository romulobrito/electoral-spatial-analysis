import json
from zipfile import ZipFile

import pytest

from electoral_analysis.municipal_crosswalk import (
    build_comparison,
    normalize_tse_code,
    read_crosswalk_zip,
)


def test_leading_zero_equivalence():
    assert normalize_tse_code("01007") == normalize_tse_code("1007")
    with pytest.raises(ValueError):
        normalize_tse_code("10AB")


def test_crosswalk_csv_and_pair(tmp_path):
    z = tmp_path / "codes.zip"
    with ZipFile(z, "w") as archive:
        archive.writestr("municipio_tse_ibge.csv",
                         "SG_UF;CD_MUNICIPIO_TSE;CD_MUNICIPIO_IBGE\n"
                         "AC;01007;1200138\n")
    cw = read_crosswalk_zip(z)
    assert cw["map"][("AC", "1007")] == "1200138"
    def report(eligible, attended):
        return {"municipal_by_round": [{"round": 1, "uf": "AC",
                 "municipality_tse": "1007", "eligible": eligible, "attended": attended,
                 "turnout_rate": attended/eligible}]}
    result = build_comparison(report(100, 75), report(110, 88), cw)
    assert result["matched"] == 1
    assert result["rows"][0]["municipality_ibge"] == "1200138"
    assert result["rows"][0]["delta_turnout_pp"] == pytest.approx(5)


def test_many_to_one_collision_rejected():
    cw = {"map": {("SP", "101"): "3500001", ("SP", "102"): "3500001"},
          "inconsistencies": [], "duplicates": 0}
    a = {"municipal_by_round": [
        {"round": 1, "uf": "SP", "municipality_tse": code,
         "eligible": 100, "attended": 70, "turnout_rate": .7}
        for code in ("101", "102")
    ]}
    with pytest.raises(ValueError, match="collision"):
        build_comparison(a, a, cw)
