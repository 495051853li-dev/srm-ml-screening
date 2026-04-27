"""Merge OpenAlex and Crossref candidate records into a deduplicated CSV."""

from __future__ import annotations

import argparse
import csv
import re
from pathlib import Path
from typing import Dict, Iterable, List, Tuple


OUTPUT_COLUMNS = [
    "paper_id",
    "merge_key",
    "source_priority",
    "openalex_id",
    "crossref_doi",
    "doi",
    "title",
    "publication_year",
    "journal",
    "authors",
    "paper_url",
    "best_oa_url",
    "is_oa",
    "cited_by_count",
    "crossref_type",
    "crossref_score",
    "crossref_url",
    "crossref_is_referenced_by_count",
    "crossref_publisher",
    "crossref_language",
    "needs_manual_review",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Merge OpenAlex and Crossref results into candidate_papers.csv.")
    parser.add_argument("--openalex", default="data/processed/openalex_candidates.csv", help="OpenAlex CSV path.")
    parser.add_argument("--crossref", default="data/processed/crossref_enriched.csv", help="Crossref CSV path.")
    parser.add_argument(
        "--output",
        default="data/processed/candidate_papers.csv",
        help="Merged candidate CSV path.",
    )
    return parser.parse_args()


def read_rows(path: Path) -> List[Dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def normalize_text(value: str) -> str:
    value = (value or "").lower().strip()
    value = re.sub(r"\s+", " ", value)
    value = re.sub(r"[^a-z0-9 ]+", "", value)
    return value


def normalize_doi(value: str) -> str:
    return (value or "").strip().replace("https://doi.org/", "").replace("http://doi.org/", "").lower()


def build_merge_key(openalex_row: Dict[str, str], crossref_row: Dict[str, str]) -> str:
    doi = normalize_doi(crossref_row.get("crossref_doi") or openalex_row.get("doi") or "")
    if doi:
        return f"doi:{doi}"

    title = normalize_text(crossref_row.get("crossref_title") or openalex_row.get("title") or "")
    year = (crossref_row.get("crossref_published_year") or openalex_row.get("publication_year") or "").strip()
    return f"title_year:{title}|{year}"


def merge_rows(openalex_rows: List[Dict[str, str]], crossref_rows: List[Dict[str, str]]) -> List[Dict[str, str]]:
    crossref_by_title_key: Dict[Tuple[str, str], Dict[str, str]] = {}
    crossref_by_doi: Dict[str, Dict[str, str]] = {}

    for row in crossref_rows:
        doi = normalize_doi(row.get("input_doi") or row.get("crossref_doi") or "")
        if doi:
            crossref_by_doi[doi] = row

        title_key = normalize_text(row.get("input_title") or "")
        year_key = (row.get("crossref_published_year") or "").strip()
        crossref_by_title_key[(title_key, year_key)] = row

    merged: Dict[str, Dict[str, str]] = {}

    for index, openalex_row in enumerate(openalex_rows, start=1):
        doi = normalize_doi(openalex_row.get("doi", ""))
        title_key = normalize_text(openalex_row.get("title", ""))
        year_key = (openalex_row.get("publication_year") or "").strip()
        crossref_row = crossref_by_doi.get(doi) or crossref_by_title_key.get((title_key, year_key)) or {}

        merge_key = build_merge_key(openalex_row, crossref_row)
        row = {
            "paper_id": f"paper_{index:04d}",
            "merge_key": merge_key,
            "source_priority": "openalex+crossref" if crossref_row else "openalex_only",
            "openalex_id": openalex_row.get("openalex_id", "") or openalex_row.get("source_id", ""),
            "crossref_doi": crossref_row.get("crossref_doi", "") or "",
            "doi": normalize_doi(crossref_row.get("crossref_doi") or openalex_row.get("doi") or ""),
            "title": crossref_row.get("crossref_title") or openalex_row.get("title", "") or "",
            "publication_year": crossref_row.get("crossref_published_year") or openalex_row.get("publication_year", "") or "",
            "journal": crossref_row.get("crossref_journal") or openalex_row.get("journal", "") or "",
            "authors": openalex_row.get("authors", "") or "",
            "paper_url": openalex_row.get("paper_url", "") or crossref_row.get("crossref_url", ""),
            "best_oa_url": openalex_row.get("best_oa_url", "") or "",
            "is_oa": openalex_row.get("is_oa", "") or "",
            "cited_by_count": openalex_row.get("cited_by_count", "") or "",
            "crossref_type": crossref_row.get("crossref_type", "") or "",
            "crossref_score": crossref_row.get("crossref_score", "") or "",
            "crossref_url": crossref_row.get("crossref_url", "") or "",
            "crossref_is_referenced_by_count": crossref_row.get("crossref_is_referenced_by_count", "") or "",
            "crossref_publisher": crossref_row.get("crossref_publisher", "") or "",
            "crossref_language": crossref_row.get("crossref_language", "") or "",
            "needs_manual_review": "yes" if not normalize_doi(crossref_row.get("crossref_doi", "")) and not doi else "no",
        }
        merged[merge_key] = row

    output_rows = list(merged.values())
    for index, row in enumerate(output_rows, start=1):
        row["paper_id"] = f"paper_{index:04d}"
    return output_rows


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
    openalex_rows = read_rows(Path(args.openalex))
    crossref_rows = read_rows(Path(args.crossref))
    merged_rows = merge_rows(openalex_rows, crossref_rows)
    count = write_rows(Path(args.output), merged_rows)

    print(f"OpenAlex rows: {len(openalex_rows)}")
    print(f"Crossref rows: {len(crossref_rows)}")
    print(f"Merged unique rows: {count}")
    print(f"Output CSV: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
