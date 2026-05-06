from __future__ import annotations

import argparse
from pathlib import Path
from typing import Dict, List

import pandas as pd


ROOT = Path(__file__).resolve().parent.parent

DERIVED_FIELDS = [
    "derived_activity_score",
    "derived_stability_score",
    "derived_coking_resistance_score",
    "derived_overall_screening_score",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Apply manual PDF review decisions to freeze v0.1 candidate layer.")
    parser.add_argument("--freeze-candidates", default="data/processed/freeze_candidate_v0_1.csv")
    parser.add_argument("--freeze-excluded", default="data/processed/freeze_excluded_needs_review_v0_1.csv")
    parser.add_argument("--manual-tasks", default="data/processed/manual_review_tasks_v0_1.csv")
    parser.add_argument("--summary", default="docs/manual_pdf_review_summary_v0_1.md")
    return parser.parse_args()


def read_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"Missing required file: {path}")
    return pd.read_csv(path, dtype=str, keep_default_na=False, encoding="utf-8-sig")


def clean(value: object) -> str:
    if value is None:
        return ""
    return " ".join(str(value).replace("\x00", " ").split())


def append_note(existing: str, note: str) -> str:
    existing = clean(existing)
    note = clean(note)
    if not existing:
        return note
    if note in existing:
        return existing
    return f"{existing} | {note}"


def ensure_columns(df: pd.DataFrame, columns: List[str]) -> pd.DataFrame:
    for column in columns:
        if column not in df.columns:
            df[column] = ""
    return df


