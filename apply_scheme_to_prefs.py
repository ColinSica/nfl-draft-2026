"""Fold scheme_archetype_tags (OC/DC archetype strings) into
team_archetype_preferences_2026.json as normalized tags.

This makes scheme-fit a first-class archetype signal that the existing
_arch_score in team_fit.py will pick up automatically.
"""
from __future__ import annotations
import json, re
from pathlib import Path

ROOT = Path(__file__).parent
FEAT = ROOT / "data" / "features"

TEAM_AGENTS = FEAT / "team_agents_2026.json"
TEAM_PREFS = FEAT / "team_archetype_preferences_2026.json"

def _tokens(text: str) -> list[str]:
    """Extract tokenized archetype signals from an archetype sentence.
    'athletic zone-blockers, lean OTs, mobile G/C'
      -> ['athletic','zone_blocker','lean_ot','mobile_g','mobile_c']
    """
    if not isinstance(text, str) or not text.strip():
        return []
    # Lowercase, split on comma/semicolon/slash/&
    txt = text.lower().replace("/", " ").replace("&", " ")
    parts = re.split(r"[,;]", txt)
    toks = []
    for p in parts:
        p = p.strip()
        if not p: continue
        # Normalize
        n = re.sub(r"[^a-z0-9 ]", "", p)
        n = n.strip().replace(" ", "_")
        if n and len(n) > 2:
            toks.append(n)
        # Also split multi-word into individual tokens
        for w in p.split():
            w = re.sub(r"[^a-z0-9]", "", w).strip()
            if len(w) > 3 and w not in {"with", "the", "and", "plus"}:
                toks.append(w)
    return list(set(toks))


agents = json.loads(TEAM_AGENTS.read_text(encoding="utf-8"))
prefs = json.loads(TEAM_PREFS.read_text(encoding="utf-8")) if TEAM_PREFS.exists() else {}

n_updated = 0
for tc, team in agents.items():
    if not isinstance(team, dict) or tc.startswith("_"): continue
    sch = team.get("scheme_archetype_tags") or {}
    if not sch: continue
    prefs.setdefault(tc, {})
    # OC side
    oc = sch.get("oc", {}) or {}
    for fld, txt in oc.items():
        for tok in _tokens(txt):
            # Weight: 1.8 for scheme tags (slightly stronger than archetype)
            prefs[tc][tok] = max(float(prefs[tc].get(tok, 0.0)), 1.8)
    # DC side
    dc = sch.get("dc", {}) or {}
    for fld, txt in dc.items():
        for tok in _tokens(txt):
            prefs[tc][tok] = max(float(prefs[tc].get(tok, 0.0)), 1.8)
    n_updated += 1

TEAM_PREFS.write_text(json.dumps(prefs, indent=2, ensure_ascii=False),
                     encoding="utf-8")
print(f"Scheme-derived archetype prefs merged for {n_updated} teams.")
total_tags = sum(len(v) for v in prefs.values() if isinstance(v, dict))
print(f"Total pref entries now: {total_tags}")
