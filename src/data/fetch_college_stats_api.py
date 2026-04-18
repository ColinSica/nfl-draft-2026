"""
Fetch college football season stats from the College Football Data API
and merge them into the combine-enriched draft dataset.

Strategy
--------
The API supports bulk queries per (year, category). We pull 5 categories
(passing, rushing, receiving, defensive, interceptions) for each college
season corresponding to draft years 2011-2025 — 15 * 5 = 75 API calls total,
instead of one-lookup-per-player.

Then fuzzy-match each drafted player against the CFBD roster for their
school + final college season (draft_year - 1).

Requires a free CFBD API key. Put it in one of:
  - env var   CFBD_API_KEY=...
  - file      .env at repo root with  CFBD_API_KEY=...
Register at https://collegefootballdata.com/key

Outputs
-------
  data/raw/college_stats_api_{draft_year}.json   (per-year bundled API dump)
  data/raw/college_stats_fuzzy_review.csv        (matches 85-94, for human QC)
  data/processed/draft_with_college.csv          (final merged dataset)
"""

import json
import os
import time
from collections import defaultdict
from pathlib import Path

import pandas as pd
import requests
from rapidfuzz import fuzz, process

ROOT = Path(__file__).resolve().parents[2]
INPUT_CSV = ROOT / "data" / "processed" / "draft_with_combine.csv"
RAW_DIR = ROOT / "data" / "raw"
MERGED_CSV = ROOT / "data" / "processed" / "draft_with_college.csv"
REVIEW_CSV = RAW_DIR / "college_stats_fuzzy_review.csv"

API_BASE = "https://api.collegefootballdata.com"
CATEGORIES = ["passing", "rushing", "receiving", "defensive", "interceptions"]
DRAFT_YEARS = range(2011, 2026)

FUZZ_THRESHOLD = 85   # accept if player-name score >= this
REVIEW_THRESHOLD = 95  # below this, flag for review
TEAM_THRESHOLD = 80   # only consider CFBD players whose team fuzzy-matches draft school
REQUEST_DELAY_SEC = 1.0

# Map raw CFBD stat types -> our clean column names.
# Keys are "{category}__{statType}" lowercased, with spaces -> underscores.
STAT_NAME_MAP = {
    "passing__att":         "pass_att",
    "passing__completions": "pass_cmp",
    "passing__cmp":         "pass_cmp",
    "passing__yds":         "pass_yds",
    "passing__td":          "pass_td",
    "passing__int":         "pass_int",
    "passing__pct":         "pass_cmp_pct",
    "passing__ypa":         "pass_ypa",

    "rushing__car":  "rush_att",
    "rushing__att":  "rush_att",
    "rushing__yds":  "rush_yds",
    "rushing__td":   "rush_td",
    "rushing__ypc":  "rush_ypc",
    "rushing__long": "rush_long",

    "receiving__rec":  "rec",
    "receiving__yds":  "rec_yds",
    "receiving__td":   "rec_td",
    "receiving__ypr":  "rec_ypr",
    "receiving__long": "rec_long",

    "defensive__solo":   "def_solo",
    "defensive__tot":    "def_tot",
    "defensive__tfl":    "def_tfl",
    "defensive__sacks":  "def_sacks",
    "defensive__pd":     "def_pd",
    "defensive__qb_hur": "def_qb_hur",

    "interceptions__int": "def_int",
    "interceptions__yds": "def_int_yds",
    "interceptions__td":  "def_int_td",
    "interceptions__avg": "def_int_avg",
}

QB_POS = {"QB"}
SKILL_POS = {"RB", "WR", "TE", "FB", "HB"}
OL_POS = {"C", "G", "OG", "OT", "T", "OL"}


def position_group(pos: str | None) -> str:
    p = (pos or "").upper()
    if p in QB_POS:
        return "QB"
    if p in SKILL_POS:
        return "SKILL"
    if p in OL_POS:
        return "OL"
    return "DEF"


