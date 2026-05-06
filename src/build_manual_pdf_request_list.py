"""Build a prioritized list of papers that need manual legal PDF acquisition."""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parent.parent


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build manual PDF request list for high-priority SRM papers.")
    parser.add_argument("--scored", default="data/processed/candidate_papers_high_if_scored.csv")
    parser.add_argument("--manifest", default="data/processed/fulltext_fetch_manifest.csv")
    parser.add_argument("--output", default="data/processed/manual_pdf_request_list.csv")
    return parser.parse_args()


def yes_mask(series: pd.Series) -> pd.Series:
    return series.fillna("").astype(str).str.lower().eq("yes")


def main() -> int:
    args = parse_args()
    scored = pd.read_csv(ROOT / args.scored)
    manifest = pd.read_csv(ROOT / args.manifest) if (ROOT / args.manifest).exists() else pd.DataFrame()

    manifest_columns = [
        "paper_id",
        "source_quality_type",
        "ready_for_extraction",
        "fetch_status",
        "failure_reason",
        "recommended_next_action",
        "access_route",
    ]
    quality = manifest[[column for column in manifest_columns if column in manifest.columns]].copy() if not manifest.empty else pd.DataFrame(columns=manifest_columns)
    merged = scored.merge(quality, on="paper_id", how="left")
    source_type = merged["source_quality_type"].fillna("")
    no_fulltext = ~source_type.isin(["pdf_fulltext", "html_fulltext"])

    mask = (
        (pd.to_numeric(merged["journal_impact_factor"], errors="coerce") >= 6.0)
        & merged["document_type"].fillna("").astype(str).str.lower().eq("journal_article")
        & (pd.to_numeric(merged["relevance_score"], errors="coerce") >= 75)
        & yes_mask(merged["likely_ni_based"])
        & no_fulltext
    )
    out = merged.loc[mask].copy()
    out = out.sort_values(
        by=["priority_score", "journal_impact_factor", "relevance_score"],
        ascending=[False, False, False],
        na_position="last",
    )

    out["failure_reason"] = out["failure_reason"].fillna("").astype(str)
    out.loc[out["failure_reason"].str.strip().eq(""), "failure_reason"] = out["fetch_status"].fillna("").astype(str)
    out.loc[out["failure_reason"].str.strip().eq(""), "failure_reason"] = "no_pdf_or_html_fulltext_available"
    out["suggested_legal_access_route"] = out.apply(
        lambda row: (
            "Use institutional IP/VPN/library link resolver, publisher page, or DOI landing page; if PDF is obtained legally, save it to data/raw/pdfs/ using paper_id.pdf."
            if str(row.get("source_quality_type", "")).strip() not in {"pdf_fulltext", "html_fulltext"}
            else "Already has fulltext; no manual PDF request needed."
        ),
        axis=1,
    )
    out["suggested_search_query"] = out.apply(
        lambda row: f'"{row.get("title", "")}" "{row.get("doi", "")}" PDF',
        axis=1,
    )
    out["manual_status"] = "pending"

    columns = [
        "paper_id",
        "title",
        "journal",
        "doi",
        "journal_impact_factor",
        "priority_score",
        "failure_reason",
        "suggested_legal_access_route",
        "suggested_search_query",
        "manual_status",
    ]
    output_path = ROOT / args.output
    output_path.parent.mkdir(parents=True, exist_ok=True)
    out[columns].to_csv(output_path, index=False, encoding="utf-8")
    print(f"Manual PDF request list written: {output_path}")
    print(f"Rows: {len(out)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