def manual_updates() -> Dict[str, Dict[str, str]]:
    return {
        "paper_0060": {
            "freeze_candidate_status": "ready_for_manual_transfer_after_check",
            "catalyst_label_reported": "unsupported pure Ni / Inco Ni 255",
            "catalyst_family": "Ni_based",
            "active_metal_primary": "Ni",
            "active_metal_secondary": "",
            "active_metal_primary_loading_wt_pct": "",
            "active_metal_secondary_loading_wt_pct": "",
            "active_metal_total_loading_wt_pct": "",
            "active_metal_loading_basis": "not_applicable_unsupported_pure_metal",
            "support_primary": "unsupported",
            "support_secondary": "",
            "support_notes": "Manual review: unsupported pure Ni catalyst, Inco Ni 255; previous Al2O3/CeO2 support assignment was from cited literature/context and should not be used for this main record.",
            "temperature_c": "700",
            "pressure_bar": "1",
            "steam_to_carbon_ratio": "2",
            "gas_hourly_space_velocity_h_inv": "8500",
            "weight_hourly_space_velocity_h_inv": "",
            "time_on_stream_h": "100",
            "methane_conversion_pct": "98",
            "measured_value_basis": "manual_pdf_review_confirmed_candidate",
            "performance_definition_notes": "Manual review: suggested main record is 700 C, CH4:H2O=1:2, P=1 atm, GHSV=8500 h^-1, time-on-stream=100 h, methane conversion=98 +/- 2%. Coke information should reference Table 2 conditions separately and must not be mixed with the 100 h stability record.",
            "condition_comparability_notes": "Manual review: main stability/activity record uses 700 C, CH4:H2O=1:2, P=1 atm, GHSV=8500 h^-1, 100 h. Coke/Table 2 conditions are a separate context and should not be compared as the same record.",
            "label_candidate_recommendation": "primary_label_candidate=methane_conversion_pct; manually reviewed value 98 +/- 2% under the stated 100 h stability condition.",
            "reviewer_must_check_fields": "temperature_c; pressure_bar; steam_to_carbon_ratio; gas_hourly_space_velocity_h_inv; time_on_stream_h; methane_conversion_pct; coke/Table 2 condition separation",
            "freeze_blocking_issues": "",
            "transfer_ready_after_manual_check": "yes",
            "reviewer_notes": "Manual review v0.1: ready for manual transfer after check; update as unsupported pure Ni / Inco Ni 255. Do not merge Table 2 coke data with 100 h stability record.",
        },
        "paper_0101": {
            "freeze_candidate_status": "ready_for_manual_transfer_after_check",
            "catalyst_label_reported": "Ni-CGO / NiO-CGO",
            "catalyst_family": "Ni_based",
            "active_metal_primary": "Ni",
            "active_metal_secondary": "",
            "active_metal_primary_loading_wt_pct": "",
            "active_metal_secondary_loading_wt_pct": "",
            "active_metal_total_loading_wt_pct": "",
            "active_metal_loading_basis": "reported_as_40_vol_pct_Ni_not_wt_pct",
            "support_primary": "CGO",
            "support_secondary": "Ce0.9Gd0.1O1.95",
            "support_notes": "Manual review: support/electrolyte phase is CGO / Ce0.9Gd0.1O1.95.",
            "preparation_method": "glycine-nitrate-process",
            "gas_hourly_space_velocity_h_inv": "",
            "weight_hourly_space_velocity_h_inv": "7.5e4 ml/(g-cat h)",
            "measured_value_basis": "manual_pdf_review_pending_record_split",
            "performance_definition_notes": "Manual review: Ni loading should be recorded as 40 vol.% Ni and must not be forced into wt%. Suggested split records: baseline activity, S/C=1.5 stability, and S/C=0.5 stability.",
            "condition_comparability_notes": "Manual review: split into baseline activity, S/C=1.5 stability, and S/C=0.5 stability records. Preserve GHSV as 7.5 x 10^4 ml/(g-cat h), not 7.5 h^-1.",
            "label_candidate_recommendation": "primary_label_candidate=methane_conversion_pct; only after splitting baseline and stability conditions.",
            "reviewer_must_check_fields": "condition split; steam_to_carbon_ratio; weight_hourly_space_velocity_h_inv; methane_conversion_pct; time_on_stream_h; 40 vol.% Ni basis",
            "freeze_blocking_issues": "requires_condition_split_before_formal_transfer",
            "transfer_ready_after_manual_check": "yes",
            "reviewer_notes": "Manual review v0.1: ready after check, but formal table should split into baseline activity, S/C=1.5 stability, and S/C=0.5 stability records.",
        },
        "paper_0158": {
            "freeze_candidate_status": "ready_for_manual_transfer_after_check",
            "catalyst_label_reported": "nickel aluminate SRM catalyst set; split required: NiAl2O4-R; Ni2Al2O5-R; Ni2Al2O5-NR; commercial 50 wt% Ni/alpha-Al2O3-NR",
            "active_metal_primary": "Ni",
            "active_metal_secondary": "",
            "active_metal_primary_loading_wt_pct": "",
            "active_metal_secondary_loading_wt_pct": "",
            "active_metal_total_loading_wt_pct": "",
            "active_metal_loading_basis": "record_specific_split_required",
            "support_primary": "nickel_aluminate_or_alpha-Al2O3_record_specific",
            "support_secondary": "",
            "temperature_c": "700",
            "pressure_bar": "",
            "steam_to_carbon_ratio": "2.4",
            "gas_hourly_space_velocity_h_inv": "65500",
            "weight_hourly_space_velocity_h_inv": "",
            "time_on_stream_h": "12",
            "measured_value_basis": "manual_pdf_review_pending_record_split",
            "performance_definition_notes": "Manual review: SRM general condition is 700 C, S/C=2.4, GHSV=65500 h^-1 dry basis, 12 h. Previous auto temperature=300, pressure=8, GHSV=52400 should be deleted if from TEM/XPS/DRM. Table 4 methane conversion is 6 h on stream; final conversion and coke data should be notes or separate stability/coking fields.",
            "condition_comparability_notes": "Manual review: split into NiAl2O4-R, Ni2Al2O5-R, Ni2Al2O5-NR, commercial 50 wt% Ni/alpha-Al2O3-NR and other relevant records; use SRM conditions only, not DRM or characterization conditions.",
            "label_candidate_recommendation": "primary_label_candidate=methane_conversion_pct; Table 4 value is 6 h on stream and must be linked to the correct catalyst-specific record.",
            "reviewer_must_check_fields": "catalyst-specific row split; temperature_c; steam_to_carbon_ratio; gas_hourly_space_velocity_h_inv; time_on_stream_h; methane_conversion_pct Table 4 6 h; final conversion; coke data",
            "freeze_blocking_issues": "requires_multi_record_split_before_formal_transfer; methane_conversion_pct_requires_table4_catalyst_specific_confirmation",
            "transfer_ready_after_manual_check": "yes",
            "reviewer_notes": "Manual review v0.1: corrected prior exclusion/uncertainty; ready after check. Delete auto values from TEM/XPS/DRM context before formal transfer.",
        },
        "paper_0220": {
            "freeze_candidate_status": "mechanistic_reference_not_for_baseline_ml",
            "catalyst_label_reported": "15 wt% Ni-1 wt% Pt/MgAlOx and 15 wt% Ni/MgAlOx under operando/dynamic reaction conditions",
            "catalyst_family": "Ni_based",
            "active_metal_primary": "Ni",
            "active_metal_secondary": "Pt",
            "active_metal_primary_loading_wt_pct": "15",
            "active_metal_secondary_loading_wt_pct": "1",
            "active_metal_total_loading_wt_pct": "16",
            "active_metal_loading_basis": "reported_nominal_wt_pct",
            "support_primary": "MgAlOx",
            "support_secondary": "",
            "measured_value_basis": "manual_pdf_review_mechanistic_reference",
            "performance_definition_notes": "Manual review: operando/dynamic reaction condition paper. Do not use as ordinary steady-state methane_conversion_pct training record.",
            "condition_comparability_notes": "Manual review: keep as operando/dynamic reaction condition reference for later structure-performance descriptor analysis; exclude from baseline steady-state ML.",
            "label_candidate_recommendation": "not_recommended_for_baseline_ml_label; mechanistic/operando reference only.",
            "reviewer_must_check_fields": "active_metal_secondary Pt; MgAlOx support; 15 wt% Ni; 1 wt% Pt; dynamic/operando condition scope",
            "freeze_blocking_issues": "not_for_baseline_ml_due_to_operando_dynamic_reaction_conditions",
            "transfer_ready_after_manual_check": "no",
            "reviewer_notes": "Manual review v0.1: mark as mechanistic reference, not baseline ML training record. Useful later for structure-performance descriptor analysis.",
        },
    }


