"""Regenerate the `reasoning` field on every pick in both full mocks.

Rules:
  - Picks are not changed. Only the `reasoning` string is rewritten.
  - Every other field (generated_at, source_board_mtime, score, factors,
    alternates, trade metadata) is preserved byte-for-byte.
  - CSV files are unaffected (they have no reasoning column).
  - Reasoning is generated from live facts: current player, team needs
    per CBS cheat-sheet, board rank, reach/value delta, GM affinity,
    scheme notes, and — for the trade mock — the trade package already
    attached to the pick.

Safe to re-run. Idempotent modulo wording.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
TEAM_AGENTS = ROOT / "data/features/team_agents_2026.json"
MOCKS = [
    ROOT / "data/processed/full_mock_2026.json",
    ROOT / "data/processed/full_mock_2026_with_trades.json",
]

POS_NAMES = {
    "QB": "quarterback", "RB": "running back", "WR": "wide receiver",
    "TE": "tight end", "OT": "offensive tackle", "IOL": "interior O-line",
    "EDGE": "edge rusher", "DL": "defensive lineman", "IDL": "interior D-line",
    "LB": "linebacker", "CB": "cornerback", "S": "safety",
    "K": "kicker", "P": "punter", "LS": "long snapper",
}

# Map nuanced position labels to the need-bucket used in roster_needs.
POS_TO_NEED = {
    "QB": "QB", "RB": "RB", "WR": "WR", "TE": "TE",
    "OT": "OT", "IOL": "IOL", "OL": "IOL", "C": "IOL", "G": "IOL",
    "EDGE": "EDGE",
    "DL": "IDL", "DT": "IDL", "IDL": "IDL", "NT": "IDL",
    "LB": "LB",
    "CB": "CB", "S": "S", "DB": "CB", "FS": "S", "SS": "S",
}


def _need_priority(needs: dict[str, float], pos: str) -> tuple[int, str]:
    """Return (rank, label). rank: 1 = #1 need, 2 = #2, ... 99 = not in needs."""
    if not needs:
        return 99, "off-need"
    bucket = POS_TO_NEED.get((pos or "").upper(), pos or "")
    sorted_needs = sorted(needs.items(), key=lambda x: -x[1])
    for i, (p, _) in enumerate(sorted_needs, start=1):
        if p == bucket:
            return i, f"#{i} need"
    return 99, "off-need"


def _need_phrase(rank: int) -> str:
    if rank == 1: return "the #1 need on the board"
    if rank == 2: return "a top-2 need"
    if rank == 3: return "a top-3 need"
    if rank <= 5: return "a top-5 need"
    if rank <= 8: return "a secondary need"
    return "a depth-chart addition"


def _value_phrase(slot: int, rank: Any) -> str:
    try:
        r = int(rank)
    except Exception:
        return ""
    delta = r - slot
    if delta <= -8:  return f"strong value — {slot - r} slots ahead of the board (rank #{r})"
    if delta <= -3:  return f"mild value pick ({-delta} slots ahead of board rank #{r})"
    if delta <= 2:   return f"on schedule with the board (rank #{r})"
    if delta <= 6:   return f"modest reach ({delta} slots past board rank #{r})"
    if delta <= 12:  return f"reach for position — {delta} slots past board rank #{r}"
    return f"notable reach (board rank #{r}, slot {slot})"


def _gm_affinity_note(agent: dict, pos: str) -> str:
    aff = (agent.get("gm_affinity") or {})
    # gm_affinity may be a mapping pos -> weight or a dict with 'positions'
    top: list[str] = []
    if isinstance(aff, dict):
        if "positions" in aff and isinstance(aff["positions"], dict):
            items = aff["positions"]
        else:
            items = aff
        try:
            ranked = sorted([(k, float(v)) for k, v in items.items()
                             if isinstance(v, (int, float))],
                            key=lambda x: -x[1])
            top = [k for k, _ in ranked[:3]]
        except Exception:
            top = []
    bucket = POS_TO_NEED.get((pos or "").upper(), pos or "")
    if bucket in top:
        return " Also a position the GM has reached for historically."
    return ""


def _scheme_note(agent: dict, pos: str) -> str:
    """Pull the OC or DC position-archetype line that matches `pos`, if the
    team profile has one. Falls back to empty string — better no scheme
    note than a generic one."""
    raw = agent.get("scheme_archetype_tags") or {}
    if not isinstance(raw, dict):
        return ""
    bucket = POS_TO_NEED.get((pos or "").upper(), pos or "")
    # Archetype keys inside oc/dc blocks
    key_map = {
        "QB":  ("oc", "qb_archetype"),
        "RB":  ("oc", "rb_archetype"),
        "WR":  ("oc", "wr_archetype"),
        "TE":  ("oc", "te_archetype"),
        "OT":  ("oc", "ol_archetype"),
        "IOL": ("oc", "ol_archetype"),
        "EDGE": ("dc", "edge_archetype"),
        "IDL": ("dc", "dl_archetype"),
        "DL":  ("dc", "dl_archetype"),
        "LB":  ("dc", "lb_archetype"),
        "CB":  ("dc", "cb_archetype"),
        "S":   ("dc", "s_archetype"),
    }
    k = key_map.get(bucket)
    if not k:
        return ""
    side = raw.get(k[0]) or {}
    if not isinstance(side, dict):
        return ""
    archetype = side.get(k[1])
    if not archetype or not isinstance(archetype, str):
        return ""
    # Trim to a single clause
    clause = archetype.split(",")[0].split(";")[0].strip()
    if len(clause) > 110:
        clause = clause[:107].rstrip() + "..."
    return f" Scheme fit: {clause.lower()}."


