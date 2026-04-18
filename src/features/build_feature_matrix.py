"""
Build per-position-group feature matrices for training.

Splits data/processed/draft_with_college.csv (historical, 3838 rows) into
four groups and writes (X, y, meta) triples under data/features/.

Position groups (per user spec — note SKILL excludes FB, OL includes LS):
  QB    : position == 'QB'
  SKILL : position in {WR, RB, TE}
  OL    : position in {T, G, C, OT, OG, LS}
  DEF   : everything else (incl. FB, K, P, and all defensive positions)

Feature construction per group:
  Universal (keep if column exists):
    age, height, weight, 40_yard, vertical, bench_press, broad_jump,
    three_cone, shuttle, combine_invite, has_college_stats, age_estimated,
    conference_tier

  Stat columns (per group, drop any column with >60% missing in that group):
    QB    : passing + rushing
    SKILL : rushing + receiving
    OL    : (none — measurements + combine only)
    DEF   : defensive

Outputs
-------
  data/features/X_{group}_historical.csv       features only
  data/features/y_{group}_historical.csv       target (pick number)
  data/features/meta_{group}_historical.csv    player, year, team, career_av
"""

import json
import os
import sys
from pathlib import Path

import pandas as pd
import requests
from rapidfuzz import fuzz, process

ROOT = Path(__file__).resolve().parents[2]
HIST_CSV = ROOT / "data" / "processed" / "draft_with_college.csv"
FEATURES_DIR = ROOT / "data" / "features"
TEAMS_JSON = ROOT / "data" / "raw" / "cfbd_teams.json"

API_BASE = "https://api.collegefootballdata.com"

POWER5 = {"ACC", "Big Ten", "Big 12", "Pac-12", "SEC"}
G5 = {"American Athletic", "Mountain West", "Conference USA",
      "Mid-American", "Sun Belt"}

UNIVERSAL_FEATURES = [
    # Core physical + combine
    "age", "height", "weight", "40_yard", "vertical", "bench_press",
    "broad_jump", "three_cone", "shuttle",
    "combine_invite", "has_college_stats", "age_estimated",
    "conference_tier",
    # Part A enrichment (always populated for 2020-2025 + 2026 prospects)
    "ras_score", "ras_drills_used", "ras_reliable",
    "speed_score",
    "college_sp_plus", "college_sp_offense", "college_sp_defense", "college_sos",
    "position_rank", "positions_ahead", "draft_class_position_depth",
    "years_in_college", "is_underclassman", "experience_score",
    "height_z", "weight_z", "size_score",
    # Positional value (hardcoded prior + historical round distribution)
    "positional_value_prior", "positional_value_adjusted",
    "position_historical_round_avg", "position_historical_round_std",
]

STAT_COLUMNS = {
    "passing":   ["pass_att", "pass_cmp", "pass_cmp_pct", "pass_int",
                  "pass_td", "pass_yds", "pass_ypa"],
    "rushing":   ["rush_att", "rush_long", "rush_td", "rush_yds", "rush_ypc"],
    "receiving": ["rec", "rec_long", "rec_td", "rec_yds", "rec_ypr"],
    "defensive": ["def_int", "def_int_avg", "def_int_td", "def_int_yds",
                  "def_pd", "def_qb_hur", "def_sacks", "def_solo",
                  "def_tfl", "def_tot", "defensive_td"],
}

GROUP_STATS = {
    "QB":    ["passing", "rushing"],
    "SKILL": ["rushing", "receiving"],
    "OL":    [],
    "DEF":   ["defensive"],
}

# Group-specific engineered features added by enrich_all_features.py
GROUP_SPECIFIC = {
    "QB":    ["td_int_ratio", "yards_per_attempt", "completion_pct",
              "dual_threat_score", "college_starts_sweet_spot"],
    "SKILL": ["dominator_rating", "team_total_yards"],
    "OL":    [],
    "DEF":   [],
}

MISSINGNESS_FLAG_THRESHOLD = 0.50

# User-mandated drops (too much missing to be worth imputing)
DROP_GLOBAL = {
    "three_cone", "shuttle", "bench_press",
    # Leaky (ordinal ranks derived from pick in historical)
    "position_rank", "positions_ahead", "draft_class_position_depth",
    # Leaky (games_played = NFL career games on PFR, not college). Null for
    # prospects, so train-time vs inference-time semantics diverge entirely.
    "games_played", "experience_score",
}
DROP_BY_GROUP = {
    # college_starts_sweet_spot and dual_threat_score divide by games_played
    "QB": {"40_yard", "speed_score", "broad_jump", "vertical", "ras_score",
           "dual_threat_score", "college_starts_sweet_spot"},
}

POSITION_MASKS = {
    "QB":    {"QB"},
    "SKILL": {"WR", "RB", "TE"},
    "OL":    {"T", "G", "C", "OT", "OG", "LS"},
}
KNOWN_POSITIONS = set().union(*POSITION_MASKS.values())

STAT_DROP_THRESHOLD = 0.60


