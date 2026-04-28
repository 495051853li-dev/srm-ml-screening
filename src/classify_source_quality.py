from __future__ import annotations

import argparse
import csv
from pathlib import Path
from typing import Dict, List

from stage5_extraction_utils import choose_best_local_source, classify_source_quality, read_rows, yes_no


OUTPUT_COLUMNS = [
    "paper_id",
    "doi",
    "title",
    "document_type",
    "priority_rank",
    "priority_score",
    "journal",
    "journal_impact_factor",
    "fetch_status",
    "ready_for_extraction",
    "source_url",
    "attempted_url",
    "local_saved_path",
    "best_local_saved_path",
    "content_type",
    "content_length",
    "checked_text_length",
    "redirect_hits",
    "domain_keyword_count",
    "experimental_keyword_count",
    "contains_msr_terms",
    "contains_condition_terms",
    "contains_performance_terms",
    "source_quality_type",
    "source_quality_score",
    "allowed_extraction_scope",
    "extraction_strategy",
    "recommended_next_action",
    "source_excerpt_preview",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Classify source quality between stage4 and stage5.")
    parser.add_argument("--manifest", default="data/processed/fulltext_fetch_manifest.csv")
    parser.add_argument("--checked", default="data/processed/stage5_ready_pool_checked.csv")
    parser.add_argument("--output", default="data/processed/source_quality_classification.csv")
    return parser.parse_args()


def build_checked_map(rows: List[Dict[str, str]]) -> Dict[str, Dict[str, str]]:
    return {str(row.get("paper_id", "")).strip(): row for row in rows if str(row.get("paper_id", "")).strip()}


def main() -> int:
    args = parse_args()
    manifest_rows = read_rows(Path(args.manifest))
    checked_map = build_checked_map(read_rows(Path(args.checked)))
    output_rows: List[Dict[str, str]] = []

    for row in manifest_rows:
        paper_id = str(row.get("paper_id", "")).strip()
        checked = checked_map.get(paper_id, {})
        best_path = checked.get("best_local_saved_path", "") or row.get("local_saved_path", "")
        quality = choose_best_local_source(paper_id, best_path)
        source_class = classify_source_quality(row, quality)

        output_row = {column: "" for column in OUTPUT_COLUMNS}
        for key in [
            "paper_id",
            "doi",
            "title",
            "document_type",
            "priority_rank",
            "priority_score",
            "journal",
            "journal_impact_factor",
            "fetch_status",
            "ready_for_extraction",
            "source_url",
            "attempted_url",
            "local_saved_path",
            "content_type",
            "content_length",
        ]:
            output_row[key] = row.get(key, "")

        output_row["best_local_saved_path"] = str(quality["best_local_saved_path"])
        output_row["checked_text_length"] = str(quality["text_length"])
        output_row["redirect_hits"] = str(quality["redirect_hits"])
        output_row["domain_keyword_count"] = str(quality["domain_keyword_count"])
        output_row["experimental_keyword_count"] = str(quality["experimental_keyword_count"])
        output_row["contains_msr_terms"] = yes_no(bool(quality["contains_msr_terms"]))
        output_row["contains_condition_terms"] = yes_no(bool(quality["contains_condition_terms"]))
        output_row["contains_performance_terms"] = yes_no(bool(quality["contains_performance_terms"]))
        output_row["source_excerpt_preview"] = str(quality["source_excerpt_preview"])
        output_row.update(source_class)
        output_rows.append(output_row)

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=OUTPUT_COLUMNS)
        writer.writeheader()
        writer.writerows(output_rows)

    print(f"Source quality classified rows: {len(output_rows)}")
    print(f"Output: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
