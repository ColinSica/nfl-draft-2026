"""
Add SackSEER-style EDGE projection + analyst bias/herding signals to
prospects_2026_enriched.csv. Apply the KC trade_up_rate override to
team_context_2026_enriched.csv.

Features added to prospects:
  explosion_index                   mean of 40_yard/vertical/broad_jump
                                    percentiles (within historical DEF pool);
                                    NaN when fewer than 1 of the 3 drills
                                    is populated.
  sack_projection_proxy             explosion_index * def_sacks
                                    (true SackSEER uses sacks/snap; we don't
                                    have college snap counts, so absolute
                                    season sacks is the closest substitute).
  scouts_grade_proxy                pff_grade_3yr where present; else
                                    100 * consensus_pct_within_position.
  scouts_grade_primary              pff_grade_3yr
  scouts_grade_secondary            100 * consensus_pct_within_position
  consensus_pct_within_position     higher = more highly-ranked within same
                                    raw position code.
  analyst_disagreement_flag         1 if |pff_rank - consensus_rank| > 15.
                                    Meaningful only where pff_rank exists.
  analyst_herding_score             1 / (1 + |pff_rank - consensus_rank|).
                                    High = analysts agree tightly (herded).
                                    NaN where pff_rank is unavailable — the
                                    true rank_stddev from NFLMDD was blocked
                                    by their anti-bot earlier in the pipeline.
  late_consensus_move               1 if stock_direction != 0. Proxy for the
                                    abs(stock_delta) > 10 signal the user
                                    requested — we have only directional
                                    stock data (-1 / 0 / 1), not numeric deltas.

Team-context updates:
  KC trade_up_rate -> 0.75 (per Veach public comment about R1 trades)
"""

from __future__ import annotations

from bisect import bisect_left
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
PROS_CSV = ROOT / "data" / "processed" / "prospects_2026_enriched.csv"
HIST_CSV = ROOT / "data" / "processed" / "draft_with_college.csv"
TEAM_CSV = ROOT / "data" / "processed" / "team_context_2026_enriched.csv"


def pct_rank(sorted_ref: list[float], val, lower_better: bool = False) -> float:
    if pd.isna(val) or not sorted_ref:
        return np.nan
    i = bisect_left(sorted_ref, float(val))
    p = i / len(sorted_ref)
    return 1.0 - p if lower_better else p


def add_sackseer(pros: pd.DataFrame, hist: pd.DataFrame) -> None:
    def_hist = hist[hist["position_group"] == "DEF"]
    r40 = sorted(def_hist["40_yard"].dropna().astype(float).tolist())
    rvt = sorted(def_hist["vertical"].dropna().astype(float).tolist())
    rbj = sorted(def_hist["broad_jump"].dropna().astype(float).tolist())

    explosion = []
    proxy = []
    for _, row in pros.iterrows():
        if row.get("position_group") != "DEF":
            explosion.append(np.nan)
            proxy.append(np.nan)
            continue
        p40 = pct_rank(r40, row.get("40_yard"), lower_better=True)
        pvt = pct_rank(rvt, row.get("vertical"))
        pbj = pct_rank(rbj, row.get("broad_jump"))
        parts = [p for p in (p40, pvt, pbj) if pd.notna(p)]
        if not parts:
            explosion.append(np.nan)
            proxy.append(np.nan)
            continue
        exp_val = sum(parts) / len(parts)
        sacks = row.get("def_sacks")
        prox = exp_val * float(sacks) if pd.notna(sacks) else np.nan
        explosion.append(exp_val)
        proxy.append(prox)
    pros["explosion_index"] = explosion
    pros["sack_projection_proxy"] = proxy


