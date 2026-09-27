"""
Feature engineering for the prediction models.

Given historical match rows (home_team, away_team, date, goals, corners, xG, result),
builds the feature set each model trains on.
"""
from __future__ import annotations
import pandas as pd
import numpy as np
from dataclasses import dataclass

ELO_K = 20
ELO_HOME_ADV = 60
ELO_START = 1500

@dataclass
class TeamState:
    elo: float = ELO_START
    recent_results: list | None = None
    def __post_init__(self):
        if self.recent_results is None:
            self.recent_results = []

def _elo_expected(rating_a: float, rating_b: float) -> float:
    return 1.0 / (1.0 + 10 ** ((rating_b - rating_a) / 400))

def _update_elo(home_elo, away_elo, result: str):
    exp_home = _elo_expected(home_elo + ELO_HOME_ADV, away_elo)
    score_home = {"H": 1.0, "D": 0.5, "A": 0.0}[result]
    delta = ELO_K * (score_home - exp_home)
    return home_elo + delta, away_elo - delta

def build_features(matches: pd.DataFrame) -> pd.DataFrame:
    matches = matches.sort_values("kickoff_utc").reset_index(drop=True)
    teams: dict[str, TeamState] = {}
    home_goal_log: dict[str, list] = {}
    away_goal_log: dict[str, list] = {}
    home_conceded_log: dict[str, list] = {}
    away_conceded_log: dict[str, list] = {}
    home_corner_log: dict[str, list] = {}
    away_corner_log: dict[str, list] = {}
    xg_log: dict[str, list] = {}
    h2h_log: dict[tuple, list] = {}
    rows = []
    LEAGUE_AVG_GOALS = 1.35

    def _shrunk_avg(log: list, prior: float, k: int = 4) -> float:
        if not log:
            return prior
        n = len(log)
        return (sum(log) + k * prior) / (n + k)

    for _, m in matches.iterrows():
        h, a = m["home_team"], m["away_team"]
        teams.setdefault(h, TeamState())
        teams.setdefault(a, TeamState())
        for d in (home_goal_log, away_goal_log, home_conceded_log, away_conceded_log,
                  home_corner_log, away_corner_log, xg_log):
            d.setdefault(h, [])
            d.setdefault(a, [])

        form_h = sum({"W": 3, "D": 1, "L": 0}[r] for r in teams[h].recent_results[-5:])
        form_a = sum({"W": 3, "D": 1, "L": 0}[r] for r in teams[a].recent_results[-5:])

        feat = {
            "match_index": len(rows), "home_team": h, "away_team": a,
            "kickoff_utc": m["kickoff_utc"],
            "elo_home": teams[h].elo, "elo_away": teams[a].elo,
            "elo_diff": teams[h].elo - teams[a].elo,
            "form_home": form_h, "form_away": form_a,
            "avg_goals_scored_home": _shrunk_avg(home_goal_log[h][-6:], LEAGUE_AVG_GOALS),
            "avg_goals_conceded_home": _shrunk_avg(home_conceded_log[h][-6:], LEAGUE_AVG_GOALS),
            "avg_goals_scored_away": _shrunk_avg(away_goal_log[a][-6:], LEAGUE_AVG_GOALS),
            "avg_goals_conceded_away": _shrunk_avg(away_conceded_log[a][-6:], LEAGUE_AVG_GOALS),
            "avg_corners_home": _shrunk_avg(home_corner_log[h][-6:], 5.2),
            "avg_corners_away": _shrunk_avg(away_corner_log[a][-6:], 4.6),
            "avg_xg_home": _shrunk_avg(xg_log[h][-6:], 1.3),
            "avg_xg_away": _shrunk_avg(xg_log[a][-6:], 1.1),
        }
        h2h_key = tuple(sorted([h, a]))
        h2h_results = h2h_log.get(h2h_key, [])
        if h2h_results:
            home_wins = sum(1 for winner in h2h_results if winner == h)
            feat["h2h_home_win_rate"] = home_wins / len(h2h_results)
        else:
            feat["h2h_home_win_rate"] = 0.45

        feat["label_result"] = m.get("result", np.nan)
        feat["label_total_goals"] = (
            (m["home_goals"] + m["away_goals"]) if pd.notna(m.get("home_goals")) else np.nan
        )
        feat["label_total_corners"] = (
            (m["home_corners"] + m["away_corners"]) if pd.notna(m.get("home_corners")) else np.nan
        )
        rows.append(feat)

        if pd.notna(m.get("result")):
            result = m["result"]
            home_goal_log[h].append(m["home_goals"])
            away_goal_log[a].append(m["away_goals"])
            home_conceded_log[h].append(m["away_goals"])
            away_conceded_log[a].append(m["home_goals"])
            if pd.notna(m.get("home_corners")):
                home_corner_log[h].append(m["home_corners"])
                away_corner_log[a].append(m["away_corners"])
            if pd.notna(m.get("home_xg")):
                xg_log[h].append(m["home_xg"])
                xg_log[a].append(m["away_xg"])

            teams[h].recent_results.append({"H": "W", "D": "D", "A": "L"}[result])
            teams[a].recent_results.append({"H": "L", "D": "D", "A": "W"}[result])
            new_h_elo, new_a_elo = _update_elo(teams[h].elo, teams[a].elo, result)
            teams[h].elo, teams[a].elo = new_h_elo, new_a_elo
            winner_team = h if result == "H" else (a if result == "A" else None)
            h2h_log.setdefault(h2h_key, []).append(winner_team)

    return pd.DataFrame(rows)

FEATURE_COLUMNS = [
    "elo_home", "elo_away", "elo_diff", "form_home", "form_away",
    "avg_goals_scored_home", "avg_goals_conceded_home",
    "avg_goals_scored_away", "avg_goals_conceded_away",
    "avg_corners_home", "avg_corners_away",
    "avg_xg_home", "avg_xg_away", "h2h_home_win_rate",
]
