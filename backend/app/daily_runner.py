import sys
import os
import json
from pathlib import Path

# Add the root directory to sys.path to allow running from any location
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.covers_scraper import CoversMLBScraper
from app.services.mlb_unified_engine import MLBUnifiedEngine

def load_static_databases():
    """
    Safely loads all static data dictionaries from the exported modules.
    Wraps imports in try-except and validates structural types.
    """
    print("\n--- STEP C: Loading Static Databases ---")
    databases = {}
    
    try:
        from app.data.teamnames import TEAM_NAME_MAPPING
        databases['team_name_mapping'] = TEAM_NAME_MAPPING if isinstance(TEAM_NAME_MAPPING, dict) else {}
        print("[OK] Loaded team_name_mapping")
    except ImportError as e:
        print(f"[ERROR] Failed to load teamnames.py: {e}")
        databases['team_name_mapping'] = {}

    try:
        from app.data.f5_rpg_data import F5_RPG_DATABASE
        databases['f5_rpg_db'] = F5_RPG_DATABASE if isinstance(F5_RPG_DATABASE, dict) else {}
        print("[OK] Loaded f5_rpg_db")
    except ImportError as e:
        print(f"[ERROR] Failed to load f5_rpg_data.py: {e}")
        databases['f5_rpg_db'] = {}

    try:
        from app.data.rpg_data import RPG_DATABASE
        databases['full_rpg_db'] = RPG_DATABASE if isinstance(RPG_DATABASE, dict) else {}
        print("[OK] Loaded full_rpg_db")
    except ImportError as e:
        print(f"[ERROR] Failed to load rpg_data.py: {e}")
        databases['full_rpg_db'] = {}

    try:
        from app.data.hitting_stats_data import HITTING_STATS
        # If it happens to be a list, convert to dict using 'name' or similar if present
        if isinstance(HITTING_STATS, list):
            databases['hitting_stats_db'] = {item.get('name', f"Player_{i}"): item for i, item in enumerate(HITTING_STATS)}
        else:
            databases['hitting_stats_db'] = HITTING_STATS if isinstance(HITTING_STATS, dict) else {}
        print("[OK] Loaded hitting_stats_db")
    except ImportError as e:
        print(f"[ERROR] Failed to load hitting_stats_data.py: {e}")
        databases['hitting_stats_db'] = {}

    try:
        from app.data.team_ba_data import TEAM_BA_DATABASE
        databases['team_ba_db'] = TEAM_BA_DATABASE if isinstance(TEAM_BA_DATABASE, dict) else {}
        print("[OK] Loaded team_ba_db")
    except ImportError as e:
        print(f"[ERROR] Failed to load team_ba_data.py: {e}")
        databases['team_ba_db'] = {}

    try:
        from app.data.pitching_metrics_data import PITCHER_METRICS
        if isinstance(PITCHER_METRICS, list):
            databases['pitcher_metrics_db'] = {item.get('name', f"Pitcher_{i}"): item for i, item in enumerate(PITCHER_METRICS)}
        else:
            databases['pitcher_metrics_db'] = PITCHER_METRICS if isinstance(PITCHER_METRICS, dict) else {}
        print("[OK] Loaded pitcher_metrics_db")
    except ImportError as e:
        print(f"[ERROR] Failed to load pitching_metrics_data.py: {e}")
        databases['pitcher_metrics_db'] = {}

    try:
        from app.data.sp_ha_data import SP_HA_DATABASE
        if isinstance(SP_HA_DATABASE, list):
            databases['sp_ha_db'] = {item.get('name', f"Pitcher_{i}"): item for i, item in enumerate(SP_HA_DATABASE)}
        else:
            databases['sp_ha_db'] = SP_HA_DATABASE if isinstance(SP_HA_DATABASE, dict) else {}
        print("[OK] Loaded sp_ha_db")
    except ImportError as e:
        print(f"[ERROR] Failed to load sp_ha_data.py: {e}")
        databases['sp_ha_db'] = {}

    return databases


