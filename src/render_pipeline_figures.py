from __future__ import annotations

from pathlib import Path
from typing import Dict, List

import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data" / "processed"
OUTPUT_DIR = ROOT / "outputs" / "figures"


def load_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"Missing required input: {path}")
    return pd.read_csv(path)


def safe_int(value: object) -> int:
    if pd.isna(value):
        return 0
    return int(value)


def collect_metrics() -> Dict[str, int]:
    candidate_master = load_csv(DATA_DIR / "candidate_papers_master.csv")
    candidate_scored = load_csv(DATA_DIR / "candidate_papers_high_if_scored.csv")
    eligible_pool = load_csv(DATA_DIR / "eligible_high_if_pool.csv")
    fetch_manifest = load_csv(DATA_DIR / "fulltext_fetch_manifest.csv")
    auto_draft = load_csv(DATA_DIR / "srm_extraction_auto_draft.csv")
    record_flags = load_csv(DATA_DIR / "srm_extraction_record_flags.csv")

    analysis_ready_count = 0
    if "analysis_ready_flag" in record_flags.columns:
        analysis_ready_count = safe_int(
            (record_flags["analysis_ready_flag"].fillna("").astype(str).str.lower() == "yes").sum()
        )

    eligible_fetch_count = 0
    if "ready_for_extraction" in fetch_manifest.columns:
        eligible_fetch_count = safe_int(
            (fetch_manifest["ready_for_extraction"].fillna("").astype(str).str.lower() == "yes").sum()
        )

    metrics = {
        "candidate_master": len(candidate_master),
        "high_if_scored": len(candidate_scored),
        "eligible_high_if": len(eligible_pool),
        "fetch_manifest": len(fetch_manifest),
        "ready_for_extraction": eligible_fetch_count,
        "auto_draft": len(auto_draft),
        "analysis_ready": analysis_ready_count,
    }
    return metrics


def save_candidate_pool_summary() -> Path:
    candidate_master = load_csv(DATA_DIR / "candidate_papers_master.csv")
    candidate_scored = load_csv(DATA_DIR / "candidate_papers_high_if_scored.csv")
    eligible_pool = load_csv(DATA_DIR / "eligible_high_if_pool.csv")
    backup_pool = load_csv(DATA_DIR / "backup_low_if_pool.csv")

    if "needs_manual_journal_check" in candidate_scored.columns:
        needs_manual = safe_int(
            (candidate_scored["needs_manual_journal_check"].fillna("").astype(str).str.lower() == "yes").sum()
        )
    else:
        needs_manual = 0

    if "journal_impact_factor" in candidate_scored.columns:
        high_if = safe_int(pd.to_numeric(candidate_scored["journal_impact_factor"], errors="coerce").ge(6.0).sum())
    else:
        high_if = 0

    labels = [
        "Master pool",
        "Scored pool",
        "IF >= 6",
        "Eligible high-IF",
        "Backup pool",
        "Manual IF check",
    ]
    values = [
        len(candidate_master),
        len(candidate_scored),
        high_if,
        len(eligible_pool),
        len(backup_pool),
        needs_manual,
    ]

    fig, ax = plt.subplots(figsize=(10, 6))
    colors = ["#224e7a", "#2c7da0", "#90be6d", "#43aa8b", "#f9c74f", "#f9844a"]
    bars = ax.bar(labels, values, color=colors)
    ax.set_title("SRM Candidate Pool Funnel")
    ax.set_ylabel("Paper count")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.tick_params(axis="x", rotation=20)

    for bar, value in zip(bars, values):
        ax.text(bar.get_x() + bar.get_width() / 2, value + 1, str(value), ha="center", va="bottom", fontsize=10)

    fig.tight_layout()
    out_path = OUTPUT_DIR / "candidate_pool_summary.png"
    fig.savefig(out_path, dpi=200, bbox_inches="tight")
    plt.close(fig)
    return out_path


