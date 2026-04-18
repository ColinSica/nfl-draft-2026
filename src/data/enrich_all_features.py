"""
enrich_all_features.py — one-shot pre-modeling feature enrichment.

Runs the 25-step pipeline described in the engineering request. Each step is
wrapped in a try/except; scrape-based steps that fail or return no parseable
data log a warning and continue with NaN columns.

Outputs (all absolute paths under data/processed/):
  draft_with_college.csv           (filtered to year>=2020, + Part A cols)
  prospects_2026_enriched.csv      (Parts A + B)
  team_context_2026_enriched.csv   (Part C)
  prospects_with_demand.csv        (Part D — join of above + team_needs)
"""

from __future__ import annotations

import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd
import requests
from bs4 import BeautifulSoup
from rapidfuzz import fuzz, process

ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = ROOT / "data" / "raw"
PROC_DIR = ROOT / "data" / "processed"

HIST_CSV = PROC_DIR / "draft_with_college.csv"
PROS_CSV = PROC_DIR / "prospects_2026.csv"
TEAM_CTX_CSV = PROC_DIR / "team_context_2026.csv"
TEAM_NEEDS_CSV = PROC_DIR / "team_needs_2026.csv"

PROS_ENRICHED_CSV = PROC_DIR / "prospects_2026_enriched.csv"
TEAM_ENRICHED_CSV = PROC_DIR / "team_context_2026_enriched.csv"
PROS_DEMAND_CSV = PROC_DIR / "prospects_with_demand.csv"

CFBD_BASE = "https://api.collegefootballdata.com"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/122.0 Safari/537.36")

FAILURES: list[tuple[str, str]] = []


def log_fail(step: str, detail: str) -> None:
    FAILURES.append((step, detail))
    print(f"  [FAIL] {step}: {detail}")


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


def cfbd_get(path: str, params: dict, api_key: str) -> Optional[list]:
    try:
        r = requests.get(
            f"{CFBD_BASE}{path}",
            headers={"Authorization": f"Bearer {api_key}",
                     "Accept": "application/json"},
            params=params, timeout=30,
        )
        if r.status_code == 200:
            return r.json()
    except requests.RequestException as e:
        print(f"  CFBD error {path} {params}: {e}")
    return None


def web_get(url: str, timeout: int = 30) -> Optional[str]:
    try:
        r = requests.get(url, headers={"User-Agent": UA},
                         timeout=timeout, allow_redirects=True)
        if r.status_code == 200 and len(r.text) > 200:
            return r.text
        print(f"  HTTP {r.status_code} for {url[:80]}")
    except requests.RequestException as e:
        print(f"  Network error {url[:80]}: {e}")
    return None


# =====================================================================
# PREREQUISITE: Filter historical to 2020+
# =====================================================================
def filter_historical() -> pd.DataFrame:
    df = pd.read_csv(HIST_CSV)
    before = len(df)
    df = df[df["year"] >= 2020].reset_index(drop=True)
    print(f"[prereq] historical rows: {before} -> {len(df)} (year>=2020)")
    return df


# =====================================================================
# PART A — BACKFILL BOTH FILES
# =====================================================================

DRILLS_HIGHER_BETTER = {"vertical", "broad_jump", "bench_press"}
DRILLS_LOWER_BETTER = {"40_yard", "three_cone", "shuttle"}
ALL_DRILLS = DRILLS_HIGHER_BETTER | DRILLS_LOWER_BETTER


def _group_stats(df: pd.DataFrame, cols: list[str]) -> dict[str, dict[str, tuple[float, float]]]:
    """Per position_group mean/std for each column."""
    stats: dict[str, dict[str, tuple[float, float]]] = {}
    for grp, sub in df.groupby("position_group"):
        stats[grp] = {}
        for c in cols:
            if c in sub.columns:
                vals = sub[c].dropna()
                if len(vals) >= 5:
                    stats[grp][c] = (vals.mean(), vals.std(ddof=0) or 1.0)
    return stats


def _z_for_row(row, stats, col, lower_is_better=False):
    grp = row.get("position_group")
    val = row.get(col)
    ref = stats.get(grp, {}).get(col)
    if pd.isna(val) or ref is None:
        return np.nan
    mu, sd = ref
    z = (val - mu) / sd
    if lower_is_better:
        z = -z
    return z


def step1_ras(hist: pd.DataFrame, pros: pd.DataFrame):
    """RAS approximation: mean of directional z-scores mapped to 0-10."""
    print("[1] RAS scores")
    ref_stats = _group_stats(hist, list(ALL_DRILLS))

    def apply(df: pd.DataFrame) -> None:
        zs = {}
        for d in ALL_DRILLS:
            lower = d in DRILLS_LOWER_BETTER
            zs[d] = df.apply(lambda r: _z_for_row(r, ref_stats, d, lower), axis=1)
        z_df = pd.DataFrame(zs)
        drill_used = z_df.notna().sum(axis=1)
        mean_z = z_df.mean(axis=1, skipna=True)
        # Map z∈[-2,2] -> [0,10] linearly, clamp
        ras = (mean_z * 2.5 + 5.0).clip(0, 10)
        df["ras_score"] = ras
        df["ras_drills_used"] = drill_used.astype(int)
        df["ras_reliable"] = (drill_used >= 3).astype(int)

    apply(hist); apply(pros)
    print(f"  historical ras present: {hist['ras_score'].notna().mean()*100:.1f}%  "
          f"prospects ras present: {pros['ras_score'].notna().mean()*100:.1f}%")


