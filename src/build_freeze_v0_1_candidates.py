from __future__ import annotations

import argparse
import re
from pathlib import Path
from typing import Iterable, List

import pandas as pd


ROOT = Path(__file__).resolve().parent.parent

REQUIRED_VALUE_FIELDS = [
    "active_metal_primary",
    "support_primary",
]

TEMPERATURE_FIELDS = ["temperature_c"]
FEED_RATIO_FIELDS = ["steam_to_carbon_ratio"]
LABEL_FIELDS = ["methane_conversion_pct", "h2_yield_pct"]

MANUAL_CHECK_FIELDS = [
    "temperature_c",
    "pressure_bar",
    "steam_to_carbon_ratio",
    "gas_hourly_space_velocity_h_inv",
    "weight_hourly_space_velocity_h_inv",
    "time_on_stream_h",
    "methane_conversion_pct",
    "h2_yield_pct",
    "h2_selectivity_pct",
    "h2_co_ratio",
    "stability_duration_h",
    "conversion_drop_pct_points",
    "coke_amount_mg_gcat",
    "coke_amount_wt_pct",
]

CATALYST_CONTEXT_FIELDS = [
    "active_metal_primary",
    "active_metal_secondary",
    "active_metal_primary_loading_wt_pct",
    "support_primary",
    "promoter_1",
    "preparation_method",
]

DERIVED_FIELDS = [
    "derived_activity_score",
    "derived_stability_score",
    "derived_coking_resistance_score",
    "derived_overall_screening_score",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build freeze v0.1 candidate and manual-review task tables.")
    parser.add_argument("--review-pack", default="data/processed/pdf_fulltext_review_pack.csv")
    parser.add_argument("--stage5", default="data/processed/srm_extraction_auto_draft_stage5.csv")
    parser.add_argument("--metadata", default="data/processed/srm_metadata_extraction_draft.csv")
    parser.add_argument("--experimental", default="data/processed/srm_experimental_extraction_draft.csv")
    parser.add_argument("--review-guide", default="docs/pdf_fulltext_review_guide.md")
    parser.add_argument("--coverage-report", default="docs/pdf_fulltext_field_coverage_report.md")
    parser.add_argument("--freeze-candidates", default="data/processed/freeze_candidate_v0_1.csv")
    parser.add_argument("--freeze-excluded", default="data/processed/freeze_excluded_needs_review_v0_1.csv")
    parser.add_argument("--manual-tasks", default="data/processed/manual_review_tasks_v0_1.csv")
    parser.add_argument("--plan", default="docs/freeze_v0_1_plan.md")
    return parser.parse_args()


def read_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"Missing required input: {path}")
    return pd.read_csv(path, dtype=str, keep_default_na=False, encoding="utf-8-sig")


def read_text_optional(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="replace")


def clean(value: object) -> str:
    if value is None:
        return ""
    text = str(value)
    if text.lower() == "nan":
        return ""
    return " ".join(text.replace("\x00", " ").split())


def present(row: pd.Series, field: str) -> bool:
    return clean(row.get(field, "")) != ""


def present_any(row: pd.Series, fields: Iterable[str]) -> bool:
    return any(present(row, field) for field in fields)


def missing_value_fields(row: pd.Series, fields: Iterable[str]) -> List[str]:
    return [field for field in fields if not present(row, field)]


def source_text(row: pd.Series) -> str:
    parts = [
        row.get("source_excerpt_metadata", ""),
        row.get("source_excerpt_experimental", ""),
        row.get("evidence_summary", ""),
        row.get("key_source_excerpt", ""),
    ]
    path = clean(row.get("source_file_path", ""))
    if path:
        full_path = ROOT / path
        if full_path.exists() and full_path.is_file():
            parts.append(full_path.read_text(encoding="utf-8", errors="ignore")[:25000])
    return clean(" ".join(str(part) for part in parts))


