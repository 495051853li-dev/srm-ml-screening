# SRM Literature Extraction Data Dictionary

This dictionary defines the blank literature extraction template for steam reforming of methane (SRM) catalyst studies.

Design principles:

- One row should represent one catalyst under one reported test condition or evaluation slice.
- `paper_id` groups records from the same publication, while `condition_id` groups records that share the same reported catalyst-test condition within or across extraction passes.
- Measured values are kept separate from derived or analyst-generated scores.
- Leave fields blank when the paper does not report them.
- Do not mix conditions from different runs into one row.
- Treat cross-paper comparisons cautiously unless reaction conditions have been normalized explicitly.

## Column Definitions

| Column | Type | Unit / Format | Definition | Notes / Common Inconsistencies |
| --- | --- | --- | --- | --- |
| record_id | string | free text, unique | Unique row identifier for the extracted record. | Recommended pattern: `firstauthor_year_suffix`. Must be unique within the dataset. |
| paper_id | string | free text | Identifier grouping rows from the same paper. | Can match DOI slug or a curated internal ID. |
| reference_type | string | enum | Source type. | Suggested values: `journal_article`, `review_from_primary_source`, `thesis`, `conference_paper`. Prefer primary sources. |
| first_author | string | text | First author surname or citation lead author. | Normalize consistently. |
| publication_year | integer | year | Publication year. | Use the paper year, not online-access date. |
| title | string | text | Paper title. | Preserve exact title text if possible. |
| journal | string | text | Journal or venue name. | Use one naming convention throughout the dataset. |
| journal_impact_factor_year | integer | year | Year associated with the recorded journal metric. | Required if `journal_impact_factor` is filled. |
| journal_impact_factor | float | unitless | Journal impact factor for the specified year. | Literature metadata only; not recommended as a default ML feature. |
| journal_quartile | string | enum | Journal quartile label. | Suggested values: `Q1`, `Q2`, `Q3`, `Q4`, `unclear`. |
| journal_metrics_source | string | enum | Source used to retrieve the journal metric. | Suggested values: `JCR`, `Scopus`, `manual_lookup`, `other`. |
| journal_metrics_notes | string | text | Notes about the journal metric lookup. | Use for ambiguities, source discrepancies, or manual decisions. |
| doi | string | DOI | Digital Object Identifier. | Some papers omit DOI; leave blank if missing. |
| condition_id | string | free text | Identifier grouping rows that represent the same reported catalyst-test condition. | Useful when one paper yields multiple rows from the same catalyst under matched conditions or when multiple outcome slices are extracted. |
| catalyst_label_reported | string | text | Catalyst name exactly or nearly exactly as reported in the paper. | Useful when papers use sample codes like `Ni/Al2O3-Ce`. |
| catalyst_family | string | enum | Broad catalyst class. | Suggested values: `Ni_based`, `noble_metal_based`, `perovskite_derived`, `hydrotalcite_derived`, `spinel`, `other`. |
| active_metal_primary | string | text | Primary active metal. | Usually `Ni`, `Rh`, `Ru`, `Pt`, `Co`, etc. |
| active_metal_secondary | string | text | Secondary active metal if present. | Leave blank for monometallic catalysts. |
| active_metal_primary_loading_wt_pct | float | wt% | Reported loading of the primary active metal. | Keep blank if the paper reports only total loading or if the basis is unclear. |
| active_metal_secondary_loading_wt_pct | float | wt% | Reported loading of the secondary active metal. | Useful for bimetallic systems; leave blank for monometallic catalysts. |
| active_metal_total_loading_wt_pct | float | wt% | Total reported active-metal loading across all active metals. | Can differ from `active_metal_loading_wt_pct`, which is retained for backward compatibility with earlier schema versions. |
| active_metal_atomic_ratio_reported | string | text | Reported atomic ratio among active metals. | Record as reported, for example `Ni:Ru = 9:1` or `Ni/Rh = 4`. |
| active_metal_loading_wt_pct | float | wt% | Legacy active-metal loading field retained for backward compatibility. | Use for the main reported loading when the paper gives only one value or when earlier extraction rounds used this field. |
| active_metal_loading_basis | string | enum | Basis of the reported loading. | Suggested values: `nominal`, `measured`, `unclear`. |
| promoter_1 | string | text | First promoter or additive. | Promoters and supports are often conflated in papers; capture carefully. |
| promoter_1_loading_wt_pct | float | wt% | Loading of first promoter if reported. | Leave blank when only molar ratios are reported. |
| promoter_2 | string | text | Second promoter or additive. | Optional. |
| promoter_2_loading_wt_pct | float | wt% | Loading of second promoter if reported. | Optional. |
| support_primary | string | text | Main support material. | Examples: `Al2O3`, `CeO2`, `MgAl2O4`. |
| support_secondary | string | text | Secondary support or mixed-oxide component. | Optional. |
| support_notes | string | text | Support composition or structural notes. | Use for mixed oxides, oxygen storage additives, phases, etc. |
| precursor_metal_source | string | text | Metal precursor(s) used in synthesis. | Example: nickel nitrate hexahydrate. |
| precursor_support_source | string | text | Support precursor(s) or support source. | Optional. |
| preparation_method | string | enum/text | Main catalyst preparation route. | Suggested values include `impregnation`, `co_precipitation`, `sol_gel`, `deposition_precipitation`, `hydrothermal`, `combustion`, `mechanical_mixing`, `commercial`, `other`. |
| preparation_details | string | text | Key preparation details. | Use for pH, aging time, calcination sequence, solvent, etc. |
| calcination_temperature_c | float | degC | Main calcination temperature. | Papers may report multiple calcination steps; use `preparation_details` when needed. |
| calcination_time_h | float | h | Main calcination duration. | Optional. |
| reduction_temperature_c | float | degC | Pre-reduction or activation temperature. | Distinguish catalyst reduction from reaction temperature. |
| reduction_time_h | float | h | Pre-reduction duration. | Optional. |
| reduction_gas | string | text | Reducing gas composition. | Example: `10% H2/N2`, `pure H2`. |
| reactor_type | string | enum/text | Reactor configuration used for testing. | Suggested values: `fixed_bed`, `packed_bed`, `fluidized_bed`, `microreactor`, `monolith`, `other`. |
| catalyst_mass_g | float | g | Catalyst mass loaded in the reactor. | Some papers report volume instead of mass; describe exceptions in notes. |
| particle_size_um | float | um | Catalyst particle size or sieve fraction midpoint if one value can be represented. | When a range is reported, record the detail in `extraction_notes`. |
| temperature_c | float | degC | Reaction temperature for the reported record. | A major comparability variable. |
| pressure_bar | float | bar | Total reaction pressure. | Papers may use atm, kPa, or MPa; convert to bar when possible and note assumptions. |
| steam_to_carbon_ratio | float | mol/mol | Feed steam-to-carbon ratio. | For SRM methane, this is a critical condition and often inconsistently defined. |
| feed_ch4_vol_pct | float | vol% | Methane fraction in the feed if reported. | Some studies use diluted feeds; do not assume balance gas identity. |
| feed_h2o_vol_pct | float | vol% | Steam fraction in the feed if reported on a volumetric basis. | Leave blank if only S/C is reported. |
| feed_co2_vol_pct | float | vol% | Carbon dioxide fraction in the feed if co-fed. | Relevant for mixed reforming studies; ensure it is truly SRM-focused. |
| feed_n2_vol_pct | float | vol% | Nitrogen fraction in the feed if reported. | Optional. |
| feed_h2_vol_pct | float | vol% | Hydrogen fraction in the feed if co-fed. | Optional. |
| balance_gas_identity | string | text | Identity of the balance gas when the feed composition does not sum to a fully reported mixture. | Common values may include `N2`, `Ar`, `He`, or `unclear`. |
| gas_hourly_space_velocity_h_inv | float | h^-1 | GHSV. | GHSV definitions may vary by standard conditions and catalyst bed basis. |
| weight_hourly_space_velocity_h_inv | float | h^-1 | WHSV. | Optional when papers report WHSV instead of GHSV. |
| contact_time_s | float | s | Contact or residence time. | Optional. |
| time_on_stream_h | float | h | Time on stream corresponding to the reported performance value. | Critical for stability interpretation. |
| methane_conversion_pct | float | % | Methane conversion. | Ensure whether it is instantaneous, steady-state, peak, or averaged. |
| h2_yield_pct | float | % | Hydrogen yield. | Some papers define yield differently; check denominator. |
| h2_selectivity_pct | float | % | Hydrogen selectivity if explicitly reported. | Less common in SRM papers. |
| h2_production_rate_mmol_gcat_h | float | mmol gcat^-1 h^-1 | Hydrogen production rate normalized by catalyst mass. | Optional; unit conversions should be documented if performed. |
| h2_production_rate_mmol_gmetal_h | float | mmol gmetal^-1 h^-1 | Hydrogen production rate normalized by active metal mass. | Optional and not directly comparable to per-catalyst values. |
| co_selectivity_pct | float | % | CO selectivity. | Definition may differ by carbon basis or dry basis. |
| co2_selectivity_pct | float | % | CO2 selectivity. | Optional. |
| h2_co_ratio | float | mol/mol | H2/CO product ratio. | Optional. |
| performance_definition_notes | string | text | Notes clarifying how the reported performance metric was defined. | Use for dry-basis corrections, denominator choices, steady-state windows, or other paper-specific metric definitions. |
| stability_test_performed | string | enum | Whether a time-on-stream stability test was explicitly reported. | Suggested values: `yes`, `no`, `unclear`. |
| stability_duration_h | float | h | Duration of explicit stability test. | Distinguish from single-point `time_on_stream_h`. |
| conversion_drop_pct_points | float | percentage points | Absolute drop in methane conversion over the stated stability test. | Derived from paper-reported endpoints only; do not estimate from plots unless your protocol allows digitization. |
| coking_test_method | string | text | Method used to assess coking. | Example: `TGA`, `TEM`, `Raman`, `elemental carbon balance`. |
| coke_amount_mg_gcat | float | mg/gcat | Coke amount normalized by catalyst mass. | Some papers report wt% coke instead. |
| coke_amount_wt_pct | float | wt% | Coke amount in weight percent if reported. | Do not convert unless the paper provides the needed basis. |
| carbon_balance_closure_pct | float | % | Carbon balance closure if reported. | Optional. |
| sintering_evidence | string | enum/text | Whether sintering was explicitly observed. | Suggested values: `yes`, `no`, `unclear`, plus notes if needed. |
| sulfur_tolerance_tested | string | enum | Whether sulfur tolerance was evaluated. | Suggested values: `yes`, `no`, `unclear`. |
| deactivation_mode_reported | string | text | Reported dominant deactivation mechanism(s). | Record paper wording when possible: coking, sintering, poisoning, oxidation, etc. |
| characterization_summary | string | text | Short summary of key characterization evidence relevant to performance. | Keep concise and factual. |
| measured_value_basis | string | enum | Whether performance values are reported as fresh, steady-state, peak, or averaged. | Suggested values: `fresh`, `steady_state`, `peak`, `average_over_window`, `unclear`. |
| digitized_from_plot | string | enum | Whether any value in the row was digitized from a figure. | Suggested values: `yes`, `no`. |
| extraction_notes | string | text | Manual notes about ambiguities or conversion assumptions. | Use this field generously. |
| comparable_within_study | string | enum | Whether the row is considered directly comparable to other rows from the same study. | Suggested values: `yes`, `no`, `unclear`. |
| analyst_qc_status | string | enum | Manual quality-control status. | Suggested values: `pending`, `reviewed`, `flagged`. |
| derived_activity_score | float | unitless | Future analyst-generated score summarizing activity. | Must remain blank during raw literature extraction. Manual entry is not allowed. This high-leakage-risk field may only be generated later by scripts from a frozen measured dataset. |
| derived_stability_score | float | unitless | Future analyst-generated score summarizing stability. | Must remain blank during raw literature extraction. Manual entry is not allowed. This high-leakage-risk field may only be generated later by scripts from a frozen measured dataset. |
| derived_coking_resistance_score | float | unitless | Future analyst-generated score summarizing coking resistance. | Must remain blank during raw literature extraction. Manual entry is not allowed. This high-leakage-risk field may only be generated later by scripts from a frozen measured dataset. |
| derived_overall_screening_score | float | unitless | Future composite screening score. | Must remain blank during raw literature extraction. Manual entry is not allowed. This high-leakage-risk field may only be generated later by scripts from a frozen measured dataset. |

