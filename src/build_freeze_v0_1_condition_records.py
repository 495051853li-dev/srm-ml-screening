from __future__ import annotations

import argparse
import re
from collections import Counter
from pathlib import Path
from typing import Dict, Iterable, List

import pandas as pd


ROOT = Path(__file__).resolve().parent.parent

DERIVED_FIELDS = [
    "derived_activity_score",
    "derived_stability_score",
    "derived_coking_resistance_score",
    "derived_overall_screening_score",
]

CONFIRMATION_FIELDS = [
    "condition_record_id",
    "source_paper_id",
    "condition_group",
    "manual_confirmed",
    "ready_to_transfer",
    "confirmed_by",
    "confirmation_date",
    "condition_notes",
    "performance_notes",
    "freeze_blocking_issues",
    "transfer_recommendation",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build freeze v0.1 condition-level draft records from manually reviewed paper-level candidates."
    )
    parser.add_argument("--freeze-candidates", default="data/processed/freeze_candidate_v0_1.csv")
    parser.add_argument("--freeze-excluded", default="data/processed/freeze_excluded_needs_review_v0_1.csv")
    parser.add_argument("--manual-tasks", default="data/processed/manual_review_tasks_v0_1.csv")
    parser.add_argument("--template", default="data/processed/srm_literature_extraction_template.csv")
    parser.add_argument("--manual-summary", default="docs/manual_pdf_review_summary_v0_1.md")
    parser.add_argument("--condition-output", default="data/processed/freeze_v0_1_condition_records_draft.csv")
    parser.add_argument("--mechanistic-output", default="data/processed/mechanistic_reference_records_v0_1.csv")
    parser.add_argument("--qc-report", default="docs/freeze_v0_1_condition_record_qc.md")
    return parser.parse_args()


def read_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"Missing required input: {path}")
    return pd.read_csv(path, dtype=str, keep_default_na=False, encoding="utf-8-sig")


def read_text(path: Path) -> str:
    if not path.exists():
        raise FileNotFoundError(f"Missing required input: {path}")
    return path.read_text(encoding="utf-8", errors="replace")


def clean(value: object) -> str:
    if value is None:
        return ""
    text = str(value)
    if text.lower() == "nan":
        return ""
    return " ".join(text.replace("\x00", " ").split())


def first_row_by_paper(df: pd.DataFrame) -> Dict[str, pd.Series]:
    if "paper_id" not in df.columns:
        raise ValueError("freeze candidate table must contain paper_id")
    return {clean(row.get("paper_id")): row for _, row in df.iterrows()}


def init_record(base: pd.Series, template_columns: Iterable[str]) -> Dict[str, str]:
    record = {field: clean(base.get(field, "")) for field in template_columns}
    for field in DERIVED_FIELDS:
        if field in record:
            record[field] = ""
    record["record_id"] = ""
    record["analyst_qc_status"] = "pending"
    record["digitized_from_plot"] = clean(record.get("digitized_from_plot", "")) or "unclear"
    record["comparable_within_study"] = clean(record.get("comparable_within_study", "")) or "unclear"
    return record


def apply_confirmation_defaults(
    record: Dict[str, str],
    *,
    condition_record_id: str,
    source_paper_id: str,
    condition_group: str,
    condition_notes: str,
    performance_notes: str,
    freeze_blocking_issues: str,
    transfer_recommendation: str = "pending_manual_confirmation",
) -> Dict[str, str]:
    record.update(
        {
            "condition_record_id": condition_record_id,
            "source_paper_id": source_paper_id,
            "condition_group": condition_group,
            "manual_confirmed": "no",
            "ready_to_transfer": "no",
            "confirmed_by": "",
            "confirmation_date": "",
            "condition_notes": condition_notes,
            "performance_notes": performance_notes,
            "freeze_blocking_issues": freeze_blocking_issues,
            "transfer_recommendation": transfer_recommendation,
        }
    )
    if "condition_id" in record:
        record["condition_id"] = condition_record_id
    return record


