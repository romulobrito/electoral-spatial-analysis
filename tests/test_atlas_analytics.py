"""E012 label identity and source-grounded scientific-panel tests."""
from pathlib import Path

import pytest

from atlas.analytics import matched_candidacies, validation_diagnostics


def test_name_label_not_ballot_number():
    pairs = matched_candidacies({
        "2022": {"13": "JOAO DA SILVA", "22": "OUTRA PESSOA"},
        "2026": {"40": "JOÃO DA SILVA", "22": "CANDIDATO DISTINTO"},
    })
    assert len(pairs) == 1
    assert pairs["JOAO DA SILVA"]["code_2022"] == "13"
    assert pairs["JOAO DA SILVA"]["code_2026"] == "40"


def test_ambiguous_labels_excluded():
    pairs = matched_candidacies({
        "2022": {"1": "IGUAL", "2": "IGUAL"},
        "2026": {"8": "IGUAL"},
    })
    assert pairs == {}


def test_real_versioned_model_csv_contract():
    report = validation_diagnostics(Path("reports"))
    assert len(report["models"]) == 5
    assert report["evaluation"]["municipalities"] == 5569
    assert report["models"][2]["method"] == "ridge_regional"
    assert report["models"][2]["mae_pp"] == pytest.approx(1.7914991430214526)
    assert set(report["moran"]) == {"global", "within_uf"}


def test_fail_if_model_file_missing(tmp_path):
    with pytest.raises(FileNotFoundError):
        validation_diagnostics(tmp_path)
