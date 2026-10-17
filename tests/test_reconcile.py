import pytest

from electoral_analysis.reconcile import reconcile


def fixture(year, accepted, extras, attended, round_id=1):
    return {"year": year,
            "national_by_round": [{
                "round": round_id, "eligible": accepted, "attended": attended,
                "abstained": accepted - attended
            }],
            "exceptional_by_round_uf": [
                {"round": round_id, "uf": "ZZ", "eligible": extras,
                 "attended": 0, "abstained": 0}
            ]}


def test_2022_reference_reconciliation():
    obj = fixture(2022, 156453354, 657, 123682372)
    result = reconcile(obj)
    assert result["all_checks_pass"]
    assert result["rounds"][0]["effective_eligible"] == 156454011


def test_2026_temporary_transfer_adjustment_is_explicit():
    obj = fixture(2026, 158745079, 423, 125275835)
    result = reconcile(obj)
    assert result["all_checks_pass"]
    assert result["rounds"][0]["raw_eligible"] == 158745502
    assert result["rounds"][0]["temporary_transfer_adjustment"] == 39
    assert result["rounds"][0]["effective_eligible"] == 158745463


def test_mismatch_fails_without_silent_correction():
    obj = fixture(2022, 156453350, 657, 123682372)
    assert not reconcile(obj)["all_checks_pass"]


def test_unexpected_votes_in_exceptional_section_fails():
    obj = fixture(2026, 158745079, 423, 125275835)
    obj["exceptional_by_round_uf"][0]["attended"] = 1
    with pytest.raises(ValueError, match="Unexpected exceptional"):
        reconcile(obj)
