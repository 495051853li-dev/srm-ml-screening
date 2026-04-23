# SRM ML Screening

## Literature Extraction Workflow

This repository starts with a manual literature extraction layer for steam reforming of methane (SRM) catalyst studies. The goal of this first stage is to capture paper-level and experiment-level information in a structured, reproducible format before any modeling begins.

1. Extract one row per catalyst-test condition into [data/processed/srm_literature_extraction_template.csv](D:/ML/srm/srm_ml_screening/data/processed/srm_literature_extraction_template.csv).
2. Use the column definitions in [docs/srm_literature_data_dictionary.md](D:/ML/srm/srm_ml_screening/docs/srm_literature_data_dictionary.md) while entering values.
3. Keep measured values exactly as reported in the paper, and leave fields blank rather than guessing.
4. Keep derived or judgment-based fields separate from measured values. Any future composite ranking or screening score should be generated downstream, not typed in as if it were an experimental observation.
5. Validate the extracted CSV before analysis:

```powershell
python src/validate_extraction_dataset.py --input data/processed/srm_literature_extraction_template.csv
```

Important assumptions and risks:

- Literature results collected at different temperatures, steam-to-carbon ratios, pressures, GHSV, feed dilutions, and times-on-stream are not automatically comparable.
- Catalyst identity fields should describe composition and processing history, but they should not encode target outcomes or future labels in a way that creates leakage.
- Stability, deactivation, and coking resistance should be recorded from explicit evidence in the paper, not inferred from activity alone.
- Blank values are acceptable when papers omit information; invented values are not.
- Journal metric fields are literature metadata for screening, stratification, bias analysis, and sensitivity analysis. They are not recommended as default machine-learning input features.
- If journal metric fields are ever added to a model, they should be used only as a controlled comparison to test whether the model is learning literature-source bias.

Field usage guidance:

- Measured experimental values are the catalyst composition, preparation, reaction-condition, activity, stability, and coking-related fields reported from the paper.
- Derived fields (`derived_*`) must remain blank during raw extraction. They are high-leakage-risk fields and may only be generated later by scripts from frozen measured datasets.
- Journal metric fields (`journal_impact_factor_year`, `journal_impact_factor`, `journal_quartile`, `journal_metrics_source`, `journal_metrics_notes`) are metadata fields, not default model features.

## Next Steps

Before any modeling work, use the extraction planning documents in `docs/` to prepare the first batch of literature entry:

- [docs/first_batch_extraction_plan.md](D:/ML/srm/srm_ml_screening/docs/first_batch_extraction_plan.md)
- [docs/single_paper_extraction_checklist.md](D:/ML/srm/srm_ml_screening/docs/single_paper_extraction_checklist.md)
- [docs/ml_field_roles.md](D:/ML/srm/srm_ml_screening/docs/ml_field_roles.md)

Recommended sequence:

1. Select the first batch of SRM papers using the criteria in `first_batch_extraction_plan.md`.
2. Enter one paper at a time using `single_paper_extraction_checklist.md`.
3. Validate the dataset after each small batch.
4. Run a first-round dataset audit before discussing any modeling targets.
