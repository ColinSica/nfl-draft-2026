"""
Stage 2 — team-player match with dynamic BPA/need weights + Monte Carlo.

Scoring per (prospect, pick slot):
    score = (1 - final_score/728) * bpa_weight
          + need_match_score * need_weight
          + visit_flag * 0.15
          + intel_link_for_team * 0.10

    - bpa_weight / need_weight come from team_context (win_pct-driven)
    - need_match_score: 1.0 when canonical position is in team top-3 needs,
      0 otherwise. Forced to 0 when the position is "locked" (QB with
      qb_urgency == 0). need_created_by_departure isn't available in the
      pipeline; the 1.5 branch would require that data.
    - proximity constraint: consensus_rank > 3 * pick_number halves the score

Monte Carlo:
    500 simulated drafts. Each sim:
      - perturb final_score per prospect with N(0, 15) noise
      - iterate picks in order; at each pick, optionally trigger a trade
        event (pick_range_trade_rate) that swaps team ownership with a later
        pick whose owner has highest trade_up_rate AND has unmet need at the
        top available player's position.
      - select top-scoring available prospect
      - record (pick_slot, owning_team, player) tuple

Outputs:
    data/processed/stage2_team_picks.csv     top-3-per-pick (no scarcity)
    data/processed/stage2_mock_draft.csv     single greedy simulation
    data/processed/monte_carlo_2026.csv      per-player landing probabilities
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
PROS_CSV = ROOT / "data" / "processed" / "prospects_2026_enriched.csv"
PRED_CSV = ROOT / "data" / "processed" / "predictions_2026.csv"
TEAM_CTX = ROOT / "data" / "processed" / "team_context_2026_enriched.csv"
TEAM_NEEDS = ROOT / "data" / "processed" / "team_needs_2026.csv"
OUT_TOP3 = ROOT / "data" / "processed" / "stage2_team_picks.csv"
OUT_MOCK = ROOT / "data" / "processed" / "stage2_mock_draft.csv"
OUT_MC = ROOT / "data" / "processed" / "monte_carlo_2026.csv"

N_SIMULATIONS = 500
NOISE_STD_FINAL_SCORE = 15.0
RNG_SEED = 42

# 2026 class narrative: EDGE/OT/CB are deep (teams can wait);
# QB/WR are thin (teams must spend early capital).
DEEP_CLASS_POSITIONS = {"EDGE", "OT", "CB"}
THIN_CLASS_POSITIONS = {"QB", "WR"}
DEEP_CLASS_MULT = 0.8
THIN_CLASS_MULT = 1.3

POS_TO_NEEDS = {
    "QB": "QB",
    "RB": "RB", "FB": "RB", "HB": "RB",
    "WR": "WR", "TE": "TE",
    "OT": "OL", "G": "OL", "C": "OL", "OG": "OL", "IOL": "OL", "T": "OL",
    "EDGE": "EDGE", "DE": "EDGE",
    "DL": "DL", "DT": "DL", "NT": "DL",
    "LB": "LB", "ILB": "LB", "OLB": "LB", "MLB": "LB",
    "CB": "CB", "DB": "CB",
    "S": "S", "FS": "S", "SS": "S", "SAF": "S",
}

NICKNAMES = {
    "49ers": "SF", "Bears": "CHI", "Bengals": "CIN", "Bills": "BUF",
    "Broncos": "DEN", "Browns": "CLE", "Buccaneers": "TB", "Cardinals": "ARI",
    "Chargers": "LAC", "Chiefs": "KC", "Colts": "IND", "Commanders": "WAS",
    "Cowboys": "DAL", "Dolphins": "MIA", "Eagles": "PHI", "Falcons": "ATL",
    "Giants": "NYG", "Jaguars": "JAX", "Jets": "NYJ", "Lions": "DET",
    "Packers": "GB", "Panthers": "CAR", "Patriots": "NE", "Raiders": "LV",
    "Rams": "LAR", "Ravens": "BAL", "Saints": "NO", "Seahawks": "SEA",
    "Steelers": "PIT", "Texans": "HOU", "Titans": "TEN", "Vikings": "MIN",
}


def parse_visits(s) -> set[str]:
    if not isinstance(s, str) or not s.strip():
        return set()
    out: set[str] = set()
    for part in s.split(","):
        p = part.strip()
        if p in NICKNAMES:
            out.add(NICKNAMES[p])
        elif 2 <= len(p) <= 3:
            out.add(p.upper())
    return out


def load_data():
    prospects = pd.read_csv(PROS_CSV)
    preds = pd.read_csv(PRED_CSV)
    prospects = prospects.merge(
        preds[["player", "final_score", "model_pred"]], how="left", on="player")

    team_ctx = pd.read_csv(TEAM_CTX)
    needs = pd.read_csv(TEAM_NEEDS)

    top3_needs: dict[str, list[str]] = {}
    for t, sub in needs.groupby("team"):
        top3_needs[t] = sub.sort_values("need_rank").head(3)["position"].tolist()

    qb_urgency_map = dict(zip(team_ctx["team"], team_ctx["qb_urgency"]))

    prospects["_visit_set"] = prospects["visited_teams"].apply(parse_visits)
    prospects["_needs_pos"] = prospects["position"].map(POS_TO_NEEDS).fillna("OTHER")

    return prospects, team_ctx, needs, top3_needs, qb_urgency_map


def compute_scores(prospects: pd.DataFrame, pick_row: pd.Series,
                   top3_needs: dict, qb_urgency_map: dict,
                   final_score_col: str = "final_score") -> pd.Series:
    """Vectorized scoring of every prospect against a single pick slot."""
    team = pick_row["team"]
    pick_num = int(pick_row["pick_number"])
    bpa_w = float(pick_row["bpa_weight"])
    need_w = float(pick_row["need_weight"])

    # BPA term
    final_sc = prospects[final_score_col].clip(lower=0, upper=728).fillna(728)
    bpa_term = (1 - final_sc / 728.0) * bpa_w

    # Need match
    pos_canon = prospects["_needs_pos"]
    top3 = top3_needs.get(team, [])
    need_match = pos_canon.isin(top3).astype(float)
    # QB lock override
    if qb_urgency_map.get(team, 1.0) == 0.0:
        need_match = need_match.where(pos_canon != "QB", 0.0)

    # Position scarcity narrative: deep class (EDGE/OT/CB) downweighted,
    # thin class (QB/WR) upweighted.
    raw_pos = prospects["position"].fillna("").astype(str).str.upper()
    scarcity_mult = pd.Series(1.0, index=prospects.index)
    scarcity_mult = scarcity_mult.where(~raw_pos.isin(DEEP_CLASS_POSITIONS),
                                        DEEP_CLASS_MULT)
    scarcity_mult = scarcity_mult.where(~raw_pos.isin(THIN_CLASS_POSITIONS),
                                        THIN_CLASS_MULT)

    need_term = need_match * need_w * scarcity_mult

    # Visit
    visit_flag = prospects["_visit_set"].apply(lambda s: 1 if team in s else 0)
    visit_term = visit_flag * 0.15

    # Intel
    intel_flag = (prospects["intel_top_team"] == team).astype(float)
    intel_term = intel_flag * prospects["intel_link_max"].fillna(0) * 0.10

    score = bpa_term + need_term + visit_term + intel_term

    # Proximity constraint: cons_rank > 3 * pick_number -> 50% penalty
    cons = prospects["rank"]
    far = cons > (3 * pick_num)
    score = score.where(~far, score * 0.5)

    return score


def greedy_mock_draft(prospects: pd.DataFrame, picks: list[dict],
                      top3_needs: dict, qb_urgency_map: dict) -> list[dict]:
    taken: set[int] = set()
    results = []
    for pick in picks:
        scores = compute_scores(
            prospects, pd.Series(pick), top3_needs, qb_urgency_map)
        scores_avail = scores[~prospects.index.isin(taken)]
        if scores_avail.empty:
            break
        winner = scores_avail.idxmax()
        taken.add(winner)
        p = prospects.loc[winner]
        results.append({
            "pick_number": pick["pick_number"], "team": pick["team"],
            "player": p["player"], "position": p["position"],
            "college": p.get("college"), "consensus_rank": p.get("rank"),
            "score": float(scores.loc[winner]),
            "need_match": p["_needs_pos"] if p["_needs_pos"]
                          in top3_needs.get(pick["team"], []) else "",
            "visit_flag": 1 if pick["team"] in p["_visit_set"] else 0,
        })
    return results


def simulate_one(prospects: pd.DataFrame, picks: list[dict],
                 top3_needs: dict, qb_urgency_map: dict,
                 rng: np.random.Generator) -> list[dict]:
    # Noise on final_score for this sim only
    local = prospects.copy()
    local["final_score_noised"] = (local["final_score"].fillna(500)
                                   + rng.normal(0, NOISE_STD_FINAL_SCORE,
                                                size=len(local)))

    picks_working = [dict(p) for p in picks]
    taken: set[int] = set()
    results = []

    for i, pick in enumerate(picks_working):
        scores = compute_scores(local, pd.Series(pick), top3_needs,
                                qb_urgency_map,
                                final_score_col="final_score_noised")
        scores_avail = scores[~local.index.isin(taken)]
        if scores_avail.empty:
            break

        # Trade event
        rate = pick.get("pick_range_trade_rate") or 0
        if rng.random() < rate:
            top_idx = scores_avail.idxmax()
            top_pos = local.loc[top_idx, "_needs_pos"]
            # Find a later pick whose team has need at top_pos AND highest trade_up_rate
            best_j, best_rate = None, -1.0
            for j in range(i + 1, len(picks_working)):
                p2 = picks_working[j]
                if (top_pos in top3_needs.get(p2["team"], [])
                        and (p2.get("trade_up_rate") or 0) > best_rate):
                    best_rate = p2.get("trade_up_rate") or 0
                    best_j = j
            if best_j is not None and best_rate > 0.5:
                swap_cols = ("team", "bpa_weight", "need_weight",
                             "trade_up_rate", "trade_down_rate",
                             "pick_range_trade_rate")
                for c in swap_cols:
                    picks_working[i][c], picks_working[best_j][c] = (
                        picks_working[best_j].get(c),
                        picks_working[i].get(c),
                    )
                # Recompute scores for the swapped team
                scores = compute_scores(local, pd.Series(picks_working[i]),
                                        top3_needs, qb_urgency_map,
                                        final_score_col="final_score_noised")
                scores_avail = scores[~local.index.isin(taken)]

        winner = scores_avail.idxmax()
        taken.add(winner)
        results.append({
            "pick_number": picks_working[i]["pick_number"],
            "team": picks_working[i]["team"],
            "player_idx": int(winner),
        })
    return results


def main():
    prospects, team_ctx, needs, top3_needs, qb_urgency_map = load_data()

    r1 = team_ctx[team_ctx["round"] == 1].sort_values("pick_number").copy()
    picks = r1.to_dict(orient="records")

    # --- Top-3 per pick (no scarcity) ---
    top3_rows = []
    for pick in picks:
        scores = compute_scores(prospects, pd.Series(pick),
                                top3_needs, qb_urgency_map)
        top_idx = scores.nlargest(3).index
        for rank, idx in enumerate(top_idx, start=1):
            p = prospects.loc[idx]
            top3_rows.append({
                "pick_number": pick["pick_number"], "team": pick["team"],
                "match_rank": rank, "player": p["player"],
                "position": p["position"], "consensus_rank": p.get("rank"),
                "score": float(scores.loc[idx]),
                "need_match": p["_needs_pos"] if p["_needs_pos"]
                              in top3_needs.get(pick["team"], []) else "",
            })
    pd.DataFrame(top3_rows).to_csv(OUT_TOP3, index=False)

    # --- Greedy single mock draft ---
    mock_results = greedy_mock_draft(prospects, picks, top3_needs, qb_urgency_map)
    mock_df = pd.DataFrame(mock_results)
    mock_df.to_csv(OUT_MOCK, index=False)
    print("Round 1 MOCK DRAFT (greedy, new scoring):")
    print(f"{'pk':>2}  {'team':<4}  {'player':<24}  {'pos':<5}  cons  score  need  v")
    print("-" * 75)
    for r in mock_results:
        cons = int(r["consensus_rank"]) if pd.notna(r["consensus_rank"]) else "?"
        print(f"{r['pick_number']:>2}  {r['team']:<4}  {r['player']:<24}  "
              f"{r['position']:<5}  {cons:>4}  {r['score']:5.2f}  "
              f"{r['need_match']:<5}  {r['visit_flag']}")

    # --- Monte Carlo ---
    print(f"\nRunning {N_SIMULATIONS} Monte Carlo simulations...")
    rng = np.random.default_rng(RNG_SEED)
    # landing[player_idx][pick_slot] = count
    landing_counts: dict[int, dict[int, int]] = {}
    # team[player_idx][team] = count (across all slots)
    team_counts: dict[int, dict[str, int]] = {}
    # also track team-per-slot combos for most_likely_team at preferred slot
    slot_team_counts: dict[int, dict[int, dict[str, int]]] = {}

    for sim in range(N_SIMULATIONS):
        res = simulate_one(prospects, picks, top3_needs, qb_urgency_map, rng)
        for r in res:
            pi = r["player_idx"]
            pk = r["pick_number"]
            tm = r["team"]
            landing_counts.setdefault(pi, {})
            landing_counts[pi][pk] = landing_counts[pi].get(pk, 0) + 1
            team_counts.setdefault(pi, {})
            team_counts[pi][tm] = team_counts[pi].get(tm, 0) + 1
            slot_team_counts.setdefault(pi, {})
            slot_team_counts[pi].setdefault(pk, {})
            slot_team_counts[pi][pk][tm] = slot_team_counts[pi][pk].get(tm, 0) + 1
        if (sim + 1) % 100 == 0:
            print(f"  ...{sim + 1}/{N_SIMULATIONS} sims done")

    # Aggregate
    mc_rows = []
    for pi, slot_dict in landing_counts.items():
        total = sum(slot_dict.values())
        most_slot = max(slot_dict, key=slot_dict.get)
        prob = slot_dict[most_slot] / N_SIMULATIONS
        teams_at_slot = slot_team_counts[pi][most_slot]
        most_team = max(teams_at_slot, key=teams_at_slot.get)
        # Variance of landing pick (std dev of pick numbers weighted by count)
        pick_values = list(slot_dict.keys())
        pick_weights = list(slot_dict.values())
        mean_pick = sum(p * w for p, w in zip(pick_values, pick_weights)) / total
        var_pick = sum(w * (p - mean_pick) ** 2
                       for p, w in zip(pick_values, pick_weights)) / total
        mc_rows.append({
            "player": prospects.loc[pi, "player"],
            "position": prospects.loc[pi, "position"],
            "college": prospects.loc[pi, "college"],
            "consensus_rank": prospects.loc[pi, "rank"],
            "pick_slot": most_slot,
            "probability": prob,
            "most_likely_team": most_team,
            "n_sims_drafted_round1": total,
            "mean_landing_pick": mean_pick,
            "variance_landing_pick": var_pick,
        })

    mc_df = pd.DataFrame(mc_rows).sort_values("pick_slot")
    mc_df.to_csv(OUT_MC, index=False)
    print(f"\nSaved -> {OUT_MC}  ({len(mc_df)} unique players landed in R1 "
          f"across {N_SIMULATIONS} sims)")

    # --- Top candidate per pick 1-32 with probability ---
    print("\nMonte Carlo top candidate per pick slot (1-32):")
    print(f"{'pk':>2}  {'team':<4}  {'top player':<26}  prob  cons  pos")
    print("-" * 72)
    for pk in range(1, 33):
        candidates = [(pi, slots.get(pk, 0))
                      for pi, slots in landing_counts.items()
                      if slots.get(pk, 0) > 0]
        if not candidates:
            continue
        candidates.sort(key=lambda x: -x[1])
        pi, count = candidates[0]
        p = prospects.loc[pi]
        team_counts_at_pk = slot_team_counts[pi][pk]
        most_team = max(team_counts_at_pk, key=team_counts_at_pk.get)
        prob = count / N_SIMULATIONS
        cons = int(p["rank"]) if pd.notna(p["rank"]) else "?"
        print(f"{pk:>2}  {most_team:<4}  {p['player']:<26}  {prob:.0%}  "
              f"{cons:>4}  {p['position']}")

    # --- Highest variance players ---
    print("\nMost uncertain landing spots (highest variance in pick number):")
    top_var = mc_df.nlargest(10, "variance_landing_pick")
    print(top_var[["player", "position", "consensus_rank",
                   "pick_slot", "probability",
                   "variance_landing_pick"]].to_string(index=False))


if __name__ == "__main__":
    main()