## Recommended Controlled Vocabularies

These are recommendations, not hard-coded ontology commitments:

- `reference_type`: `journal_article`, `review_from_primary_source`, `thesis`, `conference_paper`
- `catalyst_family`: `Ni_based`, `noble_metal_based`, `perovskite_derived`, `hydrotalcite_derived`, `spinel`, `other`
- `active_metal_loading_basis`: `nominal`, `measured`, `unclear`
- `preparation_method`: `impregnation`, `co_precipitation`, `sol_gel`, `deposition_precipitation`, `hydrothermal`, `combustion`, `mechanical_mixing`, `commercial`, `other`
- `reactor_type`: `fixed_bed`, `packed_bed`, `fluidized_bed`, `microreactor`, `monolith`, `other`
- `stability_test_performed`: `yes`, `no`, `unclear`
- `sulfur_tolerance_tested`: `yes`, `no`, `unclear`
- `measured_value_basis`: `fresh`, `steady_state`, `peak`, `average_over_window`, `unclear`
- `digitized_from_plot`: `yes`, `no`
- `comparable_within_study`: `yes`, `no`, `unclear`
- `analyst_qc_status`: `pending`, `reviewed`, `flagged`
- `journal_quartile`: `Q1`, `Q2`, `Q3`, `Q4`, `unclear`
- `journal_metrics_source`: `JCR`, `Scopus`, `manual_lookup`, `other`