def apply_updates(candidates: pd.DataFrame) -> pd.DataFrame:
    extra_columns = [
        "manual_review_v0_1_status",
        "manual_review_v0_1_summary",
        "formal_transfer_record_strategy",
    ]
    candidates = ensure_columns(candidates, extra_columns)
    updates = manual_updates()
    for paper_id, values in updates.items():
        mask = candidates["paper_id"].astype(str).eq(paper_id)
        if not mask.any():
            continue
        for column, value in values.items():
            if column not in candidates.columns:
                candidates[column] = ""
            candidates.loc[mask, column] = value
        if paper_id == "paper_0060":
            candidates.loc[mask, "manual_review_v0_1_status"] = "reviewed_ready_for_transfer_candidate"
            candidates.loc[mask, "manual_review_v0_1_summary"] = "Unsupported pure Ni / Inco Ni 255; main record conditions and methane conversion manually reviewed; coke kept separate from 100 h stability."
            candidates.loc[mask, "formal_transfer_record_strategy"] = "one main activity/stability record plus separate coke/Table 2 note or separate coking record if confirmed."
        elif paper_id == "paper_0101":
            candidates.loc[mask, "manual_review_v0_1_status"] = "reviewed_ready_for_transfer_candidate_requires_split"
            candidates.loc[mask, "manual_review_v0_1_summary"] = "Ni-CGO / NiO-CGO; CGO support; GNP preparation; 40 vol.% Ni; split into baseline, S/C=1.5 stability, S/C=0.5 stability."
            candidates.loc[mask, "formal_transfer_record_strategy"] = "split into at least three formal records before transfer."
        elif paper_id == "paper_0158":
            candidates.loc[mask, "manual_review_v0_1_status"] = "reviewed_ready_for_transfer_candidate_requires_split"
            candidates.loc[mask, "manual_review_v0_1_summary"] = "Use SRM conditions 700 C, S/C=2.4, GHSV=65500 h^-1 dry basis, 12 h; remove TEM/XPS/DRM auto values."
            candidates.loc[mask, "formal_transfer_record_strategy"] = "split into catalyst-specific records, including NiAl2O4-R, Ni2Al2O5-R, Ni2Al2O5-NR, commercial 50 wt% Ni/alpha-Al2O3-NR."
        elif paper_id == "paper_0220":
            candidates.loc[mask, "manual_review_v0_1_status"] = "reviewed_mechanistic_reference_not_for_baseline_ml"
            candidates.loc[mask, "manual_review_v0_1_summary"] = "Ni-Pt/MgAlOx operando dynamic study; keep as mechanistic reference, not baseline steady-state ML record."
            candidates.loc[mask, "formal_transfer_record_strategy"] = "do not transfer to baseline ML table; optionally keep in mechanistic/descriptor reference subset."

        candidates.loc[mask, "reviewer_notes"] = candidates.loc[mask, "reviewer_notes"].map(
            lambda existing: append_note(existing, clean(candidates.loc[mask, "manual_review_v0_1_summary"].iloc[0]))
        )

    for field in DERIVED_FIELDS:
        if field in candidates.columns:
            candidates[field] = ""
    return candidates


