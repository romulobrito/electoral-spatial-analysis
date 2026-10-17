"""CLI for explicit download/inventory and section-turnout audit."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from .acquisition import download_official
from .audit import audit_turnout_zip
from .sources import RESOURCES, resource_manifest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="electoral-audit")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("sources", help="Print source inventory without downloading")
    download = sub.add_parser("download", help="Fetch a verified TSE archive, never overwrite")
    download.add_argument("key", choices=sorted(RESOURCES))
    download.add_argument("--output-dir", type=Path, default=Path("data/bronze"))
    audit = sub.add_parser("audit-turnout", help="Audit a locally available turnout-detail ZIP")
    audit.add_argument("zip_path", type=Path)
    audit.add_argument("--year", type=int, choices=(2022, 2026), required=True)
    audit.add_argument("--member", default=None)
    audit.add_argument("--max-rows", type=int, default=None,
                       help="Diagnostic only: marks report as partial")
    audit.add_argument("--output", type=Path, default=None)
    args = parser.parse_args(argv)
    if args.command == "sources":
        result = resource_manifest()
    elif args.command == "download":
        result = download_official(RESOURCES[args.key], args.output_dir)
    else:
        result = audit_turnout_zip(args.zip_path, year=args.year, member_name=args.member,
                                   max_rows=args.max_rows)
    message = json.dumps(result, indent=2, ensure_ascii=False)
    if args.command == "audit-turnout" and args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        if args.output.exists():
            parser.error("Output exists; choose a new path to preserve audit history")
        args.output.write_text(message + "\n", encoding="utf-8")
        print(f"Audit report written to {args.output}")
    else:
        print(message)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
