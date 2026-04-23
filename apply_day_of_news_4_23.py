"""Apply draft-morning 4/23/26 news to team_agents_2026.json.

Sources (verified against ESPN, NFL.com, CBS Sports, SI, Bleeding Green Nation on
draft-morning):
  - Giants "love" Jordyn Tyson at #5 (NFL.com final buzz)
  - Eagles plotting trade-up; Roseman active (Jeremiah final mock)
  - Giants less likely to deal Thibodeaux post-Lawrence trade (NFL.com)
  - AJ Brown not attending Eagles workouts; June-1 trade watch (CBS)
  - Cowboys prefer trade-down from #20 over trade-up from #12 (CBS rumors)
  - Kiper/Jeremiah/McShay top-5 aligned: Mendoza, Love, Reese, Styles, Bailey
  - Expectation of 9 OL in R1 (deep OL class signal)

Only items that are NEW vs the 4/22 application are written. Nothing invented.
"""
from __future__ import annotations
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).parent
TA = ROOT / "data/features/team_agents_2026.json"
d = json.loads(TA.read_text(encoding="utf-8"))


def append_news(team: str, note: str) -> None:
    if team not in d or not isinstance(d[team], dict):
        return
    existing = d[team].get("_4_23_news", [])
    if isinstance(existing, str):
        existing = [existing]
    existing.append(note)
    d[team]["_4_23_news"] = existing


def set_path(team: str, dotted: str, value) -> None:
    if team not in d:
        return
    obj = d[team]
    keys = dotted.split(".")
    for k in keys[:-1]:
        obj = obj.setdefault(k, {})
    obj[keys[-1]] = value


def bump_need(team: str, pos: str, floor: float) -> None:
    needs = d.get(team, {}).get("roster_needs", {})
    if not needs:
        return
    needs[pos] = max(float(needs.get(pos, 0)), floor)
    d[team]["roster_needs"] = dict(sorted(needs.items(), key=lambda kv: -kv[1]))


# ──────────────────────── NYG @ 5 ────────────────────────
append_news(
    "NYG",
    "Draft-morning 4/23 (NFL.com final): Giants 'love' Jordyn Tyson at #5. "
    "Combined with Schefter's Love-to-ARI call, NYG-Tyson at 5 is now a "
    "market and insider consensus lean.",
)
bump_need("NYG", "WR", 3.0)

# ──────────────────────── NYG — Thibodeaux ────────────────────────
append_news(
    "NYG",
    "NFL.com buzz 4/23: Giants 'less likely to deal Thibodeaux' post-Lawrence. "
    "EDGE not a forced trade chip — roster stays intact.",
)

# ──────────────────────── PHI @ 23 ────────────────────────
append_news(
    "PHI",
    "CBS Sports 4/23: AJ Brown trade to Patriots 'still tracking' for on/after "
    "June 1 (Eagles clear $7M cap that date). Brown not attending workouts. "
    "WR urgency at 23 deferred — Roseman still plotting trade-up for OL/EDGE.",
)
# Keep WR softer on PHI pre-June-1 — urgency is post-draft
cur = d.get("PHI", {}).get("roster_needs", {})
if "WR" in cur:
    cur["WR"] = min(float(cur["WR"]), 2.0)
    d["PHI"]["roster_needs"] = dict(sorted(cur.items(), key=lambda kv: -kv[1]))

# ──────────────────────── DAL @ 12 / 20 ────────────────────────
append_news(
    "DAL",
    "CBS rumors 4/23: Cowboys prefer trade-down from #20 over trade-up from #12. "
    "Jerry: 'trades are open.' Mock markets price DAL@12 staying, DAL@20 active.",
)
set_path("DAL", "trade_behavior.trade_up_rate", 0.30)   # dial down vs 4/21
set_path("DAL", "trade_behavior.trade_down_rate", 0.55)

# ──────────────────────── Board consensus note ────────────────────────
# Kiper, Jeremiah, McShay all have top-5: Mendoza, Love, Reese, Styles, Bailey.
# We already bake this in via the board; just tag for the record.
meta = d.get("_meta", {})
if not isinstance(meta, dict):
    meta = {}
meta["latest_intel_date"] = "2026-04-23"
meta["latest_intel_scraped_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
meta.setdefault("analyst_intel_meta", {})
meta["analyst_intel_meta"]["latest_intel_date"] = "2026-04-23"
sources = meta["analyst_intel_meta"].setdefault("sources", {})
sources.setdefault("2026-04-23", []).extend([
    "NFL.com draft-morning final buzz",
    "CBS Sports draft rumors",
    "SI NFL draft trade tracker",
    "Bleeding Green Nation (Roseman intel)",
    "Kiper/Jeremiah/McShay final top 150s",
])
d["_meta"] = meta

# ──────────────────────── Top-5 consensus note ────────────────────────
# Leave a pinned note that the top-5 is Mendoza/Love/Reese/Styles/Bailey per
# all major boards — reinforces the MC's R1 picks 1-5 output.
d["_meta_top5_consensus_2026"] = {
    "date": "2026-04-23",
    "top5": ["Fernando Mendoza", "Jeremiyah Love", "Arvell Reese", "Sonny Styles", "David Bailey"],
    "agreement": "Kiper, Jeremiah, McShay all list these five in some order",
    "note": "Order varies but set is stable — treat top-5 as the consensus cluster.",
}

TA.write_text(json.dumps(d, indent=2, ensure_ascii=False), encoding="utf-8")
print(f"[4/23] wrote {TA}")
touched = [k for k, v in d.items() if isinstance(v, dict) and "_4_23_news" in v]
print(f"[4/23] teams with 4/23 news: {len(touched)} — {', '.join(touched)}")
