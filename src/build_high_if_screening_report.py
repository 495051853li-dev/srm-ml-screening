"""Build a report for high-impact-factor-first SRM candidate screening."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build report for high-IF SRM screening.")
    parser.add_argument("--candidate-input", default="data/processed/candidate_papers.csv")
    parser.add_argument("--old-scored-input", default="data/processed/candidate_papers_scored.csv")
    parser.add_argument("--high-if-input", default="data/processed/candidate_papers_high_if_scored.csv")
    parser.add_argument("--first-batch-input", default="data/processed/first_batch_priority_papers_if6plus.csv")
    parser.add_argument("--summary-input", default="outputs/tables/high_if_screening_summary.json")
    parser.add_argument("--report-output", default="docs/high_if_screening_report.md")
    return parser.parse_args()


def fmt(value: object) -> str:
    text = "" if pd.isna(value) else str(value)
    return text.strip()


def reason_for_downgrade(row: pd.Series) -> str:
    impact = pd.to_numeric(pd.Series([row.get("journal_impact_factor")]), errors="coerce").iloc[0]
    if row.get("document_type") == "review":
        return "review 仅保留为背景参考，不进入第一批正式抽取"
    if pd.isna(impact):
        return "期刊 IF 未能可靠补全，暂列人工核查或备选池"
    if impact < 6.0:
        return f"期刊 IF={impact:.1f}，低于第一批高质量门槛 6.0"
    if str(row.get("likely_contains_performance", "")).strip().lower() != "yes":
        return "摘要/元数据中性能字段信号偏弱，可提取性不足"
    return "虽然相关，但在高 IF 优先逻辑下未进入第一批池"


def build_table(df: pd.DataFrame, max_rows: int) -> str:
    if df.empty:
        return "无。"
    lines = ["| paper_id | year | journal | IF | Ni-based | title |", "| --- | ---: | --- | ---: | --- | --- |"]
    for _, row in df.head(max_rows).iterrows():
        lines.append(
            "| {paper_id} | {year} | {journal} | {impact} | {ni} | {title} |".format(
                paper_id=fmt(row.get("paper_id")),
                year=fmt(row.get("publication_year")),
                journal=fmt(row.get("journal")),
                impact=fmt(row.get("journal_impact_factor")),
                ni=fmt(row.get("likely_ni_based")),
                title=fmt(row.get("title")),
            )
        )
    return "\n".join(lines)


def main() -> int:
    args = parse_args()
    candidate_df = pd.read_csv(args.candidate_input)
    old_scored_df = pd.read_csv(args.old_scored_input)
    high_if_df = pd.read_csv(args.high_if_input)
    first_batch_df = pd.read_csv(args.first_batch_input)
    summary = json.loads(Path(args.summary_input).read_text(encoding="utf-8"))

    old_top = old_scored_df[old_scored_df["final_priority_label"] == "top_priority"].copy()
    new_pool_ids = set(first_batch_df["paper_id"].tolist())
    downgraded = high_if_df[
        high_if_df["paper_id"].isin(old_top["paper_id"]) & ~high_if_df["paper_id"].isin(new_pool_ids)
    ].copy()
    downgraded["downgrade_reason"] = downgraded.apply(reason_for_downgrade, axis=1)
    downgraded = downgraded.sort_values(
        by=["old_priority_rank", "priority_score", "publication_year"],
        ascending=[True, False, False],
    )

    paper_0078 = high_if_df[high_if_df["paper_id"] == "paper_0078"].iloc[0]
    paper_0221 = high_if_df[high_if_df["paper_id"] == "paper_0221"].iloc[0]

    high_success_fields = []
    if not first_batch_df.empty:
        high_success_fields = [
            "journal_impact_factor",
            "relevance_score",
            "extractability_score",
            "likely_ni_based",
            "likely_contains_performance",
        ]

    report = f"""# 高 IF 优先筛选报告

## 任务目标

本轮筛选暂停了以低质量候选文献为主的复核路径，改为在候选文献层重新执行“高质量优先筛选”。新的核心原则是：