def step2_speed_score(hist: pd.DataFrame, pros: pd.DataFrame):
    """speed_score = weight * 200 / 40_yard^4."""
    print("[2] speed_score")
    for df in (hist, pros):
        w = df.get("weight")
        f = df.get("40_yard")
        if w is None or f is None:
            df["speed_score"] = np.nan
            continue
        df["speed_score"] = (w * 200) / (f ** 4)


def step3_sp_plus(hist: pd.DataFrame, pros: pd.DataFrame, api_key: str):
    """CFBD SP+ per (college, year). Historical uses draft_year-1, prospects use 2025."""
    print("[3] SP+ conference strength")
    cache = RAW_DIR / "cfbd_sp_plus.json"
    if cache.exists():
        sp_by_year = json.loads(cache.read_text(encoding="utf-8"))
        # Keys come back as strings after JSON; convert
        sp_by_year = {int(k): v for k, v in sp_by_year.items()}
        print(f"  loaded cached SP+ for years: {sorted(sp_by_year.keys())}")
    else:
        sp_by_year = {}
        for yr in list(range(2019, 2025)) + [2025]:
            data = cfbd_get("/ratings/sp", {"year": yr}, api_key)
            if data is None:
                log_fail("step3", f"SP+ {yr} failed")
                continue
            sp_by_year[yr] = data
            time.sleep(0.3)
        cache.write_text(json.dumps(sp_by_year), encoding="utf-8")

    def lookup(year: int, college: str):
        teams = sp_by_year.get(year, [])
        if not teams or not isinstance(college, str):
            return (np.nan, np.nan, np.nan, np.nan)
        names = [t.get("team", "") for t in teams]
        best = process.extractOne(college, names, scorer=fuzz.WRatio)
        if best is None or best[1] < 85:
            return (np.nan, np.nan, np.nan, np.nan)
        t = teams[best[2]]
        off = t.get("offense") or {}
        defn = t.get("defense") or {}
        off_rating = off.get("rating") if isinstance(off, dict) else np.nan
        def_rating = defn.get("rating") if isinstance(defn, dict) else np.nan
        return (t.get("rating"), off_rating, def_rating, t.get("sos"))

    # Historical
    out = hist.apply(lambda r: lookup(int(r["year"]) - 1, r.get("college")), axis=1)
    hist[["college_sp_plus", "college_sp_offense", "college_sp_defense", "college_sos"]] = \
        pd.DataFrame(out.tolist(), index=hist.index)

    # Prospects (2025 season)
    out = pros.apply(lambda r: lookup(2025, r.get("college")), axis=1)
    pros[["college_sp_plus", "college_sp_offense", "college_sp_defense", "college_sos"]] = \
        pd.DataFrame(out.tolist(), index=pros.index)

    print(f"  historical SP+ coverage: {hist['college_sp_plus'].notna().mean()*100:.1f}%  "
          f"prospects: {pros['college_sp_plus'].notna().mean()*100:.1f}%")


def step4_positional_scarcity(hist: pd.DataFrame, pros: pd.DataFrame):
    """position_rank within draft class or consensus board; positions_ahead; depth."""
    print("[4] positional scarcity")
    # Historical: rank by pick within (year, position_group)
    hist["position_rank"] = hist.groupby(["year", "position_group"])["pick"] \
        .rank(method="dense", ascending=True).astype("Int64")
    hist["positions_ahead"] = hist["position_rank"] - 1
    hist["draft_class_position_depth"] = hist.groupby(
        ["year", "position_group"])["pick"].transform("count")

    # Prospects: rank by consensus rank within position_group
    pros["position_rank"] = pros.groupby("position_group")["rank"] \
        .rank(method="dense", ascending=True).astype("Int64")
    pros["positions_ahead"] = pros["position_rank"] - 1
    pros["draft_class_position_depth"] = pros.groupby("position_group")["rank"] \
        .transform("count")


def step5_college_experience(hist: pd.DataFrame, pros: pd.DataFrame):
    """years_in_college estimated from age (age-17, clamped 1-5).

    For 2026 prospects we have CFBD class year when available; use that where
    age is missing.
    """
    print("[5] college experience")
    def years_from_age(a):
        if pd.isna(a):
            return np.nan
        return max(1, min(5, int(round(float(a) - 17))))

    hist["years_in_college"] = hist["age"].apply(years_from_age).astype("Int64")
    hist["is_underclassman"] = (hist["years_in_college"] <= 3).astype("Int64")

    # Prospects: start from age, fallback to cached CFBD class year if age missing
    pros["years_in_college"] = pros["age"].apply(years_from_age).astype("Int64")

    # Try to backfill from cached roster class year
    cache = RAW_DIR / "cfbd_rosters_2025.json"
    if cache.exists():
        payload = json.loads(cache.read_text(encoding="utf-8"))
        rosters = payload.get("rosters", payload)
        school_to_cfbd = payload.get("_schools", {})
        for idx, row in pros.iterrows():
            if pd.notna(pros.at[idx, "years_in_college"]):
                continue
            school = row.get("college")
            cfbd_name = school_to_cfbd.get(school)
            roster = rosters.get(cfbd_name, []) if cfbd_name else []
            if not roster:
                continue
            names = [f"{p.get('firstName','')} {p.get('lastName','')}".strip() for p in roster]
            best = process.extractOne(row["player"], names, scorer=fuzz.WRatio)
            if best is None or best[1] < 90:
                continue
            y = roster[best[2]].get("year")
            if isinstance(y, (int, float)) and 1 <= y <= 5:
                pros.at[idx, "years_in_college"] = int(y)

    pros["is_underclassman"] = (pros["years_in_college"] <= 3).astype("Int64")


