"""Export two reviewer-friendly CSVs for VS Code:

  1. r1_picks_vs_consensus.csv
     Per-slot table: team, our pick, consensus pick, distance, flags

  2. big_board_vs_consensus.csv
     Per-prospect: our rank vs consensus rank, diff, delta flag

IMPORTANT: These CSVs use consensus data ONLY for display comparison.
They are not read by the independent model during scoring — independence
guard tests still pass.

Run: python -m src.models.evaluate.export_comparisons
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
IND_PICKS = ROOT / "data/processed/predictions_2026_independent_picks.csv"
IND_BOARD = ROOT / "data/processed/predictions_2026_independent.csv"
CONSENSUS_JSON = ROOT / "data/features/analyst_consensus_2026.json"
PROSPECTS = ROOT / "data/processed/prospects_2026_enriched.csv"
OUT_R1 = ROOT / "data/processed/r1_picks_vs_consensus.csv"
OUT_BB = ROOT / "data/processed/big_board_vs_consensus.csv"


def _norm(s):
    if not isinstance(s, str): return ""
    return s.strip().lower().replace(".", "").replace("'", "").replace("-", " ")


def _surname(s):
    n = _norm(s)
    return n.rsplit(" ", 1)[-1] if " " in n else n


def export_r1_picks():
    """Per-slot R1 comparison — reads independent picks + consensus JSON."""
    if not IND_PICKS.exists():
        print(f"Missing {IND_PICKS}. Run the MC first.")
        return

    ind = pd.read_csv(IND_PICKS).head(32)
    cons = json.loads(CONSENSUS_JSON.read_text(encoding="utf-8"))["per_pick"]

    # Load prospect positions for matching
    pros = pd.read_csv(PROSPECTS, usecols=["player", "position", "rank"])
    pros["rank"] = pd.to_numeric(pros["rank"], errors="coerce")
    full_to_pos = dict(zip(pros["player"].map(_norm), pros["position"].str.upper()))
    surname_to_pos = {}
    # Prefer highest-ranked surname match when collision
    pros_sorted = pros.sort_values("rank")
    for _, r in pros_sorted.iterrows():
        s = _surname(r["player"])
        surname_to_pos.setdefault(s, str(r["position"]).upper())

    full_to_rank = dict(zip(pros["player"].map(_norm), pros["rank"]))
    surname_to_rank = {}
    for _, r in pros_sorted.iterrows():
        surname_to_rank.setdefault(_surname(r["player"]), r["rank"])

    rows = []
    total = 0; team_match = 0; exact = 0; pos_match = 0; in_top32 = 0
    within5 = 0; within3 = 0; within_any_nearby = 0
    for _, ind_row in ind.iterrows():
        slot = int(ind_row["pick"])
        if slot > 32: continue
        total += 1

        cp = cons.get(str(slot), {})
        cons_team = cp.get("team", "?")
        cons_player = cp.get("consensus_tier1") or cp.get("consensus_player") or "?"

        ind_team = str(ind_row["team"])
        ind_player = str(ind_row["player"])

        cp_pos = (full_to_pos.get(_norm(cons_player))
                  or surname_to_pos.get(_surname(cons_player), "?"))
        ip_pos = (full_to_pos.get(_norm(ind_player))
                  or surname_to_pos.get(_surname(ind_player), "?"))

        is_team_match = (cons_team == ind_team)
        is_player_match = _surname(cons_player) == _surname(ind_player)
        is_pos_match = (cp_pos == ip_pos) and cp_pos != "?"

        # Find ind_player's consensus rank
        ind_cons_rank = (full_to_rank.get(_norm(ind_player))
                         or surname_to_rank.get(_surname(ind_player)))
        if pd.notna(ind_cons_rank) and ind_cons_rank <= 32:
            in_top32 += 1
        # Distance vs consensus slot if that player has a known consensus rank
        dist = ""
        if pd.notna(ind_cons_rank):
            d = abs(int(ind_cons_rank) - slot)
            dist = str(d)
            if d <= 3: within3 += 1; within5 += 1
            elif d <= 5: within5 += 1

        flag = ("EXACT" if is_player_match else
                "POS_MATCH" if is_pos_match else
                "TEAM_ONLY" if is_team_match else
                "DIVERGES")

        team_match += int(is_team_match)
        exact += int(is_player_match)
        pos_match += int(is_pos_match)

        rows.append({
            "slot": slot,
            "team": ind_team,
            "our_pick": ind_player,
            "our_pos": ip_pos,
            "our_grade": round(float(ind_row.get("independent_grade", 0)), 2),
            "our_fit_score": round(float(ind_row.get("fit_score", 0)), 3),
            "probability": round(float(ind_row.get("probability", 0)), 3),
            "consensus_team": cons_team,
            "consensus_pick": cons_player,
            "consensus_pos": cp_pos,
            "pick_distance_from_consensus_rank": dist,
            "match_flag": flag,
            "team_match": is_team_match,
            "exact_player_match": is_player_match,
            "position_match": is_pos_match,
        })

    df = pd.DataFrame(rows)
    df.to_csv(OUT_R1, index=False)
    print(f"\n--- R1 picks vs consensus ({total} slots) ---")
    print(f"  EXACT player at slot:     {exact}/{total} ({100*exact/max(1,total):.1f}%)")
    print(f"  POSITION match at slot:   {pos_match}/{total} ({100*pos_match/max(1,total):.1f}%)")
    print(f"  Team-at-slot match:       {team_match}/{total} ({100*team_match/max(1,total):.1f}%)")
    print(f"  Our pick in consensus top-32: {in_top32}/{total} ({100*in_top32/max(1,total):.1f}%)")
    print(f"  Within 3 picks of consensus rank: {within3}/{total}")
    print(f"  Within 5 picks of consensus rank: {within5}/{total}")
    print(f"  Wrote: {OUT_R1}")


def export_big_board():
    """Per-prospect: our rank vs consensus rank + diff."""
    if not IND_BOARD.exists():
        print(f"Missing {IND_BOARD}. Run the MC first.")
        return

    ind = pd.read_csv(IND_BOARD)
    pros = pd.read_csv(PROSPECTS, usecols=["player", "position", "college", "rank"])
    pros = pros.rename(columns={"rank": "consensus_rank"})

    # Merge by exact player name
    merged = ind.merge(
        pros[["player", "consensus_rank"]], on="player", how="left")
    merged["consensus_rank"] = pd.to_numeric(
        merged["consensus_rank"], errors="coerce")
    merged["rank_diff"] = merged["final_rank"] - merged["consensus_rank"]
    # Flag: same tier bucket?
    def _tier(r):
        if pd.isna(r): return "unranked_consensus"
        if r <= 32: return "R1"
        if r <= 64: return "R2"
        if r <= 100: return "R3"
        if r <= 150: return "R4"
        return "Day3+"
    merged["our_tier"] = merged["final_rank"].apply(_tier)
    merged["consensus_tier"] = merged["consensus_rank"].apply(_tier)
    merged["same_tier"] = merged["our_tier"] == merged["consensus_tier"]

    # Highlight R1 players (consensus <= 32) whose rank differs by more than 5
    def _flag(row):
        cr = row["consensus_rank"]
        diff = row["rank_diff"]
        if pd.isna(cr):
            return "not_ranked_by_consensus"
        if pd.isna(diff):
            return ""
        d = abs(diff)
        if cr <= 32 and d > 5:
            return "R1_BIG_GAP"          # <- flag for display
        if cr <= 32 and d > 2:
            return "R1_minor_gap"
        if cr <= 100 and d > 15:
            return "TOP100_BIG_GAP"
        return "aligned"
    merged["flag"] = merged.apply(_flag, axis=1)

    out_cols = [
        "final_rank",
        "consensus_rank",
        "rank_diff",
        "flag",              # <- new highlight column
        "player", "position", "school",
        "our_tier", "consensus_tier", "same_tier",
        "independent_grade",
        "raw_model_pred",
        "reasoning_delta",
        "visit_count", "has_injury_flag", "ras_score", "age",
    ]
    available = [c for c in out_cols if c in merged.columns]
    merged[available].head(300).to_csv(OUT_BB, index=False)

    # Also log the R1_BIG_GAP rows for immediate attention
    big_gaps = merged[merged["flag"] == "R1_BIG_GAP"].sort_values("consensus_rank")
    if len(big_gaps):
        print(f"\n  R1 players with rank diff > 5 (big-board gaps to investigate):")
        for _, r in big_gaps.iterrows():
            print(f"    cons #{int(r['consensus_rank']):>3d} ({r['position']:<4s}) "
                  f"{r['player']:<22s}  our #{int(r['final_rank']):>3d}  "
                  f"diff {int(r['rank_diff']):+d}")

    # Summary metrics
    top_n = [20, 32, 64, 100]
    print(f"\n--- Big board vs consensus (top 300 prospects) ---")
    for n in top_n:
        our_top = set(merged.head(n)["player"].values)
        cons_top = set(
            merged[merged["consensus_rank"].notna() & (merged["consensus_rank"] <= n)]
            ["player"].values)
        overlap = our_top & cons_top
        print(f"  Top-{n} overlap with consensus: {len(overlap)}/{n} "
              f"({100*len(overlap)/n:.0f}%)")

    # Within-K rank diff for ranked-in-both
    both_ranked = merged[merged["consensus_rank"].notna()]
    for thr in [5, 10, 20]:
        within = (both_ranked["rank_diff"].abs() <= thr).sum()
        total = len(both_ranked)
        print(f"  Within ±{thr} ranks: {within}/{total} "
              f"({100*within/max(1,total):.0f}%)")

    print(f"  Wrote: {OUT_BB}")


def main():
    export_r1_picks()
    export_big_board()


if __name__ == "__main__":
    main()
