"""
Training script for the three prediction models:
  1. Winner — multi-class XGBoost classifier
  2. Goals — binary XGBoost classifier
  3. Corners — XGBoost regressor
"""
from __future__ import annotations
import argparse
import json
import time
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.calibration import CalibratedClassifierCV
from sklearn.metrics import accuracy_score, log_loss, mean_absolute_error
from xgboost import XGBClassifier, XGBRegressor

try:
    from ml.features import build_features, FEATURE_COLUMNS
except ImportError:
    from features import build_features, FEATURE_COLUMNS

try:
    import optuna
    HAS_OPTUNA = True
except ImportError:
    HAS_OPTUNA = False

MODEL_DIR = Path(__file__).parent / "saved_models"
MODEL_DIR.mkdir(exist_ok=True)
RESULT_MAP = {"H": 0, "D": 1, "A": 2}

def _time_based_split(df: pd.DataFrame, test_frac: float = 0.15):
    df = df.sort_values("kickoff_utc")
    cutoff = int(len(df) * (1 - test_frac))
    return df.iloc[:cutoff], df.iloc[cutoff:]

def _tune_xgb_classifier(X_train, y_train, X_val, y_val, n_trials=25):
    if not HAS_OPTUNA:
        return {"max_depth": 4, "n_estimators": 300, "learning_rate": 0.05}
    def objective(trial):
        params = {
            "max_depth": trial.suggest_int("max_depth", 3, 7),
            "n_estimators": trial.suggest_int("n_estimators", 100, 500),
            "learning_rate": trial.suggest_float("learning_rate", 0.01, 0.2, log=True),
            "subsample": trial.suggest_float("subsample", 0.6, 1.0),
            "colsample_bytree": trial.suggest_float("colsample_bytree", 0.6, 1.0),
            "min_child_weight": trial.suggest_int("min_child_weight", 1, 10),
        }
        model = XGBClassifier(**params, eval_metric="mlogloss", tree_method="hist")
        model.fit(X_train, y_train)
        return log_loss(y_val, model.predict_proba(X_val), labels=[0, 1, 2])
    study = optuna.create_study(direction="minimize")
    study.optimize(objective, n_trials=n_trials, show_progress_bar=False)
    return study.best_params

def train_winner_model(feat_df: pd.DataFrame, tune: bool = False) -> dict:
    df = feat_df.dropna(subset=["label_result"]).copy()
    df["y"] = df["label_result"].map(RESULT_MAP)
    train_df, test_df = _time_based_split(df)
    X_train, y_train = train_df[FEATURE_COLUMNS], train_df["y"]
    X_test, y_test = test_df[FEATURE_COLUMNS], test_df["y"]
    params = _tune_xgb_classifier(X_train, y_train, X_test, y_test) if tune else {"max_depth": 4, "n_estimators": 300, "learning_rate": 0.05}
    base_model = XGBClassifier(**params, eval_metric="mlogloss", tree_method="hist")
    model = CalibratedClassifierCV(base_model, cv=3, method="isotonic")
    model.fit(X_train, y_train)
    preds_proba = model.predict_proba(X_test)
    preds = np.argmax(preds_proba, axis=1)
    metrics = {"accuracy": accuracy_score(y_test, preds), "log_loss": log_loss(y_test, preds_proba, labels=[0, 1, 2]), "baseline_accuracy": max(y_test.value_counts(normalize=True)), "n_test": len(y_test)}
    path = MODEL_DIR / "winner_model.joblib"
    joblib.dump({"model": model, "features": FEATURE_COLUMNS}, path)
    return {"path": str(path), **metrics}

