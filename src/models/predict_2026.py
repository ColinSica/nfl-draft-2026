"""
predict_2026.py — inference + blending for the 2026 draft class.

Pipeline
--------
  1. Load 4 trained position-specific ensembles from models/{group}_ensemble.pkl
  2. Split prospects_2026_enriched.csv by position group
  3. Predict pick number via the group's ensemble
  4. Blend:  final_score = 0.6 * model_pred + 0.4 * consensus_rank
  5. PFF re-rank (only rows with pff_rank populated):
       adj = (pff_rank - consensus_rank) * 0.15
       final_score += adj
  6. Rank by final_score; attach confidence tier; save + print top 32.

Notes
-----
- position code `IOL` (used on the 2026 board) is routed to the OL model
  (historical uses G/C/OG; same role).
- Prospects with unknown position codes fall through to DEF.
"""

from __future__ import annotations

import pickle
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src" / "models"))
from train_stage1 import predict_ensemble  # noqa: E402

MODELS_DIR = ROOT / "models"
PROS_CSV = ROOT / "data" / "processed" / "prospects_2026_enriched.csv"
OUT_CSV = ROOT / "data" / "processed" / "predictions_2026.csv"

INFERENCE_POS_MASKS = {
    "QB": {"QB"},
    "SKILL": {"WR", "RB", "TE"},
    "OL": {"T", "G", "C", "OT", "OG", "LS", "IOL"},
}

W_MODEL = 0.4
W_CONSENSUS = 0.6
W_PFF = 0.15

NEW_HC_TEAMS = {"LV", "NYJ", "ARI", "TEN", "NYG", "CLE", "MIA", "BUF"}
DIVERGENCE_THRESHOLD = 30


def predict_group(pros_slice: pd.DataFrame, group: str) -> np.ndarray:
    pkl = MODELS_DIR / f"{group}_ensemble.pkl"
    with open(pkl, "rb") as f:
        models = pickle.load(f)
    raw_cols = [c for c in models["state"]["feature_cols"]
                if not c.startswith("miss_")]
    X = pros_slice.reindex(columns=raw_cols)
    return predict_ensemble(models, X)


def confidence_tier(row: pd.Series) -> str:
    v = row.get("visit_count", 0)
    if pd.isna(v):
        v = 0
    cr = row["consensus_rank"]
    mp = row["model_pred"]
    if (pd.notna(cr) and pd.notna(mp)
            and v >= 1 and cr <= 50 and abs(mp - cr) < 20):
        return "HIGH"
    if (pd.notna(cr) and cr <= 100) or v >= 1:
        return "MEDIUM"
    return "LOW"


