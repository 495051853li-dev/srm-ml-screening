"""Fetch legal full-text candidates using open or authorized institutional access.

The fetcher is intentionally conservative:

- It may save publisher PDF/HTML fulltext when the current network/session
  directly returns it.
- It does not bypass paywalls, CAPTCHAs, login pages, Cloudflare gates, or other
  access controls.
- It never uses Sci-Hub or unauthorized mirror sites.
- It records failures and continues with the next paper.
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import re
import sys
import time
from collections import defaultdict
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence
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

SUCCESS_STATUSES = {
    "success_local_pdf",
    "success_oa_pdf",
    "success_oa_html",
    "success_institutional_pdf",
    "success_institutional_html",
    "skipped_existing",
}
RETRYABLE_STATUSES = {"timeout", "retryable_failure", "redirect_only"}
NON_RETRYABLE_STATUSES = {
    "forbidden",
    "paywall_or_login_required",
    "captcha_or_bot_blocked",
    "manual_required",
    "non_retryable_failure",
}

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
    "candidate_source",
    "candidate_source_type",
    "access_route",
    "is_open_access",
    "institutional_access_possible",
    "original_pdf_path",
]

LOG_COLUMNS = [
    "paper_id",
    "doi",
    "title",
    "candidate_url",
    "candidate_source",
    "candidate_source_type",
    "access_route",
    "is_open_access",
    "institutional_access_possible",
    "source_priority",
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
    "login",
    "log in",
    "shibboleth",
    "athens",
]

CAPTCHA_MARKERS = [
    "captcha",
    "robot check",
    "are you a robot",
    "verify you are human",
    "cloudflare",
    "checking your browser",
    "just a moment",
]

REDIRECT_MARKERS = [
    "redirecting",
    "enable javascript",
    "continue to article",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Fetch legal full-text candidates and update the stage4 manifest.")
    parser.add_argument("--candidates", default=str(DEFAULT_CANDIDATES))
    parser.add_argument("--manifest", default=str(DEFAULT_MANIFEST))
    parser.add_argument("--log", default=str(DEFAULT_LOG))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--limit", type=int, default=20, help="Maximum number of papers to process.")
    parser.add_argument("--max-candidates-per-paper", type=int, default=8)
    parser.add_argument("--retry-failed", action="store_true")
    parser.add_argument("--skip-existing", action="store_true", default=True)
    parser.add_argument("--no-skip-existing", action="store_false", dest="skip_existing")
    parser.add_argument("--timeout", type=int, default=30)
    parser.add_argument("--sleep", type=float, default=1.0)
    parser.add_argument("--max-per-domain", type=int, default=8, help="Maximum HTTP attempts per domain in one run.")
    parser.add_argument("--max-retries", type=int, default=1, help="Retries per candidate URL for retryable network failures.")
    return parser.parse_args()


def read_rows(path: Path) -> List[Dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def write_rows(path: Path, rows: Sequence[Dict[str, str]], columns: Sequence[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(columns), extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).astimezone().isoformat(timespec="seconds")


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


def repo_path(value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else ROOT / path


def relative_to_root(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def is_http_url(url: str) -> bool:
    return str(url or "").lower().startswith(("http://", "https://"))


def is_local_candidate(row: Dict[str, str]) -> bool:
    return row.get("candidate_source_type", "") == "local_pdf" or row.get("access_route", "") == "local_pdf"


def is_manual_candidate(row: Dict[str, str]) -> bool:
    return row.get("candidate_source_type", "") == "manual_required" or str(row.get("candidate_url", "")).startswith("manual://")


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


def normalize_manifest_rows(rows: Iterable[Dict[str, str]]) -> Dict[str, Dict[str, str]]:
    by_id: Dict[str, Dict[str, str]] = {}
    for row in rows:
        paper_id = str(row.get("paper_id", "")).strip()
        if not paper_id:
            continue
        normalized = {column: row.get(column, "") for column in MANIFEST_COLUMNS}
        normalized["source_url"] = normalized["source_url"] or row.get("selected_url", "")
        normalized["attempted_url"] = normalized["attempted_url"] or normalized["source_url"]
        normalized["local_saved_path"] = normalized["local_saved_path"] or row.get("local_path", "")
        normalized["selected_url"] = normalized["selected_url"] or normalized["source_url"]
        normalized["local_path"] = normalized["local_path"] or normalized["local_saved_path"]
        normalized["has_text_content"] = normalized["has_text_content"] or normalized["has_useful_text"]
        normalized["usable_for_extraction"] = normalized["usable_for_extraction"] or normalized["ready_for_extraction"]
        normalized["fetch_notes"] = normalized["fetch_notes"] or normalized["notes"] or normalized["failure_reason"]
        by_id[paper_id] = normalized
    return by_id


def group_candidates(rows: List[Dict[str, str]], limit: int, max_per_paper: int) -> Dict[str, List[Dict[str, str]]]:
    grouped: Dict[str, List[Dict[str, str]]] = {}
    for row in rows:
        paper_id = str(row.get("paper_id", "")).strip()
        if paper_id:
            grouped.setdefault(paper_id, []).append(row)

    ordered: Dict[str, List[Dict[str, str]]] = {}
    for paper_id, candidates in grouped.items():
        deduped: Dict[str, Dict[str, str]] = {}
        for row in candidates:
            url = str(row.get("candidate_url", "")).strip()
            if not url:
                continue
            key = url.lower()
            previous = deduped.get(key)
            current_priority = safe_float(row.get("source_priority", row.get("candidate_priority", "")), 0.0)
            previous_priority = safe_float(previous.get("source_priority", previous.get("candidate_priority", "")) if previous else "", 0.0)
            if previous is None or current_priority > previous_priority:
                deduped[key] = row
        sorted_candidates = sorted(
            deduped.values(),
            key=lambda row: -safe_float(row.get("source_priority", row.get("candidate_priority", "")), 0.0),
        )
        local = [row for row in sorted_candidates if is_local_candidate(row)]
        manual = [row for row in sorted_candidates if is_manual_candidate(row)]
        remote = [row for row in sorted_candidates if not is_local_candidate(row) and not is_manual_candidate(row)]
        ordered[paper_id] = local + remote[:max_per_paper] + manual[:1]
    if limit > 0:
        ordered = dict(list(ordered.items())[:limit])
    return ordered


def base_log(candidate: Dict[str, str]) -> Dict[str, str]:
    row = {column: "" for column in LOG_COLUMNS}
    for key in [
        "paper_id",
        "doi",
        "title",
        "candidate_url",
        "candidate_source",
        "candidate_source_type",
        "access_route",
        "is_open_access",
        "institutional_access_possible",
        "source_priority",
    ]:
        row[key] = candidate.get(key, "")
    row["fetch_time"] = now_iso()
    row["retry_recommended"] = "no"
    row["has_useful_text"] = "no"
    row["ready_for_extraction"] = "no"
    row["source_quality_score"] = "0"
    return row


def classify_quality_for_path(candidate: Dict[str, str], local_saved_path: str, content_type: str, status: str = "success") -> Dict[str, str]:
    text = load_text_from_local_path(repo_path(local_saved_path))
    quality = analyze_text_quality(text)
    quality["best_local_saved_path"] = local_saved_path
    quality["text"] = text
    manifest_like = {
        "fetch_status": status,
        "url_source": candidate.get("candidate_source_type", ""),
        "content_type": content_type,
    }
    source_class = classify_source_quality(manifest_like, quality)
    quality_type = source_class["source_quality_type"]
    return {
        **source_class,
        "has_useful_text": "yes" if quality_type in {"pdf_fulltext", "html_fulltext", "abstract_only", "doi_landing_page"} else "no",
        "ready_for_extraction": "yes" if quality_type in {"pdf_fulltext", "html_fulltext", "abstract_only"} else "no",
    }


def success_status_for_candidate(candidate: Dict[str, str], source_quality_type: str) -> str:
    access_route = candidate.get("access_route", "")
    candidate_type = candidate.get("candidate_source_type", "")
    is_oa = str(candidate.get("is_open_access", "")).lower() == "yes"
    if access_route == "local_pdf" or candidate_type == "local_pdf":
        return "success_local_pdf"
    if source_quality_type == "pdf_fulltext":
        if access_route == "open_access" or is_oa or candidate_type == "oa_pdf":
            return "success_oa_pdf"
        return "success_institutional_pdf"
    if source_quality_type == "html_fulltext":
        if access_route == "open_access" or is_oa or candidate_type in {"oa_html_fulltext", "unpaywall_location"}:
            return "success_oa_html"
        return "success_institutional_html"
    return "success"


def fetch_local(candidate: Dict[str, str]) -> Dict[str, str]:
    row = base_log(candidate)
    path = repo_path(candidate.get("candidate_url", ""))
    if not path.exists():
        row["fetch_status"] = "manual_required"
        row["failure_reason"] = "local_pdf_not_found"
        row["notes"] = "Local PDF candidate path does not exist; manual legal PDF placement is needed."
        return row
    if path.suffix.lower() != ".pdf":
        row["fetch_status"] = "non_retryable_failure"
        row["failure_reason"] = "local_candidate_not_pdf"
        row["notes"] = "Local candidate exists but is not a PDF."
        return row
    rel = relative_to_root(path)
    row["local_saved_path"] = rel
    row["content_type"] = "application/pdf"
    row["content_length"] = str(path.stat().st_size)
    quality = classify_quality_for_path(candidate, rel, "application/pdf", "success_local_pdf")
    row.update(quality)
    if row["source_quality_type"] == "pdf_fulltext":
        row["fetch_status"] = "success_local_pdf"
        row["failure_reason"] = ""
        row["notes"] = "Existing local legal PDF is usable for metadata and experimental extraction."
    else:
        row["fetch_status"] = "parse_failed"
        row["failure_reason"] = "local_pdf_text_not_useful"
        row["retry_recommended"] = "no"
        row["notes"] = "Local PDF exists, but text extraction did not produce useful SRM fulltext."
    return row


def classify_text_blockers(content: bytes, content_type: str, final_url: str) -> tuple[str, str] | None:
    snippet = content[:8000].decode("utf-8", errors="ignore").lower()
    url_lower = (final_url or "").lower()
    if any(marker in snippet for marker in CAPTCHA_MARKERS):
        return "captcha_or_bot_blocked", "captcha_or_bot_block_detected"
    if any(marker in snippet for marker in PAYWALL_MARKERS) or any(token in url_lower for token in ["login", "signin", "shibboleth", "saml"]):
        return "paywall_or_login_required", "paywall_or_login_page_detected"
    if "html" in (content_type or "").lower() and any(marker in snippet for marker in REDIRECT_MARKERS) and len(snippet.strip()) < 2500:
        return "redirect_only", "redirect_or_gate_page"
    return None


def classify_http_status(status_code: int, content: bytes, content_type: str, final_url: str) -> tuple[str, str, str]:
    blocker = classify_text_blockers(content, content_type, final_url)
    if blocker:
        status, reason = blocker
        retry = "yes" if status == "redirect_only" else "no"
        return status, reason, retry
    if status_code == 403:
        return "forbidden", "forbidden_http_403", "no"
    if status_code in {401, 402}:
        return "paywall_or_login_required", f"http_{status_code}_access_limited", "no"
    if status_code == 404:
        return "non_retryable_failure", "not_found_http_404", "no"
    if status_code in {408, 429} or 500 <= status_code <= 599:
        return "retryable_failure", f"http_{status_code}", "yes"
    if 400 <= status_code <= 499:
        return "non_retryable_failure", f"http_{status_code}", "no"
    return "", "", "no"


def fetch_remote(
    candidate: Dict[str, str],
    session: requests.Session,
    output_dir: Path,
    timeout: int,
    max_retries: int,
) -> Dict[str, str]:
    row = base_log(candidate)
    url = candidate.get("candidate_url", "")
    if not is_http_url(url):
        row["fetch_status"] = "manual_required" if is_manual_candidate(candidate) else "non_retryable_failure"
        row["failure_reason"] = "manual_required" if is_manual_candidate(candidate) else "unsupported_url_scheme"
        row["notes"] = "No HTTP fetch attempted for this candidate."
        return row

    attempts = max(1, max_retries + 1)
    last_error = None
    for attempt in range(1, attempts + 1):
        try:
            response = session.get(
                url,
                timeout=timeout,
                allow_redirects=True,
                headers={
                    "Accept": "application/pdf, text/html;q=0.9, application/xhtml+xml;q=0.8, */*;q=0.6",
                },
            )
            last_error = None
            break
        except requests.Timeout:
            last_error = ("timeout", "requests_timeout", "yes")
        except requests.RequestException as exc:
            last_error = ("retryable_failure", f"request_error:{type(exc).__name__}", "yes")
        if attempt < attempts:
            time.sleep(0.5)
    else:
        status, reason, retry = last_error or ("retryable_failure", "request_failed", "yes")
        row["fetch_status"] = status
        row["failure_reason"] = reason
        row["retry_recommended"] = retry
        row["notes"] = "Network request failed; no access bypass attempted."
        return row

    row["http_status"] = str(response.status_code)
    row["final_url"] = response.url
    row["content_type"] = response.headers.get("Content-Type", "")
    row["content_length"] = str(len(response.content))

    status, reason, retry = classify_http_status(response.status_code, response.content, row["content_type"], response.url)
    if status:
        row["fetch_status"] = status
        row["failure_reason"] = reason
        row["retry_recommended"] = retry
        row["notes"] = "Access-limited or failed response recorded; no bypass attempted."
        row["source_quality_type"] = "redirect_or_forbidden" if status in {"forbidden", "paywall_or_login_required", "captcha_or_bot_blocked", "redirect_only"} else "no_useful_content"
        return row

    extension = infer_extension(row["content_type"], response.url)
    local_name = (
        f"{safe_filename(candidate.get('paper_id', 'paper'))}_"
        f"{safe_filename(candidate.get('candidate_source_type', 'source'))}_"
        f"{safe_filename(str(candidate.get('source_priority', candidate.get('candidate_priority', ''))))}{extension}"
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    local_path = output_dir / local_name
    try:
        local_path.write_bytes(response.content)
    except OSError as exc:
        row["fetch_status"] = "parse_failed"
        row["failure_reason"] = f"write_failed:{type(exc).__name__}"
        row["retry_recommended"] = "yes"
        row["notes"] = "Failed to save fetched content."
        return row

    row["local_saved_path"] = relative_to_root(local_path)
    quality = classify_quality_for_path(candidate, row["local_saved_path"], row["content_type"], "success")
    row.update(quality)
    source_quality_type = row.get("source_quality_type", "")

    if source_quality_type in {"pdf_fulltext", "html_fulltext"}:
        row["fetch_status"] = success_status_for_candidate(candidate, source_quality_type)
        row["failure_reason"] = ""
        row["notes"] = f"Fetched directly accessible {source_quality_type}; no access bypass used."
    elif source_quality_type == "abstract_only":
        row["fetch_status"] = "abstract_only"
        row["failure_reason"] = ""
        row["notes"] = "Only abstract-level content is usable; experimental extraction is not allowed."
    elif candidate.get("candidate_source_type") == "doi_landing_page" or candidate.get("access_route") == "doi_landing":
        row["fetch_status"] = "doi_landing_only"
        row["failure_reason"] = "doi_landing_page_only"
        row["ready_for_extraction"] = "no"
        row["notes"] = "DOI landing page only; find PDF/HTML fulltext before experimental extraction."
    elif candidate.get("candidate_source_type") == "publisher_landing_page" or candidate.get("access_route") == "publisher_landing":
        row["fetch_status"] = "publisher_landing_only"
        row["failure_reason"] = "publisher_landing_page_only"
        row["ready_for_extraction"] = "no"
        row["notes"] = "Publisher landing page only; not enough for experimental extraction."
    else:
        row["fetch_status"] = "no_useful_content"
        row["failure_reason"] = "no_useful_fulltext_signal"
        row["ready_for_extraction"] = "no"
        row["notes"] = "Fetched content did not contain enough useful SRM fulltext."
    return row


def should_skip_paper(existing: Optional[Dict[str, str]], skip_existing: bool, retry_failed: bool) -> bool:
    if not existing or not skip_existing or retry_failed:
        return False
    if existing.get("fetch_status", "") in SUCCESS_STATUSES:
        return True
    return (
        existing.get("source_quality_type", "") in {"pdf_fulltext", "html_fulltext"}
        and existing.get("ready_for_extraction", "").lower() == "yes"
        and existing.get("has_useful_text", "").lower() == "yes"
    )


def log_skipped(candidate: Dict[str, str], existing: Dict[str, str]) -> Dict[str, str]:
    row = base_log(candidate)
    row["fetch_status"] = "skipped_existing"
    row["local_saved_path"] = existing.get("local_saved_path", "")
    row["source_quality_type"] = existing.get("source_quality_type", "")
    row["source_quality_score"] = existing.get("source_quality_score", "")
    row["has_useful_text"] = existing.get("has_useful_text", "")
    row["ready_for_extraction"] = existing.get("ready_for_extraction", "")
    row["notes"] = "Existing useful fulltext manifest row skipped."
    return row


def status_score(row: Dict[str, str]) -> float:
    quality_rank = {
        "pdf_fulltext": 100,
        "html_fulltext": 92,
        "abstract_only": 60,
        "doi_landing_page": 25,
        "navigation_shell": 10,
        "redirect_or_forbidden": 0,
        "no_useful_content": 0,
    }
    status_bonus = {
        "success_local_pdf": 8,
        "success_oa_pdf": 7,
        "success_institutional_pdf": 6,
        "success_oa_html": 5,
        "success_institutional_html": 4,
        "abstract_only": 2,
    }
    return quality_rank.get(row.get("source_quality_type", ""), 0) + status_bonus.get(row.get("fetch_status", ""), 0)


def best_log_row(rows: Sequence[Dict[str, str]], existing: Optional[Dict[str, str]]) -> Optional[Dict[str, str]]:
    candidates = list(rows)
    if existing:
        candidates.append(existing)
    usable = [row for row in candidates if row.get("fetch_status") != "manual_required"]
    if not usable:
        return rows[-1] if rows else existing
    return max(usable, key=status_score)


def update_manifest_row(existing: Optional[Dict[str, str]], candidate: Dict[str, str], best: Dict[str, str], attempts_added: int) -> Dict[str, str]:
    row = {column: (existing or {}).get(column, "") for column in MANIFEST_COLUMNS}
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
            "candidate_source": best.get("candidate_source", candidate.get("candidate_source", "")),
            "candidate_source_type": best.get("candidate_source_type", candidate.get("candidate_source_type", "")),
            "access_route": best.get("access_route", candidate.get("access_route", "")),
            "is_open_access": best.get("is_open_access", candidate.get("is_open_access", "")),
            "institutional_access_possible": best.get("institutional_access_possible", candidate.get("institutional_access_possible", "")),
        }
    )
    row["fetch_attempts"] = str(safe_int(row.get("fetch_attempts", "0"), 0) + attempts_added)
    row["selected_url"] = row.get("source_url", "")
    row["local_path"] = row.get("local_saved_path", "")
    row["has_text_content"] = row.get("has_useful_text", "")
    row["usable_for_extraction"] = row.get("ready_for_extraction", "")
    row["fetch_notes"] = row.get("notes", "") or row.get("failure_reason", "")
    if row["fetch_status"] == "success_local_pdf":
        row["original_pdf_path"] = row.get("local_saved_path", "")
    return row


def domain_for_candidate(row: Dict[str, str]) -> str:
    url = row.get("candidate_url", "")
    if not is_http_url(url):
        return ""
    return urlparse(url).netloc.lower()


def main() -> int:
    args = parse_args()
    candidates = read_rows(Path(args.candidates))
    manifest_by_id = normalize_manifest_rows(read_rows(Path(args.manifest)))
    grouped = group_candidates(candidates, args.limit, args.max_candidates_per_paper)

    session = requests.Session()
    session.headers.update(
        {
            "User-Agent": "srm-ml-screening/0.7 legal-authorized-fulltext-fetcher",
            "Accept-Language": "en-US,en;q=0.9",
        }
    )
    output_dir = Path(args.output_dir)
    log_rows: List[Dict[str, str]] = []
    updated_manifest = dict(manifest_by_id)
    domain_counts: Dict[str, int] = defaultdict(int)

    for paper_id, candidate_rows in grouped.items():
        existing = manifest_by_id.get(paper_id)
        if should_skip_paper(existing, args.skip_existing, args.retry_failed):
            log_rows.append(log_skipped(candidate_rows[0], existing or {}))
            continue

        per_paper_logs: List[Dict[str, str]] = []
        network_attempts = 0
        for candidate in candidate_rows:
            if is_manual_candidate(candidate):
                result = fetch_remote(candidate, session, output_dir, args.timeout, args.max_retries)
                per_paper_logs.append(result)
                log_rows.append(result)
                continue
            if is_local_candidate(candidate):
                result = fetch_local(candidate)
            else:
                domain = domain_for_candidate(candidate)
                if domain and domain_counts[domain] >= args.max_per_domain:
                    result = base_log(candidate)
                    result["fetch_status"] = "manual_required"
                    result["failure_reason"] = "max_per_domain_reached"
                    result["notes"] = f"Skipped to respect --max-per-domain={args.max_per_domain}."
                else:
                    if domain:
                        domain_counts[domain] += 1
                    result = fetch_remote(candidate, session, output_dir, args.timeout, args.max_retries)
                    network_attempts += 1
                    time.sleep(args.sleep)
            per_paper_logs.append(result)
            log_rows.append(result)
            if result.get("source_quality_type") in {"pdf_fulltext", "html_fulltext"}:
                break

        best = best_log_row(per_paper_logs, existing)
        if best:
            updated_manifest[paper_id] = update_manifest_row(existing, candidate_rows[0], best, network_attempts)

    manifest_rows = [updated_manifest[paper_id] for paper_id in sorted(updated_manifest)]
    write_rows(Path(args.log), log_rows, LOG_COLUMNS)
    write_rows(Path(args.manifest), manifest_rows, MANIFEST_COLUMNS)

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
