from __future__ import annotations

import argparse
from pathlib import Path
from typing import List

import pandas as pd


ROOT = Path(__file__).resolve().parent.parent


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build local PDF ingest report.")
    parser.add_argument("--pdf-dir", default="data/raw/pdfs")
    parser.add_argument("--ingest-log", default="data/processed/local_pdf_ingest_log.csv")
    parser.add_argument("--checked", default="data/processed/stage5_ready_pool_checked.csv")
    parser.add_argument("--metadata", default="data/processed/srm_metadata_extraction_draft.csv")
    parser.add_argument("--experimental", default="data/processed/srm_experimental_extraction_draft.csv")
    parser.add_argument("--output", default="docs/local_pdf_ingest_report.md")
    return parser.parse_args()


def read_csv_optional(path: Path) -> pd.DataFrame:
    return pd.read_csv(path) if path.exists() else pd.DataFrame()


def coverage(df: pd.DataFrame, fields: List[str]) -> List[str]:
    if df.empty:
        return ["- 无记录"]
    lines = []
    for field in fields:
        if field not in df.columns:
            value = 0.0
        else:
            value = float(df[field].fillna("").astype(str).str.strip().ne("").mean())
        lines.append(f"- `{field}`: `{value * 100:.1f}%`")
    return lines


def table_lines(df: pd.DataFrame, columns: List[str], limit: int = 30) -> List[str]:
    if df.empty:
        return ["- 无记录"]
    cols = [column for column in columns if column in df.columns]
    lines = []
    for _, row in df[cols].head(limit).iterrows():
        parts = [f"`{column}={row.get(column, '')}`" for column in cols]
        lines.append("- " + "; ".join(parts))
    return lines


def main() -> int:
    args = parse_args()
    pdf_dir = ROOT / args.pdf_dir
    ingest = read_csv_optional(ROOT / args.ingest_log)
    checked = read_csv_optional(ROOT / args.checked)
    metadata = read_csv_optional(ROOT / args.metadata)
    experimental = read_csv_optional(ROOT / args.experimental)

    pdf_files = sorted(pdf_dir.glob("*.pdf")) if pdf_dir.exists() else []
    matched = ingest[ingest["matched_paper_id"].fillna("").astype(str).str.strip().ne("")] if not ingest.empty else pd.DataFrame()
    parsed = ingest[ingest["parse_status"].fillna("").eq("parsed")] if not ingest.empty else pd.DataFrame()
    ready = ingest[ingest["ready_for_extraction"].fillna("").astype(str).str.lower().eq("yes")] if not ingest.empty else pd.DataFrame()
    unmatched = ingest[ingest["matched_paper_id"].fillna("").astype(str).str.strip().eq("")] if not ingest.empty else pd.DataFrame()

    metadata_fields = [
        "catalyst_family",
        "active_metal_primary",
        "active_metal_secondary",
        "support_primary",
        "preparation_method",
        "calcination_temperature_c",
        "reduction_temperature_c",
    ]
    experimental_fields = [
        "reactor_type",
        "temperature_c",
        "pressure_bar",
        "steam_to_carbon_ratio",
        "gas_hourly_space_velocity_h_inv",
        "methane_conversion_pct",
        "h2_yield_pct",
        "stability_duration_h",
        "coke_amount_wt_pct",
    ]

    lines: List[str] = []
    lines.append("# 本地 PDF 摄入报告")
    lines.append("")
    lines.append("## 处理概况")
    lines.append("")
    lines.append(f"- 发现 PDF 文件数：`{len(pdf_files)}`")
    lines.append(f"- 成功匹配到候选文献数：`{len(matched)}`")
    lines.append(f"- 成功解析 PDF 数：`{len(parsed)}`")
    lines.append(f"- 转为 `pdf_fulltext` 数：`{len(ready)}`")
    lines.append(f"- stage5 ready pool 记录数：`{len(checked)}`")
    lines.append(f"- metadata 草稿记录数：`{len(metadata)}`")
    lines.append(f"- experimental 草稿记录数：`{len(experimental)}`")
    lines.append("")
    lines.append("## 匹配与解析结果")
    lines.append("")
    lines.extend(
        table_lines(
            ingest,
            [
                "pdf_filename",
                "matched_paper_id",
                "match_method",
                "match_confidence",
                "parse_status",
                "page_count",
                "text_length",
                "ready_for_extraction",
            ],
            limit=50,
        )
    )
    lines.append("")
    lines.append("## Metadata 覆盖率")
    lines.append("")
    lines.extend(coverage(metadata, metadata_fields))
    lines.append("")
    lines.append("## Experimental 覆盖率")
    lines.append("")
    lines.extend(coverage(experimental, experimental_fields))
    lines.append("")
    lines.append("## 需要人工重命名或手动匹配的 PDF")
    lines.append("")
    if len(unmatched):
        lines.extend(table_lines(unmatched, ["pdf_filename", "parse_status", "failure_reason"], limit=50))
    else:
        lines.append("- 当前没有无法匹配的 PDF。")
    lines.append("")
    lines.append("## 判断")
    lines.append("")
    if len(ready) >= 10:
        lines.append("- 当前已有一批可用于 stage5 的 PDF fulltext，建议进入人工抽样复核。")
        lines.append("- 仍不建议开始机器学习；需要先复核实验字段定义、单位和反应条件可比性。")
    else:
        lines.append("- 当前 PDF fulltext 数量仍偏少，建议继续补充 PDF 后再扩大抽取。")

    output_path = ROOT / args.output
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Local PDF ingest report written to: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
