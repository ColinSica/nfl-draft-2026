"""Build a 7-round mock WITH trades from the no-trade mock.

Source research (4/23/26):
  - Tom Pelissero (NFL Network): Cardinals & Titans "checking interest
    from top-10 teams", Saints up from #8, Chiefs up from #9 for edge,
    Patriots & Seahawks have received calls about moving down.
  - Bill Barnwell (ESPN): Titans trade DOWN #4, Chiefs UP from #9,
    Eagles UP from #23, Bears UP from #25, Cowboys DOWN from #20,
    Lions DOWN from #17, Seahawks DOWN from #32.
  - Lance Zierlein: Cowboys trade UP (#12) for Arvell Reese.
  - NFL.com buzz: Chiefs, Saints among teams who could trade up.
  - Daniel Jeremiah final mock: Eagles & Saints trade up.

Synthesized R1 trades (strongest consensus signals only — 3 trades):

  Trade 1: KC sends #9 + #29 + 2027 3rd -> ARI.
           KC moves to #3, takes Arvell Reese (EDGE). ARI gets #9 + #29
           + future pick. Multi-source: Pelissero (KC up), Barnwell (KC
           up for premium pass-rusher), Pelissero (ARI checking
           interest), Zierlein (DAL wanted Reese but KC out-bid).

  Trade 2: PHI sends #23 + 2026 2nd (#55) -> DET. PHI moves to #17 for
           OT (Max Iheanachor). DET moves back to #23 + #55. Source:
           Barnwell (PHI up for OT, DET down for financial flexibility),
           Pelissero (DET may trade up before #17 — but we model the
           down-side). Jeremiah (PHI up).

  Trade 3: SEA sends #32 + #82 -> CIN (who has no R1). SEA moves back
           out of R1 into R2. CIN gains a late-R1 pick. Source:
           Pelissero (SEA has received calls), Barnwell (SEA down,
           Schneider pattern).

R2-R7 picks unchanged from the no-trade mock (trade intel doesn't
reliably extend beyond R1 in public reporting).
"""
from __future__ import annotations

import json
import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "data/processed/full_mock_2026.json"
OUT_JSON = ROOT / "data/processed/full_mock_2026_with_trades.json"
OUT_CSV = ROOT / "data/processed/full_mock_2026_with_trades.csv"
BOARD_CSV = ROOT / "data/processed/predictions_2026_independent.csv"


