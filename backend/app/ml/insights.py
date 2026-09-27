"""
Dynamic "Match Insight" text generation.

Given a match's engineered features and the model's raw outputs, produces
a human-readable sentence explaining WHY the model made that call — using
the actual numbers behind the prediction, not a canned template with the
teams swapped in. This is deterministic (no LLM call) so it's fast, free,
and always consistent with the numbers shown on the card.
"""
from __future__ import annotations


def risk_from_confidence(confidence_pct: float) -> str:
    if confidence_pct > 80:
        return "low"
    elif confidence_pct >= 60:
        return "medium"
    else:
        return "high"


def winner_insight(home: str, away: str, feat: dict, prob_home: float, prob_draw: float, prob_away: float) -> tuple[str, str]:
    """Returns (call_text, insight_text)."""
    favored_home = prob_home >= prob_away
    favored_team = home if favored_home else away
    underdog_team = away if favored_home else home

    dominant = max(prob_home, prob_draw, prob_away) > 0.65
    is_draw_call = dominant and prob_draw > prob_home and prob_draw > prob_away
    if dominant:
        if prob_home > prob_away and prob_home > prob_draw:
            call = f"Winner: {home}"
        elif prob_away > prob_home and prob_away > prob_draw:
            call = f"Winner: {away}"
        else:
            call = "Winner: Draw"
    else:
        call = f"Double Chance: {favored_team} Or Draw"

    elo_gap_signed = feat["elo_diff"] if favored_home else -feat["elo_diff"]
    form_gap = feat["form_home"] - feat["form_away"] if favored_home else feat["form_away"] - feat["form_home"]
    favored_form = feat["form_home"] if favored_home else feat["form_away"]

    if is_draw_call:
        insight = (
            f"{home} And {away} Are Closely Matched On Current Form And Rating - "
            f"A Draw Looks The Most Likely Outcome Here"
        )
    elif elo_gap_signed > 80 and form_gap >= 0:
        insight = (
            f"{favored_team} Enter In Stronger Overall Form And Rating Than {underdog_team} - "
            f"A Win Or Draw Looks Achievable Given The Gap In Quality"
        )
    elif favored_home and elo_gap_signed < 0:
        insight = (
            f"Home Advantage Gives {home} The Edge Despite {away}'s Slight Edge In Underlying Form - "
            f"A Win Or Draw Looks Achievable Against {away}"
        )
    elif form_gap > 3:
        insight = (
            f"{favored_team} Arrive In Considerably Better Recent Form Than {underdog_team} "
            f"({favored_form} Pts From Last 5) - "
            f"That Momentum Backs This Call"
        )
    else:
        insight = (
            f"A Tightly Matched Fixture On The Numbers - {favored_team} Get A Marginal Edge "
            f"From Home Advantage And Recent Form"
        )
    return call, insight


def goals_insight(home: str, away: str, feat: dict, line: float, prob_over: float) -> tuple[str, str]:
    over = prob_over >= 0.5
    call = f"Over/Under: {'Over' if over else 'Under'} {line} Goals"

    combined_conceded = feat["avg_goals_conceded_home"] + feat["avg_goals_conceded_away"]
    combined_scored = feat["avg_goals_scored_home"] + feat["avg_goals_scored_away"]
    leakier_team = away if feat["avg_goals_conceded_away"] > feat["avg_goals_conceded_home"] else home
    leakier_rate = max(feat["avg_goals_conceded_away"], feat["avg_goals_conceded_home"])

    if over and leakier_rate > 1.6:
        insight = (
            f"{leakier_team} Concede {leakier_rate:.1f} Goals Per Game On Average - "
            f"Defensive Vulnerabilities Point To Goals In This Fixture"
        )
    elif over:
        insight = (
            f"Both Sides Average A Combined {combined_scored:.1f} Goals Scored Per Game - "
            f"Enough Attacking Output To Clear {line}"
        )
    else:
        insight = (
            f"Both Defenses Concede Just {combined_conceded:.1f} Combined Goals Per Game On Average - "
            f"A Tighter, Lower-Scoring Game Looks More Likely"
        )
    return call, insight


def corners_insight(home: str, away: str, feat: dict, line: float, predicted_total: float, prob_over: float) -> tuple[str, str]:
    over = prob_over >= 0.5
    call = f"Over/Under: {'Over' if over else 'Under'} {line} Corners"
    insight = (
        f"Corner Projection: {predicted_total:.1f} Total - "
        f"{home} ({feat['avg_corners_home']:.1f} Avg) Vs {away} ({feat['avg_corners_away']:.1f} Avg)"
    )
    return call, insight
