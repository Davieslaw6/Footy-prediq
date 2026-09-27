"""
SQLAlchemy ORM models — PostgreSQL schema for the prediction system.

Tables:
  - teams: canonical team registry
  - matches: historical + upcoming fixtures with results
  - team_match_stats: per-team, per-match derived stats (goals, corners, xG)
  - predictions: logged model outputs per match
  - model_versions: tracks retraining history for the continuous learning pipeline
"""
from datetime import datetime, date
from sqlalchemy import (
    Column, Integer, String, Float, Boolean, DateTime, Date, ForeignKey,
    UniqueConstraint, Text, Enum as SAEnum
)
from sqlalchemy.orm import relationship, declarative_base
import enum

Base = declarative_base()


class League(str, enum.Enum):
    EPL = "EPL"
    LA_LIGA = "La Liga"
    SERIE_A = "Serie A"
    BUNDESLIGA = "Bundesliga"
    LIGUE_1 = "Ligue 1"
    EREDIVISIE = "Eredivisie"
    PRIMEIRA_LIGA = "Primeira Liga"
    SAUDI_PRO_LEAGUE = "Saudi Pro League"
    MLS = "MLS"
    OTHER = "Other"
    # Extend with the remaining ~21 European leagues as data sources are added.


class MatchResult(str, enum.Enum):
    HOME_WIN = "H"
    DRAW = "D"
    AWAY_WIN = "A"
    PENDING = "PENDING"


class Team(Base):
    __tablename__ = "teams"

    id = Column(Integer, primary_key=True)
    name = Column(String(120), nullable=False, unique=True, index=True)
    short_name = Column(String(40))
    league = Column(SAEnum(League), nullable=False, index=True)
    country = Column(String(60))
    logo_url = Column(String(500))
    external_ids = Column(Text)

    home_matches = relationship("Match", foreign_keys="Match.home_team_id", back_populates="home_team")
    away_matches = relationship("Match", foreign_keys="Match.away_team_id", back_populates="away_team")


class Match(Base):
    __tablename__ = "matches"

    id = Column(Integer, primary_key=True)
    league = Column(SAEnum(League), nullable=False, index=True)
    season = Column(String(9), nullable=False)
    kickoff_utc = Column(DateTime, nullable=False, index=True)

    home_team_id = Column(Integer, ForeignKey("teams.id"), nullable=False)
    away_team_id = Column(Integer, ForeignKey("teams.id"), nullable=False)
    home_team = relationship("Team", foreign_keys=[home_team_id], back_populates="home_matches")
    away_team = relationship("Team", foreign_keys=[away_team_id], back_populates="away_matches")

    home_goals = Column(Integer, nullable=True)
    away_goals = Column(Integer, nullable=True)
    home_corners = Column(Integer, nullable=True)
    away_corners = Column(Integer, nullable=True)
    home_xg = Column(Float, nullable=True)
    away_xg = Column(Float, nullable=True)
    result = Column(SAEnum(MatchResult), default=MatchResult.PENDING, index=True)

    is_finished = Column(Boolean, default=False, index=True)
    data_source = Column(String(50))

    predictions = relationship("Prediction", back_populates="match", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("home_team_id", "away_team_id", "kickoff_utc", name="uq_fixture"),
    )


class Prediction(Base):
    __tablename__ = "predictions"

    id = Column(Integer, primary_key=True)
    match_id = Column(Integer, ForeignKey("matches.id"), nullable=False, index=True)
    match = relationship("Match", back_populates="predictions")
    model_version_id = Column(Integer, ForeignKey("model_versions.id"), nullable=False)

    generated_at = Column(DateTime, default=datetime.utcnow)

    prob_home_win = Column(Float, nullable=False)
    prob_draw = Column(Float, nullable=False)
    prob_away_win = Column(Float, nullable=False)
    winner_confidence = Column(Float, nullable=False)
    winner_risk = Column(String(10), nullable=False)
    winner_call = Column(String(120), nullable=False)
    winner_insight = Column(Text, nullable=False)

    goals_line = Column(Float, nullable=False, default=2.5)
    prob_over_goals = Column(Float, nullable=False)
    goals_confidence = Column(Float, nullable=False)
    goals_risk = Column(String(10), nullable=False)
    goals_call = Column(String(120), nullable=False)
    goals_insight = Column(Text, nullable=False)

    corners_line = Column(Float, nullable=False, default=11.5)
    predicted_total_corners = Column(Float, nullable=False)
    prob_over_corners = Column(Float, nullable=False)
    corners_confidence = Column(Float, nullable=False)
    corners_risk = Column(String(10), nullable=False)
    corners_call = Column(String(120), nullable=False)
    corners_insight = Column(Text, nullable=False)


class ModelVersion(Base):
    __tablename__ = "model_versions"

    id = Column(Integer, primary_key=True)
    trained_at = Column(DateTime, default=datetime.utcnow, index=True)
    winner_model_path = Column(String(300), nullable=False)
    goals_model_path = Column(String(300), nullable=False)
    corners_model_path = Column(String(300), nullable=False)

    winner_accuracy = Column(Float)
    winner_log_loss = Column(Float)
    goals_accuracy = Column(Float)
    corners_mae = Column(Float)

    training_rows = Column(Integer)
    is_active = Column(Boolean, default=False, index=True)
    notes = Column(Text)
