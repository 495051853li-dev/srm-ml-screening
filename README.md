# SRM ML Screening

## Project Focus

This repository supports machine-learning-assisted screening for steam reforming of methane (SRM) catalysts. The current working emphasis is a **batch literature processing pipeline**, not a single-paper extraction workflow.

The purpose of the pipeline is to:

1. search and maintain a large candidate paper pool
2. rank and filter papers by SRM relevance, journal quality, and extractability
3. batch-fetch accessible source pages or PDFs
4. generate conservative automatic extraction drafts
5. produce QC summaries and analysis-preparation exports
6. prepare for later statistics and ML work without jumping into modeling too early

## Core Rules

- Do not invent experimental values.
- Literature data collected under different temperatures, steam-to-carbon ratios, pressures, GHSV, feed compositions, and times-on-stream are not automatically comparable.
- `journal_impact_factor` is currently used for literature screening priority, not as a default machine-learning feature.
- `derived_*` fields must remain blank in raw or automatic extraction layers and may only be created later by scripts from frozen measured datasets.
- Blank values are acceptable when the source is unclear; guessed values are not.

## Batch Pipeline

The current main pipeline is controlled by:

- [src/run_batch_literature_pipeline.py](D:/ML/srm/srm_ml_screening/src/run_batch_literature_pipeline.py)

Pipeline stages:

1. `stage1_search_candidates`
2. `stage2_enrich_journal_metrics`
3. `stage3_score_and_filter`
4. `stage4_fetch_sources`
5. `stage5_extract_fields`
6. `stage6_qc_and_freeze`
7. `stage7_analysis_ready_exports`

Detailed stage overview:

- [docs/batch_pipeline_overview.md](D:/ML/srm/srm_ml_screening/docs/batch_pipeline_overview.md)

Current execution plan and status:

- [docs/PLAN.md](D:/ML/srm/srm_ml_screening/docs/PLAN.md)

### Stage Inputs and Outputs

`stage1_search_candidates`

- input: `data/processed/candidate_papers.csv` or refreshed OpenAlex/Crossref search results
- output: [data/processed/candidate_papers_master.csv](D:/ML/srm/srm_ml_screening/data/processed/candidate_papers_master.csv)

`stage2_enrich_journal_metrics`

- input: `candidate_papers_master.csv`
- output: [data/processed/candidate_papers_master_enriched.csv](D:/ML/srm/srm_ml_screening/data/processed/candidate_papers_master_enriched.csv)

`stage3_score_and_filter`

- input: `candidate_papers_master_enriched.csv`
- outputs:
  - [data/processed/candidate_papers_high_if_scored.csv](D:/ML/srm/srm_ml_screening/data/processed/candidate_papers_high_if_scored.csv)
  - [data/processed/eligible_high_if_pool.csv](D:/ML/srm/srm_ml_screening/data/processed/eligible_high_if_pool.csv)
  - [data/processed/backup_low_if_pool.csv](D:/ML/srm/srm_ml_screening/data/processed/backup_low_if_pool.csv)
  - [data/processed/candidate_papers_top50.csv](D:/ML/srm/srm_ml_screening/data/processed/candidate_papers_top50.csv)
  - [data/processed/candidate_papers_top100.csv](D:/ML/srm/srm_ml_screening/data/processed/candidate_papers_top100.csv)

`stage4_fetch_sources`

- input: `eligible_high_if_pool.csv`
- outputs:
  - [data/processed/fulltext_fetch_manifest.csv](D:/ML/srm/srm_ml_screening/data/processed/fulltext_fetch_manifest.csv)
  - [outputs/fulltext/](D:/ML/srm/srm_ml_screening/outputs/fulltext)

`stage4.5_fulltext_acquisition_enhancement`

- input: `eligible_high_if_pool.csv` + `candidate_papers_high_if_scored.csv` + current manifest
- outputs:
  - [data/processed/fulltext_source_candidates.csv](D:/ML/srm/srm_ml_screening/data/processed/fulltext_source_candidates.csv)
  - [data/processed/fulltext_candidate_fetch_log.csv](D:/ML/srm/srm_ml_screening/data/processed/fulltext_candidate_fetch_log.csv)
  - [data/processed/manual_pdf_request_list.csv](D:/ML/srm/srm_ml_screening/data/processed/manual_pdf_request_list.csv)
- policy:
  - Open-access fulltext is allowed.
  - Publisher PDF/HTML fulltext directly available through the current legal institutional IP is allowed.
  - Paywall, login, captcha, Cloudflare, and other access-control bypass is not allowed.
  - Sci-Hub or unauthorized PDF mirrors are not allowed.

`stage5_extract_fields`

