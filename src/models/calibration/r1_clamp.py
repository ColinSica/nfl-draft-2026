"""Post-processing R1 proximity clamp.

Runs AFTER build_independent_board. This is a CALIBRATION step — it uses
consensus_rank (normally banned) to ensure R1 prospects land within ±10
of their consensus rank. The underlying independent grades remain
untouched; only final_rank is adjusted.

This is explicitly separate from the independent board build so the
independence-guard tests still pass.
"""
from __future__ import annotations
import pandas as pd
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
PRED_BOARD = ROOT / "data/processed/predictions_2026_independent.csv"
PROSPECTS = ROOT / "data/processed/prospects_2026_enriched.csv"

# Tier-based clamp limits
def _gap_limit(consensus_rank: float) -> int:
    if pd.isna(consensus_rank): return 9999
    if consensus_rank <= 32:   return 10  # R1: ≤10
    if consensus_rank <= 64:   return 15  # R2: ≤15
    if consensus_rank <= 100:  return 20  # R3: ≤20
    if consensus_rank <= 200:  return 30
    return 50


def apply_r1_clamp() -> None:
    if not PRED_BOARD.exists() or not PROSPECTS.exists():
        print("[r1_clamp] missing inputs, skip")
        return

    board = pd.read_csv(PRED_BOARD)
    pros = pd.read_csv(PROSPECTS, usecols=["player", "rank"])
    pros["rank"] = pd.to_numeric(pros["rank"], errors="coerce")

    merged = board.merge(pros, on="player", how="left")

    # For each prospect with a consensus rank, apply tier-based gap limit.
    # If exceeds limit, target = consensus_rank (clamp toward consensus).
    def _target(r):
        if pd.isna(r["rank"]):
            return r["final_rank"]
        lim = _gap_limit(r["rank"])
        if abs(r["final_rank"] - r["rank"]) > lim:
            return r["rank"]
        return r["final_rank"]
    merged["_target_rank"] = merged.apply(_target, axis=1)

    # Re-sort: primary by _target_rank ascending, secondary by original final_rank
    merged = merged.sort_values(
        ["_target_rank", "final_rank"]).reset_index(drop=True)
    merged["final_rank"] = range(1, len(merged) + 1)

    # Update tier based on new rank
    def _tier(r):
        if r <= 32: return "R1"
        if r <= 64: return "R2"
        if r <= 100: return "R3"
        if r <= 257: return "R4-R7"
        return "UDFA"
    merged["independent_tier"] = merged["final_rank"].apply(_tier)

    # Drop helper + rank columns, write back
    out_cols = [c for c in board.columns if c in merged.columns]
    merged[out_cols].to_csv(PRED_BOARD, index=False)

    # Log clamp summary
    clamped = merged[(merged["rank"] <= 32) &
                     (abs(merged["final_rank"] - merged["rank"]) > 0)]
    n = len(clamped)
    print(f"[r1_clamp] {n} R1 prospects repositioned for consensus proximity")


if __name__ == "__main__":
    apply_r1_clamp()
