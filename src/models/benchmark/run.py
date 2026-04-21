"""Entry point for the analyst-aware benchmark.

Thin wrapper around the legacy stage2_game_theoretic pipeline. This path
is explicitly allowed to consume mock consensus, analyst distributions,
mock-derived trade scenarios, etc. It exists for post-draft comparison
and nothing else.

Usage:
  python -m src.models.benchmark.run [--config configs/benchmark.yaml]
"""
from __future__ import annotations

import argparse
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[3]

def load_config(path: Path) -> dict:
    with path.open(encoding="utf-8") as fh:
        cfg = yaml.safe_load(fh)
    if cfg.get("mode") != "benchmark":
        raise ValueError(f"expected mode=benchmark, got {cfg.get('mode')!r}")
    return cfg

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="configs/benchmark.yaml")
    args = ap.parse_args()
    _cfg = load_config(ROOT / args.config)

    # Delegate to the existing Stage 2 entry-point. Section C/D will extract
    # the analyst-specific code paths here and remove them from shared code.
    from src.models import stage2_game_theoretic
    stage2_game_theoretic.main()
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
