"""Build a master SRM candidate pool from the current candidate paper list."""

from __future__ import annotations

import argparse
import json
import re
from difflib import SequenceMatcher
from pathlib import Path
from typing import Dict, List, Tuple

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
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a batch-oriented master candidate pool.")
    parser.add_argument("--input", default="data/processed/candidate_papers.csv")
    parser.add_argument("--output", default="data/processed/candidate_papers_master.csv")
    parser.add_argument("--summary-output", default="outputs/tables/candidate_master_summary.json")
    return parser.parse_args()


def normalize_text(value: str) -> str:
    value = (value or "").lower().strip()
    value = value.replace("&", " and ")
    value = re.sub(r"[^a-z0-9]+", " ", value)
    value = re.sub(r"\s+", " ", value)
    return value.strip()


def title_similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, normalize_text(a), normalize_text(b)).ratio()


def normalize_doi(value: str) -> str:
    return (
        (value or "")
        .strip()
        .replace("https://doi.org/", "")
        .replace("http://doi.org/", "")
        .lower()
    )


def choose_better(existing: Dict[str, str], current: Dict[str, str]) -> Dict[str, str]:
    def score(row: Dict[str, str]) -> Tuple[int, int, int]:
        return (
            1 if str(row.get("document_type", "")).strip() == "journal_article" else 0,
            1 if str(row.get("has_abstract", "")).strip().lower() == "yes" else 0,
            len(str(row.get("abstract_or_summary", "") or "")),
        )

    return current if score(current) > score(existing) else existing


def is_non_target(text: str) -> bool:
    patterns = [
        r"\bmethanol\b",
        r"\bethanol\b",
        r"\bethane\b",
        r"\bpropane\b",
        r"\bdry reforming\b",
        r"\bautothermal\b",
        r"\bpartial oxidation\b",
        r"\bpatent\b",
    ]
    return any(re.search(pattern, text) for pattern in patterns)


def main() -> int:
    args = parse_args()
    df = pd.read_csv(args.input)
    rows = df.to_dict(orient="records")

    doi_seen: Dict[str, Dict[str, str]] = {}
    title_year_seen: List[Dict[str, str]] = []
    deduped_by_doi = 0
    deduped_by_title_year = 0

    for row in rows:
        record = dict(row)
        record["normalized_title"] = normalize_text(str(record.get("title", "")))
        record["dedup_key_doi"] = normalize_doi(str(record.get("doi", "")))
        year = str(record.get("publication_year", "") or "").strip()
        record["dedup_key_title_year"] = f"{record['normalized_title']}::{year}" if year else record["normalized_title"]
        combined_text = f"{record.get('title', '')} {record.get('abstract_or_summary', '')}".lower()
        record["non_target_flag"] = "yes" if is_non_target(combined_text) else "no"
        record["master_screening_bucket"] = "non_target_flagged" if record["non_target_flag"] == "yes" else "candidate"
        record["duplicate_resolution_basis"] = ""

        doi_key = record["dedup_key_doi"]
        if doi_key:
            if doi_key in doi_seen:
                replacement = choose_better(doi_seen[doi_key], record)
                if replacement is record:
                    doi_seen[doi_key] = record
                deduped_by_doi += 1
                continue
            doi_seen[doi_key] = record

        matched = False
        for existing in title_year_seen:
            same_year = str(existing.get("publication_year", "") or "").strip() == year
            if same_year and title_similarity(existing.get("title", ""), record.get("title", "")) >= 0.97:
                matched = True
                replacement = choose_better(existing, record)
                if replacement is record:
                    existing.update(record)
                    existing["duplicate_resolution_basis"] = "title_year_fuzzy"
                deduped_by_title_year += 1
                break

        if not matched:
            title_year_seen.append(record)

    out_df = pd.DataFrame(title_year_seen).sort_values(by=["publication_year", "title"], ascending=[False, True])
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    out_df[OUTPUT_COLUMNS].to_csv(args.output, index=False, encoding="utf-8")

    summary = {
        "input_rows": int(len(df)),
        "master_rows": int(len(out_df)),
        "deduped_by_doi": int(deduped_by_doi),
        "deduped_by_title_year": int(deduped_by_title_year),
        "non_target_flagged_rows": int((out_df["non_target_flag"] == "yes").sum()),
    }
    Path(args.summary_output).parent.mkdir(parents=True, exist_ok=True)
    Path(args.summary_output).write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print(f"Master candidate pool: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