def save_fetch_status_summary() -> Path:
    fetch_manifest = load_csv(DATA_DIR / "fulltext_fetch_manifest.csv")
    counts = fetch_manifest["fetch_status"].fillna("unknown").value_counts()

    fig, ax = plt.subplots(figsize=(9, 5))
    colors = ["#43aa8b" if status in {"success", "skipped_existing"} else "#f9844a" for status in counts.index]
    bars = ax.barh(counts.index.tolist(), counts.values.tolist(), color=colors)
    ax.set_title("Stage4 Fetch Status Summary")
    ax.set_xlabel("Record count")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    for bar, value in zip(bars, counts.values.tolist()):
        ax.text(value + 0.1, bar.get_y() + bar.get_height() / 2, str(value), va="center", fontsize=10)

    fig.tight_layout()
    out_path = OUTPUT_DIR / "fetch_status_summary.png"
    fig.savefig(out_path, dpi=200, bbox_inches="tight")
    plt.close(fig)
    return out_path


def save_qc_coverage_summary() -> Path:
    qc_summary = load_csv(DATA_DIR / "srm_extraction_qc_summary.csv")
    qc_summary = qc_summary.sort_values(by="coverage_rate", ascending=False).head(12).copy()

    fig, ax = plt.subplots(figsize=(10, 7))
    coverage_pct = qc_summary["coverage_rate"].fillna(0) * 100
    bars = ax.barh(qc_summary["field_name"], coverage_pct, color="#577590")
    ax.invert_yaxis()
    ax.set_title("Top Field Coverage in Auto Extraction Draft")
    ax.set_xlabel("Coverage (%)")
    ax.set_xlim(0, 105)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    for bar, value in zip(bars, coverage_pct.tolist()):
        ax.text(min(value + 1.0, 102), bar.get_y() + bar.get_height() / 2, f"{value:.1f}%", va="center", fontsize=9)

    fig.tight_layout()
    out_path = OUTPUT_DIR / "qc_coverage_summary.png"
    fig.savefig(out_path, dpi=200, bbox_inches="tight")
    plt.close(fig)
    return out_path


def save_ni_based_subset_summary() -> Path:
    candidate_master = load_csv(DATA_DIR / "candidate_papers_master.csv")
    candidate_scored = load_csv(DATA_DIR / "candidate_papers_high_if_scored.csv")
    eligible_pool = load_csv(DATA_DIR / "eligible_high_if_pool.csv")
    top50 = load_csv(DATA_DIR / "candidate_papers_top50.csv")
    top100 = load_csv(DATA_DIR / "candidate_papers_top100.csv")

    def count_ni(df: pd.DataFrame) -> int:
        if "likely_ni_based" not in df.columns:
            return 0
        return safe_int((df["likely_ni_based"].fillna("").astype(str).str.lower() == "yes").sum())

    master_titles = candidate_master["paper_id"].nunique()
    scored_titles = candidate_scored["paper_id"].nunique()
    eligible_titles = eligible_pool["paper_id"].nunique()
    top50_titles = top50["paper_id"].nunique()
    top100_titles = top100["paper_id"].nunique()

    values_total = [master_titles, scored_titles, top100_titles, top50_titles, eligible_titles]
    values_ni = [0, count_ni(candidate_scored), count_ni(top100), count_ni(top50), count_ni(eligible_pool)]
    labels = ["Master pool", "Scored pool", "Top 100", "Top 50", "Eligible high-IF"]

    fig, ax = plt.subplots(figsize=(10.5, 6.2))
    x = range(len(labels))
    width = 0.38

    ax.bar([i - width / 2 for i in x], values_total, width=width, color="#cbd5e1", label="All papers")
    ax.bar([i + width / 2 for i in x], values_ni, width=width, color="#2a9d8f", label="Likely Ni-based")

    ax.set_title("Ni-based Subset Size Across the Batch Pipeline")
    ax.set_ylabel("Paper count")
    ax.set_xticks(list(x))
    ax.set_xticklabels(labels, rotation=15)
    ax.legend(frameon=False)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    for i, (total_v, ni_v) in enumerate(zip(values_total, values_ni)):
        ax.text(i - width / 2, total_v + 1, str(total_v), ha="center", va="bottom", fontsize=9)
        ax.text(i + width / 2, ni_v + 1, str(ni_v), ha="center", va="bottom", fontsize=9)

    ax.text(
        0.98,
        0.96,
        "Note: master pool has no stable Ni flag yet,\nso Ni count starts from the scored pool.",
        transform=ax.transAxes,
        ha="right",
        va="top",
        fontsize=9,
        color="#475569",
    )

    fig.tight_layout()
    out_path = OUTPUT_DIR / "ni_based_subset_summary.png"
    fig.savefig(out_path, dpi=200, bbox_inches="tight")
    plt.close(fig)
    return out_path


