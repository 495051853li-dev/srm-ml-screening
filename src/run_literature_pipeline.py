"""Stage-1 local SRM literature retrieval pipeline.

This script searches OpenAlex and Crossref, performs lightweight automated
screening, deduplicates candidate papers, and writes
``data/processed/candidate_papers.csv`` for later manual review.
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import html
import json
import re
import time
from difflib import SequenceMatcher
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

import requests


ROOT = Path(__file__).resolve().parent.parent
OPENALEX_URL = "https://api.openalex.org/works"
CROSSREF_URL = "https://api.crossref.org/works"
DEFAULT_QUERIES = [
    "steam reforming of methane",
    "methane steam reforming catalyst",
    "Ni-based steam reforming of methane catalyst",
    "SRM catalyst methane",
]
OUTPUT_COLUMNS = [
    "paper_id",
    "title",
    "first_author",
    "publication_year",
    "journal",
    "doi",
    "abstract_or_summary",
    "source_api",
    "is_open_access",
    "has_abstract",
    "has_fulltext",
    "document_type",
    "retrieval_query",
    "retrieval_date",
    "screening_status",
    "screening_notes",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run stage-1 SRM literature retrieval.")
    parser.add_argument(
        "--queries",
        nargs="*",
        default=DEFAULT_QUERIES,
        help="Query strings to search across OpenAlex and Crossref.",
    )
    parser.add_argument("--mailto", default="", help="Optional email for polite API access.")
    parser.add_argument(
        "--max-results-per-query",
        type=int,
        default=100,
        help="Maximum results to retrieve from each API for each query.",
    )
    parser.add_argument("--per-page", type=int, default=50, help="Page size for each API request.")
    parser.add_argument(
        "--output",
        default="data/processed/candidate_papers.csv",
        help="Path to the deduplicated candidate paper CSV.",
    )
    parser.add_argument(
        "--openalex-raw-output",
        default="outputs/tables/openalex_raw_results.csv",
        help="Optional CSV path for raw OpenAlex results.",
    )
    parser.add_argument(
        "--crossref-raw-output",
        default="outputs/tables/crossref_raw_results.csv",
        help="Optional CSV path for raw Crossref results.",
    )
    parser.add_argument("--timeout", type=int, default=30, help="HTTP timeout in seconds.")
    parser.add_argument("--sleep-seconds", type=float, default=0.15, help="Delay between API requests.")
    return parser.parse_args()


def build_session(mailto: str) -> requests.Session:
    session = requests.Session()
    user_agent = "srm-ml-screening/0.1 (stage-1 local literature retrieval)"
    if mailto:
        user_agent = f"{user_agent}; mailto:{mailto}"
    headers = {"User-Agent": user_agent}
    if mailto:
        headers["From"] = mailto
    session.headers.update(headers)
    return session


def ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def normalize_doi(value: str) -> str:
    return (
        (value or "")
        .strip()
        .replace("https://doi.org/", "")
        .replace("http://doi.org/", "")
        .lower()
    )


def normalize_text(value: str) -> str:
    value = html.unescape(value or "")
    value = value.lower().strip()
    value = re.sub(r"<[^>]+>", " ", value)
    value = re.sub(r"\s+", " ", value)
    value = re.sub(r"[^a-z0-9 ]+", "", value)
    return value


def title_similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, normalize_text(a), normalize_text(b)).ratio()


def decode_openalex_abstract(inverted_index: Optional[Dict[str, List[int]]]) -> str:
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


def strip_html_tags(value: str) -> str:
    value = html.unescape(value or "")
    value = re.sub(r"<[^>]+>", " ", value)
    value = re.sub(r"\s+", " ", value)
    return value.strip()


def normalize_document_type(source_api: str, raw_type: str, title: str, journal: str) -> str:
    raw = (raw_type or "").lower().strip()
    title_text = (title or "").lower()
    journal_text = (journal or "").lower()

    review_markers = ("review", "minireview", "mini-review")
    if any(marker in title_text for marker in review_markers):
        return "review"

    if source_api == "crossref":
        if raw == "journal-article":
            if "review" in title_text or "review" in journal_text:
                return "review"
            return "journal_article"
        if raw in {"review", "book-review"}:
            return "review"
        if raw == "posted-content":
            return "preprint"
        if raw == "proceedings-article":
            return "conference_paper"
        if raw == "dissertation":
            return "thesis"
        if raw == "journal":
            return "journal"
        if raw == "book-chapter":
            return "book_chapter"
        if raw == "report":
            return "report"
        if raw == "peer-review":
            return "peer_review"
        if raw == "book":
            return "book"
        if raw == "reference-entry":
            return "reference_entry"
        if raw == "standard":
            return "standard"
        if raw == "grant":
            return "grant"
        if raw == "dataset":
            return "dataset"
        if raw == "component":
            return "component"
        if raw == "patent":
            return "patent"

    if raw in {"article", "journal-article"}:
        return "journal_article"
    if raw:
        return raw.replace("-", "_")
    return "unknown"


def openalex_iter_works(
    session: requests.Session,
    query: str,
    max_results: int,
    per_page: int,
    timeout: int,
    sleep_seconds: float,
    mailto: str,
) -> List[Dict]:
    cursor = "*"
    fetched = 0
    works: List[Dict] = []

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

        works.extend(results)
        fetched += len(results)
        cursor = payload.get("meta", {}).get("next_cursor")
        if not cursor:
            break
        time.sleep(sleep_seconds)

    return works[:max_results]


def search_openalex(
    session: requests.Session,
    queries: List[str],
    max_results_per_query: int,
    per_page: int,
    timeout: int,
    sleep_seconds: float,
    mailto: str,
    retrieval_date: str,
) -> List[Dict[str, str]]:
    rows: List[Dict[str, str]] = []
    for query in queries:
        works = openalex_iter_works(
            session=session,
            query=query,
            max_results=max_results_per_query,
            per_page=per_page,
            timeout=timeout,
            sleep_seconds=sleep_seconds,
            mailto=mailto,
        )
        for work in works:
            primary_location = work.get("primary_location") or {}
            source = primary_location.get("source") or {}
            authorships = work.get("authorships") or []
            first_author = ""
            if authorships:
                first_author = ((authorships[0].get("author") or {}).get("display_name") or "").strip()
            doi = normalize_doi(work.get("doi", ""))
            title = (work.get("display_name") or "").strip()
            journal = (source.get("display_name") or "").strip()
            best_oa_url = (
                primary_location.get("pdf_url")
                or primary_location.get("landing_page_url")
                or (work.get("open_access") or {}).get("oa_url")
                or ""
            )
            abstract = decode_openalex_abstract(work.get("abstract_inverted_index"))
            document_type = normalize_document_type(
                source_api="openalex",
                raw_type=(work.get("type") or ""),
                title=title,
                journal=journal,
            )
            rows.append(
                {
                    "title": title,
                    "first_author": first_author,
                    "publication_year": str(work.get("publication_year") or ""),
                    "journal": journal,
                    "doi": doi,
                    "abstract_or_summary": abstract,
                    "source_api": "openalex",
                    "is_open_access": "yes" if (work.get("open_access") or {}).get("is_oa") else "no",
                    "has_abstract": "yes" if abstract else "no",
                    "has_fulltext": "yes" if best_oa_url else "no",
                    "document_type": document_type,
                    "retrieval_query": query,
                    "retrieval_date": retrieval_date,
                    "screening_status": "raw_retrieved",
                    "screening_notes": f"openalex_id={work.get('id', '')}",
                    "paper_url": primary_location.get("landing_page_url", "") or work.get("id", ""),
                }
            )
        time.sleep(sleep_seconds)
    return rows


def crossref_iter_works(
    session: requests.Session,
    query: str,
    max_results: int,
    per_page: int,
    timeout: int,
    sleep_seconds: float,
) -> List[Dict]:
    offset = 0
    works: List[Dict] = []
    while len(works) < max_results:
        params = {
            "query.bibliographic": query,
            "rows": min(per_page, max_results - len(works)),
            "offset": offset,
        }
        response = session.get(CROSSREF_URL, params=params, timeout=timeout)
        response.raise_for_status()
        items = response.json().get("message", {}).get("items", [])
        if not items:
            break
        works.extend(items)
        offset += len(items)
        time.sleep(sleep_seconds)
    return works[:max_results]


def search_crossref(
    session: requests.Session,
    queries: List[str],
    max_results_per_query: int,
    per_page: int,
    timeout: int,
    sleep_seconds: float,
    retrieval_date: str,
) -> List[Dict[str, str]]:
    rows: List[Dict[str, str]] = []
    for query in queries:
        works = crossref_iter_works(
            session=session,
            query=query,
            max_results=max_results_per_query,
            per_page=per_page,
            timeout=timeout,
            sleep_seconds=sleep_seconds,
        )
        for work in works:
            titles = work.get("title") or []
            title = titles[0].strip() if titles else ""
            journal_titles = work.get("container-title") or []
            journal = journal_titles[0].strip() if journal_titles else ""
            authors = work.get("author") or []
            first_author = ""
            if authors:
                first_author = (authors[0].get("family") or authors[0].get("name") or "").strip()

            published_year = ""
            date_parts = (
                ((work.get("published-print") or {}).get("date-parts"))
                or ((work.get("published-online") or {}).get("date-parts"))
                or []
            )
            if date_parts and date_parts[0]:
                published_year = str(date_parts[0][0])

            abstract = strip_html_tags(work.get("abstract", "") or "")
            links = work.get("link") or []
            has_fulltext = "yes" if links else "no"
            rows.append(
                {
                    "title": title,
                    "first_author": first_author,
                    "publication_year": published_year,
                    "journal": journal,
                    "doi": normalize_doi(work.get("DOI", "")),
                    "abstract_or_summary": abstract,
                    "source_api": "crossref",
                    "is_open_access": "unclear",
                    "has_abstract": "yes" if abstract else "no",
                    "has_fulltext": has_fulltext,
                    "document_type": normalize_document_type(
                        source_api="crossref",
                        raw_type=(work.get("type") or ""),
                        title=title,
                        journal=journal,
                    ),
                    "retrieval_query": query,
                    "retrieval_date": retrieval_date,
                    "screening_status": "raw_retrieved",
                    "screening_notes": f"crossref_type={work.get('type', '')}",
                    "paper_url": work.get("URL", "") or "",
                }
            )
        time.sleep(sleep_seconds)
    return rows


def should_exclude(row: Dict[str, str]) -> Optional[str]:
    text = " ".join(
        [
            row.get("title", ""),
            row.get("abstract_or_summary", ""),
            row.get("journal", ""),
            row.get("screening_notes", ""),
        ]
    ).lower()
    document_type = (row.get("document_type") or "").lower()
    title = (row.get("title") or "").lower()

    exclusion_patterns = {
        "methanol_reforming": [r"\bmethanol\b"],
        "ethanol_reforming": [r"\bethanol\b"],
        "ethane_reforming": [r"\bethane\b"],
        "propane_or_higher_hydrocarbon": [r"\bpropane\b", r"\bbutane\b", r"\bbiogasoline\b"],
        "non_methane_feed": [r"\bdimethyl ether\b", r"\bdme\b", r"\bglycerol\b"],
        "patent_like": [r"\bpatent\b"],
    }
    for reason, patterns in exclusion_patterns.items():
        if any(re.search(pattern, text) for pattern in patterns):
            return reason

    if document_type == "patent":
        return "patent_document_type"

    methane_signal = bool(re.search(r"\bmethane\b", text))
    srm_signal = bool(re.search(r"\bsteam reform", text)) or "srm" in title
    if not methane_signal or not srm_signal:
        return "weak_methane_srm_signal"

    return None


def prefer_row(existing: Dict[str, str], new_row: Dict[str, str]) -> Dict[str, str]:
    def score(row: Dict[str, str]) -> Tuple[int, int, int, int]:
        document_type = row.get("document_type", "")
        document_score = 0
        if document_type == "journal_article":
            document_score = 3
        elif document_type == "review":
            document_score = 2
        elif document_type in {"conference_paper", "thesis"}:
            document_score = 1

        has_abstract = 1 if row.get("has_abstract") == "yes" else 0
        has_fulltext = 1 if row.get("has_fulltext") == "yes" else 0
        is_open_access = 1 if row.get("is_open_access") == "yes" else 0
        return (document_score, has_abstract, has_fulltext, is_open_access)

    if score(new_row) > score(existing):
        combined_sources = sorted(set((existing.get("source_api", "") + ";" + new_row.get("source_api", "")).split(";")) - {""})
        new_row["source_api"] = ";".join(combined_sources)
        existing_query = existing.get("retrieval_query", "")
        new_query = new_row.get("retrieval_query", "")
        queries = sorted(set((existing_query + " || " + new_query).split(" || ")) - {""})
        new_row["retrieval_query"] = " || ".join(queries)
        return new_row

    combined_sources = sorted(set((existing.get("source_api", "") + ";" + new_row.get("source_api", "")).split(";")) - {""})
    existing["source_api"] = ";".join(combined_sources)
    queries = sorted(set((existing.get("retrieval_query", "") + " || " + new_row.get("retrieval_query", "")).split(" || ")) - {""})
    existing["retrieval_query"] = " || ".join(queries)
    if existing.get("has_abstract") != "yes" and new_row.get("has_abstract") == "yes":
        existing["abstract_or_summary"] = new_row.get("abstract_or_summary", "")
        existing["has_abstract"] = "yes"
    if existing.get("has_fulltext") != "yes" and new_row.get("has_fulltext") == "yes":
        existing["has_fulltext"] = "yes"
    if existing.get("is_open_access") not in {"yes"} and new_row.get("is_open_access") == "yes":
        existing["is_open_access"] = "yes"
    return existing


def deduplicate_rows(rows: List[Dict[str, str]]) -> List[Dict[str, str]]:
    by_doi: Dict[str, Dict[str, str]] = {}
    no_doi_rows: List[Dict[str, str]] = []

    for row in rows:
        doi = normalize_doi(row.get("doi", ""))
        if doi:
            if doi in by_doi:
                by_doi[doi] = prefer_row(by_doi[doi], row)
            else:
                by_doi[doi] = row
        else:
            no_doi_rows.append(row)

    deduped_no_doi: List[Dict[str, str]] = []
    for row in no_doi_rows:
        matched_index = None
        for index, existing in enumerate(deduped_no_doi):
            same_year = (existing.get("publication_year", "") or "").strip() == (row.get("publication_year", "") or "").strip()
            if same_year and title_similarity(existing.get("title", ""), row.get("title", "")) >= 0.94:
                matched_index = index
                break
        if matched_index is None:
            deduped_no_doi.append(row)
        else:
            deduped_no_doi[matched_index] = prefer_row(deduped_no_doi[matched_index], row)

    combined = list(by_doi.values()) + deduped_no_doi
    combined.sort(key=lambda r: ((r.get("publication_year") or ""), (r.get("title") or "")))
    for index, row in enumerate(combined, start=1):
        row["paper_id"] = f"paper_{index:04d}"
    return combined


def normalize_and_screen(rows: List[Dict[str, str]]) -> Tuple[List[Dict[str, str]], List[Dict[str, str]]]:
    kept: List[Dict[str, str]] = []
    excluded: List[Dict[str, str]] = []

    for row in rows:
        document_type = row.get("document_type", "")
        if document_type not in {"journal_article", "review"}:
            row["screening_status"] = "excluded_auto"
            row["screening_notes"] = f"excluded_non_priority_document_type:{document_type or 'unknown'}"
            excluded.append(row)
            continue

        exclusion_reason = should_exclude(row)
        if exclusion_reason:
            row["screening_status"] = "excluded_auto"
            row["screening_notes"] = exclusion_reason
            excluded.append(row)
            continue

        row["screening_status"] = "pending_manual_screen"
        if document_type == "review":
            row["screening_notes"] = "review_kept_separately_for_manual_flagging"
        else:
            row["screening_notes"] = "journal_article_candidate_after_auto_screening"
        kept.append(row)

    return kept, excluded


def write_rows(path: Path, rows: Iterable[Dict[str, str]], fieldnames: List[str]) -> int:
    ensure_parent(path)
    count = 0
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key, "") for key in fieldnames})
            count += 1
    return count


def main() -> int:
    args = parse_args()
    retrieval_date = dt.date.today().isoformat()
    session = build_session(args.mailto)

    openalex_rows = search_openalex(
        session=session,
        queries=args.queries,
        max_results_per_query=args.max_results_per_query,
        per_page=args.per_page,
        timeout=args.timeout,
        sleep_seconds=args.sleep_seconds,
        mailto=args.mailto,
        retrieval_date=retrieval_date,
    )
    crossref_rows = search_crossref(
        session=session,
        queries=args.queries,
        max_results_per_query=args.max_results_per_query,
        per_page=args.per_page,
        timeout=args.timeout,
        sleep_seconds=args.sleep_seconds,
        retrieval_date=retrieval_date,
    )

    raw_fieldnames = OUTPUT_COLUMNS + ["paper_url"]
    write_rows(Path(args.openalex_raw_output), openalex_rows, raw_fieldnames)
    write_rows(Path(args.crossref_raw_output), crossref_rows, raw_fieldnames)

    raw_combined = openalex_rows + crossref_rows
    screened_rows, excluded_rows = normalize_and_screen(raw_combined)
    deduped_rows = deduplicate_rows(screened_rows)
    write_rows(Path(args.output), deduped_rows, OUTPUT_COLUMNS)

    summary = {
        "queries": args.queries,
        "retrieval_date": retrieval_date,
        "openalex_raw_results": len(openalex_rows),
        "crossref_raw_results": len(crossref_rows),
        "raw_results_total": len(raw_combined),
        "auto_excluded_results": len(excluded_rows),
        "post_screen_results_before_dedup": len(screened_rows),
        "deduplicated_candidate_papers": len(deduped_rows),
        "output_csv": args.output,
    }
    summary_path = ROOT / "outputs" / "tables" / "candidate_papers_summary.json"
    ensure_parent(summary_path)
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"OpenAlex raw results: {len(openalex_rows)}")
    print(f"Crossref raw results: {len(crossref_rows)}")
    print(f"Raw results total: {len(raw_combined)}")
    print(f"Auto-excluded results: {len(excluded_rows)}")
    print(f"Post-screen results before dedup: {len(screened_rows)}")
    print(f"Deduplicated candidate papers: {len(deduped_rows)}")
    print(f"Candidate CSV: {args.output}")
    print(f"Summary JSON: {summary_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