def _trade_header(trade: dict | None) -> str:
    if not trade:
        return ""
    headline = trade.get("headline") or trade.get("id") or "trade"
    frm = trade.get("from")
    to = trade.get("to")
    if frm and to:
        return f"[TRADE: {headline}] {frm} -> {to}. "
    return f"[TRADE: {headline}] "


def _pos_long(pos: str) -> str:
    key = (pos or "").upper()
    return POS_NAMES.get(key, (pos or "prospect").lower())


def _compose_reasoning(pick: dict, agent: dict | None) -> str:
    slot = int(pick.get("pick") or 0)
    rnd = int(pick.get("round") or 0)
    team = pick.get("team") or "—"
    player = pick.get("player") or "TBD"
    pos = pick.get("position") or ""
    college = pick.get("college") or ""
    rank = pick.get("rank")
    trade = pick.get("_trade")

    needs = (agent or {}).get("roster_needs") or {}
    need_rank, need_label = _need_priority(needs, pos)
    need_phrase = _need_phrase(need_rank)

    value_phrase = _value_phrase(slot, rank)
    gm_note = _gm_affinity_note(agent or {}, pos)
    scheme_note = _scheme_note(agent or {}, pos)

    college_phrase = f", {college}" if college else ""
    pos_display = _pos_long(pos)

    # Open with trade header if applicable
    head = _trade_header(trade)

    # R1 gets a longer, bespoke sentence; R2+ gets a tighter template
    if rnd == 1 and slot <= 10:
        # Top-10 — more narrative, emphasize QB scarcity / trench premium
        if pos == "QB":
            body = (
                f"{team} takes {player} ({pos}{college_phrase}) at #{slot}. "
                f"Quarterback is {need_phrase} for this roster; he's the "
                f"{pos_display} the front office has been connected to "
                f"throughout the pre-draft cycle. {value_phrase.capitalize()}."
            )
        elif pos in ("OT", "EDGE", "CB"):
            body = (
                f"{team} stays on the trench/premium-position board with "
                f"{player} ({pos}{college_phrase}). Covers {need_phrase}; "
                f"{value_phrase}."
            )
        else:
            body = (
                f"{team} selects {player} ({pos}{college_phrase}) at #{slot}. "
                f"{pos_display.capitalize()} is {need_phrase}; {value_phrase}."
            )
    elif rnd == 1:
        body = (
            f"{team} takes {player} ({pos}{college_phrase}) at pick #{slot}. "
            f"{pos_display.capitalize()} addresses {need_phrase} for this "
            f"roster; {value_phrase}."
        )
    elif rnd == 2:
        body = (
            f"Day 2 opens with {player} ({pos}{college_phrase}) to {team} at "
            f"#{slot}. {pos_display.capitalize()} — {need_phrase} — filled "
            f"with a {value_phrase}."
        )
    elif rnd == 3:
        body = (
            f"{team} grabs {player} ({pos}{college_phrase}) in the third "
            f"round. {pos_display.capitalize()} coverage at {need_phrase}; "
            f"{value_phrase}."
        )
    else:
        body = (
            f"{team} adds {player} ({pos}{college_phrase}) in round {rnd}. "
            f"{pos_display.capitalize()} — {need_label} — {value_phrase}."
        )

    tail = (gm_note + scheme_note).rstrip()
    reasoning = (head + body + " " + tail).strip()
    # Collapse accidental double spaces
    while "  " in reasoning:
        reasoning = reasoning.replace("  ", " ")
    return reasoning


def main() -> None:
    team_agents = json.loads(TEAM_AGENTS.read_text(encoding="utf-8"))

    for mock_path in MOCKS:
        if not mock_path.exists():
            continue
        mock = json.loads(mock_path.read_text(encoding="utf-8"))
        picks = mock.get("picks") or []
        for p in picks:
            team = p.get("team")
            agent = team_agents.get(team) if team else None
            p["reasoning"] = _compose_reasoning(p, agent)
            # For trade picks, also refresh the human-readable `_trade.reason`
            # so it matches the current player at that slot (the headline /
            # package / sources stay unchanged).
            trade = p.get("_trade")
            if trade:
                pos = p.get("position") or ""
                needs = (agent or {}).get("roster_needs") or {}
                n_rank, _ = _need_priority(needs, pos)
                n_phrase = _need_phrase(n_rank)
                trade["reason"] = (
                    f"{team} selects {p.get('player')} ({pos}) — "
                    f"{n_phrase} after the trade."
                )

        mock_path.write_text(json.dumps(mock, indent=2), encoding="utf-8")
        print(f"[reasoning] rewrote {len(picks)} picks in {mock_path.name}")


if __name__ == "__main__":
    main()
