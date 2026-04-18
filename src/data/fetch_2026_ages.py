"""
Estimate 2026 prospect ages via CFBD roster class year.

For each unique school on the consensus big board we pull
  GET /roster?team={school}&year=2025
and fuzzy-match prospects to roster names. The CFBD `year` field is the
class year (1 = Fr, 2 = So, 3 = Jr, 4 = Sr, 5 = Gr).

age_at_draft = 18 + class_year   (Fr = 19 ... Gr = 23)

Overwrites the earlier nflverse-based attempt with estimated values.

Outputs
-------
  data/raw/cfbd_rosters_2025.json       cached raw rosters keyed by school
  data/processed/prospects_2026.csv     updated in place
"""

import json
import os
import sys
import time
from pathlib import Path

import pandas as pd
import requests
from rapidfuzz import fuzz, process

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from fetch_college_stats_api import load_api_key  # noqa: E402

PROSPECTS_CSV = ROOT / "data" / "processed" / "prospects_2026.csv"
ROSTERS_JSON = ROOT / "data" / "raw" / "cfbd_rosters_2025.json"
COMBINE_HIST_CSV = ROOT / "data" / "raw" / "combine_data_2011_2025.csv"
COMBINE_2026_CSV = ROOT / "data" / "raw" / "combine_2026.csv"

API_BASE = "https://api.collegefootballdata.com"
SEASON = 2025
NAME_FUZZ_THRESHOLD = 90
SCHOOL_FUZZ_THRESHOLD = 85
REQUEST_DELAY_SEC = 0.5


def fetch_roster(api_key: str, school: str) -> list[dict]:
    r = requests.get(
        f"{API_BASE}/roster",
        headers={"Authorization": f"Bearer {api_key}", "Accept": "application/json"},
        params={"team": school, "year": SEASON},
        timeout=30,
    )
    if r.status_code != 200:
        return []
    try:
        return r.json() or []
    except ValueError:
        return []


def fetch_all_teams(api_key: str) -> list[str]:
    """All FBS + FCS team names for a given season — used to canonicalise
    prospect schools whose literal name doesn't match CFBD's spelling."""
    names: set[str] = set()
    for cls in ("fbs", "fcs"):
        r = requests.get(
            f"{API_BASE}/teams",
            headers={"Authorization": f"Bearer {api_key}", "Accept": "application/json"},
            params={"classification": cls, "year": SEASON},
            timeout=30,
        )
        if r.ok:
            for t in r.json():
                name = t.get("school")
                if name:
                    names.add(name)
    return sorted(names)


def canonical_school(prospect_school: str, known: list[str]) -> str | None:
    if not isinstance(prospect_school, str) or not prospect_school.strip():
        return None
    # Exact match first
    if prospect_school in known:
        return prospect_school
    best = process.extractOne(prospect_school, known, scorer=fuzz.WRatio)
    if best is None:
        return None
    name, score, _ = best
    return name if score >= SCHOOL_FUZZ_THRESHOLD else None


def load_or_fetch_rosters(prospects: pd.DataFrame, api_key: str) -> dict[str, list[dict]]:
    if ROSTERS_JSON.exists():
        rosters = json.loads(ROSTERS_JSON.read_text(encoding="utf-8"))
        print(f"Loaded cached rosters: {len(rosters)} schools")
        return rosters

    print("Fetching full FBS + FCS team list...")
    known_teams = fetch_all_teams(api_key)
    print(f"  {len(known_teams)} teams in CFBD")

    prospect_schools = sorted(
        {s for s in prospects["school"].dropna().astype(str) if s.strip()}
    )
    print(f"  {len(prospect_schools)} unique prospect schools")

    school_to_cfbd: dict[str, str | None] = {}
    cfbd_targets: set[str] = set()
    unmapped: list[str] = []
    for s in prospect_schools:
        c = canonical_school(s, known_teams)
        school_to_cfbd[s] = c
        if c:
            cfbd_targets.add(c)
        else:
            unmapped.append(s)
    if unmapped:
        print(f"  WARNING: {len(unmapped)} prospect schools failed to map: {unmapped[:10]}...")

    print(f"Fetching {len(cfbd_targets)} rosters (~{len(cfbd_targets) * REQUEST_DELAY_SEC:.0f}s)...")
    rosters: dict[str, list[dict]] = {}
    for i, cfbd_name in enumerate(sorted(cfbd_targets), start=1):
        rosters[cfbd_name] = fetch_roster(api_key, cfbd_name)
        time.sleep(REQUEST_DELAY_SEC)
        if i % 25 == 0:
            print(f"  {i}/{len(cfbd_targets)} rosters fetched")

    # Preserve the prospect -> cfbd mapping alongside the rosters
    payload = {"_schools": school_to_cfbd, "rosters": rosters}
    ROSTERS_JSON.write_text(json.dumps(payload), encoding="utf-8")
    print(f"Saved -> {ROSTERS_JSON}")
    return payload


