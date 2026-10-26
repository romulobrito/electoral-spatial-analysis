"""Reproducible description of archived partial totals, NOT live forecast."""
from __future__ import annotations
import argparse
import csv
import json
from pathlib import Path


def audit(path: Path) -> dict:
    with path.open(encoding="utf-8", newline="") as f:
        records = list(csv.DictReader(f))
    if len(records) != 34:
        raise ValueError("Expected 34 archived observations")
    rows = []
    for r in records:
        if set(r) != {"timestamp_brt", "progress_sections_pct", "observed_valid_A", "observed_valid_B", "archive_source"}:
            raise ValueError("Unexpected partial snapshot fields")
        progress = float(r["progress_sections_pct"])
        a, b = int(r["observed_valid_A"]), int(r["observed_valid_B"])
        if not 0 < progress <= 100 or min(a, b) < 0:
            raise ValueError("Invalid observed count/progress")
        rows.append({"time": r["timestamp_brt"], "progress_pct": progress,
                     "a": a, "b": b, "archive": r["archive_source"]})
    for p,q in zip(rows,rows[1:]):
        if not (p["time"] < q["time"] and p["a"] <= q["a"] and p["b"] <= q["b"]
                and p["progress_pct"] <= q["progress_pct"]):
            raise ValueError("Unordered or decreasing historical partial totals")
    if rows[-1]["progress_pct"] != 100:
        raise ValueError("Last row is not full totalization")
    final = 100 * rows[-1]["a"] / (rows[-1]["a"]+rows[-1]["b"])
    table=[]
    for r in rows:
        partial = 100*r["a"]/(r["a"]+r["b"])
        table.append({"timestamp_brt":r["time"],"progress_sections_pct":r["progress_pct"],
                      "partial_share_A_pct":partial,"final_share_A_pct":final,
                      "naive_absolute_difference_pp":abs(partial-final),
                      "archive_source":r["archive"]})
    return {"stage":"E014", "kind":"descriptive_partial_archive",
            "note":"NOT a historical projection model, nor evidence of model accuracy",
            "final_share_A_pct":final, "records":table,
            "limitations":["Third-party archived partials; original TSE time-specific JSON hashes unavailable",
                           "Progress percentages refer to sections, not valid votes",
                           "No public historical model estimates or interval coverage assessed",
                           "These observations cannot validate Mahlmeister model performance"]}


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--source",type=Path,required=True)
    p.add_argument("--out",type=Path,required=True)
    a=p.parse_args()
    if a.out.exists():p.error("Refusing overwrite")
    result=audit(a.source)
    a.out.parent.mkdir(parents=True,exist_ok=True)
    a.out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("Audited",len(result["records"]),"observed partial snapshots")


if __name__ == "__main__":
    main()