def step6_experience_score(hist: pd.DataFrame, pros: pd.DataFrame):
    """experience_score = years_in_college * games_played (or *10 if games missing)."""
    print("[6] experience_score")
    for df in (hist, pros):
        yrs = df["years_in_college"].astype("float")
        gms = df["games_played"] if "games_played" in df.columns else pd.Series([np.nan] * len(df))
        fallback = yrs * 10
        df["experience_score"] = np.where(gms.notna(), yrs * gms, fallback)


def step7_size_score(hist: pd.DataFrame, pros: pd.DataFrame):
    """height_z, weight_z, size_score — position-adjusted using 2020-2025 means."""
    print("[7] height/weight z, size_score")
    ref = _group_stats(hist, ["height", "weight"])

    def apply(df: pd.DataFrame):
        df["height_z"] = df.apply(lambda r: _z_for_row(r, ref, "height", False), axis=1)
        df["weight_z"] = df.apply(lambda r: _z_for_row(r, ref, "weight", False), axis=1)
        df["size_score"] = df[["height_z", "weight_z"]].mean(axis=1, skipna=True)

    apply(hist); apply(pros)


def step8_dominator_rating(hist: pd.DataFrame, pros: pd.DataFrame, api_key: str):
    """SKILL only. dominator = (player_rec_yds + player_rush_yds) / team_total_yds * 100."""
    print("[8] dominator rating (SKILL only)")
    cache = RAW_DIR / "cfbd_team_season_stats.json"
    if cache.exists():
        by_year = json.loads(cache.read_text(encoding="utf-8"))
        by_year = {int(k): v for k, v in by_year.items()}
    else:
        by_year = {}
        for yr in list(range(2019, 2025)) + [2025]:
            data = cfbd_get("/stats/season", {"year": yr}, api_key)
            if data is None:
                log_fail("step8", f"season stats {yr}")
                continue
            by_year[yr] = data
            time.sleep(0.3)
        cache.write_text(json.dumps(by_year), encoding="utf-8")

    def team_total(year: int, college: str) -> float:
        teams = by_year.get(year, [])
        if not teams or not isinstance(college, str):
            return np.nan
        names = sorted({t.get("team", "") for t in teams})
        best = process.extractOne(college, names, scorer=fuzz.WRatio)
        if best is None or best[1] < 85:
            return np.nan
        target = best[0]
        total = 0.0
        found = False
        for t in teams:
            if t.get("team") != target:
                continue
            sn = t.get("statName") or ""
            if sn == "totalYards":
                total = float(t.get("statValue", 0) or 0)
                found = True
                break
        return total if found else np.nan

    def compute(df: pd.DataFrame, year_fn):
        rec = df.get("rec_yds", pd.Series([np.nan]*len(df)))
        rush = df.get("rush_yds", pd.Series([np.nan]*len(df)))
        is_skill = df["position_group"] == "SKILL" if "position_group" in df.columns else pd.Series([False]*len(df))
        team_yds = []
        for idx, row in df.iterrows():
            if not is_skill.iloc[idx]:
                team_yds.append(np.nan)
                continue
            team_yds.append(team_total(year_fn(row), row.get("college")))
        df["team_total_yards"] = team_yds
        num = rec.fillna(0) + rush.fillna(0)
        df["dominator_rating"] = np.where(
            is_skill & (df["team_total_yards"] > 0),
            num / df["team_total_yards"] * 100,
            np.nan,
        )

    compute(hist, lambda r: int(r["year"]) - 1)
    compute(pros, lambda r: 2025)


def step9_qb_features(hist: pd.DataFrame, pros: pd.DataFrame):
    """QB-only derived features."""
    print("[9] QB-specific features")
    def apply(df: pd.DataFrame, starts_col: Optional[str]):
        is_qb = df["position_group"] == "QB" if "position_group" in df.columns else pd.Series([False]*len(df))
        pa = df.get("pass_att", pd.Series([np.nan]*len(df)))
        pt = df.get("pass_td", pd.Series([np.nan]*len(df)))
        pi = df.get("pass_int", pd.Series([np.nan]*len(df)))
        py = df.get("pass_yds", pd.Series([np.nan]*len(df)))
        pc = df.get("pass_cmp", pd.Series([np.nan]*len(df)))
        ry = df.get("rush_yds", pd.Series([np.nan]*len(df)))
        rt = df.get("rush_td", pd.Series([np.nan]*len(df)))
        gp = df.get("games_played", pd.Series([np.nan]*len(df)))

        df["td_int_ratio"] = np.where(is_qb, pt / pi.replace(0, 1).clip(lower=1), np.nan)
        df["yards_per_attempt"] = np.where(is_qb & (pa > 0), py / pa, np.nan)
        df["completion_pct"] = np.where(is_qb & (pa > 0), pc / pa * 100, np.nan)
        df["dual_threat_score"] = np.where(
            is_qb & (gp.fillna(1) > 0),
            (ry.fillna(0) * 0.5 + rt.fillna(0) * 5) / gp.fillna(1).clip(lower=1),
            np.nan,
        )
        # college_starts_sweet_spot — we don't reliably have career starts;
        # approximate from years_in_college*games_played if available.
        starts = (df["years_in_college"].fillna(0) * gp.fillna(0))
        df["college_starts_sweet_spot"] = np.where(
            is_qb, ((starts >= 25) & (starts <= 34)).astype(int), np.nan,
        )

    apply(hist, None); apply(pros, None)


POWER5 = {"ACC", "Big Ten", "Big 12", "Pac-12", "SEC"}
G5 = {"American Athletic", "Mountain West", "Conference USA",
      "Mid-American", "Sun Belt"}