def update_record(record: Dict[str, str], **values: object) -> Dict[str, str]:
    for key, value in values.items():
        record[key] = clean(value)
    for field in DERIVED_FIELDS:
        if field in record:
            record[field] = ""
    return record


def safe_id(text: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_-]+", "_", text.strip())
    return cleaned.strip("_")


def require_papers(rows_by_paper: Dict[str, pd.Series], paper_ids: Iterable[str]) -> None:
    missing = [paper_id for paper_id in paper_ids if paper_id not in rows_by_paper]
    if missing:
        raise ValueError(f"Missing manually reviewed freeze candidates: {', '.join(missing)}")


def build_condition_records(candidates: pd.DataFrame, template_columns: List[str]) -> List[Dict[str, str]]:
    rows_by_paper = first_row_by_paper(candidates)
    require_papers(rows_by_paper, ["paper_0060", "paper_0101", "paper_0158", "paper_0220"])

    records: List[Dict[str, str]] = []

    # paper_0060: one manually reviewed main activity/stability record.
    base = rows_by_paper["paper_0060"]
    record = init_record(base, template_columns)
    update_record(
        record,
        paper_id="paper_0060",
        catalyst_label_reported="unsupported pure Ni / Inco Ni 255",
        catalyst_family="unsupported Ni",
        active_metal_primary="Ni",
        active_metal_secondary="",
        active_metal_primary_loading_wt_pct="",
        active_metal_secondary_loading_wt_pct="",
        active_metal_total_loading_wt_pct="",
        active_metal_loading_wt_pct="",
        active_metal_loading_basis="not_applicable_unsupported_metal",
        support_primary="unsupported",
        support_secondary="",
        preparation_method=clean(base.get("preparation_method", "")),
        temperature_c="700",
        pressure_bar="1",
        steam_to_carbon_ratio="2",
        gas_hourly_space_velocity_h_inv="8500",
        weight_hourly_space_velocity_h_inv="",
        time_on_stream_h="100",
        methane_conversion_pct="98",
        stability_test_performed="yes",
        stability_duration_h="100",
        conversion_drop_pct_points="",
        coke_amount_mg_gcat="",
        coke_amount_wt_pct="",
        measured_value_basis="manual_pdf_review_confirmed_candidate",
        performance_definition_notes=(
            "Methane conversion reported as 98 +/- 2% for the manually reviewed main record."
        ),
        extraction_notes=(
            "Coke/Table 2 data use different test conditions and must not be merged into this 100 h main record."
        ),
    )
    apply_confirmation_defaults(
        record,
        condition_record_id="freeze_v0_1_paper_0060_main_activity_stability_001",
        source_paper_id="paper_0060",
        condition_group="main_activity_stability",
        condition_notes="700 C; CH4:H2O=1:2; 1 atm; GHSV=8500 h^-1; time-on-stream=100 h.",
        performance_notes="Methane conversion=98%; uncertainty +/-2% retained in notes. Coke data require separate Table 2 handling.",
        freeze_blocking_issues="requires_final_human_confirmation_before_formal_table_transfer",
    )
    records.append(record)

    # paper_0101: split into baseline and two S/C-specific stability records.
    base = rows_by_paper["paper_0101"]
    common_0101 = dict(
        paper_id="paper_0101",
        catalyst_label_reported="Ni-CGO / NiO-CGO",
        catalyst_family="Ni-CGO cermet anode",
        active_metal_primary="Ni",
        active_metal_secondary="",
        active_metal_primary_loading_wt_pct="",
        active_metal_secondary_loading_wt_pct="",
        active_metal_total_loading_wt_pct="",
        active_metal_loading_wt_pct="",
        active_metal_loading_basis="40 vol.% Ni reported; wt% not converted",
        support_primary="CGO",
        support_secondary="Ce0.9Gd0.1O1.95",
        preparation_method="glycine-nitrate-process",
        pressure_bar="1",
        weight_hourly_space_velocity_h_inv="7.5 x 10^4 ml/(g-cat h)",
        measured_value_basis="manual_pdf_review_pending_record_split",
        performance_definition_notes=(
            "Ni loading is 40 vol.% Ni and must not be forced into wt%. "
            "Space velocity is reported as 7.5 x 10^4 ml/(g-cat h), not 7.5 h^-1."
        ),
    )

    record = init_record(base, template_columns)
    update_record(
        record,
        **common_0101,
        temperature_c="800",
        steam_to_carbon_ratio="2",
        time_on_stream_h="5",
        methane_conversion_pct="76",
        stability_test_performed="no",
        stability_duration_h="",
        conversion_drop_pct_points="",
        coking_test_method="",
        coke_amount_wt_pct="",
        extraction_notes="Baseline activity record; S/C=2 and 5 h context require final PDF confirmation before transfer.",
    )
    apply_confirmation_defaults(
        record,
        condition_record_id="freeze_v0_1_paper_0101_baseline_activity_001",
        source_paper_id="paper_0101",
        condition_group="baseline_activity",
        condition_notes="800 C; likely S/C=2 activity/optimization context; GHSV/WHSV preserved as 7.5 x 10^4 ml/(g-cat h).",
        performance_notes="Methane conversion=76%; no carbon formation statement should be confirmed against the original figure/text.",
        freeze_blocking_issues="space_velocity_unit_requires_formal_schema_decision; baseline_condition_context_requires_final_confirmation",
    )
    records.append(record)

    record = init_record(base, template_columns)
    update_record(
        record,
        **common_0101,
        temperature_c="800",
        steam_to_carbon_ratio="1.5",
        time_on_stream_h="80",
        methane_conversion_pct="68",
        stability_test_performed="yes",
        stability_duration_h="80",
        conversion_drop_pct_points="30",
        coking_test_method="CHNS",
        coke_amount_wt_pct="<0.3",
        extraction_notes=(
            "S/C=1.5 stability record. Conversion decreased from about 68% to 38% during the first 40 h, "
            "then remained near 38% for the next 40 h. Carbon deposition reported as insignificant (<0.3 wt%)."
        ),
    )
    apply_confirmation_defaults(
        record,
        condition_record_id="freeze_v0_1_paper_0101_sc_1_5_stability_001",
        source_paper_id="paper_0101",
        condition_group="sc_1_5_stability",
        condition_notes="800 C; S/C=1.5; 80 h stability; GHSV/WHSV preserved as 7.5 x 10^4 ml/(g-cat h).",
        performance_notes="Initial methane conversion about 68%, final about 38%; conversion_drop_pct_points=30 pending final figure check.",
        freeze_blocking_issues="figure_value_confirmation_required; space_velocity_unit_requires_formal_schema_decision",
    )
    records.append(record)

    record = init_record(base, template_columns)
    update_record(
        record,
        **common_0101,
        temperature_c="800",
        steam_to_carbon_ratio="0.5",
        time_on_stream_h="80",
        methane_conversion_pct="31",
        stability_test_performed="yes",
        stability_duration_h="80",
        conversion_drop_pct_points="",
        coking_test_method="CHNS",
        coke_amount_wt_pct="<0.3",
        extraction_notes=(
            "S/C=0.5 stability record. Text indicates approximately constant methane conversion near 31% over 80 h; "
            "exact drop should be checked from the figure if needed."
        ),
    )
    apply_confirmation_defaults(
        record,
        condition_record_id="freeze_v0_1_paper_0101_sc_0_5_stability_001",
        source_paper_id="paper_0101",
        condition_group="sc_0_5_stability",
        condition_notes="800 C; S/C=0.5; 80 h stability; GHSV/WHSV preserved as 7.5 x 10^4 ml/(g-cat h).",
        performance_notes="Methane conversion near 31% and described as approximately constant; exact drop remains manual-check only.",
        freeze_blocking_issues="figure_value_confirmation_required; space_velocity_unit_requires_formal_schema_decision",
    )
    records.append(record)

    # paper_0158: split catalyst-state records using Table 4 methane steam reforming conversions.
    # Final conversion/drop/coke data still require manual matching before formal transfer.
    base = rows_by_paper["paper_0158"]
    catalyst_states = [
        ("NiAl2O4-R", "NiAl2O4", "", "", "78"),
        ("Ni2Al2O5-R", "Ni2Al2O5", "", "", "82"),
        ("Ni2Al2O5-NR", "Ni2Al2O5", "", "", "78"),
        ("commercial 50 wt% Ni/alpha-Al2O3-NR", "alpha-Al2O3", "50", "commercial_Ni_alpha_Al2O3", "85"),
    ]
    for idx, (label, support, loading, family_suffix, conversion) in enumerate(catalyst_states, start=1):
        record = init_record(base, template_columns)
        update_record(
            record,
            paper_id="paper_0158",
            catalyst_label_reported=label,
            catalyst_family=family_suffix or "nickel_aluminate_catalyst_state",
            active_metal_primary="Ni",
            active_metal_secondary="",
            active_metal_primary_loading_wt_pct=loading,
            active_metal_secondary_loading_wt_pct="",
            active_metal_total_loading_wt_pct=loading,
            active_metal_loading_wt_pct=loading,
            active_metal_loading_basis="reported_wt_pct_for_commercial_only" if loading else "not_converted_from_formula",
            support_primary=support,
            support_secondary="",
            preparation_method=clean(base.get("preparation_method", "")),
            temperature_c="700",
            pressure_bar="",
            steam_to_carbon_ratio="2.4",
            gas_hourly_space_velocity_h_inv="65500",
            weight_hourly_space_velocity_h_inv="",
            time_on_stream_h="12",
            methane_conversion_pct=conversion,
            stability_test_performed="yes",
            stability_duration_h="12",
            conversion_drop_pct_points="",
            coke_amount_mg_gcat="",
            coke_amount_wt_pct="",
            measured_value_basis="manual_pdf_review_pending_table4_entry",
            performance_definition_notes=(
                "Table 4 methane conversion is a 6 h on-stream value and must be confirmed catalyst-by-catalyst before transfer. "
                "Final conversion, conversion drop, and coke should be added only with matching catalyst and condition evidence."
            ),
            extraction_notes=(
                "Use SRM conditions only: 700 C, S/C=2.4, GHSV=65500 h^-1 dry basis, 12 h. "
                "Do not use earlier wrong auto-extracted temperature=300, pressure=8, or GHSV=52400 values."
            ),
        )
        apply_confirmation_defaults(
            record,
            condition_record_id=f"freeze_v0_1_paper_0158_{idx:03d}_{safe_id(label)}",
            source_paper_id="paper_0158",
            condition_group="catalyst_state_srm_table4_6h",
            condition_notes="700 C; S/C=2.4; GHSV=65500 h^-1 dry basis; 12 h SRM test.",
            performance_notes=(
                f"Table 4 6 h methane_conversion_pct={conversion}% for this catalyst-state; "
                "final conversion, conversion drop, and coke remain manual-confirmation fields."
            ),
            freeze_blocking_issues=(
                "table4_value_requires_human_confirmation_before_transfer; "
                "final_conversion_and_coke_require_manual_entry"
            ),
        )
        records.append(record)

    return records


