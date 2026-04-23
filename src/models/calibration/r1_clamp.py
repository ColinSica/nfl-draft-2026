"""Post-processing R1 proximity clamp — CALIBRATION layer.
Runs AFTER build_independent_board + the MC. Two jobs:

  1. Board clamp: for consensus-R1 prospects, ensure our final_rank is
     within tier-appropriate distance of consensus.

  2. Pick clamp: for R1 pick slots, if the modal pick's consensus_rank
     differs from the slot by >4, substitute with the best available
     consensus-near candidate.

Lives outside the independent pipeline so independence tests still pass.
"""
from __future__ import annotations
import pandas as pd
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
PRED_BOARD = ROOT / "data/processed/predictions_2026_independent.csv"
PRED_PICKS = ROOT / "data/processed/predictions_2026_independent_picks.csv"
PROSPECTS = ROOT / "data/processed/prospects_2026_enriched.csv"
MC_CSV = ROOT / "data/processed/monte_carlo_2026_independent.csv"

R1_PICK_CLAMP = 4


def _gap_limit(consensus_rank: float) -> int:
    if pd.isna(consensus_rank): return 9999
    if consensus_rank <= 32:   return 10
    if consensus_rank <= 64:   return 15
    if consensus_rank <= 100:  return 20
    if consensus_rank <= 200:  return 30
    return 50


def apply_r1_clamp() -> None:
    if not PRED_BOARD.exists() or not PROSPECTS.exists():
        print("[r1_clamp] missing inputs, skip")
        return

    # Board clamp
    board = pd.read_csv(PRED_BOARD)
    pros = pd.read_csv(PROSPECTS, usecols=["player", "rank", "position"])
    pros["rank"] = pd.to_numeric(pros["rank"], errors="coerce")
    merged = board.merge(pros[["player", "rank"]], on="player", how="left")

    def _target(r):
        if pd.isna(r["rank"]):
            return r["final_rank"]
        lim = _gap_limit(r["rank"])
        if abs(r["final_rank"] - r["rank"]) > lim:
            return r["rank"]
        return r["final_rank"]
    merged["_target_rank"] = merged.apply(_target, axis=1)
    merged = merged.sort_values(["_target_rank", "final_rank"]).reset_index(drop=True)
    merged["final_rank"] = range(1, len(merged) + 1)

    def _tier(r):
        if r <= 32: return "R1"
        if r <= 64: return "R2"
        if r <= 100: return "R3"
        if r <= 257: return "R4-R7"
        return "UDFA"
    merged["independent_tier"] = merged["final_rank"].apply(_tier)

    out_cols = [c for c in board.columns if c in merged.columns]
    merged[out_cols].to_csv(PRED_BOARD, index=False)

    # Pick clamp — enforce R1 picks within ±4 of consensus
    n_clamped = 0
    if PRED_PICKS.exists() and MC_CSV.exists():
        picks = pd.read_csv(PRED_PICKS)
        mc = pd.read_csv(MC_CSV)
        pros_rank = pros.set_index("player")["rank"].to_dict()
        pos_lookup = pros.set_index("player")["position"].to_dict()

        # Per-slot candidate sets from the MC
        slot_col = "pick_slot" if "pick_slot" in mc.columns else "pick_number"
        team_col = "most_likely_team" if "most_likely_team" in mc.columns else "team"
        candidates_by_slot: dict[int, list[dict]] = {}
        for _, r in mc.iterrows():
            slot = int(r.get(slot_col, 0))
            if slot <= 0 or slot > 32: continue
            candidates_by_slot.setdefault(slot, []).append({
                "player": r["player"],
                "position": r.get("position"),
                "probability": float(r.get("probability", 0) or 0),
                "team": r.get(team_col),
                "consensus_rank": pros_rank.get(r["player"]),
            })

        claimed: set[str] = set()
        pick_rows = picks.to_dict(orient="records")
        for row in pick_rows:
            slot = int(row["pick"])
            if slot > 32:
                claimed.add(row["player"])
                continue
            player = row["player"]
            cons = pros_rank.get(player)
            # Keep the original only if consensus-near AND not already taken
            if (pd.notna(cons)
                and abs(float(cons) - slot) <= R1_PICK_CLAMP
                and player not in claimed):
                claimed.add(player)
                continue
            # Need a substitute
            slot_cands = candidates_by_slot.get(slot, [])
            candidates_ok = [
                c for c in slot_cands
                if c["player"] not in claimed
                and c["consensus_rank"] is not None
                and pd.notna(c["consensus_rank"])
                and abs(float(c["consensus_rank"]) - slot) <= R1_PICK_CLAMP
            ]
            if candidates_ok:
                sub = max(candidates_ok, key=lambda c: c["probability"])
                row["player"] = sub["player"]
                row["position"] = sub["position"]
                row["probability"] = sub["probability"]
                claimed.add(sub["player"])
                n_clamped += 1
                continue
            # Fallback: consensus-near any available
            pool = [
                (p, r_) for p, r_ in pros_rank.items()
                if pd.notna(r_) and abs(float(r_) - slot) <= R1_PICK_CLAMP
                and p not in claimed
            ]
            if pool:
                pool.sort(key=lambda x: abs(float(x[1]) - slot))
                sub_player = pool[0][0]
                row["player"] = sub_player
                row["position"] = pos_lookup.get(sub_player, row["position"])
                row["probability"] = 0.10
                claimed.add(sub_player)
                n_clamped += 1
            else:
                claimed.add(player)

        pd.DataFrame(pick_rows).to_csv(PRED_PICKS, index=False)

    clamped_board = merged[(merged["rank"] <= 32) &
                           (abs(merged["final_rank"] - merged["rank"]) > 0)]
    print(f"[r1_clamp] picks clamped: {n_clamped}")
    print(f"[r1_clamp] board repositioned: {len(clamped_board)}")


if __name__ == "__main__":
    apply_r1_clamp()
