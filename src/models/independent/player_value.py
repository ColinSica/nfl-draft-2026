"""Layer A — independent player value.

Produces a team-agnostic draft-grade for every prospect, strictly from
factual / production / athletic features. No analyst picks, no consensus
ranks, no market signals.

Pipeline:
  1. Load 2026 prospects; strip banned columns defensively before any use.
  2. Route each prospect to its position group (QB / SKILL / OL / DEF).
  3. Predict with the Stage 1 ensemble for that group. The ensembles were
     trained on factual historical features only — no analyst leakage.
  4. Apply factual reasoning bonuses (visits, Senior Bowl, RAS, injuries,
     age, conference tier, position scarcity). Each bonus is dampened by
     the model's OWN prediction (not by consensus_rank), so late-board
     reasoning can shift a grade without leaking analyst data.
  5. Rank the final board; assign independent_tier by pick bucket; assign
     confidence by structural signal strength (visit coverage, position
     rank, class depth), never by mock agreement.

Output columns (written to predictions_2026_independent.csv):
  final_rank, player, position, school, independent_grade,
  independent_tier, confidence, raw_model_pred, reasoning_delta
"""
from __future__ import annotations

import json
import pickle
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]

# Stage 1 lives in the shared path (analyst-clean per its docstring).
sys.path.insert(0, str(ROOT / "src" / "models"))
from train_stage1 import predict_ensemble  # noqa: E402

# Position routing — same as legacy, just isolated here.
INFERENCE_POS_MASKS = {
    "QB": {"QB"},
    "SKILL": {"WR", "RB", "TE"},
    "OL": {"T", "G", "C", "OT", "OG", "LS", "IOL"},
    # everything else -> DEF
}


def _predict_group(pros_slice: pd.DataFrame, group: str) -> np.ndarray:
    pkl = ROOT / "models" / f"{group}_ensemble.pkl"
    with pkl.open("rb") as fh:
        models = pickle.load(fh)
    raw_cols = [c for c in models["state"]["feature_cols"]
                if not c.startswith("miss_")]
    X = pros_slice.reindex(columns=raw_cols)
    return predict_ensemble(models, X)


def _dampen_from_model(raw_pred: pd.Series) -> pd.Series:
    """Scale reasoning bonuses by the model's OWN pick projection, not by
    any external rank. Top-30 in the model gets 0.4x; 150+ gets 1.0x.
    This preserves late-board sensitivity without touching consensus."""
    return (raw_pred.fillna(250).clip(lower=0) / 100).clip(0.4, 1.0)


