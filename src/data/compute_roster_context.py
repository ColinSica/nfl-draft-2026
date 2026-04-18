"""
Phase 4 — derive per-team roster context from existing repo data.

Produces two structured fields per team, merged into team_agents_2026.json
by build_team_agents.py:

  1. age_cliffs: list of {position, player, age_2026, severity}
     Source: data/raw/nflverse_roster_2025.csv + depth charts (rank=1 starters).
     A starter age >= 32 (OL) or >= 30 (skill positions) counts as a cliff;
     severity is derived from the age delta vs position-specific threshold.

  2. previous_year_allocation: dict {position_group: picks_in_2024_and_2025}
     Source: data/raw/historical_drafts_2011_2025.csv filtered to the team
     and years 2024-2025. Used to suppress back-to-back same-position R1
     picks (teams rarely hit the same position twice in consecutive firsts).

Outputs:
  data/features/roster_context_2026.json
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data" / "raw"
FEATURES = ROOT / "data" / "features"
FEATURES.mkdir(parents=True, exist_ok=True)

ROSTER_CSV = RAW / "nflverse_roster_2025.csv"
DEPTH_CSV = RAW / "nflverse_depth_charts_2025.csv"
DRAFT_CSV = RAW / "historical_drafts_2011_2025.csv"
OUT_JSON = FEATURES / "roster_context_2026.json"

# Age thresholds (2026 age) at which a starter becomes a "cliff" candidate.
# OL/TE/QB age later; skill positions decline earlier.
AGE_THRESHOLDS = {
    "OT": 32, "G": 32, "C": 32, "T": 32, "OL": 32,
    "QB": 35, "TE": 32,
    "WR": 30, "RB": 28,
    "EDGE": 31, "DE": 31, "DT": 31, "DL": 31, "NT": 31,
    "LB": 30, "ILB": 30, "OLB": 30, "MLB": 30,
    "CB": 30, "DB": 30, "S": 30, "FS": 30, "SS": 30,
}

# Position group canonicalization for previous-year draft allocation.
POS_GROUP = {
    "QB": "QB", "RB": "RB", "WR": "WR", "TE": "TE",
    "OT": "OT", "T": "OT",
    "G": "IOL", "OG": "IOL", "C": "IOL", "IOL": "IOL",
    "EDGE": "EDGE", "DE": "EDGE",
    "DT": "IDL", "DL": "IDL", "NT": "IDL",
    "LB": "LB", "ILB": "LB", "OLB": "LB",
    "CB": "CB", "DB": "CB",
    "S": "S", "FS": "S", "SS": "S",
}

# nflverse uses some 3-letter codes that differ from our standard set.
TEAM_ALIAS = {"LA": "LAR", "WSH": "WAS", "JAC": "JAX", "SD": "LAC",
               "STL": "LAR", "OAK": "LV", "NWE": "NE", "GNB": "GB",
               "NOR": "NO", "SFO": "SF", "TAM": "TB", "KAN": "KC",
               "HOU": "HOU"}


def compute_age_cliffs() -> dict[str, list[dict]]:
    roster = pd.read_csv(ROSTER_CSV)
    roster["birth_year"] = pd.to_datetime(roster["birth_date"], errors="coerce").dt.year
    roster["age_2026"] = 2026 - roster["birth_year"]

    # Filter to likely starters: ACT status + rank-1 depth-chart entries.
    depth = pd.read_csv(DEPTH_CSV)
    # Starters = pos_rank == 1 (first on the chart at that position slot).
    starters = depth[depth["pos_rank"] == 1][["team", "player_name", "pos_abb", "pos_name"]]
    starters["team"] = starters["team"].replace(TEAM_ALIAS)

    # Match roster by name+team (depth charts don't carry gsis_id reliably
    # across seasons, so name+team is our best key).
    roster_keyed = roster[["team", "full_name", "position", "age_2026", "status"]].copy()
    roster_keyed["team"] = roster_keyed["team"].replace(TEAM_ALIAS)

    merged = starters.merge(
        roster_keyed,
        left_on=["team", "player_name"],
        right_on=["team", "full_name"],
        how="left",
    ).dropna(subset=["age_2026"])

    # Specialists aren't R1 candidates — filter them out entirely.
    EXCLUDE_POS = {"K", "P", "LS"}

    # Dedupe by (team, player) — depth charts have multiple slot rows per
    # player across different scheme fronts (Base 4-3, Nickel, etc.).
    merged = (merged.drop_duplicates(subset=["team", "player_name"])
                    .reset_index(drop=True))

    out: dict[str, list[dict]] = {}
    for _, row in merged.iterrows():
        team = row["team"]
        pos = str(row["position"] or row["pos_abb"]).upper()
        if pos in EXCLUDE_POS:
            continue
        age = int(row["age_2026"])
        threshold = AGE_THRESHOLDS.get(pos, 31)
        if age < threshold:
            continue
        severity = "high" if age >= threshold + 3 else "medium"
        out.setdefault(team, []).append({
            "player":   row["player_name"],
            "position": pos,
            "age_2026": age,
            "threshold": threshold,
            "severity": severity,
        })
    # Sort each team's cliffs by severity then age descending.
    for team, lst in out.items():
        lst.sort(key=lambda r: (-r["age_2026"], r["position"]))
    return out


def compute_previous_year_allocation() -> dict[str, dict]:
    """Per team: {position_group: picks_in_{2024,2025}_r1_or_r2}.
    Used to penalize same-position R1 repeats."""
    drafts = pd.read_csv(DRAFT_CSV)
    recent = drafts[(drafts["year"].isin([2024, 2025]))
                    & (drafts["round"].isin([1, 2]))]
    recent = recent.copy()
    recent["team"] = recent["team"].replace(TEAM_ALIAS)
    recent["pos_group"] = recent["position"].map(
        lambda p: POS_GROUP.get(str(p).upper(), str(p).upper())
    )

    out: dict[str, dict] = {}
    for (team, year), sub in recent.groupby(["team", "year"]):
        bucket = out.setdefault(team, {
            "2024_r1": [], "2024_r2": [],
            "2025_r1": [], "2025_r2": [],
        })
        for _, row in sub.iterrows():
            key = f"{year}_r{row['round']}"
            bucket[key].append({
                "pos":    row["pos_group"],
                "player": row["player"],
                "pick":   int(row["pick"]),
            })
    return out


def main() -> None:
    age_cliffs = compute_age_cliffs()
    prev_alloc = compute_previous_year_allocation()

    all_teams = sorted(set(age_cliffs) | set(prev_alloc))
    out: dict[str, dict] = {}
    for t in all_teams:
        out[t] = {
            "age_cliffs": age_cliffs.get(t, []),
            "previous_year_allocation": prev_alloc.get(t, {}),
        }

    OUT_JSON.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"Saved -> {OUT_JSON}  ({len(out)} teams)")

    # Summary
    print("\nTop age cliffs per team (severity=high):")
    for t in sorted(out):
        high = [c for c in out[t]["age_cliffs"] if c["severity"] == "high"]
        if not high:
            continue
        names = [f"{c['player']} ({c['position']}/{c['age_2026']})" for c in high[:3]]
        print(f"  {t}: {', '.join(names)}")

    print("\n2024+2025 R1 position groups per team (sample):")
    for t in sorted(out)[:5]:
        alloc = out[t]["previous_year_allocation"]
        r1_2024 = [p["pos"] for p in alloc.get("2024_r1", [])]
        r1_2025 = [p["pos"] for p in alloc.get("2025_r1", [])]
        print(f"  {t}: 2024_R1={r1_2024}  2025_R1={r1_2025}")


if __name__ == "__main__":
    main()