def step10_conference_tier(hist: pd.DataFrame, pros: pd.DataFrame):
    """Ensure conference_tier present in both files."""
    print("[10] conference tier")
    cache = RAW_DIR / "cfbd_teams.json"
    if not cache.exists():
        log_fail("step10", "cfbd_teams.json cache missing — run build_feature_matrix first")
        for df in (hist, pros):
            df["conference_tier"] = 1
        return
    teams_map = json.loads(cache.read_text(encoding="utf-8"))
    names = list(teams_map.keys())

    def tier(college: str) -> int:
        if not isinstance(college, str):
            return 1
        conf = teams_map.get(college)
        if conf is None:
            best = process.extractOne(college, names, scorer=fuzz.WRatio)
            if best and best[1] >= 85:
                conf = teams_map.get(best[0])
        if conf in POWER5:
            return 3
        if conf in G5:
            return 2
        return 1

    for df in (hist, pros):
        df["conference_tier"] = df["college"].apply(tier)


# =====================================================================
# PART B — PROSPECTS ONLY (re-ranker signals, best-effort scrapes)
# =====================================================================

def _names_in_text(names: list[str], text: str) -> set[str]:
    """Return names whose exact (case-insensitive) string appears in the text."""
    t = text.lower()
    hit = set()
    for n in names:
        if not isinstance(n, str) or len(n) < 5:
            continue
        if n.lower() in t:
            hit.add(n)
    return hit


def step11_mock_variance(pros: pd.DataFrame):
    """Best-effort: the consensus big board page may show range/stddev inline."""
    print("[11] mock variance")
    for col in ("boards_count", "rank_high", "rank_low", "rank_stddev", "rank_range"):
        pros[col] = np.nan
    html = web_get("https://www.nflmockdraftdatabase.com/big-boards/2026/consensus-big-board-2026")
    if html is None:
        log_fail("step11", "big board fetch returned None")
        return
    soup = BeautifulSoup(html, "lxml")
    ul = soup.find("ul")
    if ul is None:
        log_fail("step11", "no <ul> on big board page")
        return
    parsed = 0
    for li in ul.find_all("li", recursive=False):
        name_link = li.find("a", href=lambda h: h and "/players/2026/" in h)
        if not name_link:
            continue
        name = name_link.get_text(strip=True)
        text = li.get_text(" ", strip=True)
        # Patterns the page sometimes shows: "High: 12 | Low: 45" or "(45 boards)"
        m_boards = re.search(r"(\d+)\s+boards?", text, re.IGNORECASE)
        m_high = re.search(r"high[: ]+(\d+)", text, re.IGNORECASE)
        m_low = re.search(r"low[: ]+(\d+)", text, re.IGNORECASE)
        m_std = re.search(r"std\s*dev[: ]+([\d.]+)", text, re.IGNORECASE)
        mask = pros["player"] == name
        if not mask.any():
            continue
        if m_boards:
            pros.loc[mask, "boards_count"] = int(m_boards.group(1))
        if m_high:
            pros.loc[mask, "rank_high"] = int(m_high.group(1))
        if m_low:
            pros.loc[mask, "rank_low"] = int(m_low.group(1))
        if m_std:
            pros.loc[mask, "rank_stddev"] = float(m_std.group(1))
        parsed += 1
    pros["rank_range"] = pros["rank_low"] - pros["rank_high"]
    if pros["rank_stddev"].isna().all() and pros["rank_range"].notna().any():
        pros["rank_stddev"] = pros["rank_range"] / 4.0
    coverage = pros[["boards_count", "rank_high", "rank_low"]].notna().any(axis=1).mean() * 100
    print(f"  variance coverage: {coverage:.1f}% (parsed {parsed} rows)")
    if coverage < 5:
        log_fail("step11", f"only {coverage:.1f}% coverage — page likely doesn't expose per-player variance")


def step12_betting(pros: pd.DataFrame):
    """Best-effort: VegasInsider draft odds. Per-player structured data is rare."""
    print("[12] betting odds")
    for col in ("betting_first_round_prob", "betting_pick_ou", "betting_implied_prob"):
        pros[col] = np.nan
    html = web_get("https://www.vegasinsider.com/nfl/odds/draft/")
    if html is None:
        log_fail("step12", "vegasinsider fetch failed")
        return
    # Try to parse any American-odds numbers near player names
    soup = BeautifulSoup(html, "lxml")
    text = soup.get_text(" ", strip=True)
    names = pros["player"].dropna().astype(str).tolist()
    found = _names_in_text(names, text)
    if not found:
        log_fail("step12", "no 2026 prospect names found on VegasInsider draft page")
        return
    # For each found name, try to pull odds patterns near it. Very noisy.
    for name in found:
        idx = text.find(name)
        window = text[max(0, idx - 60): idx + 200]
        m = re.search(r"([+-]\d{3,5})", window)
        if not m:
            continue
        odds = int(m.group(1))
        prob = (100 / (odds + 100)) if odds > 0 else (-odds / (-odds + 100))
        mask = pros["player"] == name
        pros.loc[mask, "betting_implied_prob"] = prob
    cov = pros["betting_implied_prob"].notna().mean() * 100
    print(f"  betting coverage: {cov:.1f}% ({int(pros['betting_implied_prob'].notna().sum())} prospects)")


