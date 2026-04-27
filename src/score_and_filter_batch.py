"""Batch scoring and filtering for large-scale SRM candidate pools."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Dict, List

import pandas as pd


OUTPUT_COLUMNS = [
    "paper_id",
    "title",
    "first_author",
    "publication_year",
    "journal",
    "doi",
    "abstract_or_summary",
    "source_api",
    "is_open_access",
    "has_abstract",
    "has_fulltext",
    "document_type",
    "retrieval_query",
    "retrieval_date",
    "screening_status",
    "screening_notes",
    "normalized_title",
    "dedup_key_doi",
    "dedup_key_title_year",
    "duplicate_resolution_basis",
    "master_screening_bucket",
    "non_target_flag",
    "journal_impact_factor_year",
    "journal_impact_factor",
    "journal_quartile",
    "journal_metrics_source",
    "journal_metrics_notes",
    "needs_manual_journal_check",
    "relevance_score",
    "extractability_score",
    "journal_quality_score",
    "priority_score",
    "likely_ni_based",
    "likely_contains_conditions",
    "likely_contains_performance",
    "exclude_reason",
    "priority_rationale",
    "final_priority_label",
    "priority_rank",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Score and filter an enriched SRM candidate pool.")
    parser.add_argument("--input", default="data/processed/candidate_papers_master_enriched.csv")
    parser.add_argument("--scored-output", default="data/processed/candidate_papers_high_if_scored.csv")
    parser.add_argument("--eligible-output", default="data/processed/eligible_high_if_pool.csv")
    parser.add_argument("--backup-output", default="data/processed/backup_low_if_pool.csv")
    parser.add_argument("--top50-output", default="data/processed/candidate_papers_top50.csv")
    parser.add_argument("--top100-output", default="data/processed/candidate_papers_top100.csv")
    parser.add_argument("--summary-output", default="outputs/tables/batch_scoring_summary.json")
    return parser.parse_args()


def normalize_text(value: str) -> str:
    value = (value or "").lower()
    value = re.sub(r"\s+", " ", value)
    return value.strip()


def contains_any(text: str, patterns: List[str]) -> bool:
    return any(pattern in text for pattern in patterns)


def matches_any_regex(text: str, patterns: List[str]) -> bool:
    return any(re.search(pattern, text) for pattern in patterns)


def to_float(value: object) -> float | None:
    text = "" if pd.isna(value) else str(value).strip()
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def journal_quality_score(impact_factor: float | None) -> int:
    if impact_factor is None:
        return 0
    if impact_factor >= 10:
        return 100
    if impact_factor >= 6:
        return 85
    if impact_factor >= 3:
        return 55
    return 25


def score_row(row: Dict[str, object]) -> Dict[str, object]:
    title = normalize_text(str(row.get("title", "") if not pd.isna(row.get("title", "")) else ""))
    abstract = normalize_text(str(row.get("abstract_or_summary", "") if not pd.isna(row.get("abstract_or_summary", "")) else ""))
    text = f"{title} {abstract}".strip()
    document_type = str(row.get("document_type", "") if not pd.isna(row.get("document_type", "")) else "").strip()
    impact_factor = to_float(row.get("journal_impact_factor"))

    strong_srm_markers = ["steam reforming of methane", "methane steam reforming", "steam reforming methane"]
    medium_srm_markers = ["steam reforming", "srm"]
    methane_markers = ["methane", "ch4"]
    catalyst_markers = ["catalyst", "catalysts", "nickel", "ni/", "support", "ceria", "alumina"]
    ni_markers = ["ni-based", "ni based", "nickel", "ni/"]
    condition_markers = ["temperature", "steam-to-carbon", "steam to carbon", "s/c", "pressure", "ghsv", "whsv", "time on stream", "tos"]
    performance_markers = ["conversion", "yield", "selectivity", "performance", "activity", "stability", "hydrogen production", "carbon deposition", "coking"]
    exclusion_patterns = [
        r"\bmethanol\b", r"\bethanol\b", r"\bethane\b", r"\bpropane\b", r"\bdry reforming\b",
        r"\bautothermal\b", r"\bpartial oxidation\b", r"\bpatent\b", r"\bcombined dry[- ]steam reforming\b",
        r"\bdry[- ]steam reforming\b", r"\bwater gas shift\b",
    ]

    relevance_score = 0
    extractability_score = 0
    exclude_reason = ""

    if matches_any_regex(text, exclusion_patterns) or str(row.get("non_target_flag", "")).strip().lower() == "yes":
        exclude_reason = "likely_non_target_or_mixed_system"

    if contains_any(text, strong_srm_markers):
        relevance_score += 50
    elif "steam reform" in text and contains_any(text, methane_markers):
        relevance_score += 40
    elif contains_any(text, medium_srm_markers) and contains_any(text, methane_markers):
        relevance_score += 25
    if contains_any(text, methane_markers):
        relevance_score += 15
    if contains_any(text, catalyst_markers):
        relevance_score += 10
    if contains_any(text, ni_markers):
        relevance_score += 20

    likely_ni_based = "yes" if contains_any(text, ni_markers) else "no"
    likely_contains_conditions = "yes" if contains_any(text, condition_markers) else "no"
    likely_contains_performance = "yes" if contains_any(text, performance_markers) else "no"

    if document_type == "journal_article":
        extractability_score += 25
    elif document_type == "review":
        extractability_score += 5
    if str(row.get("has_abstract", "")).strip().lower() == "yes":
        extractability_score += 15
    if str(row.get("has_fulltext", "")).strip().lower() == "yes":
        extractability_score += 15
    if str(row.get("doi", "")).strip():
        extractability_score += 10
    if likely_contains_conditions == "yes":
        extractability_score += 20
    if likely_contains_performance == "yes":
        extractability_score += 15
    if document_type == "review":
        extractability_score -= 10

    relevance_score = max(0, min(100, relevance_score))
    extractability_score = max(0, min(100, extractability_score))
    journal_score = journal_quality_score(impact_factor)
    priority_score = round(relevance_score * 0.30 + extractability_score * 0.20 + journal_score * 0.50, 1)

    if impact_factor is None:
        journal_note = "期刊IF缺失，需人工核查"
    elif impact_factor >= 10:
        journal_note = "期刊IF>=10，最高优先"
    elif impact_factor >= 6:
        journal_note = "期刊IF>=6，高优先"
    elif impact_factor >= 3:
        journal_note = "期刊IF介于3和6之间，中等优先"
    else:
        journal_note = "期刊IF<3，低优先"

    if exclude_reason:
        final_priority_label = "exclude"
    elif (
        document_type == "journal_article"
        and impact_factor is not None
        and impact_factor >= 6.0
        and relevance_score >= 70
        and extractability_score >= 45
        and likely_contains_performance == "yes"
    ):
        final_priority_label = "top_priority" if likely_ni_based == "yes" else "medium_priority"
    else:
        final_priority_label = "low_priority"

    row["relevance_score"] = relevance_score
    row["extractability_score"] = extractability_score
    row["journal_quality_score"] = journal_score
    row["priority_score"] = priority_score
    row["likely_ni_based"] = likely_ni_based
    row["likely_contains_conditions"] = likely_contains_conditions
    row["likely_contains_performance"] = likely_contains_performance
    row["exclude_reason"] = exclude_reason
    row["priority_rationale"] = "；".join(
        part for part in [
            journal_note,
            "存在Ni-based信号" if likely_ni_based == "yes" else "",
            "更可能包含条件字段" if likely_contains_conditions == "yes" else "",
            "更可能包含性能字段" if likely_contains_performance == "yes" else "",
            "review仅保留为背景参考" if document_type == "review" else "",
        ] if part
    )
    row["final_priority_label"] = final_priority_label
    return row


def main() -> int:
    args = parse_args()
    df = pd.read_csv(args.input)
    scored_df = pd.DataFrame([score_row(dict(row)) for row in df.to_dict(orient="records")])
    label_order = {"top_priority": 0, "medium_priority": 1, "low_priority": 2, "exclude": 3}
    scored_df = scored_df.sort_values(
        by=["final_priority_label", "priority_score", "journal_quality_score", "relevance_score", "extractability_score", "publication_year", "title"],
        ascending=[True, False, False, False, False, False, True],
        key=lambda s: s.map(label_order) if s.name == "final_priority_label" else s,
    ).reset_index(drop=True)
    scored_df["priority_rank"] = scored_df.index + 1

    eligible_df = scored_df[
        (scored_df["document_type"] == "journal_article")
        & (pd.to_numeric(scored_df["journal_impact_factor"], errors="coerce") >= 6.0)
        & (scored_df["final_priority_label"].isin(["top_priority", "medium_priority"]))
    ].copy()
    backup_df = scored_df[(~scored_df["paper_id"].isin(eligible_df["paper_id"])) & (scored_df["final_priority_label"] != "exclude")].copy()
    top50_df = scored_df.head(50).copy()
    top100_df = scored_df.head(100).copy()

    Path(args.scored_output).parent.mkdir(parents=True, exist_ok=True)
    for path, out_df in [
        (args.scored_output, scored_df),
        (args.eligible_output, eligible_df),
        (args.backup_output, backup_df),
        (args.top50_output, top50_df),
        (args.top100_output, top100_df),
    ]:
        out_df[OUTPUT_COLUMNS].to_csv(path, index=False, encoding="utf-8")

    summary = {
        "scored_rows": int(len(scored_df)),
        "eligible_high_if_pool": int(len(eligible_df)),
        "backup_low_if_pool": int(len(backup_df)),
        "top50_rows": int(len(top50_df)),
        "top100_rows": int(len(top100_df)),
        "ni_based_top_priority_rows": int(len(scored_df[(scored_df["final_priority_label"] == "top_priority") & (scored_df["likely_ni_based"] == "yes")])),
    }
    Path(args.summary_output).parent.mkdir(parents=True, exist_ok=True)
    Path(args.summary_output).write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print(f"Scored output: {args.scored_output}")
    print(f"Eligible pool: {args.eligible_output}")
    print(f"Backup pool: {args.backup_output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
