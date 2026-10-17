import pytest

from electoral_analysis.etl import inspect_csv, turnout_rate


def test_turnout():
    assert turnout_rate(75, 100) == 0.75
    with pytest.raises(ValueError):
        turnout_rate(101, 100)


def test_inspect_csv(tmp_path):
    f = tmp_path / "example.csv"
    f.write_text("NR_TURNO;QT_VOTOS\n1;12\n", encoding="utf-8")
    result = inspect_csv(f, {"NR_TURNO", "QT_VOTOS"}, encoding="utf-8")
    assert result["rows"] == 1
    assert len(result["sha256"]) == 64
    with pytest.raises(ValueError):
        inspect_csv(f, {"missing"}, encoding="utf-8")
