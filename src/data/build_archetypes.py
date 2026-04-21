"""Section F — archetype tagging for prospects and team preferences.

Prospect archetypes derived from position + measurables + production.
Team preferred archetypes derived from scheme family.

Outputs:
  data/features/prospect_archetypes_2026.json
  data/features/team_archetype_preferences_2026.json
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
PROS_PATH = ROOT / "data/processed/prospects_2026_enriched.csv"
AGENTS_PATH = ROOT / "data/features/team_agents_2026.json"
OUT_PROS = ROOT / "data/features/prospect_archetypes_2026.json"
OUT_TEAM = ROOT / "data/features/team_archetype_preferences_2026.json"


# ----- Prospect archetype classification ----------------------------------

def _tag_prospect(row) -> list[str]:
    pos = str(row.get("position", "")).upper()
    h = row.get("height", 0) or 0
    w = row.get("weight", 0) or 0
    s40 = row.get("40_yard") or 99
    ras = row.get("ras_score") or 0
    tags = []

    if pos == "WR":
        # X receiver: tall + long-arm + outside usage (proxy: weight ≥ 200)
        if h >= 74 and w >= 200:
            tags.append("X_receiver")
        # Vertical stretcher: fast + rec_ypr ≥ 15
        if s40 <= 4.45 and (row.get("rec_ypr") or 0) >= 15:
            tags.append("vertical_stretcher")
        # Slot separator: shorter + quick
        if h <= 72 and s40 <= 4.50:
            tags.append("slot_separator")
        if (row.get("rec_yds") or 0) >= 1200 and (row.get("rec_ypr") or 0) >= 12:
            tags.append("YAC_slot")
    elif pos == "RB":
        if w >= 220:
            tags.append("power_back")
        if s40 <= 4.45 and ras >= 8:
            tags.append("home_run_hitter")
        if (row.get("rec") or 0) >= 30:
            tags.append("pass_catching_back")
    elif pos == "TE":
        if w >= 255 and h >= 76:
            tags.append("inline_TE")
        if s40 <= 4.75 and w <= 250:
            tags.append("move_TE")
    elif pos in ("T", "OT"):
        if h >= 78 and (row.get("shuttle") or 99) <= 4.70:
            tags.append("movement_tackle")
        if w >= 320 and h >= 77:
            tags.append("power_tackle")
    elif pos in ("G", "C", "OG", "IOL"):
        tags.append("interior_OL")
        if ras >= 8:
            tags.append("athletic_interior")
    elif pos == "EDGE":
        if h >= 76 and w <= 260 and s40 <= 4.65:
            tags.append("standup_EDGE")
        if w >= 270 and h >= 75:
            tags.append("hand_in_dirt_EDGE")
        if (row.get("def_sacks") or 0) >= 10:
            tags.append("production_rusher")
        if ras >= 9:
            tags.append("athletic_rusher")
    elif pos in ("DT", "IDL", "NT", "DL"):
        if w >= 310:
            tags.append("run_stuffing_IDL")
        else:
            tags.append("penetrating_IDL")
    elif pos == "LB":
        if s40 <= 4.55 and (row.get("def_pd") or 0) >= 3:
            tags.append("coverage_LB")
        if w >= 230:
            tags.append("downhill_LB")
    elif pos == "CB":
        if h >= 72:
            tags.append("press_corner")
        else:
            tags.append("zone_corner")
        if s40 <= 4.40:
            tags.append("man_corner")
    elif pos == "S":
        if (row.get("def_int") or 0) >= 4:
            tags.append("ball_hawk_S")
        if w >= 210:
            tags.append("box_safety")
        else:
            tags.append("split_safety")
    elif pos == "QB":
        if (row.get("rush_yds") or 0) >= 400:
            tags.append("mobile_QB")
        else:
            tags.append("pocket_QB")
        if (row.get("pass_cmp_pct") or 0) >= 65:
            tags.append("accurate_QB")
    return tags


def _team_preferred_archetypes(agent: dict) -> dict[str, float]:
    """Map scheme / HC-tree to archetype preferences. Weight 0-1."""
    prefs: dict[str, float] = {}
    scheme = (agent.get("scheme", {}) or {}).get("type", "") or ""
    premium = (agent.get("scheme", {}) or {}).get("premium", [])

    s = scheme.lower()
    if "mcvay" in s or "shanahan" in s:
        prefs.update({
            "movement_tackle": 0.8, "YAC_slot": 0.7, "move_TE": 0.6,
            "pass_catching_back": 0.5, "zone_corner": 0.5,
            "split_safety": 0.5,
        })
    if "harbaugh" in s or "michigan" in s:
        prefs.update({
            "power_tackle": 0.9, "downhill_LB": 0.8,
            "run_stuffing_IDL": 0.7, "power_back": 0.7,
            "inline_TE": 0.6, "ball_hawk_S": 0.6,
        })
    if "saleh" in s or "wide-9" in s:
        prefs.update({
            "standup_EDGE": 0.9, "athletic_rusher": 0.8,
            "penetrating_IDL": 0.6, "zone_corner": 0.5,
        })
    if "mccarthy" in s or "west_coast" in s:
        prefs.update({
            "accurate_QB": 0.8, "YAC_slot": 0.7, "movement_tackle": 0.6,
        })
    if "schottenheimer" in s or "pro_style" in s:
        prefs.update({
            "X_receiver": 0.7, "power_tackle": 0.7,
            "hand_in_dirt_EDGE": 0.6,
        })
    if "fangio" in s:
        prefs.update({
            "split_safety": 0.8, "zone_corner": 0.7,
            "coverage_LB": 0.7,
        })
    if "belichick" in s:
        prefs.update({
            "press_corner": 0.8, "box_safety": 0.7,
        })

    # Carry scheme-premium positions into a position-level preference
    for pos in premium:
        prefs[f"position:{pos}"] = 0.5
    return prefs


def main():
    pros = pd.read_csv(PROS_PATH)
    agents = json.loads(AGENTS_PATH.read_text(encoding="utf-8"))

    prospect_tags = {}
    for _, row in pros.iterrows():
        tags = _tag_prospect(row)
        if tags:
            prospect_tags[str(row["player"])] = tags

    team_prefs = {}
    for team, agent in agents.items():
        if team.startswith("_"):
            continue
        team_prefs[team] = _team_preferred_archetypes(agent)

    OUT_PROS.write_text(
        json.dumps({"meta": {"n_tagged": len(prospect_tags)},
                    "archetypes": prospect_tags},
                   indent=2, ensure_ascii=False),
        encoding="utf-8")
    OUT_TEAM.write_text(
        json.dumps({"meta": {"n_teams": len(team_prefs)},
                    "preferences": team_prefs},
                   indent=2, ensure_ascii=False),
        encoding="utf-8")

    print(f"Wrote {OUT_PROS.name} — {len(prospect_tags)} prospects tagged")
    print(f"Wrote {OUT_TEAM.name} — {len(team_prefs)} teams")


if __name__ == "__main__":
    main()
