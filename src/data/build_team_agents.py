"""
Build data/features/team_agents_2026.json — the canonical per-team agent
profile consumed by the simulation.

Known data gaps (NOT auto-fixable, require external sources):
  - Cap situation per team — Spotrac scrape failed; none of the profiles
    carry 2026 cap-space numbers. Would affect model decisions around
    high-APY rookie-scale picks vs. vet signings.
  - visit_signals.cancelled_anywhere is a single team-agnostic list shared
    across all 32 teams — no per-team attribution available from source.
  - Visit volume is highly asymmetric (CIN 49 confirmed, LV 2). The PDF
    suggests down-weighting teams with < 8 confirmed visits.
  - NYG HC identity: PDF flagged John Harbaugh vs Jim Harbaugh ambiguity;
    agent currently says "John Harbaugh" per TEAM_META. Verify externally
    before using for coaching-tree inference.

Sources (priority order per user spec):
  1. Hardcoded FA moves + need_score values for the 16 teams the user
     called out explicitly. These override everything else.
  2. GM positional affinity: real computed deltas from
     data/processed/gm_positional_allocation.csv (computed earlier).
     New GMs (no tenure data) get the league-baseline (empty dict).
  3. Records + draft capital + bpa/need weights: from
     data/processed/team_context_2026_enriched.csv.
  4. Visit signals: from data/live/master_intel_latest.json, filtered
     to prospects in prospects_2026_enriched.csv.
  5. For the 16 teams NOT in the user's explicit list, roster_needs
     is derived from team_needs_2026.csv (top-3 positions by need_rank,
     assigned decreasing synthetic scores 3.5 / 2.5 / 1.5). These rows
     are flagged `needs_source: derived`.

Does NOT touch stage2_team_picks.py or run any simulations.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
PROC = ROOT / "data" / "processed"
LIVE = ROOT / "data" / "live"
FEATURES = ROOT / "data" / "features"
FEATURES.mkdir(parents=True, exist_ok=True)

TEAM_CTX = PROC / "team_context_2026_enriched.csv"
TEAM_NEEDS = PROC / "team_needs_2026.csv"
GM_ALLOC = PROC / "gm_positional_allocation.csv"
MASTER_INTEL = LIVE / "master_intel_latest.json"
PROSPECTS = PROC / "prospects_2026_enriched.csv"
NARRATIVE_JSON = FEATURES / "team_profiles_narrative_2026.json"
ROSTER_CTX_JSON = FEATURES / "roster_context_2026.json"
CAP_CTX_JSON = FEATURES / "cap_context_2026.json"
COACHING_JSON = FEATURES / "coaching_tree_2026.json"
ANALYST_AGG_JSON = FEATURES / "analyst_aggregate_2026.json"
ANALYST_CONSENSUS_JSON = FEATURES / "analyst_consensus_2026.json"
OUT_JSON = FEATURES / "team_agents_2026.json"

# ---------------------------------------------------------------------------
# Static metadata — GMs, HCs, new-hire flags, scheme descriptors.
# These don't come from our data pipeline so they live here.
# ---------------------------------------------------------------------------
TEAM_META: dict[str, dict] = {
    "ARI": {"gm": "Monti Ossenfort",     "hc": "Mike LaFleur",       "new_hc": True,  "new_gm": False},
    "ATL": {"gm": "Terry Fontenot",      "hc": "Raheem Morris",      "new_hc": False, "new_gm": False},
    "BAL": {"gm": "Eric DeCosta",        "hc": "Jesse Minter",       "new_hc": True,  "new_gm": False},
    "BUF": {"gm": "Brandon Beane",       "hc": "Joe Brady",          "new_hc": True,  "new_gm": False},
    "CAR": {"gm": "Dan Morgan",          "hc": "Dave Canales",       "new_hc": False, "new_gm": False},
    "CHI": {"gm": "Ryan Poles",          "hc": "Ben Johnson",        "new_hc": False, "new_gm": False},
    "CIN": {"gm": "Duke Tobin",          "hc": "Zac Taylor",         "new_hc": False, "new_gm": False},
    "CLE": {"gm": "Andrew Berry",        "hc": "Todd Monken",        "new_hc": True,  "new_gm": False},
    "DAL": {"gm": "Jerry Jones",         "hc": "Mike McCarthy",      "new_hc": False, "new_gm": False},
    "DEN": {"gm": "George Paton",        "hc": "Sean Payton",        "new_hc": False, "new_gm": False},
    "DET": {"gm": "Brad Holmes",         "hc": "Dan Campbell",       "new_hc": False, "new_gm": False},
    "GB":  {"gm": "Brian Gutekunst",     "hc": "Matt LaFleur (GB)",  "new_hc": False, "new_gm": False},
    "HOU": {"gm": "Nick Caserio",        "hc": "DeMeco Ryans",       "new_hc": False, "new_gm": False},
    "IND": {"gm": "Chris Ballard",       "hc": "Shane Steichen",     "new_hc": False, "new_gm": False},
    "JAX": {"gm": "James Gladstone",     "hc": "Liam Coen",          "new_hc": True,  "new_gm": True},
    "KC":  {"gm": "Brett Veach",         "hc": "Andy Reid",          "new_hc": False, "new_gm": False},
    "LAC": {"gm": "Joe Hortiz",          "hc": "Jim Harbaugh (LAC)", "new_hc": False, "new_gm": False},
    "LAR": {"gm": "Les Snead",           "hc": "Sean McVay",         "new_hc": False, "new_gm": False},
    "LV":  {"gm": "John Spytek",         "hc": "Klint Kubiak",       "new_hc": True,  "new_gm": True},
    "MIA": {"gm": "Jon-Eric Sullivan",   "hc": "Jeff Hafley",        "new_hc": True,  "new_gm": True},
    "MIN": {"gm": "Kwesi Adofo-Mensah",  "hc": "Kevin O'Connell",    "new_hc": False, "new_gm": False},
    "NE":  {"gm": "Eliot Wolf",          "hc": "Mike Vrabel",        "new_hc": False, "new_gm": False},
    "NO":  {"gm": "Mickey Loomis",       "hc": "Kellen Moore",       "new_hc": False, "new_gm": False},
    "NYG": {"gm": "Joe Schoen",          "hc": "John Harbaugh",      "new_hc": True,  "new_gm": False},
    "NYJ": {"gm": "Darren Mougey",       "hc": "Aaron Glenn",        "new_hc": False, "new_gm": True},
    "PHI": {"gm": "Howie Roseman",       "hc": "Nick Sirianni",      "new_hc": False, "new_gm": False},
    "PIT": {"gm": "Omar Khan",           "hc": "Mike Tomlin",        "new_hc": False, "new_gm": False},
    "SEA": {"gm": "John Schneider",      "hc": "Mike Macdonald",     "new_hc": False, "new_gm": False},
    "SF":  {"gm": "John Lynch",          "hc": "Kyle Shanahan",      "new_hc": False, "new_gm": False},
    "TB":  {"gm": "Jason Licht",         "hc": "Todd Bowles",        "new_hc": False, "new_gm": False},
    "TEN": {"gm": "Mike Borgonzi",       "hc": "Robert Saleh",       "new_hc": True,  "new_gm": True},
    "WAS": {"gm": "Adam Peters",         "hc": "Dan Quinn",          "new_hc": False, "new_gm": False},
}

# ---------------------------------------------------------------------------
# User-specified roster_needs + FA moves for 16 priority teams.
# ---------------------------------------------------------------------------
EXPLICIT_PROFILES: dict[str, dict] = {
    "LV": {
        "qb_situation": "bridge", "qb_urgency": 1.0,  # Kirk Cousins signed as bridge
        "roster_needs": {"QB": 5.0, "WR": 3.5, "OT": 3.0, "IDL": 2.5},
        "latent_needs": {},
        "fa_moves": {
            "arrivals": ["Kirk Cousins QB"],
            "departures": ["Davante Adams WR"],
        },
    },
    "NYJ": {
        "qb_situation": "bridge", "qb_urgency": 0.3,
        "roster_needs": {"EDGE": 4.5, "WR": 3.5, "CB": 2.5, "QB": 1.5, "S": 1.0},
        "latent_needs": {"QB": 2.0},
        "fa_moves": {
            "arrivals": ["Geno Smith QB", "Minkah Fitzpatrick S",
                         "Demario Davis LB", "T'Vondre Sweat IDL",
                         "Joseph Ossai EDGE", "Kingsley Enagbare EDGE"],
            "departures": ["Sauce Gardner CB", "Quinnen Williams IDL",
                           "Justin Fields QB"],
        },
    },
    "ARI": {
        "qb_situation": "rebuilding", "qb_urgency": 0.8,
        "roster_needs": {"QB": 4.0, "OT": 3.5, "EDGE": 3.0, "CB": 2.0, "WR": 1.5},
        "latent_needs": {},
        "fa_moves": {
            "arrivals": [], "departures": ["Kyler Murray QB"],
        },
    },
    "TEN": {
        "qb_situation": "locked", "qb_urgency": 0.0,
        "roster_needs": {"OT": 3.5, "EDGE": 3.0, "WR": 3.0, "RB": 2.5, "CB": 1.5},
        "latent_needs": {},
        "fa_moves": {"arrivals": [], "departures": []},
    },
    "NYG": {
        "qb_situation": "locked", "qb_urgency": 0.0,
        "roster_needs": {"WR": 3.5, "OT": 3.0, "S": 2.5, "CB": 2.5, "LB": 1.5},
        "latent_needs": {},
        "fa_moves": {
            "arrivals": [],
            "departures": ["Dexter Lawrence IDL (trade impasse)"],
        },
    },
    "CLE": {
        "qb_situation": "unknown", "qb_urgency": 0.0,  # Watson cap-locked blocks R1 QB
        "roster_needs": {"WR": 4.0, "QB": 3.5, "OT": 2.0, "EDGE": 1.5, "LB": 1.0},
        "latent_needs": {"QB": 2.0},
        "fa_moves": {
            "arrivals": ["Morgan Moses OT (re-signed)", "Dawand Jones OT",
                         "Teven Jenkins G"],
            "departures": [],
        },
    },
    "DAL": {
        "qb_situation": "locked", "qb_urgency": 0.0,
        "roster_needs": {"EDGE": 4.5, "CB": 3.5, "LB": 3.0, "S": 2.0, "OT": 1.5},
        "latent_needs": {},
        "fa_moves": {"arrivals": [], "departures": []},
    },
    "NO": {
        "qb_situation": "bridge", "qb_urgency": 0.7,
        "roster_needs": {"WR": 4.0, "EDGE": 3.5, "CB": 3.0, "OT": 2.0},
        "latent_needs": {},
        "fa_moves": {
            "arrivals": ["Travis Etienne RB"],
            "departures": ["Rashid Shaheed WR (traded)"],
        },
    },
    "KC": {
        "qb_situation": "locked", "qb_urgency": 0.0,
        "roster_needs": {"CB": 5.0, "WR": 3.5, "EDGE": 2.5, "OT": 1.5},
        "latent_needs": {},
        "fa_moves": {
            "arrivals": [],
            "departures": ["Trent McDuffie CB (traded)", "Jaylen Watson CB"],
        },
    },
    "CIN": {
        "qb_situation": "locked", "qb_urgency": 0.0,
        "roster_needs": {"CB": 4.5, "S": 3.0, "EDGE": 2.0, "LB": 1.5},
        "latent_needs": {},
        "fa_moves": {
            "arrivals": ["DeMarcus Walker EDGE"],
            "departures": ["Trey Hendrickson EDGE", "Cam Taylor-Britt CB",
                           "Joseph Ossai EDGE"],
        },
    },
    "MIA": {
        "qb_situation": "rebuilding", "qb_urgency": 0.8,
        "roster_needs": {"WR": 5.0, "CB": 4.0, "S": 3.0, "EDGE": 2.5, "QB": 2.0},
        "latent_needs": {"QB": 2.0},
        "fa_moves": {
            "arrivals": [],
            "departures": ["Tua Tagovailoa QB", "Jaylen Waddle WR",
                           "Tyreek Hill WR", "Jevon Holland S"],
        },
    },
    "LAR": {
        "qb_situation": "bridge", "qb_urgency": 0.3,
        "roster_needs": {"WR": 3.5, "OT": 2.5, "CB": 2.0},
        "latent_needs": {"QB": 2.0},
        "fa_moves": {"arrivals": [], "departures": []},  # Adams final year
    },
    "BAL": {
        "qb_situation": "locked", "qb_urgency": 0.0,
        "roster_needs": {"OT": 3.5, "WR": 3.0, "EDGE": 2.5, "IDL": 2.0},
        "latent_needs": {},
        "fa_moves": {
            "arrivals": ["Trey Hendrickson EDGE"],
            "departures": ["Tyler Linderbaum C (lost to LV)"],
        },
    },
    "DET": {
        "qb_situation": "locked", "qb_urgency": 0.0,
        "roster_needs": {"OT": 4.5, "EDGE": 3.5, "S": 2.5, "CB": 2.0},
        "latent_needs": {},
        "fa_moves": {
            "arrivals": ["Matt Borom OT (stop-gap)"],
            "departures": ["Taylor Decker OT"],
        },
    },
    "PHI": {
        "qb_situation": "locked", "qb_urgency": 0.0,
        "roster_needs": {"EDGE": 3.5, "OT": 3.0, "S": 2.5, "LB": 2.0, "WR": 1.5},
        "latent_needs": {"OT": 1.5, "WR": 1.5},  # Lane Johnson aging, AJ Brown uncertainty
        "fa_moves": {"arrivals": [], "departures": []},
    },
    "CHI": {
        "qb_situation": "locked", "qb_urgency": 0.0,
        "roster_needs": {"EDGE": 5.0, "S": 4.0, "OT": 3.0, "IDL": 1.5},
        "latent_needs": {},
        "fa_moves": {
            "arrivals": [],
            "departures": ["Dayo Odeyingbo EDGE (torn Achilles)"],
        },
    },
    # ---- Best-effort needs for the remaining 16 teams --------------------
    # These are researched not verified by the user. Marked
    # `needs_source: researched_default` so they're distinguishable.
    "ATL": {
        "qb_situation": "locked", "qb_urgency": 0.0,
        "roster_needs": {"EDGE": 4.0, "CB": 3.0, "OT": 2.5, "IDL": 1.5},
        "latent_needs": {"QB": 1.5},   # Cousins aging
        "fa_moves": {"arrivals": [], "departures": []},
    },
    "BUF": {
        "qb_situation": "locked", "qb_urgency": 0.0,
        "roster_needs": {"EDGE": 4.0, "CB": 3.0, "WR": 2.5, "IDL": 1.5},
        "latent_needs": {},
        "fa_moves": {"arrivals": [], "departures": []},
    },
    "CAR": {
        "qb_situation": "unknown", "qb_urgency": 0.4,
        "roster_needs": {"OT": 3.5, "WR": 3.0, "CB": 2.5, "IDL": 2.0},
        "latent_needs": {"QB": 1.5},   # Young unsettled
        "fa_moves": {"arrivals": [], "departures": []},
    },
    "DEN": {
        "qb_situation": "locked", "qb_urgency": 0.0,
        "roster_needs": {"WR": 3.0, "CB": 3.0, "EDGE": 2.5, "S": 2.0},
        "latent_needs": {},
        "fa_moves": {"arrivals": [], "departures": []},
    },
    "GB": {
        "qb_situation": "locked", "qb_urgency": 0.0,
        "roster_needs": {"CB": 3.5, "S": 2.5, "IDL": 2.0, "OT": 1.5},
        "latent_needs": {},
        "fa_moves": {"arrivals": [], "departures": []},
    },
    "HOU": {
        "qb_situation": "locked", "qb_urgency": 0.0,
        "roster_needs": {"IDL": 3.5, "OT": 3.0, "CB": 2.5, "LB": 1.5},
        "latent_needs": {},
        "fa_moves": {"arrivals": [], "departures": []},
    },
    "IND": {
        "qb_situation": "unknown", "qb_urgency": 0.4,
        "roster_needs": {"OT": 2.5, "CB": 2.0, "EDGE": 2.0, "WR": 1.5},
        "latent_needs": {"QB": 2.0},   # Richardson
        "fa_moves": {"arrivals": [], "departures": []},
    },
    "JAX": {
        "qb_situation": "locked", "qb_urgency": 0.0,
        "roster_needs": {"OL": 3.5, "WR": 3.0, "IDL": 2.5, "CB": 1.5},
        "latent_needs": {},
        "fa_moves": {"arrivals": [], "departures": []},
    },
    "LAC": {
        "qb_situation": "locked", "qb_urgency": 0.0,
        "roster_needs": {"IDL": 4.0, "EDGE": 3.0, "CB": 2.5, "IOL": 1.5},
        "latent_needs": {},
        "fa_moves": {"arrivals": [], "departures": []},
    },
    "MIN": {
        "qb_situation": "locked", "qb_urgency": 0.0,
        "roster_needs": {"S": 3.5, "IDL": 3.0, "EDGE": 2.5, "CB": 2.0},
        "latent_needs": {"S": 2.0},   # Harrison Smith succession
        "fa_moves": {"arrivals": [], "departures": []},
    },
    "NE": {
        "qb_situation": "locked", "qb_urgency": 0.0,
        "roster_needs": {"OT": 4.0, "WR": 3.5, "EDGE": 3.0, "CB": 2.0, "TE": 1.5},
        "latent_needs": {"TE": 1.5},   # Henry final year
        "fa_moves": {"arrivals": [], "departures": []},
    },
    "PIT": {
        "qb_situation": "bridge", "qb_urgency": 0.65,
        "roster_needs": {"OL": 4.0, "WR": 3.0, "IOL": 2.5, "S": 1.5, "QB": 1.5},
        "latent_needs": {"QB": 2.0},   # Howard internal candidate
        "fa_moves": {"arrivals": [], "departures": []},
    },
    "SEA": {
        "qb_situation": "locked", "qb_urgency": 0.0,
        "roster_needs": {"RB": 4.0, "CB": 3.0, "EDGE": 2.5, "OL": 1.5},
        "latent_needs": {},
        "fa_moves": {
            "arrivals": [],
            "departures": ["Kenneth Walker III RB", "Tariq Woolen CB"],
        },
    },
    "SF": {
        "qb_situation": "locked", "qb_urgency": 0.0,
        "roster_needs": {"OT": 4.0, "EDGE": 3.5, "CB": 2.5, "IDL": 2.0},
        "latent_needs": {"OT": 4.0},   # Williams 38
        "fa_moves": {"arrivals": [], "departures": []},
    },
    "TB": {
        "qb_situation": "locked", "qb_urgency": 0.0,
        "roster_needs": {"EDGE": 3.5, "WR": 3.0, "CB": 2.5, "S": 1.5},
        "latent_needs": {"WR": 1.5},   # Evans aging
        "fa_moves": {"arrivals": [], "departures": []},
    },
    "WAS": {
        "qb_situation": "locked", "qb_urgency": 0.0,
        "roster_needs": {"WR": 3.5, "LB": 2.5, "S": 2.0, "EDGE": 2.0},
        "latent_needs": {},
        "fa_moves": {"arrivals": [], "departures": []},
    },
}

# ---------------------------------------------------------------------------
# Trade-behavior exceptions (hardcode from NFL IQ research).
# Other teams get league-average rates.
# ---------------------------------------------------------------------------
TRADE_OVERRIDES: dict[str, dict] = {
    "NO":  {"trade_up_rate": 0.95, "trade_down_rate": 0.00},
    "LAR": {"trade_up_rate": 0.11, "trade_down_rate": 0.89},
    "IND": {"trade_up_rate": 0.25, "trade_down_rate": 0.75},
    "SEA": {"trade_up_rate": 0.35, "trade_down_rate": 0.65},
    "PHI": {"trade_up_rate": 0.45, "trade_down_rate": 0.40},
    "CIN": {"trade_up_rate": 0.05, "trade_down_rate": 0.05},
    "LAC": {"trade_up_rate": 0.10, "trade_down_rate": 0.10},
    "KC":  {"trade_up_rate": 0.75, "trade_down_rate": 0.40},
    "DAL": {"trade_up_rate": 0.65, "trade_down_rate": 0.20},
    "MIA": {"trade_up_rate": 0.25, "trade_down_rate": 0.50},
}

NICKNAME_TO_ABBR = {
    "49ers": "SF", "Bears": "CHI", "Bengals": "CIN", "Bills": "BUF",
    "Broncos": "DEN", "Browns": "CLE", "Buccaneers": "TB", "Cardinals": "ARI",
    "Chargers": "LAC", "Chiefs": "KC", "Colts": "IND", "Commanders": "WAS",
    "Cowboys": "DAL", "Dolphins": "MIA", "Eagles": "PHI", "Falcons": "ATL",
    "Giants": "NYG", "Jaguars": "JAX", "Jets": "NYJ", "Lions": "DET",
    "Packers": "GB", "Panthers": "CAR", "Patriots": "NE", "Raiders": "LV",
    "Rams": "LAR", "Ravens": "BAL", "Saints": "NO", "Seahawks": "SEA",
    "Steelers": "PIT", "Texans": "HOU", "Titans": "TEN", "Vikings": "MIN",
}


def load_gm_affinity(team: str) -> dict:
    """Returns {position_group: delta} from computed allocation table."""
    if not GM_ALLOC.exists():
        return {}
    df = pd.read_csv(GM_ALLOC)
    sub = df[df["team"] == team]
    if sub.empty:
        return {}
    return {r["position_group"]: round(float(r["delta"]), 4)
            for _, r in sub.iterrows()}


def load_visits(prospects_df: pd.DataFrame) -> dict[str, list[str]]:
    """Returns {team_abbr: [player_name, ...]} from master_intel_latest.json."""
    out: dict[str, list[str]] = {}
    if not MASTER_INTEL.exists():
        return out
    master = json.loads(MASTER_INTEL.read_text(encoding="utf-8"))
    players = master.get("players", {})
    for player, info in players.items():
        visits = info.get("teams_visited") or []
        for team in visits:
            abbr = NICKNAME_TO_ABBR.get(team, team if len(team) <= 3 else None)
            if abbr:
                out.setdefault(abbr, []).append(player)
    return out


def load_cancelled_visits() -> dict[str, list[str]]:
    """Best-effort cancellation tracker from master_intel (team-agnostic flag)."""
    if not MASTER_INTEL.exists():
        return {}
    master = json.loads(MASTER_INTEL.read_text(encoding="utf-8"))
    out: dict[str, list[str]] = {"any": []}
    for player, info in master.get("players", {}).items():
        if info.get("cancelled_visit_flag"):
            out["any"].append(player)
    return out


def derive_needs_from_team_needs(team: str) -> dict[str, float]:
    """Fallback when the team isn't in EXPLICIT_PROFILES.
    Uses the top-3 positions from team_needs_2026.csv with scores 3.5 / 2.5 / 1.5."""
    if not TEAM_NEEDS.exists():
        return {}
    df = pd.read_csv(TEAM_NEEDS)
    sub = df[df["team"] == team].sort_values("need_rank").head(3)
    scores = [3.5, 2.5, 1.5]
    return {row["position"]: scores[i]
            for i, (_, row) in enumerate(sub.iterrows()) if i < len(scores)}


def classify_win_now(win_pct: float) -> tuple[float, float, float]:
    """Returns (win_now_pressure, bpa_weight, need_weight)."""
    if pd.isna(win_pct):
        return (0.5, 0.5, 0.5)
    if win_pct < 0.375:
        return (0.2, 0.7, 0.3)
    if win_pct < 0.562:
        return (0.5, 0.5, 0.5)
    return (0.9, 0.3, 0.7)


def _analyst_for_team(team: str, r1_picks: list[int],
                       per_pick: dict, reasoning: dict) -> dict:
    """Collect analyst-consensus data for each of a team's R1 picks.
    Returns {pick_num: {consensus_all, consensus_tier1, picks_all (top-5),
    picks_tier1 (top-5), reasoning: [{analyst, text}]}}."""
    out: dict = {}
    for pick_num in r1_picks:
        info = per_pick.get(str(pick_num), {})
        if not info:
            continue
        # Keep top-5 entries per bucket for compactness.
        top_all = sorted(info.get("picks_all", {}).items(),
                         key=lambda kv: -kv[1])[:5]
        top_t1 = sorted(info.get("picks_tier1", {}).items(),
                        key=lambda kv: -kv[1])[:5]
        out[str(pick_num)] = {
            "team":             info.get("team"),
            "consensus_all":    info.get("consensus_player"),
            "consensus_tier1":  info.get("consensus_tier1"),
            "picks_all_top5":   top_all,
            "picks_tier1_top5": top_t1,
            "trade_noted":      info.get("trade_noted", False),
            "reasoning":        reasoning.get(str(pick_num), [])[:8],
        }
    return out


def _first_name_token(entry: str) -> str:
    """Normalize a player descriptor ('Dayo Odeyingbo EDGE (torn Achilles)')
    to its lowercased first-name token for dedup purposes. Crude, but stable
    enough to avoid duplicating the same player across EXPLICIT + PDF."""
    if not entry:
        return ""
    return entry.strip().split()[0].lower()


def load_narrative() -> dict:
    """Load the PDF-derived team profile narrative (team_profiles_narrative_2026.json).
    Returns an empty dict if the file is missing (pipeline stays runnable)."""
    if not NARRATIVE_JSON.exists():
        print(f"[warn] {NARRATIVE_JSON.name} not found; narratives will be empty. "
              f"Run: python src/data/parse_team_profiles_pdf.py")
        return {}
    return json.loads(NARRATIVE_JSON.read_text(encoding="utf-8"))


def load_roster_context() -> dict:
    """Load roster_context_2026.json (age cliffs + previous-year allocation).
    Returns empty dict if missing; run compute_roster_context.py first."""
    if not ROSTER_CTX_JSON.exists():
        print(f"[warn] {ROSTER_CTX_JSON.name} not found; roster context empty. "
              f"Run: python src/data/compute_roster_context.py")
        return {}
    return json.loads(ROSTER_CTX_JSON.read_text(encoding="utf-8"))


def load_cap_context() -> dict:
    if not CAP_CTX_JSON.exists():
        print(f"[warn] {CAP_CTX_JSON.name} not found; cap context empty. "
              f"Run: python src/data/build_cap_and_coaching.py")
        return {}
    return json.loads(CAP_CTX_JSON.read_text(encoding="utf-8"))


def load_coaching_tree() -> dict:
    if not COACHING_JSON.exists():
        print(f"[warn] {COACHING_JSON.name} not found; coaching tree empty. "
              f"Run: python src/data/build_cap_and_coaching.py")
        return {}
    return json.loads(COACHING_JSON.read_text(encoding="utf-8"))


def load_analyst_consensus() -> dict:
    if not ANALYST_CONSENSUS_JSON.exists():
        print(f"[warn] {ANALYST_CONSENSUS_JSON.name} not found. "
              f"Run: python src/data/ingest_analyst_mocks.py")
        return {}
    return json.loads(ANALYST_CONSENSUS_JSON.read_text(encoding="utf-8"))


def build() -> dict:
    team_ctx = pd.read_csv(TEAM_CTX)
    prospects = pd.read_csv(PROSPECTS)
    visits_by_team = load_visits(prospects)
    cancelled_any = load_cancelled_visits().get("any", [])
    narrative = load_narrative()
    roster_ctx = load_roster_context()
    cap_ctx = load_cap_context()
    coaching = load_coaching_tree()
    analyst_consensus = load_analyst_consensus()
    analyst_per_pick = analyst_consensus.get("per_pick", {})
    analyst_reasoning = analyst_consensus.get("reasoning", {})

    # Draft capital per team (count of picks across all rounds)
    pick_counts = team_ctx.groupby("team").size().to_dict()
    r1_counts = (team_ctx[team_ctx["round"] == 1].groupby("team").size()
                 .to_dict())

    # Records & weights — read from team_ctx (one row per pick; take first)
    first_row_per_team = team_ctx.drop_duplicates(subset=["team"])

    profiles: dict[str, dict] = {}
    for team in sorted(TEAM_META.keys()):
        meta = TEAM_META[team]
        row = first_row_per_team[first_row_per_team["team"] == team]
        if row.empty:
            continue
        row = row.iloc[0]

        win_pct = float(row.get("win_pct") or 0.5)
        win_now, bpa_w, need_w = classify_win_now(win_pct)

        USER_PRIORITY = {"LV", "NYJ", "ARI", "TEN", "NYG", "CLE", "DAL",
                         "NO", "KC", "CIN", "MIA", "LAR", "BAL", "DET",
                         "PHI", "CHI"}
        explicit = EXPLICIT_PROFILES.get(team, {})
        roster_needs = explicit.get("roster_needs") \
            or derive_needs_from_team_needs(team)
        if team in USER_PRIORITY:
            needs_source = "explicit_user_spec"
        elif team in EXPLICIT_PROFILES:
            needs_source = "researched_default"
        else:
            needs_source = "derived_from_team_needs"

        # Trade behaviour
        trade_override = TRADE_OVERRIDES.get(team)
        if trade_override:
            trade_up = trade_override["trade_up_rate"]
            trade_down = trade_override["trade_down_rate"]
        elif meta["new_gm"]:
            trade_up, trade_down = 0.35, 0.30   # league mean for new GMs
        else:
            trade_up = float(row.get("trade_up_rate") or 0.35)
            trade_down = float(row.get("trade_down_rate") or 0.30)

        # R1 pick numbers
        r1_picks = sorted(
            team_ctx[(team_ctx["team"] == team) & (team_ctx["round"] == 1)]
            ["pick_number"].tolist()
        )

        # Visit list
        visits = sorted(set(visits_by_team.get(team, [])))

        # Scheme hints
        scheme_hints = {
            "ARI": {"type": "McVay tree (LaFleur)", "premium": ["WR", "OT", "RB"]},
            "NYG": {"type": "Michigan / Harbaugh (physical)",
                    "premium": ["OL", "LB", "EDGE"]},
            "BAL": {"type": "defensive multiple (Minter)",
                    "premium": ["EDGE", "IDL", "CB"]},
            "CLE": {"type": "Monken offense",
                    "premium": ["WR", "TE", "OT"]},
            "LV":  {"type": "Shanahan zone (Kubiak)",
                    "premium": ["OT", "WR", "TE"]},
            "BUF": {"type": "Brady offense",
                    "premium": ["WR", "OT"]},
            "MIA": {"type": "Hafley defense",
                    "premium": ["CB", "S", "EDGE"]},
            "NYJ": {"type": "3-4 multiple (Glenn)",
                    "premium": ["EDGE", "LB"]},
            "TEN": {"type": "Saleh 4-3 defense",
                    "premium": ["EDGE", "CB", "S"]},
            "PIT": {"type": "McCarthy offense (new HC)",
                    "premium": ["OL", "WR"]},
            "JAX": {"type": "Coen offense", "premium": ["WR", "OT"]},
        }

        # --- PDF-derived structured data -----------------------------------
        # For every team, pull the PDF narrative's structured sub-fields and
        # use them to BACKFILL (never overwrite) hardcoded values. Priority:
        # hardcoded > PDF structured > empty.
        n_team = narrative.get(team, {}) if narrative else {}
        pdf_scheme = n_team.get("scheme_struct", {})
        pdf_fa = n_team.get("fa_moves_struct", {})
        pdf_latent = n_team.get("latent_needs_struct", {})
        pdf_pred_enum = n_team.get("predictability_enum", "")
        pdf_trade_prob = n_team.get("trade_probability", {})

        # scheme: prefer the hardcoded hint when available (richer label);
        # otherwise fall back to PDF-derived.
        scheme = scheme_hints.get(team) or {
            "type": pdf_scheme.get("type", "default"),
            "premium": pdf_scheme.get("premium", []),
        }
        # Always backfill `premium` if the hardcoded hint has none.
        if not scheme.get("premium") and pdf_scheme.get("premium"):
            scheme = {**scheme, "premium": pdf_scheme["premium"]}

        # fa_moves: union PDF with EXPLICIT_PROFILES. PDF is the richer
        # source (full narrative moves); the explicit dict adds any
        # hand-curated entries that aren't already covered. An EXPLICIT entry
        # with empty lists (the "researched_default" stub) contributes
        # nothing and lets the PDF through.
        explicit_fa = explicit.get("fa_moves") or {}

        def _merge_moves(pdf_list: list[str], explicit_list: list[str]) -> list[str]:
            out = list(pdf_list or [])
            seen_names = {_first_name_token(e) for e in out}
            for e in (explicit_list or []):
                if _first_name_token(e) not in seen_names:
                    out.append(e)
                    seen_names.add(_first_name_token(e))
            return out

        fa_moves = {
            "arrivals":   _merge_moves(pdf_fa.get("arrivals", []),
                                       explicit_fa.get("arrivals", [])),
            "departures": _merge_moves(pdf_fa.get("departures", []),
                                       explicit_fa.get("departures", [])),
        }

        # latent_needs: union of EXPLICIT_PROFILES + PDF-derived.
        latent = dict(explicit.get("latent_needs") or {})
        for pos, score in (pdf_latent or {}).items():
            latent.setdefault(pos, score)

        profile = {
            "team": team,
            "pick": r1_picks[0] if r1_picks else None,
            "second_pick": r1_picks[1] if len(r1_picks) > 1 else None,
            "all_r1_picks": r1_picks,
            "total_picks": int(pick_counts.get(team, 0)),
            "r1_count": int(r1_counts.get(team, 0)),
            "gm": meta["gm"],
            "hc": meta["hc"],
            "new_hc": meta["new_hc"],
            "new_gm": meta["new_gm"],

            "win_pct": round(win_pct, 3),
            "win_now_pressure": win_now,
            "bpa_weight": bpa_w,
            "need_weight": need_w,

            "qb_situation": explicit.get("qb_situation", "locked"),
            "qb_urgency": float(explicit.get("qb_urgency", row.get("qb_urgency") or 0.0)),

            "roster_needs": roster_needs,
            "latent_needs": latent,
            "needs_source": needs_source,

            "fa_moves": fa_moves,

            "gm_affinity": load_gm_affinity(team),

            "trade_behavior": {
                "trade_up_rate": round(trade_up, 3),
                "trade_down_rate": round(trade_down, 3),
                # PDF-derived qualitative tiers (where the narrative is
                # explicit about trade-up/down probability). Empty dict when
                # the PDF didn't speak to it.
                "pdf_tier": pdf_trade_prob,
            },

            "visit_signals": {
                "confirmed_visits": visits,
                "n_confirmed": len(visits),
                "cancelled_anywhere": cancelled_any,  # team-attribution unavailable
            },

            "scheme": scheme,

            # PDF-derived predictability tier (HIGH / MEDIUM-HIGH / MEDIUM /
            # LOW-MEDIUM / LOW). Suitable for use as a confidence weight on
            # the model's output distribution for this team's pick.
            "predictability": pdf_pred_enum or "",

            "draft_capital": {
                "r1_count": int(r1_counts.get(team, 0)),
                "total_picks": int(pick_counts.get(team, 0)),
                "capital_abundance":
                    "very_high" if pick_counts.get(team, 0) >= 10
                    else "high" if pick_counts.get(team, 0) >= 8
                    else "medium" if pick_counts.get(team, 0) >= 6
                    else "low",
            },

            # Full PDF-derived narrative (leadership detail, 2025 context,
            # scheme identity, tiered roster needs, player archetypes at each
            # R1 pick, GM behavioral fingerprint, uncertainty flags,
            # predictability tier, etc.). Empty dict if the narrative file
            # hasn't been generated yet.
            "narrative": narrative.get(team, {}),

            # Phase 4: roster context — age cliffs (starters 30+/32+ by
            # position) and previous-year draft allocation.
            "roster_context": roster_ctx.get(team, {
                "age_cliffs": [], "previous_year_allocation": {}
            }),

            # Phase 5: cap constraint tier + coaching tree (for coach-
            # prospect connection bonuses). cap_context is PDF-derived
            # unless data/external/cap_2026.csv is provided.
            "cap_context": cap_ctx.get(team, {
                "cap_space_m": None, "dead_cap_m": None,
                "constraint_tier": "normal", "notes": "",
            }),
            "coaching": coaching.get(team, {
                "hc_tree": "", "hc_college_stints": [],
            }),

            # Phase 8: analyst consensus + reasoning per team's R1 pick(s).
            # Pulled from the 20-analyst mock-draft spreadsheet. Includes
            # raw counts, tier-1 counts, consensus plurality, and per-pick
            # reasoning excerpts from each analyst.
            "analyst_consensus": _analyst_for_team(
                team, r1_picks, analyst_per_pick, analyst_reasoning
            ),
        }
        profiles[team] = profile

    # League-wide synthesis from the PDF (high-uncertainty teams, trade-up /
    # trade-down candidates, hard trade constraints, position urgency heat
    # map, scheme change flags, known unknowns, etc.). Stored under an
    # underscored key so consumers iterating team abbreviations can skip it.
    if narrative.get("_league"):
        profiles["_league"] = narrative["_league"]

    # Phase 7 (#17): build metadata with timestamps + input file mtimes.
    # Lets downstream consumers detect stale data and CI detect input drift.
    def _mtime(path: Path) -> str:
        if not path.exists():
            return ""
        return datetime.fromtimestamp(path.stat().st_mtime,
                                      tz=timezone.utc).isoformat(timespec="seconds")

    analyst_meta = {}
    if ANALYST_AGG_JSON.exists():
        analyst_meta = json.loads(ANALYST_AGG_JSON.read_text(encoding="utf-8")).get("_meta", {})

    profiles["_meta"] = {
        "generated_at":     datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source_mtimes": {
            "narrative":       _mtime(NARRATIVE_JSON),
            "roster_context":  _mtime(ROSTER_CTX_JSON),
            "cap_context":     _mtime(CAP_CTX_JSON),
            "coaching_tree":   _mtime(COACHING_JSON),
            "analyst_aggregate": _mtime(ANALYST_AGG_JSON),
            "team_context_csv": _mtime(TEAM_CTX),
            "prospects_csv":    _mtime(PROSPECTS),
        },
        "analyst_intel_meta": analyst_meta,
        "schema_version": "2.0",  # bumped for Phase 1-7 structured fields
    }

    return profiles


def main():
    profiles = build()
    OUT_JSON.write_text(json.dumps(profiles, indent=2), encoding="utf-8")
    print(f"Saved -> {OUT_JSON}  ({len(profiles)} team profiles)")

    # Summary
    team_keys = {k for k in profiles if not k.startswith("_")}
    explicit_teams = sorted(EXPLICIT_PROFILES.keys())
    derived_teams = sorted(team_keys - set(explicit_teams))
    print(f"\nNeeds source:")
    print(f"  explicit (user spec):   {len(explicit_teams)}  {', '.join(explicit_teams)}")
    print(f"  derived from team_needs: {len(derived_teams)}  {', '.join(derived_teams)}")

    print("\nTrade behaviour overrides applied to:")
    for t in sorted(TRADE_OVERRIDES):
        o = TRADE_OVERRIDES[t]
        print(f"  {t}: up={o['trade_up_rate']:.2f}  down={o['trade_down_rate']:.2f}")

    print("\nTop-3 roster needs per team  (src: user=your-spec, res=researched-default):")
    for team, prof in profiles.items():
        if team.startswith("_"):
            continue
        needs = prof["roster_needs"]
        top3 = sorted(needs.items(), key=lambda kv: -kv[1])[:3]
        parts = [f"{p}={v:.1f}" for p, v in top3]
        src = {"explicit_user_spec": "user",
               "researched_default": "res",
               "derived_from_team_needs": "drv"}.get(prof["needs_source"], "?")
        visits_n = prof["visit_signals"]["n_confirmed"]
        print(f"  {team:<4} [{src}]  picks={prof['r1_count']}(R1)/{prof['total_picks']}  "
              f"visits={visits_n:>2}  needs: {', '.join(parts)}")


if __name__ == "__main__":
    main()
