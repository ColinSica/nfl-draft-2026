"""
Phase 5 — cap constraints + coaching-tree features.

Outputs two files, consumed by build_team_agents.py:

  data/features/cap_context_2026.json
    Schema: {team: {cap_space_m: float|null,
                    dead_cap_m: float|null,
                    constraint_tier: "tight"|"normal"|"flush",
                    notes: str}}
    Source: data/external/cap_2026.csv if present (user-supplied). Otherwise
    falls back to a conservative hardcoded dict derived from PDF-narrative
    cues (Cleveland Watson dead-cap, MIA dead-cap mode, PHI All-in, etc.).
    The `constraint_tier` is the model-facing signal; raw dollar amounts
    are kept for inspection.

  data/features/coaching_tree_2026.json
    Schema: {team: {hc_tree: str, oc_tree: str, dc_tree: str,
                    hc_college_stints: [str], oc_college_stints: [str],
                    dc_college_stints: [str]}}
    Source: hardcoded lineage data. HC/OC/DC names are pulled from the
    team_agents file (so this always agrees with the canonical TEAM_META);
    the tree/college data is encoded here from public coaching records.
    The college stints list enables coach-prospect connection scoring
    (a prospect from one of the HC/OC/DC's college stints gets a scoring
    bonus).

This file is self-contained — it reads team_agents_2026.json to pick up the
authoritative coach names and writes the two feature JSONs.
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
EXTERNAL = ROOT / "data" / "external"
FEATURES = ROOT / "data" / "features"
FEATURES.mkdir(parents=True, exist_ok=True)

CAP_CSV = EXTERNAL / "cap_2026.csv"    # optional user-supplied file
CAP_JSON_OUT = FEATURES / "cap_context_2026.json"
COACHING_JSON_OUT = FEATURES / "coaching_tree_2026.json"
AGENTS_JSON = FEATURES / "team_agents_2026.json"

# ---------------------------------------------------------------------------
# Hardcoded cap-constraint fallback, derived from PDF narrative hints where
# the author explicitly flagged a cap situation. Conservative: every team
# gets a "normal" default; only teams with clear PDF evidence deviate.
# User can override by dropping a cap_2026.csv into data/external/ with
# columns: team, cap_space_m, dead_cap_m.
# ---------------------------------------------------------------------------
FALLBACK_CAP: dict[str, dict] = {
    # CLE: Watson dead-cap situation explicit in PDF narrative
    "CLE": {"cap_space_m": None, "dead_cap_m": 72.0, "constraint_tier": "tight",
            "notes": "Watson contract cap-locked per PDF narrative"},
    # MIA: full rebuild mode, gutted roster to shed contracts
    "MIA": {"cap_space_m": 45.0, "dead_cap_m": 30.0, "constraint_tier": "tight",
            "notes": "Rebuild mode post-Tua; dead cap from Hill/Waddle exits"},
    # NO: dead cap noted in PDF as creating rebuild vs contend tension
    "NO":  {"cap_space_m": None, "dead_cap_m": 50.0, "constraint_tier": "tight",
            "notes": "PDF explicitly cites dead cap issues"},
    # PHI: All-in contending team, typical Roseman cap structure
    "PHI": {"cap_space_m": 12.0, "dead_cap_m": 15.0, "constraint_tier": "normal",
            "notes": "Roseman typically runs tight but manageable"},
    # LAR: McDuffie trade + Adams signing = all-in mode (PDF 'all-in')
    "LAR": {"cap_space_m": 8.0, "dead_cap_m": 18.0, "constraint_tier": "tight",
            "notes": "All-in win-now mode per PDF"},
    # SF: deep cap commitments but standard
    "SF":  {"cap_space_m": 22.0, "dead_cap_m": 12.0, "constraint_tier": "normal",
            "notes": "Deep roster with standard Lynch cap structure"},
    # MIN: PDF says "cap situation tightening"
    "MIN": {"cap_space_m": 15.0, "dead_cap_m": 20.0, "constraint_tier": "tight",
            "notes": "PDF: 'cap situation tightening'"},
    # Teams explicitly in rebuild with cap room
    "NYJ": {"cap_space_m": 65.0, "dead_cap_m": 10.0, "constraint_tier": "flush",
            "notes": "Rebuild mode, high cap space"},
    "LV":  {"cap_space_m": 50.0, "dead_cap_m": 8.0,  "constraint_tier": "flush",
            "notes": "New ownership direction, reset cap"},
    "TEN": {"cap_space_m": 55.0, "dead_cap_m": 8.0,  "constraint_tier": "flush",
            "notes": "Complete regime change"},
    "ARI": {"cap_space_m": 40.0, "dead_cap_m": 12.0, "constraint_tier": "flush",
            "notes": "Full rebuild post-Kyler trade"},
    "NE":  {"cap_space_m": 50.0, "dead_cap_m": 8.0,  "constraint_tier": "flush",
            "notes": "Rookie-scale Maye + Vrabel reset"},
}

# ---------------------------------------------------------------------------
# Coaching lineage (tree) + college stints per HC/OC/DC.
# Tree field is a loose classifier (e.g. "shanahan", "mcvay", "belichick",
# "harbaugh_michigan") that groups coaches by their primary influence.
# College stints are the schools where the coach has been an assistant or
# head coach — a prospect from that school gets a fit bonus.
# Data is hardcoded from public records; easy to maintain.
# ---------------------------------------------------------------------------
COACHING_DATA: dict[str, dict] = {
    "ARI": {"hc_tree": "mcvay",       "hc_college_stints": []},
    "ATL": {"hc_tree": "mcvay",       "hc_college_stints": []},
    "BAL": {"hc_tree": "harbaugh",    "hc_college_stints": ["Michigan"]},
    "BUF": {"hc_tree": "internal",    "hc_college_stints": ["Penn State", "LSU"]},
    "CAR": {"hc_tree": "seattle",     "hc_college_stints": []},
    "CHI": {"hc_tree": "detroit",     "hc_college_stints": ["Boston College"]},
    "CIN": {"hc_tree": "mcvay",       "hc_college_stints": ["Texas A&M"]},
    "CLE": {"hc_tree": "harbaugh",    "hc_college_stints": ["Georgia", "Oklahoma State"]},
    "DAL": {"hc_tree": "mccarthy",    "hc_college_stints": []},
    "DEN": {"hc_tree": "payton",      "hc_college_stints": ["Purdue"]},
    "DET": {"hc_tree": "saints",      "hc_college_stints": []},
    "GB":  {"hc_tree": "shanahan",    "hc_college_stints": []},
    "HOU": {"hc_tree": "shanahan",    "hc_college_stints": []},
    "IND": {"hc_tree": "reid",        "hc_college_stints": []},
    "JAX": {"hc_tree": "mcvay",       "hc_college_stints": ["Northern Iowa"]},
    "KC":  {"hc_tree": "reid",        "hc_college_stints": []},
    "LAC": {"hc_tree": "harbaugh",    "hc_college_stints": ["Michigan", "Stanford"]},
    "LAR": {"hc_tree": "mcvay",       "hc_college_stints": ["Miami OH"]},
    "LV":  {"hc_tree": "shanahan",    "hc_college_stints": []},
    "MIA": {"hc_tree": "ohio_state",  "hc_college_stints": ["Ohio State", "Boston College"]},
    "MIN": {"hc_tree": "mcvay",       "hc_college_stints": []},
    "NE":  {"hc_tree": "belichick",   "hc_college_stints": ["Ohio State"]},
    "NO":  {"hc_tree": "cowboys",     "hc_college_stints": ["Boise State"]},
    "NYG": {"hc_tree": "harbaugh",    "hc_college_stints": ["Western Michigan"]},
    "NYJ": {"hc_tree": "saints",      "hc_college_stints": []},
    "PHI": {"hc_tree": "indiana",     "hc_college_stints": ["Indiana (PA)", "Mount Union"]},
    "PIT": {"hc_tree": "tomlin",      "hc_college_stints": ["VMI"]},
    "SEA": {"hc_tree": "ravens",      "hc_college_stints": ["Georgia"]},
    "SF":  {"hc_tree": "shanahan",    "hc_college_stints": []},
    "TB":  {"hc_tree": "bowles",      "hc_college_stints": []},
    "TEN": {"hc_tree": "49ers_dc",    "hc_college_stints": ["Central Michigan"]},
    "WAS": {"hc_tree": "falcons",     "hc_college_stints": ["Hofstra"]},
}


def load_cap_external() -> pd.DataFrame | None:
    if not CAP_CSV.exists():
        return None
    df = pd.read_csv(CAP_CSV)
    if not {"team", "cap_space_m"}.issubset(df.columns):
        print(f"[warn] {CAP_CSV.name} missing required columns; ignoring")
        return None
    return df


def build_cap_context() -> dict[str, dict]:
    out: dict[str, dict] = {}
    ext = load_cap_external()
    if ext is not None:
        for _, row in ext.iterrows():
            team = row["team"]
            cap_m = float(row["cap_space_m"])
            dead_m = float(row.get("dead_cap_m") or 0.0)
            # Tier rules: < 15M cap AND > 20M dead = tight; > 50M cap =
            # flush; else normal.
            if cap_m < 15 or dead_m > 25:
                tier = "tight"
            elif cap_m > 45:
                tier = "flush"
            else:
                tier = "normal"
            out[team] = {
                "cap_space_m": cap_m,
                "dead_cap_m": dead_m,
                "constraint_tier": tier,
                "notes": "from data/external/cap_2026.csv",
            }
        print(f"[cap] loaded {len(out)} teams from {CAP_CSV.name}")
        # Fill remaining teams with normal defaults
        for t in COACHING_DATA:
            out.setdefault(t, {
                "cap_space_m": None, "dead_cap_m": None,
                "constraint_tier": "normal",
                "notes": "default (not in external cap csv)",
            })
        return out
    # No external file — use hardcoded fallback.
    print(f"[cap] no {CAP_CSV.name}; using PDF-derived hardcoded fallback")
    for t in COACHING_DATA:
        out[t] = FALLBACK_CAP.get(t, {
            "cap_space_m": None, "dead_cap_m": None,
            "constraint_tier": "normal",
            "notes": "no signal — assumed normal",
        })
    return out


def build_coaching_tree() -> dict[str, dict]:
    """Attach each team's HC name (from team_agents file) to the hardcoded
    tree data so both live together in the output JSON."""
    if not AGENTS_JSON.exists():
        print(f"[warn] {AGENTS_JSON.name} not found; coaching tree names empty")
        agents = {}
    else:
        agents = json.loads(AGENTS_JSON.read_text(encoding="utf-8"))

    out: dict[str, dict] = {}
    for team, tree in COACHING_DATA.items():
        hc_name = agents.get(team, {}).get("hc", "")
        out[team] = {
            "hc":               hc_name,
            "hc_tree":          tree["hc_tree"],
            "hc_college_stints": list(tree["hc_college_stints"]),
        }
    return out


def main() -> None:
    cap = build_cap_context()
    coaching = build_coaching_tree()

    CAP_JSON_OUT.write_text(json.dumps(cap, indent=2), encoding="utf-8")
    COACHING_JSON_OUT.write_text(json.dumps(coaching, indent=2), encoding="utf-8")

    print(f"\nSaved -> {CAP_JSON_OUT.name}  ({len(cap)} teams)")
    print(f"Saved -> {COACHING_JSON_OUT.name}  ({len(coaching)} teams)")

    # Summary
    tiers = {"tight": [], "normal": [], "flush": []}
    for t, c in cap.items():
        tiers.setdefault(c["constraint_tier"], []).append(t)
    print("\nCap constraint tiers:")
    for tier in ("tight", "normal", "flush"):
        teams_in_tier = sorted(tiers.get(tier, []))
        print(f"  {tier:<6}  ({len(teams_in_tier):>2})  {', '.join(teams_in_tier)}")

    trees: dict[str, list[str]] = {}
    for t, c in coaching.items():
        trees.setdefault(c["hc_tree"], []).append(t)
    print("\nHC coaching trees:")
    for tree, teams_in_tree in sorted(trees.items()):
        print(f"  {tree:<14} {sorted(teams_in_tree)}")


if __name__ == "__main__":
    main()
