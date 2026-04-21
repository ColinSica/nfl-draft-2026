"""Odds-based post-processing clamp.

Replaces the consensus-rank clamp with a market-implied clamp for players
with Kalshi coverage. For each pick slot (R1 through R3+):

  1. If the modal pick has an odds anchor AND the slot falls within the
     player's P10..P90 market band, keep the pick.
  2. Otherwise, substitute with the most-likely candidate whose market
     P10..P90 band CONTAINS this slot.
  3. Fallback to the existing consensus-rank clamp for uncovered slots.

Board repositioning mirrors the same logic: players with market anchors
get their final_rank nudged toward the market P50 if they're more than
~8 off.

Preserves uniqueness: no player assigned to two slots.
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
PRED_BOARD = ROOT / "data/processed/predictions_2026_independent.csv"
PRED_PICKS = ROOT / "data/processed/predictions_2026_independent_picks.csv"
PROSPECTS  = ROOT / "data/processed/prospects_2026_enriched.csv"
MC_CSV     = ROOT / "data/processed/monte_carlo_2026_independent.csv"


def _tier(r: int) -> str:
    if r <= 32: return "R1"
    if r <= 64: return "R2"
    if r <= 100: return "R3"
    if r <= 257: return "R4-R7"
    return "UDFA"


def _gap_limit_consensus(consensus_rank: float) -> int:
    """Used only as fallback when no market anchor exists."""
    if pd.isna(consensus_rank): return 9999
    if consensus_rank <= 32:  return 10
    if consensus_rank <= 64:  return 15
    if consensus_rank <= 100: return 20
    if consensus_rank <= 200: return 30
    return 50


def _band_contains(slot: int, anchor: dict, padding: int = 2) -> bool:
    lo = anchor["pick_p10"] - padding
    hi = anchor["pick_p90"] + padding
    return lo <= slot <= hi


def apply_odds_clamp() -> dict:
    """Run the odds-based clamp. Returns a summary dict."""
    from src.models.independent.odds_anchor import load_anchors
    from src.models.calibration import r1_clamp as legacy

    anchors = load_anchors()
    if not anchors:
        print("[odds_clamp] no odds anchors available, falling back to r1_clamp")
        legacy.apply_r1_clamp()
        return {"used": "r1_clamp_fallback", "n_odds_players": 0}

    print(f"[odds_clamp] loaded market anchors for {len(anchors)} players")

    if not PRED_BOARD.exists() or not PROSPECTS.exists():
        print("[odds_clamp] missing inputs, skip")
        return {"used": "none", "reason": "missing_inputs"}

    # ------- BOARD: nudge final_rank toward market P50 -------
    board = pd.read_csv(PRED_BOARD)
    pros = pd.read_csv(PROSPECTS, usecols=["player", "rank", "position"])
    pros["rank"] = pd.to_numeric(pros["rank"], errors="coerce")

    board = board.merge(pros[["player", "rank"]], on="player", how="left")

    def _target(row) -> float:
        player = row["player"]
        cur = float(row["final_rank"])
        anchor = anchors.get(player)
        if anchor is not None:
            p50 = float(anchor["pick_p50"])
            gap = abs(cur - p50)
            # Market-driven: pull toward P50 if more than 8 off
            if gap > 8:
                return p50
            return cur
        # No market — fall back to consensus clamp logic
        r = row.get("rank")
        if pd.isna(r):
            return cur
        lim = _gap_limit_consensus(r)
        if abs(cur - r) > lim:
            return float(r)
        return cur

    board["_target_rank"] = board.apply(_target, axis=1)
    board = board.sort_values(["_target_rank", "final_rank"]).reset_index(drop=True)
    board["final_rank"] = range(1, len(board) + 1)
    board["independent_tier"] = board["final_rank"].apply(_tier)

    original_cols = [c for c in pd.read_csv(PRED_BOARD, nrows=1).columns
                     if c in board.columns]
    board[original_cols].to_csv(PRED_BOARD, index=False)

    # ------- PICKS: market-band gate through R3 (slot <= 100) -------
    n_clamped = 0
    n_kept_market = 0
    n_kept_original = 0
    n_consensus_fallback = 0

    if not PRED_PICKS.exists() or not MC_CSV.exists():
        return {
            "used": "odds_clamp",
            "n_odds_players": len(anchors),
            "n_picks_clamped": 0,
            "note": "no picks/MC files",
        }

    picks = pd.read_csv(PRED_PICKS)
    mc = pd.read_csv(MC_CSV)
    pros_rank = pros.set_index("player")["rank"].to_dict()
    pos_lookup = pros.set_index("player")["position"].to_dict()

    slot_col = "pick_slot" if "pick_slot" in mc.columns else "pick_number"
    team_col = "most_likely_team" if "most_likely_team" in mc.columns else "team"

    # Per-slot MC candidate set
    candidates_by_slot: dict[int, list[dict]] = {}
    for _, r in mc.iterrows():
        slot = int(r.get(slot_col, 0))
        if slot <= 0 or slot > 100:
            continue
        candidates_by_slot.setdefault(slot, []).append({
            "player": r["player"],
            "position": r.get("position"),
            "probability": float(r.get("probability", 0) or 0),
            "team": r.get(team_col),
        })

    claimed: set[str] = set()
    pick_rows = picks.to_dict(orient="records")

    for row in pick_rows:
        slot = int(row["pick"])
        player = row["player"]

        # Out-of-scope for clamp (R4+) — keep original
        if slot > 100:
            claimed.add(player)
            continue

        anchor = anchors.get(player)

        # --- Case A: player has market coverage ---
        if anchor is not None:
            if _band_contains(slot, anchor) and player not in claimed:
                claimed.add(player)
                n_kept_market += 1
                continue
            # Market says this player doesn't belong here — substitute.
            # Prefer MC candidates at this slot whose own market band contains slot.
            slot_cands = candidates_by_slot.get(slot, [])
            market_ok = [
                c for c in slot_cands
                if c["player"] not in claimed
                and c["player"] in anchors
                and _band_contains(slot, anchors[c["player"]])
            ]
            if market_ok:
                sub = max(market_ok, key=lambda c: c["probability"])
                row["player"] = sub["player"]
                row["position"] = sub["position"]
                row["probability"] = sub["probability"]
                claimed.add(sub["player"])
                n_clamped += 1
                continue
            # No market-band MC candidate — fall back to consensus near slot
            cons_cands = [
                c for c in slot_cands
                if c["player"] not in claimed
                and pros_rank.get(c["player"]) is not None
                and pd.notna(pros_rank[c["player"]])
                and abs(float(pros_rank[c["player"]]) - slot) <= 4
            ]
            if cons_cands:
                sub = max(cons_cands, key=lambda c: c["probability"])
                row["player"] = sub["player"]
                row["position"] = sub["position"]
                row["probability"] = sub["probability"]
                claimed.add(sub["player"])
                n_clamped += 1
                n_consensus_fallback += 1
                continue
            # Last resort — pool of market-anchored players whose band contains slot
            pool = [
                (p, a) for p, a in anchors.items()
                if p not in claimed and _band_contains(slot, a)
            ]
            if pool:
                pool.sort(key=lambda x: abs(float(x[1]["pick_p50"]) - slot))
                sub_player = pool[0][0]
                row["player"] = sub_player
                row["position"] = pos_lookup.get(sub_player, row["position"])
                row["probability"] = 0.15
                claimed.add(sub_player)
                n_clamped += 1
                continue
            claimed.add(player)
            n_kept_original += 1
            continue

        # --- Case B: no market coverage — consensus-based fallback clamp ---
        cons = pros_rank.get(player)
        if (pd.notna(cons)
            and abs(float(cons) - slot) <= _gap_limit_consensus(cons) / 3.0  # stricter now
            and player not in claimed):
            claimed.add(player)
            n_kept_original += 1
            continue

        slot_cands = candidates_by_slot.get(slot, [])
        # Prefer market-anchored substitutes first (they're the higher-quality signal)
        market_sub = [
            c for c in slot_cands
            if c["player"] not in claimed
            and c["player"] in anchors
            and _band_contains(slot, anchors[c["player"]])
        ]
        if market_sub:
            sub = max(market_sub, key=lambda c: c["probability"])
            row["player"] = sub["player"]
            row["position"] = sub["position"]
            row["probability"] = sub["probability"]
            claimed.add(sub["player"])
            n_clamped += 1
            continue

        cons_cands = [
            c for c in slot_cands
            if c["player"] not in claimed
            and pros_rank.get(c["player"]) is not None
            and pd.notna(pros_rank[c["player"]])
            and abs(float(pros_rank[c["player"]]) - slot) <= 4
        ]
        if cons_cands:
            sub = max(cons_cands, key=lambda c: c["probability"])
            row["player"] = sub["player"]
            row["position"] = sub["position"]
            row["probability"] = sub["probability"]
            claimed.add(sub["player"])
            n_clamped += 1
            n_consensus_fallback += 1
            continue

        claimed.add(player)
        n_kept_original += 1

    pd.DataFrame(pick_rows).to_csv(PRED_PICKS, index=False)

    summary = {
        "used": "odds_clamp",
        "n_odds_players": len(anchors),
        "n_picks_clamped": n_clamped,
        "n_kept_market_band": n_kept_market,
        "n_kept_original": n_kept_original,
        "n_consensus_fallback": n_consensus_fallback,
    }
    print(f"[odds_clamp] {summary}")
    return summary


if __name__ == "__main__":
    apply_odds_clamp()
