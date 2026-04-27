"""Search SRM-related papers from OpenAlex and save candidate metadata."""

from __future__ import annotations

import argparse
import csv
import json
import time
from pathlib import Path
from typing import Dict, Iterable, Iterator, List, Optional

import requests


OPENALEX_URL = "https://api.openalex.org/works"
DEFAULT_COLUMNS = [
    "source",
    "source_id",
    "openalex_id",
    "doi",
    "title",
    "publication_year",
    "journal",
    "authors",
    "paper_url",
    "best_oa_url",
    "is_oa",
    "cited_by_count",
    "abstract",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Search OpenAlex for SRM literature candidates.")
    parser.add_argument("--query", required=True, help="Free-text query for OpenAlex full-text search.")
    parser.add_argument("--max-results", type=int, default=200, help="Maximum number of records to fetch.")
    parser.add_argument("--per-page", type=int, default=50, help="Page size for OpenAlex API.")
    parser.add_argument(
        "--output",
        default="data/processed/openalex_candidates.csv",
        help="Path to the output CSV.",
    )
    parser.add_argument(
        "--raw-output",
        default="outputs/openalex_results.jsonl",
        help="Optional JSONL file storing raw OpenAlex responses.",
    )
    parser.add_argument("--mailto", default="", help="Optional email for polite pool access.")
    parser.add_argument("--timeout", type=int, default=30, help="HTTP timeout in seconds.")
    parser.add_argument("--sleep-seconds", type=float, default=0.2, help="Delay between API requests.")
    return parser.parse_args()


def build_session(mailto: str) -> requests.Session:
    session = requests.Session()
    headers = {"User-Agent": "srm-ml-screening/0.1 (local literature pipeline)"}
    if mailto:
        headers["From"] = mailto
    session.headers.update(headers)
    return session


def decode_abstract(inverted_index: Optional[Dict[str, List[int]]]) -> str:
    if not inverted_index:
        return ""

    max_position = max((position for positions in inverted_index.values() for position in positions), default=-1)
    if max_position < 0:
        return ""

    words = [""] * (max_position + 1)
    for token, positions in inverted_index.items():
        for position in positions:
            if 0 <= position < len(words):
                words[position] = token
    return " ".join(word for word in words if word)


def iter_works(
    session: requests.Session,
    query: str,
    max_results: int,
    per_page: int,
    timeout: int,
    sleep_seconds: float,
    mailto: str,
) -> Iterator[Dict]:
    cursor = "*"
    fetched = 0

    while fetched < max_results:
        params = {
            "search": query,
            "per-page": min(per_page, max_results - fetched),
            "cursor": cursor,
        }
        if mailto:
            params["mailto"] = mailto

        response = session.get(OPENALEX_URL, params=params, timeout=timeout)
        response.raise_for_status()
        payload = response.json()

        results = payload.get("results", [])
        if not results:
            break

        for item in results:
            yield item
            fetched += 1
            if fetched >= max_results:
                break

        cursor = payload.get("meta", {}).get("next_cursor")
        if not cursor:
            break
        time.sleep(sleep_seconds)


def normalize_work(work: Dict) -> Dict[str, str]:
    primary_location = work.get("primary_location") or {}
    source = primary_location.get("source") or {}
    authorships = work.get("authorships") or []
    authors = []
    for authorship in authorships:
        author_name = (authorship.get("author") or {}).get("display_name")
        if author_name:
            authors.append(author_name)

    doi = (work.get("doi") or "").replace("https://doi.org/", "").strip()
    return {
        "source": "openalex",
        "source_id": work.get("id", ""),
        "openalex_id": work.get("id", ""),
        "doi": doi,
        "title": work.get("display_name", "") or "",
        "publication_year": str(work.get("publication_year", "") or ""),
        "journal": source.get("display_name", "") or "",
        "authors": "; ".join(authors),
        "paper_url": primary_location.get("landing_page_url", "") or work.get("id", ""),
        "best_oa_url": primary_location.get("pdf_url", "") or "",
        "is_oa": str(bool(work.get("open_access", {}).get("is_oa", False))).lower(),
        "cited_by_count": str(work.get("cited_by_count", "") or ""),
        "abstract": decode_abstract(work.get("abstract_inverted_index")),
    }


def ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def write_csv(path: Path, rows: Iterable[Dict[str, str]]) -> int:
    ensure_parent(path)
    count = 0
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=DEFAULT_COLUMNS)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)
            count += 1
    return count


def write_jsonl(path: Path, works: Iterable[Dict]) -> int:
    ensure_parent(path)
    count = 0
    with path.open("w", encoding="utf-8") as handle:
        for work in works:
            handle.write(json.dumps(work, ensure_ascii=False) + "\n")
            count += 1
    return count


def main() -> int:
    args = parse_args()
    output_path = Path(args.output)
    raw_output_path = Path(args.raw_output) if args.raw_output else None

    session = build_session(args.mailto)
    works = list(
        iter_works(
            session=session,
            query=args.query,
            max_results=args.max_results,
            per_page=args.per_page,
            timeout=args.timeout,
            sleep_seconds=args.sleep_seconds,
            mailto=args.mailto,
        )
    )
    rows = [normalize_work(work) for work in works]
    count = write_csv(output_path, rows)
    if raw_output_path is not None:
        write_jsonl(raw_output_path, works)

    print(f"OpenAlex query: {args.query}")
    print(f"Fetched works: {count}")
    print(f"Output CSV: {output_path}")
    if raw_output_path is not None:
        print(f"Raw JSONL: {raw_output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
