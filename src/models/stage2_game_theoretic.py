"""
Stage 2 — game-theoretic agent simulation with full intel overrides.

Pipeline per simulation:
  1. Determine trade events up-front (DAL->4, CIN->5, PHI->18 etc.).
  2. Iterate picks in order. For each pick:
       a. If the pick number has a scripted override (intel hardcoded from
          April 17), sample from its probability distribution — respecting
          cascade / trade conditions and already-taken players.
       b. Otherwise, use agent utility scoring:
             BPA (consensus) + need + visit + intel + GM-specific multipliers
       c. Before scoring, check for bilateral trade negotiation using
          Fitzgerald-Spielberger pick values.
       d. After each pick, update dynamic urgency on remaining teams
          (position run detection + recent-pick panic premium).

Key fixes vs. prior stage2:
  - ARI at pick 3: cannot select WR when qb_urgency >= 0.8
  - EDGE deep-class penalty only applies when consensus_rank > 15
  - Paired picks (Bailey/Reese) enforced so both cannot go in top 3
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
PROS_CSV = ROOT / "data" / "processed" / "prospects_2026_enriched.csv"
PRED_CSV = ROOT / "data" / "processed" / "predictions_2026.csv"
TEAM_CTX = ROOT / "data" / "processed" / "team_context_2026_enriched.csv"
TEAM_NEEDS = ROOT / "data" / "processed" / "team_needs_2026.csv"
TEAM_AGENTS_JSON = ROOT / "data" / "features" / "team_agents_2026.json"
ANALYST_AGG_JSON = ROOT / "data" / "features" / "analyst_aggregate_2026.json"
TRADE_EMPIRICAL_JSON = ROOT / "data" / "features" / "trade_empirical_2021_2025.json"
ANALYST_CONSENSUS_JSON = ROOT / "data" / "features" / "analyst_consensus_2026.json"
OUT_MC = ROOT / "data" / "processed" / "monte_carlo_2026_v12.csv"
OUT_TRADES = ROOT / "data" / "processed" / "monte_carlo_trades_2026.json"
GM_ALLOC_CSV = ROOT / "data" / "processed" / "gm_positional_allocation.csv"

# ---------------------------------------------------------------------------
# PDF-derived team agent data (loaded at import time).
# build_team_agents.py produces data/features/team_agents_2026.json which
# carries the full PDF narrative + structured sub-fields (scheme, fa_moves,
# latent_needs, predictability, trade_probability, gm_affinity, etc.).
# We merge this into TEAM_PROFILE_OVERRIDES as a backfill — hardcoded values
# below win, but any field the overrides dict doesn't set is pulled from the
# agent. New fields (scheme_premium, predictability, latent_needs) are
# always exposed under their `_agent_*` key for the scorer to consume.
# ---------------------------------------------------------------------------
_TEAM_AGENTS: dict[str, dict] = {}
if TEAM_AGENTS_JSON.exists():
    _TEAM_AGENTS = json.loads(TEAM_AGENTS_JSON.read_text(encoding="utf-8"))

# Phase 2 (#5): league cascade rules. Each rule: {trigger_team, trigger_pick,
# trigger_position, dependent_team, dependent_pick, dependent_position,
# effect}. simulate_one consults this live — after a trigger pick lands on
# the trigger_position, the dependent team's need_match for that position
# is damped by CASCADE_NEED_DAMPING (0.5 = "probability drops ~50%" per the
# PDF's phrasing for the MIN->CAR S cascade).
_CASCADE_RULES = (_TEAM_AGENTS.get("_league", {})
                  .get("cascade_rules_struct", []))
CASCADE_NEED_DAMPING = 0.5

# Phase 7: analyst aggregate (multi-source visit consensus + market odds).
# Used for (a) upgrading visit signal quality when multiple sources confirm,
# and (b) market-implied per-pick priors for late-round projection.
_ANALYST_AGG: dict[str, dict] = {}
if ANALYST_AGG_JSON.exists():
    _ANALYST_AGG = json.loads(ANALYST_AGG_JSON.read_text(encoding="utf-8")).get("players", {})

# Empirical R1 trade rates from 2021-2025 Wikipedia data. Replaces the
# hardcoded 3-bucket pick_range_trade_rate and the 0.50/0.50 team placeholders
# for the 17-ish teams where no hand-curated value existed.
#
# Falls back to league base rate (0.36) for any missing slot / team.
_TRADE_EMPIRICAL: dict = {}
if TRADE_EMPIRICAL_JSON.exists():
    _TRADE_EMPIRICAL = json.loads(TRADE_EMPIRICAL_JSON.read_text(encoding="utf-8"))

# Analyst consensus from data/2026 Mock Draft Data.xlsx (20 mocks, 6 tier-1).
# Per-pick frequencies serve as the PRIMARY intel-override distribution —
# replaces my hand-transcribed 0.38/0.32 hardcoded values with actual
# empirical counts. Tier-1 analysts are weighted more heavily.
_ANALYST_CONSENSUS: dict = {}
if ANALYST_CONSENSUS_JSON.exists():
    _ANALYST_CONSENSUS = json.loads(ANALYST_CONSENSUS_JSON.read_text(encoding="utf-8"))


def analyst_distribution(pick_num: int, taken_names: set,
                          pros_df: pd.DataFrame | None = None) -> dict[str, float]:
    """Blend tier-1 and all-analyst frequencies into an empirical intel
    distribution for a given pick slot.

    If a top-5-consensus prospect is still available but ISN'T in the
    analyst-mock data for this pick (analysts didn't mock them here),
    we inject them with a floor weight proportional to their consensus
    rank — prevents Love/Bailey-type elite talents from being suppressed
    when TEN passes and analysts didn't bother writing "Love slides to 15."
    """
    info = _ANALYST_CONSENSUS.get("per_pick", {}).get(str(pick_num), {})
    if not info:
        # No analyst data at all — fall back to base scoring.
        return {}
    t1 = info.get("freq_tier1", {}) or {}
    all_ = info.get("freq_all", {}) or {}
    blended: dict[str, float] = {}
    for name, f in t1.items():
        blended[name] = blended.get(name, 0.0) + 0.60 * f
    for name, f in all_.items():
        blended[name] = blended.get(name, 0.0) + 0.40 * f

    resolved: dict[str, float] = {}
    for short, w in blended.items():
        full = _resolve_analyst_name(short)
        if full and full not in taken_names:
            resolved[full] = resolved.get(full, 0.0) + w

    # ELITE-SLIDER FLOOR: inject any top-5 consensus prospect still
    # available but missing from the analyst dist. Gives them a floor
    # weight equal to 70% of the current max — enough to be a real
    # contender when they've slid past their expected slot.
    if pros_df is not None and resolved:
        current_max = max(resolved.values())
        elite = pros_df[(pros_df["rank"] <= 5)
                         & (~pros_df["player"].isin(taken_names))]
        for _, row in elite.iterrows():
            name = row["player"]
            if name not in resolved:
                resolved[name] = current_max * 0.70

    total = sum(resolved.values())
    if total <= 0:
        return {}
    return {k: v / total for k, v in resolved.items()}


# Analyst mock columns use short surnames. Map to the full name used in our
# prospects CSV. Built from our known consensus board; extend as needed.
_ANALYST_NAME_MAP = {
    "Mendoza":              "Fernando Mendoza",
    "Reese":                "Arvell Reese",
    "Bailey":               "David Bailey",
    "Love":                 "Jeremiyah Love",
    "Styles":               "Sonny Styles",
    "Mauigoa":              "Francis Mauigoa",
    "Tate":                 "Carnell Tate",
    "Downs":                "Caleb Downs",
    "Bain Jr.":             "Rueben Bain",
    "Bain":                 "Rueben Bain",
    "Delane":               "Mansoor Delane",
    "Tyson":                "Jordyn Tyson",
    "Fano":                 "Spencer Fano",
    "Lemon":                "Makai Lemon",
    "Freeling":             "Monroe Freeling",
    "McCoy":                "Jermod McCoy",
    "Sadiq":                "Kenyon Sadiq",
    "Thieneman":            "Dillon Thieneman",
    "Proctor":              "Kadyn Proctor",
    "Faulk":                "Keldric Faulk",
    "Mesidor":              "Akheem Mesidor",
    "Cooper Jr.":           "Omar Cooper Jr.",
    "Cooper":               "Omar Cooper Jr.",
    "McNeil-Warren":        "Emmanuel McNeil-Warren",
    "Blake Miller":         "Blake Miller",
    "Miller (OT)":          "Blake Miller",
    "Lomu":                 "Caleb Lomu",
    "Concepcion":           "Kevin Concepcion",
    "Boston":               "Denzel Boston",
    "Parker":               "T.J. Parker",
    "Woods":                "Peter Woods",
    "Ioane":                "Olaivavega Ioane",
    "Iheanachor":           "Max Iheanachor",
    "Howell":               "Cashius Howell",
    "Malachi Howell":       "Cashius Howell",     # disambiguation: analyst sheet misnames
    "Young":                "Zion Young",
    "Simpson":              "Ty Simpson",
    "Johnson":              "Chris Johnson",
    "Johnson (CB)":         "Chris Johnson",
    "Hood":                 "Colton Hood",
    "Bisontis":             "Chase Bisontis",
    "Christen Miller":      "Christen Miller",
    "Lawrence":             "Malachi Lawrence",
    "Price":                "Jadarian Price",
    "Cisse":                "Brandon Cisse",
    "Stowers":              "Eli Stowers",
    "McDonald":             "Kayden McDonald",
    "Allen":                "C.J. Allen",
    "Terrell":              "Avieon Terrell",
    "Banks":                "Caleb Banks",
}

def _resolve_analyst_name(short: str) -> str | None:
    if not short:
        return None
    return _ANALYST_NAME_MAP.get(short.strip(), None)

EMPIRICAL_LEAGUE_RATE = _TRADE_EMPIRICAL.get("league_avg_rate_per_pick", 0.30)

def empirical_pick_rate(pick_num: int) -> float:
    """Empirical probability this pick slot moved 2021-2025."""
    rates = _TRADE_EMPIRICAL.get("per_pick_rate", {})
    return float(rates.get(str(pick_num), EMPIRICAL_LEAGUE_RATE))

def empirical_team_rates(team: str) -> tuple[float, float, bool]:
    """Return (trade_up_rate, trade_down_rate, has_signal) from 2021-2025."""
    info = _TRADE_EMPIRICAL.get("per_team_rates", {}).get(team, {})
    if not info.get("has_signal"):
        return (EMPIRICAL_LEAGUE_RATE / 2, EMPIRICAL_LEAGUE_RATE / 2, False)
    return (float(info["trade_up_rate"]),
            float(info["trade_down_rate"]),
            True)

# Fine-grained position mapping used by gm_positional_allocation.csv
POS_TO_GM_GROUP = {
    "QB": "QB", "RB": "RB", "FB": "RB", "HB": "RB",
    "WR": "WR", "TE": "TE",
    "OT": "OT", "T": "OT",
    "G": "G", "OG": "G", "IOL": "G",   # treat IOL as G for affinity lookup
    "C": "C",
    "EDGE": "EDGE", "DE": "EDGE",
    "DL": "IDL", "DT": "IDL", "NT": "IDL",
    "LB": "LB", "ILB": "LB", "OLB": "LB", "MLB": "LB",
    "CB": "CB", "DB": "CB",
    "S": "S", "FS": "S", "SS": "S", "SAF": "S",
}


def load_gm_affinity() -> dict:
    """Returns dict keyed by (team, gm_position_group) -> delta."""
    if not GM_ALLOC_CSV.exists():
        return {}
    df = pd.read_csv(GM_ALLOC_CSV)
    return {(r["team"], r["position_group"]): float(r["delta"])
            for _, r in df.iterrows()}


# GM-affinity scaling + clipping. delta = team_pct - league_pct.
# Roseman PHI LB +12% -> multiplier = 1 + 0.12*3 = 1.36, clipped to 1.25.
GM_AFFINITY_SCALE = 3.0
GM_AFFINITY_MIN = 0.80
GM_AFFINITY_MAX = 1.25

GM_AFFINITY_CACHE: dict = {}   # populated in main()

N_SIMULATIONS = 500
RNG_SEED = 42
NOISE_STD_FINAL_SCORE = 15.0          # picks 1-16
NOISE_STD_LATE_PICKS = 25.0           # picks 17-32 — bump variance (BUG 2)

# ---------------------------------------------------------------------------
# Dynamic trade generator — model-derived trade scenarios based on current
# board state (not hardcoded analyst consensus). Triggers:
#
#   1. QB cascade: count available-QBs vs QB-needy teams in next N picks.
#      If supply < demand, the earliest QB-needy team has elevated trade-up
#      probability for that slot.
#   2. Tier exhaustion: for premium positions (EDGE, OT, CB, WR), define
#      "elite tier" size. When last of tier is at risk and multiple teams
#      downstream need that position, trade-up probability rises.
#   3. Leapfrog: current pick holder sees a team right behind with same
#      positional need → the TRAILING team has elevated trade-up prob
#      (jump the team in front).
# ---------------------------------------------------------------------------
QB_CASCADE_WINDOW = 5   # look at next 5 picks for QB-needy teams
TIER_SIZES = {"EDGE": 5, "OT": 5, "CB": 5, "WR": 6, "QB": 2, "IDL": 4}
LEAPFROG_WINDOW = 2     # immediate next 2 picks define "leapfrog" range

def compute_dynamic_trade_boost(
    current_pick: dict,
    remaining_picks: list[dict],
    history: dict,
    taken_names: set,
    pros: pd.DataFrame,
    top3_needs: dict,
) -> float:
    """Return a multiplicative boost on the current pick's trade-down
    probability based on board state. >1.0 means the current pick is more
    likely to be traded than baseline. Returns 1.0 when no driver fires."""
    boost = 1.0

    # Driver 1: QB cascade. If QB-needy teams pick in the next N slots
    # AND there are fewer quality QBs than demand, current pick (if owned
    # by a non-QB-needy team) becomes a trade-down target for a QB-needy
    # team leapfrogging up.
    current_team = current_pick.get("team")
    current_needs = top3_needs.get(current_team, [])
    if "QB" not in current_needs:
        # Count QB-needy teams in next QB_CASCADE_WINDOW picks
        qb_needy_count = sum(
            1 for p in remaining_picks[:QB_CASCADE_WINDOW]
            if "QB" in top3_needs.get(p.get("team", ""), [])
        )
        if qb_needy_count >= 1:
            # Count available QBs with reasonable consensus rank
            avail_qbs = int(((pros["position"] == "QB") & (pros["rank"] <= 50)
                             & (~pros["player"].isin(taken_names))).sum())
            if qb_needy_count > avail_qbs:
                # Supply < demand → strong trade-up pressure on downstream QB teams
                boost *= 1.8

    # Driver 2: tier exhaustion at premium positions. If the "last of a
    # tier" is still on board, and multiple downstream teams need that
    # position, current pick becomes valuable trade-back real estate.
    for pos, tier_n in TIER_SIZES.items():
        # How many at this position have been taken so far?
        taken_at_pos = sum(
            1 for name in taken_names
            if (pros.loc[pros["player"] == name, "position"].iloc[0]
                if not pros[pros["player"] == name].empty else "") == pos
        )
        if taken_at_pos >= tier_n - 1:
            # Tier nearly exhausted. Count downstream need.
            pos_needy_behind = sum(
                1 for p in remaining_picks[:LEAPFROG_WINDOW + 2]
                if pos in top3_needs.get(p.get("team", ""), [])
            )
            if pos_needy_behind >= 2 and pos not in current_needs:
                boost *= 1.35
                break   # one tier-boost at a time

    # Driver 3: leapfrog. If current team's top-available position matches
    # the VERY NEXT pick holder's need, there's pressure (for a different
    # partner further downstream) to leapfrog. This elevates the overall
    # trade-rate at the current slot.
    if remaining_picks:
        next_pick = remaining_picks[0]
        next_needs = top3_needs.get(next_pick.get("team", ""), [])
        # Pick what the CURRENT team would take — use their top unfilled need
        for need_pos in current_needs:
            if need_pos in next_needs:
                # Both teams want same position → incentive for team further
                # down to jump BOTH. Mild boost.
                boost *= 1.15
                break

    return boost


# Phase 1 (#3): per-team multiplicative noise on scoring, driven by the PDF's
# predictability tier. LOW-predictability teams (regime-change, trade-heavy)
# have wider output distributions. HIGH-predictability (LV Mendoza lock, TB
# Licht stated EDGE) get tighter.
PREDICTABILITY_NOISE_MULT = {
    "HIGH":        0.50,
    "MEDIUM-HIGH": 0.80,
    "MEDIUM":      1.00,
    "LOW-MEDIUM":  1.30,
    "LOW":         1.70,
    "":            1.00,
}
PREDICTABILITY_SCORE_SIGMA = 0.04   # base sigma applied as score*(1 + N(0, sigma*mult))

# Phase 1 (#4): map PDF trade-probability tiers to per-pick
# pick_range_trade_rate priors. These STACK with (not replace) the hardcoded
# TRADE_OVERRIDES and the CSV-driven rates — we take the max so the PDF can
# only make a pick more trade-prone, never less.
TRADE_TIER_RATE = {
    "VERY_HIGH": 0.70,
    "HIGH":      0.50,
    "MODERATE":  0.25,
    "LOW":       0.10,
    "VERY_LOW":  0.03,
}

# ---------------------------------------------------------------------------
# Phase 6 (#13): scheme-fit thresholds. Keys are (scheme_type, position) where
# scheme_type matches the parsed `scheme_struct.type` from the PDF narrative
# (shanahan_zone, mcvay_spread, harbaugh_power, bradley_cover3, fangio_match,
# flores_pressure, ohio_state/hafley_ohio, wide9, etc.). Position is canonical
# (CB, EDGE, OT, WR, LB, S).
#
# Each entry: {min_weight, max_weight, min_ras, min_height_in} — all optional.
# A prospect's fit score is 1.0 if it passes every specified threshold, 0.5
# if it misses one, 0.0 if it misses two or more. When measurements are
# missing (height often NaN for this class), that criterion is skipped
# (treated as passing).
# ---------------------------------------------------------------------------
SCHEME_FIT_RULES: dict[tuple[str, str], dict] = {
    # Cover-3 / Bradley: big press CBs, rangy centerfield S
    ("bradley_cover3", "CB"): {"min_weight": 190, "min_ras": 8.0, "min_height_in": 72},
    ("bradley_cover3", "S"):  {"min_weight": 200, "min_ras": 8.0},
    ("bradley_cover3", "EDGE"): {"min_weight": 245, "max_weight": 275, "min_ras": 8.0},
    # Wide-9 (Ryans HOU, Schwartz CLE, SF Sorensen): twitchy EDGE
    ("schwartz_wide9", "EDGE"): {"min_weight": 240, "max_weight": 270, "min_ras": 8.5},
    ("ryans_wide9",   "EDGE"): {"min_weight": 240, "max_weight": 270, "min_ras": 8.5},
    # Harbaugh power: maulers on OL, physical DBs
    ("harbaugh_power", "OT"):  {"min_weight": 310, "min_ras": 7.0},
    ("harbaugh_power", "G"):   {"min_weight": 315, "min_ras": 7.0},
    ("harbaugh_power", "IOL"): {"min_weight": 315, "min_ras": 7.0},
    ("harbaugh_power", "CB"):  {"min_weight": 195, "min_ras": 7.5},
    # Shanahan zone / McVay / Kubiak: athletic OL with mobility
    ("shanahan_zone", "OT"):  {"min_weight": 300, "max_weight": 325, "min_ras": 8.0},
    ("shanahan_zone", "G"):   {"min_weight": 300, "max_weight": 320, "min_ras": 8.0},
    ("mcvay_spread",  "OT"):  {"min_weight": 300, "max_weight": 325, "min_ras": 8.0},
    ("lafleur_zone",  "OT"):  {"min_weight": 300, "max_weight": 325, "min_ras": 8.0},
    # Fangio/Vic match (PHI): versatile long DBs
    ("fangio_match", "CB"):   {"min_weight": 190, "min_ras": 8.0, "min_height_in": 72},
    ("fangio_match", "S"):    {"min_weight": 200, "min_ras": 8.0},
    # Flores pressure (MIN): versatile DBs + fast LBs
    ("flores_pressure", "LB"): {"min_weight": 225, "max_weight": 245, "min_ras": 8.5},
    ("flores_pressure", "CB"): {"min_weight": 185, "min_ras": 8.0},
    # Ohio State (MIA Hafley): rangy athletic DBs
    ("hafley_ohio",   "CB"):  {"min_weight": 190, "min_ras": 8.5, "min_height_in": 72},
    ("hafley_ohio",   "S"):   {"min_weight": 200, "min_ras": 8.5},
    ("hafley_ohio",   "LB"):  {"min_weight": 225, "max_weight": 240, "min_ras": 9.0},
    # Macdonald multiple (SEA)
    ("macdonald_multiple", "CB"): {"min_weight": 190, "min_ras": 8.0},
    ("macdonald_multiple", "EDGE"): {"min_weight": 250, "min_ras": 8.0},
    # Bowles blitz (TB): long DBs, twitchy EDGE
    ("bowles_blitz", "CB"):   {"min_weight": 190, "min_ras": 8.0},
    ("bowles_blitz", "EDGE"): {"min_weight": 245, "min_ras": 8.5},
    # Reid spread (KC): speed/separation WRs
    ("reid_spread", "WR"):    {"max_weight": 210, "min_ras": 8.5},
    # Monken vertical (CLE): big-bodied WRs for contested catches
    ("monken_vertical", "WR"): {"min_weight": 205, "min_ras": 7.5},
    # Quinn aggressive (WAS)
    ("quinn_aggressive", "EDGE"): {"min_weight": 245, "min_ras": 8.0},
    ("quinn_aggressive", "CB"):   {"min_weight": 190, "min_ras": 7.5},
    # Minter multiple (BAL): aggressive coverage -> long CBs
    ("minter_multiple", "CB"):   {"min_weight": 190, "min_ras": 8.0, "min_height_in": 72},
    ("minter_multiple", "EDGE"): {"min_weight": 250, "min_ras": 8.0},
}


def compute_scheme_fit(prospects: pd.DataFrame, scheme_type: str) -> pd.Series:
    """Return a per-prospect fit score in {0.0, 0.5, 1.0} given a team's
    scheme_type. Returns a Series of 1.0 (pass/no-rule) by default; only
    positions with an explicit rule entry can score below 1.0."""
    if not scheme_type or scheme_type == "default":
        return pd.Series(1.0, index=prospects.index)

    # Convert prospect height (varied formats: '6\'2"', '74', NaN) to inches.
    def _to_inches(val):
        if pd.isna(val):
            return None
        s = str(val)
        if "'" in s:
            try:
                ft, rest = s.split("'", 1)
                inch = rest.replace('"', '').strip()
                return int(ft) * 12 + float(inch or 0)
            except ValueError:
                return None
        try:
            return float(s)
        except ValueError:
            return None

    heights_in = prospects.get("height", pd.Series(index=prospects.index)).apply(_to_inches)
    weights = pd.to_numeric(prospects.get("weight"), errors="coerce")
    ras = pd.to_numeric(prospects.get("ras_score"), errors="coerce")
    pos_group = prospects["position"].fillna("").astype(str).str.upper()

    out = pd.Series(1.0, index=prospects.index)
    for (scheme, pos_rule), rule in SCHEME_FIT_RULES.items():
        if scheme != scheme_type:
            continue
        mask = pos_group == pos_rule
        if not mask.any():
            continue
        # For each prospect matching position_rule, check the thresholds.
        misses = pd.Series(0, index=prospects.index)
        if "min_weight" in rule:
            fail = mask & weights.notna() & (weights < rule["min_weight"])
            misses = misses + fail.astype(int)
        if "max_weight" in rule:
            fail = mask & weights.notna() & (weights > rule["max_weight"])
            misses = misses + fail.astype(int)
        if "min_ras" in rule:
            fail = mask & ras.notna() & (ras < rule["min_ras"])
            misses = misses + fail.astype(int)
        if "min_height_in" in rule:
            fail = mask & heights_in.notna() & (heights_in < rule["min_height_in"])
            misses = misses + fail.astype(int)
        # 0 misses → 1.0, 1 miss → 0.5, 2+ → 0.0
        out = out.where(~(mask & (misses == 1)), 0.5)
        out = out.where(~(mask & (misses >= 2)), 0.0)
    return out

# Team-profile overrides (PART 2). Patches qb_urgency, adds hard-blocked
# R1 positions, and optional team-specific need-score overrides that
# supersede team_needs_2026.csv. All fields optional.
TEAM_PROFILE_OVERRIDES: dict[str, dict] = {
    # Rookie-QB locks: Maye/Ward/Dart franchise QBs despite sub-$35M APY.
    "NE":  {"qb_urgency": 0.0, "r1_blocked_positions": {"QB"},
            "needs_override": ["OT", "WR", "EDGE", "TE", "CB"]},
    "TEN": {"qb_urgency": 0.0,
            "needs_override": ["RB", "OT", "EDGE", "CB"]},
    "NYG": {"qb_urgency": 0.0,
            "needs_override": ["WR", "OT", "S", "LB", "RB"]},
    "ARI": {"qb_urgency": 1.0},
    # PIT: latent OL need (47 sacks allowed); Howard fallback keeps qb open.
    "PIT": {"qb_urgency": 0.65,
            "needs_override": ["OL", "WR", "IOL", "S", "QB"]},
    "CHI": {"qb_urgency": 0.0, "r1_blocked_positions": {"WR", "QB"},
            "needs_override": ["EDGE", "S", "OL", "IDL"]},
    # CIN: 7.8 ypa allowed (4th worst) -> CB/S elevated latent
    "CIN": {"qb_urgency": 0.0, "r1_blocked_positions": {"QB", "RB"},
            "needs_override": ["CB", "S", "EDGE", "LB"]},
    "BAL": {"qb_urgency": 0.0, "r1_blocked_positions": {"QB"},
            "needs_override": ["EDGE", "OT", "WR", "IDL"]},
    "WAS": {"qb_urgency": 0.0,
            "needs_override": ["WR", "LB", "S", "EDGE"]},
    "BUF": {"qb_urgency": 0.0},    # Allen locked
    # KC: both McDuffie (traded) AND Watson (FA) gone — CB latent=5.
    "KC":  {"qb_urgency": 0.0,
            "needs_override": ["CB", "OL", "EDGE", "WR"]},
    "JAX": {"qb_urgency": 0.0},
    "CLE": {"qb_urgency": 0.0},
    "DET": {"qb_urgency": 0.0},
    # DAL: latent EDGE/CB/LB elevated — worst pass D by EPA in 2025.
    "DAL": {"qb_urgency": 0.0,
            "needs_override": ["EDGE", "CB", "LB", "S", "OT"]},
    "MIN": {"qb_urgency": 0.0},
    "IND": {"qb_urgency": 0.0},
    "TB":  {"qb_urgency": 0.0},
    "GB":  {"qb_urgency": 0.0},
    "DEN": {"qb_urgency": 0.0},
    "SEA": {"qb_urgency": 0.0, "r1_blocked_positions": {"QB"},
            "needs_override": ["RB", "CB", "EDGE", "WR"]},
    # SF: Trent Williams 38 -> OT latent=4; 20 sacks dead last 2025.
    "SF":  {"qb_urgency": 0.0,
            "needs_override": ["OT", "EDGE", "CB", "IOL", "DL"]},
    # LAC: WR blocked (no R1 WR need).
    "LAC": {"qb_urgency": 0.0,
            "r1_blocked_positions": {"WR"},
            "needs_override": ["DL", "EDGE", "CB", "IOL"]},
    # MIA: multi-position rebuild (WR/CB/S).
    "MIA": {"qb_urgency": 0.0,
            "needs_override": ["WR", "CB", "S", "OT", "EDGE"]},
    # Stafford 38yo; LAR latent QB succession at background tier.
    "LAR": {"qb_urgency": 0.3,
            "needs_override": ["WR", "OT", "CB", "QB", "S"]},
    # HOU: elite offense added WR via FA — WR blocked in R1.
    "HOU": {"qb_urgency": 0.0,
            "r1_blocked_positions": {"WR"},
            "needs_override": ["DL", "IOL", "OT", "CB"]},
    "PHI": {"qb_urgency": 0.0},
    "ATL": {"qb_urgency": 0.0},
    "CAR": {"qb_urgency": 0.0},
    "LV":  {"qb_urgency": 1.0},    # unsettled
    "NYJ": {"qb_urgency": 1.0},    # Geno bridge
    # NO: Shaheed traded -> WR latent=4. Shough needs weapons.
    "NO":  {"qb_urgency": 0.7,
            "needs_override": ["WR", "EDGE", "CB", "OT"]},
}


def get_team_profile(team: str) -> dict:
    """Merge the hardcoded TEAM_PROFILE_OVERRIDES entry with PDF-derived
    fields from team_agents_2026.json. Hardcoded values ALWAYS win; the
    agent file fills gaps and adds extra fields keyed with `_agent_*`.

    Extra fields exposed (all optional, scorer reads them if present):
      - _agent_scheme           : {"type": str, "premium": [positions]}
      - _agent_latent_needs     : {position: synthetic_need_score}
      - _agent_predictability   : HIGH | MEDIUM-HIGH | MEDIUM | LOW-MEDIUM | LOW
      - _agent_trade_probability: {"trade_up_tier": ..., "trade_up_prob": ...}
      - _agent_fa_moves         : {"arrivals": [...], "departures": [...]}
      - _agent_gm_affinity      : {position: delta_from_league_average}
      - _agent_narrative        : raw PDF prose for inspection/debug
    """
    merged = dict(TEAM_PROFILE_OVERRIDES.get(team, {}))
    agent = _TEAM_AGENTS.get(team, {})
    if not agent:
        return merged

    # --- Backfill fields the hardcoded override didn't set -----------------
    if "qb_urgency" not in merged and "qb_urgency" in agent:
        merged["qb_urgency"] = float(agent["qb_urgency"])

    # If no needs_override was hardcoded, derive a 5-entry list from the
    # agent's roster_needs (top 5 by score). Preserves existing behavior
    # where hardcoded overrides win.
    if "needs_override" not in merged and agent.get("roster_needs"):
        ranked = sorted(agent["roster_needs"].items(),
                        key=lambda kv: -float(kv[1]))
        merged["needs_override"] = [p for p, _ in ranked[:5]]

    # --- Always expose new fields under `_agent_*` keys --------------------
    merged["_agent_scheme"] = agent.get("scheme", {})
    merged["_agent_latent_needs"] = agent.get("latent_needs", {})
    merged["_agent_predictability"] = agent.get("predictability", "")
    merged["_agent_trade_probability"] = (
        agent.get("trade_behavior", {}).get("pdf_tier", {})
    )
    merged["_agent_fa_moves"] = agent.get("fa_moves",
                                          {"arrivals": [], "departures": []})
    merged["_agent_gm_affinity"] = agent.get("gm_affinity", {})
    merged["_agent_narrative"] = agent.get("narrative", {})
    # Phase 3: structured narrative fields (injuries, decision-maker,
    # hard constraints). Lifted to top-level for easy consumption.
    narrative = agent.get("narrative", {})
    merged["_agent_injury_flags"] = narrative.get("injury_flags", [])
    merged["_agent_decision_maker"] = narrative.get("decision_maker", {})
    merged["_agent_hard_constraints"] = [
        c.get("type") for c in narrative.get("hard_constraints", [])
    ]
    # Phase 4: roster-derived context
    roster_ctx = agent.get("roster_context", {}) or {}
    merged["_agent_age_cliffs"] = roster_ctx.get("age_cliffs", [])
    merged["_agent_prev_year_alloc"] = roster_ctx.get("previous_year_allocation", {})
    # Phase 5: cap + coaching
    cap = agent.get("cap_context", {}) or {}
    merged["_agent_cap_tier"] = cap.get("constraint_tier", "normal")
    merged["_agent_cap_space_m"] = cap.get("cap_space_m")
    merged["_agent_dead_cap_m"] = cap.get("dead_cap_m")
    coaching = agent.get("coaching", {}) or {}
    merged["_agent_hc_tree"] = coaching.get("hc_tree", "")
    merged["_agent_hc_college_stints"] = coaching.get("hc_college_stints", [])
    return merged

# Fitzgerald-Spielberger trade chart (top 32)
FITZ_VALUES = {
    1: 3000, 2: 2600, 3: 2200, 4: 1800, 5: 1600, 6: 1400, 7: 1300, 8: 1200,
    9: 1100, 10: 1000, 11: 900, 12: 850, 13: 800, 14: 750, 15: 700, 16: 650,
    17: 600, 18: 550, 19: 525, 20: 500, 21: 475, 22: 450, 23: 425, 24: 400,
    25: 375, 26: 350, 27: 325, 28: 300, 29: 275, 30: 250, 31: 225, 32: 200,
}

# 2026 class scarcity narrative (user-specified)
DEEP_CLASS = {"EDGE", "OT", "CB"}
THIN_CLASS = {"QB", "WR"}
DEEP_MULT = 0.8
THIN_MULT = 1.3
DEEP_EDGE_PROTECTION_THRESHOLD = 15   # top-15 EDGE keep full need_match

# Global per-player multipliers (news-driven). Applied in both base scoring
# and override sampling so the penalty works whether the pick is governed
# by an intel override or the base agent model.
MEDICAL_PENALTIES: dict[str, float] = {
    "Jermod McCoy": 0.75,   # missed all of 2025 with torn ACL
}

# Post-combine risers — players whose stage-1 final_score / first_round_mock
# _rate in the prospects CSV predates their combine showing. Sourced from
# current analyst coverage (Kiper / McShay / Brugler / Jeremiah mocks, PFF
# post-combine mock, betting-market moves). A multiplier of 1.30 = ~30%
# score bump, mirroring real-world analyst tier revisions post-combine.
POST_COMBINE_BOOSTS: dict[str, float] = {
    # Sonny Styles (LB/S hybrid, Ohio State) — #5-6 consensus, tier-1 analyst
    # picks for DAL trade-up scenarios. 1.45 was too aggressive (pushed him
    # above Love at TEN@4 where analysts have Love 11/20); 1.20 keeps Styles
    # competitive for pick 5/6 without displacing Love's TEN@4 plurality.
    "Sonny Styles": 1.20,
}

# Position-scarcity premium: when a prospect is the top-ranked at their
# position AND there's a large ranking gap to the next player at the same
# position, they effectively carry a higher positional value than the
# generic POS_VALUE_MULT suggests. Computed lazily at first call.
POSITION_SCARCITY_GAP_THRESHOLD = 20  # if gap >=20 to next-at-position, apply
POSITION_SCARCITY_BOOST = 1.15
_POS_SCARCITY_CACHE: dict[str, float] = {}

def _compute_position_scarcity(prospects: pd.DataFrame) -> dict[str, float]:
    """Return {player_name: boost_multiplier} for the top-ranked player at
    each position where the gap to #2 is >= POSITION_SCARCITY_GAP_THRESHOLD.
    Cached after first build."""
    if _POS_SCARCITY_CACHE:
        return _POS_SCARCITY_CACHE
    sub = prospects[["player", "position", "rank"]].dropna()
    for pos, grp in sub.groupby("position"):
        grp_sorted = grp.sort_values("rank")
        if len(grp_sorted) < 2:
            continue
        top1, top2 = grp_sorted.iloc[0], grp_sorted.iloc[1]
        gap = int(top2["rank"]) - int(top1["rank"])
        if gap >= POSITION_SCARCITY_GAP_THRESHOLD:
            _POS_SCARCITY_CACHE[top1["player"]] = POSITION_SCARCITY_BOOST
    return _POS_SCARCITY_CACHE

# Positional value multipliers on the BPA term (draft capital / scarcity).
# Top-1 at a non-premium position gets the discount reduced to 0.95
# (e.g. Jeremiyah Love as RB1, Kenyon Sadiq as TE1).
POS_VALUE_MULT = {
    "QB": 1.40, "EDGE": 1.30, "OT": 1.20, "CB": 1.20,
    "WR": 1.00, "LB": 1.00, "S": 1.00,
    # Rebalanced: the old 0.85/0.80 crushed TEs and interior DL below
    # realistic R1 odds. Historical avg: 3-4 IDL and 1-2 TE in R1 annually.
    "TE": 0.95, "RB": 0.90, "FB": 0.85, "HB": 0.90,
    "IOL": 0.95, "G": 0.95, "C": 0.95,
    # Interior DL bumped to 1.05 — 2023-2025 averaged 2-3 R1 IDL picks.
    # Previous 0.95 made them lose to cons-30+ CBs on otherwise-tied scores.
    "DL": 1.05, "DT": 1.05, "IDL": 1.05, "NT": 1.00,
}
NON_PREMIUM_RAW = {"TE", "RB", "FB", "HB", "IOL", "G", "C", "DL", "DT", "NT"}
ELITE_CONS_RANK_THRESHOLD = 20   # cons <=20 qualifies for BPA override (was 15)
REACH_GAP_THRESHOLD = 8          # cons_rank - pick_num > 8 -> 50% penalty (was 12)
LATE_PICK_REACH_THRESHOLD = 8    # picks 21-32: 8-slot reach cap (was 10)
SLIDER_BOOST_THRESHOLD = 10      # top-10 prospect still available past their slot gets +50% score

# PART 5 OUTPUT: hand-curated per-pick analyst picks for agreement checks.
# Only picks where the user provided multiple analyst signals are tracked.
# Empty strings are treated as "no data" and skipped in the agreement calc.
ANALYST_PICKS: dict[int, dict[str, str]] = {
    10: {"kiper": "Mansoor Delane", "brugler": "Mansoor Delane",
         "jeremiah": "Mansoor Delane", "miller_reid": "Mansoor Delane",
         "espn": "Jermod McCoy"},
    11: {"kiper": "Francis Mauigoa", "brugler": "Francis Mauigoa",
         "jeremiah": "Mansoor Delane", "miller_reid": "Francis Mauigoa",
         "espn": "Keldric Faulk"},
    17: {"kiper": "Monroe Freeling", "brugler": "Monroe Freeling",
         "jeremiah": "Kadyn Proctor", "miller_reid": "Monroe Freeling",
         "espn": "Monroe Freeling"},
    21: {"kiper": "Olaivavega Ioane", "brugler": "Blake Miller",
         "jeremiah": "Blake Miller", "miller_reid": "Blake Miller",
         "espn": "Blake Miller"},
    22: {"kiper": "Peter Woods", "brugler": "Akheem Mesidor",
         "jeremiah": "Avieon Terrell", "miller_reid": "Peter Woods",
         "espn": "Olaivavega Ioane"},
    23: {"kiper": "Blake Miller", "brugler": "Monroe Freeling",
         "jeremiah": "Kadyn Proctor", "miller_reid": "Emmanuel McNeil-Warren",
         "espn": "Blake Miller"},
    26: {"kiper": "Keldric Faulk", "brugler": "Malachi Lawrence",
         "jeremiah": "Keldric Faulk", "miller_reid": "Cashius Howell",
         "espn": "Keldric Faulk"},
    27: {"kiper": "Max Iheanachor", "brugler": "Caleb Lomu",
         "jeremiah": "Kadyn Proctor", "miller_reid": "Caleb Lomu",
         "espn": "Max Iheanachor"},
    28: {"kiper": "Christen Miller", "brugler": "Chase Bisontis",
         "jeremiah": "Kayden McDonald", "miller_reid": "Christen Miller",
         "espn": "Chase Bisontis"},
    31: {"kiper": "Akheem Mesidor", "brugler": "Max Iheanachor",
         "jeremiah": "Blake Miller", "miller_reid": "Cashius Howell",
         "espn": "Akheem Mesidor"},
}

# Per-pick consensus-rank cap applied in the BASE model only. Intel
# overrides are exempt by design (they're listing specific targets).
def cap_threshold(pick_num: int) -> int:
    if pick_num <= 10:
        return 22      # top-10 tighter (was 25)
    if pick_num <= 20:
        return 35      # mid-first tighter (was 40)
    return 45          # late-first tighter (was 60) — stops 12-slot reaches

# Prospect position -> canonical need position
POS_TO_NEEDS = {
    "QB": "QB", "RB": "RB", "FB": "RB", "HB": "RB",
    "WR": "WR", "TE": "TE",
    "OT": "OL", "G": "OL", "C": "OL", "OG": "OL", "IOL": "OL", "T": "OL",
    "EDGE": "EDGE", "DE": "EDGE",
    "DL": "DL", "DT": "DL", "NT": "DL",
    "LB": "LB", "ILB": "LB", "OLB": "LB", "MLB": "LB",
    "CB": "CB", "DB": "CB",
    "S": "S", "FS": "S", "SS": "S", "SAF": "S",
}

# GM-level behavioral multipliers (PART 3 step 5-6)
#   applied as multiplicative tweaks on per-prospect scores for that team's picks
def apply_gm_multipliers(team: str, prospect: pd.Series, score: float) -> float:
    """Return the score adjusted for GM-specific patterns."""
    pos = str(prospect.get("position") or "").upper()
    ras = prospect.get("ras_score")
    age = prospect.get("age")
    pv = prospect.get("positional_value_prior")
    cons = prospect.get("rank")

    if team == "CLE":  # Berry: youth bias — penalize age > 22
        if pd.notna(age) and float(age) > 22:
            score *= 0.9
    elif team == "GB":  # Gutekunst: athleticism bias
        if pd.notna(ras) and float(ras) > 8.0:
            score *= 1.15
    elif team == "PHI":  # Roseman: premium-position tiebreak
        if pd.notna(pv) and float(pv) > 7:
            score *= 1.10
    elif team == "NO":   # Loomis: trades up for impact; boost consensus<20
        if pd.notna(cons) and float(cons) < 20:
            score *= 1.20
    elif team == "KC":   # Veach: premium-pos bias
        if pd.notna(pv) and float(pv) > 7:
            score *= 1.10
    return score


# ===========================================================================
# Pick-specific intel overrides (PART 3)
# ===========================================================================

def get_override_distribution(pick_num: int, history: dict, trades: dict,
                              taken: set, pros: pd.DataFrame) -> Optional[dict]:
    """Return {player_name: probability} for this pick, or None to defer to
    the base model. Filters to players not yet taken; caller normalises.

    Hierarchy:
      1. Hardcoded scripted overrides (trade-scenario specific, cascade
         logic, intel-based) — highest priority when applicable.
      2. Analyst-consensus distribution from 20-mock dataset — applied as
         FALLBACK for any pick without a hardcoded override, and blended
         50/50 with scripted overrides where both exist.
    """

    def avail(cands: dict) -> dict:
        return {p: w for p, w in cands.items() if p not in taken}

    def blend_with_analyst(scripted: dict | None) -> dict | None:
        """Blend the scripted override 50/50 with the analyst-consensus
        distribution for this pick. When scripted is None, returns
        analyst-only. Returns None if neither is available."""
        analyst = analyst_distribution(pick_num, taken, pros_df=pros)
        if scripted is None:
            return analyst or None
        if not analyst:
            return scripted
        merged: dict[str, float] = {}
        total_s = sum(scripted.values()) or 1.0
        total_a = sum(analyst.values()) or 1.0
        for name, w in scripted.items():
            merged[name] = merged.get(name, 0.0) + 0.5 * w / total_s
        for name, w in analyst.items():
            merged[name] = merged.get(name, 0.0) + 0.5 * w / total_a
        return merged

    if pick_num == 1:
        return avail({"Fernando Mendoza": 1.0})

    if pick_num == 2:
        return avail({"David Bailey": 0.55, "Arvell Reese": 0.45})

    if pick_num == 3:
        prev2 = history.get(2)
        # ARI position constraint: qb_urgency >= 0.8, so no WR in top 5.
        # ARI doesn't need LB — their needs are QB/OT/EDGE/CB/WR — so
        # Styles probability here is low (he'd only be taken if Bailey +
        # Reese both gone AND front office reaches for BPA).
        if prev2 == "David Bailey":
            return avail({"Arvell Reese": 0.78, "Francis Mauigoa": 0.14,
                          "Sonny Styles": 0.08})
        if prev2 == "Arvell Reese":
            return avail({"David Bailey": 0.85, "Francis Mauigoa": 0.12,
                          "Sonny Styles": 0.03})

    if pick_num == 4:
        # Scenario B: DAL trades to pick 4
        if trades.get("DAL_trade_scenario") == "B":
            return avail({"Sonny Styles": 0.55, "Caleb Downs": 0.30,
                          "Rueben Bain": 0.15})
        # Post-combine: Styles rose to ~coin-flip with Love at TEN pick 4.
        # Old 0.65/0.25 was pre-combine weighting. Jeremiah 3.0, PFF
        # post-combine split; average is ~0.50/0.40 Love/Styles.
        return avail({"Jeremiyah Love": 0.50, "Sonny Styles": 0.40,
                      "Caleb Downs": 0.10})

    if pick_num == 5:
        if trades.get(5) == "CIN":
            return avail({"Caleb Downs": 0.45, "Rueben Bain": 0.35,
                          "Mansoor Delane": 0.20})
        prev4 = history.get(4)
        if trades.get(4) == "DAL" and prev4 == "Sonny Styles":
            return avail({"Jeremiyah Love": 0.55, "Caleb Downs": 0.30,
                          "Spencer Fano": 0.15})
        # PART 4: conditional Styles branch. Distribution reflects post-
        # combine analyst consensus (~Styles 40% / Downs 30% / rest split).
        # The DYNAMIC BPA + slippage logic (below in compute_base_scores)
        # handles the "Styles should rise if picks 1-4 took someone else"
        # case properly — no slot-specific hardcoding needed.
        if "Sonny Styles" not in taken:
            return avail({"Sonny Styles": 0.40, "Caleb Downs": 0.30,
                          "Jeremiyah Love": 0.18, "Carnell Tate": 0.08,
                          "Francis Mauigoa": 0.04})
        return avail({"Caleb Downs": 0.42, "Jeremiyah Love": 0.28,
                      "Carnell Tate": 0.18, "Francis Mauigoa": 0.08,
                      "Spencer Fano": 0.04})

    if pick_num == 6:
        # PART 3 Scenario A: DAL owns pick 6 via trade with CLE
        if trades.get("DAL_trade_scenario") == "A":
            return avail({"Sonny Styles": 0.55, "Caleb Downs": 0.30,
                          "Rueben Bain": 0.15})
        return avail({"Monroe Freeling": 0.40, "Rueben Bain": 0.35,
                      "Carnell Tate": 0.25})

    if pick_num == 7:
        # PART 4: WAS cascade. If DAL scenario A (took Styles at 6),
        # Tate becomes WAS's top target. Else Styles may still be here.
        styles_avail = "Sonny Styles" not in taken
        if styles_avail:
            return avail({"Sonny Styles": 0.35, "Makai Lemon": 0.28,
                          "Carnell Tate": 0.22, "Rueben Bain": 0.15})
        return avail({"Carnell Tate": 0.45, "Rueben Bain": 0.25,
                      "Caleb Downs": 0.20, "Makai Lemon": 0.10})

    if pick_num == 8:
        return avail({"Rueben Bain": 0.45, "David Bailey": 0.20,
                      "Arvell Reese": 0.10, "Sonny Styles": 0.25})

    if pick_num == 9:
        # PART 3: KC two-R1 scenario — WR or CB plausible
        return avail({"Jordyn Tyson": 0.35, "Rueben Bain": 0.25,
                      "Mansoor Delane": 0.25, "Carnell Tate": 0.10,
                      "Makai Lemon": 0.05})

    # V12: picks 10/11/12 defer to base utility function. Trade checks
    # still apply to preserve CLE/TEN/MIA partner ownership logic.
    if pick_num == 11:
        return None  # MIA / trade-partner all handled via base scoring
    if pick_num == 12:
        return None  # DAL stays -> utility scoring; DAL_traded -> same

    if pick_num == 13:
        return None   # LAR: pure utility scoring

    # V12: picks 14-15 defer to base utility. (14 BAL and 15 TB were
    # analyst-weighted overrides; now governed by needs + GM affinity.)

    if pick_num == 16:
        # Jets pick 16 — Simpson is the "surprise" pick per Cimini (10% cap).
        # Include wider CB fallbacks so Simpson doesn't inflate when the
        # primary WR/CB options are taken earlier.
        return avail({"Omar Cooper Jr.": 0.28, "Jordyn Tyson": 0.22,
                      "Makai Lemon": 0.15, "Jermod McCoy": 0.12,
                      "Ty Simpson": 0.10,
                      "Avieon Terrell": 0.05, "Colton Hood": 0.05,
                      "Chris Johnson": 0.03})

    # V12: picks 17, 18 defer to utility. Pick 19 keeps the cooldown
    # (position-run) branch — that IS state-dependent, not an analyst
    # hardcode. The distribution falls through to the utility otherwise.
    if pick_num == 19 and history.get(18) == "Dillon Thieneman":
        # Cooldown: if MIN just took the top S, CAR shouldn't also take S.
        # Soft penalty is applied in compute_base_scores; here we just
        # defer — the panic/cooldown logic lives in the scoring layer.
        return None

    # V12: picks 20/21/22 defer to utility. Pick 20 still short-circuits
    # under DAL_traded (CLE owns via scenario A) -> utility anyway.
    if pick_num == 20 or pick_num == 21 or pick_num == 22:
        return None

    if pick_num == 23:
        return None   # PHI: pure utility

    # V12: picks 25/26/27/28/29/31 defer to utility. CHI, LAC, HOU, etc.
    # positional gates are enforced via TEAM_PROFILE_OVERRIDES.

    if pick_num == 30 and trades.get("ARI_traded_to_30", False):
        # ARI trades up for Simpson (Kiper spec; QB need confirmed post-Kyler).
        return avail({"Ty Simpson": 0.70, "Francis Mauigoa": 0.20,
                      "Max Iheanachor": 0.10})

    if pick_num == 32:
        if trades.get("SEA_traded_down", False):
            return blend_with_analyst(None)
        # SEA RB/EDGE/CB primary (QB blocked by profile).
        return blend_with_analyst(avail({
            "Jadarian Price": 0.35, "T.J. Parker": 0.30,
            "Colton Hood": 0.20, "Cashius Howell": 0.10,
            "Malachi Lawrence": 0.05
        }))

    # Everything else: fall through to the analyst-consensus distribution.
    # This replaces the old `return None` (base utility scoring) for most
    # of R1. Base scoring still runs if analyst data is empty for this slot.
    return blend_with_analyst(None)


def determine_trades(rng: np.random.Generator) -> dict:
    """Pre-determine trade ownership for this simulation."""
    trades: dict = {}

    # Cowboys trade-up — calibrated against April 2026 analyst consensus
    # (20 mocks, 6 tier-1):
    #   A) 30%: DAL -> CLE (pick 6). Matches 6/20 mocks (tier-1 credible).
    #   B)  8%: DAL -> TEN (pick 4). Speculative; no direct mock support
    #            but plausible alt scenario if CLE demands too much.
    #   C) 62%: no DAL trade.
    r = rng.random()
    if r < 0.30:
        trades[6] = "DAL"
        trades[12] = "CLE"
        trades[20] = "CLE"
        trades["DAL_traded"] = True
        trades["DAL_trade_scenario"] = "A"
    elif r < 0.38:
        trades[4] = "DAL"
        trades[12] = "TEN"
        trades["DAL_traded"] = True
        trades["DAL_trade_scenario"] = "B"

    # CIN trade up to 5: REMOVED. Analyst consensus data (20 mocks from
    # 2026 Mock Draft Data.xlsx) shows ZERO mocks for this scenario. The
    # original 15% was a PDF-hint guess, not data-supported. Tobin/CIN is
    # famously a rarely-trades GM per PDF narrative AND empirical data.
    # Keep a tiny residual for model-breaking scenarios only.
    if rng.random() < 0.03:
        trades[5] = "CIN"
        trades[10] = "NYG"
        trades["CIN_traded"] = True

    # PHI trade up: analyst data shows 2 non-tier-1 mocks (PHI up for
    # Thieneman at P17, PHI up for Miller at P19). Lowered from 20% to 10%
    # and target slot is 17-19 range (not fixed at 18).
    if rng.random() < 0.10:
        trades["PHI_traded_up"] = True
        trades[18] = "PHI"

    # CLE trades up from pick 24 to 20 for Concepcion. Tier-1 credible
    # (Brugler x2), 2/20 mocks (~10%). Conditional: only fires when CLE
    # still owns 24 (i.e., didn't swap it in DAL scenario A).
    if (not trades.get("DAL_traded") or trades.get("DAL_trade_scenario") == "B") \
            and rng.random() < 0.10:
        trades[20] = "CLE"
        trades["CLE_traded_up_to_20"] = True

    # NEW: CLE trades up from pick 24 to 12 for Proctor.
    # Tier-1 credible (Kiper, McShay), 2 mocks. Incompatible with CLE
    # already trading to get pick 6 from DAL scenario A.
    if not trades.get("DAL_traded_scenario_is_A", False) \
            and rng.random() < 0.08:
        trades[12] = "CLE"
        trades["CLE_traded_up_to_12"] = True

    # LAR trade-down from 13. Analyst mocks undercount Snead's behaviour
    # (only 2/20 mocks include a LAR trade) but historical empirical rate
    # under Snead is 50-60% in R1. Calibrate at 40% — a compromise between
    # consensus sparsity and historical pattern.
    if rng.random() < 0.40:
        trades["LAR_traded_down"] = True
        trades[13] = "unknown"

    # SEA trade-down from 32. Schneider has traded out of end-of-R1 in 4 of
    # last 5 drafts. Consensus undercounts (analysts typically pick top-32
    # without modeling the trade). Historical: ~55%.
    if rng.random() < 0.45:
        trades["SEA_traded_down"] = True
        trades[32] = "unknown"

    # MIA trade-down from 11 (Sullivan accumulation preference). Lowered
    # from 20% to 12% — analyst consensus shows minimal mock support.
    if rng.random() < 0.12:
        trades["MIA_traded_down"] = True
        trades[11] = "unknown"

    # ARI trades up from R2 (34) to pick 30 for Simpson. 4/20 mocks = 20%,
    # tier-1 credible (Kiper, McShay, Draft Labs, Solak).
    if rng.random() < 0.20:
        trades[30] = "ARI"
        trades["ARI_traded_to_30"] = True

    # Phase 2 (#6): known_unknowns as scenario branches. Probabilities come
    # from league-synthesis narrative + market signals; these flip a single
    # bit per sim that downstream logic consults.
    #
    # AJ Brown trade scenario — PHI sheds Brown, becomes WR-hunting at 23.
    # Base rate: Athletic/Pelissero reports put this at ~20% through April.
    trades["aj_brown_traded"] = rng.random() < 0.20
    # Dexter Lawrence impasse — 50/50 resolved by draft day. If trade
    # executes (traded=True), NYG IDL need spikes to urgent; if retained
    # (traded=False), IDL drops out of R1 need set.
    trades["lawrence_traded"] = rng.random() < 0.50
    # NYJ QB scenario at pick 2 — Mougey has hinted at dev QB; handled in
    # override table but flagged here for analytics.
    trades["nyj_qb_at_2"] = rng.random() < 0.10

    return trades


_VALID_TEAM_RE = {"ARI","ATL","BAL","BUF","CAR","CHI","CIN","CLE","DAL",
                  "DEN","DET","GB","HOU","IND","JAX","KC","LAC","LAR",
                  "LV","MIA","MIN","NE","NO","NYG","NYJ","PHI","PIT",
                  "SF","SEA","TB","TEN","WAS"}


def apply_trade_team_swaps(picks: list[dict], trades: dict) -> list[dict]:
    """Rewrite team ownership on picks list per the trades dict. Only applies
    true team-code swaps; sentinel values ('unknown', 'traded', etc.) are
    tracked in `trades` but don't alter the listed team (base model will still
    process with the original team's profile — an acceptable approximation)."""
    picks = [dict(p) for p in picks]
    for pk, new_team in trades.items():
        if (isinstance(pk, int)
                and isinstance(new_team, str)
                and new_team in _VALID_TEAM_RE):
            for p in picks:
                if p["pick_number"] == pk:
                    p["team"] = new_team
    return picks


# ===========================================================================
# Base scoring (when override is None or yields empty available set)
# ===========================================================================

def compute_base_scores(prospects: pd.DataFrame, pick: dict,
                        top3_needs: dict, qb_urgency_map: dict,
                        recent_pick_positions: list[str],
                        final_score_col: str = "final_score",
                        return_components: bool = False,
                        rng: Optional[np.random.Generator] = None,
                        history: Optional[dict] = None,
                        trades: Optional[dict] = None):
    team = pick["team"]
    pick_num = int(pick["pick_number"])
    round_num = int(pick.get("round", 1))

    # Round-scaled BPA/need weighting. Analyst-consensus-inspired pattern:
    # at the top of R1 teams draft mostly BPA; by R4+ picks are nearly all
    # need-driven (fills roster holes with whoever's available there).
    # Default CSV weights are ~0.5/0.5 across all rounds which under-models
    # this shift. Override here rather than edit the CSV so the change is
    # reversible and auditable in one place.
    _ROUND_BPA_NEED = {
        1: (0.55, 0.45),   # R1: slight BPA lean but teams DO fill needs
        2: (0.45, 0.55),   # R2: need starts to dominate
        3: (0.35, 0.65),   # R3: clear need-driven
        4: (0.30, 0.70),   # R4: need + scheme fit
        5: (0.25, 0.75),   # R5-7: pure need + specialty
        6: (0.25, 0.75),
        7: (0.20, 0.80),
    }
    bpa_w, need_w = _ROUND_BPA_NEED.get(
        round_num, (float(pick["bpa_weight"]), float(pick["need_weight"]))
    )

    final_sc = prospects[final_score_col].clip(lower=0, upper=728).fillna(728)
    bpa_term = (1 - final_sc / 728.0) * bpa_w

    pos_canon = prospects["_needs_pos"]

    # Build the effective needs list for this team, honoring profile overrides
    profile = get_team_profile(team)
    if profile.get("needs_override") is not None:
        team_needs_list = list(profile["needs_override"])
    else:
        team_needs_list = top3_needs.get(team, [])
    blocked = profile.get("r1_blocked_positions", set())

    # Phase 1 (#2): include PDF-derived latent needs at half weight. Latent
    # positions are 2026-non-urgent but 2027+ cliffs (e.g. SF OT with T.
    # Williams at 38). They score 0.5 instead of 1.0 in need_match so they're
    # realistic fallbacks when the primary board has cleared.
    latent = {p for p in (profile.get("_agent_latent_needs") or {})
              if p not in blocked and p not in team_needs_list}

    # Phase 1 (#1): scheme-premium positions get an additive +0.25 on
    # need_match when they're already a need. A CB-needy team whose scheme
    # also prefers CBs (TEN Cover-3, CIN Golden) reinforces the need;
    # non-premium-scheme CB needs get no bonus.
    scheme_premium = set(
        profile.get("_agent_scheme", {}).get("premium", []) or []
    )

    need_match = pos_canon.isin(team_needs_list).astype(float)
    # Latent positions contribute 0.5 (BEFORE elite-override logic runs).
    if latent:
        latent_mask = pos_canon.isin(latent)
        need_match = need_match.where(~latent_mask, 0.5)
    # Scheme-premium bonus on top of need_match (only for positions that
    # are already a team need, so we don't inflate non-needs).
    if scheme_premium:
        scheme_bonus_mask = pos_canon.isin(scheme_premium) & pos_canon.isin(team_needs_list)
        need_match = need_match.where(~scheme_bonus_mask, need_match + 0.25)

    # Phase 2 (#5): cascade rules. If an earlier pick in this sim already
    # consumed the trigger position, damp our need_match for the dependent
    # position. Example: MIN at 18 takes a S -> CAR at 19 has S need halved.
    if history is not None and pick_num is not None:
        for rule in _CASCADE_RULES:
            if (rule.get("dependent_team") != team
                    or rule.get("dependent_pick") != pick_num):
                continue
            trig_team = rule.get("trigger_team")
            trig_pick = rule.get("trigger_pick")
            trig_pos_needs = POS_TO_NEEDS.get(rule.get("trigger_position", ""),
                                              rule.get("trigger_position", ""))
            dep_pos_needs = POS_TO_NEEDS.get(rule.get("dependent_position", ""),
                                             rule.get("dependent_position", ""))
            # Look up what was taken at the trigger pick.
            taken_at_trigger = history.get(trig_pick)
            if not taken_at_trigger:
                continue
            prior_row = prospects[prospects["player"] == taken_at_trigger]
            if prior_row.empty:
                continue
            prior_pos = str(prior_row.iloc[0]["_needs_pos"])
            if prior_pos == trig_pos_needs:
                damp_mask = pos_canon == dep_pos_needs
                need_match = need_match.where(~damp_mask,
                                              need_match * CASCADE_NEED_DAMPING)

    # Phase 4 (#9): age cliffs — a high-severity age cliff (starter 35+ at
    # WR, 37+ at OT, etc.) boosts need_match at that position. Lower impact
    # than an injury (+0.2 vs +0.3) because a cliff is a 2027 problem, not
    # a Week-1 starter hole.
    age_cliffs = profile.get("_agent_age_cliffs") or []
    if age_cliffs:
        cliff_positions: set[str] = set()
        for c in age_cliffs:
            if c.get("severity") != "high":
                continue
            raw = str(c.get("position", "")).upper()
            canon = POS_TO_NEEDS.get(raw, raw)
            cliff_positions.add(canon)
        if cliff_positions:
            cliff_mask = pos_canon.isin(cliff_positions) & pos_canon.isin(team_needs_list)
            need_match = need_match.where(~cliff_mask, need_match + 0.2)

    # Phase 4 (#11): previous-year same-position R1 repeat penalty. If the
    # team took a position in 2025 R1, their 2026 R1 need for that position
    # drops 40% (rarely do teams double-dip consecutively).
    prev_alloc = profile.get("_agent_prev_year_alloc") or {}
    prev_2025_r1_positions: set[str] = set()
    for entry in prev_alloc.get("2025_r1", []):
        raw = str(entry.get("pos", "")).upper()
        canon = POS_TO_NEEDS.get(raw, raw)
        prev_2025_r1_positions.add(canon)
    if prev_2025_r1_positions:
        repeat_mask = pos_canon.isin(prev_2025_r1_positions)
        need_match = need_match.where(~repeat_mask, need_match * 0.6)

    # Phase 3 (#10): high-severity roster injuries boost need_match on
    # that position. Pulled from narrative ("Bosa ACL", "Trapilo OT ACL",
    # etc.). Keeps the extraction cheap — we look up the injured player's
    # position from the injury phrase itself (it usually contains it).
    injury_flags = profile.get("_agent_injury_flags") or []
    if injury_flags:
        INJURY_POS_RX = re.compile(r"\b(QB|RB|WR|TE|OT|OL|IOL|G|C|EDGE|IDL|DT|DL|LB|CB|S|DB)\b")
        boosted_positions: set[str] = set()
        for inj in injury_flags:
            if inj.get("severity") != "high":
                continue
            m = INJURY_POS_RX.search(f"{inj.get('player','')} {inj.get('injury','')}")
            if not m:
                continue
            raw_pos_inj = m.group(1)
            canon = POS_TO_NEEDS.get(raw_pos_inj, raw_pos_inj)
            boosted_positions.add(canon)
        if boosted_positions:
            inj_mask = pos_canon.isin(boosted_positions) & pos_canon.isin(team_needs_list)
            need_match = need_match.where(~inj_mask, need_match + 0.3)

    # Phase 2 (#6): scenario-driven need adjustments from trades dict.
    if trades is not None:
        # AJ Brown traded -> PHI picks up a WR urgency at 23.
        if team == "PHI" and trades.get("aj_brown_traded"):
            wr_mask = pos_canon == "WR"
            need_match = need_match.where(~wr_mask,
                                          need_match.clip(lower=1.0) + 0.5)
        # Dexter Lawrence traded -> NYG IDL need spikes (otherwise drops).
        if team == "NYG":
            idl_mask = pos_canon == "DL"   # IDL maps to DL in POS_TO_NEEDS
            if trades.get("lawrence_traded"):
                need_match = need_match.where(~idl_mask,
                                              need_match.clip(lower=1.0) + 0.5)
            else:
                # Lawrence stays: NYG has no R1 IDL need.
                need_match = need_match.where(~idl_mask, 0.0)

    # Apply hard block (BUG 5/6): NE blocks QB, CHI blocks WR+QB, etc.
    if blocked:
        need_match = need_match.where(~pos_canon.isin(blocked), 0.0)

    # Effective QB urgency (profile override wins over team_context)
    qb_urg_eff = profile.get("qb_urgency",
                             qb_urgency_map.get(team, 1.0))
    if qb_urg_eff == 0.0:
        need_match = need_match.where(pos_canon != "QB", 0.0)

    # ARI-style position constraint: qb_urgency >= 0.8 and pick <= 5 -> no WR
    if qb_urg_eff >= 0.8 and pick_num <= 5:
        need_match = need_match.where(pos_canon != "WR", 0.0)

    # FIX 8: elite BPA override — a consensus top-ELITE_THRESHOLD player
    # should not be zeroed by need_match=0. Elite players get drafted
    # regardless of whether the team "officially" needs the position.
    cons = prospects["rank"]
    elite_mask = cons <= ELITE_CONS_RANK_THRESHOLD
    need_match = need_match.where(~elite_mask, need_match.clip(lower=1.0))

    # BUG 1 FIX — scarcity multiplier only fires when team actually needs
    # that position. No more global "WRs get a 1.3x bonus on every pick".
    raw_pos = prospects["position"].fillna("").astype(str).str.upper()
    # cons already computed above
    is_team_need = pos_canon.isin(team_needs_list) & ~pos_canon.isin(blocked)

    scarcity = pd.Series(1.0, index=prospects.index)
    deep_mask = raw_pos.isin(DEEP_CLASS)
    edge_protected = (raw_pos == "EDGE") & (cons <= DEEP_EDGE_PROTECTION_THRESHOLD)
    # Deep-class penalty only where the team has need (else it's a no-op anyway
    # since need_match=0 already zeros the term; but clean to set to 1.0)
    scarcity = scarcity.where(~(deep_mask & ~edge_protected) | ~is_team_need,
                              DEEP_MULT)
    # Thin-class boost only for need matches (BUG 1)
    thin_mask = raw_pos.isin(THIN_CLASS) & is_team_need
    scarcity = scarcity.where(~thin_mask, THIN_MULT)

    panic_mult = pd.Series(1.0, index=prospects.index)
    if len(recent_pick_positions) >= 2 and recent_pick_positions[-1] == recent_pick_positions[-2]:
        hot_pos = recent_pick_positions[-1]
        panic_mult = panic_mult.where(pos_canon != hot_pos, 1.5)

    need_term = need_match * need_w * scarcity * panic_mult

    visit_flag = prospects["_visit_set"].apply(lambda s: 1 if team in s else 0)
    # Phase 7: if multiple analyst sources confirm the visit, bump the
    # weight from 0.15 to 0.22 (≥2 sources) or 0.28 (≥3). Single-source
    # visits keep the 0.15 base.
    def _multi_source_visit_weight(player_name: str) -> float:
        agg = _ANALYST_AGG.get(player_name, {}).get("visits", {})
        per_src = agg.get("per_source", {})
        hits = sum(1 for s in per_src.values()
                   if team in (s.get("teams") or []))
        if hits >= 3:
            return 0.28
        if hits >= 2:
            return 0.22
        return 0.15
    visit_weight = prospects["player"].apply(_multi_source_visit_weight)
    visit_term = visit_flag * visit_weight

    intel_flag = (prospects["intel_top_team"] == team).astype(float)
    intel_term = intel_flag * prospects["intel_link_max"].fillna(0) * 0.10

    score = bpa_term + need_term + visit_term + intel_term

    # Round-scaled medical penalty. Analyst logic: R1 teams live with minor
    # injury flags for talent; by R3-4, a medical flag drops a guy 30+
    # picks. Use has_injury_flag (40% of board has one) as the boolean and
    # scale by round. NOTE: R1 = -0.02, R2 = -0.08, R3 = -0.15, R4+ = -0.20.
    if "has_injury_flag" in prospects.columns:
        injury = prospects["has_injury_flag"].fillna(0).astype(float)
        round_penalty = {1: 0.02, 2: 0.08, 3: 0.15, 4: 0.20,
                         5: 0.20, 6: 0.25, 7: 0.25}.get(round_num, 0.05)
        score = score - (injury * round_penalty)

    # Visit-count boost — scales harder in later rounds. A Day-3 prospect
    # with 4+ top-30 visits is a strong team-interest signal (teams don't
    # waste late visits on players they don't want). Separate from the
    # team-specific visit_term above which only fires when THIS team
    # visited.
    if "visit_count" in prospects.columns:
        vcount = prospects["visit_count"].fillna(0).clip(upper=10)
        round_visit_wt = {1: 0.005, 2: 0.010, 3: 0.015, 4: 0.020,
                          5: 0.025, 6: 0.030, 7: 0.030}.get(round_num, 0.010)
        score = score + vcount * round_visit_wt

    # FIX 9: positional value multiplier on the whole score (premium positions
    # go higher; non-premium positions get discounted except for top-1
    # players at their raw position code, which reduce to -0.05).
    pv_mult = raw_pos.map(POS_VALUE_MULT).fillna(1.0)
    top1_idx = prospects.groupby("position")["rank"].idxmin()
    is_top1_at_position = prospects.index.isin(top1_idx.values)
    non_premium_top1 = is_top1_at_position & raw_pos.isin(NON_PREMIUM_RAW)
    pv_mult = pv_mult.where(~non_premium_top1, 0.95)
    score = score * pv_mult

    # Proximity constraint (general)
    far = cons > (3 * pick_num)
    score = score.where(~far, score * 0.5)

    # FIX 10: reach prevention — if a player's consensus rank is >N picks
    # BELOW the current pick number, halve their score. Late-first allows
    # slightly wider reach than mid/early; premium-position reaches with
    # confirmed need AND visit are exempted.
    visit_flag_series = prospects["_visit_set"].apply(lambda s: 1 if team in s else 0)
    premium_need = (raw_pos.isin({"QB", "OT"})
                    & is_team_need
                    & (visit_flag_series == 1))
    gap_threshold = LATE_PICK_REACH_THRESHOLD if pick_num >= 21 else REACH_GAP_THRESHOLD
    reach_mask = ((pick_num - cons) < -gap_threshold) & ~premium_need
    score = score.where(~reach_mask, score * 0.5)

    # NEW: scaled slippage boost. A top-15 consensus prospect available
    # past their expected slot gets a multiplicative boost proportional to
    # how far they've slipped. Formula: 1.0 + 0.06 × slots_slipped, capped
    # at 1.55×. So Styles (cons=5) at pick 5 gets 1.0 (no slip), at pick 8
    # gets 1.18×, at pick 12 gets 1.42×, at pick 20+ caps at 1.55×. This
    # encodes the "falling knife" dynamic GMs describe when they say they
    # "couldn't pass on him at this value." Hard-blocked positions exempt.
    slippage = pick_num - cons
    elite_slip = (cons <= 15) & (slippage > 0)
    if blocked:
        elite_slip = elite_slip & ~pos_canon.isin(blocked)
    slip_boost = (1.0 + 0.06 * slippage).clip(upper=1.55)
    score = score.where(~elite_slip, score * slip_boost)

    # GLOBAL HARD CAP: prevent the base model from surfacing obvious reach
    # candidates. Overrides (specific intel) bypass this path entirely.
    cap = cap_threshold(pick_num)
    over_cap = cons > cap
    score = score.where(~over_cap, -1e6)

    # GM positional affinity multiplier (from compute_gm_allocation.py).
    # A 10% over-allocation at a position -> multiplier ~1.30 (clipped to 1.25).
    gm_map = GM_AFFINITY_CACHE
    gm_group = raw_pos.map(POS_TO_GM_GROUP).fillna("OTHER")
    gm_deltas = gm_group.apply(lambda g: gm_map.get((team, g), 0.0))
    gm_mult = (1.0 + gm_deltas * GM_AFFINITY_SCALE).clip(
        lower=GM_AFFINITY_MIN, upper=GM_AFFINITY_MAX)
    score = score * gm_mult

    # Global medical penalty (e.g. McCoy ACL)
    med_mult = prospects["player"].map(MEDICAL_PENALTIES).fillna(1.0)
    score = score * med_mult

    # Post-combine risers (e.g. Styles) and positional-scarcity top-1s
    # (where gap to next-at-position is large enough to matter).
    boost_mult = prospects["player"].map(POST_COMBINE_BOOSTS).fillna(1.0)
    scarcity_map = _compute_position_scarcity(prospects)
    scarcity_mult = prospects["player"].map(scarcity_map).fillna(1.0)
    score = score * boost_mult * scarcity_mult

    # Phase 5 (#7): cap-constraint tier modifies QB/premium-position risk.
    # A cap-tight team (CLE, LAR, MIA, NO, MIN) is LESS likely to take
    # high-APY rookie QBs unless urgency is forced. Conversely, cap-flush
    # teams (LV, NYJ, TEN, ARI, NE) accept rookie-scale splash picks.
    cap_tier = profile.get("_agent_cap_tier", "normal")
    if cap_tier == "tight":
        # Suppress QB unless qb_urgency forces it; modest penalty on WR/RB
        # luxury picks.
        qb_mask = pos_canon == "QB"
        if qb_urg_eff < 0.5:
            score = score.where(~qb_mask, score * 0.7)
        luxury_mask = raw_pos.isin({"RB", "TE"})
        score = score.where(~luxury_mask, score * 0.92)
    elif cap_tier == "flush":
        # Rookie-scale premium picks slightly boosted
        premium_mask = raw_pos.isin({"QB", "EDGE", "OT", "CB"})
        score = score.where(~premium_mask, score * 1.05)

    # Phase 6 (#13): scheme-fit multiplier. Poor fit (<0.5) -> 0.9x,
    # strong fit (==1.0 AND position is a team need) -> 1.04x boost. Rules
    # only apply to positions with explicit scheme criteria; everyone else
    # gets 1.0 (neutral).
    scheme_type = profile.get("_agent_scheme", {}).get("type", "")
    if scheme_type and scheme_type != "default":
        fit = compute_scheme_fit(prospects, scheme_type)
        fit_mult = pd.Series(1.0, index=prospects.index)
        fit_mult = fit_mult.where(fit >= 0.5, 0.90)   # poor fit penalty
        fit_mult = fit_mult.where(~(fit >= 1.0) | ~pos_canon.isin(team_needs_list), 1.04)
        score = score * fit_mult

    # Phase 5 (#8): coach-prospect connection bonus. If a prospect attended
    # a college where this team's HC has coached, small +8% boost.
    hc_stints = set(profile.get("_agent_hc_college_stints") or [])
    if hc_stints:
        prospect_colleges = prospects.get("college",
                                          pd.Series("", index=prospects.index))
        prospect_colleges = prospect_colleges.fillna("").astype(str)
        conn_mask = prospect_colleges.apply(
            lambda c: any(stint.lower() in c.lower() for stint in hc_stints)
                      if c else False
        )
        score = score.where(~conn_mask, score * 1.08)

    # Phase 1 (#3): team-specific predictability noise. LOW-predictability
    # teams see wider score noise, HIGH-predictability narrower. Only fires
    # when a live rng is passed (i.e. simulate_one calls it); test/introspect
    # callers with rng=None get deterministic scores.
    if rng is not None:
        pred_enum = profile.get("_agent_predictability") or ""
        mult = PREDICTABILITY_NOISE_MULT.get(pred_enum, 1.0)
        if mult != 1.0:
            sigma = PREDICTABILITY_SCORE_SIGMA * mult
            noise_factor = 1.0 + rng.normal(0, sigma, size=len(prospects))
            # Clamp to avoid negative scores flipping the argmax
            noise_factor = np.clip(noise_factor, 0.5, 1.5)
            score = score * noise_factor

    if return_components:
        components = {
            "bpa": bpa_term.copy(),
            "need": need_term.copy(),
            "visit": visit_term.copy(),
            "intel": intel_term.copy(),
            "pv_mult": pv_mult.copy(),
            "gm_affinity": gm_mult.copy(),
            "med_mult": med_mult.copy(),
            "score_final": score.copy(),
        }
        return score, components

    # FIX 1: HARD BLOCK — positions explicitly blocked (QB locked teams,
    # r1_blocked_positions like CHI-WR / NE-QB) get a 0.05 multiplier so
    # BPA reach + premium-position multiplier can't promote them anyway.
    hard_block_positions = set(blocked) if blocked else set()
    if qb_urg_eff == 0.0:
        hard_block_positions.add("QB")
    if hard_block_positions:
        # Strict disqualification: worse than the cap-violation floor (-1e6),
        # so a locked-QB team will never land on a QB unless every other
        # candidate is also disqualified (vanishingly rare).
        block_mask = pos_canon.isin(hard_block_positions)
        score = score.where(~block_mask, -1e9)

    # GM multipliers (vectorised via apply — costs ms, fine for 32 picks × 500 sims)
    if team in ("CLE", "GB", "PHI", "NO", "KC"):
        score = pd.Series(
            [apply_gm_multipliers(team, prospects.iloc[i], float(score.iloc[i]))
             for i in range(len(prospects))],
            index=prospects.index,
        )
    return score


# ===========================================================================
# Bilateral trade negotiation (PART 2)
# ===========================================================================

def try_bilateral_trade(current_idx: int, picks: list[dict],
                        prospects: pd.DataFrame, top3_needs: dict,
                        scores_avail: pd.Series, rng: np.random.Generator,
                        trade_log: list) -> Optional[int]:
    """
    Returns the new team owner of picks[current_idx] if a trade fires,
    else None. The trade partner is a later pick-holder with high
    trade_up_rate AND need at the top-available-player's canonical
    position. We value trades via Fitzgerald-Spielberger.
    """
    if scores_avail.empty:
        return None
    top_idx = scores_avail.idxmax()
    top_pos = prospects.loc[top_idx, "_needs_pos"]

    pick_now = picks[current_idx]
    value_now = FITZ_VALUES.get(pick_now["pick_number"], 100)

    best_partner = None
    best_rate = -1.0
    best_idx = None
    for j in range(current_idx + 1, len(picks)):
        p2 = picks[j]
        # Prefer empirical 2021-2025 trade-up rate for this partner team;
        # fall back to whatever the CSV set on the pick (legacy).
        emp_up, _, emp_has_signal = empirical_team_rates(p2["team"])
        csv_up = p2.get("trade_up_rate") or 0
        tur = emp_up if emp_has_signal else csv_up
        if tur < 0.4:
            continue
        if top_pos not in top3_needs.get(p2["team"], []):
            continue
        # Fitzgerald offer: their pick value + 18% premium (academic studies
        # of 2006-2022 R1 trade-ups show ~15-25% over chart value).
        offer = FITZ_VALUES.get(p2["pick_number"], 50) * 1.18
        if offer < value_now * 0.85:   # allow a slightly larger gap with premium
            continue
        if tur > best_rate:
            best_rate = tur
            best_partner = p2["team"]
            best_idx = j
    if best_partner is None:
        return None
    # Swap teams
    old_team = pick_now["team"]
    picks[current_idx]["team"] = best_partner
    picks[best_idx]["team"] = old_team
    trade_log.append({
        "pick_number": pick_now["pick_number"],
        "from_team": old_team, "to_team": best_partner,
        "target_player": prospects.loc[top_idx, "player"],
        "target_position": prospects.loc[top_idx, "position"],
    })
    return best_partner


# ===========================================================================
# Simulation driver
# ===========================================================================

def simulate_one(pros: pd.DataFrame, picks_template: list[dict],
                 top3_needs: dict, qb_urgency_map: dict,
                 rng: np.random.Generator,
                 forced_picks: dict[int, str] | None = None,
                 forced_trades: dict | None = None):
    """Run a single simulation.

    forced_picks: {pick_number: player_name} — forces a specific player at
        that slot. Overrides all other logic (override dist, trade check,
        base scoring). Used by the mock-draft builder to let users pin
        specific picks and have downstream adapt.
    forced_trades: pre-determined trade dict that replaces the random one
        from determine_trades(). Useful when the user wants a specific
        trade scenario in their mock."""
    trades = forced_trades if forced_trades is not None else determine_trades(rng)
    picks = apply_trade_team_swaps(picks_template, trades)
    forced_picks = forced_picks or {}

    local = pros.copy()

    # Log scripted team swaps so they appear in the trades JSON alongside
    # dynamic bilateral trades. Without this, a scenario like DAL→6 (40%)
    # would silently change ownership but never show up in the 'Trade X%'
    # badge on the UI.
    _scripted_trade_log: list = []
    _orig_team_by_pick = {p["pick_number"]: p["team"] for p in picks_template}
    for pick_num, pick_obj in [(p["pick_number"], p) for p in picks]:
        if pick_num in _orig_team_by_pick and pick_obj["team"] != _orig_team_by_pick[pick_num]:
            _scripted_trade_log.append({
                "pick_number":      pick_num,
                "from_team":        _orig_team_by_pick[pick_num],
                "to_team":          pick_obj["team"],
                "target_player":    "",        # unknown at pre-sim time
                "target_position":  "",
                "scripted":         True,
            })
    # BUG 2 FIX: base noise + a second noise draw we switch to for late picks
    local["final_score_noised_early"] = (
        local["final_score"].fillna(500)
        + rng.normal(0, NOISE_STD_FINAL_SCORE, size=len(local)))
    local["final_score_noised_late"] = (
        local["final_score"].fillna(500)
        + rng.normal(0, NOISE_STD_LATE_PICKS, size=len(local)))

    taken: set[int] = set()
    taken_names: set[str] = set()
    history: dict = {}
    trade_log: list = list(_scripted_trade_log)
    recent_positions: list[str] = []

    for i, pick in enumerate(picks):
        pn = pick["pick_number"]
        final_score_col = ("final_score_noised_late"
                           if pick["pick_number"] >= 17
                           else "final_score_noised_early")

        # FORCED PICK — user pinned this slot in the mock-draft builder.
        # Take their player and move on; downstream picks adapt because the
        # forced player is marked `taken`.
        if pn in forced_picks:
            forced_name = forced_picks[pn]
            match = local[local["player"] == forced_name]
            if not match.empty and forced_name not in taken_names:
                idx = match.index[0]
                taken.add(idx)
                taken_names.add(forced_name)
                history[pn] = forced_name
                recent_positions.append(local.loc[idx, "_needs_pos"])
                continue
            # If the forced player name doesn't exist in prospects or was
            # already taken, fall through to normal scoring.

        # LAZY SCORING — compute_base_scores is expensive (pandas ops on every
        # prospect row). Defer it until we actually need scores. For picks
        # governed by a strong intel override with no trade firing, we can
        # skip this entirely.
        _scores = [None]   # list-wrap so inner code can mutate
        def get_scores():
            if _scores[0] is None:
                _scores[0] = compute_base_scores(
                    local, pick, top3_needs, qb_urgency_map, recent_positions,
                    final_score_col=final_score_col,
                    rng=rng, history=history, trades=trades,
                )
            return _scores[0]

        def invalidate_scores():
            _scores[0] = None

        # 1) Override distribution?
        dist = get_override_distribution(pn, history, trades, taken_names,
                                         local)

        # 2) Check for bilateral trade. scripted_already short-circuits the
        # trade check (avoids double-swapping scripted trades). Trade rate
        # math is cheap, so we always compute it — but we only fetch scores
        # if the dice actually roll a trade.
        scripted_already = (
            pick["pick_number"] in trades
            or trades.get(f"{pick['team']}_traded_down")
        )
        team_profile = get_team_profile(pick["team"])
        constraints = set(team_profile.get("_agent_hard_constraints") or [])

        if scripted_already:
            effective_trade_rate = 0.0
        else:
            base_trade_rate = empirical_pick_rate(pick["pick_number"])
            _, team_down_rate, has_signal = empirical_team_rates(pick["team"])
            blended = ((base_trade_rate + team_down_rate) / 2
                       if has_signal else base_trade_rate)
            pdf_trade_tier = team_profile.get("_agent_trade_probability", {})
            tier_rate = TRADE_TIER_RATE.get(
                pdf_trade_tier.get("trade_down_tier", ""), 0.0)
            effective_trade_rate = max(blended, tier_rate)

            # DYNAMIC TRADE BOOST — QB cascade, tier exhaustion, leapfrog.
            # Model reasons about the current board state to decide whether
            # this pick is a juicy trade-down target. Multiplier applied
            # BEFORE hard-constraint caps.
            remaining = picks[i + 1:]
            dynamic_boost = compute_dynamic_trade_boost(
                current_pick=pick,
                remaining_picks=remaining,
                history=history,
                taken_names=taken_names,
                pros=local,
                top3_needs=top3_needs,
            )
            effective_trade_rate *= dynamic_boost

            if "no_trade_down" in constraints:
                effective_trade_rate = 0.0
            elif "rarely_trades" in constraints or "no_r1_movement_streak" in constraints:
                effective_trade_rate = min(effective_trade_rate, 0.05)
            elif "stay_put_stated" in constraints:
                effective_trade_rate = min(effective_trade_rate, 0.10)
            # Cap at 0.95 so no pick is a 100% trade-certainty
            effective_trade_rate = min(effective_trade_rate, 0.95)

        if effective_trade_rate > 0 and rng.random() < effective_trade_rate:
            # Trade dice rolled — now we need scores for partner selection.
            scores_avail = get_scores()[~local.index.isin(taken)]
            if not scores_avail.empty:
                new_team = try_bilateral_trade(i, picks, local, top3_needs,
                                               scores_avail, rng, trade_log)
                if new_team is not None:
                    pick = picks[i]
                    invalidate_scores()   # team changed, recompute needed

        # 3) Apply intel override if available (fast path).
        if dist:
            for pen_name, mult in MEDICAL_PENALTIES.items():
                if pen_name in dist:
                    dist[pen_name] = dist[pen_name] * mult
            for boost_name, mult in POST_COMBINE_BOOSTS.items():
                if boost_name in dist:
                    dist[boost_name] = dist[boost_name] * mult
            total = sum(dist.values())
            if total > 0:
                probs = np.array(list(dist.values())) / total
                names = list(dist.keys())
                chosen = rng.choice(names, p=probs)
                match = local[local["player"] == chosen]
                if not match.empty:
                    idx = match.index[0]
                    taken.add(idx)
                    taken_names.add(chosen)
                    history[pn] = chosen
                    recent_positions.append(local.loc[idx, "_needs_pos"])
                    continue   # Skip base-model scoring entirely.

        # 4) Base-model pick (only reached when dist was None or empty).
        scores_avail = get_scores()[~local.index.isin(taken)]
        if scores_avail.empty:
            break
        winner_idx = scores_avail.idxmax()
        winner_name = local.loc[winner_idx, "player"]
        taken.add(winner_idx)
        taken_names.add(winner_name)
        history[pn] = winner_name
        recent_positions.append(local.loc[winner_idx, "_needs_pos"])

    # Backfill target_player on scripted trades now that picks are resolved.
    for t in trade_log:
        if t.get("scripted") and not t.get("target_player"):
            player = history.get(t["pick_number"])
            if player:
                t["target_player"] = player
                row = local[local["player"] == player]
                if not row.empty:
                    t["target_position"] = str(row["position"].iloc[0])

    return history, trade_log, picks


def load_data():
    pros = pd.read_csv(PROS_CSV)
    preds = pd.read_csv(PRED_CSV)
    pros = pros.merge(preds[["player", "final_score", "model_pred"]],
                      how="left", on="player")

    team_ctx = pd.read_csv(TEAM_CTX)
    needs = pd.read_csv(TEAM_NEEDS)

    top3_needs: dict = {}
    for t, sub in needs.groupby("team"):
        top3_needs[t] = sub.sort_values("need_rank").head(3)["position"].tolist()

    qb_urgency_map = dict(zip(team_ctx["team"], team_ctx["qb_urgency"]))

    def parse_visits(s):
        if not isinstance(s, str) or not s.strip():
            return set()
        out = set()
        nick_map = {"49ers": "SF", "Bears": "CHI", "Bengals": "CIN", "Bills": "BUF",
                    "Broncos": "DEN", "Browns": "CLE", "Buccaneers": "TB",
                    "Cardinals": "ARI", "Chargers": "LAC", "Chiefs": "KC",
                    "Colts": "IND", "Commanders": "WAS", "Cowboys": "DAL",
                    "Dolphins": "MIA", "Eagles": "PHI", "Falcons": "ATL",
                    "Giants": "NYG", "Jaguars": "JAX", "Jets": "NYJ",
                    "Lions": "DET", "Packers": "GB", "Panthers": "CAR",
                    "Patriots": "NE", "Raiders": "LV", "Rams": "LAR",
                    "Ravens": "BAL", "Saints": "NO", "Seahawks": "SEA",
                    "Steelers": "PIT", "Texans": "HOU", "Titans": "TEN",
                    "Vikings": "MIN"}
        for part in s.split(","):
            p = part.strip()
            if p in nick_map:
                out.add(nick_map[p])
            elif 2 <= len(p) <= 3:
                out.add(p.upper())
        return out

    # Build both derived columns and attach via concat to avoid the
    # "DataFrame is highly fragmented" warning from pandas when the
    # prospects frame has accumulated many prior assignments.
    derived = pd.DataFrame({
        "_visit_set": pros["visited_teams"].apply(parse_visits),
        "_needs_pos": pros["position"].map(POS_TO_NEEDS).fillna("OTHER"),
    }, index=pros.index)
    pros = pd.concat([pros, derived], axis=1).copy()

    return pros, team_ctx, needs, top3_needs, qb_urgency_map


def main():
    global GM_AFFINITY_CACHE
    GM_AFFINITY_CACHE = load_gm_affinity()
    pros, team_ctx, _, top3_needs, qb_urgency_map = load_data()
    r1 = team_ctx[team_ctx["round"] == 1].sort_values("pick_number")
    picks_template = r1.to_dict(orient="records")

    rng = np.random.default_rng(RNG_SEED)
    landing: dict = {}        # player -> {pick_slot: count}
    team_at_slot: dict = {}   # player -> {pick_slot: {team: count}}
    all_trades: list = []     # accumulated trade events

    print(f"Running {N_SIMULATIONS} game-theoretic simulations...")
    for sim in range(N_SIMULATIONS):
        history, trades_this, _ = simulate_one(
            pros, picks_template, top3_needs, qb_urgency_map, rng)
        for pn, player in history.items():
            landing.setdefault(player, {})
            landing[player][pn] = landing[player].get(pn, 0) + 1
        # Track team by finding the team that actually held the pick in the sim
        # (picks list was mutated; we reconstruct from current picks_template by sim)
        for trade in trades_this:
            all_trades.append(trade)
        # Adaptive progress cadence so small runs still show motion — emit
        # at every sim when N <= 20, every 5 when N <= 100, every 25 when
        # N <= 500, every 100 for larger runs.
        if N_SIMULATIONS <= 20:
            cadence = 1
        elif N_SIMULATIONS <= 100:
            cadence = 5
        elif N_SIMULATIONS <= 500:
            cadence = 25
        else:
            cadence = 100
        if (sim + 1) % cadence == 0 or (sim + 1) == N_SIMULATIONS:
            print(f"  ...{sim + 1}/{N_SIMULATIONS}", flush=True)

    # Reconstruct team-at-slot tallies by re-running a lightweight pass of
    # the owning team per simulation. Simpler: re-store during loop.
    # (Redo loop once more to capture team per slot — cheap given 500 sims.)
    # Also capture conditional breakdown for pick 3 and position-run runs.
    rng = np.random.default_rng(RNG_SEED)
    pick3_conditional: dict = {"Bailey@2": {}, "Reese@2": {}, "other@2": {}}
    pick2_totals: dict = {"Bailey": 0, "Reese": 0, "other": 0}
    position_run_counts: dict = {}  # (pick, pos) -> count of back-to-back runs
    simpson_qb_locked: list = []
    # Build from the union of hardcoded overrides and agent-file teams so
    # the PDF-derived qb_urgency values also get considered.
    _all_known_teams = (set(TEAM_PROFILE_OVERRIDES)
                        | {t for t in _TEAM_AGENTS if not t.startswith("_")})
    QB_LOCKED_TEAMS = {t for t in _all_known_teams
                       if get_team_profile(t).get("qb_urgency") == 0.0}
    trade_scenario_counts: dict = {"DAL_A(6)": 0, "DAL_B(4)": 0,
                                   "DAL_none": 0, "CIN_up": 0, "PHI_up": 0,
                                   "LAR_down": 0, "SEA_down": 0, "MIA_down": 0}

    for sim in range(N_SIMULATIONS):
        history, _, picks_realised = simulate_one(
            pros, picks_template, top3_needs, qb_urgency_map, rng)
        # Count trade scenarios
        # Re-derive from the picks list by comparing to original owners
        # (simpler: track inside simulate_one and expose). For now,
        # infer from picks_realised by checking who holds key picks.
        team_at_pk = {p["pick_number"]: p["team"] for p in picks_realised}
        if team_at_pk.get(6) == "DAL":
            trade_scenario_counts["DAL_A(6)"] += 1
        elif team_at_pk.get(4) == "DAL":
            trade_scenario_counts["DAL_B(4)"] += 1
        else:
            trade_scenario_counts["DAL_none"] += 1
        if team_at_pk.get(5) == "CIN":
            trade_scenario_counts["CIN_up"] += 1
        if team_at_pk.get(18) == "PHI":
            trade_scenario_counts["PHI_up"] += 1
        pick_team_map = {p["pick_number"]: p["team"] for p in picks_realised}
        for pn, player in history.items():
            t = pick_team_map.get(pn, "?")
            team_at_slot.setdefault(player, {})
            team_at_slot[player].setdefault(pn, {})
            team_at_slot[player][pn][t] = team_at_slot[player][pn].get(t, 0) + 1

        # Pick 3 conditional tallies
        p2 = history.get(2, "")
        p3 = history.get(3, "")
        if p2 == "David Bailey":
            pick2_totals["Bailey"] += 1
            pick3_conditional["Bailey@2"][p3] = \
                pick3_conditional["Bailey@2"].get(p3, 0) + 1
        elif p2 == "Arvell Reese":
            pick2_totals["Reese"] += 1
            pick3_conditional["Reese@2"][p3] = \
                pick3_conditional["Reese@2"].get(p3, 0) + 1
        else:
            pick2_totals["other"] += 1
            pick3_conditional["other@2"][p3] = \
                pick3_conditional["other@2"].get(p3, 0) + 1

        # Position-run: consecutive picks with same canonical position
        pos_seq = []
        for p in picks_realised:
            pn_ = p["pick_number"]
            pl = history.get(pn_)
            if pl:
                pos_seq.append((pn_, pros.loc[pros["player"] == pl, "_needs_pos"].iloc[0]
                                if (pros["player"] == pl).any() else "?"))
        for i in range(1, len(pos_seq)):
            if pos_seq[i][1] == pos_seq[i - 1][1] and pos_seq[i][1] != "OTHER":
                key = (pos_seq[i - 1][0], pos_seq[i][0], pos_seq[i][1])
                position_run_counts[key] = position_run_counts.get(key, 0) + 1

        # Simpson-in-QB-locked-team check
        for pn_, pl in history.items():
            if pl == "Ty Simpson" and pn_ <= 28:
                team = pick_team_map.get(pn_, "?")
                if team in QB_LOCKED_TEAMS:
                    simpson_qb_locked.append((pn_, team))

    # Aggregate — one row per (player, slot) pair so the output covers
    # every R1 slot. Previously we wrote only the MODE row per player,
    # which meant slots where no single player was modal (picks 8, 19-21
    # etc., with multiple near-equal contenders) were dropped from the CSV.
    # The per-player aggregates (mean, variance, n_landings) are duplicated
    # across that player's rows so downstream code can read any row.
    PROB_THRESHOLD = 0.02   # skip extreme-tail landings (<2% of sims)
    rows = []
    for player, slots in landing.items():
        total = sum(slots.values())
        picks_k = list(slots.keys())
        picks_w = list(slots.values())
        mean_pk = sum(k * w for k, w in zip(picks_k, picks_w)) / total
        var_pk  = sum(w * (k - mean_pk) ** 2 for k, w in zip(picks_k, picks_w)) / total
        row = pros[pros["player"] == player].iloc[0] if (pros["player"] == player).any() else None
        position = row.get("position") if row is not None else ""
        college  = row.get("college")  if row is not None else ""
        cons_rank = row.get("rank")    if row is not None else np.nan

        for slot, count in slots.items():
            prob = count / N_SIMULATIONS
            if prob < PROB_THRESHOLD:
                continue
            # Most frequent team owner AT THIS slot across sims.
            teams_here = team_at_slot.get(player, {}).get(slot, {})
            most_team = max(teams_here, key=teams_here.get) if teams_here else "?"
            rows.append({
                "player":                player,
                "position":              position,
                "college":               college,
                "consensus_rank":        cons_rank,
                "pick_slot":             slot,
                "probability":           prob,
                "most_likely_team":      most_team,
                "n_r1_landings":         total,
                "mean_landing_pick":     mean_pk,
                "variance_landing_pick": var_pk,
            })
    mc_df = pd.DataFrame(rows).sort_values(["pick_slot", "probability"],
                                            ascending=[True, False])
    mc_df.to_csv(OUT_MC, index=False)
    n_slots = mc_df["pick_slot"].nunique() if not mc_df.empty else 0
    print(f"\nSaved -> {OUT_MC} ({len(mc_df)} rows, {n_slots}/32 slots)")

    # Per-pick top-2 candidates + utility breakdown + flags.
    # Greedy claim per slot so the same player doesn't appear as top-1
    # at two different slots (each prospect can only go to one team).
    print("\nRound 1 — top Monte-Carlo candidates per pick (v12 utility):")
    print(f"{'pk':>2}  {'team':<4}  {'top-1':<24} {'prob':>5}  {'cons':>4}  "
          f"{'pos':<5}  {'top-2':<24} {'p2':>5}  flags")
    print("-" * 110)
    anomalies: list[str] = []
    _claimed_top1: set[str] = set()
    for pn in range(1, 33):
        by_count = [(p, slots.get(pn, 0)) for p, slots in landing.items()
                    if slots.get(pn, 0) > 0]
        if not by_count:
            continue
        by_count.sort(key=lambda t: -t[1])
        # Promote first unclaimed candidate to top-1.
        top_idx = next(
            (i for i, (p, _) in enumerate(by_count) if p not in _claimed_top1),
            0,
        )
        by_count = [by_count[top_idx]] + [
            t for i, t in enumerate(by_count) if i != top_idx
        ]
        p1_name, p1_count = by_count[0]
        p2_name, p2_count = (by_count[1] if len(by_count) > 1 else ("", 0))
        _claimed_top1.add(p1_name)
        teams_here = team_at_slot.get(p1_name, {}).get(pn, {})
        best_team = max(teams_here, key=teams_here.get) if teams_here else "?"
        row = pros[pros["player"] == p1_name]
        cons = int(row["rank"].iloc[0]) if not row.empty and pd.notna(row["rank"].iloc[0]) else None
        pos = row["position"].iloc[0] if not row.empty else "?"

        flags = []
        if p1_count / N_SIMULATIONS < 0.30:
            flags.append("UNCERTAIN")
        if pn in (3, 7):
            flags.append("CONDITIONAL")
        cap = cap_threshold(pn)
        if cons is not None and cons > cap and pn <= 28:
            flags.append(f"CAP-VIOLATION({cons}>{cap})")
            anomalies.append(f"pick {pn}: {p1_name} cons={cons} > cap {cap}")

        # Analyst agreement + KIPER-ONLY / ALL-ANALYSTS-DISAGREE
        if pn in ANALYST_PICKS:
            picks_dict = ANALYST_PICKS[pn]
            analyst_values = list(picks_dict.values())
            # How many of the 5 analysts pick the model's top-1
            hits = sum(1 for v in analyst_values if v == p1_name)
            flags.append(f"analyst={hits}/5")
            kiper = picks_dict.get("kiper")
            if p1_name == kiper and hits == 1:
                flags.append("KIPER-ONLY")
            if hits == 0:
                flags.append("ALL-ANALYSTS-DISAGREE")
        flags_s = " ".join(flags) if flags else ""

        print(f"{pn:>2}  {best_team:<4}  {p1_name:<24} "
              f"{p1_count / N_SIMULATIONS:>4.0%}  "
              f"{cons if cons is not None else '?':>4}  {pos:<5}  "
              f"{p2_name:<24} {p2_count / N_SIMULATIONS:>4.0%}  {flags_s}")

    # Trade events summary
    print(f"\nBilateral trade events fired across {N_SIMULATIONS} sims: {len(all_trades)}")
    # Always write the JSON — even empty — so the dashboard can reliably
    # read it without a file-missing branch.
    trades_payload: dict = {
        "n_simulations": N_SIMULATIONS,
        "total_trade_events": len(all_trades),
        "per_pick": {},          # pick_number -> list of {from_team, to_team, count, prob, top_targets}
    }
    if all_trades:
        import json as _json
        tr_df = pd.DataFrame(all_trades)
        print("Top-10 most-frequent bilateral trade scenarios:")
        freq = (tr_df.groupby(["pick_number", "from_team", "to_team"])
                     .size().reset_index(name="count")
                     .sort_values("count", ascending=False).head(10))
        print(freq.to_string(index=False))

        # Per-pick aggregation: for each slot, list each (from, to) trade
        # combination with fire probability and the top-3 player targets.
        for pn, sub in tr_df.groupby("pick_number"):
            pairs = []
            for (ft, tt), grp in sub.groupby(["from_team", "to_team"]):
                targets = (grp.groupby("target_player")
                              .size().reset_index(name="n")
                              .sort_values("n", ascending=False).head(3))
                pairs.append({
                    "from_team": ft,
                    "to_team":   tt,
                    "count":     int(len(grp)),
                    "prob":      round(len(grp) / N_SIMULATIONS, 3),
                    "top_targets": [
                        {"player": str(r.target_player), "count": int(r.n)}
                        for r in targets.itertuples(index=False)
                    ],
                })
            pairs.sort(key=lambda d: -d["prob"])
            trades_payload["per_pick"][str(int(pn))] = pairs
    with open(OUT_TRADES, "w", encoding="utf-8") as _f:
        import json as _json
        _json.dump(trades_payload, _f, indent=2)
    print(f"Saved -> {OUT_TRADES}")

    if anomalies:
        print(f"\nCAP-VIOLATIONS in picks 1-28: {len(anomalies)}")
        for a in anomalies:
            print(f"  {a}")
    else:
        print("\nNo consensus-cap violations in picks 1-28.")

    # Utility decomposition for each pick's top-1 (post-hoc, deterministic
    # re-score at the team's base state with no noise).
    # ALSO: serialize components + a human-readable "top factors" list to
    # data/processed/model_reasoning_2026.json so the frontend can explain
    # why the model picked a specific player — especially useful when the
    # model disagrees with the analyst consensus.
    print("\nUtility decomposition (top-1 per pick, deterministic re-score):")
    print(f"{'pk':>2}  {'team':<4}  {'player':<22}  {'bpa':>5}  {'need':>5}  "
          f"{'visit':>5}  {'intel':>5}  {'pv_mult':>7}  {'gm_aff':>7}  {'score':>6}  kiper")
    print("-" * 115)
    reasoning_out: dict[str, dict] = {}
    _claimed_reasoning: set[str] = set()
    for pn in range(1, 33):
        by_count = [(p, slots.get(pn, 0)) for p, slots in landing.items()
                    if slots.get(pn, 0) > 0]
        if not by_count:
            continue
        by_count.sort(key=lambda t: -t[1])
        # Match the greedy claim used in the top-1 table above so the
        # reasoning JSON stays consistent with what the dashboard shows.
        top_idx = next(
            (i for i, (p, _) in enumerate(by_count) if p not in _claimed_reasoning),
            0,
        )
        p1_name = by_count[top_idx][0]
        _claimed_reasoning.add(p1_name)
        teams_here = team_at_slot.get(p1_name, {}).get(pn, {})
        team = max(teams_here, key=teams_here.get) if teams_here else "?"
        pick_template = {"pick_number": pn, "team": team,
                         "bpa_weight": 0.5, "need_weight": 0.5}
        tc_row = team_ctx[(team_ctx["pick_number"] == pn)]
        if not tc_row.empty:
            pick_template["bpa_weight"] = float(tc_row["bpa_weight"].iloc[0])
            pick_template["need_weight"] = float(tc_row["need_weight"].iloc[0])
        _, comps = compute_base_scores(
            pros, pick_template, top3_needs, qb_urgency_map, [],
            final_score_col="final_score", return_components=True)
        if not (pros["player"] == p1_name).any():
            continue
        idx = pros.index[pros["player"] == p1_name][0]
        b = float(comps["bpa"].iloc[idx])
        n = float(comps["need"].iloc[idx])
        v = float(comps["visit"].iloc[idx])
        intel = float(comps["intel"].iloc[idx])
        pv = float(comps["pv_mult"].iloc[idx])
        gm_a = float(comps["gm_affinity"].iloc[idx])
        sf = float(comps["score_final"].iloc[idx])
        kiper = ANALYST_PICKS.get(pn, {}).get("kiper", "-")
        agree = "AGREE" if kiper == p1_name else "DIFF"
        if kiper == "-":
            agree = ""
        print(f"{pn:>2}  {team:<4}  {p1_name[:22]:<22}  "
              f"{b:5.2f}  {n:5.2f}  {v:5.2f}  {intel:5.2f}  "
              f"{pv:7.2f}  {gm_a:7.2f}  {sf:6.2f}  "
              f"{kiper[:18]:<18} {agree}")

        # Build the human-readable factor list for the JSON export. Factors
        # are ranked by their contribution magnitude.
        pos = str(pros.loc[idx, "position"]).upper() if "position" in pros.columns else ""
        factors: list[dict] = []
        if n >= 0.45:
            factors.append({
                "key": "team_need", "magnitude": n,
                "label": f"{pos} is a top roster need",
                "detail": f"Need score contributed {n:.2f} to the total",
            })
        if v >= 0.20:
            factors.append({
                "key": "visit", "magnitude": v,
                "label": "Confirmed pre-draft visit",
                "detail": f"Multi-source visit signal worth +{v:.2f}",
            })
        if intel >= 0.25:
            factors.append({
                "key": "intel", "magnitude": intel,
                "label": "Analyst intel scripted this pick",
                "detail": f"Tier-1 analyst consensus pushed prob {intel:.2f}",
            })
        if pv >= 1.15:
            factors.append({
                "key": "positional_value", "magnitude": pv - 1.0,
                "label": f"{pos} position premium",
                "detail": f"Position-value multiplier {pv:.2f}x (premium slot)",
            })
        if pv <= 0.95 and sf > 0:
            factors.append({
                "key": "non_premium_discount", "magnitude": 1.0 - pv,
                "label": f"{pos} is a non-premium position",
                "detail": f"Discounted {(1-pv)*100:.0f}% but still outscored alternatives",
            })
        if gm_a >= 1.08:
            factors.append({
                "key": "gm_affinity", "magnitude": gm_a - 1.0,
                "label": f"GM historically favors {pos}",
                "detail": f"Positional-affinity multiplier {gm_a:.2f}x",
            })
        if gm_a <= 0.92:
            factors.append({
                "key": "gm_aversion", "magnitude": 1.0 - gm_a,
                "label": f"GM rarely drafts {pos}",
                "detail": f"Positional-affinity penalty {gm_a:.2f}x (model picked anyway)",
            })
        # Post-combine boost (Styles etc.)
        if p1_name in POST_COMBINE_BOOSTS and POST_COMBINE_BOOSTS[p1_name] > 1.0:
            mult = POST_COMBINE_BOOSTS[p1_name]
            factors.append({
                "key": "post_combine_boost", "magnitude": mult - 1.0,
                "label": "Post-combine riser",
                "detail": f"Stage-1 under-rated; boosted {(mult-1)*100:.0f}% to reflect current mocks",
            })

        factors.sort(key=lambda f: -f["magnitude"])

        reasoning_out[str(pn)] = {
            "team": team,
            "player": p1_name,
            "position": pos,
            "components": {
                "bpa": round(b, 3),
                "need": round(n, 3),
                "visit": round(v, 3),
                "intel": round(intel, 3),
                "pv_mult": round(pv, 3),
                "gm_affinity": round(gm_a, 3),
                "score_final": round(sf, 3),
            },
            "top_factors": factors[:4],
        }

    # Write reasoning JSON for API consumption
    REASON_JSON = ROOT / "data" / "processed" / "model_reasoning_2026.json"
    REASON_JSON.write_text(
        json.dumps({
            "meta": {"n_sims": N_SIMULATIONS},
            "picks": reasoning_out,
        }, indent=2),
        encoding="utf-8",
    )
    print(f"\nSaved -> {REASON_JSON.name}  ({len(reasoning_out)} picks)")

    # Pick 3 ARI conditional breakdown
    print("\nPick 3 ARI — conditional on pick 2 outcome:")
    for label, prev_text, total_key in [
        ("Bailey@2", "If NYJ took Bailey at 2", "Bailey"),
        ("Reese@2", "If NYJ took Reese at 2", "Reese"),
    ]:
        dist = pick3_conditional[label]
        denom = pick2_totals[total_key] or 1
        top = sorted(dist.items(), key=lambda kv: -kv[1])[:4]
        parts = [f"{p}: {c / denom:.0%}" for p, c in top]
        print(f"  {prev_text:<30} ({pick2_totals[total_key]} sims) -> "
              + ", ".join(parts))

    # Back-to-back position runs (e.g. S at 18 AND 19)
    print("\nPosition-run events (same canonical pos on consecutive picks):")
    b2b = sorted(position_run_counts.items(), key=lambda kv: -kv[1])[:10]
    if b2b:
        for (pk_a, pk_b, pos), count in b2b:
            print(f"  picks {pk_a}->{pk_b} ({pos}): {count / N_SIMULATIONS:.0%} of sims")
    else:
        print("  (none)")

    # Simpson-in-QB-locked-team check
    if simpson_qb_locked:
        print(f"\nSimpson landed on a QB-locked team in picks 1-28 "
              f"({len(simpson_qb_locked)} occurrences across 500 sims):")
        from collections import Counter
        for (pn_, team), c in Counter(simpson_qb_locked).most_common(5):
            print(f"  pick {pn_} ({team}): {c} sims")
    else:
        print("\nSimpson never landed on a QB-locked team in picks 1-28.")

    # Trade scenario frequencies
    print("\nTrade scenario frequencies (across 500 sims):")
    for key, count in trade_scenario_counts.items():
        if count > 0:
            print(f"  {key:<14} {count:>3} sims ({count / N_SIMULATIONS:.0%})")

    # Top-5 highest variance
    print("\nMost uncertain landing spots (top 5 variance):")
    hv = mc_df.nlargest(5, "variance_landing_pick")[
        ["player", "position", "consensus_rank", "pick_slot",
         "probability", "variance_landing_pick"]]
    print(hv.to_string(index=False))

    # Largest model-vs-consensus divergence
    print("\nLargest pick_slot vs consensus divergence:")
    mc_df["div"] = (mc_df["pick_slot"] - mc_df["consensus_rank"]).abs()
    div = mc_df.nlargest(8, "div")[
        ["player", "position", "consensus_rank", "pick_slot",
         "probability", "most_likely_team"]]
    print(div.to_string(index=False))


if __name__ == "__main__":
    main()