# Trade-induced team reassignments: slot -> new team.
# Player assignments also change where the original team's player doesn't
# fit the new team's draft strategy.
TRADE_DEFS: list[dict] = [
    {
        "id": "KC_up_ARI_back",
        "headline": "Chiefs trade UP for Arvell Reese",
        "sources": ["Pelissero (NFL Network)", "Barnwell (ESPN)"],
        "package": {
            "KC": {
                "role": "Trades up",
                "gives": ["2026 1st (#9)", "2026 1st (#29)", "2027 2nd"],
                "gets":  ["2026 1st (#3)"],
            },
            "ARI": {
                "role": "Trades back",
                "gives": ["2026 1st (#3)"],
                "gets":  ["2026 1st (#9)", "2026 1st (#29)", "2027 2nd"],
            },
        },
        "slot_reassignments": {
            3:  {"team": "KC",  "player": "Arvell Reese", "reason": "KC moves up for elite pass rusher"},
            9:  {"team": "ARI", "player": None, "reason": "ARI selects BPA after trade-back"},
            29: {"team": "ARI", "player": None, "reason": "Compensation pick received from KC"},
        },
    },
    {
        "id": "PHI_up_DET_back",
        "headline": "Eagles trade UP for Thieneman (S)",
        "sources": ["Barnwell (ESPN)", "Jeremiah (NFL.com)"],
        "package": {
            "PHI": {
                "role": "Trades up",
                "gives": ["2026 1st (#23)", "2026 2nd", "2027 3rd"],
                "gets":  ["2026 1st (#17)"],
            },
            "DET": {
                "role": "Trades back",
                "gives": ["2026 1st (#17)"],
                "gets":  ["2026 1st (#23)", "2026 2nd", "2027 3rd"],
            },
        },
        "slot_reassignments": {
            17: {"team": "PHI", "player": None, "reason": "PHI moves up for top safety"},
            23: {"team": "DET", "player": None, "reason": "DET trades back to recoup day-2 capital"},
        },
    },
    {
        "id": "CHI_up_NYJ_back",
        "headline": "Bears trade UP for DL, jump Lions",
        "sources": ["Barnwell (ESPN)"],
        "package": {
            "CHI": {
                "role": "Trades up",
                "gives": ["2026 1st (#25)", "2026 2nd (#60)", "2027 3rd"],
                "gets":  ["2026 1st (#16)"],
            },
            "NYJ": {
                "role": "Trades back",
                "gives": ["2026 1st (#16)"],
                "gets":  ["2026 1st (#25)", "2026 2nd (#60)", "2027 3rd"],
            },
        },
        "slot_reassignments": {
            16: {"team": "CHI", "player": None, "reason": "CHI pairs #25 + Buffalo #60 to jump Lions at #17"},
            25: {"team": "NYJ", "player": None, "reason": "NYJ adds to R1 stockpile (5 R1 picks in 2 years)"},
        },
    },
    {
        "id": "DAL_back_IND_up",
        "headline": "Colts trade UP (back into R1)",
        "sources": ["Barnwell (ESPN)"],
        "package": {
            "IND": {
                "role": "Trades up (re-enters R1)",
                "gives": ["2026 2nd", "2026 3rd", "2027 2nd"],
                "gets":  ["2026 1st (#20)"],
            },
            "DAL": {
                "role": "Trades back",
                "gives": ["2026 1st (#20)"],
                "gets":  ["2026 2nd", "2026 3rd", "2027 2nd"],
            },
        },
        "slot_reassignments": {
            20: {"team": "IND", "player": None, "reason": "IND jumps into R1; DAL needs day-2 capital"},
        },
    },
    {
        "id": "NE_back_GB_up",
        "headline": "Packers trade UP (back into R1)",
        "sources": ["Pelissero (NFL Network)"],
        "package": {
            "GB": {
                "role": "Trades up (re-enters R1)",
                "gives": ["2026 2nd", "2027 3rd"],
                "gets":  ["2026 1st (#31)"],
            },
            "NE": {
                "role": "Trades back",
                "gives": ["2026 1st (#31)"],
                "gets":  ["2026 2nd", "2027 3rd"],
            },
        },
        "slot_reassignments": {
            31: {"team": "GB", "player": None, "reason": "GB re-enters R1 for 5th-year-option eligibility"},
        },
    },
    {
        "id": "SEA_back_out_of_R1",
        "headline": "Bengals trade UP (back into R1)",
        "sources": ["Pelissero (NFL Network)", "Barnwell (ESPN)"],
        "package": {
            "CIN": {
                "role": "Trades up (re-enters R1)",
                "gives": ["2026 2nd", "2026 3rd", "2027 3rd"],
                "gets":  ["2026 1st (#32)"],
            },
            "SEA": {
                "role": "Trades back",
                "gives": ["2026 1st (#32)"],
                "gets":  ["2026 2nd", "2026 3rd", "2027 3rd"],
            },
        },
        "slot_reassignments": {
            32: {"team": "CIN", "player": None, "reason": "CIN re-enters R1; Schneider's historical trade-down pattern"},
        },
    },
]


def _best_on_board_for_team(board: list[dict], team: str,
                             team_needs: dict[str, list[str]],
                             used: set[str],
                             current_pick: int,
                             max_delta: int = 15) -> dict | None:
    """Pick the best available board prospect for a team, weighting their
    top-3 needs. Board is sorted by final_rank ascending."""
    needs = team_needs.get(team, [])
    best = None
    for row in board:
        if row["player"] in used:
            continue
        fr = int(row["final_rank"])
        if fr > current_pick + max_delta:
            break
        pos = row.get("position", "")
        need_rank = needs.index(pos) if pos in needs else 99
        # Prefer: top-3 need match, then board rank
        score = -fr + (20 if need_rank < 3 else 10 if need_rank < 6 else 0)
        if best is None or score > best[0]:
            best = (score, row)
    return best[1] if best else None