def step13_top30_visits(pros: pd.DataFrame):
    """Best-effort: CBS Top-30 visits tracker."""
    print("[13] top-30 visits")
    pros["visit_count"] = 0
    pros["top30_visit_flag"] = 0
    pros["visited_teams"] = ""
    pros["visit_cancelled_flag"] = 0

    for url in ("https://www.cbssports.com/nfl/news/nfl-draft-top-30-visits-tracker-2026/",
                "https://nfltraderumors.co/2026-nfl-draft-visit-tracker/"):
        html = web_get(url)
        if html is None:
            log_fail("step13", f"{url} fetch failed")
            continue
        soup = BeautifulSoup(html, "lxml")
        text = soup.get_text("\n", strip=True)
        # Find player-name hits and nearby team mentions
        names = pros["player"].dropna().astype(str).tolist()
        from_here = _names_in_text(names, text)
        for name in from_here:
            idx = text.find(name)
            window = text[max(0, idx - 100): idx + 400]
            teams = set(re.findall(r"\b(49ers|Bears|Bengals|Bills|Broncos|Browns|Buccaneers|Cardinals|Chargers|Chiefs|Colts|Commanders|Cowboys|Dolphins|Eagles|Falcons|Giants|Jaguars|Jets|Lions|Packers|Panthers|Patriots|Raiders|Rams|Ravens|Saints|Seahawks|Steelers|Texans|Titans|Vikings)\b", window))
            cancelled = bool(re.search(r"cancel|withdrew|pull", window, re.IGNORECASE))
            mask = pros["player"] == name
            existing = pros.loc[mask, "visited_teams"].iloc[0]
            merged = set(existing.split(",")) if existing else set()
            merged |= teams
            merged.discard("")
            pros.loc[mask, "visited_teams"] = ",".join(sorted(merged))
            pros.loc[mask, "visit_count"] = len(merged)
            pros.loc[mask, "top30_visit_flag"] = int(len(merged) > 0)
            if cancelled:
                pros.loc[mask, "visit_cancelled_flag"] = 1

    n = int(pros["top30_visit_flag"].sum())
    print(f"  prospects with any visit reported: {n}")


def step14_stock_direction(pros: pd.DataFrame):
    """Best-effort: ESPN risers and TWSN fallers."""
    print("[14] stock direction (risers/fallers)")
    pros["stock_direction"] = 0

    riser_html = web_get("https://www.espn.com/nfl/draft2026/story/_/id/48443025/"
                         "2026-nfl-draft-risers-prospects-freeling-thieneman-iheanachor")
    if riser_html:
        text = BeautifulSoup(riser_html, "lxml").get_text(" ", strip=True)
        names = pros["player"].dropna().astype(str).tolist()
        risers = _names_in_text(names, text)
        pros.loc[pros["player"].isin(risers), "stock_direction"] = 1
        print(f"  risers: {len(risers)}")
    else:
        log_fail("step14", "ESPN risers fetch failed")

    faller_html = web_get("https://twsn.net/2026/04/12/2026-nfl-draft-risers-fallers-offense/")
    if faller_html:
        text = BeautifulSoup(faller_html, "lxml").get_text(" ", strip=True)
        names = pros["player"].dropna().astype(str).tolist()
        # Find "fallers" section and parse names from there
        m = re.search(r"faller", text, re.IGNORECASE)
        tail = text[m.start():] if m else text
        fallers = _names_in_text(names, tail)
        # Only down-grade if not already a riser
        mask = (pros["player"].isin(fallers)) & (pros["stock_direction"] == 0)
        pros.loc[mask, "stock_direction"] = -1
        print(f"  fallers: {int(mask.sum())}")
    else:
        log_fail("step14", "TWSN fallers fetch failed")


def step15_senior_bowl(pros: pd.DataFrame):
    """Best-effort: 2026 Senior Bowl coverage flags."""
    print("[15] senior bowl")
    pros["senior_bowl_standout"] = 0
    pros["senior_bowl_invite"] = 0
    html = web_get("https://www.nfl.com/news/2026-senior-bowl-game-takeaways-2026-nfl-draft")
    if html is None:
        log_fail("step15", "NFL.com senior bowl article fetch failed")
        return
    text = BeautifulSoup(html, "lxml").get_text(" ", strip=True)
    names = pros["player"].dropna().astype(str).tolist()
    hits = _names_in_text(names, text)
    pros.loc[pros["player"].isin(hits), "senior_bowl_standout"] = 1
    pros.loc[pros["player"].isin(hits), "senior_bowl_invite"] = 1
    print(f"  mentions: {len(hits)}")


def step16_cfp(pros: pd.DataFrame):
    """Best-effort: CFP participant flag."""
    print("[16] CFP participant")
    pros["cfp_participant"] = 0
    html = web_get("https://www.espn.com/nfl/draft2026/story/_/id/47304617/"
                   "2026-nfl-draft-prospects-college-football-playoff-indiana-ohio-state-georgia")
    if html is None:
        log_fail("step16", "ESPN CFP article fetch failed")
        return
    text = BeautifulSoup(html, "lxml").get_text(" ", strip=True)
    names = pros["player"].dropna().astype(str).tolist()
    hits = _names_in_text(names, text)
    pros.loc[pros["player"].isin(hits), "cfp_participant"] = 1
    print(f"  CFP participants flagged: {len(hits)}")


def step17_injury(pros: pd.DataFrame):
    """DNP flag derivable from data we have; optional keyword search in combine article."""
    print("[17] injury flags")
    key_drills = ["40_yard", "vertical", "broad_jump", "three_cone", "shuttle"]
    invited = pros["combine_invite"] == 1
    missing_any = pros[key_drills].isna().any(axis=1)
    pros["injury_dnp_flag"] = (invited & missing_any).astype(int)

    # Top-50 keyword search in cached CBS combine HTML, if available
    pros["acl_flag"] = 0
    pros["shoulder_flag"] = 0
    pros["spine_flag"] = 0
    cbs_html_path = RAW_DIR / "_combine_2026_raw.html"
    if cbs_html_path.exists():
        text = cbs_html_path.read_text(encoding="utf-8", errors="ignore").lower()
        top50 = pros.sort_values("rank").head(50)
        for _, row in top50.iterrows():
            name = (row.get("player") or "").lower()
            if not name or name not in text:
                continue
            idx = text.find(name)
            window = text[max(0, idx - 200): idx + 600]
            if any(k in window for k in ("acl", "tear")):
                pros.loc[pros["player"] == row["player"], "acl_flag"] = 1
            if "shoulder" in window:
                pros.loc[pros["player"] == row["player"], "shoulder_flag"] = 1
            if "spine" in window or "vertebr" in window or "back " in window:
                pros.loc[pros["player"] == row["player"], "spine_flag"] = 1

    pros["has_injury_flag"] = (
        (pros["injury_dnp_flag"] == 1)
        | (pros["acl_flag"] == 1)
        | (pros["shoulder_flag"] == 1)
        | (pros["spine_flag"] == 1)
    ).astype(int)
    print(f"  DNP flags: {int(pros['injury_dnp_flag'].sum())}  "
          f"any injury flag: {int(pros['has_injury_flag'].sum())}")