def train_goals_model(feat_df: pd.DataFrame, line: float = 2.5, tune: bool = False) -> dict:
    df = feat_df.dropna(subset=["label_total_goals"]).copy()
    df["y"] = (df["label_total_goals"] > line).astype(int)
    train_df, test_df = _time_based_split(df)
    X_train, y_train = train_df[FEATURE_COLUMNS], train_df["y"]
    X_test, y_test = test_df[FEATURE_COLUMNS], test_df["y"]
    params = {"max_depth": 4, "n_estimators": 250, "learning_rate": 0.05}
    if tune and HAS_OPTUNA:
        def objective(trial):
            p = {"max_depth": trial.suggest_int("max_depth", 3, 6), "n_estimators": trial.suggest_int("n_estimators", 100, 400), "learning_rate": trial.suggest_float("learning_rate", 0.01, 0.2, log=True)}
            m = XGBClassifier(**p, eval_metric="logloss", tree_method="hist")
            m.fit(X_train, y_train)
            return log_loss(y_test, m.predict_proba(X_test))
        study = optuna.create_study(direction="minimize")
        study.optimize(objective, n_trials=20, show_progress_bar=False)
        params = study.best_params
    model = XGBClassifier(**params, eval_metric="logloss", tree_method="hist")
    model.fit(X_train, y_train)
    preds = model.predict(X_test)
    metrics = {"accuracy": accuracy_score(y_test, preds), "baseline_accuracy": max(y_test.mean(), 1 - y_test.mean()), "line": line, "n_test": len(y_test)}
    path = MODEL_DIR / "goals_model.joblib"
    joblib.dump({"model": model, "features": FEATURE_COLUMNS, "line": line}, path)
    return {"path": str(path), **metrics}

def train_corners_model(feat_df: pd.DataFrame, tune: bool = False) -> dict:
    df = feat_df.dropna(subset=["label_total_corners"]).copy()
    train_df, test_df = _time_based_split(df)
    X_train, y_train = train_df[FEATURE_COLUMNS], train_df["label_total_corners"]
    X_test, y_test = test_df[FEATURE_COLUMNS], test_df["label_total_corners"]
    params = {"max_depth": 4, "n_estimators": 250, "learning_rate": 0.05}
    if tune and HAS_OPTUNA:
        def objective(trial):
            p = {"max_depth": trial.suggest_int("max_depth", 3, 6), "n_estimators": trial.suggest_int("n_estimators", 100, 400), "learning_rate": trial.suggest_float("learning_rate", 0.01, 0.2, log=True)}
            m = XGBRegressor(**p, tree_method="hist")
            m.fit(X_train, y_train)
            return mean_absolute_error(y_test, m.predict(X_test))
        study = optuna.create_study(direction="minimize")
        study.optimize(objective, n_trials=20, show_progress_bar=False)
        params = study.best_params
    model = XGBRegressor(**params, tree_method="hist")
    model.fit(X_train, y_train)
    preds = model.predict(X_test)
    residuals = y_test.to_numpy() - preds
    residual_std = float(np.std(residuals)) if len(residuals) > 1 else 2.6
    metrics = {"mae": mean_absolute_error(y_test, preds), "baseline_mae": mean_absolute_error(y_test, [y_train.mean()] * len(y_test)), "residual_std": residual_std, "n_test": len(y_test)}
    path = MODEL_DIR / "corners_model.joblib"
    joblib.dump({"model": model, "features": FEATURE_COLUMNS, "residual_std": residual_std}, path)
    return {"path": str(path), **metrics}

def run_full_training(matches_csv: str, tune: bool = False) -> dict:
    matches = pd.read_csv(matches_csv, parse_dates=["kickoff_utc"])
    feat_df = build_features(matches)
    t0 = time.time()
    winner_metrics = train_winner_model(feat_df, tune=tune)
    goals_metrics = train_goals_model(feat_df, tune=tune)
    corners_metrics = train_corners_model(feat_df, tune=tune)
    elapsed = time.time() - t0
    summary = {"trained_at": pd.Timestamp.now("UTC").isoformat(), "training_rows": len(feat_df), "elapsed_seconds": round(elapsed, 1), "winner": winner_metrics, "goals": goals_metrics, "corners": corners_metrics}
    with open(MODEL_DIR / "training_summary.json", "w") as f:
        json.dump(summary, f, indent=2, default=str)
    return summary

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", required=True, help="Path to historical matches CSV")
    parser.add_argument("--tune", action="store_true", help="Run Optuna hyperparameter search")
    args = parser.parse_args()
    result = run_full_training(args.data, tune=args.tune)
    print(json.dumps(result, indent=2, default=str))
