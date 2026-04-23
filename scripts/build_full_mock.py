"""Build a 7-round (257 pick) mock draft assignment.

Inputs:
  - data/features/pick_order_2026.json       (257 ordered picks w/ owning team)
  - data/processed/predictions_2026_independent.csv  (independent player board)
  - data/features/team_agents_2026.json      (roster_needs, gm_affinity, scheme)

Algorithm (greedy, per-pick, with lookahead-lite):
  - Maintain per-team position counts already drafted.
  - For each pick in order, score every remaining prospect:
        score = grade_score          # from independent_grade, rank-decayed
              + need_bonus(team, position)   # based on roster_needs + already-filled
              + affinity_bonus(team, position)  # gm_affinity / scheme premium
              + positional_value_at_round       # avoid reaching for K/P early
              + visit_bonus                      # documented team visits
  - Pick the argmax, log the top-5 alternates for explainability.
  - Soft diminishing returns: each additional pick at the same position
    halves the need_bonus.

Output: data/processed/full_mock_2026.json — list of {pick, round, team,
        player, position, college, reasoning, alternates}.
"""
from __future__ import annotations

import json
import math
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent

ORDER_PATH = ROOT / "data/features/pick_order_2026.json"
BOARD_PATH = ROOT / "data/processed/predictions_2026_independent.csv"
AGENTS_PATH = ROOT / "data/features/team_agents_2026.json"
VISITS_PATH = ROOT / "data/features/team_agents_2026.json"  # visit lists live inside
OUT_PATH = ROOT / "data/processed/full_mock_2026.json"


# Map nuanced position labels → broad need-position bucket used in roster_needs.
POS_TO_NEED = {
    "QB": "QB", "RB": "RB", "WR": "WR", "TE": "TE",
    "OT": "OT", "IOL": "IOL", "OL": "IOL", "C": "IOL", "G": "IOL",
    "EDGE": "EDGE", "DE": "EDGE", "OLB": "EDGE",
    "IDL": "IDL", "DT": "IDL", "NT": "IDL", "DL": "IDL",
    "LB": "LB", "ILB": "LB", "MLB": "LB",
    "CB": "CB", "S": "S", "DB": "CB", "NB": "CB", "FS": "S", "SS": "S",
    "K": "K", "P": "P", "LS": "LS", "FB": "RB",
}

# Expected position value in each round (modulates "reach" penalty).
# Row = round (1-7). We penalize picks far below expected grade-for-round.
ROUND_EXPECTED_GRADE_PCTILE = {
    1: (0, 32),
    2: (32, 64),
    3: (64, 100),
    4: (100, 140),
    5: (140, 180),
    6: (180, 220),
    7: (220, 260),
}


def _load():
    order = json.loads(ORDER_PATH.read_text(encoding="utf-8"))["picks"]
    board = pd.read_csv(BOARD_PATH)
    agents = json.loads(AGENTS_PATH.read_text(encoding="utf-8"))
    return order, board, agents


def _normalize_pos(p: str) -> str:
    if not isinstance(p, str):
        return ""
    p = p.strip().upper()
    return POS_TO_NEED.get(p, p)


def _need_bonus(team_needs: dict, pos: str, already_drafted: Counter) -> float:
    """Softly diminishing: first pick at a need = full bonus, second = half, ..."""
    need_score = float(team_needs.get(pos, 0.0))
    prior = already_drafted.get(pos, 0)
    return need_score * (0.5 ** prior)


def _affinity_bonus(gm_aff: dict, pos: str) -> float:
    return float(gm_aff.get(pos, 0.0))


def _scheme_bonus(scheme_premium: list, pos: str) -> float:
    if not scheme_premium:
        return 0.0
    return 0.75 if pos in scheme_premium else 0.0


def _visit_bonus(visits: set, player: str) -> float:
    return 0.6 if player in visits else 0.0


def _round_for_pick(pick_num: int) -> int:
    for r, (lo, hi) in ROUND_EXPECTED_GRADE_PCTILE.items():
        if lo < pick_num <= hi:
            return r
    return 7


