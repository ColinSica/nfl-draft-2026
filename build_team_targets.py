"""
Per-team readout: what is the model actually considering for each club?

Outputs TEAM_TARGETS.md, one section per team:
- pick slot(s), GM, HC, record / win-now pressure, QB situation
- scored roster needs + scheme premium + latent
- trade-up / trade-down probability
- gm_affinity (positional biases learned from 2023-2025 draft history)
- top confirmed pre-draft visits
- top 8 prospects by landing probability in R1 (from monte_carlo_2026_v12.csv,
  most_likely_team == this team), with positions and mean landing pick
- modal Stage-2 pick + top factors (from model_reasoning_2026.json)
"""
import json
from collections import defaultdict
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).parent

agents = json.loads((ROOT / "data/features/team_agents_2026.json").read_text(encoding="utf-8"))
reasoning = json.loads((ROOT / "data/processed/model_reasoning_2026.json").read_text(encoding="utf-8"))
mc = pd.read_csv(ROOT / "data/processed/monte_carlo_2026_v12.csv")
pred = pd.read_csv(ROOT / "data/processed/predictions_2026.csv")

# Map pick slot -> modal (team, player, position, factors)
pick_to_team_modal = {int(k): v for k, v in reasoning["picks"].items()}

# Group MC landings by most_likely_team (R1 only — pick_slot 1..32)
mc_r1 = mc[mc["pick_slot"].between(1, 32)].copy()
team_candidates = defaultdict(list)
for _, row in mc_r1.iterrows():
    team_candidates[row["most_likely_team"]].append({
        "player": row["player"],
        "position": row["position"],
        "school": row["college"],
        "prob": row["probability"],
        "mean_pick": row["mean_landing_pick"],
        "n_landings": row["n_r1_landings"],
        "pick_slot": row["pick_slot"],
    })
for t in team_candidates:
    team_candidates[t].sort(key=lambda r: -r["prob"])

# --- Write the report ---
out = ROOT / "TEAM_TARGETS.md"
fh = out.open("w", encoding="utf-8")
fh.write("# 2026 NFL Draft — Per-Team Target Readout\n\n")
fh.write("**Draft dates:** April 23–25, 2026 (Pittsburgh, PA)\n\n")
fh.write("Generated from Monte Carlo v12 (500 sims) + model reasoning.\n")
fh.write(f"- Source: `monte_carlo_2026_v12.csv` ({len(mc_r1)} R1 landings), "
         f"`model_reasoning_2026.json`, `team_agents_2026.json`\n")
fh.write("- `prob` = fraction of 500 sims in which the player was that team's R1 pick\n")
fh.write("- `trade_down_prob` / `trade_up_prob` = PDF-tier from analyst consensus\n")
fh.write("- \"(NEW)\" flag = 2026-cycle hire only. 2025 hires are not labeled NEW.\n\n")

# Sort teams by their first R1 pick slot (teams with no R1 at the end, alphabetical)
def sort_key(team):
    a = agents[team]
    picks = a.get("all_r1_picks") or []
    return (min(picks) if picks else 999, team)

