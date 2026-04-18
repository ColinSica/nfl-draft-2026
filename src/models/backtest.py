"""
Stage-1 temporal backtest.

Extends train_stage1.py with an extra early fold (Fold 1) and adds two
baselines we can honestly compute from the data we have:

  Baseline A  position_median_pick : predict the median pick for each
                                      position group, using training rows only.
  Baseline B  simple_combine        : univariate OLS on a single clean feature
                                      (40_yard for SKILL/DEF, weight for OL,
                                      passing_yds for QB). Fallback to the
                                      position mean when the feature is null.

Honest caveat: the user's spec asks to compare against *consensus ADP* per
year. We have no archive of historical NFLMDD big-board snapshots, so that
baseline cannot be reconstructed from data we own. The two baselines here
capture "naive mean" and "single-feature regression" floors.

Outputs
-------
  data/backtest/backtest_results.csv   per-fold per-group per-model metrics
  stdout                                comparison table

Stage 2 (team assignment) backtest is deliberately skipped: we have no
historical visit or intel data from 2022/2023/2024 to simulate against.
"""

from __future__ import annotations

import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src" / "models"))
from train_stage1 import fit_ensemble, fit_qb_simple, predict_ensemble, load_group  # noqa: E402

warnings.filterwarnings("ignore")

BACKTEST_DIR = ROOT / "data" / "backtest"
BACKTEST_CSV = BACKTEST_DIR / "backtest_results.csv"

# 4 temporal folds per user spec
FOLDS = [
    ("2022", [2020, 2021], 2022),
    ("2023", [2020, 2021, 2022], 2023),
    ("2024", [2020, 2021, 2022, 2023], 2024),
    ("2025", [2020, 2021, 2022, 2023, 2024], 2025),
]

GROUPS = ("QB", "SKILL", "OL", "DEF")


def metrics(y_true: np.ndarray, y_pred: np.ndarray) -> dict:
    err = np.abs(y_pred - y_true)
    mae = float(np.mean(err))
    mae_rounds = float(np.mean(err / 32.0))  # 32 picks ≈ 1 round
    if len(y_true) >= 2 and np.ptp(y_pred) > 0:
        rho, _ = spearmanr(y_pred, y_true)
    else:
        rho = np.nan
    # % true top-32 captured by model's top-32
    if len(y_true) >= 32:
        true_top32 = set(np.argsort(y_true)[:32])
        pred_top32 = set(np.argsort(y_pred)[:32])
        top32_overlap = len(true_top32 & pred_top32) / 32.0
    else:
        top32_overlap = np.nan
    return {
        "mae_picks": mae, "mae_rounds": mae_rounds,
        "spearman": float(rho) if not np.isnan(rho) else np.nan,
        "top32_overlap": float(top32_overlap) if not np.isnan(top32_overlap) else np.nan,
    }


def baseline_position_median(X_train, y_train, meta_train, X_test, meta_test) -> np.ndarray:
    """Predict the median training-fold pick for each position group (no X use)."""
    # Use position_group if present in meta; else fall back to single median
    grp_col = None
    for c in ("position_group", "position"):
        if c in meta_train.columns:
            grp_col = c
            break
    if grp_col is None:
        med = float(np.median(y_train))
        return np.full(len(X_test), med)
    medians = meta_train.groupby(grp_col).apply(
        lambda df: float(np.median(y_train.loc[df.index]))).to_dict()
    overall = float(np.median(y_train))
    return np.array([medians.get(meta_test[grp_col].iloc[i], overall)
                     for i in range(len(meta_test))])


def baseline_single_feature(X_train, y_train, X_test, feature: str) -> np.ndarray:
    """Simple OLS on one feature. Returns training-mean when feature NaN."""
    if feature not in X_train.columns or X_train[feature].isna().all():
        return np.full(len(X_test), float(np.mean(y_train)))
    mask = X_train[feature].notna()
    if mask.sum() < 5:
        return np.full(len(X_test), float(np.mean(y_train)))
    x = X_train.loc[mask, feature].values.astype(float)
    y = y_train.loc[mask].values.astype(float)
    A = np.vstack([x, np.ones_like(x)]).T
    coef, intercept = np.linalg.lstsq(A, y, rcond=None)[0]
    mean_y = float(np.mean(y))
    xt = X_test[feature].fillna(x.mean()).values.astype(float)
    return coef * xt + intercept


