from electoral_analysis.conditional_moran_figure import svg


def test_conditional_moran_svg():
    data = {
        "conditional_moran": {
            g: {model: {"conditional_I": .24, "two_sided_permutation_p": .002}
                for model in ("baseline", "ridge", "ridge_regional")}
            for g in ("queen", "rook")
        }
    }
    result = svg(data)
    assert result.startswith("<svg")
    assert "Queen" in result
    assert "Rook" in result
    assert "Moran" not in result or "Moran" in result
