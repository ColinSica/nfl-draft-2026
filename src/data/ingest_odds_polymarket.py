"""Polymarket draft-odds ingestion.

Pulls live 2026 NFL Draft market prices from Polymarket's public Gamma API
and writes them to data/features/betting_odds_polymarket_2026.json in the
SAME normalized schema as the Kalshi ingester, so odds_anchor can blend
the two sources.

Auth: none required for reads (Gamma API is public JSON). The API key in
.env (POLYMARKET_API_KEY) only matters for trading, which we don't do.

Usage:
  python -m src.data.ingest_odds_polymarket
  python -m src.data.ingest_odds_polymarket --dry-run
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests

ROOT = Path(__file__).resolve().parents[2]
GAMMA_BASE = "https://gamma-api.polymarket.com"
CACHE_PATH = ROOT / "data/features/betting_odds_polymarket_2026.json"

# Curated list of event slugs we know carry 2026 NFL Draft markets.
# Discovered via a paginated scan of /events?active=true&closed=false.
# Keeping this explicit instead of a keyword scan makes the ingester
# deterministic and avoids accidentally pulling NBA/NHL draft markets.
DRAFT_EVENT_SLUGS = [
    # Pick-exact events (pick N where N = 1..10)
    "2026-pro-football-draft-1st-overall-pick",
    "nfl-draft-2026-2nd-overall-pick-792",
    "2026-pro-football-draft-3rd-overall-pick",
    "2026-pro-football-draft-4th-overall-pick",
    "2026-pro-football-draft-5th-overall-pick",
    "2026-pro-football-draft-6th-overall-pick",
    "2026-pro-football-draft-7th-overall-pick",
    "2026-pro-football-draft-8th-overall-pick",
    "2026-pro-football-draft-9th-overall-pick",
    "2026-pro-football-draft-10th-overall-pick",
    # Top-N player markets
    "2026-pro-football-draft-player-to-be-drafted-in-the-1st-round-374",
    "2026-pro-football-draft-player-to-be-drafted-top-3",
    "2026-pro-football-draft-player-to-be-drafted-top-5",
    "2026-pro-football-draft-player-to-be-drafted-top-10",
    # Team-to-draft-player markets (liquidity varies — auto-filter at parse)
    "2026-pro-football-draft-team-to-draft-ty-simpson",
    "2026-pro-football-draft-team-to-draft-arvell-reese",
    "2026-pro-football-draft-team-to-draft-jeremiyah-love",
    "2026-pro-football-draft-team-to-draft-jordyn-tyson",
    "2026-pro-football-draft-team-to-draft-david-bailey",
    "2026-pro-football-draft-team-to-draft-mansoor-delane",
    "2026-pro-football-draft-team-to-draft-makai-lemon",
    "2026-pro-football-draft-team-to-draft-omar-cooper-jr",
    "2026-pro-football-draft-team-to-draft-rueben-bain-jr",
    "2026-pro-football-draft-team-to-draft-sonny-styles",
    "2026-pro-football-draft-team-to-draft-kenyon-sadiq",
    "2026-pro-football-draft-team-to-draft-spencer-fano",
    "2026-pro-football-draft-team-to-draft-kc-concepcion",
    "2026-pro-football-draft-team-to-draft-jadarian-price",
    "2026-pro-football-draft-team-to-draft-caleb-downs",
    "2026-pro-football-draft-team-to-draft-carnell-tate",
    "2026-pro-football-draft-team-to-draft-francis-mauigoa",
    "2026-pro-football-draft-team-to-draft-garrett-nussmeier",
    "2026-pro-football-draft-team-to-draft-carson-beck",
    # Position-count O/U markets (informational — not used by anchor)
    "2026-pro-football-draft-number-of-qbs-drafted-ou-9pt5",
    "2026-pro-football-draft-number-of-rbs-drafted-ou-16pt5",
    "2026-pro-football-draft-number-of-wrs-drafted-ou",
    "2026-pro-football-draft-number-of-tes-drafted-ou-10pt5",
    # Single-player top-10 (one-off)
    "will-jeremiyah-love-go-top-10-in-the-2026-pro-football-draft",
    # 2nd QB
    "2026-pro-football-draft-2nd-qb-drafted",
    # Which teams will draft a QB in R1
    "which-teams-will-draft-a-qb-in-the-1st-round-of-the-2026-pro-football-draft",
    # Will 1st pick be a QB
    "will-the-1st-pick-in-the-2026-pro-football-draft-be-a-qb",
]


# City -> NFL code. Polymarket uses full city names (sometimes with ". Jr"
# suffix in player names, handled separately).
CITY_TO_CODE = {
    "arizona cardinals": "ARI", "atlanta falcons": "ATL", "baltimore ravens": "BAL",
    "buffalo bills": "BUF", "carolina panthers": "CAR", "chicago bears": "CHI",
    "cincinnati bengals": "CIN", "cleveland browns": "CLE", "dallas cowboys": "DAL",
    "denver broncos": "DEN", "detroit lions": "DET", "green bay packers": "GB",
    "houston texans": "HOU", "indianapolis colts": "IND", "jacksonville jaguars": "JAX",
    "kansas city chiefs": "KC", "las vegas raiders": "LV",
    "los angeles chargers": "LAC", "los angeles rams": "LAR",
    "miami dolphins": "MIA", "minnesota vikings": "MIN", "new england patriots": "NE",
    "new orleans saints": "NO", "new york giants": "NYG", "new york jets": "NYJ",
    "philadelphia eagles": "PHI", "pittsburgh steelers": "PIT",
    "san francisco 49ers": "SF", "seattle seahawks": "SEA",
    "tampa bay buccaneers": "TB", "tennessee titans": "TEN",
    "washington commanders": "WAS",
}

# Pick-exact event slug -> pick number
PICK_NUM_FROM_SLUG = {
    "2026-pro-football-draft-1st-overall-pick": 1,
    "nfl-draft-2026-2nd-overall-pick-792": 2,
    "2026-pro-football-draft-3rd-overall-pick": 3,
    "2026-pro-football-draft-4th-overall-pick": 4,
    "2026-pro-football-draft-5th-overall-pick": 5,
    "2026-pro-football-draft-6th-overall-pick": 6,
    "2026-pro-football-draft-7th-overall-pick": 7,
    "2026-pro-football-draft-8th-overall-pick": 8,
    "2026-pro-football-draft-9th-overall-pick": 9,
    "2026-pro-football-draft-10th-overall-pick": 10,
}

# Top-N event slug -> N
TOP_N_FROM_SLUG = {
    "2026-pro-football-draft-player-to-be-drafted-in-the-1st-round-374": 32,
    "2026-pro-football-draft-player-to-be-drafted-top-3": 3,
    "2026-pro-football-draft-player-to-be-drafted-top-5": 5,
    "2026-pro-football-draft-player-to-be-drafted-top-10": 10,
}


def _fetch_event(slug: str) -> dict | None:
    """Fetch one event by slug. Returns None if not found."""
    url = f"{GAMMA_BASE}/events/slug/{slug}"
    try:
        r = requests.get(url, timeout=20)
        if r.status_code == 200:
            return r.json()
        # Fall back to slug-as-query approach
        r2 = requests.get(f"{GAMMA_BASE}/events", params={"slug": slug}, timeout=20)
        if r2.status_code == 200:
            items = r2.json()
            return items[0] if items else None
    except requests.RequestException:
        return None
    return None


def _parse_prices(market: dict) -> float | None:
    """Return YES probability (0..1). Prefers last trade for liquid markets,
    otherwise uses bid/ask midpoint."""
    # Polymarket stores outcomePrices as a JSON-encoded string in some returns
    raw_prices = market.get("outcomePrices")
    yes_price = None
    if isinstance(raw_prices, str):
        try:
            parsed = json.loads(raw_prices)
            if isinstance(parsed, list) and len(parsed) >= 1:
                yes_price = float(parsed[0])
        except (ValueError, TypeError):
            pass
    elif isinstance(raw_prices, list) and len(raw_prices) >= 1:
        try:
            yes_price = float(raw_prices[0])
        except (ValueError, TypeError):
            pass

    last = market.get("lastTradePrice")
    ba = market.get("bestAsk")
    bb = market.get("bestBid")
    vol = float(market.get("volume") or 0)
    liq = float(market.get("liquidity") or 0)
    has_liquidity = vol > 100 or liq > 100

    try:
        if last is not None and has_liquidity:
            lp = float(last)
            if 0.0 < lp < 1.0:
                return lp
    except (ValueError, TypeError):
        pass

    try:
        if ba is not None and bb is not None:
            mid = (float(ba) + float(bb)) / 2.0
            if 0.0 < mid < 1.0:
                return mid
    except (ValueError, TypeError):
        pass

    if yes_price is not None and 0.0 < yes_price < 1.0:
        return yes_price

    return None


def _extract_player_from_question(question: str, slug: str) -> str | None:
    """For pick-exact and top-N events: question is 'Will <Player> be the
    first pick...' or 'Will <Player> be drafted in the top 10?'"""
    q = question or ""
    m = re.match(r"will\s+(.+?)\s+be\s+(the\s+)?", q, re.IGNORECASE)
    if m:
        return m.group(1).strip()
    return None


