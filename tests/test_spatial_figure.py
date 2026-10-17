from electoral_analysis.spatial_figure import build_svg


def test_moran_figure_contains_both_graph_definitions():
    report = {
        "moran": {
            model: {"queen": {"I": 0.1}, "rook": {"I": 0.08}}
            for model in ("baseline", "ridge", "ridge_regional")
        }
    }
    output = build_svg(report)
    assert output.startswith("<svg")
    assert "Queen" in output
    assert "Rook" in output
    assert "Moran" in output
