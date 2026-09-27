"""
FastAPI backend entrypoint.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional
import os
from pathlib import Path
import shutil
import uuid

from fastapi import FastAPI, HTTPException, BackgroundTasks, UploadFile, File, Form, Header, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.session import get_db, engine, SessionLocal
from app.db.models import Base, Match, ModelVersion, Prediction
from app.ml.predict_service import predict_match, registry

app = FastAPI(title="Football Prediction API", version="2.1.0")

ALLOWED_ORIGINS = [
    origin.strip()
    for origin in os.getenv("ALLOWED_ORIGINS", "http://localhost:3000").split(",")
    if origin.strip()
]

ADMIN_API_KEY = os.getenv("ADMIN_API_KEY")


def require_admin_key(x_admin_key: Optional[str] = Header(default=None)):
    if ADMIN_API_KEY and x_admin_key != ADMIN_API_KEY:
        raise HTTPException(status_code=401, detail="Missing or invalid X-Admin-Key header.")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

Base.metadata.create_all(bind=engine)

TRAINING_UPLOAD_DIR = Path(__file__).resolve().parents[1] / "data" / "training_uploads"
TRAINING_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

REQUIRED_CSV_COLUMNS = {
    "home_team", "away_team", "kickoff_utc", "home_goals", "away_goals",
    "home_corners", "away_corners", "home_xg", "away_xg", "result",
}


class TeamOut(BaseModel):
    name: str
    logo_url: Optional[str] = None

    class Config:
        from_attributes = True


class FixtureOut(BaseModel):
    id: int
    league: str
    kickoff_utc: datetime
    home_team: TeamOut
    away_team: TeamOut

    class Config:
        from_attributes = True


class RetrainResponse(BaseModel):
    status: str
    detail: str


@app.get("/api/matches/upcoming", response_model=list[FixtureOut])
def get_upcoming_matches(league: Optional[str] = None, limit: int = 20, db: Session = get_db()):
    query = db.query(Match).filter(Match.is_finished == False)
    if league:
        query = query.filter(Match.league == league)
    return query.order_by(Match.kickoff_utc.asc()).limit(limit).all()


@app.get("/api/predictions/{match_id}")
def get_prediction(match_id: int, db: Session = get_db()):
    match = db.query(Match).filter(Match.id == match_id).first()
    if not match:
        raise HTTPException(status_code=404, detail="Match not found")
    if not registry.is_ready:
        raise HTTPException(status_code=503, detail="Models are not trained yet. Upload training data or trigger retraining first.")

    from app.ml.feature_lookup import get_feature_row_for_match
    feat_row = get_feature_row_for_match(db, match)
    result = predict_match(match.home_team.name, match.away_team.name, feat_row)

    active_version = (
        db.query(ModelVersion)
        .filter(ModelVersion.is_active == True)
        .order_by(ModelVersion.trained_at.desc())
        .first()
    )
    if active_version:
        db.add(Prediction(
            match_id=match.id,
            model_version_id=active_version.id,
            prob_home_win=result["winner"]["prob_home_win"],
            prob_draw=result["winner"]["prob_draw"],
            prob_away_win=result["winner"]["prob_away_win"],
            winner_confidence=result["winner"]["confidence"],
            winner_risk=result["winner"]["risk"],
            winner_call=result["winner"]["call"],
            winner_insight=result["winner"]["insight"],
            goals_line=result["goals"]["line"],
            prob_over_goals=result["goals"]["prob_over"],
            goals_confidence=result["goals"]["confidence"],
            goals_risk=result["goals"]["risk"],
            goals_call=result["goals"]["call"],
            goals_insight=result["goals"]["insight"],
            corners_line=result["corners"]["line"],
            predicted_total_corners=result["corners"]["predicted_total"],
            prob_over_corners=result["corners"]["prob_over"],
            corners_confidence=result["corners"]["confidence"],
            corners_risk=result["corners"]["risk"],
            corners_call=result["corners"]["call"],
            corners_insight=result["corners"]["insight"],
        ))
        db.commit()

    return {
        "match_id": match.id,
        "league": match.league,
        "kickoff_utc": match.kickoff_utc,
        "home_team": {"name": match.home_team.name, "logo_url": match.home_team.logo_url},
        "away_team": {"name": match.away_team.name, "logo_url": match.away_team.logo_url},
        "winner": result["winner"],
        "over_under": result["goals"],
        "corners": result["corners"],
    }


@app.post("/api/admin/retrain", response_model=RetrainResponse, dependencies=[Depends(require_admin_key)])
def trigger_retrain(background_tasks: BackgroundTasks, tune: bool = False):
    from app.ml.retrain_runner import run_retrain_and_reload
    background_tasks.add_task(run_retrain_and_reload, tune)
    return RetrainResponse(
        status="accepted",
        detail="Retraining started in the background using the matches currently stored in the database.",
    )


@app.post("/api/admin/training-data/import", response_model=RetrainResponse, dependencies=[Depends(require_admin_key)])
async def import_training_csv(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    tune: bool = Form(False),
):
    """Validate an uploaded historical matches CSV and start model training from it."""
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only .csv files are accepted.")

    upload_id = uuid.uuid4().hex
    destination = TRAINING_UPLOAD_DIR / f"{upload_id}.csv"

    try:
        with destination.open("wb") as output:
            shutil.copyfileobj(file.file, output)

        import pandas as pd
        try:
            df = pd.read_csv(destination, parse_dates=["kickoff_utc"])
        except Exception as exc:
            raise HTTPException(status_code=400, detail=f"Could not read CSV: {exc}")

        missing = sorted(REQUIRED_CSV_COLUMNS - set(df.columns))
        if missing:
            raise HTTPException(
                status_code=400,
                detail=f"Missing required columns: {', '.join(missing)}",
            )

        if len(df) < 50:
            raise HTTPException(status_code=400, detail="At least 50 historical matches are required for training.")

        if df[list(REQUIRED_CSV_COLUMNS)].isnull().any().any():
            raise HTTPException(status_code=400, detail="Required training columns contain empty values.")

        invalid_results = sorted(set(df["result"].astype(str).str.upper()) - {"H", "D", "A"})
        if invalid_results:
            raise HTTPException(status_code=400, detail=f"Invalid result values: {', '.join(invalid_results)}. Use H, D, or A.")

        numeric_columns = ["home_goals", "away_goals", "home_corners", "away_corners", "home_xg", "away_xg"]
        for column in numeric_columns:
            if not pd.to_numeric(df[column], errors="coerce").notna().all():
                raise HTTPException(status_code=400, detail=f"Column '{column}' contains non-numeric values.")

        from app.ml.retrain_runner import run_training_from_csv
        background_tasks.add_task(run_training_from_csv, str(destination), tune)

        return RetrainResponse(
            status="accepted",
            detail=f"CSV accepted: {len(df)} historical matches. Training has started in the background.",
        )
    except HTTPException:
        if destination.exists():
            destination.unlink()
        raise
    except Exception as exc:
        if destination.exists():
            destination.unlink()
        raise HTTPException(status_code=500, detail=f"Could not import training CSV: {exc}")


@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "models_ready": registry.is_ready,
        "checked_at": datetime.now(timezone.utc).isoformat(),
    }
