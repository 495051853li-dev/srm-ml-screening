from __future__ import annotations

import argparse
from pathlib import Path
from typing import Iterable, List

import pandas as pd


ROOT = Path(__file__).resolve().parent.parent

CORE_CATALYST_FIELDS = [
    "active_metal_primary",
    "active_metal_secondary",
    "active_metal_primary_loading_wt_pct",
    "support_primary",
    "promoter_1",
    "preparation_method",
]

CORE_CONDITION_FIELDS = [
    "temperature_c",
    "pressure_bar",
    "steam_to_carbon_ratio",
    "gas_hourly_space_velocity_h_inv",
    "weight_hourly_space_velocity_h_inv",
    "time_on_stream_h",
]

CORE_PERFORMANCE_FIELDS = [
    "methane_conversion_pct",
    "h2_yield_pct",
    "h2_selectivity_pct",
    "h2_co_ratio",
    "stability_duration_h",
    "conversion_drop_pct_points",
    "coke_amount_mg_gcat",
    "coke_amount_wt_pct",
]

METADATA_COVERAGE_FIELDS = [
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

EXPERIMENTAL_COVERAGE_FIELDS = [
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

FIELD_GROUPS = {
    "催化剂组成字段": CORE_CATALYST_FIELDS,
    "反应条件字段": CORE_CONDITION_FIELDS,
    "性能与稳定性字段": CORE_PERFORMANCE_FIELDS,
}

CONFIDENCE_RANK = {
    "very_low": 0,
    "low": 1,
    "low_to_medium": 2,
    "medium": 3,
    "medium_to_high": 4,
    "high": 5,
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build PDF fulltext manual review pack and reports.")
    parser.add_argument("--merged", default="data/processed/srm_extraction_auto_draft_stage5.csv")
    parser.add_argument("--metadata", default="data/processed/srm_metadata_extraction_draft.csv")
    parser.add_argument("--experimental", default="data/processed/srm_experimental_extraction_draft.csv")
    parser.add_argument("--ingest-log", default="data/processed/local_pdf_ingest_log.csv")
    parser.add_argument("--stage5-qc", default="docs/stage5_extraction_qc_report.md")
    parser.add_argument("--review-pack", default="data/processed/pdf_fulltext_review_pack.csv")
    parser.add_argument("--review-guide", default="docs/pdf_fulltext_review_guide.md")
    parser.add_argument("--coverage-report", default="docs/pdf_fulltext_field_coverage_report.md")
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
    return " ".join(text.strip().split())


def is_present(row: pd.Series, field: str) -> bool:
    return clean(row.get(field, "")) != ""


def present_fields(row: pd.Series, fields: Iterable[str]) -> List[str]:
    return [field for field in fields if is_present(row, field)]


def missing_fields(row: pd.Series, fields: Iterable[str]) -> List[str]:
    return [field for field in fields if not is_present(row, field)]


def confidence_value(value: str) -> int:
    return CONFIDENCE_RANK.get(clean(value), -1)


def truncate(text: str, max_len: int = 420) -> str:
    text = clean(text)
    if len(text) <= max_len:
        return text
    return text[: max_len - 3].rstrip() + "..."


def first_nonempty(values: Iterable[str]) -> str:
    for value in values:
        value = clean(value)
        if value:
            return value
    return ""


def evidence_for_field(row: pd.Series, metadata_row: pd.Series | None, experimental_row: pd.Series | None, field: str) -> str:
    candidates = []
    if metadata_row is not None:
        candidates.append(metadata_row.get(f"{field}_source_excerpt", ""))
    if experimental_row is not None:
        candidates.append(experimental_row.get(f"{field}_source_excerpt", ""))
    candidates.append(row.get(f"{field}_source_excerpt", ""))
    return first_nonempty(candidates)


def build_evidence_summary(row: pd.Series, metadata_row: pd.Series | None, experimental_row: pd.Series | None) -> str:
    parts = []
    for field in [
        "active_metal_primary",
        "active_metal_primary_loading_wt_pct",
        "support_primary",
        "preparation_method",
        "temperature_c",
        "steam_to_carbon_ratio",
        "gas_hourly_space_velocity_h_inv",
        "methane_conversion_pct",
        "stability_duration_h",
        "coke_amount_wt_pct",
    ]:
        value = clean(row.get(field, ""))
        excerpt = evidence_for_field(row, metadata_row, experimental_row, field)
        if value or excerpt:
            if value:
                parts.append(f"{field}={value}; excerpt={truncate(excerpt, 160)}")
            else:
                parts.append(f"{field}: value missing; excerpt={truncate(excerpt, 160)}")
    if not parts:
        return truncate(first_nonempty([row.get("source_excerpt_metadata", ""), row.get("source_excerpt_experimental", "")]), 800)
    return " | ".join(parts)


def build_key_source_excerpt(row: pd.Series, metadata_row: pd.Series | None, experimental_row: pd.Series | None) -> str:
    excerpts: List[str] = []
    for field in CORE_CATALYST_FIELDS + CORE_CONDITION_FIELDS + CORE_PERFORMANCE_FIELDS:
        excerpt = evidence_for_field(row, metadata_row, experimental_row, field)
        if excerpt and excerpt not in excerpts:
            excerpts.append(excerpt)
    if not excerpts:
        excerpts = [first_nonempty([row.get("source_excerpt_metadata", ""), row.get("source_excerpt_experimental", "")])]
    return truncate(" || ".join(excerpts), 1200)


def score_review_priority(row: pd.Series) -> tuple[str, str, str]:
    catalyst_present = len(present_fields(row, CORE_CATALYST_FIELDS))
    condition_present = len(present_fields(row, CORE_CONDITION_FIELDS))
    performance_present = len(present_fields(row, CORE_PERFORMANCE_FIELDS))
    metadata_conf = confidence_value(clean(row.get("extraction_confidence_metadata", "")))
    experimental_conf = confidence_value(clean(row.get("extraction_confidence_experimental", "")))

    has_primary_signal = is_present(row, "active_metal_primary") and is_present(row, "support_primary")
    has_some_condition = condition_present >= 2
    has_some_performance = performance_present >= 1

    if has_primary_signal and catalyst_present >= 4 and has_some_condition and has_some_performance and experimental_conf >= 1:
        return (
            "high",
            "yes",
            "优先人工核对 PDF 原文中的催化剂组成、反应条件、性能定义和单位；确认后可考虑转入正式人工提取表。",
        )
    if has_primary_signal and catalyst_present >= 3 and (has_some_condition or has_some_performance):
        return (
            "medium",
            "caution",
            "先核对缺失的核心工况或性能字段；若原文证据不足，暂留在复核池。",
        )
    if metadata_conf >= 2 and has_primary_signal:
        return (
            "medium_low",
            "caution",
            "适合作为催化剂信息复核对象，但实验性能证据不足，暂不建议直接转入正式表。",
        )
    return (
        "low",
        "no",
        "关键字段缺失较多或证据弱，先补充原文定位或人工查表后再判断。",
    )


def coverage(df: pd.DataFrame, fields: List[str]) -> List[tuple[str, int, float]]:
    total = len(df)
    rows = []
    for field in fields:
        count = int(df[field].map(clean).ne("").sum()) if field in df.columns else 0
        pct = count / total if total else 0.0
        rows.append((field, count, pct))
    return rows


def fmt_pct(value: float) -> str:
    return f"{value * 100:.1f}%"


def markdown_table(rows: List[List[str]], headers: List[str]) -> List[str]:
    lines = ["| " + " | ".join(headers) + " |", "| " + " | ".join(["---"] * len(headers)) + " |"]
    for row in rows:
        escaped = [clean(cell).replace("|", "\\|") for cell in row]
        lines.append("| " + " | ".join(escaped) + " |")
    return lines


def fields_to_check(row: pd.Series) -> str:
    missing_core = missing_fields(row, CORE_CATALYST_FIELDS + CORE_CONDITION_FIELDS + CORE_PERFORMANCE_FIELDS)
    priority_missing = [
        field
        for field in [
            "active_metal_primary_loading_wt_pct",
            "preparation_method",
            "temperature_c",
            "steam_to_carbon_ratio",
            "gas_hourly_space_velocity_h_inv",
            "methane_conversion_pct",
            "h2_yield_pct",
            "stability_duration_h",
            "coke_amount_wt_pct",
        ]
        if field in missing_core
    ]
    if priority_missing:
        return ", ".join(priority_missing[:5])
    present_risky = present_fields(
        row,
        [
            "temperature_c",
            "pressure_bar",
            "steam_to_carbon_ratio",
            "gas_hourly_space_velocity_h_inv",
            "methane_conversion_pct",
            "stability_duration_h",
        ],
    )
    return ", ".join(present_risky[:5]) if present_risky else "active_metal_primary, support_primary, preparation_method"


def build_review_pack(
    merged: pd.DataFrame,
    metadata: pd.DataFrame,
    experimental: pd.DataFrame,
    ingest: pd.DataFrame,
) -> pd.DataFrame:
    metadata_by_id = {clean(row.get("paper_id", "")): row for _, row in metadata.iterrows()}
    experimental_by_id = {clean(row.get("paper_id", "")): row for _, row in experimental.iterrows()}
    ingest_by_id = {clean(row.get("matched_paper_id", "")): row for _, row in ingest.iterrows()}

    review = merged.copy()
    added_rows = []
    derived_fields = [field for field in review.columns if field.startswith("derived_")]

    for _, row in review.iterrows():
        paper_id = clean(row.get("paper_id", ""))
        metadata_row = metadata_by_id.get(paper_id)
        experimental_row = experimental_by_id.get(paper_id)
        ingest_row = ingest_by_id.get(paper_id)

        core_present = present_fields(row, CORE_CATALYST_FIELDS)
        core_missing = missing_fields(row, CORE_CATALYST_FIELDS)
        exp_fields = CORE_CONDITION_FIELDS + CORE_PERFORMANCE_FIELDS
        exp_present = present_fields(row, exp_fields)
        exp_missing = missing_fields(row, exp_fields)
        priority, ready, action = score_review_priority(row)

        if any(clean(row.get(field, "")) for field in derived_fields):
            action = action + " 注意：检测到 derived_* 非空，应在转正式表前清空并追溯来源。"

        if ingest_row is not None and clean(ingest_row.get("parsed_text_path", "")):
            source_hint = f"PDF text: {clean(ingest_row.get('parsed_text_path', ''))}"
        else:
            source_hint = f"Source file: {clean(row.get('source_file_path', ''))}"

        added_rows.append(
            {
                "review_priority": priority,
                "core_fields_present": "; ".join(core_present),
                "missing_core_fields": "; ".join(core_missing),
                "experimental_fields_present": "; ".join(exp_present),
                "missing_experimental_fields": "; ".join(exp_missing),
                "likely_ready_for_manual_confirmation": ready,
                "reviewer_action": action,
                "reviewer_notes": "",
                "evidence_summary": build_evidence_summary(row, metadata_row, experimental_row),
                "key_source_excerpt": f"{source_hint} || {build_key_source_excerpt(row, metadata_row, experimental_row)}",
            }
        )

    added = pd.DataFrame(added_rows)
    return pd.concat([review.reset_index(drop=True), added], axis=1)


def build_review_guide(review: pd.DataFrame, stage5_qc_text: str) -> str:
    priority_order = {"high": 0, "medium": 1, "medium_low": 2, "low": 3}
    sorted_review = review.copy()
    sorted_review["_priority_order"] = sorted_review["review_priority"].map(priority_order).fillna(9)
    sorted_review["_present_count"] = sorted_review["core_fields_present"].map(lambda x: len([v for v in clean(x).split(";") if v.strip()])) + sorted_review[
        "experimental_fields_present"
    ].map(lambda x: len([v for v in clean(x).split(";") if v.strip()]))
    sorted_review = sorted_review.sort_values(["_priority_order", "_present_count", "paper_id"], ascending=[True, False, True])

    lines: List[str] = []
    lines.append("# PDF 全文人工复核指南")
    lines.append("")
    lines.append("## 复核目标")
    lines.append("")
    lines.append("- 本指南面向当前 20 篇 `pdf_fulltext` 的 stage5 自动抽取草稿。")
    lines.append("- 目标是确认催化剂组成、制备、反应条件、性能、稳定性和积碳字段是否可转入正式人工提取表。")
    lines.append("- 当前阶段不开始机器学习，不把 `manual_review_required` 改为 `no`，也不填写任何 `derived_*` 字段。")
    lines.append("")
    lines.append("## 建议优先复核顺序")
    lines.append("")
    rows = []
    for _, row in sorted_review.iterrows():
        rows.append(
            [
                clean(row.get("paper_id", "")),
                clean(row.get("review_priority", "")),
                clean(row.get("likely_ready_for_manual_confirmation", "")),
                truncate(clean(row.get("title", "")), 90),
                fields_to_check(row),
            ]
        )
    lines.extend(markdown_table(rows, ["paper_id", "优先级", "可否准备确认", "题名", "最优先核对字段"]))
    lines.append("")
    lines.append("## 每篇最优先核对的字段")
    lines.append("")
    for _, row in sorted_review.iterrows():
        lines.append(f"- `{clean(row.get('paper_id', ''))}`：{fields_to_check(row)}")
    lines.append("")
    lines.append("## 最容易定义混乱的字段")
    lines.append("")
    lines.append("- `methane_conversion_pct`：必须确认是 CH4 转化率，不能把 H2 yield、carbon conversion 或 equilibrium conversion 当作转化率。")
    lines.append("- `h2_yield_pct` 与 `h2_selectivity_pct`：必须确认作者定义，不能默认两者等价。")
    lines.append("- `temperature_c`：必须确认是反应床层温度，不是焙烧、还原、蒸汽发生器或表征温度。")
    lines.append("- `pressure_bar`：必须确认绝压/表压及单位换算；摘要中的 `1 atm`、`atmospheric pressure` 需要统一记录规则。")
    lines.append("- `steam_to_carbon_ratio`：必须确认是 feed S/C，不是 H2O/CH4 分压比、进料摩尔比的中间计算值或讨论条件。")
    lines.append("- `gas_hourly_space_velocity_h_inv` 与 `weight_hourly_space_velocity_h_inv`：必须确认 GHSV/WHSV 的定义、基准和单位，不能互换。")
    lines.append("- `stability_duration_h` 与 `conversion_drop_pct_points`：必须一起解释，不能单独用 conversion drop 表示稳定性。")
    lines.append("- `coke_amount_mg_gcat` 与 `coke_amount_wt_pct`：必须确认积碳测试方法、反应时长和归一化基准。")
    lines.append("")
    lines.append("## 必须看原文单位和定义后才能确认的字段")
    lines.append("")
    lines.append("- 反应条件：`temperature_c`、`pressure_bar`、`steam_to_carbon_ratio`、`gas_hourly_space_velocity_h_inv`、`weight_hourly_space_velocity_h_inv`、`time_on_stream_h`。")
    lines.append("- 性能标签候选：`methane_conversion_pct`、`h2_yield_pct`、`h2_selectivity_pct`、`h2_co_ratio`、`stability_duration_h`、`conversion_drop_pct_points`。")
    lines.append("- 抗积碳相关：`coking_test_method`、`coke_amount_mg_gcat`、`coke_amount_wt_pct`。")
    lines.append("- 组成相关：`active_metal_primary_loading_wt_pct`、`promoter_1_loading_wt_pct`，尤其要区分 nominal loading、ICP/EDS measured loading 和配方投料量。")
    lines.append("")
    lines.append("## 暂时不适合转入正式表的记录")
    lines.append("")
    not_ready = sorted_review[sorted_review["likely_ready_for_manual_confirmation"].isin(["no", "caution"])]
    if not_ready.empty:
        lines.append("- 当前没有完全排除的记录，但仍需逐篇人工确认。")
    else:
        for _, row in not_ready.iterrows():
            lines.append(
                f"- `{clean(row.get('paper_id', ''))}`：`{clean(row.get('likely_ready_for_manual_confirmation', ''))}`；"
                f"原因是缺失字段包括 `{truncate(clean(row.get('missing_core_fields', '')), 130)}` / `{truncate(clean(row.get('missing_experimental_fields', '')), 130)}`。"
            )
    lines.append("")
    lines.append("## 如何从 review pack 转入正式人工提取表")
    lines.append("")
    lines.append("1. 先打开 `data/processed/pdf_fulltext_review_pack.csv`，按 `review_priority` 从 high 到 low 复核。")
    lines.append("2. 对每篇论文，优先核对 `key_source_excerpt` 指向的 PDF 文本位置；证据不足时回到原 PDF 查看表格、图注和实验部分。")
    lines.append("3. 只有当催化剂组成、关键工况和至少一个明确性能标签候选被人工确认后，才手动转入正式人工提取表。")
    lines.append("4. 对无法确认单位、定义或数据来源的字段保持空白，并在正式表的 `extraction_notes` 或 `performance_definition_notes` 中说明。")
    lines.append("5. `derived_activity_score`、`derived_stability_score`、`derived_coking_resistance_score`、`derived_overall_screening_score` 必须保持为空，不能人工填写。")
    lines.append("6. 不同温度、S/C、压力和空速下的数据不要直接比较；正式入表时应保留原始工况，后续分析再分层或标准化。")
    lines.append("")
    if stage5_qc_text:
        lines.append("## Stage5 QC 引用说明")
        lines.append("")
        lines.append("- 已读取 `docs/stage5_extraction_qc_report.md` 作为背景；本复核包以最新 CSV 重新计算优先级和覆盖率。")
    return "\n".join(lines) + "\n"


def build_coverage_report(review: pd.DataFrame, metadata: pd.DataFrame, experimental: pd.DataFrame) -> str:
    lines: List[str] = []
    lines.append("# PDF 全文字段覆盖率报告")
    lines.append("")
    lines.append("## 数据范围")
    lines.append("")
    lines.append(f"- PDF fulltext stage5 合并草稿记录数：`{len(review)}`")
    lines.append(f"- metadata 抽取草稿记录数：`{len(metadata)}`")
    lines.append(f"- experimental 抽取草稿记录数：`{len(experimental)}`")
    lines.append("- 覆盖率仅表示字段非空，不代表已经人工确认正确。")
    lines.append("")
    lines.append("## Metadata 字段覆盖率")
    lines.append("")
    lines.extend(markdown_table([[field, str(count), fmt_pct(pct)] for field, count, pct in coverage(review, METADATA_COVERAGE_FIELDS)], ["字段", "非空数", "覆盖率"]))
    lines.append("")
    lines.append("## Experimental 字段覆盖率")
    lines.append("")
    lines.extend(markdown_table([[field, str(count), fmt_pct(pct)] for field, count, pct in coverage(review, EXPERIMENTAL_COVERAGE_FIELDS)], ["字段", "非空数", "覆盖率"]))
    lines.append("")
    for group_name, fields in FIELD_GROUPS.items():
        lines.append(f"## {group_name}覆盖情况")
        lines.append("")
        lines.extend(markdown_table([[field, str(count), fmt_pct(pct)] for field, count, pct in coverage(review, fields)], ["字段", "非空数", "覆盖率"]))
        lines.append("")

    all_focus_fields = CORE_CATALYST_FIELDS + CORE_CONDITION_FIELDS + CORE_PERFORMANCE_FIELDS
    missing_sorted = sorted(coverage(review, all_focus_fields), key=lambda item: (item[2], item[0]))
    lines.append("## 当前最缺失的字段")
    lines.append("")
    for field, count, pct in missing_sorted[:12]:
        lines.append(f"- `{field}`：非空 `{count}/{len(review)}`，覆盖率 `{fmt_pct(pct)}`")
    lines.append("")
    lines.append("## 是否达到探索性分析门槛")
    lines.append("")
    catalyst_basic_ready = int((review["active_metal_primary"].map(clean).ne("") & review["support_primary"].map(clean).ne("")).sum())
    has_condition = int(review[CORE_CONDITION_FIELDS].apply(lambda row: any(clean(v) for v in row), axis=1).sum())
    has_performance = int(review[CORE_PERFORMANCE_FIELDS].apply(lambda row: any(clean(v) for v in row), axis=1).sum())
    if catalyst_basic_ready >= 10 and has_condition >= 10 and has_performance >= 5:
        lines.append("- 结论：可以进入非常有限的人工复核后探索性统计，例如字段缺失模式、催化剂族分布、可用标签候选分布。")
        lines.append("- 限制：这些记录仍未完成单位和定义确认，不应直接比较不同工况下的性能。")
    else:
        lines.append("- 结论：尚未达到稳健探索性分析门槛，建议先完成人工复核和缺失字段补录。")
    lines.append("")
    lines.append("## 是否达到初步机器学习门槛")
    lines.append("")
    lines.append("- 结论：未达到。当前只有 20 篇 PDF fulltext，experimental 字段置信度整体偏低，且多数性能、选择性、积碳字段覆盖不足。")
    lines.append("- 风险：如果直接建模，模型很可能学习到文献来源、测试条件或抽取噪声，而不是催化剂本征规律，存在明显数据泄漏和工况混杂风险。")
    lines.append("- 建议：先把 review pack 中 high/medium 记录人工确认，再扩充 PDF fulltext 数量，并建立按温度、S/C、压力、GHSV 分层的分析策略。")
    return "\n".join(lines) + "\n"


def main() -> int:
    args = parse_args()
    merged = read_csv(ROOT / args.merged)
    metadata = read_csv(ROOT / args.metadata)
    experimental = read_csv(ROOT / args.experimental)
    ingest = read_csv(ROOT / args.ingest_log)
    stage5_qc_text = read_text_optional(ROOT / args.stage5_qc)

    review = build_review_pack(merged, metadata, experimental, ingest)

    review_pack_path = ROOT / args.review_pack
    review_pack_path.parent.mkdir(parents=True, exist_ok=True)
    review.to_csv(review_pack_path, index=False, encoding="utf-8-sig")

    review_guide_path = ROOT / args.review_guide
    review_guide_path.parent.mkdir(parents=True, exist_ok=True)
    review_guide_path.write_text(build_review_guide(review, stage5_qc_text), encoding="utf-8")

    coverage_report_path = ROOT / args.coverage_report
    coverage_report_path.parent.mkdir(parents=True, exist_ok=True)
    coverage_report_path.write_text(build_coverage_report(review, metadata, experimental), encoding="utf-8")

    print(f"Review pack written: {review_pack_path}")
    print(f"Review guide written: {review_guide_path}")
    print(f"Coverage report written: {coverage_report_path}")
    print(f"Rows: {len(review)}")
    print("Review priority counts:")
    for key, value in review["review_priority"].value_counts().items():
        print(f"  {key}: {value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