def update_tasks(tasks: pd.DataFrame) -> pd.DataFrame:
    tasks = ensure_columns(tasks, ["manual_review_v0_1_resolution", "manual_review_v0_1_notes"])
    for paper_id, values in manual_updates().items():
        mask = tasks["paper_id"].astype(str).eq(paper_id)
        if not mask.any():
            continue
        status = values["freeze_candidate_status"]
        tasks.loc[mask, "manual_review_v0_1_resolution"] = status
        tasks.loc[mask, "manual_review_v0_1_notes"] = values.get("reviewer_notes", "")
    return tasks


def build_summary(candidates: pd.DataFrame) -> str:
    rows = []
    for paper_id in ["paper_0060", "paper_0101", "paper_0158", "paper_0220"]:
        row = candidates.loc[candidates["paper_id"].astype(str).eq(paper_id)]
        if row.empty:
            continue
        r = row.iloc[0]
        rows.append(
            {
                "paper_id": paper_id,
                "status": clean(r.get("freeze_candidate_status", "")),
                "catalyst": clean(r.get("catalyst_label_reported", "")),
                "support": clean(r.get("support_primary", "")),
                "label": clean(r.get("label_candidate_recommendation", "")),
                "transfer": clean(r.get("formal_transfer_record_strategy", "")),
            }
        )

    lines: List[str] = []
    lines.append("# Manual PDF Review Summary v0.1")
    lines.append("")
    lines.append("## Scope")
    lines.append("")
    lines.append("- This document records manual PDF review decisions for the current freeze v0.1 candidate layer.")
    lines.append("- No formal master extraction table was modified.")
    lines.append("- No machine learning was started.")
    lines.append("- All `derived_*` fields remain blank.")
    lines.append("")
    lines.append("## Updated candidate statuses")
    lines.append("")
    lines.append("| paper_id | status | catalyst/support correction | transfer strategy |")
    lines.append("| --- | --- | --- | --- |")
    for row in rows:
        correction = f"{row['catalyst']} / support={row['support']}"
        lines.append(f"| `{row['paper_id']}` | `{row['status']}` | {correction} | {row['transfer']} |")
    lines.append("")
    lines.append("## Paper-specific review notes")
    lines.append("")
    lines.append("### paper_0060")
    lines.append("")
    lines.append("- Status: `ready_for_manual_transfer_after_check`.")
    lines.append("- Catalyst corrected to unsupported pure Ni / Inco Ni 255.")
    lines.append("- `support_primary` corrected to `unsupported`; `active_metal_secondary` cleared.")
    lines.append("- Suggested main record: 700 C, CH4:H2O=1:2, P=1 atm, GHSV=8500 h^-1, time-on-stream=100 h, methane conversion=98 +/- 2%.")
    lines.append("- Coke data must reference Table 2 conditions separately and must not be mixed with the 100 h stability record.")
    lines.append("")
    lines.append("### paper_0101")
    lines.append("")
    lines.append("- Status: `ready_for_manual_transfer_after_check`.")
    lines.append("- Catalyst corrected to Ni-CGO / NiO-CGO; support corrected to CGO / Ce0.9Gd0.1O1.95.")
    lines.append("- Preparation method corrected to `glycine-nitrate-process`.")
    lines.append("- Ni loading should be recorded as 40 vol.% Ni and must not be forced into wt%.")
    lines.append("- Suggested formal transfer requires split records: baseline activity, S/C=1.5 stability, S/C=0.5 stability.")
    lines.append("- GHSV/WHSV must preserve `7.5 x 10^4 ml/(g-cat h)`; do not write it as `7.5 h^-1`.")
    lines.append("")
    lines.append("### paper_0158")
    lines.append("")
    lines.append("- Status: `ready_for_manual_transfer_after_check`.")
    lines.append("- Prior uncertainty/exclusion corrected; use SRM conditions only.")
    lines.append("- Delete auto-extracted `temperature=300`, `pressure=8`, and `GHSV=52400` if they came from TEM/XPS/DRM contexts.")
    lines.append("- SRM general conditions: 700 C, S/C=2.4, GHSV=65500 h^-1 dry basis, 12 h.")
    lines.append("- Formal transfer should split catalyst-specific records such as NiAl2O4-R, Ni2Al2O5-R, Ni2Al2O5-NR, and commercial 50 wt% Ni/alpha-Al2O3-NR.")
    lines.append("- Table 4 methane conversion is 6 h on-stream data; final conversion and coke data should be notes or separate stability/coking fields.")
    lines.append("")
    lines.append("### paper_0220")
    lines.append("")
    lines.append("- Status: `mechanistic_reference_not_for_baseline_ml`.")
    lines.append("- `active_metal_secondary` corrected to Pt; support corrected to MgAlOx.")
    lines.append("- Loading corrected to 15 wt% Ni and 1 wt% Pt.")
    lines.append("- Not recommended as an ordinary steady-state `methane_conversion_pct` baseline ML training record.")
    lines.append("- Keep as operando/dynamic reaction condition reference for later structure-performance descriptor analysis.")
    lines.append("")
    lines.append("## ML boundary")
    lines.append("")
    lines.append("- These reviewed rows are still not a machine-learning dataset.")
    lines.append("- Records with split requirements must be manually expanded in the formal table after checking original PDF context.")
    lines.append("- `journal_impact_factor`, review status fields, source quality fields, and `derived_*` must not be used as default ML inputs.")
    lines.append("- Different temperature, S/C, pressure, GHSV/WHSV, and time-on-stream conditions must be stratified or normalized before analysis.")
    return "\n".join(lines) + "\n"


