"""Validate SRM literature extraction datasets stored as CSV."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path
from typing import Dict, Iterable, List, Sequence, Set


EXPECTED_COLUMNS: List[str] = [
    "record_id",
    "paper_id",
    "reference_type",
    "first_author",
    "publication_year",
    "title",
    "journal",
    "journal_impact_factor_year",
    "journal_impact_factor",
    "journal_quartile",
    "journal_metrics_source",
    "journal_metrics_notes",
    "doi",
    "condition_id",
    "catalyst_label_reported",
    "catalyst_family",
    "active_metal_primary",
    "active_metal_secondary",
    "active_metal_primary_loading_wt_pct",
    "active_metal_secondary_loading_wt_pct",
    "active_metal_total_loading_wt_pct",
    "active_metal_atomic_ratio_reported",
    "active_metal_loading_wt_pct",
    "active_metal_loading_basis",
    "promoter_1",
    "promoter_1_loading_wt_pct",
    "promoter_2",
    "promoter_2_loading_wt_pct",
    "support_primary",
    "support_secondary",
    "support_notes",
    "precursor_metal_source",
    "precursor_support_source",
    "preparation_method",
    "preparation_details",
    "calcination_temperature_c",
    "calcination_time_h",
    "reduction_temperature_c",
    "reduction_time_h",
    "reduction_gas",
    "reactor_type",
    "catalyst_mass_g",
    "particle_size_um",
    "temperature_c",
    "pressure_bar",
    "steam_to_carbon_ratio",
    "feed_ch4_vol_pct",
    "feed_h2o_vol_pct",
    "feed_co2_vol_pct",
    "feed_n2_vol_pct",
    "feed_h2_vol_pct",
    "balance_gas_identity",
    "gas_hourly_space_velocity_h_inv",
    "weight_hourly_space_velocity_h_inv",
    "contact_time_s",
    "time_on_stream_h",
    "methane_conversion_pct",
    "h2_yield_pct",
    "h2_selectivity_pct",
    "h2_production_rate_mmol_gcat_h",
    "h2_production_rate_mmol_gmetal_h",
    "co_selectivity_pct",
    "co2_selectivity_pct",
    "h2_co_ratio",
    "performance_definition_notes",
    "stability_test_performed",
    "stability_duration_h",
    "conversion_drop_pct_points",
    "coking_test_method",
    "coke_amount_mg_gcat",
    "coke_amount_wt_pct",
    "carbon_balance_closure_pct",
    "sintering_evidence",
    "sulfur_tolerance_tested",
    "deactivation_mode_reported",
    "characterization_summary",
    "measured_value_basis",
    "digitized_from_plot",
    "extraction_notes",
    "comparable_within_study",
    "analyst_qc_status",
    "derived_activity_score",
    "derived_stability_score",
    "derived_coking_resistance_score",
    "derived_overall_screening_score",
]

REQUIRED_COLUMNS: Sequence[str] = (
    "record_id",
    "paper_id",
    "first_author",
    "publication_year",
    "catalyst_label_reported",
    "active_metal_primary",
    "support_primary",
)

NUMERIC_COLUMNS: Sequence[str] = (
    "publication_year",
    "journal_impact_factor_year",
    "journal_impact_factor",
    "active_metal_primary_loading_wt_pct",
    "active_metal_secondary_loading_wt_pct",
    "active_metal_total_loading_wt_pct",
    "active_metal_loading_wt_pct",
    "promoter_1_loading_wt_pct",
    "promoter_2_loading_wt_pct",
    "calcination_temperature_c",
    "calcination_time_h",
    "reduction_temperature_c",
    "reduction_time_h",
    "catalyst_mass_g",
    "particle_size_um",
    "temperature_c",
    "pressure_bar",
    "steam_to_carbon_ratio",
    "feed_ch4_vol_pct",
    "feed_h2o_vol_pct",
    "feed_co2_vol_pct",
    "feed_n2_vol_pct",
    "feed_h2_vol_pct",
    "gas_hourly_space_velocity_h_inv",
    "weight_hourly_space_velocity_h_inv",
    "contact_time_s",
    "time_on_stream_h",
    "methane_conversion_pct",
    "h2_yield_pct",
    "h2_selectivity_pct",
    "h2_production_rate_mmol_gcat_h",
    "h2_production_rate_mmol_gmetal_h",
    "co_selectivity_pct",
    "co2_selectivity_pct",
    "h2_co_ratio",
    "stability_duration_h",
    "conversion_drop_pct_points",
    "coke_amount_mg_gcat",
    "coke_amount_wt_pct",
    "carbon_balance_closure_pct",
    "derived_activity_score",
    "derived_stability_score",
    "derived_coking_resistance_score",
    "derived_overall_screening_score",
)

ENUM_COLUMNS: Dict[str, Set[str]] = {
    "reference_type": {"journal_article", "review_from_primary_source", "thesis", "conference_paper"},
    "catalyst_family": {"Ni_based", "noble_metal_based", "perovskite_derived", "hydrotalcite_derived", "spinel", "other"},
    "active_metal_loading_basis": {"nominal", "measured", "unclear"},
    "preparation_method": {
        "impregnation",
        "co_precipitation",
        "sol_gel",
        "deposition_precipitation",
        "hydrothermal",
        "combustion",
        "mechanical_mixing",
        "commercial",
        "other",
    },
    "reactor_type": {"fixed_bed", "packed_bed", "fluidized_bed", "microreactor", "monolith", "other"},
    "stability_test_performed": {"yes", "no", "unclear"},
    "digitized_from_plot": {"yes", "no"},
    "comparable_within_study": {"yes", "no", "unclear"},
    "analyst_qc_status": {"pending", "reviewed", "flagged"},
    "sulfur_tolerance_tested": {"yes", "no", "unclear"},
    "measured_value_basis": {"fresh", "steady_state", "peak", "average_over_window", "unclear"},
    "journal_quartile": {"Q1", "Q2", "Q3", "Q4", "unclear"},
    "journal_metrics_source": {"JCR", "Scopus", "manual_lookup", "other"},
}

PERCENT_COLUMNS: Sequence[str] = (
    "methane_conversion_pct",
    "h2_yield_pct",
    "h2_selectivity_pct",
    "co_selectivity_pct",
    "co2_selectivity_pct",
    "carbon_balance_closure_pct",
)

NONNEGATIVE_COLUMNS: Sequence[str] = (
    "journal_impact_factor",
    "active_metal_primary_loading_wt_pct",
    "active_metal_secondary_loading_wt_pct",
    "active_metal_total_loading_wt_pct",
    "active_metal_loading_wt_pct",
    "promoter_1_loading_wt_pct",
    "promoter_2_loading_wt_pct",
    "calcination_temperature_c",
    "calcination_time_h",
    "reduction_temperature_c",
    "reduction_time_h",
    "catalyst_mass_g",
    "particle_size_um",
    "temperature_c",
    "pressure_bar",
    "steam_to_carbon_ratio",
    "feed_ch4_vol_pct",
    "feed_h2o_vol_pct",
    "feed_co2_vol_pct",
    "feed_n2_vol_pct",
    "feed_h2_vol_pct",
    "gas_hourly_space_velocity_h_inv",
    "weight_hourly_space_velocity_h_inv",
    "contact_time_s",
    "time_on_stream_h",
    "methane_conversion_pct",
    "h2_yield_pct",
    "h2_selectivity_pct",
    "h2_production_rate_mmol_gcat_h",
    "h2_production_rate_mmol_gmetal_h",
    "co_selectivity_pct",
    "co2_selectivity_pct",
    "h2_co_ratio",
    "stability_duration_h",
    "coke_amount_mg_gcat",
    "coke_amount_wt_pct",
    "carbon_balance_closure_pct",
)

DERIVED_COLUMNS: Sequence[str] = (
    "derived_activity_score",
    "derived_stability_score",
    "derived_coking_resistance_score",
    "derived_overall_screening_score",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate SRM literature extraction CSV files.")
    parser.add_argument(
        "--input",
        required=True,
        help="Path to the CSV file to validate.",
    )
    return parser.parse_args()


def is_blank(value: str | None) -> bool:
    return value is None or value.strip() == ""


def parse_float(value: str) -> float:
    return float(value.strip())


def validate_columns(fieldnames: Sequence[str]) -> List[str]:
    issues: List[str] = []
    missing = [column for column in EXPECTED_COLUMNS if column not in fieldnames]
    extra = [column for column in fieldnames if column not in EXPECTED_COLUMNS]

    if missing:
        issues.append(f"Missing columns: {', '.join(missing)}")
    if extra:
        issues.append(f"Unexpected columns: {', '.join(extra)}")
    return issues


def validate_row(row_number: int, row: Dict[str, str], seen_record_ids: Set[str]) -> List[str]:
    issues: List[str] = []

    for column in REQUIRED_COLUMNS:
        if is_blank(row.get(column)):
            issues.append(f"Row {row_number}: required column '{column}' is blank.")

    record_id = row.get("record_id", "").strip()
    if record_id:
        if record_id in seen_record_ids:
            issues.append(f"Row {row_number}: duplicate record_id '{record_id}'.")
        seen_record_ids.add(record_id)

    numeric_values: Dict[str, float] = {}
    for column in NUMERIC_COLUMNS:
        value = row.get(column, "")
        if is_blank(value):
            continue
        try:
            numeric_values[column] = parse_float(value)
        except ValueError:
            issues.append(f"Row {row_number}: column '{column}' must be numeric, found '{value}'.")

    for column, allowed in ENUM_COLUMNS.items():
        value = row.get(column, "")
        if is_blank(value):
            continue
        if value not in allowed:
            issues.append(
                f"Row {row_number}: column '{column}' has invalid value '{value}'. Allowed values: {', '.join(sorted(allowed))}."
            )

    year = numeric_values.get("publication_year")
    if year is not None and not (1900 <= year <= 2100):
        issues.append(f"Row {row_number}: publication_year {year:g} is outside the expected range 1900-2100.")

    journal_metric_year = numeric_values.get("journal_impact_factor_year")
    if journal_metric_year is not None and not (1900 <= journal_metric_year <= 2100):
        issues.append(
            f"Row {row_number}: journal_impact_factor_year {journal_metric_year:g} is outside the expected range 1900-2100."
        )

    for column in NONNEGATIVE_COLUMNS:
        value = numeric_values.get(column)
        if value is not None and value < 0:
            issues.append(f"Row {row_number}: column '{column}' must be non-negative, found {value:g}.")

    for column in PERCENT_COLUMNS:
        value = numeric_values.get(column)
        if value is not None and not (0 <= value <= 100):
            issues.append(f"Row {row_number}: column '{column}' should usually be within 0-100, found {value:g}.")

    if all(
        key in numeric_values
        for key in ("feed_ch4_vol_pct", "feed_h2o_vol_pct", "feed_co2_vol_pct", "feed_n2_vol_pct", "feed_h2_vol_pct")
    ):
        feed_sum = (
            numeric_values["feed_ch4_vol_pct"]
            + numeric_values["feed_h2o_vol_pct"]
            + numeric_values["feed_co2_vol_pct"]
            + numeric_values["feed_n2_vol_pct"]
            + numeric_values["feed_h2_vol_pct"]
        )
        if feed_sum > 100.5:
            issues.append(f"Row {row_number}: reported feed fractions sum to {feed_sum:g}%, which exceeds 100%.")

    if not is_blank(row.get("journal_impact_factor")) and is_blank(row.get("journal_impact_factor_year")):
        issues.append(
            f"Row {row_number}: journal_impact_factor is filled but journal_impact_factor_year is blank."
        )

    if not is_blank(row.get("journal_metrics_source")) and is_blank(row.get("journal")):
        issues.append(f"Row {row_number}: journal_metrics_source is filled but journal is blank.")

    if not is_blank(row.get("journal_quartile")) and is_blank(row.get("journal")):
        issues.append(f"Row {row_number}: journal_quartile is filled but journal is blank.")

    stability_flag = row.get("stability_test_performed", "").strip()
    stability_duration = numeric_values.get("stability_duration_h")
    if stability_flag == "yes" and stability_duration is None:
        issues.append(f"Row {row_number}: stability_test_performed is 'yes' but stability_duration_h is blank.")
    if stability_flag == "no" and stability_duration is not None:
        issues.append(f"Row {row_number}: stability_duration_h is filled although stability_test_performed is 'no'.")

    if row.get("coking_test_method", "").strip():
        if numeric_values.get("coke_amount_mg_gcat") is None and numeric_values.get("coke_amount_wt_pct") is None:
            issues.append(
                f"Row {row_number}: coking_test_method is reported but no quantitative coke field is filled. "
                "This may be valid for qualitative evidence, but review manually."
            )

    if row.get("support_primary", "").strip() and not row.get("active_metal_primary", "").strip():
        issues.append(f"Row {row_number}: support_primary is filled but active_metal_primary is blank.")

    if row.get("measured_value_basis", "").strip() == "peak" and not row.get("extraction_notes", "").strip():
        issues.append(f"Row {row_number}: peak performance was recorded without extraction_notes explaining the basis.")

    if not is_blank(row.get("active_metal_total_loading_wt_pct")):
        total_value = numeric_values.get("active_metal_total_loading_wt_pct")
        primary_value = numeric_values.get("active_metal_primary_loading_wt_pct")
        secondary_value = numeric_values.get("active_metal_secondary_loading_wt_pct")
        if total_value is not None and primary_value is not None and secondary_value is not None:
            if abs(total_value - (primary_value + secondary_value)) > 0.25:
                issues.append(
                    f"Row {row_number}: active_metal_total_loading_wt_pct does not approximately match the sum "
                    "of active_metal_primary_loading_wt_pct and active_metal_secondary_loading_wt_pct."
                )

    if not is_blank(row.get("balance_gas_identity")):
        all_feed_keys_present = all(
            key in numeric_values
            for key in ("feed_ch4_vol_pct", "feed_h2o_vol_pct", "feed_co2_vol_pct", "feed_n2_vol_pct", "feed_h2_vol_pct")
        )
        if all_feed_keys_present:
            feed_sum = (
                numeric_values["feed_ch4_vol_pct"]
                + numeric_values["feed_h2o_vol_pct"]
                + numeric_values["feed_co2_vol_pct"]
                + numeric_values["feed_n2_vol_pct"]
                + numeric_values["feed_h2_vol_pct"]
            )
            if feed_sum >= 99.5:
                issues.append(
                    f"Row {row_number}: balance_gas_identity is filled although reported feed fractions already sum to approximately 100%."
                )

    for column in DERIVED_COLUMNS:
        if not is_blank(row.get(column)):
            issues.append(
                f"Row {row_number}: derived field '{column}' is populated. In raw literature extraction these fields must remain blank "
                "and may only be generated later by downstream scripts from frozen measured data."
            )

    return issues


def read_rows(path: Path) -> Iterable[Dict[str, str]]:
    with path.open("r", newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise ValueError("CSV file is missing a header row.")
        fieldnames = [name.strip() for name in reader.fieldnames]
        reader.fieldnames = fieldnames
        yield {"__fieldnames__": fieldnames}
        for row in reader:
            normalized = {key.strip(): (value.strip() if value is not None else "") for key, value in row.items()}
            yield normalized


def main() -> int:
    args = parse_args()
    csv_path = Path(args.input)

    if not csv_path.exists():
        print(f"ERROR: File not found: {csv_path}")
        return 1

    issues: List[str] = []
    seen_record_ids: Set[str] = set()
    row_count = 0

    rows = read_rows(csv_path)
    header_row = next(rows)
    fieldnames = header_row["__fieldnames__"]  # type: ignore[index]
    issues.extend(validate_columns(fieldnames))

    for row_number, row in enumerate(rows, start=2):
        row_count += 1
        issues.extend(validate_row(row_number, row, seen_record_ids))

    print(f"Validated file: {csv_path}")
    print(f"Detected rows: {row_count}")

    if issues:
        print(f"Validation status: FAILED ({len(issues)} issue(s))")
        for issue in issues:
            print(f"- {issue}")
        return 1

    print("Validation status: PASSED")
    print(
        "Warnings to remember: cross-paper condition differences and literature-source bias can still break comparability even when schema validation passes."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
