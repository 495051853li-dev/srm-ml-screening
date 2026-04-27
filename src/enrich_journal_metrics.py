"""Enrich the master candidate pool with journal impact factor metadata."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Dict

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
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Enrich candidate pool with curated journal metrics.")
    parser.add_argument("--input", default="data/processed/candidate_papers_master.csv")
    parser.add_argument("--lookup", default="data/processed/journal_metrics_lookup_curated.csv")
    parser.add_argument("--output", default="data/processed/candidate_papers_master_enriched.csv")
    parser.add_argument("--summary-output", default="outputs/tables/journal_metrics_enrichment_summary.json")
    return parser.parse_args()


def normalize_text(value: str) -> str:
    value = (value or "").lower().strip()
    value = value.replace("&", " and ")
    value = re.sub(r"[^a-z0-9]+", " ", value)
    value = re.sub(r"\s+", " ", value)
    return value.strip()


def main() -> int:
    args = parse_args()
    master = pd.read_csv(args.input)
    lookup = pd.read_csv(args.lookup)
    lookup["lookup_key"] = lookup["lookup_journal"].map(normalize_text)
    lookup_map: Dict[str, Dict[str, object]] = {row["lookup_key"]: row.to_dict() for _, row in lookup.iterrows()}

    rows = []
    for _, row in master.iterrows():
        current = row.to_dict()
        key = normalize_text(str(current.get("journal", "") if not pd.isna(current.get("journal", "")) else ""))
        entry = lookup_map.get(key, {})
        current["journal_impact_factor_year"] = entry.get("journal_impact_factor_year", "")
        current["journal_impact_factor"] = entry.get("journal_impact_factor", "")
        current["journal_quartile"] = entry.get("journal_quartile", "")
        current["journal_metrics_source"] = entry.get("journal_metrics_source", "")
        current["journal_metrics_notes"] = entry.get("journal_metrics_notes", "")
        current["needs_manual_journal_check"] = "no" if entry else "yes"
        rows.append(current)

    out_df = pd.DataFrame(rows)
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    out_df[OUTPUT_COLUMNS].to_csv(args.output, index=False, encoding="utf-8")

    summary = {
        "master_rows": int(len(master)),
        "metrics_filled_rows": int((out_df["needs_manual_journal_check"] == "no").sum()),
        "needs_manual_journal_check_rows": int((out_df["needs_manual_journal_check"] == "yes").sum()),
        "unique_journals_enriched": int(out_df.loc[out_df["needs_manual_journal_check"] == "no", "journal"].nunique()),
    }
    Path(args.summary_output).parent.mkdir(parents=True, exist_ok=True)
    Path(args.summary_output).write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print(f"Enriched candidate pool: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