def main() -> None:
    mock = json.loads(SOURCE.read_text(encoding="utf-8"))
    # Board sorted by rank
    import pandas as pd
    board_df = pd.read_csv(BOARD_CSV).sort_values("final_rank")
    board = board_df.to_dict("records")
    # Team needs from CBS
    team_agents = json.loads(
        (ROOT / "data/features/team_agents_2026.json").read_text(encoding="utf-8"))
    team_needs: dict[str, list[str]] = {}
    for t, a in team_agents.items():
        if t.startswith("_"):
            continue
        rn = a.get("roster_needs", {}) or {}
        team_needs[t] = [p for p, _ in sorted(rn.items(), key=lambda x: -x[1])]

    # Start from a fresh dict so we can rewrite safely
    picks = [dict(p) for p in mock.get("picks", [])]
    pick_by_slot = {int(p["pick"]): p for p in picks}

    # Apply trades
    applied_notes: list[dict] = []
    for td in TRADE_DEFS:
        for slot, reassign in td["slot_reassignments"].items():
            if slot not in pick_by_slot:
                continue
            target = pick_by_slot[slot]
            old_team = target.get("team")
            new_team = reassign["team"]
            target["team"] = new_team
            # Flag trade metadata — include enough so the frontend can
            # render a clear "TRADE" badge + package detail.
            target["_trade"] = {
                "id": td["id"],
                "from": old_team,
                "to": new_team,
                "reason": reassign["reason"],
                "headline": td.get("headline", td["id"]),
                "description": td.get("description"),
                "sources": td.get("sources", []),
                "package": td.get("package", {}),
            }
            # Player override
            if reassign.get("player"):
                target["player"] = reassign["player"]
                # Pull updated position/college from board if possible
                brow = next((r for r in board
                             if r["player"] == reassign["player"]), None)
                if brow:
                    target["position"] = brow.get("position")
                    target["college"] = brow.get("school")
                    target["rank"] = int(brow.get("final_rank", 0))
                target["reasoning"] = "[TRADE] " + reassign["reason"]
            applied_notes.append({"slot": slot, "from": old_team,
                                  "to": new_team, "trade": td["id"],
                                  "player": target.get("player")})

    # After trades, re-choose players for slots whose team changed but
    # where the original player doesn't fit the new team's top-5 needs.
    used = {p.get("player") for p in picks if p.get("player")}
    # Collect every slot whose team changed but has no forced player.
    reassigned_slots: dict[int, str] = {}
    for td in TRADE_DEFS:
        for slot, rs in td["slot_reassignments"].items():
            if rs.get("player"):
                continue  # already explicitly set (e.g. KC->Reese at #3)
            reassigned_slots[slot] = rs["team"]
    for slot, team in reassigned_slots.items():
        target = pick_by_slot[slot]
        current_player = target.get("player")
        # The player currently at this slot (from no-trade mock) might
        # still be the best choice. Keep them if the original team that
        # drafted them also needed that position AND the new team's top
        # need set overlaps. Otherwise replace with team-fit BPA.
        pos = target.get("position", "")
        needs = team_needs.get(team, [])
        if pos in needs[:5]:
            continue  # already a top-5 fit for new team
        # Remove old choice from used set so we can reclaim somebody
        if current_player:
            used.discard(current_player)
        sub = _best_on_board_for_team(board, team, team_needs, used, slot)
        if sub:
            target["player"] = sub["player"]
            target["position"] = sub.get("position")
            target["college"] = sub.get("school")
            target["rank"] = int(sub.get("final_rank", 0))
            used.add(sub["player"])
            target["reasoning"] = (
                f"[TRADE] {team} selected BPA after trade — "
                f"{sub.get('position')} {sub.get('player')}"
            )

    # Write outputs
    mock_out = dict(mock)
    mock_out["picks"] = picks
    mock_out["trades_applied"] = [
        {"id": td["id"], "description": td.get("headline", td["id"])}
        for td in TRADE_DEFS
    ]
    mock_out["variant"] = "with_trades"
    OUT_JSON.write_text(json.dumps(mock_out, indent=2), encoding="utf-8")

    with OUT_CSV.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=[
            "pick", "round", "team", "player", "position", "college", "rank",
            "trade_from", "trade_to",
        ])
        w.writeheader()
        for p in picks:
            trade = p.get("_trade") or {}
            w.writerow({
                "pick": p.get("pick"),
                "round": p.get("round"),
                "team": p.get("team"),
                "player": p.get("player"),
                "position": p.get("position"),
                "college": p.get("college"),
                "rank": p.get("rank"),
                "trade_from": trade.get("from", ""),
                "trade_to": trade.get("to", ""),
            })

    print(f"Wrote {OUT_JSON.name} + {OUT_CSV.name}")
    print(f"Trades applied:")
    for td in TRADE_DEFS:
        print(f"  - {td.get('headline', td['id'])}")
    print(f"Slot changes: {len(applied_notes)}")
    for note in applied_notes:
        print(f"  #{note['slot']:>2}: {note['from']} -> {note['to']} "
              f"({note['player'] or 'player TBD'})")


if __name__ == "__main__":
    main()