- `journal_impact_factor` 仅作为当前第一批文献筛选的硬指标使用
- `journal_impact_factor` 不作为后续机器学习输入特征
- 第一批正式抽取优先考虑 `journal_article`、明确 SRM 相关、可提取性较高、且 `journal_impact_factor >= 6.0` 的文章
- `review` 即使影响因子较高，也仅保留为背景参考，不进入第一批正式抽取

## 总体统计

- 原始候选文献：{summary['raw_candidates']} 篇
- 成功补全期刊 IF 的候选文献：{summary['journal_metrics_filled_rows']} 篇
- 仍需人工补期刊指标核查：{summary['needs_manual_journal_check_rows']} 篇
- `IF >= 6.0` 且主题明确相关的 `journal_article`：{summary['if_ge_6_relevant_articles']} 篇
- 最终进入第一批高优先池：{summary['first_batch_high_if_pool']} 篇
- 备选低 IF / 需人工补期刊指标池：{summary['backup_pool']} 篇

## 第一批高优先池

当前第一批高优先池保存在：

- [data/processed/first_batch_priority_papers_if6plus.csv](D:\\ML\\srm\\srm_ml_screening\\data\\processed\\first_batch_priority_papers_if6plus.csv)

前 20 条如下：

{build_table(first_batch_df, 20)}

## 备选池说明

备选池保存在：

- [data/processed/backup_low_if_papers.csv](D:\\ML\\srm\\srm_ml_screening\\data\\processed\\backup_low_if_papers.csv)

这些记录通常满足“主题相关”，但因为以下原因没有进入第一批高优先池：

- 期刊 IF 低于 6.0
- 期刊 IF 缺失，需人工核查
- 摘要/元数据中条件或性能信号偏弱
- 文献类型是 `review`

## 被降级的原先优先文献

以下文献在旧版“可提取性优先”排序里优先级较高，但在新的“高 IF 优先”逻辑下被降级：

{build_table(downgraded, 20)}

详细降级原因：

""" + "\n".join(
        f"- `{row.paper_id}`: {row.downgrade_reason}"
        for row in downgraded.itertuples()
    ) + f"""

## 对 `paper_0078` 和 `paper_0221` 的建议

### `paper_0078`

- 题目：{fmt(paper_0078.get('title'))}
- 期刊：{fmt(paper_0078.get('journal'))}
- IF：{fmt(paper_0078.get('journal_impact_factor')) or '未可靠补全'}
- 当前标签：{fmt(paper_0078.get('final_priority_label'))}
- 建议：{"不建议继续作为第一批优先复核对象" if fmt(paper_0078.get('final_priority_label')) != 'top_priority' and fmt(paper_0078.get('final_priority_label')) != 'medium_priority' else "可以保留在第一批池中"}

原因：

- {reason_for_downgrade(paper_0078)}

### `paper_0221`

- 题目：{fmt(paper_0221.get('title'))}
- 期刊：{fmt(paper_0221.get('journal'))}
- IF：{fmt(paper_0221.get('journal_impact_factor')) or '未可靠补全'}
- 当前标签：{fmt(paper_0221.get('final_priority_label'))}
- 建议：{"不建议继续作为第一批优先复核对象" if fmt(paper_0221.get('final_priority_label')) not in ['top_priority', 'medium_priority'] else "仍建议保留在第一批优先复核池中"}

原因：

- {reason_for_downgrade(paper_0221)}

## 结论

这轮高 IF 优先重排后，第一批正式抽取不再由“当前可抓到的页面质量”主导，而改为由“SRM 相关性 + 可提取性 + 高质量期刊”共同决定。这样做的好处是：

- 第一批抽取池的文献质量更稳定
- 后续人工复核时间更值得投入
- 可以避免把低 IF 或来源证据不足的文章过早推入正式抽取

同时需要明确提醒：

- 期刊 IF 只是当前文献筛选硬指标，不是后续机器学习特征
- 若将其错误地带入模型，会构成明显的数据泄漏风险
"""

    output_path = Path(args.report_output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(report, encoding="utf-8")
    print(f"Report written to {args.report_output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
