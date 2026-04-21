"""Extract structured reasoning signals from team narratives + analyst content.

Output: data/features/team_reasoning_signals_2026.json

Each entry is a tagged signal ABOUT a team, not a pick FOR a team. The
independent engine can read this file to apply modest team-fit bonuses
without ever consuming "analyst X picks player Y at slot Z" type data.

Signal schema:
{
  team: str,
  reason_type: str,     # see REASON_TYPES
  subtype: str | None,
  strength: float,      # 0..1
  source_count: int,    # how many independent statements support this
  source_quality: str,  # 'explicit' (direct narrative), 'inferred', 'extracted'
  recency_weight: float,# decay for older evidence; 1.0 = current
  source_date: str,     # YYYY-MM-DD
  position: str | None, # when the signal is position-specific
  raw_excerpt: str,     # short quote from source
}
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
AGENTS_PATH = ROOT / "data/features/team_agents_2026.json"
OUT_PATH = ROOT / "data/features/team_reasoning_signals_2026.json"

REASON_TYPES = {
    "positional_need",          # team needs X position
    "latent_need",              # future cliff at X
    "scheme_fit_premium",       # X position is scheme-premium
    "trade_up_likelihood",
    "trade_down_likelihood",
    "gm_tendency_affinity",     # GM historically favors position
    "gm_tendency_aversion",     # GM historically avoids position
    "coaching_preference",      # HC tree or college connection
    "medical_concern",
    "visit_signal",
    "roster_timeline",          # win-now / rebuild
    "premium_position_preference",
    "new_regime_uncertainty",   # new GM / new HC
    "rebuild_signal",
    "win_now_signal",
    "cap_constraint",
}


def _signal(team, reason_type, *, strength, source_quality="explicit",
            subtype=None, source_count=1, position=None,
            raw_excerpt="", recency=1.0,
            source_date="2026-04-19"):
    return {
        "team": team,
        "reason_type": reason_type,
        "subtype": subtype,
        "strength": float(strength),
        "source_count": int(source_count),
        "source_quality": source_quality,
        "recency_weight": float(recency),
        "source_date": source_date,
        "position": position,
        "raw_excerpt": raw_excerpt[:240],
    }


def extract_from_agent(team: str, agent: dict) -> list[dict]:
    """Each agent JSON already has 90% of the structured reasoning we
    need — this function just re-emits it in the flat tag schema above."""
    out = []
    narr = agent.get("narrative", {}) or {}

    # Positional needs (continuous)
    for pos, weight in (agent.get("roster_needs") or {}).items():
        try:
            w = float(weight)
        except (TypeError, ValueError):
            continue
        strength = min(1.0, max(0.0, w / 5.0))
        out.append(_signal(team, "positional_need", strength=strength,
                          position=pos, source_quality="explicit",
                          raw_excerpt=f"roster_needs[{pos}]={w}"))

    # Latent needs
    for pos, weight in (agent.get("latent_needs") or {}).items():
        try:
            w = float(weight)
        except (TypeError, ValueError):
            continue
        out.append(_signal(team, "latent_need", strength=min(1.0, w / 5.0),
                          position=pos, source_quality="explicit",
                          raw_excerpt=f"latent_needs[{pos}]={w}"))

    # Scheme-premium positions
    for pos in (agent.get("scheme", {}) or {}).get("premium", []):
        out.append(_signal(team, "scheme_fit_premium", strength=0.6,
                          position=pos, source_quality="explicit",
                          raw_excerpt=f"scheme.premium includes {pos}"))

    # Trade tendencies (structural)
    tb = agent.get("trade_behavior", {}) or {}
    up = tb.get("trade_up_rate")
    if up is not None:
        out.append(_signal(team, "trade_up_likelihood", strength=float(up),
                          source_quality="explicit",
                          raw_excerpt=f"trade_up_rate={up}"))
    down = tb.get("trade_down_rate")
    if down is not None:
        out.append(_signal(team, "trade_down_likelihood", strength=float(down),
                          source_quality="explicit",
                          raw_excerpt=f"trade_down_rate={down}"))
    pdf = tb.get("pdf_tier", {}) or {}
    for k, v in pdf.items():
        if "prob" in k and isinstance(v, (int, float)):
            kind = "trade_up_likelihood" if "up" in k else "trade_down_likelihood"
            out.append(_signal(team, kind, strength=float(v),
                              subtype="analyst_pdf_tier",
                              source_quality="extracted",
                              raw_excerpt=f"pdf_tier.{k}={v}"))

    # GM positional affinity — structural (real drafts)
    for pos, a in (agent.get("gm_affinity") or {}).items():
        try:
            af = float(a)
        except (TypeError, ValueError):
            continue
        if af > 0.05:
            out.append(_signal(team, "gm_tendency_affinity",
                              strength=min(1.0, abs(af) * 3),
                              position=pos, source_quality="explicit",
                              raw_excerpt=f"gm_affinity[{pos}]={af:+.2f}"))
        elif af < -0.05:
            out.append(_signal(team, "gm_tendency_aversion",
                              strength=min(1.0, abs(af) * 3),
                              position=pos, source_quality="explicit",
                              raw_excerpt=f"gm_affinity[{pos}]={af:+.2f}"))

    # Coaching — HC tree + college stints
    coaching = agent.get("coaching", {}) or {}
    tree = coaching.get("hc_tree")
    if tree:
        out.append(_signal(team, "coaching_preference", strength=0.5,
                          subtype=f"hc_tree:{tree}",
                          source_quality="explicit",
                          raw_excerpt=f"hc_tree={tree}"))
    for stint in coaching.get("hc_college_stints", []) or []:
        out.append(_signal(team, "coaching_preference", strength=0.4,
                          subtype=f"hc_college:{stint}",
                          source_quality="explicit",
                          raw_excerpt=f"hc stint at {stint}"))

    # Medical — injury flags mentioned in narrative
    for flag in (narr.get("injury_flags", []) or []):
        out.append(_signal(team, "medical_concern", strength=0.5,
                          subtype=flag.get("type") if isinstance(flag, dict) else None,
                          source_quality="extracted",
                          raw_excerpt=str(flag)[:200]))

    # Visits
    vs = agent.get("visit_signals", {}) or {}
    for name in (vs.get("confirmed_visits", []) or []):
        out.append(_signal(team, "visit_signal", strength=0.5,
                          subtype="confirmed",
                          source_quality="extracted",
                          raw_excerpt=f"confirmed visit: {name}"))

    # Roster timeline
    wn = agent.get("win_now_pressure")
    if wn is not None:
        wn = float(wn)
        out.append(_signal(team, "roster_timeline",
                          strength=wn,
                          subtype="win_now_pressure",
                          source_quality="explicit",
                          raw_excerpt=f"win_now_pressure={wn}"))
        if wn >= 0.8:
            out.append(_signal(team, "win_now_signal", strength=wn,
                              source_quality="explicit",
                              raw_excerpt=f"win_now_pressure={wn} (>=0.8)"))
        elif wn <= 0.3:
            out.append(_signal(team, "rebuild_signal", strength=1.0 - wn,
                              source_quality="explicit",
                              raw_excerpt=f"win_now_pressure={wn} (<=0.3)"))

    # Cap
    cap = agent.get("cap_context", {}) or {}
    tier = cap.get("constraint_tier")
    if tier and tier != "normal":
        out.append(_signal(team, "cap_constraint", strength=0.8,
                          subtype=tier,
                          source_quality="explicit",
                          raw_excerpt=f"cap tier={tier}, "
                                      f"space=${cap.get('cap_space_m')}M"))

    # New regime
    if agent.get("new_gm"):
        out.append(_signal(team, "new_regime_uncertainty", strength=0.6,
                          subtype="new_gm",
                          source_quality="explicit",
                          raw_excerpt="new_gm=true"))
    if agent.get("new_hc"):
        out.append(_signal(team, "new_regime_uncertainty", strength=0.5,
                          subtype="new_hc",
                          source_quality="explicit",
                          raw_excerpt="new_hc=true"))

    # Premium-position bias (if scheme premium is tight, signals strong bias)
    premium = (agent.get("scheme", {}) or {}).get("premium", [])
    if len(premium) <= 3 and premium:
        out.append(_signal(team, "premium_position_preference",
                          strength=0.7,
                          subtype=",".join(premium),
                          source_quality="inferred",
                          raw_excerpt=f"narrow scheme premium: {premium}"))

    return out


def main():
    agents = json.loads(AGENTS_PATH.read_text(encoding="utf-8"))
    all_signals = []
    for team, agent in agents.items():
        if team.startswith("_"):
            continue
        all_signals.extend(extract_from_agent(team, agent))

    # Group by team for easier consumption
    by_team = {}
    for s in all_signals:
        by_team.setdefault(s["team"], []).append(s)

    # By (team, reason_type) aggregate counts
    summary = {}
    for s in all_signals:
        key = (s["team"], s["reason_type"])
        summary.setdefault(key, 0)
        summary[key] += 1

    output = {
        "meta": {
            "generated_at": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
            "reason_types": sorted(list(REASON_TYPES)),
            "total_signals": len(all_signals),
            "teams_covered": len(by_team),
            "summary_counts": {f"{t}|{r}": c for (t, r), c in summary.items()},
        },
        "signals_by_team": by_team,
    }
    OUT_PATH.write_text(json.dumps(output, indent=2, ensure_ascii=False),
                       encoding="utf-8")
    print(f"Wrote {OUT_PATH} — {len(all_signals)} signals across {len(by_team)} teams")


if __name__ == "__main__":
    main()
