from __future__ import annotations

import argparse
from pathlib import Path
from typing import List

import pandas as pd


ROOT = Path(__file__).resolve().parent.parent


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build source quality diagnosis report for stage4/stage5.")
    parser.add_argument("--classification", default="data/processed/source_quality_classification.csv")
    parser.add_argument("--checked", default="data/processed/stage5_ready_pool_checked.csv")
    parser.add_argument("--experimental", default="data/processed/srm_experimental_extraction_draft.csv")
    parser.add_argument("--output", default="docs/source_quality_diagnosis_report.md")
    return parser.parse_args()


def table_lines(df: pd.DataFrame, columns: List[str], limit: int = 20) -> List[str]:
    if df.empty:
        return ["- 无"]
    lines = []
    for _, row in df[columns].head(limit).iterrows():
        parts = [f"`{column}={row.get(column, '')}`" for column in columns]
        lines.append("- " + "; ".join(parts))
    return lines


def fmt_counts(series: pd.Series) -> List[str]:
    if series.empty:
        return ["- 无"]
    return [f"- `{idx}`: `{int(value)}`" for idx, value in series.items()]


def main() -> int:
    args = parse_args()
    classification = pd.read_csv(ROOT / args.classification)
    checked = pd.read_csv(ROOT / args.checked)
    experimental = pd.read_csv(ROOT / args.experimental)

    ready_rows = classification[
        classification["ready_for_extraction"].fillna("").astype(str).str.lower() == "yes"
    ].copy()
    ready_counts = ready_rows["source_quality_type"].fillna("unknown").value_counts()
    experimental_capable = ready_rows[
        ready_rows["allowed_extraction_scope"].fillna("").astype(str).str.contains("experimental", regex=False)
    ].copy()

    needs_fulltext = classification[
        classification["source_quality_type"].isin(
            ["abstract_only", "doi_landing_page", "redirect_or_forbidden", "navigation_shell", "no_useful_content", "unknown"]
        )
    ].copy()
    needs_fulltext = needs_fulltext.sort_values(
        by=["journal_impact_factor", "priority_score"],
        ascending=[False, False],
        na_position="last",
    )

    experimental_fields = [
        "temperature_c",
        "pressure_bar",
        "steam_to_carbon_ratio",
        "gas_hourly_space_velocity_h_inv",
        "methane_conversion_pct",
        "h2_yield_pct",
        "stability_duration_h",
        "coke_amount_wt_pct",
    ]
    if len(experimental):
        experimental_coverage = {
            field: float(experimental[field].fillna("").astype(str).str.strip().ne("").mean())
            if field in experimental.columns
            else 0.0
            for field in experimental_fields
        }
    else:
        experimental_coverage = {field: 0.0 for field in experimental_fields}

    lines: List[str] = []
    lines.append("# 来源质量诊断报告")
    lines.append("")
    lines.append("## 当前 ready_for_extraction 记录的来源类型")
    lines.append("")
    lines.extend(fmt_counts(ready_counts))
    lines.append("")
    lines.append("## 真正可用于 experimental extraction 的记录数量")
    lines.append("")
    lines.append(f"- 当前 ready_for_extraction 记录数：`{len(ready_rows)}`")
    lines.append(f"- 允许 experimental 抽取的记录数：`{len(experimental_capable)}`")
    lines.append(f"- experimental 草稿记录数：`{len(experimental)}`")
    lines.append("")
    lines.append("## experimental 字段覆盖率低的主要原因")
    lines.append("")
    if len(experimental_capable) == 0:
        lines.append("- 当前没有 `pdf_fulltext` 或 `html_fulltext` 来源进入 experimental 抽取。")
    lines.append("- 多数来源实际是 `Redirecting`、DOI landing page 或摘要页，不包含完整实验表格、实验方法和性能结果。")
    lines.append("- `abstract_only` 来源可以帮助识别催化剂体系，但不允许填写温度、S/C、GHSV、conversion、yield 等具体实验字段。")
    lines.append("- 因不同温度、S/C、压力、GHSV 下的 SRM 结果不可直接比较，experimental 字段必须有原文数值和单位证据才允许填写。")
    lines.append("")
    lines.append("当前关键 experimental 字段覆盖率：")
    for field, coverage in experimental_coverage.items():
        lines.append(f"- `{field}`: `{coverage * 100:.1f}%`")
    lines.append("")
    lines.append("## 需要继续找 PDF / HTML fulltext 的来源")
    lines.append("")
    lines.extend(
        table_lines(
            needs_fulltext,
            [
                "paper_id",
                "source_quality_type",
                "journal",
                "journal_impact_factor",
                "recommended_next_action",
            ],
            limit=25,
        )
    )
    lines.append("")
    lines.append("## 是否建议优先做 PDF 获取增强")
    lines.append("")
    lines.append("- 建议优先增强 PDF / HTML fulltext 获取，而不是扩大候选池。")
    lines.append("- 当前瓶颈不是候选文献数量，而是来源质量不足导致 experimental 字段无法可靠落值。")
    lines.append("- 在 fulltext 获取率提高前，扩大到 top 50 / top 100 会主要增加空抽取和人工复核负担。")

    output_path = ROOT / args.output
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Source quality diagnosis report written to: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
