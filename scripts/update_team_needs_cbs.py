"""Update team_agents_2026.json roster_needs from CBS Sports 2026 cheat sheet.

Source: https://www.cbssports.com/nfl/draft/news/2026-nfl-draft-order-round-1-picks-team-needs/
Fetched: 2026-04-23

CBS lists needs in priority order. We map to our weight scheme:
  pos 1  -> 5.0 (primary need)
  pos 2  -> 4.0
  pos 3  -> 3.0
  pos 4-8 -> 2.0
  pos 9+ -> 1.2

Note: CBS article content from WebFetch only contains picks 1-16;
teams drafting 17-32 retain their prior needs_source value.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TEAM_JSON = ROOT / "data/features/team_agents_2026.json"

# Position bucket mapping: CBS vocabulary -> our schema buckets
POS_MAP = {
    "QB": "QB", "RB": "RB", "WR": "WR", "TE": "TE",
    "OT": "OT", "IOL": "IOL", "OL": "IOL", "C": "IOL", "G": "IOL",
    "EDGE": "EDGE",
    "DL": "IDL", "DT": "IDL", "IDL": "IDL", "NT": "IDL",
    "LB": "LB",
    "CB": "CB", "S": "S", "DB": "CB", "FS": "S", "SS": "S",
}

# CBS Sports 2026 cheat-sheet needs, all 32 teams + 6 no-R1 teams
# Parsed from user-supplied full article content 2026-04-23
CBS_NEEDS: dict[str, list[str]] = {
    "LV":  ["QB", "WR", "CB", "S", "DL", "IOL", "RB", "OT"],
    "NYJ": ["QB", "CB", "S", "LB", "IOL", "WR", "DL", "EDGE"],
    "ARI": ["QB", "OT", "IOL", "RB", "LB", "S", "DL"],
    "TEN": ["IOL", "LB", "EDGE", "CB", "S", "WR", "RB"],
    "NYG": ["DL", "CB", "IOL", "WR", "S", "RB", "LB"],
    "CLE": ["OT", "WR", "QB", "IOL", "CB", "TE", "RB", "S", "LB"],
    "WAS": ["RB", "WR", "IOL", "TE", "LB", "S", "CB", "EDGE"],
    "NO":  ["WR", "EDGE", "LB", "DL", "CB", "S", "TE"],
    "KC":  ["CB", "OT", "S", "DL", "RB", "EDGE", "WR", "TE"],
    "MIA": ["WR", "CB", "S", "TE", "IOL", "EDGE", "DL", "LB"],
    "DAL": ["CB", "S", "LB", "RB", "EDGE", "WR", "DL"],
    "LAR": ["OT", "WR", "DL", "LB", "CB", "S"],
    "BAL": ["DL", "IOL", "WR", "LB", "CB", "EDGE", "RB"],
    "TB":  ["IOL", "EDGE", "LB", "DL", "TE", "WR", "CB"],
    "DET": ["OT", "IOL", "EDGE", "DL", "LB", "CB"],
    "MIN": ["LB", "CB", "S", "DL", "WR", "QB", "EDGE", "TE"],
    "CAR": ["LB", "S", "DL", "CB", "WR", "RB", "IOL"],
    "PIT": ["QB", "S", "LB", "CB", "WR", "RB", "OT"],
    "LAC": ["IOL", "DL", "EDGE", "LB", "CB", "S", "WR"],
    "PHI": ["S", "EDGE", "TE", "CB", "WR", "IOL"],
    "CHI": ["DL", "S", "OT", "CB", "EDGE", "IOL", "WR"],
    "BUF": ["IOL", "EDGE", "S", "LB", "CB", "WR", "OT"],
    "SF":  ["EDGE", "DL", "WR", "IOL", "OT", "LB", "CB", "TE"],
    "HOU": ["OT", "IOL", "DL", "RB", "TE", "LB"],
    "NE":  ["IOL", "OT", "TE", "EDGE", "LB", "DL", "CB"],
    "SEA": ["CB", "IOL", "RB", "EDGE", "DL", "S", "LB"],
    # No-R1 teams (still have needs published by CBS)
    "ATL": ["EDGE", "WR", "CB", "LB", "DL", "RB"],
    "CIN": ["CB", "DL", "EDGE", "S", "LB", "IOL", "RB", "TE"],
    "DEN": ["TE", "LB", "DL", "IOL", "OT", "CB", "S"],
    "GB":  ["CB", "DL", "IOL", "OT", "LB", "EDGE"],
    "IND": ["LB", "DL", "EDGE", "S", "OT", "WR"],
    "JAX": ["CB", "S", "DL", "OT", "IOL", "LB", "EDGE"],
}

WEIGHTS = [5.0, 4.0, 3.0]  # positions 1-3
FILLER = 2.0               # positions 4-8
TAIL = 1.2                 # positions 9+


def build_needs(cbs_list: list[str]) -> dict[str, float]:
    """Convert a CBS priority list into our weighted roster_needs dict.
    Merges duplicates by taking the max weight assigned."""
    out: dict[str, float] = {}
    for i, raw in enumerate(cbs_list):
        bucket = POS_MAP.get(raw.upper().strip())
        if not bucket:
            continue
        if i < 3:
            w = WEIGHTS[i]
        elif i < 8:
            w = FILLER
        else:
            w = TAIL
        out[bucket] = max(out.get(bucket, 0.0), w)
    return out


def main() -> None:
    data = json.loads(TEAM_JSON.read_text(encoding="utf-8"))
    changed: list[str] = []
    for team, cbs in CBS_NEEDS.items():
        agent = data.get(team)
        if not agent:
            continue
        new_needs = build_needs(cbs)
        # Preserve any existing QB=0.0 flag if the CBS list omits QB
        # (some teams like TEN have qb_locked = True).
        if "QB" not in new_needs and agent.get("roster_needs", {}).get("QB") == 0.0:
            new_needs["QB"] = 0.0
        agent["roster_needs"] = new_needs
        agent["needs_source"] = "cbs_sports_2026_cheat_sheet_2026-04-23"
        changed.append(team)

    TEAM_JSON.write_text(json.dumps(data, indent=2), encoding="utf-8")
    print(f"Updated roster_needs for {len(changed)}/32 teams")
    print(f"Teams updated: {', '.join(changed)}")


if __name__ == "__main__":
    main()
