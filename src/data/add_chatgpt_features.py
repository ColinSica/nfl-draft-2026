"""
Add ChatGPT-flagged / late-round-intel features onto the already-enriched
2026 tables and probe the Odds API for what's available.

Modifies in place:
  data/processed/prospects_2026_enriched.csv
  data/processed/team_context_2026_enriched.csv
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd
import requests
from rapidfuzz import fuzz, process

ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = ROOT / "data" / "raw"
PROC_DIR = ROOT / "data" / "processed"

PROS_CSV = PROC_DIR / "prospects_2026_enriched.csv"
TEAM_CSV = PROC_DIR / "team_context_2026_enriched.csv"

STATS_2025_JSON = RAW_DIR / "college_stats_api_2026.json"   # contains 2025 season
STATS_2024_JSON = RAW_DIR / "college_stats_api_2025.json"   # contains 2024 season
TEAM_STATS_JSON = RAW_DIR / "cfbd_team_season_stats.json"

# Reuse pivot + index helpers from the existing CFBD script
sys.path.insert(0, str(Path(__file__).resolve().parent))
from fetch_college_stats_api import pivot_wide, index_by_team  # noqa: E402

# ---- 2d: hardcoded intel team-link scores (user-provided) -------------------
INTEL_TEAM_LINK = {
    "Fernando Mendoza":   {"LV": 3},
    "Arvell Reese":       {"NYJ": 3, "ARI": 2},
    "David Bailey":       {"NYJ": 2, "ARI": 3},
    "Jeremiyah Love":     {"TEN": 3, "NYG": 2, "ARI": 2, "CIN": 1},
    "Caleb Downs":        {"DAL": 3, "NYG": 2},
    "Monroe Freeling":    {"CLE": 3},
    "Omar Cooper":        {"WAS": 2},
    "Rueben Bain":        {"CIN": 2, "KC": 1, "TEN": 1, "MIA": 1},
    "Garrett Nussmeier":  {"NO": 2},
    "Carnell Tate":       {"WAS": 2, "PHI": 2},
}


# =====================================================================
# Helpers
# =====================================================================

def build_season_lookup(path: Path) -> dict[str, list[dict]]:
    """Return team_name -> list of wide-format stat dicts for that team."""
    if not path.exists():
        return {}
    records = json.loads(path.read_text(encoding="utf-8"))
    wide = pivot_wide(records)
    return index_by_team(wide)


def lookup_player_stats(player: str, college: str,
                        team_index: dict[str, list[dict]]) -> Optional[dict]:
    if not team_index or not isinstance(player, str):
        return None
    # fuzzy-match school name to indexed team
    teams = list(team_index.keys())
    if not teams:
        return None
    best_team = process.extractOne(str(college), teams, scorer=fuzz.token_set_ratio)
    if best_team is None or best_team[1] < 80:
        return None
    pool = team_index[best_team[0]]
    names = [p["player"] for p in pool]
    best_name = process.extractOne(player, names, scorer=fuzz.WRatio)
    if best_name is None or best_name[1] < 85:
        return None
    return pool[best_name[2]]


# =====================================================================
# 2a. pff_minus_consensus (all null — pff_rank absent)
# =====================================================================

def add_pff_minus_consensus(pros: pd.DataFrame) -> None:
    pros["pff_minus_consensus"] = np.nan
    pros["pff_grade_3yr"] = np.nan
    pros["pff_waa"] = np.nan


# =====================================================================
# 2b. trajectory_up_down
# =====================================================================

def add_trajectory(pros: pd.DataFrame) -> None:
    idx_2025 = build_season_lookup(STATS_2025_JSON)
    idx_2024 = build_season_lookup(STATS_2024_JSON)

    def stat_for(row: pd.Series, team_idx) -> float:
        grp = row.get("position_group")
        rec = lookup_player_stats(row.get("player"), row.get("college"), team_idx)
        if rec is None:
            return np.nan
        if grp == "QB":
            return float(rec.get("pass_yds") or 0.0)
        if grp == "SKILL":
            return float(rec.get("rec_yds") or 0.0) + float(rec.get("rush_yds") or 0.0)
        return np.nan

    results = []
    for _, row in pros.iterrows():
        grp = row.get("position_group")
        if grp not in ("QB", "SKILL"):
            results.append(np.nan)
            continue
        final = stat_for(row, idx_2025)
        prior = stat_for(row, idx_2024)
        if pd.isna(final) or pd.isna(prior) or prior <= 0:
            results.append(np.nan)
            continue
        ratio = final / prior
        if ratio > 1.1:
            results.append(1)
        elif ratio < 0.9:
            results.append(-1)
        else:
            results.append(0)
    pros["trajectory_up_down"] = results


# =====================================================================
# 2c. future_firsts_owned (team-level, added to team_context)
# =====================================================================

def add_future_firsts_owned(team: pd.DataFrame,
                            team_context_raw: pd.DataFrame) -> None:
    counts = (team_context_raw[team_context_raw["round"].isin([1, 2])]
              .groupby("team").size().rename("future_firsts_owned"))
    team["future_firsts_owned"] = team["team"].map(counts).fillna(0).astype(int)


# =====================================================================
# 2d. intel team-link
# =====================================================================

def add_intel_link(pros: pd.DataFrame) -> None:
    keys = list(INTEL_TEAM_LINK.keys())

    def lookup(name: str) -> tuple[int, str]:
        if not isinstance(name, str):
            return (0, "")
        best = process.extractOne(name, keys, scorer=fuzz.WRatio)
        if best is None or best[1] < 88:
            return (0, "")
        links = INTEL_TEAM_LINK[best[0]]
        if not links:
            return (0, "")
        top_team = max(links.items(), key=lambda kv: kv[1])
        return (top_team[1], top_team[0])

    out = pros["player"].apply(lookup)
    pros["intel_link_max"] = out.apply(lambda t: t[0])
    pros["intel_top_team"] = out.apply(lambda t: t[1])


# =====================================================================
# 2e. pick_range_trade_rate (team-level per pick)
# =====================================================================

def add_pick_range_trade_rate(team: pd.DataFrame) -> None:
    def rate(pick):
        if 1 <= pick <= 10:
            return 0.15
        if 11 <= pick <= 22:
            return 0.30
        if 23 <= pick <= 32:
            return 0.46
        return 0.25
    team["pick_range_trade_rate"] = team["pick_number"].apply(rate)


# =====================================================================
# 2f. Odds API probe
# =====================================================================

def probe_odds_api() -> None:
    key = "2c802efbe7aa90c8ace1351beb17e085"
    url = "https://api.the-odds-api.com/v4/sports/americanfootball_nfl/odds"
    for markets in ("h2h", "player_props"):
        try:
            r = requests.get(url, params={
                "apiKey": key, "regions": "us",
                "markets": markets, "oddsFormat": "american",
            }, timeout=20)
            print(f"\n[odds api] markets={markets}  status={r.status_code}")
            print("  body[:500]:", r.text[:500].replace("\n", " "))
        except Exception as e:
            print(f"[odds api] {markets} error: {e}")

    # Also list available sports (cheap call)
    try:
        r = requests.get("https://api.the-odds-api.com/v4/sports",
                         params={"apiKey": key}, timeout=20)
        if r.ok:
            sports = r.json()
            draft = [s for s in sports if "draft" in str(s.get("title", "")).lower()
                     or "draft" in str(s.get("key", "")).lower()]
            print(f"\n[odds api] draft-related sports entries: {len(draft)}")
            for s in draft[:5]:
                print(f"  {s}")
    except Exception as e:
        print(f"[odds api] sports-list error: {e}")


# =====================================================================
# Bottom-of-message additions
# =====================================================================

def add_breakout_age(pros: pd.DataFrame) -> None:
    """SKILL only. breakout_age = age when dominator_rating first crossed 30.

    We only have 2024 + 2025 season data, so this is coarse:
      - 2024 dominator > 30  -> breakout at (age_at_draft - 1)
      - else 2025 dominator > 30 -> breakout at age_at_draft
      - else null
    """
    # Build a per-team total-yards lookup for 2024
    team_yards_2024: dict[str, float] = {}
    if TEAM_STATS_JSON.exists():
        data = json.loads(TEAM_STATS_JSON.read_text(encoding="utf-8"))
        year = data.get("2024") or data.get(2024) or []
        for rec in year:
            if rec.get("statName") == "totalYards":
                team_yards_2024[rec.get("team", "")] = float(rec.get("statValue") or 0)

    idx_2024 = build_season_lookup(STATS_2024_JSON)

    def dominator_2024(row: pd.Series) -> float:
        rec = lookup_player_stats(row.get("player"), row.get("college"), idx_2024)
        if rec is None:
            return np.nan
        team = rec.get("team", "")
        total = team_yards_2024.get(team)
        if not total or total <= 0:
            # try fuzzy
            names = list(team_yards_2024.keys())
            if names:
                best = process.extractOne(team, names, scorer=fuzz.token_set_ratio)
                if best and best[1] >= 85:
                    total = team_yards_2024[best[0]]
        if not total or total <= 0:
            return np.nan
        num = float(rec.get("rec_yds") or 0) + float(rec.get("rush_yds") or 0)
        return num / total * 100

    out = []
    for _, row in pros.iterrows():
        if row.get("position_group") != "SKILL":
            out.append(np.nan)
            continue
        age = row.get("age")
        if pd.isna(age):
            out.append(np.nan)
            continue
        d24 = dominator_2024(row)
        d25 = row.get("dominator_rating")
        if pd.notna(d24) and d24 > 30:
            out.append(float(age) - 1)
        elif pd.notna(d25) and d25 > 30:
            out.append(float(age))
        else:
            out.append(np.nan)
    pros["breakout_age"] = out


def add_first_round_mock_rate(pros: pd.DataFrame) -> None:
    vc = pros.get("visit_count", pd.Series([0] * len(pros))).fillna(0)
    pros["first_round_mock_rate"] = np.where(vc >= 3, 1.0,
                                             np.where(vc >= 1, 0.5, 0.0))


def add_gm_small_sample_flag(team: pd.DataFrame) -> None:
    if "gm_data_reliable" in team.columns:
        team["gm_small_sample_flag"] = (team["gm_data_reliable"] == 0).astype(int)
    else:
        team["gm_small_sample_flag"] = 0


def add_drill_missing_flags(pros: pd.DataFrame) -> None:
    invited = (pros.get("combine_invite", 0) == 1)
    for drill in ("40_yard", "vertical", "broad_jump"):
        flag_name = f"drill_missing_{drill.replace('_yard', '').replace('broad_jump', 'broad')}"
        # Normalise the three names the user asked for
    # Explicit mapping per user spec
    for src, name in (("40_yard", "drill_missing_40"),
                      ("vertical", "drill_missing_vertical"),
                      ("broad_jump", "drill_missing_broad")):
        if src in pros.columns:
            pros[name] = (invited & pros[src].isna()).astype(int)
        else:
            pros[name] = 0


# =====================================================================
# Main
# =====================================================================

def main():
    pros = pd.read_csv(PROS_CSV)
    team = pd.read_csv(TEAM_CSV)
    team_context_raw = pd.read_csv(PROC_DIR / "team_context_2026.csv")

    before_pros_cols = pros.shape[1]
    before_team_cols = team.shape[1]

    # Drop deprecated columns from prior runs (breakout_age: 1/404 coverage = noise)
    for deprecated in ("breakout_age",):
        if deprecated in pros.columns:
            pros = pros.drop(columns=[deprecated])

    print("== Prospects-level additions ==")
    add_pff_minus_consensus(pros)
    add_trajectory(pros)
    add_intel_link(pros)
    add_first_round_mock_rate(pros)
    add_drill_missing_flags(pros)

    print("== Team-level additions ==")
    add_future_firsts_owned(team, team_context_raw)
    add_pick_range_trade_rate(team)
    add_gm_small_sample_flag(team)

    print("\n== Odds API probe ==")
    probe_odds_api()

    pros.to_csv(PROS_CSV, index=False)
    team.to_csv(TEAM_CSV, index=False)

    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"prospects_2026_enriched.csv: {before_pros_cols} -> {pros.shape[1]} cols "
          f"(+{pros.shape[1] - before_pros_cols})")
    print(f"team_context_2026_enriched.csv: {before_team_cols} -> {team.shape[1]} cols "
          f"(+{team.shape[1] - before_team_cols})")

    # New-column coverage
    new_pros_cols = [
        "pff_minus_consensus", "pff_grade_3yr", "pff_waa",
        "trajectory_up_down", "intel_link_max", "intel_top_team",
        "first_round_mock_rate",
        "drill_missing_40", "drill_missing_vertical", "drill_missing_broad",
    ]
    new_team_cols = ["future_firsts_owned", "pick_range_trade_rate",
                     "gm_small_sample_flag"]

    print("\nProspect new-column coverage:")
    for c in new_pros_cols:
        if c in pros.columns:
            notnull = pros[c].notna().sum()
            nonzero = ((pros[c] != 0) & pros[c].notna()).sum() if pd.api.types.is_numeric_dtype(pros[c]) else notnull
            print(f"  {c:<28} non-null={notnull:>4}  non-zero={nonzero:>4}")

    print("\nTeam new-column coverage:")
    for c in new_team_cols:
        if c in team.columns:
            print(f"  {c:<28} non-null={team[c].notna().sum():>3}")


if __name__ == "__main__":
    main()
