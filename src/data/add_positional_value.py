"""
Add positional-value features to draft_with_college.csv (historical 2020+)
and prospects_2026_enriched.csv, plus draft-capital features to
team_context_2026_enriched.csv.

Schema additions (both files):
  - positional_value_prior, positional_value_adjusted
  - position_historical_round_avg, position_historical_round_std

Prospects-only:
  - is_position_rank_1, position_gap_to_next, position_elite_flag
  - positional_value_tension

Team-only:
  - draft_capital_volume, capital_abundance_flag
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
PROC_DIR = ROOT / "data" / "processed"

HIST_CSV = PROC_DIR / "draft_with_college.csv"
PROS_CSV = PROC_DIR / "prospects_2026_enriched.csv"
TEAM_CSV = PROC_DIR / "team_context_2026_enriched.csv"
TEAM_CTX_RAW = PROC_DIR / "team_context_2026.csv"

# User-specified literal dict
POS_VALUE_USER = {
    "QB": 10, "EDGE": 9,
    "OT": 8, "LT": 8,
    "WR": 7, "CB": 7,
    "IDL": 6, "DT": 6,
    "LB": 5, "TE": 5,
    "S": 4,
    "G": 3, "C": 3,
    "RB": 2,
}

# Conservative aliases for codes that appear in the data but aren't in the user dict.
# We apply these AFTER the user dict so direct matches take precedence.
POS_VALUE_ALIAS = {
    # Tackles
    "T": 8, "RT": 8,
    # EDGE variants
    "DE": 9,
    # Interior DL
    "NT": 6, "DL": 6,
    # LB variants
    "ILB": 5, "OLB": 5, "MLB": 5, "WLB": 5, "SLB": 5,
    # DB variants
    "FS": 4, "SS": 4, "DB": 4, "SAF": 4,
    # Interior OL
    "OG": 3, "IOL": 3, "OL": 3,
    # RB variants
    "FB": 2, "HB": 2,
    # Specialists
    "K": 1, "P": 1, "LS": 1,
}


def map_positional_value(pos: str | float):
    if not isinstance(pos, str):
        return (np.nan, "missing")
    p = pos.strip().upper()
    if p in POS_VALUE_USER:
        return (POS_VALUE_USER[p], "user_dict")
    if p in POS_VALUE_ALIAS:
        return (POS_VALUE_ALIAS[p], "alias")
    return (np.nan, "unmapped")


def add_positional_value_prior(df: pd.DataFrame) -> dict:
    """Return a summary dict of matched / aliased / unmapped counts."""
    summary = {"user_dict": 0, "alias": 0, "unmapped": set(), "missing": 0}
    vals = []
    for pos in df["position"]:
        v, src = map_positional_value(pos)
        vals.append(v)
        if src == "unmapped":
            summary["unmapped"].add(str(pos).upper())
        elif src == "missing":
            summary["missing"] += 1
        else:
            summary[src] += 1
    df["positional_value_prior"] = vals
    return summary


def add_positional_value_adjusted(df: pd.DataFrame) -> None:
    depth = df.get("draft_class_position_depth")
    if depth is None:
        df["positional_value_adjusted"] = df["positional_value_prior"]
        return
    denom = 1 + 0.1 * depth.fillna(0)
    df["positional_value_adjusted"] = df["positional_value_prior"] / denom


def compute_historical_round_stats(hist: pd.DataFrame) -> pd.DataFrame:
    """round mean/std by position in 2020-2025 historical data."""
    sub = hist.dropna(subset=["position", "round"]).copy()
    stats = (sub.groupby("position")["round"]
                 .agg(["mean", "std"])
                 .rename(columns={"mean": "position_historical_round_avg",
                                  "std": "position_historical_round_std"})
                 .reset_index())
    return stats


def join_round_stats(df: pd.DataFrame, stats: pd.DataFrame) -> pd.DataFrame:
    return df.merge(stats, how="left", on="position")


def add_prospect_only_features(pros: pd.DataFrame) -> None:
    """is_position_rank_1, position_gap_to_next, position_elite_flag,
    positional_value_tension — all use position_group-based position_rank
    because that's how position_rank is defined upstream."""
    pros["is_position_rank_1"] = (pros["position_rank"] == 1).astype(int)

    # position_gap_to_next: gap from this player's rank to the rank of the
    # #2 player in the same position_group. 0 for non-rank-1 players.
    gaps = []
    for _, row in pros.iterrows():
        if row.get("position_rank") != 1:
            gaps.append(0)
            continue
        grp = row.get("position_group")
        me = row.get("rank")
        if pd.isna(me) or not isinstance(grp, str):
            gaps.append(0)
            continue
        next_row = pros[(pros["position_group"] == grp) & (pros["position_rank"] == 2)]
        if next_row.empty or pd.isna(next_row["rank"].iloc[0]):
            gaps.append(0)
            continue
        gaps.append(int(next_row["rank"].iloc[0] - me))
    pros["position_gap_to_next"] = gaps

    pros["position_elite_flag"] = (
        (pros["is_position_rank_1"] == 1) & (pros["position_gap_to_next"] > 15)
    ).astype(int)

    pros["positional_value_tension"] = (
        (pros["rank"] <= 15) & (pros["positional_value_prior"] <= 4)
    ).astype(int)


