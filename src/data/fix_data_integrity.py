"""
Pre-modeling integrity fixes:

1. Dedupe data/processed/draft_with_college.csv by (player, year, pick).
   Duplicates are produced when the college-stats fuzzy match hits multiple
   roster entries for a single draft pick; keep the row with the most
   non-null stat values (tiebreak on _match_score).

2. Align prospects_2026.csv column names and indicators with the historical
   file: rename school -> college, age_at_draft -> age, and add
   has_passing / has_rushing / has_receiving / has_defensive /
   has_college_stats (derived from null checks on the stat columns).

Both files are overwritten in place.
"""

from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
HIST_CSV = ROOT / "data" / "processed" / "draft_with_college.csv"
PROS_CSV = ROOT / "data" / "processed" / "prospects_2026.csv"

STAT_GROUPS = {
    "passing":   ["pass_att", "pass_cmp", "pass_cmp_pct", "pass_int",
                  "pass_td", "pass_yds", "pass_ypa"],
    "rushing":   ["rush_att", "rush_long", "rush_td", "rush_yds", "rush_ypc"],
    "receiving": ["rec", "rec_long", "rec_td", "rec_yds", "rec_ypr"],
    "defensive": ["def_int", "def_int_avg", "def_int_td", "def_int_yds",
                  "def_pd", "def_qb_hur", "def_sacks", "def_solo",
                  "def_tfl", "def_tot", "defensive_td"],
}
ALL_STAT_COLS = [c for cols in STAT_GROUPS.values() for c in cols]


def dedupe_historical(df: pd.DataFrame) -> pd.DataFrame:
    stat_cols = [c for c in ALL_STAT_COLS if c in df.columns]
    df = df.copy()
    df["_nstats"] = df[stat_cols].notna().sum(axis=1)
    if "_match_score" in df.columns:
        df["_ms"] = pd.to_numeric(df["_match_score"], errors="coerce").fillna(-1.0)
    else:
        df["_ms"] = -1.0
    df = df.sort_values(
        ["player", "year", "pick", "_nstats", "_ms"],
        ascending=[True, True, True, False, False],
    )
    df = df.drop_duplicates(subset=["player", "year", "pick"], keep="first")
    return df.drop(columns=["_nstats", "_ms"])


def byron_young_summary(df: pd.DataFrame, label: str) -> None:
    by = df[(df["player"] == "Byron Young") & (df["year"] == 2023)]
    picks = sorted(int(p) for p in by["pick"].dropna().unique())
    print(f"  Byron Young 2023 ({label}): {len(by)} row(s), picks={picks}")


def align_prospects(p: pd.DataFrame) -> pd.DataFrame:
    p = p.copy()
    rename = {}
    if "school" in p.columns and "college" not in p.columns:
        rename["school"] = "college"
    if "age_at_draft" in p.columns and "age" not in p.columns:
        rename["age_at_draft"] = "age"
    if rename:
        p = p.rename(columns=rename)

    for group, cols in STAT_GROUPS.items():
        present = [c for c in cols if c in p.columns]
        flag = f"has_{group}"
        if present:
            p[flag] = p[present].notna().any(axis=1).astype(int)
        else:
            p[flag] = 0

    group_flags = [f"has_{g}" for g in STAT_GROUPS]
    p["has_college_stats"] = p[group_flags].max(axis=1).astype(int)
    return p


def main():
    hist = pd.read_csv(HIST_CSV)
    pros = pd.read_csv(PROS_CSV)

    print("=" * 60)
    print("BEFORE")
    print("=" * 60)
    print(f"  draft_with_college: {len(hist):>5} rows x {hist.shape[1]:>3} cols")
    print(f"  prospects_2026:     {len(pros):>5} rows x {pros.shape[1]:>3} cols")

    hist_dupe_keys = hist.groupby(["player", "year", "pick"]).size()
    hist_dupe_keys = hist_dupe_keys[hist_dupe_keys > 1]
    print(f"  historical (player, year, pick) duplicate keys: {len(hist_dupe_keys)}")
    byron_young_summary(hist, "before")

    # ---- 1. Dedupe historical ----
    hist_fixed = dedupe_historical(hist)

    # ---- 2. Align prospects ----
    pros_fixed = align_prospects(pros)

    hist_fixed.to_csv(HIST_CSV, index=False)
    pros_fixed.to_csv(PROS_CSV, index=False)

    print("\n" + "=" * 60)
    print("AFTER")
    print("=" * 60)
    print(f"  draft_with_college: {len(hist_fixed):>5} rows x "
          f"{hist_fixed.shape[1]:>3} cols  "
          f"(removed {len(hist) - len(hist_fixed)})")
    print(f"  prospects_2026:     {len(pros_fixed):>5} rows x "
          f"{pros_fixed.shape[1]:>3} cols  "
          f"(+{pros_fixed.shape[1] - pros.shape[1]} cols)")

    remaining = hist_fixed.groupby(["player", "year", "pick"]).size()
    remaining = remaining[remaining > 1]
    print(f"  historical duplicates remaining: {len(remaining)}")
    byron_young_summary(hist_fixed, "after")

    shared = sorted(set(hist_fixed.columns) & set(pros_fixed.columns))
    only_h = sorted(set(hist_fixed.columns) - set(pros_fixed.columns))
    only_p = sorted(set(pros_fixed.columns) - set(hist_fixed.columns))
    print(f"\nColumn overlap: shared={len(shared)}  "
          f"hist-only={len(only_h)}  prospects-only={len(only_p)}")
    print(f"  hist-only:      {only_h}")
    print(f"  prospects-only: {only_p}")


if __name__ == "__main__":
    main()
