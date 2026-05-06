"""Ingest manually supplied legal PDFs into the SRM full-text manifest.

This script treats local PDFs as the highest-quality source layer. It never
modifies the original PDFs. Parsed text is cached under outputs/fulltext/pdf_text
and the manifest points stage5 to that text cache.
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import difflib
import re
import sys
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from stage5_extraction_utils import (  # noqa: E402
    PdfReader,
    analyze_text_quality,
    classify_source_quality,
    normalize_text,
    read_rows,
)


DEFAULT_PDF_DIR = ROOT / "data" / "raw" / "pdfs"
DEFAULT_TEXT_DIR = ROOT / "outputs" / "fulltext" / "pdf_text"
DEFAULT_CANDIDATES = ROOT / "data" / "processed" / "candidate_papers.csv"
DEFAULT_SCORED = ROOT / "data" / "processed" / "candidate_papers_high_if_scored.csv"
DEFAULT_ELIGIBLE = ROOT / "data" / "processed" / "eligible_high_if_pool.csv"
DEFAULT_MANIFEST = ROOT / "data" / "processed" / "fulltext_fetch_manifest.csv"
DEFAULT_LOG = ROOT / "data" / "processed" / "local_pdf_ingest_log.csv"

LOG_COLUMNS = [
    "pdf_filename",
    "pdf_path",
    "matched_paper_id",
    "matched_doi",
    "matched_title",
    "match_method",
    "match_confidence",
    "parse_status",
    "parsed_text_path",
    "page_count",
    "text_length",
    "failure_reason",
    "ready_for_extraction",
    "source_quality_type",
    "manifest_updated",
    "ingest_time",
]

MANIFEST_EXTRA_COLUMNS = [
    "source_quality_type",
    "source_quality_score",
    "allowed_extraction_scope",
    "extraction_strategy",
    "recommended_next_action",
    "original_pdf_path",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Ingest local manually downloaded PDFs.")
    parser.add_argument("--pdf-dir", default=str(DEFAULT_PDF_DIR))
    parser.add_argument("--text-dir", default=str(DEFAULT_TEXT_DIR))
    parser.add_argument("--candidates", default=str(DEFAULT_CANDIDATES))
    parser.add_argument("--scored", default=str(DEFAULT_SCORED))
    parser.add_argument("--eligible", default=str(DEFAULT_ELIGIBLE))
    parser.add_argument("--manifest", default=str(DEFAULT_MANIFEST))
    parser.add_argument("--log", default=str(DEFAULT_LOG))
    parser.add_argument("--min-text-length", type=int, default=3000)
    return parser.parse_args()


def resolve_repo_path(value: str | Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else ROOT / path


def write_rows(path: Path, rows: Sequence[Dict[str, str]], columns: Sequence[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(columns), extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def relative_to_root(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def normalize_doi(value: str) -> str:
    value = (value or "").strip().lower()
    value = re.sub(r"^https?://(dx\.)?doi\.org/", "", value)
    return value.strip(" .;),]")


def safe_token(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", (value or "").lower()).strip("_")


def normalized_for_match(value: str) -> str:
    value = re.sub(r"<[^>]+>", " ", value or "")
    value = re.sub(r"[^a-zA-Z0-9]+", " ", value)
    return re.sub(r"\s+", " ", value).strip().lower()


def safe_file_stem(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "_", value or "").strip("_")[:160] or "pdf_text"


def extract_dois(text: str) -> List[str]:
    pattern = re.compile(r"10\.\d{4,9}/[-._;()/:A-Z0-9]+", flags=re.IGNORECASE)
    dois: List[str] = []
    for match in pattern.findall(text or ""):
        doi = normalize_doi(match)
        if doi and doi not in dois:
            dois.append(doi)
    return dois


def load_pdf_text(path: Path) -> Tuple[str, int, str]:
    if PdfReader is None:
        return "", 0, "pypdf_not_available"
    try:
        reader = PdfReader(str(path))
        pages: List[str] = []
        for page in reader.pages:
            pages.append(page.extract_text() or "")
        text = normalize_text(" ".join(pages))
        return text, len(reader.pages), "" if text else "empty_extracted_text"
    except Exception as exc:  # pragma: no cover - parser edge cases differ by PDF
        return "", 0, f"pdf_parse_error:{type(exc).__name__}"


def build_paper_index(rows: Iterable[Dict[str, str]]) -> List[Dict[str, str]]:
    seen: set[str] = set()
    papers: List[Dict[str, str]] = []
    for row in rows:
        paper_id = str(row.get("paper_id", "")).strip()
        if not paper_id or paper_id in seen:
            continue
        seen.add(paper_id)
        enriched = dict(row)
        enriched["_normalized_doi"] = normalize_doi(row.get("doi", ""))
        enriched["_normalized_title"] = normalized_for_match(row.get("title", ""))
        papers.append(enriched)
    return papers


def match_pdf(path: Path, text: str, papers: List[Dict[str, str]]) -> Tuple[Optional[Dict[str, str]], str, float]:
    stem = safe_token(path.stem)
    for row in papers:
        paper_id = safe_token(row.get("paper_id", ""))
        if paper_id and paper_id in stem:
            return row, "filename_paper_id", 1.0

    filename_dois = extract_dois(path.stem.replace("_", "/").replace("-", "."))
    text_dois = extract_dois(text[:12000])
    all_dois = filename_dois + [doi for doi in text_dois if doi not in filename_dois]
    for doi in all_dois:
        for row in papers:
            if doi and row.get("_normalized_doi") == doi:
                method = "filename_doi" if doi in filename_dois else "pdf_text_doi"
                confidence = 0.98 if method == "filename_doi" else 0.93
                return row, method, confidence

    text_norm = normalized_for_match(text[:20000])
    best_row: Optional[Dict[str, str]] = None
    best_score = 0.0
    for row in papers:
        title = row.get("_normalized_title", "")
        if not title or len(title) < 20:
            continue
        if title in text_norm:
            return row, "pdf_text_title_exact", 0.90
        score = difflib.SequenceMatcher(None, normalized_for_match(path.stem), title).ratio()
        if score > best_score:
            best_row = row
            best_score = score

    if best_row and best_score >= 0.72:
        return best_row, "filename_title_fuzzy", round(best_score, 3)
    return None, "unmatched", 0.0


def normalize_manifest_rows(rows: List[Dict[str, str]]) -> Tuple[List[str], Dict[str, Dict[str, str]]]:
    columns = list(rows[0].keys()) if rows else []
    for column in MANIFEST_EXTRA_COLUMNS:
        if column not in columns:
            columns.append(column)
    by_id = {str(row.get("paper_id", "")).strip(): dict(row) for row in rows if row.get("paper_id")}
    return columns, by_id


def manifest_local_path_exists(row: Dict[str, str]) -> bool:
    local_path = str(row.get("local_saved_path", "") or row.get("local_path", "")).strip()
    original_pdf_path = str(row.get("original_pdf_path", "")).strip()
    for value in [local_path, original_pdf_path]:
        if not value:
            continue
        path = Path(value)
        if not path.is_absolute():
            path = ROOT / path
        if path.exists() and path.is_file():
            return True
    return False


def downgrade_missing_manifest_pdfs(manifest_by_id: Dict[str, Dict[str, str]], columns: List[str]) -> int:
    downgraded = 0
    for row in manifest_by_id.values():
        if str(row.get("source_quality_type", "")).strip() != "pdf_fulltext":
            continue
        if manifest_local_path_exists(row):
            continue
        local_path = str(row.get("local_saved_path", "") or row.get("local_path", "")).strip()
        row.update(
            {
                "fetch_status": "missing_local_file",
                "retry_recommended": "yes",
                "failure_reason": "missing_local_pdf_or_text_cache",
                "has_useful_text": "no",
                "ready_for_extraction": "no",
                "has_text_content": "no",
                "usable_for_extraction": "no",
                "source_quality_type": "missing_local_pdf",
                "source_quality_score": "0",
                "allowed_extraction_scope": "none",
                "extraction_strategy": "skip_until_pdf_restored",
                "recommended_next_action": "rerun_pdf_download_or_restore_local_pdf",
                "notes": f"Manifest previously marked pdf_fulltext, but local source is missing: {local_path}",
                "fetch_notes": f"Manifest previously marked pdf_fulltext, but local source is missing: {local_path}",
            }
        )
        downgraded += 1
    return downgraded


def update_manifest_row(
    manifest_by_id: Dict[str, Dict[str, str]],
    columns: List[str],
    paper: Dict[str, str],
    pdf_path: Path,
    text_path: Path,
    classification: Dict[str, str],
    text_length: int,
    page_count: int,
) -> None:
    now = dt.datetime.now(dt.timezone.utc).astimezone().isoformat(timespec="seconds")
    paper_id = paper.get("paper_id", "")
    row = manifest_by_id.get(paper_id, {column: "" for column in columns})
    is_ready = classification["source_quality_type"] == "pdf_fulltext"
    row.update(
        {
            "paper_id": paper_id,
            "doi": paper.get("doi", row.get("doi", "")),
            "title": paper.get("title", row.get("title", "")),
            "document_type": paper.get("document_type", row.get("document_type", "")),
            "priority_rank": paper.get("priority_rank", row.get("priority_rank", "")),
            "priority_score": paper.get("priority_score", row.get("priority_score", "")),
            "journal": paper.get("journal", row.get("journal", "")),
            "journal_impact_factor": paper.get("journal_impact_factor", row.get("journal_impact_factor", "")),
            "source_url": relative_to_root(pdf_path),
            "attempted_url": relative_to_root(pdf_path),
            "final_url": relative_to_root(pdf_path),
            "url_source": "local_manual_pdf",
            "fetch_status": "success_local_pdf" if is_ready else "parse_failed",
            "fetch_attempts": str(int(float(str(row.get("fetch_attempts", "0") or "0"))) + 1),
            "last_fetch_time": now,
            "retry_recommended": "no",
            "failure_reason": "" if is_ready else "local_pdf_not_parseable_as_fulltext",
            "local_saved_path": relative_to_root(text_path),
            "original_pdf_path": relative_to_root(pdf_path),
            "content_type": "application/pdf; parsed_text_cache",
            "content_length": str(pdf_path.stat().st_size),
            "has_useful_text": "yes" if is_ready else "no",
            "ready_for_extraction": "yes" if is_ready else "no",
            "notes": f"Local legal PDF ingested; pages={page_count}; extracted_text_length={text_length}.",
            "http_status": "",
            "source_page_kind": "local_pdf_text_cache",
            "reused_existing": "no",
            "selected_url": relative_to_root(pdf_path),
            "local_path": relative_to_root(text_path),
            "has_text_content": "yes" if is_ready else "no",
            "usable_for_extraction": "yes" if is_ready else "no",
            "fetch_notes": f"Local legal PDF ingested; pages={page_count}; extracted_text_length={text_length}.",
            **classification,
        }
    )
    for key in row:
        if key not in columns:
            columns.append(key)
    manifest_by_id[paper_id] = row


def main() -> int:
    args = parse_args()
    pdf_dir = resolve_repo_path(args.pdf_dir)
    text_dir = resolve_repo_path(args.text_dir)
    pdf_dir.mkdir(parents=True, exist_ok=True)
    text_dir.mkdir(parents=True, exist_ok=True)

    papers = build_paper_index(
        read_rows(resolve_repo_path(args.eligible))
        + read_rows(resolve_repo_path(args.scored))
        + read_rows(resolve_repo_path(args.candidates))
    )
    manifest_columns, manifest_by_id = normalize_manifest_rows(read_rows(resolve_repo_path(args.manifest)))
    downgraded_missing = downgrade_missing_manifest_pdfs(manifest_by_id, manifest_columns)

    log_rows: List[Dict[str, str]] = []
    for pdf_path in sorted(pdf_dir.glob("*.pdf")):
        now = dt.datetime.now(dt.timezone.utc).astimezone().isoformat(timespec="seconds")
        text, page_count, parse_failure = load_pdf_text(pdf_path)
        paper, match_method, match_confidence = match_pdf(pdf_path, text, papers)

        text_path = text_dir / f"{safe_file_stem(paper.get('paper_id', pdf_path.stem) if paper else pdf_path.stem)}.txt"
        parsed_text_path = ""
        if text:
            text_path.write_text(text + "\n", encoding="utf-8")
            parsed_text_path = relative_to_root(text_path)

        log = {column: "" for column in LOG_COLUMNS}
        log.update(
            {
                "pdf_filename": pdf_path.name,
                "pdf_path": relative_to_root(pdf_path),
                "match_method": match_method,
                "match_confidence": f"{match_confidence:.3f}",
                "parse_status": "parsed" if text else "parse_failed",
                "parsed_text_path": parsed_text_path,
                "page_count": str(page_count),
                "text_length": str(len(text)),
                "failure_reason": parse_failure,
                "ready_for_extraction": "no",
                "source_quality_type": "",
                "manifest_updated": "no",
                "ingest_time": now,
            }
        )

        if not paper:
            log["parse_status"] = "unmatched" if text else "parse_failed"
            log["failure_reason"] = parse_failure or "no_candidate_match"
            log_rows.append(log)
            continue

        quality = analyze_text_quality(text)
        quality["best_local_saved_path"] = parsed_text_path
        quality["text"] = text
        classification = classify_source_quality(
            {"fetch_status": "success_local_pdf", "content_type": "application/pdf; parsed_text_cache", "url_source": "local_pdf"},
            quality,
        )

        is_ready = classification.get("source_quality_type") == "pdf_fulltext" and len(text) >= args.min_text_length
        if not is_ready and len(text) < args.min_text_length:
            classification["source_quality_type"] = "no_useful_content"
            classification["source_quality_score"] = "0"
            classification["allowed_extraction_scope"] = "none"
            classification["extraction_strategy"] = "skip"
            classification["recommended_next_action"] = "manual_check_pdf_or_ocr"

        log.update(
            {
                "matched_paper_id": paper.get("paper_id", ""),
                "matched_doi": paper.get("doi", ""),
                "matched_title": paper.get("title", ""),
                "source_quality_type": classification.get("source_quality_type", ""),
                "ready_for_extraction": "yes" if is_ready else "no",
                "manifest_updated": "yes" if is_ready else "no",
                "failure_reason": "" if is_ready else (parse_failure or "not_pdf_fulltext_quality"),
            }
        )
        if is_ready:
            update_manifest_row(manifest_by_id, manifest_columns, paper, pdf_path, text_path, classification, len(text), page_count)
        log_rows.append(log)

    write_rows(resolve_repo_path(args.log), log_rows, LOG_COLUMNS)
    write_rows(resolve_repo_path(args.manifest), [manifest_by_id[key] for key in sorted(manifest_by_id)], manifest_columns)
    print(f"Local PDFs scanned: {len(list(pdf_dir.glob('*.pdf')))}")
    print(f"Matched PDFs: {sum(1 for row in log_rows if row['matched_paper_id'])}")
    print(f"Parsed PDFs: {sum(1 for row in log_rows if row['parse_status'] == 'parsed')}")
    print(f"Ready PDF fulltexts: {sum(1 for row in log_rows if row['ready_for_extraction'] == 'yes')}")
    print(f"Missing manifest PDF rows downgraded: {downgraded_missing}")
    print(f"Local PDF ingest log written: {resolve_repo_path(args.log)}")
    print(f"Manifest updated: {resolve_repo_path(args.manifest)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
