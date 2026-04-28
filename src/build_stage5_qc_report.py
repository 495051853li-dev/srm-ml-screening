from __future__ import annotations

import argparse
from pathlib import Path
from typing import Dict, List

import pandas as pd


ROOT = Path(__file__).resolve().parent.parent

METADATA_FIELDS = [
    "catalyst_label_reported",
    "catalyst_family",
    "active_metal_primary",
    "active_metal_secondary",
    "active_metal_primary_loading_wt_pct",
    "active_metal_secondary_loading_wt_pct",
    "active_metal_total_loading_wt_pct",
    "support_primary",
    "support_secondary",
    "promoter_1",
    "promoter_1_loading_wt_pct",
    "preparation_method",
    "calcination_temperature_c",
    "reduction_temperature_c",
    "reduction_time_h",
    "reduction_gas",
]

EXPERIMENTAL_FIELDS = [
    "reactor_type",
    "temperature_c",
    "pressure_bar",
    "steam_to_carbon_ratio",
    "feed_ch4_vol_pct",
    "feed_h2o_vol_pct",
    "feed_co2_vol_pct",
    "feed_n2_vol_pct",
    "gas_hourly_space_velocity_h_inv",
    "weight_hourly_space_velocity_h_inv",
    "contact_time_s",
    "time_on_stream_h",
    "methane_conversion_pct",
    "h2_yield_pct",
    "h2_selectivity_pct",
    "co_selectivity_pct",
    "h2_co_ratio",
    "stability_test_performed",
    "stability_duration_h",
    "conversion_drop_pct_points",
    "coking_test_method",
    "coke_amount_mg_gcat",
    "coke_amount_wt_pct",
    "measured_value_basis",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build markdown QC report for stage5 extraction drafts.")
    parser.add_argument("--checked", default="data/processed/stage5_ready_pool_checked.csv")
    parser.add_argument("--metadata", default="data/processed/srm_metadata_extraction_draft.csv")
    parser.add_argument("--experimental", default="data/processed/srm_experimental_extraction_draft.csv")
    parser.add_argument("--merged", default="data/processed/srm_extraction_auto_draft_stage5.csv")
    parser.add_argument("--output", default="docs/stage5_extraction_qc_report.md")
    return parser.parse_args()


def coverage_rows(df: pd.DataFrame, fields: List[str]) -> List[tuple[str, float]]:
    if len(df) == 0:
        return [(field, 0.0) for field in fields]
    rows: List[tuple[str, float]] = []
    for field in fields:
        if field not in df.columns:
            rows.append((field, 0.0))
            continue
        coverage = float(df[field].fillna("").astype(str).str.strip().ne("").mean())
        rows.append((field, coverage))
    return rows


def fmt_pct(value: float) -> str:
    return f"{value * 100:.1f}%"


def main() -> int:
    args = parse_args()
    checked = pd.read_csv(ROOT / args.checked)
    metadata = pd.read_csv(ROOT / args.metadata) if Path(ROOT / args.metadata).exists() else pd.DataFrame()
    experimental = pd.read_csv(ROOT / args.experimental) if Path(ROOT / args.experimental).exists() else pd.DataFrame()
    merged = pd.read_csv(ROOT / args.merged) if Path(ROOT / args.merged).exists() else pd.DataFrame()

    ready_original = int((checked["ready_for_extraction"].fillna("").astype(str).str.lower() == "yes").sum()) if len(checked) else 0
    ready_checked = int((checked["ready_for_extraction_checked"].fillna("").astype(str).str.lower() == "yes").sum()) if len(checked) else 0
    metadata_ready = int((checked["ready_for_metadata"].fillna("").astype(str).str.lower() == "yes").sum()) if len(checked) else 0
    experimental_ready = int((checked["ready_for_experimental"].fillna("").astype(str).str.lower() == "yes").sum()) if len(checked) else 0

    metadata_cov = coverage_rows(metadata, METADATA_FIELDS)
    experimental_cov = coverage_rows(experimental, EXPERIMENTAL_FIELDS)
    easiest_metadata = sorted(metadata_cov, key=lambda item: item[1], reverse=True)[:5]
    hardest_metadata = sorted(metadata_cov, key=lambda item: item[1])[:5]
    easiest_experimental = sorted(experimental_cov, key=lambda item: item[1], reverse=True)[:5]
    hardest_experimental = sorted(experimental_cov, key=lambda item: item[1])[:5]

    focus_review = checked.loc[
        checked["page_quality_label"].fillna("").isin(["weak_source", "metadata_only"]) | checked["not_ready_reason"].fillna("").ne(""),
        ["paper_id", "page_quality_label", "not_ready_reason"],
    ].copy()

    paper_0221 = checked.loc[checked["paper_id"] == "paper_0221"]
    if len(paper_0221):
        paper_0221_message = (
            f"paper_0221 当前 `ready_for_extraction_checked={paper_0221.iloc[0]['ready_for_extraction_checked']}`，"
            f"`page_quality_label={paper_0221.iloc[0]['page_quality_label']}`，"
            f"`not_ready_reason={paper_0221.iloc[0]['not_ready_reason']}`。"
        )
    else:
        paper_0221_message = "paper_0221 不在当前 ready pool 检查结果中。"

    lines: List[str] = []
    lines.append("# Stage5 抽取质控报告")
    lines.append("")
    lines.append("## 总览")
    lines.append("")
    lines.append(f"- ready pool 原始数量：`{ready_original}`")
    lines.append(f"- 通过二次检查数量：`{ready_checked}`")
    lines.append(f"- metadata-ready 数量：`{metadata_ready}`")
    lines.append(f"- experimental-ready 数量：`{experimental_ready}`")
    lines.append(f"- 合并后的 stage5 草稿记录数：`{len(merged)}`")
    lines.append("")
    lines.append("## Metadata 字段覆盖率")
    lines.append("")
    for field, coverage in metadata_cov:
        lines.append(f"- `{field}`: {fmt_pct(coverage)}")
    lines.append("")
    lines.append("最容易抽取的 metadata 字段：")
    for field, coverage in easiest_metadata:
        lines.append(f"- `{field}`: {fmt_pct(coverage)}")
    lines.append("")
    lines.append("最难抽取的 metadata 字段：")
    for field, coverage in hardest_metadata:
        lines.append(f"- `{field}`: {fmt_pct(coverage)}")
    lines.append("")
    lines.append("## Experimental 字段覆盖率")
    lines.append("")
    for field, coverage in experimental_cov:
        lines.append(f"- `{field}`: {fmt_pct(coverage)}")
    lines.append("")
    lines.append("最容易抽取的 experimental 字段：")
    for field, coverage in easiest_experimental:
        lines.append(f"- `{field}`: {fmt_pct(coverage)}")
    lines.append("")
    lines.append("最难抽取的 experimental 字段：")
    for field, coverage in hardest_experimental:
        lines.append(f"- `{field}`: {fmt_pct(coverage)}")
    lines.append("")
    lines.append("## 重点人工复核记录")
    lines.append("")
    if len(focus_review):
        for _, row in focus_review.iterrows():
            lines.append(
                f"- `{row['paper_id']}`: `page_quality_label={row['page_quality_label']}`; `not_ready_reason={row['not_ready_reason']}`"
            )
    else:
        lines.append("- 当前没有额外被标记为重点人工复核的记录。")
    lines.append("")
    lines.append("## paper_0221 判定")
    lines.append("")
    lines.append(f"- {paper_0221_message}")
    lines.append("- 如果仍然只是 Redirecting 或仅有极弱页面文本，则不建议继续作为当前抽取池输入。")
    lines.append("")
    lines.append("## 是否适合扩大到 top 50 / top 100")
    lines.append("")
    if experimental_ready <= 1:
        lines.append("- 当前**不建议**直接扩大到 top 50 或 top 100。")
        lines.append("- 主要原因是 stage4 当前保留下来的可用正文/摘要页仍然很少，experimental 抽取覆盖率过低。")
        lines.append("- 更合理的下一步是继续提升来源质量，或为摘要页与正文页分别设计更清晰的抽取策略。")
    else:
        lines.append("- 可以考虑先小步扩大，但仍建议先补强来源层。")

    output_path = ROOT / args.output
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Stage5 QC report written to: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
