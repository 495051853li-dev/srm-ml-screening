"""Route manual review records and build deep review sheets for batch 1."""

from __future__ import annotations

import argparse
import csv
import re
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

from bs4 import BeautifulSoup


ROOT = Path(__file__).resolve().parent.parent

ROUTING_EXTRA_COLUMNS = [
    "routing_reason",
    "next_best_action",
    "minimum_fields_to_confirm",
    "recommended_source_strategy",
]

DEEP_REVIEW_FIELDS = [
    "active_metal_primary_loading_wt_pct",
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


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Route manual review records and build deep review sheets.")
    parser.add_argument(
        "--review-pack",
        default="data/processed/srm_extraction_review_pack.csv",
        help="Input manual review pack CSV.",
    )
    parser.add_argument(
        "--fulltext-fetch-log",
        default="data/processed/fulltext_fetch_log.csv",
        help="Fetch log CSV.",
    )
    parser.add_argument(
        "--ready-output",
        default="data/processed/review_ready_for_entry.csv",
        help="Output CSV for records ready for manual confirmation and entry.",
    )
    parser.add_argument(
        "--needs-output",
        default="data/processed/review_needs_more_source.csv",
        help="Output CSV for records needing more source evidence.",
    )
    parser.add_argument(
        "--entry-candidates-output",
        default="data/processed/batch1_entry_candidates.csv",
        help="Output CSV for records currently best suited for later manual transfer.",
    )
    parser.add_argument(
        "--guide-path",
        default="docs/manual_review_guide_batch1.md",
        help="Guide markdown path to update.",
    )
    return parser.parse_args()


def read_rows(path: Path) -> List[Dict[str, str]]:
    with path.open("r", newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def write_rows(path: Path, rows: List[Dict[str, str]], fieldnames: List[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows([{field: row.get(field, "") for field in fieldnames} for row in rows])


def normalize_text(value: str) -> str:
    value = value or ""
    value = re.sub(r"\s+", " ", value)
    return value.strip()


def source_strength(row: Dict[str, str]) -> str:
    excerpt = (row.get("source_excerpt") or "").strip().lower()
    confidence = row.get("source_excerpt_confidence", "")
    if excerpt == "redirecting" or len(excerpt) < 80:
        return "weak"
    if confidence == "high":
        return "strong"
    if confidence == "medium":
        return "medium"
    return "weak"


def classify_information_clarity(row: Dict[str, str]) -> Tuple[bool, bool, bool]:
    catalyst_score = sum(bool(row.get(key)) for key in [
        "active_metal_primary",
        "active_metal_primary_loading_wt_pct",
        "support_primary",
        "preparation_method",
    ])
    condition_score = sum(bool(row.get(key)) for key in [
        "temperature_c",
        "pressure_bar",
        "steam_to_carbon_ratio",
        "gas_hourly_space_velocity_h_inv",
        "weight_hourly_space_velocity_h_inv",
        "time_on_stream_h",
    ])
    performance_score = sum(bool(row.get(key)) for key in [
        "methane_conversion_pct",
        "h2_yield_pct",
        "h2_selectivity_pct",
        "co_selectivity_pct",
        "h2_co_ratio",
        "stability_duration_h",
        "coke_amount_mg_gcat",
        "coke_amount_wt_pct",
    ])
    return catalyst_score >= 2, condition_score >= 2, performance_score >= 1


def route_row(row: Dict[str, str]) -> Tuple[str, str, str, str]:
    strength = source_strength(row)
    catalyst_clear, condition_clear, performance_clear = classify_information_clarity(row)
    title = (row.get("title") or "").lower()
    srm_clear = ("steam reforming of methane" in title) or ("methane steam reforming" in title) or ("steam reforming" in title and "methane" in title)

    if srm_clear and strength in {"strong", "medium"} and sum([catalyst_clear, condition_clear, performance_clear]) >= 2:
        routing_reason = "source_evidence_usable_and_at_least_two_information_categories_are_clear"
        next_best_action = "优先人工确认关键字段后，准备转入正式人工提取表"
        minimum_fields_to_confirm = "active_metal_primary; support_primary; temperature_c; steam_to_carbon_ratio; methane_conversion_pct_or_h2_yield_pct"
        recommended_source_strategy = "先复核当前本地页面，再视需要补看 PDF 或出版商全文"
        return routing_reason, next_best_action, minimum_fields_to_confirm, recommended_source_strategy

    reasons = []
    if not srm_clear:
        reasons.append("topic_boundary_needs_confirmation")
    if strength == "weak":
        reasons.append("source_excerpt_evidence_too_weak_or_redirect_page")
    if not condition_clear:
        reasons.append("reaction_condition_fields_not_clear_enough")
    if not performance_clear:
        reasons.append("performance_fields_not_clear_enough")
    routing_reason = "; ".join(reasons) if reasons else "needs_additional_source_confirmation"
    next_best_action = "继续寻找 PDF、全文正文或更强证据页面，再补核关键条件和性能字段"
    minimum_fields_to_confirm = "temperature_c; steam_to_carbon_ratio; pressure_bar; methane_conversion_pct_or_h2_yield_pct; measured_value_basis"
    recommended_source_strategy = "优先 PDF 正文、出版商全文页、补充信息页；摘要页不足时不要转入正式表"
    return routing_reason, next_best_action, minimum_fields_to_confirm, recommended_source_strategy


def build_routed_rows(review_rows: List[Dict[str, str]]) -> Tuple[List[Dict[str, str]], List[Dict[str, str]]]:
    ready_rows: List[Dict[str, str]] = []
    needs_rows: List[Dict[str, str]] = []
    for row in review_rows:
        routed = dict(row)
        routing_reason, next_best_action, minimum_fields_to_confirm, recommended_source_strategy = route_row(routed)
        routed["routing_reason"] = routing_reason
        routed["next_best_action"] = next_best_action
        routed["minimum_fields_to_confirm"] = minimum_fields_to_confirm
        routed["recommended_source_strategy"] = recommended_source_strategy

        strength = source_strength(routed)
        catalyst_clear, condition_clear, performance_clear = classify_information_clarity(routed)
        title = (routed.get("title") or "").lower()
        srm_clear = ("steam reforming of methane" in title) or ("methane steam reforming" in title) or ("steam reforming" in title and "methane" in title)

        if srm_clear and strength in {"strong", "medium"} and sum([catalyst_clear, condition_clear, performance_clear]) >= 2:
            ready_rows.append(routed)
        else:
            needs_rows.append(routed)
    return ready_rows, needs_rows


def build_entry_candidates(ready_rows: List[Dict[str, str]], needs_rows: List[Dict[str, str]]) -> List[Dict[str, str]]:
    candidates: List[Dict[str, str]] = []
    source_rows = ready_rows if ready_rows else sorted(
        needs_rows,
        key=lambda r: (
            {"high": 0, "medium": 1, "low": 2}.get(r.get("review_priority", ""), 9),
            {"high": 0, "medium": 1, "low": 2}.get(r.get("source_excerpt_confidence", ""), 9),
            r.get("paper_id", ""),
        ),
    )[:2]

    for row in source_rows:
        candidate = dict(row)
        candidate["ready_for_manual_confirmation"] = "yes"
        if row in ready_rows:
            candidate["transfer_recommendation"] = "人工确认后可优先转入正式表"
            candidate["transfer_notes"] = "当前来源证据与信息类别已达到优先人工确认门槛"
        else:
            candidate["transfer_recommendation"] = "仅在补强来源后再考虑转入正式表"
            candidate["transfer_notes"] = "当前仅作为最接近正式录入门槛的候选，不应直接转入正式表"
        candidates.append(candidate)
    return candidates


def field_snippet(text: str, field_name: str, current_value: str) -> str:
    value = (current_value or "").strip()
    patterns = {
        "active_metal_primary_loading_wt_pct": [value, "wt%", "nickel", "ni"],
        "support_primary": [value, "support", "alumina", "ceria", "silica"],
        "preparation_method": [value, "impregnation", "co-precipitation", "wet impregnation", "prepared"],
        "temperature_c": [value, "temperature", "°c", " c "],
        "pressure_bar": [value, "pressure", "bar", "atm", "mpa", "kpa"],
        "steam_to_carbon_ratio": [value, "steam-to-carbon", "steam to carbon", "s/c"],
        "time_on_stream_h": [value, "time on stream", "tos", "stable for"],
        "methane_conversion_pct": [value, "methane conversion", "conversion"],
        "h2_yield_pct": [value, "hydrogen yield", "h2 yield", "yield"],
        "stability_duration_h": [value, "stability", "durability", "time on stream"],
        "coke_amount_mg_gcat": [value, "coke", "mg/g"],
        "coke_amount_wt_pct": [value, "coke", "wt.%", "wt%"],
    }
    search_terms = [term for term in patterns.get(field_name, [value]) if term]
    lowered = text.lower()
    for term in search_terms:
        idx = lowered.find(str(term).lower())
        if idx >= 0:
            start = max(0, idx - 140)
            end = min(len(text), idx + 260)
            return normalize_text(text[start:end])
    return normalize_text(text[:400])


def load_source_text(path: Path) -> str:
    if not path.exists():
        return ""
    raw = path.read_text(encoding="utf-8", errors="ignore")
    if path.suffix.lower() in {".html", ".htm"}:
        soup = BeautifulSoup(raw, "html.parser")
        return normalize_text(soup.get_text(" "))
    return normalize_text(raw)


def write_review_sheet(row: Dict[str, str], output_path: Path) -> None:
    source_path = ROOT / row.get("source_file_path", "")
    source_text = load_source_text(source_path)
    current_fields = [
        "catalyst_family",
        "active_metal_primary",
        "active_metal_secondary",
        "active_metal_primary_loading_wt_pct",
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
    missing_fields = [field for field in current_fields if not (row.get(field) or "").strip()]
    priority_five = [field.strip() for field in row.get("key_missing_fields", "").split(";") if field.strip()][:5]
    if len(priority_five) < 5:
        extra = [field for field in current_fields if field not in priority_five]
        priority_five.extend(extra[: 5 - len(priority_five)])

    lines: List[str] = []
    lines.append(f"# {row.get('paper_id','')} 深度复核包")
    lines.append("")
    lines.append("## 论文基本信息")
    lines.append("")
    lines.append(f"- 标题：{row.get('title','')}")
    lines.append(f"- 第一作者：{row.get('first_author','')}")
    lines.append(f"- 年份：{row.get('publication_year','')}")
    lines.append(f"- 期刊：{row.get('journal','')}")
    lines.append(f"- DOI：{row.get('doi','')}")
    lines.append(f"- 来源文件：`{row.get('source_file_path','')}`")
    lines.append(f"- 来源摘录置信度：`{row.get('source_excerpt_confidence','')}`")
    lines.append("")
    lines.append("## 当前自动抽取到的字段")
    lines.append("")
    for field in current_fields:
        if row.get(field):
            lines.append(f"- `{field}`: {row.get(field,'')}")
    lines.append("")
    lines.append("## 当前缺失字段")
    lines.append("")
    for field in missing_fields:
        lines.append(f"- `{field}`")
    lines.append("")
    lines.append("## 最优先核对的 5 个字段")
    lines.append("")
    for field in priority_five:
        lines.append(f"- `{field}`")
    lines.append("")
    lines.append("## 字段对应来源摘录")
    lines.append("")
    for field in priority_five:
        snippet = field_snippet(source_text, field, row.get(field, ""))
        lines.append(f"### `{field}`")
        lines.append("")
        lines.append(f"- 来源文件：`{row.get('source_file_path','')}`")
        lines.append(f"- 当前值：`{row.get(field,'')}`")
        lines.append(f"- 摘录：{snippet if snippet else '当前未从本地页面中定位到有力证据摘录'}")
        lines.append("")
    lines.append("## 字段定义提醒")
    lines.append("")
    lines.append("- `methane_conversion_pct`：确认是甲烷转化率，不要与产氢收率或选择性混淆。")
    lines.append("- `h2_yield_pct`：确认分母定义，部分文章按理论产氢量，有些按转化甲烷计。")
    lines.append("- `h2_selectivity_pct` 与 `co_selectivity_pct`：只在原文明确给出时填写，不要从文字印象推断。")
    lines.append("- `stability_duration_h` 与 `conversion_drop_pct_points`：必须基于明确稳定性测试或端点。")
    lines.append("- `active_metal_primary_loading_wt_pct`：区分 nominal / measured，不清楚时不要硬填。")
    lines.append("")
    lines.append("## 建议的 reviewer action")
    lines.append("")
    lines.append(f"- {row.get('reviewer_action','')}")
    lines.append("")
    lines.append("## 是否建议进入正式人工提取表")
    lines.append("")
    source_strength_value = source_strength(row)
    catalyst_clear, condition_clear, performance_clear = classify_information_clarity(row)
    if source_strength_value in {'strong','medium'} and catalyst_clear and condition_clear and performance_clear:
        lines.append("- 建议：`yes`，但仍需人工确认关键字段后再转入。")
    else:
        lines.append("- 建议：`not_yet`，当前证据不足以直接转入正式表。")
    lines.append("")
    lines.append("## 是否建议继续找 PDF / 全文")
    lines.append("")
    if source_strength_value == "weak" or not condition_clear or not performance_clear:
        lines.append("- 建议：`yes`。当前页面更像摘要页、跳转页或证据不足页面，建议继续寻找 PDF 或正文。")
    else:
        lines.append("- 建议：`optional`。可先人工核对当前页面，再决定是否继续找全文。")

    output_path.write_text("\n".join(lines), encoding="utf-8")


def update_manual_review_guide(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    marker = "## 建议的人工复核节奏"
    addition = """
## 复核后如何转入正式人工提取表

1. 先打开 `review_ready_for_entry.csv` 或 `batch1_entry_candidates.csv`，确认本条记录是否真的具备转入条件。
2. 必须人工确认后才能转入的字段：
- `active_metal_primary`
- `support_primary`
- `preparation_method`
- `temperature_c`
- `steam_to_carbon_ratio`
- 至少一个核心性能字段：`methane_conversion_pct` 或 `h2_yield_pct`
- `measured_value_basis`
3. 可以暂时留空的字段：
- `active_metal_secondary`
- `active_metal_secondary_loading_wt_pct`
- `pressure_bar`
- `time_on_stream_h`
- `stability_duration_h`
- `coke_amount_mg_gcat`
- `coke_amount_wt_pct`
- 其他原文未明确报告的扩展字段
4. 以下情况建议暂不纳入正式表：
- 当前来源只是跳转页、摘要页或二级页面，缺少可核对证据
- 反应条件和性能字段同时大面积缺失
- 主题边界不清，无法确认是否为第一批重点 SRM 文章
- 关键数值只能靠猜测或主观推断补齐
5. 转入时仍然遵守原始提取规则：
- 不写入任何 `derived_*` 字段
- 无法确认的值保持为空
- 每转入一小批后运行 validator

"""
    if "## 复核后如何转入正式人工提取表" in text:
        return
    if marker in text:
        text = text.replace(marker, addition + "\n" + marker)
    else:
        text = text + "\n" + addition
    path.write_text(text, encoding="utf-8")


def main() -> int:
    args = parse_args()
    review_rows = read_rows(Path(args.review_pack))
    _ = read_rows(Path(args.fulltext_fetch_log))

    ready_rows, needs_rows = build_routed_rows(review_rows)
    fieldnames = list(review_rows[0].keys()) + ROUTING_EXTRA_COLUMNS if review_rows else ROUTING_EXTRA_COLUMNS
    write_rows(Path(args.ready_output), ready_rows, fieldnames)
    write_rows(Path(args.needs_output), needs_rows, fieldnames)

    entry_candidates = build_entry_candidates(ready_rows, needs_rows)
    entry_fieldnames = list(entry_candidates[0].keys()) if entry_candidates else fieldnames + [
        "ready_for_manual_confirmation",
        "transfer_recommendation",
        "transfer_notes",
    ]
    write_rows(Path(args.entry_candidates_output), entry_candidates, entry_fieldnames)

    write_review_sheet(next(row for row in review_rows if row["paper_id"] == "paper_0078"), ROOT / "docs" / "paper_0078_review_sheet.md")
    write_review_sheet(next(row for row in review_rows if row["paper_id"] == "paper_0221"), ROOT / "docs" / "paper_0221_review_sheet.md")
    update_manual_review_guide(Path(args.guide_path))

    print(f"Ready for entry rows: {len(ready_rows)}")
    print(f"Needs more source rows: {len(needs_rows)}")
    print(f"Entry candidates rows: {len(entry_candidates)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