def _extract_team_from_question(question: str) -> str | None:
    """For team-landing events: each market asks 'Will <Team> draft <Player>?'"""
    q = (question or "").lower()
    for city_name, code in CITY_TO_CODE.items():
        if city_name in q:
            return code
    return None


def _player_from_team_slug(slug: str) -> str:
    """For team-to-draft-X events, the player name is embedded in the slug.
    '2026-pro-football-draft-team-to-draft-ty-simpson' -> 'Ty Simpson'"""
    tail = slug.replace("2026-pro-football-draft-team-to-draft-", "")
    tail = tail.replace("will-", "").replace("-go-top-10-in-the-2026-pro-football-draft", "")
    parts = tail.split("-")
    return " ".join(p.capitalize() for p in parts)


def fetch_and_cache(verbose: bool = True, dry_run: bool = False) -> dict:
    """Pull all known NFL Draft 2026 events from Polymarket, parse each market
    into the shared bound_type schema, write the cache."""
    all_markets: list[dict] = []
    events_fetched = 0

    for slug in DRAFT_EVENT_SLUGS:
        ev = _fetch_event(slug)
        if not ev:
            if verbose:
                print(f"[polymarket] event {slug} not found or fetch failed")
            continue
        events_fetched += 1
        markets = ev.get("markets") or []
        if verbose:
            print(f"[polymarket] event {slug}: {len(markets)} markets")

        for m in markets:
            yes = _parse_prices(m)
            if yes is None:
                continue
            vol = float(m.get("volume") or 0)
            liq = float(m.get("liquidity") or 0)
            question = m.get("question") or ""
            # Group item title often carries clean player name
            group_title = m.get("groupItemTitle") or ""

            base = {
                "ticker": f"POLY-{m.get('id')}",
                "title": question,
                "subtitle": group_title,
                "status": "active" if ev.get("active") else "closed",
                "yes_cents": yes * 100.0,
                "yes_prob": yes,
                "volume": vol,
                "open_interest": liq,  # Polymarket liquidity ~ Kalshi OI analogue
                "close_ts": ev.get("endDate"),
                "event_ticker": slug,
                "event_title": ev.get("title"),
            }

            parsed: dict | None = None

            # --- PICK-EXACT: slot 1..10 ---
            if slug in PICK_NUM_FROM_SLUG:
                pick_n = PICK_NUM_FROM_SLUG[slug]
                player = group_title or _extract_player_from_question(question, slug)
                if not player:
                    continue
                parsed = {**base, "player_raw": player.strip(), "bound_type": "exact",
                          "pick_bound": pick_n}

            # --- TOP-N ---
            elif slug in TOP_N_FROM_SLUG:
                n = TOP_N_FROM_SLUG[slug]
                player = group_title or _extract_player_from_question(question, slug)
                if not player:
                    continue
                parsed = {**base, "player_raw": player.strip(), "bound_type": "top_n",
                          "pick_bound": n}

            # --- TEAM-TO-DRAFT-PLAYER ---
            elif slug.startswith("2026-pro-football-draft-team-to-draft-"):
                player = _player_from_team_slug(slug)
                # The team is encoded in groupItemTitle (like "Las Vegas Raiders")
                # or in the question itself
                team_raw = (group_title or "").strip().lower()
                code = CITY_TO_CODE.get(team_raw) or _extract_team_from_question(question)
                if not code:
                    continue
                parsed = {**base, "player_raw": player, "bound_type": "team",
                          "team_code": code, "pick_bound": None}

            # --- SINGLE-PLAYER TOP-10 (Jeremiyah Love) ---
            elif slug == "will-jeremiyah-love-go-top-10-in-the-2026-pro-football-draft":
                # Each outcome here is just YES/NO — use the YES price.
                if yes < 0.01 or yes > 0.99:
                    continue
                parsed = {**base, "player_raw": "Jeremiyah Love", "bound_type": "top_n",
                          "pick_bound": 10}

            # Other info markets (QB/RB/WR counts, trades count, etc.) are
            # skipped — they inform position mix but aren't per-player anchors.

            if parsed:
                all_markets.append(parsed)

    out = {
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "source": "polymarket",
        "n_events": events_fetched,
        "n_markets": len(all_markets),
        "markets": all_markets,
    }

    if not dry_run:
        CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
        CACHE_PATH.write_text(json.dumps(out, indent=2), encoding="utf-8")
        if verbose:
            print(f"[polymarket] wrote {CACHE_PATH}")

    if verbose:
        from collections import Counter
        by_type = Counter(m["bound_type"] for m in all_markets)
        matched_team = sum(1 for m in all_markets if m.get("team_code"))
        print(f"[polymarket] parsed {len(all_markets)} markets across {events_fetched} events")
        print(f"[polymarket] by type: {dict(by_type)}")
        print(f"[polymarket] team-landing markets: {matched_team}")

    return out


def load_cached() -> dict:
    if not CACHE_PATH.exists():
        return {"markets": [], "fetched_at": None, "source": "polymarket"}
    return json.loads(CACHE_PATH.read_text(encoding="utf-8"))


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args(argv)
    try:
        fetch_and_cache(verbose=not args.quiet, dry_run=args.dry_run)
    except Exception as exc:
        print(f"[polymarket] ERROR: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