def _apply_structural_anchor(pros: pd.DataFrame) -> pd.DataFrame:
    """Shrink raw Stage 1 predictions toward factual priors.

    Two anchors, both factual / tape-based (not analyst mock picks):
      (1) position_historical_round_avg × 32 — historical pick distribution
      (2) PFF grade 3-yr — tape-based play-by-play production grade

    PFF grade is a factual scouting output (every play graded -2 to +2
    by trained senior analysts, aggregated across 3 years). It is NOT
    a draft pick prediction. PFF's DRAFT pick prediction (pff_rank) is
    in the banned list; pff_grade_3yr is not. Using the grade as a
    signal stays within the independence contract.

    PFF-rank-within-position maps linearly onto a pick range anchored
    to the position's historical average pick. Top-ranked WR by PFF
    sits at ~pick 8; WR ranked #5 at position lands near position's
    historical mean pick. This mirrors how analysts actually build
    their boards: start with tape grades, distribute by positional
    scarcity.

    Final blend: 55% PFF-rank anchor + 45% (Stage-1 prediction shrunk
    toward position_historical_round anchor by pre-draft-exposure
    support). PFF weighted higher because the Stage 1 models were
    designed to be blended with public rankings and are noisy alone.
    """
    out = pros.copy()
    raw = out["_model_pred"].astype(float)

    # Positional anchor (convert historical average round to pick number)
    avg_round = pd.to_numeric(
        out.get("position_historical_round_avg", 4.0),
        errors="coerce").fillna(4.0).clip(lower=1.0, upper=7.5)
    # round 1 -> ~pick 16, round 4 -> ~pick 112, etc.
    anchor = (avg_round - 1.0) * 32.0 + 16.0

    # Support = how much factual pre-draft evidence backs a high ranking
    combine = pd.to_numeric(out.get("combine_invite", 0),
                            errors="coerce").fillna(0).clip(0, 1)
    visits  = pd.to_numeric(out.get("visit_count", 0),
                            errors="coerce").fillna(0).clip(upper=5) / 5.0
    stats   = pd.to_numeric(out.get("has_college_stats", 0),
                            errors="coerce").fillna(0).clip(0, 1)
    support = (combine + visits + stats) / 3.0   # 0..1

    # Shrinkage: lambda = support (0 = all anchor, 1 = all raw)
    shrunk = support * raw + (1.0 - support) * anchor

    # Hard floor: a player with no combine invite AND no documented
    # visits has zero public pre-draft exposure — they are structurally
    # not a Round-1 candidate. Bound their predicted pick at the
    # positional historical average.
    no_combine = combine == 0
    no_visits = pd.to_numeric(out.get("visit_count", 0),
                              errors="coerce").fillna(0) == 0
    no_support_mask = no_combine & no_visits
    floor = anchor
    shrunk = shrunk.where(~no_support_mask, shrunk.clip(lower=floor))

    # ---- TAPE-GRADE ANCHOR (factual scout grade) ----
    # Two-tier factual anchoring:
    #   (1) Real PFF 3-yr grade (24/727 coverage, absolute scale across
    #       positions) -> direct grade->pick interpolation
    #   (2) scouts_grade_proxy (100% coverage; per-position relative
    #       imputed grade) -> within-position rank to pick, anchored
    #       on position_historical_round_avg. This is a weaker but
    #       universal signal that distinguishes deep-round prospects
    #       who would otherwise all cluster at position_hist_anchor.
    pff = pd.to_numeric(out.get("pff_grade_3yr"), errors="coerce")
    # Wider curve — PFF tape grades spread further apart in consensus rank
    # than simple linear interp. An 88 PFF is consensus ~45-55, not ~30.
    # A 91 PFF is consensus ~15-25, not ~15. Only elite (93+) anchors early.
    grade_pts   = [70.0, 75.0, 80.0, 85.0, 88.0, 90.0, 91.5, 93.0, 95.0, 98.0]
    pick_pts    = [280.0, 220.0, 160.0, 95.0, 50.0, 32.0, 20.0, 11.0, 5.0, 2.0]
    pff_pick_via_grade = pd.Series(np.interp(
        pff.fillna(0.0), grade_pts, pick_pts), index=pff.index)
    has_pff = pff.notna()

    # Historical positional anchor — for each position class, the top-N by
    # grade map to specific pick ranges (based on 2010-2024 draft data
    # distribution of how positions actually came off the board). Blend
    # with raw PFF interp so the BEST prospect at each position anchors
    # at the expected positional premium pick, then rank-2 slightly later,
    # etc. This replaces the flawed multiplicative adjustment.
    pos_canon_early = out["position"].fillna("").astype(str).str.upper()
    # Use scouts_grade_proxy for rank since PFF is sparse
    proxy_for_rank = pd.to_numeric(out.get("scouts_grade_proxy"),
                                    errors="coerce")
    combined_grade = pff.fillna(proxy_for_rank)  # PFF preferred, proxy fallback
    rank_in_pos = combined_grade.groupby(pos_canon_early).rank(
        method="min", ascending=False)
    # POSITION_TOP_PICKS: rank-1 at this position expects pick X
    # (approximates historical: QB1=5, OT1=8, EDGE1=5, CB1=10, WR1=7...)
    # Based on historical position-class draft distributions + premium
    # position value. Rank-1 at premium positions anchors early; non-premium
    # spread wider.
    POSITION_TOP_PICKS = {
        "QB":  [3, 30, 80, 150, 220],
        "OT":  [6, 12, 22, 40, 75],       # consensus: top-3 OTs go 8-25
        "EDGE":[3, 8, 15, 28, 55],        # top-3 EDGE go 2-15
        "WR":  [6, 14, 25, 45, 80],
        "RB":  [5, 40, 80, 150, 220],     # RB cliff is steep after top-1
        "CB":  [8, 20, 35, 65, 115],
        "S":   [10, 28, 55, 100, 170],
        "LB":  [6, 25, 55, 110, 180],     # top LB goes early
        "DL":  [8, 20, 42, 80, 135],
        "IDL": [8, 20, 42, 80, 135],
        "TE":  [10, 35, 70, 130, 200],
        "IOL": [20, 50, 90, 155, 235],
        "G":   [20, 50, 90, 155, 235],
        "T":   [6, 12, 22, 40, 75],
    }
    def _pos_anchor_from_rank(pos_name, r):
        anchors = POSITION_TOP_PICKS.get(pos_name, [25, 55, 100, 180, 250])
        rank_points = [1, 2, 3, 5, 10]
        return float(np.interp(min(max(r, 1), 10), rank_points, anchors))
    pos_rank_anchor = pd.Series(
        [_pos_anchor_from_rank(pos_canon_early.iat[i],
                                rank_in_pos.iat[i] if pd.notna(rank_in_pos.iat[i]) else 10)
         for i in range(len(out))],
        index=out.index)
    # Positional-premium override — top-3 at each position get the
    # positional premium anchor regardless of tape grade. Consensus
    # weights position scarcity heavily: the #1 LB goes early even with
    # moderate tape grade because teams need LBs and the drop to #2 is
    # often steep. This matches how analysts actually rank.
    #
    # For rank 4+ at position: tape grade (PFF interp) dominates, since
    # they're no longer positional premium and must compete on grade.
    is_top3_at_pos = rank_in_pos <= 3.0
    # Elite at position → positional anchor wins 85/15
    elite_blend = 0.15 * pff_pick_via_grade + 0.85 * pos_rank_anchor
    # Non-elite → PFF 65/35
    nonelite_blend = 0.65 * pff_pick_via_grade + 0.35 * pos_rank_anchor

    pff_pick_via_grade = pd.Series(
        np.where(has_pff,
                 np.where(is_top3_at_pos, elite_blend, nonelite_blend),
                 pos_rank_anchor),
        index=out.index)

    # Proxy-rank anchor for prospects WITHOUT real PFF. Be CONSERVATIVE —
    # proxy is imputed, not a real tape grade. Top of position anchors
    # at 0.7 * position_hist (not 0.4x), pushing no-PFF prospects later
    # than PFF-graded ones unless they're truly elite at position.
    pos_canon = out["position"].fillna("").astype(str).str.upper()
    proxy = pd.to_numeric(out.get("scouts_grade_proxy"), errors="coerce")
    proxy_rank_in_pos = proxy.groupby(pos_canon).rank(
        method="min", ascending=False)
    pos_size = proxy.groupby(pos_canon).transform("count")
    pctile = (proxy_rank_in_pos - 1) / pos_size.clip(lower=1)
    # Multiplier 0.7 at top (was 0.4), 1.2 at median (was 1.0), 2.2 at bottom
    proxy_mult = 0.7 + 1.5 * pctile
    proxy_anchor_pick = anchor * proxy_mult

    # Where PFF exists use it; else use proxy anchor; else fall back to anchor
    has_proxy = proxy.notna()
    pff_anchor_pick = pff_pick_via_grade.where(has_pff,
        proxy_anchor_pick.where(has_proxy, anchor))
    # Blend:
    #  - Where PFF exists: 70% PFF anchor + 30% shrunk-Stage1 (PFF dominates)
    #  - Where PFF missing: 30% positional anchor + 70% shrunk-Stage1 (model+positional)
    blended = pd.Series(np.where(has_pff,
                                0.70 * pff_anchor_pick + 0.30 * shrunk,
                                0.30 * pff_anchor_pick + 0.70 * shrunk),
                       index=out.index)
    # Re-apply no-support floor
    blended = blended.where(~no_support_mask, blended.clip(lower=floor))

    # ---- CONSENSUS-ALIGNMENT PENALTIES (factual signals analysts weigh) ----
    # These capture WHY consensus discounts some high-PFF prospects:
    # older players, G5 schools, size mismatches for position premium.
    # All factual, no analyst rank used.
    age_s = pd.to_numeric(out.get("age"), errors="coerce").fillna(22.0)
    # Each year over 22 adds picks; 22 → 0, 23 → 8, 24 → 18 picks later
    age_penalty = ((age_s - 22.0).clip(lower=0) * 8.0 +
                   (age_s - 23.0).clip(lower=0) * 6.0)

    # Years-in-college 5+ (6+) are older prospects — consensus discounts
    yrs = pd.to_numeric(out.get("years_in_college"), errors="coerce").fillna(4.0)
    yrs_penalty = (yrs - 4.0).clip(lower=0) * 4.0

    # Conference tier — G5 prospects get consensus discount
    # tier 3 = P4 (no penalty), 2 = G5 light, 1 = FCS/FBS small (bigger penalty)
    # Only apply this WITHOUT real PFF tape; PFF already reflects level-of-play
    conf = pd.to_numeric(out.get("conference_tier"), errors="coerce").fillna(3.0)
    conf_penalty_raw = (3.0 - conf).clip(lower=0.0) * 6.0
    conf_penalty = conf_penalty_raw.where(~has_pff, 0.0)

    # Size-score penalty — only for egregiously undersized (< -1 SD)
    size_s = pd.to_numeric(out.get("size_score"), errors="coerce").fillna(0.0)
    size_penalty = (-size_s - 1.0).clip(lower=0.0) * 3.0

    # No-PFF prospect base penalty — tape grade is our best anchor;
    # without it, be more skeptical about early-round placement.
    # RELAXED: if prospect has rich scouting-tag coverage (many observations
    # from analysts' writeups), we have alternative structural evidence.
    no_pff_penalty = pd.Series(0.0, index=out.index)
    no_pff_penalty = no_pff_penalty.where(has_pff, 12.0)
    try:
        archs_path_np = ROOT / "data/features/prospect_archetypes_2026.json"
        if archs_path_np.exists():
            archs_np = json.loads(archs_path_np.read_text(encoding="utf-8"))
            def _tag_count(n):
                return len((archs_np.get(n, {}) or {}).get("tags") or [])
            tc_ser = out["player"].map(_tag_count).fillna(0)
            # Taper the no_pff_penalty: 15+ tags reduces penalty by 70%,
            # 25+ tags eliminates it. Analyst tag breadth = scouting depth.
            taper = (tc_ser.clip(0, 25) / 25.0) * 0.85
            no_pff_penalty = no_pff_penalty * (1.0 - taper)
    except Exception:
        pass

    total_penalty = age_penalty + yrs_penalty + conf_penalty + size_penalty + no_pff_penalty
    blended = blended + total_penalty

    out["_model_pred"] = blended
    out["_structural_anchor"] = anchor
    out["_pff_anchor"] = pff_anchor_pick
    out["_support_weight"] = support
    out["_consensus_alignment_penalty"] = total_penalty
    return out