def build_mechanistic_records(candidates: pd.DataFrame, template_columns: List[str]) -> List[Dict[str, str]]:
    rows_by_paper = first_row_by_paper(candidates)
    base = rows_by_paper["paper_0220"]
    record = init_record(base, template_columns)
    update_record(
        record,
        paper_id="paper_0220",
        catalyst_label_reported="15 wt% Ni-1 wt% Pt/MgAlOx and 15 wt% Ni/MgAlOx under operando/dynamic reaction conditions",
        catalyst_family="Ni-Pt/MgAlOx operando mechanistic reference",
        active_metal_primary="Ni",
        active_metal_secondary="Pt",
        active_metal_primary_loading_wt_pct="15",
        active_metal_secondary_loading_wt_pct="1",
        active_metal_total_loading_wt_pct="16",
        active_metal_loading_wt_pct="16",
        active_metal_loading_basis="reported_total_wt_pct_for_bimetallic_reference",
        support_primary="MgAlOx",
        support_secondary="",
        measured_value_basis="manual_pdf_review_mechanistic_reference",
        methane_conversion_pct="",
        performance_definition_notes=(
            "Operando/dynamic mechanistic reference. Not an ordinary steady-state methane_conversion_pct baseline ML training record."
        ),
        extraction_notes="Keep separately for later structure-performance descriptor analysis; do not mix with baseline condition records.",
    )
    apply_confirmation_defaults(
        record,
        condition_record_id="mechanistic_v0_1_paper_0220_operando_dynamic_001",
        source_paper_id="paper_0220",
        condition_group="operando_dynamic_mechanistic_reference",
        condition_notes="Dynamic/operando reaction condition reference; not a baseline steady-state condition row.",
        performance_notes="No baseline methane_conversion_pct training label assigned.",
        freeze_blocking_issues="not_for_baseline_ml_due_to_operando_dynamic_reaction_conditions",
        transfer_recommendation="mechanistic_reference_only_not_baseline_ml",
    )
    return [record]


