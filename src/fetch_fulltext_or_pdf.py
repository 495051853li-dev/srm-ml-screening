"""Fetch full text links or PDFs for candidate papers.

This stage is intentionally conservative. It only attempts direct downloads
from URLs already present in the candidate table and does not fabricate content.
"""

from __future__ import annotations

import argparse
import csv
from pathlib import Path
from urllib.parse import urlparse

import requests


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Fetch PDFs or OA full text for candidate papers.")
    parser.add_argument("--input", default="data/processed/candidate_papers.csv", help="Candidate paper CSV path.")
    parser.add_argument("--output-dir", default="outputs/fulltext", help="Directory for downloaded files.")
    parser.add_argument("--timeout", type=int, default=60, help="HTTP timeout in seconds.")
    parser.add_argument("--limit", type=int, default=20, help="Maximum number of files to attempt.")
    return parser.parse_args()


def safe_name(value: str) -> str:
    return "".join(ch if ch.isalnum() or ch in {"-", "_", "."} else "_" for ch in value)


def infer_extension(url: str) -> str:
    path = urlparse(url).path.lower()
    if path.endswith(".pdf"):
        return ".pdf"
    if path.endswith(".html") or path.endswith(".htm"):
        return ".html"
    return ".bin"


def main() -> int:
    args = parse_args()
    input_path = Path(args.input)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    if not input_path.exists():
        print(f"ERROR: Input file not found: {input_path}")
        return 1

    with input_path.open("r", newline="", encoding="utf-8-sig") as handle:
        rows = list(csv.DictReader(handle))

    attempted = 0
    downloaded = 0
    session = requests.Session()
    session.headers.update({"User-Agent": "srm-ml-screening/0.1 (local literature pipeline)"})

    for row in rows:
        if attempted >= args.limit:
            break
        url = row.get("best_oa_url") or row.get("paper_url") or ""
        if not url.startswith("http"):
            continue
        attempted += 1
        suffix = infer_extension(url)
        filename = safe_name(row.get("paper_id", f"candidate_{attempted}")) + suffix
        destination = output_dir / filename
        try:
            response = session.get(url, timeout=args.timeout)
            response.raise_for_status()
            destination.write_bytes(response.content)
            downloaded += 1
        except requests.RequestException as exc:
            print(f"WARNING: failed to fetch {url}: {exc}")

    print(f"Attempted downloads: {attempted}")
    print(f"Downloaded files: {downloaded}")
    print(f"Output directory: {output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
