"""
Prediction service: loads the currently active model versions, runs inference
for a given match, and assembles the full response payload (confidence, risk,
call text, insight) that the API returns and the frontend renders.
"""
from __future__ import annotations
from pathlib import Path
import joblib
import numpy as np
import pandas as pd

from app.ml.insights import risk_from_confidence, winner_insight, goals_insight, corners_insight

MODEL_DIR = Path(__file__).resolve().parents[2] / "ml" / "saved_models"


class ModelRegistry:
    def __init__(self):
        self.winner = None
        self.goals = None
        self.corners = None
        self.features: list[str] = []
        self.goals_line = 2.5
        self.corners_residual_std = 2.6
        self.reload()

    def reload(self):
        winner_path = MODEL_DIR / "winner_model.joblib"
        goals_path = MODEL_DIR / "goals_model.joblib"
        corners_path = MODEL_DIR / "corners_model.joblib"

        if winner_path.exists():
            bundle = joblib.load(winner_path)
            self.winner = bundle["model"]
            self.features = bundle["features"]
        if goals_path.exists():
            bundle = joblib.load(goals_path)
            self.goals = bundle["model"]
            self.goals_line = bundle.get("line", 2.5)
        if corners_path.exists():
            bundle = joblib.load(corners_path)
            self.corners = bundle["model"]
            self.corners_residual_std = bundle.get("residual_std", 2.6)

    @property
    def is_ready(self) -> bool:
        return all([self.winner, self.goals, self.corners])


registry = ModelRegistry()


def predict_match(home_team: str, away_team: str, feat_row: dict) -> dict:
    if not registry.is_ready:
        raise RuntimeError(
            "Models not trained yet. Run `python -m ml.train --data <csv>` "
            "or POST /api/admin/retrain first."
        )

    X = pd.DataFrame([{k: feat_row[k] for k in registry.features}])

    proba = registry.winner.predict_proba(X)[0]
    prob_home, prob_draw, prob_away = float(proba[0]), float(proba[1]), float(proba[2])
    winner_confidence = round(float(max(proba)) * 100, 2)
    winner_call, winner_text = winner_insight(home_team, away_team, feat_row, prob_home, prob_draw, prob_away)

    goals_proba = registry.goals.predict_proba(X)[0]
    prob_over_goals = float(goals_proba[1])
    goals_confidence = round(float(max(goals_proba)) * 100, 2)
    goals_call, goals_text = goals_insight(home_team, away_team, feat_row, registry.goals_line, prob_over_goals)

    predicted_corners = float(registry.corners.predict(X)[0])
    corners_line = 11.5
    residual_std = registry.corners_residual_std
    from scipy.stats import norm
    prob_over_corners = float(1 - norm.cdf(corners_line, loc=predicted_corners, scale=residual_std))
    corners_confidence = round(max(prob_over_corners, 1 - prob_over_corners) * 100, 2)
    corners_call, corners_text = corners_insight(
        home_team, away_team, feat_row, corners_line, predicted_corners, prob_over_corners
    )

    return {
        "winner": {
            "prob_home_win": round(prob_home, 4),
            "prob_draw": round(prob_draw, 4),
            "prob_away_win": round(prob_away, 4),
            "confidence": winner_confidence,
            "risk": risk_from_confidence(winner_confidence),
            "call": winner_call,
            "insight": winner_text,
        },
        "goals": {
            "line": registry.goals_line,
            "prob_over": round(prob_over_goals, 4),
            "confidence": goals_confidence,
            "risk": risk_from_confidence(goals_confidence),
            "call": goals_call,
            "insight": goals_text,
        },
        "corners": {
            "line": corners_line,
            "predicted_total": round(predicted_corners, 1),
            "prob_over": round(prob_over_corners, 4),
            "confidence": corners_confidence,
            "risk": risk_from_confidence(corners_confidence),
            "call": corners_call,
            "insight": corners_text,
        },
    }