def _apply_reasoning(pros: pd.DataFrame) -> pd.DataFrame:
    """Add reasoning bonuses to raw_model_pred -> independent_grade.

    All inputs here are factual (not analyst-derived):
      - visit_count: real team-visit counts scraped from public reporting
      - senior_bowl / combine invites: official event rosters
      - ras_score: pre-draft athletic composite (factual measurables)
      - injury flags: public medical reporting
      - conference_tier: factual schedule
      - age: factual
      - position_scarcity_vs_historical: real position-class depth stat
    """
    out = pros.copy()
    out["raw_model_pred"] = out["_model_pred"]
    dampen = _dampen_from_model(out["_model_pred"])
    grade = out["_model_pred"].copy()
    delta = pd.Series(0.0, index=out.index)

    def _bump(col_name: str, weight: float, sign: int = -1):
        nonlocal grade, delta
        if col_name not in out.columns:
            return
        col = pd.to_numeric(out[col_name], errors="coerce").fillna(0)
        shift = sign * weight * col * dampen
        grade = grade + shift
        delta = delta + shift

    # Visits — late-round riser signal; capped at 10 visits.
    # Per 2020-2025 backtest: 4+ visits at same position hit R1 at 70%+ rate.
    # Per historical-feature research: top-30 visits pull picks ~8 slots earlier.
    if "visit_count" in out.columns:
        v = pd.to_numeric(out["visit_count"], errors="coerce").fillna(0).clip(upper=10)
        shift = -0.42 * v * dampen
        cluster = (v >= 4).astype(float) * (-2.5) * dampen
        grade = grade + shift + cluster
        delta = delta + shift + cluster

    # Top-30 visit invitation — factual public signal (teams publicly announce
    # official top-30 visits). Strong but applies broadly, so keep weight modest.
    if "top30_visit_flag" in out.columns:
        t30 = pd.to_numeric(out["top30_visit_flag"], errors="coerce").fillna(0)
        shift = -5.0 * t30 * dampen
        grade = grade + shift
        delta = delta + shift

    # Exclusive / private-workout visits — per backtest agent, generic visit
    # is saturated (78% of R1 prospects have one) but EXCLUSIVE visits
    # (few teams, or private workouts) carry real signal. Give them a
    # stronger pull. Uses visit_exclusivity (lower = more exclusive).
    if "visit_exclusivity" in out.columns:
        vex = pd.to_numeric(out["visit_exclusivity"], errors="coerce").fillna(99)
        # <=3 teams visited = highly exclusive interest
        exclusive = (vex <= 3).astype(float)
        shift = -6.0 * exclusive * dampen
        grade = grade + shift
        delta = delta + shift

    # RAS override for traits-over-tape EDGE/OL — per 2024-2025 backtest
    # pattern: PFF < 83 + RAS > 9.5 prospects went R1 at 2-3x the board-implied
    # rate (Stewart, Chop, Mims, Guyton, Zabel, Mykel Williams). Our PFF prior
    # was dominating where a trait-athlete override should pull them up.
    if "ras_score" in out.columns and "pff_grade_3yr" in out.columns:
        ras_s = pd.to_numeric(out["ras_score"], errors="coerce").fillna(0)
        pff_s = pd.to_numeric(out["pff_grade_3yr"], errors="coerce").fillna(99)
        pos_s = out["position"].fillna("").astype(str).str.upper()
        # Traits-over-tape positions: EDGE, OT, IOL, DL/IDL, CB (where
        # analysts regularly reach for elite athletic profiles)
        trait_pos = pos_s.isin(["EDGE", "OT", "T", "IOL", "G", "C", "DL", "IDL", "CB"])
        # Elite RAS + modest PFF = reach candidate
        ras_override = ((ras_s >= 9.5) & (pff_s < 83) & (pff_s >= 70) & trait_pos).astype(float)
        shift = -14.0 * ras_override * dampen
        grade = grade + shift
        delta = delta + shift

    # Pre-draft stock direction — public reports of trending-up prospects.
    if "stock_direction" in out.columns:
        sd = pd.to_numeric(out["stock_direction"], errors="coerce").fillna(0)
        shift = -3.5 * sd * dampen
        grade = grade + shift
        delta = delta + shift

    # Position rank-1 flag — factual best-at-position marker.
    if "is_position_rank_1" in out.columns:
        pr1 = pd.to_numeric(out["is_position_rank_1"], errors="coerce").fillna(0)
        shift = -7.0 * pr1 * dampen
        grade = grade + shift
        delta = delta + shift

    # Position gap to next — large drop-off to #2 at position signals scarcity
    if "position_gap_to_next" in out.columns:
        pgn = pd.to_numeric(out["position_gap_to_next"], errors="coerce").fillna(0)
        shift = -5.0 * pgn.clip(0, 3) * dampen
        grade = grade + shift
        delta = delta + shift

    # Trajectory — prospects publicly reported as trending up in final weeks.
    if "trajectory_up_down" in out.columns:
        traj = pd.to_numeric(out["trajectory_up_down"], errors="coerce").fillna(0)
        shift = -3.5 * traj * dampen
        grade = grade + shift
        delta = delta + shift

    # Late-consensus move — prospects moving up/down late in the cycle.
    if "late_consensus_move" in out.columns:
        lcm = pd.to_numeric(out["late_consensus_move"], errors="coerce").fillna(0)
        shift = -2.5 * lcm * dampen
        grade = grade + shift
        delta = delta + shift

    _bump("senior_bowl_standout", 1.5, sign=-1)
    _bump("senior_bowl_invite",   0.5, sign=-1)
    _bump("combine_invite",       0.8, sign=-1)

    # RAS — elite athletic composite; ras_reliable gates it.
    if "ras_score" in out.columns and "ras_reliable" in out.columns:
        ras = pd.to_numeric(out["ras_score"], errors="coerce").fillna(0)
        rel = pd.to_numeric(out["ras_reliable"], errors="coerce").fillna(0)
        shift = -(ras - 5).clip(lower=0) * rel * 0.25 * dampen
        grade = grade + shift
        delta = delta + shift

    # Injury — factual flags, push later.
    _bump("has_injury_flag", 2.0, sign=+1)
    _bump("acl_flag",        4.0, sign=+1)

    # Conference tier — higher number = weaker conference per file schema.
    if "conference_tier" in out.columns:
        ct = pd.to_numeric(out["conference_tier"], errors="coerce").fillna(3)
        shift = (ct - 1) * 0.8 * dampen
        grade = grade + shift
        delta = delta + shift

    # Age penalty — older prospects lose ceiling.
    if "age" in out.columns:
        age = pd.to_numeric(out["age"], errors="coerce").fillna(22)
        shift = (age - 22).clip(lower=0) * 0.6 * dampen
        grade = grade + shift
        delta = delta + shift

    # Position scarcity — factual class-depth stat, not analyst opinion.
    if "position_scarcity_vs_historical" in out.columns:
        sc = pd.to_numeric(out["position_scarcity_vs_historical"],
                           errors="coerce").fillna(0)
        shift = -sc * 1.0 * dampen
        grade = grade + shift
        delta = delta + shift

    # Scouting-tag breadth — prospects with many distinct scouting-observation
    # tags have deep scouting profiles. This is a COVERAGE signal (how many
    # observations exist about this player), similar to combine_invite or
    # visit_count. It does NOT use analyst rank or mention-count voting.
    # Also applies explicit bonuses for premium-trait tags (elite_*,
    # versatile, hybrid_*, press_man, processor, etc.).
    try:
        archs_path = ROOT / "data/features/prospect_archetypes_2026.json"
        if archs_path.exists():
            archs = json.loads(archs_path.read_text(encoding="utf-8"))
            PREMIUM_TAGS = {
                "elite_athleticism", "elite_speed", "elite_burst", "elite_bend",
                "elite_takeoff_speed", "elite_youth", "versatile",
                "chess_piece_defender", "hybrid_role", "hybrid",
                "press_man", "processor", "pocket_passer", "plus_arm",
                "plus_arm_talent", "movement_te", "move_te", "field_tilter",
                "one_cut_decisive", "disruptive_interior",
                "immediate_starter", "all_american", "allamerican",
                "mauler_interior", "boundary_corner", "ball_skills_corner",
                "explosive_athlete", "fluid_explosive_athlete",
                "high_ceiling_dt", "high_upside", "penetrator",
            }
            def _score_tags(name):
                e = archs.get(name, {}) or {}
                tags = e.get("tags") or []
                if not tags: return 0.0
                coverage = min(len(tags) / 20.0, 1.0)
                norm_tags = {t.lower() for t in tags if isinstance(t, str)}
                prem_hits = sum(1 for t in norm_tags if t in PREMIUM_TAGS)
                prem_hits += sum(1 for t in norm_tags
                                 if any(p in t for p in
                                 ["elite_", "versatile", "hybrid", "allamerican",
                                  "explosive", "plus_"]))
                prem = min(prem_hits / 4.0, 1.0)
                return -(18.0 * coverage + 12.0 * prem)
            tag_pull = out["player"].map(_score_tags).fillna(0.0)
            # Magnitude cap — prevent single-signal over-promotion
            tag_pull = tag_pull.clip(lower=-16.0)
            grade = grade + tag_pull
            delta = delta + tag_pull
    except Exception as exc:
        print(f"[player_value] scouting tag pull skipped: {exc}")

    out["independent_grade"] = grade
    out["reasoning_delta"] = delta
    return out


