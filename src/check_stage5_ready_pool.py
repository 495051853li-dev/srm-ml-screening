from __future__ import annotations

import argparse
import csv
from pathlib import Path
from typing import Dict, List

from stage5_extraction_utils import ROOT, choose_best_local_source, classify_source_quality, read_rows, yes_no


OUTPUT_COLUMNS = [
    "paper_id",
    "doi",
    "title",
    "document_type",
    "priority_rank",
    "priority_score",
    "journal",
    "journal_impact_factor",
    "source_url",
    "attempted_url",
    "fetch_status",
    "fetch_attempts",
    "last_fetch_time",
    "retry_recommended",
    "failure_reason",
    "local_saved_path",
    "content_type",
    "content_length",
    "has_useful_text",
    "ready_for_extraction",
    "best_local_saved_path",
    "best_source_file_name",
    "local_path_exists",
    "local_file_nonempty",
    "best_source_score",
    "checked_text_length",
    "redirect_hits",
    "domain_keyword_count",
    "experimental_keyword_count",
    "contains_msr_terms",
    "contains_condition_terms",
    "contains_performance_terms",
    "has_useful_domain_text",
    "ready_for_metadata",
    "ready_for_experimental",
    "ready_for_extraction_checked",
    "page_quality_label",
    "not_ready_reason",
    "source_quality_type",
    "source_quality_score",
    "allowed_extraction_scope",
    "extraction_strategy",
    "recommended_next_action",
    "source_excerpt_preview",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Check stage5 ready pool quality from fetch manifest.")
    parser.add_argument("--input", default="data/processed/fulltext_fetch_manifest.csv")
    parser.add_argument("--output", default="data/processed/stage5_ready_pool_checked.csv")
    return parser.parse_args()


def page_quality_label(score: int, ready_metadata: bool, ready_experimental: bool) -> str:
    if ready_experimental:
        return "strong_for_experimental"
    if ready_metadata:
        return "metadata_only"
    if score > 0:
        return "weak_source"
    return "not_usable"


def main() -> int:
    args = parse_args()
    manifest_rows = read_rows(Path(args.input))
    output_rows: List[Dict[str, str]] = []

    for row in manifest_rows:
        if str(row.get("ready_for_extraction", "")).strip().lower() != "yes":
            continue

        paper_id = str(row.get("paper_id", "")).strip()
        quality = choose_best_local_source(paper_id, str(row.get("local_saved_path", "")))
        source_class = classify_source_quality(row, quality)
        allowed_scope = str(source_class["allowed_extraction_scope"])
        ready_metadata = "metadata" in allowed_scope or "bibliographic_metadata" in allowed_scope
        ready_experimental = "experimental" in allowed_scope
        checked_ready = ready_metadata or ready_experimental

        # Explicit guard requested by the user: paper_0221 should not inherit old ready=yes blindly.
        if paper_id == "paper_0221" and (quality["text_length"] < 100 or "redirect" in str(quality["not_ready_reason"])):
            ready_metadata = False
            ready_experimental = False
            checked_ready = False

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
            "source_url",
            "attempted_url",
            "fetch_status",
            "fetch_attempts",
            "last_fetch_time",
            "retry_recommended",
            "failure_reason",
            "local_saved_path",
            "content_type",
            "content_length",
            "has_useful_text",
            "ready_for_extraction",
        ]:
            output_row[key] = row.get(key, "")

        output_row["best_local_saved_path"] = str(quality["best_local_saved_path"])
        output_row["best_source_file_name"] = str(quality["best_source_file_name"])
        output_row["local_path_exists"] = yes_no(bool(quality["best_local_saved_path"]))
        output_row["local_file_nonempty"] = yes_no(int(quality["text_length"]) > 0)
        output_row["best_source_score"] = str(quality["best_source_score"])
        output_row["checked_text_length"] = str(quality["text_length"])
        output_row["redirect_hits"] = str(quality["redirect_hits"])
        output_row["domain_keyword_count"] = str(quality["domain_keyword_count"])
        output_row["experimental_keyword_count"] = str(quality["experimental_keyword_count"])
        output_row["contains_msr_terms"] = yes_no(bool(quality["contains_msr_terms"]))
        output_row["contains_condition_terms"] = yes_no(bool(quality["contains_condition_terms"]))
        output_row["contains_performance_terms"] = yes_no(bool(quality["contains_performance_terms"]))
        output_row["has_useful_domain_text"] = yes_no(bool(quality["has_useful_domain_text"]))
        output_row["ready_for_metadata"] = yes_no(ready_metadata)
        output_row["ready_for_experimental"] = yes_no(ready_experimental)
        output_row["ready_for_extraction_checked"] = yes_no(checked_ready)
        output_row["page_quality_label"] = page_quality_label(int(quality["best_source_score"]), ready_metadata, ready_experimental)
        output_row["not_ready_reason"] = str(quality["not_ready_reason"])
        output_row.update(source_class)
        output_row["source_excerpt_preview"] = str(quality["source_excerpt_preview"])
        output_rows.append(output_row)

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=OUTPUT_COLUMNS)
        writer.writeheader()
        writer.writerows(output_rows)

    ready_metadata_count = sum(1 for row in output_rows if row["ready_for_metadata"] == "yes")
    ready_experimental_count = sum(1 for row in output_rows if row["ready_for_experimental"] == "yes")
    print(f"Stage5 ready-pool checked rows: {len(output_rows)}")
    print(f"Metadata-ready rows: {ready_metadata_count}")
    print(f"Experimental-ready rows: {ready_experimental_count}")
    print(f"Output: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
