"""Discover legal full-text source candidates for high-priority SRM papers.

This stage does not download content. It only builds a ranked candidate URL
table for stage4.5 full-text acquisition. Candidate URLs are intentionally
conservative: they use DOI landing pages, URLs already present in OpenAlex or
Crossref metadata, publisher URL patterns that are deterministic from DOI, and
local PDF paths for manually supplied files.
"""

from __future__ import annotations

import argparse
import csv
import re
from pathlib import Path
from typing import Dict, Iterable, List, Sequence


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_ELIGIBLE = ROOT / "data" / "processed" / "eligible_high_if_pool.csv"
DEFAULT_SCORED = ROOT / "data" / "processed" / "candidate_papers_high_if_scored.csv"
DEFAULT_MANIFEST = ROOT / "data" / "processed" / "fulltext_fetch_manifest.csv"
DEFAULT_OPENALEX_RAW = ROOT / "outputs" / "tables" / "openalex_raw_results.csv"
DEFAULT_CROSSREF_RAW = ROOT / "outputs" / "tables" / "crossref_raw_results.csv"
DEFAULT_OUTPUT = ROOT / "data" / "processed" / "fulltext_source_candidates.csv"
PDF_DIR = ROOT / "data" / "raw" / "pdfs"

OUTPUT_COLUMNS = [
    "paper_id",
    "doi",
    "title",
    "candidate_url",
    "candidate_source_type",
    "candidate_priority",
    "expected_content_type",
    "source_discovery_method",
    "notes",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Discover full-text candidate sources for SRM papers.")
    parser.add_argument("--eligible", default=str(DEFAULT_ELIGIBLE))
    parser.add_argument("--scored", default=str(DEFAULT_SCORED))
    parser.add_argument("--manifest", default=str(DEFAULT_MANIFEST))
    parser.add_argument("--openalex-raw", default=str(DEFAULT_OPENALEX_RAW))
    parser.add_argument("--crossref-raw", default=str(DEFAULT_CROSSREF_RAW))
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    parser.add_argument("--limit", type=int, default=20, help="Limit papers for a controlled test run.")
    return parser.parse_args()


def read_rows(path: Path) -> List[Dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def write_rows(path: Path, rows: Sequence[Dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=OUTPUT_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)


def normalize_doi(value: str) -> str:
    value = (value or "").strip()
    value = re.sub(r"^https?://(dx\.)?doi\.org/", "", value, flags=re.IGNORECASE)
    return value.lower().strip()


def doi_safe_name(doi: str) -> str:
    doi = normalize_doi(doi)
    return re.sub(r"[^A-Za-z0-9._-]+", "_", doi).strip("_")


def title_slug(title: str, max_len: int = 80) -> str:
    slug = re.sub(r"[^A-Za-z0-9]+", "_", title or "").strip("_").lower()
    return slug[:max_len]


def build_doi_map(rows: Iterable[Dict[str, str]]) -> Dict[str, List[Dict[str, str]]]:
    mapping: Dict[str, List[Dict[str, str]]] = {}
    for row in rows:
        doi = normalize_doi(row.get("doi", ""))
        if doi:
            mapping.setdefault(doi, []).append(row)
    return mapping


def choose_papers(eligible_rows: List[Dict[str, str]], scored_rows: List[Dict[str, str]], limit: int) -> List[Dict[str, str]]:
    rows = eligible_rows or scored_rows
    rows = [row for row in rows if str(row.get("paper_id", "")).strip()]
    if "priority_rank" in (rows[0].keys() if rows else []):
        rows = sorted(rows, key=lambda row: safe_float(row.get("priority_rank", "999999"), 999999.0))
    if limit > 0:
        rows = rows[:limit]
    return rows


def safe_float(value: str, default: float = 0.0) -> float:
    try:
        return float(str(value or "").strip())
    except ValueError:
        return default


def add_candidate(
    rows: List[Dict[str, str]],
    seen: set[tuple[str, str, str]],
    paper: Dict[str, str],
    candidate_url: str,
    candidate_source_type: str,
    candidate_priority: int,
    expected_content_type: str,
    method: str,
    notes: str,
) -> None:
    paper_id = str(paper.get("paper_id", "")).strip()
    candidate_url = (candidate_url or "").strip()
    if not paper_id or not candidate_url:
        return
    key = (paper_id, candidate_url.lower(), candidate_source_type)
    if key in seen:
        return
    seen.add(key)
    rows.append(
        {
            "paper_id": paper_id,
            "doi": paper.get("doi", ""),
            "title": paper.get("title", ""),
            "candidate_url": candidate_url,
            "candidate_source_type": candidate_source_type,
            "candidate_priority": str(candidate_priority),
            "expected_content_type": expected_content_type,
            "source_discovery_method": method,
            "notes": notes,
        }
    )


def rsc_year_from_paper(paper: Dict[str, str]) -> str:
    year = str(paper.get("publication_year", "")).strip()
    if "." in year:
        year = year.split(".", 1)[0]
    return year


def add_publisher_patterns(rows: List[Dict[str, str]], seen: set[tuple[str, str, str]], paper: Dict[str, str]) -> None:
    doi = normalize_doi(paper.get("doi", ""))
    if not doi:
        return
    if doi.startswith("10.1021/"):
        add_candidate(
            rows,
            seen,
            paper,
            f"https://pubs.acs.org/doi/{doi}",
            "publisher_landing_page",
            60,
            "html",
            "publisher_doi_pattern",
            "ACS landing page pattern from DOI; legal if publicly accessible.",
        )
        add_candidate(
            rows,
            seen,
            paper,
            f"https://pubs.acs.org/doi/pdf/{doi}",
            "publisher_pdf_candidate",
            85,
            "pdf",
            "publisher_pdf_pattern",
            "ACS PDF URL pattern from DOI; do not bypass access controls.",
        )
    elif doi.startswith("10.1039/"):
        suffix = doi.split("/", 1)[1]
        year = rsc_year_from_paper(paper)
        if year:
            journal_code = suffix[2:4] if len(suffix) >= 4 else ""
            if journal_code:
                add_candidate(
                    rows,
                    seen,
                    paper,
                    f"https://pubs.rsc.org/en/content/articlelanding/{year}/{journal_code}/{suffix}",
                    "publisher_landing_page",
                    70,
                    "html",
                    "publisher_doi_pattern",
                    "RSC landing page pattern with journal code from DOI suffix; legal if publicly accessible.",
                )
                add_candidate(
                    rows,
                    seen,
                    paper,
                    f"https://pubs.rsc.org/en/content/articlepdf/{year}/{journal_code}/{suffix}",
                    "publisher_pdf_candidate",
                    92,
                    "pdf",
                    "publisher_pdf_pattern",
                    "RSC PDF URL pattern with journal code from DOI suffix; do not bypass access controls.",
                )
            add_candidate(
                rows,
                seen,
                paper,
                f"https://pubs.rsc.org/en/content/articlelanding/{year}/{suffix}",
                "publisher_landing_page",
                60,
                "html",
                "publisher_doi_pattern",
                "RSC landing page pattern from DOI; legal if publicly accessible.",
            )
            add_candidate(
                rows,
                seen,
                paper,
                f"https://pubs.rsc.org/en/content/articlepdf/{year}/{suffix}",
                "publisher_pdf_candidate",
                90,
                "pdf",
                "publisher_pdf_pattern",
                "RSC PDF URL pattern from DOI; do not bypass access controls.",
            )


def add_local_pdf_candidates(rows: List[Dict[str, str]], seen: set[tuple[str, str, str]], paper: Dict[str, str]) -> None:
    doi = normalize_doi(paper.get("doi", ""))
    title = paper.get("title", "")
    paper_id = paper.get("paper_id", "")
    candidates = [
        PDF_DIR / f"{paper_id}.pdf",
        PDF_DIR / f"{doi_safe_name(doi)}.pdf",
        PDF_DIR / f"{paper_id}_{doi_safe_name(doi)}.pdf",
    ]
    slug = title_slug(title)
    if slug:
        candidates.append(PDF_DIR / f"{paper_id}_{slug}.pdf")
    for path in candidates:
        rel = path.relative_to(ROOT)
        exists = path.exists()
        add_candidate(
            rows,
            seen,
            paper,
            str(rel),
            "local_pdf_candidate",
            100 if exists else 75,
            "pdf",
            "local_manual_pdf_path",
            "Manual legal PDF drop path; place a legally obtained PDF here before running ingest_local_pdfs.py."
            + (" File already exists." if exists else ""),
        )


def main() -> int:
    args = parse_args()
    eligible_rows = read_rows(Path(args.eligible))
    scored_rows = read_rows(Path(args.scored))
    manifest_rows = read_rows(Path(args.manifest))
    openalex_map = build_doi_map(read_rows(Path(args.openalex_raw)))
    crossref_map = build_doi_map(read_rows(Path(args.crossref_raw)))
    manifest_map = {str(row.get("paper_id", "")).strip(): row for row in manifest_rows if row.get("paper_id")}

    papers = choose_papers(eligible_rows, scored_rows, args.limit)
    candidates: List[Dict[str, str]] = []
    seen: set[tuple[str, str, str]] = set()

    for paper in papers:
        doi = normalize_doi(paper.get("doi", ""))
        if doi:
            add_candidate(
                candidates,
                seen,
                paper,
                f"https://doi.org/{doi}",
                "doi_url",
                50,
                "html",
                "doi_from_candidate_pool",
                "DOI resolver landing page; useful for redirection but often not enough for experimental extraction.",
            )

        existing = manifest_map.get(str(paper.get("paper_id", "")).strip())
        for key in ["source_url", "final_url", "attempted_url", "selected_url"]:
            if existing:
                add_candidate(
                    candidates,
                    seen,
                    paper,
                    existing.get(key, ""),
                    "existing_manifest_url",
                    55,
                    "html_or_pdf",
                    "previous_stage4_manifest",
                    f"Previously recorded stage4 URL from `{key}`.",
                )

        for row in openalex_map.get(doi, []):
            url = row.get("paper_url", "")
            if url:
                add_candidate(
                    candidates,
                    seen,
                    paper,
                    url,
                    "openalex_landing_or_oa_url",
                    70 if str(row.get("is_open_access", "")).lower() == "yes" else 55,
                    "html_or_pdf",
                    "openalex_raw_metadata",
                    "URL available in local OpenAlex raw metadata; OA flag is used only as a hint.",
                )

        for row in crossref_map.get(doi, []):
            url = row.get("paper_url", "")
            if url:
                add_candidate(
                    candidates,
                    seen,
                    paper,
                    url,
                    "crossref_landing_or_link_url",
                    45,
                    "html_or_pdf",
                    "crossref_raw_metadata",
                    "URL available in local Crossref raw metadata.",
                )

        add_publisher_patterns(candidates, seen, paper)
        add_local_pdf_candidates(candidates, seen, paper)

    candidates = sorted(
        candidates,
        key=lambda row: (
            str(row["paper_id"]),
            -safe_float(row["candidate_priority"], 0.0),
            row["candidate_source_type"],
        ),
    )
    write_rows(Path(args.output), candidates)
    print(f"Fulltext source candidates written: {Path(args.output)}")
    print(f"Papers considered: {len(papers)}")
    print(f"Candidate URLs/paths: {len(candidates)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
