# Independent team-agent draft model

## What this is

A 32-team-agent simulator that predicts the 2026 NFL Draft WITHOUT reading
any analyst mock picks, consensus rankings, or mock-derived trade priors.

Each pick is justifiable in team-logic terms:
- the team's structural needs, scheme, coach preferences
- the team's GM historical patterns (from real drafts, not mocks)
- the player's independent grade (Stage 1 ensembles + scouting features)
- the availability of better options at this exact slot
- a trade-incentive model grounded in historical pick-range rates

## What this is NOT

A consensus reproducer. The mocks are the scoreboard, not the fuel.

## Directory layout

```
src/models/independent/
  __init__.py          # module-level docstring with allowed/banned inputs
  player_value.py      # Layer A — team-agnostic grade
  team_fit.py          # Layer B — team-specific value
  availability.py      # Layer C — P(player available | pick slot)
  trade.py             # Layer D — structural trade logic
  run.py               # Monte Carlo entry point
  README.md            # this file
```

## Running

```bash
# Independent model (preferred)
python -m src.models.independent.run

# Benchmark (analyst-aware, for comparison)
python -m src.models.benchmark.run

# Independence guard tests
pytest tests/test_independence.py -v
```

## Contract

The set of banned inputs is declared in `configs/independent.yaml` and
enforced by `tests/test_independence.py`. That test is the canonical
source-of-truth: if you're unsure whether a change violates independence,
run `pytest tests/test_independence.py`.

Status: Section B scaffolded. Implementation lands in Sections C-D.