def match_and_age(prospects: pd.DataFrame, payload: dict) -> pd.DataFrame:
    school_to_cfbd = payload["_schools"]
    rosters = payload["rosters"]

    # Drop prior (stale) age columns if present
    for c in ("age_at_draft", "age_estimated", "has_age"):
        if c in prospects.columns:
            prospects = prospects.drop(columns=[c])

    ages: list[float | None] = []
    estimated_flags: list[int] = []
    for _, row in prospects.iterrows():
        school = row.get("school")
        name = row.get("player")
        cfbd_name = school_to_cfbd.get(school)
        roster = rosters.get(cfbd_name, []) if cfbd_name else []
        if not roster or not isinstance(name, str):
            ages.append(None)
            estimated_flags.append(0)
            continue

        roster_names = [f"{p.get('firstName', '')} {p.get('lastName', '')}".strip()
                        for p in roster]
        best = process.extractOne(name, roster_names, scorer=fuzz.WRatio)
        if best is None:
            ages.append(None)
            estimated_flags.append(0)
            continue
        _, score, idx = best
        if score < NAME_FUZZ_THRESHOLD:
            ages.append(None)
            estimated_flags.append(0)
            continue

        class_year = roster[idx].get("year")
        if not isinstance(class_year, (int, float)) or class_year < 1 or class_year > 6:
            ages.append(None)
            estimated_flags.append(0)
            continue

        ages.append(18 + float(class_year))
        estimated_flags.append(1)

    prospects = prospects.copy()
    prospects["age_at_draft"] = ages
    prospects["age_estimated"] = estimated_flags
    return prospects


def check_combine_age_source():
    print("\nChecking combine files for an 'age' column...")
    for path in (COMBINE_HIST_CSV, COMBINE_2026_CSV):
        if not path.exists():
            print(f"  {path.name}: (missing)")
            continue
        cols = pd.read_csv(path, nrows=0).columns.tolist()
        has_age = "age" in {c.lower() for c in cols}
        print(f"  {path.name}: age column -> {has_age}")


def main():
    api_key = load_api_key()
    prospects = pd.read_csv(PROSPECTS_CSV)
    payload = load_or_fetch_rosters(prospects, api_key)

    merged = match_and_age(prospects, payload)
    merged.to_csv(PROSPECTS_CSV, index=False)
    print(f"\nSaved -> {PROSPECTS_CSV} ({merged.shape[1]} cols)")

    check_combine_age_source()

    matched = int(merged["age_estimated"].sum())
    total = len(merged)
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Prospects with estimated age: {matched}/{total} "
          f"({matched / total * 100:.1f}%)")
    if matched:
        ages = merged.loc[merged["age_estimated"] == 1, "age_at_draft"]
        print(f"Age range: {ages.min():.0f} - {ages.max():.0f}, "
              f"mean {ages.mean():.2f}")
        print("\nAge distribution (count per integer age):")
        for age, count in ages.value_counts().sort_index().items():
            print(f"  {age:>4.0f}: {count}")

    missing = total - matched
    print(f"\nStill missing age: {missing} ({missing / total * 100:.1f}%)")


if __name__ == "__main__":
    main()
