"""
Final enrichment (prospects-only):

  5. visit_exclusivity        1 if visit_count == 1 else 0
  6. market_consensus_score   weighted composite of market signals
  7. position_scarcity_vs_historical
                             (historical_avg - class_2026_count) / historical_std
                             by position, positive = scarcer than usual
"""

from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
PROC_DIR = ROOT / "data" / "processed"
HIST_CSV = PROC_DIR / "draft_with_college.csv"
PROS_CSV = PROC_DIR / "prospects_2026_enriched.csv"


def add_visit_exclusivity(pros: pd.DataFrame) -> None:
    vc = pros.get("visit_count", pd.Series([0] * len(pros))).fillna(0)
    pros["visit_exclusivity"] = (vc == 1).astype(int)


def add_market_consensus_score(pros: pd.DataFrame) -> None:
    # Higher rank (closer to 1) = better. Invert.
    rank = pros["rank"].astype(float)
    max_rank = max(len(pros), 728)
    rank_term = (1.0 - rank / max_rank).clip(0, 1)

    mock = pros.get("first_round_mock_rate", pd.Series([0] * len(pros))).fillna(0)
    intel = pros.get("intel_link_max", pd.Series([0] * len(pros))).fillna(0) / 3.0
    raw = rank_term * 0.6 + mock * 0.3 + intel * 0.1
    # Normalize 0-1 across the set
    rng = raw.max() - raw.min()
    pros["market_consensus_score"] = (raw - raw.min()) / rng if rng > 0 else 0.0


def add_position_scarcity(hist: pd.DataFrame, pros: pd.DataFrame) -> None:
    """(historical_avg - class_2026_count) / historical_std per position."""
    hist_counts = (hist.groupby(["year", "position"]).size()
                       .reset_index(name="n"))
    # Only positions that appear in ≥2 historical years for a stable std
    stats = (hist_counts.groupby("position")["n"]
                         .agg(["mean", "std"]).reset_index())
    stats = stats.rename(columns={"mean": "hist_avg", "std": "hist_std"})

    class_counts = pros.groupby("position").size().rename("class_2026_count")

    pros["_class_cnt"] = pros["position"].map(class_counts).fillna(0)
    stats_map = stats.set_index("position")
    pros["_hist_avg"] = pros["position"].map(stats_map["hist_avg"])
    pros["_hist_std"] = pros["position"].map(stats_map["hist_std"])

    # Scarcity: positive when fewer 2026 prospects than historical avg
    denom = pros["_hist_std"].replace(0, np.nan)
    pros["position_scarcity_vs_historical"] = (
        (pros["_hist_avg"] - pros["_class_cnt"]) / denom
    )
    pros.drop(columns=["_class_cnt", "_hist_avg", "_hist_std"], inplace=True)


def main():
    hist = pd.read_csv(HIST_CSV)
    pros = pd.read_csv(PROS_CSV)
    before = pros.shape[1]

    add_visit_exclusivity(pros)
    add_market_consensus_score(pros)
    add_position_scarcity(hist, pros)

    pros.to_csv(PROS_CSV, index=False)
    print(f"prospects_2026_enriched.csv: {before} -> {pros.shape[1]} cols")

    # Coverage
    print(f"\nvisit_exclusivity=1: {int(pros['visit_exclusivity'].sum())}")
    mcs = pros["market_consensus_score"]
    print(f"market_consensus_score range: [{mcs.min():.3f}, {mcs.max():.3f}]  "
          f"mean {mcs.mean():.3f}")
    psv = pros["position_scarcity_vs_historical"]
    print(f"position_scarcity_vs_historical non-null: {psv.notna().sum()}/{len(pros)}  "
          f"range [{psv.min():.2f}, {psv.max():.2f}]")


if __name__ == "__main__":
    main()
