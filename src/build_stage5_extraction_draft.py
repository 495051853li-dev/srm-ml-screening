from __future__ import annotations

import argparse
import csv
from pathlib import Path
from typing import Dict, List

from stage5_extraction_utils import read_rows


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build merged stage5 extraction draft.")
    parser.add_argument("--template", default="data/processed/srm_literature_extraction_template.csv")
    parser.add_argument("--metadata", default="data/processed/srm_metadata_extraction_draft.csv")
    parser.add_argument("--experimental", default="data/processed/srm_experimental_extraction_draft.csv")
    parser.add_argument("--output", default="data/processed/srm_extraction_auto_draft_stage5.csv")
    return parser.parse_args()


def template_columns(path: Path) -> List[str]:
    with path.open("r", encoding="utf-8-sig") as handle:
        header = handle.readline().strip()
    return [part.strip() for part in header.split(",") if part.strip()]


def build_map(rows: List[Dict[str, str]]) -> Dict[str, Dict[str, str]]:
    return {str(row.get("paper_id", "")).strip(): row for row in rows if str(row.get("paper_id", "")).strip()}


def main() -> int:
    args = parse_args()
    base_columns = template_columns(Path(args.template))
    metadata_rows = read_rows(Path(args.metadata))
    experimental_rows = read_rows(Path(args.experimental))
    metadata_map = build_map(metadata_rows)
    experimental_map = build_map(experimental_rows)
    paper_ids = sorted(set(metadata_map) | set(experimental_map))

    extra_columns = [
        "source_file_path",
        "source_excerpt_metadata",
        "source_excerpt_experimental",
        "extraction_confidence_metadata",
        "extraction_confidence_experimental",
        "manual_review_required",
    ]

    output_columns = base_columns + [column for column in extra_columns if column not in base_columns]
    output_rows: List[Dict[str, str]] = []

    for paper_id in paper_ids:
        row = {column: "" for column in output_columns}
        meta = metadata_map.get(paper_id, {})
        exp = experimental_map.get(paper_id, {})

        row["paper_id"] = paper_id
        for source in [meta, exp]:
            for key, value in source.items():
                if key in row and value not in {"", None}:
                    row[key] = value

        row["record_id"] = ""
        row["reference_type"] = "journal_article"
        row["condition_id"] = ""
        row["digitized_from_plot"] = row.get("digitized_from_plot", "") or "no"
        row["analyst_qc_status"] = "pending"
        row["manual_review_required"] = row.get("manual_review_required", "") or exp.get("manual_review_required", "yes") or "yes"
        row["derived_activity_score"] = ""
        row["derived_stability_score"] = ""
        row["derived_coking_resistance_score"] = ""
        row["derived_overall_screening_score"] = ""
        row["source_file_path"] = meta.get("source_file_path", "") or exp.get("source_file_path", "")
        row["source_excerpt_metadata"] = meta.get("source_excerpt_metadata", "")
        row["source_excerpt_experimental"] = exp.get("source_excerpt_experimental", "")
        row["extraction_confidence_metadata"] = meta.get("extraction_confidence_metadata", "")
        row["extraction_confidence_experimental"] = exp.get("extraction_confidence_experimental", "")

        output_rows.append(row)

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=output_columns)
        writer.writeheader()
        writer.writerows(output_rows)

    print(f"Stage5 merged draft rows: {len(output_rows)}")
    print(f"Output: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