def group_feature(group: str) -> str:
    return {"QB": "pass_yds", "SKILL": "40_yard",
            "OL": "weight", "DEF": "40_yard"}[group]


def main():
    BACKTEST_DIR.mkdir(parents=True, exist_ok=True)
    rows = []

    for group in GROUPS:
        X, y, meta = load_group(group)
        print(f"\n=== {group} ===  total rows: {len(X)}")

        for fold_name, train_years, test_year in FOLDS:
            train_mask = meta["year"].isin(train_years)
            test_mask = meta["year"] == test_year
            n_train = int(train_mask.sum())
            n_test = int(test_mask.sum())
            if n_train < 10 or n_test < 3:
                print(f"  fold {fold_name}: insufficient data (train={n_train} test={n_test}) — skipped")
                continue

            X_tr, X_te = X[train_mask], X[test_mask]
            y_tr, y_te = y[train_mask], y[test_mask]
            meta_tr, meta_te = meta[train_mask], meta[test_mask]

            # Ensemble / simple-QB Lasso
            fit_fn = fit_qb_simple if group == "QB" else fit_ensemble
            models = fit_fn(X_tr, y_tr)
            preds_m = predict_ensemble(models, X_te)
            m_model = metrics(y_te.values, preds_m)

            # Baseline A: position median
            preds_a = baseline_position_median(X_tr, y_tr, meta_tr, X_te, meta_te)
            m_base_a = metrics(y_te.values, preds_a)

            # Baseline B: single-feature OLS
            preds_b = baseline_single_feature(X_tr, y_tr, X_te, group_feature(group))
            m_base_b = metrics(y_te.values, preds_b)

            for name, m in (("ensemble", m_model),
                            ("baseline_pos_median", m_base_a),
                            ("baseline_single_feat", m_base_b)):
                rows.append({
                    "group": group, "fold": fold_name, "model": name,
                    "n_train": n_train, "n_test": n_test,
                    **m,
                })

            print(f"  fold {fold_name}: train={n_train} test={n_test}  "
                  f"ensemble MAE={m_model['mae_picks']:.1f}  rho={m_model['spearman']:.2f}  "
                  f"|  baseline_pos MAE={m_base_a['mae_picks']:.1f}  "
                  f"|  baseline_feat MAE={m_base_b['mae_picks']:.1f}")

    bt = pd.DataFrame(rows)
    bt.to_csv(BACKTEST_CSV, index=False)
    print(f"\nSaved -> {BACKTEST_CSV}")

    # Summary: mean metrics per (group, model)
    print("\n" + "=" * 70)
    print("BACKTEST SUMMARY — mean across folds")
    print("=" * 70)
    summary = (bt.groupby(["group", "model"])
                 [["mae_picks", "mae_rounds", "spearman", "top32_overlap"]]
                 .mean().reset_index())
    print(summary.round(2).to_string(index=False))

    # Flag folds where ensemble underperforms both baselines (model is hurting)
    print("\nFolds where ensemble underperforms BOTH baselines (by MAE):")
    flagged = []
    for (g, f), sub in bt.groupby(["group", "fold"]):
        ens_mae = sub[sub["model"] == "ensemble"]["mae_picks"].iloc[0]
        base_maes = sub[sub["model"] != "ensemble"]["mae_picks"].tolist()
        if base_maes and ens_mae > min(base_maes):
            best_base = sub.loc[sub["model"] != "ensemble", "mae_picks"].min()
            flagged.append((g, f, ens_mae, best_base))
    if flagged:
        for g, f, e, b in flagged:
            print(f"  {g:<6} fold {f}:  ensemble MAE={e:.1f}  "
                  f"best baseline MAE={b:.1f}  (gap={e-b:+.1f})")
    else:
        print("  (none — ensemble beats baselines on every fold)")


if __name__ == "__main__":
    main()
