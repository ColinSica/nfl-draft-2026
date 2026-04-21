"""Merge research agent outputs into team_agents_2026.json + prospect_archetypes_2026.json.

Data sources (finished agents only — agents 1, 7 may add later):
  - scheme_and_roster_intel_2026.json (Agent 6)
  - supplementary_intel_2026.json     (Agent 3)
  - big_board_reasoning_2026.json     (Agent 2)
  - accuracy_drivers_2026.json        (Agent 4 — tuning recs, documentation only)
  - backtest_2020_2025.json           (Agent 5 — tuning recs, documentation only)

Targets:
  - team_agents_2026.json
      * roster_needs: overwrite from pillar2_roster_composition (room score -> weight)
      * scheme: enrich with OC/DC archetype tags from pillar1_scheme_taxonomy
      * coaching_tree: annotate from supplementary_intel coach_gm_tendencies
  - prospect_archetypes_2026.json
      * tags: add archetype_tags + strength tags from big_board_reasoning

Backup previous versions as .pre_research_merge_bak.json. Never touches MC code.
"""
from __future__ import annotations
import json, shutil
from pathlib import Path

ROOT = Path(__file__).parent
FEAT = ROOT / "data" / "features"

TEAM_AGENTS = FEAT / "team_agents_2026.json"
PROSPECT_ARCH = FEAT / "prospect_archetypes_2026.json"

SCHEME_ROSTER = FEAT / "scheme_and_roster_intel_2026.json"
SUPP_INTEL = FEAT / "supplementary_intel_2026.json"
BIG_BOARD = FEAT / "big_board_reasoning_2026.json"

# room score (1-5) -> need weight mapping
ROOM_TO_WEIGHT = {5: 5.0, 4: 4.0, 3: 2.5, 2: 1.2, 1: 0.0}

ROOM_TO_POS = {
    "qb_room": "QB",
    "rb_room": "RB",
    "wr_room": "WR",
    "te_room": "TE",
    "ot_room": "OT",
    "iol_room": "IOL",
    "edge_room": "EDGE",
    "dt_room": "IDL",
    "lb_room": "LB",
    "cb_room": "CB",
    "s_room": "S",
}


def _load(p: Path) -> dict:
    if not p.exists():
        print(f"MISSING: {p.name} — skip")
        return {}
    return json.loads(p.read_text(encoding="utf-8"))


def _backup(p: Path):
    if p.exists():
        bak = p.with_suffix(".pre_research_merge_bak.json")
        shutil.copy2(p, bak)
        print(f"  backup -> {bak.name}")


def merge_roster_rooms(agents: dict, scheme_roster: dict) -> int:
    """Overwrite roster_needs from fresh post-FA room scores.
    Returns count of teams updated."""
    roster = scheme_roster.get("pillar2_roster_composition", {})
    updated = 0
    for tc, rooms in roster.items():
        if tc.startswith("_"): continue
        if tc not in agents: continue
        new_needs: dict[str, float] = {}
        for room_key, pos_code in ROOM_TO_POS.items():
            score = rooms.get(room_key)
            if score is None: continue
            w = ROOM_TO_WEIGHT.get(int(score), 0.0)
            if w > 0:
                new_needs[pos_code] = w
        # Preserve any existing need the fresh data didn't speak to (rare)
        for k, v in (agents[tc].get("roster_needs") or {}).items():
            if k not in new_needs and float(v) >= 2.0:
                new_needs[k] = float(v) * 0.7  # slight damp — older data
        agents[tc]["roster_needs"] = dict(
            sorted(new_needs.items(), key=lambda kv: -kv[1]))
        # Also stash the raw room scores for auditing
        agents[tc]["_roster_rooms_4_20_26"] = {
            k: v for k, v in rooms.items() if not k.startswith("_")
        }
        updated += 1
    return updated


def merge_scheme_tags(agents: dict, scheme_roster: dict) -> int:
    """Enrich team scheme profile with OC/DC archetype tags."""
    tax = scheme_roster.get("pillar1_scheme_taxonomy", {})
    updated = 0
    for tc, sch in tax.items():
        if tc.startswith("_"): continue
        if tc not in agents: continue
        agents[tc]["scheme_archetype_tags"] = {
            "oc": sch.get("oc_scheme", {}),
            "dc": sch.get("dc_scheme", {}),
        }
        updated += 1
    return updated


def merge_coach_gm_tendencies(agents: dict, supp: dict) -> int:
    """Annotate coach/GM tendencies from supplementary_intel."""
    tend = supp.get("coach_gm_tendencies", {}) or {}
    updated = 0
    for tc, ten in tend.items():
        if tc not in agents: continue
        # Keep existing hc/gm names, augment with research
        existing = agents[tc].get("coach_gm_research", {})
        existing.update(ten)
        agents[tc]["coach_gm_research"] = existing
        updated += 1
    return updated


def merge_prospect_reasoning(archs: dict, big_board: dict) -> int:
    """Fold big-board reasoning archetype_tags into prospect archetypes."""
    pros_reason = big_board.get("prospect_reasoning", {}) or {}
    updated = 0
    for name, r in pros_reason.items():
        # Extract tag signal
        tags_from_board = []
        tags_from_board.extend(r.get("archetype_tags") or [])
        tags_from_board.extend(r.get("strengths") or [])
        tags_from_board.extend(r.get("scheme_fits") or [])
        if not tags_from_board: continue
        # Normalize: lowercase, replace spaces with underscores
        norm = [t.strip().lower().replace(" ", "_").replace("-", "_")
                for t in tags_from_board if isinstance(t, str) and t.strip()]
        if name not in archs:
            archs[name] = {"tags": [], "_source": "big_board_reasoning"}
        existing = set(archs[name].get("tags") or [])
        merged = list(existing | set(norm))
        archs[name]["tags"] = merged
        archs[name]["_board_mention_count"] = r.get("analyst_board_mentions", 1)
        updated += 1
    return updated


def main():
    print("=== Research merge (4/20/26, T-3 days to draft) ===\n")

    # Load all
    agents = _load(TEAM_AGENTS)
    archs = _load(PROSPECT_ARCH)
    scheme_roster = _load(SCHEME_ROSTER)
    supp = _load(SUPP_INTEL)
    big_board = _load(BIG_BOARD)

    if not agents or not scheme_roster:
        raise SystemExit("Missing critical inputs.")

    # Backup
    _backup(TEAM_AGENTS)
    _backup(PROSPECT_ARCH)

    # Merge roster rooms (HIGHEST IMPACT)
    n = merge_roster_rooms(agents, scheme_roster)
    print(f"  roster_needs refreshed: {n} teams")

    # Scheme tags
    n = merge_scheme_tags(agents, scheme_roster)
    print(f"  scheme_archetype_tags added: {n} teams")

    # Coach/GM tendencies
    n = merge_coach_gm_tendencies(agents, supp)
    print(f"  coach_gm_research annotated: {n} teams")

    # Prospect archetype enrichment
    n = merge_prospect_reasoning(archs, big_board)
    print(f"  prospect archetype tags enriched: {n} prospects")

    # Write
    TEAM_AGENTS.write_text(json.dumps(agents, indent=2, ensure_ascii=False),
                            encoding="utf-8")
    PROSPECT_ARCH.write_text(json.dumps(archs, indent=2, ensure_ascii=False),
                              encoding="utf-8")
    print(f"\nWrote: {TEAM_AGENTS.name}")
    print(f"Wrote: {PROSPECT_ARCH.name}")


if __name__ == "__main__":
    main()
