from zipfile import ZipFile

import pytest

from electoral_analysis.turnout_detail import (
    audit_detail_archive,
    comparable_municipal_changes,
)

H = ("ANO_ELEICAO;NR_TURNO;SG_UF;CD_MUNICIPIO;NR_ZONA;NR_SECAO;"
     "DS_CARGO;QT_APTOS;QT_COMPARECIMENTO;QT_ABSTENCOES\n")
A = "2022;1;SP;1234;1;1;Presidente;300;250;50\n"
B = "2022;1;SP;1234;1;1;Governador;300;250;50\n"
C = "2022;1;SP;1234;1;2;Presidente;200;150;50\n"


def make_zip(path, members):
    with ZipFile(path, "w") as z:
        for name, content in members.items():
            z.writestr(name, content)


def test_multi_csv_duplicate_and_presidential_filter(tmp_path):
    p = tmp_path / "detail.zip"
    make_zip(p, {"detail_SP.csv": H + A + B + C,
                 "detail_BRASIL.csv": H + A})
    result = audit_detail_archive(p, 2022)
    assert result["unique_presidential_sections"] == 2
    assert result["identical_duplicate_rows"] == 1
    assert result["national_by_round"][0]["eligible"] == 500
    assert result["national_by_round"][0]["attended"] == 400
    assert result["municipal_by_round"][0]["turnout_rate"] == .8


def test_conflicting_duplicate_fails(tmp_path):
    p = tmp_path / "detail.zip"
    make_zip(p, {"SP.csv": H + A, "BRASIL.csv": H + A.replace("250;50", "240;60")})
    with pytest.raises(ValueError, match="inconsistent"):
        audit_detail_archive(p, 2022)


def test_bad_conservation_fails(tmp_path):
    p = tmp_path / "detail.zip"
    make_zip(p, {"SP.csv": H + A.replace("250;50", "249;50") + C})
    result = audit_detail_archive(p, 2022)
    assert result["quarantined_nonconserving_rows"] == 1
    assert result["counts_are_partial_if_quarantined"]
    assert result["nonconserving_samples"][0]["difference"] == 1


def test_pairing_and_unmatched():
    a = {"municipal_by_round": [
        {"round": 1, "uf": "SP", "municipality_tse": "100",
         "turnout_rate": .80, "eligible": 100}]}
    b = {"municipal_by_round": [
        {"round": 1, "uf": "SP", "municipality_tse": "100",
         "turnout_rate": .75, "eligible": 120},
        {"round": 1, "uf": "SP", "municipality_tse": "200",
         "turnout_rate": .90, "eligible": 70}]}
    p = comparable_municipal_changes(a, b)
    assert p["paired"] == 1
    assert p["2026_only"] == 1
    assert round(p["rows"][0]["delta_turnout_pp"], 8) == -5.0

def test_duplicated_nonconserving_records_count_once(tmp_path):
    p = tmp_path / "details.zip"
    anomaly = A.replace("250;50", "249;50")
    make_zip(p, {"BR.csv": H + anomaly + C, "SP.csv": H + anomaly})
    data = audit_detail_archive(p, 2022)
    assert data["quarantined_nonconserving_rows"] == 2
    assert data["unique_exception_sections"] == 1
    assert data["duplicate_exception_rows"] == 1
    assert data["exceptional_by_round_uf"][0]["eligible"] == 300
    assert data["national_by_round"][0]["eligible"] == 200
