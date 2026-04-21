"""Fix the roster_needs vs qb_urgency inconsistency that caused LV to
not take Mendoza at #1.

The roster_rooms merge overrode QB needs based on post-FA depth, but
some teams' qb_situation is "rebuilding" / "bridge" / "locked" which
should override. E.g., LV has Minshew/O'Connell → room=2 → need=1.2,
but qb_urgency=1.0 says they MUST take a QB.
"""
from __future__ import annotations
import json
from pathlib import Path

ROOT = Path(__file__).parent
TA = ROOT / "data/features/team_agents_2026.json"

d = json.loads(TA.read_text(encoding="utf-8"))

n = 0
for tc, t in d.items():
    if not isinstance(t, dict) or tc.startswith("_"): continue
    rn = t.get("roster_needs") or {}
    qb_urg = float(t.get("qb_urgency") or 0.0)
    qb_sit = t.get("qb_situation") or ""

    # Rule 1: high qb_urgency forces QB to top of needs
    if qb_urg >= 0.8:
        rn["QB"] = max(float(rn.get("QB", 0.0)), 5.5)  # higher than standard 5.0
        n += 1
    elif qb_urg >= 0.5:
        rn["QB"] = max(float(rn.get("QB", 0.0)), 4.0)
        n += 1
    elif qb_urg >= 0.3:
        rn["QB"] = max(float(rn.get("QB", 0.0)), 2.5)
    elif qb_sit == "locked":
        # Lock in: QB can't be > 2
        if "QB" in rn and float(rn["QB"]) > 2.0:
            rn["QB"] = 1.5

    # Re-sort
    t["roster_needs"] = dict(sorted(rn.items(), key=lambda kv: -float(kv[1])))

TA.write_text(json.dumps(d, indent=2, ensure_ascii=False), encoding="utf-8")
print(f"QB-need sync applied to {n} teams")

# Verify LV specifically
lv = d["LV"]
print(f"\nLV verify: needs={lv['roster_needs']}, qb_urg={lv.get('qb_urgency')}")