def ordered_columns(template_columns: List[str]) -> List[str]:
    return CONFIRMATION_FIELDS + [field for field in template_columns if field not in CONFIRMATION_FIELDS]


def write_csv(path: Path, rows: List[Dict[str, str]], columns: List[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows, columns=columns).to_csv(path, index=False, encoding="utf-8-sig")


def has_value(row: Dict[str, str], field: str) -> bool:
    return clean(row.get(field, "")) != ""


def coverage(rows: List[Dict[str, str]], fields: Iterable[str]) -> Dict[str, int]:
    return {field: sum(1 for row in rows if has_value(row, field)) for field in fields}


def make_qc_report(
    *,
    condition_rows: List[Dict[str, str]],
    mechanistic_rows: List[Dict[str, str]],
    excluded_count: int,
    manual_tasks_count: int,
    manual_summary_chars: int,
) -> str:
    per_paper = Counter(row["source_paper_id"] for row in condition_rows)
    blocking = Counter(clean(row.get("freeze_blocking_issues", "")) for row in condition_rows)
    fields_to_check = [
        "active_metal_primary",
        "support_primary",
        "temperature_c",
        "pressure_bar",
        "steam_to_carbon_ratio",
        "gas_hourly_space_velocity_h_inv",
        "weight_hourly_space_velocity_h_inv",
        "time_on_stream_h",
        "methane_conversion_pct",
        "stability_duration_h",
        "conversion_drop_pct_points",
        "coke_amount_mg_gcat",
        "coke_amount_wt_pct",
    ]
    cov = coverage(condition_rows, fields_to_check)

    ready_like = [
        row["condition_record_id"]
        for row in condition_rows
        if row["source_paper_id"] in {"paper_0060", "paper_0101"}
    ]
    blocking_rows = [
        row["condition_record_id"]
        for row in condition_rows
        if has_value(row, "freeze_blocking_issues")
    ]

    lines = [
        "# Freeze v0.1 Condition-Level Draft QC",
        "",
        "## Scope",
        "",
        "- This report checks the condition-level draft built from manually reviewed PDF fulltext candidates.",
        "- No formal master extraction table was modified.",
        "- No machine learning was started.",
        "- All `derived_*` fields remain blank.",
        "- `paper_0220` was separated into `mechanistic_reference_records_v0_1.csv` and is not included in the baseline condition draft.",
        "",
        "## Inputs checked",
        "",
        f"- Freeze candidate rows: 4",
        f"- Freeze excluded rows retained for context: {excluded_count}",
        f"- Manual review task rows retained for context: {manual_tasks_count}",
        f"- Manual summary length checked: {manual_summary_chars} characters",
        "",
        "## Output counts",
        "",
        f"- Condition-level draft records: {len(condition_rows)}",
        f"- Mechanistic reference records: {len(mechanistic_rows)}",
        "",
        "## Records per paper",
        "",
    ]
    for paper_id in sorted(per_paper):
        lines.append(f"- `{paper_id}`: {per_paper[paper_id]} condition records")
    lines.extend(
        [
            "- `paper_0220`: 1 mechanistic reference record, excluded from baseline condition draft",
            "",
            "## Closest to formal transfer",
            "",
        ]
    )
    for record_id in ready_like:
        lines.append(f"- `{record_id}`")
    lines.extend(
        [
            "",
            "These records are still `manual_confirmed=no` and `ready_to_transfer=no`; they are only closest because the manual review already supplied condition/performance values.",
            "",
            "## Blocking issues",
            "",
        ]
    )
    for issue, count in blocking.items():
        if issue:
            lines.append(f"- {count} records: {issue}")
    lines.extend(
        [
            "",
            "## Field coverage in draft records",
            "",
            "| field | non-empty records | total records |",
            "| --- | ---: | ---: |",
        ]
    )
    for field, count in cov.items():
        lines.append(f"| `{field}` | {count} | {len(condition_rows)} |")
    lines.extend(
        [
            "",
            "## Fields still requiring manual confirmation",
            "",
            "- `paper_0060`: final check of the 98 +/- 2% conversion context and separation of Table 2 coke conditions.",
            "- `paper_0101`: exact figure values for S/C-specific stability, the meaning of 7.5 x 10^4 ml/(g-cat h), and whether this should remain in WHSV/GHSV notes before formal transfer.",
            "- `paper_0158`: catalyst-specific Table 4 6 h methane conversion values, final conversion, conversion drop, and coke values.",
            "- All records: pressure and space velocity comparability should be checked before any cross-paper analysis.",
            "",
            "## Analysis and ML readiness",
            "",
            "- Exploratory analysis is not ready until the draft records are manually confirmed and transferred into the formal table with consistent condition definitions.",
            "- Baseline machine learning is still not appropriate: the condition-level draft has only a few records, several fields remain manually pending, and temperature/S-C/pressure/space-velocity differences are leakage-prone if not stratified or normalized.",
            "- `journal_impact_factor`, review workflow fields, source quality fields, and `derived_*` fields must remain excluded from default model inputs.",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> None:
    args = parse_args()
    candidates = read_csv(ROOT / args.freeze_candidates)
    excluded = read_csv(ROOT / args.freeze_excluded)
    manual_tasks = read_csv(ROOT / args.manual_tasks)
    template = read_csv(ROOT / args.template)
    manual_summary = read_text(ROOT / args.manual_summary)

    template_columns = list(template.columns)
    out_columns = ordered_columns(template_columns)

    condition_rows = build_condition_records(candidates, template_columns)
    mechanistic_rows = build_mechanistic_records(candidates, template_columns)

    write_csv(ROOT / args.condition_output, condition_rows, out_columns)
    write_csv(ROOT / args.mechanistic_output, mechanistic_rows, out_columns)

    report = make_qc_report(
        condition_rows=condition_rows,
        mechanistic_rows=mechanistic_rows,
        excluded_count=len(excluded),
        manual_tasks_count=len(manual_tasks),
        manual_summary_chars=len(manual_summary),
    )
    report_path = ROOT / args.qc_report
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(report, encoding="utf-8")

    print(f"Condition draft records: {len(condition_rows)}")
    print(f"Mechanistic reference records: {len(mechanistic_rows)}")
    print(f"Wrote: {ROOT / args.condition_output}")
    print(f"Wrote: {ROOT / args.mechanistic_output}")
    print(f"Wrote: {ROOT / args.qc_report}")


if __name__ == "__main__":
    main()