## Field Role Guidance

- Journal metric fields (`journal_impact_factor_year`, `journal_impact_factor`, `journal_quartile`, `journal_metrics_source`, `journal_metrics_notes`) are literature metadata.
- These journal metric fields are mainly intended for literature screening, data stratification, bias analysis, and sensitivity analysis.
- These journal metric fields are not recommended as default machine-learning input features.
- If they are ever included in a model, they should be used only in controlled comparison experiments to test whether the model is exploiting literature-source bias.
- Derived score fields (`derived_*`) are not part of raw literature extraction and should be populated only by documented downstream scripts after the measured dataset has been frozen.

## Common SRM Extraction Pitfalls

- Temperature, steam-to-carbon ratio, pressure, and GHSV strongly affect performance. Do not compare catalysts across papers as if they were tested under identical conditions.
- Methane conversion, hydrogen yield, and hydrogen productivity are not interchangeable targets.
- Some papers report nominal catalyst composition, while others report post-synthesis composition from ICP or EDX. Use `active_metal_loading_basis`.
- Stability claims may rely on short runs, selected snapshots, or visually interpreted plots. Record the exact basis in `measured_value_basis`, `performance_definition_notes`, and `extraction_notes`.
- Coke can be reported as wt%, mg/gcat, mg/g, mmol C/gcat, Raman proxy, or qualitative microscopy evidence. Keep original reported basis rather than forcing unsafe conversion.
- Promoters, supports, and structural modifiers are often ambiguously described. Favor faithful extraction over aggressive normalization.
- Journal metrics can introduce publication-source bias if treated as model inputs. Keep them as metadata unless you are explicitly testing that bias.
- Derived scores can easily leak future labels into training if entered manually. Generate them later in code, from documented rules, after the measured dataset has been frozen.
