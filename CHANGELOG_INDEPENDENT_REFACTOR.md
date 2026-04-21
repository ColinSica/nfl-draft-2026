# Independent Team-Agent Refactor — Summary

Refactor executed in sections A–H to satisfy the
**"analyst-independent NFL Draft prediction system"** directive.

## Objective

Build a 32-team-agent simulator whose picks are explainable in team-logic
terms alone, without consuming analyst mock picks, consensus rank, or
mock-derived trade priors. Judge success after the real 2026 draft by
comparing the independent model against leading mocks.

## What ships

Two clearly separated model paths, with the independent path as the
default for serious evaluation:

```
src/models/independent/   — NO analyst picks, NO consensus rank
  player_value.py         — Stage 1 ensembles + factual reasoning bonuses
  team_fit.py             — need × scheme × archetype × GM × injury × ...
  availability.py         — board state (unpicked players)
  trade.py                — structural trade probability (no mock priors)
  run.py                  — Monte Carlo entry point

src/models/benchmark/     — analyst-aware, legacy path (for comparison)
  run.py                  — thin wrapper over stage2_game_theoretic

src/models/common/        — reserved for truly shared factual utilities
src/models/evaluate/      — backtest + post-draft scoreboard

configs/independent.yaml  — banned_* lists enforced by tests
configs/benchmark.yaml
tests/test_independence.py — 8 contract tests
```

## Run commands

```bash
# Independent (preferred)
python -m src.models.independent.run --sims 500 --seed 42

# Benchmark
python -m src.models.benchmark.run

# Backtest
python -m src.models.evaluate.backtest

# Post-draft scoreboard (after dropping data/live/actual_r1_2026.csv)
python -m src.models.evaluate.scoreboard

# Tests
pytest tests/test_independence.py -v

# API mode switch (env var)
DRAFT_MODE=independent python -m src.api.app
```

## Section-by-section

### Section A — verified Excel deltas
Applied the 2026-04-19 mock-refresh deltas that were factual (not analyst
picks): NO QB locked (Shough), HOU EDGE fully addressed (Anderson $150M),
TEN Saleh defensive HC, NYG Harbaugh-spine restructure + $18.4M cap fill,
pick provenance (#16 Gardner, #24 Lawrence, #30 Ramsey/Chubb, #29
Stafford), DAL DC Eberflus, NYJ QB lock, CLE QB consistency fix.
Flagged two Excel staleness contradictions (ARI HC, PIT HC) rather than
silently applying wrong data. Feedback memory saved so future Excel
syncs don't defer blindly.