def load_api_key() -> str:
    key = os.environ.get("CFBD_API_KEY")
    if key:
        return key.strip()
    env = ROOT / ".env"
    if env.exists():
        for line in env.read_text(encoding="utf-8").splitlines():
            if line.startswith("CFBD_API_KEY="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    raise SystemExit("CFBD_API_KEY not set")


def load_teams_map() -> dict[str, str | None]:
    """Return {school_name: conference_string}. Cached to data/raw/cfbd_teams.json."""
    if TEAMS_JSON.exists():
        return json.loads(TEAMS_JSON.read_text(encoding="utf-8"))
    hdr = {"Authorization": f"Bearer {load_api_key()}", "Accept": "application/json"}
    teams: dict[str, str | None] = {}
    for cls in ("fbs", "fcs"):
        r = requests.get(f"{API_BASE}/teams", headers=hdr,
                         params={"classification": cls}, timeout=30)
        if r.ok:
            for t in r.json():
                s = t.get("school")
                if s:
                    teams[s] = t.get("conference")
    TEAMS_JSON.write_text(json.dumps(teams), encoding="utf-8")
    return teams


def make_tier_fn(teams_map: dict[str, str | None]):
    names = list(teams_map.keys())
    cache: dict[str, int] = {}

    def tier(college) -> int:
        if not isinstance(college, str) or not college.strip():
            return 1
        if college in cache:
            return cache[college]
        conf = teams_map.get(college)
        if conf is None:
            best = process.extractOne(college, names, scorer=fuzz.WRatio)
            if best and best[1] >= 85:
                conf = teams_map.get(best[0])
        if conf in POWER5:
            out = 3
        elif conf in G5:
            out = 2
        else:
            out = 1
        cache[college] = out
        return out

    return tier


def position_mask(positions: pd.Series, group: str) -> pd.Series:
    if group == "DEF":
        return ~positions.isin(KNOWN_POSITIONS)
    return positions.isin(POSITION_MASKS[group])


def build_group(df: pd.DataFrame, group: str):
    sub = df[position_mask(df["position"], group)].copy().reset_index(drop=True)

    feat_cols = [c for c in UNIVERSAL_FEATURES if c in sub.columns]
    for c in GROUP_SPECIFIC.get(group, []):
        if c in sub.columns:
            feat_cols.append(c)
    for sg in GROUP_STATS[group]:
        for c in STAT_COLUMNS[sg]:
            if c not in sub.columns:
                continue
            if sub[c].isna().mean() <= STAT_DROP_THRESHOLD:
                feat_cols.append(c)

    # Apply mandated drops (global + per-group)
    banned = DROP_GLOBAL | DROP_BY_GROUP.get(group, set())
    feat_cols = [c for c in feat_cols if c not in banned]

    X = sub[feat_cols].copy()
    y = sub["pick"].rename("pick")
    meta_cols = [c for c in ("player", "year", "team", "career_av") if c in sub.columns]
    meta = sub[meta_cols].copy()
    return X, y, meta, feat_cols


def main():
    FEATURES_DIR.mkdir(parents=True, exist_ok=True)
    df = pd.read_csv(HIST_CSV)
    print(f"Loaded {len(df)} rows from {HIST_CSV.name}")

    if "age_estimated" not in df.columns:
        df["age_estimated"] = 0

    teams_map = load_teams_map()
    print(f"Loaded {len(teams_map)} CFBD teams for conference mapping")

    tier_fn = make_tier_fn(teams_map)
    df["conference_tier"] = df["college"].apply(tier_fn)

    # Sanity: distribution of conference_tier
    tier_counts = df["conference_tier"].value_counts().sort_index()
    tier_names = {1: "FCS/unknown", 2: "G5", 3: "P5"}
    print("Conference tier distribution: " +
          ", ".join(f"{tier_names[t]}={n}" for t, n in tier_counts.items()))

    for group in ("QB", "SKILL", "OL", "DEF"):
        X, y, meta, features = build_group(df, group)
        X.to_csv(FEATURES_DIR / f"X_{group}_historical.csv", index=False)
        y.to_csv(FEATURES_DIR / f"y_{group}_historical.csv",
                 index=False, header=True)
        meta.to_csv(FEATURES_DIR / f"meta_{group}_historical.csv", index=False)

        print("\n" + "=" * 60)
        print(f"{group}")
        print("=" * 60)
        print(f"Rows: {len(X)}    Features: {len(features)}")
        print(f"Feature list: {features}")
        miss = (X.isna().mean() * 100).sort_values(ascending=False)
        high_missing = [(f, pct) for f, pct in miss.items()
                        if pct > MISSINGNESS_FLAG_THRESHOLD * 100]
        print("% missing per feature (descending):")
        for f, pct in miss.items():
            flag = "  <- DROP?" if pct > MISSINGNESS_FLAG_THRESHOLD * 100 else ""
            print(f"  {pct:5.1f}%  {f}{flag}")
        if high_missing:
            print(f"\n  Features with >50% missing (consider dropping): "
                  f"{[f for f, _ in high_missing]}")


if __name__ == "__main__":
    main()
