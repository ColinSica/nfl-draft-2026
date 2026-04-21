"""Layer C — availability.

MVP: exact board state (players already picked are unavailable). The
surrounding MC loop tracks which prospects have been taken, so the
availability check here is a plain set-difference against picks_made.

The more sophisticated variant — forecasting P(available at my slot)
given upstream teams' preferences — can be slotted in later without
changing the call signature.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def available_mask(prospects: pd.DataFrame,
                   picks_made: list[dict]) -> pd.Series:
    """Return a boolean Series: True if prospect hasn't been picked."""
    taken = {p["player"] for p in picks_made}
    return ~prospects["player"].isin(taken)


def estimate_availability(prospects: pd.DataFrame, pick_slot: int,
                          prior_picks: list[dict]) -> np.ndarray:
    """Numpy variant used by the runner. 1.0 if available, 0.0 if taken."""
    return available_mask(prospects, prior_picks).astype(float).to_numpy()
