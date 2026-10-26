"""Render neutral municipal-turnout calibration figures from official-run CSV."""
from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path


def render(source: Path, metadata: Path, out_dir: Path) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    rows = list(csv.DictReader(source.open(encoding="utf-8", newline="")))
    config = json.loads(metadata.read_text(encoding="utf-8"))
    out_dir.mkdir(parents=True, exist_ok=True)
    selected = config["selection"]["selected"]
    names = ("uf_shrunk_swing", "e016_guarded_quadratic",
             "e017_moderate_quadratic", "e017_permissive_quadratic", selected)
    names = list(dict.fromkeys(names))
    phases = ("development", "evaluation")
    scenarios = ("uniform_municipality_random", "balanced_uf_random")
    for phase in phases:
        for metric, label, filename in (
            ("mean_abs_error_pp", "MAE (percentage points)", "mae"),
            ("fallback_fraction", "Fallback fraction", "fallback"),
            ("max_abs_error_pp", "Maximum absolute error (pp)", "tail"),
        ):
            fig, ax = plt.subplots(figsize=(9, 5))
            for scenario in scenarios:
                for name in names:
                    subset = sorted(
                        (r for r in rows if r["phase"] == phase
                         and r["scenario"] == scenario and r["method"] == name),
                        key=lambda r: float(r["threshold_pct"]),
                    )
                    if subset:
                        x = [float(r["threshold_pct"]) for r in subset]
                        y = [float(r[metric]) for r in subset]
                        ax.plot(x, y, marker="o", markersize=3,
                                label=f"{name} | {scenario}")
            ax.set_xscale("log")
            ax.set_xlabel("Revealed electorate (%) — synthetic municipal orders")
            ax.set_ylabel(label)
            ax.set_title(f"E017: {label} — {phase}")
            ax.grid(alpha=.25)
            ax.legend(fontsize=6, ncol=2)
            fig.tight_layout()
            fig.savefig(out_dir / f"{phase}_{filename}.png", dpi=160)
            fig.savefig(out_dir / f"{phase}_{filename}.svg")
            plt.close(fig)


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--source", type=Path, required=True)
    p.add_argument("--metadata", type=Path, required=True)
    p.add_argument("--out-dir", type=Path, required=True)
    args = p.parse_args()
    render(args.source, args.metadata, args.out_dir)


if __name__ == "__main__":
    main()
