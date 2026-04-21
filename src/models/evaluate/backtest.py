"""Section G — historical backtest (baseline).

Reconstructs a minimal independent-model-style ranking for prior drafts
and scores it against actual outcomes. This is a baseline that shows the
structural Stage 1 ensemble (already analyst-independent) on its own,
without the full team-agent simulation that requires per-year team
profiles we don't have.

Metrics reported per year (R1-only unless noted):
  - exact_match_rate:           player at correct overall pick
  - within_3_pick_rate
  - within_5_pick_rate
  - r1_inclusion_rate:          prospect predicted R1 was picked R1
  - top32_overlap:              |predicted_top32 ∩ actual_r1|

Future work (requires more data):
  - Full 32-team agent sim per year (needs historical team profiles)
  - GM affinity as-of-that-year, not current-only

Usage:  python -m src.models.evaluate.backtest
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
FEATURES = ROOT / "data/features"
OUT = ROOT / "data/processed/backtest_independent.csv"

POS_GROUPS = {
    "QB": {"QB"},
    "SKILL": {"WR", "RB", "TE"},
    "OL": {"T", "G", "C", "OT", "OG", "LS", "IOL"},
}


def _group_for(pos: str) -> str:
    pos = (pos or "").upper()
    for g, s in POS_GROUPS.items():
        if pos in s:
            return g
    return "DEF"


def _score_year(year: int) -> dict | None:
    """Score Stage 1 ensemble-only predictions for a prior year against
    actual draft order. Uses per-group X / y / meta historical files.
    Training is the same temporal-CV as train_stage1 for that fold."""
    import pickle

    import numpy as np

    results = {}
    all_rows_pred = []

    for group in ("QB", "SKILL", "OL", "DEF"):
        X = pd.read_csv(FEATURES / f"X_{group}_historical.csv")
        y = pd.read_csv(FEATURES / f"y_{group}_historical.csv").squeeze("columns")
        meta = pd.read_csv(FEATURES / f"meta_{group}_historical.csv")
        train_mask = meta["year"] < year
        test_mask = meta["year"] == year
        if not test_mask.any() or not train_mask.any():
            continue

        # Re-train on everything before `year`
        from src.models.train_stage1 import fit_ensemble, fit_qb_simple, predict_ensemble
        # Drop any non-numeric columns (same as train_stage1 load_group)
        X = X.select_dtypes(include="number")
        Xtr, ytr = X[train_mask], y[train_mask]
        Xte = X[test_mask]
        if group == "QB":
            models = fit_qb_simple(Xtr, ytr)
        else:
            models = fit_ensemble(Xtr, ytr)
        preds = predict_ensemble(models, Xte)
        for i, idx in enumerate(Xte.index):
            m = meta.loc[idx]
            all_rows_pred.append({
                "year": year,
                "group": group,
                "player": m.get("player", "?"),
                "actual_pick": int(y.loc[idx]),
                "predicted_pick": float(preds[i]),
            })

    if not all_rows_pred:
        return None

    df = pd.DataFrame(all_rows_pred)
    df = df.sort_values("predicted_pick").reset_index(drop=True)
    df["predicted_rank"] = df.index + 1

    # R1 = actual_pick <= 32
    actual_r1 = df[df["actual_pick"] <= 32].copy()
    pred_top32 = df.head(32).copy()

    overlap = set(actual_r1["player"]) & set(pred_top32["player"])
    r1_incl = (pred_top32["actual_pick"] <= 32).mean() if len(pred_top32) else 0.0

    # within-K: compare predicted_rank vs actual_pick for R1-actual players.
    # Drop predicted_rank from actual_r1 to avoid merge conflict, then look up.
    rank_map = dict(zip(df["player"], df["predicted_rank"]))
    actual_r1 = actual_r1.copy()
    actual_r1["predicted_rank"] = actual_r1["player"].map(rank_map)
    diff = (actual_r1["predicted_rank"] - actual_r1["actual_pick"]).abs().dropna()
    within_3 = float((diff <= 3).mean()) if len(diff) else 0.0
    within_5 = float((diff <= 5).mean()) if len(diff) else 0.0
    exact = float((diff == 0).mean()) if len(diff) else 0.0

    return {
        "year": year,
        "n_prospects_scored": len(df),
        "actual_r1_count": len(actual_r1),
        "top32_overlap": len(overlap),
        "top32_overlap_rate": round(len(overlap) / max(1, len(actual_r1)), 3),
        "r1_inclusion_rate": round(r1_incl, 3),
        "within_5_pick_rate": round(within_5, 3),
        "within_3_pick_rate": round(within_3, 3),
        "exact_match_rate": round(exact, 3),
    }


def main():
    results = []
    for y in (2021, 2022, 2023, 2024, 2025):
        r = _score_year(y)
        if r is None:
            continue
        results.append(r)
        print(f"{y}: top32_overlap={r['top32_overlap']}/{r['actual_r1_count']} "
              f"({r['top32_overlap_rate']*100:.1f}%), "
              f"within5={r['within_5_pick_rate']*100:.1f}%, "
              f"exact={r['exact_match_rate']*100:.1f}%")
    if results:
        pd.DataFrame(results).to_csv(OUT, index=False)
        print(f"\nWrote {OUT}")


if __name__ == "__main__":
    main()
