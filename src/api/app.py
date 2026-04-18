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

import asyncio
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

import pandas as pd
from fastapi import FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

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
MODEL_REASONING_JSON = PROCESSED / "model_reasoning_2026.json"
MC_CSV = PROCESSED / "monte_carlo_2026_v12.csv"
PREDICTIONS_CSV = PROCESSED / "predictions_2026.csv"
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


# ---------------------------------------------------------------------------
# Prospect / analyst endpoints
# ---------------------------------------------------------------------------

@app.get("/api/prospects")
def prospects_summary(limit: int = 64) -> dict:
    if not PROSPECTS_CSV.exists():
        return {"prospects": []}
    df = pd.read_csv(PROSPECTS_CSV)
    pred = pd.read_csv(PREDICTIONS_CSV) if PREDICTIONS_CSV.exists() else None
    if pred is not None:
        df = df.merge(pred[["player", "final_score", "model_pred"]],
                      how="left", on="player")
    keep = ["player", "position", "college", "rank", "final_score", "ras_score",
            "weight", "height"]
    have = [c for c in keep if c in df.columns]
    df = df[have].copy()
    if "rank" in df.columns:
        df = df.sort_values("rank", na_position="last").head(limit)
    return {
        "prospects": df.replace({float("nan"): None}).to_dict("records"),
        "count": int(len(df)),
    }


