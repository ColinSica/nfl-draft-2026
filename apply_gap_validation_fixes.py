"""Apply data fixes from r1_gap_validation_2026.json research.

Per research findings:
  - Woods, Parker, Faulk, Cooper Jr. over-promoted → strip excess premium tags
  - Tate, McNeil-Warren under-ranked → add premium tags
  - McCoy medical 0.50 → soften to 0.65
"""
from __future__ import annotations
import json
from pathlib import Path

ROOT = Path(__file__).parent
ARCH = ROOT / "data/features/prospect_archetypes_2026.json"
TA = ROOT / "data/features/team_agents_2026.json"

archs = json.loads(ARCH.read_text(encoding="utf-8"))
agents = json.loads(TA.read_text(encoding="utf-8"))

# --- Strip excess premium from over-promoted prospects ---
# These tags are being matched by model's premium-prefix dict and pulling them
# too early. Research shows they don't have consensus support.
strip_tags = {
    "Peter Woods":  {"elite_youth", "explosive_athlete", "hybrid_di",
                     "disruptive_interior", "penetrator", "high_ceiling_dt"},
    "T.J. Parker":  {"explosive_athlete", "elite_bend", "allamerican"},
    "Omar Cooper Jr.": {"elite_burst", "explosive_athlete",
                        "plus_separation", "plus_ball_skills"},
    "Keldric Faulk": {"explosive_athlete", "elite_bend", "versatile",
                     "hybrid_edge_di"},
}

n_stripped = 0
for name, to_strip in strip_tags.items():
    e = archs.get(name)
    if not e: continue
    before = set(e.get("tags") or [])
    after = before - to_strip
    if len(after) < len(before):
        e["tags"] = sorted(after)
        n_stripped += 1

# --- Add premium tags to under-ranked prospects ---
add_tags = {
    "Carnell Tate":            ["elite_hands", "plus_separation",
                                "allamerican", "versatile"],
    "Emmanuel McNeil-Warren":  ["elite_range", "versatile", "allamerican",
                               "plus_coverage"],
    "Jermod McCoy":            ["elite_athleticism", "press_man",
                               "allamerican", "plus_ball_skills"],
    "Makai Lemon":             ["elite_separation", "explosive_athlete",
                               "allamerican"],
    # Bain gets a small nudge since he's borderline
    "Rueben Bain":             ["elite_bend", "plus_power", "explosive_athlete"],
}

n_added = 0
for name, tags in add_tags.items():
    e = archs.setdefault(name, {"tags": []})
    before = set(e.get("tags") or [])
    merged = before | set(tags)
    if len(merged) > len(before):
        e["tags"] = sorted(merged)
        n_added += 1

# --- Soften McCoy medical flag per research (Kiper has him #16 with full injury context) ---
med_flags = agents.get("_meta_medical_flags_2026") or {}
if "Jermod McCoy" in med_flags:
    # was severity=medium or similar with 0.50 multiplier — change to low severity
    med_flags["Jermod McCoy"] = {
        "type": "acl_recovery_clean",
        "severity": "low",  # was medium/high
        "detail": "Kiper 4/19 research: ACL recovery complete, 4.37 forty, full injury context priced in at consensus #16."
    }
    agents["_meta_medical_flags_2026"] = med_flags

ARCH.write_text(json.dumps(archs, indent=2, ensure_ascii=False),
                encoding="utf-8")
TA.write_text(json.dumps(agents, indent=2, ensure_ascii=False),
              encoding="utf-8")
print(f"Stripped excess premium from {n_stripped} over-promoted prospects")
print(f"Added premium to {n_added} under-ranked prospects")
print(f"McCoy medical softened to low severity")
