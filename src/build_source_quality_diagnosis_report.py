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
    parser.add_argument("--candidate-fetch-log", default="data/processed/fulltext_candidate_fetch_log.csv")
    parser.add_argument("--manual-pdf-list", default="data/processed/manual_pdf_request_list.csv")
    parser.add_argument("--output", default="docs/source_quality_diagnosis_report.md")
    return parser.parse_args()


def read_csv_optional(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path)


def fmt_counts(series: pd.Series) -> List[str]:
    if series.empty:
        return ["- 无记录"]
    return [f"- `{idx}`: `{int(value)}`" for idx, value in series.items()]


def table_lines(df: pd.DataFrame, columns: List[str], limit: int = 20) -> List[str]:
    if df.empty:
        return ["- 无记录"]
    existing_columns = [column for column in columns if column in df.columns]
    lines = []
    for _, row in df[existing_columns].head(limit).iterrows():
        parts = [f"`{column}={row.get(column, '')}`" for column in existing_columns]
        lines.append("- " + "; ".join(parts))
    return lines


def main() -> int:
    args = parse_args()
    classification = read_csv_optional(ROOT / args.classification)
    checked = read_csv_optional(ROOT / args.checked)
    experimental = read_csv_optional(ROOT / args.experimental)
    candidate_fetch_log = read_csv_optional(ROOT / args.candidate_fetch_log)
    manual_pdf = read_csv_optional(ROOT / args.manual_pdf_list)

    if classification.empty:
        raise FileNotFoundError(f"Missing or empty classification file: {ROOT / args.classification}")

    ready_rows = classification[
        classification["ready_for_extraction"].fillna("").astype(str).str.lower() == "yes"
    ].copy()
    ready_counts = ready_rows["source_quality_type"].fillna("unknown").value_counts()
    all_quality_counts = classification["source_quality_type"].fillna("unknown").value_counts()
    experimental_capable = ready_rows[
        ready_rows["allowed_extraction_scope"].fillna("").astype(str).str.contains("experimental", regex=False)
    ].copy()

    needs_fulltext_types = [
        "abstract_only",
        "doi_landing_page",
        "redirect_or_forbidden",
        "navigation_shell",
        "no_useful_content",
        "unknown",
    ]
    needs_fulltext = classification[classification["source_quality_type"].isin(needs_fulltext_types)].copy()
    sort_columns = [column for column in ["journal_impact_factor", "priority_score"] if column in needs_fulltext.columns]
    if sort_columns:
        needs_fulltext = needs_fulltext.sort_values(by=sort_columns, ascending=[False] * len(sort_columns), na_position="last")

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
    experimental_coverage = {}
    for field in experimental_fields:
        if not experimental.empty and field in experimental.columns:
            experimental_coverage[field] = float(experimental[field].fillna("").astype(str).str.strip().ne("").mean())
        else:
            experimental_coverage[field] = 0.0

    lines: List[str] = []
    lines.append("# 来源质量诊断报告")
    lines.append("")
    lines.append("## 当前来源质量分层")
    lines.append("")
    lines.append(f"- 分层记录数：`{len(classification)}`")
    lines.extend(fmt_counts(all_quality_counts))
    lines.append("")
    lines.append("## ready_for_extraction 记录的来源类型")
    lines.append("")
    lines.append(f"- ready_for_extraction=yes 记录数：`{len(ready_rows)}`")
    lines.extend(fmt_counts(ready_counts))
    lines.append("")
    lines.append("## 真正可用于 experimental extraction 的记录数量")
    lines.append("")
    lines.append(f"- 允许 metadata + experimental 抽取的记录数：`{len(experimental_capable)}`")
    lines.append(f"- 当前 experimental 草稿记录数：`{len(experimental)}`")
    lines.append("")
    lines.append("## fulltext candidate fetch 诊断")
    lines.append("")
    if candidate_fetch_log.empty:
        lines.append("- 尚未生成 `fulltext_candidate_fetch_log.csv`。")
    else:
        lines.append(f"- 已记录 candidate_url 尝试数：`{len(candidate_fetch_log)}`")
        if "fetch_status" in candidate_fetch_log.columns:
            lines.extend(fmt_counts(candidate_fetch_log["fetch_status"].fillna("unknown").value_counts()))
        if "source_quality_type" in candidate_fetch_log.columns:
            lines.append("")
            lines.append("candidate_url 获取后的来源质量：")
            lines.extend(fmt_counts(candidate_fetch_log["source_quality_type"].fillna("unknown").replace("", "unknown").value_counts()))
    lines.append("")
    lines.append("## experimental 字段覆盖率低的主要原因")
    lines.append("")
    if len(experimental_capable) == 0:
        lines.append("- 当前没有 `pdf_fulltext` 或 `html_fulltext` 来源进入 experimental 抽取。")
    lines.append("- 多数来源实际是 DOI landing page、Redirecting 页面、受限页面、导航壳或摘要页，不包含完整实验方法、反应条件和性能数据表。")
    lines.append("- `abstract_only` 只能用于题录、催化剂体系和有限催化剂层面信息，不能填写温度、S/C、GHSV、conversion、yield 等具体实验字段。")
    lines.append("- 不同温度、S/C、压力、GHSV 下的 SRM 性能不可直接比较；实验字段必须有原文数值、单位和上下文证据才允许进入草稿。")
    lines.append("")
    lines.append("当前关键 experimental 字段覆盖率：")
    for field, coverage in experimental_coverage.items():
        lines.append(f"- `{field}`: `{coverage * 100:.1f}%`")
    lines.append("")
    lines.append("## 需要继续寻找 PDF / HTML fulltext 的来源")
    lines.append("")
    lines.extend(
        table_lines(
            needs_fulltext,
            [
                "paper_id",
                "source_quality_type",
                "journal",
                "journal_impact_factor",
                "priority_score",
                "recommended_next_action",
            ],
            limit=25,
        )
    )
    lines.append("")
    lines.append("## 人工 PDF 优先清单")
    lines.append("")
    if manual_pdf.empty:
        lines.append("- 尚未生成 `manual_pdf_request_list.csv`，或当前没有符合条件的记录。")
    else:
        lines.append(f"- 待人工合法下载 PDF 的优先记录数：`{len(manual_pdf)}`")
        lines.extend(
            table_lines(
                manual_pdf,
                ["paper_id", "journal", "journal_impact_factor", "priority_score", "doi"],
                limit=15,
            )
        )
    lines.append("")
    lines.append("## 是否建议优先做 PDF 获取增强")
    lines.append("")
    lines.append("- 建议继续优先增强合法 PDF / HTML fulltext 获取，而不是扩大候选池。")
    lines.append("- 当前瓶颈不是候选文献数量，而是可用于实验字段抽取的全文来源数量。")
    lines.append("- 当 `pdf_fulltext` 或 `html_fulltext` 达到一批稳定样本后，再重新运行 stage5 的 metadata 与 experimental 抽取更合理。")

    output_path = ROOT / args.output
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Source quality diagnosis report written to: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
