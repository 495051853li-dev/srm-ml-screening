# Freeze v0.1 Condition-Level Draft QC

## Scope

- This report checks the condition-level draft built from manually reviewed PDF fulltext candidates.
- No formal master extraction table was modified.
- No machine learning was started.
- All `derived_*` fields remain blank.
- `paper_0220` was separated into `mechanistic_reference_records_v0_1.csv` and is not included in the baseline condition draft.

## Inputs checked

- Freeze candidate rows: 4
- Freeze excluded rows retained for context: 16
- Manual review task rows retained for context: 280
- Manual summary length checked: 3831 characters

## Output counts

- Condition-level draft records: 8
- Mechanistic reference records: 1

## Records per paper

- `paper_0060`: 1 condition records
- `paper_0101`: 3 condition records
- `paper_0158`: 4 condition records
- `paper_0220`: 1 mechanistic reference record, excluded from baseline condition draft

## Closest to formal transfer

- `freeze_v0_1_paper_0060_main_activity_stability_001`
- `freeze_v0_1_paper_0101_baseline_activity_001`
- `freeze_v0_1_paper_0101_sc_1_5_stability_001`
- `freeze_v0_1_paper_0101_sc_0_5_stability_001`

These records are still `manual_confirmed=no` and `ready_to_transfer=no`; they are only closest because the manual review already supplied condition/performance values.

## Blocking issues

- 1 records: requires_final_human_confirmation_before_formal_table_transfer
- 1 records: space_velocity_unit_requires_formal_schema_decision; baseline_condition_context_requires_final_confirmation
- 2 records: figure_value_confirmation_required; space_velocity_unit_requires_formal_schema_decision
- 4 records: table4_value_requires_human_confirmation_before_transfer; final_conversion_and_coke_require_manual_entry

## Field coverage in draft records

| field | non-empty records | total records |
| --- | ---: | ---: |
| `active_metal_primary` | 8 | 8 |
| `support_primary` | 8 | 8 |
| `temperature_c` | 8 | 8 |
| `pressure_bar` | 4 | 8 |
| `steam_to_carbon_ratio` | 8 | 8 |
| `gas_hourly_space_velocity_h_inv` | 5 | 8 |
| `weight_hourly_space_velocity_h_inv` | 3 | 8 |
| `time_on_stream_h` | 8 | 8 |
| `methane_conversion_pct` | 8 | 8 |
| `stability_duration_h` | 7 | 8 |
| `conversion_drop_pct_points` | 1 | 8 |
| `coke_amount_mg_gcat` | 0 | 8 |
| `coke_amount_wt_pct` | 2 | 8 |

## Fields still requiring manual confirmation

- `paper_0060`: final check of the 98 +/- 2% conversion context and separation of Table 2 coke conditions.
- `paper_0101`: exact figure values for S/C-specific stability, the meaning of 7.5 x 10^4 ml/(g-cat h), and whether this should remain in WHSV/GHSV notes before formal transfer.
- `paper_0158`: catalyst-specific Table 4 6 h methane conversion values, final conversion, conversion drop, and coke values.
- All records: pressure and space velocity comparability should be checked before any cross-paper analysis.

## Analysis and ML readiness

- Exploratory analysis is not ready until the draft records are manually confirmed and transferred into the formal table with consistent condition definitions.
- Baseline machine learning is still not appropriate: the condition-level draft has only a few records, several fields remain manually pending, and temperature/S-C/pressure/space-velocity differences are leakage-prone if not stratified or normalized.
- `journal_impact_factor`, review workflow fields, source quality fields, and `derived_*` fields must remain excluded from default model inputs.
