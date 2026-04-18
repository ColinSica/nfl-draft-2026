"""
Stage-1 training: position-specific ensemble regressors predicting draft pick.

Per group (QB / SKILL / OL / DEF):
  - Temporal CV: 3 expanding-window folds
      fold A: train 2020-2022, test 2023
      fold B: train 2020-2023, test 2024
      fold C: train 2020-2024, test 2025
  - Preprocessing: missingness flags + median imputation (fit on train only)
  - Models: RandomForest (0.4) + XGBoost (0.4) + Ridge (0.2)
  - Metrics per fold: MAE, Spearman rho on pick number
  - After CV, fit a final ensemble on all 2020-2025 rows and pickle
  - SHAP top-10 features from the XGBoost component of the final model

Outputs
-------
  models/{group}_ensemble.pkl   {rf, xgb, ridge, imputer, feature_cols, medians}
  models/_stage1_results.csv    per-fold MAE + Spearman
  models/_stage1_shap.csv       top-10 features per group with mean |SHAP|
"""

from __future__ import annotations

import pickle
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import Ridge
from sklearn.preprocessing import StandardScaler

import xgboost as xgb
import shap
from sklearn.linear_model import Lasso

# Features used by the stripped-down QB model (user-flagged from backtest:
# the 37-feature ensemble was losing to a univariate OLS baseline on 3 of 4
# folds with only 71 training rows). Note: consensus_rank and
# betting_implied_prob, which the user also requested, are pre-draft
# scouting signals not available in the historical training set, so they're
# omitted from training. They get blended back in at inference time via
# predict_2026.py's consensus-rank weighting.
QB_SIMPLE_FEATURES = ["pass_yds", "age", "height", "weight", "years_in_college"]

warnings.filterwarnings("ignore", category=UserWarning)
warnings.filterwarnings("ignore", category=FutureWarning)

ROOT = Path(__file__).resolve().parents[2]
FEATURES_DIR = ROOT / "data" / "features"
MODELS_DIR = ROOT / "models"

GROUPS = ("QB", "SKILL", "OL", "DEF")
FOLDS = [
    ("2023", [2020, 2021, 2022], 2023),
    ("2024", [2020, 2021, 2022, 2023], 2024),
    ("2025", [2020, 2021, 2022, 2023, 2024], 2025),
]
WEIGHTS = {"rf": 0.4, "xgb": 0.4, "ridge": 0.2}


def add_missingness_flags(X: pd.DataFrame) -> pd.DataFrame:
    """Append boolean 'miss_{col}' flags for each column that has any nulls."""
    flags = {}
    for c in X.columns:
        if X[c].isna().any():
            flags[f"miss_{c}"] = X[c].isna().astype(int)
    if flags:
        return pd.concat([X, pd.DataFrame(flags, index=X.index)], axis=1)
    return X


