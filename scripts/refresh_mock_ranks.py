"""Re-sync `rank` field on every pick in both full mocks to the current
Kiper-anchored board rank. Without this, the RCH / VAL flags on the
Full Mock page lie — they compare slot to a stored rank that hasn't
been updated since the initial build_full_mock.py run.

Run after any realign_big_board / realign_r1_picks / realign_r2 pass.
"""
from __future__ import annotations

import json
import csv
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
BOARD = ROOT / "data/processed/predictions_2026_independent.csv"

MOCKS = [
    (ROOT / "data/processed/full_mock_2026.json",
     ROOT / "data/processed/full_mock_2026.csv"),
    (ROOT / "data/processed/full_mock_2026_with_trades.json",
     ROOT / "data/processed/full_mock_2026_with_trades.csv"),
]


def main() -> None:
    board = pd.read_csv(BOARD)
    rank_of: dict[str, int] = {
        str(p): int(r) for p, r in zip(board["player"], board["final_rank"])
    }

    for mock_json, mock_csv in MOCKS:
        if not mock_json.exists():
            continue
        mock = json.loads(mock_json.read_text(encoding="utf-8"))
        n_fixed = 0
        for pick in mock.get("picks", []):
            player = str(pick.get("player") or "")
            new_rank = rank_of.get(player)
            if new_rank is None:
                continue
            if pick.get("rank") != new_rank:
                pick["rank"] = new_rank
                n_fixed += 1
            # Also fix alternates' ranks so the expanded detail is honest
            for alt in (pick.get("alternates") or []):
                ap = str(alt.get("player") or "")
                ar = rank_of.get(ap)
                if ar is not None and alt.get("rank") != ar:
                    alt["rank"] = ar
        mock_json.write_text(json.dumps(mock, indent=2), encoding="utf-8")

        # Regenerate CSV with the fresh ranks
        if mock_csv.exists() or True:
            fields = ["pick", "round", "team", "player", "position",
                      "college", "rank"]
            has_trades = any("_trade" in p for p in mock.get("picks", []))
            if has_trades:
                fields += ["trade_from", "trade_to"]
            with mock_csv.open("w", newline="", encoding="utf-8") as f:
                w = csv.DictWriter(f, fieldnames=fields)
                w.writeheader()
                for p in mock.get("picks", []):
                    row = {k: p.get(k) for k in
                           ["pick", "round", "team", "player", "position",
                            "college", "rank"]}
                    if has_trades:
                        t = p.get("_trade") or {}
                        row["trade_from"] = t.get("from", "")
                        row["trade_to"] = t.get("to", "")
                    w.writerow(row)

        print(f"[refresh_ranks] {mock_json.name}: {n_fixed} picks updated")


if __name__ == "__main__":
    main()
