import math

class F5ModelModule:
    """
    Standalone Python class to project the "First 5 Innings" (F5) scores for both Away and Home teams,
    along with Moneyline Probabilities and Totals based on specific MLB Excel formulas.
    """

    def __init__(self, team_name_mapping, f5_rpg_database, team_database, pitcher_metrics, bullpen_database):
        self.team_name_mapping = team_name_mapping
        self.f5_rpg_database = f5_rpg_database
        self.team_database = team_database
        self.pitcher_metrics = pitcher_metrics
        self.bullpen_database = bullpen_database
        
        # Global Parameters (Defaults as per formula)
        self.lgERA = 4.2
        self.hfa = 1.03
        self.offExp = 1.83
        self.pMin = 0.6
        self.pMax = 1.4
        self.vMin = 0.95
        self.vMax = 1.1

    def _normalize_team_name(self, team_name):
        return self.team_name_mapping.get(team_name, team_name)

    def _fetch_offense_stats(self, team_code):
        # Default fallbacks
        rpg0 = 4.5
        wrc = 100.0
        ba = 0.245
        
        # Fetch RPG
        rpg_info = self.f5_rpg_database.get(team_code, {})
        if isinstance(rpg_info, dict):
            # Try specific keys from f5_rpg_database structure
            rpg0 = rpg_info.get("current_2026", rpg_info.get("rpg0", 4.5))
        elif isinstance(rpg_info, (int, float)):
            rpg0 = float(rpg_info)
            
        # Fetch wRC+ and Batting Average (avg)
        team_info = self.team_database.get(team_code, {})
        if isinstance(team_info, dict):
            wrc = float(team_info.get("wrc_plus", 100))
            ba = float(team_info.get("avg", 0.245))
            
        return rpg0, wrc, ba

    def _fetch_pitching_stats(self, pitcher_name, team_code):
        # Default fallbacks
        sp0 = 4.2
        bp0 = 4.39
        
        # Fetch SP rating (xERA or SIERA)
        sp_info = self.pitcher_metrics.get(pitcher_name, {})
        if isinstance(sp_info, dict):
            sp0 = float(sp_info.get("xera", sp_info.get("siera", 4.2)))
            
        # Fetch Bullpen rating
        bp_info = self.bullpen_database.get(team_code, {})
        if isinstance(bp_info, dict):
            bp0 = float(bp_info.get("rating", bp_info.get("xera", 4.39)))
        elif isinstance(bp_info, (int, float)):
            bp0 = float(bp_info)
            
        return sp0, bp0

    def calculate_score(self, offense_team, pitching_team, pitcher, is_home):
        """
        Calculates the projected F5 score for a single team.
        """
        off_code = self._normalize_team_name(offense_team)
        pitch_code = self._normalize_team_name(pitching_team)
        
        # Fetch data safely
        rpg0, wrc, ba = self._fetch_offense_stats(off_code)
        sp0, bp0 = self._fetch_pitching_stats(pitcher, pitch_code)
        
        # 1. Fetch & Cap Base Variables
        rpg = max(3, min(6, rpg0)) if rpg0 > 0 else 4.5
        sp = max(2, min(8, sp0))
        bp = max(2, min(8, bp0))
        
        # 2. Core Component Calculations
        base_score = 0.6 * rpg + 0.4 * self.lgERA
        
        # Offense
        ba_term = 1.0 if ba <= 0 else (ba / 0.245) ** 0.5
        ba_term_capped = max(0.95, min(1.05, ba_term))
        off = ((wrc / 100) ** self.offExp) * ba_term_capped
        
        # Pitching
        exponent = ((0.7 * sp + 0.3 * bp) - self.lgERA) / self.lgERA
        pitchRaw = math.exp(exponent)
        pitch = max(self.pMin, min(self.pMax, pitchRaw))
        
        # Volatility
        volRaw = 0.5 * (abs(wrc - 100) / 50.0 + abs(sp - self.lgERA) / 2.0)
        vol = max(self.vMin, min(self.vMax, volRaw))
        
        # 3. Score Calculation
        score = base_score * off * pitch * vol
        if is_home:
            score *= self.hfa
            
        # 4. Finalizing
        final_score = round(max(0, min(15, score)), 1)
        return final_score

    def calculate(self, away_team, home_team, away_pitcher, home_pitcher):
        """
        Main calculation method that outputs dictionary format expected.
        """
        # Calculate individual scores
        away_score = self.calculate_score(away_team, home_team, home_pitcher, is_home=False)
        home_score = self.calculate_score(home_team, away_team, away_pitcher, is_home=True)
        
        # Advanced Metrics
        model_total = round(away_score + home_score, 2)
        
        # ML Probabilities
        if away_score == 0 and home_score == 0:
            away_prob = 0.5
            home_prob = 0.5
        else:
            away_pow = away_score ** 1.83
            home_pow = home_score ** 1.83
            away_prob = away_pow / (away_pow + home_pow)
            home_prob = home_pow / (away_pow + home_pow)
            
        spread_adv = round(abs(home_score - away_score) - 1.5, 2)
        
        return {
            "away_score": away_score,
            "home_score": home_score,
            "total": model_total,
            "away_win_prob": round(away_prob, 3),
            "home_win_prob": round(home_prob, 3),
            "spread_adv": spread_adv
        }
