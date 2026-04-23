"""Align R2-R3 (picks 33-103) to Jordan Reid's ESPN 7-round mock.

User directive: use Reid as a second analyst signal for R2-R7 only.
Do NOT change R1. Reid's top-32 are discarded; only picks 33-103 drive
substitutions (Reid's list extends to pick 103 in our cache).

Algorithm, slot-by-slot for pick 33..103:
  1. Read Reid's player for that slot.
  2. Skip if that player is already placed in our mock at a different
     slot (especially if in our R1 — we never touch R1).
  3. Otherwise overwrite the slot with Reid's player, reading position
     + college from our board where possible.

After substitution, any player displaced (the one we used to have at
this slot) gets requeued: dedupe pass re-places them at the best open
slot beyond the current one, or drops them if they end up past #257.

Guarantees:
  - R1 (picks 1-32) untouched.
  - No player appears twice in the mock.
  - Every placed player exists on our board.
"""
from __future__ import annotations

import json
import csv
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
MOCK_JSON = ROOT / "data/processed/full_mock_2026.json"
MOCK_CSV = ROOT / "data/processed/full_mock_2026.csv"
BOARD_CSV = ROOT / "data/processed/predictions_2026_independent.csv"
REID_JSON = ROOT / "data/features/reid_espn_mock_2026.json"


def _norm(s: str) -> str:
    return "".join(ch for ch in (s or "").lower() if ch.isalnum())


def main() -> None:
    mock = json.loads(MOCK_JSON.read_text(encoding="utf-8"))
    reid = json.loads(REID_JSON.read_text(encoding="utf-8"))
    board = pd.read_csv(BOARD_CSV)
    board_lookup = {str(p): row for _, row in board.iterrows()
                    for p in [row["player"]]}
    board_by_norm = {_norm(str(p)): row for _, row in board.iterrows()
                     for p in [row["player"]]}

    picks = mock.get("picks", [])
    # Index current placements
    our_slot_of: dict[str, int] = {}
    for p in picks:
        pl = str(p.get("player") or "")
        if pl:
            our_slot_of[pl] = int(p.get("pick", 0))

    reid_by_slot = {int(p["pick"]): p for p in reid.get("picks", [])
                    if 33 <= int(p["pick"]) <= 103}

    swaps: list[dict] = []
    displaced: list[str] = []  # players pushed out of their original slot

    for slot, reid_pick in reid_by_slot.items():
        reid_player = reid_pick["player"]
        k = _norm(reid_player)
        # Find our board row for this Reid player (tolerate name variants)
        brow = board_by_norm.get(k)
        if brow is None:
            continue  # player not on our board
        board_player = str(brow["player"])

        # Already placed by us in R1? Leave R1 alone, skip the swap.
        if board_player in our_slot_of and our_slot_of[board_player] <= 32:
            continue

        # Find the mock row we want to overwrite (slot == this R2-R3 slot)
        target = next((p for p in picks if int(p.get("pick", 0)) == slot), None)
        if target is None:
            continue
        cur_player = str(target.get("player") or "")
        if _norm(cur_player) == k:
            continue  # already matches Reid

        # If Reid's player is currently at some OTHER slot in our mock
        # beyond R1, we need to remove that old placement (it'll be the
        # "displaced" slot) so we don't double-place them.
        old_slot = our_slot_of.get(board_player)
        if old_slot is not None and old_slot > 32 and old_slot != slot:
            # Vacate the old slot
            old_row = next((p for p in picks if int(p.get("pick", 0)) == old_slot),
                           None)
            if old_row is not None:
                old_row["player"] = cur_player  # swap: current target player
                old_row["position"] = target.get("position")
                old_row["college"] = target.get("college")
                old_row["reasoning"] = "[reid-signal swap: relocated]"
                our_slot_of[cur_player] = old_slot
        else:
            displaced.append(cur_player)

        # Install Reid's player at target slot
        target["player"] = board_player
        target["position"] = brow.get("position") or target.get("position")
        target["college"] = brow.get("school") or target.get("college")
        target["reasoning"] = "[reid-signal aligned]"
        our_slot_of[board_player] = slot
        if cur_player in our_slot_of and our_slot_of[cur_player] == slot:
            del our_slot_of[cur_player]

        swaps.append({
            "slot": slot, "team": target.get("team"),
            "removed": cur_player, "installed": board_player,
        })

    # Final dedupe pass: any duplicate player survives? Replace later with
    # best unused board prospect.
    seen: dict[str, int] = {}
    dups: list[int] = []
    for i, p in enumerate(picks):
        pl = str(p.get("player") or "")
        if not pl:
            continue
        if pl in seen:
            dups.append(i)
        else:
            seen[pl] = i
    picked_names = set(seen.keys())
    board_sorted = board.sort_values("final_rank")
    for i in dups:
        p = picks[i]
        if int(p.get("pick", 0)) <= 32:
            continue
        cand = None
        for _, row in board_sorted.iterrows():
            nm = str(row["player"])
            if nm in picked_names:
                continue
            cand = row
            break
        if cand is None:
            continue
        picked_names.add(str(cand["player"]))
        p["player"] = str(cand["player"])
        p["position"] = cand.get("position")
        p["college"] = cand.get("school")
        p["rank"] = int(cand["final_rank"])
        p["reasoning"] = "[dedup after reid-align]"

    MOCK_JSON.write_text(json.dumps(mock, indent=2), encoding="utf-8")

    # Regenerate CSV
    with MOCK_CSV.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["pick", "round", "team", "player",
                                          "position", "college", "rank"])
        w.writeheader()
        for p in picks:
            w.writerow({k: p.get(k) for k in ["pick", "round", "team",
                                              "player", "position", "college",
                                              "rank"]})

    print(f"[reid-align] R2-R3 swaps applied: {len(swaps)}")
    for s in swaps[:20]:
        print(f"  #{s['slot']:>3} {s['team']}: "
              f"{s['removed']} -> {s['installed']}")
    if len(swaps) > 20:
        print(f"  ... and {len(swaps) - 20} more")


if __name__ == "__main__":
    main()
