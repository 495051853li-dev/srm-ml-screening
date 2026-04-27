"""Extract structured SRM fields from local full-text artifacts.

This script currently produces a review queue rather than claiming successful
scientific extraction from unverified PDFs or HTML.
"""

from __future__ import annotations

import argparse
import csv
from pathlib import Path


OUTPUT_COLUMNS = [
    "paper_id",
    "source_file",
    "extraction_status",
    "needs_manual_review",
    "notes",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Prepare a manual-review queue for SRM field extraction.")
    parser.add_argument("--input-dir", default="outputs/fulltext", help="Directory containing downloaded files.")
    parser.add_argument(
        "--output",
        default="data/processed/extraction_queue.csv",
        help="CSV path for the extraction queue.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    input_dir = Path(args.input_dir)
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    rows = []
    if input_dir.exists():
        for path in sorted(input_dir.iterdir()):
            if path.is_file():
                rows.append(
                    {
                        "paper_id": path.stem,
                        "source_file": str(path),
                        "extraction_status": "pending_manual_extraction",
                        "needs_manual_review": "yes",
                        "notes": "Automatic SRM field extraction is not enabled yet; review source content manually.",
                    }
                )

    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=OUTPUT_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)

    print(f"Queued files: {len(rows)}")
    print(f"Output CSV: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
