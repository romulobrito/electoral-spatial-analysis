# ruff: noqa: ISC004  # Long report/figure text literals are wrapped for legibility.\n"""Render neutral aggregate model-error diagnostics into versioned SVG/Markdown."""
from __future__ import annotations

import argparse
import json
from html import escape
from pathlib import Path

MEASURES = (
    ("baseline_mae_pp", "Persistência histórica", "#94a3b8"),
    ("ridge_mae_pp", "Ridge", "#64748b"),
    ("regional_mae_pp", "Ridge + região", "#0d9488"),
)


def error_bars_svg(report: dict) -> str:
    """A model-performance graphic. No political/geographic propensity scores."""
    groups = report["macrorregions_alphabetical"]
    height = 125 + 80 * len(groups)
    high = max(group[name] for group in groups for name, _, _ in MEASURES) * 1.16
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 950 {height}" '
        'role="img" aria-label="Erros do comparecimento, por macrorregião">',
        f'<rect x="0" y="0" width="950" height="{height}" fill="white"/>',
        '<text x="24" y="30" font-size="18" font-family="Arial" font-weight="bold">'
        'Erro de comparecimento por macrorregião (MAE, pp)</text>',
        '<text x="24" y="49" font-size="12" font-family="Arial" fill="#475569">'
        'Resultados retrospectivos, com estado inteiro fora do treinamento</text>',
    ]
    for index, group in enumerate(groups):
        y = 85 + index * 80
        parts.append(
            f'<text x="24" y="{y + 18}" font-size="13" font-family="Arial">'
            f'{escape(group["region"])}</text>'
        )
        for pos, (name, _, color) in enumerate(MEASURES):
            value = group[name]
            length = 600 * value / high
            top = y + pos * 19 - 7
            parts.extend([
                f'<rect x="210" y="{top}" width="{length:.1f}" height="14" '
                f'rx="2" fill="{color}"/>',
                f'<text x="{218 + length:.1f}" y="{top + 12}" '
                f'font-size="11" font-family="Arial">{value:.3f}</text>',
            ])
    bottom = 85 + len(groups) * 80
    for index, (_, label, color) in enumerate(MEASURES):
        x = 25 + index * 270
        parts.append(f'<rect x="{x}" y="{bottom}" width="15" height="15" '
                     f'fill="{color}"/>')
        parts.append(f'<text x="{x + 23}" y="{bottom + 13}" '
                     f'font-size="12" font-family="Arial">{escape(label)}</text>')
    parts.append(f'<text x="24" y="{height - 13}" font-size="10" '
                 'font-family="Arial" fill="#64748b">Fonte: TSE, IBGE e auditoria '
                 'E007 · 5.569 municípios · Sem inferência de preferência política</text>')
    parts.append("</svg>")
    return "\n".join(parts) + "\n"


def markdown_report(report: dict) -> str:
    overall = report["overall"]
    intervals = report["state_cluster_bootstrap"]["percentile_95_intervals_pp"]
    def number(x):
        return f"{x:.4f}"
    lines = [
        "# E007 — Resíduos regionais do comparecimento municipal",
        "",
        "**Escopo:** participação eleitoral agregada de 2022–2026, "
        "sem previsão de apoio a candidato ou segmentação política.",
        "",
        "## Erros em estados reservados para avaliação",
        "",
        "| Método | MAE (pp) |",
        "| --- | ---: |",
        f'| Persistência histórica | {number(overall["baseline_mae_pp"])} |',
        f'| Ridge com Censo 2022 | {number(overall["ridge_mae_pp"])} |',
        f'| Ridge com intercepto macrorregional estimado apenas no treino | '
        f'**{number(overall["regional_mae_pp"])}** |',
        "",
        f'Avaliação sobre **{overall["municipalities"]} municípios**, '
        "com 27 estados/DF reservados individualmente para teste.",
        "",
        "## Sensibilidade por reamostragem de estados",
        "",
    ]
    for name, label in (
        ("ridge_minus_baseline_mae_pp", "Ridge menos persistência"),
        ("regional_minus_ridge_mae_pp", "Correção regional menos ridge"),
    ):
        bounds = intervals[name]
        lines.append(
            f'- {label}: diferença média '
            f'{number(overall[name])} pp; intervalo bootstrap 95% '
            f'[{number(bounds[0])}, {number(bounds[1])}] pp.'
        )
    lines += [
        "",
        "## Diagnósticos por macrorregião",
        "",
        "| Macrorregião | Municípios | MAE ridge | MAE com região | Viés assinado ridge (pp) |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]
    for item in report["macrorregions_alphabetical"]:
        lines.append(
            f'| {item["region"]} | {item["municipalities"]} | '
            f'{number(item["ridge_mae_pp"])} | {number(item["regional_mae_pp"])} | '
            f'{number(item["ridge_mean_signed_residual_pp"])} |'
        )
    lines += [
        "",
        "![Erros de comparecimento por macrorregião](region_error.svg)",
        "",
        f'Parcela descritiva da variação residual entre estados: '
        f'**{number(report["state_residual_eta_squared"] * 100)}%**. '
        "**Não é Moran’s I ou um teste formal de autocorrelação espacial.**",
        "",
        "## Limitações metodológicas",
        "",
        "- Esta correção regional foi proposta **depois** da análise E006. "
        "O experimento é exploratório e os intervalos não demonstram "
        "vantagem confirmatória em outra eleição.",
        "- O erro de cada estado é avaliado sem os seus próprios dados no ajuste, "
        "inclusive na correção por macrorregião (shrinkage fixo 100).",
        "- A publicação de indicadores censitários pode ser posterior ao pleito de 2022. "
        "Não se reivindica previsão operacional ex-ante em 2022.",
        "- O estudo não estima preferências individuais ou de bairros, nem "
        "probabilidades de votos futuros para qualquer candidatura.",
        "",
        "## Proveniência",
        "",
        "Fontes agregadas oficiais: TSE 2022/2026, Censo IBGE 2022, "
        "chaves municipais TSE–IBGE; hashes de E005/E006 fixados no workflow.",
    ]
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("input_json", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    if args.output_dir.exists():
        parser.error("Output already exists")
    report = json.loads(args.input_json.read_text(encoding="utf-8"))
    args.output_dir.mkdir(parents=True)
    (args.output_dir / "region_error.svg").write_text(error_bars_svg(report), encoding="utf-8")
    (args.output_dir / "findings.md").write_text(markdown_report(report), encoding="utf-8")
    print("E007 diagnostics visualizations and report rendered")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
