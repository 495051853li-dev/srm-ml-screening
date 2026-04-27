"""Re-rank SRM candidate papers with journal impact factor as a first-batch screening priority."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Dict, List

import pandas as pd

SECONDARY_EXCLUSION_PATTERNS = [
    r"\bdry[- ]steam reforming\b",
    r"\bcombined dry[- ]steam reforming\b",
    r"\bwater gas shift\b",
]


HIGH_IF_SCORED_COLUMNS = [
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
    "old_priority_score",
    "old_final_priority_label",
    "old_priority_rank",
    "final_priority_label",
]

PRIORITY_COLUMNS = [
    "paper_id",
    "title",
    "first_author",
    "publication_year",
    "journal",
    "doi",
    "document_type",
    "journal_impact_factor_year",
    "journal_impact_factor",
    "journal_quartile",
    "journal_metrics_source",
    "needs_manual_journal_check",
    "relevance_score",
    "extractability_score",
    "journal_quality_score",
    "priority_score",
    "likely_ni_based",
    "likely_contains_conditions",
    "likely_contains_performance",
    "priority_rationale",
    "screening_notes",
]

BACKUP_COLUMNS = PRIORITY_COLUMNS + ["exclude_reason", "old_final_priority_label"]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="High-impact-factor-first screening for SRM candidate papers.")
    parser.add_argument("--candidate-input", default="data/processed/candidate_papers.csv")
    parser.add_argument("--scored-input", default="data/processed/candidate_papers_scored.csv")
    parser.add_argument("--old-priority-input", default="data/processed/first_batch_priority_papers.csv")
    parser.add_argument("--journal-lookup", default="data/processed/journal_metrics_lookup_curated.csv")
    parser.add_argument("--high-if-output", default="data/processed/candidate_papers_high_if_scored.csv")
    parser.add_argument("--first-batch-output", default="data/processed/first_batch_priority_papers_if6plus.csv")
    parser.add_argument("--backup-output", default="data/processed/backup_low_if_papers.csv")
    parser.add_argument("--summary-output", default="outputs/tables/high_if_screening_summary.json")
    return parser.parse_args()


def normalize_text(value: str) -> str:
    value = (value or "").lower().strip()
    value = value.replace("&", " and ")
    value = re.sub(r"[^a-z0-9]+", " ", value)
    value = re.sub(r"\s+", " ", value)
    return value.strip()


def truthy(value: str) -> bool:
    return str(value or "").strip().lower() == "yes"


def as_text(value: object) -> str:
    if value is None or pd.isna(value):
        return ""
    return str(value).strip()


def to_float(value: object) -> float | None:
    if value is None:
        return None
    text = str(value).strip()
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


def build_priority_rationale(row: pd.Series, impact_factor: float | None) -> str:
    parts: List[str] = []
    if as_text(row.get("document_type")) == "review":
        parts.append("review仅作背景参考")
    if impact_factor is None:
        parts.append("期刊IF缺失，需人工核查")
    elif impact_factor >= 10:
        parts.append("期刊IF>=10，期刊质量最高优先")
    elif impact_factor >= 6:
        parts.append("期刊IF>=6，满足第一批高质量筛选门槛")
    elif impact_factor >= 3:
        parts.append("期刊IF介于3和6之间，保留为中质量备选")
    else:
        parts.append("期刊IF<3，优先级较低")

    if as_text(row.get("likely_ni_based")).lower() == "yes":
        parts.append("存在Ni-based信号")
    if as_text(row.get("likely_contains_conditions")).lower() == "yes":
        parts.append("更可能包含条件字段")
    if as_text(row.get("likely_contains_performance")).lower() == "yes":
        parts.append("更可能包含性能字段")
    return "；".join(parts)


def derive_exclude_reason(row: pd.Series, impact_factor: float | None) -> str:
    old_reason = as_text(row.get("exclude_reason"))
    if old_reason:
        return old_reason
    title = as_text(row.get("title")).lower()
    abstract = as_text(row.get("abstract_or_summary")).lower()
    text = f"{title} {abstract}".strip()
    if any(re.search(pattern, text) for pattern in SECONDARY_EXCLUSION_PATTERNS):
        return "likely_non_target_or_mixed_system"
    if as_text(row.get("document_type")) == "review":
        return "review_background_only"
    if impact_factor is None and not as_text(row.get("journal")):
        return "missing_journal_title"
    return ""


def is_high_if_first_batch(row: pd.Series, impact_factor: float | None) -> bool:
    if row.get("exclude_reason", ""):
        return False
    if as_text(row.get("document_type")) != "journal_article":
        return False
    if impact_factor is None or impact_factor < 6.0:
        return False
    if float(row.get("relevance_score", 0) or 0) < 70:
        return False
    if as_text(row.get("likely_contains_performance")).lower() != "yes":
        return False
    if float(row.get("extractability_score", 0) or 0) < 45:
        return False
    return True


def read_csv(path: str) -> pd.DataFrame:
    return pd.read_csv(path)


def main() -> int:
    args = parse_args()

    candidate_df = read_csv(args.candidate_input)
    scored_df = read_csv(args.scored_input)
    old_priority_df = read_csv(args.old_priority_input)
    lookup_df = read_csv(args.journal_lookup)

    if len(candidate_df) != len(scored_df):
        raise ValueError("candidate_papers.csv and candidate_papers_scored.csv row counts differ.")

    lookup_df["lookup_key"] = lookup_df["lookup_journal"].map(normalize_text)
    lookup_map: Dict[str, Dict[str, object]] = {
        row["lookup_key"]: row.to_dict() for _, row in lookup_df.iterrows()
    }

    old_priority_rank = {
        paper_id: index + 1 for index, paper_id in enumerate(old_priority_df["paper_id"].tolist())
    }

    merged = scored_df.copy()
    merged["journal_lookup_key"] = merged["journal"].fillna("").map(normalize_text)

    records: List[Dict[str, object]] = []
    for _, row in merged.iterrows():
        current = row.to_dict()
        lookup = lookup_map.get(current.get("journal_lookup_key", ""), {})
        impact_factor = to_float(lookup.get("journal_impact_factor", ""))

        current["journal_impact_factor_year"] = lookup.get("journal_impact_factor_year", "")
        current["journal_impact_factor"] = lookup.get("journal_impact_factor", "")
        current["journal_quartile"] = lookup.get("journal_quartile", "")
        current["journal_metrics_source"] = lookup.get("journal_metrics_source", "")
        current["journal_metrics_notes"] = lookup.get("journal_metrics_notes", "")
        current["needs_manual_journal_check"] = "yes" if impact_factor is None else "no"
        current["journal_quality_score"] = journal_quality_score(impact_factor)
        current["old_priority_score"] = current.get("priority_score", "")
        current["old_final_priority_label"] = current.get("final_priority_label", "")
        current["old_priority_rank"] = old_priority_rank.get(current["paper_id"], "")

        current["exclude_reason"] = derive_exclude_reason(pd.Series(current), impact_factor)
        current["priority_rationale"] = build_priority_rationale(pd.Series(current), impact_factor)

        relevance = float(current.get("relevance_score", 0) or 0)
        extractability = float(current.get("extractability_score", 0) or 0)
        current["priority_score"] = round(
            relevance * 0.30 + extractability * 0.20 + current["journal_quality_score"] * 0.50,
            1,
        )

        if is_high_if_first_batch(pd.Series(current), impact_factor):
            current["final_priority_label"] = (
                "top_priority"
                if as_text(current.get("likely_ni_based")).lower() == "yes"
                else "medium_priority"
            )
        elif current["exclude_reason"]:
            current["final_priority_label"] = "exclude"
        else:
            current["final_priority_label"] = "low_priority"

        records.append(current)

    result_df = pd.DataFrame(records)

    result_df = result_df.sort_values(
        by=[
            "final_priority_label",
            "likely_ni_based",
            "likely_contains_conditions",
            "journal_quality_score",
            "priority_score",
            "publication_year",
            "title",
        ],
        ascending=[True, False, False, False, False, False, True],
        key=lambda series: series.map(
            {
                "top_priority": 0,
                "medium_priority": 1,
                "low_priority": 2,
                "exclude": 3,
                "yes": 0,
                "no": 1,
            }
        ).fillna(series),
    )

    first_batch_df = result_df[
        result_df["final_priority_label"].isin(["top_priority", "medium_priority"])
    ].copy()
    first_batch_df = first_batch_df[
        (first_batch_df["document_type"] == "journal_article")
        & (pd.to_numeric(first_batch_df["journal_impact_factor"], errors="coerce") >= 6.0)
    ].copy()
    first_batch_df = first_batch_df.sort_values(
        by=[
            "likely_ni_based",
            "journal_quality_score",
            "priority_score",
            "likely_contains_conditions",
            "publication_year",
            "title",
        ],
        ascending=[False, False, False, False, False, True],
    )

    backup_df = result_df[
        (~result_df["paper_id"].isin(first_batch_df["paper_id"]))
        & (result_df["exclude_reason"] != "likely_non_target_or_mixed_system")
    ].copy()
    backup_df = backup_df.sort_values(
        by=[
            "relevance_score",
            "journal_quality_score",
            "priority_score",
            "publication_year",
            "title",
        ],
        ascending=[False, False, False, False, True],
    )

    Path(args.high_if_output).parent.mkdir(parents=True, exist_ok=True)
    result_df[HIGH_IF_SCORED_COLUMNS].to_csv(args.high_if_output, index=False, encoding="utf-8")
    first_batch_df[PRIORITY_COLUMNS].to_csv(args.first_batch_output, index=False, encoding="utf-8")
    backup_df[BACKUP_COLUMNS].to_csv(args.backup_output, index=False, encoding="utf-8")

    summary = {
        "raw_candidates": int(len(candidate_df)),
        "journal_metrics_filled_rows": int((result_df["journal_impact_factor"].astype(str).str.strip() != "").sum()),
        "needs_manual_journal_check_rows": int((result_df["needs_manual_journal_check"] == "yes").sum()),
        "if_ge_6_relevant_articles": int(
            (
                (result_df["document_type"] == "journal_article")
                & (pd.to_numeric(result_df["journal_impact_factor"], errors="coerce") >= 6.0)
                & (result_df["relevance_score"] >= 70)
            ).sum()
        ),
        "first_batch_high_if_pool": int(len(first_batch_df)),
        "backup_pool": int(len(backup_df)),
    }
    Path(args.summary_output).parent.mkdir(parents=True, exist_ok=True)
    Path(args.summary_output).write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print(f"High-IF scored output: {args.high_if_output}")
    print(f"High-IF first-batch output: {args.first_batch_output}")
    print(f"Backup output: {args.backup_output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