def window_has(text: str, pattern_a: str, pattern_b: str, window: int = 140) -> bool:
    lowered = text.lower()
    for match in re.finditer(pattern_a, lowered, flags=re.IGNORECASE):
        left = max(0, match.start() - window)
        right = min(len(lowered), match.end() + window)
        if re.search(pattern_b, lowered[left:right], flags=re.IGNORECASE):
            return True
    return False


def has_reaction_temperature_evidence(row: pd.Series) -> bool:
    if present(row, "temperature_c"):
        return True
    text = source_text(row)
    if not text:
        return False
    temp_pattern = r"\b(?:[3-9]\d{2}|1[01]\d{2})\s*(?:°\s*c|◦\s*c|º\s*c|8c|c\b|k\b)"
    reaction_pattern = r"(?:steam reforming|methane reforming|reaction|reactor|catalytic|conversion|activity|tested|msr)"
    return window_has(text, temp_pattern, reaction_pattern) or window_has(text, reaction_pattern, temp_pattern)


def has_feed_ratio_evidence(row: pd.Series) -> bool:
    if present(row, "steam_to_carbon_ratio"):
        return True
    if present(row, "feed_ch4_vol_pct") and present(row, "feed_h2o_vol_pct"):
        return True
    text = source_text(row).lower()
    if not text:
        return False
    patterns = [
        r"\bs\s*/\s*c\s*(?:=|ratio|of|:)?\s*\d",
        r"steam\s*(?:to|-)\s*carbon\s*(?:ratio)?\s*(?:=|of|:)?\s*\d",
        r"h\s*2\s*o\s*/\s*ch\s*4\s*(?:=|ratio|of|:)?\s*\d",
        r"ch\s*4\s*:\s*h\s*2\s*o\s*(?:=|of|:)?\s*\d",
        r"h\s*2\s*o\s*:\s*ch\s*4\s*(?:=|of|:)?\s*\d",
    ]
    return any(re.search(pattern, text, flags=re.IGNORECASE) for pattern in patterns)


def has_label_candidate(row: pd.Series) -> bool:
    return present_any(row, LABEL_FIELDS)


def freeze_missing_required(row: pd.Series) -> List[str]:
    missing = missing_value_fields(row, REQUIRED_VALUE_FIELDS)
    if not has_reaction_temperature_evidence(row):
        missing.append("temperature_c_or_reaction_temperature_evidence")
    if not has_feed_ratio_evidence(row):
        missing.append("steam_to_carbon_ratio_or_feed_h2o_ch4_evidence")
    if not has_label_candidate(row):
        missing.append("methane_conversion_pct_or_h2_yield_pct")
    return missing


def confidence_is_low(row: pd.Series) -> bool:
    return clean(row.get("extraction_confidence_experimental", "")) in {"very_low", "low", ""}


def label_recommendation(row: pd.Series) -> str:
    has_conversion = present(row, "methane_conversion_pct")
    has_yield = present(row, "h2_yield_pct")
    if has_conversion and has_yield:
        return "primary_label_candidate=methane_conversion_pct; keep h2_yield_pct as secondary context only after confirming definitions."
    if has_conversion:
        return "primary_label_candidate=methane_conversion_pct; confirm definition, basis, and matching reaction condition."
    if has_yield:
        return "fallback_label_candidate=h2_yield_pct; use only if yield definition is explicit and conversion is unavailable."
    return "no_label_candidate; do not freeze until methane_conversion_pct or h2_yield_pct is manually confirmed."


def comparability_notes(row: pd.Series) -> str:
    pieces = []
    for field in [
        "temperature_c",
        "pressure_bar",
        "steam_to_carbon_ratio",
        "gas_hourly_space_velocity_h_inv",
        "weight_hourly_space_velocity_h_inv",
        "time_on_stream_h",
    ]:
        value = clean(row.get(field, ""))
        pieces.append(f"{field}={value or 'missing'}")
    pieces.append("Do not compare activity across different temperature/S-C/pressure/space-velocity/time-on-stream conditions unless stratified or normalized.")
    return "; ".join(pieces)