_team_keys = [k for k in agents.keys() if not k.startswith("_")]
for team in sorted(_team_keys, key=sort_key):
    a = agents[team]
    picks = a.get("all_r1_picks") or []
    r1_str = ", ".join(str(p) for p in picks) if picks else "— (no R1)"

    fh.write(f"\n---\n\n## {team} — Pick {r1_str}\n\n")

    # Pick provenance (two-firsts / trade context)
    prov = (a.get("narrative", {}) or {}).get("pick_provenance", {}) or {}
    if prov:
        for pk in sorted(prov.keys(), key=lambda x: int(x) if str(x).isdigit() else 999):
            fh.write(f"- **Pick {pk}:** {prov[pk]}\n")
        fh.write("\n")

    # Front office
    fh.write(f"**Front office:** GM {a.get('gm','?')}"
             + (" (NEW)" if a.get("new_gm") else "")
             + f" · HC {a.get('hc','?')}"
             + (" (NEW)" if a.get("new_hc") else "")
             + "\n\n")

    # Situation
    import math as _math
    wp = a.get("win_pct", 0)
    try:
        wp_f = float(wp)
        if _math.isnan(wp_f):
            wp_str = "n/a"
        else:
            wp_str = f"{wp_f:.3f}"
    except (TypeError, ValueError):
        wp_str = "n/a"
    fh.write(f"**Situation:** {wp_str} win% · "
             f"win-now pressure {a.get('win_now_pressure',0):.2f} · "
             f"QB {a.get('qb_situation','?')} (urgency {a.get('qb_urgency',0):.2f})\n\n")

    # Cap + scheme
    cap = a.get("cap_context", {}) or {}
    sch = a.get("scheme", {}) or {}
    cap_space = cap.get("cap_space_m")
    dead = cap.get("dead_cap_m")
    tier = cap.get("constraint_tier", "normal")
    if cap_space is not None or dead is not None:
        parts = []
        if cap_space is not None:
            parts.append(f"${cap_space}M space")
        parts.append(f"tier `{tier}`")
        if dead is not None:
            parts.append(f"dead ${dead}M")
        fh.write(f"**Cap:** " + " · ".join(parts) + "\n\n")
    elif tier and tier != "normal":
        fh.write(f"**Cap:** tier `{tier}` (no dollar figures available)\n\n")
    fh.write(f"**Scheme:** {sch.get('type','?')} · "
             f"premium positions: {', '.join(sch.get('premium',[])) or '—'}\n\n")

    # Needs
    needs = a.get("roster_needs", {}) or {}
    latent = a.get("latent_needs", {}) or {}
    needs_sorted = sorted(needs.items(), key=lambda kv: -kv[1])
    fh.write("**Scored roster needs** (higher = more urgent):\n\n")
    if needs_sorted:
        fh.write("| Pos | Score |\n|---|---|\n")
        for pos, sc in needs_sorted:
            fh.write(f"| {pos} | {sc} |\n")
    else:
        fh.write("_none specified_\n")
    if latent:
        fh.write(f"\n**Latent / future needs:** "
                 + ", ".join(f"{k} ({v})" for k, v in latent.items()) + "\n")
    fh.write(f"\n**Needs source:** `{a.get('needs_source','?')}`\n\n")

    # GM affinity (positional biases)
    aff = a.get("gm_affinity", {}) or {}
    if aff:
        num_aff = [(k, float(v)) for k, v in aff.items()
                   if isinstance(v, (int, float)) or
                   (isinstance(v, str) and v.replace('-','').replace('.','').isdigit())]
        if num_aff:
            top_aff = sorted(num_aff, key=lambda kv: -kv[1])[:3]
            bot_aff = sorted(num_aff, key=lambda kv:  kv[1])[:3]
            fh.write("**GM positional affinity** (from 2023-2025 draft history):\n\n")
            fh.write("- Favors: " + ", ".join(f"{k} {v:+.2f}" for k, v in top_aff) + "\n")
            fh.write("- Avoids: " + ", ".join(f"{k} {v:+.2f}" for k, v in bot_aff) + "\n\n")

    # Trade behavior
    tb = a.get("trade_behavior", {}) or {}
    pdf = tb.get("pdf_tier", {}) or {}
    tb_parts = []
    if "trade_up_rate" in tb:
        tb_parts.append(f"trade_up_rate={tb['trade_up_rate']:.2f}")
    if "trade_down_rate" in tb:
        tb_parts.append(f"trade_down_rate={tb['trade_down_rate']:.2f}")
    if pdf:
        for k, v in pdf.items():
            tb_parts.append(f"{k}={v}")
    fh.write("**Trade behavior:** " + (", ".join(tb_parts) if tb_parts else "—") + "\n\n")

    # Predictability
    fh.write(f"**Predictability:** {a.get('predictability','?')} · "
             f"Capital: {a.get('draft_capital',{}).get('capital_abundance','?')} "
             f"({a.get('total_picks','?')} picks total)\n\n")

    # Visits
    vs = a.get("visit_signals", {}) or {}
    conf = vs.get("confirmed_visits", []) or []
    if conf:
        fh.write(f"**Confirmed visits ({len(conf)}):** "
                 + ", ".join(conf) + "\n\n")

    # Age cliffs (future-need trigger)
    cliffs = (a.get("roster_context", {}) or {}).get("age_cliffs", []) or []
    if cliffs:
        fh.write("**Age cliffs (starters aging out):**\n\n")
        for c in cliffs[:6]:
            fh.write(f"- {c.get('player','?')} ({c.get('position','?')}), "
                     f"age {c.get('age_2026','?')} — severity {c.get('severity','?')}\n")
        fh.write("\n")

    # Previous-year allocation
    prev = (a.get("roster_context", {}) or {}).get("previous_year_allocation", {}) or {}
    if prev:
        parts = []
        for yr in ("2024_r1", "2024_r2", "2025_r1", "2025_r2"):
            picks_y = prev.get(yr, [])
            if picks_y:
                parts.append(f"{yr}: " + ", ".join(
                    f"{p.get('pos','?')} {p.get('player','')} (#{p.get('pick','')})"
                    for p in picks_y
                ))
        if parts:
            fh.write("**Recent draft history:** " + " · ".join(parts) + "\n\n")

    # Scripted/modal pick from model reasoning
    fh.write("### Modal R1 pick(s) from 500-sim MC\n\n")
    modal_written = False
    for p in picks:
        r = pick_to_team_modal.get(int(p))
        if not r:
            continue
        modal_written = True
        c = r.get("components", {}) or {}
        fh.write(f"**Pick {p}** — modal player: **{r.get('player','?')}** "
                 f"({r.get('position','?')})\n\n")
        fh.write(f"- Components: "
                 f"bpa={c.get('bpa','?')}, need={c.get('need','?')}, "
                 f"visit={c.get('visit','?')}, intel={c.get('intel','?')}, "
                 f"pv_mult={c.get('pv_mult','?')}, gm_aff={c.get('gm_affinity','?')}, "
                 f"**final={c.get('score_final','?')}**\n")
        tf = r.get("top_factors", []) or []
        if tf:
            fh.write("- Top reasons:\n")
            for f in tf:
                fh.write(f"  - **{f.get('label','?')}** ({f.get('key','?')}, "
                         f"magnitude {f.get('magnitude',0):.2f}): "
                         f"{f.get('detail','')}\n")
        fh.write("\n")
    if not modal_written and not picks:
        fh.write("_No R1 pick; Stage 2 sim operates in R1 only. "
                 "Day-2 targets not modeled here._\n\n")

    # Top 8 MC-landing candidates where this team is most_likely_team
    cands = team_candidates.get(team, [])
    fh.write("### Top prospects whose most-likely R1 landing = this team\n\n")
    if cands:
        fh.write("| Player | Pos | School | Pick | P(landing) | Mean pick |\n")
        fh.write("|---|---|---|---|---|---|\n")
        for r in cands[:8]:
            fh.write(f"| {r['player']} | {r['position']} | {r['school']} | "
                     f"{r['pick_slot']} | {r['prob']:.3f} | {r['mean_pick']:.2f} |\n")
    else:
        fh.write("_No R1 picks attributed to this team in the 500-sim MC._\n")
    fh.write("\n")

    # Narrative summary
    narr = a.get("narrative", {}) or {}
    if narr.get("player_archetypes"):
        fh.write("### Analyst/scout archetype notes\n\n")
        for pk, txt in narr["player_archetypes"].items():
            fh.write(f"- **Pick {pk}:** {txt}\n")
        fh.write("\n")
    if narr.get("roster_needs_tiered"):
        fh.write(f"**Needs (tiered, from team-profile PDF):**\n\n"
                 f"{narr['roster_needs_tiered']}\n\n")
    if narr.get("gm_fingerprint"):
        fh.write(f"**GM fingerprint:** {narr['gm_fingerprint']}\n\n")
    if narr.get("uncertainty_flags"):
        fh.write(f"**Uncertainty flags:** {narr['uncertainty_flags']}\n\n")
    if narr.get("roster_depth_note"):
        fh.write(f"**Roster depth note:** {narr['roster_depth_note']}\n\n")
    if narr.get("hunter_usage_note"):
        fh.write(f"**Hunter (WR/CB) usage note:** {narr['hunter_usage_note']}\n\n")
    if narr.get("context_2026"):
        fh.write(f"**2026 context:** {narr['context_2026']}\n\n")

fh.close()
print(f"Wrote {out} ({out.stat().st_size/1024:.1f} KB, "
      f"{len(open(out,encoding='utf-8').readlines())} lines)")
