"""Build markdown reports for first-batch screening and auto extraction."""

from __future__ import annotations

import csv
from collections import Counter
from pathlib import Path
from typing import Dict, List


ROOT = Path(__file__).resolve().parent.parent


def read_rows(path: Path) -> List[Dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def top_rows(rows: List[Dict[str, str]], n: int) -> List[Dict[str, str]]:
    eligible = [row for row in rows if row.get("final_priority_label") != "exclude"]
    label_order = {"top_priority": 0, "medium_priority": 1, "low_priority": 2}
    eligible.sort(
        key=lambda r: (
            label_order.get(r.get("final_priority_label", ""), 9),
            -float(r.get("priority_score", "0") or 0),
            r.get("publication_year", ""),
            r.get("title", ""),
        )
    )
    return eligible[:n]


def build_screening_report(candidate_rows: List[Dict[str, str]], scored_rows: List[Dict[str, str]], output_path: Path) -> None:
    counts = Counter(row.get("final_priority_label", "") for row in scored_rows)
    top20 = top_rows(scored_rows, 20)
    top30 = top_rows(scored_rows, 30)

    lines: List[str] = []
    lines.append("# 第一批文献二次筛选报告")
    lines.append("")
    lines.append("## 总体情况")
    lines.append("")
    lines.append(f"- 原始候选文献数：{len(candidate_rows)}")
    lines.append(f"- 二次筛选后 `top_priority`：{counts.get('top_priority', 0)}")
    lines.append(f"- 二次筛选后 `medium_priority`：{counts.get('medium_priority', 0)}")
    lines.append(f"- 二次筛选后 `low_priority`：{counts.get('low_priority', 0)}")
    lines.append(f"- 二次筛选后 `exclude`：{counts.get('exclude', 0)}")
    lines.append("")
    lines.append("## 筛选逻辑摘要")
    lines.append("")
    lines.append("- 优先保留明确属于 methane steam reforming / steam reforming of methane 的文章")
    lines.append("- 优先 `journal_article`，`review` 保留但不作为第一批优先抽取对象")
    lines.append("- 对题目、摘要和元数据中更可能包含 catalyst + condition + performance 信息的文章提高优先级")
    lines.append("- 对明显混合体系或非目标体系自动降级或排除")
    lines.append("")
    lines.append("## Top 20 列表")
    lines.append("")
    lines.append("| rank | paper_id | year | title | journal | priority_score | label |")
    lines.append("| --- | --- | --- | --- | --- | --- | --- |")
    for index, row in enumerate(top20, start=1):
        lines.append(
            f"| {index} | {row.get('paper_id','')} | {row.get('publication_year','')} | {row.get('title','').replace('|','/')} | {row.get('journal','').replace('|','/')} | {row.get('priority_score','')} | {row.get('final_priority_label','')} |"
        )
    lines.append("")
    lines.append("## Top 30 列表")
    lines.append("")
    lines.append("| rank | paper_id | year | title | journal | priority_score | label |")
    lines.append("| --- | --- | --- | --- | --- | --- | --- |")
    for index, row in enumerate(top30, start=1):
        lines.append(
            f"| {index} | {row.get('paper_id','')} | {row.get('publication_year','')} | {row.get('title','').replace('|','/')} | {row.get('journal','').replace('|','/')} | {row.get('priority_score','')} | {row.get('final_priority_label','')} |"
        )
    lines.append("")
    lines.append("## 说明")
    lines.append("")
    lines.append("- 本报告仅用于第一批人工录入准备，不代表最终纳入集。")
    lines.append("- `exclude` 仅表示当前自动规则下不优先，不代表完全无研究价值。")
    output_path.write_text("\n".join(lines), encoding="utf-8")


def build_auto_extraction_summary(
    scored_rows: List[Dict[str, str]],
    fetch_rows: List[Dict[str, str]],
    draft_rows: List[Dict[str, str]],
    output_path: Path,
) -> None:
    top20 = top_rows(scored_rows, 20)
    field_names = [
        "catalyst_family",
        "active_metal_primary",
        "support_primary",
        "preparation_method",
        "temperature_c",
        "pressure_bar",
        "steam_to_carbon_ratio",
        "time_on_stream_h",
        "methane_conversion_pct",
        "h2_yield_pct",
        "stability_duration_h",
        "coke_amount_mg_gcat",
        "coke_amount_wt_pct",
    ]
    success_counts = {field: sum(1 for row in draft_rows if row.get(field)) for field in field_names}
    sorted_fields = sorted(success_counts.items(), key=lambda item: (-item[1], item[0]))

    lines: List[str] = []
    lines.append("# 自动抽取阶段摘要")
    lines.append("")
    lines.append("## 总体统计")
    lines.append("")
    lines.append(f"- 二次筛选后原始候选数：{len(scored_rows)}")
    lines.append(f"- Top 20 抓取尝试数：{len(top20)}")
    lines.append(f"- 成功获取可用于抽取文本的文献数：{sum(1 for row in fetch_rows if row.get('usable_for_extraction') == 'yes')}")
    lines.append(f"- 成功生成自动抽取草稿的文献数：{len(draft_rows)}")
    lines.append("")
    lines.append("## 全文获取情况")
    lines.append("")
    lines.append("| paper_id | fetch_status | usable_for_extraction | fetch_notes |")
    lines.append("| --- | --- | --- | --- |")
    for row in fetch_rows:
        lines.append(
            f"| {row.get('paper_id','')} | {row.get('fetch_status','')} | {row.get('usable_for_extraction','')} | {row.get('fetch_notes','').replace('|','/')} |"
        )
    lines.append("")
    lines.append("## 字段抽取成功率较高的字段")
    lines.append("")
    for field, count in sorted_fields[:8]:
        lines.append(f"- `{field}`：{count}/{len(draft_rows)}")
    lines.append("")
    lines.append("## 最需要人工复核的字段")
    lines.append("")
    lines.append("- `active_metal_secondary`：容易被双金属或文本上下文误触发")
    lines.append("- `active_metal_*_loading_wt_pct`：负载量单位和归属对象需要人工核对")
    lines.append("- `temperature_c`、`pressure_bar`、`steam_to_carbon_ratio`：出版商页面经常只给摘要，条件信息覆盖不稳定")
    lines.append("- `methane_conversion_pct`、`h2_yield_pct`：摘要中可能只出现部分结果，不能替代全文核查")
    lines.append("- `stability_duration_h`、`conversion_drop_pct_points`、`coke_amount_*`：通常最依赖全文和图表，自动抽取成功率较低")
    lines.append("")
    lines.append("## 说明")
    lines.append("")
    lines.append("- 自动抽取草稿只用于人工复核前的预填充，不得直接视为正式实验数据。")
    lines.append("- 所有 `derived_*` 字段在本阶段均保持为空。")
    output_path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    candidate_rows = read_rows(ROOT / "data" / "processed" / "candidate_papers.csv")
    scored_rows = read_rows(ROOT / "data" / "processed" / "candidate_papers_scored.csv")
    fetch_rows = read_rows(ROOT / "data" / "processed" / "fulltext_fetch_log.csv")
    draft_rows = read_rows(ROOT / "data" / "processed" / "srm_extraction_auto_draft.csv")

    screening_output = ROOT / "docs" / "first_batch_screening_report.md"
    extraction_output = ROOT / "docs" / "auto_extraction_summary.md"

    build_screening_report(candidate_rows, scored_rows, screening_output)
    build_auto_extraction_summary(scored_rows, fetch_rows, draft_rows, extraction_output)

    print(f"Screening report: {screening_output}")
    print(f"Extraction summary: {extraction_output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
