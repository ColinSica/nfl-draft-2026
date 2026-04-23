"""Sync team roster_needs to ESPN's official 2026 Draft cheat-sheet (4/23).

Source: https://www.espn.com/nfl/story/_/id/48503427/2026-nfl-draft-cheat-sheet

Our prior team needs were sourced from NFL.com / internal audits and in some
cases were stale post-FA. ESPN's cheat-sheet reflects the latest post-FA,
pre-draft team-need snapshot and should override.

Mapping (ESPN -> our buckets):
  OG -> IOL
  C  -> IOL
  DT -> IDL
  OT -> OT
  WR -> WR
  EDGE -> EDGE
  LB -> LB
  CB -> CB
  S  -> S
  QB -> QB
  RB -> RB
  TE -> TE

Tier assignment:
  Need 1 (primary)   -> 5.0
  Need 2 (secondary) -> 4.0
  Need 3 (tertiary)  -> 3.0
  Everything else    -> capped at 2.0 (keeps depth in the tier system but
                        ensures ESPN's top-3 dominate)
"""
from __future__ import annotations
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).parent
TA = ROOT / "data/features/team_agents_2026.json"
d = json.loads(TA.read_text(encoding="utf-8"))

# ESPN mapping (their label -> our bucket)
POS_MAP = {
    "OG": "IOL", "C": "IOL", "OL": "IOL",
    "DT": "IDL", "NT": "IDL",
    "OT": "OT", "WR": "WR", "EDGE": "EDGE", "LB": "LB",
    "CB": "CB", "S": "S", "QB": "QB", "RB": "RB", "TE": "TE",
}

# ESPN 2026 Draft Cheat-Sheet — verbatim from the article
# Format: team code -> (need1, need2, need3)
ESPN_NEEDS = {
    "ARI": ("QB", "OT", "EDGE"),
    "ATL": ("DT", "WR", "LB"),
    "BAL": ("CB", "S", "DT"),
    "BUF": ("WR", "EDGE", "LB"),
    "CAR": ("S", "WR", "EDGE"),
    "CHI": ("S", "DT", "EDGE"),
    "CIN": ("CB", "OT", "WR"),
    "CLE": ("QB", "WR", "OT"),
    "DAL": ("CB", "S", "LB"),
    "DEN": ("DT", "LB", "TE"),
    "DET": ("EDGE", "DT", "OT"),
    "GB":  ("CB", "OT", "EDGE"),
    "HOU": ("OG", "C", "DT"),
    "IND": ("EDGE", "WR", "LB"),
    "JAX": ("DT", "EDGE", "LB"),
    "KC":  ("WR", "EDGE", "DT"),
    "LV":  ("QB", "WR", "DT"),
    "LAC": ("OG", "DT", "EDGE"),
    "LAR": ("WR", "OT", "CB"),
    "MIA": ("WR", "CB", "EDGE"),
    "MIN": ("S", "C", "WR"),
    "NE":  ("OT", "DT", "TE"),
    "NO":  ("EDGE", "WR", "CB"),
    "NYG": ("WR", "OG", "CB"),
    "NYJ": ("QB", "WR", "EDGE"),
    "PHI": ("EDGE", "TE", "OT"),
    "PIT": ("QB", "OG", "OT"),
    "SF":  ("OT", "EDGE", "WR"),
    "SEA": ("RB", "EDGE", "CB"),
    "TB":  ("EDGE", "CB", "DT"),
    "TEN": ("EDGE", "WR", "OG"),
    "WAS": ("WR", "CB", "C"),
}

updated = []
for team, (n1, n2, n3) in ESPN_NEEDS.items():
    if team not in d or not isinstance(d[team], dict):
        continue

    mapped = (POS_MAP.get(n1, n1), POS_MAP.get(n2, n2), POS_MAP.get(n3, n3))
    new_needs = {mapped[0]: 5.0, mapped[1]: 4.0, mapped[2]: 3.0}

    # Dedupe if ESPN listed same mapped bucket twice (e.g. OG + C both -> IOL)
    # Take the highest tier assigned.
    final = {}
    for i, pos in enumerate(mapped):
        bucket = POS_MAP.get(pos, pos)
        tier = [5.0, 4.0, 3.0][i]
        if bucket not in final or tier > final[bucket]:
            final[bucket] = tier

    # Preserve existing needs below 2.0 (keeps depth for non-primary positions)
    existing = d[team].get("roster_needs", {}) or {}
    for pos, val in existing.items():
        v = float(val)
        if pos not in final:
            # Cap residual needs at 2.0 so ESPN top-3 dominate
            final[pos] = min(v, 2.0)

    d[team]["roster_needs"] = dict(sorted(final.items(), key=lambda kv: -kv[1]))
    d[team]["_4_23_espn_needs"] = f"ESPN cheat-sheet 4/23: {n1}/{n2}/{n3}"
    updated.append(team)
    print(f"  {team}: {n1}/{n2}/{n3} -> {final}")

# Meta
meta = d.get("_meta", {})
if not isinstance(meta, dict):
    meta = {}
meta["latest_intel_date"] = "2026-04-23"
meta.setdefault("analyst_intel_meta", {}).setdefault("sources", {}).setdefault(
    "2026-04-23", []
).append("ESPN 2026 Draft cheat-sheet — official team needs")
meta["needs_source"] = "espn_cheat_sheet_2026_04_23"
d["_meta"] = meta

TA.write_text(json.dumps(d, indent=2, ensure_ascii=False), encoding="utf-8")
print(f"\n[ESPN needs] synced {len(updated)} teams from ESPN 4/23 cheat-sheet")