def preprocess_fit(X_train: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    X_flagged = add_missingness_flags(X_train)
    medians = X_flagged.median(numeric_only=True)
    X_filled = X_flagged.fillna(medians)
    # Drop any column that is still fully NaN (e.g. all-missing in this fold)
    all_nan = X_filled.columns[X_filled.isna().all()].tolist()
    if all_nan:
        X_filled = X_filled.drop(columns=all_nan)
    feature_cols = X_filled.columns.tolist()
    # Ridge needs scaled input; keep an optional scaler
    scaler = StandardScaler().fit(X_filled.values)
    return X_filled, {
        "medians": medians.to_dict(),
        "feature_cols": feature_cols,
        "dropped_all_nan": all_nan,
        "scaler": scaler,
    }


def preprocess_transform(X_test: pd.DataFrame, state: dict) -> pd.DataFrame:
    X_flagged = add_missingness_flags(X_test)
    # Reindex to match training schema (fills missing flag cols with 0, drops unknowns)
    X_flagged = X_flagged.reindex(columns=state["feature_cols"], fill_value=0)
    X_filled = X_flagged.fillna(state["medians"])
    # Remaining NaNs -> 0 (catch any column that was never seen in train)
    return X_filled.fillna(0)


def fit_qb_simple(X_train: pd.DataFrame, y_train: pd.Series) -> dict:
    """Stripped-down QB model: Lasso on <=5 features, no ensemble.
    Backtest showed the full ensemble was overfitting on 71 rows."""
    feats = [f for f in QB_SIMPLE_FEATURES if f in X_train.columns]
    Xs = X_train[feats].copy()
    medians = Xs.median(numeric_only=True).to_dict()
    Xs_filled = Xs.fillna(medians)
    scaler = StandardScaler().fit(Xs_filled.values)
    lasso = Lasso(alpha=1.0, max_iter=10000)
    lasso.fit(scaler.transform(Xs_filled.values), y_train.values)
    state = {
        "medians": medians,
        "feature_cols": feats,           # no miss_ flags on purpose
        "dropped_all_nan": [],
        "scaler": scaler,
        "qb_simple": True,
    }
    # Fill all three slots with the same Lasso; weighted avg == Lasso
    return {"rf": lasso, "xgb": lasso, "ridge": lasso, "state": state}


def fit_ensemble(X_train: pd.DataFrame, y_train: pd.Series) -> dict:
    X_proc, state = preprocess_fit(X_train)
    rf = RandomForestRegressor(
        n_estimators=300, max_depth=None, min_samples_leaf=2,
        n_jobs=-1, random_state=42,
    )
    rf.fit(X_proc.values, y_train.values)
    xgb_model = xgb.XGBRegressor(
        n_estimators=400, learning_rate=0.05, max_depth=5,
        subsample=0.8, colsample_bytree=0.8, reg_lambda=1.0,
        objective="reg:squarederror", random_state=42,
        tree_method="hist", verbosity=0,
    )
    xgb_model.fit(X_proc.values, y_train.values)
    ridge = Ridge(alpha=1.0)
    ridge.fit(state["scaler"].transform(X_proc.values), y_train.values)

    return {"rf": rf, "xgb": xgb_model, "ridge": ridge, "state": state}


def predict_ensemble(models: dict, X_test: pd.DataFrame) -> np.ndarray:
    state = models["state"]
    if state.get("qb_simple"):
        # Single-Lasso path: skip missingness flags, use 5-feature schema
        feats = state["feature_cols"]
        Xt = X_test.reindex(columns=feats).copy()
        Xt = Xt.fillna(state["medians"]).fillna(0)
        return models["rf"].predict(state["scaler"].transform(Xt.values))
    X_proc = preprocess_transform(X_test, state)
    rf_pred = models["rf"].predict(X_proc.values)
    xgb_pred = models["xgb"].predict(X_proc.values)
    ridge_pred = models["ridge"].predict(state["scaler"].transform(X_proc.values))
    return (WEIGHTS["rf"] * rf_pred
            + WEIGHTS["xgb"] * xgb_pred
            + WEIGHTS["ridge"] * ridge_pred)


def load_group(group: str) -> tuple[pd.DataFrame, pd.Series, pd.DataFrame]:
    X = pd.read_csv(FEATURES_DIR / f"X_{group}_historical.csv")
    y = pd.read_csv(FEATURES_DIR / f"y_{group}_historical.csv").squeeze("columns")
    meta = pd.read_csv(FEATURES_DIR / f"meta_{group}_historical.csv")
    # Drop any string / non-numeric feature accidentally left in X
    non_numeric = [c for c in X.columns
                   if not pd.api.types.is_numeric_dtype(X[c])]
    if non_numeric:
        X = X.drop(columns=non_numeric)
    return X, y, meta


def cross_validate(group: str, X: pd.DataFrame, y: pd.Series,
                   meta: pd.DataFrame) -> list[dict]:
    rows = []
    for label, train_years, test_year in FOLDS:
        train_mask = meta["year"].isin(train_years)
        test_mask = meta["year"] == test_year
        if train_mask.sum() == 0 or test_mask.sum() == 0:
            rows.append({"group": group, "fold": label,
                         "n_train": int(train_mask.sum()),
                         "n_test": int(test_mask.sum()),
                         "mae": np.nan, "spearman": np.nan})
            continue
        fit_fn = fit_qb_simple if group == "QB" else fit_ensemble
        models = fit_fn(X[train_mask], y[train_mask])
        preds = predict_ensemble(models, X[test_mask])
        y_true = y[test_mask].values
        mae = float(np.mean(np.abs(preds - y_true)))
        if len(y_true) >= 2:
            rho, _ = spearmanr(preds, y_true)
        else:
            rho = np.nan
        rows.append({"group": group, "fold": label,
                     "n_train": int(train_mask.sum()),
                     "n_test": int(test_mask.sum()),
                     "mae": mae, "spearman": float(rho) if rho == rho else np.nan})
    return rows


def shap_top10(group: str, models: dict, X_sample: pd.DataFrame) -> pd.DataFrame:
    state = models["state"]
    X_proc = preprocess_transform(X_sample, state)
    explainer = shap.TreeExplainer(models["xgb"])
    shap_vals = explainer.shap_values(X_proc.values)
    importance = np.mean(np.abs(shap_vals), axis=0)
    df = pd.DataFrame({
        "group": group,
        "feature": X_proc.columns,
        "mean_abs_shap": importance,
    }).sort_values("mean_abs_shap", ascending=False).head(10)
    return df


def main():
    MODELS_DIR.mkdir(parents=True, exist_ok=True)

    all_cv_rows = []
    all_shap_rows = []

    for group in GROUPS:
        X, y, meta = load_group(group)
        print(f"\n=== {group} ===  X: {X.shape}  y: {y.shape}")

        # Temporal CV
        cv_rows = cross_validate(group, X, y, meta)
        all_cv_rows.extend(cv_rows)
        for r in cv_rows:
            print(f"  fold test={r['fold']}  "
                  f"n_train={r['n_train']:>4}  n_test={r['n_test']:>3}  "
                  f"MAE={r['mae']:.2f}  Spearman={r['spearman']:.3f}")

        # Final fit on all 2020-2025
        final = fit_qb_simple(X, y) if group == "QB" else fit_ensemble(X, y)
        with open(MODELS_DIR / f"{group}_ensemble.pkl", "wb") as f:
            pickle.dump(final, f)

        # SHAP on the most recent fold's holdout (2025). Skip for QB Lasso —
        # SHAP tree explainer only works for tree models.
        test_mask_2025 = meta["year"] == 2025
        X_shap = X[test_mask_2025] if test_mask_2025.any() else X.tail(100)
        if final["state"].get("qb_simple"):
            # Surface Lasso coefficients instead
            feats = final["state"]["feature_cols"]
            coefs = final["rf"].coef_
            top = pd.DataFrame({
                "group": group, "feature": feats,
                "mean_abs_shap": np.abs(coefs),
            }).sort_values("mean_abs_shap", ascending=False)
        else:
            top = shap_top10(group, final, X_shap)
        all_shap_rows.append(top)
        print(f"  top-10 features ({group}):")
        for _, row in top.iterrows():
            print(f"    {row['mean_abs_shap']:7.3f}  {row['feature']}")

    # Save results
    cv_df = pd.DataFrame(all_cv_rows)
    cv_df.to_csv(MODELS_DIR / "_stage1_results.csv", index=False)
    shap_df = pd.concat(all_shap_rows, ignore_index=True)
    shap_df.to_csv(MODELS_DIR / "_stage1_shap.csv", index=False)

    print("\n" + "=" * 70)
    print("STAGE-1 SUMMARY")
    print("=" * 70)
    print("\nPer-group averages across 3 folds:")
    agg = (cv_df.groupby("group")[["mae", "spearman"]]
               .mean().reset_index())
    for _, row in agg.iterrows():
        print(f"  {row['group']:<6}  mean MAE={row['mae']:.2f}  "
              f"mean Spearman={row['spearman']:.3f}")

    print("\nSaved models: " +
          ", ".join(f"models/{g}_ensemble.pkl" for g in GROUPS))
    print("Saved CV results: models/_stage1_results.csv")
    print("Saved SHAP ranks: models/_stage1_shap.csv")


if __name__ == "__main__":
    main()
