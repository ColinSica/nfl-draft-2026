"""
Phase 7 (#16, #17) — aggregate daily live-intel scrapes into a single
versioned, multi-source analyst aggregate file.

Reads any files matching these patterns under data/live/:
  visits_<source>_<YYYY-MM-DD>.json         -> team visit signals
  betting_odds_<source>_<YYYY-MM-DD>.json   -> market odds per prospect
  stock_moves_<source>_<YYYY-MM-DD>.json    -> daily stock direction

Produces:
  data/features/analyst_aggregate_2026.json

Schema:
{
  "_meta": {"generated_at": "<iso-8601>", "latest_intel_date": "YYYY-MM-DD",
            "sources": {"visits": [...], "betting_odds": [...],
                        "stock_moves": [...]}},
  "players": {
    "<player>": {
      "visits": {"confirmed_teams": [...], "cancelled_flag": 0|1,
                 "source_count": int, "per_source": {...}},
      "market": {"best_american_odds": int, "best_implied_prob": float,
                 "avg_implied_prob": float, "source_count": int},
      "stock_moves": {"net_daily": int, "source_count": int},
      "freshness": {"latest_signal_date": "YYYY-MM-DD",
                     "days_stale": int}
    },
    ...
  }
}

Aggregation rules:
  - Visits: UNION of teams across sources; cancelled_flag = 1 if ANY source
    reports cancellation (conservative — signals flake).
  - Market: best (longest) American odds across sources; implied prob is min
    when computed from best odds; avg across sources for smoothing.
  - Stock moves: sum of daily directions (-1/0/+1) across sources.
  - Freshness: date in filename; stale > 2 days prompts a warning.
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LIVE = ROOT / "data" / "live"
FEATURES = ROOT / "data" / "features"
FEATURES.mkdir(parents=True, exist_ok=True)

OUT = FEATURES / "analyst_aggregate_2026.json"
FNAME_RX = re.compile(r"^(?P<kind>visits|betting_odds|stock_moves)_"
                       r"(?P<source>[a-zA-Z0-9]+)_"
                       r"(?P<date>\d{4}-\d{2}-\d{2})\.json$")

TODAY = datetime.now(timezone.utc).strftime("%Y-%m-%d")


def scan_intel_files() -> dict[str, list[tuple[str, Path]]]:
    """Group intel files by kind: {visits: [(source, path), ...], ...}."""
    out: dict[str, list[tuple[str, Path]]] = {
        "visits": [], "betting_odds": [], "stock_moves": []
    }
    for p in sorted(LIVE.glob("*.json")):
        m = FNAME_RX.match(p.name)
        if not m:
            continue
        out[m.group("kind")].append((m.group("source"), p))
    return out


def _latest_date_in_group(files: list[tuple[str, Path]]) -> str:
    """Return the latest YYYY-MM-DD suffix in a group (empty string if none)."""
    if not files:
        return ""
    dates = []
    for _, p in files:
        m = FNAME_RX.match(p.name)
        if m:
            dates.append(m.group("date"))
    return max(dates) if dates else ""


def aggregate_visits(files: list[tuple[str, Path]]) -> dict:
    """Union of confirmed teams per player; cancelled = ANY source says 1."""
    players: dict[str, dict] = {}
    for source, path in files:
        try:
            d = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, FileNotFoundError):
            continue
        if isinstance(d, list) or not d:
            continue
        for name, info in d.items():
            p = players.setdefault(name, {
                "confirmed_teams": set(),
                "cancelled_flag": 0,
                "source_count": 0,
                "per_source": {},
            })
            teams = list(info.get("teams_visited") or [])
            flag = int(info.get("cancelled_visit_flag") or 0)
            p["confirmed_teams"].update(teams)
            p["cancelled_flag"] = max(p["cancelled_flag"], flag)
            p["source_count"] += 1
            p["per_source"][source] = {"teams": teams, "cancelled_flag": flag}
    for name, info in players.items():
        info["confirmed_teams"] = sorted(info["confirmed_teams"])
    return players


def aggregate_market(files: list[tuple[str, Path]]) -> dict:
    players: dict[str, dict] = {}
    for source, path in files:
        try:
            d = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, FileNotFoundError):
            continue
        if not isinstance(d, dict):
            continue
        for name, info in d.items():
            odds = info.get("american_odds")
            ip = info.get("implied_prob")
            p = players.setdefault(name, {
                "best_american_odds": None,
                "best_implied_prob":  None,
                "avg_implied_prob":   None,
                "_sum": 0.0,
                "source_count": 0,
                "per_source": {},
            })
            p["per_source"][source] = {"american_odds": odds, "implied_prob": ip}
            if ip is not None:
                p["_sum"] += float(ip)
                p["source_count"] += 1
                if p["best_implied_prob"] is None or ip < p["best_implied_prob"]:
                    p["best_implied_prob"] = ip
                    p["best_american_odds"] = odds
    for name, info in players.items():
        if info["source_count"] > 0:
            info["avg_implied_prob"] = info["_sum"] / info["source_count"]
        del info["_sum"]
    return players


def aggregate_stock(files: list[tuple[str, Path]]) -> dict:
    players: dict[str, dict] = {}
    for source, path in files:
        try:
            d = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, FileNotFoundError):
            continue
        if not isinstance(d, dict):
            continue
        for name, info in d.items():
            direction = int(info.get("stock_direction_daily") or 0)
            p = players.setdefault(name, {
                "net_daily": 0,
                "source_count": 0,
                "per_source": {},
            })
            p["net_daily"] += direction
            p["source_count"] += 1
            p["per_source"][source] = {"stock_direction_daily": direction}
    return players


def main() -> None:
    groups = scan_intel_files()

    visits_data = aggregate_visits(groups["visits"])
    market_data = aggregate_market(groups["betting_odds"])
    stock_data  = aggregate_stock(groups["stock_moves"])

    latest_dates = {
        "visits":      _latest_date_in_group(groups["visits"]),
        "betting_odds":_latest_date_in_group(groups["betting_odds"]),
        "stock_moves": _latest_date_in_group(groups["stock_moves"]),
    }
    latest = max([d for d in latest_dates.values() if d], default="")

    all_players = (set(visits_data) | set(market_data) | set(stock_data))
    players: dict[str, dict] = {}
    for name in sorted(all_players):
        entry: dict = {}
        if name in visits_data:
            entry["visits"] = visits_data[name]
        if name in market_data:
            entry["market"] = market_data[name]
        if name in stock_data:
            entry["stock_moves"] = stock_data[name]
        # Staleness
        if latest:
            try:
                delta = (datetime.strptime(TODAY, "%Y-%m-%d")
                         - datetime.strptime(latest, "%Y-%m-%d")).days
            except ValueError:
                delta = 0
            entry["freshness"] = {
                "latest_signal_date": latest,
                "days_stale": delta,
            }
        players[name] = entry

    meta = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "latest_intel_date": latest,
        "sources": {
            k: [s for s, _ in v] for k, v in groups.items()
        },
        "per_kind_latest_date": latest_dates,
        "player_count": len(players),
    }

    out = {"_meta": meta, "players": players}
    OUT.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"Saved -> {OUT}")
    print(f"  players: {len(players)}")
    print(f"  latest intel date: {latest}  (today={TODAY})")
    print(f"  sources: {meta['sources']}")
    if latest:
        stale = (datetime.strptime(TODAY, "%Y-%m-%d")
                 - datetime.strptime(latest, "%Y-%m-%d")).days
        if stale > 2:
            print(f"  [WARN] intel is {stale} days stale")


if __name__ == "__main__":
    main()
