"""Generate a conservative first-pass SRM extraction draft from fetched text artifacts."""

from __future__ import annotations

import argparse
import csv
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from bs4 import BeautifulSoup


ROOT = Path(__file__).resolve().parent.parent
VENDOR = ROOT / ".vendor"
if VENDOR.exists():
    sys.path.insert(0, str(VENDOR))

try:
    from pypdf import PdfReader  # type: ignore
except Exception:  # pragma: no cover
    PdfReader = None  # type: ignore


OUTPUT_COLUMNS = [
    "paper_id",
    "first_author",
    "publication_year",
    "title",
    "journal",
    "doi",
    "catalyst_label_reported",
    "catalyst_family",
    "active_metal_primary",
    "active_metal_secondary",
    "active_metal_primary_loading_wt_pct",
    "active_metal_secondary_loading_wt_pct",
    "active_metal_total_loading_wt_pct",
    "support_primary",
    "support_secondary",
    "promoter_1",
    "promoter_1_loading_wt_pct",
    "preparation_method",
    "calcination_temperature_c",
    "reduction_temperature_c",
    "reduction_time_h",
    "reduction_gas",
    "reactor_type",
    "temperature_c",
    "pressure_bar",
    "steam_to_carbon_ratio",
    "gas_hourly_space_velocity_h_inv",
    "weight_hourly_space_velocity_h_inv",
    "time_on_stream_h",
    "methane_conversion_pct",
    "h2_yield_pct",
    "h2_selectivity_pct",
    "co_selectivity_pct",
    "h2_co_ratio",
    "stability_test_performed",
    "stability_duration_h",
    "conversion_drop_pct_points",
    "coking_test_method",
    "coke_amount_mg_gcat",
    "coke_amount_wt_pct",
    "measured_value_basis",
    "digitized_from_plot",
    "performance_definition_notes",
    "extraction_notes",
    "analyst_qc_status",
    "extraction_confidence",
    "extraction_source_location",
    "extraction_method",
    "manual_review_required",
    "derived_activity_score",
    "derived_stability_score",
    "derived_coking_resistance_score",
    "derived_overall_screening_score",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate conservative SRM auto-extraction draft.")
    parser.add_argument("--candidates", default="data/processed/candidate_papers_high_if_scored.csv", help="Scored candidate CSV.")
    parser.add_argument("--fetch-log", default="data/processed/fulltext_fetch_manifest.csv", help="Fulltext fetch log CSV.")
    parser.add_argument(
        "--output",
        default="data/processed/srm_extraction_auto_draft.csv",
        help="Output draft extraction CSV.",
    )
    return parser.parse_args()


def read_rows(path: Path) -> List[Dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def normalize_text(value: str) -> str:
    value = (value or "").replace("\x00", " ")
    value = re.sub(r"\s+", " ", value)
    return value.strip()


def extract_text_from_file(path: Path) -> Tuple[str, str]:
    suffix = path.suffix.lower()
    if suffix in {".html", ".htm"}:
        text = path.read_text(encoding="utf-8", errors="ignore")
        soup = BeautifulSoup(text, "html.parser")
        return normalize_text(soup.get_text(" ")), "html_page"
    if suffix == ".pdf" and PdfReader is not None:
        try:
            reader = PdfReader(str(path))
            pages = []
            for page in reader.pages[:8]:
                pages.append(page.extract_text() or "")
            return normalize_text(" ".join(pages)), "pdf_text"
        except Exception:
            return "", "pdf_text_failed"
    text = path.read_text(encoding="utf-8", errors="ignore") if path.exists() else ""
    return normalize_text(text), "plain_text"


def find_first(patterns: List[str], text: str) -> str:
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            return match.group(1) if match.groups() else match.group(0)
    return ""


def infer_catalyst_family(text: str) -> str:
    lowered = text.lower()
    if "nickel" in lowered or re.search(r"\bni\b", lowered):
        return "Ni_based"
    if any(token in lowered for token in ["rhodium", "rhodium", "ruthenium", "platinum", "pt/", "ru/", "rh/"]):
        return "noble_metal_based"
    return ""


def infer_metals(text: str) -> Tuple[str, str]:
    lowered = text.lower()
    metal_map = [
        ("Ni", [r"\bnickel\b", r"\bni\b", r"ni[/\-]"]),
        ("Ru", [r"\bruthenium\b", r"\bru\b", r"ru[/\-]"]),
        ("Rh", [r"\brhodium\b", r"\brh\b", r"rh[/\-]"]),
        ("Pt", [r"\bplatinum\b", r"\bpt\b", r"pt[/\-]"]),
        ("Co", [r"\bcobalt\b", r"co[/\-]", r"[/\-]co\b"]),
        ("Fe", [r"\biron\b", r"fe[/\-]", r"[/\-]fe\b"]),
        ("Cu", [r"\bcopper\b", r"cu[/\-]", r"[/\-]cu\b"]),
    ]
    found: List[str] = []
    for metal, patterns in metal_map:
        if any(re.search(pattern, lowered) for pattern in patterns):
            found.append(metal)
    if not found:
        return "", ""
    if len(found) == 1:
        return found[0], ""
    return found[0], found[1]


def infer_supports(text: str) -> Tuple[str, str]:
    lowered = text.lower()
    support_map = [
        ("Al2O3", ["alumina", "al2o3"]),
        ("CeO2", ["ceria", "ceo2"]),
        ("SiO2", ["silica", "sio2"]),
        ("MgAl2O4", ["mgal2o4"]),
        ("ZrO2", ["zirconia", "zro2"]),
        ("TiO2", ["titania", "tio2"]),
    ]
    found = [label for label, patterns in support_map if any(pattern in lowered for pattern in patterns)]
    if not found:
        return "", ""
    if len(found) == 1:
        return found[0], ""
    return found[0], found[1]


def infer_preparation_method(text: str) -> str:
    lowered = text.lower()
    mapping = [
        ("impregnation", ["impregnation", "incipient wetness"]),
        ("co_precipitation", ["co-precipitation", "coprecipitation", "co precipitation"]),
        ("sol_gel", ["sol-gel", "sol gel"]),
        ("deposition_precipitation", ["deposition precipitation", "deposition-precipitation"]),
        ("hydrothermal", ["hydrothermal"]),
        ("combustion", ["combustion"]),
        ("mechanical_mixing", ["mechanical mixing", "physically mixed"]),
    ]
    for label, patterns in mapping:
        if any(pattern in lowered for pattern in patterns):
            return label
    return ""


def infer_reactor_type(text: str) -> str:
    lowered = text.lower()
    if "fixed-bed" in lowered or "fixed bed" in lowered:
        return "fixed_bed"
    if "packed-bed" in lowered or "packed bed" in lowered:
        return "packed_bed"
    if "fluidized bed" in lowered:
        return "fluidized_bed"
    if "microreactor" in lowered:
        return "microreactor"
    return ""


def infer_measured_value_basis(text: str) -> str:
    lowered = text.lower()
    if "steady-state" in lowered or "steady state" in lowered:
        return "steady_state"
    if "peak" in lowered:
        return "peak"
    if "average" in lowered:
        return "average_over_window"
    if lowered:
        return "unclear"
    return ""


def extract_numeric(pattern: str, text: str) -> str:
    match = re.search(pattern, text, flags=re.IGNORECASE)
    return match.group(1) if match else ""


def build_row(candidate: Dict[str, str], fetch_row: Dict[str, str], text: str, source_location: str) -> Dict[str, str]:
    combined_text = normalize_text(f"{candidate.get('title', '')} {candidate.get('abstract_or_summary', '')} {text}")
    title = candidate.get("title", "")

    active_primary, active_secondary = infer_metals(combined_text)
    support_primary, support_secondary = infer_supports(combined_text)

    row = {column: "" for column in OUTPUT_COLUMNS}
    row["paper_id"] = candidate.get("paper_id", "")
    row["first_author"] = candidate.get("first_author", "")
    row["publication_year"] = candidate.get("publication_year", "")
    row["title"] = candidate.get("title", "")
    row["journal"] = candidate.get("journal", "")
    row["doi"] = candidate.get("doi", "")
    row["catalyst_label_reported"] = title if ("catalyst" in title.lower() or "/" in title) else ""
    row["catalyst_family"] = infer_catalyst_family(combined_text)
    row["active_metal_primary"] = active_primary
    row["active_metal_secondary"] = active_secondary
    row["active_metal_primary_loading_wt_pct"] = extract_numeric(r"(\d+(?:\.\d+)?)\s*(?:wt\.?\s*%|%)\s*(?:ni|nickel)", combined_text)
    row["active_metal_secondary_loading_wt_pct"] = extract_numeric(r"(\d+(?:\.\d+)?)\s*(?:wt\.?\s*%|%)\s*(?:ru|ruthenium|rh|rhodium|pt|platinum|co|cobalt|fe|iron|cu|copper)", combined_text)
    row["active_metal_total_loading_wt_pct"] = ""
    row["support_primary"] = support_primary
    row["support_secondary"] = support_secondary
    promoter = find_first([r"\b(promoted with [a-z0-9\-]+)", r"\b(doped with [a-z0-9\-]+)"], combined_text)
    row["promoter_1"] = promoter
    row["promoter_1_loading_wt_pct"] = ""
    row["preparation_method"] = infer_preparation_method(combined_text)
    row["calcination_temperature_c"] = extract_numeric(r"calcined (?:at|in)\s*(\d+(?:\.\d+)?)\s*(?:°c|c|k)", combined_text)
    row["reduction_temperature_c"] = extract_numeric(r"reduc(?:ed|tion) (?:at|in)\s*(\d+(?:\.\d+)?)\s*(?:°c|c|k)", combined_text)
    row["reduction_time_h"] = extract_numeric(r"reduc(?:ed|tion).*?for\s*(\d+(?:\.\d+)?)\s*h", combined_text)
    row["reduction_gas"] = find_first([r"(?:reduced|reduction) in ([a-z0-9%/\- ]*h2[a-z0-9%/\- ]*)"], combined_text)
    row["reactor_type"] = infer_reactor_type(combined_text)
    row["temperature_c"] = extract_numeric(r"temperature(?: range)?(?: of| was| at)?\s*(\d+(?:\.\d+)?)\s*(?:°c|c|k)", combined_text)
    row["pressure_bar"] = extract_numeric(r"pressure(?: range)?(?: of| was| at)?\s*(\d+(?:\.\d+)?)\s*(?:bar|atm|mpa|kpa)", combined_text)
    row["steam_to_carbon_ratio"] = extract_numeric(r"(?:steam-to-carbon|steam to carbon|s/c)\s*(?:ratio)?(?: of|=)?\s*(\d+(?:\.\d+)?)", combined_text)
    row["gas_hourly_space_velocity_h_inv"] = extract_numeric(r"ghsv(?: of|=)?\s*(\d+(?:\.\d+)?)", combined_text)
    row["weight_hourly_space_velocity_h_inv"] = extract_numeric(r"whsv(?: of|=)?\s*(\d+(?:\.\d+)?)", combined_text)
    row["time_on_stream_h"] = extract_numeric(r"(?:time on stream|tos)(?: of|=)?\s*(\d+(?:\.\d+)?)\s*h", combined_text)
    row["methane_conversion_pct"] = extract_numeric(r"methane conversion(?: of| was|=)?\s*(\d+(?:\.\d+)?)\s*%", combined_text)
    row["h2_yield_pct"] = extract_numeric(r"(?:hydrogen|h2) yield(?: of| was|=)?\s*(\d+(?:\.\d+)?)\s*%", combined_text)
    row["h2_selectivity_pct"] = extract_numeric(r"(?:hydrogen|h2) selectivity(?: of| was|=)?\s*(\d+(?:\.\d+)?)\s*%", combined_text)
    row["co_selectivity_pct"] = extract_numeric(r"co selectivity(?: of| was|=)?\s*(\d+(?:\.\d+)?)\s*%", combined_text)
    row["h2_co_ratio"] = extract_numeric(r"h2/co(?: ratio)?(?: of| was|=)?\s*(\d+(?:\.\d+)?)", combined_text)
    row["stability_test_performed"] = "yes" if any(token in combined_text.lower() for token in ["stability", "time on stream", "deactivation"]) else ""
    row["stability_duration_h"] = extract_numeric(r"(?:stability test|time on stream|stable for)\s*(\d+(?:\.\d+)?)\s*h", combined_text)
    row["conversion_drop_pct_points"] = extract_numeric(r"conversion drop(?: of| was|=)?\s*(\d+(?:\.\d+)?)\s*(?:percentage points|% points|points)", combined_text)
    row["coking_test_method"] = find_first([r"\b(tga)\b", r"\b(tpo)\b", r"\b(raman)\b", r"\b(tem)\b"], combined_text)
    row["coke_amount_mg_gcat"] = extract_numeric(r"coke(?: amount)?(?: of| was|=)?\s*(\d+(?:\.\d+)?)\s*mg/?g", combined_text)
    row["coke_amount_wt_pct"] = extract_numeric(r"coke(?: amount)?(?: of| was|=)?\s*(\d+(?:\.\d+)?)\s*wt\.?\s*%", combined_text)
    row["measured_value_basis"] = infer_measured_value_basis(combined_text)
    row["digitized_from_plot"] = "no"
    row["performance_definition_notes"] = ""
    row["extraction_notes"] = (
        "Automatic heuristic draft from accessible text only; blank fields indicate insufficient confidence. "
        f"fetch_status={fetch_row.get('fetch_status', '')}"
    )
    row["analyst_qc_status"] = "pending"

    extracted_count = sum(1 for key in [
        "active_metal_primary",
        "support_primary",
        "preparation_method",
        "temperature_c",
        "steam_to_carbon_ratio",
        "methane_conversion_pct",
        "h2_yield_pct",
        "stability_duration_h",
        "coke_amount_mg_gcat",
        "coke_amount_wt_pct",
    ] if row.get(key))
    if extracted_count >= 6:
        confidence = "medium"
    elif extracted_count >= 3:
        confidence = "low_to_medium"
    else:
        confidence = "low"

    row["extraction_confidence"] = confidence
    row["extraction_source_location"] = source_location
    row["extraction_method"] = "regex_heuristic_from_accessible_text"
    row["manual_review_required"] = "yes"
    row["derived_activity_score"] = ""
    row["derived_stability_score"] = ""
    row["derived_coking_resistance_score"] = ""
    row["derived_overall_screening_score"] = ""
    return row


def main() -> int:
    args = parse_args()
    candidate_rows = {row["paper_id"]: row for row in read_rows(Path(args.candidates))}
    fetch_rows = [row for row in read_rows(Path(args.fetch_log)) if row.get("usable_for_extraction") == "yes"]

    output_rows: List[Dict[str, str]] = []
    for fetch_row in fetch_rows:
        paper_id = fetch_row.get("paper_id", "")
        candidate = candidate_rows.get(paper_id)
        if not candidate:
            continue
        local_path = Path(fetch_row.get("local_path", ""))
        if not local_path.exists():
            continue
        text, source_location = extract_text_from_file(local_path)
        combined_reference_text = normalize_text(f"{candidate.get('abstract_or_summary', '')} {text}")
        row = build_row(candidate, fetch_row, text, source_location)
        if len(combined_reference_text) < 200:
            row["extraction_confidence"] = "low"
            row["extraction_notes"] = (
                "Automatic heuristic draft from accessible text only; parsed text was short after cleanup, "
                f"so this row should be treated as metadata-only and manually re-checked. fetch_status={fetch_row.get('fetch_status', '')}"
            )
        output_rows.append(row)

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=OUTPUT_COLUMNS)
        writer.writeheader()
        writer.writerows(output_rows)

    print(f"Usable fetch rows: {len(fetch_rows)}")
    print(f"Auto draft rows written: {len(output_rows)}")
    print(f"Output draft: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