def add_analyst_signals(pros: pd.DataFrame) -> None:
    # Consensus percentile within raw position (higher = more elite at position)
    def pct_within(series: pd.Series) -> pd.Series:
        # lowest rank gets highest percentile
        ranked = series.rank(method="min", ascending=True)
        n = series.notna().sum()
        if n <= 1:
            return pd.Series([1.0 if v else np.nan for v in series.notna()], index=series.index)
        return 1.0 - (ranked - 1) / max(n - 1, 1)

    pros["consensus_pct_within_position"] = pros.groupby("position")["rank"].transform(pct_within)

    pros["scouts_grade_primary"] = pros["pff_grade_3yr"]
    pros["scouts_grade_secondary"] = pros["consensus_pct_within_position"] * 100
    pros["scouts_grade_proxy"] = pros["scouts_grade_primary"].fillna(pros["scouts_grade_secondary"])

    has_both = pros["pff_rank"].notna() & pros["rank"].notna()
    diff = (pros["pff_rank"] - pros["rank"]).abs()

    pros["analyst_disagreement_flag"] = 0
    pros.loc[has_both & (diff > 15), "analyst_disagreement_flag"] = 1

    herding = pd.Series(np.nan, index=pros.index, dtype=float)
    herding[has_both] = 1.0 / (1.0 + diff[has_both])
    pros["analyst_herding_score"] = herding

    sd = pros.get("stock_direction", pd.Series([0] * len(pros))).fillna(0)
    pros["late_consensus_move"] = (sd != 0).astype(int)


def update_kc_trade_up(team: pd.DataFrame) -> None:
    mask = team["team"] == "KC"
    if not mask.any():
        print("KC rows not found — skipping trade_up_rate override")
        return
    before = float(team.loc[mask, "trade_up_rate"].iloc[0])
    team.loc[mask, "trade_up_rate"] = 0.75
    print(f"KC trade_up_rate: {before:.2f} -> 0.75")


def main():
    pros = pd.read_csv(PROS_CSV)
    hist = pd.read_csv(HIST_CSV)
    team = pd.read_csv(TEAM_CSV)

    # Drop prior versions so the script is idempotent
    for c in ("explosion_index", "sack_projection_proxy",
              "scouts_grade_proxy", "scouts_grade_primary",
              "scouts_grade_secondary", "consensus_pct_within_position",
              "analyst_disagreement_flag", "analyst_herding_score",
              "late_consensus_move"):
        if c in pros.columns:
            pros = pros.drop(columns=[c])

    add_sackseer(pros, hist)
    add_analyst_signals(pros)
    update_kc_trade_up(team)

    pros.to_csv(PROS_CSV, index=False)
    team.to_csv(TEAM_CSV, index=False)

    print(f"\nprospects_2026_enriched.csv: {pros.shape[1]} cols")
    for c in ("explosion_index", "sack_projection_proxy", "scouts_grade_proxy",
              "analyst_disagreement_flag", "analyst_herding_score",
              "late_consensus_move"):
        n = int(pros[c].notna().sum())
        print(f"  {c:<32} non-null={n}")

    # Top EDGE by sack projection
    edge = pros[(pros["position"] == "EDGE") & pros["sack_projection_proxy"].notna()]
    if not edge.empty:
        print("\nTop 10 EDGE by sack_projection_proxy:")
        cols = ["player", "college", "40_yard", "vertical", "broad_jump",
                "def_sacks", "explosion_index", "sack_projection_proxy", "rank"]
        show = edge.nlargest(10, "sack_projection_proxy")[cols].copy()
        for c in ("40_yard", "vertical", "broad_jump", "explosion_index",
                  "sack_projection_proxy"):
            show[c] = pd.to_numeric(show[c], errors="coerce").round(2)
        print(show.to_string(index=False))

    # Analyst disagreement highlights (within top 25 where pff_rank exists)
    dis = pros[pros["analyst_disagreement_flag"] == 1]
    if not dis.empty:
        print(f"\nAnalyst disagreement flagged ({len(dis)} prospects):")
        print(dis[["player", "position", "rank", "pff_rank", "pff_grade_3yr"]]
              .to_string(index=False))


if __name__ == "__main__":
    main()
