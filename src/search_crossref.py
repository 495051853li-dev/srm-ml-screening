"""Enrich candidate papers with Crossref metadata."""

from __future__ import annotations

import argparse
import csv
import time
from pathlib import Path
from typing import Dict, Iterable, List, Optional

import requests


CROSSREF_URL = "https://api.crossref.org/works"
OUTPUT_COLUMNS = [
    "source",
    "source_id",
    "input_title",
    "input_doi",
    "crossref_doi",
    "crossref_title",
    "crossref_journal",
    "crossref_published_year",
    "crossref_type",
    "crossref_score",
    "crossref_url",
    "crossref_is_referenced_by_count",
    "crossref_publisher",
    "crossref_language",
    "crossref_abstract",
    "crossref_matched_by",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Enrich candidate paper metadata with Crossref.")
    parser.add_argument(
        "--input",
        default="data/processed/openalex_candidates.csv",
        help="Input CSV, typically the OpenAlex candidate file.",
    )
    parser.add_argument(
        "--output",
        default="data/processed/crossref_enriched.csv",
        help="Output CSV path.",
    )
    parser.add_argument("--mailto", default="", help="Optional email for polite Crossref access.")
    parser.add_argument("--timeout", type=int, default=30, help="HTTP timeout in seconds.")
    parser.add_argument("--sleep-seconds", type=float, default=0.2, help="Delay between API requests.")
    return parser.parse_args()


def build_session(mailto: str) -> requests.Session:
    session = requests.Session()
    agent = "srm-ml-screening/0.1 (local literature pipeline)"
    if mailto:
        agent = f"{agent}; mailto:{mailto}"
    session.headers.update({"User-Agent": agent})
    return session


def read_rows(path: Path) -> List[Dict[str, str]]:
    with path.open("r", newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def normalize_doi(value: str) -> str:
    value = (value or "").strip()
    return value.replace("https://doi.org/", "").replace("http://doi.org/", "")


def find_crossref_match(session: requests.Session, row: Dict[str, str], timeout: int) -> Dict:
    doi = normalize_doi(row.get("doi", ""))
    if doi:
        response = session.get(f"{CROSSREF_URL}/{doi}", timeout=timeout)
        if response.status_code == 200:
            return {"message": response.json().get("message", {}), "matched_by": "doi"}
        if response.status_code not in {404, 422}:
            response.raise_for_status()

    params = {
        "query.bibliographic": row.get("title", ""),
        "rows": 1,
    }
    if row.get("publication_year"):
        params["filter"] = f"from-pub-date:{row['publication_year']},until-pub-date:{row['publication_year']}"

    response = session.get(CROSSREF_URL, params=params, timeout=timeout)
    response.raise_for_status()
    items = response.json().get("message", {}).get("items", [])
    if not items:
        return {"message": {}, "matched_by": "none"}
    return {"message": items[0], "matched_by": "title_year"}


def normalize_crossref(row: Dict[str, str], payload: Dict) -> Dict[str, str]:
    message = payload.get("message", {}) or {}
    title = ""
    titles = message.get("title") or []
    if titles:
        title = titles[0]

    journal = ""
    container = message.get("container-title") or []
    if container:
        journal = container[0]

    published_year = ""
    date_parts = (((message.get("published-print") or {}).get("date-parts")) or ((message.get("published-online") or {}).get("date-parts")) or [])
    if date_parts and date_parts[0]:
        published_year = str(date_parts[0][0])

    return {
        "source": "crossref",
        "source_id": message.get("DOI", "") or "",
        "input_title": row.get("title", "") or "",
        "input_doi": row.get("doi", "") or "",
        "crossref_doi": message.get("DOI", "") or "",
        "crossref_title": title,
        "crossref_journal": journal,
        "crossref_published_year": published_year,
        "crossref_type": message.get("type", "") or "",
        "crossref_score": str(message.get("score", "") or ""),
        "crossref_url": message.get("URL", "") or "",
        "crossref_is_referenced_by_count": str(message.get("is-referenced-by-count", "") or ""),
        "crossref_publisher": message.get("publisher", "") or "",
        "crossref_language": message.get("language", "") or "",
        "crossref_abstract": message.get("abstract", "") or "",
        "crossref_matched_by": payload.get("matched_by", "none"),
    }


def write_rows(path: Path, rows: Iterable[Dict[str, str]]) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=OUTPUT_COLUMNS)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)
            count += 1
    return count


def main() -> int:
    args = parse_args()
    input_path = Path(args.input)
    output_path = Path(args.output)

    if not input_path.exists():
        print(f"ERROR: Input file not found: {input_path}")
        return 1

    session = build_session(args.mailto)
    input_rows = read_rows(input_path)
    output_rows: List[Dict[str, str]] = []
    for row in input_rows:
        payload = find_crossref_match(session, row, timeout=args.timeout)
        output_rows.append(normalize_crossref(row, payload))
        time.sleep(args.sleep_seconds)

    count = write_rows(output_path, output_rows)
    print(f"Crossref input rows: {len(input_rows)}")
    print(f"Crossref output rows: {count}")
    print(f"Output CSV: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
