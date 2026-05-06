"""Download publisher PDFs listed in a literature table when access is available.

The downloader is not limited to open-access records. It attempts normal
publisher PDF URLs and DOI-derived PDF URLs using the current network/session.
It does not bypass paywalls: only responses that are actually PDFs are saved.
HTML login pages, redirect shells, 403 pages, and abstract pages are logged and
discarded.
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence
from urllib.parse import quote, urlparse

import requests


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_INPUT = ROOT / "data" / "processed" / "manual_pdf_request_list.csv"
DEFAULT_SCORED = ROOT / "data" / "processed" / "candidate_papers_high_if_scored.csv"
DEFAULT_SOURCE_CANDIDATES = ROOT / "data" / "processed" / "fulltext_source_candidates.csv"
DEFAULT_LOG = ROOT / "data" / "processed" / "pdf_download_log.csv"
DEFAULT_PDF_DIR = ROOT / "data" / "raw" / "pdfs"

LOG_COLUMNS = [
    "paper_id",
    "doi",
    "title",
    "candidate_url",
    "candidate_source_type",
    "attempt_order",
    "download_status",
    "http_status",
    "final_url",
    "content_type",
    "content_length",
    "saved_pdf_path",
    "pdf_validated",
    "failure_reason",
    "access_note",
    "download_time",
]

PAYWALL_MARKERS = [
    "purchase access",
    "institutional access",
    "sign in through your institution",
    "subscribe to access",
    "rent or buy",
    "access through your institution",
    "get access",
    "login",
    "shibboleth",
]

REDIRECT_MARKERS = [
    "redirecting",
    "just a moment",
    "enable javascript",
    "checking your browser",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Download accessible publisher PDFs from a literature table.")
    parser.add_argument("--input", default=str(DEFAULT_INPUT), help="CSV table containing paper_id, doi, and title.")
    parser.add_argument("--scored", default=str(DEFAULT_SCORED), help="Scored candidate pool for metadata enrichment.")
    parser.add_argument("--source-candidates", default=str(DEFAULT_SOURCE_CANDIDATES), help="Fulltext source candidates CSV.")
    parser.add_argument("--output-log", default=str(DEFAULT_LOG))
    parser.add_argument("--pdf-dir", default=str(DEFAULT_PDF_DIR))
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--max-candidates-per-paper", type=int, default=8)
    parser.add_argument("--timeout", type=int, default=45)
    parser.add_argument("--sleep", type=float, default=0.5)
    parser.add_argument("--overwrite", action="store_true", help="Overwrite an existing local PDF for the same paper_id.")
    parser.add_argument("--ingest-after-download", action="store_true", help="Run ingest_local_pdfs.py after downloading.")
    parser.add_argument("--max-mb", type=float, default=80.0, help="Safety limit for a single PDF response.")
    parser.add_argument("--cookies", default="", help="Optional Netscape cookie.txt file exported from a browser session.")
    parser.add_argument("--cookie-header", default="", help="Optional raw Cookie header string for publisher access.")
    parser.add_argument("--no-live-metadata", action="store_true", help="Disable live OpenAlex/Crossref DOI metadata lookups.")
    return parser.parse_args()


def read_rows(path: Path) -> List[Dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def resolve_repo_path(value: str | Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else ROOT / path


def write_rows(path: Path, rows: Sequence[Dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=LOG_COLUMNS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def load_netscape_cookies(session: requests.Session, cookie_path: Path) -> int:
    if not cookie_path.exists():
        raise FileNotFoundError(f"Cookie file not found: {cookie_path}")
    loaded = 0
    for raw_line in cookie_path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split("\t")
        if len(parts) != 7:
            continue
        domain, _include_subdomains, path, secure, _expires, name, value = parts
        session.cookies.set(name, value, domain=domain.lstrip("."), path=path or "/", secure=secure.upper() == "TRUE")
        loaded += 1
    return loaded


def normalize_doi(value: str) -> str:
    value = (value or "").strip()
    value = re.sub(r"^https?://(dx\.)?doi\.org/", "", value, flags=re.IGNORECASE)
    return value.lower().strip()


def doi_safe_name(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "_", normalize_doi(value)).strip("_")


def safe_filename(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "_", value or "").strip("_")[:180] or "paper"


def safe_float(value: str, default: float = 0.0) -> float:
    try:
        return float(str(value or "").strip())
    except ValueError:
        return default


def build_lookup(rows: Iterable[Dict[str, str]], key: str) -> Dict[str, Dict[str, str]]:
    lookup: Dict[str, Dict[str, str]] = {}
    for row in rows:
        value = str(row.get(key, "")).strip()
        if value and value not in lookup:
            lookup[value] = row
    return lookup


def enrich_input_rows(input_rows: List[Dict[str, str]], scored_rows: List[Dict[str, str]]) -> List[Dict[str, str]]:
    by_id = build_lookup(scored_rows, "paper_id")
    by_doi = {normalize_doi(row.get("doi", "")): row for row in scored_rows if normalize_doi(row.get("doi", ""))}
    enriched: List[Dict[str, str]] = []
    for row in input_rows:
        paper_id = str(row.get("paper_id", "")).strip()
        doi = normalize_doi(row.get("doi", ""))
        base = by_id.get(paper_id) or by_doi.get(doi) or {}
        merged = dict(base)
        merged.update({key: value for key, value in row.items() if value not in {None, ""}})
        enriched.append(merged)
    return enriched


def publication_year(row: Dict[str, str]) -> str:
    year = str(row.get("publication_year", "")).strip()
    if "." in year:
        year = year.split(".", 1)[0]
    return year


def rsc_journal_code(doi: str) -> str:
    suffix = doi.split("/", 1)[1] if "/" in doi else ""
    return suffix[2:4] if len(suffix) >= 4 else ""


def publisher_pdf_candidates(row: Dict[str, str]) -> List[Dict[str, str]]:
    doi = normalize_doi(row.get("doi", ""))
    year = publication_year(row)
    candidates: List[Dict[str, str]] = []

    def add(url: str, source_type: str, priority: int) -> None:
        if url:
            candidates.append(
                {
                    "candidate_url": url,
                    "candidate_source_type": source_type,
                    "candidate_priority": str(priority),
                }
            )

    if not doi:
        return candidates

    quoted_doi = quote(doi, safe="/.")
    add(f"https://doi.org/{doi}", "doi_resolver_for_pdf_discovery", 30)

    if doi.startswith("10.1021/"):
        add(f"https://pubs.acs.org/doi/pdf/{doi}", "acs_pdf", 100)
    if doi.startswith("10.1039/"):
        suffix = doi.split("/", 1)[1]
        code = rsc_journal_code(doi)
        if year and code:
            add(f"https://pubs.rsc.org/en/content/articlepdf/{year}/{code}/{suffix}", "rsc_pdf", 100)
        if year:
            add(f"https://pubs.rsc.org/en/content/articlepdf/{year}/{suffix}", "rsc_pdf_legacy_pattern", 80)
    if doi.startswith("10.1016/"):
        add(f"https://www.sciencedirect.com/science/article/pii/{doi.split('/')[-1]}/pdfft?isDTMRedir=true&download=true", "sciencedirect_pdf_from_doi_suffix", 60)
    if doi.startswith("10.1007/") or doi.startswith("10.1186/"):
        add(f"https://link.springer.com/content/pdf/{quoted_doi}.pdf", "springer_pdf", 95)
    if doi.startswith("10.1002/") or doi.startswith("10.1111/"):
        add(f"https://onlinelibrary.wiley.com/doi/pdf/{doi}", "wiley_pdf", 95)
    if doi.startswith("10.1080/") or doi.startswith("10.1081/"):
        add(f"https://www.tandfonline.com/doi/pdf/{doi}", "tandf_pdf", 95)

    return candidates


def add_live_candidate(candidates: List[Dict[str, str]], url: str, source_type: str, priority: int, note: str = "") -> None:
    if not url:
        return
    if not str(url).lower().startswith(("http://", "https://")):
        return
    candidates.append(
        {
            "candidate_url": str(url),
            "candidate_source_type": source_type,
            "candidate_priority": str(priority),
            "source_note": note,
        }
    )


def live_metadata_pdf_candidates(row: Dict[str, str], session: requests.Session, timeout: int) -> List[Dict[str, str]]:
    doi = normalize_doi(row.get("doi", ""))
    if not doi:
        return []

    candidates: List[Dict[str, str]] = []
    openalex_url = "https://api.openalex.org/works/doi:" + quote("https://doi.org/" + doi, safe=":/")
    try:
        response = session.get(openalex_url, timeout=timeout)
        if response.ok:
            work = response.json()
            open_access = work.get("open_access") or {}
            add_live_candidate(
                candidates,
                open_access.get("oa_url", ""),
                "openalex_oa_url",
                90,
                "OpenAlex open_access.oa_url",
            )
            primary = work.get("primary_location") or {}
            add_live_candidate(
                candidates,
                primary.get("pdf_url", ""),
                "openalex_primary_pdf",
                108,
                "OpenAlex primary_location.pdf_url",
            )
            for location in work.get("locations") or []:
                source = location.get("source") or {}
                source_name = str(source.get("display_name", "unknown_source")).replace("\t", " ")
                priority = 112 if str(source.get("type", "")).lower() == "repository" else 106
                add_live_candidate(
                    candidates,
                    location.get("pdf_url", ""),
                    "openalex_repository_pdf" if priority == 112 else "openalex_location_pdf",
                    priority,
                    f"OpenAlex location pdf_url from {source_name}",
                )
    except (requests.RequestException, ValueError):
        pass

    crossref_url = "https://api.crossref.org/works/" + quote(doi, safe="")
    try:
        response = session.get(crossref_url, timeout=timeout)
        if response.ok:
            message = response.json().get("message", {})
            for link in message.get("link") or []:
                url = link.get("URL", "")
                content_type = str(link.get("content-type", "")).lower()
                intended = str(link.get("intended-application", ""))
                if "pdf" in content_type or "pdf" in url.lower():
                    add_live_candidate(
                        candidates,
                        url,
                        "crossref_pdf_link",
                        104,
                        f"Crossref link content-type={content_type}; intended={intended}",
                    )
    except (requests.RequestException, ValueError):
        pass

    return candidates


def source_table_pdf_candidates(row: Dict[str, str], source_rows: List[Dict[str, str]]) -> List[Dict[str, str]]:
    paper_id = str(row.get("paper_id", "")).strip()
    doi = normalize_doi(row.get("doi", ""))
    candidates: List[Dict[str, str]] = []
    for source in source_rows:
        same_paper = paper_id and str(source.get("paper_id", "")).strip() == paper_id
        same_doi = doi and normalize_doi(source.get("doi", "")) == doi
        if not (same_paper or same_doi):
            continue
        source_type = str(source.get("candidate_source_type", ""))
        expected = str(source.get("expected_content_type", "")).lower()
        url = str(source.get("candidate_url", "")).strip()
        if not url.lower().startswith(("http://", "https://")):
            continue
        if "pdf" not in expected and "pdf" not in source_type.lower():
            continue
        candidates.append(
            {
                "candidate_url": url,
                "candidate_source_type": source_type or "source_table_pdf_candidate",
                "candidate_priority": source.get("candidate_priority", "70"),
            }
        )
    return candidates


def resolve_elsevier_pdf_candidate(row: Dict[str, str], session: requests.Session, timeout: int) -> List[Dict[str, str]]:
    doi = normalize_doi(row.get("doi", ""))
    if not doi.startswith("10.1016/"):
        return []
    try:
        response = session.get(f"https://doi.org/{doi}", timeout=timeout, allow_redirects=True)
    except requests.RequestException:
        return []
    final_url = response.url or ""
    match = re.search(r"(?:pii/|retrieve/pii/)([A-Za-z0-9]+)", final_url)
    if not match:
        return []
    pii = match.group(1)
    return [
        {
            "candidate_url": f"https://www.sciencedirect.com/science/article/pii/{pii}/pdfft?isDTMRedir=true&download=true",
            "candidate_source_type": "sciencedirect_pdf_from_resolved_pii",
            "candidate_priority": "98",
        }
    ]


def dedupe_candidates(candidates: List[Dict[str, str]], max_candidates: int) -> List[Dict[str, str]]:
    best_by_url: Dict[str, Dict[str, str]] = {}
    for candidate in candidates:
        url = str(candidate.get("candidate_url", "")).strip()
        if not url.lower().startswith(("http://", "https://")):
            continue
        previous = best_by_url.get(url.lower())
        if previous is None or safe_float(candidate.get("candidate_priority", ""), 0.0) > safe_float(previous.get("candidate_priority", ""), 0.0):
            best_by_url[url.lower()] = candidate
    sorted_candidates = sorted(best_by_url.values(), key=lambda item: -safe_float(item.get("candidate_priority", ""), 0.0))
    return sorted_candidates[:max_candidates]


def is_pdf_response(content: bytes, content_type: str) -> bool:
    if content.startswith(b"%PDF-"):
        return True
    return "application/pdf" in (content_type or "").lower() and b"<html" not in content[:500].lower()


def classify_non_pdf(content: bytes, content_type: str) -> tuple[str, str]:
    snippet = content[:5000].decode("utf-8", errors="ignore").lower()
    if any(marker in snippet for marker in PAYWALL_MARKERS):
        return "login_or_paywall_html", "HTML page indicates login, subscription, or institutional access flow."
    if any(marker in snippet for marker in REDIRECT_MARKERS):
        return "redirect_or_gate_html", "HTML page appears to be redirect/gate content."
    if "html" in (content_type or "").lower() or "<html" in snippet[:1000]:
        return "not_pdf_html", "Server returned HTML rather than a PDF."
    return "not_pdf", "Server response did not validate as PDF."


def base_log(row: Dict[str, str], candidate: Dict[str, str], attempt_order: int) -> Dict[str, str]:
    return {
        "paper_id": row.get("paper_id", ""),
        "doi": row.get("doi", ""),
        "title": row.get("title", ""),
        "candidate_url": candidate.get("candidate_url", ""),
        "candidate_source_type": candidate.get("candidate_source_type", ""),
        "attempt_order": str(attempt_order),
        "download_time": dt.datetime.now(dt.timezone.utc).astimezone().isoformat(timespec="seconds"),
        "pdf_validated": "no",
    }


def target_pdf_path(row: Dict[str, str], pdf_dir: Path) -> Path:
    paper_id = str(row.get("paper_id", "")).strip()
    if paper_id:
        return pdf_dir / f"{safe_filename(paper_id)}.pdf"
    doi_name = doi_safe_name(row.get("doi", ""))
    return pdf_dir / f"{doi_name}.pdf"


def relative_to_root(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def download_candidate(
    row: Dict[str, str],
    candidate: Dict[str, str],
    attempt_order: int,
    session: requests.Session,
    pdf_dir: Path,
    timeout: int,
    overwrite: bool,
    max_bytes: int,
) -> Dict[str, str]:
    log = base_log(row, candidate, attempt_order)
    target = target_pdf_path(row, pdf_dir)
    if target.exists() and not overwrite:
        log.update(
            {
                "download_status": "skipped_existing",
                "saved_pdf_path": relative_to_root(target),
                "pdf_validated": "yes",
                "access_note": "Existing local PDF retained; use --overwrite to replace.",
            }
        )
        return log

    try:
        response = session.get(
            candidate["candidate_url"],
            timeout=timeout,
            allow_redirects=True,
            headers={"Accept": "application/pdf,application/octet-stream;q=0.9,text/html;q=0.8"},
        )
    except requests.Timeout:
        log.update({"download_status": "timeout", "failure_reason": "requests_timeout"})
        return log
    except requests.RequestException as exc:
        log.update({"download_status": "request_error", "failure_reason": type(exc).__name__})
        return log

    content = response.content
    content_type = response.headers.get("Content-Type", "")
    log.update(
        {
            "http_status": str(response.status_code),
            "final_url": response.url,
            "content_type": content_type,
            "content_length": str(len(content)),
        }
    )

    if response.status_code in {401, 402, 403}:
        log.update(
            {
                "download_status": "forbidden_or_login_required",
                "failure_reason": f"http_{response.status_code}",
                "access_note": "Publisher did not provide PDF to this HTTP session; no bypass attempted.",
            }
        )
        return log
    if response.status_code >= 400:
        log.update({"download_status": "http_error", "failure_reason": f"http_{response.status_code}"})
        return log
    if len(content) > max_bytes:
        log.update({"download_status": "too_large", "failure_reason": f"response_exceeds_{max_bytes}_bytes"})
        return log
    if not is_pdf_response(content, content_type):
        status, note = classify_non_pdf(content, content_type)
        log.update({"download_status": status, "failure_reason": "response_not_valid_pdf", "access_note": note})
        return log
    if len(content) < 5000:
        log.update({"download_status": "invalid_pdf_too_small", "failure_reason": "pdf_response_too_small"})
        return log

    pdf_dir.mkdir(parents=True, exist_ok=True)
    target.write_bytes(content)
    log.update(
        {
            "download_status": "downloaded_pdf",
            "saved_pdf_path": relative_to_root(target),
            "pdf_validated": "yes",
            "access_note": "Saved only after PDF signature/content validation.",
        }
    )
    return log


def should_stop_after_success(log: Dict[str, str]) -> bool:
    return log.get("download_status") in {"downloaded_pdf", "skipped_existing"}


def main() -> int:
    args = parse_args()
    input_rows = read_rows(resolve_repo_path(args.input))
    scored_rows = read_rows(resolve_repo_path(args.scored))
    source_rows = read_rows(resolve_repo_path(args.source_candidates))
    rows = enrich_input_rows(input_rows, scored_rows)
    if args.limit > 0:
        rows = rows[: args.limit]

    pdf_dir = resolve_repo_path(args.pdf_dir)
    max_bytes = int(args.max_mb * 1024 * 1024)
    session = requests.Session()
    session.headers.update(
        {
            "User-Agent": "srm-ml-screening/0.6 institutional-access-pdf-downloader",
            "Accept-Language": "en-US,en;q=0.9",
        }
    )
    if args.cookie_header:
        session.headers.update({"Cookie": args.cookie_header})
    loaded_cookies = 0
    if args.cookies:
        loaded_cookies = load_netscape_cookies(session, resolve_repo_path(args.cookies))

    log_rows: List[Dict[str, str]] = []
    for row in rows:
        candidates = []
        candidates.extend(source_table_pdf_candidates(row, source_rows))
        if not args.no_live_metadata:
            candidates.extend(live_metadata_pdf_candidates(row, session, args.timeout))
        candidates.extend(publisher_pdf_candidates(row))
        candidates.extend(resolve_elsevier_pdf_candidate(row, session, args.timeout))
        candidates = dedupe_candidates(candidates, args.max_candidates_per_paper)
        if not candidates:
            log_rows.append(
                {
                    "paper_id": row.get("paper_id", ""),
                    "doi": row.get("doi", ""),
                    "title": row.get("title", ""),
                    "download_status": "no_candidate_url",
                    "failure_reason": "no_pdf_candidate_generated",
                    "download_time": dt.datetime.now(dt.timezone.utc).astimezone().isoformat(timespec="seconds"),
                    "pdf_validated": "no",
                }
            )
            continue
        for attempt_order, candidate in enumerate(candidates, start=1):
            log = download_candidate(
                row=row,
                candidate=candidate,
                attempt_order=attempt_order,
                session=session,
                pdf_dir=pdf_dir,
                timeout=args.timeout,
                overwrite=args.overwrite,
                max_bytes=max_bytes,
            )
            log_rows.append(log)
            if should_stop_after_success(log):
                break
            time.sleep(args.sleep)

    write_rows(resolve_repo_path(args.output_log), log_rows)

    if args.ingest_after_download:
        subprocess.run(
            [
                sys.executable,
                "src/ingest_local_pdfs.py",
                "--pdf-dir",
                relative_to_root(pdf_dir),
            ],
            cwd=ROOT,
            check=True,
        )

    status_counts: Dict[str, int] = {}
    for row in log_rows:
        status = row.get("download_status", "") or "unknown"
        status_counts[status] = status_counts.get(status, 0) + 1
    print(f"PDF download log written: {Path(args.output_log)}")
    if args.cookies:
        print(f"Browser cookies loaded: {loaded_cookies}")
    print(f"Papers considered: {len(rows)}")
    print(f"Attempts logged: {len(log_rows)}")
    for status in sorted(status_counts):
        print(f"{status}: {status_counts[status]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
