"""Fetch and classify full-text source candidates without bypassing access controls."""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import re
import sys
import time
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple
from urllib.parse import urlparse

import requests

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from stage5_extraction_utils import analyze_text_quality, classify_source_quality, load_text_from_local_path


DEFAULT_CANDIDATES = ROOT / "data" / "processed" / "fulltext_source_candidates.csv"
DEFAULT_MANIFEST = ROOT / "data" / "processed" / "fulltext_fetch_manifest.csv"
DEFAULT_LOG = ROOT / "data" / "processed" / "fulltext_candidate_fetch_log.csv"
DEFAULT_OUTPUT_DIR = ROOT / "outputs" / "fulltext"

QUALITY_RANK = {
    "pdf_fulltext": 95,
    "html_fulltext": 90,
    "abstract_only": 60,
    "doi_landing_page": 30,
    "navigation_shell": 10,
    "redirect_or_forbidden": 0,
    "no_useful_content": 0,
    "unknown": 0,
}

MANIFEST_REQUIRED_COLUMNS = [
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
    "selected_url",
    "local_path",
    "has_text_content",
    "usable_for_extraction",
    "fetch_notes",
]

MANIFEST_EXTRA_COLUMNS = [
    "source_quality_type",
    "source_quality_score",
    "allowed_extraction_scope",
    "extraction_strategy",
    "recommended_next_action",
]

LOG_COLUMNS = [
    "paper_id",
    "doi",
    "title",
    "candidate_url",
    "candidate_source_type",
    "candidate_priority",
    "expected_content_type",
    "fetch_status",
    "http_status",
    "final_url",
    "content_type",
    "content_length",
    "local_saved_path",
    "source_quality_type",
    "source_quality_score",
    "has_useful_text",
    "ready_for_extraction",
    "retry_recommended",
    "failure_reason",
    "notes",
    "fetch_time",
]

PAYWALL_MARKERS = [
    "purchase access",
    "institutional access",
    "sign in through your institution",
    "subscribe to access",
    "rent or buy",
    "access through your institution",
    "get access",
]