def step18_heisman(pros: pd.DataFrame):
    """Hardcode known 2025 major-award winners. Leave incomplete entries as 0."""
    print("[18] heisman / major awards")
    # The 2025-season Heisman winner isn't known to me at script-write time;
    # leaving this as an explicit blank hook the user can populate.
    heisman_winners: set[str] = set()   # e.g. {"Fernando Mendoza"}
    major_award_winners: set[str] = set()

    pros["heisman_flag"] = pros["player"].isin(heisman_winners).astype(int)
    pros["major_award_flag"] = pros["player"].isin(
        heisman_winners | major_award_winners).astype(int)
    if not heisman_winners:
        log_fail("step18",
                 "no Heisman winner hardcoded — all prospects get 0. Edit step18_heisman to populate.")


# =====================================================================
# PART C — TEAM CONTEXT
# =====================================================================

# Step 20: new HC info
NEW_HC_2026 = {"LV", "BAL", "NYG", "CLE", "MIA", "ARI", "BUF"}
HC_NAMES = {
    "LV": "Kubiak", "BAL": "Minter", "NYG": "Harbaugh", "CLE": "Monken",
    "MIA": "Hafley", "ARI": "LaFleur", "BUF": "Brady",
}
HC_TREES = {
    "Kubiak": "Shanahan", "LaFleur": "McVay-Shanahan", "Harbaugh": "Michigan-Harbaugh",
    "Brady": "Bills", "Hafley": "defensive-specialist",
    "Minter": "Harbaugh-def", "Monken": "Stefanski",
}

# Step 21: GM tendencies (user provided)
GM_TENDENCIES = {
    "LAR": {"gm": "Les Snead", "trade_down_rate": 0.89, "trade_up_rate": 0.11},
    "SEA": {"gm": "John Schneider", "trade_down_rate": 0.65, "trade_up_rate": 0.35},
    "NO": {"gm": "Mickey Loomis", "trade_down_rate": 0.0, "trade_up_rate": 1.0},
    "PHI": {"gm": "Howie Roseman", "trade_down_rate": 0.3, "trade_up_rate": 0.7},
    "KC": {"gm": "Brett Veach", "trade_down_rate": 0.4, "trade_up_rate": 0.6},
    "IND": {"gm": "Chris Ballard", "trade_down_rate": 0.75, "trade_up_rate": 0.25},
    "GB": {"gm": "Brian Gutekunst", "trade_down_rate": 0.5, "trade_up_rate": 0.5},
    "CIN": {"gm": "Duke Tobin", "trade_down_rate": 0.9, "trade_up_rate": 0.1},
    "LAC": {"gm": "Joe Hortiz", "trade_down_rate": 0.9, "trade_up_rate": 0.1},
    "DAL": {"gm": "Jerry Jones", "trade_down_rate": 0.3, "trade_up_rate": 0.7},
    "SF": {"gm": "John Lynch", "trade_down_rate": 0.4, "trade_up_rate": 0.6},
    "BAL": {"gm": "Eric DeCosta", "trade_down_rate": 0.5, "trade_up_rate": 0.5},
    "MIN": {"gm": "Kwesi Adofo-Mensah", "trade_down_rate": 0.6, "trade_up_rate": 0.4},
    "DEN": {"gm": "George Paton", "trade_down_rate": 0.5, "trade_up_rate": 0.5},
    "MIA": {"gm": "Jon-Eric Sullivan", "trade_down_rate": 0.5, "trade_up_rate": 0.5},
    "LV": {"gm": "John Spytek", "trade_down_rate": 0.5, "trade_up_rate": 0.5},
    "ARI": {"gm": "Monti Ossenfort", "trade_down_rate": 0.5, "trade_up_rate": 0.5},
    "NYJ": {"gm": "Darren Mougey", "trade_down_rate": 0.5, "trade_up_rate": 0.5},
    "TEN": {"gm": "Mike Borgonzi", "trade_down_rate": 0.5, "trade_up_rate": 0.5},
    "NYG": {"gm": "Joe Schoen", "trade_down_rate": 0.4, "trade_up_rate": 0.6},
    "CAR": {"gm": "Dan Morgan", "trade_down_rate": 0.5, "trade_up_rate": 0.5},
    "ATL": {"gm": "Terry Fontenot", "trade_down_rate": 0.5, "trade_up_rate": 0.5},
    "JAX": {"gm": "James Gladstone", "trade_down_rate": 0.5, "trade_up_rate": 0.5},
    "PIT": {"gm": "Omar Khan", "trade_down_rate": 0.5, "trade_up_rate": 0.5},
    "CLE": {"gm": "Andrew Berry", "trade_down_rate": 0.5, "trade_up_rate": 0.5},
    "DET": {"gm": "Brad Holmes", "trade_down_rate": 0.4, "trade_up_rate": 0.6},
    "CHI": {"gm": "Ryan Poles", "trade_down_rate": 0.5, "trade_up_rate": 0.5},
    "WAS": {"gm": "Adam Peters", "trade_down_rate": 0.5, "trade_up_rate": 0.5},
    "HOU": {"gm": "Nick Caserio", "trade_down_rate": 0.4, "trade_up_rate": 0.6},
    "TB": {"gm": "Jason Licht", "trade_down_rate": 0.45, "trade_up_rate": 0.55},
    "BUF": {"gm": "Brandon Beane", "trade_down_rate": 0.4, "trade_up_rate": 0.6},
    "NE": {"gm": "Eliot Wolf", "trade_down_rate": 0.5, "trade_up_rate": 0.5},
}
# Which GMs are new-ish (first year on job — reduced reliability of tendency data)
NEW_GMS = {"MIA", "LV", "NYJ", "TEN", "JAX", "NE"}  # heuristic


