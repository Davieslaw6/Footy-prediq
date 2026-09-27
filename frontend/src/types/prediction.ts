export type RiskLevel = "low" | "medium" | "high";

export interface TeamInfo {
  name: string;
  logo_url?: string | null;
}

export interface WinnerPrediction {
  prob_home_win: number;
  prob_draw: number;
  prob_away_win: number;
  confidence: number;
  risk: RiskLevel;
  call: string;
  insight: string;
}

export interface GoalsPrediction {
  line: number;
  prob_over: number;
  confidence: number;
  risk: RiskLevel;
  call: string;
  insight: string;
}

export interface CornersPrediction {
  line: number;
  predicted_total: number;
  prob_over: number;
  confidence: number;
  risk: RiskLevel;
  call: string;
  insight: string;
}

export interface UpcomingFixture {
  id: number;
  league: string;
  kickoff_utc: string;
  home_team: TeamInfo;
  away_team: TeamInfo;
}

export interface MatchPrediction {
  match_id: number;
  league: string;
  kickoff_utc: string;
  home_team: TeamInfo;
  away_team: TeamInfo;
  winner: WinnerPrediction;
  over_under: GoalsPrediction;
  corners: CornersPrediction;
}
