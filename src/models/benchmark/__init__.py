"""Market / analyst-aware benchmark model.

Wraps the legacy stage2_game_theoretic pipeline. Retained for:
  - post-draft scoring against mock drafts
  - UI comparison mode
  - sanity checks on the independent model
  - backtesting one against the other

Anything in this namespace MAY consume analyst picks, consensus_rank,
mock-derived trade priors, etc. That's the point — it's the market mirror.

The independent model (src/models/independent/) must never import from here.
"""
