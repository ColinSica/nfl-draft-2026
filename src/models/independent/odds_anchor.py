"""Odds-to-anchor conversion.

Given market data from multiple exchanges (Kalshi + Polymarket), builds a
per-player pick CDF and extracts:

  - pick_p10, pick_p50, pick_p90    (order statistics)
  - expected_pick                   (CDF mean)
  - market_confidence               (combined volume / open interest)

The CDF is constructed by sorting threshold points {(pick_bound, P(pick <= bound))}
and interpolating. Exact-pick markets contribute point masses; top-N markets
contribute CDF values; over-under lines contribute 1 - YES = P(pick <= N).

Market sources are merged at the market-list level: if Kalshi and Polymarket
both price Mendoza-at-1, both price points enter the CDF construction, and
market_confidence naturally scales with combined liquidity.

Handles noise by clamping to monotone and smoothing tiny inversions.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
CACHE_PATH = ROOT / "data/features/betting_odds_2026.json"                # Kalshi
POLYMARKET_CACHE_PATH = ROOT / "data/features/betting_odds_polymarket_2026.json"

# Pick grid for CDF interpolation (1..257).
_PICK_GRID = np.arange(1, 258)


# ---------- Name normalization for Polymarket matching ----------
# Polymarket's groupItemTitle is clean ("Fernando Mendoza") but may differ
# slightly from our prospects CSV. Use the same fuzzy logic as Kalshi.

_SUFFIX_RE = re.compile(r"\s+(jr|sr|ii|iii|iv|v)\.?$", re.IGNORECASE)
_PUNCT_RE = re.compile(r"[.,']")


def _stripped_key(name: str) -> str:
    n = re.sub(r"[^\w\s'\-.]", "", name or "").strip().lower()
    n = _SUFFIX_RE.sub("", n)
    n = _PUNCT_RE.sub("", n)
    return re.sub(r"\s+", " ", n).strip()


def _match_polymarket_to_prospect(raw: str, prospect_names: set[str],
                                   key_map: dict[str, str]) -> str | None:
    if not raw:
        return None
    low = raw.strip().lower()
    # Fast path: exact name match
    for p in prospect_names:
        if p.lower() == low:
            return p
    # Stripped-key match
    k = _stripped_key(raw)
    if k in key_map:
        return key_map[k]
    return None


def _load_polymarket_normalized() -> list[dict]:
    """Load Polymarket markets and attach `player` (matched to prospects CSV)
    + `matched_to_prospect` flag so they flow through the same filter as
    Kalshi markets."""
    if not POLYMARKET_CACHE_PATH.exists():
        return []
    try:
        data = json.loads(POLYMARKET_CACHE_PATH.read_text(encoding="utf-8"))
    except Exception:
        return []

    # Load prospects CSV for matching
    import pandas as pd
    pros_path = ROOT / "data/processed/prospects_2026_enriched.csv"
    prospect_names: set[str] = set()
    key_map: dict[str, str] = {}
    if pros_path.exists():
        names = pd.read_csv(pros_path, usecols=["player"])["player"].dropna().astype(str).tolist()
        prospect_names = set(names)
        for n in names:
            key_map.setdefault(_stripped_key(n), n)

    out: list[dict] = []
    for m in data.get("markets", []) or []:
        raw = m.get("player_raw")
        matched = _match_polymarket_to_prospect(raw, prospect_names, key_map) if raw else None
        m2 = {**m, "player": matched or raw, "matched_to_prospect": bool(matched),
              "_source": "polymarket"}
        out.append(m2)
    return out


def _load_all_markets(cache: dict | None = None) -> list[dict]:
    """Merge Kalshi + Polymarket markets into one list. Each market carries a
    `_source` tag so downstream can weight by exchange if needed."""
    if cache is None:
        if CACHE_PATH.exists():
            cache = json.loads(CACHE_PATH.read_text(encoding="utf-8"))
        else:
            cache = {"markets": []}
    kalshi_markets = [{**m, "_source": "kalshi"} for m in (cache.get("markets") or [])]
    poly_markets = _load_polymarket_normalized()
    return kalshi_markets + poly_markets


def _build_cdf_points(markets: list[dict]) -> list[tuple[float, float]]:
    """Return (pick_bound, P(pick <= bound)) points combining:
      - top_n markets:   direct CDF observation — P(pick <= N) = yes_prob
      - over markets:    P(pick <= N) = 1 - yes_prob
      - exact markets:   P(pick = N) = yes_prob — accumulate into running CDF
    Final points combine the three sources taking MAX at each bound; the
    caller then enforces monotone non-decreasing on the grid.
    """
    exact_pmf: dict[int, float] = {}
    threshold_pts: list[tuple[float, float]] = []

    for m in markets:
        bt = m.get("bound_type")
        n = m.get("pick_bound")
        yes = m.get("yes_prob")
        if n is None or yes is None:
            continue
        n_f = float(n)
        yes_f = float(yes)
        if bt == "exact":
            k = int(n_f)
            exact_pmf[k] = max(exact_pmf.get(k, 0.0), yes_f)
        elif bt == "top_n":
            threshold_pts.append((n_f, yes_f))
        elif bt == "over":
            threshold_pts.append((n_f, 1.0 - yes_f))

    exact_cdf_pts: list[tuple[float, float]] = []
    if exact_pmf:
        running = 0.0
        for k in sorted(exact_pmf.keys()):
            running = min(1.0, running + exact_pmf[k])
            exact_cdf_pts.append((float(k), running))

    combined: dict[float, float] = {}
    for k, v in exact_cdf_pts + threshold_pts:
        combined[k] = max(combined.get(k, 0.0), float(v))
    return sorted(combined.items())


def _monotone_cdf(points: list[tuple[float, float]]) -> np.ndarray:
    """Return a CDF over _PICK_GRID (length 257) clamped to monotone non-decreasing."""
    if not points:
        return np.zeros_like(_PICK_GRID, dtype=float)
    xs = np.array([p[0] for p in points])
    ys = np.array([p[1] for p in points])
    # Aggregate duplicates by taking max (favor higher-confidence markets)
    uniq: dict[float, float] = {}
    for x, y in zip(xs, ys):
        uniq[x] = max(uniq.get(x, 0.0), y)
    xs = np.array(sorted(uniq.keys()))
    ys = np.array([uniq[x] for x in xs])

    # Enforce monotone non-decreasing on the raw observations.
    for i in range(1, len(ys)):
        if ys[i] < ys[i - 1]:
            ys[i] = ys[i - 1]

    # Anchor left (before first observed bound) at 0 and right (>= 257) at 1.
    xs_full = np.concatenate(([0.5], xs, [257.0]))
    ys_full = np.concatenate(([0.0], ys, [1.0]))

    cdf = np.interp(_PICK_GRID.astype(float), xs_full, ys_full)
    cdf = np.clip(cdf, 0.0, 1.0)
    # Final monotone pass over grid
    np.maximum.accumulate(cdf, out=cdf)
    return cdf


def _quantile(cdf: np.ndarray, q: float) -> float:
    idx = np.searchsorted(cdf, q, side="left")
    return float(_PICK_GRID[min(idx, len(_PICK_GRID) - 1)])


def _expected_pick(cdf: np.ndarray) -> float:
    # E[X] = sum_{k>=1} P(X >= k) = sum_{k>=1} (1 - CDF(k-1))
    survival = 1.0 - np.concatenate(([0.0], cdf[:-1]))
    return float(survival.sum())


def build_player_anchors(cache: dict | None = None) -> dict[str, dict]:
    """Return {player_name -> {pick_p10, pick_p50, pick_p90, expected_pick,
    cdf, n_markets, market_confidence}}.

    Markets are loaded from BOTH Kalshi and Polymarket and merged into a
    combined CDF per player. Only includes players whose combined markets
    produced a non-trivial CDF.
    """
    all_markets = _load_all_markets(cache)
    by_player: dict[str, list[dict]] = {}
    for m in all_markets:
        if not m.get("matched_to_prospect"):
            continue
        p = m.get("player")
        if not p:
            continue
        by_player.setdefault(p, []).append(m)

    # Liquidity reliability filter — require per-market OI+volume threshold
    # so we only trust market signals with real trading interest behind them.
    # Markets below the floor are excluded from CDF construction; if a player
    # has NO markets meeting the floor, the player is dropped entirely.
    #
    # Per-exchange thresholds: Polymarket lists every player on pick-exact
    # events as a placeholder market, most with <$100 in volume. These stale
    # seed prices (bestAsk/lastTrade on never-traded YES tokens) distort the
    # CDF. Kalshi's markets are more uniformly thick.
    MIN_KALSHI = 50       # dollars OI + volume
    MIN_POLYMARKET = 300  # stricter — skip placeholder/seed markets

    def _passes_liquidity(m: dict) -> bool:
        total = float(m.get("open_interest") or 0) + float(m.get("volume") or 0)
        floor = MIN_POLYMARKET if m.get("_source") == "polymarket" else MIN_KALSHI
        return total >= floor

    out: dict[str, dict] = {}
    for player, mkts in by_player.items():
        # Filter to markets with enough liquidity (per-exchange floor)
        liquid = [m for m in mkts if _passes_liquidity(m)]
        if not liquid:
            continue
        # Drop dust — players with only 1-cent quotes and no threshold coverage.
        # Require EITHER a top_n/over market (which pins the CDF shape) OR at
        # least one exact-pick market with yes_prob >= 3%.
        has_threshold = any(m.get("bound_type") in ("top_n", "over") for m in liquid)
        max_exact = max((float(m.get("yes_prob") or 0)
                         for m in liquid if m.get("bound_type") == "exact"),
                        default=0.0)
        if not has_threshold and max_exact < 0.03:
            continue

        pts = _build_cdf_points(liquid)
        if not pts:
            continue
        cdf = _monotone_cdf(pts)
        if cdf[-1] < 0.10:
            continue
        mkts = liquid  # use only liquid markets for volume aggregates
        volume = sum(float(m.get("volume") or 0) for m in mkts)
        oi = sum(float(m.get("open_interest") or 0) for m in mkts)
        n_kalshi = sum(1 for m in mkts if m.get("_source") == "kalshi")
        n_poly = sum(1 for m in mkts if m.get("_source") == "polymarket")
        out[player] = {
            "pick_p10": _quantile(cdf, 0.10),
            "pick_p50": _quantile(cdf, 0.50),
            "pick_p90": _quantile(cdf, 0.90),
            "expected_pick": _expected_pick(cdf),
            "n_markets": len(mkts),
            "n_kalshi_markets": n_kalshi,
            "n_polymarket_markets": n_poly,
            "market_confidence": min(1.0, (volume + oi) / 5000.0),
            "cdf_sample": {int(k): float(cdf[k - 1]) for k in (1, 5, 10, 20, 32, 64, 100)},
            "source": "pick_cdf",
        }

    # ---- FALLBACK: fill in players who only have position-rank markets ----
    # These players don't have OU or exact-pick coverage but DO have "Will X
    # be the Nth at POS drafted?" markets. Convert via _POS_RANK_TO_PICK.
    pos_rank_anchors = build_position_rank_anchors(cache)
    for player, d in pos_rank_anchors.items():
        if player in out:
            continue
        pa = float(d["pick_anchor"])
        # Treat the pick_anchor as a soft P50 with wide band (pos-rank is
        # less precise than direct pick markets).
        p10 = max(1.0, pa * 0.65)
        p90 = min(257.0, pa * 1.55)
        out[player] = {
            "pick_p10": p10,
            "pick_p50": pa,
            "pick_p90": p90,
            "expected_pick": pa,
            "n_markets": d["n_markets"],
            "market_confidence": float(d["confidence"]) * 0.6,  # discounted vs direct
            "cdf_sample": {},
            "source": "pos_rank_fallback",
        }
    return out


def load_anchors() -> dict[str, dict]:
    """Load fresh anchors from the cached odds file."""
    return build_player_anchors()


# ---------- team-landing priors ----------

# Historical position-rank → pick distribution. Used to convert "Nth at position"
# Kalshi markets into pick-position anchors. Mirrors player_value.POSITION_TOP_PICKS.
_POS_RANK_TO_PICK = {
    "QB":   [1, 25, 55, 90, 150],
    "OT":   [6, 12, 22, 40, 75],
    "OL":   [6, 12, 22, 40, 75],
    "IOL":  [16, 38, 60, 100, 170],
    "EDGE": [3, 9, 18, 32, 55],
    "WR":   [7, 14, 22, 40, 75],
    "RB":   [5, 35, 75, 125, 200],
    "CB":   [10, 18, 32, 60, 100],
    "DB":   [10, 18, 32, 60, 100],
    "S":    [8, 22, 50, 95, 160],
    "LB":   [2, 22, 50, 90, 150],
    "DL":   [8, 20, 42, 80, 135],
    "DT":   [8, 20, 42, 80, 135],
    "TE":   [17, 40, 75, 130, 200],
}


def build_team_landing_priors(cache: dict | None = None,
                               min_markets: int = 4) -> dict[str, dict]:
    """Return {player: {
        "team_probs": {team_code: normalized_prob},
        "raw_sum": unnormalized sum,
        "confidence": 0..1 from volume/OI,
        "n_teams": count
    }}.

    Kalshi prices each team-market independently; the raw sum across 32 teams
    is usually 0.7-1.1 (depending on overround and player-is-drafted probability).
    We normalize so probs sum to 1 (conditional on being drafted).
    """
    # Merge Kalshi + Polymarket team-landing markets
    all_markets = _load_all_markets(cache)
    by_player: dict[str, list[dict]] = {}
    for m in all_markets:
        if m.get("bound_type") != "team":
            continue
        if not m.get("matched_to_prospect"):
            continue
        p = m.get("player")
        if not p:
            continue
        by_player.setdefault(p, []).append(m)

    out: dict[str, dict] = {}
    for player, mkts in by_player.items():
        if len(mkts) < min_markets:
            continue
        raw: dict[str, float] = {}
        oi_total = 0.0
        vol_total = 0.0
        for m in mkts:
            tc = m.get("team_code")
            yp = float(m.get("yes_prob") or 0.0)
            if not tc:
                continue
            raw[tc] = raw.get(tc, 0.0) + yp
            oi_total += float(m.get("open_interest") or 0.0)
            vol_total += float(m.get("volume") or 0.0)
        s = sum(raw.values())
        if s <= 0:
            continue
        normalized = {tc: v / s for tc, v in raw.items()}
        out[player] = {
            "team_probs": normalized,
            "raw_sum": s,
            "n_teams": len(raw),
            "confidence": min(1.0, (oi_total + vol_total) / 10000.0),
        }
    return out


def build_team_pick1_priors(cache: dict | None = None) -> dict[str, float]:
    """Return {team_code: normalized_prob_of_having_pick_1}."""
    if cache is None:
        if not CACHE_PATH.exists():
            return {}
        cache = json.loads(CACHE_PATH.read_text(encoding="utf-8"))
    raw: dict[str, float] = {}
    for m in cache.get("markets", []) or []:
        if m.get("bound_type") != "team_pick1":
            continue
        tc = m.get("team_code")
        if not tc:
            continue
        raw[tc] = max(raw.get(tc, 0.0), float(m.get("yes_prob") or 0.0))
    s = sum(raw.values())
    if s <= 0:
        return {}
    return {tc: v / s for tc, v in raw.items()}


def build_position_rank_anchors(cache: dict | None = None,
                                 min_markets: int = 2) -> dict[str, dict]:
    """For players not covered by OU markets but with position-rank markets,
    compute an expected rank at position and convert to a pick anchor.

    E[rank_at_pos] = sum_N N * P(Nth at position)
    pick_anchor = interpolate _POS_RANK_TO_PICK[position] at E[rank].

    Returns {player: {"position": POS, "expected_rank": E, "pick_anchor": X,
                      "n_markets": n, "confidence": c}}.
    """
    if cache is None:
        if not CACHE_PATH.exists():
            return {}
        cache = json.loads(CACHE_PATH.read_text(encoding="utf-8"))

    by_player: dict[str, list[dict]] = {}
    for m in cache.get("markets", []) or []:
        if m.get("bound_type") != "pos_rank":
            continue
        if not m.get("matched_to_prospect"):
            continue
        p = m.get("player")
        if not p:
            continue
        by_player.setdefault(p, []).append(m)

    out: dict[str, dict] = {}
    for player, mkts in by_player.items():
        if len(mkts) < min_markets:
            continue
        # Group by (position, rank), take max yes_prob per (to combine dupes)
        rank_probs: dict[int, float] = {}
        pos_of = None
        for m in mkts:
            r = m.get("pos_rank")
            if r is None:
                continue
            pos_of = m.get("position") or pos_of
            rank_probs[int(r)] = max(rank_probs.get(int(r), 0.0),
                                      float(m.get("yes_prob") or 0.0))
        if not rank_probs or not pos_of:
            continue
        s = sum(rank_probs.values())
        if s <= 0:
            continue
        # Expected rank (weighted mean) — capped at last observed rank
        exp_rank = sum(r * (p / s) for r, p in rank_probs.items())
        # Convert to pick using position table
        anchors = _POS_RANK_TO_PICK.get(pos_of, [15, 35, 65, 110, 180])
        rank_pts = [1, 2, 3, 4, 5]
        pick_anchor = float(np.interp(min(max(exp_rank, 1.0), 5.0),
                                       rank_pts, anchors))
        oi_total = sum(float(m.get("open_interest") or 0.0) for m in mkts)
        out[player] = {
            "position": pos_of,
            "expected_rank": exp_rank,
            "pick_anchor": pick_anchor,
            "n_markets": len(mkts),
            "confidence": min(1.0, oi_total / 2000.0),
        }
    return out


def build_r1_position_counts(cache: dict | None = None) -> dict[str, float]:
    """Return {position: expected_R1_count} from CAT markets.
    P(count >= K) for each K → E[count] = sum_K P(count >= K)."""
    if cache is None:
        if not CACHE_PATH.exists():
            return {}
        cache = json.loads(CACHE_PATH.read_text(encoding="utf-8"))

    by_pos: dict[str, dict[int, float]] = {}
    for m in cache.get("markets", []) or []:
        if m.get("bound_type") != "pos_count":
            continue
        pos = m.get("position")
        k = m.get("pos_count_min")
        if not pos or k is None:
            continue
        by_pos.setdefault(pos, {})[int(k)] = float(m.get("yes_prob") or 0.0)

    out: dict[str, float] = {}
    for pos, probs in by_pos.items():
        # E[X] = sum P(X >= k) for k=1,2,...
        # We have entries at arbitrary k. Fill the gaps assuming monotone decrease.
        if not probs:
            continue
        ks = sorted(probs.keys())
        # For every k from 1..max, interpolate
        exp = 0.0
        max_k = max(ks)
        for k in range(1, max_k + 1):
            if k in probs:
                exp += probs[k]
            else:
                # linear interp between neighboring observed ks
                lo = max([kk for kk in ks if kk < k], default=None)
                hi = min([kk for kk in ks if kk > k], default=None)
                if lo is not None and hi is not None:
                    w = (k - lo) / (hi - lo)
                    exp += (1 - w) * probs[lo] + w * probs[hi]
                elif lo is not None:
                    exp += probs[lo]
                elif hi is not None:
                    exp += probs[hi]
        out[pos] = exp
    return out


if __name__ == "__main__":
    import sys
    anchors = load_anchors()
    print(f"[odds_anchor] built anchors for {len(anchors)} players")
    for p, a in sorted(anchors.items(), key=lambda x: x[1]["pick_p50"])[:40]:
        print(f"  {p:<30} P50={a['pick_p50']:>5.1f}  "
              f"E={a['expected_pick']:>5.1f}  "
              f"[{a['pick_p10']:>4.1f}-{a['pick_p90']:>5.1f}]  "
              f"n={a['n_markets']}  conf={a['market_confidence']:.2f}")