def add_box(ax, x: float, y: float, w: float, h: float, title: str, lines: List[str], facecolor: str) -> None:
    box = FancyBboxPatch(
        (x, y),
        w,
        h,
        boxstyle="round,pad=0.02,rounding_size=0.02",
        linewidth=1.5,
        edgecolor="#1f2937",
        facecolor=facecolor,
    )
    ax.add_patch(box)
    ax.text(x + 0.02, y + h - 0.06, title, fontsize=12, weight="bold", va="top", ha="left", color="#111827")
    ax.text(x + 0.02, y + h - 0.12, "\n".join(lines), fontsize=10, va="top", ha="left", color="#1f2937")


def save_pipeline_overview(metrics: Dict[str, int]) -> Path:
    fig, ax = plt.subplots(figsize=(15, 5.5))
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")

    stages = [
        (
            0.02,
            "Stage1-3\nSearch / Enrich / Score",
            [
                f"Master pool: {metrics['candidate_master']}",
                f"Scored pool: {metrics['high_if_scored']}",
                f"Eligible high-IF: {metrics['eligible_high_if']}",
            ],
            "#dbeafe",
        ),
        (
            0.26,
            "Stage4\nFetch Sources",
            [
                f"Manifest rows: {metrics['fetch_manifest']}",
                f"Ready for extraction: {metrics['ready_for_extraction']}",
                "Resume + skip supported",
            ],
            "#dcfce7",
        ),
        (
            0.50,
            "Stage5\nAuto Extraction Draft",
            [
                f"Draft rows: {metrics['auto_draft']}",
                "Only confirmed values filled",
                "Derived fields stay empty",
            ],
            "#fef3c7",
        ),
        (
            0.74,
            "Stage6-7\nQC / Freeze / Export",
            [
                f"Analysis-ready rows: {metrics['analysis_ready']}",
                "Record flags + field coverage",
                "No modeling in this stage",
            ],
            "#fee2e2",
        ),
    ]

    for idx, (x, title, lines, facecolor) in enumerate(stages):
        add_box(ax, x, 0.25, 0.20, 0.45, title, lines, facecolor)
        if idx < len(stages) - 1:
            ax.annotate(
                "",
                xy=(x + 0.235, 0.475),
                xytext=(x + 0.205, 0.475),
                arrowprops=dict(arrowstyle="->", lw=2, color="#475569"),
            )

    ax.text(
        0.02,
        0.9,
        "SRM Batch Literature Pipeline Overview",
        fontsize=18,
        weight="bold",
        ha="left",
        color="#0f172a",
    )
    ax.text(
        0.02,
        0.83,
        "Focus: large-scale candidate screening, source fetching, conservative extraction, QC, and analysis-ready export.",
        fontsize=11,
        ha="left",
        color="#334155",
    )

    out_path = OUTPUT_DIR / "pipeline_overview.png"
    fig.savefig(out_path, dpi=200, bbox_inches="tight")
    plt.close(fig)
    return out_path


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    metrics = collect_metrics()
    generated = [
        save_pipeline_overview(metrics),
        save_candidate_pool_summary(),
        save_fetch_status_summary(),
        save_qc_coverage_summary(),
        save_ni_based_subset_summary(),
    ]
    for path in generated:
        print(path.relative_to(ROOT))


if __name__ == "__main__":
    main()
