import sys
import os
import json
from pathlib import Path

# Add the root directory to sys.path to allow running from any location
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

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

def load_static_databases():
    """
    Safely loads all static data dictionaries from the exported modules.
    Wraps imports in try-except and validates structural types.
    """
    databases = {}
    
    try:
        from app.data.teamnames import TEAM_NAME_MAPPING
        databases['team_name_mapping'] = TEAM_NAME_MAPPING if isinstance(TEAM_NAME_MAPPING, dict) else {}
    except ImportError:
        databases['team_name_mapping'] = {}

    try:
        from app.data.f5_rpg_data import F5_RPG_DATABASE
        databases['f5_rpg_db'] = F5_RPG_DATABASE if isinstance(F5_RPG_DATABASE, dict) else {}
    except ImportError:
        databases['f5_rpg_db'] = {}

    try:
        from app.data.rpg_data import RPG_DATABASE
        databases['full_rpg_db'] = RPG_DATABASE if isinstance(RPG_DATABASE, dict) else {}
    except ImportError:
        databases['full_rpg_db'] = {}

    try:
        from app.data.hitting_stats_data import HITTING_STATS
        if isinstance(HITTING_STATS, list):
            databases['hitting_stats_db'] = {item.get('name', f"Player_{i}"): item for i, item in enumerate(HITTING_STATS)}
        else:
            databases['hitting_stats_db'] = HITTING_STATS if isinstance(HITTING_STATS, dict) else {}
    except ImportError:
        databases['hitting_stats_db'] = {}

    try:
        from app.data.team_ba_data import TEAM_BA_DATABASE
        databases['team_ba_db'] = TEAM_BA_DATABASE if isinstance(TEAM_BA_DATABASE, dict) else {}
    except ImportError:
        databases['team_ba_db'] = {}

    try:
        from app.data.pitching_metrics_data import PITCHER_METRICS
        if isinstance(PITCHER_METRICS, list):
            databases['pitcher_metrics_db'] = {item.get('name', f"Pitcher_{i}"): item for i, item in enumerate(PITCHER_METRICS)}
        else:
            databases['pitcher_metrics_db'] = PITCHER_METRICS if isinstance(PITCHER_METRICS, dict) else {}
    except ImportError:
        databases['pitcher_metrics_db'] = {}

    try:
        from app.data.sp_ha_data import SP_HA_DATABASE
        if isinstance(SP_HA_DATABASE, list):
            databases['sp_ha_db'] = {item.get('name', f"Pitcher_{i}"): item for i, item in enumerate(SP_HA_DATABASE)}
        else:
            databases['sp_ha_db'] = SP_HA_DATABASE if isinstance(SP_HA_DATABASE, dict) else {}
    except ImportError:
        databases['sp_ha_db'] = {}

    return databases

