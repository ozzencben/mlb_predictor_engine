from app.services.mlb_unified_engine import MLBUnifiedEngine

# --- 1. MOCK DATA (Gelişmiş Test Verileri) ---
mock_team_mapping = {
    "Detroit Tigers": {"fangraphs": "DET"},
    "Boston Red Sox": {"fangraphs": "BOS"}
}

mock_f5_rpg = {"DET": 2.50, "BOS": 2.20}
mock_full_rpg = {"DET": 4.30, "BOS": 4.80}

# Takas edilmiş bir oyuncu simüle edelim (Jazz Chisholm Jr.)
mock_hitting_stats = {
    "Riley Greene": {"team": "DET", "wrc_plus": 135},
    "Jazz Chisholm Jr.": {"team": "2 Tms", "wrc_plus": 120}, # Red Sox'a takas olmuş gibi düşünelim
    "Rafael Devers": {"team": "BOS", "wrc_plus": 140}
}

mock_team_ba = {
    "DET": {"away": 0.237, "home": 0.257},
    "BOS": {"away": 0.247, "home": 0.262}
}

mock_pitcher_metrics = {
    "Jack Flaherty": {"xera": 3.20}, # xERA'yı iyileştirdim ki NRFI farkı anlaşılsın
    "Sonny Gray": {"xera": 3.40}
}

# Pitcher Home/Away Splits! (En kritik yeni özelliğimiz)
mock_sp_ha = {
    "Sonny Gray": {
        "home": {"era": 2.80}, # Kendi evinde bir canavar!
        "away": {"era": 4.10}
    }
}

mock_bullpen = {"DET": 4.10, "BOS": 3.50} # Red Sox bullpen'i çok iyi

# --- 2. MOTORU BAŞLATMA ---
engine = MLBUnifiedEngine(
    team_name_mapping=mock_team_mapping,
    f5_rpg_db=mock_f5_rpg,
    full_rpg_db=mock_full_rpg,
    hitting_stats_db=mock_hitting_stats,
    team_ba_db=mock_team_ba,
    pitcher_metrics_db=mock_pitcher_metrics,
    sp_ha_db=mock_sp_ha,
    bullpen_db=mock_bullpen
)

# --- 3. TEST ÇALIŞTIRMA ---
print("Simülasyon Başlıyor: Detroit Tigers @ Boston Red Sox")
print("====================================================\n")

# Opsiyonel Lineup verisi gönderiyoruz
away_lineup = ["Riley Greene"] 
home_lineup = ["Rafael Devers", "Jazz Chisholm Jr."] # Jazz "2 Tms" olmasına rağmen hesaplanacak

results = engine.predict_matchup(
    away_team="Detroit Tigers",
    home_team="Boston Red Sox",
    away_pitcher="Jack Flaherty",
    home_pitcher="Sonny Gray",
    away_lineup=away_lineup,
    home_lineup=home_lineup
)

# --- 4. SONUÇ EKRANI ---
print("🎯 [NRFI/YRFI TAHMİNİ]")
print(f"İlk İnnig'de Sayı OLMAMA İhtimali (NRFI): %{results['NRFI']['confidence_pct']}")
print("-" * 30)

print("⏱️ [F5 - İLK 5 INNING TAHMİNİ]")
print(f"Tigers F5 Skor: {results['F5']['away_score']}")
print(f"Red Sox F5 Skor: {results['F5']['home_score']}")
print(f"F5 Toplam: {results['F5']['total']}")
print(f"Red Sox F5 Kazanma İhtimali: %{results['F5']['home_win_prob'] * 100:.1f}")
print("-" * 30)

print("⚾ [FULL GAME - TAM MAÇ TAHMİNİ]")
print(f"Tigers Tam Maç Skor: {results['Full_Game']['away_score']}")
print(f"Red Sox Tam Maç Skor: {results['Full_Game']['home_score']}")
print(f"Tam Maç Toplam: {results['Full_Game']['total']}")
print(f"Red Sox Maç Sonu Kazanma İhtimali: %{results['Full_Game']['home_win_prob'] * 100:.1f}")
print("====================================================")