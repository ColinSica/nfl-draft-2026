"""
Derive 2026 team positional needs from nflverse depth charts, join to the
draft order, and save two processed CSVs.

Source: https://github.com/nflverse/nflverse-data/releases/download/depth_charts/depth_charts_2025.csv
         (cached to data/raw/nflverse_depth_charts_2025.csv)

Needs are computed from the most recent snapshot only. For each team we bucket
roster players into 10 canonical position groups (QB, RB, WR, TE, OL, DL, EDGE,
LB, CB, S), count unique players per group, and compare against a typical
NFL-depth target. The larger the deficit, the higher the need.

Outputs
-------
  data/processed/team_needs_2026.csv     one row per (team, position)
  data/processed/picks_with_needs_2026.csv   draft order × that team's needs
"""

from pathlib import Path

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = ROOT / "data" / "raw"
PROCESSED_DIR = ROOT / "data" / "processed"

DEPTH_URL = ("https://github.com/nflverse/nflverse-data/releases/download/"
             "depth_charts/depth_charts_2025.csv")
DEPTH_CSV = RAW_DIR / "nflverse_depth_charts_2025.csv"
PICKS_CSV = PROCESSED_DIR / "team_context_2026.csv"
NEEDS_CSV = PROCESSED_DIR / "team_needs_2026.csv"
PICKS_WITH_NEEDS_CSV = PROCESSED_DIR / "picks_with_needs_2026.csv"

# pos_abb -> canonical position group (skip special teams)
POS_GROUP = {
    "QB": "QB",
    "RB": "RB", "FB": "RB",
    "WR": "WR",
    "TE": "TE",
    "LT": "OL", "LG": "OL", "C": "OL", "RG": "OL", "RT": "OL",
    "LDE": "EDGE", "RDE": "EDGE",
    "LDT": "DL", "RDT": "DL", "NT": "DL",
    "WLB": "LB", "MLB": "LB", "SLB": "LB", "LILB": "LB", "RILB": "LB",
    "LCB": "CB", "RCB": "CB", "NB": "CB",
    "FS": "S", "SS": "S",
}
POSITION_GROUPS = ["QB", "RB", "WR", "TE", "OL", "DL", "EDGE", "LB", "CB", "S"]

# Rough NFL-depth targets (starters + realistic backup depth)
TARGET_DEPTH = {
    "QB": 3, "RB": 3, "WR": 5, "TE": 3,
    "OL": 8, "DL": 5, "EDGE": 4, "LB": 5, "CB": 5, "S": 4,
}


def fetch_depth_charts() -> pd.DataFrame:
    if DEPTH_CSV.exists():
        df = pd.read_csv(DEPTH_CSV)
        print(f"Loaded cached depth charts: {len(df)} rows")
        return df
    r = requests.get(DEPTH_URL, timeout=120)
    r.raise_for_status()
    DEPTH_CSV.write_bytes(r.content)
    df = pd.read_csv(DEPTH_CSV)
    print(f"Downloaded depth charts: {len(df)} rows -> {DEPTH_CSV}")
    return df


def compute_needs(depth: pd.DataFrame) -> pd.DataFrame:
    latest_dt = depth["dt"].max()
    snap = depth[depth["dt"] == latest_dt].copy()
    # nflverse uses "LA" for the Rams; NFL.com draft order uses "LAR".
    # Normalize to the draft-order convention before aggregating.
    snap["team"] = snap["team"].replace({"LA": "LAR"})
    # Only offense (3WR 1TE) and base defense; skip Special Teams
    snap = snap[snap["pos_grp"].isin(["3WR 1TE", "Base 4-3 D", "Base 3-4 D"])]
    snap["pos_group"] = snap["pos_abb"].map(POS_GROUP)
    snap = snap.dropna(subset=["pos_group", "player_name"])

    # Unique players per (team, pos_group)
    counts = (snap.drop_duplicates(["team", "pos_group", "player_name"])
                   .groupby(["team", "pos_group"]).size()
                   .reset_index(name="player_count"))

    # Ensure every (team, pos_group) exists in the output
    teams = sorted(snap["team"].unique())
    grid = pd.MultiIndex.from_product(
        [teams, POSITION_GROUPS], names=["team", "pos_group"]
    ).to_frame(index=False)
    out = grid.merge(counts, on=["team", "pos_group"], how="left")
    out["player_count"] = out["player_count"].fillna(0).astype(int)
    out["target_depth"] = out["pos_group"].map(TARGET_DEPTH)
    out["deficit"] = (out["target_depth"] - out["player_count"]).clip(lower=0)

    # Rank within team: larger deficit -> rank 1 (biggest need). Stable tiebreak.
    out["need_rank"] = (out.groupby("team")["deficit"]
                           .rank(method="first", ascending=False)
                           .astype(int))
    out = out.rename(columns={"pos_group": "position"})
    out = out[["team", "position", "player_count", "target_depth",
               "deficit", "need_rank"]]
    out = out.sort_values(["team", "need_rank"]).reset_index(drop=True)
    return out


def main():
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    depth = fetch_depth_charts()
    needs = compute_needs(depth)
    needs.to_csv(NEEDS_CSV, index=False)
    print(f"Saved -> {NEEDS_CSV} ({len(needs)} rows)")

    picks = pd.read_csv(PICKS_CSV)
    picks_with_needs = picks.merge(needs, on="team", how="left")
    picks_with_needs.to_csv(PICKS_WITH_NEEDS_CSV, index=False)
    print(f"Saved -> {PICKS_WITH_NEEDS_CSV} ({len(picks_with_needs)} rows)")

    # Summary
    teams_with_needs = needs["team"].nunique()
    total_teams = picks["team"].nunique()
    missing = set(picks["team"].unique()) - set(needs["team"].unique())
    print(f"\nTeams with needs data: {teams_with_needs}/{total_teams}")
    if missing:
        print(f"  Missing: {sorted(missing)}")

    print(f"\nteam_needs_2026.csv rows: {len(needs)}")
    print(f"picks_with_needs_2026.csv rows: {len(picks_with_needs)}")
    print(f"  ({len(picks)} picks × {len(POSITION_GROUPS)} positions per team)")

    print("\nTop 3 needs per team (sample):")
    for team in sorted(needs["team"].unique())[:5]:
        top = needs[needs["team"] == team].head(3)
        tops = [f"{r.position}({r.deficit:.0f})" for r in top.itertuples()]
        print(f"  {team}: {', '.join(tops)}")


if __name__ == "__main__":
    main()
