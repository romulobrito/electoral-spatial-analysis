"""Plot only aggregate model-error Moran I under state-conditioned nulls."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

MODELS = (
    ("baseline", "Persistência"),
    ("ridge", "Ridge"),
    ("ridge_regional", "Ridge + região"),
)
PALETTE = (("queen", "#0d9488"), ("rook", "#64748b"))


def svg(report: dict) -> str:
    results = report["conditional_moran"]
    observed = [results[g][m]["conditional_I"] for m, _ in MODELS for g, _ in PALETTE]
    lo = min(-0.06, min(observed) - 0.05)
    hi = max(0.06, max(observed) + 0.05)

    def xpos(value: float) -> float:
        return 290 + 550 * (value - lo) / (hi - lo)

    content = [
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 990 395" '
        'role="img" aria-label="Moran residual condicionado às unidades federativas">',
        '<rect width="990" height="395" fill="white"/>',
        '<text x="25" y="35" font-family="Arial" font-size="21" font-weight="bold">'
        'Autocorrelação dos resíduos dentro dos estados</text>',
        '<text x="25" y="58" font-family="Arial" font-size="13" fill="#475569">'
        'Grafo intrauf, resíduos centrados por UF e permutações restritas à UF</text>',
    ]
    zero = xpos(0)
    content.append(
        f'<line x1="{zero:.1f}" y1="80" x2="{zero:.1f}" y2="317" '
        'stroke="#94a3b8" stroke-dasharray="4,4"/>'
    )
    for i, (method, label) in enumerate(MODELS):
        y = 118 + i * 83
        content.append(
            f'<text x="25" y="{y+8}" font-family="Arial" font-size="15">{label}</text>'
        )
        for j, (graph, color) in enumerate(PALETTE):
            cell = results[graph][method]
            value = cell["conditional_I"]
            xp = xpos(value)
            yp = y - 8 + 23*j
            content.extend([
                f'<circle cx="{xp:.1f}" cy="{yp}" r="7" fill="{color}"/>',
                f'<text x="{min(xp+12,910):.1f}" y="{yp+5}" '
                f'font-size="12" font-family="Arial">{value:+.4f}</text>',
            ])
    content.extend([
        '<circle cx="35" cy="353" r="6" fill="#0d9488"/>',
        '<text x="50" y="358" font-size="12" font-family="Arial">Queen</text>',
        '<circle cx="163" cy="353" r="6" fill="#64748b"/>',
        '<text x="178" y="358" font-size="12" font-family="Arial">Rook</text>',
        '<text x="25" y="380" font-family="Arial" font-size="11" fill="#64748b">'
        'Fontes: IBGE 2022, TSE E005/E007. Estudo exploratório, sem inferência causal.</text>',
        '</svg>',
    ])
    return "\n".join(content) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if args.out.exists():
        parser.error("Refusing to overwrite an existing figure")
    data = json.loads(args.source.read_text(encoding="utf-8"))
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(svg(data), encoding="utf-8")
    print("State-conditioned Moran graphic rendered")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
