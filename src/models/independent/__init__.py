"""Independent team-agent draft model.

BANNED inputs (see tests/test_independence.py):
  - analyst mock picks
  - consensus_rank / rank / ADP
  - per-pick analyst distributions
  - mock-derived trade scenarios
  - scripted pick overrides based on mocks

ALLOWED inputs:
  - team profiles (structural: roster, cap, coaching, scheme)
  - extracted analyst *reasoning* tags (need signals, archetype fits,
    trade tendencies) — NOT analyst picks
  - Stage 1 ensembles trained only on factual/production/trait features
  - historical (real) draft and trade data
  - public visit data (typed, quality-weighted)
  - public medical / contract / depth-chart data

The final pick decision must be justifiable in team-logic terms alone.
"""
