from zipfile import ZipFile

import pytest

from electoral_analysis.municipal_results import (
    aggregate_first_round_zip,
    make_descriptive_panel,
    summarize_turnout_baseline,
)


def votes(year, mun="100", valid=90, blank=5, null=5):
    return {
        "year": year, "zip_sha256": str(year),
        "candidate_option_names": {"13": ["CANDIDATO A"]},
        "municipalities": [{
            "uf": "SP", "tse_code": mun, "valid": valid, "blank": blank,
            "null": null, "other": 0, "candidate_votes": {"13": valid},
        }],
    }


def detail(year, turnout):
    return {"zip_sha256": str(year), "municipal_by_round": [{
        "round": 1, "uf": "SP", "municipality_tse": "100",
        "eligible": 120, "attended": 100, "turnout_rate": turnout,
    }]}


def test_paired_observations_and_temporal_turnout_baseline():
    crosswalk = {"map": {("SP", "100"): "3500001"},
                 "inconsistencies": [], "duplicates": 0}
    p = make_descriptive_panel(votes(2022), votes(2026), crosswalk,
                               detail(2022, 0.8), detail(2026, 0.75))
    assert p["matched_municipalities"] == 1
    assert p["municipalities"][0]["2022"]["candidates"]["13"]["valid_share"] == 1
    assert summarize_turnout_baseline(p)["mae_pp"] == pytest.approx(5)


def test_disagreeing_vote_and_turnout_counts_are_rejected():
    crosswalk = {"map": {("SP", "100"): "3500001"},
                 "inconsistencies": [], "duplicates": 0}
    with pytest.raises(ValueError, match="disagree"):
        make_descriptive_panel(votes(2022), votes(2026, valid=88),
                               crosswalk, detail(2022, 0.8), detail(2026, 0.75))


def test_never_impute_missing_prior_year():
    crosswalk = {"map": {("SP", "100"): "3500001", ("SP", "200"): "3500002"},
                 "inconsistencies": [], "duplicates": 0}
    p = make_descriptive_panel(votes(2022), votes(2026, mun="200"), crosswalk,
                               detail(2022, 0.8), detail(2026, 0.75))
    assert p["matched_municipalities"] == 0
    assert p["not_paired_2022"] == 1
    assert p["not_paired_2026"] == 1


def test_incomplete_national_csv_is_not_accepted(tmp_path):
    path = tmp_path / "votes.zip"
    header = ("ANO_ELEICAO;NR_TURNO;SG_UF;CD_MUNICIPIO;DS_CARGO;"
              "NR_VOTAVEL;NM_VOTAVEL;QT_VOTOS\n")
    with ZipFile(path, "w") as z:
        z.writestr("votes.csv", header + "2026;1;SP;100;Presidente;13;CANDIDATO;25\n")
    with pytest.raises(ValueError, match="National tally differs"):
        aggregate_first_round_zip(path, 2026)
