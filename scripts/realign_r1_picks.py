"""Realign R1 picks so every pick is within MAX_DELTA of analyst consensus.

For each R1 slot:
  1. Build the eligible pool: any player at least one analyst placed
     within slot +/- MAX_DELTA slots.
  2. Weight each candidate by (a) summed analyst-appearances near this
     slot (closer = higher weight) and (b) board rank (earlier = better).
  3. Greedy-assign slot by slot, preserving team (team column in picks
     CSV is not changed; only player/position/school are overwritten).

If a slot has no eligible pool (unlikely inside R1), leave the original
occupant. The script is idempotent and re-runnable.

Also rewrites full_mock_2026.json R1 rows so the Full Mock page matches.
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

MAX_DELTA = 3  # every pick must be within this many slots of an analyst slot


def _norm(s: str) -> str:
    return "".join(ch for ch in (s or "").lower() if ch.isalnum())


def _key_variants(full: str) -> list[str]:
    """Possible keys under which analyst_consensus indexes this player."""
    f = full
    no_suf = re.sub(r"\s+(Jr\.?|Sr\.?|II|III|IV)$", "", f, flags=re.IGNORECASE).strip()
    tokens = no_suf.split()
    last = tokens[-1] if tokens else f
    return [f, no_suf, last, last + " Jr.", last + " Jr"]


def _load_analyst_hits() -> dict[str, dict[int, int]]:
    """Return {analyst_key -> {slot -> appearance_count}}."""
    d = json.loads(ANALYST_JSON.read_text(encoding="utf-8"))
    out: dict[str, dict[int, int]] = {}
    for slot_s, rec in (d.get("per_pick") or {}).items():
        slot = int(slot_s)
        if slot > 32:
            continue
        for player, n in (rec.get("picks_all") or {}).items():
            out.setdefault(player, {})[slot] = int(n)
    return out


def _hits_for(player_name: str, table: dict[str, dict[int, int]]) -> dict[int, int]:
    """Merge all matching analyst-key variants (analysts index the same
    player under multiple keys, e.g. "Delane" AND "Mansoor Delane")."""
    merged: dict[int, int] = {}
    for k in _key_variants(player_name):
        for slot, cnt in (table.get(k) or {}).items():
            merged[slot] = max(merged.get(slot, 0), int(cnt))
    return merged


def main() -> None:
    picks = pd.read_csv(PICKS_CSV)
    board = pd.read_csv(BOARD_CSV).sort_values("final_rank").reset_index(drop=True)
    board_rank: dict[str, int] = {_norm(str(p)): int(r)
                                   for p, r in zip(board["player"], board["final_rank"])}
    analyst_hits = _load_analyst_hits()

    # Build player pool with pre-computed analyst slot sets (for our own
    # player names as they appear on the board).
    player_hits: dict[str, dict[int, int]] = {}
    for p in board["player"]:
        hits = _hits_for(str(p), analyst_hits)
        if hits:
            player_hits[str(p)] = hits

    # Kiper top-15 must land in R1. Their market + analyst data reliably
    # pin them to R1 even if analyst_hits keys are spotty.
    kiper = json.loads(KIPER_JSON.read_text(encoding="utf-8"))
    kiper_top15: list[str] = []
    for e in kiper.get("top100", []):
        if int(e["rank"]) > 15:
            break
        # Find the board-side name matching this Kiper entry.
        mk = _norm(e["player"])
        match = next((str(p) for p in board["player"] if _norm(str(p)) == mk), None)
        if match:
            kiper_top15.append(match)

    def _score(player: str, slot: int) -> float:
        """Higher is better. Weight = analyst appearances near slot
        (decaying by distance) + Kiper-top-15 bonus + board-rank bonus."""
        hits = player_hits.get(player, {})
        # Only eligible if at least one analyst slot is within MAX_DELTA
        eligible_hits = {s: c for s, c in hits.items() if abs(s - slot) <= MAX_DELTA}
        if not eligible_hits:
            # Kiper top-15 fallback: eligible for any R1 slot if their Kiper
            # rank is within 12 of the slot (so Styles Kiper #4 can fit 1-16).
            if player in kiper_top15:
                kr = next((int(e["rank"]) for e in kiper["top100"]
                           if _norm(e["player"]) == _norm(player)), None)
                if kr is not None and abs(kr - slot) <= 12:
                    return 0.5  # soft-eligible
            return -1.0
        # Weighted analyst appearance score
        total = 0.0
        for s, c in eligible_hits.items():
            total += c * (1.0 / (1.0 + abs(s - slot)))
        # Small bonus for better board rank (earlier rank = higher score)
        rank = board_rank.get(_norm(player), 300)
        total += max(0.0, 100 - rank) * 0.02
        # Kiper top-15 bonus
        if player in kiper_top15:
            total += 2.5
        return total

    # Hard-pin top 5 per user directive (2026-04-23):
    # "top 5 should be mendoza, bailey, reese, love, then either downs or
    # styles at 5". Pick Styles at 5 (Kiper #4 > Downs #6; market gives
    # Styles P50=5 exactly) unless a name doesn't match the board.
    TOP5_PINS = ["Fernando Mendoza", "David Bailey", "Arvell Reese",
                 "Jeremiyah Love", "Sonny Styles"]
    pinned: dict[int, str] = {}
    for slot, name in enumerate(TOP5_PINS, start=1):
        # Tolerate small name variation between our board and the pin.
        match = next((str(p) for p in board["player"] if _norm(str(p)) == _norm(name)),
                     None)
        if match:
            pinned[slot] = match

    r1_rows = picks[picks["round"] == 1].sort_values("pick")
    assignments: dict[int, str] = {}  # slot -> chosen player
    used: set[str] = set()
    # Apply pins first so the greedy pass respects them.
    for slot, player in pinned.items():
        assignments[slot] = player
        used.add(player)

    # Greedy: iterate slots 1..32 in order. Could do Hungarian but greedy
    # from best-covered players downward is simpler and produces clean
    # R1 orderings because early slots have richer analyst coverage.
    for _, row in r1_rows.iterrows():
        slot = int(row["pick"])
        if slot in pinned:
            continue
        candidates: list[tuple[float, str]] = []
        for p in board["player"].head(60):
            pn = str(p)
            if pn in used:
                continue
            s = _score(pn, slot)
            if s <= 0:
                continue
            candidates.append((s, pn))
        if not candidates:
            # Last resort: keep the existing pick (shouldn't happen in R1)
            assignments[slot] = str(row["player"])
            used.add(str(row["player"]))
            continue
        candidates.sort(reverse=True)
        chosen = candidates[0][1]
        assignments[slot] = chosen
        used.add(chosen)

    # Build new picks rows
    new_rows: list[dict] = []
    board_lookup = board.set_index("player")
    swaps: list[dict] = []
    for _, row in picks.iterrows():
        r = dict(row)
        if int(r["round"]) == 1:
            slot = int(r["pick"])
            new_player = assignments.get(slot, r["player"])
            if new_player != r["player"]:
                swaps.append({"slot": slot, "team": r["team"],
                              "removed": r["player"], "installed": new_player})
            r["player"] = new_player
            if new_player in board_lookup.index:
                brow = board_lookup.loc[new_player]
                if isinstance(brow, pd.DataFrame):
                    brow = brow.iloc[0]
                r["position"] = brow["position"]
                r["school"] = brow["school"]
                r["independent_grade"] = float(brow["independent_grade"])
        new_rows.append(r)

    pd.DataFrame(new_rows).to_csv(PICKS_CSV, index=False)

    # Full-mock sync + dedupe. A player now in R1 may still be listed in a
    # later round from a previous run; we must (a) push the R1 assignment
    # into the mock, (b) replace the stale later-round duplicate with the
    # next-best board player who isn't already picked somewhere in the mock.
    if MOCK_JSON.exists():
        mock = json.loads(MOCK_JSON.read_text(encoding="utf-8"))
        r1_by_slot = {int(r["pick"]): r for r in new_rows if int(r["round"]) == 1}
        # Step 1: overwrite R1 rows in the mock.
        for p in mock.get("picks", []):
            slot = int(p.get("pick", 0))
            if slot in r1_by_slot:
                src = r1_by_slot[slot]
                if p.get("player") != src["player"]:
                    p["player"] = src["player"]
                    p["position"] = src["position"]
                    p["college"] = src.get("school", p.get("college"))
                    p["reasoning"] = ("[realigned to analyst consensus] "
                                      + (p.get("reasoning") or "")[:300])

        # Step 2: dedupe. For each duplicate player, keep the EARLIEST
        # placement and replace the later one with the best unused board
        # player whose final_rank is reasonable for that slot.
        used: dict[str, int] = {}
        dup_slots: list[int] = []
        for i, p in enumerate(mock.get("picks", [])):
            pl = str(p.get("player") or "")
            if not pl:
                continue
            if pl in used:
                dup_slots.append(i)  # this is the LATER placement (by iter order)
            else:
                used[pl] = i

        board_sorted = board.sort_values("final_rank")
        picked_names = set(used.keys())
        # For each duplicate, choose a replacement.
        replacements: list[dict] = []
        for i in dup_slots:
            p = mock["picks"][i]
            slot = int(p.get("pick", 0))
            # Prefer board candidates within +/-30 of slot, else nearest.
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
            replacements.append({
                "slot": slot, "team": p.get("team"),
                "removed": p.get("player"),
                "installed": str(cand["player"]),
                "board_rank": int(cand["final_rank"]),
            })
            p["player"] = str(cand["player"])
            p["position"] = cand.get("position")
            p["college"] = cand.get("school")
            p["rank"] = int(cand["final_rank"])
            p["reasoning"] = "[deduplicated: replaced with next-best board candidate]"

        MOCK_JSON.write_text(json.dumps(mock, indent=2), encoding="utf-8")
        if replacements:
            print(f"[realign_r1] deduplicated {len(replacements)} full-mock rows:")
            for r in replacements[:15]:
                print(f"  #{r['slot']:>3} {r['team']}: "
                      f"{r['removed']} -> {r['installed']} "
                      f"(board rank {r['board_rank']})")

    print(f"[realign_r1] MAX_DELTA={MAX_DELTA} — final R1:")
    for _, row in pd.DataFrame(new_rows).query("round == 1").sort_values("pick").iterrows():
        slot = int(row["pick"])
        pn = str(row["player"])
        hits = player_hits.get(pn, {})
        in_window = {s: c for s, c in hits.items() if abs(s - slot) <= MAX_DELTA}
        tag = (f"analyst {sorted(in_window)}" if in_window
               else f"(Kiper-forced, no analyst w/in {MAX_DELTA})")
        print(f"  #{slot:>2} {row['team']:<3} {pn:<25} {tag}")
    if swaps:
        print(f"\n[realign_r1] made {len(swaps)} swaps")


if __name__ == "__main__":
    main()
