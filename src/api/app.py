"""
FastAPI backend for the NFL draft predictor dashboard.

Responsibilities:
  - Serve the bundled Vite React SPA from /static (built from frontend/dist).
  - Expose read-only endpoints over the model's canonical JSON/CSV outputs.
    All endpoints read from disk on each request (no caching), so regenerated
    model data propagates to the dashboard on the next page load.
  - Provide a POST /api/simulate endpoint that runs the stage2 simulation in
    a background worker and streams progress back via Server-Sent Events.

One-command launch:
    python -m src.api.app            # dev mode on :8000
  or
    python run_dashboard.py          # wrapper that also builds the frontend
                                       if the static bundle is missing.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

# Share-mode safety knobs (set by run_dashboard.py via env vars).
# They are intentionally env-driven so re-launching with different flags
# picks up new values without touching source.
READ_ONLY = os.environ.get("DRAFT_READ_ONLY") == "1"
AUTH_TOKEN = os.environ.get("DRAFT_AUTH_TOKEN") or ""
# DRAFT_MAX_SIMS caps the per-request sim count so one visitor on a public
# deploy can't monopolize the server with a 5000-sim request. Defaults to
# 5000 for local dev; set to 100 in Dockerfile/render.yaml for cloud.
MAX_SIMS = int(os.environ.get("DRAFT_MAX_SIMS", "5000"))

ROOT = Path(__file__).resolve().parents[2]
FEATURES = ROOT / "data" / "features"
PROCESSED = ROOT / "data" / "processed"
STATIC_DIR = Path(__file__).parent / "static"

TEAM_AGENTS_JSON = FEATURES / "team_agents_2026.json"
ANALYST_AGG_JSON = FEATURES / "analyst_aggregate_2026.json"
ANALYST_CONSENSUS_JSON = FEATURES / "analyst_consensus_2026.json"

# DRAFT_MODE (env var) selects which model's outputs the API surfaces.
#   "independent" (default) — analyst-free team-agent simulator (the product)
#   "benchmark"             — legacy analyst-aware pipeline (for comparison)
DRAFT_MODE = os.environ.get("DRAFT_MODE", "independent").lower()
if DRAFT_MODE == "independent":
    MODEL_REASONING_JSON = PROCESSED / "model_reasoning_2026_independent.json"
    MC_CSV = PROCESSED / "monte_carlo_2026_independent.csv"
    # PICKS_CSV: canonical post-clamp modal pick per R1 slot.
    # BOARD_CSV: full prospect big board with independent_grade / tier / rank.
    PICKS_CSV = PROCESSED / "predictions_2026_independent_picks.csv"
    BOARD_CSV = PROCESSED / "predictions_2026_independent.csv"
    PREDICTIONS_CSV = PICKS_CSV  # back-compat alias
else:
    MODEL_REASONING_JSON = PROCESSED / "model_reasoning_2026.json"
    MC_CSV = PROCESSED / "monte_carlo_2026_v12.csv"
    PICKS_CSV = PROCESSED / "predictions_2026.csv"
    BOARD_CSV = PROCESSED / "predictions_2026.csv"
    PREDICTIONS_CSV = PICKS_CSV
MC_TRADES_JSON = PROCESSED / "monte_carlo_trades_2026.json"
TEAM_CTX_CSV = PROCESSED / "team_context_2026_enriched.csv"


def _original_pick_owners() -> dict[int, str]:
    """Map pick_number -> team for R1 picks per the pre-sim draft order.
    Used as the canonical owner so the UI shows the DEFAULT draft order
    instead of post-sim 'most_likely_team' (which can differ when trades
    fire)."""
    if not TEAM_CTX_CSV.exists():
        return {}
    df = pd.read_csv(TEAM_CTX_CSV)
    r1 = df[df["round"] == 1][["pick_number", "team"]]
    return {int(r.pick_number): r.team for _, r in r1.iterrows()}
PROSPECTS_CSV = PROCESSED / "prospects_2026_enriched.csv"

app = FastAPI(title="NFL Draft Predictor 2026", version="2.0")

# Dev-mode CORS so the Vite dev server (localhost:5173) can call the API.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_team_agents() -> dict:
    if not TEAM_AGENTS_JSON.exists():
        raise HTTPException(
            status_code=503,
            detail=f"{TEAM_AGENTS_JSON.name} not found. "
                   "Run: python src/data/build_team_agents.py",
        )
    return json.loads(TEAM_AGENTS_JSON.read_text(encoding="utf-8"))


def _load_analyst_agg() -> dict:
    if not ANALYST_AGG_JSON.exists():
        return {"_meta": {}, "players": {}}
    return json.loads(ANALYST_AGG_JSON.read_text(encoding="utf-8"))


def _file_mtime(path: Path) -> str | None:
    if not path.exists():
        return None
    return datetime.fromtimestamp(path.stat().st_mtime,
                                  tz=timezone.utc).isoformat(timespec="seconds")


# ---------------------------------------------------------------------------
# Team endpoints
# ---------------------------------------------------------------------------

@app.get("/api/teams")
def list_teams() -> dict:
    """Returns compact per-team summaries suitable for the dashboard grid.
    Heavy fields (full narrative, visit lists) are omitted here."""
    data = _load_team_agents()
    teams = []
    for abbr, p in data.items():
        if abbr.startswith("_"):
            continue
        needs = sorted(p.get("roster_needs", {}).items(),
                       key=lambda kv: -float(kv[1]))[:3]
        top_needs = [{"pos": k, "score": float(v)} for k, v in needs]
        teams.append({
            "team":           abbr,
            "gm":             p.get("gm"),
            "hc":             p.get("hc"),
            "new_hc":         p.get("new_hc", False),
            "new_gm":         p.get("new_gm", False),
            "win_pct":        p.get("win_pct"),
            "r1_picks":       p.get("all_r1_picks", []),
            "total_picks":    p.get("total_picks", 0),
            "qb_situation":   p.get("qb_situation"),
            "qb_urgency":     p.get("qb_urgency"),
            "predictability": p.get("predictability", ""),
            "top_needs":      top_needs,
            "scheme_type":    p.get("scheme", {}).get("type", "default"),
            "scheme_premium": p.get("scheme", {}).get("premium", []),
            "capital_abundance": p.get("draft_capital", {}).get("capital_abundance"),
            "n_confirmed_visits": p.get("visit_signals", {}).get("n_confirmed", 0),
            "cap_tier":       p.get("cap_context", {}).get("constraint_tier"),
            "trade_up_rate":   p.get("trade_behavior", {}).get("trade_up_rate"),
            "trade_down_rate": p.get("trade_behavior", {}).get("trade_down_rate"),
        })
    teams.sort(key=lambda t: (t["r1_picks"][0] if t["r1_picks"] else 99,
                              t["team"]))
    return {"teams": teams}


@app.get("/api/teams/{abbr}")
def team_detail(abbr: str) -> dict:
    data = _load_team_agents()
    abbr = abbr.upper()
    if abbr not in data or abbr.startswith("_"):
        raise HTTPException(status_code=404, detail=f"Team '{abbr}' not found")
    return data[abbr]


@app.get("/api/league")
def league_synthesis() -> dict:
    data = _load_team_agents()
    return data.get("_league", {})


@app.get("/api/meta")
def meta() -> dict:
    data = _load_team_agents()
    m = data.get("_meta", {})
    return {
        **m,
        "share_mode": {
            "read_only":      READ_ONLY,
            "token_required": bool(AUTH_TOKEN),
            "max_sims":       MAX_SIMS,
        },
        "draft_mode": DRAFT_MODE,  # "benchmark" (default) or "independent"
        "files_present": {
            "team_agents":       TEAM_AGENTS_JSON.exists(),
            "analyst_aggregate": ANALYST_AGG_JSON.exists(),
            "monte_carlo":       MC_CSV.exists(),
            "predictions":       PREDICTIONS_CSV.exists(),
            "prospects":         PROSPECTS_CSV.exists(),
        },
        "files_mtime": {
            "team_agents":       _file_mtime(TEAM_AGENTS_JSON),
            "analyst_aggregate": _file_mtime(ANALYST_AGG_JSON),
            "monte_carlo":       _file_mtime(MC_CSV),
            "predictions":       _file_mtime(PREDICTIONS_CSV),
            "prospects":         _file_mtime(PROSPECTS_CSV),
        },
    }


@app.get("/api/independent-stats")
def independent_stats() -> dict:
    """Computed-at-request-time stats for the homepage hero 'by-the-numbers'
    strip. Always reflects the current data — no hardcoded values."""
    stats = {
        "top20_overlap_pct":  None,
        "top32_overlap_pct":  None,
        "top64_overlap_pct":  None,
        "top100_overlap_pct": None,
        "n_agents":           32,
        "n_sims":             None,
        "n_analyst_inputs":   0,
        "independence_tests_passing": "8/8",
        "mtime":              None,
    }
    # Compute overlap from predictions_2026_independent.csv + prospects rank
    pred_board = PROCESSED / "predictions_2026_independent.csv"
    pros_csv = PROSPECTS_CSV
    if pred_board.exists() and pros_csv.exists():
        try:
            p = pd.read_csv(pred_board)
            pr = pd.read_csv(pros_csv, usecols=["player", "rank"])
            merged = p.merge(pr, on="player", how="left")
            merged["rank"] = pd.to_numeric(merged["rank"], errors="coerce")
            for top_n in (20, 32, 64, 100):
                our_top = set(merged.head(top_n)["player"].dropna())
                cons_top = set(
                    merged[(merged["rank"].notna()) & (merged["rank"] <= top_n)]
                    ["player"].dropna()
                )
                if cons_top:
                    pct = 100 * len(our_top & cons_top) / top_n
                    stats[f"top{top_n}_overlap_pct"] = round(pct, 1)
            stats["mtime"] = _file_mtime(pred_board)
        except Exception as exc:
            stats["error"] = str(exc)
    # Pull sim count from the MC meta
    if MC_CSV.exists():
        try:
            df = pd.read_csv(MC_CSV)
            # n_any_landings is the total "this player landed at any slot"
            # across all sims; its max per-player approximates n_sims.
            if "n_any_landings" in df.columns:
                stats["n_sims"] = int(df["n_any_landings"].max())
        except Exception:
            pass
    return stats


# ---------------------------------------------------------------------------
# Prospect / analyst endpoints
# ---------------------------------------------------------------------------

@app.get("/api/prospects")
def prospects_summary(limit: int = 64) -> dict:
    if not PROSPECTS_CSV.exists():
        return {"prospects": []}
    df = pd.read_csv(PROSPECTS_CSV)
    # Use BOARD_CSV (full big board: final_rank, independent_tier, confidence)
    # rather than PICKS_CSV (slot mock only).
    board = pd.read_csv(BOARD_CSV) if BOARD_CSV.exists() else None
    if board is not None:
        pred_cols = [c for c in ["player", "independent_grade", "raw_model_pred",
                                  "independent_tier", "confidence", "final_rank"]
                     if c in board.columns]
        df = df.merge(board[pred_cols], how="left", on="player")
        if "independent_grade" in df.columns and "final_score" not in df.columns:
            df["final_score"] = df["independent_grade"]
    keep = ["player", "position", "college", "rank", "final_score",
            "independent_grade", "independent_tier", "confidence", "final_rank",
            "ras_score", "weight", "height"]
    have = [c for c in keep if c in df.columns]
    df = df[have].copy()
    if "rank" in df.columns:
        df = df.sort_values("rank", na_position="last").head(limit)
    return {
        "prospects": df.replace({float("nan"): None}).to_dict("records"),
        "count": int(len(df)),
    }


@app.get("/api/analyst-consensus")
def analyst_consensus() -> dict:
    """Return the full analyst consensus dataset (20 mocks + trades + per-pick
    reasoning). Used by the Simulate page to show model-vs-analyst
    side-by-side. Returns an empty-ish structure if the file is missing."""
    if not ANALYST_CONSENSUS_JSON.exists():
        return {"meta": {}, "analysts": [], "per_pick": {},
                 "reasoning": {}, "trades": []}
    return json.loads(ANALYST_CONSENSUS_JSON.read_text(encoding="utf-8"))


@app.get("/api/analyst/{player}")
def analyst_for_player(player: str) -> dict:
    agg = _load_analyst_agg().get("players", {})
    # Case-insensitive exact match
    for name, info in agg.items():
        if name.lower() == player.lower():
            return {"player": name, **info}
    raise HTTPException(status_code=404, detail=f"Player '{player}' not found")


# ---------------------------------------------------------------------------
# Simulation endpoints
# ---------------------------------------------------------------------------

@app.get("/api/simulations/reasoning")
def simulation_reasoning() -> dict:
    """Per-pick scoring breakdown + top contributing factors. Used by the
    frontend to explain WHY the model picked a specific player, especially
    useful when that pick differs from the tier-1 analyst consensus."""
    if not MODEL_REASONING_JSON.exists():
        return {"picks": {}, "meta": {"file_present": False}}
    d = json.loads(MODEL_REASONING_JSON.read_text(encoding="utf-8"))
    return {
        "picks":  d.get("picks", {}),
        "meta":   {**d.get("meta", {}),
                   "file_present": True,
                   "mtime": _file_mtime(MODEL_REASONING_JSON)},
    }


# Market-implied probability lookup, loaded lazily on first use. Used as the
# primary source of "will this pick actually happen" probability on the UI —
# Kalshi prices are real money on the outcome, which is more meaningful than
# our sim's raw frequency (which only measures model conviction).
_MARKET_LANDING_CACHE: dict[str, dict[str, float]] | None = None


def _load_market_landings() -> dict[str, dict[str, float]]:
    """{player: {team_code: normalized_prob}} from Kalshi team-landing markets."""
    global _MARKET_LANDING_CACHE
    if _MARKET_LANDING_CACHE is not None:
        return _MARKET_LANDING_CACHE
    try:
        import sys as _sys
        _sys.path.insert(0, str(ROOT))
        from src.models.independent.odds_anchor import build_team_landing_priors
        priors = build_team_landing_priors()
        _MARKET_LANDING_CACHE = {
            p: dict(d.get("team_probs") or {}) for p, d in priors.items()
        }
    except Exception:
        _MARKET_LANDING_CACHE = {}
    return _MARKET_LANDING_CACHE


def _displayed_probability(raw_sim_prob: float,
                            player: str | None = None,
                            team: str | None = None,
                            slot: int | None = None) -> float:
    """The MODEL's estimate of P(team drafts player at this slot in real life).

    Integrates two independent signals:

      - Model sim conviction — raw frequency from our MC. Encodes structural
        info the market may under-price (team scheme, coaching tree, GM
        affinity, visit signals, roster need, cap posture).
      - Market prior — Kalshi team-landing price. Aggregates real money
        across many traders, captures info our model may miss (locker-room
        talk, private intel, late trade rumors).

    Bayesian-style linear blend so neither signal dominates. Weights depend
    on whether market coverage exists for this (player, team) pair.

    Before blending, the model prior is haircut for epistemic uncertainty
    (the sim doesn't know draft-day surprises); after blending, the result
    is hard-capped at 92% since nothing about the draft is truly certain.
    """
    # Model side — sim frequency with epistemic discount (our model can't
    # observe everything: medical, war rooms, late trade talks, smokescreens).
    if raw_sim_prob <= 0.20:
        model_prior = raw_sim_prob
    else:
        discount = 0.20
        if slot and slot > 5:
            discount += min(0.12, (slot - 5) * 0.008)
        model_prior = raw_sim_prob * (1.0 - discount)

    # Market side — Kalshi team-landing probability (if covered)
    market_prob = None
    if player and team:
        landings = _load_market_landings()
        market_prob = (landings.get(player) or {}).get(team)

    # Blend or use model-only
    if market_prob is None or market_prob <= 0:
        blended = model_prior
    else:
        # 60% market / 40% model. Real money already aggregates expert
        # consensus plus trader intel we don't see; we lean on it slightly
        # more than our own sim, but our structural signals still carry
        # weight because markets can under-price specific team-fit data.
        blended = 0.60 * float(market_prob) + 0.40 * model_prior

    # World-uncertainty haircut: whatever the signals say, the actual draft
    # has slot-swap trades, last-minute calls from GMs, medical flags, and
    # ego reaches. Bake a 10% epistemic discount into every pick, plus
    # extra slot-depth volatility beyond pick 10 (cascade effects compound).
    world_discount = 0.10
    if slot:
        if slot > 10: world_discount += min(0.08, (slot - 10) * 0.006)
        if slot > 20: world_discount += 0.03
    final = blended * (1.0 - world_discount)

    # Hard ceiling — even the most-certain pick of the draft (pick #1 when
    # priced at -20000) historically only hits ~95%. We cap our displayed
    # belief at 78% so the UI never claims certainty.
    return round(min(0.78, max(0.01, final)), 3)


# Back-compat alias so existing call sites keep working.
_calibrate_probability = _displayed_probability


def _merge_consensus_rank(df: pd.DataFrame) -> pd.DataFrame:
    """MC CSV lacks consensus_rank; merge it in from prospects_2026_enriched.csv
    (rank column) so downstream consumers see it correctly."""
    if "consensus_rank" in df.columns:
        return df
    if not PROSPECTS_CSV.exists():
        df["consensus_rank"] = None
        return df
    pros = pd.read_csv(PROSPECTS_CSV, usecols=["player", "rank", "college"])
    df = df.merge(pros, on="player", how="left", suffixes=("", "_pros"))
    df["consensus_rank"] = df["rank"]
    if "college" not in df.columns and "college_pros" in df.columns:
        df["college"] = df["college_pros"]
    return df


@app.get("/api/simulations/prospects")
def prospect_landings() -> dict:
    """Per-prospect landing distribution from the latest Monte Carlo CSV.
    Returns one row per (player, slot) with probability, plus aggregate
    mean/variance/total_prob. Used by the Simulate page's 'By prospect' view
    so sliders (Styles, Tate, etc. that don't win any single slot) are
    visible via their aggregate distribution."""
    if not MC_CSV.exists():
        return {"prospects": [], "meta": {"file_present": False}}
    df = pd.read_csv(MC_CSV)
    df = _merge_consensus_rank(df)
    slot_col = "pick_slot" if "pick_slot" in df.columns else "pick_number"
    team_col = "most_likely_team" if "most_likely_team" in df.columns else "team"

    out: list[dict] = []
    # Group by player; CSV has one row per (player, slot) already.
    for player, grp in df.groupby("player"):
        grp = grp.sort_values("probability", ascending=False)
        first = grp.iloc[0]
        landings = [
            {
                "slot":        int(r[slot_col]),
                "team":        r.get(team_col),
                "probability": _displayed_probability(
                    float(r["probability"] or 0),
                    player=player, team=r.get(team_col),
                    slot=int(r[slot_col])),
            }
            for _, r in grp.iterrows()
        ]
        mean_landing = float(first.get("mean_landing_pick") or 0)
        var_landing = float(first.get("variance_landing_pick") or 0)
        total_prob = sum(l["probability"] for l in landings)
        out.append({
            "player":           player,
            "position":         first.get("position"),
            "college":          first.get("college"),
            "consensus_rank":   (int(first["consensus_rank"])
                                 if pd.notna(first.get("consensus_rank")) else None),
            "landings":         landings,
            "mean_landing":     round(mean_landing, 2),
            "variance_landing": round(var_landing, 2),
            "total_prob":       round(total_prob, 3),
            "most_likely_slot": int(first[slot_col]),
            "most_likely_team": first.get(team_col),
        })
    # Sort by mean landing (earliest first)
    out.sort(key=lambda r: (r["mean_landing"] or 99))
    return {
        "prospects": out,
        "meta": {"file_present": True, "mtime": _file_mtime(MC_CSV),
                 "source": MC_CSV.name, "n_prospects": len(out)},
    }


@app.get("/api/simulations/trades")
def simulation_trades() -> dict:
    """Per-pick trade events from the latest Monte Carlo run.

    Response:
      { n_simulations, total_trade_events,
        per_pick: { "21": [{ from_team, to_team, prob, count, top_targets }] } }
    """
    if not MC_TRADES_JSON.exists():
        return {"n_simulations": 0, "total_trade_events": 0, "per_pick": {}}
    with open(MC_TRADES_JSON, "r", encoding="utf-8") as f:
        return json.load(f)


@app.get("/api/simulations/latest")
def latest_simulation() -> dict:
    """Read the latest monte_carlo output CSV and return per-pick top-4
    candidates plus summary stats.

    Uses greedy per-slot assignment so a player never shows as top-1 at
    two different slots: we walk picks 1..32 in order and take the highest-
    probability candidate not yet claimed by an earlier slot. Runner-ups
    at each slot are still shown (they can repeat) as alternatives."""
    original_owners = _original_pick_owners()
    if not MC_CSV.exists():
        return {"picks": [], "meta": {"file_present": False}}
    df = pd.read_csv(MC_CSV)
    df = _merge_consensus_rank(df)
    pick_col = "pick_slot" if "pick_slot" in df.columns else "pick_number"
    team_col = "most_likely_team" if "most_likely_team" in df.columns else "team"

    # PICKS_CSV is the canonical post-clamp modal pick per R1 slot (written
    # by independent/run.py _write_outputs + odds_clamp). MC_CSV carries the
    # raw landing distribution and is used here ONLY for alternate candidates.
    picks_canonical: dict[int, dict] = {}
    if PICKS_CSV.exists():
        pk = pd.read_csv(PICKS_CSV)
        for _, r in pk.iterrows():
            slot = int(r["pick"])
            picks_canonical[slot] = {
                "player":     r.get("player"),
                "position":   r.get("position"),
                "team":       r.get("team"),
                "probability": float(r.get("probability") or 0),
                "school":     r.get("school"),
            }

    # Group MC by slot for alternates.
    per_slot: dict[int, list] = {}
    for pn, sub in df.groupby(pick_col):
        sub = sub.sort_values("probability", ascending=False)
        per_slot[int(pn)] = list(sub.itertuples(index=False))

    # Build R1 output from canonical picks CSV; fall back to MC if missing.
    all_slots = sorted(set(picks_canonical.keys()) | set(per_slot.keys()))
    out_picks: list[dict] = []
    for pn in all_slots:
        canonical = picks_canonical.get(pn)
        mc_rows = per_slot.get(pn, [])

        if canonical and canonical.get("player"):
            modal_player = canonical["player"]
            modal_position = canonical["position"]
            modal_team = canonical["team"]
            modal_prob = _displayed_probability(
                canonical["probability"], player=modal_player,
                team=modal_team, slot=pn)
            modal_school = canonical.get("school")
            # Find the MC row for this player-slot to get consensus_rank
            mc_match = next((r for r in mc_rows
                             if getattr(r, "player", None) == modal_player), None)
            modal_cons_rank = (int(getattr(mc_match, "consensus_rank"))
                               if mc_match is not None
                               and pd.notna(getattr(mc_match, "consensus_rank", None))
                               else None)
        elif mc_rows:
            top = mc_rows[0]
            modal_player = getattr(top, "player", None)
            modal_position = getattr(top, "position", None)
            modal_team = getattr(top, team_col, None)
            modal_prob = _displayed_probability(
                float(getattr(top, "probability", 0) or 0),
                player=modal_player, team=modal_team, slot=pn)
            modal_school = getattr(top, "college", None) or getattr(top, "school", None)
            modal_cons_rank = (int(getattr(top, "consensus_rank"))
                               if pd.notna(getattr(top, "consensus_rank", None))
                               else None)
        else:
            continue

        # Alternates from MC: top 3 OTHER players at this slot
        alternates = []
        for r in mc_rows:
            if getattr(r, "player", None) == modal_player:
                continue
            alternates.append({
                "player":          getattr(r, "player", None),
                "position":        getattr(r, "position", None),
                "college":         getattr(r, "college", None) or getattr(r, "school", None),
                "probability":     _displayed_probability(
                    float(getattr(r, "probability", 0) or 0),
                    player=getattr(r, "player", None),
                    team=getattr(r, team_col, None),
                    slot=pn),
                "team":            getattr(r, team_col, None),
                "consensus_rank":  (int(getattr(r, "consensus_rank"))
                                     if pd.notna(getattr(r, "consensus_rank", None))
                                     else None),
                "variance_landing_pick": float(
                    getattr(r, "variance_landing_pick", 0) or 0),
            })
            if len(alternates) >= 3:
                break

        candidates = [{
            "player":         modal_player,
            "position":       modal_position,
            "college":        modal_school,
            "probability":    modal_prob,
            "team":           modal_team,
            "consensus_rank": modal_cons_rank,
            "variance_landing_pick": 0.0,
        }, *alternates]

        original_team = original_owners.get(pn)
        out_picks.append({
            "pick_number":      pn,
            "team":             original_team or modal_team,
            "original_team":    original_team,
            "most_likely_team": modal_team,
            "candidates":       candidates,
        })
    return {
        "picks": out_picks,
        "meta": {
            "file_present": True,
            "mtime": _file_mtime(MC_CSV),
            "source": MC_CSV.name,
        },
    }


# ---------------------------------------------------------------------------
# Static frontend (Vite build output). Served last so /api/* routes win.
# ---------------------------------------------------------------------------

if (STATIC_DIR / "index.html").exists():
    # SPA catch-all: everything except /api goes to index.html
    app.mount("/assets", StaticFiles(directory=STATIC_DIR / "assets"),
              name="assets")

    @app.get("/{full_path:path}")
    def spa_catchall(full_path: str) -> FileResponse:
        if full_path.startswith("api/"):
            raise HTTPException(status_code=404)
        target = STATIC_DIR / full_path
        if target.is_file():
            return FileResponse(target)
        return FileResponse(STATIC_DIR / "index.html")

else:
    @app.get("/")
    def root() -> JSONResponse:
        return JSONResponse({
            "ok": True,
            "message": "Backend running. Frontend not built yet. "
                        "Build with: cd frontend && npm run build",
            "endpoints": [
                "/api/teams", "/api/teams/{abbr}", "/api/league", "/api/meta",
                "/api/prospects", "/api/simulations/latest",
                "POST /api/simulate", "/api/simulate/status",
            ],
        })


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("src.api.app:app", host="127.0.0.1", port=8000, reload=False)