### Section B — independent/benchmark split scaffold
Directory skeleton + banned-input contract enforced by 8 pytest tests:
- no banned imports in independent/*
- no banned column names in independent/*
- no banned file basenames in independent/*
- independent runner executes cleanly (in scaffold + full modes)
- independent output CSV contains no `consensus*`/`market*`/`analyst*` columns
- MC outputs exist and are well-formed

### Section C — independent player-value layer
`player_value.build_independent_board()` uses Stage 1 ensembles (clean
per their training docstring) + factual reasoning bonuses scaled by the
model's **own** prediction (not by consensus_rank). Banned columns are
stripped defensively at read time.

Output: `data/processed/predictions_2026_independent.csv` (727 prospects).

Removed from the independent path:
- 60-85% consensus_rank blend
- PFF rank re-rank
- analyst-tier dampening of reasoning bonuses

### Section D — team_fit + availability + trade + Monte Carlo
The core engine: each pick is a function of the team's structural profile
alone. 10 scoring components (vectorized via position-lookup dicts):

BPA, need (+qb_urgency additive), latent need, scheme premium, age-cliff
boost, coach college connection, scarcity, prior investment penalty, GM
affinity multiplier, injury/medical multiplier. Plus (Section F)
archetype fit.

`trade.py` gives structural trade_up/trade_down probabilities from team
historical rates × tier-exhaustion × capital × late-R1 premium.
**No mock-derived scenario files loaded.**

500-sim MC completes in ~4 min and writes:
- `predictions_2026_independent_picks.csv` — modal R1 picks
- `monte_carlo_2026_independent.csv` — landing probabilities
- `model_reasoning_2026_independent.json` — per-pick reasoning

### Section E — reasoning signal extraction
`src/data/extract_reasoning_signals.py` converts agent narratives into
structured tags: `{team, reason_type, subtype, strength, source_count,
source_quality, recency_weight, position, raw_excerpt}`. Reason types
include positional_need, latent_need, scheme_fit_premium, trade_*_likelihood,
gm_tendency_*, coaching_preference, medical_concern, visit_signal,
roster_timeline, premium_position_preference, new_regime_uncertainty,
cap_constraint.

Output: `data/features/team_reasoning_signals_2026.json` (1,011 signals
across 32 teams). Consumable by the engine as team-side evidence
(never as picks).

### Section F — archetypes, typed medical
`src/data/build_archetypes.py` tags 376 prospects with archetype labels
(X_receiver, slot_separator, press_corner, etc.) derived from measurables
+ production. Teams get scheme-driven preferred-archetype maps.

Tiered medical in `team_fit.py`: distinguishes generic `has_injury_flag`
from ACL / spine / shoulder flags with escalating multipliers, each
gated by the team's `medical_tolerance` (default 0.95).

### Section G — historical backtest + post-draft scoreboard
- `src/models/evaluate/backtest.py` — trains Stage 1 on years prior to
  each target year and scores it against the real R1. Reports top-32
  overlap, within-3, within-5, exact match.
  **Current baseline (Stage 1 alone, no team-agent layer):**
  ```
  2021: top32_overlap 40.6%  within5 21.9%
  2022: top32_overlap 34.4%  within5 12.5%
  2023: top32_overlap 50.0%  within5 25.0%
  2024: top32_overlap 56.2%  within5 18.8%
  2025: top32_overlap 46.9%  within5 15.6%
  ```
  (Full team-agent backtest requires per-year team profiles that aren't
  yet reconstructed; that's scoped as future work.)
- `src/models/evaluate/scoreboard.py` — stub that, after the 2026 draft,
  scores independent vs benchmark vs actual R1 when the user drops
  `data/live/actual_r1_2026.csv`.

### Section H — API mode toggle + summary
`src/api/app.py` now reads `DRAFT_MODE` env var. Default `benchmark`
(backward compatible); setting `DRAFT_MODE=independent` swaps the
MC/predictions/reasoning file paths so the same endpoints serve the
independent outputs without code changes. `/api/meta` surfaces the
active mode so the frontend can badge it.

## Contract (enforced by tests)

From `configs/independent.yaml`:

```yaml
banned_prospect_columns:
  - consensus_rank
  - rank
  - market_consensus_score
  - model_consensus_divergence
  - model_consensus_divergence_flag
  - confidence_tier
  - kiper_rank
  - mcshay_rank
  - pff_rank
  - any_analyst_rank

banned_files:
  - data/features/analyst_aggregate_2026.json
  - data/features/analyst_consensus_2026.json
  - data/features/trade_scenarios_expanded_2026.json

banned_imports:
  - src.models.benchmark
  - src.data.ingest_analyst_mocks
```

Any PR that re-introduces leakage fails `pytest tests/test_independence.py`.

## What remains as future work

- Full team-agent historical backtest (requires reconstructing per-year
  team profiles from contemporaneous public data)
- Confidence-tier recalibration from backtest hit rates
- Frontend UI badge/toggle for mode switch (API already supports it)
- Bilateral trade matching in the MC loop (currently records structural
  trade probability but doesn't mutate the schedule)
- More granular visit typing (top-30 / private workout / local day
  distinction currently collapsed to binary confirmed_visits)
- Pre-draft medical severity deeper than binary flags

None of these are blocking for the 2026-04-25 scoreboard run.
