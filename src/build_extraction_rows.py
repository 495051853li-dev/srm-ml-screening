"""Build extraction rows from the review queue.

This keeps the pipeline honest by generating blank rows for later manual entry
rather than inventing catalyst or performance data.
"""

from __future__ import annotations

import argparse
import csv
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create blank extraction rows from the extraction queue.")
    parser.add_argument("--input", default="data/processed/extraction_queue.csv", help="Extraction queue CSV path.")
    parser.add_argument(
        "--output",
        default="data/processed/srm_literature_extraction_template_autobuild.csv",
        help="Output CSV path.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    input_path = Path(args.input)
    output_path = Path(args.output)

    if not input_path.exists():
        print(f"ERROR: Input file not found: {input_path}")
        return 1

    with input_path.open("r", newline="", encoding="utf-8-sig") as handle:
        queue_rows = list(csv.DictReader(handle))

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8") as handle:
        fieldnames = ["paper_id", "record_id", "title", "doi", "temperature_c", "methane_conversion_pct", "extraction_notes"]
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for index, row in enumerate(queue_rows, start=1):
            writer.writerow(
                {
                    "paper_id": row.get("paper_id", ""),
                    "record_id": f"pending_{index:04d}",
                    "title": "",
                    "doi": "",
                    "temperature_c": "",
                    "methane_conversion_pct": "",
                    "extraction_notes": "Blank row generated for later manual extraction. No values inferred automatically.",
                }
            )

    print(f"Input queue rows: {len(queue_rows)}")
    print(f"Output CSV: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
