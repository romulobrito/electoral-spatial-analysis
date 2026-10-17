import io
from zipfile import ZipFile

import pytest

from electoral_analysis.vote_audit import (
    add_reference_audit, audit_csv, audit_zip, vote_category,
)

HEADER = (
    "ANO_ELEICAO;NR_TURNO;SG_UF;CD_MUNICIPIO;NR_ZONA;NR_SECAO;"
    "DS_CARGO;NR_VOTAVEL;NM_VOTAVEL;QT_VOTOS\n"
)
ROWS = [
    "2022;1;SP;100;1;1;Presidente;13;Candidate A;100\n",
    "2022;1;SP;100;1;1;Presidente;22;Candidate B;80\n",
    "2022;1;SP;100;1;1;Presidente;95;Branco;7\n",
    "2022;1;SP;100;1;1;Presidente;96;Nulo;13\n",
    "2022;2;SP;100;1;1;Presidente;13;Candidate A;120\n",
    "2022;1;RJ;101;2;2;Presidente;13;Candidate A;50\n",
]


def test_categories():
    assert [vote_category(str(x)) for x in (13, 95, 96, 97)] == [
        "valid", "blank", "null", "unclassified",
    ]


def test_streamed_counts_and_unique_sections():
    out = audit_csv(io.StringIO(HEADER + "".join(ROWS)), year=2022)
    assert out["input_rows"] == 6
    assert out["unique_presidential_sections_over_rounds"] == 3
    assert out["rounds"][0] == {
        "round": 1, "valid": 230, "blank": 7, "null": 13,
        "unclassified": 0, "counted_votes": 250,
    }
    assert out["rounds"][1]["valid"] == 120
    assert len(out["state_aggregates"]) == 3


def test_ignores_other_offices():
    row = ROWS[0].replace("Presidente", "Governador")
    result = audit_csv(io.StringIO(HEADER + row + ROWS[1]), year=2022)
    assert result["filtered_other_cargo_rows"] == 1
    assert result["rounds"][0]["valid"] == 80


def test_unclassified_never_valid():
    row = ROWS[0].replace(";13;Candidate A;", ";97;Unknown;")
    result = audit_csv(io.StringIO(HEADER + row), year=2022)
    assert result["rounds"][0]["valid"] == 0
    assert result["unclassified_options"][0]["votes"] == 100


def test_wrong_year_rejected():
    with pytest.raises(ValueError, match="Invalid year"):
        audit_csv(io.StringIO(HEADER + ROWS[0].replace("2022;", "2026;")), year=2022)


def test_bad_and_missing_fields():
    with pytest.raises(ValueError, match="Invalid year"):
        audit_csv(io.StringIO(HEADER + ROWS[0].replace(";100\n", ";-1\n")), year=2022)
    with pytest.raises(ValueError, match="Missing required"):
        audit_csv(io.StringIO("ANO_ELEICAO\n2022\n"), year=2022)


def test_zip_and_reference(tmp_path):
    path = tmp_path / "votes.zip"
    with ZipFile(path, "w") as z:
        z.writestr("votes.csv", HEADER + "".join(ROWS))
        z.writestr("leiame.pdf", b"fixture")
    result = audit_zip(path, year=2022)
    assert result["csv_member"] == "votes.csv"
    assert len(result["sha256"]) == 64
    assert not all(v["matches"] for v in result["reference"]["comparisons"])


def test_partial_2026_reference():
    row = ROWS[0].replace("2022;", "2026;")
    data = audit_csv(io.StringIO(HEADER + row), year=2026)
    assert "not final" in add_reference_audit(data)["reference"]["kind"]
