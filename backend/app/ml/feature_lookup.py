"""
Builds the engineered feature row for ONE fixture at prediction time, using
all finished matches involving either team as history (no lookahead).

In a high-traffic production setup you'd cache each team's rolling state
(Elo, form, averages) in the DB or Redis and update it incrementally after
every finished match, rather than recomputing from full history per request.
This straightforward version recomputes from the match table each call,
which is fine at moderate traffic and is far easier to reason about —
optimize only once it's measurably slow.
"""
from __future__ import annotations
import pandas as pd
from sqlalchemy.orm import Session

from app.db.models import Match


def get_feature_row_for_match(db: Session, target_match: Match) -> dict:
    from ml.features import build_features

    home_name = target_match.home_team.name
    away_name = target_match.away_team.name

    history = (
        db.query(Match)
        .filter(Match.is_finished == True)
        .filter(Match.kickoff_utc < target_match.kickoff_utc)
        .filter(
            (Match.home_team_id == target_match.home_team_id)
            | (Match.away_team_id == target_match.home_team_id)
            | (Match.home_team_id == target_match.away_team_id)
            | (Match.away_team_id == target_match.away_team_id)
        )
        .order_by(Match.kickoff_utc.asc())
        .all()
    )

    rows = [{
        "home_team": m.home_team.name,
        "away_team": m.away_team.name,
        "kickoff_utc": m.kickoff_utc,
        "home_goals": m.home_goals,
        "away_goals": m.away_goals,
        "home_corners": m.home_corners,
        "away_corners": m.away_corners,
        "home_xg": m.home_xg,
        "away_xg": m.away_xg,
        "result": m.result.value,
    } for m in history]

    rows.append({
        "home_team": home_name,
        "away_team": away_name,
        "kickoff_utc": target_match.kickoff_utc,
        "home_goals": None, "away_goals": None,
        "home_corners": None, "away_corners": None,
        "home_xg": None, "away_xg": None,
        "result": None,
    })

    df = pd.DataFrame(rows)
    feat_df = build_features(df)
    return feat_df.iloc[-1].to_dict()
