"""
Post-process data/processed/draft_with_college.csv:

  1. Null out college stats for fuzzy matches whose matched name shares
     neither first NOR last token with the draft player name
     (see data/raw/college_stats_fuzzy_review.csv).
  2. Add missingness indicator columns (has_passing, has_rushing,
     has_receiving, has_defensive, has_college_stats).
  3. Print a data-quality summary.

Overwrites draft_with_college.csv in place.
"""

from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
MERGED_CSV = ROOT / "data" / "processed" / "draft_with_college.csv"
REVIEW_CSV = ROOT / "data" / "raw" / "college_stats_fuzzy_review.csv"

STAT_GROUPS = {
    "passing":   ["pass_att", "pass_cmp", "pass_cmp_pct", "pass_int",
                  "pass_td", "pass_yds", "pass_ypa"],
    "rushing":   ["rush_att", "rush_long", "rush_td", "rush_yds", "rush_ypc"],
    "receiving": ["rec", "rec_long", "rec_td", "rec_yds", "rec_ypr"],
    "defensive": ["def_int", "def_int_avg", "def_int_td", "def_int_yds",
                  "def_pd", "def_qb_hur", "def_sacks", "def_solo",
                  "def_tfl", "def_tot", "defensive_td"],
}
MATCH_META = ["_match_score", "_matched_name", "_matched_team"]
ALL_STAT_COLS = [c for cols in STAT_GROUPS.values() for c in cols]

SUFFIXES = {"jr", "sr", "ii", "iii", "iv", "v"}


def name_tokens(name: str) -> list[str]:
    if not isinstance(name, str):
        return []
    n = name.lower().replace("-", " ").replace("'", "").replace(".", "").replace(",", "")
    return [p for p in n.split() if p and p not in SUFFIXES]


def shares_first_or_last(a: str, b: str) -> bool:
    ta, tb = name_tokens(a), name_tokens(b)
    if not ta or not tb:
        return False
    return ta[0] == tb[0] or ta[-1] == tb[-1]


def main():
    df = pd.read_csv(MERGED_CSV)
    review = pd.read_csv(REVIEW_CSV)
    print(f"Loaded {len(df)} draft rows and {len(review)} review rows")

    # --- 1. Null out false-positive fuzzy matches ---------------------------
    bad = review[~review.apply(
        lambda r: shares_first_or_last(r["draft_player"], r["matched_name"]),
        axis=1,
    )].copy()
    bad_keys = set(zip(bad["draft_player"], bad["year"].astype(int)))
    print(f"Flagged {len(bad_keys)} (player, year) pairs for nulling")

    df_key = list(zip(df["player"], df["year"].astype("Int64")))
    mask = pd.Series([k in bad_keys for k in df_key], index=df.index)
    nulled_rows = int(mask.sum())

    cols_to_null = [c for c in ALL_STAT_COLS + MATCH_META if c in df.columns]
    df.loc[mask, cols_to_null] = pd.NA
    print(f"Nulled stat columns on {nulled_rows} row(s)")

    if not bad.empty:
        print("\nNulled matches:")
        for _, r in bad.iterrows():
            print(f"  {r['draft_player']} ({r['draft_college']}) "
                  f"-> {r['matched_name']} ({r['matched_team']})  score={r['score']:.0f}")

    # --- 2. Add has_{group} + has_college_stats -----------------------------
    for group, cols in STAT_GROUPS.items():
        present = [c for c in cols if c in df.columns]
        df[f"has_{group}"] = df[present].notna().any(axis=1).astype(int) if present else 0

    df["has_college_stats"] = df["_match_score"].notna().astype(int) \
        if "_match_score" in df.columns else 0

    df.to_csv(MERGED_CSV, index=False)
    print(f"\nSaved -> {MERGED_CSV}")

    # --- 3. Summary ---------------------------------------------------------
    print("\n" + "=" * 60)
    print("DATA QUALITY SUMMARY")
    print("=" * 60)
    print(f"Rows:    {len(df)}")
    print(f"Columns: {df.shape[1]}")
    print(f"Rows nulled in cleanup: {nulled_rows}")

    print("\nHas-stat indicator totals:")
    for group in list(STAT_GROUPS) + ["college_stats"]:
        col = f"has_{group}"
        if col in df.columns:
            n = int(df[col].sum())
            print(f"  {col:<22} {n:>5} / {len(df)} ({n/len(df)*100:.1f}%)")

    print("\nRow counts by position group:")
    if "position_group" in df.columns:
        for g, n in df["position_group"].value_counts().items():
            print(f"  {g:<6} {n}")

    print("\n% missing per column (descending):")
    miss = (df.isna().mean() * 100).sort_values(ascending=False)
    for col, pct in miss.items():
        print(f"  {pct:5.1f}%  {col}")


if __name__ == "__main__":
    main()
