"""Discover legal full-text source candidates for high-priority SRM papers.

This stage only builds a ranked source-candidate table. It does not download
content and does not bypass access controls. Candidate sources include local
PDFs, open-access links, Crossref/OpenAlex/Unpaywall locations, DOI landing
pages, publisher landing pages, and publisher PDF/HTML URL patterns that may
work when the current institutional IP is authorized.
"""

from __future__ import annotations

import argparse
import csv
import os
import re
import time
from pathlib import Path
from typing import Dict, Iterable, List, Sequence
from urllib.parse import quote

import requests


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
    "candidate_source",
    "candidate_source_type",
    "expected_content_type",
    "access_route",
    "is_open_access",
    "institutional_access_possible",
    "source_priority",
    "candidate_priority",
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
    parser.add_argument("--sleep", type=float, default=0.2, help="Sleep seconds between optional live API requests.")
    parser.add_argument("--timeout", type=int, default=25)
    parser.add_argument(
        "--no-live-lookup",
        action="store_true",
        help="Skip live OpenAlex/Crossref/Unpaywall lookup and use only local metadata.",
    )
    parser.add_argument(
        "--unpaywall-email",
        default=os.environ.get("UNPAYWALL_EMAIL", ""),
        help="Optional email for Unpaywall API. If omitted, Unpaywall lookup is skipped.",
    )
    return parser.parse_args()


