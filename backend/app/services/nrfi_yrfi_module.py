import math

class NRFIYRFIModule:
    """
    Standalone Python module to calculate NRFI and YRFI Confidence percentages
    based on MLB statistics and pre-formatted databases.
    """

    def __init__(self, pitcher_db: dict, team_db: dict, ballpark_db: dict, rpg_db: dict, team_name_mapping: dict):
        self.pitcher_db = pitcher_db
        self.team_db = team_db
        self.ballpark_db = ballpark_db
        self.rpg_db = rpg_db
        self.team_mapping = team_name_mapping

        # Fallback "League Average" values
        self.fallback_era = 4.2
        self.fallback_wrc = 100.0
        self.fallback_ba = 0.245
        self.fallback_nrfi_pct = 49.79
        self.fallback_yrfi_pct = 100.0 - 49.79  # 50.21
        self.fallback_ra = 0.5
        self.fallback_rpg = 0.5
        self.fallback_park = 50.0

    @staticmethod
    def DECx(x) -> float:
        """If x > 1, return x/100, otherwise return x."""
        try:
            val = float(x)
            return val / 100.0 if val > 1 else val
        except (ValueError, TypeError):
            return 0.5

    @staticmethod
    def clamp_norm(val, base, divisor) -> float:
        """Return max(0, min(1, (val - base) / divisor))"""
        try:
            return max(0, min(1, (float(val) - base) / divisor))
        except (ValueError, TypeError):
            return 0.5

    def _get_pitcher_stats(self, pitcher_name: str):
        # Allow case-insensitive partial matches if necessary, but assume direct lookup
        data = self.pitcher_db.get(pitcher_name, {})
        nrfi_pct = data.get('nrfi_pct', data.get('pNRFI', self.fallback_nrfi_pct))
        era = data.get('era', data.get('ERA', self.fallback_era))
        return self.DECx(nrfi_pct), float(era)

    def _get_team_stats(self, tcl_name: str, fg_name: str):
        tcl_data = self.team_db.get(tcl_name, {})
        fg_data = self.team_db.get(fg_name, tcl_data)

        # Ensure we return valid numbers using fallback defaults
        t_nrfi = self.DECx(tcl_data.get('nrfi_pct', tcl_data.get('tNRFI', self.fallback_nrfi_pct)))
        t_yrfi = self.DECx(tcl_data.get('yrfi_pct', tcl_data.get('tYRFI', self.fallback_yrfi_pct)))
        ra = self.DECx(tcl_data.get('runs_allowed_pct', tcl_data.get('RA', self.fallback_ra)))

        ba = float(fg_data.get('avg', fg_data.get('BA', self.fallback_ba)))
        wrc = float(fg_data.get('wrc_plus', fg_data.get('wRC+', self.fallback_wrc)))

        return t_nrfi, t_yrfi, ra, ba, wrc

    def _get_ballpark_stats(self, home_tcl: str):
        park_data = {}
        # Ballpark DB is sometimes keyed by Stadium Name
        if home_tcl in self.ballpark_db:
            park_data = self.ballpark_db[home_tcl]
        else:
            for stadium, data in self.ballpark_db.items():
                if isinstance(data, dict) and data.get('team') == home_tcl:
                    park_data = data
                    break

        park_n = self.DECx(park_data.get('nrfi_pct', park_data.get('parkN', self.fallback_park)))
        park_y = self.DECx(park_data.get('yrfi_pct', park_data.get('parkY', self.fallback_park)))
        return park_n, park_y

    def _get_rpg_stats(self, tr_name: str):
        # Support RPG_DATABASE or FIRST_INN_RPG_DATABASE structures
        data = self.rpg_db.get(tr_name, {})

        rpg_2025 = float(data.get('rpg_2025', data.get('prev_2025', self.fallback_rpg)))
        rpg_2026 = float(data.get('rpg_last3', data.get('current_2026', self.fallback_rpg)))
        orpg_2025 = float(data.get('orpg_2025', data.get('prev_2025', self.fallback_rpg)))
        orpg_2026 = float(data.get('orpg_last3', data.get('current_2026', self.fallback_rpg)))

        return rpg_2025, rpg_2026, orpg_2025, orpg_2026

    def calculate(self, away_team: str, home_team: str, away_pitcher: str, home_pitcher: str) -> str:
        # Team Mappings
        away_map = self.team_mapping.get(away_team, {})
        home_map = self.team_mapping.get(home_team, {})

        away_tcl = away_map.get('thecrowdsline', away_map.get('TCL', away_team))
        home_tcl = home_map.get('thecrowdsline', home_map.get('TCL', home_team))
        away_fg = away_map.get('fangraphs', away_map.get('FG', away_team))
        home_fg = home_map.get('fangraphs', home_map.get('FG', home_team))
        away_tr = away_map.get('teamrankings', away_map.get('TR', away_team))
        home_tr = home_map.get('teamrankings', home_map.get('TR', home_team))

        # --- 1. Fetch Pitcher Data ---
        pNRFIa, eraA = self._get_pitcher_stats(away_pitcher)
        pNRFIh, eraH = self._get_pitcher_stats(home_pitcher)

        # --- 2. Fetch Team Data ---
        tNRFIa, tYRFIa, raA, baA, wrcA = self._get_team_stats(away_tcl, away_fg)
        tNRFIh, tYRFIh, raH, baH, wrcH = self._get_team_stats(home_tcl, home_fg)

        # --- 3. Fetch Ballpark Data ---
        parkN, parkY = self._get_ballpark_stats(home_tcl)

        # --- 4. Fetch RPG Data ---
        away_rpg_25, away_rpg_26, away_orpg_25, away_orpg_26 = self._get_rpg_stats(away_tr)
        home_rpg_25, home_rpg_26, home_orpg_25, home_orpg_26 = self._get_rpg_stats(home_tr)

        # Calculate weighted RPG
        rpgA = 0.3 * away_rpg_25 + 0.7 * away_rpg_26
        rpgH = 0.3 * home_rpg_25 + 0.7 * home_rpg_26
        
        # Opponent RPG (orpgVsA = Home Team's Defensive oRPG, orpgVsH = Away Team's Defensive oRPG)
        orpgVsA = 0.3 * home_orpg_25 + 0.7 * home_orpg_26
        orpgVsH = 0.3 * away_orpg_25 + 0.7 * away_orpg_26

        # Normalize RPG (min(1, x))
        rpgA_n = min(1.0, rpgA)
        rpgH_n = min(1.0, rpgH)
        orpgVsA_n = min(1.0, orpgVsA)
        orpgVsH_n = min(1.0, orpgVsH)

        # --- 5. Threshold Calculations ---
        baThrA = self.clamp_norm(baA, 0.25, 0.08)
        baThrH = self.clamp_norm(baH, 0.25, 0.08)

        wrcThrA = self.clamp_norm(wrcA, 100, 50)
        wrcThrH = self.clamp_norm(wrcH, 100, 50)

        eraThrA = self.clamp_norm(eraA, 0, 6)
        eraThrH = self.clamp_norm(eraH, 0, 6)

        # --- 6. NRFI Score (11 Components) ---
        nrfi_score = (
            0.25 * pNRFIa +
            0.25 * pNRFIh +
            0.05 * tNRFIa +
            0.05 * tNRFIh +
            0.15 * parkN +
            0.03 * (1.0 - baThrA) +
            0.03 * (1.0 - baThrH) +
            0.03 * (1.0 - wrcThrA) +
            0.03 * (1.0 - wrcThrH) +
            0.065 * (1.0 - eraThrA) +
            0.065 * (1.0 - eraThrH)
        )

        # --- 7. YRFI Score (6 Components) ---
        era_comp = (min(1.0, eraA / 6.0) + min(1.0, eraH / 6.0)) / 2.0
        
        yrfi_score = (
            0.20 * ((tYRFIa + tYRFIh) / 2.0) +
            0.15 * ((raA + raH) / 2.0) +
            0.25 * ((rpgA_n + rpgH_n) / 2.0) +
            0.20 * ((orpgVsA_n + orpgVsH_n) / 2.0) +
            0.10 * parkY +
            0.10 * era_comp
        )

        # --- 8. Output Final Percentage ---
        final_score = max(nrfi_score, yrfi_score)
        return f"{round(final_score * 100, 1)}%"
