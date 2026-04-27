"""Generate batch QC summaries and record-level flags for SRM auto-extraction drafts."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import List

import pandas as pd


ID_COLUMNS = {"paper_id", "first_author", "publication_year", "title", "journal", "doi"}
QC_METADATA_COLUMNS = {
    "analyst_qc_status",
    "extraction_confidence",
    "extraction_source_location",
    "extraction_method",
    "manual_review_required",
    "derived_activity_score",
    "derived_stability_score",
    "derived_coking_resistance_score",
    "derived_overall_screening_score",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="QC and freeze-prep summaries for SRM batch extraction.")
    parser.add_argument("--draft-input", default="data/processed/srm_extraction_auto_draft.csv")
    parser.add_argument("--scored-input", default="data/processed/candidate_papers_high_if_scored.csv")
    parser.add_argument("--manifest-input", default="data/processed/fulltext_fetch_manifest.csv")
    parser.add_argument("--summary-output", default="data/processed/srm_extraction_qc_summary.csv")
    parser.add_argument("--flags-output", default="data/processed/srm_extraction_record_flags.csv")
    parser.add_argument("--report-output", default="docs/batch_qc_report.md")
    return parser.parse_args()


def non_empty(series: pd.Series) -> pd.Series:
    return series.fillna("").astype(str).str.strip() != ""


def main() -> int:
    args = parse_args()
    draft = pd.read_csv(args.draft_input)
    scored = pd.read_csv(args.scored_input)
    manifest = pd.read_csv(args.manifest_input)

    merged = draft.merge(
        scored[
            [
                "paper_id",
                "journal_impact_factor",
                "journal_quality_score",
                "likely_ni_based",
                "final_priority_label",
                "priority_score",
                "document_type",
            ]
        ],
        on="paper_id",
        how="left",
    )

    data_fields = [col for col in draft.columns if col not in ID_COLUMNS and col not in QC_METADATA_COLUMNS]
    summary_rows: List[dict] = []
    for field in data_fields:
        filled_mask = non_empty(merged[field])
        coverage = float(filled_mask.mean()) if len(merged) else 0.0
        if filled_mask.any():
            high_conf_ratio = float((merged.loc[filled_mask, "extraction_confidence"] == "medium").mean())
        else:
            high_conf_ratio = 0.0
        summary_rows.append(
            {
                "field_name": field,
                "non_empty_count": int(filled_mask.sum()),
                "coverage_rate": round(coverage, 4),
                "high_confidence_ratio": round(high_conf_ratio, 4),
            }
        )

    summary_df = pd.DataFrame(summary_rows).sort_values(by=["coverage_rate", "high_confidence_ratio", "field_name"], ascending=[False, False, True])

    merged["key_condition_count"] = (
        non_empty(merged["temperature_c"]).astype(int)
        + non_empty(merged["pressure_bar"]).astype(int)
        + non_empty(merged["steam_to_carbon_ratio"]).astype(int)
        + non_empty(merged["gas_hourly_space_velocity_h_inv"]).astype(int)
        + non_empty(merged["weight_hourly_space_velocity_h_inv"]).astype(int)
        + non_empty(merged["time_on_stream_h"]).astype(int)
    )
    merged["key_performance_count"] = (
        non_empty(merged["methane_conversion_pct"]).astype(int)
        + non_empty(merged["h2_yield_pct"]).astype(int)
        + non_empty(merged["h2_selectivity_pct"]).astype(int)
        + non_empty(merged["co_selectivity_pct"]).astype(int)
        + non_empty(merged["h2_co_ratio"]).astype(int)
    )
    merged["core_identity_count"] = (
        non_empty(merged["active_metal_primary"]).astype(int)
        + non_empty(merged["support_primary"]).astype(int)
        + non_empty(merged["catalyst_family"]).astype(int)
    )

    merged["human_sample_review_flag"] = "no"
    merged.loc[
        (merged["manual_review_required"] == "yes")
        & ((merged["extraction_confidence"] != "medium") | (merged["key_condition_count"] < 2) | (merged["key_performance_count"] < 1)),
        "human_sample_review_flag",
    ] = "yes"
    medium_rows = merged[merged["extraction_confidence"] == "medium"].sort_values("paper_id").head(5).index
    merged.loc[medium_rows, "human_sample_review_flag"] = "yes"

    merged["analysis_ready_flag"] = "no"
    merged.loc[
        (merged["core_identity_count"] >= 2)
        & (merged["key_condition_count"] >= 2)
        & (merged["key_performance_count"] >= 1)
        & (merged["extraction_confidence"].isin(["medium", "low_to_medium"])),
        "analysis_ready_flag",
    ] = "yes"
    merged["freeze_recommendation"] = merged["analysis_ready_flag"].map({"yes": "candidate_for_analysis_freeze", "no": "needs_more_review"})

    flags_df = merged[
        [
            "paper_id",
            "title",
            "journal",
            "journal_impact_factor",
            "likely_ni_based",
            "final_priority_label",
            "priority_score",
            "extraction_confidence",
            "manual_review_required",
            "human_sample_review_flag",
            "analysis_ready_flag",
            "freeze_recommendation",
            "key_condition_count",
            "key_performance_count",
            "core_identity_count",
        ]
    ].copy()

    Path(args.summary_output).parent.mkdir(parents=True, exist_ok=True)
    summary_df.to_csv(args.summary_output, index=False, encoding="utf-8")
    flags_df.to_csv(args.flags_output, index=False, encoding="utf-8")

    total_eligible = len(scored[scored["final_priority_label"].isin(["top_priority", "medium_priority"])])
    total_fetched = len(manifest)
    total_usable = int((manifest["usable_for_extraction"] == "yes").sum()) if len(manifest) else 0
    total_extracted = len(draft)
    if_ge6_candidates = scored[pd.to_numeric(scored["journal_impact_factor"], errors="coerce") >= 6.0]
    if_lt6_candidates = scored[pd.to_numeric(scored["journal_impact_factor"], errors="coerce") < 6.0]
    ni_subset = scored[scored["likely_ni_based"] == "yes"]
    analysis_ready_count = int((flags_df["analysis_ready_flag"] == "yes").sum())

    manifest_enriched = manifest.merge(
        scored[["paper_id", "likely_ni_based"]],
        on="paper_id",
        how="left",
    )
    doc_type_lines = []
    for document_type, sub in manifest_enriched.groupby("document_type", dropna=False):
        usable = int((sub["usable_for_extraction"] == "yes").sum())
        doc_type_label = str(document_type) if pd.notna(document_type) and str(document_type).strip() else "unknown"
        doc_type_lines.append(f"- `{doc_type_label}`: {len(sub)} 条尝试，{usable} 条可用于抽取")

    if_ge6_attempts = manifest_enriched[pd.to_numeric(manifest_enriched["journal_impact_factor"], errors="coerce") >= 6.0]
    if_lt6_attempts = manifest_enriched[pd.to_numeric(manifest_enriched["journal_impact_factor"], errors="coerce") < 6.0]

    report = f"""# 批量抽取 QC 报告

