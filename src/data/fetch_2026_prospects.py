"""
Fetch 2026 NFL draft prospect data.

Steps
-----
1. Scrape the NFL Mock Draft Database consensus big board for 2026.
2. Fetch the 2025 college season from the CFBD API (5 categories).
3. Fuzzy-match each prospect to their 2025 college stats.

Outputs
-------
  data/raw/prospects_2026_consensus.csv
  data/raw/college_stats_api_2026.json   (draft-year convention; contains 2025 season)
  data/processed/prospects_2026.csv
"""

import json
import sys
import time
from pathlib import Path

import pandas as pd
import undetected_chromedriver as uc
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from fetch_college_stats_api import (  # noqa: E402
    fetch_season,
    index_by_team,
    load_api_key,
    match_player,
    pivot_wide,
    position_group,
)

RAW_DIR = ROOT / "data" / "raw"
PROCESSED_DIR = ROOT / "data" / "processed"

BIGBOARD_URL = "https://www.nflmockdraftdatabase.com/big-boards/2026/consensus-big-board-2026"
BIGBOARD_CSV = RAW_DIR / "prospects_2026_consensus.csv"
STATS_JSON = RAW_DIR / "college_stats_api_2026.json"
PROSPECTS_CSV = PROCESSED_DIR / "prospects_2026.csv"

SEASON_YEAR = 2025


def scrape_bigboard() -> pd.DataFrame:
    opts = uc.ChromeOptions()
    opts.add_argument("--disable-gpu")
    opts.add_argument("--window-size=1280,900")
    driver = uc.Chrome(options=opts)
    try:
        driver.get(BIGBOARD_URL)
        time.sleep(10)
        if "Just a moment" in driver.title:
            time.sleep(10)
        html = driver.page_source
    finally:
        try:
            driver.quit()
        except OSError:
            pass

    soup = BeautifulSoup(html, "lxml")
    ul = soup.find("ul")
    if ul is None:
        raise RuntimeError("No <ul> on big board page — page structure changed")

    rows = []
    for idx, li in enumerate(ul.find_all("li", recursive=False), start=1):
        name_link = li.find("a", href=lambda h: h and "/players/2026/" in h)
        if not name_link:
            continue
        name = name_link.get_text(strip=True)
        if not name:
            continue

        # Rank: the list is already ordered by consensus rank on the page,
        # so use iteration index. (The rank number is also rendered inside
        # each <li>, but inside multiple responsive variants + stat blocks,
        # which made a text-based extraction unreliable.)
        rank = idx

        # Position: leaf <div> whose own text is the position code.
        # Restrict to leaves (no nested <div>/<a>) so we don't concatenate with
        # an adjacent all-caps school abbreviation like LSU/USC/TCU.
        position = None
        name_block = name_link.parent
        if name_block is not None:
            for d in name_block.find_all("div"):
                if d.find(["div", "a"]) is not None:
                    continue
                t = d.get_text(strip=True)
                if 1 <= len(t) <= 5 and t.isupper():
                    position = t
                    break

        # School: aria-label on a non-player anchor
        school = None
        for a in li.find_all("a"):
            aria = (a.get("aria-label") or "").strip()
            if aria and aria != name:
                school = aria
                break

        rows.append({
            "rank": rank,
            "player": name,
            "position": position,
            "school": school,
        })

    # Preserve the page's rank order; dropping dupes with keep="first"
    # keeps the higher-ranked occurrence if a name appears twice.
    df = pd.DataFrame(rows).dropna(subset=["player"])
    df = df.drop_duplicates(subset=["player"], keep="first").reset_index(drop=True)
    return df


def main():
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    # 1. Big board
    if BIGBOARD_CSV.exists():
        prospects = pd.read_csv(BIGBOARD_CSV)
        print(f"Loaded cached big board: {len(prospects)} prospects -> {BIGBOARD_CSV}")
    else:
        print("Scraping NFL Mock Draft Database consensus big board...")
        prospects = scrape_bigboard()
        prospects.to_csv(BIGBOARD_CSV, index=False)
        print(f"Scraped {len(prospects)} prospects -> {BIGBOARD_CSV}")

    # 2. CFBD 2025 season stats
    if STATS_JSON.exists():
        records = json.loads(STATS_JSON.read_text(encoding="utf-8"))
        print(f"Loaded cached CFBD {SEASON_YEAR} stats: {len(records)} records")
    else:
        api_key = load_api_key()
        print(f"Fetching CFBD {SEASON_YEAR} season (5 categories)...")
        records = fetch_season(api_key, SEASON_YEAR)
        STATS_JSON.write_text(json.dumps(records), encoding="utf-8")
        print(f"Fetched {len(records)} records -> {STATS_JSON}")

    # 3. Fuzzy match (threshold 85, same as fetch_college_stats_api.py)
    wide = pivot_wide(records)
    team_index = index_by_team(wide)

    matched_rows = []
    for _, row in prospects.iterrows():
        stats, score, mname, mteam = match_player(
            row["player"],
            str(row["school"]) if pd.notna(row.get("school")) else "",
            team_index,
        )
        if stats is None:
            continue
        flat = {k: v for k, v in stats.items()
                if k not in ("player", "team", "conference")}
        flat["_match_score"] = score
        flat["_matched_name"] = mname
        flat["_matched_team"] = mteam
        flat["player"] = row["player"]
        matched_rows.append(flat)

    matches_df = pd.DataFrame(matched_rows)
    if not matches_df.empty:
        id_cols = ["player", "_match_score", "_matched_name", "_matched_team"]
        other = sorted([c for c in matches_df.columns if c not in id_cols])
        matches_df = matches_df[id_cols + other]

    merged = prospects.merge(matches_df, how="left", on="player")
    merged["position_group"] = merged["position"].apply(position_group)
    merged.to_csv(PROSPECTS_CSV, index=False)
    print(f"\nSaved -> {PROSPECTS_CSV}")

    print_summary(merged, matches_df)


def print_summary(merged: pd.DataFrame, matches_df: pd.DataFrame):
    total = len(merged)
    matched = int(merged["_match_score"].notna().sum()) if "_match_score" in merged else 0

    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Prospects: {total}")
    print(f"Matched to 2025 college stats: {matched}/{total} "
          f"({matched / total * 100:.1f}%)" if total else "")

    print("\nMatch rate by position group:")
    grp_all = merged.groupby("position_group").size()
    grp_matched = merged[merged["_match_score"].notna()].groupby("position_group").size()
    for g in ("QB", "SKILL", "OL", "DEF"):
        t = int(grp_all.get(g, 0))
        m = int(grp_matched.get(g, 0))
        r = m / t * 100 if t else 0.0
        print(f"  {g:<6} {m:>4}/{t:<4} ({r:.1f}%)")

    non_stat = {"rank", "player", "position", "school", "position_group",
                "_match_score", "_matched_name", "_matched_team"}
    stat_cols = [c for c in merged.columns if c not in non_stat]
    if stat_cols:
        print("\n% missing per stat column (descending):")
        miss = (merged[stat_cols].isna().mean() * 100).sort_values(ascending=False)
        for c, p in miss.items():
            print(f"  {p:5.1f}%  {c}")


if __name__ == "__main__":
    main()
