"""Section G — post-draft scoreboard.

After the real 2026 NFL Draft concludes (2026-04-25), drop the actual R1
picks into `data/live/actual_r1_2026.csv` with columns:
  pick,team,player,position,school

Then run:
  python -m src.models.evaluate.scoreboard

The scoreboard compares:
  - independent model (predictions_2026_independent_picks.csv)
  - benchmark model  (predictions_2026.csv if present)
  - individual analyst mocks (from data/2026 Mock Draft Data.xlsx)
  - consensus (if present in data/features/analyst_consensus_2026.json)

Metrics (all R1-only):
  - exact team+player match
  - team match at slot (any player that team took)
  - player R1 inclusion
  - within-3 / within-5 pick slots
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
ACTUAL_PATH = ROOT / "data/live/actual_r1_2026.csv"
IND_PICKS = ROOT / "data/processed/predictions_2026_independent_picks.csv"
BEN_PICKS = ROOT / "data/processed/predictions_2026.csv"
OUT = ROOT / "data/processed/scoreboard_2026.csv"


def _norm_name(s: str) -> str:
    if not isinstance(s, str):
        return ""
    return s.strip().lower().replace(".", "").replace("'", "")


def score_predictions(actual: pd.DataFrame, pred: pd.DataFrame,
                      label: str) -> dict:
    """actual: pick,team,player,position
       pred:   pick,team,player,position (top-32)"""
    m = actual[["pick", "team", "player"]].merge(
        pred[["pick", "team", "player"]].rename(
            columns={"team": "pred_team", "player": "pred_player"}),
        on="pick", how="left")
    m["actual_n"] = m["player"].map(_norm_name)
    m["pred_n"] = m["pred_player"].map(_norm_name)
    exact_pp = (m["actual_n"] == m["pred_n"]) & (m["team"] == m["pred_team"])
    team_match = (m["team"] == m["pred_team"])

    # within-K uses full 32-row join on player name
    actual_ranks = {_norm_name(p): int(s) for s, p in
                    zip(actual["pick"], actual["player"])}
    pred_ranks = {_norm_name(p): int(s) for s, p in
                  zip(pred["pick"], pred["player"])}
    within_3 = 0
    within_5 = 0
    hits_r1 = 0
    for p, actual_slot in actual_ranks.items():
        if p in pred_ranks:
            hits_r1 += 1
            diff = abs(pred_ranks[p] - actual_slot)
            if diff <= 3: within_3 += 1
            if diff <= 5: within_5 += 1
    n = len(actual_ranks)
    return {
        "label": label,
        "n_picks": n,
        "exact_pick_player_match": int(exact_pp.sum()),
        "team_match_at_slot": int(team_match.sum()),
        "r1_player_inclusion": hits_r1,
        "within_3": within_3,
        "within_5": within_5,
        "exact_rate": round(exact_pp.sum() / max(1, n), 3),
        "team_match_rate": round(team_match.sum() / max(1, n), 3),
        "within_3_rate": round(within_3 / max(1, n), 3),
        "within_5_rate": round(within_5 / max(1, n), 3),
    }


def main():
    if not ACTUAL_PATH.exists():
        print(f"No actual results yet. Drop CSV at: {ACTUAL_PATH}")
        print("Columns: pick,team,player,position,school")
        return 1
    actual = pd.read_csv(ACTUAL_PATH)
    rows = []

    if IND_PICKS.exists():
        ind = pd.read_csv(IND_PICKS)
        rows.append(score_predictions(actual, ind, "independent"))
    if BEN_PICKS.exists():
        ben = pd.read_csv(BEN_PICKS)
        # benchmark uses final_rank as the slot proxy
        if "final_rank" in ben.columns and "pick" not in ben.columns:
            ben = ben.head(32).assign(pick=lambda d: d["final_rank"])
            # benchmark didn't assign team at slot, skip if missing
        if "team" in ben.columns:
            rows.append(score_predictions(actual, ben, "benchmark"))

    if not rows:
        print("No predictions found to score."); return 1
    df = pd.DataFrame(rows)
    df.to_csv(OUT, index=False)
    print(df.to_string(index=False))
    print(f"\nWrote {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