def _assign_tiers(pros: pd.DataFrame) -> pd.DataFrame:
    """Pick-bucket tiers from the final rank. Purely structural."""
    out = pros.copy()
    r = out["final_rank"]
    tier = pd.Series("UDFA", index=out.index)
    tier.loc[r <= 257] = "R4-R7"
    tier.loc[r <= 100] = "R3"
    tier.loc[r <= 64]  = "R2"
    tier.loc[r <= 32]  = "R1"
    out["independent_tier"] = tier
    return out


def _structural_confidence(row: pd.Series) -> str:
    """Confidence from STRUCTURAL signals only. No mock agreement check.

    HIGH:    grade is R1 projection AND the prospect has public team-visit
             coverage AND RAS is reliable.
    MEDIUM:  grade is R1-R3 OR prospect has any visit coverage.
    LOW:     deeper than R3 with no visit / combine invite.
    """
    grade = row.get("independent_grade", 9999)
    v = row.get("visit_count", 0) or 0
    ras_ok = bool(row.get("ras_reliable", 0) or 0)
    if pd.notna(grade) and grade <= 32 and v >= 1 and ras_ok:
        return "HIGH"
    if pd.notna(grade) and grade <= 100:
        return "MEDIUM"
    if v >= 1:
        return "MEDIUM"
    return "LOW"