def freeze_blocking_issues(row: pd.Series, missing: List[str]) -> str:
    issues = list(missing)
    if confidence_is_low(row):
        issues.append("experimental_extraction_low_confidence_manual_confirmation_required")
    if any(present(row, field) for field in DERIVED_FIELDS):
        issues.append("derived_field_nonempty_must_be_cleared_before_freeze")
    if clean(row.get("manual_review_required", "")).lower() != "yes":
        issues.append("manual_review_required_flag_unexpected")
    if not present(row, "source_file_path"):
        issues.append("missing_source_file_path")
    return "; ".join(dict.fromkeys(issues))


def reviewer_must_check(row: pd.Series, missing: List[str]) -> str:
    fields = [
        "active_metal_primary",
        "support_primary",
        "active_metal_primary_loading_wt_pct",
        "preparation_method",
        "temperature_c",
        "pressure_bar",
        "steam_to_carbon_ratio",
        "gas_hourly_space_velocity_h_inv",
        "weight_hourly_space_velocity_h_inv",
        "time_on_stream_h",
        "methane_conversion_pct",
        "h2_yield_pct",
        "h2_selectivity_pct",
        "h2_co_ratio",
        "stability_duration_h",
        "conversion_drop_pct_points",
        "coke_amount_mg_gcat",
        "coke_amount_wt_pct",
    ]
    priority = []
    for field in fields:
        if field in {"temperature_c", "steam_to_carbon_ratio"} or present(row, field) or field in missing:
            priority.append(field)
    return "; ".join(dict.fromkeys(priority))


def source_excerpt_for_field(field: str, row: pd.Series, experimental_by_id: dict[str, pd.Series], metadata_by_id: dict[str, pd.Series]) -> str:
    paper_id = clean(row.get("paper_id", ""))
    candidates = []
    exp = experimental_by_id.get(paper_id)
    meta = metadata_by_id.get(paper_id)
    if exp is not None:
        candidates.append(exp.get(f"{field}_source_excerpt", ""))
    if meta is not None:
        candidates.append(meta.get(f"{field}_source_excerpt", ""))
    candidates.extend([row.get("evidence_summary", ""), row.get("key_source_excerpt", "")])
    for candidate in candidates:
        text = clean(candidate)
        if text:
            return text[:700]
    return ""


def task_priority(field: str, is_candidate: bool, row: pd.Series) -> str:
    if field in {"temperature_c", "steam_to_carbon_ratio"}:
        return "P0_freeze_blocker" if is_candidate else "P0_missing_for_freeze"
    if field == "methane_conversion_pct":
        if present(row, "methane_conversion_pct") or not present(row, "h2_yield_pct"):
            return "P0_freeze_blocker" if is_candidate else "P0_missing_for_freeze"
        return "P2_label_context"
    if field == "h2_yield_pct":
        if present(row, "h2_yield_pct") or not present(row, "methane_conversion_pct"):
            return "P0_freeze_blocker" if is_candidate else "P0_missing_for_freeze"
        return "P2_label_context"
    if field in {"gas_hourly_space_velocity_h_inv", "weight_hourly_space_velocity_h_inv", "pressure_bar", "time_on_stream_h"}:
        return "P1_condition_context"
    if field in {"h2_selectivity_pct", "h2_co_ratio", "stability_duration_h", "conversion_drop_pct_points"}:
        return "P2_label_context"
    return "P3_coking_or_optional_context"


def manual_action(field: str, row: pd.Series) -> str:
    value = clean(row.get(field, ""))
    if value:
        return "Confirm value, unit, definition, source table/figure, and matching reaction condition in the PDF."
    return "Look up the field in the PDF; keep blank if value/unit/definition is not explicit."