def step19_cap_space(team: pd.DataFrame):
    """Best-effort: Spotrac is usually bot-protected."""
    print("[19] cap space (Spotrac)")
    team["cap_space_2026"] = np.nan
    team["dead_money"] = np.nan
    html = web_get("https://www.spotrac.com/nfl/cap/")
    if html is None:
        log_fail("step19", "Spotrac fetch failed (likely bot-protected)")
        return
    # Parse table if present
    soup = BeautifulSoup(html, "lxml")
    table = soup.find("table")
    if table is None:
        log_fail("step19", "no <table> on Spotrac page")
        return
    # Would need careful parsing; log presence and move on.
    log_fail("step19", "Spotrac HTML received but parser not implemented — left nulls")


def step20_new_hc(team: pd.DataFrame):
    print("[20] new HC flags")
    team["new_hc_flag"] = team["team"].isin(NEW_HC_2026).astype(int)
    team["hc_name"] = team["team"].map(HC_NAMES).fillna("")
    team["hc_coaching_tree"] = team["hc_name"].map(HC_TREES).fillna("")


def step21_gm(team: pd.DataFrame):
    print("[21] GM tendencies")
    team["gm_name"] = team["team"].map(lambda t: GM_TENDENCIES.get(t, {}).get("gm", ""))
    team["trade_up_rate"] = team["team"].map(
        lambda t: GM_TENDENCIES.get(t, {}).get("trade_up_rate", np.nan))
    team["trade_down_rate"] = team["team"].map(
        lambda t: GM_TENDENCIES.get(t, {}).get("trade_down_rate", np.nan))
    team["gm_data_reliable"] = team["team"].apply(lambda t: 0 if t in NEW_GMS else 1)


def step22_nfl_needs(team: pd.DataFrame):
    """Best-effort: NFL.com per-team needs article."""
    print("[22] NFL.com team needs override")
    team["need_1"] = ""
    team["need_2"] = ""
    team["need_3"] = ""
    html = web_get("https://www.nfl.com/news/2026-nfl-draft-order-round-1-needs-for-all-32-teams")
    if html is None:
        log_fail("step22", "NFL.com team-needs article fetch failed")
        return
    soup = BeautifulSoup(html, "lxml")
    # The article commonly uses <h3>Team Name</h3> followed by a "Needs:" paragraph.
    # Parse conservatively.
    full_text = soup.get_text("\n", strip=True)
    for team_abbr in team["team"].unique():
        # We'd need a team_abbr -> full_name map; reuse draft-order map
        pass
    log_fail("step22", "NFL.com article parsing is stub-only — need_1/2/3 left empty")


def step23_fa_needs(team: pd.DataFrame):
    """Best-effort: free-agency signings → positions already addressed."""
    print("[23] FA addressed positions")
    team["fa_addressed_positions"] = ""
    team["need_eliminated_flag"] = 0
    html = web_get("https://www.nfl.com/news/2026-nfl-free-agency-tracker-latest-signings-trades-contract-info-for-all-32-teams")
    if html is None:
        log_fail("step23", "FA tracker fetch failed")
        return
    # Text analysis would require long prose parsing; leave stub.
    log_fail("step23", "FA tracker parse not implemented — stub nulls")


def step24_trade_risk(team: pd.DataFrame):
    print("[24] trade risk flags per pick")
    def risk(pick):
        if 1 <= pick <= 10:
            return 0.0
        if 11 <= pick <= 22:
            return 0.5
        return 1.0
    team["trade_risk_flag"] = team["pick_number"].apply(risk)
    # Specific heightened intel: Cowboys #11, #20; Jets #2 (user-provided)
    elevated_picks = set()
    dal_picks = team.loc[team["team"] == "DAL", "pick_number"].head(2).tolist()
    elevated_picks.update(dal_picks)
    nyj_early = team.loc[team["team"] == "NYJ", "pick_number"].iloc[0] \
        if (team["team"] == "NYJ").any() else None
    if nyj_early is not None:
        elevated_picks.add(nyj_early)
    team["elevated_trade_flag"] = team["pick_number"].isin(elevated_picks).astype(int)


# =====================================================================
# PART D — DEMAND SCORE
# =====================================================================