def read_rows(path: Path) -> List[Dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def write_rows(path: Path, rows: Sequence[Dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=OUTPUT_COLUMNS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def normalize_doi(value: str) -> str:
    value = (value or "").strip()
    value = re.sub(r"^https?://(dx\.)?doi\.org/", "", value, flags=re.IGNORECASE)
    return value.lower().strip()


def doi_safe_name(doi: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "_", normalize_doi(doi)).strip("_")


def title_slug(title: str, max_len: int = 80) -> str:
    slug = re.sub(r"[^A-Za-z0-9]+", "_", title or "").strip("_").lower()
    return slug[:max_len]


def safe_float(value: str, default: float = 0.0) -> float:
    try:
        return float(str(value or "").strip())
    except ValueError:
        return default


def yes_no_from_value(value: str) -> str:
    value = str(value or "").strip().lower()
    if value in {"yes", "true", "1", "oa", "open"}:
        return "yes"
    if value in {"no", "false", "0"}:
        return "no"
    return "unclear"


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
    if rows and "priority_rank" in rows[0]:
        rows = sorted(rows, key=lambda row: safe_float(row.get("priority_rank", "999999"), 999999.0))
    if limit > 0:
        rows = rows[:limit]
    return rows


def add_candidate(
    rows: List[Dict[str, str]],
    seen: set[tuple[str, str, str]],
    paper: Dict[str, str],
    candidate_url: str,
    candidate_source: str,
    candidate_source_type: str,
    expected_content_type: str,
    access_route: str,
    is_open_access: str,
    institutional_access_possible: str,
    source_priority: int,
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
            "candidate_source": candidate_source,
            "candidate_source_type": candidate_source_type,
            "expected_content_type": expected_content_type,
            "access_route": access_route,
            "is_open_access": is_open_access,
            "institutional_access_possible": institutional_access_possible,
            "source_priority": str(source_priority),
            "candidate_priority": str(source_priority),
            "source_discovery_method": method,
            "notes": notes,
        }
    )


def publication_year(paper: Dict[str, str]) -> str:
    year = str(paper.get("publication_year", "")).strip()
    if "." in year:
        year = year.split(".", 1)[0]
    return year


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
            "local_manual_pdf",
            "local_pdf",
            "pdf",
            "local_pdf",
            "unclear",
            "no",
            120 if exists else 65,
            "local_manual_pdf_path",
            "Local legally obtained PDF path."
            + (" File exists and should be checked before network fetching." if exists else " Candidate path for manual PDF placement."),
        )


def add_doi_candidate(rows: List[Dict[str, str]], seen: set[tuple[str, str, str]], paper: Dict[str, str]) -> None:
    doi = normalize_doi(paper.get("doi", ""))
    if not doi:
        return
    add_candidate(
        rows,
        seen,
        paper,
        f"https://doi.org/{doi}",
        "doi_resolver",
        "doi_landing_page",
        "html",
        "doi_landing",
        yes_no_from_value(paper.get("is_open_access", "")),
        "unknown",
        45,
        "doi_from_candidate_pool",
        "DOI resolver landing page. Useful for discovery, but not enough for experimental extraction by itself.",
    )


def add_publisher_patterns(rows: List[Dict[str, str]], seen: set[tuple[str, str, str]], paper: Dict[str, str]) -> None:
    doi = normalize_doi(paper.get("doi", ""))
    if not doi:
        return
    year = publication_year(paper)
    quoted_doi = quote(doi, safe="/.")

    def add(url: str, source: str, source_type: str, expected: str, route: str, priority: int, notes: str) -> None:
        add_candidate(
            rows,
            seen,
            paper,
            url,
            source,
            source_type,
            expected,
            route,
            "unclear",
            "yes",
            priority,
            "publisher_doi_pattern",
            notes + " This only uses normal direct URLs and does not bypass access controls.",
        )

    if doi.startswith("10.1021/"):
        add(f"https://pubs.acs.org/doi/{doi}", "acs", "publisher_landing_page", "html", "publisher_landing", 70, "ACS article landing page.")
        add(f"https://pubs.acs.org/doi/pdf/{doi}", "acs", "institutional_pdf", "pdf", "institutional_access", 105, "ACS PDF URL pattern.")
    elif doi.startswith("10.1039/"):
        suffix = doi.split("/", 1)[1]
        journal_code = suffix[2:4] if len(suffix) >= 4 else ""
        if year and journal_code:
            add(
                f"https://pubs.rsc.org/en/content/articlelanding/{year}/{journal_code}/{suffix}",
                "rsc",
                "publisher_landing_page",
                "html",
                "publisher_landing",
                72,
                "RSC article landing page pattern.",
            )
            add(
                f"https://pubs.rsc.org/en/content/articlepdf/{year}/{journal_code}/{suffix}",
                "rsc",
                "institutional_pdf",
                "pdf",
                "institutional_access",
                108,
                "RSC PDF URL pattern.",
            )
    elif doi.startswith("10.1016/"):
        add(
            f"https://www.sciencedirect.com/science/article/pii/{doi.split('/')[-1]}",
            "sciencedirect",
            "publisher_landing_page",
            "html",
            "publisher_landing",
            65,
            "ScienceDirect landing pattern from DOI suffix.",
        )
        add(
            f"https://www.sciencedirect.com/science/article/pii/{doi.split('/')[-1]}/pdfft?isDTMRedir=true&download=true",
            "sciencedirect",
            "institutional_pdf",
            "pdf",
            "institutional_access",
            85,
            "ScienceDirect PDF pattern from DOI suffix.",
        )
    elif doi.startswith("10.1007/") or doi.startswith("10.1186/"):
        add(f"https://link.springer.com/article/{doi}", "springer", "publisher_landing_page", "html", "publisher_landing", 72, "Springer article landing page.")
        add(f"https://link.springer.com/content/pdf/{quoted_doi}.pdf", "springer", "institutional_pdf", "pdf", "institutional_access", 105, "Springer PDF pattern.")
    elif doi.startswith("10.1002/") or doi.startswith("10.1111/"):
        add(f"https://onlinelibrary.wiley.com/doi/{doi}", "wiley", "publisher_landing_page", "html", "publisher_landing", 72, "Wiley article landing page.")
        add(f"https://onlinelibrary.wiley.com/doi/pdf/{doi}", "wiley", "institutional_pdf", "pdf", "institutional_access", 105, "Wiley PDF pattern.")
    elif doi.startswith("10.1080/") or doi.startswith("10.1081/"):
        add(f"https://www.tandfonline.com/doi/full/{doi}", "taylor_francis", "institutional_html_fulltext", "html", "institutional_access", 88, "Taylor & Francis full HTML pattern.")
        add(f"https://www.tandfonline.com/doi/pdf/{doi}", "taylor_francis", "institutional_pdf", "pdf", "institutional_access", 105, "Taylor & Francis PDF pattern.")


def add_local_raw_metadata_candidates(
    rows: List[Dict[str, str]],
    seen: set[tuple[str, str, str]],
    paper: Dict[str, str],
    openalex_map: Dict[str, List[Dict[str, str]]],
    crossref_map: Dict[str, List[Dict[str, str]]],
) -> None:
    doi = normalize_doi(paper.get("doi", ""))
    for raw in openalex_map.get(doi, []):
        url = raw.get("paper_url", "")
        is_oa = yes_no_from_value(raw.get("is_open_access", ""))
        source_type = "oa_html_fulltext" if is_oa == "yes" else "openalex_location"
        route = "open_access" if is_oa == "yes" else "unknown"
        add_candidate(
            rows,
            seen,
            paper,
            url,
            "openalex_location",
            source_type,
            "html_or_pdf",
            route,
            is_oa,
            "unknown",
            84 if is_oa == "yes" else 58,
            "openalex_raw_metadata",
            "URL from local OpenAlex raw metadata.",
        )
    for raw in crossref_map.get(doi, []):
        add_candidate(
            rows,
            seen,
            paper,
            raw.get("paper_url", ""),
            "crossref_link",
            "crossref_link",
            "html_or_pdf",
            "unknown",
            "unclear",
            "unknown",
            52,
            "crossref_raw_metadata",
            "URL from local Crossref raw metadata.",
        )


def add_live_api_candidates(
    rows: List[Dict[str, str]],
    seen: set[tuple[str, str, str]],
    paper: Dict[str, str],
    session: requests.Session,
    timeout: int,
    unpaywall_email: str,
) -> None:
    doi = normalize_doi(paper.get("doi", ""))
    if not doi:
        return

    try:
        response = session.get("https://api.openalex.org/works/doi:" + quote("https://doi.org/" + doi, safe=":/"), timeout=timeout)
        if response.ok:
            work = response.json()
            open_access = work.get("open_access") or {}
            if open_access.get("oa_url"):
                add_candidate(
                    rows,
                    seen,
                    paper,
                    open_access.get("oa_url", ""),
                    "openalex_location",
                    "oa_pdf" if str(open_access.get("oa_url", "")).lower().endswith(".pdf") else "oa_html_fulltext",
                    "pdf" if str(open_access.get("oa_url", "")).lower().endswith(".pdf") else "html_or_pdf",
                    "open_access",
                    "yes",
                    "no",
                    110,
                    "openalex_live_open_access",
                    "OpenAlex open_access.oa_url.",
                )
            locations = [work.get("primary_location") or {}] + list(work.get("locations") or [])
            for location in locations:
                source = location.get("source") or {}
                is_oa = "yes" if location.get("is_oa") else "no"
                pdf_url = location.get("pdf_url", "")
                landing = location.get("landing_page_url", "")
                if pdf_url:
                    add_candidate(
                        rows,
                        seen,
                        paper,
                        pdf_url,
                        "openalex_location",
                        "oa_pdf" if is_oa == "yes" else "institutional_pdf",
                        "pdf",
                        "open_access" if is_oa == "yes" else "institutional_access",
                        is_oa,
                        "no" if is_oa == "yes" else "yes",
                        112 if is_oa == "yes" else 102,
                        "openalex_live_location",
                        f"OpenAlex pdf_url from {source.get('display_name', 'unknown source')}.",
                    )
                if landing:
                    add_candidate(
                        rows,
                        seen,
                        paper,
                        landing,
                        "openalex_location",
                        "oa_html_fulltext" if is_oa == "yes" else "publisher_landing_page",
                        "html",
                        "open_access" if is_oa == "yes" else "publisher_landing",
                        is_oa,
                        "unknown",
                        88 if is_oa == "yes" else 62,
                        "openalex_live_location",
                        f"OpenAlex landing_page_url from {source.get('display_name', 'unknown source')}.",
                    )
    except (requests.RequestException, ValueError):
        pass

    try:
        response = session.get("https://api.crossref.org/works/" + quote(doi, safe=""), timeout=timeout)
        if response.ok:
            message = response.json().get("message", {})
            for link in message.get("link") or []:
                url = link.get("URL", "")
                content_type = str(link.get("content-type", "")).lower()
                is_pdf = "pdf" in content_type or "pdf" in str(url).lower()
                add_candidate(
                    rows,
                    seen,
                    paper,
                    url,
                    "crossref_link",
                    "crossref_link",
                    "pdf" if is_pdf else "html_or_pdf",
                    "unknown",
                    "unclear",
                    "unknown",
                    86 if is_pdf else 56,
                    "crossref_live_link",
                    f"Crossref link content-type={content_type}; intended={link.get('intended-application', '')}.",
                )
    except (requests.RequestException, ValueError):
        pass

    if not unpaywall_email:
        return
    try:
        response = session.get(f"https://api.unpaywall.org/v2/{quote(doi, safe='')}?email={quote(unpaywall_email)}", timeout=timeout)
        if response.ok:
            payload = response.json()
            locations = [payload.get("best_oa_location") or {}] + list(payload.get("oa_locations") or [])
            for location in locations:
                pdf_url = location.get("url_for_pdf", "")
                landing = location.get("url_for_landing_page", "")
                if pdf_url:
                    add_candidate(
                        rows,
                        seen,
                        paper,
                        pdf_url,
                        "unpaywall_location",
                        "oa_pdf",
                        "pdf",
                        "open_access",
                        "yes",
                        "no",
                        115,
                        "unpaywall_live_location",
                        "Unpaywall OA PDF URL.",
                    )
                if landing:
                    add_candidate(
                        rows,
                        seen,
                        paper,
                        landing,
                        "unpaywall_location",
                        "unpaywall_location",
                        "html",
                        "open_access",
                        "yes",
                        "no",
                        90,
                        "unpaywall_live_location",
                        "Unpaywall OA landing page.",
                    )
    except (requests.RequestException, ValueError):
        pass


def add_existing_manifest_candidate(rows: List[Dict[str, str]], seen: set[tuple[str, str, str]], paper: Dict[str, str], manifest_map: Dict[str, Dict[str, str]]) -> None:
    existing = manifest_map.get(str(paper.get("paper_id", "")).strip())
    if not existing:
        return
    for key in ["local_saved_path", "source_url", "final_url", "attempted_url", "selected_url"]:
        value = existing.get(key, "")
        if not value:
            continue
        is_local = not value.lower().startswith(("http://", "https://"))
        if is_local and not value.lower().endswith(".pdf"):
            continue
        add_candidate(
            rows,
            seen,
            paper,
            value,
            "previous_manifest",
            "local_pdf" if is_local and value.lower().endswith(".pdf") else "publisher_landing_page",
            "pdf" if value.lower().endswith(".pdf") else "html_or_pdf",
            "local_pdf" if is_local else "unknown",
            "unclear",
            "unknown",
            100 if is_local else 50,
            f"previous_manifest_{key}",
            "Previously recorded source path or URL.",
        )


def add_manual_required_candidate(rows: List[Dict[str, str]], seen: set[tuple[str, str, str]], paper: Dict[str, str]) -> None:
    add_candidate(
        rows,
        seen,
        paper,
        f"manual://{paper.get('paper_id', '')}",
        "manual_required",
        "manual_required",
        "pdf_or_html",
        "manual_required",
        "unclear",
        "unknown",
        1,
        "fallback_manual_request",
        "Fallback row for manual legal PDF/HTML acquisition if automatic direct access fails.",
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
    session = requests.Session()
    session.headers.update({"User-Agent": "srm-ml-screening/0.7 legal-fulltext-source-discovery"})

    for index, paper in enumerate(papers, start=1):
        add_local_pdf_candidates(candidates, seen, paper)
        add_existing_manifest_candidate(candidates, seen, paper, manifest_map)
        add_local_raw_metadata_candidates(candidates, seen, paper, openalex_map, crossref_map)
        add_doi_candidate(candidates, seen, paper)
        add_publisher_patterns(candidates, seen, paper)
        if not args.no_live_lookup:
            add_live_api_candidates(candidates, seen, paper, session, args.timeout, args.unpaywall_email)
            if index < len(papers):
                time.sleep(args.sleep)
        add_manual_required_candidate(candidates, seen, paper)

    candidates = sorted(
        candidates,
        key=lambda row: (
            str(row["paper_id"]),
            -safe_float(row["source_priority"], 0.0),
            row["candidate_source_type"],
            row["candidate_url"],
        ),
    )
    write_rows(Path(args.output), candidates)
    counts: Dict[str, int] = {}
    for row in candidates:
        key = row["candidate_source_type"] or "unknown"
        counts[key] = counts.get(key, 0) + 1
    print(f"Fulltext source candidates written: {Path(args.output)}")
    print(f"Papers considered: {len(papers)}")
    print(f"Candidate URLs/paths: {len(candidates)}")
    for key in sorted(counts):
        print(f"candidate_source_type.{key}: {counts[key]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
