"""Accuracy sanity check: independent model vs current mock consensus.

IMPORTANT: this is ONLY a comparison for evaluation. The independent model
does not consume these consensus picks in its scoring — see
tests/test_independence.py. This script reads the consensus file (which
is in the banned_files list for the independent engine) only to measure
post-hoc distance.

Reports:
  - modal team match rate (R1)
  - exact player match rate at same slot (fuzzy surname matching)
  - within-3 / within-5 pick distance for players present in both boards
  - per-pick side-by-side table highlighting disagreements

Run:
  python -m src.models.evaluate.compare_to_consensus
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
IND_PICKS = ROOT / "data/processed/predictions_2026_independent_picks.csv"
CONSENSUS_JSON = ROOT / "data/features/analyst_consensus_2026.json"
OUT_CSV = ROOT / "data/processed/compare_independent_vs_consensus.csv"


def _norm(name: str) -> str:
    if not isinstance(name, str):
        return ""
    return (name.strip().lower()
            .replace(".", "").replace("'", "")
            .replace("-", " ").replace("  ", " "))


def _surname(name: str) -> str:
    n = _norm(name)
    return n.rsplit(" ", 1)[-1] if " " in n else n


def main():
    if not IND_PICKS.exists():
        print(f"Run the independent MC first — missing {IND_PICKS}")
        return 1
    if not CONSENSUS_JSON.exists():
        print(f"Consensus file missing: {CONSENSUS_JSON}")
        return 1

    ind = pd.read_csv(IND_PICKS)
    cons = json.loads(CONSENSUS_JSON.read_text(encoding="utf-8"))["per_pick"]

    # Build lookup: surname -> (ind_slot, ind_full_name)
    ind_by_surname = {_surname(r.player): (int(r.pick), r.player, r.team)
                      for _, r in ind.iterrows()}
    ind_by_slot = {int(r.pick): (r.player, r.team) for _, r in ind.iterrows()}

    # Look up consensus and independent POSITIONS via prospects CSV surname
    # index. Prefer the TOP-RANKED player for any surname collision so
    # "Reese" resolves to Arvell Reese (EDGE/LB) not a lower-ranked RB.
    pros_path = ROOT / "data/processed/prospects_2026_enriched.csv"
    surname_to_pos: dict[str, str] = {}
    full_to_pos: dict[str, str] = {}
    if pros_path.exists():
        pdf = pd.read_csv(pros_path)
        # Sort by draft rank so earlier picks win surname collisions
        rank_col = "rank" if "rank" in pdf.columns else "final_rank"
        if rank_col in pdf.columns:
            pdf = pdf.sort_values(rank_col).reset_index(drop=True)
        for _, row in pdf.iterrows():
            full = _norm(row["player"])
            pos = str(row["position"]).upper()
            full_to_pos[full] = pos
            if " " in full:
                surname = full.rsplit(" ", 1)[-1]
                # Only set the first (top-ranked) occurrence for this surname
                surname_to_pos.setdefault(surname, pos)

    rows = []
    team_matches = 0
    player_matches = 0  # exact player at exact slot
    position_matches = 0  # same position at same slot
    within_3_r1 = 0
    within_5_r1 = 0
    hits_r1 = 0  # consensus player also in independent top 32
    total = 0

    for slot_s, p in sorted(cons.items(), key=lambda kv: int(kv[0])):
        slot = int(slot_s)
        if slot > 32:
            break
        total += 1
        cons_team = p.get("team", "")
        cons_player = p.get("consensus_tier1") or p.get("consensus_player")
        if not cons_player:
            continue

        ind_player, ind_team = ind_by_slot.get(slot, ("?", "?"))
        ind_slot_for_cons, _, _ = ind_by_surname.get(_surname(cons_player), (None, None, None))

        is_team_match = (cons_team == ind_team)
        is_player_match = _surname(cons_player) == _surname(ind_player)
        # Position-match check — same position at the same slot even if the
        # specific player differs (valid analyst variance, per user).
        # Prefer full-name match; fall back to surname lookup (top-ranked
        # wins collisions).
        cons_pos = (full_to_pos.get(_norm(cons_player))
                    or surname_to_pos.get(_surname(cons_player), ""))
        ind_pos = (full_to_pos.get(_norm(ind_player))
                   or surname_to_pos.get(_surname(ind_player), ""))
        is_pos_match = bool(cons_pos) and (cons_pos == ind_pos)
        team_matches += int(is_team_match)
        player_matches += int(is_player_match)
        position_matches += int(is_pos_match)
        if ind_slot_for_cons is not None:
            hits_r1 += 1
            diff = abs(ind_slot_for_cons - slot)
            within_3_r1 += int(diff <= 3)
            within_5_r1 += int(diff <= 5)
            diff_str = str(diff)
        else:
            diff_str = "NOT_IN_R1"

        rows.append({
            "slot": slot,
            "team": cons_team,
            "consensus_player": cons_player,
            "consensus_pos": cons_pos,
            "independent_player": ind_player,
            "independent_pos": ind_pos,
            "independent_team": ind_team,
            "team_match": is_team_match,
            "player_match_same_slot": is_player_match,
            "position_match_same_slot": is_pos_match,
            "ind_slot_for_consensus_player": ind_slot_for_cons,
            "pick_distance": diff_str,
        })

    df = pd.DataFrame(rows)
    df.to_csv(OUT_CSV, index=False)

    def _pct(n): return f"{100.0 * n / max(1, total):.1f}%"

    print("=" * 72)
    print("INDEPENDENT MODEL vs CURRENT MOCK CONSENSUS")
    print("=" * 72)
    print(f"R1 picks compared:         {total}")
    print(f"Team match at slot:        {team_matches}/{total} ({_pct(team_matches)})")
    print(f"POSITION match at slot:    {position_matches}/{total} ({_pct(position_matches)})  <- analyst-variance-tolerant")
    print(f"Exact player at same slot: {player_matches}/{total} ({_pct(player_matches)})")
    print(f"Consensus player in ind top-32: {hits_r1}/{total} ({_pct(hits_r1)})")
    print(f"  within 3 picks: {within_3_r1}/{total} ({_pct(within_3_r1)})")
    print(f"  within 5 picks: {within_5_r1}/{total} ({_pct(within_5_r1)})")
    print()
    print("Per-pick table (slot / consensus / independent / distance):")
    print("-" * 72)
    for _, r in df.iterrows():
        # OK = exact player; POS = same position, different player; ~~ = team-at-slot only; XX = all-wrong
        if r.player_match_same_slot:
            flag = "OK "
        elif r.position_match_same_slot:
            flag = "POS"
        elif r.team_match:
            flag = "~~ "
        else:
            flag = "XX "
        print(f"  {flag} #{int(r.slot):>2} {r.team:<4} "
              f"cons={r.consensus_player:<18} ({r.consensus_pos:<4}) "
              f"ind={r.independent_player:<22} ({r.independent_pos:<4}) "
              f"dist={r.pick_distance}")
    print()
    print(f"Wrote {OUT_CSV}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
