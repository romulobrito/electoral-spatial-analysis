"""Checks for neutral, internally consistent static atlas preparation."""
import pytest

from atlas.build import _validate_year, normalize_panel


def year_row():
    return {"valid":7,"blank":1,"null":0,"attended":8,
            "eligible_conserving_sections":10,"turnout_rate":0.8,
            "candidates":{"10":{"votes":7,"valid_share":1.0}}}

def minimal_panel():
    states=["AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", "MA", "MT", "MS", "MG", "PA", "PB", "PR", "PE", "PI", "RJ", "RN", "RS", "RO", "RR", "SC", "SP", "SE", "TO"]
    municipalities=[{"uf":states[i%27],"municipality_ibge":str(i+1000000),
                     "2022":year_row(),"2026":year_row()} for i in range(5570)]
    return {"matched_municipalities":5570,
            "candidate_options":{"2022":{"10":["CANDIDATURA FICTÍCIA"]},
                                 "2026":{"10":["CANDIDATURA FICTÍCIA"]}},
            "municipalities":municipalities}

def test_normalized_panel_counts_and_denominators():
    rows,meta=normalize_panel(minimal_panel())
    assert len(rows)==5570 and meta["municipalities"]==5570
    assert len(meta["municipalities_by_uf"])==27
    assert rows["1000000"]["2022"]["votes"]["10"]==7

def test_candidate_and_ballot_totals_rejected():
    data=year_row();data["candidates"]["10"]["votes"]=8
    with pytest.raises(ValueError,match="totals"):_validate_year(data)
    data=year_row();data["attended"]=9
    with pytest.raises(ValueError,match="totals"):_validate_year(data)

def test_inconsistent_turnout_denominator_rejected():
    data=year_row();data["turnout_rate"]=0.4
    with pytest.raises(ValueError,match="Turnout"):_validate_year(data)

def test_duplicate_geography_and_label_ambiguity_rejected():
    panel=minimal_panel()
    panel["municipalities"][1]["municipality_ibge"]=panel["municipalities"][0]["municipality_ibge"]
    with pytest.raises(ValueError,match="Duplicate"):normalize_panel(panel)
    panel=minimal_panel()
    panel["candidate_options"]["2022"]["10"]=["CANDIDATURA A","CANDIDATURA B"]
    with pytest.raises(ValueError,match="Ambiguous"):normalize_panel(panel)

def test_incomplete_coverage_rejected():
    panel=minimal_panel();panel["municipalities"].pop()
    with pytest.raises(ValueError,match="count changed"):normalize_panel(panel)

def test_am_denominator_exception_visible():
    panel=minimal_panel()
    panel["municipalities"][0]["municipality_ibge"]="1302603"
    rows,meta=normalize_panel(panel)
    assert rows["1302603"]["turnout_denominator_caveat"]
    assert meta["municipal_turnout_caveat_ibge"]=="1302603"
