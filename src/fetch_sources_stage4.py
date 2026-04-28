"""Stage-4 source fetching for the SRM batch literature pipeline.

This script is the canonical stage-4 entrypoint. It is designed for
large-batch usage and emphasizes:

- resumable execution
- unified manifest output
- skip / retry behavior controlled by manifest state
- explicit failure categorization
- non-blocking handling of single-paper failures
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import time
from pathlib import Path
from typing import Dict, Iterable, List, Tuple
from urllib.parse import urlparse

import requests


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_INPUT = ROOT / "data" / "processed" / "eligible_high_if_pool.csv"
DEFAULT_MANIFEST = ROOT / "data" / "processed" / "fulltext_fetch_manifest.csv"
DEFAULT_OUTPUT_DIR = ROOT / "outputs" / "fulltext"
DEFAULT_OPENALEX_RAW = ROOT / "outputs" / "tables" / "openalex_raw_results.csv"
DEFAULT_CROSSREF_RAW = ROOT / "outputs" / "tables" / "crossref_raw_results.csv"

FETCH_SUCCESS_STATUSES = {"success", "skipped_existing"}
FETCH_RETRYABLE_STATUSES = {"timeout", "retryable_failure", "parse_failed", "redirect_only"}
FETCH_NON_RETRYABLE_STATUSES = {"forbidden", "no_useful_content", "non_retryable_failure"}

REDIRECT_MARKERS = [
    "redirecting",
    "just a moment",
    "enable javascript",
    "access through your institution",
    "checking your browser",
]

MANIFEST_COLUMNS = [
    "paper_id",
    "doi",
    "title",
    "document_type",
    "priority_rank",
    "priority_score",
    "journal",
    "journal_impact_factor",
    "source_url",
    "attempted_url",
    "final_url",
    "url_source",
    "fetch_status",
    "fetch_attempts",
    "last_fetch_time",
    "retry_recommended",
    "failure_reason",
    "local_saved_path",
    "content_type",
    "content_length",
    "has_useful_text",
    "ready_for_extraction",
    "notes",
    "http_status",
    "source_page_kind",
    "reused_existing",
    # Compatibility aliases for existing downstream scripts.
    "selected_url",
    "local_path",
    "has_text_content",
    "usable_for_extraction",
    "fetch_notes",
    "source_quality_type",
    "source_quality_score",
    "allowed_extraction_scope",
    "extraction_strategy",
    "recommended_next_action",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run stage4 source fetching for the SRM batch pipeline.")
    parser.add_argument("--input", default=str(DEFAULT_INPUT))
    parser.add_argument("--openalex-raw", default=str(DEFAULT_OPENALEX_RAW))
    parser.add_argument("--crossref-raw", default=str(DEFAULT_CROSSREF_RAW))
    parser.add_argument("--output", default=str(DEFAULT_MANIFEST))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--limit", type=int, default=50)
    parser.add_argument("--retry-failed", action="store_true", help="Retry records with retryable failed statuses.")
    parser.add_argument("--skip-existing", action="store_true", default=True, help="Skip already successful useful records.")
    parser.add_argument("--no-skip-existing", action="store_false", dest="skip_existing", help="Do not skip existing successes.")
    parser.add_argument(
        "--only-ready-pool",
        action="store_true",
        help="When the input is a broad scored pool, keep only journal articles in top/medium priority.",
    )
    parser.add_argument("--timeout", type=int, default=45)
    parser.add_argument("--sleep", type=float, default=0.5, help="Sleep seconds between HTTP attempts.")
    return parser.parse_args()


def read_rows(path: Path) -> List[Dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def write_rows(path: Path, rows: List[Dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=MANIFEST_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)


def normalize_doi(value: str) -> str:
    return (
        (value or "")
        .strip()
        .replace("https://doi.org/", "")
        .replace("http://doi.org/", "")
        .lower()
    )


def yes_no(flag: bool) -> str:
    return "yes" if flag else "no"


def safe_name(value: str) -> str:
    return "".join(ch if ch.isalnum() or ch in {"-", "_", "."} else "_" for ch in value)


def safe_int(value: str, default: int = 0) -> int:
    try:
        return int(str(value or "").strip())
    except ValueError:
        return default


def relative_path_string(path: Path | str) -> str:
    if not path:
        return ""
    path_obj = Path(path)
    try:
        if path_obj.is_absolute():
            return str(path_obj.resolve().relative_to(ROOT))
    except Exception:
        return str(path_obj)
    return str(path_obj)


def normalize_manifest(rows: Iterable[Dict[str, str]]) -> Dict[str, Dict[str, str]]:
    manifest: Dict[str, Dict[str, str]] = {}
    for row in rows:
        paper_id = str(row.get("paper_id", "")).strip()
        if not paper_id:
            continue
        normalized = {column: row.get(column, "") for column in MANIFEST_COLUMNS}
        normalized["source_url"] = normalized["source_url"] or row.get("selected_url", "")
        normalized["attempted_url"] = normalized["attempted_url"] or normalized["source_url"]
        normalized["local_saved_path"] = relative_path_string(
            normalized["local_saved_path"] or row.get("local_path", "")
        )
        normalized["has_useful_text"] = normalized["has_useful_text"] or row.get("has_text_content", "")
        normalized["ready_for_extraction"] = normalized["ready_for_extraction"] or row.get("usable_for_extraction", "")
        normalized["notes"] = normalized["notes"] or row.get("fetch_notes", "") or row.get("failure_reason", "")
        normalized["selected_url"] = normalized["selected_url"] or normalized["source_url"]
        normalized["local_path"] = normalized["local_path"] or normalized["local_saved_path"]
        normalized["has_text_content"] = normalized["has_text_content"] or normalized["has_useful_text"]
        normalized["usable_for_extraction"] = normalized["usable_for_extraction"] or normalized["ready_for_extraction"]
        normalized["fetch_notes"] = normalized["fetch_notes"] or normalized["notes"]
        normalized["retry_recommended"] = normalized["retry_recommended"] or (
            "yes" if normalized["fetch_status"] in FETCH_RETRYABLE_STATUSES else "no"
        )
        if not normalized["content_length"] and normalized["local_saved_path"]:
            local_candidate = ROOT / normalized["local_saved_path"]
            if local_candidate.exists():
                normalized["content_length"] = str(local_candidate.stat().st_size)
        normalized["content_length"] = normalized["content_length"] or "0"
        manifest[paper_id] = normalized
    return manifest


def filter_candidates(rows: List[Dict[str, str]], only_ready_pool: bool) -> List[Dict[str, str]]:
    if not only_ready_pool:
        return rows
    filtered: List[Dict[str, str]] = []
    for row in rows:
        doc_type = str(row.get("document_type", "")).strip().lower()
        label = str(row.get("final_priority_label", "")).strip().lower()
        if doc_type == "review":
            continue
        if label and label not in {"top_priority", "medium_priority"}:
            continue
        filtered.append(row)
    return filtered


def build_maps(
    openalex_rows: List[Dict[str, str]],
    crossref_rows: List[Dict[str, str]],
) -> Tuple[Dict[str, List[Dict[str, str]]], Dict[str, List[Dict[str, str]]]]:
    openalex_map: Dict[str, List[Dict[str, str]]] = {}
    crossref_map: Dict[str, List[Dict[str, str]]] = {}
    for row in openalex_rows:
        openalex_map.setdefault(normalize_doi(row.get("doi", "")), []).append(row)
    for row in crossref_rows:
        crossref_map.setdefault(normalize_doi(row.get("doi", "")), []).append(row)
    return openalex_map, crossref_map


def choose_urls(
    candidate: Dict[str, str],
    openalex_map: Dict[str, List[Dict[str, str]]],
    crossref_map: Dict[str, List[Dict[str, str]]],
) -> List[Tuple[str, str]]:
    urls: List[Tuple[str, str]] = []
    seen = set()

    def add_url(url: str, source: str) -> None:
        if url.startswith("http") and url not in seen:
            urls.append((url, source))
            seen.add(url)

    doi = normalize_doi(candidate.get("doi", ""))
    if doi:
        add_url(f"https://doi.org/{doi}", "doi_landing")

    for row in openalex_map.get(doi, []):
        for key in ["pdf_url", "paper_url", "landing_page_url"]:
            add_url(row.get(key, ""), f"openalex_{key}")

    for row in crossref_map.get(doi, []):
        add_url(row.get("paper_url", ""), "crossref_url")

    return urls


def infer_extension(content_type: str, url: str) -> str:
    content_type = (content_type or "").lower()
    path = urlparse(url).path.lower()
    if "pdf" in content_type or path.endswith(".pdf"):
        return ".pdf"
    if "html" in content_type or path.endswith(".html") or path.endswith(".htm"):
        return ".html"
    if "xml" in content_type:
        return ".xml"
    if "json" in content_type:
        return ".json"
    return ".bin"


def text_signal(content: bytes, content_type: str) -> Tuple[bool, str]:
    content_type = (content_type or "").lower()
    if "pdf" in content_type:
        return (len(content) >= 5000, "pdf")
    if "html" in content_type:
        return (len(content) >= 1500, "html")
    if "text" in content_type or "xml" in content_type or "json" in content_type:
        return (len(content) >= 1000, "text")
    return (len(content) >= 1500, "binary_or_unknown")


def looks_like_redirect_only(content: bytes, content_type: str, final_url: str) -> bool:
    content_type = (content_type or "").lower()
    if "html" not in content_type:
        return False
    snippet = content[:2500].decode("utf-8", errors="ignore").lower()
    if any(marker in snippet for marker in REDIRECT_MARKERS):
        return True
    if len(snippet.strip()) < 200 and any(token in final_url.lower() for token in ["login", "redirect", "shibboleth"]):
        return True
    return False


def classify_http_failure(status_code: int) -> Tuple[str, str, str]:
    if status_code == 403:
        return ("forbidden", "forbidden_http_403", "no")
    if status_code == 404:
        return ("non_retryable_failure", "not_found_http_404", "no")
    if status_code in {408, 429} or 500 <= status_code <= 599:
        return ("retryable_failure", f"http_{status_code}", "yes")
    if 400 <= status_code <= 499:
        return ("non_retryable_failure", f"http_{status_code}", "no")
    return ("retryable_failure", f"http_{status_code}", "yes")


def should_skip_existing(existing: Dict[str, str] | None, skip_existing: bool) -> bool:
    if not skip_existing or not existing:
        return False
    return (
        existing.get("fetch_status", "") in FETCH_SUCCESS_STATUSES
        and str(existing.get("has_useful_text", "")).strip().lower() == "yes"
        and str(existing.get("ready_for_extraction", "")).strip().lower() == "yes"
    )


def is_retryable_failure(existing: Dict[str, str] | None) -> bool:
    if not existing:
        return False
    status = str(existing.get("fetch_status", "")).strip()
    return status in FETCH_RETRYABLE_STATUSES


def base_row(candidate: Dict[str, str], previous: Dict[str, str] | None) -> Dict[str, str]:
    attempts = safe_int(previous.get("fetch_attempts", "0") if previous else "0")
    row = {column: "" for column in MANIFEST_COLUMNS}
    row.update(
        {
            "paper_id": candidate.get("paper_id", ""),
            "doi": candidate.get("doi", ""),
            "title": candidate.get("title", ""),
            "document_type": candidate.get("document_type", ""),
            "priority_rank": candidate.get("priority_rank", ""),
            "priority_score": candidate.get("priority_score", ""),
            "journal": candidate.get("journal", ""),
            "journal_impact_factor": candidate.get("journal_impact_factor", ""),
            "fetch_attempts": str(attempts),
            "retry_recommended": "yes",
            "content_length": "0",
            "has_useful_text": "no",
            "ready_for_extraction": "no",
            "notes": "",
            "reused_existing": "no",
        }
    )
    return row


def compatibility_fill(row: Dict[str, str]) -> Dict[str, str]:
    row["selected_url"] = row.get("source_url", "")
    row["local_path"] = row.get("local_saved_path", "")
    row["has_text_content"] = row.get("has_useful_text", "")
    row["usable_for_extraction"] = row.get("ready_for_extraction", "")
    row["fetch_notes"] = row.get("notes", "") or row.get("failure_reason", "")
    return row


def preserved_existing_row(existing: Dict[str, str], fetch_status_override: str | None = None) -> Dict[str, str]:
    row = {column: existing.get(column, "") for column in MANIFEST_COLUMNS}
    if fetch_status_override:
        row["fetch_status"] = fetch_status_override
    row["reused_existing"] = "yes"
    row["retry_recommended"] = "no" if row["fetch_status"] in FETCH_SUCCESS_STATUSES else row.get("retry_recommended", "")
    row["notes"] = row.get("notes", "") or row.get("failure_reason", "")
    return compatibility_fill(row)


def try_fetch_candidate(
    candidate: Dict[str, str],
    previous: Dict[str, str] | None,
    urls: List[Tuple[str, str]],
    session: requests.Session,
    timeout: int,
    output_dir: Path,
    sleep_seconds: float,
) -> Dict[str, str]:
    row = base_row(candidate, previous)
    row["fetch_attempts"] = str(safe_int(row["fetch_attempts"], 0) + 1)
    row["last_fetch_time"] = dt.datetime.now(dt.timezone.utc).astimezone().isoformat(timespec="seconds")

    if not urls:
        row["fetch_status"] = "non_retryable_failure"
        row["failure_reason"] = "no_candidate_url"
        row["retry_recommended"] = "no"
        row["notes"] = "No candidate source URL available from DOI/OpenAlex/Crossref."
        return compatibility_fill(row)

    last_failure_status = "non_retryable_failure"
    last_failure_reason = "no_candidate_url"
    last_retry_recommended = "no"
    last_notes = "No fetch attempt succeeded."

    for source_url, url_source in urls:
        row["source_url"] = source_url
        row["attempted_url"] = source_url
        row["url_source"] = url_source

        try:
            response = session.get(source_url, timeout=timeout, allow_redirects=True)
        except requests.Timeout:
            last_failure_status = "timeout"
            last_failure_reason = "requests_timeout"
            last_retry_recommended = "yes"
            last_notes = "HTTP request timed out."
            time.sleep(sleep_seconds)
            continue
        except requests.RequestException as exc:
            last_failure_status = "retryable_failure"
            last_failure_reason = f"request_error:{type(exc).__name__}"
            last_retry_recommended = "yes"
            last_notes = f"Request exception: {type(exc).__name__}"
            time.sleep(sleep_seconds)
            continue

        row["http_status"] = str(response.status_code)
        row["content_type"] = response.headers.get("Content-Type", "")
        row["content_length"] = str(len(response.content))
        row["final_url"] = response.url

        if response.status_code >= 400:
            last_failure_status, last_failure_reason, last_retry_recommended = classify_http_failure(response.status_code)
            last_notes = f"HTTP {response.status_code} from source."
            time.sleep(sleep_seconds)
            continue

        try:
            extension = infer_extension(row["content_type"], response.url)
            local_name = f"{safe_name(candidate.get('paper_id', 'paper'))}_{safe_name(url_source)}{extension}"
            local_path = output_dir / local_name
            local_path.write_bytes(response.content)
            row["local_saved_path"] = str(local_path.relative_to(ROOT))
        except Exception as exc:  # pragma: no cover - filesystem edge cases
            last_failure_status = "parse_failed"
            last_failure_reason = f"write_failed:{type(exc).__name__}"
            last_retry_recommended = "yes"
            last_notes = f"Failed to save content locally: {type(exc).__name__}"
            time.sleep(sleep_seconds)
            continue

        if looks_like_redirect_only(response.content, row["content_type"], response.url):
            row["source_page_kind"] = "redirect_page"
            row["fetch_status"] = "redirect_only"
            row["failure_reason"] = "redirect_or_gate_page"
            row["retry_recommended"] = "yes"
            row["has_useful_text"] = "no"
            row["ready_for_extraction"] = "no"
            row["notes"] = "Fetched page appears to be redirect/gate content only."
            return compatibility_fill(row)

        has_useful_text, page_kind = text_signal(response.content, row["content_type"])
        row["source_page_kind"] = page_kind
        row["has_useful_text"] = yes_no(has_useful_text)
        row["ready_for_extraction"] = yes_no(has_useful_text)

        if has_useful_text:
            row["fetch_status"] = "success"
            row["failure_reason"] = ""
            row["retry_recommended"] = "no"
            row["notes"] = "Content saved and judged useful for downstream extraction."
            return compatibility_fill(row)

        last_failure_status = "no_useful_content"
        last_failure_reason = "insufficient_text_signal"
        last_retry_recommended = "no"
        last_notes = "Content fetched but text signal was too weak for extraction."
        time.sleep(sleep_seconds)

    row["fetch_status"] = last_failure_status
    row["failure_reason"] = last_failure_reason
    row["retry_recommended"] = last_retry_recommended
    row["notes"] = last_notes
    row["has_useful_text"] = "no"
    row["ready_for_extraction"] = "no"
    return compatibility_fill(row)


def prepare_candidate_rows(input_path: Path, only_ready_pool: bool, limit: int) -> List[Dict[str, str]]:
    rows = read_rows(input_path)
    rows = filter_candidates(rows, only_ready_pool)
    if limit > 0:
        rows = rows[:limit]
    return rows


def summarize_statuses(rows: List[Dict[str, str]]) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    for row in rows:
        status = str(row.get("fetch_status", "")).strip() or "unknown"
        counts[status] = counts.get(status, 0) + 1
    return counts


def main() -> int:
    args = parse_args()
    input_path = Path(args.input)
    output_path = Path(args.output)
    output_dir = Path(args.output_dir)

    candidates = prepare_candidate_rows(input_path, args.only_ready_pool, args.limit)
    openalex_rows = read_rows(Path(args.openalex_raw))
    crossref_rows = read_rows(Path(args.crossref_raw))
    openalex_map, crossref_map = build_maps(openalex_rows, crossref_rows)
    existing_manifest = normalize_manifest(read_rows(output_path))

    output_dir.mkdir(parents=True, exist_ok=True)
    session = requests.Session()
    session.headers.update({"User-Agent": "srm-ml-screening/0.4 stage4 fetch manifest"})

    output_rows: List[Dict[str, str]] = []
    for candidate in candidates:
        paper_id = str(candidate.get("paper_id", "")).strip()
        existing = existing_manifest.get(paper_id)

        if should_skip_existing(existing, args.skip_existing):
            output_rows.append(preserved_existing_row(existing, fetch_status_override="skipped_existing"))
            continue

        if existing and existing.get("fetch_status", "") in FETCH_NON_RETRYABLE_STATUSES:
            output_rows.append(preserved_existing_row(existing))
            continue

        if existing and not args.retry_failed and existing.get("fetch_status", "") in FETCH_RETRYABLE_STATUSES:
            output_rows.append(preserved_existing_row(existing))
            continue

        urls = choose_urls(candidate, openalex_map, crossref_map)
        row = try_fetch_candidate(
            candidate=candidate,
            previous=existing,
            urls=urls,
            session=session,
            timeout=args.timeout,
            output_dir=output_dir,
            sleep_seconds=args.sleep,
        )
        output_rows.append({column: row.get(column, "") for column in MANIFEST_COLUMNS})

    write_rows(output_path, output_rows)

    status_counts = summarize_statuses(output_rows)
    ready_for_extraction = sum(
        1 for row in output_rows if str(row.get("ready_for_extraction", "")).strip().lower() == "yes"
    )
    print(f"Stage4 processed rows: {len(output_rows)}")
    print(f"Ready for extraction: {ready_for_extraction}")
    for status in sorted(status_counts):
        print(f"{status}: {status_counts[status]}")
    print(f"Manifest written to: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