def add_team_capital(team: pd.DataFrame) -> None:
    if not TEAM_CTX_RAW.exists():
        print("[team] team_context_2026.csv missing — skipping draft_capital_volume")
        team["draft_capital_volume"] = np.nan
        team["capital_abundance_flag"] = np.nan
        return
    raw = pd.read_csv(TEAM_CTX_RAW)
    counts = raw.groupby("team").size().rename("draft_capital_volume")
    team["draft_capital_volume"] = team["team"].map(counts).fillna(0).astype(int)

    def flag(n: int) -> float:
        if n >= 8:
            return 1.0
        if n >= 6:
            return 0.5
        return 0.0
    team["capital_abundance_flag"] = team["draft_capital_volume"].apply(flag)


def main():
    hist = pd.read_csv(HIST_CSV)
    pros = pd.read_csv(PROS_CSV)
    team = pd.read_csv(TEAM_CSV)

    # ---- a. positional_value_prior ----
    print("[a] positional_value_prior")
    summ_hist = add_positional_value_prior(hist)
    summ_pros = add_positional_value_prior(pros)
    for label, summ in (("historical", summ_hist), ("prospects", summ_pros)):
        print(f"  {label}: user_dict={summ['user_dict']}  alias={summ['alias']}  "
              f"missing={summ['missing']}  unmapped_codes={sorted(summ['unmapped'])}")

    # ---- b. positional_value_adjusted ----
    print("[b] positional_value_adjusted")
    add_positional_value_adjusted(hist)
    add_positional_value_adjusted(pros)

    # ---- c. round mean/std from historical ----
    print("[c] position_historical_round_avg / _std")
    stats = compute_historical_round_stats(hist)
    hist = join_round_stats(hist.drop(columns=[c for c in (
        "position_historical_round_avg", "position_historical_round_std"
    ) if c in hist.columns]), stats)
    pros = join_round_stats(pros.drop(columns=[c for c in (
        "position_historical_round_avg", "position_historical_round_std"
    ) if c in pros.columns]), stats)
    print(f"  historical coverage: {hist['position_historical_round_avg'].notna().mean()*100:.1f}%  "
          f"prospects coverage: {pros['position_historical_round_avg'].notna().mean()*100:.1f}%")

    # ---- d. prospect-only features ----
    print("[d] is_position_rank_1 / position_gap_to_next / position_elite_flag / "
          "positional_value_tension")
    add_prospect_only_features(pros)
    print(f"  position_elite_flag = 1: {int(pros['position_elite_flag'].sum())}")
    print(f"  positional_value_tension = 1: {int(pros['positional_value_tension'].sum())}")

    # ---- e. draft capital volume ----
    print("[e] draft_capital_volume / capital_abundance_flag")
    add_team_capital(team)
    print(f"  teams with >=8 picks: {int((team['capital_abundance_flag'] == 1.0).any(axis=None))}")

    hist.to_csv(HIST_CSV, index=False)
    pros.to_csv(PROS_CSV, index=False)
    team.to_csv(TEAM_CSV, index=False)

    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"draft_with_college.csv: {hist.shape[1]} cols")
    print(f"prospects_2026_enriched.csv: {pros.shape[1]} cols")
    print(f"team_context_2026_enriched.csv: {team.shape[1]} cols")


if __name__ == "__main__":
    main()