@app.get("/api/settings/defaults")
def settings_defaults() -> dict:
    """Return the model's default tunable parameters. Single source of
    truth: pulled directly from stage2 module constants, so whenever the
    code changes these, the 'Reset to defaults' button in the UI picks up
    the new values.

    Only exposes knobs safe for non-expert users to tweak without blowing
    up the model. Trade and scoring internals remain code-configured."""
    import sys as _sys
    from pathlib import Path as _Path
    _sys.path.insert(0, str(_Path(__file__).resolve().parents[2]))
    from src.models import stage2_game_theoretic as s
    return {
        "reach_gap_threshold":          s.REACH_GAP_THRESHOLD,
        "late_pick_reach_threshold":    s.LATE_PICK_REACH_THRESHOLD,
        "elite_cons_rank_threshold":    s.ELITE_CONS_RANK_THRESHOLD,
        "slider_boost_threshold":       s.SLIDER_BOOST_THRESHOLD,
        "position_scarcity_gap":        s.POSITION_SCARCITY_GAP_THRESHOLD,
        "position_scarcity_boost":      s.POSITION_SCARCITY_BOOST,
        "predictability_score_sigma":   s.PREDICTABILITY_SCORE_SIGMA,
        "post_combine_boosts":          dict(s.POST_COMBINE_BOOSTS),
        "qb_cascade_window":            s.QB_CASCADE_WINDOW,
        "tier_sizes":                   dict(s.TIER_SIZES),
        # Position-value multipliers — the spine of positional scarcity
        "pos_value_mult":               dict(s.POS_VALUE_MULT),
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

class SimulateRequest(BaseModel):
    n_simulations: int = 500


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
                "probability": float(r["probability"] or 0),
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


@app.get("/api/simulations/latest")
def latest_simulation() -> dict:
    """Read the latest monte_carlo output CSV and return per-pick top-4
    candidates plus summary stats.

    Uses greedy per-slot assignment so a player never shows as top-1 at
    two different slots: we walk picks 1..32 in order and take the highest-
    probability candidate not yet claimed by an earlier slot. Runner-ups
    at each slot are still shown (they can repeat) as alternatives."""
    if not MC_CSV.exists():
        return {"picks": [], "meta": {"file_present": False}}
    df = pd.read_csv(MC_CSV)
    pick_col = "pick_slot" if "pick_slot" in df.columns else "pick_number"
    team_col = "most_likely_team" if "most_likely_team" in df.columns else "team"

    # Group by slot with candidates sorted by probability desc.
    per_slot: dict[int, list] = {}
    for pn, sub in df.groupby(pick_col):
        sub = sub.sort_values("probability", ascending=False)
        per_slot[int(pn)] = list(sub.itertuples(index=False))

    # Greedy top-1 assignment: walk slots in pick order, claim each slot's
    # best-available player.
    claimed: set[str] = set()
    out_picks: list[dict] = []
    for pn in sorted(per_slot.keys()):
        rows = per_slot[pn]
        # Pick top-1 as first unclaimed, falling back to index 0 if all taken.
        top_idx = next(
            (i for i, r in enumerate(rows)
             if getattr(r, "player", None) not in claimed),
            0,
        )
        ordered = [rows[top_idx]] + [r for i, r in enumerate(rows) if i != top_idx]
        ordered = ordered[:4]
        if getattr(ordered[0], "player", None):
            claimed.add(ordered[0].player)
        out_picks.append({
            "pick_number": pn,
            "team": getattr(ordered[0], team_col, None),
            "candidates": [
                {
                    "player":          getattr(r, "player", None),
                    "position":        getattr(r, "position", None),
                    "college":         getattr(r, "college", None),
                    "probability":     float(getattr(r, "probability", 0) or 0),
                    "team":            getattr(r, team_col, None),
                    "consensus_rank":  (int(getattr(r, "consensus_rank"))
                                         if pd.notna(getattr(r, "consensus_rank", None))
                                         else None),
                    "variance_landing_pick": float(
                        getattr(r, "variance_landing_pick", 0) or 0
                    ),
                }
                for r in ordered
            ],
        })
    return {
        "picks": out_picks,
        "meta": {
            "file_present": True,
            "mtime": _file_mtime(MC_CSV),
            "source": MC_CSV.name,
        },
    }


# Background sim state — a single in-memory job slot. Runs one sim at a time.
_SIM_STATE: dict = {
    "status": "idle",      # idle | running | complete | error
    "started_at": None,
    "finished_at": None,
    "n_simulations": 0,
    "progress_current": 0,   # N sims completed so far (parsed from stdout)
    "progress_pct": 0.0,     # 0-100
    "log_tail": [],
    "error": None,
}


async def _run_simulation(n_sims: int) -> None:
    """Spawn the stage2 simulator as a subprocess, capture stdout, push the
    last N lines into _SIM_STATE.log_tail so the frontend can poll."""
    _SIM_STATE.update({
        "status": "running",
        "started_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "finished_at": None,
        "n_simulations": n_sims,
        "progress_current": 0,
        "progress_pct": 0.0,
        "log_tail": [],
        "error": None,
    })
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    cmd = [
        sys.executable, "-c",
        f"import sys; sys.path.insert(0, r'{ROOT}'); "
        f"import src.models.stage2_game_theoretic as s; "
        f"s.N_SIMULATIONS = {int(n_sims)}; s.main()",
    ]
    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
            cwd=str(ROOT),
            env=env,
        )
        assert proc.stdout is not None
        # Filter patterns that should never reach the UI — they're noise
        # (pandas/numpy warnings, internal paths, deprecation notices).
        NOISE_PATTERNS = (
            "PerformanceWarning",
            "DataFrame is highly fragmented",
            "Consider joining all columns",
            "frame.copy()",
            "DeprecationWarning",
            "FutureWarning",
            "UserWarning",
        )
        # Progress marker: stage2 prints "  ...N/M" every 100 sims. We extract
        # current/total, convert to pct, and expose via sim_state for the UI
        # progress bar.
        import re as _re
        PROGRESS_RX = _re.compile(r"^\s*\.\.\.(\d+)/(\d+)\s*$")
        async for raw in proc.stdout:
            line = raw.decode("utf-8", errors="replace").rstrip()
            # Update progress counter before any filtering
            pm = PROGRESS_RX.match(line)
            if pm:
                current = int(pm.group(1))
                total = int(pm.group(2)) or 1
                _SIM_STATE["progress_current"] = current
                _SIM_STATE["progress_pct"] = round(100 * current / total, 1)
            if any(p in line for p in NOISE_PATTERNS):
                continue
            if line.startswith("  ") and ("[" in line or ".py" in line or "pros[" in line):
                continue
            if not line.strip():
                continue
            _SIM_STATE["log_tail"].append(line)
            if len(_SIM_STATE["log_tail"]) > 120:
                _SIM_STATE["log_tail"] = _SIM_STATE["log_tail"][-120:]
        rc = await proc.wait()
        if rc != 0:
            _SIM_STATE.update({"status": "error",
                               "error": f"exit code {rc}"})
        else:
            _SIM_STATE.update({
                "status": "complete",
                "progress_pct": 100.0,
                "progress_current": _SIM_STATE.get("n_simulations", 0),
            })
    except Exception as exc:  # pragma: no cover — surface to client
        _SIM_STATE.update({"status": "error", "error": str(exc)})
    finally:
        _SIM_STATE["finished_at"] = datetime.now(timezone.utc).isoformat(
            timespec="seconds")


@app.post("/api/simulate")
async def simulate(
    req: SimulateRequest,
    x_auth_token: Optional[str] = Header(default=None),
) -> dict:
    # Share-mode safety gates. When the launcher sets DRAFT_READ_ONLY=1 the
    # whole endpoint is disabled; when DRAFT_AUTH_TOKEN is set the caller
    # must present it as X-Auth-Token.
    if READ_ONLY:
        raise HTTPException(
            status_code=403,
            detail="Dashboard is running in read-only mode; simulation disabled",
        )
    if AUTH_TOKEN and x_auth_token != AUTH_TOKEN:
        raise HTTPException(
            status_code=401,
            detail="Missing or invalid X-Auth-Token header",
        )
    if _SIM_STATE["status"] == "running":
        raise HTTPException(
            status_code=409,
            detail="A simulation is already running; poll /api/simulate/status",
        )
    if req.n_simulations < 1 or req.n_simulations > MAX_SIMS:
        raise HTTPException(
            status_code=400,
            detail=f"n_simulations must be between 1 and {MAX_SIMS}",
        )
    asyncio.create_task(_run_simulation(req.n_simulations))
    return {"status": "started", "n_simulations": req.n_simulations}


