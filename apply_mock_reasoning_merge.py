"""Merge mock_reasoning_bank_2026.json (Agent 1) into team + prospect profiles.

Team_reasoning (scheme_cited, needs_cited, archetype_cited, gm_tendency_cited)
  -> team_agents_2026.json `analyst_reasoning` field (non-picking, profile flavor)
  -> Also bumps team_archetype_preferences_2026.json for frequently-cited archetypes

Prospect_reasoning (traits, comps, scheme_fits, risk)
  -> prospect_archetypes_2026.json tags (union with existing)
"""
from __future__ import annotations
import json, re
from pathlib import Path
from collections import Counter

ROOT = Path(__file__).parent
FEAT = ROOT / "data" / "features"

MOCK = FEAT / "mock_reasoning_bank_2026.json"
TEAM_AGENTS = FEAT / "team_agents_2026.json"
PROSPECT_ARCH = FEAT / "prospect_archetypes_2026.json"
TEAM_ARCH_PREF = FEAT / "team_archetype_preferences_2026.json"

mock = json.loads(MOCK.read_text(encoding="utf-8"))
agents = json.loads(TEAM_AGENTS.read_text(encoding="utf-8"))
archs = json.loads(PROSPECT_ARCH.read_text(encoding="utf-8"))
pref = json.loads(TEAM_ARCH_PREF.read_text(encoding="utf-8")) if TEAM_ARCH_PREF.exists() else {}

def _norm_tag(s):
    if not isinstance(s, str): return None
    t = re.sub(r"[^a-z0-9_ ]", "", s.strip().lower())
    t = t.replace(" ", "_").replace("-", "_")
    return t or None


# ---- Team reasoning merge ----
team_reasoning = mock.get("team_reasoning", {}) or {}
n_team = 0
for tc, r in team_reasoning.items():
    if tc not in agents: continue
    agents[tc]["analyst_reasoning"] = r  # attach full block for traceability

    # Bump archetype preferences based on cited archetypes
    cited_arches = r.get("archetype_cited", []) or []
    if cited_arches:
        pref.setdefault(tc, {})
        for arche in cited_arches:
            tag = _norm_tag(arche)
            if not tag: continue
            pref[tc][tag] = max(float(pref[tc].get(tag, 0.0)), 1.5)  # cap modest
    n_team += 1

# ---- Prospect reasoning merge ----
prospect_reasoning = mock.get("prospect_reasoning", {}) or {}
n_pros = 0
for name, pr in prospect_reasoning.items():
    # Build tag set from traits, scheme_fits, comps (as tags)
    tag_sources = []
    tag_sources.extend(pr.get("traits") or [])
    tag_sources.extend(pr.get("scheme_fits") or [])
    tag_sources.extend(pr.get("archetype_tags") or [])
    tag_sources.extend(pr.get("strengths") or [])
    norm = {t for t in (_norm_tag(s) for s in tag_sources) if t}
    if not norm: continue

    if name not in archs:
        archs[name] = {"tags": [], "_source": "mock_reasoning"}
    existing = set(archs[name].get("tags") or [])
    archs[name]["tags"] = sorted(existing | norm)
    # Preserve mention count hint (used as signal of scouting breadth)
    mc = pr.get("analyst_mention_count") or pr.get("mention_count") or 0
    if mc:
        cur = archs[name].get("_board_mention_count", 0)
        archs[name]["_board_mention_count"] = max(int(cur or 0), int(mc))
    n_pros += 1

# Persist
TEAM_AGENTS.write_text(json.dumps(agents, indent=2, ensure_ascii=False),
                       encoding="utf-8")
PROSPECT_ARCH.write_text(json.dumps(archs, indent=2, ensure_ascii=False),
                         encoding="utf-8")
TEAM_ARCH_PREF.write_text(json.dumps(pref, indent=2, ensure_ascii=False),
                           encoding="utf-8")
print(f"Team reasoning merged: {n_team} teams")
print(f"Prospect tags merged:  {n_pros} prospects")
print(f"Archetype preferences bumped: {sum(1 for v in pref.values() if v)} teams")
