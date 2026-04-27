"""Legacy wrapper for stage4 fetching against the scored candidate pool.

This script is kept for compatibility with earlier project commands.
It now delegates to the canonical `src/fetch_sources_stage4.py` logic.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from fetch_sources_stage4 import main as stage4_main


ROOT = Path(__file__).resolve().parent.parent


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Legacy top-priority fetch wrapper.")
    parser.add_argument("--input", default="data/processed/candidate_papers_scored.csv")
    parser.add_argument("--openalex-raw", default="outputs/tables/openalex_raw_results.csv")
    parser.add_argument("--crossref-raw", default="outputs/tables/crossref_raw_results.csv")
    parser.add_argument("--output-log", default="data/processed/fulltext_fetch_manifest.csv")
    parser.add_argument("--output-dir", default="outputs/fulltext")
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--timeout", type=int, default=45)
    parser.add_argument("--sleep", type=float, default=0.5)
    parser.add_argument("--retry-failed", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    forwarded = [
        sys.executable,
        str(ROOT / "src" / "fetch_sources_stage4.py"),
        "--input",
        args.input,
        "--openalex-raw",
        args.openalex_raw,
        "--crossref-raw",
        args.crossref_raw,
        "--output",
        args.output_log,
        "--output-dir",
        args.output_dir,
        "--limit",
        str(args.limit),
        "--timeout",
        str(args.timeout),
        "--sleep",
        str(args.sleep),
        "--only-ready-pool",
        "--skip-existing",
    ]
    if args.retry_failed:
        forwarded.append("--retry-failed")

    # Reuse the canonical stage4 process by replacing argv.
    old_argv = sys.argv
    try:
        sys.argv = [forwarded[1], *forwarded[2:]]
        return stage4_main()
    finally:
        sys.argv = old_argv


if __name__ == "__main__":
    raise SystemExit(main())
