import math

from app.services.mlb_model_module import MLBModelModule

# --- 1. MOCK DATA (Test Verileri) ---
# Gerçek projedeki veritabanlarından import edilecek kısımlar
mock_team_mapping = {
    "Detroit Tigers": "DET",
    "Boston Red Sox": "BOS"
}

# Tam maç (9 Inning) RPG verileri (F5 verilerinden daha yüksektir)
mock_full_rpg = {
    "DET": {"current_2026": 4.30}, 
    "BOS": {"current_2026": 4.80}
}

mock_team_db = {
    "DET": {"wrc_plus": 106, "avg": 0.249},
    "BOS": {"wrc_plus": 124, "avg": 0.271}
}

mock_pitcher_metrics = {
    "Jack Flaherty": {"xera": 5.4, "siera": 5.5},
    "Sonny Gray": {"xera": 5.6, "siera": 4.4}
}

# Bullpen verisi elimizde yok, ama boş sözlük göndersek bile 
# motor 4.39 (Lig Ortalaması) atayarak çalışmaya devam edecek.
mock_bullpen = {} 

# --- 2. MODELİ BAŞLATMA ---
# (MLBModelModule sınıfının aynı dosyada veya import edildiğini varsayıyoruz)
mlb_engine = MLBModelModule(
    team_name_mapping=mock_team_mapping,
    full_rpg_database=mock_full_rpg,
    team_database=mock_team_db,
    pitcher_metrics=mock_pitcher_metrics,
    bullpen_database=mock_bullpen
)

# --- 3. TEST ÇALIŞTIRMA ---
# Matchup: Detroit Tigers (Jack Flaherty) @ Boston Red Sox (Sonny Gray)
prediction = mlb_engine.calculate(
    away_team="Detroit Tigers",
    home_team="Boston Red Sox",
    away_pitcher="Jack Flaherty",
    home_pitcher="Sonny Gray"
)

# --- 4. SONUÇLARI GÖRÜNTÜLEME ---
print("--- FULL MLB MODEL (9 INNING) TEST SONUÇLARI ---")
print(f"Deplasman (Tigers) Tahmini Skor: {prediction['away_score']}")
print(f"Ev Sahibi (Red Sox) Tahmini Skor: {prediction['home_score']}")
print(f"Model Toplam Sayı: {prediction['total']}")
print(f"Ev Sahibi Kazanma Olasılığı: {round(prediction['home_win_prob'] * 100, 1)}%")
print(f"Spread Avantajı: {prediction['spread_adv']}")
print("------------------------------------------------")