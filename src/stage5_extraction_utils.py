from __future__ import annotations

import csv
import re
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

from bs4 import BeautifulSoup


ROOT = Path(__file__).resolve().parent.parent

REDIRECT_TERMS = [
    "redirecting",
    "access denied",
    "forbidden",
    "enable javascript",
    "checking your browser",
    "sign in through your institution",
]

DOMAIN_KEYWORDS = [
    "methane",
    "steam reforming",
    "catalyst",
    "reaction",
    "conversion",
    "temperature",
    "yield",
    "selectivity",
    "pressure",
    "ghsv",
    "steam-to-carbon",
    "s/c",
]

EXPERIMENTAL_KEYWORDS = [
    "temperature",
    "pressure",
    "steam-to-carbon",
    "s/c",
    "ghsv",
    "whsv",
    "conversion",
    "yield",
    "selectivity",
    "time on stream",
    "stability",
    "coke",
]

FULLTEXT_SECTION_TERMS = [
    "introduction",
    "experimental",
    "materials and methods",
    "results and discussion",
    "conclusions",
    "references",
]

METAL_PATTERN_MAP: Sequence[Tuple[str, Sequence[str]]] = [
    ("Ni", [r"\bnickel\b", r"\bni\b", r"ni[/\-]"]),
    ("Rh", [r"\brhodium\b", r"\brh\b", r"rh[/\-]"]),
    ("Co", [r"\bcobalt\b", r"\bco\b", r"co[/\-]", r"[/\-]co\b"]),
    ("Pt", [r"\bplatinum\b", r"\bpt\b", r"pt[/\-]"]),
    ("Ru", [r"\bruthenium\b", r"\bru\b", r"ru[/\-]"]),
    ("Cu", [r"\bcopper\b", r"\bcu\b", r"cu[/\-]"]),
    ("Fe", [r"\biron\b", r"\bfe\b", r"fe[/\-]"]),
]

SUPPORT_PATTERN_MAP: Sequence[Tuple[str, Sequence[str]]] = [
    ("Al2O3", ["alumina", "al2o3"]),
    ("CeO2", ["ceria", "ceo2"]),
    ("SiO2", ["silica", "sio2"]),
    ("MgAl2O4", ["mgal2o4"]),
    ("ZrO2", ["zirconia", "zro2"]),
    ("TiO2", ["titania", "tio2"]),
    ("BaZrCeYYbO3", ["bazr", "ce", "yb", "yo", "proton-conducting ceramic"]),
    ("SiC", ["sic", "silicon carbide"]),
]

PREPARATION_METHOD_MAP: Sequence[Tuple[str, Sequence[str]]] = [
    ("impregnation", ["impregnation", "incipient wetness"]),
    ("co_precipitation", ["co-precipitation", "coprecipitation", "co precipitation"]),
    ("sol_gel", ["sol-gel", "sol gel"]),
    ("deposition_precipitation", ["deposition precipitation", "deposition-precipitation"]),
    ("hydrothermal", ["hydrothermal"]),
    ("combustion", ["combustion"]),
    ("mechanical_mixing", ["mechanical mixing", "physically mixed"]),
]