## 总体状态

- 高优先候选池规模：{total_eligible}
- 已尝试批量获取来源：{total_fetched}
- 可用于自动抽取的来源：{total_usable}
- 已生成自动抽取草稿：{total_extracted}

## 字段覆盖率说明

- 输出文件：[data/processed/srm_extraction_qc_summary.csv](D:/ML/srm/srm_ml_screening/data/processed/srm_extraction_qc_summary.csv)
- `coverage_rate` 表示该字段在当前自动抽取草稿中的非空比例
- `high_confidence_ratio` 当前按“非空值中来自 `extraction_confidence = medium` 的比例”近似计算

## 抽取成功率

- 批量来源获取成功率：{(total_usable / total_fetched) if total_fetched else 0:.2%}
- 自动抽取成稿率（相对可用来源）：{(total_extracted / total_usable) if total_usable else 0:.2%}

按文献类型统计：

{chr(10).join(doc_type_lines) if doc_type_lines else '- 当前 manifest 中没有可统计的文献类型分组'}

## 子集差异

- `IF >= 6.0` 候选规模：{len(if_ge6_candidates)}
- `IF < 6.0` 候选规模：{len(if_lt6_candidates)}
- `IF >= 6.0` 当前来源获取尝试：{len(if_ge6_attempts)}，其中可用于抽取：{int((if_ge6_attempts['usable_for_extraction'] == 'yes').sum()) if len(if_ge6_attempts) else 0}
- `IF < 6.0` 当前来源获取尝试：{len(if_lt6_attempts)}，其中可用于抽取：{int((if_lt6_attempts['usable_for_extraction'] == 'yes').sum()) if len(if_lt6_attempts) else 0}
- `Ni-based` 候选规模：{len(ni_subset)}
- 当前自动抽取主池仍集中在 `IF >= 6.0` 高优先候选，这属于文献筛选策略，不代表期刊 IF 可进入后续模型

## 记录级标记

- 输出文件：[data/processed/srm_extraction_record_flags.csv](D:/ML/srm/srm_ml_screening/data/processed/srm_extraction_record_flags.csv)
- `human_sample_review_flag = yes`：优先用于人工抽样 QC
- `analysis_ready_flag = yes`：可进入分析准备导出候选
- `freeze_recommendation = candidate_for_analysis_freeze`：适合进入冻结候选子集
- 当前 `analysis_ready_flag = yes` 记录数：{analysis_ready_count}

## 风险提醒

- 不同温度、S/C、压力、GHSV、TOS 下的文献数据默认不可直接比较
- `journal_impact_factor` 只是当前文献筛选元数据，不应带入后续机器学习特征
- 自动抽取草稿仍有漏抽和定义误判风险，尤其是 `conversion / yield / selectivity`、`GHSV / WHSV`、`stability duration / TOS` 等字段
"""

    output_path = Path(args.report_output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(report, encoding="utf-8")

    print(f"QC summary: {args.summary_output}")
    print(f"Record flags: {args.flags_output}")
    print(f"QC report: {args.report_output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
