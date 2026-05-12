import math

class MLBUnifiedEngine:
    """
    Unified MLB Prediction Engine handling NRFI, First 5 (F5), and Full Game projections.
    Refactored to resolve mathematical inconsistencies and data-routing bottlenecks.
    """
    def __init__(self, team_name_mapping, f5_rpg_db, full_rpg_db, hitting_stats_db, team_ba_db, pitcher_metrics_db, sp_ha_db, bullpen_db):
        self.team_name_mapping = team_name_mapping
        self.f5_rpg_db = f5_rpg_db
        self.full_rpg_db = full_rpg_db
        self.hitting_stats_db = hitting_stats_db
        self.team_ba_db = team_ba_db
        self.pitcher_metrics_db = pitcher_metrics_db
        self.sp_ha_db = sp_ha_db
        self.bullpen_db = bullpen_db

        # Global Parameters
        self.lgERA = 4.20
        self.hfa = 1.03
        self.pMin = 0.60
        self.pMax = 1.40
        self.vMin = 0.95
        self.vMax = 1.10

    def _normalize_team_name(self, team_name, source="fangraphs"):
        """Resolves raw team names into matching DB codes."""
        mapping = self.team_name_mapping.get(team_name, {})
        return mapping.get(source, team_name)

    def _get_situational_vars(self, segment):
        """Returns dynamic weights based on the game segment (sp_weight, bp_weight, pythag_exp)."""
        if segment == "f5":
            return 0.95, 0.05, 1.55
        elif segment == "full":
            return 0.60, 0.40, 1.83
        return 0.60, 0.40, 1.83

    def _extract_wrc(self, p_stats):
        """Extracts wRC+ effectively across split records."""
        vl = p_stats.get('vsLHP', {}).get('wrc_plus')
        vr = p_stats.get('vsRHP', {}).get('wrc_plus')
        if vl is not None and vr is not None:
            return (vl + vr) / 2.0
        elif vl is not None:
            return float(vl)
        elif vr is not None:
            return float(vr)
        elif 'wrc_plus' in p_stats:
            return float(p_stats['wrc_plus'])
        return 100.0

    def _calculate_score_segment(self, segment, offense_team, pitching_team, pitcher, offense_is_home, pitcher_is_home, lineup=None):
        off_code = self._normalize_team_name(offense_team, "fangraphs")
        pitch_code = self._normalize_team_name(pitching_team, "fangraphs")

        sp_weight, bp_weight, pythag_exp = self._get_situational_vars(segment)

        # 1. Fetch RPG
        rpg_db = self.f5_rpg_db if segment == "f5" else self.full_rpg_db
        rpg_info = rpg_db.get(off_code, {})
        rpg = 4.50
        if isinstance(rpg_info, dict):
            rpg = float(rpg_info.get("current_2026", rpg_info.get("rpg0", 4.50)))
        elif isinstance(rpg_info, (int, float)):
            rpg = float(rpg_info)
        rpg = max(3.0, min(6.0, rpg))

        # 2. Fetch BA (Split by Home/Away)
        ba_info = self.team_ba_db.get(off_code, {})
        split_key_offense = "home" if offense_is_home else "away"
        ba = float(ba_info.get(split_key_offense, ba_info.get("avg", 0.245)))

        # 3. Fetch wRC+ (The "2 Tms" Trade Artifact Fix)
        wrc = 100.0
        if lineup:
            wrc_list = []
            for player in lineup:
                p_stats = self.hitting_stats_db.get(player)
                if p_stats:
                    # Player found: Process regardless of current team code
                    wrc_list.append(self._extract_wrc(p_stats))
                else:
                    wrc_list.append(100.0)
            if wrc_list:
                wrc = sum(wrc_list) / len(wrc_list)
        else:
            # Fallback if no specific lineup provided
            team_wrcs = []
            for p_name, p_stats in self.hitting_stats_db.items():
                if p_stats.get('team', '') == off_code:
                    team_wrcs.append(self._extract_wrc(p_stats))
            if team_wrcs:
                wrc = sum(team_wrcs) / len(team_wrcs)

        # 4. Fetch SP ERA (The SP HA Routing Fix)
        sp_ha_info = self.sp_ha_db.get(pitcher, {})
        sp = 4.20
        split_key_pitcher = "home" if pitcher_is_home else "away"
        
        if split_key_pitcher in sp_ha_info and "era" in sp_ha_info[split_key_pitcher]:
            sp = float(sp_ha_info[split_key_pitcher]["era"])
        else:
            p_metrics = self.pitcher_metrics_db.get(pitcher, {})
            sp = float(p_metrics.get("xera", p_metrics.get("siera", 4.20)))

        # 5. Fetch BP ERA
        bp_info = self.bullpen_db.get(pitch_code, {})
        bp = 4.39
        if isinstance(bp_info, dict):
            bp = float(bp_info.get("rating", bp_info.get("xera", 4.39)))
        elif isinstance(bp_info, (int, float)):
            bp = float(bp_info)

        # 6. Core Computations
        base_score = 0.6 * rpg + 0.4 * self.lgERA
        
        ba_term = 1.0 if ba <= 0 else (ba / 0.245) ** 0.5
        off = ((wrc / 100.0) ** pythag_exp) * max(0.95, min(1.05, ba_term))
        
        pitchRaw = math.exp(((sp_weight * sp + bp_weight * bp) - self.lgERA) / self.lgERA)
        pitch = max(self.pMin, min(self.pMax, pitchRaw))
        
        # 7. Volatility (vol) Formula Fix (Directional scaling)
        volRaw = 1.0 + ((wrc - 100.0) / 200.0) - ((sp - self.lgERA) / 10.0)
        vol = max(self.vMin, min(self.vMax, volRaw))
        
        hfa_mult = self.hfa if offense_is_home else 1.0
        raw_score = base_score * off * pitch * vol * hfa_mult
        
        return round(max(0.0, min(15.0, raw_score)), 1)

    def _calculate_nrfi_proxy(self, away_team, home_team, away_pitcher, home_pitcher):
        """Robust Proxy NRFI calculation utilizing available core variables."""
        away_code = self._normalize_team_name(away_team, "fangraphs")
        home_code = self._normalize_team_name(home_team, "fangraphs")
        
        p_metrics_a = self.pitcher_metrics_db.get(away_pitcher, {})
        eraA = float(p_metrics_a.get("xera", p_metrics_a.get("siera", 4.20)))
        
        p_metrics_h = self.pitcher_metrics_db.get(home_pitcher, {})
        eraH = float(p_metrics_h.get("xera", p_metrics_h.get("siera", 4.20)))
        
        ba_a = float(self.team_ba_db.get(away_code, {}).get("away", 0.245))
        ba_h = float(self.team_ba_db.get(home_code, {}).get("home", 0.245))
        
        def clamp(val, base, div): return max(0.0, min(1.0, (val - base)/div))
        
        baThrA = clamp(ba_a, 0.25, 0.08)
        baThrH = clamp(ba_h, 0.25, 0.08)
        eraThrA = clamp(eraA, 0.0, 6.0)
        eraThrH = clamp(eraH, 0.0, 6.0)
        
        # Approximated formula combining hitting and pitching threat indicators
        nrfi_score = (
            0.50 + 
            0.03 * (1.0 - baThrA) + 0.03 * (1.0 - baThrH) + 
            0.065 * (1.0 - eraThrA) + 0.065 * (1.0 - eraThrH)
        )
        return round(nrfi_score * 100.0, 1)

    def predict_matchup(self, away_team, home_team, away_pitcher, home_pitcher, away_lineup=None, home_lineup=None):
        """Main prediction method uniting all segments into a comprehensive dictionary."""
        
        # 1. Calculate First 5 (F5) Segment
        away_f5 = self._calculate_score_segment(
            "f5", away_team, home_team, home_pitcher, 
            offense_is_home=False, pitcher_is_home=True, lineup=away_lineup
        )
        home_f5 = self._calculate_score_segment(
            "f5", home_team, away_team, away_pitcher, 
            offense_is_home=True, pitcher_is_home=False, lineup=home_lineup
        )
        
        # 2. Calculate Full Game Segment
        away_full = self._calculate_score_segment(
            "full", away_team, home_team, home_pitcher, 
            offense_is_home=False, pitcher_is_home=True, lineup=away_lineup
        )
        home_full = self._calculate_score_segment(
            "full", home_team, away_team, away_pitcher, 
            offense_is_home=True, pitcher_is_home=False, lineup=home_lineup
        )
        
        # 3. Probabilities Integration
        _, _, pythag_f5 = self._get_situational_vars("f5")
        _, _, pythag_full = self._get_situational_vars("full")
        
        def calc_prob(away_s, home_s, exp):
            if away_s == 0 and home_s == 0:
                return 0.5, 0.5
            a_pow = away_s ** exp
            h_pow = home_s ** exp
            return a_pow / (a_pow + h_pow), h_pow / (a_pow + h_pow)
            
        away_f5_prob, home_f5_prob = calc_prob(away_f5, home_f5, pythag_f5)
        away_full_prob, home_full_prob = calc_prob(away_full, home_full, pythag_full)
        
        # 4. Process NRFI
        nrfi_pct = self._calculate_nrfi_proxy(away_team, home_team, away_pitcher, home_pitcher)
        
        return {
            "NRFI": {
                "confidence_pct": nrfi_pct
            },
            "F5": {
                "away_score": away_f5,
                "home_score": home_f5,
                "total": round(away_f5 + home_f5, 2),
                "away_win_prob": round(away_f5_prob, 3),
                "home_win_prob": round(home_f5_prob, 3),
                "spread_adv": round(abs(home_f5 - away_f5) - 1.5, 2)
            },
            "Full_Game": {
                "away_score": away_full,
                "home_score": home_full,
                "total": round(away_full + home_full, 2),
                "away_win_prob": round(away_full_prob, 3),
                "home_win_prob": round(home_full_prob, 3),
                "spread_adv": round(abs(home_full - away_full) - 1.5, 2)
            }
        }