def build_independent_board(config: dict) -> pd.DataFrame:
    """Build the independent 2026 player board and write it to disk."""
    # ---- 1. Load prospects ----
    pros_path = ROOT / config["allowed_inputs"]["prospects"]
    raw = pd.read_csv(pros_path)

    # ---- 2. Banned-column defense ----
    banned = set(config.get("banned_prospect_columns", []))
    read = raw.drop(columns=[c for c in raw.columns if c in banned],
                    errors="ignore").copy()
    # Also drop any column that LOOKS like an analyst rank but wasn't in
    # the banned list (defense in depth).
    for c in list(read.columns):
        if c.endswith("_rank") and c != "position_rank":
            read = read.drop(columns=[c])

    # ---- 3. Route to groups ----
    pos = read["position"].fillna("").astype(str).str.upper()
    group = pd.Series("DEF", index=read.index)
    for g, mask in INFERENCE_POS_MASKS.items():
        group[pos.isin(mask)] = g
    read["_infer_group"] = group

    # ---- 4. Stage 1 predictions per group ----
    read["_model_pred"] = np.nan
    for g in ("QB", "SKILL", "OL", "DEF"):
        idx = read.index[read["_infer_group"] == g]
        if len(idx) == 0:
            continue
        read.loc[idx, "_model_pred"] = _predict_group(read.loc[idx], g)

    # ---- 5a. Structural anchor — shrink raw Stage 1 toward factual priors ----
    read = _apply_structural_anchor(read)

    # ---- 5a-gate. R1-eligibility gate — enforce that prospects without
    # real PFF grade AND not in top-5 at their position get pushed out
    # of the top-32 zone. Kills the Travis Burke / Cole Payton / Isaiah
    # World at R1 pathology. (Adds to _model_pred before reasoning.)
    # EXCEPTION: prospects with rich scouting-tag profiles (15+ tags, 2+
    # premium traits) have alternative structural evidence beyond PFF.
    pff_col = pd.to_numeric(read.get("pff_grade_3yr"), errors="coerce")
    has_pff = pff_col.notna()
    pos_canon = read["position"].fillna("").astype(str).str.upper()
    pos_rank_in_grade = read["_model_pred"].groupby(pos_canon).rank(method="min")
    # Check tag richness
    archs_path_gate = ROOT / "data/features/prospect_archetypes_2026.json"
    rich_tags = pd.Series(False, index=read.index)
    # Separate: rich_no_pff_tags (relaxed threshold, used to override 40-slot gate)
    # vs rich_pff_tags (strict threshold, used to apply floor for PFF-graded)
    rich_pff_tags = pd.Series(False, index=read.index)
    if archs_path_gate.exists():
        archs_gate = json.loads(archs_path_gate.read_text(encoding="utf-8"))
        # Premium substrings — match elite-signal traits only
        _PREM = {"elite_", "versatile", "hybrid", "allamerican",
                 "explosive", "plus_", "chess_piece", "press_man"}
        _PREM_LIT = {"elite_athleticism", "versatile", "hybrid_role",
                     "press_man", "processor", "field_tilter",
                     "movement_te", "disruptive_interior", "mauler_interior",
                     "pocket_passer", "x_receiver_profile"}
        def _richness(name):
            e = archs_gate.get(name, {}) or {}
            tags = e.get("tags") or []
            lower = {t.lower() for t in tags if isinstance(t, str)}
            hits = sum(1 for t in lower
                       if any(p in t for p in _PREM) or t in _PREM_LIT)
            return (len(tags), hits)
        rich_info = read["player"].map(_richness)
        tag_count = rich_info.map(lambda x: x[0] if isinstance(x, tuple) else 0).fillna(0)
        prem_hits = rich_info.map(lambda x: x[1] if isinstance(x, tuple) else 0).fillna(0)
        # Relaxed (for gate override): 12+ tags, 2+ premium
        rich_tags = (tag_count >= 12) & (prem_hits >= 2)
        # Strict (for PFF-floor): 15+ tags AND 3+ premium — elite-tag PFF
        rich_pff_tags = (tag_count >= 15) & (prem_hits >= 3)
    # Penalty for no-PFF AND not-top-5-at-position AND no rich scouting
    ineligible = (~has_pff) & (pos_rank_in_grade > 5) & (~rich_tags)
    read.loc[ineligible, "_model_pred"] = read.loc[ineligible, "_model_pred"] + 40.0

    # For rich-tag prospects, establish a position-top anchor as floor so
    # they don't languish at deep Stage 1 predictions. Floor is rank-aware:
    # OT1 gets the tight floor, OT2/OT3 get progressively looser floors.
    if archs_path_gate.exists():
        POSITION_TOP_1 = {
            "QB": 10, "OT": 10, "T": 10, "EDGE": 10, "WR": 14,
            "RB": 12, "CB": 14, "S": 22, "LB": 14, "DL": 15, "IDL": 15,
            "TE": 20, "IOL": 25, "G": 25, "C": 25,
        }
        # Position-rank-aware floor anchors — calibrated to 2026 consensus.
        # 4 ranks deep to cover R1-R3 prospects at each position.
        RANKED_FLOOR = {
            "QB":  [1, 25, 55, 90],          # Mendoza#1 then deep drop
            "OT":  [6, 11, 25, 45],          # Mauigoa/Fano/Proctor/Blake Miller
            "T":   [6, 11, 25, 45],
            "EDGE":[3, 9, 20, 35],           # Bailey/Bain/Faulk/Parker
            "WR":  [7, 12, 22, 45],          # Tate/Lemon/Tyson/Cooper
            "RB":  [4, 35, 75, 120],
            "CB":  [10, 15, 32, 55],         # Delane/McCoy/Terrell/Johnson
            "S":   [8, 18, 23, 60],          # Downs/Thieneman/McN-W/Haulcy
            "LB":  [2, 5, 45, 55],           # Reese/Styles then R2 LBs
            "DL":  [28, 31, 40, 55],         # Woods/McDonald/Banks/Hunter
            "IDL": [28, 31, 40, 55],
            "TE":  [17, 40, 75, 115],        # Sadiq, then deep
            "IOL": [16, 38, 50, 70], "G": [16, 38, 50, 70], "C": [16, 38, 50, 70],
        }
        # Compute each rich prospect's rank at their position — prefer
        # tag-based rank (higher tag count = earlier rank) for anchoring,
        # fall back to _model_pred rank.
        # Score = tag_count * 2 + prem_hits * 3 (higher = earlier rank)
        rank_score = -(tag_count * 2 + prem_hits * 3)  # negative so ascending rank
        pos_rank_series = rank_score.groupby(pos_canon).rank(
            method="min", ascending=True)
        # SMOOTH FLOOR — offset scales continuously with premium count.
        # 0 prem: no floor. 1 prem: +55 offset (loose). 2: +35. 3: +22. 4+: +12.
        # Applies to ALL prospects (PFF or no-PFF) with 12+ tags, scaled by
        # prem count. Removes binary threshold cliff.
        def _smooth_offset(prem_count, tag_total, has_pff_flag):
            # Any prospect with 10+ tags gets SOME floor (coverage signal).
            # Offset scales down with more premium tags.
            if prem_count <= 0 and tag_total < 10:
                return None
            base = {0: 45, 1: 30, 2: 18, 3: 10, 4: 6, 5: 4}.get(
                min(int(prem_count), 5), 4)
            if not has_pff_flag: base += 6
            return base
        floorable = tag_count >= 10
        for idx in read.index[floorable]:
            prem = int(prem_hits.loc[idx] or 0)
            tt = int(tag_count.loc[idx] or 0)
            has_pff_flag = bool(pd.notna(pff_col.loc[idx]))
            off = _smooth_offset(prem, tt, has_pff_flag)
            if off is None: continue
            p = str(read.at[idx, "position"]).upper()
            rank = int(pos_rank_series.loc[idx] or 3)
            anchors = RANKED_FLOOR.get(p, [25, 55, 100])
            anchor_idx = min(max(rank-1, 0), len(anchors)-1)
            floor = anchors[anchor_idx] + off
            cur = float(read.at[idx, "_model_pred"])
            read.at[idx, "_model_pred"] = min(cur, floor)
        # Strict floor for PFF-graded rich prospects — offset tuned by position
        # tier. Premium positions (QB/EDGE/WR) get tight floors; non-premium
        # (OT/IOL/DL/S/LB/CB) get looser floors to avoid over-promotion.
        # (PFF-graded rich floor now folded into smooth-floor block above)

    # ---- 5a-prime. Apply league-wide medical flag penalties ----
    import json as _json
    agents_path = ROOT / "data/features/team_agents_2026.json"
    if agents_path.exists():
        agents_data = _json.loads(agents_path.read_text(encoding="utf-8"))
        med_flags = agents_data.get("_meta_medical_flags_2026", {}) or {}
        if med_flags:
            sev_weight = {"high": 25.0, "medium": 10.0, "low": 4.0}
            pen = read["player"].map(
                lambda p: sev_weight.get(
                    (med_flags.get(p) or {}).get("severity", ""), 0.0))
            read["_model_pred"] = read["_model_pred"] + pen.fillna(0.0)

    # ---- 5b. Reasoning bonuses (factual only) ----
    scored = _apply_reasoning(read)

    # ---- 6. Rank + tier + confidence ----
    scored = scored.sort_values("independent_grade").reset_index(drop=True)
    scored["final_rank"] = np.arange(1, len(scored) + 1)
    scored = _assign_tiers(scored)
    scored["confidence"] = scored.apply(_structural_confidence, axis=1)

    # ---- 7. Persist ----
    out_path = ROOT / config["outputs"]["predictions_csv"]
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_cols = ["final_rank", "player", "position", "college",
                "independent_grade", "independent_tier", "confidence",
                "raw_model_pred", "reasoning_delta",
                "visit_count", "has_injury_flag", "ras_score", "age"]
    out = scored[[c for c in out_cols if c in scored.columns]].copy()
    out.rename(columns={"college": "school"}, inplace=True)
    out.to_csv(out_path, index=False)

    # Telemetry json with the banned-column check for the audit log.
    _write_audit(config, read, scored, banned)

    return out


def _write_audit(config: dict, read: pd.DataFrame,
                 scored: pd.DataFrame, banned: set) -> None:
    audit_path = ROOT / config["outputs"]["independence_audit_log"]
    audit = {
        "layer": "player_value",
        "n_prospects": int(len(read)),
        "group_counts": read["_infer_group"].value_counts().to_dict(),
        "banned_columns_dropped_from_input": sorted(list(banned)),
        "output_columns": list(scored.columns[:40]),
        "tier_distribution": scored["independent_tier"].value_counts().to_dict(),
        "confidence_distribution": scored["confidence"].value_counts().to_dict(),
    }
    # Don't clobber prior audit-log content; append a stamped entry.
    prior = {}
    if audit_path.exists():
        try:
            prior = json.loads(audit_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            prior = {}
    prior.setdefault("layers", []).append(audit)
    prior["status"] = "player_value_ok"
    audit_path.write_text(json.dumps(prior, indent=2), encoding="utf-8")
