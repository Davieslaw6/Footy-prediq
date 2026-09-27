"""
Training orchestration for database data and uploaded CSV datasets.
"""
from __future__ import annotations
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from ml.train import run_full_training
from app.db.session import SessionLocal
from app.db.models import ModelVersion
from app.ml.predict_service import registry

logger = logging.getLogger("retrain_runner")

DATA_EXPORT_PATH = Path(__file__).resolve().parents[2] / "ml" / "data" / "matches_export.csv"


def export_matches_to_csv(db) -> str:
    import pandas as pd
    from app.db.models import Match

    rows = []
    for m in db.query(Match).all():
        rows.append({
            "home_team": m.home_team.name,
            "away_team": m.away_team.name,
            "kickoff_utc": m.kickoff_utc,
            "home_goals": m.home_goals,
            "away_goals": m.away_goals,
            "home_corners": m.home_corners,
            "away_corners": m.away_corners,
            "home_xg": m.home_xg,
            "away_xg": m.away_xg,
            "result": m.result.value if m.result and m.result.value != "PENDING" else None,
        })
    if not rows:
        raise ValueError("No matches in the database to export. Import a historical CSV first.")
    df = pd.DataFrame(rows)
    DATA_EXPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(DATA_EXPORT_PATH, index=False)
    return str(DATA_EXPORT_PATH)


def _record_training_summary(db, summary: dict, source: str, tune: bool) -> dict:
    db.query(ModelVersion).update({ModelVersion.is_active: False})
    version = ModelVersion(
        winner_model_path=summary["winner"]["path"],
        goals_model_path=summary["goals"]["path"],
        corners_model_path=summary["corners"]["path"],
        winner_accuracy=summary["winner"]["accuracy"],
        winner_log_loss=summary["winner"]["log_loss"],
        goals_accuracy=summary["goals"]["accuracy"],
        corners_mae=summary["corners"]["mae"],
        training_rows=summary["training_rows"],
        is_active=True,
        notes=f"Trained from {source}; {'tuned' if tune else 'default-params'} pipeline",
    )
    db.add(version)
    db.commit()
    registry.reload()
    return summary


def run_training_from_csv(csv_path: str, tune: bool = False) -> dict:
    db = SessionLocal()
    try:
        summary = run_full_training(csv_path, tune=tune)
        result = _record_training_summary(db, summary, "uploaded CSV", tune)
        logger.info("Training from uploaded CSV complete: %s rows, winner_acc=%.3f",
                    result["training_rows"], result["winner"]["accuracy"])
        return result
    except Exception:
        logger.exception("Training from uploaded CSV failed (csv_path=%s)", csv_path)
        raise
    finally:
        db.close()


def run_retrain_and_reload(tune: bool = False) -> dict:
    db = SessionLocal()
    try:
        csv_path = export_matches_to_csv(db)
        summary = run_full_training(csv_path, tune=tune)
        result = _record_training_summary(db, summary, "database matches", tune)
        logger.info("Retraining from database complete: %s rows, winner_acc=%.3f",
                    result["training_rows"], result["winner"]["accuracy"])
        return result
    except Exception:
        logger.exception("Retraining from database failed")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    result = run_retrain_and_reload(tune=False)
    print("Retraining complete:", result)
