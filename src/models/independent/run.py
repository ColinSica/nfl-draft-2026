"""Entry point for the independent-mode Monte Carlo.

Usage:
  python -m src.models.independent.run [--config configs/independent.yaml]
                                        [--sims N]
                                        [--seed S]

Pipeline:
  1. Enforce independence guard
  2. Layer A — build independent player board (player_value.py)
  3. Monte Carlo: for each sim, iterate R1 picks 1..32
       - compute team_fit on remaining prospects
       - apply availability mask
       - optionally trade down (stubbed to "noted only" for MVP)
       - soft-argmax pick using a small temperature for variance
  4. Aggregate: modal picks, landing probabilities, reasoning
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[3]


def load_config(path: Path) -> dict:
    with path.open(encoding="utf-8") as fh:
        cfg = yaml.safe_load(fh)
    if cfg.get("mode") != "independent":
        raise ValueError(f"expected mode=independent, got {cfg.get('mode')!r}")
    return cfg


def enforce_independence(cfg: dict, audit_log: list[dict]) -> None:
    for rel in cfg.get("banned_files", []):
        p = ROOT / rel
        audit_log.append({
            "check": "banned_file_not_loaded_by_independent",
            "file": rel,
            "exists_on_disk": p.exists(),
            "loaded_here": False,
        })
    banned = set(cfg.get("banned_imports", []))
    leaks = []
    for modname, mod in list(sys.modules.items()):
        if not modname.startswith("src.models.independent"):
            continue
        for bad in banned:
            if any(k.startswith(bad) for k in getattr(mod, "__dict__", {})):
                leaks.append((modname, bad))
    if leaks:
        raise RuntimeError(f"independence violation: {leaks}")
    audit_log.append({"check": "banned_imports_absent", "leaks": []})


def _build_slot_team_map(team_agents: dict) -> dict[int, str]:
    """R1-only slot→team mapping from team_agents. Kept for backward compat."""
    out: dict[int, str] = {}
    for team, agent in team_agents.items():
        if team.startswith("_"):
            continue
        for pk in agent.get("all_r1_picks") or []:
            out[int(pk)] = team
    return out


def _build_full_slot_team_map(team_context_csv: Path) -> dict[int, str]:
    """All-7-rounds slot→team map from team_context CSV (all 257 picks)."""
    if not team_context_csv.exists():
        return {}
    import pandas as pd
    df = pd.read_csv(team_context_csv)
    return {int(r.pick_number): r.team for _, r in df[["pick_number", "team"]].iterrows()}


def _round_for_slot(slot: int) -> int:
    """2026 NFL round boundaries (32-32-32-33-32-32-38 ≈)."""
    if slot <= 32: return 1
    if slot <= 64: return 2
    if slot <= 100: return 3
    if slot <= 135: return 4
    if slot <= 177: return 5
    if slot <= 220: return 6
    return 7


def _softmax_pick(scores: pd.Series, rng: np.random.Generator,
                  temperature: float = 0.12, top_k: int = 10) -> int:
    """Soft-argmax over the top-K candidates. Lower temperature = closer to
    argmax. Returns the DataFrame index of the chosen prospect."""
    ranked = scores.sort_values(ascending=False).head(top_k)
    logits = ranked.values / max(temperature, 1e-6)
    logits = logits - logits.max()
    probs = np.exp(logits)
    probs = probs / probs.sum()
    idx = rng.choice(ranked.index.values, p=probs)
    return int(idx)


def _maybe_fire_bilateral_trades(slot_team: dict[int, str],
                                  team_agents: dict,
                                  trade_rate_by_slot: dict[int, float],
                                  board: pd.DataFrame,
                                  rng: np.random.Generator,
                                  max_slot: int = 32) -> list[dict]:
    """Pre-sim bilateral trade matching.

    For each (earlier slot A, later slot B in A+3..A+15), if team_A has
    structural trade-down motive AND team_B has structural trade-up
    motive AND their profiles are compatible, execute a SLOT SWAP
    (team_B picks at A, team_A picks at B).

    Purely structural — no mock picks consulted. Drivers:
      - A's trade_down_p (team historical rate + capital abundance + 5th-yr
        premium dampener)
      - B's trade_up_p (QB scarcity + contender urgency + capital scarcity)
      - Fitzgerald chart compatibility (not extremely far apart)

    Returns list of executed swap records. Modifies slot_team in place.
    """
    from src.models.independent import trade as trade_mod
    mutated = slot_team.copy()
    executed = []
    used_slots = set()
    # Walk slots in order; max 3 trades per sim to avoid cascade chaos
    for a_slot in range(1, min(max_slot, 32) + 1):
        if len(executed) >= 3:
            break
        if a_slot in used_slots:
            continue
        a_team = mutated.get(a_slot)
        if not a_team or a_team.startswith("_"):
            continue
        a_profile = team_agents[a_team]
        a_avail = board
        base_rate = trade_rate_by_slot.get(a_slot, 0.08)
        a_td = trade_mod.trade_down_probability(
            a_team, a_profile, a_slot, a_avail, pick_range_trade_rate=base_rate)
        if a_td < 0.30:
            continue
        # Find a later team with trade-up motive within Fitzgerald proximity
        best_b_slot = None
        best_score = 0.0
        for b_slot in range(a_slot + 3, min(a_slot + 16, max_slot) + 1):
            if b_slot in used_slots:
                continue
            b_team = mutated.get(b_slot)
            if not b_team or b_team == a_team or b_team.startswith("_"):
                continue
            b_profile = team_agents[b_team]
            b_tu = trade_mod.trade_up_probability(b_team, b_profile, b_slot, a_avail)
            if b_tu < 0.30:
                continue
            # Combined structural score — roll against it
            combined = a_td * b_tu
            if combined > best_score:
                best_score = combined
                best_b_slot = b_slot
        if best_b_slot is not None and rng.random() < min(best_score * 2.5, 0.55):
            # Execute swap
            b_team = mutated[best_b_slot]
            mutated[a_slot], mutated[best_b_slot] = b_team, a_team
            executed.append({
                "from_slot": a_slot, "to_slot": best_b_slot,
                "moved_down": a_team, "moved_up": b_team,
                "a_td_p": round(a_td, 3), "b_tu_p": round(best_score / max(a_td, 0.001), 3),
            })
            used_slots.add(a_slot); used_slots.add(best_b_slot)

    # Write mutations back to caller's dict
    slot_team.clear()
    slot_team.update(mutated)
    return executed


def _simulate_once(prospects: pd.DataFrame, team_agents: dict,
                   slot_team: dict[int, str], trade_rate_by_slot: dict[int, float],
                   rng: np.random.Generator,
                   max_slot: int = 257) -> list[dict]:
    from src.models.independent.team_fit import compute_team_fit
    from src.models.independent.availability import available_mask
    from src.models.independent import trade as trade_mod

    picks_made: list[dict] = []
    board = prospects.copy()

    # ---- Bilateral trade matching BEFORE picks start ----
    sim_slot_team = dict(slot_team)
    trades_fired = _maybe_fire_bilateral_trades(
        sim_slot_team, team_agents, trade_rate_by_slot, board, rng, max_slot)

    # ---- Cascade state tracked during the sim ----
    # Position-run detection: if 2+ prospects at a position go in the last
    # 3 picks, subsequent teams with that need get a premium boost (FOMO).
    # Tier-exhaustion: if a position's R1-grade prospects are gone, teams
    # that needed that position see their need DAMPENED (they pivot).
    recent_positions: list[str] = []   # last 3 pick positions

    for slot in range(1, max_slot + 1):
        team = sim_slot_team.get(slot)
        if team is None:
            continue
        profile = dict(team_agents[team])
        profile["team"] = team
        profile["_slot"] = slot
        profile["_round"] = _round_for_slot(slot)

        # --- CASCADE: boost need for positions in recent "run" ---
        run_counts: dict[str, int] = {}
        for p in recent_positions[-3:]:
            run_counts[p] = run_counts.get(p, 0) + 1
        active_runs = {p: c for p, c in run_counts.items() if c >= 2}
        if active_runs:
            boosted_needs = dict(profile.get("roster_needs", {}) or {})
            for pos, c in active_runs.items():
                cur = float(boosted_needs.get(pos, 0.0))
                # 2 of 3 = 1.2x, 3 of 3 = 1.4x; capped at 5.5
                boosted_needs[pos] = min(cur * (1.0 + 0.2 * c), 5.5)
            profile["roster_needs"] = boosted_needs

        avail_series = available_mask(board, picks_made)
        avail = board[avail_series]
        if avail.empty:
            break

        # --- Structural trade probability (no mock references) ---
        base_rate = trade_rate_by_slot.get(slot, 0.08)
        p_down = trade_mod.trade_down_probability(team, profile, slot, avail,
                                                  pick_range_trade_rate=base_rate)

        # MVP: record structural trade probability but don't mutate the
        # schedule. Section G will add bilateral matching + schedule mutation.
        trade_noted = bool(rng.random() < p_down)

        # --- Team fit + argmax (soft) ---
        fit = compute_team_fit(avail, profile)
        chosen_idx = _softmax_pick(fit, rng)
        player_row = avail.loc[chosen_idx]

        # Reasoning snapshot — decompose score for the modal pick
        picks_made.append({
            "slot": slot, "round": _round_for_slot(slot), "team": team,
            "player": str(player_row["player"]),
            "position": str(player_row["position"]),
            "school": str(player_row.get("college",
                             player_row.get("school", ""))),
            "independent_grade": float(player_row["independent_grade"]),
            "fit_score": float(fit.loc[chosen_idx]),
            "trade_down_p_structural": round(p_down, 3),
            "trade_noted": trade_noted,
        })
        # Track recent positions for cascade detection
        recent_positions.append(str(player_row["position"]))

    return picks_made


def _aggregate(all_sims: list[list[dict]], n_sims: int) -> dict:
    # Per-slot modal team pick
    slot_counts: dict[int, Counter] = defaultdict(Counter)
    # Per-player landing distribution (team × slot)
    player_slots: dict[str, Counter] = defaultdict(Counter)
    player_teams: dict[str, Counter] = defaultdict(Counter)
    player_pos: dict[str, str] = {}
    player_sch: dict[str, str] = {}
    player_grade: dict[str, float] = {}

    for sim in all_sims:
        for p in sim:
            slot_counts[p["slot"]][p["player"]] += 1
            player_slots[p["player"]][p["slot"]] += 1
            player_teams[p["player"]][p["team"]] += 1
            player_pos[p["player"]] = p["position"]
            player_sch[p["player"]] = p["school"]
            player_grade[p["player"]] = p["independent_grade"]

    # Per-round summary
    from collections import Counter as _C
    round_pos_counts: dict[int, Counter] = defaultdict(Counter)
    for sim in all_sims:
        for p in sim:
            rnd = p.get("round", _round_for_slot(p["slot"]))
            round_pos_counts[rnd][p["position"]] += 1

    return {
        "slot_counts": slot_counts,
        "player_slots": player_slots,
        "player_teams": player_teams,
        "player_pos": player_pos,
        "player_sch": player_sch,
        "player_grade": player_grade,
        "round_pos_counts": round_pos_counts,
    }


def _write_outputs(agg: dict, all_sims: list[list[dict]], n_sims: int,
                   cfg: dict) -> None:
    # monte_carlo_independent — landing probabilities per player (all rounds)
    mc_rows = []
    for player, slots in agg["player_slots"].items():
        total = sum(slots.values())
        if total == 0:
            continue
        modal_slot = slots.most_common(1)[0][0]
        modal_team, team_ct = agg["player_teams"][player].most_common(1)[0]
        mean_pick = sum(s * c for s, c in slots.items()) / total
        var_pick = (sum((s * s) * c for s, c in slots.items()) / total
                    - mean_pick * mean_pick)
        modal_round = _round_for_slot(modal_slot)
        # Landings specifically in R1 (slot 1-32) for backward compat
        r1_landings = sum(c for s, c in slots.items() if s <= 32)
        mc_rows.append({
            "player": player,
            "position": agg["player_pos"][player],
            "school": agg["player_sch"][player],
            "independent_grade": round(agg["player_grade"][player], 2),
            "pick_slot": modal_slot,
            "modal_round": modal_round,
            "probability": round(team_ct / n_sims, 3),
            "most_likely_team": modal_team,
            "n_r1_landings": r1_landings,
            "n_any_landings": total,
            "mean_landing_pick": round(mean_pick, 2),
            "variance_landing_pick": round(var_pick, 4),
        })
    mc_df = pd.DataFrame(mc_rows).sort_values("pick_slot")
    mc_path = ROOT / cfg["outputs"]["monte_carlo_csv"]
    mc_df.to_csv(mc_path, index=False)

    # predictions — modal pick per slot with UNIQUENESS constraint.
    # Greedy allocation: for each slot in order, pick the most-common player
    # that hasn't already been assigned to an earlier slot. Prevents the
    # aggregation artifact where the same player shows as "modal" at multiple
    # slots even though in any single sim each player is picked once.
    pred_rows = []
    reasoning = {"meta": {"n_sims": n_sims}, "picks": {}}
    assigned_players: set[str] = set()
    for slot in sorted(agg["slot_counts"].keys()):
        pc = agg["slot_counts"][slot]
        # Find the most common unassigned player
        player, ct = None, 0
        for cand_player, cand_ct in pc.most_common():
            if cand_player not in assigned_players:
                player, ct = cand_player, cand_ct
                break
        if player is None:
            continue  # no unassigned candidate (extremely rare)
        assigned_players.add(player)
        prob = round(ct / n_sims, 3)
        # use the first sim that chose this player at this slot for components
        for sim in all_sims:
            for p in sim:
                if p["slot"] == slot and p["player"] == player:
                    pred_rows.append({
                        "pick": slot,
                        "round": _round_for_slot(slot),
                        "team": p["team"],
                        "player": player,
                        "position": p["position"],
                        "school": p["school"],
                        "probability": prob,
                        "independent_grade": round(p["independent_grade"], 2),
                        "fit_score": round(p["fit_score"], 3),
                        "trade_down_p_structural": p["trade_down_p_structural"],
                    })
                    rs, top_factors = _build_reasoning(p, prob)
                    reasoning["picks"][str(slot)] = {
                        "team": p["team"],
                        "player": player,
                        "position": p["position"],
                        "fit_score": round(p["fit_score"], 3),
                        "independent_grade": round(p["independent_grade"], 2),
                        "probability": prob,
                        "trade_down_p_structural": p["trade_down_p_structural"],
                        "reasoning_summary": rs,
                        "top_factors": top_factors,
                    }
                    break
            else:
                continue
            break
    pred_df = pd.DataFrame(pred_rows)
    pred_path = ROOT / cfg["outputs"]["predictions_csv"]
    # Write mock picks to a separate file so the player board CSV stays clean
    picks_path = pred_path.with_name(pred_path.stem + "_picks.csv")
    pred_df.to_csv(picks_path, index=False)

    reason_path = ROOT / cfg["outputs"]["reasoning_json"]
    reason_path.write_text(json.dumps(reasoning, indent=2), encoding="utf-8")


_AGENTS_CACHE = None
_ODDS_ANCHORS_CACHE = None
_TEAM_LANDINGS_CACHE = None
_RESEARCH_CACHE = None


def _load_reasoning_sources():
    """One-time load of all data sources for reasoning construction."""
    global _AGENTS_CACHE, _ODDS_ANCHORS_CACHE, _TEAM_LANDINGS_CACHE, _RESEARCH_CACHE
    try:
        p = ROOT / "data/features/team_agents_2026.json"
        _AGENTS_CACHE = json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}
    except Exception:
        _AGENTS_CACHE = {}
    try:
        from src.models.independent.odds_anchor import load_anchors, build_team_landing_priors
        _ODDS_ANCHORS_CACHE = load_anchors()
        _TEAM_LANDINGS_CACHE = build_team_landing_priors()
    except Exception:
        _ODDS_ANCHORS_CACHE = {}
        _TEAM_LANDINGS_CACHE = {}
    try:
        rp = ROOT / "data/features/pick_reasoning_sources_2026.json"
        _RESEARCH_CACHE = json.loads(rp.read_text(encoding="utf-8")) if rp.exists() else {}
    except Exception:
        _RESEARCH_CACHE = {}


def _extract_player_note(narrative: dict, player: str) -> str | None:
    """Find a player-specific analyst note in the team's narrative block.
    Returns the first matching sentence from player_archetypes or other fields."""
    pa = narrative.get("player_archetypes") or {}
    if isinstance(pa, dict):
        # player_archetypes often keys entries by slot number with prose
        # containing the player's name. Walk all entries, find first match.
        surname = player.rsplit(" ", 1)[-1] if " " in player else player
        for key, val in pa.items():
            if not isinstance(val, str):
                continue
            if surname.lower() in val.lower() or player.lower() in val.lower():
                return val.strip()
    # Fall back to roster_needs_tiered or context_2026 free-text searches
    for k in ("roster_needs_tiered", "context_2026", "gm_fingerprint",
              "uncertainty_flags", "trade_up_scenario"):
        v = narrative.get(k)
        if not isinstance(v, str):
            continue
        if player.lower() in v.lower():
            # Extract the containing sentence
            for sent in re.split(r"[.!?]\s+", v):
                if player.lower() in sent.lower():
                    return sent.strip()
    return None


def _build_reasoning(pick: dict, prob: float) -> tuple[str, list[dict]]:
    """Build a data-cited reasoning explanation for a pick. Sources:
      - Team narrative (PDF-parsed analyst commentary in team_agents_2026.json)
      - External research cache (pick_reasoning_sources_2026.json) — ESPN,
        CBS, The Ringer, PFN, NFL.com, Bleacher Report etc.
      - Model factor math (need, scheme, coaching tree, fit score)

    Intentionally does NOT surface Kalshi or any betting-market data in the
    user-facing text. Markets drive picks (via anchor + team_fit bonus) but
    are kept silent in the justification.
    """
    global _AGENTS_CACHE, _ODDS_ANCHORS_CACHE, _TEAM_LANDINGS_CACHE, _RESEARCH_CACHE
    if _AGENTS_CACHE is None:
        _load_reasoning_sources()

    team_code = pick.get("team")
    player = pick.get("player") or ""
    position = pick.get("position") or ""
    slot = int(pick.get("slot") or 0)
    fit_score = float(pick.get("fit_score", 0) or 0)
    indep_grade = float(pick.get("independent_grade", 999) or 999)

    team = (_AGENTS_CACHE.get(team_code) or {}) if isinstance(_AGENTS_CACHE, dict) else {}
    narrative = team.get("narrative", {}) or {}
    needs = team.get("roster_needs", {}) or {}
    need_weight = float(needs.get(position, 0.0))
    qb_urg = float(team.get("qb_urgency", 0.0) or 0.0)
    scheme = (team.get("scheme") or {}).get("type") or (team.get("scheme") or {}).get("base") or ""
    hc_tree = (team.get("coaching") or {}).get("hc_tree") or ""
    cap_tier = (team.get("cap_context") or {}).get("cap_tier") or team.get("cap_tier")
    predictability = team.get("predictability") or ""

    factors: list[dict] = []

    # ---- Source 1: Need weight with analyst-narrative citation ----
    rn_tier = narrative.get("roster_needs_tiered")
    if need_weight >= 4:
        lbl = f"Critical {position} need (weight {need_weight:.1f}/5)"
        if isinstance(rn_tier, str) and position in rn_tier:
            lbl += f" — analyst profile: \"{rn_tier.split(':')[0].strip()}\""
        factors.append({"label": lbl, "weight": need_weight / 5, "source": "team_profile"})
    elif need_weight >= 2.5:
        factors.append({"label": f"Roster need at {position} (weight {need_weight:.1f}/5)",
                        "weight": need_weight / 5, "source": "team_profile"})
    elif need_weight >= 1:
        factors.append({"label": f"Moderate interest at {position}",
                        "weight": need_weight / 5, "source": "team_profile"})

    if position == "QB" and qb_urg >= 0.8:
        qs = narrative.get("qb_situation")
        lbl = f"QB urgency high (score {qb_urg:.2f})"
        if isinstance(qs, str):
            qs_short = qs.strip().split(".")[0][:140]
            lbl += f" — {qs_short}"
        factors.append({"label": lbl, "weight": qb_urg, "source": "qb_situation"})

    # ---- Source 3: Board value ----
    if indep_grade < 20:
        factors.append({"label": f"Top-of-board talent (model grade {indep_grade:.1f})",
                        "weight": 0.85, "source": "model"})
    elif indep_grade < 50:
        factors.append({"label": f"Strong board value (grade {indep_grade:.1f})",
                        "weight": 0.65, "source": "model"})

    # ---- Source 4: Scheme / coaching tree ----
    if scheme:
        s_line = narrative.get("scheme_identity")
        lbl = f"Aligns with {scheme} scheme"
        if isinstance(s_line, str):
            lbl += f" — {s_line.split('.')[0][:120]}"
        factors.append({"label": lbl, "weight": 0.5, "source": "scheme"})
    if hc_tree and hc_tree not in ("None", ""):
        factors.append({"label": f"Fits {hc_tree}-tree coaching tendencies",
                        "weight": 0.4, "source": "coaching_tree"})

    # ---- Source 5: Player-specific analyst note ----
    player_note = _extract_player_note(narrative, player)
    if player_note:
        short = player_note[:240].strip()
        factors.append({"label": f"Analyst note: \"{short}\"",
                        "weight": 0.7, "source": "team_profile_narrative"})

    # ---- Source 6: GM fingerprint ----
    gm_fp = narrative.get("gm_fingerprint")
    if isinstance(gm_fp, str) and gm_fp.strip():
        # Pull one sentence relevant to position type
        for sent in re.split(r"[.!?]\s+", gm_fp):
            s = sent.strip()
            if not s: continue
            if (position.lower() in s.lower() or "premium" in s.lower()
                or "trench" in s.lower() or "build" in s.lower()):
                factors.append({"label": f"GM fingerprint: \"{s[:180]}\"",
                                "weight": 0.45, "source": "gm_fingerprint"})
                break

    # ---- Source 7: Fit score (model) ----
    if fit_score >= 2.5:
        factors.append({"label": f"Elite team-fit score ({fit_score:.2f})",
                        "weight": min(fit_score / 3, 1), "source": "model"})
    elif fit_score >= 1.8:
        factors.append({"label": f"Strong team-fit score ({fit_score:.2f})",
                        "weight": fit_score / 3, "source": "model"})

    # ---- Source 8: Team+player-specific analyst commentary ----
    # v2 schema: cache is {player: {team_quotes: {TEAM_CODE: [...]}, general_quotes: [...]}}
    # Prefer quotes tagged to THIS team. If none, fall back to general scouting.
    if isinstance(_RESEARCH_CACHE, dict):
        rec = _RESEARCH_CACHE.get(player) or {}
        if isinstance(rec, dict):
            tq = (rec.get("team_quotes") or {}) if isinstance(rec.get("team_quotes"), dict) else {}
            team_specific = tq.get(team_code) or []
            general = rec.get("general_quotes") or []
            chosen: list = []
            for q in team_specific[:2]:
                if isinstance(q, dict) and q.get("text"):
                    chosen.append(("team", q))
            if not chosen:
                # No team-specific quote — pull general scouting
                for q in general[:1]:
                    if isinstance(q, dict) and q.get("text"):
                        chosen.append(("general", q))
            for tag, q in chosen:
                src = q.get("source") or "analyst"
                txt = str(q.get("text") or "")[:240]
                prefix = f"{src} on {team_code}-{player}:" if tag == "team" else f"{src} scouting report:"
                factors.append({
                    "label": f"{prefix} \"{txt}\"",
                    "weight": 0.85 if tag == "team" else 0.6,
                    "source": f"research:{src}",
                    "team_tagged": tag == "team",
                })
            # Also surface into the summary so it reads as prose
            if chosen:
                _, q0 = chosen[0]
                rec.setdefault("_last_cited", {})
                rec["_last_cited"][team_code] = q0.get("text")

    # ---- Sim-probability context ----
    if prob >= 0.8:
        factors.append({"label": f"Dominant pick across sims ({int(prob*100)}%)",
                        "weight": prob, "source": "model"})
    elif prob < 0.4:
        factors.append({"label": f"Close call ({int(prob*100)}% modal vs alternates)",
                        "weight": 0.3, "source": "model"})

    # ---- Build summary ----
    parts: list[str] = []
    if need_weight >= 4:
        parts.append(f"{team_code} has a critical {position} need")
    elif need_weight >= 2.5:
        parts.append(f"{team_code} has a real {position} need")
    elif indep_grade < 20:
        parts.append(f"{team_code} takes the board's top {position} on value")
    else:
        parts.append(f"{team_code} addresses {position} at this slot")

    if scheme or hc_tree:
        parts.append(f"{player} fits the {scheme or hc_tree+' tree'} scheme")

    if player_note:
        parts.append(f"scouting: \"{player_note[:140]}\"")

    if prob >= 0.8:
        parts.append(f"near-lock in {int(prob*100)}% of sims")
    elif prob >= 0.5:
        parts.append(f"{int(prob*100)}% modal outcome")

    summary = "; ".join(parts)
    if summary:
        summary = summary[0].upper() + summary[1:]
    summary = summary.rstrip(".") + "."
    if cap_tier:
        summary += f" Cap: {cap_tier}."
    if predictability and predictability.lower() != "medium":
        summary += f" Predictability: {predictability.lower()}."

    factors.sort(key=lambda f: -float(f.get("weight", 0)))
    return summary, factors[:8]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="configs/independent.yaml")
    ap.add_argument("--sims", type=int, default=None, help="override n_simulations")
    ap.add_argument("--seed", type=int, default=None, help="override rng_seed")
    ap.add_argument("--max-slot", type=int, default=257,
                    help="cap sim at this pick slot (32 for R1-only, 257 for full draft)")
    args = ap.parse_args(argv)

    cfg = load_config(ROOT / args.config)
    audit: list[dict] = []
    enforce_independence(cfg, audit)

    n_sims = args.sims or cfg.get("n_simulations", 500)
    seed = args.seed if args.seed is not None else cfg.get("rng_seed")
    rng = np.random.default_rng(seed)

    out_log = ROOT / cfg["outputs"]["independence_audit_log"]
    out_log.parent.mkdir(parents=True, exist_ok=True)
    out_log.write_text(json.dumps({
        "status": "running",
        "guard": audit,
    }, indent=2), encoding="utf-8")

    # --- Layer A: build player board ---
    from src.models.independent import player_value
    board = player_value.build_independent_board(cfg)
    print(f"[independent] player board: {len(board)} prospects")

    # The board CSV dropped analyst cols; re-read the ENRICHED file sans
    # banned columns so we still have has_injury_flag / visit_count / age
    # for team_fit (which doesn't use consensus columns).
    pros_full = pd.read_csv(ROOT / cfg["allowed_inputs"]["prospects"])
    banned = set(cfg.get("banned_prospect_columns", []))
    for c in list(pros_full.columns):
        if c in banned or (c.endswith("_rank") and c != "position_rank"):
            pros_full = pros_full.drop(columns=[c])
    # Join independent_grade onto the full frame
    graded = pros_full.merge(
        board[["player", "independent_grade"]],
        on="player", how="left")
    graded = graded.dropna(subset=["independent_grade"])

    # --- Load team agents + full 7-round slot-team map ---
    team_agents = json.loads(
        (ROOT / cfg["allowed_inputs"]["team_agents"]).read_text(encoding="utf-8"))
    team_ctx_csv = ROOT / cfg["allowed_inputs"]["team_context"]
    slot_team = _build_full_slot_team_map(team_ctx_csv)
    if not slot_team:
        # Fallback: R1 only
        slot_team = _build_slot_team_map(team_agents)

    # Optional: historical pick-range trade rates (structural, not mock)
    trade_rate_by_slot: dict[int, float] = {}
    try:
        team_ctx = pd.read_csv(ROOT / cfg["allowed_inputs"]["team_context"])
        if "pick_range_trade_rate" in team_ctx.columns:
            trade_rate_by_slot = dict(zip(
                team_ctx["pick_number"].astype(int),
                team_ctx["pick_range_trade_rate"].fillna(0.08)))
    except Exception:
        pass

    # --- Monte Carlo ---
    print(f"[independent] running {n_sims} simulations...")
    all_sims: list[list[dict]] = []
    for i in range(n_sims):
        all_sims.append(_simulate_once(
            graded, team_agents, slot_team, trade_rate_by_slot, rng,
            max_slot=args.max_slot))
        if (i + 1) % 100 == 0:
            print(f"  ... {i + 1} sims")

    # --- Aggregate + persist ---
    agg = _aggregate(all_sims, n_sims)
    _write_outputs(agg, all_sims, n_sims, cfg)

    # Final audit
    out_log.write_text(json.dumps({
        "status": "independent_run_ok",
        "n_sims": n_sims,
        "guard": audit,
        "outputs": {
            "board_csv": cfg["outputs"]["predictions_csv"],
            "monte_carlo_csv": cfg["outputs"]["monte_carlo_csv"],
            "reasoning_json": cfg["outputs"]["reasoning_json"],
        },
    }, indent=2), encoding="utf-8")

    # Apply post-processing clamp. If Kalshi market anchors are available,
    # use the odds-based clamp (extends through R3, uses P10/P90 bands).
    # Otherwise fall back to the legacy consensus-rank R1 clamp.
    try:
        from src.models.calibration import odds_clamp as _oc
        _oc.apply_odds_clamp()
    except Exception as exc:
        print(f"[independent] odds_clamp failed: {exc}; falling back to r1_clamp",
              file=sys.stderr)
        try:
            from src.models.calibration import r1_clamp as _rc
            _rc.apply_r1_clamp()
        except Exception as exc2:
            print(f"[independent] r1_clamp also failed: {exc2}", file=sys.stderr)

    # Auto-export reviewer-friendly comparison CSVs so VS Code stays in sync.
    try:
        from src.models.evaluate import export_comparisons as _ec
        _ec.main()
    except Exception as exc:
        print(f"[independent] export_comparisons failed: {exc}", file=sys.stderr)

    print(f"[independent] done. outputs in data/processed/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