def build_mock():
    order, board, agents = _load()

    # Prepare board: sort by rank (smaller = better), index by player.
    board = board.copy()
    board = board.sort_values("final_rank", ascending=True).reset_index(drop=True)
    # Rank-based grade score: 1st overall = 1.00, decaying.
    # Rank 32 ≈ 0.55, rank 100 ≈ 0.30, rank 250 ≈ 0.10.
    board["_grade_score"] = 1.0 / (1.0 + 0.015 * (board["final_rank"] - 1))
    # Normalize position
    board["_need_pos"] = board["position"].map(_normalize_pos)
    # Convert to list of dicts for fast filtering
    remaining: dict[str, dict] = {}
    for _, row in board.iterrows():
        remaining[row["player"]] = {
            "player":  row["player"],
            "position": row["position"],
            "need_pos": row["_need_pos"],
            "college": row.get("school") or row.get("college") or "",
            "rank":    int(row["final_rank"]),
            "grade":   float(row["_grade_score"]),
            "tier":    row.get("independent_tier") or "",
        }

    # Per-team state
    team_state: dict[str, dict] = {}
    for abbr, p in agents.items():
        if abbr.startswith("_") or not isinstance(p, dict):
            continue
        team_state[abbr] = {
            "needs":    dict(p.get("roster_needs", {}) or {}),
            "affinity": dict(p.get("gm_affinity", {}) or {}),
            "scheme_premium": list(p.get("scheme", {}).get("premium", []) or []),
            "visits":   set(p.get("visit_signals", {}).get("confirmed_visits", []) or []),
            "drafted":  Counter(),
            "scheme_type": (p.get("scheme", {}) or {}).get("type", ""),
        }

    picks_out: list[dict] = []

    for entry in order:
        pick_num = int(entry["pick"])
        rnd = int(entry["round"])
        team = entry["team"]
        state = team_state.get(team)
        if state is None:
            # Team not in agents (shouldn't happen but be safe)
            continue

        expected_lo, expected_hi = ROUND_EXPECTED_GRADE_PCTILE[rnd]

        # Score all remaining prospects
        scored: list[tuple[float, dict, dict]] = []
        for player, prow in remaining.items():
            pos = prow["need_pos"]
            rank = prow["rank"]
            grade = prow["grade"]

            # "Reach" penalty: prospect ranked far below the round's grade band.
            # Lightly penalize picks ranked much later than round midpoint.
            rnd_mid = (expected_lo + expected_hi) / 2
            distance = (rank - rnd_mid) / max(20.0, (expected_hi - expected_lo))
            # distance=0 when on-schedule; >0 when player is ranked lower than
            # the round band (an "over-reach" to avoid in R1 but common in R7).
            # Symmetric penalty on both sides, gentler in late rounds.
            reach_penalty = 0.35 * max(0.0, -distance) ** 1.5  # reaching = picking much earlier than rank warrants
            # Also punish wildly late picks in early rounds:
            too_late_penalty = 0.15 * max(0.0, distance) ** 1.2 if rnd <= 3 else 0.0

            need_b = _need_bonus(state["needs"], pos, state["drafted"])
            aff_b  = 0.15 * _affinity_bonus(state["affinity"], pos)
            schm_b = _scheme_bonus(state["scheme_premium"], pos)
            vis_b  = _visit_bonus(state["visits"], player)

            total = (
                grade
                + 0.22 * need_b
                + aff_b
                + schm_b
                + vis_b
                - reach_penalty
                - too_late_penalty
            )

            # Hard discourage: drafting a kicker/punter before round 5
            if pos in ("K", "P") and rnd <= 4:
                total -= 2.0
            # Hard discourage: drafting a QB with no QB need at all
            if pos == "QB":
                qb_need = float(state["needs"].get("QB", 0.0))
                prior_qb = state["drafted"].get("QB", 0)
                if qb_need < 1.0 and prior_qb == 0:
                    total -= 0.8  # not a massive cut — can still take a developmental QB

            breakdown = {
                "grade": round(grade, 3),
                "need":  round(0.22 * need_b, 3),
                "aff":   round(aff_b, 3),
                "scheme": round(schm_b, 3),
                "visit": round(vis_b, 3),
                "reach": round(-reach_penalty, 3),
                "late":  round(-too_late_penalty, 3),
            }
            scored.append((total, prow, breakdown))

        if not scored:
            break
        scored.sort(key=lambda t: -t[0])
        top_score, top_prow, top_breakdown = scored[0]

        # Alternates: show top 4 others
        alternates = [
            {"player": p["player"], "position": p["position"],
             "rank": p["rank"], "score": round(s, 3)}
            for s, p, _ in scored[1:5]
        ]

        # Drop selected player from remaining
        del remaining[top_prow["player"]]
        # Update team state
        state["drafted"][top_prow["need_pos"]] += 1

        # Reasoning — 1-line, data-cited
        reasons = []
        if top_breakdown["need"] > 0.05:
            reasons.append(f"{top_prow['need_pos']} tier-{state['needs'].get(top_prow['need_pos'], 0):.1f} need")
        if top_breakdown["scheme"] > 0:
            reasons.append(f"fits {state.get('scheme_type') or 'scheme'} premium")
        if top_breakdown["visit"] > 0:
            reasons.append("confirmed pre-draft visit")
        if top_breakdown["aff"] > 0.02:
            reasons.append("GM-history affinity")
        if top_prow["rank"] <= 32 and rnd == 1:
            reasons.append(f"consensus top-32 ({top_prow['tier']})")
        reasoning = "; ".join(reasons) or f"best available ({top_prow['tier'] or 'BPA'})"

        picks_out.append({
            "pick":     pick_num,
            "round":    rnd,
            "team":     team,
            "player":   top_prow["player"],
            "position": top_prow["position"],
            "college":  top_prow["college"],
            "rank":     top_prow["rank"],
            "tier":     top_prow["tier"],
            "reasoning": reasoning,
            "score":    round(top_score, 3),
            "factors":  top_breakdown,
            "alternates": alternates,
        })

    out = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "n_picks": len(picks_out),
        "source_board_mtime": datetime.fromtimestamp(
            BOARD_PATH.stat().st_mtime, tz=timezone.utc
        ).isoformat(timespec="seconds"),
        "methodology": (
            "Greedy per-pick assignment using the independent model's 727-prospect "
            "board (kalshi-anchored + PFF tape) × each team's roster_needs, "
            "gm_affinity, scheme premium, and documented pre-draft visits. "
            "Diminishing-returns: each additional pick at the same position halves "
            "the need weight. Reach + over-value penalties applied per round band."
        ),
        "picks": picks_out,
    }
    OUT_PATH.write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"[full_mock] wrote {OUT_PATH}  ({len(picks_out)} picks)")
    # Summary
    by_round = Counter(p["round"] for p in picks_out)
    print(f"[full_mock] picks per round: {dict(sorted(by_round.items()))}")
    by_pos = Counter(p["position"] for p in picks_out)
    print(f"[full_mock] picks per position: {dict(by_pos.most_common())}")
    return out


if __name__ == "__main__":
    build_mock()
