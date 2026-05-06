from __future__ import annotations

import argparse
from pathlib import Path
from typing import List, Tuple

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


def read_csv_optional(path: Path) -> pd.DataFrame:
    return pd.read_csv(path) if path.exists() else pd.DataFrame()


def coverage_rows(df: pd.DataFrame, fields: List[str]) -> List[Tuple[str, float]]:
    rows: List[Tuple[str, float]] = []
    for field in fields:
        if df.empty or field not in df.columns:
            rows.append((field, 0.0))
        else:
            rows.append((field, float(df[field].fillna("").astype(str).str.strip().ne("").mean())))
    return rows


def fmt_pct(value: float) -> str:
    return f"{value * 100:.1f}%"


def counts_line(df: pd.DataFrame, column: str) -> List[str]:
    if df.empty or column not in df.columns:
        return ["- 无记录"]
    return [f"- `{key}`: `{int(value)}`" for key, value in df[column].fillna("missing").value_counts().items()]


def main() -> int:
    args = parse_args()
    checked = read_csv_optional(ROOT / args.checked)
    metadata = read_csv_optional(ROOT / args.metadata)
    experimental = read_csv_optional(ROOT / args.experimental)
    merged = read_csv_optional(ROOT / args.merged)

    metadata_cov = coverage_rows(metadata, METADATA_FIELDS)
    experimental_cov = coverage_rows(experimental, EXPERIMENTAL_FIELDS)

    lines: List[str] = []
    lines.append("# Stage5 字段抽取 QC 报告")
    lines.append("")
    lines.append("## 总览")
    lines.append("")
    lines.append(f"- ready pool 记录数：`{len(checked)}`")
    if not checked.empty and "source_quality_type" in checked.columns:
        lines.append(f"- `pdf_fulltext` 记录数：`{int((checked['source_quality_type'] == 'pdf_fulltext').sum())}`")
    if not checked.empty and "ready_for_experimental" in checked.columns:
        lines.append(f"- experimental-ready 记录数：`{int((checked['ready_for_experimental'].astype(str).str.lower() == 'yes').sum())}`")
    lines.append(f"- metadata 草稿记录数：`{len(metadata)}`")
    lines.append(f"- experimental 草稿记录数：`{len(experimental)}`")
    lines.append(f"- 合并 stage5 草稿记录数：`{len(merged)}`")
    lines.append("")
    lines.append("## Metadata 抽取置信度")
    lines.append("")
    lines.extend(counts_line(metadata, "extraction_confidence_metadata"))
    lines.append("")
    lines.append("## Experimental 抽取置信度")
    lines.append("")
    lines.extend(counts_line(experimental, "extraction_confidence_experimental"))
    lines.append("")
    lines.append("## Metadata 字段覆盖率")
    lines.append("")
    for field, coverage in metadata_cov:
        lines.append(f"- `{field}`: `{fmt_pct(coverage)}`")
    lines.append("")
    lines.append("## Experimental 字段覆盖率")
    lines.append("")
    for field, coverage in experimental_cov:
        lines.append(f"- `{field}`: `{fmt_pct(coverage)}`")
    lines.append("")
    lines.append("## 人工复核重点")
    lines.append("")
    lines.append("- experimental 字段仍按保守规则抽取，所有记录默认 `manual_review_required=yes`。")
    lines.append("- `pressure_bar`、`temperature_c`、`steam_to_carbon_ratio`、`GHSV/WHSV`、`conversion/yield/selectivity` 必须人工核对原文上下文，避免把表征条件、预处理条件或摘要描述误当作反应性能。")
    lines.append("- 不同温度、S/C、压力和空速下的数据不可直接比较，后续冻结和建模前必须按工况分层或标准化。")
    lines.append("- `derived_*` 字段保持为空，不能作为人工提取输入。")
    lines.append("")
    lines.append("## 下一步建议")
    lines.append("")
    if len(experimental) >= 10:
        lines.append("- 当前已有一批 PDF fulltext，可以进入人工抽样复核阶段；不建议直接建模。")
    else:
        lines.append("- 当前 PDF fulltext 数量仍偏少，建议继续补充 PDF 后再扩大 stage5 抽取。")

    output_path = ROOT / args.output
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Stage5 QC report written to: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