@app.get("/api/simulate/status")
def simulate_status() -> dict:
    return _SIM_STATE


class ReplayRequest(BaseModel):
    forced_picks: dict[int, str] = {}   # {pick_number: player_name}
    n_simulations: int = 10


@app.post("/api/simulate/replay")
def simulate_replay(req: ReplayRequest) -> dict:
    """Re-run the simulator with user-specified forced picks. Used by the
    Mock Draft builder: when the user pins a pick, this endpoint returns
    model predictions for the remaining slots given those constraints.

    Runs in-process (not subprocess) because this is a short-lived request
    that needs quick turnaround for interactive UX. Caps at 20 sims/request
    to keep response time bounded."""
    if READ_ONLY:
        raise HTTPException(status_code=403, detail="Read-only mode")
    n_sims = max(3, min(int(req.n_simulations), 20))
    # Import the simulator lazily so the FastAPI startup isn't slowed by
    # loading pandas+model artifacts.
    import sys as _sys
    from pathlib import Path as _Path
    _sys.path.insert(0, str(_Path(__file__).resolve().parents[2]))
    from src.models import stage2_game_theoretic as s
    import numpy as np
    from collections import Counter, defaultdict

    pros, team_ctx, needs, top3_needs, qb_urgency_map = s.load_data()
    s.GM_AFFINITY_CACHE = s.load_gm_affinity()
    picks_template = [
        {
            "pick_number": int(row["pick_number"]),
            "team":         row["team"],
            "bpa_weight":   float(row.get("bpa_weight") or 0.5),
            "need_weight":  float(row.get("need_weight") or 0.5),
            "trade_up_rate":   float(row.get("trade_up_rate") or 0.35),
            "trade_down_rate": float(row.get("trade_down_rate") or 0.30),
            "pick_range_trade_rate": float(row.get("pick_range_trade_rate") or 0.30),
            "round":        int(row.get("round") or 1),
            "qb_urgency":   float(row.get("qb_urgency") or 0.0),
        }
        for _, row in team_ctx[team_ctx["round"] == 1].iterrows()
    ]

    rng = np.random.default_rng(int(hash(repr(req.forced_picks)) & 0xFFFFFFFF))
    # Aggregate landings
    landing: dict = defaultdict(lambda: Counter())
    team_at_slot: dict = defaultdict(lambda: defaultdict(Counter))
    for _ in range(n_sims):
        history, _tl, picks_realised = s.simulate_one(
            pros, picks_template, top3_needs, qb_urgency_map, rng,
            forced_picks={int(k): v for k, v in req.forced_picks.items()},
        )
        pick_team_map = {p["pick_number"]: p["team"] for p in picks_realised}
        for pn, player in history.items():
            landing[player][pn] += 1
            team_at_slot[player][pn][pick_team_map.get(pn, "?")] += 1

    # Build per-slot top-4 with greedy assignment so a player never shows
    # as top-1 at two different slots. Walk slots 1..32 in order and claim
    # each slot's best-available unclaimed player.
    claimed: set[str] = set()
    out_picks: list[dict] = []
    for pn in range(1, 33):
        by_prob = [(player, slots.get(pn, 0))
                   for player, slots in landing.items()
                   if slots.get(pn, 0) > 0]
        by_prob.sort(key=lambda t: -t[1])
        if not by_prob:
            continue
        # Promote the first unclaimed player to top-1.
        top_idx = next(
            (i for i, (p, _) in enumerate(by_prob) if p not in claimed),
            0,
        )
        ordered = [by_prob[top_idx]] + [
            t for i, t in enumerate(by_prob) if i != top_idx
        ]
        ordered = ordered[:4]
        claimed.add(ordered[0][0])
        candidates = []
        for player, count in ordered:
            prow = pros[pros["player"] == player]
            teams_here = team_at_slot[player][pn]
            team = teams_here.most_common(1)[0][0] if teams_here else "?"
            candidates.append({
                "player":         player,
                "position":       (prow["position"].iloc[0]
                                    if not prow.empty else None),
                "college":        (prow["college"].iloc[0]
                                    if not prow.empty else None),
                "consensus_rank": (int(prow["rank"].iloc[0])
                                    if not prow.empty and pd.notna(prow["rank"].iloc[0]) else None),
                "probability":    count / n_sims,
                "team":           team,
            })
        out_picks.append({
            "pick_number": pn,
            "team":        candidates[0]["team"] if candidates else None,
            "candidates":  candidates,
        })

    return {
        "picks": out_picks,
        "meta":  {"n_sims": n_sims,
                   "forced_picks_count": len(req.forced_picks)},
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
