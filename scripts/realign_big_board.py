"""Realign the big board.

Cascade rule per user directive:
  1. Kiper top-150 (from ESPN big board): final_rank = kiper_rank
  2. Not in Kiper, but has `rank` in prospects_2026_enriched.csv: final_rank
     = 150 + position_in_that_ranked_list (so ranks 151, 152, ... based on
     consensus order)
  3. Everyone else: preserve prior relative order, bumped after the
     cascade.

This keeps the top-150 identical to Kiper's ESPN big board and fills in
the long tail with the best secondary consensus we have.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
BOARD_CSV = ROOT / "data/processed/predictions_2026_independent.csv"
PROSPECTS_CSV = ROOT / "data/processed/prospects_2026_enriched.csv"
KIPER_JSON = ROOT / "data/features/kiper_big_board_2026.json"


def _norm(s: str) -> str:
    """Case- and suffix-insensitive name key."""
    if not s:
        return ""
    n = re.sub(r"\s+(jr|sr|ii|iii|iv|v)\.?$", "", s.strip(), flags=re.IGNORECASE)
    # "Nick" vs "Nicholas" — normalize common first-name aliases
    n = re.sub(r"^nicholas\s+", "nick ", n, flags=re.IGNORECASE)
    return "".join(ch for ch in n.lower() if ch.isalnum())


def main() -> None:
    board = pd.read_csv(BOARD_CSV)
    kiper = json.loads(KIPER_JSON.read_text(encoding="utf-8"))
    pros = pd.read_csv(PROSPECTS_CSV, usecols=["player", "rank"])
    pros["rank"] = pd.to_numeric(pros["rank"], errors="coerce")

    # Inject placeholder rows for any Kiper entries not in our board so the
    # final ranks line up exactly with Kiper's numbers (no off-by-N from
    # missing prospects like Ted Hurst / Georgia State WR).
    board_keys_before = {_norm(str(p)) for p in board["player"]}
    added_rows: list[dict] = []
    for e in kiper.get("top100", []):
        if _norm(e["player"]) in board_keys_before:
            continue
        row = {c: None for c in board.columns}
        row["player"] = e["player"]
        row["position"] = e.get("pos")
        if "school" in row:
            row["school"] = e.get("college")
        row["independent_grade"] = float(e["rank"])
        row["final_rank"] = 10000 + int(e["rank"])
        if "independent_tier" in row:
            row["independent_tier"] = "R4-R7"
        if "confidence" in row:
            row["confidence"] = "LOW"
        added_rows.append(row)
    if added_rows:
        board = pd.concat([board, pd.DataFrame(added_rows)], ignore_index=True)
        print(f"[realign] added {len(added_rows)} placeholder rows for "
              f"unmatched Kiper entries")

    # 1. Kiper map
    kiper_map: dict[str, int] = {}
    for entry in kiper.get("top100", []):
        kiper_map[_norm(entry["player"])] = int(entry["rank"])
    kiper_size = max(kiper_map.values()) if kiper_map else 0

    # 2. Secondary consensus: prospects CSV rank, re-indexed from kiper_size+1
    # Only players NOT in kiper_map, sorted by their `rank`.
    secondary_pairs = [
        (_norm(p), float(r))
        for p, r in zip(pros["player"], pros["rank"])
        if pd.notna(r) and _norm(p) not in kiper_map
    ]
    secondary_pairs.sort(key=lambda x: x[1])  # ascending by consensus rank
    secondary_map: dict[str, int] = {}
    for i, (k, _) in enumerate(secondary_pairs):
        secondary_map[k] = kiper_size + 1 + i  # 151, 152, ...

    def _target(row) -> float:
        k = _norm(str(row["player"]))
        if k in kiper_map:
            return float(kiper_map[k])
        if k in secondary_map:
            return float(secondary_map[k])
        return 100000.0 + float(row.get("final_rank") or 99999)

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

    n_k = sum(1 for p in board["player"] if _norm(str(p)) in kiper_map)
    n_s = sum(1 for p in board["player"]
              if _norm(str(p)) not in kiper_map and _norm(str(p)) in secondary_map)
    print(f"[realign] {len(board)} prospects reranked "
          f"({n_k}/{kiper_size} Kiper matched, "
          f"{n_s} filled by prospects_enriched consensus, "
          f"{len(board) - n_k - n_s} unanchored)")
    # Surface any Kiper entries we couldn't match (name drift warnings).
    board_keys = {_norm(str(p)) for p in board["player"]}
    unmatched = [e for e in kiper.get("top100", [])
                 if _norm(e["player"]) not in board_keys]
    if unmatched:
        print(f"[realign] {len(unmatched)} unmatched Kiper entries:")
        for e in unmatched:
            print(f"  #{e['rank']}: {e['player']} ({e['pos']}, {e['college']})")


if __name__ == "__main__":
    main()