def read_rows(path: Path) -> List[Dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def normalize_text(value: str) -> str:
    value = (value or "").replace("\x00", " ")
    value = re.sub(r"\s+", " ", value)
    return value.strip()


def yes_no(flag: bool) -> str:
    return "yes" if flag else "no"


def load_text_from_local_path(path: Path) -> str:
    if not path.exists():
        return ""
    text = path.read_text(encoding="utf-8", errors="ignore")
    if path.suffix.lower() in {".html", ".htm"}:
        soup = BeautifulSoup(text, "html.parser")
        return normalize_text(soup.get_text(" "))
    return normalize_text(text)


def candidate_local_files(paper_id: str, primary_local_path: str) -> List[Path]:
    candidates: List[Path] = []
    if primary_local_path:
        primary_path = ROOT / primary_local_path
        if primary_path.exists():
            candidates.append(primary_path)

    fulltext_dir = ROOT / "outputs" / "fulltext"
    for path in sorted(fulltext_dir.glob(f"{paper_id}*")):
        if path.is_file() and path not in candidates:
            candidates.append(path)
    return candidates


def analyze_text_quality(text: str) -> Dict[str, object]:
    lowered = text.lower()
    redirect_hits = [term for term in REDIRECT_TERMS if term in lowered]
    domain_hits = [term for term in DOMAIN_KEYWORDS if term in lowered]
    experimental_hits = [term for term in EXPERIMENTAL_KEYWORDS if term in lowered]
    text_length = len(text)
    hard_redirect_only = text_length < 30
    soft_redirect_marker = bool(redirect_hits)
    is_redirect_like = hard_redirect_only or (soft_redirect_marker and text_length < 800 and len(domain_hits) < 3)
    has_useful_domain_text = (
        not is_redirect_like
        and text_length >= 500
        and len(domain_hits) >= 3
        and "methane" in lowered
    )
    metadata_ready = has_useful_domain_text and ("catalyst" in lowered or "steam reforming" in lowered)
    experimental_ready = has_useful_domain_text and text_length >= 3000 and len(experimental_hits) >= 3

    not_ready_reasons: List[str] = []
    if is_redirect_like:
        not_ready_reasons.append("redirect_or_shell_page")
    elif soft_redirect_marker:
        not_ready_reasons.append("contains_gate_marker_but_text_is_still_usable")
    if text_length == 0:
        not_ready_reasons.append("empty_text")
    if text_length > 0 and len(domain_hits) < 3:
        not_ready_reasons.append("weak_domain_signal")
    if not experimental_ready:
        if len(experimental_hits) < 3:
            not_ready_reasons.append("weak_experimental_signal")
        elif text_length < 3000:
            not_ready_reasons.append("text_too_short_for_experimental_extraction")

    return {
        "text_length": text_length,
        "redirect_hits": ";".join(redirect_hits),
        "domain_keyword_count": len(domain_hits),
        "experimental_keyword_count": len(experimental_hits),
        "contains_msr_terms": ("steam reforming" in lowered and "methane" in lowered),
        "contains_condition_terms": any(term in lowered for term in ["temperature", "pressure", "steam-to-carbon", "s/c", "ghsv", "whsv"]),
        "contains_performance_terms": any(term in lowered for term in ["conversion", "yield", "selectivity", "stability", "coke"]),
        "has_useful_domain_text": has_useful_domain_text,
        "metadata_ready": metadata_ready,
        "experimental_ready": experimental_ready,
        "not_ready_reason": ";".join(dict.fromkeys(not_ready_reasons)),
        "source_excerpt_preview": text[:400],
    }


def classify_source_quality(fetch_row: Dict[str, str], quality: Dict[str, object]) -> Dict[str, str]:
    status = str(fetch_row.get("fetch_status", "")).strip().lower()
    url_source = str(fetch_row.get("url_source", "")).strip().lower()
    content_type = str(fetch_row.get("content_type", "")).strip().lower()
    local_path = str(quality.get("best_local_saved_path", ""))
    text = str(quality.get("text", ""))
    lowered = text.lower()
    text_length = int(quality.get("text_length", 0) or 0)
    domain_count = int(quality.get("domain_keyword_count", 0) or 0)
    experimental_count = int(quality.get("experimental_keyword_count", 0) or 0)
    has_msr_terms = bool(quality.get("contains_msr_terms", False))
    redirect_hits = str(quality.get("redirect_hits", ""))

    fulltext_section_count = sum(1 for term in FULLTEXT_SECTION_TERMS if term in lowered)
    local_suffix = Path(local_path).suffix.lower()

    source_quality_type = "unknown"
    source_quality_score = 0
    allowed_extraction_scope = "none"
    extraction_strategy = "skip"
    recommended_next_action = "manual_check_source"

    if status in {"forbidden", "redirect_only"} or (text_length < 30 and redirect_hits):
        source_quality_type = "redirect_or_forbidden"
        source_quality_score = 0
        recommended_next_action = "find_pdf_or_open_access_fulltext"
    elif status in {"no_useful_content", "non_retryable_failure", "retryable_failure", "timeout", "parse_failed"}:
        source_quality_type = "no_useful_content"
        source_quality_score = 0
        recommended_next_action = "retry_if_retryable_or_find_alternate_source"
    elif text_length < 200 and domain_count < 2:
        source_quality_type = "no_useful_content"
        source_quality_score = 0
        recommended_next_action = "find_pdf_or_html_fulltext"
    elif local_suffix == ".pdf" or "pdf" in content_type:
        if text_length >= 3000 and has_msr_terms:
            source_quality_type = "pdf_fulltext"
            source_quality_score = 95
            allowed_extraction_scope = "metadata;experimental"
            extraction_strategy = "pdf_fulltext_metadata_and_experimental"
            recommended_next_action = "run_metadata_and_experimental_extraction"
        else:
            source_quality_type = "no_useful_content"
            source_quality_score = 20
            recommended_next_action = "check_pdf_text_extraction_or_find_better_pdf"
    elif text_length >= 10000 and fulltext_section_count >= 3 and has_msr_terms:
        source_quality_type = "html_fulltext"
        source_quality_score = 90
        allowed_extraction_scope = "metadata;experimental"
        extraction_strategy = "html_fulltext_metadata_and_experimental"
        recommended_next_action = "run_metadata_and_experimental_extraction"
    elif "abstract" in lowered and has_msr_terms and domain_count >= 3:
        source_quality_type = "abstract_only"
        source_quality_score = 60
        allowed_extraction_scope = "metadata;limited_catalyst"
        extraction_strategy = "abstract_metadata_only_no_quantitative_experimental"
        recommended_next_action = "extract_metadata_then_find_fulltext_for_experimental_fields"
    elif "doi_landing" in url_source and text_length >= 200:
        source_quality_type = "doi_landing_page"
        source_quality_score = 30
        allowed_extraction_scope = "bibliographic_metadata"
        extraction_strategy = "bibliographic_metadata_only"
        recommended_next_action = "find_pdf_or_html_fulltext"
    elif text_length >= 500 and domain_count < 3:
        source_quality_type = "navigation_shell"
        source_quality_score = 10
        recommended_next_action = "find_pdf_or_html_fulltext"
    elif text_length >= 500 and experimental_count < 2:
        source_quality_type = "doi_landing_page"
        source_quality_score = 25
        allowed_extraction_scope = "bibliographic_metadata"
        extraction_strategy = "bibliographic_metadata_only"
        recommended_next_action = "find_fulltext_before_field_extraction"

    return {
        "source_quality_type": source_quality_type,
        "source_quality_score": str(source_quality_score),
        "allowed_extraction_scope": allowed_extraction_scope,
        "extraction_strategy": extraction_strategy,
        "recommended_next_action": recommended_next_action,
    }


def choose_best_local_source(paper_id: str, primary_local_path: str) -> Dict[str, object]:
    best: Optional[Dict[str, object]] = None
    for path in candidate_local_files(paper_id, primary_local_path):
        text = load_text_from_local_path(path)
        quality = analyze_text_quality(text)
        score = (
            int(bool(quality["metadata_ready"])) * 6
            + int(bool(quality["experimental_ready"])) * 10
            + int(quality["domain_keyword_count"]) * 2
            + int(quality["experimental_keyword_count"]) * 3
            + min(int(quality["text_length"]) // 500, 12)
        )
        candidate = {
            "best_local_saved_path": str(path.relative_to(ROOT)),
            "best_source_file_name": path.name,
            "best_source_score": score,
            "text": text,
            **quality,
        }
        if best is None or candidate["best_source_score"] > best["best_source_score"]:
            best = candidate

    if best is None:
        return {
            "best_local_saved_path": "",
            "best_source_file_name": "",
            "best_source_score": 0,
            "text": "",
            "text_length": 0,
            "redirect_hits": "",
            "domain_keyword_count": 0,
            "experimental_keyword_count": 0,
            "contains_msr_terms": False,
            "contains_condition_terms": False,
            "contains_performance_terms": False,
            "has_useful_domain_text": False,
            "metadata_ready": False,
            "experimental_ready": False,
            "not_ready_reason": "missing_local_file",
            "source_excerpt_preview": "",
        }
    return best


def build_candidate_map(rows: Iterable[Dict[str, str]]) -> Dict[str, Dict[str, str]]:
    return {str(row.get("paper_id", "")).strip(): row for row in rows if str(row.get("paper_id", "")).strip()}


def extract_excerpt(text: str, start: int, end: int, window: int = 80) -> str:
    left = max(0, start - window)
    right = min(len(text), end + window)
    return normalize_text(text[left:right])


def first_regex_match(patterns: Sequence[str], text: str) -> Tuple[str, str]:
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            value = match.group(1).strip() if match.groups() else match.group(0).strip()
            return value, extract_excerpt(text, match.start(), match.end())
    return "", ""


def detect_metals(text: str) -> List[str]:
    lowered = text.lower()
    found: List[str] = []
    for metal, patterns in METAL_PATTERN_MAP:
        if any(re.search(pattern, lowered) for pattern in patterns):
            found.append(metal)
    return found


def detect_supports(text: str) -> List[str]:
    lowered = text.lower()
    found: List[str] = []
    for support, patterns in SUPPORT_PATTERN_MAP:
        if any(pattern in lowered for pattern in patterns):
            found.append(support)
    deduped: List[str] = []
    for item in found:
        if item not in deduped:
            deduped.append(item)
    return deduped


def detect_preparation_method(text: str) -> Tuple[str, str]:
    lowered = text.lower()
    for label, patterns in PREPARATION_METHOD_MAP:
        for pattern in patterns:
            idx = lowered.find(pattern)
            if idx >= 0:
                return label, extract_excerpt(text, idx, idx + len(pattern))
    return "", ""


def infer_catalyst_family(metals: Sequence[str]) -> str:
    if not metals:
        return ""
    if metals[0] == "Ni":
        return "Ni_based"
    return "other_metal_based"


def excerpt_for_title(value: str) -> str:
    return normalize_text(value)[:240]