- input: `candidate_papers_high_if_scored.csv` + `fulltext_fetch_manifest.csv`
- output: [data/processed/srm_extraction_auto_draft.csv](D:/ML/srm/srm_ml_screening/data/processed/srm_extraction_auto_draft.csv)

`stage6_qc_and_freeze`

- inputs: auto draft + scored pool + fetch manifest
- outputs:
  - [data/processed/srm_extraction_qc_summary.csv](D:/ML/srm/srm_ml_screening/data/processed/srm_extraction_qc_summary.csv)
  - [data/processed/srm_extraction_record_flags.csv](D:/ML/srm/srm_ml_screening/data/processed/srm_extraction_record_flags.csv)
  - [docs/batch_qc_report.md](D:/ML/srm/srm_ml_screening/docs/batch_qc_report.md)

`stage7_analysis_ready_exports`

- inputs: auto draft + QC flags + scored metadata
- outputs:
  - [data/processed/analysis_ready_dataset.csv](D:/ML/srm/srm_ml_screening/data/processed/analysis_ready_dataset.csv)
  - [data/processed/analysis_ready_ni_based_high_if.csv](D:/ML/srm/srm_ml_screening/data/processed/analysis_ready_ni_based_high_if.csv)

## How to Run

Run the full batch pipeline:

```powershell
python src/run_batch_literature_pipeline.py
```

Refresh OpenAlex/Crossref search before rebuilding the pipeline:

```powershell
python src/run_batch_literature_pipeline.py --refresh-search
```

Rerun only selected stages:

```powershell
python src/run_batch_literature_pipeline.py --stages stage3_score_and_filter
python src/run_batch_literature_pipeline.py --stages stage4_fetch_sources stage5_extract_fields
python src/run_batch_literature_pipeline.py --stages stage6_qc_and_freeze stage7_analysis_ready_exports
```

Run the authorized fulltext acquisition enhancement on a small batch:

```powershell
python src/discover_fulltext_sources.py --limit 20
python src/fetch_fulltext_authorized.py --limit 20 --skip-existing --sleep 1.0 --timeout 30 --max-per-domain 5
python src/check_stage5_ready_pool.py
python src/classify_source_quality.py
```

Detailed fulltext policy and behavior:

- [docs/fulltext_acquisition_strategy.md](D:/ML/srm/srm_ml_screening/docs/fulltext_acquisition_strategy.md)
- [docs/legal_fulltext_access_policy.md](D:/ML/srm/srm_ml_screening/docs/legal_fulltext_access_policy.md)

## Manual Extraction Layer

The repository still keeps a structured manual extraction schema for later curation or downstream correction:

- [data/processed/srm_literature_extraction_template.csv](D:/ML/srm/srm_ml_screening/data/processed/srm_literature_extraction_template.csv)
- [docs/srm_literature_data_dictionary.md](D:/ML/srm/srm_ml_screening/docs/srm_literature_data_dictionary.md)
- [src/validate_extraction_dataset.py](D:/ML/srm/srm_ml_screening/src/validate_extraction_dataset.py)

Validation command:

```powershell
python src/validate_extraction_dataset.py --input data/processed/srm_literature_extraction_template.csv
```

This manual extraction layer is now a **curation target**, not the main orchestration layer. The main orchestration layer is the batch pipeline above.

## Field Usage Guidance

- Journal metric fields are literature metadata for screening, stratification, bias analysis, and sensitivity analysis.
- Journal metric fields are not recommended as default machine-learning input features.
- If journal metric fields are ever added to a model, use them only as a controlled comparison to check literature-source bias.
- Measured catalyst, preparation, condition, activity, stability, and coking fields belong to the extraction layer.
- `derived_*` fields are high-leakage-risk fields and must not be manually entered into raw extraction datasets.

## Current Outputs Worth Checking First

- [data/processed/candidate_papers_master.csv](D:/ML/srm/srm_ml_screening/data/processed/candidate_papers_master.csv)
- [data/processed/candidate_papers_high_if_scored.csv](D:/ML/srm/srm_ml_screening/data/processed/candidate_papers_high_if_scored.csv)
- [data/processed/eligible_high_if_pool.csv](D:/ML/srm/srm_ml_screening/data/processed/eligible_high_if_pool.csv)
- [data/processed/fulltext_fetch_manifest.csv](D:/ML/srm/srm_ml_screening/data/processed/fulltext_fetch_manifest.csv)
- [data/processed/srm_extraction_auto_draft.csv](D:/ML/srm/srm_ml_screening/data/processed/srm_extraction_auto_draft.csv)
- [docs/batch_qc_report.md](D:/ML/srm/srm_ml_screening/docs/batch_qc_report.md)
