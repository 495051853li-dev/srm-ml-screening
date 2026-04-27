"""Batch-oriented controller for the SRM literature retrieval and extraction pipeline.

This runner intentionally stays lightweight:

- it orchestrates stages in order
- it allows partial reruns by stage name
- it avoids embedding heavy retry or resume logic directly here

Stage-specific resume / skip / retry behavior should live in the stage scripts
themselves, especially for network-facing steps such as source fetching.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path
from typing import Dict, List


ROOT = Path(__file__).resolve().parent.parent

STAGE_COMMANDS: Dict[str, List[List[str]]] = {
    "stage1_search_candidates": [[sys.executable, "src/build_candidate_master.py"]],
    "stage2_enrich_journal_metrics": [[sys.executable, "src/enrich_journal_metrics.py"]],
    "stage3_score_and_filter": [[sys.executable, "src/score_and_filter_batch.py"]],
    "stage4_fetch_sources": [[
        sys.executable,
        "src/fetch_sources_stage4.py",
        "--input",
        "data/processed/eligible_high_if_pool.csv",
        "--output",
        "data/processed/fulltext_fetch_manifest.csv",
        "--limit",
        "50",
        "--skip-existing",
    ]],
    "stage5_extract_fields": [[
        sys.executable, "src/auto_extract_srm_draft.py",
        "--candidates", "data/processed/candidate_papers_high_if_scored.csv",
        "--fetch-log", "data/processed/fulltext_fetch_manifest.csv",
        "--output", "data/processed/srm_extraction_auto_draft.csv",
    ]],
    "stage6_qc_and_freeze": [[sys.executable, "src/qc_and_freeze_batch.py"]],
    "stage7_analysis_ready_exports": [[sys.executable, "src/export_analysis_ready.py"]],
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the batch SRM literature pipeline by stage.")
    parser.add_argument("--stages", nargs="*", default=list(STAGE_COMMANDS.keys()))
    parser.add_argument("--refresh-search", action="store_true", help="Rerun OpenAlex/Crossref retrieval before building the master pool.")
    parser.add_argument("--list-stages", action="store_true", help="Print available stage names and exit.")
    return parser.parse_args()


def run_command(command: List[str]) -> None:
    print(f"[batch-pipeline] running: {' '.join(command)}")
    subprocess.run(command, cwd=ROOT, check=True)


def main() -> int:
    args = parse_args()
    if args.list_stages:
        for stage in STAGE_COMMANDS:
            print(stage)
        return 0

    requested_stages = args.stages
    if args.refresh_search and "stage1_search_candidates" in requested_stages:
        run_command([sys.executable, "src/run_literature_pipeline.py"])

    for stage in requested_stages:
        if stage not in STAGE_COMMANDS:
            raise ValueError(f"Unknown stage: {stage}")
        for command in STAGE_COMMANDS[stage]:
            run_command(command)

    print("[batch-pipeline] completed stages:", ", ".join(requested_stages))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