def main() -> int:
    args = parse_args()
    candidate_path = ROOT / args.freeze_candidates
    excluded_path = ROOT / args.freeze_excluded
    tasks_path = ROOT / args.manual_tasks
    summary_path = ROOT / args.summary

    candidates = read_csv(candidate_path)
    excluded = read_csv(excluded_path)
    tasks = read_csv(tasks_path)

    candidates = apply_updates(candidates)
    tasks = update_tasks(tasks)

    # Ensure paper_0158 is not duplicated in the excluded table if older runs placed it there.
    if "paper_id" in excluded.columns:
        excluded = excluded.loc[~excluded["paper_id"].astype(str).eq("paper_0158")].copy()

    candidate_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    candidates.to_csv(candidate_path, index=False, encoding="utf-8-sig")
    excluded.to_csv(excluded_path, index=False, encoding="utf-8-sig")
    tasks.to_csv(tasks_path, index=False, encoding="utf-8-sig")
    summary_path.write_text(build_summary(candidates), encoding="utf-8")

    print(f"Updated freeze candidates: {candidate_path}")
    print(f"Updated freeze excluded: {excluded_path}")
    print(f"Updated manual review tasks: {tasks_path}")
    print(f"Manual review summary written: {summary_path}")
    print("Statuses:")
    print(candidates["freeze_candidate_status"].value_counts().to_string())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
