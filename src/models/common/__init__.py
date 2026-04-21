"""Shared utilities used by BOTH independent and benchmark models.

Only truly factual, non-market-polluting helpers belong here:
  - team-agent schema loaders (reading team_agents_2026.json)
  - Stage 1 player-value board loaders (the ensembles themselves)
  - pick-value charts
  - historical draft/trade parsing

Anything that touches analyst picks / consensus_rank / mock distributions
belongs in benchmark/, not here.
"""
