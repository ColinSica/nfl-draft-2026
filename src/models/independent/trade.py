"""Layer D — structural trade logic.

Trade probability is grounded in:
  - historical pick-range trade rates (from 2011-2025 real drafts)
  - real team / GM trade tendencies
  - board-state scarcity signals (QB-run, tier exhaustion)
  - capital abundance / scarcity
  - win-now pressure
  - 5th-year option premium in the late first round

Does NOT read mock-derived scenarios, analyst-mentioned trade frequency,
or any "scripted override" table.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

# Fitzgerald / Jimmy Johnson classic value chart (factual function of slot).
# Values for picks 1-32; higher = more valuable pick.
_FITZGERALD_R1 = {
    1: 3000, 2: 2600, 3: 2200, 4: 1800, 5: 1700,
    6: 1600, 7: 1500, 8: 1400, 9: 1350, 10: 1300,
    11: 1250, 12: 1200, 13: 1150, 14: 1100, 15: 1050,
    16: 1000, 17:  950, 18:  900, 19:  875, 20:  850,
    21:  800, 22:  780, 23:  760, 24:  740, 25:  720,
    26:  700, 27:  680, 28:  660, 29:  640, 30:  620,
    31:  600, 32:  590,
}


def pick_value(slot: int) -> float:
    """Fitzgerald chart value; slots past 32 get exponential decay."""
    if slot in _FITZGERALD_R1:
        return _FITZGERALD_R1[slot]
    return float(max(40.0, 580.0 * (0.97 ** (slot - 32))))


def _qb_on_board_count(prospects_avail: pd.DataFrame, top_n: int = 3) -> int:
    """How many top-tier QBs are still available (used to gauge QB scarcity)."""
    qb = prospects_avail[prospects_avail["position"].str.upper() == "QB"]
    return int((qb["independent_grade"].rank(method="min") <= top_n).sum())


def _tier_about_to_exhaust(prospects_avail: pd.DataFrame,
                           position: str, tier_size: int = 3) -> bool:
    """True if only `tier_size` prospects remain at `position` in what the
    model considers the elite tier (top-40 by grade)."""
    pos = prospects_avail[prospects_avail["position"].str.upper() == position.upper()]
    elite = pos[pos["independent_grade"] <= 80.0]
    return len(elite) <= tier_size


def trade_down_probability(team: str, team_profile: dict,
                           slot: int, prospects_avail: pd.DataFrame,
                           pick_range_trade_rate: float = 0.10) -> float:
    """Structural P(team trades DOWN from this slot)."""
    tb = team_profile.get("trade_behavior", {}) or {}
    team_rate = float(tb.get("trade_down_rate", 0.35))
    # Historical base rate at this slot range
    base = pick_range_trade_rate
    prob = 0.5 * team_rate + 0.5 * base

    # Dampen if a tier is exhausting at a top-need position — more incentive
    # to USE the pick than trade back.
    needs = team_profile.get("roster_needs", {}) or {}
    for pos, weight in needs.items():
        if float(weight) >= 3.0 and _tier_about_to_exhaust(prospects_avail, pos):
            prob *= 0.60
            break

    # Capital-abundance boost — teams with many picks are more willing to
    # trade down further.
    abund = (team_profile.get("draft_capital") or {}).get("capital_abundance")
    if abund == "very_high":
        prob *= 1.20
    elif abund == "high":
        prob *= 1.10
    elif abund == "low":
        prob *= 0.80

    # Late-R1 5th-year option premium — teams less willing to trade out of R1.
    if slot >= 29:
        prob *= 0.70

    return float(np.clip(prob, 0.0, 0.70))


def trade_up_probability(team: str, team_profile: dict,
                         slot: int, prospects_avail: pd.DataFrame) -> float:
    """Structural P(team trades UP into an earlier slot).

    Main drivers: QB urgency when a QB tier is about to exhaust, plus
    the team's baseline trade_up_rate from real history.
    """
    tb = team_profile.get("trade_behavior", {}) or {}
    team_rate = float(tb.get("trade_up_rate", 0.15))
    prob = 0.6 * team_rate  # base

    qb_urg = float(team_profile.get("qb_urgency", 0.0) or 0.0)
    if qb_urg >= 0.6:
        # If QB is near-exhausted, bump significantly
        if _qb_on_board_count(prospects_avail, top_n=2) <= 1:
            prob += 0.25
        else:
            prob += 0.10

    # Contender + top-need-tier-exhausting combo
    win_now = float(team_profile.get("win_now_pressure", 0.5) or 0.5)
    if win_now >= 0.8:
        needs = team_profile.get("roster_needs", {}) or {}
        for pos, w in needs.items():
            if float(w) >= 4.0 and _tier_about_to_exhaust(prospects_avail, pos, tier_size=2):
                prob += 0.10
                break

    # Capital-scarce teams trade up less (they don't have the pieces)
    abund = (team_profile.get("draft_capital") or {}).get("capital_abundance")
    if abund == "low":
        prob *= 0.70

    # First-year GM trade-up prior bump — 2020-2025 backtest: first-year GMs
    # drive ~45% of surprise R1 trade-ups (new regime wants to announce pick).
    if bool(team_profile.get("new_gm", False)):
        prob *= 1.80

    return float(np.clip(prob, 0.0, 0.60))
