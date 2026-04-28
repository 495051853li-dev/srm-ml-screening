"""Ingest manually supplied legal PDFs into the SRM full-text manifest."""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import re
import sys
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from stage5_extraction_utils import analyze_text_quality, classify_source_quality, load_text_from_local_path


DEFAULT_PDF_DIR = ROOT / "data" / "raw" / "pdfs"
DEFAULT_SCORED = ROOT / "data" / "processed" / "candidate_papers_high_if_scored.csv"
DEFAULT_ELIGIBLE = ROOT / "data" / "processed" / "eligible_high_if_pool.csv"
DEFAULT_MANIFEST = ROOT / "data" / "processed" / "fulltext_fetch_manifest.csv"
DEFAULT_LOG = ROOT / "data" / "processed" / "local_pdf_ingest_log.csv"

LOG_COLUMNS = [
    "pdf_file",
    "matched_paper_id",
    "matched_by",
    "doi",
    "title",
    "parse_status",
    "text_length",
    "source_quality_type",
    "ready_for_extraction",
    "manifest_updated",
    "notes",
    "ingest_time",
]

MANIFEST_EXTRA_COLUMNS = [
    "source_quality_type",
    "source_quality_score",
    "allowed_extraction_scope",
    "extraction_strategy",
    "recommended_next_action",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Ingest local manually downloaded PDFs.")
    parser.add_argument("--pdf-dir", default=str(DEFAULT_PDF_DIR))
    parser.add_argument("--scored", default=str(DEFAULT_SCORED))
    parser.add_argument("--eligible", default=str(DEFAULT_ELIGIBLE))
    parser.add_argument("--manifest", default=str(DEFAULT_MANIFEST))
    parser.add_argument("--log", default=str(DEFAULT_LOG))
    return parser.parse_args()


def read_rows(path: Path) -> List[Dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def resolve_repo_path(value: str | Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else ROOT / path


def write_rows(path: Path, rows: Sequence[Dict[str, str]], columns: Sequence[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(columns), extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def normalize_doi(value: str) -> str:
    value = (value or "").strip().lower()
    value = re.sub(r"^https?://(dx\.)?doi\.org/", "", value)
    return value


def safe_token(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", (value or "").lower()).strip("_")


def build_paper_index(rows: Iterable[Dict[str, str]]) -> Dict[str, Dict[str, str]]:
    index: Dict[str, Dict[str, str]] = {}
    for row in rows:
        paper_id = str(row.get("paper_id", "")).strip()
        if paper_id and paper_id not in index:
            index[paper_id] = row
    return index


def match_pdf(path: Path, papers: Dict[str, Dict[str, str]]) -> tuple[Optional[Dict[str, str]], str]:
    stem = safe_token(path.stem)
    for paper_id, row in papers.items():
        if safe_token(paper_id) in stem:
            return row, "paper_id"
    for row in papers.values():
        doi = safe_token(normalize_doi(row.get("doi", "")))
        if doi and doi in stem:
            return row, "doi"
    for row in papers.values():
        title_tokens = safe_token(row.get("title", ""))
        if title_tokens and len(title_tokens) >= 24 and title_tokens[:40] in stem:
            return row, "title_filename"
    return None, ""


def normalize_manifest_rows(rows: List[Dict[str, str]]) -> tuple[List[str], Dict[str, Dict[str, str]]]:
    columns = list(rows[0].keys()) if rows else []
    for column in MANIFEST_EXTRA_COLUMNS:
        if column not in columns:
            columns.append(column)
    by_id = {str(row.get("paper_id", "")).strip(): dict(row) for row in rows if row.get("paper_id")}
    return columns, by_id


def update_manifest_row(
    manifest_by_id: Dict[str, Dict[str, str]],
    columns: List[str],
    paper: Dict[str, str],
    pdf_path: Path,
    classification: Dict[str, str],
    text_length: int,
) -> None:
    now = dt.datetime.now(dt.timezone.utc).astimezone().isoformat(timespec="seconds")
    paper_id = paper.get("paper_id", "")
    row = manifest_by_id.get(paper_id, {column: "" for column in columns})
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
            "source_url": str(pdf_path.relative_to(ROOT)),
            "attempted_url": str(pdf_path.relative_to(ROOT)),
            "final_url": str(pdf_path.relative_to(ROOT)),
            "url_source": "local_manual_pdf",
            "fetch_status": "success" if classification["source_quality_type"] == "pdf_fulltext" else "parse_failed",
            "fetch_attempts": str(int(float(str(row.get("fetch_attempts", "0") or "0"))) + 1),
            "last_fetch_time": now,
            "retry_recommended": "no",
            "failure_reason": "" if classification["source_quality_type"] == "pdf_fulltext" else "local_pdf_not_parseable_as_fulltext",
            "local_saved_path": str(pdf_path.relative_to(ROOT)),
            "content_type": "application/pdf",
            "content_length": str(pdf_path.stat().st_size),
            "has_useful_text": "yes" if classification["source_quality_type"] == "pdf_fulltext" else "no",
            "ready_for_extraction": "yes" if classification["source_quality_type"] == "pdf_fulltext" else "no",
            "notes": f"Local legal PDF ingested; extracted_text_length={text_length}.",
            "http_status": "",
            "source_page_kind": "local_pdf",
            "reused_existing": "no",
            "selected_url": str(pdf_path.relative_to(ROOT)),
            "local_path": str(pdf_path.relative_to(ROOT)),
            "has_text_content": "yes" if classification["source_quality_type"] == "pdf_fulltext" else "no",
            "usable_for_extraction": "yes" if classification["source_quality_type"] == "pdf_fulltext" else "no",
            "fetch_notes": f"Local legal PDF ingested; extracted_text_length={text_length}.",
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
    pdf_dir.mkdir(parents=True, exist_ok=True)
    papers = build_paper_index(read_rows(resolve_repo_path(args.eligible)) + read_rows(resolve_repo_path(args.scored)))
    manifest_columns, manifest_by_id = normalize_manifest_rows(read_rows(resolve_repo_path(args.manifest)))

    log_rows: List[Dict[str, str]] = []
    for pdf_path in sorted(pdf_dir.glob("*.pdf")):
        now = dt.datetime.now(dt.timezone.utc).astimezone().isoformat(timespec="seconds")
        log = {column: "" for column in LOG_COLUMNS}
        log["pdf_file"] = str(pdf_path.relative_to(ROOT))
        log["ingest_time"] = now
        paper, matched_by = match_pdf(pdf_path, papers)
        if not paper:
            log["parse_status"] = "unmatched"
            log["notes"] = "No paper_id, DOI, or title filename match found."
            log_rows.append(log)
            continue

        text = load_text_from_local_path(pdf_path)
        quality = analyze_text_quality(text)
        quality["best_local_saved_path"] = str(pdf_path.relative_to(ROOT))
        quality["text"] = text
        classification = classify_source_quality({"fetch_status": "success", "content_type": "application/pdf", "url_source": "local_pdf"}, quality)

        log.update(
            {
                "matched_paper_id": paper.get("paper_id", ""),
                "matched_by": matched_by,
                "doi": paper.get("doi", ""),
                "title": paper.get("title", ""),
                "parse_status": "parsed" if text else "parse_failed",
                "text_length": str(len(text)),
                "source_quality_type": classification.get("source_quality_type", ""),
                "ready_for_extraction": "yes" if classification.get("source_quality_type") == "pdf_fulltext" else "no",
                "manifest_updated": "yes" if classification.get("source_quality_type") == "pdf_fulltext" else "no",
                "notes": "Local PDF classified from extracted text; no experimental values generated.",
            }
        )
        if classification.get("source_quality_type") == "pdf_fulltext":
            update_manifest_row(manifest_by_id, manifest_columns, paper, pdf_path, classification, len(text))
        log_rows.append(log)

    write_rows(resolve_repo_path(args.log), log_rows, LOG_COLUMNS)
    write_rows(resolve_repo_path(args.manifest), [manifest_by_id[key] for key in sorted(manifest_by_id)], manifest_columns)
    print(f"Local PDFs scanned: {len(list(pdf_dir.glob('*.pdf')))}")
    print(f"Local PDF ingest log written: {Path(args.log)}")
    print(f"Manifest updated: {Path(args.manifest)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
