# ruff: noqa: ISC004  # Wrapped explanatory SVG literals.\n"""Lightweight explanatory SVG of Moran's I diagnostics: no targeting maps."""
from __future__ import annotations

import argparse
import json
from pathlib import Path


def build_svg(report: dict) -> str:
    """Compare three residual types for queen and rook with a common axis."""
    data = report["moran"]
    order = ("baseline", "ridge", "ridge_regional")
    labels = ("Persistência", "Ridge", "Ridge + região")
    variants = (("queen", "#0d9488"), ("rook", "#64748b"))
    low = min(data[m][g]["I"] for m in order for g, _ in variants)
    high = max(data[m][g]["I"] for m in order for g, _ in variants)
    low = min(-0.05, low - 0.04)
    high = max(0.05, high + 0.04)
    def x(value: float) -> float:
        return 255 + (value-low) * 600 / (high-low)
    segments = [
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1000 425" '
        'role="img" aria-label="Índice global de Moran dos erros de comparecimento">',
        '<rect width="1000" height="425" fill="white"/>',
        '<text x="28" y="34" font-size="21" font-family="Arial" font-weight="bold">'
        'Autocorrelação espacial dos resíduos: Moran I</text>',
        '<text x="28" y="58" font-family="Arial" font-size="13" fill="#475569">'
        'UFs inteiras reservadas para teste; pesos padronizados por linha</text>',
    ]
    if low < 0 < high:
        zero=x(0)
        segments.append(
            f'<line x1="{zero:.1f}" y1="85" x2="{zero:.1f}" y2="325" '
            'stroke="#a1a1aa" stroke-width="1" stroke-dasharray="4,4"/>'
        )
    for i, (model, label) in enumerate(zip(order, labels)):
        y = 124+i*84
        segments.append(f'<text x="28" y="{y+13}" font-family="Arial" '
                        f'font-size="15">{label}</text>')
        for j, (contiguity, color) in enumerate(variants):
            value = data[model][contiguity]["I"]
            yy=y+j*27
            xx=x(value)
            segments += [
                f'<line x1="{min(x(0),xx):.1f}" y1="{yy}" '
                f'x2="{max(x(0),xx):.1f}" y2="{yy}" stroke="{color}" stroke-width="7"/>',
                f'<circle cx="{xx:.1f}" cy="{yy}" r="6" fill="{color}"/>',
                f'<text x="{min(xx+12,915):.1f}" y="{yy+5}" font-size="12" '
                f'font-family="Arial">{value:+.4f}</text>',
            ]
    segments += [
        '<rect x="28" y="350" width="15" height="15" fill="#0d9488"/>',
        '<text x="50" y="363" font-family="Arial" font-size="13">Queen (toque)</text>',
        '<rect x="258" y="350" width="15" height="15" fill="#64748b"/>',
        '<text x="280" y="363" font-family="Arial" font-size="13">Rook (fronteira)</text>',
        '<text x="28" y="394" font-family="Arial" font-size="11" fill="#475569">'
        'Fonte: IBGE 2022, TSE E005 e E007. Diagnóstico exploratório, não causal.</text>',
        '</svg>',
    ]
    return "\n".join(segments) + "\n"


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("input", type=Path)
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args()
    if args.out.exists():
        p.error("Figure already exists")
    report = json.loads(args.input.read_text(encoding="utf-8"))
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(build_svg(report), encoding="utf-8")
    print("E008 Moran figure generated")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
