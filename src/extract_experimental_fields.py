from __future__ import annotations

import argparse
import csv
from pathlib import Path
from typing import Dict, List

from stage5_extraction_utils import (
    ROOT,
    build_candidate_map,
    first_regex_match,
    load_text_from_local_path,
    normalize_text,
    read_rows,
)


OUTPUT_COLUMNS = [
    "paper_id",
    "reactor_type",
    "reactor_type_source_excerpt",
    "temperature_c",
    "temperature_c_source_excerpt",
    "pressure_bar",
    "pressure_bar_source_excerpt",
    "steam_to_carbon_ratio",
    "steam_to_carbon_ratio_source_excerpt",
    "feed_ch4_vol_pct",
    "feed_ch4_vol_pct_source_excerpt",
    "feed_h2o_vol_pct",
    "feed_h2o_vol_pct_source_excerpt",
    "feed_co2_vol_pct",
    "feed_co2_vol_pct_source_excerpt",
    "feed_n2_vol_pct",
    "feed_n2_vol_pct_source_excerpt",
    "gas_hourly_space_velocity_h_inv",
    "gas_hourly_space_velocity_h_inv_source_excerpt",
    "weight_hourly_space_velocity_h_inv",
    "weight_hourly_space_velocity_h_inv_source_excerpt",
    "contact_time_s",
    "contact_time_s_source_excerpt",
    "time_on_stream_h",
    "time_on_stream_h_source_excerpt",
    "methane_conversion_pct",
    "methane_conversion_pct_source_excerpt",
    "h2_yield_pct",
    "h2_yield_pct_source_excerpt",
    "h2_selectivity_pct",
    "h2_selectivity_pct_source_excerpt",
    "co_selectivity_pct",
    "co_selectivity_pct_source_excerpt",
    "h2_co_ratio",
    "h2_co_ratio_source_excerpt",
    "stability_test_performed",
    "stability_test_performed_source_excerpt",
    "stability_duration_h",
    "stability_duration_h_source_excerpt",
    "conversion_drop_pct_points",
    "conversion_drop_pct_points_source_excerpt",
    "coking_test_method",
    "coking_test_method_source_excerpt",
    "coke_amount_mg_gcat",
    "coke_amount_mg_gcat_source_excerpt",
    "coke_amount_wt_pct",
    "coke_amount_wt_pct_source_excerpt",
    "measured_value_basis",
    "performance_definition_notes",
    "source_file_path",
    "source_excerpt_experimental",
    "extraction_confidence_experimental",
    "manual_review_required",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Extract experimental SRM fields from checked ready pool.")
    parser.add_argument("--input", default="data/processed/stage5_ready_pool_checked.csv")
    parser.add_argument("--candidates", default="data/processed/candidate_papers_high_if_scored.csv")
    parser.add_argument("--output", default="data/processed/srm_experimental_extraction_draft.csv")
    return parser.parse_args()


def validate_numeric_excerpt(value: str, excerpt: str, required_terms: List[str], forbidden_terms: List[str]) -> tuple[str, str]:
    lowered = excerpt.lower()
    if not value:
        return "", ""
    if required_terms and not any(term in lowered for term in required_terms):
        return "", ""
    if any(term in lowered for term in forbidden_terms):
        return "", ""
    return value, excerpt


def text_for_row(row: Dict[str, str], candidate: Dict[str, str]) -> str:
    path = ROOT / row.get("best_local_saved_path", "")
    source_text = load_text_from_local_path(path)
    return normalize_text(" ".join([normalize_text(candidate.get("abstract_or_summary", "")), source_text]))


def build_row(checked_row: Dict[str, str], candidate: Dict[str, str]) -> Dict[str, str]:
    text = text_for_row(checked_row, candidate)
    lowered = text.lower()

    row = {column: "" for column in OUTPUT_COLUMNS}
    row["paper_id"] = candidate.get("paper_id", "")
    row["source_file_path"] = checked_row.get("best_local_saved_path", "")
    row["source_excerpt_experimental"] = checked_row.get("source_excerpt_preview", "")
    row["manual_review_required"] = "yes"

    reactor_type, reactor_excerpt = first_regex_match(
        [r"(fixed[\- ]bed)", r"(packed[\- ]bed)", r"(microreactor)", r"(fluidized bed)"],
        lowered,
    )
    row["reactor_type"] = reactor_type.replace(" ", "_") if reactor_type else ""
    row["reactor_type_source_excerpt"] = reactor_excerpt

    temperature, temperature_excerpt = first_regex_match(
        [
            r"(?:temperature|reaction at|tested at|operated at)\s*(\d+(?:\.\d+)?)\s*(?:c|k)",
            r"(\d+(?:\.\d+)?)\s*(?:c|k)\s*(?:for|during)\s*(?:steam reforming|reaction)",
        ],
        lowered,
    )
    pressure, pressure_excerpt = first_regex_match(
        [r"(\d+(?:\.\d+)?)\s*(?:bar|atm|mpa|kpa)"],
        lowered,
    )
    sc_ratio, sc_excerpt = first_regex_match(
        [r"(?:steam-to-carbon|steam to carbon|s/c)\s*(?:ratio)?(?: of|=)?\s*(\d+(?:\.\d+)?)"],
        lowered,
    )
    ghsv, ghsv_excerpt = first_regex_match(
        [r"ghsv(?: of|=)?\s*(\d+(?:\.\d+)?)\s*(?:h-1|h\^-1)?"],
        lowered,
    )
    whsv, whsv_excerpt = first_regex_match(
        [r"whsv(?: of|=)?\s*(\d+(?:\.\d+)?)\s*(?:h-1|h\^-1)?"],
        lowered,
    )
    tos, tos_excerpt = first_regex_match(
        [r"(?:time on stream|stable for)\s*(\d+(?:\.\d+)?)\s*h"],
        lowered,
    )

    row["temperature_c"] = temperature
    row["temperature_c_source_excerpt"] = temperature_excerpt
    row["pressure_bar"] = pressure
    row["pressure_bar_source_excerpt"] = pressure_excerpt
    row["steam_to_carbon_ratio"] = sc_ratio
    row["steam_to_carbon_ratio_source_excerpt"] = sc_excerpt
    row["gas_hourly_space_velocity_h_inv"] = ghsv
    row["gas_hourly_space_velocity_h_inv_source_excerpt"] = ghsv_excerpt
    row["weight_hourly_space_velocity_h_inv"] = whsv
    row["weight_hourly_space_velocity_h_inv_source_excerpt"] = whsv_excerpt
    row["time_on_stream_h"] = tos
    row["time_on_stream_h_source_excerpt"] = tos_excerpt

    row["temperature_c"], row["temperature_c_source_excerpt"] = validate_numeric_excerpt(
        row["temperature_c"],
        row["temperature_c_source_excerpt"],
        required_terms=["temperature", "reaction", "steam reforming", "tested at", "operated at"],
        forbidden_terms=["pdf", "article information", "download citation", "supplementary files"],
    )

    # Performance values are only filled when numeric values and units are explicit.
    methane_conversion, methane_conv_excerpt = first_regex_match(
        [r"methane conversion(?: of| was|=)?\s*(\d+(?:\.\d+)?)\s*%"],
        lowered,
    )
    h2_yield, h2_yield_excerpt = first_regex_match(
        [r"(?:hydrogen|h2) yield(?: of| was|=)?\s*(\d+(?:\.\d+)?)\s*%"],
        lowered,
    )
    h2_selectivity, h2_sel_excerpt = first_regex_match(
        [r"(?:hydrogen|h2) selectivity(?: of| was|=)?\s*(\d+(?:\.\d+)?)\s*%"],
        lowered,
    )
    co_selectivity, co_sel_excerpt = first_regex_match(
        [r"co selectivity(?: of| was|=)?\s*(\d+(?:\.\d+)?)\s*%"],
        lowered,
    )
    h2_co_ratio, h2co_excerpt = first_regex_match(
        [r"h2/co(?: ratio)?(?: of| was|=)?\s*(\d+(?:\.\d+)?)"],
        lowered,
    )
    stability_duration, stability_excerpt = first_regex_match(
        [r"(?:stable for|stability.*?for)\s*(\d+(?:\.\d+)?)\s*h"],
        lowered,
    )
    conversion_drop, conversion_drop_excerpt = first_regex_match(
        [r"conversion drop(?: of| was|=)?\s*(\d+(?:\.\d+)?)\s*(?:percentage points|% points|points)"],
        lowered,
    )
    coke_mg, coke_mg_excerpt = first_regex_match(
        [r"coke(?: amount)?(?: of| was|=)?\s*(\d+(?:\.\d+)?)\s*mg/?g"],
        lowered,
    )
    coke_wt, coke_wt_excerpt = first_regex_match(
        [r"coke(?: amount)?(?: of| was|=)?\s*(\d+(?:\.\d+)?)\s*wt\.?\s*%"],
        lowered,
    )
    coking_method, coking_excerpt = first_regex_match(
        [r"\b(tga)\b", r"\b(tpo)\b", r"\b(raman)\b", r"\b(tem)\b"],
        lowered,
    )

    row["methane_conversion_pct"] = methane_conversion
    row["methane_conversion_pct_source_excerpt"] = methane_conv_excerpt
    row["h2_yield_pct"] = h2_yield
    row["h2_yield_pct_source_excerpt"] = h2_yield_excerpt
    row["h2_selectivity_pct"] = h2_selectivity
    row["h2_selectivity_pct_source_excerpt"] = h2_sel_excerpt
    row["co_selectivity_pct"] = co_selectivity
    row["co_selectivity_pct_source_excerpt"] = co_sel_excerpt
    row["h2_co_ratio"] = h2_co_ratio
    row["h2_co_ratio_source_excerpt"] = h2co_excerpt

    if stability_duration:
        row["stability_test_performed"] = "yes"
        row["stability_test_performed_source_excerpt"] = stability_excerpt
        row["stability_duration_h"] = stability_duration
        row["stability_duration_h_source_excerpt"] = stability_excerpt
    row["conversion_drop_pct_points"] = conversion_drop
    row["conversion_drop_pct_points_source_excerpt"] = conversion_drop_excerpt
    row["coking_test_method"] = coking_method
    row["coking_test_method_source_excerpt"] = coking_excerpt
    row["coke_amount_mg_gcat"] = coke_mg
    row["coke_amount_mg_gcat_source_excerpt"] = coke_mg_excerpt
    row["coke_amount_wt_pct"] = coke_wt
    row["coke_amount_wt_pct_source_excerpt"] = coke_wt_excerpt

    if "steady-state" in lowered or "steady state" in lowered:
        row["measured_value_basis"] = "steady_state"
    elif any(value for value in [methane_conversion, h2_yield, h2_selectivity, co_selectivity, h2_co_ratio]):
        row["measured_value_basis"] = "unclear"

    notes: List[str] = []
    if "high methane conversion" in lowered and not methane_conversion:
        notes.append("summary reports high methane conversion but no explicit numeric value in checked source")
    if "hydrogen yield" in lowered and not h2_yield:
        notes.append("source mentions hydrogen yield without explicit numeric value")
    if stability_duration and not conversion_drop:
        notes.append("stability duration explicit but degradation magnitude not explicit")
    row["performance_definition_notes"] = "; ".join(notes)

    experimental_hits = sum(
        1
        for field in [
            "temperature_c",
            "pressure_bar",
            "steam_to_carbon_ratio",
            "gas_hourly_space_velocity_h_inv",
            "time_on_stream_h",
            "methane_conversion_pct",
            "h2_yield_pct",
            "h2_selectivity_pct",
            "stability_duration_h",
            "coke_amount_wt_pct",
            "coke_amount_mg_gcat",
        ]
        if row.get(field)
    )
    if experimental_hits >= 5:
        confidence = "low_to_medium"
    elif experimental_hits >= 2:
        confidence = "low"
    else:
        confidence = "very_low"
    row["extraction_confidence_experimental"] = confidence
    return row


def main() -> int:
    args = parse_args()
    checked_rows = read_rows(Path(args.input))
    candidate_rows = read_rows(Path(args.candidates))
    candidate_map = build_candidate_map(candidate_rows)

    output_rows: List[Dict[str, str]] = []
    for checked_row in checked_rows:
        allowed_scope = str(checked_row.get("allowed_extraction_scope", ""))
        source_quality_type = str(checked_row.get("source_quality_type", ""))
        if "experimental" not in allowed_scope:
            continue
        if source_quality_type not in {"pdf_fulltext", "html_fulltext"}:
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

    print(f"Experimental draft rows: {len(output_rows)}")
    print(f"Output: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