def load_api_key() -> str:
    key = os.environ.get("CFBD_API_KEY")
    if key:
        return key.strip()
    env_path = ROOT / ".env"
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line.startswith("CFBD_API_KEY="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    raise SystemExit(
        "CFBD_API_KEY not found.\n"
        "Register for a free key at https://collegefootballdata.com/key\n"
        "then set it via either:\n"
        "  setx CFBD_API_KEY your_key_here   (then restart shell)\n"
        "  echo CFBD_API_KEY=your_key_here > .env"
    )


def fetch_season(api_key: str, season_year: int) -> list[dict]:
    """Pull all 5 categories for one season. Returns combined list of long-format records."""
    headers = {"Authorization": f"Bearer {api_key}", "Accept": "application/json"}
    records: list[dict] = []
    for cat in CATEGORIES:
        params = {"year": season_year, "seasonType": "regular", "category": cat}
        r = requests.get(f"{API_BASE}/stats/player/season",
                         params=params, headers=headers, timeout=30)
        r.raise_for_status()
        data = r.json()
        # Tag each record with its category; CFBD includes it already but belt+suspenders
        for rec in data:
            rec.setdefault("category", cat)
        records.extend(data)
        time.sleep(REQUEST_DELAY_SEC)
    return records


def pivot_wide(records: list[dict]) -> list[dict]:
    """Collapse long-format (one row per stat) into wide-format (one row per player+team)."""
    wide: dict[tuple, dict] = defaultdict(dict)
    for rec in records:
        player = rec.get("player")
        team = rec.get("team")
        if not player or not team:
            continue
        key = (team, player)
        w = wide[key]
        w.setdefault("player", player)
        w.setdefault("team", team)
        w.setdefault("conference", rec.get("conference"))

        cat = (rec.get("category") or "").strip().lower()
        stype = (rec.get("statType") or "").strip().lower().replace(" ", "_")
        raw_key = f"{cat}__{stype}"
        col = STAT_NAME_MAP.get(raw_key, f"{cat}_{stype}")
        val = rec.get("stat")
        try:
            val = float(val)
        except (TypeError, ValueError):
            pass
        w[col] = val
    return list(wide.values())


def index_by_team(wide_records: list[dict]) -> dict[str, list[dict]]:
    out: dict[str, list[dict]] = defaultdict(list)
    for r in wide_records:
        out[r["team"]].append(r)
    return out


def find_candidate_teams(college: str, team_index: dict[str, list[dict]]) -> list[str]:
    if not college:
        return []
    c = college.lower()
    scored = [(team, fuzz.token_set_ratio(c, team.lower())) for team in team_index]
    return [team for team, s in scored if s >= TEAM_THRESHOLD]


def match_player(draft_player: str, draft_college: str,
                 team_index: dict[str, list[dict]]) -> tuple[dict | None, float, str, str]:
    """Return (stats_dict, score, matched_name, matched_team) or (None, 0, '', '')."""
    teams = find_candidate_teams(draft_college, team_index)
    if not teams:
        return None, 0.0, "", ""

    pool: list[dict] = []
    for t in teams:
        pool.extend(team_index[t])
    if not pool:
        return None, 0.0, "", ""

    names = [r["player"] for r in pool]
    best = process.extractOne(draft_player, names, scorer=fuzz.WRatio)
    if best is None:
        return None, 0.0, "", ""
    matched_name, score, idx = best
    if score < FUZZ_THRESHOLD:
        return None, score, matched_name, pool[idx]["team"]
    return pool[idx], float(score), matched_name, pool[idx]["team"]


def run():
    api_key = load_api_key()
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    MERGED_CSV.parent.mkdir(parents=True, exist_ok=True)

    drafts = pd.read_csv(INPUT_CSV)
    drafts = drafts.dropna(subset=["player", "year"]).copy()
    drafts["year"] = drafts["year"].astype(int)
    drafts["position_group"] = drafts["position"].apply(position_group)

    print(f"Loaded {len(drafts)} draft picks from {INPUT_CSV.name}")
    print(f"Fetching CFBD seasons {DRAFT_YEARS.start - 1} - {DRAFT_YEARS.stop - 2}...\n")

    api_calls = 0
    api_failures: list[tuple[int, str, str]] = []
    team_index_by_draft_year: dict[int, dict[str, list[dict]]] = {}

    for draft_year in DRAFT_YEARS:
        season_year = draft_year - 1
        per_year_path = RAW_DIR / f"college_stats_api_{draft_year}.json"

        # Reuse cached raw dump if present
        if per_year_path.exists():
            records = json.loads(per_year_path.read_text(encoding="utf-8"))
            print(f"  {draft_year} (season {season_year}): loaded cache "
                  f"({len(records)} records)")
        else:
            try:
                records = fetch_season(api_key, season_year)
                api_calls += len(CATEGORIES)
                per_year_path.write_text(json.dumps(records), encoding="utf-8")
                print(f"  {draft_year} (season {season_year}): fetched "
                      f"{len(records)} records")
            except requests.HTTPError as e:
                api_failures.append((draft_year, "http_error", str(e)[:120]))
                print(f"  {draft_year}: HTTP error {e}")
                continue
            except requests.RequestException as e:
                api_failures.append((draft_year, "request_error", str(e)[:120]))
                print(f"  {draft_year}: request error {e}")
                continue

        wide = pivot_wide(records)
        team_index_by_draft_year[draft_year] = index_by_team(wide)

    print(f"\nAPI calls made: {api_calls}  |  failures: {len(api_failures)}\n")

    # Match every draft pick
    stat_cols: set[str] = set()
    matched_rows: list[dict] = []
    review_rows: list[dict] = []
    for _, row in drafts.iterrows():
        team_index = team_index_by_draft_year.get(int(row["year"]))
        if team_index is None:
            continue
        stats, score, matched_name, matched_team = match_player(
            row["player"], str(row["college"]) if pd.notna(row["college"]) else "",
            team_index,
        )
        if stats is None:
            continue

        flat = {k: v for k, v in stats.items() if k not in ("player", "team", "conference")}
        flat["_match_score"] = score
        flat["_matched_name"] = matched_name
        flat["_matched_team"] = matched_team
        flat["player"] = row["player"]
        flat["year"] = int(row["year"])
        matched_rows.append(flat)
        stat_cols.update(k for k in flat.keys() if k not in ("player", "year"))

        if score < REVIEW_THRESHOLD:
            review_rows.append({
                "draft_player": row["player"],
                "draft_college": row["college"],
                "year": int(row["year"]),
                "matched_name": matched_name,
                "matched_team": matched_team,
                "score": score,
            })

    matches_df = pd.DataFrame(matched_rows)
    if not matches_df.empty:
        # Order columns predictably: identifiers first
        id_cols = ["player", "year", "_match_score", "_matched_name", "_matched_team"]
        other = sorted([c for c in matches_df.columns if c not in id_cols])
        matches_df = matches_df[id_cols + other]

    merged = drafts.merge(matches_df, how="left", on=["player", "year"])
    merged.to_csv(MERGED_CSV, index=False)
    print(f"Saved merged dataset -> {MERGED_CSV}")

    # Review log
    review_df = pd.DataFrame(review_rows)
    review_df.to_csv(REVIEW_CSV, index=False)
    print(f"Saved fuzzy review log -> {REVIEW_CSV} ({len(review_df)} rows)")

    print_summary(drafts, merged, matches_df, review_df, api_calls, api_failures)


def print_summary(drafts, merged, matches_df, review_df, api_calls, api_failures):
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)

    print(f"API calls made:     {api_calls}")
    if api_failures:
        print(f"API failures ({len(api_failures)}):")
        for yr, kind, msg in api_failures:
            print(f"  {yr}: {kind} — {msg}")
    else:
        print("API failures:       0")

    n_matched = len(matches_df)
    total = len(drafts)
    overall_rate = n_matched / total * 100 if total else 0.0
    print(f"\nPlayers matched:    {n_matched}/{total} ({overall_rate:.1f}%)")

    print("\nMatch rate by position group:")
    grp_all = drafts.groupby("position_group").size()
    merged_match = merged[merged["_match_score"].notna()]
    grp_matched = merged_match.groupby("position_group").size()
    for g in ("QB", "SKILL", "OL", "DEF"):
        t = int(grp_all.get(g, 0))
        m = int(grp_matched.get(g, 0))
        r = m / t * 100 if t else 0.0
        print(f"  {g:<6} {m:>4}/{t:<4} ({r:.1f}%)")

    # Missingness (among matched rows)
    stat_cols = [c for c in matches_df.columns
                 if c not in ("player", "year", "_match_score",
                              "_matched_name", "_matched_team")]
    if stat_cols and not merged_match.empty:
        print("\nColumns with >30% missing (among matched rows):")
        flagged = []
        for c in stat_cols:
            pct = merged_match[c].isna().mean() * 100
            if pct > 30:
                flagged.append((c, pct))
        for c, p in sorted(flagged, key=lambda x: -x[1]):
            print(f"  - {c}: {p:.1f}% missing")
        if not flagged:
            print("  (none)")

    print(f"\nFuzzy review log ({len(review_df)} matches below "
          f"score {REVIEW_THRESHOLD}):")
    if not review_df.empty:
        sample = review_df.sort_values("score").head(10)
        for _, r in sample.iterrows():
            print(f"  score={r['score']:.0f}  "
                  f"{r['draft_player']} ({r['draft_college']}) -> "
                  f"{r['matched_name']} ({r['matched_team']})")


if __name__ == "__main__":
    run()