def main():
    pros = pd.read_csv(PROS_CSV)

    # Route each prospect to its inference group
    pos = pros["position"].fillna("").astype(str).str.upper()
    group_col = pd.Series("DEF", index=pros.index)
    for g, mask in INFERENCE_POS_MASKS.items():
        group_col[pos.isin(mask)] = g
    pros["_infer_group"] = group_col
    print("Prospects by inference group:")
    print(pros["_infer_group"].value_counts().to_string())

    # Predict per group
    pros["model_pred"] = np.nan
    for g in ("QB", "SKILL", "OL", "DEF"):
        idx = pros.index[pros["_infer_group"] == g]
        if len(idx) == 0:
            continue
        preds = predict_group(pros.loc[idx], g)
        pros.loc[idx, "model_pred"] = preds

    # Blend model prediction with consensus rank, with a COVERAGE-AWARE
    # weight. Tier-1 analyst agreement is very strong for ranks 1-30 (a
    # Caleb Downs at #8 is cross-validated across every board) but
    # deteriorates past rank 60 and collapses past 100. Weight matches
    # this:
    #   rank <= 30:  W_consensus = 0.85  (strong cross-analyst agreement)
    #   rank 31-60:  W_consensus = 0.70
    #   rank 61-100: W_consensus = 0.50
    #   rank 101-150: W_consensus = 0.35
    #   rank > 150:  W_consensus = 0.20  (model dominates)
    # This stops the model from being a consensus remix in deep rounds —
    # we want the stage-1 ML reasoning (PFF, RAS, visits, conference,
    # age, production) to drive late-round projections — while still
    # trusting dense consensus for the top of the board.
    pros["consensus_rank"] = pros["rank"]
    cr = pros["consensus_rank"]
    w_c = pd.Series(0.20, index=pros.index)
    w_c = w_c.where(~(cr <= 150), 0.35)
    w_c = w_c.where(~(cr <= 100), 0.50)
    w_c = w_c.where(~(cr <= 60),  0.70)
    w_c = w_c.where(~(cr <= 30),  0.85)
    w_m = 1.0 - w_c
    pros["final_score"] = w_m * pros["model_pred"] + w_c * pros["consensus_rank"]

    # PFF re-rank where available
    has_pff = pros["pff_rank"].notna() & pros["consensus_rank"].notna()
    if has_pff.any():
        adj = (pros.loc[has_pff, "pff_rank"]
               - pros.loc[has_pff, "consensus_rank"]) * W_PFF
        pros.loc[has_pff, "final_score"] += adj

    # -------- Reasoning bonuses -----------------------------------------
    # These encode the qualitative factors analysts use to bump players
    # up/down (NOT a rank blend — concrete rationale). Added as final_score
    # deltas so a prospect's projection reflects the same signals an
    # analyst looks at, rather than just riding the consensus.
    #
    # Sign convention: final_score is projected pick slot (lower = better),
    # so bonuses SUBTRACT (moving player earlier) and penalties ADD
    # (pushing later). Magnitudes are calibrated so no single factor
    # exceeds ~3-4 picks of influence on a Day-2 prospect, and half that
    # on a top-30 prospect (where consensus already captures most signal).
    #
    # dampen = amplitude scaler that's 0.4 for top-30, scaling up to 1.0
    # for rank-150+. This lets reasoning drive late-round rankings (the
    # user's goal: extend to R2-R4) without sabotaging the top-30 where
    # cross-analyst agreement is strong.
    dampen = (pros["consensus_rank"].fillna(250) / 100).clip(0.4, 1.0)

    # Visit count — top-30 visits are a lagging indicator of team interest.
    # A Day-2 prospect with 5+ documented visits rarely falls past R3.
    if "visit_count" in pros.columns:
        v = pros["visit_count"].fillna(0).clip(upper=10)
        pros["final_score"] -= v * 0.30 * dampen

    # Senior Bowl / combine invite — pre-draft exposure boost. Analysts
    # routinely cite Senior Bowl week performance as a riser trigger.
    if "senior_bowl_standout" in pros.columns:
        pros["final_score"] -= pros["senior_bowl_standout"].fillna(0) * 1.5 * dampen
    if "senior_bowl_invite" in pros.columns:
        pros["final_score"] -= pros["senior_bowl_invite"].fillna(0) * 0.5 * dampen
    if "combine_invite" in pros.columns:
        pros["final_score"] -= pros["combine_invite"].fillna(0) * 0.8 * dampen

    # RAS — elite athleticism is a late-round riser driver. Effect already
    # grows with depth via the dampen factor, so no separate scaling here.
    if "ras_score" in pros.columns and "ras_reliable" in pros.columns:
        ras = pros["ras_score"].fillna(0)
        reliable = pros["ras_reliable"].fillna(0)
        pros["final_score"] -= (ras - 5).clip(lower=0) * reliable * 0.25 * dampen

    # Injury flags — push players LATER. Scale by consensus rank: R1 locks
    # with minor flags still go R1, but Day-2 guys with flags fall harder.
    if "has_injury_flag" in pros.columns:
        inj = pros["has_injury_flag"].fillna(0)
        pros["final_score"] += inj * 2.0 * dampen
    if "acl_flag" in pros.columns:
        pros["final_score"] += pros["acl_flag"].fillna(0) * 4.0 * dampen

    # Conference tier — SEC/B1G/ACC/Big-12 pipeline boost vs G5. Analysts
    # explicitly cite "level of competition" as a downgrade signal.
    if "conference_tier" in pros.columns:
        ct = pros["conference_tier"].fillna(3)
        pros["final_score"] += (ct - 1) * 0.8 * dampen

    # Age — older prospects (5th/6th years) lose ceiling. Analysts weight
    # age heavily for late-round projection.
    if "age" in pros.columns:
        age = pros["age"].fillna(22)
        age_penalty = (age - 22).clip(lower=0) * 0.6 * dampen
        pros["final_score"] += age_penalty

    # Position scarcity in class — a mid-tier QB in a weak QB class goes
    # earlier than his raw grade. Uses the PFF-derived class scarcity
    # signal if present.
    if "position_scarcity_vs_historical" in pros.columns:
        scarcity = pros["position_scarcity_vs_historical"].fillna(0)
        pros["final_score"] -= scarcity * 1.0 * dampen

    pros = pros.sort_values("final_score").reset_index(drop=True)
    pros["final_rank"] = np.arange(1, len(pros) + 1)
    pros["confidence_tier"] = pros.apply(confidence_tier, axis=1)

    # --- Warning flags (task 3) ---
    # new_gm_flag: intel's top-linked team is a new-HC situation
    pros["new_gm_flag"] = pros["intel_top_team"].isin(NEW_HC_TEAMS).astype(int)

    # trade_risk_flag: look up the pick_range_trade_rate at the prospect's
    # consensus_rank (only meaningful for ranks 1-257 = actual draft slots)
    team_ctx = pd.read_csv(ROOT / "data" / "processed" / "team_context_2026_enriched.csv")
    rate_by_pick = dict(zip(team_ctx["pick_number"], team_ctx["pick_range_trade_rate"]))
    pros["trade_risk_flag"] = pros["consensus_rank"].map(rate_by_pick)

    # positional_value_tension already exists on the enriched file; just carry through
    if "positional_value_tension" not in pros.columns:
        pros["positional_value_tension"] = 0

    # model_consensus_divergence
    pros["model_consensus_divergence"] = (
        pros["model_pred"] - pros["consensus_rank"]).abs()
    pros["model_consensus_divergence_flag"] = (
        pros["model_consensus_divergence"] > DIVERGENCE_THRESHOLD).astype(int)

    out_cols = ["final_rank", "player", "position", "college",
                "model_pred", "consensus_rank", "final_score",
                "pff_grade_3yr", "visit_count", "top30_visit_flag",
                "market_consensus_score", "confidence_tier",
                "new_gm_flag", "trade_risk_flag", "positional_value_tension",
                "model_consensus_divergence", "model_consensus_divergence_flag"]
    out = pros[out_cols].copy()
    out.rename(columns={"college": "school"}, inplace=True)
    out.to_csv(OUT_CSV, index=False)
    print(f"\nSaved -> {OUT_CSV}  ({len(out)} rows)")

    print("\nConfidence tier counts:")
    print(out["confidence_tier"].value_counts().to_string())

    print("\nTop 32 predictions:")
    display = out.head(32).copy()
    for c in ("model_pred", "final_score", "pff_grade_3yr",
              "market_consensus_score"):
        if c in display.columns:
            display[c] = pd.to_numeric(display[c], errors="coerce").round(2)
    print(display.to_string(index=False))


if __name__ == "__main__":
    main()
