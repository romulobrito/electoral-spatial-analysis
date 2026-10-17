import io
import json
from zipfile import ZipFile

import pytest

from electoral_analysis.acquisition import inventory_zip
from electoral_analysis.audit import audit_turnout_csv, audit_turnout_zip
from electoral_analysis.cli import main
from electoral_analysis.sources import RESOURCES, validated_download_url

HEADER = "NR_TURNO;SG_UF;CD_MUNICIPIO;NR_ZONA;NR_SECAO;DS_CARGO;QT_APTOS;QT_COMPARECIMENTO;QT_ABSTENCOES\n"
R1 = "1;SP;71072;1;1;Presidente;300;250;50\n"
R2 = "1;SP;71072;1;2;Presidente;200;170;30\n"


def test_sources_are_official():
    assert len(RESOURCES) == 4
    for item in RESOURCES.values():
        assert validated_download_url(item).endswith(".zip")


def test_dedup_sections_and_municipality_sums():
    data = HEADER + R1 + R1 + R2
    result = audit_turnout_csv(io.StringIO(data), year=2022)
    assert result["input_rows"] == 3
    assert result["unique_president_sections"] == 2
    assert result["duplicate_section_rows"] == 1
    assert result["municipalities"][0]["eligible"] == 500
    assert result["municipalities"][0]["attended"] == 420
    assert result["municipalities"][0]["turnout_rate"] == 0.84


def test_conflict_is_not_silently_overwritten():
    altered = R1.replace("250;50", "240;60")
    with pytest.raises(ValueError, match="Conflicting totals"):
        audit_turnout_csv(io.StringIO(HEADER + R1 + altered), year=2026)


def test_failure_on_missing_fields():
    with pytest.raises(ValueError, match="Missing required"):
        audit_turnout_csv(io.StringIO("DS_CARGO;SG_UF;QT_APTOS\nPresidente;SP;1\n"), year=2026)


def test_reconcile_and_nonnegative():
    with pytest.raises(ValueError, match="do not reconcile"):
        audit_turnout_csv(io.StringIO(HEADER + R1.replace("250;50", "249;50")), year=2022)
    with pytest.raises(ValueError, match="Negative field"):
        audit_turnout_csv(io.StringIO(HEADER + R1.replace("300;250;50", "300;-1;301")), year=2022)


def test_mixed_cargos_excluded():
    other = R1.replace("Presidente", "Governador")
    result = audit_turnout_csv(io.StringIO(HEADER + other + R2), year=2022)
    assert result["unique_president_sections"] == 1


def test_zip_and_partial_flag(tmp_path):
    z = tmp_path / "toy.zip"
    with ZipFile(z, "w") as handle:
        handle.writestr("data.csv", HEADER + R1 + R2)
    assert inventory_zip(z)[0]["name"] == "data.csv"
    result = audit_turnout_zip(z, year=2022, max_rows=1)
    assert result["is_partial"]
    assert result["unique_president_sections"] == 1


def test_zip_path_traversal_rejected(tmp_path):
    z = tmp_path / "bad.zip"
    with ZipFile(z, "w") as handle:
        handle.writestr("../escape.csv", HEADER + R1)
    with pytest.raises(ValueError, match="Unsafe"):
        inventory_zip(z)


def test_cli_sources(capsys):
    assert main(["sources"]) == 0
    result = json.loads(capsys.readouterr().out)
    assert {r["year"] for r in result} == {2022, 2026}


def test_no_presidential_rows_rejected():
    with pytest.raises(ValueError, match="No presidential"):
        audit_turnout_csv(io.StringIO(HEADER + R1.replace("Presidente", "Governador")), year=2022)


def test_no_cargo_column_rejected():
    bad = "NR_TURNO;SG_UF;CD_MUNICIPIO;NR_ZONA;NR_SECAO;QT_APTOS;QT_COMPARECIMENTO;QT_ABSTENCOES\n"
    with pytest.raises(ValueError, match="cargo column"):
        audit_turnout_csv(io.StringIO(bad + "1;SP;1;1;1;300;250;50\n"), year=2022)
