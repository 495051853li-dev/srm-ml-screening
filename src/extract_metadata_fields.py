from __future__ import annotations

import argparse
import csv
from pathlib import Path
from typing import Dict, List

from stage5_extraction_utils import (
    ROOT,
    build_candidate_map,
    detect_metals,
    detect_preparation_method,
    detect_supports,
    excerpt_for_title,
    first_regex_match,
    infer_catalyst_family,
    load_text_from_local_path,
    normalize_text,
    read_rows,
)


OUTPUT_COLUMNS = [
    "paper_id",
    "first_author",
    "publication_year",
    "title",
    "journal",
    "doi",
    "catalyst_label_reported",
    "catalyst_label_reported_source_excerpt",
    "catalyst_family",
    "catalyst_family_source_excerpt",
    "active_metal_primary",
    "active_metal_primary_source_excerpt",
    "active_metal_secondary",
    "active_metal_secondary_source_excerpt",
    "active_metal_primary_loading_wt_pct",
    "active_metal_primary_loading_wt_pct_source_excerpt",
    "active_metal_secondary_loading_wt_pct",
    "active_metal_secondary_loading_wt_pct_source_excerpt",
    "active_metal_total_loading_wt_pct",
    "active_metal_total_loading_wt_pct_source_excerpt",
    "active_metal_loading_basis",
    "support_primary",
    "support_primary_source_excerpt",
    "support_secondary",
    "support_secondary_source_excerpt",
    "promoter_1",
    "promoter_1_source_excerpt",
    "promoter_1_loading_wt_pct",
    "promoter_1_loading_wt_pct_source_excerpt",
    "preparation_method",
    "preparation_method_source_excerpt",
    "calcination_temperature_c",
    "calcination_temperature_c_source_excerpt",
    "reduction_temperature_c",
    "reduction_temperature_c_source_excerpt",
    "reduction_time_h",
    "reduction_time_h_source_excerpt",
    "reduction_gas",
    "reduction_gas_source_excerpt",
    "source_file_path",
    "source_excerpt_metadata",
    "extraction_confidence_metadata",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Extract metadata-level SRM fields from checked ready pool.")
    parser.add_argument("--input", default="data/processed/stage5_ready_pool_checked.csv")
    parser.add_argument("--candidates", default="data/processed/candidate_papers_high_if_scored.csv")
    parser.add_argument("--output", default="data/processed/srm_metadata_extraction_draft.csv")
    return parser.parse_args()


def text_for_row(row: Dict[str, str], candidate: Dict[str, str]) -> str:
    path = ROOT / row.get("best_local_saved_path", "")
    source_text = load_text_from_local_path(path)
    combined = " ".join(
        [
            normalize_text(candidate.get("title", "")),
            normalize_text(candidate.get("abstract_or_summary", "")),
            source_text,
        ]
    )
    return normalize_text(combined)


def match_loading_for_metal(text: str, metal: str) -> tuple[str, str]:
    if not metal:
        return "", ""
    patterns = [
        rf"(\d+(?:\.\d+)?)\s*(?:wt\.?\s*%|%)\s*{metal.lower()}",
        rf"{metal.lower()}\s*\((\d+(?:\.\d+)?)\s*(?:wt\.?\s*%|%)\)",
        rf"(\d+(?:\.\d+)?)\s*{metal.lower()}\/",
    ]
    return first_regex_match(patterns, text.lower())


def build_row(checked_row: Dict[str, str], candidate: Dict[str, str]) -> Dict[str, str]:
    text = text_for_row(checked_row, candidate)
    title = normalize_text(candidate.get("title", ""))
    abstract = normalize_text(candidate.get("abstract_or_summary", ""))
    metals = detect_metals(text)
    supports = detect_supports(text)
    prep_method, prep_excerpt = detect_preparation_method(text)
    source_quality_type = str(checked_row.get("source_quality_type", "unknown"))
    allowed_scope = str(checked_row.get("allowed_extraction_scope", ""))
    limited_catalyst_only = source_quality_type == "abstract_only"
    bibliographic_only = source_quality_type == "doi_landing_page" or allowed_scope == "bibliographic_metadata"

    row = {column: "" for column in OUTPUT_COLUMNS}
    row["paper_id"] = candidate.get("paper_id", "")
    row["first_author"] = candidate.get("first_author", "")
    row["publication_year"] = candidate.get("publication_year", "")
    row["title"] = candidate.get("title", "")
    row["journal"] = candidate.get("journal", "")
    row["doi"] = candidate.get("doi", "")
    row["source_file_path"] = checked_row.get("best_local_saved_path", "")
    row["source_excerpt_metadata"] = checked_row.get("source_excerpt_preview", "")

    if title:
        row["catalyst_label_reported"] = title
        row["catalyst_label_reported_source_excerpt"] = excerpt_for_title(title)

    if bibliographic_only:
        row["extraction_confidence_metadata"] = "bibliographic_only"
        return row

    if metals:
        row["catalyst_family"] = infer_catalyst_family(metals)
        row["catalyst_family_source_excerpt"] = excerpt_for_title(title or abstract)
        row["active_metal_primary"] = metals[0]
        row["active_metal_primary_source_excerpt"] = excerpt_for_title(title or abstract)
    if len(metals) > 1:
        row["active_metal_secondary"] = metals[1]
        row["active_metal_secondary_source_excerpt"] = excerpt_for_title(title or abstract)

    if not limited_catalyst_only:
        primary_loading, primary_loading_excerpt = match_loading_for_metal(text, row["active_metal_primary"])
        secondary_loading, secondary_loading_excerpt = match_loading_for_metal(text, row["active_metal_secondary"])
        row["active_metal_primary_loading_wt_pct"] = primary_loading
        row["active_metal_primary_loading_wt_pct_source_excerpt"] = primary_loading_excerpt
        row["active_metal_secondary_loading_wt_pct"] = secondary_loading
        row["active_metal_secondary_loading_wt_pct_source_excerpt"] = secondary_loading_excerpt
        total_loading, total_loading_excerpt = first_regex_match(
            [r"total (?:metal )?loading(?: of|=)?\s*(\d+(?:\.\d+)?)\s*(?:wt\.?\s*%|%)"],
            text.lower(),
        )
        row["active_metal_total_loading_wt_pct"] = total_loading
        row["active_metal_total_loading_wt_pct_source_excerpt"] = total_loading_excerpt
        row["active_metal_loading_basis"] = "unclear"

    if supports:
        row["support_primary"] = supports[0]
        row["support_primary_source_excerpt"] = excerpt_for_title(title or abstract)
    if len(supports) > 1:
        row["support_secondary"] = supports[1]
        row["support_secondary_source_excerpt"] = excerpt_for_title(title or abstract)

    if not limited_catalyst_only:
        promoter, promoter_excerpt = first_regex_match(
            [r"([a-z0-9]+)\s+promoter", r"promoted with\s+([a-z0-9]+)", r"([a-z0-9]+)\s+doping"],
            text.lower(),
        )
        if promoter and promoter.upper() not in {"NI", "RH", "CO", "PT", "RU", "CU", "FE"}:
            row["promoter_1"] = promoter
            row["promoter_1_source_excerpt"] = promoter_excerpt
            promoter_loading, promoter_loading_excerpt = first_regex_match(
                [rf"(\d+(?:\.\d+)?)\s*(?:wt\.?\s*%|%)\s*{promoter.lower()}"],
                text.lower(),
            )
            row["promoter_1_loading_wt_pct"] = promoter_loading
            row["promoter_1_loading_wt_pct_source_excerpt"] = promoter_loading_excerpt

    if not limited_catalyst_only:
        row["preparation_method"] = prep_method
        row["preparation_method_source_excerpt"] = prep_excerpt

    if not limited_catalyst_only:
        calc_temp, calc_excerpt = first_regex_match(
            [r"calcined (?:at|in)\s*(\d+(?:\.\d+)?)\s*(?:c|k)", r"calcination(?: temperature)?(?: of|=)?\s*(\d+(?:\.\d+)?)\s*(?:c|k)"],
            text.lower(),
        )
        red_temp, red_temp_excerpt = first_regex_match(
            [r"reduced (?:at|in)\s*(\d+(?:\.\d+)?)\s*(?:c|k)", r"reduction(?: temperature)?(?: of|=)?\s*(\d+(?:\.\d+)?)\s*(?:c|k)"],
            text.lower(),
        )
        red_time, red_time_excerpt = first_regex_match(
            [r"reduction.*?for\s*(\d+(?:\.\d+)?)\s*h", r"reduced.*?for\s*(\d+(?:\.\d+)?)\s*h"],
            text.lower(),
        )
        red_gas, red_gas_excerpt = first_regex_match(
            [r"reduction in\s+([a-z0-9%/\- ]*h2[a-z0-9%/\- ]*)", r"reduced in\s+([a-z0-9%/\- ]*h2[a-z0-9%/\- ]*)"],
            text.lower(),
        )
        row["calcination_temperature_c"] = calc_temp
        row["calcination_temperature_c_source_excerpt"] = calc_excerpt
        row["reduction_temperature_c"] = red_temp
        row["reduction_temperature_c_source_excerpt"] = red_temp_excerpt
        row["reduction_time_h"] = red_time
        row["reduction_time_h_source_excerpt"] = red_time_excerpt
        row["reduction_gas"] = red_gas
        row["reduction_gas_source_excerpt"] = red_gas_excerpt

    metadata_hits = sum(
        1
        for field in [
            "catalyst_family",
            "active_metal_primary",
            "support_primary",
            "preparation_method",
            "calcination_temperature_c",
            "reduction_temperature_c",
            "reduction_time_h",
        ]
        if row.get(field)
    )
    if metadata_hits >= 5:
        confidence = "medium"
    elif metadata_hits >= 3:
        confidence = "low_to_medium"
    else:
        confidence = "low"
    if limited_catalyst_only and confidence == "medium":
        confidence = "low_to_medium"
    row["extraction_confidence_metadata"] = confidence
    return row


def main() -> int:
    args = parse_args()
    checked_rows = read_rows(Path(args.input))
    candidate_rows = read_rows(Path(args.candidates))
    candidate_map = build_candidate_map(candidate_rows)

    output_rows: List[Dict[str, str]] = []
    for checked_row in checked_rows:
        allowed_scope = str(checked_row.get("allowed_extraction_scope", ""))
        if not ("metadata" in allowed_scope or "bibliographic_metadata" in allowed_scope):
            continue
        if str(checked_row.get("source_quality_type", "")) in {"redirect_or_forbidden", "navigation_shell", "no_useful_content", "unknown"}:
            continue
        paper_id = str(checked_row.get("paper_id", "")).strip()
        candidate = candidate_map.get(paper_id, {})
        if not candidate:
            continue
        output_rows.append(build_row(checked_row, candidate))

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=OUTPUT_COLUMNS)
        writer.writeheader()
        writer.writerows(output_rows)

    print(f"Metadata draft rows: {len(output_rows)}")
    print(f"Output: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
