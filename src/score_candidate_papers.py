"""Second-round screening and prioritization for SRM candidate papers."""

from __future__ import annotations

import argparse
import csv
import re
from pathlib import Path
from typing import Dict, List


SCORED_COLUMNS = [
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
    "relevance_score",
    "extractability_score",
    "priority_score",
    "likely_ni_based",
    "likely_contains_conditions",
    "likely_contains_performance",
    "exclude_reason",
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
    "relevance_score",
    "extractability_score",
    "priority_score",
    "likely_ni_based",
    "likely_contains_conditions",
    "likely_contains_performance",
    "final_priority_label",
    "screening_notes",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Second-round screen and rank SRM candidate papers.")
    parser.add_argument("--input", default="data/processed/candidate_papers.csv", help="Input candidate paper CSV.")
    parser.add_argument(
        "--scored-output",
        default="data/processed/candidate_papers_scored.csv",
        help="Output CSV with scores and priority labels.",
    )
    parser.add_argument(
        "--priority-output",
        default="data/processed/first_batch_priority_papers.csv",
        help="Output CSV sorted for first-batch extraction priority.",
    )
    return parser.parse_args()


def normalize_text(value: str) -> str:
    value = (value or "").lower()
    value = re.sub(r"\s+", " ", value)
    return value.strip()


def contains_any(text: str, patterns: List[str]) -> bool:
    return any(pattern in text for pattern in patterns)


def matches_any_regex(text: str, patterns: List[str]) -> bool:
    return any(re.search(pattern, text) for pattern in patterns)


def score_row(row: Dict[str, str]) -> Dict[str, str]:
    title = normalize_text(row.get("title", ""))
    abstract = normalize_text(row.get("abstract_or_summary", ""))
    text = f"{title} {abstract}".strip()
    document_type = (row.get("document_type") or "").strip()

    relevance_score = 0
    extractability_score = 0
    exclude_reason = ""

    strong_srm_markers = [
        "steam reforming of methane",
        "methane steam reforming",
        "steam reforming methane",
    ]
    medium_srm_markers = [
        "srm",
        "steam reforming",
    ]
    methane_markers = ["methane", "ch4"]
    catalyst_markers = ["catalyst", "catalysts", "ni/", "nickel", "alumina", "ceria", "support"]
    ni_markers = ["ni-based", "ni based", "nickel", "ni/"]
    condition_markers = [
        "temperature",
        "steam-to-carbon",
        "steam to carbon",
        "s/c",
        "pressure",
        "ghsv",
        "whsv",
        "time on stream",
        "tos",
    ]
    performance_markers = [
        "conversion",
        "yield",
        "selectivity",
        "activity",
        "performance",
        "hydrogen production",
        "stability",
        "coking",
        "carbon deposition",
    ]
    exclusion_patterns = [
        r"\bmethanol\b",
        r"\bethanol\b",
        r"\bethane\b",
        r"\bpropane\b",
        r"\bdry reforming\b",
        r"\bautothermal\b",
        r"\bpartial oxidation\b",
        r"\bpatent\b",
    ]

    if matches_any_regex(text, exclusion_patterns):
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
        extractability_score += 10
    else:
        extractability_score += 0

    if row.get("has_abstract") == "yes":
        extractability_score += 15
    if row.get("has_fulltext") == "yes":
        extractability_score += 15
    if row.get("doi"):
        extractability_score += 10
    if likely_contains_conditions == "yes":
        extractability_score += 20
    if likely_contains_performance == "yes":
        extractability_score += 15

    if document_type == "review":
        extractability_score -= 10

    relevance_score = max(0, min(100, relevance_score))
    extractability_score = max(0, min(100, extractability_score))
    priority_score = round(relevance_score * 0.6 + extractability_score * 0.4, 1)

    row["relevance_score"] = f"{relevance_score}"
    row["extractability_score"] = f"{extractability_score}"
    row["priority_score"] = f"{priority_score}"
    row["likely_ni_based"] = likely_ni_based
    row["likely_contains_conditions"] = likely_contains_conditions
    row["likely_contains_performance"] = likely_contains_performance
    row["exclude_reason"] = exclude_reason
    row["final_priority_label"] = ""

    return row


def assign_priority_labels(rows: List[Dict[str, str]]) -> None:
    rows.sort(
        key=lambda r: (
            r.get("exclude_reason", "") != "",
            -float(r.get("priority_score", "0") or 0),
            r.get("publication_year", ""),
            r.get("title", ""),
        )
    )

    eligible = [
        row
        for row in rows
        if not row.get("exclude_reason")
        and row.get("document_type") == "journal_article"
    ]

    top_priority_ids = {row["paper_id"] for row in eligible[:20]}
    medium_priority_ids = {row["paper_id"] for row in eligible[20:60]}

    for row in rows:
        if row.get("exclude_reason"):
            row["final_priority_label"] = "exclude"
        elif row["paper_id"] in top_priority_ids:
            row["final_priority_label"] = "top_priority"
        elif row["paper_id"] in medium_priority_ids:
            row["final_priority_label"] = "medium_priority"
        else:
            row["final_priority_label"] = "low_priority"


def read_rows(path: Path) -> List[Dict[str, str]]:
    with path.open("r", newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def write_rows(path: Path, rows: List[Dict[str, str]], fieldnames: List[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fieldnames})


def main() -> int:
    args = parse_args()
    input_path = Path(args.input)
    rows = read_rows(input_path)
    scored = [score_row(dict(row)) for row in rows]
    assign_priority_labels(scored)

    write_rows(Path(args.scored_output), scored, SCORED_COLUMNS)

    priority_sorted = sorted(
        scored,
        key=lambda r: (
            {"top_priority": 0, "medium_priority": 1, "low_priority": 2, "exclude": 3}.get(
                r.get("final_priority_label", ""), 9
            ),
            -float(r.get("priority_score", "0") or 0),
            r.get("publication_year", ""),
            r.get("title", ""),
        ),
    )
    write_rows(Path(args.priority_output), priority_sorted, PRIORITY_COLUMNS)

    print(f"Input candidate rows: {len(rows)}")
    print(f"Top priority rows: {sum(1 for row in scored if row['final_priority_label'] == 'top_priority')}")
    print(f"Medium priority rows: {sum(1 for row in scored if row['final_priority_label'] == 'medium_priority')}")
    print(f"Low priority rows: {sum(1 for row in scored if row['final_priority_label'] == 'low_priority')}")
    print(f"Exclude rows: {sum(1 for row in scored if row['final_priority_label'] == 'exclude')}")
    print(f"Scored output: {args.scored_output}")
    print(f"Priority output: {args.priority_output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
