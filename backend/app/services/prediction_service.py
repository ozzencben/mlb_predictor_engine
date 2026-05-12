import os
import json
import logging
from pathlib import Path
from app.services.covers_scraper import CoversMLBScraper
from app.services.mlb_unified_engine import MLBUnifiedEngine

def get_implied_prob(american_odds):
    """
    Converts American odds (e.g., -150 or +130) to implied probability (0 to 1).
    """
    if american_odds is None:
        return None
    try:
        odds = float(american_odds)
        if odds == 0:
            return 0.50
        if odds < 0:
            return -odds / (-odds + 100)
        else:
            return 100 / (odds + 100)
    except (ValueError, TypeError):
        return None

class PredictionService:
    def __init__(self):
        # Resolve the root directory of the project regardless of execution context
        self.root_dir = Path(__file__).resolve().parent.parent.parent
        self.data_dir = self.root_dir / "data"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        self.databases = self.load_static_databases()
        self.engine = MLBUnifiedEngine(
            team_name_mapping=self.databases.get('team_name_mapping', {}),
            f5_rpg_db=self.databases.get('f5_rpg_db', {}),
            full_rpg_db=self.databases.get('full_rpg_db', {}),
            hitting_stats_db=self.databases.get('hitting_stats_db', {}),
            team_ba_db=self.databases.get('team_ba_db', {}),
            pitcher_metrics_db=self.databases.get('pitcher_metrics_db', {}),
            sp_ha_db=self.databases.get('sp_ha_db', {}),
            bullpen_db={}
        )
        self.scraper = CoversMLBScraper()

    def load_static_databases(self):
        """
        Safely loads all static data dictionaries from the exported modules.
        """
        databases = {}
        
        try: from app.data.teamnames import TEAM_NAME_MAPPING
        except ImportError: TEAM_NAME_MAPPING = {}
        databases['team_name_mapping'] = TEAM_NAME_MAPPING if isinstance(TEAM_NAME_MAPPING, dict) else {}

        try: from app.data.f5_rpg_data import F5_RPG_DATABASE
        except ImportError: F5_RPG_DATABASE = {}
        databases['f5_rpg_db'] = F5_RPG_DATABASE if isinstance(F5_RPG_DATABASE, dict) else {}

        try: from app.data.rpg_data import RPG_DATABASE
        except ImportError: RPG_DATABASE = {}
        databases['full_rpg_db'] = RPG_DATABASE if isinstance(RPG_DATABASE, dict) else {}

        try: from app.data.hitting_stats_data import HITTING_STATS
        except ImportError: HITTING_STATS = {}
        if isinstance(HITTING_STATS, list):
            databases['hitting_stats_db'] = {item.get('name', f"Player_{i}"): item for i, item in enumerate(HITTING_STATS)}
        else:
            databases['hitting_stats_db'] = HITTING_STATS if isinstance(HITTING_STATS, dict) else {}

        try: from app.data.team_ba_data import TEAM_BA_DATABASE
        except ImportError: TEAM_BA_DATABASE = {}
        databases['team_ba_db'] = TEAM_BA_DATABASE if isinstance(TEAM_BA_DATABASE, dict) else {}

        try: from app.data.pitching_metrics_data import PITCHER_METRICS
        except ImportError: PITCHER_METRICS = {}
        if isinstance(PITCHER_METRICS, list):
            databases['pitcher_metrics_db'] = {item.get('name', f"Pitcher_{i}"): item for i, item in enumerate(PITCHER_METRICS)}
        else:
            databases['pitcher_metrics_db'] = PITCHER_METRICS if isinstance(PITCHER_METRICS, dict) else {}

        try: from app.data.sp_ha_data import SP_HA_DATABASE
        except ImportError: SP_HA_DATABASE = {}
        if isinstance(SP_HA_DATABASE, list):
            databases['sp_ha_db'] = {item.get('name', f"Pitcher_{i}"): item for i, item in enumerate(SP_HA_DATABASE)}
        else:
            databases['sp_ha_db'] = SP_HA_DATABASE if isinstance(SP_HA_DATABASE, dict) else {}

        return databases

    def run_daily_pipeline(self):
        """
        Executes the scraping and prediction logic and returns the full JSON payload.
        """
        db_path = self.data_dir / "daily_matchups.json"
        
        # Scrape today's data
        daily_matches = self.scraper.build_and_save_daily_db(filename=str(db_path))

        results = []
        if not daily_matches:
            logging.warning("No matches found or failed to scrape data.")
            return results

        for match in daily_matches:
            away_team_raw = match.get("away_team", "Unknown")
            home_team_raw = match.get("home_team", "Unknown")
            
            away_code = self.engine._normalize_team_name(away_team_raw, "fangraphs")
            home_code = self.engine._normalize_team_name(home_team_raw, "fangraphs")

            # Dynamically inject Live Bullpen ERA into the engine
            self.engine.bullpen_db[away_code] = {"rating": match.get("away_bullpen_era", 4.39)}
            self.engine.bullpen_db[home_code] = {"rating": match.get("home_bullpen_era", 4.39)}

            away_pitcher = match.get("away_pitcher") or "Unknown"
            home_pitcher = match.get("home_pitcher") or "Unknown"
            if away_pitcher.upper() == "TBD": away_pitcher = "Unknown"
            if home_pitcher.upper() == "TBD": home_pitcher = "Unknown"

            away_lineup = match.get("away_lineup", [])
            home_lineup = match.get("home_lineup", [])

            odds_data = match.get("odds", {})
            vegas_away_ml = odds_data.get("away_ml")
            vegas_home_ml = odds_data.get("home_ml")
            vegas_total = odds_data.get("ou_total")

            vegas_away_prob = get_implied_prob(vegas_away_ml)
            vegas_home_prob = get_implied_prob(vegas_home_ml)

            try:
                prediction = self.engine.predict_matchup(
                    away_team=away_team_raw, 
                    home_team=home_team_raw, 
                    away_pitcher=away_pitcher, 
                    home_pitcher=home_pitcher,
                    away_lineup=away_lineup,
                    home_lineup=home_lineup
                )
                
                # Extract Engine Results
                nrfi_prob = prediction["NRFI"]["confidence_pct"]
                f5_away_score = prediction["F5"]["away_score"]
                f5_home_score = prediction["F5"]["home_score"]
                full_away_score = prediction["Full_Game"]["away_score"]
                full_home_score = prediction["Full_Game"]["home_score"]
                model_total = prediction["Full_Game"]["total"]
                model_away_win_prob = prediction["Full_Game"]["away_win_prob"]
                model_home_win_prob = prediction["Full_Game"]["home_win_prob"]
                spread_adv = prediction["Full_Game"]["spread_adv"]
                
                # F5 Pick
                if f5_away_score > f5_home_score:
                    f5_pick = away_team_raw
                elif f5_home_score > f5_away_score:
                    f5_pick = home_team_raw
                else:
                    f5_pick = "TIE"

                # Total Play & Confidence
                total_play = "PASS"
                confidence = None
                ou_edge = 0.0
                if vegas_total is not None:
                    try:
                        import math
                        v_total = float(vegas_total)
                        diff = model_total - v_total
                        ou_edge = diff
                        if diff >= 2.0:
                            total_play = "BET OVER"
                        elif diff <= -2.0:
                            total_play = "BET UNDER"
                            
                        # Confidence: MAX(1, MIN(10, ROUNDUP(ABS(model_total - vegas_ou) * 2, 0)))
                        raw_conf = math.ceil(abs(diff) * 2.0)
                        confidence = max(1, min(10, int(raw_conf)))
                    except ValueError:
                        pass

                # ML Edge
                ml_value = "PASS"
                ml_edge = None
                if vegas_away_prob is not None and vegas_home_prob is not None:
                    away_edge = model_away_win_prob - vegas_away_prob
                    home_edge = model_home_win_prob - vegas_home_prob
                    
                    if away_edge >= 0.05:
                        ml_value = "PLAY AWAY"
                        ml_edge = away_edge
                    elif home_edge >= 0.05:
                        ml_value = "PLAY HOME"
                        ml_edge = home_edge
                    else:
                        ml_edge = max(away_edge, home_edge)

                # Inject ALL required fields into original match dictionary
                # Using max confidence from proxy calculation
                match["nrfi_confidence"] = nrfi_prob / 100.0 if nrfi_prob else None
                match["nrfi_prob"] = match["nrfi_confidence"] # legacy compatibility
                match["f5_away_score"] = f5_away_score
                match["f5_home_score"] = f5_home_score
                match["full_away_score"] = full_away_score
                match["full_home_score"] = full_home_score
                match["model_away_win_prob"] = model_away_win_prob
                match["model_home_win_prob"] = model_home_win_prob
                match["model_total"] = model_total
                match["total_play"] = total_play
                match["confidence"] = confidence
                match["spread_adv"] = spread_adv
                
                # Keep legacy values that frontend might expect
                match["f5_pick"] = f5_pick
                match["ou_play"] = total_play
                match["ou_edge"] = round(ou_edge, 2)
                match["ml_value"] = ml_value
                match["ml_edge"] = round(ml_edge, 4) if ml_edge is not None else None
                match["raw_prediction"] = prediction

                results.append(match)
                
            except Exception as e:
                logging.error(f"Error processing {away_team_raw} @ {home_team_raw}: {e}")

        return results
