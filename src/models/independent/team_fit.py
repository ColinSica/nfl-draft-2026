"""Layer B — team-specific fit.

Given a player board (with `independent_grade` from player_value.py) and a
team's structural profile, return a fit score per prospect for THIS team.

Score = weighted sum of structural signals, then multiplied by GM affinity
and medical-tolerance, then dampened by a same-position-repeat penalty.

All inputs come from team_agents_2026.json — factual/structural only.

Components (per prospect):
  BPA        1 - independent_grade / 260        (grade-normalized quality)
  NEED       roster_needs[pos] / 5.0            (continuous, not a mask)
  LATENT     latent_needs[pos] / 10.0
  SCHEME     +0.15 if pos in scheme.premium
  SCARCITY   +0.08 if position is top-3 in its class by grade
  AGE_CLIFF  +0.10 per high-severity same-position cliff
  COLLEGE    +0.05 if prospect.college matches any hc_college_stints
  PRIOR_INV  -0.25 per R1 same-position in previous_year_allocation.2024_r1/2025_r1
  GM_MULT    clip(1 + gm_affinity[pos] * 3, 0.7, 1.3)
  INJ_MULT   team.medical_tolerance for has_injury_flag == 1 (default 0.95)

Nothing here reads analyst data or consensus ranks.
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

_ROOT = Path(__file__).resolve().parents[3]


def _load_archetypes() -> tuple[dict, dict]:
    """Cache archetype data at module import time."""
    p_path = _ROOT / "data/features/prospect_archetypes_2026.json"
    t_path = _ROOT / "data/features/team_archetype_preferences_2026.json"
    p_data, t_data = {}, {}
    if p_path.exists():
        p_data = json.loads(p_path.read_text(encoding="utf-8")).get("archetypes", {})
    if t_path.exists():
        t_data = json.loads(t_path.read_text(encoding="utf-8")).get("preferences", {})
    return p_data, t_data


_PROSPECT_ARCHETYPES, _TEAM_ARCHETYPE_PREFS = _load_archetypes()

def _reload_archetypes():
    """Force-reload archetype JSONs (called by sims after patches)."""
    global _PROSPECT_ARCHETYPES, _TEAM_ARCHETYPE_PREFS
    _PROSPECT_ARCHETYPES, _TEAM_ARCHETYPE_PREFS = _load_archetypes()

# Position-to-needs key canonicalization. The team_needs dict uses NFL
# position codes; the prospect dataframe uses similar but varies (OT vs T,
# IOL vs G/C, DL vs EDGE/IDL).
POS_ALIASES = {
    "T": "OT", "OT": "OT",
    "G": "IOL", "OG": "IOL", "C": "IOL", "IOL": "IOL", "OL": "IOL",
    "EDGE": "EDGE", "DE": "EDGE",
    "DT": "IDL", "NT": "IDL", "IDL": "IDL", "DL": "IDL",
    "OLB": "LB", "MLB": "LB", "ILB": "LB", "LB": "LB",
    "CB": "CB",
    "S": "S", "FS": "S", "SS": "S",
    "WR": "WR", "RB": "RB", "TE": "TE", "QB": "QB",
    "FB": "RB", "ATH": "WR", "LS": "IOL", "K": "K", "P": "P",
}

def _canon_pos(p: str) -> str:
    if not isinstance(p, str):
        return ""
    return POS_ALIASES.get(p.upper().strip(), p.upper().strip())


def _need_score(pos: str, team_profile: dict) -> float:
    needs = team_profile.get("roster_needs", {}) or {}
    base = float(needs.get(pos, 0.0)) / 5.0
    # QB is special: analyst 'needs' lists include QB when a team has a
    # long-term QB question even if they're not drafting one in Round 1
    # (e.g. CLE with Watson cap-locked, NYJ with Rodgers bridge, PIT
    # with Rodgers TBD). Scale QB need by qb_urgency so the model only
    # treats QB as R1-actionable when urgency is real.
    #   urgency >= 0.8 -> full need + additive boost
    #   urgency 0.5-0.8 -> full need, modest boost
    #   urgency < 0.5 -> need dampened proportionally
    if pos == "QB":
        urg = float(team_profile.get("qb_urgency", 0.0) or 0.0)
        qb_sit = (team_profile.get("qb_situation") or "").lower()
        # Dampen: base = base * (0.25 + 0.75 * urg) so urg=1 -> full, urg=0 -> 0.25x
        base = base * (0.25 + 0.75 * urg)
        # Still allow additive boost for explicit high-urgency teams
        if urg >= 0.6:
            base += 0.4 * urg
        # Hard penalty for teams with locked QB rooms (Dak, Dart, Lamar, etc.).
        # These teams virtually never take a QB in R1. Prior calibration
        # allowed a large-enough BPA weight to surface QBs for DAL/NYG/BAL
        # even with qb_urgency=0, which is unrealistic.
        if qb_sit == "locked" and urg < 0.1:
            base -= 2.5
    return base


def _latent_score(pos: str, team_profile: dict) -> float:
    latent = team_profile.get("latent_needs", {}) or {}
    return float(latent.get(pos, 0.0)) / 10.0


def _scheme_bonus(pos: str, team_profile: dict) -> float:
    sch = team_profile.get("scheme", {}) or {}
    premium = set(sch.get("premium", []) or [])
    if pos in premium:
        return 0.15
    # Allow aliases: OL premium matches both OT and IOL
    if "OL" in premium and pos in ("OT", "IOL"):
        return 0.15
    return 0.0


def _age_cliff_boost(pos: str, team_profile: dict) -> float:
    cliffs = ((team_profile.get("roster_context") or {})
              .get("age_cliffs", []) or [])
    boost = 0.0
    for c in cliffs:
        cpos = _canon_pos(c.get("position", ""))
        if cpos == pos:
            sev = (c.get("severity") or "medium").lower()
            boost += 0.10 if sev == "high" else 0.05
    return min(boost, 0.25)


def _college_connection(prospect_school: str, team_profile: dict) -> float:
    if not isinstance(prospect_school, str):
        return 0.0
    stints = ((team_profile.get("coaching") or {})
              .get("hc_college_stints", []) or [])
    if not stints:
        return 0.0
    sch = prospect_school.lower()
    for stint in stints:
        s = stint.lower() if isinstance(stint, str) else ""
        if s and (s in sch or sch in s):
            return 0.05
    return 0.0


def _prior_investment_penalty(pos: str, team_profile: dict) -> float:
    prev = ((team_profile.get("roster_context") or {})
            .get("previous_year_allocation", {}) or {})
    penalty = 0.0
    for k in ("2024_r1", "2025_r1"):
        for entry in prev.get(k, []) or []:
            if _canon_pos(entry.get("pos", "")) == pos:
                penalty += 0.25
    return min(penalty, 0.50)


def _gm_multiplier(pos: str, team_profile: dict) -> float:
    aff = team_profile.get("gm_affinity", {}) or {}
    raw = aff.get(pos, 0.0)
    try:
        raw = float(raw)
    except (TypeError, ValueError):
        raw = 0.0
    return max(0.70, min(1.30, 1.0 + raw * 3.0))


# Coaching-tree positional premium — per Agent 5's 2020-2025 backtest,
# specific coaching trees draft particular positions at much higher rates
# than average. Expressed as a per-position multiplier on fit score.
_COACHING_TREE_POS_PREMIUM = {
    "shanahan":        {"OT": 1.15, "IOL": 1.12, "TE": 1.10, "DL": 1.18, "IDL": 1.18},
    "shanahan_kubiak": {"OT": 1.15, "IOL": 1.12, "TE": 1.10, "DL": 1.18, "IDL": 1.18},
    "kubiak":          {"OT": 1.15, "IOL": 1.12, "TE": 1.10, "DL": 1.18, "IDL": 1.18},
    "harbaugh":        {"CB": 1.15, "S": 1.15, "OT": 1.12, "IOL": 1.12, "EDGE": 1.10},
    "belichick":       {"IOL": 1.12, "LB": 1.12, "S": 1.08, "CB": 1.05},
    "payton":          {"TE": 1.18, "RB": 1.10, "WR": 1.08},
    "reid":            {"WR": 1.10, "TE": 1.08, "OT": 1.08},
    "mcdermott":       {"EDGE": 1.08, "CB": 1.08},
    "mcvay":           {"OT": 1.10, "WR": 1.10, "IOL": 1.08},
    "sirianni":        {"EDGE": 1.10, "OT": 1.08},
    "dan_campbell":    {"EDGE": 1.10, "OT": 1.10, "LB": 1.08},
    "49ers_dc":        {"EDGE": 1.18, "DL": 1.15, "IDL": 1.15, "CB": 1.10},
    "saints":          {"EDGE": 1.12, "OT": 1.12, "RB": 1.08, "TE": 1.10},
    "falcons":         {"EDGE": 1.15, "CB": 1.12, "S": 1.08},
    "cowboys":         {"WR": 1.10, "OT": 1.12, "EDGE": 1.08},
    "mccarthy_west_coast": {"WR": 1.12, "OT": 1.12, "TE": 1.10},
    "ohio_state":      {"CB": 1.15, "S": 1.12, "LB": 1.10, "WR": 1.08},
    "west_coast":      {"WR": 1.12, "OT": 1.10, "TE": 1.10},
}


def _coaching_tree_mult(pos: str, team_profile: dict) -> float:
    tree = ((team_profile.get("coaching") or {}).get("hc_tree") or "").lower()
    if not tree: return 1.0
    prem = _COACHING_TREE_POS_PREMIUM.get(tree, {})
    return float(prem.get(pos, 1.0))


def _injury_multiplier(row: pd.Series, team_profile: dict) -> float:
    flag = int(row.get("has_injury_flag", 0) or 0)
    if not flag:
        return 1.0
    # medical_tolerance is a future field; default to mild penalty.
    tol = float(team_profile.get("medical_tolerance", 0.95))
    return max(0.75, min(1.05, tol))


def _build_position_lookups(team_profile: dict) -> dict[str, float]:
    """Precompute per-position scalar contributions so compute_team_fit can
    vectorize with series.map(dict) instead of Python apply."""
    positions = {"QB", "WR", "RB", "TE", "OT", "IOL", "EDGE", "IDL",
                 "LB", "CB", "S", "K", "P"}
    team_code = team_profile.get("team") or ""
    reasoning_boost = _reasoning_position_boost(team_code)
    need = {p: _need_score(p, team_profile) + reasoning_boost.get(p, 0.0)
            for p in positions}
    latent = {p: _latent_score(p, team_profile) for p in positions}
    scheme = {p: _scheme_bonus(p, team_profile) for p in positions}
    age_cliff = {p: _age_cliff_boost(p, team_profile) for p in positions}
    prior = {p: _prior_investment_penalty(p, team_profile) for p in positions}
    gm_mult = {p: _gm_multiplier(p, team_profile) for p in positions}
    # Cap-tier multiplier on need (not on raw BPA — we still want good
    # players regardless of cap, just de-prioritize expensive positions
    # when cap is tight).
    cap_mult = {p: _cap_constraint_mult(p, team_profile) for p in positions}
    # Coaching tree positional premium (Agent 5 backtest: tree patterns)
    coach_mult = {p: _coaching_tree_mult(p, team_profile) for p in positions}
    return {
        "need": need, "latent": latent, "scheme": scheme,
        "age_cliff": age_cliff, "prior": prior, "gm_mult": gm_mult,
        "cap_mult": cap_mult, "coach_mult": coach_mult,
    }


def compute_team_fit(prospects: pd.DataFrame,
                     team_profile: dict) -> pd.Series:
    """Return a fit score per prospect for this team.

    prospects must contain at minimum: position, college (or school),
    independent_grade, has_injury_flag.
    """
    # Canonical position — vectorized via map(dict)
    pos_canon = prospects["position"].fillna("").astype(str).str.upper().map(
        lambda s: POS_ALIASES.get(s.strip(), s.strip()))
    # Flex position (hybrids) — e.g. Reese LB with EDGE flex, Styles LB with S flex.
    # When present, take MAX of the primary and flex need scores so teams with
    # high flex-position need can reach for hybrid prospects.
    if "position_flex" in prospects.columns:
        pos_flex = prospects["position_flex"].fillna("").astype(str).str.upper().map(
            lambda s: POS_ALIASES.get(s.strip(), s.strip()) if s.strip() else "")
    else:
        pos_flex = pd.Series("", index=prospects.index)
    lookups = _build_position_lookups(team_profile)

    grade = pd.to_numeric(prospects["independent_grade"],
                          errors="coerce").fillna(260.0)
    bpa = (1.0 - (grade / 260.0)).clip(lower=0.0, upper=1.0)

    def _max_with_flex(lookup_dict, damp=1.0):
        primary = pos_canon.map(lookup_dict).fillna(0.0)
        flex = pos_flex.map(lookup_dict).fillna(0.0) * damp
        return pd.concat([primary, flex], axis=1).max(axis=1)

    need      = _max_with_flex(lookups["need"])
    latent    = _max_with_flex(lookups["latent"])
    scheme    = _max_with_flex(lookups["scheme"])
    age_cliff = pos_canon.map(lookups["age_cliff"]).fillna(0.0)
    prior     = pos_canon.map(lookups["prior"]).fillna(0.0)
    # Multipliers: for hybrid prospects, take MAX of primary-pos and flex-pos
    # GM affinity + coaching tree should credit the flex role too.
    def _max_mult(lookup_dict):
        primary = pos_canon.map(lookup_dict).fillna(1.0)
        flex = pos_flex.map(lookup_dict).fillna(1.0)
        # Only replace primary if the prospect has a flex AND the flex multiplier is higher
        has_flex = pos_flex != ""
        return primary.where(~has_flex, pd.concat([primary, flex], axis=1).max(axis=1))
    gm_mult   = _max_mult(lookups["gm_mult"])
    coach_mult = _max_mult(lookups["coach_mult"])
    cap_mult  = pos_canon.map(lookups["cap_mult"]).fillna(1.0)
    need = need * cap_mult

    # College connection — vectorized over the stints list once.
    school_col = "college" if "college" in prospects.columns else "school"
    stints = ((team_profile.get("coaching") or {})
              .get("hc_college_stints", []) or [])
    if stints:
        school_lower = prospects[school_col].fillna("").astype(str).str.lower()
        college_bonus = pd.Series(0.0, index=prospects.index)
        for s in stints:
            if not isinstance(s, str) or not s:
                continue
            s_low = s.lower()
            match = school_lower.str.contains(s_low, na=False, regex=False)
            college_bonus = college_bonus.where(~match, 0.05)
    else:
        college_bonus = pd.Series(0.0, index=prospects.index)

    # Position scarcity — vectorized top-3 per position
    pos_rank = prospects.groupby(pos_canon)["independent_grade"].rank(method="min")
    scarcity = (pos_rank <= 3).astype(float) * 0.08

    # Per-team visit signal — cached per team to keep hot path O(N).
    team_code = team_profile.get("team") or ""
    visit_map = _visit_bonus_map(team_code, team_profile)
    if visit_map and "player" in prospects.columns:
        visit_bonus = prospects["player"].map(visit_map).fillna(0.0)
    else:
        visit_bonus = pd.Series(0.0, index=prospects.index)

    # Narrative-mentioned specific prospects — cached per (team, player)
    # so this stays O(N) in the sim hot path.
    narr_bonus_map = _narrative_bonus_map(team_profile)
    if narr_bonus_map and "player" in prospects.columns:
        narr_bonus = prospects["player"].map(narr_bonus_map).fillna(0.0)
    else:
        narr_bonus = pd.Series(0.0, index=prospects.index)

    # Archetype fit (Section F + reasoning-driven prefs from apply_reasoning_driven_fits.py).
    # Now STRONGER: each matched archetype × team preference weight contributes
    # 0.22 (up from 0.10), capped at 0.50 total (up from 0.20). This makes
    # reasoning-derived team preferences a first-class driver of picks, not
    # a tiebreaker. Rationale per user: narratives/reasoning need to actually
    # impact model picks, not be decorative.
    team_code = team_profile.get("team")
    team_prefs = _TEAM_ARCHETYPE_PREFS.get(team_code, {}) or {}
    # Refresh cache each call in case we updated the JSON (cheap — module-level)
    if team_prefs and "player" in prospects.columns:
        def _arch_score(player_name: str) -> float:
            tags = _PROSPECT_ARCHETYPES.get(player_name, [])
            if not tags:
                return 0.0
            total = 0.0
            for t in tags:
                total += team_prefs.get(t, 0.0)
            return min(0.32, total * 0.13)
        archetype_bonus = prospects["player"].map(_arch_score).fillna(0.0)
    else:
        archetype_bonus = pd.Series(0.0, index=prospects.index)

    # Tiered medical (Section F — recalibrated 4/23):
    #
    # The `has_injury_flag` column is ON for ~80% of top prospects (any college
    # injury history counts), so penalizing it uniformly hands a baseline
    # advantage to the one or two prospects with perfectly clean records.
    # Prior calibration had inj_mult=0.95 for has_injury_flag=1, which was
    # enough to flip first-OT from Mauigoa (flag=1, rank 5) to Fano (flag=0,
    # rank 21) — even though every analyst has Mauigoa as OT1.
    #
    # New calibration:
    #   - Generic has_injury_flag: 0.99 (barely a signal; most top prospects have it)
    #   - Specific severe flags (ACL/spine/shoulder): meaningful penalty
    #   - News-flagged concerns (via _meta_medical_flags_2026 with severity set):
    #     applied in player_value.py as a grade delta, not here
    med_tol = float(team_profile.get("medical_tolerance", 0.99))
    med_tol = max(0.85, min(1.05, med_tol))
    inj_generic = pd.to_numeric(prospects.get("has_injury_flag", 0),
                                errors="coerce").fillna(0)
    acl = pd.to_numeric(prospects.get("acl_flag", 0), errors="coerce").fillna(0)
    spine = pd.to_numeric(prospects.get("spine_flag", 0), errors="coerce").fillna(0)
    shoulder = pd.to_numeric(prospects.get("shoulder_flag", 0),
                             errors="coerce").fillna(0)
    # Start at 1.0. Generic flag: near-neutral. Specific severe injury: real penalty.
    inj_mult = pd.Series(1.0, index=prospects.index)
    inj_mult = inj_mult.where(inj_generic == 0, med_tol)          # 0.99 — tiny
    inj_mult = inj_mult.where(acl == 0, 0.88)                      # ACL: -12%
    inj_mult = inj_mult.where(spine == 0, 0.82)                    # spine: -18%
    inj_mult = inj_mult.where(shoulder == 0, inj_mult * 0.96)      # shoulder: -4%
    inj_mult = inj_mult.clip(lower=0.60, upper=1.05)

    # Round-specific need/BPA weighting:
    #  R1   — 0.75 need, 1.25 BPA (per user: elite talent can't be passed up
    #         even without a specific need — consensus-top prospects go early
    #         regardless of fit)
    #  R2-3 — 0.70 need, 1.10 BPA (BPA starts winning)
    #  R4-5 — 0.50 need, 1.20 BPA (fliers, developmental)
    #  R6-7 — 0.35 need, 1.30 BPA (pure upside swings)
    round_num = team_profile.get("_round", 1)
    if round_num == 1:
        need_w, bpa_w = 0.75, 1.25
    elif round_num in (2, 3):
        need_w, bpa_w = 0.70, 1.10
    elif round_num in (4, 5):
        need_w, bpa_w = 0.50, 1.20
    else:
        need_w, bpa_w = 0.35, 1.30

    need_total = need + latent + scheme + age_cliff - prior
    base = (bpa_w * bpa
            + need_w * need_total
            + college_bonus + scarcity + archetype_bonus
            + visit_bonus + narr_bonus)

    # Kalshi team-landing bonus. Gated at 3% above uniform noise floor.
    # Weight raised so a clear market favourite (e.g. Tate-WAS at 15%)
    # beats the team's own need/coaching-tree bias for a different player.
    team_code = team_profile.get("team") or ""
    if team_code and _TEAM_LANDING_PRIORS and "player" in prospects.columns:
        def _landing(player_name: str) -> float:
            probs = _TEAM_LANDING_PRIORS.get(player_name, {}) or {}
            return max(0.0, probs.get(team_code, 0.0) - 0.03)
        landing_raw = prospects["player"].map(_landing).fillna(0.0)
        # Weight 5.0 → 15% market landing (Tate-WAS) = +0.60 fit bonus;
        #               30% landing = +1.35.
        market_landing_bonus = landing_raw * 5.0
    else:
        market_landing_bonus = pd.Series(0.0, index=prospects.index)

    # Kalshi pick-slot bonus — PEAKS at P50, not flat across P10-P90.
    #
    # Previous behaviour (flat band) let a prospect whose P50 is 21 and
    # P10 is 7 get the full bonus at slot 7 — equal to a prospect whose
    # P50 *is* 7. That's how Faulk (P50≈21) was stealing WAS's #7 pick
    # from Tate (P50=7, Tate-WAS market landing 15%).
    #
    # New curve:
    #   - Triangular peak at P50 with asymmetric falloff toward P10/P90.
    #   - Bonus at P10/P90 edge ≈ 0.2; bonus at P50 ≈ 1.0. Scales by conf.
    #   - Outside the band: stronger penalty than before so the model
    #     doesn't let prospects "reach" far from their market.
    slot = team_profile.get("_slot") or 0
    if slot and _PICK_ANCHORS and "player" in prospects.columns:
        def _slot_match(player_name: str) -> float:
            a = _PICK_ANCHORS.get(player_name)
            if not a or not a.get("anchor"):
                return 0.0
            anchor = a["anchor"]  # expected_pick for bimodal; P50 for symmetric
            p10, p90 = a["p10"], a["p90"]
            if anchor <= 0:
                return 0.0
            conf = max(0.2, a.get("conf", 0.5))

            # Fixed tolerance band around anchor: bonus peaks at anchor,
            # falls to 0 at ±15 slots, penalizes beyond. This replaces the
            # old P10-P90 band logic which was meaningless for right-tail
            # prospects (P90=150+ allowed any pick without penalty).
            dist = abs(slot - anchor)
            if dist <= 15:
                # Triangular bonus: 1.0 at anchor, 0 at ±15.
                return conf * (1.0 - dist / 15.0) * 0.8
            # Beyond 15 slots from anchor: real penalty, scaled by distance.
            # 20 slots off = -0.5*conf; 40 off = -1.2*conf; capped at -1.5.
            excess = dist - 15
            return -conf * min(1.5, 0.3 + excess * 0.04)
        slot_bonus_raw = prospects["player"].map(_slot_match).fillna(0.0)
        # Weight 2.2 → conf=1.0 P50-exact match gives +2.2 fit;
        #               band-edge match gives +0.44; out-of-band up to -2.2.
        # Strong enough that a clear P50-match beats a P10-edge-reach even
        # when the reach candidate has strong need/coaching-tree bonuses.
        market_slot_bonus = slot_bonus_raw * 2.2
    else:
        market_slot_bonus = pd.Series(0.0, index=prospects.index)

    # Apply multiplicative team-specific biases (gm_mult, coach_mult,
    # inj_mult) to the TEAM-FIT base ONLY — not to market bonuses. This
    # prevents a team's scheme/coach premium for one position from scaling
    # the market bonus for another position (which was letting WAS's CB-
    # coaching-tree multiplier suppress Tate's market-implied advantage at
    # slot 7). Market signals remain absolute, and additive.
    needy_scaled = base * gm_mult * coach_mult * inj_mult
    return needy_scaled + market_landing_bonus + market_slot_bonus


_NARRATIVE_NAME_CACHE: dict = {}
_NARRATIVE_BONUS_CACHE: dict = {}
_VISIT_BONUS_CACHE: dict = {}


def _load_visit_spread() -> dict[str, int]:
    """{player -> n_teams_that_visited}. Used to dampen shared visits."""
    import json as _json
    p = _ROOT / "data/features/team_agents_2026.json"
    if not p.exists():
        return {}
    data = _json.loads(p.read_text(encoding="utf-8"))
    return (data.get("_meta_visit_spread_2026", {}) or {}).get(
        "per_player_visit_count", {})


_VISIT_SPREAD = _load_visit_spread()


def _load_pff_lookup() -> dict[str, float]:
    """{player -> PFF grade} for R1-eligibility gating."""
    import pandas as _pd
    p = _ROOT / "data/processed/prospects_2026_enriched.csv"
    if not p.exists():
        return {}
    df = _pd.read_csv(p, usecols=["player", "pff_grade_3yr"])
    return {r.player: float(r.pff_grade_3yr)
            for _, r in df.iterrows()
            if _pd.notna(r.pff_grade_3yr)}


_PFF_LOOKUP = _load_pff_lookup()


def _load_reasoning_signals() -> dict:
    """Load analyst reasoning signals extracted in Section E. These are
    per-team structured tags like 'positional_need', 'archetype_fit',
    'premium_position_preference'. Used as a small need-boost supplement
    (not a pick driver)."""
    import json as _json
    p = _ROOT / "data/features/team_reasoning_signals_2026.json"
    if not p.exists():
        return {}
    return _json.loads(p.read_text(encoding="utf-8")).get(
        "signals_by_team", {})


_REASONING_SIGNALS = _load_reasoning_signals()


def _load_team_landing_priors() -> dict:
    """{player: {team: prob, ...}} — market-implied team landing probabilities
    from Kalshi draft markets. Loaded once at import; refreshed via reload()."""
    try:
        from src.models.independent.odds_anchor import build_team_landing_priors
        priors = build_team_landing_priors()
    except Exception as exc:
        print(f"[team_fit] market team-landing load failed: {exc}")
        return {}
    # Flatten to {player: {team: prob}} for hot-path lookup
    out: dict[str, dict[str, float]] = {}
    for p, d in priors.items():
        out[p] = dict(d.get("team_probs") or {})
    return out


def _load_pick_anchors() -> dict:
    """{player: {p10, p50, p90, expected_pick, anchor}} — market-implied pick-position
    CDF per player. `anchor` = expected_pick for right-tail bimodal CDFs (Simpson,
    Beck, etc.) or P50 for symmetric ones. Used to reward slot-aligned picks."""
    try:
        from src.models.independent.odds_anchor import load_anchors
        raw = load_anchors()
    except Exception as exc:
        print(f"[team_fit] pick anchors load failed: {exc}")
        return {}
    out = {}
    for p, d in raw.items():
        p10 = float(d.get("pick_p10") or 0)
        p50 = float(d.get("pick_p50") or 0)
        p90 = float(d.get("pick_p90") or 0)
        ep = float(d.get("expected_pick") or p50)
        # Right-tail heavy → use expected_pick as the anchor; else P50.
        right_heavy = (p90 - p50) > 2 * (p50 - p10) + 20
        anchor = ep if right_heavy else p50
        out[p] = {"p10": p10, "p50": p50, "p90": p90,
                  "expected_pick": ep, "anchor": anchor,
                  "conf": float(d.get("market_confidence") or 0)}
    return out


_TEAM_LANDING_PRIORS = _load_team_landing_priors()
_PICK_ANCHORS = _load_pick_anchors()


def reload_market_signals():
    """Reload Kalshi market priors. Call after a fresh odds refresh."""
    global _TEAM_LANDING_PRIORS, _PICK_ANCHORS
    _TEAM_LANDING_PRIORS = _load_team_landing_priors()
    _PICK_ANCHORS = _load_pick_anchors()


def _reasoning_position_boost(team_code: str) -> dict[str, float]:
    """Aggregate positional_need / premium_position_preference signals
    for a team into per-position small weights. Called once per team."""
    if not team_code or team_code not in _REASONING_SIGNALS:
        return {}
    out = {}
    for sig in _REASONING_SIGNALS[team_code]:
        if sig.get("reason_type") == "positional_need" and sig.get("position"):
            pos = sig["position"]
            out[pos] = out.get(pos, 0.0) + 0.20 * float(sig.get("strength", 0))
        elif sig.get("reason_type") == "latent_need" and sig.get("position"):
            pos = sig["position"]
            out[pos] = out.get(pos, 0.0) + 0.10 * float(sig.get("strength", 0))
        elif sig.get("reason_type") == "scheme_fit_premium" and sig.get("position"):
            pos = sig["position"]
            out[pos] = out.get(pos, 0.0) + 0.08
    # Cap each at +0.40 so reasoning supplements but never dominates
    return {k: min(v, 0.40) for k, v in out.items()}


def _cap_constraint_mult(pos: str, team_profile: dict) -> float:
    """Cap-tight teams can't swing high-$ rookie QBs or premium OL as
    easily. Cap-flush teams have a bit more latitude on premium positions.
    Returns a multiplier on the need score (0.85 to 1.10)."""
    cap = team_profile.get("cap_context", {}) or {}
    tier = (cap.get("constraint_tier") or "normal").lower()
    if tier in ("severely_tight", "tight"):
        # QB rookie contracts are expensive 5-year commitments; OT/premium
        # positions locked in by existing FA. Mild penalty.
        if pos in ("QB", "OT", "EDGE"):
            return 0.90 if tier == "tight" else 0.82
    if tier == "flush":
        if pos in ("QB", "OT", "EDGE", "WR"):
            return 1.08
    return 1.00


def _visit_bonus_map(team_code: str, team_profile: dict) -> dict[str, float]:
    """Precompute {player_name -> visit_bonus} per team, cached.

    Gating applied (audit-2026-04-20 fixes):
      - Shared-visit dampening: divide bonus by sqrt(n_teams_that_visited+1).
        A player visited by 15 teams (like Malachi Lawrence) signals less
        than one visited by 3.
      - PFF gate: prospects without a real PFF grade get HALF the visit
        bonus. Stops no-grade prospects from riding visits into top 32.
    """
    import math
    cached = _VISIT_BONUS_CACHE.get(team_code)
    if cached is not None:
        return cached
    vs = team_profile.get("visit_signals", {}) or {}
    visited = vs.get("confirmed_visits", []) or []
    if not visited:
        _VISIT_BONUS_CACHE[team_code] = {}
        return {}
    visit_full_lower = set()
    visit_surnames = set()
    for v in visited:
        if not isinstance(v, str): continue
        vl = v.strip().lower()
        visit_full_lower.add(vl)
        last = vl.rsplit(" ", 1)[-1] if " " in vl else vl
        if len(last) >= 4:
            visit_surnames.add(last)
    import pandas as pd
    pros_path = _ROOT / "data/processed/prospects_2026_enriched.csv"
    if not pros_path.exists():
        _VISIT_BONUS_CACHE[team_code] = {}
        return {}
    players = pd.read_csv(pros_path, usecols=["player"])["player"].dropna().astype(str)
    out = {}
    for p in players:
        pl = p.lower()
        if pl in visit_full_lower:
            base = 0.30
        elif (pl.rsplit(" ", 1)[-1] if " " in pl else pl) in visit_surnames:
            base = 0.12
        else:
            continue
        # Shared-visit dampening
        spread = _VISIT_SPREAD.get(p, 1)
        base = base / math.sqrt(max(1, spread))
        # PFF gate — halve for no-grade prospects
        if p not in _PFF_LOOKUP:
            base *= 0.5
        out[p] = base
    _VISIT_BONUS_CACHE[team_code] = out
    return out


def _narrative_bonus_map(team_profile: dict) -> dict[str, float]:
    """Precompute {player_name -> bonus} for narrative mentions, once per
    team. Returns the full-name match table so team_fit can use map() in
    the hot path instead of str.contains across 25 mentions × 727 rows
    every pick."""
    team_code = team_profile.get("team") or ""
    cached = _NARRATIVE_BONUS_CACHE.get(team_code)
    if cached is not None:
        return cached
    mentions = _collect_narrative_mentions(team_profile)
    if not mentions:
        _NARRATIVE_BONUS_CACHE[team_code] = {}
        return {}
    # Load prospects once per team so we can do the containment check
    # here (still once, not per-sim).
    import pandas as pd
    from pathlib import Path
    pros_path = _ROOT / "data/processed/prospects_2026_enriched.csv"
    if not pros_path.exists():
        _NARRATIVE_BONUS_CACHE[team_code] = {}
        return {}
    players = pd.read_csv(pros_path, usecols=["player"])["player"].dropna().astype(str)
    pl_lower = players.str.lower()
    bonus = pd.Series(0.0, index=players.index)
    for m in mentions:
        m_low = m.lower()
        match = pl_lower.str.contains(m_low, regex=False, na=False)
        bonus = bonus.where(~match, bonus + 0.08)
    bonus = bonus.clip(upper=0.20)
    result = {p: float(b) for p, b in zip(players, bonus) if b > 0}
    _NARRATIVE_BONUS_CACHE[team_code] = result
    return result


def _collect_narrative_mentions(team_profile: dict) -> list[str]:
    """Extract specific prospect names that appear in the team's narrative
    blocks (player_archetypes, roster_needs_tiered, uncertainty_flags).

    Analysts write team-side reasoning like 'ARI's EDGE board at #3 is
    Bailey/Reese; Mauigoa if they pivot to OL' — those name-drops are the
    structured result of team research, not analyst picks assigned to
    slots. Using them as candidate-pool weak bonuses is the allowed
    reasoning-signal path per the directive.
    """
    import re
    team_code = team_profile.get("team") or ""
    if team_code in _NARRATIVE_NAME_CACHE:
        return _NARRATIVE_NAME_CACHE[team_code]
    narr = team_profile.get("narrative", {}) or {}
    fields = []
    pa = narr.get("player_archetypes", {}) or {}
    if isinstance(pa, dict):
        fields.extend([v for v in pa.values() if isinstance(v, str)])
    for k in ("roster_needs_tiered", "gm_fingerprint", "uncertainty_flags",
              "context_2025", "context_2026"):
        v = narr.get(k)
        if isinstance(v, str):
            fields.append(v)

    combined = " \n ".join(fields)
    # Capitalized name heuristic: "Fernando Mendoza", "Caleb Downs", "Bailey"
    # Allow single-capitalized tokens to catch surname-only references, but
    # require at least 4 letters to avoid catching TLA team codes.
    pattern = re.compile(r"\b([A-Z][A-Za-z.'-]{3,}(?:\s+[A-Z][A-Za-z.'-]+)?)\b")
    hits = set()
    for m in pattern.findall(combined):
        # Drop team names, school tokens, and common words
        if m.upper() in {"ARIZONA","ATLANTA","BALTIMORE","BUFFALO","CAROLINA",
                         "CHICAGO","CINCINNATI","CLEVELAND","DALLAS","DENVER",
                         "DETROIT","GREEN","HOUSTON","INDIANAPOLIS","JACKSONVILLE",
                         "KANSAS","LAS","ANGELES","MIAMI","MINNESOTA","NEW",
                         "ORLEANS","ENGLAND","YORK","OAKLAND","PHILADELPHIA",
                         "PITTSBURGH","SAN","SEATTLE","TAMPA","TENNESSEE",
                         "WASHINGTON","ALABAMA","AUBURN","GEORGIA","MICHIGAN",
                         "OHIO","TEXAS","USC","CLEMSON","OREGON","UTAH","LSU",
                         "UNIVERSITY","COLLEGE","BOARD","BOARDS","DAY","ROUND",
                         "TIER","PICK","PICKS","NEED","NEEDS","PREMIUM","FIT"}:
            continue
        if m.lower() in {"edge","ol","dl","wr","qb","rb","te","cb","lb","ss","fs"}:
            continue
        hits.add(m)
    result = sorted(hits, key=lambda s: -len(s))[:25]
    _NARRATIVE_NAME_CACHE[team_code] = result
    return result
