"""Realign the big board to be (nearly) identical to Kiper's top-100.

Simple, deterministic rule:
  - Kiper top-100: final_rank = kiper_rank (1..100)
  - Everyone else: keep prior relative order, bumped to rank 101+

This is what the user asked for — the board should "look like the ESPN
link" — so we don't try to be clever about non-Kiper prospects.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
BOARD_CSV = ROOT / "data/processed/predictions_2026_independent.csv"
KIPER_JSON = ROOT / "data/features/kiper_big_board_2026.json"


def _norm(s: str) -> str:
    """Normalize aggressively: lowercase, strip suffixes, strip punct/spaces."""
    if not s:
        return ""
    n = re.sub(r"\s+(jr|sr|ii|iii|iv|v)\.?$", "", s.strip(), flags=re.IGNORECASE)
    return "".join(ch for ch in n.lower() if ch.isalnum())


def main() -> None:
    board = pd.read_csv(BOARD_CSV)

    kiper = json.loads(KIPER_JSON.read_text(encoding="utf-8"))
    kiper_map: dict[str, int] = {}
    for entry in kiper.get("top100", []):
        kiper_map[_norm(entry["player"])] = int(entry["rank"])

    # For each board row, compute target rank
    def _target(row) -> float:
        k = _norm(str(row["player"]))
        kr = kiper_map.get(k)
        if kr is not None:
            return float(kr)
        # Non-Kiper: push past rank 100, preserving prior relative order.
        prior = float(row.get("final_rank") or 99999)
        return 1000.0 + prior

    board["_target"] = board.apply(_target, axis=1)
    board = board.sort_values(["_target", "final_rank"]).reset_index(drop=True)
    board["final_rank"] = range(1, len(board) + 1)

    def _tier(r: int) -> str:
        if r <= 32: return "R1"
        if r <= 64: return "R2"
        if r <= 100: return "R3"
        if r <= 257: return "R4-R7"
        return "UDFA"

    board["independent_tier"] = board["final_rank"].apply(_tier)

    orig_cols = [c for c in pd.read_csv(BOARD_CSV, nrows=1).columns if c in board.columns]
    board[orig_cols].to_csv(BOARD_CSV, index=False)

    n_kiper = sum(1 for p in board["player"] if _norm(str(p)) in kiper_map)
    print(f"[realign] reranked {len(board)} prospects "
          f"({n_kiper}/{len(kiper_map)} Kiper top-100 matched)")
    # Report unmatched Kiper entries so name drift is visible.
    board_keys = {_norm(str(p)) for p in board["player"]}
    unmatched = [e for e in kiper.get("top100", []) if _norm(e["player"]) not in board_keys]
    if unmatched:
        print(f"[realign] {len(unmatched)} Kiper entries have no matching board row:")
        for e in unmatched:
            print(f"  Kiper #{e['rank']}: {e['player']} ({e['pos']}, {e['college']})")


if __name__ == "__main__":
    main()
