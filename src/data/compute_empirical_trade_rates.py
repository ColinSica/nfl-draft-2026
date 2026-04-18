"""
Compute empirical R1 trade rates from data/raw/r1_trades_2021_2025.json.

Two outputs, both written to data/features/trade_empirical_2021_2025.json:

  per_pick_rate[slot]   — what fraction of the 5 drafts had this R1 slot
                           change hands (either pre-draft or draft-day).
                           Replaces the 3-bucket hardcoded function.

  per_team_rates[abbr]  — {"trade_up_rate": p, "trade_down_rate": p,
                           "n_trades_up": int, "n_trades_down": int,
                           "sample_size": 5}
                           Expressed as "times per 5-year window divided by
                           5" — i.e. roughly probability that the team moves
                           an R1 pick in a given year, per direction.
                           Teams not seen in the scraped data get None, and
                           the consumer falls back to the league base rate.

Also exposes:
  pick_slot_distribution_for_trade_up[origin_bucket] — where traded-up picks
                                                        came from (later
                                                        buckets). Used for
                                                        realistic partner
                                                        selection.
  per_pick_traded_in_direction[slot]                 — P(slot traded up) vs
                                                        P(slot traded down).

Limitations: 2021-2025 Wikipedia annotations do not distinguish draft-day
from pre-draft R1 trades; both show as "from Team" on the selecting team's
pick. We treat both as evidence of R1 trade propensity — a LAR pick that was
moved in March is still a LAR trade. This slightly over-attributes activity
but directionally matches real behaviour.
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
IN_JSON = ROOT / "data" / "raw" / "r1_trades_2021_2025.json"
OUT_JSON = ROOT / "data" / "features" / "trade_empirical_2021_2025.json"
OUT_JSON.parent.mkdir(parents=True, exist_ok=True)

ALL_TEAMS = {
    "ARI","ATL","BAL","BUF","CAR","CHI","CIN","CLE","DAL","DEN","DET","GB",
    "HOU","IND","JAX","KC","LAC","LAR","LV","MIA","MIN","NE","NO","NYG","NYJ",
    "PHI","PIT","SEA","SF","TB","TEN","WAS",
}


def main() -> None:
    if not IN_JSON.exists():
        raise SystemExit(f"Missing {IN_JSON}. Run scrape_r1_trades.py first.")

    data = json.loads(IN_JSON.read_text(encoding="utf-8"))
    trades = data["trades"]
    years = data["years"]
    n_years = len(years)

    # --- Per-pick slot rate ------------------------------------------------
    per_pick_traded_count: Counter[int] = Counter()
    per_pick_traded_up: Counter[int] = Counter()
    per_pick_traded_down: Counter[int] = Counter()
    for t in trades:
        slot = t["pick"]
        per_pick_traded_count[slot] += 1
        # direction from the slot's perspective:
        # Final team holds the slot — if they ACQUIRED it, the slot itself
        # was the TARGET of a trade-up (by the acquirer). So this slot is a
        # "trade-up destination" for the acquirer.
        per_pick_traded_up[slot] += 1

    per_pick_rate: dict[str, float] = {}
    for slot in range(1, 33):
        per_pick_rate[str(slot)] = per_pick_traded_count.get(slot, 0) / n_years

    # --- Per-team direction rates -----------------------------------------
    per_team_up: Counter[str] = Counter()      # team acquired an R1 slot
    per_team_down: Counter[str] = Counter()    # team gave up an R1 slot
    for t in trades:
        per_team_up[t["final_team"]] += 1
        per_team_down[t["original_team"]] += 1

    per_team_rates: dict[str, dict] = {}
    for team in sorted(ALL_TEAMS):
        n_up = per_team_up.get(team, 0)
        n_down = per_team_down.get(team, 0)
        per_team_rates[team] = {
            "n_trades_up":     n_up,
            "n_trades_down":   n_down,
            "trade_up_rate":   round(n_up / n_years, 3),
            "trade_down_rate": round(n_down / n_years, 3),
            "sample_years":    n_years,
            "has_signal":      (n_up + n_down) >= 1,
        }

    # --- Per-pick direction breakdown (for partner selection) -------------
    # For each slot bucket, what % of trades landed there as trade-ups vs
    # trade-downs (from the ORIGINAL team's perspective).
    bucket_totals: Counter[str] = Counter()
    for t in trades:
        slot = t["pick"]
        if slot <= 5:    b = "1-5"
        elif slot <= 10: b = "6-10"
        elif slot <= 15: b = "11-15"
        elif slot <= 20: b = "16-20"
        elif slot <= 25: b = "21-25"
        else:            b = "26-32"
        bucket_totals[b] += 1
    bucket_rates: dict[str, dict] = {}
    slot_counts_per_bucket = {"1-5": 5, "6-10": 5, "11-15": 5, "16-20": 5,
                              "21-25": 5, "26-32": 7}
    for bucket, n_slots in slot_counts_per_bucket.items():
        total_opps = n_slots * n_years
        n_trades = bucket_totals.get(bucket, 0)
        bucket_rates[bucket] = {
            "n_trades":    n_trades,
            "opportunities": total_opps,
            "rate":        round(n_trades / total_opps, 3),
        }

    # --- League-wide sanity check ------------------------------------------
    league_mean = len(trades) / n_years
    league_pct  = len(trades) / (n_years * 32)

    out = {
        "source":     str(IN_JSON.name),
        "n_years":    n_years,
        "years":      years,
        "n_trades":   len(trades),
        "league_avg_trades_per_year": round(league_mean, 2),
        "league_avg_rate_per_pick":   round(league_pct, 3),
        "per_pick_rate":       per_pick_rate,
        "per_team_rates":      per_team_rates,
        "per_bucket_rates":    bucket_rates,
    }
    OUT_JSON.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"Saved -> {OUT_JSON}")
    print(f"\nLeague baseline: {league_mean:.1f} R1 trades/yr, {league_pct:.1%} of picks move")
    print(f"\nPer-bucket trade rate:")
    for bucket, info in bucket_rates.items():
        print(f"  picks {bucket:<6}  {info['rate']:.0%}  ({info['n_trades']}/{info['opportunities']})")
    print(f"\nPer-team rates (sorted by activity):")
    teams_sorted = sorted(ALL_TEAMS,
                          key=lambda t: -(per_team_rates[t]["n_trades_up"]
                                          + per_team_rates[t]["n_trades_down"]))
    for t in teams_sorted[:20]:
        r = per_team_rates[t]
        sig = " " if r["has_signal"] else "*"  # * = no signal in 5 years
        print(f"  {t:<4}{sig} up={r['trade_up_rate']:.2f}({r['n_trades_up']}) "
              f"down={r['trade_down_rate']:.2f}({r['n_trades_down']})")
    no_signal = [t for t in ALL_TEAMS if not per_team_rates[t]["has_signal"]]
    if no_signal:
        print(f"\n  no trade signal 2021-2025 ({len(no_signal)}): {', '.join(no_signal)}")


if __name__ == "__main__":
    main()
