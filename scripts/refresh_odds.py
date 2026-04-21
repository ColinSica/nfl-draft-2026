"""Refresh the Kalshi draft-odds cache and print a summary.

Usage:
  python scripts/refresh_odds.py
  python scripts/refresh_odds.py --dry-run
  python scripts/refresh_odds.py --anchors-only   # rebuild anchors from existing cache
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.data import ingest_odds_kalshi
from src.models.independent import odds_anchor


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true",
                    help="Fetch but don't write the cache file")
    ap.add_argument("--anchors-only", action="store_true",
                    help="Skip the API fetch, just rebuild anchors from cached JSON")
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args()

    if not args.anchors_only:
        try:
            ingest_odds_kalshi.fetch_and_cache(
                verbose=not args.quiet, dry_run=args.dry_run)
        except Exception as exc:
            print(f"[refresh_odds] Kalshi fetch failed: {exc}", file=sys.stderr)
            print("[refresh_odds] Check KALSHI_KEY_ID and KALSHI_PRIVATE_KEY_PATH in .env",
                  file=sys.stderr)
            return 1

    anchors = odds_anchor.load_anchors()
    if not anchors:
        print("[refresh_odds] no usable anchors built. "
              "Market parsing may need tuning to this event's titles.")
        return 2

    print(f"\n[refresh_odds] {len(anchors)} players with market anchors\n")
    print(f"{'Player':<30} {'P10':>6} {'P50':>6} {'P90':>6} {'E[pk]':>6} {'n':>3} {'conf':>5}")
    print("-" * 70)
    for p, a in sorted(anchors.items(), key=lambda x: x[1]["pick_p50"]):
        print(f"{p:<30} {a['pick_p10']:>6.1f} {a['pick_p50']:>6.1f} "
              f"{a['pick_p90']:>6.1f} {a['expected_pick']:>6.1f} "
              f"{a['n_markets']:>3d} {a['market_confidence']:>5.2f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
