"""Independence-guard tests.

These tests are the contract. Any PR that breaks them is a PR that
re-introduces analyst leakage into the independent model.
"""
from __future__ import annotations

import ast
import importlib
import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
INDEPENDENT_DIR = ROOT / "src/models/independent"
CONFIG_PATH = ROOT / "configs/independent.yaml"

def _cfg() -> dict:
    with CONFIG_PATH.open(encoding="utf-8") as fh:
        return yaml.safe_load(fh)

def _all_independent_py_files() -> list[Path]:
    return [p for p in INDEPENDENT_DIR.rglob("*.py") if p.name != "__init__.py"]

def test_config_exists():
    assert CONFIG_PATH.exists(), "configs/independent.yaml must exist"

def test_config_declares_banned_lists():
    cfg = _cfg()
    assert "banned_prospect_columns" in cfg, "config must declare banned_prospect_columns"
    assert "banned_files" in cfg, "config must declare banned_files"
    assert "banned_imports" in cfg, "config must declare banned_imports"

def test_independent_source_does_not_import_banned_modules():
    """Static AST check: no file under src/models/independent/ imports anything
    from the benchmark namespace or from analyst-mock ingestion."""
    cfg = _cfg()
    banned = set(cfg["banned_imports"])
    offenders = []
    for py in _all_independent_py_files():
        tree = ast.parse(py.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if any(alias.name.startswith(b) for b in banned):
                        offenders.append((py.name, alias.name))
            elif isinstance(node, ast.ImportFrom):
                mod = node.module or ""
                if any(mod.startswith(b) for b in banned):
                    offenders.append((py.name, mod))
    assert not offenders, f"banned imports in independent/: {offenders}"

def test_independent_source_does_not_reference_banned_columns():
    """Static string-search check: no banned column name appears as a literal
    in the independent sources. Catches DataFrame['consensus_rank'] leaks."""
    cfg = _cfg()
    banned_cols = cfg["banned_prospect_columns"]
    offenders = []
    for py in _all_independent_py_files():
        text = py.read_text(encoding="utf-8")
        for col in banned_cols:
            # require word-boundary-ish match — don't flag a column name that
            # appears only inside a longer identifier (e.g. 'rank' is too short
            # to flag without bounds)
            marker = f'"{col}"'
            marker2 = f"'{col}'"
            if marker in text or marker2 in text:
                offenders.append((py.name, col))
    assert not offenders, f"banned column reference in independent/: {offenders}"

def test_independent_source_does_not_reference_banned_files():
    cfg = _cfg()
    banned_files = cfg["banned_files"]
    offenders = []
    for py in _all_independent_py_files():
        text = py.read_text(encoding="utf-8")
        for rel in banned_files:
            basename = Path(rel).name
            if basename in text:
                offenders.append((py.name, rel))
    assert not offenders, f"banned file path referenced from independent/: {offenders}"

def test_independent_run_executes_cleanly():
    """The independent runner should execute end-to-end and write both the
    board and the audit log without ever touching analyst data."""
    for mod in list(sys.modules):
        if mod.startswith("src.models.independent"):
            del sys.modules[mod]
    from src.models.independent import run as runner
    # Cap sims to keep the test fast; production uses 500.
    rc = runner.main(argv=["--sims", "5", "--seed", "1"])
    assert rc == 0
    cfg = _cfg()
    audit = ROOT / cfg["outputs"]["independence_audit_log"]
    board = ROOT / cfg["outputs"]["predictions_csv"]
    assert audit.exists(), "expected independence_audit_log to be written"
    assert board.exists(), "expected predictions_csv to be written"

def test_independent_monte_carlo_outputs_exist():
    """After a full run the MC outputs should exist and be non-empty."""
    cfg = _cfg()
    mc = ROOT / cfg["outputs"]["monte_carlo_csv"]
    picks = (ROOT / cfg["outputs"]["predictions_csv"]).with_name(
        Path(cfg["outputs"]["predictions_csv"]).stem + "_picks.csv"
    )
    reasoning = ROOT / cfg["outputs"]["reasoning_json"]
    for p in (mc, picks, reasoning):
        if not p.exists():
            pytest.skip(f"full MC not yet run; {p.name} missing")
    import pandas as pd
    mc_df = pd.read_csv(mc)
    assert len(mc_df) > 0
    # Independent MC must not carry consensus_rank or analyst columns.
    suspicious = [c for c in mc_df.columns
                  if any(t in c.lower()
                         for t in ("consensus", "market", "analyst"))]
    assert not suspicious, f"analyst leakage in MC CSV: {suspicious}"


def test_independent_output_has_no_banned_columns():
    """The written predictions_independent.csv must not contain any
    analyst-derived column."""
    import pandas as pd
    cfg = _cfg()
    board = ROOT / cfg["outputs"]["predictions_csv"]
    if not board.exists():
        pytest.skip("board not built yet — run the pipeline first")
    df = pd.read_csv(board)
    banned = set(cfg["banned_prospect_columns"])
    leaks = [c for c in df.columns if c in banned]
    assert not leaks, f"banned columns present in independent output: {leaks}"
    # Defense in depth: no column with 'consensus' or 'market' or 'analyst' substring.
    suspicious = [c for c in df.columns
                  if any(tok in c.lower()
                         for tok in ("consensus", "market", "analyst"))]
    assert not suspicious, f"suspicious columns in independent output: {suspicious}"