def main():
    print("================================================")
    print("      MLB PREDICTOR ENGINE - DAILY RUNNER       ")
    print("================================================\n")

    # Step A: Instantiate CoversMLBScraper and run build_and_save_daily_db()
    print("--- STEP A: Fetching Today's Live Bullpen Stats ---")
    scraper = CoversMLBScraper()
    # Wait, the scraper uses a relative path. Let's make it absolute to project root.
    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    db_path = Path(root_dir) / "data" / "bullpen_db.json"
    
    # Passing the exact path ensures it correctly goes to the intended data/ dir
    scraper.build_and_save_daily_db(filename=str(db_path))

    # Step B: Load the freshly scraped data/bullpen_db.json into a Python dictionary
    print("\n--- STEP B: Loading Bullpen DB ---")
    bullpen_db = {}
    try:
        if db_path.exists():
            with open(db_path, "r", encoding="utf-8") as f:
                bullpen_db = json.load(f)
            print(f"Loaded {len(bullpen_db)} teams from {db_path}")
        else:
            print(f"Warning: {db_path} not found. Fallback to default 4.39 BP ERA.")
    except Exception as e:
        print(f"Error loading {db_path}: {e}. Fallback to default 4.39 BP ERA.")

    # Step C: Load other static databases (The Wiring)
    databases = load_static_databases()

    # Step D: Instantiate MLBUnifiedEngine
    print("\n--- STEP D: Instantiating MLBUnifiedEngine ---")
    engine = MLBUnifiedEngine(
        team_name_mapping=databases['team_name_mapping'],
        f5_rpg_db=databases['f5_rpg_db'],
        full_rpg_db=databases['full_rpg_db'],
        hitting_stats_db=databases['hitting_stats_db'],
        team_ba_db=databases['team_ba_db'],
        pitcher_metrics_db=databases['pitcher_metrics_db'],
        sp_ha_db=databases['sp_ha_db'],
        bullpen_db=bullpen_db
    )
    print("Engine instantiated successfully with real static data.")

    # DEDEKTİF KODU (Step D'den hemen sonra ekle)
    print("\n--- DATABASE KEY INSPECTOR ---")
    sample_keys = list(engine.hitting_stats_db.keys())[:5]
    print(f"Hitting DB'deki ilk 5 örnek isim: {sample_keys}")
    
    # "Harper" kelimesini içeren tüm kayıtları ara
    harper_matches = [k for k in engine.hitting_stats_db.keys() if "Harper" in str(k)]
    print(f"İçinde 'Harper' geçen kayıtlar: {harper_matches}")
    print("------------------------------")

    # --- STEP E: Running Prediction ---
    print("\n--- STEP E: Running Prediction ---")
    
    away_team = "Philadelphia Phillies"
    home_team = "Atlanta Braves"
    away_pitcher = "Aaron Nola"
    home_pitcher = "Chris Sale"

    # Sahaya çıkacak gerçek oyuncuları (Lineup) veriyoruz
    away_lineup = ["Kyle Schwarber", "Trea Turner", "Bryce Harper", "J.T. Realmuto", "Alec Bohm"]
    home_lineup = ["Ronald Acuña Jr.", "Ozzie Albies", "Austin Riley", "Matt Olson", "Marcell Ozuna"]

    # Motorun Bryce Harper'ı nasıl okuduğunu doğru şekilde test edelim:
    harper_data = engine.hitting_stats_db.get("Bryce Harper", {})
    harper_wrc = engine._extract_wrc(harper_data)
    print(f"Sistem Kontrolü -> Bryce Harper Hesaplanan wRC+: {harper_wrc}")
    print("------------------------------------------------")

    prediction = engine.predict_matchup(
        away_team=away_team, 
        home_team=home_team, 
        away_pitcher=away_pitcher, 
        home_pitcher=home_pitcher,
        away_lineup=away_lineup,   # <--- İŞTE SİHİR BURADA
        home_lineup=home_lineup    # <--- İŞTE SİHİR BURADA
    )

    # (Buradan sonrası aynı print Matchup Report kısmı)

    # Print clean formatted report to console
    print("\n================ MATCHUP REPORT ================")
    print(f"Matchup: {away_team} (Away) vs {home_team} (Home)")
    print(f"Pitchers: {away_pitcher} vs {home_pitcher}")
    print("------------------------------------------------")
    print(f"NRFI Confidence: {prediction['NRFI']['confidence_pct']}%")
    print("------------------------------------------------")
    print("First 5 Innings (F5):")
    print(f"  {away_team} Score: {prediction['F5']['away_score']}")
    print(f"  {home_team} Score: {prediction['F5']['home_score']}")
    print(f"  Total: {prediction['F5']['total']}")
    print(f"  {away_team} Win Prob: {prediction['F5']['away_win_prob']*100:.1f}%")
    print(f"  {home_team} Win Prob: {prediction['F5']['home_win_prob']*100:.1f}%")
    if prediction['F5']['home_score'] > prediction['F5']['away_score']:
        print(f"  Spread Adv: {home_team} -1.5")
    else:
        print(f"  Spread Adv: {away_team} -1.5")
    print("------------------------------------------------")
    print("Full Game:")
    print(f"  {away_team} Score: {prediction['Full_Game']['away_score']}")
    print(f"  {home_team} Score: {prediction['Full_Game']['home_score']}")
    print(f"  Total: {prediction['Full_Game']['total']}")
    print(f"  {away_team} Win Prob: {prediction['Full_Game']['away_win_prob']*100:.1f}%")
    print(f"  {home_team} Win Prob: {prediction['Full_Game']['home_win_prob']*100:.1f}%")
    if prediction['Full_Game']['home_score'] > prediction['Full_Game']['away_score']:
        print(f"  Spread Adv: {home_team} -1.5")
    else:
        print(f"  Spread Adv: {away_team} -1.5")
    print("================================================\n")

if __name__ == "__main__":
    main()
