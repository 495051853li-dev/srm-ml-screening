"""Export analysis-preparation datasets from batch extraction outputs."""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Export analysis-ready SRM datasets without modeling.")
    parser.add_argument("--draft-input", default="data/processed/srm_extraction_auto_draft.csv")
    parser.add_argument("--flags-input", default="data/processed/srm_extraction_record_flags.csv")
    parser.add_argument("--scored-input", default="data/processed/candidate_papers_high_if_scored.csv")
    parser.add_argument("--output", default="data/processed/analysis_ready_dataset.csv")
    parser.add_argument("--ni-output", default="data/processed/analysis_ready_ni_based_high_if.csv")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    draft = pd.read_csv(args.draft_input)
    flags = pd.read_csv(args.flags_input)
    scored = pd.read_csv(args.scored_input)

    merged = draft.merge(
        flags[["paper_id", "analysis_ready_flag", "freeze_recommendation", "human_sample_review_flag"]],
        on="paper_id",
        how="left",
    ).merge(
        scored[
            [
                "paper_id",
                "journal_impact_factor_year",
                "journal_impact_factor",
                "journal_quartile",
                "needs_manual_journal_check",
                "likely_ni_based",
                "final_priority_label",
                "priority_score",
            ]
        ],
        on="paper_id",
        how="left",
    )

    analysis_ready = merged[merged["analysis_ready_flag"] == "yes"].copy()
    ni_high_if = analysis_ready[
        (analysis_ready["likely_ni_based"] == "yes")
        & (pd.to_numeric(analysis_ready["journal_impact_factor"], errors="coerce") >= 6.0)
    ].copy()

    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    analysis_ready.to_csv(args.output, index=False, encoding="utf-8")
    ni_high_if.to_csv(args.ni_output, index=False, encoding="utf-8")

    print(f"Analysis-ready rows: {len(analysis_ready)}")
    print(f"Ni-based high-IF rows: {len(ni_high_if)}")
    print(f"Output: {args.output}")
    print(f"Ni output: {args.ni_output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