def main():
    if sys.stdout.encoding.lower() != 'utf-8':
        sys.stdout.reconfigure(encoding='utf-8')
        
    print("=====================================================================================================================================")
    print("                                            MLB PREDICTOR ENGINE - AUTOMATED VALUE HUNTER                                            ")
    print("=====================================================================================================================================\n")

    print("[*] Loading Static Databases...")
    databases = load_static_databases()
    
    print("[*] Instantiating MLBUnifiedEngine...")
    engine = MLBUnifiedEngine(
        team_name_mapping=databases['team_name_mapping'],
        f5_rpg_db=databases['f5_rpg_db'],
        full_rpg_db=databases['full_rpg_db'],
        hitting_stats_db=databases['hitting_stats_db'],
        team_ba_db=databases['team_ba_db'],
        pitcher_metrics_db=databases['pitcher_metrics_db'],
        sp_ha_db=databases['sp_ha_db'],
        bullpen_db={}
    )

    print("[*] Instantiating CoversMLBScraper and fetching today's matchups with Vegas Odds...")
    scraper = CoversMLBScraper()
    root_dir = os.path.dirname(os.path.abspath(__file__))
    db_path = Path(root_dir) / "data" / "daily_matchups.json"
    
    daily_matches = scraper.build_and_save_daily_db(filename=str(db_path))

    if not daily_matches:
        print("[!] No matches found or failed to scrape data.")
        return

    print(f"\n[*] Successfully loaded {len(daily_matches)} matchups. Processing Predictions...\n")

    # Table Header
    header = f"{'Matchup':<23} | {'Pitchers':<28} | {'NRFI %':<8} | {'F5 Pick':<15} | {'O/U Play (Edge)':<20} | {'ML Value (Edge)':<25}"
    print("-" * 133)
    print(header)
    print("-" * 133)

    for match in daily_matches:
        away_team_raw = match.get("away_team", "Unknown")
        home_team_raw = match.get("home_team", "Unknown")
        
        away_code = engine._normalize_team_name(away_team_raw, "fangraphs")
        home_code = engine._normalize_team_name(home_team_raw, "fangraphs")

        # Dynamically inject Live Bullpen ERA into the engine
        engine.bullpen_db[away_code] = {"rating": match.get("away_bullpen_era", 4.39)}
        engine.bullpen_db[home_code] = {"rating": match.get("home_bullpen_era", 4.39)}

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
            prediction = engine.predict_matchup(
                away_team=away_team_raw, 
                home_team=home_team_raw, 
                away_pitcher=away_pitcher, 
                home_pitcher=home_pitcher,
                away_lineup=away_lineup,
                home_lineup=home_lineup
            )
            
            nrfi_prob = prediction["NRFI"]["confidence_pct"]
            f5_away_score = prediction["F5"]["away_score"]
            f5_home_score = prediction["F5"]["home_score"]
            full_away_score = prediction["Full_Game"]["away_score"]
            full_home_score = prediction["Full_Game"]["home_score"]
            model_total = prediction["Full_Game"]["total"]
            model_away_win_prob = prediction["Full_Game"]["away_win_prob"]
            model_home_win_prob = prediction["Full_Game"]["home_win_prob"]
            spread_adv = prediction["Full_Game"]["spread_adv"]
            
            # --- F5 Pick ---
            if f5_away_score > f5_home_score:
                f5_pick = away_team_raw[:15]
            elif f5_home_score > f5_away_score:
                f5_pick = home_team_raw[:15]
            else:
                f5_pick = "TIE"

            # --- Total Play & Confidence ---
            total_play = "PASS"
            confidence = None
            ou_play = "AWAITING ODDS"
            if vegas_total is not None:
                try:
                    import math
                    v_total = float(vegas_total)
                    diff = model_total - v_total
                    if diff >= 2.0:
                        total_play = "BET OVER"
                        ou_play = f"BET OVER (+{diff:.1f})"
                    elif diff <= -2.0:
                        total_play = "BET UNDER"
                        ou_play = f"BET UNDER ({diff:.1f})"
                    else:
                        total_play = "PASS"
                        ou_play = "PASS"

                    raw_conf = math.ceil(abs(diff) * 2.0)
                    confidence = max(1, min(10, int(raw_conf)))
                except ValueError:
                    ou_play = "PASS"

            # --- ML Edge ---
            ml_value = "AWAITING ODDS"
            ml_edge = None
            if vegas_away_prob is not None and vegas_home_prob is not None:
                away_edge = model_away_win_prob - vegas_away_prob
                home_edge = model_home_win_prob - vegas_home_prob
                
                if away_edge >= 0.05:
                    ml_value = f"🔥 PLAY AWAY (+{away_edge*100:.1f}%)"
                    ml_edge = away_edge
                elif home_edge >= 0.05:
                    ml_value = f"🔥 PLAY HOME (+{home_edge*100:.1f}%)"
                    ml_edge = home_edge
                else:
                    ml_value = "PASS"
                    ml_edge = max(away_edge, home_edge)

            # --- Inject into Original Dict ---
            match["nrfi_prob"] = nrfi_prob / 100.0 if nrfi_prob else None
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
            match["f5_pick"] = f5_pick
            match["ou_play"] = total_play
            match["ml_edge"] = round(ml_edge, 4) if ml_edge is not None else None

            # Formatting
            matchup_str = f"{away_team_raw[:10]} @ {home_team_raw[:10]}"
            pitchers_str = f"{away_pitcher[:13]} v {home_pitcher[:12]}"
            nrfi_str = f"{nrfi_prob:.1f}%"
            if nrfi_prob > 65.0:
                nrfi_str = f"*{nrfi_str}*"

            row = f"{matchup_str:<23} | {pitchers_str:<28} | {nrfi_str:<8} | {f5_pick:<15} | {ou_play:<20} | {ml_value:<25}"
            print(row)
            
        except Exception as e:
            err_msg = f"{away_team_raw} @ {home_team_raw} -> ERROR: {e}"
            print(f"{err_msg:<133}")

    print("-" * 133)
    print("* = High Confidence NRFI Picks (>65%)")
    
    # Write back to JSON to persist the injected fields
    with open(db_path, "w", encoding="utf-8") as f:
        json.dump(daily_matches, f, indent=4, ensure_ascii=False)
        
    print(f"[*] Enriched data successfully saved to {db_path}")
    print("Done. Happy hunting!")

if __name__ == "__main__":
    main()