def add_freeze_columns(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for _, row in df.iterrows():
        missing = freeze_missing_required(row)
        issues = freeze_blocking_issues(row, missing)
        out = row.to_dict()
        out.update(
            {
                "freeze_candidate_status": "candidate_pending_manual_confirmation" if not missing else "excluded_needs_review",
                "missing_required_fields": "; ".join(missing),
                "condition_comparability_notes": comparability_notes(row),
                "label_candidate_recommendation": label_recommendation(row),
                "reviewer_must_check_fields": reviewer_must_check(row, missing),
                "freeze_blocking_issues": issues,
                "transfer_ready_after_manual_check": "yes" if not missing else "no",
            }
        )
        rows.append(out)
    return pd.DataFrame(rows)


def build_tasks(
    combined: pd.DataFrame,
    candidate_ids: set[str],
    experimental: pd.DataFrame,
    metadata: pd.DataFrame,
) -> pd.DataFrame:
    experimental_by_id = {clean(row.get("paper_id", "")): row for _, row in experimental.iterrows()}
    metadata_by_id = {clean(row.get("paper_id", "")): row for _, row in metadata.iterrows()}
    task_rows = []
    for _, row in combined.iterrows():
        paper_id = clean(row.get("paper_id", ""))
        is_candidate = paper_id in candidate_ids
        for field in MANUAL_CHECK_FIELDS:
            task_rows.append(
                {
                    "paper_id": paper_id,
                    "title": clean(row.get("title", "")),
                    "freeze_group": "freeze_candidate_v0_1" if is_candidate else "excluded_needs_review_v0_1",
                    "task_priority": task_priority(field, is_candidate, row),
                    "field_name": field,
                    "current_auto_value": clean(row.get(field, "")),
                    "auto_value_present": "yes" if present(row, field) else "no",
                    "source_excerpt": source_excerpt_for_field(field, row, experimental_by_id, metadata_by_id),
                    "manual_action": manual_action(field, row),
                    "reviewer_notes": "",
                    "source_file_path": clean(row.get("source_file_path", "")),
                }
            )
    priority_order = {
        "P0_freeze_blocker": 0,
        "P0_missing_for_freeze": 0,
        "P1_condition_context": 1,
        "P2_label_context": 2,
        "P3_coking_or_optional_context": 3,
    }
    tasks = pd.DataFrame(task_rows)
    tasks["_priority_order"] = tasks["task_priority"].map(priority_order).fillna(9)
    tasks["_group_order"] = tasks["freeze_group"].map({"freeze_candidate_v0_1": 0, "excluded_needs_review_v0_1": 1}).fillna(9)
    tasks = tasks.sort_values(["_group_order", "paper_id", "_priority_order", "field_name"]).drop(columns=["_priority_order", "_group_order"])
    return tasks


def most_common_blockers(excluded: pd.DataFrame) -> List[tuple[str, int]]:
    counts: dict[str, int] = {}
    for value in excluded.get("missing_required_fields", pd.Series(dtype=str)):
        for item in clean(value).split(";"):
            item = item.strip()
            if item:
                counts[item] = counts.get(item, 0) + 1
    return sorted(counts.items(), key=lambda item: (-item[1], item[0]))


def build_plan_doc(candidates: pd.DataFrame, excluded: pd.DataFrame, tasks: pd.DataFrame) -> str:
    blockers = most_common_blockers(excluded)
    lines: List[str] = []
    lines.append("# Freeze Dataset v0.1 Plan")
    lines.append("")
    lines.append("## 当前为什么还不能机器学习")
    lines.append("")
    lines.append("- 当前 stage5 输出仍是自动抽取草稿，所有实验字段都需要人工确认。")
    lines.append("- 只有 20 篇 PDF fulltext，样本量太小，且不同温度、S/C、压力、GHSV、time-on-stream 下的性能不可直接比较。")
    lines.append("- `methane_conversion_pct`、`h2_yield_pct`、选择性、稳定性和积碳字段的定义在不同论文中可能不同，直接混用会造成标签噪声。")
    lines.append("- `journal_impact_factor`、`review_priority`、`source_quality`、`manual_review_status`、`derived_*` 等字段存在文献来源偏差或数据泄漏风险，不能默认入模。")
    lines.append("")
    lines.append("## Freeze v0.1 最低纳入标准")
    lines.append("")
    lines.append("记录进入 `freeze_candidate_v0_1.csv` 必须至少满足：")
    lines.append("")
    lines.append("- `active_metal_primary` 非空。")
    lines.append("- `support_primary` 非空。")
    lines.append("- 有 `temperature_c`，或 PDF 证据中明确出现反应温度。")
    lines.append("- 有 `steam_to_carbon_ratio`，或 PDF 证据中明确出现 feed H2O/CH4、S/C、steam-to-carbon 信息。")
    lines.append("- 有 `methane_conversion_pct` 或 `h2_yield_pct` 作为标签候选。")
    lines.append("")
    lines.append("这些标准只表示“值得人工确认”，不表示已经冻结。")
    lines.append("")
    lines.append("## 本轮拆分结果")
    lines.append("")
    lines.append(f"- `freeze_candidate_v0_1.csv`：`{len(candidates)}` 条。")
    lines.append(f"- `freeze_excluded_needs_review_v0_1.csv`：`{len(excluded)}` 条。")
    if blockers:
        lines.append("- 最常见 blocking 字段：")
        for field, count in blockers:
            lines.append(f"- `{field}`：`{count}` 条。")
    lines.append("")
    lines.append("## 必须人工确认的字段")
    lines.append("")
    lines.append("- 催化剂：`active_metal_primary`、`active_metal_secondary`、`active_metal_primary_loading_wt_pct`、`support_primary`、`promoter_1`、`preparation_method`。")
    lines.append("- 工况：`temperature_c`、`pressure_bar`、`steam_to_carbon_ratio`、`gas_hourly_space_velocity_h_inv`、`weight_hourly_space_velocity_h_inv`、`time_on_stream_h`。")
    lines.append("- 性能：`methane_conversion_pct`、`h2_yield_pct`、`h2_selectivity_pct`、`h2_co_ratio`。")
    lines.append("- 稳定性和积碳：`stability_duration_h`、`conversion_drop_pct_points`、`coke_amount_mg_gcat`、`coke_amount_wt_pct`。")
    lines.append("")
    lines.append("## 第一版主标签建议")
    lines.append("")
    lines.append("- 第一版最建议使用 `methane_conversion_pct` 作为主标签候选。")
    lines.append("- 原因是它在当前草稿中比 `h2_yield_pct` 覆盖更好，且通常更直接对应 SRM 活性。")
    lines.append("- `h2_yield_pct` 可以作为 fallback 或辅助分析字段，但不建议和 `methane_conversion_pct` 在第一版起步时同时作为主标签。")
    lines.append("- `conversion_drop_pct_points` 必须结合 `stability_duration_h` 才能解释，后续可由脚本派生标准化退化速率，但原始提取阶段不新增人工派生字段。")
    lines.append("")
    lines.append("## 为什么需要工况分层")
    lines.append("")
    lines.append("- SRM 性能强烈依赖反应温度、S/C、压力、GHSV/WHSV、催化剂量和 time-on-stream。")
    lines.append("- 不同工况下的 conversion 或 yield 不可直接作为同一标签比较。")
    lines.append("- Freeze v0.1 应优先保留原始工况，后续探索时按相近工况分层，或只在条件足够接近的子集中比较。")
    lines.append("")
    lines.append("## 默认不能作为 ML 输入的字段")
    lines.append("")
    lines.append("- `journal_impact_factor`、`journal_quartile`、`journal_metrics_source`：只能用于文献筛选、偏差分析或敏感性分析。")
    lines.append("- `derived_*`：必须留空，不能人工填写，属于高泄漏风险字段。")
    lines.append("- `review_priority`、`source_quality_type`、`source_quality_score`、`manual_review_required`、`freeze_candidate_status`：只能用于流程控制和 QC，不能作为模型特征。")
    lines.append("- `source_excerpt_*`、`reviewer_notes`、`evidence_summary`：只能作为审计证据或备注。")
    lines.append("")
    lines.append("## 什么时候可以开始探索性分析")
    lines.append("")
    lines.append("- 建议至少完成 `20-30` 条人工确认记录后，再做探索性统计。")
    lines.append("- 探索性分析应限于字段覆盖率、催化剂族分布、工况分布、标签候选分布和缺失模式。")
    lines.append("- 如果本轮候选不足 20 条，应先补 PDF 或人工复核 excluded 记录。")
    lines.append("")
    lines.append("## 什么时候可以开始初步 baseline ML")
    lines.append("")
    lines.append("- 建议至少积累 `100-200` 条人工确认的 condition-performance 记录后，再尝试非常保守的 baseline。")
    lines.append("- 更稳妥的目标是 `300+` 条已确认且可分层的记录，尤其是 Ni-based、相近工况、同一主标签的子集。")
    lines.append("- baseline ML 前必须先冻结数据版本、定义标签、划分训练/验证策略，并明确数据泄漏控制。")
    lines.append("")
    lines.append("## 人工复核优先顺序")
    lines.append("")
    if len(candidates):
        for _, row in candidates.iterrows():
            lines.append(f"- `{clean(row.get('paper_id', ''))}`：优先确认 `{clean(row.get('reviewer_must_check_fields', ''))}`。")
    else:
        lines.append("- 当前没有记录满足 freeze v0.1 最低候选标准，应先补齐反应温度、S/C 和标签候选字段。")
    return "\n".join(lines) + "\n"


def main() -> int:
    args = parse_args()
    review = read_csv(ROOT / args.review_pack)
    _stage5 = read_csv(ROOT / args.stage5)
    metadata = read_csv(ROOT / args.metadata)
    experimental = read_csv(ROOT / args.experimental)
    _guide = read_text_optional(ROOT / args.review_guide)
    _coverage = read_text_optional(ROOT / args.coverage_report)

    combined = add_freeze_columns(review)
    is_candidate = combined["missing_required_fields"].map(clean).eq("")
    candidates = combined.loc[is_candidate].copy()
    excluded = combined.loc[~is_candidate].copy()

    output_candidate = ROOT / args.freeze_candidates
    output_excluded = ROOT / args.freeze_excluded
    output_tasks = ROOT / args.manual_tasks
    output_plan = ROOT / args.plan
    for path in [output_candidate, output_excluded, output_tasks, output_plan]:
        path.parent.mkdir(parents=True, exist_ok=True)

    candidates.to_csv(output_candidate, index=False, encoding="utf-8-sig")
    excluded.to_csv(output_excluded, index=False, encoding="utf-8-sig")

    tasks = build_tasks(combined, set(candidates["paper_id"].map(clean)), experimental, metadata)
    tasks.to_csv(output_tasks, index=False, encoding="utf-8-sig")
    output_plan.write_text(build_plan_doc(candidates, excluded, tasks), encoding="utf-8")

    print(f"Freeze candidates written: {output_candidate}")
    print(f"Freeze excluded written: {output_excluded}")
    print(f"Manual review tasks written: {output_tasks}")
    print(f"Freeze plan written: {output_plan}")
    print(f"Candidate rows: {len(candidates)}")
    print(f"Excluded rows: {len(excluded)}")
    print("Most common blockers:")
    for field, count in most_common_blockers(excluded):
        print(f"  {field}: {count}")
    if len(candidates):
        print("Candidate paper_ids:", ", ".join(candidates["paper_id"].map(clean)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
