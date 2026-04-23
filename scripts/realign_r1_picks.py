"""Realign R1 picks to analyst consensus.

Reads data/features/analyst_consensus_2026.json (20 analyst mocks) and
ensures every pick in predictions_2026_independent_picks.csv has at
least ONE analyst with that player inside pick +/- window. If not, swap
with the best-ranked Kiper/consensus-anchored player whose analyst
appearances cover this slot and who isn't already placed.

Also rewrites full_mock_2026.json's R1 picks for display consistency.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
PICKS_CSV = ROOT / "data/processed/predictions_2026_independent_picks.csv"
BOARD_CSV = ROOT / "data/processed/predictions_2026_independent.csv"
MOCK_JSON = ROOT / "data/processed/full_mock_2026.json"
ANALYST_JSON = ROOT / "data/features/analyst_consensus_2026.json"
KIPER_JSON = ROOT / "data/features/kiper_big_board_2026.json"

SLOT_WINDOW = 8


def _norm(s: str) -> str:
    return "".join(ch for ch in (s or "").lower() if ch.isalnum())


def _key_variants(full: str) -> list[str]:
    f = full
    no_suffix = re.sub(r"\s+(Jr\.?|Sr\.?|II|III|IV)$", "", f, flags=re.IGNORECASE).strip()
    tokens = no_suffix.split()
    last = tokens[-1] if tokens else f
    return [f, no_suffix, last, last + " Jr.", last + " Jr"]


def _load_analyst_slots() -> dict[str, list[int]]:
    """Return {player_key_variant -> [slots where any analyst placed them]}."""
    d = json.loads(ANALYST_JSON.read_text(encoding="utf-8"))
    out: dict[str, list[int]] = {}
    for slot_s, rec in (d.get("per_pick") or {}).items():
        slot = int(slot_s)
        if slot > 32:
            continue
        for player in (rec.get("picks_all") or {}).keys():
            out.setdefault(player, []).append(slot)
    return out


def _slots_for(full_name: str, table: dict[str, list[int]]) -> list[int]:
    for k in _key_variants(full_name):
        if k in table:
            return table[k]
    return []


def main() -> None:
    picks = pd.read_csv(PICKS_CSV)
    board = pd.read_csv(BOARD_CSV)
    analyst_slots = _load_analyst_slots()

    # Map player -> final_rank on the realigned board
    rank_of = {_norm(p): int(r) for p, r in zip(board["player"], board["final_rank"])}
    board_by_rank = board.set_index("final_rank")

    kiper = json.loads(KIPER_JSON.read_text(encoding="utf-8"))
    kiper_set = {_norm(e["player"]) for e in kiper.get("top100", [])}

    def _needs_swap(slot: int, player: str) -> bool:
        slots = _slots_for(player, analyst_slots)
        if not slots:
            return True
        return not any(abs(s - slot) <= SLOT_WINDOW for s in slots)

    # Build candidate pool: Kiper top-45 players not already picked
    picked = {_norm(p) for p in picks[picks["round"] == 1]["player"]}

    def _eligible_for_slot(slot: int) -> list[dict]:
        """Players whose analyst coverage contains slot +/- window AND whose
        board rank is within a realistic band of the slot. A rank-4 player
        doesn't fall to pick 17 in any universe."""
        RANK_BAND = 12  # board rank must be within this of slot
        cands: list[dict] = []
        for _, row in board.head(80).iterrows():
            if _norm(row["player"]) in picked:
                continue
            fr = int(row["final_rank"])
            if abs(fr - slot) > RANK_BAND:
                continue
            slots = _slots_for(row["player"], analyst_slots)
            if not slots:
                continue
            if any(abs(s - slot) <= SLOT_WINDOW for s in slots):
                cands.append({
                    "player": row["player"],
                    "position": row["position"],
                    "school": row["school"],
                    "final_rank": fr,
                    "in_kiper": _norm(row["player"]) in kiper_set,
                })
        # Prefer candidates whose rank is >= slot (falling value picks) and
        # closer to slot; penalize reaches (rank > slot is OK, rank < slot
        # is a "reach" which shouldn't happen if we picked right earlier).
        cands.sort(key=lambda r: (abs(r["final_rank"] - slot), r["final_rank"]))
        return cands

    swaps: list[dict] = []
    rows = picks.to_dict(orient="records")
    for i, row in enumerate(rows):
        if int(row["round"]) != 1:
            continue
        slot = int(row["pick"])
        player = str(row["player"])
        if not _needs_swap(slot, player):
            continue
        # Remove the bad player from picked-set, find sub
        picked.discard(_norm(player))
        cands = _eligible_for_slot(slot)
        if not cands:
            continue
        sub = cands[0]
        rows[i]["player"] = sub["player"]
        rows[i]["position"] = sub["position"]
        rows[i]["school"] = sub["school"]
        rows[i]["independent_grade"] = float(
            board_by_rank.loc[sub["final_rank"], "independent_grade"])
        picked.add(_norm(sub["player"]))
        swaps.append({
            "slot": slot, "team": row["team"],
            "removed": player, "installed": sub["player"],
            "sub_final_rank": sub["final_rank"],
        })

    # ---- Second pass: guarantee Kiper top-15 all appear in R1 ----
    # Their market P50 + Kiper rank both put them in R1; if the sim missed
    # one, substitute the lowest-graded R1 player whose slot is within
    # SLOT_WINDOW of the missing player's analyst coverage.
    picked = {_norm(str(r["player"])) for r in rows if int(r["round"]) == 1}
    kiper_top15 = [e for e in kiper.get("top100", []) if int(e["rank"]) <= 15]
    forced: list[dict] = []
    for entry in kiper_top15:
        if _norm(entry["player"]) in picked:
            continue
        # Find the player's actual board row (their name on our board may
        # differ slightly, e.g. "Rueben Bain" vs Kiper's "Rueben Bain Jr.")
        mk = _norm(entry["player"])
        board_row = board[board["player"].map(lambda p: _norm(str(p))) == mk]
        if board_row.empty:
            continue
        brow = board_row.iloc[0]
        b_player = brow["player"]
        b_slots = _slots_for(b_player, analyst_slots) or [int(entry["rank"])]
        # Find the R1 row whose slot is closest to any analyst slot for this
        # player, and whose current occupant has the weakest board grade.
        r1_rows = [(i, r) for i, r in enumerate(rows) if int(r["round"]) == 1]
        # Only allow swap if slot is within SLOT_WINDOW of an analyst slot
        legal = [(i, r) for i, r in r1_rows
                 if any(abs(s - int(r["pick"])) <= SLOT_WINDOW for s in b_slots)
                 and _norm(str(r["player"])) in rank_of]
        if not legal:
            continue
        # Prefer displacing the player with the highest (worst) board rank
        legal.sort(key=lambda ir: -rank_of.get(_norm(str(ir[1]["player"])), 0))
        i, victim_row = legal[0]
        removed = victim_row["player"]
        rows[i]["player"] = b_player
        rows[i]["position"] = brow["position"]
        rows[i]["school"] = brow["school"]
        rows[i]["independent_grade"] = float(brow["independent_grade"])
        picked.discard(_norm(str(removed)))
        picked.add(_norm(str(b_player)))
        forced.append({"slot": int(victim_row["pick"]),
                       "team": victim_row["team"],
                       "removed": removed, "installed": b_player,
                       "kiper_rank": int(entry["rank"])})

    pd.DataFrame(rows).to_csv(PICKS_CSV, index=False)
    if forced:
        print(f"[realign_r1] forced {len(forced)} Kiper top-15 inclusions:")
        for s in forced:
            print(f"  #{s['slot']:>2} {s['team']}: "
                  f"{s['removed']} -> {s['installed']} "
                  f"(Kiper #{s['kiper_rank']})")

    # Update full_mock R1 picks to match
    if MOCK_JSON.exists():
        mock = json.loads(MOCK_JSON.read_text(encoding="utf-8"))
        r1_by_slot = {int(r["pick"]): r for r in rows if int(r["round"]) == 1}
        for p in mock.get("picks", []):
            slot = int(p.get("pick", 0))
            if slot in r1_by_slot:
                src = r1_by_slot[slot]
                p["player"] = src["player"]
                p["position"] = src["position"]
                p["college"] = src.get("school", p.get("college"))
                # Leave reasoning/alternates alone; flag stale
                p["reasoning"] = (
                    "[realigned to analyst consensus] " + (p.get("reasoning") or "")[:300]
                )
        MOCK_JSON.write_text(json.dumps(mock, indent=2), encoding="utf-8")

    print(f"[realign_r1] swapped {len(swaps)} R1 picks:")
    for s in swaps:
        print(f"  #{s['slot']:>2} {s['team']}: "
              f"{s['removed']} -> {s['installed']} "
              f"(board rank {s['sub_final_rank']})")


if __name__ == "__main__":
    main()
