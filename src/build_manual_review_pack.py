"""Build a manual review pack for the first batch of SRM extraction drafts."""

from __future__ import annotations

import argparse
import csv
import re
from pathlib import Path
from typing import Dict, List, Tuple

from bs4 import BeautifulSoup


ROOT = Path(__file__).resolve().parent.parent


REVIEW_EXTRA_COLUMNS = [
    "review_priority",
    "key_missing_fields",
    "likely_needs_manual_lookup",
    "reviewer_action",
    "reviewer_notes",
    "source_file_path",
    "source_excerpt",
    "source_excerpt_confidence",
]

KEY_FIELDS = [
    "active_metal_primary",
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
    parser = argparse.ArgumentParser(description="Build manual review pack and guide for batch 1.")
    parser.add_argument(
        "--draft",
        default="data/processed/srm_extraction_auto_draft.csv",
        help="Auto extraction draft CSV.",
    )
    parser.add_argument(
        "--fetch-log",
        default="data/processed/fulltext_fetch_log.csv",
        help="Fetch log CSV.",
    )
    parser.add_argument(
        "--screening-report",
        default="docs/first_batch_screening_report.md",
        help="Screening report path.",
    )
    parser.add_argument(
        "--extraction-summary",
        default="docs/auto_extraction_summary.md",
        help="Auto extraction summary path.",
    )
    parser.add_argument(
        "--review-pack-output",
        default="data/processed/srm_extraction_review_pack.csv",
        help="Output review pack CSV.",
    )
    parser.add_argument(
        "--guide-output",
        default="docs/manual_review_guide_batch1.md",
        help="Output manual review guide markdown.",
    )
    return parser.parse_args()


def read_rows(path: Path) -> List[Dict[str, str]]:
    with path.open("r", newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def normalize_text(value: str) -> str:
    value = value or ""
    value = re.sub(r"\s+", " ", value)
    return value.strip()


def load_source_excerpt(path: Path, limit: int = 700) -> Tuple[str, str]:
    if not path.exists():
        return "", "low"

    text = path.read_text(encoding="utf-8", errors="ignore")
    if path.suffix.lower() in {".html", ".htm"}:
        soup = BeautifulSoup(text, "html.parser")
        content = normalize_text(soup.get_text(" "))
    else:
        content = normalize_text(text)

    excerpt = content[:limit]
    if len(content) >= 4000:
        confidence = "high"
    elif len(content) >= 1200:
        confidence = "medium"
    else:
        confidence = "low"
    return excerpt, confidence


def determine_missing_fields(row: Dict[str, str]) -> List[str]:
    return [field for field in KEY_FIELDS if not (row.get(field) or "").strip()]


def determine_review_priority(row: Dict[str, str], missing_fields: List[str]) -> str:
    confidence = row.get("extraction_confidence", "")
    if confidence == "low_to_medium":
        return "high"
    if len(missing_fields) <= 7:
        return "high"
    if len(missing_fields) <= 10:
        return "medium"
    return "medium"


def determine_reviewer_action(row: Dict[str, str], missing_fields: List[str]) -> str:
    missing_set = set(missing_fields)
    if {"temperature_c", "steam_to_carbon_ratio", "methane_conversion_pct", "h2_yield_pct"} & missing_set:
        return "优先核对反应条件与核心性能字段，必要时继续向论文全文或 PDF 深入查找"
    if {"active_metal_primary_loading_wt_pct", "support_primary", "preparation_method"} & missing_set:
        return "优先核对催化剂组成与制备字段，并确认负载量口径"
    return "先核对已自动填入字段，再补录剩余关键缺失字段"


def build_review_pack_rows(draft_rows: List[Dict[str, str]], fetch_rows: List[Dict[str, str]]) -> List[Dict[str, str]]:
    fetch_map = {row["paper_id"]: row for row in fetch_rows}
    review_rows: List[Dict[str, str]] = []

    for draft_row in draft_rows:
        row = dict(draft_row)
        fetch_row = fetch_map.get(row.get("paper_id", ""), {})
        source_path = ROOT / fetch_row.get("local_path", "")
        excerpt, excerpt_confidence = load_source_excerpt(source_path)
        missing_fields = determine_missing_fields(row)
        row["review_priority"] = determine_review_priority(row, missing_fields)
        row["key_missing_fields"] = "; ".join(missing_fields[:8])
        row["likely_needs_manual_lookup"] = "yes" if len(missing_fields) >= 6 else "no"
        row["reviewer_action"] = determine_reviewer_action(row, missing_fields)
        row["reviewer_notes"] = ""
        row["source_file_path"] = fetch_row.get("local_path", "")
        row["source_excerpt"] = excerpt
        row["source_excerpt_confidence"] = excerpt_confidence
        review_rows.append(row)

    review_rows.sort(
        key=lambda r: (
            {"high": 0, "medium": 1, "low": 2}.get(r.get("review_priority", ""), 9),
            {"low_to_medium": 0, "medium": 1, "low": 2}.get(r.get("extraction_confidence", ""), 9),
            r.get("publication_year", ""),
        )
    )
    return review_rows


def top_five_fields_to_check(row: Dict[str, str]) -> List[str]:
    priority_order = [
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
    missing = [field for field in priority_order if not (row.get(field) or "").strip()]
    existing = [field for field in priority_order if (row.get(field) or "").strip()]
    result = missing[:5]
    if len(result) < 5:
        result.extend(existing[: 5 - len(result)])
    return result[:5]


def write_csv(path: Path, rows: List[Dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(rows[0].keys()) if rows else []
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def write_guide(
    path: Path,
    review_rows: List[Dict[str, str]],
    screening_report_path: Path,
    extraction_summary_path: Path,
) -> None:
    lines: List[str] = []
    lines.append("# 第一批人工复核指南")
    lines.append("")
    lines.append("本指南用于配合 `data/processed/srm_extraction_review_pack.csv` 对当前 6 篇自动抽取草稿进行逐篇人工复核。")
    lines.append("")
    lines.append("参考来源：")
    lines.append("")
    lines.append(f"- `{screening_report_path}`")
    lines.append(f"- `{extraction_summary_path}`")
    lines.append("")
    lines.append("## 复核顺序")
    lines.append("")
    lines.append("建议优先按以下顺序复核：")
    lines.append("")
    for index, row in enumerate(review_rows, start=1):
        lines.append(
            f"{index}. `{row.get('paper_id','')}` - {row.get('title','')}。优先级：`{row.get('review_priority','')}`，自动抽取置信度：`{row.get('extraction_confidence','')}`。"
        )
    lines.append("")
    lines.append("排序依据：")
    lines.append("")
    lines.append("- 优先处理 `review_priority = high` 的记录")
    lines.append("- 在同优先级内，优先处理自动抽取置信度相对更高的记录")
    lines.append("- 这样可以先把最有可能快速转成正式人工提取结果的文献处理掉")
    lines.append("")
    lines.append("## 每篇最优先核对的 5 个字段")
    lines.append("")
    for row in review_rows:
        fields = top_five_fields_to_check(row)
        lines.append(f"### {row.get('paper_id','')} - {row.get('title','')}")
        lines.append("")
        for field in fields:
            lines.append(f"- `{field}`")
        lines.append("")
    lines.append("## 最容易定义混乱的字段")
    lines.append("")
    lines.append("- `active_metal_primary_loading_wt_pct`：要区分主金属负载、总负载和 nominal / measured basis")
    lines.append("- `steam_to_carbon_ratio`：需确认是否为真正的 S/C，而不是由进料体积分数间接推断")
    lines.append("- `pressure_bar`：要注意原文可能使用 atm、kPa 或 MPa")
    lines.append("- `methane_conversion_pct` 与 `h2_yield_pct`：要确认是瞬时值、稳态值、峰值还是平均值")
    lines.append("- `stability_duration_h` 与 `conversion_drop_pct_points`：必须确认是否来自明确稳定性测试，而不是摘要性描述")
    lines.append("- `coke_amount_mg_gcat` 与 `coke_amount_wt_pct`：不要混用不同归一化口径")
    lines.append("- `preparation_method`：摘要里经常只给部分制备信息，必要时需继续追全文")
    lines.append("")
    lines.append("## 如何把复核后的结果转入正式人工提取表")
    lines.append("")
    lines.append("1. 以 `srm_extraction_review_pack.csv` 作为复核底稿，不要直接把自动草稿当作正式数据。")
    lines.append("2. 打开 `source_file_path` 对应的本地页面，结合 `source_excerpt` 快速定位信息。")
    lines.append("3. 只把已经人工确认的字段转写到正式人工提取表 `data/processed/srm_literature_extraction_template.csv`。")
    lines.append("4. 无法确认的字段继续留空，不要猜测填写。")
    lines.append("5. `derived_*` 字段保持为空。")
    lines.append("6. 每完成一小批转写后，运行 validator：")
    lines.append("")
    lines.append("```powershell")
    lines.append("python src/validate_extraction_dataset.py --input data/processed/srm_literature_extraction_template.csv")
    lines.append("```")
    lines.append("")
    lines.append("## 建议的人工复核节奏")
    lines.append("")
    lines.append("- 先完成前 3 篇高优先级文献")
    lines.append("- 再检查一次字段缺失模式是否一致")
    lines.append("- 如果发现某类字段持续无法从摘要页获得，就把这类字段统一标记为“需要进一步全文查找”")
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    args = parse_args()
    draft_rows = read_rows(Path(args.draft))
    fetch_rows = read_rows(Path(args.fetch_log))

    review_rows = build_review_pack_rows(draft_rows, fetch_rows)
    if review_rows:
        write_csv(Path(args.review_pack_output), review_rows)
    else:
        Path(args.review_pack_output).write_text("", encoding="utf-8")

    write_guide(
        Path(args.guide_output),
        review_rows,
        Path(args.screening_report),
        Path(args.extraction_summary),
    )

    print(f"Review pack rows: {len(review_rows)}")
    print(f"Review pack: {args.review_pack_output}")
    print(f"Guide: {args.guide_output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
