"""E018 observed-only diagnostic charts for snapshot replay."""
from __future__ import annotations

import argparse
import csv
from datetime import datetime
from pathlib import Path


def render(source: Path, dest: Path, *, label: str) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    rows = list(csv.DictReader(source.open(encoding="utf-8", newline="")))
    if not rows:
        raise ValueError("No data")
    dates = [datetime.fromisoformat(row["received_utc"].replace("Z", "+00:00"))
             for row in rows]
    for field, title, name in (
        ("observed_turnout_pct", "Turnout observed in already reported sections", "turnout"),
        ("section_coverage_pct", "Sections reported among currently observed units", "coverage"),
    ):
        fig, ax = plt.subplots(figsize=(9, 4.5))
        ax.plot(dates, [float(row[field]) if row[field] else float("nan")
                        for row in rows], marker="o")
        ax.set_title(f"E018: {title} — {label}")
        ax.set_xlabel("Snapshot receipt time (UTC)")
        ax.set_ylabel("Percentage (%)")
        ax.grid(alpha=.25)
        fig.autofmt_xdate()
        fig.tight_layout()
        dest.mkdir(parents=True, exist_ok=True)
        fig.savefig(dest / f"{name}.png", dpi=160)
        fig.savefig(dest / f"{name}.svg")
        plt.close(fig)


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--source", type=Path, required=True)
    p.add_argument("--out-dir", type=Path, required=True)
    p.add_argument("--label", default="UNVERIFIED INPUT")
    args = p.parse_args()
    render(args.source, args.out_dir, label=args.label)


if __name__ == "__main__":
    main()
