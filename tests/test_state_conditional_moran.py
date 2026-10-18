"""Small synthetic topology checks for within-state Moran — not electoral data."""
import pytest

from electoral_analysis.state_conditional_moran import (
    conditional_permutations,
    prepare_within_state_graph,
    report_csv,
    study,
)


def fixture():
    records = {
        "a": {"uf": "AA", "baseline": -1, "ridge": 2, "ridge_regional": -2},
        "b": {"uf": "AA", "baseline": 0, "ridge": 0, "ridge_regional": 0},
        "c": {"uf": "AA", "baseline": 2, "ridge": -1, "ridge_regional": 2},
        "d": {"uf": "BB", "baseline": -2, "ridge": 4, "ridge_regional": -4},
        "e": {"uf": "BB", "baseline": 1, "ridge": 1, "ridge_regional": -1},
        "f": {"uf": "BB", "baseline": 100, "ridge": 100, "ridge_regional": 100},
    }
    # One boundary crossing between states and one isolated municipality.
    edges = [["a", "b"], ["b", "c"], ["d", "e"], ["a", "d"]]
    return records, edges


def test_interstate_edges_are_removed_and_isolates_excluded():
    records, edges = fixture()
    prepared = prepare_within_state_graph(records, edges)
    assert prepared["cross_state_edges_removed"] == 1
    assert prepared["within_state_edges"] == 3
    assert prepared["isolated_ibge_codes"] == ["f"]
    assert len(prepared["nodes"]) == 5
    assert sorted(prepared["groups"]) == ["AA", "BB"]


def test_uf_demeaning_invariant_to_state_offset():
    records, edges = fixture()
    prepared = prepare_within_state_graph(records, edges)
    original = conditional_permutations(records, prepared, "ridge", permutations=99)
    shifted = {k: dict(v) for k, v in records.items()}
    for record in shifted.values():
        record["ridge"] += 1000 if record["uf"] == "AA" else -9000
    new = conditional_permutations(shifted, prepared, "ridge", permutations=99)
    assert new["conditional_I"] == pytest.approx(original["conditional_I"])
    assert new["null_center_empirical"] == pytest.approx(original["null_center_empirical"])
    assert new["two_sided_permutation_p"] == original["two_sided_permutation_p"]


def test_fixed_seed_bootstrap_and_tabular_output():
    records, edges = fixture()
    adjacency = {"queen": {"edges": edges}, "rook": {"edges": edges[:-1]}}
    a = study(records, adjacency, permutations=99)
    b = study(records, adjacency, permutations=99)
    assert a == b
    summary = report_csv(a)
    assert "cross_uf_edges_removed" in summary
    assert summary.count("\n") == 7
    assert a["conditional_moran"]["queen"]["baseline"]["connected_nodes"] == 5


def test_empty_within_state_variation_rejected():
    records, edges = fixture()
    for record in records.values():
        record["ridge"] = 1 if record["uf"] == "AA" else -2
    prepared = prepare_within_state_graph(records, edges)
    with pytest.raises(ValueError, match="No within-UF variance"):
        conditional_permutations(records, prepared, "ridge", permutations=99)


def test_unknown_key_and_unavailable_graph_rejected():
    records, edges = fixture()
    with pytest.raises(ValueError, match="Unknown municipality"):
        prepare_within_state_graph(records, edges + [["a", "unknown"]])
    with pytest.raises(ValueError, match="Missing queen"):
        study(records, {"queen": {}, "rook": {"edges": edges}})