def step25_demand(pros: pd.DataFrame, team: pd.DataFrame, needs: pd.DataFrame) -> pd.DataFrame:
    """For each prospect, count teams with pick < prospect's rank whose top-3
    needs include the prospect's position_group."""
    print("[25] demand score")
    # Build team -> top-3 needs (use team_needs_2026 ranking if need_1/2/3 absent)
    if "need_1" in team.columns and team["need_1"].astype(bool).any():
        team_needs_map = {r["team"]: {r.get("need_1"), r.get("need_2"), r.get("need_3")}
                          for _, r in team.iterrows()}
    else:
        team_needs_map = {}
        for t, sub in needs.groupby("team"):
            top3 = sub.sort_values("need_rank").head(3)["position"].tolist()
            team_needs_map[t] = set(top3)

    # Build pick_number -> (team, round) from team context
    pick_rows = team[["pick_number", "team", "round"]].sort_values("pick_number")

    prospects_out = pros.copy()
    demand = []
    needy = []
    for _, row in prospects_out.iterrows():
        rank = row.get("rank")
        pos = row.get("position_group")
        if pd.isna(rank) or not isinstance(pos, str):
            demand.append(0)
            needy.append(0)
            continue
        rank = int(rank)
        teams_ahead = pick_rows[pick_rows["pick_number"] < rank]["team"]
        count = sum(1 for t in teams_ahead if pos in team_needs_map.get(t, set()))
        demand.append(count)
        needy.append(count)
    prospects_out["demand_score"] = demand
    prospects_out["needy_teams_ahead"] = needy
    return prospects_out


# =====================================================================
# MAIN
# =====================================================================

def _report(df: pd.DataFrame, name: str, new_cols: list[str]) -> None:
    print(f"\n--- {name} ---")
    print(f"  total columns: {df.shape[1]}")
    miss_rows = []
    for c in new_cols:
        if c in df.columns:
            pct = df[c].isna().mean() * 100
            miss_rows.append((c, pct))
    miss_rows.sort(key=lambda x: -x[1])
    print("  % missing per NEW column:")
    for c, pct in miss_rows:
        print(f"    {pct:5.1f}%  {c}")


def main():
    PROC_DIR.mkdir(parents=True, exist_ok=True)
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    hist = filter_historical()
    pros = pd.read_csv(PROS_CSV)
    team = pd.read_csv(TEAM_CTX_CSV)
    needs = pd.read_csv(TEAM_NEEDS_CSV)

    api_key = load_api_key()

    base_hist_cols = set(hist.columns)
    base_pros_cols = set(pros.columns)
    base_team_cols = set(team.columns)

    # --- PART A ---
    step1_ras(hist, pros)
    step2_speed_score(hist, pros)
    step3_sp_plus(hist, pros, api_key)
    step4_positional_scarcity(hist, pros)
    step5_college_experience(hist, pros)
    step6_experience_score(hist, pros)
    step7_size_score(hist, pros)
    try:
        step8_dominator_rating(hist, pros, api_key)
    except Exception as e:
        log_fail("step8", f"{type(e).__name__}: {e}")
    step9_qb_features(hist, pros)
    step10_conference_tier(hist, pros)

    # Save historical now (Part A applied)
    hist.to_csv(HIST_CSV, index=False)

    # --- PART B (prospects only, best-effort) ---
    for step in (step11_mock_variance, step12_betting, step13_top30_visits,
                 step14_stock_direction, step15_senior_bowl, step16_cfp,
                 step17_injury, step18_heisman):
        try:
            step(pros)
        except Exception as e:
            log_fail(step.__name__, f"{type(e).__name__}: {e}")

    pros.to_csv(PROS_ENRICHED_CSV, index=False)

    # --- PART C (team context) ---
    for step in (step19_cap_space, step20_new_hc, step21_gm,
                 step22_nfl_needs, step23_fa_needs, step24_trade_risk):
        try:
            step(team)
        except Exception as e:
            log_fail(step.__name__, f"{type(e).__name__}: {e}")

    team.to_csv(TEAM_ENRICHED_CSV, index=False)

    # --- PART D ---
    pros_demand = step25_demand(pros, team, needs)
    pros_demand.to_csv(PROS_DEMAND_CSV, index=False)

    # =====================================================================
    # Summary
    # =====================================================================
    new_hist = [c for c in hist.columns if c not in base_hist_cols]
    new_pros = [c for c in pros.columns if c not in base_pros_cols]
    new_team = [c for c in team.columns if c not in base_team_cols]

    print("\n" + "=" * 70)
    print("ENRICHMENT SUMMARY")
    print("=" * 70)
    _report(hist, "draft_with_college.csv (2020+)", new_hist)
    _report(pros, "prospects_2026_enriched.csv", new_pros)
    _report(team, "team_context_2026_enriched.csv", new_team)
    print(f"\nprospects_with_demand.csv rows: {len(pros_demand)}")
    print(f"  prospects with demand_score > 0: "
          f"{int((pros_demand['demand_score'] > 0).sum())}")

    # Part B coverage
    print("\nPart B coverage (prospects):")
    for cols, label in [
        (["boards_count", "rank_high", "rank_low"], "mock variance"),
        (["betting_implied_prob"], "betting"),
        (["top30_visit_flag"], "visits"),
        (["stock_direction"], "stock direction"),
        (["senior_bowl_standout"], "senior bowl"),
        (["cfp_participant"], "CFP participant"),
    ]:
        if all(c in pros.columns for c in cols):
            any_set = (pros[cols].fillna(0).astype(bool)).any(axis=1).mean() * 100
            print(f"  {label:<20} {any_set:.1f}%")

    # Team missing cap / needs data
    missing_cap = team[team["cap_space_2026"].isna()]["team"].tolist() \
        if "cap_space_2026" in team.columns else []
    missing_needs = team[team["need_1"] == ""]["team"].unique().tolist() \
        if "need_1" in team.columns else []
    print(f"\nTeams missing cap data: {len(set(missing_cap))}")
    print(f"Teams missing NFL.com needs override: {len(set(missing_needs))}")

    if FAILURES:
        print("\nFAILURES / STUBS:")
        for step, detail in FAILURES:
            print(f"  {step}: {detail}")


if __name__ == "__main__":
    main()