REDIRECT_MARKERS = [
    "redirecting",
    "just a moment",
    "enable javascript",
    "checking your browser",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Fetch full-text candidate URLs and update the stage4 manifest.")
    parser.add_argument("--candidates", default=str(DEFAULT_CANDIDATES))
    parser.add_argument("--manifest", default=str(DEFAULT_MANIFEST))
    parser.add_argument("--log", default=str(DEFAULT_LOG))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--limit", type=int, default=20, help="Maximum number of papers to process.")
    parser.add_argument("--max-candidates-per-paper", type=int, default=6)
    parser.add_argument("--retry-failed", action="store_true")
    parser.add_argument("--skip-existing", action="store_true", default=True)
    parser.add_argument("--timeout", type=int, default=30)
    parser.add_argument("--sleep", type=float, default=0.5)
    return parser.parse_args()


def read_rows(path: Path) -> List[Dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def write_rows(path: Path, rows: Sequence[Dict[str, str]], columns: Sequence[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(columns), extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def safe_float(value: str, default: float = 0.0) -> float:
    try:
        return float(str(value or "").strip())
    except ValueError:
        return default


def safe_int(value: str, default: int = 0) -> int:
    try:
        return int(str(value or "").strip())
    except ValueError:
        return default


def safe_filename(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "_", value or "").strip("_")[:160] or "source"


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


def normalize_manifest_rows(rows: Iterable[Dict[str, str]]) -> Tuple[List[str], Dict[str, Dict[str, str]]]:
    all_columns = list(dict.fromkeys(MANIFEST_REQUIRED_COLUMNS + MANIFEST_EXTRA_COLUMNS))
    by_id: Dict[str, Dict[str, str]] = {}
    for row in rows:
        paper_id = str(row.get("paper_id", "")).strip()
        if not paper_id:
            continue
        normalized = {column: row.get(column, "") for column in all_columns}
        normalized["source_url"] = normalized["source_url"] or row.get("selected_url", "")
        normalized["attempted_url"] = normalized["attempted_url"] or normalized["source_url"]
        normalized["local_saved_path"] = normalized["local_saved_path"] or row.get("local_path", "")
        normalized["selected_url"] = normalized["selected_url"] or normalized["source_url"]
        normalized["local_path"] = normalized["local_path"] or normalized["local_saved_path"]
        normalized["has_text_content"] = normalized["has_text_content"] or normalized["has_useful_text"]
        normalized["usable_for_extraction"] = normalized["usable_for_extraction"] or normalized["ready_for_extraction"]
        normalized["fetch_notes"] = normalized["fetch_notes"] or normalized["notes"] or normalized["failure_reason"]
        by_id[paper_id] = normalized
    return all_columns, by_id


def group_candidates(rows: List[Dict[str, str]], limit: int, max_per_paper: int) -> Dict[str, List[Dict[str, str]]]:
    grouped: Dict[str, List[Dict[str, str]]] = {}
    for row in rows:
        paper_id = str(row.get("paper_id", "")).strip()
        if not paper_id:
            continue
        grouped.setdefault(paper_id, []).append(row)
    ordered: Dict[str, List[Dict[str, str]]] = {}
    for paper_id, candidates in grouped.items():
        local_candidates = [row for row in candidates if is_local_candidate(row)]
        remote_candidates = [row for row in candidates if not is_local_candidate(row)]
        deduped_remote: Dict[str, Dict[str, str]] = {}
        for row in remote_candidates:
            url = str(row.get("candidate_url", "")).strip().lower()
            if not url:
                continue
            previous = deduped_remote.get(url)
            if previous is None or safe_float(row.get("candidate_priority", ""), 0.0) > safe_float(previous.get("candidate_priority", ""), 0.0):
                deduped_remote[url] = row
        sorted_remote = sorted(
            deduped_remote.values(),
            key=lambda row: -safe_float(row.get("candidate_priority", ""), 0.0),
        )
        sorted_local = sorted(
            local_candidates,
            key=lambda row: -safe_float(row.get("candidate_priority", ""), 0.0),
        )
        # Local manual PDF paths are logged for human handoff, but they should
        # not consume the finite HTTP fetch budget for each paper.
        ordered[paper_id] = sorted_remote[:max_per_paper] + sorted_local
    if limit > 0:
        ordered = dict(list(ordered.items())[:limit])
    return ordered


def is_http_url(url: str) -> bool:
    return url.lower().startswith(("http://", "https://"))


def is_local_candidate(row: Dict[str, str]) -> bool:
    return row.get("candidate_source_type", "") == "local_pdf_candidate"


def classify_saved_content(
    manifest_like_row: Dict[str, str],
    local_saved_path: str,
) -> Dict[str, str]:
    text = load_text_from_local_path(ROOT / local_saved_path)
    quality = analyze_text_quality(text)
    quality["best_local_saved_path"] = local_saved_path
    quality["text"] = text
    classification = classify_source_quality(manifest_like_row, quality)
    return {
        **classification,
        "has_useful_text": "yes" if classification["source_quality_type"] in {"pdf_fulltext", "html_fulltext", "abstract_only", "doi_landing_page"} else "no",
        "ready_for_extraction": "yes" if classification["source_quality_type"] in {"pdf_fulltext", "html_fulltext", "abstract_only"} else "no",
    }


def classify_response_without_saving(response: requests.Response) -> Tuple[str, str, str]:
    status_code = response.status_code
    if status_code == 403:
        return "forbidden", "forbidden_http_403", "no"
    if status_code in {401, 402}:
        return "non_retryable_failure", f"http_{status_code}_access_limited", "no"
    if status_code == 404:
        return "non_retryable_failure", "not_found_http_404", "no"
    if status_code in {408, 429} or 500 <= status_code <= 599:
        return "retryable_failure", f"http_{status_code}", "yes"
    if 400 <= status_code <= 499:
        return "non_retryable_failure", f"http_{status_code}", "no"
    return "", "", "no"


def looks_like_redirect_or_paywall(content: bytes) -> Tuple[bool, bool]:
    snippet = content[:4000].decode("utf-8", errors="ignore").lower()
    redirect_like = any(marker in snippet for marker in REDIRECT_MARKERS)
    paywall_like = any(marker in snippet for marker in PAYWALL_MARKERS)
    return redirect_like, paywall_like


def fetch_one(
    candidate: Dict[str, str],
    session: requests.Session,
    output_dir: Path,
    timeout: int,
) -> Dict[str, str]:
    now = dt.datetime.now(dt.timezone.utc).astimezone().isoformat(timespec="seconds")
    row = {column: "" for column in LOG_COLUMNS}
    row.update({key: candidate.get(key, "") for key in [
        "paper_id",
        "doi",
        "title",
        "candidate_url",
        "candidate_source_type",
        "candidate_priority",
        "expected_content_type",
    ]})
    row["fetch_time"] = now
    row["retry_recommended"] = "no"
    row["has_useful_text"] = "no"
    row["ready_for_extraction"] = "no"
    row["source_quality_score"] = "0"

    url = candidate.get("candidate_url", "")
    if is_local_candidate(candidate):
        row["fetch_status"] = "local_candidate_not_fetched"
        row["failure_reason"] = "handled_by_ingest_local_pdfs"
        row["source_quality_type"] = "local_pdf_candidate"
        row["notes"] = "Local PDF candidates are not fetched over HTTP."
        return row

    if not is_http_url(url):
        row["fetch_status"] = "non_retryable_failure"
        row["failure_reason"] = "unsupported_url_scheme"
        row["notes"] = "Only legal http(s) sources are fetched by this script."
        return row

    try:
        response = session.get(url, timeout=timeout, allow_redirects=True)
    except requests.Timeout:
        row["fetch_status"] = "timeout"
        row["failure_reason"] = "requests_timeout"
        row["retry_recommended"] = "yes"
        row["notes"] = "HTTP request timed out."
        return row
    except requests.RequestException as exc:
        row["fetch_status"] = "retryable_failure"
        row["failure_reason"] = f"request_error:{type(exc).__name__}"
        row["retry_recommended"] = "yes"
        row["notes"] = f"Request exception: {type(exc).__name__}"
        return row

    row["http_status"] = str(response.status_code)
    row["final_url"] = response.url
    row["content_type"] = response.headers.get("Content-Type", "")
    row["content_length"] = str(len(response.content))

    status, reason, retry = classify_response_without_saving(response)
    if status:
        row["fetch_status"] = status
        row["failure_reason"] = reason
        row["retry_recommended"] = retry
        row["notes"] = f"HTTP status {response.status_code}; no access bypass attempted."
        row["source_quality_type"] = "redirect_or_forbidden" if status == "forbidden" else "no_useful_content"
        row["source_quality_score"] = "0"
        return row

    redirect_like, paywall_like = looks_like_redirect_or_paywall(response.content)
    extension = infer_extension(row["content_type"], response.url)
    local_name = f"{safe_filename(candidate.get('paper_id', 'paper'))}_{safe_filename(candidate.get('candidate_source_type', 'source'))}_{safe_filename(str(candidate.get('candidate_priority', '')))}{extension}"
    local_path = output_dir / local_name
    output_dir.mkdir(parents=True, exist_ok=True)
    local_path.write_bytes(response.content)
    row["local_saved_path"] = str(local_path.relative_to(ROOT))

    if paywall_like:
        row["fetch_status"] = "non_retryable_failure"
        row["failure_reason"] = "paywall_or_institutional_access_required"
        row["retry_recommended"] = "no"
        row["notes"] = "Page indicates access is restricted; no bypass attempted."
        row["source_quality_type"] = "redirect_or_forbidden"
        row["source_quality_score"] = "0"
        return row

    if redirect_like:
        text = load_text_from_local_path(local_path)
        if len(text) < 1000:
            row["fetch_status"] = "redirect_only"
            row["failure_reason"] = "redirect_or_gate_page"
            row["retry_recommended"] = "yes"
            row["notes"] = "Fetched page appears to be redirect/gate content only."
            row["source_quality_type"] = "redirect_or_forbidden"
            row["source_quality_score"] = "0"
            return row

    manifest_like = {
        "fetch_status": "success",
        "url_source": candidate.get("candidate_source_type", ""),
        "content_type": row["content_type"],
    }
    classification = classify_saved_content(manifest_like, row["local_saved_path"])
    row.update(classification)

    source_quality_type = row.get("source_quality_type", "")
    if source_quality_type in {"pdf_fulltext", "html_fulltext"}:
        row["fetch_status"] = "success"
        row["failure_reason"] = ""
        row["notes"] = f"Fetched {source_quality_type}; ready for metadata and experimental extraction."
    elif source_quality_type == "abstract_only":
        row["fetch_status"] = "success"
        row["failure_reason"] = ""
        row["notes"] = "Fetched abstract-only page; not suitable for quantitative experimental extraction."
    elif source_quality_type == "doi_landing_page":
        row["fetch_status"] = "no_useful_content"
        row["failure_reason"] = "doi_landing_page_only"
        row["ready_for_extraction"] = "no"
        row["notes"] = "Landing page only; find PDF/HTML fulltext before experimental extraction."
    elif source_quality_type == "navigation_shell":
        row["fetch_status"] = "no_useful_content"
        row["failure_reason"] = "navigation_shell"
        row["ready_for_extraction"] = "no"
        row["notes"] = "Navigation shell without sufficient SRM experimental text."
    else:
        row["fetch_status"] = "no_useful_content"
        row["failure_reason"] = "no_useful_fulltext_signal"
        row["ready_for_extraction"] = "no"
        row["notes"] = "Fetched content did not contain enough useful SRM text."
    return row


def should_skip_paper(existing: Optional[Dict[str, str]], skip_existing: bool, retry_failed: bool) -> bool:
    if not existing or not skip_existing:
        return False
    if retry_failed:
        return False
    source_quality_type = str(existing.get("source_quality_type", "")).strip()
    if source_quality_type in {"pdf_fulltext", "html_fulltext"}:
        return True
    return (
        str(existing.get("fetch_status", "")).strip() in {"success", "skipped_existing"}
        and str(existing.get("has_useful_text", "")).strip().lower() == "yes"
        and str(existing.get("ready_for_extraction", "")).strip().lower() == "yes"
        and source_quality_type in {"pdf_fulltext", "html_fulltext"}
    )


def log_skipped(candidate: Dict[str, str], existing: Dict[str, str]) -> Dict[str, str]:
    row = {column: "" for column in LOG_COLUMNS}
    row.update({key: candidate.get(key, "") for key in [
        "paper_id",
        "doi",
        "title",
        "candidate_url",
        "candidate_source_type",
        "candidate_priority",
        "expected_content_type",
    ]})
    row["fetch_status"] = "skipped_existing"
    row["source_quality_type"] = existing.get("source_quality_type", "")
    row["source_quality_score"] = existing.get("source_quality_score", "")
    row["local_saved_path"] = existing.get("local_saved_path", "")
    row["ready_for_extraction"] = existing.get("ready_for_extraction", "")
    row["has_useful_text"] = existing.get("has_useful_text", "")
    row["notes"] = "Existing PDF/HTML fulltext manifest row skipped."
    row["fetch_time"] = dt.datetime.now(dt.timezone.utc).astimezone().isoformat(timespec="seconds")
    return row


def best_log_row(rows: Sequence[Dict[str, str]], existing: Optional[Dict[str, str]]) -> Optional[Dict[str, str]]:
    best: Optional[Dict[str, str]] = None
    if existing:
        existing_quality_type = str(existing.get("source_quality_type", "") or "").strip()
        best = {
            "paper_id": existing.get("paper_id", ""),
            "doi": existing.get("doi", ""),
            "title": existing.get("title", ""),
            "candidate_url": existing.get("source_url", ""),
            "candidate_source_type": existing.get("url_source", ""),
            "fetch_status": existing.get("fetch_status", ""),
            "http_status": existing.get("http_status", ""),
            "final_url": existing.get("final_url", ""),
            "content_type": existing.get("content_type", ""),
            "content_length": existing.get("content_length", ""),
            "local_saved_path": existing.get("local_saved_path", ""),
            "source_quality_type": existing_quality_type,
            "source_quality_score": existing.get("source_quality_score", "-1" if not existing_quality_type else "0"),
            "has_useful_text": existing.get("has_useful_text", ""),
            "ready_for_extraction": existing.get("ready_for_extraction", ""),
            "retry_recommended": existing.get("retry_recommended", ""),
            "failure_reason": existing.get("failure_reason", ""),
            "notes": existing.get("notes", ""),
        }
    for row in rows:
        if row.get("fetch_status") == "local_candidate_not_fetched":
            continue
        current_score = safe_float(row.get("source_quality_score", ""), QUALITY_RANK.get(row.get("source_quality_type", ""), 0))
        best_score = safe_float(best.get("source_quality_score", "") if best else "", QUALITY_RANK.get(best.get("source_quality_type", "") if best else "", 0))
        if best is None or current_score > best_score:
            best = row
        elif best is not None and current_score == best_score:
            best_quality = str(best.get("source_quality_type", "") or "").strip()
            current_quality = str(row.get("source_quality_type", "") or "").strip()
            if current_quality and not best_quality:
                best = row
            elif current_quality == "abstract_only" and best_quality not in {"pdf_fulltext", "html_fulltext", "abstract_only"}:
                best = row
            elif current_quality in {"redirect_or_forbidden", "no_useful_content"} and best_quality == "":
                best = row
    return best


def update_manifest_row(existing: Optional[Dict[str, str]], candidate: Dict[str, str], best: Dict[str, str]) -> Dict[str, str]:
    all_columns = list(dict.fromkeys(MANIFEST_REQUIRED_COLUMNS + MANIFEST_EXTRA_COLUMNS))
    row = {column: (existing or {}).get(column, "") for column in all_columns}
    row.update(
        {
            "paper_id": candidate.get("paper_id", row.get("paper_id", "")),
            "doi": candidate.get("doi", row.get("doi", "")),
            "title": candidate.get("title", row.get("title", "")),
            "source_url": best.get("candidate_url", row.get("source_url", "")),
            "attempted_url": best.get("candidate_url", row.get("attempted_url", "")),
            "final_url": best.get("final_url", row.get("final_url", "")),
            "url_source": best.get("candidate_source_type", row.get("url_source", "")),
            "fetch_status": best.get("fetch_status", row.get("fetch_status", "")),
            "last_fetch_time": best.get("fetch_time", row.get("last_fetch_time", "")),
            "retry_recommended": best.get("retry_recommended", "no"),
            "failure_reason": best.get("failure_reason", ""),
            "local_saved_path": best.get("local_saved_path", row.get("local_saved_path", "")),
            "content_type": best.get("content_type", row.get("content_type", "")),
            "content_length": best.get("content_length", row.get("content_length", "0")),
            "has_useful_text": best.get("has_useful_text", "") or "no",
            "ready_for_extraction": best.get("ready_for_extraction", "") or "no",
            "notes": best.get("notes", ""),
            "http_status": best.get("http_status", ""),
            "reused_existing": "no",
            "source_quality_type": best.get("source_quality_type", row.get("source_quality_type", "")),
            "source_quality_score": best.get("source_quality_score", row.get("source_quality_score", "0")),
            "allowed_extraction_scope": best.get("allowed_extraction_scope", row.get("allowed_extraction_scope", "")),
            "extraction_strategy": best.get("extraction_strategy", row.get("extraction_strategy", "")),
            "recommended_next_action": best.get("recommended_next_action", row.get("recommended_next_action", "")),
        }
    )
    row["fetch_attempts"] = str(safe_int(row.get("fetch_attempts", "0"), 0) + 1)
    row["selected_url"] = row.get("source_url", "")
    row["local_path"] = row.get("local_saved_path", "")
    row["has_text_content"] = row.get("has_useful_text", "")
    row["usable_for_extraction"] = row.get("ready_for_extraction", "")
    row["fetch_notes"] = row.get("notes", "") or row.get("failure_reason", "")
    return row


def main() -> int:
    args = parse_args()
    candidates = read_rows(Path(args.candidates))
    manifest_columns, manifest_by_id = normalize_manifest_rows(read_rows(Path(args.manifest)))
    all_manifest_columns = list(dict.fromkeys(manifest_columns + MANIFEST_EXTRA_COLUMNS))
    grouped = group_candidates(candidates, args.limit, args.max_candidates_per_paper)

    session = requests.Session()
    session.headers.update({"User-Agent": "srm-ml-screening/0.5 legal-fulltext-acquisition"})
    output_dir = Path(args.output_dir)

    log_rows: List[Dict[str, str]] = []
    updated_manifest = dict(manifest_by_id)

    for paper_id, candidate_rows in grouped.items():
        existing = manifest_by_id.get(paper_id)
        if should_skip_paper(existing, args.skip_existing, args.retry_failed):
            log_rows.append(log_skipped(candidate_rows[0], existing or {}))
            continue

        per_paper_logs: List[Dict[str, str]] = []
        for candidate in candidate_rows:
            result = fetch_one(candidate, session, output_dir, args.timeout)
            per_paper_logs.append(result)
            log_rows.append(result)
            time.sleep(args.sleep)
            if result.get("source_quality_type") in {"pdf_fulltext", "html_fulltext"}:
                break

        best = best_log_row(per_paper_logs, existing)
        if best:
            updated_manifest[paper_id] = update_manifest_row(existing, candidate_rows[0], best)

    # Preserve manifest rows outside the test batch.
    manifest_rows = [updated_manifest[paper_id] for paper_id in sorted(updated_manifest)]
    write_rows(Path(args.log), log_rows, LOG_COLUMNS)
    write_rows(Path(args.manifest), manifest_rows, all_manifest_columns)

    status_counts: Dict[str, int] = {}
    quality_counts: Dict[str, int] = {}
    for row in log_rows:
        status_counts[row.get("fetch_status", "") or "unknown"] = status_counts.get(row.get("fetch_status", "") or "unknown", 0) + 1
        quality_counts[row.get("source_quality_type", "") or "unknown"] = quality_counts.get(row.get("source_quality_type", "") or "unknown", 0) + 1
    print(f"Candidate fetch log written: {Path(args.log)}")
    print(f"Manifest updated: {Path(args.manifest)}")
    print(f"Papers processed: {len(grouped)}")
    print(f"Candidate attempts logged: {len(log_rows)}")
    for status in sorted(status_counts):
        print(f"fetch_status.{status}: {status_counts[status]}")
    for quality in sorted(quality_counts):
        print(f"source_quality_type.{quality}: {quality_counts[quality]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
